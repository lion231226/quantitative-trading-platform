"""
收益计算引擎
提供多种收益率计算方法，支持单期和累计收益计算
"""

from typing import List, Union, Optional, Any
from enum import Enum
import numpy as np
import pandas as pd
from dataclasses import dataclass
from datetime import datetime
import structlog

logger = structlog.get_logger()


class ReturnType(Enum):
    """收益计算类型"""
    SIMPLE = "simple"  # 简单收益率
    LOG = "log"       # 对数收益率


@dataclass
class ReturnCalculationConfig:
    """收益计算配置"""
    return_type: ReturnType = ReturnType.SIMPLE
    benchmark_returns: Optional[np.ndarray] = None  # 基准收益率（用于超额收益计算）
    include_costs: bool = True  # 是否包含交易成本
    risk_free_rate: float = 0.02  # 无风险利率（年化）
    trading_days: int = 252  # 年交易天数


class ReturnCalculator:
    """收益计算器"""

    def __init__(self, config: Optional[ReturnCalculationConfig] = None) -> None:
        """
        初始化收益计算器

        Args:
            config: 收益计算配置
        """
        self.config = config or ReturnCalculationConfig()
        logger.info("收益计算器初始化", config=self.config.return_type.value)

    def calculate_single_period_returns(
        self,
        prices: Union[List[float], np.ndarray[Any], pd.Series],
        periods: int = 1
    ) -> np.ndarray[Any]:
        """
        计算单期收益率

        Args:
            prices: 价格序列
            periods: 计算周期（默认为1期）

        Returns:
            收益率数组
        """
        prices = np.asarray(prices, dtype=np.float64)

        if len(prices) < periods + 1:
            raise ValueError(f"价格序列长度不足，至少需要 {periods + 1} 个数据点")

        if self.config.return_type == ReturnType.SIMPLE:
            # 简单收益率: (P_t - P_{t-1}) / P_{t-1}
            returns = (prices[periods:] - prices[:-periods]) / prices[:-periods]
        elif self.config.return_type == ReturnType.LOG:
            # 对数收益率: ln(P_t / P_{t-1})
            returns = np.log(prices[periods:] / prices[:-periods])
        else:
            raise ValueError(f"不支持的收益率类型: {self.config.return_type}")

        logger.debug("计算单期收益率",
                    return_type=self.config.return_type.value,
                    data_points=len(returns),
                    periods=periods)

        return returns

    def calculate_cumulative_returns(self, returns: Union[List[float], np.ndarray]) -> np.ndarray[Any]:
        """
        计算累计收益率

        Args:
            returns: 收益率序列

        Returns:
            累计收益率数组
        """
        returns = np.asarray(returns, dtype=np.float64)

        if len(returns) == 0:
            return np.array([])

        if self.config.return_type == ReturnType.SIMPLE:
            # 简单收益率累计: (1 + r1) * (1 + r2) * ... * (1 + rn) - 1
            cumulative = np.cumprod(1 + returns) - 1
        elif self.config.return_type == ReturnType.LOG:
            # 对数收益率累计: exp(sum(log_returns)) - 1
            cumulative = np.exp(np.cumsum(returns)) - 1
        else:
            raise ValueError(f"不支持的收益率类型: {self.config.return_type}")

        logger.debug("计算累计收益率",
                    return_type=self.config.return_type.value,
                    final_cumulative_return=cumulative[-1] if len(cumulative) > 0 else 0)

        return cumulative

    def calculate_position_values(
        self,
        signals: Union[List[int], np.ndarray],
        prices: Union[List[float], np.ndarray],
        initial_capital: float = 100000,
        position_size: float = 1.0
    ) -> np.ndarray[Any]:
        """
        基于策略信号计算仓位价值

        Args:
            signals: 交易信号序列 (1: 多头, -1: 空头, 0: 无仓位)
            prices: 价格序列
            initial_capital: 初始资金
            position_size: 仓位大小（比例）

        Returns:
            仓位价值序列
        """
        signals = np.asarray(signals, dtype=np.int32)
        prices = np.asarray(prices, dtype=np.float64)

        if len(signals) != len(prices):
            raise ValueError("信号序列和价格序列长度必须相同")

        if len(signals) == 0:
            return np.array([])

        # 确保价格都大于0
        if np.any(prices <= 0):
            raise ValueError("价格必须都大于0")

        # 计算仓位价值
        position_values = np.zeros_like(prices, dtype=np.float64)
        position_values[0] = initial_capital

        current_position = 0  # 当前持仓数量（正数为多头，负数为空头）
        cash = initial_capital

        for i in range(1, len(prices)):
            # 检查信号变化
            if signals[i] != signals[i-1]:
                # 需要平仓
                if current_position != 0:
                    if current_position > 0:  # 平多头仓
                        cash += current_position * prices[i]
                    else:  # 平空头仓
                        cash += current_position * prices[i]  # current_position为负数
                    current_position = 0

                # 开新仓
                if signals[i] != 0:
                    # 计算要买的数量
                    cash_for_position = cash * position_size
                    if signals[i] > 0:  # 开多头
                        current_position = cash_for_position / prices[i]
                        cash -= cash_for_position
                    else:  # 开空头
                        # 空头：卖出借入的股票，获得现金
                        shares_to_short = cash_for_position / prices[i]
                        current_position = -shares_to_short
                        cash += cash_for_position  # 空头获得现金

            # 更新持仓价值（现金 + 持仓价值）
            if current_position > 0:  # 多头持仓
                position_value = current_position * prices[i]
            elif current_position < 0:  # 空头持仓
                # 空头持仓价值 = 初始卖出金额 - 当前买回成本
                position_value = cash + abs(current_position) * prices[i]
            else:  # 无持仓
                position_value = cash

            position_values[i] = position_value

        logger.debug("计算仓位价值",
                    initial_capital=initial_capital,
                    final_value=position_values[-1],
                    total_return=(position_values[-1] - initial_capital) / initial_capital)

        return position_values

    def calculate_annualized_return(self, returns: Union[List[float], np.ndarray]) -> float:
        """
        计算年化收益率

        Args:
            returns: 收益率序列

        Returns:
            年化收益率
        """
        returns = np.asarray(returns, dtype=np.float64)

        if len(returns) == 0:
            return 0.0

        # 计算累计收益率
        cumulative_return = self.calculate_cumulative_returns(returns)
        if len(cumulative_return) == 0:
            return 0.0

        total_return = cumulative_return[-1]

        # 年化收益率 = (1 + total_return)^(252/n) - 1
        years = len(returns) / self.config.trading_days
        annualized_return = (1 + total_return) ** (1 / years) - 1

        logger.debug("计算年化收益率",
                    total_return=total_return,
                    periods=len(returns),
                    years=years,
                    annualized_return=annualized_return)

        return annualized_return

    def calculate_excess_returns(
        self,
        returns: Union[List[float], np.ndarray],
        benchmark_returns: Union[List[float], np.ndarray]
    ) -> np.ndarray[Any]:
        """
        计算超额收益率

        Args:
            returns: 策略收益率序列
            benchmark_returns: 基准收益率序列

        Returns:
            超额收益率序列
        """
        returns = np.asarray(returns, dtype=np.float64)
        benchmark_returns = np.asarray(benchmark_returns, dtype=np.float64)

        if len(returns) != len(benchmark_returns):
            raise ValueError("策略收益率和基准收益率序列长度必须相同")

        if len(returns) == 0:
            return np.array([])

        excess_returns = returns - benchmark_returns

        logger.debug("计算超额收益率",
                    strategy_return=np.mean(returns),
                    benchmark_return=np.mean(benchmark_returns),
                    excess_return=np.mean(excess_returns))

        return excess_returns


def create_return_calculator(config: ReturnCalculationConfig = None) -> ReturnCalculator:
    """
    创建收益计算器的工厂函数

    Args:
        config: 收益计算配置

    Returns:
        收益计算器实例
    """
    return ReturnCalculator(config)