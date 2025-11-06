"""
进度跟踪和错误处理器

This module provides comprehensive progress tracking and error handling capabilities
including real-time progress monitoring, detailed error diagnosis, recovery mechanisms,
and user-friendly feedback interfaces for the one-click launcher.
"""

import os
import time
import traceback
import threading
from typing import Dict, List, Optional, Tuple, Any, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import json

from utils.logger import get_logger
from utils.progress_tracker import ProgressTracker, ProgressInfo, ProgressStatus
from core.dependency_analyzer import ProjectDependency
from core.batch_installer import InstallationResult, InstallationStatus

logger = get_logger(__name__)


class ErrorSeverity(Enum):
    """错误严重程度"""
    INFO = "info"           # 信息
    WARNING = "warning"     # 警告
    ERROR = "error"         # 错误
    CRITICAL = "critical"   # 严重错误
    FATAL = "fatal"         # 致命错误


class ErrorCategory(Enum):
    """错误类别"""
    NETWORK = "network"         # 网络错误
    FILESYSTEM = "filesystem"   # 文件系统错误
    DEPENDENCY = "dependency"   # 依赖错误
    PERMISSION = "permission"   # 权限错误
    RESOURCE = "resource"       # 资源错误
    CONFIGURATION = "configuration"  # 配置错误
    SYSTEM = "system"           # 系统错误
    USER = "user"               # 用户错误
    UNKNOWN = "unknown"         # 未知错误


class RecoveryAction(Enum):
    """恢复动作"""
    RETRY = "retry"                     # 重试
    SKIP = "skip"                       # 跳过
    FALLBACK = "fallback"               # 回退
    MANUAL_INTERVENTION = "manual"      # 手动干预
    ABORT = "abort"                     # 中止
    CONTINUE = "continue"               # 继续


@dataclass
class ErrorInfo:
    """错误信息"""
    error_id: str
    timestamp: float
    severity: ErrorSeverity
    category: ErrorCategory
    message: str
    details: Optional[str] = None
    component: Optional[str] = None
    dependency: Optional[ProjectDependency] = None
    traceback_info: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    suggested_actions: List[str] = field(default_factory=list)
    recovery_action: Optional[RecoveryAction] = None
    is_recoverable: bool = True
    retry_count: int = 0
    max_retries: int = 3


@dataclass
class ProgressSnapshot:
    """进度快照"""
    timestamp: float
    overall_progress: float
    component_progress: Dict[str, float]
    current_phase: str
    completed_steps: List[str]
    active_steps: List[str]
    errors_count: int
    warnings_count: int
    estimated_remaining_time: Optional[float] = None


@dataclass
class ProgressReport:
    """进度报告"""
    session_id: str
    start_time: float
    end_time: Optional[float] = None
    snapshots: List[ProgressSnapshot] = field(default_factory=list)
    errors: List[ErrorInfo] = field(default_factory=list)
    warnings: List[ErrorInfo] = field(default_factory=list)
    total_steps: int = 0
    completed_steps: int = 0
    success_rate: float = 0.0
    summary: str = ""


class ErrorClassifier:
    """错误分类器"""

    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
        self._classification_patterns = self._initialize_patterns()

    def _initialize_patterns(self) -> Dict[ErrorCategory, List[str]]:
        """初始化分类模式"""
        return {
            ErrorCategory.NETWORK: [
                "connection refused", "timeout", "network unreachable",
                "dns resolution failed", "ssl", "certificate", "proxy",
                "urllib error", "requests exception", "http error"
            ],
            ErrorCategory.FILESYSTEM: [
                "no such file", "permission denied", "disk full",
                "file not found", "directory not found", "access denied",
                "io error", "disk space", "read only", "lock"
            ],
            ErrorCategory.DEPENDENCY: [
                "dependency not found", "version conflict", "module not found",
                "import error", "package not found", "requirement not satisfied",
                "pip install failed", "npm install failed", "setup failed"
            ],
            ErrorCategory.PERMISSION: [
                "permission denied", "access denied", "unauthorized",
                "admin privileges", "sudo required", "root required",
                "insufficient privileges"
            ],
            ErrorCategory.RESOURCE: [
                "out of memory", "cpu limit", "disk space", "resource limit",
                "too many files", "process limit", "memory limit"
            ],
            ErrorCategory.CONFIGURATION: [
                "configuration error", "invalid config", "missing config",
                "parse error", "syntax error", "invalid format"
            ],
            ErrorCategory.SYSTEM: [
                "system error", "os error", "kernel panic", "blue screen",
                "crash", "exception", "error code"
            ]
        }

    def classify_error(self, error: Exception, context: Optional[Dict[str, Any]] = None) -> ErrorCategory:
        """分类错误"""
        error_message = str(error).lower()
        error_class_name = error.__class__.__name__.lower()

        # 检查错误消息模式
        for category, patterns in self._classification_patterns.items():
            for pattern in patterns:
                if pattern in error_message or pattern in error_class_name:
                    return category

        # 检查上下文信息
        if context:
            for key, value in context.items():
                if isinstance(value, str) and any(p in value.lower() for p in ["network", "internet", "connection"]):
                    return ErrorCategory.NETWORK
                elif isinstance(value, str) and any(p in value.lower() for p in ["file", "directory", "path"]):
                    return ErrorCategory.FILESYSTEM

        return ErrorCategory.UNKNOWN

    def determine_severity(self, error: Exception, category: ErrorCategory) -> ErrorSeverity:
        """确定错误严重程度"""
        # 根据错误类型确定基础严重程度
        base_severity = {
            ErrorCategory.NETWORK: ErrorSeverity.WARNING,
            ErrorCategory.FILESYSTEM: ErrorSeverity.ERROR,
            ErrorCategory.DEPENDENCY: ErrorSeverity.WARNING,
            ErrorCategory.PERMISSION: ErrorSeverity.ERROR,
            ErrorCategory.RESOURCE: ErrorSeverity.ERROR,
            ErrorCategory.CONFIGURATION: ErrorSeverity.WARNING,
            ErrorCategory.SYSTEM: ErrorSeverity.CRITICAL,
            ErrorCategory.UNKNOWN: ErrorSeverity.WARNING
        }

        severity = base_severity.get(category, ErrorSeverity.WARNING)

        # 根据错误类型调整严重程度
        error_class_name = error.__class__.__name__.lower()
        if any(keyword in error_class_name for keyword in ["critical", "fatal", "exception"]):
            severity = ErrorSeverity.CRITICAL
        elif any(keyword in error_class_name for keyword in ["warning", "warn"]):
            severity = ErrorSeverity.WARNING

        return severity


class RecoveryStrategy:
    """恢复策略"""

    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
        self._recovery_actions = self._initialize_recovery_actions()

    def _initialize_recovery_actions(self) -> Dict[ErrorCategory, List[RecoveryAction]]:
        """初始化恢复动作"""
        return {
            ErrorCategory.NETWORK: [
                RecoveryAction.RETRY,
                RecoveryAction.FALLBACK,
                RecoveryAction.MANUAL_INTERVENTION
            ],
            ErrorCategory.FILESYSTEM: [
                RecoveryAction.RETRY,
                RecoveryAction.MANUAL_INTERVENTION,
                RecoveryAction.SKIP
            ],
            ErrorCategory.DEPENDENCY: [
                RecoveryAction.RETRY,
                RecoveryAction.FALLBACK,
                RecoveryAction.MANUAL_INTERVENTION
            ],
            ErrorCategory.PERMISSION: [
                RecoveryAction.MANUAL_INTERVENTION,
                RecoveryAction.SKIP
            ],
            ErrorCategory.RESOURCE: [
                RecoveryAction.RETRY,
                RecoveryAction.SKIP,
                RecoveryAction.ABORT
            ],
            ErrorCategory.CONFIGURATION: [
                RecoveryAction.MANUAL_INTERVENTION,
                RecoveryAction.SKIP
            ],
            ErrorCategory.SYSTEM: [
                RecoveryAction.ABORT,
                RecoveryAction.MANUAL_INTERVENTION
            ],
            ErrorCategory.UNKNOWN: [
                RecoveryAction.RETRY,
                RecoveryAction.SKIP,
                RecoveryAction.MANUAL_INTERVENTION
            ]
        }

    def suggest_recovery_action(self, error: ErrorInfo) -> RecoveryAction:
        """建议恢复动作"""
        actions = self._recovery_actions.get(error.category, [RecoveryAction.RETRY])

        # 根据重试次数调整
        if error.retry_count >= error.max_retries:
            if RecoveryAction.RETRY in actions:
                actions.remove(RecoveryAction.RETRY)

        # 根据严重程度调整
        if error.severity == ErrorSeverity.CRITICAL:
            return RecoveryAction.ABORT
        elif error.severity == ErrorSeverity.FATAL:
            return RecoveryAction.ABORT

        # 返回优先级最高的动作
        if actions:
            return actions[0]

        return RecoveryAction.MANUAL_INTERVENTION

    def generate_suggestions(self, error: ErrorInfo) -> List[str]:
        """生成恢复建议"""
        suggestions = []

        if error.category == ErrorCategory.NETWORK:
            suggestions.extend([
                "检查网络连接",
                "尝试切换到其他网络环境",
                "检查防火墙设置",
                "使用代理或镜像源"
            ])
        elif error.category == ErrorCategory.FILESYSTEM:
            suggestions.extend([
                "检查文件权限",
                "确保磁盘空间充足",
                "检查文件路径是否正确",
                "以管理员权限运行"
            ])
        elif error.category == ErrorCategory.DEPENDENCY:
            suggestions.extend([
                "检查依赖版本兼容性",
                "清理包管理器缓存",
                "尝试使用不同的包管理器",
                "检查系统环境变量"
            ])
        elif error.category == ErrorCategory.PERMISSION:
            suggestions.extend([
                "以管理员权限运行",
                "检查文件和目录权限",
                "确保当前用户有写入权限",
                "使用sudo命令（Linux/macOS）"
            ])
        elif error.category == ErrorCategory.RESOURCE:
            suggestions.extend([
                "关闭其他应用程序释放资源",
                "增加系统内存或磁盘空间",
                "减少并发安装数量",
                "检查系统资源使用情况"
            ])

        # 通用建议
        suggestions.extend([
            "查看详细错误日志",
            "尝试重新运行安装",
            "检查系统环境配置"
        ])

        return suggestions[:5]  # 最多返回5个建议


class ProgressErrorHandler:
    """
    进度跟踪和错误处理器

    功能特性：
    - 实时进度监控
    - 错误分类和诊断
    - 自动恢复机制
    - 用户友好的反馈
    - 详细的报告生成
    """

    def __init__(self, session_id: Optional[str] = None):
        """
        初始化进度错误处理器

        Args:
            session_id: 会话ID，如果不提供则自动生成
        """
        self.session_id = session_id or self._generate_session_id()
        self.logger = get_logger(self.__class__.__name__)

        # 组件
        self.error_classifier = ErrorClassifier()
        self.recovery_strategy = RecoveryStrategy()

        # 状态
        self.start_time = time.time()
        self.end_time: Optional[float] = None
        self.progress_trackers: Dict[str, ProgressTracker] = {}
        self.errors: List[ErrorInfo] = []
        self.warnings: List[ErrorInfo] = []
        self.snapshots: List[ProgressSnapshot] = []

        # 线程安全
        self._lock = threading.Lock()

        self.logger.info(f"初始化进度错误处理器，会话ID: {self.session_id}")

    def _generate_session_id(self) -> str:
        """生成会话ID"""
        import uuid
        return f"session_{uuid.uuid4().hex[:8]}_{int(time.time())}"

    def create_progress_tracker(self, component_name: str, total_steps: int = 0) -> ProgressTracker:
        """创建进度跟踪器"""
        with self._lock:
            if component_name in self.progress_trackers:
                return self.progress_trackers[component_name]

            tracker = ProgressTracker(
                component_name=component_name,
                log_callback=self._log_progress_message
            )

            if total_steps > 0:
                for i in range(total_steps):
                    tracker.add_step(f"Step {i+1}", f"Processing step {i+1}")

            self.progress_trackers[component_name] = tracker
            self.logger.debug(f"创建进度跟踪器: {component_name}")

            return tracker

    def _log_progress_message(self, message: str) -> None:
        """记录进度消息"""
        self.logger.info(f"进度更新: {message}")

    def track_progress(self, component_name: str, step_index: int, progress_data: Optional[Dict[str, Any]] = None) -> None:
        """跟踪进度"""
        with self._lock:
            if component_name not in self.progress_trackers:
                self.create_progress_tracker(component_name)

            tracker = self.progress_trackers[component_name]
            tracker.start_step(step_index)

            # 记录进度快照
            self._capture_progress_snapshot()

    def complete_step(self, component_name: str, step_index: int, success: bool = True, error_message: Optional[str] = None) -> None:
        """完成步骤"""
        with self._lock:
            if component_name in self.progress_trackers:
                tracker = self.progress_trackers[component_name]
                tracker.complete_step(step_index, success, error_message)

                if not success and error_message:
                    self.handle_error(
                        error=Exception(error_message),
                        component=component_name,
                        context={"step_index": step_index}
                    )

    def handle_error(
        self,
        error: Exception,
        component: Optional[str] = None,
        dependency: Optional[ProjectDependency] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> ErrorInfo:
        """处理错误"""
        with self._lock:
            # 分类错误
            category = self.error_classifier.classify_error(error, context)
            severity = self.error_classifier.determine_severity(error, category)

            # 创建错误信息
            error_id = f"error_{len(self.errors) + 1}_{int(time.time())}"
            error_info = ErrorInfo(
                error_id=error_id,
                timestamp=time.time(),
                severity=severity,
                category=category,
                message=str(error),
                details=error.__class__.__name__,
                component=component,
                dependency=dependency,
                traceback_info=traceback.format_exc(),
                context=context or {}
            )

            # 生成恢复建议
            error_info.suggested_actions = self.recovery_strategy.generate_suggestions(error_info)
            error_info.recovery_action = self.recovery_strategy.suggest_recovery_action(error_info)

            # 根据严重程度决定是否可恢复
            error_info.is_recoverable = severity not in [ErrorSeverity.CRITICAL, ErrorSeverity.FATAL]

            # 添加到相应的列表
            if severity in [ErrorSeverity.ERROR, ErrorSeverity.CRITICAL, ErrorSeverity.FATAL]:
                self.errors.append(error_info)
                self.logger.error(f"错误 [{error_id}]: {error_info.message} ({category.value})")
            else:
                self.warnings.append(error_info)
                self.logger.warning(f"警告 [{error_id}]: {error_info.message} ({category.value})")

            return error_info

    def handle_installation_result(self, result: InstallationResult) -> None:
        """处理安装结果"""
        if not result.success and result.error_message:
            self.handle_error(
                error=Exception(result.error_message),
                component=result.dependency.ecosystem,
                dependency=result.dependency,
                context={
                    "return_code": result.return_code,
                    "output": result.output
                }
            )

    def retry_error(self, error_id: str) -> bool:
        """重试错误"""
        with self._lock:
            for error in self.errors:
                if error.error_id == error_id and error.retry_count < error.max_retries:
                    error.retry_count += 1
                    self.logger.info(f"重试错误 [{error_id}]: 第 {error.retry_count} 次重试")
                    return True

        return False

    def _capture_progress_snapshot(self) -> None:
        """捕获进度快照"""
        with self._lock:
            # 计算总体进度
            total_progress = 0.0
            component_progress = {}

            if self.progress_trackers:
                total_progress = sum(
                    tracker.get_progress().progress_percentage
                    for tracker in self.progress_trackers.values()
                ) / len(self.progress_trackers)

                component_progress = {
                    name: tracker.get_progress().progress_percentage
                    for name, tracker in self.progress_trackers.items()
                }

            # 获取活动步骤
            active_steps = []
            completed_steps = []

            for tracker in self.progress_trackers.values():
                progress = tracker.get_progress()
                if progress.current_step_name:
                    active_steps.append(f"{progress.component}: {progress.current_step_name}")

                for step in progress.steps:
                    if step.status == ProgressStatus.COMPLETED:
                        completed_steps.append(f"{progress.component}: {step.name}")

            snapshot = ProgressSnapshot(
                timestamp=time.time(),
                overall_progress=total_progress,
                component_progress=component_progress,
                current_phase="installation",
                completed_steps=completed_steps,
                active_steps=active_steps,
                errors_count=len(self.errors),
                warnings_count=len(self.warnings)
            )

            self.snapshots.append(snapshot)

    def get_current_progress(self) -> ProgressSnapshot:
        """获取当前进度"""
        self._capture_progress_snapshot()
        return self.snapshots[-1] if self.snapshots else ProgressSnapshot(
            timestamp=time.time(),
            overall_progress=0.0,
            component_progress={},
            current_phase="initialization",
            completed_steps=[],
            active_steps=[],
            errors_count=0,
            warnings_count=0
        )

    def get_progress_summary(self) -> Dict[str, Any]:
        """获取进度摘要"""
        current_progress = self.get_current_progress()
        elapsed_time = time.time() - self.start_time

        # 按严重程度统计错误
        error_summary = {}
        for error in self.errors:
            severity = error.severity.value
            error_summary[severity] = error_summary.get(severity, 0) + 1

        return {
            "session_id": self.session_id,
            "elapsed_time_sec": elapsed_time,
            "overall_progress": current_progress.overall_progress,
            "component_progress": current_progress.component_progress,
            "current_phase": current_progress.current_phase,
            "total_errors": len(self.errors),
            "total_warnings": len(self.warnings),
            "error_summary": error_summary,
            "active_components": list(self.progress_trackers.keys()),
            "is_completed": self.end_time is not None
        }

    def generate_report(self) -> ProgressReport:
        """生成进度报告"""
        end_time = self.end_time or time.time()
        duration = end_time - self.start_time

        # 计算成功率
        total_operations = len(self.errors) + len(self.warnings) + sum(
            len(tracker.get_progress().steps) for tracker in self.progress_trackers.values()
        )
        successful_operations = sum(
            len([step for step in tracker.get_progress().steps if step.status == ProgressStatus.COMPLETED])
            for tracker in self.progress_trackers.values()
        )
        success_rate = successful_operations / total_operations if total_operations > 0 else 0.0

        # 生成摘要
        summary_parts = []
        if self.errors:
            summary_parts.append(f"遇到 {len(self.errors)} 个错误")
        if self.warnings:
            summary_parts.append(f"产生 {len(self.warnings)} 个警告")
        if success_rate > 0.8:
            summary_parts.append("安装基本成功")
        else:
            summary_parts.append("安装存在问题")

        summary = "，".join(summary_parts) if summary_parts else "安装完成"

        report = ProgressReport(
            session_id=self.session_id,
            start_time=self.start_time,
            end_time=end_time,
            snapshots=self.snapshots.copy(),
            errors=self.errors.copy(),
            warnings=self.warnings.copy(),
            total_steps=sum(len(tracker.get_progress().steps) for tracker in self.progress_trackers.values()),
            completed_steps=successful_operations,
            success_rate=success_rate,
            summary=summary
        )

        return report

    def save_report(self, output_path: str) -> bool:
        """保存报告"""
        try:
            report = self.generate_report()
            report_data = {
                "session_id": report.session_id,
                "start_time": report.start_time,
                "end_time": report.end_time,
                "duration_sec": report.end_time - report.start_time if report.end_time else 0,
                "summary": report.summary,
                "success_rate": report.success_rate,
                "total_steps": report.total_steps,
                "completed_steps": report.completed_steps,
                "errors": [
                    {
                        "error_id": error.error_id,
                        "timestamp": error.timestamp,
                        "severity": error.severity.value,
                        "category": error.category.value,
                        "message": error.message,
                        "component": error.component,
                        "dependency": error.dependency.name if error.dependency else None,
                        "suggested_actions": error.suggested_actions
                    }
                    for error in report.errors
                ],
                "warnings": [
                    {
                        "error_id": warning.error_id,
                        "timestamp": warning.timestamp,
                        "message": warning.message,
                        "component": warning.component
                    }
                    for warning in report.warnings
                ],
                "progress_snapshots": [
                    {
                        "timestamp": snapshot.timestamp,
                        "overall_progress": snapshot.overall_progress,
                        "component_progress": snapshot.component_progress,
                        "errors_count": snapshot.errors_count,
                        "warnings_count": snapshot.warnings_count
                    }
                    for snapshot in report.snapshots[-10:]  # 只保存最近10个快照
                ]
            }

            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, indent=2, ensure_ascii=False)

            self.logger.info(f"进度报告已保存到: {output_path}")
            return True

        except Exception as e:
            self.logger.error(f"保存进度报告失败: {e}")
            return False

    def finish_session(self) -> None:
        """结束会话"""
        with self._lock:
            self.end_time = time.time()
            self.logger.info(f"会话 {self.session_id} 已结束")

    def get_user_friendly_feedback(self) -> str:
        """获取用户友好的反馈信息"""
        summary = self.get_progress_summary()

        feedback_parts = []

        # 进度信息
        if summary["overall_progress"] > 0:
            feedback_parts.append(f"进度: {summary['overall_progress']:.1f}%")

        # 状态信息
        if summary["total_errors"] == 0 and summary["total_warnings"] == 0:
            feedback_parts.append("✅ 一切正常")
        elif summary["total_errors"] == 0:
            feedback_parts.append(f"⚠️ 有 {summary['total_warnings']} 个警告")
        else:
            feedback_parts.append(f"❌ 有 {summary['total_errors']} 个错误")

        # 时间信息
        elapsed_min = summary["elapsed_time_sec"] / 60
        if elapsed_min > 1:
            feedback_parts.append(f"已用时: {elapsed_min:.1f} 分钟")

        # 主要错误
        if summary["total_errors"] > 0:
            latest_error = self.errors[-1]
            feedback_parts.append(f"最新错误: {latest_error.category.value}")

        return " | ".join(feedback_parts)


# 便利函数
def create_progress_error_handler(session_id: Optional[str] = None) -> ProgressErrorHandler:
    """创建进度错误处理器"""
    return ProgressErrorHandler(session_id)


def track_dependency_installation(
    handler: ProgressErrorHandler,
    dependency: ProjectDependency,
    installation_func: Callable,
    *args, **kwargs
) -> Any:
    """
    跟踪依赖安装的便利函数

    Args:
        handler: 进度错误处理器
        dependency: 依赖项
        installation_func: 安装函数
        *args, **kwargs: 安装函数参数

    Returns:
        安装结果
    """
    component_name = f"{dependency.ecosystem}:{dependency.name}"
    tracker = handler.create_progress_tracker(component_name, total_steps=3)

    tracker.start_installation()

    try:
        # 步骤1: 准备安装
        handler.track_progress(component_name, 0)
        tracker.start_step(0)
        time.sleep(0.1)  # 模拟准备时间
        tracker.complete_step(0, True)

        # 步骤2: 执行安装
        handler.track_progress(component_name, 1)
        tracker.start_step(1)
        result = installation_func(*args, **kwargs)

        if hasattr(result, 'success') and not result.success:
            raise Exception(result.error_message or "安装失败")

        tracker.complete_step(1, True)

        # 步骤3: 验证安装
        handler.track_progress(component_name, 2)
        tracker.start_step(2)
        time.sleep(0.1)  # 模拟验证时间
        tracker.complete_step(2, True)

        tracker.complete_installation(True)
        return result

    except Exception as e:
        tracker.complete_step(1, False, str(e))
        tracker.complete_installation(False)
        handler.handle_error(e, component_name, dependency)
        raise