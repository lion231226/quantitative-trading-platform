"""
Unit tests for dependency checking functionality.

This test suite provides comprehensive coverage of the dependency
checking modules with mocking for external dependencies.
"""

import unittest
from unittest.mock import patch, MagicMock, mock_open
import asyncio
import sys
import os
import json
from pathlib import Path

# Add the project root to the path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.dependency_checker import (
    DependencyChecker, DependencyInfo, DependencyStatus, DependencyType,
    VersionInfo, VersionComparator
)
from utils.network_utils import NetworkChecker, NetworkStatus, PackageManagerType
from core.dependency_reporter import DependencyReporter, InstallationSuggestion
from core.environment_checker import EnvironmentChecker


class TestVersionInfo(unittest.TestCase):
    """Test VersionInfo class functionality"""

    def test_version_info_creation(self):
        """Test VersionInfo object creation and string representation"""
        version = VersionInfo(18, 17, 0)
        self.assertEqual(version.major, 18)
        self.assertEqual(version.minor, 17)
        self.assertEqual(version.patch, 0)
        self.assertEqual(str(version), "18.17.0")

    def test_version_info_with_build_and_prerelease(self):
        """Test VersionInfo with build and prerelease components"""
        version = VersionInfo(1, 2, 3, build="abc123", prerelease="beta")
        self.assertEqual(str(version), "1.2.3+abc123-beta")

    def test_version_from_string(self):
        """Test parsing version strings"""
        # Test standard version
        version = VersionInfo.from_string("18.17.0")
        self.assertEqual(version.major, 18)
        self.assertEqual(version.minor, 17)
        self.assertEqual(version.patch, 0)

        # Test version with v prefix
        version = VersionInfo.from_string("v3.9.7")
        self.assertEqual(version.major, 3)
        self.assertEqual(version.minor, 9)
        self.assertEqual(version.patch, 7)

        # Test version with prerelease
        version = VersionInfo.from_string("1.0.0-beta")
        self.assertEqual(version.major, 1)
        self.assertEqual(version.minor, 0)
        self.assertEqual(version.patch, 0)
        self.assertEqual(version.prerelease, "beta")

        # Test version with build
        version = VersionInfo.from_string("1.0.0+build123")
        self.assertEqual(version.major, 1)
        self.assertEqual(version.minor, 0)
        self.assertEqual(version.patch, 0)
        self.assertEqual(version.build, "build123")

    def test_version_from_string_partial(self):
        """Test parsing partial version strings"""
        version = VersionInfo.from_string("3.9")
        self.assertEqual(version.major, 3)
        self.assertEqual(version.minor, 9)
        self.assertEqual(version.patch, 0)

        version = VersionInfo.from_string("5")
        self.assertEqual(version.major, 5)
        self.assertEqual(version.minor, 0)
        self.assertEqual(version.patch, 0)


class TestVersionComparator(unittest.TestCase):
    """Test version comparison functionality"""

    def test_compare_versions_equal(self):
        """Test comparing equal versions"""
        result = VersionComparator.compare_versions("1.0.0", "1.0.0")
        self.assertEqual(result, 0)

        result = VersionComparator.compare_versions(VersionInfo(1, 0, 0), VersionInfo(1, 0, 0))
        self.assertEqual(result, 0)

    def test_compare_versions_less_than(self):
        """Test comparing versions where first is less than second"""
        result = VersionComparator.compare_versions("1.0.0", "2.0.0")
        self.assertEqual(result, -1)

        result = VersionComparator.compare_versions("1.0.0", "1.1.0")
        self.assertEqual(result, -1)

        result = VersionComparator.compare_versions("1.0.0", "1.0.1")
        self.assertEqual(result, -1)

    def test_compare_versions_greater_than(self):
        """Test comparing versions where first is greater than second"""
        result = VersionComparator.compare_versions("2.0.0", "1.0.0")
        self.assertEqual(result, 1)

        result = VersionComparator.compare_versions("1.1.0", "1.0.0")
        self.assertEqual(result, 1)

        result = VersionComparator.compare_versions("1.0.1", "1.0.0")
        self.assertEqual(result, 1)

    def test_meets_requirement(self):
        """Test version requirement checking"""
        # Meets requirement
        self.assertTrue(VersionComparator.meets_requirement("1.5.0", "1.0.0"))
        self.assertTrue(VersionComparator.meets_requirement("2.0.0", "1.5.0"))

        # Does not meet requirement
        self.assertFalse(VersionComparator.meets_requirement("1.0.0", "1.5.0"))
        self.assertFalse(VersionComparator.meets_requirement("0.9.0", "1.0.0"))

        # Equal versions meet requirement
        self.assertTrue(VersionComparator.meets_requirement("1.0.0", "1.0.0"))


class TestDependencyChecker(unittest.TestCase):
    """Test dependency checking functionality"""

    def setUp(self):
        """Set up test fixtures"""
        self.checker = DependencyChecker()

    @patch('shutil.which')
    def test_find_executable_found(self, mock_which):
        """Test finding an executable that exists"""
        mock_which.return_value = "/usr/bin/node"

        result = self.checker._find_executable(DependencyType.NODEJS)
        self.assertEqual(result, "/usr/bin/node")

    @patch('shutil.which')
    @patch('os.path.exists')
    def test_find_executable_in_common_paths(self, mock_exists, mock_which):
        """Test finding executable in common paths"""
        mock_which.return_value = None
        mock_exists.return_value = True

        # Mock the _get_common_paths method
        with patch.object(self.checker, '_get_common_paths', return_value=['/usr/local/bin']):
            result = self.checker._find_executable(DependencyType.NODEJS)
            self.assertIsNotNone(result)

    @patch('shutil.which')
    @patch('os.path.exists')
    def test_find_executable_not_found(self, mock_exists, mock_which):
        """Test failing to find executable"""
        mock_which.return_value = None
        mock_exists.return_value = False

        with patch.object(self.checker, '_get_common_paths', return_value=['/usr/bin']):
            result = self.checker._find_executable(DependencyType.NODEJS)
            self.assertIsNone(result)

    @patch.object(DependencyChecker, '_find_executable')
    @patch.object(DependencyChecker, '_run_command')
    def test_check_nodejs_success(self, mock_run_command, mock_find_executable):
        """Test successful Node.js check"""
        mock_find_executable.return_value = "/usr/bin/node"
        mock_run_command.return_value = (True, "v18.17.0", "")

        result = self.checker.check_nodejs()

        self.assertEqual(result.name, "Node.js")
        self.assertEqual(result.type, DependencyType.NODEJS)
        self.assertEqual(result.status, DependencyStatus.INSTALLED)
        self.assertEqual(result.executable_path, "/usr/bin/node")
        self.assertEqual(str(result.version), "18.17.0")

    @patch.object(DependencyChecker, '_find_executable')
    def test_check_nodejs_not_installed(self, mock_find_executable):
        """Test Node.js not installed"""
        mock_find_executable.return_value = None

        result = self.checker.check_nodejs()

        self.assertEqual(result.status, DependencyStatus.NOT_INSTALLED)
        self.assertIn("not found", result.error_message)

    @patch.object(DependencyChecker, '_find_executable')
    @patch.object(DependencyChecker, '_run_command')
    def test_check_nodejs_version_mismatch(self, mock_run_command, mock_find_executable):
        """Test Node.js version mismatch"""
        mock_find_executable.return_value = "/usr/bin/node"
        mock_run_command.return_value = (True, "v14.0.0", "")  # Below minimum 16.0.0

        result = self.checker.check_nodejs()

        self.assertEqual(result.status, DependencyStatus.VERSION_MISMATCH)
        self.assertIn("below minimum requirement", result.error_message)

    @patch.object(DependencyChecker, '_find_executable')
    @patch.object(DependencyChecker, '_run_command')
    def test_check_nodejs_command_failure(self, mock_run_command, mock_find_executable):
        """Test Node.js command failure"""
        mock_find_executable.return_value = "/usr/bin/node"
        mock_run_command.return_value = (False, "", "Permission denied")

        result = self.checker.check_nodejs()

        self.assertEqual(result.status, DependencyStatus.INACCESSIBLE)
        self.assertIn("Failed to get Node.js version", result.error_message)

    @patch.object(DependencyChecker, 'check_nodejs')
    @patch.object(DependencyChecker, 'check_python')
    @patch.object(DependencyChecker, 'check_git')
    def test_check_all_dependencies(self, mock_check_git, mock_check_python, mock_check_nodejs):
        """Test checking all dependencies"""
        # Mock successful checks
        mock_check_nodejs.return_value = DependencyInfo(
            name="Node.js", type=DependencyType.NODEJS, status=DependencyStatus.INSTALLED
        )
        mock_check_python.return_value = DependencyInfo(
            name="Python", type=DependencyType.PYTHON, status=DependencyStatus.INSTALLED
        )
        mock_check_git.return_value = DependencyInfo(
            name="Git", type=DependencyType.GIT, status=DependencyStatus.INSTALLED
        )

        result = self.checker.check_all_dependencies()

        self.assertEqual(len(result), 3)  # NODEJS, PYTHON, GIT
        self.assertIn(DependencyType.NODEJS, result)
        self.assertIn(DependencyType.PYTHON, result)
        self.assertIn(DependencyType.GIT, result)

    def test_get_missing_dependencies(self):
        """Test getting missing dependencies"""
        # Create mock dependencies
        self.checker.checked_dependencies = {
            DependencyType.NODEJS: DependencyInfo(
                name="Node.js", type=DependencyType.NODEJS, status=DependencyStatus.INSTALLED
            ),
            DependencyType.PYTHON: DependencyInfo(
                name="Python", type=DependencyType.PYTHON, status=DependencyStatus.NOT_INSTALLED
            ),
            DependencyType.GIT: DependencyInfo(
                name="Git", type=DependencyType.GIT, status=DependencyStatus.VERSION_MISMATCH
            )
        }

        missing = self.checker.get_missing_dependencies()

        self.assertEqual(len(missing), 2)
        self.assertEqual(missing[0].type, DependencyType.PYTHON)
        self.assertEqual(missing[1].type, DependencyType.GIT)

    def test_get_dependency_summary(self):
        """Test getting dependency summary"""
        # Create mock dependencies
        self.checker.checked_dependencies = {
            DependencyType.NODEJS: DependencyInfo(
                name="Node.js", type=DependencyType.NODEJS, status=DependencyStatus.INSTALLED
            ),
            DependencyType.PYTHON: DependencyInfo(
                name="Python", type=DependencyType.PYTHON, status=DependencyStatus.NOT_INSTALLED
            )
        }

        summary = self.checker.get_dependency_summary()

        self.assertEqual(summary["total_dependencies"], 2)
        self.assertEqual(summary["installed"], 1)
        self.assertEqual(summary["missing"], 1)


class TestNetworkChecker(unittest.TestCase):
    """Test network checking functionality"""

    def setUp(self):
        """Set up test fixtures"""
        self.checker = NetworkChecker()

    def test_detect_proxy_config_no_proxy(self):
        """Test detecting no proxy configuration"""
        # Clear proxy environment variables
        with patch.dict(os.environ, {}, clear=True):
            config = self.checker.detect_proxy_config()

            self.assertFalse(config.enabled)
            self.assertIsNone(config.http_proxy)
            self.assertIsNone(config.https_proxy)

    def test_detect_proxy_config_with_http_proxy(self):
        """Test detecting HTTP proxy configuration"""
        with patch.dict(os.environ, {"HTTP_PROXY": "http://proxy.example.com:8080"}):
            config = self.checker.detect_proxy_config()

            self.assertTrue(config.enabled)
            self.assertEqual(config.http_proxy, "http://proxy.example.com:8080")

    def test_detect_proxy_config_with_auth(self):
        """Test detecting proxy configuration with authentication"""
        with patch.dict(os.environ, {"HTTP_PROXY": "http://user:pass@proxy.example.com:8080"}):
            config = self.checker.detect_proxy_config()

            self.assertTrue(config.enabled)
            self.assertTrue(config.proxy_auth)

    @patch('urllib.request.urlopen')
    def test_test_url_accessibility_success(self, mock_urlopen):
        """Test successful URL accessibility test"""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_urlopen.return_value.__enter__.return_value = mock_response

        async def run_test():
            return await self.checker.test_url_accessibility("https://example.com")

        result = asyncio.run(run_test())

        self.assertTrue(result[0])  # accessible
        self.assertGreater(result[1], 0)  # response_time
        self.assertEqual(result[2], "")  # error_message

    @patch('urllib.request.urlopen')
    def test_test_url_accessibility_http_error(self, mock_urlopen):
        """Test URL accessibility test with HTTP error"""
        from urllib.error import HTTPError

        mock_urlopen.side_effect = HTTPError(
            url="https://example.com",
            code=404,
            msg="Not Found",
            hdrs={},
            fp=None
        )

        async def run_test():
            return await self.checker.test_url_accessibility("https://example.com")

        result = asyncio.run(run_test())

        self.assertFalse(result[0])  # accessible
        self.assertGreater(result[1], 0)  # response_time
        self.assertIn("HTTP 404", result[2])  # error_message

    def test_detect_offline_mode_env_var(self):
        """Test detecting offline mode via environment variable"""
        with patch.dict(os.environ, {"OFFLINE_MODE": "true"}):
            result = self.checker.detect_offline_mode()
            self.assertTrue(result)

    @patch('socket.gethostbyname')
    def test_detect_offline_mode_dns_failure(self, mock_gethostbyname):
        """Test detecting offline mode via DNS failure"""
        mock_gethostbyname.side_effect = socket.gaierror("Name resolution failed")

        result = self.checker.detect_offline_mode()
        self.assertTrue(result)


class TestDependencyReporter(unittest.TestCase):
    """Test dependency reporting functionality"""

    def setUp(self):
        """Set up test fixtures"""
        self.reporter = DependencyReporter()

    def test_generate_installation_suggestion(self):
        """Test generating installation suggestion"""
        dependency_info = DependencyInfo(
            name="Node.js",
            type=DependencyType.NODEJS,
            status=DependencyStatus.NOT_INSTALLED
        )

        with patch.object(self.reporter, '_get_platform_name', return_value="windows"):
            suggestion = self.reporter.generate_installation_suggestion(dependency_info)

            self.assertEqual(suggestion.dependency_name, "Node.js")
            self.assertEqual(suggestion.dependency_type, DependencyType.NODEJS)
            self.assertEqual(suggestion.platform, "windows")
            self.assertGreater(len(suggestion.install_commands), 0)

    def test_analyze_dependencies_all_installed(self):
        """Test analyzing dependencies when all are installed"""
        dependencies = {
            DependencyType.NODEJS: DependencyInfo(
                name="Node.js", type=DependencyType.NODEJS, status=DependencyStatus.INSTALLED
            ),
            DependencyType.PYTHON: DependencyInfo(
                name="Python", type=DependencyType.PYTHON, status=DependencyStatus.INSTALLED
            )
        }

        summary = self.reporter.analyze_dependencies(dependencies)

        self.assertEqual(summary.total_dependencies, 2)
        self.assertEqual(summary.installed_count, 2)
        self.assertEqual(summary.missing_count, 0)
        self.assertEqual(summary.version_mismatch_count, 0)

    def test_analyze_dependencies_with_issues(self):
        """Test analyzing dependencies with issues"""
        dependencies = {
            DependencyType.NODEJS: DependencyInfo(
                name="Node.js", type=DependencyType.NODEJS, status=DependencyStatus.NOT_INSTALLED
            ),
            DependencyType.PYTHON: DependencyInfo(
                name="Python", type=DependencyType.PYTHON, status=DependencyStatus.VERSION_MISMATCH
            ),
            DependencyType.GIT: DependencyInfo(
                name="Git", type=DependencyType.GIT, status=DependencyStatus.INSTALLED
            )
        }

        summary = self.reporter.analyze_dependencies(dependencies)

        self.assertEqual(summary.total_dependencies, 3)
        self.assertEqual(summary.installed_count, 1)
        self.assertEqual(summary.missing_count, 1)
        self.assertEqual(summary.version_mismatch_count, 1)
        self.assertEqual(len(summary.critical_issues), 2)

    def test_format_console_report(self):
        """Test formatting console report"""
        # Create mock report
        from datetime import datetime
        from core.dependency_checker import DependencyInfo, DependencyStatus
        from core.dependency_reporter import DependencyReportSummary, DependencyReport

        dependencies = {
            "nodejs": DependencyInfo(
                name="Node.js", type=DependencyType.NODEJS, status=DependencyStatus.INSTALLED
            )
        }

        summary = DependencyReportSummary(
            total_dependencies=1,
            installed_count=1,
            missing_count=0,
            version_mismatch_count=0,
            inaccessible_count=0,
            network_accessible=True,
            package_managers_accessible={},
            critical_issues=[],
            recommendations=["All dependencies are properly installed"]
        )

        report = DependencyReport(
            timestamp=datetime.now(),
            operating_system="Test OS",
            python_version="3.9.0",
            dependency_summary=summary,
            dependencies=dependencies
        )

        formatted = self.reporter.format_console_report(report)

        self.assertIn("DEPENDENCY CHECK REPORT", formatted)
        self.assertIn("Node.js", formatted)
        self.assertIn("SUMMARY", formatted)

    def test_export_report_json(self):
        """Test exporting report as JSON"""
        # Create a minimal mock report
        from datetime import datetime
        from core.dependency_reporter import DependencyReportSummary, DependencyReport

        summary = DependencyReportSummary(
            total_dependencies=0,
            installed_count=0,
            missing_count=0,
            version_mismatch_count=0,
            inaccessible_count=0,
            network_accessible=False,
            package_managers_accessible={},
            critical_issues=[],
            recommendations=[]
        )

        report = DependencyReport(
            timestamp=datetime.now(),
            operating_system="Test OS",
            python_version="3.9.0",
            dependency_summary=summary,
            dependencies={}
        )

        json_str = self.reporter.format_json_report(report)
        parsed = json.loads(json_str)

        self.assertEqual(parsed["operating_system"], "Test OS")
        self.assertEqual(parsed["python_version"], "3.9.0")


class TestEnvironmentChecker(unittest.TestCase):
    """Test integrated environment checking functionality"""

    def setUp(self):
        """Set up test fixtures"""
        self.checker = EnvironmentChecker()

    @patch('core.environment_checker.OperatingSystemDetector')
    @patch('core.environment_checker.DependencyChecker')
    @patch('core.environment_checker.NetworkChecker')
    async def test_check_environment_success(self, mock_network_checker_class,
                                           mock_dependency_checker_class,
                                           mock_os_detector_class):
        """Test successful environment check"""
        # Mock OS detection
        mock_os_detector = MagicMock()
        mock_os_detector_class.return_value = mock_os_detector
        mock_os_info = MagicMock()
        mock_os_info.os_type.value = "linux"
        mock_os_info.version = "20.04"
        mock_os_info.is_supported = True
        mock_os_detector.detect_system.return_value = mock_os_info

        # Mock dependency checking
        mock_dependency_checker = MagicMock()
        mock_dependency_checker_class.return_value = mock_dependency_checker
        mock_dependencies = {}
        mock_dependency_checker.check_all_dependencies.return_value = mock_dependencies

        # Mock network checking
        mock_network_checker = MagicMock()
        mock_network_checker_class.return_value = mock_network_checker
        mock_network_info = MagicMock()
        mock_network_info.internet_connected = True
        mock_network_checker.get_comprehensive_network_info.return_value = mock_network_info

        # Run the check
        result = await self.checker.check_environment()

        # Verify results
        self.assertIsNotNone(result)
        self.assertEqual(result.os_info, mock_os_info)
        self.assertIsNotNone(result.dependency_report)

    def test_check_quick_dependency_status(self):
        """Test quick dependency status check"""
        # Mock OS detection
        with patch('core.environment_checker.OperatingSystemDetector') as mock_os_detector_class:
            mock_os_detector = MagicMock()
            mock_os_detector_class.return_value = mock_os_detector
            mock_os_info = MagicMock()
            mock_os_info.os_type.value = "linux"
            mock_os_info.version = "20.04"
            mock_os_detector.detect_system.return_value = mock_os_info

            # Mock dependency checking
            with patch('core.environment_checker.DependencyChecker') as mock_dep_checker_class:
                mock_dep_checker = MagicMock()
                mock_dep_checker_class.return_value = mock_dep_checker
                mock_dependencies = {
                    DependencyType.NODEJS: MagicMock(status=DependencyStatus.INSTALLED)
                }
                mock_dep_checker.check_all_dependencies.return_value = mock_dependencies

                result = self.checker.check_quick_dependency_status()

                self.assertIn("os_type", result)
                self.assertIn("dependencies", result)
                self.assertIn("all_installed", result)


if __name__ == '__main__':
    # Create test suite
    test_suite = unittest.TestSuite()

    # Add test cases
    test_classes = [
        TestVersionInfo,
        TestVersionComparator,
        TestDependencyChecker,
        TestNetworkChecker,
        TestDependencyReporter,
        TestEnvironmentChecker
    ]

    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)

    # Print summary
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print(f"{'='*60}")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")

    if result.failures:
        print(f"\nFAILURES:")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback.split('AssertionError:')[-1].strip()}")

    if result.errors:
        print(f"\nERRORS:")
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback.split('Exception:')[-1].strip()}")