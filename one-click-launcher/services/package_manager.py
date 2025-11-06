"""
包管理器配置和设置引擎

此模块提供 npm 和 pip 包管理器的配置功能，包括全局包路径设置、
版本升级、基本开发包安装和注册表配置。
"""

import os
import platform
import subprocess
from typing import Dict, Optional, Any
from dataclasses import dataclass
from enum import Enum

from utils.logger import get_logger
from core.operating_system_detector import OperatingSystem

logger = get_logger(__name__)


class PackageManagerType(Enum):
    """包管理器类型枚举"""
    NPM = "npm"
    PIP = "pip"
    YARN = "yarn"
    PNPM = "pnpm"


class ConfigurationStatus(Enum):
    """配置状态枚举"""
    NOT_CONFIGURED = "not_configured"
    CONFIGURING = "configuring"
    CONFIGURED = "configured"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class PackageManagerConfig:
    """包管理器配置信息"""
    global_install_path: Optional[str] = None
    cache_path: Optional[str] = None
    registry_url: Optional[str] = None
    proxy_config: Optional[Dict[str, str]] = None
    environment_variables: Optional[Dict[str, str]] = None
    auto_update: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'global_install_path': self.global_install_path,
            'cache_path': self.cache_path,
            'registry_url': self.registry_url,
            'proxy_config': self.proxy_config,
            'environment_variables': self.environment_variables,
            'auto_update': self.auto_update
        }


@dataclass
class PackageInfo:
    """包信息"""
    name: str
    version: Optional[str] = None
    is_global: bool = False
    is_dev_dependency: bool = False
    install_time: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'name': self.name,
            'version': self.version,
            'is_global': self.is_global,
            'is_dev_dependency': self.is_dev_dependency,
            'install_time': self.install_time
        }


class PackageManagerSetup:
    """
    包管理器配置和设置器

    功能特性：
    - 配置 npm 和 pip 的全局安装路径
    - 升级包管理器到最新版本
    - 安装基本的开发工具和依赖
    - 配置包注册表和镜像源
    - 环境变量管理
    - 代理配置
    """

    def __init__(self, os_detector):
        """
        初始化包管理器设置器

        Args:
            os_detector: 操作系统检测器
        """
        self.os_detector = os_detector
        self.npm_config = PackageManagerConfig()
        self.pip_config = PackageManagerConfig()
        self.status = ConfigurationStatus.NOT_CONFIGURED

        # 基本开发包列表
        self.essential_npm_packages = [
            "typescript",
            "ts-node",
            "nodemon",
            "eslint",
            "prettier",
            "@types/node",
            "node-gyp",
            "webpack",
            "rollup",
            "vite"
        ]

        self.essential_pip_packages = [
            "setuptools",
            "wheel",
            "pip",
            "virtualenv",
            "black",
            "flake8",
            "mypy",
            "pytest",
            "requests",
            "python-dotenv",
            "build",
            "twine"
        ]

        logger.info(f"PackageManagerSetup initialized for {os_detector.get_os_info()}")

    def configure_npm(self, config: Optional[PackageManagerConfig] = None) -> bool:
        """
        配置 npm 包管理器

        Args:
            config: npm 配置信息，如果为 None 则使用默认配置

        Returns:
            配置是否成功
        """
        try:
            logger.info("Configuring npm package manager")

            self.status = ConfigurationStatus.CONFIGURING

            if config:
                self.npm_config = config
            else:
                self._auto_configure_npm()

            # 检查 npm 是否可用
            if not self._check_npm_available():
                logger.error("npm is not available for configuration")
                self.status = ConfigurationStatus.FAILED
                return False

            # 升级 npm 到最新版本
            if self.npm_config.auto_update:
                self._upgrade_npm()

            # 设置全局安装路径
            if self.npm_config.global_install_path:
                self._set_npm_global_path(self.npm_config.global_install_path)

            # 设置缓存路径
            if self.npm_config.cache_path:
                self._set_npm_cache_path(self.npm_config.cache_path)

            # 配置注册表
            if self.npm_config.registry_url:
                self._set_npm_registry(self.npm_config.registry_url)

            # 配置代理
            if self.npm_config.proxy_config:
                self._set_npm_proxy(self.npm_config.proxy_config)

            # 安装基本包
            self._install_essential_npm_packages()

            # 验证配置
            if self._verify_npm_configuration():
                self.status = ConfigurationStatus.CONFIGURED
                logger.info("npm configuration completed successfully")
                return True
            else:
                self.status = ConfigurationStatus.FAILED
                logger.error("npm configuration verification failed")
                return False

        except Exception as e:
            logger.error(f"Failed to configure npm: {e}")
            self.status = ConfigurationStatus.FAILED
            return False

    def configure_pip(self, config: Optional[PackageManagerConfig] = None) -> bool:
        """
        配置 pip 包管理器

        Args:
            config: pip 配置信息，如果为 None 则使用默认配置

        Returns:
            配置是否成功
        """
        try:
            logger.info("Configuring pip package manager")

            if config:
                self.pip_config = config
            else:
                self._auto_configure_pip()

            # 检查 pip 是否可用
            if not self._check_pip_available():
                logger.error("pip is not available for configuration")
                return False

            # 升级 pip 到最新版本
            if self.pip_config.auto_update:
                self._upgrade_pip()

            # 设置全局安装路径
            if self.pip_config.global_install_path:
                self._set_pip_global_path(self.pip_config.global_install_path)

            # 设置缓存路径
            if self.pip_config.cache_path:
                self._set_pip_cache_path(self.pip_config.cache_path)

            # 配置注册表（索引源）
            if self.pip_config.registry_url:
                self._set_pip_index_url(self.pip_config.registry_url)

            # 配置代理
            if self.pip_config.proxy_config:
                self._set_pip_proxy(self.pip_config.proxy_config)

            # 安装基本包
            self._install_essential_pip_packages()

            # 验证配置
            if self._verify_pip_configuration():
                logger.info("pip configuration completed successfully")
                return True
            else:
                logger.error("pip configuration verification failed")
                return False

        except Exception as e:
            logger.error(f"Failed to configure pip: {e}")
            return False

    def _auto_configure_npm(self):
        """自动配置 npm 设置"""
        os_info = self.os_detector.get_os_info()

        # 设置默认全局安装路径
        if os_info.os_type == OperatingSystem.WINDOWS:
            global_path = os.path.expanduser("~/npm-global")
            cache_path = os.path.expanduser("~/npm-cache")
        else:
            global_path = os.path.expanduser("~/.npm-global")
            cache_path = os.path.expanduser("~/.npm-cache")

        self.npm_config = PackageManagerConfig(
            global_install_path=global_path,
            cache_path=cache_path,
            registry_url=None,  # 使用默认 npm 源
            auto_update=True
        )

        logger.info(f"Auto-configured npm with global path: {global_path}")

    def _auto_configure_pip(self):
        """自动配置 pip 设置"""
        os_info = self.os_detector.get_os_info()

        # 设置默认路径
        if os_info.os_type == OperatingSystem.WINDOWS:
            global_path = os.path.expanduser("~/pip-global")
            cache_path = os.path.expanduser("~/pip-cache")
        else:
            global_path = os.path.expanduser("~/.local")
            cache_path = os.path.expanduser("~/.cache/pip")

        # 默认不配置镜像源，让用户根据需要配置
        self.pip_config = PackageManagerConfig(
            global_install_path=global_path,
            cache_path=cache_path,
            registry_url=None,  # 使用默认 PyPI
            auto_update=True
        )

        logger.info(f"Auto-configured pip with global path: {global_path}")

    def _check_npm_available(self) -> bool:
        """
        检查 npm 是否可用

        Returns:
            npm 是否可用
        """
        try:
            result = subprocess.run(['npm', '--version'],
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                logger.info(f"npm version: {result.stdout.strip()}")
                return True
            return False
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def _check_pip_available(self) -> bool:
        """
        检查 pip 是否可用

        Returns:
            pip 是否可用
        """
        try:
            result = subprocess.run(['pip', '--version'],
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                logger.info(f"pip version: {result.stdout.strip()}")
                return True
            return False
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def _upgrade_npm(self) -> bool:
        """
        升级 npm 到最新版本

        Returns:
            升级是否成功
        """
        try:
            logger.info("Upgrading npm to latest version")

            cmd = ['npm', 'install', '-g', 'npm@latest']
            result = subprocess.run(cmd, timeout=300, capture_output=True, text=True)

            if result.returncode == 0:
                logger.info("npm upgrade completed successfully")
                return True
            else:
                logger.warning(f"npm upgrade failed: {result.stderr}")
                return False

        except Exception as e:
            logger.warning(f"Failed to upgrade npm: {e}")
            return False

    def _upgrade_pip(self) -> bool:
        """
        升级 pip 到最新版本

        Returns:
            升级是否成功
        """
        try:
            logger.info("Upgrading pip to latest version")

            cmd = ['python', '-m', 'pip', 'install', '--upgrade', 'pip']
            result = subprocess.run(cmd, timeout=300, capture_output=True, text=True)

            if result.returncode == 0:
                logger.info("pip upgrade completed successfully")
                return True
            else:
                logger.warning(f"pip upgrade failed: {result.stderr}")
                return False

        except Exception as e:
            logger.warning(f"Failed to upgrade pip: {e}")
            return False

    def _set_npm_global_path(self, path: str) -> bool:
        """
        设置 npm 全局安装路径

        Args:
            path: 全局安装路径

        Returns:
            设置是否成功
        """
        try:
            logger.info(f"Setting npm global path to: {path}")

            # 创建目录
            os.makedirs(path, exist_ok=True)

            # 设置 npm 全局路径
            cmd = ['npm', 'config', 'set', 'prefix', path]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                # 添加到 PATH 环境变量
                bin_path = os.path.join(path, 'bin' if platform.system() != 'Windows' else '')
                if os.path.exists(bin_path) or platform.system() == 'Windows':
                    self._add_to_path(bin_path)

                logger.info(f"npm global path set to: {path}")
                return True
            else:
                logger.error(f"Failed to set npm global path: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"Failed to set npm global path: {e}")
            return False

    def _set_npm_cache_path(self, path: str) -> bool:
        """
        设置 npm 缓存路径

        Args:
            path: 缓存路径

        Returns:
            设置是否成功
        """
        try:
            logger.info(f"Setting npm cache path to: {path}")

            # 创建目录
            os.makedirs(path, exist_ok=True)

            # 设置 npm 缓存路径
            cmd = ['npm', 'config', 'set', 'cache', path]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                logger.info(f"npm cache path set to: {path}")
                return True
            else:
                logger.error(f"Failed to set npm cache path: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"Failed to set npm cache path: {e}")
            return False

    def _set_npm_registry(self, registry_url: str) -> bool:
        """
        设置 npm 注册表

        Args:
            registry_url: 注册表 URL

        Returns:
            设置是否成功
        """
        try:
            logger.info(f"Setting npm registry to: {registry_url}")

            cmd = ['npm', 'config', 'set', 'registry', registry_url]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                logger.info(f"npm registry set to: {registry_url}")
                return True
            else:
                logger.error(f"Failed to set npm registry: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"Failed to set npm registry: {e}")
            return False

    def _set_npm_proxy(self, proxy_config: Dict[str, str]) -> bool:
        """
        设置 npm 代理配置

        Args:
            proxy_config: 代理配置

        Returns:
            设置是否成功
        """
        try:
            logger.info("Setting npm proxy configuration")

            success = True

            # 设置 HTTP 代理
            if 'http' in proxy_config:
                cmd = ['npm', 'config', 'set', 'proxy', proxy_config['http']]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                if result.returncode != 0:
                    logger.error(f"Failed to set npm HTTP proxy: {result.stderr}")
                    success = False

            # 设置 HTTPS 代理
            if 'https' in proxy_config:
                cmd = ['npm', 'config', 'set', 'https-proxy', proxy_config['https']]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                if result.returncode != 0:
                    logger.error(f"Failed to set npm HTTPS proxy: {result.stderr}")
                    success = False

            if success:
                logger.info("npm proxy configuration completed successfully")

            return success

        except Exception as e:
            logger.error(f"Failed to set npm proxy: {e}")
            return False

    def _set_pip_global_path(self, path: str) -> bool:
        """
        设置 pip 全局安装路径

        Args:
            path: 全局安装路径

        Returns:
            设置是否成功
        """
        try:
            logger.info(f"Setting pip global path to: {path}")

            # 创建目录
            os.makedirs(path, exist_ok=True)

            # 创建 pip 配置目录
            config_dir = self._get_pip_config_dir()
            os.makedirs(config_dir, exist_ok=True)

            # 创建或更新 pip.conf 文件
            config_file = os.path.join(config_dir, 'pip.conf' if platform.system() != 'Windows' else 'pip.ini')

            config_content = f"[global]\ntarget = {path}\n"

            # 读取现有配置
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    existing_content = f.read()
                # 如果已有 target 配置，不重复添加
                if 'target =' in existing_content:
                    logger.info("pip global path already configured")
                    return True

            # 写入配置
            with open(config_file, 'w') as f:
                if os.path.exists(config_file):
                    f.write(existing_content + '\n' + config_content)
                else:
                    f.write(config_content)

            # 添加到 PATH
            scripts_path = os.path.join(path, 'Scripts' if platform.system() == 'Windows' else 'bin')
            self._add_to_path(scripts_path)

            logger.info(f"pip global path set to: {path}")
            return True

        except Exception as e:
            logger.error(f"Failed to set pip global path: {e}")
            return False

    def _set_pip_cache_path(self, path: str) -> bool:
        """
        设置 pip 缓存路径

        Args:
            path: 缓存路径

        Returns:
            设置是否成功
        """
        try:
            logger.info(f"Setting pip cache path to: {path}")

            # 创建目录
            os.makedirs(path, exist_ok=True)

            # 创建 pip 配置目录
            config_dir = self._get_pip_config_dir()
            os.makedirs(config_dir, exist_ok=True)

            # 创建或更新 pip.conf 文件
            config_file = os.path.join(config_dir, 'pip.conf' if platform.system() != 'Windows' else 'pip.ini')

            config_content = f"cache-dir = {path}\n"

            # 读取现有配置
            existing_content = ""
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    existing_content = f.read()

            # 如果已有 cache-dir 配置，更新它
            if 'cache-dir =' in existing_content:
                import re
                existing_content = re.sub(r'cache-dir\s*=\s*[^\n]+', f'cache-dir = {path}', existing_content)
            else:
                # 添加新配置
                if existing_content and not existing_content.endswith('\n'):
                    existing_content += '\n'
                if not existing_content.startswith('[global]'):
                    existing_content = '[global]\n' + existing_content
                existing_content += config_content

            # 写入配置
            with open(config_file, 'w') as f:
                f.write(existing_content)

            logger.info(f"pip cache path set to: {path}")
            return True

        except Exception as e:
            logger.error(f"Failed to set pip cache path: {e}")
            return False

    def _set_pip_index_url(self, index_url: str) -> bool:
        """
        设置 pip 索引 URL

        Args:
            index_url: 索引 URL

        Returns:
            设置是否成功
        """
        try:
            logger.info(f"Setting pip index URL to: {index_url}")

            # 创建 pip 配置目录
            config_dir = self._get_pip_config_dir()
            os.makedirs(config_dir, exist_ok=True)

            # 创建或更新 pip.conf 文件
            config_file = os.path.join(config_dir, 'pip.conf' if platform.system() != 'Windows' else 'pip.ini')

            config_content = f"index-url = {index_url}\n"

            # 读取现有配置
            existing_content = ""
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    existing_content = f.read()

            # 如果已有 index-url 配置，更新它
            if 'index-url =' in existing_content:
                import re
                existing_content = re.sub(r'index-url\s*=\s*[^\n]+', f'index-url = {index_url}', existing_content)
            else:
                # 添加新配置
                if existing_content and not existing_content.endswith('\n'):
                    existing_content += '\n'
                if not existing_content.startswith('[global]'):
                    existing_content = '[global]\n' + existing_content
                existing_content += config_content

            # 写入配置
            with open(config_file, 'w') as f:
                f.write(existing_content)

            logger.info(f"pip index URL set to: {index_url}")
            return True

        except Exception as e:
            logger.error(f"Failed to set pip index URL: {e}")
            return False

    def _set_pip_proxy(self, proxy_config: Dict[str, str]) -> bool:
        """
        设置 pip 代理配置

        Args:
            proxy_config: 代理配置

        Returns:
            设置是否成功
        """
        try:
            logger.info("Setting pip proxy configuration")

            # 创建 pip 配置目录
            config_dir = self._get_pip_config_dir()
            os.makedirs(config_dir, exist_ok=True)

            # 创建或更新 pip.conf 文件
            config_file = os.path.join(config_dir, 'pip.conf' if platform.system() != 'Windows' else 'pip.ini')

            # 读取现有配置
            existing_content = ""
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    existing_content = f.read()

            # 确保有 [global] 部分
            if not existing_content.startswith('[global]'):
                existing_content = '[global]\n' + existing_content

            # 添加代理配置
            if 'http' in proxy_config:
                if 'proxy =' in existing_content:
                    import re
                    existing_content = re.sub(r'proxy\s*=\s*[^\n]+', f'proxy = {proxy_config["http"]}', existing_content)
                else:
                    existing_content += f'proxy = {proxy_config["http"]}\n'

            if 'https' in proxy_config:
                if 'proxy =' in existing_content and 'https' not in proxy_config.get('http', ''):
                    import re
                    existing_content = re.sub(r'proxy\s*=\s*[^\n]+', f'proxy = {proxy_config["https"]}', existing_content)
                elif 'https-proxy =' not in existing_content:
                    existing_content += f'proxy = {proxy_config["https"]}\n'

            # 写入配置
            with open(config_file, 'w') as f:
                f.write(existing_content)

            logger.info("pip proxy configuration completed successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to set pip proxy: {e}")
            return False

    def _get_pip_config_dir(self) -> str:
        """
        获取 pip 配置目录

        Returns:
            pip 配置目录路径
        """
        if platform.system() == 'Windows':
            return os.path.expanduser("~/pip")
        else:
            return os.path.expanduser("~/.config/pip")

    def _add_to_path(self, path: str) -> None:
        """
        添加路径到 PATH 环境变量

        Args:
            path: 要添加的路径
        """
        try:
            if not os.path.exists(path):
                return

            current_path = os.environ.get('PATH', '')
            if path not in current_path:
                os.environ['PATH'] = path + os.pathsep + current_path
                logger.info(f"Added {path} to PATH")

        except Exception as e:
            logger.warning(f"Failed to add {path} to PATH: {e}")

    def _install_essential_npm_packages(self) -> bool:
        """
        安装基本的 npm 包

        Returns:
            安装是否成功
        """
        try:
            logger.info("Installing essential npm packages")

            failed_packages = []

            for package in self.essential_npm_packages:
                try:
                    cmd = ['npm', 'install', '-g', package]
                    result = subprocess.run(cmd, timeout=300, capture_output=True, text=True)

                    if result.returncode == 0:
                        logger.info(f"Successfully installed npm package: {package}")
                    else:
                        logger.warning(f"Failed to install npm package: {package} - {result.stderr}")
                        failed_packages.append(package)

                except subprocess.TimeoutExpired:
                    logger.error(f"Timeout installing npm package: {package}")
                    failed_packages.append(package)

            if failed_packages:
                logger.warning(f"Some npm packages failed to install: {failed_packages}")
                return len(failed_packages) <= len(self.essential_npm_packages) // 2  # 至少一半成功
            else:
                logger.info("All essential npm packages installed successfully")
                return True

        except Exception as e:
            logger.error(f"Failed to install essential npm packages: {e}")
            return False

    def _install_essential_pip_packages(self) -> bool:
        """
        安装基本的 pip 包

        Returns:
            安装是否成功
        """
        try:
            logger.info("Installing essential pip packages")

            failed_packages = []

            for package in self.essential_pip_packages:
                try:
                    cmd = ['pip', 'install', '--upgrade', package]
                    result = subprocess.run(cmd, timeout=300, capture_output=True, text=True)

                    if result.returncode == 0:
                        logger.info(f"Successfully installed pip package: {package}")
                    else:
                        logger.warning(f"Failed to install pip package: {package} - {result.stderr}")
                        failed_packages.append(package)

                except subprocess.TimeoutExpired:
                    logger.error(f"Timeout installing pip package: {package}")
                    failed_packages.append(package)

            if failed_packages:
                logger.warning(f"Some pip packages failed to install: {failed_packages}")
                return len(failed_packages) < len(self.essential_pip_packages) // 2  # 至少一半成功
            else:
                logger.info("All essential pip packages installed successfully")
                return True

        except Exception as e:
            logger.error(f"Failed to install essential pip packages: {e}")
            return False

    def _verify_npm_configuration(self) -> bool:
        """
        验证 npm 配置

        Returns:
            验证是否成功
        """
        try:
            # 检查 npm 配置
            cmd = ['npm', 'config', 'list']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                return False

            config_output = result.stdout

            # 验证基本配置
            checks = []

            if self.npm_config.global_install_path:
                checks.append(f'prefix = "{self.npm_config.global_install_path}"' in config_output or
                            f'prefix = {self.npm_config.global_install_path}' in config_output)

            if self.npm_config.cache_path:
                checks.append(f'cache = "{self.npm_config.cache_path}"' in config_output or
                            f'cache = {self.npm_config.cache_path}' in config_output)

            if self.npm_config.registry_url:
                checks.append(f'registry = "{self.npm_config.registry_url}"' in config_output or
                            f'registry = {self.npm_config.registry_url}' in config_output)

            # 如果没有特定配置要求，至少要能正常运行
            if not checks:
                checks.append(True)

            return all(checks)

        except Exception as e:
            logger.error(f"Failed to verify npm configuration: {e}")
            return False

    def _verify_pip_configuration(self) -> bool:
        """
        验证 pip 配置

        Returns:
            验证是否成功
        """
        try:
            config_dir = self._get_pip_config_dir()
            config_file = os.path.join(config_dir, 'pip.conf' if platform.system() != 'Windows' else 'pip.ini')

            if not os.path.exists(config_file):
                # 如果没有配置文件，说明使用默认配置
                return True

            with open(config_file, 'r') as f:
                config_content = f.read()

            # 基本验证配置文件格式
            return '[global]' in config_content or len(config_content.strip()) == 0

        except Exception as e:
            logger.error(f"Failed to verify pip configuration: {e}")
            return False

    def get_status(self) -> ConfigurationStatus:
        """
        获取当前配置状态

        Returns:
            配置状态
        """
        return self.status

    def get_npm_config(self) -> PackageManagerConfig:
        """
        获取 npm 配置

        Returns:
            npm 配置对象
        """
        return self.npm_config

    def get_pip_config(self) -> PackageManagerConfig:
        """
        获取 pip 配置

        Returns:
            pip 配置对象
        """
        return self.pip_config

    def test_npm_functionality(self) -> bool:
        """
        测试 npm 功能

        Returns:
            功能测试是否成功
        """
        try:
            # 测试 npm 命令
            result = subprocess.run(['npm', '--version'],
                                  capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                return False

            # 测试全局包安装
            test_cmd = ['npm', 'list', '-g', '--depth=0']
            result = subprocess.run(test_cmd, capture_output=True, text=True, timeout=30)

            return result.returncode == 0

        except Exception as e:
            logger.error(f"npm functionality test failed: {e}")
            return False

    def test_pip_functionality(self) -> bool:
        """
        测试 pip 功能

        Returns:
            功能测试是否成功
        """
        try:
            # 测试 pip 命令
            result = subprocess.run(['pip', '--version'],
                                  capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                return False

            # 测试包列表
            test_cmd = ['pip', 'list']
            result = subprocess.run(test_cmd, capture_output=True, text=True, timeout=30)

            return result.returncode == 0

        except Exception as e:
            logger.error(f"pip functionality test failed: {e}")
            return False

    def reset_npm_config(self) -> bool:
        """
        重置 npm 配置到默认值

        Returns:
            重置是否成功
        """
        try:
            logger.info("Resetting npm configuration to defaults")

            # 清除 npm 配置
            cmd = ['npm', 'config', 'delete', 'prefix']
            subprocess.run(cmd, capture_output=True, timeout=30)

            cmd = ['npm', 'config', 'delete', 'cache']
            subprocess.run(cmd, capture_output=True, timeout=30)

            cmd = ['npm', 'config', 'delete', 'registry']
            subprocess.run(cmd, capture_output=True, timeout=30)

            # 重新配置
            self._auto_configure_npm()
            return self.configure_npm()

        except Exception as e:
            logger.error(f"Failed to reset npm configuration: {e}")
            return False

    def reset_pip_config(self) -> bool:
        """
        重置 pip 配置到默认值

        Returns:
            重置是否成功
        """
        try:
            logger.info("Resetting pip configuration to defaults")

            # 删除 pip 配置文件
            config_dir = self._get_pip_config_dir()
            config_file = os.path.join(config_dir, 'pip.conf' if platform.system() != 'Windows' else 'pip.ini')

            if os.path.exists(config_file):
                os.remove(config_file)

            # 重新配置
            self._auto_configure_pip()
            return self.configure_pip()

        except Exception as e:
            logger.error(f"Failed to reset pip configuration: {e}")
            return False