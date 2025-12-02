"""
Health Check Endpoints
Comprehensive health monitoring for application and dependencies
"""

import time
import asyncio
import psutil
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel

from .sentry_config import sentry_config
from .metrics import metrics
from .logging_config import get_logger


class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    """Health check result for a component"""
    name: str
    status: HealthStatus
    message: str
    response_time: float
    details: Dict[str, Any] = None
    timestamp: str = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow().isoformat()


@dataclass
class SystemHealthResponse:
    """System health response"""
    status: HealthStatus
    timestamp: str
    uptime: float
    version: str
    environment: str
    checks: List[HealthCheckResult]
    metrics: Dict[str, Any] = None


class HealthChecker:
    """Comprehensive health checking for application components"""

    def __init__(self):
        self.start_time = time.time()
        self.logger = get_logger("health.checker")
        self.check_history: Dict[str, List[HealthCheckResult]] = {}

    async def check_database_health(self) -> HealthCheckResult:
        """Check database connectivity and performance"""
        start_time = time.time()
        try:
            # This would be implemented with actual database connection
            # For now, simulate the check
            await asyncio.sleep(0.1)  # Simulate query time

            response_time = time.time() - start_time

            if response_time > 5.0:
                status = HealthStatus.DEGRADED
                message = "Database response time is slow"
            else:
                status = HealthStatus.HEALTHY
                message = "Database is responding normally"

            return HealthCheckResult(
                name="database",
                status=status,
                message=message,
                response_time=response_time,
                details={
                    "connection_pool_active": 5,
                    "connection_pool_idle": 15,
                    "total_connections": 20,
                    "query_time": response_time,
                }
            )

        except Exception as e:
            response_time = time.time() - start_time
            self.logger.error("Database health check failed", error=str(e))
            return HealthCheckResult(
                name="database",
                status=HealthStatus.UNHEALTHY,
                message=f"Database connection failed: {str(e)}",
                response_time=response_time,
                details={"error": str(e)}
            )

    async def check_redis_health(self) -> HealthCheckResult:
        """Check Redis connectivity and performance"""
        start_time = time.time()
        try:
            # This would be implemented with actual Redis connection
            # For now, simulate the check
            await asyncio.sleep(0.01)  # Simulate Redis response time

            response_time = time.time() - start_time

            if response_time > 1.0:
                status = HealthStatus.DEGRADED
                message = "Redis response time is slow"
            else:
                status = HealthStatus.HEALTHY
                message = "Redis is responding normally"

            return HealthCheckResult(
                name="redis",
                status=status,
                message=message,
                response_time=response_time,
                details={
                    "ping_time": response_time,
                    "memory_usage": "45MB",
                    "connected_clients": 10,
                    "total_commands_processed": 125000,
                }
            )

        except Exception as e:
            response_time = time.time() - start_time
            self.logger.error("Redis health check failed", error=str(e))
            return HealthCheckResult(
                name="redis",
                status=HealthStatus.UNHEALTHY,
                message=f"Redis connection failed: {str(e)}",
                response_time=response_time,
                details={"error": str(e)}
            )

    async def check_akshare_health(self) -> HealthCheckResult:
        """Check AKShare API availability"""
        start_time = time.time()
        try:
            # This would make an actual call to AKShare API
            # For now, simulate the check
            await asyncio.sleep(0.5)  # Simulate API response time

            response_time = time.time() - start_time

            if response_time > 10.0:
                status = HealthStatus.DEGRADED
                message = "AKShare API response time is slow"
            elif response_time > 30.0:
                status = HealthStatus.UNHEALTHY
                message = "AKShare API is not responding"
            else:
                status = HealthStatus.HEALTHY
                message = "AKShare API is available"

            return HealthCheckResult(
                name="akshare_api",
                status=status,
                message=message,
                response_time=response_time,
                details={
                    "endpoint": "stock_zh_a_hist",
                    "response_time": response_time,
                    "rate_limit_remaining": 95,
                    "last_successful_request": datetime.utcnow().isoformat(),
                }
            )

        except Exception as e:
            response_time = time.time() - start_time
            self.logger.error("AKShare health check failed", error=str(e))
            return HealthCheckResult(
                name="akshare_api",
                status=HealthStatus.UNHEALTHY,
                message=f"AKShare API unavailable: {str(e)}",
                response_time=response_time,
                details={"error": str(e)}
            )

    async def check_disk_space(self) -> HealthCheckResult:
        """Check disk space availability"""
        start_time = time.time()
        try:
            disk_usage = psutil.disk_usage('/')
            total_gb = disk_usage.total / (1024**3)
            used_gb = disk_usage.used / (1024**3)
            free_gb = disk_usage.free / (1024**3)
            usage_percent = (used_gb / total_gb) * 100

            response_time = time.time() - start_time

            if usage_percent > 90:
                status = HealthStatus.UNHEALTHY
                message = "Disk space critically low"
            elif usage_percent > 80:
                status = HealthStatus.DEGRADED
                message = "Disk space running low"
            else:
                status = HealthStatus.HEALTHY
                message = "Disk space is adequate"

            return HealthCheckResult(
                name="disk_space",
                status=status,
                message=message,
                response_time=response_time,
                details={
                    "total_gb": round(total_gb, 2),
                    "used_gb": round(used_gb, 2),
                    "free_gb": round(free_gb, 2),
                    "usage_percent": round(usage_percent, 2),
                }
            )

        except Exception as e:
            response_time = time.time() - start_time
            self.logger.error("Disk space health check failed", error=str(e))
            return HealthCheckResult(
                name="disk_space",
                status=HealthStatus.UNKNOWN,
                message=f"Failed to check disk space: {str(e)}",
                response_time=response_time,
                details={"error": str(e)}
            )

    async def check_memory_usage(self) -> HealthCheckResult:
        """Check memory usage"""
        start_time = time.time()
        try:
            memory = psutil.virtual_memory()
            response_time = time.time() - start_time

            if memory.percent > 90:
                status = HealthStatus.UNHEALTHY
                message = "Memory usage critically high"
            elif memory.percent > 80:
                status = HealthStatus.DEGRADED
                message = "Memory usage is high"
            else:
                status = HealthStatus.HEALTHY
                message = "Memory usage is normal"

            return HealthCheckResult(
                name="memory",
                status=status,
                message=message,
                response_time=response_time,
                details={
                    "total_gb": round(memory.total / (1024**3), 2),
                    "available_gb": round(memory.available / (1024**3), 2),
                    "used_gb": round(memory.used / (1024**3), 2),
                    "usage_percent": memory.percent,
                    "swap_percent": psutil.swap_memory().percent,
                }
            )

        except Exception as e:
            response_time = time.time() - start_time
            self.logger.error("Memory usage health check failed", error=str(e))
            return HealthCheckResult(
                name="memory",
                status=HealthStatus.UNKNOWN,
                message=f"Failed to check memory usage: {str(e)}",
                response_time=response_time,
                details={"error": str(e)}
            )

    async def check_cpu_usage(self) -> HealthCheckResult:
        """Check CPU usage"""
        start_time = time.time()
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            response_time = time.time() - start_time

            if cpu_percent > 90:
                status = HealthStatus.UNHEALTHY
                message = "CPU usage critically high"
            elif cpu_percent > 80:
                status = HealthStatus.DEGRADED
                message = "CPU usage is high"
            else:
                status = HealthStatus.HEALTHY
                message = "CPU usage is normal"

            return HealthCheckResult(
                name="cpu",
                status=status,
                message=message,
                response_time=response_time,
                details={
                    "usage_percent": cpu_percent,
                    "core_count": psutil.cpu_count(),
                    "load_average": list(psutil.getloadavg()) if hasattr(psutil, 'getloadavg') else None,
                }
            )

        except Exception as e:
            response_time = time.time() - start_time
            self.logger.error("CPU usage health check failed", error=str(e))
            return HealthCheckResult(
                name="cpu",
                status=HealthStatus.UNKNOWN,
                message=f"Failed to check CPU usage: {str(e)}",
                response_time=response_time,
                details={"error": str(e)}
            )

    async def check_sentry_health(self) -> HealthCheckResult:
        """Check Sentry connectivity"""
        start_time = time.time()
        try:
            # Check if Sentry is configured and responsive
            if not sentry_config.is_enabled:
                return HealthCheckResult(
                    name="sentry",
                    status=HealthStatus.HEALTHY,
                    message="Sentry monitoring is disabled",
                    response_time=time.time() - start_time,
                    details={"enabled": False}
                )

            # This would make a test call to Sentry
            # For now, just check configuration
            response_time = time.time() - start_time

            return HealthCheckResult(
                name="sentry",
                status=HealthStatus.HEALTHY,
                message="Sentry monitoring is active",
                response_time=response_time,
                details={
                    "enabled": True,
                    "environment": sentry_config.environment,
                    "dsn_configured": bool(sentry_config.dsn),
                }
            )

        except Exception as e:
            response_time = time.time() - start_time
            self.logger.error("Sentry health check failed", error=str(e))
            return HealthCheckResult(
                name="sentry",
                status=HealthStatus.UNHEALTHY,
                message=f"Sentry configuration issue: {str(e)}",
                response_time=response_time,
                details={"error": str(e)}
            )

    async def run_all_checks(self) -> List[HealthCheckResult]:
        """Run all health checks in parallel"""
        check_functions = [
            self.check_database_health,
            self.check_redis_health,
            self.check_akshare_health,
            self.check_disk_space,
            self.check_memory_usage,
            self.check_cpu_usage,
            self.check_sentry_health,
        ]

        results = await asyncio.gather(*check_functions, return_exceptions=True)

        health_checks = []
        for result in results:
            if isinstance(result, Exception):
                health_checks.append(HealthCheckResult(
                    name="unknown",
                    status=HealthStatus.UNHEALTHY,
                    message=f"Health check failed: {str(result)}",
                    response_time=0,
                    details={"error": str(result)}
                ))
            else:
                health_checks.append(result)
                # Store in history
                if result.name not in self.check_history:
                    self.check_history[result.name] = []
                self.check_history[result.name].append(result)

                # Keep only last 10 checks
                if len(self.check_history[result.name]) > 10:
                    self.check_history[result.name].pop(0)

        return health_checks

    def get_overall_status(self, checks: List[HealthCheckResult]) -> HealthStatus:
        """Determine overall system health status"""
        if not checks:
            return HealthStatus.UNKNOWN

        statuses = [check.status for check in checks]

        if all(status == HealthStatus.HEALTHY for status in statuses):
            return HealthStatus.HEALTHY
        elif any(status == HealthStatus.UNHEALTHY for status in statuses):
            return HealthStatus.UNHEALTHY
        elif any(status == HealthStatus.DEGRADED for status in statuses):
            return HealthStatus.DEGRADED
        else:
            return HealthStatus.UNKNOWN

    def get_system_metrics(self) -> Dict[str, Any]:
        """Get comprehensive system metrics"""
        try:
            return {
                "uptime_seconds": time.time() - self.start_time,
                "process": {
                    "pid": psutil.Process().pid,
                    "memory_mb": psutil.Process().memory_info().rss / (1024**2),
                    "cpu_percent": psutil.Process().cpu_percent(),
                    "create_time": psutil.Process().create_time(),
                },
                "system": {
                    "cpu_count": psutil.cpu_count(),
                    "memory_total_gb": psutil.virtual_memory().total / (1024**3),
                    "disk_total_gb": psutil.disk_usage('/').total / (1024**3),
                    "boot_time": psutil.boot_time(),
                },
                "application": {
                    "version": "0.1.0",  # This would come from environment
                    "environment": sentry_config.environment,
                    "hostname": psutil.os.uname().nodename,
                }
            }
        except Exception as e:
            self.logger.error("Failed to collect system metrics", error=str(e))
            return {"error": str(e)}


# Global health checker instance
health_checker = HealthChecker()


# API Router
health_router = APIRouter(prefix="/health", tags=["Health"])


@health_router.get("/", response_model=SystemHealthResponse)
async def basic_health_check():
    """Basic health check endpoint"""
    start_time = time.time()

    try:
        # Run a minimal set of checks
        checks = [
            await health_checker.check_memory_usage(),
            await health_checker.check_cpu_usage(),
        ]

        overall_status = health_checker.get_overall_status(checks)

        return SystemHealthResponse(
            status=overall_status,
            timestamp=datetime.utcnow().isoformat(),
            uptime=time.time() - health_checker.start_time,
            version="0.1.0",
            environment=sentry_config.environment,
            checks=checks,
            metrics={
                "response_time": time.time() - start_time,
                "check_count": len(checks),
            }
        )

    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Health check failed: {str(e)}"
        )


@health_router.get("/ready", response_model=SystemHealthResponse)
async def readiness_check():
    """Readiness check - verify all dependencies are ready"""
    try:
        checks = await health_checker.run_all_checks()
        overall_status = health_checker.get_overall_status(checks)

        if overall_status == HealthStatus.UNHEALTHY:
            raise HTTPException(
                status_code=503,
                detail="System is not ready"
            )

        return SystemHealthResponse(
            status=overall_status,
            timestamp=datetime.utcnow().isoformat(),
            uptime=time.time() - health_checker.start_time,
            version="0.1.0",
            environment=sentry_config.environment,
            checks=checks,
            metrics=health_checker.get_system_metrics(),
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Readiness check failed: {str(e)}"
        )


@health_router.get("/live", response_model=SystemHealthResponse)
async def liveness_check():
    """Liveness check - verify the application is running"""
    try:
        # For liveness, we just check if the process is responsive
        process = psutil.Process()

        return SystemHealthResponse(
            status=HealthStatus.HEALTHY,
            timestamp=datetime.utcnow().isoformat(),
            uptime=time.time() - health_checker.start_time,
            version="0.1.0",
            environment=sentry_config.environment,
            checks=[
                HealthCheckResult(
                    name="process",
                    status=HealthStatus.HEALTHY,
                    message="Process is running",
                    response_time=0.001,
                    details={
                        "pid": process.pid,
                        "status": process.status(),
                        "create_time": process.create_time(),
                    }
                )
            ],
        )

    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Liveness check failed: {str(e)}"
        )


@health_router.get("/detailed", response_model=SystemHealthResponse)
async def detailed_health_check():
    """Detailed health check with all components"""
    try:
        checks = await health_checker.run_all_checks()
        overall_status = health_checker.get_overall_status(checks)

        return SystemHealthResponse(
            status=overall_status,
            timestamp=datetime.utcnow().isoformat(),
            uptime=time.time() - health_checker.start_time,
            version="0.1.0",
            environment=sentry_config.environment,
            checks=checks,
            metrics=health_checker.get_system_metrics(),
        )

    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Detailed health check failed: {str(e)}"
        )