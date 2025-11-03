"""
回测配置
定义回测参数和设置
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
import json
import yaml
from pathlib import Path
import structlog

logger = structlog.get_logger()


@dataclass
class BacktestConfig:
    """回测配置"""
    # 基础配置
    start_date: str  # 开始日期 YYYY-MM-DD
    end_date: str    # 结束日期 YYYY-MM-DD
    symbols: List[str]  # 交易标的列表
    initial_capital: float = 100000.0  # 初始资金

    # 数据配置
    data_frequency: str = "1d"  # 数据频率 (1m, 5m, 15m, 1h, 1d)
    benchmark_symbol: str = ""   # 基准标的

    # 执行配置
    commission_enabled: bool = True
    commission_rate: float = 0.001
    slippage_enabled: bool = True
    slippage_rate: float = 0.0001

    # 输出配置
    save_trades: bool = True
    save_equity_curve: bool = True
    save_signals: bool = True
    output_directory: str = "backtest_results"

    # 高级配置
    parallel_processing: bool = False
    max_workers: int = 4
    chunk_size: int = 1000

    def validate(self) -> tuple[bool, List[str]]:
        """
        验证回测配置

        Returns:
            (is_valid, error_messages)
        """
        errors = []

        # 验证日期格式
        try:
            start_dt = datetime.fromisoformat(self.start_date)
            end_dt = datetime.fromisoformat(self.end_date)
            if start_dt >= end_dt:
                errors.append("开始日期必须早于结束日期")
        except ValueError:
            errors.append("日期格式无效，请使用 YYYY-MM-DD 格式")

        # 验证标的列表
        if not self.symbols:
            errors.append("至少需要指定一个交易标的")

        # 验证初始资金
        if self.initial_capital <= 0:
            errors.append("初始资金必须大于0")

        # 验证手续费率
        if not 0 <= self.commission_rate < 1:
            errors.append("手续费率必须在 0 到 1 之间")

        # 验证滑点率
        if not 0 <= self.slippage_rate < 1:
            errors.append("滑点率必须在 0 到 1 之间")

        # 验证数据频率
        valid_frequencies = ["1m", "5m", "15m", "30m", "1h", "4h", "1d", "1w"]
        if self.data_frequency not in valid_frequencies:
            errors.append(f"数据频率无效，支持的频率: {', '.join(valid_frequencies)}")

        return len(errors) == 0, errors

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'start_date': self.start_date,
            'end_date': self.end_date,
            'symbols': self.symbols,
            'initial_capital': self.initial_capital,
            'data_frequency': self.data_frequency,
            'benchmark_symbol': self.benchmark_symbol,
            'commission_enabled': self.commission_enabled,
            'commission_rate': self.commission_rate,
            'slippage_enabled': self.slippage_enabled,
            'slippage_rate': self.slippage_rate,
            'save_trades': self.save_trades,
            'save_equity_curve': self.save_equity_curve,
            'save_signals': self.save_signals,
            'output_directory': self.output_directory,
            'parallel_processing': self.parallel_processing,
            'max_workers': self.max_workers,
            'chunk_size': self.chunk_size
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BacktestConfig':
        """从字典创建配置"""
        return cls(**data)

    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)

    @classmethod
    def from_json(cls, json_str: str) -> 'BacktestConfig':
        """从JSON字符串创建配置"""
        data = json.loads(json_str)
        return cls.from_dict(data)

    def to_yaml(self) -> str:
        """转换为YAML字符串"""
        return yaml.dump(self.to_dict(), default_flow_style=False, allow_unicode=True)

    @classmethod
    def from_yaml(cls, yaml_str: str) -> 'BacktestConfig':
        """从YAML字符串创建配置"""
        data = yaml.safe_load(yaml_str)
        return cls.from_dict(data)

    def save_to_file(self, file_path: str) -> None:
        """保存到文件"""
        file_path = Path(file_path)

        if file_path.suffix.lower() == '.json':
            content = self.to_json()
        elif file_path.suffix.lower() in ['.yaml', '.yml']:
            content = self.to_yaml()
        else:
            raise ValueError(f"不支持的文件格式: {file_path.suffix}")

        file_path.write_text(content, encoding='utf-8')
        logger.info("回测配置已保存", file_path=str(file_path))

    @classmethod
    def load_from_file(cls, file_path: str) -> 'BacktestConfig':
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

    def clone(self) -> 'BacktestConfig':
        """克隆配置"""
        return self.from_dict(self.to_dict())


# 预定义的回测配置模板
class BacktestPresets:
    """回测配置预设"""

    @staticmethod
    def daily_single_symbol(symbol: str,
                           start_date: str,
                           end_date: str,
                           initial_capital: float = 100000.0) -> BacktestConfig:
        """日线单标的回测配置"""
        return BacktestConfig(
            start_date=start_date,
            end_date=end_date,
            symbols=[symbol],
            initial_capital=initial_capital,
            data_frequency="1d",
            commission_enabled=True,
            commission_rate=0.001,
            slippage_enabled=True,
            slippage_rate=0.0001
        )

    @staticmethod
    def intraday_single_symbol(symbol: str,
                              start_date: str,
                              end_date: str,
                              frequency: str = "1h",
                              initial_capital: float = 100000.0) -> BacktestConfig:
        """日内单标的回测配置"""
        return BacktestConfig(
            start_date=start_date,
            end_date=end_date,
            symbols=[symbol],
            initial_capital=initial_capital,
            data_frequency=frequency,
            commission_enabled=True,
            commission_rate=0.0005,
            slippage_enabled=True,
            slippage_rate=0.0002
        )

    @staticmethod
    def multi_symbol(symbols: List[str],
                    start_date: str,
                    end_date: str,
                    initial_capital: float = 100000.0) -> BacktestConfig:
        """多标的回测配置"""
        return BacktestConfig(
            start_date=start_date,
            end_date=end_date,
            symbols=symbols,
            initial_capital=initial_capital,
            data_frequency="1d",
            commission_enabled=True,
            commission_rate=0.001,
            slippage_enabled=True,
            slippage_rate=0.0001,
            parallel_processing=True,
            max_workers=min(len(symbols), 4)
        )

    @staticmethod
    def stress_test(symbol: str,
                   start_date: str,
                   end_date: str,
                   initial_capital: float = 50000.0) -> BacktestConfig:
        """压力测试配置（较高手续费和滑点）"""
        return BacktestConfig(
            start_date=start_date,
            end_date=end_date,
            symbols=[symbol],
            initial_capital=initial_capital,
            data_frequency="1h",
            commission_enabled=True,
            commission_rate=0.002,
            slippage_enabled=True,
            slippage_rate=0.0005
        )

    @staticmethod
    def ideal_conditions(symbol: str,
                        start_date: str,
                        end_date: str,
                        initial_capital: float = 100000.0) -> BacktestConfig:
        """理想条件配置（无手续费和滑点）"""
        return BacktestConfig(
            start_date=start_date,
            end_date=end_date,
            symbols=[symbol],
            initial_capital=initial_capital,
            data_frequency="1d",
            commission_enabled=False,
            commission_rate=0.0,
            slippage_enabled=False,
            slippage_rate=0.0
        )


# 便捷函数
def create_backtest_config(start_date: str,
                          end_date: str,
                          symbols: List[str],
                          **kwargs) -> BacktestConfig:
    """创建回测配置"""
    return BacktestConfig(
        start_date=start_date,
        end_date=end_date,
        symbols=symbols,
        **kwargs
    )


def get_recent_months_config(symbol: str, months: int = 6) -> BacktestConfig:
    """获取最近几个月的回测配置"""
    from datetime import datetime, timedelta

    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=months * 30)

    return BacktestPresets.daily_single_symbol(
        symbol=symbol,
        start_date=start_date.isoformat(),
        end_date=end_date.isoformat()
    )


def get_year_to_date_config(symbol: str, initial_capital: float = 100000.0) -> BacktestConfig:
    """获取今年至今的回测配置"""
    from datetime import datetime

    current_year = datetime.now().year
    start_date = f"{current_year}-01-01"
    end_date = datetime.now().date().isoformat()

    return BacktestPresets.daily_single_symbol(
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
        initial_capital=initial_capital
    )