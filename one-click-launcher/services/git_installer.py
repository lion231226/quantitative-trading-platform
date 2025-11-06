"""
Git 自动安装和配置引擎

此模块提供跨平台的 Git 自动安装功能，支持 Windows、macOS 和 Linux 系统。
包括 Git 安装、基本配置、SSH密钥生成和验证功能。
"""

import os
import subprocess
import tempfile
import shutil
from typing import Dict, Optional, Any
from dataclasses import dataclass
from enum import Enum
import urllib.request
import urllib.error

from utils.logger import get_logger
from core.operating_system_detector import OperatingSystem
from utils.network_utils import NetworkChecker

logger = get_logger(__name__)


class GitInstallationStatus(Enum):
    """Git安装状态枚举"""
    NOT_STARTED = "not_started"
    DOWNLOADING = "downloading"
    INSTALLING = "installing"
    CONFIGURING = "configuring"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class GitConfiguration:
    """Git 配置信息"""
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    default_editor: Optional[str] = None
    default_branch: str = "main"
    auto_crlf: Optional[str] = None  # true, false, input
    ssh_key_type: str = "ed25519"
    ssh_key_path: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'user_name': self.user_name,
            'user_email': self.user_email,
            'default_editor': self.default_editor,
            'default_branch': self.default_branch,
            'auto_crlf': self.auto_crlf,
            'ssh_key_type': self.ssh_key_type,
            'ssh_key_path': self.ssh_key_path
        }


@dataclass
class GitInstallationProgress:
    """Git安装进度信息"""
    status: GitInstallationStatus
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


class GitInstaller:
    """
    Git 跨平台自动安装器和配置器

    功能特性：
    - 自动检测操作系统和架构
    - 跨平台下载和安装 Git
    - Git 基本配置（用户名、邮箱、编辑器等）
    - SSH 密钥生成和配置
    - 安装进度跟踪
    - 错误处理和回滚
    - 安装验证
    """

    def __init__(self, os_detector, network_checker: NetworkChecker):
        """
        初始化 Git 安装器

        Args:
            os_detector: 操作系统检测器
            network_checker: 网络检查器
        """
        self.os_detector = os_detector
        self.network_checker = network_checker
        self.temp_dir = None
        self.progress = GitInstallationProgress(
            status=GitInstallationStatus.NOT_STARTED
        )
        self.configuration = GitConfiguration()

        # Git 官方下载配置
        self.git_official_url = "https://git-scm.com/download/"
        self.git_windows_base = "https://github.com/git-for-windows/git/releases/download/"
        self.git_macos_base = "https://sourceforge.net/projects/git-osx-installer/files/"

        logger.info(f"GitInstaller initialized for {os_detector.get_os_info()}")

    def install_and_configure(self, config: Optional[GitConfiguration] = None) -> bool:
        """
        安装和配置 Git

        Args:
            config: Git 配置信息，如果为 None 则使用默认配置

        Returns:
            安装和配置是否成功
        """
        try:
            logger.info("Starting Git installation and configuration")

            # 设置配置
            if config:
                self.configuration = config
            else:
                self._auto_configure()

            # 检查是否已安装 Git
            if self._check_existing_git():
                logger.info("Git already installed, proceeding with configuration")
                self.progress = GitInstallationProgress(
                    status=GitInstallationStatus.CONFIGURING,
                    progress_percentage=60.0,
                    current_step="Configuring existing Git installation"
                )
            else:
                # 创建临时目录
                self.temp_dir = tempfile.mkdtemp(prefix='git_install_')
                logger.info(f"Created temporary directory: {self.temp_dir}")

                # 下载 Git
                self.progress = GitInstallationProgress(
                    status=GitInstallationStatus.DOWNLOADING,
                    progress_percentage=10.0,
                    current_step="Downloading Git installer"
                )

                installer_path = self._download_git()

                # 安装 Git
                self.progress = GitInstallationProgress(
                    status=GitInstallationStatus.INSTALLING,
                    progress_percentage=40.0,
                    current_step="Installing Git"
                )

                install_success = self._install_git(installer_path)
                if not install_success:
                    raise Exception("Git installation failed")

            # 配置 Git
            configure_success = self._configure_git()
            if not configure_success:
                raise Exception("Git configuration failed")

            # 生成 SSH 密钥（如果需要）
            if self._should_generate_ssh_key():
                self.progress = GitInstallationProgress(
                    status=GitInstallationStatus.CONFIGURING,
                    progress_percentage=80.0,
                    current_step="Generating SSH key"
                )

                ssh_success = self._generate_ssh_key()
                if not ssh_success:
                    logger.warning("SSH key generation failed, but Git installation completed")

            # 验证安装
            self.progress = GitInstallationProgress(
                status=GitInstallationStatus.VERIFYING,
                progress_percentage=90.0,
                current_step="Verifying Git installation"
            )

            if self._verify_installation():
                self.progress = GitInstallationProgress(
                    status=GitInstallationStatus.COMPLETED,
                    progress_percentage=100.0,
                    current_step="Git installation and configuration completed successfully"
                )

                logger.info("Git installation and configuration completed successfully")
                return True
            else:
                raise Exception("Git installation verification failed")

        except Exception as e:
            logger.error(f"Git installation and configuration failed: {e}")
            self.progress = GitInstallationProgress(
                status=GitInstallationStatus.FAILED,
                progress_percentage=self.progress.progress_percentage,
                current_step=self.progress.current_step,
                error_message=str(e)
            )
            return False

        finally:
            self._cleanup()

    def _auto_configure(self):
        """自动配置 Git 基本设置"""
        # 设置默认分支名称
        self.configuration.default_branch = "main"

        # 根据平台设置 line ending
        os_info = self.os_detector.get_os_info()
        if os_info.os_type == OperatingSystem.WINDOWS:
            self.configuration.auto_crlf = "true"
        else:
            self.configuration.auto_crlf = "input"

        # 设置默认编辑器
        if os_info.os_type == OperatingSystem.WINDOWS:
            self.configuration.default_editor = "notepad"
        elif os_info.os_type == OperatingSystem.MACOS:
            self.configuration.default_editor = "nano"
        else:
            self.configuration.default_editor = "nano"

        logger.info(f"Auto-configured Git with default settings for {os_info.os_type.value}")

    def _check_existing_git(self) -> bool:
        """
        检查是否已安装 Git

        Returns:
            是否存在可用的 Git 安装
        """
        try:
            # 检查 Git 命令
            git_commands = ['git']

            for cmd in git_commands:
                try:
                    result = subprocess.run([cmd, '--version'],
                                          capture_output=True, text=True, timeout=10)
                    if result.returncode == 0:
                        version_str = result.stdout
                        logger.info(f"Found existing Git: {version_str.strip()}")
                        return True
                except (subprocess.TimeoutExpired, FileNotFoundError):
                    continue

            return False

        except Exception as e:
            logger.warning(f"Error checking existing Git: {e}")
            return False

    def _download_git(self) -> str:
        """
        下载 Git 安装包

        Returns:
            下载的文件路径
        """
        try:
            if not self.temp_dir:
                raise Exception("Temporary directory not created")

            # 检查网络连接
            if not self.network_checker.check_connectivity():
                raise Exception("No internet connection available")

            download_url = self._get_download_url()
            file_name = download_url.split('/')[-1]
            if not file_name:
                raise Exception("Unable to parse file name from download URL")

            file_path = os.path.join(self.temp_dir, file_name)

            logger.info(f"Downloading Git from: {download_url}")

            # 下载文件
            def progress_callback(downloaded: int, total: Optional[int]):
                if total:
                    percentage = (downloaded / total) * 100
                    self.progress.downloaded_bytes = downloaded
                    self.progress.download_size = total
                    self.progress.progress_percentage = 10.0 + (percentage * 0.3)  # 10-40%

            self._download_file(download_url, file_path, progress_callback)

            # 验证下载
            if not os.path.exists(file_path):
                raise Exception("Downloaded file not found")

            file_size = os.path.getsize(file_path)
            logger.info(f"Downloaded Git installer: {file_name} ({file_size} bytes)")

            return file_path

        except Exception as e:
            logger.error(f"Failed to download Git: {e}")
            raise

    def _get_download_url(self) -> str:
        """
        获取适合当前平台的 Git 下载 URL

        Returns:
            Git 下载 URL
        """
        os_info = self.os_detector.get_os_info()

        if os_info.os_type == OperatingSystem.WINDOWS:
            # Windows Git for Windows
            return f"{self.git_windows_base}v2.43.0.windows.1/Git-2.43.0-64-bit.exe"

        elif os_info.os_type == OperatingSystem.MACOS:
            # macOS Git installer
            return "https://sourceforge.net/projects/git-osx-installer/files/git-2.39.3-intel-universal-mavericks.dmg/download"

        elif os_info.os_type == OperatingSystem.LINUX:
            # Linux - 通常通过包管理器安装，但提供源码下载链接
            return "https://github.com/git/git/archive/refs/tags/v2.43.0.tar.gz"

        else:
            raise Exception(f"Unsupported operating system: {os_info.os_type}")

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

    def _install_git(self, installer_path: str) -> bool:
        """
        安装 Git

        Args:
            installer_path: 安装包路径

        Returns:
            安装是否成功
        """
        try:
            os_info = self.os_detector.get_os_info()

            if os_info.os_type == OperatingSystem.WINDOWS:
                return self._install_on_windows(installer_path)
            elif os_info.os_type == OperatingSystem.MACOS:
                return self._install_on_macos(installer_path)
            elif os_info.os_type == OperatingSystem.LINUX:
                return self._install_on_linux(installer_path)
            else:
                raise Exception(f"Unsupported operating system: {os_info.os_type}")

        except Exception as e:
            logger.error(f"Failed to install Git: {e}")
            return False

    def _install_on_windows(self, installer_path: str) -> bool:
        """
        在 Windows 上安装 Git

        Args:
            installer_path: 安装包路径

        Returns:
            安装是否成功
        """
        try:
            # 使用静默安装参数
            cmd = [
                installer_path,
                '/VERYSILENT',
                '/NORESTART',
                '/NOCANCEL',
                '/SP-',
                '/SUPPRESSMSGBOXES'
            ]

            logger.info(f"Running Windows Git installer: {' '.join(cmd)}")

            result = subprocess.run(cmd, timeout=600, capture_output=True, text=True)

            if result.returncode == 0:
                logger.info("Windows Git installation completed successfully")
                return True
            else:
                logger.error(f"Windows Git installer failed: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"Failed to install Git on Windows: {e}")
            return False

    def _install_on_macos(self, installer_path: str) -> bool:
        """
        在 macOS 上安装 Git

        Args:
            installer_path: 安装包路径

        Returns:
            安装是否成功
        """
        try:
            if installer_path.endswith('.dmg'):
                # 挂载 DMG 文件
                mount_cmd = ['hdiutil', 'attach', installer_path]
                result = subprocess.run(mount_cmd, timeout=120, capture_output=True, text=True)

                if result.returncode != 0:
                    logger.error(f"Failed to mount DMG: {result.stderr}")
                    # 尝试使用 Homebrew
                    return self._install_with_homebrew()

                # 查找挂载点
                mount_point = None
                if result.stdout:
                    lines = result.stdout.split('\n')
                    for line in lines:
                        if '/Volumes/' in line:
                            mount_point = line.split()[-1]
                            break

                if not mount_point:
                    return self._install_with_homebrew()

                # 运行 PKG 安装器
                pkg_files = []
                for root, dirs, files in os.walk(mount_point):
                    for file in files:
                        if file.endswith('.pkg'):
                            pkg_files.append(os.path.join(root, file))

                if not pkg_files:
                    return self._install_with_homebrew()

                pkg_path = pkg_files[0]
                install_cmd = ['sudo', 'installer', '-pkg', pkg_path, '-target', '/']

                logger.info(f"Running macOS Git installer: {' '.join(install_cmd)}")

                result = subprocess.run(install_cmd, timeout=300, capture_output=True, text=True)

                # 卸载 DMG
                subprocess.run(['hdiutil', 'detach', mount_point], capture_output=True)

                if result.returncode == 0:
                    logger.info("macOS Git installation completed successfully")
                    return True
                else:
                    logger.error(f"macOS Git installer failed: {result.stderr}")
                    return self._install_with_homebrew()
            else:
                return self._install_with_homebrew()

        except Exception as e:
            logger.error(f"Failed to install Git on macOS: {e}")
            # 回退到 Homebrew
            return self._install_with_homebrew()

    def _install_with_homebrew(self) -> bool:
        """
        使用 Homebrew 安装 Git

        Returns:
            安装是否成功
        """
        try:
            # 检查 Homebrew 是否可用
            brew_check = subprocess.run(['which', 'brew'], capture_output=True)
            if brew_check.returncode != 0:
                logger.error("Homebrew not available")
                return False

            # 安装 Git
            cmd = ['brew', 'install', 'git']

            logger.info(f"Installing Git with Homebrew: {' '.join(cmd)}")

            result = subprocess.run(cmd, timeout=600, capture_output=True, text=True)

            if result.returncode == 0:
                logger.info("Homebrew Git installation completed successfully")
                return True
            else:
                logger.error(f"Homebrew Git installation failed: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"Failed to install Git with Homebrew: {e}")
            return False

    def _install_on_linux(self, installer_path: str) -> bool:
        """
        在 Linux 上安装 Git

        Args:
            installer_path: 安装包路径

        Returns:
            安装是否成功
        """
        try:
            # 优先使用包管理器安装
            return self._install_with_package_manager()

        except Exception as e:
            logger.error(f"Failed to install Git on Linux: {e}")
            return False

    def _install_with_package_manager(self) -> bool:
        """
        使用包管理器安装 Git

        Returns:
            安装是否成功
        """
        try:
            # 检测发行版
            distro = self._detect_linux_distro()

            if distro == 'ubuntu' or distro == 'debian':
                cmd = ['sudo', 'apt-get', 'update']
                subprocess.run(cmd, timeout=300)

                cmd = ['sudo', 'apt-get', 'install', '-y', 'git']
            elif distro == 'centos' or distro == 'rhel' or distro == 'fedora':
                cmd = ['sudo', 'yum', 'install', '-y', 'git']
            elif distro == 'arch':
                cmd = ['sudo', 'pacman', '-S', '--noconfirm', 'git']
            else:
                logger.error(f"Unsupported Linux distribution: {distro}")
                return False

            logger.info(f"Installing Git with package manager: {' '.join(cmd)}")

            result = subprocess.run(cmd, timeout=300, capture_output=True, text=True)

            if result.returncode == 0:
                logger.info("Package manager Git installation completed successfully")
                return True
            else:
                logger.error(f"Package manager Git installation failed: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"Failed to install Git with package manager: {e}")
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

    def _configure_git(self) -> bool:
        """
        配置 Git 设置

        Returns:
            配置是否成功
        """
        try:
            logger.info("Configuring Git settings")

            # 配置用户名（如果提供）
            if self.configuration.user_name:
                cmd = ['git', 'config', '--global', 'user.name', self.configuration.user_name]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                if result.returncode != 0:
                    logger.error(f"Failed to set user name: {result.stderr}")
                    return False

            # 配置用户邮箱（如果提供）
            if self.configuration.user_email:
                cmd = ['git', 'config', '--global', 'user.email', self.configuration.user_email]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                if result.returncode != 0:
                    logger.error(f"Failed to set user email: {result.stderr}")
                    return False

            # 配置默认分支
            cmd = ['git', 'config', '--global', 'init.defaultBranch', self.configuration.default_branch]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                logger.warning(f"Failed to set default branch: {result.stderr}")

            # 配置 line ending
            if self.configuration.auto_crlf:
                cmd = ['git', 'config', '--global', 'core.autocrlf', self.configuration.auto_crlf]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                if result.returncode != 0:
                    logger.warning(f"Failed to set autocrlf: {result.stderr}")

            # 配置默认编辑器
            if self.configuration.default_editor:
                cmd = ['git', 'config', '--global', 'core.editor', self.configuration.default_editor]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                if result.returncode != 0:
                    logger.warning(f"Failed to set default editor: {result.stderr}")

            logger.info("Git configuration completed successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to configure Git: {e}")
            return False

    def _should_generate_ssh_key(self) -> bool:
        """
        检查是否应该生成 SSH 密钥

        Returns:
            是否应该生成 SSH 密钥
        """
        try:
            # 检查是否已存在 SSH 密钥
            ssh_dir = os.path.expanduser("~/.ssh")
            if not os.path.exists(ssh_dir):
                return True

            # 检查常见的密钥文件
            key_types = ['id_ed25519', 'id_rsa', 'id_ecdsa']
            for key_type in key_types:
                key_path = os.path.join(ssh_dir, key_type)
                if os.path.exists(key_path):
                    logger.info(f"SSH key already exists: {key_path}")
                    return False

            return True

        except Exception as e:
            logger.warning(f"Error checking SSH keys: {e}")
            return False

    def _generate_ssh_key(self) -> bool:
        """
        生成 SSH 密钥

        Returns:
            生成是否成功
        """
        try:
            logger.info(f"Generating SSH key ({self.configuration.ssh_key_type})")

            # 创建 SSH 目录
            ssh_dir = os.path.expanduser("~/.ssh")
            os.makedirs(ssh_dir, exist_ok=True)

            # 设置权限
            os.chmod(ssh_dir, 0o700)

            # 生成密钥
            key_path = os.path.join(ssh_dir, f"id_{self.configuration.ssh_key_type}")
            cmd = ['ssh-keygen', '-t', self.configuration.ssh_key_type, '-f', key_path, '-N', '']

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

            if result.returncode == 0:
                # 添加到 ssh-agent
                try:
                    agent_cmd = ['ssh-add', key_path]
                    subprocess.run(agent_cmd, capture_output=True, timeout=30)
                except Exception:
                    logger.warning("Failed to add SSH key to ssh-agent")

                self.configuration.ssh_key_path = key_path
                logger.info(f"SSH key generated successfully: {key_path}")
                return True
            else:
                logger.error(f"SSH key generation failed: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"Failed to generate SSH key: {e}")
            return False

    def _verify_installation(self) -> bool:
        """
        验证 Git 安装

        Returns:
            验证是否成功
        """
        try:
            logger.info("Verifying Git installation")

            # 检查 Git 命令
            result = subprocess.run(['git', '--version'],
                                  capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                logger.error("Git command not found")
                return False

            version_str = result.stdout.strip()
            logger.info(f"Git version: {version_str}")

            # 检查基本功能
            temp_repo = tempfile.mkdtemp(prefix='git_test_')
            try:
                # 测试 git init
                result = subprocess.run(['git', 'init'], cwd=temp_repo,
                                      capture_output=True, text=True, timeout=30)
                if result.returncode != 0:
                    logger.error("Git init failed")
                    return False

                # 测试 git config
                result = subprocess.run(['git', 'config', '--list'], cwd=temp_repo,
                                      capture_output=True, text=True, timeout=30)
                if result.returncode != 0:
                    logger.error("Git config failed")
                    return False

                logger.info("Git installation verification successful")
                return True

            finally:
                shutil.rmtree(temp_repo, ignore_errors=True)

        except Exception as e:
            logger.error(f"Failed to verify Git installation: {e}")
            return False

    def _cleanup(self) -> None:
        """清理临时文件"""
        try:
            if self.temp_dir and os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir, ignore_errors=True)
                logger.info(f"Cleaned up temporary directory: {self.temp_dir}")
        except Exception as e:
            logger.warning(f"Failed to cleanup temporary directory: {e}")

    def get_progress(self) -> GitInstallationProgress:
        """
        获取当前安装进度

        Returns:
            安装进度对象
        """
        return self.progress

    def cancel_installation(self) -> None:
        """取消安装"""
        logger.info("Cancelling Git installation")
        self.progress.status = GitInstallationStatus.CANCELLED
        self._cleanup()

    def get_configuration(self) -> GitConfiguration:
        """
        获取当前 Git 配置

        Returns:
            Git 配置对象
        """
        return self.configuration

    def get_ssh_public_key(self) -> Optional[str]:
        """
        获取 SSH 公钥内容

        Returns:
            SSH 公钥内容，如果不存在则返回 None
        """
        try:
            if not self.configuration.ssh_key_path:
                return None

            public_key_path = self.configuration.ssh_key_path + '.pub'
            if not os.path.exists(public_key_path):
                return None

            with open(public_key_path, 'r') as f:
                return f.read().strip()

        except Exception as e:
            logger.error(f"Failed to read SSH public key: {e}")
            return None

    def test_git_connection(self, repo_url: str = "https://github.com") -> bool:
        """
        测试 Git 连接

        Args:
            repo_url: 测试用的仓库 URL

        Returns:
            连接测试是否成功
        """
        try:
            cmd = ['git', 'ls-remote', repo_url]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            return result.returncode == 0

        except Exception as e:
            logger.error(f"Git connection test failed: {e}")
            return False

    def is_git_configured(self) -> bool:
        """
        检查 Git 是否已配置用户信息

        Returns:
            是否已配置
        """
        try:
            # 检查用户名
            result = subprocess.run(['git', 'config', '--global', 'user.name'],
                                  capture_output=True, text=True, timeout=10)
            if not result.stdout.strip():
                return False

            # 检查邮箱
            result = subprocess.run(['git', 'config', '--global', 'user.email'],
                                  capture_output=True, text=True, timeout=10)
            if not result.stdout.strip():
                return False

            return True

        except Exception as e:
            logger.error(f"Error checking Git configuration: {e}")
            return False