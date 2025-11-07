#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单的AKShare连接测试
"""

import sys
import os
import asyncio
import time
from datetime import datetime

# 修复Windows编码问题
if sys.platform == "win32":
    os.environ['PYTHONIOENCODING'] = 'utf-8'

try:
    import akshare as ak
    print("[OK] AKShare模块导入成功")
except ImportError as e:
    print(f"[FAIL] AKShare模块导入失败: {e}")
    sys.exit(1)

async def test_akshare_basic():
    """测试AKShare基本功能"""
    print("\n=== AKShare连接测试 ===")

    try:
        print("1. 测试基本连接...")
        # 测试一个简单的API调用
        start_time = time.time()

        # 使用一个更简单的API来测试连接
        print("   尝试获取股票基本信息...")
        df = ak.stock_zh_a_hist(symbol="000001", period="daily", start_date="20241101", end_date="20241106", adjust="")

        elapsed = time.time() - start_time
        print(f"   [OK] API调用成功，耗时: {elapsed:.2f}秒")
        print(f"   数据形状: {df.shape}")

        return True

    except Exception as e:
        print(f"   [FAIL] AKShare连接失败: {str(e)}")
        return False

async def test_futures_symbols():
    """测试期货品种获取"""
    print("\n=== 期货品种测试 ===")

    try:
        print("2. 测试期货品种获取...")
        start_time = time.time()

        # 测试原油期货数据获取
        print("   尝试获取原油期货信息...")
        df = ak.futures_main_sina(symbol="SC0")

        elapsed = time.time() - start_time
        print(f"   [OK] 期货数据获取成功，耗时: {elapsed:.2f}秒")
        print(f"   数据形状: {df.shape}")
        print(f"   数据列: {list(df.columns)}")

        return True

    except Exception as e:
        print(f"   [FAIL] 期货品种获取失败: {str(e)}")
        return False

async def main():
    """主测试函数"""
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 测试基本连接
    basic_success = await test_akshare_basic()

    # 测试期货品种（如果基本连接成功）
    if basic_success:
        futures_success = await test_futures_symbols()
    else:
        futures_success = False

    print(f"\n=== 测试结果 ===")
    print(f"AKShare基本连接: {'[OK] 成功' if basic_success else '[FAIL] 失败'}")
    print(f"期货品种获取: {'[OK] 成功' if futures_success else '[FAIL] 失败'}")

    if basic_success and futures_success:
        print("[SUCCESS] 所有测试通过！AKShare工作正常。")
        return 0
    else:
        print("[WARNING] 部分测试失败，可能存在网络连接或AKShare配置问题。")
        return 1

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n用户中断测试")
        sys.exit(1)
    except Exception as e:
        print(f"\n测试过程中发生错误: {e}")
        sys.exit(1)
