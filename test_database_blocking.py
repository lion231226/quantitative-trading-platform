#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库阻塞测试 - 检查数据库连接和初始化是否导致阻塞
"""

import asyncio
import time
import sys
import os
from contextlib import asynccontextmanager

# 修复Windows控制台编码问题
if sys.platform == "win32":
    os.environ['PYTHONIOENCODING'] = 'utf-8'

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import uvicorn
import structlog

# 导入原始组件
sys.path.append('D:/Demo/backend')
from app.core.config import settings
from app.core.database import init_database, db_manager
from app.core.middleware import (
    RequestLoggingMiddleware,
    SecurityMiddleware,
    RateLimitMiddleware,
    PerformanceMonitoringMiddleware,
    APIVersionMiddleware
)
from app.utils.errors import setup_exception_handlers
from app.api.v1.api import api_router

# 简化的AKShare客户端
class SimpleAKShareClient:
    async def get_available_symbols(self, sector: str = "energy"):
        """简化的期货品种获取"""
        try:
            print(f"[DEBUG] 开始获取期货品种数据: {sector}")
            start_time = time.time()

            import akshare as ak
            if sector == "energy":
                print("[DEBUG] 获取能源期货品种...")
                df = ak.futures_main_sina(symbol="SC0")
            else:
                print(f"[DEBUG] 获取默认期货品种...")
                df = ak.futures_main_sina(symbol="SC0")

            process_time = time.time() - start_time
            print(f"[DEBUG] AKShare数据获取完成，耗时: {process_time:.2f}秒")
            print(f"[DEBUG] 获取到 {len(df)} 行数据")

            if not df.empty:
                symbols = df.index.tolist()[:10]
                return {
                    "status": "success",
                    "data": {
                        "symbols": symbols,
                        "sector": sector,
                        "count": len(symbols),
                        "source": "akshare",
                        "process_time": process_time
                    },
                    "message": f"成功获取{len(symbols)}个期货品种"
                }
            else:
                return {
                    "status": "error",
                    "error": "未获取到期货品种数据",
                    "data": None
                }

        except Exception as e:
            print(f"[DEBUG] AKShare获取失败: {str(e)}")
            return {
                "status": "error",
                "error": f"数据获取失败: {str(e)}",
                "data": None
            }

# 创建测试应用函数
def create_test_app(with_database: bool = False, with_middleware: bool = False, name: str = "基础版本"):
    """创建测试应用"""

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """应用生命周期管理"""
        if with_database:
            print(f"[SETUP] {name} - 开始数据库初始化...")
            try:
                init_database()
                print(f"[SETUP] {name} - 数据库初始化成功")
            except Exception as e:
                print(f"[ERROR] {name} - 数据库初始化失败: {str(e)}")
                raise

        yield

        if with_database:
            print(f"[SETUP] {name} - 关闭数据库连接...")
            try:
                await db_manager.close_connections()
                print(f"[SETUP] {name} - 数据库连接已关闭")
            except Exception as e:
                print(f"[ERROR] {name} - 关闭数据库连接失败: {str(e)}")

    app = FastAPI(
        title=f"数据库阻塞测试 - {name}",
        description=f"测试 {name} 是否导致阻塞",
        version="1.0.0",
        lifespan=lifespan if with_database else None
    )

    # 添加CORS中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 添加受信任主机中间件
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*"]
    )

    # 添加自定义中间件
    if with_middleware:
        # 按照原版本顺序添加
        app.add_middleware(APIVersionMiddleware, default_version="v1")
        app.add_middleware(PerformanceMonitoringMiddleware)
        app.add_middleware(RateLimitMiddleware)
        app.add_middleware(SecurityMiddleware)
        app.add_middleware(RequestLoggingMiddleware)
        print(f"[SETUP] {name} - 已添加所有中间件")

    # 设置异常处理器
    if with_database or with_middleware:
        setup_exception_handlers(app)
        print(f"[SETUP] {name} - 已设置异常处理器")

    # 创建AKShare客户端
    akshare_client = SimpleAKShareClient()

    @app.get("/")
    async def root():
        return {"message": f"数据库阻塞测试: {name}", "status": "ok"}

    @app.get("/health")
    async def health():
        return {
            "status": "healthy",
            "test_name": name,
            "database": with_database,
            "middleware": with_middleware
        }

    @app.get("/api/v1/market-data/symbols")
    async def get_symbols_test(sector: str = "energy"):
        """期货品种获取端点"""
        try:
            print(f"[INFO] [{name}] 接收到期货品种请求: sector={sector}")
            start_time = time.time()

            result = await akshare_client.get_available_symbols(sector)
            process_time = time.time() - start_time

            print(f"[INFO] [{name}] 期货品种请求处理完成，耗时: {process_time:.2f}秒")
            return JSONResponse(content=result)

        except Exception as e:
            print(f"[ERROR] [{name}] 期货品种请求处理失败: {str(e)}")
            raise HTTPException(status_code=500, detail=f"服务器内部错误: {str(e)}")

    # 如果有数据库和中间件，也添加原始路由
    if with_database and with_middleware:
        app.include_router(api_router, prefix=settings.API_V1_STR)
        print(f"[SETUP] {name} - 已包含原始API路由")

    return app

async def test_version(with_database: bool, with_middleware: bool, name: str, port: int):
    """测试指定版本"""
    print(f"\n{'='*60}")
    print(f"测试版本: {name}")
    print(f"端口: {port}")
    print(f"数据库: {with_database}, 中间件: {with_middleware}")
    print(f"{'='*60}")

    # 创建测试应用
    app = create_test_app(with_database, with_middleware, name)

    # 在后台启动服务器
    config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="error")
    server = uvicorn.Server(config)

    # 启动服务器
    import threading
    server_task = threading.Thread(target=server.run, daemon=True)
    server_task.start()

    # 等待服务器启动（数据库初始化可能需要更长时间）
    await asyncio.sleep(5 if with_database else 2)

    # 测试API
    try:
        print(f"[TEST] 测试 {name} 的期货品种API...")
        start_time = time.time()

        import aiohttp
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=20)) as session:
            async with session.get(f"http://localhost:{port}/api/v1/market-data/symbols") as response:
                if response.status == 200:
                    data = await response.json()
                    elapsed = time.time() - start_time
                    print(f"[SUCCESS] {name}: 响应正常 ({elapsed:.2f}秒)")
                    print(f"  数据: {data.get('status', 'unknown')}")
                    return True, elapsed
                else:
                    elapsed = time.time() - start_time
                    print(f"[FAIL] {name}: HTTP {response.status} ({elapsed:.2f}秒)")
                    return False, elapsed

    except asyncio.TimeoutError:
        elapsed = time.time() - start_time
        print(f"[TIMEOUT] {name}: 请求超时 ({elapsed:.2f}秒)")
        return False, elapsed
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"[ERROR] {name}: {str(e)} ({elapsed:.2f}秒)")
        return False, elapsed

    finally:
        # 关闭服务器
        server.should_exit = True
        await asyncio.sleep(1)

async def main():
    """主测试函数"""
    print("=" * 80)
    print("数据库阻塞测试 - 检查数据库连接是否导致阻塞")
    print("=" * 80)

    # 渐进式测试配置
    test_configs = [
        # 基础版本
        (False, False, "基础版本（无数据库无中间件）", 8030),

        # 单独测试数据库
        (True, False, "仅数据库（无中间件）", 8031),

        # 单独测试中间件
        (False, True, "仅中间件（无数据库）", 8032),

        # 完整版本（模拟原版本）
        (True, True, "完整版本（数据库+中间件）", 8033),
    ]

    results = []

    for with_database, with_middleware, name, port in test_configs:
        success, elapsed = await test_version(with_database, with_middleware, name, port)
        results.append({
            "name": name,
            "database": with_database,
            "middleware": with_middleware,
            "success": success,
            "elapsed": elapsed,
            "status": "PASS" if success else "FAIL"
        })

    # 汇总结果
    print(f"\n{'='*80}")
    print("测试结果汇总")
    print(f"{'='*80}")
    print(f"{'版本':<30} {'数据库':<8} {'中间件':<8} {'状态':<8} {'响应时间':<10}")
    print("-" * 75)

    for result in results:
        db_str = "YES" if result["database"] else "NO"
        mw_str = "YES" if result["middleware"] else "NO"
        status = result["status"]
        elapsed = f"{result['elapsed']:.2f}s"
        print(f"{result['name']:<30} {db_str:<8} {mw_str:<8} {status:<8} {elapsed:<10}")

    # 分析结果
    failed = [r for r in results if not r["success"]]
    if failed:
        print(f"\n[发现] 问题配置:")
        for f in failed:
            print(f"  - {f['name']}: {f['elapsed']:.2f}秒")

        # 分析数据库影响
        db_results = [r for r in results if r["database"]]
        mw_results = [r for r in results if r["middleware"]]

        db_failed = [r for r in db_results if not r["success"]]
        mw_failed = [r for r in mw_results if not r["success"]]

        if db_failed and not mw_failed:
            print(f"\n[结论] 数据库初始化是导致阻塞的原因")
        elif mw_failed and not db_failed:
            print(f"\n[结论] 中间件是导致阻塞的原因")
        elif db_failed and mw_failed:
            print(f"\n[结论] 数据库和中间件的组合导致阻塞")
        else:
            print(f"\n[结论] 阻塞原因需要进一步调查")
    else:
        print(f"\n[结论] 所有配置测试通过，阻塞原因在其他地方")

if __name__ == "__main__":
    asyncio.run(main())