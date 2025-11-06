"""
批量依赖安装引擎

This module provides comprehensive batch dependency installation capabilities
including parallel installation, resource management, and progress tracking
for the one-click launcher.
"""

import os
import subprocess
import asyncio
import threading
import time
import psutil
from typing import Dict, List, Optional, Tuple, Any, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed, Future
import queue

from utils.logger import get_logger
from core.dependency_analyzer import ProjectDependency, DependencyAnalysis
from core.installation_strategy import InstallationStrategy, InstallationStrategySelector, PackageSource
from core.conflict_resolver import VersionConflictResolver, ResolutionStrategy
from utils.progress_tracker import ProgressTracker

logger = get_logger(__name__)


class InstallationStatus(Enum):
    """安装状态"""
    PENDING = "pending"
    DOWNLOADING = "downloading"
    INSTALLING = "installing"
    CONFIGURING = "configuring"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"


class ResourceLimit(Enum):
    """资源限制类型"""
    CPU = "cpu"
    MEMORY = "memory"
    DISK_IO = "disk_io"
    NETWORK = "network"


@dataclass
class InstallationResult:
    """安装结果"""
    dependency: ProjectDependency
    strategy: InstallationStrategy
    status: InstallationStatus
    start_time: float
    end_time: Optional[float] = None
    success: bool = False
    error_message: Optional[str] = None
    output: str = ""
    return_code: Optional[int] = None
    installed_version: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def duration(self) -> Optional[float]:
        """获取安装持续时间"""
        if self.end_time and self.start_time:
            return self.end_time - self.start_time
        return None


@dataclass
class InstallationContext:
    """安装上下文"""
    project_root: str
    analysis: DependencyAnalysis
    strategies: List[InstallationStrategy]
    max_concurrent: int = 4
    timeout: int = 300
    dry_run: bool = False
    continue_on_error: bool = True
    progress_tracker: Optional[ProgressTracker] = None
    callback: Optional[Callable[[InstallationResult], None]] = None


@dataclass
class ResourceUsage:
    """资源使用情况"""
    cpu_percent: float
    memory_percent: float
    memory_mb: int
    active_processes: int
    network_io: Dict[str, int] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class ResourceMonitor:
    """资源监控器"""

    def __init__(self, max_cpu_percent: float = 80.0, max_memory_percent: float = 85.0):
        """
        初始化资源监控器

        Args:
            max_cpu_percent: 最大CPU使用率百分比
            max_memory_percent: 最大内存使用率百分比
        """
        self.max_cpu_percent = max_cpu_percent
        self.max_memory_percent = max_memory_percent
        self.logger = get_logger(self.__class__.__name__)
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None

    def get_current_usage(self) -> ResourceUsage:
        """获取当前资源使用情况"""
        try:
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=1)

            # 内存使用情况
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_mb = memory.used // (1024 * 1024)

            # 活动进程数
            active_processes = len(psutil.pids())

            # 网络IO（简化版）
            network_io = {}

            return ResourceUsage(
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                memory_mb=memory_mb,
                active_processes=active_processes,
                network_io=network_io
            )
        except Exception as e:
            self.logger.error(f"获取资源使用情况失败: {e}")
            return ResourceUsage(cpu_percent=0, memory_percent=0, memory_mb=0, active_processes=0)

    def is_resource_available(self, usage: ResourceUsage) -> bool:
        """检查资源是否可用"""
        return (usage.cpu_percent < self.max_cpu_percent and
                usage.memory_percent < self.max_memory_percent)

    def wait_for_resources(self, timeout: int = 60) -> bool:
        """等待资源可用"""
        start_time = time.time()

        while time.time() - start_time < timeout:
            usage = self.get_current_usage()
            if self.is_resource_available(usage):
                return True
            time.sleep(1)

        return False


class DependencyInstaller:
    """单个依赖安装器"""

    def __init__(self, resource_monitor: ResourceMonitor):
        """
        初始化依赖安装器

        Args:
            resource_monitor: 资源监控器
        """
        self.resource_monitor = resource_monitor
        self.logger = get_logger(self.__class__.__name__)

    def install(
        self,
        dependency: ProjectDependency,
        strategy: InstallationStrategy,
        timeout: int = 300,
        dry_run: bool = False
    ) -> InstallationResult:
        """
        安装单个依赖

        Args:
            dependency: 要安装的依赖
            strategy: 安装策略
            timeout: 超时时间（秒）
            dry_run: 是否为试运行

        Returns:
            安装结果
        """
        start_time = time.time()
        result = InstallationResult(
            dependency=dependency,
            strategy=strategy,
            status=InstallationStatus.PENDING,
            start_time=start_time
        )

        try:
            self.logger.info(f"开始安装 {dependency.name}...")

            # 等待资源可用
            if not self.resource_monitor.wait_for_resources():
                raise RuntimeError("资源不足，无法开始安装")

            # 试运行模式
            if dry_run:
                result.status = InstallationStatus.COMPLETED
                result.success = True
                result.output = f"[DRY RUN] Would install {dependency.name} with command: {' '.join(strategy.install_command)}"
                return result

            # 执行安装
            result.status = InstallationStatus.INSTALLING
            output, return_code = self._execute_install_command(strategy.install_command, timeout)

            result.end_time = time.time()
            result.output = output
            result.return_code = return_code
            result.success = return_code == 0

            if result.success:
                result.status = InstallationStatus.COMPLETED
                result.installed_version = self._get_installed_version(dependency, strategy)
                self.logger.info(f"成功安装 {dependency.name}")
            else:
                result.status = InstallationStatus.FAILED
                result.error_message = f"安装失败，返回码: {return_code}"
                self.logger.error(f"安装失败 {dependency.name}: {result.error_message}")

        except Exception as e:
            result.end_time = time.time()
            result.status = InstallationStatus.FAILED
            result.success = False
            result.error_message = str(e)
            self.logger.error(f"安装 {dependency.name} 时发生异常: {e}")

        return result

    def _execute_install_command(self, command: List[str], timeout: int) -> Tuple[str, int]:
        """执行安装命令"""
        try:
            self.logger.debug(f"执行命令: {' '.join(command)}")

            # 设置工作目录
            cwd = Path.cwd()

            # 执行命令
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=cwd,
                env=os.environ.copy()
            )

            try:
                stdout, _ = process.communicate(timeout=timeout)
                return stdout, process.returncode
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
                raise RuntimeError(f"命令执行超时 ({timeout}秒)")

        except Exception as e:
            self.logger.error(f"执行安装命令失败: {e}")
            return f"命令执行失败: {e}", 1

    def _get_installed_version(self, dependency: ProjectDependency, strategy: InstallationStrategy) -> Optional[str]:
        """获取已安装的版本"""
        try:
            if dependency.ecosystem == "python" and strategy.package_manager == "pip":
                # 使用 pip show 获取版本
                result = subprocess.run(
                    ["pip", "show", dependency.name],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0:
                    for line in result.stdout.split('\n'):
                        if line.startswith('Version:'):
                            return line.split(':', 1)[1].strip()

            elif dependency.ecosystem == "nodejs" and strategy.package_manager == "npm":
                # 使用 npm list 获取版本
                result = subprocess.run(
                    ["npm", "list", dependency.name, "--depth=0"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0:
                    for line in result.stdout.split('\n'):
                        if dependency.name in line:
                            # 解析版本信息
                            parts = line.split('@')
                            if len(parts) >= 2:
                                return parts[-1].strip()

        except Exception as e:
            self.logger.debug(f"获取 {dependency.name} 版本失败: {e}")

        return None


class BatchInstaller:
    """
    批量依赖安装引擎

    功能特性：
    - 并行安装管理
    - 资源监控和限制
    - 错误处理和重试
    - 进度跟踪
    - 安装结果汇总
    """

    def __init__(self, max_concurrent: int = 4, timeout: int = 300):
        """
        初始化批量安装器

        Args:
            max_concurrent: 最大并发安装数
            timeout: 默认超时时间（秒）
        """
        self.max_concurrent = max_concurrent
        self.timeout = timeout
        self.logger = get_logger(self.__class__.__name__)
        self.resource_monitor = ResourceMonitor()
        self.installer = DependencyInstaller(self.resource_monitor)

        # 安装状态
        self._is_installing = False
        self._cancel_event = threading.Event()
        self._installation_queue: queue.Queue = queue.Queue()
        self._results: List[InstallationResult] = []

    def install_dependencies(
        self,
        context: InstallationContext
    ) -> List[InstallationResult]:
        """
        批量安装依赖

        Args:
            context: 安装上下文

        Returns:
            安装结果列表
        """
        self.logger.info(f"开始批量安装 {len(context.strategies)} 个依赖...")

        self._is_installing = True
        self._cancel_event.clear()
        self._results = []

        try:
            # 准备安装队列
            self._prepare_installation_queue(context)

            # 执行批量安装
            if context.progress_tracker:
                context.progress_tracker.start_installation()

            results = self._execute_parallel_installation(context)

            if context.progress_tracker:
                success_count = len([r for r in results if r.success])
                context.progress_tracker.complete_installation(success_count == len(results))

            self.logger.info(f"批量安装完成: 成功 {len([r for r in results if r.success])}, 失败 {len([r for r in results if not r.success])}")
            return results

        except Exception as e:
            self.logger.error(f"批量安装过程中发生异常: {e}")
            return self._results
        finally:
            self._is_installing = False

    def _prepare_installation_queue(self, context: InstallationContext):
        """准备安装队列"""
        for strategy in context.strategies:
            self._installation_queue.put((strategy.dependency, strategy))

    def _execute_parallel_installation(self, context: InstallationContext) -> List[InstallationResult]:
        """执行并行安装"""
        results = []
        completed_count = 0
        total_count = len(context.strategies)

        with ThreadPoolExecutor(max_workers=context.max_concurrent) as executor:
            # 提交安装任务
            futures = []
            for strategy in context.strategies:
                if self._cancel_event.is_set():
                    break

                future = executor.submit(
                    self._install_single_dependency,
                    strategy.dependency,
                    strategy,
                    context.timeout,
                    context.dry_run
                )
                futures.append((future, strategy))

            # 等待任务完成
            for future, strategy in futures:
                if self._cancel_event.is_set():
                    break

                try:
                    result = future.result()
                    results.append(result)

                    # 调用回调函数
                    if context.callback:
                        try:
                            context.callback(result)
                        except Exception as e:
                            self.logger.error(f"回调函数执行失败: {e}")

                    # 更新进度
                    completed_count += 1
                    if context.progress_tracker:
                        step_index = context.strategies.index(strategy)
                        context.progress_tracker.complete_step(step_index, result.success, result.error_message)

                except Exception as e:
                    self.logger.error(f"安装任务执行失败: {e}")

                    # 创建失败结果
                    error_result = InstallationResult(
                        dependency=strategy.dependency,
                        strategy=strategy,
                        status=InstallationStatus.FAILED,
                        start_time=time.time(),
                        end_time=time.time(),
                        success=False,
                        error_message=str(e)
                    )
                    results.append(error_result)

                    if not context.continue_on_error:
                        self.logger.error("安装失败，停止批量安装")
                        break

        self._results = results
        return results

    def _install_single_dependency(
        self,
        dependency: ProjectDependency,
        strategy: InstallationStrategy,
        timeout: int,
        dry_run: bool
    ) -> InstallationResult:
        """安装单个依赖"""
        if self._cancel_event.is_set():
            return InstallationResult(
                dependency=dependency,
                strategy=strategy,
                status=InstallationStatus.CANCELLED,
                start_time=time.time(),
                end_time=time.time(),
                success=False,
                error_message="安装被取消"
            )

        result = self.installer.install(dependency, strategy, timeout, dry_run)

        # 如果失败且有回退源，尝试回退安装
        if not result.success and strategy.fallback_sources:
            result = self._try_fallback_installation(dependency, strategy, timeout, dry_run)

        return result

    def _try_fallback_installation(
        self,
        dependency: ProjectDependency,
        primary_strategy: InstallationStrategy,
        timeout: int,
        dry_run: bool
    ) -> InstallationResult:
        """尝试回退安装"""
        for fallback_source in primary_strategy.fallback_sources:
            if self._cancel_event.is_set():
                break

            self.logger.info(f"尝试使用回退源 {fallback_source.name} 安装 {dependency.name}")

            # 创建回退策略
            fallback_strategy = InstallationStrategy(
                dependency=dependency,
                mode=primary_strategy.mode,
                package_manager=primary_strategy.package_manager,
                source=fallback_source,
                install_command=self._generate_fallback_command(dependency, primary_strategy, fallback_source),
                estimated_time_sec=primary_strategy.estimated_time_sec,
                confidence_score=primary_strategy.confidence_score * 0.8  # 降低置信度
            )

            try:
                result = self.installer.install(dependency, fallback_strategy, timeout, dry_run)
                if result.success:
                    result.metadata["fallback_source"] = fallback_source.name
                    return result
            except Exception as e:
                self.logger.debug(f"回退安装失败: {e}")
                continue

        return InstallationResult(
            dependency=dependency,
            strategy=primary_strategy,
            status=InstallationStatus.FAILED,
            start_time=time.time(),
            end_time=time.time(),
            success=False,
            error_message="所有安装源都失败"
        )

    def _generate_fallback_command(
        self,
        dependency: ProjectDependency,
        primary_strategy: InstallationStrategy,
        fallback_source: PackageSource
    ) -> List[str]:
        """生成回退安装命令"""
        command = primary_strategy.install_command.copy()

        # 替换源URL
        if primary_strategy.source.url and fallback_source.url:
            for i, arg in enumerate(command):
                if arg == primary_strategy.source.url:
                    command[i] = fallback_source.url
                elif arg == "--registry" and i + 1 < len(command):
                    if command[i + 1] == primary_strategy.source.url:
                        command[i + 1] = fallback_source.url

        return command

    def cancel_installation(self):
        """取消安装"""
        self.logger.info("取消批量安装...")
        self._cancel_event.set()
        self._is_installing = False

    def is_installing(self) -> bool:
        """检查是否正在安装"""
        return self._is_installing

    def get_installation_progress(self) -> Dict[str, Any]:
        """获取安装进度"""
        if not self._results:
            return {
                "total": 0,
                "completed": 0,
                "successful": 0,
                "failed": 0,
                "progress_percentage": 0.0
            }

        total = len(self._results)
        successful = len([r for r in self._results if r.success])
        failed = len([r for r in self._results if not r.success])
        completed = len([r for r in self._results if r.status in [InstallationStatus.COMPLETED, InstallationStatus.FAILED]])

        return {
            "total": total,
            "completed": completed,
            "successful": successful,
            "failed": failed,
            "progress_percentage": (completed / total * 100) if total > 0 else 0.0,
            "current_resource_usage": self.resource_monitor.get_current_usage().__dict__
        }

    def get_installation_summary(self, results: List[InstallationResult]) -> Dict[str, Any]:
        """获取安装摘要"""
        if not results:
            return {"message": "没有安装结果"}

        successful_results = [r for r in results if r.success]
        failed_results = [r for r in results if not r.success]

        total_time = sum(r.duration or 0 for r in results)
        avg_time = total_time / len(results) if results else 0

        # 按生态系统统计
        ecosystems = {}
        for result in results:
            ecosystem = result.dependency.ecosystem
            if ecosystem not in ecosystems:
                ecosystems[ecosystem] = {"total": 0, "successful": 0, "failed": 0}
            ecosystems[ecosystem]["total"] += 1
            if result.success:
                ecosystems[ecosystem]["successful"] += 1
            else:
                ecosystems[ecosystem]["failed"] += 1

        return {
            "total_dependencies": len(results),
            "successful_installations": len(successful_results),
            "failed_installations": len(failed_results),
            "success_rate": len(successful_results) / len(results) * 100,
            "total_installation_time_sec": total_time,
            "average_installation_time_sec": avg_time,
            "ecosystems_breakdown": ecosystems,
            "failed_dependencies": [
                {
                    "name": r.dependency.name,
                    "ecosystem": r.dependency.ecosystem,
                    "error": r.error_message
                }
                for r in failed_results
            ]
        }


# 便利函数
def create_batch_installer(
    analysis: DependencyAnalysis,
    config_manager: Optional[Any] = None,
    progress_tracker: Optional[ProgressTracker] = None
) -> Tuple[BatchInstaller, InstallationContext]:
    """
    创建批量安装器

    Args:
        analysis: 依赖分析结果
        config_manager: 配置管理器
        progress_tracker: 进度跟踪器

    Returns:
        批量安装器和安装上下文
    """
    # 创建策略选择器
    strategy_selector = InstallationStrategySelector(config_manager)

    # 选择安装策略
    strategies = strategy_selector.batch_select_strategies(
        analysis.all_dependencies,
        progress_tracker=progress_tracker
    )

    # 创建安装上下文
    context = InstallationContext(
        project_root=analysis.project_root,
        analysis=analysis,
        strategies=strategies,
        max_concurrent=config_manager.get_max_concurrent_installs() if config_manager else 4,
        timeout=config_manager.get_installation_timeout() if config_manager else 300,
        progress_tracker=progress_tracker
    )

    # 创建批量安装器
    installer = BatchInstaller(
        max_concurrent=context.max_concurrent,
        timeout=context.timeout
    )

    return installer, context