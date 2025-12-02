from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import PlainTextResponse
from contextlib import asynccontextmanager
import structlog
import time
from datetime import datetime

from app.core.config import settings
from app.core.logging import setup_logging
from app.core.database import init_database, db_manager
from app.core.middleware import (
    RequestLoggingMiddleware,
    SecurityMiddleware,
    RateLimitMiddleware,
    PerformanceMonitoringMiddleware,
    APIVersionMiddleware
)
from app.api.v1.api import api_router
from app.utils.errors import setup_exception_handlers
from app.monitoring.metrics_endpoint import metrics_router
from app.monitoring.health import health_router

# 设置结构化日志
setup_logging()
logger = structlog.get_logger()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    logger.info("Starting up Quant Trading Platform API...")

    # 初始化数据库
    try:
        init_database()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error("Failed to initialize database", error=str(e))
        raise

    yield
    # 关闭时执行
    logger.info("Shutting down Quant Trading Platform API...")

    # 关闭数据库连接
    try:
        await db_manager.close_connections()
        logger.info("Database connections closed")
    except Exception as e:
        logger.error("Failed to close database connections", error=str(e))

# 创建FastAPI应用实例
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="量化交易单均线策略分析平台 API",
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan,
)

# 设置CORS中间件
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# 添加受信任主机中间件
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.ALLOWED_HOSTS
)

# 添加自定义中间件
app.add_middleware(APIVersionMiddleware, default_version="v1")
app.add_middleware(PerformanceMonitoringMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(SecurityMiddleware)
app.add_middleware(RequestLoggingMiddleware)

# 设置异常处理器
setup_exception_handlers(app)

# 包含API路由
app.include_router(api_router, prefix=settings.API_V1_STR)

# 包含监控路由
app.include_router(metrics_router)
app.include_router(health_router, prefix="/health")

@app.get("/")
async def root():
    """根路径健康检查"""
    return {
        "message": "量化交易单均线策略分析平台 API",
        "version": "1.0.0",
        "status": "healthy",
        "docs": f"{settings.API_V1_STR}/docs"
    }

@app.get("/health")
async def health_check():
    """详细健康检查"""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
        "api_version": settings.API_V1_STR
    }

@app.get("/metrics", response_class=PlainTextTextResponse)
async def metrics_redirect():
    """Prometheus metrics endpoint - direct mapping for AC3 compliance"""
    from app.monitoring.metrics_endpoint import metrics_exposer
    return await metrics_exposer.collect_metrics()

@app.get("/ready")
async def ready_check():
    """Readiness check - verify application is ready to handle traffic"""
    from app.monitoring.health import health_checker
    try:
        checks = await health_checker.run_all_checks()
        overall_status = health_checker.get_overall_status(checks)

        return {
            "status": overall_status.value,
            "ready": overall_status.value in ["healthy", "degraded"],
            "timestamp": datetime.utcnow().isoformat(),
            "checks": len(checks)
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "ready": False,
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }

@app.get("/status")
async def status_check():
    """Detailed system status - complete system information"""
    from app.monitoring.health import health_checker
    try:
        checks = await health_checker.run_all_checks()
        overall_status = health_checker.get_overall_status(checks)

        return {
            "status": overall_status.value,
            "version": "1.0.0",
            "environment": settings.ENVIRONMENT,
            "uptime_seconds": time.time() - health_checker.start_time,
            "timestamp": datetime.utcnow().isoformat(),
            "components": {check.name: check.status.value for check in checks},
            "api_version": settings.API_V1_STR
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info"
    )