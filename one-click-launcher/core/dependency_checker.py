"""
Development Environment Dependency Checker Module

This module provides comprehensive dependency checking capabilities
including version detection, path verification, and status reporting
for development tools required by the quantitative trading platform.
"""

import os
import sys
import subprocess
import platform
import re
import json
from typing import Dict, List, Optional, Tuple, Union, Any
from dataclasses import dataclass, asdict
from enum import Enum
import shutil
from pathlib import Path

from utils.logger import get_logger
from core.operating_system_detector import OperatingSystem, Architecture

logger = get_logger(__name__)


class DependencyStatus(Enum):
    """Dependency status values"""
    INSTALLED = "installed"
    NOT_INSTALLED = "not_installed"
    VERSION_MISMATCH = "version_mismatch"
    INACCESSIBLE = "inaccessible"
    UNKNOWN = "unknown"


class DependencyType(Enum):
    """Types of dependencies to check"""
    NODEJS = "nodejs"
    PYTHON = "python"
    GIT = "git"
    NPM = "npm"
    PIP = "pip"


@dataclass
class VersionInfo:
    """Version information for a dependency"""
    major: int
    minor: int
    patch: int = 0
    build: Optional[str] = None
    prerelease: Optional[str] = None

    def __str__(self) -> str:
        version_str = f"{self.major}.{self.minor}"
        if self.patch > 0:
            version_str += f".{self.patch}"
        if self.build:
            version_str += f"+{self.build}"
        if self.prerelease:
            version_str += f"-{self.prerelease}"
        return version_str

    @classmethod
    def from_string(cls, version_str: str) -> 'VersionInfo':
        """Parse version string into VersionInfo object"""
        # Remove 'v' prefix if present
        version_str = version_str.strip().lstrip('v')

        # Split version and prerelease/build parts
        main_parts = []
        prerelease = None
        build = None

        if '+' in version_str:
            version_str, build = version_str.split('+', 1)

        if '-' in version_str:
            version_str, prerelease = version_str.split('-', 1)

        # Parse main version parts
        parts = version_str.split('.')
        major = int(parts[0]) if len(parts) > 0 and parts[0].isdigit() else 0
        minor = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
        patch = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 0

        return cls(
            major=major,
            minor=minor,
            patch=patch,
            build=build,
            prerelease=prerelease
        )


@dataclass
class DependencyInfo:
    """Complete information about a dependency"""
    name: str
    type: DependencyType
    status: DependencyStatus
    version: Optional[VersionInfo] = None
    min_version: Optional[VersionInfo] = None
    install_path: Optional[str] = None
    executable_path: Optional[str] = None
    error_message: Optional[str] = None
    additional_info: Dict[str, Any] = None

    def __post_init__(self):
        if self.additional_info is None:
            self.additional_info = {}


class VersionComparator:
    """Utility class for comparing semantic versions"""

    @staticmethod
    def compare_versions(version1: Union[str, VersionInfo],
                        version2: Union[str, VersionInfo]) -> int:
        """
        Compare two versions.

        Returns:
            -1 if version1 < version2
             0 if version1 == version2
             1 if version1 > version2
        """
        # Convert to VersionInfo objects if needed
        if isinstance(version1, str):
            version1 = VersionInfo.from_string(version1)
        if isinstance(version2, str):
            version2 = VersionInfo.from_string(version2)

        # Compare major version
        if version1.major < version2.major:
            return -1
        elif version1.major > version2.major:
            return 1

        # Compare minor version
        if version1.minor < version2.minor:
            return -1
        elif version1.minor > version2.minor:
            return 1

        # Compare patch version
        if version1.patch < version2.patch:
            return -1
        elif version1.patch > version2.patch:
            return 1

        # If all numeric parts are equal, consider prerelease/build info
        # Simple comparison - in a full implementation, this would be more sophisticated
        return 0

    @staticmethod
    def meets_requirement(version: Union[str, VersionInfo],
                         min_version: Union[str, VersionInfo]) -> bool:
        """Check if version meets minimum requirement"""
        return VersionComparator.compare_versions(version, min_version) >= 0


class DependencyChecker:
    """
    Main dependency checking class that provides comprehensive
    detection and validation of development environment dependencies.
    """

    # Minimum version requirements
    MINIMUM_REQUIREMENTS = {
        DependencyType.NODEJS: VersionInfo.from_string("16.0.0"),
        DependencyType.PYTHON: VersionInfo.from_string("3.8.0"),
        DependencyType.GIT: VersionInfo.from_string("2.30.0"),
        DependencyType.NPM: VersionInfo.from_string("8.0.0"),
        DependencyType.PIP: VersionInfo.from_string("21.0.0"),
    }

    # Executable names by platform
    EXECUTABLE_NAMES = {
        OperatingSystem.WINDOWS: {
            DependencyType.NODEJS: ["node.exe"],
            DependencyType.NPM: ["npm.cmd"],
            DependencyType.PYTHON: ["python.exe", "py.exe"],
            DependencyType.PIP: ["pip.exe"],
            DependencyType.GIT: ["git.exe"],
        },
        OperatingSystem.MACOS: {
            DependencyType.NODEJS: ["node"],
            DependencyType.NPM: ["npm"],
            DependencyType.PYTHON: ["python3", "python"],
            DependencyType.PIP: ["pip3", "pip"],
            DependencyType.GIT: ["git"],
        },
        OperatingSystem.LINUX: {
            DependencyType.NODEJS: ["node", "nodejs"],
            DependencyType.NPM: ["npm"],
            DependencyType.PYTHON: ["python3", "python"],
            DependencyType.PIP: ["pip3", "pip"],
            DependencyType.GIT: ["git"],
        },
    }

    def __init__(self, operating_system: Optional[OperatingSystem] = None):
        """
        Initialize the dependency checker.

        Args:
            operating_system: Operating system to check for. If None, will auto-detect.
        """
        self.operating_system = operating_system or self._detect_os()
        self.logger = get_logger(self.__class__.__name__)
        self.checked_dependencies: Dict[DependencyType, DependencyInfo] = {}

    def _detect_os(self) -> OperatingSystem:
        """Detect the current operating system"""
        system = platform.system().lower()
        if system == "windows":
            return OperatingSystem.WINDOWS
        elif system == "darwin":
            return OperatingSystem.MACOS
        elif system == "linux":
            return OperatingSystem.LINUX
        else:
            return OperatingSystem.UNKNOWN

    def _find_executable(self, dependency_type: DependencyType) -> Optional[str]:
        """
        Find the executable path for a dependency.

        Args:
            dependency_type: Type of dependency to find

        Returns:
            Path to executable if found, None otherwise
        """
        executable_names = self.EXECUTABLE_NAMES.get(
            self.operating_system, {}
        ).get(dependency_type, [])

        for name in executable_names:
            # Try to find in PATH
            path = shutil.which(name)
            if path:
                return path

            # Try common installation paths
            common_paths = self._get_common_paths(dependency_type)
            for common_path in common_paths:
                full_path = os.path.join(common_path, name)
                if os.path.exists(full_path):
                    return full_path

        return None

    def _get_common_paths(self, dependency_type: DependencyType) -> List[str]:
        """Get common installation paths for a dependency type"""
        paths = []

        if self.operating_system == OperatingSystem.WINDOWS:
            program_files = os.environ.get("ProgramFiles", "C:\\Program Files")
            program_files_x86 = os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)")
            local_app_data = os.environ.get("LOCALAPPDATA", os.path.expanduser("~\\AppData\\Local"))
            app_data = os.environ.get("APPDATA", os.path.expanduser("~\\AppData\\Roaming"))

            if dependency_type == DependencyType.NODEJS:
                paths.extend([
                    f"{program_files}\\nodejs",
                    f"{program_files_x86}\\nodejs",
                    f"{local_app_data}\\Programs\\nodejs",
                    f"{app_data}\\npm",
                ])
            elif dependency_type == DependencyType.PYTHON:
                paths.extend([
                    f"{local_app_data}\\Programs\\Python",
                    f"{program_files}\\Python*",
                    f"{program_files_x86}\\Python*",
                ])
            elif dependency_type == DependencyType.GIT:
                paths.extend([
                    f"{program_files}\\Git\\cmd",
                    f"{program_files_x86}\\Git\\cmd",
                    f"{local_app_data}\\Programs\\Git\\cmd",
                ])

        elif self.operating_system == OperatingSystem.MACOS:
            home = os.path.expanduser("~")
            paths.extend([
                "/usr/local/bin",
                "/usr/bin",
                "/opt/homebrew/bin",
                f"{home}/.nvm/versions/node/*/bin",
                f"{home}/.pyenv/versions/*/bin",
                f"{home}/brew/bin",
            ])

        elif self.operating_system == OperatingSystem.LINUX:
            home = os.path.expanduser("~")
            paths.extend([
                "/usr/local/bin",
                "/usr/bin",
                "/snap/bin",
                f"{home}/.nvm/versions/node/*/bin",
                f"{home}/.pyenv/versions/*/bin",
                f"{home}/.local/bin",
            ])

        # Expand wildcards
        expanded_paths = []
        for path in paths:
            if '*' in path:
                try:
                    import glob
                    expanded_paths.extend(glob.glob(path))
                except:
                    expanded_paths.append(path)
            else:
                expanded_paths.append(path)

        return expanded_paths

    def _run_command(self, command: List[str], timeout: int = 10) -> Tuple[bool, str, str]:
        """
        Run a command and return success status, stdout, and stderr.

        Args:
            command: Command to run as list of strings
            timeout: Command timeout in seconds

        Returns:
            Tuple of (success, stdout, stderr)
        """
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=True
            )
            return True, result.stdout.strip(), result.stderr.strip()
        except subprocess.CalledProcessError as e:
            return False, e.stdout.strip(), e.stderr.strip()
        except subprocess.TimeoutExpired:
            return False, "", "Command timed out"
        except Exception as e:
            return False, "", str(e)

    def _parse_version_output(self, output: str, dependency_type: DependencyType) -> Optional[VersionInfo]:
        """
        Parse version output string into VersionInfo object.

        Args:
            output: Command output containing version information
            dependency_type: Type of dependency being parsed

        Returns:
            Parsed version info or None if parsing failed
        """
        output = output.strip()

        # Define regex patterns for different dependency types
        patterns = {
            DependencyType.NODEJS: [
                r'v?(\d+)\.(\d+)\.(\d+)',  # v18.17.0
                r'v?(\d+)\.(\d+)\.(\d+)-(.+)',  # v18.17.0-pre
            ],
            DependencyType.PYTHON: [
                r'Python (\d+)\.(\d+)\.(\d+)',  # Python 3.9.7
                r'Python (\d+)\.(\d+)',  # Python 3.9
            ],
            DependencyType.GIT: [
                r'git version (\d+)\.(\d+)\.(\d+)',  # git version 2.35.1
                r'git version (\d+)\.(\d+)\.(\d+)\.(\w+)',  # git version 2.35.1.windows.2
            ],
            DependencyType.NPM: [
                r'(\d+)\.(\d+)\.(\d+)',  # 8.19.2
                r'(\d+)\.(\d+)\.(\d+)-(.+)',  # 8.19.2-pre
            ],
            DependencyType.PIP: [
                r'pip (\d+)\.(\d+)\.(\d+)',  # pip 22.0.4
                r'pip (\d+)\.(\d+)\.(\d+) from',  # pip 22.0.4 from ...
            ],
        }

        for pattern in patterns.get(dependency_type, []):
            match = re.search(pattern, output, re.IGNORECASE)
            if match:
                try:
                    version_str = match.group(0)
                    # Extract just the version part
                    version_match = re.search(r'(\d+\.\d+\.\d+(?:[+-][\w\.]+)?)', version_str)
                    if version_match:
                        return VersionInfo.from_string(version_match.group(1))
                except Exception as e:
                    self.logger.debug(f"Failed to parse version with pattern '{pattern}': {e}")
                    continue

        self.logger.warning(f"Could not parse version from output: {output}")
        return None

    def check_nodejs(self) -> DependencyInfo:
        """Check Node.js installation and version"""
        self.logger.info("Checking Node.js installation...")

        dependency_info = DependencyInfo(
            name="Node.js",
            type=DependencyType.NODEJS,
            status=DependencyStatus.UNKNOWN,  # Will be updated based on checks
            min_version=self.MINIMUM_REQUIREMENTS[DependencyType.NODEJS]
        )

        # Find executable
        executable_path = self._find_executable(DependencyType.NODEJS)
        if not executable_path:
            dependency_info = DependencyInfo(
                name="Node.js",
                type=DependencyType.NODEJS,
                status=DependencyStatus.NOT_INSTALLED,
                min_version=self.MINIMUM_REQUIREMENTS[DependencyType.NODEJS],
                error_message="Node.js executable not found in PATH or common installation directories"
            )
            return dependency_info

        dependency_info.executable_path = executable_path

        # Get version
        success, stdout, stderr = self._run_command([executable_path, "--version"])
        if not success:
            dependency_info.status = DependencyStatus.INACCESSIBLE
            dependency_info.error_message = f"Failed to get Node.js version: {stderr}"
            return dependency_info

        version = self._parse_version_output(stdout, DependencyType.NODEJS)
        if not version:
            dependency_info.status = DependencyStatus.UNKNOWN
            dependency_info.error_message = f"Could not parse Node.js version from: {stdout}"
            return dependency_info

        dependency_info.version = version

        # Check version requirement
        if not VersionComparator.meets_requirement(version, dependency_info.min_version):
            dependency_info.status = DependencyStatus.VERSION_MISMATCH
            dependency_info.error_message = (
                f"Node.js version {version} is below minimum requirement {dependency_info.min_version}"
            )
            return dependency_info

        # Get installation path
        success, stdout, stderr = self._run_command([executable_path, "-e", "console.log(process.execPath)"])
        if success:
            dependency_info.install_path = stdout

        dependency_info.status = DependencyStatus.INSTALLED
        self.logger.info(f"Node.js {version} found at {executable_path}")

        return dependency_info

    def check_python(self) -> DependencyInfo:
        """Check Python installation and version"""
        self.logger.info("Checking Python installation...")

        dependency_info = DependencyInfo(
            name="Python",
            type=DependencyType.PYTHON,
            status=DependencyStatus.UNKNOWN,  # Will be updated based on checks
            min_version=self.MINIMUM_REQUIREMENTS[DependencyType.PYTHON]
        )

        # Find executable
        executable_path = self._find_executable(DependencyType.PYTHON)
        if not executable_path:
            dependency_info.status = DependencyStatus.NOT_INSTALLED
            dependency_info.error_message = "Python executable not found in PATH or common installation directories"
            return dependency_info

        dependency_info.executable_path = executable_path

        # Get version
        success, stdout, stderr = self._run_command([executable_path, "--version"])
        if not success:
            dependency_info.status = DependencyStatus.INACCESSIBLE
            dependency_info.error_message = f"Failed to get Python version: {stderr}"
            return dependency_info

        version = self._parse_version_output(stdout, DependencyType.PYTHON)
        if not version:
            dependency_info.status = DependencyStatus.UNKNOWN
            dependency_info.error_message = f"Could not parse Python version from: {stdout}"
            return dependency_info

        dependency_info.version = version
        dependency_info.install_path = executable_path

        # Check version requirement
        if not VersionComparator.meets_requirement(version, dependency_info.min_version):
            dependency_info.status = DependencyStatus.VERSION_MISMATCH
            dependency_info.error_message = (
                f"Python version {version} is below minimum requirement {dependency_info.min_version}"
            )
            return dependency_info

        # Get additional Python info
        try:
            import sys
            dependency_info.additional_info = {
                "python_path": sys.executable,
                "site_packages": [path for path in sys.path if "site-packages" in path],
                "python_version": sys.version,
            }
        except:
            pass

        dependency_info.status = DependencyStatus.INSTALLED
        self.logger.info(f"Python {version} found at {executable_path}")

        return dependency_info

    def check_git(self) -> DependencyInfo:
        """Check Git installation and version"""
        self.logger.info("Checking Git installation...")

        dependency_info = DependencyInfo(
            name="Git",
            type=DependencyType.GIT,
            status=DependencyStatus.UNKNOWN,  # Will be updated based on checks
            min_version=self.MINIMUM_REQUIREMENTS[DependencyType.GIT]
        )

        # Find executable
        executable_path = self._find_executable(DependencyType.GIT)
        if not executable_path:
            dependency_info.status = DependencyStatus.NOT_INSTALLED
            dependency_info.error_message = "Git executable not found in PATH or common installation directories"
            return dependency_info

        dependency_info.executable_path = executable_path

        # Get version
        success, stdout, stderr = self._run_command([executable_path, "--version"])
        if not success:
            dependency_info.status = DependencyStatus.INACCESSIBLE
            dependency_info.error_message = f"Failed to get Git version: {stderr}"
            return dependency_info

        version = self._parse_version_output(stdout, DependencyType.GIT)
        if not version:
            dependency_info.status = DependencyStatus.UNKNOWN
            dependency_info.error_message = f"Could not parse Git version from: {stdout}"
            return dependency_info

        dependency_info.version = version

        # Check version requirement
        if not VersionComparator.meets_requirement(version, dependency_info.min_version):
            dependency_info.status = DependencyStatus.VERSION_MISMATCH
            dependency_info.error_message = (
                f"Git version {version} is below minimum requirement {dependency_info.min_version}"
            )
            return dependency_info

        # Get Git configuration info
        try:
            # Get git installation path
            success, stdout, stderr = self._run_command([executable_path, "--exec-path"])
            if success:
                dependency_info.install_path = stdout

            # Get user configuration
            for key in ["user.name", "user.email"]:
                success, stdout, stderr = self._run_command([executable_path, "config", "--global", "--get", key])
                if success and stdout:
                    dependency_info.additional_info[key] = stdout
        except:
            pass

        dependency_info.status = DependencyStatus.INSTALLED
        self.logger.info(f"Git {version} found at {executable_path}")

        return dependency_info

    def check_dependency(self, dependency_type: DependencyType) -> DependencyInfo:
        """
        Check a specific dependency.

        Args:
            dependency_type: Type of dependency to check

        Returns:
            DependencyInfo object with check results
        """
        if dependency_type in self.checked_dependencies:
            return self.checked_dependencies[dependency_type]

        if dependency_type == DependencyType.NODEJS:
            result = self.check_nodejs()
        elif dependency_type == DependencyType.PYTHON:
            result = self.check_python()
        elif dependency_type == DependencyType.GIT:
            result = self.check_git()
        else:
            # For package managers (npm, pip), we'll implement these later
            result = DependencyInfo(
                name=dependency_type.value,
                type=dependency_type,
                status=DependencyStatus.UNKNOWN,
                error_message=f"Dependency type {dependency_type} not yet implemented"
            )

        self.checked_dependencies[dependency_type] = result
        return result

    def check_all_dependencies(self) -> Dict[DependencyType, DependencyInfo]:
        """
        Check all supported dependencies.

        Returns:
            Dictionary mapping dependency types to their info
        """
        self.logger.info("Starting comprehensive dependency check...")

        results = {}
        for dependency_type in DependencyType:
            if dependency_type in [DependencyType.NPM, DependencyType.PIP]:
                # Skip package managers for now, will be implemented in network task
                continue

            try:
                results[dependency_type] = self.check_dependency(dependency_type)
            except Exception as e:
                self.logger.error(f"Error checking {dependency_type}: {e}")
                results[dependency_type] = DependencyInfo(
                    name=dependency_type.value,
                    type=dependency_type,
                    status=DependencyStatus.UNKNOWN,
                    error_message=f"Unexpected error: {str(e)}"
                )

        self.checked_dependencies.update(results)
        return results

    def get_missing_dependencies(self) -> List[DependencyInfo]:
        """Get list of missing or problematic dependencies"""
        return [
            dep for dep in self.checked_dependencies.values()
            if dep.status not in [DependencyStatus.INSTALLED]
        ]

    def get_dependency_summary(self) -> Dict[str, Any]:
        """Get a summary of dependency status"""
        total = len(self.checked_dependencies)
        installed = len([
            dep for dep in self.checked_dependencies.values()
            if dep.status == DependencyStatus.INSTALLED
        ])

        return {
            "total_dependencies": total,
            "installed": installed,
            "missing": total - installed,
            "operating_system": self.operating_system.value,
            "dependencies": {
                dep_type.value: asdict(dep_info)
                for dep_type, dep_info in self.checked_dependencies.items()
            }
        }