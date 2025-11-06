"""
服务健康检查器

提供多种类型的健康检查功能，包括HTTP检查、数据库连接检查和进程检查。
支持重试机制、超时处理和异步操作。
"""

import asyncio
import aiohttp
import socket
import psutil
from typing import Dict, List, Optional, Any, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
import time
import json
from datetime import datetime, timedelta
import subprocess
import platform

from .service_dependency_analyzer import ServiceInfo, ServiceType, ServiceStatus
from utils.logger import get_logger

logger = get_logger(__name__)


class HealthStatus(Enum):
    """健康状态枚举"""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"
    TIMEOUT = "timeout"
    CONNECTION_ERROR = "connection_error"
    AUTHENTICATION_ERROR = "authentication_error"
    SERVICE_UNAVAILABLE = "service_unavailable"


@dataclass
class HealthCheckResult:
    """健康检查结果"""
    status: HealthStatus
    service_name: str
    check_type: str
    response_time: Optional[float] = None
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    retry_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'status': self.status.value,
            'service_name': self.service_name,
            'check_type': self.check_type,
            'response_time': self.response_time,
            'message': self.message,
            'details': self.details,
            'timestamp': self.timestamp.isoformat(),
            'retry_count': self.retry_count
        }


@dataclass
class HealthCheckConfig:
    """健康检查配置"""
    timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0
    retry_backoff_factor: float = 2.0
    success_threshold: int = 1  # 连续成功次数阈值
    failure_threshold: int = 1  # 连续失败次数阈值
    check_interval: float = 5.0  # 检查间隔（秒）

    # HTTP检查配置
    http_user_agent: str = "ServiceHealthChecker/1.0"
    http_headers: Dict[str, str] = field(default_factory=dict)
    http_verify_ssl: bool = True
    http_follow_redirects: bool = True
    expected_status_codes: List[int] = field(default_factory=lambda: [200, 201, 202])

    # 连接检查配置
    connection_timeout: float = 5.0

    # 进程检查配置
    process_timeout: float = 10.0
    memory_threshold_mb: Optional[float] = None
    cpu_threshold_percent: Optional[float] = None


class HealthChecker:
    """
    服务健康检查器

    功能特性：
    - HTTP健康检查
    - 数据库连接检查
    - 进程健康检查
    - 重试机制和超时处理
    - 异步并发检查
    - 自定义健康检查策略
    """

    def __init__(self, config: Optional[HealthCheckConfig] = None):
        """
        初始化健康检查器

        Args:
            config: 健康检查配置
        """
        self.config = config or HealthCheckConfig()
        self.logger = get_logger(self.__class__.__name__)

        # 健康检查历史记录
        self.check_history: Dict[str, List[HealthCheckResult]] = {}

        # 当前健康状态缓存
        self.health_cache: Dict[str, HealthCheckResult] = {}

        # 检查统计信息
        self.check_stats: Dict[str, Dict[str, Any]] = {}

        self.logger.info("健康检查器初始化完成")

    async def check_http_health(self, endpoint: str, service_name: str = "",
                              headers: Optional[Dict[str, str]] = None,
                              method: str = "GET",
                              expected_status_codes: Optional[List[int]] = None) -> HealthCheckResult:
        """
        执行HTTP健康检查

        Args:
            endpoint: HTTP端点URL
            service_name: 服务名称
            headers: 请求头
            method: HTTP方法
            expected_status_codes: 期望的HTTP状态码

        Returns:
            健康检查结果
        """
        if not service_name:
            service_name = self._extract_service_name_from_url(endpoint)

        start_time = time.time()
        status = HealthStatus.UNKNOWN
        message = ""
        response_time = None
        details = {}

        try:
            # 准备请求头
            request_headers = self.config.http_headers.copy()
            request_headers['User-Agent'] = self.config.http_user_agent
            if headers:
                request_headers.update(headers)

            # 设置期望的状态码
            expected_codes = expected_status_codes or self.config.expected_status_codes

            # 配置超时
            timeout = aiohttp.ClientTimeout(total=self.config.timeout)

            async with aiohttp.ClientSession(
                timeout=timeout,
                connector=aiohttp.TCPConnector(verify_ssl=self.config.http_verify_ssl)
            ) as session:
                async with session.request(
                    method=method,
                    url=endpoint,
                    headers=request_headers,
                    allow_redirects=self.config.http_follow_redirects
                ) as response:
                    response_time = time.time() - start_time

                    # 记录响应详情
                    details = {
                        'status_code': response.status,
                        'headers': dict(response.headers),
                        'url': str(response.url),
                        'method': method
                    }

                    # 尝试读取响应内容（限制大小）
                    try:
                        content = await response.text()
                        if len(content) <= 1000:  # 限制响应内容大小
                            details['response_content'] = content
                        else:
                            details['response_content'] = content[:1000] + '...(truncated)'
                    except Exception as e:
                        self.logger.warning(f"读取响应内容失败: {e}")
                        details['response_content'] = 'Failed to read content'

                    # 判断健康状态
                    if response.status in expected_codes:
                        status = HealthStatus.HEALTHY
                        message = f"HTTP检查成功 (状态码: {response.status}, 响应时间: {response_time:.3f}s)"
                    else:
                        status = HealthStatus.SERVICE_UNAVAILABLE
                        message = f"HTTP检查失败 (状态码: {response.status}, 期望: {expected_codes})"

        except asyncio.TimeoutError:
            response_time = time.time() - start_time
            status = HealthStatus.TIMEOUT
            message = f"HTTP检查超时 (超时时间: {self.config.timeout}s)"
            details['timeout'] = self.config.timeout

        except aiohttp.ClientConnectorError as e:
            response_time = time.time() - start_time
            status = HealthStatus.CONNECTION_ERROR
            message = f"HTTP连接错误: {str(e)}"
            details['connection_error'] = str(e)

        except aiohttp.ClientError as e:
            response_time = time.time() - start_time
            status = HealthStatus.UNHEALTHY
            message = f"HTTP客户端错误: {str(e)}"
            details['client_error'] = str(e)

        except Exception as e:
            response_time = time.time() - start_time
            status = HealthStatus.UNHEALTHY
            message = f"HTTP检查异常: {str(e)}"
            details['exception'] = str(e)

        return HealthCheckResult(
            status=status,
            service_name=service_name,
            check_type="http",
            response_time=response_time,
            message=message,
            details=details
        )

    async def check_connection_health(self, host: str, port: int, service_name: str = "",
                                    timeout: Optional[float] = None) -> HealthCheckResult:
        """
        执行连接健康检查

        Args:
            host: 主机地址
            port: 端口号
            service_name: 服务名称
            timeout: 连接超时时间

        Returns:
            健康检查结果
        """
        if not service_name:
            service_name = f"{host}:{port}"

        start_time = time.time()
        status = HealthStatus.UNKNOWN
        message = ""
        response_time = None
        details = {
            'host': host,
            'port': port,
            'timeout': timeout or self.config.connection_timeout
        }

        try:
            connection_timeout = timeout or self.config.connection_timeout

            # 尝试建立TCP连接
            future = asyncio.open_connection(host, port)
            reader, writer = await asyncio.wait_for(future, timeout=connection_timeout)

            response_time = time.time() - start_time

            # 成功建立连接
            status = HealthStatus.HEALTHY
            message = f"连接检查成功 (响应时间: {response_time:.3f}s)"
            details['local_address'] = writer.get_extra_info('sockname')
            details['remote_address'] = writer.get_extra_info('peername')

            # 关闭连接
            writer.close()
            await writer.wait_closed()

        except asyncio.TimeoutError:
            response_time = time.time() - start_time
            status = HealthStatus.TIMEOUT
            message = f"连接检查超时 (超时时间: {connection_timeout}s)"
            details['timeout_error'] = True

        except ConnectionRefusedError:
            response_time = time.time() - start_time
            status = HealthStatus.CONNECTION_ERROR
            message = f"连接被拒绝 ({host}:{port})"
            details['connection_refused'] = True

        except socket.gaierror as e:
            response_time = time.time() - start_time
            status = HealthStatus.CONNECTION_ERROR
            message = f"DNS解析失败: {str(e)}"
            details['dns_error'] = str(e)

        except OSError as e:
            response_time = time.time() - start_time
            status = HealthStatus.CONNECTION_ERROR
            message = f"网络错误: {str(e)}"
            details['network_error'] = str(e)

        except Exception as e:
            response_time = time.time() - start_time
            status = HealthStatus.UNHEALTHY
            message = f"连接检查异常: {str(e)}"
            details['exception'] = str(e)

        return HealthCheckResult(
            status=status,
            service_name=service_name,
            check_type="connection",
            response_time=response_time,
            message=message,
            details=details
        )

    async def check_process_health(self, process_name: str, service_name: str = "",
                                 command_pattern: Optional[str] = None,
                                 pid: Optional[int] = None) -> HealthCheckResult:
        """
        执行进程健康检查

        Args:
            process_name: 进程名称
            service_name: 服务名称
            command_pattern: 命令行模式匹配
            pid: 进程ID

        Returns:
            健康检查结果
        """
        if not service_name:
            service_name = process_name

        start_time = time.time()
        status = HealthStatus.UNKNOWN
        message = ""
        details = {
            'process_name': process_name,
            'command_pattern': command_pattern,
            'pid': pid
        }

        try:
            processes = []

            if pid:
                # 通过PID查找进程
                try:
                    process = psutil.Process(pid)
                    processes = [process]
                except psutil.NoSuchProcess:
                    processes = []
            else:
                # 通过进程名称或命令模式查找进程
                for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                    try:
                        proc_info = proc.info
                        if (process_name.lower() in proc_info['name'].lower() or
                            (command_pattern and any(command_pattern in cmd for cmd in proc_info['cmdline']))):
                            processes.append(proc)
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue

            if not processes:
                status = HealthStatus.UNHEALTHY
                message = f"未找到进程: {process_name}"
                details['process_count'] = 0
            else:
                # 检查每个找到的进程
                healthy_processes = []
                for proc in processes:
                    try:
                        proc_info = {
                            'pid': proc.pid,
                            'name': proc.name(),
                            'status': proc.status(),
                            'cpu_percent': proc.cpu_percent(),
                            'memory_info': proc.memory_info()._asdict(),
                            'create_time': proc.create_time(),
                            'cmdline': proc.cmdline()
                        }

                        # 检查进程状态
                        if proc.status() == psutil.STATUS_ZOMBIE:
                            continue

                        # 检查CPU使用率阈值
                        if self.config.cpu_threshold_percent:
                            cpu_percent = proc.cpu_percent()
                            if cpu_percent > self.config.cpu_threshold_percent:
                                details['cpu_warning'] = f"CPU使用率过高: {cpu_percent:.1f}%"

                        # 检查内存使用阈值
                        if self.config.memory_threshold_mb:
                            memory_mb = proc.memory_info().rss / 1024 / 1024
                            if memory_mb > self.config.memory_threshold_mb:
                                details['memory_warning'] = f"内存使用过高: {memory_mb:.1f}MB"

                        healthy_processes.append(proc_info)

                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue

                response_time = time.time() - start_time

                if healthy_processes:
                    status = HealthStatus.HEALTHY
                    message = f"进程检查成功 (找到 {len(healthy_processes)} 个健康进程)"
                    details['healthy_processes'] = healthy_processes
                    details['process_count'] = len(healthy_processes)
                else:
                    status = HealthStatus.UNHEALTHY
                    message = f"未找到健康的进程: {process_name}"
                    details['process_count'] = 0

        except Exception as e:
            response_time = time.time() - start_time
            status = HealthStatus.UNHEALTHY
            message = f"进程检查异常: {str(e)}"
            details['exception'] = str(e)

        return HealthCheckResult(
            status=status,
            service_name=service_name,
            check_type="process",
            response_time=response_time,
            message=message,
            details=details
        )

    async def check_service_health(self, service_info: ServiceInfo) -> HealthCheckResult:
        """
        根据服务类型执行相应的健康检查

        Args:
            service_info: 服务信息

        Returns:
            健康检查结果
        """
        self.logger.debug(f"开始健康检查: {service_info.name} (类型: {service_info.service_type.value})")

        result = None

        try:
            if service_info.service_type == ServiceType.BACKEND_API:
                # HTTP健康检查
                if service_info.health_endpoint:
                    endpoint = f"http://{service_info.host}:{service_info.port}{service_info.health_endpoint}"
                    result = await self.check_http_health(endpoint, service_info.name)
                else:
                    # 尝试默认健康检查端点
                    default_endpoints = [
                        f"http://{service_info.host}:{service_info.port}/health",
                        f"http://{service_info.host}:{service_info.port}/api/health",
                        f"http://{service_info.host}:{service_info.port}/status",
                        f"http://{service_info.host}:{service_info.port}/"
                    ]

                    for endpoint in default_endpoints:
                        result = await self.check_http_health(endpoint, service_info.name)
                        if result.status == HealthStatus.HEALTHY:
                            break

            elif service_info.service_type in [ServiceType.DATABASE, ServiceType.CACHE]:
                # 连接健康检查
                if service_info.port:
                    result = await self.check_connection_health(
                        service_info.host, service_info.port, service_info.name
                    )
                else:
                    result = HealthCheckResult(
                        status=HealthStatus.UNKNOWN,
                        service_name=service_info.name,
                        check_type="connection",
                        message="数据库服务未配置端口号"
                    )

            elif service_info.service_type == ServiceType.FRONTEND:
                # 检查前端应用是否运行（通过端口连接）
                if service_info.port:
                    result = await self.check_connection_health(
                        service_info.host, service_info.port, service_info.name
                    )
                else:
                    result = HealthCheckResult(
                        status=HealthStatus.UNKNOWN,
                        service_name=service_info.name,
                        check_type="connection",
                        message="前端服务未配置端口号"
                    )

            else:
                # 通用进程检查
                result = await self.check_process_health(service_info.name, service_info.name)

        except Exception as e:
            self.logger.error(f"健康检查异常: {e}")
            result = HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                service_name=service_info.name,
                check_type="general",
                message=f"健康检查异常: {str(e)}",
                details={'exception': str(e)}
            )

        # 更新缓存和历史记录
        self._update_health_cache(service_info.name, result)

        return result

    async def check_service_health_with_retry(self, service_info: ServiceInfo) -> HealthCheckResult:
        """
        带重试机制的服务健康检查

        Args:
            service_info: 服务信息

        Returns:
            最终健康检查结果
        """
        last_result = None

        for attempt in range(self.config.max_retries + 1):
            result = await self.check_service_health(service_info)
            result.retry_count = attempt

            # 如果检查成功，直接返回
            if result.status == HealthStatus.HEALTHY:
                if attempt > 0:
                    self.logger.info(f"服务 {service_info.name} 在第 {attempt + 1} 次尝试后健康检查通过")
                return result

            last_result = result

            # 如果不是最后一次尝试，等待后重试
            if attempt < self.config.max_retries:
                delay = self.config.retry_delay * (self.config.retry_backoff_factor ** attempt)
                self.logger.warning(f"服务 {service_info.name} 健康检查失败，{delay:.1f}秒后重试 (尝试 {attempt + 1}/{self.config.max_retries + 1})")
                await asyncio.sleep(delay)

        return last_result

    async def check_multiple_services(self, services: List[ServiceInfo]) -> Dict[str, HealthCheckResult]:
        """
        并发检查多个服务的健康状态

        Args:
            services: 服务信息列表

        Returns:
            服务健康检查结果字典
        """
        tasks = []
        for service in services:
            task = asyncio.create_task(self.check_service_health_with_retry(service))
            tasks.append((service.name, task))

        results = {}
        for service_name, task in tasks:
            try:
                result = await task
                results[service_name] = result
            except Exception as e:
                self.logger.error(f"检查服务 {service_name} 健康状态失败: {e}")
                results[service_name] = HealthCheckResult(
                    status=HealthStatus.UNHEALTHY,
                    service_name=service_name,
                    check_type="error",
                    message=f"健康检查执行失败: {str(e)}",
                    details={'exception': str(e)}
                )

        return results

    def _update_health_cache(self, service_name: str, result: HealthCheckResult) -> None:
        """更新健康状态缓存和历史记录"""
        # 更新缓存
        self.health_cache[service_name] = result

        # 更新历史记录
        if service_name not in self.check_history:
            self.check_history[service_name] = []

        self.check_history[service_name].append(result)

        # 限制历史记录长度
        max_history = 100
        if len(self.check_history[service_name]) > max_history:
            self.check_history[service_name] = self.check_history[service_name][-max_history:]

        # 更新统计信息
        if service_name not in self.check_stats:
            self.check_stats[service_name] = {
                'total_checks': 0,
                'healthy_checks': 0,
                'unhealthy_checks': 0,
                'average_response_time': 0.0,
                'last_check_time': result.timestamp,
                'uptime_percentage': 0.0
            }

        stats = self.check_stats[service_name]
        stats['total_checks'] += 1
        stats['last_check_time'] = result.timestamp

        if result.status == HealthStatus.HEALTHY:
            stats['healthy_checks'] += 1
        else:
            stats['unhealthy_checks'] += 1

        # 计算平均响应时间
        if result.response_time is not None:
            total_time = stats['average_response_time'] * (stats['total_checks'] - 1) + result.response_time
            stats['average_response_time'] = total_time / stats['total_checks']

        # 计算可用性百分比
        stats['uptime_percentage'] = (stats['healthy_checks'] / stats['total_checks']) * 100

    def get_health_summary(self) -> Dict[str, Any]:
        """
        获取健康检查摘要

        Returns:
            健康检查摘要信息
        """
        total_services = len(self.health_cache)
        healthy_services = sum(1 for result in self.health_cache.values() if result.status == HealthStatus.HEALTHY)
        unhealthy_services = total_services - healthy_services

        summary = {
            'total_services': total_services,
            'healthy_services': healthy_services,
            'unhealthy_services': unhealthy_services,
            'health_percentage': (healthy_services / total_services * 100) if total_services > 0 else 0,
            'last_check_time': max((result.timestamp for result in self.health_cache.values()), default=datetime.now()),
            'services': {}
        }

        for service_name, result in self.health_cache.items():
            summary['services'][service_name] = {
                'status': result.status.value,
                'check_type': result.check_type,
                'response_time': result.response_time,
                'message': result.message,
                'last_check': result.timestamp.isoformat()
            }

        return summary

    def get_service_health_history(self, service_name: str, limit: int = 50) -> List[HealthCheckResult]:
        """
        获取指定服务的健康检查历史

        Args:
            service_name: 服务名称
            limit: 返回记录数量限制

        Returns:
            健康检查历史记录列表
        """
        history = self.check_history.get(service_name, [])
        return history[-limit:] if limit > 0 else history

    def _extract_service_name_from_url(self, url: str) -> str:
        """从URL中提取服务名称"""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return f"{parsed.hostname}:{parsed.port}" if parsed.port else parsed.hostname or "unknown"
        except Exception:
            return "unknown"

    def clear_cache(self) -> None:
        """清空健康状态缓存"""
        self.health_cache.clear()
        self.logger.info("健康状态缓存已清空")

    def clear_history(self) -> None:
        """清空健康检查历史记录"""
        self.check_history.clear()
        self.check_stats.clear()
        self.logger.info("健康检查历史记录已清空")