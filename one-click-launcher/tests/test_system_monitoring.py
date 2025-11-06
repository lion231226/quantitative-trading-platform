"""
System Monitoring Tests

This module contains comprehensive tests for the system monitoring and
log management functionality.
"""

import unittest
import time
import tempfile
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from pathlib import Path

# Test imports
from core.system_monitor import SystemMonitor, SystemMetrics, ServiceStatus, MonitorAlert, AlertLevel, MonitorStatus
from core.monitoring_dashboard import MonitoringDashboard, DashboardTheme
from core.log_manager import LogManager, LogEntry, LogLevel, LogCategory, LogFilter
from utils.log_analyzer import LogAnalyzer, AnalysisType, PatternMatch
from utils.log_exporter import LogExporter, ExportFormat, PrivacyLevel, ExportConfig


class TestSystemMonitor(unittest.TestCase):
    """系统监控器测试"""

    def setUp(self):
        """测试设置"""
        self.config = {
            "monitor_interval": 0.1,  # 快速测试
            "max_history_size": 10,
            "enable_service_monitoring": True,
            "enable_performance_monitoring": True,
            "thresholds": {
                "cpu_warning": 50.0,
                "cpu_critical": 80.0,
                "memory_warning": 60.0,
                "memory_critical": 85.0
            }
        }
        self.monitor = SystemMonitor(self.config)

    def tearDown(self):
        """测试清理"""
        if self.monitor.status == MonitorStatus.RUNNING:
            self.monitor.stop_monitoring()

    def test_monitor_initialization(self):
        """测试监控器初始化"""
        self.assertEqual(self.monitor.status, MonitorStatus.STOPPED)
        self.assertEqual(len(self.monitor.metrics_history), 0)
        self.assertEqual(len(self.monitor.service_statuses), 0)
        self.assertEqual(len(self.monitor.alerts), 0)

    def test_start_stop_monitoring(self):
        """测试启动和停止监控"""
        # 启动监控
        result = self.monitor.start_monitoring()
        self.assertTrue(result)
        self.assertEqual(self.monitor.status, MonitorStatus.RUNNING)

        # 等待一些数据收集
        time.sleep(0.3)

        # 停止监控
        result = self.monitor.stop_monitoring()
        self.assertTrue(result)
        self.assertEqual(self.monitor.status, MonitorStatus.STOPPED)

    def test_collect_system_metrics(self):
        """测试系统指标收集"""
        metrics = self.monitor._collect_system_metrics()

        self.assertIsInstance(metrics, SystemMetrics)
        self.assertIsInstance(metrics.timestamp, datetime)
        self.assertGreaterEqual(metrics.cpu_percent, 0)
        self.assertLessEqual(metrics.cpu_percent, 100)
        self.assertGreater(metrics.cpu_count, 0)
        self.assertGreaterEqual(metrics.memory_percent, 0)
        self.assertLessEqual(metrics.memory_percent, 100)
        self.assertGreater(metrics.memory_total, 0)

    def test_threshold_checking(self):
        """测试阈值检查"""
        # 创建高CPU使用率的指标
        metrics = SystemMetrics(
            cpu_percent=90.0,  # 超过临界阈值
            memory_percent=70.0  # 超过警告阈值
        )

        # 重置告警
        self.monitor.alerts.clear()

        # 检查阈值
        self.monitor._check_thresholds(metrics)

        # 验证告警
        self.assertGreater(len(self.monitor.alerts), 0)

        # 检查是否有CPU临界告警
        cpu_alerts = [a for a in self.monitor.alerts if "CPU" in a.message]
        self.assertGreater(len(cpu_alerts), 0)
        self.assertEqual(cpu_alerts[0].level, AlertLevel.CRITICAL)

    def test_get_current_metrics(self):
        """测试获取当前指标"""
        # 启动监控
        self.monitor.start_monitoring()

        # 等待监控启动并最多等待2秒来获取数据
        max_wait = 2.0
        wait_interval = 0.1
        total_wait = 0

        metrics = self.monitor.get_current_metrics()
        while metrics is None and total_wait < max_wait:
            time.sleep(wait_interval)
            total_wait += wait_interval
            metrics = self.monitor.get_current_metrics()

        self.assertIsNotNone(metrics)
        self.assertIsInstance(metrics, SystemMetrics)

        self.monitor.stop_monitoring()

    def test_get_metrics_history(self):
        """测试获取指标历史"""
        # 启动监控
        self.monitor.start_monitoring()

        # 等待监控启动并最多等待2秒来获取历史数据
        max_wait = 2.0
        wait_interval = 0.1
        total_wait = 0

        history = self.monitor.get_metrics_history(minutes=5)
        while len(history) == 0 and total_wait < max_wait:
            time.sleep(wait_interval)
            total_wait += wait_interval
            history = self.monitor.get_metrics_history(minutes=5)

        self.assertGreater(len(history), 0)
        self.assertIsInstance(history[0], SystemMetrics)

        self.monitor.stop_monitoring()

    def test_alert_callbacks(self):
        """测试告警回调"""
        callback_called = False
        alert_received = None

        def test_callback(alert):
            nonlocal callback_called, alert_received
            callback_called = True
            alert_received = alert

        self.monitor.add_alert_callback(test_callback)

        # 创建告警
        self.monitor._create_alert(
            AlertLevel.WARNING,
            "Test alert",
            "test_source"
        )

        self.assertTrue(callback_called)
        self.assertIsNotNone(alert_received)
        self.assertEqual(alert_received.level, AlertLevel.WARNING)
        self.assertEqual(alert_received.message, "Test alert")

    def test_export_monitor_data(self):
        """测试监控数据导出"""
        # 启动监控并等待数据
        self.monitor.start_monitoring()
        time.sleep(0.2)

        # JSON导出
        json_data = self.monitor.export_monitor_data("json")
        self.assertIsInstance(json_data, str)
        self.assertIn("monitor_summary", json_data)

        # CSV导出
        csv_data = self.monitor.export_monitor_data("csv")
        self.assertIsInstance(csv_data, str)
        self.assertIn("timestamp", csv_data)

        self.monitor.stop_monitoring()


class TestLogManager(unittest.TestCase):
    """日志管理器测试"""

    def setUp(self):
        """测试设置"""
        self.temp_dir = tempfile.mkdtemp()
        self.config = {
            "max_memory_entries": 100,
            "log_dir": self.temp_dir,
            "real_time_mode": False,  # 禁用实时模式以便测试
            "rotation": {"enabled": False}  # 禁用轮转以便测试
        }
        self.log_manager = LogManager(self.config)

    def tearDown(self):
        """测试清理"""
        self.log_manager.shutdown()
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_log_manager_initialization(self):
        """测试日志管理器初始化"""
        self.assertIsNotNone(self.log_manager.collectors)
        self.assertEqual(len(self.log_manager.log_entries), 0)

    def test_add_log_entry(self):
        """测试添加日志条目"""
        entry = LogEntry(
            timestamp=datetime.now(),
            level=LogLevel.INFO,
            category=LogCategory.SYSTEM,
            component="test_component",
            message="Test message"
        )

        self.log_manager.add_log_entry(entry)
        self.assertEqual(len(self.log_manager.log_entries), 1)
        self.assertEqual(self.log_manager.log_entries[0], entry)

    def test_log_methods(self):
        """测试日志记录方法"""
        # 测试各个级别
        self.log_manager.debug(LogCategory.SYSTEM, "test", "Debug message")
        self.log_manager.info(LogCategory.SYSTEM, "test", "Info message")
        self.log_manager.warning(LogCategory.SYSTEM, "test", "Warning message")
        self.log_manager.error(LogCategory.SYSTEM, "test", "Error message")
        self.log_manager.critical(LogCategory.SYSTEM, "test", "Critical message")

        self.assertEqual(len(self.log_manager.log_entries), 5)

        # 验证级别
        levels = [log.level for log in self.log_manager.log_entries]
        expected_levels = [LogLevel.DEBUG, LogLevel.INFO, LogLevel.WARNING, LogLevel.ERROR, LogLevel.CRITICAL]
        self.assertEqual(levels, expected_levels)

    def test_collect_logs_with_filter(self):
        """测试带过滤器的日志收集"""
        # 添加不同级别的日志
        self.log_manager.info(LogCategory.SYSTEM, "comp1", "Info message")
        self.log_manager.error(LogCategory.SYSTEM, "comp1", "Error message")
        self.log_manager.warning(LogCategory.SERVICE, "comp2", "Warning message")

        # 按级别过滤
        error_filter = LogFilter(level_min=LogLevel.ERROR)
        error_logs = self.log_manager.collect_logs(error_filter)
        self.assertEqual(len(error_logs), 1)
        self.assertEqual(error_logs[0].level, LogLevel.ERROR)

        # 按分类过滤
        system_filter = LogFilter(categories=[LogCategory.SYSTEM])
        system_logs = self.log_manager.collect_logs(system_filter)
        self.assertEqual(len(system_logs), 2)

        # 按组件过滤
        comp1_filter = LogFilter(components=["comp1"])
        comp1_logs = self.log_manager.collect_logs(comp1_filter)
        self.assertEqual(len(comp1_logs), 2)

    def test_log_statistics(self):
        """测试日志统计"""
        # 添加测试日志
        self.log_manager.info(LogCategory.SYSTEM, "comp1", "Info message")
        self.log_manager.error(LogCategory.SYSTEM, "comp1", "Error message")
        self.log_manager.warning(LogCategory.SERVICE, "comp2", "Warning message")

        stats = self.log_manager.get_log_statistics()

        self.assertEqual(stats["total_logs"], 3)
        self.assertIn("by_level", stats)
        self.assertIn("by_category", stats)
        self.assertIn("by_component", stats)

        # 验证级别分布
        level_dist = stats["by_level"]
        self.assertEqual(level_dist.get("INFO"), 1)
        self.assertEqual(level_dist.get("ERROR"), 1)
        self.assertEqual(level_dist.get("WARNING"), 1)

    def test_export_logs(self):
        """测试日志导出"""
        # 添加测试日志
        self.log_manager.info(LogCategory.SYSTEM, "comp1", "Test message 1")
        self.log_manager.error(LogCategory.SYSTEM, "comp1", "Test message 2")

        # JSON导出
        json_data = self.log_manager.export_logs("json")
        self.assertIsInstance(json_data, str)
        parsed = json.loads(json_data)
        self.assertEqual(len(parsed), 2)

        # CSV导出
        csv_data = self.log_manager.export_logs("csv")
        self.assertIsInstance(csv_data, str)
        self.assertIn("timestamp", csv_data)
        self.assertIn("level", csv_data)

        # 文本导出
        txt_data = self.log_manager.export_logs("txt")
        self.assertIsInstance(txt_data, str)
        self.assertIn("Test message 1", txt_data)
        self.assertIn("Test message 2", txt_data)

    def test_cleanup_old_logs(self):
        """测试清理旧日志"""
        # 添加旧日志
        old_time = datetime.now() - timedelta(days=10)
        old_entry = LogEntry(
            timestamp=old_time,
            level=LogLevel.INFO,
            category=LogCategory.SYSTEM,
            component="test",
            message="Old message"
        )
        self.log_manager.add_log_entry(old_entry)

        # 添加新日志
        new_entry = LogEntry(
            timestamp=datetime.now(),
            level=LogLevel.INFO,
            category=LogCategory.SYSTEM,
            component="test",
            message="New message"
        )
        self.log_manager.add_log_entry(new_entry)

        self.assertEqual(len(self.log_manager.log_entries), 2)

        # 清理7天前的日志
        self.log_manager.cleanup_old_logs(days=7)

        # 验证只有新日志保留
        self.assertEqual(len(self.log_manager.log_entries), 1)
        self.assertEqual(self.log_manager.log_entries[0].message, "New message")


class TestLogAnalyzer(unittest.TestCase):
    """日志分析器测试"""

    def setUp(self):
        """测试设置"""
        self.temp_dir = tempfile.mkdtemp()
        self.log_manager = LogManager({
            "log_dir": self.temp_dir,
            "real_time_mode": False,
            "rotation": {"enabled": False}
        })
        self.analyzer = LogAnalyzer(self.log_manager)

        # 添加测试日志
        self._add_test_logs()

    def tearDown(self):
        """测试清理"""
        self.log_manager.shutdown()
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _add_test_logs(self):
        """添加测试日志"""
        test_logs = [
            LogEntry(
                timestamp=datetime.now() - timedelta(minutes=5),
                level=LogLevel.ERROR,
                category=LogCategory.SYSTEM,
                component="database",
                message="Connection failed to database server",
                details={"error_code": "DB_CONN_ERROR"}
            ),
            LogEntry(
                timestamp=datetime.now() - timedelta(minutes=4),
                level=LogLevel.ERROR,
                category=LogCategory.SYSTEM,
                component="database",
                message="Connection failed to database server",
                details={"error_code": "DB_CONN_ERROR"}
            ),
            LogEntry(
                timestamp=datetime.now() - timedelta(minutes=3),
                level=LogLevel.WARNING,
                category=LogCategory.SERVICE,
                component="api",
                message="Slow request detected",
                details={"response_time": 5.2}
            ),
            LogEntry(
                timestamp=datetime.now() - timedelta(minutes=2),
                level=LogLevel.INFO,
                category=LogCategory.USER,
                component="auth",
                message="User login successful",
                details={"user_id": "user123"}
            ),
            LogEntry(
                timestamp=datetime.now() - timedelta(minutes=1),
                level=LogLevel.CRITICAL,
                category=LogCategory.SYSTEM,
                component="system",
                message="Out of memory error",
                details={"memory_usage": "95%"}
            )
        ]

        for log in test_logs:
            self.log_manager.add_log_entry(log)

    def test_search_logs(self):
        """测试日志搜索"""
        # 搜索包含"connection"的日志
        results = self.analyzer.search_logs("connection")
        self.assertEqual(len(results), 2)

        # 搜索包含"user"的日志
        results = self.analyzer.search_logs("user")
        self.assertEqual(len(results), 1)

        # 搜索不存在的内容
        results = self.analyzer.search_logs("nonexistent")
        self.assertEqual(len(results), 0)

    def test_search_logs_with_regex(self):
        """测试正则表达式搜索"""
        # 搜索邮箱模式
        self.log_manager.add_log_entry(LogEntry(
            timestamp=datetime.now(),
            level=LogLevel.INFO,
            category=LogCategory.USER,
            component="auth",
            message="User user@example.com logged in"
        ))

        results = self.analyzer.search_logs(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', use_regex=True)
        self.assertEqual(len(results), 1)
        self.assertIn("user@example.com", results[0].message)

    def test_analyze_patterns(self):
        """测试模式分析"""
        result = self.analyzer.analyze_patterns()

        self.assertEqual(result.analysis_type, AnalysisType.PATTERN)
        self.assertIn("total_logs", result.summary)
        self.assertGreater(result.summary["total_logs"], 0)

        # 应该检测到一些模式
        if result.patterns:
            pattern = result.patterns[0]
            self.assertIsInstance(pattern, PatternMatch)
            self.assertGreater(pattern.count, 0)

    def test_analyze_trends(self):
        """测试趋势分析"""
        result = self.analyzer.analyze_trends()

        self.assertEqual(result.analysis_type, AnalysisType.TREND)
        self.assertIn("total_logs", result.summary)
        self.assertIn("time_buckets", result.summary)

        # 验证时间线数据
        if result.details:
            self.assertIn("timestamp", result.details[0])
            self.assertIn("total", result.details[0])

    def test_detect_anomalies(self):
        """测试异常检测"""
        result = self.analyzer.detect_anomalies()

        self.assertEqual(result.analysis_type, AnalysisType.ANOMALY)
        self.assertIn("total_logs", result.summary)
        self.assertIn("anomalies_found", result.summary)

    def test_get_statistics(self):
        """测试统计信息"""
        stats = self.analyzer.get_statistics()

        self.assertGreater(stats.total_entries, 0)
        self.assertIsInstance(stats.time_range, tuple)
        self.assertIsInstance(stats.level_distribution, dict)
        self.assertIsInstance(stats.category_distribution, dict)
        self.assertIsInstance(stats.component_distribution, dict)

    def test_export_analysis(self):
        """测试分析结果导出"""
        result = self.analyzer.analyze_patterns()

        # JSON导出
        json_data = self.analyzer.export_analysis(result, "json")
        self.assertIsInstance(json_data, str)
        parsed = json.loads(json_data)
        self.assertEqual(parsed["analysis_type"], "pattern")

        # 文本导出
        txt_data = self.analyzer.export_analysis(result, "txt")
        self.assertIsInstance(txt_data, str)
        self.assertIn("Analysis Type:", txt_data)


class TestLogExporter(unittest.TestCase):
    """日志导出器测试"""

    def setUp(self):
        """测试设置"""
        self.temp_dir = tempfile.mkdtemp()
        self.log_manager = LogManager({
            "log_dir": self.temp_dir,
            "real_time_mode": False,
            "rotation": {"enabled": False}
        })
        self.exporter = LogExporter(self.log_manager)

        # 添加测试日志
        self._add_test_logs()

    def tearDown(self):
        """测试清理"""
        self.log_manager.shutdown()
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _add_test_logs(self):
        """添加测试日志"""
        test_logs = [
            LogEntry(
                timestamp=datetime.now(),
                level=LogLevel.INFO,
                category=LogCategory.USER,
                component="auth",
                message="User user@example.com logged in from 192.168.1.1",
                user_id="user123",
                session_id="session456"
            ),
            LogEntry(
                timestamp=datetime.now(),
                level=LogLevel.ERROR,
                category=LogCategory.SYSTEM,
                component="database",
                message="Database connection failed for user admin@test.com",
                details={"error": "Connection timeout", "ip": "10.0.0.1"}
            ),
            LogEntry(
                timestamp=datetime.now(),
                level=LogLevel.WARNING,
                category=LogCategory.SECURITY,
                component="auth",
                message="Multiple failed login attempts for user@test.com",
                details={"attempts": 5, "ip": "192.168.1.100"}
            )
        ]

        for log in test_logs:
            self.log_manager.add_log_entry(log)

    def test_export_to_json(self):
        """测试JSON导出"""
        config = ExportConfig(format=ExportFormat.JSON, privacy_level=PrivacyLevel.NONE)
        data = self.exporter.export_logs(export_config=config)

        self.assertIsInstance(data, bytes)
        parsed = json.loads(data.decode('utf-8'))
        self.assertIn("logs", parsed)
        self.assertEqual(len(parsed["logs"]), 3)

    def test_export_to_csv(self):
        """测试CSV导出"""
        config = ExportConfig(format=ExportFormat.CSV, privacy_level=PrivacyLevel.NONE)
        data = self.exporter.export_logs(export_config=config)

        self.assertIsInstance(data, bytes)
        csv_text = data.decode('utf-8')
        self.assertIn("timestamp", csv_text)
        self.assertIn("level", csv_text)
        self.assertIn("message", csv_text)

    def test_export_to_txt(self):
        """测试文本导出"""
        config = ExportConfig(format=ExportFormat.TXT, privacy_level=PrivacyLevel.NONE)
        data = self.exporter.export_logs(export_config=config)

        self.assertIsInstance(data, bytes)
        txt_text = data.decode('utf-8')
        self.assertIn("LOG EXPORT", txt_text)
        self.assertIn("Total Entries: 3", txt_text)

    def test_privacy_filtering(self):
        """测试隐私过滤"""
        # 无过滤
        config_none = ExportConfig(format=ExportFormat.JSON, privacy_level=PrivacyLevel.NONE)
        data_none = self.exporter.export_logs(export_config=config_none)
        parsed_none = json.loads(data_none.decode('utf-8'))

        # 验证敏感信息存在
        messages = [log["message"] for log in parsed_none["logs"]]
        self.assertTrue(any("user@example.com" in msg for msg in messages))

        # 基本过滤
        config_basic = ExportConfig(format=ExportFormat.JSON, privacy_level=PrivacyLevel.BASIC)
        data_basic = self.exporter.export_logs(export_config=config_basic)
        parsed_basic = json.loads(data_basic.decode('utf-8'))

        # 验证敏感信息被过滤
        messages = [log["message"] for log in parsed_basic["logs"]]
        self.assertTrue(any("[EMAIL_REDACTED]" in msg for msg in messages))
        self.assertTrue(any("[IP_REDACTED]" in msg for msg in messages))

        # 严格过滤
        config_strict = ExportConfig(format=ExportFormat.JSON, privacy_level=PrivacyLevel.STRICT)
        data_strict = self.exporter.export_logs(export_config=config_strict)
        parsed_strict = json.loads(data_strict.decode('utf-8'))

        # 验证更多信息被过滤
        messages = [log["message"] for log in parsed_strict["logs"]]
        user_ids = [log.get("user_id") for log in parsed_strict["logs"]]
        self.assertTrue(any("[USER_ID_REDACTED]" in uid for uid in user_ids if uid))

    def test_export_package(self):
        """测试导出包创建"""
        package_data = self.exporter.create_export_package(
            formats=[ExportFormat.JSON, ExportFormat.CSV],
            privacy_level=PrivacyLevel.BASIC
        )

        self.assertIsInstance(package_data, bytes)
        self.assertGreater(len(package_data), 0)

        # 验证是有效的ZIP文件
        import zipfile
        import io

        with zipfile.ZipFile(io.BytesIO(package_data)) as zip_file:
            file_names = zip_file.namelist()
            self.assertIn("logs.json", file_names)
            self.assertIn("logs.csv", file_names)
            self.assertIn("README.txt", file_names)

    def test_validate_export_integrity(self):
        """测试导出完整性验证"""
        # 导出JSON数据
        config = ExportConfig(format=ExportFormat.JSON)
        data = self.exporter.export_logs(export_config=config)

        # 验证完整性
        result = self.exporter.validate_export_integrity(data, ExportFormat.JSON)

        self.assertTrue(result["valid"])
        self.assertIn("statistics", result)
        self.assertGreater(result["statistics"]["file_size_bytes"], 0)

    def test_custom_privacy_filter(self):
        """测试自定义隐私过滤器"""
        # 添加自定义过滤器
        self.exporter.add_custom_privacy_filter(
            PrivacyLevel.CUSTOM,
            "test_filter",
            r'\btest\d+\b',
            "[TEST_REDACTED]",
            "Test pattern filtering"
        )

        # 添加包含测试模式的日志
        self.log_manager.add_log_entry(LogEntry(
            timestamp=datetime.now(),
            level=LogLevel.INFO,
            category=LogCategory.SYSTEM,
            component="test",
            message="User test123 logged in"
        ))

        # 使用自定义过滤器导出
        config = ExportConfig(format=ExportFormat.JSON, privacy_level=PrivacyLevel.CUSTOM)
        data = self.exporter.export_logs(export_config=config)
        parsed = json.loads(data.decode('utf-8'))

        # 验证自定义过滤生效
        messages = [log["message"] for log in parsed["logs"]]
        self.assertTrue(any("[TEST_REDACTED]" in msg for msg in messages))

    def test_privacy_filter_summary(self):
        """测试隐私过滤器摘要"""
        summary = self.exporter.get_privacy_filter_summary(PrivacyLevel.BASIC)

        self.assertEqual(summary["privacy_level"], "basic")
        self.assertIn("filter_count", summary)
        self.assertIn("filters", summary)

        filter_names = [f["name"] for f in summary["filters"]]
        expected_filters = ["email_addresses", "ip_addresses", "phone_numbers"]
        for expected in expected_filters:
            self.assertIn(expected, filter_names)


class TestMonitoringDashboard(unittest.TestCase):
    """监控仪表板测试"""

    def setUp(self):
        """测试设置"""
        self.monitor = SystemMonitor({
            "monitor_interval": 0.1,
            "max_history_size": 10
        })
        self.dashboard = MonitoringDashboard(self.monitor)

    def tearDown(self):
        """测试清理"""
        if self.monitor.status == MonitorStatus.RUNNING:
            self.monitor.stop_monitoring()

    def test_dashboard_initialization(self):
        """测试仪表板初始化"""
        self.assertIsNotNone(self.dashboard.monitor)
        self.assertIsNotNone(self.dashboard.layout)
        self.assertFalse(self.dashboard.is_running)

    def test_get_status_color(self):
        """测试状态颜色获取"""
        # 测试各种状态颜色
        self.assertEqual(self.dashboard._get_status_color("running"), "green")
        self.assertEqual(self.dashboard._get_status_color("stopped"), "red")
        self.assertEqual(self.dashboard._get_status_color("error"), "red")

    def test_get_percentage_color(self):
        """测试百分比颜色获取"""
        self.assertEqual(self.dashboard._get_percentage_color(95), "red")
        self.assertEqual(self.dashboard._get_percentage_color(80), "yellow")
        self.assertEqual(self.dashboard._get_percentage_color(60), "cyan")
        self.assertEqual(self.dashboard._get_percentage_color(30), "green")

    def test_get_gauge_style(self):
        """测试仪表样式获取"""
        style = self.dashboard._get_gauge_style(95)
        self.assertEqual(style, "bar.back:red")

        style = self.dashboard._get_gauge_style(80)
        self.assertEqual(style, "bar.back:yellow")

        style = self.dashboard._get_gauge_style(40)
        self.assertEqual(style, "bar.back:green")

    def test_format_uptime(self):
        """测试运行时间格式化"""
        # 测试不同时间长度
        self.assertEqual(self.dashboard._format_uptime(3665), "1h 1m 5s")
        self.assertEqual(self.dashboard._format_uptime(125), "2m 5s")
        self.assertEqual(self.dashboard._format_uptime(30), "30s")
        self.assertEqual(self.dashboard._format_uptime(None), "N/A")

    @patch('rich.console.Console.print')
    def test_handle_user_input(self, mock_print):
        """测试用户输入处理"""
        self.dashboard.handle_user_input()

        # 验证print被调用
        self.assertTrue(mock_print.called)


if __name__ == '__main__':
    unittest.main()