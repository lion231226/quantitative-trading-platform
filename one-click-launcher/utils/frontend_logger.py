"""
前端服务专用日志记录器

提供前端启动、运行和错误处理的专门日志记录功能。
"""

import logging
import sys
import json
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict
import traceback

from utils.logger import get_logger


@dataclass
class FrontendLogEvent:
    """前端日志事件"""
    timestamp: str
    level: str
    component: str
    message: str
    details: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    stack_trace: Optional[str] = None


class FrontendLogger:
    """前端服务专用日志记录器"""

    def __init__(self, service_name: str = "frontend"):
        self.service_name = service_name
        self.logger = get_logger(f"{__name__}.{service_name}")
        self._setup_structured_logging()

    def _setup_structured_logging(self):
        """设置结构化日志记录"""
        # 创建专用的前端日志格式
        formatter = logging.Formatter(
            '%(asctime)s | %(name)s | %(levelname)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # 如果需要，可以添加文件处理器
        try:
            log_file = Path("logs/frontend.log")
            log_file.parent.mkdir(parents=True, exist_ok=True)

            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
        except Exception as e:
            self.logger.warning(f"Failed to setup file logging: {e}")

    def log_startup_start(self, config: Dict[str, Any]):
        """记录启动开始"""
        event = FrontendLogEvent(
            timestamp=datetime.now().isoformat(),
            level="INFO",
            component="startup",
            message=f"Starting {self.service_name} service",
            details={
                "host": config.get("host", "localhost"),
                "port": config.get("port", 3000),
                "frontend_dir": config.get("frontend_dir", "frontend"),
                "auto_open_browser": config.get("auto_open_browser", False)
            }
        )
        self._log_event(event)

    def log_startup_success(self, url: str, pid: Optional[int] = None, startup_time: Optional[float] = None):
        """记录启动成功"""
        details = {"url": url}
        if pid:
            details["pid"] = pid
        if startup_time:
            details["startup_time_seconds"] = startup_time

        event = FrontendLogEvent(
            timestamp=datetime.now().isoformat(),
            level="INFO",
            component="startup",
            message=f"{self.service_name} service started successfully",
            details=details
        )
        self._log_event(event)

    def log_startup_failure(self, error: Exception, startup_time: Optional[float] = None):
        """记录启动失败"""
        details = {}
        if startup_time:
            details["startup_time_seconds"] = startup_time

        event = FrontendLogEvent(
            timestamp=datetime.now().isoformat(),
            level="ERROR",
            component="startup",
            message=f"{self.service_name} service startup failed",
            details=details,
            error=str(error),
            stack_trace=traceback.format_exc()
        )
        self._log_event(event)

    def log_process_detected(self, processes: list):
        """记录进程检测结果"""
        event = FrontendLogEvent(
            timestamp=datetime.now().isoformat(),
            level="INFO",
            component="process_detection",
            message=f"Detected {len(processes)} Node.js processes",
            details={"process_count": len(processes), "processes": processes}
        )
        self._log_event(event)

    def log_service_stopped(self, shutdown_time: Optional[float] = None):
        """记录服务停止"""
        details = {}
        if shutdown_time:
            details["shutdown_time_seconds"] = shutdown_time

        event = FrontendLogEvent(
            timestamp=datetime.now().isoformat(),
            level="INFO",
            component="shutdown",
            message=f"{self.service_name} service stopped",
            details=details
        )
        self._log_event(event)

    def log_health_check(self, status: str, response_time: Optional[float] = None, error: Optional[str] = None):
        """记录健康检查结果"""
        details = {"status": status}
        if response_time:
            details["response_time_ms"] = round(response_time * 1000, 2)
        if error:
            details["error"] = error

        level = "INFO" if status == "healthy" else "WARNING"
        event = FrontendLogEvent(
            timestamp=datetime.now().isoformat(),
            level=level,
            component="health_check",
            message=f"Health check: {status}",
            details=details
        )
        self._log_event(event)

    def log_browser_opened(self, url: str, success: bool = True, error: Optional[str] = None):
        """记录浏览器打开结果"""
        details = {"url": url, "success": success}
        if error:
            details["error"] = error

        level = "INFO" if success else "WARNING"
        message = f"Browser opened: {url}" if success else f"Failed to open browser: {url}"

        event = FrontendLogEvent(
            timestamp=datetime.now().isoformat(),
            level=level,
            component="browser",
            message=message,
            details=details
        )
        self._log_event(event)

    def log_dependency_check(self, dependency_type: str, status: str, details: Optional[Dict[str, Any]] = None):
        """记录依赖检查结果"""
        event = FrontendLogEvent(
            timestamp=datetime.now().isoformat(),
            level="INFO" if status == "passed" else "ERROR",
            component="dependency_check",
            message=f"Dependency check [{dependency_type}]: {status}",
            details=details or {"type": dependency_type, "status": status}
        )
        self._log_event(event)

    def log_configuration_loaded(self, config_path: str, config_count: int):
        """记录配置加载结果"""
        event = FrontendLogEvent(
            timestamp=datetime.now().isoformat(),
            level="INFO",
            component="configuration",
            message=f"Configuration loaded from {config_path}",
            details={"config_path": config_path, "config_items_count": config_count}
        )
        self._log_event(event)

    def log_timeout_event(self, operation: str, timeout_seconds: int):
        """记录超时事件"""
        event = FrontendLogEvent(
            timestamp=datetime.now().isoformat(),
            level="ERROR",
            component="timeout",
            message=f"Operation '{operation}' timed out after {timeout_seconds} seconds",
            details={"operation": operation, "timeout_seconds": timeout_seconds}
        )
        self._log_event(event)

    def log_retry_attempt(self, operation: str, attempt: int, max_attempts: int, error: Optional[str] = None):
        """记录重试尝试"""
        details = {"operation": operation, "attempt": attempt, "max_attempts": max_attempts}
        if error:
            details["error"] = error

        event = FrontendLogEvent(
            timestamp=datetime.now().isoformat(),
            level="INFO",
            component="retry",
            message=f"Retry attempt {attempt}/{max_attempts} for {operation}",
            details=details
        )
        self._log_event(event)

    def _log_event(self, event: FrontendLogEvent):
        """记录日志事件"""
        # 将事件转换为JSON格式用于结构化日志
        log_data = asdict(event)

        # 记录到标准日志
        log_level = getattr(logging, event.level.upper(), logging.INFO)
        self.logger.log(log_level, json.dumps(log_data, indent=2))

    def debug(self, message: str, details: Optional[Dict[str, Any]] = None):
        """记录调试信息"""
        event = FrontendLogEvent(
            timestamp=datetime.now().isoformat(),
            level="DEBUG",
            component="general",
            message=message,
            details=details
        )
        self._log_event(event)

    def info(self, message: str, details: Optional[Dict[str, Any]] = None):
        """记录信息"""
        event = FrontendLogEvent(
            timestamp=datetime.now().isoformat(),
            level="INFO",
            component="general",
            message=message,
            details=details
        )
        self._log_event(event)

    def warning(self, message: str, details: Optional[Dict[str, Any]] = None):
        """记录警告"""
        event = FrontendLogEvent(
            timestamp=datetime.now().isoformat(),
            level="WARNING",
            component="general",
            message=message,
            details=details
        )
        self._log_event(event)

    def error(self, message: str, error: Optional[Exception] = None, details: Optional[Dict[str, Any]] = None):
        """记录错误"""
        event = FrontendLogEvent(
            timestamp=datetime.now().isoformat(),
            level="ERROR",
            component="general",
            message=message,
            details=details,
            error=str(error) if error else None,
            stack_trace=traceback.format_exc() if error else None
        )
        self._log_event(event)


# 全局前端日志记录器实例
_frontend_logger = None


def get_frontend_logger(service_name: str = "frontend") -> FrontendLogger:
    """获取前端日志记录器实例"""
    global _frontend_logger
    if _frontend_logger is None:
        _frontend_logger = FrontendLogger(service_name)
    return _frontend_logger