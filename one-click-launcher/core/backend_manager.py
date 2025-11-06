"""
后端管理器核心逻辑

提供后端服务的高级管理功能，包括服务编排、状态监控和错误处理。
"""

import asyncio
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import json

from services.backend_service import (
    BackendServiceManager, BackendServiceConfig, BackendServiceStatus, BackendServiceInfo
)
from core.service_dependency_analyzer import ServiceDependencyAnalyzer, ServiceInfo, ServiceType
from core.health_checker import HealthChecker, HealthCheckResult, HealthStatus
from core.service_configurator import ServiceConfigurator

from utils.logger import get_logger
from utils.progress_tracker import ProgressTracker

logger = get_logger(__name__)


class BackendManagerStatus(Enum):
    """后端管理器状态"""
    IDLE = "idle"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class BackendManagerConfig:
    """后端管理器配置"""
    service_configs: List[BackendServiceConfig] = field(default_factory=list)
    health_check_interval: int = 30  # seconds
    auto_restart: bool = True
    max_restart_attempts: int = 3
    restart_delay: int = 10  # seconds
    enable_monitoring: bool = True


@dataclass
class BackendManagerState:
    """后端管理器状态"""
    status: BackendManagerStatus
    services: Dict[str, BackendServiceManager] = field(default_factory=dict)
    health_results: Dict[str, HealthCheckResult] = field(default_factory=dict)
    start_time: Optional[datetime] = None
    last_health_check: Optional[datetime] = None
    error_message: Optional[str] = None
    restart_attempts: Dict[str, int] = field(default_factory=dict)


class BackendManager:
    """后端管理器"""

    def __init__(self, config: BackendManagerConfig):
        self.config = config
        self.state = BackendManagerState(status=BackendManagerStatus.IDLE)

        # Initialize core components
        self.health_checker = HealthChecker()
        self.dependency_analyzer = ServiceDependencyAnalyzer()
        self.service_configurator = ServiceConfigurator()

        # Progress tracking
        self.progress_tracker = ProgressTracker(
            component_name="backend_manager",
            total_steps=3
        )

        # Background tasks
        self._monitoring_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()

        logger.info("BackendManager initialized")

    async def start_all_services(self) -> bool:
        """
        启动所有后端服务

        Returns:
            bool: 是否所有服务都启动成功
        """
        try:
            logger.info("Starting all backend services")
            self.state.status = BackendManagerStatus.STARTING
            self.progress_tracker.start()

            if not self.config.service_configs:
                logger.warning("No service configurations provided")
                return True

            # Start services in dependency order
            startup_order = await self._calculate_startup_order()

            all_started = True
            for service_name in startup_order:
                try:
                    service_config = next(
                        config for config in self.config.service_configs
                        if config.service_name == service_name
                    )

                    service_manager = BackendServiceManager(service_config)
                    self.state.services[service_name] = service_manager

                    logger.info(f"Starting service: {service_name}")
                    success = await service_manager.start()

                    if not success:
                        logger.error(f"Failed to start service: {service_name}")
                        all_started = False
                        if not self.config.auto_restart:
                            break
                    else:
                        logger.info(f"Service started successfully: {service_name}")

                except Exception as e:
                    logger.error(f"Error starting service {service_name}: {e}")
                    all_started = False
                    if not self.config.auto_restart:
                        break

            self.progress_tracker.update_step("Services started")

            # Start monitoring if enabled
            if self.config.enable_monitoring and all_started:
                await self._start_monitoring()

            self.state.status = BackendManagerStatus.RUNNING if all_started else BackendManagerStatus.ERROR
            self.state.start_time = datetime.now()

            self.progress_tracker.complete()

            return all_started

        except Exception as e:
            logger.error(f"Failed to start backend services: {e}")
            self.state.status = BackendManagerStatus.ERROR
            self.state.error_message = str(e)
            self.progress_tracker.complete_with_error(str(e))
            return False

    async def stop_all_services(self) -> bool:
        """
        停止所有后端服务

        Returns:
            bool: 是否所有服务都停止成功
        """
        try:
            logger.info("Stopping all backend services")
            self.state.status = BackendManagerStatus.STOPPING

            # Stop monitoring
            await self._stop_monitoring()

            # Stop services in reverse order
            stop_order = list(self.state.services.keys())[::-1]

            all_stopped = True
            for service_name in stop_order:
                try:
                    service_manager = self.state.services.get(service_name)
                    if service_manager:
                        logger.info(f"Stopping service: {service_name}")
                        success = await service_manager.stop()

                        if not success:
                            logger.error(f"Failed to stop service: {service_name}")
                            all_stopped = False
                        else:
                            logger.info(f"Service stopped successfully: {service_name}")

                except Exception as e:
                    logger.error(f"Error stopping service {service_name}: {e}")
                    all_stopped = False

            self.state.status = BackendManagerStatus.STOPPED if all_stopped else BackendManagerStatus.ERROR
            return all_stopped

        except Exception as e:
            logger.error(f"Failed to stop backend services: {e}")
            self.state.status = BackendManagerStatus.ERROR
            self.state.error_message = str(e)
            return False

    async def get_service_status(self, service_name: str) -> Optional[BackendServiceInfo]:
        """
        获取特定服务状态

        Args:
            service_name: 服务名称

        Returns:
            Optional[BackendServiceInfo]: 服务信息
        """
        service_manager = self.state.services.get(service_name)
        if service_manager:
            return await service_manager.get_status()
        return None

    async def get_all_services_status(self) -> Dict[str, BackendServiceInfo]:
        """
        获取所有服务状态

        Returns:
            Dict[str, BackendServiceInfo]: 所有服务状态
        """
        status = {}
        for service_name, service_manager in self.state.services.items():
            try:
                status[service_name] = await service_manager.get_status()
            except Exception as e:
                logger.error(f"Error getting status for {service_name}: {e}")
                # Create error status
                error_status = BackendServiceInfo(
                    config=service_manager.config,
                    status=BackendServiceStatus.FAILED,
                    error_message=str(e)
                )
                status[service_name] = error_status

        return status

    async def health_check_all_services(self) -> Dict[str, HealthCheckResult]:
        """
        对所有服务执行健康检查

        Returns:
            Dict[str, HealthCheckResult]: 健康检查结果
        """
        results = {}

        for service_name, service_manager in self.state.services.items():
            try:
                result = await service_manager.health_check()
                results[service_name] = result
                self.state.health_results[service_name] = result
            except Exception as e:
                logger.error(f"Health check failed for {service_name}: {e}")
                error_result = HealthCheckResult(
                    status=HealthStatus.UNHEALTHY,
                    service_name=service_name,
                    check_type="health_check",
                    message=f"Health check error: {e}"
                )
                results[service_name] = error_result
                self.state.health_results[service_name] = error_result

        self.state.last_health_check = datetime.now()
        return results

    async def restart_service(self, service_name: str) -> bool:
        """
        重启特定服务

        Args:
            service_name: 服务名称

        Returns:
            bool: 重启是否成功
        """
        service_manager = self.state.services.get(service_name)
        if not service_manager:
            logger.error(f"Service not found: {service_name}")
            return False

        # Check restart limit
        restart_count = self.state.restart_attempts.get(service_name, 0)
        if restart_count >= self.config.max_restart_attempts:
            logger.error(f"Max restart attempts reached for {service_name}")
            return False

        logger.info(f"Restarting service: {service_name}")
        self.state.restart_attempts[service_name] = restart_count + 1

        try:
            success = await service_manager.restart()
            if success:
                # Reset restart count on successful restart
                self.state.restart_attempts[service_name] = 0
                logger.info(f"Service restarted successfully: {service_name}")
            else:
                logger.error(f"Failed to restart service: {service_name}")

            return success

        except Exception as e:
            logger.error(f"Error restarting service {service_name}: {e}")
            return False

    async def get_manager_status(self) -> BackendManagerState:
        """
        获取管理器状态

        Returns:
            BackendManagerState: 管理器状态
        """
        return self.state

    # Private methods

    async def _calculate_startup_order(self) -> List[str]:
        """计算服务启动顺序"""
        # For now, return services in order they appear in config
        # In the future, this could analyze dependencies
        return [config.service_name for config in self.config.service_configs]

    async def _start_monitoring(self):
        """启动后台监控"""
        if self._monitoring_task:
            return

        logger.info("Starting backend service monitoring")
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())

    async def _stop_monitoring(self):
        """停止后台监控"""
        if self._monitoring_task:
            logger.info("Stopping backend service monitoring")
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
            self._monitoring_task = None

    async def _monitoring_loop(self):
        """监控循环"""
        while not self._shutdown_event.is_set():
            try:
                # Perform health checks
                await self.health_check_all_services()

                # Check for failed services and auto-restart if enabled
                if self.config.auto_restart:
                    await self._check_and_restart_failed_services()

                # Wait for next check
                try:
                    await asyncio.wait_for(
                        self._shutdown_event.wait(),
                        timeout=self.config.health_check_interval
                    )
                    break  # Shutdown event was set
                except asyncio.TimeoutError:
                    continue  # Continue monitoring

            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(5)  # Brief pause before retry

    async def _check_and_restart_failed_services(self):
        """检查并重启失败的服务"""
        for service_name, health_result in self.state.health_results.items():
            if health_result.status != HealthStatus.HEALTHY:
                service_manager = self.state.services.get(service_name)
                if service_manager:
                    service_info = await service_manager.get_status()

                    # Check if service needs restart
                    if (service_info.status in [BackendServiceStatus.FAILED, BackendServiceStatus.STOPPED] and
                        self.state.restart_attempts.get(service_name, 0) < self.config.max_restart_attempts):

                        logger.warning(f"Detected failed service, attempting restart: {service_name}")

                        # Wait before restart
                        await asyncio.sleep(self.config.restart_delay)

                        # Attempt restart
                        success = await self.restart_service(service_name)
                        if not success:
                            logger.error(f"Auto-restart failed for service: {service_name}")