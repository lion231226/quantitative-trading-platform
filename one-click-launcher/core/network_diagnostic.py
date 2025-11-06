#!/usr/bin/env python3
"""
网络连接和服务可用性诊断模块

提供跨平台的网络连接检测、服务可用性检查、DNS解析验证等功能。
"""

import asyncio
import socket
import subprocess
import platform
import time
from typing import Dict, List, Optional, Tuple, Union, Any
from dataclasses import dataclass, field
from enum import Enum
import urllib.request
import urllib.error
import urllib.parse
import json
import ipaddress
from concurrent.futures import ThreadPoolExecutor, as_completed

from utils.logger import get_logger
from utils.progress_tracker import ProgressTracker

logger = get_logger(__name__)


class NetworkStatus(Enum):
    """网络状态枚举"""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    PARTIAL = "partial"
    UNKNOWN = "unknown"


class ServiceStatus(Enum):
    """服务状态枚举"""
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    TIMEOUT = "timeout"
    ERROR = "error"
    UNKNOWN = "unknown"


class ConnectionType(Enum):
    """连接类型枚举"""
    TCP = "tcp"
    UDP = "udp"
    HTTP = "http"
    HTTPS = "https"
    PING = "ping"
    DNS = "dns"


@dataclass
class NetworkInterface:
    """网络接口信息"""
    name: str
    is_up: bool
    ip_addresses: List[str] = field(default_factory=list)
    mac_address: Optional[str] = None
    netmask: Optional[str] = None
    gateway: Optional[str] = None


@dataclass
class ConnectivityResult:
    """连接测试结果"""
    target: str
    connection_type: ConnectionType
    status: NetworkStatus
    response_time: Optional[float] = None
    error_message: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ServiceCheckResult:
    """服务检查结果"""
    service_name: str
    host: str
    port: Optional[int] = None
    status: ServiceStatus = ServiceStatus.UNKNOWN
    response_time: Optional[float] = None
    error_message: Optional[str] = None
    http_status: Optional[int] = None
    content_length: Optional[int] = None
    headers: Dict[str, str] = field(default_factory=dict)
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DNSResult:
    """DNS解析结果"""
    domain: str
    record_type: str
    status: NetworkStatus
    resolved_addresses: List[str] = field(default_factory=list)
    response_time: Optional[float] = None
    error_message: Optional[str] = None
    dns_server: Optional[str] = None


@dataclass
class NetworkDiagnosticResult:
    """网络诊断结果"""
    timestamp: str
    overall_status: NetworkStatus
    interfaces: List[NetworkInterface] = field(default_factory=list)
    connectivity_tests: List[ConnectivityResult] = field(default_factory=list)
    service_checks: List[ServiceCheckResult] = field(default_factory=list)
    dns_tests: List[DNSResult] = field(default_factory=list)
    issues: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)


class NetworkDiagnostic:
    """网络诊断器"""

    def __init__(self, progress_tracker: Optional[ProgressTracker] = None):
        self.progress_tracker = progress_tracker
        self.platform = platform.system().lower()
        self.executor = ThreadPoolExecutor(max_workers=10)

    def _log(self, message: str, level: str = "info"):
        """记录日志"""
        if self.progress_tracker:
            self.progress_tracker._log(message)
        else:
            getattr(logger, level)(message)

    async def get_network_interfaces(self) -> List[NetworkInterface]:
        """获取网络接口信息"""
        self._log("Getting network interfaces")

        interfaces = []

        try:
            if self.platform == "windows":
                interfaces = await self._get_windows_interfaces()
            else:
                interfaces = await self._get_unix_interfaces()
        except Exception as e:
            self._log(f"Error getting network interfaces: {e}", "error")

        return interfaces

    async def _get_windows_interfaces(self) -> List[NetworkInterface]:
        """获取Windows网络接口"""
        interfaces = []

        try:
            # 使用 ipconfig 命令获取网络接口信息
            result = subprocess.run(
                ['ipconfig', '/all'],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                interfaces = self._parse_windows_ipconfig(result.stdout)
        except Exception as e:
            self._log(f"Error getting Windows interfaces: {e}", "error")

        return interfaces

    async def _get_unix_interfaces(self) -> List[NetworkInterface]:
        """获取Unix/Linux网络接口"""
        interfaces = []

        try:
            # 使用 ifconfig 或 ip 命令获取网络接口信息
            for cmd in [['ifconfig'], ['ip', 'addr', 'show']]:
                try:
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=10
                    )

                    if result.returncode == 0:
                        if 'ifconfig' in cmd:
                            interfaces = self._parse_ifconfig(result.stdout)
                        else:
                            interfaces = self._parse_ip_addr(result.stdout)
                        break
                except FileNotFoundError:
                    continue

        except Exception as e:
            self._log(f"Error getting Unix interfaces: {e}", "error")

        return interfaces

    def _parse_windows_ipconfig(self, output: str) -> List[NetworkInterface]:
        """解析Windows ipconfig输出"""
        interfaces = []
        current_adapter = None

        for line in output.split('\n'):
            line = line.strip()

            # 适配器名称
            if line.startswith('adapter '):
                if current_adapter:
                    interfaces.append(current_adapter)
                adapter_name = line.split('adapter ')[1].rstrip(':')
                current_adapter = NetworkInterface(name=adapter_name, is_up=True)

            # IP地址
            elif line.startswith('IPv4 Address') and current_adapter:
                ip = line.split(': ')[1]
                current_adapter.ip_addresses.append(ip)

            # MAC地址
            elif line.startswith('Physical Address') and current_adapter:
                mac = line.split(': ')[1]
                current_adapter.mac_address = mac

            # 默认网关
            elif line.startswith('Default Gateway') and current_adapter:
                gateway = line.split(': ')[1]
                if gateway:
                    current_adapter.gateway = gateway

        if current_adapter:
            interfaces.append(current_adapter)

        return interfaces

    def _parse_ifconfig(self, output: str) -> List[NetworkInterface]:
        """解析ifconfig输出"""
        interfaces = []
        current_interface = None

        for line in output.split('\n'):
            line = line.strip()

            if line and not line.startswith(' '):
                # 新接口
                if current_interface:
                    interfaces.append(current_interface)

                parts = line.split(':')[0].split()
                interface_name = parts[0]
                flags = parts[1] if len(parts) > 1 else ''

                is_up = 'UP' in flags.upper()
                current_interface = NetworkInterface(name=interface_name, is_up=is_up)

            elif current_interface:
                # inet addr
                if 'inet addr:' in line:
                    ip = line.split('inet addr:')[1].split()[0]
                    current_interface.ip_addresses.append(ip)

                # HWaddr
                elif 'HWaddr' in line:
                    mac = line.split('HWaddr ')[1]
                    current_interface.mac_address = mac

                # inet6 addr
                elif 'inet6 addr:' in line:
                    ip6 = line.split('inet6 addr:')[1].split('/')[0]
                    current_interface.ip_addresses.append(ip6)

        if current_interface:
            interfaces.append(current_interface)

        return interfaces

    def _parse_ip_addr(self, output: str) -> List[NetworkInterface]:
        """解析ip addr输出"""
        interfaces = []
        current_interface = None

        for line in output.split('\n'):
            line = line.strip()

            if line.isdigit():
                # 新接口
                if current_interface:
                    interfaces.append(current_interface)

                parts = line.split()
                interface_name = parts[1]

                current_interface = NetworkInterface(name=interface_name, is_up=True)

            elif current_interface and line:
                parts = line.split()

                if 'inet' in parts:
                    idx = parts.index('inet')
                    if idx + 1 < len(parts):
                        ip = parts[idx + 1].split('/')[0]
                        current_interface.ip_addresses.append(ip)

                if 'link/ether' in parts:
                    idx = parts.index('link/ether')
                    if idx + 1 < len(parts):
                        mac = parts[idx + 1]
                        current_interface.mac_address = mac

        if current_interface:
            interfaces.append(current_interface)

        return interfaces

    async def test_connectivity(self, targets: List[Dict[str, Any]]) -> List[ConnectivityResult]:
        """测试网络连接"""
        self._log(f"Testing connectivity to {len(targets)} targets")

        results = []

        # 并发执行连接测试
        loop = asyncio.get_event_loop()
        tasks = []

        for target in targets:
            task = loop.run_in_executor(
                self.executor,
                self._test_single_connectivity,
                target
            )
            tasks.append(task)

        if tasks:
            completed_results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in completed_results:
                if isinstance(result, Exception):
                    self._log(f"Connectivity test error: {result}", "error")
                elif result:
                    results.append(result)

        return results

    def _test_single_connectivity(self, target: Dict[str, Any]) -> ConnectivityResult:
        """测试单个目标的连接"""
        host = target.get('host', 'localhost')
        port = target.get('port')
        connection_type = ConnectionType(target.get('type', 'tcp'))
        timeout = target.get('timeout', 5)

        result = ConnectivityResult(
            target=host,
            connection_type=connection_type,
            status=NetworkStatus.UNKNOWN
        )

        start_time = time.time()

        try:
            if connection_type in [ConnectionType.TCP, ConnectionType.HTTPS]:
                result = self._test_tcp_connection(host, port, timeout, connection_type)
            elif connection_type == ConnectionType.HTTP:
                result = self._test_http_connection(host, port, timeout)
            elif connection_type == ConnectionType.PING:
                result = self._test_ping_connection(host, timeout)
            elif connection_type == ConnectionType.DNS:
                result = self._test_dns_connection(host, timeout)

        except Exception as e:
            result.status = NetworkStatus.DISCONNECTED
            result.error_message = str(e)
            self._log(f"Error testing connectivity to {host}: {e}", "error")

        result.response_time = time.time() - start_time
        return result

    def _test_tcp_connection(self, host: str, port: int, timeout: int,
                           connection_type: ConnectionType) -> ConnectivityResult:
        """测试TCP连接"""
        result = ConnectivityResult(
            target=host,
            connection_type=connection_type,
            status=NetworkStatus.DISCONNECTED
        )

        try:
            with socket.create_connection((host, port), timeout=timeout):
                result.status = NetworkStatus.CONNECTED
                result.details['port'] = port
                result.details['connection_successful'] = True

        except socket.timeout:
            result.status = NetworkStatus.DISCONNECTED
            result.error_message = f"Connection timeout to {host}:{port}"

        except socket.gaierror as e:
            result.status = NetworkStatus.DISCONNECTED
            result.error_message = f"DNS resolution failed for {host}: {e}"

        except ConnectionRefusedError:
            result.status = NetworkStatus.DISCONNECTED
            result.error_message = f"Connection refused by {host}:{port}"

        except Exception as e:
            result.status = NetworkStatus.DISCONNECTED
            result.error_message = f"TCP connection error: {e}"

        return result

    def _test_http_connection(self, host: str, port: Optional[int], timeout: int) -> ConnectivityResult:
        """测试HTTP连接"""
        if port is None:
            port = 80

        url = f"http://{host}:{port}"

        result = ConnectivityResult(
            target=url,
            connection_type=ConnectionType.HTTP,
            status=NetworkStatus.DISCONNECTED
        )

        try:
            req = urllib.request.Request(
                url,
                headers={'User-Agent': 'NetworkDiagnostic/1.0'}
            )

            with urllib.request.urlopen(req, timeout=timeout) as response:
                result.status = NetworkStatus.CONNECTED
                result.details['http_status'] = response.getcode()
                result.details['content_type'] = response.headers.get('Content-Type')
                result.details['server'] = response.headers.get('Server')

        except urllib.error.HTTPError as e:
            if e.code in [401, 403]:  # 认证错误但服务器可达
                result.status = NetworkStatus.CONNECTED
                result.details['http_status'] = e.code
                result.error_message = f"HTTP error {e.code}: {e.reason}"
            else:
                result.status = NetworkStatus.DISCONNECTED
                result.error_message = f"HTTP error {e.code}: {e.reason}"

        except urllib.error.URLError as e:
            result.status = NetworkStatus.DISCONNECTED
            result.error_message = f"HTTP URL error: {e.reason}"

        except Exception as e:
            result.status = NetworkStatus.DISCONNECTED
            result.error_message = f"HTTP connection error: {e}"

        return result

    def _test_ping_connection(self, host: str, timeout: int) -> ConnectivityResult:
        """测试Ping连接"""
        result = ConnectivityResult(
            target=host,
            connection_type=ConnectionType.PING,
            status=NetworkStatus.DISCONNECTED
        )

        try:
            cmd = ['ping'] + self._get_ping_params(host, timeout)
            ping_result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout + 2
            )

            if ping_result.returncode == 0:
                result.status = NetworkStatus.CONNECTED
                result.details['ping_successful'] = True

                # 解析ping结果获取响应时间
                output = ping_result.stdout
                if 'time=' in output.lower():
                    try:
                        time_str = output.split('time=')[1].split()[0]
                        time_ms = float(time_str.replace('ms', ''))
                        result.response_time = time_ms / 1000.0  # 转换为秒
                        result.details['ping_time_ms'] = time_ms
                    except:
                        pass
            else:
                result.status = NetworkStatus.DISCONNECTED
                result.error_message = "Ping failed"
                result.details['ping_output'] = ping_result.stdout

        except subprocess.TimeoutExpired:
            result.status = NetworkStatus.DISCONNECTED
            result.error_message = f"Ping timeout after {timeout} seconds"

        except FileNotFoundError:
            result.status = NetworkStatus.UNKNOWN
            result.error_message = "Ping command not found"

        except Exception as e:
            result.status = NetworkStatus.DISCONNECTED
            result.error_message = f"Ping error: {e}"

        return result

    def _test_dns_connection(self, host: str, timeout: int) -> ConnectivityResult:
        """测试DNS连接"""
        result = ConnectivityResult(
            target=host,
            connection_type=ConnectionType.DNS,
            status=NetworkStatus.DISCONNECTED
        )

        try:
            # 尝试解析域名
            socket.gethostbyname(host)
            result.status = NetworkStatus.CONNECTED
            result.details['dns_resolution_successful'] = True

        except socket.gaierror as e:
            result.status = NetworkStatus.DISCONNECTED
            result.error_message = f"DNS resolution failed: {e}"

        except Exception as e:
            result.status = NetworkStatus.DISCONNECTED
            result.error_message = f"DNS error: {e}"

        return result

    def _get_ping_params(self, host: str, timeout: int) -> List[str]:
        """获取ping命令参数"""
        if self.platform == "windows":
            return ['-n', '1', '-w', str(timeout * 1000), host]
        else:
            return ['-c', '1', '-W', str(timeout), host]

    async def check_service_availability(self, services: List[Dict[str, Any]]) -> List[ServiceCheckResult]:
        """检查服务可用性"""
        self._log(f"Checking availability of {len(services)} services")

        results = []

        # 并发执行服务检查
        loop = asyncio.get_event_loop()
        tasks = []

        for service in services:
            task = loop.run_in_executor(
                self.executor,
                self._check_single_service,
                service
            )
            tasks.append(task)

        if tasks:
            completed_results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in completed_results:
                if isinstance(result, Exception):
                    self._log(f"Service check error: {result}", "error")
                elif result:
                    results.append(result)

        return results

    def _check_single_service(self, service: Dict[str, Any]) -> ServiceCheckResult:
        """检查单个服务"""
        service_name = service.get('name', 'Unknown Service')
        host = service.get('host', 'localhost')
        port = service.get('port')
        protocol = service.get('protocol', 'http')
        timeout = service.get('timeout', 10)
        path = service.get('path', '/')

        result = ServiceCheckResult(
            service_name=service_name,
            host=host,
            port=port
        )

        start_time = time.time()

        try:
            if protocol in ['http', 'https']:
                result = self._check_http_service(service, timeout)
            elif protocol == 'tcp':
                result = self._check_tcp_service(service, timeout)
            elif protocol == 'ping':
                result = self._check_ping_service(service, timeout)

        except Exception as e:
            result.status = ServiceStatus.ERROR
            result.error_message = str(e)
            self._log(f"Error checking service {service_name}: {e}", "error")

        result.response_time = time.time() - start_time
        return result

    def _check_http_service(self, service: Dict[str, Any], timeout: int) -> ServiceCheckResult:
        """检查HTTP服务"""
        service_name = service.get('name', 'HTTP Service')
        host = service.get('host', 'localhost')
        port = service.get('port', 80)
        protocol = service.get('protocol', 'http')
        path = service.get('path', '/')

        url = f"{protocol}://{host}:{port}{path}"

        result = ServiceCheckResult(
            service_name=service_name,
            host=host,
            port=port
        )

        try:
            req = urllib.request.Request(
                url,
                headers={
                    'User-Agent': 'ServiceMonitor/1.0',
                    'Accept': 'application/json,text/plain,*/*'
                }
            )

            with urllib.request.urlopen(req, timeout=timeout) as response:
                result.status = ServiceStatus.AVAILABLE
                result.http_status = response.getcode()
                result.content_length = len(response.read())
                result.headers = dict(response.headers)

                # 检查响应状态
                if response.getcode() >= 400:
                    result.status = ServiceStatus.UNAVAILABLE
                    result.error_message = f"HTTP {response.getcode()}: Service unavailable"
                elif response.getcode() >= 500:
                    result.status = ServiceStatus.ERROR
                    result.error_message = f"HTTP {response.getcode()}: Server error"

        except urllib.error.HTTPError as e:
            if e.code in [401, 403]:
                result.status = ServiceStatus.AVAILABLE  # 服务存在但需要认证
                result.http_status = e.code
                result.error_message = f"Service requires authentication: {e.reason}"
            else:
                result.status = ServiceStatus.UNAVAILABLE if e.code < 500 else ServiceStatus.ERROR
                result.http_status = e.code
                result.error_message = f"HTTP {e.code}: {e.reason}"

        except urllib.error.URLError as e:
            if isinstance(e.reason, socket.timeout):
                result.status = ServiceStatus.TIMEOUT
                result.error_message = f"Service timeout: {e.reason}"
            else:
                result.status = ServiceStatus.UNAVAILABLE
                result.error_message = f"Service unavailable: {e.reason}"

        except socket.timeout:
            result.status = ServiceStatus.TIMEOUT
            result.error_message = f"Connection timeout after {timeout} seconds"

        except Exception as e:
            result.status = ServiceStatus.ERROR
            result.error_message = f"Service check error: {e}"

        return result

    def _check_tcp_service(self, service: Dict[str, Any], timeout: int) -> ServiceCheckResult:
        """检查TCP服务"""
        service_name = service.get('name', 'TCP Service')
        host = service.get('host', 'localhost')
        port = service.get('port')

        result = ServiceCheckResult(
            service_name=service_name,
            host=host,
            port=port
        )

        try:
            with socket.create_connection((host, port), timeout=timeout):
                result.status = ServiceStatus.AVAILABLE

        except socket.timeout:
            result.status = ServiceStatus.TIMEOUT
            result.error_message = f"TCP connection timeout to {host}:{port}"

        except ConnectionRefusedError:
            result.status = ServiceStatus.UNAVAILABLE
            result.error_message = f"TCP connection refused by {host}:{port}"

        except Exception as e:
            result.status = ServiceStatus.ERROR
            result.error_message = f"TCP service error: {e}"

        return result

    def _check_ping_service(self, service: Dict[str, Any], timeout: int) -> ServiceCheckResult:
        """检查Ping服务"""
        service_name = service.get('name', 'Ping Service')
        host = service.get('host', 'localhost')

        result = ServiceCheckResult(
            service_name=service_name,
            host=host
        )

        try:
            cmd = ['ping'] + self._get_ping_params(host, timeout)
            ping_result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout + 2
            )

            if ping_result.returncode == 0:
                result.status = ServiceStatus.AVAILABLE
                result.details['ping_successful'] = True
            else:
                result.status = ServiceStatus.UNAVAILABLE
                result.error_message = "Ping failed"

        except subprocess.TimeoutExpired:
            result.status = ServiceStatus.TIMEOUT
            result.error_message = f"Ping timeout after {timeout} seconds"

        except Exception as e:
            result.status = ServiceStatus.ERROR
            result.error_message = f"Ping service error: {e}"

        return result

    async def test_dns_resolution(self, domains: List[str], dns_servers: Optional[List[str]] = None) -> List[DNSResult]:
        """测试DNS解析"""
        self._log(f"Testing DNS resolution for {len(domains)} domains")

        results = []

        for domain in domains:
            result = await self._test_single_dns(domain, dns_servers)
            results.append(result)

        return results

    async def _test_single_dns(self, domain: str, dns_servers: Optional[List[str]] = None) -> DNSResult:
        """测试单个域名的DNS解析"""
        result = DNSResult(
            domain=domain,
            record_type="A",
            status=NetworkStatus.DISCONNECTED
        )

        if dns_servers:
            result.dns_server = dns_servers[0]

        start_time = time.time()

        try:
            # 基本DNS解析
            addresses = socket.gethostbyname_ex(domain)[2]
            result.resolved_addresses = addresses
            result.status = NetworkStatus.CONNECTED

        except socket.gaierror as e:
            result.status = NetworkStatus.DISCONNECTED
            result.error_message = f"DNS resolution failed: {e}"

        except Exception as e:
            result.status = NetworkStatus.DISCONNECTED
            result.error_message = f"DNS error: {e}"

        result.response_time = time.time() - start_time
        return result

    async def run_comprehensive_diagnosis(self, config: Optional[Dict[str, Any]] = None) -> NetworkDiagnosticResult:
        """运行综合网络诊断"""
        from datetime import datetime

        self._log("Starting comprehensive network diagnosis")

        if config is None:
            config = self._get_default_config()

        result = NetworkDiagnosticResult(
            timestamp=datetime.now().isoformat(),
            overall_status=NetworkStatus.UNKNOWN
        )

        # 1. 获取网络接口
        if self.progress_tracker:
            self.progress_tracker._log("Getting network interfaces (10%)")
        result.interfaces = await self.get_network_interfaces()

        # 2. 测试基本连接
        if self.progress_tracker:
            self.progress_tracker._log("Testing basic connectivity (30%)")
        result.connectivity_tests = await self.test_connectivity(config['connectivity_targets'])

        # 3. 检查服务可用性
        if self.progress_tracker:
            self.progress_tracker._log("Checking service availability (60%)")
        result.service_checks = await self.check_service_availability(config['services'])

        # 4. 测试DNS解析
        if self.progress_tracker:
            self.progress_tracker._log("Testing DNS resolution (80%)")
        result.dns_tests = await self.test_dns_resolution(config['dns_domains'])

        # 5. 分析结果
        if self.progress_tracker:
            self.progress_tracker._log("Analyzing results (90%)")
        result.issues, result.recommendations = self._analyze_results(result)

        # 6. 生成摘要
        result.overall_status = self._determine_overall_status(result)
        result.summary = self._generate_summary(result)

        if self.progress_tracker:
            self.progress_tracker._log("Network diagnosis completed (100%)")

        return result

    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认诊断配置"""
        return {
            'connectivity_targets': [
                {'host': '8.8.8.8', 'type': 'ping', 'timeout': 5},
                {'host': '1.1.1.1', 'type': 'ping', 'timeout': 5},
                {'host': 'google.com', 'type': 'dns', 'timeout': 5},
                {'host': 'baidu.com', 'type': 'dns', 'timeout': 5},
                {'host': 'github.com', 'type': 'http', 'port': 80, 'timeout': 10},
                {'host': 'github.com', 'type': 'https', 'port': 443, 'timeout': 10},
            ],
            'services': [
                {
                    'name': 'Local Backend API',
                    'host': 'localhost',
                    'port': 8000,
                    'protocol': 'http',
                    'path': '/api/health',
                    'timeout': 5
                },
                {
                    'name': 'Local Frontend',
                    'host': 'localhost',
                    'port': 3000,
                    'protocol': 'http',
                    'path': '/',
                    'timeout': 5
                },
                {
                    'name': 'Google DNS',
                    'host': '8.8.8.8',
                    'port': 53,
                    'protocol': 'tcp',
                    'timeout': 5
                }
            ],
            'dns_domains': [
                'google.com',
                'github.com',
                'stackoverflow.com',
                'pypi.org'
            ]
        }

    def _analyze_results(self, result: NetworkDiagnosticResult) -> Tuple[List[str], List[str]]:
        """分析诊断结果"""
        issues = []
        recommendations = []

        # 分析网络接口
        active_interfaces = [i for i in result.interfaces if i.is_up]
        if not active_interfaces:
            issues.append("No active network interfaces found")
            recommendations.append("Check network adapter and cable connection")

        # 分析连接测试
        failed_connectivity = [c for c in result.connectivity_tests
                             if c.status == NetworkStatus.DISCONNECTED]
        if failed_connectivity:
            issues.append(f"Failed connectivity tests: {len(failed_connectivity)} targets unreachable")

            # 区分网络故障和服务问题
            dns_failures = [c for c in failed_connectivity if c.connection_type == ConnectionType.DNS]
            ping_failures = [c for c in failed_connectivity if c.connection_type == ConnectionType.PING]

            if dns_failures:
                issues.append("DNS resolution failures detected")
                recommendations.append("Check DNS settings and try alternative DNS servers (8.8.8.8, 1.1.1.1)")

            if ping_failures:
                issues.append("Basic connectivity failures detected")
                recommendations.append("Check internet connection and firewall settings")

        # 分析服务检查
        failed_services = [s for s in result.service_checks
                         if s.status in [ServiceStatus.UNAVAILABLE, ServiceStatus.ERROR]]
        if failed_services:
            issues.append(f"Unavailable services: {len(failed_services)} services not responding")

            for service in failed_services:
                if service.error_message:
                    issues.append(f"  - {service.service_name}: {service.error_message}")

            recommendations.append("Check if required services are running and accessible")

        # 分析DNS测试
        failed_dns = [d for d in result.dns_tests if d.status == NetworkStatus.DISCONNECTED]
        if failed_dns:
            issues.append(f"DNS resolution failures: {len(failed_dns)} domains cannot be resolved")
            recommendations.append("Check DNS configuration and internet connectivity")

        return issues, recommendations

    def _determine_overall_status(self, result: NetworkDiagnosticResult) -> NetworkStatus:
        """确定整体网络状态"""
        if not result.connectivity_tests and not result.service_checks:
            return NetworkStatus.UNKNOWN

        # 统计各种状态
        total_tests = len(result.connectivity_tests) + len(result.service_checks) + len(result.dns_tests)

        if total_tests == 0:
            return NetworkStatus.UNKNOWN

        # 计算成功率
        successful_tests = 0

        successful_connectivity = len([c for c in result.connectivity_tests
                                    if c.status == NetworkStatus.CONNECTED])
        successful_services = len([s for s in result.service_checks
                                 if s.status == ServiceStatus.AVAILABLE])
        successful_dns = len([d for d in result.dns_tests
                            if d.status == NetworkStatus.CONNECTED])

        successful_tests = successful_connectivity + successful_services + successful_dns
        success_rate = successful_tests / total_tests

        if success_rate >= 0.9:
            return NetworkStatus.CONNECTED
        elif success_rate >= 0.5:
            return NetworkStatus.PARTIAL
        else:
            return NetworkStatus.DISCONNECTED

    def _generate_summary(self, result: NetworkDiagnosticResult) -> Dict[str, Any]:
        """生成诊断摘要"""
        summary = {
            'total_interfaces': len(result.interfaces),
            'active_interfaces': len([i for i in result.interfaces if i.is_up]),
            'connectivity_tests': len(result.connectivity_tests),
            'successful_connectivity': len([c for c in result.connectivity_tests
                                          if c.status == NetworkStatus.CONNECTED]),
            'service_checks': len(result.service_checks),
            'available_services': len([s for s in result.service_checks
                                     if s.status == ServiceStatus.AVAILABLE]),
            'dns_tests': len(result.dns_tests),
            'successful_dns': len([d for d in result.dns_tests
                                 if d.status == NetworkStatus.CONNECTED]),
            'total_issues': len(result.issues),
            'total_recommendations': len(result.recommendations)
        }

        return summary

    def generate_network_guide(self, issue_type: str) -> Dict[str, Any]:
        """生成网络问题解决指南"""
        guides = {
            'connectivity': {
                'title': '网络连接问题解决指南',
                'description': '解决无法连接到互联网或特定服务的问题',
                'steps': [
                    {
                        'name': '检查网络接口',
                        'description': '确认网络适配器已启用并连接',
                        'commands': [
                            'Windows: ipconfig /all',
                            'Linux/Mac: ip addr show 或 ifconfig'
                        ]
                    },
                    {
                        'name': '测试基本连接',
                        'description': '使用ping测试基本网络连通性',
                        'commands': [
                            'ping 8.8.8.8',
                            'ping google.com'
                        ]
                    },
                    {
                        'name': '检查DNS设置',
                        'description': '验证DNS配置是否正确',
                        'commands': [
                            'Windows: nslookup google.com',
                            'Linux/Mac: dig google.com'
                        ]
                    },
                    {
                        'name': '检查防火墙设置',
                        'description': '确认防火墙没有阻止必要的连接',
                        'commands': [
                            '检查防火墙状态',
                            '临时禁用防火墙进行测试'
                        ]
                    }
                ]
            },
            'service_availability': {
                'title': '服务可用性问题解决指南',
                'description': '解决本地服务无法访问的问题',
                'steps': [
                    {
                        'name': '检查服务状态',
                        'description': '确认目标服务正在运行',
                        'commands': [
                            'Windows: netstat -an | findstr :8000',
                            'Linux/Mac: netstat -an | grep :8000',
                            '检查服务进程是否运行'
                        ]
                    },
                    {
                        'name': '测试端口连接',
                        'description': '使用telnet或nc测试端口连通性',
                        'commands': [
                            'telnet localhost 8000',
                            'nc -zv localhost 8000'
                        ]
                    },
                    {
                        'name': '检查服务配置',
                        'description': '验证服务配置和绑定地址',
                        'commands': [
                            '检查服务配置文件',
                            '确认服务绑定到正确的地址和端口'
                        ]
                    }
                ]
            },
            'dns_resolution': {
                'title': 'DNS解析问题解决指南',
                'description': '解决域名无法解析的问题',
                'steps': [
                    {
                        'name': '检查DNS配置',
                        'description': '验证DNS服务器配置',
                        'commands': [
                            'Windows: ipconfig /all',
                            'Linux/Mac: cat /etc/resolv.conf'
                        ]
                    },
                    {
                        'name': '测试DNS服务器',
                        'description': '测试不同DNS服务器的解析能力',
                        'commands': [
                            'nslookup google.com 8.8.8.8',
                            'nslookup google.com 1.1.1.1'
                        ]
                    },
                    {
                        'name': '清除DNS缓存',
                        'description': '清除本地DNS缓存',
                        'commands': [
                            'Windows: ipconfig /flushdns',
                            'Linux: sudo systemctl restart systemd-resolved',
                            'Mac: sudo dscacheutil -flushcache'
                        ]
                    }
                ]
            }
        }

        return guides.get(issue_type, {
            'title': '网络问题解决指南',
            'description': '通用网络问题解决方法',
            'steps': []
        })

    async def __aenter__(self):
        """异步上下文管理器入口"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        if self.executor:
            self.executor.shutdown(wait=False)


# 便利函数
async def quick_network_check() -> NetworkDiagnosticResult:
    """快速网络检查"""
    async with NetworkDiagnostic() as diagnostic:
        config = {
            'connectivity_targets': [
                {'host': '8.8.8.8', 'type': 'ping', 'timeout': 3},
                {'host': 'google.com', 'type': 'dns', 'timeout': 3},
            ],
            'services': [],
            'dns_domains': ['google.com']
        }

        return await diagnostic.run_comprehensive_diagnosis(config)


async def check_local_services(services: List[Dict[str, Any]]) -> List[ServiceCheckResult]:
    """检查本地服务"""
    async with NetworkDiagnostic() as diagnostic:
        return await diagnostic.check_service_availability(services)