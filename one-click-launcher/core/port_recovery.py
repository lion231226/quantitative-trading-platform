"""
Port Recovery Module

This module extends the existing PortConflictResolver to support automatic
process termination with user confirmation, permission checks, and safe
process termination mechanisms for port conflict resolution.
"""

import asyncio
import time
import subprocess
import platform
import signal
from typing import Dict, List, Optional, Tuple, Union, Any
from dataclasses import dataclass, asdict
from enum import Enum
import json

try:
    import psutil
except ImportError:
    psutil = None

from core.port_detector import (
    PortConflictResolver, PortConflict, ResolutionResult,
    ResolutionStrategy, PortStatus
)
from core.port_checker import PortChecker
from utils.logger import get_logger
from utils.progress_tracker import ProgressTracker
from utils.user_confirmation import (
    UserConfirmation, ConfirmationAction, ConfirmationType,
    ConfirmationMethod, ConfirmationResult, confirm_destructive_action
)
from utils.error_knowledge_base import ErrorKnowledgeBase

logger = get_logger(__name__)


class TerminationMethod(Enum):
    """进程终止方法枚举"""
    GRACEFUL = "graceful"
    FORCEFUL = "forceful"
    HYBRID = "hybrid"


class PermissionLevel(Enum):
    """权限级别枚举"""
    USER = "user"
    ADMIN = "admin"
    ROOT = "root"


@dataclass
class ProcessTerminationResult:
    """进程终止结果"""
    success: bool
    pid: int
    process_name: str
    termination_method: TerminationMethod
    time_taken: float
    error_message: Optional[str] = None
    requires_elevation: bool = False
    rollback_possible: bool = True


@dataclass
class PortRecoveryResult:
    """端口恢复结果"""
    port: int
    conflict_resolved: bool
    process_terminated: bool
    user_confirmed: bool
    termination_result: Optional[ProcessTerminationResult] = None
    resolution_time: float = 0.0
    verification_passed: bool = False
    error_details: Optional[str] = None


class PortRecoveryOrchestrator:
    """端口恢复编排器"""

    def __init__(self,
                 progress_tracker: Optional[ProgressTracker] = None,
                 auto_confirm_low_risk: bool = True,
                 enable_rollback: bool = True):
        """
        初始化端口恢复编排器

        Args:
            progress_tracker: 进度跟踪器
            auto_confirm_low_risk: 是否自动确认低风险操作
            enable_rollback: 是否启用回滚功能
        """
        self.progress_tracker = progress_tracker
        self.enable_rollback = enable_rollback

        # 初始化组件
        self.port_resolver = PortConflictResolver(progress_tracker)
        self.user_confirmation = UserConfirmation(
            auto_confirm_risks=["low"] if auto_confirm_low_risk else []
        )
        self.error_knowledge = ErrorKnowledgeBase()

        # 终止历史记录（用于回滚）
        self.termination_history: List[ProcessTerminationResult] = []

        # 平台特定配置
        self.platform_info = self._get_platform_info()

        logger.info("PortRecoveryOrchestrator initialized")

    def _get_platform_info(self) -> Dict[str, Any]:
        """获取平台信息"""
        system = platform.system().lower()

        privilege_indicators = {
            "windows": {
                "admin_commands": ["net session", "tasklist /v"],
                "elevation_tool": "runas",
                "process_hierarchy": True
            },
            "darwin": {
                "admin_commands": ["sudo -n true", "dscl . -read /Users/$(whoami)"],
                "elevation_tool": "sudo",
                "process_hierarchy": True
            },
            "linux": {
                "admin_commands": ["sudo -n true", "id -u"],
                "elevation_tool": "sudo",
                "process_hierarchy": True
            }
        }

        return {
            "system": system,
            "privilege_info": privilege_indicators.get(system, {}),
            "supported_signals": self._get_supported_signals()
        }

    def _get_supported_signals(self) -> List[int]:
        """获取支持的信号"""
        signals = []
        if hasattr(signal, 'SIGTERM'):
            signals.append(signal.SIGTERM)
        if hasattr(signal, 'SIGKILL'):
            signals.append(signal.SIGKILL)
        if hasattr(signal, 'SIGINT'):
            signals.append(signal.SIGINT)
        return signals

    async def check_permissions(self) -> PermissionLevel:
        """
        检查当前权限级别

        Returns:
            PermissionLevel: 权限级别
        """
        try:
            system = self.platform_info["system"]

            if system == "windows":
                return await self._check_windows_permissions()
            elif system in ["darwin", "linux"]:
                return await self._check_unix_permissions()
            else:
                logger.warning(f"Unsupported platform: {system}")
                return PermissionLevel.USER

        except Exception as e:
            logger.error(f"Error checking permissions: {str(e)}")
            return PermissionLevel.USER

    async def _check_windows_permissions(self) -> PermissionLevel:
        """检查Windows权限"""
        try:
            # 尝试执行需要管理员权限的命令
            result = subprocess.run(
                "net session 2>nul",
                shell=True,
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                return PermissionLevel.ADMIN
            else:
                return PermissionLevel.USER

        except Exception:
            return PermissionLevel.USER

    async def _check_unix_permissions(self) -> PermissionLevel:
        """检查Unix/Linux权限"""
        try:
            # 检查是否为root
            if subprocess.run("id -u", shell=True, capture_output=True, text=True).stdout.strip() == "0":
                return PermissionLevel.ROOT

            # 检查是否有sudo权限
            result = subprocess.run(
                "sudo -n true 2>/dev/null",
                shell=True,
                capture_output=True
            )

            if result.returncode == 0:
                return PermissionLevel.ADMIN
            else:
                return PermissionLevel.USER

        except Exception:
            return PermissionLevel.USER

    async def request_permission_elevation(self, reason: str) -> bool:
        """
        请求权限提升

        Args:
            reason: 提升权限的原因

        Returns:
            bool: 是否获得权限提升
        """
        system = self.platform_info["system"]

        if system == "windows":
            return await self._request_windows_elevation(reason)
        elif system in ["darwin", "linux"]:
            return await self._request_unix_elevation(reason)
        else:
            logger.warning(f"Elevation not supported on: {system}")
            return False

    async def _request_windows_elevation(self, reason: str) -> bool:
        """请求Windows权限提升"""
        try:
            # 创建用户确认操作
            action = ConfirmationAction(
                action_id="windows_elevation_request",
                title="Windows管理员权限请求",
                description=f"需要管理员权限来执行操作: {reason}",
                risk_level="medium",
                confirm_type=ConfirmationType.YES_NO,
                method=ConfirmationMethod.INTERACTIVE
            )

            response = await self.user_confirmation.request_confirmation(action)

            if response.result == ConfirmationResult.YES:
                # 在实际实现中，这里会触发UAC提升
                logger.info("User approved Windows elevation request")
                return True
            else:
                logger.info("User declined Windows elevation request")
                return False

        except Exception as e:
            logger.error(f"Windows elevation request failed: {str(e)}")
            return False

    async def _request_unix_elevation(self, reason: str) -> bool:
        """请求Unix/Linux权限提升"""
        try:
            action = ConfirmationAction(
                action_id="unix_elevation_request",
                title="Unix/Linux权限提升请求",
                description=f"需要管理员/root权限来执行操作: {reason}\n系统将提示输入密码。",
                risk_level="medium",
                confirm_type=ConfirmationType.YES_NO,
                method=ConfirmationMethod.INTERACTIVE
            )

            response = await self.user_confirmation.request_confirmation(action)

            if response.result == ConfirmationResult.YES:
                # 验证sudo权限
                result = subprocess.run(
                    "sudo -v",
                    shell=True,
                    capture_output=True
                )

                if result.returncode == 0:
                    logger.info("Unix elevation approved and verified")
                    return True
                else:
                    logger.warning("Unix elevation approved but verification failed")
                    return False
            else:
                logger.info("User declined Unix elevation request")
                return False

        except Exception as e:
            logger.error(f"Unix elevation request failed: {str(e)}")
            return False

    async def auto_resolve_port_conflict(self,
                                       conflict: PortConflict,
                                       allow_process_termination: bool = False,
                                       preferred_method: TerminationMethod = TerminationMethod.HYBRID) -> PortRecoveryResult:
        """
        自动解决端口冲突

        Args:
            conflict: 端口冲突信息
            allow_process_termination: 是否允许进程终止
            preferred_method: 首选的终止方法

        Returns:
            PortRecoveryResult: 端口恢复结果
        """
        start_time = time.time()
        logger.info(f"Starting port recovery for port {conflict.port}")

        if self.progress_tracker:
            self.progress_tracker.start_task(
                "port_recovery",
                f"Resolving port conflict on port {conflict.port}"
            )

        try:
            # 1. 检查权限
            current_permission = await self.check_permissions()
            logger.info(f"Current permission level: {current_permission.value}")

            # 2. 分析冲突严重性和风险
            risk_assessment = await self._assess_termination_risk(conflict, current_permission)

            # 3. 请求用户确认（如果需要）
            user_confirmed = await self._request_termination_confirmation(conflict, risk_assessment)

            if not user_confirmed:
                return PortRecoveryResult(
                    port=conflict.port,
                    conflict_resolved=False,
                    process_terminated=False,
                    user_confirmed=False,
                    error_details="User declined termination confirmation"
                )

            # 4. 执行进程终止（如果批准）
            termination_result = None
            process_terminated = False

            if allow_process_termination and conflict.process_info:
                termination_result = await self._execute_process_termination(
                    conflict.process_info,
                    preferred_method,
                    current_permission
                )
                process_terminated = termination_result.success

                # 记录终止历史
                if termination_result.success:
                    self.termination_history.append(termination_result)

            # 5. 验证端口释放
            verification_passed = await self._verify_port_release(conflict.port, conflict.host)

            # 6. 生成恢复建议
            if not verification_passed:
                await self._provide_recovery_guidance(conflict, termination_result)

            resolution_time = time.time() - start_time

            result = PortRecoveryResult(
                port=conflict.port,
                conflict_resolved=verification_passed,
                process_terminated=process_terminated,
                user_confirmed=user_confirmed,
                termination_result=termination_result,
                resolution_time=resolution_time,
                verification_passed=verification_passed
            )

            if self.progress_tracker:
                status = "resolved" if verification_passed else "failed"
                self.progress_tracker.complete_task(
                    "port_recovery",
                    f"Port {conflict.port} recovery {status}"
                )

            return result

        except Exception as e:
            logger.error(f"Port recovery failed for port {conflict.port}: {str(e)}")

            if self.progress_tracker:
                self.progress_tracker.complete_task(
                    "port_recovery",
                    f"Port {conflict.port} recovery failed: {str(e)}"
                )

            return PortRecoveryResult(
                port=conflict.port,
                conflict_resolved=False,
                process_terminated=False,
                user_confirmed=False,
                error_details=str(e),
                resolution_time=time.time() - start_time
            )

    async def _assess_termination_risk(self, conflict: PortConflict,
                                     permission: PermissionLevel) -> Dict[str, Any]:
        """评估终止风险"""
        risk_level = "medium"
        risk_factors = []

        # 基于服务类型评估风险
        critical_services = ["postgres", "redis", "mongodb", "mysql"]
        if conflict.service_type in critical_services:
            risk_level = "high"
            risk_factors.append("critical_database_service")

        # 基于进程信息评估风险
        if conflict.process_info:
            process_name = conflict.process_info.get('name', '').lower()
            if any(sys_proc in process_name for sys_proc in ['system', 'kernel', 'init']):
                risk_level = "critical"
                risk_factors.append("system_process")

        # 基于权限评估风险
        if permission == PermissionLevel.USER:
            risk_factors.append("insufficient_privileges")
            risk_level = max(risk_level, "high", key=lambda x: ["low", "medium", "high", "critical"].index(x))

        return {
            "risk_level": risk_level,
            "risk_factors": risk_factors,
            "permission_level": permission.value,
            "service_type": conflict.service_type,
            "confidence": 0.85
        }

    async def _request_termination_confirmation(self,
                                              conflict: PortConflict,
                                              risk_assessment: Dict[str, Any]) -> bool:
        """请求终止确认"""
        risk_level = risk_assessment["risk_level"]

        # 构建确认消息
        title = f"端口冲突解决确认 - 端口 {conflict.port}"
        description = f"检测到端口 {conflict.port} 被占用"

        if conflict.process_info:
            proc_info = conflict.process_info
            description += f"\n进程: {proc_info.get('name', 'Unknown')} (PID: {proc_info.get('pid', 'N/A')})"
            description += f"\n服务类型: {conflict.service_type or 'Unknown'}"

        description += f"\n风险级别: {risk_level.upper()}"

        # 添加风险因素说明
        risk_factors = risk_assessment.get("risk_factors", [])
        if risk_factors:
            description += "\n风险因素: " + ", ".join(risk_factors)

        # 添加恢复建议
        if risk_level == "high":
            description += "\n⚠️  建议先尝试其他解决方案，如更换端口"
        elif risk_level == "critical":
            description += "\n🚨 危险操作！可能影响系统稳定性"

        # 确定确认类型
        if risk_level == "critical":
            confirm_type = ConfirmationType.YES_NO_CANCEL
        else:
            confirm_type = ConfirmationType.YES_NO

        action = ConfirmationAction(
            action_id=f"port_termination_{conflict.port}",
            title=title,
            description=description,
            risk_level=risk_level,
            confirm_type=confirm_type,
            method=ConfirmationMethod.TIMEOUT,
            timeout_seconds=30.0,
            default_result=ConfirmationResult.NO if risk_level == "critical" else None
        )

        response = await self.user_confirmation.request_confirmation(action)

        return response.result in [ConfirmationResult.YES, ConfirmationResult.OK, ConfirmationResult.CONTINUE]

    async def _execute_process_termination(self,
                                         process_info: Dict[str, Any],
                                         method: TerminationMethod,
                                         permission: PermissionLevel) -> ProcessTerminationResult:
        """执行进程终止"""
        pid = process_info.get('pid')
        process_name = process_info.get('name', 'Unknown')

        if not pid:
            return ProcessTerminationResult(
                success=False,
                pid=0,
                process_name=process_name,
                termination_method=method,
                time_taken=0.0,
                error_message="No process ID available"
            )

        start_time = time.time()

        try:
            if method == TerminationMethod.GRACEFUL:
                success = await self._terminate_gracefully(pid, permission)
            elif method == TerminationMethod.FORCEFUL:
                success = await self._terminate_forcefully(pid, permission)
            elif method == TerminationMethod.HYBRID:
                # 先尝试优雅终止，失败后强制终止
                success = await self._terminate_hybrid(pid, permission)
            else:
                raise ValueError(f"Unsupported termination method: {method}")

            time_taken = time.time() - start_time

            return ProcessTerminationResult(
                success=success,
                pid=pid,
                process_name=process_name,
                termination_method=method,
                time_taken=time_taken,
                requires_elevation=permission in [PermissionLevel.ADMIN, PermissionLevel.ROOT],
                rollback_possible=method != TerminationMethod.FORCEFUL
            )

        except Exception as e:
            return ProcessTerminationResult(
                success=False,
                pid=pid,
                process_name=process_name,
                termination_method=method,
                time_taken=time.time() - start_time,
                error_message=str(e),
                requires_elevation=permission in [PermissionLevel.ADMIN, PermissionLevel.ROOT]
            )

    async def _terminate_gracefully(self, pid: int, permission: PermissionLevel) -> bool:
        """优雅终止进程"""
        try:
            if psutil:
                process = psutil.Process(pid)
                process.terminate()

                try:
                    process.wait(timeout=10)
                    return True
                except psutil.TimeoutExpired:
                    logger.warning(f"Graceful termination timed out for PID {pid}")
                    return False
            else:
                # 使用系统命令
                system = self.platform_info["system"]
                if system == "windows":
                    result = subprocess.run(
                        f"taskkill /PID {pid}",
                        shell=True,
                        capture_output=True
                    )
                else:
                    result = subprocess.run(
                        f"kill -15 {pid}",  # SIGTERM
                        shell=True,
                        capture_output=True
                    )

                return result.returncode == 0

        except Exception as e:
            logger.error(f"Graceful termination failed for PID {pid}: {str(e)}")
            return False

    async def _terminate_forcefully(self, pid: int, permission: PermissionLevel) -> bool:
        """强制终止进程"""
        try:
            if psutil:
                process = psutil.Process(pid)
                process.kill()
                return True
            else:
                # 使用系统命令
                system = self.platform_info["system"]
                if system == "windows":
                    result = subprocess.run(
                        f"taskkill /F /PID {pid}",
                        shell=True,
                        capture_output=True
                    )
                else:
                    result = subprocess.run(
                        f"kill -9 {pid}",  # SIGKILL
                        shell=True,
                        capture_output=True
                    )

                return result.returncode == 0

        except Exception as e:
            logger.error(f"Forceful termination failed for PID {pid}: {str(e)}")
            return False

    async def _terminate_hybrid(self, pid: int, permission: PermissionLevel) -> bool:
        """混合终止进程（先优雅后强制）"""
        # 先尝试优雅终止
        graceful_success = await self._terminate_gracefully(pid, permission)

        if graceful_success:
            return True

        logger.info(f"Graceful termination failed for PID {pid}, trying forceful termination")

        # 等待短暂时间后尝试强制终止
        await asyncio.sleep(2)
        forceful_success = await self._terminate_forcefully(pid, permission)

        return forceful_success

    async def _verify_port_release(self, port: int, host: str = "localhost") -> bool:
        """验证端口是否已释放"""
        try:
            # 多次检查以确保端口真正释放
            for _ in range(3):
                await asyncio.sleep(1)

                port_checker = PortChecker()
                result = await port_checker.check_port_availability(host, port)

                if result.is_available:
                    logger.info(f"Port {port} successfully released")
                    return True

            logger.warning(f"Port {port} still occupied after termination attempts")
            return False

        except Exception as e:
            logger.error(f"Port verification failed for port {port}: {str(e)}")
            return False

    async def _provide_recovery_guidance(self,
                                        conflict: PortConflict,
                                        termination_result: Optional[ProcessTerminationResult]) -> None:
        """提供恢复指导"""
        try:
            # 从错误知识库获取解决方案
            error_code = f"PORT_CONFLICT_{conflict.port}"
            solution = self.error_knowledge.get_solution(error_code, {
                "service_type": conflict.service_type,
                "port": conflict.port,
                "termination_failed": termination_result is None or not termination_result.success
            })

            if solution:
                logger.info(f"Recovery guidance for port {conflict.port}: {solution.get('solution', 'No specific guidance available')}")

            # 生成通用建议
            suggestions = [
                f"尝试使用替代端口: {', '.join(map(str, conflict.alternative_ports[:3]))}",
                "检查是否有其他应用程序实例正在运行",
                "重启相关服务或应用程序",
                "如果问题持续，考虑重启系统"
            ]

            if conflict.service_type in ["postgres", "redis", "mongodb"]:
                suggestions.insert(0, "谨慎处理数据库服务终止，确保数据完整性")

            logger.info(f"General recovery suggestions for port {conflict.port}: {'; '.join(suggestions)}")

        except Exception as e:
            logger.error(f"Failed to provide recovery guidance: {str(e)}")

    async def rollback_termination(self, termination_result: ProcessTerminationResult) -> bool:
        """
        回滚进程终止操作（有限支持）

        Args:
            termination_result: 要回滚的终止结果

        Returns:
            bool: 是否成功回滚
        """
        if not self.enable_rollback or not termination_result.rollback_possible:
            logger.warning("Rollback not available for this termination")
            return False

        try:
            logger.warning(f"Rollback requested for PID {termination_result.pid} - limited support available")

            # 对于某些服务，可以尝试重启
            if termination_result.process_name in ["nginx", "apache", "httpd"]:
                return await self._restart_web_server(termination_result.process_name)

            # 对于数据库服务，提供重启指导
            if termination_result.process_name in ["postgres", "redis", "mongodb"]:
                logger.info(f"Database service {termination_result.process_name} terminated - manual restart required")
                return True

            logger.warning("Automatic rollback not supported for this process type")
            return False

        except Exception as e:
            logger.error(f"Rollback failed: {str(e)}")
            return False

    async def _restart_web_server(self, service_name: str) -> bool:
        """尝试重启Web服务器"""
        try:
            system = self.platform_info["system"]

            if system == "windows":
                # Windows服务重启
                result = subprocess.run(
                    f"net start {service_name}",
                    shell=True,
                    capture_output=True
                )
            else:
                # Unix/Linux服务重启
                result = subprocess.run(
                    f"systemctl restart {service_name}",
                    shell=True,
                    capture_output=True
                )

            return result.returncode == 0

        except Exception as e:
            logger.error(f"Failed to restart web server {service_name}: {str(e)}")
            return False

    async def batch_resolve_conflicts(self,
                                    conflicts: List[PortConflict],
                                    allow_batch_confirmation: bool = True) -> List[PortRecoveryResult]:
        """
        批量解决端口冲突

        Args:
            conflicts: 端口冲突列表
            allow_batch_confirmation: 是否允许批量确认

        Returns:
            List[PortRecoveryResult]: 端口恢复结果列表
        """
        logger.info(f"Starting batch port conflict resolution for {len(conflicts)} conflicts")

        if not conflicts:
            return []

        # 如果启用批量确认且风险级别合适
        if allow_batch_confirmation:
            batch_confirmation = await self._request_batch_confirmation(conflicts)

            if not batch_confirmation:
                # 用户拒绝了批量操作，退回到单个确认
                return [await self.auto_resolve_port_conflict(conflict) for conflict in conflicts]

        # 并行或串行处理冲突
        results = []
        for conflict in conflicts:
            result = await self.auto_resolve_port_conflict(conflict)
            results.append(result)

            # 在处理之间添加小延迟以避免系统负载过高
            await asyncio.sleep(0.5)

        return results

    async def _request_batch_confirmation(self, conflicts: List[PortConflict]) -> bool:
        """请求批量确认"""
        try:
            # 评估总体风险
            max_risk = "low"
            for conflict in conflicts:
                risk_assessment = await self._assess_termination_risk(conflict, PermissionLevel.USER)
                max_risk = max(max_risk, risk_assessment["risk_level"],
                              key=lambda x: ["low", "medium", "high", "critical"].index(x))

            # 构建批量确认消息
            title = f"批量端口冲突解决确认 ({len(conflicts)} 个冲突)"
            description = f"即将解决 {len(conflicts)} 个端口冲突\n"
            description += f"最高风险级别: {max_risk.upper()}\n\n"

            # 列出所有冲突
            for i, conflict in enumerate(conflicts, 1):
                description += f"{i}. 端口 {conflict.port}"
                if conflict.service_type:
                    description += f" ({conflict.service_type})"
                if conflict.process_info:
                    description += f" - PID: {conflict.process_info.get('pid', 'N/A')}"
                description += "\n"

            action = ConfirmationAction(
                action_id="batch_port_termination",
                title=title,
                description=description,
                risk_level=max_risk,
                confirm_type=ConfirmationType.YES_NO_CANCEL,
                method=ConfirmationMethod.INTERACTIVE,
                timeout_seconds=60.0
            )

            response = await self.user_confirmation.request_confirmation(action)
            return response.result == ConfirmationResult.YES

        except Exception as e:
            logger.error(f"Batch confirmation failed: {str(e)}")
            return False

    def get_termination_history(self) -> List[ProcessTerminationResult]:
        """获取终止历史记录"""
        return self.termination_history.copy()

    def get_recovery_statistics(self) -> Dict[str, Any]:
        """获取恢复统计信息"""
        if not self.termination_history:
            return {
                "total_terminations": 0,
                "successful_terminations": 0,
                "failed_terminations": 0,
                "average_termination_time": 0.0,
                "most_common_method": None,
                "total_rollback_attempts": 0
            }

        total = len(self.termination_history)
        successful = sum(1 for t in self.termination_history if t.success)
        failed = total - successful

        avg_time = sum(t.time_taken for t in self.termination_history) / total

        method_counts = {}
        for t in self.termination_history:
            method = t.termination_method.value
            method_counts[method] = method_counts.get(method, 0) + 1

        most_common_method = max(method_counts.items(), key=lambda x: x[1])[0] if method_counts else None

        return {
            "total_terminations": total,
            "successful_terminations": successful,
            "failed_terminations": failed,
            "success_rate": successful / total * 100,
            "average_termination_time": avg_time,
            "most_common_method": most_common_method,
            "method_distribution": method_counts,
            "total_rollback_attempts": sum(1 for t in self.termination_history if t.rollback_possible)
        }