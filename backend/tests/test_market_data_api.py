import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, date, timedelta
from fastapi.testclient import TestClient
from fastapi import FastAPI
import json

from app.api.v1.endpoints.market_data import router
from app.schemas.market_data import MarketDataResponse, SymbolResponse, RefreshDataRequest
from app.services.akshare_client import AKShareClient
from app.services.cache_service import CacheService
from app.utils.errors import APIError, ValidationError

# 创建测试应用
app = FastAPI()
app.include_router(router, prefix="/api/v1/market-data", tags=["market-data"])

@pytest.fixture
def client():
    """创建测试客户端"""
    return TestClient(app)

@pytest.fixture
def sample_market_data():
    """示例市场数据"""
    return [
        MarketDataResponse(
            symbol="CU",
            date=datetime(2023, 1, 1),
            open_price=100.0,
            high_price=105.0,
            low_price=95.0,
            close_price=104.0,
            volume=1000,
            turnover=104000.0,
            settlement_price=104.0,
            open_interest=5000
        ),
        MarketDataResponse(
            symbol="CU",
            date=datetime(2023, 1, 2),
            open_price=104.0,
            high_price=109.0,
            low_price=99.0,
            close_price=108.0,
            volume=1100,
            turnover=118800.0,
            settlement_price=108.0,
            open_interest=5200
        )
    ]

@pytest.fixture
def sample_symbols():
    """示例品种数据"""
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
            symbol="AL",
            name="铝",
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

class TestMarketDataAPI:
    """市场数据API集成测试"""

    @patch('app.api.v1.endpoints.market_data.AKShareClient')
    @patch('app.api.v1.endpoints.market_data.CacheService')
    def test_get_available_symbols_success(self, mock_cache_service_class, mock_akshare_client_class, client, sample_symbols):
        """测试成功获取可用品种列表"""
        # 设置mock
        mock_client = Mock()
        mock_client.get_available_symbols = AsyncMock(return_value=sample_symbols)
        mock_akshare_client_class.return_value = mock_client

        # 发送请求
        response = client.get("/api/v1/market-data/symbols")

        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) == 3
        assert data["data"][0]["symbol"] == "CU"
        assert data["data"][0]["name"] == "铜"
        assert data["data"][0]["sector"] == "metal"
        assert data["data"][2]["symbol"] == "SC"
        assert data["data"][2]["sector"] == "energy"

    @patch('app.api.v1.endpoints.market_data.AKShareClient')
    @patch('app.api.v1.endpoints.market_data.CacheService')
    def test_get_available_symbols_with_sector(self, mock_cache_service_class, mock_akshare_client_class, client, sample_symbols):
        """测试获取特定版块的品种列表"""
        # 设置mock，只返回金属版块
        metal_symbols = [s for s in sample_symbols if s.sector == "metal"]
        mock_client = Mock()
        mock_client.get_available_symbols = AsyncMock(return_value=metal_symbols)
        mock_akshare_client_class.return_value = mock_client

        # 发送请求
        response = client.get("/api/v1/market-data/symbols?sector=metal")

        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) == 2
        assert all(s["sector"] == "metal" for s in data["data"])
        mock_client.get_available_symbols.assert_called_once_with("metal")

    @patch('app.api.v1.endpoints.market_data.AKShareClient')
    @patch('app.api.v1.endpoints.market_data.CacheService')
    def test_get_available_symbols_api_error(self, mock_cache_service_class, mock_akshare_client_class, client):
        """测试获取品种列表时API错误"""
        # 设置mock抛出异常
        mock_client = Mock()
        mock_client.get_available_symbols.side_effect = APIError("获取品种列表失败")
        mock_akshare_client_class.return_value = mock_client

        # 发送请求
        response = client.get("/api/v1/market-data/symbols")

        # 验证响应
        assert response.status_code == 400
        data = response.json()
        assert "获取品种列表失败" in data["detail"]

    @patch('app.api.v1.endpoints.market_data.AKShareClient')
    @patch('app.api.v1.endpoints.market_data.CacheService')
    def test_get_market_data_history_from_cache(self, mock_cache_service_class, mock_akshare_client_class, client, sample_market_data):
        """测试从缓存获取历史数据"""
        # 设置mock
        mock_cache_service = Mock()
        mock_cache_service.get_market_data.return_value = sample_market_data
        mock_cache_service_class.return_value = mock_cache_service
        mock_client = Mock()
        mock_akshare_client_class.return_value = mock_client

        # 发送请求
        response = client.get("/api/v1/market-data/history?symbol=CU&start_date=2023-01-01&end_date=2023-01-02")

        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["symbol"] == "CU"
        assert data[0]["close_price"] == 104.0

        # 验证只调用了缓存，没有调用API
        mock_cache_service.get_market_data.assert_called_once()
        mock_client.get_market_data.assert_not_called()

    @patch('app.api.v1.endpoints.market_data.AKShareClient')
    @patch('app.api.v1.endpoints.market_data.CacheService')
    def test_get_market_data_history_from_api(self, mock_cache_service_class, mock_akshare_client_class, client, sample_market_data):
        """测试从API获取历史数据"""
        # 设置mock - 缓存未命中
        mock_cache_service = Mock()
        mock_cache_service.get_market_data.return_value = None
        mock_cache_service.set_market_data.return_value = True
        mock_cache_service_class.return_value = mock_cache_service

        mock_client = Mock()
        mock_client.get_market_data.return_value = sample_market_data
        mock_akshare_client_class.return_value = mock_client

        # 发送请求
        response = client.get("/api/v1/market-data/history?symbol=CU&start_date=2023-01-01&end_date=2023-01-02")

        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["symbol"] == "CU"

        # 验证调用了API和缓存设置
        mock_cache_service.get_market_data.assert_called_once()
        mock_client.get_market_data.assert_called_once()
        mock_cache_service.set_market_data.assert_called_once()

    @patch('app.api.v1.endpoints.market_data.AKShareClient')
    @patch('app.api.v1.endpoints.market_data.CacheService')
    def test_get_market_data_history_invalid_date_range(self, mock_cache_service_class, mock_akshare_client_class, client):
        """测试无效日期范围"""
        # 发送请求 - 结束日期早于开始日期
        response = client.get("/api/v1/market-data/history?symbol=CU&start_date=2023-01-05&end_date=2023-01-01")

        # 验证响应
        assert response.status_code == 400
        data = response.json()
        assert "开始日期不能晚于结束日期" in data["detail"]

    @patch('app.api.v1.endpoints.market_data.AKShareClient')
    @patch('app.api.v1.endpoints.market_data.CacheService')
    def test_get_market_data_history_date_range_too_long(self, mock_cache_service_class, mock_akshare_client_class, client):
        """测试日期范围过长"""
        # 发送请求 - 超过1年
        response = client.get("/api/v1/market-data/history?symbol=CU&start_date=2023-01-01&end_date=2024-01-02")

        # 验证响应
        assert response.status_code == 400
        data = response.json()
        assert "查询时间范围不能超过1年" in data["detail"]

    @patch('app.api.v1.endpoints.market_data.AKShareClient')
    @patch('app.api.v1.endpoints.market_data.CacheService')
    def test_get_market_data_history_api_error(self, mock_cache_service_class, mock_akshare_client_class, client):
        """测试获取历史数据时API错误"""
        # 设置mock - 缓存未命中，API调用失败
        mock_cache_service = Mock()
        mock_cache_service.get_market_data.return_value = None
        mock_cache_service_class.return_value = mock_cache_service

        mock_client = Mock()
        mock_client.get_market_data.side_effect = APIError("获取数据失败")
        mock_akshare_client_class.return_value = mock_client

        # 发送请求
        response = client.get("/api/v1/market-data/history?symbol=CU&start_date=2023-01-01&end_date=2023-01-02")

        # 验证响应
        assert response.status_code == 400
        data = response.json()
        assert "获取数据失败" in data["detail"]

    @patch('app.api.v1.endpoints.market_data.AKShareClient')
    @patch('app.api.v1.endpoints.market_data.CacheService')
    def test_refresh_market_data_success(self, mock_cache_service_class, mock_akshare_client_class, client, sample_market_data):
        """测试成功刷新数据"""
        # 设置mock
        mock_cache_service = Mock()
        mock_cache_service.delete_market_data.return_value = True
        mock_cache_service.set_market_data.return_value = True
        mock_cache_service_class.return_value = mock_cache_service

        mock_client = Mock()
        mock_client.get_market_data.return_value = sample_market_data
        mock_akshare_client_class.return_value = mock_client

        # 请求数据
        request_data = {
            "symbol": "CU",
            "start_date": "2023-01-01",
            "end_date": "2023-01-02"
        }

        # 发送请求
        response = client.post("/api/v1/market-data/refresh", json=request_data)

        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "CU" in data["message"]
        assert data["data_count"] == 2

        # 验证调用
        mock_cache_service.delete_market_data.assert_called_once_with("CU")
        mock_client.get_market_data.assert_called_once()
        mock_cache_service.set_market_data.assert_called_once()

    @patch('app.api.v1.endpoints.market_data.AKShareClient')
    @patch('app.api.v1.endpoints.market_data.CacheService')
    def test_refresh_market_data_default_dates(self, mock_cache_service_class, mock_akshare_client_class, client, sample_market_data):
        """测试刷新数据使用默认日期范围"""
        # 设置mock
        mock_cache_service = Mock()
        mock_cache_service.delete_market_data.return_value = True
        mock_cache_service.set_market_data.return_value = True
        mock_cache_service_class.return_value = mock_cache_service

        mock_client = Mock()
        mock_client.get_market_data.return_value = sample_market_data
        mock_akshare_client_class.return_value = mock_client

        # 请求数据 - 不提供日期，使用默认值
        request_data = {
            "symbol": "CU"
        }

        # 发送请求
        response = client.post("/api/v1/market-data/refresh", json=request_data)

        # 验证响应
        assert response.status_code == 200

        # 验证API调用使用了默认日期范围
        call_args = mock_client.get_market_data.call_args
        assert call_args[0][0] == "CU"
        assert isinstance(call_args[0][1], date)  # start_date
        assert isinstance(call_args[0][2], date)  # end_date

    @patch('app.api.v1.endpoints.market_data.AKShareClient')
    @patch('app.api.v1.endpoints.market_data.CacheService')
    def test_refresh_market_data_invalid_date_range(self, mock_cache_service_class, mock_akshare_client_class, client):
        """测试刷新数据时无效日期范围"""
        # 请求数据 - 结束日期早于开始日期
        request_data = {
            "symbol": "CU",
            "start_date": "2023-01-05",
            "end_date": "2023-01-01"
        }

        # 发送请求
        response = client.post("/api/v1/market-data/refresh", json=request_data)

        # 验证响应
        assert response.status_code == 422  # 验证错误

    @patch('app.api.v1.endpoints.market_data.AKShareClient')
    @patch('app.api.v1.endpoints.market_data.CacheService')
    def test_refresh_market_data_api_error(self, mock_cache_service_class, mock_akshare_client_class, client):
        """测试刷新数据时API错误"""
        # 设置mock
        mock_cache_service = Mock()
        mock_cache_service.delete_market_data.return_value = True
        mock_cache_service_class.return_value = mock_cache_service

        mock_client = Mock()
        mock_client.get_market_data.side_effect = APIError("获取数据失败")
        mock_akshare_client_class.return_value = mock_client

        # 请求数据
        request_data = {
            "symbol": "CU",
            "start_date": "2023-01-01",
            "end_date": "2023-01-02"
        }

        # 发送请求
        response = client.post("/api/v1/market-data/refresh", json=request_data)

        # 验证响应
        assert response.status_code == 400
        data = response.json()
        assert "刷新数据失败" in data["detail"]

    @patch('app.api.v1.endpoints.market_data.AKShareClient')
    @patch('app.api.v1.endpoints.market_data.CacheService')
    def test_get_supported_sectors(self, mock_cache_service_class, mock_akshare_client_class, client):
        """测试获取支持版块列表"""
        # 设置mock
        mock_client = Mock()
        mock_client.get_supported_sectors.return_value = ["energy", "metal", "agriculture", "chemical"]
        mock_akshare_client_class.return_value = mock_client

        # 发送请求
        response = client.get("/api/v1/market-data/sectors")

        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 4
        assert "energy" in data
        assert "metal" in data
        assert "agriculture" in data
        assert "chemical" in data

    @patch('app.api.v1.endpoints.market_data.AKShareClient')
    @patch('app.api.v1.endpoints.market_data.CacheService')
    def test_get_supported_sectors_error(self, mock_cache_service_class, mock_akshare_client_class, client):
        """测试获取支持版块列表时错误"""
        # 设置mock
        mock_client = Mock()
        mock_client.get_supported_sectors.side_effect = APIError("获取版块列表失败")
        mock_akshare_client_class.return_value = mock_client

        # 发送请求
        response = client.get("/api/v1/market-data/sectors")

        # 验证响应
        assert response.status_code == 400
        data = response.json()
        assert "获取版块列表失败" in data["detail"]

    def test_missing_required_parameters(self, client):
        """测试缺少必需参数"""
        # 测试获取历史数据缺少symbol参数
        response = client.get("/api/v1/market-data/history?start_date=2023-01-01&end_date=2023-01-02")
        assert response.status_code == 422

        # 测试获取历史数据缺少start_date参数
        response = client.get("/api/v1/market-data/history?symbol=CU&end_date=2023-01-02")
        assert response.status_code == 422

        # 测试获取历史数据缺少end_date参数
        response = client.get("/api/v1/market-data/history?symbol=CU&start_date=2023-01-01")
        assert response.status_code == 422

    def test_invalid_date_format(self, client):
        """测试无效日期格式"""
        # 测试无效日期格式
        response = client.get("/api/v1/market-data/history?symbol=CU&start_date=2023-13-01&end_date=2023-01-02")
        assert response.status_code == 422

    @patch('app.api.v1.endpoints.market_data.AKShareClient')
    @patch('app.api.v1.endpoints.market_data.CacheService')
    def test_concurrent_requests(self, mock_cache_service_class, mock_akshare_client_class, client, sample_market_data):
        """测试并发请求处理"""
        # 设置mock
        mock_cache_service = Mock()
        mock_cache_service.get_market_data.return_value = sample_market_data
        mock_cache_service_class.return_value = mock_cache_service
        mock_client = Mock()
        mock_akshare_client_class.return_value = mock_client

        # 模拟并发请求
        import threading
        import time

        results = []

        def make_request():
            response = client.get("/api/v1/market-data/history?symbol=CU&start_date=2023-01-01&end_date=2023-01-02")
            results.append(response.status_code)

        # 创建多个线程同时请求
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        # 验证所有请求都成功
        assert all(status == 200 for status in results)
        assert len(results) == 5

    @patch('app.api.v1.endpoints.market_data.AKShareClient')
    @patch('app.api.v1.endpoints.market_data.CacheService')
    def test_response_headers(self, mock_cache_service_class, mock_akshare_client_class, client, sample_market_data):
        """测试响应头"""
        # 设置mock
        mock_cache_service = Mock()
        mock_cache_service.get_market_data.return_value = sample_market_data
        mock_cache_service_class.return_value = mock_cache_service
        mock_client = Mock()
        mock_akshare_client_class.return_value = mock_client

        # 发送请求
        response = client.get("/api/v1/market-data/history?symbol=CU&start_date=2023-01-01&end_date=2023-01-02")

        # 验证响应头
        assert response.status_code == 200
        assert "application/json" in response.headers["content-type"]

if __name__ == "__main__":
    pytest.main([__file__])