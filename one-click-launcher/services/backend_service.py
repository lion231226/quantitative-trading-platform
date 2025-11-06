"""
后端API服务启动器

提供FastAPI/Flask后端服务的统一启动、配置和健康检查功能。
"""

import asyncio
import sys
import time
import psutil
import subprocess
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from datetime import datetime
import json
import signal
import os

# Import core components
from core.service_dependency_analyzer import (
    ServiceDependencyAnalyzer, ServiceInfo, ServiceType, ServiceStatus
)
from core.health_checker import HealthChecker, HealthCheckResult, HealthStatus
from core.port_manager import PortManager, PortInfo, PortStatus
from core.timeout_manager import TimeoutManager, TimeoutConfig, StartupResult
from core.service_configurator import ServiceConfigurator, ServiceConfig, Environment

# Import utilities
from utils.logger import get_logger
from utils.progress_tracker import ProgressTracker
from utils.api_health_checker import APIHealthChecker
from utils.database_validator import DatabaseValidator

logger = get_logger(__name__)


class BackendServiceStatus(Enum):
    """后端服务状态"""
    NOT_STARTED = "not_started"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class BackendServiceConfig:
    """后端服务配置"""
    service_name: str = "backend_api"
    host: str = "localhost"
    port: int = 8000
    backend_type: str = "fastapi"
    working_directory: str = "backend"
    startup_script: str = "main.py"
    python_executable: str = "python"
    startup_timeout: int = 30
    health_check_interval: int = 5
    max_retries: int = 3
    env_file: Optional[str] = None
    log_level: str = "INFO"

    # API endpoints configuration
    health_endpoint: str = "/health"
    docs_endpoint: str = "/api/docs"

    # Database connections
    redis_host: str = "localhost"
    redis_port: int = 6379
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "quantdb"


@dataclass
class BackendServiceInfo:
    """后端服务信息"""
    config: BackendServiceConfig
    status: BackendServiceStatus
    process_id: Optional[int] = None
    start_time: Optional[datetime] = None
    last_health_check: Optional[datetime] = None
    health_status: Optional[HealthCheckResult] = None
    startup_log: List[str] = field(default_factory=list)
    error_message: Optional[str] = None
    restart_count: int = 0


class BackendServiceManager:
    """后端服务管理器"""

    def __init__(self, config: BackendServiceConfig):
        self.config = config
        self.service_info = BackendServiceInfo(
            config=config,
            status=BackendServiceStatus.NOT_STARTED
        )

        # Initialize core components
        self.health_checker = HealthChecker()
        self.port_manager = PortManager()
        self.timeout_manager = TimeoutManager(TimeoutConfig(
            default_timeout=config.startup_timeout,
            max_retries=config.max_retries
        ))
        self.service_configurator = ServiceConfigurator(
            config_path="config/backend-config.yaml"
        )
        self.dependency_analyzer = ServiceDependencyAnalyzer()

        # Initialize specialized validators
        self.api_health_checker = APIHealthChecker(timeout=10.0)
        self.database_validator = DatabaseValidator(timeout=10.0)

        # Initialize progress tracker
        self.progress_tracker = ProgressTracker(
            component_name="backend_api_startup"
        )

        self._is_running = False
        self._shutdown_event = asyncio.Event()

        logger.info(f"BackendServiceManager initialized for {config.service_name}")

    async def start(self) -> bool:
        """启动后端服务"""
        try:
            logger.info(f"Starting backend service: {self.config.service_name}")
            self.service_info.status = BackendServiceStatus.STARTING
            self.progress_tracker.start()

            # Step 1: 检查依赖服务
            await self._check_dependencies()
            self.progress_tracker.update_step("Dependencies checked")

            # Step 2: 配置服务参数
            await self._configure_service()
            self.progress_tracker.update_step("Service configured")

            # Step 3: 启动Python进程
            await self._start_backend_process()
            self.progress_tracker.update_step("Backend process started")

            # Step 4: 验证API端点
            await self._verify_api_endpoints()
            self.progress_tracker.update_step("API endpoints verified")

            # Step 5: 初始化应用状态
            await self._initialize_application_state()
            self.progress_tracker.update_step("Application state initialized")

            self.service_info.status = BackendServiceStatus.RUNNING
            self._is_running = True
            self.service_info.start_time = datetime.now()

            logger.info(f"Backend service started successfully: {self.config.service_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to start backend service: {e}")
            self.service_info.status = BackendServiceStatus.FAILED
            self.service_info.error_message = str(e)
            self.progress_tracker.complete_with_error(f"Startup failed: {e}")
            return False

    async def stop(self) -> bool:
        """停止后端服务"""
        try:
            logger.info(f"Stopping backend service: {self.config.service_name}")
            self.service_info.status = BackendServiceStatus.STOPPING
            self._shutdown_event.set()
            self._is_running = False

            if self.service_info.process_id:
                await self._stop_backend_process()

            self.service_info.status = BackendServiceStatus.STOPPED
            logger.info(f"Backend service stopped successfully: {self.config.service_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to stop backend service: {e}")
            self.service_info.error_message = str(e)
            return False

    async def health_check(self) -> HealthCheckResult:
        """执行健康检查"""
        try:
            # Check process status
            if not await self._is_process_running():
                return HealthCheckResult(
                    status=HealthStatus.UNHEALTHY,
                    service_name=self.config.service_name,
                    check_type="process",
                    message="Backend process is not running"
                )

            # Check API endpoints
            health_result = await self._check_health_endpoint()
            docs_result = await self._check_docs_endpoint()

            # Check database connections
            db_result = await self._check_database_connections()

            # Combine results
            overall_status = HealthStatus.HEALTHY
            messages = []

            if health_result.status != HealthStatus.HEALTHY:
                overall_status = HealthStatus.UNHEALTHY
                messages.append(f"Health endpoint: {health_result.message}")

            if docs_result.status != HealthStatus.HEALTHY:
                overall_status = HealthStatus.UNHEALTHY
                messages.append(f"Docs endpoint: {docs_result.message}")

            if db_result.status != HealthStatus.HEALTHY:
                overall_status = HealthStatus.UNHEALTHY
                messages.append(f"Database: {db_result.message}")

            result = HealthCheckResult(
                status=overall_status,
                service_name=self.config.service_name,
                check_type="comprehensive",
                message="; ".join(messages) if messages else "All checks passed",
                details={
                    "health_endpoint": health_result.to_dict(),
                    "docs_endpoint": docs_result.to_dict(),
                    "database": db_result.to_dict()
                }
            )

            self.service_info.health_status = result
            self.service_info.last_health_check = datetime.now()

            return result

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                service_name=self.config.service_name,
                check_type="comprehensive",
                message=f"Health check error: {e}"
            )

    async def get_status(self) -> BackendServiceInfo:
        """获取服务状态"""
        return self.service_info

    async def restart(self) -> bool:
        """重启后端服务"""
        logger.info(f"Restarting backend service: {self.config.service_name}")
        self.service_info.restart_count += 1

        if await self.stop():
            await asyncio.sleep(2)
            return await self.start()

        return False

    # Private methods

    async def _check_dependencies(self):
        """检查依赖服务"""
        logger.info("Checking backend service dependencies")

        dependencies = [
            ServiceInfo(
                name="redis",
                service_type=ServiceType.DATABASE,
                host=self.config.redis_host,
                port=self.config.redis_port
            ),
            ServiceInfo(
                name="postgresql",
                service_type=ServiceType.DATABASE,
                host=self.config.postgres_host,
                port=self.config.postgres_port
            )
        ]

        for dependency in dependencies:
            result = await self.health_checker.check_service_health(dependency)
            if result.status != HealthStatus.HEALTHY:
                raise Exception(f"Dependency {dependency.name} is not healthy: {result.message}")

        self.service_info.startup_log.append("Dependencies verified successfully")

    async def _configure_service(self):
        """配置服务参数"""
        logger.info("Configuring backend service")

        if self.config.env_file and Path(self.config.env_file).exists():
            await self.service_configurator.load_env_file(self.config.env_file)

        port_available = await self.port_manager.check_port_availability(self.config.port)
        if not port_available:
            raise Exception(f"Port {self.config.port} is not available")

        env_vars = {
            "PYTHONPATH": str(Path.cwd()),
            "LOG_LEVEL": self.config.log_level,
            "REDIS_HOST": self.config.redis_host,
            "REDIS_PORT": str(self.config.redis_port),
            "POSTGRES_HOST": self.config.postgres_host,
            "POSTGRES_PORT": str(self.config.postgres_port),
            "POSTGRES_DB": self.config.postgres_db,
        }

        for key, value in env_vars.items():
            os.environ[key] = value

        self.service_info.startup_log.append(f"Service configured on port {self.config.port}")

    async def _start_backend_process(self):
        """启动后端Python进程"""
        logger.info("Starting backend process")

        startup_cmd = [
            self.config.python_executable,
            self.config.startup_script
        ]

        work_dir = Path(self.config.working_directory)
        if not work_dir.exists():
            raise Exception(f"Working directory does not exist: {work_dir}")

        try:
            process = subprocess.Popen(
                startup_cmd,
                cwd=work_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=os.environ.copy()
            )

            self.service_info.process_id = process.pid
            self.service_info.startup_log.append(f"Backend process started with PID: {process.pid}")

            await asyncio.sleep(2)

            if not await self._is_process_running():
                raise Exception("Backend process failed to start or exited immediately")

            logger.info(f"Backend process started successfully with PID: {process.pid}")

        except Exception as e:
            logger.error(f"Failed to start backend process: {e}")
            raise

    async def _verify_api_endpoints(self):
        """验证API端点"""
        logger.info("Verifying API endpoints")

        health_result = await self._check_health_endpoint()
        if health_result.status != HealthStatus.HEALTHY:
            raise Exception(f"Health endpoint verification failed: {health_result.message}")

        docs_result = await self._check_docs_endpoint()
        if docs_result.status != HealthStatus.HEALTHY:
            raise Exception(f"Docs endpoint verification failed: {docs_result.message}")

        if health_result.response_time and health_result.response_time > 2.0:
            raise Exception(f"Health endpoint response time too slow: {health_result.response_time}s")

        self.service_info.startup_log.append("API endpoints verified successfully")

    async def _initialize_application_state(self):
        """初始化应用状态"""
        logger.info("Initializing application state")

        await asyncio.sleep(1)

        self.service_info.startup_log.append("Application state initialized")

    async def _is_process_running(self) -> bool:
        """检查进程是否运行"""
        if not self.service_info.process_id:
            return False

        try:
            process = psutil.Process(self.service_info.process_id)
            return process.is_running() and process.status() != psutil.STATUS_ZOMBIE
        except psutil.NoSuchProcess:
            return False

    async def _stop_backend_process(self):
        """停止后端进程"""
        if not self.service_info.process_id:
            return

        try:
            process = psutil.Process(self.service_info.process_id)

            process.terminate()
            await asyncio.sleep(5)

            if process.is_running():
                process.kill()
                await asyncio.sleep(2)

            self.service_info.process_id = None
            logger.info("Backend process stopped")

        except psutil.NoSuchProcess:
            logger.info("Backend process already stopped")
            self.service_info.process_id = None

    async def _check_health_endpoint(self) -> HealthCheckResult:
        """检查健康端点"""
        url = f"http://{self.config.host}:{self.config.port}{self.config.health_endpoint}"

        try:
            result = await self.health_checker.check_http_health(
                endpoint=url,
                service_name=self.config.service_name
            )
            return result
        except Exception as e:
            return HealthCheckResult(
                status=HealthStatus.CONNECTION_ERROR,
                service_name=self.config.service_name,
                check_type="health_endpoint",
                message=f"Health endpoint check failed: {e}"
            )

    async def _check_docs_endpoint(self) -> HealthCheckResult:
        """检查文档端点"""
        url = f"http://{self.config.host}:{self.config.port}{self.config.docs_endpoint}"

        try:
            result = await self.health_checker.check_http_health(
                endpoint=url,
                service_name=self.config.service_name
            )
            return result
        except Exception as e:
            return HealthCheckResult(
                status=HealthStatus.CONNECTION_ERROR,
                service_name=self.config.service_name,
                check_type="docs_endpoint",
                message=f"Docs endpoint check failed: {e}"
            )

    async def _check_database_connections(self) -> HealthCheckResult:
        """检查数据库连接"""
        try:
            redis_service = ServiceInfo(
                name="redis",
                service_type=ServiceType.DATABASE,
                host=self.config.redis_host,
                port=self.config.redis_port
            )
            redis_result = await self.health_checker.check_service_health(redis_service)

            postgres_service = ServiceInfo(
                name="postgresql",
                service_type=ServiceType.DATABASE,
                host=self.config.postgres_host,
                port=self.config.postgres_port
            )
            postgres_result = await self.health_checker.check_service_health(postgres_service)

            if redis_result.status == HealthStatus.HEALTHY and postgres_result.status == HealthStatus.HEALTHY:
                return HealthCheckResult(
                    status=HealthStatus.HEALTHY,
                    service_name=self.config.service_name,
                    check_type="database",
                    message="All database connections healthy"
                )
            else:
                messages = []
                if redis_result.status != HealthStatus.HEALTHY:
                    messages.append(f"Redis: {redis_result.message}")
                if postgres_result.status != HealthStatus.HEALTHY:
                    messages.append(f"PostgreSQL: {postgres_result.message}")

                return HealthCheckResult(
                    status=HealthStatus.UNHEALTHY,
                    service_name=self.config.service_name,
                    check_type="database",
                    message="; ".join(messages)
                )

        except Exception as e:
            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                service_name=self.config.service_name,
                check_type="database",
                message=f"Database connection check failed: {e}"
            )