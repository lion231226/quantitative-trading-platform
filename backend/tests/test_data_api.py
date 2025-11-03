import pytest
import json
from datetime import date, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI

from app.api.v1.endpoints.data import router
from app.schemas.market_data import MarketDataResponse, DataQueryResponse
from app.services.data_storage import DataStorageService

@pytest.fixture
def app():
    """创建FastAPI测试应用"""
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    return app

@pytest.fixture
def client(app):
    """创建测试客户端"""
    return TestClient(app)

@pytest.fixture
def sample_market_data_response():
    """示例市场数据响应"""
    return [
        MarketDataResponse(
            symbol="CU",
            date=datetime(2024, 1, 1),
            open_price=50000.0,
            high_price=51000.0,
            low_price=49000.0,
            close_price=50500.0,
            volume=10000,
            turnover=505000000.0,
            settlement_price=50500.0,
            open_interest=50000
        ),
        MarketDataResponse(
            symbol="CU",
            date=datetime(2024, 1, 2),
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

class TestDataQueryEndpoints:
    """数据查询端点测试"""

    def test_query_market_data_success(self, client, sample_market_data_response):
        """测试查询市场数据成功"""
        symbol = "CU"
        start_date = "2024-01-01"
        end_date = "2024-01-02"

        with patch('app.api.v1.endpoints.data.data_storage_service') as mock_service:
            mock_service.query_market_data.return_value = [
                {
                    'symbol': item.symbol,
                    'date': item.date,
                    'open_price': item.open_price,
                    'high_price': item.high_price,
                    'low_price': item.low_price,
                    'close_price': item.close_price,
                    'volume': item.volume,
                    'turnover': item.turnover,
                    'settlement_price': item.settlement_price,
                    'open_interest': item.open_interest
                }
                for item in sample_market_data_response
            ]

            response = client.get(
                f"/api/v1/data/query?symbol={symbol}&start_date={start_date}&end_date={end_date}"
            )

            assert response.status_code == 200
            data = response.json()
            assert data['symbol'] == symbol
            assert data['total_count'] == 2
            assert len(data['data']) == 2
            assert data['data'][0]['symbol'] == symbol

    def test_query_market_data_missing_symbol(self, client):
        """测试查询市场数据缺少期货代码"""
        response = client.get("/api/v1/data/query")
        assert response.status_code == 422  # Validation error

    def test_query_market_data_invalid_date_format(self, client):
        """测试查询市场数据无效日期格式"""
        symbol = "CU"
        invalid_date = "invalid-date"

        response = client.get(f"/api/v1/data/query?symbol={symbol}&start_date={invalid_date}")
        assert response.status_code == 422

    def test_query_market_data_with_pagination(self, client, sample_market_data_response):
        """测试分页查询"""
        symbol = "CU"
        page = 1
        size = 10

        with patch('app.api.v1.endpoints.data.data_storage_service') as mock_service:
            mock_service.query_market_data.return_value = [
                {
                    'symbol': item.symbol,
                    'date': item.date,
                    'open_price': item.open_price,
                    'high_price': item.high_price,
                    'low_price': item.low_price,
                    'close_price': item.close_price,
                    'volume': item.volume,
                    'turnover': item.turnover,
                    'settlement_price': item.settlement_price,
                    'open_interest': item.open_interest
                }
                for item in sample_market_data_response[:1]
            ]

            response = client.get(
                f"/api/v1/data/query?symbol={symbol}&page={page}&size={size}"
            )

            assert response.status_code == 200
            data = response.json()
            assert data['page'] == page
            assert data['size'] == size
            assert data['total_count'] == 1

    def test_get_latest_data_success(self, client, sample_market_data_response):
        """测试获取最新数据成功"""
        symbol = "CU"
        days = 7

        with patch('app.api.v1.endpoints.data.data_storage_service') as mock_service:
            mock_service.query_latest_data.return_value = [
                {
                    'symbol': item.symbol,
                    'date': item.date,
                    'open_price': item.open_price,
                    'high_price': item.high_price,
                    'low_price': item.low_price,
                    'close_price': item.close_price,
                    'volume': item.volume,
                    'turnover': item.turnover,
                    'settlement_price': item.settlement_price,
                    'open_interest': item.open_interest
                }
                for item in sample_market_data_response
            ]

            response = client.get(f"/api/v1/data/latest/{symbol}?days={days}")

            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            assert len(data) == 2
            assert data[0]['symbol'] == symbol

    def test_get_latest_data_invalid_days(self, client):
        """测试获取最新数据无效天数"""
        symbol = "CU"
        invalid_days = 400  # 超过最大限制

        response = client.get(f"/api/v1/data/latest/{symbol}?days={invalid_days}")
        assert response.status_code == 422

    def test_get_data_statistics_success(self, client):
        """测试获取数据统计成功"""
        symbol = "CU"

        with patch('app.api.v1.endpoints.data.data_storage_service') as mock_service:
            mock_service.get_data_statistics.return_value = {
                'symbol': symbol,
                'total_records': 1000,
                'symbol_count': 1,
                'date_range': {
                    'start': '2024-01-01',
                    'end': '2024-12-31'
                }
            }

            response = client.get(f"/api/v1/data/statistics?symbol={symbol}")

            assert response.status_code == 200
            data = response.json()
            assert data['symbol'] == symbol
            assert data['total_records'] == 1000
            assert 'date_range' in data

    def test_get_storage_health_success(self, client):
        """测试存储健康检查成功"""
        with patch('app.api.v1.endpoints.data.data_storage_service') as mock_service:
            mock_service.get_storage_health_check.return_value = {
                'timestamp': datetime.utcnow().isoformat(),
                'database_connection': True,
                'data_quality': {},
                'storage_stats': {}
            }

            response = client.get("/api/v1/data/health")

            assert response.status_code == 200
            data = response.json()
            assert 'timestamp' in data
            assert 'database_connection' in data
            assert data['database_connection'] is True

class TestDataExportEndpoints:
    """数据导出端点测试"""

    def test_export_data_csv_success(self, client, sample_market_data_response):
        """测试导出CSV格式数据成功"""
        symbol = "CU"
        format = "csv"

        with patch('app.api.v1.endpoints.data.data_storage_service') as mock_service:
            mock_service.export_market_data.return_value = b"symbol,date,open_price\nCU,2024-01-01,50000.0"

            response = client.post(
                f"/api/v1/data/export/{symbol}?format={format}"
            )

            assert response.status_code == 200
            assert response.headers['content-type'] == 'text/csv; charset=utf-8'
            assert 'attachment;' in response.headers['content-disposition']
            assert b"symbol,date,open_price" in response.content

    def test_export_data_json_success(self, client, sample_market_data_response):
        """测试导出JSON格式数据成功"""
        symbol = "CU"
        format = "json"

        with patch('app.api.v1.endpoints.data.data_storage_service') as mock_service:
            mock_service.export_market_data.return_value = json.dumps([
                {
                    'symbol': item.symbol,
                    'date': item.date.isoformat(),
                    'open_price': item.open_price
                }
                for item in sample_market_data_response
            ]).encode('utf-8')

            response = client.post(
                f"/api/v1/data/export/{symbol}?format={format}"
            )

            assert response.status_code == 200
            assert response.headers['content-type'] == 'application/json'
            data = json.loads(response.content.decode('utf-8'))
            assert isinstance(data, list)
            assert len(data) == 2

    def test_export_data_excel_success(self, client, sample_market_data_response):
        """测试导出Excel格式数据成功"""
        symbol = "CU"
        format = "excel"

        with patch('app.api.v1.endpoints.data.data_storage_service') as mock_service:
            mock_service.export_market_data.return_value = b'fake_excel_content'

            response = client.post(
                f"/api/v1/data/export/{symbol}?format={format}"
            )

            assert response.status_code == 200
            assert 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' in response.headers['content-type']

    def test_export_data_invalid_format(self, client):
        """测试导出数据无效格式"""
        symbol = "CU"
        invalid_format = "xml"

        response = client.post(
            f"/api/v1/data/export/{symbol}?format={invalid_format}"
        )

        assert response.status_code == 422

    def test_export_data_no_data_found(self, client):
        """测试导出数据无数据"""
        symbol = "CU"

        with patch('app.api.v1.endpoints.data.data_storage_service') as mock_service:
            mock_service.export_market_data.return_value = b""

            response = client.post(f"/api/v1/data/export/{symbol}")

            assert response.status_code == 404

class DataSyncEndpoints:
    """数据同步端点测试"""

    def test_sync_incremental_data_success(self, client):
        """测试增量数据同步成功"""
        symbol = "CU"
        sync_data = [
            {
                'date': '2024-01-01',
                'open': 50000.0,
                'high': 51000.0,
                'low': 49000.0,
                'close': 50500.0,
                'volume': 10000
            }
        ]

        with patch('app.api.v1.endpoints.data.data_storage_service') as mock_service:
            mock_service.sync_incremental_data.return_value = {
                'symbol': symbol,
                'new_records': 1,
                'updated_records': 0,
                'quality_score': 95.0,
                'sync_time': datetime.utcnow().isoformat()
            }

            response = client.post(
                f"/api/v1/data/sync/{symbol}",
                json=sync_data
            )

            assert response.status_code == 200
            data = response.json()
            assert data['symbol'] == symbol
            assert data['new_records'] == 1
            assert data['quality_score'] == 95.0
            assert 'sync_time' in data

    def test_sync_incremental_data_empty(self, client):
        """测试增量数据同步空数据"""
        symbol = "CU"
        empty_data = []

        response = client.post(
            f"/api/v1/data/sync/{symbol}",
            json=empty_data
        )

        assert response.status_code == 400

class DataManagementEndpoints:
    """数据管理端点测试"""

    def test_delete_market_data_success(self, client):
        """测试删除市场数据成功"""
        symbol = "CU"
        start_date = "2024-01-01"
        end_date = "2024-01-31"

        with patch('app.api.v1.endpoints.data.data_storage_service') as mock_service:
            mock_service.delete_market_data.return_value = 5

            response = client.delete(
                f"/api/v1/data/{symbol}?start_date={start_date}&end_date={end_date}"
            )

            assert response.status_code == 200
            data = response.json()
            assert data['symbol'] == symbol
            assert data['deleted_count'] == 5

    def test_vacuum_database_success(self, client):
        """测试数据库优化成功"""
        with patch('app.api.v1.endpoints.data.data_storage_service') as mock_service:
            mock_service.vacuum_database.return_value = True

            response = client.post("/api/v1/data/vacuum")

            assert response.status_code == 200
            data = response.json()
            assert data['success'] is True
            assert 'message' in data

    def test_get_data_quality_report_success(self, client):
        """测试获取数据质量报告成功"""
        symbol = "CU"

        with patch('app.api.v1.endpoints.data.data_storage_service') as mock_service:
            with patch('app.api.v1.endpoints.data.data_processor') as mock_processor:
                mock_service.query_latest_data.return_value = [MagicMock()] * 30
                mock_processor.get_data_quality_report.return_value = {
                    'symbol': symbol,
                    'total_records': 30,
                    'quality_score': 95.5,
                    'issues': []
                }

                response = client.get(f"/api/v1/data/quality/{symbol}")

                assert response.status_code == 200
                data = response.json()
                assert data['symbol'] == symbol
                assert data['quality_score'] == 95.5

    def test_get_data_quality_report_no_data(self, client):
        """测试获取数据质量报告无数据"""
        symbol = "CU"

        with patch('app.api.v1.endpoints.data.data_storage_service') as mock_service:
            mock_service.query_latest_data.return_value = []

            response = client.get(f"/api/v1/data/quality/{symbol}")

            assert response.status_code == 200
            data = response.json()
            assert data['symbol'] == symbol
            assert data['quality_score'] == 0.0
            assert 'message' in data

    def test_get_symbols_latest_dates_success(self, client):
        """测试获取多个品种最新日期成功"""
        symbols = "CU,AL,ZN"

        with patch('app.api.v1.endpoints.data.data_storage_service') as mock_service:
            mock_service.query_symbols_latest_date.return_value = {
                'CU': date(2024, 1, 15),
                'AL': date(2024, 1, 14),
                'ZN': date(2024, 1, 16)
            }

            response = client.get(f"/api/v1/data/symbols/latest?symbols={symbols}")

            assert response.status_code == 200
            data = response.json()
            assert 'symbols' in data
            assert 'latest_dates' in data
            assert len(data['latest_dates']) == 3

    def test_get_symbols_latest_dates_empty_symbols(self, client):
        """测试获取最新日期空品种列表"""
        symbols = ""

        response = client.get(f"/api/v1/data/symbols/latest?symbols={symbols}")

        assert response.status_code == 400

class TestErrorHandling:
    """错误处理测试"""

    def test_service_error_handling(self, client):
        """测试服务错误处理"""
        symbol = "CU"

        with patch('app.api.v1.endpoints.data.data_storage_service') as mock_service:
            from app.utils.errors import APIError
            mock_service.query_market_data.side_effect = APIError("服务错误")

            response = client.get(f"/api/v1/data/query?symbol={symbol}")

            assert response.status_code == 500

    def test_validation_error_handling(self, client):
        """测试验证错误处理"""
        symbol = "CU"

        with patch('app.api.v1.endpoints.data.data_storage_service') as mock_service:
            from app.utils.errors import ValidationError
            mock_service.query_market_data.side_effect = ValidationError("验证错误")

            response = client.get(f"/api/v1/data/query?symbol={symbol}")

            assert response.status_code == 400

    def test_unexpected_error_handling(self, client):
        """测试意外错误处理"""
        symbol = "CU"

        with patch('app.api.v1.endpoints.data.data_storage_service') as mock_service:
            mock_service.query_market_data.side_effect = Exception("意外错误")

            response = client.get(f"/api/v1/data/query?symbol={symbol}")

            assert response.status_code == 500

@pytest.mark.asyncio
async def test_api_integration():
    """API集成测试"""
    # 这个测试可以用来验证整个API的工作流程
    # 在实际测试中，可能需要使用真实的数据存储服务
    pass

if __name__ == "__main__":
    pytest.main([__file__, "-v"])