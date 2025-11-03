import pytest
import asyncio
from typing import Generator
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import tempfile
import os

from main import app
from app.core.config import settings

# 设置测试环境
os.environ["TESTING"] = "true"

@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """创建事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def client() -> Generator:
    """创建测试客户端"""
    with TestClient(app) as c:
        yield c

@pytest.fixture
def temp_db() -> Generator:
    """创建临时数据库"""
    # 创建临时文件
    db_fd, db_path = tempfile.mkstemp(suffix=".db")

    # 更新数据库URL
    original_url = settings.DATABASE_URL
    settings.DATABASE_URL = f"sqlite:///{db_path}"

    yield db_path

    # 清理
    os.close(db_fd)
    os.unlink(db_path)
    settings.DATABASE_URL = original_url

@pytest.fixture
def mock_redis():
    """模拟Redis连接"""
    import redis
    from unittest.mock import MagicMock

    mock_client = MagicMock()
    mock_client.ping.return_value = True
    mock_client.get.return_value = None
    mock_client.set.return_value = True
    mock_client.delete.return_value = 1

    return mock_client

@pytest.fixture
def sample_market_data():
    """示例市场数据"""
    return [
        {
            "symbol": "CU2401",
            "date": "2023-01-01",
            "open_price": 65000.0,
            "high_price": 65500.0,
            "low_price": 64800.0,
            "close_price": 65200.0,
            "volume": 10000
        },
        {
            "symbol": "CU2401",
            "date": "2023-01-02",
            "open_price": 65200.0,
            "high_price": 65800.0,
            "low_price": 65100.0,
            "close_price": 65700.0,
            "volume": 12000
        }
    ]

@pytest.fixture
def sample_strategy_params():
    """示例策略参数"""
    return {
        "ma_period": 20,
        "initial_capital": 100000,
        "stop_loss": 0.05
    }

@pytest.fixture
def sample_performance_metrics():
    """示例绩效指标"""
    return {
        "total_return": 0.15,
        "max_drawdown": 0.08,
        "sharpe_ratio": 1.2,
        "win_rate": 0.6,
        "profit_loss_ratio": 1.5,
        "total_trades": 25,
        "winning_trades": 15,
        "losing_trades": 10
    }

@pytest.fixture
def mock_akshare_response():
    """模拟AKShare API响应"""
    return {
        "日期": ["2023-01-01", "2023-01-02", "2023-01-03"],
        "开盘": [65000, 65200, 65700],
        "最高": [65500, 65800, 66000],
        "最低": [64800, 65100, 65500],
        "收盘": [65200, 65700, 65900],
        "成交量": [10000, 12000, 11000]
    }

# 测试标记
pytest_plugins = []

def pytest_configure(config):
    """配置pytest标记"""
    config.addinivalue_line(
        "markers", "unit: 标记单元测试"
    )
    config.addinivalue_line(
        "markers", "integration: 标记集成测试"
    )
    config.addinivalue_line(
        "markers", "slow: 标记慢测试"
    )
    config.addinivalue_line(
        "markers", "external: 标记需要外部服务的测试"
    )

@pytest.fixture(autouse=True)
def setup_test_environment():
    """设置测试环境"""
    # 在每个测试前设置
    original_testing = settings.TESTING
    settings.TESTING = True

    yield

    # 在每个测试后清理
    settings.TESTING = original_testing

@pytest.fixture
def mock_logger():
    """模拟日志记录器"""
    from unittest.mock import MagicMock
    import structlog

    mock_logger = MagicMock(spec=structlog.BoundLogger)
    mock_logger.info.return_value = None
    mock_logger.error.return_value = None
    mock_logger.warning.return_value = None
    mock_logger.debug.return_value = None

    return mock_logger