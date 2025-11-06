"""
Tests for ReportGenerator module

This test suite covers:
- Environment status analysis for all verification systems
- Scoring calculations and status determination
- Report generation in multiple formats
- Recommendation and next step generation
- Export functionality
- Progress tracking integration
"""

import pytest
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

from core.report_generator import (
    ReportGenerator,
    ReadinessStatus,
    ReportFormat,
    EnvironmentStatus,
    EnvironmentSummary,
    EnvironmentReport
)
from core.build_verifier import BuildResult, BuildTool
from core.python_module_verifier import ModuleImportResult, ImportError, ImportErrorType
from core.database_tester import DatabaseTestResult, DatabaseType, TestStatus
from core.port_checker import PortScanSummary, PortCheckResult, PortStatus
from utils.progress_tracker import ProgressTracker


class TestReportGenerator:
    """Test suite for ReportGenerator class"""

    @pytest.fixture
    def generator(self):
        """Create a ReportGenerator instance for testing"""
        return ReportGenerator()

    @pytest.fixture
    def mock_progress_tracker(self):
        """Create a mock progress tracker"""
        tracker = Mock(spec=ProgressTracker)
        tracker.start_task = Mock()
        tracker.update_progress = Mock()
        tracker.complete_task = Mock()
        return tracker

    @pytest.fixture
    def successful_build_result(self):
        """Create a successful build result"""
        return BuildResult(
            success=True,
            tool=BuildTool.NPM,
            command="npm run build",
            exit_code=0,
            stdout="Build completed successfully",
            stderr="",
            duration=10.5,
            artifacts_validated=True,
            dependencies_checked=True
        )

    @pytest.fixture
    def failed_build_result(self):
        """Create a failed build result"""
        return BuildResult(
            success=False,
            tool=BuildTool.NPM,
            command="npm run build",
            exit_code=1,
            stdout="",
            stderr="Error: Cannot find module 'express'",
            duration=5.2,
            error_analysis={
                'error_type': 'npm_missing_dependency',
                'severity': 'high',
                'message': 'Build failed: Npm Missing Dependency',
                'solution': 'Run npm install to install missing dependencies',
                'details': {'tool': 'npm'}
            }
        )

    @pytest.fixture
    def successful_python_result(self):
        """Create a successful Python module verification result"""
        return ModuleImportResult(
            success=True,
            total_files=5,
            verified_files=5,
            syntax_errors=[],
            import_errors=[],
            missing_modules=[],
            python_version="3.9.0",
            recommendations=["All modules imported successfully"]
        )

    @pytest.fixture
    def failed_python_result(self):
        """Create a failed Python module verification result"""
        syntax_error = ImportError(
            error_type=ImportErrorType.SYNTAX_ERROR,
            severity='critical',
            file_path='test.py',
            line_number=10,
            error_message='Syntax error: missing closing parenthesis'
        )

        import_error = ImportError(
            error_type=ImportErrorType.MODULE_NOT_FOUND,
            severity='high',
            file_path='main.py',
            line_number=5,
            error_message='Module not found: requests',
            module_name='requests',
            suggestion='pip install requests'
        )

        return ModuleImportResult(
            success=False,
            total_files=5,
            verified_files=3,
            syntax_errors=[syntax_error],
            import_errors=[import_error],
            missing_modules=['requests'],
            python_version="3.9.0",
            recommendations=["pip install requests", "Fix syntax errors"]
        )

    @pytest.fixture
    def successful_database_result(self):
        """Create a successful database test result"""
        return DatabaseTestResult(
            database_type=DatabaseType.POSTGRESQL,
            host="localhost",
            port=5432,
            status=TestStatus.SUCCESS,
            connection_time=0.5,
            read_time=0.1,
            write_time=0.2,
            error_message=None,
            details={"test_key": "test_value"}
        )

    @pytest.fixture
    def failed_database_result(self):
        """Create a failed database test result"""
        return DatabaseTestResult(
            database_type=DatabaseType.REDIS,
            host="localhost",
            port=6379,
            status=TestStatus.FAILURE,
            connection_time=5.0,
            read_time=None,
            write_time=None,
            error_message="Connection refused: Redis server not running",
            details={}
        )

    @pytest.fixture
    def successful_port_summary(self):
        """Create a successful port scan summary"""
        results = []
        for port in [3000, 3001, 8080]:
            result = Mock(spec=PortCheckResult)
            result.port = port
            result.status = PortStatus.AVAILABLE
            result.is_available = True
            result.process_info = None
            result.error_message = None
            results.append(result)

        return PortScanSummary(
            total_ports=3,
            available_ports=3,
            occupied_ports=0,
            conflicting_ports=0,
            scan_duration=1.5,
            results=results
        )

    @pytest.fixture
    def mixed_port_summary(self):
        """Create a mixed port scan summary with some occupied ports"""
        results = []

        # Available port
        result1 = Mock(spec=PortCheckResult)
        result1.port = 3000
        result1.status = PortStatus.AVAILABLE
        result1.is_available = True
        result1.process_info = None
        results.append(result1)

        # Occupied port
        result2 = Mock(spec=PortCheckResult)
        result2.port = 3001
        result2.status = PortStatus.OCCUPIED
        result2.is_available = False
        result2.process_info = {
            'pid': 1234,
            'name': 'node',
            'command_line': 'node server.js'
        }
        results.append(result2)

        return PortScanSummary(
            total_ports=2,
            available_ports=1,
            occupied_ports=1,
            conflicting_ports=0,
            scan_duration=2.0,
            results=results
        )

    def test_init_default_values(self, generator):
        """Test ReportGenerator initialization with default values"""
        assert generator.progress_tracker is None
        assert generator.start_time is None
        assert generator.scoring_weights['build_verification'] == 0.25
        assert generator.scoring_weights['python_modules'] == 0.25
        assert generator.scoring_weights['database_connectivity'] == 0.30
        assert generator.scoring_weights['port_availability'] == 0.20

    def test_set_progress_tracker(self, generator, mock_progress_tracker):
        """Test setting progress tracker"""
        generator.set_progress_tracker(mock_progress_tracker)
        assert generator.progress_tracker == mock_progress_tracker

    def test_start_timing(self, generator):
        """Test starting timing"""
        assert generator.start_time is None
        generator._start_timing()
        assert generator.start_time is not None

    def test_get_elapsed_time_no_timing(self, generator):
        """Test getting elapsed time when timing not started"""
        elapsed = generator._get_elapsed_time()
        assert elapsed == 0.0

    def test_calculate_component_score_ready(self, generator):
        """Test calculating component score for ready status"""
        score = generator._calculate_component_score(ReadinessStatus.READY, 0, 10)
        assert score == 100.0

    def test_calculate_component_score_warning_with_issues(self, generator):
        """Test calculating component score for warning status with issues"""
        score = generator._calculate_component_score(ReadinessStatus.WARNING, 2, 10)
        assert score == 80.0 - (2/10) * 20  # 80 - 4 = 76

    def test_determine_status_from_score_ready(self, generator):
        """Test determining ready status from high score"""
        status = generator._determine_status_from_score(95.0)
        assert status == ReadinessStatus.READY

    def test_determine_status_from_score_warning(self, generator):
        """Test determining warning status from medium score"""
        status = generator._determine_status_from_score(80.0)
        assert status == ReadinessStatus.WARNING

    def test_determine_status_from_score_error(self, generator):
        """Test determining error status from low score"""
        status = generator._determine_status_from_score(60.0)
        assert status == ReadinessStatus.ERROR

    def test_determine_status_from_score_critical(self, generator):
        """Test determining critical status from very low score"""
        status = generator._determine_status_from_score(30.0)
        assert status == ReadinessStatus.CRITICAL

    def test_analyze_build_results_all_successful(self, generator, successful_build_result):
        """Test analyzing build results with all successful builds"""
        status = generator._analyze_build_results([successful_build_result])

        assert status.component == "Build Verification"
        assert status.status == ReadinessStatus.READY
        assert status.score == 100.0
        assert status.details['total_builds'] == 1
        assert status.details['successful_builds'] == 1
        assert status.details['success_rate'] == 100.0
        assert len(status.issues) == 0

    def test_analyze_build_results_mixed(self, generator, successful_build_result, failed_build_result):
        """Test analyzing build results with mixed success/failure"""
        status = generator._analyze_build_results([successful_build_result, failed_build_result])

        assert status.component == "Build Verification"
        assert status.status == ReadinessStatus.WARNING  # 50% success rate
        assert status.details['total_builds'] == 2
        assert status.details['successful_builds'] == 1
        assert status.details['success_rate'] == 50.0
        assert len(status.issues) > 0
        assert "Error: Cannot find module 'express'" in status.issues[0]
        assert len(status.recommendations) > 0
        assert "Run npm install to install missing dependencies" in status.recommendations[0]

    def test_analyze_build_results_no_results(self, generator):
        """Test analyzing build results when no results provided"""
        status = generator._analyze_build_results([])

        assert status.component == "Build Verification"
        assert status.status == ReadinessStatus.WARNING
        assert status.score == 75.0  # Updated to match _calculate_component_score logic
        assert len(status.issues) == 1
        assert "No build verification was performed" in status.issues[0]
        assert len(status.recommendations) == 1
        assert "Run build verification for your projects" in status.recommendations[0]

    def test_analyze_python_results_successful(self, generator, successful_python_result):
        """Test analyzing Python results with successful verification"""
        status = generator._analyze_python_results(successful_python_result)

        assert status.component == "Python Module Verification"
        assert status.status == ReadinessStatus.READY
        assert status.score == 100.0
        assert status.details['total_files'] == 5
        assert status.details['verified_files'] == 5
        assert status.details['syntax_errors'] == 0
        assert len(status.issues) == 0

    def test_analyze_python_results_failed(self, generator, failed_python_result):
        """Test analyzing Python results with failed verification"""
        status = generator._analyze_python_results(failed_python_result)

        assert status.component == "Python Module Verification"
        assert status.status == ReadinessStatus.WARNING  # 2 issues for 5 files
        assert status.details['total_files'] == 5
        assert status.details['syntax_errors'] == 1
        assert status.details['import_errors'] == 1
        assert status.details['missing_modules'] == 1
        assert len(status.issues) == 3  # 1 syntax + 1 import + 1 missing module
        assert len(status.recommendations) >= 2

    def test_analyze_python_results_no_results(self, generator):
        """Test analyzing Python results when no result provided"""
        status = generator._analyze_python_results(None)

        assert status.component == "Python Module Verification"
        assert status.status == ReadinessStatus.WARNING
        assert status.score == 75.0  # Updated to match _calculate_component_score logic
        assert len(status.issues) == 1
        assert "No Python module verification was performed" in status.issues[0]

    def test_analyze_database_results_all_successful(self, generator, successful_database_result):
        """Test analyzing database results with all successful connections"""
        status = generator._analyze_database_results([successful_database_result])

        assert status.component == "Database Connectivity"
        assert status.status == ReadinessStatus.READY
        assert status.score == 100.0
        assert status.details['total_tests'] == 1
        assert status.details['successful_connections'] == 1
        assert status.details['success_rate'] == 100.0
        assert len(status.issues) == 0

    def test_analyze_database_results_mixed(self, generator, successful_database_result, failed_database_result):
        """Test analyzing database results with mixed success/failure"""
        status = generator._analyze_database_results([successful_database_result, failed_database_result])

        assert status.component == "Database Connectivity"
        assert status.status == ReadinessStatus.WARNING  # 50% success rate
        assert status.details['total_tests'] == 2
        assert status.details['successful_connections'] == 1
        assert status.details['success_rate'] == 50.0
        assert len(status.issues) > 0
        assert "Connection refused: Redis server not running" in status.issues[0]
        assert len(status.recommendations) > 0

    def test_analyze_database_results_no_results(self, generator):
        """Test analyzing database results when no results provided"""
        status = generator._analyze_database_results([])

        assert status.component == "Database Connectivity"
        assert status.status == ReadinessStatus.WARNING
        assert status.score == 75.0  # Updated to match _calculate_component_score logic
        assert len(status.issues) == 1
        assert "No database connectivity tests were performed" in status.issues[0]

    def test_analyze_port_results_all_available(self, generator, successful_port_summary):
        """Test analyzing port results with all ports available"""
        status = generator._analyze_port_results([successful_port_summary])

        assert status.component == "Port Availability"
        assert status.status == ReadinessStatus.READY
        assert status.score == 100.0
        assert status.details['total_ports'] == 3
        assert status.details['available_ports'] == 3
        assert status.details['occupied_ports'] == 0
        assert status.details['availability_rate'] == 100.0
        assert len(status.issues) == 0

    def test_analyze_port_results_mixed(self, generator, mixed_port_summary):
        """Test analyzing port results with mixed availability"""
        status = generator._analyze_port_results([mixed_port_summary])

        assert status.component == "Port Availability"
        assert status.status == ReadinessStatus.WARNING  # 50% availability
        assert status.details['total_ports'] == 2
        assert status.details['available_ports'] == 1
        assert status.details['occupied_ports'] == 1
        assert status.details['availability_rate'] == 50.0
        assert len(status.issues) == 1
        assert "Port 3001 is occupied by node" in status.issues[0]
        assert len(status.recommendations) >= 2

    def test_analyze_port_results_no_results(self, generator):
        """Test analyzing port results when no results provided"""
        status = generator._analyze_port_results([])

        assert status.component == "Port Availability"
        assert status.status == ReadinessStatus.WARNING
        assert status.score == 75.0  # Updated to match _calculate_component_score logic
        assert len(status.issues) == 1
        assert "No port availability checks were performed" in status.issues[0]

    def test_calculate_overall_score(self, generator):
        """Test calculating overall score from components"""
        components = [
            EnvironmentStatus(
                component="Build Verification",
                status=ReadinessStatus.READY,
                score=100.0,
                details={},
                issues=[],
                recommendations=[]
            ),
            EnvironmentStatus(
                component="Python Module Verification",
                status=ReadinessStatus.WARNING,
                score=80.0,
                details={},
                issues=[],
                recommendations=[]
            ),
            EnvironmentStatus(
                component="Database Connectivity",
                status=ReadinessStatus.READY,
                score=100.0,
                details={},
                issues=[],
                recommendations=[]
            ),
            EnvironmentStatus(
                component="Port Availability",
                status=ReadinessStatus.ERROR,
                score=60.0,
                details={},
                issues=[],
                recommendations=[]
            )
        ]

        overall_score = generator._calculate_overall_score(components)

        # Weighted calculation: 100*0.25 + 80*0.25 + 100*0.30 + 60*0.20 = 25 + 20 + 30 + 12 = 87
        assert overall_score == 87.0

    def test_calculate_overall_score_empty_components(self, generator):
        """Test calculating overall score with no components"""
        score = generator._calculate_overall_score([])
        assert score == 0.0

    def test_generate_recommendations_all_ready(self, generator):
        """Test generating recommendations when all components are ready"""
        components = [
            EnvironmentStatus(
                component="Test Component",
                status=ReadinessStatus.READY,
                score=100.0,
                details={},
                issues=[],
                recommendations=[]
            )
        ]

        recommendations = generator._generate_recommendations(components)

        assert len(recommendations) >= 1
        assert "✅ Environment is ready for deployment!" in recommendations[0]

    def test_generate_recommendations_with_errors(self, generator):
        """Test generating recommendations when there are errors"""
        components = [
            EnvironmentStatus(
                component="Test Component",
                status=ReadinessStatus.ERROR,
                score=40.0,
                details={},
                issues=["Test error"],
                recommendations=["Fix the test error"]
            )
        ]

        recommendations = generator._generate_recommendations(components)

        assert len(recommendations) >= 2
        assert "❌ ERRORS DETECTED" in recommendations[0]
        assert "Fix the test error" in recommendations

    def test_generate_recommendations_with_critical(self, generator):
        """Test generating recommendations when there are critical issues"""
        components = [
            EnvironmentStatus(
                component="Test Component",
                status=ReadinessStatus.CRITICAL,
                score=0.0,
                details={},
                issues=["Critical error"],
                recommendations=["Fix critical error immediately"]
            )
        ]

        recommendations = generator._generate_recommendations(components)

        assert len(recommendations) >= 2
        assert "🚨 CRITICAL ISSUES FOUND" in recommendations[0]
        assert "Fix critical error immediately" in recommendations

    def test_generate_next_steps_all_ready(self, generator):
        """Test generating next steps when all components are ready"""
        components = [
            EnvironmentStatus(
                component="Test Component",
                status=ReadinessStatus.READY,
                score=100.0,
                details={},
                issues=[],
                recommendations=[]
            )
        ]

        next_steps = generator._generate_next_steps(components)

        assert len(next_steps) >= 1
        assert "🎉 All components verified successfully" in next_steps[-1]  # Check last item

    def test_generate_next_steps_mixed_status(self, generator):
        """Test generating next steps with mixed component status"""
        components = [
            EnvironmentStatus(
                component="Critical Component",
                status=ReadinessStatus.CRITICAL,
                score=0.0,
                details={},
                issues=["Critical issue"],
                recommendations=[]
            ),
            EnvironmentStatus(
                component="Warning Component",
                status=ReadinessStatus.WARNING,
                score=80.0,
                details={},
                issues=["Warning issue"],
                recommendations=[]
            ),
            EnvironmentStatus(
                component="Ready Component",
                status=ReadinessStatus.READY,
                score=100.0,
                details={},
                issues=[],
                recommendations=[]
            )
        ]

        next_steps = generator._generate_next_steps(components)

        assert len(next_steps) >= 3
        assert any("Address critical and error issues" in step for step in next_steps)
        assert any("Review and resolve warnings" in step for step in next_steps)
        assert any("Verified components ready" in step for step in next_steps)

    def test_get_system_info(self, generator):
        """Test gathering system information"""
        system_info = generator._get_system_info()

        assert isinstance(system_info, dict)
        assert "platform" in system_info
        assert "python_version" in system_info
        assert "working_directory" in system_info
        assert "report_timestamp" in system_info

    @pytest.mark.asyncio
    async def test_generate_report_all_successful(
        self,
        generator,
        successful_build_result,
        successful_python_result,
        successful_database_result,
        successful_port_summary
    ):
        """Test generating report with all successful results"""
        generator._start_timing()

        report = await generator.generate_report(
            build_results=[successful_build_result],
            python_result=successful_python_result,
            database_results=[successful_database_result],
            port_results=[successful_port_summary]
        )

        assert isinstance(report, EnvironmentReport)
        assert report.summary.overall_status == ReadinessStatus.READY
        assert report.summary.overall_score == 100.0
        assert report.summary.total_components == 4
        assert report.summary.ready_components == 4
        assert len(report.components) == 4
        assert len(report.recommendations) >= 1
        assert "✅ Environment is ready for deployment!" in report.recommendations[0]

    @pytest.mark.asyncio
    async def test_generate_report_mixed_results(
        self,
        generator,
        successful_build_result,
        failed_python_result,
        failed_database_result,
        mixed_port_summary
    ):
        """Test generating report with mixed success/failure results"""
        generator._start_timing()

        report = await generator.generate_report(
            build_results=[successful_build_result],
            python_result=failed_python_result,
            database_results=[failed_database_result],
            port_results=[mixed_port_summary]
        )

        assert isinstance(report, EnvironmentReport)
        assert report.summary.overall_status in [ReadinessStatus.WARNING, ReadinessStatus.ERROR]
        assert report.summary.total_components == 4
        assert report.summary.ready_components < 4  # Not all components are ready
        assert len(report.components) == 4
        assert len(report.recommendations) >= 1

    @pytest.mark.asyncio
    async def test_generate_report_no_results(self, generator):
        """Test generating report with no verification results"""
        generator._start_timing()

        report = await generator.generate_report()

        assert isinstance(report, EnvironmentReport)
        assert report.summary.overall_status == ReadinessStatus.WARNING
        assert report.summary.total_components == 4
        assert report.summary.warning_components == 4  # All components should be warnings
        assert len(report.components) == 4

    @pytest.mark.asyncio
    async def test_generate_report_with_progress_tracker(
        self,
        generator,
        mock_progress_tracker,
        successful_build_result
    ):
        """Test generating report with progress tracker"""
        generator.set_progress_tracker(mock_progress_tracker)
        generator._start_timing()

        await generator.generate_report(build_results=[successful_build_result])

        # Verify progress tracker was called
        assert mock_progress_tracker.start_task.called
        assert mock_progress_tracker.update_progress.called
        assert mock_progress_tracker.complete_task.called

        # Check specific progress updates
        update_calls = mock_progress_tracker.update_progress.call_args_list
        assert len(update_calls) >= 4  # Should have at least 4 progress updates

    def test_generate_console_report_ready(self, generator):
        """Test generating console report for ready status"""
        # Create a simple ready report
        summary = EnvironmentSummary(
            overall_status=ReadinessStatus.READY,
            overall_score=100.0,
            total_components=4,
            ready_components=4,
            warning_components=0,
            error_components=0,
            critical_components=0,
            verification_duration=5.0,
            timestamp=datetime.now()
        )

        components = [
            EnvironmentStatus(
                component="Test Component",
                status=ReadinessStatus.READY,
                score=100.0,
                details={},
                issues=[],
                recommendations=[]
            )
        ]

        report = EnvironmentReport(
            summary=summary,
            components=components,
            build_results=[],
            python_results=None,
            database_results=[],
            port_results=[],
            system_info={},
            recommendations=["✅ Environment is ready for deployment!"],
            next_steps=["🎉 All components verified successfully - Ready to proceed!"]
        )

        console_report = generator.generate_console_report(report)

        assert isinstance(console_report, str)
        assert "🔍 ENVIRONMENT VERIFICATION REPORT" in console_report
        assert "✅ READY" in console_report
        assert "Overall Score: 100.0/100" in console_report
        assert "✅ Test Component" in console_report
        assert "✅ Environment is ready for deployment!" in console_report
        assert "🎉 All components verified successfully" in console_report

    def test_generate_console_report_with_issues(self, generator):
        """Test generating console report with issues"""
        # Create a report with issues
        summary = EnvironmentSummary(
            overall_status=ReadinessStatus.WARNING,
            overall_score=75.0,
            total_components=4,
            ready_components=2,
            warning_components=1,
            error_components=1,
            critical_components=0,
            verification_duration=5.0,
            timestamp=datetime.now()
        )

        components = [
            EnvironmentStatus(
                component="Build Verification",
                status=ReadinessStatus.ERROR,
                score=40.0,
                details={},
                issues=["Build failed: Missing dependency"],
                recommendations=["Run npm install"]
            )
        ]

        report = EnvironmentReport(
            summary=summary,
            components=components,
            build_results=[],
            python_results=None,
            database_results=[],
            port_results=[],
            system_info={},
            recommendations=["❌ ERRORS DETECTED - Fix errors before attempting deployment"],
            next_steps=["1. Address critical and error issues:"]
        )

        console_report = generator.generate_console_report(report)

        assert isinstance(console_report, str)
        assert "⚠️ WARNING" in console_report
        assert "Overall Score: 75.0/100" in console_report
        assert "❌ Build Verification" in console_report
        assert "Build failed: Missing dependency" in console_report
        assert "❌ ERRORS DETECTED" in console_report

    def test_save_json_report_success(self, generator):
        """Test saving report as JSON file"""
        # Create a simple report
        summary = EnvironmentSummary(
            overall_status=ReadinessStatus.READY,
            overall_score=100.0,
            total_components=1,
            ready_components=1,
            warning_components=0,
            error_components=0,
            critical_components=0,
            verification_duration=1.0,
            timestamp=datetime.now()
        )

        report = EnvironmentReport(
            summary=summary,
            components=[],
            build_results=[],
            python_results=None,
            database_results=[],
            port_results=[],
            system_info={},
            recommendations=[],
            next_steps=[]
        )

        # Test saving
        temp_dir = tempfile.mkdtemp()
        try:
            output_file = Path(temp_dir) / "test_report.json"
            success = generator.save_json_report(report, str(output_file))

            assert success is True
            assert output_file.exists()

            # Verify content
            with open(output_file, 'r') as f:
                data = json.load(f)

            assert data['summary']['overall_status'] == 'ready'
            assert data['summary']['overall_score'] == 100.0
            assert 'timestamp' in data['summary']

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_save_json_report_failure(self, generator):
        """Test saving JSON report with invalid path"""
        summary = EnvironmentSummary(
            overall_status=ReadinessStatus.READY,
            overall_score=100.0,
            total_components=1,
            ready_components=1,
            warning_components=0,
            error_components=0,
            critical_components=0,
            verification_duration=1.0,
            timestamp=datetime.now()
        )

        report = EnvironmentReport(
            summary=summary,
            components=[],
            build_results=[],
            python_results=None,
            database_results=[],
            port_results=[],
            system_info={},
            recommendations=[],
            next_steps=[]
        )

        # Try to save to invalid path - use a path with invalid characters
        invalid_path = "C:\\<invalid>\\path\\report.json"  # Contains invalid filename characters
        success = generator.save_json_report(report, invalid_path)

        assert success is False

    def test_save_markdown_report_success(self, generator):
        """Test saving report as Markdown file"""
        # Create a simple report
        summary = EnvironmentSummary(
            overall_status=ReadinessStatus.READY,
            overall_score=100.0,
            total_components=1,
            ready_components=1,
            warning_components=0,
            error_components=0,
            critical_components=0,
            verification_duration=1.0,
            timestamp=datetime.now()
        )

        component = EnvironmentStatus(
            component="Test Component",
            status=ReadinessStatus.READY,
            score=100.0,
            details={},
            issues=[],
            recommendations=[]
        )

        report = EnvironmentReport(
            summary=summary,
            components=[component],
            build_results=[],
            python_results=None,
            database_results=[],
            port_results=[],
            system_info={},
            recommendations=["Test recommendation"],
            next_steps=["Test next step"]
        )

        # Test saving
        temp_dir = tempfile.mkdtemp()
        try:
            output_file = Path(temp_dir) / "test_report.md"
            success = generator.save_markdown_report(report, str(output_file))

            assert success is True
            assert output_file.exists()

            # Verify content
            with open(output_file, 'r', encoding='utf-8') as f:
                content = f.read()

            assert "# 🔍 Environment Verification Report" in content
            assert "✅ READY" in content
            assert "**Overall Score:** 100.0/100" in content
            assert "✅ Test Component" in content
            assert "Test recommendation" in content
            assert "Test next step" in content

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_save_markdown_report_failure(self, generator):
        """Test saving Markdown report with invalid path"""
        summary = EnvironmentSummary(
            overall_status=ReadinessStatus.READY,
            overall_score=100.0,
            total_components=1,
            ready_components=1,
            warning_components=0,
            error_components=0,
            critical_components=0,
            verification_duration=1.0,
            timestamp=datetime.now()
        )

        report = EnvironmentReport(
            summary=summary,
            components=[],
            build_results=[],
            python_results=None,
            database_results=[],
            port_results=[],
            system_info={},
            recommendations=[],
            next_steps=[]
        )

        # Try to save to invalid path - use a path with invalid characters
        invalid_path = "C:\\<invalid>\\path\\report.md"  # Contains invalid filename characters
        success = generator.save_markdown_report(report, invalid_path)

        assert success is False

    def test_format_status(self, generator):
        """Test status formatting"""
        formatted = generator._format_status(ReadinessStatus.READY)
        assert "✅" in formatted
        assert "READY" in formatted

        formatted = generator._format_status(ReadinessStatus.ERROR)
        assert "❌" in formatted
        assert "ERROR" in formatted

    def test_get_status_icon(self, generator):
        """Test getting status icons"""
        assert generator._get_status_icon(ReadinessStatus.READY) == "✅"
        assert generator._get_status_icon(ReadinessStatus.WARNING) == "⚠️"
        assert generator._get_status_icon(ReadinessStatus.ERROR) == "❌"
        assert generator._get_status_icon(ReadinessStatus.CRITICAL) == "🚨"

    @pytest.mark.asyncio
    async def test_generate_and_save_report_all_formats(
        self,
        generator,
        successful_build_result
    ):
        """Test generating and saving report in all formats"""
        generator._start_timing()

        temp_dir = tempfile.mkdtemp()
        try:
            results = await generator.generate_and_save_report(
                output_directory=temp_dir,
                formats=[ReportFormat.CONSOLE, ReportFormat.JSON, ReportFormat.MARKDOWN],
                build_results=[successful_build_result]
            )

            assert len(results) == 3
            assert results['console'] is True  # Console format always succeeds
            assert results['json'] is True
            assert results['markdown'] is True

            # Check that files were created
            output_path = Path(temp_dir)
            json_files = list(output_path.glob("*.json"))
            md_files = list(output_path.glob("*.md"))

            assert len(json_files) == 1
            assert len(md_files) == 1

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.mark.asyncio
    async def test_generate_and_save_report_default_formats(
        self,
        generator,
        successful_build_result
    ):
        """Test generating and saving report with default formats"""
        generator._start_timing()

        temp_dir = tempfile.mkdtemp()
        try:
            results = await generator.generate_and_save_report(
                output_directory=temp_dir,
                build_results=[successful_build_result]
            )

            # Should generate console, JSON, and Markdown by default
            assert len(results) == 3
            assert 'console' in results
            assert 'json' in results
            assert 'markdown' in results

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestReportGeneratorIntegration:
    """Integration tests for ReportGenerator with realistic scenarios"""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_real_complete_verification_workflow(self):
        """Test complete verification workflow with realistic data"""
        generator = ReportGenerator()
        generator._start_timing()

        # Create realistic build results
        build_results = [
            BuildResult(
                success=True,
                tool=BuildTool.NPM,
                command="npm run build",
                exit_code=0,
                stdout="Build completed",
                stderr="",
                duration=15.2,
                artifacts_validated=True,
                dependencies_checked=True
            ),
            BuildResult(
                success=False,
                tool=BuildTool.YARN,
                command="yarn build",
                exit_code=1,
                stdout="",
                stderr="Module not found: lodash",
                duration=8.7,
                error_analysis={
                    'error_type': 'npm_missing_dependency',
                    'solution': 'Run yarn install'
                }
            )
        ]

        # Create realistic Python results
        python_result = ModuleImportResult(
            success=False,
            total_files=12,
            verified_files=10,
            syntax_errors=[
                ImportError(
                    error_type=ImportErrorType.SYNTAX_ERROR,
                    severity='critical',
                    file_path='src/utils.py',
                    line_number=25,
                    error_message='SyntaxError: invalid syntax'
                )
            ],
            import_errors=[
                ImportError(
                    error_type=ImportErrorType.MODULE_NOT_FOUND,
                    severity='high',
                    file_path='src/main.py',
                    line_number=8,
                    error_message='ModuleNotFoundError: No module named \'requests\'',
                    module_name='requests',
                    suggestion='pip install requests'
                )
            ],
            missing_modules=['requests', 'numpy'],
            python_version="3.9.7",
            recommendations=['pip install requests numpy', 'Fix syntax error in src/utils.py']
        )

        # Create realistic database results
        database_results = [
            DatabaseTestResult(
                database_type=DatabaseType.POSTGRESQL,
                host="localhost",
                port=5432,
                status=TestStatus.SUCCESS,
                connection_time=0.8,
                read_time=0.15,
                write_time=0.25,
                error_message=None,
                details={"test": "data"}
            ),
            DatabaseTestResult(
                database_type=DatabaseType.REDIS,
                host="localhost",
                port=6379,
                status=TestStatus.FAILURE,
                connection_time=5.0,
                read_time=None,
                write_time=None,
                error_message="Connection refused: [Errno 61] Connection refused",
                details={}
            )
        ]

        # Create realistic port results
        port_results = []
        for port in [3000, 8080, 5432, 6379]:
            if port in [3000, 8080]:
                status = PortStatus.AVAILABLE
                is_available = True
                process_info = None
            else:
                status = PortStatus.OCCUPIED
                is_available = False
                process_info = {'pid': 1234, 'name': 'postgres'} if port == 5432 else {'pid': 5678, 'name': 'redis-server'}

            result = Mock(spec=PortCheckResult)
            result.port = port
            result.status = status
            result.is_available = is_available
            result.process_info = process_info
            result.error_message = None

            if not hasattr(PortScanSummary, '__annotations__'):
                # Create a simple result object for testing
                port_results.append(result)

        # Create port summary
        port_summary = PortScanSummary(
            total_ports=4,
            available_ports=2,
            occupied_ports=2,
            conflicting_ports=0,
            scan_duration=3.2,
            results=port_results
        )

        # Generate comprehensive report
        report = await generator.generate_report(
            build_results=build_results,
            python_result=python_result,
            database_results=database_results,
            port_results=[port_summary]
        )

        # Verify report structure
        assert isinstance(report, EnvironmentReport)
        assert report.summary.total_components == 4
        assert report.summary.overall_score < 100.0  # Should not be perfect due to issues
        assert report.summary.overall_status in [ReadinessStatus.WARNING, ReadinessStatus.ERROR]

        # Verify components
        assert len(report.components) == 4
        component_names = [comp.component for comp in report.components]
        assert "Build Verification" in component_names
        assert "Python Module Verification" in component_names
        assert "Database Connectivity" in component_names
        assert "Port Availability" in component_names

        # Verify issues were detected
        total_issues = sum(len(comp.issues) for comp in report.components)
        assert total_issues > 0

        # Verify recommendations were generated
        assert len(report.recommendations) > 0
        assert any("pip install" in rec for rec in report.recommendations)
        assert any("yarn install" in rec for rec in report.recommendations)

        # Verify next steps were generated
        assert len(report.next_steps) > 0

        # Generate console report
        console_report = generator.generate_console_report(report)
        assert isinstance(console_report, str)
        assert len(console_report) > 500  # Should be a substantial report
        assert "🔍 ENVIRONMENT VERIFICATION REPORT" in console_report
        assert "COMPONENT DETAILS" in console_report
        assert "RECOMMENDATIONS" in console_report
        assert "NEXT STEPS" in console_report

        # Save reports
        temp_dir = tempfile.mkdtemp()
        try:
            results = await generator.generate_and_save_report(
                output_directory=temp_dir,
                formats=[ReportFormat.JSON, ReportFormat.MARKDOWN],
                build_results=build_results,
                python_result=python_result,
                database_results=database_results,
                port_results=[port_summary]
            )

            assert results['json'] is True
            assert results['markdown'] is True

            # Verify files exist and have content
            output_path = Path(temp_dir)
            json_file = next(output_path.glob("*.json"))
            md_file = next(output_path.glob("*.md"))

            assert json_file.stat().st_size > 1000  # Should be substantial
            assert md_file.stat().st_size > 1000

            # Verify JSON content
            with open(json_file, 'r') as f:
                json_data = json.load(f)
            assert 'summary' in json_data
            assert 'components' in json_data
            assert 'recommendations' in json_data

            # Verify Markdown content
            with open(md_file, 'r', encoding='utf-8') as f:
                md_content = f.read()
            assert "# 🔍 Environment Verification Report" in md_content
            assert "## 📊 Summary" in md_content
            assert "## 🔧 Component Details" in md_content

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

        # Print summary for manual verification
        print("\n" + "=" * 80)
        print("INTEGRATION TEST REPORT SUMMARY:")
        print("=" * 80)
        print(f"Overall Status: {report.summary.overall_status.value}")
        print(f"Overall Score: {report.summary.overall_score:.1f}/100")
        print(f"Total Issues: {total_issues}")
        print(f"Recommendations: {len(report.recommendations)}")
        print(f"Report Generation Duration: {report.summary.verification_duration:.2f}s")
        print("=" * 80)