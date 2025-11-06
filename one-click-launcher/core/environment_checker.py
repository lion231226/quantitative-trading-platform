"""
Integrated Environment Checker Module

This module provides comprehensive environment checking by integrating
operating system detection with dependency checking and network validation.
"""

import asyncio
import platform
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import datetime

from core.operating_system_detector import OperatingSystemDetector, SystemInfo, OperatingSystem
from core.dependency_checker import DependencyChecker, DependencyType, DependencyInfo
from utils.network_utils import NetworkChecker, NetworkInfo
from core.dependency_reporter import DependencyReporter, DependencyReport
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class EnvironmentCheckResult:
    """Complete environment check result"""
    timestamp: datetime.datetime
    os_info: SystemInfo
    dependency_report: DependencyReport
    network_info: NetworkInfo
    overall_status: str
    critical_issues: List[str]
    recommendations: List[str]
    is_ready_for_development: bool


class EnvironmentChecker:
    """
    Integrated environment checker that combines OS detection,
    dependency checking, and network validation.
    """

    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
        self.os_detector = OperatingSystemDetector()
        self.dependency_checker = None  # Will be initialized after OS detection
        self.network_checker = NetworkChecker()
        self.reporter = DependencyReporter()

    async def check_environment(self, include_network_check: bool = True) -> EnvironmentCheckResult:
        """
        Perform comprehensive environment check.

        Args:
            include_network_check: Whether to perform network connectivity checks

        Returns:
            Complete environment check result
        """
        self.logger.info("Starting comprehensive environment check...")
        timestamp = datetime.datetime.now()

        # Step 1: Detect operating system
        self.logger.info("Step 1: Detecting operating system...")
        os_info = self.os_detector.detect_os_info()
        self.logger.info(f"OS detected: {os_info.os_type.value} {os_info.version}")

        # Step 2: Initialize dependency checker with detected OS
        self.dependency_checker = DependencyChecker(os_info.os_type)

        # Step 3: Check dependencies
        self.logger.info("Step 2: Checking dependencies...")
        dependencies = self.dependency_checker.check_all_dependencies()

        # Step 4: Check network connectivity (if requested)
        network_info = None
        if include_network_check:
            self.logger.info("Step 3: Checking network connectivity...")
            try:
                network_info = await self.network_checker.get_comprehensive_network_info()
            except Exception as e:
                self.logger.error(f"Network check failed: {e}")
                network_info = NetworkInfo(
                    status=NetworkStatus.UNKNOWN,
                    internet_connected=False,
                    proxy_config=self.network_checker.detect_proxy_config(),
                    package_managers={}
                )

        # Step 5: Generate dependency report
        self.logger.info("Step 4: Generating report...")
        dependency_report = self.reporter.generate_report(dependencies, network_info)

        # Step 6: Analyze results and provide recommendations
        overall_status, critical_issues, recommendations = self._analyze_results(
            os_info, dependency_report, network_info
        )

        is_ready = (
            len(critical_issues) == 0 and
            dependency_report.dependency_summary.installed_count == dependency_report.dependency_summary.total_dependencies
        )

        result = EnvironmentCheckResult(
            timestamp=timestamp,
            os_info=os_info,
            dependency_report=dependency_report,
            network_info=network_info,
            overall_status=overall_status,
            critical_issues=critical_issues,
            recommendations=recommendations,
            is_ready_for_development=is_ready
        )

        self.logger.info(f"Environment check completed. Status: {overall_status}, Ready for development: {is_ready}")
        return result

    def _analyze_results(self,
                        os_info: SystemInfo,
                        dependency_report: DependencyReport,
                        network_info: Optional[NetworkInfo]) -> Tuple[str, List[str], List[str]]:
        """
        Analyze check results and determine overall status.

        Args:
            os_info: Operating system information
            dependency_report: Dependency check report
            network_info: Network check information

        Returns:
            Tuple of (overall_status, critical_issues, recommendations)
        """
        critical_issues = []
        recommendations = []

        # Check OS compatibility
        if os_info.os_type == OperatingSystem.UNKNOWN:
            critical_issues.append("Unsupported or unknown operating system")
        elif not os_info.is_supported:
            critical_issues.append(f"Unsupported {os_info.os_type.value} version: {os_info.version}")

        # Check dependency status
        summary = dependency_report.dependency_summary

        if summary.missing_count > 0:
            critical_issues.append(f"{summary.missing_count} critical dependencies are missing")

        if summary.version_mismatch_count > 0:
            critical_issues.append(f"{summary.version_mismatch_count} dependencies have version mismatches")

        if summary.inaccessible_count > 0:
            critical_issues.append(f"{summary.inaccessible_count} dependencies are inaccessible")

        # Check network status if available
        if network_info:
            if not network_info.internet_connected:
                critical_issues.append("No internet connectivity detected")

            # Check package manager accessibility
            inaccessible_pm = [
                pm_type.value for pm_type, pm_status in network_info.package_managers.items()
                if not pm_status.accessible
            ]
            if inaccessible_pm:
                critical_issues.append(f"Package managers inaccessible: {', '.join(inaccessible_pm)}")

        # Determine overall status
        if not critical_issues:
            overall_status = "READY"
        elif len(critical_issues) <= 2:
            overall_status = "NEEDS_ATTENTION"
        else:
            overall_status = "NOT_READY"

        # Add recommendations
        recommendations.extend(dependency_report.dependency_summary.recommendations)

        if overall_status != "READY":
            recommendations.append("Run the installation commands provided in the report")
            recommendations.append("Verify PATH includes all required executable directories")

        if os_info.os_type == OperatingSystem.WINDOWS:
            recommendations.append("Consider using Windows Subsystem for Linux (WSL) for better compatibility")
        elif os_info.os_type == OperatingSystem.MACOS:
            recommendations.append("Ensure Xcode Command Line Tools are installed: xcode-select --install")

        return overall_status, critical_issues, recommendations

    def check_quick_dependency_status(self) -> Dict[str, Any]:
        """
        Perform quick dependency status check without network tests.

        Returns:
            Dictionary with basic dependency status
        """
        self.logger.info("Performing quick dependency check...")

        # Detect OS
        os_info = self.os_detector.detect_os_info()

        # Check dependencies without network
        self.dependency_checker = DependencyChecker(os_info.os_type)
        dependencies = self.dependency_checker.check_all_dependencies()

        # Simple status summary
        status_summary = {}
        for dep_type, dep_info in dependencies.items():
            status_summary[dep_type.value] = {
                "status": dep_info.status.value,
                "version": str(dep_info.version) if dep_info.version else None,
                "installed": dep_info.status.value == "installed"
            }

        return {
            "os_type": os_info.os_type.value,
            "os_version": str(os_info.version),
            "dependencies": status_summary,
            "all_installed": all(dep["installed"] for dep in status_summary.values())
        }

    async def check_specific_dependency(self, dependency_type: DependencyType) -> DependencyInfo:
        """
        Check a specific dependency in detail.

        Args:
            dependency_type: Type of dependency to check

        Returns:
            Detailed dependency information
        """
        if not self.dependency_checker:
            os_info = self.os_detector.detect_system()
            self.dependency_checker = DependencyChecker(os_info.os_type)

        return self.dependency_checker.check_dependency(dependency_type)

    def get_installation_commands(self, missing_dependencies: List[str]) -> Dict[str, List[str]]:
        """
        Get installation commands for missing dependencies.

        Args:
            missing_dependencies: List of missing dependency names

        Returns:
            Dictionary mapping dependency names to installation commands
        """
        platform_name = self._get_platform_name()
        commands = {}

        with open('config/dependency-requirements.json', 'r') as f:
            import json
            config = json.load(f)

        for dep_name in missing_dependencies:
            if dep_name in config["installation_sources"]:
                platform_commands = config["installation_sources"][dep_name]["package_managers"].get(platform_name, [])
                commands[dep_name] = platform_commands

        return commands

    def _get_platform_name(self) -> str:
        """Get platform name for configuration lookup"""
        system = platform.system().lower()
        if system == "windows":
            return "windows"
        elif system == "darwin":
            return "macos"
        else:
            return "linux"

    def print_environment_summary(self, result: EnvironmentCheckResult) -> None:
        """
        Print a summary of environment check results.

        Args:
            result: Environment check result to display
        """
        print("\n" + "=" * 60)
        print("ENVIRONMENT CHECK SUMMARY")
        print("=" * 60)
        print(f"Timestamp: {result.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Operating System: {result.os_info.os_type.value} {result.os_info.version}")
        print(f"Overall Status: {result.overall_status}")
        print(f"Ready for Development: {'✓ Yes' if result.is_ready_for_development else '✗ No'}")

        # Dependencies summary
        summary = result.dependency_report.dependency_summary
        print(f"\nDependencies: {summary.installed_count}/{summary.total_dependencies} installed")
        if summary.missing_count > 0:
            print(f"  Missing: {summary.missing_count}")
        if summary.version_mismatch_count > 0:
            print(f"  Outdated: {summary.version_mismatch_count}")

        # Network status
        if result.network_info:
            print(f"Network Access: {'✓ Connected' if result.network_info.internet_connected else '✗ Disconnected'}")

        # Critical issues
        if result.critical_issues:
            print(f"\nCritical Issues ({len(result.critical_issues)}):")
            for issue in result.critical_issues:
                print(f"  ❌ {issue}")

        # Recommendations
        if result.recommendations:
            print(f"\nRecommendations:")
            for rec in result.recommendations[:5]:  # Limit to 5 recommendations
                print(f"  💡 {rec}")

        print("=" * 60)

    def export_full_report(self, result: EnvironmentCheckResult, file_path: Optional[str] = None) -> str:
        """
        Export full environment check report.

        Args:
            result: Environment check result to export
            file_path: Output file path (auto-generated if None)

        Returns:
            Path to exported report
        """
        return self.reporter.export_report(result.dependency_report, file_path, format_type="json")