"""
绩效分析相关的数据模型
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Index, Boolean
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator
from decimal import Decimal

Base = declarative_base()


class PerformanceMetricsDB(Base):
    """绩效指标数据库模型"""
    __tablename__ = "performance_metrics"

    id = Column(Integer, primary_key=True, index=True)
    strategy_id = Column(String(50), nullable=False, comment="策略ID")
    calculation_date = Column(DateTime, nullable=False, comment="计算日期")

    # 基础收益指标
    total_return = Column(Float, nullable=False, comment="总收益率")
    annualized_return = Column(Float, nullable=True, comment="年化收益率")

    # 风险指标
    max_drawdown = Column(Float, nullable=False, comment="最大回撤")
    max_drawdown_period = Column(Integer, nullable=True, comment="最大回撤期间")
    volatility = Column(Float, nullable=True, comment="波动率")
    sharpe_ratio = Column(Float, nullable=True, comment="夏普比率")
    sortino_ratio = Column(Float, nullable=True, comment="Sortino比率")

    # 交易统计
    win_rate = Column(Float, nullable=True, comment="胜率")
    profit_loss_ratio = Column(Float, nullable=True, comment="盈亏比")
    total_trades = Column(Integer, nullable=True, comment="总交易次数")
    profitable_trades = Column(Integer, nullable=True, comment="盈利交易次数")

    # 元数据
    benchmark_id = Column(String(50), nullable=True, comment="基准ID")
    period_start = Column(DateTime, nullable=True, comment="分析期间开始")
    period_end = Column(DateTime, nullable=True, comment="分析期间结束")
    data_points = Column(Integer, nullable=True, comment="数据点数量")

    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")

    # 创建复合索引用于查询优化
    __table_args__ = (
        Index('idx_strategy_date', 'strategy_id', 'calculation_date'),
        Index('idx_calculation_date', 'calculation_date'),
    )


class TradingStatisticsDB(Base):
    """交易统计数据模型"""
    __tablename__ = "trading_statistics"

    id = Column(Integer, primary_key=True, index=True)
    strategy_id = Column(String(50), nullable=False, comment="策略ID")
    trade_date = Column(DateTime, nullable=False, comment="交易日期")

    # 交易统计
    trade_count = Column(Integer, nullable=False, comment="交易次数")
    winning_trades = Column(Integer, nullable=False, comment="盈利交易次数")
    losing_trades = Column(Integer, nullable=False, comment="亏损交易次数")

    # 收益统计
    average_win = Column(Float, nullable=True, comment="平均盈利")
    average_loss = Column(Float, nullable=True, comment="平均亏损")
    largest_win = Column(Float, nullable=True, comment="最大盈利")
    largest_loss = Column(Float, nullable=True, comment="最大亏损")

    # 时间统计
    average_holding_period = Column(Float, nullable=True, comment="平均持仓时间（天）")
    trade_frequency = Column(Float, nullable=True, comment="交易频率（次/月）")

    # 成本统计
    total_commission = Column(Float, nullable=True, comment="总手续费")
    total_slippage = Column(Float, nullable=True, comment="总滑点")

    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")

    # 创建复合索引用于查询优化
    __table_args__ = (
        Index('idx_strategy_trade_date', 'strategy_id', 'trade_date'),
        Index('idx_trade_date', 'trade_date'),
    )


class PerformanceMetrics(BaseModel):
    """绩效指标响应模型"""
    strategy_id: str = Field(..., description="策略ID")
    calculation_date: datetime = Field(..., description="计算日期")

    # 基础收益指标
    total_return: float = Field(..., description="总收益率")
    annualized_return: Optional[float] = Field(None, description="年化收益率")

    # 风险指标
    max_drawdown: float = Field(..., description="最大回撤")
    max_drawdown_period: Optional[int] = Field(None, description="最大回撤期间")
    volatility: Optional[float] = Field(None, description="波动率")
    sharpe_ratio: Optional[float] = Field(None, description="夏普比率")
    sortino_ratio: Optional[float] = Field(None, description="Sortino比率")

    # 交易统计
    win_rate: Optional[float] = Field(None, ge=0, le=1, description="胜率")
    profit_loss_ratio: Optional[float] = Field(None, ge=0, description="盈亏比")
    total_trades: Optional[int] = Field(None, ge=0, description="总交易次数")
    profitable_trades: Optional[int] = Field(None, ge=0, description="盈利交易次数")

    # 元数据
    benchmark_id: Optional[str] = Field(None, description="基准ID")
    period_start: Optional[datetime] = Field(None, description="分析期间开始")
    period_end: Optional[datetime] = Field(None, description="分析期间结束")
    data_points: Optional[int] = Field(None, ge=0, description="数据点数量")

    @field_validator('total_return')
    @classmethod
    def validate_total_return(cls, v):
        if v < -1:
            raise ValueError('总收益率不能小于-100%')
        return v

    @field_validator('max_drawdown')
    @classmethod
    def validate_max_drawdown(cls, v):
        # 最大回撤应该是0或负数（例如-0.15表示15%的回撤）
        if v > 0:
            # 如果计算结果是正数，转换为负数
            v = -abs(v)
        return v

    @field_validator('sharpe_ratio', 'sortino_ratio')
    @classmethod
    def validate_ratios(cls, v):
        if v is not None and v < -10:
            raise ValueError('风险调整收益比率不能小于-10')
        return v

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class TradingStatistics(BaseModel):
    """交易统计响应模型"""
    strategy_id: str = Field(..., description="策略ID")
    trade_date: datetime = Field(..., description="交易日期")

    # 交易统计
    trade_count: int = Field(..., ge=0, description="交易次数")
    winning_trades: int = Field(..., ge=0, description="盈利交易次数")
    losing_trades: int = Field(..., ge=0, description="亏损交易次数")

    # 收益统计
    average_win: Optional[float] = Field(None, ge=0, description="平均盈利")
    average_loss: Optional[float] = Field(None, le=0, description="平均亏损")
    largest_win: Optional[float] = Field(None, ge=0, description="最大盈利")
    largest_loss: Optional[float] = Field(None, le=0, description="最大亏损")

    # 时间统计
    average_holding_period: Optional[float] = Field(None, ge=0, description="平均持仓时间（天）")
    trade_frequency: Optional[float] = Field(None, ge=0, description="交易频率（次/月）")

    # 成本统计
    total_commission: Optional[float] = Field(None, ge=0, description="总手续费")
    total_slippage: Optional[float] = Field(None, ge=0, description="总滑点")

    @field_validator('losing_trades')
    @classmethod
    def validate_losing_trades(cls, v, info):
        if info.context and 'trade_count' in info.context and 'winning_trades' in info.context:
            if v + info.context['winning_trades'] != info.context['trade_count']:
                raise ValueError('亏损交易次数 + 盈利交易次数必须等于总交易次数')
        return v

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class PerformanceReport(BaseModel):
    """绩效报告模型"""
    strategy_id: str = Field(..., description="策略ID")
    report_date: datetime = Field(default_factory=datetime.now, description="报告日期")
    report_type: str = Field(..., description="报告类型")
    period_start: datetime = Field(..., description="分析期间开始")
    period_end: datetime = Field(..., description="分析期间结束")

    # 报告内容
    metrics: PerformanceMetrics = Field(..., description="绩效指标")
    trading_stats: Optional[TradingStatistics] = Field(None, description="交易统计")
    benchmark_comparison: Optional[dict] = Field(None, description="基准比较")

    # 分析摘要
    summary: str = Field(..., description="绩效摘要")
    recommendations: Optional[list] = Field(None, description="改进建议")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class PerformanceCalculationRequest(BaseModel):
    """绩效计算请求模型"""
    strategy_id: str = Field(..., description="策略ID")
    return_type: str = Field("simple", pattern="^(simple|log)$", description="收益率类型")
    initial_capital: float = Field(100000, ge=1000, description="初始资金")
    position_size: float = Field(1.0, ge=0, le=1, description="仓位大小")
    benchmark_id: Optional[str] = Field(None, description="基准ID")
    risk_free_rate: float = Field(0.02, ge=0, le=1, description="无风险利率")
    include_costs: bool = Field(True, description="是否包含交易成本")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }