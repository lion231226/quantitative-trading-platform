#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强服务编排器 - 智能服务启动和依赖管理

提供增强的服务启动序列控制、智能健康检查、
依赖等待机制和详细错误诊断功能。
"""

import os
import sys
import asyncio
import subprocess
import time
import socket
import json
import psutil
import platform
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import requests
from datetime import datetime

# 导入项目模块
from utils.logger import get_logger
from utils.config_manager import ConfigManager

logger = get_logger(__name__)
config = ConfigManager()

class ServiceStatus(Enum):
    """服务状态"""
    NOT_STARTED = "not_started"
    STARTING = "starting"
    HEALTH_CHECKING = "health_checking"
    READY = "ready"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"
    TIMEOUT = "timeout"
    DEPENDENCY_FAILED = "dependency_failed"

class HealthCheckType(Enum):
    """健康检查类型"""
    PORT_CONNECT = "port_connect"
    HTTP_ENDPOINT = "http_endpoint"
    TCP_PING = "tcp_ping"
    CUSTOM_CHECK = "custom_check"

@dataclass
class HealthCheckConfig:
    """健康检查配置"""
    check_type: HealthCheckType
    endpoint: Optional[str] = None
    expected_status: int = 200
    timeout: int = 5
    retry_count: int = 3
    retry_delay: float = 2.0
    custom_check: Optional[Callable] = None

@dataclass
class ServiceConfig:
    """增强的服务配置"""
    name: str
    service_type: str
    port: int
    host: str = "localhost"
    required: bool = True
    startup_timeout: int = 120
    health_check: Optional[HealthCheckConfig] = None
    dependencies: List[str] = None
    startup_command: Optional[List[str]] = None
    working_directory: Optional[str] = None
    env_vars: Dict[str, str] = None
    readiness_checks: List[Callable] = None

    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []
        if self.env_vars is None:
            self.env_vars = {}
        if self.readiness_checks is None:
            self.readiness_checks = []

@dataclass
class ServiceStartupResult:
    """服务启动结果"""
    service_name: str
    success: bool
    status: ServiceStatus
    start_time: float
    process_id: Optional[int] = None
    error_message: Optional[str] = None
    diagnostics: Optional[Dict[str, Any]] = None
    health_check_results: List[Dict[str, Any]] = None

    def __post_init__(self):
        if self.health_check_results is None:
            self.health_check_results = []
        if self.diagnostics is None:
            self.diagnostics = {}

@dataclass
class DependencyWaitResult:
    """依赖等待结果"""
    dependency_name: str
    success: bool
    wait_time: float
    error_message: Optional[str] = None

class EnhancedServiceOrchestrator:
    """增强的服务编排器"""

    def __init__(self):
        """初始化服务编排器"""
        self.service_processes = {}
        self.service_status = {}
        self.service_config = {}
        self.startup_history = []
        self._setup_default_config()

    def _setup_default_config(self):
        """设置默认配置"""
        # 从配置文件读取默认值
        self.default_timeout = config.get("default", "service_start_timeout", 120)
        self.health_check_timeout = config.get("default", "health_check_timeout", 30)
        self.max_retry_count = config.get("default", "max_retry_count", 3)
        self.retry_delay = config.get("default", "retry_delay", 5)

    async def start_services(self, service_configs: Dict[str, ServiceConfig]) -> Dict[str, ServiceStartupResult]:
        """启动所有服务"""
        results = {}
        startup_order = self._calculate_startup_order(service_configs)

        logger.info(f"开始启动服务，顺序: {' → '.join(startup_order)}")

        for service_name in startup_order:
            if service_name in service_configs:
                service_cfg = service_configs[service_name]

                # 检查依赖
                if not await self._wait_for_dependencies(service_cfg, results):
                    if service_cfg.required:
                        results[service_name] = ServiceStartupResult(
                            service_name=service_name,
                            success=False,
                            status=ServiceStatus.DEPENDENCY_FAILED,
                            start_time=0,
                            error_message=f"必需服务 {service_name} 的依赖启动失败"
                        )
                        break
                    else:
                        logger.warning(f"可选服务 {service_name} 的依赖失败，跳过此服务")
                        results[service_name] = ServiceStartupResult(
                            service_name=service_name,
                            success=False,
                            status=ServiceStatus.DEPENDENCY_FAILED,
                            start_time=0,
                            error_message=f"可选服务 {service_name} 的依赖启动失败，但跳过此服务继续启动"
                        )
                        # 继续下一个服务，不中断流程
                        continue

                # 启动服务
                result = await self.start_single_service(service_name, service_cfg)
                results[service_name] = result

                if not result.success:
                    if service_cfg.required:
                        logger.error(f"必需服务 {service_name} 启动失败，停止后续服务启动")
                        break
                    else:
                        logger.warning(f"可选服务 {service_name} 启动失败，继续启动其他服务")
                        # 继续启动其他服务，不中断流程

        self.startup_history.append({
            "timestamp": datetime.now().isoformat(),
            "results": {name: asdict(result) for name, result in results.items()}
        })

        return results

    async def start_single_service(self, service_name: str, service_config: ServiceConfig) -> ServiceStartupResult:
        """启动单个服务"""
        start_time = time.time()

        logger.info(f"启动服务: {service_name}")
        self.service_status[service_name] = ServiceStatus.STARTING
        self.service_config[service_name] = service_config

        try:
            # 启动服务进程
            process = await self._start_service_process(service_config)
            if not process:
                return ServiceStartupResult(
                    service_name=service_name,
                    success=False,
                    status=ServiceStatus.ERROR,
                    start_time=time.time() - start_time,
                    error_message="无法启动服务进程"
                )

            self.service_processes[service_name] = process

            # 等待服务就绪
            ready_result = await self._wait_for_service_ready(service_name, service_config)

            if ready_result:
                self.service_status[service_name] = ServiceStatus.READY
                logger.info(f"服务 {service_name} 启动成功 (PID: {process.pid})")

                return ServiceStartupResult(
                    service_name=service_name,
                    success=True,
                    status=ServiceStatus.READY,
                    start_time=time.time() - start_time,
                    process_id=process.pid,
                    diagnostics={
                        "port": service_config.port,
                        "host": service_config.host,
                        "startup_time": time.time() - start_time
                    }
                )
            else:
                # 停止失败的服务
                await self.stop_service(service_name)
                return ServiceStartupResult(
                    service_name=service_name,
                    success=False,
                    status=ServiceStatus.TIMEOUT,
                    start_time=time.time() - start_time,
                    error_message=f"服务在 {service_config.startup_timeout} 秒内未能就绪",
                    diagnostics=await self._collect_service_diagnostics(service_name, service_config)
                )

        except Exception as e:
            logger.error(f"启动服务 {service_name} 时发生异常: {str(e)}")
            return ServiceStartupResult(
                service_name=service_name,
                success=False,
                status=ServiceStatus.ERROR,
                start_time=time.time() - start_time,
                error_message=str(e),
                diagnostics=await self._collect_service_diagnostics(service_name, service_config)
            )

    async def _start_service_process(self, service_config: ServiceConfig) -> Optional[subprocess.Popen]:
        """启动服务进程"""
        try:
            if service_config.startup_command:
                # 使用自定义启动命令
                cmd = service_config.startup_command
                cwd = service_config.working_directory
                env = os.environ.copy()
                env.update(service_config.env_vars)

                logger.debug(f"启动命令: {' '.join(cmd)}, 工作目录: {cwd}")

                process = subprocess.Popen(
                    cmd,
                    cwd=cwd,
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )

                return process
            else:
                # 使用默认服务启动方法
                return await self._start_default_service(service_config)

        except Exception as e:
            logger.error(f"启动服务进程失败: {str(e)}")
            return None

    async def _start_default_service(self, service_config: ServiceConfig) -> Optional[subprocess.Popen]:
        """默认服务启动方法"""
        service_type = service_config.service_type

        if service_type == "redis":
            # Redis服务启动
            return await self._start_redis_service(service_config)
        elif service_type == "backend":
            # 后端服务启动
            return await self._start_backend_service(service_config)
        elif service_type == "frontend":
            # 前端服务启动
            return await self._start_frontend_service(service_config)
        else:
            logger.error(f"未知的服务类型: {service_type}")
            return None

    async def _start_redis_service(self, service_config: ServiceConfig) -> Optional[subprocess.Popen]:
        """启动Redis服务"""
        try:
            # 检查Redis是否已经运行
            if await self._check_redis_running(service_config.port):
                logger.info("Redis服务已在运行")
                return None

            # Windows Redis启动逻辑
            if platform.system() == "Windows":
                redis_cmd = "redis-server.exe"
            else:
                redis_cmd = "redis-server"

            process = subprocess.Popen(
                [redis_cmd],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            return process

        except Exception as e:
            logger.error(f"启动Redis服务失败: {str(e)}")
            return None

    async def _start_backend_service(self, service_config: ServiceConfig) -> Optional[subprocess.Popen]:
        """启动后端服务"""
        try:
            backend_path = config.get("paths", "backend_path", "../backend")
            backend_path = os.path.abspath(backend_path)

            if not os.path.exists(os.path.join(backend_path, "main.py")):
                logger.error(f"后端main.py文件不存在: {backend_path}")
                return None

            process = subprocess.Popen(
                [sys.executable, "main.py"],
                cwd=backend_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            return process

        except Exception as e:
            logger.error(f"启动后端服务失败: {str(e)}")
            return None

    async def _start_frontend_service(self, service_config: ServiceConfig) -> Optional[subprocess.Popen]:
        """启动前端服务"""
        try:
            frontend_path = config.get("paths", "frontend_path", "../frontend")
            frontend_path = os.path.abspath(frontend_path)

            # 检查Node.js和npm
            npm_cmd = "npm.cmd" if platform.system() == "Windows" else "npm"

            # 检查依赖是否已安装
            node_modules_path = os.path.join(frontend_path, "node_modules")
            if not os.path.exists(node_modules_path):
                logger.info("安装前端依赖...")
                install_process = subprocess.run(
                    [npm_cmd, "install"],
                    cwd=frontend_path,
                    capture_output=True,
                    text=True,
                    timeout=300
                )
                if install_process.returncode != 0:
                    logger.error(f"npm install失败: {install_process.stderr}")
                    return None

            # 启动前端服务
            process = subprocess.Popen(
                [npm_cmd, "run", "dev"],
                cwd=frontend_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            return process

        except Exception as e:
            logger.error(f"启动前端服务失败: {str(e)}")
            return None

    async def _wait_for_service_ready(self, service_name: str, service_config: ServiceConfig) -> bool:
        """等待服务就绪"""
        timeout = service_config.startup_timeout
        start_time = time.time()

        logger.info(f"等待服务 {service_name} 就绪 (超时: {timeout}s)")

        while time.time() - start_time < timeout:
            try:
                # 执行健康检查
                if await self._perform_health_check(service_config):
                    logger.info(f"服务 {service_name} 健康检查通过")

                    # 执行自定义就绪检查
                    if await self._perform_readiness_checks(service_config):
                        logger.info(f"服务 {service_name} 就绪检查通过")
                        return True

                await asyncio.sleep(2)

            except Exception as e:
                logger.debug(f"健康检查异常: {str(e)}")
                await asyncio.sleep(1)

        logger.warning(f"服务 {service_name} 就绪等待超时")
        return False

    async def _perform_health_check(self, service_config: ServiceConfig) -> bool:
        """执行健康检查"""
        if not service_config.health_check:
            # 默认端口连接检查
            return await self._check_port_connection(service_config.host, service_config.port)

        health_config = service_config.health_check

        for attempt in range(health_config.retry_count):
            try:
                if health_config.check_type == HealthCheckType.PORT_CONNECT:
                    return await self._check_port_connection(
                        health_config.endpoint or service_config.host,
                        service_config.port,
                        health_config.timeout
                    )

                elif health_config.check_type == HealthCheckType.HTTP_ENDPOINT:
                    return await self._check_http_endpoint(
                        health_config.endpoint,
                        health_config.expected_status,
                        health_config.timeout
                    )

                elif health_config.check_type == HealthCheckType.CUSTOM_CHECK:
                    if health_config.custom_check:
                        return await health_config.custom_check(service_config)

                break

            except Exception as e:
                logger.debug(f"健康检查尝试 {attempt + 1} 失败: {str(e)}")
                if attempt < health_config.retry_count - 1:
                    await asyncio.sleep(health_config.retry_delay)

        return False

    async def _perform_readiness_checks(self, service_config: ServiceConfig) -> bool:
        """执行就绪检查"""
        for check_func in service_config.readiness_checks:
            try:
                if not await check_func(service_config):
                    logger.debug(f"就绪检查失败: {check_func.__name__}")
                    return False
            except Exception as e:
                logger.debug(f"就绪检查异常: {check_func.__name__}: {str(e)}")
                return False

        return True

    async def _check_port_connection(self, host: str, port: int, timeout: int = 5) -> bool:
        """检查端口连接"""
        try:
            future = asyncio.open_connection(host, port)
            reader, writer = await asyncio.wait_for(future, timeout=timeout)
            writer.close()
            await writer.wait_closed()
            return True
        except Exception:
            return False

    async def _check_http_endpoint(self, endpoint: str, expected_status: int = 200, timeout: int = 5) -> bool:
        """检查HTTP端点"""
        try:
            response = requests.get(endpoint, timeout=timeout)
            return response.status_code == expected_status
        except Exception:
            return False

    async def _check_redis_running(self, port: int) -> bool:
        """检查Redis是否运行"""
        try:
            import redis
            r = redis.Redis(host='localhost', port=port, db=0, socket_connect_timeout=2)
            r.ping()
            return True
        except Exception:
            return False

    async def _wait_for_dependencies(self, service_config: ServiceConfig, results: Dict[str, ServiceStartupResult]) -> bool:
        """等待依赖服务"""
        if not service_config.dependencies:
            return True

        logger.info(f"等待服务 {service_config.name} 的依赖: {', '.join(service_config.dependencies)}")

        for dep_name in service_config.dependencies:
            if dep_name not in results or not results[dep_name].success:
                logger.error(f"依赖服务 {dep_name} 启动失败")
                return False

            # 等待依赖服务完全就绪
            dep_config = self.service_config.get(dep_name)
            if dep_config:
                wait_time = 0
                max_wait = 30

                while wait_time < max_wait:
                    if await self._perform_health_check(dep_config):
                        logger.info(f"依赖服务 {dep_name} 已就绪")
                        break

                    await asyncio.sleep(2)
                    wait_time += 2
                else:
                    logger.error(f"依赖服务 {dep_name} 在 {max_wait}s 内未就绪")
                    return False

        return True

    def _calculate_startup_order(self, service_configs: Dict[str, ServiceConfig]) -> List[str]:
        """计算服务启动顺序"""
        # 基础启动顺序
        base_order = ["redis", "database", "backend", "frontend"]

        # 根据依赖关系调整顺序
        ordered = []
        remaining = list(service_configs.keys())

        while remaining:
            added_in_iteration = False

            for service_name in remaining[:]:
                service_config = service_configs[service_name]

                # 检查所有依赖是否已添加
                if all(dep in ordered for dep in service_config.dependencies):
                    ordered.append(service_name)
                    remaining.remove(service_name)
                    added_in_iteration = True

            if not added_in_iteration:
                # 循环依赖或缺失依赖，按基础顺序添加
                for service_name in base_order:
                    if service_name in remaining:
                        ordered.append(service_name)
                        remaining.remove(service_name)
                        break

        return ordered

    async def _collect_service_diagnostics(self, service_name: str, service_config: ServiceConfig) -> Dict[str, Any]:
        """收集服务诊断信息"""
        diagnostics = {
            "service_name": service_name,
            "timestamp": datetime.now().isoformat(),
            "config": asdict(service_config),
            "system_info": {}
        }

        try:
            # 端口状态
            diagnostics["port_status"] = await self._check_port_status(service_config.host, service_config.port)

            # 进程状态
            if service_name in self.service_processes:
                process = self.service_processes[service_name]
                if process:
                    diagnostics["process_info"] = {
                        "pid": process.pid,
                        "returncode": process.poll(),
                        "running": process.poll() is None
                    }

            # 系统信息
            diagnostics["system_info"] = {
                "platform": platform.system(),
                "python_version": platform.python_version(),
                "available_memory": psutil.virtual_memory().available // (1024**3) if psutil else "unknown"
            }

            # 网络连接测试
            diagnostics["network_test"] = await self._test_network_connectivity(service_config.host, service_config.port)

        except Exception as e:
            diagnostics["diagnostic_error"] = str(e)

        return diagnostics

    async def _check_port_status(self, host: str, port: int) -> Dict[str, Any]:
        """检查端口状态"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex((host, port))
            sock.close()

            return {
                "host": host,
                "port": port,
                "connectable": result == 0,
                "error_code": result
            }
        except Exception as e:
            return {
                "host": host,
                "port": port,
                "connectable": False,
                "error": str(e)
            }

    async def _test_network_connectivity(self, host: str, port: int) -> Dict[str, Any]:
        """测试网络连接"""
        try:
            start_time = time.time()
            result = await self._check_port_connection(host, port, 5)
            response_time = time.time() - start_time

            return {
                "host": host,
                "port": port,
                "connected": result,
                "response_time": response_time
            }
        except Exception as e:
            return {
                "host": host,
                "port": port,
                "connected": False,
                "error": str(e)
            }

    async def stop_service(self, service_name: str) -> bool:
        """停止服务"""
        try:
            if service_name in self.service_processes:
                process = self.service_processes[service_name]
                if process and process.poll() is None:
                    logger.info(f"停止服务: {service_name}")
                    process.terminate()

                    try:
                        process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()

                    self.service_status[service_name] = ServiceStatus.STOPPED
                    del self.service_processes[service_name]

                    logger.info(f"服务 {service_name} 已停止")
                    return True

            return False

        except Exception as e:
            logger.error(f"停止服务 {service_name} 失败: {str(e)}")
            return False

    async def stop_all_services(self) -> Dict[str, bool]:
        """停止所有服务"""
        results = {}

        # 按相反顺序停止服务
        stop_order = list(reversed(list(self.service_processes.keys())))

        for service_name in stop_order:
            results[service_name] = await self.stop_service(service_name)

        return results

    def get_service_status(self, service_name: str) -> ServiceStatus:
        """获取服务状态"""
        return self.service_status.get(service_name, ServiceStatus.NOT_STARTED)

    def get_all_services_status(self) -> Dict[str, ServiceStatus]:
        """获取所有服务状态"""
        return self.service_status.copy()

    def get_startup_history(self) -> List[Dict[str, Any]]:
        """获取启动历史"""
        return self.startup_history.copy()

# 便利函数
def create_enhanced_service_configs() -> Dict[str, ServiceConfig]:
    """创建增强的服务配置"""
    return {
        "redis": ServiceConfig(
            name="Redis",
            service_type="redis",
            port=6379,
            required=False,  # Redis可选，后端有内存缓存回退机制
            startup_timeout=30,
            health_check=HealthCheckConfig(
                check_type=HealthCheckType.CUSTOM_CHECK,
                timeout=5,
                retry_count=3
            )
        ),

        "backend": ServiceConfig(
            name="Backend",
            service_type="backend",
            port=8000,
            required=True,
            startup_timeout=60,
            dependencies=[],  # 移除Redis依赖，后端有回退机制
            health_check=HealthCheckConfig(
                check_type=HealthCheckType.HTTP_ENDPOINT,
                endpoint="http://localhost:8000/health",
                expected_status=200,
                timeout=5,
                retry_count=5
            )
        ),

        "frontend": ServiceConfig(
            name="Frontend",
            service_type="frontend",
            port=3000,
            required=True,
            startup_timeout=120,
            dependencies=["backend"],
            health_check=HealthCheckConfig(
                check_type=HealthCheckType.PORT_CONNECT,
                timeout=5,
                retry_count=10
            )
        )
    }