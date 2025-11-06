"""
Dependency Report Generation Module

This module provides comprehensive dependency reporting capabilities
including formatted reports, installation suggestions, and export functionality.
"""

import os
import json
import datetime
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from pathlib import Path
import tempfile

from utils.logger import get_logger
from core.dependency_checker import (
    DependencyInfo, DependencyStatus, DependencyType,
    VersionInfo, VersionComparator
)
from utils.network_utils import (
    NetworkInfo, NetworkStatus, PackageManagerStatus, PackageManagerType
)

logger = get_logger(__name__)


@dataclass
class InstallationSuggestion:
    """Installation suggestion for a missing dependency"""
    dependency_name: str
    dependency_type: DependencyType
    platform: str
    install_commands: List[str]
    download_urls: List[str]
    alternative_options: List[str]
    notes: List[str]


@dataclass
class DependencyReportSummary:
    """Summary of dependency check results"""
    total_dependencies: int
    installed_count: int
    missing_count: int
    version_mismatch_count: int
    inaccessible_count: int
    network_accessible: bool
    package_managers_accessible: Dict[str, bool]
    critical_issues: List[str]
    recommendations: List[str]


@dataclass
class DependencyReport:
    """Complete dependency report with all information"""
    timestamp: datetime.datetime
    operating_system: str
    python_version: str
    dependency_summary: DependencyReportSummary
    dependencies: Dict[str, DependencyInfo]
    network_info: Optional[NetworkInfo] = None
    installation_suggestions: List[InstallationSuggestion] = None
    raw_data: Dict[str, Any] = None

    def __post_init__(self):
        if self.installation_suggestions is None:
            self.installation_suggestions = []
        if self.raw_data is None:
            self.raw_data = {}


class DependencyReporter:
    """
    Main class for generating comprehensive dependency reports
    with installation suggestions and export capabilities.
    """

    # Installation instructions by platform and dependency type
    INSTALLATION_GUIDES = {
        "windows": {
            DependencyType.NODEJS: {
                "commands": [
                    "winget install OpenJS.NodeJS",
                    "choco install nodejs --version=18.17.0",
                    "scoop install node"
                ],
                "download_urls": [
                    "https://nodejs.org/en/download/",
                    "https://github.com/nodejs/node/releases"
                ],
                "alternatives": [
                    "Use Node Version Manager (nvm-windows)",
                    "Download from official Node.js website"
                ],
                "notes": [
                    "Node.js 16.0.0 or higher is required",
                    "NPM is included with Node.js installation",
                    "Add Node.js to PATH during installation"
                ]
            },
            DependencyType.PYTHON: {
                "commands": [
                    "winget install Python.Python.3.11",
                    "choco install python --version=3.11.5",
                    "pyenv install 3.11.5"
                ],
                "download_urls": [
                    "https://www.python.org/downloads/windows/",
                    "https://github.com/python/cpython/releases"
                ],
                "alternatives": [
                    "Use Microsoft Store Python installation",
                    "Download from python.org",
                    "Use conda/miniconda"
                ],
                "notes": [
                    "Python 3.8 or higher is required",
                    "Check 'Add Python to PATH' during installation",
                    "pip is included with Python 3.4+"
                ]
            },
            DependencyType.GIT: {
                "commands": [
                    "winget install Git.Git",
                    "choco install git",
                    "scoop install git"
                ],
                "download_urls": [
                    "https://git-scm.com/download/win",
                    "https://github.com/git-for-windows/git/releases"
                ],
                "alternatives": [
                    "Use GitHub Desktop (includes Git)",
                    "Download from git-scm.com"
                ],
                "notes": [
                    "Git 2.30 or higher is required",
                    "Configure user.name and user.email after installation",
                    "Choose Git Bash integration if available"
                ]
            }
        },
        "macos": {
            DependencyType.NODEJS: {
                "commands": [
                    "brew install node@18",
                    "brew install node",
                    "curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash",
                    "nvm install 18"
                ],
                "download_urls": [
                    "https://nodejs.org/en/download/",
                    "https://github.com/nodejs/node/releases"
                ],
                "alternatives": [
                    "Use Homebrew",
                    "Use Node Version Manager (nvm)",
                    "Download from official Node.js website"
                ],
                "notes": [
                    "Node.js 16.0.0 or higher is required",
                    "nvm is recommended for version management",
                    "Update PATH after nvm installation"
                ]
            },
            DependencyType.PYTHON: {
                "commands": [
                    "brew install python@3.11",
                    "brew install python",
                    "pyenv install 3.11.5"
                ],
                "download_urls": [
                    "https://www.python.org/downloads/macos/",
                    "https://github.com/python/cpython/releases"
                ],
                "alternatives": [
                    "Use Homebrew",
                    "Use pyenv for version management",
                    "Download from python.org"
                ],
                "notes": [
                    "Python 3.8 or higher is required",
                    "macOS includes Python 2.7, but Python 3.x is needed",
                    "Use python3 command to avoid conflicts with system Python"
                ]
            },
            DependencyType.GIT: {
                "commands": [
                    "brew install git",
                    "xcode-select --install"
                ],
                "download_urls": [
                    "https://git-scm.com/download/mac",
                    "https://github.com/git/git/releases"
                ],
                "alternatives": [
                    "Use Xcode Command Line Tools",
                    "Download from git-scm.com"
                ],
                "notes": [
                    "Git 2.30 or higher is required",
                    "Xcode Command Line Tools includes Git",
                    "Configure Git after installation"
                ]
            }
        },
        "linux": {
            DependencyType.NODEJS: {
                "commands": [
                    "curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -",
                    "sudo apt-get install -y nodejs",
                    "sudo yum install -y nodejs npm",
                    "sudo dnf install -y nodejs npm"
                ],
                "download_urls": [
                    "https://nodejs.org/en/download/",
                    "https://github.com/nodesource/distributions"
                ],
                "alternatives": [
                    "Use distribution package manager",
                    "Use Node Version Manager (nvm)",
                    "Download from official Node.js website"
                ],
                "notes": [
                    "Node.js 16.0.0 or higher is required",
                    "Some distributions have old Node.js versions",
                    "Consider using nvm for version management"
                ]
            },
            DependencyType.PYTHON: {
                "commands": [
                    "sudo apt-get update && sudo apt-get install -y python3.11 python3-pip",
                    "sudo yum install -y python3 python3-pip",
                    "sudo dnf install -y python3 python3-pip"
                ],
                "download_urls": [
                    "https://www.python.org/downloads/source/",
                    "https://github.com/python/cpython/releases"
                ],
                "alternatives": [
                    "Use distribution package manager",
                    "Use pyenv for version management",
                    "Compile from source"
                ],
                "notes": [
                    "Python 3.8 or higher is required",
                    "Use python3 and pip3 commands",
                    "Install python3-pip separately on some systems"
                ]
            },
            DependencyType.GIT: {
                "commands": [
                    "sudo apt-get update && sudo apt-get install -y git",
                    "sudo yum install -y git",
                    "sudo dnf install -y git"
                ],
                "download_urls": [
                    "https://git-scm.com/download/linux",
                    "https://github.com/git/git/releases"
                ],
                "alternatives": [
                    "Use distribution package manager",
                    "Compile from source"
                ],
                "notes": [
                    "Git 2.30 or higher is required",
                    "Configure Git user.name and user.email after installation",
                    "Some distributions have old Git versions"
                ]
            }
        }
    }

    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)

    def _get_platform_name(self) -> str:
        """Get platform name for installation guides"""
        import platform
        system = platform.system().lower()
        if system == "windows":
            return "windows"
        elif system == "darwin":
            return "macos"
        elif system == "linux":
            return "linux"
        else:
            return "linux"  # Default to Linux for unknown systems

    def generate_installation_suggestion(self, dependency_info: DependencyInfo) -> InstallationSuggestion:
        """
        Generate installation suggestion for a dependency.

        Args:
            dependency_info: Dependency information

        Returns:
            InstallationSuggestion with installation guidance
        """
        platform_name = self._get_platform_name()
        guides = self.INSTALLATION_GUIDES.get(platform_name, {}).get(dependency_info.type, {})

        suggestion = InstallationSuggestion(
            dependency_name=dependency_info.name,
            dependency_type=dependency_info.type,
            platform=platform_name,
            install_commands=guides.get("commands", []),
            download_urls=guides.get("download_urls", []),
            alternative_options=guides.get("alternatives", []),
            notes=guides.get("notes", [])
        )

        return suggestion

    def analyze_dependencies(self, dependencies: Dict[DependencyType, DependencyInfo]) -> DependencyReportSummary:
        """
        Analyze dependency check results and create summary.

        Args:
            dependencies: Dictionary of dependency information

        Returns:
            Summary of dependency analysis
        """
        total = len(dependencies)
        installed = 0
        missing = 0
        version_mismatch = 0
        inaccessible = 0
        critical_issues = []
        recommendations = []

        for dep_type, dep_info in dependencies.items():
            if dep_info.status == DependencyStatus.INSTALLED:
                installed += 1
            elif dep_info.status == DependencyStatus.NOT_INSTALLED:
                missing += 1
                critical_issues.append(f"Missing {dep_info.name}: {dep_info.error_message}")
            elif dep_info.status == DependencyStatus.VERSION_MISMATCH:
                version_mismatch += 1
                critical_issues.append(
                    f"Outdated {dep_info.name}: {dep_info.version} (required: {dep_info.min_version})"
                )
            elif dep_info.status == DependencyStatus.INACCESSIBLE:
                inaccessible += 1
                critical_issues.append(f"Inaccessible {dep_info.name}: {dep_info.error_message}")

        # Generate recommendations
        if missing > 0:
            recommendations.append(f"Install {missing} missing dependencies")
        if version_mismatch > 0:
            recommendations.append(f"Update {version_mismatch} outdated dependencies")
        if inaccessible > 0:
            recommendations.append(f"Fix {inaccessible} inaccessible dependencies")

        if total == installed:
            recommendations.append("All dependencies are properly installed and configured")

        return DependencyReportSummary(
            total_dependencies=total,
            installed_count=installed,
            missing_count=missing,
            version_mismatch_count=version_mismatch,
            inaccessible_count=inaccessible,
            network_accessible=False,  # Will be updated with network info
            package_managers_accessible={},  # Will be updated with network info
            critical_issues=critical_issues,
            recommendations=recommendations
        )

    def generate_report(self,
                       dependencies: Dict[DependencyType, DependencyInfo],
                       network_info: Optional[NetworkInfo] = None) -> DependencyReport:
        """
        Generate comprehensive dependency report.

        Args:
            dependencies: Dictionary of dependency information
            network_info: Network connectivity information

        Returns:
            Complete dependency report
        """
        self.logger.info("Generating dependency report...")

        timestamp = datetime.datetime.now()

        # Get platform and Python info
        import platform
        operating_system = f"{platform.system()} {platform.release()}"
        python_version = platform.python_version()

        # Analyze dependencies
        dependency_summary = self.analyze_dependencies(dependencies)

        # Update network info in summary
        if network_info:
            dependency_summary.network_accessible = network_info.internet_connected
            dependency_summary.package_managers_accessible = {
                pm_type.value: pm_status.accessible
                for pm_type, pm_status in network_info.package_managers.items()
            }

        # Generate installation suggestions for missing/problematic dependencies
        installation_suggestions = []
        for dep_type, dep_info in dependencies.items():
            if dep_info.status != DependencyStatus.INSTALLED:
                suggestion = self.generate_installation_suggestion(dep_info)
                installation_suggestions.append(suggestion)

        # Prepare raw data
        raw_data = {
            "dependencies": {
                dep_type.value: asdict(dep_info)
                for dep_type, dep_info in dependencies.items()
            },
            "network_info": asdict(network_info) if network_info else None,
            "platform_info": {
                "system": platform.system(),
                "release": platform.release(),
                "version": platform.version(),
                "machine": platform.machine(),
                "processor": platform.processor()
            }
        }

        report = DependencyReport(
            timestamp=timestamp,
            operating_system=operating_system,
            python_version=python_version,
            dependency_summary=dependency_summary,
            dependencies={
                dep_type.value: dep_info
                for dep_type, dep_info in dependencies.items()
            },
            network_info=network_info,
            installation_suggestions=installation_suggestions,
            raw_data=raw_data
        )

        self.logger.info(f"Report generated: {dependency_summary.installed_count}/{dependency_summary.total_dependencies} dependencies installed")
        return report

    def format_console_report(self, report: DependencyReport) -> str:
        """
        Format dependency report for console output.

        Args:
            report: Dependency report to format

        Returns:
            Formatted string for console display
        """
        lines = []
        lines.append("=" * 70)
        lines.append("DEPENDENCY CHECK REPORT")
        lines.append("=" * 70)
        lines.append(f"Generated: {report.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"Operating System: {report.operating_system}")
        lines.append(f"Python Version: {report.python_version}")
        lines.append("")

        # Summary section
        summary = report.dependency_summary
        lines.append("SUMMARY")
        lines.append("-" * 30)
        lines.append(f"Total Dependencies: {summary.total_dependencies}")
        lines.append(f"✓ Installed: {summary.installed_count}")
        lines.append(f"✗ Missing: {summary.missing_count}")
        lines.append(f"⚠ Outdated: {summary.version_mismatch_count}")
        lines.append(f"❌ Inaccessible: {summary.inaccessible_count}")
        lines.append(f"🌐 Network Access: {'✓' if summary.network_accessible else '✗'}")
        lines.append("")

        # Package manager accessibility
        if summary.package_managers_accessible:
            lines.append("PACKAGE MANAGER ACCESSIBILITY")
            lines.append("-" * 30)
            for pm_name, accessible in summary.package_managers_accessible.items():
                status = "✓" if accessible else "✗"
                lines.append(f"{status} {pm_name}")
            lines.append("")

        # Dependencies section
        lines.append("DEPENDENCIES")
        lines.append("-" * 30)
        for dep_name, dep_info in report.dependencies.items():
            status_icon = {
                DependencyStatus.INSTALLED: "✓",
                DependencyStatus.NOT_INSTALLED: "✗",
                DependencyStatus.VERSION_MISMATCH: "⚠",
                DependencyStatus.INACCESSIBLE: "❌",
                DependencyStatus.UNKNOWN: "?"
            }.get(dep_info.status, "?")

            version_str = str(dep_info.version) if dep_info.version else "Unknown"
            lines.append(f"{status_icon} {dep_name}: {version_str}")

            if dep_info.status != DependencyStatus.INSTALLED:
                lines.append(f"   └─ {dep_info.error_message}")
            elif dep_info.executable_path:
                lines.append(f"   └─ {dep_info.executable_path}")
        lines.append("")

        # Issues and recommendations
        if summary.critical_issues:
            lines.append("CRITICAL ISSUES")
            lines.append("-" * 30)
            for issue in summary.critical_issues:
                lines.append(f"❌ {issue}")
            lines.append("")

        if summary.recommendations:
            lines.append("RECOMMENDATIONS")
            lines.append("-" * 30)
            for rec in summary.recommendations:
                lines.append(f"💡 {rec}")
            lines.append("")

        # Installation suggestions
        if report.installation_suggestions:
            lines.append("INSTALLATION SUGGESTIONS")
            lines.append("-" * 30)
            for suggestion in report.installation_suggestions:
                lines.append(f"📦 {suggestion.dependency_name} ({suggestion.platform})")
                if suggestion.install_commands:
                    lines.append("   Commands:")
                    for cmd in suggestion.install_commands:
                        lines.append(f"     {cmd}")
                if suggestion.download_urls:
                    lines.append("   Download:")
                    for url in suggestion.download_urls[:2]:  # Limit URLs
                        lines.append(f"     {url}")
                if suggestion.notes:
                    for note in suggestion.notes[:2]:  # Limit notes
                        lines.append(f"   ℹ️  {note}")
                lines.append("")

        lines.append("=" * 70)

        return "\n".join(lines)

    def format_json_report(self, report: DependencyReport) -> str:
        """
        Format dependency report as JSON.

        Args:
            report: Dependency report to format

        Returns:
            JSON string representation
        """
        def custom_serializer(obj):
            if isinstance(obj, datetime.datetime):
                return obj.isoformat()
            elif hasattr(obj, '__dict__'):
                return asdict(obj)
            else:
                return str(obj)

        report_dict = asdict(report)
        return json.dumps(report_dict, indent=2, default=custom_serializer)

    def export_report(self,
                     report: DependencyReport,
                     file_path: Optional[str] = None,
                     format_type: str = "json") -> str:
        """
        Export dependency report to file.

        Args:
            report: Dependency report to export
            file_path: Output file path (auto-generated if None)
            format_type: Export format ("json", "txt", "both")

        Returns:
            Path to exported file(s)
        """
        if not file_path:
            timestamp = report.timestamp.strftime("%Y%m%d_%H%M%S")
            base_name = f"dependency_report_{timestamp}"

            if format_type == "both":
                # Export both formats
                json_path = os.path.join(tempfile.gettempdir(), f"{base_name}.json")
                txt_path = os.path.join(tempfile.gettempdir(), f"{base_name}.txt")

                # Export JSON
                with open(json_path, 'w', encoding='utf-8') as f:
                    f.write(self.format_json_report(report))

                # Export text
                with open(txt_path, 'w', encoding='utf-8') as f:
                    f.write(self.format_console_report(report))

                self.logger.info(f"Reports exported: {json_path}, {txt_path}")
                return f"{json_path}, {txt_path}"

            else:
                # Single format
                extension = "json" if format_type == "json" else "txt"
                file_path = os.path.join(tempfile.gettempdir(), f"{base_name}.{extension}")

        # Export single file
        if format_type == "json":
            content = self.format_json_report(report)
        else:
            content = self.format_console_report(report)

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        self.logger.info(f"Report exported: {file_path}")
        return file_path

    def print_report(self, report: DependencyReport) -> None:
        """
        Print dependency report to console.

        Args:
            report: Dependency report to print
        """
        console_report = self.format_console_report(report)
        print(console_report)