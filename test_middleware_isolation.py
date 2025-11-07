#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
中间件隔离测试 - 逐个测试中间件找出阻塞元凶
"""

import asyncio
import time
import sys
import os

# 修复Windows控制台编码问题
if sys.platform == "win32":
    os.environ['PYTHONIOENCODING'] = 'utf-8'

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
import uvicorn

# 导入原始中间件
sys.path.append('D:/Demo/backend')
from app.core.middleware import (
    RequestLoggingMiddleware,
    SecurityMiddleware,
    RateLimitMiddleware,
    PerformanceMonitoringMiddleware,
    APIVersionMiddleware
)

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

# 创建带测试中间件的FastAPI应用
def create_test_app(middleware_name: str, middleware_class=None):
    """创建测试应用"""
    app = FastAPI(
        title=f"中间件测试 - {middleware_name}",
        description=f"测试 {middleware_name} 是否导致阻塞",
        version="1.0.0"
    )

    # 只添加指定的中间件
    if middleware_class:
        app.add_middleware(middleware_class)
        print(f"[SETUP] 已添加中间件: {middleware_name}")

    # 创建AKShare客户端
    akshare_client = SimpleAKShareClient()

    @app.get("/")
    async def root():
        return {"message": f"中间件测试: {middleware_name}", "status": "ok"}

    @app.get("/health")
    async def health():
        return {"status": "healthy", "middleware": middleware_name}

    @app.get("/api/v1/market-data/symbols")
    async def get_symbols_test(sector: str = "energy"):
        """期货品种获取端点"""
        try:
            print(f"[INFO] [{middleware_name}] 接收到期货品种请求: sector={sector}")
            start_time = time.time()

            result = await akshare_client.get_available_symbols(sector)
            process_time = time.time() - start_time

            print(f"[INFO] [{middleware_name}] 期货品种请求处理完成，耗时: {process_time:.2f}秒")
            return JSONResponse(content=result)

        except Exception as e:
            print(f"[ERROR] [{middleware_name}] 期货品种请求处理失败: {str(e)}")
            raise HTTPException(status_code=500, detail=f"服务器内部错误: {str(e)}")

    return app

async def test_middleware(middleware_name: str, middleware_class=None, port: int = 8002):
    """测试单个中间件"""
    print(f"\n{'='*60}")
    print(f"测试中间件: {middleware_name}")
    print(f"端口: {port}")
    print(f"{'='*60}")

    # 创建测试应用
    app = create_test_app(middleware_name, middleware_class)

    # 在后台启动服务器
    config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="error")
    server = uvicorn.Server(config)

    # 启动服务器
    import threading
    server_task = threading.Thread(target=server.run, daemon=True)
    server_task.start()

    # 等待服务器启动
    await asyncio.sleep(2)

    # 测试API
    try:
        print(f"[TEST] 测试 {middleware_name} 的期货品种API...")
        start_time = time.time()

        import aiohttp
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as session:
            async with session.get(f"http://localhost:{port}/api/v1/market-data/symbols") as response:
                if response.status == 200:
                    data = await response.json()
                    elapsed = time.time() - start_time
                    print(f"[SUCCESS] {middleware_name}: 响应正常 ({elapsed:.2f}秒)")
                    print(f"  数据: {data.get('status', 'unknown')}")
                    return True, elapsed
                else:
                    elapsed = time.time() - start_time
                    print(f"[FAIL] {middleware_name}: HTTP {response.status} ({elapsed:.2f}秒)")
                    return False, elapsed

    except asyncio.TimeoutError:
        elapsed = time.time() - start_time
        print(f"[TIMEOUT] {middleware_name}: 请求超时 ({elapsed:.2f}秒)")
        return False, elapsed
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"[ERROR] {middleware_name}: {str(e)} ({elapsed:.2f}秒)")
        return False, elapsed

    finally:
        # 关闭服务器
        server.should_exit = True
        await asyncio.sleep(1)

async def main():
    """主测试函数"""
    print("=" * 80)
    print("中间件隔离测试 - 找出阻塞元凶")
    print("=" * 80)

    # 测试配置
    middleware_tests = [
        ("无中间件", None, 8002),
        ("APIVersionMiddleware", APIVersionMiddleware, 8003),
        ("PerformanceMonitoringMiddleware", PerformanceMonitoringMiddleware, 8004),
        ("RateLimitMiddleware", RateLimitMiddleware, 8005),
        ("SecurityMiddleware", SecurityMiddleware, 8006),
        ("RequestLoggingMiddleware", RequestLoggingMiddleware, 8007),
    ]

    results = []

    for name, middleware_class, port in middleware_tests:
        success, elapsed = await test_middleware(name, middleware_class, port)
        results.append({
            "middleware": name,
            "success": success,
            "elapsed": elapsed,
            "status": "PASS" if success else "FAIL"
        })

    # 汇总结果
    print(f"\n{'='*80}")
    print("测试结果汇总")
    print(f"{'='*80}")
    print(f"{'中间件':<25} {'状态':<8} {'响应时间':<10}")
    print("-" * 50)

    for result in results:
        status = result["status"]
        elapsed = f"{result['elapsed']:.2f}s"
        print(f"{result['middleware']:<25} {status:<8} {elapsed:<10}")

    # 找出问题中间件
    failed = [r for r in results if not r["success"]]
    if failed:
        print(f"\n[发现] 可疑中间件:")
        for f in failed:
            print(f"  - {f['middleware']}: {f['elapsed']:.2f}秒")
    else:
        print(f"\n[结论] 所有中间件测试通过")

if __name__ == "__main__":
    asyncio.run(main())