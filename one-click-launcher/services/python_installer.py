"""
Python 自动安装引擎

此模块提供跨平台的 Python 自动安装功能，支持 Windows、macOS 和 Linux 系统。
包括 Python 3.8+ 版本检测、下载、安装和验证功能。
"""

import os
import platform
import subprocess
import tempfile
import shutil
import json
import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import urllib.request
import urllib.error
import zipfile
import tarfile

from utils.logger import get_logger
from core.operating_system_detector import OperatingSystem, Architecture
from utils.network_utils import NetworkChecker

logger = get_logger(__name__)


class PythonInstallationStatus(Enum):
    """Python安装状态枚举"""
    NOT_STARTED = "not_started"
    DOWNLOADING = "downloading"
    INSTALLING = "installing"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class PythonVersion:
    """Python 版本信息"""
    version: str
    release_date: str
    download_url: str
    checksum: str
    is_stable: bool = True
    eol_date: Optional[str] = None

    def __str__(self) -> str:
        stable_str = " (Stable)" if self.is_stable else " (Pre-release)"
        return f"Python {self.version}{stable_str}"

    @classmethod
    def from_release_data(cls, data: Dict[str, Any]) -> 'PythonVersion':
        """从发布数据创建版本对象"""
        return cls(
            version=data.get('version', ''),
            release_date=data.get('release_date', ''),
            download_url=data.get('download_url', ''),
            checksum=data.get('checksum', ''),
            is_stable=data.get('is_stable', True),
            eol_date=data.get('eol_date')
        )


@dataclass
class PythonInstallationProgress:
    """Python安装进度信息"""
    status: PythonInstallationStatus
    progress_percentage: float = 0.0
    current_step: str = ""
    error_message: Optional[str] = None
    download_size: Optional[int] = None
    downloaded_bytes: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'status': self.status.value,
            'progress_percentage': self.progress_percentage,
            'current_step': self.current_step,
            'error_message': self.error_message,
            'download_size': self.download_size,
            'downloaded_bytes': self.downloaded_bytes
        }


class PythonInstaller:
    """
    Python 跨平台自动安装器

    功能特性：
    - 自动检测操作系统和架构
    - 获取最新的 Python 3.8+ 版本
    - 跨平台下载和安装
    - 安装进度跟踪
    - 错误处理和回滚
    - 安装验证
    - 虚拟环境创建
    """

    def __init__(self, os_detector, network_checker: NetworkChecker):
        """
        初始化 Python 安装器

        Args:
            os_detector: 操作系统检测器
            network_checker: 网络检查器
        """
        self.os_detector = os_detector
        self.network_checker = network_checker
        self.temp_dir = None
        self.progress = PythonInstallationProgress(
            status=PythonInstallationStatus.NOT_STARTED
        )

        # Python 官方 API 配置
        self.python_api_base = "https://api.github.com/repos/python/cpython/releases"
        self.python_download_base = "https://www.python.org/downloads/"

        # 最小支持版本
        self.min_version = "3.8"

        logger.info(f"PythonInstaller initialized for {os_detector.get_os_info()}")

    def get_available_versions(self, min_version: Optional[str] = None) -> List[PythonVersion]:
        """
        获取可用的 Python 版本列表

        Args:
            min_version: 最小版本要求，默认为 3.8

        Returns:
            可用的 Python 版本列表
        """
        try:
            min_version = min_version or self.min_version
            logger.info(f"Fetching Python versions >= {min_version}")

            # 检查网络连接
            if not self.network_checker.check_connectivity():
                raise Exception("No internet connection available")

            # 获取发布数据
            versions = self._fetch_release_data(min_version)

            # 排序版本（最新的在前）
            versions.sort(key=lambda x: tuple(map(int, x.version.split('.'))), reverse=True)

            logger.info(f"Found {len(versions)} Python versions available")
            return versions

        except Exception as e:
            logger.error(f"Failed to fetch Python versions: {e}")
            raise

    def _fetch_release_data(self, min_version: str) -> List[PythonVersion]:
        """
        从 GitHub API 获取发布数据

        Args:
            min_version: 最小版本要求

        Returns:
            Python 版本列表
        """
        try:
            # 构建 API URL
            url = f"{self.python_api_base}?per_page=50"

            # 发送请求
            with urllib.request.urlopen(url, timeout=30) as response:
                data = json.loads(response.read().decode('utf-8'))

            versions = []
            min_parts = tuple(map(int, min_version.split('.')))

            for release in data:
                # 跳过预发布版本
                if release.get('prerelease', True):
                    continue

                tag_name = release.get('tag_name', '')
                if not tag_name.startswith('v'):
                    continue

                version = tag_name[1:]  # 移除 'v' 前缀
                version_parts = tuple(map(int, version.split('.')[:2]))  # 只比较主版本和次版本

                # 检查版本是否满足最小要求
                if version_parts < min_parts:
                    continue

                # 获取下载信息
                download_info = self._get_download_info(release.get('assets', []))
                if not download_info:
                    continue

                versions.append(PythonVersion(
                    version=version,
                    release_date=release.get('published_at', ''),
                    download_url=download_info['url'],
                    checksum=download_info.get('checksum', ''),
                    is_stable=not release.get('prerelease', True)
                ))

            return versions[:20]  # 限制返回数量

        except Exception as e:
            logger.error(f"Failed to fetch release data: {e}")
            raise

    def _get_download_info(self, assets: List[Dict]) -> Optional[Dict]:
        """
        根据当前平台获取下载信息

        Args:
            assets: GitHub API 返回的资源列表

        Returns:
            下载信息字典
        """
        os_info = self.os_detector.get_os_info()
        architecture = os_info.architecture

        # 根据平台确定文件模式
        file_patterns = []

        if os_info.os_type == OperatingSystem.WINDOWS:
            if architecture == Architecture.X64:
                file_patterns = [
                    "python-*-amd64.exe",
                    "python-*-embed-amd64.zip"
                ]
            elif architecture == Architecture.ARM64:
                file_patterns = [
                    "python-*-arm64.exe",
                    "python-*-embed-arm64.zip"
                ]
            elif architecture == Architecture.X86:
                file_patterns = [
                    "python*-32.exe",
                    "python*-embed-win32.zip"
                ]

        elif os_info.os_type == OperatingSystem.MACOS:
            if architecture == Architecture.X64:
                file_patterns = ["python-*-macosx10.9.pkg"]
            elif architecture == Architecture.ARM64:
                file_patterns = ["python-*-macos11.pkg"]

        elif os_info.os_type == OperatingSystem.LINUX:
            if architecture == Architecture.X64:
                file_patterns = ["Python-*.tgz"]
            elif architecture == Architecture.ARM64:
                file_patterns = ["Python-*.tgz"]
            elif architecture == Architecture.X86:
                file_patterns = ["Python-*.tgz"]

        # 查找匹配的资源
        for asset in assets:
            asset_name = asset.get('name', '')
            for pattern in file_patterns:
                # 更精确的模式匹配
                if self._pattern_match(pattern, asset_name):
                    return {
                        'url': asset.get('browser_download_url', ''),
                        'name': asset_name,
                        'size': asset.get('size', 0),
                        'checksum': ''  # GitHub 不提供校验和
                    }

        return None

    def _pattern_match(self, pattern: str, filename: str) -> bool:
        """
        简单的通配符模式匹配

        Args:
            pattern: 模式字符串，如 "python-*-amd64.exe"
            filename: 文件名，如 "python-3.11.0-amd64.exe"

        Returns:
            是否匹配
        """
        if '*' not in pattern:
            return pattern == filename

        parts = pattern.split('*')
        if len(parts) != 2:
            # 多个通配符或复杂模式，简化处理
            return pattern.replace('*', '') in filename

        prefix, suffix = parts
        return filename.startswith(prefix) and filename.endswith(suffix)

    def install(self, min_version: Optional[str] = None,
                install_virtual_env: bool = True) -> bool:
        """
        安装 Python

        Args:
            min_version: 最小版本要求
            install_virtual_env: 是否创建虚拟环境

        Returns:
            安装是否成功
        """
        try:
            logger.info(f"Starting Python installation (min_version: {min_version or self.min_version})")

            # 检查是否已安装符合要求的 Python
            if self._check_existing_python(min_version):
                logger.info("Python already installed with required version")
                self.progress = PythonInstallationProgress(
                    status=PythonInstallationStatus.COMPLETED,
                    progress_percentage=100.0,
                    current_step="Python already available"
                )
                return True

            # 获取可用版本
            versions = self.get_available_versions(min_version)
            if not versions:
                raise Exception("No suitable Python versions found")

            # 选择最新稳定版本
            selected_version = versions[0]
            logger.info(f"Selected Python version: {selected_version}")

            # 创建临时目录
            self.temp_dir = tempfile.mkdtemp(prefix='python_install_')
            logger.info(f"Created temporary directory: {self.temp_dir}")

            # 下载 Python
            self.progress = PythonInstallationProgress(
                status=PythonInstallationStatus.DOWNLOADING,
                progress_percentage=10.0,
                current_step="Downloading Python installer"
            )

            installer_path = self._download_python(selected_version)

            # 安装 Python
            self.progress = PythonInstallationProgress(
                status=PythonInstallationStatus.INSTALLING,
                progress_percentage=50.0,
                current_step="Installing Python"
            )

            success = self._install_python(installer_path, selected_version)

            if success:
                # 验证安装
                self.progress = PythonInstallationProgress(
                    status=PythonInstallationStatus.VERIFYING,
                    progress_percentage=90.0,
                    current_step="Verifying installation"
                )

                if self._verify_installation(selected_version.version):
                    # 创建虚拟环境（如果需要）
                    if install_virtual_env:
                        self.progress = PythonInstallationProgress(
                            status=PythonInstallationStatus.VERIFYING,
                            progress_percentage=95.0,
                            current_step="Creating virtual environment"
                        )
                        self._create_virtual_environment(selected_version.version)

                    self.progress = PythonInstallationProgress(
                        status=PythonInstallationStatus.COMPLETED,
                        progress_percentage=100.0,
                        current_step="Installation completed successfully"
                    )

                    logger.info("Python installation completed successfully")
                    return True
                else:
                    raise Exception("Python installation verification failed")
            else:
                raise Exception("Python installation failed")

        except Exception as e:
            logger.error(f"Python installation failed: {e}")
            self.progress = PythonInstallationProgress(
                status=PythonInstallationStatus.FAILED,
                progress_percentage=self.progress.progress_percentage,
                current_step=self.progress.current_step,
                error_message=str(e)
            )
            return False

        finally:
            self._cleanup()

    def _check_existing_python(self, min_version: Optional[str]) -> bool:
        """
        检查是否已安装符合要求的 Python

        Args:
            min_version: 最小版本要求

        Returns:
            是否存在符合要求的 Python
        """
        try:
            min_version = min_version or self.min_version

            # 检查 Python 命令
            python_commands = ['python3', 'python', 'py']

            for cmd in python_commands:
                try:
                    result = subprocess.run([cmd, '--version'],
                                          capture_output=True, text=True, timeout=10)
                    if result.returncode == 0:
                        version_str = result.stderr or result.stdout
                        version = self._parse_version_string(version_str)
                        if version and self._compare_versions(version, min_version) >= 0:
                            logger.info(f"Found existing Python {version} using '{cmd}'")
                            return True
                except (subprocess.TimeoutExpired, FileNotFoundError):
                    continue

            return False

        except Exception as e:
            logger.warning(f"Error checking existing Python: {e}")
            return False

    def _parse_version_string(self, version_str: str) -> Optional[str]:
        """
        解析版本字符串

        Args:
            version_str: 版本字符串

        Returns:
            格式化的版本号
        """
        try:
            # 匹配版本号模式，如 "Python 3.9.7"
            match = re.search(r'Python (\d+\.\d+(?:\.\d+)?)', version_str)
            if match:
                return match.group(1)
            return None
        except Exception:
            return None

    def _compare_versions(self, version1: str, version2: str) -> int:
        """
        比较版本号

        Args:
            version1: 版本1
            version2: 版本2

        Returns:
            -1: version1 < version2
            0: version1 == version2
            1: version1 > version2
        """
        def version_key(v):
            return tuple(map(int, (v.split('.'))))

        v1_key = version_key(version1)
        v2_key = version_key(version2)

        if v1_key < v2_key:
            return -1
        elif v1_key > v2_key:
            return 1
        else:
            return 0

    def _download_python(self, version: PythonVersion) -> str:
        """
        下载 Python 安装包

        Args:
            version: Python 版本信息

        Returns:
            下载的文件路径
        """
        try:
            if not self.temp_dir:
                raise Exception("Temporary directory not created")

            # 解析文件名
            file_name = version.download_url.split('/')[-1]
            if not file_name:
                raise Exception("Unable to parse file name from download URL")

            file_path = os.path.join(self.temp_dir, file_name)

            logger.info(f"Downloading Python from: {version.download_url}")

            # 下载文件
            def progress_callback(downloaded: int, total: Optional[int]):
                if total:
                    percentage = (downloaded / total) * 100
                    self.progress.downloaded_bytes = downloaded
                    self.progress.download_size = total
                    self.progress.progress_percentage = 10.0 + (percentage * 0.3)  # 10-40%

            self._download_file(version.download_url, file_path, progress_callback)

            # 验证下载
            if not os.path.exists(file_path):
                raise Exception("Downloaded file not found")

            file_size = os.path.getsize(file_path)
            logger.info(f"Downloaded Python installer: {file_name} ({file_size} bytes)")

            return file_path

        except Exception as e:
            logger.error(f"Failed to download Python: {e}")
            raise

    def _download_file(self, url: str, file_path: str,
                      progress_callback: Optional[callable] = None) -> None:
        """
        下载文件并显示进度

        Args:
            url: 下载 URL
            file_path: 保存路径
            progress_callback: 进度回调函数
        """
        try:
            with urllib.request.urlopen(url, timeout=30) as response:
                total_size = int(response.headers.get('Content-Length', 0))
                downloaded = 0

                with open(file_path, 'wb') as f:
                    while True:
                        chunk = response.read(8192)
                        if not chunk:
                            break

                        f.write(chunk)
                        downloaded += len(chunk)

                        if progress_callback and total_size > 0:
                            progress_callback(downloaded, total_size)

        except Exception as e:
            logger.error(f"Failed to download file {url}: {e}")
            raise

    def _install_python(self, installer_path: str, version: PythonVersion) -> bool:
        """
        安装 Python

        Args:
            installer_path: 安装包路径
            version: Python 版本信息

        Returns:
            安装是否成功
        """
        try:
            os_info = self.os_detector.get_os_info()

            if os_info.os_type == OperatingSystem.WINDOWS:
                return self._install_on_windows(installer_path, version)
            elif os_info.os_type == OperatingSystem.MACOS:
                return self._install_on_macos(installer_path, version)
            elif os_info.os_type == OperatingSystem.LINUX:
                return self._install_on_linux(installer_path, version)
            else:
                raise Exception(f"Unsupported operating system: {os_info.os_type}")

        except Exception as e:
            logger.error(f"Failed to install Python: {e}")
            return False

    def _install_on_windows(self, installer_path: str, version: PythonVersion) -> bool:
        """
        在 Windows 上安装 Python

        Args:
            installer_path: 安装包路径
            version: Python 版本信息

        Returns:
            安装是否成功
        """
        try:
            if installer_path.endswith('.exe'):
                # 使用 MSI 安装器参数
                cmd = [
                    installer_path,
                    '/quiet',
                    'InstallAllUsers=0',
                    'PrependPath=1',
                    'Include_test=0',
                    'TargetDir=C:\\Python' + version.version.replace('.', '')
                ]

                logger.info(f"Running Windows installer: {' '.join(cmd)}")

                result = subprocess.run(cmd, timeout=600, capture_output=True, text=True)

                if result.returncode == 0:
                    logger.info("Windows Python installation completed successfully")

                    # 更新环境变量
                    self._update_windows_path(version.version)

                    return True
                else:
                    logger.error(f"Windows installer failed: {result.stderr}")
                    return False
            elif installer_path.endswith('.zip'):
                # 嵌入式版本 - 解压并配置
                return self._install_embedded_windows(installer_path, version)
            else:
                raise Exception("Unsupported installer format for Windows")

        except Exception as e:
            logger.error(f"Failed to install Python on Windows: {e}")
            return False

    def _install_embedded_windows(self, zip_path: str, version: PythonVersion) -> bool:
        """
        安装 Windows 嵌入式版本

        Args:
            zip_path: ZIP 文件路径
            version: Python 版本信息

        Returns:
            安装是否成功
        """
        try:
            # 创建安装目录
            install_dir = f"C:\\Python{version.version.replace('.', '')}"
            os.makedirs(install_dir, exist_ok=True)

            # 解压文件
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(install_dir)

            # 创建 python.bat 包装器
            wrapper_path = os.path.join(install_dir, 'python.bat')
            with open(wrapper_path, 'w') as f:
                f.write(f'@echo off\n"{install_dir}\\python.exe" %*\n')

            # 添加到 PATH
            self._add_to_windows_path(install_dir)

            logger.info(f"Embedded Python installed to: {install_dir}")
            return True

        except Exception as e:
            logger.error(f"Failed to install embedded Python: {e}")
            return False

    def _install_on_macos(self, installer_path: str, version: PythonVersion) -> bool:
        """
        在 macOS 上安装 Python

        Args:
            installer_path: 安装包路径
            version: Python 版本信息

        Returns:
            安装是否成功
        """
        try:
            if installer_path.endswith('.pkg'):
                # 使用 installer 命令
                cmd = ['sudo', 'installer', '-pkg', installer_path, '-target', '/']

                logger.info(f"Running macOS installer: {' '.join(cmd)}")

                # 在交互式环境中，这可能需要用户输入密码
                result = subprocess.run(cmd, timeout=600, capture_output=True, text=True)

                if result.returncode == 0:
                    logger.info("macOS Python installation completed successfully")
                    return True
                else:
                    logger.error(f"macOS installer failed: {result.stderr}")

                    # 尝试使用 Homebrew
                    return self._install_with_homebrew(version)
            else:
                raise Exception("Unsupported installer format for macOS")

        except Exception as e:
            logger.error(f"Failed to install Python on macOS: {e}")
            # 回退到 Homebrew
            return self._install_with_homebrew(version)

    def _install_with_homebrew(self, version: PythonVersion) -> bool:
        """
        使用 Homebrew 安装 Python

        Args:
            version: Python 版本信息

        Returns:
            安装是否成功
        """
        try:
            # 检查 Homebrew 是否可用
            brew_check = subprocess.run(['which', 'brew'], capture_output=True)
            if brew_check.returncode != 0:
                logger.error("Homebrew not available")
                return False

            # 安装指定版本的 Python
            major_minor = '.'.join(version.version.split('.')[:2])
            cmd = ['brew', 'install', f'python@{major_minor}']

            logger.info(f"Installing Python with Homebrew: {' '.join(cmd)}")

            result = subprocess.run(cmd, timeout=600, capture_output=True, text=True)

            if result.returncode == 0:
                logger.info("Homebrew Python installation completed successfully")
                return True
            else:
                logger.error(f"Homebrew installation failed: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"Failed to install Python with Homebrew: {e}")
            return False

    def _install_on_linux(self, installer_path: str, version: PythonVersion) -> bool:
        """
        在 Linux 上安装 Python

        Args:
            installer_path: 安装包路径
            version: Python 版本信息

        Returns:
            安装是否成功
        """
        try:
            if installer_path.endswith('.tgz') or installer_path.endswith('.tar.gz'):
                return self._install_from_source(installer_path, version)
            else:
                # 尝试使用包管理器
                return self._install_with_package_manager(version)

        except Exception as e:
            logger.error(f"Failed to install Python on Linux: {e}")
            return False

    def _install_from_source(self, source_path: str, version: PythonVersion) -> bool:
        """
        从源代码编译安装 Python

        Args:
            source_path: 源代码压缩包路径
            version: Python 版本信息

        Returns:
            安装是否成功
        """
        try:
            # 解压源代码
            extract_dir = os.path.join(self.temp_dir, 'python_source')
            os.makedirs(extract_dir, exist_ok=True)

            with tarfile.open(source_path, 'r:*') as tar_ref:
                tar_ref.extractall(extract_dir)

            # 查找解压后的目录
            python_dir = None
            for item in os.listdir(extract_dir):
                item_path = os.path.join(extract_dir, item)
                if os.path.isdir(item_path) and item.startswith('Python-'):
                    python_dir = item_path
                    break

            if not python_dir:
                raise Exception("Python source directory not found")

            # 安装构建依赖
            self._install_build_dependencies()

            # 配置、编译和安装
            commands = [
                ['./configure', '--prefix=/usr/local', '--enable-optimizations'],
                ['make', '-j4'],  # 使用4个并行编译
                ['sudo', 'make', 'altinstall']  # altinstall 避免覆盖系统 Python
            ]

            for cmd in commands:
                logger.info(f"Running: {' '.join(cmd)}")
                result = subprocess.run(cmd, cwd=python_dir, timeout=1800,
                                      capture_output=True, text=True)
                if result.returncode != 0:
                    logger.error(f"Command failed: {' '.join(cmd)}")
                    logger.error(f"Error: {result.stderr}")
                    return False

            logger.info("Python installation from source completed successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to install Python from source: {e}")
            return False

    def _install_with_package_manager(self, version: PythonVersion) -> bool:
        """
        使用包管理器安装 Python

        Args:
            version: Python 版本信息

        Returns:
            安装是否成功
        """
        try:
            # 检测发行版
            distro = self._detect_linux_distro()

            major_minor = '.'.join(version.version.split('.')[:2])

            if distro == 'ubuntu' or distro == 'debian':
                cmd = ['sudo', 'apt-get', 'update']
                subprocess.run(cmd, timeout=300)

                cmd = ['sudo', 'apt-get', 'install', '-y', f'python{major_minor}']
            elif distro == 'centos' or distro == 'rhel' or distro == 'fedora':
                cmd = ['sudo', 'yum', 'install', '-y', f'python{major_minor}']
            elif distro == 'arch':
                cmd = ['sudo', 'pacman', '-S', '--noconfirm', f'python{major_minor}']
            else:
                logger.error(f"Unsupported Linux distribution: {distro}")
                return False

            logger.info(f"Installing Python with package manager: {' '.join(cmd)}")

            result = subprocess.run(cmd, timeout=600, capture_output=True, text=True)

            if result.returncode == 0:
                logger.info("Package manager Python installation completed successfully")
                return True
            else:
                logger.error(f"Package manager installation failed: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"Failed to install Python with package manager: {e}")
            return False

    def _detect_linux_distro(self) -> str:
        """
        检测 Linux 发行版

        Returns:
            发行版名称
        """
        try:
            # 尝试从 /etc/os-release 读取
            if os.path.exists('/etc/os-release'):
                with open('/etc/os-release', 'r') as f:
                    content = f.read()
                    if 'ubuntu' in content.lower():
                        return 'ubuntu'
                    elif 'debian' in content.lower():
                        return 'debian'
                    elif 'centos' in content.lower():
                        return 'centos'
                    elif 'rhel' in content.lower():
                        return 'rhel'
                    elif 'fedora' in content.lower():
                        return 'fedora'
                    elif 'arch' in content.lower():
                        return 'arch'

            # 回退到检查发行版特定文件
            distro_files = {
                '/etc/lsb-release': 'ubuntu',
                '/etc/debian_version': 'debian',
                '/etc/centos-release': 'centos',
                '/etc/redhat-release': 'rhel',
                '/etc/fedora-release': 'fedora',
                '/etc/arch-release': 'arch'
            }

            for file_path, distro in distro_files.items():
                if os.path.exists(file_path):
                    return distro

            return 'unknown'

        except Exception as e:
            logger.warning(f"Failed to detect Linux distribution: {e}")
            return 'unknown'

    def _install_build_dependencies(self) -> None:
        """
        安装构建依赖
        """
        try:
            distro = self._detect_linux_distro()

            if distro == 'ubuntu' or distro == 'debian':
                cmd = [
                    'sudo', 'apt-get', 'install', '-y',
                    'build-essential', 'libssl-dev', 'libffi-dev',
                    'zlib1g-dev', 'libncurses5-dev', 'libgdbm-dev',
                    'libnss3-dev', 'libreadline-dev', 'libsqlite3-dev'
                ]
            elif distro == 'centos' or distro == 'rhel' or distro == 'fedora':
                cmd = [
                    'sudo', 'yum', 'groupinstall', '-y', 'Development Tools',
                    '&&', 'sudo', 'yum', 'install', '-y',
                    'openssl-devel', 'libffi-devel', 'zlib-devel',
                    'ncurses-devel', 'gdbm-devel', 'nss-devel',
                    'readline-devel', 'sqlite-devel'
                ]
            else:
                logger.warning(f"Skipping build dependencies for unknown distribution: {distro}")
                return

            logger.info(f"Installing build dependencies: {' '.join(cmd)}")

            result = subprocess.run(cmd, timeout=600, capture_output=True, text=True)
            if result.returncode != 0:
                logger.warning(f"Failed to install some build dependencies: {result.stderr}")

        except Exception as e:
            logger.warning(f"Failed to install build dependencies: {e}")

    def _verify_installation(self, version: str) -> bool:
        """
        验证 Python 安装

        Args:
            version: 期望的 Python 版本

        Returns:
            验证是否成功
        """
        try:
            logger.info(f"Verifying Python {version} installation")

            # 检查 Python 命令
            python_commands = ['python3', 'python']

            for cmd in python_commands:
                try:
                    # 检查版本
                    version_result = subprocess.run([cmd, '--version'],
                                                  capture_output=True, text=True, timeout=10)
                    if version_result.returncode == 0:
                        installed_version = self._parse_version_string(
                            version_result.stderr or version_result.stdout
                        )
                        if installed_version and installed_version.startswith(version):
                            # 检查基本功能
                            test_result = subprocess.run([cmd, '-c', 'print("Hello, World!")'],
                                                       capture_output=True, text=True, timeout=10)
                            if test_result.returncode == 0 and "Hello, World!" in test_result.stdout:
                                logger.info(f"Python {version} verification successful with '{cmd}'")
                                return True
                except (subprocess.TimeoutExpired, FileNotFoundError):
                    continue

            logger.error("Python verification failed - no working installation found")
            return False

        except Exception as e:
            logger.error(f"Failed to verify Python installation: {e}")
            return False

    def _create_virtual_environment(self, python_version: str) -> bool:
        """
        创建 Python 虚拟环境

        Args:
            python_version: Python 版本

        Returns:
            创建是否成功
        """
        try:
            logger.info(f"Creating virtual environment for Python {python_version}")

            # 查找 Python 可执行文件
            python_exe = self._find_python_executable(python_version)
            if not python_exe:
                raise Exception("Python executable not found")

            # 创建虚拟环境目录
            venv_dir = os.path.expanduser("~/python_venv")
            os.makedirs(os.path.dirname(venv_dir), exist_ok=True)

            # 创建虚拟环境
            cmd = [python_exe, '-m', 'venv', venv_dir]
            result = subprocess.run(cmd, timeout=300, capture_output=True, text=True)

            if result.returncode == 0:
                logger.info(f"Virtual environment created at: {venv_dir}")

                # 激活脚本路径
                if platform.system() == 'Windows':
                    activate_script = os.path.join(venv_dir, 'Scripts', 'activate.bat')
                else:
                    activate_script = os.path.join(venv_dir, 'bin', 'activate')

                logger.info(f"Virtual environment activation script: {activate_script}")
                return True
            else:
                logger.error(f"Failed to create virtual environment: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"Failed to create virtual environment: {e}")
            return False

    def _find_python_executable(self, version: str) -> Optional[str]:
        """
        查找指定版本的 Python 可执行文件

        Args:
            version: Python 版本

        Returns:
            Python 可执行文件路径
        """
        try:
            python_commands = [f'python{version}', f'python3.{version.split(".")[1]}', 'python3', 'python']

            for cmd in python_commands:
                try:
                    # 查找命令路径
                    which_cmd = 'where' if platform.system() == 'Windows' else 'which'
                    result = subprocess.run([which_cmd, cmd], capture_output=True, text=True, timeout=10)
                    if result.returncode == 0:
                        exe_path = result.stdout.strip().split('\n')[0]
                        if os.path.exists(exe_path):
                            # 验证版本
                            version_result = subprocess.run([exe_path, '--version'],
                                                          capture_output=True, text=True, timeout=10)
                            if version_result.returncode == 0:
                                installed_version = self._parse_version_string(
                                    version_result.stderr or version_result.stdout
                                )
                                if installed_version and installed_version.startswith(version):
                                    logger.info(f"Found Python {version} at: {exe_path}")
                                    return exe_path
                except (subprocess.TimeoutExpired, FileNotFoundError):
                    continue

            return None

        except Exception as e:
            logger.error(f"Failed to find Python executable: {e}")
            return None

    def _update_windows_path(self, version: str) -> None:
        """
        更新 Windows PATH 环境变量

        Args:
            version: Python 版本
        """
        try:
            import winreg

            # Python 安装路径
            python_path = f"C:\\Python{version.replace('.', '')}"
            scripts_path = os.path.join(python_path, 'Scripts')

            # 添加到用户 PATH
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_SET_VALUE)
            try:
                path_value, _ = winreg.QueryValueEx(key, "PATH")
                path_entries = [p.strip() for p in path_value.split(';') if p.strip()]

                # 只添加不在PATH中的路径
                for new_path in [python_path, scripts_path]:
                    if new_path not in path_entries:
                        path_entries.append(new_path)

                new_path = ';'.join(path_entries)
                winreg.SetValueEx(key, "PATH", 0, winreg.REG_EXPAND_SZ, new_path)

                # 通知系统环境变量更改
                import ctypes
                ctypes.windll.user32.SendMessageTimeoutW(0xFFFF, 0x001A, 0, "Environment", 0x0002, 5000, None)

                logger.info("Updated Windows PATH environment variable")

            except FileNotFoundError:
                # PATH 不存在，创建新的
                new_path = f"{python_path};{scripts_path}"
                winreg.SetValueEx(key, "PATH", 0, winreg.REG_EXPAND_SZ, new_path)
                logger.info("Created Windows PATH environment variable")

            finally:
                winreg.CloseKey(key)

        except Exception as e:
            logger.warning(f"Failed to update Windows PATH: {e}")

    def _add_to_windows_path(self, directory: str) -> None:
        """
        添加目录到 Windows PATH

        Args:
            directory: 要添加的目录路径
        """
        try:
            import winreg

            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_SET_VALUE)
            try:
                path_value, _ = winreg.QueryValueEx(key, "PATH")
                path_entries = [p.strip() for p in path_value.split(';') if p.strip()]

                if directory not in path_entries:
                    path_entries.append(directory)
                    new_path = ';'.join(path_entries)
                    winreg.SetValueEx(key, "PATH", 0, winreg.REG_EXPAND_SZ, new_path)
                    logger.info(f"Added {directory} to Windows PATH")
                else:
                    logger.info(f"{directory} already exists in Windows PATH")
            except FileNotFoundError:
                winreg.SetValueEx(key, "PATH", 0, winreg.REG_EXPAND_SZ, directory)
                logger.info(f"Created Windows PATH with {directory}")

            finally:
                winreg.CloseKey(key)

        except Exception as e:
            logger.warning(f"Failed to add directory to Windows PATH: {e}")

    def _cleanup(self) -> None:
        """清理临时文件"""
        try:
            if self.temp_dir and os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir, ignore_errors=True)
                logger.info(f"Cleaned up temporary directory: {self.temp_dir}")
        except Exception as e:
            logger.warning(f"Failed to cleanup temporary directory: {e}")

    def get_progress(self) -> PythonInstallationProgress:
        """
        获取当前安装进度

        Returns:
            安装进度对象
        """
        return self.progress

    def cancel_installation(self) -> None:
        """取消安装"""
        logger.info("Cancelling Python installation")
        self.progress.status = PythonInstallationStatus.CANCELLED
        self._cleanup()

    def get_supported_versions(self) -> List[str]:
        """
        获取支持的 Python 版本列表

        Returns:
            支持的版本列表
        """
        return [
            "3.12", "3.11", "3.10", "3.9", "3.8"
        ]

    def is_version_supported(self, version: str) -> bool:
        """
        检查版本是否支持

        Args:
            version: Python 版本

        Returns:
            是否支持该版本
        """
        supported = self.get_supported_versions()
        major_minor = '.'.join(version.split('.')[:2])
        return major_minor in supported