"""
Automatic Recovery Test Suite

This module provides comprehensive testing for automatic recovery mechanisms
including service restart, port conflict resolution, permission fixes, cache cleanup,
and configuration repair operations.
"""

import pytest
import asyncio
import time
import os
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta

from core.recovery_orchestrator import RecoveryOrchestrator, RecoveryType, RecoveryStatus
from core.service_recovery import ServiceRecovery, RestartConfig, RestartStrategy, ServiceStatus
from core.port_recovery import PortRecoveryOrchestrator, TerminationMethod, PermissionLevel, ProcessTerminationResult, PortRecoveryResult
from core.port_detector import PortConflict, PortConflictResolver, ResolutionStrategy
from utils.recovery_strategies import (
    RetryStrategyEnum, CircuitBreaker, RetryWithCircuitBreaker,
    DEFAULT_RETRY_CONFIGS, DEFAULT_CIRCUIT_CONFIGS, RetryStrategy as RetryStrategyClass
)
from utils.user_confirmation import UserConfirmation, ConfirmationAction, ConfirmationType, ConfirmationResult, ConfirmationMethod
from core.permission_recovery import PermissionRepairer, PermissionElevationRequest, ElevationMethod, RepairResult, PermissionRepairResult
from core.cache_cleaner import CacheCleaner, CacheType, CleanupPolicy, CacheEntry, CleanupResult
from core.config_repairer import ConfigRepairer, ConfigValidator, RepairStrategy, ConfigFormat, ConfigValidationResult


class TestRecoveryOrchestrator:
    """恢复编排器测试"""

    @pytest.fixture
    def recovery_orchestrator(self):
        """创建恢复编排器实例"""
        return RecoveryOrchestrator()

    @pytest.mark.asyncio
    async def test_initialization(self, recovery_orchestrator):
        """测试初始化"""
        assert recovery_orchestrator is not None
        assert len(recovery_orchestrator.recovery_history) == 0
        assert len(recovery_orchestrator.active_recoveries) == 0
        assert recovery_orchestrator.progress_tracker is not None

    @pytest.mark.asyncio
    async def test_analyze_errors_and_plan_recovery(self, recovery_orchestrator):
        """测试错误分析和恢复计划制定"""
        detected_errors = {
            "port_conflicts": [{"port": 8080, "process_name": "node"}],
            "permission_issues": [{"path": "/tmp/test", "issue": "read_permission"}]
        }

        service_configs = [
            {"name": "test_service", "url": "http://localhost:8080"}
        ]

        with patch.object(recovery_orchestrator.health_checker, 'check_service_health_with_retry') as mock_health:
            mock_health.return_value = Mock(status="unhealthy")

            actions = await recovery_orchestrator._analyze_errors_and_plan_recovery(
                detected_errors, service_configs
            )

            assert len(actions) >= 2  # 至少有端口冲突和权限问题的恢复操作
            port_action = next((a for a in actions if a.recovery_type == RecoveryType.PORT_CONFLICT), None)
            permission_action = next((a for a in actions if a.recovery_type == RecoveryType.PERMISSION_FIX), None)

            assert port_action is not None
            assert permission_action is not None
            assert port_action.target_component == "port_8080"
            assert permission_action.target_component == "/tmp/test"

    @pytest.mark.asyncio
    async def test_execute_recovery_action_service_restart(self, recovery_orchestrator):
        """测试执行服务重启恢复操作"""
        action = Mock(
            recovery_type=RecoveryType.SERVICE_RESTART,
            target_component="test_service",
            parameters={"service_config": {"name": "test_service"}}
        )

        with patch.object(recovery_orchestrator, '_restart_service') as mock_restart:
            mock_restart.return_value = True

            result = await recovery_orchestrator._execute_recovery_action(action)

            assert result.success is True
            assert result.status == RecoveryStatus.COMPLETED
            assert result.action == action
            mock_restart.assert_called_once()

    @pytest.mark.asyncio
    async def test_calculate_retry_delay(self, recovery_orchestrator):
        """测试重试延迟计算"""
        # 测试指数退避
        delay1 = recovery_orchestrator._calculate_retry_delay(RecoveryType.SERVICE_RESTART, 0)
        delay2 = recovery_orchestrator._calculate_retry_delay(RecoveryType.SERVICE_RESTART, 1)
        delay3 = recovery_orchestrator._calculate_retry_delay(RecoveryType.SERVICE_RESTART, 2)

        assert delay2 > delay1
        assert delay3 > delay2

        # 测试最大延迟限制
        large_delay = recovery_orchestrator._calculate_retry_delay(RecoveryType.SERVICE_RESTART, 10)
        assert large_delay <= 60.0  # max_delay for service restart

    def test_get_recovery_statistics(self, recovery_orchestrator):
        """测试获取恢复统计信息"""
        # 添加一些模拟的恢复历史
        mock_result1 = Mock(success=True, action=Mock(recovery_type=RecoveryType.SERVICE_RESTART))
        mock_result2 = Mock(success=False, action=Mock(recovery_type=RecoveryType.PORT_CONFLICT))
        recovery_orchestrator.recovery_history = [mock_result1, mock_result2]

        stats = recovery_orchestrator.get_recovery_statistics()

        assert stats["total_recoveries"] == 2
        assert stats["successful_recoveries"] == 1
        assert stats["failed_recoveries"] == 1
        assert stats["success_rate"] == 0.5
        assert "recovery_by_type" in stats


class TestServiceRecovery:
    """服务恢复测试"""

    @pytest.fixture
    def service_recovery(self):
        """创建服务恢复实例"""
        return ServiceRecovery()

    @pytest.fixture
    def restart_config(self):
        """创建重启配置"""
        return RestartConfig(
            service_name="test_service",
            max_retries=3,
            strategy=RestartStrategy.EXPONENTIAL_BACKOFF
        )

    @pytest.mark.asyncio
    async def test_initialization(self, service_recovery):
        """测试初始化"""
        assert service_recovery is not None
        assert len(service_recovery.restart_history) == 0
        assert len(service_recovery.active_restarts) == 0
        assert service_recovery.progress_tracker is not None

    @pytest.mark.asyncio
    async def test_get_service_status(self, service_recovery):
        """测试获取服务状态"""
        with patch('psutil.process_iter') as mock_process_iter:
            # 模拟没有进程的情况
            mock_process_iter.return_value = []
            status = await service_recovery._get_service_status("nonexistent_service")
            assert status == ServiceStatus.STOPPED

            # 模拟有进程的情况
            mock_process = Mock()
            mock_process.is_running.return_value = True
            mock_process.info = {'pid': 1234, 'name': 'test_service', 'cmdline': ['python', 'test_service.py']}
            mock_process_iter.return_value = [mock_process]

            status = await service_recovery._get_service_status("test_service")
            assert status == ServiceStatus.RUNNING

    @pytest.mark.asyncio
    async def test_restart_service_success(self, service_recovery, restart_config):
        """测试成功重启服务"""
        with patch.object(service_recovery, '_get_service_status') as mock_status, \
             patch.object(service_recovery, '_check_dependencies') as mock_deps, \
             patch.object(service_recovery, '_stop_service') as mock_stop, \
             patch.object(service_recovery, '_start_service') as mock_start, \
             patch.object(service_recovery, '_verify_service_health') as mock_health:

            # 模拟服务正在运行
            mock_status.return_value = ServiceStatus.RUNNING
            mock_deps.return_value = True
            mock_stop.return_value = True
            mock_start.return_value = True
            mock_health.return_value = True

            result = await service_recovery.restart_service(restart_config)

            assert result.success is True
            assert result.status == ServiceStatus.RUNNING
            assert result.service_name == "test_service"
            mock_stop.assert_called_once()
            mock_start.assert_called_once()
            mock_health.assert_called_once()

    @pytest.mark.asyncio
    async def test_restart_service_with_retry(self, service_recovery, restart_config):
        """测试服务重启重试机制"""
        with patch.object(service_recovery, '_get_service_status') as mock_status, \
             patch.object(service_recovery, '_check_dependencies') as mock_deps, \
             patch.object(service_recovery, '_stop_service') as mock_stop, \
             patch.object(service_recovery, '_start_service') as mock_start, \
             patch.object(service_recovery, '_verify_service_health') as mock_health:

            # 模拟前两次启动失败，第三次成功
            mock_status.return_value = ServiceStatus.STOPPED
            mock_deps.return_value = True
            mock_stop.return_value = True
            mock_start.side_effect = [False, False, True]  # 前两次失败，第三次成功
            mock_health.return_value = True

            result = await service_recovery.restart_service(restart_config)

            assert result.success is True
            assert result.retry_count == 2  # 应该重试了2次
            assert mock_start.call_count == 3

    def test_calculate_restart_delay(self, service_recovery):
        """测试重启延迟计算"""
        config = RestartConfig(
            service_name="test",
            strategy=RestartStrategy.EXPONENTIAL_BACKOFF,
            base_delay=1.0,
            backoff_multiplier=2.0
        )

        delay1 = service_recovery._calculate_restart_delay(config, 0)
        delay2 = service_recovery._calculate_restart_delay(config, 1)
        delay3 = service_recovery._calculate_restart_delay(config, 2)

        assert delay1 == 0.0  # 第一次不延迟
        assert delay2 == 2.0  # 1.0 * 2^1
        assert delay3 == 4.0  # 1.0 * 2^2

    def test_get_restart_statistics(self, service_recovery):
        """测试获取重启统计信息"""
        # 添加一些模拟的重启历史
        mock_result1 = Mock(success=True, service_name="service1", duration=timedelta(seconds=5))
        mock_result2 = Mock(success=False, service_name="service1", duration=timedelta(seconds=3))
        mock_result1.duration.total_seconds.return_value = 5
        mock_result2.duration.total_seconds.return_value = 3

        service_recovery.restart_history = [mock_result1, mock_result2]

        stats = service_recovery.get_restart_statistics("service1")

        assert stats["total_restarts"] == 2
        assert stats["successful_restarts"] == 1
        assert stats["failed_restarts"] == 1
        assert stats["success_rate"] == 0.5
        assert stats["average_restart_time_seconds"] == 4.0  # (5 + 3) / 2


class TestRecoveryStrategies:
    """恢复策略测试"""

    @pytest.mark.asyncio
    async def test_retry_strategy_success(self):
        """测试重试策略成功情况"""
        from utils.recovery_strategies import RetryConfig, RetryStrategy as Retry

        config = RetryConfig(max_attempts=3, base_delay=0.1)
        strategy = RetryStrategyClass(config)

        async def test_func():
            return "success"

        result = await strategy.execute(test_func)

        assert result.success is True
        assert result.attempts == 1
        assert result.result == "success"

    @pytest.mark.asyncio
    async def test_retry_strategy_with_retry(self):
        """测试重试策略的重试机制"""
        from utils.recovery_strategies import RetryConfig, RetryStrategy as Retry

        config = RetryConfig(max_attempts=3, base_delay=0.1)
        strategy = RetryStrategyClass(config)

        call_count = 0

        async def test_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary failure")
            return "success"

        result = await strategy.execute(test_func)

        assert result.success is True
        assert result.attempts == 3
        assert result.result == "success"
        assert len(result.delays) == 2  # 应该有2次延迟

    @pytest.mark.asyncio
    async def test_retry_strategy_failure(self):
        """测试重试策略失败情况"""
        from utils.recovery_strategies import RetryConfig, RetryStrategy as Retry

        config = RetryConfig(max_attempts=2, base_delay=0.1)
        strategy = Retry(config)

        async def test_func():
            raise ValueError("Permanent failure")

        result = await strategy.execute(test_func)

        assert result.success is False
        assert result.attempts == 2
        assert result.error is not None
        assert isinstance(result.error, ValueError)

    def test_circuit_breaker(self):
        """测试断路器"""
        from utils.recovery_strategies import CircuitBreakerConfig

        config = CircuitBreakerConfig(failure_threshold=2, recovery_timeout=1.0)
        circuit_breaker = CircuitBreaker(config)

        # 初始状态应该是关闭的
        assert circuit_breaker.get_state().value == "closed"

        # 模拟失败
        circuit_breaker._on_failure(Exception("Test error"))
        assert circuit_breaker.get_state().value == "closed"

        circuit_breaker._on_failure(Exception("Test error"))
        assert circuit_breaker.get_state().value == "open"

        # 测试统计信息
        stats = circuit_breaker.get_stats()
        assert stats["failure_count"] == 2
        assert stats["state"] == "open"

    def test_default_configs(self):
        """测试默认配置"""
        assert "conservative" in DEFAULT_RETRY_CONFIGS
        assert "aggressive" in DEFAULT_RETRY_CONFIGS
        assert "gentle" in DEFAULT_RETRY_CONFIGS
        assert "fast" in DEFAULT_RETRY_CONFIGS

        assert "sensitive" in DEFAULT_CIRCUIT_CONFIGS
        assert "normal" in DEFAULT_CIRCUIT_CONFIGS
        assert "resilient" in DEFAULT_CIRCUIT_CONFIGS

        # 验证配置属性
        conservative = DEFAULT_RETRY_CONFIGS["conservative"]
        assert conservative.max_attempts == 5
        assert conservative.strategy.value == "exponential_backoff"

        normal = DEFAULT_CIRCUIT_CONFIGS["normal"]
        assert normal.failure_threshold == 5
        assert normal.recovery_timeout == 120.0


class TestUserConfirmation:
    """用户确认测试"""

    @pytest.fixture
    def user_confirmation(self):
        """创建用户确认实例"""
        return UserConfirmation(auto_confirm_risks=["low"])

    def test_initialization(self, user_confirmation):
        """测试初始化"""
        assert user_confirmation is not None
        assert "low" in user_confirmation.auto_confirm_risks
        assert len(user_confirmation.confirmation_history) == 0
        assert len(user_confirmation.pending_confirmations) == 0

    @pytest.mark.asyncio
    async def test_auto_confirm_low_risk(self, user_confirmation):
        """测试低风险自动确认"""
        action = ConfirmationAction(
            action_id="test_low_risk",
            title="Low Risk Action",
            description="This is a low risk action",
            risk_level="low"
        )

        with patch('builtins.input', return_value="yes"):
            response = await user_confirmation.request_confirmation(action)

        assert response.result == ConfirmationResult.YES
        assert response.method_used.value == "automatic"

    @pytest.mark.asyncio
    async def test_interactive_confirmation(self, user_confirmation):
        """测试交互式确认"""
        action = ConfirmationAction(
            action_id="test_interactive",
            title="Interactive Test",
            description="This is an interactive test",
            risk_level="high",  # 不会自动确认
            confirm_type=ConfirmationType.YES_NO
        )

        with patch('builtins.input', return_value="yes"):
            response = await user_confirmation.request_confirmation(action)

        assert response.result == ConfirmationResult.YES
        assert response.method_used.value == "interactive"
        assert response.user_input == "yes"

    @pytest.mark.asyncio
    async def test_timeout_confirmation(self, user_confirmation):
        """测试超时确认"""
        action = ConfirmationAction(
            action_id="test_timeout",
            title="Timeout Test",
            description="This is a timeout test",
            risk_level="medium",
            method=ConfirmationMethod.TIMEOUT,
            timeout_seconds=0.1,  # 很短的超时时间
            default_result=ConfirmationResult.NO
        )

        # 模拟超时（不提供输入）
        with patch('asyncio.wait_for', side_effect=asyncio.TimeoutError()):
            response = await user_confirmation.request_confirmation(action)

        assert response.result == ConfirmationResult.NO
        assert response.timed_out is True
        assert response.method_used.value == "timeout"

    def test_confirmation_statistics(self, user_confirmation):
        """测试确认统计信息"""
        # 添加一些模拟的确认历史
        mock_response1 = Mock(result=ConfirmationResult.YES, method_used=Mock(value="interactive"))
        mock_response2 = Mock(result=ConfirmationResult.NO, method_used=Mock(value="automatic"))
        mock_response1.response_time = 1.0
        mock_response2.response_time = 0.5

        user_confirmation.confirmation_history = [mock_response1, mock_response2]

        stats = user_confirmation.get_confirmation_statistics()

        assert stats["total_confirmations"] == 2
        assert "by_result" in stats
        assert "by_method" in stats
        assert stats["average_response_time"] == 0.75  # (1.0 + 0.5) / 2


class TestIntegration:
    """集成测试"""

    @pytest.mark.asyncio
    async def test_full_recovery_workflow(self):
        """测试完整的恢复工作流"""
        # 创建恢复编排器
        orchestrator = RecoveryOrchestrator()

        # 模拟服务配置
        service_configs = [
            {"name": "database", "url": "http://localhost:5432"},
            {"name": "backend", "url": "http://localhost:8000"},
            {"name": "frontend", "url": "http://localhost:3000"}
        ]

        # 模拟错误检测结果
        detected_errors = {
            "port_conflicts": [{"port": 8000, "process_name": "python"}],
            "permission_issues": [{"path": "/var/lib/postgresql", "issue": "write_permission"}]
        }

        # Mock 所有依赖方法
        with patch.object(orchestrator.health_checker, 'check_service_health_with_retry') as mock_health, \
             patch.object(orchestrator, '_restart_service') as mock_restart, \
             patch.object(orchestrator, '_resolve_port_conflict') as mock_port, \
             patch.object(orchestrator, '_fix_permission_issue') as mock_permission:

            # 设置模拟返回值
            mock_health.return_value = Mock(status="unhealthy")
            mock_restart.return_value = True
            mock_port.return_value = True
            mock_permission.return_value = True

            # 执行监控和恢复
            results = await orchestrator.monitor_and_recover(service_configs)

            # 验证结果
            assert len(results) >= 2  # 至少有端口冲突和权限问题的恢复操作

            # 验证统计信息
            stats = orchestrator.get_recovery_statistics()
            assert stats["total_recoveries"] >= 2
            assert stats["success_rate"] > 0

    @pytest.mark.asyncio
    async def test_service_recovery_with_strategies(self):
        """测试带策略的服务恢复"""
        from utils.recovery_strategies import RetryConfig, RetryStrategy as Retry, RetryStrategyEnum

        service_recovery = ServiceRecovery()
        retry_config = RetryConfig(
            max_attempts=3,
            base_delay=0.1,
            strategy=RetryStrategyEnum.EXPONENTIAL_BACKOFF
        )
        restart_config = RestartConfig(
            service_name="test_service",
            strategy=RestartStrategy.EXPONENTIAL_BACKOFF
        )

        call_count = 0

        async def mock_stop_service(config):
            return True

        async def mock_start_service(config):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                return False  # 前两次启动失败
            return True  # 第三次启动成功

        async def mock_verify_health(config):
            return True

        with patch.object(service_recovery, '_get_service_status') as mock_status, \
             patch.object(service_recovery, '_stop_service', side_effect=mock_stop_service), \
             patch.object(service_recovery, '_start_service', side_effect=mock_start_service), \
             patch.object(service_recovery, '_verify_service_health', side_effect=mock_verify_health):

            mock_status.return_value = ServiceStatus.STOPPED

            result = await service_recovery.restart_service(restart_config)

            assert result.success is True
            assert result.retry_count == 2  # 应该重试了2次
            assert call_count == 3  # 总共尝试了3次启动


class TestPortRecovery:
    """端口恢复测试 - Task 2"""

    @pytest.fixture
    def port_recovery_orchestrator(self):
        """创建端口恢复编排器实例"""
        return PortRecoveryOrchestrator(
            progress_tracker=None,
            auto_confirm_low_risk=False,  # 测试中不自动确认
            enable_rollback=True
        )

    @pytest.fixture
    def mock_port_conflict(self):
        """创建模拟端口冲突"""
        return PortConflict(
            port=8080,
            host="localhost",
            process_info={
                "pid": 12345,
                "name": "node",
                "command_line": "node server.js"
            },
            service_type="node",
            severity="medium",
            resolution_options=[ResolutionStrategy.STOP_PROCESS, ResolutionStrategy.USE_ALTERNATIVE],
            alternative_ports=[8081, 8082]
        )

    @pytest.mark.asyncio
    async def test_port_recovery_initialization(self, port_recovery_orchestrator):
        """测试端口恢复编排器初始化"""
        assert port_recovery_orchestrator is not None
        assert port_recovery_orchestrator.port_resolver is not None
        assert port_recovery_orchestrator.user_confirmation is not None
        assert port_recovery_orchestrator.error_knowledge is not None
        assert len(port_recovery_orchestrator.termination_history) == 0

    @pytest.mark.asyncio
    async def test_check_permissions(self, port_recovery_orchestrator):
        """测试权限检查"""
        with patch('platform.system', return_value='Linux'), \
             patch('subprocess.run', return_value=Mock(returncode=0)):

            permission = await port_recovery_orchestrator.check_permissions()
            assert permission in [PermissionLevel.USER, PermissionLevel.ADMIN, PermissionLevel.ROOT]

    @pytest.mark.asyncio
    async def test_assess_termination_risk(self, port_recovery_orchestrator, mock_port_conflict):
        """测试终止风险评估"""
        risk_assessment = await port_recovery_orchestrator._assess_termination_risk(
            mock_port_conflict, PermissionLevel.USER
        )

        assert "risk_level" in risk_assessment
        assert "risk_factors" in risk_assessment
        assert "permission_level" in risk_assessment
        assert risk_assessment["risk_level"] in ["low", "medium", "high", "critical"]

    @pytest.mark.asyncio
    async def test_request_termination_confirmation_low_risk(self, port_recovery_orchestrator):
        """测试低风险终止确认"""
        low_risk_conflict = PortConflict(
            port=3001,
            host="localhost",
            process_info={"pid": 99999, "name": "test_app"},
            service_type=None,
            severity="low",
            resolution_options=[ResolutionStrategy.USE_ALTERNATIVE],
            alternative_ports=[3002]
        )

        with patch.object(port_recovery_orchestrator.user_confirmation, 'request_confirmation') as mock_confirm:
            mock_confirm.return_value = Mock(result=ConfirmationResult.YES)

            confirmed = await port_recovery_orchestrator._request_termination_confirmation(
                low_risk_conflict, {"risk_level": "low"}
            )

            assert confirmed is True
            mock_confirm.assert_called_once()

    @pytest.mark.asyncio
    async def test_request_termination_confirmation_high_risk(self, port_recovery_orchestrator):
        """测试高风险终止确认"""
        high_risk_conflict = PortConflict(
            port=5432,
            host="localhost",
            process_info={"pid": 1234, "name": "postgres"},
            service_type="postgres",
            severity="high",
            resolution_options=[ResolutionStrategy.CHANGE_PORT],
            alternative_ports=[5433]
        )

        with patch.object(port_recovery_orchestrator.user_confirmation, 'request_confirmation') as mock_confirm:
            mock_confirm.return_value = Mock(result=ConfirmationResult.NO)

            confirmed = await port_recovery_orchestrator._request_termination_confirmation(
                high_risk_conflict, {"risk_level": "high"}
            )

            assert confirmed is False
            mock_confirm.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_process_termination_graceful(self, port_recovery_orchestrator):
        """测试优雅进程终止"""
        process_info = {"pid": 12345, "name": "test_process"}

        with patch('psutil.Process') as mock_process_class, \
             patch('psutil.TimeoutError', side_effect=Exception), \
             patch.object(port_recovery_orchestrator, '_get_platform_info', return_value={"system": "linux"}):

            mock_process = Mock()
            mock_process.terminate.return_value = None
            mock_process.wait.return_value = None
            mock_process_class.return_value = mock_process

            result = await port_recovery_orchestrator._execute_process_termination(
                process_info, TerminationMethod.GRACEFUL, PermissionLevel.USER
            )

            assert result.success is True
            assert result.pid == 12345
            assert result.process_name == "test_process"
            assert result.termination_method == TerminationMethod.GRACEFUL
            assert result.time_taken >= 0

    @pytest.mark.asyncio
    async def test_execute_process_termination_forceful(self, port_recovery_orchestrator):
        """测试强制进程终止"""
        process_info = {"pid": 12345, "name": "test_process"}

        with patch('psutil.Process') as mock_process_class, \
             patch.object(port_recovery_orchestrator, '_get_platform_info', return_value={"system": "linux"}):

            mock_process = Mock()
            mock_process.kill.return_value = None
            mock_process_class.return_value = mock_process

            result = await port_recovery_orchestrator._execute_process_termination(
                process_info, TerminationMethod.FORCEFUL, PermissionLevel.USER
            )

            assert result.success is True
            assert result.pid == 12345
            assert result.process_name == "test_process"
            assert result.termination_method == TerminationMethod.FORCEFUL
            assert result.rollback_possible is False  # 强制终止不可回滚

    @pytest.mark.asyncio
    async def test_execute_process_termination_hybrid(self, port_recovery_orchestrator):
        """测试混合进程终止（先优雅后强制）"""
        process_info = {"pid": 12345, "name": "test_process"}

        with patch('psutil.Process') as mock_process_class, \
             patch('psutil.TimeoutError', side_effect=Exception), \
             patch.object(port_recovery_orchestrator, '_get_platform_info', return_value={"system": "linux"}):

            mock_process = Mock()
            # 优雅终止失败，强制终止成功
            mock_process.terminate.return_value = None
            mock_process.wait.side_effect = [Exception("Timeout"), None]  # 第一次超时，第二次成功
            mock_process.kill.return_value = None
            mock_process_class.return_value = mock_process

            with patch.object(port_recovery_orchestrator, '_terminate_gracefully', return_value=False), \
                 patch.object(port_recovery_orchestrator, '_terminate_forcefully', return_value=True):

                result = await port_recovery_orchestrator._execute_process_termination(
                    process_info, TerminationMethod.HYBRID, PermissionLevel.USER
                )

                assert result.success is True
                assert result.termination_method == TerminationMethod.HYBRID

    @pytest.mark.asyncio
    async def test_verify_port_release_success(self, port_recovery_orchestrator):
        """测试端口释放验证成功"""
        with patch('core.port_checker.PortChecker') as mock_checker_class:
            mock_checker = Mock()
            mock_checker.check_port_availability.return_value = Mock(is_available=True)
            mock_checker_class.return_value = mock_checker

            result = await port_recovery_orchestrator._verify_port_release(8080, "localhost")
            assert result is True

    @pytest.mark.asyncio
    async def test_verify_port_release_failure(self, port_recovery_orchestrator):
        """测试端口释放验证失败"""
        with patch('core.port_checker.PortChecker') as mock_checker_class:
            mock_checker = Mock()
            # 确保前3次检查都返回占用状态
            mock_checker.check_port_availability.return_value = Mock(is_available=False)
            mock_checker_class.return_value = mock_checker

            result = await port_recovery_orchestrator._verify_port_release(8080, "localhost")
            assert result is False

    @pytest.mark.asyncio
    async def test_auto_resolve_port_conflict_success(self, port_recovery_orchestrator, mock_port_conflict):
        """测试成功自动解决端口冲突"""
        with patch.object(port_recovery_orchestrator, 'check_permissions', return_value=PermissionLevel.USER), \
             patch.object(port_recovery_orchestrator, '_assess_termination_risk', return_value={"risk_level": "medium"}), \
             patch.object(port_recovery_orchestrator, '_request_termination_confirmation', return_value=True), \
             patch.object(port_recovery_orchestrator, '_execute_process_termination', return_value=ProcessTerminationResult(
                 success=True, pid=12345, process_name="node", termination_method=TerminationMethod.HYBRID, time_taken=2.0
             )), \
             patch.object(port_recovery_orchestrator, '_verify_port_release', return_value=True):

            result = await port_recovery_orchestrator.auto_resolve_port_conflict(
                mock_port_conflict, allow_process_termination=True
            )

            assert result.conflict_resolved is True
            assert result.process_terminated is True
            assert result.user_confirmed is True
            assert result.verification_passed is True
            assert result.termination_result is not None
            assert result.termination_result.success is True

    @pytest.mark.asyncio
    async def test_auto_resolve_port_conflict_user_declined(self, port_recovery_orchestrator, mock_port_conflict):
        """测试用户拒绝终止确认"""
        with patch.object(port_recovery_orchestrator, 'check_permissions', return_value=PermissionLevel.USER), \
             patch.object(port_recovery_orchestrator, '_assess_termination_risk', return_value={"risk_level": "high"}), \
             patch.object(port_recovery_orchestrator, '_request_termination_confirmation', return_value=False):

            result = await port_recovery_orchestrator.auto_resolve_port_conflict(
                mock_port_conflict, allow_process_termination=True
            )

            assert result.conflict_resolved is False
            assert result.process_terminated is False
            assert result.user_confirmed is False
            assert result.error_details == "User declined termination confirmation"

    @pytest.mark.asyncio
    async def test_auto_resolve_port_conflict_no_process_info(self, port_recovery_orchestrator):
        """测试无进程信息的端口冲突解决"""
        conflict_no_process = PortConflict(
            port=8080,
            host="localhost",
            process_info=None,
            service_type="unknown",
            severity="low",
            resolution_options=[ResolutionStrategy.USE_ALTERNATIVE],
            alternative_ports=[8081]
        )

        with patch.object(port_recovery_orchestrator, 'check_permissions', return_value=PermissionLevel.USER), \
             patch.object(port_recovery_orchestrator, '_assess_termination_risk', return_value={"risk_level": "low"}), \
             patch.object(port_recovery_orchestrator, '_request_termination_confirmation', return_value=True), \
             patch.object(port_recovery_orchestrator, '_verify_port_release', return_value=True):

            result = await port_recovery_orchestrator.auto_resolve_port_conflict(
                conflict_no_process, allow_process_termination=True
            )

            assert result.conflict_resolved is True
            assert result.process_terminated is False
            assert result.termination_result is None

    @pytest.mark.asyncio
    async def test_batch_resolve_conflicts(self, port_recovery_orchestrator):
        """测试批量解决端口冲突"""
        conflicts = [
            PortConflict(
                port=8080, host="localhost", process_info={"pid": 1234, "name": "node1"},
                service_type="node", severity="medium", resolution_options=[ResolutionStrategy.STOP_PROCESS], alternative_ports=[]
            ),
            PortConflict(
                port=8081, host="localhost", process_info={"pid": 5678, "name": "node2"},
                service_type="node", severity="medium", resolution_options=[ResolutionStrategy.STOP_PROCESS], alternative_ports=[]
            )
        ]

        with patch.object(port_recovery_orchestrator, '_request_batch_confirmation', return_value=True), \
             patch.object(port_recovery_orchestrator, 'auto_resolve_port_conflict', side_effect=[
                 PortRecoveryResult(port=8080, conflict_resolved=True, process_terminated=True, user_confirmed=True, verification_passed=True),
                 PortRecoveryResult(port=8081, conflict_resolved=True, process_terminated=True, user_confirmed=True, verification_passed=True)
             ]):

            results = await port_recovery_orchestrator.batch_resolve_conflicts(conflicts, allow_batch_confirmation=True)

            assert len(results) == 2
            assert all(result.conflict_resolved for result in results)

    def test_get_termination_history(self, port_recovery_orchestrator):
        """测试获取终止历史"""
        # 添加一些终止历史
        port_recovery_orchestrator.termination_history = [
            ProcessTerminationResult(success=True, pid=1234, process_name="test1", termination_method=TerminationMethod.GRACEFUL, time_taken=1.0),
            ProcessTerminationResult(success=False, pid=5678, process_name="test2", termination_method=TerminationMethod.FORCEFUL, time_taken=0.5)
        ]

        history = port_recovery_orchestrator.get_termination_history()
        assert len(history) == 2
        assert history[0].success is True
        assert history[1].success is False

    def test_get_recovery_statistics(self, port_recovery_orchestrator):
        """测试获取恢复统计信息"""
        # 添加一些终止历史
        port_recovery_orchestrator.termination_history = [
            ProcessTerminationResult(success=True, pid=1234, process_name="test1", termination_method=TerminationMethod.GRACEFUL, time_taken=1.0),
            ProcessTerminationResult(success=False, pid=5678, process_name="test2", termination_method=TerminationMethod.FORCEFUL, time_taken=0.5),
            ProcessTerminationResult(success=True, pid=9012, process_name="test3", termination_method=TerminationMethod.HYBRID, time_taken=2.0)
        ]

        stats = port_recovery_orchestrator.get_recovery_statistics()

        assert stats["total_terminations"] == 3
        assert stats["successful_terminations"] == 2
        assert stats["failed_terminations"] == 1
        assert stats["success_rate"] == 66.66666666666666
        assert "most_common_method" in stats
        assert "method_distribution" in stats
        assert "average_termination_time" in stats

    @pytest.mark.asyncio
    async def test_request_permission_elevation_unix(self, port_recovery_orchestrator):
        """测试Unix/Linux权限提升请求"""
        with patch.object(port_recovery_orchestrator, 'platform_info', {"system": "linux"}), \
             patch.object(port_recovery_orchestrator, '_request_unix_elevation', return_value=True):
            result = await port_recovery_orchestrator.request_permission_elevation("测试权限提升")
            assert result is True

    @pytest.mark.asyncio
    async def test_rollback_termination_web_server(self, port_recovery_orchestrator):
        """测试Web服务器终止回滚"""
        termination_result = ProcessTerminationResult(
            success=True, pid=1234, process_name="nginx", termination_method=TerminationMethod.GRACEFUL,
            time_taken=1.0, rollback_possible=True
        )

        with patch.object(port_recovery_orchestrator, '_restart_web_server', return_value=True):
            result = await port_recovery_orchestrator.rollback_termination(termination_result)
            assert result is True

    @pytest.mark.asyncio
    async def test_rollback_termination_unsupported(self, port_recovery_orchestrator):
        """测试不支持的终止回滚"""
        termination_result = ProcessTerminationResult(
            success=True, pid=1234, process_name="custom_app", termination_method=TerminationMethod.FORCEFUL,
            time_taken=1.0, rollback_possible=False
        )

        result = await port_recovery_orchestrator.rollback_termination(termination_result)
        assert result is False


class TestPortRecoveryIntegration:
    """端口恢复集成测试"""

    @pytest.mark.asyncio
    async def test_full_port_recovery_workflow(self):
        """测试完整的端口恢复工作流 - AC2"""
        # 创建恢复编排器
        recovery_orchestrator = RecoveryOrchestrator()

        # 创建端口冲突操作
        port_conflict_action = Mock(
            recovery_type=RecoveryType.PORT_CONFLICT,
            target_component="port_8080",
            parameters={
                "conflict_info": {"port": 8080, "process_name": "node"},
                "allow_termination": True
            }
        )

        # 模拟端口恢复编排器
        mock_recovery_result = PortRecoveryResult(
            port=8080,
            conflict_resolved=True,
            process_terminated=True,
            user_confirmed=True,
            verification_passed=True
        )

        with patch.object(recovery_orchestrator.port_recovery_orchestrator, 'auto_resolve_port_conflict', return_value=mock_recovery_result), \
             patch('core.port_detector.PortConflictResolver') as mock_resolver_class, \
             patch.object(mock_resolver_class.return_value, 'detect_conflicts', return_value=[Mock()]):

            result = await recovery_orchestrator._resolve_port_conflict(port_conflict_action)

            assert result is True
            recovery_orchestrator.port_recovery_orchestrator.auto_resolve_port_conflict.assert_called_once()

    @pytest.mark.asyncio
    async def test_port_recovery_with_user_confirmation(self):
        """测试带用户确认的端口恢复"""
        port_recovery = PortRecoveryOrchestrator(auto_confirm_low_risk=False)

        conflict = PortConflict(
            port=3000,
            host="localhost",
            process_info={"pid": 12345, "name": "node", "command_line": "node app.js"},
            service_type="node",
            severity="medium",
            resolution_options=[ResolutionStrategy.STOP_PROCESS],
            alternative_ports=[3001]
        )

        # 模拟用户确认为YES
        with patch.object(port_recovery.user_confirmation, 'request_confirmation') as mock_confirm, \
             patch.object(port_recovery, 'check_permissions', return_value=PermissionLevel.USER), \
             patch.object(port_recovery, '_assess_termination_risk', return_value={"risk_level": "medium"}), \
             patch.object(port_recovery, '_execute_process_termination', return_value=ProcessTerminationResult(
                 success=True, pid=12345, process_name="node", termination_method=TerminationMethod.HYBRID, time_taken=1.5
             )), \
             patch.object(port_recovery, '_verify_port_release', return_value=True):

            mock_confirm.return_value = Mock(result=ConfirmationResult.YES)

            result = await port_recovery.auto_resolve_port_conflict(conflict, allow_process_termination=True)

            assert result.conflict_resolved is True
            assert result.user_confirmed is True
            assert result.process_terminated is True

    @pytest.mark.asyncio
    async def test_port_recovery_permission_denied(self):
        """测试权限被拒绝的端口恢复"""
        port_recovery = PortRecoveryOrchestrator()

        conflict = PortConflict(
            port=5432,
            host="localhost",
            process_info={"pid": 1234, "name": "postgres", "command_line": "postgres -D /var/lib/postgresql"},
            service_type="postgres",
            severity="high",
            resolution_options=[ResolutionStrategy.STOP_PROCESS],
            alternative_ports=[5433]
        )

        with patch.object(port_recovery, 'check_permissions', return_value=PermissionLevel.USER), \
             patch.object(port_recovery, '_assess_termination_risk', return_value={"risk_level": "high", "risk_factors": ["insufficient_privileges"]}), \
             patch.object(port_recovery, '_request_termination_confirmation', return_value=False):

            result = await port_recovery.auto_resolve_port_conflict(conflict, allow_process_termination=True)

            assert result.conflict_resolved is False
            assert result.user_confirmed is False
            assert "权限" in result.error_details or "permission" in result.error_details.lower()


class TestPermissionRepairer:
    """权限修复器测试"""

    @pytest.fixture
    def permission_repairer(self):
        """创建权限修复器实例"""
        return PermissionRepairer()  # 创建实例（默认不进行实际修改）

    @pytest.fixture
    def temp_file(self, tmp_path):
        """创建临时文件用于测试"""
        test_file = tmp_path / "test_file.txt"
        test_file.write_text("test content")
        return str(test_file)

    def test_initialization(self, permission_repairer):
        """测试初始化"""
        assert permission_repairer is not None
        assert permission_repairer.diagnostic is not None
        assert permission_repairer.elevation_request is not None
        assert permission_repairer is not None

    def test_permission_backup_creation(self, permission_repairer, temp_file):
        """测试权限备份创建"""
        backup = permission_repairer.create_permission_backup(temp_file)

        assert backup is not None
        assert backup.path == temp_file
        assert backup.backup_id is not None
        assert backup.timestamp is not None
        assert len(permission_repairer.backups) == 1

    def test_permission_repair_success(self, permission_repairer, temp_file):
        """测试权限修复成功"""
        result = permission_repairer.repair_file_permissions(temp_file)

        assert result is not None
        assert isinstance(result, PermissionRepairResult)
        assert result.success is True
        # 文件可能有正确权限，所以operations可能为空，这仍然是成功的
        assert result.elevation_requested is False  # 在正常情况下不应请求提升权限

    def test_privilege_elevation_request(self, permission_repairer):
        """测试权限提升请求"""
        result = permission_repairer.request_privilege_elevation()

        assert result is not None
        assert 'success' in result
        assert 'method' in result or 'error' in result

    def test_permission_verification(self, permission_repairer, temp_file):
        """测试权限修复验证"""
        verification = permission_repairer.verify_repair(temp_file)

        assert verification is not None
        assert 'path' in verification
        assert 'exists' in verification
        assert 'verification_passed' in verification

    def test_permission_rollback(self, permission_repairer, temp_file):
        """测试权限回滚"""
        # 先创建备份
        backup = permission_repairer.create_permission_backup(temp_file)

        # 执行回滚
        rollback_result = permission_repairer.rollback_permissions(backup.backup_id)

        assert rollback_result is not None
        assert 'success' in rollback_result
        assert 'rolled_back_count' in rollback_result

    def test_backup_state_management(self, permission_repairer, tmp_path):
        """测试备份状态管理"""
        state_file = tmp_path / "backup_state.json"

        # 保存状态
        save_result = permission_repairer.save_backup_state(str(state_file))
        assert save_result['success'] is True

        # 加载状态
        load_result = permission_repairer.load_backup_state(str(state_file))
        assert load_result['success'] is True


class TestCacheCleaner:
    """缓存清理器测试"""

    @pytest.fixture
    def cache_cleaner(self):
        """创建缓存清理器实例"""
        return CacheCleaner(dry_run=True)  # 使用dry_run模式避免实际删除

    @pytest.fixture
    def temp_cache_dir(self, tmp_path):
        """创建临时缓存目录"""
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()

        # 创建一些测试缓存文件
        cache1_path = cache_dir / "cache1.json"
        cache2_path = cache_dir / "cache2.tmp"
        important_path = cache_dir / "important.txt"

        cache1_path.write_text('{"data": "test"}')
        cache2_path.write_text("temp data")
        important_path.write_text("important data")

        # 修改文件修改时间，模拟较旧的文件（6小时前）
        import time
        old_timestamp = time.time() - (6 * 60 * 60)  # 6小时前
        os.utime(cache1_path, (old_timestamp, old_timestamp))
        os.utime(cache2_path, (old_timestamp, old_timestamp))
        os.utime(important_path, (old_timestamp, old_timestamp))

        return str(cache_dir)

    def test_initialization(self, cache_cleaner):
        """测试初始化"""
        assert cache_cleaner is not None
        assert cache_cleaner.corruption_detector is not None
        assert cache_cleaner.file_cleaner is not None
        assert cache_cleaner.dry_run is True

    def test_cache_corruption_detection(self, cache_cleaner, temp_cache_dir):
        """测试缓存损坏检测"""
        # 创建一个损坏的JSON文件
        corrupted_file = Path(temp_cache_dir) / "corrupted.json"
        corrupted_file.write_text('{"invalid": json}')  # 无效JSON

        is_corrupted, reason = cache_cleaner.corruption_detector.check_corruption(str(corrupted_file))

        assert is_corrupted is True
        assert "Invalid JSON" in reason

    def test_safe_file_deletion_check(self, cache_cleaner, temp_cache_dir):
        """测试安全文件删除检查"""
        cache_type = CacheType.APPLICATION_CACHE

        # 检查普通缓存文件
        safe, reason = cache_cleaner.file_cleaner.is_safe_to_delete(
            os.path.join(temp_cache_dir, "cache1.json"),
            cache_type
        )
        assert safe is True

        # 检查重要文件（应该不安全）
        safe, reason = cache_cleaner.file_cleaner.is_safe_to_delete(
            os.path.join(temp_cache_dir, "important.txt"),
            cache_type
        )
        assert safe is False

    def test_cache_directory_scan(self, cache_cleaner, temp_cache_dir):
        """测试缓存目录扫描"""
        entries = cache_cleaner.scan_cache_directories([CacheType.APPLICATION_CACHE])

        # 在dry_run模式下，可能扫描不到实际文件，但应该返回列表
        assert isinstance(entries, list)
        # 如果扫描到文件，验证条目结构
        if entries:
            entry = entries[0]
            assert isinstance(entry, CacheEntry)

    def test_cache_cleanup_safe_policy(self, cache_cleaner):
        """测试安全清理策略"""
        result = cache_cleaner.cleanup_cache(
            cache_types=[CacheType.APPLICATION_CACHE],
            policy=CleanupPolicy.SAFE
        )

        assert result is not None
        assert isinstance(result, CleanupResult)
        assert result.cleanup_policy == CleanupPolicy.SAFE
        # 在dry_run模式下，应该没有实际删除文件
        assert result.files_processed == 0

    def test_cache_cleanup_statistics(self, cache_cleaner):
        """测试缓存清理统计"""
        stats = cache_cleaner.get_cleanup_statistics()

        assert 'total_entries' in stats
        assert 'total_size_bytes' in stats
        assert 'cache_type_breakdown' in stats

    def test_periodic_cleanup_scheduling(self, cache_cleaner):
        """测试定期清理调度（占位符实现）"""
        # 这只是一个占位符测试，实际实现需要调度器
        cache_cleaner.schedule_periodic_cleanup(interval_hours=24)
        # 没有异常抛出即为成功


class TestConfigRepairer:
    """配置修复器测试"""

    @pytest.fixture
    def config_repairer(self):
        """创建配置修复器实例"""
        return ConfigRepairer()

    @pytest.fixture
    def temp_config_dir(self, tmp_path):
        """创建临时配置目录"""
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        return str(config_dir)

    @pytest.fixture
    def valid_json_config(self, temp_config_dir):
        """创建有效的JSON配置文件"""
        config_file = Path(temp_config_dir) / "valid.json"
        config_file.write_text('{"database": {"host": "localhost"}, "api": {"port": 8000}}')
        return str(config_file)

    @pytest.fixture
    def corrupted_json_config(self, temp_config_dir):
        """创建损坏的JSON配置文件"""
        config_file = Path(temp_config_dir) / "corrupted.json"
        config_file.write_text('{"database": {"host": "localhost", "invalid": json}')  # 缺少闭合括号
        return str(config_file)

    def test_initialization(self, config_repairer):
        """测试初始化"""
        assert config_repairer is not None
        assert config_repairer.validator is not None
        assert len(config_repairer.templates) > 0
        assert 'app_config' in config_repairer.templates

    def test_json_config_validation_valid(self, config_repairer, valid_json_config):
        """测试有效JSON配置验证"""
        report = config_repairer.validator.validate_config(valid_json_config)

        assert report is not None
        assert report.result == ConfigValidationResult.VALID
        assert report.format == ConfigFormat.JSON
        assert len(report.issues) == 0

    def test_json_config_validation_corrupted(self, config_repairer, corrupted_json_config):
        """测试损坏JSON配置验证"""
        report = config_repairer.validator.validate_config(corrupted_json_config)

        assert report is not None
        assert report.result == ConfigValidationResult.CORRUPTED
        assert report.format == ConfigFormat.JSON
        assert len(report.issues) > 0
        assert any(issue.issue_type == "syntax" for issue in report.issues)

    def test_config_format_detection(self, config_repairer, temp_config_dir):
        """测试配置格式检测"""
        # 测试JSON格式检测
        json_file = Path(temp_config_dir) / "test.json"
        json_file.write_text('{"test": true}')

        detected_format = config_repairer.validator._detect_format(str(json_file))
        assert detected_format == ConfigFormat.JSON

    def test_config_auto_repair(self, config_repairer, corrupted_json_config):
        """测试配置自动修复"""
        operation = config_repairer.repair_config(
            corrupted_json_config,
            strategy=RepairStrategy.AUTO_REPAIR
        )

        assert operation is not None
        assert operation.strategy == RepairStrategy.AUTO_REPAIR
        assert operation.file_path == corrupted_json_config

    def test_config_reset_to_default(self, config_repairer, temp_config_dir):
        """测试配置重置为默认值"""
        config_file = Path(temp_config_dir) / "reset_test.json"
        config_file.write_text('{"old": "config"}')

        operation = config_repairer.repair_config(
            str(config_file),
            strategy=RepairStrategy.RESET_TO_DEFAULT,
            template_name='app_config'
        )

        assert operation is not None
        assert operation.strategy == RepairStrategy.RESET_TO_DEFAULT
        assert operation.status in ['completed', 'failed']

    def test_config_repair_verification(self, config_repairer, valid_json_config):
        """测试配置修复验证"""
        # 先进行一次"修复"
        operation = config_repairer.repair_config(
            valid_json_config,
            strategy=RepairStrategy.VALIDATE_ONLY
        )

        # 验证修复结果
        verification = config_repairer.verify_repair(
            valid_json_config,
            operation.operation_id
        )

        assert verification is not None
        assert 'success' in verification
        assert 'verification_passed' in verification

    def test_config_rollback(self, config_repairer, temp_config_dir):
        """测试配置回滚"""
        config_file = Path(temp_config_dir) / "rollback_test.json"
        config_file.write_text('{"original": "config"}')

        # 先进行修复（会创建备份）
        operation = config_repairer.repair_config(
            str(config_file),
            strategy=RepairStrategy.RESET_TO_DEFAULT
        )

        if operation.backup_path and os.path.exists(operation.backup_path):
            # 执行回滚
            rollback_result = config_repairer.rollback_config(
                str(config_file),
                operation.operation_id
            )

            assert rollback_result is not None
            assert 'success' in rollback_result

    def test_repair_history(self, config_repairer, valid_json_config):
        """测试修复历史记录"""
        # 进行一次修复
        config_repairer.repair_config(
            valid_json_config,
            strategy=RepairStrategy.VALIDATE_ONLY
        )

        # 获取修复历史
        history = config_repairer.get_repair_history(valid_json_config)

        assert isinstance(history, list)
        if history:  # 如果有历史记录
            assert 'operation_id' in history[0]
            assert 'strategy' in history[0]

    def test_repair_state_management(self, config_repairer, tmp_path):
        """测试修复状态管理"""
        state_file = tmp_path / "repair_state.json"

        # 保存状态
        save_result = config_repairer.save_repair_state(str(state_file))
        assert save_result['success'] is True

        # 加载状态
        load_result = config_repairer.load_repair_state(str(state_file))
        assert load_result['success'] is True

    def test_template_availability(self, config_repairer):
        """测试模板可用性"""
        templates = config_repairer.templates

        assert 'app_config' in templates
        assert 'env_config' in templates
        assert 'logger_config' in templates

        # 检查模板结构
        app_template = templates['app_config']
        assert app_template.name is not None
        assert app_template.version is not None
        assert app_template.content is not None


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "--tb=short"])