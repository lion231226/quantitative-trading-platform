"""
Test suite for intelligent error detection and diagnosis module.

This test suite validates the functionality of port conflict detection,
permission issue diagnosis, network connectivity checking, dependency
conflict detection, and error classification.
"""

import pytest
import asyncio
import socket
import tempfile
import os
import json
from unittest.mock import Mock, patch, AsyncMock
from typing import List, Dict, Any

# Import modules to test
from core.error_detector import (
    ErrorDetector, ErrorInfo, PortConflictError, PermissionError,
    ErrorSeverity, ErrorRecoveryType
)
from core.port_detector import (
    PortConflictResolver, PortConflict, ResolutionStrategy, ResolutionResult
)
from utils.error_knowledge_base import (
    ErrorKnowledgeBase, ErrorCategory, Platform, ErrorSolution
)
from core.port_checker import PortCheckResult, PortStatus


class TestErrorDetector:
    """Test cases for ErrorDetector class"""

    @pytest.fixture
    def error_detector(self):
        """Create ErrorDetector instance for testing"""
        return ErrorDetector()

    @pytest.fixture
    def mock_port_checker(self):
        """Create mock port checker"""
        mock_checker = Mock()
        mock_checker.check_port_availability = AsyncMock()
        return mock_checker

    @pytest.fixture
    def sample_port_conflict(self):
        """Create sample port conflict for testing"""
        return PortConflictError(
            port=3000,
            host="localhost",
            process_info={
                "pid": 1234,
                "name": "node",
                "command_line": "node server.js",
                "user": "testuser"
            },
            alternative_ports=[3001, 3002],
            service_type="Frontend Dev Server",
            resolution_steps=[
                "Stop the conflicting process 'node' (PID: 1234)",
                "Use alternative port: 3001",
                "Configure application to use port 3001"
            ]
        )

    @pytest.mark.asyncio
    async def test_detect_port_conflicts_with_available_ports(self, error_detector, mock_port_checker):
        """Test port conflict detection when all ports are available"""
        # Mock port checker responses for available ports
        mock_port_checker.check_port_availability.side_effect = [
            PortCheckResult(port=3000, host="localhost", status=PortStatus.AVAILABLE, is_available=True),
            PortCheckResult(port=8000, host="localhost", status=PortStatus.AVAILABLE, is_available=True),
            PortCheckResult(port=5432, host="localhost", status=PortStatus.AVAILABLE, is_available=True)
        ]

        # Replace the port checker with mock
        error_detector.port_checker = mock_port_checker

        # Test detection
        conflicts = await error_detector.detect_port_conflicts("localhost", [3000, 8000, 5432])

        # Verify no conflicts detected
        assert len(conflicts) == 0

        # Verify port checker was called for each port
        assert mock_port_checker.check_port_availability.call_count == 3

    @pytest.mark.asyncio
    async def test_detect_port_conflicts_with_occupied_ports(self, error_detector, mock_port_checker):
        """Test port conflict detection when ports are occupied"""
        # Mock port checker responses for occupied ports
        mock_port_checker.check_port_availability.side_effect = [
            PortCheckResult(
                port=3000,
                host="localhost",
                status=PortStatus.OCCUPIED,
                is_available=False,
                process_info={
                    "pid": 1234,
                    "name": "node",
                    "command_line": "node app.js"
                }
            ),
            PortCheckResult(
                port=8000,
                host="localhost",
                status=PortStatus.OCCUPIED,
                is_available=False,
                process_info={
                    "pid": 5678,
                    "name": "python",
                    "command_line": "python manage.py runserver"
                }
            )
        ]

        # Mock alternative port suggestions
        mock_port_checker.suggest_alternative_ports = AsyncMock(return_value=[3001, 3002])

        # Replace the port checker with mock
        error_detector.port_checker = mock_port_checker

        # Test detection
        conflicts = await error_detector.detect_port_conflicts("localhost", [3000, 8000])

        # Verify conflicts detected
        assert len(conflicts) == 2
        assert conflicts[0].port == 3000
        assert conflicts[0].service_type == "Frontend Dev Server"
        assert conflicts[1].port == 8000
        assert conflicts[1].service_type == "Backend API Server"

    @pytest.mark.asyncio
    async def test_detect_permission_issues_with_valid_paths(self, error_detector):
        """Test permission detection with valid accessible paths"""
        # Create temporary directory for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test with accessible paths
            paths = [temp_dir, os.path.dirname(temp_dir)]

            with patch('os.path.exists', return_value=True), \
                 patch('os.access', return_value=True), \
                 patch('platform.system', return_value='Linux'), \
                 patch.object(error_detector.permission_diagnostic, 'check_admin_privileges') as mock_admin:

                # Configure mock to return no admin privileges (simple mock)
                mock_result = type('MockResult', (), {
                    'has_admin': False,
                    'admin_required': False,
                    'current_user': 'testuser',
                    'platform': 'linux',
                    'has_permission': False,
                    'current_level': type('MockLevel', (), {'value': 'user'})(),
                    'required_level': type('MockLevel', (), {'value': 'admin'})(),
                    'suggestions': []
                })()
                mock_admin.return_value = mock_result

                issues = await error_detector.detect_permission_issues(paths)

                # Should detect no file-specific permission issues (may still detect system-level issues)
                file_permission_issues = [issue for issue in issues if hasattr(issue, 'resource_path') and issue.resource_path in paths]
                assert len(file_permission_issues) == 0

    @pytest.mark.asyncio
    async def test_detect_permission_issues_with_inaccessible_paths(self, error_detector):
        """Test permission detection with inaccessible paths"""
        # Test with inaccessible paths
        paths = ["/restricted/path", "/private/directory"]

        with patch('os.path.exists', return_value=True), \
             patch('os.access', side_effect=[False, True]), \
             patch('platform.system', return_value='Linux'), \
             patch.object(error_detector.permission_diagnostic, 'check_admin_privileges') as mock_admin, \
             patch.object(error_detector, '_get_current_user', return_value='testuser'):

                # Configure mock to return no admin privileges (simple mock)
                mock_result = type('MockResult', (), {
                    'has_admin': False,
                    'admin_required': False,
                    'current_user': 'testuser',
                    'platform': 'linux',
                    'has_permission': False,
                    'current_level': type('MockLevel', (), {'value': 'user'})(),
                    'required_level': type('MockLevel', (), {'value': 'admin'})(),
                    'suggestions': []
                })()
                mock_admin.return_value = mock_result

                issues = await error_detector.detect_permission_issues(paths)

                # Should detect at least one file-specific permission issue
                file_permission_issues = [issue for issue in issues if hasattr(issue, 'resource_path') and issue.resource_path in paths]
                assert len(file_permission_issues) >= 1
                restricted_path_issue = next((issue for issue in file_permission_issues if issue.resource_path == "/restricted/path"), None)
                assert restricted_path_issue is not None
                assert "read" in restricted_path_issue.required_permissions.lower() or "access" in restricted_path_issue.required_permissions.lower()

    def test_create_port_conflict_error(self, error_detector, sample_port_conflict):
        """Test creation of structured port conflict error"""
        error_info = error_detector.create_port_conflict_error(sample_port_conflict)

        # Verify error structure
        assert isinstance(error_info, ErrorInfo)
        assert error_info.code == "PORT_CONFLICT_3000"
        assert "Port 3000 is occupied" in error_info.message
        assert "node" in error_info.message
        assert error_info.severity == ErrorSeverity.HIGH
        assert error_info.recovery_type == ErrorRecoveryType.REQUIRES_USER_ACTION
        assert error_info.category == "port_conflict"
        assert "resolution options" in error_info.solution.lower()
        assert error_info.details["port"] == 3000
        assert error_info.details["process_info"]["name"] == "node"

    def test_create_permission_error(self, error_detector):
        """Test creation of structured permission error"""
        permission_error = PermissionError(
            resource_path="/test/path",
            required_permissions="write access",
            current_user="testuser",
            admin_required=True,
            platform_specific_guidance={
                "unix": "chmod +w /test/path",
                "windows": "Right-click → Properties → Security"
            }
        )

        error_info = error_detector.create_permission_error(permission_error)

        # Verify error structure
        assert isinstance(error_info, ErrorInfo)
        assert error_info.code == "PERMISSION_DENIED"
        assert "Permission denied for '/test/path'" in error_info.message
        assert "write access" in error_info.message
        assert error_info.severity == ErrorSeverity.HIGH
        assert error_info.recovery_type == ErrorRecoveryType.REQUIRES_ADMIN
        assert error_info.category == "permission"
        assert error_info.details["admin_required"] is True

    @pytest.mark.asyncio
    async def test_comprehensive_detection(self, error_detector):
        """Test comprehensive error detection across all categories"""
        # Mock individual detection methods
        port_conflicts = [PortConflictError(
            port=3000,
            host="localhost",
            process_info={"pid": 1234, "name": "node"},
            alternative_ports=[3001]
        )]

        permission_issues = [PermissionError(
            resource_path="/test/path",
            required_permissions="read access"
        )]

        with patch.object(error_detector, 'detect_port_conflicts', return_value=port_conflicts), \
             patch.object(error_detector, 'detect_permission_issues', return_value=permission_issues):

            results = await error_detector.run_comprehensive_detection("localhost", [3000], ["/test/path"])

            # Verify results structure
            assert "port_conflicts" in results
            assert "permission_issues" in results
            assert len(results["port_conflicts"]) == 1
            assert len(results["permission_issues"]) == 1
            assert isinstance(results["port_conflicts"][0], ErrorInfo)
            assert isinstance(results["permission_issues"][0], ErrorInfo)


class TestPortConflictResolver:
    """Test cases for PortConflictResolver class"""

    @pytest.fixture
    def resolver(self):
        """Create PortConflictResolver instance for testing"""
        return PortConflictResolver()

    @pytest.fixture
    def sample_conflict(self):
        """Create sample port conflict for testing"""
        return PortConflict(
            port=3000,
            host="localhost",
            process_info={"pid": 1234, "name": "node", "command_line": "node app.js"},
            service_type="node",
            severity="medium",
            resolution_options=[ResolutionStrategy.USE_ALTERNATIVE, ResolutionStrategy.STOP_PROCESS],
            alternative_ports=[3001, 3002]
        )

    @pytest.mark.asyncio
    async def test_detect_conflicts_no_conflicts(self, resolver):
        """Test conflict detection when no ports are occupied"""
        # Mock available ports
        with patch.object(resolver.port_checker, 'check_port_availability') as mock_check:
            mock_check.return_value = PortCheckResult(
                port=3000, host="localhost", status=PortStatus.AVAILABLE, is_available=True
            )

            conflicts = await resolver.detect_conflicts("localhost", [3000])

            # Should detect no conflicts
            assert len(conflicts) == 0

    @pytest.mark.asyncio
    async def test_detect_conflicts_with_occupied_port(self, resolver, sample_conflict):
        """Test conflict detection when port is occupied"""
        # Mock occupied port
        with patch.object(resolver.port_checker, 'check_port_availability') as mock_check, \
             patch.object(resolver, '_get_alternative_ports') as mock_alternatives:

            mock_check.return_value = PortCheckResult(
                port=3000,
                host="localhost",
                status=PortStatus.OCCUPIED,
                is_available=False,
                process_info={"pid": 1234, "name": "node"}
            )
            mock_alternatives.return_value = [3001, 3002]

            conflicts = await resolver.detect_conflicts("localhost", [3000])

            # Should detect conflict
            assert len(conflicts) == 1
            assert conflicts[0].port == 3000
            assert conflicts[0].service_type == "node"
            assert conflicts[0].severity == "medium"
            assert ResolutionStrategy.USE_ALTERNATIVE in conflicts[0].resolution_options

    @pytest.mark.asyncio
    async def test_resolve_conflict_with_alternative_port(self, resolver, sample_conflict):
        """Test conflict resolution using alternative port"""
        # Mock successful alternative port resolution
        with patch.object(resolver, '_resolve_with_alternative_port') as mock_resolve:
            mock_resolve.return_value = ResolutionResult(
                success=True,
                strategy_used=ResolutionStrategy.USE_ALTERNATIVE,
                resolved_port=3001,
                message="Use alternative port 3001",
                action_taken="Suggested port 3001",
                requires_user_action=True
            )

            result = await resolver.resolve_conflict(sample_conflict)

            # Verify successful resolution
            assert result.success is True
            assert result.strategy_used == ResolutionStrategy.USE_ALTERNATIVE
            assert result.resolved_port == 3001
            assert result.requires_user_action is True

    @pytest.mark.asyncio
    async def test_auto_resolve_all_conflicts(self, resolver):
        """Test automatic resolution of all conflicts"""
        # Mock conflicts and resolution
        conflicts = [
            PortConflict(
                port=3000,
                host="localhost",
                process_info=None,
                service_type="node",
                severity="medium",
                resolution_options=[ResolutionStrategy.USE_ALTERNATIVE],
                alternative_ports=[3001]
            )
        ]

        with patch.object(resolver, 'detect_conflicts', return_value=conflicts), \
             patch.object(resolver, 'resolve_conflict') as mock_resolve:

            mock_resolve.return_value = ResolutionResult(
                success=True,
                strategy_used=ResolutionStrategy.USE_ALTERNATIVE,
                resolved_port=3001,
                message="Use alternative port 3001",
                action_taken="Suggested port 3001"
            )

            result = await resolver.auto_resolve_all_conflicts("localhost", [3000])

            # Verify resolution results
            assert result["conflicts_detected"] == 1
            assert result["conflicts_resolved"] == 1
            assert result["conflicts_failed"] == 0
            assert len(result["resolutions"]) == 1
            assert result["resolutions"][0]["success"] is True
            assert result["resolutions"][0]["resolved_port"] == 3001

    def test_generate_resolution_report(self, resolver):
        """Test generation of resolution report"""
        # Create sample conflicts and resolutions
        conflicts = [
            PortConflict(
                port=3000,
                host="localhost",
                process_info={"pid": 1234, "name": "node"},
                service_type="node",
                severity="medium",
                resolution_options=[ResolutionStrategy.USE_ALTERNATIVE],
                alternative_ports=[3001]
            )
        ]

        resolutions = [
            ResolutionResult(
                success=True,
                strategy_used=ResolutionStrategy.USE_ALTERNATIVE,
                resolved_port=3001,
                message="Use alternative port 3001",
                action_taken="Suggested port 3001",
                requires_user_action=True
            )
        ]

        report = resolver.generate_resolution_report(conflicts, resolutions)

        # Verify report structure
        assert "PORT CONFLICT RESOLUTION REPORT" in report
        assert "Total Conflicts: 1" in report
        assert "Successfully Resolved: 1" in report
        assert "Port 3000 (node) - RESOLVED ✅" in report
        assert "Strategy Used: use_alternative" in report
        assert "RECOMMENDATIONS:" in report

    def test_identify_service_by_port(self, resolver):
        """Test service identification by port number"""
        # Test known port mappings
        assert resolver._identify_service_by_port(3000, None) == "node"
        assert resolver._identify_service_by_port(5432, None) == "postgres"
        assert resolver._identify_service_by_port(6379, None) == "redis"

        # Test with process info
        process_info = {"name": "python", "command_line": "python app.py"}
        assert resolver._identify_service_by_port(8000, process_info) == "python"

    def test_assess_conflict_severity(self, resolver):
        """Test conflict severity assessment"""
        # Test critical service
        severity, options = resolver._assess_conflict_severity(5432, "postgres", None)
        assert severity == "high"
        assert ResolutionStrategy.CHANGE_PORT in options

        # Test development service
        severity, options = resolver._assess_conflict_severity(3000, "node", None)
        assert severity == "medium"
        assert ResolutionStrategy.STOP_PROCESS in options

        # Test unknown service
        severity, options = resolver._assess_conflict_severity(9999, None, None)
        assert severity == "low"
        assert ResolutionStrategy.USE_ALTERNATIVE in options


class TestErrorKnowledgeBase:
    """Test cases for ErrorKnowledgeBase class"""

    @pytest.fixture
    def knowledge_base(self):
        """Create ErrorKnowledgeBase instance for testing"""
        return ErrorKnowledgeBase()

    def test_get_solution_existing_error(self, knowledge_base):
        """Test getting solution for existing error code"""
        solution = knowledge_base.get_solution("PORT_3000_CONFLICT")

        # Verify solution structure
        assert solution is not None
        assert solution.error_code == "PORT_3000_CONFLICT"
        assert "Port 3000 Conflict" in solution.title
        assert solution.category == ErrorCategory.PORT_CONFLICT
        assert len(solution.solution_steps) > 0
        assert len(solution.alternative_solutions) > 0

    def test_get_solution_nonexistent_error(self, knowledge_base):
        """Test getting solution for non-existent error code"""
        solution = knowledge_base.get_solution("NONEXISTENT_ERROR")
        assert solution is None

    def test_find_solutions_by_category(self, knowledge_base):
        """Test finding solutions by category"""
        port_conflicts = knowledge_base.find_solutions_by_category(ErrorCategory.PORT_CONFLICT)

        # Verify results
        assert len(port_conflicts) > 0
        for solution in port_conflicts:
            assert solution.category == ErrorCategory.PORT_CONFLICT
            assert "PORT_" in solution.error_code

    def test_find_solutions_by_platform(self, knowledge_base):
        """Test finding solutions by platform"""
        universal_solutions = knowledge_base.find_solutions_by_platform(Platform.UNIVERSAL)

        # Verify results include universal platform solutions
        assert len(universal_solutions) > 0
        for solution in universal_solutions:
            assert Platform.UNIVERSAL in solution.platforms

    def test_search_solutions(self, knowledge_base):
        """Test searching solutions by keyword"""
        # Test search by port conflict
        results = knowledge_base.search_solutions("port 3000")
        assert len(results) > 0
        assert any("3000" in solution.title for solution in results)

        # Test search by permission
        results = knowledge_base.search_solutions("permission")
        assert len(results) > 0
        assert any(solution.category == ErrorCategory.PERMISSION_DENIED for solution in results)

    def test_generate_user_guide(self, knowledge_base):
        """Test generation of user guide"""
        error_codes = ["PORT_3000_CONFLICT", "PERMISSION_FILE_ACCESS"]
        guide = knowledge_base.generate_user_guide(error_codes, Platform.UNIVERSAL)

        # Verify guide structure
        assert "ERROR RESOLUTION GUIDE" in guide
        assert "TABLE OF CONTENTS:" in guide
        assert "DETAILED SOLUTIONS:" in guide
        assert "Port 3000 Conflict" in guide
        assert "File Access Permission Denied" in guide
        assert "GENERAL TROUBLESHOOTING:" in guide

    def test_get_quick_fixes(self, knowledge_base):
        """Test getting quick fixes for multiple errors"""
        error_codes = ["PORT_3000_CONFLICT", "DEPENDENCY_MISSING"]
        quick_fixes = knowledge_base.get_quick_fixes(error_codes)

        # Verify quick fixes
        assert len(quick_fixes) == 2
        assert any("Port 3000 Conflict" in fix for fix in quick_fixes)
        assert any("Missing Dependency" in fix for fix in quick_fixes)

    def test_export_knowledge_base(self, knowledge_base):
        """Test export knowledge base to JSON"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as tmp_file:
            success = knowledge_base.export_knowledge_base(tmp_file.name)

            # Verify export success
            assert success is True

            # Verify file contents
            with open(tmp_file.name, 'r', encoding='utf-8') as f:
                data = json.load(f)
                assert "version" in data
                assert "solutions" in data
                assert "PORT_3000_CONFLICT" in data["solutions"]

            # Clean up with Windows-compatible approach
            try:
                tmp_file.close()  # Ensure file is closed before deletion
                if os.path.exists(tmp_file.name):
                    os.unlink(tmp_file.name)
            except (OSError, PermissionError):
                # Windows may have file locks, try once more after a brief delay
                import time
                time.sleep(0.1)
                try:
                    if os.path.exists(tmp_file.name):
                        os.unlink(tmp_file.name)
                except (OSError, PermissionError):
                    # If still can't delete, file will be cleaned up by system temp directory management
                    pass


class TestIntegration:
    """Integration tests for error detection system"""

    @pytest.mark.asyncio
    async def test_end_to_end_port_conflict_resolution(self):
        """Test end-to-end port conflict detection and resolution"""
        # Create components
        error_detector = ErrorDetector()
        resolver = PortConflictResolver()
        knowledge_base = ErrorKnowledgeBase()

        # Mock port checker to simulate port conflict
        with patch.object(error_detector.port_checker, 'check_port_availability') as mock_check, \
             patch.object(resolver.port_checker, 'check_port_availability') as mock_resolver_check, \
             patch.object(resolver, '_get_alternative_ports') as mock_alternatives:

            # Simulate port 3000 conflict
            mock_check.return_value = PortCheckResult(
                port=3000,
                host="localhost",
                status=PortStatus.OCCUPIED,
                is_available=False,
                process_info={"pid": 1234, "name": "node", "command_line": "node app.js"}
            )
            mock_resolver_check.return_value = mock_check.return_value
            mock_alternatives.return_value = [3001, 3002]

            # Detect conflicts
            conflicts = await error_detector.detect_port_conflicts("localhost", [3000])
            assert len(conflicts) == 1

            # Create structured error
            error_info = error_detector.create_port_conflict_error(conflicts[0])
            assert error_info.code == "PORT_CONFLICT_3000"

            # Get solution from knowledge base
            solution = knowledge_base.get_solution("PORT_3000_CONFLICT")
            assert solution is not None


class TestPermissionDiagnostic:
    """Test cases for PermissionDiagnostic class"""

    @pytest.fixture
    def permission_diagnostic(self):
        """Create PermissionDiagnostic instance for testing"""
        from core.permission_diagnostic import PermissionDiagnostic
        return PermissionDiagnostic()

    def test_detect_platform(self, permission_diagnostic):
        """Test platform detection"""
        from core.permission_diagnostic import PlatformType
        platform = permission_diagnostic._detect_platform()
        assert isinstance(platform, PlatformType)
        assert platform in [PlatformType.WINDOWS, PlatformType.LINUX, PlatformType.MACOS]

    def test_get_current_user(self, permission_diagnostic):
        """Test current user detection"""
        user = permission_diagnostic._get_current_user()
        assert isinstance(user, str)
        assert len(user) > 0
        assert user != 'unknown'

    @patch('platform.system')
    def test_windows_platform_detection(self, mock_system, permission_diagnostic):
        """Test Windows platform detection"""
        mock_system.return_value = 'Windows'
        platform = permission_diagnostic._detect_platform()
        from core.permission_diagnostic import PlatformType
        assert platform == PlatformType.WINDOWS

    @patch('platform.system')
    def test_linux_platform_detection(self, mock_system, permission_diagnostic):
        """Test Linux platform detection"""
        mock_system.return_value = 'Linux'
        platform = permission_diagnostic._detect_platform()
        from core.permission_diagnostic import PlatformType
        assert platform == PlatformType.LINUX

    @patch('platform.system')
    def test_macos_platform_detection(self, mock_system, permission_diagnostic):
        """Test macOS platform detection"""
        mock_system.return_value = 'Darwin'
        platform = permission_diagnostic._detect_platform()
        from core.permission_diagnostic import PlatformType
        assert platform == PlatformType.MACOS

    def test_check_admin_privileges(self, permission_diagnostic):
        """Test administrator privilege checking"""
        result = permission_diagnostic.check_admin_privileges()
        from core.permission_diagnostic import PermissionCheckResult, PermissionLevel, PlatformType

        assert isinstance(result, PermissionCheckResult)
        assert isinstance(result.has_permission, bool)
        assert isinstance(result.current_level, PermissionLevel)
        assert isinstance(result.required_level, PermissionLevel)
        assert isinstance(result.platform, PlatformType)
        assert isinstance(result.details, dict)
        assert isinstance(result.suggestions, list)

    def test_check_file_permissions_existing_file(self, permission_diagnostic):
        """Test file permission checking for existing file"""
        # Create a temporary file for testing
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
            temp_file.write("test content")
            temp_path = temp_file.name

        try:
            result = permission_diagnostic.check_file_permissions(temp_path)
            from core.permission_diagnostic import FilePermissionResult

            assert isinstance(result, FilePermissionResult)
            assert result.exists is True
            assert result.readable is True
            assert isinstance(result.writable, bool)
            assert isinstance(result.executable, bool)
            assert isinstance(result.permissions, str)
            assert isinstance(result.issues, list)
            assert isinstance(result.suggestions, list)
        finally:
            os.unlink(temp_path)

    def test_check_file_permissions_nonexistent_file(self, permission_diagnostic):
        """Test file permission checking for non-existent file"""
        nonexistent_path = "/path/that/does/not/exist"
        result = permission_diagnostic.check_file_permissions(nonexistent_path)
        from core.permission_diagnostic import FilePermissionResult

        assert isinstance(result, FilePermissionResult)
        assert result.exists is False
        assert result.readable is False
        assert result.writable is False
        assert result.executable is False
        assert len(result.issues) > 0
        assert len(result.suggestions) > 0

    def test_check_file_permissions_directory(self, permission_diagnostic):
        """Test directory permission checking"""
        with tempfile.TemporaryDirectory() as temp_dir:
            result = permission_diagnostic.check_file_permissions(temp_dir)
            from core.permission_diagnostic import FilePermissionResult

            assert isinstance(result, FilePermissionResult)
            assert result.exists is True
            assert result.readable is True
            assert isinstance(result.writable, bool)
            assert isinstance(result.executable, bool)

    def test_generate_privilege_suggestions(self, permission_diagnostic):
        """Test privilege escalation suggestions generation"""
        from core.permission_diagnostic import PermissionLevel
        suggestions = permission_diagnostic._generate_privilege_suggestions(PermissionLevel.ADMIN)

        assert isinstance(suggestions, list)
        assert len(suggestions) > 0
        assert all(isinstance(suggestion, str) for suggestion in suggestions)

    def test_diagnose_permission_issues_comprehensive(self, permission_diagnostic):
        """Test comprehensive permission diagnosis"""
        result = permission_diagnostic.diagnose_permission_issues()

        assert isinstance(result, dict)
        assert 'platform' in result
        assert 'current_user' in result
        assert 'admin_check' in result
        assert 'file_checks' in result
        assert 'overall_issues' in result
        assert 'recommendations' in result

        # Check admin check structure
        admin_check = result['admin_check']
        assert 'has_admin' in admin_check
        assert 'current_level' in admin_check
        assert 'required_level' in admin_check
        assert 'suggestions' in admin_check

        # Check file checks structure
        file_checks = result['file_checks']
        assert isinstance(file_checks, dict)

    def test_generate_privilege_guide(self, permission_diagnostic):
        """Test privilege guide generation"""
        guide = permission_diagnostic.generate_privilege_guide('port_binding')

        assert isinstance(guide, dict)
        assert 'methods' in guide
        assert 'notes' in guide
        assert 'operation_guidance' in guide

        # Check methods structure
        methods = guide['methods']
        assert isinstance(methods, list)
        assert len(methods) > 0

        for method in methods:
            assert 'name' in method
            assert 'steps' in method
            assert isinstance(method['steps'], list)

    def test_operation_specific_guidance(self, permission_diagnostic):
        """Test operation-specific guidance generation"""
        operations = ['port_binding', 'file_system', 'service_management', 'network_configuration']

        for operation in operations:
            guidance = permission_diagnostic._get_operation_specific_guidance(operation)
            assert isinstance(guidance, dict)
            assert 'description' in guidance
            assert 'additional_requirements' in guidance

    def test_get_common_paths_to_check(self, permission_diagnostic):
        """Test common paths generation"""
        paths = permission_diagnostic._get_common_paths_to_check()

        assert isinstance(paths, list)
        assert len(paths) > 0
        assert all(isinstance(path, str) for path in paths)


class TestPermissionDetectionIntegration:
    """Test cases for permission detection integration with ErrorDetector"""

    @pytest.fixture
    def error_detector(self):
        """Create ErrorDetector instance for testing"""
        return ErrorDetector()

    @pytest.mark.asyncio
    async def test_detect_permission_issues_integration(self, error_detector):
        """Test permission detection integration"""
        # Create temporary file for testing
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
            temp_file.write("test content")
            temp_path = temp_file.name

        try:
            # Test permission detection with specific paths
            permission_errors = await error_detector.detect_permission_issues([temp_path])

            assert isinstance(permission_errors, list)
            # The result should be empty since the temp file should be accessible
            # but we check the structure anyway
            for error in permission_errors:
                assert isinstance(error, PermissionError)
                assert hasattr(error, 'resource_path')
                assert hasattr(error, 'required_permissions')
                assert hasattr(error, 'current_user')
                assert hasattr(error, 'admin_required')
                assert hasattr(error, 'platform_specific_guidance')
        finally:
            os.unlink(temp_path)

    @pytest.mark.asyncio
    async def test_detect_permission_issues_default_paths(self, error_detector):
        """Test permission detection with default paths"""
        permission_errors = await error_detector.detect_permission_issues()

        assert isinstance(permission_errors, list)
        # Check structure of any errors found
        for error in permission_errors:
            assert isinstance(error, PermissionError)
            assert error.resource_path is not None
            assert error.required_permissions is not None

    def test_permission_diagnostic_initialization(self, error_detector):
        """Test that PermissionDiagnostic is properly initialized in ErrorDetector"""
        assert hasattr(error_detector, 'permission_diagnostic')
        assert error_detector.permission_diagnostic is not None

        # Test that the diagnostic module has required methods
        assert hasattr(error_detector.permission_diagnostic, 'check_admin_privileges')
        assert hasattr(error_detector.permission_diagnostic, 'check_file_permissions')
        assert hasattr(error_detector.permission_diagnostic, 'diagnose_permission_issues')
        assert hasattr(error_detector.permission_diagnostic, 'generate_privilege_guide')


# Test configuration and utilities
@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


def pytest_configure(config):
    """Configure pytest for error detection tests"""
    config.addinivalue_line(
        "markers", "asyncio: mark test as async"
    )


if __name__ == "__main__":
    # Run tests when script is executed directly
    pytest.main([__file__, "-v", "--tb=short"])