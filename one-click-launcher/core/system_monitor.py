"""
System Monitor Module

This module provides comprehensive system monitoring functionality for
real-time metrics collection and service status monitoring.
"""

import time
import threading
import asyncio
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json
import psutil
import platform
from pathlib import Path

from utils.logger import get_logger


class MonitorStatus(Enum):
    """监控器状态"""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"


class AlertLevel(Enum):
    """告警级别"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class SystemMetrics:
    """系统指标"""
    timestamp: datetime = field(default_factory=datetime.now)

    # CPU指标
    cpu_percent: float = 0.0
    cpu_count: int = 0
    cpu_freq: float = 0.0

    # 内存指标
    memory_percent: float = 0.0
    memory_used: int = 0
    memory_total: int = 0
    memory_available: int = 0

    # 磁盘指标
    disk_usage: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # 网络指标
    network_io: Dict[str, int] = field(default_factory=dict)

    # 进程指标
    process_count: int = 0
    active_processes: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class ServiceStatus:
    """服务状态"""
    name: str
    status: str  # "running", "stopped", "error", "unknown"
    pid: Optional[int] = None
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    uptime: Optional[float] = None
    last_check: datetime = field(default_factory=datetime.now)
    health_check_url: Optional[str] = None
    response_time: Optional[float] = None


@dataclass
class MonitorAlert:
    """监控告警"""
    alert_id: str
    level: AlertLevel
    message: str
    source: str
    timestamp: datetime = field(default_factory=datetime.now)
    metrics: Dict[str, Any] = field(default_factory=dict)
    acknowledged: bool = False


class SystemMonitor:
    """
    系统监控器，提供全面的系统指标收集和服务状态监控
    """

    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化系统监控器

        Args:
            config: 监控配置
        """
        self.logger = get_logger(self.__class__.__name__)

        # 配置
        self.config = config or self._get_default_config()

        # 状态
        self.status = MonitorStatus.STOPPED
        self.start_time: Optional[datetime] = None
        self.metrics_history: List[SystemMetrics] = []
        self.service_statuses: Dict[str, ServiceStatus] = {}
        self.alerts: List[MonitorAlert] = []

        # 监控线程
        self.monitor_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()

        # 回调函数
        self.alert_callbacks: List[Callable[[MonitorAlert], None]] = []
        self.metric_callbacks: List[Callable[[SystemMetrics], None]] = []

        # 阈值
        self.thresholds = self.config.get("thresholds", {})

        # 监控间隔
        self.monitor_interval = self.config.get("monitor_interval", 5.0)

        # 历史数据保留
        self.max_history_size = self.config.get("max_history_size", 1000)

        self.logger.info("System Monitor initialized")

    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "monitor_interval": 5.0,
            "max_history_size": 1000,
            "enable_service_monitoring": True,
            "enable_performance_monitoring": True,
            "thresholds": {
                "cpu_warning": 70.0,
                "cpu_critical": 90.0,
                "memory_warning": 75.0,
                "memory_critical": 90.0,
                "disk_warning": 80.0,
                "disk_critical": 95.0,
                "response_time_warning": 5.0,
                "response_time_critical": 10.0
            },
            "services": {
                "database": {
                    "ports": [5432],
                    "health_check_urls": [],
                    "process_names": ["postgres", "postgresql"]
                },
                "backend": {
                    "ports": [8000],
                    "health_check_urls": ["http://localhost:8000/health"],
                    "process_names": ["python", "node"]
                },
                "frontend": {
                    "ports": [3000],
                    "health_check_urls": ["http://localhost:3000"],
                    "process_names": ["node", "npm"]
                }
            }
        }

    def start_monitoring(self) -> bool:
        """
        启动监控

        Returns:
            是否启动成功
        """
        if self.status == MonitorStatus.RUNNING:
            self.logger.warning("Monitor is already running")
            return True

        try:
            self.status = MonitorStatus.STARTING
            self.start_time = datetime.now()
            self.stop_event.clear()

            # 启动监控线程
            self.monitor_thread = threading.Thread(
                target=self._monitoring_loop,
                name="SystemMonitor",
                daemon=True
            )
            self.monitor_thread.start()

            # 等待线程启动
            time.sleep(0.1)

            if self.monitor_thread.is_alive():
                self.status = MonitorStatus.RUNNING
                self.logger.info("System monitoring started")
                return True
            else:
                self.status = MonitorStatus.ERROR
                self.logger.error("Failed to start monitoring thread")
                return False

        except Exception as e:
            self.status = MonitorStatus.ERROR
            self.logger.error(f"Error starting monitoring: {e}")
            return False

    def stop_monitoring(self) -> bool:
        """
        停止监控

        Returns:
            是否停止成功
        """
        if self.status != MonitorStatus.RUNNING:
            return True

        try:
            self.status = MonitorStatus.STOPPING
            self.stop_event.set()

            # 等待线程结束
            if self.monitor_thread and self.monitor_thread.is_alive():
                self.monitor_thread.join(timeout=10.0)

            self.status = MonitorStatus.STOPPED
            self.logger.info("System monitoring stopped")
            return True

        except Exception as e:
            self.logger.error(f"Error stopping monitoring: {e}")
            return False

    def _monitoring_loop(self):
        """监控循环"""
        self.logger.debug("Starting monitoring loop")

        while not self.stop_event.is_set():
            try:
                # 收集系统指标
                if self.config.get("enable_performance_monitoring", True):
                    metrics = self._collect_system_metrics()
                    self._process_metrics(metrics)

                # 检查服务状态
                if self.config.get("enable_service_monitoring", True):
                    self._check_service_statuses()

                # 清理历史数据
                self._cleanup_history()

                # 等待下次监控
                self.stop_event.wait(self.monitor_interval)

            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                # 创建错误告警
                self._create_alert(
                    AlertLevel.ERROR,
                    f"Monitoring loop error: {e}",
                    "system_monitor"
                )
                time.sleep(1.0)  # 防止快速错误循环

        self.logger.debug("Monitoring loop ended")

    def _collect_system_metrics(self) -> SystemMetrics:
        """收集系统指标"""
        try:
            metrics = SystemMetrics()

            # CPU指标
            metrics.cpu_percent = psutil.cpu_percent(interval=0.1)
            metrics.cpu_count = psutil.cpu_count()
            cpu_freq = psutil.cpu_freq()
            metrics.cpu_freq = cpu_freq.current if cpu_freq else 0.0

            # 内存指标
            memory = psutil.virtual_memory()
            metrics.memory_percent = memory.percent
            metrics.memory_used = memory.used
            metrics.memory_total = memory.total
            metrics.memory_available = memory.available

            # 磁盘指标
            for partition in psutil.disk_partitions():
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    metrics.disk_usage[partition.mountpoint] = {
                        "total": usage.total,
                        "used": usage.used,
                        "free": usage.free,
                        "percent": (usage.used / usage.total) * 100
                    }
                except (PermissionError, OSError):
                    continue

            # 网络指标
            network = psutil.net_io_counters()
            metrics.network_io = {
                "bytes_sent": network.bytes_sent,
                "bytes_recv": network.bytes_recv,
                "packets_sent": network.packets_sent,
                "packets_recv": network.packets_recv
            }

            # 进程指标
            metrics.process_count = len(psutil.pids())

            # 活跃进程（按CPU使用率排序的前10个）
            active_processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                try:
                    proc_info = proc.info
                    if proc_info['cpu_percent'] > 0:
                        active_processes.append(proc_info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            # 按CPU使用率排序并取前10个
            active_processes.sort(key=lambda x: x['cpu_percent'], reverse=True)
            metrics.active_processes = active_processes[:10]

            return metrics

        except Exception as e:
            self.logger.error(f"Error collecting system metrics: {e}")
            return SystemMetrics()

    def _process_metrics(self, metrics: SystemMetrics):
        """处理系统指标"""
        # 添加到历史记录
        self.metrics_history.append(metrics)

        # 检查阈值并创建告警
        self._check_thresholds(metrics)

        # 调用指标回调
        for callback in self.metric_callbacks:
            try:
                callback(metrics)
            except Exception as e:
                self.logger.error(f"Error in metric callback: {e}")

    def _check_thresholds(self, metrics: SystemMetrics):
        """检查阈值并创建告警"""
        # CPU阈值检查
        cpu_warning = self.thresholds.get("cpu_warning", 70.0)
        cpu_critical = self.thresholds.get("cpu_critical", 90.0)

        if metrics.cpu_percent >= cpu_critical:
            self._create_alert(
                AlertLevel.CRITICAL,
                f"CPU usage is critical: {metrics.cpu_percent:.1f}%",
                "cpu_monitor",
                {"cpu_percent": metrics.cpu_percent}
            )
        elif metrics.cpu_percent >= cpu_warning:
            self._create_alert(
                AlertLevel.WARNING,
                f"CPU usage is high: {metrics.cpu_percent:.1f}%",
                "cpu_monitor",
                {"cpu_percent": metrics.cpu_percent}
            )

        # 内存阈值检查
        memory_warning = self.thresholds.get("memory_warning", 75.0)
        memory_critical = self.thresholds.get("memory_critical", 90.0)

        if metrics.memory_percent >= memory_critical:
            self._create_alert(
                AlertLevel.CRITICAL,
                f"Memory usage is critical: {metrics.memory_percent:.1f}%",
                "memory_monitor",
                {"memory_percent": metrics.memory_percent}
            )
        elif metrics.memory_percent >= memory_warning:
            self._create_alert(
                AlertLevel.WARNING,
                f"Memory usage is high: {metrics.memory_percent:.1f}%",
                "memory_monitor",
                {"memory_percent": metrics.memory_percent}
            )

        # 磁盘阈值检查
        disk_warning = self.thresholds.get("disk_warning", 80.0)
        disk_critical = self.thresholds.get("disk_critical", 95.0)

        for mount_point, usage in metrics.disk_usage.items():
            if usage["percent"] >= disk_critical:
                self._create_alert(
                    AlertLevel.CRITICAL,
                    f"Disk usage is critical on {mount_point}: {usage['percent']:.1f}%",
                    "disk_monitor",
                    {"mount_point": mount_point, "percent": usage["percent"]}
                )
            elif usage["percent"] >= disk_warning:
                self._create_alert(
                    AlertLevel.WARNING,
                    f"Disk usage is high on {mount_point}: {usage['percent']:.1f}%",
                    "disk_monitor",
                    {"mount_point": mount_point, "percent": usage["percent"]}
                )

    def _check_service_statuses(self):
        """检查服务状态"""
        services_config = self.config.get("services", {})

        for service_name, service_config in services_config.items():
            try:
                status = self._check_single_service(service_name, service_config)
                self.service_statuses[service_name] = status

                # 检查服务响应时间阈值
                if status.response_time:
                    resp_warning = self.thresholds.get("response_time_warning", 5.0)
                    resp_critical = self.thresholds.get("response_time_critical", 10.0)

                    if status.response_time >= resp_critical:
                        self._create_alert(
                            AlertLevel.CRITICAL,
                            f"Service {service_name} response time is critical: {status.response_time:.2f}s",
                            "service_monitor",
                            {"service": service_name, "response_time": status.response_time}
                        )
                    elif status.response_time >= resp_warning:
                        self._create_alert(
                            AlertLevel.WARNING,
                            f"Service {service_name} response time is slow: {status.response_time:.2f}s",
                            "service_monitor",
                            {"service": service_name, "response_time": status.response_time}
                        )

                # 检查服务是否停止
                if status.status == "stopped":
                    self._create_alert(
                        AlertLevel.ERROR,
                        f"Service {service_name} is stopped",
                        "service_monitor",
                        {"service": service_name, "status": status.status}
                    )
                elif status.status == "error":
                    self._create_alert(
                        AlertLevel.CRITICAL,
                        f"Service {service_name} is in error state",
                        "service_monitor",
                        {"service": service_name, "status": status.status}
                    )

            except Exception as e:
                self.logger.error(f"Error checking service {service_name}: {e}")

    def _check_single_service(self, service_name: str, service_config: Dict[str, Any]) -> ServiceStatus:
        """检查单个服务状态"""
        status = ServiceStatus(
            name=service_name,
            status="unknown",
            last_check=datetime.now()
        )

        # 检查端口
        ports = service_config.get("ports", [])
        if ports:
            status.status = "stopped"  # 假设停止，如果找到运行中的进程则更新

        for port in ports:
            try:
                import socket
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1.0)
                result = sock.connect_ex(('localhost', port))
                sock.close()

                if result == 0:
                    status.status = "running"
                    break
            except Exception:
                continue

        # 检查进程
        process_names = service_config.get("process_names", [])
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                proc_info = proc.info
                if any(name.lower() in proc_info['name'].lower() for name in process_names):
                    status.pid = proc_info['pid']
                    status.cpu_percent = proc_info['cpu_percent']
                    status.memory_percent = proc_info['memory_percent']
                    if status.status == "unknown":
                        status.status = "running"
                    break
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        # 健康检查
        health_urls = service_config.get("health_check_urls", [])
        if health_urls:
            import aiohttp
            import asyncio

            async def _check_health():
                try:
                    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5.0)) as session:
                        start_time = time.time()
                        async with session.get(health_urls[0]) as response:
                            status.response_time = time.time() - start_time
                            if response.status == 200:
                                if status.status == "unknown":
                                    status.status = "running"
                            else:
                                status.status = "error"
                except Exception:
                    if status.status == "unknown":
                        status.status = "error"

            # 在同步环境中运行异步检查
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # 如果已经在事件循环中，创建任务
                    asyncio.create_task(_check_health())
                else:
                    # 如果没有事件循环，运行新的
                    asyncio.run(_check_health())
            except Exception:
                # 如果异步检查失败，不影响整体状态
                pass

        return status

    def _create_alert(self, level: AlertLevel, message: str, source: str, metrics: Dict[str, Any] = None):
        """创建告警"""
        alert = MonitorAlert(
            alert_id=f"alert_{int(time.time())}_{len(self.alerts)}",
            level=level,
            message=message,
            source=source,
            metrics=metrics or {}
        )

        self.alerts.append(alert)

        # 调用告警回调
        for callback in self.alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                self.logger.error(f"Error in alert callback: {e}")

        # 记录日志
        log_message = f"ALERT [{level.value.upper()}] {source}: {message}"
        if level == AlertLevel.CRITICAL:
            self.logger.critical(log_message)
        elif level == AlertLevel.ERROR:
            self.logger.error(log_message)
        elif level == AlertLevel.WARNING:
            self.logger.warning(log_message)
        else:
            self.logger.info(log_message)

    def _cleanup_history(self):
        """清理历史数据"""
        # 清理指标历史
        if len(self.metrics_history) > self.max_history_size:
            self.metrics_history = self.metrics_history[-self.max_history_size:]

        # 清理告警历史（保留最近100个）
        if len(self.alerts) > 100:
            self.alerts = self.alerts[-100:]

    def get_current_metrics(self) -> Optional[SystemMetrics]:
        """获取当前系统指标"""
        if self.metrics_history:
            return self.metrics_history[-1]

        # 如果还没有历史数据但监控正在运行，尝试立即收集一次
        if self.status == MonitorStatus.RUNNING:
            try:
                metrics = self._collect_system_metrics()
                self._process_metrics(metrics)
                return metrics
            except Exception as e:
                self.logger.warning(f"Failed to collect immediate metrics: {e}")

        return None

    def get_metrics_history(self, minutes: int = 60) -> List[SystemMetrics]:
        """
       获取指定时间范围内的指标历史

        Args:
            minutes: 时间范围（分钟）

        Returns:
            指标历史列表
        """
        # 如果没有历史数据但监控正在运行，尝试立即收集一次
        if not self.metrics_history and self.status == MonitorStatus.RUNNING:
            try:
                metrics = self._collect_system_metrics()
                self._process_metrics(metrics)
            except Exception as e:
                self.logger.warning(f"Failed to collect immediate metrics for history: {e}")

        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        return [m for m in self.metrics_history if m.timestamp >= cutoff_time]

    def get_service_statuses(self) -> Dict[str, ServiceStatus]:
        """获取所有服务状态"""
        return self.service_statuses.copy()

    def get_alerts(self, level: AlertLevel = None, acknowledged: bool = None) -> List[MonitorAlert]:
        """
        获取告警列表

        Args:
            level: 告警级别过滤
            acknowledged: 是否已确认过滤

        Returns:
            告警列表
        """
        alerts = self.alerts.copy()

        if level:
            alerts = [a for a in alerts if a.level == level]

        if acknowledged is not None:
            alerts = [a for a in alerts if a.acknowledged == acknowledged]

        return alerts

    def acknowledge_alert(self, alert_id: str) -> bool:
        """
        确认告警

        Args:
            alert_id: 告警ID

        Returns:
            是否成功确认
        """
        for alert in self.alerts:
            if alert.alert_id == alert_id:
                alert.acknowledged = True
                self.logger.info(f"Alert {alert_id} acknowledged")
                return True
        return False

    def add_alert_callback(self, callback: Callable[[MonitorAlert], None]):
        """添加告警回调函数"""
        self.alert_callbacks.append(callback)

    def add_metric_callback(self, callback: Callable[[SystemMetrics], None]):
        """添加指标回调函数"""
        self.metric_callbacks.append(callback)

    def get_monitor_summary(self) -> Dict[str, Any]:
        """获取监控摘要"""
        uptime = None
        if self.start_time:
            uptime = (datetime.now() - self.start_time).total_seconds()

        current_metrics = self.get_current_metrics()

        return {
            "status": self.status.value,
            "uptime_seconds": uptime,
            "metrics_count": len(self.metrics_history),
            "services_count": len(self.service_statuses),
            "alerts_count": len(self.alerts),
            "unacknowledged_alerts": len([a for a in self.alerts if not a.acknowledged]),
            "current_metrics": current_metrics.__dict__ if current_metrics else None,
            "service_statuses": {name: status.__dict__ for name, status in self.service_statuses.items()}
        }

    def export_monitor_data(self, format: str = "json") -> str:
        """
        导出监控数据

        Args:
            format: 导出格式 (json, csv)

        Returns:
            导出的数据字符串
        """
        if format.lower() == "json":
            data = {
                "export_time": datetime.now().isoformat(),
                "monitor_summary": self.get_monitor_summary(),
                "metrics_history": [m.__dict__ for m in self.metrics_history],
                "service_statuses": {name: status.__dict__ for name, status in self.service_statuses.items()},
                "alerts": [alert.__dict__ for alert in self.alerts]
            }
            return json.dumps(data, indent=2, default=str)

        elif format.lower() == "csv":
            import csv
            import io

            output = io.StringIO()
            writer = csv.writer(output)

            # 写入指标数据
            writer.writerow(["timestamp", "cpu_percent", "memory_percent", "process_count"])
            for metrics in self.metrics_history:
                writer.writerow([
                    metrics.timestamp.isoformat(),
                    metrics.cpu_percent,
                    metrics.memory_percent,
                    metrics.process_count
                ])

            return output.getvalue()

        else:
            raise ValueError(f"Unsupported export format: {format}")