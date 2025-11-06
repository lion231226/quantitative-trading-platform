"""
Operating System Detection and Platform Adaptation Module

This module provides comprehensive operating system detection capabilities
including version detection, architecture identification, and compatibility checks.
"""

import os
import sys
import platform
import subprocess
import re
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum
import json


class OperatingSystem(Enum):
    """Supported operating systems"""
    WINDOWS = "windows"
    MACOS = "macos"
    LINUX = "linux"
    UNKNOWN = "unknown"


class Architecture(Enum):
    """Supported system architectures"""
    X64 = "x64"
    ARM64 = "arm64"
    X86 = "x86"
    UNKNOWN = "unknown"


@dataclass
class OSVersion:
    """Operating system version information"""
    major: int
    minor: int
    patch: int = 0
    build: Optional[int] = None
    name: Optional[str] = None  # e.g., "Catalina", "Big Sur", "Ubuntu"

    def __str__(self) -> str:
        version_str = f"{self.major}.{self.minor}"
        if self.patch > 0:
            version_str += f".{self.patch}"
        if self.build:
            version_str += f" (Build {self.build})"
        if self.name:
            version_str += f" {self.name}"
        return version_str

    def is_compatible(self, min_version: Tuple[int, int, int]) -> bool:
        """Check if version meets minimum requirements"""
        return (self.major, self.minor, self.patch) >= min_version


@dataclass
class SystemInfo:
    """Comprehensive system information"""
    os_type: OperatingSystem
    architecture: Architecture
    version: OSVersion
    python_version: str
    python_executable: str
    platform_details: Dict[str, str]
    compatibility: Dict[str, bool]

    def is_supported(self) -> bool:
        """Check if the system is supported"""
        return self.compatibility.get('os_supported', False) and \
               self.compatibility.get('architecture_supported', False)

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'os_type': self.os_type.value,
            'architecture': self.architecture.value,
            'version': str(self.version),
            'python_version': self.python_version,
            'python_executable': self.python_executable,
            'platform_details': self.platform_details,
            'compatibility': self.compatibility,
            'is_supported': self.is_supported()
        }


class OperatingSystemDetector:
    """
    Comprehensive operating system detection and platform adaptation.

    Features:
    - Cross-platform OS detection (Windows 10/11, macOS 10.15+, Ubuntu 18.04+)
    - Architecture detection (x64, ARM64)
    - Version compatibility checking
    - Platform-specific configuration
    """

    # Minimum version requirements
    MIN_VERSIONS = {
        OperatingSystem.WINDOWS: (10, 0, 0),
        OperatingSystem.MACOS: (10, 15, 0),
        OperatingSystem.LINUX: (18, 4, 0)  # Ubuntu 18.04+
    }

    # Architecture mappings
    ARCHITECTURE_MAP = {
        'AMD64': Architecture.X64,
        'x86_64': Architecture.X64,
        'Intel64': Architecture.X64,
        'EM64T': Architecture.X64,
        'arm64': Architecture.ARM64,
        'aarch64': Architecture.ARM64,
        'ARM64': Architecture.ARM64,
        'i386': Architecture.X86,
        'i686': Architecture.X86,
        'x86': Architecture.X86,
    }

    def __init__(self):
        self.system_info: Optional[SystemInfo] = None

    def detect_os_info(self) -> SystemInfo:
        """
        Detect comprehensive operating system information.

        Returns:
            SystemInfo: Complete system information

        Raises:
            RuntimeError: If OS detection fails
        """
        try:
            # Detect OS type
            os_type = self._detect_os_type()

            # Detect architecture
            architecture = self._detect_architecture()

            # Detect version information
            version = self._detect_os_version(os_type)

            # Get Python information
            python_version = platform.python_version()
            python_executable = sys.executable

            # Collect platform-specific details
            platform_details = self._collect_platform_details(os_type)

            # Check compatibility
            compatibility = self._check_compatibility(os_type, architecture, version)

            self.system_info = SystemInfo(
                os_type=os_type,
                architecture=architecture,
                version=version,
                python_version=python_version,
                python_executable=python_executable,
                platform_details=platform_details,
                compatibility=compatibility
            )

            return self.system_info

        except Exception as e:
            raise RuntimeError(f"Failed to detect OS information: {e}")

    def _detect_os_type(self) -> OperatingSystem:
        """Detect the operating system type"""
        system = platform.system().lower()

        if system == 'windows':
            return OperatingSystem.WINDOWS
        elif system == 'darwin':
            return OperatingSystem.MACOS
        elif system == 'linux':
            return OperatingSystem.LINUX
        else:
            return OperatingSystem.UNKNOWN

    def _detect_architecture(self) -> Architecture:
        """Detect system architecture"""
        machine = platform.machine().upper()

        # Map common architecture strings to standard names
        if machine in self.ARCHITECTURE_MAP:
            return self.ARCHITECTURE_MAP[machine]

        # Try alternative methods
        try:
            # Check processor info on Windows
            if self._detect_os_type() == OperatingSystem.WINDOWS:
                result = subprocess.run(['wmic', 'cpu', 'get', 'name'],
                                      capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    output = result.stdout.lower()
                    if 'arm64' in output or 'aarch64' in output:
                        return Architecture.ARM64
                    elif '64' in output:
                        return Architecture.X64
                    else:
                        return Architecture.X86
        except (subprocess.SubprocessError, FileNotFoundError):
            pass

        return Architecture.UNKNOWN

    def _detect_os_version(self, os_type: OperatingSystem) -> OSVersion:
        """Detect operating system version"""
        if os_type == OperatingSystem.WINDOWS:
            return self._detect_windows_version()
        elif os_type == OperatingSystem.MACOS:
            return self._detect_macos_version()
        elif os_type == OperatingSystem.LINUX:
            return self._detect_linux_version()
        else:
            return OSVersion(0, 0, 0)

    def _detect_windows_version(self) -> OSVersion:
        """Detect Windows version"""
        try:
            # Try platform module first
            version = platform.win32_ver()
            if version and version[0]:  # (version, csd, ptype, build)
                version_str = version[0]
                build_num = version[3] if len(version) > 3 else None

                # Parse version string
                version_parts = version_str.split('.')
                major = int(version_parts[0]) if version_parts[0].isdigit() else 0
                minor = int(version_parts[1]) if len(version_parts) > 1 and version_parts[1].isdigit() else 0
                patch = int(version_parts[2]) if len(version_parts) > 2 and version_parts[2].isdigit() else 0

                # Get Windows name from version
                name = self._get_windows_name(major, minor)

                return OSVersion(
                    major=major,
                    minor=minor,
                    patch=patch,
                    build=int(build_num) if build_num and build_num.isdigit() else None,
                    name=name
                )

            # Fallback to registry query
            return self._detect_windows_version_registry()

        except Exception:
            return OSVersion(0, 0, 0)

    def _detect_windows_version_registry(self) -> OSVersion:
        """Detect Windows version from registry"""
        try:
            import winreg

            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                              r"SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion") as key:

                major = int(winreg.QueryValueEx(key, "CurrentMajorVersionNumber")[0])
                minor = int(winreg.QueryValueEx(key, "CurrentMinorVersionNumber")[0])
                build = winreg.QueryValueEx(key, "CurrentBuildNumber")[0]
                product_name = winreg.QueryValueEx(key, "ProductName")[0]

                # Extract name from product name
                name = product_name.replace("Windows ", "")

                return OSVersion(
                    major=major,
                    minor=minor,
                    build=int(build) if build.isdigit() else None,
                    name=name
                )
        except (ImportError, OSError, ValueError):
            pass

        return OSVersion(0, 0, 0)

    def _get_windows_name(self, major: int, minor: int) -> str:
        """Get Windows name from version"""
        if major == 10:
            return "Windows 10" if minor == 0 else "Windows 11"
        elif major == 6:
            if minor == 3:
                return "Windows 8.1"
            elif minor == 2:
                return "Windows 8"
            elif minor == 1:
                return "Windows 7"
        elif major == 5:
            if minor == 1:
                return "Windows XP"
            elif minor == 0:
                return "Windows 2000"

        return f"Windows {major}.{minor}"

    def _detect_macos_version(self) -> OSVersion:
        """Detect macOS version"""
        try:
            # Try platform module first
            version = platform.mac_ver()
            if version and version[0]:  # (release, versioninfo, machine)
                version_str = version[0]
                version_parts = version_str.split('.')

                major = int(version_parts[0]) if version_parts[0].isdigit() else 0
                minor = int(version_parts[1]) if len(version_parts) > 1 and version_parts[1].isdigit() else 0
                patch = int(version_parts[2]) if len(version_parts) > 2 and version_parts[2].isdigit() else 0

                # Get macOS name from version
                name = self._get_macos_name(major, minor)

                return OSVersion(major=major, minor=minor, patch=patch, name=name)

            # Fallback to sw_vers command
            return self._detect_macos_version_sw_vers()

        except Exception:
            return OSVersion(0, 0, 0)

    def _detect_macos_version_sw_vers(self) -> OSVersion:
        """Detect macOS version using sw_vers command"""
        try:
            result = subprocess.run(['sw_vers', '-productVersion'],
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                version_str = result.stdout.strip()
                version_parts = version_str.split('.')

                major = int(version_parts[0])
                minor = int(version_parts[1])
                patch = int(version_parts[2]) if len(version_parts) > 2 else 0

                name = self._get_macos_name(major, minor)

                return OSVersion(major=major, minor=minor, patch=patch, name=name)
        except (subprocess.SubprocessError, FileNotFoundError, ValueError):
            pass

        return OSVersion(0, 0, 0)

    def _get_macos_name(self, major: int, minor: int) -> str:
        """Get macOS name from version"""
        if major == 15:
            return "Sequoia"
        elif major == 14:
            return "Sonoma"
        elif major == 13:
            return "Ventura"
        elif major == 12:
            return "Monterey"
        elif major == 11:
            return "Big Sur"
        elif major == 10:
            if minor >= 15:
                return "Catalina" if minor == 15 else "Mojave or later"
            else:
                return "Legacy macOS"

        return f"macOS {major}.{minor}"

    def _detect_linux_version(self) -> OSVersion:
        """Detect Linux distribution version"""
        try:
            # Try to read /etc/os-release
            if os.path.exists('/etc/os-release'):
                return self._parse_os_release()

            # Fallback to lsb_release
            if self._command_exists('lsb_release'):
                return self._detect_linux_version_lsb()

            # Try other common files
            if os.path.exists('/etc/ubuntu-release'):
                return self._parse_ubuntu_release()
            elif os.path.exists('/etc/redhat-release'):
                return self._parse_redhat_release()

        except Exception:
            pass

        return OSVersion(0, 0, 0, name="Unknown Linux")

    def _parse_os_release(self) -> OSVersion:
        """Parse /etc/os-release file"""
        try:
            with open('/etc/os-release', 'r') as f:
                content = f.read()

            # Extract distribution name and version
            name = "Unknown Linux"
            version_id = None

            for line in content.split('\n'):
                if line.startswith('ID='):
                    name = line.split('=')[1].strip('"')
                elif line.startswith('VERSION_ID='):
                    version_id = line.split('=')[1].strip('"')

            # Map distribution names
            name_map = {
                'ubuntu': 'Ubuntu',
                'debian': 'Debian',
                'fedora': 'Fedora',
                'centos': 'CentOS',
                'rhel': 'Red Hat'
            }

            display_name = name_map.get(name, name.title())

            if version_id:
                version_parts = version_id.split('.')
                major = int(version_parts[0]) if version_parts[0].isdigit() else 0
                minor = int(version_parts[1]) if len(version_parts) > 1 and version_parts[1].isdigit() else 0
                patch = int(version_parts[2]) if len(version_parts) > 2 and version_parts[2].isdigit() else 0

                return OSVersion(major=major, minor=minor, patch=patch, name=display_name)

            return OSVersion(0, 0, 0, name=display_name)

        except Exception:
            return OSVersion(0, 0, 0, name="Unknown Linux")

    def _detect_linux_version_lsb(self) -> OSVersion:
        """Detect Linux version using lsb_release"""
        try:
            result = subprocess.run(['lsb_release', '-irc'],
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')

                distributor = None
                release = None

                for line in lines:
                    if line.startswith('Distributor ID:'):
                        distributor = line.split(':')[-1].strip()
                    elif line.startswith('Release:'):
                        release = line.split(':')[-1].strip()

                if release:
                    version_parts = release.split('.')
                    major = int(version_parts[0]) if version_parts[0].isdigit() else 0
                    minor = int(version_parts[1]) if len(version_parts) > 1 and version_parts[1].isdigit() else 0
                    patch = int(version_parts[2]) if len(version_parts) > 2 and version_parts[2].isdigit() else 0

                    return OSVersion(
                        major=major,
                        minor=minor,
                        patch=patch,
                        name=distributor or "Unknown Linux"
                    )
        except Exception:
            pass

        return OSVersion(0, 0, 0)

    def _parse_ubuntu_release(self) -> OSVersion:
        """Parse Ubuntu release file"""
        try:
            with open('/etc/ubuntu-release', 'r') as f:
                content = f.read()

            # Extract version from content like "Ubuntu 18.04.3 LTS"
            match = re.search(r'Ubuntu (\d+)\.(\d+)(?:\.(\d+))?', content)
            if match:
                major = int(match.group(1))
                minor = int(match.group(2))
                patch = int(match.group(3)) if match.group(3) else 0

                return OSVersion(major=major, minor=minor, patch=patch, name="Ubuntu")
        except Exception:
            pass

        return OSVersion(0, 0, 0)

    def _parse_redhat_release(self) -> OSVersion:
        """Parse Red Hat release file"""
        try:
            with open('/etc/redhat-release', 'r') as f:
                content = f.read()

            # Extract version from content like "Red Hat Enterprise Linux Server 7.9"
            match = re.search(r'(\d+)\.(\d+)(?:\.(\d+))?', content)
            if match:
                major = int(match.group(1))
                minor = int(match.group(2))
                patch = int(match.group(3)) if match.group(3) else 0

                return OSVersion(major=major, minor=minor, patch=patch, name="Red Hat")
        except Exception:
            pass

        return OSVersion(0, 0, 0)

    def _collect_platform_details(self, os_type: OperatingSystem) -> Dict[str, str]:
        """Collect platform-specific details"""
        details = {
            'platform': platform.platform(),
            'processor': platform.processor(),
            'node': platform.node(),
            'release': platform.release(),
        }

        if os_type == OperatingSystem.WINDOWS:
            details.update(self._get_windows_details())
        elif os_type == OperatingSystem.MACOS:
            details.update(self._get_macos_details())
        elif os_type == OperatingSystem.LINUX:
            details.update(self._get_linux_details())

        return details

    def _get_windows_details(self) -> Dict[str, str]:
        """Get Windows-specific details"""
        details = {}

        try:
            # Get Windows edition
            result = subprocess.run(['wmic', 'os', 'get', 'caption'],
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                if len(lines) > 1:
                    details['edition'] = lines[1].strip()
        except Exception:
            pass

        return details

    def _get_macos_details(self) -> Dict[str, str]:
        """Get macOS-specific details"""
        details = {}

        try:
            # Get system profile
            result = subprocess.run(['system_profiler', 'SPSoftwareDataType'],
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                output = result.stdout
                for line in output.split('\n'):
                    if 'Kernel Version:' in line:
                        details['kernel_version'] = line.split(':')[-1].strip()
        except Exception:
            pass

        return details

    def _get_linux_details(self) -> Dict[str, str]:
        """Get Linux-specific details"""
        details = {}

        try:
            # Get kernel version
            result = subprocess.run(['uname', '-r'],
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                details['kernel_version'] = result.stdout.strip()
        except Exception:
            pass

        return details

    def _check_compatibility(self, os_type: OperatingSystem,
                           architecture: Architecture,
                           version: OSVersion) -> Dict[str, bool]:
        """Check system compatibility"""
        compatibility = {
            'os_supported': False,
            'architecture_supported': False,
            'version_compatible': False,
            'python_supported': False
        }

        # Check OS support
        if os_type in [OperatingSystem.WINDOWS, OperatingSystem.MACOS, OperatingSystem.LINUX]:
            compatibility['os_supported'] = True

        # Check architecture support
        if architecture in [Architecture.X64, Architecture.ARM64]:
            compatibility['architecture_supported'] = True

        # Check version compatibility
        if os_type in self.MIN_VERSIONS:
            min_version = self.MIN_VERSIONS[os_type]
            compatibility['version_compatible'] = version.is_compatible(min_version)

        # Check Python version (3.8+ requirement)
        python_version = sys.version_info
        compatibility['python_supported'] = python_version >= (3, 8)

        return compatibility

    def _command_exists(self, command: str) -> bool:
        """Check if a command exists on the system"""
        try:
            subprocess.run(['which', command],
                          capture_output=True, timeout=5)
            return True
        except (subprocess.SubprocessError, FileNotFoundError):
            return False

    def get_platform_config(self) -> Dict[str, Union[str, List[str]]]:
        """
        Get platform-specific configuration for installation and setup.

        Returns:
            Dict containing platform-specific settings
        """
        if not self.system_info:
            self.detect_os_info()

        config = {
            'platform': self.system_info.os_type.value,
            'architecture': self.system_info.architecture.value,
            'package_manager': self._get_package_manager(),
            'install_commands': self._get_install_commands(),
            'path_separator': self._get_path_separator(),
            'executable_extension': self._get_executable_extension(),
            'service_commands': self._get_service_commands(),
        }

        return config

    def _get_package_manager(self) -> str:
        """Get the appropriate package manager for the platform"""
        if self.system_info.os_type == OperatingSystem.WINDOWS:
            return 'winget'
        elif self.system_info.os_type == OperatingSystem.MACOS:
            return 'brew'
        elif self.system_info.os_type == OperatingSystem.LINUX:
            # Check for available package managers
            for pm in ['apt', 'yum', 'dnf', 'pacman']:
                if self._command_exists(pm):
                    return pm
            return 'apt'  # Default to apt
        return 'unknown'

    def _get_install_commands(self) -> List[str]:
        """Get platform-specific installation commands"""
        commands = []

        if self.system_info.os_type == OperatingSystem.WINDOWS:
            commands = [
                'winget install --id=Microsoft.PowerShell -e',
                'winget install --id=Git.Git -e',
                'winget install --id=Python.Python.3.11 -e'
            ]
        elif self.system_info.os_type == OperatingSystem.MACOS:
            commands = [
                'brew install git',
                'brew install python@3.11',
                'brew install redis'
            ]
        elif self.system_info.os_type == OperatingSystem.LINUX:
            pm = self._get_package_manager()
            commands = [
                f'{pm} update',
                f'{pm} install -y git python3.11 redis-server'
            ]

        return commands

    def _get_path_separator(self) -> str:
        """Get the path separator for the platform"""
        return ';' if self.system_info.os_type == OperatingSystem.WINDOWS else ':'

    def _get_executable_extension(self) -> str:
        """Get the executable extension for the platform"""
        return '.exe' if self.system_info.os_type == OperatingSystem.WINDOWS else ''

    def _get_service_commands(self) -> Dict[str, str]:
        """Get platform-specific service commands"""
        if self.system_info.os_type == OperatingSystem.WINDOWS:
            return {
                'start': 'Start-Service',
                'stop': 'Stop-Service',
                'status': 'Get-Service'
            }
        elif self.system_info.os_type == OperatingSystem.MACOS:
            return {
                'start': 'brew services start',
                'stop': 'brew services stop',
                'status': 'brew services list'
            }
        elif self.system_info.os_type == OperatingSystem.LINUX:
            return {
                'start': 'systemctl start',
                'stop': 'systemctl stop',
                'status': 'systemctl status'
            }
        return {}

    def print_system_info(self) -> None:
        """Print formatted system information"""
        if not self.system_info:
            self.detect_os_info()

        print("=== System Information ===")
        print(f"OS: {self.system_info.os_type.value.title()}")
        print(f"Architecture: {self.system_info.architecture.value}")
        print(f"Version: {self.system_info.version}")
        print(f"Python: {self.system_info.python_version} ({self.system_info.python_executable})")
        print(f"Supported: {self.system_info.is_supported()}")

        print("\n=== Compatibility ===")
        for key, value in self.system_info.compatibility.items():
            status = "✓" if value else "✗"
            print(f"{key.replace('_', ' ').title()}: {status}")

    def save_system_info(self, filepath: str) -> None:
        """Save system information to JSON file"""
        if not self.system_info:
            self.detect_os_info()

        with open(filepath, 'w') as f:
            json.dump(self.system_info.to_dict(), f, indent=2)


# Convenience functions
def detect_system() -> SystemInfo:
    """Convenience function to detect system information"""
    detector = OperatingSystemDetector()
    return detector.detect_os_info()


def get_platform_config() -> Dict[str, Union[str, List[str]]]:
    """Convenience function to get platform configuration"""
    detector = OperatingSystemDetector()
    return detector.get_platform_config()


if __name__ == "__main__":
    # Demo usage
    detector = OperatingSystemDetector()
    system_info = detector.detect_os_info()
    detector.print_system_info()

    print("\n=== Platform Configuration ===")
    config = detector.get_platform_config()
    for key, value in config.items():
        print(f"{key}: {value}")