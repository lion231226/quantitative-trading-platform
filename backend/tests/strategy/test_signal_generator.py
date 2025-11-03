"""
交易信号生成器测试
"""

import pytest
from datetime import datetime, timezone

from app.strategy.signals import (
    SignalGenerator, SignalConfig, SignalType, SignalStrength,
    CrossDetector, SignalFilter, TradingSignal
)
from app.strategy.indicators import MAType


class TestSignalConfig:
    """信号配置测试"""

    def test_default_config(self):
        """测试默认配置"""
        config = SignalConfig()
        assert config.ma_type == MAType.SMA
        assert config.ma_period == 20
        assert config.min_cross_percentage == 0.001
        assert config.confirmation_periods == 1
        assert config.max_signals_per_day == 10
        assert config.signal_cooldown == 300

    def test_config_validation(self):
        """测试配置验证"""
        # 有效配置
        valid_config = SignalConfig()
        assert valid_config.validate() is True

        # 无效配置
        invalid_config = SignalConfig(ma_period=0)
        assert invalid_config.validate() is False

        invalid_config = SignalConfig(min_cross_percentage=-0.01)
        assert invalid_config.validate() is False

        invalid_config = SignalConfig(max_signals_per_day=0)
        assert invalid_config.validate() is False

    def test_custom_config(self):
        """测试自定义配置"""
        config = SignalConfig(
            ma_type=MAType.EMA,
            ma_period=10,
            min_cross_percentage=0.005,
            confirmation_periods=2
        )

        assert config.ma_type == MAType.EMA
        assert config.ma_period == 10
        assert config.min_cross_percentage == 0.005
        assert config.confirmation_periods == 2


class TestCrossDetector:
    """交叉检测器测试"""

    def test_detect_golden_cross(self):
        """测试金叉检测"""
        detector = CrossDetector()

        # 创建金叉场景：价格从下方向上突破MA
        prices = [8, 9, 10, 11, 12, 13, 14, 15]  # 价格上升
        ma_values = [10] * len(prices)  # 固定MA值
        timestamps = list(range(len(prices)))

        crosses = detector.detect_crosses(prices, ma_values, timestamps)

        # 应该检测到金叉（返回的是列表格式）
        golden_crosses = [cross for cross in crosses if cross[1] == 'golden_cross']
        assert len(golden_crosses) >= 1

        # 验证金叉时间戳在价格超过MA的位置
        for cross_timestamp, cross_type in golden_crosses:
            cross_index = timestamps.index(cross_timestamp)
            assert prices[cross_index] > ma_values[cross_index]
            if cross_index > 0:
                assert prices[cross_index - 1] <= ma_values[cross_index - 1]

    def test_detect_death_cross(self):
        """测试死叉检测"""
        detector = CrossDetector()

        # 创建死叉场景：价格从上方向下突破MA
        prices = [15, 14, 13, 12, 11, 10, 9, 8]  # 价格下降
        ma_values = [10] * len(prices)  # 固定MA值
        timestamps = list(range(len(prices)))

        crosses = detector.detect_crosses(prices, ma_values, timestamps)

        # 应该检测到死叉（返回的是列表格式）
        death_crosses = [cross for cross in crosses if cross[1] == 'death_cross']
        assert len(death_crosses) >= 1

        # 验证死叉时间戳在价格跌破MA的位置
        for cross_timestamp, cross_type in death_crosses:
            cross_index = timestamps.index(cross_timestamp)
            assert prices[cross_index] < ma_values[cross_index]
            if cross_index > 0:
                assert prices[cross_index - 1] >= ma_values[cross_index - 1]

    def test_no_crosses(self):
        """测试无交叉场景"""
        detector = CrossDetector()

        # 创建无交叉场景：价格始终在MA之上
        prices = [12, 13, 14, 15, 16]
        ma_values = [10] * len(prices)
        timestamps = list(range(len(prices)))

        crosses = detector.detect_crosses(prices, ma_values, timestamps)

        # 应该没有死叉，但可能有金叉（取决于起始位置）
        death_crosses = [cross for cross in crosses if cross[1] == 'death_cross']
        assert len(death_crosses) == 0

    def test_min_cross_percentage_filter(self):
        """测试最小穿越百分比过滤"""
        detector = CrossDetector()

        # 创建小幅波动场景
        prices = [9.9, 10.0, 10.1, 10.0, 9.9]  # 小幅波动
        ma_values = [10.0] * len(prices)
        timestamps = list(range(len(prices)))

        # 设置较高的最小穿越百分比
        min_cross_pct = 0.02  # 2%
        crosses = detector.detect_crosses(prices, ma_values, timestamps, min_cross_pct)

        # 由于波动太小，应该检测不到交叉
        golden_crosses = [cross for cross in crosses if cross[1] == 'golden_cross']
        death_crosses = [cross for cross in crosses if cross[1] == 'death_cross']
        total_crosses = len(golden_crosses) + len(death_crosses)
        assert total_crosses == 0

    def test_confirm_signal(self):
        """测试信号确认"""
        detector = CrossDetector()

        # 创建金叉确认场景
        prices = [8, 9, 10, 11, 12, 13, 14, 15]
        ma_values = [10, 10.5, 11, 11.5, 12, 12.5, 13, 13.5]
        timestamps = list(range(len(prices)))

        # 在第2个位置有金叉（价格10超过MA10）
        cross_index = 2

        # 1周期确认
        confirmed = detector.confirm_signal(prices, ma_values, cross_index, 1)
        assert confirmed is True

        # 多周期确认
        confirmed = detector.confirm_signal(prices, ma_values, cross_index, 3)
        assert confirmed is True

    def test_signal_confirmation_failure(self):
        """测试信号确认失败"""
        detector = CrossDetector()

        # 创建假突破场景：金叉后立即跌破
        prices = [9, 10, 11, 9, 8, 7]  # 突破后立即回落
        ma_values = [10, 10, 10, 10, 10, 10]
        timestamps = list(range(len(prices)))

        # 在第1个位置有金叉
        cross_index = 1

        # 多周期确认应该失败
        confirmed = detector.confirm_signal(prices, ma_values, cross_index, 3)
        assert confirmed is False


class TestSignalFilter:
    """信号过滤器测试"""

    def test_cooldown_filter(self):
        """测试冷却时间过滤"""
        config = SignalConfig(signal_cooldown=300)  # 5分钟冷却
        filter_obj = SignalFilter(config)

        # 创建第一个信号
        signal1 = TradingSignal(
            signal_type=SignalType.BUY,
            timestamp=1000,
            price=10.0,
            ma_value=9.5,
            strength=SignalStrength.MEDIUM,
            confidence=0.7,
            reason="测试信号1"
        )

        assert filter_obj.filter_signal(signal1) is True

        # 创建第二个信号（在冷却时间内）
        signal2 = TradingSignal(
            signal_type=SignalType.BUY,
            timestamp=1200,  # 只过了200秒
            price=10.5,
            ma_value=10.0,
            strength=SignalStrength.MEDIUM,
            confidence=0.7,
            reason="测试信号2"
        )

        assert filter_obj.filter_signal(signal2) is False

        # 创建第三个信号（超出冷却时间）
        signal3 = TradingSignal(
            signal_type=SignalType.BUY,
            timestamp=1400,  # 过了400秒，超出300秒冷却
            price=11.0,
            ma_value=10.5,
            strength=SignalStrength.MEDIUM,
            confidence=0.7,
            reason="测试信号3"
        )

        assert filter_obj.filter_signal(signal3) is True

    def test_daily_signal_limit(self):
        """测试每日信号数量限制"""
        config = SignalConfig(max_signals_per_day=3)
        filter_obj = SignalFilter(config)

        base_timestamp = int(datetime(2023, 1, 1, 10, 0, 0, tzinfo=timezone.utc).timestamp())

        # 创建4个信号（超过限制）
        for i in range(4):
            signal = TradingSignal(
                signal_type=SignalType.BUY,
                timestamp=base_timestamp + i * 100,
                price=10.0 + i,
                ma_value=9.5 + i,
                strength=SignalStrength.MEDIUM,
                confidence=0.7,
                reason=f"测试信号{i+1}"
            )

            if i < 3:
                assert filter_obj.filter_signal(signal) is True
            else:
                assert filter_obj.filter_signal(signal) is False

    def test_date_reset(self):
        """测试日期重置"""
        config = SignalConfig(max_signals_per_day=2)
        filter_obj = SignalFilter(config)

        # 第一天的信号
        day1_timestamp = int(datetime(2023, 1, 1, 10, 0, 0, tzinfo=timezone.utc).timestamp())

        signal1 = TradingSignal(
            signal_type=SignalType.BUY,
            timestamp=day1_timestamp,
            price=10.0,
            ma_value=9.5,
            strength=SignalStrength.MEDIUM,
            confidence=0.7,
            reason="第一天信号1"
        )

        signal2 = TradingSignal(
            signal_type=SignalType.BUY,
            timestamp=day1_timestamp + 100,
            price=10.5,
            ma_value=10.0,
            strength=SignalStrength.MEDIUM,
            confidence=0.7,
            reason="第一天信号2"
        )

        # 第二天的信号（应该重置计数器）
        day2_timestamp = int(datetime(2023, 1, 2, 10, 0, 0, tzinfo=timezone.utc).timestamp())

        signal3 = TradingSignal(
            signal_type=SignalType.BUY,
            timestamp=day2_timestamp,
            price=11.0,
            ma_value=10.5,
            strength=SignalStrength.MEDIUM,
            confidence=0.7,
            reason="第二天信号1"
        )

        assert filter_obj.filter_signal(signal1) is True
        assert filter_obj.filter_signal(signal2) is True
        assert filter_obj.filter_signal(signal3) is True  # 应该被允许，因为是新的一天

    def test_filter_reset(self):
        """测试过滤器重置"""
        config = SignalConfig(signal_cooldown=300)
        filter_obj = SignalFilter(config)

        # 处理一些信号
        signal = TradingSignal(
            signal_type=SignalType.BUY,
            timestamp=1000,
            price=10.0,
            ma_value=9.5,
            strength=SignalStrength.MEDIUM,
            confidence=0.7,
            reason="测试信号"
        )

        filter_obj.filter_signal(signal)
        assert filter_obj.last_signal_time == 1000
        assert filter_obj.signals_today == 1

        # 重置
        filter_obj.reset()
        assert filter_obj.last_signal_time == 0
        assert filter_obj.signals_today == 0
        assert filter_obj.last_date is None


class TestSignalGenerator:
    """信号生成器测试"""

    def test_generator_initialization(self):
        """测试信号生成器初始化"""
        config = SignalConfig()
        generator = SignalGenerator(config)

        assert generator.config is config
        assert generator.ma_calculator is not None
        assert generator.cross_detector is not None
        assert generator.signal_filter is not None

    def test_generator_with_invalid_config(self):
        """测试无效配置的初始化"""
        invalid_config = SignalConfig(ma_period=0)
        with pytest.raises(ValueError):
            SignalGenerator(invalid_config)

    def test_generate_signals_with_insufficient_data(self):
        """测试数据不足时的信号生成"""
        config = SignalConfig(ma_period=10)
        generator = SignalGenerator(config)

        prices = [10, 11, 12]  # 只有3个数据点，少于MA周期10
        timestamps = list(range(len(prices)))

        signals = generator.generate_signals_from_data(prices, timestamps)
        assert len(signals) == 0

    def test_generate_signals_golden_cross(self):
        """测试生成金叉信号"""
        config = SignalConfig(ma_period=5, min_cross_percentage=0.01)
        generator = SignalGenerator(config)

        # 创建金叉场景
        prices = [8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19]
        timestamps = list(range(len(prices)))

        signals = generator.generate_signals_from_data(prices, timestamps)

        # 应该至少有一个买入信号
        buy_signals = [s for s in signals if s.signal_type == SignalType.BUY]
        assert len(buy_signals) >= 1

        # 验证信号属性
        for signal in buy_signals:
            assert isinstance(signal, TradingSignal)
            assert signal.signal_type == SignalType.BUY
            assert signal.price > 0
            assert signal.ma_value > 0
            assert signal.strength in SignalStrength
            assert 0 <= signal.confidence <= 1
            assert len(signal.reason) > 0

    def test_generate_signals_death_cross(self):
        """测试生成死叉信号"""
        config = SignalConfig(ma_period=5, min_cross_percentage=0.01)
        generator = SignalGenerator(config)

        # 创建死叉场景
        prices = [19, 18, 17, 16, 15, 14, 13, 12, 11, 10, 9, 8]
        timestamps = list(range(len(prices)))

        signals = generator.generate_signals_from_data(prices, timestamps)

        # 应该至少有一个卖出信号
        sell_signals = [s for s in signals if s.signal_type == SignalType.SELL]
        assert len(sell_signals) >= 1

        # 验证信号属性
        for signal in sell_signals:
            assert isinstance(signal, TradingSignal)
            assert signal.signal_type == SignalType.SELL
            assert signal.price > 0
            assert signal.ma_value > 0

    def test_signal_filtering(self):
        """测试信号过滤"""
        config = SignalConfig(
            ma_period=3,
            signal_cooldown=1000,  # 很长的冷却时间
            max_signals_per_day=1
        )
        generator = SignalGenerator(config)

        # 创建多个潜在信号的场景
        prices = [8, 12, 8, 12, 8, 12, 8, 12, 8, 12]
        timestamps = [i * 100 for i in range(len(prices))]  # 每100秒一个数据点

        signals = generator.generate_signals_from_data(prices, timestamps)

        # 由于冷却时间和每日限制，实际信号应该很少
        assert len(signals) <= 2  # 最多2个信号（一个买入，一个卖出）

    def test_generate_single_signal(self):
        """测试生成单个信号"""
        config = SignalConfig(ma_period=5)
        generator = SignalGenerator(config)

        # 历史数据
        historical_data = {
            'prices': [10, 11, 12, 13, 14],
            'timestamps': list(range(5))
        }

        # 当前数据
        current_price = 15.0
        current_timestamp = 5

        signal = generator.generate_single_signal(
            current_price, current_timestamp, historical_data
        )

        # 可能返回信号或None
        if signal:
            assert isinstance(signal, TradingSignal)
            assert signal.timestamp == current_timestamp
            assert signal.price == current_price

    def test_config_update(self):
        """测试配置更新"""
        config = SignalConfig(ma_period=10)
        generator = SignalGenerator(config)

        # 更新配置
        new_config = SignalConfig(ma_period=20, min_cross_percentage=0.005)
        generator.update_config(new_config)

        assert generator.config is new_config
        assert generator.config.ma_period == 20
        assert generator.config.min_cross_percentage == 0.005

    def test_invalid_config_update(self):
        """测试无效配置更新"""
        config = SignalConfig(ma_period=10)
        generator = SignalGenerator(config)

        # 尝试更新为无效配置
        invalid_config = SignalConfig(ma_period=0)
        with pytest.raises(ValueError):
            generator.update_config(invalid_config)

    def test_generator_reset(self):
        """测试信号生成器重置"""
        config = SignalConfig()
        generator = SignalGenerator(config)

        # 生成一些信号
        prices = [8, 12, 8, 12, 8, 12]
        timestamps = list(range(len(prices)))
        generator.generate_signals_from_data(prices, timestamps)

        # 重置
        generator.reset()

        # 重新生成信号应该得到相同结果
        signals1 = generator.generate_signals_from_data(prices, timestamps)
        generator.reset()
        signals2 = generator.generate_signals_from_data(prices, timestamps)

        # 信号数量应该相同
        assert len(signals1) == len(signals2)


class TestTradingSignal:
    """交易信号测试"""

    def test_signal_creation(self):
        """测试信号创建"""
        signal = TradingSignal(
            signal_type=SignalType.BUY,
            timestamp=1234567890,
            price=10.5,
            ma_value=10.0,
            strength=SignalStrength.STRONG,
            confidence=0.8,
            reason="价格突破移动平均线"
        )

        assert signal.signal_type == SignalType.BUY
        assert signal.timestamp == 1234567890
        assert signal.price == 10.5
        assert signal.ma_value == 10.0
        assert signal.strength == SignalStrength.STRONG
        assert signal.confidence == 0.8
        assert signal.reason == "价格突破移动平均线"

    def test_signal_to_dict(self):
        """测试信号转换为字典"""
        signal = TradingSignal(
            signal_type=SignalType.SELL,
            timestamp=1234567890,
            price=15.0,
            ma_value=15.5,
            strength=SignalStrength.WEAK,
            confidence=0.3,
            reason="价格跌破移动平均线"
        )

        signal_dict = signal.to_dict()

        assert signal_dict['signal_type'] == 'SELL'
        assert signal_dict['timestamp'] == 1234567890
        assert signal_dict['price'] == 15.0
        assert signal_dict['ma_value'] == 15.5
        assert signal_dict['strength'] == 1  # SignalStrength.WEAK.value
        assert signal_dict['confidence'] == 0.3
        assert signal_dict['reason'] == "价格跌破移动平均线"

    def test_signal_datetime_property(self):
        """测试信号日期时间属性"""
        timestamp = 1234567890
        signal = TradingSignal(
            signal_type=SignalType.BUY,
            timestamp=timestamp,
            price=10.0,
            ma_value=9.5,
            strength=SignalStrength.MEDIUM,
            confidence=0.5,
            reason="测试信号"
        )

        signal_datetime = signal.datetime
        assert signal_datetime.year == 2009
        assert signal_datetime.month == 2
        assert signal_datetime.day == 13
        assert signal_datetime.hour == 23
        assert signal_datetime.minute == 31
        assert signal_datetime.second == 30


if __name__ == "__main__":
    pytest.main([__file__, "-v"])