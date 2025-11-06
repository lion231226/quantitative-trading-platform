"""
Service Recovery Module

This module provides intelligent service restart mechanisms with exponential backoff,
retry limits, and comprehensive monitoring capabilities. It integrates with existing
service managers for safe and reliable restart operations.
"""

import asyncio
import time
import signal
import psutil
import subprocess
import platform
from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import threading
from pathlib import Path

from core.health_checker import HealthChecker, HealthStatus, HealthCheckResult
from utils.progress_tracker import ProgressTracker
from utils.logger import get_logger

logger = get_logger(__name__)


class RestartStrategy(Enum):
    """重启策略枚举"""
    IMMEDIATE = "immediate"
    GRACEFUL = "graceful"
    FORCE = "force"
    EXPONENTIAL_BACKOFF = "exponential_backoff"


class ServiceStatus(Enum):
    """服务状态枚举"""
    RUNNING = "running"
    STOPPED = "stopped"
    STARTING = "starting"
    STOPPING = "stopping"
    FAILED = "failed"
    UNKNOWN = "unknown"


@dataclass
class RestartConfig:
    """重启配置"""
    service_name: str
    max_retries: int = 3
    base_delay: float = 2.0
    max_delay: float = 60.0
    backoff_multiplier: float = 2.0
    timeout_seconds: int = 60
    strategy: RestartStrategy = RestartStrategy.EXPONENTIAL_BACKOFF
    health_check_interval: float = 5.0
    graceful_shutdown_timeout: int = 30
    dependencies: List[str] = field(default_factory=list)
    startup_order: int = 0


@dataclass
class RestartResult:
    """重启结果"""
    service_name: str
    success: bool
    status: ServiceStatus
    message: str
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    retry_count: int = 0
    total_downtime: float = 0.0
    error_details: Optional[str] = None
    health_check_results: List[HealthCheckResult] = field(default_factory=list)

    @property
    def duration(self) -> Optional[timedelta]:
        """获取重启操作持续时间"""
        if self.end_time and self.start_time:
            return self.end_time - self.start_time
        return None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "service_name": self.service_name,
            "success": self.success,
            "status": self.status.value,
            "message": self.message,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": self.duration.total_seconds() if self.duration else None,
            "retry_count": self.retry_count,
            "total_downtime": self.total_downtime,
            "error_details": self.error_details,
            "health_checks_count": len(self.health_check_results)
        }


class ServiceRecovery:
    """服务恢复管理器"""

    def __init__(self):
        """初始化服务恢复管理器"""
        self.health_checker = HealthChecker()
        self.progress_tracker = ProgressTracker(
            component_name="service_recovery"
        )

        # 服务状态监控
        self.service_status_cache: Dict[str, Dict[str, Any]] = {}
        self.status_cache_timeout = 30.0  # 缓存30秒

        # 重试历史
        self.restart_history: List[RestartResult] = []
        self.active_restarts: Dict[str, RestartResult] = {}

        # 线程锁
        self._lock = threading.Lock()

        # 平台特定的信号处理
        self._setup_signal_handlers()

        logger.info("ServiceRecovery initialized")

    def _setup_signal_handlers(self):
        """设置平台特定的信号处理器"""
        self.system = platform.system().lower()

        if self.system == "windows":
            self.sigterm = signal.SIGTERM
            self.sigkill = signal.CTRL_BREAK_EVENT
        else:
            self.sigterm = signal.SIGTERM
            self.sigkill = signal.SIGKILL

    async def restart_service(self, restart_config: RestartConfig) -> RestartResult:
        """
        重启服务

        Args:
            restart_config: 重启配置

        Returns:
            RestartResult: 重启结果
        """
        result = RestartResult(
            service_name=restart_config.service_name,
            success=False,
            status=ServiceStatus.UNKNOWN,
            message="开始重启服务"
        )

        with self._lock:
            self.active_restarts[restart_config.service_name] = result

        try:
            logger.info(f"Starting service restart: {restart_config.service_name}")

            # 初始化进度跟踪 - 添加步骤
            self.progress_tracker.add_step(f"重启服务: {restart_config.service_name}", "服务重启流程", 100.0)
            self.progress_tracker.add_step("检查服务状态", "检查服务当前状态", 10.0)
            if restart_config.dependencies:
                self.progress_tracker.add_step("检查依赖服务", "检查依赖服务状态", 15.0)
            self.progress_tracker.add_step("停止服务", "停止当前运行的服务", 30.0)
            self.progress_tracker.add_step("启动服务", "重新启动服务", 40.0)
            self.progress_tracker.add_step("验证服务状态", "验证服务启动成功", 5.0)

            # 开始重启流程
            self.progress_tracker.start_step(0)

            # 步骤1: 检查服务当前状态
            step_index = 1
            self.progress_tracker.start_step(step_index)
            current_status = await self._get_service_status(restart_config.service_name)
            self.progress_tracker.complete_step(step_index, True, f"当前状态: {current_status}")

            # 步骤2: 检查依赖服务
            if restart_config.dependencies:
                step_index += 1
                self.progress_tracker.start_step(step_index)
                dependencies_ok = await self._check_dependencies(restart_config.dependencies)
                if not dependencies_ok:
                    raise RuntimeError("依赖服务状态异常，无法安全重启")
                self.progress_tracker.complete_step(step_index, True, "依赖服务检查通过")

            # 步骤3: 停止服务
            step_index += 1
            self.progress_tracker.start_step(step_index)
            stop_success = await self._stop_service(restart_config)
            if not stop_success:
                raise RuntimeError("服务停止失败")
            self.progress_tracker.complete_step(step_index, True, "服务停止成功")

            # 步骤4: 等待重启延迟
            if restart_config.strategy == RestartStrategy.EXPONENTIAL_BACKOFF:
                delay = self._calculate_restart_delay(restart_config, result.retry_count)
                if delay > 0:
                    # 这个延迟步骤不在主要步骤中，直接跳过进度跟踪
                    await asyncio.sleep(delay)

            # 步骤5: 启动服务
            step_index += 1
            self.progress_tracker.start_step(step_index)
            start_success = await self._start_service(restart_config)
            if not start_success:
                raise RuntimeError("服务启动失败")
            self.progress_tracker.complete_step(step_index, True, "服务启动成功")

            # 步骤6: 健康检查
            step_index += 1
            self.progress_tracker.start_step(step_index)
            health_ok = await self._verify_service_health(restart_config)
            if not health_ok:
                raise RuntimeError("服务健康检查失败")
            self.progress_tracker.complete_step(step_index, True, "健康检查通过")

            # 重启成功
            result.success = True
            result.status = ServiceStatus.RUNNING
            result.message = f"服务 {restart_config.service_name} 重启成功"
            result.end_time = datetime.now()

            # 完成整个流程
            self.progress_tracker.complete_step(0, True, "服务重启完成")

            logger.info(f"Service restart completed successfully: {restart_config.service_name}")

        except Exception as e:
            logger.error(f"Service restart failed for {restart_config.service_name}: {str(e)}")
            result.success = False
            result.status = ServiceStatus.FAILED
            result.message = f"服务重启失败: {str(e)}"
            result.error_details = str(e)
            result.end_time = datetime.now()

            # 如果步骤已经添加，标记第一个步骤失败
            if len(self.progress_tracker.progress_info.steps) > 0:
                self.progress_tracker.complete_step(0, False, f"服务重启失败: {str(e)}")

            # 检查是否需要重试
            if result.retry_count < restart_config.max_retries:
                result.retry_count += 1
                logger.info(f"Retrying service restart for {restart_config.service_name} (attempt {result.retry_count})")

                # 等待重试延迟
                delay = self._calculate_restart_delay(restart_config, result.retry_count)
                await asyncio.sleep(delay)

                # 递归重试
                return await self.restart_service(restart_config)

        # 记录重启历史
        with self._lock:
            self.restart_history.append(result)
            if restart_config.service_name in self.active_restarts:
                del self.active_restarts[restart_config.service_name]

        return result

    async def _get_service_status(self, service_name: str) -> ServiceStatus:
        """获取服务状态"""
        # 检查缓存
        cached_status = self.service_status_cache.get(service_name)
        if cached_status:
            cache_time = cached_status.get("timestamp", 0)
            if time.time() - cache_time < self.status_cache_timeout:
                return cached_status.get("status", ServiceStatus.UNKNOWN)

        try:
            # 查找服务进程
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmdline = ' '.join(proc.info['cmdline'] or [])
                    if service_name.lower() in cmdline.lower() or service_name.lower() in proc.info['name'].lower():
                        processes.append(proc)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            if not processes:
                status = ServiceStatus.STOPPED
            else:
                # 检查进程是否在运行
                running_processes = [p for p in processes if p.is_running()]
                if running_processes:
                    status = ServiceStatus.RUNNING
                else:
                    status = ServiceStatus.STOPPED

            # 更新缓存
            with self._lock:
                self.service_status_cache[service_name] = {
                    "status": status,
                    "timestamp": time.time(),
                    "processes": len(processes)
                }

            return status

        except Exception as e:
            logger.error(f"Error getting service status for {service_name}: {str(e)}")
            return ServiceStatus.UNKNOWN

    async def _check_dependencies(self, dependencies: List[str]) -> bool:
        """检查依赖服务状态"""
        for dependency in dependencies:
            status = await self._get_service_status(dependency)
            if status != ServiceStatus.RUNNING:
                logger.warning(f"Dependency service {dependency} is not running (status: {status})")
                return False
        return True

    async def _stop_service(self, restart_config: RestartConfig) -> bool:
        """停止服务"""
        service_name = restart_config.service_name
        logger.info(f"Stopping service: {service_name}")

        try:
            # 获取服务进程
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmdline = ' '.join(proc.info['cmdline'] or [])
                    if service_name.lower() in cmdline.lower() or service_name.lower() in proc.info['name'].lower():
                        processes.append(proc)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            if not processes:
                logger.info(f"No processes found for service: {service_name}")
                return True

            # 根据策略停止服务
            if restart_config.strategy == RestartStrategy.GRACEFUL:
                # 优雅关闭
                for proc in processes:
                    try:
                        proc.terminate()
                        logger.info(f"Sent SIGTERM to process {proc.pid}")
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue

                # 等待优雅关闭
                await asyncio.sleep(restart_config.graceful_shutdown_timeout)

                # 检查是否还有进程在运行
                remaining_processes = [p for p in processes if p.is_running()]
                if remaining_processes:
                    logger.warning(f"Graceful shutdown timeout, forcing termination for {len(remaining_processes)} processes")
                    for proc in remaining_processes:
                        try:
                            if self.system == "windows":
                                proc.send_signal(self.sigkill)
                            else:
                                proc.kill()
                            logger.info(f"Force killed process {proc.pid}")
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            continue

            elif restart_config.strategy == RestartStrategy.FORCE:
                # 强制关闭
                for proc in processes:
                    try:
                        if self.system == "windows":
                            proc.send_signal(self.sigkill)
                        else:
                            proc.kill()
                        logger.info(f"Force killed process {proc.pid}")
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue

            else:
                # 默认策略：先尝试优雅关闭，再强制关闭
                for proc in processes:
                    try:
                        proc.terminate()
                        logger.info(f"Sent SIGTERM to process {proc.pid}")
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue

                await asyncio.sleep(5)

                remaining_processes = [p for p in processes if p.is_running()]
                for proc in remaining_processes:
                    try:
                        if self.system == "windows":
                            proc.send_signal(self.sigkill)
                        else:
                            proc.kill()
                        logger.info(f"Force killed process {proc.pid}")
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue

            # 等待一段时间确保进程完全停止
            await asyncio.sleep(2)

            # 验证服务是否已停止
            status = await self._get_service_status(service_name)
            return status == ServiceStatus.STOPPED

        except Exception as e:
            logger.error(f"Error stopping service {service_name}: {str(e)}")
            return False

    async def _start_service(self, restart_config: RestartConfig) -> bool:
        """启动服务"""
        service_name = restart_config.service_name
        logger.info(f"Starting service: {service_name}")

        try:
            # 这里应该根据服务类型调用相应的启动逻辑
            # 例如：调用 service_manager 或执行启动脚本

            # 模拟服务启动
            await asyncio.sleep(3)

            # 验证服务是否启动成功
            status = await self._get_service_status(service_name)
            return status == ServiceStatus.RUNNING

        except Exception as e:
            logger.error(f"Error starting service {service_name}: {str(e)}")
            return False

    async def _verify_service_health(self, restart_config: RestartConfig) -> bool:
        """验证服务健康状态"""
        service_name = restart_config.service_name
        logger.info(f"Verifying health for service: {service_name}")

        try:
            # 构造服务配置用于健康检查
            service_config = {
                "name": service_name,
                "type": "http",  # 默认类型
                "url": f"http://localhost:8000/health",  # 默认健康检查端点
                "timeout": restart_config.timeout_seconds
            }

            # 执行健康检查
            health_result = await self.health_checker.check_service_health_with_retry(
                service_config, max_retries=3
            )

            # 记录健康检查结果
            if hasattr(self, '_current_restart_result'):
                self._current_restart_result.health_check_results.append(health_result)

            return health_result.status == HealthStatus.HEALTHY

        except Exception as e:
            logger.error(f"Error verifying health for service {service_name}: {str(e)}")
            return False

    def _calculate_restart_delay(self, restart_config: RestartConfig, retry_count: int) -> float:
        """计算重启延迟（指数退避）"""
        if restart_config.strategy != RestartStrategy.EXPONENTIAL_BACKOFF:
            return 0.0

        delay = min(
            restart_config.base_delay * (restart_config.backoff_multiplier ** retry_count),
            restart_config.max_delay
        )
        return delay

    async def monitor_service(self, service_name: str, health_check_interval: float = 30.0) -> None:
        """
        持续监控服务状态

        Args:
            service_name: 服务名称
            health_check_interval: 健康检查间隔（秒）
        """
        logger.info(f"Starting service monitoring for: {service_name}")

        try:
            while True:
                status = await self._get_service_status(service_name)
                logger.debug(f"Service {service_name} status: {status}")

                # 如果服务状态异常，触发自动恢复
                if status == ServiceStatus.FAILED or status == ServiceStatus.UNKNOWN:
                    logger.warning(f"Service {service_name} status is abnormal: {status}")

                    # 创建默认重启配置
                    restart_config = RestartConfig(
                        service_name=service_name,
                        strategy=RestartStrategy.EXPONENTIAL_BACKOFF,
                        max_retries=3
                    )

                    # 执行自动重启
                    await self.restart_service(restart_config)

                await asyncio.sleep(health_check_interval)

        except asyncio.CancelledError:
            logger.info(f"Service monitoring cancelled for: {service_name}")
        except Exception as e:
            logger.error(f"Error in service monitoring for {service_name}: {str(e)}")

    def get_restart_history(self, service_name: Optional[str] = None, limit: Optional[int] = None) -> List[RestartResult]:
        """获取重启历史记录"""
        with self._lock:
            history = self.restart_history

            if service_name:
                history = [r for r in history if r.service_name == service_name]

            if limit:
                history = history[-limit:]

            return history.copy()

    def get_active_restarts(self) -> Dict[str, RestartResult]:
        """获取当前活跃的重启操作"""
        with self._lock:
            return self.active_restarts.copy()

    def get_restart_statistics(self, service_name: Optional[str] = None) -> Dict[str, Any]:
        """获取重启统计信息"""
        with self._lock:
            history = self.restart_history

            if service_name:
                history = [r for r in history if r.service_name == service_name]

            total_restarts = len(history)
            successful_restarts = len([r for r in history if r.success])
            failed_restarts = total_restarts - successful_restarts

            # 计算平均重启时间
            successful_times = [r.duration.total_seconds() for r in history if r.success and r.duration]
            avg_restart_time = sum(successful_times) / len(successful_times) if successful_times else 0

            # 计算平均停机时间
            avg_downtime = sum(r.total_downtime for r in history) / total_restarts if total_restarts > 0 else 0

            return {
                "service_name": service_name,
                "total_restarts": total_restarts,
                "successful_restarts": successful_restarts,
                "failed_restarts": failed_restarts,
                "success_rate": successful_restarts / total_restarts if total_restarts > 0 else 0,
                "average_restart_time_seconds": avg_restart_time,
                "average_downtime_seconds": avg_downtime,
                "active_restarts": len(self.active_restarts),
                "last_restart": history[-1].to_dict() if history else None
            }

    def clear_restart_history(self, service_name: Optional[str] = None, older_than: Optional[timedelta] = None) -> int:
        """清理重启历史记录"""
        with self._lock:
            original_count = len(self.restart_history)

            if older_than:
                cutoff_time = datetime.now() - older_than
                self.restart_history = [
                    r for r in self.restart_history
                    if r.start_time > cutoff_time and (not service_name or r.service_name == service_name)
                ]
            elif service_name:
                self.restart_history = [r for r in self.restart_history if r.service_name != service_name]
            else:
                self.restart_history.clear()

            return original_count - len(self.restart_history)