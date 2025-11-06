"""
Simple logging utility for the one-click launcher.

This provides a basic logging interface that works across platforms.
"""

import logging
import sys
from pathlib import Path
from typing import Optional


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    Get a configured logger instance.

    Args:
        name: Logger name
        level: Logging level

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    if not logger.handlers:
        # Create console handler
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)

        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)

        # Add handler to logger
        logger.addHandler(handler)
        logger.setLevel(level)

    return logger


def setup_file_logger(name: str, log_file: Path, level: int = logging.INFO) -> logging.Logger:
    """
    Setup a file logger.

    Args:
        name: Logger name
        log_file: Path to log file
        level: Logging level

    Returns:
        Configured logger instance
    """
    logger = get_logger(name, level)

    # Add file handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(level)

    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(formatter)

    logger.addHandler(file_handler)

    return logger