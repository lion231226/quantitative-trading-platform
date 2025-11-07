#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
中间件组合测试 - 找出导致死锁的中间件组合
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
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
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

# 创建带中间件组合的FastAPI应用
def create_combination_test_app(middleware_list: list, combination_name: str, port: int):
    """创建中间件组合测试应用"""
    app = FastAPI(
        title=f"中间件组合测试 - {combination_name}",
        description=f"测试中间件组合: {combination_name}",
        version="1.0.0"
    )

    # 添加原始版本的CORS和TrustedHost中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # 简化配置
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*"]  # 简化配置
    )

    # 按照原版本顺序添加自定义中间件
    for middleware_class in middleware_list:
        app.add_middleware(middleware_class)

    print(f"[SETUP] {combination_name} - 已添加中间件: {[cls.__name__ for cls in middleware_list]}")

    # 创建AKShare客户端
    akshare_client = SimpleAKShareClient()

    @app.get("/")
    async def root():
        return {"message": f"中间件组合测试: {combination_name}", "status": "ok"}

    @app.get("/health")
    async def health():
        return {"status": "healthy", "combination": combination_name}

    @app.get("/api/v1/market-data/symbols")
    async def get_symbols_test(sector: str = "energy"):
        """期货品种获取端点"""
        try:
            print(f"[INFO] [{combination_name}] 接收到期货品种请求: sector={sector}")
            start_time = time.time()

            result = await akshare_client.get_available_symbols(sector)
            process_time = time.time() - start_time

            print(f"[INFO] [{combination_name}] 期货品种请求处理完成，耗时: {process_time:.2f}秒")
            return JSONResponse(content=result)

        except Exception as e:
            print(f"[ERROR] [{combination_name}] 期货品种请求处理失败: {str(e)}")
            raise HTTPException(status_code=500, detail=f"服务器内部错误: {str(e)}")

    return app

async def test_combination(middleware_list: list, combination_name: str, port: int):
    """测试中间件组合"""
    print(f"\n{'='*60}")
    print(f"测试中间件组合: {combination_name}")
    print(f"端口: {port}")
    print(f"中间件: {[cls.__name__ for cls in middleware_list]}")
    print(f"{'='*60}")

    # 创建测试应用
    app = create_combination_test_app(middleware_list, combination_name, port)

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
        print(f"[TEST] 测试 {combination_name} 的期货品种API...")
        start_time = time.time()

        import aiohttp
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as session:
            async with session.get(f"http://localhost:{port}/api/v1/market-data/symbols") as response:
                if response.status == 200:
                    data = await response.json()
                    elapsed = time.time() - start_time
                    print(f"[SUCCESS] {combination_name}: 响应正常 ({elapsed:.2f}秒)")
                    print(f"  数据: {data.get('status', 'unknown')}")
                    return True, elapsed
                else:
                    elapsed = time.time() - start_time
                    print(f"[FAIL] {combination_name}: HTTP {response.status} ({elapsed:.2f}秒)")
                    return False, elapsed

    except asyncio.TimeoutError:
        elapsed = time.time() - start_time
        print(f"[TIMEOUT] {combination_name}: 请求超时 ({elapsed:.2f}秒)")
        return False, elapsed
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"[ERROR] {combination_name}: {str(e)} ({elapsed:.2f}秒)")
        return False, elapsed

    finally:
        # 关闭服务器
        server.should_exit = True
        await asyncio.sleep(1)

async def main():
    """主测试函数"""
    print("=" * 80)
    print("中间件组合测试 - 找出死锁组合")
    print("=" * 80)

    # 按照原版本main.py的顺序测试中间件组合
    middleware_classes = [
        APIVersionMiddleware,
        PerformanceMonitoringMiddleware,
        RateLimitMiddleware,
        SecurityMiddleware,
        RequestLoggingMiddleware
    ]

    # 渐进式测试组合
    combination_tests = [
        # 原版本完整组合
        ("完整中间件组合", middleware_classes, 8010),

        # 逐步减少中间件
        ("前4个中间件", middleware_classes[:4], 8011),
        ("前3个中间件", middleware_classes[:3], 8012),
        ("前2个中间件", middleware_classes[:2], 8013),
        ("只有第1个", [middleware_classes[0]], 8014),

        # 跳过可疑中间件的组合
        ("跳过PerformanceMonitor", [m for i, m in enumerate(middleware_classes) if i != 1], 8015),
        ("跳过RateLimit", [m for i, m in enumerate(middleware_classes) if i != 2], 8016),
        ("跳过Security", [m for i, m in enumerate(middleware_classes) if i != 3], 8017),
        ("跳过RequestLogging", [m for i, m in enumerate(middleware_classes) if i != 4], 8018),

        # 可能的问题组合
        ("PerformanceMonitor+RateLimit", middleware_classes[1:3], 8019),
        ("RateLimit+Security", middleware_classes[2:4], 8020),
        ("Security+RequestLogging", middleware_classes[3:5], 8021),
    ]

    results = []

    for name, middleware_list, port in combination_tests:
        success, elapsed = await test_combination(middleware_list, name, port)
        results.append({
            "combination": name,
            "middleware_count": len(middleware_list),
            "success": success,
            "elapsed": elapsed,
            "status": "PASS" if success else "FAIL"
        })

    # 汇总结果
    print(f"\n{'='*80}")
    print("测试结果汇总")
    print(f"{'='*80}")
    print(f"{'组合名称':<25} {'中间件数':<8} {'状态':<8} {'响应时间':<10}")
    print("-" * 60)

    for result in results:
        status = result["status"]
        elapsed = f"{result['elapsed']:.2f}s"
        print(f"{result['combination']:<25} {result['middleware_count']:<8} {status:<8} {elapsed:<10}")

    # 找出问题组合
    failed = [r for r in results if not r["success"]]
    if failed:
        print(f"\n[发现] 问题中间件组合:")
        for f in failed:
            print(f"  - {f['combination']}: {f['elapsed']:.2f}秒")

        # 分析模式
        print(f"\n[分析] 失败组合的共同特征:")
        failed_counts = [r['middleware_count'] for r in failed]
        if len(set(failed_counts)) == 1:
            print(f"  - 所有失败组合都包含 {failed_counts[0]} 个中间件")

        print(f"  - 需要进一步检查中间件之间的交互")
    else:
        print(f"\n[结论] 所有中间件组合测试通过")

if __name__ == "__main__":
    asyncio.run(main())