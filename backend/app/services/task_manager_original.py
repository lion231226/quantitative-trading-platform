import asyncio
import uuid
from typing import Dict, Any, Optional, Callable, Awaitable, Any
from datetime import datetime, timedelta
import structlog
from enum import Enum

logger = structlog.get_logger()

class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class TaskManager:
    """异步任务管理器"""

    def __init__(self) -> None:
        self.tasks: Dict[str, Dict[str, Any]] = {}
        self._running_tasks: Dict[str, asyncio.Task[Any]] = {}

    async def create_task(
        self,
        func: Callable[..., Awaitable[Any]],
        *args: Any,
        **kwargs: Any
    ) -> str:
        """创建异步任务"""
        task_id = str(uuid.uuid4())

        task_info = {
            "task_id": task_id,
            "status": TaskStatus.PENDING.value,
            "created_at": datetime.now(),
            "started_at": None,
            "completed_at": None,
            "result": None,
            "error": None,
            "progress": 0.0
        }

        self.tasks[task_id] = task_info

        # 创建并启动异步任务
        async_task = asyncio.create_task(
            self._run_task(task_id, func, *args, **kwargs)
        )
        self._running_tasks[task_id] = async_task

        logger.info("异步任务已创建", task_id=task_id, func=func.__name__)

        return task_id

    async def _run_task(
        self,
        task_id: str,
        func: Callable[..., Awaitable[Any]],
        *args: Any,
        **kwargs: Any
    ) -> Any:
        """执行异步任务"""
        try:
            # 更新任务状态为运行中
            self.tasks[task_id]["status"] = TaskStatus.RUNNING.value
            self.tasks[task_id]["started_at"] = datetime.now()

            logger.info("异步任务开始执行", task_id=task_id, func=func.__name__)

            # 执行函数
            result = await func(*args, **kwargs)

            # 任务完成
            self.tasks[task_id]["status"] = TaskStatus.COMPLETED.value
            self.tasks[task_id]["completed_at"] = datetime.now()
            self.tasks[task_id]["result"] = result
            self.tasks[task_id]["progress"] = 1.0

            logger.info(
                "异步任务执行完成",
                task_id=task_id,
                func=func.__name__,
                duration=(datetime.now() - self.tasks[task_id]["started_at"]).total_seconds()
            )

            return result

        except Exception as e:
            # 任务失败
            self.tasks[task_id]["status"] = TaskStatus.FAILED.value
            self.tasks[task_id]["completed_at"] = datetime.now()
            self.tasks[task_id]["error"] = str(e)

            logger.error(
                "异步任务执行失败",
                task_id=task_id,
                func=func.__name__,
                error=str(e)
            )

            raise

        finally:
            # 清理运行中的任务引用
            if task_id in self._running_tasks:
                del self._running_tasks[task_id]

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        return self.tasks.get(task_id)

    def get_task_result(self, task_id: str) -> Optional[Any]:
        """获取任务结果"""
        task_info = self.tasks.get(task_id)
        if task_info and task_info["status"] == TaskStatus.COMPLETED.value:
            return task_info["result"]
        return None

    async def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        if task_id in self._running_tasks:
            try:
                self._running_tasks[task_id].cancel()
                self.tasks[task_id]["status"] = TaskStatus.FAILED.value
                self.tasks[task_id]["error"] = "Task cancelled"
                self.tasks[task_id]["completed_at"] = datetime.now()

                logger.info("异步任务已取消", task_id=task_id)
                return True
            except Exception as e:
                logger.error("取消异步任务失败", task_id=task_id, error=str(e))
                return False
        return False

    def update_progress(self, task_id: str, progress: float) -> None:
        """更新任务进度"""
        if task_id in self.tasks:
            self.tasks[task_id]["progress"] = min(1.0, max(0.0, progress))

    def get_all_tasks(self) -> Dict[str, Dict[str, Any]]:
        """获取所有任务"""
        return self.tasks.copy()

    def cleanup_completed_tasks(self, older_than_hours: int = 24) -> int:
        """清理已完成的任务"""
        cutoff_time = datetime.now() - timedelta(hours=older_than_hours)
        tasks_to_remove = []

        for task_id, task_info in self.tasks.items():
            if (task_info["status"] in [TaskStatus.COMPLETED.value, TaskStatus.FAILED.value] and
                task_info["completed_at"] and
                task_info["completed_at"] < cutoff_time):
                tasks_to_remove.append(task_id)

        for task_id in tasks_to_remove:
            del self.tasks[task_id]

        logger.info("清理已完成任务", removed_count=len(tasks_to_remove))
        return len(tasks_to_remove)

    async def shutdown(self) -> None:
        """关闭任务管理器"""
        logger.info("正在关闭任务管理器")

        # 取消所有运行中的任务
        for task_id in list(self._running_tasks.keys()):
            await self.cancel_task(task_id)

        logger.info("任务管理器已关闭")

# 全局任务管理器实例
task_manager = TaskManager()