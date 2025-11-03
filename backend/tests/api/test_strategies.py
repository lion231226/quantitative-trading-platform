import pytest
from fastapi.testclient import TestClient
from datetime import date, timedelta
import json
import uuid

from main import app

client = TestClient(app)

class TestStrategiesAPI:
    """策略API测试"""

    def test_get_strategy_list_success(self):
        """测试获取策略列表 - 成功"""
        response = client.get("/api/v1/strategies/")

        assert response.status_code == 200
        data = response.json()

        assert "strategies" in data
        assert "total" in data
        assert isinstance(data["strategies"], list)
        assert data["total"] == len(data["strategies"])

        # 检查策略结构
        if data["strategies"]:
            strategy = data["strategies"][0]
            assert "id" in strategy
            assert "name" in strategy
            assert "description" in strategy
            assert "parameters" in strategy

    def test_run_strategy_success(self):
        """测试运行策略 - 成功创建任务"""
        request_data = {
            "symbol": "CU2401",
            "strategy_type": "single_ma",
            "start_date": "2023-01-01",
            "end_date": "2023-12-31",
            "parameters": {
                "ma_period": 20,
                "initial_capital": 100000,
                "stop_loss": 0.05
            }
        }

        response = client.post("/api/v1/strategies/run", json=request_data)

        assert response.status_code == 200
        data = response.json()

        assert "strategy_id" in data
        assert "strategy_type" in data
        assert "symbol" in data
        assert "parameters" in data
        assert "status" in data
        assert data["status"] == "running"

        # 验证strategy_id是有效的UUID
        uuid.UUID(data["strategy_id"])

    def test_run_strategy_invalid_type(self):
        """测试运行策略 - 无效策略类型"""
        request_data = {
            "symbol": "CU2401",
            "strategy_type": "invalid_strategy",
            "start_date": "2023-01-01",
            "end_date": "2023-12-31",
            "parameters": {}
        }

        response = client.post("/api/v1/strategies/run", json=request_data)

        assert response.status_code == 400
        data = response.json()

        assert data["success"] is False
        assert "error" in data
        assert "不支持的策略类型" in data["error"]["message"]

    def test_run_strategy_missing_fields(self):
        """测试运行策略 - 缺少必要字段"""
        request_data = {
            "symbol": "CU2401",
            "strategy_type": "single_ma"
            # 缺少start_date, end_date, parameters
        }

        response = client.post("/api/v1/strategies/run", json=request_data)

        assert response.status_code == 422  # 验证错误

    def test_get_strategy_results_not_found(self):
        """测试获取策略结果 - 结果不存在"""
        fake_strategy_id = str(uuid.uuid4())

        response = client.get(f"/api/v1/strategies/{fake_strategy_id}/results")

        assert response.status_code == 400
        data = response.json()

        assert data["success"] is False
        assert "策略结果不存在或已过期" in data["error"]["message"]

    def test_get_strategy_parameters_single_ma(self):
        """测试获取单均线策略参数说明"""
        response = client.get("/api/v1/strategies/parameters/single-ma")

        assert response.status_code == 200
        data = response.json()

        assert "strategy_name" in data
        assert "description" in data
        assert "parameters" in data
        assert "usage" in data

        # 检查参数结构
        parameters = data["parameters"]
        expected_params = ["ma_period", "initial_capital", "stop_loss"]
        for param in expected_params:
            assert param in parameters
            assert "name" in parameters[param]
            assert "type" in parameters[param]
            assert "default" in parameters[param]
            assert "min" in parameters[param]
            assert "max" in parameters[param]
            assert "description" in parameters[param]

    def test_configure_strategy_parameters_success(self):
        """测试配置策略参数 - 成功"""
        request_data = {
            "strategy_type": "single_ma",
            "parameters": {
                "ma_period": 20,
                "initial_capital": 100000,
                "stop_loss": 0.05
            }
        }

        response = client.post("/api/v1/strategies/configure", json=request_data)

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert "config_id" in data
        assert "strategy_type" in data
        assert "parameters" in data

        # 验证config_id是有效的UUID
        uuid.UUID(data["config_id"])

    def test_configure_strategy_parameters_invalid_type(self):
        """测试配置策略参数 - 无效策略类型"""
        request_data = {
            "strategy_type": "invalid_strategy",
            "parameters": {
                "ma_period": 20
            }
        }

        response = client.post("/api/v1/strategies/configure", json=request_data)

        assert response.status_code == 400
        data = response.json()

        assert data["success"] is False
        assert "不支持的策略类型" in data["error"]["message"]

    def test_configure_strategy_parameters_invalid_params(self):
        """测试配置策略参数 - 无效参数值"""
        request_data = {
            "strategy_type": "single_ma",
            "parameters": {
                "ma_period": 300,  # 超出最大值
                "initial_capital": 5000,  # 低于最小值
                "stop_loss": 0.5  # 超出最大值
            }
        }

        response = client.post("/api/v1/strategies/configure", json=request_data)

        assert response.status_code == 400
        data = response.json()

        assert data["success"] is False
        assert "error" in data

    def test_get_task_status(self):
        """测试获取任务状态"""
        # 首先创建一个策略任务
        request_data = {
            "symbol": "CU2401",
            "strategy_type": "single_ma",
            "start_date": "2023-01-01",
            "end_date": "2023-12-31",
            "parameters": {
                "ma_period": 20,
                "initial_capital": 100000
            }
        }

        create_response = client.post("/api/v1/strategies/run", json=request_data)
        assert create_response.status_code == 200
        strategy_id = create_response.json()["strategy_id"]

        # 获取任务状态
        response = client.get(f"/api/v1/strategies/task/{strategy_id}/status")

        # 任务可能成功也可能失败，都应该能查询到状态
        assert response.status_code in [200, 400]
        data = response.json()

        if response.status_code == 200:
            # 成功情况
            assert data["success"] is True
            assert "data" in data
            task_data = data["data"]
            assert "task_id" in task_data
            assert "status" in task_data
            assert "progress" in task_data
            assert "created_at" in task_data
            # 验证task_id
            assert task_data["task_id"] == strategy_id
        else:
            # 失败情况 - 至少应该能返回错误信息
            assert data["success"] is False
            assert "error" in data

    def test_get_task_status_not_found(self):
        """测试获取任务状态 - 任务不存在"""
        fake_task_id = str(uuid.uuid4())

        response = client.get(f"/api/v1/strategies/task/{fake_task_id}/status")

        assert response.status_code == 400
        data = response.json()

        assert data["success"] is False
        assert "任务不存在" in data["error"]["message"]

    def test_cancel_task(self):
        """测试取消任务"""
        # 首先创建一个策略任务
        request_data = {
            "symbol": "CU2401",
            "strategy_type": "single_ma",
            "start_date": "2023-01-01",
            "end_date": "2023-12-31",
            "parameters": {
                "ma_period": 20,
                "initial_capital": 100000,
                "stop_loss": 0.05
            }
        }

        create_response = client.post("/api/v1/strategies/run", json=request_data)
        assert create_response.status_code == 200
        strategy_id = create_response.json()["strategy_id"]

        # 取消任务
        response = client.delete(f"/api/v1/strategies/task/{strategy_id}")

        # 可能成功或失败，取决于任务状态
        assert response.status_code in [200, 400]

    def test_get_strategy_performance_not_found(self):
        """测试获取策略绩效指标 - 结果不存在"""
        fake_strategy_id = str(uuid.uuid4())

        response = client.get(f"/api/v1/strategies/{fake_strategy_id}/performance")

        assert response.status_code == 400
        data = response.json()

        assert data["success"] is False
        assert "策略结果不存在或已过期" in data["error"]["message"]

    def test_get_strategy_trades_not_found(self):
        """测试获取策略交易记录 - 结果不存在"""
        fake_strategy_id = str(uuid.uuid4())

        response = client.get(f"/api/v1/strategies/{fake_strategy_id}/trades")

        assert response.status_code == 400
        data = response.json()

        assert data["success"] is False
        assert "策略结果不存在或已过期" in data["error"]["message"]

    def test_get_strategy_trades_invalid_pagination(self):
        """测试获取策略交易记录 - 无效分页参数"""
        fake_strategy_id = str(uuid.uuid4())

        # 测试无效页码
        response = client.get(f"/api/v1/strategies/{fake_strategy_id}/trades?page=0")
        assert response.status_code == 400

        # 测试无效页面大小
        response = client.get(f"/api/v1/strategies/{fake_strategy_id}/trades?size=0")
        assert response.status_code == 400

        response = client.get(f"/api/v1/strategies/{fake_strategy_id}/trades?size=101")
        assert response.status_code == 400

    def test_get_strategy_summary_not_found(self):
        """测试获取策略执行摘要 - 结果不存在"""
        fake_strategy_id = str(uuid.uuid4())

        response = client.get(f"/api/v1/strategies/{fake_strategy_id}/summary")

        assert response.status_code == 400
        data = response.json()

        assert data["success"] is False
        assert "策略结果不存在或已过期" in data["error"]["message"]

    def test_api_response_format_consistency(self):
        """测试API响应格式一致性"""
        response = client.get("/api/v1/strategies/")

        assert response.status_code == 200
        data = response.json()

        # 策略列表API没有使用标准格式，这是预期的
        # 但应该包含必要的字段
        assert "strategies" in data
        assert "total" in data

    def test_error_handling_invalid_json(self):
        """测试错误处理 - 无效JSON"""
        response = client.post(
            "/api/v1/strategies/run",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )

        assert response.status_code == 422

    def test_async_task_creation(self):
        """测试异步任务创建"""
        request_data = {
            "symbol": "CU2401",
            "strategy_type": "single_ma",
            "start_date": "2023-01-01",
            "end_date": "2023-12-31",
            "parameters": {
                "ma_period": 20,
                "initial_capital": 100000,
                "stop_loss": 0.05
            }
        }

        response = client.post("/api/v1/strategies/run", json=request_data)

        assert response.status_code == 200
        data = response.json()

        # 应该立即返回任务ID，而不是等待完成
        assert "strategy_id" in data
        assert "status" in data
        assert data["status"] == "running"

    def test_strategy_parameter_validation(self):
        """测试策略参数验证"""
        test_cases = [
            {
                "name": "ma_period_below_min",
                "parameters": {"ma_period": 4, "initial_capital": 100000, "stop_loss": 0.05}
            },
            {
                "name": "ma_period_above_max",
                "parameters": {"ma_period": 201, "initial_capital": 100000, "stop_loss": 0.05}
            },
            {
                "name": "initial_capital_below_min",
                "parameters": {"ma_period": 20, "initial_capital": 9999, "stop_loss": 0.05}
            },
            {
                "name": "stop_loss_below_min",
                "parameters": {"ma_period": 20, "initial_capital": 100000, "stop_loss": 0.005}
            },
            {
                "name": "stop_loss_above_max",
                "parameters": {"ma_period": 20, "initial_capital": 100000, "stop_loss": 0.25}
            }
        ]

        for test_case in test_cases:
            request_data = {
                "strategy_type": "single_ma",
                "parameters": test_case["parameters"]
            }

            response = client.post("/api/v1/strategies/configure", json=request_data)

            assert response.status_code == 400
            data = response.json()
            assert data["success"] is False