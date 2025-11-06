"""
Environment Ready Report Generation System

This module provides comprehensive report generation capabilities for environment
configuration verification, including status summarization, scoring, recommendations,
and export functionality.
"""

import os
import json
import time
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union, Any
from dataclasses import dataclass, asdict
from enum import Enum

from utils.logger import get_logger
from utils.progress_tracker import ProgressTracker
from core.database_tester import DatabaseTestResult, DatabaseType, TestStatus
from core.build_verifier import BuildResult, BuildTool
from core.python_module_verifier import ModuleImportResult, ImportErrorType
from core.port_checker import PortScanSummary, PortStatus

logger = get_logger(__name__)


class ReadinessStatus(Enum):
    """Environment readiness status"""
    READY = "ready"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ReportFormat(Enum):
    """Available report formats"""
    CONSOLE = "console"
    JSON = "json"
    HTML = "html"
    MARKDOWN = "markdown"


@dataclass
class EnvironmentStatus:
    """Status of an environment component"""
    component: str
    status: ReadinessStatus
    score: float
    details: Dict[str, Any]
    issues: List[str]
    recommendations: List[str]


@dataclass
class EnvironmentSummary:
    """Overall environment summary"""
    overall_status: ReadinessStatus
    overall_score: float
    total_components: int
    ready_components: int
    warning_components: int
    error_components: int
    critical_components: int
    verification_duration: float
    timestamp: datetime


@dataclass
class EnvironmentReport:
    """Complete environment verification report"""
    summary: EnvironmentSummary
    components: List[EnvironmentStatus]
    build_results: List[BuildResult]
    python_results: Optional[ModuleImportResult]
    database_results: List[DatabaseTestResult]
    port_results: List[PortScanSummary]
    system_info: Dict[str, Any]
    recommendations: List[str]
    next_steps: List[str]


class ReportGenerator:
    """
    Environment Ready Report Generation System

    Features:
    - Comprehensive status aggregation from all verification systems
    - Environment readiness scoring and assessment
    - Detailed recommendations and next steps
    - Multiple export formats (console, JSON, HTML, Markdown)
    - Rich console output with progress tracking
    """

    def __init__(self, progress_tracker: Optional[ProgressTracker] = None):
        """
        Initialize report generator

        Args:
            progress_tracker: Progress tracker for report generation
        """
        self.progress_tracker = progress_tracker
        self.start_time = None

        # Scoring weights for different components
        self.scoring_weights = {
            'build_verification': 0.25,
            'python_modules': 0.25,
            'database_connectivity': 0.30,
            'port_availability': 0.20
        }

        # Status scoring thresholds
        self.score_thresholds = {
            ReadinessStatus.READY: 90.0,
            ReadinessStatus.WARNING: 70.0,
            ReadinessStatus.ERROR: 50.0,
            ReadinessStatus.CRITICAL: 0.0
        }

    def set_progress_tracker(self, tracker: ProgressTracker):
        """Set progress tracker for report generation"""
        self.progress_tracker = tracker

    def _start_timing(self):
        """Start timing the verification process"""
        self.start_time = time.time()

    def _get_elapsed_time(self) -> float:
        """Get elapsed time since start_timing was called"""
        if self.start_time is None:
            return 0.0
        return time.time() - self.start_time

    def _filter_sensitive_info(self, data: Dict) -> Dict:
        """
        Filter sensitive information from data before inclusion in reports

        Args:
            data: Dictionary potentially containing sensitive information

        Returns:
            Dictionary with sensitive information filtered out
        """
        import re
        import os

        # Patterns for sensitive information
        sensitive_patterns = [
            # Usernames (Windows and Unix)
            r'/Users/[^/]+', r'C:\\Users\\[^\\]+', r'/home/[^/]+',
            # API keys and tokens (common patterns)
            r'(api[_-]?key|token|secret|password|pwd)[\s:=]+["\']?[A-Za-z0-9+/=_-]{10,}["\']?',
            # Database connection strings (enhanced patterns)
            r'(mysql|postgresql|redis|mongodb)://[^:\s]+:[^@\s]+@[^/\s]+',
            r'host=[^;&\s]+.*?password=[^;&\s]+',
            r'password=[^;&\s]+.*?host=[^;&\s]+',
            # Connection parameters in URLs
            r'[?&](password|pwd|token|secret)=[^&\s]+',
            # Email addresses
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            # Authorization headers
            r'(authorization|auth)[\s:=]+["\']?[A-Za-z0-9+/=_-]{10,}["\']?',
            r'Bearer\s+[A-Za-z0-9+/=_-]{10,}',
            # Private keys and certificates
            r'-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----',
            r'-----BEGIN\s+CERTIFICATE-----',
            # IP addresses (optional, can be useful for debugging)
            r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b',
            # File paths with sensitive patterns
            r'\.ssh[/\\]', r'\.aws[/\\]', r'\.config[/\\]',
            r'\.env', r'\.pem', r'\.key', r'\.crt',
        ]

        def filter_string(text: str) -> str:
            """Apply filtering to a single string"""
            if not isinstance(text, str):
                return text

            filtered = text
            for pattern in sensitive_patterns:
                # Replace sensitive patterns with placeholder
                filtered = re.sub(pattern, '[FILTERED]', filtered, flags=re.IGNORECASE)

            # Additional path filtering
            if '/' in filtered or '\\' in filtered:
                # Extract just the filename from paths, remove directory structure
                if os.path.isfile(filtered):
                    filtered = os.path.basename(filtered)
                else:
                    # For directories, keep only the last two components
                    parts = os.path.normpath(filtered).split(os.sep)
                    if len(parts) > 2:
                        filtered = os.path.join(*parts[-2:])

            return filtered

        def filter_recursive(obj):
            """Recursively filter sensitive information from data structure"""
            if isinstance(obj, dict):
                return {key: filter_recursive(value) for key, value in obj.items()}
            elif isinstance(obj, list):
                return [filter_recursive(item) for item in obj]
            elif isinstance(obj, str):
                return filter_string(obj)
            else:
                return obj

        return filter_recursive(data)

    def _filter_database_results(self, database_results: List[DatabaseTestResult]) -> List[DatabaseTestResult]:
        """
        Filter sensitive information from database test results

        Args:
            database_results: List of database test results

        Returns:
            List of database test results with sensitive information filtered
        """
        if not database_results:
            return database_results

        filtered_results = []
        for result in database_results:
            # Create a copy of the result with filtered information
            filtered_result = DatabaseTestResult(
                database_type=result.database_type,
                host=result.host,
                port=result.port,
                status=result.status,
                connection_time=result.connection_time,
                read_time=result.read_time,
                write_time=result.write_time,
                error_message=self._filter_sensitive_info({"error": result.error_message})["error"] if result.error_message else None,
                details=self._filter_sensitive_info(result.details) if result.details else None
            )
            filtered_results.append(filtered_result)

        return filtered_results

    def _calculate_component_score(self, status: ReadinessStatus, issues_count: int, total_items: int) -> float:
        """
        Calculate score for a component based on status and issues

        Args:
            status: Component status
            issues_count: Number of issues found
            total_items: Total items checked

        Returns:
            Score between 0-100
        """
        base_score = {
            ReadinessStatus.READY: 100.0,
            ReadinessStatus.WARNING: 80.0,
            ReadinessStatus.ERROR: 40.0,
            ReadinessStatus.CRITICAL: 0.0
        }.get(status, 0.0)

        # Deduct points for issues only if tests were actually performed
        if total_items > 0:
            issue_penalty = (issues_count / total_items) * 20
            base_score = max(0, base_score - issue_penalty)
        elif status == ReadinessStatus.WARNING:
            # For warning status with no tests performed, give a moderate score
            # This indicates no verification was done, not actual failures
            base_score = 75.0  # Above WARNING threshold (70.0) but below READY (90.0)

        return base_score

    def _determine_status_from_score(self, score: float) -> ReadinessStatus:
        """
        Determine readiness status from score

        Args:
            score: Component score

        Returns:
            ReadinessStatus based on score thresholds
        """
        if score >= self.score_thresholds[ReadinessStatus.READY]:
            return ReadinessStatus.READY
        elif score >= self.score_thresholds[ReadinessStatus.WARNING]:
            return ReadinessStatus.WARNING
        elif score >= self.score_thresholds[ReadinessStatus.ERROR]:
            return ReadinessStatus.ERROR
        else:
            return ReadinessStatus.CRITICAL

    def _analyze_build_results(self, build_results: List[BuildResult]) -> EnvironmentStatus:
        """
        Analyze build verification results

        Args:
            build_results: List of build verification results

        Returns:
            EnvironmentStatus for build verification
        """
        if not build_results:
            score = self._calculate_component_score(ReadinessStatus.WARNING, 1, 0)  # 1 issue (no verification), 0 items
            return EnvironmentStatus(
                component="Build Verification",
                status=ReadinessStatus.WARNING,
                score=score,
                details={"message": "No build results provided"},
                issues=["No build verification was performed"],
                recommendations=["Run build verification for your projects"]
            )

        successful_builds = sum(1 for result in build_results if result.success)
        total_builds = len(build_results)
        success_rate = (successful_builds / total_builds) * 100 if total_builds > 0 else 0

        issues = []
        recommendations = []

        for result in build_results:
            if not result.success:
                issues.append(f"Build failed for {result.tool.value}: {result.stderr[:200]}...")

                if result.error_analysis:
                    recommendations.append(result.error_analysis.get('solution', 'Check build configuration'))

        if success_rate == 100:
            status = ReadinessStatus.READY
        elif success_rate >= 50:
            status = ReadinessStatus.WARNING
        else:
            status = ReadinessStatus.ERROR

        score = self._calculate_component_score(status, len(issues), total_builds)

        return EnvironmentStatus(
            component="Build Verification",
            status=status,
            score=score,
            details={
                "total_builds": total_builds,
                "successful_builds": successful_builds,
                "success_rate": success_rate,
                "build_tools": list(set(r.tool.value for r in build_results))
            },
            issues=issues,
            recommendations=recommendations
        )

    def _analyze_python_results(self, python_result: Optional[ModuleImportResult]) -> EnvironmentStatus:
        """
        Analyze Python module verification results

        Args:
            python_result: Python module import verification result

        Returns:
            EnvironmentStatus for Python modules
        """
        if python_result is None:
            score = self._calculate_component_score(ReadinessStatus.WARNING, 1, 0)  # 1 issue (no verification), 0 items
            return EnvironmentStatus(
                component="Python Module Verification",
                status=ReadinessStatus.WARNING,
                score=score,
                details={"message": "No Python verification was performed"},
                issues=["No Python module verification was performed"],
                recommendations=["Run Python module verification for your projects"]
            )

        total_issues = len(python_result.syntax_errors) + len(python_result.import_errors)
        total_files = python_result.total_files

        issues = []
        recommendations = []

        # Add syntax errors
        for error in python_result.syntax_errors:
            issues.append(f"Syntax error in {error.file_path}:{error.line_number}: {error.error_message}")

        # Add import errors
        for error in python_result.import_errors:
            issues.append(f"Import error in {error.file_path}: {error.error_message}")

        # Add missing modules
        for module in python_result.missing_modules:
            issues.append(f"Missing module: {module}")

        # Add recommendations from result
        recommendations.extend(python_result.recommendations)

        if python_result.success:
            status = ReadinessStatus.READY
        elif total_issues <= 3:
            status = ReadinessStatus.WARNING
        else:
            status = ReadinessStatus.ERROR

        score = self._calculate_component_score(status, total_issues, total_files)

        return EnvironmentStatus(
            component="Python Module Verification",
            status=status,
            score=score,
            details={
                "total_files": python_result.total_files,
                "verified_files": python_result.verified_files,
                "syntax_errors": len(python_result.syntax_errors),
                "import_errors": len(python_result.import_errors),
                "missing_modules": len(python_result.missing_modules),
                "python_version": python_result.python_version
            },
            issues=issues,
            recommendations=recommendations
        )

    def _analyze_database_results(self, database_results: List[DatabaseTestResult]) -> EnvironmentStatus:
        """
        Analyze database connectivity test results

        Args:
            database_results: List of database test results

        Returns:
            EnvironmentStatus for database connectivity
        """
        if not database_results:
            score = self._calculate_component_score(ReadinessStatus.WARNING, 1, 0)  # 1 issue (no verification), 0 items
            return EnvironmentStatus(
                component="Database Connectivity",
                status=ReadinessStatus.WARNING,
                score=score,
                details={"message": "No database tests were performed"},
                issues=["No database connectivity tests were performed"],
                recommendations=["Run database connectivity tests for your databases"]
            )

        successful_connections = sum(1 for result in database_results if result.status == TestStatus.SUCCESS)
        total_tests = len(database_results)
        success_rate = (successful_connections / total_tests) * 100 if total_tests > 0 else 0

        issues = []
        recommendations = []

        for result in database_results:
            if result.status != TestStatus.SUCCESS:
                issues.append(f"Database connection failed for {result.database_type.value}: {result.error_message}")

                if result.database_type == DatabaseType.REDIS:
                    recommendations.append("Ensure Redis server is running and accessible")
                elif result.database_type == DatabaseType.POSTGRESQL:
                    recommendations.append("Ensure PostgreSQL server is running and connection details are correct")

            # Check if read/write tests were performed (indicated by presence of read_time and write_time)
            if (result.status == TestStatus.SUCCESS and
                (result.read_time is None or result.write_time is None)):
                issues.append(f"Database read/write test incomplete for {result.database_type.value}")
                recommendations.append(f"Check database permissions for {result.database_type.value}")

        if success_rate == 100:
            status = ReadinessStatus.READY
        elif success_rate >= 50:
            status = ReadinessStatus.WARNING
        else:
            status = ReadinessStatus.ERROR

        score = self._calculate_component_score(status, len(issues), total_tests)

        return EnvironmentStatus(
            component="Database Connectivity",
            status=status,
            score=score,
            details={
                "total_tests": total_tests,
                "successful_connections": successful_connections,
                "success_rate": success_rate,
                "database_types": list(set(r.database_type.value for r in database_results))
            },
            issues=issues,
            recommendations=recommendations
        )

    def _analyze_port_results(self, port_results: List[PortScanSummary]) -> EnvironmentStatus:
        """
        Analyze port availability check results

        Args:
            port_results: List of port scan summaries

        Returns:
            EnvironmentStatus for port availability
        """
        if not port_results:
            status = ReadinessStatus.WARNING
            score = self._calculate_component_score(status, 0, 0)  # No tests performed
            return EnvironmentStatus(
                component="Port Availability",
                status=status,
                score=score,
                details={"message": "No port checks were performed"},
                issues=["No port availability checks were performed"],
                recommendations=["Run port availability checks for required ports"]
            )

        total_ports = sum(summary.total_ports for summary in port_results)
        available_ports = sum(summary.available_ports for summary in port_results)
        occupied_ports = sum(summary.occupied_ports for summary in port_results)
        conflicting_ports = sum(summary.conflicting_ports for summary in port_results)

        availability_rate = (available_ports / total_ports) * 100 if total_ports > 0 else 0

        issues = []
        recommendations = []

        for summary in port_results:
            for result in summary.results:
                if not result.is_available:
                    if result.status == PortStatus.OCCUPIED:
                        if result.process_info:
                            issues.append(f"Port {result.port} is occupied by {result.process_info.get('name', 'unknown process')} (PID: {result.process_info.get('pid', 'N/A')})")
                        else:
                            issues.append(f"Port {result.port} is occupied by unknown process")
                    elif result.status == PortStatus.CONFLICT:
                        issues.append(f"Port {result.port} has permission or configuration conflicts")
                        recommendations.append(f"Check permissions for port {result.port}")

        # Add general recommendations for occupied ports
        if occupied_ports > 0:
            recommendations.append("Stop unnecessary services to free up required ports")
            recommendations.append("Consider using alternative ports if required ports are occupied")

        if availability_rate >= 90:
            status = ReadinessStatus.READY
        elif availability_rate >= 50:
            status = ReadinessStatus.WARNING
        else:
            status = ReadinessStatus.ERROR

        score = self._calculate_component_score(status, occupied_ports + conflicting_ports, total_ports)

        return EnvironmentStatus(
            component="Port Availability",
            status=status,
            score=score,
            details={
                "total_ports": total_ports,
                "available_ports": available_ports,
                "occupied_ports": occupied_ports,
                "conflicting_ports": conflicting_ports,
                "availability_rate": availability_rate,
                "scan_duration": sum(summary.scan_duration for summary in port_results)
            },
            issues=issues,
            recommendations=recommendations
        )

    def _calculate_overall_score(self, components: List[EnvironmentStatus]) -> float:
        """
        Calculate overall environment score

        Args:
            components: List of component statuses

        Returns:
            Overall score (0-100)
        """
        if not components:
            return 0.0

        weighted_scores = []
        for component in components:
            weight = self.scoring_weights.get(component.component.lower().replace(' ', '_'), 0.25)
            weighted_score = component.score * weight
            weighted_scores.append(weighted_score)

        return sum(weighted_scores)

    def _generate_recommendations(self, components: List[EnvironmentStatus]) -> List[str]:
        """
        Generate overall recommendations based on component analysis

        Args:
            components: List of component statuses

        Returns:
            List of recommendations
        """
        recommendations = []
        critical_issues = []

        for component in components:
            # Add component-specific recommendations
            recommendations.extend(component.recommendations)

            # Track critical issues
            if component.status == ReadinessStatus.CRITICAL:
                critical_issues.append(f"{component.component}: {len(component.issues)} critical issues")

        # Add overall recommendations based on status
        if any(comp.status == ReadinessStatus.CRITICAL for comp in components):
            recommendations.insert(0, "🚨 CRITICAL ISSUES FOUND - Address critical issues before proceeding")

        if any(comp.status == ReadinessStatus.ERROR for comp in components):
            recommendations.insert(0, "❌ ERRORS DETECTED - Fix errors before attempting deployment")

        if any(comp.status == ReadinessStatus.WARNING for comp in components):
            recommendations.append("⚠️  WARNINGS - Review warnings for optimal performance")

        # Add success message if all components are ready
        if all(comp.status == ReadinessStatus.READY for comp in components):
            recommendations.insert(0, "✅ Environment is ready for deployment!")

        return recommendations

    def _generate_next_steps(self, components: List[EnvironmentStatus]) -> List[str]:
        """
        Generate next steps based on component analysis

        Args:
            components: List of component statuses

        Returns:
            List of next steps
        """
        next_steps = []

        # Prioritize critical and error components
        critical_components = [comp for comp in components if comp.status in [ReadinessStatus.CRITICAL, ReadinessStatus.ERROR]]
        warning_components = [comp for comp in components if comp.status == ReadinessStatus.WARNING]
        ready_components = [comp for comp in components if comp.status == ReadinessStatus.READY]

        if critical_components:
            next_steps.append("1. Address critical and error issues:")
            for comp in critical_components:
                next_steps.append(f"   - Fix {comp.component} issues")

        if warning_components:
            next_steps.append("2. Review and resolve warnings:")
            for comp in warning_components:
                next_steps.append(f"   - Check {comp.component} warnings")

        if ready_components:
            next_steps.append("3. Verified components ready:")
            for comp in ready_components:
                next_steps.append(f"   - {comp.component} is ready")

        if not critical_components and not warning_components:
            next_steps.append("🎉 All components verified successfully - Ready to proceed!")

        return next_steps

    def _get_system_info(self) -> Dict[str, Any]:
        """
        Gather system information for the report

        Returns:
            Dictionary with system information
        """
        try:
            import platform
            import sys

            system_info = {
                "platform": platform.platform(),
                "system": platform.system(),
                "release": platform.release(),
                "version": platform.version(),
                "machine": platform.machine(),
                "processor": platform.processor(),
                "python_version": sys.version.split()[0],  # Only keep version number, not build info
                "python_executable": os.path.basename(sys.executable),  # Only keep executable name
                "working_directory": os.path.basename(os.getcwd()),  # Only keep directory name
                "report_timestamp": datetime.now().isoformat()
            }

            # Apply sensitive information filtering
            return self._filter_sensitive_info(system_info)
        except Exception as e:
            logger.warning(f"Failed to gather system info: {e}")
            return {"error": f"Failed to gather system info: {str(e)}"}

    async def generate_report(
        self,
        build_results: List[BuildResult] = None,
        python_result: Optional[ModuleImportResult] = None,
        database_results: List[DatabaseTestResult] = None,
        port_results: List[PortScanSummary] = None
    ) -> EnvironmentReport:
        """
        Generate comprehensive environment verification report

        Args:
            build_results: List of build verification results
            python_result: Python module verification result
            database_results: List of database test results
            port_results: List of port scan summaries

        Returns:
            Complete environment verification report
        """
        if self.progress_tracker:
            self.progress_tracker.start_task(
                "report_generation",
                "Generating environment verification report..."
            )

        # Initialize with empty results if None provided
        build_results = build_results or []
        database_results = database_results or []
        port_results = port_results or []

        # Apply sensitive information filtering to database results
        database_results = self._filter_database_results(database_results)

        # Analyze each component
        if self.progress_tracker:
            self.progress_tracker.update_progress(25, 100, "Analyzing build verification results...")

        build_status = self._analyze_build_results(build_results)

        if self.progress_tracker:
            self.progress_tracker.update_progress(50, 100, "Analyzing Python module verification results...")

        python_status = self._analyze_python_results(python_result)

        if self.progress_tracker:
            self.progress_tracker.update_progress(70, 100, "Analyzing database connectivity results...")

        database_status = self._analyze_database_results(database_results)

        if self.progress_tracker:
            self.progress_tracker.update_progress(85, 100, "Analyzing port availability results...")

        port_status = self._analyze_port_results(port_results)

        # Compile all components
        components = [build_status, python_status, database_status, port_status]

        # Calculate overall score and status
        if self.progress_tracker:
            self.progress_tracker.update_progress(90, 100, "Calculating overall scores and recommendations...")

        overall_score = self._calculate_overall_score(components)
        overall_status = self._determine_status_from_score(overall_score)

        # Count components by status
        status_counts = {
            ReadinessStatus.READY: 0,
            ReadinessStatus.WARNING: 0,
            ReadinessStatus.ERROR: 0,
            ReadinessStatus.CRITICAL: 0
        }

        for component in components:
            status_counts[component.status] += 1

        # Create summary
        summary = EnvironmentSummary(
            overall_status=overall_status,
            overall_score=overall_score,
            total_components=len(components),
            ready_components=status_counts[ReadinessStatus.READY],
            warning_components=status_counts[ReadinessStatus.WARNING],
            error_components=status_counts[ReadinessStatus.ERROR],
            critical_components=status_counts[ReadinessStatus.CRITICAL],
            verification_duration=self._get_elapsed_time(),
            timestamp=datetime.now()
        )

        # Generate recommendations and next steps
        recommendations = self._generate_recommendations(components)
        next_steps = self._generate_next_steps(components)

        # Get system information
        system_info = self._get_system_info()

        # Create final report
        report = EnvironmentReport(
            summary=summary,
            components=components,
            build_results=build_results,
            python_results=python_result,
            database_results=database_results,
            port_results=port_results,
            system_info=system_info,
            recommendations=recommendations,
            next_steps=next_steps
        )

        if self.progress_tracker:
            self.progress_tracker.complete_task(
                "report_generation",
                f"Report generation complete - Overall status: {overall_status.value.upper()}"
            )

        return report

    def generate_console_report(self, report: EnvironmentReport) -> str:
        """
        Generate console-formatted report

        Args:
            report: Environment verification report

        Returns:
            Console-formatted report string
        """
        lines = []

        # Header
        lines.append("=" * 80)
        lines.append("🔍 ENVIRONMENT VERIFICATION REPORT")
        lines.append("=" * 80)
        lines.append(f"Generated: {report.summary.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"Overall Status: {self._format_status(report.summary.overall_status)}")
        lines.append(f"Overall Score: {report.summary.overall_score:.1f}/100")
        lines.append(f"Verification Duration: {report.summary.verification_duration:.2f} seconds")
        lines.append("")

        # Summary
        lines.append("📊 SUMMARY")
        lines.append("-" * 40)
        lines.append(f"Total Components: {report.summary.total_components}")
        lines.append(f"✅ Ready: {report.summary.ready_components}")
        lines.append(f"⚠️  Warning: {report.summary.warning_components}")
        lines.append(f"❌ Error: {report.summary.error_components}")
        lines.append(f"🚨 Critical: {report.summary.critical_components}")
        lines.append("")

        # Component Details
        lines.append("🔧 COMPONENT DETAILS")
        lines.append("-" * 40)

        for component in report.components:
            status_icon = self._get_status_icon(component.status)
            lines.append(f"{status_icon} {component.component}")
            lines.append(f"   Score: {component.score:.1f}/100")
            lines.append(f"   Status: {component.status.value.upper()}")

            if component.issues:
                lines.append(f"   Issues ({len(component.issues)}):")
                for issue in component.issues[:3]:  # Limit to first 3 issues
                    lines.append(f"     • {issue}")
                if len(component.issues) > 3:
                    lines.append(f"     ... and {len(component.issues) - 3} more")

            lines.append("")

        # Recommendations
        if report.recommendations:
            lines.append("💡 RECOMMENDATIONS")
            lines.append("-" * 40)
            for rec in report.recommendations[:5]:  # Limit to first 5 recommendations
                lines.append(f"• {rec}")
            if len(report.recommendations) > 5:
                lines.append(f"... and {len(report.recommendations) - 5} more recommendations")
            lines.append("")

        # Next Steps
        if report.next_steps:
            lines.append("📋 NEXT STEPS")
            lines.append("-" * 40)
            for step in report.next_steps:
                lines.append(step)
            lines.append("")

        # System Info
        lines.append("💻 SYSTEM INFORMATION")
        lines.append("-" * 40)
        lines.append(f"Platform: {report.system_info.get('platform', 'N/A')}")
        lines.append(f"Python: {report.system_info.get('python_version', 'N/A')}")
        lines.append(f"Working Directory: {report.system_info.get('working_directory', 'N/A')}")

        lines.append("")
        lines.append("=" * 80)

        return "\n".join(lines)

    def _format_status(self, status: ReadinessStatus) -> str:
        """Format status with appropriate icon"""
        return f"{self._get_status_icon(status)} {status.value.upper()}"

    def _get_status_icon(self, status: ReadinessStatus) -> str:
        """Get icon for status"""
        icons = {
            ReadinessStatus.READY: "✅",
            ReadinessStatus.WARNING: "⚠️",
            ReadinessStatus.ERROR: "❌",
            ReadinessStatus.CRITICAL: "🚨"
        }
        return icons.get(status, "❓")

    def save_json_report(self, report: EnvironmentReport, output_file: str) -> bool:
        """
        Save report as JSON file

        Args:
            report: Environment verification report
            output_file: Path to output JSON file

        Returns:
            True if successful, False otherwise
        """
        try:
            # Convert report to JSON-serializable format
            report_dict = asdict(report)

            # Handle datetime serialization
            report_dict['summary']['timestamp'] = report.summary.timestamp.isoformat()

            # Convert enums to strings
            def convert_enums(obj):
                if isinstance(obj, dict):
                    return {k: convert_enums(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [convert_enums(item) for item in obj]
                elif isinstance(obj, (ReadinessStatus, ReportFormat, BuildTool, DatabaseType, PortStatus, TestStatus, ImportErrorType)):
                    return obj.value
                else:
                    return obj

            report_dict = convert_enums(report_dict)

            # Write to file
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(report_dict, f, indent=2, ensure_ascii=False)

            logger.info(f"JSON report saved to: {output_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to save JSON report: {e}")
            return False

    def save_markdown_report(self, report: EnvironmentReport, output_file: str) -> bool:
        """
        Save report as Markdown file

        Args:
            report: Environment verification report
            output_file: Path to output Markdown file

        Returns:
            True if successful, False otherwise
        """
        try:
            lines = []

            # Header
            lines.append("# 🔍 Environment Verification Report")
            lines.append("")
            lines.append(f"**Generated:** {report.summary.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
            lines.append(f"**Overall Status:** {self._format_status(report.summary.overall_status)}")
            lines.append(f"**Overall Score:** {report.summary.overall_score:.1f}/100")
            lines.append(f"**Verification Duration:** {report.summary.verification_duration:.2f} seconds")
            lines.append("")

            # Summary Table
            lines.append("## 📊 Summary")
            lines.append("")
            lines.append("| Status | Count |")
            lines.append("|--------|-------|")
            lines.append(f"| ✅ Ready | {report.summary.ready_components} |")
            lines.append(f"| ⚠️ Warning | {report.summary.warning_components} |")
            lines.append(f"| ❌ Error | {report.summary.error_components} |")
            lines.append(f"| 🚨 Critical | {report.summary.critical_components} |")
            lines.append("")

            # Component Details
            lines.append("## 🔧 Component Details")
            lines.append("")

            for component in report.components:
                lines.append(f"### {self._get_status_icon(component.status)} {component.component}")
                lines.append("")
                lines.append(f"- **Score:** {component.score:.1f}/100")
                lines.append(f"- **Status:** {component.status.value.upper()}")

                if component.issues:
                    lines.append(f"- **Issues ({len(component.issues)}):**")
                    for issue in component.issues:
                        lines.append(f"  - {issue}")

                if component.recommendations:
                    lines.append(f"- **Recommendations:**")
                    for rec in component.recommendations:
                        lines.append(f"  - {rec}")

                lines.append("")

            # Recommendations
            if report.recommendations:
                lines.append("## 💡 Recommendations")
                lines.append("")
                for rec in report.recommendations:
                    lines.append(f"- {rec}")
                lines.append("")

            # Next Steps
            if report.next_steps:
                lines.append("## 📋 Next Steps")
                lines.append("")
                for step in report.next_steps:
                    lines.append(step)
                lines.append("")

            # System Information
            lines.append("## 💻 System Information")
            lines.append("")
            lines.append(f"- **Platform:** {report.system_info.get('platform', 'N/A')}")
            lines.append(f"- **Python:** {report.system_info.get('python_version', 'N/A')}")
            lines.append(f"- **Working Directory:** {report.system_info.get('working_directory', 'N/A')}")
            lines.append("")

            # Write to file
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))

            logger.info(f"Markdown report saved to: {output_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to save Markdown report: {e}")
            return False

    async def generate_and_save_report(
        self,
        output_directory: str,
        formats: List[ReportFormat] = None,
        build_results: List[BuildResult] = None,
        python_result: Optional[ModuleImportResult] = None,
        database_results: List[DatabaseTestResult] = None,
        port_results: List[PortScanSummary] = None
    ) -> Dict[str, bool]:
        """
        Generate report and save in multiple formats

        Args:
            output_directory: Directory to save reports
            formats: List of report formats to generate
            build_results: Build verification results
            python_result: Python module verification result
            database_results: Database test results
            port_results: Port scan results

        Returns:
            Dictionary mapping format names to success status
        """
        if formats is None:
            formats = [ReportFormat.CONSOLE, ReportFormat.JSON, ReportFormat.MARKDOWN]

        # Start timing
        self._start_timing()

        # Generate report
        report = await self.generate_report(
            build_results=build_results,
            python_result=python_result,
            database_results=database_results,
            port_results=port_results
        )

        # Save in different formats
        results = {}
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        for format_type in formats:
            try:
                if format_type == ReportFormat.CONSOLE:
                    console_report = self.generate_console_report(report)
                    print(console_report)
                    results[format_type.value] = True

                elif format_type == ReportFormat.JSON:
                    output_file = Path(output_directory) / f"environment_report_{timestamp}.json"
                    success = self.save_json_report(report, str(output_file))
                    results[format_type.value] = success

                elif format_type == ReportFormat.MARKDOWN:
                    output_file = Path(output_directory) / f"environment_report_{timestamp}.md"
                    success = self.save_markdown_report(report, str(output_file))
                    results[format_type.value] = success

                else:
                    logger.warning(f"Unsupported format: {format_type}")
                    results[format_type.value] = False

            except Exception as e:
                logger.error(f"Failed to generate {format_type.value} report: {e}")
                results[format_type.value] = False

        return results