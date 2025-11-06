"""
安装进度跟踪器

提供实时安装进度跟踪、日志记录和用户反馈功能。
支持多种进度显示格式和回调机制。
"""

import time
import threading
from typing import Dict, List, Optional, Callable, Any, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import json
import os
from pathlib import Path

from utils.logger import get_logger

logger = get_logger(__name__)


class ProgressStatus(Enum):
    """进度状态枚举"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


@dataclass
class ProgressStep:
    """进度步骤"""
    name: str
    description: str
    weight: float = 1.0  # 权重，用于计算总体进度
    status: ProgressStatus = ProgressStatus.PENDING
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    error_message: Optional[str] = None
    sub_steps: List['ProgressStep'] = field(default_factory=list)

    def __post_init__(self):
        if self.weight <= 0:
            raise ValueError("步骤权重必须大于0")

    @property
    def duration(self) -> Optional[timedelta]:
        """获取步骤持续时间"""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return None

    @property
    def is_active(self) -> bool:
        """检查步骤是否处于活动状态"""
        return self.status == ProgressStatus.IN_PROGRESS

    @property
    def is_completed(self) -> bool:
        """检查步骤是否已完成"""
        return self.status in [ProgressStatus.COMPLETED, ProgressStatus.FAILED, ProgressStatus.CANCELLED]

    def start(self) -> None:
        """开始步骤"""
        self.status = ProgressStatus.IN_PROGRESS
        self.start_time = datetime.now()
        self.error_message = None

    def complete(self, success: bool = True, error_message: Optional[str] = None) -> None:
        """完成步骤"""
        self.end_time = datetime.now()
        if success:
            self.status = ProgressStatus.COMPLETED
        else:
            self.status = ProgressStatus.FAILED
            self.error_message = error_message

    def cancel(self) -> None:
        """取消步骤"""
        self.end_time = datetime.now()
        self.status = ProgressStatus.CANCELLED

    def pause(self) -> None:
        """暂停步骤"""
        if self.status == ProgressStatus.IN_PROGRESS:
            self.status = ProgressStatus.PAUSED

    def resume(self) -> None:
        """恢复步骤"""
        if self.status == ProgressStatus.PAUSED:
            self.status = ProgressStatus.IN_PROGRESS


@dataclass
class ProgressInfo:
    """进度信息"""
    component: str  # 组件名称（如 "Node.js", "Python", "Git"）
    current_step: int = 0
    total_steps: int = 0
    progress_percentage: float = 0.0
    status: ProgressStatus = ProgressStatus.PENDING
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    current_step_name: str = ""
    current_step_description: str = ""
    error_message: Optional[str] = None
    steps: List[ProgressStep] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def duration(self) -> Optional[timedelta]:
        """获取总持续时间"""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        elif self.start_time:
            return datetime.now() - self.start_time
        return None

    @property
    def estimated_remaining_time(self) -> Optional[timedelta]:
        """估算剩余时间"""
        if self.progress_percentage <= 0 or not self.start_time:
            return None

        elapsed = datetime.now() - self.start_time
        if self.progress_percentage >= 100:
            return timedelta(0)

        estimated_total = elapsed * (100.0 / self.progress_percentage)
        remaining = estimated_total - elapsed
        return max(remaining, timedelta(0))

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'component': self.component,
            'current_step': self.current_step,
            'total_steps': self.total_steps,
            'progress_percentage': self.progress_percentage,
            'status': self.status.value,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'current_step_name': self.current_step_name,
            'current_step_description': self.current_step_description,
            'error_message': self.error_message,
            'duration': str(self.duration) if self.duration else None,
            'estimated_remaining': str(self.estimated_remaining_time) if self.estimated_remaining_time else None,
            'steps': [
                {
                    'name': step.name,
                    'description': step.description,
                    'weight': step.weight,
                    'status': step.status.value,
                    'duration': str(step.duration) if step.duration else None,
                    'error_message': step.error_message
                }
                for step in self.steps
            ],
            'metadata': self.metadata
        }


class ProgressTracker:
    """
    安装进度跟踪器

    功能特性：
    - 实时进度跟踪和计算
    - 多步骤管理
    - 时间估算
    - 错误处理和日志记录
    - 回调机制支持
    - 进度持久化
    """

    def __init__(self, component_name: str, log_callback: Optional[Callable[[str], None]] = None):
        """
        初始化进度跟踪器

        Args:
            component_name: 组件名称（如 "Node.js"）
            log_callback: 日志回调函数
        """
        self.component_name = component_name
        self.log_callback = log_callback
        self.logger = get_logger(self.__class__.__name__)

        # 进度信息
        self.progress_info = ProgressInfo(component=component_name)
        self._lock = threading.Lock()

        # 回调函数列表
        self._progress_callbacks: List[Callable[[ProgressInfo], None]] = []
        self._step_callbacks: List[Callable[[ProgressStep], None]] = []

        # 状态标志
        self._is_started = False
        self._is_completed = False
        self._is_cancelled = False

        self.logger.info(f"初始化 {component_name} 进度跟踪器")

    def add_step(self, name: str, description: str, weight: float = 1.0) -> ProgressStep:
        """
        添加进度步骤

        Args:
            name: 步骤名称
            description: 步骤描述
            weight: 步骤权重

        Returns:
            创建的进度步骤
        """
        with self._lock:
            step = ProgressStep(name=name, description=description, weight=weight)
            self.progress_info.steps.append(step)
            self.progress_info.total_steps = len(self.progress_info.steps)

            self.logger.debug(f"添加步骤: {name} (权重: {weight})")
            return step

    def add_steps(self, steps: List[Tuple[str, str, float]]) -> None:
        """
        批量添加进度步骤

        Args:
            steps: 步骤列表，每个元素为 (name, description, weight)
        """
        for name, description, weight in steps:
            self.add_step(name, description, weight)

    def start_installation(self) -> None:
        """开始安装"""
        with self._lock:
            if self._is_started:
                self.logger.warning("安装已经开始")
                return

            self.progress_info.status = ProgressStatus.IN_PROGRESS
            self.progress_info.start_time = datetime.now()
            self._is_started = True

            self._log(f"开始安装 {self.component_name}")
            self._notify_progress_update()

    def start_step(self, step_index: int) -> bool:
        """
        开始指定步骤

        Args:
            step_index: 步骤索引

        Returns:
            是否成功开始
        """
        with self._lock:
            if not self._is_started or self._is_completed or self._is_cancelled:
                return False

            if step_index < 0 or step_index >= len(self.progress_info.steps):
                self.logger.error(f"无效的步骤索引: {step_index}")
                return False

            # 完成之前的步骤
            for i in range(step_index):
                step = self.progress_info.steps[i]
                if step.status == ProgressStatus.PENDING:
                    step.complete(success=False, error_message="步骤被跳过")

            # 开始当前步骤
            step = self.progress_info.steps[step_index]
            if step.status == ProgressStatus.PENDING:
                step.start()
                self.progress_info.current_step = step_index
                self.progress_info.current_step_name = step.name
                self.progress_info.current_step_description = step.description

                self._log(f"开始步骤: {step.description}")
                self._recalculate_progress()
                self._notify_step_update(step)
                self._notify_progress_update()
                return True

            return False

    def complete_step(self, step_index: int, success: bool = True, error_message: Optional[str] = None) -> bool:
        """
        完成指定步骤

        Args:
            step_index: 步骤索引
            success: 是否成功
            error_message: 错误消息

        Returns:
            是否成功完成
        """
        with self._lock:
            if not self._is_started or step_index < 0 or step_index >= len(self.progress_info.steps):
                return False

            step = self.progress_info.steps[step_index]
            if step.status == ProgressStatus.IN_PROGRESS:
                step.complete(success, error_message)

                if success:
                    self._log(f"完成步骤: {step.description}")
                else:
                    self._log(f"步骤失败: {step.description} - {error_message or '未知错误'}")

                self._recalculate_progress()
                self._notify_step_update(step)
                self._notify_progress_update()
                return True

            return False

    def update_step_progress(self, step_index: int, sub_step_name: str, sub_progress: float) -> bool:
        """
        更新步骤的子进度

        Args:
            step_index: 步骤索引
            sub_step_name: 子步骤名称
            sub_progress: 子进度 (0.0 - 1.0)

        Returns:
            是否成功更新
        """
        with self._lock:
            if not self._is_started or step_index < 0 or step_index >= len(self.progress_info.steps):
                return False

            step = self.progress_info.steps[step_index]
            if step.status == ProgressStatus.IN_PROGRESS:
                # 更新步骤的元数据
                step_metadata = self.progress_info.metadata.setdefault('step_progress', {})
                step_metadata[f"{step_index}_{sub_step_name}"] = sub_progress

                self._recalculate_progress()
                self._notify_progress_update()
                return True

            return False

    def complete_installation(self, success: bool = True, error_message: Optional[str] = None) -> None:
        """
        完成安装

        Args:
            success: 是否成功
            error_message: 错误消息
        """
        with self._lock:
            if not self._is_started or self._is_completed:
                return

            self.progress_info.end_time = datetime.now()

            if success:
                self.progress_info.status = ProgressStatus.COMPLETED
                self.progress_info.progress_percentage = 100.0
                self._log(f"成功安装 {self.component_name}")
            else:
                self.progress_info.status = ProgressStatus.FAILED
                self.progress_info.error_message = error_message
                self._log(f"安装失败 {self.component_name}: {error_message or '未知错误'}")

            self._is_completed = True
            self._notify_progress_update()

    def complete_with_error(self, error_message: str) -> None:
        """
        标记进度失败并记录错误信息

        Args:
            error_message: 错误消息
        """
        self.complete_installation(success=False, error_message=error_message)

    def start(self) -> None:
        """
        开始进度跟踪（兼容方法）
        """
        self.start_installation()

    def update_step(self, step_description: str) -> None:
        """
        更新当前步骤（兼容方法）

        Args:
            step_description: 步骤描述
        """
        with self._lock:
            # 如果没有步骤，自动添加步骤
            if not self.progress_info.steps:
                self.add_step(step_description, step_description, 1.0)
                self.start_step(0)
                self.complete_step(0, success=True)
            else:
                # 查找当前活动的步骤或添加新步骤
                current_step_index = self.progress_info.current_step
                if current_step_index < len(self.progress_info.steps) - 1:
                    # 移动到下一步
                    next_step_index = current_step_index + 1
                    self.start_step(next_step_index)
                    self.complete_step(next_step_index, success=True)
                else:
                    # 添加新步骤
                    new_step_index = len(self.progress_info.steps)
                    self.add_step(step_description, step_description, 1.0)
                    self.start_step(new_step_index)
                    self.complete_step(new_step_index, success=True)

            # 更新当前步骤描述
            self.progress_info.current_step_description = step_description
            self._log(f"步骤完成: {step_description}")
            self._notify_progress_update()

    def cancel_installation(self) -> None:
        """取消安装"""
        with self._lock:
            if not self._is_started or self._is_completed or self._is_cancelled:
                return

            # 取消当前活动步骤
            for step in self.progress_info.steps:
                if step.is_active:
                    step.cancel()

            self.progress_info.end_time = datetime.now()
            self.progress_info.status = ProgressStatus.CANCELLED
            self._is_cancelled = True

            self._log(f"取消安装 {self.component_name}")
            self._notify_progress_update()

    def _recalculate_progress(self) -> None:
        """重新计算总体进度"""
        if not self.progress_info.steps:
            self.progress_info.progress_percentage = 0.0
            return

        total_weight = sum(step.weight for step in self.progress_info.steps)
        completed_weight = 0.0

        for step in self.progress_info.steps:
            if step.status == ProgressStatus.COMPLETED:
                completed_weight += step.weight
            elif step.status == ProgressStatus.IN_PROGRESS:
                # 考虑子步骤进度
                step_progress = self.progress_info.metadata.get('step_progress', {})
                step_sub_progress = 0.0
                sub_count = 0

                for key, progress in step_progress.items():
                    if key.startswith(f"{self.progress_info.steps.index(step)}_"):
                        step_sub_progress += progress
                        sub_count += 1

                if sub_count > 0:
                    # 平均子步骤进度
                    avg_sub_progress = step_sub_progress / sub_count
                    completed_weight += step.weight * avg_sub_progress

        # 计算总体进度百分比
        if total_weight > 0:
            self.progress_info.progress_percentage = (completed_weight / total_weight) * 100.0
        else:
            self.progress_info.progress_percentage = 0.0

        # 确保进度在合理范围内
        self.progress_info.progress_percentage = max(0.0, min(100.0, self.progress_info.progress_percentage))

    def add_progress_callback(self, callback: Callable[[ProgressInfo], None]) -> None:
        """
        添加进度更新回调函数

        Args:
            callback: 回调函数，接收 ProgressInfo 参数
        """
        self._progress_callbacks.append(callback)

    def add_step_callback(self, callback: Callable[[ProgressStep], None]) -> None:
        """
        添加步骤更新回调函数

        Args:
            callback: 回调函数，接收 ProgressStep 参数
        """
        self._step_callbacks.append(callback)

    def remove_progress_callback(self, callback: Callable[[ProgressInfo], None]) -> bool:
        """
        移除进度更新回调函数

        Args:
            callback: 要移除的回调函数

        Returns:
            是否成功移除
        """
        try:
            self._progress_callbacks.remove(callback)
            return True
        except ValueError:
            return False

    def remove_step_callback(self, callback: Callable[[ProgressStep], None]) -> bool:
        """
        移除步骤更新回调函数

        Args:
            callback: 要移除的回调函数

        Returns:
            是否成功移除
        """
        try:
            self._step_callbacks.remove(callback)
            return True
        except ValueError:
            return False

    def _notify_progress_update(self) -> None:
        """通知进度更新"""
        for callback in self._progress_callbacks:
            try:
                callback(self.progress_info)
            except Exception as e:
                self.logger.error(f"进度回调函数执行失败: {e}")

    def _notify_step_update(self, step: ProgressStep) -> None:
        """通知步骤更新"""
        for callback in self._step_callbacks:
            try:
                callback(step)
            except Exception as e:
                self.logger.error(f"步骤回调函数执行失败: {e}")

    def _log(self, message: str) -> None:
        """记录日志"""
        self.logger.info(message)
        if self.log_callback:
            try:
                self.log_callback(message)
            except Exception as e:
                self.logger.error(f"日志回调函数执行失败: {e}")

    def get_progress(self) -> ProgressInfo:
        """获取当前进度信息"""
        with self._lock:
            # 更新实时信息
            if self.progress_info.status == ProgressStatus.IN_PROGRESS:
                self._recalculate_progress()
            return self.progress_info

    def get_progress_summary(self) -> str:
        """获取进度摘要字符串"""
        progress = self.get_progress()

        status_emoji = {
            ProgressStatus.PENDING: "⏳",
            ProgressStatus.IN_PROGRESS: "🔄",
            ProgressStatus.COMPLETED: "✅",
            ProgressStatus.FAILED: "❌",
            ProgressStatus.CANCELLED: "🚫",
            ProgressStatus.PAUSED: "⏸️"
        }

        emoji = status_emoji.get(progress.status, "❓")
        percentage = progress.progress_percentage

        summary = f"{emoji} {self.component_name}: {percentage:.1f}%"

        if progress.current_step_name:
            summary += f" - {progress.current_step_description}"

        if progress.estimated_remaining_time:
            remaining = progress.estimated_remaining_time
            if remaining.total_seconds() > 60:
                summary += f" (剩余: {remaining.total_seconds()/60:.1f}分钟)"
            else:
                summary += f" (剩余: {remaining.total_seconds():.0f}秒)"

        return summary

    def save_progress(self, filepath: str) -> bool:
        """
        保存进度到文件

        Args:
            filepath: 文件路径

        Returns:
            是否成功保存
        """
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self.progress_info.to_dict(), f, indent=2, ensure_ascii=False)
            self.logger.debug(f"进度已保存到: {filepath}")
            return True
        except Exception as e:
            self.logger.error(f"保存进度失败: {e}")
            return False

    def load_progress(self, filepath: str) -> bool:
        """
        从文件加载进度

        Args:
            filepath: 文件路径

        Returns:
            是否成功加载
        """
        try:
            if not os.path.exists(filepath):
                return False

            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 恢复进度信息
            self.progress_info.component = data.get('component', self.component_name)
            self.progress_info.progress_percentage = data.get('progress_percentage', 0.0)
            self.progress_info.status = ProgressStatus(data.get('status', 'pending'))
            self.progress_info.current_step = data.get('current_step', 0)
            self.progress_info.total_steps = data.get('total_steps', 0)
            self.progress_info.current_step_name = data.get('current_step_name', '')
            self.progress_info.current_step_description = data.get('current_step_description', '')
            self.progress_info.error_message = data.get('error_message')
            self.progress_info.metadata = data.get('metadata', {})

            # 恢复时间信息
            if data.get('start_time'):
                self.progress_info.start_time = datetime.fromisoformat(data['start_time'])
            if data.get('end_time'):
                self.progress_info.end_time = datetime.fromisoformat(data['end_time'])

            # 恢复步骤信息
            self.progress_info.steps = []
            for step_data in data.get('steps', []):
                step = ProgressStep(
                    name=step_data['name'],
                    description=step_data['description'],
                    weight=step_data['weight'],
                    status=ProgressStatus(step_data['status'])
                )
                step.error_message = step_data.get('error_message')
                self.progress_info.steps.append(step)

            self.logger.debug(f"进度已从文件加载: {filepath}")
            return True

        except Exception as e:
            self.logger.error(f"加载进度失败: {e}")
            return False

    def print_detailed_progress(self) -> None:
        """打印详细的进度信息"""
        progress = self.get_progress()

        print(f"\n=== {self.component_name} 安装进度 ===")
        print(f"状态: {progress.status.value}")
        print(f"总体进度: {progress.progress_percentage:.1f}%")

        if progress.start_time:
            print(f"开始时间: {progress.start_time.strftime('%H:%M:%S')}")
            if progress.duration:
                print(f"已用时间: {progress.duration}")

        if progress.estimated_remaining_time:
            print(f"预计剩余: {progress.estimated_remaining_time}")

        print(f"\n当前步骤: {progress.current_step_description}")

        print("\n步骤详情:")
        for i, step in enumerate(progress.steps):
            status_icon = {
                ProgressStatus.PENDING: "⏸️",
                ProgressStatus.IN_PROGRESS: "🔄",
                ProgressStatus.COMPLETED: "✅",
                ProgressStatus.FAILED: "❌",
                ProgressStatus.CANCELLED: "🚫"
            }.get(step.status, "❓")

            print(f"  {i+1}. {status_icon} {step.description} (权重: {step.weight})")
            if step.error_message:
                print(f"     错误: {step.error_message}")
            if step.duration:
                print(f"     用时: {step.duration}")

        if progress.error_message:
            print(f"\n错误: {progress.error_message}")

        print("=" * 40)


# 便利函数
def create_nodejs_progress_tracker(log_callback: Optional[Callable[[str], None]] = None) -> ProgressTracker:
    """
    创建 Node.js 安装进度跟踪器

    Args:
        log_callback: 日志回调函数

    Returns:
        配置好的进度跟踪器
    """
    tracker = ProgressTracker("Node.js", log_callback)

    # 添加标准 Node.js 安装步骤
    tracker.add_steps([
        ("检查系统", "检查操作系统和架构", 5),
        ("获取版本信息", "获取最新的 Node.js LTS 版本", 10),
        ("下载安装包", "下载 Node.js 安装包", 30),
        ("验证安装包", "验证下载文件的完整性", 5),
        ("执行安装", "安装 Node.js", 40),
        ("配置环境", "配置环境变量和路径", 5),
        ("验证安装", "验证 Node.js 和 NPM 是否正常工作", 5)
    ])

    return tracker


def create_python_progress_tracker(log_callback: Optional[Callable[[str], None]] = None) -> ProgressTracker:
    """
    创建 Python 安装进度跟踪器

    Args:
        log_callback: 日志回调函数

    Returns:
        配置好的进度跟踪器
    """
    tracker = ProgressTracker("Python", log_callback)

    # 添加标准 Python 安装步骤
    tracker.add_steps([
        ("检查系统", "检查操作系统和架构", 5),
        ("获取版本信息", "获取最新的 Python 3.x 版本", 10),
        ("下载安装包", "下载 Python 安装包", 30),
        ("验证安装包", "验证下载文件的完整性", 5),
        ("执行安装", "安装 Python", 40),
        ("配置环境", "配置环境变量和 pip", 5),
        ("验证安装", "验证 Python 和 pip 是否正常工作", 5)
    ])

    return tracker


def create_git_progress_tracker(log_callback: Optional[Callable[[str], None]] = None) -> ProgressTracker:
    """
    创建 Git 安装进度跟踪器

    Args:
        log_callback: 日志回调函数

    Returns:
        配置好的进度跟踪器
    """
    tracker = ProgressTracker("Git", log_callback)

    # 添加标准 Git 安装步骤
    tracker.add_steps([
        ("检查系统", "检查操作系统和架构", 5),
        ("获取版本信息", "获取最新的 Git 版本", 10),
        ("下载安装包", "下载 Git 安装包", 30),
        ("验证安装包", "验证下载文件的完整性", 5),
        ("执行安装", "安装 Git", 40),
        ("基础配置", "配置 Git 用户信息", 5),
        ("验证安装", "验证 Git 是否正常工作", 5)
    ])

    return tracker