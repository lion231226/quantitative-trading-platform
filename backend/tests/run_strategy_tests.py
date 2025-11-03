"""
策略模块测试运行脚本
"""

import os
import sys
import subprocess
import time
from pathlib import Path


def run_test_file(test_file):
    """运行单个测试文件"""
    print(f"\n{'='*60}")
    print(f"运行测试: {test_file}")
    print(f"{'='*60}")

    start_time = time.time()

    try:
        # 使用pytest运行测试
        result = subprocess.run([
            sys.executable, "-m", "pytest",
            test_file,
            "-v",  # 详细输出
            "-s",  # 不捕获输出
            "--tb=short",  # 简短的错误回溯
            "--color=yes"  # 彩色输出
        ], capture_output=False, text=True)

        end_time = time.time()
        duration = end_time - start_time

        if result.returncode == 0:
            print(f"\n[PASS] {test_file} 测试通过 (耗时: {duration:.2f}秒)")
        else:
            print(f"\n[FAIL] {test_file} 测试失败 (耗时: {duration:.2f}秒)")

        return result.returncode == 0

    except Exception as e:
        print(f"\n[ERROR] 运行 {test_file} 时出错: {e}")
        return False


def main():
    """主函数"""
    # 获取策略测试目录
    current_dir = Path(__file__).parent
    strategy_test_dir = current_dir / "strategy"

    if not strategy_test_dir.exists():
        print(f"[ERROR] 策略测试目录不存在: {strategy_test_dir}")
        return 1

    # 定义测试文件列表
    test_files = [
        "test_moving_average.py",
        "test_signal_generator.py",
        "test_position_manager.py",
        "test_strategy_engine.py",
        "test_integration.py"
    ]

    # 检查测试文件是否存在
    existing_files = []
    for test_file in test_files:
        file_path = strategy_test_dir / test_file
        if file_path.exists():
            existing_files.append(str(file_path))
        else:
            print(f"[WARN] 测试文件不存在: {file_path}")

    if not existing_files:
        print("[ERROR] 没有找到任何测试文件")
        return 1

    print(f"[START] 开始运行策略模块测试")
    print(f"[INFO] 测试目录: {strategy_test_dir}")
    print(f"[INFO] 测试文件: {len(existing_files)} 个")

    # 运行所有测试
    passed_tests = 0
    total_tests = len(existing_files)

    for test_file in existing_files:
        if run_test_file(test_file):
            passed_tests += 1

    # 输出总结
    print(f"\n{'='*60}")
    print(f"[SUMMARY] 测试总结")
    print(f"{'='*60}")
    print(f"[PASS] 通过: {passed_tests}/{total_tests}")
    print(f"[FAIL] 失败: {total_tests - passed_tests}/{total_tests}")
    print(f"[RATE] 成功率: {(passed_tests/total_tests)*100:.1f}%")

    if passed_tests == total_tests:
        print("\n[SUCCESS] 所有测试都通过了！")
        return 0
    else:
        print(f"\n[WARNING] 有 {total_tests - passed_tests} 个测试失败")
        return 1


if __name__ == "__main__":
    # 设置环境变量
    os.environ["PYTHONPATH"] = str(Path(__file__).parent.parent)

    # 运行测试
    exit_code = main()
    sys.exit(exit_code)