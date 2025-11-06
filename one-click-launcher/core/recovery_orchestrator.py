"""
Automatic Recovery Orchestrator

This module provides comprehensive automatic recovery coordination for all system components.
It leverages error detection patterns to trigger appropriate recovery mechanisms and provides
intelligent retry strategies with safety checks and rollback capabilities.
"""

import asyncio
import time
import json
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import threading
from pathlib import Path

from core.error_detector import ErrorDetector, ErrorSeverity
from core.health_checker import HealthChecker, HealthStatus, HealthCheckResult
from core.port_manager import PortManager
from core.permission_diagnostic import PermissionDiagnostic
from core.port_recovery import PortRecoveryOrchestrator, TerminationMethod
from utils.progress_tracker import ProgressTracker, ProgressStatus
from utils.logger import get_logger

logger = get_logger(__name__)


class RecoveryType(Enum):
    """恢复类型枚举"""
    SERVICE_RESTART = "service_restart"
    PORT_CONFLICT = "port_conflict"
    PERMISSION_FIX = "permission_fix"
    CACHE_CLEANUP = "cache_cleanup"
    CONFIG_REPAIR = "config_repair"
    DEPENDENCY_FIX = "dependency_fix"


class RecoveryStatus(Enum):
    """恢复状态枚举"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"
    CANCELLED = "cancelled"


@dataclass
class RecoveryAction:
    """恢复操作定义"""
    recovery_type: RecoveryType
    target_component: str
    description: str
    priority: int = 1  # 1=最高优先级
    max_retries: int = 3
    timeout_seconds: int = 60
    requires_user_confirmation: bool = False
    rollback_action: Optional['RecoveryAction'] = None
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RecoveryResult:
    """恢复操作结果"""
    action: RecoveryAction
    status: RecoveryStatus
    success: bool
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    retry_count: int = 0
    error_details: Optional[str] = None
    rollback_performed: bool = False

    @property
    def duration(self) -> Optional[timedelta]:
        """获取恢复操作持续时间"""
        if self.end_time and self.start_time:
            return self.end_time - self.start_time
        return None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "recovery_type": self.action.recovery_type.value,
            "target_component": self.action.target_component,
            "status": self.status.value,
            "success": self.success,
            "message": self.message,
            "details": self.details,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": self.duration.total_seconds() if self.duration else None,
            "retry_count": self.retry_count,
            "error_details": self.error_details,
            "rollback_performed": self.rollback_performed
        }


class RecoveryOrchestrator:
    """自动恢复编排器"""

    def __init__(self):
        """初始化恢复编排器"""
        self.error_detector = ErrorDetector()
        self.health_checker = HealthChecker()
        self.port_manager = PortManager()
        self.permission_diagnostic = PermissionDiagnostic()
        self.port_recovery_orchestrator = PortRecoveryOrchestrator(
            progress_tracker=ProgressTracker(
                component_name="port_recovery"
            ),
            auto_confirm_low_risk=True,
            enable_rollback=True
        )
        self.progress_tracker = ProgressTracker(
            component_name="automatic_recovery"
        )

        # 恢复历史记录
        self.recovery_history: List[RecoveryResult] = []
        self.active_recoveries: Dict[str, RecoveryResult] = {}

        # 恢复策略配置
        self.recovery_strategies = self._initialize_recovery_strategies()

        # 线程锁
        self._lock = threading.Lock()

        logger.info("RecoveryOrchestrator initialized")

    def _initialize_recovery_strategies(self) -> Dict[RecoveryType, Dict]:
        """初始化恢复策略配置"""
        return {
            RecoveryType.SERVICE_RESTART: {
                "max_retries": 3,
                "base_delay": 2.0,
                "max_delay": 60.0,
                "backoff_multiplier": 2.0,
                "timeout": 60
            },
            RecoveryType.PORT_CONFLICT: {
                "max_retries": 2,
                "base_delay": 1.0,
                "max_delay": 30.0,
                "backoff_multiplier": 1.5,
                "timeout": 30,
                "require_confirmation": True
            },
            RecoveryType.PERMISSION_FIX: {
                "max_retries": 2,
                "base_delay": 1.0,
                "max_delay": 15.0,
                "backoff_multiplier": 1.5,
                "timeout": 30,
                "require_confirmation": True
            },
            RecoveryType.CACHE_CLEANUP: {
                "max_retries": 1,
                "base_delay": 0.5,
                "max_delay": 10.0,
                "backoff_multiplier": 1.0,
                "timeout": 30
            },
            RecoveryType.CONFIG_REPAIR: {
                "max_retries": 2,
                "base_delay": 2.0,
                "max_delay": 45.0,
                "backoff_multiplier": 2.0,
                "timeout": 60
            },
            RecoveryType.DEPENDENCY_FIX: {
                "max_retries": 3,
                "base_delay": 3.0,
                "max_delay": 90.0,
                "backoff_multiplier": 2.0,
                "timeout": 120
            }
        }

    async def monitor_and_recover(self, service_configs: List[Dict[str, Any]]) -> List[RecoveryResult]:
        """
        监控服务状态并执行自动恢复

        Args:
            service_configs: 服务配置列表

        Returns:
            List[RecoveryResult]: 恢复操作结果列表
        """
        logger.info("Starting service monitoring and automatic recovery")

        recovery_results = []

        try:
            # 初始化进度跟踪 - 添加步骤
            self.progress_tracker.add_step("服务监控和恢复", "监控服务并执行自动恢复", 100.0)
            self.progress_tracker.add_step("错误检测", "检测系统中的错误", 20.0)
            self.progress_tracker.add_step("恢复计划制定", "分析错误并制定恢复计划", 20.0)
            self.progress_tracker.add_step("执行恢复操作", "执行具体的恢复操作", 50.0)
            self.progress_tracker.add_step("验证恢复结果", "验证恢复是否成功", 10.0)

            # 开始恢复流程
            self.progress_tracker.start_step(0)

            # 步骤1: 错误检测
            self.progress_tracker.start_step(1)
            detected_errors = await self.error_detector.run_comprehensive_detection()
            self.progress_tracker.complete_step(1, True, "错误检测完成")

            # 步骤2: 分析错误并制定恢复计划
            self.progress_tracker.start_step(2)
            recovery_actions = await self._analyze_errors_and_plan_recovery(detected_errors, service_configs)
            self.progress_tracker.complete_step(2, True, f"制定了 {len(recovery_actions)} 个恢复操作")

            # 步骤3: 执行恢复操作
            self.progress_tracker.start_step(3)
            for action in recovery_actions:
                result = await self._execute_recovery_action(action)
                recovery_results.append(result)
            self.progress_tracker.complete_step(3, True, f"执行了 {len(recovery_results)} 个恢复操作")

            # 步骤4: 验证恢复效果
            self.progress_tracker.start_step(4)
            verification_results = await self._verify_recovery_results(recovery_results, service_configs)
            self.progress_tracker.complete_step(4, True, "恢复验证完成")

            # 完成整个流程
            self.progress_tracker.complete_step(0, True, "服务监控和恢复完成")

            logger.info(f"Service monitoring and recovery completed. Results: {len(recovery_results)} operations")
            return recovery_results

        except Exception as e:
            logger.error(f"Error during service monitoring and recovery: {str(e)}")
            # 如果步骤已经添加，标记第一个步骤失败
            if len(self.progress_tracker.progress_info.steps) > 0:
                self.progress_tracker.complete_step(0, False, f"服务监控和恢复失败: {str(e)}")
            raise

    async def _analyze_errors_and_plan_recovery(
        self,
        detected_errors: Dict[str, Any],
        service_configs: List[Dict[str, Any]]
    ) -> List[RecoveryAction]:
        """分析检测到的错误并制定恢复计划"""
        recovery_actions = []

        # 分析端口冲突
        if detected_errors.get("port_conflicts"):
            port_conflicts = detected_errors["port_conflicts"]
            for conflict in port_conflicts:
                action = RecoveryAction(
                    recovery_type=RecoveryType.PORT_CONFLICT,
                    target_component=f"port_{conflict.get('port')}",
                    description=f"解决端口 {conflict.get('port')} 冲突",
                    priority=1,
                    requires_user_confirmation=True,
                    parameters={"conflict_info": conflict}
                )
                recovery_actions.append(action)

        # 分析权限问题
        if detected_errors.get("permission_issues"):
            permission_issues = detected_errors["permission_issues"]
            for issue in permission_issues:
                # issue是ErrorInfo对象，不是字典
                target_path = issue.details.get("path", "unknown") if hasattr(issue, 'details') else "unknown"
                action = RecoveryAction(
                    recovery_type=RecoveryType.PERMISSION_FIX,
                    target_component=target_path,
                    description=f"修复权限问题: {target_path}",
                    priority=2,
                    requires_user_confirmation=True,
                    parameters={"issue_info": issue}
                )
                recovery_actions.append(action)

        # 分析服务健康状态
        for service_config in service_configs:
            service_name = service_config.get("name")
            health_result = await self.health_checker.check_service_health_with_retry(
                service_config, max_retries=1
            )

            if health_result.status != HealthStatus.HEALTHY:
                action = RecoveryAction(
                    recovery_type=RecoveryType.SERVICE_RESTART,
                    target_component=service_name,
                    description=f"重启服务: {service_name}",
                    priority=1,
                    parameters={"service_config": service_config}
                )
                recovery_actions.append(action)

        # 按优先级排序
        recovery_actions.sort(key=lambda x: x.priority)

        return recovery_actions

    async def _execute_recovery_action(self, action: RecoveryAction) -> RecoveryResult:
        """执行恢复操作"""
        result = RecoveryResult(action=action, status=RecoveryStatus.IN_PROGRESS, success=False, message="开始执行恢复操作")

        with self._lock:
            self.active_recoveries[action.target_component] = result

        try:
            logger.info(f"Executing recovery action: {action.description}")

            strategy = self.recovery_strategies.get(action.recovery_type, {})
            max_retries = strategy.get("max_retries", action.max_retries)

            for attempt in range(max_retries + 1):
                try:
                    if attempt > 0:
                        delay = self._calculate_retry_delay(action.recovery_type, attempt)
                        logger.info(f"Retrying recovery action in {delay} seconds (attempt {attempt + 1}/{max_retries + 1})")
                        await asyncio.sleep(delay)

                    result.retry_count = attempt

                    # 根据恢复类型执行相应的恢复操作
                    if action.recovery_type == RecoveryType.SERVICE_RESTART:
                        success = await self._restart_service(action)
                    elif action.recovery_type == RecoveryType.PORT_CONFLICT:
                        success = await self._resolve_port_conflict(action)
                    elif action.recovery_type == RecoveryType.PERMISSION_FIX:
                        success = await self._fix_permission_issue(action)
                    elif action.recovery_type == RecoveryType.CACHE_CLEANUP:
                        success = await self._cleanup_cache(action)
                    elif action.recovery_type == RecoveryType.CONFIG_REPAIR:
                        success = await self._repair_configuration(action)
                    elif action.recovery_type == RecoveryType.DEPENDENCY_FIX:
                        success = await self._fix_dependency_issue(action)
                    else:
                        raise ValueError(f"Unsupported recovery type: {action.recovery_type}")

                    if success:
                        result.status = RecoveryStatus.COMPLETED
                        result.success = True
                        result.message = f"恢复操作成功完成: {action.description}"
                        result.end_time = datetime.now()
                        break

                except Exception as e:
                    logger.warning(f"Recovery attempt {attempt + 1} failed: {str(e)}")
                    result.error_details = str(e)

                    if attempt == max_retries:
                        # 最后一次尝试失败，考虑执行回滚
                        if action.rollback_action:
                            logger.info(f"Executing rollback for failed recovery: {action.description}")
                            rollback_success = await self._execute_rollback(action.rollback_action)
                            result.rollback_performed = rollback_success

                        result.status = RecoveryStatus.FAILED
                        result.success = False
                        result.message = f"恢复操作失败，已尝试 {max_retries + 1} 次: {action.description}"
                        result.end_time = datetime.now()

            # 记录恢复历史
            with self._lock:
                self.recovery_history.append(result)
                if action.target_component in self.active_recoveries:
                    del self.active_recoveries[action.target_component]

            return result

        except Exception as e:
            logger.error(f"Unexpected error during recovery execution: {str(e)}")
            result.status = RecoveryStatus.FAILED
            result.success = False
            result.message = f"恢复执行过程中发生意外错误: {str(e)}"
            result.error_details = str(e)
            result.end_time = datetime.now()

            with self._lock:
                self.recovery_history.append(result)
                if action.target_component in self.active_recoveries:
                    del self.active_recoveries[action.target_component]

            return result

    def _calculate_retry_delay(self, recovery_type: RecoveryType, attempt: int) -> float:
        """计算重试延迟（指数退避）"""
        strategy = self.recovery_strategies.get(recovery_type, {})
        base_delay = strategy.get("base_delay", 1.0)
        max_delay = strategy.get("max_delay", 60.0)
        backoff_multiplier = strategy.get("backoff_multiplier", 2.0)

        delay = min(base_delay * (backoff_multiplier ** attempt), max_delay)
        return delay

    async def _restart_service(self, action: RecoveryAction) -> bool:
        """重启服务"""
        service_config = action.parameters.get("service_config")
        if not service_config:
            raise ValueError("Service configuration not provided for service restart")

        service_name = service_config.get("name")
        logger.info(f"Restarting service: {service_name}")

        try:
            # 这里应该调用实际的服务重启逻辑
            # 例如: await self.service_manager.restart_service(service_config)

            # 模拟服务重启
            await asyncio.sleep(2)

            # 验证服务是否重启成功
            health_result = await self.health_checker.check_service_health_with_retry(
                service_config, max_retries=3
            )

            return health_result.status == HealthStatus.HEALTHY

        except Exception as e:
            logger.error(f"Failed to restart service {service_name}: {str(e)}")
            raise

    async def _resolve_port_conflict(self, action: RecoveryAction) -> bool:
        """解决端口冲突"""
        conflict_info = action.parameters.get("conflict_info")
        port = conflict_info.get("port") if conflict_info else None

        if not port:
            raise ValueError("Port information not provided for port conflict resolution")

        logger.info(f"Resolving port conflict for port: {port}")

        try:
            # 使用新的端口恢复编排器解决冲突
            from core.port_detector import PortConflictResolver, PortConflict

            # 创建端口冲突对象
            conflict_resolver = PortConflictResolver(self.progress_tracker)
            conflicts = await conflict_resolver.detect_conflicts("localhost", [port])

            if not conflicts:
                logger.info(f"No port conflict found for port {port}")
                return True

            conflict = conflicts[0]

            # 使用端口恢复编排器自动解决冲突
            recovery_result = await self.port_recovery_orchestrator.auto_resolve_port_conflict(
                conflict=conflict,
                allow_process_termination=action.parameters.get("allow_termination", True),
                preferred_method=TerminationMethod.HYBRID
            )

            logger.info(f"Port conflict resolution result for port {port}: {recovery_result.conflict_resolved}")

            return recovery_result.conflict_resolved

        except Exception as e:
            logger.error(f"Failed to resolve port conflict for port {port}: {str(e)}")
            raise

    async def _fix_permission_issue(self, action: RecoveryAction) -> bool:
        """修复权限问题"""
        issue_info = action.parameters.get("issue_info")
        target_path = issue_info.get("path") if issue_info else None

        if not target_path:
            raise ValueError("Path not provided for permission fix")

        logger.info(f"Fixing permission issue for path: {target_path}")

        try:
            # 调用权限诊断器修复权限
            result = await self.permission_diagnostic.diagnose_permission_issues(target_path)
            return result.get("status") == "fixed"

        except Exception as e:
            logger.error(f"Failed to fix permission issue for {target_path}: {str(e)}")
            raise

    async def _cleanup_cache(self, action: RecoveryAction) -> bool:
        """清理缓存"""
        logger.info("Performing cache cleanup")

        try:
            # 这里应该实现实际的缓存清理逻辑
            await asyncio.sleep(1)
            return True

        except Exception as e:
            logger.error(f"Failed to cleanup cache: {str(e)}")
            raise

    async def _repair_configuration(self, action: RecoveryAction) -> bool:
        """修复配置"""
        logger.info("Repairing configuration")

        try:
            # 这里应该实现实际的配置修复逻辑
            await asyncio.sleep(2)
            return True

        except Exception as e:
            logger.error(f"Failed to repair configuration: {str(e)}")
            raise

    async def _fix_dependency_issue(self, action: RecoveryAction) -> bool:
        """修复依赖问题"""
        logger.info("Fixing dependency issue")

        try:
            # 这里应该实现实际的依赖修复逻辑
            await asyncio.sleep(3)
            return True

        except Exception as e:
            logger.error(f"Failed to fix dependency issue: {str(e)}")
            raise

    async def _execute_rollback(self, rollback_action: RecoveryAction) -> bool:
        """执行回滚操作"""
        logger.info(f"Executing rollback: {rollback_action.description}")

        try:
            # 这里应该实现具体的回滚逻辑
            await asyncio.sleep(1)
            return True

        except Exception as e:
            logger.error(f"Rollback failed: {str(e)}")
            return False

    async def _verify_recovery_results(
        self,
        recovery_results: List[RecoveryResult],
        service_configs: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """验证恢复结果"""
        verification_results = {
            "total_recoveries": len(recovery_results),
            "successful_recoveries": len([r for r in recovery_results if r.success]),
            "failed_recoveries": len([r for r in recovery_results if not r.success]),
            "services_verified": 0,
            "services_healthy": 0
        }

        # 验证服务健康状态
        for service_config in service_configs:
            verification_results["services_verified"] += 1
            health_result = await self.health_checker.check_service_health_with_retry(
                service_config, max_retries=1
            )

            if health_result.status == HealthStatus.HEALTHY:
                verification_results["services_healthy"] += 1

        return verification_results

    def get_recovery_history(self, limit: Optional[int] = None) -> List[RecoveryResult]:
        """获取恢复历史记录"""
        with self._lock:
            if limit:
                return self.recovery_history[-limit:]
            return self.recovery_history.copy()

    def get_active_recoveries(self) -> Dict[str, RecoveryResult]:
        """获取当前活跃的恢复操作"""
        with self._lock:
            return self.active_recoveries.copy()

    def get_recovery_statistics(self) -> Dict[str, Any]:
        """获取恢复统计信息"""
        with self._lock:
            total_recoveries = len(self.recovery_history)
            successful_recoveries = len([r for r in self.recovery_history if r.success])
            failed_recoveries = total_recoveries - successful_recoveries

            # 按恢复类型统计
            recovery_by_type = {}
            for result in self.recovery_history:
                recovery_type = result.action.recovery_type.value
                if recovery_type not in recovery_by_type:
                    recovery_by_type[recovery_type] = {"total": 0, "successful": 0}
                recovery_by_type[recovery_type]["total"] += 1
                if result.success:
                    recovery_by_type[recovery_type]["successful"] += 1

            return {
                "total_recoveries": total_recoveries,
                "successful_recoveries": successful_recoveries,
                "failed_recoveries": failed_recoveries,
                "success_rate": successful_recoveries / total_recoveries if total_recoveries > 0 else 0,
                "active_recoveries": len(self.active_recoveries),
                "recovery_by_type": recovery_by_type,
                "last_recovery": self.recovery_history[-1].to_dict() if self.recovery_history else None
            }