"""
策略配置管理模块
"""

from .strategy_config import (
    StrategyType,
    MovingAverageConfig,
    StrategyConfig,
    StrategyConfigManager,
    create_single_ma_config,
    get_default_strategy_configs
)

__all__ = [
    'StrategyType',
    'MovingAverageConfig',
    'StrategyConfig',
    'StrategyConfigManager',
    'create_single_ma_config',
    'get_default_strategy_configs'
]