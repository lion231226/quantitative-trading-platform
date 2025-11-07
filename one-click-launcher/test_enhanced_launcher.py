#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强启动器测试脚本

验证修复后的服务启动序列、依赖管理和错误诊断功能。
"""

import asyncio
import sys
import time
import os
from pathlib import Path

# 添加项目根目录到Python路径
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from launcher import RealLauncher, LauncherMode
from core.enhanced_service_orchestrator import create_enhanced_service_configs
from core.error_diagnostic_system import diagnostic_system
from utils.logger import get_logger

logger = get_logger(__name__)

class LauncherTester:
    """启动器测试器"""

    def __init__(self):
        """初始化测试器"""
        self.test_results = []
        self.start_time = time.time()

    async def run_all_tests(self):
        """运行所有测试"""
        print("=" * 60)
        print("增强一键启动器测试")
        print("=" * 60)
        print(f"开始时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print()

        tests = [
            ("服务配置验证", self.test_service_configs),
            ("增强编排器功能", self.test_enhanced_orchestrator),
            ("错误诊断系统", self.test_error_diagnostic),
            ("启动器集成测试", self.test_launcher_integration),
            ("依赖管理验证", self.test_dependency_management)
        ]

        for test_name, test_func in tests:
            print(f"🧪 运行测试: {test_name}")
            try:
                result = await test_func()
                self.test_results.append({
                    "name": test_name,
                    "success": result,
                    "message": "通过" if result else "失败"
                })
                status = "✅ 通过" if result else "❌ 失败"
                print(f"   状态: {status}")
            except Exception as e:
                self.test_results.append({
                    "name": test_name,
                    "success": False,
                    "message": f"异常: {str(e)}"
                })
                print(f"   状态: ❌ 异常 - {str(e)}")
            print()

        self.print_test_summary()

    async def test_service_configs(self) -> bool:
        """测试服务配置"""
        try:
            configs = create_enhanced_service_configs()

            # 验证基本配置
            required_services = ["redis", "backend", "frontend"]
            for service in required_services:
                if service not in configs:
                    print(f"   缺少服务配置: {service}")
                    return False

            # 验证依赖关系
            if "backend" not in configs["redis"].dependencies:
                if "redis" not in configs["backend"].dependencies:
                    print("   Backend应该依赖Redis")
                    return False

            if "frontend" not in configs["backend"].dependencies:
                if "backend" not in configs["frontend"].dependencies:
                    print("   Frontend应该依赖Backend")
                    return False

            print("   ✓ 服务配置正确")
            print(f"   ✓ 配置了 {len(configs)} 个服务")
            return True

        except Exception as e:
            print(f"   ✗ 配置验证失败: {str(e)}")
            return False

    async def test_enhanced_orchestrator(self) -> bool:
        """测试增强编排器"""
        try:
            from core.enhanced_service_orchestrator import EnhancedServiceOrchestrator

            orchestrator = EnhancedServiceOrchestrator()

            # 测试启动顺序计算
            configs = create_enhanced_service_configs()
            startup_order = orchestrator._calculate_startup_order(configs)

            expected_order = ["redis", "backend", "frontend"]
            if startup_order != expected_order:
                print(f"   启动顺序不正确: {startup_order} vs {expected_order}")
                return False

            print("   ✓ 启动顺序计算正确")
            print(f"   ✓ 计算结果: {' → '.join(startup_order)}")

            # 测试端口连接检查
            redis_port_open = await orchestrator._check_port_connection("localhost", 6379)
            backend_port_open = await orchestrator._check_port_connection("localhost", 8000)
            frontend_port_open = await orchestrator._check_port_connection("localhost", 3000)

            print(f"   ✓ 端口状态检查 - Redis: {'开放' if redis_port_open else '关闭'}")
            print(f"   ✓ 端口状态检查 - Backend: {'开放' if backend_port_open else '关闭'}")
            print(f"   ✓ 端口状态检查 - Frontend: {'开放' if frontend_port_open else '关闭'}")

            return True

        except Exception as e:
            print(f"   ✗ 编排器测试失败: {str(e)}")
            return False

    async def test_error_diagnostic(self) -> bool:
        """测试错误诊断系统"""
        try:
            # 测试错误分类
            test_cases = [
                ("Address already in use", "port_conflict"),
                ("ModuleNotFoundError: No module named 'redis'", "dependency_missing"),
                ("Connection refused", "network"),
                ("Timeout occurred", "timeout")
            ]

            for error_msg, expected_category in test_cases:
                category = diagnostic_system._classify_error(error_msg)
                if category.value != expected_category:
                    print(f"   错误分类不准确: '{error_msg}' -> {category.value} (期望: {expected_category})")
                    return False

            print("   ✓ 错误分类功能正常")
            print(f"   ✓ 测试了 {len(test_cases)} 种错误类型")

            # 测试严重程度判断
            critical_services = ["redis", "backend", "frontend"]
            for service in critical_services:
                severity = diagnostic_system._determine_severity(
                    diagnostic_system._classify_error("port conflict"),
                    service
                )
                if severity.value not in ["high", "critical"]:
                    print(f"   关键服务严重程度判断错误: {service} -> {severity.value}")
                    return False

            print("   ✓ 严重程度判断正确")
            return True

        except Exception as e:
            print(f"   ✗ 错误诊断测试失败: {str(e)}")
            return False

    async def test_launcher_integration(self) -> bool:
        """测试启动器集成"""
        try:
            # 创建启动器实例
            launcher = RealLauncher(mode=LauncherMode.DEBUG)

            # 验证增强编排器是否正确集成
            if not hasattr(launcher, 'service_orchestrator'):
                print("   启动器缺少增强编排器")
                return False

            if not hasattr(launcher, '_start_real_services_fallback'):
                print("   启动器缺少回退启动方法")
                return False

            print("   ✓ 增强编排器已集成")
            print("   ✓ 回退启动方法已添加")

            # 测试环境准备
            env_ready = await launcher._prepare_environment()
            print(f"   ✓ 环境准备: {'成功' if env_ready else '失败但继续'}")

            return True

        except Exception as e:
            print(f"   ✗ 集成测试失败: {str(e)}")
            return False

    async def test_dependency_management(self) -> bool:
        """测试依赖管理"""
        try:
            configs = create_enhanced_service_configs()

            # 验证Redis依赖配置
            redis_config = configs["redis"]
            if not redis_config.required:
                print("   Redis应该标记为必需依赖")
                return False

            # 验证Backend依赖
            backend_config = configs["backend"]
            if "redis" not in backend_config.dependencies:
                print("   Backend应该依赖Redis")
                return False

            # 验证Frontend依赖
            frontend_config = configs["frontend"]
            if "backend" not in frontend_config.dependencies:
                print("   Frontend应该依赖Backend")
                return False

            print("   ✓ Redis依赖配置正确")
            print("   ✓ Backend依赖配置正确")
            print("   ✓ Frontend依赖配置正确")

            # 测试配置文件读取
            from utils.config_manager import ConfigManager
            config_manager = ConfigManager()
            redis_required = config_manager.get("dependencies", "redis_required", True)

            if not redis_required:
                print("   配置文件中Redis应该设置为必需")
                return False

            print("   ✓ 配置文件读取正确")
            return True

        except Exception as e:
            print(f"   ✗ 依赖管理测试失败: {str(e)}")
            return False

    def print_test_summary(self):
        """打印测试摘要"""
        total_time = time.time() - self.start_time
        passed = sum(1 for result in self.test_results if result["success"])
        total = len(self.test_results)

        print("=" * 60)
        print("测试摘要")
        print("=" * 60)
        print(f"总测试数: {total}")
        print(f"通过: {passed}")
        print(f"失败: {total - passed}")
        print(f"成功率: {passed/total*100:.1f}%")
        print(f"总耗时: {total_time:.2f}秒")
        print()

        for result in self.test_results:
            status = "✅" if result["success"] else "❌"
            print(f"{status} {result['name']}: {result['message']}")

        print()

        if passed == total:
            print("🎉 所有测试通过！增强启动器修复成功。")
        else:
            print("⚠️  部分测试失败，需要进一步修复。")

        print("=" * 60)

async def main():
    """主函数"""
    tester = LauncherTester()
    await tester.run_all_tests()

if __name__ == "__main__":
    # 设置事件循环策略（Windows兼容性）
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    # 运行测试
    asyncio.run(main())