"""
绩效分析相关的API响应模式
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class PerformanceCalculationRequest(BaseModel):
    """绩效计算请求"""
    strategy_id: str = Field(..., description="策略ID")
    return_type: str = Field("simple", pattern="^(simple|log)$", description="收益率类型")
    initial_capital: float = Field(100000, ge=1000, description="初始资金")
    position_size: float = Field(1.0, ge=0, le=1, description="仓位大小")
    benchmark_id: Optional[str] = Field(None, description="基准ID")
    risk_free_rate: float = Field(0.02, ge=0, le=1, description="无风险利率")
    include_costs: bool = Field(True, description="是否包含交易成本")
    start_date: Optional[str] = Field(None, description="开始日期 (YYYY-MM-DD)")
    end_date: Optional[str] = Field(None, description="结束日期 (YYYY-MM-DD)")


class PerformanceMetricsResponse(BaseModel):
    """绩效指标响应"""
    success: bool = Field(True, description="请求是否成功")
    data: Optional[Dict[str, Any]] = Field(None, description="绩效指标数据")
    message: str = Field("绩效计算成功", description="响应消息")


class PerformanceCalculationResponse(BaseModel):
    """绩效计算响应"""
    success: bool = Field(True, description="请求是否成功")
    data: Optional[Dict[str, Any]] = Field(None, description="计算结果")
    message: str = Field("收益率计算成功", description="响应消息")


class PerformanceReportRequest(BaseModel):
    """绩效报告请求"""
    strategy_id: str = Field(..., description="策略ID")
    report_type: str = Field("comprehensive", pattern="^(comprehensive|risk|returns)$", description="报告类型")
    time_period: str = Field("1y", pattern="^(1m|3m|6m|1y|all)$", description="时间期间")
    include_charts: bool = Field(True, description="是否包含图表")
    format: str = Field("json", pattern="^(json|pdf|html)$", description="报告格式")


class PerformanceReportResponse(BaseModel):
    """绩效报告响应"""
    success: bool = Field(True, description="请求是否成功")
    data: Optional[Dict[str, Any]] = Field(None, description="报告数据")
    message: str = Field("报告生成成功", description="响应消息")


class ErrorResponse(BaseModel):
    """错误响应"""
    success: bool = Field(False, description="请求是否失败")
    error: Dict[str, Any] = Field(..., description="错误信息")
    message: str = Field(..., description="错误消息")


class ValidationErrorResponse(BaseModel):
    """验证错误响应"""
    success: bool = Field(False, description="请求是否失败")
    error: Dict[str, Any] = Field(
        default={
            "type": "VALIDATION_ERROR",
            "message": "参数验证失败",
            "details": {}
        },
        description="验证错误信息"
    )
    message: str = Field("参数验证失败", description="错误消息")


# API响应格式示例
SUCCESS_RESPONSE_EXAMPLE = {
    "success": True,
    "data": {
        "strategy_id": "strategy_123456",
        "total_return": 0.156,
        "annualized_return": 0.142,
        "max_drawdown": -0.089,
        "sharpe_ratio": 1.23,
        "sortino_ratio": 1.67,
        "volatility": 0.186,
        "win_rate": 0.65,
        "profit_loss_ratio": 1.85,
        "total_trades": 24,
        "profitable_trades": 16,
        "calculation_date": "2025-11-01T10:30:00Z"
    },
    "message": "绩效计算成功"
}

ERROR_RESPONSE_EXAMPLE = {
    "success": False,
    "error": {
        "type": "VALIDATION_ERROR",
        "message": "参数验证失败",
        "details": {
            "field": "initial_capital",
            "issue": "初始资金必须大于等于1000"
        }
    },
    "message": "参数验证失败"
}