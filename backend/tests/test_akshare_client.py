import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, date, timedelta
import pandas as pd
from app.services.akshare_client import AKShareClient
from app.schemas.market_data import MarketDataResponse, SymbolResponse
from app.utils.errors import APIError, ValidationError

@pytest.fixture
def akshare_client():
    """创建AKShare客户端实例"""
    return AKShareClient()

@pytest.fixture
def sample_market_data_df():
    """示例市场数据DataFrame"""
    return pd.DataFrame({
        'date': pd.date_range('2023-01-01', periods=5, freq='D'),
        'open': [100.0, 101.0, 102.0, 103.0, 104.0],
        'high': [105.0, 106.0, 107.0, 108.0, 109.0],
        'low': [95.0, 96.0, 97.0, 98.0, 99.0],
        'close': [104.0, 105.0, 106.0, 107.0, 108.0],
        'volume': [1000, 1100, 1200, 1300, 1400],
        'turnover': [104000.0, 115500.0, 127200.0, 139100.0, 151200.0]
    })

@pytest.fixture
def sample_symbol_responses():
    """示例品种响应列表"""
    return [
        SymbolResponse(
            symbol="CU",
            name="铜",
            exchange="SHFE",
            sector="metal",
            contract_size=5,
            trading_unit="手",
            price_quote="元/吨",
            min_price_change=10,
            is_active=True
        ),
        SymbolResponse(
            symbol="SC",
            name="原油",
            exchange="INE",
            sector="energy",
            contract_size=1000,
            trading_unit="手",
            price_quote="元/桶",
            min_price_change=0.1,
            is_active=True
        )
    ]

class TestAKShareClient:
    """AKShare客户端测试"""

    @pytest.mark.asyncio
    async def test_get_supported_sectors(self, akshare_client):
        """测试获取支持的版块列表"""
        sectors = await akshare_client.get_supported_sectors()

        assert isinstance(sectors, list)
        assert "energy" in sectors
        assert "metal" in sectors
        assert "agriculture" in sectors
        assert "chemical" in sectors
        assert len(sectors) == 4

    @pytest.mark.asyncio
    async def test_get_available_symbols_all_sectors(self, akshare_client):
        """测试获取所有版块的期货品种"""
        with patch.object(akshare_client, '_get_energy_symbols', new_callable=AsyncMock) as mock_energy, \
             patch.object(akshare_client, '_get_metal_symbols', new_callable=AsyncMock) as mock_metal, \
             patch.object(akshare_client, '_get_agriculture_symbols', new_callable=AsyncMock) as mock_agri, \
             patch.object(akshare_client, '_get_chemical_symbols', new_callable=AsyncMock) as mock_chem:

            # 设置mock返回值
            mock_energy.return_value = [SymbolResponse(symbol="SC", name="原油", exchange="INE", sector="energy")]
            mock_metal.return_value = [SymbolResponse(symbol="CU", name="铜", exchange="SHFE", sector="metal")]
            mock_agri.return_value = [SymbolResponse(symbol="C", name="玉米", exchange="DCE", sector="agriculture")]
            mock_chem.return_value = [SymbolResponse(symbol="TA", name="PTA", exchange="CZCE", sector="chemical")]

            symbols = await akshare_client.get_available_symbols()

            assert len(symbols) == 4
            assert any(s.symbol == "SC" for s in symbols)
            assert any(s.symbol == "CU" for s in symbols)
            assert any(s.symbol == "C" for s in symbols)
            assert any(s.symbol == "TA" for s in symbols)

    @pytest.mark.asyncio
    async def test_get_available_symbols_specific_sector(self, akshare_client):
        """测试获取特定版块的期货品种"""
        with patch.object(akshare_client, '_get_metal_symbols', new_callable=AsyncMock) as mock_metal:
            mock_metal.return_value = [
                SymbolResponse(symbol="CU", name="铜", exchange="SHFE", sector="metal"),
                SymbolResponse(symbol="AL", name="铝", exchange="SHFE", sector="metal")
            ]

            symbols = await akshare_client.get_available_symbols(sector="metal")

            assert len(symbols) == 2
            assert all(s.sector == "metal" for s in symbols)
            mock_metal.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_metal_symbols(self, akshare_client):
        """测试获取金属版块品种"""
        symbols = await akshare_client._get_metal_symbols()

        assert isinstance(symbols, list)
        assert len(symbols) > 0

        # 检查是否包含常见金属品种
        symbol_codes = [s.symbol for s in symbols]
        assert "CU" in symbol_codes  # 铜
        assert "AL" in symbol_codes  # 铝

        # 检查字段完整性
        for symbol in symbols:
            assert symbol.symbol is not None
            assert symbol.name is not None
            assert symbol.exchange is not None
            assert symbol.sector == "metal"
            assert symbol.is_active is True

    @pytest.mark.asyncio
    async def test_get_energy_symbols(self, akshare_client):
        """测试获取能源版块品种"""
        symbols = await akshare_client._get_energy_symbols()

        assert isinstance(symbols, list)

        # 检查字段完整性
        for symbol in symbols:
            assert symbol.symbol is not None
            assert symbol.name is not None
            assert symbol.exchange is not None
            assert symbol.sector == "energy"

    @pytest.mark.asyncio
    async def test_get_agriculture_symbols(self, akshare_client):
        """测试获取农产品版块品种"""
        symbols = await akshare_client._get_agriculture_symbols()

        assert isinstance(symbols, list)
        assert len(symbols) > 0

        # 检查是否包含常见农产品品种
        symbol_codes = [s.symbol for s in symbols]
        assert "C" in symbol_codes  # 玉米
        assert "M" in symbol_codes  # 豆粕

        # 检查字段完整性
        for symbol in symbols:
            assert symbol.sector == "agriculture"

    @pytest.mark.asyncio
    async def test_get_chemical_symbols(self, akshare_client):
        """测试获取化工版块品种"""
        symbols = await akshare_client._get_chemical_symbols()

        assert isinstance(symbols, list)
        assert len(symbols) > 0

        # 检查是否包含常见化工品种
        symbol_codes = [s.symbol for s in symbols]
        assert "TA" in symbol_codes  # PTA
        assert "MA" in symbol_codes  # 甲醇

        # 检查字段完整性
        for symbol in symbols:
            assert symbol.sector == "chemical"

    @pytest.mark.asyncio
    async def test_determine_exchange_and_contract(self, akshare_client):
        """测试确定交易所和合约代码"""
        # 测试上海期货交易所
        exchange, contract = await akshare_client._determine_exchange_and_contract("CU")
        assert exchange == "SHFE"
        assert contract == "CU0"

        # 测试大连商品交易所
        exchange, contract = await akshare_client._determine_exchange_and_contract("C")
        assert exchange == "DCE"
        assert contract == "C0"

        # 测试郑州商品交易所
        exchange, contract = await akshare_client._determine_exchange_and_contract("TA")
        assert exchange == "CZCE"
        assert contract == "TA0"

        # 测试上海国际能源交易中心
        exchange, contract = await akshare_client._determine_exchange_and_contract("SC")
        assert exchange == "INE"
        assert contract == "SC0"

    @pytest.mark.asyncio
    async def test_fetch_futures_data(self, akshare_client, sample_market_data_df):
        """测试从AKShare获取期货数据"""
        with patch('app.services.akshare_client.ak.futures_main_sina') as mock_akshare:
            mock_akshare.return_value = sample_market_data_df

            start_date = date(2023, 1, 1)
            end_date = date(2023, 1, 5)

            df = await akshare_client._fetch_futures_data("SHFE", "CU0", start_date, end_date)

            assert not df.empty
            assert len(df) == 5
            assert 'date' in df.columns
            assert 'open' in df.columns
            assert 'close' in df.columns
            assert 'volume' in df.columns

    @pytest.mark.asyncio
    async def test_clean_dataframe(self, akshare_client):
        """测试数据清洗"""
        # 创建包含中文列名的测试数据
        df = pd.DataFrame({
            '日期': ['2023-01-01', '2023-01-02'],
            '开盘价': [100.0, 101.0],
            '最高价': [105.0, 106.0],
            '最低价': [95.0, 96.0],
            '收盘价': [104.0, 105.0],
            '成交量': [1000, 1100]
        })

        start_date = date(2023, 1, 1)
        end_date = date(2023, 1, 5)

        cleaned_df = await akshare_client._clean_dataframe(df, start_date, end_date)

        # 检查列名转换
        assert 'date' in cleaned_df.columns
        assert 'open' in cleaned_df.columns
        assert 'high' in cleaned_df.columns
        assert 'low' in cleaned_df.columns
        assert 'close' in cleaned_df.columns
        assert 'volume' in cleaned_df.columns

        # 检查数据类型
        assert pd.api.types.is_datetime64_any_dtype(cleaned_df['date'])
        assert pd.api.types.is_numeric_dtype(cleaned_df['open'])
        assert pd.api.types.is_numeric_dtype(cleaned_df['close'])
        assert pd.api.types.is_numeric_dtype(cleaned_df['volume'])

    @pytest.mark.asyncio
    async def test_convert_dataframe_to_market_data(self, akshare_client):
        """测试将DataFrame转换为市场数据"""
        df = pd.DataFrame({
            'date': pd.date_range('2023-01-01', periods=3, freq='D'),
            'open': [100.0, 101.0, 102.0],
            'high': [105.0, 106.0, 107.0],
            'low': [95.0, 96.0, 97.0],
            'close': [104.0, 105.0, 106.0],
            'volume': [1000, 1100, 1200],
            'turnover': [104000.0, 115500.0, 127200.0]
        })

        market_data_list = await akshare_client._convert_dataframe_to_market_data(df, "CU")

        assert len(market_data_list) == 3
        assert all(isinstance(item, MarketDataResponse) for item in market_data_list)
        assert all(item.symbol == "CU" for item in market_data_list)

        # 检查第一条数据
        first_item = market_data_list[0]
        assert first_item.open_price == 100.0
        assert first_item.high_price == 105.0
        assert first_item.low_price == 95.0
        assert first_item.close_price == 104.0
        assert first_item.volume == 1000

    @pytest.mark.asyncio
    async def test_get_market_data_success(self, akshare_client, sample_market_data_df):
        """测试成功获取市场数据"""
        with patch.object(akshare_client, '_fetch_futures_data', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = sample_market_data_df

            start_date = date(2023, 1, 1)
            end_date = date(2023, 1, 5)

            market_data = await akshare_client.get_market_data("CU", start_date, end_date)

            assert len(market_data) == 5
            assert all(isinstance(item, MarketDataResponse) for item in market_data)
            assert all(item.symbol == "CU" for item in market_data)

    @pytest.mark.asyncio
    async def test_get_market_data_invalid_date_range(self, akshare_client):
        """测试无效日期范围"""
        start_date = date(2023, 1, 5)
        end_date = date(2023, 1, 1)  # 结束日期早于开始日期

        with pytest.raises(ValidationError, match="开始日期不能晚于结束日期"):
            await akshare_client.get_market_data("CU", start_date, end_date)

    @pytest.mark.asyncio
    async def test_get_market_data_date_range_too_long(self, akshare_client):
        """测试日期范围过长"""
        start_date = date(2023, 1, 1)
        end_date = date(2024, 1, 2)  # 超过1年

        with pytest.raises(ValidationError, match="查询时间范围不能超过1年"):
            await akshare_client.get_market_data("CU", start_date, end_date)

    @pytest.mark.asyncio
    async def test_get_market_data_no_data(self, akshare_client):
        """测试无数据情况"""
        with patch.object(akshare_client, '_fetch_futures_data', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = pd.DataFrame()  # 空DataFrame

            start_date = date(2023, 1, 1)
            end_date = date(2023, 1, 5)

            market_data = await akshare_client.get_market_data("CU", start_date, end_date)

            assert market_data == []

    @pytest.mark.asyncio
    async def test_validate_symbol_valid(self, akshare_client):
        """测试有效品种代码验证"""
        with patch.object(akshare_client, 'get_available_symbols', new_callable=AsyncMock) as mock_symbols:
            mock_symbols.return_value = [
                SymbolResponse(symbol="CU", name="铜", exchange="SHFE", sector="metal"),
                SymbolResponse(symbol="AL", name="铝", exchange="SHFE", sector="metal")
            ]

            is_valid = await akshare_client.validate_symbol("CU")
            assert is_valid is True

    @pytest.mark.asyncio
    async def test_validate_symbol_invalid(self, akshare_client):
        """测试无效品种代码验证"""
        with patch.object(akshare_client, 'get_available_symbols', new_callable=AsyncMock) as mock_symbols:
            mock_symbols.return_value = [
                SymbolResponse(symbol="CU", name="铜", exchange="SHFE", sector="metal"),
                SymbolResponse(symbol="AL", name="铝", exchange="SHFE", sector="metal")
            ]

            is_valid = await akshare_client.validate_symbol("INVALID")
            assert is_valid is False

    @pytest.mark.asyncio
    async def test_retry_decorator_success(self, akshare_client):
        """测试重试装饰器成功情况"""
        from app.services.akshare_client import retry_on_failure
        call_count = 0

        @retry_on_failure(max_retries=3, delay=0.1)
        async def test_function():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise APIError("模拟失败")
            return "success"

        result = await test_function()
        assert result == "success"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_retry_decorator_max_retries(self, akshare_client):
        """测试重试装饰器达到最大重试次数"""
        from app.services.akshare_client import retry_on_failure

        @retry_on_failure(max_retries=2, delay=0.1)
        async def test_function():
            raise APIError("总是失败")

        with pytest.raises(APIError, match="总是失败"):
            await test_function()

    def test_sector_mapping(self, akshare_client):
        """测试版块映射"""
        assert akshare_client.SECTOR_MAPPING["energy"] == "能源"
        assert akshare_client.SECTOR_MAPPING["metal"] == "金属"
        assert akshare_client.SECTOR_MAPPING["agriculture"] == "农产品"
        assert akshare_client.SECTOR_MAPPING["chemical"] == "化工"

    def test_exchange_mapping(self, akshare_client):
        """测试交易所映射"""
        assert akshare_client.EXCHANGE_MAPPING["SHFE"] == "上海期货交易所"
        assert akshare_client.EXCHANGE_MAPPING["DCE"] == "大连商品交易所"
        assert akshare_client.EXCHANGE_MAPPING["CZCE"] == "郑州商品交易所"
        assert akshare_client.EXCHANGE_MAPPING["CFFEX"] == "中国金融期货交易所"
        assert akshare_client.EXCHANGE_MAPPING["INE"] == "上海国际能源交易中心"

if __name__ == "__main__":
    pytest.main([__file__])