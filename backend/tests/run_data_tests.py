#!/usr/bin/env python3
"""
数据处理和存储模块测试运行脚本

运行所有与数据处理相关的测试，包括：
- 数据处理器测试
- 数据存储服务测试
- 数据API端点测试
- 数据库管理器测试
"""

import sys
import os
import asyncio
import subprocess
from pathlib import Path
from datetime import datetime

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def run_test_module(test_module: str, verbose: bool = True) -> bool:
    """运行单个测试模块"""
    try:
        cmd = [sys.executable, "-m", "pytest", test_module]
        if verbose:
            cmd.append("-v")

        print(f"\n{'='*60}")
        print(f"运行测试模块: {test_module}")
        print(f"{'='*60}")

        result = subprocess.run(cmd, cwd=project_root, capture_output=False)

        if result.returncode == 0:
            print(f"✅ {test_module} 测试通过")
            return True
        else:
            print(f"❌ {test_module} 测试失败")
            return False

    except Exception as e:
        print(f"❌ 运行 {test_module} 时发生错误: {e}")
        return False

def run_specific_tests(test_pattern: str = None) -> bool:
    """运行特定模式的测试"""
    if test_pattern:
        try:
            cmd = [sys.executable, "-m", "pytest", test_pattern, "-v"]
            print(f"\n{'='*60}")
            print(f"运行测试模式: {test_pattern}")
            print(f"{'='*60}")

            result = subprocess.run(cmd, cwd=project_root, capture_output=False)
            return result.returncode == 0
        except Exception as e:
            print(f"❌ 运行测试模式 {test_pattern} 时发生错误: {e}")
            return False
    return True

def check_test_dependencies() -> bool:
    """检查测试依赖"""
    required_modules = [
        'pytest',
        'pytest-asyncio',
        'pytest-cov',
        'fastapi',
        'sqlalchemy',
        'pandas',
        'numpy'
    ]

    missing_modules = []
    for module in required_modules:
        try:
            __import__(module)
        except ImportError:
            missing_modules.append(module)

    if missing_modules:
        print("❌ 缺少以下测试依赖:")
        for module in missing_modules:
            print(f"   - {module}")
        print("\n请运行以下命令安装依赖:")
        print(f"pip install {' '.join(missing_modules)}")
        return False

    print("✅ 所有测试依赖已满足")
    return True

def setup_test_environment():
    """设置测试环境"""
    print("🔧 设置测试环境...")

    # 设置测试环境变量
    os.environ['TESTING'] = 'true'
    os.environ['DATABASE_URL'] = 'sqlite:///./test_quant_trading.db'
    os.environ['REDIS_URL'] = 'redis://localhost:6379/1'  # 使用不同的数据库

    # 创建必要的目录
    test_dirs = [
        project_root / "test_data",
        project_root / "test_logs"
    ]

    for directory in test_dirs:
        directory.mkdir(exist_ok=True)

    print("✅ 测试环境设置完成")

def cleanup_test_environment():
    """清理测试环境"""
    print("🧹 清理测试环境...")

    # 清理测试数据库文件
    test_db_files = [
        project_root / "test_quant_trading.db",
        project_root / "test_quant_trading.db-journal"
    ]

    for db_file in test_db_files:
        if db_file.exists():
            db_file.unlink()
            print(f"   删除测试数据库: {db_file.name}")

    print("✅ 测试环境清理完成")

def generate_test_report(results: dict):
    """生成测试报告"""
    print("\n" + "="*60)
    print("📊 测试报告")
    print("="*60)

    total_tests = len(results)
    passed_tests = sum(1 for result in results.values() if result)
    failed_tests = total_tests - passed_tests

    print(f"总测试模块: {total_tests}")
    print(f"通过: {passed_tests}")
    print(f"失败: {failed_tests}")
    print(f"成功率: {passed_tests/total_tests*100:.1f}%")

    print("\n详细结果:")
    for module, result in results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {module}: {status}")

    # 生成报告文件
    report_content = f"""
# 数据处理和存储模块测试报告

生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 测试统计
- 总测试模块: {total_tests}
- 通过: {passed_tests}
- 失败: {failed_tests}
- 成功率: {passed_tests/total_tests*100:.1f}%

## 测试详情
"""

    for module, result in results.items():
        status = "通过" if result else "失败"
        report_content += f"- {module}: {status}\n"

    report_file = project_root / "test_report.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report_content)

    print(f"\n📄 详细报告已保存到: {report_file}")

def main():
    """主函数"""
    print("🚀 开始运行数据处理和存储模块测试")

    # 检查依赖
    if not check_test_dependencies():
        sys.exit(1)

    # 设置测试环境
    setup_test_environment()

    try:
        # 定义要运行的测试模块
        test_modules = [
            "tests/test_data_storage.py",
            "tests/test_data_api.py"
        ]

        # 运行所有测试
        results = {}
        overall_success = True

        for module in test_modules:
            success = run_test_module(module)
            results[module] = success
            if not success:
                overall_success = False

        # 如果指定了特定测试模式
        if len(sys.argv) > 1:
            test_pattern = sys.argv[1]
            pattern_success = run_specific_tests(test_pattern)
            results[f"pattern:{test_pattern}"] = pattern_success
            if not pattern_success:
                overall_success = False

        # 生成测试报告
        generate_test_report(results)

        # 返回总体结果
        if overall_success:
            print("\n🎉 所有测试通过!")
            sys.exit(0)
        else:
            print("\n💥 部分测试失败!")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n⚠️ 测试被用户中断")
        sys.exit(1)

    except Exception as e:
        print(f"\n💥 测试运行过程中发生错误: {e}")
        sys.exit(1)

    finally:
        # 清理测试环境
        cleanup_test_environment()

if __name__ == "__main__":
    main()