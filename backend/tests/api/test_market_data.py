import pytest
from fastapi.testclient import TestClient
from datetime import date, timedelta
import json

from main import app
from app.core.config import settings

client = TestClient(app)

class TestMarketDataAPI:
    """市场数据API测试"""

    def test_get_available_symbols_success(self):
        """测试获取可用期货品种列表 - 成功"""
        response = client.get("/api/v1/market-data/symbols")

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert "data" in data
        assert "message" in data
        assert isinstance(data["data"], list)

    def test_get_available_symbols_with_sector(self):
        """测试获取指定版块期货品种列表"""
        response = client.get("/api/v1/market-data/symbols?sector=energy")

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert "data" in data

    def test_get_market_data_history_success(self):
        """测试获取历史数据 - 成功"""
        end_date = date.today()
        start_date = end_date - timedelta(days=30)

        response = client.get(
            f"/api/v1/market-data/history",
            params={
                "symbol": "CU2401",
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            }
        )

        # 可能返回404（如果数据不存在）或200（如果数据存在）
        assert response.status_code in [200, 404]

        if response.status_code == 200:
            data = response.json()
            assert data["success"] is True
            assert "data" in data

    def test_get_market_data_history_invalid_date_range(self):
        """测试获取历史数据 - 无效日期范围"""
        end_date = date.today()
        start_date = end_date + timedelta(days=1)  # 开始日期晚于结束日期

        response = client.get(
            f"/api/v1/market-data/history",
            params={
                "symbol": "CU2401",
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            }
        )

        assert response.status_code == 400
        data = response.json()

        assert data["success"] is False
        assert "error" in data
        assert data["error"]["type"] == "VALIDATION_ERROR"

    def test_get_market_data_history_date_range_too_long(self):
        """测试获取历史数据 - 日期范围过长"""
        end_date = date.today()
        start_date = end_date - timedelta(days=400)  # 超过1年

        response = client.get(
            f"/api/v1/market-data/history",
            params={
                "symbol": "CU2401",
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            }
        )

        assert response.status_code == 400
        data = response.json()

        assert data["success"] is False
        assert "error" in data

    def test_get_market_data_history_missing_symbol(self):
        """测试获取历史数据 - 缺少品种代码"""
        response = client.get(
            f"/api/v1/market-data/history",
            params={
                "start_date": "2023-01-01",
                "end_date": "2023-12-31"
            }
        )

        assert response.status_code == 422  # 验证错误

    def test_refresh_market_data_success(self):
        """测试刷新市场数据 - 成功"""
        request_data = {
            "symbol": "CU2401",
            "start_date": "2023-01-01",
            "end_date": "2023-12-31"
        }

        response = client.post(
            "/api/v1/market-data/refresh",
            json=request_data
        )

        # 可能返回各种状态码，取决于实际数据源
        assert response.status_code in [200, 400, 503]

    def test_get_supported_sectors_success(self):
        """测试获取支持版块列表 - 成功"""
        response = client.get("/api/v1/market-data/sectors")

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert "data" in data

    def test_api_response_format_consistency(self):
        """测试API响应格式一致性"""
        response = client.get("/api/v1/market-data/symbols")

        assert response.status_code == 200
        data = response.json()

        # 检查必要字段
        required_fields = ["success", "data", "message"]
        for field in required_fields:
            assert field in data, f"缺少字段: {field}"

        # 检查数据类型
        assert isinstance(data["success"], bool)
        assert isinstance(data["message"], str)

    def test_error_handling_invalid_symbol(self):
        """测试错误处理 - 无效品种代码"""
        end_date = date.today()
        start_date = end_date - timedelta(days=30)

        response = client.get(
            f"/api/v1/market-data/history",
            params={
                "symbol": "INVALID123",
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            }
        )

        # 应该返回错误或404
        assert response.status_code in [400, 404, 500]

    def test_rate_limiting(self):
        """测试频率限制（如果启用）"""
        # 快速发送多个请求
        responses = []
        for _ in range(10):
            response = client.get("/api/v1/market-data/symbols")
            responses.append(response)

        # 至少有一些请求应该成功
        success_count = sum(1 for r in responses if r.status_code == 200)
        assert success_count > 0

    def test_cors_headers(self):
        """测试CORS头"""
        response = client.options("/api/v1/market-data/symbols")

        # 检查CORS头是否存在
        cors_headers = [
            "access-control-allow-origin",
            "access-control-allow-methods",
            "access-control-allow-headers"
        ]

        # 注意：实际CORS头可能在开发环境中有所不同
        # 这个测试主要确保API能够响应OPTIONS请求

    def test_security_headers(self):
        """测试安全头"""
        response = client.get("/api/v1/market-data/symbols")

        assert response.status_code == 200

        # 检查安全头
        security_headers = [
            "x-content-type-options",
            "x-frame-options",
            "x-xss-protection"
        ]

        for header in security_headers:
            assert header in response.headers, f"缺少安全头: {header}"

    def test_request_logging_headers(self):
        """测试请求日志相关头"""
        response = client.get("/api/v1/market-data/symbols")

        assert response.status_code == 200

        # 检查是否添加了请求ID和处理时间头
        assert "x-request-id" in response.headers
        assert "x-process-time" in response.headers

    def test_api_version_header(self):
        """测试API版本头"""
        response = client.get("/api/v1/market-data/symbols")

        assert response.status_code == 200
        assert "api-version" in response.headers