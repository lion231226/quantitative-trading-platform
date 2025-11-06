"""
API健康检查工具

提供专门用于API端点健康检查的工具和函数。
"""

import asyncio
import aiohttp
import time
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass
from datetime import datetime
import json

from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class APIHealthCheckResult:
    """API健康检查结果"""
    endpoint: str
    is_healthy: bool
    response_time: Optional[float]
    status_code: Optional[int]
    content_type: Optional[str]
    content_length: Optional[int]
    error_message: Optional[str]
    timestamp: datetime
    headers: Dict[str, str]

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'endpoint': self.endpoint,
            'is_healthy': self.is_healthy,
            'response_time': self.response_time,
            'status_code': self.status_code,
            'content_type': self.content_type,
            'content_length': self.content_length,
            'error_message': self.error_message,
            'timestamp': self.timestamp.isoformat(),
            'headers': self.headers
        }


class APIHealthChecker:
    """API健康检查器"""

    def __init__(self, timeout: float = 10.0, max_retries: int = 3):
        self.timeout = timeout
        self.max_retries = max_retries
        self._session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self._ensure_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close_session()

    async def _ensure_session(self):
        """确保HTTP会话存在"""
        if not self._session or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self._session = aiohttp.ClientSession(
                timeout=timeout,
                headers={
                    'User-Agent': 'BackendAPI-HealthChecker/1.0'
                }
            )

    async def close_session(self):
        """关闭HTTP会话"""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    async def check_endpoint(
        self,
        url: str,
        method: str = "GET",
        expected_status: int = 200,
        timeout: Optional[float] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> APIHealthCheckResult:
        """
        检查单个API端点

        Args:
            url: 端点URL
            method: HTTP方法
            expected_status: 期望的状态码
            timeout: 超时时间
            headers: 请求头

        Returns:
            APIHealthCheckResult: 健康检查结果
        """
        await self._ensure_session()

        request_timeout = timeout or self.timeout
        start_time = time.time()

        try:
            async with self._session.request(
                method=method,
                url=url,
                headers=headers
            ) as response:
                response_time = time.time() - start_time
                content_type = response.headers.get('content-type')
                content_length = response.headers.get('content-length')

                # Read content length from response if not in headers
                if content_length is None:
                    content = await response.text()
                    content_length = len(content.encode())
                else:
                    content_length = int(content_length)

                is_healthy = (
                    response.status == expected_status and
                    response_time < request_timeout
                )

                result = APIHealthCheckResult(
                    endpoint=url,
                    is_healthy=is_healthy,
                    response_time=response_time,
                    status_code=response.status,
                    content_type=content_type,
                    content_length=content_length,
                    error_message=None,
                    timestamp=datetime.now(),
                    headers=dict(response.headers)
                )

                logger.debug(f"API health check successful: {url} - {response.status} in {response_time:.3f}s")
                return result

        except asyncio.TimeoutError:
            response_time = time.time() - start_time
            return APIHealthCheckResult(
                endpoint=url,
                is_healthy=False,
                response_time=response_time,
                status_code=None,
                content_type=None,
                content_length=None,
                error_message=f"Request timeout after {request_timeout}s",
                timestamp=datetime.now(),
                headers={}
            )

        except aiohttp.ClientError as e:
            response_time = time.time() - start_time
            return APIHealthCheckResult(
                endpoint=url,
                is_healthy=False,
                response_time=response_time,
                status_code=None,
                content_type=None,
                content_length=None,
                error_message=f"Connection error: {e}",
                timestamp=datetime.now(),
                headers={}
            )

        except Exception as e:
            response_time = time.time() - start_time
            return APIHealthCheckResult(
                endpoint=url,
                is_healthy=False,
                response_time=response_time,
                status_code=None,
                content_type=None,
                content_length=None,
                error_message=f"Unexpected error: {e}",
                timestamp=datetime.now(),
                headers={}
            )

    async def check_multiple_endpoints(
        self,
        endpoints: List[Dict[str, Any]],
        concurrent_limit: int = 10
    ) -> List[APIHealthCheckResult]:
        """
        检查多个API端点

        Args:
            endpoints: 端点配置列表，每个元素包含url, method, expected_status等
            concurrent_limit: 并发限制

        Returns:
            List[APIHealthCheckResult]: 健康检查结果列表
        """
        semaphore = asyncio.Semaphore(concurrent_limit)

        async def check_with_semaphore(endpoint_config: Dict[str, Any]) -> APIHealthCheckResult:
            async with semaphore:
                return await self.check_endpoint(**endpoint_config)

        tasks = [check_with_semaphore(endpoint_config) for endpoint_config in endpoints]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Convert exceptions to error results
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                endpoint_config = endpoints[i]
                final_results.append(APIHealthCheckResult(
                    endpoint=endpoint_config.get('url', 'unknown'),
                    is_healthy=False,
                    response_time=None,
                    status_code=None,
                    content_type=None,
                    content_length=None,
                    error_message=f"Task error: {result}",
                    timestamp=datetime.now(),
                    headers={}
                ))
            else:
                final_results.append(result)

        return final_results

    async def check_endpoint_with_retry(
        self,
        url: str,
        method: str = "GET",
        expected_status: int = 200,
        timeout: Optional[float] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> APIHealthCheckResult:
        """
        带重试机制的端点检查

        Args:
            url: 端点URL
            method: HTTP方法
            expected_status: 期望的状态码
            timeout: 超时时间
            headers: 请求头

        Returns:
            APIHealthCheckResult: 健康检查结果
        """
        last_result = None

        for attempt in range(self.max_retries + 1):
            result = await self.check_endpoint(
                url=url,
                method=method,
                expected_status=expected_status,
                timeout=timeout,
                headers=headers
            )

            if result.is_healthy:
                if attempt > 0:
                    logger.info(f"API endpoint healthy after {attempt + 1} attempts: {url}")
                return result

            last_result = result

            if attempt < self.max_retries:
                wait_time = min(2 ** attempt, 10)  # Exponential backoff, max 10s
                logger.warning(f"API endpoint check failed (attempt {attempt + 1}), retrying in {wait_time}s: {url}")
                await asyncio.sleep(wait_time)

        logger.error(f"API endpoint check failed after {self.max_retries + 1} attempts: {url}")
        return last_result

    async def measure_endpoint_performance(
        self,
        url: str,
        method: str = "GET",
        sample_count: int = 5,
        sample_interval: float = 1.0
    ) -> Dict[str, Any]:
        """
        测量端点性能

        Args:
            url: 端点URL
            method: HTTP方法
            sample_count: 采样次数
            sample_interval: 采样间隔

        Returns:
            Dict[str, Any]: 性能统计
        """
        response_times = []
        success_count = 0
        error_count = 0

        for i in range(sample_count):
            result = await self.check_endpoint(url, method)

            if result.is_healthy and result.response_time:
                response_times.append(result.response_time)
                success_count += 1
            else:
                error_count += 1

            # Wait between samples (except for the last one)
            if i < sample_count - 1:
                await asyncio.sleep(sample_interval)

        if not response_times:
            return {
                'endpoint': url,
                'total_samples': sample_count,
                'successful_samples': 0,
                'failed_samples': sample_count,
                'success_rate': 0.0,
                'avg_response_time': 0.0,
                'min_response_time': 0.0,
                'max_response_time': 0.0,
                'p50_response_time': 0.0,
                'p95_response_time': 0.0,
                'p99_response_time': 0.0
            }

        response_times.sort()
        total_samples = len(response_times) + error_count

        return {
            'endpoint': url,
            'total_samples': total_samples,
            'successful_samples': len(response_times),
            'failed_samples': error_count,
            'success_rate': len(response_times) / total_samples if total_samples > 0 else 0.0,
            'avg_response_time': sum(response_times) / len(response_times),
            'min_response_time': min(response_times),
            'max_response_time': max(response_times),
            'p50_response_time': response_times[len(response_times) // 2],
            'p95_response_time': response_times[int(len(response_times) * 0.95)],
            'p99_response_time': response_times[int(len(response_times) * 0.99)]
        }

    async def check_api_suite(
        self,
        base_url: str,
        endpoints: List[Dict[str, Any]],
        timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        检查API套件

        Args:
            base_url: 基础URL
            endpoints: 端点配置列表
            timeout: 超时时间

        Returns:
            Dict[str, Any]: 套件检查结果
        """
        # Prepare endpoint configurations
        endpoint_configs = []
        for endpoint in endpoints:
            url = f"{base_url.rstrip('/')}/{endpoint['path'].lstrip('/')}"
            config = {
                'url': url,
                'method': endpoint.get('method', 'GET'),
                'expected_status': endpoint.get('expected_status', 200),
                'timeout': timeout or self.timeout,
                'headers': endpoint.get('headers')
            }
            endpoint_configs.append(config)

        # Check all endpoints
        results = await self.check_multiple_endpoints(endpoint_configs)

        # Analyze results
        healthy_count = sum(1 for result in results if result.is_healthy)
        total_count = len(results)
        overall_health = healthy_count == total_count

        # Calculate average response time
        response_times = [result.response_time for result in results if result.response_time is not None]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0.0

        return {
            'base_url': base_url,
            'overall_health': overall_health,
            'healthy_endpoints': healthy_count,
            'total_endpoints': total_count,
            'health_percentage': (healthy_count / total_count * 100) if total_count > 0 else 0.0,
            'avg_response_time': avg_response_time,
            'results': [result.to_dict() for result in results],
            'timestamp': datetime.now().isoformat()
        }


# Convenience functions

async def check_api_health(
    base_url: str,
    health_endpoint: str = "/health",
    timeout: float = 5.0
) -> APIHealthCheckResult:
    """
    检查API健康状态

    Args:
        base_url: 基础URL
        health_endpoint: 健康检查端点
        timeout: 超时时间

    Returns:
        APIHealthCheckResult: 健康检查结果
    """
    url = f"{base_url.rstrip('/')}/{health_endpoint.lstrip('/')}"

    async with APIHealthChecker(timeout=timeout) as checker:
        return await checker.check_endpoint(url)


async def check_api_docs(
    base_url: str,
    docs_endpoint: str = "/api/docs",
    timeout: float = 5.0
) -> APIHealthCheckResult:
    """
    检查API文档可访问性

    Args:
        base_url: 基础URL
        docs_endpoint: 文档端点
        timeout: 超时时间

    Returns:
        APIHealthCheckResult: 文档检查结果
    """
    url = f"{base_url.rstrip('/')}/{docs_endpoint.lstrip('/')}"

    async with APIHealthChecker(timeout=timeout) as checker:
        return await checker.check_endpoint(url)


async def run_comprehensive_api_health_check(
    base_url: str,
    timeout: float = 10.0
) -> Dict[str, Any]:
    """
    运行综合API健康检查

    Args:
        base_url: 基础URL
        timeout: 超时时间

    Returns:
        Dict[str, Any]: 综合健康检查结果
    """
    endpoints = [
        {'path': '/health', 'expected_status': 200},
        {'path': '/api/docs', 'expected_status': 200},
        {'path': '/metrics', 'expected_status': 200, 'method': 'GET'}
    ]

    async with APIHealthChecker(timeout=timeout) as checker:
        return await checker.check_api_suite(base_url, endpoints, timeout)