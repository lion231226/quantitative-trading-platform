"""
系统性能监控器

提供跨层性能监控、延迟测量和趋势分析功能。
支持前端、后端、数据库各层面的性能指标收集和分析。
"""

import asyncio
import aiohttp
import time
import psutil
import json
import statistics
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from collections import defaultdict, deque
import threading

from .health_checker import HealthChecker, HealthStatus, HealthCheckResult
from .service_dependency_analyzer import ServiceInfo, ServiceType
from utils.logger import get_logger

logger = get_logger(__name__)


class MetricType(Enum):
    """指标类型"""
    RESPONSE_TIME = "response_time"
    THROUGHPUT = "throughput"
    ERROR_RATE = "error_rate"
    CPU_USAGE = "cpu_usage"
    MEMORY_USAGE = "memory_usage"
    DISK_IO = "disk_io"
    NETWORK_IO = "network_io"
    DATABASE_QUERY_TIME = "database_query_time"
    CACHE_HIT_RATE = "cache_hit_rate"


class AlertLevel(Enum):
    """告警级别"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class PerformanceMetric:
    """性能指标"""
    metric_type: MetricType
    service_name: str
    value: float
    unit: str
    timestamp: datetime
    stage: Optional[str] = None
    tags: Dict[str, str] = field(default_factory=dict)
    threshold: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'metric_type': self.metric_type.value,
            'service_name': self.service_name,
            'value': self.value,
            'unit': self.unit,
            'timestamp': self.timestamp.isoformat(),
            'stage': self.stage,
            'tags': self.tags,
            'threshold': self.threshold
        }


@dataclass
class PerformanceThreshold:
    """性能阈值"""
    metric_type: MetricType
    service_name: str
    warning_threshold: float
    critical_threshold: float
    unit: str
    description: str = ""


@dataclass
class PerformanceAlert:
    """性能告警"""
    alert_id: str
    level: AlertLevel
    metric_type: MetricType
    service_name: str
    current_value: float
    threshold_value: float
    message: str
    timestamp: datetime
    resolved: bool = False
    resolved_at: Optional[datetime] = None


@dataclass
class LatencyMeasurement:
    """延迟测量结果"""
    request_id: str
    stages: Dict[str, float]  # 各阶段延迟
    total_latency: float
    frontend_to_backend: float
    backend_processing: float
    database_operations: float
    backend_to_frontend: float
    timestamp: datetime

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'request_id': self.request_id,
            'stages': self.stages,
            'total_latency': self.total_latency,
            'frontend_to_backend': self.frontend_to_backend,
            'backend_processing': self.backend_processing,
            'database_operations': self.database_operations,
            'backend_to_frontend': self.backend_to_frontend,
            'timestamp': self.timestamp.isoformat()
        }


@dataclass
class PerformanceReport:
    """性能报告"""
    report_id: str
    generated_at: datetime
    time_range: Tuple[datetime, datetime]
    metrics_summary: Dict[str, Any]
    latency_analysis: Dict[str, Any]
    bottleneck_analysis: Dict[str, Any]
    trend_analysis: Dict[str, Any]
    alerts: List[PerformanceAlert]
    recommendations: List[str]


class PerformanceMonitor:
    """
    系统性能监控器

    功能特性：
    - 跨层响应时间测量
    - 资源使用率监控
    - 性能趋势分析
    - 自动告警机制
    - 瓶颈识别和建议
    """

    def __init__(self, monitoring_interval: int = 30):
        """
        初始化性能监控器

        Args:
            monitoring_interval: 监控间隔（秒）
        """
        self.monitoring_interval = monitoring_interval
        self.logger = get_logger(self.__class__.__name__)

        # 指标存储
        self.metrics_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.latency_measurements: List[LatencyMeasurement] = []
        self.active_alerts: Dict[str, PerformanceAlert] = {}

        # 性能阈值配置
        self.thresholds = self._initialize_default_thresholds()

        # 监控状态
        self.monitoring_active = False
        self.monitoring_task: Optional[asyncio.Task] = None

        # 统计数据
        self.performance_stats = defaultdict(dict)

        self.logger.info("性能监控器初始化完成")

    def _initialize_default_thresholds(self) -> Dict[str, PerformanceThreshold]:
        """初始化默认性能阈值"""
        thresholds = {}

        # 响应时间阈值
        thresholds['frontend_response_time'] = PerformanceThreshold(
            metric_type=MetricType.RESPONSE_TIME,
            service_name='frontend',
            warning_threshold=2.0,
            critical_threshold=5.0,
            unit='seconds',
            description='前端响应时间'
        )

        thresholds['backend_response_time'] = PerformanceThreshold(
            metric_type=MetricType.RESPONSE_TIME,
            service_name='backend',
            warning_threshold=1.0,
            critical_threshold=3.0,
            unit='seconds',
            description='后端API响应时间'
        )

        thresholds['database_query_time'] = PerformanceThreshold(
            metric_type=MetricType.DATABASE_QUERY_TIME,
            service_name='database',
            warning_threshold=0.5,
            critical_threshold=2.0,
            unit='seconds',
            description='数据库查询时间'
        )

        # 资源使用阈值
        thresholds['cpu_usage'] = PerformanceThreshold(
            metric_type=MetricType.CPU_USAGE,
            service_name='system',
            warning_threshold=70.0,
            critical_threshold=90.0,
            unit='percent',
            description='CPU使用率'
        )

        thresholds['memory_usage'] = PerformanceThreshold(
            metric_type=MetricType.MEMORY_USAGE,
            service_name='system',
            warning_threshold=80.0,
            critical_threshold=95.0,
            unit='percent',
            description='内存使用率'
        )

        # 错误率阈值
        thresholds['error_rate'] = PerformanceThreshold(
            metric_type=MetricType.ERROR_RATE,
            service_name='system',
            warning_threshold=5.0,
            critical_threshold=15.0,
            unit='percent',
            description='错误率'
        )

        return thresholds

    async def start_monitoring(self):
        """开始性能监控"""
        if self.monitoring_active:
            self.logger.warning("性能监控已在运行中")
            return

        self.monitoring_active = True
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        self.logger.info("性能监控已启动")

    async def stop_monitoring(self):
        """停止性能监控"""
        if not self.monitoring_active:
            return

        self.monitoring_active = False
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass

        self.logger.info("性能监控已停止")

    async def _monitoring_loop(self):
        """监控循环"""
        while self.monitoring_active:
            try:
                # 收集系统指标
                await self._collect_system_metrics()

                # 检查告警
                self._check_alerts()

                # 等待下一次监控
                await asyncio.sleep(self.monitoring_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"监控循环异常: {e}")
                await asyncio.sleep(5)

    async def _collect_system_metrics(self):
        """收集系统性能指标"""
        current_time = datetime.now()

        # CPU使用率
        cpu_percent = psutil.cpu_percent(interval=1)
        self._add_metric(PerformanceMetric(
            metric_type=MetricType.CPU_USAGE,
            service_name='system',
            value=cpu_percent,
            unit='percent',
            timestamp=current_time,
            threshold=self.thresholds['cpu_usage'].critical_threshold
        ))

        # 内存使用率
        memory = psutil.virtual_memory()
        self._add_metric(PerformanceMetric(
            metric_type=MetricType.MEMORY_USAGE,
            service_name='system',
            value=memory.percent,
            unit='percent',
            timestamp=current_time,
            threshold=self.thresholds['memory_usage'].critical_threshold
        ))

        # 磁盘IO
        disk_io = psutil.disk_io_counters()
        if disk_io:
            self._add_metric(PerformanceMetric(
                metric_type=MetricType.DISK_IO,
                service_name='system',
                value=disk_io.read_bytes + disk_io.write_bytes,
                unit='bytes',
                timestamp=current_time
            ))

        # 网络IO
        network_io = psutil.net_io_counters()
        if network_io:
            self._add_metric(PerformanceMetric(
                metric_type=MetricType.NETWORK_IO,
                service_name='system',
                value=network_io.bytes_sent + network_io.bytes_recv,
                unit='bytes',
                timestamp=current_time
            ))

    async def measure_request_latency(self, request_id: str,
                                   frontend_url: str,
                                   backend_url: str) -> LatencyMeasurement:
        """
        测量请求延迟

        Args:
            request_id: 请求ID
            frontend_url: 前端URL
            backend_url: 后端URL

        Returns:
            延迟测量结果
        """
        start_time = time.time()
        stages = {}

        try:
            # 测量前端到后端延迟
            frontend_start = time.time()
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    urljoin(backend_url, "/api/health"),
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    frontend_to_backend_time = time.time() - frontend_start
                    stages['frontend_to_backend'] = frontend_to_backend_time

            # 测量后端处理延迟
            backend_start = time.time()
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    urljoin(backend_url, "/api/test/latency"),
                    json={'request_id': request_id, 'timestamp': datetime.now().isoformat()},
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    backend_data = await response.json()
                    backend_processing_time = time.time() - backend_start
                    stages['backend_processing'] = backend_processing_time

            # 测量数据库操作延迟
            db_start = time.time()
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    urljoin(backend_url, "/api/test/database_latency"),
                    json={'test_query': 'SELECT 1'},
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    db_data = await response.json()
                    database_time = time.time() - db_start
                    stages['database_operations'] = database_time

            total_latency = time.time() - start_time

            measurement = LatencyMeasurement(
                request_id=request_id,
                stages=stages,
                total_latency=total_latency,
                frontend_to_backend=frontend_to_backend_time,
                backend_processing=backend_processing_time,
                database_operations=database_time,
                backend_to_frontend=0.0,  # 简化实现
                timestamp=datetime.now()
            )

            self.latency_measurements.append(measurement)

            # 记录延迟指标
            self._add_metric(PerformanceMetric(
                metric_type=MetricType.RESPONSE_TIME,
                service_name='pipeline',
                value=total_latency,
                unit='seconds',
                timestamp=datetime.now(),
                stage='total'
            ))

            return measurement

        except Exception as e:
            self.logger.error(f"延迟测量失败: {e}")
            return LatencyMeasurement(
                request_id=request_id,
                stages={'error': time.time() - start_time},
                total_latency=time.time() - start_time,
                frontend_to_backend=0.0,
                backend_processing=0.0,
                database_operations=0.0,
                backend_to_frontend=0.0,
                timestamp=datetime.now()
            )

    async def measure_endpoint_performance(self, service_name: str,
                                         endpoint_url: str,
                                         method: str = "GET",
                                         duration: int = 60) -> Dict[str, Any]:
        """
        测量端点性能

        Args:
            service_name: 服务名称
            endpoint_url: 端点URL
            method: HTTP方法
            duration: 测试持续时间（秒）

        Returns:
            性能测量结果
        """
        self.logger.info(f"开始端点性能测试: {service_name} - {endpoint_url}")

        response_times = []
        error_count = 0
        success_count = 0
        start_time = time.time()

        async with aiohttp.ClientSession() as session:
            while time.time() - start_time < duration:
                try:
                    request_start = time.time()
                    async with session.request(
                        method, endpoint_url,
                        timeout=aiohttp.ClientTimeout(total=10)
                    ) as response:
                        response_time = time.time() - request_start
                        response_times.append(response_time)

                        if 200 <= response.status < 400:
                            success_count += 1
                        else:
                            error_count += 1

                except Exception as e:
                    error_count += 1
                    self.logger.warning(f"端点测试请求失败: {e}")

                await asyncio.sleep(1)  # 每秒一次请求

        # 计算统计数据
        total_requests = success_count + error_count
        avg_response_time = statistics.mean(response_times) if response_times else 0
        p95_response_time = statistics.quantiles(response_times, n=20)[18] if len(response_times) >= 20 else 0
        p99_response_time = statistics.quantiles(response_times, n=100)[98] if len(response_times) >= 100 else 0
        error_rate = (error_count / total_requests * 100) if total_requests > 0 else 0
        throughput = success_count / duration

        # 记录性能指标
        self._add_metric(PerformanceMetric(
            metric_type=MetricType.RESPONSE_TIME,
            service_name=service_name,
            value=avg_response_time,
            unit='seconds',
            timestamp=datetime.now()
        ))

        self._add_metric(PerformanceMetric(
            metric_type=MetricType.THROUGHPUT,
            service_name=service_name,
            value=throughput,
            unit='requests_per_second',
            timestamp=datetime.now()
        ))

        self._add_metric(PerformanceMetric(
            metric_type=MetricType.ERROR_RATE,
            service_name=service_name,
            value=error_rate,
            unit='percent',
            timestamp=datetime.now()
        ))

        return {
            'service_name': service_name,
            'endpoint_url': endpoint_url,
            'duration': duration,
            'total_requests': total_requests,
            'successful_requests': success_count,
            'failed_requests': error_count,
            'error_rate': error_rate,
            'throughput': throughput,
            'avg_response_time': avg_response_time,
            'p95_response_time': p95_response_time,
            'p99_response_time': p99_response_time,
            'min_response_time': min(response_times) if response_times else 0,
            'max_response_time': max(response_times) if response_times else 0
        }

    def _add_metric(self, metric: PerformanceMetric):
        """添加性能指标"""
        key = f"{metric.service_name}_{metric.metric_type.value}"
        self.metrics_history[key].append(metric)

        # 更新统计
        if metric.service_name not in self.performance_stats:
            self.performance_stats[metric.service_name] = {}

        stats = self.performance_stats[metric.service_name]
        metric_key = f"{metric.metric_type.value}_stats"

        if metric_key not in stats:
            stats[metric_key] = {
                'count': 0,
                'sum': 0.0,
                'min': float('inf'),
                'max': 0.0,
                'values': deque(maxlen=100)
            }

        stat_info = stats[metric_key]
        stat_info['count'] += 1
        stat_info['sum'] += metric.value
        stat_info['min'] = min(stat_info['min'], metric.value)
        stat_info['max'] = max(stat_info['max'], metric.value)
        stat_info['values'].append(metric.value)

    def _check_alerts(self):
        """检查告警条件"""
        current_time = datetime.now()

        for threshold_key, threshold in self.thresholds.items():
            key = f"{threshold.service_name}_{threshold.metric_type.value}"

            if key in self.metrics_history and self.metrics_history[key]:
                latest_metric = self.metrics_history[key][-1]

                # 检查阈值
                alert_id = f"{threshold_key}_{int(current_time.timestamp())}"

                if latest_metric.value >= threshold.critical_threshold:
                    self._create_alert(
                        alert_id=alert_id,
                        level=AlertLevel.CRITICAL,
                        metric=latest_metric,
                        threshold=threshold.critical_threshold
                    )
                elif latest_metric.value >= threshold.warning_threshold:
                    self._create_alert(
                        alert_id=alert_id,
                        level=AlertLevel.WARNING,
                        metric=latest_metric,
                        threshold=threshold.warning_threshold
                    )

    def _create_alert(self, alert_id: str, level: AlertLevel,
                     metric: PerformanceMetric, threshold: float):
        """创建告警"""
        if alert_id in self.active_alerts:
            return  # 避免重复告警

        alert = PerformanceAlert(
            alert_id=alert_id,
            level=level,
            metric_type=metric.metric_type,
            service_name=metric.service_name,
            current_value=metric.value,
            threshold_value=threshold,
            message=f"{metric.service_name} {metric.metric_type.value} 超过{level.value}阈值: {metric.value:.2f} > {threshold}",
            timestamp=datetime.now()
        )

        self.active_alerts[alert_id] = alert
        self.logger.warning(f"性能告警: {alert.message}")

    def get_performance_summary(self, time_range: Optional[int] = None) -> Dict[str, Any]:
        """
        获取性能摘要

        Args:
            time_range: 时间范围（分钟），None表示所有数据

        Returns:
            性能摘要
        """
        cutoff_time = None
        if time_range:
            cutoff_time = datetime.now() - timedelta(minutes=time_range)

        summary = {
            'generated_at': datetime.now().isoformat(),
            'time_range_minutes': time_range,
            'services': {},
            'alerts': {
                'active': len(self.active_alerts),
                'critical': len([a for a in self.active_alerts.values() if a.level == AlertLevel.CRITICAL]),
                'warning': len([a for a in self.active_alerts.values() if a.level == AlertLevel.WARNING])
            },
            'latency_analysis': self._analyze_latency(),
            'bottleneck_analysis': self._analyze_bottlenecks()
        }

        # 按服务统计
        for service_name in self.performance_stats.keys():
            service_stats = self.performance_stats[service_name]
            service_summary = {}

            for metric_key, stat_info in service_stats.items():
                if stat_info['count'] > 0:
                    avg_value = stat_info['sum'] / stat_info['count']

                    # 应用时间过滤
                    if cutoff_time:
                        key = f"{service_name}_{metric_key.replace('_stats', '')}"
                        if key in self.metrics_history:
                            recent_values = [
                                m.value for m in self.metrics_history[key]
                                if m.timestamp >= cutoff_time
                            ]
                            if recent_values:
                                avg_value = statistics.mean(recent_values)
                            else:
                                continue

                    service_summary[metric_key] = {
                        'count': stat_info['count'],
                        'average': avg_value,
                        'min': stat_info['min'],
                        'max': stat_info['max'],
                        'latest': stat_info['values'][-1] if stat_info['values'] else None
                    }

            if service_summary:
                summary['services'][service_name] = service_summary

        return summary

    def _analyze_latency(self) -> Dict[str, Any]:
        """分析延迟数据"""
        if not self.latency_measurements:
            return {'error': '没有延迟数据'}

        recent_measurements = self.latency_measurements[-100:]  # 最近100次测量

        # 计算统计数据
        total_latencies = [m.total_latency for m in recent_measurements]
        frontend_to_backend = [m.frontend_to_backend for m in recent_measurements]
        backend_processing = [m.backend_processing for m in recent_measurements]
        database_operations = [m.database_operations for m in recent_measurements]

        analysis = {
            'sample_count': len(recent_measurements),
            'time_range': {
                'start': recent_measurements[0].timestamp.isoformat(),
                'end': recent_measurements[-1].timestamp.isoformat()
            },
            'total_latency': {
                'average': statistics.mean(total_latencies),
                'min': min(total_latencies),
                'max': max(total_latencies),
                'p95': statistics.quantiles(total_latencies, n=20)[18] if len(total_latencies) >= 20 else 0,
                'p99': statistics.quantiles(total_latencies, n=100)[98] if len(total_latencies) >= 100 else 0
            },
            'by_stage': {
                'frontend_to_backend': {
                    'average': statistics.mean(frontend_to_backend),
                    'percentage': statistics.mean(frontend_to_backend) / statistics.mean(total_latencies) * 100
                },
                'backend_processing': {
                    'average': statistics.mean(backend_processing),
                    'percentage': statistics.mean(backend_processing) / statistics.mean(total_latencies) * 100
                },
                'database_operations': {
                    'average': statistics.mean(database_operations),
                    'percentage': statistics.mean(database_operations) / statistics.mean(total_latencies) * 100
                }
            }
        }

        return analysis

    def _analyze_bottlenecks(self) -> Dict[str, Any]:
        """分析性能瓶颈"""
        bottlenecks = []

        # 分析各阶段延迟
        if self.latency_measurements:
            recent_measurements = self.latency_measurements[-50:]

            # 计算各阶段平均延迟
            avg_frontend = statistics.mean([m.frontend_to_backend for m in recent_measurements])
            avg_backend = statistics.mean([m.backend_processing for m in recent_measurements])
            avg_database = statistics.mean([m.database_operations for m in recent_measurements])

            # 找出最慢的阶段
            stage_times = {
                'frontend_to_backend': avg_frontend,
                'backend_processing': avg_backend,
                'database_operations': avg_database
            }

            slowest_stage = max(stage_times.items(), key=lambda x: x[1])

            if slowest_stage[1] > 2.0:  # 超过2秒认为是瓶颈
                bottlenecks.append({
                    'type': 'latency_bottleneck',
                    'stage': slowest_stage[0],
                    'value': slowest_stage[1],
                    'description': f'{slowest_stage[0]} 阶段响应时间过长'
                })

        # 分析资源使用
        for metric_key, metrics in self.metrics_history.items():
            if 'cpu_usage' in metric_key and metrics:
                recent_cpu = [m.value for m in list(metrics)[-20:]]
                avg_cpu = statistics.mean(recent_cpu)
                if avg_cpu > 80:
                    bottlenecks.append({
                        'type': 'resource_bottleneck',
                        'resource': 'CPU',
                        'value': avg_cpu,
                        'description': f'CPU使用率过高: {avg_cpu:.1f}%'
                    })

            elif 'memory_usage' in metric_key and metrics:
                recent_memory = [m.value for m in list(metrics)[-20:]]
                avg_memory = statistics.mean(recent_memory)
                if avg_memory > 85:
                    bottlenecks.append({
                        'type': 'resource_bottleneck',
                        'resource': 'Memory',
                        'value': avg_memory,
                        'description': f'内存使用率过高: {avg_memory:.1f}%'
                    })

        return {
            'bottlenecks': bottlenecks,
            'count': len(bottlenecks),
            'severity': 'high' if len(bottlenecks) > 3 else 'medium' if len(bottlenecks) > 0 else 'low'
        }

    def generate_performance_report(self, time_range_minutes: int = 60) -> PerformanceReport:
        """
        生成性能报告

        Args:
            time_range_minutes: 时间范围（分钟）

        Returns:
            性能报告
        """
        end_time = datetime.now()
        start_time = end_time - timedelta(minutes=time_range_minutes)

        report_id = f"perf_report_{int(end_time.timestamp())}"

        # 生成报告各部分
        metrics_summary = self.get_performance_summary(time_range_minutes)
        latency_analysis = self._analyze_latency()
        bottleneck_analysis = self._analyze_bottlenecks()

        # 趋势分析
        trend_analysis = self._analyze_trends(time_range_minutes)

        # 生成建议
        recommendations = self._generate_performance_recommendations(
            metrics_summary, bottleneck_analysis
        )

        # 收集告警
        alerts = list(self.active_alerts.values())

        return PerformanceReport(
            report_id=report_id,
            generated_at=end_time,
            time_range=(start_time, end_time),
            metrics_summary=metrics_summary,
            latency_analysis=latency_analysis,
            bottleneck_analysis=bottleneck_analysis,
            trend_analysis=trend_analysis,
            alerts=alerts,
            recommendations=recommendations
        )

    def _analyze_trends(self, time_range_minutes: int) -> Dict[str, Any]:
        """分析性能趋势"""
        trends = {}
        cutoff_time = datetime.now() - timedelta(minutes=time_range_minutes)

        for key, metrics in self.metrics_history.items():
            recent_metrics = [m for m in metrics if m.timestamp >= cutoff_time]

            if len(recent_metrics) >= 10:  # 至少需要10个数据点
                values = [m.value for m in recent_metrics]

                # 简单线性趋势分析
                n = len(values)
                x = list(range(n))

                # 计算线性回归斜率
                sum_x = sum(x)
                sum_y = sum(values)
                sum_xy = sum(x[i] * values[i] for i in range(n))
                sum_x2 = sum(x[i] ** 2 for i in range(n))

                slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x ** 2)

                # 判断趋势
                if slope > 0.01:
                    trend_direction = 'increasing'
                elif slope < -0.01:
                    trend_direction = 'decreasing'
                else:
                    trend_direction = 'stable'

                trends[key] = {
                    'direction': trend_direction,
                    'slope': slope,
                    'current_value': values[-1],
                    'average_value': statistics.mean(values),
                    'data_points': n
                }

        return trends

    def _generate_performance_recommendations(self, metrics_summary: Dict[str, Any],
                                            bottleneck_analysis: Dict[str, Any]) -> List[str]:
        """生成性能优化建议"""
        recommendations = []

        # 基于瓶颈分析生成建议
        for bottleneck in bottleneck_analysis.get('bottlenecks', []):
            if bottleneck['type'] == 'latency_bottleneck':
                stage = bottleneck['stage']
                if 'frontend' in stage:
                    recommendations.append("优化前端资源加载和渲染性能")
                elif 'backend' in stage:
                    recommendations.append("优化后端API处理逻辑，考虑缓存和数据库优化")
                elif 'database' in stage:
                    recommendations.append("优化数据库查询，添加索引和查询优化")

            elif bottleneck['type'] == 'resource_bottleneck':
                resource = bottleneck['resource']
                if resource == 'CPU':
                    recommendations.append("CPU使用率过高，建议优化算法或增加计算资源")
                elif resource == 'Memory':
                    recommendations.append("内存使用率过高，建议检查内存泄漏或增加内存")

        # 基于告警生成建议
        critical_alerts = [a for a in self.active_alerts.values() if a.level == AlertLevel.CRITICAL]
        if critical_alerts:
            recommendations.append(f"存在{len(critical_alerts)}个严重告警，需要立即处理")

        return recommendations

    def clear_metrics(self):
        """清空所有指标数据"""
        self.metrics_history.clear()
        self.latency_measurements.clear()
        self.active_alerts.clear()
        self.performance_stats.clear()
        self.logger.info("性能指标数据已清空")

    def export_metrics(self, filename: str, format: str = 'json'):
        """
        导出性能指标

        Args:
            filename: 文件名
            format: 导出格式 ('json' 或 'csv')
        """
        if format == 'json':
            data = {
                'export_time': datetime.now().isoformat(),
                'metrics': {key: [m.to_dict() for m in metrics] for key, metrics in self.metrics_history.items()},
                'latency_measurements': [m.to_dict() for m in self.latency_measurements],
                'alerts': [a.__dict__ for a in self.active_alerts.values()]
            }

            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

        elif format == 'csv':
            import csv

            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['service_name', 'metric_type', 'value', 'unit', 'timestamp'])

                for metrics in self.metrics_history.values():
                    for metric in metrics:
                        writer.writerow([
                            metric.service_name,
                            metric.metric_type.value,
                            metric.value,
                            metric.unit,
                            metric.timestamp.isoformat()
                        ])

        self.logger.info(f"性能指标已导出到: {filename}")