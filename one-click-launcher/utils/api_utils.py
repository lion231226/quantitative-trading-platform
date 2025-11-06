"""
API工具函数

提供API端点检查、HTTP请求处理和响应验证等工具函数。
"""

import asyncio
import aiohttp
import time
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass
from datetime import datetime
import json
import ssl

from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class APIResponse:
    """API响应结果"""
    status_code: int
    response_time: float
    content: Any
    headers: Dict[str, str]
    url: str
    timestamp: datetime


@dataclass
class EndpointCheckResult:
    """端点检查结果"""
    url: str
    is_accessible: bool
    response_time: Optional[float]
    status_code: Optional[int]
    error_message: Optional[str]
    content_length: Optional[int]
    timestamp: datetime


class APIUtils:
    """API工具类"""

    def __init__(self, timeout: int = 30, verify_ssl: bool = True):
        self.timeout = timeout
        self.verify_ssl = verify_ssl
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
            # Create SSL context for HTTPS requests
            ssl_context = None
            if not self.verify_ssl:
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE

            # Configure timeout
            timeout = aiohttp.ClientTimeout(total=self.timeout)

            self._session = aiohttp.ClientSession(
                timeout=timeout,
                ssl=ssl_context,
                headers={
                    'User-Agent': 'BackendAPI-Checker/1.0'
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
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None
    ) -> EndpointCheckResult:
        """
        检查API端点可访问性

        Args:
            url: 端点URL
            method: HTTP方法
            expected_status: 期望的状态码
            headers: 请求头
            timeout: 超时时间（秒）

        Returns:
            EndpointCheckResult: 端点检查结果
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
                content_length = response.headers.get('content-length')

                # Read response content (limited to avoid memory issues)
                content = await response.text()

                result = EndpointCheckResult(
                    url=url,
                    is_accessible=response.status == expected_status,
                    response_time=response_time,
                    status_code=response.status,
                    error_message=None,
                    content_length=int(content_length) if content_length else len(content.encode()),
                    timestamp=datetime.now()
                )

                logger.debug(f"Endpoint check successful: {url} - {response.status} in {response_time:.3f}s")
                return result

        except asyncio.TimeoutError:
            response_time = time.time() - start_time
            return EndpointCheckResult(
                url=url,
                is_accessible=False,
                response_time=response_time,
                status_code=None,
                error_message=f"Request timeout after {request_timeout}s",
                content_length=None,
                timestamp=datetime.now()
            )

        except aiohttp.ClientError as e:
            response_time = time.time() - start_time
            return EndpointCheckResult(
                url=url,
                is_accessible=False,
                response_time=response_time,
                status_code=None,
                error_message=f"Connection error: {e}",
                content_length=None,
                timestamp=datetime.now()
            )

        except Exception as e:
            response_time = time.time() - start_time
            return EndpointCheckResult(
                url=url,
                is_accessible=False,
                response_time=response_time,
                status_code=None,
                error_message=f"Unexpected error: {e}",
                content_length=None,
                timestamp=datetime.now()
            )

    async def check_endpoints_batch(
        self,
        urls: List[str],
        concurrent_limit: int = 10
    ) -> List[EndpointCheckResult]:
        """
        批量检查多个端点

        Args:
            urls: URL列表
            concurrent_limit: 并发限制

        Returns:
            List[EndpointCheckResult]: 端点检查结果列表
        """
        semaphore = asyncio.Semaphore(concurrent_limit)

        async def check_with_semaphore(url: str) -> EndpointCheckResult:
            async with semaphore:
                return await self.check_endpoint(url)

        tasks = [check_with_semaphore(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Convert exceptions to error results
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                final_results.append(EndpointCheckResult(
                    url=urls[i],
                    is_accessible=False,
                    response_time=None,
                    status_code=None,
                    error_message=f"Task error: {result}",
                    content_length=None,
                    timestamp=datetime.now()
                ))
            else:
                final_results.append(result)

        return final_results

    async def make_request(
        self,
        url: str,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Union[str, Dict[str, Any]]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None
    ) -> APIResponse:
        """
        发送HTTP请求

        Args:
            url: 请求URL
            method: HTTP方法
            headers: 请求头
            params: URL参数
            data: 请求数据
            json_data: JSON数据
            timeout: 超时时间

        Returns:
            APIResponse: API响应结果
        """
        await self._ensure_session()

        request_timeout = timeout or self.timeout
        start_time = time.time()

        try:
            async with self._session.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                data=data,
                json=json_data
            ) as response:
                response_time = time.time() - start_time

                # Handle response content based on content type
                content_type = response.headers.get('content-type', '').lower()

                if 'application/json' in content_type:
                    content = await response.json()
                else:
                    content = await response.text()

                api_response = APIResponse(
                    status_code=response.status,
                    response_time=response_time,
                    content=content,
                    headers=dict(response.headers),
                    url=str(response.url),
                    timestamp=datetime.now()
                )

                logger.debug(f"API request successful: {method} {url} - {response.status} in {response_time:.3f}s")
                return api_response

        except asyncio.TimeoutError:
            raise TimeoutError(f"Request timeout after {request_timeout}s")

        except aiohttp.ClientError as e:
            raise ConnectionError(f"Connection error: {e}")

    async def validate_json_response(
        self,
        response: APIResponse,
        required_fields: Optional[List[str]] = None,
        schema: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, List[str]]:
        """
        验证JSON响应格式

        Args:
            response: API响应
            required_fields: 必需字段列表
            schema: JSON schema

        Returns:
            Tuple[bool, List[str]]: (是否有效, 错误消息列表)
        """
        errors = []

        # Check if response is JSON
        if not isinstance(response.content, dict):
            errors.append("Response content is not valid JSON")
            return False, errors

        # Check required fields
        if required_fields:
            for field in required_fields:
                if field not in response.content:
                    errors.append(f"Missing required field: {field}")

        # Validate against schema (basic implementation)
        if schema:
            # This is a simplified schema validation
            # In production, use a proper JSON schema validator
            for field, field_schema in schema.items():
                if field in response.content:
                    expected_type = field_schema.get('type')
                    if expected_type and not isinstance(response.content[field], eval(expected_type)):
                        errors.append(f"Field '{field}' should be of type {expected_type}")

        is_valid = len(errors) == 0
        return is_valid, errors

    async def measure_response_time(
        self,
        url: str,
        method: str = "GET",
        sample_count: int = 5,
        sample_interval: float = 1.0
    ) -> Dict[str, float]:
        """
        测量API响应时间统计

        Args:
            url: 端点URL
            method: HTTP方法
            sample_count: 采样次数
            sample_interval: 采样间隔

        Returns:
            Dict[str, float]: 响应时间统计
        """
        response_times = []

        for i in range(sample_count):
            result = await self.check_endpoint(url, method)
            if result.is_accessible and result.response_time:
                response_times.append(result.response_time)

            # Wait between samples (except for the last one)
            if i < sample_count - 1:
                await asyncio.sleep(sample_interval)

        if not response_times:
            return {
                'avg': 0.0,
                'min': 0.0,
                'max': 0.0,
                'p50': 0.0,
                'p95': 0.0,
                'p99': 0.0,
                'samples': 0
            }

        response_times.sort()

        return {
            'avg': sum(response_times) / len(response_times),
            'min': min(response_times),
            'max': max(response_times),
            'p50': response_times[len(response_times) // 2],
            'p95': response_times[int(len(response_times) * 0.95)],
            'p99': response_times[int(len(response_times) * 0.99)],
            'samples': len(response_times)
        }


# Convenience functions

async def check_api_health(
    base_url: str,
    health_endpoint: str = "/health",
    timeout: float = 5.0
) -> EndpointCheckResult:
    """
    检查API健康状态

    Args:
        base_url: 基础URL
        health_endpoint: 健康检查端点
        timeout: 超时时间

    Returns:
        EndpointCheckResult: 健康检查结果
    """
    url = f"{base_url.rstrip('/')}{health_endpoint}"

    async with APIUtils(timeout=timeout) as api_utils:
        return await api_utils.check_endpoint(url)


async def check_api_docs(
    base_url: str,
    docs_endpoint: str = "/api/docs",
    timeout: float = 5.0
) -> EndpointCheckResult:
    """
    检查API文档可访问性

    Args:
        base_url: 基础URL
        docs_endpoint: 文档端点
        timeout: 超时时间

    Returns:
        EndpointCheckResult: 文档检查结果
    """
    url = f"{base_url.rstrip('/')}{docs_endpoint}"

    async with APIUtils(timeout=timeout) as api_utils:
        return await api_utils.check_endpoint(url)


async def measure_api_performance(
    base_url: str,
    endpoint: str = "/health",
    sample_count: int = 10,
    timeout: float = 5.0
) -> Dict[str, float]:
    """
    测量API性能

    Args:
        base_url: 基础URL
        endpoint: 测量端点
        sample_count: 采样次数
        timeout: 超时时间

    Returns:
        Dict[str, float]: 性能统计
    """
    url = f"{base_url.rstrip('/')}{endpoint}"

    async with APIUtils(timeout=timeout) as api_utils:
        return await api_utils.measure_response_time(
            url=url,
            sample_count=sample_count,
            sample_interval=0.5
        )