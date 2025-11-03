"""
测试用的策略配置类
避免循环导入问题
"""

from dataclasses import dataclass
from typing import List
from enum import Enum


class StrategyType(Enum):
    """策略类型"""
    SINGLE_MA = "single_ma"
    DUAL_MA = "dual_ma"
    MULTI_MA = "multi_ma"


class MAType(Enum):
    """移动平均线类型"""
    SMA = "SMA"
    EMA = "EMA"


@dataclass
class MovingAverageConfig:
    """移动平均线配置"""
    ma_type: MAType
    period: int
    source: str = "close"


@dataclass
class SignalConfig:
    """信号配置"""
    min_cross_percentage: float = 0.001
    confirmation_periods: int = 1
    max_signals_per_day: int = 10
    signal_cooldown: int = 300
    max_position_size: float = 0.1
    stop_loss_pct: float = 0.02
    take_profit_pct: float = 0.05


@dataclass
class RiskConfig:
    """风险配置"""
    max_position_size: float = 0.1
    max_positions: int = 5
    stop_loss_pct: float = 0.02
    take_profit_pct: float = 0.05
    max_drawdown: float = 0.1
    commission_rate: float = 0.001
    slippage_rate: float = 0.0001


@dataclass
class TradingConfig:
    """交易配置"""
    commission_rate: float = 0.001
    slippage_rate: float = 0.0001


@dataclass
class BacktestConfig:
    """回测配置"""
    start_date: str
    end_date: str
    symbols: List[str]
    timeframe: str = "1d"
    initial_capital: float = 100000.0


@dataclass
class StrategyConfig:
    """策略配置"""
    strategy_name: str
    strategy_type: StrategyType
    moving_averages: List[MovingAverageConfig]
    signal_config: SignalConfig
    risk_config: RiskConfig
    trading_config: TradingConfig

    def __post_init__(self):
        """验证配置"""
        if self.strategy_type == StrategyType.SINGLE_MA and len(self.moving_averages) != 1:
            raise ValueError("单均线策略只需要一个移动平均线配置")


def create_test_strategy_config() -> StrategyConfig:
    """创建测试策略配置"""
    return StrategyConfig(
        strategy_name="Test Strategy",
        strategy_type=StrategyType.SINGLE_MA,
        moving_averages=[
            MovingAverageConfig(
                ma_type=MAType.SMA,
                period=5,
                source="close"
            )
        ],
        signal_config=SignalConfig(
            min_cross_percentage=0.005,
            confirmation_periods=1,
            max_signals_per_day=20,
            signal_cooldown=60
        ),
        risk_config=RiskConfig(
            max_position_size=0.3,
            max_positions=3,
            stop_loss_pct=0.02,
            take_profit_pct=0.04,
            max_drawdown=0.1,
            commission_rate=0.001,
            slippage_rate=0.0001
        ),
        trading_config=TradingConfig(
            commission_rate=0.001,
            slippage_rate=0.0001
        )
    )