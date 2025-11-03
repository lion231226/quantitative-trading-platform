import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
from typing import Generator, AsyncGenerator
from fastapi.testclient import TestClient
from fastapi import FastAPI

@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """创建事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def client() -> TestClient:
    """创建测试客户端"""
    # 创建一个简单的测试应用
    test_app = FastAPI()

    # 导入并注册路由
    try:
        from app.api.v1.endpoints import market_data
        test_app.include_router(market_data.router, prefix="/api/v1/market-data")
    except ImportError:
        # 如果导入失败，返回一个空的应用
        pass

    return TestClient(test_app)

@pytest.fixture
def mock_akshare_client() -> Mock:
    """模拟AKShare客户端"""
    mock_client = Mock()
    mock_client.__class__.__name__ = "AKShareClient"

    # 设置常用的异步方法
    mock_client.get_supported_sectors = AsyncMock(return_value=["energy", "metal", "agriculture", "chemical"])
    mock_client.get_available_symbols = AsyncMock(return_value=[])
    mock_client.get_market_data = AsyncMock(return_value=[])
    mock_client.validate_symbol = AsyncMock(return_value=True)

    return mock_client

@pytest.fixture
def mock_cache_service() -> Mock:
    """模拟缓存服务"""
    mock_service = Mock()
    mock_service.__class__.__name__ = "CacheService"

    # 设置常用的异步方法
    mock_service.get_market_data = AsyncMock(return_value=None)
    mock_service.set_market_data = AsyncMock(return_value=True)
    mock_service.get_symbols = AsyncMock(return_value=None)
    mock_service.set_symbols = AsyncMock(return_value=True)
    mock_service.delete_market_data = AsyncMock(return_value=True)
    mock_service.clear_all_cache = AsyncMock(return_value=True)
    mock_service.get_cache_stats = AsyncMock(return_value={"cache_type": "redis", "total_keys": 0})

    return mock_service

@pytest.fixture
def sample_market_data():
    """示例市场数据"""
    from datetime import datetime

    return [
        {
            "symbol": "CU",
            "date": datetime(2023, 1, 1),
            "open_price": 100.0,
            "high_price": 105.0,
            "low_price": 95.0,
            "close_price": 104.0,
            "volume": 1000,
            "turnover": 104000.0,
            "settlement_price": 104.0,
            "open_interest": 5000
        },
        {
            "symbol": "CU",
            "date": datetime(2023, 1, 2),
            "open_price": 104.0,
            "high_price": 109.0,
            "low_price": 99.0,
            "close_price": 108.0,
            "volume": 1100,
            "turnover": 118800.0,
            "settlement_price": 108.0,
            "open_interest": 5200
        }
    ]

@pytest.fixture
def sample_symbols():
    """示例品种数据"""
    return [
        {
            "symbol": "CU",
            "name": "铜",
            "exchange": "SHFE",
            "sector": "metal",
            "contract_size": 5,
            "trading_unit": "手",
            "price_quote": "元/吨",
            "min_price_change": 10,
            "is_active": True
        },
        {
            "symbol": "AL",
            "name": "铝",
            "exchange": "SHFE",
            "sector": "metal",
            "contract_size": 5,
            "trading_unit": "手",
            "price_quote": "元/吨",
            "min_price_change": 10,
            "is_active": True
        },
        {
            "symbol": "SC",
            "name": "原油",
            "exchange": "INE",
            "sector": "energy",
            "contract_size": 1000,
            "trading_unit": "手",
            "price_quote": "元/桶",
            "min_price_change": 0.1,
            "is_active": True
        }
    ]

@pytest.fixture
def mock_redis():
    """模拟Redis客户端"""
    import redis
    with pytest.MonkeyPatch().context() as m:
        mock_redis_client = Mock()
        mock_redis_client.ping.return_value = True
        mock_redis_client.get.return_value = None
        mock_redis_client.setex.return_value = True
        mock_redis_client.delete.return_value = 1
        mock_redis_client.keys.return_value = []
        mock_redis_client.flushdb.return_value = True
        mock_redis_client.info.return_value = {
            'used_memory_human': '1M',
            'connected_clients': 1,
            'uptime_in_seconds': 3600
        }
        mock_redis_client.dbsize.return_value = 0
        mock_redis_client.ttl.return_value = 3600
        mock_redis_client.exists.return_value = 0

        m.setattr(redis, "Redis", lambda **kwargs: mock_redis_client)
        yield mock_redis_client

# 测试标记
def pytest_configure(config):
    """配置pytest标记"""
    config.addinivalue_line(
        "markers", "unit: 标记单元测试"
    )
    config.addinivalue_line(
        "markers", "integration: 标记集成测试"
    )
    config.addinivalue_line(
        "markers", "slow: 标记慢速测试"
    )
    config.addinivalue_line(
        "markers", "external_api: 标记需要外部API的测试"
    )

# 异步测试支持
@pytest.fixture(scope="function")
async def async_test_setup():
    """异步测试设置"""
    # 这里可以添加异步测试前的设置
    yield
    # 这里可以添加异步测试后的清理

# 跳过条件
def pytest_collection_modifyitems(config, items):
    """修改测试收集"""
    # 跳过需要外部API的测试，除非指定--run-external-api
    if not config.getoption("--run-external-api"):
        skip_external = pytest.mark.skip(reason="需要--run-external-api选项来运行外部API测试")
        for item in items:
            if "external_api" in item.keywords:
                item.add_marker(skip_external)

    # 跳过慢速测试，除非指定--run-slow
    if not config.getoption("--run-slow"):
        skip_slow = pytest.mark.skip(reason="需要--run-slow选项来运行慢速测试")
        for item in items:
            if "slow" in item.keywords:
                item.add_marker(skip_slow)

def pytest_addoption(parser):
    """添加pytest选项"""
    parser.addoption(
        "--run-external-api",
        action="store_true",
        default=False,
        help="运行需要外部API的测试"
    )
    parser.addoption(
        "--run-slow",
        action="store_true",
        default=False,
        help="运行慢速测试"
    )