"""
Log Manager Module

This module provides comprehensive log management functionality including
structured logging, collection, rotation, and analysis.
"""

import json
import logging
import logging.handlers
import time
import threading
import gzip
import shutil
from typing import Dict, List, Optional, Any, Union, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
import re
import os

from utils.logger import get_logger, setup_logger


class LogLevel(Enum):
    """日志级别"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogCategory(Enum):
    """日志分类"""
    SYSTEM = "system"
    SERVICE = "service"
    MONITORING = "monitoring"
    USER = "user"
    ERROR = "error"
    PERFORMANCE = "performance"
    SECURITY = "security"
    AUDIT = "audit"
    DEBUG = "debug"


@dataclass
class LogEntry:
    """日志条目"""
    timestamp: datetime
    level: LogLevel
    category: LogCategory
    component: str
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    exception_info: Optional[str] = None
    stack_trace: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        data['level'] = self.level.value
        data['category'] = self.category.value
        return data

    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LogEntry':
        """从字典创建日志条目"""
        if isinstance(data.get('timestamp'), str):
            data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        if isinstance(data.get('level'), str):
            data['level'] = LogLevel(data['level'])
        if isinstance(data.get('category'), str):
            data['category'] = LogCategory(data['category'])
        return cls(**data)


@dataclass
class LogFilter:
    """日志过滤器"""
    level_min: Optional[LogLevel] = None
    level_max: Optional[LogLevel] = None
    categories: Optional[List[LogCategory]] = None
    components: Optional[List[str]] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    keywords: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None


class StructuredLogHandler(logging.Handler):
    """结构化日志处理器"""

    def __init__(self, log_manager: 'LogManager'):
        super().__init__()
        self.log_manager = log_manager

    def emit(self, record: logging.LogRecord):
        """发出日志记录"""
        try:
            # 确定日志级别
            level = LogLevel(record.levelname)

            # 确定日志分类
            category = self._determine_category(record)

            # 提取组件名称
            component = getattr(record, 'component', record.name)

            # 提取额外信息
            details = {}
            for key, value in record.__dict__.items():
                if key not in ['name', 'msg', 'args', 'levelname', 'levelno',
                              'pathname', 'filename', 'module', 'lineno',
                              'funcName', 'created', 'msecs', 'relativeCreated',
                              'thread', 'threadName', 'processName', 'process']:
                    details[key] = value

            # 提取用户信息
            user_id = getattr(record, 'user_id', None)
            session_id = getattr(record, 'session_id', None)
            request_id = getattr(record, 'request_id', None)

            # 提取标签
            tags = getattr(record, 'tags', [])
            if isinstance(tags, str):
                tags = [tags]

            # 提取异常信息
            exception_info = None
            stack_trace = None
            if record.exc_info:
                exception_info = str(record.exc_info[1])
                stack_trace = self.format(record)

            # 创建日志条目
            log_entry = LogEntry(
                timestamp=datetime.fromtimestamp(record.created),
                level=level,
                category=category,
                component=component,
                message=record.getMessage(),
                details=details,
                user_id=user_id,
                session_id=session_id,
                request_id=request_id,
                tags=tags,
                exception_info=exception_info,
                stack_trace=stack_trace
            )

            # 添加到日志管理器
            self.log_manager.add_log_entry(log_entry)

        except Exception as e:
            # 避免日志处理本身出现错误导致递归
            print(f"Error in StructuredLogHandler: {e}")

    def _determine_category(self, record: logging.LogRecord) -> LogCategory:
        """确定日志分类"""
        # 根据模块名和消息内容确定分类
        module_name = record.module.lower()
        message = record.getMessage().lower()

        if 'monitor' in module_name or 'monitor' in message:
            return LogCategory.MONITORING
        elif 'service' in module_name or 'service' in message:
            return LogCategory.SERVICE
        elif 'user' in message or 'auth' in message:
            return LogCategory.USER
        elif 'error' in message or 'fail' in message or 'exception' in message:
            return LogCategory.ERROR
        elif 'performance' in message or 'slow' in message or 'timeout' in message:
            return LogCategory.PERFORMANCE
        elif 'security' in message or 'auth' in message or 'permission' in message:
            return LogCategory.SECURITY
        elif 'audit' in message or 'access' in message:
            return LogCategory.AUDIT
        elif record.levelname in ['DEBUG']:
            return LogCategory.DEBUG
        else:
            return LogCategory.SYSTEM


class LogManager:
    """
    日志管理器，提供结构化日志收集、存储、轮转和分析功能
    """

    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化日志管理器

        Args:
            config: 日志管理配置
        """
        self.logger = get_logger(self.__class__.__name__)

        # 配置
        self.config = config or self._get_default_config()

        # 日志存储
        self.log_entries: List[LogEntry] = []
        self.max_memory_entries = self.config.get("max_memory_entries", 10000)

        # 文件存储
        self.log_dir = Path(self.config.get("log_dir", "logs"))
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # 轮转配置
        self.rotation_config = self.config.get("rotation", {})
        self.compression_enabled = self.rotation_config.get("compression", True)

        # 线程锁
        self._lock = threading.RLock()

        # 日志收集器
        self.collectors: Dict[str, logging.Logger] = {}

        # 回调函数
        self.callbacks: List[Callable[[LogEntry], None]] = []

        # 初始化文件日志记录器
        self._setup_file_loggers()

        # 启动后台线程
        self._start_background_threads()

        self.logger.info("Log Manager initialized")

    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "max_memory_entries": 10000,
            "log_dir": "logs",
            "file_format": "json",  # json, text
            "rotation": {
                "enabled": True,
                "max_size_mb": 100,
                "max_files": 10,
                "compression": True,
                "check_interval": 300  # 5分钟
            },
            "categories": {
                "system": {"file": "system.log", "level": "INFO"},
                "service": {"file": "service.log", "level": "INFO"},
                "monitoring": {"file": "monitoring.log", "level": "DEBUG"},
                "user": {"file": "user.log", "level": "INFO"},
                "error": {"file": "error.log", "level": "ERROR"},
                "performance": {"file": "performance.log", "level": "INFO"},
                "security": {"file": "security.log", "level": "WARNING"},
                "audit": {"file": "audit.log", "level": "INFO"}
            },
            "real_time_mode": True,
            "buffer_size": 100,
            "flush_interval": 10  # 秒
        }

    def _setup_file_loggers(self):
        """设置文件日志记录器"""
        categories_config = self.config.get("categories", {})

        for category_name, category_config in categories_config.items():
            try:
                # 获取日志级别
                level_str = category_config.get("level", "INFO")
                log_level = getattr(logging, level_str)

                # 创建日志记录器
                logger_name = f"structured_{category_name}"
                logger = setup_logger(
                    name=logger_name,
                    log_level=level_str,
                    log_file=str(self.log_dir / category_config.get("file", f"{category_name}.log")),
                    console_output=False
                )

                # 添加结构化处理器
                structured_handler = StructuredLogHandler(self)
                logger.addHandler(structured_handler)

                self.collectors[category_name] = logger

            except Exception as e:
                self.logger.error(f"Error setting up logger for category {category_name}: {e}")

    def _start_background_threads(self):
        """启动后台线程"""
        # 启动日志刷新线程
        if self.config.get("real_time_mode", True):
            self.flush_thread = threading.Thread(
                target=self._flush_loop,
                name="LogFlusher",
                daemon=True
            )
            self.flush_thread.start()

        # 启动日志轮转线程
        if self.rotation_config.get("enabled", True):
            self.rotation_thread = threading.Thread(
                target=self._rotation_loop,
                name="LogRotator",
                daemon=True
            )
            self.rotation_thread.start()

    def _flush_loop(self):
        """日志刷新循环"""
        flush_interval = self.config.get("flush_interval", 10)

        while True:
            try:
                time.sleep(flush_interval)
                self.flush_to_disk()
            except Exception as e:
                self.logger.error(f"Error in flush loop: {e}")

    def _rotation_loop(self):
        """日志轮转循环"""
        check_interval = self.rotation_config.get("check_interval", 300)

        while True:
            try:
                time.sleep(check_interval)
                self.rotate_logs()
            except Exception as e:
                self.logger.error(f"Error in rotation loop: {e}")

    def add_log_entry(self, log_entry: LogEntry):
        """
        添加日志条目

        Args:
            log_entry: 日志条目
        """
        with self._lock:
            # 添加到内存
            self.log_entries.append(log_entry)

            # 限制内存中的日志数量
            if len(self.log_entries) > self.max_memory_entries:
                # 移除最旧的日志
                self.log_entries = self.log_entries[-self.max_memory_entries:]

            # 调用回调函数
            for callback in self.callbacks:
                try:
                    callback(log_entry)
                except Exception as e:
                    self.logger.error(f"Error in log callback: {e}")

            # 实时模式：立即写入文件
            if self.config.get("real_time_mode", True):
                self._write_log_to_file(log_entry)

    def _write_log_to_file(self, log_entry: LogEntry):
        """写入日志到文件"""
        try:
            # 获取对应分类的日志记录器
            category_str = log_entry.category.value
            if category_str in self.collectors:
                logger = self.collectors[category_str]

                # 创建标准日志记录
                record = logging.LogRecord(
                    name=log_entry.component,
                    level=getattr(logging, log_entry.level.value),
                    pathname="",
                    lineno=0,
                    msg=log_entry.message,
                    args=(),
                    exc_info=None
                )

                # 添加额外属性
                record.component = log_entry.component
                record.category = log_entry.category.value
                record.user_id = log_entry.user_id
                record.session_id = log_entry.session_id
                record.request_id = log_entry.request_id
                record.tags = log_entry.tags
                record.details = log_entry.details

                logger.handle(record)

        except Exception as e:
            self.logger.error(f"Error writing log to file: {e}")

    def log(self, level: LogLevel, category: LogCategory, component: str,
            message: str, details: Dict[str, Any] = None, **kwargs):
        """
        记录日志

        Args:
            level: 日志级别
            category: 日志分类
            component: 组件名称
            message: 日志消息
            details: 详细信息
            **kwargs: 其他参数（user_id, session_id, tags等）
        """
        log_entry = LogEntry(
            timestamp=datetime.now(),
            level=level,
            category=category,
            component=component,
            message=message,
            details=details or {},
            **kwargs
        )

        self.add_log_entry(log_entry)

    def debug(self, category: LogCategory, component: str, message: str, **kwargs):
        """记录DEBUG级别日志"""
        self.log(LogLevel.DEBUG, category, component, message, **kwargs)

    def info(self, category: LogCategory, component: str, message: str, **kwargs):
        """记录INFO级别日志"""
        self.log(LogLevel.INFO, category, component, message, **kwargs)

    def warning(self, category: LogCategory, component: str, message: str, **kwargs):
        """记录WARNING级别日志"""
        self.log(LogLevel.WARNING, category, component, message, **kwargs)

    def error(self, category: LogCategory, component: str, message: str, **kwargs):
        """记录ERROR级别日志"""
        self.log(LogLevel.ERROR, category, component, message, **kwargs)

    def critical(self, category: LogCategory, component: str, message: str, **kwargs):
        """记录CRITICAL级别日志"""
        self.log(LogLevel.CRITICAL, category, component, message, **kwargs)

    def collect_logs(self, log_filter: LogFilter = None) -> List[LogEntry]:
        """
        收集日志

        Args:
            log_filter: 日志过滤器

        Returns:
            过滤后的日志列表
        """
        with self._lock:
            logs = self.log_entries.copy()

        # 应用过滤器
        if log_filter:
            logs = self._apply_filter(logs, log_filter)

        return logs

    def _apply_filter(self, logs: List[LogEntry], log_filter: LogFilter) -> List[LogEntry]:
        """应用日志过滤器"""
        filtered_logs = logs

        # 级别过滤
        if log_filter.level_min:
            level_values = {LogLevel.DEBUG: 10, LogLevel.INFO: 20, LogLevel.WARNING: 30,
                          LogLevel.ERROR: 40, LogLevel.CRITICAL: 50}
            min_value = level_values.get(log_filter.level_min, 0)
            filtered_logs = [log for log in filtered_logs
                           if level_values.get(log.level, 0) >= min_value]

        if log_filter.level_max:
            level_values = {LogLevel.DEBUG: 10, LogLevel.INFO: 20, LogLevel.WARNING: 30,
                          LogLevel.ERROR: 40, LogLevel.CRITICAL: 50}
            max_value = level_values.get(log_filter.level_max, 50)
            filtered_logs = [log for log in filtered_logs
                           if level_values.get(log.level, 0) <= max_value]

        # 分类过滤
        if log_filter.categories:
            filtered_logs = [log for log in filtered_logs
                           if log.category in log_filter.categories]

        # 组件过滤
        if log_filter.components:
            filtered_logs = [log for log in filtered_logs
                           if log.component in log_filter.components]

        # 时间过滤
        if log_filter.start_time:
            filtered_logs = [log for log in filtered_logs
                           if log.timestamp >= log_filter.start_time]

        if log_filter.end_time:
            filtered_logs = [log for log in filtered_logs
                           if log.timestamp <= log_filter.end_time]

        # 关键词过滤
        if log_filter.keywords:
            filtered_logs = [log for log in filtered_logs
                           if any(keyword.lower() in log.message.lower() or
                                keyword.lower() in str(log.details).lower()
                                for keyword in log_filter.keywords)]

        # 标签过滤
        if log_filter.tags:
            filtered_logs = [log for log in filtered_logs
                           if any(tag in log.tags for tag in log_filter.tags)]

        # 用户过滤
        if log_filter.user_id:
            filtered_logs = [log for log in filtered_logs
                           if log.user_id == log_filter.user_id]

        # 会话过滤
        if log_filter.session_id:
            filtered_logs = [log for log in filtered_logs
                           if log.session_id == log_filter.session_id]

        # 请求过滤
        if log_filter.request_id:
            filtered_logs = [log for log in filtered_logs
                           if log.request_id == log_filter.request_id]

        return filtered_logs

    def rotate_logs(self):
        """轮转日志文件"""
        if not self.rotation_config.get("enabled", True):
            return

        try:
            max_size_mb = self.rotation_config.get("max_size_mb", 100)
            max_files = self.rotation_config.get("max_files", 10)

            for category_name, logger in self.collectors.items():
                # 检查所有处理器
                for handler in logger.handlers:
                    if isinstance(handler, logging.handlers.RotatingFileHandler):
                        # 获取日志文件路径
                        log_file = Path(handler.baseFilename)

                        if log_file.exists() and log_file.stat().st_size > max_size_mb * 1024 * 1024:
                            # 执行轮转
                            handler.doRollover()

                            # 压缩旧文件
                            if self.compression_enabled:
                                self._compress_old_logs(log_file, max_files)

        except Exception as e:
            self.logger.error(f"Error rotating logs: {e}")

    def _compress_old_logs(self, log_file: Path, max_files: int):
        """压缩旧日志文件"""
        try:
            # 查找需要压缩的日志文件
            base_name = log_file.stem
            log_dir = log_file.parent

            # 查找所有备份文件
            backup_files = sorted(
                log_dir.glob(f"{base_name}.*"),
                key=lambda x: x.stat().st_mtime,
                reverse=True
            )

            # 保留最新的max_files个文件，压缩更旧的文件
            for i, backup_file in enumerate(backup_files[max_files:], 1):
                if not backup_file.name.endswith('.gz'):
                    # 压缩文件
                    compressed_file = backup_file.with_suffix(backup_file.suffix + '.gz')
                    with open(backup_file, 'rb') as f_in:
                        with gzip.open(compressed_file, 'wb') as f_out:
                            shutil.copyfileobj(f_in, f_out)
                    backup_file.unlink()

        except Exception as e:
            self.logger.error(f"Error compressing old logs: {e}")

    def flush_to_disk(self):
        """刷新日志到磁盘"""
        # 在实时模式下，日志已经实时写入，这里可以做一些额外的刷新操作
        pass

    def get_log_statistics(self) -> Dict[str, Any]:
        """获取日志统计信息"""
        with self._lock:
            total_logs = len(self.log_entries)

            if total_logs == 0:
                return {
                    "total_logs": 0,
                    "by_level": {},
                    "by_category": {},
                    "by_component": {},
                    "time_range": None
                }

            # 按级别统计
            by_level = {}
            for log in self.log_entries:
                level = log.level.value
                by_level[level] = by_level.get(level, 0) + 1

            # 按分类统计
            by_category = {}
            for log in self.log_entries:
                category = log.category.value
                by_category[category] = by_category.get(category, 0) + 1

            # 按组件统计
            by_component = {}
            for log in self.log_entries:
                component = log.component
                by_component[component] = by_component.get(component, 0) + 1

            # 时间范围
            timestamps = [log.timestamp for log in self.log_entries]
            time_range = {
                "start": min(timestamps).isoformat(),
                "end": max(timestamps).isoformat()
            }

            return {
                "total_logs": total_logs,
                "by_level": by_level,
                "by_category": by_category,
                "by_component": by_component,
                "time_range": time_range
            }

    def cleanup_old_logs(self, days: int = 30):
        """
        清理旧日志

        Args:
            days: 保留天数
        """
        cutoff_date = datetime.now() - timedelta(days=days)

        with self._lock:
            original_count = len(self.log_entries)
            self.log_entries = [log for log in self.log_entries if log.timestamp >= cutoff_date]
            removed_count = original_count - len(self.log_entries)

        if removed_count > 0:
            self.logger.info(f"Cleaned up {removed_count} old log entries")

    def add_callback(self, callback: Callable[[LogEntry], None]):
        """添加日志回调函数"""
        self.callbacks.append(callback)

    def remove_callback(self, callback: Callable[[LogEntry], None]):
        """移除日志回调函数"""
        if callback in self.callbacks:
            self.callbacks.remove(callback)

    def export_logs(self, format: str = "json", log_filter: LogFilter = None) -> str:
        """
        导出日志

        Args:
            format: 导出格式 (json, csv, txt)
            log_filter: 日志过滤器

        Returns:
            导出的日志字符串
        """
        logs = self.collect_logs(log_filter)

        if format.lower() == "json":
            return json.dumps([log.to_dict() for log in logs], indent=2, ensure_ascii=False)

        elif format.lower() == "csv":
            import csv
            import io

            output = io.StringIO()
            if logs:
                fieldnames = logs[0].to_dict().keys()
                writer = csv.DictWriter(output, fieldnames=fieldnames)
                writer.writeheader()
                for log in logs:
                    # 转换datetime为字符串
                    log_dict = log.to_dict()
                    writer.writerow(log_dict)
            return output.getvalue()

        elif format.lower() == "txt":
            lines = []
            for log in logs:
                line = f"{log.timestamp.isoformat()} [{log.level.value}] {log.category.value}:{log.component} - {log.message}"
                if log.details:
                    line += f" | Details: {log.details}"
                lines.append(line)
            return "\n".join(lines)

        else:
            raise ValueError(f"Unsupported export format: {format}")

    def shutdown(self):
        """关闭日志管理器"""
        self.logger.info("Shutting down log manager")

        # 刷新剩余日志
        self.flush_to_disk()

        # 关闭所有日志记录器
        for logger in self.collectors.values():
            for handler in logger.handlers:
                handler.close()
            logger.handlers.clear()

        self.collectors.clear()
        self.callbacks.clear()