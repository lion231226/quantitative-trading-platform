"""
前后端通信验证器

提供前端到后端API通信测试、CORS配置验证和数据检索功能验证。
"""

import asyncio
import aiohttp
import json
import time
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
from urllib.parse import urljoin, urlparse

from utils.frontend_logger import get_frontend_logger

logger = get_frontend_logger()


class CommunicationStatus(Enum):
    """通信状态"""
    UNKNOWN = "unknown"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CORS_ERROR = "cors_error"
    AUTH_ERROR = "auth_error"


@dataclass
class APIEndpoint:
    """API端点定义"""
    path: str
    method: str = "GET"
    expected_status: int = 200
    timeout: int = 10
    auth_required: bool = False
    request_data: Optional[Dict[str, Any]] = None
    expected_response_keys: Optional[List[str]] = None
    description: str = ""


@dataclass
class CommunicationConfig:
    """通信验证配置"""
    frontend_url: str
    backend_url: str
    api_endpoints: List[APIEndpoint]
    cors_origins: List[str] = None
    timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0
    verify_cors: bool = True
    verify_data_flow: bool = True

    def __post_init__(self):
        if self.cors_origins is None:
            self.cors_origins = [urlparse(self.frontend_url).netloc]


@dataclass
class CommunicationResult:
    """通信验证结果"""
    endpoint: APIEndpoint
    status: CommunicationStatus
    response_time: float
    status_code: Optional[int] = None
    response_data: Optional[Dict[str, Any]] = None
    response_headers: Optional[Dict[str, str]] = None
    cors_headers: Optional[Dict[str, str]] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    data_validation_passed: bool = False


@dataclass
class CommunicationReport:
    """通信验证报告"""
    frontend_url: str
    backend_url: str
    overall_status: CommunicationStatus
    total_endpoints: int
    successful_endpoints: int
    failed_endpoints: int
    average_response_time: float
    results: List[CommunicationResult]
    cors_status: str
    data_flow_status: str
    error_summary: List[str]

    @property
    def success_rate(self) -> float:
        """成功率"""
        return self.successful_endpoints / self.total_endpoints if self.total_endpoints > 0 else 0.0


class FrontendBackendCommunicator:
    """前后端通信验证器"""

    def __init__(self):
        self.logger = logger
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        """异步上下文管理器入口"""
        connector = aiohttp.TCPConnector(
            limit=50,
            limit_per_host=10,
            ttl_dns_cache=300,
            use_dns_cache=True,
        )
        timeout = aiohttp.ClientTimeout(total=60, connect=10)
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={'User-Agent': 'One-Click-Launcher-Frontend-Backend-Communicator/1.0'}
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        if self.session:
            await self.session.close()

    async def verify_communication(self, config: CommunicationConfig) -> CommunicationReport:
        """验证前后端通信"""
        self.logger.info(f"Starting frontend-backend communication verification")
        self.logger.info(f"Frontend URL: {config.frontend_url}")
        self.logger.info(f"Backend URL: {config.backend_url}")

        results = []
        successful_endpoints = 0
        failed_endpoints = 0

        # 验证每个API端点
        for endpoint in config.api_endpoints:
            try:
                result = await self._test_api_endpoint(config, endpoint)
                results.append(result)

                if result.status == CommunicationStatus.CONNECTED:
                    successful_endpoints += 1
                else:
                    failed_endpoints += 1

                self.logger.info(f"Endpoint {endpoint.path} ({endpoint.method}): {result.status.value}")

            except Exception as e:
                error_result = CommunicationResult(
                    endpoint=endpoint,
                    status=CommunicationStatus.FAILED,
                    response_time=0.0,
                    error_message=str(e)
                )
                results.append(error_result)
                failed_endpoints += 1
                self.logger.error(f"Endpoint {endpoint.path} test failed: {e}")

        # 计算整体状态
        overall_status = self._determine_overall_status(results)
        average_response_time = sum(r.response_time for r in results) / len(results) if results else 0.0

        # CORS验证
        cors_status = "not_tested"
        if config.verify_cors:
            cors_status = await self._verify_cors_configuration(config)

        # 数据流验证
        data_flow_status = "not_tested"
        if config.verify_data_flow:
            data_flow_status = await self._verify_data_flow(config, results)

        # 错误汇总
        error_summary = [r.error_message for r in results if r.error_message]

        report = CommunicationReport(
            frontend_url=config.frontend_url,
            backend_url=config.backend_url,
            overall_status=overall_status,
            total_endpoints=len(config.api_endpoints),
            successful_endpoints=successful_endpoints,
            failed_endpoints=failed_endpoints,
            average_response_time=average_response_time,
            results=results,
            cors_status=cors_status,
            data_flow_status=data_flow_status,
            error_summary=error_summary
        )

        self.logger.info(f"Communication verification completed. Success rate: {report.success_rate:.1%}")
        return report

    async def _test_api_endpoint(self, config: CommunicationConfig,
                                endpoint: APIEndpoint) -> CommunicationResult:
        """测试单个API端点"""
        result = CommunicationResult(
            endpoint=endpoint,
            status=CommunicationStatus.CONNECTING,
            response_time=0.0
        )

        full_url = urljoin(config.backend_url, endpoint.path)

        for attempt in range(config.max_retries + 1):
            try:
                result.retry_count = attempt
                start_time = time.time()

                # 构建请求
                headers = {'Origin': config.frontend_url}
                if endpoint.auth_required:
                    headers['Authorization'] = 'Bearer test-token'

                # 发送请求
                async with self.session.request(
                    endpoint.method,
                    full_url,
                    headers=headers,
                    json=endpoint.request_data,
                    timeout=aiohttp.ClientTimeout(total=endpoint.timeout)
                ) as response:
                    result.response_time = time.time() - start_time
                    result.status_code = response.status

                    # 读取响应
                    response_text = await response.text()
                    try:
                        result.response_data = json.loads(response_text)
                    except json.JSONDecodeError:
                        result.response_data = {'raw_response': response_text}

                    # 获取响应头
                    result.response_headers = dict(response.headers)
                    result.cors_headers = self._extract_cors_headers(response.headers)

                    # 检查状态码
                    if response.status == endpoint.expected_status:
                        result.status = CommunicationStatus.CONNECTED

                        # 验证响应数据
                        if endpoint.expected_response_keys:
                            result.data_validation_passed = self._validate_response_data(
                                result.response_data, endpoint.expected_response_keys
                            )
                        else:
                            result.data_validation_passed = True

                        return result
                    elif response.status == 401:
                        result.status = CommunicationStatus.AUTH_ERROR
                        result.error_message = "Authentication required/failed"
                        return result
                    elif response.status == 403:
                        result.status = CommunicationStatus.FAILED
                        result.error_message = "Access forbidden"
                        return result
                    else:
                        result.status = CommunicationStatus.FAILED
                        result.error_message = f"Unexpected status code: {response.status}"
                        return result

            except asyncio.TimeoutError:
                result.status = CommunicationStatus.TIMEOUT
                result.error_message = f"Request timeout after {endpoint.timeout}s"
            except aiohttp.ClientConnectorError as e:
                result.status = CommunicationStatus.FAILED
                result.error_message = f"Connection failed: {e}"
            except Exception as e:
                result.status = CommunicationStatus.FAILED
                result.error_message = str(e)

            # 重试逻辑
            if attempt < config.max_retries:
                self.logger.log_retry_attempt(
                    f"api_endpoint_{endpoint.path}", attempt + 1, config.max_retries + 1,
                    result.error_message
                )
                await asyncio.sleep(config.retry_delay)

        return result

    def _extract_cors_headers(self, headers: Dict[str, str]) -> Dict[str, str]:
        """提取CORS相关头部"""
        cors_headers = {}
        cors_prefixes = ['Access-Control-', 'origin', 'Origin']

        for key, value in headers.items():
            if any(prefix.lower() in key.lower() for prefix in cors_prefixes):
                cors_headers[key] = value

        return cors_headers

    def _validate_response_data(self, data: Dict[str, Any],
                               expected_keys: List[str]) -> bool:
        """验证响应数据结构"""
        if not isinstance(data, dict):
            return False

        missing_keys = []
        for key in expected_keys:
            if key not in data:
                missing_keys.append(key)

        if missing_keys:
            self.logger.warning(f"Missing expected response keys: {missing_keys}")
            return False

        return True

    def _determine_overall_status(self, results: List[CommunicationResult]) -> CommunicationStatus:
        """确定整体通信状态"""
        if not results:
            return CommunicationStatus.UNKNOWN

        # 检查是否有连接成功的端点
        successful_results = [r for r in results if r.status == CommunicationStatus.CONNECTED]
        if successful_results:
            return CommunicationStatus.CONNECTED

        # 检查是否有CORS错误
        cors_errors = [r for r in results if r.status == CommunicationStatus.CORS_ERROR]
        if cors_errors:
            return CommunicationStatus.CORS_ERROR

        # 检查是否有认证错误
        auth_errors = [r for r in results if r.status == CommunicationStatus.AUTH_ERROR]
        if auth_errors:
            return CommunicationStatus.AUTH_ERROR

        # 检查是否有超时
        timeouts = [r for r in results if r.status == CommunicationStatus.TIMEOUT]
        if timeouts:
            return CommunicationStatus.TIMEOUT

        # 默认为失败
        return CommunicationStatus.FAILED

    async def _verify_cors_configuration(self, config: CommunicationConfig) -> str:
        """验证CORS配置"""
        try:
            # 发送OPTIONS请求测试CORS
            test_url = urljoin(config.backend_url, "/api/test")
            headers = {'Origin': config.frontend_url}

            async with self.session.options(test_url, headers=headers) as response:
                cors_headers = self._extract_cors_headers(dict(response.headers))

                # 检查必要的CORS头部
                required_headers = ['Access-Control-Allow-Origin']
                missing_headers = [h for h in required_headers if h not in cors_headers]

                if missing_headers:
                    return f"missing_headers: {missing_headers}"

                # 检查Origin是否被允许
                allowed_origin = cors_headers.get('Access-Control-Allow-Origin', '')
                if allowed_origin != config.frontend_url and allowed_origin != '*':
                    return f"origin_not_allowed: {allowed_origin}"

                return "configured"

        except Exception as e:
            return f"error: {e}"

    async def _verify_data_flow(self, config: CommunicationConfig,
                               results: List[CommunicationResult]) -> str:
        """验证数据流"""
        try:
            # 检查是否有端点返回有效数据
            valid_data_results = [
                r for r in results
                if r.response_data and r.status == CommunicationStatus.CONNECTED
            ]

            if not valid_data_results:
                return "no_valid_data"

            # 检查数据验证是否通过
            data_validation_passed = all(r.data_validation_passed for r in valid_data_results)
            if not data_validation_passed:
                return "data_validation_failed"

            # 检查响应时间
            avg_response_time = sum(r.response_time for r in valid_data_results) / len(valid_data_results)
            if avg_response_time > 5.0:
                return f"slow_response: {avg_response_time:.2f}s"

            return "working"

        except Exception as e:
            return f"error: {e}"

    async def test_data_retrieval(self, backend_url: str, test_endpoints: List[str]) -> Dict[str, Any]:
        """测试数据检索功能"""
        results = {}

        for endpoint in test_endpoints:
            try:
                full_url = urljoin(backend_url, endpoint)
                start_time = time.time()

                async with self.session.get(full_url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    response_time = time.time() - start_time
                    response_data = await response.json()

                    results[endpoint] = {
                        'status_code': response.status,
                        'response_time': response_time,
                        'data_size': len(json.dumps(response_data)),
                        'success': response.status == 200,
                        'data_preview': str(response_data)[:200] + "..." if str(response_data) > 200 else str(response_data)
                    }

            except Exception as e:
                results[endpoint] = {
                    'success': False,
                    'error': str(e),
                    'response_time': 0.0
                }

        return results

    async def monitor_communication_status(self, frontend_url: str, backend_url: str,
                                         duration: int = 60, interval: int = 5) -> Dict[str, Any]:
        """监控通信状态"""
        start_time = time.time()
        monitoring_results = []

        test_endpoint = "/api/health"

        while time.time() - start_time < duration:
            try:
                full_url = urljoin(backend_url, test_endpoint)
                request_start = time.time()

                async with self.session.get(
                    full_url,
                    headers={'Origin': frontend_url},
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    request_time = time.time() - request_start

                    monitoring_results.append({
                        'timestamp': time.time(),
                        'status_code': response.status,
                        'response_time': request_time,
                        'success': response.status == 200
                    })

            except Exception as e:
                monitoring_results.append({
                    'timestamp': time.time(),
                    'success': False,
                    'error': str(e),
                    'response_time': 0.0
                })

            await asyncio.sleep(interval)

        # 计算统计数据
        total_requests = len(monitoring_results)
        successful_requests = sum(1 for r in monitoring_results if r.get('success', False))
        avg_response_time = sum(r.get('response_time', 0) for r in monitoring_results) / total_requests

        return {
            'duration': duration,
            'total_requests': total_requests,
            'successful_requests': successful_requests,
            'success_rate': successful_requests / total_requests,
            'average_response_time': avg_response_time,
            'results': monitoring_results
        }

    def create_communication_report(self, report: CommunicationReport) -> str:
        """创建通信验证报告"""
        lines = [
            "# Frontend-Backend Communication Verification Report",
            f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## Configuration",
            f"- Frontend URL: {report.frontend_url}",
            f"- Backend URL: {report.backend_url}",
            f"- Total Endpoints: {report.total_endpoints}",
            "",
            "## Results Summary",
            f"- Overall Status: {report.overall_status.value}",
            f"- Successful Endpoints: {report.successful_endpoints}",
            f"- Failed Endpoints: {report.failed_endpoints}",
            f"- Success Rate: {report.success_rate:.1%}",
            f"- Average Response Time: {report.average_response_time:.3f}s",
            f"- CORS Status: {report.cors_status}",
            f"- Data Flow Status: {report.data_flow_status}",
            "",
            "## Endpoint Details"
        ]

        for i, result in enumerate(report.results, 1):
            lines.extend([
                f"",
                f"### {i}. {result.endpoint.path} ({result.endpoint.method})",
                f"- Status: {result.status.value}",
                f"- Response Time: {result.response_time:.3f}s",
                f"- Status Code: {result.status_code}",
                f"- Retry Count: {result.retry_count}",
                f"- Data Validation: {'Passed' if result.data_validation_passed else 'Failed'}",
            ])

            if result.error_message:
                lines.append(f"- Error: {result.error_message}")

            if result.cors_headers:
                lines.append("- CORS Headers:")
                for key, value in result.cors_headers.items():
                    lines.append(f"  - {key}: {value}")

        if report.error_summary:
            lines.extend([
                "",
                "## Error Summary",
                *[f"- {error}" for error in report.error_summary]
            ])

        return "\n".join(lines)