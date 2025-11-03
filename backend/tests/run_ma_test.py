"""
独立的移动平均线测试
避开循环导入问题
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_moving_average():
    """测试移动平均线功能"""
    print("开始测试移动平均线功能...")

    try:
        # 测试导入
        print("1. 测试导入...")
        from app.strategy.indicators import SMA, EMA, MovingAverageCalculator, MAType
        print("   [OK] 导入成功")

        # 测试SMA
        print("2. 测试SMA...")
        sma = SMA(3)  # 使用较短的周期

        # 测试数据不足的情况
        result1 = sma.calculate_single(10.0)
        result2 = sma.calculate_single(11.0)
        assert result1 is None, "数据不足时应该返回None"
        assert result2 is None, "数据不足时应该返回None"
        print("   [OK] 数据不足情况正常")

        # 测试数据充足的情况
        result3 = sma.calculate_single(12.0)
        expected_sma = (10.0 + 11.0 + 12.0) / 3
        assert result3 is not None, "有足够数据时应该返回有效值"
        assert abs(result3 - expected_sma) < 1e-10, f"SMA计算错误: 期望{expected_sma}, 实际{result3}"
        print("   [OK] SMA计算正确")

        # 测试批量计算
        sma5 = SMA(5)  # 使用5周期进行批量计算测试
        prices = [10, 11, 12, 13, 14, 15, 16, 17, 18, 19]
        timestamps = list(range(len(prices)))

        batch_result = sma5.calculate_batch(prices, timestamps)

        assert len(batch_result.values) == len(prices) - 5 + 1, "批量计算结果数量错误"
        assert batch_result.ma_type == MAType.SMA, "MA类型错误"
        assert batch_result.period == 5, "MA周期错误"
        print("   [OK] 批量计算正确")

        # 测试EMA
        print("3. 测试EMA...")
        ema = EMA(5)

        # 第一个值应该等于价格
        ema_result1 = ema.calculate_single(10.0)
        assert ema_result1 == 10.0, "EMA第一个值应该等于价格"
        print("   [OK] EMA初始值正确")

        # 测试计算器
        print("4. 测试移动平均线计算器...")
        calculator = MovingAverageCalculator()

        # 创建SMA指标
        sma_indicator = calculator.create_indicator(MAType.SMA, 10, "test_sma")
        assert isinstance(sma_indicator, SMA), "创建的指标类型错误"
        assert sma_indicator.period == 10, "指标周期错误"
        print("   [OK] 指标创建正确")

        # 测试获取和移除指标
        retrieved = calculator.get_indicator("test_sma")
        assert retrieved is sma_indicator, "获取指标失败"

        removed = calculator.remove_indicator("test_sma")
        assert removed is True, "移除指标失败"

        not_found = calculator.get_indicator("test_sma")
        assert not_found is None, "移除后仍能找到指标"
        print("   [OK] 指标管理正确")

        print("\n[SUCCESS] 所有移动平均线测试通过！")
        return True

    except Exception as e:
        print(f"\n[FAIL] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_signal_generator():
    """测试信号生成器"""
    print("开始测试信号生成器...")

    try:
        from app.strategy.signals import SignalGenerator, SignalConfig, SignalType, SignalStrength, TradingSignal
        from app.strategy.indicators import MAType

        # 创建配置
        config = SignalConfig(
            ma_type=MAType.SMA,
            ma_period=5,
            min_cross_percentage=0.01,
            confirmation_periods=1
        )

        # 创建信号生成器
        generator = SignalGenerator(config)
        print("   [OK] 信号生成器创建成功")

        # 测试信号生成（金叉场景）
        prices = [8, 9, 10, 11, 12, 13, 14, 15]  # 上升趋势
        timestamps = list(range(len(prices)))

        signals = generator.generate_signals_from_data(prices, timestamps)

        # 验证信号
        buy_signals = [s for s in signals if s.signal_type == SignalType.BUY]
        print(f"   [OK] 生成了 {len(buy_signals)} 个买入信号")

        if buy_signals:
            signal = buy_signals[0]
            assert isinstance(signal, TradingSignal), "信号类型错误"
            assert signal.signal_type == SignalType.BUY, "信号类型错误"
            assert signal.price > 0, "信号价格错误"
            assert signal.ma_value > 0, "MA值错误"
            assert signal.strength in SignalStrength, "信号强度错误"
            assert 0 <= signal.confidence <= 1, "信号置信度错误"
            print("   [OK] 信号属性正确")

        print("\n[SUCCESS] 信号生成器测试通过！")
        return True

    except Exception as e:
        print(f"\n[FAIL] 信号生成器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    print("=" * 60)
    print("策略模块核心功能测试")
    print("=" * 60)

    # 运行测试
    tests = [
        ("移动平均线", test_moving_average),
        ("信号生成器", test_signal_generator)
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        print(f"\n{'-' * 40}")
        print(f"测试: {test_name}")
        print(f"{'-' * 40}")

        if test_func():
            passed += 1
        else:
            print(f"测试 {test_name} 失败")

    # 输出总结
    print(f"\n{'=' * 60}")
    print(f"测试总结")
    print(f"{'=' * 60}")
    print(f"通过: {passed}/{total}")
    print(f"失败: {total - passed}/{total}")
    print(f"成功率: {(passed/total)*100:.1f}%")

    if passed == total:
        print("\n[SUCCESS] 所有核心功能测试都通过了！")
        return 0
    else:
        print(f"\n[WARNING] 有 {total - passed} 个测试失败")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)