"""
移动平均线计算引擎
支持简单移动平均线（SMA）和指数移动平均线（EMA）
"""

from typing import List, Optional, Union, Dict, Any
from dataclasses import dataclass
from enum import Enum
import numpy as np
import pandas as pd
from abc import ABC, abstractmethod
import structlog
import time

logger = structlog.get_logger()


class MAType(Enum):
    """移动平均线类型枚举"""
    SMA = "SMA"  # 简单移动平均线
    EMA = "EMA"  # 指数移动平均线


@dataclass
class MAResult:
    """移动平均线计算结果"""
    values: List[float]  # 移动平均线值
    timestamps: List[int]  # 时间戳
    ma_type: MAType  # 移动平均线类型
    period: int  # 计算周期
    valid_count: int  # 有效值数量

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'values': self.values,
            'timestamps': self.timestamps,
            'ma_type': self.ma_type.value,
            'period': self.period,
            'valid_count': self.valid_count
        }

    def to_dataframe(self) -> pd.DataFrame:
        """转换为Pandas DataFrame"""
        df = pd.DataFrame({
            'timestamp': pd.to_datetime(self.timestamps, unit='s'),
            'value': self.values
        })
        df['ma_type'] = self.ma_type.value
        df['period'] = self.period
        return df


class MovingAverageBase(ABC):
    """移动平均线基类"""

    def __init__(self, period: int, name: Optional[str] = None) -> None:
        """
        初始化移动平均线计算器

        Args:
            period: 计算周期
            name: 指标名称
        """
        if period <= 0:
            raise ValueError("计算周期必须大于0")

        self.period = period
        self.name = name or f"{self.__class__.__name__}_{period}"
        self._values: List[float] = []
        self._timestamps: List[int] = []
        self._is_initialized = False

    def calculate_single(self, price: float) -> Optional[float]:
        """
        计算单个移动平均线值

        Args:
            price: 价格数据

        Returns:
            移动平均线值（如果数据不足返回None）
        """
        ma_value = self._calculate_single_impl(price)
        if ma_value is not None:
            self._values.append(ma_value)
            self._timestamps.append(int(time.time()))
            if not self._is_initialized:
                self._is_initialized = True
        return ma_value

    @abstractmethod
    def _calculate_single_impl(self, price: float) -> Optional[float]:
        """
        计算单个移动平均线值的实际实现（由子类实现）

        Args:
            price: 价格数据

        Returns:
            移动平均线值（如果数据不足返回None）
        """
        pass

    def calculate_batch(self, prices: List[float], timestamps: List[int]) -> MAResult:
        """
        批量计算移动平均线

        Args:
            prices: 价格列表
            timestamps: 时间戳列表

        Returns:
            移动平均线计算结果
        """
        if len(prices) != len(timestamps):
            raise ValueError("价格和时间戳列表长度不一致")

        if not prices:
            return MAResult(
                values=[],
                timestamps=[],
                ma_type=self.get_ma_type(),
                period=self.period,
                valid_count=0
            )

        # 重置内部状态
        self.reset()

        # 逐个计算移动平均线值
        ma_values = []
        ma_timestamps = []

        for price, timestamp in zip(prices, timestamps):
            ma_value = self.calculate_single(price)
            if ma_value is not None:
                ma_values.append(ma_value)
                ma_timestamps.append(timestamp)

        return MAResult(
            values=ma_values,
            timestamps=ma_timestamps,
            ma_type=self.get_ma_type(),
            period=self.period,
            valid_count=len(ma_values)
        )

    def update(self, price: float, timestamp: int) -> Optional[float]:
        """
        更新移动平均线计算

        Args:
            price: 新价格
            timestamp: 时间戳

        Returns:
            当前的移动平均线值（如果数据不足返回None）
        """
        ma_value = self.calculate_single(price)
        if ma_value is not None:
            self._values.append(ma_value)
            self._timestamps.append(timestamp)
        return ma_value

    def reset(self) -> None:
        """重置计算器状态"""
        self._values.clear()
        self._timestamps.clear()
        self._reset_internal_state()
        self._is_initialized = False

    @abstractmethod
    def _reset_internal_state(self) -> None:
        """重置内部状态（由子类实现）"""
        pass

    @abstractmethod
    def get_ma_type(self) -> MAType:
        """获取移动平均线类型"""
        pass

    @property
    def is_initialized(self) -> bool:
        """是否已初始化（有足够的数据进行计算）"""
        return self._is_initialized

    @property
    def current_value(self) -> Optional[float]:
        """当前移动平均线值"""
        if self._values:
            return self._values[-1]
        return None

    @property
    def values(self) -> List[float]:
        """获取所有计算出的值"""
        return self._values.copy()

    @property
    def timestamps(self) -> List[int]:
        """获取所有时间戳"""
        return self._timestamps.copy()


class SMA(MovingAverageBase):
    """简单移动平均线（Simple Moving Average）"""

    def __init__(self, period: int, name: Optional[str] = None) -> None:
        super().__init__(period, name)
        self._price_buffer: List[float] = []

    def _calculate_single_impl(self, price: float) -> Optional[float]:
        """计算SMA值"""
        self._price_buffer.append(price)

        # 保持缓冲区大小
        if len(self._price_buffer) > self.period:
            self._price_buffer.pop(0)

        # 计算SMA
        if len(self._price_buffer) == self.period:
            return sum(self._price_buffer) / self.period

        return None

    def _reset_internal_state(self) -> None:
        """重置内部状态"""
        self._price_buffer.clear()

    def get_ma_type(self) -> MAType:
        """获取移动平均线类型"""
        return MAType.SMA


class EMA(MovingAverageBase):
    """指数移动平均线（Exponential Moving Average）"""

    def __init__(self, period: int, name: Optional[str] = None) -> None:
        super().__init__(period, name)
        self._multiplier = 2.0 / (period + 1)  # 平滑系数
        self._previous_ema: Optional[float] = None
        self._first_value_calculated = False

    def _calculate_single_impl(self, price: float) -> Optional[float]:
        """计算EMA值"""
        if not self._first_value_calculated:
            # 第一个EMA值使用SMA
            self._previous_ema = price
            self._first_value_calculated = True
            return price

        if self._previous_ema is not None:
            # EMA计算公式: EMA = (Price × K) + (Previous EMA × (1 − K))
            current_ema = (price * self._multiplier) + (self._previous_ema * (1 - self._multiplier))
            self._previous_ema = current_ema
            return current_ema

        return None

    def _reset_internal_state(self) -> None:
        """重置内部状态"""
        self._previous_ema = None
        self._first_value_calculated = False

    def get_ma_type(self) -> MAType:
        """获取移动平均线类型"""
        return MAType.EMA


class MovingAverageCalculator:
    """移动平均线计算器"""

    def __init__(self) -> None:
        self._indicators: Dict[str, MovingAverageBase] = {}

    def create_indicator(self,
                        ma_type: Union[str, MAType],
                        period: int,
                        name: Optional[str] = None) -> MovingAverageBase:
        """
        创建移动平均线指标

        Args:
            ma_type: 移动平均线类型
            period: 计算周期
            name: 指标名称

        Returns:
            移动平均线指标实例
        """
        if isinstance(ma_type, str):
            ma_type = MAType(ma_type.upper())

        indicator_name = name or f"{ma_type.value}_{period}"
        indicator: MovingAverageBase

        if ma_type == MAType.SMA:
            indicator = SMA(period, indicator_name)
        elif ma_type == MAType.EMA:
            indicator = EMA(period, indicator_name)
        else:
            raise ValueError(f"不支持的移动平均线类型: {ma_type}")

        self._indicators[indicator_name] = indicator
        return indicator

    def get_indicator(self, name: str) -> Optional[MovingAverageBase]:
        """获取指定名称的指标"""
        return self._indicators.get(name)

    def remove_indicator(self, name: str) -> bool:
        """移除指定名称的指标"""
        if name in self._indicators:
            del self._indicators[name]
            return True
        return False

    def list_indicators(self) -> List[str]:
        """列出所有指标名称"""
        return list(self._indicators.keys())

    def reset_all(self) -> None:
        """重置所有指标"""
        for indicator in self._indicators.values():
            indicator.reset()

    def calculate_from_dataframe(self,
                                df: pd.DataFrame,
                                price_column: str = 'close',
                                ma_type: Union[str, MAType] = MAType.SMA,
                                period: int = 20) -> MAResult:
        """
        从DataFrame计算移动平均线

        Args:
            df: 数据DataFrame
            price_column: 价格列名
            ma_type: 移动平均线类型
            period: 计算周期

        Returns:
            移动平均线计算结果
        """
        if price_column not in df.columns:
            raise ValueError(f"DataFrame中不存在列: {price_column}")

        prices = df[price_column].tolist()
        timestamps = df.index.astype(np.int64) // 10**9  # 转换为秒时间戳

        indicator = self.create_indicator(ma_type, period)
        return indicator.calculate_batch(prices, timestamps)

    def calculate_batch(self,
                       prices: List[float],
                       timestamps: List[int],
                       ma_type: Union[str, MAType] = MAType.SMA,
                       period: int = 20) -> MAResult:
        """
        批量计算移动平均线

        Args:
            prices: 价格列表
            timestamps: 时间戳列表
            ma_type: 移动平均线类型
            period: 计算周期

        Returns:
            移动平均线计算结果
        """
        if isinstance(ma_type, str):
            ma_type = MAType(ma_type.upper())

        # 创建临时指标进行计算
        indicator: MovingAverageBase
        if ma_type == MAType.SMA:
            indicator = SMA(period)
        elif ma_type == MAType.EMA:
            indicator = EMA(period)
        else:
            raise ValueError(f"不支持的移动平均线类型: {ma_type}")

        return indicator.calculate_batch(prices, timestamps)

    def calculate_cross_signals(self,
                               prices: List[float],
                               timestamps: List[int],
                               ma_type: Union[str, MAType] = MAType.SMA,
                               period: int = 20) -> Dict[str, List[int]]:
        """
        计算价格与移动平均线的交叉信号

        Args:
            prices: 价格列表
            timestamps: 时间戳列表
            ma_type: 移动平均线类型
            period: 计算周期

        Returns:
            交叉信号字典 {'golden_cross': [时间戳列表], 'death_cross': [时间戳列表]}
        """
        ma_result = self.calculate_batch(prices, timestamps, ma_type, period)

        if len(ma_result.values) < 2:
            return {'golden_cross': [], 'death_cross': []}

        golden_crosses = []
        death_crosses = []

        # 获取对应的价格数据（需要与MA值对齐）
        start_idx = len(prices) - len(ma_result.values)
        aligned_prices = prices[start_idx:]

        for i in range(1, len(ma_result.values)):
            prev_price = aligned_prices[i-1]
            curr_price = aligned_prices[i]
            prev_ma = ma_result.values[i-1]
            curr_ma = ma_result.values[i]

            # 金叉：价格从下方穿越移动平均线
            if prev_price <= prev_ma and curr_price > curr_ma:
                golden_crosses.append(ma_result.timestamps[i])

            # 死叉：价格从上方穿越移动平均线
            elif prev_price >= prev_ma and curr_price < curr_ma:
                death_crosses.append(ma_result.timestamps[i])

        return {
            'golden_cross': golden_crosses,
            'death_cross': death_crosses
        }


# 便捷函数
def create_sma(period: int, name: Optional[str] = None) -> SMA:
    """创建SMA指标"""
    return SMA(period, name)


def create_ema(period: int, name: Optional[str] = None) -> EMA:
    """创建EMA指标"""
    return EMA(period, name)


def calculate_sma(prices: List[float], period: int) -> List[float]:
    """快速计算SMA值列表"""
    sma = SMA(period)
    result = []
    for price in prices:
        value = sma.calculate_single(price)
        if value is not None:
            result.append(value)
    return result


def calculate_ema(prices: List[float], period: int) -> List[float]:
    """快速计算EMA值列表"""
    ema = EMA(period)
    result = []
    for price in prices:
        value = ema.calculate_single(price)
        if value is not None:
            result.append(value)
    return result