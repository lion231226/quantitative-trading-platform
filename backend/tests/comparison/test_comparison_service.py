"""
对比分析服务测试
"""
import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from app.services.comparison_service import ComparisonService

class TestComparisonService:
    """对比分析服务测试类"""

    @pytest.fixture
    def comparison_service(self):
        """创建对比分析服务实例"""
        return ComparisonService()

    @pytest.fixture
    def sample_strategy_result(self):
        """示例策略结果数据"""
        return {
            "trades": [
                {"date": "2024-01-02", "pnl": 1000, "type": "BUY"},
                {"date": "2024-01-05", "pnl": -500, "type": "SELL"},
                {"date": "2024-01-10", "pnl": 1500, "type": "BUY"},
                {"date": "2024-01-15", "pnl": 800, "type": "SELL"},
                {"date": "2024-01-20", "pnl": -300, "type": "SELL"},
                {"date": "2024-01-25", "pnl": 2000, "type": "BUY"}
            ],
            "equity": [
                {"date": "2024-01-01", "equity": 100000},
                {"date": "2024-01-02", "equity": 101000},
                {"date": "2024-01-05", "equity": 100500},
                {"date": "2024-01-10", "equity": 102000},
                {"date": "2024-01-15", "equity": 102800},
                {"date": "2024-01-20", "equity": 102500},
                {"date": "2024-01-25", "equity": 104500}
            ],
            "signals": [
                {"date": "2024-01-02", "signal": "BUY", "price": 4000},
                {"date": "2024-01-05", "signal": "SELL", "price": 4050},
                {"date": "2024-01-10", "signal": "BUY", "price": 3950},
                {"date": "2024-01-15", "signal": "SELL", "price": 4100},
                {"date": "2024-01-20", "signal": "SELL", "price": 4080},
                {"date": "2024-01-25", "signal": "BUY", "price": 4020}
            ]
        }

    @pytest.fixture
    def sample_results(self):
        """示例对比结果数据"""
        return [
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
                    "totalTrades": 6
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
                    "winRate": 0.50,
                    "totalTrades": 4
                },
                "trades": [],
                "equity": [],
                "signals": []
            },
            {
                "symbol": "SC2410",
                "name": "原油2410",
                "sector": "能源",
                "exchange": "INE",
                "metrics": {
                    "totalReturn": -0.05,
                    "sharpeRatio": -0.3,
                    "maxDrawdown": -0.15,
                    "volatility": 0.20,
                    "winRate": 0.33,
                    "totalTrades": 3
                },
                "trades": [],
                "equity": [],
                "signals": []
            }
        ]

    @pytest.mark.asyncio
    async def test_calculate_metrics(self, comparison_service, sample_strategy_result):
        """测试绩效指标计算"""
        metrics = await comparison_service.calculate_metrics(sample_strategy_result)

        # 验证基础指标
        assert "totalReturn" in metrics
        assert "sharpeRatio" in metrics
        assert "maxDrawdown" in metrics
        assert "volatility" in metrics
        assert "winRate" in metrics
        assert "totalTrades" in metrics

        # 验证具体数值
        assert metrics["totalReturn"] == pytest.approx(0.045, rel=1e-2)  # 4.5%总收益
        assert metrics["totalTrades"] == 6
        assert metrics["winningTrades"] == 4  # 盈利交易数
        assert metrics["losingTrades"] == 2   # 亏损交易数
        assert metrics["winRate"] == pytest.approx(0.667, rel=1e-2)  # 66.7%胜率

        # 验证数值合理性
        assert metrics["totalReturn"] > 0  # 应该有正收益
        assert 0 <= metrics["winRate"] <= 1  # 胜率应在0-1之间
        assert metrics["volatility"] >= 0  # 波动率应为非负数
        assert metrics["maxDrawdown"] <= 0  # 最大回撤应为非正数

    @pytest.mark.asyncio
    async def test_calculate_metrics_empty_data(self, comparison_service):
        """测试空数据的指标计算"""
        empty_result = {"trades": [], "equity": [], "signals": []}
        metrics = await comparison_service.calculate_metrics(empty_result)

        assert metrics == {}

    @pytest.mark.asyncio
    async def test_calculate_metrics_partial_data(self, comparison_service):
        """测试部分数据的指标计算"""
        partial_result = {
            "trades": [{"pnl": 1000}],
            "equity": [],
            "signals": []
        }
        metrics = await comparison_service.calculate_metrics(partial_result)

        assert metrics == {}

    @pytest.mark.asyncio
    async def test_generate_summary(self, comparison_service, sample_results):
        """测试生成对比总结"""
        request = {
            "start_date": "2024-01-01",
            "end_date": "2024-12-31"
        }

        summary = await comparison_service.generate_summary(sample_results, request)

        # 验证总结结构
        assert "totalVarieties" in summary
        assert "successfulVarieties" in summary
        assert "failedVarieties" in summary
        assert "bestPerformer" in summary
        assert "worstPerformer" in summary
        assert "averageReturn" in summary
        assert "averageSharpeRatio" in summary
        assert "totalTrades" in summary
        assert "dateRange" in summary

        # 验证具体数值
        assert summary["totalVarieties"] == 3
        assert summary["successfulVarieties"] == 3
        assert summary["failedVarieties"] == 0
        assert summary["bestPerformer"] == "RB2410"  # 最高收益率
        assert summary["worstPerformer"] == "SC2410"  # 最低收益率
        assert summary["averageReturn"] == pytest.approx(0.06, rel=1e-2)  # 平均收益率
        assert summary["averageSharpeRatio"] == pytest.approx(0.6, rel=1e-2)  # 平均夏普比率

    @pytest.mark.asyncio
    async def test_generate_summary_with_failures(self, comparison_service):
        """测试包含失败品种的总结生成"""
        results_with_failures = [
            {
                "symbol": "RB2410",
                "name": "螺纹钢2410",
                "sector": "金属",
                "exchange": "SHFE",
                "metrics": {"totalReturn": 0.15},
                "trades": [],
                "equity": [],
                "signals": []
            },
            {
                "symbol": "FAIL2410",
                "name": "失败品种",
                "sector": "未知",
                "exchange": "未知",
                "error": "数据获取失败",
                "trades": [],
                "equity": [],
                "signals": []
            }
        ]

        request = {"start_date": "2024-01-01", "end_date": "2024-12-31"}
        summary = await comparison_service.generate_summary(results_with_failures, request)

        assert summary["totalVarieties"] == 2
        assert summary["successfulVarieties"] == 1
        assert summary["failedVarieties"] == 1
        assert summary["bestPerformer"] == "RB2410"

    @pytest.mark.asyncio
    async def test_generate_summary_empty_results(self, comparison_service):
        """测试空结果的总结生成"""
        request = {"start_date": "2024-01-01", "end_date": "2024-12-31"}
        summary = await comparison_service.generate_summary([], request)

        assert summary["totalVarieties"] == 0
        assert summary["successfulVarieties"] == 0
        assert summary["failedVarieties"] == 0
        assert summary["bestPerformer"] == ""
        assert summary["worstPerformer"] == ""

    @pytest.mark.asyncio
    async def test_generate_rankings(self, comparison_service, sample_results):
        """测试生成排名"""
        rankings = await comparison_service.generate_rankings(sample_results)

        # 验证排名结构
        assert len(rankings) == 3
        for ranking in rankings:
            assert "rank" in ranking
            assert "symbol" in ranking
            assert "name" in ranking
            assert "sector" in ranking
            assert "score" in ranking
            assert "metrics" in ranking
            assert "highlights" in ranking

            # 验证排名指标
            assert "returnRank" in ranking["metrics"]
            assert "riskRank" in ranking["metrics"]
            assert "riskAdjustedReturnRank" in ranking["metrics"]
            assert "consistencyRank" in ranking["metrics"]

        # 验证排名顺序（按综合评分降序）
        assert rankings[0]["symbol"] == "RB2410"  # 最高评分
        assert rankings[2]["symbol"] == "SC2410"  # 最低评分

        # 验证排名数值
        assert rankings[0]["rank"] == 1
        assert rankings[1]["rank"] == 2
        assert rankings[2]["rank"] == 3

        # 验证评分合理性
        for ranking in rankings:
            assert 0 <= ranking["score"] <= 1

    @pytest.mark.asyncio
    async def test_generate_rankings_empty_results(self, comparison_service):
        """测试空结果的排名生成"""
        rankings = await comparison_service.generate_rankings([])

        assert rankings == []

    @pytest.mark.asyncio
    async def test_generate_rankings_with_failures(self, comparison_service):
        """测试包含失败品种的排名生成"""
        results_with_failures = [
            {
                "symbol": "RB2410",
                "name": "螺纹钢2410",
                "sector": "金属",
                "exchange": "SHFE",
                "metrics": {"totalReturn": 0.15, "sharpeRatio": 1.2, "maxDrawdown": -0.08, "volatility": 0.12},
                "trades": [],
                "equity": [],
                "signals": []
            },
            {
                "symbol": "FAIL2410",
                "name": "失败品种",
                "sector": "未知",
                "exchange": "未知",
                "error": "数据获取失败",
                "trades": [],
                "equity": [],
                "signals": []
            }
        ]

        rankings = await comparison_service.generate_rankings(results_with_failures)

        # 应该只包含成功的结果
        assert len(rankings) == 1
        assert rankings[0]["symbol"] == "RB2410"

    def test_normalize_score_higher_better(self, comparison_service):
        """测试分数标准化（越高越好）"""
        # 正值
        score = comparison_service._normalize_score(0.5, higher_better=True)
        assert 0 < score < 1

        # 零值
        score = comparison_service._normalize_score(0, higher_better=True)
        assert score == 0

        # 负值
        score = comparison_service._normalize_score(-0.1, higher_better=True)
        assert score == 0

    def test_normalize_score_lower_better(self, comparison_service):
        """测试分数标准化（越低越好）"""
        # 正值（应该得到低分）
        score = comparison_service._normalize_score(0.5, higher_better=False)
        assert 0 < score < 1

        # 零值（应该得到满分）
        score = comparison_service._normalize_score(0, higher_better=False)
        assert score == 1

    @pytest.mark.asyncio
    async def test_calculate_correlation_matrix(self, comparison_service):
        """测试相关性矩阵计算"""
        # 创建具有相同日期的权益曲线数据
        results = [
            {
                "symbol": "RB2410",
                "equity": [
                    {"date": "2024-01-01", "equity": 100000},
                    {"date": "2024-01-02", "equity": 101000},
                    {"date": "2024-01-03", "equity": 100500}
                ]
            },
            {
                "symbol": "I2410",
                "equity": [
                    {"date": "2024-01-01", "equity": 100000},
                    {"date": "2024-01-02", "equity": 102000},
                    {"date": "2024-01-03", "equity": 101000}
                ]
            }
        ]

        correlation_matrix = await comparison_service.calculate_correlation_matrix(results)

        # 验证矩阵结构
        assert "symbols" in correlation_matrix
        assert "matrix" in correlation_matrix
        assert "averageCorrelation" in correlation_matrix
        assert "minCorrelation" in correlation_matrix
        assert "maxCorrelation" in correlation_matrix

        # 验证符号列表
        assert len(correlation_matrix["symbols"]) == 2
        assert "RB2410" in correlation_matrix["symbols"]
        assert "I2410" in correlation_matrix["symbols"]

        # 验证矩阵维度
        assert len(correlation_matrix["matrix"]) == 2
        assert len(correlation_matrix["matrix"][0]) == 2

        # 验证对角线元素（应该为1）
        assert correlation_matrix["matrix"][0][0] == pytest.approx(1.0)
        assert correlation_matrix["matrix"][1][1] == pytest.approx(1.0)

    @pytest.mark.asyncio
    async def test_calculate_correlation_matrix_insufficient_data(self, comparison_service):
        """测试数据不足的相关性矩阵计算"""
        # 只有一个品种的数据
        results = [
            {
                "symbol": "RB2410",
                "equity": [
                    {"date": "2024-01-01", "equity": 100000},
                    {"date": "2024-01-02", "equity": 101000}
                ]
            }
        ]

        correlation_matrix = await comparison_service.calculate_correlation_matrix(results)

        assert correlation_matrix == {}

    @pytest.mark.asyncio
    async def test_statistical_analysis(self, comparison_service, sample_results):
        """测试统计分析"""
        analysis = await comparison_service.statistical_analysis(sample_results)

        # 验证分析结构
        assert "normalityTest" in analysis
        assert "pairwiseTests" in analysis

        # 验证正态性检验
        normality_test = analysis["normalityTest"]
        assert "statistic" in normality_test
        assert "pValue" in normality_test
        assert "isNormal" in normality_test

        # 验证配对检验
        pairwise_tests = analysis["pairwiseTests"]
        assert len(pairwise_tests) > 0  # 应该有配对检验结果

    @pytest.mark.asyncio
    async def test_statistical_analysis_insufficient_data(self, comparison_service):
        """测试数据不足的统计分析"""
        analysis = await comparison_service.statistical_analysis([])

        assert analysis == {}

    @pytest.mark.asyncio
    async def test_calculate_metrics_edge_cases(self, comparison_service):
        """测试指标计算的边界情况"""
        # 所有交易都盈利的情况
        all_winning_result = {
            "trades": [{"pnl": 1000}, {"pnl": 500}, {"pnl": 200}],
            "equity": [
                {"date": "2024-01-01", "equity": 100000},
                {"date": "2024-01-02", "equity": 101000},
                {"date": "2024-01-03", "equity": 101500},
                {"date": "2024-01-04", "equity": 101700}
            ],
            "signals": []
        }

        metrics = await comparison_service.calculate_metrics(all_winning_result)

        assert metrics["winRate"] == 1.0  # 100%胜率
        assert metrics["profitFactor"] == float('inf')  # 无穷大盈亏比

        # 所有交易都亏损的情况
        all_losing_result = {
            "trades": [{"pnl": -1000}, {"pnl": -500}, {"pnl": -200}],
            "equity": [
                {"date": "2024-01-01", "equity": 100000},
                {"date": "2024-01-02", "equity": 99000},
                {"date": "2024-01-03", "equity": 98500},
                {"date": "2024-01-04", "equity": 98300}
            ],
            "signals": []
        }

        metrics = await comparison_service.calculate_metrics(all_losing_result)

        assert metrics["winRate"] == 0.0  # 0%胜率
        assert metrics["profitFactor"] == 0.0  # 零盈亏比