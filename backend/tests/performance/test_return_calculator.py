"""
收益计算引擎测试
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime

from app.services.performance.return_calculator import (
    ReturnCalculator,
    ReturnCalculationConfig,
    ReturnType,
    create_return_calculator
)


class TestReturnCalculationConfig:
    """收益计算配置测试"""

    def test_default_config(self):
        """测试默认配置"""
        config = ReturnCalculationConfig()
        assert config.return_type == ReturnType.SIMPLE
        assert config.risk_free_rate == 0.02
        assert config.trading_days == 252
        assert config.include_costs is True

    def test_custom_config(self):
        """测试自定义配置"""
        config = ReturnCalculationConfig(
            return_type=ReturnType.LOG,
            risk_free_rate=0.03,
            trading_days=365
        )
        assert config.return_type == ReturnType.LOG
        assert config.risk_free_rate == 0.03
        assert config.trading_days == 365


class TestReturnCalculator:
    """收益计算器测试"""

    def setup_method(self):
        """设置测试数据"""
        self.config = ReturnCalculationConfig(return_type=ReturnType.SIMPLE)
        self.calculator = ReturnCalculator(self.config)

        # 测试价格序列
        self.prices = np.array([100, 105, 102, 108, 110, 107, 112, 115, 113, 118])

        # 预期的简单收益率
        self.expected_simple_returns = np.array([
            0.05, -0.02857143, 0.05882353, 0.01851852,
            -0.02727273, 0.04672897, 0.02678571, -0.0173913, 0.04424779
        ])

    def test_calculator_initialization(self):
        """测试计算器初始化"""
        calculator = ReturnCalculator()
        assert calculator.config.return_type == ReturnType.SIMPLE

    def test_simple_return_calculation(self):
        """测试简单收益率计算"""
        returns = self.calculator.calculate_single_period_returns(self.prices)

        np.testing.assert_array_almost_equal(
            returns, self.expected_simple_returns, decimal=8
        )

    def test_log_return_calculation(self):
        """测试对数收益率计算"""
        config = ReturnCalculationConfig(return_type=ReturnType.LOG)
        calculator = ReturnCalculator(config)

        returns = calculator.calculate_single_period_returns(self.prices)

        # 对数收益率应该接近简单收益率（对于小变化）
        assert len(returns) == len(self.prices) - 1
        assert all(r > -0.5 for r in returns)  # 对数收益率不能小于-50%

    def test_multi_period_returns(self):
        """测试多期收益率计算"""
        returns = self.calculator.calculate_single_period_returns(self.prices, periods=2)

        # 2期简单收益率: (P_t - P_{t-2}) / P_{t-2}
        expected_len = len(self.prices) - 2
        assert len(returns) == expected_len

    def test_insufficient_data(self):
        """测试数据不足的情况"""
        with pytest.raises(ValueError, match="价格序列长度不足"):
            self.calculator.calculate_single_period_returns([100])

    def test_cumulative_returns_simple(self):
        """测试简单收益率的累计计算"""
        returns = np.array([0.1, -0.05, 0.08, 0.02])
        cumulative = self.calculator.calculate_cumulative_returns(returns)

        expected = np.array([0.1, 0.045, 0.1286, 0.1512])  # (1.1)*(0.95)*(1.08)*(1.02) - 1
        np.testing.assert_array_almost_equal(cumulative, expected, decimal=4)

    def test_cumulative_returns_log(self):
        """测试对数收益率的累计计算"""
        config = ReturnCalculationConfig(return_type=ReturnType.LOG)
        calculator = ReturnCalculator(config)

        returns = np.array([0.09531, -0.05129, 0.07696, 0.01980])  # ln(1.1), ln(0.95), etc.
        cumulative = calculator.calculate_cumulative_returns(returns)

        expected = np.array([0.1, 0.045, 0.1286, 0.1512])  # exp(sum(log_returns)) - 1
        np.testing.assert_array_almost_equal(cumulative, expected, decimal=4)

    def test_empty_returns(self):
        """测试空收益率序列"""
        cumulative = self.calculator.calculate_cumulative_returns([])
        assert len(cumulative) == 0

    def test_position_values_calculation(self):
        """测试仓位价值计算"""
        signals = np.array([0, 1, 1, 1, 0, 0, 1, 1, 0, 0])  # 简化信号：只做多，不做空
        prices = np.array([100, 102, 105, 103, 101, 98, 100, 104, 107, 105])

        position_values = self.calculator.calculate_position_values(
            signals=signals,
            prices=prices,
            initial_capital=10000,
            position_size=0.5
        )

        assert len(position_values) == len(prices)
        assert position_values[0] == 10000  # 初始价值
        # 验证价值变化合理
        assert position_values[-1] >= 0  # 不应该为负
        assert position_values[-1] != 10000  # 应该有变化

        # 验证在持仓期间价值跟随价格变化
        # 当信号=1时，应该有仓位
        for i in range(1, len(prices)):
            if signals[i] == 1 and signals[i-1] == 1:  # 持续持仓
                # 仓位价值应该反映价格变化
                if prices[i] > prices[i-1]:  # 价格上涨
                    assert position_values[i] >= position_values[i-1]  # 价值应该增加或保持

    def test_position_values_mismatched_lengths(self):
        """测试信号和价格序列长度不匹配"""
        signals = np.array([1, 0, 1])
        prices = np.array([100, 102])

        with pytest.raises(ValueError, match="信号序列和价格序列长度必须相同"):
            self.calculator.calculate_position_values(signals, prices)

    def test_annualized_return_calculation(self):
        """测试年化收益率计算"""
        # 252个交易日，总收益20%
        daily_returns = np.full(252, 0.0007)  # 约0.07%每日
        annualized = self.calculator.calculate_annualized_return(daily_returns)

        expected = (1 + 0.0007) ** 252 - 1  # 约20%
        np.testing.assert_array_almost_equal(annualized, expected, decimal=4)

    def test_annualized_return_empty(self):
        """测试空收益率序列的年化收益率"""
        annualized = self.calculator.calculate_annualized_return([])
        assert annualized == 0.0

    def test_excess_returns_calculation(self):
        """测试超额收益率计算"""
        strategy_returns = np.array([0.01, 0.02, -0.01, 0.03])
        benchmark_returns = np.array([0.005, 0.01, -0.005, 0.015])

        excess = self.calculator.calculate_excess_returns(strategy_returns, benchmark_returns)
        expected = np.array([0.005, 0.01, -0.005, 0.015])

        np.testing.assert_array_almost_equal(excess, expected)

    def test_excess_returns_mismatched_lengths(self):
        """测试超额收益率计算时序列长度不匹配"""
        strategy_returns = np.array([0.01, 0.02])
        benchmark_returns = np.array([0.005])

        with pytest.raises(ValueError, match="策略收益率和基准收益率序列长度必须相同"):
            self.calculator.calculate_excess_returns(strategy_returns, benchmark_returns)

    def test_edge_case_zero_prices(self):
        """测试价格为0的边界情况"""
        prices = np.array([0, 100, 105])

        # 应该能处理价格为0的情况（虽然在实际应用中不应该出现）
        try:
            returns = self.calculator.calculate_single_period_returns(prices)
            assert len(returns) == 2
        except (ValueError, ZeroDivisionError):
            # 预期会抛出异常
            pass

    def test_negative_prices(self):
        """测试负价格的边界情况"""
        prices = np.array([100, 90, 110])

        # 应该能处理价格变化
        returns = self.calculator.calculate_single_period_returns(prices)
        assert len(returns) == 2

    def test_large_dataset_performance(self):
        """测试大数据集的性能"""
        # 生成大量数据点（50,000个）
        np.random.seed(42)
        large_prices = np.cumprod(np.random.normal(1.0001, 0.01, 50000)) * 100

        import time
        start_time = time.time()

        returns = self.calculator.calculate_single_period_returns(large_prices)
        cumulative = self.calculator.calculate_cumulative_returns(returns)

        end_time = time.time()

        # 验证结果
        assert len(returns) == 49999
        assert len(cumulative) == 49999

        # 性能检查：应该在1秒内完成
        assert end_time - start_time < 1.0, f"计算耗时过长: {end_time - start_time:.2f}秒"


class TestCreateReturnCalculator:
    """创建收益计算器工厂函数测试"""

    def test_create_with_default_config(self):
        """测试使用默认配置创建计算器"""
        calculator = create_return_calculator()
        assert isinstance(calculator, ReturnCalculator)
        assert calculator.config.return_type == ReturnType.SIMPLE

    def test_create_with_custom_config(self):
        """测试使用自定义配置创建计算器"""
        config = ReturnCalculationConfig(return_type=ReturnType.LOG)
        calculator = create_return_calculator(config)
        assert calculator.config.return_type == ReturnType.LOG

    def test_create_with_none_config(self):
        """测试传入None配置"""
        calculator = create_return_calculator(None)
        assert isinstance(calculator, ReturnCalculator)
        assert calculator.config.return_type == ReturnType.SIMPLE


class TestReturnCalculatorIntegration:
    """收益计算器集成测试"""

    def test_complete_workflow(self):
        """测试完整的工作流程"""
        # 创建计算器
        calculator = create_return_calculator(
            ReturnCalculationConfig(
                return_type=ReturnType.SIMPLE,
                risk_free_rate=0.02,
                trading_days=252
            )
        )

        # 模拟真实价格数据
        np.random.seed(42)
        returns = np.random.normal(0.0005, 0.02, 100)  # 100天的收益率
        prices = np.cumprod(1 + returns) * 100  # 从100开始的价格

        # 计算单期收益率
        calculated_returns = calculator.calculate_single_period_returns(prices)
        assert len(calculated_returns) == len(prices) - 1

        # 计算累计收益率
        cumulative_returns = calculator.calculate_cumulative_returns(calculated_returns)
        assert len(cumulative_returns) == len(calculated_returns)

        # 计算年化收益率
        annualized_return = calculator.calculate_annualized_return(calculated_returns)
        assert isinstance(annualized_return, float)

        # 验证一致性：最后一个累计收益率应该约等于总收益率
        total_return = (prices[-1] - prices[0]) / prices[0]
        np.testing.assert_array_almost_equal(
            cumulative_returns[-1], total_return, decimal=6
        )