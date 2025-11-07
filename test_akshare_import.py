#!/usr/bin/env python3
"""
AKShare导入测试脚本
用于复现和验证Python 3.13.4兼容性问题
"""
import sys
import time

print(f"Python版本: {sys.version}")
print(f"当前工作目录: {sys.executable}")

# 测试1: 基础AKShare导入
print("\n=== 测试1: 直接AKShare导入 ===")
print("正在尝试导入AKShare...")
start_time = time.time()

try:
    import akshare as ak
    end_time = time.time()
    print(f"[SUCCESS] AKShare导入成功！")
    print(f"导入耗时: {end_time - start_time:.2f}秒")
    print(f"AKShare版本: {ak.__version__ if hasattr(ak, '__version__') else '未知'}")
except Exception as e:
    end_time = time.time()
    print(f"[FAILED] AKShare导入失败！")
    print(f"失败耗时: {end_time - start_time:.2f}秒")
    print(f"错误信息: {type(e).__name__}: {e}")

# 测试2: 逐步导入诊断
print("\n=== 测试2: 逐步导入诊断 ===")
print("步骤1: 导入基础依赖...")

try:
    import pandas as pd
    print("✅ pandas 导入成功")
except Exception as e:
    print(f"❌ pandas 导入失败: {e}")

try:
    import requests
    print("✅ requests 导入成功")
except Exception as e:
    print(f"❌ requests 导入失败: {e}")

try:
    import aiohttp
    print("✅ aiohttp 导入成功")
except Exception as e:
    print(f"❌ aiohttp 导入失败: {e}")

print("📋 步骤2: 等待2秒...")
time.sleep(2)

print("📋 步骤3: 再次尝试AKShare导入...")
start_time = time.time()

try:
    import akshare as ak
    end_time = time.time()
    print(f"✅ 第二次导入成功，耗时: {end_time - start_time:.2f}秒")
except KeyboardInterrupt:
    print("🛑 用户中断 - 可能表明进程阻塞")
except Exception as e:
    end_time = time.time()
    print(f"❌ 第二次导入失败，耗时: {end_time - start_time:.2f}秒")
    print(f"🚨 错误详情: {type(e).__name__}: {e}")

print("\n=== 测试完成 ===")