"""
启动超时管理器

提供可配置的超时机制、渐进式超时升级、监控和取消功能。
支持不同服务类型的超时配置和事件日志记录。
"""

import asyncio
import time
import signal
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import threading
import json
from pathlib import Path

from .service_dependency_analyzer import ServiceInfo, ServiceType
from utils.logger import get_logger

logger = get_logger(__name__)


class TimeoutStatus(Enum):
    """超时状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    FAILED = "failed"


@dataclass
class TimeoutConfig:
    """超时配置"""
    default_timeout: int = 60
    max_timeout: int = 300
    min_timeout: int = 10
    escalation_factor: float = 1.5
    max_retries: int = 3
    retry_delay: float = 2.0
    grace_period: float = 5.0  # 宽限期

    # 服务类型特定的超时配置
    service_timeouts: Dict[ServiceType, int] = field(default_factory=lambda: {
        ServiceType.DATABASE: 30,
        ServiceType.BACKEND_API: 60,
        ServiceType.FRONTEND: 120,
        ServiceType.CACHE: 15,
        ServiceType.MESSAGE_QUEUE: 45,
        ServiceType.EXTERNAL_API: 30,
        ServiceType.UTILITY: 30
    })

    def get_timeout_for_service(self, service_type: ServiceType) -> int:
        """获取服务类型对应的超时时间"""
        return self.service_timeouts.get(service_type, self.default_timeout)


@dataclass
class TimeoutEvent:
    """超时事件"""
    event_id: str
    service_name: str
    timeout: int
    start_time: datetime
    end_time: Optional[datetime] = None
    status: TimeoutStatus = TimeoutStatus.PENDING
    retry_count: int = 0
    escalation_count: int = 0
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    @property
    def elapsed_time(self) -> timedelta:
        """已用时间"""
        end = self.end_time or datetime.now()
        return end - self.start_time

    @property
    def remaining_time(self) -> Optional[timedelta]:
        """剩余时间"""
        if self.status in [TimeoutStatus.COMPLETED, TimeoutStatus.TIMEOUT, TimeoutStatus.CANCELLED]:
            return None
        timeout_delta = timedelta(seconds=self.timeout)
        elapsed = self.elapsed_time
        remaining = timeout_delta - elapsed
        return remaining if remaining.total_seconds() > 0 else timedelta(0)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'event_id': self.event_id,
            'service_name': self.service_name,
            'timeout': self.timeout,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'status': self.status.value,
            'retry_count': self.retry_count,
            'escalation_count': self.escalation_count,
            'message': self.message,
            'details': self.details,
            'elapsed_seconds': self.elapsed_time.total_seconds(),
            'remaining_seconds': self.remaining_time.total_seconds() if self.remaining_time else None
        }


@dataclass
class StartupResult:
    """启动结果"""
    success: bool
    service_name: str
    start_time: datetime
    end_time: datetime
    duration: float
    timeout_used: int
    retries: int = 0
    escalations: int = 0
    error_message: Optional[str] = None
    events: List[TimeoutEvent] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'success': self.success,
            'service_name': self.service_name,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat(),
            'duration': self.duration,
            'timeout_used': self.timeout_used,
            'retries': self.retries,
            'escalations': self.escalations,
            'error_message': self.error_message,
            'events': [event.to_dict() for event in self.events]
        }


class TimeoutManager:
    """
    启动超时管理器

    功能特性：
    - 可配置的超时机制
    - 渐进式超时升级
    - 超时监控和取消
    - 事件日志记录
    - 异步操作支持
    """

    def __init__(self, config: Optional[TimeoutConfig] = None):
        """
        初始化超时管理器

        Args:
            config: 超时配置
        """
        self.config = config or TimeoutConfig()
        self.logger = get_logger(self.__class__.__name__)

        # 活动的超时事件
        self.active_events: Dict[str, TimeoutEvent] = {}

        # 事件历史记录
        self.event_history: List[TimeoutEvent] = []

        # 统计信息
        self.stats = {
            'total_events': 0,
            'successful_events': 0,
            'timeout_events': 0,
            'cancelled_events': 0,
            'average_duration': 0.0,
            'total_duration': 0.0
        }

        # 事件回调函数
        self.event_callbacks: Dict[str, List[Callable[[TimeoutEvent], None]]] = {
            'start': [],
            'progress': [],
            'timeout': [],
            'complete': [],
            'cancel': [],
            'escalate': []
        }

        # 线程锁
        self._lock = threading.RLock()

        self.logger.info("启动超时管理器初始化完成")

    def set_service_timeout(self, service_type: Union[str, ServiceType], timeout: int) -> None:
        """
        设置服务类型的超时时间

        Args:
            service_type: 服务类型
            timeout: 超时时间（秒）
        """
        if isinstance(service_type, str):
            service_type = ServiceType(service_type)

        if timeout < self.config.min_timeout:
            timeout = self.config.min_timeout
        elif timeout > self.config.max_timeout:
            timeout = self.config.max_timeout

        self.config.service_timeouts[service_type] = timeout
        self.logger.info(f"设置服务类型 {service_type.value} 的超时时间为 {timeout} 秒")

    async def wait_with_timeout(self, coro, timeout: Optional[int] = None,
                              service_name: str = "unknown") -> Any:
        """
        等待协程完成，带超时控制

        Args:
            coro: 协程对象
            timeout: 超时时间
            service_name: 服务名称

        Returns:
            协程结果

        Raises:
            asyncio.TimeoutError: 超时异常
        """
        if timeout is None:
            timeout = self.config.default_timeout

        start_time = datetime.now()
        event_id = f"{service_name}_{int(start_time.timestamp())}"

        # 创建超时事件
        timeout_event = TimeoutEvent(
            event_id=event_id,
            service_name=service_name,
            timeout=timeout,
            start_time=start_time,
            status=TimeoutStatus.RUNNING
        )

        with self._lock:
            self.active_events[event_id] = timeout_event
            self.stats['total_events'] += 1

        # 触发开始事件回调
        await self._trigger_event_callbacks('start', timeout_event)

        try:
            # 使用asyncio.wait_for实现超时控制
            result = await asyncio.wait_for(coro, timeout=timeout)

            # 成功完成
            timeout_event.status = TimeoutStatus.COMPLETED
            timeout_event.end_time = datetime.now()
            timeout_event.message = f"操作在 {timeout_event.elapsed_time.total_seconds():.2f} 秒内成功完成"

            with self._lock:
                self.stats['successful_events'] += 1
                self.stats['total_duration'] += timeout_event.elapsed_time.total_seconds()
                if self.stats['successful_events'] > 0:
                    self.stats['average_duration'] = self.stats['total_duration'] / self.stats['successful_events']

            # 触发完成事件回调
            await self._trigger_event_callbacks('complete', timeout_event)

            return result

        except asyncio.TimeoutError:
            # 超时处理
            timeout_event.status = TimeoutStatus.TIMEOUT
            timeout_event.end_time = datetime.now()
            timeout_event.message = f"操作超时 (限制: {timeout} 秒, 实际: {timeout_event.elapsed_time.total_seconds():.2f} 秒)"

            with self._lock:
                self.stats['timeout_events'] += 1

            # 触发超时事件回调
            await self._trigger_event_callbacks('timeout', timeout_event)

            raise

        except Exception as e:
            # 其他异常
            timeout_event.status = TimeoutStatus.FAILED
            timeout_event.end_time = datetime.now()
            timeout_event.message = f"操作失败: {str(e)}"
            timeout_event.details['exception'] = str(e)

            # 触发失败事件回调
            await self._trigger_event_callbacks('complete', timeout_event)  # 使用complete回调，因为操作已结束

            raise

        finally:
            # 清理活动事件
            with self._lock:
                if event_id in self.active_events:
                    del self.active_events[event_id]
                self.event_history.append(timeout_event)

                # 限制历史记录长度
                max_history = 1000
                if len(self.event_history) > max_history:
                    self.event_history = self.event_history[-max_history:]

    async def monitor_startup(self, service_info: ServiceInfo,
                            startup_func: Callable[[], Any]) -> StartupResult:
        """
        监控服务启动过程

        Args:
            service_info: 服务信息
            startup_func: 启动函数

        Returns:
            启动结果
        """
        start_time = datetime.now()
        events = []

        # 获取服务特定的超时时间
        base_timeout = self.config.get_timeout_for_service(service_info.service_type)
        if service_info.startup_timeout:
            base_timeout = service_info.startup_timeout

        current_timeout = base_timeout
        retry_count = 0
        escalation_count = 0

        while True:
            try:
                # 创建超时事件
                event_id = f"{service_info.name}_{int(start_time.timestamp())}_{retry_count}"
                timeout_event = TimeoutEvent(
                    event_id=event_id,
                    service_name=service_info.name,
                    timeout=current_timeout,
                    start_time=datetime.now(),
                    retry_count=retry_count,
                    escalation_count=escalation_count
                )

                events.append(timeout_event)

                self.logger.info(f"启动服务 {service_info.name} (尝试 {retry_count + 1}, 超时: {current_timeout}s)")

                # 执行启动操作
                await self.wait_with_timeout(startup_func(), current_timeout, service_info.name)

                # 启动成功
                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()

                result = StartupResult(
                    success=True,
                    service_name=service_info.name,
                    start_time=start_time,
                    end_time=end_time,
                    duration=duration,
                    timeout_used=current_timeout,
                    retries=retry_count,
                    escalations=escalation_count,
                    events=events
                )

                self.logger.info(f"服务 {service_info.name} 启动成功，耗时 {duration:.2f} 秒")
                return result

            except asyncio.TimeoutError:
                # 超时处理
                retry_count += 1

                if retry_count <= self.config.max_retries:
                    # 计算升级后的超时时间
                    escalation_count += 1
                    current_timeout = min(
                        int(current_timeout * self.config.escalation_factor),
                        self.config.max_timeout
                    )

                    self.logger.warning(f"服务 {service_info.name} 启动超时，{self.config.retry_delay}秒后重试 (新超时: {current_timeout}s)")
                    await asyncio.sleep(self.config.retry_delay)

                    # 触发升级事件回调
                    timeout_event.status = TimeoutStatus.TIMEOUT
                    await self._trigger_event_callbacks('escalate', timeout_event)

                else:
                    # 超过最大重试次数
                    end_time = datetime.now()
                    duration = (end_time - start_time).total_seconds()

                    result = StartupResult(
                        success=False,
                        service_name=service_info.name,
                        start_time=start_time,
                        end_time=end_time,
                        duration=duration,
                        timeout_used=current_timeout,
                        retries=retry_count,
                        escalations=escalation_count,
                        error_message=f"启动超时，已重试 {retry_count} 次",
                        events=events
                    )

                    self.logger.error(f"服务 {service_info.name} 启动失败，超过最大重试次数")
                    return result

            except Exception as e:
                # 其他异常
                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()

                result = StartupResult(
                    success=False,
                    service_name=service_info.name,
                    start_time=start_time,
                    end_time=end_time,
                    duration=duration,
                    timeout_used=current_timeout,
                    retries=retry_count,
                    escalations=escalation_count,
                    error_message=str(e),
                    events=events
                )

                self.logger.error(f"服务 {service_info.name} 启动异常: {e}")
                return result

    def cancel_timeout(self, event_id: str, reason: str = "手动取消") -> bool:
        """
        取消超时事件

        Args:
            event_id: 事件ID
            reason: 取消原因

        Returns:
            是否成功取消
        """
        with self._lock:
            if event_id in self.active_events:
                timeout_event = self.active_events[event_id]
                timeout_event.status = TimeoutStatus.CANCELLED
                timeout_event.end_time = datetime.now()
                timeout_event.message = reason

                self.stats['cancelled_events'] += 1

                # 异步触发取消事件回调
                asyncio.create_task(self._trigger_event_callbacks('cancel', timeout_event))

                self.logger.info(f"取消超时事件: {event_id} ({reason})")
                return True

        return False

    def get_active_events(self) -> List[TimeoutEvent]:
        """获取所有活动的超时事件"""
        with self._lock:
            return list(self.active_events.values())

    def get_event_history(self, service_name: Optional[str] = None,
                         limit: int = 100) -> List[TimeoutEvent]:
        """
        获取事件历史记录

        Args:
            service_name: 服务名称过滤
            limit: 返回记录数量限制

        Returns:
            事件历史记录列表
        """
        with self._lock:
            history = self.event_history

            if service_name:
                history = [event for event in history if event.service_name == service_name]

            return history[-limit:] if limit > 0 else history

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            stats = self.stats.copy()
            stats['active_events_count'] = len(self.active_events)
            stats['total_history_count'] = len(self.event_history)

            # 计算成功率
            if stats['total_events'] > 0:
                stats['success_rate'] = (stats['successful_events'] / stats['total_events']) * 100
                stats['timeout_rate'] = (stats['timeout_events'] / stats['total_events']) * 100
                stats['cancellation_rate'] = (stats['cancelled_events'] / stats['total_events']) * 100
            else:
                stats['success_rate'] = 0.0
                stats['timeout_rate'] = 0.0
                stats['cancellation_rate'] = 0.0

            return stats

    def add_event_callback(self, event_type: str, callback: Callable[[TimeoutEvent], None]) -> None:
        """
        添加事件回调函数

        Args:
            event_type: 事件类型 (start, progress, timeout, complete, cancel, escalate)
            callback: 回调函数
        """
        if event_type in self.event_callbacks:
            self.event_callbacks[event_type].append(callback)
            self.logger.debug(f"添加 {event_type} 事件回调函数")
        else:
            raise ValueError(f"不支持的事件类型: {event_type}")

    def remove_event_callback(self, event_type: str, callback: Callable[[TimeoutEvent], None]) -> bool:
        """
        移除事件回调函数

        Args:
            event_type: 事件类型
            callback: 回调函数

        Returns:
            是否成功移除
        """
        if event_type in self.event_callbacks:
            try:
                self.event_callbacks[event_type].remove(callback)
                self.logger.debug(f"移除 {event_type} 事件回调函数")
                return True
            except ValueError:
                pass
        return False

    async def _trigger_event_callbacks(self, event_type: str, event: TimeoutEvent) -> None:
        """触发事件回调函数"""
        if event_type in self.event_callbacks:
            for callback in self.event_callbacks[event_type]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(event)
                    else:
                        callback(event)
                except Exception as e:
                    self.logger.error(f"执行 {event_type} 事件回调函数失败: {e}")

    def create_progress_monitor(self, service_name: str, total_steps: int) -> Callable[[int, str], None]:
        """
        创建进度监控函数

        Args:
            service_name: 服务名称
            total_steps: 总步骤数

        Returns:
            进度更新函数
        """
        def update_progress(current_step: int, message: str = "") -> None:
            progress = (current_step / total_steps) * 100

            # 记录进度日志
            self.logger.info(f"服务 {service_name} 进度: {progress:.1f}% ({current_step}/{total_steps}) {message}")

            # 可以在这里添加进度事件回调
            for event in self.active_events.values():
                if event.service_name == service_name:
                    event.details['progress'] = progress
                    event.details['current_step'] = current_step
                    event.details['total_steps'] = total_steps
                    event.details['progress_message'] = message
                    break

        return update_progress

    def export_timeout_data(self, include_history: bool = False) -> Dict[str, Any]:
        """
        导出超时管理数据

        Args:
            include_history: 是否包含历史记录

        Returns:
            超时管理数据
        """
        data = {
            'config': {
                'default_timeout': self.config.default_timeout,
                'max_timeout': self.config.max_timeout,
                'min_timeout': self.config.min_timeout,
                'escalation_factor': self.config.escalation_factor,
                'max_retries': self.config.max_retries,
                'retry_delay': self.config.retry_delay,
                'service_timeouts': {
                    service_type.value: timeout
                    for service_type, timeout in self.config.service_timeouts.items()
                }
            },
            'statistics': self.get_statistics(),
            'active_events': [event.to_dict() for event in self.get_active_events()]
        }

        if include_history:
            data['event_history'] = [event.to_dict() for event in self.event_history]

        return data

    def clear_history(self) -> None:
        """清空事件历史记录"""
        with self._lock:
            self.event_history.clear()
            self.logger.info("超时事件历史记录已清空")

    def reset_statistics(self) -> None:
        """重置统计信息"""
        with self._lock:
            self.stats = {
                'total_events': 0,
                'successful_events': 0,
                'timeout_events': 0,
                'cancelled_events': 0,
                'average_duration': 0.0,
                'total_duration': 0.0
            }
            self.logger.info("超时统计信息已重置")