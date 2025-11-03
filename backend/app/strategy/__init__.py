"""
策略模块
包含策略执行引擎和相关组件
"""

from .strategy_engine import (
    EngineState,
    MarketDataUpdate,
    StrategyState,
    StrategyEngine,
    create_strategy_engine
)

from .indicators import (
    MAType,
    MAResult,
    MovingAverageBase,
    SMA,
    EMA,
    MovingAverageCalculator
)

from .signals import (
    SignalType,
    SignalStrength,
    TradingSignal,
    SignalConfig,
    SignalGenerator
)

from .trading import (
    PositionType,
    OrderType,
    OrderStatus,
    PositionStatus,
    Order,
    Position,
    RiskConfig,
    PositionManager
)

from .config import (
    StrategyConfig,
    StrategyType,
    StrategyConfigManager
)

__all__ = [
    # Engine
    'EngineState',
    'MarketDataUpdate',
    'StrategyState',
    'StrategyEngine',
    'create_strategy_engine',

    # Indicators
    'MAType',
    'MAResult',
    'MovingAverageBase',
    'SMA',
    'EMA',
    'MovingAverageCalculator',

    # Signals
    'SignalType',
    'SignalStrength',
    'TradingSignal',
    'SignalConfig',
    'SignalGenerator',

    # Trading
    'PositionType',
    'OrderType',
    'OrderStatus',
    'PositionStatus',
    'Order',
    'Position',
    'RiskConfig',
    'PositionManager',

    # Config
    'StrategyConfig',
    'StrategyType',
    'StrategyConfigManager'
]