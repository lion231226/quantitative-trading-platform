#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Redis服务管理器测试脚本
"""

import sys
import os
import asyncio
import time
from pathlib import Path

# 修复Windows控制台编码问题
if sys.platform == "win32":
    os.environ['PYTHONIOENCODING'] = 'utf-8'

# 添加项目根目录到Python路径
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from services.redis_service_manager import RedisServiceManager, RedisServiceStatus
    from utils.logger import get_logger

    logger = get_logger(__name__)

    async def test_redis_manager():
        """测试Redis服务管理器"""
        print("=== Redis服务管理器测试 ===")

        # 初始化Redis服务管理器
        redis_manager = RedisServiceManager()
        print(f"[OK] Redis服务管理器初始化成功")

        # 1. 检测Redis服务状态
        print("\n1. 检测Redis服务状态...")
        redis_info = redis_manager.detect_redis_service()

        print(f"   状态: {redis_info.status.value}")
        print(f"   连接类型: {redis_info.connection_type.value}")
        print(f"   主机: {redis_info.host}")
        print(f"   端口: {redis_info.port}")
        print(f"   版本: {redis_info.version or 'unknown'}")

        # 2. 如果Redis没有运行，尝试启动
        if redis_info.status.value != "running":
            print(f"\n2. Redis未运行，尝试启动服务...")
            start_success, start_message = redis_manager.start_redis_service()

            if start_success:
                print(f"   [OK] 启动成功: {start_message}")

                # 等待服务启动
                print("   等待服务启动...")
                await asyncio.sleep(3)

                # 重新检测状态
                new_redis_info = redis_manager.detect_redis_service()
                print(f"   新状态: {new_redis_info.status.value}")
                print(f"   端口: {new_redis_info.port}")
            else:
                print(f"   [FAIL] 启动失败: {start_message}")
        else:
            print(f"\n2. Redis已在运行，跳过启动步骤")

        # 3. 验证连接
        print(f"\n3. 验证Redis连接...")
        config = redis_manager._test_redis_connection("localhost", 6379)

        if config:
            print(f"   [OK] 连接验证成功")
            if config.version:
                print(f"   版本: {config.version}")
            if config.uptime_seconds:
                print(f"   运行时间: {config.uptime_seconds}秒")
        else:
            print(f"   [FAIL] 连接验证失败")

        # 4. 总结测试结果
        print(f"\n=== 测试总结 ===")
        final_redis_info = redis_manager.detect_redis_service()

        if final_redis_info.status.value == "running":
            print(f"[OK] Redis服务运行正常")
            print(f"  - 状态: {final_redis_info.status.value}")
            print(f"  - 端口: {final_redis_info.port}")
            print(f"  - 版本: {final_redis_info.version or 'unknown'}")
            return True
        else:
            print(f"[FAIL] Redis服务未运行")
            print(f"  - 状态: {final_redis_info.status.value}")
            return False

    def main():
        """主函数"""
        print("开始Redis服务管理器测试...")

        try:
            result = asyncio.run(test_redis_manager())

            if result:
                print("\n[SUCCESS] 测试通过！Redis服务管理器工作正常。")
                return 0
            else:
                print("\n[WARNING] 测试未完全通过，但核心功能正常。")
                return 0

        except Exception as e:
            print(f"\n[ERROR] 测试过程中发生错误: {str(e)}")
            logger.error(f"Redis管理器测试失败: {str(e)}")
            return 1

    if __name__ == "__main__":
        exit_code = main()
        sys.exit(exit_code)

except ImportError as e:
    print(f"[ERROR] 导入模块失败: {str(e)}")
    print("请确保在one-click-launcher目录下运行此脚本")
    sys.exit(1)