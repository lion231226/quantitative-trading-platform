"""
Structured Logging Configuration
Comprehensive logging setup with structlog and Sentry integration
"""

import os
import sys
import json
import logging
import logging.handlers
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path

import structlog
from structlog.stdlib import LoggerFactory

from .sentry_config import sentry_config


class SensitiveDataFilter:
    """Filter for removing sensitive data from logs"""

    SENSITIVE_FIELDS = {
        'password', 'passwd', 'secret', 'token', 'key', 'auth', 'credential',
        'session', 'cookie', 'authorization', 'bearer', 'api_key',
        'access_token', 'refresh_token', 'private_key', 'passphrase'
    }

    SENSITIVE_PATTERNS = [
        r'password[:=]\s*["\']?[\w\-@#$%^&*+]{8,}["\']?',
        r'token[:=]\s*["\']?[\w\-\.]{20,}["\']?',
        r'key[:=]\s*["\']?[A-Za-z0-9+/]{32,}["\']?',
        r'bearer\s+[A-Za-z0-9\-._~+\/]+=*',
        r'basic\s+[A-Za-z0-9+/=]+',
    ]

    def __init__(self):
        import re
        self.patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.SENSITIVE_PATTERNS]

    def sanitize_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize dictionary by removing sensitive fields"""
        if not isinstance(data, dict):
            return data

        sanitized = {}
        for key, value in data.items():
            # Check if key is sensitive
            if key.lower() in self.SENSITIVE_FIELDS:
                sanitized[key] = "[REDACTED]"
            elif isinstance(value, str):
                # Check if value contains sensitive patterns
                if any(pattern.search(value) for pattern in self.patterns):
                    sanitized[key] = "[REDACTED]"
                else:
                    sanitized[key] = value
            elif isinstance(value, dict):
                sanitized[key] = self.sanitize_dict(value)
            elif isinstance(value, list):
                sanitized[key] = [self.sanitize_dict(item) if isinstance(item, dict) else item for item in value]
            else:
                sanitized[key] = value

        return sanitized

    def sanitize_string(self, text: str) -> str:
        """Sanitize string by removing sensitive patterns"""
        for pattern in self.patterns:
            text = pattern.sub("[REDACTED]", text)
        return text


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging"""

    def __init__(self, sensitive_filter: SensitiveDataFilter = None):
        super().__init__()
        self.sensitive_filter = sensitive_filter or SensitiveDataFilter()

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add thread and process information
        log_entry.update({
            "thread_id": record.thread,
            "thread_name": record.threadName,
            "process_id": record.process,
        })

        # Add service information
        log_entry.update({
            "service": "quant-trading-backend",
            "version": os.getenv("APP_VERSION", "0.1.0"),
            "environment": os.getenv("NODE_ENV", "development"),
            "hostname": os.getenv("HOSTNAME", "unknown"),
        })

        # Add exception information if present
        if record.exc_info:
            log_entry["error_type"] = record.exc_info[0].__name__
            log_entry["error_message"] = str(record.exc_info[1])
            log_entry["stack_trace"] = self.formatException(record.exc_info)

        # Add custom fields from record
        if hasattr(record, "trace_id"):
            log_entry["trace_id"] = record.trace_id
        if hasattr(record, "span_id"):
            log_entry["span_id"] = record.span_id
        if hasattr(record, "user_id"):
            log_entry["user_id"] = record.user_id
        if hasattr(record, "request_id"):
            log_entry["request_id"] = record.request_id
        if hasattr(record, "operation"):
            log_entry["operation"] = record.operation
        if hasattr(record, "duration"):
            log_entry["duration"] = record.duration

        # Add extra fields
        extra_fields = {}
        for key, value in record.__dict__.items():
            if key not in {
                'name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                'filename', 'module', 'lineno', 'funcName', 'created',
                'msecs', 'relativeCreated', 'thread', 'threadName',
                'processName', 'process', 'getMessage', 'exc_info',
                'exc_text', 'stack_info', 'trace_id', 'span_id',
                'user_id', 'request_id', 'operation', 'duration'
            }:
                extra_fields[key] = value

        if extra_fields:
            # Sanitize extra fields
            extra_fields = self.sensitive_filter.sanitize_dict(extra_fields)
            log_entry["metadata"] = extra_fields

        # Sanitize sensitive data
        log_entry = self.sensitive_filter.sanitize_dict(log_entry)

        return json.dumps(log_entry, ensure_ascii=False, default=str)


class LoggingManager:
    """Centralized logging management"""

    def __init__(self):
        self.sensitive_filter = SensitiveDataFilter()
        self.loggers = {}
        self.setup_logging()

    def setup_logging(self):
        """Setup comprehensive logging configuration"""
        # Configure structlog
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                self.sanitize_processor,
                structlog.processors.UnicodeDecoder(),
                structlog.processors.JSONRenderer()
            ],
            context_class=dict,
            logger_factory=LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )

        # Setup standard library logging
        self.setup_stdlib_logging()

    def sanitize_processor(self, logger, method_name: str, event_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Custom structlog processor for sensitive data sanitization"""
        return self.sensitive_filter.sanitize_dict(event_dict)

    def setup_stdlib_logging(self):
        """Setup standard library logging configuration"""
        # Get log level from environment
        log_level = os.getenv("LOG_LEVEL", "INFO").upper()
        numeric_level = getattr(logging, log_level, logging.INFO)

        # Root logger configuration
        root_logger = logging.getLogger()
        root_logger.setLevel(numeric_level)

        # Clear existing handlers
        root_logger.handlers.clear()

        # Console handler
        if os.getenv("CONSOLE_LOGGING", "true").lower() == "true":
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(numeric_level)

            if os.getenv("STRUCTURED_LOGGING", "true").lower() == "true":
                console_handler.setFormatter(JSONFormatter(self.sensitive_filter))
            else:
                console_formatter = logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                )
                console_handler.setFormatter(console_formatter)

            root_logger.addHandler(console_handler)

        # File handler
        log_file = os.getenv("LOG_FILE")
        if log_file:
            # Create log directory if it doesn't exist
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)

            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=int(os.getenv("LOG_FILE_MAX_SIZE", "10")) * 1024 * 1024,  # 10MB
                backupCount=int(os.getenv("LOG_FILE_BACKUP_COUNT", "5"))
            )
            file_handler.setLevel(numeric_level)
            file_handler.setFormatter(JSONFormatter(self.sensitive_filter))
            root_logger.addHandler(file_handler)

        # Disable noisy loggers
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
        logging.getLogger("uvicorn.error").setLevel(logging.ERROR)
        logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    def get_logger(self, name: str) -> structlog.stdlib.BoundLogger:
        """Get structured logger for a specific module"""
        if name not in self.loggers:
            self.loggers[name] = structlog.get_logger(name)
        return self.loggers[name]

    def log_request(self, method: str, url: str, status_code: int, duration: float,
                   trace_id: str = None, user_id: str = None, **kwargs):
        """Log HTTP request"""
        logger = self.get_logger("http.request")
        logger.info(
            "HTTP request completed",
            method=method,
            url=url,
            status_code=status_code,
            duration=duration,
            trace_id=trace_id,
            user_id=user_id,
            **kwargs
        )

    def log_database_operation(self, operation: str, table: str, duration: float,
                              trace_id: str = None, **kwargs):
        """Log database operation"""
        logger = self.get_logger("database.operation")
        logger.info(
            "Database operation completed",
            operation=operation,
            table=table,
            duration=duration,
            trace_id=trace_id,
            **kwargs
        )

    def log_strategy_calculation(self, strategy_name: str, data_points: int,
                               duration: float, success: bool = True,
                               trace_id: str = None, user_id: str = None, **kwargs):
        """Log strategy calculation"""
        logger = self.get_logger("strategy.calculation")
        log_level = "info" if success else "error"
        getattr(logger, log_level)(
            "Strategy calculation completed",
            strategy_name=strategy_name,
            data_points=data_points,
            duration=duration,
            success=success,
            trace_id=trace_id,
            user_id=user_id,
            **kwargs
        )

    def log_security_event(self, event_type: str, user_id: str = None,
                         ip_address: str = None, user_agent: str = None,
                         success: bool = True, **kwargs):
        """Log security event"""
        logger = self.get_logger("security.event")
        log_level = "info" if success else "warning"
        getattr(logger, log_level)(
            "Security event recorded",
            event_type=event_type,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            success=success,
            **kwargs
        )

    def log_performance_metric(self, metric_name: str, value: float,
                             unit: str = "milliseconds", trace_id: str = None,
                             **kwargs):
        """Log performance metric"""
        logger = self.get_logger("performance.metric")
        logger.info(
            "Performance metric recorded",
            metric_name=metric_name,
            value=value,
            unit=unit,
            trace_id=trace_id,
            **kwargs
        )

    def log_external_api_call(self, service: str, endpoint: str, method: str,
                            status_code: int, duration: float,
                            trace_id: str = None, **kwargs):
        """Log external API call"""
        logger = self.get_logger("external.api")
        success = 200 <= status_code < 400
        log_level = "info" if success else "error"

        getattr(logger, log_level)(
            "External API call completed",
            service=service,
            endpoint=endpoint,
            method=method,
            status_code=status_code,
            duration=duration,
            trace_id=trace_id,
            **kwargs
        )

    def log_user_action(self, action: str, resource: str, user_id: str = None,
                       success: bool = True, trace_id: str = None, **kwargs):
        """Log user action"""
        logger = self.get_logger("user.action")
        log_level = "info" if success else "error"

        getattr(logger, log_level)(
            "User action recorded",
            action=action,
            resource=resource,
            user_id=user_id,
            success=success,
            trace_id=trace_id,
            **kwargs
        )

    def log_system_event(self, event_type: str, component: str,
                       severity: str = "info", **kwargs):
        """Log system event"""
        logger = self.get_logger("system.event")
        log_method = getattr(logger, severity.lower(), logger.info)
        log_method(
            "System event recorded",
            event_type=event_type,
            component=component,
            severity=severity,
            **kwargs
        )


# Global logging manager instance
logging_manager = LoggingManager()

# Convenience functions
def get_logger(name: str = None) -> structlog.stdlib.BoundLogger:
    """Get logger instance"""
    return logging_manager.get_logger(name or __name__)

def configure_request_logging(request):
    """Configure logging for current request"""
    trace_context = getattr(request.state, 'trace_context', None)
    if trace_context:
        structlog.contextvars.bind_contextvars(
            trace_id=trace_context.trace_id,
            span_id=trace_context.span_id,
        )

# Logging context manager for operations
from contextlib import contextmanager

@contextmanager
def log_operation(operation_name: str, logger: str = None, **kwargs):
    """Context manager for logging operations"""
    operation_logger = get_logger(logger or "operation")
    start_time = datetime.utcnow()

    operation_logger.info(
        f"Operation started: {operation_name}",
        operation=operation_name,
        start_time=start_time.isoformat(),
        **kwargs
    )

    try:
        yield operation_logger
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds() * 1000

        operation_logger.info(
            f"Operation completed: {operation_name}",
            operation=operation_name,
            end_time=end_time.isoformat(),
            duration=duration,
            success=True,
            **kwargs
        )
    except Exception as e:
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds() * 1000

        operation_logger.error(
            f"Operation failed: {operation_name}",
            operation=operation_name,
            end_time=end_time.isoformat(),
            duration=duration,
            success=False,
            error_type=type(e).__name__,
            error_message=str(e),
            **kwargs
        )
        raise