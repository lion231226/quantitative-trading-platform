import logging
import structlog
import sys
from typing import Any, Dict
import json
from datetime import datetime

from app.core.config import settings

def setup_logging() -> None:
    """配置结构化日志"""

    # 配置标准库logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.LOG_LEVEL.upper()),
    )

    # 配置structlog处理器
    if settings.LOG_FORMAT.lower() == "json":
        # JSON格式日志（生产环境推荐）
        processors = [
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ]
    else:
        # 可读格式日志（开发环境推荐）
        processors = [
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            ConsoleRenderer()
        ]

    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

class ConsoleRenderer:
    """控制台日志渲染器"""

    def __call__(self, logger: Any, method_name: str, event_dict: Dict[str, Any]) -> str:
        """渲染日志消息"""

        # 获取时间戳
        timestamp = event_dict.get("timestamp", datetime.now().isoformat())

        # 获取日志级别
        level = event_dict.get("level", "INFO").upper()

        # 获取日志名称
        logger_name = event_dict.get("logger", "unknown")

        # 获取事件消息
        message = event_dict.get("event", "")

        # 获取异常信息
        exc_info = event_dict.get("exc_info")
        if exc_info:
            message += f" - {exc_info}"

        # 构建基础日志格式
        log_line = f"{timestamp} | {level:8} | {logger_name:20} | {message}"

        # 添加额外字段
        extra_fields = {k: v for k, v in event_dict.items()
                       if k not in ["timestamp", "level", "logger", "event", "exc_info"]}

        if extra_fields:
            extra_str = " | ".join([f"{k}={v}" for k, v in extra_fields.items()])
            log_line += f" | {extra_str}"

        return log_line

class APIRequestLogger:
    """API请求日志记录器"""

    def __init__(self):
        self.logger = structlog.get_logger("api_request")

    def log_request(self, method: str, path: str, user_id: str = None, **kwargs):
        """记录API请求"""
        self.logger.info(
            "API请求",
            method=method,
            path=path,
            user_id=user_id,
            **kwargs
        )

    def log_response(self, method: str, path: str, status_code: int,
                    duration: float = None, **kwargs):
        """记录API响应"""
        self.logger.info(
            "API响应",
            method=method,
            path=path,
            status_code=status_code,
            duration=duration,
            **kwargs
        )

    def log_error(self, method: str, path: str, error: str, **kwargs):
        """记录API错误"""
        self.logger.error(
            "API错误",
            method=method,
            path=path,
            error=error,
            **kwargs
        )

class StrategyLogger:
    """策略执行日志记录器"""

    def __init__(self):
        self.logger = structlog.get_logger("strategy")

    def log_strategy_start(self, strategy_id: str, symbol: str, **kwargs):
        """记录策略开始执行"""
        self.logger.info(
            "策略开始执行",
            strategy_id=strategy_id,
            symbol=symbol,
            **kwargs
        )

    def log_strategy_complete(self, strategy_id: str, execution_time: float, **kwargs):
        """记录策略执行完成"""
        self.logger.info(
            "策略执行完成",
            strategy_id=strategy_id,
            execution_time=execution_time,
            **kwargs
        )

    def log_strategy_error(self, strategy_id: str, error: str, **kwargs):
        """记录策略执行错误"""
        self.logger.error(
            "策略执行错误",
            strategy_id=strategy_id,
            error=error,
            **kwargs
        )

class DataLogger:
    """数据处理日志记录器"""

    def __init__(self):
        self.logger = structlog.get_logger("data")

    def log_data_fetch(self, symbol: str, source: str, count: int, **kwargs):
        """记录数据获取"""
        self.logger.info(
            "数据获取成功",
            symbol=symbol,
            source=source,
            count=count,
            **kwargs
        )

    def log_data_cache_hit(self, symbol: str, cache_key: str, **kwargs):
        """记录缓存命中"""
        self.logger.info(
            "数据缓存命中",
            symbol=symbol,
            cache_key=cache_key,
            **kwargs
        )

    def log_data_error(self, symbol: str, error: str, **kwargs):
        """记录数据获取错误"""
        self.logger.error(
            "数据获取失败",
            symbol=symbol,
            error=error,
            **kwargs
        )

class PerformanceLogger:
    """性能监控日志记录器"""

    def __init__(self):
        self.logger = structlog.get_logger("performance")

    def log_slow_query(self, query: str, duration: float, **kwargs):
        """记录慢查询"""
        self.logger.warning(
            "检测到慢查询",
            query=query,
            duration=duration,
            **kwargs
        )

    def log_memory_usage(self, component: str, memory_mb: float, **kwargs):
        """记录内存使用"""
        self.logger.info(
            "内存使用情况",
            component=component,
            memory_mb=memory_mb,
            **kwargs
        )

    def log_api_performance(self, endpoint: str, duration: float, **kwargs):
        """记录API性能"""
        level = "warning" if duration > 1.0 else "info"
        getattr(self.logger, level)(
            "API性能指标",
            endpoint=endpoint,
            duration=duration,
            **kwargs
        )

# 创建全局日志记录器实例
api_logger = APIRequestLogger()
strategy_logger = StrategyLogger()
data_logger = DataLogger()
performance_logger = PerformanceLogger()