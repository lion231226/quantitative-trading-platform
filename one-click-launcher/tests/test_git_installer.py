"""
Git 安装器单元测试

测试 Git 自动安装和配置引擎的各项功能，包括安装、配置、SSH密钥生成和验证。
"""

import pytest
import unittest
from unittest.mock import Mock, patch, MagicMock, call
import tempfile
import os
import subprocess
from pathlib import Path

# 添加项目根目录到路径
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from services.git_installer import (
    GitInstaller, GitConfiguration, GitInstallationStatus,
    GitInstallationProgress
)
from core.operating_system_detector import OperatingSystem, Architecture, SystemInfo


class TestGitInstaller(unittest.TestCase):
    """GitInstaller 测试类"""

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

        # 创建 Git 安装器实例
        self.installer = GitInstaller(self.mock_os_detector, self.mock_network_checker)

    def test_init(self):
        """测试初始化"""
        self.assertIsNotNone(self.installer.os_detector)
        self.assertIsNotNone(self.installer.network_checker)
        self.assertEqual(
            self.installer.progress.status,
            GitInstallationStatus.NOT_STARTED
        )
        self.assertIsInstance(self.installer.configuration, GitConfiguration)

    def test_git_configuration_creation(self):
        """测试 GitConfiguration 对象创建"""
        config = GitConfiguration(
            user_name="Test User",
            user_email="test@example.com",
            default_editor="nano",
            default_branch="main",
            auto_crlf="true"
        )

        self.assertEqual(config.user_name, "Test User")
        self.assertEqual(config.user_email, "test@example.com")
        self.assertEqual(config.default_editor, "nano")
        self.assertEqual(config.default_branch, "main")
        self.assertEqual(config.auto_crlf, "true")

        config_dict = config.to_dict()
        expected_dict = {
            'user_name': "Test User",
            'user_email': "test@example.com",
            'default_editor': "nano",
            'default_branch': "main",
            'auto_crlf': "true",
            'ssh_key_type': "ed25519",
            'ssh_key_path': None
        }
        self.assertEqual(config_dict, expected_dict)

    @patch('subprocess.run')
    def test_check_existing_git_success(self, mock_run):
        """测试检查现有 Git 成功"""
        # Mock Git 命令成功
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "git version 2.43.0"

        result = self.installer._check_existing_git()

        self.assertTrue(result)
        mock_run.assert_called_with(['git', '--version'], capture_output=True, text=True, timeout=10)

    @patch('subprocess.run')
    def test_check_existing_git_not_found(self, mock_run):
        """测试检查现有 Git 未找到"""
        # Mock Git 命令失败
        mock_run.side_effect = FileNotFoundError()

        result = self.installer._check_existing_git()

        self.assertFalse(result)

    def test_get_download_url_windows(self):
        """测试获取 Windows Git 下载 URL"""
        self.mock_os_info.os_type = OperatingSystem.WINDOWS

        url = self.installer._get_download_url()

        self.assertIn("git-for-windows", url)
        self.assertTrue(url.endswith('.exe'))

    def test_get_download_url_macos(self):
        """测试获取 macOS Git 下载 URL"""
        # 创建macOS系统信息
        from core.operating_system_detector import OSVersion
        macos_info = SystemInfo(
            os_type=OperatingSystem.MACOS,
            architecture=Architecture.X64,
            version=OSVersion(12, 0, build=21559, name="macOS Monterey"),
            python_version="3.9.7",
            python_executable="python3",
            platform_details={},
            compatibility={'os_supported': True, 'architecture_supported': True}
        )

        # 重新设置mock返回值
        self.mock_os_detector.get_os_info.return_value = macos_info

        url = self.installer._get_download_url()

        self.assertIn("sourceforge.net", url)
        # 检查URL是否包含dmg，而不是以dmg结尾（因为可能有重定向参数）
        self.assertIn('.dmg', url)

    def test_get_download_url_linux(self):
        """测试获取 Linux Git 下载 URL"""
        self.mock_os_info.os_type = OperatingSystem.LINUX

        url = self.installer._get_download_url()

        self.assertIn("github.com", url)
        self.assertTrue(url.endswith('.tar.gz'))

    def test_auto_configure_windows(self):
        """测试 Windows 自动配置"""
        self.mock_os_info.os_type = OperatingSystem.WINDOWS

        self.installer._auto_configure()

        self.assertEqual(self.installer.configuration.default_branch, "main")
        self.assertEqual(self.installer.configuration.auto_crlf, "true")
        self.assertEqual(self.installer.configuration.default_editor, "notepad")

    def test_auto_configure_linux(self):
        """测试 Linux 自动配置"""
        self.mock_os_info.os_type = OperatingSystem.LINUX

        self.installer._auto_configure()

        self.assertEqual(self.installer.configuration.default_branch, "main")
        self.assertEqual(self.installer.configuration.auto_crlf, "input")
        self.assertEqual(self.installer.configuration.default_editor, "nano")

    @patch('subprocess.run')
    def test_install_on_windows_success(self, mock_run):
        """测试在 Windows 上安装成功"""
        installer_path = "/tmp/git-installer.exe"

        # Mock 成功的安装
        mock_run.return_value.returncode = 0
        mock_run.return_value.stderr = ""

        result = self.installer._install_on_windows(installer_path)

        self.assertTrue(result)
        expected_cmd = [
            installer_path,
            '/VERYSILENT',
            '/NORESTART',
            '/NOCANCEL',
            '/SP-',
            '/SUPPRESSMSGBOXES'
        ]
        mock_run.assert_called_with(expected_cmd, timeout=600, capture_output=True, text=True)

    @patch('subprocess.run')
    def test_install_on_windows_failure(self, mock_run):
        """测试在 Windows 上安装失败"""
        installer_path = "/tmp/git-installer.exe"

        # Mock 失败的安装
        mock_run.return_value.returncode = 1
        mock_run.return_value.stderr = "Installation failed"

        result = self.installer._install_on_windows(installer_path)

        self.assertFalse(result)

    @patch('subprocess.run')
    def test_install_on_macos_success(self, mock_run):
        """测试在 macOS 上安装成功"""
        # 设置为 macOS
        self.mock_os_info.os_type = OperatingSystem.MACOS
        self.mock_os_detector.get_os_info.return_value = self.mock_os_info

        installer_path = "/tmp/git-installer.dmg"

        # Mock DMG 挂载和安装
        mock_run.side_effect = [
            Mock(returncode=0, stdout="/Volumes/Git 2.43"),  # hdiutil attach
            Mock(returncode=0),  # installer
            Mock(returncode=0)   # hdiutil detach
        ]

        with patch('os.walk') as mock_walk:
            # Mock 文件遍历找到 PKG
            mock_walk.return_value = [
                ['/Volumes/Git 2.43', [], ['git-2.43.0-intel-universal-mavericks.pkg']]
            ]

            result = self.installer._install_on_macos(installer_path)

            self.assertTrue(result)

    @patch('subprocess.run')
    def test_install_on_linux_package_manager(self, mock_run):
        """测试在 Linux 上使用包管理器安装"""
        # 设置为 Linux
        self.mock_os_info.os_type = OperatingSystem.LINUX

        # Mock 包管理器安装
        mock_run.side_effect = [
            Mock(returncode=0),  # apt-get update
            Mock(returncode=0)   # apt-get install git
        ]

        with patch.object(self.installer, '_detect_linux_distro', return_value='ubuntu'):
            result = self.installer._install_on_linux("/tmp/any-file")

            self.assertTrue(result)

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

    @patch('subprocess.run')
    def test_configure_git_success(self, mock_run):
        """测试 Git 配置成功"""
        # 设置配置
        self.installer.configuration.user_name = "Test User"
        self.installer.configuration.user_email = "test@example.com"

        # Mock 所有配置命令成功
        mock_run.return_value.returncode = 0

        result = self.installer._configure_git()

        self.assertTrue(result)
        self.assertGreaterEqual(mock_run.call_count, 2)  # 至少 name, email

    @patch('subprocess.run')
    def test_configure_git_partial_failure(self, mock_run):
        """测试 Git 配置部分失败"""
        # 设置配置
        self.installer.configuration.user_name = "Test User"
        self.installer.configuration.user_email = "test@example.com"

        # Mock 用户名配置成功，邮箱配置失败
        mock_run.side_effect = [
            Mock(returncode=0),  # user name success
            Mock(returncode=1, stderr="Invalid email")  # user email failure
        ]

        result = self.installer._configure_git()

        self.assertFalse(result)

    @patch('os.path.exists')
    @patch('os.path.expanduser')
    def test_should_generate_ssh_key_no_existing_keys(self, mock_expanduser, mock_exists):
        """测试没有现有SSH密钥时应该生成"""
        mock_expanduser.return_value = "/tmp/.ssh"

        # Mock SSH目录存在，但所有密钥文件都不存在
        def mock_exists_func(path):
            if path == "/tmp/.ssh":
                return True
            # 所有密钥文件都不存在
            if any(key in path for key in ['id_ed25519', 'id_rsa', 'id_ecdsa']):
                return False
            return True

        mock_exists.side_effect = mock_exists_func

        result = self.installer._should_generate_ssh_key()

        self.assertTrue(result)

    @patch('os.path.exists')
    @patch('os.listdir')
    def test_should_generate_ssh_key_existing_key(self, mock_listdir, mock_exists):
        """测试已有SSH密钥时不应该生成"""
        mock_exists.return_value = True
        mock_listdir.return_value = ['id_ed25519', 'id_ed25519.pub', 'known_hosts']

        result = self.installer._should_generate_ssh_key()

        self.assertFalse(result)

    @patch('subprocess.run')
    @patch('os.makedirs')
    @patch('os.chmod')
    @patch('os.path.exists')
    def test_generate_ssh_key_success(self, mock_path_exists, mock_chmod, mock_makedirs, mock_run):
        """测试SSH密钥生成成功"""
        mock_path_exists.return_value = False
        mock_run.return_value.returncode = 0

        result = self.installer._generate_ssh_key()

        self.assertTrue(result)
        self.assertIsNotNone(self.installer.configuration.ssh_key_path)

    @patch('subprocess.run')
    @patch('os.makedirs')
    @patch('os.chmod')
    @patch('os.path.exists')
    def test_generate_ssh_key_failure(self, mock_path_exists, mock_chmod, mock_makedirs, mock_run):
        """测试SSH密钥生成失败"""
        mock_path_exists.return_value = False
        mock_run.return_value.returncode = 1
        mock_run.return_value.stderr = "Key generation failed"

        result = self.installer._generate_ssh_key()

        self.assertFalse(result)

    @patch('subprocess.run')
    @patch('tempfile.mkdtemp')
    @patch('shutil.rmtree')
    def test_verify_installation_success(self, mock_rmtree, mock_mkdtemp, mock_run):
        """测试验证安装成功"""
        mock_mkdtemp.return_value = "/tmp/git_test"

        # Mock Git 版本和基本功能
        mock_run.side_effect = [
            Mock(returncode=0, stdout="git version 2.43.0"),  # git --version
            Mock(returncode=0),  # git init
            Mock(returncode=0)   # git config --list
        ]

        result = self.installer._verify_installation()

        self.assertTrue(result)

    @patch('subprocess.run')
    def test_verify_installation_failure(self, mock_run):
        """测试验证安装失败"""
        # Mock Git 命令失败
        mock_run.side_effect = FileNotFoundError()

        result = self.installer._verify_installation()

        self.assertFalse(result)

    @patch('builtins.open', new_callable=unittest.mock.mock_open, read_data="ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAI... user@host")
    def test_get_ssh_public_key_success(self, mock_open):
        """测试获取SSH公钥成功"""
        self.installer.configuration.ssh_key_path = "/home/user/.ssh/id_ed25519"

        with patch('os.path.exists', return_value=True):
            result = self.installer.get_ssh_public_key()

            self.assertIsNotNone(result)
            self.assertIn("ssh-ed25519", result)

    def test_get_ssh_public_key_no_key(self):
        """测试没有SSH密钥时获取公钥"""
        self.installer.configuration.ssh_key_path = None

        result = self.installer.get_ssh_public_key()

        self.assertIsNone(result)

    @patch('subprocess.run')
    def test_test_git_connection_success(self, mock_run):
        """测试Git连接测试成功"""
        mock_run.return_value.returncode = 0

        result = self.installer.test_git_connection()

        self.assertTrue(result)

    @patch('subprocess.run')
    def test_test_git_connection_failure(self, mock_run):
        """测试Git连接测试失败"""
        mock_run.return_value.returncode = 1

        result = self.installer.test_git_connection()

        self.assertFalse(result)

    @patch('subprocess.run')
    def test_is_git_configured_true(self, mock_run):
        """测试Git已配置检查 - 已配置"""
        mock_run.side_effect = [
            Mock(returncode=0, stdout="Test User"),  # user.name
            Mock(returncode=0, stdout="test@example.com")  # user.email
        ]

        result = self.installer.is_git_configured()

        self.assertTrue(result)

    @patch('subprocess.run')
    def test_is_git_configured_false(self, mock_run):
        """测试Git已配置检查 - 未配置"""
        mock_run.side_effect = [
            Mock(returncode=0, stdout=""),  # user.name empty
            Mock(returncode=0, stdout="test@example.com")  # user.email
        ]

        result = self.installer.is_git_configured()

        self.assertFalse(result)

    def test_progress_tracking(self):
        """测试进度跟踪"""
        # 初始状态
        progress = self.installer.get_progress()
        self.assertEqual(progress.status, GitInstallationStatus.NOT_STARTED)
        self.assertEqual(progress.progress_percentage, 0.0)

        # 更新进度
        new_progress = GitInstallationProgress(
            status=GitInstallationStatus.INSTALLING,
            progress_percentage=50.0,
            current_step="Installing Git"
        )
        self.installer.progress = new_progress

        progress = self.installer.get_progress()
        self.assertEqual(progress.status, GitInstallationStatus.INSTALLING)
        self.assertEqual(progress.progress_percentage, 50.0)
        self.assertEqual(progress.current_step, "Installing Git")

    def test_cancel_installation(self):
        """测试取消安装"""
        # 设置安装中状态
        self.installer.progress = GitInstallationProgress(
            status=GitInstallationStatus.INSTALLING,
            progress_percentage=50.0
        )

        with patch.object(self.installer, '_cleanup') as mock_cleanup:
            self.installer.cancel_installation()

            self.assertEqual(
                self.installer.progress.status,
                GitInstallationStatus.CANCELLED
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

    def test_installation_progress_to_dict(self):
        """测试安装进度转换为字典"""
        progress = GitInstallationProgress(
            status=GitInstallationStatus.INSTALLING,
            progress_percentage=75.0,
            current_step="Installing Git",
            error_message=None,
            download_size=50000000,
            downloaded_bytes=37500000
        )

        result = progress.to_dict()

        expected = {
            'status': 'installing',
            'progress_percentage': 75.0,
            'current_step': 'Installing Git',
            'error_message': None,
            'download_size': 50000000,
            'downloaded_bytes': 37500000
        }

        self.assertEqual(result, expected)


if __name__ == '__main__':
    unittest.main()