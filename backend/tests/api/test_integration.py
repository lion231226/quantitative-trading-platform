import pytest
from fastapi.testclient import TestClient
from datetime import date, timedelta
import json
import uuid

from main import app

client = TestClient(app)

class TestAPIIntegration:
    """API集成测试"""

    def test_complete_market_data_workflow(self):
        """测试完整的市场数据工作流程"""
        # 1. 获取支持的版块
        sectors_response = client.get("/api/v1/market-data/sectors")
        assert sectors_response.status_code == 200

        # 2. 获取可用品种列表
        symbols_response = client.get("/api/v1/market-data/symbols")
        assert symbols_response.status_code == 200
        symbols_data = symbols_response.json()
        assert symbols_data["success"] is True

        # 3. 获取历史数据（如果品种列表不为空）
        if symbols_data["data"]:
            symbol = symbols_data["data"][0]["symbol"]
            end_date = date.today()
            start_date = end_date - timedelta(days=30)

            history_response = client.get(
                f"/api/v1/market-data/history",
                params={
                    "symbol": symbol,
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat()
                }
            )
            # 可能返回200（有数据）或404（无数据）
            assert history_response.status_code in [200, 404]

    def test_complete_strategy_workflow(self):
        """测试完整的策略工作流程"""
        # 1. 获取策略列表
        strategies_response = client.get("/api/v1/strategies/")
        assert strategies_response.status_code == 200
        strategies_data = strategies_response.json()
        assert len(strategies_data["strategies"]) > 0

        # 2. 获取策略参数说明
        params_response = client.get("/api/v1/strategies/parameters/single-ma")
        assert params_response.status_code == 200
        params_data = params_response.json()
        assert "parameters" in params_data

        # 3. 配置策略参数
        config_response = client.post("/api/v1/strategies/configure", json={
            "strategy_type": "single_ma",
            "parameters": {
                "ma_period": 20,
                "initial_capital": 100000,
                "stop_loss": 0.05
            }
        })
        assert config_response.status_code == 200
        config_data = config_response.json()
        assert config_data["success"] is True
        assert "config_id" in config_data

        # 4. 运行策略（创建异步任务）
        run_response = client.post("/api/v1/strategies/run", json={
            "symbol": "CU2401",
            "strategy_type": "single_ma",
            "start_date": "2023-01-01",
            "end_date": "2023-12-31",
            "parameters": {
                "ma_period": 20,
                "initial_capital": 100000,
                "stop_loss": 0.05
            }
        })
        assert run_response.status_code == 200
        run_data = run_response.json()
        assert "strategy_id" in run_data
        assert run_data["status"] == "running"

        strategy_id = run_data["strategy_id"]

        # 5. 检查任务状态
        status_response = client.get(f"/api/v1/strategies/task/{strategy_id}/status")
        assert status_response.status_code == 200
        status_data = status_response.json()
        assert status_data["success"] is True
        assert status_data["data"]["task_id"] == strategy_id

        # 6. 尝试获取结果（可能还没有完成）
        results_response = client.get(f"/api/v1/strategies/{strategy_id}/results")
        # 可能返回400（未完成）或200（已完成）
        assert results_response.status_code in [200, 400]

    def test_error_propagation_consistency(self):
        """测试错误传播一致性"""
        # 测试各种错误情况的响应格式一致性
        error_test_cases = [
            {
                "url": "/api/v1/market-data/history",
                "method": "GET",
                "params": {
                    "symbol": "INVALID",
                    "start_date": "2023-12-31",
                    "end_date": "2023-01-01"  # 无效日期范围
                },
                "expected_status": 400
            },
            {
                "url": "/api/v1/strategies/run",
                "method": "POST",
                "json": {
                    "strategy_type": "invalid",
                    "symbol": "CU2401"
                },
                "expected_status": 422
            }
        ]

        for test_case in error_test_cases:
            if test_case["method"] == "GET":
                response = client.get(test_case["url"], params=test_case["params"])
            else:
                response = client.request(
                    test_case["method"],
                    test_case["url"],
                    json=test_case["json"]
                )

            assert response.status_code == test_case["expected_status"]
            data = response.json()

            # 检查错误响应格式
            if "success" in data:
                assert data["success"] is False
            if "error" in data:
                assert "type" in data["error"]
                assert "message" in data["error"]

    def test_api_versioning(self):
        """测试API版本控制"""
        # 测试带版本号的请求
        response = client.get("/api/v1/market-data/symbols")
        assert response.status_code == 200
        assert "api-version" in response.headers
        assert response.headers["api-version"] == "v1"

    def test_concurrent_requests(self):
        """测试并发请求处理"""
        import concurrent.futures
        import threading

        def make_request():
            return client.get("/api/v1/market-data/symbols")

        # 发送多个并发请求
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request) for _ in range(10)]
            responses = [future.result() for future in concurrent.futures.as_completed(futures)]

        # 检查所有请求都得到响应
        success_count = sum(1 for r in responses if r.status_code == 200)
        assert success_count >= 8  # 允许一些请求失败（由于频率限制等）

    def test_request_response_time_consistency(self):
        """测试请求响应时间一致性"""
        import time

        response_times = []
        for _ in range(5):
            start_time = time.time()
            response = client.get("/api/v1/market-data/symbols")
            end_time = time.time()
            response_times.append(end_time - start_time)

        # 检查响应时间是否在合理范围内
        avg_response_time = sum(response_times) / len(response_times)
        assert avg_response_time < 2.0  # 平均响应时间应小于2秒

        # 检查响应时间是否稳定
        max_time = max(response_times)
        min_time = min(response_times)
        assert (max_time - min_time) < 1.0  # 响应时间变化应小于1秒

    def test_large_payload_handling(self):
        """测试大负载处理"""
        # 测试大参数请求
        large_params = {
            "strategy_type": "single_ma",
            "parameters": {
                "ma_period": 20,
                "initial_capital": 100000,
                "stop_loss": 0.05,
                "large_field": "x" * 10000  # 大字段
            }
        }

        response = client.post("/api/v1/strategies/configure", json=large_params)
        # 可能成功或失败，取决于大小限制
        assert response.status_code in [200, 400, 413]

    def test_unicode_handling(self):
        """测试Unicode字符处理"""
        unicode_data = {
            "strategy_type": "single_ma",
            "parameters": {
                "ma_period": 20,
                "initial_capital": 100000,
                "stop_loss": 0.05,
                "description": "测试中文🚀emoji和特殊字符"
            }
        }

        response = client.post("/api/v1/strategies/configure", json=unicode_data)
        # 应该能正确处理Unicode
        assert response.status_code in [200, 400]

    def test_content_type_handling(self):
        """测试内容类型处理"""
        # 测试不同的内容类型
        headers = {"Content-Type": "application/json"}
        data = {"test": "data"}

        response = client.post(
            "/api/v1/strategies/configure",
            json=data,
            headers=headers
        )
        # 可能因缺少必要字段而失败，但不应该因内容类型而失败
        assert response.status_code in [200, 400, 422]

    def test_cors_preflight(self):
        """测试CORS预检请求"""
        headers = {
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type"
        }

        response = client.options("/api/v1/strategies/run", headers=headers)
        # CORS预检请求应该成功
        assert response.status_code in [200, 204]

    def test_health_check_endpoints(self):
        """测试健康检查端点"""
        # 根路径健康检查
        root_response = client.get("/")
        assert root_response.status_code == 200
        root_data = root_response.json()
        assert "status" in root_data
        assert root_data["status"] == "healthy"

        # 详细健康检查
        health_response = client.get("/health")
        assert health_response.status_code == 200
        health_data = health_response.json()
        assert health_data["status"] == "healthy"
        assert "version" in health_data
        assert "environment" in health_data

    def test_api_documentation_accessibility(self):
        """测试API文档可访问性"""
        # 测试Swagger UI
        docs_response = client.get("/api/v1/docs")
        assert docs_response.status_code == 200

        # 测试ReDoc
        redoc_response = client.get("/api/v1/redoc")
        assert redoc_response.status_code == 200

        # 测试OpenAPI JSON
        openapi_response = client.get("/api/v1/openapi.json")
        assert openapi_response.status_code == 200
        openapi_data = openapi_response.json()
        assert "openapi" in openapi_data
        assert "info" in openapi_data
        assert "paths" in openapi_data