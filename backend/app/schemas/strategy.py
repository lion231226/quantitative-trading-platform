"""
策略相关API响应模式
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, date
from pydantic import BaseModel, Field, model_validator


class StrategyParameters(BaseModel):
    """策略参数"""
    ma_period: int = Field(20, ge=5, le=200, description="移动平均线周期")
    initial_capital: float = Field(100000, ge=10000, le=10000000, description="初始资金")
    stop_loss: float = Field(0.05, ge=0, le=0.5, description="止损百分比")
    position_size: float = Field(0.1, ge=0.01, le=1, description="仓位大小")
    commission: float = Field(0.001, ge=0, le=0.01, description="手续费率")
    slippage: float = Field(0.0001, ge=0, le=0.001, description="滑点")


class StrategyRequest(BaseModel):
    """策略执行请求"""
    symbol: str = Field(..., description="期货品种")
    strategy_type: str = Field(..., description="策略类型")
    start_date: date = Field(..., description="开始日期")
    end_date: date = Field(..., description="结束日期")
    parameters: Dict[str, Any] = Field(..., description="策略参数")

    @model_validator(mode='after')
    def validate_date_range(self) -> 'StrategyRequest':
        if self.end_date < self.start_date:
            raise ValueError('结束日期不能早于开始日期')
        return self


class StrategyResponse(BaseModel):
    """策略执行响应"""
    strategy_id: str = Field(..., description="策略执行ID")
    strategy_type: str = Field(..., description="策略类型")
    symbol: str = Field(..., description="期货品种")
    parameters: Dict[str, Any] = Field(..., description="策略参数")
    status: str = Field(..., description="执行状态")
    message: Optional[str] = Field(None, description="状态消息")
    execution_time: Optional[float] = Field(None, description="执行时间（秒）")
    data: Optional[Dict[str, Any]] = Field(None, description="策略结果数据")


class StrategyListResponse(BaseModel):
    """策略列表响应"""
    strategies: List[Dict[str, Any]] = Field(..., description="策略列表")
    total: int = Field(..., description="策略总数")


# 向后兼容的响应格式
class LegacyStrategyResponse(BaseModel):
    """策略执行响应（兼容旧格式）"""
    success: bool = Field(True, description="请求是否成功")
    data: Optional[Dict[str, Any]] = Field(None, description="策略执行结果")
    message: str = Field("策略执行成功", description="响应消息")


class LegacyStrategyListResponse(BaseModel):
    """策略列表响应（兼容旧格式）"""
    success: bool = Field(True, description="请求是否成功")
    data: Optional[List[Dict[str, Any]]] = Field(None, description="策略列表")
    message: str = Field("策略列表获取成功", description="响应消息")