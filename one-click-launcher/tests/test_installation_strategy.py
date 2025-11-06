"""
安装策略选择器测试

This module contains comprehensive tests for the installation strategy selector
including network detection, mirror selection, and strategy generation.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from core.installation_strategy import (
    InstallationStrategySelector,
    InstallationMode,
    NetworkStatus,
    PackageSourceType,
    ProjectDependency,
    PackageSource,
    NetworkInfo,
    InstallationStrategy
)


class TestNetworkDetector:
    """网络检测器测试"""

    @pytest.fixture
    def detector(self):
        """创建网络检测器实例"""
        from core.installation_strategy import NetworkDetector
        return NetworkDetector()

    def test_detect_network_status_connected(self, detector):
        """测试网络连接状态检测"""
        # 修复mock路径，使用正确的urlopen模块路径
        with patch('urllib.request.urlopen') as mock_urlopen:
            # 模拟成功响应
            mock_response = Mock()
            mock_response.getcode.return_value = 200
            mock_urlopen.return_value = mock_response

            # 测试连接性
            connectivity = detector._test_connectivity()
            assert connectivity["connected"] is True
            assert connectivity["success_rate"] > 0

            # 测试状态确定
            status = detector._determine_status(connectivity, {"avg_latency": 100}, {"bandwidth": 10.0})
            assert status == NetworkStatus.CONNECTED

    def test_detect_network_status_disconnected(self, detector):
        """测试网络断开状态检测"""
        with patch('urllib.request.urlopen') as mock_urlopen:
            # 模拟连接失败
            mock_urlopen.side_effect = Exception("Connection failed")

            network_info = detector.detect_network_status()

            assert network_info.status == NetworkStatus.DISCONNECTED

    def test_test_connectivity(self, detector):
        """测试连接性测试"""
        with patch('urllib.request.urlopen') as mock_urlopen:
            mock_response = Mock()
            mock_response.getcode.return_value = 200
            mock_urlopen.return_value = mock_response

            result = detector._test_connectivity()

            assert result["connected"] is True
            assert result["success_rate"] > 0

    def test_determine_status_connected(self, detector):
        """测试状态确定"""
        connectivity = {"connected": True, "success_rate": 1.0}
        latency = {"avg_latency": 100}
        bandwidth = {"bandwidth": 10.0}

        status = detector._determine_status(connectivity, latency, bandwidth)

        assert status == NetworkStatus.CONNECTED


class TestMirrorSelector:
    """镜像源选择器测试"""

    @pytest.fixture
    def selector(self):
        """创建镜像源选择器实例"""
        from core.installation_strategy import MirrorSelector
        return MirrorSelector()

    def test_get_available_mirrors_python(self, selector):
        """测试获取 Python 镜像源"""
        mirrors = selector.get_available_mirrors("python")

        assert len(mirrors) > 0
        assert any(m.name == "pypi-official" for m in mirrors)
        assert any(m.name == "pypi-tuna" for m in mirrors)
        assert all(m.ecosystem == "python" for m in mirrors)

    def test_get_available_mirrors_nodejs(self, selector):
        """测试获取 Node.js 镜像源"""
        mirrors = selector.get_available_mirrors("nodejs")

        assert len(mirrors) > 0
        assert any(m.name == "npm-official" for m in mirrors)
        assert any(m.name == "npm-taobao" for m in mirrors)
        assert all(m.ecosystem == "nodejs" for m in mirrors)

    def test_select_best_mirror_good_network(self, selector):
        """测试网络良好时选择最佳镜像"""
        network_info = NetworkInfo(status=NetworkStatus.CONNECTED, latency_ms=50)

        with patch.object(selector, '_test_mirror_speed') as mock_test:
            # 模拟测试结果
            fast_mirror = PackageSource(
                name="fast-mirror",
                url="https://fast-mirror.com",
                source_type=PackageSourceType.MIRROR,
                ecosystem="python"
            )
            fast_mirror.response_time_ms = 50
            mock_test.return_value = fast_mirror

            best = selector.select_best_mirror("python", network_info)

            assert best is not None
            assert best.name == "fast-mirror"

    def test_select_best_mirror_slow_network(self, selector):
        """测试网络缓慢时选择镜像源"""
        network_info = NetworkInfo(status=NetworkStatus.SLOW, latency_ms=5000)

        best = selector.select_best_mirror("python", network_info)

        assert best is not None
        assert best.source_type == PackageSourceType.MIRROR


class TestInstallationStrategySelector:
    """安装策略选择器测试"""

    @pytest.fixture
    def selector(self):
        """创建策略选择器实例"""
        config_manager = Mock()
        # Mock不同的生态系统返回不同的包管理器
        def mock_get_package_manager(ecosystem):
            managers = {
                "python": "pip",
                "nodejs": "npm",
                "unknown": "unknown"
            }
            return managers.get(ecosystem, "unknown")

        config_manager.get_package_manager.side_effect = mock_get_package_manager
        return InstallationStrategySelector(config_manager)

    @pytest.fixture
    def sample_dependency(self):
        """创建示例依赖"""
        return ProjectDependency(
            name="fastapi",
            ecosystem="python",
            version_spec="==0.111.0",
            source_file="requirements.txt"
        )

    def test_select_installation_strategy_online(self, selector, sample_dependency):
        """测试在线模式策略选择"""
        with patch.object(selector, '_get_network_info') as mock_network:
            # 模拟网络连接良好
            network_info = NetworkInfo(status=NetworkStatus.CONNECTED, latency_ms=100)
            mock_network.return_value = network_info

            with patch.object(selector.mirror_selector, 'select_best_mirror') as mock_mirror:
                # 模拟选择到镜像源
                mirror = PackageSource(
                    name="pypi-tuna",
                    url="https://pypi.tuna.tsinghua.edu.cn/simple/",
                    source_type=PackageSourceType.MIRROR,
                    ecosystem="python"
                )
                mock_mirror.return_value = mirror

                strategy = selector.select_installation_strategy(sample_dependency)

                assert strategy.dependency == sample_dependency
                assert strategy.mode == InstallationMode.ONLINE
                assert strategy.package_manager == "pip"
                assert strategy.source.name == "pypi-tuna"
                assert "pip install" in " ".join(strategy.install_command)
                assert strategy.confidence_score > 0

    def test_select_installation_strategy_offline(self, selector, sample_dependency):
        """测试离线模式策略选择"""
        with patch.object(selector, '_get_network_info') as mock_network:
            # 模拟网络断开
            network_info = NetworkInfo(status=NetworkStatus.DISCONNECTED)
            mock_network.return_value = network_info

            strategy = selector.select_installation_strategy(sample_dependency)

            assert strategy.mode == InstallationMode.OFFLINE
            assert strategy.source.source_type == PackageSourceType.LOCAL

    def test_select_package_manager(self, selector):
        """测试包管理器选择"""
        # 测试 Python
        manager = selector._select_package_manager("python")
        assert manager == "pip"

        # 测试 Node.js
        manager = selector._select_package_manager("nodejs")
        assert manager == "npm"

        # 测试未知生态系统
        manager = selector._select_package_manager("unknown")
        assert manager == "unknown"

    def test_generate_python_command(self, selector, sample_dependency):
        """测试 Python 安装命令生成"""
        source = PackageSource(
            name="pypi-tuna",
            url="https://pypi.tuna.tsinghua.edu.cn/simple/",
            source_type=PackageSourceType.MIRROR,
            ecosystem="python"
        )

        command = selector._generate_install_command(
            sample_dependency, "pip", source, InstallationMode.ONLINE
        )

        assert command[0] == "pip"
        assert "install" in command
        assert "-i" in command
        assert source.url in command
        assert f"{sample_dependency.name}{sample_dependency.version_spec}" in command

    def test_generate_nodejs_command(self, selector):
        """测试 Node.js 安装命令生成"""
        dependency = ProjectDependency(
            name="react",
            ecosystem="nodejs",
            version_spec="^18.0.0",
            source_file="package.json"
        )

        source = PackageSource(
            name="npm-taobao",
            url="https://registry.npmmirror.com/",
            source_type=PackageSourceType.MIRROR,
            ecosystem="nodejs"
        )

        command = selector._generate_install_command(
            dependency, "npm", source, InstallationMode.ONLINE
        )

        assert command[0] == "npm"
        assert "install" in command
        assert "--registry" in command
        assert source.url in command
        assert f"{dependency.name}@{dependency.version_spec}" in command

    def test_prepare_fallback_sources(self, selector):
        """测试回退源准备"""
        primary_source = PackageSource(
            name="primary",
            url="https://primary.com",
            source_type=PackageSourceType.OFFICIAL,
            ecosystem="python"
        )

        fallback_sources = selector._prepare_fallback_sources("python", primary_source, InstallationMode.ONLINE)

        assert len(fallback_sources) <= 3
        assert all(source.name != "primary" for source in fallback_sources)
        assert all(source.ecosystem == "python" for source in fallback_sources)

    def test_estimate_installation_time(self, selector, sample_dependency):
        """测试安装时间估算"""
        # 在线模式
        time_sec = selector._estimate_installation_time(sample_dependency, InstallationMode.ONLINE)
        assert isinstance(time_sec, int)
        assert time_sec > 0

        # 离线模式（应该更快）
        offline_time = selector._estimate_installation_time(sample_dependency, InstallationMode.OFFLINE)
        assert offline_time < time_sec

    def test_calculate_confidence(self, selector, sample_dependency):
        """测试置信度计算"""
        network_info = NetworkInfo(status=NetworkStatus.CONNECTED, latency_ms=100)

        confidence = selector._calculate_confidence(
            sample_dependency, InstallationMode.ONLINE, network_info
        )

        assert 0.0 <= confidence <= 1.0
        assert confidence > 0.5  # 良好网络应该有较高置信度

    def test_batch_select_strategies(self, selector):
        """测试批量策略选择"""
        dependencies = [
            ProjectDependency("fastapi", "python", "==0.111.0", "req.txt"),
            ProjectDependency("react", "nodejs", "^18.0.0", "package.json"),
            ProjectDependency("redis", "database", "", "docker.yml"),
        ]

        with patch.object(selector, 'select_installation_strategy') as mock_select:
            # 模拟单个策略选择
            mock_strategy = Mock(spec=InstallationStrategy)
            mock_strategy.confidence_score = 0.8
            mock_select.return_value = mock_strategy

            strategies = selector.batch_select_strategies(dependencies)

            assert len(strategies) == len(dependencies)
            assert mock_select.call_count == len(dependencies)

    def test_get_strategy_summary(self, selector):
        """测试策略摘要"""
        strategies = [
            Mock(spec=InstallationStrategy, mode=InstallationMode.ONLINE, confidence_score=0.8),
            Mock(spec=InstallationStrategy, mode=InstallationMode.OFFLINE, confidence_score=0.6),
        ]

        # 设置依赖属性
        for i, strategy in enumerate(strategies):
            strategy.dependency = Mock()
            strategy.dependency.ecosystem = "python" if i == 0 else "nodejs"
            strategy.source = Mock()
            strategy.source.source_type = PackageSourceType.MIRROR
            strategy.estimated_time_sec = 60

        summary = selector.get_strategy_summary(strategies)

        assert "total_strategies" in summary
        assert "average_confidence" in summary
        assert "modes_distribution" in summary
        assert summary["total_strategies"] == 2
        assert summary["average_confidence"] == 0.7


if __name__ == "__main__":
    pytest.main([__file__, "-v"])