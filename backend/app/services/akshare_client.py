import akshare as ak
import pandas as pd
from typing import List, Optional, Dict, Any, Any
from datetime import datetime, date, timedelta
import asyncio
import structlog
from app.models.market_data import MarketData, SymbolInfo, SectorInfo
from app.schemas.market_data import MarketDataResponse, SymbolResponse, SectorResponse
from app.utils.errors import APIError, ValidationError
import time
from functools import wraps

logger = structlog.get_logger()

def retry_on_failure(max_retries: int = 3, delay: float = 1.0) -> Any:
    """重试装饰器"""
    def decorator(func) -> Any:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        logger.warning(
                            f"函数 {func.__name__} 调用失败，正在重试",
                            attempt=attempt + 1,
                            max_retries=max_retries,
                            error=str(e)
                        )
                        await asyncio.sleep(delay * (2 ** attempt))  # 指数退避
                    else:
                        logger.error(
                            f"函数 {func.__name__} 调用失败，已达到最大重试次数",
                            max_retries=max_retries,
                            error=str(e)
                        )
            raise last_exception
        return wrapper
    return decorator

class AKShareClient:
    """AKShare API客户端"""

    # 版块映射
    SECTOR_MAPPING = {
        "energy": "能源",
        "metal": "金属",
        "agriculture": "农产品",
        "chemical": "化工"
    }

    # 期货交易所映射
    EXCHANGE_MAPPING = {
        "SHFE": "上海期货交易所",
        "DCE": "大连商品交易所",
        "CZCE": "郑州商品交易所",
        "CFFEX": "中国金融期货交易所",
        "INE": "上海国际能源交易中心"
    }

    def __init__(self) -> Any:
        self.timeout = 30  # API调用超时时间

    async def get_supported_sectors(self) -> List[str]:
        """获取支持的版块列表"""
        try:
            return list(self.SECTOR_MAPPING.keys())
        except Exception as e:
            logger.error("获取支持版块列表失败", error=str(e))
            raise APIError(f"获取支持版块列表失败: {str(e)}")

    @retry_on_failure(max_retries=3, delay=1.0)
    async def get_available_symbols(self, sector: Optional[str] = None) -> List[SymbolResponse]:
        """获取可用的期货品种列表"""
        try:
            logger.info("获取期货品种列表", sector=sector)

            symbols = []

            # 根据版块获取不同的期货品种
            if sector is None or sector == "energy":
                # 能源版块 - 原油、燃油等
                energy_symbols = await self._get_energy_symbols()
                symbols.extend(energy_symbols)

            if sector is None or sector == "metal":
                # 金属版块 - 铜、铝、锌、镍、锡等
                metal_symbols = await self._get_metal_symbols()
                symbols.extend(metal_symbols)

            if sector is None or sector == "agriculture":
                # 农产品版块 - 大豆、玉米、棉花等
                agri_symbols = await self._get_agriculture_symbols()
                symbols.extend(agri_symbols)

            if sector is None or sector == "chemical":
                # 化工版块 - PTA、甲醇等
                chem_symbols = await self._get_chemical_symbols()
                symbols.extend(chem_symbols)

            logger.info("获取期货品种成功", count=len(symbols), sector=sector)
            return symbols

        except Exception as e:
            logger.error("获取期货品种失败", error=str(e), sector=sector)
            raise APIError(f"获取期货品种失败: {str(e)}")

    async def _get_energy_symbols(self) -> List[SymbolResponse]:
        """获取能源版块期货品种"""
        symbols = []
        try:
            # 获取原油期货 - 使用异步方式避免阻塞事件循环
            loop = asyncio.get_event_loop()
            df = await loop.run_in_executor(None, lambda: ak.futures_main_sina(symbol="SC0"))  # 原油主力合约
            if not df.empty:
                symbols.append(SymbolResponse(
                    symbol="SC",
                    name="原油",
                    exchange="INE",
                    sector="energy",
                    contract_size=1000,
                    trading_unit="手",
                    price_quote="元/桶",
                    min_price_change=0.1,
                    is_active=True
                ))
        except Exception as e:
            logger.warning("获取原油期货信息失败", error=str(e))

        return symbols

    async def _get_metal_symbols(self) -> List[SymbolResponse]:
        """获取金属版块期货品种"""
        symbols = []
        metal_futures = {
            "CU": ("铜", "SHFE", 5),
            "AL": ("铝", "SHFE", 5),
            "ZN": ("锌", "SHFE", 5),
            "NI": ("镍", "SHFE", 1),
            "SN": ("锡", "SHFE", 1),
            "PB": ("铅", "SHFE", 5),
            "AU": ("黄金", "SHFE", 1000),
            "AG": ("白银", "SHFE", 15)
        }

        for symbol, (name, exchange, contract_size) in metal_futures.items():
            try:
                symbols.append(SymbolResponse(
                    symbol=symbol,
                    name=name,
                    exchange=exchange,
                    sector="metal",
                    contract_size=contract_size,
                    trading_unit="手",
                    price_quote="元/吨",
                    min_price_change=10 if symbol in ["CU", "AL", "ZN", "PB"] else 1,
                    is_active=True
                ))
            except Exception as e:
                logger.warning(f"获取{symbol}期货信息失败", error=str(e))

        return symbols

    async def _get_agriculture_symbols(self) -> List[SymbolResponse]:
        """获取农产品版块期货品种"""
        symbols = []
        agri_futures = {
            "M": ("豆粕", "DCE", 10),
            "Y": ("豆油", "DCE", 10),
            "A": ("大豆一号", "DCE", 10),
            "C": ("玉米", "DCE", 10),
            "CF": ("棉花", "CZCE", 5),
            "SR": ("白糖", "CZCE", 10),
            "RM": ("菜粕", "CZCE", 10),
            "OI": ("菜油", "CZCE", 10),
            "JD": ("鸡蛋", "DCE", 10),
            "AP": ("苹果", "CZCE", 10)
        }

        for symbol, (name, exchange, contract_size) in agri_futures.items():
            try:
                symbols.append(SymbolResponse(
                    symbol=symbol,
                    name=name,
                    exchange=exchange,
                    sector="agriculture",
                    contract_size=contract_size,
                    trading_unit="手",
                    price_quote="元/吨",
                    min_price_change=1,
                    is_active=True
                ))
            except Exception as e:
                logger.warning(f"获取{symbol}期货信息失败", error=str(e))

        return symbols

    async def _get_chemical_symbols(self) -> List[SymbolResponse]:
        """获取化工版块期货品种"""
        symbols = []
        chem_futures = {
            "TA": ("PTA", "CZCE", 5),
            "MA": ("甲醇", "CZCE", 50),
            "L": ("LLDPE", "DCE", 5),
            "V": ("PVC", "DCE", 5),
            "PP": ("PP", "DCE", 5),
            "EB": ("苯乙烯", "DCE", 5),
            "EG": ("乙二醇", "DCE", 10),
            "PG": ("LPG", "DCE", 20),
            "SA": ("纯碱", "CZCE", 20),
            "UR": ("尿素", "CZCE", 20)
        }

        for symbol, (name, exchange, contract_size) in chem_futures.items():
            try:
                symbols.append(SymbolResponse(
                    symbol=symbol,
                    name=name,
                    exchange=exchange,
                    sector="chemical",
                    contract_size=contract_size,
                    trading_unit="手",
                    price_quote="元/吨",
                    min_price_change=1,
                    is_active=True
                ))
            except Exception as e:
                logger.warning(f"获取{symbol}期货信息失败", error=str(e))

        return symbols

    @retry_on_failure(max_retries=3, delay=1.0)
    async def get_market_data(
        self,
        symbol: str,
        start_date: date,
        end_date: date
    ) -> List[MarketDataResponse]:
        """获取期货历史数据"""
        try:
            logger.info("获取期货历史数据", symbol=symbol, start_date=start_date, end_date=end_date)

            # 验证日期范围
            if start_date > end_date:
                raise ValidationError("开始日期不能晚于结束日期")

            date_diff = (end_date - start_date).days
            if date_diff > 365:
                raise ValidationError("查询时间范围不能超过1年")

            # 确定期货交易所和合约代码
            exchange, contract_code = await self._determine_exchange_and_contract(symbol)

            # 调用AKShare API获取数据
            df = await self._fetch_futures_data(exchange, contract_code, start_date, end_date)

            if df.empty:
                logger.warning("未获取到数据", symbol=symbol, start_date=start_date, end_date=end_date)
                return []

            # 数据转换和验证
            market_data_list = await self._convert_dataframe_to_market_data(df, symbol)

            logger.info("获取期货数据成功", symbol=symbol, count=len(market_data_list))
            return market_data_list

        except ValidationError:
            raise
        except Exception as e:
            logger.error("获取期货数据失败", error=str(e), symbol=symbol)
            raise APIError(f"获取期货数据失败: {str(e)}")

    async def _determine_exchange_and_contract(self, symbol: str) -> tuple:
        """确定期货交易所和合约代码"""
        # 根据品种代码确定交易所
        if symbol in ["CU", "AL", "ZN", "NI", "SN", "PB", "AU", "AG"]:
            return "SHFE", f"{symbol}0"  # 上海期货交易所
        elif symbol in ["SC"]:
            return "INE", f"{symbol}0"  # 上海国际能源交易中心
        elif symbol in ["M", "Y", "A", "C", "L", "V", "PP", "EB", "EG", "PG", "JD", "I", "J", "JM", "B", "P", "FB"]:
            return "DCE", f"{symbol}0"  # 大连商品交易所
        elif symbol in ["CF", "SR", "RM", "OI", "TA", "MA", "SA", "UR", "AP", "SM", "SF", "FG", "WH", "PM", "RI", "JR", "LR", "WS", "WT", "RS", "RO", "OI", "TC", "WH"]:
            return "CZCE", f"{symbol}0"  # 郑州商品交易所
        elif symbol in ["IF", "IH", "IC", "T", "TF", "TS", "TL"]:
            return "CFFEX", f"{symbol}0"  # 中国金融期货交易所
        else:
            # 默认尝试大连商品交易所
            return "DCE", f"{symbol}0"

    async def _fetch_futures_data(
        self,
        exchange: str,
        contract_code: str,
        start_date: date,
        end_date: date
    ) -> pd.DataFrame:
        """从AKShare获取期货数据"""
        try:
            # 转换日期格式
            start_str = start_date.strftime("%Y%m%d")
            end_str = end_date.strftime("%Y%m%d")

            # 根据交易所选择不同的API
            if exchange == "SHFE":
                df = ak.futures_main_sina(symbol=contract_code)
            elif exchange == "DCE":
                df = ak.futures_main_sina(symbol=contract_code)
            elif exchange == "CZCE":
                df = ak.futures_main_sina(symbol=contract_code)
            elif exchange == "INE":
                df = ak.futures_main_sina(symbol=contract_code)
            else:
                # 通用方法
                df = ak.futures_main_sina(symbol=contract_code)

            if df.empty:
                return df

            # 数据清洗和转换
            df = await self._clean_dataframe(df, start_date, end_date)
            return df

        except Exception as e:
            logger.error("从AKShare获取数据失败", error=str(e), exchange=exchange, contract_code=contract_code)
            raise APIError(f"从AKShare获取数据失败: {str(e)}")

    async def _clean_dataframe(self, df: pd.DataFrame, start_date: date, end_date: date) -> pd.DataFrame:
        """清洗和预处理数据"""
        try:
            # 标准化列名
            column_mapping = {
                '日期': 'date',
                '开盘价': 'open',
                '最高价': 'high',
                '最低价': 'low',
                '收盘价': 'close',
                '成交量': 'volume',
                '成交额': 'turnover',
                '持仓量': 'open_interest'
            }

            # 检查并重命名列
            existing_columns = df.columns.tolist()
            for chinese_col, english_col in column_mapping.items():
                if chinese_col in existing_columns:
                    df = df.rename(columns={chinese_col: english_col})

            # 确保日期列为datetime类型
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'])
            else:
                # 尝试使用索引作为日期
                if isinstance(df.index, pd.DatetimeIndex):
                    df = df.reset_index()
                    df = df.rename(columns={'index': 'date'})
                else:
                    raise ValueError("无法识别日期列")

            # 过滤日期范围
            df = df[
                (df['date'].dt.date >= start_date) &
                (df['date'].dt.date <= end_date)
            ]

            # 确保数值列的数据类型正确
            numeric_columns = ['open', 'high', 'low', 'close', 'volume', 'turnover', 'open_interest']
            for col in numeric_columns:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')

            # 按日期排序
            df = df.sort_values('date').reset_index(drop=True)

            return df

        except Exception as e:
            logger.error("数据清洗失败", error=str(e))
            raise APIError(f"数据清洗失败: {str(e)}")

    async def _convert_dataframe_to_market_data(self, df: pd.DataFrame, symbol: str) -> List[MarketDataResponse]:
        """将DataFrame转换为市场数据列表"""
        market_data_list = []

        for _, row in df.iterrows():
            try:
                # 验证价格数据的合理性
                open_price = float(row.get('open', 0))
                high_price = float(row.get('high', 0))
                low_price = float(row.get('low', 0))
                close_price = float(row.get('close', 0))
                volume = int(row.get('volume', 0))

                # 基本数据验证
                if high_price < low_price:
                    logger.warning("价格数据异常", symbol=symbol, date=row['date'], high=high_price, low=low_price)
                    continue

                if open_price <= 0 or close_price <= 0:
                    logger.warning("价格数据为零或负数", symbol=symbol, date=row['date'])
                    continue

                # 增强的价格合理性验证
                if not self._validate_price_reasonability(open_price, high_price, low_price, close_price):
                    logger.warning("价格数据不合理", symbol=symbol, date=row['date'],
                                open=open_price, high=high_price, low=low_price, close=close_price)
                    continue

                # 检查价格波动幅度（防止异常数据）
                price_change_pct = abs((close_price - open_price) / open_price) if open_price > 0 else 0
                if price_change_pct > 0.5:  # 单日涨跌幅超过50%
                    logger.warning("价格波动异常", symbol=symbol, date=row['date'],
                                change_pct=price_change_pct, open=open_price, close=close_price)
                    continue

                market_data = MarketDataResponse(
                    symbol=symbol,
                    date=row['date'],
                    open_price=open_price,
                    high_price=high_price,
                    low_price=low_price,
                    close_price=close_price,
                    volume=volume,
                    turnover=float(row.get('turnover', 0)) if pd.notna(row.get('turnover')) else None,
                    settlement_price=float(row.get('close', 0)),  # 用收盘价作为结算价
                    open_interest=int(row.get('open_interest', 0)) if pd.notna(row.get('open_interest')) else None
                )
                market_data_list.append(market_data)

            except Exception as e:
                logger.warning("转换数据行失败", symbol=symbol, date=row.get('date'), error=str(e))
                continue

        return market_data_list

    def _validate_price_reasonability(self, open_price: float, high_price: float, low_price: float, close_price: float) -> bool:
        """验证价格数据的合理性"""
        try:
            # 检查价格是否为正数
            if any(price <= 0 for price in [open_price, high_price, low_price, close_price]):
                return False

            # 检查高低价关系
            if not (low_price <= open_price <= high_price and low_price <= close_price <= high_price):
                return False

            # 检查价格跳跃幅度（高低价差异不应过大）
            if high_price > 0:
                price_range_pct = (high_price - low_price) / high_price
                # 单日价格波动范围不应超过80%
                if price_range_pct > 0.8:
                    return False

            # 检查收盘价与开盘价的关系（单日涨跌幅不应过大）
            if open_price > 0:
                daily_change_pct = abs((close_price - open_price) / open_price)
                # 正常期货单日涨跌幅限制在30%以内
                if daily_change_pct > 0.3:
                    return False

            return True

        except Exception as e:
            logger.warning("价格合理性验证失败", error=str(e))
            return False

    async def validate_symbol(self, symbol: str) -> bool:
        """验证期货代码是否有效"""
        try:
            # 获取所有支持的品种
            symbols = await self.get_available_symbols()
            symbol_codes = [s.symbol for s in symbols]
            return symbol in symbol_codes
        except Exception as e:
            logger.error("验证期货代码失败", error=str(e), symbol=symbol)
            return False