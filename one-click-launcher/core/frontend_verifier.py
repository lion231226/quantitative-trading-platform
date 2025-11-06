"""
前端应用访问性验证器

提供前端应用访问性检查、页面加载验证和响应时间监控功能。
"""

import asyncio
import aiohttp
import time
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import re
from urllib.parse import urljoin, urlparse

from core.health_checker import HealthChecker, HealthCheckResult, HealthStatus
from utils.frontend_logger import get_frontend_logger

logger = get_frontend_logger()


class VerificationStatus(Enum):
    """验证状态"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    PASSED = "passed"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class AccessibilityConfig:
    """访问性验证配置"""
    url: str
    timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 2.0
    expected_status_codes: List[int] = None
    expected_content_patterns: List[str] = None
    forbidden_patterns: List[str] = None
    response_time_threshold: float = 5.0
    check_resources: bool = True
    verify_rendering: bool = True

    def __post_init__(self):
        if self.expected_status_codes is None:
            self.expected_status_codes = [200]
        if self.expected_content_patterns is None:
            self.expected_content_patterns = []
        if self.forbidden_patterns is None:
            self.forbidden_patterns = []


@dataclass
class AccessibilityResult:
    """访问性验证结果"""
    url: str
    status: VerificationStatus
    response_time: float
    status_code: Optional[int] = None
    content_length: Optional[int] = None
    content_matches: Dict[str, bool] = None
    forbidden_matches: Dict[str, bool] = None
    resource_results: List[Dict[str, Any]] = None
    rendering_result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    retry_count: int = 0

    def __post_init__(self):
        if self.content_matches is None:
            self.content_matches = {}
        if self.forbidden_matches is None:
            self.forbidden_matches = {}
        if self.resource_results is None:
            self.resource_results = []


@dataclass
class ResourceCheckResult:
    """资源检查结果"""
    url: str
    resource_type: str
    status_code: Optional[int] = None
    response_time: Optional[float] = None
    content_length: Optional[int] = None
    status: VerificationStatus = VerificationStatus.PENDING
    error_message: Optional[str] = None


class FrontendAccessibilityVerifier:
    """前端访问性验证器"""

    def __init__(self):
        self.health_checker = HealthChecker()
        self.logger = logger
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        """异步上下文管理器入口"""
        connector = aiohttp.TCPConnector(
            limit=100,
            limit_per_host=20,
            ttl_dns_cache=300,
            use_dns_cache=True,
        )
        timeout = aiohttp.ClientTimeout(total=60, connect=10)
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={'User-Agent': 'One-Click-Launcher-Frontend-Verifier/1.0'}
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        if self.session:
            await self.session.close()

    async def verify_accessibility(self, config: AccessibilityConfig) -> AccessibilityResult:
        """验证前端访问性"""
        self.logger.info(f"Starting accessibility verification for {config.url}")

        result = AccessibilityResult(
            url=config.url,
            status=VerificationStatus.PENDING,
            response_time=0.0
        )

        for attempt in range(config.max_retries + 1):
            try:
                result.retry_count = attempt
                result = await self._perform_accessibility_check(config, result)

                if result.status == VerificationStatus.PASSED:
                    self.logger.info(f"Accessibility verification passed for {config.url}")
                    return result
                elif attempt < config.max_retries:
                    self.logger.log_retry_attempt(
                        "accessibility_verification", attempt + 1, config.max_retries + 1,
                        result.error_message
                    )
                    await asyncio.sleep(config.retry_delay)

            except Exception as e:
                result.error_message = str(e)
                if attempt < config.max_retries:
                    self.logger.log_retry_attempt(
                        "accessibility_verification", attempt + 1, config.max_retries + 1, str(e)
                    )
                    await asyncio.sleep(config.retry_delay)

        result.status = VerificationStatus.FAILED
        self.logger.error(f"Accessibility verification failed for {config.url}: {result.error_message}")
        return result

    async def _perform_accessibility_check(self, config: AccessibilityConfig,
                                         result: AccessibilityResult) -> AccessibilityResult:
        """执行访问性检查"""
        start_time = time.time()
        result.status = VerificationStatus.IN_PROGRESS

        try:
            # 基本HTTP请求检查
            async with self.session.get(config.url, timeout=aiohttp.ClientTimeout(total=config.timeout)) as response:
                result.status_code = response.status
                result.content_length = len(await response.text())
                result.response_time = time.time() - start_time

                # 检查状态码
                if response.status not in config.expected_status_codes:
                    result.status = VerificationStatus.FAILED
                    result.error_message = f"Unexpected status code: {response.status}"
                    return result

                # 读取内容进行模式匹配
                content = await response.text()
                await self._check_content_patterns(config, result, content)

                # 检查响应时间
                if result.response_time > config.response_time_threshold:
                    result.status = VerificationStatus.FAILED
                    result.error_message = f"Response time too slow: {result.response_time:.2f}s"
                    return result

                # 检查资源加载
                if config.check_resources:
                    await self._check_resources(config, result, content)

                # 验证页面渲染
                if config.verify_rendering:
                    await self._verify_page_rendering(config, result, content)

                # 如果所有检查都通过
                if result.status == VerificationStatus.IN_PROGRESS:
                    result.status = VerificationStatus.PASSED

        except asyncio.TimeoutError:
            result.status = VerificationStatus.TIMEOUT
            result.error_message = f"Request timeout after {config.timeout}s"
        except Exception as e:
            result.status = VerificationStatus.FAILED
            result.error_message = str(e)

        return result

    async def _check_content_patterns(self, config: AccessibilityConfig,
                                    result: AccessibilityResult, content: str):
        """检查内容模式"""
        # 检查期望的内容模式
        for pattern in config.expected_content_patterns:
            try:
                match = bool(re.search(pattern, content, re.IGNORECASE))
                result.content_matches[pattern] = match
                if not match:
                    result.status = VerificationStatus.FAILED
                    result.error_message = f"Expected content pattern not found: {pattern}"
                    return
            except re.error as e:
                result.content_matches[pattern] = False
                result.status = VerificationStatus.FAILED
                result.error_message = f"Invalid regex pattern '{pattern}': {e}"
                return

        # 检查禁止的模式
        for pattern in config.forbidden_patterns:
            try:
                match = bool(re.search(pattern, content, re.IGNORECASE))
                result.forbidden_matches[pattern] = match
                if match:
                    result.status = VerificationStatus.FAILED
                    result.error_message = f"Forbidden content pattern found: {pattern}"
                    return
            except re.error as e:
                self.logger.warning(f"Invalid forbidden regex pattern '{pattern}': {e}")

    async def _check_resources(self, config: AccessibilityConfig,
                             result: AccessibilityResult, content: str):
        """检查页面资源加载"""
        # 提取CSS、JS、图片等资源URL
        resource_patterns = [
            (r'<link[^>]+href=["\']([^"\']+)["\']', 'css'),
            (r'<script[^>]+src=["\']([^"\']+)["\']', 'js'),
            (r'<img[^>]+src=["\']([^"\']+)["\']', 'image'),
            (r'<source[^>]+src=["\']([^"\']+)["\']', 'media'),
        ]

        base_url = urlparse(config.url)

        for pattern, resource_type in resource_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                resource_url = match.group(1)

                # 转换为绝对URL
                if resource_url.startswith('//'):
                    resource_url = f"{base_url.scheme}:{resource_url}"
                elif not resource_url.startswith(('http://', 'https://')):
                    resource_url = urljoin(config.url, resource_url)

                # 检查资源
                resource_result = await self._check_single_resource(resource_url, resource_type)
                result.resource_results.append({
                    'url': resource_url,
                    'type': resource_type,
                    'status_code': resource_result.status_code,
                    'response_time': resource_result.response_time,
                    'status': resource_result.status.value,
                    'error_message': resource_result.error_message
                })

                # 如果关键资源加载失败，标记验证失败
                if (resource_type in ['css', 'js'] and
                    resource_result.status == VerificationStatus.FAILED):
                    result.status = VerificationStatus.FAILED
                    result.error_message = f"Critical resource failed to load: {resource_url}"
                    return

    async def _check_single_resource(self, url: str, resource_type: str) -> ResourceCheckResult:
        """检查单个资源"""
        result = ResourceCheckResult(
            url=url,
            resource_type=resource_type,
            status=VerificationStatus.PENDING
        )

        try:
            start_time = time.time()
            async with self.session.head(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                result.status_code = response.status
                result.response_time = time.time() - start_time

                if 'content-length' in response.headers:
                    result.content_length = int(response.headers['content-length'])

                # 检查状态码
                if response.status == 200:
                    result.status = VerificationStatus.PASSED
                else:
                    result.status = VerificationStatus.FAILED
                    result.error_message = f"HTTP {response.status}"

        except asyncio.TimeoutError:
            result.status = VerificationStatus.TIMEOUT
            result.error_message = "Resource request timeout"
        except Exception as e:
            result.status = VerificationStatus.FAILED
            result.error_message = str(e)

        return result

    async def _verify_page_rendering(self, config: AccessibilityConfig,
                                   result: AccessibilityResult, content: str):
        """验证页面渲染完整性"""
        rendering_checks = {
            'has_html_structure': bool(re.search(r'<html[^>]*>', content, re.IGNORECASE)),
            'has_head_section': bool(re.search(r'<head[^>]*>.*?</head>', content, re.IGNORECASE | re.DOTALL)),
            'has_body_section': bool(re.search(r'<body[^>]*>.*?</body>', content, re.IGNORECASE | re.DOTALL)),
            'has_title_tag': bool(re.search(r'<title[^>]*>.*?</title>', content, re.IGNORECASE)),
            'has_meta_viewport': bool(re.search(r'<meta[^>]+name=["\']viewport["\']', content, re.IGNORECASE)),
            'has_react_root': bool(re.search(r'<div[^>]+id=["\']root["\']', content, re.IGNORECASE)),
            'has_no_critical_errors': not bool(re.search(r'<[^>]+error[^>]*>', content, re.IGNORECASE)),
        }

        result.rendering_result = rendering_checks

        # 检查关键渲染元素
        critical_checks = ['has_html_structure', 'has_head_section', 'has_body_section']
        failed_critical = [check for check in critical_checks if not rendering_checks[check]]

        if failed_critical:
            result.status = VerificationStatus.FAILED
            result.error_message = f"Critical rendering elements missing: {', '.join(failed_critical)}"

    async def check_response_time(self, url: str, timeout: int = 10) -> Tuple[float, bool]:
        """检查响应时间"""
        start_time = time.time()
        try:
            async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as response:
                response_time = time.time() - start_time
                return response_time, response.status == 200
        except Exception:
            return time.time() - start_time, False

    async def verify_page_loading_completeness(self, url: str,
                                             timeout: int = 30) -> Dict[str, Any]:
        """验证页面加载完整性"""
        result = {
            'url': url,
            'status': VerificationStatus.PENDING.value,
            'load_time': 0.0,
            'dom_content_loaded': False,
            'resources_loaded': False,
            'javascript_executed': False,
            'error_message': None
        }

        try:
            start_time = time.time()

            # 基本页面加载
            async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as response:
                content = await response.text()
                result['load_time'] = time.time() - start_time

                if response.status == 200:
                    result['dom_content_loaded'] = True

                    # 检查关键资源
                    resource_patterns = [
                        r'<link[^>]+href=["\']([^"\']+\.css)["\']',
                        r'<script[^>]+src=["\']([^"\']+\.js)["\']'
                    ]

                    resources_found = 0
                    for pattern in resource_patterns:
                        resources_found += len(re.findall(pattern, content, re.IGNORECASE))

                    result['resources_loaded'] = resources_found > 0

                    # 检查JavaScript执行（通过检查React应用的特征）
                    result['javascript_executed'] = bool(re.search(r'react|ReactDOM|__NEXT_DATA__', content, re.IGNORECASE))

                    if all([result['dom_content_loaded'], result['resources_loaded'], result['javascript_executed']]):
                        result['status'] = VerificationStatus.PASSED.value
                    else:
                        result['status'] = VerificationStatus.FAILED.value
                        result['error_message'] = "Page loading incomplete"
                else:
                    result['status'] = VerificationStatus.FAILED.value
                    result['error_message'] = f"HTTP {response.status}"

        except asyncio.TimeoutError:
            result['status'] = VerificationStatus.TIMEOUT.value
            result['error_message'] = "Page loading timeout"
        except Exception as e:
            result['status'] = VerificationStatus.FAILED.value
            result['error_message'] = str(e)

        return result

    async def create_accessibility_report(self, results: List[AccessibilityResult]) -> Dict[str, Any]:
        """创建访问性验证报告"""
        report = {
            'timestamp': time.time(),
            'total_checks': len(results),
            'passed': sum(1 for r in results if r.status == VerificationStatus.PASSED),
            'failed': sum(1 for r in results if r.status == VerificationStatus.FAILED),
            'timeout': sum(1 for r in results if r.status == VerificationStatus.TIMEOUT),
            'average_response_time': sum(r.response_time for r in results) / len(results) if results else 0,
            'details': []
        }

        for result in results:
            detail = {
                'url': result.url,
                'status': result.status.value,
                'response_time': result.response_time,
                'status_code': result.status_code,
                'content_length': result.content_length,
                'retry_count': result.retry_count,
                'error_message': result.error_message
            }

            if result.content_matches:
                detail['content_matches'] = result.content_matches
            if result.forbidden_matches:
                detail['forbidden_matches'] = result.forbidden_matches
            if result.resource_results:
                detail['resource_count'] = len(result.resource_results)
                detail['failed_resources'] = sum(1 for r in result.resource_results if r.get('status') == 'failed')
            if result.rendering_result:
                detail['rendering_checks'] = result.rendering_result

            report['details'].append(detail)

        return report