"""
Error Classification and Recovery Assessment System

This module provides comprehensive error classification capabilities including
error taxonomy, severity assessment, recovery evaluation, and solution matching.
"""

import time
import re
import platform
from typing import Dict, List, Optional, Tuple, Union, Any
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from utils.logger import get_logger
from utils.progress_tracker import ProgressTracker

logger = get_logger(__name__)


class ErrorCategory(Enum):
    """Primary error categories based on system architecture"""
    NETWORK = "network"
    PORT_CONFLICT = "port_conflict"
    PERMISSION = "permission"
    DEPENDENCY = "dependency"
    SERVICE_UNAVAILABLE = "service_unavailable"
    SYSTEM_RESOURCE = "system_resource"
    CONFIGURATION = "configuration"
    ENVIRONMENT = "environment"
    UNKNOWN = "unknown"


class ErrorSubcategory(Enum):
    """Detailed error subcategories for precise classification"""
    # Network subcategories
    CONNECTIVITY_FAILURE = "connectivity_failure"
    DNS_RESOLUTION = "dns_resolution"
    FIREWALL_BLOCKED = "firewall_blocked"
    PROXY_ISSUE = "proxy_issue"
    TIMEOUT = "timeout"

    # Port conflict subcategories
    PROCESS_OCCUPATION = "process_occupation"
    SYSTEM_SERVICE = "system_service"
    APPLICATION_CONFLICT = "application_conflict"

    # Permission subcategories
    FILE_ACCESS = "file_access"
    ADMIN_PRIVILEGE = "admin_privilege"
    SERVICE_PERMISSION = "service_permission"
    EXECUTION_RIGHTS = "execution_rights"

    # Dependency subcategories
    VERSION_CONFLICT = "version_conflict"
    MISSING_PACKAGE = "missing_package"
    INCOMPATIBLE_VERSION = "incompatible_version"
    CIRCULAR_DEPENDENCY = "circular_dependency"

    # Service unavailable subcategories
    SERVICE_NOT_RUNNING = "service_not_running"
    HEALTH_CHECK_FAILED = "health_check_failed"
    ENDPOINT_UNREACHABLE = "endpoint_unreachable"

    # System resource subcategories
    MEMORY_INSUFFICIENT = "memory_insufficient"
    DISK_SPACE_LOW = "disk_space_low"
    CPU_OVERLOAD = "cpu_overload"

    # Configuration subcategories
    INVALID_CONFIG = "invalid_config"
    MISSING_CONFIG = "missing_config"
    CONFIG_MISMATCH = "config_mismatch"

    # Environment subcategories
    PATH_MISSING = "path_missing"
    ENV_VARIABLE_MISSING = "env_variable_missing"
    VERSION_MISMATCH = "version_mismatch"


class ErrorSeverity(Enum):
    """Error severity levels with priority ordering"""
    CRITICAL = 4      # System-breaking errors requiring immediate attention
    HIGH = 3         # Major functionality impact
    MEDIUM = 2       # Partial functionality impact
    LOW = 1          # Minor issues with workarounds available
    INFO = 0         # Informational messages


class RecoveryComplexity(Enum):
    """Complexity levels for error recovery procedures"""
    AUTOMATIC = 1        # Can be resolved automatically
    SIMPLE = 2          # Basic user action required
    MODERATE = 3        # Multiple steps or technical knowledge needed
    COMPLEX = 4         # Advanced troubleshooting required
    EXPERT = 5          # Requires expert intervention


class ErrorRecoverability(Enum):
    """Error recoverability assessment"""
    FULLY_RECOVERABLE = "fully_recoverable"          # Complete restoration possible
    PARTIALLY_RECOVERABLE = "partially_recoverable"  # Partial recovery with limitations
    WORKAROUND_AVAILABLE = "workaround_available"     # Alternative solution exists
    NON_RECOVERABLE = "non_recoverable"              # Cannot be recovered
    REQUIRES_REINSTALLATION = "requires_reinstallation"  # Fresh setup needed


@dataclass
class ErrorPattern:
    """Error pattern for classification matching"""
    pattern_id: str
    name: str
    category: ErrorCategory
    subcategory: ErrorSubcategory
    severity: ErrorSeverity
    recoverability: ErrorRecoverability
    complexity: RecoveryComplexity
    keywords: List[str] = field(default_factory=list)
    regex_patterns: List[str] = field(default_factory=list)
    error_codes: List[str] = field(default_factory=list)
    contexts: List[str] = field(default_factory=list)

    def matches(self, error_message: str, error_code: str = None, context: Dict[str, Any] = None) -> bool:
        """Check if this pattern matches the given error"""
        error_lower = error_message.lower()

        # Check keywords
        for keyword in self.keywords:
            if keyword.lower() in error_lower:
                return True

        # Check regex patterns
        for pattern in self.regex_patterns:
            try:
                if re.search(pattern, error_message, re.IGNORECASE):
                    return True
            except re.error:
                logger.warning(f"Invalid regex pattern: {pattern}")

        # Check error codes
        if error_code and error_code in self.error_codes:
            return True

        # Check contexts
        if context:
            for ctx_key in self.contexts:
                if ctx_key in context:
                    return True

        return False


@dataclass
class ErrorClassification:
    """Complete error classification result"""
    error_id: str
    category: ErrorCategory
    subcategory: ErrorSubcategory
    severity: ErrorSeverity
    recoverability: ErrorRecoverability
    complexity: RecoveryComplexity
    confidence: float  # 0.0 to 1.0
    patterns_matched: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


@dataclass
class RecoveryAction:
    """Individual recovery action step"""
    action_id: str
    description: str
    command: Optional[str] = None
    expected_result: Optional[str] = None
    verification_step: Optional[str] = None
    risk_level: str = "low"  # low, medium, high
    automated: bool = False
    platform_specific: Dict[str, str] = field(default_factory=dict)


@dataclass
class RecoveryPlan:
    """Complete recovery plan for classified error"""
    plan_id: str
    error_id: str
    title: str
    description: str
    estimated_time: str
    success_probability: float
    actions: List[RecoveryAction] = field(default_factory=list)
    prerequisites: List[str] = field(default_factory=list)
    rollback_plan: List[str] = field(default_factory=list)
    verification_steps: List[str] = field(default_factory=list)
    alternative_solutions: List[str] = field(default_factory=list)


class ErrorClassifier:
    """
    Advanced error classification and recovery assessment system
    """

    def __init__(self, progress_tracker: Optional[ProgressTracker] = None):
        """Initialize the error classifier"""
        self.progress_tracker = progress_tracker
        self.logger = get_logger(self.__class__.__name__)
        self.platform = platform.system().lower()

        # Initialize classification patterns
        self.patterns = self._load_error_patterns()
        self.severity_weights = self._load_severity_weights()
        self.recovery_templates = self._load_recovery_templates()

        # Classification cache
        self.classification_cache = {}

        self.logger.info(f"ErrorClassifier initialized for platform: {self.platform}")

    def _load_error_patterns(self) -> Dict[str, ErrorPattern]:
        """Load comprehensive error pattern database"""
        patterns = {}

        # Network connectivity patterns
        patterns['network_dns_failure'] = ErrorPattern(
            pattern_id="network_dns_failure",
            name="DNS Resolution Failure",
            category=ErrorCategory.NETWORK,
            subcategory=ErrorSubcategory.DNS_RESOLUTION,
            severity=ErrorSeverity.HIGH,
            recoverability=ErrorRecoverability.FULLY_RECOVERABLE,
            complexity=RecoveryComplexity.MODERATE,
            keywords=["dns", "name resolution", "could not resolve", "unknown host"],
            regex_patterns=[r"could not resolve host", r"dns.*failed", r"name resolution error"],
            error_codes=["DNS_ERROR", "EAI_NONAME"]
        )

        patterns['network_connectivity'] = ErrorPattern(
            pattern_id="network_connectivity",
            name="Network Connectivity Failure",
            category=ErrorCategory.NETWORK,
            subcategory=ErrorSubcategory.CONNECTIVITY_FAILURE,
            severity=ErrorSeverity.CRITICAL,
            recoverability=ErrorRecoverability.PARTIALLY_RECOVERABLE,
            complexity=RecoveryComplexity.MODERATE,
            keywords=["connection refused", "network unreachable", "no route to host", "timeout"],
            regex_patterns=[r"connection.*refused", r"network.*unreachable", r"no route to host"],
            error_codes=["ECONNREFUSED", "ENETUNREACH", "ETIMEDOUT"]
        )

        patterns['network_firewall'] = ErrorPattern(
            pattern_id="network_firewall",
            name="Firewall Blocking Connection",
            category=ErrorCategory.NETWORK,
            subcategory=ErrorSubcategory.FIREWALL_BLOCKED,
            severity=ErrorSeverity.MEDIUM,
            recoverability=ErrorRecoverability.FULLY_RECOVERABLE,
            complexity=RecoveryComplexity.COMPLEX,
            keywords=["firewall", "blocked", "access denied", "forbidden"],
            regex_patterns=[r"firewall.*blocked", r"access.*denied", r"connection.*blocked"],
            error_codes=["EACCES", "EPERM"]
        )

        # Port conflict patterns
        patterns['port_process_occupation'] = ErrorPattern(
            pattern_id="port_process_occupation",
            name="Port Already in Use",
            category=ErrorCategory.PORT_CONFLICT,
            subcategory=ErrorSubcategory.PROCESS_OCCUPATION,
            severity=ErrorSeverity.HIGH,
            recoverability=ErrorRecoverability.FULLY_RECOVERABLE,
            complexity=RecoveryComplexity.SIMPLE,
            keywords=["port already in use", "address already in use", "bind", "occupied"],
            regex_patterns=[r"port.*already in use", r"address.*already in use", r"bind.*failed"],
            error_codes=["EADDRINUSE", "EADDRNOTAVAIL"]
        )

        # Permission patterns
        patterns['permission_admin_required'] = ErrorPattern(
            pattern_id="permission_admin_required",
            name="Administrator Privileges Required",
            category=ErrorCategory.PERMISSION,
            subcategory=ErrorSubcategory.ADMIN_PRIVILEGE,
            severity=ErrorSeverity.HIGH,
            recoverability=ErrorRecoverability.FULLY_RECOVERABLE,
            complexity=RecoveryComplexity.SIMPLE,
            keywords=["administrator", "root", "privilege", "access denied", "permission denied"],
            regex_patterns=[r"administrator.*required", r"root.*privilege", r"access.*denied"],
            error_codes=["EPERM", "EACCES"]
        )

        patterns['permission_file_access'] = ErrorPattern(
            pattern_id="permission_file_access",
            name="File Access Permission Denied",
            category=ErrorCategory.PERMISSION,
            subcategory=ErrorSubcategory.FILE_ACCESS,
            severity=ErrorSeverity.MEDIUM,
            recoverability=ErrorRecoverability.FULLY_RECOVERABLE,
            complexity=RecoveryComplexity.MODERATE,
            keywords=["permission denied", "access denied", "read only", "write protected"],
            regex_patterns=[r"permission.*denied", r"access.*denied", r"read.*only"],
            error_codes=["EPERM", "EACCES", "EROFS"]
        )

        # Dependency patterns
        patterns['dependency_version_conflict'] = ErrorPattern(
            pattern_id="dependency_version_conflict",
            name="Dependency Version Conflict",
            category=ErrorCategory.DEPENDENCY,
            subcategory=ErrorSubcategory.VERSION_CONFLICT,
            severity=ErrorSeverity.HIGH,
            recoverability=ErrorRecoverability.FULLY_RECOVERABLE,
            complexity=RecoveryComplexity.MODERATE,
            keywords=["version conflict", "incompatible version", "dependency", "requires"],
            regex_patterns=[r"version.*conflict", r"incompatible.*version", r"dependency.*requires"],
            error_codes=["DEPENDENCY_CONFLICT", "VERSION_MISMATCH"]
        )

        patterns['dependency_missing'] = ErrorPattern(
            pattern_id="dependency_missing",
            name="Missing Dependency",
            category=ErrorCategory.DEPENDENCY,
            subcategory=ErrorSubcategory.MISSING_PACKAGE,
            severity=ErrorSeverity.CRITICAL,
            recoverability=ErrorRecoverability.FULLY_RECOVERABLE,
            complexity=RecoveryComplexity.SIMPLE,
            keywords=["module not found", "no module named", "package not found", "dependency not found"],
            regex_patterns=[r"module.*not found", r"no module named", r"package.*not found"],
            error_codes=["MODULE_NOT_FOUND", "IMPORT_ERROR", "DEPENDENCY_MISSING"]
        )

        # Service unavailable patterns
        patterns['service_not_running'] = ErrorPattern(
            pattern_id="service_not_running",
            name="Service Not Running",
            category=ErrorCategory.SERVICE_UNAVAILABLE,
            subcategory=ErrorSubcategory.SERVICE_NOT_RUNNING,
            severity=ErrorSeverity.CRITICAL,
            recoverability=ErrorRecoverability.FULLY_RECOVERABLE,
            complexity=RecoveryComplexity.SIMPLE,
            keywords=["service not running", "service unavailable", "connection refused", "service down"],
            regex_patterns=[r"service.*not running", r"service.*unavailable", r"connection.*refused"],
            error_codes=["SERVICE_UNAVAILABLE", "CONNECTION_REFUSED"]
        )

        # System resource patterns
        patterns['memory_insufficient'] = ErrorPattern(
            pattern_id="memory_insufficient",
            name="Insufficient Memory",
            category=ErrorCategory.SYSTEM_RESOURCE,
            subcategory=ErrorSubcategory.MEMORY_INSUFFICIENT,
            severity=ErrorSeverity.HIGH,
            recoverability=ErrorRecoverability.PARTIALLY_RECOVERABLE,
            complexity=RecoveryComplexity.COMPLEX,
            keywords=["out of memory", "insufficient memory", "memory allocation failed", "oom"],
            regex_patterns=[r"out of memory", r"insufficient memory", r"memory.*allocation.*failed"],
            error_codes=["ENOMEM", "OUT_OF_MEMORY"]
        )

        patterns['disk_space_low'] = ErrorPattern(
            pattern_id="disk_space_low",
            name="Low Disk Space",
            category=ErrorCategory.SYSTEM_RESOURCE,
            subcategory=ErrorSubcategory.DISK_SPACE_LOW,
            severity=ErrorSeverity.MEDIUM,
            recoverability=ErrorRecoverability.FULLY_RECOVERABLE,
            complexity=RecoveryComplexity.SIMPLE,
            keywords=["disk space", "no space left", "storage full", "insufficient disk space"],
            regex_patterns=[r"no space left", r"disk.*full", r"insufficient.*disk"],
            error_codes=["ENOSPC", "DISK_FULL"]
        )

        # Configuration patterns
        patterns['config_invalid'] = ErrorPattern(
            pattern_id="config_invalid",
            name="Invalid Configuration",
            category=ErrorCategory.CONFIGURATION,
            subcategory=ErrorSubcategory.INVALID_CONFIG,
            severity=ErrorSeverity.MEDIUM,
            recoverability=ErrorRecoverability.FULLY_RECOVERABLE,
            complexity=RecoveryComplexity.MODERATE,
            keywords=["invalid configuration", "config error", "malformed config", "parse error"],
            regex_patterns=[r"invalid.*configuration", r"config.*error", r"parse.*error"],
            error_codes=["CONFIG_ERROR", "PARSE_ERROR", "INVALID_CONFIG"]
        )

        # Environment patterns
        patterns['env_path_missing'] = ErrorPattern(
            pattern_id="env_path_missing",
            name="Environment Path Missing",
            category=ErrorCategory.ENVIRONMENT,
            subcategory=ErrorSubcategory.PATH_MISSING,
            severity=ErrorSeverity.HIGH,
            recoverability=ErrorRecoverability.FULLY_RECOVERABLE,
            complexity=RecoveryComplexity.MODERATE,
            keywords=["path not found", "command not found", "executable not found", "environment path"],
            regex_patterns=[r"path.*not found", r"command.*not found", r"executable.*not found"],
            error_codes=["PATH_NOT_FOUND", "COMMAND_NOT_FOUND", "ENOENT"]
        )

        return patterns

    def _load_severity_weights(self) -> Dict[str, float]:
        """Load severity assessment weights for different factors"""
        return {
            'service_impact': 0.4,      # Impact on service functionality
            'user_impact': 0.3,         # Impact on user experience
            'system_impact': 0.2,       # Impact on system stability
            'recovery_difficulty': 0.1   # Difficulty of recovery
        }

    def _load_recovery_templates(self) -> Dict[str, List[RecoveryAction]]:
        """Load recovery action templates for different error types"""
        templates = {}

        # Network recovery templates
        templates['network_dns_failure'] = [
            RecoveryAction(
                action_id="check_dns_config",
                description="Check DNS configuration",
                command="nslookup google.com",
                expected_result="DNS resolution successful",
                verification_step="Verify DNS servers are correctly configured",
                risk_level="low"
            ),
            RecoveryAction(
                action_id="flush_dns",
                description="Flush DNS cache",
                command="ipconfig /flushdns" if platform.system().lower() == "windows" else "sudo systemctl restart systemd-resolved",
                expected_result="DNS cache flushed",
                verification_step="Test DNS resolution again",
                risk_level="low",
                platform_specific={
                    "windows": "ipconfig /flushdns",
                    "linux": "sudo systemctl restart systemd-resolved",
                    "darwin": "sudo dscacheutil -flushcache"
                }
            ),
            RecoveryAction(
                action_id="change_dns_servers",
                description="Change to public DNS servers",
                command=None,  # Manual action
                expected_result="DNS servers updated",
                verification_step="Test with new DNS servers",
                risk_level="medium"
            )
        ]

        templates['network_connectivity'] = [
            RecoveryAction(
                action_id="check_internet_connection",
                description="Verify internet connectivity",
                command="ping 8.8.8.8",
                expected_result="Internet connectivity confirmed",
                verification_step="Check if external services are reachable",
                risk_level="low"
            ),
            RecoveryAction(
                action_id="check_firewall",
                description="Check firewall settings",
                command=None,
                expected_result="Firewall rules identified",
                verification_step="Verify firewall is not blocking required ports",
                risk_level="medium"
            ),
            RecoveryAction(
                action_id="check_proxy_settings",
                description="Check proxy configuration",
                command=None,
                expected_result="Proxy settings verified",
                verification_step="Ensure proxy settings are correct",
                risk_level="low"
            )
        ]

        # Port conflict recovery templates
        templates['port_process_occupation'] = [
            RecoveryAction(
                action_id="identify_process",
                description="Identify process using the port",
                command="netstat -ano | findstr :PORT" if platform.system().lower() == "windows" else "lsof -i :PORT",
                expected_result="Process identified",
                verification_step="Confirm process details",
                risk_level="low"
            ),
            RecoveryAction(
                action_id="stop_conflicting_process",
                description="Stop the conflicting process",
                command="taskkill /PID PID /F" if platform.system().lower() == "windows" else "kill -9 PID",
                expected_result="Process terminated",
                verification_step="Verify port is now available",
                risk_level="medium",
                platform_specific={
                    "windows": "taskkill /PID {pid} /F",
                    "linux": "kill -9 {pid}",
                    "darwin": "kill -9 {pid}"
                }
            ),
            RecoveryAction(
                action_id="use_alternative_port",
                description="Configure application to use alternative port",
                command=None,
                expected_result="Application configured for new port",
                verification_step="Start application on alternative port",
                risk_level="low"
            )
        ]

        # Permission recovery templates
        templates['permission_admin_required'] = [
            RecoveryAction(
                action_id="run_with_admin",
                description="Run application with administrator privileges",
                command=None,
                expected_result="Application running with elevated privileges",
                verification_step="Verify application starts successfully",
                risk_level="medium",
                platform_specific={
                    "windows": "Run as Administrator",
                    "linux": "sudo {command}",
                    "darwin": "sudo {command}"
                }
            )
        ]

        templates['permission_file_access'] = [
            RecoveryAction(
                action_id="check_file_permissions",
                description="Check file and directory permissions",
                command="ls -la FILE_PATH" if platform.system().lower() != "windows" else "icacls FILE_PATH",
                expected_result="Current permissions displayed",
                verification_step="Review permission settings",
                risk_level="low"
            ),
            RecoveryAction(
                action_id="modify_permissions",
                description="Modify file permissions",
                command="chmod 755 FILE_PATH" if platform.system().lower() != "windows" else "icacls FILE_PATH /grant Users:F",
                expected_result="Permissions updated",
                verification_step="Verify access is now allowed",
                risk_level="medium"
            )
        ]

        # Dependency recovery templates
        templates['dependency_version_conflict'] = [
            RecoveryAction(
                action_id="analyze_conflict",
                description="Analyze dependency version requirements",
                command=None,
                expected_result="Conflict details identified",
                verification_step="Review version requirements",
                risk_level="low"
            ),
            RecoveryAction(
                action_id="update_dependencies",
                description="Update to compatible versions",
                command="pip install -r requirements.txt --upgrade" if True else "npm update",
                expected_result="Dependencies updated",
                verification_step="Verify all dependencies are compatible",
                risk_level="medium"
            ),
            RecoveryAction(
                action_id="use_virtual_environment",
                description="Create isolated virtual environment",
                command="python -m venv venv && source venv/bin/activate" if True else "npm install",
                expected_result="Virtual environment created",
                verification_step="Install dependencies in isolated environment",
                risk_level="low"
            )
        ]

        templates['dependency_missing'] = [
            RecoveryAction(
                action_id="install_missing_dependency",
                description="Install the missing dependency",
                command="pip install PACKAGE_NAME" if True else "npm install PACKAGE_NAME",
                expected_result="Dependency installed",
                verification_step="Verify dependency is available",
                risk_level="low"
            )
        ]

        # Service recovery templates
        templates['service_not_running'] = [
            RecoveryAction(
                action_id="check_service_status",
                description="Check service status",
                command="systemctl status SERVICE" if platform.system().lower() != "windows" else "sc query SERVICE",
                expected_result="Service status displayed",
                verification_step="Confirm service is not running",
                risk_level="low"
            ),
            RecoveryAction(
                action_id="start_service",
                description="Start the service",
                command="systemctl start SERVICE" if platform.system().lower() != "windows" else "net start SERVICE",
                expected_result="Service started",
                verification_step="Verify service is running",
                risk_level="medium"
            )
        ]

        # System resource recovery templates
        templates['memory_insufficient'] = [
            RecoveryAction(
                action_id="check_memory_usage",
                description="Check current memory usage",
                command="free -h" if platform.system().lower() != "windows" else "tasklist /fo table",
                expected_result="Memory usage displayed",
                verification_step="Identify memory-intensive processes",
                risk_level="low"
            ),
            RecoveryAction(
                action_id="close_memory_intensive_applications",
                description="Close memory-intensive applications",
                command=None,
                expected_result="Memory freed up",
                verification_step="Verify available memory increased",
                risk_level="medium"
            )
        ]

        templates['disk_space_low'] = [
            RecoveryAction(
                action_id="check_disk_usage",
                description="Check disk space usage",
                command="df -h" if platform.system().lower() != "windows" else "dir /s",
                expected_result="Disk usage displayed",
                verification_step="Identify large files and directories",
                risk_level="low"
            ),
            RecoveryAction(
                action_id="clean_temp_files",
                description="Clean temporary files",
                command="rm -rf /tmp/*" if platform.system().lower() != "windows" else "del /q /s %TEMP%\\*",
                expected_result="Temporary files removed",
                verification_step="Verify disk space increased",
                risk_level="low"
            )
        ]

        return templates

    async def classify_error(self, error_message: str, error_code: str = None,
                           context: Dict[str, Any] = None) -> ErrorClassification:
        """
        Classify an error using pattern matching and context analysis

        Args:
            error_message: The error message to classify
            error_code: Optional error code for classification
            context: Additional context information

        Returns:
            ErrorClassification: Complete classification result
        """
        if self.progress_tracker:
            self.progress_tracker._log(
                f"Error Classification: Classifying error: {error_message[:100]}..."
            )

        # Check cache first
        cache_key = f"{error_message}_{error_code}_{str(context)}"
        if cache_key in self.classification_cache:
            classification = self.classification_cache[cache_key]
            self.logger.debug(f"Retrieved classification from cache: {classification.error_id}")
            return classification

        # Pattern matching
        matched_patterns = []
        for pattern_id, pattern in self.patterns.items():
            if pattern.matches(error_message, error_code, context):
                matched_patterns.append((pattern_id, pattern))

        # Determine best match
        if matched_patterns:
            # Use severity and confidence scoring for best match
            best_pattern_id, best_pattern = self._select_best_pattern(matched_patterns, error_message, context)
            confidence = self._calculate_confidence(best_pattern, error_message, context)
        else:
            # Default classification for unknown errors
            best_pattern_id = "unknown_error"
            best_pattern = self._create_unknown_pattern(error_message)
            confidence = 0.5

        # Create classification
        classification = ErrorClassification(
            error_id=f"error_{int(time.time())}_{hash(error_message) % 10000}",
            category=best_pattern.category,
            subcategory=best_pattern.subcategory,
            severity=best_pattern.severity,
            recoverability=best_pattern.recoverability,
            complexity=best_pattern.complexity,
            confidence=confidence,
            patterns_matched=[p[0] for p in matched_patterns],
            metadata={
                'original_message': error_message,
                'error_code': error_code,
                'context': context or {},
                'pattern_id': best_pattern_id,
                'platform': self.platform
            }
        )

        # Cache the result
        self.classification_cache[cache_key] = classification

        if self.progress_tracker:
            self.progress_tracker._log(
                f"Error Classification: Error classified as {classification.category.value}/{classification.subcategory.value} (confidence: {confidence:.2f})"
            )

        return classification

    def _select_best_pattern(self, matched_patterns: List[Tuple[str, ErrorPattern]],
                           error_message: str, context: Dict[str, Any]) -> Tuple[str, ErrorPattern]:
        """Select the best matching pattern from multiple matches"""
        if len(matched_patterns) == 1:
            return matched_patterns[0]

        # Score patterns based on multiple factors
        scored_patterns = []
        for pattern_id, pattern in matched_patterns:
            score = 0

            # Keyword matching score
            error_lower = error_message.lower()
            keyword_matches = sum(1 for keyword in pattern.keywords if keyword.lower() in error_lower)
            score += keyword_matches * 10

            # Regex matching score
            regex_matches = sum(1 for regex in pattern.regex_patterns
                              if re.search(regex, error_message, re.IGNORECASE))
            score += regex_matches * 15

            # Error code matching score
            if context and context.get('error_code') in pattern.error_codes:
                score += 20

            # Context matching score
            if context:
                context_matches = sum(1 for ctx_key in pattern.contexts if ctx_key in context)
                score += context_matches * 5

            # Severity bonus (more specific errors get bonus)
            score += pattern.severity.value * 2

            scored_patterns.append((pattern_id, pattern, score))

        # Return pattern with highest score
        scored_patterns.sort(key=lambda x: x[2], reverse=True)
        return scored_patterns[0][0], scored_patterns[0][1]

    def _calculate_confidence(self, pattern: ErrorPattern, error_message: str,
                            context: Dict[str, Any]) -> float:
        """Calculate confidence score for pattern match"""
        confidence = 0.5  # Base confidence

        error_lower = error_message.lower()

        # Keyword matches
        keyword_matches = sum(1 for keyword in pattern.keywords if keyword.lower() in error_lower)
        confidence += min(keyword_matches * 0.15, 0.3)

        # Regex matches
        regex_matches = sum(1 for regex in pattern.regex_patterns
                          if re.search(regex, error_message, re.IGNORECASE))
        confidence += min(regex_matches * 0.2, 0.4)

        # Error code matches
        if context and context.get('error_code') in pattern.error_codes:
            confidence += 0.2

        # Context matches
        if context:
            context_matches = sum(1 for ctx_key in pattern.contexts if ctx_key in context)
            confidence += min(context_matches * 0.1, 0.2)

        return min(confidence, 1.0)

    def _create_unknown_pattern(self, error_message: str) -> ErrorPattern:
        """Create a pattern for unknown errors"""
        return ErrorPattern(
            pattern_id="unknown_error",
            name="Unknown Error",
            category=ErrorCategory.UNKNOWN,
            subcategory=ErrorSubcategory.MISSING_CONFIG,  # Default subcategory
            severity=ErrorSeverity.MEDIUM,
            recoverability=ErrorRecoverability.PARTIALLY_RECOVERABLE,
            complexity=RecoveryComplexity.COMPLEX,
            keywords=[],
            regex_patterns=[],
            error_codes=[],
            contexts=[]
        )

    def assess_severity(self, classification: ErrorClassification,
                       impact_context: Dict[str, Any] = None) -> ErrorSeverity:
        """
        Assess and potentially adjust error severity based on impact context

        Args:
            classification: Initial error classification
            impact_context: Context about the impact of the error

        Returns:
            ErrorSeverity: Adjusted severity assessment
        """
        if not impact_context:
            return classification.severity

        severity_score = classification.severity.value
        weights = self.severity_weights

        # Service impact assessment
        service_impact = impact_context.get('service_impact', 'medium')
        if service_impact == 'critical':
            severity_score += 2
        elif service_impact == 'high':
            severity_score += 1
        elif service_impact == 'low':
            severity_score -= 1

        # User impact assessment
        user_impact = impact_context.get('user_impact', 'medium')
        if user_impact == 'critical':
            severity_score += 1.5
        elif user_impact == 'high':
            severity_score += 0.5
        elif user_impact == 'low':
            severity_score -= 0.5

        # System impact assessment
        system_impact = impact_context.get('system_impact', 'medium')
        if system_impact == 'critical':
            severity_score += 1
        elif system_impact == 'high':
            severity_score += 0.5
        elif system_impact == 'low':
            severity_score -= 0.5

        # Recovery difficulty assessment
        recovery_difficulty = impact_context.get('recovery_difficulty', 'medium')
        if recovery_difficulty == 'expert':
            severity_score += 1
        elif recovery_difficulty == 'complex':
            severity_score += 0.5
        elif recovery_difficulty == 'simple':
            severity_score -= 0.5

        # Convert score back to enum with bounds checking
        severity_score = max(0, min(4, int(round(severity_score))))

        return ErrorSeverity(severity_score)

    def generate_recovery_plan(self, classification: ErrorClassification,
                             context: Dict[str, Any] = None) -> RecoveryPlan:
        """
        Generate a comprehensive recovery plan for the classified error

        Args:
            classification: Error classification result
            context: Additional context for recovery planning

        Returns:
            RecoveryPlan: Comprehensive recovery plan
        """
        pattern_id = classification.metadata.get('pattern_id', 'unknown')

        # Get base recovery actions
        base_actions = self.recovery_templates.get(pattern_id, [])

        # Customize actions based on context
        customized_actions = []
        for action in base_actions:
            customized_action = self._customize_action(action, classification, context)
            if customized_action:
                customized_actions.append(customized_action)

        # Add context-specific actions
        context_actions = self._generate_context_actions(classification, context)
        customized_actions.extend(context_actions)

        # Calculate success probability and estimated time
        success_probability = self._calculate_success_probability(classification, customized_actions)
        estimated_time = self._estimate_recovery_time(classification, customized_actions)

        # Generate verification steps
        verification_steps = self._generate_verification_steps(classification, customized_actions)

        # Generate rollback plan
        rollback_plan = self._generate_rollback_plan(classification, customized_actions)

        # Generate alternative solutions
        alternative_solutions = self._generate_alternative_solutions(classification)

        plan = RecoveryPlan(
            plan_id=f"plan_{classification.error_id}_{int(time.time())}",
            error_id=classification.error_id,
            title=f"Recovery Plan for {classification.category.value.replace('_', ' ').title()} Error",
            description=f"Automated recovery plan for {classification.subcategory.value.replace('_', ' ')}",
            estimated_time=estimated_time,
            success_probability=success_probability,
            actions=customized_actions,
            prerequisites=self._generate_prerequisites(classification),
            rollback_plan=rollback_plan,
            verification_steps=verification_steps,
            alternative_solutions=alternative_solutions
        )

        return plan

    def _customize_action(self, action: RecoveryAction, classification: ErrorClassification,
                        context: Dict[str, Any]) -> Optional[RecoveryAction]:
        """Customize a recovery action based on classification and context"""
        # Clone the action
        customized = RecoveryAction(
            action_id=action.action_id,
            description=action.description,
            command=action.command,
            expected_result=action.expected_result,
            verification_step=action.verification_step,
            risk_level=action.risk_level,
            automated=action.automated,
            platform_specific=action.platform_specific.copy()
        )

        # Customize command based on platform
        if customized.platform_specific and self.platform in customized.platform_specific:
            customized.command = customized.platform_specific[self.platform]

        # Add context-specific customizations
        if context:
            # Replace placeholders in commands
            if customized.command:
                for key, value in context.items():
                    placeholder = "{" + key.upper() + "}"
                    if placeholder in customized.command:
                        customized.command = customized.command.replace(placeholder, str(value))

        return customized

    def _generate_context_actions(self, classification: ErrorClassification,
                                context: Dict[str, Any]) -> List[RecoveryAction]:
        """Generate additional actions based on context"""
        actions = []

        if classification.category == ErrorCategory.DEPENDENCY:
            if context and context.get('package_manager'):
                actions.append(RecoveryAction(
                    action_id="update_package_manager",
                    description=f"Update {context['package_manager']} packages",
                    command=self._get_update_command(context['package_manager']),
                    expected_result="Package manager updated",
                    verification_step="Verify package manager is up to date",
                    risk_level="low"
                ))

        elif classification.category == ErrorCategory.NETWORK:
            actions.append(RecoveryAction(
                action_id="restart_network_service",
                description="Restart network services",
                command=self._get_network_restart_command(),
                expected_result="Network services restarted",
                verification_step="Verify network connectivity",
                risk_level="medium"
            ))

        return actions

    def _calculate_success_probability(self, classification: ErrorClassification,
                                     actions: List[RecoveryAction]) -> float:
        """Calculate success probability for the recovery plan"""
        base_probability = 0.7  # Base success rate

        # Adjust based on recoverability
        if classification.recoverability == ErrorRecoverability.FULLY_RECOVERABLE:
            base_probability += 0.2
        elif classification.recoverability == ErrorRecoverability.PARTIALLY_RECOVERABLE:
            base_probability += 0.1
        elif classification.recoverability == ErrorRecoverability.NON_RECOVERABLE:
            base_probability -= 0.3

        # Adjust based on complexity
        if classification.complexity == RecoveryComplexity.AUTOMATIC:
            base_probability += 0.2
        elif classification.complexity == RecoveryComplexity.SIMPLE:
            base_probability += 0.1
        elif classification.complexity == RecoveryComplexity.COMPLEX:
            base_probability -= 0.1
        elif classification.complexity == RecoveryComplexity.EXPERT:
            base_probability -= 0.3

        # Adjust based on action risk levels
        high_risk_actions = sum(1 for action in actions if action.risk_level == "high")
        if high_risk_actions > 0:
            base_probability -= high_risk_actions * 0.1

        return max(0.1, min(0.95, base_probability))

    def _estimate_recovery_time(self, classification: ErrorClassification,
                               actions: List[RecoveryAction]) -> str:
        """Estimate recovery time based on actions and complexity"""
        base_time = 5  # Base time in minutes

        # Add time based on complexity
        if classification.complexity == RecoveryComplexity.AUTOMATIC:
            base_time = 1
        elif classification.complexity == RecoveryComplexity.SIMPLE:
            base_time = 5
        elif classification.complexity == RecoveryComplexity.MODERATE:
            base_time = 15
        elif classification.complexity == RecoveryComplexity.COMPLEX:
            base_time = 30
        elif classification.complexity == RecoveryComplexity.EXPERT:
            base_time = 60

        # Add time for each action
        for action in actions:
            if action.automated:
                base_time += 1
            else:
                base_time += 3

        if base_time < 5:
            return f"{int(base_time)} minutes"
        elif base_time < 60:
            return f"{int(base_time)} minutes"
        else:
            hours = base_time / 60
            return f"{hours:.1f} hours"

    def _generate_verification_steps(self, classification: ErrorClassification,
                                    actions: List[RecoveryAction]) -> List[str]:
        """Generate verification steps for the recovery plan"""
        steps = [
            "Verify the original error condition no longer exists",
            "Test related functionality to ensure proper operation",
            "Check system logs for any new errors"
        ]

        # Add category-specific verification
        if classification.category == ErrorCategory.NETWORK:
            steps.extend([
                "Test network connectivity to external services",
                "Verify DNS resolution is working correctly"
            ])
        elif classification.category == ErrorCategory.PORT_CONFLICT:
            steps.extend([
                "Verify the required port is available",
                "Test application startup on the required port"
            ])
        elif classification.category == ErrorCategory.DEPENDENCY:
            steps.extend([
                "Verify all dependencies are correctly installed",
                "Test application imports and functionality"
            ])

        return steps

    def _generate_rollback_plan(self, classification: ErrorClassification,
                               actions: List[RecoveryAction]) -> List[str]:
        """Generate rollback plan for recovery actions"""
        rollback_steps = []

        for action in actions:
            if action.action_id == "modify_permissions":
                rollback_steps.append("Restore original file permissions")
            elif action.action_id == "update_dependencies":
                rollback_steps.append("Restore original dependency versions")
            elif action.action_id == "stop_conflicting_process":
                rollback_steps.append("Restart stopped processes if needed")
            elif "change" in action.action_id or "modify" in action.action_id:
                rollback_steps.append(f"Reverse changes made by {action.description}")

        if not rollback_steps:
            rollback_steps.append("No rollback actions needed - all changes are safe")

        return rollback_steps

    def _generate_alternative_solutions(self, classification: ErrorClassification) -> List[str]:
        """Generate alternative solutions for the error"""
        alternatives = []

        if classification.category == ErrorCategory.PORT_CONFLICT:
            alternatives.extend([
                "Use a different port for the application",
                "Run the application on a different machine",
                "Use containerization (Docker) to isolate the application"
            ])
        elif classification.category == ErrorCategory.DEPENDENCY:
            alternatives.extend([
                "Use a different version of the conflicting dependency",
                "Replace the dependency with an alternative package",
                "Use containerization to manage dependencies"
            ])
        elif classification.category == ErrorCategory.PERMISSION:
            alternatives.extend([
                "Run the application in a dedicated user environment",
                "Change file locations to avoid permission issues",
                "Use containerization with appropriate permissions"
            ])
        elif classification.category == ErrorCategory.NETWORK:
            alternatives.extend([
                "Use offline mode if available",
                "Configure alternative network routes",
                "Use VPN or proxy to bypass network restrictions"
            ])

        return alternatives

    def _generate_prerequisites(self, classification: ErrorClassification) -> List[str]:
        """Generate prerequisites for the recovery plan"""
        prerequisites = [
            "Ensure you have necessary system permissions",
            "Save all important work before proceeding",
            "Create a system backup if critical changes are needed"
        ]

        if classification.complexity in [RecoveryComplexity.COMPLEX, RecoveryComplexity.EXPERT]:
            prerequisites.extend([
                "Consult with system administrator",
                "Schedule maintenance window for production systems",
                "Prepare rollback procedures"
            ])

        if classification.category == ErrorCategory.DEPENDENCY:
            prerequisites.append("Ensure package manager is up to date")
        elif classification.category == ErrorCategory.NETWORK:
            prerequisites.append("Verify physical network connectivity")
        elif classification.category == ErrorCategory.PERMISSION:
            prerequisites.append("Obtain administrative privileges if required")

        return prerequisites

    def _get_update_command(self, package_manager: str) -> str:
        """Get update command for package manager"""
        commands = {
            'pip': 'pip install --upgrade pip',
            'npm': 'npm update -g',
            'yarn': 'yarn global upgrade',
            'apt': 'sudo apt update && sudo apt upgrade',
            'yum': 'sudo yum update',
            'brew': 'brew update && brew upgrade'
        }
        return commands.get(package_manager, f'{package_manager} update')

    def _get_network_restart_command(self) -> str:
        """Get network restart command for current platform"""
        if self.platform == "windows":
            return "netsh winsock reset && netsh int ip reset"
        elif self.platform == "darwin":
            return "sudo dscacheutil -flushcache && sudo killall -HUP mDNSResponder"
        else:  # Linux
            return "sudo systemctl restart network-manager"

    async def batch_classify_errors(self, errors: List[Dict[str, Any]]) -> List[ErrorClassification]:
        """
        Classify multiple errors in batch

        Args:
            errors: List of error dictionaries with 'message', 'code', and 'context' keys

        Returns:
            List[ErrorClassification]: Classification results for all errors
        """
        if self.progress_tracker:
            self.progress_tracker.start_task(
                "batch_error_classification",
                f"Classifying {len(errors)} errors"
            )

        classifications = []
        for i, error in enumerate(errors):
            if self.progress_tracker:
                self.progress_tracker._log(
                    component="batch_classification",
                    message=f"Classifying error {i+1}/{len(errors)}",
                    level="info"
                )

            classification = await self.classify_error(
                error.get('message', ''),
                error.get('code'),
                error.get('context', {})
            )
            classifications.append(classification)

        if self.progress_tracker:
            self.progress_tracker.complete_task("batch_error_classification")

        return classifications

    def get_error_statistics(self, classifications: List[ErrorClassification]) -> Dict[str, Any]:
        """
        Generate statistics from error classifications

        Args:
            classifications: List of error classifications

        Returns:
            Dict containing error statistics
        """
        stats = {
            'total_errors': len(classifications),
            'categories': {},
            'severities': {},
            'recoverabilities': {},
            'complexities': {},
            'average_confidence': 0.0,
            'most_common_category': None,
            'most_common_severity': None
        }

        if not classifications:
            return stats

        # Count categories, severities, etc.
        for classification in classifications:
            # Category stats
            cat = classification.category.value
            stats['categories'][cat] = stats['categories'].get(cat, 0) + 1

            # Severity stats
            sev = classification.severity.name
            stats['severities'][sev] = stats['severities'].get(sev, 0) + 1

            # Recoverability stats
            rec = classification.recoverability.value
            stats['recoverabilities'][rec] = stats['recoverabilities'].get(rec, 0) + 1

            # Complexity stats
            comp = classification.complexity.name
            stats['complexities'][comp] = stats['complexities'].get(comp, 0) + 1

        # Calculate average confidence
        total_confidence = sum(c.confidence for c in classifications)
        stats['average_confidence'] = total_confidence / len(classifications)

        # Find most common
        stats['most_common_category'] = max(stats['categories'], key=stats['categories'].get)
        stats['most_common_severity'] = max(stats['severities'], key=stats['severities'].get)

        return stats