"""
Distributed Tracing Middleware
Comprehensive request tracing across services and dependencies
"""

import time
import uuid
import asyncio
from typing import Dict, Any, Optional, Callable, List
from functools import wraps
from contextlib import asynccontextmanager

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from sentry_config import sentry_config, set_transaction_name
from metrics import metrics, performance_monitor


class TraceContext:
    """Trace context for distributed tracing"""

    def __init__(self, trace_id: str = None, parent_span_id: str = None):
        self.trace_id = trace_id or str(uuid.uuid4())
        self.parent_span_id = parent_span_id
        self.span_id = str(uuid.uuid4())[:16]
        self.start_time = time.time()
        self.tags: Dict[str, str] = {}
        self.data: Dict[str, Any] = {}
        self.spans: List['Span'] = []

    def add_tag(self, key: str, value: str):
        """Add tag to trace context"""
        self.tags[key] = value

    def add_data(self, key: str, value: Any):
        """Add data to trace context"""
        self.data[key] = value

    def create_span(self, name: str, operation: str = None) -> 'Span':
        """Create a new span"""
        span = Span(name, operation, self.trace_id, self.span_id)
        self.spans.append(span)
        return span

    def get_headers(self) -> Dict[str, str]:
        """Get tracing headers for downstream calls"""
        return {
            'X-Trace-Id': self.trace_id,
            'X-Parent-Span-Id': self.span_id,
        }

    def get_duration(self) -> float:
        """Get trace duration in seconds"""
        return time.time() - self.start_time


class Span:
    """Individual span for operation tracking"""

    def __init__(self, name: str, operation: str = None, trace_id: str = None, parent_span_id: str = None):
        self.name = name
        self.operation = operation or name
        self.trace_id = trace_id or str(uuid.uuid4())
        self.parent_span_id = parent_span_id
        self.span_id = str(uuid.uuid4())[:16]
        self.start_time = time.time()
        self.end_time: Optional[float] = None
        self.tags: Dict[str, str] = {}
        self.data: Dict[str, Any] = {}
        self.status = "ok"
        self.error: Optional[Exception] = None

    def set_tag(self, key: str, value: str):
        """Set tag on span"""
        self.tags[key] = value

    def set_data(self, key: str, value: Any):
        """Set data on span"""
        self.data[key] = value

    def set_error(self, error: Exception):
        """Mark span as error"""
        self.error = error
        self.status = "error"
        self.set_tag("error", "true")
        self.set_data("error.message", str(error))
        self.set_data("error.type", type(error).__name__)

    def finish(self):
        """Finish the span"""
        self.end_time = time.time()

    def get_duration(self) -> float:
        """Get span duration in seconds"""
        if self.end_time is None:
            return time.time() - self.start_time
        return self.end_time - self.start_time

    def to_dict(self) -> Dict[str, Any]:
        """Convert span to dictionary"""
        return {
            "name": self.name,
            "operation": self.operation,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": self.get_duration(),
            "status": self.status,
            "tags": self.tags,
            "data": self.data,
            "error": str(self.error) if self.error else None,
        }


class TracingMiddleware(BaseHTTPMiddleware):
    """Distributed tracing middleware for FastAPI"""

    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.active_traces: Dict[str, TraceContext] = {}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with distributed tracing"""

        # Extract trace context from headers
        trace_id = request.headers.get("X-Trace-Id")
        parent_span_id = request.headers.get("X-Parent-Span-Id")

        # Create trace context
        trace_context = TraceContext(trace_id, parent_span_id)

        # Create root span for HTTP request
        root_span = trace_context.create_span(
            name=f"HTTP {request.method} {request.url.path}",
            operation="http.request"
        )

        # Set basic tags
        root_span.set_tag("http.method", request.method)
        root_span.set_tag("http.url", str(request.url))
        root_span.set_tag("http.host", request.url.hostname)
        root_span.set_tag("http.path", request.url.path)
        root_span.set_tag("http.scheme", request.url.scheme)

        # Store trace context in request state for access in endpoints
        request.state.trace_context = trace_context
        request.state.root_span = root_span

        # Track active trace
        self.active_traces[trace_context.trace_id] = trace_context

        try:
            # Process request
            start_time = time.time()
            response = await call_next(request)
            duration = time.time() - start_time

            # Set response tags
            root_span.set_tag("http.status_code", str(response.status_code))
            root_span.set_tag("http.status_class", self._get_status_class(response.status_code))

            # Record metrics
            metrics.record_http_request(
                method=request.method,
                endpoint=request.url.path,
                status_code=response.status_code,
                duration=duration
            )

            # Add tracing headers to response
            response.headers["X-Trace-Id"] = trace_context.trace_id
            response.headers["X-Span-Id"] = root_span.span_id

            return response

        except Exception as error:
            # Mark span as error
            root_span.set_error(error)

            # Capture error in Sentry
            from sentry_config import capture_error_with_context
            capture_error_with_context(
                error,
                context={
                    "trace_id": trace_context.trace_id,
                    "span_id": root_span.span_id,
                    "request_method": request.method,
                    "request_path": request.url.path,
                },
                tags={
                    "component": "tracing_middleware",
                    "operation": "http_request",
                }
            )

            # Re-raise the exception
            raise

        finally:
            # Finish root span and cleanup
            root_span.finish()
            self._finish_trace(trace_context)

            # Remove from active traces
            self.active_traces.pop(trace_context.trace_id, None)

    def _get_status_class(self, status_code: int) -> str:
        """Get HTTP status class"""
        if 200 <= status_code < 300:
            return "2xx"
        elif 300 <= status_code < 400:
            return "3xx"
        elif 400 <= status_code < 500:
            return "4xx"
        elif 500 <= status_code < 600:
            return "5xx"
        else:
            return "unknown"

    def _finish_trace(self, trace_context: TraceContext):
        """Finish trace and send to monitoring systems"""
        try:
            # Send to Sentry
            if sentry_config.is_enabled:
                import sentry_sdk

                # Set transaction name
                set_transaction_name(trace_context.spans[0].operation if trace_context.spans else "unknown")

                # Add breadcrumb with trace summary
                sentry_sdk.addBreadcrumb({
                    'category': 'trace',
                    'message': f'Trace completed: {trace_context.trace_id}',
                    'level': 'info',
                    'data': {
                        'trace_id': trace_context.trace_id,
                        'duration_ms': trace_context.get_duration() * 1000,
                        'span_count': len(trace_context.spans),
                        'tags': trace_context.tags,
                    }
                })

            # Send to metrics
            performance_monitor.end_operation(
                "http_request_trace",
                f"{trace_context.trace_id}_{trace_context.span_id}",
                success=trace_context.spans[-1].status == "ok" if trace_context.spans else True,
                metadata={
                    "duration_ms": trace_context.get_duration() * 1000,
                    "span_count": len(trace_context.spans),
                }
            )

        except Exception as e:
            print(f"Failed to finish trace: {e}")


def get_trace_context(request: Request) -> Optional[TraceContext]:
    """Get trace context from request"""
    return getattr(request.state, 'trace_context', None)


def get_root_span(request: Request) -> Optional[Span]:
    """Get root span from request"""
    return getattr(request.state, 'root_span', None)


@asynccontextmanager
async def trace_operation(name: str, operation: str = None, tags: Dict[str, str] = None):
    """Context manager for tracing operations"""
    trace_context = getattr(asyncio.current_task(), 'trace_context', None)

    if trace_context is None:
        trace_context = TraceContext()
        asyncio.current_task().trace_context = trace_context

    span = trace_context.create_span(name, operation)

    if tags:
        for key, value in tags.items():
            span.set_tag(key, value)

    try:
        yield span
        span.status = "ok"
    except Exception as e:
        span.set_error(e)
        raise
    finally:
        span.finish()


def trace_function(name: str = None, operation: str = None, tags: Dict[str, str] = None):
    """Decorator for tracing functions"""
    def decorator(func: Callable):
        func_name = name or f"{func.__module__}.{func.__name__}"
        func_operation = operation or func_name

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            async with trace_operation(func_name, func_operation, tags) as span:
                # Add function arguments as data (excluding sensitive info)
                span.set_data("function.name", func.__name__)
                span.set_data("function.args_count", len(args) + len(kwargs))

                try:
                    result = await func(*args, **kwargs)
                    span.set_data("function.success", True)
                    return result
                except Exception as e:
                    span.set_data("function.success", False)
                    raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # For sync functions, we need to create a simple span
            span = Span(func_name, func_operation)

            if tags:
                for key, value in tags.items():
                    span.set_tag(key, value)

            span.set_data("function.name", func.__name__)
            span.set_data("function.args_count", len(args) + len(kwargs))

            try:
                result = func(*args, **kwargs)
                span.set_data("function.success", True)
                span.status = "ok"
                return result
            except Exception as e:
                span.set_error(e)
                span.set_data("function.success", False)
                raise
            finally:
                span.finish()

                # Send to monitoring
                performance_monitor.end_operation(
                    func_name,
                    span.span_id,
                    span.status == "ok",
                    {"duration_ms": span.get_duration() * 1000}
                )

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    return decorator


class DatabaseTracer:
    """Database operation tracer"""

    @staticmethod
    async def trace_query(query: str, params: Dict[str, Any] = None, operation: str = "query"):
        async with trace_operation(
            name="database_query",
            operation=operation,
            tags={"db.operation": operation, "db.type": "sql"}
        ) as span:
            span.set_data("db.query", query[:200])  # Limit query length
            if params:
                span.set_data("db.params_count", len(params))

            start_time = time.time()
            try:
                # This would be implemented with actual database query
                # result = await database.execute(query, params)
                duration = time.time() - start_time

                span.set_data("db.duration_ms", duration * 1000)
                metrics.record_db_query(operation, "unknown", duration)

                # return result
                return None  # Placeholder
            except Exception as e:
                duration = time.time() - start_time
                span.set_data("db.duration_ms", duration * 1000)
                span.set_data("db.error", True)
                raise


class ExternalServiceTracer:
    """External service call tracer"""

    @staticmethod
    async def trace_http_call(url: str, method: str = "GET", headers: Dict[str, str] = None):
        async with trace_operation(
            name="external_http_call",
            operation="http.client",
            tags={
                "http.method": method,
                "http.url": url,
                "service.type": "external"
            }
        ) as span:
            if headers:
                # Remove sensitive headers
                safe_headers = {k: v for k, v in headers.items()
                              if k.lower() not in ['authorization', 'x-api-key']}
                span.set_data("http.headers_count", len(safe_headers))

            start_time = time.time()
            try:
                # This would be implemented with actual HTTP client
                # response = await http_client.request(method, url, headers=headers)
                duration = time.time() - start_time

                span.set_data("http.duration_ms", duration * 1000)
                # span.set_tag("http.status_code", str(response.status_code))

                # return response
                return None  # Placeholder
            except Exception as e:
                duration = time.time() - start_time
                span.set_data("http.duration_ms", duration * 1000)
                span.set_data("http.error", True)
                raise


# Global tracer instances
db_tracer = DatabaseTracer()
external_service_tracer = ExternalServiceTracer()