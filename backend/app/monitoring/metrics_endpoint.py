"""
Metrics Endpoint
Prometheus-compatible metrics exposition for application monitoring
"""

import time
import asyncio
from typing import Dict, Any
from datetime import datetime, timedelta

from fastapi import APIRouter, Response
from fastapi.responses import PlainTextResponse

from .metrics import metrics, performance_monitor
from .health import health_checker
from .logging_config import get_logger


class MetricsExposer:
    """Prometheus metrics exposition"""

    def __init__(self):
        self.logger = get_logger("metrics.exposer")
        self.last_collection_time = 0

    async def collect_metrics(self) -> str:
        """Collect and format all metrics in Prometheus format"""
        try:
            start_time = time.time()

            # Get base metrics from Prometheus collector
            metrics_text = metrics.get_metrics()

            # Add custom application metrics
            custom_metrics = await self.collect_custom_metrics()

            # Combine all metrics
            all_metrics = f"""# Custom application metrics
{custom_metrics}

# Prometheus metrics
{metrics_text}

# Collection metadata
# HELP metrics_collection_seconds Time spent collecting metrics
# TYPE metrics_collection_seconds gauge
metrics_collection_seconds {time.time() - start_time}
# HELP metrics_last_collection_timestamp Unix timestamp of last metrics collection
# TYPE metrics_last_collection_timestamp gauge
metrics_last_collection_timestamp {time.time()}
"""

            self.last_collection_time = time.time()
            return all_metrics

        except Exception as e:
            self.logger.error("Failed to collect metrics", error=str(e))
            return f"# Error collecting metrics: {str(e)}"

    async def collect_custom_metrics(self) -> str:
        """Collect custom application-specific metrics"""
        custom_metrics = []

        # Application health metrics
        custom_metrics.extend(await self.collect_health_metrics())

        # Performance metrics
        custom_metrics.extend(await self.collect_performance_metrics())

        # Business metrics
        custom_metrics.extend(await self.collect_business_metrics())

        # System metrics
        custom_metrics.extend(await self.collect_system_metrics())

        return "\n".join(custom_metrics)

    async def collect_health_metrics(self) -> list:
        """Collect health-related metrics"""
        try:
            health_metrics = []
            checks = await health_checker.run_all_checks()

            # Health check status metrics
            for check in checks:
                status_value = {
                    "healthy": 1,
                    "degraded": 0.5,
                    "unhealthy": 0,
                    "unknown": -1
                }.get(check.status.value, -1)

                health_metrics.append(f"""# HELP health_check_status Health check status (1=healthy, 0.5=degraded, 0=unhealthy, -1=unknown)
# TYPE health_check_status gauge
health_check_status{{component="{check.name}"}} {status_value}""")

                health_metrics.append(f"""# HELP health_check_response_time_seconds Health check response time in seconds
# TYPE health_check_response_time_seconds gauge
health_check_response_time_seconds{{component="{check.name}"}} {check.response_time}""")

            return health_metrics

        except Exception as e:
            self.logger.error("Failed to collect health metrics", error=str(e))
            return []

    async def collect_performance_metrics(self) -> list:
        """Collect performance-related metrics"""
        try:
            perf_metrics = []
            stats = performance_monitor.get_all_stats()

            for operation_name, operation_stats in stats.items():
                if operation_stats.get('count', 0) > 0:
                    perf_metrics.append(f"""# HELP operation_total Total number of operations performed
# TYPE operation_total counter
operation_total{{operation="{operation_name}"}} {operation_stats.get('count', 0)}""")

                    perf_metrics.append(f"""# HELP operation_duration_seconds Average operation duration in seconds
# TYPE operation_duration_seconds gauge
operation_duration_seconds{{operation="{operation_name}"}} {operation_stats.get('average_time', 0)}""")

                    perf_metrics.append(f"""# HELP operation_duration_seconds_max Maximum operation duration in seconds
# TYPE operation_duration_seconds_max gauge
operation_duration_seconds_max{{operation="{operation_name}"}} {operation_stats.get('max_time', 0)}""")

            return perf_metrics

        except Exception as e:
            self.logger.error("Failed to collect performance metrics", error=str(e))
            return []

    async def collect_business_metrics(self) -> list:
        """Collect business-related metrics"""
        try:
            business_metrics = []

            # Strategy calculation metrics (these would come from actual business logic)
            business_metrics.append("""# HELP strategy_calculations_total Total number of strategy calculations performed
# TYPE strategy_calculations_total counter
strategy_calculations_total 0""")

            business_metrics.append("""# HELP strategy_calculation_success_rate Strategy calculation success rate (0-1)
# TYPE strategy_calculation_success_rate gauge
strategy_calculation_success_rate 0""")

            # User activity metrics
            business_metrics.append("""# HELP active_users Current number of active users
# TYPE active_users gauge
active_users 0""")

            # Data processing metrics
            business_metrics.append("""# HELP data_processing_queue_size Current size of data processing queue
# TYPE data_processing_queue_size gauge
data_processing_queue_size 0""")

            return business_metrics

        except Exception as e:
            self.logger.error("Failed to collect business metrics", error=str(e))
            return []

    async def collect_system_metrics(self) -> list:
        """Collect system-related metrics"""
        try:
            import psutil

            system_metrics = []

            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            system_metrics.append(f"""# HELP system_cpu_usage_percent CPU usage percentage
# TYPE system_cpu_usage_percent gauge
system_cpu_usage_percent {cpu_percent}""")

            system_metrics.append(f"""# HELP system_cpu_count Number of CPU cores
# TYPE system_cpu_count gauge
system_cpu_count {psutil.cpu_count()}""")

            # Memory metrics
            memory = psutil.virtual_memory()
            system_metrics.append(f"""# HELP system_memory_usage_percent Memory usage percentage
# TYPE system_memory_usage_percent gauge
system_memory_usage_percent {memory.percent}""")

            system_metrics.append(f"""# HELP system_memory_available_bytes Available memory in bytes
# TYPE system_memory_available_bytes gauge
system_memory_available_bytes {memory.available}""")

            system_metrics.append(f"""# HELP system_memory_total_bytes Total memory in bytes
# TYPE system_memory_total_bytes gauge
system_memory_total_bytes {memory.total}""")

            # Disk metrics
            disk = psutil.disk_usage('/')
            disk_usage_percent = (disk.used / disk.total) * 100
            system_metrics.append(f"""# HELP system_disk_usage_percent Disk usage percentage
# TYPE system_disk_usage_percent gauge
system_disk_usage_percent {disk_usage_percent}""")

            system_metrics.append(f"""# HELP system_disk_free_bytes Free disk space in bytes
# TYPE system_disk_free_bytes gauge
system_disk_free_bytes {disk.free}""")

            system_metrics.append(f"""# HELP system_disk_total_bytes Total disk space in bytes
# TYPE system_disk_total_bytes gauge
system_disk_total_bytes {disk.total}""")

            # Process metrics
            process = psutil.Process()
            process_memory = process.memory_info()
            system_metrics.append(f"""# HELP process_memory_bytes Process memory usage in bytes
# TYPE process_memory_bytes gauge
process_memory_bytes {process_memory.rss}""")

            system_metrics.append(f"""# HELP process_cpu_usage_percent Process CPU usage percentage
# TYPE process_cpu_usage_percent gauge
process_cpu_usage_percent {process.cpu_percent()}""")

            # Uptime metrics
            uptime = time.time() - health_checker.start_time
            system_metrics.append(f"""# HELP application_uptime_seconds Application uptime in seconds
# TYPE application_uptime_seconds counter
application_uptime_seconds {uptime}""")

            return system_metrics

        except Exception as e:
            self.logger.error("Failed to collect system metrics", error=str(e))
            return []


# Global metrics exposer instance
metrics_exposer = MetricsExposer()

# API Router
metrics_router = APIRouter(prefix="/metrics", tags=["Metrics"])


@metrics_router.get("/", response_class=PlainTextTextResponse)
async def get_metrics():
    """Get Prometheus-formatted metrics"""
    return await metrics_exposer.collect_metrics()


@metrics_router.get("/prometheus", response_class=PlainTextTextResponse)
async def get_prometheus_metrics():
    """Alias for Prometheus metrics endpoint"""
    return await metrics_exposer.collect_metrics()


@metrics_router.get("/health")
async def metrics_health():
    """Health check for metrics endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "last_collection": metrics_exposer.last_collection_time,
    }


@metrics_router.get("/info")
async def get_metrics_info():
    """Get information about available metrics"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "metrics_available": {
            "http_requests_total": "Total HTTP requests by method, endpoint, and status code",
            "http_request_duration_seconds": "HTTP request duration in seconds",
            "health_check_status": "Health check status for each component",
            "health_check_response_time_seconds": "Health check response time in seconds",
            "operation_total": "Total number of operations performed",
            "operation_duration_seconds": "Average operation duration in seconds",
            "system_cpu_usage_percent": "System CPU usage percentage",
            "system_memory_usage_percent": "System memory usage percentage",
            "system_disk_usage_percent": "System disk usage percentage",
            "application_uptime_seconds": "Application uptime in seconds",
        },
        "collection_frequency": "On-demand via HTTP request",
        "format": "Prometheus text-based format",
    }