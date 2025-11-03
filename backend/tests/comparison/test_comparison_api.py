"""
对比分析API端点测试
"""
import pytest
import json
from fastapi.testclient import TestClient
from datetime import datetime, timedelta
from unittest.mock import patch, AsyncMock

from app.main import app

client = TestClient(app)

class TestComparisonAPI:
    """对比分析API测试类"""

    @pytest.fixture
    def sample_request(self):
        """示例对比分析请求"""
        return {
            "symbols": ["RB2410", "I2410", "CU2410"],
            "start_date": "2024-01-01",
            "end_date": "2024-12-31",
            "strategy": {
                "name": "SMA",
                "params": {"window": 20}
            }
        }

    @pytest.fixture
    def mock_task_result(self):
        """示例任务结果"""
        return {
            "requestId": "test-task-id",
            "timestamp": datetime.now().isoformat(),
            "request": {
                "symbols": ["RB2410", "I2410"],
                "start_date": "2024-01-01",
                "end_date": "2024-12-31",
                "strategy": {"name": "SMA", "params": {"window": 20}}
            },
            "results": [
                {
                    "symbol": "RB2410",
                    "name": "螺纹钢2410",
                    "sector": "金属",
                    "exchange": "SHFE",
                    "metrics": {
                        "totalReturn": 0.15,
                        "sharpeRatio": 1.2,
                        "maxDrawdown": -0.08,
                        "volatility": 0.12,
                        "winRate": 0.67,
                        "totalTrades": 25
                    },
                    "trades": [],
                    "equity": [],
                    "signals": []
                },
                {
                    "symbol": "I2410",
                    "name": "铁矿石2410",
                    "sector": "金属",
                    "exchange": "DCE",
                    "metrics": {
                        "totalReturn": 0.08,
                        "sharpeRatio": 0.9,
                        "maxDrawdown": -0.12,
                        "volatility": 0.15,
                        "winRate": 0.55,
                        "totalTrades": 20
                    },
                    "trades": [],
                    "equity": [],
                    "signals": []
                }
            ],
            "summary": {
                "totalVarieties": 2,
                "successfulVarieties": 2,
                "failedVarieties": 0,
                "bestPerformer": "RB2410",
                "worstPerformer": "I2410",
                "averageReturn": 0.115,
                "averageSharpeRatio": 1.05,
                "totalTrades": 45,
                "dateRange": {
                    "start": "2024-01-01",
                    "end": "2024-12-31",
                    "tradingDays": 252
                }
            },
            "rankings": [
                {
                    "rank": 1,
                    "symbol": "RB2410",
                    "name": "螺纹钢2410",
                    "sector": "金属",
                    "score": 0.85,
                    "metrics": {
                        "returnRank": 1,
                        "riskRank": 2,
                        "riskAdjustedReturnRank": 1,
                        "consistencyRank": 1
                    },
                    "highlights": ["高收益率", "优秀风险调整收益"]
                },
                {
                    "rank": 2,
                    "symbol": "I2410",
                    "name": "铁矿石2410",
                    "sector": "金属",
                    "score": 0.65,
                    "metrics": {
                        "returnRank": 2,
                        "riskRank": 1,
                        "riskAdjustedReturnRank": 2,
                        "consistencyRank": 2
                    },
                    "highlights": ["低回撤"]
                }
            ]
        }

    def test_run_comparison_success(self, sample_request):
        """测试成功启动对比分析"""
        with patch('app.api.v1.endpoints.comparison.process_comparison_task') as mock_task:
            mock_task.return_value = None

            response = client.post("/api/v1/comparison/run", json=sample_request)

            assert response.status_code == 200
            data = response.json()
            assert "task_id" in data
            assert data["status"] == "started"
            assert "message" in data

    def test_run_comparison_insufficient_symbols(self):
        """测试品种数量不足的情况"""
        request = {
            "symbols": ["RB2410"],  # 只有一个品种
            "start_date": "2024-01-01",
            "end_date": "2024-12-31",
            "strategy": {"name": "SMA", "params": {"window": 20}}
        }

        response = client.post("/api/v1/comparison/run", json=request)

        assert response.status_code == 400
        assert "至少需要选择2个品种进行对比" in response.json()["detail"]

    def test_run_comparison_too_many_symbols(self):
        """测试品种数量过多的情况"""
        request = {
            "symbols": [f"SYM{i}" for i in range(12)],  # 12个品种，超过限制
            "start_date": "2024-01-01",
            "end_date": "2024-12-31",
            "strategy": {"name": "SMA", "params": {"window": 20}}
        }

        response = client.post("/api/v1/comparison/run", json=request)

        assert response.status_code == 400
        assert "最多支持10个品种同时对比" in response.json()["detail"]

    def test_run_comparison_invalid_date_format(self):
        """测试无效日期格式"""
        request = {
            "symbols": ["RB2410", "I2410"],
            "start_date": "2024/01/01",  # 错误的日期格式
            "end_date": "2024-12-31",
            "strategy": {"name": "SMA", "params": {"window": 20}}
        }

        response = client.post("/api/v1/comparison/run", json=request)

        assert response.status_code == 400
        assert "日期格式无效" in response.json()["detail"]

    def test_run_comparison_invalid_date_range(self):
        """测试无效日期范围"""
        request = {
            "symbols": ["RB2410", "I2410"],
            "start_date": "2024-12-31",
            "end_date": "2024-01-01",  # 开始日期晚于结束日期
            "strategy": {"name": "SMA", "params": {"window": 20}}
        }

        response = client.post("/api/v1/comparison/run", json=request)

        assert response.status_code == 400
        assert "开始日期必须早于结束日期" in response.json()["detail"]

    def test_run_comparison_future_date(self):
        """测试未来日期"""
        future_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        request = {
            "symbols": ["RB2410", "I2410"],
            "start_date": "2024-01-01",
            "end_date": future_date,  # 未来日期
            "strategy": {"name": "SMA", "params": {"window": 20}}
        }

        response = client.post("/api/v1/comparison/run", json=request)

        assert response.status_code == 400
        assert "结束日期不能超过当前日期" in response.json()["detail"]

    def test_get_comparison_results_success(self, mock_task_result):
        """测试成功获取对比结果"""
        # 首先创建一个已完成的任务
        from app.api.v1.endpoints.comparison import comparison_tasks
        task_id = "test-task-id"
        comparison_tasks[task_id] = {
            "status": "completed",
            "request": {"symbols": ["RB2410", "I2410"]},
            "progress": 100,
            "result": mock_task_result,
            "error": None,
            "created_at": datetime.now().isoformat()
        }

        response = client.get(f"/api/v1/comparison/results/{task_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == task_id
        assert data["status"] == "completed"
        assert data["progress"] == 100
        assert "result" in data
        assert data["result"]["requestId"] == task_id

    def test_get_comparison_results_not_found(self):
        """测试获取不存在任务的结果"""
        response = client.get("/api/v1/comparison/results/non-existent-task")

        assert response.status_code == 404
        assert "任务不存在" in response.json()["detail"]

    def test_get_comparison_results_pending(self):
        """测试获取进行中任务的结果"""
        from app.api.v1.endpoints.comparison import comparison_tasks
        task_id = "pending-task-id"
        comparison_tasks[task_id] = {
            "status": "running",
            "request": {"symbols": ["RB2410", "I2410"]},
            "progress": 50,
            "result": None,
            "error": None,
            "created_at": datetime.now().isoformat()
        }

        response = client.get(f"/api/v1/comparison/results/{task_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "running"
        assert data["progress"] == 50
        assert "result" not in data

    def test_get_comparison_results_failed(self):
        """测试获取失败任务的结果"""
        from app.api.v1.endpoints.comparison import comparison_tasks
        task_id = "failed-task-id"
        comparison_tasks[task_id] = {
            "status": "failed",
            "request": {"symbols": ["RB2410", "I2410"]},
            "progress": 30,
            "result": None,
            "error": "数据处理失败",
            "created_at": datetime.now().isoformat()
        }

        response = client.get(f"/api/v1/comparison/results/{task_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "failed"
        assert data["error"] == "数据处理失败"

    def test_cancel_comparison_success(self):
        """测试成功取消对比任务"""
        from app.api.v1.endpoints.comparison import comparison_tasks
        task_id = "running-task-id"
        comparison_tasks[task_id] = {
            "status": "running",
            "request": {"symbols": ["RB2410", "I2410"]},
            "progress": 25,
            "result": None,
            "error": None,
            "created_at": datetime.now().isoformat()
        }

        response = client.delete(f"/api/v1/comparison/cancel/{task_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == task_id
        assert data["status"] == "cancelled"

        # 验证任务状态已更新
        assert comparison_tasks[task_id]["status"] == "cancelled"

    def test_cancel_comparison_not_found(self):
        """测试取消不存在的任务"""
        response = client.delete("/api/v1/comparison/cancel/non-existent-task")

        assert response.status_code == 404
        assert "任务不存在" in response.json()["detail"]

    def test_cancel_comparison_completed_task(self):
        """测试取消已完成的任务"""
        from app.api.v1.endpoints.comparison import comparison_tasks
        task_id = "completed-task-id"
        comparison_tasks[task_id] = {
            "status": "completed",
            "request": {"symbols": ["RB2410", "I2410"]},
            "progress": 100,
            "result": {},
            "error": None,
            "created_at": datetime.now().isoformat()
        }

        response = client.delete(f"/api/v1/comparison/cancel/{task_id}")

        assert response.status_code == 400
        assert "任务已完成，无法取消" in response.json()["detail"]

    def test_get_available_metrics(self):
        """测试获取可用指标"""
        response = client.get("/api/v1/comparison/metrics")

        assert response.status_code == 200
        data = response.json()
        assert "metrics" in data

        metrics = data["metrics"]
        assert len(metrics) > 0

        # 验证指标结构
        for metric in metrics:
            assert "name" in metric
            assert "label" in metric
            assert "description" in metric
            assert "unit" in metric
            assert "higher_is_better" in metric

        # 验证特定指标存在
        metric_names = [m["name"] for m in metrics]
        assert "total_return" in metric_names
        assert "sharpe_ratio" in metric_names
        assert "max_drawdown" in metric_names

    def test_get_historical_comparison_success(self):
        """测试获取历史对比数据"""
        with patch('app.api.v1.endpoints.comparison.market_data_service') as mock_service:
            # Mock市场数据服务
            mock_service.get_historical_data = AsyncMock(side_effect=[
                [  # RB2410的数据
                    {"date": "2024-01-01", "close": 4000},
                    {"date": "2024-01-02", "close": 4050},
                    {"date": "2024-01-03", "close": 4100}
                ],
                [  # I2410的数据
                    {"date": "2024-01-01", "close": 800},
                    {"date": "2024-01-02", "close": 810},
                    {"date": "2024-01-03", "close": 820}
                ]
            ])

            response = client.post(
                "/api/v1/comparison/historical",
                json={"symbols": ["RB2410", "I2410"], "days": 30}
            )

            assert response.status_code == 200
            data = response.json()
            assert "symbols" in data
            assert "period" in data
            assert "results" in data

            assert data["symbols"] == ["RB2410", "I2410"]
            assert len(data["results"]) == 2

            # 验证结果结构
            for result in data["results"]:
                assert "symbol" in result
                assert "total_return" in result
                assert "volatility" in result
                assert "data_points" in result

    def test_get_historical_comparison_insufficient_symbols(self):
        """测试历史对比品种数量不足"""
        response = client.post(
            "/api/v1/comparison/historical",
            json={"symbols": ["RB2410"], "days": 30}
        )

        assert response.status_code == 400
        assert "至少需要2个品种" in response.json()["detail"]

    def test_get_historical_comparison_invalid_days(self):
        """测试无效的天数范围"""
        response = client.post(
            "/api/v1/comparison/historical",
            json={"symbols": ["RB2410", "I2410"], "days": 5}  # 少于7天
        )

        assert response.status_code == 400
        assert "天数范围应在7-365天之间" in response.json()["detail"]

        response = client.post(
            "/api/v1/comparison/historical",
            json={"symbols": ["RB2410", "I2410"], "days": 400}  # 超过365天
        )

        assert response.status_code == 400
        assert "天数范围应在7-365天之间" in response.json()["detail"]

    @patch('app.api.v1.endpoints.comparison.process_comparison_task')
    def test_process_comparison_task_background_execution(self, mock_task):
        """测试后台任务处理"""
        mock_task.return_value = None

        request = {
            "symbols": ["RB2410", "I2410"],
            "start_date": "2024-01-01",
            "end_date": "2024-12-31",
            "strategy": {"name": "SMA", "params": {"window": 20}}
        }

        response = client.post("/api/v1/comparison/run", json=request)

        assert response.status_code == 200

        # 验证后台任务被调用
        mock_task.assert_called_once()

    def test_cleanup_expired_tasks(self):
        """测试清理过期任务"""
        from app.api.v1.endpoints.comparison import cleanup_expired_tasks, comparison_tasks

        # 创建一个过期任务（超过24小时）
        expired_time = (datetime.now() - timedelta(hours=25)).isoformat()
        comparison_tasks["expired-task"] = {
            "status": "completed",
            "created_at": expired_time
        }

        # 创建一个新任务
        recent_time = (datetime.now() - timedelta(hours=1)).isoformat()
        comparison_tasks["recent-task"] = {
            "status": "completed",
            "created_at": recent_time
        }

        # 运行清理
        import asyncio
        asyncio.run(cleanup_expired_tasks())

        # 验证过期任务被删除，新任务保留
        assert "expired-task" not in comparison_tasks
        assert "recent-task" in comparison_tasks