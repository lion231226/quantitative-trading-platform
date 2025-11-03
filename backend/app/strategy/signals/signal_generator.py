"""
交易信号生成器
实现基于移动平均线的交易信号生成逻辑
"""

from typing import List, Dict, Any, Optional, Tuple, Union, Any
from dataclasses import dataclass, field
from enum import Enum
import pandas as pd
import numpy as np
from datetime import datetime, timezone
import structlog

from ..indicators import MovingAverageCalculator, MAType, MAResult

logger = structlog.get_logger()


class SignalType(Enum):
    """交易信号类型"""
    BUY = "BUY"          # 买入信号
    SELL = "SELL"        # 卖出信号
    HOLD = "HOLD"        # 持有信号（无操作）
    CLOSE_BUY = "CLOSE_BUY"  # 平买仓
    CLOSE_SELL = "CLOSE_SELL" # 平卖仓


class SignalStrength(Enum):
    """信号强度"""
    WEAK = 1      # 弱信号
    MEDIUM = 2    # 中等信号
    STRONG = 3    # 强信号


@dataclass
class TradingSignal:
    """交易信号数据结构"""
    signal_type: SignalType
    timestamp: int
    price: float
    ma_value: float
    strength: SignalStrength
    confidence: float  # 信号置信度 (0-1)
    reason: str       # 信号原因说明
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'signal_type': self.signal_type.value,
            'timestamp': self.timestamp,
            'price': self.price,
            'ma_value': self.ma_value,
            'strength': self.strength.value,
            'confidence': self.confidence,
            'reason': self.reason,
            'metadata': self.metadata
        }

    @property
    def datetime(self) -> datetime:
        """获取信号的日期时间"""
        return datetime.fromtimestamp(self.timestamp, tz=timezone.utc)


@dataclass
class SignalConfig:
    """信号生成配置"""
    # 移动平均线参数
    ma_type: MAType = MAType.SMA
    ma_period: int = 20

    # 信号确认参数
    min_cross_percentage: float = 0.001  # 最小穿越百分比（避免小幅波动）
    confirmation_periods: int = 1        # 确认周期数
    volume_threshold: Optional[float] = None  # 成交量阈值

    # 信号过滤参数
    min_price_change: float = 0.0005    # 最小价格变化
    max_signals_per_day: int = 10       # 每日最大信号数
    signal_cooldown: int = 300          # 信号冷却时间（秒）

    # 风险控制参数
    max_position_size: float = 1.0      # 最大仓位
    stop_loss_pct: float = 0.02         # 止损百分比
    take_profit_pct: float = 0.05       # 止盈百分比

    def validate(self) -> bool:
        """验证配置参数"""
        if self.ma_period <= 0:
            return False
        if self.min_cross_percentage < 0:
            return False
        if self.confirmation_periods < 1:
            return False
        if self.min_price_change < 0:
            return False
        if self.max_signals_per_day <= 0:
            return False
        if self.signal_cooldown < 0:
            return False
        if not 0 < self.max_position_size <= 1:
            return False
        if not 0 < self.stop_loss_pct < 1:
            return False
        if not 0 < self.take_profit_pct < 1:
            return False
        return True


class CrossDetector:
    """价格与移动平均线交叉检测器"""

    @staticmethod
    def detect_crosses(prices: List[float],
                      ma_values: List[float],
                      timestamps: List[int],
                      min_cross_pct: float = 0.001) -> List[Tuple[int, str]]:
        """
        检测价格与移动平均线的交叉点

        Args:
            prices: 价格列表
            ma_values: 移动平均线值列表
            timestamps: 时间戳列表
            min_cross_pct: 最小穿越百分比

        Returns:
            交叉点列表 [(timestamp, cross_type), ...]
            cross_type: 'golden_cross' 或 'death_cross'
        """
        if len(prices) != len(ma_values) or len(prices) != len(timestamps):
            raise ValueError("价格、移动平均线值和时间戳列表长度不一致")

        if len(prices) < 2:
            return []

        crosses = []
        for i in range(1, len(prices)):
            prev_price = prices[i-1]
            curr_price = prices[i]
            prev_ma = ma_values[i-1]
            curr_ma = ma_values[i]  # 使用当前MA值进行交叉判断

            # 计算穿越百分比
            cross_pct = abs(curr_price - prev_ma) / prev_ma

            if cross_pct < min_cross_pct:
                continue  # 忽略小幅波动

            # 金叉检测：价格从下方向上突破移动平均线
            if prev_price <= prev_ma and curr_price > prev_ma:
                crosses.append((timestamps[i], 'golden_cross'))

            # 死叉检测：价格从上方向下突破移动平均线
            elif prev_price >= prev_ma and curr_price < prev_ma:
                crosses.append((timestamps[i], 'death_cross'))

        return crosses

    @staticmethod
    def confirm_signal(prices: List[float],
                      ma_values: List[float],
                      cross_index: int,
                      confirmation_periods: int = 1) -> bool:
        """
        确认交叉信号的有效性

        Args:
            prices: 价格列表
            ma_values: 移动平均线值列表
            cross_index: 交叉点索引
            confirmation_periods: 确认周期数

        Returns:
            信号是否有效
        """
        if cross_index + confirmation_periods >= len(prices):
            return False

        # 检查后续确认周期的价格走向
        for i in range(1, confirmation_periods + 1):
            idx = cross_index + i
            if idx >= len(prices):
                break

            price = prices[idx]
            ma_value = ma_values[idx]

            # 对于金叉，后续价格应该保持在MA之上
            if prices[cross_index] > ma_values[cross_index]:  # 金叉
                if price <= ma_value:
                    return False
            # 对于死叉，后续价格应该保持在MA之下
            else:  # 死叉
                if price >= ma_value:
                    return False

        return True


class SignalFilter:
    """信号过滤器"""

    def __init__(self, config: SignalConfig) -> Any:
        self.config = config
        self.last_signal_time = 0
        self.signals_today = 0
        self.last_date = None

    def filter_signal(self, signal: TradingSignal) -> bool:
        """
        过滤交易信号

        Args:
            signal: 交易信号

        Returns:
            信号是否通过过滤
        """
        current_time = signal.timestamp
        current_date = datetime.fromtimestamp(current_time).date()

        # 检查日期变化，重置每日计数器
        if self.last_date != current_date:
            self.last_date = current_date
            self.signals_today = 0

        # 冷却时间检查
        if current_time - self.last_signal_time < self.config.signal_cooldown:
            logger.debug("信号被冷却时间过滤",
                        signal_time=current_time,
                        last_signal_time=self.last_signal_time,
                        cooldown=self.config.signal_cooldown)
            return False

        # 每日信号数量限制
        if self.signals_today >= self.config.max_signals_per_day:
            logger.debug("超过每日最大信号数限制",
                        signals_today=self.signals_today,
                        max_signals=self.config.max_signals_per_day)
            return False

        # 更新统计信息
        self.last_signal_time = current_time
        self.signals_today += 1

        return True

    def reset(self) -> Any:
        """重置过滤器状态"""
        self.last_signal_time = 0
        self.signals_today = 0
        self.last_date = None


class SignalGenerator:
    """交易信号生成器"""

    def __init__(self, config: SignalConfig) -> Any:
        if not config.validate():
            raise ValueError("信号配置参数无效")

        self.config = config
        self.ma_calculator = MovingAverageCalculator()
        self.cross_detector = CrossDetector()
        self.signal_filter = SignalFilter(config)

    def generate_signals_from_data(self,
                                  prices: List[float],
                                  timestamps: List[int],
                                  volumes: Optional[List[float]] = None) -> List[TradingSignal]:
        """
        从价格数据生成交易信号

        Args:
            prices: 价格列表
            timestamps: 时间戳列表
            volumes: 成交量列表（可选）

        Returns:
            交易信号列表
        """
        if len(prices) != len(timestamps):
            raise ValueError("价格和时间戳列表长度不一致")

        if len(prices) < self.config.ma_period:
            logger.warning("数据不足，无法生成信号",
                         data_length=len(prices),
                         required_period=self.config.ma_period)
            return []

        # 计算移动平均线
        ma_result = self.ma_calculator.calculate_batch(
            prices, timestamps, self.config.ma_type, self.config.ma_period
        )

        if len(ma_result.values) < 2:
            return []

        # 检测交叉点
        aligned_prices = prices[-len(ma_result.values):]
        aligned_timestamps = timestamps[-len(ma_result.values):]

        crosses = self.cross_detector.detect_crosses(
            aligned_prices, ma_result.values, aligned_timestamps,
            self.config.min_cross_percentage
        )

        # 生成交易信号
        signals = []
        for cross_timestamp, cross_type in crosses:
            signal = self._create_signal_from_cross(
                cross_timestamp, cross_type, aligned_prices, ma_result.values, aligned_timestamps
            )
            if signal and self.signal_filter.filter_signal(signal):
                signals.append(signal)

        return signals

    def _create_signal_from_cross(self,
                                 cross_timestamp: int,
                                 cross_type: str,
                                 prices: List[float],
                                 ma_values: List[float],
                                 timestamps: List[int]) -> Optional[TradingSignal]:
        """从交叉点创建交易信号"""
        try:
            cross_index = timestamps.index(cross_timestamp)
        except ValueError:
            return None

        # 确认信号有效性
        if not self.cross_detector.confirm_signal(
            prices, ma_values, cross_index, self.config.confirmation_periods
        ):
            return None

        price = prices[cross_index]
        ma_value = ma_values[cross_index]

        # 计算信号强度和置信度
        strength, confidence = self._calculate_signal_strength(
            price, ma_value, cross_type, cross_index, prices, ma_values
        )

        # 确定信号类型
        if cross_type == 'golden_cross':
            signal_type = SignalType.BUY
            reason = f"价格{price:.4f}从下方突破{self.config.ma_type.value}({self.config.ma_period}){ma_value:.4f}"
        else:  # death_cross
            signal_type = SignalType.SELL
            reason = f"价格{price:.4f}从上方跌破{self.config.ma_type.value}({self.config.ma_period}){ma_value:.4f}"

        return TradingSignal(
            signal_type=signal_type,
            timestamp=cross_timestamp,
            price=price,
            ma_value=ma_value,
            strength=strength,
            confidence=confidence,
            reason=reason,
            metadata={
                'cross_type': cross_type,
                'ma_type': self.config.ma_type.value,
                'ma_period': self.config.ma_period,
                'cross_percentage': abs(price - ma_value) / ma_value
            }
        )

    def _calculate_signal_strength(self,
                                  price: float,
                                  ma_value: float,
                                  cross_type: str,
                                  cross_index: int,
                                  prices: List[float],
                                  ma_values: List[float]) -> Tuple[SignalStrength, float]:
        """计算信号强度和置信度"""
        # 计算交叉强度（基于穿越幅度）
        cross_magnitude = abs(price - ma_value) / ma_value

        # 计算趋势强度（基于近期价格变化）
        trend_strength = 0.0
        if cross_index >= 5:
            recent_prices = prices[cross_index-5:cross_index+1]
            price_change = (recent_prices[-1] - recent_prices[0]) / recent_prices[0]
            trend_strength = abs(price_change)

        # 综合计算置信度
        confidence = min(cross_magnitude * 10 + trend_strength * 5, 1.0)

        # 确定信号强度等级
        if confidence >= 0.7:
            strength = SignalStrength.STRONG
        elif confidence >= 0.4:
            strength = SignalStrength.MEDIUM
        else:
            strength = SignalStrength.WEAK

        return strength, confidence

    def generate_single_signal(self,
                              current_price: float,
                              current_timestamp: int,
                              historical_data: Optional[Dict[str, List]] = None) -> Optional[TradingSignal]:
        """
        生成单个时间点的交易信号（用于实时交易）

        Args:
            current_price: 当前价格
            current_timestamp: 当前时间戳
            historical_data: 历史数据字典 {'prices': [], 'timestamps': []}

        Returns:
            交易信号或None
        """
        if not historical_data or len(historical_data.get('prices', [])) < self.config.ma_period:
            return None

        prices = historical_data['prices'] + [current_price]
        timestamps = historical_data['timestamps'] + [current_timestamp]

        # 只检查最新的信号
        signals = self.generate_signals_from_data(prices, timestamps)
        return signals[-1] if signals else None

    def reset(self) -> Any:
        """重置信号生成器状态"""
        self.signal_filter.reset()
        self.ma_calculator.reset_all()

    def get_config(self) -> SignalConfig:
        """获取当前配置"""
        return self.config

    def update_config(self, new_config: SignalConfig) -> Any:
        """更新配置"""
        if not new_config.validate():
            raise ValueError("新配置参数无效")
        self.config = new_config
        self.signal_filter = SignalFilter(new_config)


# 便捷函数
def create_default_signal_generator() -> SignalGenerator:
    """创建默认配置的信号生成器"""
    config = SignalConfig()
    return SignalGenerator(config)


def create_signal_generator(ma_type: str = "SMA",
                           ma_period: int = 20,
                           **kwargs) -> SignalGenerator:
    """创建指定参数的信号生成器"""
    config = SignalConfig(
        ma_type=MAType(ma_type.upper()),
        ma_period=ma_period,
        **kwargs
    )
    return SignalGenerator(config)