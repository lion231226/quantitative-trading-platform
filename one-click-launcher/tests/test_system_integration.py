"""
系统集成验证测试

测试完整的系统集成验证功能，包括管道验证、性能监控、错误处理和报告生成。
"""

import pytest
import asyncio
import json
import time
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
from pathlib import Path

from core.pipeline_verifier import (
    PipelineVerifier, PipelineConfig, PipelineStatus, PipelineStage
)
from core.performance_monitor import (
    PerformanceMonitor, MetricType, AlertLevel
)
from core.error_handler_validator import (
    ErrorHandlerValidator, ErrorType, ErrorSeverity
)
from services.system_integration_service import (
    SystemIntegrationService, SystemIntegrationConfig, SystemReadinessStatus
)
from utils.readiness_reporter import (
    ReadinessReporter, ReportFormat, ReportType
)


class TestPipelineVerifier:
    """管道验证器测试"""

    @pytest.fixture
    def pipeline_config(self):
        """管道验证配置"""
        return PipelineConfig(
            frontend_url="http://localhost:3000",
            backend_url="http://localhost:8000",
            database_host="localhost",
            database_port=5432,
            test_endpoints=[],
            database_test_queries=[],
            timeout=30
        )

    @pytest.fixture
    def pipeline_verifier(self, pipeline_config):
        """管道验证器实例"""
        return PipelineVerifier(pipeline_config)

    @pytest.mark.asyncio
    async def test_pipeline_verifier_initialization(self, pipeline_verifier):
        """测试管道验证器初始化"""
        assert pipeline_verifier.config.frontend_url == "http://localhost:3000"
        assert pipeline_verifier.config.backend_url == "http://localhost:8000"
        assert pipeline_verifier.config.database_host == "localhost"
        assert pipeline_verifier.config.database_port == 5432
        assert pipeline_verifier.config.timeout == 30

    @pytest.mark.asyncio
    async def test_generate_default_test_requests(self, pipeline_verifier):
        """测试生成默认测试请求"""
        requests = pipeline_verifier._generate_default_test_requests()

        assert len(requests) == 2
        assert requests[0].test_data['type'] == 'health_check'
        assert requests[1].test_data['type'] == 'data_query'
        assert all(PipelineStage.FRONTEND in req.expected_pipeline for req in requests)

    @pytest.mark.asyncio
    async def test_detect_bottleneck(self, pipeline_verifier):
        """测试瓶颈检测"""
        from one_click_launcher.core.pipeline_verifier import PipelineStep

        # 创建测试步骤
        steps = [
            PipelineStep(PipelineStage.FRONTEND, "Frontend", "Test", duration=0.1),
            PipelineStep(PipelineStage.BACKEND_API, "Backend", "Test", duration=5.0),  # 瓶颈
            PipelineStep(PipelineStage.DATABASE, "Database", "Test", duration=0.5)
        ]

        bottleneck = pipeline_verifier._detect_bottleneck(steps)
        assert bottleneck == PipelineStage.BACKEND_API

    @pytest.mark.asyncio
    async def test_calculate_performance_metrics(self, pipeline_verifier):
        """测试性能指标计算"""
        from one_click_launcher.core.pipeline_verifier import PipelineStep

        steps = [
            PipelineStep(PipelineStage.FRONTEND, "Frontend", "Test", duration=0.1),
            PipelineStep(PipelineStage.BACKEND_API, "Backend", "Test", duration=1.0),
            PipelineStep(PipelineStage.DATABASE, "Database", "Test", duration=0.5)
        ]

        metrics = pipeline_verifier._calculate_performance_metrics(steps)

        assert 'total_pipeline_time' in metrics
        assert 'frontend_time' in metrics
        assert 'backend_api_time' in metrics
        assert 'database_time' in metrics
        assert metrics['total_pipeline_time'] == 1.6

    @pytest.mark.asyncio
    async def test_pipeline_summary_calculation(self, pipeline_verifier):
        """测试管道摘要计算"""
        from one_click_launcher.core.pipeline_verifier import PipelineTestResult

        # 创建模拟结果
        results = [
            PipelineTestResult(
                request_id="test1",
                overall_status=PipelineStatus.HEALTHY,
                total_duration=1.0,
                steps=[],
                success_rate=1.0
            ),
            PipelineTestResult(
                request_id="test2",
                overall_status=PipelineStatus.DEGRADED,
                total_duration=2.0,
                steps=[],
                success_rate=0.8
            )
        ]

        summary = pipeline_verifier.get_pipeline_summary(results)

        assert summary['total_tests'] == 2
        assert summary['successful_tests'] == 1
        assert summary['degraded_tests'] == 1
        assert summary['success_rate'] == 0.5
        assert summary['average_duration'] == 1.5


class TestPerformanceMonitor:
    """性能监控器测试"""

    @pytest.fixture
    def performance_monitor(self):
        """性能监控器实例"""
        return PerformanceMonitor(monitoring_interval=5)

    def test_performance_monitor_initialization(self, performance_monitor):
        """测试性能监控器初始化"""
        assert performance_monitor.monitoring_interval == 5
        assert not performance_monitor.monitoring_active
        assert len(performance_monitor.metrics_history) == 0

    def test_initialize_default_thresholds(self, performance_monitor):
        """测试默认阈值初始化"""
        thresholds = performance_monitor._initialize_default_thresholds()

        assert 'frontend_response_time' in thresholds
        assert 'backend_response_time' in thresholds
        assert 'database_query_time' in thresholds
        assert 'cpu_usage' in thresholds
        assert 'memory_usage' in thresholds

    @pytest.mark.asyncio
    async def test_add_metric(self, performance_monitor):
        """测试添加性能指标"""
        from one_click_launcher.core.performance_monitor import PerformanceMetric

        metric = PerformanceMetric(
            metric_type=MetricType.RESPONSE_TIME,
            service_name="test_service",
            value=1.5,
            unit="seconds",
            timestamp=datetime.now()
        )

        performance_monitor._add_metric(metric)

        key = "test_service_response_time"
        assert key in performance_monitor.metrics_history
        assert len(performance_monitor.metrics_history[key]) == 1
        assert performance_monitor.metrics_history[key][0].value == 1.5

    @pytest.mark.asyncio
    async def test_measure_request_latency(self, performance_monitor):
        """测试请求延迟测量"""
        request_id = "test_request_123"

        with patch('aiohttp.ClientSession') as mock_session:
            # 模拟HTTP响应
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = {"status": "ok"}

            mock_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value = mock_response
            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value = mock_response

            measurement = await performance_monitor.measure_request_latency(
                request_id,
                "http://localhost:3000",
                "http://localhost:8000"
            )

            assert measurement.request_id == request_id
            assert measurement.total_latency > 0
            assert 'frontend_to_backend' in measurement.stages
            assert 'backend_processing' in measurement.stages

    @pytest.mark.asyncio
    async def test_performance_summary_generation(self, performance_monitor):
        """测试性能摘要生成"""
        # 添加一些测试指标
        from one_click_launcher.core.performance_monitor import PerformanceMetric

        for i in range(10):
            metric = PerformanceMetric(
                metric_type=MetricType.RESPONSE_TIME,
                service_name="test_service",
                value=1.0 + i * 0.1,
                unit="seconds",
                timestamp=datetime.now() - timedelta(minutes=i)
            )
            performance_monitor._add_metric(metric)

        summary = performance_monitor.get_performance_summary(time_range=60)

        assert 'generated_at' in summary
        assert 'services' in summary
        assert 'alerts' in summary
        assert 'latency_analysis' in summary
        assert 'bottleneck_analysis' in summary

    def test_alert_generation(self, performance_monitor):
        """测试告警生成"""
        from one_click_launcher.core.performance_monitor import PerformanceMetric, PerformanceAlert

        # 添加超过阈值的指标
        metric = PerformanceMetric(
            metric_type=MetricType.CPU_USAGE,
            service_name="system",
            value=95.0,  # 超过阈值
            unit="percent",
            timestamp=datetime.now()
        )

        performance_monitor._add_metric(metric)
        performance_monitor._check_alerts()

        # 检查是否生成了告警
        assert len(performance_monitor.active_alerts) > 0

        alert = list(performance_monitor.active_alerts.values())[0]
        assert alert.level == AlertLevel.CRITICAL
        assert alert.metric_type == MetricType.CPU_USAGE


class TestErrorHandlerValidator:
    """错误处理验证器测试"""

    @pytest.fixture
    def error_validator(self):
        """错误处理验证器实例"""
        return ErrorHandlerValidator(
            frontend_url="http://localhost:3000",
            backend_url="http://localhost:8000"
        )

    def test_error_validator_initialization(self, error_validator):
        """测试错误处理验证器初始化"""
        assert error_validator.frontend_url == "http://localhost:3000"
        assert error_validator.backend_url == "http://localhost:8000"
        assert len(error_validator.error_scenarios) > 0
        assert len(error_validator.test_results) == 0

    def test_initialize_error_scenarios(self, error_validator):
        """测试错误场景初始化"""
        scenarios = error_validator._initialize_error_scenarios()

        assert len(scenarios) > 0

        # 检查是否有各种类型的错误场景
        error_types = [s.error_type for s in scenarios]
        assert ErrorType.NETWORK_ERROR in error_types
        assert ErrorType.DATABASE_ERROR in error_types
        assert ErrorType.VALIDATION_ERROR in error_types

    def test_validate_user_message(self, error_validator):
        """测试用户消息验证"""
        # 测试清晰的消息
        clear, actionable = error_validator._validate_user_message(
            None, "请求失败，请检查输入参数后重试"
        )
        assert clear is True
        assert actionable is True

        # 测试不清晰的消息
        clear, actionable = error_validator._validate_user_message(
            None, "ERROR"
        )
        assert clear is False
        assert actionable is False

    def test_validate_recovery_mechanism(self, error_validator):
        """测试恢复机制验证"""
        # 测试有重试机制的情况
        details = {'retry_count': 3, 'fallback_used': True}
        recovery, degradation = error_validator._validate_recovery_mechanism(None, details)
        assert recovery is True
        assert degradation is True

        # 测试没有恢复机制的情况
        details = {}
        recovery, degradation = error_validator._validate_recovery_mechanism(None, details)
        assert recovery is False
        assert degradation is False

    def test_calculate_overall_score(self, error_validator):
        """测试总体评分计算"""
        from one_click_launcher.core.error_handler_validator import ErrorTestResult

        # 创建测试结果
        results = [
            ErrorTestResult(
                scenario_id="test1",
                error_triggered=True,
                error_propagated_correctly=True,
                user_message_clear=True,
                user_message_actionable=True,
                recovery_mechanism_triggered=True,
                graceful_degradation_achieved=True
            ),
            ErrorTestResult(
                scenario_id="test2",
                error_triggered=True,
                error_propagated_correctly=False,
                user_message_clear=False,
                user_message_actionable=False,
                recovery_mechanism_triggered=False,
                graceful_degradation_achieved=False
            )
        ]

        score = error_validator._calculate_overall_score(results)
        assert 0 <= score <= 100
        assert score == 50.0  # 一个完美，一个零分


class TestSystemIntegrationService:
    """系统集成服务测试"""

    @pytest.fixture
    def integration_config(self):
        """系统集成配置"""
        return SystemIntegrationConfig(
            system_name="TestSystem",
            frontend_url="http://localhost:3000",
            backend_url="http://localhost:8000",
            database_host="localhost",
            database_port=5432,
            monitoring_interval=5,
            certificate_validity_hours=1
        )

    @pytest.fixture
    def integration_service(self, integration_config):
        """系统集成服务实例"""
        return SystemIntegrationService(integration_config)

    def test_integration_service_initialization(self, integration_service):
        """测试系统集成服务初始化"""
        assert integration_service.config.system_name == "TestSystem"
        assert integration_service.config.frontend_url == "http://localhost:3000"
        assert integration_service.config.backend_url == "http://localhost:8000"
        assert integration_service.pipeline_verifier is not None
        assert integration_service.performance_monitor is not None
        assert integration_service.error_handler_validator is not None

    def test_calculate_pipeline_score(self, integration_service):
        """测试管道评分计算"""
        from one_click_launcher.core.pipeline_verifier import PipelineTestResult, PipelineStatus

        # 创建模拟结果
        results = [
            PipelineTestResult(
                request_id="test1",
                overall_status=PipelineStatus.HEALTHY,
                total_duration=1.0,
                steps=[],
                success_rate=1.0
            ),
            PipelineTestResult(
                request_id="test2",
                overall_status=PipelineStatus.HEALTHY,
                total_duration=3.0,
                steps=[],
                success_rate=1.0
            )
        ]

        integration_service.latest_pipeline_results = results
        score = integration_service._calculate_pipeline_score()

        assert 0 <= score <= 100
        # 两个成功的测试，但平均响应时间2秒，应该有一些扣分
        assert score >= 70  # 成功率满分，但响应时间有一些扣分

    def test_calculate_performance_score(self, integration_service):
        """测试性能评分计算"""
        # 模拟性能摘要
        performance_summary = {
            'alerts': {'critical': 0, 'warning': 1},
            'bottleneck_analysis': {'severity': 'low'}
        }

        with patch.object(integration_service.performance_monitor, 'get_performance_summary', return_value=performance_summary):
            score = integration_service._calculate_performance_score()

            assert 0 <= score <= 100
            assert score >= 85  # 只有警告，没有严重告警

    def test_determine_overall_status(self, integration_service):
        """测试整体状态确定"""
        from one_click_launcher.services.system_integration_service import SystemReadinessCertificate

        # 测试有证书的情况
        certificate = SystemReadinessCertificate(
            certificate_id="test",
            system_name="TestSystem",
            overall_status=SystemReadinessStatus.READY,
            readiness_score=95.0,
            pipeline_status={},
            performance_status={},
            error_handling_status={},
            integration_score=95.0,
            generated_at=datetime.now(),
            expires_at=datetime.now() + timedelta(hours=1),
            recommendations=[],
            next_check_time=datetime.now() + timedelta(hours=1)
        )

        integration_service.latest_certificate = certificate
        status = integration_service._determine_overall_status()
        assert status == "ready"

    @pytest.mark.asyncio
    async def test_perform_health_checks(self, integration_service):
        """测试健康检查执行"""
        with patch.object(integration_service.health_checker, 'check_multiple_services', return_value={}) as mock_check:
            await integration_service._perform_health_checks()
            mock_check.assert_called_once()

    def test_should_update_certificate(self, integration_service):
        """测试证书更新检查"""
        # 测试没有证书的情况
        assert integration_service._should_update_certificate() is True

        # 测试有过期证书的情况
        from one_click_launcher.services.system_integration_service import SystemReadinessCertificate

        expired_certificate = SystemReadinessCertificate(
            certificate_id="test",
            system_name="TestSystem",
            overall_status=SystemReadinessStatus.READY,
            readiness_score=95.0,
            pipeline_status={},
            performance_status={},
            error_handling_status={},
            integration_score=95.0,
            generated_at=datetime.now() - timedelta(hours=2),
            expires_at=datetime.now() - timedelta(hours=1),  # 已过期
            recommendations=[],
            next_check_time=datetime.now() - timedelta(hours=1)
        )

        integration_service.latest_certificate = expired_certificate
        assert integration_service._should_update_certificate() is True


class TestReadinessReporter:
    """就绪报告生成器测试"""

    @pytest.fixture
    def mock_integration_service(self):
        """模拟集成服务"""
        service = MagicMock()
        service.config.system_name = "TestSystem"
        service.latest_certificate = None
        service.generated_reports = []
        return service

    @pytest.fixture
    def readiness_reporter(self, mock_integration_service):
        """就绪报告生成器实例"""
        return ReadinessReporter(mock_integration_service)

    def test_readiness_reporter_initialization(self, readiness_reporter):
        """测试就绪报告生成器初始化"""
        assert readiness_reporter.integration_service == readiness_reporter.mock_integration_service
        assert len(readiness_reporter.report_templates) > 0
        assert readiness_reporter.output_dir.exists()

    def test_initialize_templates(self, readiness_reporter):
        """测试报告模板初始化"""
        templates = readiness_reporter._initialize_templates()

        assert 'summary_json' in templates
        assert 'summary_markdown' in templates
        assert 'detailed_markdown' in templates
        assert 'detailed_html' in templates
        assert 'technical_markdown' in templates
        assert 'executive_html' in templates

    def test_extract_key_metrics(self, readiness_reporter):
        """测试关键指标提取"""
        from one_click_launcher.services.system_integration_service import SystemReadinessCertificate, SystemReadinessStatus

        certificate = SystemReadinessCertificate(
            certificate_id="test",
            system_name="TestSystem",
            overall_status=SystemReadinessStatus.READY,
            readiness_score=95.0,
            pipeline_status={'status': True},
            performance_status={'status': True},
            error_handling_status={'overall_score': 90.0},
            integration_score=95.0,
            generated_at=datetime.now(),
            expires_at=datetime.now() + timedelta(hours=1),
            recommendations=[],
            next_check_time=datetime.now() + timedelta(hours=1)
        )

        metrics = readiness_reporter._extract_key_metrics(certificate)

        assert metrics['readiness_score'] == 95.0
        assert metrics['integration_score'] == 95.0
        assert metrics['overall_status'] == 'ready'
        assert metrics['pipeline_health'] is True
        assert metrics['performance_health'] is True
        assert metrics['error_handling_score'] == 90.0

    def test_generate_markdown_report(self, readiness_reporter):
        """测试Markdown报告生成"""
        from one_click_launcher.services.system_integration_service import SystemReadinessCertificate, SystemReadinessStatus

        certificate = SystemReadinessCertificate(
            certificate_id="test",
            system_name="TestSystem",
            overall_status=SystemReadinessStatus.READY,
            readiness_score=95.0,
            pipeline_status={'status': True, 'success_rate': 1.0, 'total_tests': 5},
            performance_status={'status': True, 'active_alerts': {'critical': 0, 'warning': 0}},
            error_handling_status={'status': True, 'overall_score': 90.0, 'total_tests': 8},
            integration_score=95.0,
            generated_at=datetime.now(),
            expires_at=datetime.now() + timedelta(hours=1),
            recommendations=["建议1", "建议2"],
            next_check_time=datetime.now() + timedelta(hours=1)
        )

        template = readiness_reporter.report_templates['summary_markdown']
        content = readiness_reporter._generate_markdown_report(template, certificate)

        assert "TestSystem 系统就绪报告" in content
        assert "95.0/100" in content
        assert "READY" in content
        assert "建议1" in content
        assert "建议2" in content

    def test_generate_html_report(self, readiness_reporter):
        """测试HTML报告生成"""
        from one_click_launcher.services.system_integration_service import SystemReadinessCertificate, SystemReadinessStatus

        certificate = SystemReadinessCertificate(
            certificate_id="test",
            system_name="TestSystem",
            overall_status=SystemReadinessStatus.READY,
            readiness_score=95.0,
            pipeline_status={'status': True, 'success_rate': 1.0},
            performance_status={'status': True, 'active_alerts': {'critical': 0, 'warning': 0}},
            error_handling_status={'status': True, 'overall_score': 90.0},
            integration_score=95.0,
            generated_at=datetime.now(),
            expires_at=datetime.now() + timedelta(hours=1),
            recommendations=["建议1"],
            next_check_time=datetime.now() + timedelta(hours=1)
        )

        template = readiness_reporter.report_templates['summary_html']
        content = readiness_reporter._generate_html_report(template, certificate)

        assert "<!DOCTYPE html>" in content
        assert "TestSystem 系统就绪报告" in content
        assert "95.0" in content
        assert "READY" in content

    def test_calculate_content_hash(self, readiness_reporter):
        """测试内容哈希计算"""
        content = "test content"
        hash1 = readiness_reporter._calculate_content_hash(content)
        hash2 = readiness_reporter._calculate_content_hash(content)

        assert hash1 == hash2
        assert len(hash1) == 16

    def test_get_available_templates(self, readiness_reporter):
        """测试获取可用模板"""
        templates = readiness_reporter.get_available_templates()

        assert len(templates) > 0
        assert 'summary_json' in templates
        assert 'detailed_markdown' in templates


class TestIntegrationWorkflow:
    """集成工作流测试"""

    @pytest.fixture
    def integration_config(self):
        """集成配置"""
        return SystemIntegrationConfig(
            system_name="TestSystem",
            frontend_url="http://localhost:3000",
            backend_url="http://localhost:8000",
            database_host="localhost",
            database_port=5432,
            monitoring_interval=1,
            certificate_validity_hours=1
        )

    @pytest.mark.asyncio
    async def test_complete_verification_workflow(self, integration_config):
        """测试完整验证工作流"""
        # 由于这是集成测试，我们使用模拟来避免依赖外部服务
        with patch('core.pipeline_verifier.FrontendBackendCommunicator') as mock_comm:
            with patch('aiohttp.ClientSession') as mock_session:
                # 模拟通信验证成功
                mock_comm.return_value.__aenter__.return_value.verify_communication.return_value = MagicMock(
                    overall_status="connected",
                    average_response_time=0.5,
                    successful_endpoints=1,
                    total_endpoints=1
                )

                # 模拟HTTP请求成功
                mock_response = AsyncMock()
                mock_response.status = 200
                mock_response.json.return_value = {"status": "ok", "processing_time": 0.1}
                mock_session.return_value.__aenter__.return_value.request.return_value.__aenter__.return_value = mock_response
                mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value = mock_response
                mock_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value = mock_response

                # 创建服务
                service = SystemIntegrationService(integration_config)

                # 执行验证（使用更简单的模拟）
                with patch.object(service.pipeline_verifier, 'verify_complete_pipeline') as mock_pipeline:
                    with patch.object(service.performance_monitor, 'measure_request_latency') as mock_latency:
                        with patch.object(service.error_handler_validator, 'validate_error_handling') as mock_error:

                            # 模拟返回值
                            mock_pipeline.return_value = []
                            mock_latency.return_value = MagicMock(to_dict=lambda: {
                                'request_id': 'test',
                                'total_latency': 1.0
                            })
                            mock_error.return_value = MagicMock(__dict__={
                                'overall_score': 85.0,
                                'test_results': []
                            })

                            # 执行验证
                            result = await service.perform_complete_verification()

                            # 验证结果结构
                            assert 'verification_id' in result
                            assert 'system_name' in result
                            assert 'start_time' in result
                            assert 'duration' in result
                            assert 'results' in result
                            assert result['system_name'] == "TestSystem"

    @pytest.mark.asyncio
    async def test_readiness_certificate_generation(self, integration_config):
        """测试就绪证书生成"""
        service = SystemIntegrationService(integration_config)

        # 模拟一些验证结果
        from one_click_launcher.core.pipeline_verifier import PipelineTestResult, PipelineStatus

        service.latest_pipeline_results = [
            PipelineTestResult(
                request_id="test",
                overall_status=PipelineStatus.HEALTHY,
                total_duration=1.0,
                steps=[],
                success_rate=1.0
            )
        ]

        # 模拟性能监控器
        with patch.object(service.performance_monitor, 'get_performance_summary', return_value={
            'alerts': {'critical': 0, 'warning': 0},
            'bottleneck_analysis': {'severity': 'low'}
        }):
            certificate = await service.generate_readiness_certificate()

            assert certificate.system_name == "TestSystem"
            assert certificate.certificate_id.startswith("cert_")
            assert 0 <= certificate.readiness_score <= 100
            assert 0 <= certificate.integration_score <= 100
            assert certificate.overall_status in [SystemReadinessStatus.READY, SystemReadinessStatus.DEGRADED, SystemReadinessStatus.NOT_READY]
            assert len(certificate.recommendations) >= 0


# 运行测试的便捷函数
def run_integration_tests():
    """运行集成测试"""
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-x"  # 遇到第一个失败就停止
    ])


if __name__ == "__main__":
    run_integration_tests()