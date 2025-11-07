#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化测试版本 - 无中间件的FastAPI应用
用于验证中间件阻塞假设
"""

import asyncio
import time
import sys
import os

# 修复Windows控制台编码问题
if sys.platform == "win32":
    os.environ['PYTHONIOENCODING'] = 'utf-8'

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import uvicorn

# 简化的AKShare客户端
class SimpleAKShareClient:
    async def get_available_symbols(self, sector: str = "energy"):
        """简化的期货品种获取"""
        try:
            print(f"[DEBUG] 开始获取期货品种数据: {sector}")
            start_time = time.time()

            # 直接导入akshare
            import akshare as ak

            if sector == "energy":
                print("[DEBUG] 获取能源期货品种...")
                df = ak.futures_main_sina(symbol="SC0")  # 原油期货
            else:
                print(f"[DEBUG] 获取默认期货品种...")
                df = ak.futures_main_sina(symbol="SC0")

            process_time = time.time() - start_time
            print(f"[DEBUG] AKShare数据获取完成，耗时: {process_time:.2f}秒")
            print(f"[DEBUG] 获取到 {len(df)} 行数据")

            if not df.empty:
                # 返回简化的数据
                symbols = df.index.tolist()[:10]  # 只返回前10个
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

# 创建FastAPI应用（无中间件）
app = FastAPI(
    title="简化测试API",
    description="用于测试中间件阻塞问题的简化版本",
    version="1.0.0"
)

# 创建AKShare客户端实例
akshare_client = SimpleAKShareClient()

@app.get("/")
async def root():
    """根路径"""
    return {"message": "简化测试API正在运行", "status": "ok"}

@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "healthy", "message": "简化版本运行正常"}

@app.get("/api/v1/market-data/symbols")
async def get_symbols_simple(sector: str = "energy"):
    """简化的期货品种获取端点（无中间件）"""
    try:
        print(f"[INFO] 接收到期货品种请求: sector={sector}")
        start_time = time.time()

        # 调用AKShare客户端
        result = await akshare_client.get_available_symbols(sector)

        process_time = time.time() - start_time
        print(f"[INFO] 期货品种请求处理完成，耗时: {process_time:.2f}秒")

        return JSONResponse(content=result)

    except Exception as e:
        print(f"[ERROR] 期货品种请求处理失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"服务器内部错误: {str(e)}")

@app.get("/test/akshare-direct")
async def test_akshare_direct():
    """直接测试AKShare功能"""
    try:
        print("[INFO] 直接测试AKShare功能")
        start_time = time.time()

        import akshare as ak
        df = ak.futures_main_sina(symbol="SC0")

        process_time = time.time() - start_time

        return {
            "status": "success",
            "message": f"AKShare直接测试成功",
            "data": {
                "rows": len(df),
                "columns": len(df.columns) if not df.empty else 0,
                "process_time": process_time,
                "sample_data": df.head(2).to_dict() if not df.empty else None
            }
        }

    except Exception as e:
        print(f"[ERROR] AKShare直接测试失败: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "message": "AKShare直接测试失败"
        }

if __name__ == "__main__":
    print("=" * 60)
    print("简化测试服务器启动")
    print("用途: 验证中间件阻塞假设")
    print("特点: 无中间件，直接处理请求")
    print("=" * 60)

    # 使用不同端口避免冲突
    port = 8001
    print(f"服务器启动在 http://localhost:{port}")
    print("测试端点:")
    print(f"  - 健康检查: http://localhost:{port}/health")
    print(f"  - 期货品种: http://localhost:{port}/api/v1/market-data/symbols")
    print(f"  - AKShare测试: http://localhost:{port}/test/akshare-direct")
    print("=" * 60)

    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")