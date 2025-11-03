"""
策略回测模块
"""

from .backtest_config import (
    BacktestConfig,
    BacktestPresets,
    create_backtest_config,
    get_recent_months_config,
    get_year_to_date_config
)
from .backtest_engine import (
    BacktestEngine,
    BacktestState,
    BacktestResult,
    TradeRecord,
    run_backtest
)

__all__ = [
    # 配置相关
    'BacktestConfig',
    'BacktestPresets',
    'create_backtest_config',
    'get_recent_months_config',
    'get_year_to_date_config',

    # 回测引擎
    'BacktestEngine',
    'BacktestState',
    'BacktestResult',
    'TradeRecord',
    'run_backtest'
]