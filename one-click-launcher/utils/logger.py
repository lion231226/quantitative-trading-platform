"""
日志工具模块

提供统一的日志配置和管理功能。
"""

import logging
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime
import logging.handlers


def setup_logger(
    name: str = "launcher",
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
    console_output: bool = True
) -> logging.Logger:
    """
    设置日志记录器

    Args:
        name: 日志记录器名称
        log_level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: 日志文件路径 (可选)
        max_bytes: 日志文件最大大小
        backup_count: 备份文件数量
        console_output: 是否输出到控制台

    Returns:
        配置好的日志记录器
    """
    # 创建日志记录器
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level.upper()))

    # 避免重复添加处理器
    if logger.handlers:
        return logger

    # 创建格式化器
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 控制台处理器
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    # 文件处理器
    if log_file:
        # 确保日志目录存在
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        # 使用轮转文件处理器
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    获取日志记录器实例

    Args:
        name: 日志记录器名称

    Returns:
        日志记录器实例
    """
    # 如果还没有设置过，使用默认配置
    logger = logging.getLogger(name)
    if not logger.handlers:
        return setup_logger(name)
    return logger


def set_log_level(logger: logging.Logger, level: str) -> None:
    """
    设置日志记录器级别

    Args:
        logger: 日志记录器实例
        level: 日志级别
    """
    logger.setLevel(getattr(logging, level.upper()))

    # 同时设置所有处理器的级别
    for handler in logger.handlers:
        handler.setLevel(getattr(logging, level.upper()))


class LoggerMixin:
    """日志记录器混入类"""

    @property
    def logger(self) -> logging.Logger:
        """获取当前类的日志记录器"""
        return get_logger(self.__class__.__name__)


# 创建默认的启动器日志记录器
launcher_logger = setup_logger("launcher")


def log_exception(logger: logging.Logger, message: str = "Exception occurred") -> None:
    """
    记录异常信息

    Args:
        logger: 日志记录器
        message: 附加消息
    """
    import traceback

    logger.error(f"{message}:\n{traceback.format_exc()}")


def log_function_call(logger: logging.Logger, func_name: str, args: tuple = (), kwargs: dict = None) -> None:
    """
    记录函数调用信息

    Args:
        logger: 日志记录器
        func_name: 函数名称
        args: 位置参数
        kwargs: 关键字参数
    """
    kwargs = kwargs or {}
    logger.debug(f"Calling {func_name} with args={args}, kwargs={kwargs}")