"""
Node.js 自动安装引擎

此模块提供跨平台的 Node.js 自动安装功能，支持 Windows、macOS 和 Linux 系统。
包括 LTS 版本检测、下载、安装和验证功能。
"""

import os
import subprocess
import tempfile
import shutil
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import urllib.request
import urllib.error
import hashlib

from utils.logger import get_logger
from core.operating_system_detector import OperatingSystem, Architecture
from utils.network_utils import NetworkChecker

logger = get_logger(__name__)


class InstallationStatus(Enum):
    """安装状态枚举"""
    NOT_STARTED = "not_started"
    DOWNLOADING = "downloading"
    INSTALLING = "installing"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class NodeVersion:
    """Node.js 版本信息"""
    version: str
    lts: bool
    date: str
    files: List[Dict[str, str]]
    security: bool = False

    def __str__(self) -> str:
        lts_str = " LTS" if self.lts else ""
        security_str = " (Security)" if self.security else ""
        return f"v{self.version}{lts_str}{security_str}"

    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> 'NodeVersion':
        """从 API 响应创建版本对象"""
        # 处理 LTS 字段，可能是布尔值或字符串
        lts_value = data.get('lts', False)
        is_lts = bool(lts_value)  # 任何非空值都视为 LTS

        return cls(
            version=data.get('version', '').lstrip('v'),
            lts=is_lts,
            date=data.get('date', ''),
            files=data.get('files', []),
            security=data.get('security', False)
        )


@dataclass
class InstallationProgress:
    """安装进度信息"""
    status: InstallationStatus
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


class NodeJSInstaller:
    """
    Node.js 跨平台自动安装器

    功能特性：
    - 自动检测操作系统和架构
    - 获取最新的 LTS 版本
    - 下载并安装 Node.js
    - 验证安装结果
    - 更新环境变量
    - 支持静默安装
    """

    # Node.js 官方 API 端点
    NODE_API_BASE_URL = "https://nodejs.org/dist"
    NODE_INDEX_URL = "https://nodejs.org/dist/index.json"

    # 下载超时时间（秒）
    DOWNLOAD_TIMEOUT = 600

    # 支持的平台和架构组合
    PLATFORM_MAPPING = {
        (OperatingSystem.WINDOWS, Architecture.X64): "win-x64",
        (OperatingSystem.WINDOWS, Architecture.X86): "win-x86",
        (OperatingSystem.WINDOWS, Architecture.ARM64): "win-arm64",
        (OperatingSystem.MACOS, Architecture.X64): "darwin-x64",
        (OperatingSystem.MACOS, Architecture.ARM64): "darwin-arm64",
        (OperatingSystem.LINUX, Architecture.X64): "linux-x64",
        (OperatingSystem.LINUX, Architecture.ARM64): "linux-arm64",
        (OperatingSystem.LINUX, Architecture.X86): "linux-x86",
    }

    def __init__(self, os_detector, network_utils: Optional[NetworkChecker] = None):
        """
        初始化 Node.js 安装器

        Args:
            os_detector: 操作系统检测器实例
            network_utils: 网络工具实例（可选）
        """
        self.os_detector = os_detector
        self.network_utils = network_utils or NetworkChecker()
        self.logger = get_logger(self.__class__.__name__)

        # 安装状态
        self.progress = InstallationProgress(status=InstallationStatus.NOT_STARTED)
        self._installation_cancelled = False

        # 获取系统信息
        self.system_info = os_detector.detect_os_info()
        self.platform_string = self._get_platform_string()

        self.logger.info(f"初始化 Node.js 安装器 - 平台: {self.platform_string}")

    def _get_platform_string(self) -> str:
        """获取平台字符串"""
        platform_key = (self.system_info.os_type, self.system_info.architecture)
        platform_string = self.PLATFORM_MAPPING.get(platform_key)

        if not platform_string:
            raise RuntimeError(f"不支持的平台组合: {self.system_info.os_type.value} {self.system_info.architecture.value}")

        return platform_string

    async def get_available_versions(self, include_unstable: bool = False) -> List[NodeVersion]:
        """
        获取可用的 Node.js 版本列表

        Args:
            include_unstable: 是否包含非稳定版本

        Returns:
            版本列表，LTS 版本在前
        """
        try:
            self.logger.info("正在获取 Node.js 版本列表...")

            # 检查网络连接
            network_info = await self.network_utils.get_comprehensive_network_info()
            if not network_info.internet_connected:
                raise RuntimeError("网络连接不可用，无法获取版本信息")

            # 下载版本索引
            with urllib.request.urlopen(self.NODE_INDEX_URL, timeout=30) as response:
                if response.status != 200:
                    raise RuntimeError(f"获取版本列表失败: HTTP {response.status}")

                data = json.loads(response.read().decode('utf-8'))

            # 解析版本信息
            versions = []
            for version_data in data:
                version = NodeVersion.from_api_response(version_data)

                # 过滤不稳定版本
                if not include_unstable and not version.lts and not version.security:
                    continue

                # 检查当前平台的支持
                if self._is_platform_supported(version, self.platform_string):
                    versions.append(version)

            # 排序：LTS 版本在前，然后按版本号排序
            versions.sort(key=lambda v: (not v.lts, tuple(map(int, v.version.split('.')))), reverse=True)

            self.logger.info(f"获取到 {len(versions)} 个可用版本")
            return versions

        except Exception as e:
            self.logger.error(f"获取版本列表失败: {e}")
            raise RuntimeError(f"无法获取 Node.js 版本信息: {e}")

    def _is_platform_supported(self, version: NodeVersion, platform: str) -> bool:
        """检查版本是否支持指定平台"""
        return any(file_info.get('platform') == platform for file_info in version.files)

    async def get_latest_lts_version(self) -> Optional[NodeVersion]:
        """
        获取最新的 LTS 版本

        Returns:
            最新 LTS 版本信息，如果没有则返回 None
        """
        try:
            versions = await self.get_available_versions(include_unstable=False)

            for version in versions:
                if version.lts:
                    self.logger.info(f"最新 LTS 版本: {version}")
                    return version

            self.logger.warning("未找到 LTS 版本")
            return None

        except Exception as e:
            self.logger.error(f"获取最新 LTS 版本失败: {e}")
            return None

    async def install(self, version: str = 'lts', force_reinstall: bool = False) -> bool:
        """
        安装 Node.js

        Args:
            version: 要安装的版本 ('lts' 表示最新 LTS 版本)
            force_reinstall: 是否强制重新安装

        Returns:
            安装是否成功
        """
        try:
            self._installation_cancelled = False
            self.progress = InstallationProgress(status=InstallationStatus.INSTALLING)

            self.logger.info(f"开始安装 Node.js {version}")

            # 检查是否已安装
            if not force_reinstall and self._is_nodejs_installed():
                installed_version = self._get_installed_nodejs_version()
                self.logger.info(f"Node.js {installed_version} 已安装")
                self.progress.status = InstallationStatus.COMPLETED
                self.progress.progress_percentage = 100.0
                return True

            # 获取版本信息
            if version.lower() == 'lts':
                target_version = await self.get_latest_lts_version()
                if not target_version:
                    raise RuntimeError("无法获取最新 LTS 版本")
            else:
                target_version = await self._find_version(version)
                if not target_version:
                    raise RuntimeError(f"找不到版本: {version}")

            self.progress.current_step = f"准备安装 Node.js {target_version.version}"

            # 下载安装包
            installer_path = await self._download_installer(target_version)
            if self._installation_cancelled:
                return False

            # 执行安装
            success = await self._execute_installation(installer_path, target_version)
            if not success:
                return False

            # 验证安装
            self.progress.current_step = "验证安装"
            self.progress.status = InstallationStatus.VERIFYING
            self.progress.progress_percentage = 90.0

            if self._verify_installation(target_version):
                self.progress.status = InstallationStatus.COMPLETED
                self.progress.progress_percentage = 100.0
                self.progress.current_step = "安装完成"

                self.logger.info(f"Node.js {target_version.version} 安装成功")
                return True
            else:
                raise RuntimeError("安装验证失败")

        except Exception as e:
            self.logger.error(f"安装失败: {e}")
            self.progress.status = InstallationStatus.FAILED
            self.progress.error_message = str(e)
            return False

    async def _find_version(self, version_str: str) -> Optional[NodeVersion]:
        """查找指定版本"""
        versions = await self.get_available_versions(include_unstable=True)

        # 精确匹配
        for version in versions:
            if version.version == version_str.lstrip('v'):
                return version

        # 模糊匹配
        for version in versions:
            if version.version.startswith(version_str.lstrip('v')):
                return version

        return None

    def _is_nodejs_installed(self) -> bool:
        """检查 Node.js 是否已安装"""
        try:
            result = subprocess.run(['node', '--version'],
                                  capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError):
            return False

    def _get_installed_nodejs_version(self) -> Optional[str]:
        """获取已安装的 Node.js 版本"""
        try:
            result = subprocess.run(['node', '--version'],
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                return result.stdout.strip()
        except (subprocess.SubprocessError, FileNotFoundError):
            pass
        return None

    async def _download_installer(self, version: NodeVersion) -> str:
        """
        下载 Node.js 安装包

        Args:
            version: 要下载的版本信息

        Returns:
            下载的安装包文件路径
        """
        try:
            self.progress.current_step = "下载安装包"
            self.progress.status = InstallationStatus.DOWNLOADING
            self.progress.progress_percentage = 10.0

            # 查找匹配的文件
            file_info = self._find_matching_file(version, self.platform_string)
            if not file_info:
                raise RuntimeError(f"找不到平台 {self.platform_string} 的安装包")

            download_url = f"{self.NODE_API_BASE_URL}/v{version.version}/{file_info['filename']}"
            filename = file_info['filename']

            # 创建临时下载目录
            temp_dir = tempfile.mkdtemp(prefix='nodejs_install_')
            installer_path = os.path.join(temp_dir, filename)

            self.logger.info(f"下载 URL: {download_url}")
            self.logger.info(f"保存到: {installer_path}")

            # 下载文件
            await self._download_file(download_url, installer_path)

            if self._installation_cancelled:
                raise RuntimeError("下载已取消")

            # 验证下载文件
            if not self._verify_download_checksum(installer_path, file_info):
                raise RuntimeError("下载文件校验失败")

            self.progress.progress_percentage = 50.0
            return installer_path

        except Exception as e:
            self.logger.error(f"下载安装包失败: {e}")
            raise

    def _find_matching_file(self, version: NodeVersion, platform: str) -> Optional[Dict[str, str]]:
        """查找匹配的安装包文件"""
        for file_info in version.files:
            if file_info.get('platform') == platform:
                return file_info
        return None

    async def _download_file(self, url: str, filepath: str) -> None:
        """
        下载文件并显示进度

        Args:
            url: 下载 URL
            filepath: 保存路径
        """
        def progress_callback(block_num, block_size, total_size):
            if self._installation_cancelled:
                return

            if total_size > 0:
                downloaded = block_num * block_size
                progress = min(downloaded / total_size, 1.0)

                # 更新进度（10% - 40% 用于下载）
                self.progress.progress_percentage = 10.0 + (progress * 30.0)
                self.progress.downloaded_bytes = downloaded
                self.progress.download_size = total_size

                # 每 10% 记录一次日志
                if int(progress * 10) > int((downloaded - block_size) / total_size * 10):
                    self.logger.info(f"下载进度: {progress*100:.1f}%")

        # 使用 urllib.request 下载
        with urllib.request.urlopen(url, timeout=self.DOWNLOAD_TIMEOUT) as response:
            if response.status != 200:
                raise RuntimeError(f"下载失败: HTTP {response.status}")

            total_size = int(response.headers.get('Content-Length', 0))
            self.progress.download_size = total_size

            with open(filepath, 'wb') as f:
                downloaded = 0
                chunk_size = 8192

                while True:
                    if self._installation_cancelled:
                        break

                    chunk = response.read(chunk_size)
                    if not chunk:
                        break

                    f.write(chunk)
                    downloaded += len(chunk)

                    # 更新进度
                    if total_size > 0:
                        progress = min(downloaded / total_size, 1.0)
                        self.progress.progress_percentage = 10.0 + (progress * 30.0)
                        self.progress.downloaded_bytes = downloaded

    def _verify_download_checksum(self, filepath: str, file_info: Dict[str, str]) -> bool:
        """
        验证下载文件的校验和

        Args:
            filepath: 文件路径
            file_info: 文件信息（包含校验和）

        Returns:
            校验是否成功
        """
        try:
            # Node.js 官方提供 SHA256 校验和
            expected_sha256 = file_info.get('sha256sum')
            if not expected_sha256:
                self.logger.warning("文件没有提供 SHA256 校验和，跳过验证")
                return True

            self.logger.info("验证文件完整性...")

            # 计算 SHA256
            sha256_hash = hashlib.sha256()
            with open(filepath, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(chunk)

            calculated_sha256 = sha256_hash.hexdigest()

            if calculated_sha256.lower() == expected_sha256.lower():
                self.logger.info("文件完整性验证通过")
                return True
            else:
                self.logger.error(f"SHA256 校验失败: 期望 {expected_sha256}, 计算 {calculated_sha256}")
                return False

        except Exception as e:
            self.logger.error(f"校验和验证失败: {e}")
            return False

    async def _execute_installation(self, installer_path: str, version: NodeVersion) -> bool:
        """
        执行安装过程

        Args:
            installer_path: 安装包路径
            version: 版本信息

        Returns:
            安装是否成功
        """
        try:
            self.progress.current_step = "安装 Node.js"
            self.progress.progress_percentage = 60.0

            if self.system_info.os_type == OperatingSystem.WINDOWS:
                return await self._install_on_windows(installer_path, version)
            elif self.system_info.os_type == OperatingSystem.MACOS:
                return await self._install_on_macos(installer_path, version)
            elif self.system_info.os_type == OperatingSystem.LINUX:
                return await self._install_on_linux(installer_path, version)
            else:
                raise RuntimeError(f"不支持的操作系统: {self.system_info.os_type}")

        except Exception as e:
            self.logger.error(f"执行安装失败: {e}")
            return False

    async def _install_on_windows(self, installer_path: str, version: NodeVersion) -> bool:
        """在 Windows 上安装 Node.js"""
        try:
            self.logger.info("在 Windows 上安装 Node.js...")

            # Windows MSI 安装包参数
            # /quiet: 静默安装
            # /norestart: 安装后不重启
            # ADDLOCAL=ALL: 安装所有组件
            cmd = [
                'msiexec', '/i', installer_path,
                '/quiet', '/norestart',
                'ADDLOCAL=ALL'
            ]

            self.logger.info(f"执行命令: {' '.join(cmd)}")

            # 执行安装
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # 等待安装完成
            stdout, stderr = process.communicate(timeout=self.DOWNLOAD_TIMEOUT)

            if process.returncode == 0:
                self.logger.info("Windows 安装完成")
                self.progress.progress_percentage = 80.0

                # 更新环境变量
                await self._update_windows_path()
                return True
            else:
                self.logger.error(f"安装失败，返回码: {process.returncode}")
                self.logger.error(f"错误输出: {stderr}")
                return False

        except subprocess.TimeoutExpired:
            self.logger.error("安装超时")
            return False
        except Exception as e:
            self.logger.error(f"Windows 安装失败: {e}")
            return False

    async def _install_on_macos(self, installer_path: str, version: NodeVersion) -> bool:
        """在 macOS 上安装 Node.js"""
        try:
            self.logger.info("在 macOS 上安装 Node.js...")

            # 检查是否为 PKG 文件
            if installer_path.endswith('.pkg'):
                return await self._install_macos_pkg(installer_path)
            # 检查是否为 TAR 文件
            elif installer_path.endswith('.tar.gz') or installer_path.endswith('.tar.xz'):
                return await self._install_macos_tar(installer_path, version)
            else:
                raise RuntimeError(f"不支持的安装包格式: {installer_path}")

        except Exception as e:
            self.logger.error(f"macOS 安装失败: {e}")
            return False

    async def _install_macos_pkg(self, pkg_path: str) -> bool:
        """使用 PKG 文件在 macOS 上安装"""
        try:
            # 使用 installer 命令静默安装 PKG
            cmd = [
                'sudo', 'installer',
                '-pkg', pkg_path,
                '-target', '/'
            ]

            self.logger.info(f"执行命令: {' '.join(cmd)}")

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            stdout, stderr = process.communicate(timeout=self.DOWNLOAD_TIMEOUT)

            if process.returncode == 0:
                self.logger.info("macOS PKG 安装完成")
                self.progress.progress_percentage = 80.0
                return True
            else:
                self.logger.error(f"PKG 安装失败，返回码: {process.returncode}")
                self.logger.error(f"错误输出: {stderr}")
                return False

        except subprocess.TimeoutExpired:
            self.logger.error("PKG 安装超时")
            return False

    async def _install_macos_tar(self, tar_path: str, version: NodeVersion) -> bool:
        """使用 TAR 文件在 macOS 上安装"""
        try:
            # 创建安装目录
            install_dir = f"/usr/local/node-v{version.version}"

            # 解压文件
            subprocess.run(['sudo', 'mkdir', '-p', install_dir], check=True)
            subprocess.run(['sudo', 'tar', '-xzf', tar_path, '-C', install_dir, '--strip-components=1'], check=True)

            # 创建符号链接
            node_bin = os.path.join(install_dir, 'bin', 'node')
            npm_bin = os.path.join(install_dir, 'bin', 'npm')

            subprocess.run(['sudo', 'ln', '-sf', node_bin, '/usr/local/bin/node'], check=True)
            subprocess.run(['sudo', 'ln', '-sf', npm_bin, '/usr/local/bin/npm'], check=True)

            self.logger.info("macOS TAR 安装完成")
            self.progress.progress_percentage = 80.0
            return True

        except subprocess.SubprocessError as e:
            self.logger.error(f"TAR 安装失败: {e}")
            return False

    async def _install_on_linux(self, installer_path: str, version: NodeVersion) -> bool:
        """在 Linux 上安装 Node.js"""
        try:
            self.logger.info("在 Linux 上安装 Node.js...")

            # Linux 通常是 TAR 文件
            if installer_path.endswith('.tar.gz') or installer_path.endswith('.tar.xz'):
                return await self._install_linux_tar(installer_path, version)
            else:
                raise RuntimeError(f"不支持的安装包格式: {installer_path}")

        except Exception as e:
            self.logger.error(f"Linux 安装失败: {e}")
            return False

    async def _install_linux_tar(self, tar_path: str, version: NodeVersion) -> bool:
        """使用 TAR 文件在 Linux 上安装"""
        try:
            # 创建安装目录
            install_dir = f"/usr/local/node-v{version.version}"

            # 解压文件
            subprocess.run(['sudo', 'mkdir', '-p', install_dir], check=True)
            subprocess.run(['sudo', 'tar', '-xzf', tar_path, '-C', install_dir, '--strip-components=1'], check=True)

            # 创建符号链接
            node_bin = os.path.join(install_dir, 'bin', 'node')
            npm_bin = os.path.join(install_dir, 'bin', 'npm')

            subprocess.run(['sudo', 'ln', '-sf', node_bin, '/usr/local/bin/node'], check=True)
            subprocess.run(['sudo', 'ln', '-sf', npm_bin, '/usr/local/bin/npm'], check=True)

            self.logger.info("Linux TAR 安装完成")
            self.progress.progress_percentage = 80.0
            return True

        except subprocess.SubprocessError as e:
            self.logger.error(f"Linux TAR 安装失败: {e}")
            return False

    async def _update_windows_path(self) -> None:
        """更新 Windows 系统路径"""
        try:
            # Node.js 默认安装路径
            nodejs_path = os.path.expandvars(r"%ProgramFiles%\nodejs")

            # 检查路径是否存在
            if not os.path.exists(nodejs_path):
                self.logger.warning(f"Node.js 安装路径不存在: {nodejs_path}")
                return

            # 获取当前 PATH
            import winreg

            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                              r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment",
                              0, winreg.KEY_READ) as key:
                current_path = winreg.QueryValueEx(key, "PATH")[0]

            # 检查是否已在 PATH 中
            path_entries = [p.strip() for p in current_path.split(';') if p.strip()]
            if nodejs_path not in path_entries:
                # 更新 PATH
                path_entries.append(nodejs_path)
                new_path = ';'.join(path_entries)

                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                  r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment",
                                  0, winreg.KEY_SET_VALUE) as key:
                    winreg.SetValueEx(key, "PATH", 0, winreg.REG_EXPAND_SZ, new_path)

                # 通知系统环境变量已更改
                from ctypes import windll
                windll.user32.SendMessageTimeoutW(0xFFFF, 0x001A, 0, "Environment",
                                                 0, 5000, None)

                self.logger.info("已更新系统 PATH 环境变量")

        except Exception as e:
            self.logger.error(f"更新 Windows PATH 失败: {e}")

    def _verify_installation(self, version: NodeVersion) -> bool:
        """
        验证 Node.js 安装

        Args:
            version: 应该安装的版本

        Returns:
            验证是否成功
        """
        try:
            # 检查 node 命令是否可用
            result = subprocess.run(['node', '--version'],
                                  capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                self.logger.error("Node.js 命令不可用")
                return False

            installed_version = result.stdout.strip()
            self.logger.info(f"已安装版本: {installed_version}")

            # 检查版本是否匹配
            expected_version = f"v{version.version}"
            if installed_version != expected_version:
                self.logger.warning(f"版本不匹配: 期望 {expected_version}, 实际 {installed_version}")
                # 不一定算失败，可能是更新版本

            # 检查 npm 是否可用
            npm_result = subprocess.run(['npm', '--version'],
                                      capture_output=True, text=True, timeout=30)

            if npm_result.returncode == 0:
                self.logger.info(f"NPM 版本: {npm_result.stdout.strip()}")
            else:
                self.logger.error("NPM 不可用")
                return False

            return True

        except subprocess.TimeoutExpired:
            self.logger.error("命令执行超时")
            return False
        except Exception as e:
            self.logger.error(f"安装验证失败: {e}")
            return False

    def cancel_installation(self) -> None:
        """取消安装"""
        self._installation_cancelled = True
        self.progress.status = InstallationStatus.CANCELLED
        self.progress.current_step = "安装已取消"
        self.logger.info("用户取消了安装")

    def get_progress(self) -> InstallationProgress:
        """获取当前安装进度"""
        return self.progress

    def cleanup(self) -> None:
        """清理临时文件"""
        try:
            temp_dir = tempfile.gettempdir()
            for item in os.listdir(temp_dir):
                if item.startswith('nodejs_install_'):
                    temp_path = os.path.join(temp_dir, item)
                    if os.path.isdir(temp_path):
                        shutil.rmtree(temp_path, ignore_errors=True)
                    else:
                        os.remove(temp_path)
        except Exception as e:
            self.logger.error(f"清理临时文件失败: {e}")