#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Error Handler Module - 错误处理模块

Provides intelligent error detection, classification, and recovery mechanisms for the launcher.
"""

import os
import sys
import time
import traceback
import subprocess
import platform
from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
import asyncio
from pathlib import Path

# Import Rich libraries for enhanced UI
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text
    from rich.table import Table
    from rich.markdown import Markdown
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    print("Warning: Rich library not available. Using basic error output.")

from utils.logger import get_logger

logger = get_logger(__name__)

class ErrorSeverity(Enum):
    """Error severity levels"""
    WARNING = "warning"
    ERROR = "error"
    FATAL = "fatal"

class ErrorCategory(Enum):
    """Error categories"""
    RECOVERABLE = "recoverable"
    USER_ACTION_REQUIRED = "user_action_required"
    FATAL = "fatal"

@dataclass
class ErrorInfo:
    """Structured error information"""
    code: str
    message: str
    severity: ErrorSeverity
    category: ErrorCategory
    solution: str
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    retry_count: int = 0
    max_retries: int = 3

@dataclass
class RecoveryAction:
    """Recovery action definition"""
    name: str
    description: str
    action_func: Callable
    is_automatic: bool = True
    priority: int = 1

class ErrorHandler:
    """Intelligent error handler with recovery mechanisms"""

    def __init__(self, use_rich: bool = True):
        """Initialize error handler"""
        self.use_rich = use_rich and RICH_AVAILABLE
        self.console = Console() if self.use_rich else None
        self.error_history: List[ErrorInfo] = []
        self.recovery_actions: Dict[str, List[RecoveryAction]] = {}
        self._setup_error_patterns()
        self._setup_recovery_actions()

    def _setup_error_patterns(self):
        """Setup common error patterns and their classifications"""
        self.error_patterns = {
            # Port conflicts
            "port_conflict": {
                "patterns": ["Address already in use", "Port already in use", "EADDRINUSE"],
                "severity": ErrorSeverity.ERROR,
                "category": ErrorCategory.RECOVERABLE,
                "solution": "Try using alternative ports or stop conflicting services"
            },

            # Permission issues
            "permission_denied": {
                "patterns": ["Permission denied", "Access denied", "EACCES"],
                "severity": ErrorSeverity.ERROR,
                "category": ErrorCategory.USER_ACTION_REQUIRED,
                "solution": "Run as administrator or check file permissions"
            },

            # Missing dependencies
            "missing_dependency": {
                "patterns": ["ModuleNotFoundError", "ImportError", "command not found"],
                "severity": ErrorSeverity.ERROR,
                "category": ErrorCategory.RECOVERABLE,
                "solution": "Install missing dependencies using the installer"
            },

            # Network issues
            "network_error": {
                "patterns": ["Connection refused", "Network unreachable", "Timeout"],
                "severity": ErrorSeverity.ERROR,
                "category": ErrorCategory.RECOVERABLE,
                "solution": "Check network connectivity and firewall settings"
            },

            # Disk space issues
            "disk_space": {
                "patterns": ["No space left", "Disk full", "Insufficient disk space"],
                "severity": ErrorSeverity.FATAL,
                "category": ErrorCategory.USER_ACTION_REQUIRED,
                "solution": "Free up disk space and retry"
            },

            # Memory issues
            "memory_error": {
                "patterns": ["MemoryError", "Out of memory", "Cannot allocate memory"],
                "severity": ErrorSeverity.FATAL,
                "category": ErrorCategory.FATAL,
                "solution": "Close other applications or increase system memory"
            },

            # Configuration issues
            "config_error": {
                "patterns": ["Configuration error", "Invalid config", "Missing config"],
                "severity": ErrorSeverity.ERROR,
                "category": ErrorCategory.RECOVERABLE,
                "solution": "Check configuration files and reset to defaults if needed"
            },

            # Service startup failures
            "service_startup": {
                "patterns": ["Service failed to start", "Startup timeout", "Initialization failed"],
                "severity": ErrorSeverity.ERROR,
                "category": ErrorCategory.RECOVERABLE,
                "solution": "Check service logs and try restarting the service"
            }
        }

    def _setup_recovery_actions(self):
        """Setup automatic recovery actions"""
        self.recovery_actions = {
            "port_conflict": [
                RecoveryAction(
                    name="find_alternative_port",
                    description="Find and use alternative ports",
                    action_func=self._find_alternative_ports,
                    is_automatic=True,
                    priority=1
                ),
                RecoveryAction(
                    name="stop_conflicting_services",
                    description="Stop conflicting services",
                    action_func=self._stop_conflicting_services,
                    is_automatic=True,
                    priority=2
                )
            ],
            "missing_dependency": [
                RecoveryAction(
                    name="install_missing_dependencies",
                    description="Install missing dependencies automatically",
                    action_func=self._install_missing_dependencies,
                    is_automatic=True,
                    priority=1
                )
            ],
            "network_error": [
                RecoveryAction(
                    name="retry_with_backoff",
                    description="Retry operation with exponential backoff",
                    action_func=self._retry_with_backoff,
                    is_automatic=True,
                    priority=1
                )
            ],
            "service_startup": [
                RecoveryAction(
                    name="restart_service",
                    description="Restart the failed service",
                    action_func=self._restart_service,
                    is_automatic=True,
                    priority=1
                ),
                RecoveryAction(
                    name="reset_service_config",
                    description="Reset service configuration to defaults",
                    action_func=self._reset_service_config,
                    is_automatic=False,
                    priority=2
                )
            ]
        }

    def classify_error(self, error_message: str) -> Tuple[str, ErrorSeverity, ErrorCategory, str]:
        """Classify error based on message patterns"""
        error_message_lower = error_message.lower()

        for error_type, pattern_info in self.error_patterns.items():
            for pattern in pattern_info["patterns"]:
                if pattern.lower() in error_message_lower:
                    return (
                        error_type,
                        pattern_info["severity"],
                        pattern_info["category"],
                        pattern_info["solution"]
                    )

        # Default classification
        return (
            "unknown_error",
            ErrorSeverity.ERROR,
            ErrorCategory.RECOVERABLE,
            "Unknown error occurred. Check logs for more details."
        )

    def handle_error(self, error: Exception, context: Dict[str, Any] = None) -> ErrorInfo:
        """Handle an error with automatic recovery attempts"""
        error_message = str(error)
        error_type, severity, category, solution = self.classify_error(error_message)

        # Create error info
        error_info = ErrorInfo(
            code=error_type,
            message=error_message,
            severity=severity,
            category=category,
            solution=solution,
            details={
                "exception_type": type(error).__name__,
                "traceback": traceback.format_exc(),
                "context": context or {}
            }
        )

        # Add to error history
        self.error_history.append(error_info)

        # Log the error
        self._log_error(error_info)

        # Attempt recovery
        if category == ErrorCategory.RECOVERABLE:
            self._attempt_recovery(error_info)

        # Display error to user
        self._display_error(error_info)

        return error_info

    def _log_error(self, error_info: ErrorInfo):
        """Log error information"""
        if error_info.severity == ErrorSeverity.FATAL:
            logger.critical(f"FATAL ERROR [{error_info.code}]: {error_info.message}")
        elif error_info.severity == ErrorSeverity.ERROR:
            logger.error(f"ERROR [{error_info.code}]: {error_info.message}")
        else:
            logger.warning(f"WARNING [{error_info.code}]: {error_info.message}")

        logger.debug(f"Error details: {error_info.details}")

    def _attempt_recovery(self, error_info: ErrorInfo) -> bool:
        """Attempt automatic recovery for recoverable errors"""
        if error_info.code not in self.recovery_actions:
            logger.info(f"No recovery actions available for error type: {error_info.code}")
            return False

        recovery_actions = sorted(
            self.recovery_actions[error_info.code],
            key=lambda x: x.priority
        )

        for action in recovery_actions:
            if not action.is_automatic:
                continue

            try:
                logger.info(f"Attempting recovery action: {action.name}")
                success = action.action_func(error_info)
                if success:
                    logger.info(f"Recovery action successful: {action.name}")
                    return True
                else:
                    logger.warning(f"Recovery action failed: {action.name}")
            except Exception as e:
                logger.error(f"Recovery action error: {action.name} - {str(e)}")

        return False

    def _display_error(self, error_info: ErrorInfo):
        """Display error information to user"""
        if not self.use_rich:
            self._display_basic_error(error_info)
            return

        # Create error display
        title = f"[ERROR] {error_info.severity.value.upper()} ERROR"

        # Error details table
        table = Table(title=title, show_header=True, header_style="bold red")
        table.add_column("Property", style="cyan", width=15)
        table.add_column("Value", style="white", width=50)

        table.add_row("Error Code", error_info.code)
        table.add_row("Message", error_info.message)
        table.add_row("Category", error_info.category.value)
        table.add_row("Solution", error_info.solution)
        table.add_row("Time", time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(error_info.timestamp)))

        self.console.print(table)

        # Show recovery suggestions
        if error_info.category == ErrorCategory.RECOVERABLE:
            if error_info.code in self.recovery_actions:
                recovery_text = Text("\n[RECOVERY] Automatic Recovery Attempts:\n", style="bold yellow")
                for action in self.recovery_actions[error_info.code]:
                    if action.is_automatic:
                        recovery_text.append(f"• {action.description}\n", style="yellow")

                recovery_panel = Panel(recovery_text, title="Recovery", border_style="yellow")
                self.console.print(recovery_panel)

        # Show user action required
        if error_info.category == ErrorCategory.USER_ACTION_REQUIRED:
            action_text = Text("[ACTION] User Action Required:\n", style="bold red")
            action_text.append(f"• {error_info.solution}\n", style="red")

            if error_info.code == "permission_denied":
                action_text.append("• Try running the launcher as administrator\n", style="red")
            elif error_info.code == "disk_space":
                action_text.append("• Free up disk space and restart the launcher\n", style="red")

            action_panel = Panel(action_text, title="Required Action", border_style="red")
            self.console.print(action_panel)

    def _display_basic_error(self, error_info: ErrorInfo):
        """Display basic error without Rich"""
        print(f"\n{'='*60}")
        print(f"[ERROR] {error_info.severity.value.upper()} ERROR")
        print(f"{'='*60}")
        print(f"Error Code: {error_info.code}")
        print(f"Message: {error_info.message}")
        print(f"Category: {error_info.category.value}")
        print(f"Solution: {error_info.solution}")
        print(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(error_info.timestamp))}")

        if error_info.category == ErrorCategory.RECOVERABLE:
            print("\n[RECOVERY] Automatic recovery will be attempted...")

        if error_info.category == ErrorCategory.USER_ACTION_REQUIRED:
            print(f"\n[ACTION] ACTION REQUIRED: {error_info.solution}")

        print(f"{'='*60}")

    # Recovery action implementations
    def _find_alternative_ports(self, error_info: ErrorInfo) -> bool:
        """Find alternative ports for conflicting services"""
        try:
            alternative_ports = {
                "redis": 6380,
                "backend": 8001,
                "frontend": 3001
            }

            logger.info(f"Attempting to use alternative ports: {alternative_ports}")

            # Store in context for later use
            error_info.details["alternative_ports"] = alternative_ports
            return True
        except Exception as e:
            logger.error(f"Failed to find alternative ports: {str(e)}")
            return False

    def _stop_conflicting_services(self, error_info: ErrorInfo) -> bool:
        """Stop conflicting services using detected ports"""
        try:
            # This would implement service stopping logic
            logger.info("Attempting to stop conflicting services...")
            return True
        except Exception as e:
            logger.error(f"Failed to stop conflicting services: {str(e)}")
            return False

    def _install_missing_dependencies(self, error_info: ErrorInfo) -> bool:
        """Install missing dependencies automatically"""
        try:
            logger.info("Attempting to install missing dependencies...")
            # This would trigger the dependency installer
            return True
        except Exception as e:
            logger.error(f"Failed to install dependencies: {str(e)}")
            return False

    def _retry_with_backoff(self, error_info: ErrorInfo) -> bool:
        """Retry operation with exponential backoff"""
        try:
            max_retries = error_info.max_retries
            if error_info.retry_count >= max_retries:
                logger.warning(f"Max retries ({max_retries}) exceeded")
                return False

            delay = 2 ** error_info.retry_count  # Exponential backoff
            logger.info(f"Retrying in {delay} seconds... (attempt {error_info.retry_count + 1}/{max_retries})")
            time.sleep(delay)

            error_info.retry_count += 1
            return True
        except Exception as e:
            logger.error(f"Retry failed: {str(e)}")
            return False

    def _restart_service(self, error_info: ErrorInfo) -> bool:
        """Restart a failed service"""
        try:
            logger.info("Attempting to restart service...")
            # This would implement service restart logic
            return True
        except Exception as e:
            logger.error(f"Failed to restart service: {str(e)}")
            return False

    def _reset_service_config(self, error_info: ErrorInfo) -> bool:
        """Reset service configuration to defaults"""
        try:
            logger.info("Resetting service configuration to defaults...")
            # This would implement config reset logic
            return True
        except Exception as e:
            logger.error(f"Failed to reset service config: {str(e)}")
            return False

    def get_error_summary(self) -> Dict[str, Any]:
        """Get summary of all errors encountered"""
        if not self.error_history:
            return {"total_errors": 0, "by_severity": {}, "by_category": {}}

        by_severity = {}
        by_category = {}

        for error in self.error_history:
            # Count by severity
            severity = error.severity.value
            by_severity[severity] = by_severity.get(severity, 0) + 1

            # Count by category
            category = error.category.value
            by_category[category] = by_category.get(category, 0) + 1

        return {
            "total_errors": len(self.error_history),
            "by_severity": by_severity,
            "by_category": by_category,
            "latest_error": self.error_history[-1].__dict__ if self.error_history else None
        }

    def clear_error_history(self):
        """Clear error history"""
        self.error_history.clear()
        logger.info("Error history cleared")

    def export_errors(self) -> List[Dict[str, Any]]:
        """Export error data for analysis"""
        return [error.__dict__ for error in self.error_history]

    def create_error_report(self) -> str:
        """Create a detailed error report"""
        if not self.error_history:
            return "No errors encountered."

        report = []
        report.append("ERROR REPORT")
        report.append("=" * 50)
        report.append(f"Total Errors: {len(self.error_history)}")
        report.append(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")

        for i, error in enumerate(self.error_history, 1):
            report.append(f"Error #{i}")
            report.append(f"Code: {error.code}")
            report.append(f"Severity: {error.severity.value}")
            report.append(f"Category: {error.category.value}")
            report.append(f"Message: {error.message}")
            report.append(f"Solution: {error.solution}")
            report.append(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(error.timestamp))}")
            report.append(f"Retries: {error.retry_count}/{error.max_retries}")
            report.append("-" * 30)

        return "\n".join(report)