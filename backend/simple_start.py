#!/usr/bin/env python3
"""
简化的FastAPI启动脚本 - 跳过数据库初始化
"""
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.api import api_router
from app.core.config import settings

# 创建FastAPI应用实例
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="量化交易单均线策略分析平台 API",
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
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

# 包含API路由
app.include_router(api_router, prefix=settings.API_V1_STR)

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

if __name__ == "__main__":
    uvicorn.run(
        "simple_start:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )