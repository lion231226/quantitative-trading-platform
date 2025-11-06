#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Progress Tracker Module - 进度跟踪模块

Provides rich progress tracking and user feedback capabilities for the launcher.
"""

import time
import threading
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import asyncio

# Import Rich libraries for enhanced UI
try:
    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn, TimeRemainingColumn
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text
    from rich.live import Live
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    print("Warning: Rich library not available. Using basic progress output.")

from utils.logger import get_logger

logger = get_logger(__name__)

class ProgressStatus(Enum):
    """Progress status enumeration"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class ProgressStep:
    """Individual progress step"""
    id: str
    name: str
    description: str
    status: ProgressStatus = ProgressStatus.PENDING
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    progress: float = 0.0
    error_message: Optional[str] = None
    substeps: List['ProgressStep'] = field(default_factory=list)
    parent_step: Optional[str] = None

    @property
    def duration(self) -> Optional[float]:
        """Calculate step duration"""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        elif self.start_time:
            return time.time() - self.start_time
        return None

    @property
    def is_completed(self) -> bool:
        """Check if step is completed"""
        return self.status == ProgressStatus.COMPLETED

    @property
    def is_active(self) -> bool:
        """Check if step is currently active"""
        return self.status == ProgressStatus.IN_PROGRESS

@dataclass
class ProgressSummary:
    """Progress summary information"""
    total_steps: int = 0
    completed_steps: int = 0
    failed_steps: int = 0
    current_step: Optional[str] = None
    overall_progress: float = 0.0
    estimated_time_remaining: Optional[float] = None
    total_elapsed_time: float = 0.0

class ProgressTracker:
    """Enhanced progress tracker with Rich UI support"""

    def __init__(self, use_rich: bool = True):
        """Initialize progress tracker"""
        self.use_rich = use_rich and RICH_AVAILABLE
        self.console = Console() if self.use_rich else None
        self.steps: Dict[str, ProgressStep] = {}
        self.root_steps: List[str] = []
        self.current_step_id: Optional[str] = None
        self.start_time: Optional[float] = None
        self.callbacks: List[Callable[[ProgressStep], None]] = []
        self._lock = threading.Lock()
        self._live_display: Optional[Live] = None

    def add_step(self, step_id: str, name: str, description: str = "", parent_step_id: Optional[str] = None) -> ProgressStep:
        """Add a new progress step"""
        with self._lock:
            if step_id in self.steps:
                logger.warning(f"Step {step_id} already exists, updating existing step")
                step = self.steps[step_id]
                step.name = name
                step.description = description
            else:
                step = ProgressStep(
                    id=step_id,
                    name=name,
                    description=description,
                    parent_step=parent_step_id
                )
                self.steps[step_id] = step

                # Add to appropriate step list
                if not parent_step_id:
                    self.root_steps.append(step_id)
                else:
                    # Add to parent step's substeps
                    if parent_step_id in self.steps:
                        self.steps[parent_step_id].substeps.append(step)

            # Initialize start time if this is the first step
            if not self.start_time:
                self.start_time = time.time()

            return step

    def start_step(self, step_id: str) -> bool:
        """Start a progress step"""
        with self._lock:
            if step_id not in self.steps:
                logger.error(f"Step {step_id} does not exist")
                return False

            step = self.steps[step_id]
            step.status = ProgressStatus.IN_PROGRESS
            step.start_time = time.time()
            step.progress = 0.0

            # Auto-start parent step if it's still pending
            if step.parent_step and self.steps[step.parent_step].status == ProgressStatus.PENDING:
                self.start_step(step.parent_step)

            self.current_step_id = step_id

            # Notify callbacks
            self._notify_callbacks(step)

            logger.info(f"Starting step: {step.name}")
            return True

    def update_progress(self, step_id: str, progress: float, message: str = "") -> bool:
        """Update step progress"""
        with self._lock:
            if step_id not in self.steps:
                logger.error(f"Step {step_id} does not exist")
                return False

            step = self.steps[step_id]
            step.progress = min(max(progress, 0.0), 100.0)

            # Update parent progress
            if step.parent_step:
                self._update_parent_progress(step.parent_step)

            # Notify callbacks
            self._notify_callbacks(step)

            if message:
                logger.debug(f"Step {step.name}: {progress:.1f}% - {message}")

            return True

    def complete_step(self, step_id: str, message: str = "") -> bool:
        """Complete a progress step"""
        with self._lock:
            if step_id not in self.steps:
                logger.error(f"Step {step_id} does not exist")
                return False

            step = self.steps[step_id]
            step.status = ProgressStatus.COMPLETED
            step.end_time = time.time()
            step.progress = 100.0

            # Complete all active substeps
            for substep in step.substeps:
                if substep.status == ProgressStatus.IN_PROGRESS:
                    self.complete_step(substep.id)

            # Update parent progress
            if step.parent_step:
                self._update_parent_progress(step.parent_step)
                self._check_parent_completion(step.parent_step)

            # Notify callbacks
            self._notify_callbacks(step)

            logger.info(f"Completed step: {step.name} {message}")
            return True

    def fail_step(self, step_id: str, error_message: str) -> bool:
        """Mark a step as failed"""
        with self._lock:
            if step_id not in self.steps:
                logger.error(f"Step {step_id} does not exist")
                return False

            step = self.steps[step_id]
            step.status = ProgressStatus.FAILED
            step.end_time = time.time()
            step.error_message = error_message

            # Notify callbacks
            self._notify_callbacks(step)

            logger.error(f"Step failed: {step.name} - {error_message}")
            return True

    def _update_parent_progress(self, parent_id: str):
        """Update parent step progress based on substeps"""
        if parent_id not in self.steps:
            return

        parent = self.steps[parent_id]
        if not parent.substeps:
            return

        total_progress = sum(substep.progress for substep in parent.substeps)
        parent.progress = total_progress / len(parent.substeps)

    def _check_parent_completion(self, parent_id: str):
        """Check if parent step should be marked as completed"""
        if parent_id not in self.steps:
            return

        parent = self.steps[parent_id]
        if not parent.substeps:
            return

        # Check if all substeps are completed
        all_completed = all(substep.status == ProgressStatus.COMPLETED for substep in parent.substeps)
        any_failed = any(substep.status == ProgressStatus.FAILED for substep in parent.substeps)

        if all_completed:
            self.complete_step(parent_id)
        elif any_failed and parent.status == ProgressStatus.IN_PROGRESS:
            self.fail_step(parent_id, "Substep failed")

    def get_step(self, step_id: str) -> Optional[ProgressStep]:
        """Get a progress step by ID"""
        return self.steps.get(step_id)

    def get_summary(self) -> ProgressSummary:
        """Get progress summary"""
        with self._lock:
            total_steps = len(self.steps)
            completed_steps = sum(1 for step in self.steps.values() if step.is_completed)
            failed_steps = sum(1 for step in self.steps.values() if step.status == ProgressStatus.FAILED)

            # Calculate overall progress
            if self.root_steps:
                total_progress = sum(self.steps[step_id].progress for step_id in self.root_steps) / len(self.root_steps)
            else:
                total_progress = 0.0

            # Estimate time remaining
            estimated_time_remaining = self._estimate_time_remaining()

            # Calculate elapsed time
            total_elapsed_time = time.time() - self.start_time if self.start_time else 0.0

            return ProgressSummary(
                total_steps=total_steps,
                completed_steps=completed_steps,
                failed_steps=failed_steps,
                current_step=self.current_step_id,
                overall_progress=total_progress,
                estimated_time_remaining=estimated_time_remaining,
                total_elapsed_time=total_elapsed_time
            )

    def _estimate_time_remaining(self) -> Optional[float]:
        """Estimate time remaining for completion"""
        if not self.start_time or not self.root_steps:
            return None

        completed_root_steps = [
            step_id for step_id in self.root_steps
            if self.steps[step_id].is_completed
        ]

        if len(completed_root_steps) == 0:
            return None

        # Calculate average step time
        total_time = sum(self.steps[step_id].duration for step_id in completed_root_steps if self.steps[step_id].duration)
        if total_time == 0:
            return None

        avg_step_time = total_time / len(completed_root_steps)
        remaining_steps = len(self.root_steps) - len(completed_root_steps)

        return avg_step_time * remaining_steps

    def display_progress(self, title: str = "系统进度"):
        """Display current progress"""
        if not self.use_rich:
            self._display_basic_progress(title)
            return

        summary = self.get_summary()

        # Create progress table
        table = Table(title=title, show_header=True, header_style="bold magenta")
        table.add_column("步骤", style="cyan", width=30)
        table.add_column("状态", style="green", width=10)
        table.add_column("进度", style="blue", width=15)
        table.add_column("耗时", style="yellow", width=10)

        # Add root steps to table
        for step_id in self.root_steps:
            if step_id in self.steps:
                step = self.steps[step_id]
                status_text = self._get_status_text(step.status)
                progress_text = f"{step.progress:.1f}%"
                duration_text = f"{step.duration:.1f}s" if step.duration else "-"

                table.add_row(step.name, status_text, progress_text, duration_text)

                # Add substeps
                for substep in step.substeps:
                    sub_status_text = self._get_status_text(substep.status)
                    sub_progress_text = f"{substep.progress:.1f}%"
                    sub_duration_text = f"{substep.duration:.1f}s" if substep.duration else "-"
                    table.add_row(f"  {substep.name}", sub_status_text, sub_progress_text, sub_duration_text)

        # Display summary info
        info_text = Text()
        info_text.append(f"总进度: {summary.overall_progress:.1f}%\n", style="bold blue")
        info_text.append(f"完成: {summary.completed_steps}/{summary.total_steps}\n", style="green")
        info_text.append(f"总耗时: {summary.total_elapsed_time:.1f}s", style="yellow")

        if summary.estimated_time_remaining:
            info_text.append(f"\n预计剩余: {summary.estimated_time_remaining:.1f}s", style="cyan")

        info_panel = Panel(info_text, title="总览信息", border_style="blue")

        self.console.print(table)
        self.console.print(info_panel)

    def _display_basic_progress(self, title: str):
        """Display basic progress without Rich"""
        summary = self.get_summary()

        print(f"\n{title}")
        print("=" * 50)
        print(f"总进度: {summary.overall_progress:.1f}%")
        print(f"完成: {summary.completed_steps}/{summary.total_steps}")
        print(f"总耗时: {summary.total_elapsed_time:.1f}s")

        if summary.estimated_time_remaining:
            print(f"预计剩余: {summary.estimated_time_remaining:.1f}s")

        print("-" * 50)

        for step_id in self.root_steps:
            if step_id in self.steps:
                step = self.steps[step_id]
                status_text = self._get_status_text(step.status)
                duration_text = f"({step.duration:.1f}s)" if step.duration else ""
                print(f"{step.name}: {status_text} {step.progress:.1f}% {duration_text}")

    def _get_status_text(self, status: ProgressStatus) -> str:
        """Get status text in Chinese"""
        status_map = {
            ProgressStatus.PENDING: "等待中",
            ProgressStatus.IN_PROGRESS: "进行中",
            ProgressStatus.COMPLETED: "已完成",
            ProgressStatus.FAILED: "失败",
            ProgressStatus.CANCELLED: "已取消"
        }
        return status_map.get(status, "未知")

    def add_callback(self, callback: Callable[[ProgressStep], None]):
        """Add progress change callback"""
        self.callbacks.append(callback)

    def _notify_callbacks(self, step: ProgressStep):
        """Notify all callbacks of progress change"""
        for callback in self.callbacks:
            try:
                callback(step)
            except Exception as e:
                logger.error(f"Progress callback error: {str(e)}")

    def start_live_display(self, refresh_rate: float = 0.5):
        """Start live display with Rich"""
        if not self.use_rich:
            return

        if self._live_display:
            return  # Already running

        self._live_display = Live(refresh_per_second=refresh_rate, console=self.console)
        self._live_display.start()

    def update_live_display(self, title: str = "系统进度"):
        """Update live display"""
        if not self._live_display or not self.use_rich:
            return

        # Create display content
        summary = self.get_summary()

        # Create progress table
        table = Table(title=title, show_header=True, header_style="bold magenta")
        table.add_column("步骤", style="cyan", width=30)
        table.add_column("状态", style="green", width=10)
        table.add_column("进度", style="blue", width=15)
        table.add_column("耗时", style="yellow", width=10)

        # Add steps to table
        for step_id in self.root_steps:
            if step_id in self.steps:
                step = self.steps[step_id]
                status_text = self._get_status_text(step.status)
                progress_text = f"{step.progress:.1f}%"
                duration_text = f"{step.duration:.1f}s" if step.duration else "-"

                table.add_row(step.name, status_text, progress_text, duration_text)

        # Create summary info
        info_text = Text()
        info_text.append(f"总进度: {summary.overall_progress:.1f}%\n", style="bold blue")
        info_text.append(f"完成: {summary.completed_steps}/{summary.total_steps}\n", style="green")
        info_text.append(f"总耗时: {summary.total_elapsed_time:.1f}s", style="yellow")

        if summary.estimated_time_remaining:
            info_text.append(f"\n预计剩余: {summary.estimated_time_remaining:.1f}s", style="cyan")

        info_panel = Panel(info_text, title="总览信息", border_style="blue")

        # Update display
        self._live_display.update(table)
        self._live_display.update(info_panel)

    def stop_live_display(self):
        """Stop live display"""
        if self._live_display:
            self._live_display.stop()
            self._live_display = None

    def reset(self):
        """Reset progress tracker"""
        with self._lock:
            self.steps.clear()
            self.root_steps.clear()
            self.current_step_id = None
            self.start_time = None
            self.stop_live_display()

    def export_progress(self) -> Dict[str, Any]:
        """Export progress data"""
        with self._lock:
            return {
                "steps": {
                    step_id: {
                        "name": step.name,
                        "description": step.description,
                        "status": step.status.value,
                        "progress": step.progress,
                        "start_time": step.start_time,
                        "end_time": step.end_time,
                        "duration": step.duration,
                        "error_message": step.error_message
                    }
                    for step_id, step in self.steps.items()
                },
                "summary": self.get_summary().__dict__
            }