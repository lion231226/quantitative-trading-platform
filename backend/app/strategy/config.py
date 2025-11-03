"""
策略配置模块
提供策略参数配置、验证和管理功能
"""

from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass, field
from enum import Enum
import json
from pathlib import Path
import structlog

from ..indicators import MAType
from .signals import SignalConfig
from .trading import RiskConfig

logger = structlog.get_logger()


class StrategyType(Enum):
    """策略类型枚举"""
    SINGLE_MA = "SINGLE_MA"           # 单均线策略
    DUAL_MA = "DUAL_MA"               # 双均线策略
    MULTI_MA = "MULTI_MA"             # 多均线策略
    MEAN_REVERSION = "MEAN_REVERSION" # 均值回归策略
    MOMENTUM = "MOMENTUM"             # 动量策略


@dataclass
class MAConfig:
    """移动平均线配置"""
    ma_type: MAType = MAType.SMA
    period: int = 20
    enabled: bool = True
    weight: float = 1.0  # 权重（用于多均线策略）

    def validate(self) -> tuple[bool, List[str]]:
        """验证配置"""
        errors = []
        if self.period <= 0:
            errors.append("移动平均线周期必须大于0")
        if self.period > 1000:
            errors.append("移动平均线周期不能超过1000")
        if not 0 <= self.weight <= 1:
            errors.append("权重必须在0-1之间")
        return len(errors) == 0, errors


@dataclass
class SignalParameterConfig:
    """信号参数配置"""
    min_cross_percentage: float = 0.001      # 最小穿越百分比
    confirmation_periods: int = 1            # 确认周期数
    volume_threshold: Optional[float] = None # 成交量阈值
    min_price_change: float = 0.0005        # 最小价格变化
    max_signals_per_day: int = 10           # 每日最大信号数
    signal_cooldown: int = 300              # 信号冷却时间（秒）

    def validate(self) -> tuple[bool, List[str]]:
        """验证配置"""
        errors = []
        if self.min_cross_percentage < 0:
            errors.append("最小穿越百分比不能为负数")
        if self.confirmation_periods < 1:
            errors.append("确认周期数必须大于0")
        if self.min_price_change < 0:
            errors.append("最小价格变化不能为负数")
        if self.max_signals_per_day <= 0:
            errors.append("每日最大信号数必须大于0")
        if self.signal_cooldown < 0:
            errors.append("信号冷却时间不能为负数")
        return len(errors) == 0, errors


@dataclass
class RiskParameterConfig:
    """风险参数配置"""
    max_position_size: float = 1.0          # 最大仓位（占总资金比例）
    max_positions: int = 5                  # 最大持仓数量
    stop_loss_pct: float = 0.02             # 止损百分比
    take_profit_pct: float = 0.05           # 止盈百分比
    max_drawdown_pct: float = 0.10          # 最大回撤百分比
    max_loss_per_trade: float = 0.02        # 单笔最大亏损比例
    commission_rate: float = 0.001          # 手续费率
    slippage_rate: float = 0.0001           # 滑点率

    def validate(self) -> tuple[bool, List[str]]:
        """验证配置"""
        errors = []
        if not 0 < self.max_position_size <= 1:
            errors.append("最大仓位必须在0-1之间")
        if self.max_positions <= 0:
            errors.append("最大持仓数量必须大于0")
        if not 0 < self.stop_loss_pct < 1:
            errors.append("止损百分比必须在0-1之间")
        if not 0 < self.take_profit_pct < 1:
            errors.append("止盈百分比必须在0-1之间")
        if not 0 < self.max_drawdown_pct < 1:
            errors.append("最大回撤百分比必须在0-1之间")
        if not 0 < self.max_loss_per_trade < 1:
            errors.append("单笔最大亏损比例必须在0-1之间")
        if not 0 <= self.commission_rate < 1:
            errors.append("手续费率必须在0-1之间")
        if not 0 <= self.slippage_rate < 1:
            errors.append("滑点率必须在0-1之间")
        return len(errors) == 0, errors


@dataclass
class BacktestConfig:
    """回测配置"""
    initial_capital: float = 100000.0       # 初始资金
    start_date: str = ""                    # 开始日期
    end_date: str = ""                      # 结束日期
    data_frequency: str = "1d"              # 数据频率
    benchmark_symbol: Optional[str] = None  # 基准标的

    def validate(self) -> tuple[bool, List[str]]:
        """验证配置"""
        errors = []
        if self.initial_capital <= 0:
            errors.append("初始资金必须大于0")
        if not self.start_date:
            errors.append("开始日期不能为空")
        if not self.end_date:
            errors.append("结束日期不能为空")
        if self.start_date >= self.end_date:
            errors.append("开始日期必须早于结束日期")
        if self.data_frequency not in ["1m", "5m", "15m", "30m", "1h", "1d", "1w", "1M"]:
            errors.append("数据频率无效")
        return len(errors) == 0, errors


@dataclass
class StrategyConfig:
    """策略配置"""
    # 基础信息
    strategy_name: str = "默认策略"
    strategy_type: StrategyType = StrategyType.SINGLE_MA
    description: str = ""
    version: str = "1.0.0"

    # 移动平均线配置
    ma_configs: List[MAConfig] = field(default_factory=list)

    # 信号配置
    signal_config: SignalParameterConfig = field(default_factory=SignalParameterConfig)

    # 风险配置
    risk_config: RiskParameterConfig = field(default_factory=RiskParameterConfig)

    # 回测配置
    backtest_config: BacktestConfig = field(default_factory=BacktestConfig)

    # 其他参数
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """初始化后处理"""
        # 如果没有MA配置，添加默认配置
        if not self.ma_configs:
            self.ma_configs = [
                MAConfig(ma_type=MAType.SMA, period=20, enabled=True)
            ]

    def validate(self) -> tuple[bool, List[str]]:
        """验证整个策略配置"""
        all_errors = []

        # 验证基础信息
        if not self.strategy_name:
            all_errors.append("策略名称不能为空")
        if not self.description:
            all_errors.append("策略描述不能为空")

        # 验证MA配置
        if not self.ma_configs:
            all_errors.append("至少需要一个移动平均线配置")
        else:
            for i, ma_config in enumerate(self.ma_configs):
                is_valid, errors = ma_config.validate()
                if not is_valid:
                    all_errors.extend([f"MA配置{i+1}: {error}" for error in errors])

        # 验证信号配置
        is_valid, errors = self.signal_config.validate()
        if not is_valid:
            all_errors.extend([f"信号配置: {error}" for error in errors])

        # 验证风险配置
        is_valid, errors = self.risk_config.validate()
        if not is_valid:
            all_errors.extend([f"风险配置: {error}" for error in errors])

        # 验证回测配置
        is_valid, errors = self.backtest_config.validate()
        if not is_valid:
            all_errors.extend([f"回测配置: {error}" for error in errors])

        return len(all_errors) == 0, all_errors

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'strategy_name': self.strategy_name,
            'strategy_type': self.strategy_type.value,
            'description': self.description,
            'version': self.version,
            'ma_configs': [
                {
                    'ma_type': ma.ma_type.value,
                    'period': ma.period,
                    'enabled': ma.enabled,
                    'weight': ma.weight
                } for ma in self.ma_configs
            ],
            'signal_config': {
                'min_cross_percentage': self.signal_config.min_cross_percentage,
                'confirmation_periods': self.signal_config.confirmation_periods,
                'volume_threshold': self.signal_config.volume_threshold,
                'min_price_change': self.signal_config.min_price_change,
                'max_signals_per_day': self.signal_config.max_signals_per_day,
                'signal_cooldown': self.signal_config.signal_cooldown
            },
            'risk_config': {
                'max_position_size': self.risk_config.max_position_size,
                'max_positions': self.risk_config.max_positions,
                'stop_loss_pct': self.risk_config.stop_loss_pct,
                'take_profit_pct': self.risk_config.take_profit_pct,
                'max_drawdown_pct': self.risk_config.max_drawdown_pct,
                'max_loss_per_trade': self.risk_config.max_loss_per_trade,
                'commission_rate': self.risk_config.commission_rate,
                'slippage_rate': self.risk_config.slippage_rate
            },
            'backtest_config': {
                'initial_capital': self.backtest_config.initial_capital,
                'start_date': self.backtest_config.start_date,
                'end_date': self.backtest_config.end_date,
                'data_frequency': self.backtest_config.data_frequency,
                'benchmark_symbol': self.backtest_config.benchmark_symbol
            },
            'enabled': self.enabled,
            'metadata': self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StrategyConfig':
        """从字典创建配置"""
        # 转换MA配置
        ma_configs = []
        for ma_data in data.get('ma_configs', []):
            ma_config = MAConfig(
                ma_type=MAType(ma_data['ma_type']),
                period=ma_data['period'],
                enabled=ma_data.get('enabled', True),
                weight=ma_data.get('weight', 1.0)
            )
            ma_configs.append(ma_config)

        # 转换信号配置
        signal_data = data.get('signal_config', {})
        signal_config = SignalParameterConfig(
            min_cross_percentage=signal_data.get('min_cross_percentage', 0.001),
            confirmation_periods=signal_data.get('confirmation_periods', 1),
            volume_threshold=signal_data.get('volume_threshold'),
            min_price_change=signal_data.get('min_price_change', 0.0005),
            max_signals_per_day=signal_data.get('max_signals_per_day', 10),
            signal_cooldown=signal_data.get('signal_cooldown', 300)
        )

        # 转换风险配置
        risk_data = data.get('risk_config', {})
        risk_config = RiskParameterConfig(
            max_position_size=risk_data.get('max_position_size', 1.0),
            max_positions=risk_data.get('max_positions', 5),
            stop_loss_pct=risk_data.get('stop_loss_pct', 0.02),
            take_profit_pct=risk_data.get('take_profit_pct', 0.05),
            max_drawdown_pct=risk_data.get('max_drawdown_pct', 0.10),
            max_loss_per_trade=risk_data.get('max_loss_per_trade', 0.02),
            commission_rate=risk_data.get('commission_rate', 0.001),
            slippage_rate=risk_data.get('slippage_rate', 0.0001)
        )

        # 转换回测配置
        backtest_data = data.get('backtest_config', {})
        backtest_config = BacktestConfig(
            initial_capital=backtest_data.get('initial_capital', 100000.0),
            start_date=backtest_data.get('start_date', ''),
            end_date=backtest_data.get('end_date', ''),
            data_frequency=backtest_data.get('data_frequency', '1d'),
            benchmark_symbol=backtest_data.get('benchmark_symbol')
        )

        return cls(
            strategy_name=data.get('strategy_name', '默认策略'),
            strategy_type=StrategyType(data.get('strategy_type', 'SINGLE_MA')),
            description=data.get('description', ''),
            version=data.get('version', '1.0.0'),
            ma_configs=ma_configs,
            signal_config=signal_config,
            risk_config=risk_config,
            backtest_config=backtest_config,
            enabled=data.get('enabled', True),
            metadata=data.get('metadata', {})
        )

    def save_to_file(self, file_path: str) -> bool:
        """保存配置到文件"""
        try:
            config_dict = self.to_dict()
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(config_dict, f, indent=2, ensure_ascii=False)
            logger.info("策略配置已保存", file_path=file_path)
            return True
        except Exception as e:
            logger.error("保存策略配置失败", error=str(e))
            return False

    @classmethod
    def load_from_file(cls, file_path: str) -> Optional['StrategyConfig']:
        """从文件加载配置"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                config_dict = json.load(f)
            config = cls.from_dict(config_dict)
            logger.info("策略配置已加载", file_path=file_path)
            return config
        except Exception as e:
            logger.error("加载策略配置失败", error=str(e))
            return None

    def create_signal_config(self) -> SignalConfig:
        """创建信号配置对象"""
        return SignalConfig(
            ma_type=self.ma_configs[0].ma_type if self.ma_configs else MAType.SMA,
            ma_period=self.ma_configs[0].period if self.ma_configs else 20,
            min_cross_percentage=self.signal_config.min_cross_percentage,
            confirmation_periods=self.signal_config.confirmation_periods,
            volume_threshold=self.signal_config.volume_threshold,
            min_price_change=self.signal_config.min_price_change,
            max_signals_per_day=self.signal_config.max_signals_per_day,
            signal_cooldown=self.signal_config.signal_cooldown,
            max_position_size=self.risk_config.max_position_size,
            stop_loss_pct=self.risk_config.stop_loss_pct,
            take_profit_pct=self.risk_config.take_profit_pct
        )

    def create_risk_config(self) -> RiskConfig:
        """创建风险配置对象"""
        return RiskConfig(
            max_position_size=self.risk_config.max_position_size,
            max_positions=self.risk_config.max_positions,
            stop_loss_pct=self.risk_config.stop_loss_pct,
            take_profit_pct=self.risk_config.take_profit_pct,
            max_drawdown_pct=self.risk_config.max_drawdown_pct,
            max_loss_per_trade=self.risk_config.max_loss_per_trade,
            commission_rate=self.risk_config.commission_rate,
            slippage_rate=self.risk_config.slippage_rate
        )


# 预设策略模板
class StrategyPresets:
    """策略预设模板"""

    @staticmethod
    def conservative_sma() -> StrategyConfig:
        """保守型SMA策略"""
        return StrategyConfig(
            strategy_name="保守型SMA策略",
            strategy_type=StrategyType.SINGLE_MA,
            description="使用50日SMA的保守策略，适合风险厌恶投资者",
            ma_configs=[
                MAConfig(ma_type=MAType.SMA, period=50, enabled=True)
            ],
            signal_config=SignalParameterConfig(
                min_cross_percentage=0.002,
                confirmation_periods=2,
                max_signals_per_day=5
            ),
            risk_config=RiskParameterConfig(
                max_position_size=0.3,
                stop_loss_pct=0.015,
                take_profit_pct=0.03
            )
        )

    @staticmethod
    def aggressive_ema() -> StrategyConfig:
        """激进型EMA策略"""
        return StrategyConfig(
            strategy_name="激进型EMA策略",
            strategy_type=StrategyType.SINGLE_MA,
            description="使用12日EMA的激进策略，追求高收益",
            ma_configs=[
                MAConfig(ma_type=MAType.EMA, period=12, enabled=True)
            ],
            signal_config=SignalParameterConfig(
                min_cross_percentage=0.0005,
                confirmation_periods=1,
                max_signals_per_day=15
            ),
            risk_config=RiskParameterConfig(
                max_position_size=0.8,
                stop_loss_pct=0.025,
                take_profit_pct=0.08
            )
        )

    @staticmethod
    def dual_ma_crossover() -> StrategyConfig:
        """双均线交叉策略"""
        return StrategyConfig(
            strategy_name="双均线交叉策略",
            strategy_type=StrategyType.DUAL_MA,
            description="使用10日和30日双均线的经典交叉策略",
            ma_configs=[
                MAConfig(ma_type=MAType.EMA, period=10, enabled=True, weight=0.6),
                MAConfig(ma_type=MAType.EMA, period=30, enabled=True, weight=0.4)
            ],
            signal_config=SignalParameterConfig(
                min_cross_percentage=0.001,
                confirmation_periods=1,
                max_signals_per_day=8
            ),
            risk_config=RiskParameterConfig(
                max_position_size=0.6,
                stop_loss_pct=0.02,
                take_profit_pct=0.06
            )
        )


def create_default_strategy_config() -> StrategyConfig:
    """创建默认策略配置"""
    return StrategyConfig(
        strategy_name="默认单均线策略",
        strategy_type=StrategyType.SINGLE_MA,
        description="使用20日SMA的默认策略配置",
        ma_configs=[
            MAConfig(ma_type=MAType.SMA, period=20, enabled=True)
        ]
    )