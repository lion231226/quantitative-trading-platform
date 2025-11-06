"""
Environment Detection and Dependency Analysis Module

This module provides comprehensive environment detection capabilities
including system analysis, dependency checking, and compatibility validation.
"""

import os
import sys
import platform
import subprocess
import re
import shutil
from typing import Dict, List, Optional, Tuple, Union, Set
from dataclasses import dataclass
from enum import Enum
import json
from pathlib import Path


class DependencyType(Enum):
    """Types of dependencies to detect"""
    RUNTIME = "runtime"
    DEVELOPMENT = "development"
    SYSTEM = "system"
    OPTIONAL = "optional"


class DependencyStatus(Enum):
    """Status of a dependency"""
    INSTALLED = "installed"
    MISSING = "missing"
    VERSION_MISMATCH = "version_mismatch"
    INCOMPATIBLE = "incompatible"
    UNKNOWN = "unknown"


@dataclass
class Dependency:
    """Represents a system dependency"""
    name: str
    type: DependencyType
    required_version: Optional[str] = None
    installed_version: Optional[str] = None
    status: DependencyStatus = DependencyStatus.UNKNOWN
    install_command: Optional[str] = None
    check_command: Optional[str] = None
    description: Optional[str] = None


@dataclass
class SystemInfo:
    """System information"""
    os_name: str
    os_version: str
    architecture: str
    cpu_count: int
    memory_gb: float
    disk_space_gb: float
    python_version: str
    available_ports: List[int]


@dataclass
class EnvironmentReport:
    """Complete environment detection report"""
    system_info: SystemInfo
    dependencies: Dict[str, Dependency]
    missing_dependencies: List[str]
    occupied_ports: Dict[int, str]
    is_environment_ready: bool
    issues: List[str]
    recommendations: List[str]


class EnvironmentDetector:
    """Comprehensive environment detection and analysis"""

    def __init__(self):
        self.logger = self._setup_logger()
        self._known_dependencies = self._initialize_dependency_database()

    def _setup_logger(self):
        """Setup logging for environment detection"""
        import logging
        logger = logging.getLogger(__name__)
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger

    def _initialize_dependency_database(self) -> Dict[str, Dependency]:
        """Initialize known dependencies database"""
        return {
            # Runtime dependencies
            "python": Dependency(
                name="python",
                type=DependencyType.RUNTIME,
                required_version=">=3.8.0",
                check_command="python --version",
                install_command="Visit https://python.org",
                description="Python programming language runtime"
            ),
            "node": Dependency(
                name="node",
                type=DependencyType.RUNTIME,
                required_version=">=16.0.0",
                check_command="node --version",
                install_command="Visit https://nodejs.org",
                description="Node.js JavaScript runtime"
            ),
            "npm": Dependency(
                name="npm",
                type=DependencyType.RUNTIME,
                required_version=">=8.0.0",
                check_command="npm --version",
                install_command="Installed with Node.js",
                description="Node.js package manager"
            ),

            # System dependencies
            "git": Dependency(
                name="git",
                type=DependencyType.SYSTEM,
                required_version=">=2.0.0",
                check_command="git --version",
                install_command="Visit https://git-scm.com",
                description="Git version control system"
            ),
            "redis": Dependency(
                name="redis",
                type=DependencyType.SYSTEM,
                required_version=">=6.0.0",
                check_command="redis-server --version",
                install_command="Visit https://redis.io",
                description="Redis in-memory data store"
            ),
            "postgresql": Dependency(
                name="postgresql",
                type=DependencyType.SYSTEM,
                required_version=">=12.0.0",
                check_command="psql --version",
                install_command="Visit https://postgresql.org",
                description="PostgreSQL database system"
            ),

            # Development dependencies
            "pip": Dependency(
                name="pip",
                type=DependencyType.DEVELOPMENT,
                required_version=">=21.0.0",
                check_command="pip --version",
                install_command="python -m ensurepip --upgrade",
                description="Python package installer"
            ),
            "virtualenv": Dependency(
                name="virtualenv",
                type=DependencyType.DEVELOPMENT,
                required_version=">=20.0.0",
                check_command="virtualenv --version",
                install_command="pip install virtualenv",
                description="Python virtual environment creator"
            ),
        }

    def detect_all(self) -> EnvironmentReport:
        """
        Perform complete environment detection

        Returns:
            EnvironmentReport: Comprehensive environment analysis
        """
        self.logger.info("Starting comprehensive environment detection...")

        # Detect system information
        system_info = self._detect_system_info()

        # Check all dependencies
        dependencies = self._check_all_dependencies()

        # Find missing dependencies
        missing_dependencies = [
            name for name, dep in dependencies.items()
            if dep.status in [DependencyStatus.MISSING, DependencyStatus.INCOMPATIBLE]
        ]

        # Check occupied ports
        occupied_ports = self._check_occupied_ports()

        # Determine environment readiness
        is_ready = len(missing_dependencies) == 0

        # Generate issues and recommendations
        issues, recommendations = self._analyze_environment(
            system_info, dependencies, occupied_ports
        )

        report = EnvironmentReport(
            system_info=system_info,
            dependencies=dependencies,
            missing_dependencies=missing_dependencies,
            occupied_ports=occupied_ports,
            is_environment_ready=is_ready,
            issues=issues,
            recommendations=recommendations
        )

        self.logger.info(f"Environment detection complete. Ready: {is_ready}")
        return report

    def _detect_system_info(self) -> SystemInfo:
        """Detect basic system information"""
        try:
            # OS information
            os_name = platform.system()
            os_version = platform.version()
            architecture = platform.machine()

            # CPU information
            cpu_count = os.cpu_count() or 1

            # Memory information
            try:
                if os_name == "Windows":
                    import psutil
                    memory_bytes = psutil.virtual_memory().total
                    memory_gb = memory_bytes / (1024**3)
                else:
                    # Try to get memory from /proc/meminfo on Unix-like systems
                    with open('/proc/meminfo', 'r') as f:
                        for line in f:
                            if line.startswith('MemTotal:'):
                                memory_kb = int(line.split()[1])
                                memory_gb = memory_kb / (1024**2)
                                break
                        else:
                            memory_gb = 4.0  # Default fallback
            except:
                memory_gb = 4.0  # Default fallback

            # Disk space
            try:
                current_path = Path.cwd()
                disk_usage = shutil.disk_usage(current_path)
                disk_space_gb = disk_usage.free / (1024**3)
            except:
                disk_space_gb = 10.0  # Default fallback

            # Python version
            python_version = platform.python_version()

            # Available ports (common ports to check)
            available_ports = self._scan_available_ports()

            return SystemInfo(
                os_name=os_name,
                os_version=os_version,
                architecture=architecture,
                cpu_count=cpu_count,
                memory_gb=memory_gb,
                disk_space_gb=disk_space_gb,
                python_version=python_version,
                available_ports=available_ports
            )

        except Exception as e:
            self.logger.error(f"Error detecting system info: {e}")
            return SystemInfo(
                os_name="Unknown",
                os_version="Unknown",
                architecture="Unknown",
                cpu_count=1,
                memory_gb=4.0,
                disk_space_gb=10.0,
                python_version=platform.python_version(),
                available_ports=[]
            )

    def _check_all_dependencies(self) -> Dict[str, Dependency]:
        """Check all known dependencies"""
        dependencies = {}

        for name, dep_template in self._known_dependencies.items():
            dependency = self._check_dependency(dep_template)
            dependencies[name] = dependency

        return dependencies

    def _check_dependency(self, dependency: Dependency) -> Dependency:
        """Check a single dependency"""
        try:
            if dependency.check_command:
                result = subprocess.run(
                    dependency.check_command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=10
                )

                if result.returncode == 0:
                    dependency.status = DependencyStatus.INSTALLED
                    # Extract version from output
                    dependency.installed_version = self._extract_version(
                        result.stdout or result.stderr
                    )

                    # Check version compatibility
                    if dependency.required_version:
                        if not self._is_version_compatible(
                            dependency.installed_version,
                            dependency.required_version
                        ):
                            dependency.status = DependencyStatus.VERSION_MISMATCH
                else:
                    dependency.status = DependencyStatus.MISSING
            else:
                dependency.status = DependencyStatus.UNKNOWN

        except subprocess.TimeoutExpired:
            dependency.status = DependencyStatus.UNKNOWN
        except Exception as e:
            self.logger.warning(f"Error checking dependency {dependency.name}: {e}")
            dependency.status = DependencyStatus.UNKNOWN

        return dependency

    def _extract_version(self, output: str) -> Optional[str]:
        """Extract version string from command output"""
        # Common version patterns
        patterns = [
            r'\d+\.\d+\.\d+',  # x.y.z
            r'\d+\.\d+',        # x.y
            r'v\d+\.\d+\.\d+',  # vx.y.z
        ]

        for pattern in patterns:
            match = re.search(pattern, output)
            if match:
                return match.group(0)

        return None

    def _is_version_compatible(self, installed: str, required: str) -> bool:
        """Check if installed version meets requirements"""
        try:
            # Simple version comparison (can be enhanced)
            if installed and required:
                installed_parts = [int(x) for x in installed.split('.') if x.isdigit()]
                required_parts = [int(x) for x in required.split('.') if x.isdigit()]

                # Pad shorter version with zeros
                max_len = max(len(installed_parts), len(required_parts))
                installed_parts.extend([0] * (max_len - len(installed_parts)))
                required_parts.extend([0] * (max_len - len(required_parts)))

                return installed_parts >= required_parts
        except:
            pass

        return True  # Assume compatible if can't determine

    def _check_occupied_ports(self) -> Dict[int, str]:
        """Check commonly used ports"""
        common_ports = [3000, 3001, 8000, 8001, 6379, 5432, 27017]
        occupied_ports = {}

        for port in common_ports:
            try:
                import socket
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                result = sock.connect_ex(('localhost', port))
                sock.close()

                if result == 0:
                    occupied_ports[port] = "Occupied"
            except:
                pass

        return occupied_ports

    def _scan_available_ports(self) -> List[int]:
        """Scan for available ports"""
        available_ports = []

        for port in range(3000, 3010):
            if port not in self._check_occupied_ports():
                available_ports.append(port)

        for port in range(8000, 8010):
            if port not in self._check_occupied_ports():
                available_ports.append(port)

        return available_ports[:5]  # Return first 5 available ports

    def _analyze_environment(
        self,
        system_info: SystemInfo,
        dependencies: Dict[str, Dependency],
        occupied_ports: Dict[int, str]
    ) -> Tuple[List[str], List[str]]:
        """Analyze environment and generate issues/recommendations"""
        issues = []
        recommendations = []

        # Check memory
        if system_info.memory_gb < 4:
            issues.append("Low memory detected (< 4GB)")
            recommendations.append("Consider upgrading to at least 8GB RAM")

        # Check disk space
        if system_info.disk_space_gb < 5:
            issues.append("Low disk space detected (< 5GB available)")
            recommendations.append("Free up disk space or use a different location")

        # Check Python version
        if system_info.python_version:
            try:
                version_parts = [int(x) for x in system_info.python_version.split('.')]
                if version_parts < [3, 8]:
                    issues.append(f"Python {system_info.python_version} is outdated")
                    recommendations.append("Upgrade to Python 3.8 or higher")
            except:
                issues.append("Unable to determine Python version compatibility")

        # Check missing dependencies
        missing_count = len([
            dep for dep in dependencies.values()
            if dep.status == DependencyStatus.MISSING
        ])

        if missing_count > 0:
            issues.append(f"{missing_count} required dependencies are missing")
            recommendations.append("Install missing dependencies using provided commands")

        # Check port conflicts
        if occupied_ports:
            conflict_ports = [port for port in occupied_ports.keys() if port in [3000, 8000, 6379, 5432]]
            if conflict_ports:
                issues.append(f"Port conflicts detected: {conflict_ports}")
                recommendations.append("Stop conflicting services or use alternative ports")

        return issues, recommendations

    def get_missing_dependencies(self) -> List[str]:
        """
        Get list of missing dependencies

        Returns:
            List[str]: Names of missing dependencies
        """
        report = self.detect_all()
        return report.missing_dependencies

    def get_occupied_ports(self) -> Dict[int, str]:
        """
        Get occupied ports

        Returns:
            Dict[int, str]: Port number and description
        """
        report = self.detect_all()
        return report.occupied_ports

    def is_environment_ready(self) -> bool:
        """
        Check if environment is ready for launch

        Returns:
            bool: True if environment is ready
        """
        report = self.detect_all()
        return report.is_environment_ready

    def get_dependency_info(self, dependency_name: str) -> Optional[Dependency]:
        """
        Get information about a specific dependency

        Args:
            dependency_name: Name of the dependency

        Returns:
            Optional[Dependency]: Dependency information if found
        """
        report = self.detect_all()
        return report.dependencies.get(dependency_name)

    def generate_install_script(self) -> str:
        """
        Generate installation script for missing dependencies

        Returns:
            str: Installation script content
        """
        report = self.detect_all()
        missing_deps = [
            dep for dep in report.dependencies.values()
            if dep.status == DependencyStatus.MISSING and dep.install_command
        ]

        if not missing_deps:
            return "# All dependencies are already installed\n"

        script_lines = [
            "#!/bin/bash",
            "# Auto-generated dependency installation script",
            "",
            "echo 'Installing missing dependencies...'",
            ""
        ]

        for dep in missing_deps:
            script_lines.extend([
                f"echo 'Installing {dep.name}...'",
                f"# {dep.description or ''}",
                f"{dep.install_command}",
                "echo ''"
            ])

        script_lines.extend([
            "echo 'Dependency installation complete.'",
            "echo 'Please verify installations and run the launcher again.'"
        ])

        return '\n'.join(script_lines)


# Convenience functions for backward compatibility
def detect_environment() -> EnvironmentReport:
    """Convenience function to detect environment"""
    detector = EnvironmentDetector()
    return detector.detect_all()


def check_dependencies() -> Dict[str, Dependency]:
    """Convenience function to check dependencies"""
    detector = EnvironmentDetector()
    report = detector.detect_all()
    return report.dependencies


def is_ready() -> bool:
    """Convenience function to check if environment is ready"""
    detector = EnvironmentDetector()
    return detector.is_environment_ready()