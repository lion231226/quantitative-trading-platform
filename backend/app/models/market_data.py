from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Index
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator
from decimal import Decimal

Base = declarative_base()

class MarketDataDB(Base):
    """市场数据数据库模型"""
    __tablename__ = "market_data"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), nullable=False, comment="期货代码")
    date = Column(DateTime, nullable=False, comment="交易日期")
    open_price = Column(Float, nullable=False, comment="开盘价")
    high_price = Column(Float, nullable=False, comment="最高价")
    low_price = Column(Float, nullable=False, comment="最低价")
    close_price = Column(Float, nullable=False, comment="收盘价")
    volume = Column(Integer, nullable=False, comment="成交量")
    turnover = Column(Float, nullable=True, comment="成交额")
    settlement_price = Column(Float, nullable=True, comment="结算价")
    open_interest = Column(Integer, nullable=True, comment="持仓量")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")

    # 创建复合索引用于查询优化
    __table_args__ = (
        Index('idx_symbol_date', 'symbol', 'date'),
        Index('idx_date_symbol', 'date', 'symbol'),
    )

class MarketData(BaseModel):
    """市场数据响应模型"""
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

    @field_validator('high_price')
    @classmethod
    def high_price_must_be_ge_open(cls, v, info):
        if info.data and 'open_price' in info.data and v < info.data['open_price']:
            raise ValueError('最高价不能低于开盘价')
        if info.data and 'low_price' in info.data and v < info.data['low_price']:
            raise ValueError('最高价不能低于最低价')
        if info.data and 'close_price' in info.data and v < info.data['close_price']:
            raise ValueError('最高价不能低于收盘价')
        return v

    @field_validator('low_price')
    @classmethod
    def low_price_must_be_le_open(cls, v, info):
        if info.data and 'open_price' in info.data and v > info.data['open_price']:
            raise ValueError('最低价不能高于开盘价')
        if info.data and 'high_price' in info.data and v > info.data['high_price']:
            raise ValueError('最低价不能高于最高价')
        if info.data and 'close_price' in info.data and v > info.data['close_price']:
            raise ValueError('最低价不能高于收盘价')
        return v

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class SymbolInfo(BaseModel):
    """期货品种信息模型"""
    symbol: str = Field(..., description="期货代码")
    name: str = Field(..., description="品种名称")
    exchange: str = Field(..., description="交易所")
    sector: str = Field(..., description="版块")
    contract_size: Optional[int] = Field(None, description="合约乘数")
    trading_unit: Optional[str] = Field(None, description="交易单位")
    price_quote: Optional[str] = Field(None, description="报价单位")
    min_price_change: Optional[float] = Field(None, ge=0, description="最小变动价位")
    is_active: bool = Field(True, description="是否活跃交易")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class SectorInfo(BaseModel):
    """版块信息模型"""
    sector_id: str = Field(..., description="版块ID")
    sector_name: str = Field(..., description="版块名称")
    description: str = Field(..., description="版块描述")
    symbols_count: int = Field(..., ge=0, description="品种数量")

class DataUpdateLog(BaseModel):
    """数据更新日志模型"""
    symbol: str = Field(..., description="期货代码")
    update_time: datetime = Field(..., description="更新时间")
    data_count: int = Field(..., ge=0, description="更新数据条数")
    status: str = Field(..., description="更新状态")
    error_message: Optional[str] = Field(None, description="错误信息")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }