#!/usr/bin/env python3
"""
Dependency Conflict Detector Test Suite

Tests for dependency version conflict detection, compatibility validation,
resolution generation, and automated fixes.
"""

import asyncio
import unittest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import sys
import os
import tempfile
import json

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.dependency_conflict_detector import (
    DependencyConflictDetector, DependencyType, ConflictSeverity, ResolutionType,
    DependencyInfo, VersionConflict, DependencyResolution, DependencyAnalysisResult
)
from utils.progress_tracker import ProgressTracker


class TestDependencyConflictDetector(unittest.TestCase):
    """Dependency Conflict Detector Core Tests"""

    def setUp(self):
        """Set up test fixtures"""
        self.progress_tracker = Mock(spec=ProgressTracker)
        self.progress_tracker._log = Mock()
        self.detector = DependencyConflictDetector(self.progress_tracker)

    def test_initialization(self):
        """Test DependencyConflictDetector initialization"""
        self.assertEqual(self.detector.platform, os.sys.platform.lower())
        self.assertIsNotNone(self.detector.executor)

    def test_parse_requirement_line(self):
        """Test requirement line parsing"""
        # Test exact version
        result = self.detector._parse_requirement_line("requests==2.28.1")
        self.assertIsNotNone(result)
        self.assertEqual(result.name, "requests")
        self.assertEqual(result.required_version, "==2.28.1")
        self.assertEqual(result.dependency_type, DependencyType.PYTHON_PIP)

        # Test version range
        result = self.detector._parse_requirement("numpy>=1.20.0,<2.0.0")
        self.assertIsNotNone(result)
        self.assertEqual(result.name, "numpy")
        self.assertEqual(result.required_version, ">=1.20.0,<2.0.0")

        # Test no version
        result = self.detector._parse_requirement("pandas")
        self.assertIsNotNone(result)
        self.assertEqual(result.name, "pandas")
        self.assertIsNone(result.required_version)

    def test_version_comparison(self):
        """Test version comparison functions"""
        # Test exact matches
        self.assertTrue(self.detector._compare_versions("1.2.3", "1.2.3", "=="))
        self.assertFalse(self.detector._compare_versions("1.2.3", "1.2.4", "=="))

        # Test greater than or equal
        self.assertTrue(self.detector._compare_versions("1.2.4", "1.2.3", ">="))
        self.assertFalse(self.detector._compare_versions("1.2.2", "1.2.3", ">="))

        # Test less than
        self.assertTrue(self.detector._compare_versions("1.2.2", "1.2.3", "<"))
        self.assertFalse(self.detector._compare_versions("1.2.4", "1.2.3", "<"))

    def test_simple_version_check(self):
        """Test simple version checking"""
        # Test compatible version (~=)
        self.assertTrue(self.detector._simple_version_check("1.2.4", "1.2.3", "compatible"))
        self.assertFalse(self.detector._simple_version_check("1.3.0", "1.2.3", "compatible"))

        # Test caret version (^)
        self.assertTrue(self.detector._simple_version_check("1.2.4", "1.2.3", "caret"))
        self.assertFalse(self.detector._simple_version_check("2.0.0", "1.2.3", "caret"))

    @patch('builtins.open')
    def test_parse_requirements_file(self, mock_open):
        """Test requirements.txt file parsing"""
        requirements_content = """
fastapi==0.111.0
uvicorn[standard]==0.29.0
requests>=2.28.0
pytest>=7.0.0,<8.0.0
# This is a comment
numpy>=1.20.0
"""

        mock_file = MagicMock()
        mock_file.__enter__.return_value = mock_file
        mock_file.__exit__.return_value = None
        mock_file.readlines.return_value = requirements_content.split('\n')
        mock_open.return_value = mock_file

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        dependencies = loop.run_until_complete(self.detector._parse_requirements_file("fake_path"))
        loop.close()

        self.assertEqual(len(dependencies), 4)
        self.assertEqual(dependencies[0].name, "fastapi")
        self.assertEqual(dependencies[0].required_version, "==0.111.0")
        self.assertEqual(dependencies[3].name, "numpy")
        self.assertEqual(dependencies[3].required_version, ">=1.20.0")

    @patch('builtins.open')
    def test_parse_package_json(self, mock_open):
        """Test package.json file parsing"""
        package_json_content = {
            "name": "test-project",
            "dependencies": {
                "express": "^4.18.0",
                "mongoose": "^7.0.0"
            },
            "devDependencies": {
                "jest": "^29.0.0",
                "eslint": "^8.0.0"
            }
        }

        mock_file = MagicMock()
        mock_file.__enter__.return_value = mock_file
        mock_file.__exit__.return_value = None
        mock_file.read.return_value = json.dumps(package_json_content)
        mock_open.return_value = mock_file

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        dependencies = loop.run_until_complete(self.detector._parse_package_json("fake_path"))
        loop.close()

        self.assertEqual(len(dependencies), 4)
        self.assertEqual(dependencies[0].name, "express")
        self.assertEqual(dependencies[0].required_version, "^4.18.0")
        self.assertEqual(dependencies[2].name, "jest")
        self.assertEqual(dependencies[2].metadata.get('package_type'), "devDependency")

    @patch('importlib.metadata.version')
    def test_check_python_package_installed(self, mock_version):
        """Test Python package installation checking"""
        # Test installed package
        mock_version.return_value = "1.2.3"

        dep = DependencyInfo(name="requests", dependency_type=DependencyType.PYTHON_PIP)
        self.detector._check_python_package(dep)

        self.assertTrue(dep.installed)
        self.assertEqual(dep.current_version, "1.2.3")

        # Test missing package
        mock_version.side_effect = Exception("Package not found")

        dep = DependencyInfo(name="nonexistent", dependency_type=DependencyType.PYTHON_PIP)
        self.detector._check_python_package(dep)

        self.assertFalse(dep.installed)

    @patch('subprocess.run')
    def test_check_node_package_installed(self, mock_run):
        """Test Node.js package installation checking"""
        # Test installed package
        mock_run.return_value = Mock(
            returncode=0,
            stdout='{"dependencies": {"express": {"version": "4.18.0"}}}',
            stderr=""
        )

        dep = DependencyInfo(name="express", dependency_type=DependencyType.NODE_NPM)
        self.detector._check_node_package(dep)

        self.assertTrue(dep.installed)
        self.assertEqual(dep.current_version, "4.18.0")

        # Test missing package
        mock_run.return_value = Mock(returncode=1, stderr="", stdout="")

        dep = DependencyInfo(name="nonexistent", dependency_type=DependencyType.NODE_NPM)
        self.detector._check_node_package(dep)

        self.assertFalse(dep.installed)

    def test_assess_conflict_severity(self):
        """Test conflict severity assessment"""
        # Test critical package
        dep = DependencyInfo(name="django", dependency_type=DependencyType.PYTHON_PIP)
        severity = self.detector._assess_conflict_severity(dep)
        self.assertEqual(severity, ConflictSeverity.CRITICAL)

        # Test dev dependency
        dep = DependencyInfo(
            name="eslint",
            dependency_type=DependencyType.NODE_NPM,
            metadata={'package_type': 'devDependency'}
        )
        severity = self.detector._assess_conflict_severity(dep)
        self.assertEqual(severity, ConflictSeverity.LOW)

    def test_get_install_command(self):
        """Test install command generation"""
        # Test Python package
        dep = DependencyInfo(
            name="requests",
            required_version="==2.28.1",
            dependency_type=DependencyType.PYTHON_PIP
        )
        command = self.detector._get_install_command(dep)
        self.assertEqual(command, "pip install requests==2.28.1")

        # Test Node.js package
        dep = DependencyInfo(
            name="express",
            required_version="^4.18.0",
            dependency_type=DependencyType.NODE_NPM
        )
        command = self.detector._get_install_command(dep)
        self.assertEqual(command, "npm install express@^4.18.0")

    def test_get_upgrade_command(self):
        """Test upgrade command generation"""
        dep = DependencyInfo(
            name="fastapi",
            current_version="0.110.0",
            dependency_type=DependencyType.PYTHON_PIP
        )
        command = self.detector._get_upgrade_command(dep, "0.111.0")
        self.assertEqual(command, "pip install --upgrade fastapi==0.111.0")

    def test_get_downgrade_command(self):
        """Test downgrade command generation"""
        dep = DependencyInfo(
            name="fastapi",
            current_version="0.115.0",
            dependency_type=DependencyType.PYTHON_PIP
        )
        command = self.detector._get_downgrade_command(dep, "0.111.0")
        self.assertEqual(command, "pip install fastapi==0.111.0")

    def test_get_reinstall_command(self):
        """Test reinstall command generation"""
        # Test Python package
        dep = DependencyInfo(
            name="requests",
            current_version="2.28.1",
            dependency_type=DependencyType.PYTHON_PIP
        )
        command = self.detector._get_reinstall_command(dep)
        self.assertEqual(command, "pip uninstall requests -y && pip install requests==2.28.1")

        # Test Node.js package
        dep = DependencyInfo(
            name="express",
            dependency_type=DependencyType.NODE_NPM
        )
        command = self.detector._get_reinstall_command(dep)
        self.assertEqual(command, "npm uninstall express && npm install express")


class TestDependencyConflictAnalysis(unittest.TestCase):
    """Dependency Conflict Analysis Tests"""

    def setUp(self):
        """Set up test fixtures"""
        self.progress_tracker = Mock(spec=ProgressTracker)
        self.progress_tracker._log = Mock()
        self.detector = DependencyConflictDetector(self.progress_tracker)

    @patch.object(DependencyConflictDetector, '_scan_project_dependencies')
    @patch.object(DependencyConflictDetector, '_check_installation_status')
    @patch.object(DependencyConflictDetector, '_detect_version_conflicts')
    @patch.object(DependencyConflictDetector, '_generate_resolutions')
    async def test_analyze_dependencies(self, mock_generate_resolutions, mock_detect_conflicts,
                                          mock_check_status, mock_scan):
        """Test comprehensive dependency analysis"""
        # Setup mock dependencies
        mock_deps = [
            DependencyInfo(name="fastapi", required_version="==0.111.0", installed=True, current_version="0.115.14"),
            DependencyInfo(name="uvicorn", required_version="==0.29.0", installed=True, current_version="0.34.3")
        ]
        mock_scan.return_value = mock_deps

        # Setup mock conflicts
        mock_conflicts = [
            VersionConflict(
                dependency_name="fastapi",
                dependency_type=DependencyType.PYTHON_PIP,
                current_version="0.115.14",
                required_version="==0.111.0",
                conflict_type="version_mismatch",
                severity=ConflictSeverity.MEDIUM,
                description="Version conflict"
            )
        ]
        mock_detect_conflicts.return_value = mock_conflicts

        # Setup mock resolutions
        mock_resolutions = [
            DependencyResolution(
                conflict=mock_conflicts[0],
                resolution_type=ResolutionType.DOWNGRADE,
                target_version="0.111.0",
                command="pip install fastapi==0.111.0",
                description="Downgrade fastapi",
                automated=True
            )
        ]
        mock_generate_resolutions.return_value = mock_resolutions

        # Run analysis
        result = await self.detector.analyze_dependencies()

        # Verify results
        self.assertIsInstance(result, DependencyAnalysisResult)
        self.assertEqual(result.total_dependencies, 2)
        self.assertEqual(result.compatible_dependencies, 0)
        self.assertEqual(result.conflicting_dependencies, 2)
        self.assertEqual(result.missing_dependencies, 0)
        self.assertEqual(len(result.conflicts), 1)
        self.assertEqual(len(result.resolutions), 1)
        self.assertGreater(len(result.recommendations), 0)

    def test_generate_version_resolution_options(self):
        """Test version resolution option generation"""
        # Test upgrade scenario
        dep = DependencyInfo(
            name="requests",
            current_version="2.27.0",
            required_version=">=2.28.0",
            dependency_type=DependencyType.PYTHON_PIP
        )
        options = self.detector._generate_version_resolution_options(dep)

        self.assertGreater(len(options), 0)
        self.assertTrue(any(opt["type"] == "upgrade" for opt in options))

        # Test downgrade scenario
        dep = DependencyInfo(
            name="requests",
            current_version="2.29.0",
            required_version="==2.28.0",
            dependency_type=DependencyType.PYTHON_PIP
        )
        options = self.detector._generate_version_resolution_options(dep)

        self.assertGreater(len(options), 0)
        self.assertTrue(any(opt["type"] == "downgrade" for opt in options))

    def test_check_version_compatibility(self):
        """Test version compatibility checking"""
        # Test exact match
        compatible = self.detector._check_version_compatibility("1.2.3", "==1.2.3")
        self.assertTrue(compatible)

        # Test version range
        compatible = self.detector._check_version_compatibility("1.2.4", ">=1.2.0,<2.0.0")
        self.assertTrue(compatible)

        # Test caret version
        compatible = self.detector._check_version_compatibility("1.2.4", "^1.2.0")
        self.assertTrue(compatible)

        # Test compatible version
        compatible = self.detector._check_version_compatibility("1.2.4", "~=1.2.0")
        self.assertTrue(compatible)

        # Test incompatible
        compatible = self.detector._check_version_compatibility("2.0.0", "^1.2.0")
        self.assertFalse(compatible)

    def test_select_best_resolution_option(self):
        """Test best resolution option selection"""
        conflict = VersionConflict(
            dependency_name="test",
            dependency_type=DependencyType.PYTHON_PIP,
            current_version="1.0.0",
            required_version="2.0.0",
            conflict_type="version_mismatch",
            severity=ConflictSeverity.MEDIUM,
            description="Test conflict"
        )

        # Create resolution options with different priorities
        conflict.resolution_options = [
            {"type": "remove_conflict", "command": "remove test", "description": "Remove"},
            {"type": "upgrade", "command": "upgrade test", "description": "Upgrade", "automated": True},
            {"type": "reinstall", "command": "reinstall test", "description": "Reinstall"}
        ]

        best_option = self.detector._select_best_resolution_option(conflict)
        self.assertIsNotNone(best_option)
        self.assertEqual(best_option["type"], "upgrade")

    def test_generate_recommendations(self):
        """Test recommendation generation"""
        result = DependencyAnalysisResult(
            timestamp="2024-01-01T00:00:00",
            total_dependencies=10,
            compatible_dependencies=8,
            conflicting_dependencies=2,
            missing_dependencies=0,
            conflicts=[]
        )

        recommendations = self.detector._generate_recommendations(result)
        self.assertGreater(len(recommendations), 0)

    def test_generate_summary(self):
        """Test summary generation"""
        result = DependencyAnalysisResult(
            timestamp="2024-01-01T00:00:00",
            total_dependencies=10,
            compatible_dependencies=8,
            conflicting_dependencies=2,
            missing_dependencies=0,
            conflicts=[],
            resolutions=[]
        )

        summary = self.detector._generate_summary(result)

        self.assertEqual(summary['total_packages'], 10)
        self.assertEqual(summary['compatible_packages'], 8)
        self.assertEqualsummary['conflicting_packages'], 2)
        self.assertEqual(summary['missing_packages'], 0)
        self.assertEqual(summary['dependency_health'], 'needs_attention')


class TestDependencyConflictIntegration(unittest.TestCase):
    """Dependency Conflict Integration Tests"""

    def test_quick_dependency_check(self):
        """Test quick dependency check"""
        with patch.object(DependencyConflictDetector, 'analyze_dependencies') as mock_analyze:
            mock_result = DependencyAnalysisResult(
                timestamp="2024-01-01T00:00:00",
                total_dependencies=5,
                compatible_dependencies=5,
                conflicting_dependencies=0,
                missing_dependencies=0
            )
            mock_analyze.return_value = mock_result

            loop = asyncio.new_event_loop()
            result = loop.run_until_complete(quick_dependency_check())
            loop.close()

            self.assertIsInstance(result, DependencyAnalysisResult)
            self.assertEqual(result.total_dependencies, 5)

    def test_fix_common_issues(self):
        """Test common issues fixing"""
        with patch.object(DependencyConflictDetector, 'analyze_dependencies') as mock_analyze, \
             patch.object(DependencyConflictDetector, 'apply_resolution') as mock_apply:

            # Setup mock analysis result
            conflict = VersionConflict(
                dependency_name="critical-package",
                dependency_type=DependencyType.PYTHON_PIP,
                current_version="1.0.0",
                required_version="2.0.0",
                conflict_type="version_mismatch",
                severity=ConflictSeverity.HIGH,
                description="Critical version conflict"
            )
            resolution = DependencyResolution(
                conflict=conflict,
                resolution_type=ResolutionType.UPGRADE,
                target_version="2.0.0",
                command="pip install critical-package==2.0.0",
                description="Upgrade critical-package",
                automated=True
            )

            mock_result = DependencyAnalysisResult(
                timestamp="2024-01-01T00:00:00",
                total_dependencies=1,
                compatible_dependencies=0,
                conflicting_dependencies=1,
                missing_dependencies=0,
                conflicts=[conflict],
                resolutions=[resolution]
            )
            mock_analyze.return_value = mock_result
            mock_apply.return_value = True

            loop = asyncio.new_event_loop()
            results = loop.run_until_complete(fix_common_issues())
            loop.close()

            self.assertEqual(len(results), 1)
            self.assertTrue(results[0])


class TestDependencyConflictErrorHandling(unittest.TestCase):
    """Dependency Conflict Error Handling Tests"""

    def test_async_context_manager(self):
        """Test async context manager"""
        async def test_context_manager():
            async with DependencyConflictDetector() as detector:
                self.assertIsNotNone(detector)
                return detector

        loop = asyncio.new_event_loop()
        detector = loop.run_until_complete(test_context_manager())
        loop.close()

        self.assertIsNotNone(detector)

    def test_file_not_found_handling(self):
        """Test file not found error handling"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Test requirements.txt not found
        dependencies = loop.run_until_complete(self.detector._parse_requirements_file("nonexistent.txt"))
        self.assertEqual(len(dependencies), 0)

        loop.close()

    def test_invalid_json_handling(self):
        """Test invalid JSON error handling"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Test invalid package.json
        with patch('builtins.open') as mock_open:
            mock_file = MagicMock()
            mock_file.__enter__.return_value = mock_file
            mock_file.__exit__.return_value = None
            mock_file.read.return_value = "invalid json"
            mock_open.return_value = mock_file

            dependencies = loop.run_until_complete(self.detector._parse_package_json("fake_path"))
            self.assertEqual(len(dependencies), 0)

        loop.close()

    def test_package_import_error_handling(self):
        """Test package import error handling"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Test importlib.metadata.PackageNotFoundError
        with patch('importlib.metadata.version') as mock_version:
            mock_version.side_effect = Exception("Package not found")

            dep = DependencyInfo(name="nonexistent", dependency_type=DependencyType.PYTHON_PIP)
            self.detector._check_python_package(dep)

            self.assertFalse(dep.installed)

        loop.close()

    def test_subprocess_timeout_handling(self):
        """Test subprocess timeout error handling"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Test subprocess.TimeoutExpired
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired('npm list', 30)

            dep = DependencyInfo(name="slow-package", dependency_type=DependencyType.NODE_NPM)
            self.detector._check_node_package(dep)

            self.assertFalse(dep.installed)

        loop.close()


if __name__ == '__main__':
    # Create test suite
    suite = unittest.TestSuite()

    # Add test cases
    suite.addTest(unittest.makeSuite(TestDependencyConflictDetector))
    suite.addTest(unittest.makeSuite(TestDependencyConflictAnalysis))
    suite.addTest(unittest.makeSuite(TestDependencyConflictIntegration))
    suite.addTest(unittest.makeSuite(TestDependencyConflictErrorHandling))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1)