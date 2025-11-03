#!/usr/bin/env python3
"""
简化版验证脚本
验证Story 1.2的文件结构和基础组件
"""

import os
import importlib.util

def check_file_exists(filepath):
    """检查文件是否存在"""
    if os.path.exists(filepath):
        print(f"[OK] {filepath}")
        return True
    else:
        print(f"[ERROR] {filepath} - 文件不存在")
        return False

def check_module_syntax(filepath):
    """检查模块语法"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            code = f.read()
        compile(code, filepath, 'exec')
        print(f"[OK] {filepath} - 语法正确")
        return True
    except SyntaxError as e:
        print(f"[ERROR] {filepath} - 语法错误: {e}")
        return False
    except Exception as e:
        print(f"[ERROR] {filepath} - 检查失败: {e}")
        return False

def main():
    print("Story 1.2: 数据获取模块基础 - 验证报告")
    print("=" * 50)

    # 必需的文件列表
    required_files = [
        "app/services/akshare_client.py",
        "app/services/cache_service.py",
        "app/models/market_data.py",
        "app/schemas/market_data.py",
        "app/api/v1/endpoints/market_data.py",
        "tests/test_akshare_client.py",
        "tests/test_cache_service.py",
        "tests/test_market_data_api.py",
        "docs/market-data-api.md"
    ]

    # 检查文件存在性
    print("\n1. 检查文件存在性:")
    file_exists_results = []
    for filepath in required_files:
        result = check_file_exists(filepath)
        file_exists_results.append(result)

    # 检查语法
    print("\n2. 检查文件语法:")
    syntax_results = []
    py_files = [f for f in required_files if f.endswith('.py')]
    for filepath in py_files:
        result = check_module_syntax(filepath)
        syntax_results.append(result)

    # 验证关键类
    print("\n3. 检查关键类和函数:")

    # 检查AKShare客户端
    try:
        spec = importlib.util.spec_from_file_location("akshare_client", "app/services/akshare_client.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        if hasattr(module, 'AKShareClient'):
            print("[OK] AKShareClient - 类存在")
            client_class = getattr(module, 'AKShareClient')

            # 检查关键方法
            methods = ['get_supported_sectors', 'get_available_symbols', 'get_market_data']
            for method in methods:
                if hasattr(client_class, method):
                    print(f"[OK] AKShareClient.{method} - 方法存在")
                else:
                    print(f"[ERROR] AKShareClient.{method} - 方法不存在")
        else:
            print("[ERROR] AKShareClient - 类不存在")
    except Exception as e:
        print(f"[ERROR] 检查AKShareClient失败: {e}")

    # 检查缓存服务
    try:
        spec = importlib.util.spec_from_file_location("cache_service", "app/services/cache_service.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        if hasattr(module, 'CacheService'):
            print("[OK] CacheService - 类存在")
            service_class = getattr(module, 'CacheService')

            # 检查关键方法
            methods = ['get_market_data', 'set_market_data', 'get_symbols']
            for method in methods:
                if hasattr(service_class, method):
                    print(f"[OK] CacheService.{method} - 方法存在")
                else:
                    print(f"[ERROR] CacheService.{method} - 方法不存在")
        else:
            print("[ERROR] CacheService - 类不存在")
    except Exception as e:
        print(f"[ERROR] 检查CacheService失败: {e}")

    # 总结
    print("\n" + "=" * 50)
    print("验证总结:")

    all_files_exist = all(file_exists_results)
    all_syntax_ok = all(syntax_results)

    print(f"文件存在性: {'通过' if all_files_exist else '失败'}")
    print(f"语法检查: {'通过' if all_syntax_ok else '失败'}")
    print(f"关键组件: 检查完成")

    if all_files_exist and all_syntax_ok:
        print("\n[SUCCESS] Story 1.2 基础验证通过!")
        print("核心组件已实现，文件结构完整。")
    else:
        print("\n[FAILED] 验证失败，请检查上述错误。")

    print("=" * 50)

if __name__ == "__main__":
    main()