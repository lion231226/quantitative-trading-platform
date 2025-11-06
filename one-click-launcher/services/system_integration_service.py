"""
系统集成服务

提供完整的系统集成验证功能，包括管道验证、性能监控、错误处理验证和系统就绪报告生成。
整合所有验证组件，提供统一的系统健康状态监控和报告。
"""

import asyncio
import json
import time
import uuid
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from pathlib import Path

from core.pipeline_verifier import (
    PipelineVerifier, PipelineConfig, PipelineTestResult,
    PipelineStatus, PipelineIntegrityResult
)
from core.performance_monitor import (
    PerformanceMonitor, PerformanceReport, AlertLevel,
    PerformanceThreshold, MetricType
)
from core.error_handler_validator import (
    ErrorHandlerValidator, ErrorHandlingReport, ErrorType
)
from core.health_checker import HealthChecker, HealthStatus
from core.service_dependency_analyzer import ServiceInfo, ServiceType
from core.functionality_integration_tester import (
    DataAcquisitionTester, StrategyCalculationTester, DisplayPipelineTester,
    DataAcquisitionTestConfig, StrategyCalculationTestConfig, DisplayPipelineTestConfig
)
from core.data_consistency_validator import (
    DataConsistencyValidator, DataConsistencyConfig
)
from utils.progress_tracker import ProgressTracker, ProgressStep, ProgressStatus
from utils.logger import get_logger

logger = get_logger(__name__)


class SystemReadinessStatus(Enum):
    """系统就绪状态"""
    NOT_READY = "not_ready"
    DEGRADED = "degraded"
    READY = "ready"
    ERROR = "error"


@dataclass
class SystemReadinessCertificate:
    """系统就绪证书"""
    certificate_id: str
    system_name: str
    overall_status: SystemReadinessStatus
    readiness_score: float  # 0-100
    pipeline_status: Dict[str, Any]
    performance_status: Dict[str, Any]
    error_handling_status: Dict[str, Any]
    integration_score: float
    generated_at: datetime
    expires_at: datetime
    recommendations: List[str]
    next_check_time: datetime

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'certificate_id': self.certificate_id,
            'system_name': self.system_name,
            'overall_status': self.overall_status.value,
            'readiness_score': self.readiness_score,
            'pipeline_status': self.pipeline_status,
            'performance_status': self.performance_status,
            'error_handling_status': self.error_handling_status,
            'integration_score': self.integration_score,
            'generated_at': self.generated_at.isoformat(),
            'expires_at': self.expires_at.isoformat(),
            'recommendations': self.recommendations,
            'next_check_time': self.next_check_time.isoformat()
        }


@dataclass
class SystemIntegrationConfig:
    """系统集成配置"""
    system_name: str
    frontend_url: str
    backend_url: str
    database_host: str
    database_port: int
    monitoring_interval: int = 30
    test_duration: int = 300  # 5分钟
    performance_thresholds: Dict[str, float] = field(default_factory=dict)
    error_handling_enabled: bool = True
    performance_monitoring_enabled: bool = True
    pipeline_verification_enabled: bool = True
    certificate_validity_hours: int = 24


class SystemIntegrationService:
    """
    系统集成服务

    功能特性：
    - 完整系统集成验证
    - 实时健康状态监控
    - 性能指标收集和分析
    - 错误处理机制验证
    - 系统就绪证书生成
    - 自动化报告和建议
    """

    def __init__(self, config: SystemIntegrationConfig):
        """
        初始化系统集成服务

        Args:
            config: 系统集成配置
        """
        self.config = config
        self.logger = get_logger(self.__class__.__name__)

        # 初始化组件
        self.progress_tracker = ProgressTracker(
            component_name="system_integration_verification"
        )

        # 管道验证器
        if config.pipeline_verification_enabled:
            pipeline_config = PipelineConfig(
                frontend_url=config.frontend_url,
                backend_url=config.backend_url,
                database_host=config.database_host,
                database_port=config.database_port,
                test_endpoints=[],
                database_test_queries=[],
                timeout=30,
                performance_thresholds=config.performance_thresholds
            )
            self.pipeline_verifier = PipelineVerifier(pipeline_config)
        else:
            self.pipeline_verifier = None

        # 性能监控器
        if config.performance_monitoring_enabled:
            self.performance_monitor = PerformanceMonitor(
                monitoring_interval=config.monitoring_interval
            )
        else:
            self.performance_monitor = None

        # 错误处理验证器
        if config.error_handling_enabled:
            self.error_handler_validator = ErrorHandlerValidator(
                frontend_url=config.frontend_url,
                backend_url=config.backend_url
            )
        else:
            self.error_handler_validator = None

        # 健康检查器
        self.health_checker = HealthChecker()

        # 功能集成测试器
        self.data_acquisition_tester = DataAcquisitionTester(
            DataAcquisitionTestConfig(
                api_endpoints=["/api/market/stock", "/api/strategy/results"],
                database_tables=["stock_prices", "strategy_results"],
                timeout_seconds=30,
                retry_attempts=3
            )
        )

        self.strategy_calculation_tester = StrategyCalculationTester(
            StrategyCalculationTestConfig(
                strategy_types=["moving_average", "rsi"],
                calculation_timeout=60
            )
        )

        self.display_pipeline_tester = DisplayPipelineTester(
            DisplayPipelineTestConfig(
                frontend_components=["PerformanceChart", "ResultsTable"],
                rendering_formats=["chart", "table"],
                accessibility_checks=True
            )
        )

        # 数据一致性验证器
        self.data_consistency_validator = DataConsistencyValidator(
            DataConsistencyConfig(
                tolerance_thresholds={"price": 0.01, "volume": 0.05},
                consistency_checks=["data_hash", "record_count", "value_consistency"],
                sample_size=1000
            )
        )

        # 验证结果存储
        self.latest_pipeline_results: List[PipelineTestResult] = []
        self.latest_performance_report: Optional[PerformanceReport] = None
        self.latest_error_report: Optional[ErrorHandlingReport] = None
        self.latest_functionality_results: Dict[str, List[Any]] = {}
        self.latest_consistency_results: List[Any] = []
        self.latest_certificate: Optional[SystemReadinessCertificate] = None

        # 监控状态
        self.monitoring_active = False
        self.monitoring_task: Optional[asyncio.Task] = None

        self.logger.info(f"系统集成服务初始化完成: {config.system_name}")

    async def start_monitoring(self):
        """开始系统监控"""
        if self.monitoring_active:
            self.logger.warning("系统监控已在运行中")
            return

        self.monitoring_active = True

        # 启动性能监控
        if self.performance_monitor:
            await self.performance_monitor.start_monitoring()

        # 启动主监控循环
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())

        self.logger.info("系统监控已启动")

    async def stop_monitoring(self):
        """停止系统监控"""
        if not self.monitoring_active:
            return

        self.monitoring_active = False

        # 停止性能监控
        if self.performance_monitor:
            await self.performance_monitor.stop_monitoring()

        # 停止监控任务
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass

        self.logger.info("系统监控已停止")

    async def _monitoring_loop(self):
        """监控循环"""
        while self.monitoring_active:
            try:
                # 定期执行健康检查
                await self._perform_health_checks()

                # 检查是否需要更新就绪证书
                if self._should_update_certificate():
                    await self.generate_readiness_certificate()

                # 等待下一次检查
                await asyncio.sleep(self.config.monitoring_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"监控循环异常: {e}")
                await asyncio.sleep(10)

    async def _perform_health_checks(self):
        """执行健康检查"""
        try:
            # 简化的健康检查逻辑
            services = [
                ServiceInfo(
                    name="frontend",
                    service_type=ServiceType.FRONTEND,
                    host="localhost",
                    port=3000
                ),
                ServiceInfo(
                    name="backend",
                    service_type=ServiceType.BACKEND_API,
                    host="localhost",
                    port=8000
                ),
                ServiceInfo(
                    name="database",
                    service_type=ServiceType.DATABASE,
                    host=self.config.database_host,
                    port=self.config.database_port
                )
            ]

            health_results = await self.health_checker.check_multiple_services(services)

            # 记录健康检查结果
            for service_name, result in health_results.items():
                if result.status != HealthStatus.HEALTHY:
                    self.logger.warning(f"服务 {service_name} 健康状态异常: {result.message}")

        except Exception as e:
            self.logger.error(f"健康检查失败: {e}")

    def _should_update_certificate(self) -> bool:
        """检查是否需要更新就绪证书"""
        if not self.latest_certificate:
            return True

        # 检查证书是否过期
        if datetime.now() >= self.latest_certificate.expires_at:
            return True

        # 检查是否到了下次检查时间
        if datetime.now() >= self.latest_certificate.next_check_time:
            return True

        return False

    async def perform_complete_verification(self) -> Dict[str, Any]:
        """
        执行完整的系统集成验证

        Returns:
            验证结果摘要
        """
        self.logger.info("开始完整系统集成验证")

        verification_start = time.time()
        results = {}

        # 创建主要进度步骤
        main_step = ProgressStep(
            name="complete_system_integration_verification",
            description="完整系统集成验证",
            weight=5.0  # 管道验证、性能验证、错误处理验证、功能集成测试
        )

        self.progress_tracker.track_step("system_integration_verification", main_step)

        try:
            # 1. 管道验证
            if self.pipeline_verifier:
                self.logger.info("执行管道验证...")
                pipeline_step = ProgressStep(
                    name="pipeline_verification",
                    description="端到端请求管道验证",
                    weight=1.0
                )

                self.progress_tracker.track_step("system_integration_verification", pipeline_step)

                pipeline_results = await self.pipeline_verifier.verify_complete_pipeline()
                integrity_result = await self.pipeline_verifier.verify_pipeline_integrity(pipeline_results)
                pipeline_summary = self.pipeline_verifier.get_pipeline_summary(pipeline_results)

                results['pipeline_verification'] = {
                    'results': pipeline_results,
                    'integrity': integrity_result,
                    'summary': pipeline_summary
                }

                self.latest_pipeline_results = pipeline_results

                pipeline_step.status = ProgressStatus.COMPLETED
                self.progress_tracker.complete_step("system_integration_verification", pipeline_step)

            # 2. 性能验证
            if self.performance_monitor:
                self.logger.info("执行性能验证...")
                performance_step = ProgressStep(
                    name="performance_verification",
                    description="系统性能指标验证",
                    weight=1.0
                )

                self.progress_tracker.track_step("system_integration_verification", performance_step)

                # 执行延迟测量
                latency_measurement = await self.performance_monitor.measure_request_latency(
                    f"verification_{uuid.uuid4().hex[:8]}",
                    self.config.frontend_url,
                    self.config.backend_url
                )

                # 生成性能报告
                performance_report = self.performance_monitor.generate_performance_report(
                    time_range_minutes=30
                )

                results['performance_verification'] = {
                    'latency_measurement': latency_measurement.to_dict(),
                    'performance_report': performance_report.__dict__
                }

                self.latest_performance_report = performance_report

                performance_step.status = ProgressStatus.COMPLETED
                self.progress_tracker.complete_step("system_integration_verification", performance_step)

            # 3. 错误处理验证
            if self.error_handler_validator:
                self.logger.info("执行错误处理验证...")
                error_step = ProgressStep(
                    name="error_handling_verification",
                    description="错误处理机制验证",
                    weight=1.0
                )

                self.progress_tracker.track_step("system_integration_verification", error_step)

                error_report = await self.error_handler_validator.validate_error_handling()

                results['error_handling_verification'] = {
                    'report': error_report.__dict__
                }

                self.latest_error_report = error_report

                error_step.status = ProgressStatus.COMPLETED
                self.progress_tracker.complete_step("system_integration_verification", error_step)

            # 4. 核心功能集成测试
            self.logger.info("执行核心功能集成测试...")
            functionality_step = ProgressStep(
                name="functionality_integration_testing",
                description="核心功能集成测试",
                weight=2.0  # 数据获取、策略计算、显示管道、数据一致性
            )

            self.progress_tracker.track_step("system_integration_verification", functionality_step)

            # 4.1 数据获取流测试
            self.logger.info("执行数据获取流测试...")
            data_acquisition_results = await self.data_acquisition_tester.test_api_to_database_flow()
            self.latest_functionality_results['data_acquisition'] = data_acquisition_results

            # 4.2 策略计算验证
            self.logger.info("执行策略计算验证...")
            strategy_calculation_results = await self.strategy_calculation_tester.test_strategy_calculations()
            self.latest_functionality_results['strategy_calculation'] = strategy_calculation_results

            # 4.3 显示管道测试
            self.logger.info("执行显示管道测试...")
            display_pipeline_results = await self.display_pipeline_tester.test_results_display_pipeline()
            self.latest_functionality_results['display_pipeline'] = display_pipeline_results

            # 4.4 数据一致性验证
            self.logger.info("执行数据一致性验证...")
            consistency_results = await self.data_consistency_validator.validate_cross_component_consistency(
                components=["database", "backend", "frontend"]
            )
            self.latest_consistency_results = consistency_results

            results['functionality_integration_testing'] = {
                'data_acquisition': [result.__dict__ for result in data_acquisition_results],
                'strategy_calculation': [result.__dict__ for result in strategy_calculation_results],
                'display_pipeline': [result.__dict__ for result in display_pipeline_results],
                'data_consistency': [result.__dict__ for result in consistency_results],
                'summary': self._generate_functionality_summary()
            }

            functionality_step.status = ProgressStatus.COMPLETED
            self.progress_tracker.complete_step("system_integration_verification", functionality_step)

            # 5. 生成系统就绪证书
            self.logger.info("生成系统就绪证书...")
            certificate = await self.generate_readiness_certificate()
            results['readiness_certificate'] = certificate.to_dict()

            # 完成主步骤
            main_step.status = ProgressStatus.COMPLETED
            self.progress_tracker.complete_step("system_integration_verification", main_step)

            verification_duration = time.time() - verification_start

            summary = {
                'verification_id': f"verification_{uuid.uuid4().hex[:8]}",
                'system_name': self.config.system_name,
                'start_time': datetime.fromtimestamp(verification_start).isoformat(),
                'duration': verification_duration,
                'overall_status': self._determine_overall_status(),
                'results': results,
                'recommendations': self._generate_integration_recommendations(results)
            }

            self.logger.info(f"系统集成验证完成，耗时: {verification_duration:.2f}秒")

            return summary

        except Exception as e:
            self.logger.error(f"系统集成验证失败: {e}")
            main_step.status = ProgressStatus.FAILED
            main_step.error_message = str(e)
            self.progress_tracker.complete_step("system_integration_verification", main_step)

            return {
                'verification_id': f"verification_{uuid.uuid4().hex[:8]}",
                'system_name': self.config.system_name,
                'status': 'failed',
                'error': str(e),
                'start_time': datetime.fromtimestamp(verification_start).isoformat()
            }

    async def generate_readiness_certificate(self) -> SystemReadinessCertificate:
        """生成系统就绪证书"""
        self.logger.info("生成系统就绪证书")

        current_time = datetime.now()
        certificate_id = f"cert_{int(current_time.timestamp())}"

        # 计算各项评分
        pipeline_score = self._calculate_pipeline_score()
        performance_score = self._calculate_performance_score()
        error_handling_score = self._calculate_error_handling_score()

        # 计算集成评分
        integration_score = (pipeline_score + performance_score + error_handling_score) / 3

        # 确定就绪状态
        readiness_score = integration_score
        if readiness_score >= 90:
            overall_status = SystemReadinessStatus.READY
        elif readiness_score >= 70:
            overall_status = SystemReadinessStatus.DEGRADED
        else:
            overall_status = SystemReadinessStatus.NOT_READY

        # 生成状态报告
        pipeline_status = self._get_pipeline_status()
        performance_status = self._get_performance_status()
        error_handling_status = self._get_error_handling_status()

        # 生成建议
        recommendations = self._generate_certificate_recommendations(
            pipeline_score, performance_score, error_handling_score
        )

        # 设置有效期和下次检查时间
        expires_at = current_time + timedelta(hours=self.config.certificate_validity_hours)
        next_check_time = current_time + timedelta(hours=1)  # 1小时后再次检查

        certificate = SystemReadinessCertificate(
            certificate_id=certificate_id,
            system_name=self.config.system_name,
            overall_status=overall_status,
            readiness_score=readiness_score,
            pipeline_status=pipeline_status,
            performance_status=performance_status,
            error_handling_status=error_handling_status,
            integration_score=integration_score,
            generated_at=current_time,
            expires_at=expires_at,
            recommendations=recommendations,
            next_check_time=next_check_time
        )

        self.latest_certificate = certificate

        self.logger.info(f"系统就绪证书已生成: {certificate_id}, 状态: {overall_status.value}, 评分: {readiness_score:.1f}")

        return certificate

    def _calculate_pipeline_score(self) -> float:
        """计算管道评分"""
        if not self.latest_pipeline_results:
            return 0.0

        successful_tests = len([r for r in self.latest_pipeline_results if r.overall_status == PipelineStatus.HEALTHY])
        total_tests = len(self.latest_pipeline_results)

        if total_tests == 0:
            return 0.0

        success_rate = successful_tests / total_tests

        # 考虑平均响应时间 - 修复评分算法
        avg_duration = sum(r.total_duration for r in self.latest_pipeline_results) / total_tests
        if avg_duration <= 2.0:  # 2秒内为满分
            duration_score = 100
        elif avg_duration <= 5.0:  # 2-5秒线性扣分
            duration_score = 100 - (avg_duration - 2.0) * 20
        else:  # 超过5秒线性扣分
            duration_score = 40 - min(avg_duration - 5.0, 10) * 4

        duration_score = max(0, duration_score)

        # 综合评分：成功率占70%，响应时间占30%
        return (success_rate * 100 * 0.7 + duration_score * 0.3)

    def _calculate_performance_score(self) -> float:
        """计算性能评分"""
        if not self.performance_monitor:
            return 0.0

        # 获取性能摘要
        performance_summary = self.performance_monitor.get_performance_summary(time_range=30)

        if 'services' not in performance_summary:
            return 0.0

        score = 100.0

        # 检查告警情况
        alerts = performance_summary.get('alerts', {})
        if alerts.get('critical', 0) > 0:
            score -= 30
        if alerts.get('warning', 0) > 0:
            score -= 15

        # 检查瓶颈分析
        bottleneck_analysis = performance_summary.get('bottleneck_analysis', {})
        if bottleneck_analysis.get('severity') == 'high':
            score -= 25
        elif bottleneck_analysis.get('severity') == 'medium':
            score -= 10

        return max(0, score)

    def _calculate_error_handling_score(self) -> float:
        """计算错误处理评分"""
        if not self.latest_error_report:
            return 0.0

        return self.latest_error_report.overall_score

    def _get_pipeline_status(self) -> Dict[str, Any]:
        """获取管道状态"""
        if not self.latest_pipeline_results:
            return {'status': 'unknown', 'message': '未执行管道验证'}

        summary = self.pipeline_verifier.get_pipeline_summary(self.latest_pipeline_results) if self.pipeline_verifier else {}

        return {
            'status': summary.get('success_rate', 0) > 0.8,
            'success_rate': summary.get('success_rate', 0),
            'total_tests': summary.get('total_tests', 0),
            'bottleneck_analysis': summary.get('bottleneck_analysis', {})
        }

    def _get_performance_status(self) -> Dict[str, Any]:
        """获取性能状态"""
        if not self.performance_monitor:
            return {'status': 'unknown', 'message': '性能监控未启用'}

        summary = self.performance_monitor.get_performance_summary(time_range=30)

        return {
            'status': summary.get('alerts', {}).get('critical', 0) == 0,
            'active_alerts': summary.get('alerts', {}),
            'bottlenecks': summary.get('bottleneck_analysis', {})
        }

    def _get_error_handling_status(self) -> Dict[str, Any]:
        """获取错误处理状态"""
        if not self.latest_error_report:
            return {'status': 'unknown', 'message': '未执行错误处理验证'}

        return {
            'status': self.latest_error_report.overall_score > 70,
            'overall_score': self.latest_error_report.overall_score,
            'total_tests': len(self.latest_error_report.test_results)
        }

    def _determine_overall_status(self) -> str:
        """确定整体状态"""
        if not self.latest_certificate:
            return "unknown"

        return self.latest_certificate.overall_status.value

    def _generate_certificate_recommendations(self, pipeline_score: float,
                                            performance_score: float,
                                            error_handling_score: float) -> List[str]:
        """生成证书建议"""
        recommendations = []

        if pipeline_score < 80:
            recommendations.append("管道验证评分较低，建议检查服务间通信和数据流")

        if performance_score < 80:
            recommendations.append("性能评分较低，建议优化系统性能和资源配置")

        if error_handling_score < 80:
            recommendations.append("错误处理评分较低，建议改进错误处理和恢复机制")

        # 如果所有评分都很好
        if pipeline_score >= 90 and performance_score >= 90 and error_handling_score >= 90:
            recommendations.append("系统运行状态良好，继续保持监控")

        return recommendations

    def _generate_integration_recommendations(self, results: Dict[str, Any]) -> List[str]:
        """生成集成建议"""
        recommendations = []

        # 分析管道验证结果
        if 'pipeline_verification' in results:
            pipeline_summary = results['pipeline_verification']['summary']
            if pipeline_summary.get('success_rate', 0) < 0.9:
                recommendations.append("管道验证成功率偏低，需要优化服务间通信")

            bottlenecks = pipeline_summary.get('bottleneck_analysis', {})
            if bottlenecks:
                recommendations.append(f"发现性能瓶颈: {list(bottlenecks.keys())}")

        # 分析性能验证结果
        if 'performance_verification' in results:
            performance_report = results['performance_verification']['performance_report']
            alerts = performance_report.get('alerts', [])
            if alerts:
                critical_count = len([a for a in alerts if a['level'] == 'critical'])
                if critical_count > 0:
                    recommendations.append(f"存在{critical_count}个严重性能告警，需要立即处理")

        # 分析错误处理验证结果
        if 'error_handling_verification' in results:
            error_report = results['error_handling_verification']['report']
            overall_score = error_report.get('overall_score', 0)
            if overall_score < 70:
                recommendations.append("错误处理机制需要改进，提高系统容错能力")

        return recommendations

    async def export_verification_report(self, filename: str, format: str = 'json') -> str:
        """
        导出验证报告

        Args:
            filename: 文件名
            format: 导出格式 ('json' 或 'markdown')

        Returns:
            导出文件路径
        """
        report_data = {
            'export_time': datetime.now().isoformat(),
            'system_name': self.config.system_name,
            'configuration': self.config.__dict__,
            'latest_certificate': self.latest_certificate.to_dict() if self.latest_certificate else None,
            'monitoring_status': {
                'active': self.monitoring_active,
                'components': {
                    'pipeline_verifier': self.pipeline_verifier is not None,
                    'performance_monitor': self.performance_monitor is not None,
                    'error_handler_validator': self.error_handler_validator is not None
                }
            }
        }

        # 确保目录存在
        file_path = Path(filename)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        if format == 'json':
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, indent=2, ensure_ascii=False, default=str)

        elif format == 'markdown':
            markdown_content = self._generate_markdown_report(report_data)
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(markdown_content)

        self.logger.info(f"验证报告已导出到: {filename}")

        return str(file_path.absolute())

    def _generate_markdown_report(self, report_data: Dict[str, Any]) -> str:
        """生成Markdown格式报告"""
        lines = [
            f"# 系统集成验证报告",
            f"",
            f"**系统名称**: {report_data['system_name']}",
            f"**导出时间**: {report_data['export_time']}",
            f"**监控状态**: {'运行中' if report_data['monitoring_status']['active'] else '已停止'}",
            f"",
        ]

        # 添加就绪证书信息
        if report_data['latest_certificate']:
            cert = report_data['latest_certificate']
            lines.extend([
                f"## 系统就绪证书",
                f"",
                f"- **证书ID**: {cert['certificate_id']}",
                f"- **整体状态**: {cert['overall_status']}",
                f"- **就绪评分**: {cert['readiness_score']:.1f}/100",
                f"- **集成评分**: {cert['integration_score']:.1f}/100",
                f"- **生成时间**: {cert['generated_at']}",
                f"- **过期时间**: {cert['expires_at']}",
                f"- **下次检查**: {cert['next_check_time']}",
                f"",
            ])

            if cert['recommendations']:
                lines.extend([
                    f"### 建议",
                    f""
                ])
                for rec in cert['recommendations']:
                    lines.append(f"- {rec}")
                lines.append("")

        return "\n".join(lines)

    def get_system_status(self) -> Dict[str, Any]:
        """获取系统当前状态"""
        status = {
            'system_name': self.config.system_name,
            'monitoring_active': self.monitoring_active,
            'timestamp': datetime.now().isoformat(),
            'components': {
                'pipeline_verifier': self.pipeline_verifier is not None,
                'performance_monitor': self.performance_monitor is not None,
                'error_handler_validator': self.error_handler_validator is not None,
                'health_checker': True
            }
        }

        # 添加最新证书信息
        if self.latest_certificate:
            status['readiness_certificate'] = {
                'id': self.latest_certificate.certificate_id,
                'status': self.latest_certificate.overall_status.value,
                'score': self.latest_certificate.readiness_score,
                'expires_at': self.latest_certificate.expires_at.isoformat()
            }

        # 添加性能摘要
        if self.performance_monitor:
            status['performance_summary'] = self.performance_monitor.get_performance_summary(time_range=10)

        return status

    def _generate_functionality_summary(self) -> Dict[str, Any]:
        """生成功能集成测试摘要"""
        summary = {
            'data_acquisition': {
                'total_tests': len(self.latest_functionality_results.get('data_acquisition', [])),
                'success_rate': self._calculate_success_rate('data_acquisition'),
                'average_quality_score': self._calculate_average_quality_score('data_acquisition'),
                'key_metrics': self._extract_key_metrics('data_acquisition')
            },
            'strategy_calculation': {
                'total_tests': len(self.latest_functionality_results.get('strategy_calculation', [])),
                'success_rate': self._calculate_success_rate('strategy_calculation'),
                'average_accuracy': self._calculate_average_accuracy('strategy_calculation'),
                'key_metrics': self._extract_key_metrics('strategy_calculation')
            },
            'display_pipeline': {
                'total_tests': len(self.latest_functionality_results.get('display_pipeline', [])),
                'success_rate': self._calculate_success_rate('display_pipeline'),
                'average_render_time': self._calculate_average_render_time('display_pipeline'),
                'average_accessibility_score': self._calculate_average_accessibility_score('display_pipeline')
            },
            'data_consistency': {
                'total_tests': len(self.latest_consistency_results),
                'consistency_rate': self._calculate_consistency_rate(),
                'average_consistency_score': self._calculate_average_consistency_score(),
                'total_violations': sum(len(result.violations) for result in self.latest_consistency_results)
            },
            'overall_score': self._calculate_overall_functionality_score()
        }

        return summary

    def _calculate_success_rate(self, component: str) -> float:
        """计算组件成功率"""
        results = self.latest_functionality_results.get(component, [])
        if not results:
            return 0.0

        success_count = 0
        for result in results:
            if hasattr(result, 'status'):
                if component == 'data_acquisition':
                    success_count += 1 if result.status.value == 'success' else 0
                elif component == 'strategy_calculation':
                    success_count += 1 if result.status.value == 'success' else 0
                elif component == 'display_pipeline':
                    success_count += 1 if result.status.value == 'success' else 0

        return (success_count / len(results)) * 100 if results else 0.0

    def _calculate_average_quality_score(self, component: str) -> float:
        """计算平均质量分数"""
        results = self.latest_functionality_results.get(component, [])
        if not results:
            return 0.0

        total_score = sum(getattr(result, 'data_quality_score', 0) for result in results)
        return total_score / len(results) if results else 0.0

    def _calculate_average_accuracy(self, component: str) -> float:
        """计算平均准确率"""
        results = self.latest_functionality_results.get(component, [])
        if not results:
            return 0.0

        total_accuracy = sum(getattr(result, 'calculation_accuracy', 0) for result in results)
        return total_accuracy / len(results) if results else 0.0

    def _calculate_average_render_time(self, component: str) -> float:
        """计算平均渲染时间"""
        results = self.latest_functionality_results.get(component, [])
        if not results:
            return 0.0

        total_time = sum(getattr(result, 'render_time_ms', 0) for result in results)
        return total_time / len(results) if results else 0.0

    def _calculate_average_accessibility_score(self, component: str) -> float:
        """计算平均可访问性评分"""
        results = self.latest_functionality_results.get(component, [])
        if not results:
            return 0.0

        total_score = sum(getattr(result, 'accessibility_score', 0) for result in results)
        return total_score / len(results) if results else 0.0

    def _calculate_consistency_rate(self) -> float:
        """计算一致性率"""
        if not self.latest_consistency_results:
            return 0.0

        consistent_count = sum(1 for result in self.latest_consistency_results
                              if result.status.value == 'consistent')
        return (consistent_count / len(self.latest_consistency_results)) * 100

    def _calculate_average_consistency_score(self) -> float:
        """计算平均一致性评分"""
        if not self.latest_consistency_results:
            return 0.0

        total_score = sum(result.consistency_score for result in self.latest_consistency_results)
        return total_score / len(self.latest_consistency_results)

    def _extract_key_metrics(self, component: str) -> Dict[str, float]:
        """提取关键指标"""
        results = self.latest_functionality_results.get(component, [])
        if not results:
            return {}

        metrics = {}
        for result in results[:5]:  # 只取前5个结果的关键指标
            if hasattr(result, 'performance_metrics'):
                for key, value in result.performance_metrics.items():
                    if key not in metrics:
                        metrics[key] = []
                    metrics[key].append(value)

        # 计算平均值
        avg_metrics = {}
        for key, values in metrics.items():
            if values:
                avg_metrics[f'avg_{key}'] = sum(values) / len(values)

        return avg_metrics

    def _calculate_overall_functionality_score(self) -> float:
        """计算总体功能评分"""
        scores = []

        # 数据获取评分 (权重: 25%)
        data_acq_score = self._calculate_success_rate('data_acquisition')
        scores.append(('data_acquisition', data_acq_score, 0.25))

        # 策略计算评分 (权重: 25%)
        strategy_score = self._calculate_success_rate('strategy_calculation')
        scores.append(('strategy_calculation', strategy_score, 0.25))

        # 显示管道评分 (权重: 25%)
        display_score = self._calculate_success_rate('display_pipeline')
        scores.append(('display_pipeline', display_score, 0.25))

        # 数据一致性评分 (权重: 25%)
        consistency_score = self._calculate_consistency_rate()
        scores.append(('data_consistency', consistency_score, 0.25))

        # 计算加权平均
        total_score = sum(score * weight for _, score, weight in scores)
        return round(total_score, 2)

    async def cleanup(self):
        """清理资源"""
        await self.stop_monitoring()

        if self.performance_monitor:
            self.performance_monitor.clear_metrics()

        self.logger.info("系统集成服务资源已清理")