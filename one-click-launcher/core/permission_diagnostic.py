"""
Permission Issue Diagnosis and Guidance Module

This module provides comprehensive permission issue detection, diagnosis,
and user-friendly guidance for privilege escalation across different platforms.
"""

import os
import sys
import platform
import subprocess
import stat
from typing import Dict, List, Optional, Tuple, Union, Any
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

# Platform-specific imports
try:
    import pwd
    import grp
    UNIX_SUPPORT = True
except ImportError:
    # Windows doesn't have pwd/grp modules
    pwd = None
    grp = None
    UNIX_SUPPORT = False

from utils.logger import get_logger
from utils.progress_tracker import ProgressTracker

logger = get_logger(__name__)


class PermissionLevel(Enum):
    """Permission levels for different operations"""
    USER = "user"
    ADMIN = "admin"
    ROOT = "root"


class PlatformType(Enum):
    """Supported platforms"""
    WINDOWS = "windows"
    LINUX = "linux"
    MACOS = "macos"


@dataclass
class PermissionCheckResult:
    """Result of permission check"""
    has_permission: bool
    current_level: PermissionLevel
    required_level: PermissionLevel
    platform: PlatformType
    details: Dict[str, Any]
    suggestions: List[str]


@dataclass
class FilePermissionResult:
    """Result of file/directory permission check"""
    path: str
    exists: bool
    readable: bool
    writable: bool
    executable: bool
    owner: Optional[str]
    group: Optional[str]
    permissions: str
    issues: List[str]
    suggestions: List[str]


class PermissionDiagnostic:
    """Comprehensive permission diagnosis and guidance system"""

    def __init__(self, progress_tracker: Optional[ProgressTracker] = None):
        self.progress_tracker = progress_tracker
        self.platform = self._detect_platform()
        self.current_user = self._get_current_user()

    def _detect_platform(self) -> PlatformType:
        """Detect the current platform"""
        system = platform.system().lower()
        if system == "windows":
            return PlatformType.WINDOWS
        elif system == "darwin":
            return PlatformType.MACOS
        elif system == "linux":
            return PlatformType.LINUX
        else:
            # Default to Linux for Unix-like systems
            return PlatformType.LINUX

    def _get_current_user(self) -> str:
        """Get current username"""
        try:
            if self.platform == PlatformType.WINDOWS:
                return os.environ.get('USERNAME', 'unknown')
            else:
                return os.environ.get('USER', 'unknown')
        except Exception as e:
            logger.warning(f"Could not determine current user: {e}")
            return 'unknown'

    def check_admin_privileges(self) -> PermissionCheckResult:
        """
        Check if current user has administrator/root privileges
        """
        logger.info("Checking administrator privileges")

        if self.progress_tracker:
            self.progress_tracker._log("Checking admin privileges (10%)")

        has_admin = False
        current_level = PermissionLevel.USER
        required_level = PermissionLevel.ADMIN
        details = {}
        suggestions = []

        try:
            if self.platform == PlatformType.WINDOWS:
                has_admin, details = self._check_windows_admin()
            else:
                has_admin, details = self._check_unix_admin()

            current_level = PermissionLevel.ADMIN if has_admin else PermissionLevel.USER

            if not has_admin:
                suggestions = self._generate_privilege_suggestions(required_level)

        except Exception as e:
            logger.error(f"Error checking admin privileges: {e}")
            details['error'] = str(e)
            suggestions.append("Run the application with administrator privileges")

        result = PermissionCheckResult(
            has_permission=has_admin,
            current_level=current_level,
            required_level=required_level,
            platform=self.platform,
            details=details,
            suggestions=suggestions
        )

        if self.progress_tracker:
            self.progress_tracker._log("Admin privileges check completed (25%)")

        return result

    def _check_windows_admin(self) -> Tuple[bool, Dict[str, Any]]:
        """Check admin privileges on Windows"""
        details = {}

        try:
            import ctypes
            from ctypes import wintypes

            # Check if running as admin
            is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
            details['method'] = 'Windows API IsUserAnAdmin'
            details['is_admin'] = is_admin

            # Additional check using UAC
            try:
                import win32com.client
                shell = win32com.client.Dispatch("WScript.Shell")
                details['uac_enabled'] = True
            except ImportError:
                details['uac_check'] = 'win32com not available'

            return is_admin, details

        except Exception as e:
            # Fallback method: try to write to system directory
            try:
                system_dir = os.environ.get('SystemRoot', 'C:\\Windows')
                test_file = os.path.join(system_dir, 'temp_admin_test.txt')

                with open(test_file, 'w') as f:
                    f.write('test')

                os.remove(test_file)
                details['method'] = 'write test to system directory'
                return True, details

            except (PermissionError, OSError):
                details['method'] = 'write test to system directory (failed)'
                return False, details

    def _check_unix_admin(self) -> Tuple[bool, Dict[str, Any]]:
        """Check admin/root privileges on Unix-like systems"""
        details = {}

        # Primary check: effective user ID
        if hasattr(os, 'geteuid'):
            is_root = os.geteuid() == 0
            details['method'] = 'os.geteuid()'
            details['euid'] = os.geteuid()
        else:
            # Fallback for older Python versions
            is_root = os.getuid() == 0
            details['method'] = 'os.getuid()'
            details['uid'] = os.getuid()

        # Additional checks
        try:
            # Check if user is in sudoers
            sudo_result = subprocess.run(['sudo', '-n', 'true'],
                                      capture_output=True,
                                      timeout=5)
            details['sudo_available'] = sudo_result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            details['sudo_available'] = False

        # Check groups
        try:
            if UNIX_SUPPORT:
                groups = [g.gr_name for g in grp.getgrall() if self.current_user in g.gr_mem]
                details['user_groups'] = groups
                details['is_in_admin_group'] = any(group in groups for group in ['admin', 'wheel', 'sudo'])
            else:
                # Windows - use net user command to check group membership
                try:
                    result = subprocess.run(['net', 'user', self.current_user],
                                          capture_output=True, text=True, timeout=10)
                    groups = []
                    if result.returncode == 0:
                        for line in result.stdout.split('\n'):
                            if 'Local Group Memberships' in line or 'Global Group memberships' in line:
                                # Extract groups from output
                                groups_line = line.split('*')[1].strip() if '*' in line else ''
                                groups = [g.strip() for g in groups_line.split() if g.strip()]

                    details['user_groups'] = groups
                    details['is_in_admin_group'] = any('Administrators' in group for group in groups)
                except Exception:
                    details['group_check'] = 'failed'
                    details['user_groups'] = []
                    details['is_in_admin_group'] = False
        except Exception:
            details['group_check'] = 'failed'

        return is_root, details

    def check_file_permissions(self, file_path: str) -> FilePermissionResult:
        """
        Check permissions for a specific file or directory
        """
        logger.info(f"Checking file permissions for: {file_path}")

        if self.progress_tracker:
            self.progress_tracker._log(f"Checking file permissions: {file_path} (50%)")

        path_obj = Path(file_path)
        issues = []
        suggestions = []

        # Check if path exists
        if not path_obj.exists():
            return FilePermissionResult(
                path=file_path,
                exists=False,
                readable=False,
                writable=False,
                executable=False,
                owner=None,
                group=None,
                permissions="",
                issues=["Path does not exist"],
                suggestions=[f"Create the directory: mkdir -p {file_path}"]
            )

        # Get basic permissions
        try:
            stat_info = path_obj.stat()
            permissions = oct(stat_info.st_mode)[-3:]

            # Check read permission
            readable = os.access(file_path, os.R_OK)
            if not readable:
                issues.append("No read permission")
                suggestions.append(f"Grant read permission: chmod +r {file_path}")

            # Check write permission
            writable = os.access(file_path, os.W_OK)
            if not writable:
                issues.append("No write permission")
                suggestions.append(f"Grant write permission: chmod +w {file_path}")

            # Check execute permission (for directories)
            executable = os.access(file_path, os.X_OK)
            if path_obj.is_dir() and not executable:
                issues.append("No execute permission for directory")
                suggestions.append(f"Grant execute permission: chmod +x {file_path}")

            # Get owner and group
            owner = None
            group = None

            if UNIX_SUPPORT and self.platform != PlatformType.WINDOWS:
                try:
                    owner = pwd.getpwuid(stat_info.st_uid).pw_name
                    group = grp.getgrgid(stat_info.st_gid).gr_name
                except Exception:
                    pass

            result = FilePermissionResult(
                path=file_path,
                exists=True,
                readable=readable,
                writable=writable,
                executable=executable,
                owner=owner,
                group=group,
                permissions=permissions,
                issues=issues,
                suggestions=suggestions
            )

        except Exception as e:
            logger.error(f"Error checking file permissions: {e}")
            result = FilePermissionResult(
                path=file_path,
                exists=True,
                readable=False,
                writable=False,
                executable=False,
                owner=None,
                group=None,
                permissions="unknown",
                issues=[f"Error checking permissions: {e}"],
                suggestions=["Check file system permissions manually"]
            )

        if self.progress_tracker:
            self.progress_tracker._log("File permissions check completed (75%)")

        return result

    def _generate_privilege_suggestions(self, required_level: PermissionLevel) -> List[str]:
        """Generate platform-specific privilege escalation suggestions"""
        suggestions = []

        if self.platform == PlatformType.WINDOWS:
            suggestions.extend([
                "Right-click the application and select 'Run as administrator'",
                "Search for Command Prompt, right-click and 'Run as administrator'",
                "Use Windows + X, then select 'Windows PowerShell (Admin)' or 'Command Prompt (Admin)'",
                "If UAC is enabled, click 'Yes' when prompted for administrator access"
            ])
        elif self.platform == PlatformType.MACOS:
            suggestions.extend([
                f"Use: sudo {' '.join(sys.argv)}",
                "Or run with: sudo python3 your_script.py",
                "Enter your password when prompted (it won't show characters as you type)",
                "For GUI applications, use the terminal or modify app permissions in System Preferences"
            ])
        else:  # Linux
            suggestions.extend([
                f"Use: sudo {' '.join(sys.argv)}",
                "Or run with: sudo python3 your_script.py",
                "Enter your password when prompted (it won't show characters as you type)",
                "Add user to sudo group: sudo usermod -aG sudo $USER (then logout and login again)",
                "For specific commands, you might need: sudo chmod +x script.sh"
            ])

        return suggestions

    def diagnose_permission_issues(self, paths: List[str] = None) -> Dict[str, Any]:
        """
        Comprehensive permission diagnosis for common issues
        """
        logger.info("Starting comprehensive permission diagnosis")

        if self.progress_tracker:
            self.progress_tracker._log("Starting permission diagnosis (0%)")

        results = {
            'platform': self.platform.value,
            'current_user': self.current_user,
            'admin_check': None,
            'file_checks': {},
            'overall_issues': [],
            'recommendations': []
        }

        # Check admin privileges
        admin_result = self.check_admin_privileges()
        results['admin_check'] = {
            'has_admin': admin_result.has_permission,
            'current_level': admin_result.current_level.value,
            'required_level': admin_result.required_level.value,
            'suggestions': admin_result.suggestions
        }

        if not admin_result.has_permission:
            results['overall_issues'].append("Lacks administrator privileges")
            results['recommendations'].extend(admin_result.suggestions)

        # Check common paths if not specified
        if paths is None:
            paths = self._get_common_paths_to_check()

        # Check file permissions for each path
        for path in paths:
            try:
                file_result = self.check_file_permissions(path)
                results['file_checks'][path] = {
                    'exists': file_result.exists,
                    'readable': file_result.readable,
                    'writable': file_result.writable,
                    'executable': file_result.executable,
                    'permissions': file_result.permissions,
                    'issues': file_result.issues,
                    'suggestions': file_result.suggestions
                }

                if file_result.issues:
                    results['overall_issues'].extend([f"{path}: {issue}" for issue in file_result.issues])
                    results['recommendations'].extend(file_result.suggestions)

            except Exception as e:
                logger.error(f"Error checking path {path}: {e}")
                results['file_checks'][path] = {'error': str(e)}

        # Remove duplicate recommendations
        results['recommendations'] = list(set(results['recommendations']))

        if self.progress_tracker:
            self.progress_tracker._log("Permission diagnosis completed (100%)")

        return results

    def _get_common_paths_to_check(self) -> List[str]:
        """Get common paths that typically need permission checks"""
        current_dir = os.getcwd()

        common_paths = [
            current_dir,
            os.path.expanduser('~'),
            '/tmp' if self.platform != PlatformType.WINDOWS else os.environ.get('TEMP', 'C:\\temp'),
            '/var/log' if self.platform != PlatformType.WINDOWS else os.environ.get('TEMP', 'C:\\temp'),
        ]

        # Add project-specific paths
        project_paths = [
            'logs',
            'data',
            'config',
            '.env'
        ]

        for path in project_paths:
            full_path = os.path.join(current_dir, path)
            common_paths.append(full_path)

        return common_paths

    def generate_privilege_guide(self, operation: str) -> Dict[str, Any]:
        """
        Generate platform-specific guidance for acquiring privileges
        """
        logger.info(f"Generating privilege guide for operation: {operation}")

        guides = {
            'windows': {
                'methods': [
                    {
                        'name': 'Run as Administrator',
                        'steps': [
                            'Right-click on the application or Command Prompt',
                            'Select "Run as administrator" from the context menu',
                            'Click "Yes" on the User Account Control (UAC) prompt',
                            'The application will now run with elevated privileges'
                        ],
                        'command_line': None
                    },
                    {
                        'name': 'Administrator Command Prompt',
                        'steps': [
                            'Press Windows Key + X',
                            'Select "Windows PowerShell (Admin)" or "Command Prompt (Admin)"',
                            'Click "Yes" on the UAC prompt',
                            'Navigate to your application directory and run it from there'
                        ],
                        'command_line': 'Run your commands in the admin terminal'
                    }
                ],
                'notes': [
                    'UAC (User Account Control) may prompt for confirmation',
                    'Some operations may still require additional configuration',
                    'Ensure your user account has administrator rights'
                ]
            },
            'linux': {
                'methods': [
                    {
                        'name': 'Using sudo',
                        'steps': [
                            f'Prefix your command with: sudo {" ".join(sys.argv)}',
                            'Enter your password when prompted (characters won\'t show)',
                            'The command will execute with root privileges'
                        ],
                        'command_line': f'sudo {" ".join(sys.argv)}'
                    },
                    {
                        'name': 'Switch to root user',
                        'steps': [
                            'Use: sudo su -',
                            'Enter your password',
                            'You are now logged in as root user',
                            'Run your commands normally',
                            'Type "exit" to return to normal user'
                        ],
                        'command_line': 'sudo su -'
                    }
                ],
                'notes': [
                    'Your user must be in the sudoers file',
                    'Password is typically required for each sudo operation',
                    'Be careful with root privileges - you can damage your system'
                ]
            },
            'macos': {
                'methods': [
                    {
                        'name': 'Using sudo',
                        'steps': [
                            f'Use: sudo {" ".join(sys.argv)}',
                            'Enter your password when prompted (characters won\'t show)',
                            'The command will execute with administrator privileges'
                        ],
                        'command_line': f'sudo {" ".join(sys.argv)}'
                    },
                    {
                        'name': 'GUI Application Rights',
                        'steps': [
                            'Go to System Preferences > Security & Privacy',
                            'Click the lock icon and enter your password',
                            'Add your application to the list of allowed applications',
                            'Grant necessary permissions in Accessibility or Full Disk Access'
                        ],
                        'command_line': None
                    }
                ],
                'notes': [
                    'macOS uses a different permission model than Linux',
                    'Some GUI applications may need explicit permission in System Preferences',
                    'System Integrity Protection (SIP) may restrict certain operations'
                ]
            }
        }

        platform_key = self.platform.value
        guide = guides.get(platform_key, guides['linux'])

        # Add operation-specific guidance
        operation_guidance = self._get_operation_specific_guidance(operation)
        guide['operation_guidance'] = operation_guidance

        return guide

    def _get_operation_specific_guidance(self, operation: str) -> Dict[str, Any]:
        """Get specific guidance for different types of operations"""
        guidance_map = {
            'port_binding': {
                'description': 'Binding to privileged ports (< 1024)',
                'additional_requirements': [
                    'Requires root/administrator privileges on most systems',
                    'Consider using alternative ports (> 1024) if possible',
                    'Some systems allow port binding configuration changes'
                ]
            },
            'file_system': {
                'description': 'File system operations in protected directories',
                'additional_requirements': [
                    'System directories typically require elevated privileges',
                    'Consider using user-writable locations when possible',
                    'Check specific directory permissions'
                ]
            },
            'service_management': {
                'description': 'Starting/stopping system services',
                'additional_requirements': [
                    'Service management almost always requires admin privileges',
                    'Use systemctl (Linux), services.msc (Windows), or launchctl (macOS)',
                    'Some services may require additional configuration'
                ]
            },
            'network_configuration': {
                'description': 'Network configuration changes',
                'additional_requirements': [
                    'Network configuration requires system-level privileges',
                    'May affect system-wide network settings',
                    'Consider impact on other applications'
                ]
            }
        }

        return guidance_map.get(operation, {
            'description': 'General operation requiring elevated privileges',
            'additional_requirements': [
                'Administrator privileges may be required',
                'Check specific operation requirements',
                'Consider security implications'
            ]
        })