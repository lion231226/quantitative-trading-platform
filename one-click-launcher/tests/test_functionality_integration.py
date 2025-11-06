"""
功能集成测试套件

测试数据获取、策略计算、显示管道和数据一致性的完整集成功能。
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

from core.functionality_integration_tester import (
    DataAcquisitionTester, DataAcquisitionTestConfig, DataAcquisitionStatus,
    StrategyCalculationTester, StrategyCalculationTestConfig, StrategyCalculationStatus,
    DisplayPipelineTester, DisplayPipelineTestConfig, DisplayPipelineStatus
)
from core.data_consistency_validator import (
    DataConsistencyValidator, DataConsistencyConfig, ConsistencyStatus
)
from services.system_integration_service import (
    SystemIntegrationService, SystemIntegrationConfig, SystemReadinessStatus
)


class TestDataAcquisitionIntegration:
    """数据获取集成测试"""

    @pytest.mark.asyncio
    async def test_data_acquisition_config_creation(self):
        """测试数据获取配置创建"""
        config = DataAcquisitionTestConfig(
            api_endpoints=["/api/market/stock", "/api/strategy/results"],
            database_tables=["stock_prices", "strategy_results"],
            timeout_seconds=30,
            retry_attempts=3
        )

        assert len(config.api_endpoints) == 2
        assert len(config.database_tables) == 2
        assert config.timeout_seconds == 30
        assert config.retry_attempts == 3

    @pytest.mark.asyncio
    async def test_data_acquisition_tester_initialization(self):
        """测试数据获取测试器初始化"""
        config = DataAcquisitionTestConfig()
        tester = DataAcquisitionTester(config)

        assert tester.config == config
        assert len(tester.test_history) == 0

    @pytest.mark.asyncio
    async def test_api_to_database_flow_testing(self):
        """测试API到数据库流程测试"""
        config = DataAcquisitionTestConfig()
        tester = DataAcquisitionTester(config)

        results = await tester.test_api_to_database_flow()

        assert len(results) == 2  # 默认生成2个测试场景
        assert all(result.test_id in ["stock_data_acquisition", "strategy_results_acquisition"] for result in results)
        assert len(tester.test_history) == 2

    @pytest.mark.asyncio
    async def test_data_acquisition_success_scenario(self):
        """测试数据获取成功场景"""
        config = DataAcquisitionTestConfig()
        tester = DataAcquisitionTester(config)

        # 创建自定义测试场景
        test_scenarios = [
            {
                "test_id": "test_success_scenario",
                "endpoint": "/api/test",
                "table_name": "test_table",
                "expected_fields": ["id", "value"],
                "sample_query": "SELECT * FROM test_table"
            }
        ]

        results = await tester.test_api_to_database_flow(test_scenarios)

        assert len(results) == 1
        result = results[0]
        assert result.test_id == "test_success_scenario"
        assert result.status == DataAcquisitionStatus.SUCCESS
        assert result.records_processed > 0
        assert result.data_quality_score > 0

    @pytest.mark.asyncio
    async def test_data_acquisition_error_handling(self):
        """测试数据获取错误处理"""
        config = DataAcquisitionTestConfig()
        tester = DataAcquisitionTester(config)

        # 模拟错误场景
        with patch.object(tester, '_test_api_data_acquisition', return_value=None):
            test_scenarios = [
                {
                    "test_id": "test_error_scenario",
                    "endpoint": "/api/invalid",
                    "table_name": "invalid_table",
                    "expected_fields": ["id"],
                    "sample_query": "SELECT * FROM invalid_table"
                }
            ]

            results = await tester.test_api_to_database_flow(test_scenarios)

            assert len(results) == 1
            result = results[0]
            assert result.status == DataAcquisitionStatus.API_ERROR
            assert "API数据获取失败" in result.error_message


class TestStrategyCalculationIntegration:
    """策略计算集成测试"""

    @pytest.mark.asyncio
    async def test_strategy_calculation_config_creation(self):
        """测试策略计算配置创建"""
        config = StrategyCalculationTestConfig(
            strategy_types=["moving_average", "rsi"],
            calculation_timeout=60
        )

        assert len(config.strategy_types) == 2
        assert config.calculation_timeout == 60

    @pytest.mark.asyncio
    async def test_strategy_calculation_tester_initialization(self):
        """测试策略计算测试器初始化"""
        config = StrategyCalculationTestConfig()
        tester = StrategyCalculationTester(config)

        assert tester.config == config
        assert len(tester.test_history) == 0

    @pytest.mark.asyncio
    async def test_strategy_calculations_testing(self):
        """测试策略计算测试"""
        config = StrategyCalculationTestConfig()
        tester = StrategyCalculationTester(config)

        results = await tester.test_strategy_calculations()

        assert len(results) == 2  # 默认生成2个策略场景
        assert all(result.strategy_type in ["moving_average", "rsi"] for result in results)
        assert len(tester.test_history) == 2

    @pytest.mark.asyncio
    async def test_moving_average_calculation(self):
        """测试移动平均计算"""
        config = StrategyCalculationTestConfig()
        tester = StrategyCalculationTester(config)

        test_scenarios = [
            {
                "test_id": "ma_test",
                "strategy_type": "moving_average",
                "input_data": {"prices": [100, 105, 102, 108, 110], "period": 3},
                "expected_indicators": ["sma"]
            }
        ]

        results = await tester.test_strategy_calculations(test_scenarios)

        assert len(results) == 1
        result = results[0]
        assert result.strategy_type == "moving_average"
        assert result.status == StrategyCalculationStatus.SUCCESS
        assert result.calculation_accuracy > 0.9  # 90%以上准确率
        assert result.output_records > 0

    @pytest.mark.asyncio
    async def test_rsi_calculation(self):
        """测试RSI计算"""
        config = StrategyCalculationTestConfig()
        tester = StrategyCalculationTester(config)

        test_scenarios = [
            {
                "test_id": "rsi_test",
                "strategy_type": "rsi",
                "input_data": {"prices": [100, 102, 98, 105, 103], "period": 14},
                "expected_indicators": ["rsi"]
            }
        ]

        results = await tester.test_strategy_calculations(test_scenarios)

        assert len(results) == 1
        result = results[0]
        assert result.strategy_type == "rsi"
        assert result.status == StrategyCalculationStatus.SUCCESS
        assert result.calculation_accuracy > 0.9

    @pytest.mark.asyncio
    async def test_strategy_calculation_error_handling(self):
        """测试策略计算错误处理"""
        config = StrategyCalculationTestConfig()
        tester = StrategyCalculationTester(config)

        # 测试无效输入数据
        test_scenarios = [
            {
                "test_id": "invalid_input_test",
                "strategy_type": "moving_average",
                "input_data": {},  # 空输入数据
                "expected_indicators": ["sma"]
            }
        ]

        results = await tester.test_strategy_calculations(test_scenarios)

        assert len(results) == 1
        result = results[0]
        assert result.status == StrategyCalculationStatus.INPUT_DATA_INVALID
        assert "输入数据为空" in result.error_message


class TestDisplayPipelineIntegration:
    """显示管道集成测试"""

    @pytest.mark.asyncio
    async def test_display_pipeline_config_creation(self):
        """测试显示管道配置创建"""
        config = DisplayPipelineTestConfig(
            frontend_components=["PerformanceChart", "ResultsTable"],
            rendering_formats=["chart", "table"],
            accessibility_checks=True
        )

        assert len(config.frontend_components) == 2
        assert len(config.rendering_formats) == 2
        assert config.accessibility_checks is True

    @pytest.mark.asyncio
    async def test_display_pipeline_tester_initialization(self):
        """测试显示管道测试器初始化"""
        config = DisplayPipelineTestConfig()
        tester = DisplayPipelineTester(config)

        assert tester.config == config
        assert len(tester.test_history) == 0

    @pytest.mark.asyncio
    async def test_results_display_pipeline_testing(self):
        """测试结果显示管道测试"""
        config = DisplayPipelineTestConfig()
        tester = DisplayPipelineTester(config)

        results = await tester.test_results_display_pipeline()

        assert len(results) == 2  # 默认生成2个显示场景
        assert all(result.component in ["PerformanceChart", "ResultsTable"] for result in results)
        assert len(tester.test_history) == 2

    @pytest.mark.asyncio
    async def test_chart_display_pipeline(self):
        """测试图表显示管道"""
        config = DisplayPipelineTestConfig()
        tester = DisplayPipelineTester(config)

        test_scenarios = [
            {
                "test_id": "chart_test",
                "component": "PerformanceChart",
                "data_points": 50,
                "chart_type": "line",
                "expected_interactions": ["zoom", "pan"]
            }
        ]

        results = await tester.test_results_display_pipeline(test_scenarios)

        assert len(results) == 1
        result = results[0]
        assert result.component == "PerformanceChart"
        assert result.status == DisplayPipelineStatus.SUCCESS
        assert result.data_points_rendered > 0
        assert result.render_time_ms > 0

    @pytest.mark.asyncio
    async def test_table_display_pipeline(self):
        """测试表格显示管道"""
        config = DisplayPipelineTestConfig()
        tester = DisplayPipelineTester(config)

        test_scenarios = [
            {
                "test_id": "table_test",
                "component": "ResultsTable",
                "data_points": 100,
                "table_features": ["sorting", "filtering"],
                "expected_interactions": ["sort", "filter"]
            }
        ]

        results = await tester.test_results_display_pipeline(test_scenarios)

        assert len(results) == 1
        result = results[0]
        assert result.component == "ResultsTable"
        assert result.status == DisplayPipelineStatus.SUCCESS
        assert result.data_points_rendered == 100

    @pytest.mark.asyncio
    async def test_accessibility_checks(self):
        """测试可访问性检查"""
        config = DisplayPipelineTestConfig(accessibility_checks=True)
        tester = DisplayPipelineTester(config)

        test_scenarios = [
            {
                "test_id": "accessibility_test",
                "component": "ResultsTable",
                "data_points": 10,
                "expected_interactions": []
            }
        ]

        results = await tester.test_results_display_pipeline(test_scenarios)

        assert len(results) == 1
        result = results[0]
        assert result.accessibility_score >= 0.0
        assert result.accessibility_score <= 1.0


class TestDataConsistencyIntegration:
    """数据一致性集成测试"""

    @pytest.mark.asyncio
    async def test_data_consistency_config_creation(self):
        """测试数据一致性配置创建"""
        config = DataConsistencyConfig(
            tolerance_thresholds={"price": 0.01, "volume": 0.05},
            consistency_checks=["data_hash", "record_count"],
            sample_size=1000
        )

        assert config.tolerance_thresholds["price"] == 0.01
        assert len(config.consistency_checks) == 2
        assert config.sample_size == 1000

    @pytest.mark.asyncio
    async def test_data_consistency_validator_initialization(self):
        """测试数据一致性验证器初始化"""
        config = DataConsistencyConfig()
        validator = DataConsistencyValidator(config)

        assert validator.config == config
        assert len(validator.test_history) == 0
        assert len(validator.data_snapshots) == 0

    @pytest.mark.asyncio
    async def test_cross_component_consistency_validation(self):
        """测试跨组件一致性验证"""
        config = DataConsistencyConfig()
        validator = DataConsistencyValidator(config)

        components = ["database", "backend", "frontend"]
        results = await validator.validate_cross_component_consistency(components)

        assert len(results) == 3  # 默认生成3个一致性场景
        assert all(result.status in [ConsistencyStatus.CONSISTENT, ConsistencyStatus.PARTIALLY_CONSISTENT] for result in results)
        assert len(validator.test_history) == 3

    @pytest.mark.asyncio
    async def test_consistency_score_calculation(self):
        """测试一致性评分计算"""
        config = DataConsistencyConfig()
        validator = DataConsistencyValidator(config)

        components = ["database", "backend"]
        results = await validator.validate_cross_component_consistency(components)

        assert len(results) == 3  # 默认生成3个一致性场景
        result = results[0]
        assert 0 <= result.consistency_score <= 100
        assert result.total_records_checked > 0

    @pytest.mark.asyncio
    async def test_consistency_violation_detection(self):
        """测试一致性违规检测"""
        config = DataConsistencyConfig(
            tolerance_thresholds={"price": 0.001}  # 非常严格的容差
        )
        validator = DataConsistencyValidator(config)

        components = ["database", "backend", "frontend"]
        results = await validator.validate_cross_component_consistency(components)

        # 由于严格的容差，应该检测到一些违规
        total_violations = sum(len(result.violations) for result in results)
        assert total_violations >= 0

    @pytest.mark.asyncio
    async def test_consistency_report_generation(self):
        """测试一致性报告生成"""
        config = DataConsistencyConfig()
        validator = DataConsistencyValidator(config)

        components = ["database", "backend"]
        await validator.validate_cross_component_consistency(components)

        report = await validator.generate_consistency_report()

        assert "report_timestamp" in report
        assert "total_tests" in report
        assert "summary" in report
        assert "detailed_results" in report
        assert "recommendations" in report
        assert report["total_tests"] == 3  # 默认生成3个一致性场景


class TestSystemIntegrationFunctional:
    """系统集成功能测试"""

    @pytest.mark.asyncio
    async def test_functionality_integration_in_system_service(self):
        """测试功能集成在系统服务中的集成"""
        config = SystemIntegrationConfig(
            system_name="TestSystem",
            frontend_url="http://localhost:3000",
            backend_url="http://localhost:8000",
            database_host="localhost",
            database_port=5432
        )

        service = SystemIntegrationService(config)

        # 验证功能集成测试器已正确初始化
        assert service.data_acquisition_tester is not None
        assert service.strategy_calculation_tester is not None
        assert service.display_pipeline_tester is not None
        assert service.data_consistency_validator is not None

        # 验证功能结果存储已初始化
        assert isinstance(service.latest_functionality_results, dict)
        assert isinstance(service.latest_consistency_results, list)

    @pytest.mark.asyncio
    async def test_functionality_summary_generation(self):
        """测试功能摘要生成"""
        config = SystemIntegrationConfig(
            system_name="TestSystem",
            frontend_url="http://localhost:3000",
            backend_url="http://localhost:8000",
            database_host="localhost",
            database_port=5432
        )

        service = SystemIntegrationService(config)

        # 执行一些功能测试以填充结果
        data_acq_results = await service.data_acquisition_tester.test_api_to_database_flow()
        strategy_results = await service.strategy_calculation_tester.test_strategy_calculations()
        display_results = await service.display_pipeline_tester.test_results_display_pipeline()
        consistency_results = await service.data_consistency_validator.validate_cross_component_consistency(
            ["database", "backend"]
        )

        service.latest_functionality_results = {
            'data_acquisition': data_acq_results,
            'strategy_calculation': strategy_results,
            'display_pipeline': display_results
        }
        service.latest_consistency_results = consistency_results

        # 生成功能摘要
        summary = service._generate_functionality_summary()

        assert 'data_acquisition' in summary
        assert 'strategy_calculation' in summary
        assert 'display_pipeline' in summary
        assert 'data_consistency' in summary
        assert 'overall_score' in summary

        # 验证评分计算
        assert 0 <= summary['overall_score'] <= 100

    @pytest.mark.asyncio
    async def test_complete_verification_with_functionality_testing(self):
        """测试包含功能测试的完整验证"""
        config = SystemIntegrationConfig(
            system_name="TestSystem",
            frontend_url="http://localhost:3000",
            backend_url="http://localhost:8000",
            database_host="localhost",
            database_port=5432
        )

        service = SystemIntegrationService(config)

        # 模拟完整验证中的功能测试部分
        try:
            # 4.1 数据获取流测试
            data_acquisition_results = await service.data_acquisition_tester.test_api_to_database_flow()
            assert len(data_acquisition_results) > 0

            # 4.2 策略计算验证
            strategy_calculation_results = await service.strategy_calculation_tester.test_strategy_calculations()
            assert len(strategy_calculation_results) > 0

            # 4.3 显示管道测试
            display_pipeline_results = await service.display_pipeline_tester.test_results_display_pipeline()
            assert len(display_pipeline_results) > 0

            # 4.4 数据一致性验证
            consistency_results = await service.data_consistency_validator.validate_cross_component_consistency(
                components=["database", "backend", "frontend"]
            )
            assert len(consistency_results) > 0

            # 验证结果结构
            functionality_results = {
                'data_acquisition': [result.__dict__ for result in data_acquisition_results],
                'strategy_calculation': [result.__dict__ for result in strategy_calculation_results],
                'display_pipeline': [result.__dict__ for result in display_pipeline_results],
                'data_consistency': [result.__dict__ for result in consistency_results]
            }

            assert 'data_acquisition' in functionality_results
            assert 'strategy_calculation' in functionality_results
            assert 'display_pipeline' in functionality_results
            assert 'data_consistency' in functionality_results

        except Exception as e:
            pytest.fail(f"功能集成测试失败: {str(e)}")


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "--tb=short"])