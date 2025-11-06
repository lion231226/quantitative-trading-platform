#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
服务管理器 - 系统服务启动和管理

提供完整的服务启动、停止、监控和健康检查功能。
支持服务依赖管理和启动序列控制。
"""

import os
import sys
import asyncio
import subprocess
import time
import socket
import psutil
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

# 服务模块导入
try:
    from services.redis_service_manager import RedisServiceManager, RedisServiceStatus
    from services.database_service import DatabaseService
    from services.backend_service import BackendService
    from services.frontend_service import FrontendService
    SERVICE_MODULES_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Some service modules not available: {e}")
    SERVICE_MODULES_AVAILABLE = False

from utils.logger import get_logger
from utils.config_manager import ConfigManager

logger = get_logger(__name__)
config = ConfigManager()

class ServiceStatus(Enum):
    """服务状态"""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"
    UNKNOWN = "unknown"

class ServiceType(Enum):
    """服务类型"""
    REDIS = "redis"
    DATABASE = "database"
    BACKEND = "backend"
    FRONTEND = "frontend"

@dataclass
class ServiceHealthResult:
    """服务健康检查结果"""
    service_name: str
    is_healthy: bool
    response_time: float
    error_message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

@dataclass
class ServiceStartResult:
    """服务启动结果"""
    service_name: str
    success: bool
    start_time: float
    error_message: Optional[str] = None
    process_id: Optional[int] = None

class ServiceManager:
    """服务管理器主类"""

    def __init__(self):
        """初始化服务管理器"""
        self.service_managers = {}
        self.service_processes = {}
        self.service_status = {}
        self._initialize_service_managers()

    def _initialize_service_managers(self):
        """初始化服务管理器"""
        if not SERVICE_MODULES_AVAILABLE:
            logger.warning("服务模块不可用，使用基础服务管理")
            return

        try:
            # 初始化各个服务管理器
            self.service_managers[ServiceType.REDIS] = RedisServiceManager()
            self.service_managers[ServiceType.DATABASE] = DatabaseService()
            self.service_managers[ServiceType.BACKEND] = BackendService()
            self.service_managers[ServiceType.FRONTEND] = FrontendService()

            logger.info("服务管理器初始化完成")

        except Exception as e:
            logger.error(f"初始化服务管理器出错: {str(e)}")

    async def start_service(self, service_name: str, service_config, progress_tracker=None) -> bool:
        """启动服务"""
        try:
            logger.info(f"正在启动服务: {service_name}")

            # 更新状态
            self.service_status[service_name] = ServiceStatus.STARTING

            start_result = await self._start_service_implementation(
                service_name, service_config, progress_tracker
            )

            if start_result.success:
                self.service_status[service_name] = ServiceStatus.RUNNING
                self.service_processes[service_name] = start_result.process_id
                logger.info(f"服务 {service_name} 启动成功")
                return True
            else:
                self.service_status[service_name] = ServiceStatus.ERROR
                logger.error(f"服务 {service_name} 启动失败: {start_result.error_message}")
                return False

        except Exception as e:
            self.service_status[service_name] = ServiceStatus.ERROR
            logger.error(f"启动服务 {service_name} 出错: {str(e)}")
            return False

    async def _start_service_implementation(self, service_name: str, service_config, progress_tracker=None) -> ServiceStartResult:
        """启动服务具体实现"""
        start_time = time.time()

        try:
            if service_name == "redis":
                return await self._start_redis_service(service_config, progress_tracker)
            elif service_name == "database":
                return await self._start_database_service(service_config, progress_tracker)
            elif service_name == "backend":
                return await self._start_backend_service(service_config, progress_tracker)
            elif service_name == "frontend":
                return await self._start_frontend_service(service_config, progress_tracker)
            else:
                return ServiceStartResult(
                    service_name=service_name,
                    success=False,
                    start_time=0,
                    error_message=f"未知服务类型: {service_name}"
                )

        except Exception as e:
            return ServiceStartResult(
                service_name=service_name,
                success=False,
                start_time=time.time() - start_time,
                error_message=str(e)
            )

    async def _start_redis_service(self, service_config, progress_tracker=None) -> ServiceStartResult:
        """启动 Redis 服务"""
        try:
            if SERVICE_MODULES_AVAILABLE and ServiceType.REDIS in self.service_managers:
                # 使用现有的 Redis 服务管理器
                redis_manager = self.service_managers[ServiceType.REDIS]

                # 检查 Redis 服务状态
                current_status = redis_manager.get_service_status()
                if current_status == RedisServiceStatus.RUNNING:
                    return ServiceStartResult(
                        service_name="redis",
                        success=True,
                        start_time=0,
                        error_message=None
                    )

                # 启动 Redis
                start_success = redis_manager.start_service()

                if start_success:
                    # 等待服务就绪
                    await self._wait_for_service_ready("redis", service_config.port, 30)

                    return ServiceStartResult(
                        service_name="redis",
                        success=True,
                        start_time=0,
                        process_id=self._get_redis_process_id()
                    )
                else:
                    return ServiceStartResult(
                        service_name="redis",
                        success=False,
                        start_time=0,
                        error_message="Redis 启动失败"
                    )
            else:
                # 使用基础启动方法
                return await self._start_service_basic("redis", service_config, ["redis-server"])

        except Exception as e:
            return ServiceStartResult(
                service_name="redis",
                success=False,
                start_time=0,
                error_message=str(e)
            )

    async def _start_database_service(self, service_config, progress_tracker=None) -> ServiceStartResult:
        """启动数据库服务"""
        try:
            if SERVICE_MODULES_AVAILABLE and ServiceType.DATABASE in self.service_managers:
                # 使用现有的数据库服务管理器
                db_service = self.service_managers[ServiceType.DATABASE]

                # 启动数据库
                start_success = db_service.start_service()

                if start_success:
                    # 等待服务就绪
                    await self._wait_for_service_ready("database", service_config.port, 60)

                    return ServiceStartResult(
                        service_name="database",
                        success=True,
                        start_time=0,
                        process_id=self._get_database_process_id()
                    )
                else:
                    return ServiceStartResult(
                        service_name="database",
                        success=False,
                        start_time=0,
                        error_message="数据库启动失败"
                    )
            else:
                # 使用基础启动方法
                return await self._start_service_basic("database", service_config, ["postgres"])

        except Exception as e:
            return ServiceStartResult(
                service_name="database",
                success=False,
                start_time=0,
                error_message=str(e)
            )

    async def _start_backend_service(self, service_config, progress_tracker=None) -> ServiceStartResult:
        """启动后端服务"""
        try:
            backend_path = service_config.path
            if not backend_path:
                return ServiceStartResult(
                    service_name="backend",
                    success=False,
                    start_time=0,
                    error_message="后端路径未配置"
                )

            if SERVICE_MODULES_AVAILABLE and ServiceType.BACKEND in self.service_managers:
                # 使用现有的后端服务管理器
                backend_service = self.service_managers[ServiceType.BACKEND]

                # 启动后端
                start_success = backend_service.start_service()

                if start_success:
                    # 等待服务就绪
                    await self._wait_for_service_ready("backend", service_config.port, 60)

                    return ServiceStartResult(
                        service_name="backend",
                        success=True,
                        start_time=0,
                        process_id=self._get_backend_process_id()
                    )
                else:
                    return ServiceStartResult(
                        service_name="backend",
                        success=False,
                        start_time=0,
                        error_message="后端启动失败"
                    )
            else:
                # 使用基础启动方法
                return await self._start_service_basic(
                    "backend",
                    service_config,
                    ["python", backend_path]
                )

        except Exception as e:
            return ServiceStartResult(
                service_name="backend",
                success=False,
                start_time=0,
                error_message=str(e)
            )

    async def _start_frontend_service(self, service_config, progress_tracker=None) -> ServiceStartResult:
        """启动前端服务"""
        try:
            frontend_path = service_config.path
            if not frontend_path:
                return ServiceStartResult(
                    service_name="frontend",
                    success=False,
                    start_time=0,
                    error_message="前端路径未配置"
                )

            if SERVICE_MODULES_AVAILABLE and ServiceType.FRONTEND in self.service_managers:
                # 使用现有的前端服务管理器
                frontend_service = self.service_managers[ServiceType.FRONTEND]

                # 启动前端
                start_success = frontend_service.start_service()

                if start_success:
                    # 等待服务就绪
                    await self._wait_for_service_ready("frontend", service_config.port, 120)

                    return ServiceStartResult(
                        service_name="frontend",
                        success=True,
                        start_time=0,
                        process_id=self._get_frontend_process_id()
                    )
                else:
                    return ServiceStartResult(
                        service_name="frontend",
                        success=False,
                        start_time=0,
                        error_message="前端启动失败"
                    )
            else:
                # 使用基础启动方法
                return await self._start_service_basic(
                    "frontend",
                    service_config,
                    ["npm", "start"],
                    cwd=frontend_path
                )

        except Exception as e:
            return ServiceStartResult(
                service_name="frontend",
                success=False,
                start_time=0,
                error_message=str(e)
            )

    async def _start_service_basic(self, service_name: str, service_config, command: List[str], cwd: str = None) -> ServiceStartResult:
        """基础服务启动方法"""
        try:
            # 检查端口是否可用
            port = service_config.port
            if self._is_port_available(port):
                # 启动服务
                process = await asyncio.create_subprocess_exec(
                    *command,
                    cwd=cwd or os.getcwd(),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )

                # 等待服务启动
                await self._wait_for_service_ready(service_name, port, 30)

                return ServiceStartResult(
                    service_name=service_name,
                    success=True,
                    start_time=0,
                    process_id=process.pid
                )
            else:
                return ServiceStartResult(
                    service_name=service_name,
                    success=False,
                    start_time=0,
                    error_message=f"端口 {port} 已被占用"
                )

        except Exception as e:
            return ServiceStartResult(
                service_name=service_name,
                success=False,
                start_time=0,
                error_message=str(e)
            )

    async def _wait_for_service_ready(self, service_name: str, port: int, timeout: int):
        """等待服务就绪"""
        start_time = time.time()

        while time.time() - start_time < timeout:
            if await self._check_service_availability(service_name, port):
                logger.info(f"服务 {service_name} 已就绪")
                return True

            await asyncio.sleep(2)

        logger.warning(f"服务 {service_name} 在 {timeout} 秒内未就绪")
        return False

    async def _check_service_availability(self, service_name: str, port: int) -> bool:
        """检查服务可用性"""
        try:
            # 基础端口检查
            if not self._is_port_available(port):
                # 尝试连接
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)
                result = sock.connect_ex(('localhost', port))
                sock.close()
                return result == 0

            return False

        except Exception as e:
            logger.error(f"检查服务 {service_name} 可用性出错: {str(e)}")
            return False

    def _is_port_available(self, port: int) -> bool:
        """检查端口是否可用"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('localhost', port))
            sock.close()
            return result != 0
        except Exception:
            return True

    def _get_redis_process_id(self) -> Optional[int]:
        """获取 Redis 进程 ID"""
        try:
            for proc in psutil.process_iter(['pid', 'name']):
                if 'redis' in proc.info['name'].lower():
                    return proc.info['pid']
            return None
        except Exception:
            return None

    def _get_database_process_id(self) -> Optional[int]:
        """获取数据库进程 ID"""
        try:
            for proc in psutil.process_iter(['pid', 'name']):
                if 'postgres' in proc.info['name'].lower():
                    return proc.info['pid']
            return None
        except Exception:
            return None

    def _get_backend_process_id(self) -> Optional[int]:
        """获取后端进程 ID"""
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                if proc.info['cmdline'] and 'main.py' in ' '.join(proc.info['cmdline']):
                    return proc.info['pid']
            return None
        except Exception:
            return None

    def _get_frontend_process_id(self) -> Optional[int]:
        """获取前端进程 ID"""
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                if proc.info['cmdline'] and 'npm' in ' '.join(proc.info['cmdline']):
                    return proc.info['pid']
            return None
        except Exception:
            return None

    async def stop_service(self, service_name: str) -> bool:
        """停止服务"""
        try:
            logger.info(f"正在停止服务: {service_name}")

            self.service_status[service_name] = ServiceStatus.STOPPING

            if service_name in self.service_processes:
                process_id = self.service_processes[service_name]
                if process_id:
                    # 终止进程
                    try:
                        proc = psutil.Process(process_id)
                        proc.terminate()
                        proc.wait(timeout=10)
                    except psutil.NoSuchProcess:
                        pass
                    except psutil.TimeoutExpired:
                        proc.kill()

            self.service_status[service_name] = ServiceStatus.STOPPED
            del self.service_processes[service_name]

            logger.info(f"服务 {service_name} 已停止")
            return True

        except Exception as e:
            logger.error(f"停止服务 {service_name} 出错: {str(e)}")
            self.service_status[service_name] = ServiceStatus.ERROR
            return False

    async def health_check(self, service_name: str) -> ServiceHealthResult:
        """服务健康检查"""
        start_time = time.time()

        try:
            if service_name not in self.service_status:
                return ServiceHealthResult(
                    service_name=service_name,
                    is_healthy=False,
                    response_time=time.time() - start_time,
                    error_message="服务未找到"
                )

            # 检查服务状态
            status = self.service_status[service_name]
            if status != ServiceStatus.RUNNING:
                return ServiceHealthResult(
                    service_name=service_name,
                    is_healthy=False,
                    response_time=time.time() - start_time,
                    error_message=f"服务状态异常: {status}"
                )

            # 检查进程是否存在
            if service_name in self.service_processes:
                process_id = self.service_processes[service_name]
                if process_id and not psutil.pid_exists(process_id):
                    return ServiceHealthResult(
                        service_name=service_name,
                        is_healthy=False,
                        response_time=time.time() - start_time,
                        error_message="服务进程不存在"
                    )

            # 服务健康
            return ServiceHealthResult(
                service_name=service_name,
                is_healthy=True,
                response_time=time.time() - start_time,
                details={"status": status}
            )

        except Exception as e:
            return ServiceHealthResult(
                service_name=service_name,
                is_healthy=False,
                response_time=time.time() - start_time,
                error_message=str(e)
            )

    async def start_all_services(self, service_configs: Dict[str, Any], progress_tracker=None) -> Dict[str, bool]:
        """按顺序启动所有服务"""
        results = {}

        # 服务启动顺序：Redis -> Database -> Backend -> Frontend
        startup_order = ["redis", "database", "backend", "frontend"]

        for service_name in startup_order:
            if service_name in service_configs:
                if progress_tracker:
                    progress_tracker.update_progress(
                        f"正在启动 {service_name} 服务...",
                        progress=startup_order.index(service_name) / len(startup_order) * 100
                    )

                success = await self.start_service(service_name, service_configs[service_name], progress_tracker)
                results[service_name] = success

                if not success:
                    logger.error(f"服务 {service_name} 启动失败，停止后续服务启动")
                    break

        return results

    async def stop_all_services(self) -> Dict[str, bool]:
        """停止所有服务"""
        results = {}

        # 按相反顺序停止服务：Frontend -> Backend -> Database -> Redis
        stop_order = ["frontend", "backend", "database", "redis"]

        for service_name in stop_order:
            if service_name in self.service_status:
                success = await self.stop_service(service_name)
                results[service_name] = success

        return results

    def get_service_status(self, service_name: str) -> ServiceStatus:
        """获取服务状态"""
        return self.service_status.get(service_name, ServiceStatus.UNKNOWN)

    def get_all_services_status(self) -> Dict[str, ServiceStatus]:
        """获取所有服务状态"""
        return self.service_status.copy()