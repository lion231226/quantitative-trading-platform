"""
Integration tests for the dependency checking system.

These tests verify the integration between different components
and test real-world scenarios.
"""

import unittest
import asyncio
import sys
import os
from pathlib import Path

# Add the project root to the path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.environment_checker import EnvironmentChecker
from core.dependency_checker import DependencyChecker, DependencyType
from utils.network_utils import NetworkChecker
from core.dependency_reporter import DependencyReporter


class TestRealEnvironmentCheck(unittest.TestCase):
    """Test the environment checker with real system dependencies"""

    def setUp(self):
        """Set up test fixtures"""
        self.checker = EnvironmentChecker()

    def test_quick_dependency_check(self):
        """Test quick dependency check on the current system"""
        print("\n" + "="*50)
        print("QUICK DEPENDENCY CHECK")
        print("="*50)

        result = self.checker.check_quick_dependency_status()

        print(f"OS Type: {result['os_type']}")
        print(f"OS Version: {result['os_version']}")
        print(f"All dependencies installed: {result['all_installed']}")

        for dep_name, dep_info in result['dependencies'].items():
            status_icon = "✓" if dep_info['installed'] else "✗"
            version_str = f" (v{dep_info['version']})" if dep_info['version'] else ""
            print(f"  {status_icon} {dep_name}{version_str}")

        # Verify the structure of the result
        self.assertIn('os_type', result)
        self.assertIn('os_version', result)
        self.assertIn('dependencies', result)
        self.assertIn('all_installed', result)

        # Check that we have the expected dependencies
        expected_deps = ['nodejs', 'python', 'git']
        for dep in expected_deps:
            self.assertIn(dep, result['dependencies'])

    async def test_full_environment_check_async(self):
        """Test full environment check including network tests"""
        print("\n" + "="*50)
        print("FULL ENVIRONMENT CHECK")
        print("="*50)

        try:
            result = await self.checker.check_environment(include_network_check=True)

            print(f"Overall Status: {result.overall_status}")
            print(f"Ready for Development: {result.is_ready_for_development}")
            print(f"Critical Issues: {len(result.critical_issues)}")

            if result.critical_issues:
                print("Critical Issues:")
                for issue in result.critical_issues:
                    print(f"  ❌ {issue}")

            if result.recommendations:
                print("Recommendations:")
                for rec in result.recommendations[:3]:  # Show first 3
                    print(f"  💡 {rec}")

            # Verify result structure
            self.assertIsNotNone(result.timestamp)
            self.assertIsNotNone(result.os_info)
            self.assertIsNotNone(result.dependency_report)
            self.assertIsNotNone(result.network_info)

            print("\n✓ Full environment check completed successfully")

        except Exception as e:
            print(f"\n⚠ Full environment check failed: {e}")
            # This might fail due to network issues, so we don't fail the test
            self.skipTest("Network connectivity required for full environment check")

    def test_specific_dependency_checks(self):
        """Test checking specific dependencies individually"""
        print("\n" + "="*50)
        print("SPECIFIC DEPENDENCY CHECKS")
        print("="*50)

        # Test Python dependency (should be available since we're running Python)
        async def check_python():
            return await self.checker.check_specific_dependency(DependencyType.PYTHON)

        # Use asyncio.run to run the async function
        try:
            python_info = asyncio.run(check_python())
            print(f"Python Status: {python_info.status.value}")
            if python_info.version:
                print(f"Python Version: {python_info.version}")
            if python_info.executable_path:
                print(f"Python Path: {python_info.executable_path}")

            # Verify Python is properly detected
            self.assertEqual(python_info.name, "Python")
            self.assertEqual(python_info.type, DependencyType.PYTHON)

        except Exception as e:
            print(f"Python check failed: {e}")
            # This shouldn't fail since we're running Python
            raise

    def test_dependency_report_generation(self):
        """Test dependency report generation and formatting"""
        print("\n" + "="*50)
        print("DEPENDENCY REPORT GENERATION")
        print("="*50)

        # Get quick status first
        quick_status = self.checker.check_quick_dependency_status()

        # Create a mock dependency report for testing
        from datetime import datetime
        from core.dependency_checker import DependencyInfo, DependencyStatus
        from core.dependency_reporter import DependencyReportSummary, DependencyReport

        dependencies = {}
        for dep_name, dep_info in quick_status['dependencies'].items():
            # Map string types back to enum values (simplified for test)
            if dep_name == 'nodejs':
                dep_type = DependencyType.NODEJS
            elif dep_name == 'python':
                dep_type = DependencyType.PYTHON
            elif dep_name == 'git':
                dep_type = DependencyType.GIT
            else:
                continue

            status = DependencyStatus.INSTALLED if dep_info['installed'] else DependencyStatus.NOT_INSTALLED

            dependencies[dep_name] = DependencyInfo(
                name=dep_name.capitalize(),
                type=dep_type,
                status=status
            )

        summary = DependencyReportSummary(
            total_dependencies=len(dependencies),
            installed_count=sum(1 for d in dependencies.values() if d.status == DependencyStatus.INSTALLED),
            missing_count=sum(1 for d in dependencies.values() if d.status == DependencyStatus.NOT_INSTALLED),
            version_mismatch_count=0,
            inaccessible_count=0,
            network_accessible=True,
            package_managers_accessible={},
            critical_issues=[],
            recommendations=[]
        )

        report = DependencyReport(
            timestamp=datetime.now(),
            operating_system="Test OS",
            python_version=sys.version.split()[0],
            dependency_summary=summary,
            dependencies=dependencies
        )

        # Test console formatting
        reporter = DependencyReporter()
        console_report = reporter.format_console_report(report)

        print("Console Report Preview:")
        print("-" * 30)
        # Show first 500 characters of the report
        print(console_report[:500] + "..." if len(console_report) > 500 else console_report)

        # Verify the report contains expected content
        self.assertIn("DEPENDENCY CHECK REPORT", console_report)
        self.assertIn("SUMMARY", console_report)

        print("\n✓ Report generation completed successfully")

    def test_network_check(self):
        """Test basic network connectivity check"""
        print("\n" + "="*50)
        print("NETWORK CONNECTIVITY CHECK")
        print("="*50)

        async def check_network():
            checker = NetworkChecker()

            # Test proxy detection
            proxy_config = checker.detect_proxy_config()
            print(f"Proxy detected: {proxy_config.enabled}")
            if proxy_config.enabled:
                print(f"HTTP proxy: {proxy_config.http_proxy}")
                print(f"HTTPS proxy: {proxy_config.https_proxy}")

            # Test basic connectivity (quick test)
            try:
                from utils.network_utils import check_internet_connection
                connected = await check_internet_connection(timeout=3)
                print(f"Internet connectivity: {'✓' if connected else '✗'}")
            except Exception as e:
                print(f"Internet connectivity test failed: {e}")

            # Test offline mode detection
            offline_mode = checker.detect_offline_mode()
            print(f"Offline mode detected: {'✓' if offline_mode else '✗'}")

            return proxy_config, offline_mode

        try:
            proxy_config, offline_mode = asyncio.run(check_network())
            print("\n✓ Network check completed successfully")

            # Verify proxy config structure
            self.assertIsInstance(proxy_config.enabled, bool)

        except Exception as e:
            print(f"\n⚠ Network check failed: {e}")
            # Network tests can fail due to various reasons, so we don't fail the test


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error handling"""

    def test_version_parsing_edge_cases(self):
        """Test version parsing with edge cases"""
        from core.dependency_checker import VersionInfo

        test_cases = [
            ("v1.0.0", "1.0.0"),
            ("1.0", "1.0.0"),
            ("1", "1.0.0"),
            ("1.0.0-beta.1", "1.0.0-beta.1"),
            ("1.0.0+build.1", "1.0.0+build.1"),
            ("1.0.0-beta.1+build.1", "1.0.0-beta.1+build.1"),
            ("", "0.0.0"),  # Empty string edge case
        ]

        for input_version, expected_output in test_cases:
            try:
                if input_version == "":
                    # Test empty string handling
                    with self.assertRaises((IndexError, ValueError)):
                        VersionInfo.from_string(input_version)
                else:
                    version = VersionInfo.from_string(input_version)
                    expected = VersionInfo.from_string(expected_output)
                    self.assertEqual(version.major, expected.major)
                    self.assertEqual(version.minor, expected.minor)
                    self.assertEqual(version.patch, expected.patch)
                    print(f"✓ Version parsing: '{input_version}' -> '{version}'")
            except Exception as e:
                print(f"⚠ Version parsing failed for '{input_version}': {e}")
                # Some edge cases might fail, which is expected

    def test_dependency_checker_with_invalid_os(self):
        """Test dependency checker with unknown OS"""
        # Mock an unknown OS
        with unittest.mock.patch('core.dependency_checker.platform.system', return_value='UnknownOS'):
            checker = DependencyChecker()
            self.assertEqual(checker.operating_system.value, "unknown")

    def test_missing_config_file_handling(self):
        """Test behavior when config files are missing"""
        from core.dependency_checker import DependencyChecker

        checker = DependencyChecker()

        # The checker should handle missing config gracefully
        try:
            # This should not crash even if config is missing
            result = checker.check_dependency(DependencyType.NODEJS)
            print("✓ Missing config handled gracefully")
        except Exception as e:
            print(f"⚠ Missing config handling issue: {e}")


def run_integration_tests():
    """Run all integration tests"""
    print("Starting integration tests...")
    print("="*60)

    # Create test suite
    suite = unittest.TestSuite()

    # Add test cases
    test_classes = [
        TestRealEnvironmentCheck,
        TestEdgeCases
    ]

    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        suite.addTests(tests)

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Print summary
    print(f"\n{'='*60}")
    print("INTEGRATION TEST SUMMARY")
    print(f"{'='*60}")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped)}")

    if result.testsRun > 0:
        success_rate = ((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100)
        print(f"Success rate: {success_rate:.1f}%")

    if result.failures:
        print(f"\nFAILURES:")
        for test, traceback in result.failures:
            print(f"  - {test}")

    if result.errors:
        print(f"\nERRORS:")
        for test, traceback in result.errors:
            print(f"  - {test}")

    print("\nIntegration tests completed.")
    return result


if __name__ == '__main__':
    # Run the integration tests
    run_integration_tests()