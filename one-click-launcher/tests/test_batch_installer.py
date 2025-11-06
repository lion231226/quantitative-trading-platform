"""
批量安装引擎测试

This module contains comprehensive tests for the batch dependency installation engine
including parallel installation, resource management, and progress tracking.
"""

import pytest
import tempfile
import time
from unittest.mock import Mock, patch, MagicMock

from core.batch_installer import (
    BatchInstaller,
    DependencyInstaller,
    ResourceMonitor,
    InstallationStatus,
    InstallationResult,
    InstallationContext,
    ResourceUsage
)
from core.dependency_analyzer import ProjectDependency, DependencyAnalysis
from core.installation_strategy import InstallationStrategy, InstallationMode, PackageSource, PackageSourceType


class TestResourceMonitor:
    """资源监控器测试"""

    @pytest.fixture
    def monitor(self):
        """创建资源监控器实例"""
        return ResourceMonitor(max_cpu_percent=80.0, max_memory_percent=85.0)

    def test_get_current_usage(self, monitor):
        """测试获取当前资源使用情况"""
        with patch('psutil.cpu_percent') as mock_cpu, \
             patch('psutil.virtual_memory') as mock_memory, \
             patch('psutil.pids') as mock_pids:

            # 模拟资源使用情况
            mock_cpu.return_value = 45.5
            mock_memory_obj = Mock()
            mock_memory_obj.percent = 60.2
            mock_memory_obj.used = 4 * 1024 * 1024 * 1024  # 4GB
            mock_memory.return_value = mock_memory_obj
            mock_pids.return_value = [1, 2, 3, 4, 5]

            usage = monitor.get_current_usage()

            assert usage.cpu_percent == 45.5
            assert usage.memory_percent == 60.2
            assert usage.memory_mb == 4096
            assert usage.active_processes == 5

    def test_is_resource_available(self, monitor):
        """测试资源可用性检查"""
        # 资源充足
        good_usage = ResourceUsage(cpu_percent=50.0, memory_percent=70.0, memory_mb=2048, active_processes=10)
        assert monitor.is_resource_available(good_usage) is True

        # CPU过高
        high_cpu = ResourceUsage(cpu_percent=90.0, memory_percent=70.0, memory_mb=2048, active_processes=10)
        assert monitor.is_resource_available(high_cpu) is False

        # 内存过高
        high_memory = ResourceUsage(cpu_percent=50.0, memory_percent=90.0, memory_mb=4096, active_processes=10)
        assert monitor.is_resource_available(high_memory) is False


class TestDependencyInstaller:
    """依赖安装器测试"""

    @pytest.fixture
    def installer(self):
        """创建依赖安装器实例"""
        monitor = ResourceMonitor()
        return DependencyInstaller(monitor)

    @pytest.fixture
    def sample_dependency(self):
        """创建示例依赖"""
        return ProjectDependency(
            name="test-package",
            ecosystem="python",
            version_spec="==1.0.0",
            source_file="requirements.txt"
        )

    @pytest.fixture
    def sample_strategy(self):
        """创建示例安装策略"""
        source = PackageSource(
            name="test-source",
            url="https://test-source.com",
            source_type=PackageSourceType.MIRROR,
            ecosystem="python"
        )

        strategy = InstallationStrategy(
            dependency=ProjectDependency("test-package", "python"),
            mode=InstallationMode.ONLINE,
            package_manager="pip",
            source=source,
            install_command=["pip", "install", "test-package==1.0.0"]
        )
        return strategy

    def test_install_dry_run(self, installer, sample_dependency, sample_strategy):
        """测试试运行安装"""
        result = installer.install(sample_dependency, sample_strategy, dry_run=True)

        assert result.status == InstallationStatus.COMPLETED
        assert result.success is True
        assert "[DRY RUN]" in result.output
        assert result.return_code is None

    def test_install_success(self, installer, sample_dependency, sample_strategy):
        """测试成功安装"""
        with patch('subprocess.Popen') as mock_popen:
            # 模拟成功安装
            mock_process = Mock()
            mock_process.communicate.return_value = ("Successfully installed", 0)
            mock_process.returncode = 0
            mock_popen.return_value = mock_process

            result = installer.install(sample_dependency, sample_strategy)

            assert result.status == InstallationStatus.COMPLETED
            assert result.success is True
            assert result.return_code == 0
            assert "Successfully installed" in result.output

    def test_install_failure(self, installer, sample_dependency, sample_strategy):
        """测试安装失败"""
        with patch('subprocess.Popen') as mock_popen:
            # 模拟安装失败
            mock_process = Mock()
            mock_process.communicate.return_value = ("Installation failed", 1)
            mock_process.returncode = 1
            mock_popen.return_value = mock_process

            result = installer.install(sample_dependency, sample_strategy)

            assert result.status == InstallationStatus.FAILED
            assert result.success is False
            assert result.return_code == 1
            assert result.error_message is not None

    def test_install_timeout(self, installer, sample_dependency, sample_strategy):
        """测试安装超时"""
        with patch('subprocess.Popen') as mock_popen:
            # 模拟超时
            mock_process = Mock()
            mock_process.communicate.side_effect = subprocess.TimeoutExpired("cmd", 300)
            mock_process.kill.return_value = None
            mock_process.wait.return_value = None
            mock_popen.return_value = mock_process

            result = installer.install(sample_dependency, sample_strategy, timeout=1)

            assert result.status == InstallationStatus.FAILED
            assert result.success is False
            assert "超时" in result.error_message

    def test_get_installed_version_python(self, installer, sample_dependency, sample_strategy):
        """测试获取Python包版本"""
        with patch('subprocess.run') as mock_run:
            # 模拟pip show输出
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "Name: test-package\nVersion: 1.0.0\nSummary: Test package"

            version = installer._get_installed_version(sample_dependency, sample_strategy)

            assert version == "1.0.0"

    def test_get_installed_version_nodejs(self, installer, sample_dependency, sample_strategy):
        """测试获取Node.js包版本"""
        # 修改为Node.js生态
        sample_dependency.ecosystem = "nodejs"
        sample_strategy.package_manager = "npm"

        with patch('subprocess.run') as mock_run:
            # 模拟npm list输出
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "test@1.0.0 node_modules/test"

            version = installer._get_installed_version(sample_dependency, sample_strategy)

            assert version == "1.0.0"


class TestBatchInstaller:
    """批量安装器测试"""

    @pytest.fixture
    def installer(self):
        """创建批量安装器实例"""
        return BatchInstaller(max_concurrent=2, timeout=300)

    @pytest.fixture
    def sample_context(self):
        """创建示例安装上下文"""
        # 创建模拟依赖
        dependencies = [
            ProjectDependency("dep1", "python", "==1.0.0", "req1.txt"),
            ProjectDependency("dep2", "nodejs", "^2.0.0", "package.json"),
        ]

        # 创建模拟策略
        strategies = []
        for dep in dependencies:
            source = PackageSource(
                name="test-source",
                url="https://test.com",
                source_type=PackageSourceType.OFFICIAL,
                ecosystem=dep.ecosystem
            )
            strategy = InstallationStrategy(
                dependency=dep,
                mode=InstallationMode.ONLINE,
                package_manager="pip" if dep.ecosystem == "python" else "npm",
                source=source,
                install_command=[f"{dep.ecosystem}-install", dep.name]
            )
            strategies.append(strategy)

        # 创建模拟分析
        analysis = Mock(spec=DependencyAnalysis)
        analysis.project_root = "/test/project"
        analysis.all_dependencies = dependencies

        return InstallationContext(
            project_root="/test/project",
            analysis=analysis,
            strategies=strategies,
            max_concurrent=2,
            timeout=300,
            dry_run=True  # 使用试运行模式
        )

    def test_install_dependencies_dry_run(self, installer, sample_context):
        """测试批量安装（试运行）"""
        results = installer.install_dependencies(sample_context)

        assert len(results) == len(sample_context.strategies)
        assert all(result.status == InstallationStatus.COMPLETED for result in results)
        assert all(result.success for result in results)
        assert all("[DRY RUN]" in result.output for result in results)

    def test_install_dependencies_with_failure(self, installer, sample_context):
        """测试批量安装（包含失败）"""
        sample_context.dry_run = False
        sample_context.continue_on_error = True

        with patch('subprocess.Popen') as mock_popen:
            # 模拟第一个成功，第二个失败
            def side_effect(*args, **kwargs):
                mock_process = Mock()
                if "dep1" in " ".join(args[0]):
                    mock_process.communicate.return_value = ("Success", 0)
                    mock_process.returncode = 0
                else:
                    mock_process.communicate.return_value = ("Failed", 1)
                    mock_process.returncode = 1
                return mock_process

            mock_popen.side_effect = side_effect

            results = installer.install_dependencies(sample_context)

            assert len(results) == 2
            assert results[0].success is True
            assert results[1].success is False

    def test_cancel_installation(self, installer, sample_context):
        """测试取消安装"""
        # 在另一个线程中开始安装，然后立即取消
        import threading

        def install():
            return installer.install_dependencies(sample_context)

        install_thread = threading.Thread(target=install)
        install_thread.start()

        # 立即取消
        time.sleep(0.1)
        installer.cancel_installation()

        install_thread.join(timeout=2)

        assert installer.is_installing() is False

    def test_get_installation_progress(self, installer):
        """测试获取安装进度"""
        # 初始状态
        progress = installer.get_installation_progress()
        assert progress["total"] == 0
        assert progress["progress_percentage"] == 0.0

    def test_get_installation_summary(self, installer):
        """测试获取安装摘要"""
        # 创建模拟结果
        results = [
            InstallationResult(
                dependency=ProjectDependency("dep1", "python"),
                strategy=Mock(),
                status=InstallationStatus.COMPLETED,
                start_time=time.time(),
                end_time=time.time() + 1,
                success=True
            ),
            InstallationResult(
                dependency=ProjectDependency("dep2", "nodejs"),
                strategy=Mock(),
                status=InstallationStatus.FAILED,
                start_time=time.time(),
                end_time=time.time() + 1,
                success=False,
                error_message="Test error"
            )
        ]

        summary = installer.get_installation_summary(results)

        assert summary["total_dependencies"] == 2
        assert summary["successful_installations"] == 1
        assert summary["failed_installations"] == 1
        assert summary["success_rate"] == 50.0
        assert len(summary["failed_dependencies"]) == 1

    def test_try_fallback_installation(self, installer, sample_context):
        """测试回退安装"""
        dependency = sample_context.strategies[0].dependency
        primary_strategy = sample_context.strategies[0]

        # 添加回退源
        fallback_source = PackageSource(
            name="fallback-source",
            url="https://fallback.com",
            source_type=PackageSourceType.MIRROR,
            ecosystem=dependency.ecosystem
        )
        primary_strategy.fallback_sources = [fallback_source]

        with patch('subprocess.Popen') as mock_popen:
            # 第一次失败，第二次成功
            call_count = 0
            def side_effect(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                mock_process = Mock()
                if call_count == 1:
                    mock_process.communicate.return_value = ("Failed", 1)
                    mock_process.returncode = 1
                else:
                    mock_process.communicate.return_value = ("Success with fallback", 0)
                    mock_process.returncode = 0
                return mock_process

            mock_popen.side_effect = side_effect

            result = installer._try_fallback_installation(
                dependency, primary_strategy, 300, False
            )

            assert result.success is True
            assert result.metadata.get("fallback_source") == "fallback-source"


def test_create_batch_installer():
    """测试创建批量安装器的便利函数"""
    from core.batch_installer import create_batch_installer

    # 创建模拟分析
    analysis = Mock(spec=DependencyAnalysis)
    analysis.project_root = "/test"
    analysis.all_dependencies = []

    config_manager = Mock()
    config_manager.get_max_concurrent_installs.return_value = 4
    config_manager.get_installation_timeout.return_value = 300

    installer, context = create_batch_installer(analysis, config_manager)

    assert isinstance(installer, BatchInstaller)
    assert isinstance(context, InstallationContext)
    assert context.max_concurrent == 4
    assert context.timeout == 300


if __name__ == "__main__":
    pytest.main([__file__, "-v"])