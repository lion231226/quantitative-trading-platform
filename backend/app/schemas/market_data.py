from typing import List, Optional, Dict, Any
from datetime import datetime, date
from pydantic import BaseModel, Field, field_validator
from app.models.market_data import MarketData, SymbolInfo, SectorInfo, DataUpdateLog

class MarketDataResponse(BaseModel):
    """市场数据API响应模型"""
    symbol: str = Field(..., description="期货代码")
    date: datetime = Field(..., description="交易日期")
    open_price: float = Field(..., ge=0, description="开盘价")
    high_price: float = Field(..., ge=0, description="最高价")
    low_price: float = Field(..., ge=0, description="最低价")
    close_price: float = Field(..., ge=0, description="收盘价")
    volume: int = Field(..., ge=0, description="成交量")
    turnover: Optional[float] = Field(None, ge=0, description="成交额")
    settlement_price: Optional[float] = Field(None, ge=0, description="结算价")
    open_interest: Optional[int] = Field(None, ge=0, description="持仓量")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class SymbolResponse(BaseModel):
    """期货品种信息API响应模型"""
    symbol: str = Field(..., description="期货代码")
    name: str = Field(..., description="品种名称")
    exchange: str = Field(..., description="交易所")
    sector: str = Field(..., description="版块")
    contract_size: Optional[int] = Field(None, description="合约乘数")
    trading_unit: Optional[str] = Field(None, description="交易单位")
    price_quote: Optional[str] = Field(None, description="报价单位")
    min_price_change: Optional[float] = Field(None, ge=0, description="最小变动价位")
    is_active: bool = Field(True, description="是否活跃交易")

class SectorResponse(BaseModel):
    """版块信息API响应模型"""
    sector_id: str = Field(..., description="版块ID")
    sector_name: str = Field(..., description="版块名称")
    description: str = Field(..., description="版块描述")
    symbols_count: int = Field(..., ge=0, description="品种数量")

class RefreshDataRequest(BaseModel):
    """刷新数据请求模型"""
    symbol: str = Field(..., description="期货代码")
    start_date: Optional[date] = Field(None, description="开始日期")
    end_date: Optional[date] = Field(None, description="结束日期")
    force_refresh: bool = Field(False, description="是否强制刷新")

    @field_validator('end_date')
    @classmethod
    def validate_date_range(cls, v, info):
        if v and info.data and 'start_date' in info.data and info.data['start_date']:
            if v < info.data['start_date']:
                raise ValueError('结束日期不能早于开始日期')
            # 检查日期范围不超过1年
            date_diff = (v - info.data['start_date']).days
            if date_diff > 365:
                raise ValueError('查询时间范围不能超过1年')
        return v

class MarketDataQuery(BaseModel):
    """市场数据查询参数模型"""
    symbol: str = Field(..., description="期货代码")
    start_date: date = Field(..., description="开始日期")
    end_date: date = Field(..., description="结束日期")
    include_volume: bool = Field(True, description="是否包含成交量")
    include_turnover: bool = Field(False, description="是否包含成交额")
    include_open_interest: bool = Field(False, description="是否包含持仓量")

    @field_validator('end_date')
    @classmethod
    def validate_date_range(cls, v, info):
        if info.data and 'start_date' in info.data and v < info.data['start_date']:
            raise ValueError('结束日期不能早于开始日期')
        # 检查日期范围不超过1年
        if info.data and 'start_date' in info.data:
            date_diff = (v - info.data['start_date']).days
            if date_diff > 365:
                raise ValueError('查询时间范围不能超过1年')
        return v

class DataRefreshResponse(BaseModel):
    """数据刷新响应模型"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="响应消息")
    data_count: int = Field(..., ge=0, description="数据条数")
    symbol: str = Field(..., description="期货代码")
    refresh_time: datetime = Field(..., description="刷新时间")
    cache_hit: bool = Field(False, description="是否命中缓存")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class MarketDataStatistics(BaseModel):
    """市场数据统计模型"""
    symbol: str = Field(..., description="期货代码")
    data_count: int = Field(..., ge=0, description="数据条数")
    date_range: Dict[str, date] = Field(..., description="日期范围")
    price_range: Dict[str, float] = Field(..., description="价格范围")
    avg_volume: Optional[float] = Field(None, ge=0, description="平均成交量")
    total_turnover: Optional[float] = Field(None, ge=0, description="总成交额")
    last_update: datetime = Field(..., description="最后更新时间")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat()
        }

class BatchQueryRequest(BaseModel):
    """批量查询请求模型"""
    symbols: List[str] = Field(..., min_length=1, max_length=50, description="期货代码列表")
    start_date: date = Field(..., description="开始日期")
    end_date: date = Field(..., description="结束日期")

    @field_validator('symbols')
    @classmethod
    def validate_symbols(cls, v):
        if len(set(v)) != len(v):
            raise ValueError('期货代码列表不能包含重复项')
        return v

    @field_validator('end_date')
    @classmethod
    def validate_date_range(cls, v, info):
        if info.data and 'start_date' in info.data and v < info.data['start_date']:
            raise ValueError('结束日期不能早于开始日期')
        # 检查日期范围不超过1年
        if info.data and 'start_date' in info.data:
            date_diff = (v - info.data['start_date']).days
            if date_diff > 365:
                raise ValueError('查询时间范围不能超过1年')
        return v

class BatchQueryResponse(BaseModel):
    """批量查询响应模型"""
    success_count: int = Field(..., ge=0, description="成功查询数量")
    total_count: int = Field(..., ge=0, description="总查询数量")
    results: Dict[str, List[MarketDataResponse]] = Field(..., description="查询结果")
    errors: Dict[str, str] = Field(default_factory=dict, description="错误信息")
    query_time: datetime = Field(..., description="查询时间")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class DataQueryResponse(BaseModel):
    """数据查询响应模型"""
    symbol: str = Field(..., description="期货代码")
    data: List[MarketDataResponse] = Field(..., description="市场数据列表")
    total_count: int = Field(..., ge=0, description="总记录数")
    page: int = Field(..., ge=1, description="当前页码")
    size: int = Field(..., ge=1, description="每页大小")
    start_date: Optional[date] = Field(None, description="开始日期")
    end_date: Optional[date] = Field(None, description="结束日期")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat()
        }

class DataExportRequest(BaseModel):
    """数据导出请求模型"""
    symbol: str = Field(..., description="期货代码")
    start_date: Optional[date] = Field(None, description="开始日期")
    end_date: Optional[date] = Field(None, description="结束日期")
    format: str = Field("csv", pattern="^(csv|json|excel)$", description="导出格式")

class DataSyncResponse(BaseModel):
    """数据同步响应模型"""
    symbol: str = Field(..., description="期货代码")
    new_records: int = Field(..., ge=0, description="新增记录数")
    updated_records: int = Field(..., ge=0, description="更新记录数")
    quality_score: float = Field(..., ge=0, le=100, description="数据质量评分")
    sync_time: str = Field(..., description="同步时间")

class DataQualityReport(BaseModel):
    """数据质量报告模型"""
    symbol: str = Field(..., description="期货代码")
    total_records: int = Field(..., ge=0, description="总记录数")
    date_range: Dict[str, str] = Field(..., description="日期范围")
    quality_score: float = Field(..., ge=0, le=100, description="质量评分")
    completeness: Dict[str, Dict[str, Any]] = Field(..., description="完整性统计")
    consistency: Dict[str, Dict[str, Any]] = Field(..., description="一致性统计")
    issues: List[str] = Field(default_factory=list, description="问题列表")