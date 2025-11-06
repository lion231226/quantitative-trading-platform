"""
User Confirmation Module

This module provides user confirmation interfaces for potentially destructive
recovery operations. It supports different confirmation methods including
interactive prompts, timeout-based confirmations, and batch confirmations.
"""

import asyncio
import sys
import time
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import threading
import json

from utils.logger import get_logger

logger = get_logger(__name__)


class ConfirmationType(Enum):
    """确认类型枚举"""
    YES_NO = "yes_no"
    YES_NO_CANCEL = "yes_no_cancel"
    OK_CANCEL = "ok_cancel"
    CONTINUE_STOP = "continue_stop"
    RETRY_SKIP = "retry_skip"
    CUSTOM = "custom"


class ConfirmationMethod(Enum):
    """确认方法枚举"""
    INTERACTIVE = "interactive"
    TIMEOUT = "timeout"
    BATCH = "batch"
    AUTOMATIC = "automatic"
    CALLBACK = "callback"


class ConfirmationResult(Enum):
    """确认结果枚举"""
    YES = "yes"
    NO = "no"
    CANCEL = "cancel"
    OK = "ok"
    CONTINUE = "continue"
    STOP = "stop"
    RETRY = "retry"
    SKIP = "skip"
    TIMEOUT = "timeout"
    CUSTOM = "custom"


@dataclass
class ConfirmationAction:
    """确认操作定义"""
    action_id: str
    title: str
    description: str
    risk_level: str  # "low", "medium", "high", "critical"
    confirm_type: ConfirmationType = ConfirmationType.YES_NO
    method: ConfirmationMethod = ConfirmationMethod.INTERACTIVE
    timeout_seconds: Optional[float] = None
    default_result: Optional[ConfirmationResult] = None
    custom_options: Optional[List[str]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConfirmationResponse:
    """确认响应"""
    action_id: str
    result: ConfirmationResult
    confirmed_at: datetime = field(default_factory=datetime.now)
    response_time: float = 0.0
    user_input: Optional[str] = None
    method_used: ConfirmationMethod = ConfirmationMethod.INTERACTIVE
    timed_out: bool = False
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "action_id": self.action_id,
            "result": self.result.value,
            "confirmed_at": self.confirmed_at.isoformat(),
            "response_time": self.response_time,
            "user_input": self.user_input,
            "method_used": self.method_used.value,
            "timed_out": self.timed_out,
            "details": self.details
        }


class UserConfirmation:
    """用户确认管理器"""

    def __init__(self, auto_confirm_risks: List[str] = None):
        """
        初始化用户确认管理器

        Args:
            auto_confirm_risks: 自动确认的风险级别列表
        """
        self.auto_confirm_risks = auto_confirm_risks or ["low"]
        self.confirmation_history: List[ConfirmationResponse] = []
        self.pending_confirmations: Dict[str, ConfirmationAction] = {}
        self.confirmation_callbacks: Dict[str, Callable] = {}
        self._lock = threading.Lock()

        logger.info(f"UserConfirmation initialized with auto-confirm risks: {self.auto_confirm_risks}")

    async def request_confirmation(self, action: ConfirmationAction) -> ConfirmationResponse:
        """
        请求用户确认

        Args:
            action: 确认操作定义

        Returns:
            ConfirmationResponse: 确认响应
        """
        start_time = time.time()
        logger.info(f"Requesting confirmation for action: {action.action_id}")

        with self._lock:
            self.pending_confirmations[action.action_id] = action

        try:
            # 检查是否应该自动确认
            if self._should_auto_confirm(action):
                result = self._get_auto_confirm_result(action)
                response_time = time.time() - start_time
                response = ConfirmationResponse(
                    action_id=action.action_id,
                    result=result,
                    response_time=response_time,
                    method_used=ConfirmationMethod.AUTOMATIC,
                    details={"auto_confirmed": True, "risk_level": action.risk_level}
                )
                logger.info(f"Auto-confirmed action {action.action_id} with result: {result.value}")
                return response

            # 根据确认方法处理请求
            if action.method == ConfirmationMethod.INTERACTIVE:
                response = await self._handle_interactive_confirmation(action)
            elif action.method == ConfirmationMethod.TIMEOUT:
                response = await self._handle_timeout_confirmation(action)
            elif action.method == ConfirmationMethod.BATCH:
                response = await self._handle_batch_confirmation(action)
            elif action.method == ConfirmationMethod.CALLBACK:
                response = await self._handle_callback_confirmation(action)
            else:
                raise ValueError(f"Unsupported confirmation method: {action.method}")

            response_time = time.time() - start_time
            response.response_time = response_time

            # 记录确认历史
            with self._lock:
                self.confirmation_history.append(response)
                if action.action_id in self.pending_confirmations:
                    del self.pending_confirmations[action.action_id]

            logger.info(f"Confirmation completed for {action.action_id}: {response.result.value}")
            return response

        except Exception as e:
            logger.error(f"Error during confirmation for {action.action_id}: {str(e)}")
            response_time = time.time() - start_time
            response = ConfirmationResponse(
                action_id=action.action_id,
                result=ConfirmationResult.CANCEL,
                response_time=response_time,
                method_used=action.method,
                details={"error": str(e)}
            )
            return response

    def _should_auto_confirm(self, action: ConfirmationAction) -> bool:
        """检查是否应该自动确认"""
        return action.risk_level in self.auto_confirm_risks

    def _get_auto_confirm_result(self, action: ConfirmationAction) -> ConfirmationResult:
        """获取自动确认结果"""
        if action.default_result:
            return action.default_result

        # 根据确认类型返回默认结果
        if action.confirm_type == ConfirmationType.YES_NO:
            return ConfirmationResult.YES
        elif action.confirm_type == ConfirmationType.YES_NO_CANCEL:
            return ConfirmationResult.YES
        elif action.confirm_type == ConfirmationType.OK_CANCEL:
            return ConfirmationResult.OK
        elif action.confirm_type == ConfirmationType.CONTINUE_STOP:
            return ConfirmationResult.CONTINUE
        elif action.confirm_type == ConfirmationType.RETRY_SKIP:
            return ConfirmationResult.RETRY
        else:
            return ConfirmationResult.YES

    async def _handle_interactive_confirmation(self, action: ConfirmationAction) -> ConfirmationResponse:
        """处理交互式确认"""
        print(f"\n{'='*60}")
        print(f"🔔 需要确认: {action.title}")
        print(f"📝 描述: {action.description}")
        print(f"⚠️  风险级别: {action.risk_level.upper()}")
        print(f"{'='*60}")

        # 根据确认类型显示选项
        if action.confirm_type == ConfirmationType.YES_NO:
            options = ["yes", "no"]
            prompt = "请确认 (yes/no): "
        elif action.confirm_type == ConfirmationType.YES_NO_CANCEL:
            options = ["yes", "no", "cancel"]
            prompt = "请确认 (yes/no/cancel): "
        elif action.confirm_type == ConfirmationType.OK_CANCEL:
            options = ["ok", "cancel"]
            prompt = "请确认 (ok/cancel): "
        elif action.confirm_type == ConfirmationType.CONTINUE_STOP:
            options = ["continue", "stop"]
            prompt = "请确认 (continue/stop): "
        elif action.confirm_type == ConfirmationType.RETRY_SKIP:
            options = ["retry", "skip"]
            prompt = "请确认 (retry/skip): "
        elif action.confirm_type == ConfirmationType.CUSTOM and action.custom_options:
            options = action.custom_options
            prompt = f"请选择 ({'/'.join(options)}): "
        else:
            options = ["yes", "no"]
            prompt = "请确认 (yes/no): "

        # 获取用户输入
        while True:
            try:
                user_input = input(prompt).strip().lower()

                if user_input in options:
                    result = ConfirmationResult(user_input)
                    break
                elif not user_input and action.default_result:
                    result = action.default_result
                    break
                else:
                    print(f"无效输入，请选择: {', '.join(options)}")
            except (KeyboardInterrupt, EOFError):
                print("\n操作被取消")
                result = ConfirmationResult.CANCEL
                break

        return ConfirmationResponse(
            action_id=action.action_id,
            result=result,
            user_input=user_input,
            method_used=ConfirmationMethod.INTERACTIVE
        )

    async def _handle_timeout_confirmation(self, action: ConfirmationAction) -> ConfirmationResponse:
        """处理超时确认"""
        if not action.timeout_seconds:
            # 如果没有设置超时，回退到交互式确认
            return await self._handle_interactive_confirmation(action)

        print(f"\n{'='*60}")
        print(f"⏰ 需要确认 (超时: {action.timeout_seconds}秒): {action.title}")
        print(f"📝 描述: {action.description}")
        print(f"⚠️  风险级别: {action.risk_level.upper()}")
        print(f"{'='*60}")

        # 显示默认结果
        default_text = action.default_result.value if action.default_result else "cancel"
        print(f"默认结果 (超时): {default_text}")

        # 根据确认类型显示选项
        if action.confirm_type == ConfirmationType.YES_NO:
            prompt = "请确认 (yes/no): "
        elif action.confirm_type == ConfirmationType.YES_NO_CANCEL:
            prompt = "请确认 (yes/no/cancel): "
        else:
            prompt = "请确认: "

        try:
            # 使用 asyncio.wait_for 实现超时
            user_input = await asyncio.wait_for(
                self._get_input_async(prompt),
                timeout=action.timeout_seconds
            )

            # 验证用户输入
            if self._validate_input(user_input, action):
                result = ConfirmationResult(user_input.lower())
                return ConfirmationResponse(
                    action_id=action.action_id,
                    result=result,
                    user_input=user_input,
                    method_used=ConfirmationMethod.TIMEOUT
                )
            else:
                print(f"无效输入，使用默认结果: {default_text}")
                result = action.default_result or ConfirmationResult.CANCEL
                return ConfirmationResponse(
                    action_id=action.action_id,
                    result=result,
                    user_input=user_input,
                    method_used=ConfirmationMethod.TIMEOUT,
                    details={"invalid_input": True}
                )

        except asyncio.TimeoutError:
            print(f"\n⏰ 超时，使用默认结果: {default_text}")
            result = action.default_result or ConfirmationResult.CANCEL
            return ConfirmationResponse(
                action_id=action.action_id,
                result=result,
                method_used=ConfirmationMethod.TIMEOUT,
                timed_out=True
            )

    async def _handle_batch_confirmation(self, actions: List[ConfirmationAction]) -> List[ConfirmationResponse]:
        """处理批量确认"""
        print(f"\n{'='*60}")
        print(f"📋 批量确认 ({len(actions)} 个操作)")
        print(f"{'='*60}")

        # 显示所有操作摘要
        for i, action in enumerate(actions, 1):
            risk_icon = {"low": "🟢", "medium": "🟡", "high": "🟠", "critical": "🔴"}.get(action.risk_level, "⚪")
            print(f"{i}. {risk_icon} {action.title}")
            print(f"   {action.description}")
            print(f"   风险: {action.risk_level}")
            print()

        # 询问批量确认
        print("选项:")
        print("  all     - 确认所有操作")
        print("  none    - 拒绝所有操作")
        print("  selective - 选择性确认")
        print("  cancel  - 取消操作")

        while True:
            try:
                choice = input("请选择 (all/none/selective/cancel): ").strip().lower()

                if choice == "all":
                    return [ConfirmationResponse(
                        action_id=action.action_id,
                        result=self._get_auto_confirm_result(action),
                        method_used=ConfirmationMethod.BATCH,
                        details={"batch_choice": "all"}
                    ) for action in actions]

                elif choice == "none":
                    return [ConfirmationResponse(
                        action_id=action.action_id,
                        result=ConfirmationResult.NO,
                        method_used=ConfirmationMethod.BATCH,
                        details={"batch_choice": "none"}
                    ) for action in actions]

                elif choice == "selective":
                    return await self._handle_selective_confirmation(actions)

                elif choice == "cancel":
                    return [ConfirmationResponse(
                        action_id=action.action_id,
                        result=ConfirmationResult.CANCEL,
                        method_used=ConfirmationMethod.BATCH,
                        details={"batch_choice": "cancel"}
                    ) for action in actions]

                else:
                    print("无效输入，请选择: all, none, selective, cancel")

            except (KeyboardInterrupt, EOFError):
                print("\n操作被取消")
                return [ConfirmationResponse(
                    action_id=action.action_id,
                    result=ConfirmationResult.CANCEL,
                    method_used=ConfirmationMethod.BATCH,
                    details={"interrupted": True}
                ) for action in actions]

    async def _handle_selective_confirmation(self, actions: List[ConfirmationAction]) -> List[ConfirmationResponse]:
        """处理选择性确认"""
        print("\n选择性确认:")
        print("输入要确认的操作编号，用逗号分隔 (例如: 1,3,5)")
        print("或者输入 'all' 确认所有操作")

        while True:
            try:
                user_input = input("请选择: ").strip().lower()

                if user_input == "all":
                    selected_actions = actions
                else:
                    try:
                        indices = [int(x.strip()) - 1 for x in user_input.split(",")]
                        selected_actions = [actions[i] for i in indices if 0 <= i < len(actions)]
                    except ValueError:
                        print("无效输入，请输入正确的编号")
                        continue

                # 逐个确认选中的操作
                responses = []
                for action in actions:
                    if action in selected_actions:
                        # 确认选中的操作
                        response = await self._handle_interactive_confirmation(action)
                        response.method_used = ConfirmationMethod.BATCH
                        response.details["selective_choice"] = "confirmed"
                    else:
                        # 拒绝未选中的操作
                        response = ConfirmationResponse(
                            action_id=action.action_id,
                            result=ConfirmationResult.NO,
                            method_used=ConfirmationMethod.BATCH,
                            details={"selective_choice": "rejected"}
                        )
                    responses.append(response)

                return responses

            except (KeyboardInterrupt, EOFError):
                print("\n操作被取消")
                return [ConfirmationResponse(
                    action_id=action.action_id,
                    result=ConfirmationResult.CANCEL,
                    method_used=ConfirmationMethod.BATCH,
                    details={"interrupted": True}
                ) for action in actions]

    async def _handle_callback_confirmation(self, action: ConfirmationAction) -> ConfirmationResponse:
        """处理回调确认"""
        callback = self.confirmation_callbacks.get(action.action_id)
        if not callback:
            logger.warning(f"No callback found for action {action.action_id}")
            # 回退到交互式确认
            return await self._handle_interactive_confirmation(action)

        try:
            # 调用回调函数
            if asyncio.iscoroutinefunction(callback):
                result = await callback(action)
            else:
                result = callback(action)

            # 验证回调结果
            if isinstance(result, ConfirmationResult):
                return ConfirmationResponse(
                    action_id=action.action_id,
                    result=result,
                    method_used=ConfirmationMethod.CALLBACK
                )
            elif isinstance(result, str) and result in [r.value for r in ConfirmationResult]:
                return ConfirmationResponse(
                    action_id=action.action_id,
                    result=ConfirmationResult(result),
                    method_used=ConfirmationMethod.CALLBACK
                )
            else:
                logger.warning(f"Invalid callback result for {action.action_id}: {result}")
                # 回退到交互式确认
                return await self._handle_interactive_confirmation(action)

        except Exception as e:
            logger.error(f"Callback confirmation failed for {action.action_id}: {str(e)}")
            # 回退到交互式确认
            return await self._handle_interactive_confirmation(action)

    async def _get_input_async(self, prompt: str) -> str:
        """异步获取用户输入"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, input, prompt)

    def _validate_input(self, user_input: str, action: ConfirmationAction) -> bool:
        """验证用户输入"""
        if not user_input:
            return False

        user_input = user_input.lower()

        if action.confirm_type == ConfirmationType.YES_NO:
            return user_input in ["yes", "y", "no", "n"]
        elif action.confirm_type == ConfirmationType.YES_NO_CANCEL:
            return user_input in ["yes", "y", "no", "n", "cancel", "c"]
        elif action.confirm_type == ConfirmationType.OK_CANCEL:
            return user_input in ["ok", "k", "cancel", "c"]
        elif action.confirm_type == ConfirmationType.CONTINUE_STOP:
            return user_input in ["continue", "cont", "stop", "s"]
        elif action.confirm_type == ConfirmationType.RETRY_SKIP:
            return user_input in ["retry", "r", "skip", "s"]
        elif action.confirm_type == ConfirmationType.CUSTOM and action.custom_options:
            return user_input in [opt.lower() for opt in action.custom_options]
        else:
            return user_input in ["yes", "y", "no", "n"]

    def register_callback(self, action_id: str, callback: Callable):
        """注册确认回调函数"""
        self.confirmation_callbacks[action_id] = callback
        logger.info(f"Registered confirmation callback for action: {action_id}")

    def unregister_callback(self, action_id: str):
        """注销确认回调函数"""
        if action_id in self.confirmation_callbacks:
            del self.confirmation_callbacks[action_id]
            logger.info(f"Unregistered confirmation callback for action: {action_id}")

    def get_confirmation_history(self, action_id: Optional[str] = None, limit: Optional[int] = None) -> List[ConfirmationResponse]:
        """获取确认历史记录"""
        with self._lock:
            history = self.confirmation_history

            if action_id:
                history = [r for r in history if r.action_id == action_id]

            if limit:
                history = history[-limit:]

            return history.copy()

    def get_pending_confirmations(self) -> Dict[str, ConfirmationAction]:
        """获取待处理的确认操作"""
        with self._lock:
            return self.pending_confirmations.copy()

    def get_confirmation_statistics(self) -> Dict[str, Any]:
        """获取确认统计信息"""
        with self._lock:
            total_confirmations = len(self.confirmation_history)
            if total_confirmations == 0:
                return {
                    "total_confirmations": 0,
                    "by_result": {},
                    "by_method": {},
                    "by_risk_level": {},
                    "average_response_time": 0.0,
                    "timeout_rate": 0.0
                }

            # 按结果统计
            by_result = {}
            for response in self.confirmation_history:
                result = response.result.value
                by_result[result] = by_result.get(result, 0) + 1

            # 按方法统计
            by_method = {}
            for response in self.confirmation_history:
                method = response.method_used.value
                by_method[method] = by_method.get(method, 0) + 1

            # 按风险级别统计
            by_risk_level = {}
            for response in self.confirmation_history:
                risk_level = response.details.get("risk_level", "unknown")
                by_risk_level[risk_level] = by_risk_level.get(risk_level, 0) + 1

            # 计算平均响应时间
            avg_response_time = sum(r.response_time for r in self.confirmation_history) / total_confirmations

            # 计算超时率
            timeout_count = sum(1 for r in self.confirmation_history if r.timed_out)
            timeout_rate = timeout_count / total_confirmations

            return {
                "total_confirmations": total_confirmations,
                "by_result": by_result,
                "by_method": by_method,
                "by_risk_level": by_risk_level,
                "average_response_time": avg_response_time,
                "timeout_rate": timeout_rate,
                "pending_confirmations": len(self.pending_confirmations)
            }

    def set_auto_confirm_risks(self, risk_levels: List[str]):
        """设置自动确认的风险级别"""
        self.auto_confirm_risks = risk_levels
        logger.info(f"Updated auto-confirm risks: {self.auto_confirm_risks}")


# 便捷函数
async def confirm_action(
    title: str,
    description: str,
    risk_level: str = "medium",
    confirm_type: ConfirmationType = ConfirmationType.YES_NO,
    timeout: Optional[float] = None,
    auto_confirm: bool = False
) -> ConfirmationResult:
    """
    便捷函数：请求用户确认

    Args:
        title: 操作标题
        description: 操作描述
        risk_level: 风险级别
        confirm_type: 确认类型
        timeout: 超时时间（秒）
        auto_confirm: 是否自动确认

    Returns:
        ConfirmationResult: 确认结果
    """
    confirmation = UserConfirmation(auto_confirm_risks=["low", "medium"] if auto_confirm else [])

    action = ConfirmationAction(
        action_id=f"quick_confirm_{int(time.time())}",
        title=title,
        description=description,
        risk_level=risk_level,
        confirm_type=confirm_type,
        method=ConfirmationMethod.TIMEOUT if timeout else ConfirmationMethod.INTERACTIVE,
        timeout_seconds=timeout
    )

    response = await confirmation.request_confirmation(action)
    return response.result


async def confirm_destructive_action(
    operation: str,
    target: str,
    details: str = "",
    timeout: float = 30.0
) -> bool:
    """
    便捷函数：确认破坏性操作

    Args:
        operation: 操作类型
        target: 操作目标
        details: 详细信息
        timeout: 超时时间

    Returns:
        bool: 是否确认执行
    """
    title = f"破坏性操作确认: {operation}"
    description = f"目标: {target}"
    if details:
        description += f"\n详细信息: {details}"

    result = await confirm_action(
        title=title,
        description=description,
        risk_level="high",
        confirm_type=ConfirmationType.YES_NO,
        timeout=timeout
    )

    return result == ConfirmationResult.YES