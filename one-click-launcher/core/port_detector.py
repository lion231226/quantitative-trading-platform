"""
Port Conflict Detection and Resolution Module

This module provides intelligent port conflict detection and resolution
capabilities including process identification, alternative port suggestions,
and automated resolution strategies.
"""

import asyncio
import socket
import time
import subprocess
import platform
from typing import Dict, List, Optional, Tuple, Union, Any
from dataclasses import dataclass, asdict
from enum import Enum
import json

try:
    import psutil
except ImportError:
    psutil = None

from core.port_checker import PortChecker, PortCheckResult, PortStatus, ServiceType
from utils.logger import get_logger
from utils.progress_tracker import ProgressTracker

logger = get_logger(__name__)


class ResolutionStrategy(Enum):
    """Port conflict resolution strategies"""
    STOP_PROCESS = "stop_process"
    CHANGE_PORT = "change_port"
    USE_ALTERNATIVE = "use_alternative"
    KILL_PROCESS = "kill_process"
    RESTART_SERVICE = "restart_service"


@dataclass
class PortConflict:
    """Port conflict information"""
    port: int
    host: str
    process_info: Optional[Dict[str, Any]]
    service_type: Optional[str]
    severity: str
    resolution_options: List[ResolutionStrategy]
    alternative_ports: List[int]


@dataclass
class ResolutionResult:
    """Result of port conflict resolution attempt"""
    success: bool
    strategy_used: Optional[ResolutionStrategy]
    resolved_port: Optional[int]
    message: str
    action_taken: Optional[str]
    requires_user_action: bool = False
    admin_required: bool = False


class PortConflictResolver:
    """
    Advanced port conflict detection and resolution class
    """

    def __init__(self, progress_tracker: Optional[ProgressTracker] = None):
        """
        Initialize port conflict resolver

        Args:
            progress_tracker: Progress tracker for resolution operations
        """
        self.progress_tracker = progress_tracker
        self.logger = get_logger(self.__class__.__name__)
        self.port_checker = PortChecker(progress_tracker)

        # Process termination commands by platform
        self.platform_commands = self._get_platform_commands()

        # Service recognition patterns
        self.service_patterns = {
            "node": {
                "ports": [3000, 8000, 8080, 9000],
                "processes": ["node", "node.exe"],
                "descriptions": ["Node.js application", "JavaScript runtime"]
            },
            "python": {
                "ports": [8000, 5000, 8080],
                "processes": ["python", "python.exe", "python3"],
                "descriptions": ["Python application", "Django/Flask server"]
            },
            "postgres": {
                "ports": [5432, 5433],
                "processes": ["postgres", "postgresql"],
                "descriptions": ["PostgreSQL database server"]
            },
            "redis": {
                "ports": [6379],
                "processes": ["redis-server", "redis"],
                "descriptions": ["Redis in-memory data store"]
            },
            "mongodb": {
                "ports": [27017],
                "processes": ["mongod", "mongod.exe"],
                "descriptions": ["MongoDB database server"]
            },
            "nginx": {
                "ports": [80, 443, 8080],
                "processes": ["nginx", "nginx.exe"],
                "descriptions": ["Nginx web server"]
            },
            "apache": {
                "ports": [80, 443, 8080],
                "processes": ["httpd", "apache2", "httpd.exe"],
                "descriptions": ["Apache web server"]
            }
        }

    def _get_platform_commands(self) -> Dict[str, Dict[str, str]]:
        """Get platform-specific process management commands"""
        return {
            "windows": {
                "list_processes": "tasklist /fo csv",
                "kill_process": "taskkill /F /PID {pid}",
                "find_process": "tasklist /fi \"PID eq {pid}\" /fo csv",
                "stop_service": "net stop {service_name}",
                "kill_by_name": "taskkill /F /IM {process_name}"
            },
            "darwin": {
                "list_processes": "ps aux",
                "kill_process": "kill -9 {pid}",
                "find_process": "ps -p {pid}",
                "stop_service": "brew services stop {service_name}",
                "kill_by_name": "pkill -f {process_name}"
            },
            "linux": {
                "list_processes": "ps aux",
                "kill_process": "kill -9 {pid}",
                "find_process": "ps -p {pid}",
                "stop_service": "systemctl stop {service_name}",
                "kill_by_name": "pkill -f {process_name}"
            }
        }

    def get_current_platform(self) -> str:
        """Get current platform identifier"""
        system = platform.system().lower()
        if system == "windows":
            return "windows"
        elif system == "darwin":
            return "darwin"
        elif system == "linux":
            return "linux"
        else:
            return "unknown"

    async def detect_conflicts(self, host: str = "localhost",
                             required_ports: List[int] = None) -> List[PortConflict]:
        """
        Detect port conflicts for specified ports

        Args:
            host: Host to check
            required_ports: List of required port numbers

        Returns:
            List of detected port conflicts
        """
        if required_ports is None:
            required_ports = [3000, 8000, 5432, 6379]

        self.logger.info(f"Detecting port conflicts on {host} for ports: {required_ports}")

        if self.progress_tracker:
            self.progress_tracker.start_task(
                "port_conflict_detection",
                f"Scanning {len(required_ports)} ports for conflicts"
            )

        conflicts = []

        for i, port in enumerate(required_ports):
            if self.progress_tracker:
                progress = int((i + 1) / len(required_ports) * 100)
                self.progress_tracker.update_progress(
                    progress, 100,
                    f"Checking port {port} ({progress}%)"
                )

            result = await self.port_checker.check_port_availability(host, port)

            if not result.is_available:
                # Identify service type
                service_type = self._identify_service_by_port(port, result.process_info)

                # Determine severity and resolution options
                severity, resolution_options = self._assess_conflict_severity(
                    port, service_type, result.process_info
                )

                # Get alternative ports
                alternatives = await self._get_alternative_ports(host, port, service_type)

                conflict = PortConflict(
                    port=port,
                    host=host,
                    process_info=result.process_info,
                    service_type=service_type,
                    severity=severity,
                    resolution_options=resolution_options,
                    alternative_ports=alternatives
                )

                conflicts.append(conflict)

        if self.progress_tracker:
            self.progress_tracker.complete_task(
                "port_conflict_detection",
                f"Found {len(conflicts)} port conflicts"
            )

        return conflicts

    def _identify_service_by_port(self, port: int, process_info: Optional[Dict[str, Any]]) -> Optional[str]:
        """Identify service type based on port and process information"""
        # First try to identify by port
        port_service_map = {
            3000: "node",
            8000: "python",
            8080: "nginx",
            5432: "postgres",
            6379: "redis",
            27017: "mongodb",
            3306: "mysql",
            5672: "rabbitmq",
            15672: "rabbitmq_management",
        }

        service_type = port_service_map.get(port)

        # Try to refine identification using process info
        if process_info:
            process_name = process_info.get('name', '').lower()
            command_line = process_info.get('command_line', '').lower()

            for service, patterns in self.service_patterns.items():
                if any(proc in process_name for proc in patterns["processes"]):
                    service_type = service
                    break
                elif any(proc in command_line for proc in patterns["processes"]):
                    service_type = service
                    break

        return service_type

    def _assess_conflict_severity(self, port: int, service_type: Optional[str],
                                process_info: Optional[Dict[str, Any]]) -> Tuple[str, List[ResolutionStrategy]]:
        """Assess conflict severity and available resolution strategies"""
        severity = "medium"
        resolution_options = [ResolutionStrategy.CHANGE_PORT, ResolutionStrategy.USE_ALTERNATIVE]

        # High severity for system-critical services
        critical_services = ["postgres", "redis", "mongodb"]
        if service_type in critical_services:
            severity = "high"
            resolution_options.insert(0, ResolutionStrategy.CHANGE_PORT)

        # Medium severity for development servers
        dev_services = ["node", "python"]
        if service_type in dev_services:
            severity = "medium"
            resolution_options.insert(0, ResolutionStrategy.STOP_PROCESS)

        # Low severity for user applications
        if service_type is None:
            severity = "low"
            resolution_options = [ResolutionStrategy.USE_ALTERNATIVE]

        # Add kill process option if process info is available
        if process_info:
            resolution_options.insert(0, ResolutionStrategy.KILL_PROCESS)

        return severity, resolution_options

    async def _get_alternative_ports(self, host: str, port: int,
                                   service_type: Optional[str]) -> List[int]:
        """Get alternative ports for a conflicting port"""
        if service_type and service_type in self.service_patterns:
            service_ports = self.service_patterns[service_type]["ports"]
            service_enum = self._get_service_enum(service_type)

            if service_enum:
                alternatives = await self.port_checker.suggest_alternative_ports(
                    host, [port], service_enum
                )
                return alternatives

        # Default alternatives for unknown services
        default_ranges = [
            range(10000, 10010),
            range(20000, 20010),
            range(30000, 30010)
        ]

        for range_list in default_ranges:
            for alt_port in range_list:
                result = await self.port_checker.check_port_availability(host, alt_port)
                if result.is_available:
                    return [alt_port]

        return []

    def _get_service_enum(self, service_type: str) -> Optional[ServiceType]:
        """Convert service type string to ServiceType enum"""
        type_mapping = {
            "node": ServiceType.FRONTEND,
            "python": ServiceType.API_SERVER,
            "nginx": ServiceType.WEB_SERVER,
            "postgres": ServiceType.DATABASE_POSTGRESQL,
            "redis": ServiceType.DATABASE_REDIS,
        }
        return type_mapping.get(service_type)

    async def resolve_conflict(self, conflict: PortConflict,
                             preferred_strategy: Optional[ResolutionStrategy] = None) -> ResolutionResult:
        """
        Attempt to resolve a port conflict

        Args:
            conflict: Port conflict to resolve
            preferred_strategy: Preferred resolution strategy

        Returns:
            ResolutionResult with resolution outcome
        """
        self.logger.info(f"Attempting to resolve port conflict on port {conflict.port}")

        # Use preferred strategy if specified and available
        if preferred_strategy and preferred_strategy in conflict.resolution_options:
            strategies = [preferred_strategy] + [s for s in conflict.resolution_options if s != preferred_strategy]
        else:
            strategies = conflict.resolution_options

        for strategy in strategies:
            try:
                result = await self._attempt_resolution(conflict, strategy)
                if result.success:
                    return result
            except Exception as e:
                self.logger.warning(f"Resolution strategy {strategy.value} failed: {e}")
                continue

        # All strategies failed
        return ResolutionResult(
            success=False,
            strategy_used=None,
            resolved_port=None,
            message="All automatic resolution strategies failed. Manual intervention required.",
            action_taken=None,
            requires_user_action=True,
            admin_required=conflict.severity == "high"
        )

    async def _attempt_resolution(self, conflict: PortConflict,
                                strategy: ResolutionStrategy) -> ResolutionResult:
        """Attempt to resolve conflict using specific strategy"""
        if strategy == ResolutionStrategy.USE_ALTERNATIVE:
            return await self._resolve_with_alternative_port(conflict)
        elif strategy == ResolutionStrategy.STOP_PROCESS:
            return await self._resolve_by_stopping_process(conflict)
        elif strategy == ResolutionStrategy.KILL_PROCESS:
            return await self._resolve_by_killing_process(conflict)
        elif strategy == ResolutionStrategy.CHANGE_PORT:
            return await self._resolve_by_changing_port(conflict)
        else:
            raise ValueError(f"Unsupported resolution strategy: {strategy}")

    async def _resolve_with_alternative_port(self, conflict: PortConflict) -> ResolutionResult:
        """Resolve conflict by suggesting alternative port"""
        if not conflict.alternative_ports:
            return ResolutionResult(
                success=False,
                strategy_used=ResolutionStrategy.USE_ALTERNATIVE,
                resolved_port=None,
                message="No alternative ports available",
                action_taken=None
            )

        best_alternative = conflict.alternative_ports[0]

        return ResolutionResult(
            success=True,
            strategy_used=ResolutionStrategy.USE_ALTERNATIVE,
            resolved_port=best_alternative,
            message=f"Use alternative port {best_alternative} instead of {conflict.port}",
            action_taken=f"Suggested port {best_alternative} as alternative",
            requires_user_action=True
        )

    async def _resolve_by_stopping_process(self, conflict: PortConflict) -> ResolutionResult:
        """Resolve conflict by stopping the conflicting process"""
        if not conflict.process_info:
            return ResolutionResult(
                success=False,
                strategy_used=ResolutionStrategy.STOP_PROCESS,
                resolved_port=None,
                message="No process information available",
                action_taken=None
            )

        pid = conflict.process_info.get('pid')
        process_name = conflict.process_info.get('name', 'unknown')

        if not pid:
            return ResolutionResult(
                success=False,
                strategy_used=ResolutionStrategy.STOP_PROCESS,
                resolved_port=None,
                message="No process ID available",
                action_taken=None
            )

        try:
            # Try graceful termination first
            success = await self._stop_process_gracefully(pid)
            action = f"Gracefully stopped process {process_name} (PID: {pid})"

            if not success:
                # Force termination if graceful fails
                success = await self._kill_process_forcefully(pid)
                action = f"Forcefully killed process {process_name} (PID: {pid})"

            if success:
                # Verify port is now available
                await asyncio.sleep(1)  # Give process time to terminate
                result = await self.port_checker.check_port_availability(conflict.host, conflict.port)

                if result.is_available:
                    return ResolutionResult(
                        success=True,
                        strategy_used=ResolutionStrategy.STOP_PROCESS,
                        resolved_port=conflict.port,
                        message=f"Process stopped successfully. Port {conflict.port} is now available.",
                        action_taken=action
                    )
                else:
                    return ResolutionResult(
                        success=False,
                        strategy_used=ResolutionStrategy.STOP_PROCESS,
                        resolved_port=None,
                        message=f"Process stopped but port {conflict.port} is still occupied",
                        action_taken=action
                    )
            else:
                return ResolutionResult(
                    success=False,
                    strategy_used=ResolutionStrategy.STOP_PROCESS,
                    resolved_port=None,
                    message=f"Failed to stop process {process_name} (PID: {pid})",
                    action_taken=None,
                    requires_user_action=True
                )

        except Exception as e:
            return ResolutionResult(
                success=False,
                strategy_used=ResolutionStrategy.STOP_PROCESS,
                resolved_port=None,
                message=f"Error stopping process: {str(e)}",
                action_taken=None,
                requires_user_action=True
            )

    async def _resolve_by_killing_process(self, conflict: PortConflict) -> ResolutionResult:
        """Resolve conflict by forcefully killing the process"""
        if not conflict.process_info:
            return ResolutionResult(
                success=False,
                strategy_used=ResolutionStrategy.KILL_PROCESS,
                resolved_port=None,
                message="No process information available",
                action_taken=None
            )

        pid = conflict.process_info.get('pid')
        process_name = conflict.process_info.get('name', 'unknown')

        if not pid:
            return ResolutionResult(
                success=False,
                strategy_used=ResolutionStrategy.KILL_PROCESS,
                resolved_port=None,
                message="No process ID available",
                action_taken=None
            )

        try:
            success = await self._kill_process_forcefully(pid)

            if success:
                # Verify port is now available
                await asyncio.sleep(1)
                result = await self.port_checker.check_port_availability(conflict.host, conflict.port)

                if result.is_available:
                    return ResolutionResult(
                        success=True,
                        strategy_used=ResolutionStrategy.KILL_PROCESS,
                        resolved_port=conflict.port,
                        message=f"Process killed successfully. Port {conflict.port} is now available.",
                        action_taken=f"Forcefully killed process {process_name} (PID: {pid})"
                    )
                else:
                    return ResolutionResult(
                        success=False,
                        strategy_used=ResolutionStrategy.KILL_PROCESS,
                        resolved_port=None,
                        message=f"Process killed but port {conflict.port} is still occupied",
                        action_taken=f"Forcefully killed process {process_name} (PID: {pid})"
                    )
            else:
                return ResolutionResult(
                    success=False,
                    strategy_used=ResolutionStrategy.KILL_PROCESS,
                    resolved_port=None,
                    message=f"Failed to kill process {process_name} (PID: {pid})",
                    action_taken=None,
                    requires_user_action=True,
                    admin_required=True
                )

        except Exception as e:
            return ResolutionResult(
                success=False,
                strategy_used=ResolutionStrategy.KILL_PROCESS,
                resolved_port=None,
                message=f"Error killing process: {str(e)}",
                action_taken=None,
                requires_user_action=True,
                admin_required=True
            )

    async def _resolve_by_changing_port(self, conflict: PortConflict) -> ResolutionResult:
        """Resolve conflict by suggesting port change"""
        if not conflict.alternative_ports:
            return ResolutionResult(
                success=False,
                strategy_used=ResolutionStrategy.CHANGE_PORT,
                resolved_port=None,
                message="No alternative ports available for port change",
                action_taken=None
            )

        best_alternative = conflict.alternative_ports[0]

        return ResolutionResult(
            success=True,
            strategy_used=ResolutionStrategy.CHANGE_PORT,
            resolved_port=best_alternative,
            message=f"Configure application to use port {best_alternative} instead of {conflict.port}",
            action_taken=f"Suggested port change from {conflict.port} to {best_alternative}",
            requires_user_action=True
        )

    async def _stop_process_gracefully(self, pid: int) -> bool:
        """Attempt to stop process gracefully"""
        try:
            if psutil:
                process = psutil.Process(pid)
                process.terminate()
                try:
                    process.wait(timeout=5)
                    return True
                except psutil.TimeoutExpired:
                    return False
            else:
                # Fallback to system commands
                platform = self.get_current_platform()
                if platform in self.platform_commands:
                    command = self.platform_commands[platform]["kill_process"].format(pid=pid)
                    # Use termination signal if available
                    if platform != "windows":
                        command = command.replace("-9", "-15")  # SIGTERM instead of SIGKILL

                    result = subprocess.run(command, shell=True, capture_output=True, text=True)
                    return result.returncode == 0
                return False
        except Exception:
            return False

    async def _kill_process_forcefully(self, pid: int) -> bool:
        """Forcefully kill process"""
        try:
            if psutil:
                process = psutil.Process(pid)
                process.kill()
                return True
            else:
                # Fallback to system commands
                platform = self.get_current_platform()
                if platform in self.platform_commands:
                    command = self.platform_commands[platform]["kill_process"].format(pid=pid)
                    result = subprocess.run(command, shell=True, capture_output=True, text=True)
                    return result.returncode == 0
                return False
        except Exception:
            return False

    def generate_resolution_report(self, conflicts: List[PortConflict],
                                 resolutions: List[ResolutionResult]) -> str:
        """Generate a comprehensive resolution report"""
        report_lines = [
            "=" * 80,
            "PORT CONFLICT RESOLUTION REPORT",
            "=" * 80,
            f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            f"Total Conflicts: {len(conflicts)}",
            f"Successfully Resolved: {sum(1 for r in resolutions if r.success)}",
            f"Failed: {sum(1 for r in resolutions if not r.success)}",
            "",
            "DETAILED RESULTS:",
            "-" * 40
        ]

        for i, (conflict, resolution) in enumerate(zip(conflicts, resolutions), 1):
            status_icon = "✅" if resolution.success else "❌"
            status_text = "RESOLVED" if resolution.success else "FAILED"

            report_lines.extend([
                f"{i}. Port {conflict.port} ({conflict.service_type or 'Unknown Service'}) - {status_text} {status_icon}",
                f"   Severity: {conflict.severity}",
                f"   Strategy Used: {resolution.strategy_used.value if resolution.strategy_used else 'None'}",
                f"   Message: {resolution.message}",
            ])

            if resolution.action_taken:
                report_lines.append(f"   Action Taken: {resolution.action_taken}")

            if conflict.process_info:
                info = conflict.process_info
                report_lines.extend([
                    f"   Conflicting Process: {info.get('name', 'Unknown')} (PID: {info.get('pid', 'N/A')})",
                ])

            if resolution.requires_user_action:
                report_lines.append("   ⚠️  Requires user action")

            if resolution.admin_required:
                report_lines.append("   🔒 Administrator privileges required")

            report_lines.append("")

        # Add summary section
        report_lines.extend([
            "RESOLUTION SUMMARY:",
            "-" * 40,
            f"Automatic Resolutions: {sum(1 for r in resolutions if r.success and not r.requires_user_action)}",
            f"Manual Actions Required: {sum(1 for r in resolutions if r.requires_user_action)}",
            f"Admin Privileges Required: {sum(1 for r in resolutions if r.admin_required)}",
            "",
            "RECOMMENDATIONS:",
            "-" * 40
        ])

        # Add specific recommendations based on resolution results
        failed_resolutions = [(c, r) for c, r in zip(conflicts, resolutions) if not r.success]
        if failed_resolutions:
            report_lines.append("• Review failed resolutions and take manual action")
            report_lines.append("• Consider stopping conflicting applications manually")
            report_lines.append("• Restart services if necessary")

        manual_actions = [r for r in resolutions if r.requires_user_action]
        if manual_actions:
            report_lines.append("• Complete manual configuration changes for suggested alternatives")

        admin_required = [r for r in resolutions if r.admin_required]
        if admin_required:
            report_lines.append("• Run launcher with administrator/root privileges if needed")

        return "\n".join(report_lines)

    async def auto_resolve_all_conflicts(self, host: str = "localhost",
                                       required_ports: List[int] = None,
                                       allow_process_termination: bool = False) -> Dict[str, Any]:
        """
        Automatically resolve all detected port conflicts

        Args:
            host: Host to check
            required_ports: List of required ports
            allow_process_termination: Whether to allow process termination

        Returns:
            Dictionary with resolution results
        """
        self.logger.info("Starting automatic port conflict resolution...")

        if self.progress_tracker:
            self.progress_tracker.start_task(
                "auto_port_conflict_resolution",
                "Automatically resolving port conflicts"
            )

        # Detect conflicts
        conflicts = await self.detect_conflicts(host, required_ports)

        if not conflicts:
            result = {
                "conflicts_detected": 0,
                "conflicts_resolved": 0,
                "conflicts_failed": 0,
                "resolutions": [],
                "report": "No port conflicts detected."
            }

            if self.progress_tracker:
                self.progress_tracker.complete_task(
                    "auto_port_conflict_resolution",
                    "No conflicts to resolve"
                )

            return result

        # Resolve conflicts
        resolutions = []
        for conflict in conflicts:
            # Filter strategies based on permissions
            available_strategies = conflict.resolution_options.copy()

            if not allow_process_termination:
                available_strategies = [
                    s for s in available_strategies
                    if s not in [ResolutionStrategy.STOP_PROCESS, ResolutionStrategy.KILL_PROCESS]
                ]

            if not available_strategies:
                # Only alternative port strategies available
                available_strategies = [ResolutionStrategy.USE_ALTERNATIVE]

            resolution = await self.resolve_conflict(conflict, available_strategies[0])
            resolutions.append(resolution)

        # Generate results
        resolved_count = sum(1 for r in resolutions if r.success)
        failed_count = len(resolutions) - resolved_count

        report = self.generate_resolution_report(conflicts, resolutions)

        result = {
            "conflicts_detected": len(conflicts),
            "conflicts_resolved": resolved_count,
            "conflicts_failed": failed_count,
            "resolutions": [
                {
                    "port": c.port,
                    "service_type": c.service_type,
                    "success": r.success,
                    "strategy": r.strategy_used.value if r.strategy_used else None,
                    "resolved_port": r.resolved_port,
                    "message": r.message,
                    "requires_user_action": r.requires_user_action,
                    "admin_required": r.admin_required
                }
                for c, r in zip(conflicts, resolutions)
            ],
            "report": report
        }

        if self.progress_tracker:
            self.progress_tracker.complete_task(
                "auto_port_conflict_resolution",
                f"Resolved {resolved_count}/{len(conflicts)} conflicts"
            )

        return result