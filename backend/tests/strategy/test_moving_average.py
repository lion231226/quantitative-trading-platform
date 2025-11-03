"""
移动平均线计算引擎测试
"""

import pytest
import numpy as np
from datetime import datetime, timezone

from app.strategy.indicators import SMA, EMA, MovingAverageCalculator, MAType


class TestSMA:
    """SMA指标测试"""

    def test_sma_initialization(self):
        """测试SMA初始化"""
        sma = SMA(20)
        assert sma.period == 20
        assert sma.get_ma_type() == MAType.SMA
        assert not sma.is_initialized
        assert sma.current_value is None

    def test_sma_invalid_period(self):
        """测试无效周期"""
        with pytest.raises(ValueError):
            SMA(0)
        with pytest.raises(ValueError):
            SMA(-5)

    def test_sma_calculation_single(self):
        """测试SMA单值计算"""
        sma = SMA(3)

        # 前两个值应该返回None（数据不足）
        assert sma.calculate_single(10.0) is None
        assert sma.calculate_single(11.0) is None
        assert not sma.is_initialized

        # 第三个值应该返回有效SMA
        sma_value = sma.calculate_single(12.0)
        assert sma_value == (10.0 + 11.0 + 12.0) / 3
        assert sma.is_initialized
        assert sma.current_value == sma_value

    def test_sma_calculation_batch(self):
        """测试SMA批量计算"""
        sma = SMA(5)
        prices = [10, 11, 12, 13, 14, 15, 16, 17, 18, 19]
        timestamps = [int(datetime.now(tz=timezone.utc).timestamp()) + i for i in range(len(prices))]

        result = sma.calculate_batch(prices, timestamps)

        # 应该有6个有效值（10-3=7，但最后一个可能因为对齐问题只有6个）
        assert len(result.values) == len(prices) - sma.period + 1
        assert len(result.timestamps) == len(result.values)
        assert result.ma_type == MAType.SMA
        assert result.period == 5

        # 验证第一个SMA值
        expected_first_sma = sum(prices[:5]) / 5
        assert abs(result.values[0] - expected_first_sma) < 1e-10

    def test_sma_reset(self):
        """测试SMA重置"""
        sma = SMA(3)

        # 计算一些值
        sma.calculate_single(10.0)
        sma.calculate_single(11.0)
        sma.calculate_single(12.0)

        assert sma.is_initialized
        assert len(sma.values) == 1

        # 重置
        sma.reset()

        assert not sma.is_initialized
        assert len(sma.values) == 0
        assert sma.current_value is None

    def test_sma_update(self):
        """测试SMA更新"""
        sma = SMA(3)
        timestamp = int(datetime.now(tz=timezone.utc).timestamp())

        # 更新值
        result1 = sma.update(10.0, timestamp)
        assert result1 is None

        result2 = sma.update(11.0, timestamp + 1)
        assert result2 is None

        result3 = sma.update(12.0, timestamp + 2)
        assert result3 == (10.0 + 11.0 + 12.0) / 3
        assert len(sma.values) == 1
        assert len(sma.timestamps) == 1


class TestEMA:
    """EMA指标测试"""

    def test_ema_initialization(self):
        """测试EMA初始化"""
        ema = EMA(20)
        assert ema.period == 20
        assert ema.get_ma_type() == MAType.EMA
        assert ema._multiplier == 2.0 / (20 + 1)
        assert not ema.is_initialized

    def test_ema_calculation_single(self):
        """测试EMA单值计算"""
        ema = EMA(3)

        # 第一个值应该返回价格本身
        first_value = ema.calculate_single(10.0)
        assert first_value == 10.0
        assert ema.is_initialized
        assert ema.current_value == 10.0

        # 第二个值应该使用EMA公式计算
        second_value = ema.calculate_single(11.0)
        k = 2.0 / (3 + 1)  # 平滑系数
        expected_second = 11.0 * k + 10.0 * (1 - k)
        assert abs(second_value - expected_second) < 1e-10

        # 第三个值
        third_value = ema.calculate_single(12.0)
        expected_third = 12.0 * k + second_value * (1 - k)
        assert abs(third_value - expected_third) < 1e-10

    def test_ema_calculation_batch(self):
        """测试EMA批量计算"""
        ema = EMA(5)
        prices = [10, 11, 12, 13, 14, 15, 16]
        timestamps = [int(datetime.now(tz=timezone.utc).timestamp()) + i for i in range(len(prices))]

        result = ema.calculate_batch(prices, timestamps)

        # EMA从第一个值开始就有结果
        assert len(result.values) == len(prices)
        assert result.ma_type == MAType.EMA
        assert result.period == 5

        # 第一个值应该等于第一个价格
        assert result.values[0] == prices[0]

    def test_ema_reset(self):
        """测试EMA重置"""
        ema = EMA(3)

        # 计算一些值
        ema.calculate_single(10.0)
        ema.calculate_single(11.0)

        assert ema.is_initialized
        assert ema._previous_ema is not None

        # 重置
        ema.reset()

        assert not ema.is_initialized
        assert ema._previous_ema is None
        assert not ema._first_value_calculated


class TestMovingAverageCalculator:
    """移动平均线计算器测试"""

    def test_calculator_initialization(self):
        """测试计算器初始化"""
        calc = MovingAverageCalculator()
        assert len(calc.list_indicators()) == 0

    def test_create_sma_indicator(self):
        """测试创建SMA指标"""
        calc = MovingAverageCalculator()

        sma = calc.create_indicator(MAType.SMA, 20, "test_sma")
        assert isinstance(sma, SMA)
        assert sma.period == 20
        assert len(calc.list_indicators()) == 1
        assert "test_sma" in calc.list_indicators()

    def test_create_ema_indicator(self):
        """测试创建EMA指标"""
        calc = MovingAverageCalculator()

        ema = calc.create_indicator(MAType.EMA, 10, "test_ema")
        assert isinstance(ema, EMA)
        assert ema.period == 10
        assert len(calc.list_indicators()) == 1

    def test_get_and_remove_indicator(self):
        """测试获取和移除指标"""
        calc = MovingAverageCalculator()

        # 创建指标
        sma = calc.create_indicator(MAType.SMA, 20, "test_sma")
        ema = calc.create_indicator(MAType.EMA, 10, "test_ema")

        # 获取指标
        retrieved_sma = calc.get_indicator("test_sma")
        assert retrieved_sma is sma

        # 移除指标
        assert calc.remove_indicator("test_sma") is True
        assert calc.get_indicator("test_sma") is None
        assert len(calc.list_indicators()) == 1

        # 移除不存在的指标
        assert calc.remove_indicator("nonexistent") is False

    def test_calculate_from_dataframe(self):
        """测试从DataFrame计算"""
        import pandas as pd

        calc = MovingAverageCalculator()

        # 创建测试数据
        data = {
            'close': [10, 11, 12, 13, 14, 15, 16, 17, 18, 19],
            'open': [9.5, 10.5, 11.5, 12.5, 13.5, 14.5, 15.5, 16.5, 17.5, 18.5]
        }
        df = pd.DataFrame(data)

        # 计算SMA
        result = calc.calculate_from_dataframe(df, 'close', MAType.SMA, 5)

        assert result.ma_type == MAType.SMA
        assert result.period == 5
        assert len(result.values) == len(df) - 5 + 1

        # 验证第一个SMA值
        expected_first_sma = sum(data['close'][:5]) / 5
        assert abs(result.values[0] - expected_first_sma) < 1e-10

    def test_calculate_cross_signals(self):
        """测试交叉信号计算"""
        calc = MovingAverageCalculator()

        # 创建测试数据：价格从低于均线变为高于均线（金叉）
        prices = [8, 9, 10, 11, 12, 13, 14, 15, 16, 17]
        timestamps = [int(datetime.now(tz=timezone.utc).timestamp()) + i for i in range(len(prices))]

        signals = calc.calculate_cross_signals(prices, timestamps, MAType.SMA, 5)

        # 应该检测到一个金叉信号
        assert 'golden_cross' in signals
        assert 'death_cross' in signals

        # 检查信号数量（可能0个或多个，取决于数据）
        assert isinstance(signals['golden_cross'], list)
        assert isinstance(signals['death_cross'], list)

    def test_reset_all(self):
        """测试重置所有指标"""
        calc = MovingAverageCalculator()

        # 创建多个指标
        sma1 = calc.create_indicator(MAType.SMA, 10, "sma1")
        sma2 = calc.create_indicator(MAType.SMA, 20, "sma2")
        ema1 = calc.create_indicator(MAType.EMA, 5, "ema1")

        # 计算一些值
        for i in range(15):
            sma1.calculate_single(10 + i)
            sma2.calculate_single(10 + i)
            ema1.calculate_single(10 + i)

        # 验证指标已初始化
        assert sma1.is_initialized
        assert sma2.is_initialized
        assert ema1.is_initialized

        # 重置所有指标
        calc.reset_all()

        # 验证所有指标都已重置
        assert not sma1.is_initialized
        assert not sma2.is_initialized
        assert not ema1.is_initialized


class TestMovingAverageEdgeCases:
    """移动平均线边界情况测试"""

    def test_empty_data(self):
        """测试空数据"""
        sma = SMA(10)
        result = sma.calculate_batch([], [])
        assert len(result.values) == 0
        assert len(result.timestamps) == 0

    def test_insufficient_data(self):
        """测试数据不足"""
        sma = SMA(10)
        prices = [10, 11, 12]
        timestamps = [1, 2, 3]

        result = sma.calculate_batch(prices, timestamps)
        assert len(result.values) == 0  # 数据不足，没有有效结果

    def test_mismatched_lengths(self):
        """测试长度不匹配的数据"""
        sma = SMA(5)
        prices = [10, 11, 12, 13, 14, 15]
        timestamps = [1, 2, 3, 4, 5]  # 长度不匹配

        with pytest.raises(ValueError):
            sma.calculate_batch(prices, timestamps)

    def test_constant_prices(self):
        """测试价格不变的情况"""
        ema = EMA(5)
        constant_prices = [100] * 10
        timestamps = list(range(10))

        result = ema.calculate_batch(constant_prices, timestamps)

        # EMA应该逐渐接近常数价格
        for value in result.values:
            assert abs(value - 100) < 1e-10

    def test_large_price_movements(self):
        """测试大幅价格变动"""
        sma = SMA(3)
        prices = [100, 1000, 1, 10000, 0.1, 500]
        timestamps = list(range(len(prices)))

        result = sma.calculate_batch(prices, timestamps)

        # 验证计算不会出错
        assert len(result.values) == len(prices) - 3 + 1
        for value in result.values:
            assert isinstance(value, (int, float))
            assert not np.isnan(value)
            assert not np.isinf(value)

    def test_negative_prices(self):
        """测试负价格（虽然不现实，但测试鲁棒性）"""
        ema = EMA(5)
        prices = [-10, -5, 0, 5, 10, 15]
        timestamps = list(range(len(prices)))

        result = ema.calculate_batch(prices, timestamps)

        # 应该能正常计算
        assert len(result.values) == len(prices)
        assert all(isinstance(v, (int, float)) for v in result.values)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])