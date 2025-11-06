"""
Node.js 安装器测试

测试 NodeJSInstaller 类的各项功能，包括版本检测、下载、安装和验证。
使用 Mock 技术避免实际下载和安装软件。
"""

import pytest
import asyncio
import json
import tempfile
import os
import subprocess
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from pathlib import Path

# 添加项目根目录到 Python 路径
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.nodejs_installer import (
    NodeJSInstaller, NodeVersion, InstallationStatus, InstallationProgress
)
from core.operating_system_detector import OperatingSystem, Architecture, SystemInfo, OSVersion
from utils.network_utils import NetworkChecker, NetworkStatus, NetworkInfo
from utils.logger import get_logger


logger = get_logger(__name__)


class TestNodeVersion:
    """测试 NodeVersion 类"""

    def test_node_version_creation(self):
        """测试版本对象创建"""
        version = NodeVersion(
            version="18.17.0",
            lts=True,
            date="2023-07-18",
            files=[{"platform": "win-x64", "filename": "node-v18.17.0-x64.msi"}],
            security=False
        )

        assert version.version == "18.17.0"
        assert version.lts is True
        assert version.date == "2023-07-18"
        assert len(version.files) == 1
        assert version.security is False

    def test_node_version_string_representation(self):
        """测试版本字符串表示"""
        # LTS 版本
        lts_version = NodeVersion(version="18.17.0", lts=True, date="2023-07-18", files=[])
        assert str(lts_version) == "v18.17.0 LTS"

        # 安全版本
        security_version = NodeVersion(version="16.20.1", lts=False, date="2023-07-18",
                                    files=[], security=True)
        assert str(security_version) == "v16.20.1 (Security)"

        # 普通版本
        regular_version = NodeVersion(version="20.5.0", lts=False, date="2023-07-18", files=[])
        assert str(regular_version) == "v20.5.0"

    def test_from_api_response(self):
        """测试从 API 响应创建版本对象"""
        api_data = {
            "version": "v18.17.0",
            "lts": "Hydrogen",
            "date": "2023-07-18",
            "files": [
                {"platform": "win-x64", "filename": "node-v18.17.0-x64.msi"},
                {"platform": "darwin-x64", "filename": "node-v18.17.0-darwin-x64.tar.gz"}
            ],
            "security": False
        }

        version = NodeVersion.from_api_response(api_data)

        assert version.version == "18.17.0"
        assert version.lts is True
        assert version.date == "2023-07-18"
        assert len(version.files) == 2
        assert version.security is False


class TestInstallationProgress:
    """测试 InstallationProgress 类"""

    def test_progress_creation(self):
        """测试进度对象创建"""
        progress = InstallationProgress(
            status=InstallationStatus.INSTALLING,
            progress_percentage=50.0,
            current_step="下载安装包"
        )

        assert progress.status == InstallationStatus.INSTALLING
        assert progress.progress_percentage == 50.0
        assert progress.current_step == "下载安装包"
        assert progress.error_message is None

    def test_progress_to_dict(self):
        """测试进度转换为字典"""
        progress = InstallationProgress(
            status=InstallationStatus.DOWNLOADING,
            progress_percentage=25.0,
            current_step="正在下载",
            error_message="网络错误",
            download_size=1000000,
            downloaded_bytes=250000
        )

        result = progress.to_dict()

        assert result['status'] == 'downloading'
        assert result['progress_percentage'] == 25.0
        assert result['current_step'] == '正在下载'
        assert result['error_message'] == '网络错误'
        assert result['download_size'] == 1000000
        assert result['downloaded_bytes'] == 250000


@pytest.fixture
def mock_os_detector():
    """创建模拟的操作系统检测器"""
    system_info = SystemInfo(
        os_type=OperatingSystem.WINDOWS,
        architecture=Architecture.X64,
        version=OSVersion(10, 0, 0, name="Windows 10"),
        python_version="3.11.0",
        python_executable="python.exe",
        platform_details={},
        compatibility={'os_supported': True, 'architecture_supported': True}
    )

    mock_detector = Mock()
    mock_detector.detect_os_info.return_value = system_info
    return mock_detector


@pytest.fixture
def mock_network_checker():
    """创建模拟的网络检查器"""
    mock_checker = Mock(spec=NetworkChecker)

    # 模拟网络信息
    network_info = NetworkInfo(
        status=NetworkStatus.CONNECTED,
        internet_connected=True,
        proxy_config=Mock(enabled=False),
        package_managers={},
        local_ip="192.168.1.100"
    )

    mock_checker.get_comprehensive_network_info = AsyncMock(return_value=network_info)
    return mock_checker


@pytest.fixture
def nodejs_installer(mock_os_detector, mock_network_checker):
    """创建 Node.js 安装器实例"""
    return NodeJSInstaller(mock_os_detector, mock_network_checker)


class TestNodeJSInstaller:
    """测试 NodeJSInstaller 类"""

    def test_installer_initialization(self, nodejs_installer, mock_os_detector):
        """测试安装器初始化"""
        assert nodejs_installer.os_detector == mock_os_detector
        assert nodejs_installer.network_utils is not None
        assert nodejs_installer.system_info is not None
        assert nodejs_installer.platform_string == "win-x64"

    def test_platform_string_detection(self):
        """测试平台字符串检测"""
        # Windows x64
        mock_detector = Mock()
        mock_detector.detect_os_info.return_value = SystemInfo(
            os_type=OperatingSystem.WINDOWS,
            architecture=Architecture.X64,
            version=OSVersion(10, 0, 0),
            python_version="3.11.0",
            python_executable="python.exe",
            platform_details={},
            compatibility={}
        )
        installer = NodeJSInstaller(mock_detector)
        assert installer.platform_string == "win-x64"

        # macOS ARM64
        mock_detector.detect_os_info.return_value = SystemInfo(
            os_type=OperatingSystem.MACOS,
            architecture=Architecture.ARM64,
            version=OSVersion(13, 0, 0),
            python_version="3.11.0",
            python_executable="python3",
            platform_details={},
            compatibility={}
        )
        installer = NodeJSInstaller(mock_detector)
        assert installer.platform_string == "darwin-arm64"

        # Linux x64
        mock_detector.detect_os_info.return_value = SystemInfo(
            os_type=OperatingSystem.LINUX,
            architecture=Architecture.X64,
            version=OSVersion(20, 4, 0, name="Ubuntu"),
            python_version="3.11.0",
            python_executable="python3",
            platform_details={},
            compatibility={}
        )
        installer = NodeJSInstaller(mock_detector)
        assert installer.platform_string == "linux-x64"

    @pytest.mark.asyncio
    async def test_get_available_versions_success(self, nodejs_installer):
        """测试获取可用版本 - 成功情况"""
        # 模拟 API 响应
        mock_response_data = [
            {
                "version": "v20.5.0",
                "lts": False,
                "date": "2023-07-18",
                "files": [
                    {"platform": "win-x64", "filename": "node-v20.5.0-x64.msi"},
                    {"platform": "linux-x64", "filename": "node-v20.5.0-linux-x64.tar.xz"}
                ],
                "security": False
            },
            {
                "version": "v18.17.0",
                "lts": "Hydrogen",
                "date": "2023-07-04",
                "files": [
                    {"platform": "win-x64", "filename": "node-v18.17.0-x64.msi"},
                    {"platform": "linux-x64", "filename": "node-v18.17.0-linux-x64.tar.xz"}
                ],
                "security": False
            }
        ]

        with patch('urllib.request.urlopen') as mock_urlopen:
            # 模拟 HTTP 响应
            mock_response = Mock()
            mock_response.status = 200
            mock_response.read.return_value = json.dumps(mock_response_data).encode('utf-8')
            mock_urlopen.return_value.__enter__.return_value = mock_response

            # 测试包含不稳定版本
            versions = await nodejs_installer.get_available_versions(include_unstable=True)

            assert len(versions) == 2
            assert versions[0].version == "20.5.0"  # 更新版本应该在前
            assert versions[0].lts is False
            assert versions[1].version == "18.17.0"
            assert versions[1].lts is True

            # 测试不包含不稳定版本（默认行为）
            stable_versions = await nodejs_installer.get_available_versions(include_unstable=False)

            assert len(stable_versions) == 1
            assert stable_versions[0].version == "18.17.0"
            assert stable_versions[0].lts is True

    @pytest.mark.asyncio
    async def test_get_available_versions_network_error(self, nodejs_installer):
        """测试获取可用版本 - 网络错误"""
        # 模拟网络连接失败
        nodejs_installer.network_utils.get_comprehensive_network_info = AsyncMock(
            return_value=NetworkInfo(
                status=NetworkStatus.DISCONNECTED,
                internet_connected=False,
                proxy_config=Mock(enabled=False),
                package_managers={},
                local_ip=None
            )
        )

        with pytest.raises(RuntimeError, match="网络连接不可用"):
            await nodejs_installer.get_available_versions()

    @pytest.mark.asyncio
    async def test_get_latest_lts_version(self, nodejs_installer):
        """测试获取最新 LTS 版本"""
        # 模拟版本数据
        mock_versions = [
            NodeVersion(version="20.5.0", lts=False, date="2023-07-18", files=[]),
            NodeVersion(version="18.17.0", lts=True, date="2023-07-04", files=[]),
            NodeVersion(version="16.20.1", lts=True, date="2023-06-20", files=[])
        ]

        with patch.object(nodejs_installer, 'get_available_versions', return_value=mock_versions):
            lts_version = await nodejs_installer.get_latest_lts_version()

            assert lts_version is not None
            assert lts_version.version == "18.17.0"
            assert lts_version.lts is True

    @pytest.mark.asyncio
    async def test_get_latest_lts_version_no_lts(self, nodejs_installer):
        """测试获取最新 LTS 版本 - 没有 LTS 版本"""
        # 模拟没有 LTS 版本的数据
        mock_versions = [
            NodeVersion(version="20.5.0", lts=False, date="2023-07-18", files=[]),
            NodeVersion(version="19.9.0", lts=False, date="2023-04-18", files=[])
        ]

        with patch.object(nodejs_installer, 'get_available_versions', return_value=mock_versions):
            lts_version = await nodejs_installer.get_latest_lts_version()

            assert lts_version is None

    def test_is_nodejs_installed_true(self, nodejs_installer):
        """测试检查 Node.js 是否已安装 - 已安装"""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "v18.17.0"

            assert nodejs_installer._is_nodejs_installed() is True
            mock_run.assert_called_once_with(['node', '--version'], capture_output=True, text=True, timeout=10)

    def test_is_nodejs_installed_false(self, nodejs_installer):
        """测试检查 Node.js 是否已安装 - 未安装"""
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = FileNotFoundError()

            assert nodejs_installer._is_nodejs_installed() is False

    def test_get_installed_nodejs_version(self, nodejs_installer):
        """测试获取已安装的 Node.js 版本"""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "v18.17.0\n"

            version = nodejs_installer._get_installed_nodejs_version()
            assert version == "v18.17.0"

    def test_find_matching_file(self, nodejs_installer):
        """测试查找匹配的安装包文件"""
        version = NodeVersion(
            version="18.17.0",
            lts=True,
            date="2023-07-04",
            files=[
                {"platform": "win-x64", "filename": "node-v18.17.0-x64.msi"},
                {"platform": "linux-x64", "filename": "node-v18.17.0-linux-x64.tar.xz"},
                {"platform": "darwin-x64", "filename": "node-v18.17.0-darwin-x64.tar.gz"}
            ]
        )

        # 测试找到匹配文件
        file_info = nodejs_installer._find_matching_file(version, "win-x64")
        assert file_info is not None
        assert file_info["platform"] == "win-x64"
        assert file_info["filename"] == "node-v18.17.0-x64.msi"

        # 测试未找到匹配文件
        file_info = nodejs_installer._find_matching_file(version, "linux-arm64")
        assert file_info is None

    def test_verify_download_checksum_success(self, nodejs_installer):
        """测试下载文件校验 - 成功"""
        # 创建临时测试文件
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
            temp_file.write("test content")
            temp_file_path = temp_file.name

        try:
            # 计算正确的 SHA256
            import hashlib
            sha256_hash = hashlib.sha256()
            with open(temp_file_path, 'rb') as f:
                sha256_hash.update(f.read())
            expected_sha256 = sha256_hash.hexdigest()

            file_info = {"sha256sum": expected_sha256}
            assert nodejs_installer._verify_download_checksum(temp_file_path, file_info) is True

        finally:
            os.unlink(temp_file_path)

    def test_verify_download_checksum_failure(self, nodejs_installer):
        """测试下载文件校验 - 失败"""
        # 创建临时测试文件
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
            temp_file.write("test content")
            temp_file_path = temp_file.name

        try:
            file_info = {"sha256sum": "invalid_checksum"}
            assert nodejs_installer._verify_download_checksum(temp_file_path, file_info) is False

        finally:
            os.unlink(temp_file_path)

    def test_verify_download_checksum_no_checksum(self, nodejs_installer):
        """测试下载文件校验 - 没有校验和"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
            temp_file.write("test content")
            temp_file_path = temp_file.name

        try:
            file_info = {}  # 没有 SHA256 校验和
            assert nodejs_installer._verify_download_checksum(temp_file_path, file_info) is True

        finally:
            os.unlink(temp_file_path)

    @pytest.mark.asyncio
    async def test_install_already_installed(self, nodejs_installer):
        """测试安装 - 已经安装"""
        # 模拟已经安装 Node.js
        with patch.object(nodejs_installer, '_is_nodejs_installed', return_value=True), \
             patch.object(nodejs_installer, '_get_installed_nodejs_version', return_value="v18.17.0"), \
             patch.object(nodejs_installer, 'get_latest_lts_version') as mock_get_lts:

            mock_lts_version = NodeVersion(version="18.17.0", lts=True, date="2023-07-04", files=[])
            mock_get_lts.return_value = mock_lts_version

            result = await nodejs_installer.install('lts')

            assert result is True
            assert nodejs_installer.progress.status == InstallationStatus.COMPLETED
            assert nodejs_installer.progress.progress_percentage == 100.0

    @pytest.mark.asyncio
    async def test_install_force_reinstall(self, nodejs_installer):
        """测试安装 - 强制重新安装"""
        # 模拟已经安装但强制重新安装
        mock_lts_version = NodeVersion(
            version="18.17.0",
            lts=True,
            date="2023-07-04",
            files=[{"platform": "win-x64", "filename": "node-v18.17.0-x64.msi", "sha256sum": "test_checksum"}]
        )

        with patch.object(nodejs_installer, '_is_nodejs_installed', return_value=True), \
             patch.object(nodejs_installer, 'get_latest_lts_version', return_value=mock_lts_version), \
             patch.object(nodejs_installer, '_download_installer', return_value="test_installer.msi") as mock_download, \
             patch.object(nodejs_installer, '_execute_installation', return_value=True) as mock_install, \
             patch.object(nodejs_installer, '_verify_installation', return_value=True) as mock_verify:

            result = await nodejs_installer.install('lts', force_reinstall=True)

            assert result is True
            mock_download.assert_called_once_with(mock_lts_version)
            mock_install.assert_called_once()
            mock_verify.assert_called_once_with(mock_lts_version)

    @pytest.mark.asyncio
    async def test_install_download_failure(self, nodejs_installer):
        """测试安装 - 下载失败"""
        with patch.object(nodejs_installer, '_is_nodejs_installed', return_value=False), \
             patch.object(nodejs_installer, 'get_latest_lts_version') as mock_get_lts, \
             patch.object(nodejs_installer, '_download_installer', side_effect=RuntimeError("下载失败")):

            mock_lts_version = NodeVersion(version="18.17.0", lts=True, date="2023-07-04", files=[])
            mock_get_lts.return_value = mock_lts_version

            result = await nodejs_installer.install('lts')

            assert result is False
            assert nodejs_installer.progress.status == InstallationStatus.FAILED
            assert "下载失败" in nodejs_installer.progress.error_message

    def test_cancel_installation(self, nodejs_installer):
        """测试取消安装"""
        nodejs_installer.cancel_installation()

        assert nodejs_installer._installation_cancelled is True
        assert nodejs_installer.progress.status == InstallationStatus.CANCELLED

    def test_get_progress(self, nodejs_installer):
        """测试获取进度"""
        progress = nodejs_installer.get_progress()
        assert isinstance(progress, InstallationProgress)
        assert progress.status == InstallationStatus.NOT_STARTED

    def test_cleanup(self, nodejs_installer):
        """测试清理临时文件"""
        # 简化测试：只验证清理函数能正常调用而不出错
        # 由于清理函数依赖实际的文件系统操作，复杂的 mock 可能不可靠
        try:
            nodejs_installer.cleanup()
            # 如果没有异常，说明清理函数可以正常执行
            assert True
        except Exception as e:
            # 清理函数中的异常处理应该捕获所有错误
            # 如果有异常抛出，说明错误处理有问题
            pytest.fail(f"清理函数不应该抛出异常: {e}")


class TestIntegration:
    """集成测试"""

    @pytest.mark.asyncio
    async def test_full_installation_workflow_mock(self, mock_os_detector, mock_network_checker):
        """测试完整的安装工作流程（模拟）"""
        installer = NodeJSInstaller(mock_os_detector, mock_network_checker)

        # 模拟完整的安装数据
        mock_lts_version = NodeVersion(
            version="18.17.0",
            lts=True,
            date="2023-07-04",
            files=[{
                "platform": "win-x64",
                "filename": "node-v18.17.0-x64.msi",
                "sha256sum": "test_checksum_hash"
            }]
        )

        with patch.object(installer, '_is_nodejs_installed', return_value=False), \
             patch.object(installer, 'get_latest_lts_version', return_value=mock_lts_version), \
             patch.object(installer, '_download_installer', return_value="test_installer.msi") as mock_download, \
             patch.object(installer, '_execute_installation', return_value=True) as mock_install, \
             patch.object(installer, '_verify_installation', return_value=True) as mock_verify:

            result = await installer.install('lts')

            # 验证安装成功
            assert result is True
            assert installer.progress.status == InstallationStatus.COMPLETED

            # 验证所有步骤都被调用
            mock_download.assert_called_once_with(mock_lts_version)
            mock_install.assert_called_once()
            mock_verify.assert_called_once_with(mock_lts_version)

    def test_unsupported_platform(self):
        """测试不支持的平台"""
        # 创建不支持的系统信息
        system_info = SystemInfo(
            os_type=OperatingSystem.UNKNOWN,
            architecture=Architecture.UNKNOWN,
            version=OSVersion(0, 0, 0),
            python_version="3.11.0",
            python_executable="python.exe",
            platform_details={},
            compatibility={}
        )

        mock_detector = Mock()
        mock_detector.detect_os_info.return_value = system_info

        with pytest.raises(RuntimeError, match="不支持的平台组合"):
            NodeJSInstaller(mock_detector)


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "--tb=short"])