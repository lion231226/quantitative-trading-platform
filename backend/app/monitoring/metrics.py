"""
Metrics Collection and Export Module
Prometheus-compatible metrics for comprehensive application monitoring
"""

import time
import asyncio
from typing import Dict, Any, Optional, Callable
from functools import wraps
from contextlib import asynccontextmanager

try:
    from prometheus_client import Counter, Histogram, Gauge, Info, CollectorRegistry, generate_latest
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    print("⚠️  prometheus_client not available - metrics disabled")

from .sentry_config import add_performance_metric


class MetricsCollector:
    """Comprehensive metrics collection for trading platform"""

    def __init__(self):
        if not PROMETHEUS_AVAILABLE:
            self.enabled = False
            return

        self.enabled = True
        self.registry = CollectorRegistry()

        # HTTP metrics
        self.http_requests_total = Counter(
            'http_requests_total',
            'Total HTTP requests',
            ['method', 'endpoint', 'status_code'],
            registry=self.registry
        )

        self.http_request_duration = Histogram(
            'http_request_duration_seconds',
            'HTTP request duration in seconds',
            ['method', 'endpoint'],
            registry=self.registry
        )

        # Database metrics
        self.db_query_duration = Histogram(
            'db_query_duration_seconds',
            'Database query duration in seconds',
            ['query_type', 'table'],
            registry=self.registry
        )

        self.db_connections_active = Gauge(
            'db_connections_active',
            'Active database connections',
            registry=self.registry
        )

        # Trading operation metrics
        self.strategy_calculations_total = Counter(
            'strategy_calculations_total',
            'Total strategy calculations performed',
            ['strategy_name', 'status'],
            registry=self.registry
        )

        self.strategy_calculation_duration = Histogram(
            'strategy_calculation_duration_seconds',
            'Strategy calculation duration in seconds',
            ['strategy_name', 'data_points'],
            registry=self.registry
        )

        # Data provider metrics
        self.akshare_requests_total = Counter(
            'akshare_requests_total',
            'Total AKShare API requests',
            ['endpoint', 'status'],
            registry=self.registry
        )

        self.akshare_request_duration = Histogram(
            'akshare_request_duration_seconds',
            'AKShare API request duration in seconds',
            ['endpoint'],
            registry=self.registry
        )

        # Redis metrics
        self.redis_operations_total = Counter(
            'redis_operations_total',
            'Total Redis operations',
            ['operation', 'status'],
            registry=self.registry
        )

        self.redis_operation_duration = Histogram(
            'redis_operation_duration_seconds',
            'Redis operation duration in seconds',
            ['operation'],
            registry=self.registry
        )

        # Application metrics
        self.active_users = Gauge(
            'active_users',
            'Number of currently active users',
            registry=self.registry
        )

        self.data_processing_queue_size = Gauge(
            'data_processing_queue_size',
            'Size of data processing queue',
            registry=self.registry
        )

        # System metrics
        self.cpu_usage = Gauge(
            'cpu_usage_percent',
            'CPU usage percentage',
            registry=self.registry
        )

        self.memory_usage = Gauge(
            'memory_usage_percent',
            'Memory usage percentage',
            registry=self.registry
        )

        # Application info
        self.app_info = Info(
            'application_info',
            'Application information',
            registry=self.registry
        )

        # Initialize app info
        self._initialize_app_info()

    def _initialize_app_info(self):
        """Initialize application information"""
        import os
        self.app_info.info({
            'name': 'quant-trading-backend',
            'version': os.getenv('APP_VERSION', '0.1.0'),
            'environment': os.getenv('NODE_ENV', 'development'),
            'python_version': os.sys.version,
        })

    def record_http_request(self, method: str, endpoint: str, status_code: int, duration: float):
        """Record HTTP request metrics"""
        if not self.enabled:
            return

        self.http_requests_total.labels(
            method=method,
            endpoint=endpoint,
            status_code=str(status_code)
        ).inc()

        self.http_request_duration.labels(
            method=method,
            endpoint=endpoint
        ).observe(duration)

        # Send to Sentry if duration is high
        if duration > 5.0:  # 5 seconds threshold
            add_performance_metric('slow_http_request', duration * 1000, 'millisecond')

    def record_db_query(self, query_type: str, table: str, duration: float):
        """Record database query metrics"""
        if not self.enabled:
            return

        self.db_query_duration.labels(
            query_type=query_type,
            table=table
        ).observe(duration)

        # Alert on slow queries
        if duration > 2.0:  # 2 seconds threshold
            add_performance_metric('slow_db_query', duration * 1000, 'millisecond')

    def record_strategy_calculation(self, strategy_name: str, data_points: int, duration: float, success: bool = True):
        """Record strategy calculation metrics"""
        if not self.enabled:
            return

        status = 'success' if success else 'error'

        self.strategy_calculations_total.labels(
            strategy_name=strategy_name,
            status=status
        ).inc()

        self.strategy_calculation_duration.labels(
            strategy_name=strategy_name,
            data_points=str(data_points)
        ).observe(duration)

        # Alert on slow calculations
        if duration > 10.0:  # 10 seconds threshold
            add_performance_metric('slow_strategy_calculation', duration * 1000, 'millisecond')

    def record_akshare_request(self, endpoint: str, duration: float, success: bool = True):
        """Record AKShare API request metrics"""
        if not self.enabled:
            return

        status = 'success' if success else 'error'

        self.akshare_requests_total.labels(
            endpoint=endpoint,
            status=status
        ).inc()

        self.akshare_request_duration.labels(endpoint=endpoint).observe(duration)

        # Alert on slow API calls
        if duration > 30.0:  # 30 seconds threshold
            add_performance_metric('slow_akshare_request', duration * 1000, 'millisecond')

    def record_redis_operation(self, operation: str, duration: float, success: bool = True):
        """Record Redis operation metrics"""
        if not self.enabled:
            return

        status = 'success' if success else 'error'

        self.redis_operations_total.labels(
            operation=operation,
            status=status
        ).inc()

        self.redis_operation_duration.labels(operation=operation).observe(duration)

    def update_active_users(self, count: int):
        """Update active users gauge"""
        if not self.enabled:
            return
        self.active_users.set(count)

    def update_queue_size(self, size: int):
        """Update data processing queue size"""
        if not self.enabled:
            return
        self.data_processing_queue_size.set(size)

    def update_system_metrics(self, cpu_percent: float, memory_percent: float):
        """Update system metrics"""
        if not self.enabled:
            return

        self.cpu_usage.set(cpu_percent)
        self.memory_usage.set(memory_percent)

    def get_metrics(self) -> str:
        """Get metrics in Prometheus format"""
        if not self.enabled:
            return '# Metrics disabled - prometheus_client not available'

        return generate_latest(self.registry).decode('utf-8')


# Global metrics collector instance
metrics = MetricsCollector()


def timed(metric_name: Optional[str] = None,
         labels: Optional[Dict[str, str]] = None,
         histogram: Optional['Histogram'] = None):
    """Decorator to measure function execution time"""
    def decorator(func: Callable):
        name = metric_name or f"{func.__module__}.{func.__name__}"

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            if not metrics.enabled:
                return await func(*args, **kwargs)

            start_time = time.time()
            try:
                result = await func(*args, **kwargs)

                # Record success metric
                if histogram:
                    histogram.observe(time.time() - start_time)
                else:
                    add_performance_metric(name, (time.time() - start_time) * 1000, 'millisecond')

                return result
            except Exception as e:
                # Record error metric
                add_performance_metric(f"{name}_error", (time.time() - start_time) * 1000, 'millisecond')
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            if not metrics.enabled:
                return func(*args, **kwargs)

            start_time = time.time()
            try:
                result = func(*args, **kwargs)

                # Record success metric
                if histogram:
                    histogram.observe(time.time() - start_time)
                else:
                    add_performance_metric(name, (time.time() - start_time) * 1000, 'millisecond')

                return result
            except Exception as e:
                # Record error metric
                add_performance_metric(f"{name}_error", (time.time() - start_time) * 1000, 'millisecond')
                raise

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


@asynccontextmanager
async def measure_time(operation_name: str, labels: Optional[Dict[str, str]] = None):
    """Context manager to measure execution time"""
    if not metrics.enabled:
        yield
        return

    start_time = time.time()
    try:
        yield
    finally:
        duration = time.time() - start_time
        add_performance_metric(operation_name, duration * 1000, 'millisecond')


# Specific decorators for common operations
@timed(metric_name="database_query", histogram=metrics.db_query_duration)
def measure_db_query(func: Callable):
    """Decorator for database query timing"""
    return func


@timed(metric_name="akshare_request", histogram=metrics.akshare_request_duration)
def measure_akshare_request(func: Callable):
    """Decorator for AKShare API request timing"""
    return func


@timed(metric_name="strategy_calculation", histogram=metrics.strategy_calculation_duration)
def measure_strategy_calculation(func: Callable):
    """Decorator for strategy calculation timing"""
    return func


class PerformanceMonitor:
    """High-level performance monitoring interface"""

    def __init__(self):
        self.operation_counts: Dict[str, int] = {}
        self.operation_times: Dict[str, list] = {}

    def start_operation(self, operation_name: str) -> str:
        """Start monitoring an operation"""
        operation_id = f"{operation_name}_{int(time.time() * 1000000)}"

        # Add breadcrumb
        from .sentry_config import sentry_config
        if sentry_config.is_enabled:
            import sentry_sdk
            sentry_sdk.addBreadcrumb({
                'category': 'performance',
                'message': f'Started operation: {operation_name}',
                'level': 'info',
                'data': {'operation_id': operation_id}
            })

        return operation_id

    def end_operation(self, operation_name: str, operation_id: str, success: bool = True, metadata: Optional[Dict] = None):
        """End monitoring an operation"""
        duration = time.time() - float(operation_id.split('_')[-1]) / 1000000

        # Update statistics
        if operation_name not in self.operation_counts:
            self.operation_counts[operation_name] = 0
            self.operation_times[operation_name] = []

        self.operation_counts[operation_name] += 1
        self.operation_times[operation_name].append(duration)

        # Send to Sentry
        status = 'success' if success else 'error'
        add_performance_metric(f"{operation_name}_{status}", duration * 1000, 'millisecond')

        # Add breadcrumb
        from .sentry_config import sentry_config
        if sentry_config.is_enabled:
            import sentry_sdk
            sentry_sdk.addBreadcrumb({
                'category': 'performance',
                'message': f'Completed operation: {operation_name}',
                'level': 'info',
                'data': {
                    'operation_id': operation_id,
                    'duration_ms': duration * 1000,
                    'success': success,
                    'metadata': metadata
                }
            })

    def get_operation_stats(self, operation_name: str) -> Dict[str, Any]:
        """Get statistics for an operation"""
        if operation_name not in self.operation_counts:
            return {}

        times = self.operation_times[operation_name]
        return {
            'count': len(times),
            'total_time': sum(times),
            'average_time': sum(times) / len(times),
            'min_time': min(times),
            'max_time': max(times),
            'success_rate': 1.0, # This would need to be tracked separately
        }

    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all operations"""
        return {
            op_name: self.get_operation_stats(op_name)
            for op_name in self.operation_counts.keys()
        }


# Global performance monitor
performance_monitor = PerformanceMonitor()