"""
Python 安装器单元测试

测试 Python 自动安装引擎的各项功能，包括版本检测、下载、安装和验证。
"""

import pytest
import unittest
from unittest.mock import Mock, patch, MagicMock, call
import tempfile
import os
import json
import subprocess
from pathlib import Path

# 添加项目根目录到路径
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from services.python_installer import (
    PythonInstaller, PythonVersion, PythonInstallationStatus,
    PythonInstallationProgress
)
from core.operating_system_detector import OperatingSystem, Architecture, SystemInfo


class TestPythonInstaller(unittest.TestCase):
    """PythonInstaller 测试类"""

    def setUp(self):
        """测试前准备"""
        # Mock 操作系统检测器
        self.mock_os_detector = Mock()
        from core.operating_system_detector import OSVersion
        self.mock_os_info = SystemInfo(
            os_type=OperatingSystem.WINDOWS,
            architecture=Architecture.X64,
            version=OSVersion(10, 0, build=19042, name="Windows 10"),
            python_version="3.9.7",
            python_executable="python.exe",
            platform_details={},
            compatibility={'os_supported': True, 'architecture_supported': True}
        )
        self.mock_os_detector.get_os_info.return_value = self.mock_os_info

        # Mock 网络检查器
        self.mock_network_checker = Mock()
        self.mock_network_checker.check_connectivity.return_value = True

        # 创建 Python 安装器实例
        self.installer = PythonInstaller(self.mock_os_detector, self.mock_network_checker)

    def test_init(self):
        """测试初始化"""
        self.assertIsNotNone(self.installer.os_detector)
        self.assertIsNotNone(self.installer.network_checker)
        self.assertEqual(self.installer.min_version, "3.8")
        self.assertEqual(
            self.installer.progress.status,
            PythonInstallationStatus.NOT_STARTED
        )

    def test_get_supported_versions(self):
        """测试获取支持的版本列表"""
        versions = self.installer.get_supported_versions()
        expected = ["3.12", "3.11", "3.10", "3.9", "3.8"]
        self.assertEqual(versions, expected)

    def test_is_version_supported(self):
        """测试版本支持检查"""
        self.assertTrue(self.installer.is_version_supported("3.9"))
        self.assertTrue(self.installer.is_version_supported("3.9.7"))
        self.assertTrue(self.installer.is_version_supported("3.8"))
        self.assertFalse(self.installer.is_version_supported("3.7"))
        self.assertFalse(self.installer.is_version_supported("2.7"))

    @patch('urllib.request.urlopen')
    def test_get_available_versions_success(self, mock_urlopen):
        """测试获取可用版本成功"""
        # Mock API 响应
        mock_response = Mock()
        mock_response.read.return_value = json.dumps([
            {
                'tag_name': 'v3.11.0',
                'prerelease': False,
                'published_at': '2022-10-24T17:00:00Z',
                'assets': [
                    {
                        'name': 'python-3.11.0-amd64.exe',
                        'browser_download_url': 'https://www.python.org/ftp/python/3.11.0/python-3.11.0-amd64.exe',
                        'size': 25000000
                    }
                ]
            },
            {
                'tag_name': 'v3.10.8',
                'prerelease': False,
                'published_at': '2022-10-10T00:00:00Z',
                'assets': [
                    {
                        'name': 'python-3.10.8-amd64.exe',
                        'browser_download_url': 'https://www.python.org/ftp/python/3.10.8/python-3.10.8-amd64.exe',
                        'size': 24000000
                    }
                ]
            }
        ]).encode('utf-8')
        mock_urlopen.return_value.__enter__.return_value = mock_response

        versions = self.installer.get_available_versions("3.10")

        self.assertEqual(len(versions), 2)
        self.assertEqual(versions[0].version, "3.11.0")
        self.assertEqual(versions[1].version, "3.10.8")
        self.assertTrue(versions[0].is_stable)

    def test_parse_version_string(self):
        """测试版本字符串解析"""
        test_cases = [
            ("Python 3.9.7", "3.9.7"),
            ("Python 3.8.10", "3.8.10"),
            ("Python 3.11.0", "3.11.0"),
            ("Invalid string", None),
            ("", None)
        ]

        for input_str, expected in test_cases:
            with self.subTest(input_str=input_str):
                result = self.installer._parse_version_string(input_str)
                self.assertEqual(result, expected)

    def test_compare_versions(self):
        """测试版本比较"""
        # version1 == version2
        self.assertEqual(self.installer._compare_versions("3.9.7", "3.9.7"), 0)

        # version1 > version2
        self.assertEqual(self.installer._compare_versions("3.10.0", "3.9.7"), 1)
        self.assertEqual(self.installer._compare_versions("3.9.8", "3.9.7"), 1)

        # version1 < version2
        self.assertEqual(self.installer._compare_versions("3.8.10", "3.9.7"), -1)
        self.assertEqual(self.installer._compare_versions("3.9.6", "3.9.7"), -1)

    @patch('subprocess.run')
    def test_check_existing_python_success(self, mock_run):
        """测试检查现有 Python 成功"""
        # Mock Python 命令成功
        mock_run.return_value.returncode = 0
        mock_run.return_value.stderr = "Python 3.9.7"

        result = self.installer._check_existing_python("3.8")

        self.assertTrue(result)
        mock_run.assert_called()

    @patch('subprocess.run')
    def test_check_existing_python_not_found(self, mock_run):
        """测试检查现有 Python 未找到"""
        # Mock Python 命令失败
        mock_run.side_effect = FileNotFoundError()

        result = self.installer._check_existing_python("3.8")

        self.assertFalse(result)

    @patch('subprocess.run')
    def test_check_existing_python_version_too_low(self, mock_run):
        """测试检查现有 Python 版本过低"""
        # Mock Python 命令成功但版本过低
        mock_run.return_value.returncode = 0
        mock_run.return_value.stderr = "Python 3.7.9"

        result = self.installer._check_existing_python("3.8")

        self.assertFalse(result)

    def test_get_download_info_windows(self):
        """测试获取 Windows 下载信息"""
        # 设置Mock以返回正确的平台信息
        self.mock_os_info.os_type = OperatingSystem.WINDOWS
        self.mock_os_info.architecture = Architecture.X64

        assets = [
            {
                'name': 'python-3.11.0-amd64.exe',
                'browser_download_url': 'https://www.python.org/ftp/python/3.11.0/python-3.11.0-amd64.exe',
                'size': 25000000
            },
            {
                'name': 'python-3.11.0-arm64.exe',
                'browser_download_url': 'https://www.python.org/ftp/python/3.11.0/python-3.11.0-arm64.exe',
                'size': 25000000
            }
        ]

        result = self.installer._get_download_info(assets)

        self.assertIsNotNone(result)
        self.assertEqual(result['name'], 'python-3.11.0-amd64.exe')
        self.assertIn('python-3.11.0-amd64.exe', result['url'])

    def test_get_download_info_macos(self):
        """测试获取 macOS 下载信息"""
        # 设置为 macOS
        self.mock_os_info.os_type = OperatingSystem.MACOS
        self.mock_os_info.architecture = Architecture.ARM64

        assets = [
            {
                'name': 'python-3.11.0-macos11.pkg',
                'browser_download_url': 'https://www.python.org/ftp/python/3.11.0/python-3.11.0-macos11.pkg',
                'size': 30000000
            },
            {
                'name': 'python-3.11.0-macosx10.9.pkg',
                'browser_download_url': 'https://www.python.org/ftp/python/3.11.0/python-3.11.0-macosx10.9.pkg',
                'size': 30000000
            }
        ]

        result = self.installer._get_download_info(assets)

        self.assertIsNotNone(result)
        self.assertEqual(result['name'], 'python-3.11.0-macos11.pkg')

    @patch('tempfile.mkdtemp')
    def test_install_python_already_exists(self, mock_mkdtemp):
        """测试安装 Python 时已存在符合要求的版本"""
        mock_mkdtemp.return_value = "/tmp/test"

        # Mock 现有 Python 检查成功
        with patch.object(self.installer, '_check_existing_python', return_value=True):
            result = self.installer.install("3.9")

            self.assertTrue(result)
            self.assertEqual(
                self.installer.progress.status,
                PythonInstallationStatus.COMPLETED
            )
            self.assertEqual(self.installer.progress.progress_percentage, 100.0)

    @patch('tempfile.mkdtemp')
    @patch.object(PythonInstaller, '_check_existing_python')
    @patch.object(PythonInstaller, 'get_available_versions')
    @patch.object(PythonInstaller, '_download_python')
    @patch.object(PythonInstaller, '_install_python')
    @patch.object(PythonInstaller, '_verify_installation')
    def test_install_python_success(self, mock_verify, mock_install,
                                   mock_download, mock_versions, mock_check,
                                   mock_mkdtemp):
        """测试完整安装 Python 成功"""
        mock_mkdtemp.return_value = "/tmp/test"
        mock_check.return_value = False
        mock_download.return_value = "/tmp/test/python-installer.exe"
        mock_install.return_value = True
        mock_verify.return_value = True

        # Mock 版本
        version = PythonVersion(
            version="3.11.0",
            release_date="2022-10-24",
            download_url="https://example.com/python.exe",
            checksum="sha256:abc123"
        )
        mock_versions.return_value = [version]

        result = self.installer.install("3.9", install_virtual_env=False)

        self.assertTrue(result)
        self.assertEqual(
            self.installer.progress.status,
            PythonInstallationStatus.COMPLETED
        )
        self.assertEqual(self.installer.progress.progress_percentage, 100.0)

    @patch('tempfile.mkdtemp')
    @patch.object(PythonInstaller, '_check_existing_python')
    @patch.object(PythonInstaller, 'get_available_versions')
    def test_install_no_versions_available(self, mock_versions, mock_check, mock_mkdtemp):
        """测试没有可用版本时的安装"""
        mock_mkdtemp.return_value = "/tmp/test"
        mock_check.return_value = False
        mock_versions.return_value = []

        result = self.installer.install("3.9")

        self.assertFalse(result)
        self.assertEqual(
            self.installer.progress.status,
            PythonInstallationStatus.FAILED
        )

    @patch('subprocess.run')
    def test_install_on_windows_success(self, mock_run):
        """测试在 Windows 上安装成功"""
        installer_path = "/tmp/python-3.11.0-amd64.exe"
        version = PythonVersion(
            version="3.11.0",
            release_date="2022-10-24",
            download_url="https://example.com/python.exe",
            checksum="sha256:abc123"
        )

        # Mock 成功的安装
        mock_run.return_value.returncode = 0
        mock_run.return_value.stderr = ""

        with patch.object(self.installer, '_update_windows_path'):
            result = self.installer._install_on_windows(installer_path, version)

            self.assertTrue(result)
            expected_cmd = [
                installer_path,
                '/quiet',
                'InstallAllUsers=0',
                'PrependPath=1',
                'Include_test=0',
                'TargetDir=C:\\Python3110'
            ]
            mock_run.assert_called_with(expected_cmd, timeout=600, capture_output=True, text=True)

    @patch('subprocess.run')
    def test_install_on_windows_failure(self, mock_run):
        """测试在 Windows 上安装失败"""
        installer_path = "/tmp/python-3.11.0-amd64.exe"
        version = PythonVersion(
            version="3.11.0",
            release_date="2022-10-24",
            download_url="https://example.com/python.exe",
            checksum="sha256:abc123"
        )

        # Mock 失败的安装
        mock_run.return_value.returncode = 1
        mock_run.return_value.stderr = "Installation failed"

        result = self.installer._install_on_windows(installer_path, version)

        self.assertFalse(result)

    @patch('subprocess.run')
    def test_install_on_macos_success(self, mock_run):
        """测试在 macOS 上安装成功"""
        # 设置为 macOS
        self.mock_os_info.os_type = OperatingSystem.MACOS

        installer_path = "/tmp/python-3.11.0-macos11.pkg"
        version = PythonVersion(
            version="3.11.0",
            release_date="2022-10-24",
            download_url="https://example.com/python.pkg",
            checksum="sha256:abc123"
        )

        # Mock 成功的安装
        mock_run.return_value.returncode = 0
        mock_run.return_value.stderr = ""

        result = self.installer._install_on_macos(installer_path, version)

        self.assertTrue(result)
        expected_cmd = ['sudo', 'installer', '-pkg', installer_path, '-target', '/']
        mock_run.assert_called_with(expected_cmd, timeout=600, capture_output=True, text=True)

    @patch('subprocess.run')
    def test_install_on_linux_package_manager(self, mock_run):
        """测试在 Linux 上使用包管理器安装"""
        # 设置为 Linux
        self.mock_os_info.os_type = OperatingSystem.LINUX

        # 使用非 .tgz 文件以触发包管理器安装路径
        installer_path = "/tmp/python-installer.bin"
        version = PythonVersion(
            version="3.11.0",
            release_date="2022-10-24",
            download_url="https://example.com/python.bin",
            checksum="sha256:abc123"
        )

        # Mock 发行版检测和包管理器安装
        with patch.object(self.installer, '_detect_linux_distro', return_value='ubuntu'):
            # Mock apt-get update 和 install
            mock_run.side_effect = [
                Mock(returncode=0),  # apt-get update
                Mock(returncode=0)   # apt-get install
            ]
            mock_run.return_value.returncode = 0

            result = self.installer._install_on_linux(installer_path, version)

            self.assertTrue(result)

    @patch('subprocess.run')
    def test_verify_installation_success(self, mock_run):
        """测试验证安装成功"""
        # Mock Python 命令成功
        mock_run.side_effect = [
            Mock(returncode=0, stderr="Python 3.11.0"),  # 版本检查
            Mock(returncode=0, stdout="Hello, World!\n")  # 功能测试
        ]

        result = self.installer._verify_installation("3.11.0")

        self.assertTrue(result)
        self.assertEqual(mock_run.call_count, 2)

    @patch('subprocess.run')
    def test_verify_installation_failure(self, mock_run):
        """测试验证安装失败"""
        # Mock Python 命令失败
        mock_run.side_effect = FileNotFoundError()

        result = self.installer._verify_installation("3.11.0")

        self.assertFalse(result)

    @patch('subprocess.run')
    def test_create_virtual_environment_success(self, mock_run):
        """测试创建虚拟环境成功"""
        # Mock 查找 Python 可执行文件
        with patch.object(self.installer, '_find_python_executable', return_value='/usr/bin/python3.11'):
            # Mock 虚拟环境创建
            mock_run.return_value.returncode = 0

            result = self.installer._create_virtual_environment("3.11.0")

            self.assertTrue(result)
            expected_cmd = ['/usr/bin/python3.11', '-m', 'venv', os.path.expanduser("~/python_venv")]
            mock_run.assert_called_with(expected_cmd, timeout=300, capture_output=True, text=True)

    @patch('subprocess.run')
    @patch('platform.system')
    @patch('os.path.exists')
    def test_find_python_executable_success(self, mock_exists, mock_system, mock_run):
        """测试查找 Python 可执行文件成功"""
        mock_system.return_value = 'Linux'
        mock_exists.return_value = True

        # Mock which 命令和版本检查
        mock_which = Mock(returncode=0, stdout="/usr/bin/python3.11\n")
        mock_version = Mock(returncode=0, stderr="Python 3.11.0")
        mock_run.side_effect = [mock_which, mock_version]

        result = self.installer._find_python_executable("3.11.0")

        self.assertEqual(result, "/usr/bin/python3.11")

    def test_detect_linux_distro_ubuntu(self):
        """测试检测 Ubuntu 发行版"""
        with patch('builtins.open', unittest.mock.mock_open(read_data="NAME=Ubuntu\nVERSION=20.04")):
            with patch('os.path.exists', return_value=True):
                distro = self.installer._detect_linux_distro()
                self.assertEqual(distro, 'ubuntu')

    def test_detect_linux_distro_centos(self):
        """测试检测 CentOS 发行版"""
        with patch('os.path.exists') as mock_exists:
            def exists_side_effect(path):
                return path == '/etc/centos-release'
            mock_exists.side_effect = exists_side_effect
            distro = self.installer._detect_linux_distro()
            self.assertEqual(distro, 'centos')

    def test_progress_tracking(self):
        """测试进度跟踪"""
        # 初始状态
        progress = self.installer.get_progress()
        self.assertEqual(progress.status, PythonInstallationStatus.NOT_STARTED)
        self.assertEqual(progress.progress_percentage, 0.0)

        # 更新进度
        new_progress = PythonInstallationProgress(
            status=PythonInstallationStatus.INSTALLING,
            progress_percentage=50.0,
            current_step="Installing Python"
        )
        self.installer.progress = new_progress

        progress = self.installer.get_progress()
        self.assertEqual(progress.status, PythonInstallationStatus.INSTALLING)
        self.assertEqual(progress.progress_percentage, 50.0)
        self.assertEqual(progress.current_step, "Installing Python")

    def test_cancel_installation(self):
        """测试取消安装"""
        # 设置安装中状态
        self.installer.progress = PythonInstallationProgress(
            status=PythonInstallationStatus.INSTALLING,
            progress_percentage=50.0
        )

        with patch.object(self.installer, '_cleanup') as mock_cleanup:
            self.installer.cancel_installation()

            self.assertEqual(
                self.installer.progress.status,
                PythonInstallationStatus.CANCELLED
            )
            mock_cleanup.assert_called_once()

    def test_cleanup_temp_directory(self):
        """测试清理临时目录"""
        with tempfile.TemporaryDirectory() as temp_dir:
            self.installer.temp_dir = temp_dir

            # 创建一些测试文件
            test_file = os.path.join(temp_dir, "test.txt")
            with open(test_file, 'w') as f:
                f.write("test")

            self.installer._cleanup()

            # 目录应该被清理
            self.assertFalse(os.path.exists(temp_dir))

    def test_python_version_creation(self):
        """测试 PythonVersion 对象创建"""
        data = {
            'version': '3.11.0',
            'release_date': '2022-10-24',
            'download_url': 'https://example.com/python.exe',
            'checksum': 'sha256:abc123',
            'is_stable': True,
            'eol_date': '2027-10-24'
        }

        version = PythonVersion.from_release_data(data)

        self.assertEqual(version.version, '3.11.0')
        self.assertEqual(version.release_date, '2022-10-24')
        self.assertEqual(version.download_url, 'https://example.com/python.exe')
        self.assertEqual(version.checksum, 'sha256:abc123')
        self.assertTrue(version.is_stable)
        self.assertEqual(version.eol_date, '2027-10-24')
        self.assertEqual(str(version), 'Python 3.11.0 (Stable)')

    def test_installation_progress_to_dict(self):
        """测试安装进度转换为字典"""
        progress = PythonInstallationProgress(
            status=PythonInstallationStatus.INSTALLING,
            progress_percentage=75.0,
            current_step="Installing Python",
            error_message=None,
            download_size=1000000,
            downloaded_bytes=750000
        )

        result = progress.to_dict()

        expected = {
            'status': 'installing',
            'progress_percentage': 75.0,
            'current_step': 'Installing Python',
            'error_message': None,
            'download_size': 1000000,
            'downloaded_bytes': 750000
        }

        self.assertEqual(result, expected)


if __name__ == '__main__':
    unittest.main()