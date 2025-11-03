"""
交易信号模块
包含交易信号生成、过滤和管理功能
"""

from .signal_generator import (
    SignalType,
    SignalStrength,
    TradingSignal,
    SignalConfig,
    CrossDetector,
    SignalFilter,
    SignalGenerator,
    create_default_signal_generator,
    create_signal_generator
)

__all__ = [
    'SignalType',
    'SignalStrength',
    'TradingSignal',
    'SignalConfig',
    'CrossDetector',
    'SignalFilter',
    'SignalGenerator',
    'create_default_signal_generator',
    'create_signal_generator'
]