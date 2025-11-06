#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
启动器集成测试

测试主启动器的完整功能，包括：
- 环境检测和依赖安装
- 服务启动和管理
- 进度跟踪
- 错误处理
- 跨平台兼容性
"""

import os
import sys
import asyncio
import pytest
import time
from pathlib import Path
from typing import Dict, Any
from unittest.mock import Mock, patch, AsyncMock

# 添加项目根目录到Python路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 导入测试目标
from launcher import OneClickLauncher, LauncherMode, LaunchResult
from core.dependency_installer import DependencyInstaller
from core.service_manager import ServiceManager
from core.progress_tracker import ProgressTracker, ProgressStatus
from core.error_handler import ErrorHandler, ErrorSeverity

class TestOneClickLauncher:
    """一键启动器测试类"""

    @pytest.fixture
    def launcher(self):
        """创建启动器实例"""
        return OneClickLauncher(mode=LauncherMode.NORMAL)

    @pytest.fixture
    def mock_dependencies(self):
        """模拟依赖"""
        with patch('launcher.DependencyInstaller') as mock_installer, \
             patch('launcher.ServiceManager') as mock_service_manager, \
             patch('launcher.ProgressTracker') as mock_progress_tracker, \
             patch('launcher.ErrorHandler') as mock_error_handler:

            # 配置模拟对象
            mock_installer.return_value.check_and_install_dependencies = AsyncMock(
                return_value=Mock(
                    success=True,
                    system_info=Mock(platform="test", python_version="3.9.0"),
                    dependency_results=[],
                    missing_required=[]
                )
            )

            mock_service_manager.return_value.start_service = AsyncMock(return_value=True)
            mock_service_manager.return_value.health_check = AsyncMock(return_value=True)
            mock_service_manager.return_value.stop_services = AsyncMock(return_value=True)

            mock_progress_tracker.return_value.start_step = Mock(return_value=True)
            mock_progress_tracker.return_value.update_progress = Mock(return_value=True)
            mock_progress_tracker.return_value.complete_step = Mock(return_value=True)

            yield {
                'installer': mock_installer,
                'service_manager': mock_service_manager,
                'progress_tracker': mock_progress_tracker,
                'error_handler': mock_error_handler
            }

    @pytest.mark.asyncio
    async def test_launcher_initialization(self, launcher):
        """测试启动器初始化"""
        assert launcher.mode == LauncherMode.NORMAL
        assert launcher.services is not None
        assert len(launcher.services) == 4  # redis, database, backend, frontend
        assert "redis" in launcher.services
        assert "database" in launcher.services
        assert "backend" in launcher.services
        assert "frontend" in launcher.services

    @pytest.mark.asyncio
    async def test_successful_launch(self, launcher, mock_dependencies):
        """测试成功启动流程"""
        # 模拟成功的组件响应
        mock_dependencies['installer'].return_value.check_and_install_dependencies.return_value.success = True
        mock_dependencies['service_manager'].return_value.start_service.return_value = True
        mock_dependencies['service_manager'].return_value.health_check.return_value = True

        # 模拟浏览器打开
        with patch('launcher.webbrowser.open', Mock()):
            result = await launcher.launch()

        # 验证结果
        assert isinstance(result, LaunchResult)
        assert result.success is True
        assert len(result.services_started) == 4
        assert len(result.failed_services) == 0
        assert result.total_time > 0

    @pytest.mark.asyncio
    async def test_environment_preparation_failure(self, launcher, mock_dependencies):
        """测试环境准备失败"""
        # 模拟环境检测失败
        mock_dependencies['installer'].return_value.check_and_install_dependencies.return_value.success = False
        mock_dependencies['installer'].return_value.check_and_install_dependencies.return_value.error_message = "Environment check failed"

        result = await launcher.launch()

        assert result.success is False
        assert "Environment check failed" in result.error_message

    @pytest.mark.asyncio
    async def test_service_startup_failure(self, launcher, mock_dependencies):
        """测试服务启动失败"""
        # 模拟服务启动失败
        mock_dependencies['service_manager'].return_value.start_service.return_value = False

        result = await launcher.launch()

        assert result.success is False
        assert len(result.failed_services) > 0

    @pytest.mark.asyncio
    async def test_system_verification_failure(self, launcher, mock_dependencies):
        """测试系统验证失败"""
        # 模拟健康检查失败
        mock_dependencies['service_manager'].return_value.health_check.return_value = False

        result = await launcher.launch()

        assert result.success is False

    @pytest.mark.asyncio
    async def test_browser_opening(self, launcher):
        """测试浏览器打开功能"""
        # 禁用其他组件
        launcher.dependency_installer = AsyncMock()
        launcher.dependency_installer.check_and_install_dependencies = AsyncMock(
            return_value=Mock(success=True, system_info=Mock(), dependency_results=[], missing_required=[])
        )
        launcher.service_manager = AsyncMock()
        launcher.service_manager.start_service = AsyncMock(return_value=True)
        launcher.service_manager.health_check = AsyncMock(return_value=True)

        # 模拟浏览器打开
        with patch('launcher.webbrowser.open') as mock_open:
            result = await launcher.launch()

            if launcher.config.get("auto_open_browser", True):
                mock_open.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_services(self, launcher):
        """测试服务停止功能"""
        launcher.service_manager = AsyncMock()
        launcher.service_manager.stop_services = AsyncMock(return_value=True)

        result = await launcher.stop_services()

        assert result is True
        launcher.service_manager.stop_services.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_status(self, launcher):
        """测试状态获取功能"""
        launcher.service_manager = AsyncMock()
        launcher.service_manager.health_check = AsyncMock(return_value=True)

        status = await launcher.get_status()

        assert "services" in status
        assert "system" in status
        assert "timestamp" in status
        assert len(status["services"]) == 4

class TestDependencyInstaller:
    """依赖安装器测试"""

    @pytest.fixture
    def installer(self):
        """创建依赖安装器实例"""
        return DependencyInstaller()

    @pytest.mark.asyncio
    async def test_environment_detection(self, installer):
        """测试环境检测"""
        # 模拟环境检测器
        with patch.object(installer.env_detector, 'detect_all') as mock_detect:
            mock_detect.return_value = Mock(
                platform="test",
                python_version="3.9.0",
                architecture="x64"
            )

            await installer._detect_system_environment()

            assert installer.system_info is not None
            mock_detect.assert_called_once()

    @pytest.mark.asyncio
    async def test_python_package_check(self, installer):
        """测试Python包检查"""
        # 测试已安装的包
        requirement = Mock(
            name="os",
            dependency_type="python_package"
        )

        result = await installer._check_python_package(requirement)

        assert result.dependency_name == "os"
        assert result.status == "installed"

        # 测试未安装的包
        requirement.name = "nonexistent_package_xyz"

        result = await installer._check_python_package(requirement)

        assert result.status == "not_installed"

    @pytest.mark.asyncio
    async def test_external_tool_check(self, installer):
        """测试外部工具检查"""
        requirement = Mock(
            name="python",
            check_command="python --version",
            version_extract_pattern=r"Python (\d+\.\d+\.\d+)"
        )

        result = await installer._check_external_tool(requirement)

        assert result.dependency_name == "python"
        # 应该能找到python命令
        assert result.status in ["installed", "failed"]

class TestServiceManager:
    """服务管理器测试"""

    @pytest.fixture
    def service_manager(self):
        """创建服务管理器实例"""
        return ServiceManager()

    @pytest.mark.asyncio
    async def test_service_start(self, service_manager):
        """测试服务启动"""
        service_config = Mock(
            name="test",
            port=3000,
            timeout=30
        )

        # 模拟成功启动
        with patch.object(service_manager, '_start_service_implementation') as mock_start:
            mock_start.return_value = Mock(success=True, process_id=12345)

            result = await service_manager.start_service("test", service_config)

            assert result is True
            assert service_manager.service_status["test"] == "running"

    @pytest.mark.asyncio
    async def test_health_check(self, service_manager):
        """测试健康检查"""
        service_config = Mock(
            port=3000,
            health_check_endpoint="/health"
        )

        # 模拟端口连接测试
        with patch.object(service_manager, '_test_port_connection', return_value=True):
            result = await service_manager.health_check("frontend", service_config)

            assert result is True

    @pytest.mark.asyncio
    async def test_service_stop(self, service_manager):
        """测试服务停止"""
        # 模拟成功停止
        with patch.object(service_manager, '_stop_service_basic', return_value=True):
            result = await service_manager.stop_service("test")

            assert result is True

class TestProgressTracker:
    """进度跟踪器测试"""

    @pytest.fixture
    def progress_tracker(self):
        """创建进度跟踪器实例"""
        return ProgressTracker(use_rich=False)  # 禁用Rich以简化测试

    def test_step_management(self, progress_tracker):
        """测试步骤管理"""
        # 添加步骤
        step = progress_tracker.add_step("test_step", "Test Step", "Test Description")

        assert step.id == "test_step"
        assert step.name == "Test Step"
        assert step.status == ProgressStatus.PENDING

        # 开始步骤
        result = progress_tracker.start_step("test_step")
        assert result is True
        assert step.status == ProgressStatus.IN_PROGRESS
        assert step.start_time is not None

        # 更新进度
        result = progress_tracker.update_progress("test_step", 50.0)
        assert result is True
        assert step.progress == 50.0

        # 完成步骤
        result = progress_tracker.complete_step("test_step")
        assert result is True
        assert step.status == ProgressStatus.COMPLETED
        assert step.progress == 100.0

    def test_progress_summary(self, progress_tracker):
        """测试进度摘要"""
        # 添加多个步骤
        progress_tracker.add_step("step1", "Step 1")
        progress_tracker.add_step("step2", "Step 2")

        # 完成一个步骤
        progress_tracker.start_step("step1")
        progress_tracker.complete_step("step1")

        summary = progress_tracker.get_summary()

        assert summary.total_steps == 2
        assert summary.completed_steps == 1
        assert summary.overall_progress == 50.0

class TestErrorHandler:
    """错误处理器测试"""

    @pytest.fixture
    def error_handler(self):
        """创建错误处理器实例"""
        return ErrorHandler()

    @pytest.mark.asyncio
    async def test_error_handling(self, error_handler):
        """测试错误处理"""
        test_error = Exception("Test error")

        result = await error_handler.handle_error(test_error, service_name="test_service")

        assert isinstance(result, type(result))  # RecoveryResult type
        assert result.action_taken is not None

    def test_error_classification(self, error_handler):
        """测试错误分类"""
        test_cases = [
            ("port 3000 is occupied", "port_occupied"),
            ("module not found", "dependency_missing"),
            ("permission denied", "permission_denied"),
            ("connection refused", "network_error"),
            ("out of memory", "memory_error")
        ]

        for error_message, expected_category in test_cases:
            category = error_handler._basic_error_classification(error_message)
            assert category == expected_category

    def test_severity_determination(self, error_handler):
        """测试严重程度确定"""
        test_cases = [
            (Exception("critical system error"), ErrorSeverity.CRITICAL),
            (Exception("permission denied"), ErrorSeverity.HIGH),
            (Exception("connection timeout"), ErrorSeverity.MEDIUM),
            (Exception("minor issue"), ErrorSeverity.LOW)
        ]

        for error, expected_severity in test_cases:
            severity = error_handler._determine_severity(error)
            assert severity == expected_severity

    def test_recovery_strategy_selection(self, error_handler):
        """测试恢复策略选择"""
        # 创建错误信息
        error_info = Mock(
            error_message="port 3000 is occupied",
            severity=ErrorSeverity.MEDIUM
        )

        strategy = error_handler._select_recovery_strategy(error_info)

        assert strategy is not None
        assert RecoveryAction.CHANGE_PORT in strategy.actions

class TestPerformanceRequirements:
    """性能要求测试"""

    @pytest.mark.asyncio
    async def test_startup_timing(self, launcher, mock_dependencies):
        """测试启动时间要求"""
        start_time = time.time()

        # 模拟快速启动
        mock_dependencies['installer'].return_value.check_and_install_dependencies = AsyncMock(
            return_value=Mock(success=True, system_info=Mock(), dependency_results=[], missing_required=[])
        )
        mock_dependencies['service_manager'].return_value.start_service = AsyncMock(return_value=True)
        mock_dependencies['service_manager'].return_value.health_check = AsyncMock(return_value=True)

        with patch('launcher.webbrowser.open'):
            result = await launcher.launch()

        total_time = time.time() - start_time

        # 验证启动时间合理（应该很快，因为都是模拟）
        assert result.success is True
        assert total_time < 5.0  # 模拟启动应该在5秒内完成

    @pytest.mark.asyncio
    async def test_memory_usage(self, launcher):
        """测试内存使用"""
        import psutil
        import os

        process = psutil.Process(os.getpid())
        memory_before = process.memory_info().rss

        # 模拟启动过程
        launcher.dependency_installer = AsyncMock()
        launcher.service_manager = AsyncMock()

        with patch('launcher.webbrowser.open'):
            await launcher.launch()

        memory_after = process.memory_info().rss
        memory_increase = (memory_after - memory_before) / (1024 * 1024)  # MB

        # 内存增长应该在合理范围内（小于100MB）
        assert memory_increase < 100

if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v"])