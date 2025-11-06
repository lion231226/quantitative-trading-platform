"""
Port Availability Checking Module

This module provides comprehensive port scanning and conflict detection capabilities
including process identification for occupied ports, port conflict resolution suggestions,
and automatic port allocation for services.
"""

import asyncio
import socket
import time
import json
import subprocess
import platform
from typing import Dict, List, Optional, Tuple, Union, Any
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path

try:
    import psutil
except ImportError:
    psutil = None

from utils.logger import get_logger
from utils.progress_tracker import ProgressTracker
from core.operating_system_detector import OperatingSystemDetector

logger = get_logger(__name__)


class PortStatus(Enum):
    """Port status enumeration"""
    AVAILABLE = "available"
    OCCUPIED = "occupied"
    CONFLICT = "conflict"
    TIMEOUT = "timeout"
    ERROR = "error"


class ServiceType(Enum):
    """Common service types and their default ports"""
    WEB_SERVER = "web_server"
    DATABASE_REDIS = "database_redis"
    DATABASE_POSTGRESQL = "database_postgresql"
    API_SERVER = "api_server"
    FRONTEND = "frontend"
    CACHE = "cache"
    MESSAGE_QUEUE = "message_queue"


# Default port mappings for common services
DEFAULT_PORTS = {
    ServiceType.WEB_SERVER: [80, 8080, 8000, 3000],
    ServiceType.DATABASE_REDIS: [6379],
    ServiceType.DATABASE_POSTGRESQL: [5432, 5433],
    ServiceType.API_SERVER: [8000, 8080, 9000],
    ServiceType.FRONTEND: [3000, 3001, 4000],
    ServiceType.CACHE: [11211],
    ServiceType.MESSAGE_QUEUE: [5672, 15672]
}


@dataclass
class PortCheckResult:
    """Result of port check"""
    port: int
    host: str
    status: PortStatus
    is_available: bool
    process_info: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    check_time: float = 0.0


@dataclass
class PortScanSummary:
    """Summary of port scan results"""
    total_ports: int
    available_ports: int
    occupied_ports: int
    conflicting_ports: int
    scan_duration: float
    results: List[PortCheckResult]


@dataclass
class ProcessInfo:
    """Information about a process using a port"""
    pid: int
    name: str
    command_line: str
    user: Optional[str] = None
    cpu_percent: Optional[float] = None
    memory_percent: Optional[float] = None
    create_time: Optional[float] = None


class PortChecker:
    """Port availability checking service"""

    def __init__(self, progress_tracker: Optional[ProgressTracker] = None):
        """
        Initialize port checker

        Args:
            progress_tracker: Progress tracker for scan status updates
        """
        self.progress_tracker = progress_tracker
        self.os_detector = OperatingSystemDetector()
        self.timeout = 5
        # Cache for port check results to avoid redundant checks
        self._port_cache = {}  # Format: {(host, port): PortCheckResult}

    def set_progress_tracker(self, tracker: ProgressTracker):
        """Set progress tracker for monitoring"""
        self.progress_tracker = tracker

    def _create_socket(self) -> socket.socket:
        """Create a socket with appropriate settings"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(self.timeout)
        return sock

    async def check_port_availability(self, host: str, port: int) -> PortCheckResult:
        """
        Check if a specific port is available

        Args:
            host: Host to check
            port: Port number to check

        Returns:
            PortCheckResult with check details
        """
        start_time = time.time()

        try:
            # Create socket and try to bind to the port
            sock = self._create_socket()

            try:
                # Try to bind to the port
                sock.bind((host, port))
                check_time = time.time() - start_time

                # Port is available if binding succeeds
                result = PortCheckResult(
                    port=port,
                    host=host,
                    status=PortStatus.AVAILABLE,
                    is_available=True,
                    check_time=check_time
                )

            finally:
                sock.close()

            # Get process info if port is occupied
            if not result.is_available:
                result.process_info = await self._get_process_info(host, port)

            return result

        except socket.error as e:
            check_time = time.time() - start_time

            # Determine status based on error
            if "Address already in use" in str(e):
                status = PortStatus.OCCUPIED
            elif "Permission denied" in str(e):
                status = PortStatus.CONFLICT
            else:
                status = PortStatus.ERROR

            # Get process info for occupied ports
            process_info = None
            if status == PortStatus.OCCUPIED:
                process_info = await self._get_process_info(host, port)

            return PortCheckResult(
                port=port,
                host=host,
                status=status,
                is_available=False,
                process_info=process_info,
                error_message=str(e),
                check_time=check_time
            )

        except Exception as e:
            check_time = time.time() - start_time
            return PortCheckResult(
                port=port,
                host=host,
                status=PortStatus.ERROR,
                is_available=False,
                error_message=f"Unexpected error: {str(e)}",
                check_time=check_time
            )

    async def _get_process_info(self, host: str, port: int) -> Optional[Dict[str, Any]]:
        """Get information about the process using a port"""
        if psutil is None:
            return None

        try:
            # Find process using the port
            for conn in psutil.net_connections():
                if (conn.laddr.port == port and
                    (conn.status == psutil.CONN_ESTABLISHED or conn.status == psutil.CONN_LISTEN)):

                    try:
                        process = psutil.Process(conn.pid)
                        return {
                            "pid": process.pid,
                            "name": process.name(),
                            "command_line": " ".join(process.cmdline()),
                            "user": process.username() if hasattr(process, 'username') else None,
                            "cpu_percent": process.cpu_percent(),
                            "memory_percent": process.memory_percent(),
                            "create_time": process.create_time(),
                            "status": conn.status
                        }
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        # Process might have ended
                        continue

        except Exception as e:
            logger.warning(f"Failed to get process info for port {port}: {str(e)}")

        return None

    async def scan_port_range(self, host: str, start_port: int, end_port: int) -> List[PortCheckResult]:
        """
        Scan a range of ports

        Args:
            host: Host to scan
            start_port: Starting port number
            end_port: Ending port number

        Returns:
            List of PortCheckResult objects
        """
        if self.progress_tracker:
            self.progress_tracker.start_task(
                "port_scanning",
                f"Scanning ports {start_port}-{end_port} on {host}"
            )

        results = []
        total_ports = end_port - start_port + 1

        for i, port in enumerate(range(start_port, end_port + 1)):
            if self.progress_tracker:
                progress = int((i + 1) / total_ports * 100)
                self.progress_tracker.update_progress(
                    progress, 100,
                    f"Checking port {port} ({progress}%)"
                )

            result = await self.check_port_availability(host, port)
            results.append(result)

        if self.progress_tracker:
            self.progress_tracker.complete_task(
                "port_scanning",
                f"Port scanning complete: {sum(1 for r in results if r.is_available)}/{total_ports} available"
            )

        return results

    async def check_service_ports(self, host: str, service_type: ServiceType) -> List[PortCheckResult]:
        """
        Check common ports for a specific service type

        Args:
            host: Host to check
            service_type: Type of service

        Returns:
            List of PortCheckResult objects
        """
        if service_type not in DEFAULT_PORTS:
            logger.warning(f"Unknown service type: {service_type}")
            return []

        ports = DEFAULT_PORTS[service_type]
        return await self.scan_port_range(host, min(ports), max(ports))

    async def find_available_port(self, host: str, start_port: int = 3000, max_attempts: int = 100) -> Optional[int]:
        """
        Find an available port in a range

        Args:
            host: Host to check
            start_port: Starting port number
            max_attempts: Maximum number of ports to check

        Returns:
            First available port number, or None if none found
        """
        end_port = start_port + max_attempts - 1

        for port in range(start_port, end_port + 1):
            result = await self.check_port_availability(host, port)
            if result.is_available:
                return port

        return None

    async def suggest_alternative_ports(self, host: str, occupied_ports: List[int], service_type: ServiceType) -> List[int]:
        """
        Suggest alternative ports for occupied ports

        Args:
            host: Host to check
            occupied_ports: List of occupied ports
            service_type: Type of service

        Returns:
            List of suggested alternative ports
        """
        alternatives = []

        if service_type in DEFAULT_PORTS:
            # Check other default ports for this service
            default_ports = [p for p in DEFAULT_PORTS[service_type] if p not in occupied_ports]

            for port in default_ports:
                cache_key = (host, port)
                if cache_key in self._port_cache:
                    result = self._port_cache[cache_key]
                else:
                    result = await self.check_port_availability(host, port)
                    self._port_cache[cache_key] = result

                if result.is_available:
                    alternatives.append(port)

        # If no default alternatives, find any available port in custom range
        if not alternatives:
            start_range = 10000
            end_range = 11000
            max_attempts = 50  # Limit attempts to avoid infinite scanning

            attempts = 0
            for port in range(start_range, end_range):
                if attempts >= max_attempts:
                    break
                if port not in occupied_ports and port not in alternatives:
                    cache_key = (host, port)
                    if cache_key in self._port_cache:
                        result = self._port_cache[cache_key]
                    else:
                        result = await self.check_port_availability(host, port)
                        self._port_cache[cache_key] = result

                    attempts += 1  # Count this as an actual attempt

                    if result.is_available:
                        alternatives.append(port)
                        if len(alternatives) >= 5:  # Limit suggestions
                            break

        return alternatives[:5]  # Return at most 5 suggestions

    async def check_required_ports(self, host: str, required_ports: List[int]) -> PortScanSummary:
        """
        Check a list of required ports

        Args:
            host: Host to check
            required_ports: List of required port numbers

        Returns:
            PortScanSummary with results
        """
        if self.progress_tracker:
            self.progress_tracker.start_task(
                "required_ports_check",
                f"Checking {len(required_ports)} required ports on {host}"
            )

        start_time = time.time()
        results = []

        for i, port in enumerate(required_ports):
            if self.progress_tracker:
                progress = int((i + 1) / len(required_ports) * 100)
                self.progress_tracker.update_progress(
                    progress, 100,
                    f"Checking required port {port} ({progress}%)"
                )

            result = await self.check_port_availability(host, port)
            results.append(result)

        scan_duration = time.time() - start_time

        # Calculate summary
        available = sum(1 for r in results if r.is_available)
        occupied = len(results) - available
        conflicting = sum(1 for r in results if r.status == PortStatus.CONFLICT)

        summary = PortScanSummary(
            total_ports=len(results),
            available_ports=available,
            occupied_ports=occupied,
            conflicting_ports=conflicting,
            scan_duration=scan_duration,
            results=results
        )

        if self.progress_tracker:
            self.progress_tracker.complete_task(
                "required_ports_check",
                f"Required ports check complete: {available}/{len(results)} available"
            )

        return summary

    def generate_conflict_report(self, summary: PortScanSummary) -> str:
        """
        Generate a report of port conflicts

        Args:
            summary: Port scan summary

        Returns:
            Formatted conflict report string
        """
        report_lines = [
            "=" * 60,
            "PORT CONFLICT REPORT",
            "=" * 60,
            f"Scan Duration: {summary.scan_duration:.2f} seconds",
            f"Total Ports Checked: {summary.total_ports}",
            f"Available: {summary.available_ports}",
            f"Occupied: {summary.occupied_ports}",
            f"Conflicts: {summary.conflicting_ports}",
            "",
            "DETAILED RESULTS:",
            "-" * 40
        ]

        for result in summary.results:
            status_icon = "✅" if result.is_available else "❌"
            status_text = "Available" if result.is_available else "Occupied"

            report_lines.append(
                f"{status_icon} Port {result.port} ({result.status.value.upper()}) - {status_text}"
            )

            if not result.is_available and result.process_info:
                info = result.process_info
                report_lines.extend([
                    f"   Process: {info.get('name', 'Unknown')} (PID: {info.get('pid', 'N/A')})",
                    f"   Command: {info.get('command_line', 'N/A')}",
                    f"   User: {info.get('user', 'N/A')}",
                    f"   CPU: {info.get('cpu_percent', 'N/A')}%" if info.get('cpu_percent') else "",
                    f"   Memory: {info.get('memory_percent', 'N/A')}%" if info.get('memory_percent') else ""
                ])

            if result.error_message:
                report_lines.append(f"   Error: {result.error_message}")

            report_lines.append("")

        # Add suggestions for occupied ports
        occupied_results = [r for r in summary.results if not r.is_available]
        if occupied_results:
            report_lines.extend([
                "RECOMMENDATIONS:",
                "-" * 40
            ])

            for result in occupied_results[:5]:  # Limit to first 5
                if result.process_info:
                    report_lines.append(
                        f"• Stop process '{result.process_info.get('name', 'unknown')}' (PID: {result.process_info.get('pid', 'N/A')}) to free port {result.port}"
                    )
                else:
                    report_lines.append(
                        f"• Investigate port {result.port} usage - unknown process"
                    )

        return "\n".join(report_lines)

    def save_scan_results(self, summary: PortScanSummary, output_file: str) -> bool:
        """
        Save port scan results to JSON file

        Args:
            summary: Port scan summary
            output_file: Path to output file

        Returns:
            True if successful, False otherwise
        """
        try:
            # Convert to serializable format
            results_data = {
                "scan_summary": asdict(summary),
                "timestamp": time.time(),
                "total_ports": summary.total_ports,
                "available_ports": summary.available_ports,
                "occupied_ports": summary.occupied_ports,
                "conflicting_ports": summary.conflicting_ports,
                "duration": summary.scan_duration,
                "results": [
                    {
                        **asdict(result),
                        "status": result.status.value
                    }
                    for result in summary.results
                ]
            }

            # Write to file
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(results_data, f, indent=2, ensure_ascii=False)

            logger.info(f"Port scan results saved to: {output_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to save port scan results: {str(e)}")
            return False

    async def resolve_port_conflicts(self, host: str, conflicts: List[Tuple[int, ServiceType]]) -> Dict[int, Optional[int]]:
        """
        Attempt to resolve port conflicts by finding alternative ports

        Args:
            host: Host to check
            conflicts: List of (occupied_port, service_type) tuples

        Returns:
            Dictionary mapping original ports to alternative ports (None if no alternative found)
        """
        resolutions = {}

        for occupied_port, service_type in conflicts:
            logger.info(f"Finding alternative for port {occupied_port} ({service_type.value})")

            alternatives = await self.suggest_alternative_ports(host, [occupied_port], service_type)

            if alternatives:
                best_alternative = alternatives[0]
                resolutions[occupied_port] = best_alternative
                logger.info(f"Suggested alternative: {occupied_port} → {best_alternative}")
            else:
                resolutions[occupied_port] = None
                logger.warning(f"No alternative found for port {occupied_port}")

        return resolutions

    def get_service_recommendations(self, occupied_ports: List[int]) -> Dict[str, List[str]]:
        """
        Get recommendations for handling occupied ports based on common services

        Args:
            occupied_ports: List of occupied port numbers

        Returns:
            Dictionary with service recommendations
        """
        recommendations = {}

        # Common service port mappings
        service_ports = {
            "Web Server": [80, 8080, 8000, 3000],
            "API Server": [8000, 8080, 9000],
            "Database (Redis)": [6379],
            "Database (PostgreSQL)": [5432, 5433],
            "Frontend Dev Server": [3000, 3001, 4000],
            "Message Queue": [5672, 15672]
        }

        for service_name, ports in service_ports.items():
            occupied_service_ports = [p for p in ports if p in occupied_ports]
            if occupied_service_ports:
                recommendations[service_name] = [
                    f"Port(s) {', '.join(map(str, occupied_service_ports))} are occupied",
                    "Consider stopping the service or using alternative ports",
                    f"Common alternatives: {', '.join(map(str, [p for p in ports if p not in occupied_ports]))}"
                ]

        return recommendations