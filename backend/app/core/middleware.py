import time
import uuid
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import structlog

logger = structlog.get_logger()

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """请求日志中间件"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 生成请求ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        # 记录请求开始时间
        start_time = time.time()

        # 获取客户端IP
        client_ip = request.client.host if request.client else "unknown"

        # 转发代理IP处理
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()

        # 记录请求信息
        logger.info(
            "API请求开始",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            query_params=str(request.query_params),
            client_ip=client_ip,
            user_agent=request.headers.get("user-agent", "unknown")
        )

        # 处理请求
        try:
            response = await call_next(request)

            # 计算处理时间
            process_time = time.time() - start_time

            # 记录响应信息
            logger.info(
                "API请求完成",
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                process_time=round(process_time, 4),
                client_ip=client_ip
            )

            # 添加响应头
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = str(round(process_time, 4))

            return response

        except Exception as e:
            # 计算处理时间
            process_time = time.time() - start_time

            # 记录错误信息
            logger.error(
                "API请求异常",
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                error=str(e),
                error_type=type(e).__name__,
                process_time=round(process_time, 4),
                client_ip=client_ip
            )
            raise

class SecurityMiddleware(BaseHTTPMiddleware):
    """安全中间件"""

    def __init__(self, app, **kwargs):
        super().__init__(app, **kwargs)
        # 敏感路径列表
        self.sensitive_paths = ["/admin", "/config", "/debug"]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 添加安全头
        response = await call_next(request)

        # 安全HTTP头
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # 隐藏服务器信息
        response.headers["Server"] = "QuantTradingAPI"

        # 记录敏感路径访问
        if any(request.url.path.startswith(path) for path in self.sensitive_paths):
            logger.warning(
                "敏感路径访问",
                path=request.url.path,
                method=request.method,
                client_ip=request.client.host if request.client else "unknown",
                request_id=getattr(request.state, 'request_id', 'unknown')
            )

        return response

class RateLimitMiddleware(BaseHTTPMiddleware):
    """简单的频率限制中间件"""

    def __init__(self, app, **kwargs):
        super().__init__(app, **kwargs)
        # 简单的内存存储，生产环境应使用Redis
        self.request_counts = {}
        self.window_size = 60  # 时间窗口（秒）
        self.max_requests = 100  # 最大请求数

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        client_ip = request.client.host if request.client else "unknown"
        current_time = time.time()

        # 清理过期记录
        self._cleanup_expired_records(current_time)

        # 检查频率限制
        if self._is_rate_limited(client_ip, current_time):
            logger.warning(
                "频率限制触发",
                client_ip=client_ip,
                path=request.url.path,
                request_id=getattr(request.state, 'request_id', 'unknown')
            )

            from fastapi import HTTPException
            raise HTTPException(
                status_code=429,
                detail="请求过于频繁，请稍后重试",
                headers={"Retry-After": str(self.window_size)}
            )

        # 记录请求
        self._record_request(client_ip, current_time)

        return await call_next(request)

    def _cleanup_expired_records(self, current_time: float):
        """清理过期记录"""
        expired_ips = []
        for ip, requests in self.request_counts.items():
            # 移除超过时间窗口的请求
            self.request_counts[ip] = [req_time for req_time in requests if current_time - req_time < self.window_size]

            # 如果没有请求记录，标记为过期
            if not self.request_counts[ip]:
                expired_ips.append(ip)

        # 删除过期IP
        for ip in expired_ips:
            del self.request_counts[ip]

    def _is_rate_limited(self, client_ip: str, current_time: float) -> bool:
        """检查是否触发频率限制"""
        if client_ip not in self.request_counts:
            return False

        # 只考虑时间窗口内的请求
        recent_requests = [
            req_time for req_time in self.request_counts[client_ip]
            if current_time - req_time < self.window_size
        ]

        return len(recent_requests) >= self.max_requests

    def _record_request(self, client_ip: str, current_time: float):
        """记录请求"""
        if client_ip not in self.request_counts:
            self.request_counts[client_ip] = []

        self.request_counts[client_ip].append(current_time)

class PerformanceMonitoringMiddleware(BaseHTTPMiddleware):
    """性能监控中间件"""

    def __init__(self, app, **kwargs):
        super().__init__(app, **kwargs)
        # 慢请求阈值（秒）
        self.slow_request_threshold = 2.0

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()

        # 处理请求
        response = await call_next(request)

        # 计算处理时间
        process_time = time.time() - start_time

        # 记录慢请求
        if process_time > self.slow_request_threshold:
            logger.warning(
                "慢请求检测",
                path=request.url.path,
                method=request.method,
                process_time=round(process_time, 4),
                threshold=self.slow_request_threshold,
                request_id=getattr(request.state, 'request_id', 'unknown')
            )

        # 添加性能指标到响应头
        response.headers["X-Response-Time"] = str(round(process_time, 4))

        return response

# 版本控制中间件
class APIVersionMiddleware(BaseHTTPMiddleware):
    """API版本控制中间件"""

    def __init__(self, app, default_version: str = "v1", **kwargs):
        super().__init__(app, **kwargs)
        self.default_version = default_version
        self.supported_versions = ["v1"]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 从URL路径提取版本
        path_parts = request.url.path.strip("/").split("/")
        if path_parts and path_parts[0] in self.supported_versions:
            request.state.api_version = path_parts[0]
        else:
            request.state.api_version = self.default_version

        # 从请求头检查版本
        api_version = request.headers.get("API-Version", request.state.api_version)

        if api_version not in self.supported_versions:
            logger.warning(
                "不支持的API版本",
                requested_version=api_version,
                supported_versions=self.supported_versions,
                path=request.url.path,
                request_id=getattr(request.state, 'request_id', 'unknown')
            )

        request.state.api_version = api_version
        response = await call_next(request)

        # 添加版本信息到响应头
        response.headers["API-Version"] = request.state.api_version

        return response