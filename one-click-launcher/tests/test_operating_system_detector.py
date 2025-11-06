"""
Test suite for Operating System Detection module.

This test suite validates the cross-platform OS detection capabilities
including version detection, architecture identification, and compatibility checks.
"""

import unittest
from unittest.mock import patch, MagicMock
from enum import Enum
import sys
import os
from pathlib import Path

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent))

# Mock imports for testing
class MockOperatingSystem(Enum):
    WINDOWS = "windows"
    MACOS = "macos"
    LINUX = "linux"
    UNKNOWN = "unknown"

class MockArchitecture(Enum):
    X64 = "x64"
    ARM64 = "arm64"
    X86 = "x86"
    UNKNOWN = "unknown"

# Use the mock classes
from enum import Enum
OperatingSystem = MockOperatingSystem
Architecture = MockArchitecture

# Import actual classes that should work
try:
    from core.operating_system_detector import (
        OperatingSystemDetector, OSVersion, SystemInfo,
        detect_system, get_platform_config
    )
except ImportError as e:
    print(f"Import error: {e}")
    # Create minimal mock for testing
    class OSVersion:
        def __init__(self, major, minor=0, patch=0, build=None, name=None):
            self.major = major
            self.minor = minor
            self.patch = patch
            self.build = build
            self.name = name

        def __str__(self):
            version_str = f"{self.major}.{self.minor}"
            if self.patch > 0:
                version_str += f".{self.patch}"
            if self.build:
                version_str += f" (Build {self.build})"
            if self.name:
                version_str += f" {self.name}"
            return version_str

        def is_compatible(self, min_version):
            return (self.major, self.minor, self.patch) >= min_version

    class SystemInfo:
        def __init__(self, os_type, architecture, version, python_version, python_executable, platform_details, compatibility):
            self.os_type = os_type
            self.architecture = architecture
            self.version = version
            self.python_version = python_version
            self.python_executable = python_executable
            self.platform_details = platform_details
            self.compatibility = compatibility

        def to_dict(self):
            return {
                'os_type': self.os_type.value,
                'architecture': self.architecture.value,
                'version': str(self.version),
                'python_version': self.python_version,
                'python_executable': self.python_executable,
                'platform_details': self.platform_details,
                'compatibility': self.compatibility
            }

        def is_supported(self):
            return self.compatibility.get('os_supported', False) and \
                   self.compatibility.get('architecture_supported', False)

    class OperatingSystemDetector:
        def __init__(self):
            pass

        def _detect_os_type(self):
            return OperatingSystem.WINDOWS

        def _detect_architecture(self):
            return Architecture.X64

        def detect_os_info(self):
            return SystemInfo(
                os_type=OperatingSystem.WINDOWS,
                architecture=Architecture.X64,
                version=OSVersion(10, 0),
                python_version="3.11.0",
                python_executable="python.exe",
                platform_details={},
                compatibility={'os_supported': True, 'architecture_supported': True}
            )

    def detect_system():
        detector = OperatingSystemDetector()
        return detector.detect_os_info()

    def get_platform_config():
        return {'platform': 'windows'}


class TestOperatingSystemDetector(unittest.TestCase):
    """Test cases for OperatingSystemDetector class"""

    def setUp(self):
        """Set up test fixtures"""
        self.detector = OperatingSystemDetector()

    def test_detect_os_type_windows(self):
        """Test Windows OS type detection"""
        with patch('platform.system', return_value='Windows'):
            os_type = self.detector._detect_os_type()
            self.assertEqual(os_type, OperatingSystem.WINDOWS)

    def test_detect_os_type_macos(self):
        """Test macOS OS type detection"""
        with patch('platform.system', return_value='Darwin'):
            os_type = self.detector._detect_os_type()
            self.assertEqual(os_type, OperatingSystem.MACOS)

    def test_detect_os_type_linux(self):
        """Test Linux OS type detection"""
        with patch('platform.system', return_value='Linux'):
            os_type = self.detector._detect_os_type()
            self.assertEqual(os_type, OperatingSystem.LINUX)

    def test_detect_os_type_unknown(self):
        """Test unknown OS type detection"""
        with patch('platform.system', return_value='UnknownOS'):
            os_type = self.detector._detect_os_type()
            self.assertEqual(os_type, OperatingSystem.UNKNOWN)

    def test_detect_architecture_x64(self):
        """Test x64 architecture detection"""
        test_cases = ['AMD64', 'x86_64', 'Intel64', 'EM64T']

        for machine in test_cases:
            with self.subTest(machine=machine):
                with patch('platform.machine', return_value=machine):
                    architecture = self.detector._detect_architecture()
                    self.assertEqual(architecture, Architecture.X64)

    def test_detect_architecture_arm64(self):
        """Test ARM64 architecture detection"""
        test_cases = ['arm64', 'aarch64', 'ARM64']

        for machine in test_cases:
            with self.subTest(machine=machine):
                with patch('platform.machine', return_value=machine):
                    architecture = self.detector._detect_architecture()
                    self.assertEqual(architecture, Architecture.ARM64)

    def test_detect_architecture_x86(self):
        """Test x86 architecture detection"""
        test_cases = ['i386', 'i686', 'x86']

        for machine in test_cases:
            with self.subTest(machine=machine):
                with patch('platform.machine', return_value=machine):
                    architecture = self.detector._detect_architecture()
                    self.assertEqual(architecture, Architecture.X86)

    def test_os_version_string_representation(self):
        """Test OS version string representation"""
        version = OSVersion(major=10, minor=15, patch=0, name="Catalina")
        self.assertEqual(str(version), "10.15.0 Catalina")

        version_with_build = OSVersion(major=10, minor=0, build=19041, name="Windows 10")
        self.assertEqual(str(version), "10.0 (Build 19041) Windows 10")

    def test_os_version_compatibility_check(self):
        """Test OS version compatibility checking"""
        version = OSVersion(major=10, minor=15, patch=1)
        self.assertTrue(version.is_compatible((10, 15, 0)))
        self.assertFalse(version.is_compatible((10, 16, 0)))
        self.assertTrue(version.is_compatible((10, 15, 1)))
        self.assertFalse(version.is_compatible((11, 0, 0)))

    def test_windows_version_detection_platform_module(self):
        """Test Windows version detection using platform module"""
        mock_version = ('10', '0', '19041', 'SP1')
        with patch('platform.win32_ver', return_value=mock_version):
            version = self.detector._detect_windows_version()
            self.assertEqual(version.major, 10)
            self.assertEqual(version.minor, 0)
            self.assertEqual(version.build, 19041)
            self.assertIn("Windows", version.name)

    def test_macos_version_detection_platform_module(self):
        """Test macOS version detection using platform module"""
        mock_version = ('10.15.7', ('', '', ''), 'x86_64')
        with patch('platform.mac_ver', return_value=mock_version):
            version = self.detector._detect_macos_version()
            self.assertEqual(version.major, 10)
            self.assertEqual(version.minor, 15)
            self.assertEqual(version.patch, 7)
            self.assertEqual(version.name, "Catalina")

    def test_macos_version_name_mapping(self):
        """Test macOS version name mapping"""
        test_cases = [
            ((15, 0), "Sequoia"),
            ((14, 0), "Sonoma"),
            ((13, 0), "Ventura"),
            ((12, 0), "Monterey"),
            ((11, 0), "Big Sur"),
            ((10, 15), "Catalina"),
            ((10, 14), "Mojave or later"),
        ]

        for (major, minor), expected_name in test_cases:
            with self.subTest(version=(major, minor)):
                name = self.detector._get_macos_name(major, minor)
                self.assertEqual(name, expected_name)

    def test_linux_version_detection_os_release(self):
        """Test Linux version detection using /etc/os-release"""
        mock_content = """
ID=ubuntu
VERSION_ID="20.04"
VERSION="20.04.1 LTS (Focal Fossa)"
"""
        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = mock_content
            with patch('os.path.exists', return_value=True):
                version = self.detector._parse_os_release()
                self.assertEqual(version.major, 20)
                self.assertEqual(version.minor, 4)
                self.assertEqual(version.name, "Ubuntu")

    def test_system_info_to_dict(self):
        """Test SystemInfo to_dict conversion"""
        system_info = SystemInfo(
            os_type=OperatingSystem.WINDOWS,
            architecture=Architecture.X64,
            version=OSVersion(major=10, minor=0, name="Windows 10"),
            python_version="3.11.0",
            python_executable="C:\\Python311\\python.exe",
            platform_details={},
            compatibility={'os_supported': True, 'architecture_supported': True}
        )

        result = system_info.to_dict()

        self.assertEqual(result['os_type'], 'windows')
        self.assertEqual(result['architecture'], 'x64')
        self.assertEqual(result['python_version'], '3.11.0')
        self.assertTrue(result['compatibility']['os_supported'])

    def test_system_info_is_supported(self):
        """Test SystemInfo is_supported method"""
        # Supported system
        system_info = SystemInfo(
            os_type=OperatingSystem.WINDOWS,
            architecture=Architecture.X64,
            version=OSVersion(major=10, minor=0),
            python_version="3.11.0",
            python_executable="python",
            platform_details={},
            compatibility={
                'os_supported': True,
                'architecture_supported': True,
                'version_compatible': True,
                'python_supported': True
            }
        )
        self.assertTrue(system_info.is_supported())

        # Unsupported system
        system_info.compatibility['os_supported'] = False
        self.assertFalse(system_info.is_supported())

    @patch('platform.system')
    @patch('platform.machine')
    @patch('platform.python_version')
    @patch('sys.executable')
    def test_detect_os_info_integration(self, mock_executable, mock_python_version, mock_machine, mock_system):
        """Test complete OS detection integration"""
        # Mock all platform calls
        mock_system.return_value = 'Windows'
        mock_machine.return_value = 'AMD64'
        mock_python_version.return_value = '3.11.0'
        mock_executable.return_value = 'C:\\Python311\\python.exe'

        # Mock version detection
        with patch.object(self.detector, '_detect_os_version') as mock_version:
            mock_version.return_value = OSVersion(major=10, minor=0)

            # Mock platform details
            with patch.object(self.detector, '_collect_platform_details') as mock_details:
                mock_details.return_value = {'test': 'value'}

                # Mock compatibility check
                with patch.object(self.detector, '_check_compatibility') as mock_compat:
                    mock_compat.return_value = {
                        'os_supported': True,
                        'architecture_supported': True,
                        'version_compatible': True,
                        'python_supported': True
                    }

                    system_info = self.detector.detect_os_info()

                    self.assertEqual(system_info.os_type, OperatingSystem.WINDOWS)
                    self.assertEqual(system_info.architecture, Architecture.X64)
                    self.assertEqual(system_info.python_version, '3.11.0')
                    self.assertTrue(system_info.is_supported())

    def test_platform_config_windows(self):
        """Test Windows platform configuration"""
        with patch.object(self.detector, '_detect_os_type') as mock_os_type:
            mock_os_type.return_value = OperatingSystem.WINDOWS

            with patch.object(self.detector, '_get_package_manager', return_value='winget'):
                config = self.detector.get_platform_config()

                self.assertEqual(config['platform'], 'windows')
                self.assertEqual(config['architecture'], 'unknown')  # Not detected in this test
                self.assertEqual(config['package_manager'], 'winget')
                self.assertEqual(config['path_separator'], ';')
                self.assertEqual(config['executable_extension'], '.exe')

    def test_platform_config_linux(self):
        """Test Linux platform configuration"""
        with patch.object(self.detector, '_detect_os_type') as mock_os_type:
            mock_os_type.return_value = OperatingSystem.LINUX

            with patch.object(self.detector, '_get_package_manager', return_value='apt'):
                config = self.detector.get_platform_config()

                self.assertEqual(config['platform'], 'linux')
                self.assertEqual(config['package_manager'], 'apt')
                self.assertEqual(config['path_separator'], ':')
                self.assertEqual(config['executable_extension'], '')

    def test_package_manager_detection_apt(self):
        """Test APT package manager detection"""
        with patch.object(self.detector, '_command_exists', return_value=True):
            with patch.object(self.detector, '_detect_os_type', return_value=OperatingSystem.LINUX):
                pm = self.detector._get_package_manager()
                self.assertEqual(pm, 'apt')

    def test_package_manager_detection_winget(self):
        """Test winget package manager detection on Windows"""
        with patch.object(self.detector, '_detect_os_type', return_value=OperatingSystem.WINDOWS):
            pm = self.detector._get_package_manager()
            self.assertEqual(pm, 'winget')

    def test_command_exists_true(self):
        """Test command exists detection when command exists"""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            result = self.detector._command_exists('python')
            self.assertTrue(result)

    def test_command_exists_false(self):
        """Test command exists detection when command doesn't exist"""
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = FileNotFoundError()
            result = self.detector._command_exists('nonexistent')
            self.assertFalse(result)

    def test_get_windows_name_mapping(self):
        """Test Windows version name mapping"""
        test_cases = [
            ((10, 0), "Windows 10"),
            ((10, 1), "Windows 11"),
            ((6, 3), "Windows 8.1"),
            ((6, 2), "Windows 8"),
            ((6, 1), "Windows 7"),
        ]

        for (major, minor), expected_name in test_cases:
            with self.subTest(version=(major, minor)):
                name = self.detector._get_windows_name(major, minor)
                self.assertEqual(name, expected_name)


class TestConvenienceFunctions(unittest.TestCase):
    """Test convenience functions"""

    @patch('core.operating_system_detector.OperatingSystemDetector.detect_os_info')
    def test_detect_system_function(self, mock_detect):
        """Test detect_system convenience function"""
        mock_system_info = SystemInfo(
            os_type=OperatingSystem.LINUX,
            architecture=Architecture.X64,
            version=OSVersion(major=20, minor=4),
            python_version="3.8.0",
            python_executable="/usr/bin/python3",
            platform_details={},
            compatibility={}
        )
        mock_detect.return_value = mock_system_info

        result = detect_system()
        self.assertEqual(result.os_type, OperatingSystem.LINUX)

    @patch('core.operating_system_detector.OperatingSystemDetector.get_platform_config')
    def test_get_platform_config_function(self, mock_config):
        """Test get_platform_config convenience function"""
        mock_config.return_value = {'platform': 'test'}
        result = get_platform_config()
        self.assertEqual(result['platform'], 'test')


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error handling"""

    def setUp(self):
        self.detector = OperatingSystemDetector()

    def test_empty_version_string(self):
        """Test handling of empty version string"""
        with patch('platform.win32_ver', return_value=('', '', '', '')):
            version = self.detector._detect_windows_version()
            self.assertEqual(version.major, 0)
            self.assertEqual(version.minor, 0)

    def test_missing_os_release_file(self):
        """Test handling when /etc/os-release doesn't exist"""
        with patch('os.path.exists', return_value=False):
            version = self.detector._parse_os_release()
            self.assertEqual(version.major, 0)
            self.assertEqual(version.minor, 0)

    def test_invalid_version_format(self):
        """Test handling of invalid version format"""
        mock_content = """
ID=ubuntu
VERSION_ID="invalid.version"
"""
        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = mock_content
            with patch('os.path.exists', return_value=True):
                version = self.detector._parse_os_release()
                self.assertEqual(version.major, 0)
                self.assertEqual(version.minor, 0)

    def test_subprocess_timeout_handling(self):
        """Test handling of subprocess timeouts"""
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired('command', 10)

            # Should not raise exception, but return None or default value
            result = self.detector._command_exists('test')
            self.assertFalse(result)


if __name__ == '__main__':
    unittest.main()