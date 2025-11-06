"""
Intelligent Error Detection Module

This module provides comprehensive error detection capabilities including
port occupation detection, permission issue diagnosis, network connectivity
checking, dependency version conflict detection, and error classification.
"""

import asyncio
import os
import sys
import subprocess
import platform
import json
import time
from typing import Dict, List, Optional, Tuple, Union, Any
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path

try:
    import psutil
except ImportError:
    psutil = None

from core.port_checker import PortChecker, PortCheckResult, PortStatus, ServiceType
from core.dependency_checker import DependencyChecker, DependencyStatus, DependencyType
from core.permission_diagnostic import PermissionDiagnostic, PermissionCheckResult, FilePermissionResult
from core.network_diagnostic import NetworkDiagnostic, NetworkDiagnosticResult, NetworkStatus, ServiceStatus
from core.dependency_conflict_detector import DependencyConflictDetector, DependencyAnalysisResult
from core.error_classifier import (
    ErrorClassifier, ErrorClassification, RecoveryPlan, RecoveryComplexity,
    ErrorRecoverability, ErrorSeverity
)
from utils.logger import get_logger
from utils.progress_tracker import ProgressTracker

logger = get_logger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorRecoveryType(Enum):
    """Error recovery types"""
    RECOVERABLE = "recoverable"
    NON_RECOVERABLE = "non_recoverable"
    REQUIRES_USER_ACTION = "requires_user_action"
    REQUIRES_ADMIN = "requires_admin"


@dataclass
class ErrorInfo:
    """Structured error information following unified error format"""
    code: str
    message: str
    solution: str
    details: Dict[str, Any]
    severity: ErrorSeverity
    recovery_type: ErrorRecoveryType
    category: str
    timestamp: float = 0.0

    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()


@dataclass
class PortConflictError:
    """Port conflict specific error information"""
    port: int
    host: str
    process_info: Optional[Dict[str, Any]] = None
    alternative_ports: List[int] = None
    service_type: Optional[str] = None
    resolution_steps: List[str] = None

    def __post_init__(self):
        if self.alternative_ports is None:
            self.alternative_ports = []
        if self.resolution_steps is None:
            self.resolution_steps = []


@dataclass
class PermissionError:
    """Permission specific error information"""
    resource_path: str
    required_permissions: str
    current_user: Optional[str] = None
    admin_required: bool = False
    platform_specific_guidance: Dict[str, str] = None

    def __post_init__(self):
        if self.platform_specific_guidance is None:
            self.platform_specific_guidance = {}


@dataclass
class NetworkError:
    """Network specific error information"""
    host: str
    port: Optional[int] = None
    connectivity_status: NetworkStatus = NetworkStatus.UNKNOWN
    dns_resolution: bool = False
    service_available: bool = False
    proxy_detected: bool = False
    firewall_blocked: bool = False
    troubleshooting_steps: List[str] = None

    def __post_init__(self):
        if self.troubleshooting_steps is None:
            self.troubleshooting_steps = []


@dataclass
class DependencyConflict:
    """Dependency conflict specific error information"""
    dependency_name: str
    current_version: Optional[str] = None
    required_version: Optional[str] = None
    conflict_type: str = ""
    resolution_strategy: str = ""
    auto_fix_available: bool = False
    manual_steps: List[str] = None

    def __post_init__(self):
        if self.manual_steps is None:
            self.manual_steps = []


class ErrorDetector:
    """
    Main intelligent error detection class that provides comprehensive
    error detection and diagnosis capabilities.
    """

    def __init__(self, progress_tracker: Optional[ProgressTracker] = None):
        """
        Initialize error detector

        Args:
            progress_tracker: Progress tracker for error detection status
        """
        self.progress_tracker = progress_tracker
        self.logger = get_logger(self.__class__.__name__)

        # Initialize component detectors
        self.port_checker = PortChecker(progress_tracker)
        self.dependency_checker = DependencyChecker()
        self.permission_diagnostic = PermissionDiagnostic(progress_tracker)
        self.error_classifier = ErrorClassifier(progress_tracker)

        # Detection results cache
        self.detection_cache = {}
        self.error_knowledge_base = self._load_error_knowledge_base()

    def _load_error_knowledge_base(self) -> Dict[str, Dict[str, Any]]:
        """Load error solutions and guidance knowledge base"""
        return {
            "port_conflicts": {
                "common_ports": {
                    3000: ["Frontend development server", "React/Vue/Angular dev server", "Node.js application"],
                    8000: ["Backend API server", "Django/Flask development server", "FastAPI application"],
                    5432: ["PostgreSQL database server", "Primary database instance"],
                    6379: ["Redis cache server", "In-memory data store"],
                    27017: ["MongoDB database server", "NoSQL database instance"],
                    8080: ["Alternative web server", "Tomcat/JBoss server", "Java application"],
                },
                "resolution_strategies": {
                    "stop_process": "Stop the conflicting process using task manager or command line",
                    "change_port": "Configure the application to use a different port",
                    "use_alternative": "Use one of the suggested alternative ports"
                }
            },
            "permission_issues": {
                "windows": {
                    "admin_elevation": "Run as Administrator",
                    "file_permissions": "Right-click file → Properties → Security → Edit permissions",
                    "service_installation": "Open Command Prompt as Administrator"
                },
                "macos": {
                    "admin_elevation": "Use 'sudo' command in terminal",
                    "file_permissions": "Use 'chmod' command to modify permissions",
                    "service_installation": "Use 'sudo' for system-wide installation"
                },
                "linux": {
                    "admin_elevation": "Use 'sudo' command in terminal",
                    "file_permissions": "Use 'chmod' and 'chown' commands",
                    "service_installation": "Use system package manager with sudo"
                }
            },
            "network_issues": {
                "connectivity_tests": [
                    "ping 8.8.8.8 - Test basic internet connectivity",
                    "nslookup google.com - Test DNS resolution",
                    "curl -I https://www.google.com - Test HTTP connectivity"
                ],
                "firewall_indicators": [
                    "Connection timeout errors",
                    "Unable to reach specific ports",
                    "VPN or proxy interference"
                ],
                "proxy_detection": [
                    "Check HTTP_PROXY and HTTPS_PROXY environment variables",
                    "Verify system proxy settings",
                    "Corporate network configuration"
                ]
            },
            "dependency_conflicts": {
                "version_resolution": {
                    "npm": "Use 'npm install package@version' to specify version",
                    "python": "Use 'pip install package==version' for exact version",
                    "node": "Use version manager like nvm or n",
                    "python": "Use virtual environments for dependency isolation"
                },
                "conflict_resolution": {
                    "upgrade": "Upgrade to latest compatible version",
                    "downgrade": "Downgrade to meet requirements",
                    "replace": "Replace with alternative package",
                    "fork": "Use custom build if available"
                }
            }
        }

    async def detect_port_conflicts(self, host: str = "localhost",
                                  required_ports: List[int] = None) -> List[PortConflictError]:
        """
        Detect port conflicts for specified ports

        Args:
            host: Host to check
            required_ports: List of required port numbers

        Returns:
            List of port conflict errors
        """
        if required_ports is None:
            required_ports = [3000, 8000, 5432, 6379]  # Default service ports

        self.logger.info(f"Detecting port conflicts on {host} for ports: {required_ports}")

        if self.progress_tracker:
            self.progress_tracker.start_task(
                "port_conflict_detection",
                f"Checking port conflicts for {len(required_ports)} ports"
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
                # Determine service type
                service_type = self._identify_service_type(port)

                # Get alternative ports
                service_enum = self._get_service_enum(service_type)
                alternatives = []
                if service_enum:
                    alternatives = await self.port_checker.suggest_alternative_ports(
                        host, [port], service_enum
                    )

                # Create resolution steps
                resolution_steps = self._generate_port_resolution_steps(
                    port, result.process_info, alternatives, service_type
                )

                conflict = PortConflictError(
                    port=port,
                    host=host,
                    process_info=result.process_info,
                    alternative_ports=alternatives,
                    service_type=service_type,
                    resolution_steps=resolution_steps
                )

                conflicts.append(conflict)

        if self.progress_tracker:
            self.progress_tracker.complete_task(
                "port_conflict_detection",
                f"Found {len(conflicts)} port conflicts"
            )

        return conflicts

    def _identify_service_type(self, port: int) -> str:
        """Identify service type based on port number"""
        port_service_map = {
            3000: "Frontend Dev Server",
            8000: "Backend API Server",
            8080: "Web Server",
            5432: "PostgreSQL Database",
            6379: "Redis Cache",
            27017: "MongoDB Database",
            5672: "RabbitMQ",
            15672: "RabbitMQ Management",
            11211: "Memcached",
            3306: "MySQL Database",
        }
        return port_service_map.get(port, "Unknown Service")

    def _get_service_enum(self, service_type: str) -> Optional[ServiceType]:
        """Convert service type string to ServiceType enum"""
        type_mapping = {
            "Frontend Dev Server": ServiceType.FRONTEND,
            "Backend API Server": ServiceType.API_SERVER,
            "Web Server": ServiceType.WEB_SERVER,
            "PostgreSQL Database": ServiceType.DATABASE_POSTGRESQL,
            "Redis Cache": ServiceType.DATABASE_REDIS,
        }
        return type_mapping.get(service_type)

    def _generate_port_resolution_steps(self, port: int, process_info: Optional[Dict[str, Any]],
                                     alternatives: List[int], service_type: str) -> List[str]:
        """Generate resolution steps for port conflicts"""
        steps = []

        if process_info:
            process_name = process_info.get('name', 'unknown process')
            pid = process_info.get('pid', 'N/A')
            steps.append(f"Option 1: Stop the conflicting process '{process_name}' (PID: {pid})")

            # Platform-specific process termination commands
            current_platform = platform.system().lower()
            if current_platform == "windows":
                steps.append(f"  - Windows: taskkill /F /PID {pid}")
                steps.append(f"  - Windows: Open Task Manager and end '{process_name}'")
            elif current_platform == "darwin" or current_platform == "linux":
                steps.append(f"  - Unix: kill -9 {pid}")
                steps.append(f"  - Unix: pkill -f '{process_name}'")

        if alternatives:
            alt_str = ", ".join(map(str, alternatives[:3]))  # Show first 3 alternatives
            steps.append(f"Option 2: Use an alternative port: {alt_str}")
            steps.append(f"  - Configure your {service_type} to use port {alternatives[0]}")

        steps.append(f"Option 3: Find another available port")
        steps.append(f"  - Use port scanner to find available ports")
        steps.append(f"  - Common alternative range: 10000-11000")

        return steps

    async def detect_permission_issues(self, paths: List[str] = None) -> List[PermissionError]:
        """
        Detect permission issues for specified paths using the comprehensive permission diagnostic system

        Args:
            paths: List of file/directory paths to check

        Returns:
            List of permission errors
        """
        self.logger.info("Starting comprehensive permission diagnosis")

        if self.progress_tracker:
            self.progress_tracker.start_task(
                "permission_detection",
                "Comprehensive permission diagnosis and guidance"
            )

        # Use the PermissionDiagnostic module for comprehensive analysis
        diagnosis_result = self.permission_diagnostic.diagnose_permission_issues(paths)

        # Convert diagnosis results to PermissionError objects
        permission_errors = []

        # Check admin privileges
        if not diagnosis_result['admin_check']['has_admin']:
            admin_error = PermissionError(
                resource_path="system",
                required_permissions="administrator/root",
                current_user=diagnosis_result['current_user'],
                admin_required=True,
                platform_specific_guidance={
                    'platform': diagnosis_result['platform'],
                    'suggestions': diagnosis_result['admin_check']['suggestions']
                }
            )
            permission_errors.append(admin_error)

        # Check file permissions
        for path, file_check in diagnosis_result['file_checks'].items():
            if file_check.get('issues'):
                file_error = PermissionError(
                    resource_path=path,
                    required_permissions="read/write/execute",
                    current_user=diagnosis_result['current_user'],
                    admin_required=False,
                    platform_specific_guidance={
                        'platform': diagnosis_result['platform'],
                        'permissions': file_check.get('permissions', 'unknown'),
                        'suggestions': file_check.get('suggestions', [])
                    }
                )
                permission_errors.append(file_error)

        if self.progress_tracker:
            self.progress_tracker.complete_task(
                "permission_detection",
                f"Found {len(permission_errors)} permission issues"
            )

        return permission_errors

    def _get_critical_paths(self) -> List[str]:
        """Get list of critical paths to check permissions for"""
        paths = []

        # Application directories
        current_dir = os.getcwd()
        paths.extend([
            current_dir,
            os.path.join(current_dir, "logs"),
            os.path.join(current_dir, "data"),
            os.path.join(current_dir, "temp"),
        ])

        # System-specific critical paths
        system = platform.system().lower()
        if system == "windows":
            paths.extend([
                os.environ.get("TEMP", "C:\\temp"),
                os.environ.get("ProgramFiles", "C:\\Program Files"),
            ])
        elif system == "darwin":
            paths.extend([
                "/usr/local/bin",
                "/opt/homebrew/bin",
                os.path.expanduser("~/Library/Application Support"),
            ])
        elif system == "linux":
            paths.extend([
                "/usr/local/bin",
                "/tmp",
                os.path.expanduser("~/.local/bin"),
            ])

        return [p for p in paths if os.path.exists(p)]

    def _get_current_user(self) -> str:
        """Get current username"""
        try:
            import getpass
            return getpass.getuser()
        except:
            return os.environ.get("USER", os.environ.get("USERNAME", "unknown"))

    def _check_path_permissions(self, path: str, current_user: str) -> Optional[PermissionError]:
        """Check permissions for a specific path"""
        try:
            # Check if path exists
            if not os.path.exists(path):
                return PermissionError(
                    resource_path=path,
                    required_permissions="read/write access",
                    current_user=current_user,
                    admin_required=False,
                    platform_specific_guidance=self._get_missing_path_guidance(path)
                )

            # Check read permissions
            if not os.access(path, os.R_OK):
                return PermissionError(
                    resource_path=path,
                    required_permissions="read access",
                    current_user=current_user,
                    admin_required=self._requires_admin_for_read(path),
                    platform_specific_guidance=self._get_read_permission_guidance(path)
                )

            # Check write permissions for directories
            if os.path.isdir(path):
                test_file = os.path.join(path, f".permission_test_{int(time.time())}")
                try:
                    with open(test_file, 'w') as f:
                        f.write("test")
                    os.remove(test_file)
                except PermissionError:
                    return PermissionError(
                        resource_path=path,
                        required_permissions="write access",
                        current_user=current_user,
                        admin_required=self._requires_admin_for_write(path),
                        platform_specific_guidance=self._get_write_permission_guidance(path)
                    )

            return None

        except Exception as e:
            self.logger.warning(f"Error checking permissions for {path}: {e}")
            return None

    def _requires_admin_for_read(self, path: str) -> bool:
        """Check if admin rights are required for read access"""
        # System directories typically require admin access
        system_indicators = ["C:\\Windows", "C:\\Program Files", "/usr/bin", "/etc", "/var"]
        return any(indicator in path.lower() for indicator in system_indicators)

    def _requires_admin_for_write(self, path: str) -> bool:
        """Check if admin rights are required for write access"""
        # Most system directories require admin for write access
        system_indicators = ["C:\\Windows", "C:\\Program Files", "/usr", "/etc", "/var", "/opt"]
        return any(indicator in path.lower() for indicator in system_indicators)

    def _get_missing_path_guidance(self, path: str) -> Dict[str, str]:
        """Get guidance for missing paths"""
        system = platform.system().lower()
        guidance = {}

        if system == "windows":
            guidance["windows"] = f"Create directory: mkdir '{path}'"
            guidance["admin"] = f"Run as Administrator and create directory"
        elif system == "darwin" or system == "linux":
            guidance["unix"] = f"Create directory: mkdir -p '{path}'"
            guidance["admin"] = f"Use sudo: sudo mkdir -p '{path}'"

        return guidance

    def _get_read_permission_guidance(self, path: str) -> Dict[str, str]:
        """Get guidance for read permission issues"""
        system = platform.system().lower()
        guidance = {}

        if system == "windows":
            guidance["windows"] = f"Right-click '{path}' → Properties → Security → Edit permissions"
            guidance["admin"] = f"Run as Administrator and change file permissions"
        elif system == "darwin" or system == "linux":
            guidance["unix"] = f"Use 'chmod +r {path}' to add read permission"
            guidance["admin"] = f"Use 'sudo chmod +r {path}' for system files"

        return guidance

    def _get_write_permission_guidance(self, path: str) -> Dict[str, str]:
        """Get guidance for write permission issues"""
        system = platform.system().lower()
        guidance = {}

        if system == "windows":
            guidance["windows"] = f"Right-click '{path}' → Properties → Security → Edit permissions"
            guidance["admin"] = f"Run as Administrator and change file permissions"
        elif system == "darwin" or system == "linux":
            guidance["unix"] = f"Use 'chmod +w {path}' to add write permission"
            guidance["admin"] = f"Use 'sudo chmod +w {path}' for system directories"
            guidance["ownership"] = f"Change ownership: sudo chown $USER:$USER {path}"

        return guidance

    def create_port_conflict_error(self, conflict: PortConflictError) -> ErrorInfo:
        """Create structured error info for port conflicts"""
        code = f"PORT_CONFLICT_{conflict.port}"

        message = f"Port {conflict.port} is occupied"
        if conflict.process_info:
            process_name = conflict.process_info.get('name', 'unknown process')
            message += f" by {process_name}"

        solution = "Port conflict resolution options:\n"
        for i, step in enumerate(conflict.resolution_steps, 1):
            solution += f"{i}. {step}\n"

        details = {
            "port": conflict.port,
            "host": conflict.host,
            "service_type": conflict.service_type,
            "process_info": conflict.process_info,
            "alternative_ports": conflict.alternative_ports,
            "resolution_steps": conflict.resolution_steps
        }

        return ErrorInfo(
            code=code,
            message=message,
            solution=solution.strip(),
            details=details,
            severity=ErrorSeverity.HIGH,
            recovery_type=ErrorRecoveryType.REQUIRES_USER_ACTION,
            category="port_conflict"
        )

    def create_permission_error(self, perm_error: PermissionError) -> ErrorInfo:
        """Create structured error info for permission issues"""
        code = "PERMISSION_DENIED"

        message = f"Permission denied for '{perm_error.resource_path}'"
        if perm_error.required_permissions:
            message += f" (requires {perm_error.required_permissions})"

        solution = "Permission resolution steps:\n"
        system = platform.system().lower()

        if system in perm_error.platform_specific_guidance:
            solution += perm_error.platform_specific_guidance[system]
        else:
            solution += "Check file permissions and try running with elevated privileges if needed"

        if perm_error.admin_required:
            solution += "\nAdministrator privileges may be required for this operation"

        details = {
            "resource_path": perm_error.resource_path,
            "required_permissions": perm_error.required_permissions,
            "current_user": perm_error.current_user,
            "admin_required": perm_error.admin_required,
            "platform_specific_guidance": perm_error.platform_specific_guidance
        }

        return ErrorInfo(
            code=code,
            message=message,
            solution=solution.strip(),
            details=details,
            severity=ErrorSeverity.HIGH if perm_error.admin_required else ErrorSeverity.MEDIUM,
            recovery_type=ErrorRecoveryType.REQUIRES_ADMIN if perm_error.admin_required else ErrorRecoveryType.REQUIRES_USER_ACTION,
            category="permission"
        )

    async def detect_network_connectivity(self, services: List[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Detect network connectivity and service availability issues using the comprehensive network diagnostic system

        Args:
            services: List of services to check (optional)

        Returns:
            List of network issues
        """
        self.logger.info("Starting comprehensive network diagnosis")

        if self.progress_tracker:
            self.progress_tracker.start_task(
                "network_detection",
                "Comprehensive network connectivity and service availability diagnosis"
            )

        # Use the NetworkDiagnostic module for comprehensive analysis
        network_diagnostic = NetworkDiagnostic(self.progress_tracker)
        diagnosis_result = await network_diagnostic.run_comprehensive_diagnosis()

        # Convert diagnosis results to network issue objects
        network_issues = []

        # Analyze connectivity failures
        failed_connectivity = [c for c in diagnosis_result.connectivity_tests
                             if c.status == NetworkStatus.DISCONNECTED]

        for conn in failed_connectivity:
            issue = {
                'type': 'connectivity_failure',
                'target': conn.target,
                'connection_type': conn.connection_type.value,
                'error_message': conn.error_message,
                'response_time': conn.response_time,
                'details': conn.details,
                'severity': self._classify_connectivity_severity(conn)
            }
            network_issues.append(issue)

        # Analyze service availability issues
        failed_services = [s for s in diagnosis_result.service_checks
                         if s.status in [ServiceStatus.UNAVAILABLE, ServiceStatus.ERROR, ServiceStatus.TIMEOUT]]

        for service in failed_services:
            issue = {
                'type': 'service_unavailable',
                'service_name': service.service_name,
                'host': service.host,
                'port': service.port,
                'status': service.status.value,
                'error_message': service.error_message,
                'response_time': service.response_time,
                'http_status': service.http_status,
                'details': service.details,
                'severity': self._classify_service_severity(service)
            }
            network_issues.append(issue)

        # Analyze DNS resolution failures
        failed_dns = [d for d in diagnosis_result.dns_tests
                     if d.status == NetworkStatus.DISCONNECTED]

        for dns in failed_dns:
            issue = {
                'type': 'dns_resolution_failure',
                'domain': dns.domain,
                'record_type': dns.record_type,
                'error_message': dns.error_message,
                'response_time': dns.response_time,
                'dns_server': dns.dns_server,
                'severity': ErrorSeverity.HIGH  # DNS failures are typically critical
            }
            network_issues.append(issue)

        # Add network interface issues
        inactive_interfaces = [i for i in diagnosis_result.interfaces if not i.is_up]
        if inactive_interfaces:
            issue = {
                'type': 'network_interface_down',
                'interfaces': [i.name for i in inactive_interfaces],
                'error_message': f"Network interfaces down: {', '.join(i.name for i in inactive_interfaces)}",
                'severity': ErrorSeverity.MEDIUM
            }
            network_issues.append(issue)

        if self.progress_tracker:
            self.progress_tracker.complete_task(
                "network_detection",
                f"Found {len(network_issues)} network issues"
            )

        return network_issues

    def _classify_connectivity_severity(self, conn) -> ErrorSeverity:
        """分类连接问题的严重程度"""
        if conn.connection_type.value in ['dns']:
            return ErrorSeverity.HIGH
        elif conn.connection_type.value in ['ping']:
            return ErrorSeverity.MEDIUM
        else:
            return ErrorSeverity.MEDIUM

    def _classify_service_severity(self, service) -> ErrorSeverity:
        """分类服务问题的严重程度"""
        if service.status == ServiceStatus.TIMEOUT:
            return ErrorSeverity.MEDIUM
        elif service.status == ServiceStatus.ERROR:
            return ErrorSeverity.HIGH
        elif service.http_status and service.http_status >= 500:
            return ErrorSeverity.HIGH
        elif service.http_status and service.http_status >= 400:
            return ErrorSeverity.MEDIUM
        else:
            return ErrorSeverity.MEDIUM

    def create_network_error(self, network_issue: Dict[str, Any]) -> ErrorInfo:
        """
        Create a standardized network error from network issue data

        Args:
            network_issue: Network issue data

        Returns:
            Standardized ErrorInfo object
        """
        issue_type = network_issue['type']
        severity = network_issue.get('severity', ErrorSeverity.MEDIUM)

        if issue_type == 'connectivity_failure':
            target = network_issue['target']
            conn_type = network_issue['connection_type']
            error_msg = network_issue.get('error_message', 'Connection failed')

            message = f"Cannot connect to {target} via {conn_type}"
            if error_msg:
                message += f": {error_msg}"

            # Distinguish network failures from service issues
            if conn_type in ['dns']:
                category = "dns_resolution"
                solution = self._get_dns_solution(network_issue)
            elif conn_type in ['ping']:
                category = "basic_connectivity"
                solution = self._get_connectivity_solution(network_issue)
            else:
                category = "network_service"
                solution = self._get_service_connectivity_solution(network_issue)

        elif issue_type == 'service_unavailable':
            service_name = network_issue['service_name']
            host = network_issue['host']
            port = network_issue.get('port')
            error_msg = network_issue.get('error_message', 'Service unavailable')

            message = f"Service '{service_name}' at {host}"
            if port:
                message += f":{port}"
            message += f" is unavailable"
            if error_msg:
                message += f": {error_msg}"

            category = "service_availability"
            solution = self._get_service_availability_solution(network_issue)

        elif issue_type == 'dns_resolution_failure':
            domain = network_issue['domain']
            error_msg = network_issue.get('error_message', 'DNS resolution failed')

            message = f"Cannot resolve domain '{domain}'"
            if error_msg:
                message += f": {error_msg}"

            category = "dns_resolution"
            solution = self._get_dns_solution(network_issue)

        elif issue_type == 'network_interface_down':
            interfaces = ', '.join(network_issue['interfaces'])
            message = f"Network interfaces are down: {interfaces}"
            category = "network_interface"
            solution = self._get_interface_solution(network_issue)

        else:
            message = f"Unknown network issue: {network_issue}"
            category = "network"
            solution = ["Run comprehensive network diagnostics", "Check network hardware and drivers"]

        # Build details
        details = {
            'issue_type': issue_type,
            'detection_method': 'NetworkDiagnostic',
            'timestamp': time.time()
        }

        # Add specific details based on issue type
        if 'response_time' in network_issue and network_issue['response_time'] is not None:
            details['response_time'] = f"{network_issue['response_time']:.3f}s"

        if 'details' in network_issue:
            details.update(network_issue['details'])

        # Add diagnostic suggestions
        details['diagnostic_suggestions'] = self._get_network_diagnostic_suggestions(issue_type)

        return ErrorInfo(
            code=f"network_{issue_type}_{int(time.time())}",
            message=message,
            solution='\n'.join(solution) if isinstance(solution, list) else solution,
            details=details,
            severity=severity,
            recovery_type=ErrorRecoveryType.REQUIRES_USER_ACTION,
            category=category
        )

    def _get_dns_solution(self, issue: Dict[str, Any]) -> List[str]:
        """获取DNS问题的解决方案"""
        solutions = [
            "Check DNS configuration in network settings",
            "Try using alternative DNS servers (8.8.8.8, 1.1.1.1)",
            "Flush DNS cache:",
            "  Windows: ipconfig /flushdns",
            "  Linux: sudo systemctl restart systemd-resolved",
            "  Mac: sudo dscacheutil -flushcache",
            "Check internet connectivity",
            "Verify domain spelling"
        ]
        return solutions

    def _get_connectivity_solution(self, issue: Dict[str, Any]) -> List[str]:
        """获取基本连接问题的解决方案"""
        solutions = [
            "Check network cable and Wi-Fi connection",
            "Restart network adapter:",
            "  Windows: Disable/enable in Network Settings",
            "  Linux: sudo systemctl restart NetworkManager",
            "Check router and modem status",
            "Ping local gateway to test local network",
            "Disable VPN if enabled",
            "Check firewall settings"
        ]
        return solutions

    def _get_service_connectivity_solution(self, issue: Dict[str, Any]) -> List[str]:
        """获取服务连接问题的解决方案"""
        solutions = [
            "Verify target service is running",
            "Check if port is blocked by firewall",
            "Test with telnet: telnet <host> <port>",
            "Check network routing to target",
            "Verify proxy settings if applicable",
            "Check for corporate network restrictions"
        ]
        return solutions

    def _get_service_availability_solution(self, issue: Dict[str, Any]) -> List[str]:
        """获取服务可用性问题的解决方案"""
        service_name = issue.get('service_name', 'Service')
        host = issue.get('host', 'localhost')
        port = issue.get('port')

        solutions = [
            f"Check if {service_name} service is running",
            f"Verify service configuration and bindings",
            f"Check service logs for errors",
            f"Test service locally: curl http://{host}:{port or '80'}/",
            f"Restart the service if necessary",
            f"Check system resources (memory, CPU)",
            f"Verify port is not blocked by firewall"
        ]

        if port:
            solutions.append(f"Check port {port} availability: netstat -an | findstr :{port}")

        return solutions

    def _get_interface_solution(self, issue: Dict[str, Any]) -> List[str]:
        """获取网络接口问题的解决方案"""
        interfaces = issue.get('interfaces', [])
        solutions = [
            "Check network adapter hardware",
            "Update network drivers",
            "Restart network services:",
            "  Windows: Restart Network List Service",
            "  Linux: sudo systemctl restart networking",
            "Check physical cable connections",
            "Reset network adapter:",
            "  Windows: netsh winsock reset",
            "  Linux: sudo ip link set <interface> down && sudo ip link set <interface> up"
        ]

        if interfaces:
            solutions.append(f"Enable disabled interfaces: {', '.join(interfaces)}")

        return solutions

    def _get_network_diagnostic_suggestions(self, issue_type: str) -> List[str]:
        """获取网络诊断建议"""
        suggestions = [
            "Run comprehensive network diagnostics",
            "Test with different network tools (ping, traceroute, nslookup)",
            "Check network status indicators",
            "Try connecting to different targets"
        ]

        if issue_type == 'dns_resolution_failure':
            suggestions.extend([
                "Test with multiple DNS servers",
                "Check DNS server response times",
                "Verify DNS propagation"
            ])
        elif issue_type == 'service_unavailable':
            suggestions.extend([
                "Check service health endpoints",
                "Monitor service response times",
                "Test service with different clients"
            ])

        return suggestions

    async def run_comprehensive_detection(self, host: str = "localhost",
                                        required_ports: List[int] = None,
                                        check_paths: List[str] = None) -> Dict[str, List[ErrorInfo]]:
        """
        Run comprehensive error detection for all categories

        Args:
            host: Host to check for port conflicts
            required_ports: List of required ports
            check_paths: List of paths to check for permissions

        Returns:
            Dictionary of error categories and their errors
        """
        self.logger.info("Starting comprehensive error detection...")

        if self.progress_tracker:
            self.progress_tracker.start_task(
                "comprehensive_error_detection",
                "Running comprehensive error detection"
            )

        results = {}

        # Detect port conflicts
        port_conflicts = await self.detect_port_conflicts(host, required_ports)
        results["port_conflicts"] = [
            self.create_port_conflict_error(conflict) for conflict in port_conflicts
        ]

        # Detect permission issues
        permission_issues = await self.detect_permission_issues(check_paths)
        results["permission_issues"] = [
            self.create_permission_error(issue) for issue in permission_issues
        ]

        # Network connectivity and service availability detection (Task 3)
        network_issues = await self.detect_network_connectivity()
        results["network_issues"] = [
            self.create_network_error(issue) for issue in network_issues
        ]

        # Dependency conflict detection (Task 4)
        dependency_conflicts = await self.detect_dependency_conflicts()
        results["dependency_conflicts"] = [
            self.create_dependency_error(issue) for issue in dependency_conflicts
        ]

        # Error classification and recovery assessment (Task 5)
        classifications = await self.classify_all_errors(results)
        recovery_plans = await self.generate_recovery_plans_for_errors(classifications)
        results["error_classifications"] = classifications
        results["recovery_plans"] = recovery_plans

        if self.progress_tracker:
            total_errors = sum(len(errors) for errors in results.values())
            self.progress_tracker.complete_task(
                "comprehensive_error_detection",
                f"Found {total_errors} total errors across {len(results)} categories"
            )

        return results

    async def detect_dependency_conflicts(self, project_path: str = None) -> List[Dict[str, Any]]:
        """
        Detect dependency version conflicts using the comprehensive dependency conflict detection system

        Args:
            project_path: Project path to analyze (optional)

        Returns:
            List of dependency conflict issues
        """
        self.logger.info("Starting comprehensive dependency conflict detection")

        if self.progress_tracker:
            self.progress_tracker.start_task(
                "dependency_conflict_detection",
                "Comprehensive dependency version conflict detection and resolution"
            )

        # Use the DependencyConflictDetector module for comprehensive analysis
        dependency_detector = DependencyConflictDetector(self.progress_tracker)
        analysis_result = await dependency_detector.analyze_dependencies(project_path)

        # Convert analysis results to dependency conflict issue objects
        dependency_issues = []

        # Analyze version conflicts
        for conflict in analysis_result.conflicts:
            issue = {
                'type': 'dependency_conflict',
                'dependency_name': conflict.dependency_name,
                'dependency_type': conflict.dependency_type.value,
                'conflict_type': conflict.conflict_type,
                'severity': conflict.severity.value,
                'current_version': conflict.current_version,
                'required_version': conflict.required_version,
                'description': conflict.description,
                'affected_dependencies': conflict.affected_dependencies,
                'resolution_options': conflict.resolution_options,
                'details': conflict.details
            }
            dependency_issues.append(issue)

        # Analyze missing dependencies
        missing_deps = [conflict for conflict in analysis_result.conflicts
                        if conflict.conflict_type == 'missing_dependency']
        for missing in missing_deps:
            issue = {
                'type': 'missing_dependency',
                'dependency_name': missing.dependency_name,
                'dependency_type': missing.dependency_type.value,
                'severity': missing.severity.value,
                'description': missing.description,
                'resolution_options': missing.resolution_options,
                'details': missing.details
            }
            dependency_issues.append(issue)

        if self.progress_tracker:
            self.progress_tracker.complete_task(
                "dependency_conflict_detection",
                f"Found {len(dependency_issues)} dependency issues"
            )

        return dependency_issues

    def create_dependency_error(self, dependency_issue: Dict[str, Any]) -> ErrorInfo:
        """
        Create a standardized dependency error from dependency issue data

        Args:
            dependency_issue: Dependency issue data

        Returns:
            Standardized ErrorInfo object
        """
        issue_type = dependency_issue['type']
        dependency_name = dependency_issue['dependency_name']
        dependency_type = dependency_issue.get('dependency_type', 'unknown')
        severity_str = dependency_issue.get('severity', 'medium')

        # Map severity string to enum
        severity_map = {
            'low': ErrorSeverity.LOW,
            'medium': ErrorSeverity.MEDIUM,
            'high': ErrorSeverity.HIGH,
            'critical': ErrorSeverity.CRITICAL
        }
        severity = severity_map.get(severity_str, ErrorSeverity.MEDIUM)

        if issue_type == 'dependency_conflict':
            current_version = dependency_issue.get('current_version', 'unknown')
            required_version = dependency_issue.get('required_version', 'unknown')
            conflict_type = dependency_issue.get('conflict_type', 'unknown')

            message = f"Dependency conflict for '{dependency_name}' ({dependency_type})"
            if current_version != 'unknown' and required_version != 'unknown':
                message += f": current {current_version}, required {required_version}"
            elif conflict_type == 'version_mismatch':
                message += f": version mismatch detected"

            category = "dependency_conflict"
            solution = self._get_dependency_conflict_solution(dependency_issue)

        elif issue_type == 'missing_dependency':
            message = f"Missing dependency '{dependency_name}' ({dependency_type})"
            category = "missing_dependency"
            solution = self._get_missing_dependency_solution(dependency_issue)

        else:
            message = f"Unknown dependency issue: {dependency_name}"
            category = "dependency"
            solution = ["Run dependency installation commands", "Check package manager configuration"]

        # Build details
        details = {
            'issue_type': issue_type,
            'dependency_name': dependency_name,
            'dependency_type': dependency_type,
            'detection_method': 'DependencyConflictDetector',
            'timestamp': time.time()
        }

        # Add specific details based on issue type
        if 'current_version' in dependency_issue:
            details['current_version'] = dependency_issue['current_version']
        if 'required_version' in dependency_issue:
            details['required_version'] = dependency_issue['required_version']
        if 'affected_dependencies' in dependency_issue:
            details['affected_dependencies'] = dependency_issue['affected_dependencies']

        # Add resolution options
        if 'resolution_options' in dependency_issue:
            details['resolution_options'] = dependency_issue['resolution_options']

        # Add diagnostic suggestions
        details['diagnostic_suggestions'] = self._get_dependency_diagnostic_suggestions(issue_type)

        return ErrorInfo(
            code=f"dependency_{issue_type}_{dependency_name}_{int(time.time())}",
            message=message,
            solution='\n'.join(solution) if isinstance(solution, list) else solution,
            details=details,
            severity=severity,
            recovery_type=ErrorRecoveryType.REQUIRES_USER_ACTION,
            category=category
        )

    def _get_dependency_conflict_solution(self, issue: Dict[str, Any]) -> List[str]:
        """获取依赖冲突解决方案"""
        dependency_name = issue['dependency_name']
        dependency_type = issue.get('dependency_type', 'unknown')
        resolution_options = issue.get('resolution_options', [])

        solutions = [
            f"Review dependency requirements for {dependency_name}",
            f"Check version compatibility with other dependencies",
            f"Consider using a virtual environment to isolate dependencies"
        ]

        # Add specific resolution commands
        for option in resolution_options:
            if option.get('command'):
                solutions.append(f"Execute: {option['command']}")
            if option.get('description'):
                solutions.append(f"Option: {option['description']}")

        # Add dependency type specific solutions
        if dependency_type == 'python_pip':
            solutions.extend([
                f"Update requirements.txt with compatible version for {dependency_name}",
                f"Run: pip install {dependency_name}==<compatible_version>",
                f"Consider using pip-tools for dependency pinning"
            ])
        elif dependency_type == 'node_npm':
            solutions.extend([
                f"Update package.json with compatible version for {dependency_name}",
                f"Run: npm install {dependency_name}@<compatible_version>",
                f"Consider using npm shrinkwrap for dependency locking"
            ])

        return solutions

    def _get_missing_dependency_solution(self, issue: Dict[str, Any]) -> List[str]:
        """获取缺失依赖解决方案"""
        dependency_name = issue['dependency_name']
        dependency_type = issue.get('dependency_type', 'unknown')
        resolution_options = issue.get('resolution_options', [])

        solutions = [
            f"Install missing dependency '{dependency_name}'",
            f"Check if dependency name is correct"
        ]

        # Add specific installation commands
        for option in resolution_options:
            if option.get('command'):
                solutions.append(f"Execute: {option['command']}")

        # Add dependency type specific solutions
        if dependency_type == 'python_pip':
            solutions.extend([
                f"Run: pip install {dependency_name}",
                f"Check if package exists in PyPI",
                f"Verify Python and pip versions"
            ])
        elif dependency_type == 'node_npm':
            solutions.extend([
                f"Run: npm install {dependency_name}",
                f"Check if package exists in npm registry",
                f"Verify Node.js and npm versions"
            ])

        return solutions

    def _get_dependency_diagnostic_suggestions(self, issue_type: str) -> List[str]:
        """获取依赖诊断建议"""
        suggestions = [
            "Run comprehensive dependency analysis",
            "Check dependency manifest files (requirements.txt, package.json)",
            "Review dependency version constraints",
            "Use dependency management best practices"
        ]

        if issue_type == 'dependency_conflict':
            suggestions.extend([
                "Use semantic versioning for better compatibility",
                "Pin dependency versions for stable builds",
                "Consider using dependency management tools"
            ])
        elif issue_type == 'missing_dependency':
            suggestions.extend([
                "Verify all required dependencies are listed",
                "Check package manager configuration",
                "Run package manager in verbose mode for debugging"
            ])

        return suggestions

    # Error Classification and Recovery Assessment Methods (Task 5)

    async def classify_all_errors(self, error_results: Dict[str, List[ErrorInfo]]) -> List[Dict[str, Any]]:
        """
        Classify all detected errors using the advanced error classification system

        Args:
            error_results: Dictionary of error categories and their errors

        Returns:
            List of error classification results
        """
        self.logger.info("Starting comprehensive error classification")

        if self.progress_tracker:
            self.progress_tracker.start_task(
                "error_classification",
                "Classifying all detected errors with advanced taxonomy"
            )

        classifications = []

        # Flatten all errors from all categories
        all_errors = []
        for category, errors in error_results.items():
            if category in ["error_classifications", "recovery_plans"]:
                continue  # Skip existing classification results
            for error in errors:
                all_errors.append((category, error))

        # Classify each error
        for category, error in all_errors:
            try:
                # Extract error message and context
                error_message = error.message
                error_code = getattr(error, 'code', None)
                context = {
                    'category': category,
                    'severity': error.severity.value if hasattr(error, 'severity') else 'unknown',
                    'details': error.details
                }

                # Classify the error
                classification = await self.error_classifier.classify_error(
                    error_message, error_code, context
                )

                # Assess severity with impact context
                impact_context = self._create_impact_context(error, category)
                adjusted_severity = self.error_classifier.assess_severity(classification, impact_context)

                # Update classification with adjusted severity
                classification.severity = adjusted_severity

                classifications.append({
                    'error_info': error,
                    'classification': classification,
                    'category': category,
                    'recovery_assessment': self._assess_recovery_options(classification)
                })

            except Exception as e:
                self.logger.error(f"Error classifying error: {e}")
                # Create fallback classification
                fallback_classification = {
                    'error_info': error,
                    'classification': None,
                    'category': category,
                    'error': str(e)
                }
                classifications.append(fallback_classification)

        if self.progress_tracker:
            self.progress_tracker.complete_task(
                "error_classification",
                f"Classified {len(classifications)} errors"
            )

        return classifications

    def _create_impact_context(self, error: ErrorInfo, category: str) -> Dict[str, Any]:
        """Create impact context for severity assessment"""
        impact_context = {
            'service_impact': 'medium',
            'user_impact': 'medium',
            'system_impact': 'low',
            'recovery_difficulty': 'moderate'
        }

        # Category-specific impact assessment
        if category == 'port_conflicts':
            impact_context['service_impact'] = 'high'
            impact_context['user_impact'] = 'high'
            impact_context['recovery_difficulty'] = 'simple'
        elif category == 'permission_issues':
            impact_context['service_impact'] = 'high'
            impact_context['recovery_difficulty'] = 'moderate'
        elif category == 'network_issues':
            impact_context['service_impact'] = 'critical'
            impact_context['user_impact'] = 'critical'
            impact_context['system_impact'] = 'high'
            impact_context['recovery_difficulty'] = 'moderate'
        elif category == 'dependency_conflicts':
            impact_context['service_impact'] = 'critical'
            impact_context['recovery_difficulty'] = 'moderate'

        # Severity-based adjustments
        if hasattr(error, 'severity'):
            if error.severity.value >= 3:  # HIGH or CRITICAL
                impact_context['service_impact'] = 'critical'
                impact_context['user_impact'] = 'high'

        return impact_context

    def _assess_recovery_options(self, classification: ErrorClassification) -> Dict[str, Any]:
        """Assess recovery options for classified error"""
        recovery_assessment = {
            'recoverable': classification.recoverability.value,
            'complexity': classification.complexity.name,
            'estimated_time': self._estimate_recovery_time_by_complexity(classification.complexity),
            'success_probability': self._calculate_success_probability_by_type(classification),
            'automated_recovery_available': classification.complexity == RecoveryComplexity.AUTOMATIC,
            'user_action_required': classification.complexity in [
                RecoveryComplexity.SIMPLE, RecoveryComplexity.MODERATE
            ],
            'expert_assistance_required': classification.complexity in [
                RecoveryComplexity.COMPLEX, RecoveryComplexity.EXPERT
            ]
        }

        return recovery_assessment

    def _estimate_recovery_time_by_complexity(self, complexity: RecoveryComplexity) -> str:
        """Estimate recovery time based on complexity"""
        time_estimates = {
            RecoveryComplexity.AUTOMATIC: "1-2 minutes",
            RecoveryComplexity.SIMPLE: "5-10 minutes",
            RecoveryComplexity.MODERATE: "15-30 minutes",
            RecoveryComplexity.COMPLEX: "30-60 minutes",
            RecoveryComplexity.EXPERT: "1-2 hours"
        }
        return time_estimates.get(complexity, "Unknown")

    def _calculate_success_probability_by_type(self, classification: ErrorClassification) -> float:
        """Calculate success probability based on error type and recoverability"""
        base_probability = 0.7

        # Adjust based on recoverability
        if classification.recoverability == ErrorRecoverability.FULLY_RECOVERABLE:
            base_probability = 0.9
        elif classification.recoverability == ErrorRecoverability.PARTIALLY_RECOVERABLE:
            base_probability = 0.7
        elif classification.recoverability == ErrorRecoverability.WORKAROUND_AVAILABLE:
            base_probability = 0.8
        elif classification.recoverability == ErrorRecoverability.NON_RECOVERABLE:
            base_probability = 0.2
        elif classification.recoverability == ErrorRecoverability.REQUIRES_REINSTALLATION:
            base_probability = 0.6

        # Adjust based on complexity
        if classification.complexity == RecoveryComplexity.AUTOMATIC:
            base_probability += 0.1
        elif classification.complexity == RecoveryComplexity.EXPERT:
            base_probability -= 0.3

        return max(0.1, min(0.95, base_probability))

    async def generate_recovery_plans_for_errors(self, classifications: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Generate recovery plans for all classified errors

        Args:
            classifications: List of error classification results

        Returns:
            List of recovery plans
        """
        self.logger.info("Generating recovery plans for classified errors")

        if self.progress_tracker:
            self.progress_tracker.start_task(
                "recovery_plan_generation",
                "Generating comprehensive recovery plans"
            )

        recovery_plans = []

        for classification_result in classifications:
            if classification_result.get('classification') is None:
                continue

            classification = classification_result['classification']
            error_info = classification_result['error_info']

            try:
                # Generate recovery plan
                recovery_plan = self.error_classifier.generate_recovery_plan(
                    classification,
                    classification_result.get('recovery_assessment', {})
                )

                recovery_plans.append({
                    'error_info': error_info,
                    'classification': classification,
                    'recovery_plan': recovery_plan,
                    'priority': self._calculate_recovery_priority(classification),
                    'automated_actions': self._identify_automated_actions(recovery_plan)
                })

            except Exception as e:
                self.logger.error(f"Error generating recovery plan: {e}")
                recovery_plans.append({
                    'error_info': error_info,
                    'classification': classification,
                    'recovery_plan': None,
                    'error': str(e)
                })

        if self.progress_tracker:
            self.progress_tracker.complete_task(
                "recovery_plan_generation",
                f"Generated {len(recovery_plans)} recovery plans"
            )

        return recovery_plans

    def _calculate_recovery_priority(self, classification: ErrorClassification) -> int:
        """Calculate recovery priority (higher number = higher priority)"""
        priority = 0

        # Severity-based priority
        priority += classification.severity.value * 10

        # Recoverability-based priority (more recoverable gets lower priority for immediate action)
        if classification.recoverability == ErrorRecoverability.NON_RECOVERABLE:
            priority += 20
        elif classification.recoverability == ErrorRecoverability.REQUIRES_REINSTALLATION:
            priority += 15
        elif classification.recoverability == ErrorRecoverability.FULLY_RECOVERABLE:
            priority += 5

        # Complexity-based priority (simpler gets higher priority)
        if classification.complexity == RecoveryComplexity.AUTOMATIC:
            priority += 10
        elif classification.complexity == RecoveryComplexity.SIMPLE:
            priority += 8
        elif classification.complexity == RecoveryComplexity.EXPERT:
            priority -= 5

        # Confidence-based priority
        priority += int(classification.confidence * 5)

        return max(1, priority)

    def _identify_automated_actions(self, recovery_plan: RecoveryPlan) -> List[str]:
        """Identify actions that can be automated"""
        automated_actions = []

        for action in recovery_plan.actions:
            if action.automated:
                automated_actions.append(action.action_id)
            elif action.risk_level == "low" and action.command:
                # Low-risk commands can often be automated
                automated_actions.append(action.action_id)

        return automated_actions

    async def get_error_summary_report(self, classifications: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate comprehensive error summary report

        Args:
            classifications: List of error classification results

        Returns:
            Comprehensive error summary report
        """
        if not classifications:
            return {
                'total_errors': 0,
                'categories': {},
                'severities': {},
                'recoverabilities': {},
                'complexities': {},
                'recommendations': []
            }

        # Extract classifications
        valid_classifications = [
            c['classification'] for c in classifications
            if c.get('classification') is not None
        ]

        # Get statistics from classifier
        stats = self.error_classifier.get_error_statistics(valid_classifications)

        # Generate recommendations
        recommendations = self._generate_recommendations(valid_classifications)

        # Create prioritized action items
        action_items = self._create_action_items(classifications)

        return {
            'total_errors': len(classifications),
            'successfully_classified': len(valid_classifications),
            'classification_success_rate': len(valid_classifications) / len(classifications) * 100,
            'statistics': stats,
            'recommendations': recommendations,
            'action_items': action_items,
            'recovery_summary': self._create_recovery_summary(classifications)
        }

    def _generate_recommendations(self, classifications: List[ErrorClassification]) -> List[str]:
        """Generate system-wide recommendations based on error patterns"""
        recommendations = []

        # Analyze common patterns
        category_counts = {}
        for classification in classifications:
            cat = classification.category.value
            category_counts[cat] = category_counts.get(cat, 0) + 1

        # Category-specific recommendations
        if category_counts.get('network', 0) > 0:
            recommendations.append(
                "Consider implementing network monitoring and automatic failover mechanisms"
            )
        if category_counts.get('dependency', 0) > 1:
            recommendations.append(
                "Implement dependency management with version pinning to prevent conflicts"
            )
        if category_counts.get('permission', 0) > 0:
            recommendations.append(
                "Review and standardize file permissions and service configurations"
            )
        if category_counts.get('port_conflict', 0) > 0:
            recommendations.append(
                "Implement dynamic port allocation or service discovery mechanisms"
            )

        # Severity-based recommendations
        critical_errors = [c for c in classifications if c.severity == ErrorSeverity.CRITICAL]
        if critical_errors:
            recommendations.append(
                f"Immediate attention required: {len(critical_errors)} critical errors detected"
            )

        return recommendations

    def _create_action_items(self, classifications: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Create prioritized action items from classifications"""
        action_items = []

        for classification_result in classifications:
            if classification_result.get('classification') is None:
                continue

            classification = classification_result['classification']
            recovery_assessment = classification_result.get('recovery_assessment', {})

            action_item = {
                'error_id': classification.error_id,
                'category': classification.category.value,
                'subcategory': classification.subcategory.value,
                'severity': classification.severity.name,
                'recoverability': classification.recoverability.value,
                'complexity': classification.complexity.name,
                'confidence': classification.confidence,
                'priority': self._calculate_recovery_priority(classification),
                'estimated_time': recovery_assessment.get('estimated_time', 'Unknown'),
                'success_probability': recovery_assessment.get('success_probability', 0.5),
                'automated_available': recovery_assessment.get('automated_recovery_available', False),
                'description': classification.metadata.get('original_message', 'No description available')
            }

            action_items.append(action_item)

        # Sort by priority (descending)
        action_items.sort(key=lambda x: x['priority'], reverse=True)

        return action_items

    def _create_recovery_summary(self, classifications: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create recovery summary statistics"""
        total_classified = sum(1 for c in classifications if c.get('classification') is not None)

        if total_classified == 0:
            return {
                'total_classified': 0,
                'fully_recoverable': 0,
                'partially_recoverable': 0,
                'non_recoverable': 0,
                'automated_recovery_available': 0,
                'requires_expert_assistance': 0
            }

        recoverability_counts = {}
        complexity_counts = {}
        automated_available = 0
        expert_required = 0

        for classification_result in classifications:
            classification = classification_result.get('classification')
            if not classification:
                continue

            # Count recoverability types
            rec = classification.recoverability.value
            recoverability_counts[rec] = recoverability_counts.get(rec, 0) + 1

            # Count complexity types
            comp = classification.complexity.name
            complexity_counts[comp] = complexity_counts.get(comp, 0) + 1

            # Count automated recovery options
            if classification.complexity == RecoveryComplexity.AUTOMATIC:
                automated_available += 1

            # Count expert assistance requirements
            if classification.complexity in [RecoveryComplexity.COMPLEX, RecoveryComplexity.EXPERT]:
                expert_required += 1

        return {
            'total_classified': total_classified,
            'recoverability_breakdown': recoverability_counts,
            'complexity_breakdown': complexity_counts,
            'fully_recoverable_count': recoverability_counts.get('fully_recoverable', 0),
            'partially_recoverable_count': recoverability_counts.get('partially_recoverable', 0),
            'non_recoverable_count': recoverability_counts.get('non_recoverable', 0),
            'automated_recovery_available': automated_available,
            'requires_expert_assistance': expert_required,
            'automated_recovery_percentage': (automated_available / total_classified) * 100,
            'expert_assistance_percentage': (expert_required / total_classified) * 100
        }