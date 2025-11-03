import pytest
import asyncio
from datetime import date, datetime
from typing import List, Dict, Any
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.data_storage import DataStorageService
from app.services.data_processor import DataProcessor
from app.models.market_data import MarketData
from app.core.database import get_async_session, db_manager
from app.utils.errors import ProcessingError, APIError

@pytest.fixture
async def data_storage_service():
    """创建数据存储服务实例"""
    service = DataStorageService()
    return service

@pytest.fixture
async def sample_raw_data():
    """示例原始数据"""
    return [
        {
            'date': '2024-01-01',
            'open': 50000.0,
            'high': 51000.0,
            'low': 49000.0,
            'close': 50500.0,
            'volume': 10000,
            'turnover': 505000000.0,
            'open_interest': 50000
        },
        {
            'date': '2024-01-02',
            'open': 50500.0,
            'high': 51500.0,
            'low': 49500.0,
            'close': 51000.0,
            'volume': 12000,
            'turnover': 612000000.0,
            'open_interest': 52000
        }
    ]

@pytest.fixture
async def sample_market_data():
    """示例市场数据"""
    return [
        MarketData(
            symbol="CU",
            date=date(2024, 1, 1),
            open_price=50000.0,
            high_price=51000.0,
            low_price=49000.0,
            close_price=50500.0,
            volume=10000,
            turnover=505000000.0,
            settlement_price=50500.0,
            open_interest=50000
        ),
        MarketData(
            symbol="CU",
            date=date(2024, 1, 2),
            open_price=50500.0,
            high_price=51500.0,
            low_price=49500.0,
            close_price=51000.0,
            volume=12000,
            turnover=612000000.0,
            settlement_price=51000.0,
            open_interest=52000
        )
    ]

class TestDataProcessor:
    """数据处理器测试"""

    @pytest.fixture
    def data_processor(self):
        """创建数据处理器实例"""
        return DataProcessor()

    @pytest.mark.asyncio
    async def test_clean_and_validate_data_success(self, data_processor, sample_raw_data):
        """测试数据清洗成功情况"""
        symbol = "CU"

        result = await data_processor.clean_and_validate_data(sample_raw_data, symbol)

        assert len(result) == 2
        assert all(item.symbol == symbol for item in result)
        assert all(item.open_price > 0 for item in result)
        assert all(item.high_price >= item.low_price for item in result)

    @pytest.mark.asyncio
    async def test_clean_and_validate_data_empty(self, data_processor):
        """测试空数据处理"""
        symbol = "CU"
        result = await data_processor.clean_and_validate_data([], symbol)
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_clean_and_validate_data_invalid_prices(self, data_processor):
        """测试无效价格数据处理"""
        symbol = "CU"
        invalid_data = [
            {
                'date': '2024-01-01',
                'open': -1000.0,  # 负价格
                'high': 50000.0,
                'low': 49000.0,
                'close': 50500.0,
                'volume': 10000
            },
            {
                'date': '2024-01-02',
                'open': 50500.0,
                'high': 49000.0,  # high < low
                'low': 51500.0,   # low > high
                'close': 51000.0,
                'volume': 12000
            }
        ]

        result = await data_processor.clean_and_validate_data(invalid_data, symbol)

        # 应该过滤掉无效数据
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_standardize_columns(self, data_processor):
        """测试列名标准化"""
        import pandas as pd

        # 中英文混合列名
        df_data = {
            '日期': ['2024-01-01', '2024-01-02'],
            '开盘价': [50000.0, 50500.0],
            '最高价': [51000.0, 51500.0],
            '最低价': [49000.0, 49500.0],
            '收盘价': [50500.0, 51000.0],
            '成交量': [10000, 12000]
        }

        df = pd.DataFrame(df_data)
        result_df = data_processor._standardize_columns(df)

        expected_columns = ['date', 'open_price', 'high_price', 'low_price', 'close_price', 'volume']
        for col in expected_columns:
            assert col in result_df.columns

    def test_calculate_quality_score(self, data_processor):
        """测试质量评分计算"""
        import pandas as pd

        df_data = {
            'symbol': ['CU', 'CU'],
            'date': [date(2024, 1, 1), date(2024, 1, 2)],
            'open_price': [50000.0, 50500.0],
            'high_price': [51000.0, 51500.0],
            'low_price': [49000.0, 49500.0],
            'close_price': [50500.0, 51000.0],
            'volume': [10000, 12000]
        }

        df = pd.DataFrame(df_data)
        result_df = data_processor._calculate_quality_score(df)

        assert 'quality_score' in result_df.columns
        assert all(0 <= score <= 100 for score in result_df['quality_score'])

class TestDataStorageService:
    """数据存储服务测试"""

    @pytest.mark.asyncio
    async def test_store_market_data_success(self, data_storage_service, sample_raw_data):
        """测试存储市场数据成功"""
        symbol = "CU"

        with patch.object(data_storage_service.data_processor, 'clean_and_validate_data') as mock_clean:
            # Mock清洗后的数据
            mock_clean.return_value = await data_storage_service.data_processor.clean_and_validate_data(sample_raw_data, symbol)

            with patch('app.services.data_storage.get_async_session') as mock_session:
                # Mock数据库会话
                mock_session.return_value.__aenter__.return_value = MagicMock()
                mock_session.return_value.__aexit__.return_value = None

                with patch.object(data_storage_service, '_incremental_update') as mock_update:
                    mock_update.return_value = 2

                    new_count, quality_score = await data_storage_service.store_market_data(sample_raw_data, symbol)

                    assert new_count == 2
                    assert 0 <= quality_score <= 100

    @pytest.mark.asyncio
    async def test_store_market_data_empty(self, data_storage_service):
        """测试存储空数据"""
        symbol = "CU"

        new_count, quality_score = await data_storage_service.store_market_data([], symbol)

        assert new_count == 0
        assert quality_score == 0.0

    @pytest.mark.asyncio
    async def test_query_market_data_success(self, data_storage_service, sample_market_data):
        """测试查询市场数据成功"""
        symbol = "CU"
        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 2)

        with patch('app.services.data_storage.get_async_session') as mock_session:
            # Mock数据库查询结果
            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = [
                MagicMock(
                    symbol=item.symbol,
                    date=item.date,
                    open_price=item.open_price,
                    high_price=item.high_price,
                    low_price=item.low_price,
                    close_price=item.close_price,
                    volume=item.volume,
                    turnover=item.turnover,
                    settlement_price=item.settlement_price,
                    open_interest=item.open_interest
                )
                for item in sample_market_data
            ]

            mock_session.return_value.__aenter__.return_value.execute.return_value = mock_result
            mock_session.return_value.__aexit__.return_value = None

            result = await data_storage_service.query_market_data(symbol, start_date, end_date)

            assert len(result) == 2
            assert all(item.symbol == symbol for item in result)
            assert all(start_date <= item.date <= end_date for item in result)

    @pytest.mark.asyncio
    async def test_query_latest_data(self, data_storage_service, sample_market_data):
        """测试查询最新数据"""
        symbol = "CU"
        days = 30

        with patch.object(data_storage_service, 'query_market_data') as mock_query:
            mock_query.return_value = sample_market_data

            result = await data_storage_service.query_latest_data(symbol, days)

            assert len(result) == 2
            mock_query.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_data_statistics(self, data_storage_service):
        """测试获取数据统计"""
        symbol = "CU"

        with patch('app.services.data_storage.get_async_session') as mock_session:
            # Mock统计查询结果
            mock_session.return_value.__aenter__.return_value.execute.return_value.scalar.return_value = 100
            mock_session.return_value.__aenter__.return_value.execute.return_value.first.return_value = MagicMock(
                min_date=date(2024, 1, 1),
                max_date=date(2024, 12, 31)
            )
            mock_session.return_value.__aexit__.return_value = None

            stats = await data_storage_service.get_data_statistics(symbol)

            assert 'symbol' in stats
            assert 'total_records' in stats
            assert 'date_range' in stats
            assert stats['symbol'] == symbol

    @pytest.mark.asyncio
    async def test_delete_market_data(self, data_storage_service):
        """测试删除市场数据"""
        symbol = "CU"
        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 31)

        with patch('app.services.data_storage.get_async_session') as mock_session:
            # Mock删除操作
            mock_result = MagicMock()
            mock_result.rowcount = 5
            mock_session.return_value.__aenter__.return_value.execute.return_value = mock_result
            mock_session.return_value.__aenter__.return_value.commit = AsyncMock()
            mock_session.return_value.__aexit__.return_value = None

            deleted_count = await data_storage_service.delete_market_data(symbol, start_date, end_date)

            assert deleted_count == 5

    @pytest.mark.asyncio
    async def test_export_market_data_csv(self, data_storage_service, sample_market_data):
        """测试导出CSV格式数据"""
        symbol = "CU"
        format = "csv"

        with patch.object(data_storage_service, 'query_market_data') as mock_query:
            mock_query.return_value = sample_market_data

            result = await data_storage_service.export_market_data(symbol, format=format)

            assert isinstance(result, bytes)
            assert len(result) > 0
            # 检查CSV内容
            csv_content = result.decode('utf-8')
            assert 'symbol' in csv_content
            assert 'date' in csv_content
            assert symbol in csv_content

    @pytest.mark.asyncio
    async def test_export_market_data_json(self, data_storage_service, sample_market_data):
        """测试导出JSON格式数据"""
        symbol = "CU"
        format = "json"

        with patch.object(data_storage_service, 'query_market_data') as mock_query:
            mock_query.return_value = sample_market_data

            result = await data_storage_service.export_market_data(symbol, format=format)

            assert isinstance(result, bytes)
            assert len(result) > 0
            # 检查JSON内容
            import json
            json_content = json.loads(result.decode('utf-8'))
            assert isinstance(json_content, list)
            assert len(json_content) == 2

    @pytest.mark.asyncio
    async def test_sync_incremental_data(self, data_storage_service, sample_raw_data):
        """测试增量数据同步"""
        symbol = "CU"

        with patch.object(data_storage_service, 'query_symbols_latest_date') as mock_latest:
            with patch.object(data_storage_service, 'store_market_data') as mock_store:
                # Mock没有现有数据
                mock_latest.return_value = {symbol: None}
                mock_store.return_value = (2, 95.0)

                result = await data_storage_service.sync_incremental_data(symbol, sample_raw_data)

                assert result['symbol'] == symbol
                assert result['new_records'] == 2
                assert result['quality_score'] == 95.0
                assert 'sync_time' in result

    @pytest.mark.asyncio
    async def test_vacuum_database(self, data_storage_service):
        """测试数据库优化"""
        with patch('app.services.data_storage.get_async_session') as mock_session:
            mock_session.return_value.__aenter__.return_value.execute = AsyncMock()
            mock_session.return_value.__aenter__.return_value.commit = AsyncMock()
            mock_session.return_value.__aexit__.return_value = None

            result = await data_storage_service.vacuum_database()

            assert result is True

    @pytest.mark.asyncio
    async def test_get_storage_health_check(self, data_storage_service):
        """测试存储健康检查"""
        with patch.object(db_manager, 'check_connection') as mock_check:
            with patch.object(db_manager, 'get_database_info') as mock_info:
                with patch.object(data_storage_service, 'query_latest_data') as mock_query:
                    mock_check.return_value = True
                    mock_info.return_value = {
                        'database_url': 'sqlite:///test.db',
                        'market_data_stats': {
                            'total_records': 1000
                        }
                    }
                    mock_query.return_value = [MagicMock()] * 30  # 30条记录

                    health_info = await data_storage_service.get_storage_health_check()

                    assert 'timestamp' in health_info
                    assert 'database_connection' in health_info
                    assert 'data_quality' in health_info
                    assert 'storage_stats' in health_info
                    assert health_info['database_connection'] is True

class TestDatabaseManager:
    """数据库管理器测试"""

    @pytest.mark.asyncio
    async def test_get_database_info(self):
        """测试获取数据库信息"""
        with patch('app.core.database.get_async_session') as mock_session:
            # Mock查询结果
            mock_session.return_value.__aenter__.return_value.execute.return_value.fetchall.return_value = [
                ('market_data',), ('symbols',)
            ]
            mock_session.return_value.__aenter__.return_value.execute.return_value.scalar.return_value = 1000
            mock_session.return_value.__aexit__.return_value = None

            info = await db_manager.get_database_info()

            assert 'database_url' in info
            assert 'tables' in info
            assert 'market_data_stats' in info
            assert 'initialized' in info

    def test_check_connection(self):
        """测试数据库连接检查"""
        with patch('app.core.database.db_manager.sync_engine') as mock_engine:
            mock_connection = MagicMock()
            mock_engine.connect.return_value.__enter__.return_value.execute.return_value = None

            result = db_manager.check_connection()

            # 连接检查应该成功
            assert result is True

    @pytest.mark.asyncio
    async def test_backup_database(self):
        """测试数据库备份"""
        import tempfile
        from pathlib import Path

        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as temp_db:
            temp_db_path = temp_db.name

        # 创建测试数据库文件
        Path(temp_db_path).touch()

        backup_path = temp_db_path.replace('.db', '_backup.db')

        try:
            result = await db_manager.backup_database(backup_path)
            assert result is True
            assert Path(backup_path).exists()
        finally:
            # 清理测试文件
            for path in [temp_db_path, backup_path]:
                if Path(path).exists():
                    Path(path).unlink()

@pytest.mark.asyncio
async def test_integration_data_flow():
    """集成测试：完整数据流程"""
    # 创建服务实例
    storage_service = DataStorageService()

    # 模拟原始数据
    raw_data = [
        {
            'date': '2024-01-01',
            'open': 50000.0,
            'high': 51000.0,
            'low': 49000.0,
            'close': 50500.0,
            'volume': 10000
        }
    ]

    symbol = "CU"

    # 使用mock避免实际数据库操作
    with patch.object(storage_service, '_incremental_update') as mock_update:
        with patch.object(storage_service, 'query_market_data') as mock_query:
            mock_update.return_value = 1
            mock_query.return_value = [
                MarketData(
                    symbol=symbol,
                    date=date(2024, 1, 1),
                    open_price=50000.0,
                    high_price=51000.0,
                    low_price=49000.0,
                    close_price=50500.0,
                    volume=10000
                )
            ]

            # 存储数据
            new_count, quality_score = await storage_service.store_market_data(raw_data, symbol)
            assert new_count == 1
            assert quality_score > 0

            # 查询数据
            result = await storage_service.query_market_data(symbol, date(2024, 1, 1), date(2024, 1, 1))
            assert len(result) == 1
            assert result[0].symbol == symbol

if __name__ == "__main__":
    pytest.main([__file__, "-v"])