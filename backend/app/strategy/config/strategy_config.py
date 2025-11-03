"""
策略配置管理
实现灵活的策略参数配置接口
"""

from typing import Dict, Any, Optional, Union, List
from dataclasses import dataclass, field, asdict
from enum import Enum
import json
import yaml
from pathlib import Path
import structlog

from ..indicators import MAType
from ..signals import SignalConfig
from ..trading import RiskConfig

logger = structlog.get_logger()


class StrategyType(Enum):
    """策略类型枚举"""
    SINGLE_MA = "single_ma"              # 单均线策略
    DUAL_MA = "dual_ma"                  # 双均线策略
    MULTI_MA = "multi_ma"                # 多均线策略
    CUSTOM = "custom"                    # 自定义策略


@dataclass
class MovingAverageConfig:
    """移动平均线配置"""
    ma_type: MAType = MAType.SMA
    period: int = 20
    enabled: bool = True

    def validate(self) -> bool:
        """验证配置"""
        if self.period <= 0:
            return False
        return True


@dataclass
class StrategyConfig:
    """策略配置数据类"""
    # 基础配置
    strategy_name: str
    strategy_type: StrategyType
    description: str = ""
    version: str = "1.0.0"
    enabled: bool = True

    # 移动平均线配置
    ma_configs: List[MovingAverageConfig] = field(default_factory=list)

    # 信号配置
    signal_config: SignalConfig = field(default_factory=SignalConfig)

    # 风险管理配置
    risk_config: RiskConfig = field(default_factory=RiskConfig)

    # 回测配置
    initial_capital: float = 100000.0
    benchmark_symbol: str = ""

    # 其他配置
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """初始化后处理"""
        if not self.ma_configs:
            # 默认添加一个SMA配置
            self.ma_configs = [
                MovingAverageConfig(ma_type=MAType.SMA, period=20)
            ]

    def validate(self) -> tuple[bool, List[str]]:
        """
        验证策略配置

        Returns:
            (is_valid, error_messages)
        """
        errors = []

        # 基础配置验证
        if not self.strategy_name.strip():
            errors.append("策略名称不能为空")

        if not isinstance(self.strategy_type, StrategyType):
            errors.append("策略类型无效")

        # 移动平均线配置验证
        if not self.ma_configs:
            errors.append("至少需要配置一个移动平均线")

        for i, ma_config in enumerate(self.ma_configs):
            if not ma_config.validate():
                errors.append(f"移动平均线配置 {i+1} 无效")

        # 信号配置验证
        if not self.signal_config.validate():
            errors.append("信号配置无效")

        # 风险配置验证
        if not self.risk_config.validate():
            errors.append("风险配置无效")

        # 资金配置验证
        if self.initial_capital <= 0:
            errors.append("初始资金必须大于0")

        return len(errors) == 0, errors

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        result = asdict(self)

        # 转换枚举类型
        result['strategy_type'] = self.strategy_type.value

        # 转换移动平均线配置
        ma_configs = []
        for ma_config in self.ma_configs:
            ma_dict = asdict(ma_config)
            ma_dict['ma_type'] = ma_config.ma_type.value
            ma_configs.append(ma_dict)
        result['ma_configs'] = ma_configs

        # 转换信号配置
        result['signal_config'] = {
            **asdict(self.signal_config),
            'ma_type': self.signal_config.ma_type.value
        }

        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StrategyConfig':
        """从字典创建配置"""
        # 复制数据以避免修改原始数据
        data = data.copy()

        # 转换策略类型
        if 'strategy_type' in data:
            data['strategy_type'] = StrategyType(data['strategy_type'])

        # 转换移动平均线配置
        ma_configs = []
        for ma_data in data.get('ma_configs', []):
            ma_data = ma_data.copy()
            ma_data['ma_type'] = MAType(ma_data['ma_type'])
            ma_configs.append(MovingAverageConfig(**ma_data))
        data['ma_configs'] = ma_configs

        # 转换信号配置
        signal_data = data.get('signal_config', {})
        if signal_data:
            signal_data = signal_data.copy()
            signal_data['ma_type'] = MAType(signal_data['ma_type'])
            data['signal_config'] = SignalConfig(**signal_data)

        # 转换风险配置
        risk_data = data.get('risk_config', {})
        if risk_data:
            data['risk_config'] = RiskConfig(**risk_data)

        return cls(**data)

    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)

    @classmethod
    def from_json(cls, json_str: str) -> 'StrategyConfig':
        """从JSON字符串创建配置"""
        data = json.loads(json_str)
        return cls.from_dict(data)

    def to_yaml(self) -> str:
        """转换为YAML字符串"""
        return yaml.dump(self.to_dict(), default_flow_style=False, allow_unicode=True)

    @classmethod
    def from_yaml(cls, yaml_str: str) -> 'StrategyConfig':
        """从YAML字符串创建配置"""
        data = yaml.safe_load(yaml_str)
        return cls.from_dict(data)

    def save_to_file(self, file_path: Union[str, Path]) -> None:
        """保存到文件"""
        file_path = Path(file_path)

        if file_path.suffix.lower() == '.json':
            content = self.to_json()
        elif file_path.suffix.lower() in ['.yaml', '.yml']:
            content = self.to_yaml()
        else:
            raise ValueError(f"不支持的文件格式: {file_path.suffix}")

        file_path.write_text(content, encoding='utf-8')
        logger.info("策略配置已保存", file_path=str(file_path))

    @classmethod
    def load_from_file(cls, file_path: Union[str, Path]) -> 'StrategyConfig':
        """从文件加载配置"""
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {file_path}")

        content = file_path.read_text(encoding='utf-8')

        if file_path.suffix.lower() == '.json':
            return cls.from_json(content)
        elif file_path.suffix.lower() in ['.yaml', '.yml']:
            return cls.from_yaml(content)
        else:
            raise ValueError(f"不支持的文件格式: {file_path.suffix}")

    def update(self, **kwargs) -> None:
        """更新配置参数"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
            else:
                logger.warning("未知的配置参数", key=key)

    def get_ma_config(self, index: int = 0) -> Optional[MovingAverageConfig]:
        """获取指定索引的移动平均线配置"""
        if 0 <= index < len(self.ma_configs):
            return self.ma_configs[index]
        return None

    def add_ma_config(self, ma_config: MovingAverageConfig) -> None:
        """添加移动平均线配置"""
        if ma_config.validate():
            self.ma_configs.append(ma_config)
        else:
            raise ValueError("无效的移动平均线配置")

    def remove_ma_config(self, index: int) -> bool:
        """移除指定索引的移动平均线配置"""
        if 0 <= index < len(self.ma_configs):
            del self.ma_configs[index]
            return True
        return False

    def clone(self) -> 'StrategyConfig':
        """克隆配置"""
        return self.from_dict(self.to_dict())


class StrategyConfigManager:
    """策略配置管理器"""

    def __init__(self, config_dir: Optional[Union[str, Path]] = None):
        """
        初始化配置管理器

        Args:
            config_dir: 配置文件目录
        """
        self.config_dir = Path(config_dir) if config_dir else Path.cwd() / "configs"
        self.config_dir.mkdir(exist_ok=True)
        self._configs: Dict[str, StrategyConfig] = {}
        self._load_default_configs()

    def _load_default_configs(self) -> None:
        """加载默认配置"""
        # 创建默认的单均线策略配置
        default_single_ma = StrategyConfig(
            strategy_name="默认单均线策略",
            strategy_type=StrategyType.SINGLE_MA,
            description="基于20期简单移动平均线的默认策略",
            ma_configs=[
                MovingAverageConfig(ma_type=MAType.SMA, period=20)
            ]
        )
        self._configs["default_single_ma"] = default_single_ma

        # 创建保守的单均线策略配置
        conservative_single_ma = StrategyConfig(
            strategy_name="保守单均线策略",
            strategy_type=StrategyType.SINGLE_MA,
            description="使用较长周期的保守策略",
            ma_configs=[
                MovingAverageConfig(ma_type=MAType.SMA, period=50)
            ],
            signal_config=SignalConfig(
                ma_period=50,
                min_cross_percentage=0.002,
                confirmation_periods=3
            ),
            risk_config=RiskConfig(
                stop_loss_pct=0.015,
                take_profit_pct=0.03,
                max_position_size=0.5
            )
        )
        self._configs["conservative_single_ma"] = conservative_single_ma

        # 创建激进的单均线策略配置
        aggressive_single_ma = StrategyConfig(
            strategy_name="激进单均线策略",
            strategy_type=StrategyType.SINGLE_MA,
            description="使用较短周期的激进策略",
            ma_configs=[
                MovingAverageConfig(ma_type=MAType.EMA, period=10)
            ],
            signal_config=SignalConfig(
                ma_type=MAType.EMA,
                ma_period=10,
                min_cross_percentage=0.0005,
                confirmation_periods=1
            ),
            risk_config=RiskConfig(
                stop_loss_pct=0.025,
                take_profit_pct=0.08,
                max_position_size=0.8
            )
        )
        self._configs["aggressive_single_ma"] = aggressive_single_ma

    def create_config(self, config: StrategyConfig) -> str:
        """
        创建新配置

        Args:
            config: 策略配置

        Returns:
            配置ID
        """
        is_valid, errors = config.validate()
        if not is_valid:
            raise ValueError(f"配置验证失败: {', '.join(errors)}")

        config_id = f"{config.strategy_name}_{len(self._configs)}"
        self._configs[config_id] = config

        logger.info("策略配置已创建", config_id=config_id, name=config.strategy_name)
        return config_id

    def get_config(self, config_id: str) -> Optional[StrategyConfig]:
        """获取配置"""
        return self._configs.get(config_id)

    def list_configs(self) -> Dict[str, Dict[str, Any]]:
        """列出所有配置"""
        result = {}
        for config_id, config in self._configs.items():
            result[config_id] = {
                'name': config.strategy_name,
                'type': config.strategy_type.value,
                'description': config.description,
                'enabled': config.enabled
            }
        return result

    def update_config(self, config_id: str, config: StrategyConfig) -> bool:
        """更新配置"""
        if config_id not in self._configs:
            return False

        is_valid, errors = config.validate()
        if not is_valid:
            raise ValueError(f"配置验证失败: {', '.join(errors)}")

        self._configs[config_id] = config
        logger.info("策略配置已更新", config_id=config_id)
        return True

    def delete_config(self, config_id: str) -> bool:
        """删除配置"""
        if config_id in self._configs:
            del self._configs[config_id]
            logger.info("策略配置已删除", config_id=config_id)
            return True
        return False

    def save_config(self, config_id: str, file_path: Optional[Union[str, Path]] = None) -> None:
        """保存配置到文件"""
        if config_id not in self._configs:
            raise ValueError(f"配置不存在: {config_id}")

        config = self._configs[config_id]

        if file_path is None:
            file_path = self.config_dir / f"{config_id}.json"

        config.save_to_file(file_path)

    def load_config(self, file_path: Union[str, Path], config_id: Optional[str] = None) -> str:
        """从文件加载配置"""
        config = StrategyConfig.load_from_file(file_path)

        if config_id is None:
            config_id = f"loaded_{len(self._configs)}"

        self._configs[config_id] = config
        logger.info("策略配置已从文件加载", config_id=config_id, file_path=str(file_path))
        return config_id

    def get_default_config(self) -> StrategyConfig:
        """获取默认配置"""
        return self._configs.get("default_single_ma", StrategyConfig(
            strategy_name="默认策略",
            strategy_type=StrategyType.SINGLE_MA
        ))


# 便捷函数
def create_single_ma_config(name: str = "单均线策略",
                           ma_type: str = "SMA",
                           ma_period: int = 20,
                           **kwargs) -> StrategyConfig:
    """创建单均线策略配置"""
    return StrategyConfig(
        strategy_name=name,
        strategy_type=StrategyType.SINGLE_MA,
        ma_configs=[MovingAverageConfig(ma_type=MAType(ma_type), period=ma_period)],
        **kwargs
    )


def get_default_strategy_configs() -> Dict[str, StrategyConfig]:
    """获取默认策略配置字典"""
    manager = StrategyConfigManager()
    return manager._configs.copy()