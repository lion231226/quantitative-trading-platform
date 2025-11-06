"""
包管理器配置单元测试

测试 npm 和 pip 包管理器的配置功能，包括路径设置、包安装、注册表配置等。
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

from services.package_manager import (
    PackageManagerSetup, PackageManagerConfig, PackageManagerType,
    ConfigurationStatus, PackageInfo
)
from core.operating_system_detector import OperatingSystem, Architecture, SystemInfo


class TestPackageManagerSetup(unittest.TestCase):
    """PackageManagerSetup 测试类"""

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

        # 创建包管理器设置器实例
        self.setup = PackageManagerSetup(self.mock_os_detector)

    def test_init(self):
        """测试初始化"""
        self.assertIsNotNone(self.setup.os_detector)
        self.assertEqual(self.setup.status, ConfigurationStatus.NOT_CONFIGURED)
        self.assertIsInstance(self.setup.npm_config, PackageManagerConfig)
        self.assertIsInstance(self.setup.pip_config, PackageManagerConfig)
        self.assertIsNotNone(self.setup.essential_npm_packages)
        self.assertIsNotNone(self.setup.essential_pip_packages)

    def test_package_manager_config_creation(self):
        """测试 PackageManagerConfig 对象创建"""
        config = PackageManagerConfig(
            global_install_path="/npm-global",
            cache_path="/npm-cache",
            registry_url="https://registry.npmjs.org",
            auto_update=True
        )

        self.assertEqual(config.global_install_path, "/npm-global")
        self.assertEqual(config.cache_path, "/npm-cache")
        self.assertEqual(config.registry_url, "https://registry.npmjs.org")
        self.assertTrue(config.auto_update)

        config_dict = config.to_dict()
        expected_dict = {
            'global_install_path': "/npm-global",
            'cache_path': "/npm-cache",
            'registry_url': "https://registry.npmjs.org",
            'proxy_config': None,
            'environment_variables': None,
            'auto_update': True
        }
        self.assertEqual(config_dict, expected_dict)

    @patch('subprocess.run')
    def test_check_npm_available_success(self, mock_run):
        """测试检查 npm 可用成功"""
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "8.5.5"

        result = self.setup._check_npm_available()

        self.assertTrue(result)
        mock_run.assert_called_with(['npm', '--version'], capture_output=True, text=True, timeout=10)

    @patch('subprocess.run')
    def test_check_npm_available_failure(self, mock_run):
        """测试检查 npm 可用失败"""
        mock_run.side_effect = FileNotFoundError()

        result = self.setup._check_npm_available()

        self.assertFalse(result)

    @patch('subprocess.run')
    def test_check_pip_available_success(self, mock_run):
        """测试检查 pip 可用成功"""
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "pip 23.0.1 from ..."

        result = self.setup._check_pip_available()

        self.assertTrue(result)
        mock_run.assert_called_with(['pip', '--version'], capture_output=True, text=True, timeout=10)

    @patch('subprocess.run')
    def test_check_pip_available_failure(self, mock_run):
        """测试检查 pip 可用失败"""
        mock_run.side_effect = FileNotFoundError()

        result = self.setup._check_pip_available()

        self.assertFalse(result)

    def test_auto_configure_npm_windows(self):
        """测试 Windows 自动配置 npm"""
        self.mock_os_info.os_type = OperatingSystem.WINDOWS

        self.setup._auto_configure_npm()

        self.assertIn("npm-global", self.setup.npm_config.global_install_path)
        self.assertIn("npm-cache", self.setup.npm_config.cache_path)
        self.assertTrue(self.setup.npm_config.auto_update)

    def test_auto_configure_npm_linux(self):
        """测试 Linux 自动配置 npm"""
        self.mock_os_info.os_type = OperatingSystem.LINUX

        self.setup._auto_configure_npm()

        self.assertIn(".npm-global", self.setup.npm_config.global_install_path)
        self.assertIn(".npm-cache", self.setup.npm_config.cache_path)
        self.assertTrue(self.setup.npm_config.auto_update)

    def test_auto_configure_pip_windows(self):
        """测试 Windows 自动配置 pip"""
        self.mock_os_info.os_type = OperatingSystem.WINDOWS

        self.setup._auto_configure_pip()

        self.assertIn("pip-global", self.setup.pip_config.global_install_path)
        self.assertIn("pip-cache", self.setup.pip_config.cache_path)
        self.assertTrue(self.setup.pip_config.auto_update)

    def test_auto_configure_pip_linux(self):
        """测试 Linux 自动配置 pip"""
        self.mock_os_info.os_type = OperatingSystem.LINUX

        self.setup._auto_configure_pip()

        self.assertIn(".local", self.setup.pip_config.global_install_path)
        self.assertIn(".cache/pip", self.setup.pip_config.cache_path)
        self.assertTrue(self.setup.pip_config.auto_update)

    @patch('subprocess.run')
    def test_upgrade_npm_success(self, mock_run):
        """测试升级 npm 成功"""
        mock_run.return_value.returncode = 0

        result = self.setup._upgrade_npm()

        self.assertTrue(result)
        mock_run.assert_called_with(['npm', 'install', '-g', 'npm@latest'], timeout=300, capture_output=True, text=True)

    @patch('subprocess.run')
    def test_upgrade_npm_failure(self, mock_run):
        """测试升级 npm 失败"""
        mock_run.return_value.returncode = 1
        mock_run.return_value.stderr = "Permission denied"

        result = self.setup._upgrade_npm()

        self.assertFalse(result)

    @patch('subprocess.run')
    def test_upgrade_pip_success(self, mock_run):
        """测试升级 pip 成功"""
        mock_run.return_value.returncode = 0

        result = self.setup._upgrade_pip()

        self.assertTrue(result)
        mock_run.assert_called_with(['python', '-m', 'pip', 'install', '--upgrade', 'pip'], timeout=300, capture_output=True, text=True)

    @patch('subprocess.run')
    @patch('os.makedirs')
    @patch('os.path.exists')
    def test_set_npm_global_path_success(self, mock_exists, mock_makedirs, mock_run):
        """测试设置 npm 全局路径成功"""
        mock_exists.return_value = True
        mock_run.return_value.returncode = 0

        result = self.setup._set_npm_global_path("/test/npm-global")

        self.assertTrue(result)

    @patch('subprocess.run')
    @patch('os.makedirs')
    @patch('os.path.exists')
    def test_set_npm_global_path_failure(self, mock_exists, mock_makedirs, mock_run):
        """测试设置 npm 全局路径失败"""
        mock_exists.return_value = True
        mock_run.return_value.returncode = 1
        mock_run.return_value.stderr = "Permission denied"

        result = self.setup._set_npm_global_path("/test/npm-global")

        self.assertFalse(result)

    @patch('subprocess.run')
    @patch('os.makedirs')
    @patch('os.path.exists')
    def test_set_npm_cache_path_success(self, mock_exists, mock_makedirs, mock_run):
        """测试设置 npm 缓存路径成功"""
        mock_exists.return_value = True
        mock_run.return_value.returncode = 0

        result = self.setup._set_npm_cache_path("/test/npm-cache")

        self.assertTrue(result)

    @patch('subprocess.run')
    @patch('os.makedirs')
    @patch('os.path.exists')
    def test_set_npm_registry_success(self, mock_exists, mock_makedirs, mock_run):
        """测试设置 npm 注册表成功"""
        mock_exists.return_value = True
        mock_run.return_value.returncode = 0

        result = self.setup._set_npm_registry("https://registry.npm.taobao.org")

        self.assertTrue(result)

    @patch('subprocess.run')
    @patch('os.makedirs')
    @patch('os.path.exists')
    def test_set_npm_proxy_success(self, mock_exists, mock_makedirs, mock_run):
        """测试设置 npm 代理成功"""
        mock_exists.return_value = True
        mock_run.return_value.returncode = 0

        proxy_config = {
            'http': 'http://proxy.example.com:8080',
            'https': 'https://proxy.example.com:8080'
        }

        result = self.setup._set_npm_proxy(proxy_config)

        self.assertTrue(result)
        self.assertEqual(mock_run.call_count, 2)  # HTTP and HTTPS proxy

    @patch('subprocess.run')
    @patch('os.makedirs')
    @patch('os.path.exists')
    def test_set_npm_proxy_partial_failure(self, mock_exists, mock_makedirs, mock_run):
        """测试设置 npm 代理部分失败"""
        mock_exists.return_value = True
        mock_run.side_effect = [
            Mock(returncode=0),  # HTTP proxy success
            Mock(returncode=1)   # HTTPS proxy failure
        ]

        proxy_config = {
            'http': 'http://proxy.example.com:8080',
            'https': 'https://proxy.example.com:8080'
        }

        result = self.setup._set_npm_proxy(proxy_config)

        self.assertFalse(result)

    @patch('platform.system')
    def test_get_pip_config_dir_windows(self, mock_system):
        """测试获取 pip 配置目录 - Windows"""
        mock_system.return_value = 'Windows'

        config_dir = self.setup._get_pip_config_dir()

        self.assertTrue(config_dir.endswith('pip'))

    @patch('platform.system')
    def test_get_pip_config_dir_linux(self, mock_system):
        """测试获取 pip 配置目录 - Linux"""
        mock_system.return_value = 'Linux'

        config_dir = self.setup._get_pip_config_dir()

        self.assertTrue(config_dir.endswith('.config/pip'))

    @patch('builtins.open', new_callable=unittest.mock.mock_open)
    @patch('os.makedirs')
    @patch('os.path.exists')
    @patch('platform.system')
    def test_set_pip_global_path_success(self, mock_system, mock_exists, mock_makedirs, mock_open):
        """测试设置 pip 全局路径成功"""
        mock_system.return_value = 'Linux'
        mock_exists.return_value = False

        result = self.setup._set_pip_global_path("/test/pip-global")

        self.assertTrue(result)
        mock_makedirs.assert_called()
        mock_open.assert_called()

    @patch('builtins.open', new_callable=unittest.mock.mock_open, read_data="")
    @patch('os.makedirs')
    @patch('os.path.exists')
    @patch('platform.system')
    def test_set_pip_cache_path_success(self, mock_system, mock_exists, mock_makedirs, mock_open):
        """测试设置 pip 缓存路径成功"""
        mock_system.return_value = 'Linux'
        mock_exists.return_value = True

        result = self.setup._set_pip_cache_path("/test/pip-cache")

        self.assertTrue(result)

    @patch('builtins.open', new_callable=unittest.mock.mock_open, read_data="")
    @patch('os.makedirs')
    @patch('os.path.exists')
    @patch('platform.system')
    def test_set_pip_index_url_success(self, mock_system, mock_exists, mock_makedirs, mock_open):
        """测试设置 pip 索引 URL 成功"""
        mock_system.return_value = 'Linux'
        mock_exists.return_value = True

        result = self.setup._set_pip_index_url("https://pypi.tuna.tsinghua.edu.cn/simple/")

        self.assertTrue(result)

    @patch('builtins.open', new_callable=unittest.mock.mock_open, read_data="")
    @patch('os.makedirs')
    @patch('os.path.exists')
    @patch('platform.system')
    def test_set_pip_proxy_success(self, mock_system, mock_exists, mock_makedirs, mock_open):
        """测试设置 pip 代理成功"""
        mock_system.return_value = 'Linux'
        mock_exists.return_value = True

        proxy_config = {
            'http': 'http://proxy.example.com:8080',
            'https': 'https://proxy.example.com:8080'
        }

        result = self.setup._set_pip_proxy(proxy_config)

        self.assertTrue(result)

    @patch('subprocess.run')
    def test_install_essential_npm_packages_success(self, mock_run):
        """测试安装基本 npm 包成功"""
        mock_run.return_value.returncode = 0

        # 减少包数量以加快测试
        self.setup.essential_npm_packages = ['typescript', 'eslint']

        result = self.setup._install_essential_npm_packages()

        self.assertTrue(result)
        self.assertEqual(mock_run.call_count, 2)

    @patch('subprocess.run')
    def test_install_essential_npm_packages_partial_failure(self, mock_run):
        """测试安装基本 npm 包部分失败"""
        mock_run.side_effect = [
            Mock(returncode=0),  # First package success
            Mock(returncode=1)   # Second package failure
        ]

        # 减少包数量以加快测试
        self.setup.essential_npm_packages = ['typescript', 'eslint']

        result = self.setup._install_essential_npm_packages()

        self.assertTrue(result)  # At least half succeed

    @patch('subprocess.run')
    def test_install_essential_pip_packages_success(self, mock_run):
        """测试安装基本 pip 包成功"""
        mock_run.return_value.returncode = 0

        # 减少包数量以加快测试
        self.setup.essential_pip_packages = ['setuptools', 'wheel']

        result = self.setup._install_essential_pip_packages()

        self.assertTrue(result)
        self.assertEqual(mock_run.call_count, 2)

    @patch('subprocess.run')
    @patch('builtins.open', new_callable=unittest.mock.mock_open, read_data='[global]\n')
    @patch('os.path.exists')
    def test_verify_npm_configuration_success(self, mock_exists, mock_open, mock_run):
        """测试验证 npm 配置成功"""
        # 设置配置
        self.setup.npm_config.global_install_path = "/test/path"

        # Mock npm config list 输出包含设置的配置
        mock_run.return_value = Mock(
            returncode=0,
            stdout='prefix = "/test/path"\n'
        )

        result = self.setup._verify_npm_configuration()

        # 当配置匹配时应该返回 True
        self.assertTrue(result)

    @patch('os.path.exists')
    def test_verify_pip_configuration_no_file(self, mock_exists):
        """测试验证 pip 配置 - 无配置文件"""
        mock_exists.return_value = False

        result = self.setup._verify_pip_configuration()

        self.assertTrue(result)  # No config file means default config

    @patch('builtins.open', new_callable=unittest.mock.mock_open, read_data='[global]\ntarget = /test/path\n')
    @patch('os.path.exists')
    def test_verify_pip_configuration_with_file(self, mock_exists, mock_open):
        """测试验证 pip 配置 - 有配置文件"""
        mock_exists.return_value = True

        result = self.setup._verify_pip_configuration()

        self.assertTrue(result)

    @patch('subprocess.run')
    def test_test_npm_functionality_success(self, mock_run):
        """测试 npm 功能测试成功"""
        mock_run.side_effect = [
            Mock(returncode=0, stdout="8.5.5"),  # npm --version
            Mock(returncode=0)  # npm list -g
        ]

        result = self.setup.test_npm_functionality()

        self.assertTrue(result)

    @patch('subprocess.run')
    def test_test_npm_functionality_failure(self, mock_run):
        """测试 npm 功能测试失败"""
        mock_run.return_value.returncode = 1

        result = self.setup.test_npm_functionality()

        self.assertFalse(result)

    @patch('subprocess.run')
    def test_test_pip_functionality_success(self, mock_run):
        """测试 pip 功能测试成功"""
        mock_run.side_effect = [
            Mock(returncode=0, stdout="pip 23.0.1"),  # pip --version
            Mock(returncode=0)  # pip list
        ]

        result = self.setup.test_pip_functionality()

        self.assertTrue(result)

    @patch('subprocess.run')
    def test_test_pip_functionality_failure(self, mock_run):
        """测试 pip 功能测试失败"""
        mock_run.return_value.returncode = 1

        result = self.setup.test_pip_functionality()

        self.assertFalse(result)

    def test_get_status(self):
        """测试获取状态"""
        status = self.setup.get_status()
        self.assertEqual(status, ConfigurationStatus.NOT_CONFIGURED)

    def test_get_npm_config(self):
        """测试获取 npm 配置"""
        config = self.setup.get_npm_config()
        self.assertIsInstance(config, PackageManagerConfig)

    def test_get_pip_config(self):
        """测试获取 pip 配置"""
        config = self.setup.get_pip_config()
        self.assertIsInstance(config, PackageManagerConfig)

    def test_package_info_creation(self):
        """测试 PackageInfo 对象创建"""
        package = PackageInfo(
            name="test-package",
            version="1.0.0",
            is_global=True,
            is_dev_dependency=False
        )

        self.assertEqual(package.name, "test-package")
        self.assertEqual(package.version, "1.0.0")
        self.assertTrue(package.is_global)
        self.assertFalse(package.is_dev_dependency)

        package_dict = package.to_dict()
        expected_dict = {
            'name': 'test-package',
            'version': '1.0.0',
            'is_global': True,
            'is_dev_dependency': False,
            'install_time': None
        }
        self.assertEqual(package_dict, expected_dict)

    @patch('subprocess.run')
    @patch('builtins.open', new_callable=unittest.mock.mock_open)
    @patch('os.path.exists')
    @patch('os.remove')
    def test_reset_pip_config_success(self, mock_remove, mock_exists, mock_open, mock_run):
        """测试重置 pip 配置成功"""
        mock_exists.return_value = True
        mock_run.return_value.returncode = 0

        result = self.setup.reset_pip_config()

        self.assertTrue(result)
        mock_remove.assert_called_once()

    @patch('subprocess.run')
    def test_reset_pip_config_no_file(self, mock_run):
        """测试重置 pip 配置 - 无配置文件"""
        with patch('os.path.exists', return_value=False):
            mock_run.return_value.returncode = 0

            result = self.setup.reset_pip_config()

            self.assertTrue(result)


if __name__ == '__main__':
    unittest.main()