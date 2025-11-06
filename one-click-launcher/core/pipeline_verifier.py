"""
端到端请求管道验证器

提供完整的用户请求链路验证，包括前端到后端API，后端到数据库的完整数据流测试。
支持管道完整性检查、瓶颈检测、延迟测量和故障点识别。
"""

import asyncio
import aiohttp
import json
import time
import uuid
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from enum import Enum
from urllib.parse import urljoin, urlparse
from datetime import datetime, timedelta
import traceback

from .frontend_backend_communicator import (
    FrontendBackendCommunicator, CommunicationConfig, APIEndpoint,
    CommunicationResult, CommunicationStatus
)
from .health_checker import HealthChecker, HealthStatus, HealthCheckResult
from .service_dependency_analyzer import ServiceInfo, ServiceType
from utils.progress_tracker import ProgressTracker, ProgressStep, ProgressStatus
from utils.logger import get_logger

logger = get_logger(__name__)


class PipelineStage(Enum):
    """管道阶段"""
    FRONTEND = "frontend"
    FRONTEND_TO_BACKEND = "frontend_to_backend"
    BACKEND_API = "backend_api"
    BACKEND_TO_DATABASE = "backend_to_database"
    DATABASE = "database"
    DATABASE_TO_BACKEND = "database_to_backend"
    BACKEND_TO_FRONTEND = "backend_to_frontend"
    COMPLETE = "complete"


class PipelineStatus(Enum):
    """管道状态"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"
    UNKNOWN = "unknown"
    TIMEOUT = "timeout"
    BOTTLENECK = "bottleneck"


@dataclass
class PipelineStep:
    """管道步骤"""
    stage: PipelineStage
    name: str
    description: str
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    duration: Optional[float] = None
    status: PipelineStatus = PipelineStatus.UNKNOWN
    error_message: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)

    def start(self):
        """开始步骤"""
        self.start_time = time.time()
        self.status = PipelineStatus.UNKNOWN

    def complete(self, status: PipelineStatus, error_message: Optional[str] = None):
        """完成步骤"""
        self.end_time = time.time()
        if self.start_time is not None:
            self.duration = self.end_time - self.start_time
        self.status = status
        self.error_message = error_message


@dataclass
class PipelineTestRequest:
    """管道测试请求"""
    request_id: str
    test_data: Dict[str, Any]
    expected_pipeline: List[PipelineStage]
    timeout: int = 60
    retry_count: int = 0
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class PipelineTestResult:
    """管道测试结果"""
    request_id: str
    overall_status: PipelineStatus
    total_duration: float
    steps: List[PipelineStep]
    success_rate: float
    bottleneck_stage: Optional[PipelineStage] = None
    failure_points: List[str] = field(default_factory=list)
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

    @property
    def successful_steps(self) -> List[PipelineStep]:
        """成功步骤列表"""
        return [step for step in self.steps if step.status == PipelineStatus.HEALTHY]

    @property
    def failed_steps(self) -> List[PipelineStep]:
        """失败步骤列表"""
        return [step for step in self.steps if step.status == PipelineStatus.FAILED]

    @property
    def step_count(self) -> int:
        """步骤总数"""
        return len(self.steps)


@dataclass
class PipelineIntegrityResult:
    """管道完整性验证结果"""
    is_complete: bool
    missing_stages: List[PipelineStage]
    broken_connections: List[Tuple[PipelineStage, PipelineStage]]
    data_integrity_issues: List[str]
    bottleneck_analysis: Dict[str, Any]
    recommendations: List[str]


@dataclass
class PipelineConfig:
    """管道验证配置"""
    frontend_url: str
    backend_url: str
    database_host: str
    database_port: int
    test_endpoints: List[APIEndpoint]
    database_test_queries: List[Dict[str, Any]]
    timeout: int = 60
    max_retries: int = 3
    retry_delay: float = 1.0
    performance_thresholds: Dict[str, float] = field(default_factory=lambda: {
        'max_frontend_response_time': 3.0,
        'max_backend_response_time': 2.0,
        'max_database_query_time': 1.0,
        'max_total_pipeline_time': 10.0
    })
    integrity_checks: bool = True
    bottleneck_detection: bool = True
    latency_measurement: bool = True


class PipelineVerifier:
    """
    端到端请求管道验证器

    功能特性：
    - 完整请求链路测试（前端→后端→数据库）
    - 管道完整性验证和瓶颈检测
    - 请求延迟测量和性能分析
    - 故障点识别和报告生成
    - 管道健康监控和状态跟踪
    """

    def __init__(self, config: PipelineConfig):
        """
        初始化管道验证器

        Args:
            config: 管道验证配置
        """
        self.config = config
        self.logger = get_logger(self.__class__.__name__)

        # 初始化组件
        self.health_checker = HealthChecker()
        self.progress_tracker = ProgressTracker(
            component_name="system_integration_verification"
        )

        # 测试历史记录
        self.test_history: List[PipelineTestResult] = []
        self.performance_baseline: Dict[str, float] = {}

        # 管道状态缓存
        self.pipeline_cache: Dict[str, Any] = {}

        self.logger.info("管道验证器初始化完成")

    async def verify_complete_pipeline(self, test_requests: Optional[List[PipelineTestRequest]] = None) -> List[PipelineTestResult]:
        """
        验证完整的请求管道

        Args:
            test_requests: 测试请求列表，如果为None则使用默认测试

        Returns:
            管道测试结果列表
        """
        self.logger.info("开始完整管道验证")

        # 如果没有提供测试请求，使用默认测试
        if test_requests is None:
            test_requests = self._generate_default_test_requests()

        results = []

        # 创建进度步骤
        pipeline_step = ProgressStep(
            name="end_to_end_pipeline_verification",
            description="端到端请求管道验证",
            weight=len(test_requests)
        )

        self.progress_tracker.track_step("system_integration_verification", pipeline_step)

        try:
            # 执行每个测试请求
            for i, request in enumerate(test_requests):
                self.logger.info(f"执行测试请求 {i+1}/{len(test_requests)}: {request.request_id}")

                result = await self._execute_pipeline_test(request)
                results.append(result)
                self.test_history.append(result)

                # 更新进度
                self.progress_tracker.update_step_progress(
                    "system_integration_verification",
                    pipeline_step.name,
                    (i + 1) / len(test_requests)
                )

                # 短暂延迟避免过载
                await asyncio.sleep(0.5)

            # 完成进度跟踪
            pipeline_step.status = ProgressStatus.COMPLETED
            self.progress_tracker.complete_step("system_integration_verification", pipeline_step)

            self.logger.info(f"管道验证完成，成功率: {sum(r.success_rate for r in results) / len(results):.1%}")

        except Exception as e:
            self.logger.error(f"管道验证过程中发生错误: {e}")
            pipeline_step.status = ProgressStatus.FAILED
            pipeline_step.error_message = str(e)
            self.progress_tracker.complete_step("system_integration_verification", pipeline_step)

        return results

    async def _execute_pipeline_test(self, request: PipelineTestRequest) -> PipelineTestResult:
        """
        执行单个管道测试

        Args:
            request: 管道测试请求

        Returns:
            管道测试结果
        """
        start_time = time.time()
        steps = []
        overall_status = PipelineStatus.UNKNOWN

        try:
            # 步骤1: 前端健康检查
            frontend_step = PipelineStep(
                stage=PipelineStage.FRONTEND,
                name="前端服务检查",
                description="验证前端服务是否正常运行"
            )
            steps.append(frontend_step)

            frontend_step.start()
            frontend_result = await self.health_checker.check_connection_health(
                urlparse(self.config.frontend_url).hostname,
                urlparse(self.config.frontend_url).port or 3000,
                "frontend"
            )

            if frontend_result.status == HealthStatus.HEALTHY:
                frontend_step.complete(PipelineStatus.HEALTHY)
            else:
                frontend_step.complete(PipelineStatus.FAILED, frontend_result.message)
                return PipelineTestResult(
                    request_id=request.request_id,
                    overall_status=PipelineStatus.FAILED,
                    total_duration=time.time() - start_time,
                    steps=steps,
                    success_rate=0.0
                )

            # 步骤2: 前端到后端通信测试
            frontend_backend_step = PipelineStep(
                stage=PipelineStage.FRONTEND_TO_BACKEND,
                name="前端到后端通信",
                description="测试前端到后端API的通信"
            )
            steps.append(frontend_backend_step)

            frontend_backend_step.start()
            frontend_backend_result = await self._test_frontend_to_backend_communication(request)

            if frontend_backend_result['success']:
                frontend_backend_step.complete(PipelineStatus.HEALTHY)
            else:
                frontend_backend_step.complete(PipelineStatus.FAILED, frontend_backend_result['error'])
                return PipelineTestResult(
                    request_id=request.request_id,
                    overall_status=PipelineStatus.FAILED,
                    total_duration=time.time() - start_time,
                    steps=steps,
                    success_rate=0.0
                )

            # 步骤3: 后端API处理测试
            backend_step = PipelineStep(
                stage=PipelineStage.BACKEND_API,
                name="后端API处理",
                description="验证后端API的请求处理能力"
            )
            steps.append(backend_step)

            backend_step.start()
            backend_result = await self._test_backend_api_processing(request)

            if backend_result['success']:
                backend_step.complete(PipelineStatus.HEALTHY)
            else:
                backend_step.complete(PipelineStatus.FAILED, backend_result['error'])
                return PipelineTestResult(
                    request_id=request.request_id,
                    overall_status=PipelineStatus.FAILED,
                    total_duration=time.time() - start_time,
                    steps=steps,
                    success_rate=len([s for s in steps if s.status == PipelineStatus.HEALTHY]) / len(steps)
                )

            # 步骤4: 后端到数据库连接测试
            backend_db_step = PipelineStep(
                stage=PipelineStage.BACKEND_TO_DATABASE,
                name="后端到数据库连接",
                description="验证后端到数据库的连接和查询"
            )
            steps.append(backend_db_step)

            backend_db_step.start()
            backend_db_result = await self._test_backend_database_connection(request)

            if backend_db_result['success']:
                backend_db_step.complete(PipelineStatus.HEALTHY)
            else:
                backend_db_step.complete(PipelineStatus.FAILED, backend_db_result['error'])

            # 步骤5: 数据库查询测试
            database_step = PipelineStep(
                stage=PipelineStage.DATABASE,
                name="数据库查询处理",
                description="验证数据库查询处理能力"
            )
            steps.append(database_step)

            database_step.start()
            database_result = await self._test_database_processing(request)

            if database_result['success']:
                database_step.complete(PipelineStatus.HEALTHY)
            else:
                database_step.complete(PipelineStatus.FAILED, database_result['error'])

            # 计算整体状态和成功率
            successful_steps = len([s for s in steps if s.status == PipelineStatus.HEALTHY])
            success_rate = successful_steps / len(steps)

            if success_rate >= 1.0:
                overall_status = PipelineStatus.HEALTHY
            elif success_rate >= 0.7:
                overall_status = PipelineStatus.DEGRADED
            else:
                overall_status = PipelineStatus.FAILED

            total_duration = time.time() - start_time

            # 检测瓶颈
            bottleneck_stage = self._detect_bottleneck(steps)

            # 计算性能指标
            performance_metrics = self._calculate_performance_metrics(steps)

            return PipelineTestResult(
                request_id=request.request_id,
                overall_status=overall_status,
                total_duration=total_duration,
                steps=steps,
                success_rate=success_rate,
                bottleneck_stage=bottleneck_stage,
                performance_metrics=performance_metrics
            )

        except Exception as e:
            self.logger.error(f"管道测试执行失败: {e}")
            overall_status = PipelineStatus.FAILED

            return PipelineTestResult(
                request_id=request.request_id,
                overall_status=overall_status,
                total_duration=time.time() - start_time,
                steps=steps,
                success_rate=0.0,
                failure_points=[f"管道测试异常: {str(e)}"]
            )

    async def _test_frontend_to_backend_communication(self, request: PipelineTestRequest) -> Dict[str, Any]:
        """测试前端到后端通信"""
        try:
            async with FrontendBackendCommunicator() as communicator:
                # 构建通信配置
                comm_config = CommunicationConfig(
                    frontend_url=self.config.frontend_url,
                    backend_url=self.config.backend_url,
                    api_endpoints=[
                        APIEndpoint(
                            path="/api/health",
                            method="GET",
                            expected_status=200,
                            timeout=10
                        )
                    ],
                    timeout=self.config.timeout
                )

                # 执行通信验证
                report = await communicator.verify_communication(comm_config)

                return {
                    'success': report.overall_status == CommunicationStatus.CONNECTED,
                    'response_time': report.average_response_time,
                    'details': {
                        'successful_endpoints': report.successful_endpoints,
                        'total_endpoints': report.total_endpoints,
                        'cors_status': report.cors_status
                    },
                    'error': None if report.overall_status == CommunicationStatus.CONNECTED else "通信验证失败"
                }

        except Exception as e:
            self.logger.error(f"前端到后端通信测试失败: {e}")
            return {
                'success': False,
                'error': f"通信测试异常: {str(e)}"
            }

    async def _test_backend_api_processing(self, request: PipelineTestRequest) -> Dict[str, Any]:
        """测试后端API处理"""
        try:
            async with aiohttp.ClientSession() as session:
                # 测试API处理能力
                test_url = urljoin(self.config.backend_url, "/api/test/processing")
                test_data = {
                    'test_id': request.request_id,
                    'timestamp': datetime.now().isoformat(),
                    'data': request.test_data
                }

                start_time = time.time()
                async with session.post(
                    test_url,
                    json=test_data,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    response_time = time.time() - start_time
                    response_data = await response.json()

                    return {
                        'success': response.status == 200,
                        'response_time': response_time,
                        'processing_time': response_data.get('processing_time', 0),
                        'details': response_data,
                        'error': None if response.status == 200 else f"API处理失败: {response.status}"
                    }

        except Exception as e:
            self.logger.error(f"后端API处理测试失败: {e}")
            return {
                'success': False,
                'error': f"API处理测试异常: {str(e)}"
            }

    async def _test_backend_database_connection(self, request: PipelineTestRequest) -> Dict[str, Any]:
        """测试后端到数据库连接"""
        try:
            async with aiohttp.ClientSession() as session:
                # 测试数据库连接端点
                test_url = urljoin(self.config.backend_url, "/api/test/database")
                test_data = {
                    'test_type': 'connection',
                    'test_id': request.request_id
                }

                start_time = time.time()
                async with session.post(
                    test_url,
                    json=test_data,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    response_time = time.time() - start_time
                    response_data = await response.json()

                    return {
                        'success': response.status == 200 and response_data.get('connected', False),
                        'response_time': response_time,
                        'connection_time': response_data.get('connection_time', 0),
                        'database_type': response_data.get('database_type'),
                        'details': response_data,
                        'error': None if response.status == 200 else f"数据库连接测试失败: {response.status}"
                    }

        except Exception as e:
            self.logger.error(f"数据库连接测试失败: {e}")
            return {
                'success': False,
                'error': f"数据库连接测试异常: {str(e)}"
            }

    async def _test_database_processing(self, request: PipelineTestRequest) -> Dict[str, Any]:
        """测试数据库处理"""
        try:
            async with aiohttp.ClientSession() as session:
                # 测试数据库查询处理
                test_url = urljoin(self.config.backend_url, "/api/test/database")
                test_data = {
                    'test_type': 'query',
                    'test_id': request.request_id,
                    'queries': self.config.database_test_queries[:1]  # 使用第一个测试查询
                }

                start_time = time.time()
                async with session.post(
                    test_url,
                    json=test_data,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    response_time = time.time() - start_time
                    response_data = await response.json()

                    return {
                        'success': response.status == 200,
                        'response_time': response_time,
                        'query_time': response_data.get('query_time', 0),
                        'records_affected': response_data.get('records_affected', 0),
                        'details': response_data,
                        'error': None if response.status == 200 else f"数据库查询失败: {response.status}"
                    }

        except Exception as e:
            self.logger.error(f"数据库处理测试失败: {e}")
            return {
                'success': False,
                'error': f"数据库处理测试异常: {str(e)}"
            }

    def _generate_default_test_requests(self) -> List[PipelineTestRequest]:
        """生成默认测试请求"""
        test_requests = []

        # 基础健康检查请求
        health_request = PipelineTestRequest(
            request_id=f"health_check_{uuid.uuid4().hex[:8]}",
            test_data={'type': 'health_check', 'timestamp': datetime.now().isoformat()},
            expected_pipeline=[
                PipelineStage.FRONTEND,
                PipelineStage.FRONTEND_TO_BACKEND,
                PipelineStage.BACKEND_API,
                PipelineStage.BACKEND_TO_DATABASE,
                PipelineStage.DATABASE
            ],
            timeout=30
        )
        test_requests.append(health_request)

        # 数据查询测试请求
        query_request = PipelineTestRequest(
            request_id=f"data_query_{uuid.uuid4().hex[:8]}",
            test_data={
                'type': 'data_query',
                'query': 'SELECT COUNT(*) FROM test_table',
                'timestamp': datetime.now().isoformat()
            },
            expected_pipeline=[
                PipelineStage.FRONTEND,
                PipelineStage.FRONTEND_TO_BACKEND,
                PipelineStage.BACKEND_API,
                PipelineStage.BACKEND_TO_DATABASE,
                PipelineStage.DATABASE
            ],
            timeout=60
        )
        test_requests.append(query_request)

        return test_requests

    def _detect_bottleneck(self, steps: List[PipelineStep]) -> Optional[PipelineStage]:
        """检测管道瓶颈"""
        if not steps:
            return None

        # 找到耗时最长的步骤
        slowest_step = max(steps, key=lambda s: s.duration or 0)

        # 如果最慢步骤的耗时显著高于平均水平，认为是瓶颈
        if slowest_step.duration and slowest_step.duration > 2.0:  # 2秒阈值
            return slowest_step.stage

        return None

    def _calculate_performance_metrics(self, steps: List[PipelineStep]) -> Dict[str, float]:
        """计算性能指标"""
        metrics = {}

        # 总耗时
        total_time = sum(s.duration or 0 for s in steps)
        metrics['total_pipeline_time'] = total_time

        # 各阶段耗时
        for step in steps:
            if step.duration:
                metrics[f"{step.stage}_time"] = step.duration

        # 平均响应时间
        completed_steps = [s for s in steps if s.duration is not None]
        if completed_steps:
            metrics['average_step_time'] = sum(s.duration for s in completed_steps) / len(completed_steps)

        return metrics

    def get_pipeline_summary(self, results: List[PipelineTestResult]) -> Dict[str, Any]:
        """获取管道验证摘要"""
        if not results:
            return {'error': '没有验证结果'}

        total_tests = len(results)
        successful_tests = len([r for r in results if r.overall_status == PipelineStatus.HEALTHY])
        degraded_tests = len([r for r in results if r.overall_status == PipelineStatus.DEGRADED])
        failed_tests = len([r for r in results if r.overall_status == PipelineStatus.FAILED])

        avg_duration = sum(r.total_duration for r in results) / total_tests
        avg_success_rate = sum(r.success_rate for r in results) / total_tests

        # 瓶颈分析
        bottleneck_stages = {}
        for result in results:
            if result.bottleneck_stage:
                stage_name = result.bottleneck_stage.value
                bottleneck_stages[stage_name] = bottleneck_stages.get(stage_name, 0) + 1

        summary = {
            'total_tests': total_tests,
            'successful_tests': successful_tests,
            'degraded_tests': degraded_tests,
            'failed_tests': failed_tests,
            'success_rate': successful_tests / total_tests,
            'average_duration': avg_duration,
            'average_success_rate': avg_success_rate,
            'bottleneck_analysis': bottleneck_stages,
            'recommendations': self._generate_recommendations(results)
        }

        return summary

    def _generate_recommendations(self, results: List[PipelineTestResult]) -> List[str]:
        """生成改进建议"""
        recommendations = []

        # 分析失败模式
        failure_patterns = {}
        for result in results:
            for failed_step in result.failed_steps:
                stage_name = failed_step.stage.value
                failure_patterns[stage_name] = failure_patterns.get(stage_name, 0) + 1

        # 基于失败模式生成建议
        if failure_patterns.get('frontend', 0) > 0:
            recommendations.append("前端服务响应不稳定，建议检查前端应用状态和资源使用情况")

        if failure_patterns.get('frontend_to_backend', 0) > 0:
            recommendations.append("前后端通信存在问题，建议检查网络连接和CORS配置")

        if failure_patterns.get('backend_api', 0) > 0:
            recommendations.append("后端API处理能力不足，建议优化API性能和增加资源")

        if failure_patterns.get('backend_to_database', 0) > 0:
            recommendations.append("数据库连接不稳定，建议检查数据库服务状态和连接池配置")

        if failure_patterns.get('database', 0) > 0:
            recommendations.append("数据库性能问题，建议优化查询和索引")

        # 性能建议
        avg_duration = sum(r.total_duration for r in results) / len(results)
        if avg_duration > self.config.performance_thresholds.get('max_total_pipeline_time', 10.0):
            recommendations.append("整体响应时间过长，建议进行性能优化")

        return recommendations

    async def verify_pipeline_integrity(self, results: List[PipelineTestResult]) -> PipelineIntegrityResult:
        """
        验证管道完整性

        Args:
            results: 管道测试结果列表

        Returns:
            管道完整性验证结果
        """
        missing_stages = []
        broken_connections = []
        data_integrity_issues = []

        # 检查各阶段完整性
        all_stages = set(PipelineStage)
        tested_stages = set()

        for result in results:
            for step in result.steps:
                tested_stages.add(step.stage)

        missing_stages = list(all_stages - tested_stages)

        # 检查连接完整性
        for result in results:
            for i, step in enumerate(result.steps[:-1]):
                next_step = result.steps[i + 1]
                if step.status == PipelineStatus.HEALTHY and next_step.status == PipelineStatus.FAILED:
                    broken_connections.append((step.stage, next_step.stage))

        # 瓶颈分析
        bottleneck_stages = {}
        for result in results:
            if result.bottleneck_stage:
                stage_name = result.bottleneck_stage.value
                bottleneck_stages[stage_name] = bottleneck_stages.get(stage_name, 0) + 1

        # 生成建议
        recommendations = []
        if missing_stages:
            recommendations.append(f"缺少测试阶段: {[s.value for s in missing_stages]}")

        if broken_connections:
            recommendations.append(f"存在断开的连接: {[f'{s1.value}→{s2.value}' for s1, s2 in broken_connections]}")

        return PipelineIntegrityResult(
            is_complete=len(missing_stages) == 0 and len(broken_connections) == 0,
            missing_stages=missing_stages,
            broken_connections=broken_connections,
            data_integrity_issues=data_integrity_issues,
            bottleneck_analysis=bottleneck_stages,
            recommendations=recommendations
        )