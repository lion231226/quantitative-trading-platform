"""
Monitoring Dashboard Module

This module provides a real-time monitoring dashboard using rich library
for beautiful CLI interface display.
"""

import time
import threading
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from enum import Enum

try:
    from rich.console import Console
    from rich.layout import Layout
    from rich.panel import Panel
    from rich.table import Table
    from rich.progress import Progress, BarColumn, TextColumn, TimeElapsedColumn
    from rich.live import Live
    from rich.text import Text
    from rich.align import Align
    from rich.columns import Columns
    from rich import box
    from rich.status import Status
    # Gauge class doesn't exist in current Rich versions, will create custom implementation
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

from core.system_monitor import SystemMonitor, SystemMetrics, ServiceStatus, MonitorAlert, AlertLevel, MonitorStatus
from utils.logger import get_logger


# Custom Gauge implementation since rich.gauge doesn't exist
class Gauge:
    """Custom Gauge implementation for progress visualization"""

    def __init__(self, value: float = 0.0, style: str = "bar.back"):
        self.value = max(0.0, min(1.0, value))  # Clamp between 0 and 1
        self.style = style

    def __rich_console__(self, console, options):
        """Render the gauge"""
        width = options.max_width or 20
        filled = int(width * self.value)
        bar = "█" * filled + "░" * (width - filled)
        return Text(f"{bar} {self.value*100:.1f}%")


class DashboardTheme(Enum):
    """仪表板主题"""
    DEFAULT = "default"
    DARK = "dark"
    LIGHT = "light"
    COLORFUL = "colorful"


class MonitoringDashboard:
    """
    监控仪表板，提供实时系统监控的可视化界面
    """

    def __init__(self, system_monitor: SystemMonitor, config: Dict[str, Any] = None):
        """
        初始化监控仪表板

        Args:
            system_monitor: 系统监控器实例
            config: 仪表板配置
        """
        self.logger = get_logger(self.__class__.__name__)

        if not RICH_AVAILABLE:
            self.logger.error("Rich library is not available. Please install it with: pip install rich")
            raise ImportError("Rich library is required for MonitoringDashboard")

        self.monitor = system_monitor
        self.config = config or self._get_default_config()

        # Rich 控制台
        self.console = Console()

        # 布局
        self.layout = Layout()

        # 状态
        self.is_running = False
        self.live: Optional[Live] = None
        self.update_interval = self.config.get("update_interval", 2.0)

        # 主题
        self.theme = self.config.get("theme", DashboardTheme.DEFAULT)

        # 过滤器
        self.alert_level_filter = self.config.get("alert_level_filter", None)
        self.show_services = self.config.get("show_services", True)
        self.show_processes = self.config.get("show_processes", True)
        self.show_alerts = self.config.get("show_alerts", True)

        # 布局配置
        self._setup_layout()

        self.logger.info("Monitoring Dashboard initialized")

    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "update_interval": 2.0,
            "theme": DashboardTheme.DEFAULT,
            "show_services": True,
            "show_processes": True,
            "show_alerts": True,
            "alert_level_filter": None,
            "max_process_display": 10,
            "max_alert_display": 10,
            "history_minutes": 60,
            "auto_refresh": True,
            "show_graphs": True
        }

    def _setup_layout(self):
        """设置布局"""
        self.layout.split(
            Layout(name="header", size=3),
            Layout(name="main"),
            Layout(name="footer", size=3)
        )

        self.layout["main"].split_row(
            Layout(name="left", ratio=1),
            Layout(name="center", ratio=2),
            Layout(name="right", ratio=1)
        )

        self.layout["left"].split_column(
            Layout(name="system_info", size=12),
            Layout(name="services", size=15)
        )

        self.layout["center"].split_column(
            Layout(name="metrics", size=20),
            Layout(name="processes", size=15)
        )

        self.layout["right"].split_column(
            Layout(name="alerts", size=20),
            Layout(name="performance", size=10)
        )

    def start_dashboard(self):
        """启动仪表板"""
        if self.is_running:
            self.logger.warning("Dashboard is already running")
            return

        try:
            self.is_running = True

            with Live(
                self.layout,
                console=self.console,
                refresh_per_second=1/self.update_interval,
                screen=False,
                auto_refresh=self.config.get("auto_refresh", True)
            ) as self.live:
                while self.is_running:
                    self._update_dashboard()
                    time.sleep(self.update_interval)

        except KeyboardInterrupt:
            self.stop_dashboard()
        except Exception as e:
            self.logger.error(f"Error running dashboard: {e}")
            self.stop_dashboard()

    def stop_dashboard(self):
        """停止仪表板"""
        self.is_running = False
        if self.live:
            self.live.stop()
        self.logger.info("Monitoring dashboard stopped")

    def _update_dashboard(self):
        """更新仪表板内容"""
        try:
            # 更新各个区域
            self._update_header()
            self._update_system_info()
            self._update_services()
            self._update_metrics()
            self._update_processes()
            self._update_alerts()
            self._update_performance()
            self._update_footer()

        except Exception as e:
            self.logger.error(f"Error updating dashboard: {e}")

    def _update_header(self):
        """更新头部"""
        summary = self.monitor.get_monitor_summary()

        # 状态颜色
        status_color = self._get_status_color(summary["status"])

        header_text = Text()
        header_text.append("🖥️  System Monitoring Dashboard ", style="bold blue")
        header_text.append(f"Status: ", style="default")
        header_text.append(f"{summary['status'].upper()} ", style=f"bold {status_color}")
        header_text.append(f"Uptime: ", style="default")
        header_text.append(f"{self._format_uptime(summary['uptime_seconds'])} ", style="green")
        header_text.append(f"Updated: ", style="default")
        header_text.append(f"{datetime.now().strftime('%H:%M:%S')} ", style="cyan")

        panel = Panel(
            Align.center(header_text),
            box=box.ROUNDED,
            style="on blue"
        )

        self.layout["header"].update(panel)

    def _update_system_info(self):
        """更新系统信息"""
        current_metrics = self.monitor.get_current_metrics()

        if not current_metrics:
            self.layout["system_info"].update(
                Panel("No metrics available", title="📊 System Information", box=box.ROUNDED)
            )
            return

        # 创建系统信息表格
        table = Table(show_header=False, box=None, padding=0)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="white")

        # CPU信息
        cpu_color = self._get_percentage_color(current_metrics.cpu_percent)
        table.add_row("CPU Usage:", f"[{cpu_color}]{current_metrics.cpu_percent:.1f}%[/{cpu_color}]")
        table.add_row("CPU Cores:", str(current_metrics.cpu_count))
        table.add_row("CPU Freq:", f"{current_metrics.cpu_freq:.0f} MHz")

        # 内存信息
        memory_color = self._get_percentage_color(current_metrics.memory_percent)
        memory_gb = current_metrics.memory_used / (1024**3)
        memory_total_gb = current_metrics.memory_total / (1024**3)
        table.add_row("Memory Usage:", f"[{memory_color}]{current_metrics.memory_percent:.1f}%[/{memory_color}]")
        table.add_row("Memory Used:", f"{memory_gb:.1f} GB / {memory_total_gb:.1f} GB")

        # 进程信息
        table.add_row("Processes:", str(current_metrics.process_count))

        # 网络信息
        network_mb_sent = current_metrics.network_io.get("bytes_sent", 0) / (1024**2)
        network_mb_recv = current_metrics.network_io.get("bytes_recv", 0) / (1024**2)
        table.add_row("Network Sent:", f"{network_mb_sent:.1f} MB")
        table.add_row("Network Recv:", f"{network_mb_recv:.1f} MB")

        panel = Panel(
            table,
            title="📊 System Information",
            box=box.ROUNDED,
            border_style="blue"
        )

        self.layout["system_info"].update(panel)

    def _update_services(self):
        """更新服务状态"""
        if not self.show_services:
            self.layout["services"].update(Panel("", title="🔧 Services", box=box.ROUNDED))
            return

        services = self.monitor.get_service_statuses()

        if not services:
            self.layout["services"].update(
                Panel("No services configured", title="🔧 Services", box=box.ROUNDED)
            )
            return

        table = Table(title="Service Status", box=box.ROUNDED)
        table.add_column("Service", style="cyan")
        table.add_column("Status", style="white")
        table.add_column("CPU", style="white")
        table.add_column("Memory", style="white")
        table.add_column("Response", style="white")

        for service_name, status in services.items():
            # 状态颜色
            status_color = self._get_service_status_color(status.status)
            status_text = f"[{status_color}]{status.status}[/{status_color}]"

            # CPU和内存百分比
            cpu_text = f"{status.cpu_percent:.1f}%" if status.cpu_percent > 0 else "N/A"
            memory_text = f"{status.memory_percent:.1f}%" if status.memory_percent > 0 else "N/A"

            # 响应时间
            response_text = f"{status.response_time:.2f}s" if status.response_time else "N/A"

            table.add_row(
                service_name,
                status_text,
                cpu_text,
                memory_text,
                response_text
            )

        panel = Panel(
            table,
            title="🔧 Services",
            box=box.ROUNDED,
            border_style="green"
        )

        self.layout["services"].update(panel)

    def _update_metrics(self):
        """更新指标显示"""
        if not self.config.get("show_graphs", True):
            self.layout["metrics"].update(Panel("", title="📈 Metrics", box=box.ROUNDED))
            return

        # 获取历史数据
        history = self.monitor.get_metrics_history(self.config.get("history_minutes", 60))

        if len(history) < 2:
            self.layout["metrics"].update(
                Panel("Insufficient data for graphs", title="📈 Metrics", box=box.ROUNDED)
            )
            return

        # 创建CPU和内存使用率图表
        current_metrics = history[-1]

        # CPU使用率仪表
        cpu_gauge = Gauge(
            current_metrics.cpu_percent / 100,
            title="CPU Usage",
            style=self._get_gauge_style(current_metrics.cpu_percent)
        )

        # 内存使用率仪表
        memory_gauge = Gauge(
            current_metrics.memory_percent / 100,
            title="Memory Usage",
            style=self._get_gauge_style(current_metrics.memory_percent)
        )

        # 磁盘使用率（只显示前几个）
        disk_text = Text("Disk Usage:\n", style="bold cyan")
        for mount_point, usage in list(current_metrics.disk_usage.items())[:3]:
            disk_color = self._get_percentage_color(usage["percent"])
            disk_text.append(f"  {mount_point}: ", style="default")
            disk_text.append(f"{usage['percent']:.1f}%\n", style=disk_color)

        # 组合显示
        columns = Columns([
            Panel(cpu_gauge, title="CPU", box=box.ROUNDED, border_style="blue"),
            Panel(memory_gauge, title="Memory", box=box.ROUNDED, border_style="green"),
            Panel(disk_text, title="Disk", box=box.ROUNDED, border_style="yellow")
        ])

        panel = Panel(
            columns,
            title="📈 Metrics",
            box=box.ROUNDED,
            border_style="cyan"
        )

        self.layout["metrics"].update(panel)

    def _update_processes(self):
        """更新进程列表"""
        if not self.show_processes:
            self.layout["processes"].update(Panel("", title="⚙️  Top Processes", box=box.ROUNDED))
            return

        current_metrics = self.monitor.get_current_metrics()

        if not current_metrics or not current_metrics.active_processes:
            self.layout["processes"].update(
                Panel("No process data available", title="⚙️  Top Processes", box=box.ROUNDED)
            )
            return

        table = Table(title="Top Processes", box=box.ROUNDED)
        table.add_column("PID", style="cyan")
        table.add_column("Name", style="white")
        table.add_column("CPU%", style="white")
        table.add_column("Mem%", style="white")

        max_processes = self.config.get("max_process_display", 10)
        for process in current_metrics.active_processes[:max_processes]:
            cpu_color = self._get_percentage_color(process.get('cpu_percent', 0))
            memory_color = self._get_percentage_color(process.get('memory_percent', 0))

            table.add_row(
                str(process.get('pid', 'N/A')),
                process.get('name', 'Unknown')[:20],  # 限制名称长度
                f"[{cpu_color}]{process.get('cpu_percent', 0):.1f}%[/{cpu_color}]",
                f"[{memory_color}]{process.get('memory_percent', 0):.1f}%[/{memory_color}]"
            )

        panel = Panel(
            table,
            title="⚙️  Top Processes",
            box=box.ROUNDED,
            border_style="yellow"
        )

        self.layout["processes"].update(panel)

    def _update_alerts(self):
        """更新告警列表"""
        if not self.show_alerts:
            self.layout["alerts"].update(Panel("", title="🚨 Alerts", box=box.ROUNDED))
            return

        alerts = self.monitor.get_alerts(level=self.alert_level_filter, acknowledged=False)

        if not alerts:
            self.layout["alerts"].update(
                Panel("No active alerts", title="🚨 Alerts", box=box.ROUNDED)
            )
            return

        # 只显示最近的告警
        max_alerts = self.config.get("max_alert_display", 10)
        recent_alerts = alerts[-max_alerts:]

        table = Table(title="Active Alerts", box=box.ROUNDED)
        table.add_column("Time", style="cyan")
        table.add_column("Level", style="white")
        table.add_column("Source", style="white")
        table.add_column("Message", style="white")

        for alert in recent_alerts:
            level_color = self._get_alert_level_color(alert.level)
            time_str = alert.timestamp.strftime("%H:%M:%S")
            message = alert.message[:50] + "..." if len(alert.message) > 50 else alert.message

            table.add_row(
                time_str,
                f"[{level_color}]{alert.level.value.upper()}[/{level_color}]",
                alert.source,
                message
            )

        panel = Panel(
            table,
            title=f"🚨 Alerts ({len(alerts)} total)",
            box=box.ROUNDED,
            border_style="red"
        )

        self.layout["alerts"].update(panel)

    def _update_performance(self):
        """更新性能指标"""
        summary = self.monitor.get_monitor_summary()

        # 性能统计
        perf_text = Text()
        perf_text.append("Performance Stats:\n\n", style="bold cyan")

        # 监控统计
        perf_text.append(f"Metrics Collected: ", style="default")
        perf_text.append(f"{summary['metrics_count']}\n", style="green")

        perf_text.append(f"Services Monitored: ", style="default")
        perf_text.append(f"{summary['services_count']}\n", style="green")

        perf_text.append(f"Total Alerts: ", style="default")
        perf_text.append(f"{summary['alerts_count']}\n", style="yellow")

        perf_text.append(f"Unacknowledged: ", style="default")
        perf_text.append(f"{summary['unacknowledged_alerts']}\n", style="red")

        # 数据库/缓存统计（如果有）
        perf_text.append("\nData Storage:\n", style="bold cyan")
        perf_text.append(f"History Retention: ", style="default")
        perf_text.append(f"{self.config.get('history_minutes', 60)} min\n", style="white")

        panel = Panel(
            perf_text,
            title="⚡ Performance",
            box=box.ROUNDED,
            border_style="magenta"
        )

        self.layout["performance"].update(panel)

    def _update_footer(self):
        """更新底部"""
        footer_text = Text()
        footer_text.append("Controls: ", style="bold")
        footer_text.append("[Q]uit ", style="green")
        footer_text.append("[R]efresh ", style="yellow")
        footer_text.append("[A]ck Alerts ", style="cyan")
        footer_text.append("[T]heme ", style="magenta")

        if self.monitor.status == MonitorStatus.RUNNING:
            footer_text.append(" | ", style="default")
            footer_text.append("Monitor: ", style="default")
            footer_text.append("RUNNING ", style="green bold")
        else:
            footer_text.append(" | ", style="default")
            footer_text.append("Monitor: ", style="default")
            footer_text.append(f"{self.monitor.status.value.upper()} ", style="red bold")

        panel = Panel(
            Align.center(footer_text),
            box=box.ROUNDED,
            style="on dark_blue"
        )

        self.layout["footer"].update(panel)

    def _get_status_color(self, status: str) -> str:
        """获取状态颜色"""
        status_colors = {
            MonitorStatus.RUNNING.value: "green",
            MonitorStatus.STOPPED.value: "red",
            MonitorStatus.STARTING.value: "yellow",
            MonitorStatus.STOPPING.value: "yellow",
            MonitorStatus.ERROR.value: "red"
        }
        return status_colors.get(status, "white")

    def _get_service_status_color(self, status: str) -> str:
        """获取服务状态颜色"""
        service_colors = {
            "running": "green",
            "stopped": "red",
            "error": "red",
            "unknown": "yellow"
        }
        return service_colors.get(status, "white")

    def _get_alert_level_color(self, level: AlertLevel) -> str:
        """获取告警级别颜色"""
        alert_colors = {
            AlertLevel.INFO: "blue",
            AlertLevel.WARNING: "yellow",
            AlertLevel.ERROR: "red",
            AlertLevel.CRITICAL: "bold red"
        }
        return alert_colors.get(level, "white")

    def _get_percentage_color(self, percentage: float) -> str:
        """获取百分比颜色"""
        if percentage >= 90:
            return "red"
        elif percentage >= 75:
            return "yellow"
        elif percentage >= 50:
            return "cyan"
        else:
            return "green"

    def _get_gauge_style(self, percentage: float) -> str:
        """获取仪表样式"""
        if percentage >= 90:
            return "bar.back:red"
        elif percentage >= 75:
            return "bar.back:yellow"
        elif percentage >= 50:
            return "bar.back:blue"
        else:
            return "bar.back:green"

    def _format_uptime(self, uptime_seconds: Optional[float]) -> str:
        """格式化运行时间"""
        if not uptime_seconds:
            return "N/A"

        hours = int(uptime_seconds // 3600)
        minutes = int((uptime_seconds % 3600) // 60)
        seconds = int(uptime_seconds % 60)

        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"

    def set_theme(self, theme: DashboardTheme):
        """设置主题"""
        self.theme = theme
        self.config["theme"] = theme
        # 这里可以添加更多主题相关的设置

    def set_alert_filter(self, level: AlertLevel = None):
        """设置告警过滤器"""
        self.alert_level_filter = level
        self.config["alert_level_filter"] = level

    def toggle_section(self, section: str):
        """切换显示区域"""
        if section == "services":
            self.show_services = not self.show_services
            self.config["show_services"] = self.show_services
        elif section == "processes":
            self.show_processes = not self.show_processes
            self.config["show_processes"] = self.show_processes
        elif section == "alerts":
            self.show_alerts = not self.show_alerts
            self.config["show_alerts"] = self.show_alerts

    def acknowledge_all_alerts(self):
        """确认所有告警"""
        alerts = self.monitor.get_alerts(acknowledged=False)
        for alert in alerts:
            self.monitor.acknowledge_alert(alert.alert_id)
        self.logger.info(f"Acknowledged {len(alerts)} alerts")

    def refresh(self):
        """手动刷新"""
        self._update_dashboard()

    def handle_user_input(self):
        """处理用户输入（简化版本）"""
        # 这是一个简化版本，实际应用中可以使用更复杂的输入处理
        self.console.print("\n[bold]Dashboard Controls:[/bold]")
        self.console.print("  [Q]uit - Exit dashboard")
        self.console.print("  [R]efresh - Force refresh")
        self.console.print("  [A]ck - Acknowledge all alerts")
        self.console.print("  [T]heme - Change theme")
        self.console.print("  [S]ervices - Toggle services display")
        self.console.print("  [P]rocesses - Toggle processes display")
        self.console.print("  [Lerts - Toggle alerts display")