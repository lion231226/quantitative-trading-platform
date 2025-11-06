"""
Permission Recovery and Automatic Repair Module

This module provides comprehensive permission issue automatic repair capabilities
including privilege elevation requests, file permission fixes, and rollback mechanisms.
"""

import os
import sys
import platform
import subprocess
import stat
import shutil
import json
import tempfile
from typing import Dict, List, Optional, Tuple, Union, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
from datetime import datetime

# Platform-specific imports
try:
    import pwd
    import grp
    UNIX_SUPPORT = True
except ImportError:
    pwd = None
    grp = None
    UNIX_SUPPORT = False

from utils.logger import get_logger
from utils.progress_tracker import ProgressTracker
from core.permission_diagnostic import PermissionDiagnostic, PermissionLevel, PlatformType, FilePermissionResult

logger = get_logger(__name__)


class RepairResult(Enum):
    """Result of a permission repair operation"""
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"
    REQUIRES_ELEVATION = "requires_elevation"
    ROLLED_BACK = "rolled_back"


class ElevationMethod(Enum):
    """Methods for privilege elevation"""
    UAC = "uac"  # Windows User Account Control
    SUDO = "sudo"  # Unix sudo
    GUI = "gui"  # GUI elevation dialog
    RUN_AS_ADMIN = "run_as_admin"  # Windows run as administrator


@dataclass
class PermissionBackup:
    """Backup information for permission rollback"""
    path: str
    original_permissions: str
    original_owner: Optional[str]
    original_group: Optional[str]
    timestamp: str
    backup_id: str


@dataclass
class RepairOperation:
    """Represents a permission repair operation"""
    operation_id: str
    operation_type: str
    target_path: str
    description: str
    requires_elevation: bool
    repair_command: Optional[str]
    rollback_command: Optional[str]
    result: Optional[RepairResult]
    error_message: Optional[str]
    timestamp: str


@dataclass
class PermissionRepairResult:
    """Result of permission repair operation"""
    success: bool
    result_type: RepairResult
    operations: List[RepairOperation]
    backups_created: List[PermissionBackup]
    elevation_requested: bool
    elevation_method: Optional[ElevationMethod]
    error_message: Optional[str]
    suggestions: List[str]


class PermissionElevationRequest:
    """Handles permission elevation requests across platforms"""

    def __init__(self, platform: PlatformType):
        self.platform = platform

    def request_elevation(self, method: Optional[ElevationMethod] = None) -> Dict[str, Any]:
        """
        Request privilege elevation using platform-appropriate method
        """
        logger.info(f"Requesting privilege elevation using method: {method}")

        if self.platform == PlatformType.WINDOWS:
            return self._request_windows_elevation(method)
        else:
            return self._request_unix_elevation(method)

    def _request_windows_elevation(self, method: Optional[ElevationMethod]) -> Dict[str, Any]:
        """Request elevation on Windows"""
        try:
            import ctypes
            from ctypes import wintypes

            # Check if already running as admin
            is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
            if is_admin:
                return {
                    'success': True,
                    'method': 'already_admin',
                    'message': 'Already running with administrator privileges'
                }

            # Request UAC elevation
            if method == ElevationMethod.UAC or method is None:
                return self._request_uac_elevation()
            elif method == ElevationMethod.RUN_AS_ADMIN:
                return self._request_run_as_admin()
            else:
                return {
                    'success': False,
                    'error': f'Elevation method {method} not supported on Windows'
                }

        except Exception as e:
            logger.error(f"Error requesting Windows elevation: {e}")
            return {
                'success': False,
                'error': f"Failed to request elevation: {e}"
            }

    def _request_uac_elevation(self) -> Dict[str, Any]:
        """Request UAC elevation on Windows"""
        try:
            # Use ShellExecuteW to trigger UAC
            import ctypes
            from ctypes import wintypes

            shell32 = ctypes.windll.shell32
            shell32.ShellExecuteW(
                None,
                "runas",  # Verbs that trigger UAC
                sys.executable,
                " ".join(sys.argv),
                None,
                1  # SW_SHOWNORMAL
            )

            return {
                'success': True,
                'method': 'uac',
                'message': 'UAC elevation requested. Please approve the prompt.',
                'requires_restart': True
            }

        except Exception as e:
            return {
                'success': False,
                'error': f"UAC elevation failed: {e}"
            }

    def _request_run_as_admin(self) -> Dict[str, Any]:
        """Request run as administrator on Windows"""
        return {
            'success': True,
            'method': 'run_as_admin',
            'message': 'Please right-click the application and select "Run as administrator"',
            'manual_action_required': True
        }

    def _request_unix_elevation(self, method: Optional[ElevationMethod]) -> Dict[str, Any]:
        """Request elevation on Unix-like systems"""
        # Check if already running as root
        if hasattr(os, 'geteuid') and os.geteuid() == 0:
            return {
                'success': True,
                'method': 'already_root',
                'message': 'Already running with root privileges'
            }

        if method == ElevationMethod.SUDO or method is None:
            return self._request_sudo_elevation()
        else:
            return {
                'success': False,
                'error': f'Elevation method {method} not supported on {self.platform.value}'
            }

    def _request_sudo_elevation(self) -> Dict[str, Any]:
        """Request sudo elevation on Unix-like systems"""
        try:
            # Test if sudo is available
            result = subprocess.run(['sudo', '-n', 'true'],
                                  capture_output=True,
                                  timeout=5)

            if result.returncode == 0:
                return {
                    'success': True,
                    'method': 'sudo',
                    'message': 'Sudo access available'
                }
            else:
                return {
                    'success': False,
                    'method': 'sudo',
                    'message': 'Sudo access required. Please run with sudo.',
                    'command': f'sudo {" ".join(sys.argv)}',
                    'manual_action_required': True
                }

        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            return {
                'success': False,
                'error': f"Sudo not available or timed out: {e}"
            }


class PermissionRepairer:
    """Comprehensive permission repair and rollback system"""

    def __init__(self, progress_tracker: Optional[ProgressTracker] = None):
        self.progress_tracker = progress_tracker
        self.diagnostic = PermissionDiagnostic(progress_tracker)
        self.elevation_request = PermissionElevationRequest(self.diagnostic.platform)
        self.backups: List[PermissionBackup] = []
        self.operations: List[RepairOperation] = []

    def create_permission_backup(self, path: str) -> Optional[PermissionBackup]:
        """
        Create a backup of current permissions for rollback
        """
        try:
            path_obj = Path(path)
            if not path_obj.exists():
                logger.warning(f"Cannot create backup for non-existent path: {path}")
                return None

            stat_info = path_obj.stat()
            permissions = oct(stat_info.st_mode)[-3:]

            owner = None
            group = None

            if UNIX_SUPPORT and self.diagnostic.platform != PlatformType.WINDOWS:
                try:
                    owner = pwd.getpwuid(stat_info.st_uid).pw_name
                    group = grp.getgrgid(stat_info.st_gid).gr_name
                except Exception:
                    pass

            backup = PermissionBackup(
                path=path,
                original_permissions=permissions,
                original_owner=owner,
                original_group=group,
                timestamp=datetime.now().isoformat(),
                backup_id=f"backup_{int(datetime.now().timestamp())}"
            )

            self.backups.append(backup)
            logger.info(f"Created permission backup for {path}")
            return backup

        except Exception as e:
            logger.error(f"Error creating permission backup for {path}: {e}")
            return None

    def repair_file_permissions(self, file_path: str,
                                target_permissions: Optional[str] = None,
                                recursive: bool = False) -> PermissionRepairResult:
        """
        Repair file or directory permissions automatically
        """
        logger.info(f"Starting permission repair for: {file_path}")

        operations = []
        backups_created = []
        elevation_requested = False
        elevation_method = None

        try:
            # Create backup before making changes
            backup = self.create_permission_backup(file_path)
            if backup:
                backups_created.append(backup)

            # Check current permissions
            current_result = self.diagnostic.check_file_permissions(file_path)

            if not current_result.exists:
                return PermissionRepairResult(
                    success=False,
                    result_type=RepairResult.FAILED,
                    operations=operations,
                    backups_created=backups_created,
                    elevation_requested=elevation_requested,
                    elevation_method=elevation_method,
                    error_message=f"Path does not exist: {file_path}",
                    suggestions=[f"Create the path: mkdir -p {file_path}"]
                )

            # Determine target permissions
            if target_permissions is None:
                target_permissions = self._get_default_permissions(file_path)

            # Repair operations
            path_obj = Path(file_path)

            # Fix read permissions if needed
            if not current_result.readable:
                read_op = self._fix_read_permission(file_path, target_permissions)
                operations.append(read_op)

                if read_op.result == RepairResult.REQUIRES_ELEVATION:
                    elevation_requested = True
                    elevation_method = self._get_elevation_method()

            # Fix write permissions if needed
            if not current_result.writable:
                write_op = self._fix_write_permission(file_path, target_permissions)
                operations.append(write_op)

                if write_op.result == RepairResult.REQUIRES_ELEVATION:
                    elevation_requested = True
                    elevation_method = self._get_elevation_method()

            # Fix execute permissions for directories
            if path_obj.is_dir() and not current_result.executable:
                exec_op = self._fix_execute_permission(file_path, target_permissions)
                operations.append(exec_op)

                if exec_op.result == RepairResult.REQUIRES_ELEVATION:
                    elevation_requested = True
                    elevation_method = self._get_elevation_method()

            # Apply recursive permissions if requested
            if recursive and path_obj.is_dir():
                recursive_ops = self._apply_recursive_permissions(file_path, target_permissions)
                operations.extend(recursive_ops)

            # Determine overall result
            success = all(op.result in [RepairResult.SUCCESS] for op in operations)
            result_type = RepairResult.SUCCESS if success else RepairResult.PARTIAL

            return PermissionRepairResult(
                success=success,
                result_type=result_type,
                operations=operations,
                backups_created=backups_created,
                elevation_requested=elevation_requested,
                elevation_method=elevation_method,
                error_message=None,
                suggestions=self._generate_repair_suggestions(file_path, current_result)
            )

        except Exception as e:
            logger.error(f"Error repairing permissions for {file_path}: {e}")
            return PermissionRepairResult(
                success=False,
                result_type=RepairResult.FAILED,
                operations=operations,
                backups_created=backups_created,
                elevation_requested=elevation_requested,
                elevation_method=elevation_method,
                error_message=str(e),
                suggestions=["Check file system permissions manually", "Run with administrator privileges"]
            )

    def _get_default_permissions(self, file_path: str) -> str:
        """Get default permissions for a file or directory"""
        path_obj = Path(file_path)

        if path_obj.is_dir():
            return "755"  # rwxr-xr-x
        else:
            return "644"  # rw-r--r--

    def _fix_read_permission(self, file_path: str, target_permissions: str) -> RepairOperation:
        """Fix read permission for a file"""
        operation_id = f"read_fix_{int(datetime.now().timestamp())}"

        try:
            # Add read permission
            current_mode = os.stat(file_path).st_mode
            new_mode = current_mode | stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH

            os.chmod(file_path, new_mode)

            return RepairOperation(
                operation_id=operation_id,
                operation_type="fix_read_permission",
                target_path=file_path,
                description=f"Added read permission to {file_path}",
                requires_elevation=False,
                repair_command=f"chmod +r {file_path}",
                rollback_command=f"chmod {oct(os.stat(file_path).st_mode)[-3:]} {file_path}",
                result=RepairResult.SUCCESS,
                error_message=None,
                timestamp=datetime.now().isoformat()
            )

        except PermissionError:
            return RepairOperation(
                operation_id=operation_id,
                operation_type="fix_read_permission",
                target_path=file_path,
                description=f"Add read permission to {file_path} (requires elevation)",
                requires_elevation=True,
                repair_command=f"chmod +r {file_path}",
                rollback_command=None,
                result=RepairResult.REQUIRES_ELEVATION,
                error_message="Permission denied - requires administrator privileges",
                timestamp=datetime.now().isoformat()
            )
        except Exception as e:
            return RepairOperation(
                operation_id=operation_id,
                operation_type="fix_read_permission",
                target_path=file_path,
                description=f"Failed to fix read permission for {file_path}",
                requires_elevation=False,
                repair_command=f"chmod +r {file_path}",
                rollback_command=None,
                result=RepairResult.FAILED,
                error_message=str(e),
                timestamp=datetime.now().isoformat()
            )

    def _fix_write_permission(self, file_path: str, target_permissions: str) -> RepairOperation:
        """Fix write permission for a file"""
        operation_id = f"write_fix_{int(datetime.now().timestamp())}"

        try:
            # Add write permission for owner
            current_mode = os.stat(file_path).st_mode
            new_mode = current_mode | stat.S_IWUSR

            os.chmod(file_path, new_mode)

            return RepairOperation(
                operation_id=operation_id,
                operation_type="fix_write_permission",
                target_path=file_path,
                description=f"Added write permission to {file_path}",
                requires_elevation=False,
                repair_command=f"chmod +w {file_path}",
                rollback_command=f"chmod {oct(os.stat(file_path).st_mode)[-3:]} {file_path}",
                result=RepairResult.SUCCESS,
                error_message=None,
                timestamp=datetime.now().isoformat()
            )

        except PermissionError:
            return RepairOperation(
                operation_id=operation_id,
                operation_type="fix_write_permission",
                target_path=file_path,
                description=f"Add write permission to {file_path} (requires elevation)",
                requires_elevation=True,
                repair_command=f"chmod +w {file_path}",
                rollback_command=None,
                result=RepairResult.REQUIRES_ELEVATION,
                error_message="Permission denied - requires administrator privileges",
                timestamp=datetime.now().isoformat()
            )
        except Exception as e:
            return RepairOperation(
                operation_id=operation_id,
                operation_type="fix_write_permission",
                target_path=file_path,
                description=f"Failed to fix write permission for {file_path}",
                requires_elevation=False,
                repair_command=f"chmod +w {file_path}",
                rollback_command=None,
                result=RepairResult.FAILED,
                error_message=str(e),
                timestamp=datetime.now().isoformat()
            )

    def _fix_execute_permission(self, file_path: str, target_permissions: str) -> RepairOperation:
        """Fix execute permission for a directory"""
        operation_id = f"exec_fix_{int(datetime.now().timestamp())}"

        try:
            # Add execute permission for user, group, and others (for directories)
            current_mode = os.stat(file_path).st_mode
            new_mode = current_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH

            os.chmod(file_path, new_mode)

            return RepairOperation(
                operation_id=operation_id,
                operation_type="fix_execute_permission",
                target_path=file_path,
                description=f"Added execute permission to directory {file_path}",
                requires_elevation=False,
                repair_command=f"chmod +x {file_path}",
                rollback_command=f"chmod {oct(os.stat(file_path).st_mode)[-3:]} {file_path}",
                result=RepairResult.SUCCESS,
                error_message=None,
                timestamp=datetime.now().isoformat()
            )

        except PermissionError:
            return RepairOperation(
                operation_id=operation_id,
                operation_type="fix_execute_permission",
                target_path=file_path,
                description=f"Add execute permission to directory {file_path} (requires elevation)",
                requires_elevation=True,
                repair_command=f"chmod +x {file_path}",
                rollback_command=None,
                result=RepairResult.REQUIRES_ELEVATION,
                error_message="Permission denied - requires administrator privileges",
                timestamp=datetime.now().isoformat()
            )
        except Exception as e:
            return RepairOperation(
                operation_id=operation_id,
                operation_type="fix_execute_permission",
                target_path=file_path,
                description=f"Failed to fix execute permission for {file_path}",
                requires_elevation=False,
                repair_command=f"chmod +x {file_path}",
                rollback_command=None,
                result=RepairResult.FAILED,
                error_message=str(e),
                timestamp=datetime.now().isoformat()
            )

    def _apply_recursive_permissions(self, dir_path: str, target_permissions: str) -> List[RepairOperation]:
        """Apply permissions recursively to directory contents"""
        operations = []

        try:
            path_obj = Path(dir_path)

            for root, dirs, files in os.walk(dir_path):
                # Fix directory permissions
                for dir_name in dirs:
                    full_dir_path = os.path.join(root, dir_name)
                    dir_op = self._fix_execute_permission(full_dir_path, target_permissions)
                    operations.append(dir_op)

                # Fix file permissions
                for file_name in files:
                    full_file_path = os.path.join(root, file_name)
                    file_result = self.diagnostic.check_file_permissions(full_file_path)

                    if not file_result.readable:
                        read_op = self._fix_read_permission(full_file_path, target_permissions)
                        operations.append(read_op)

                    if not file_result.writable:
                        write_op = self._fix_write_permission(full_file_path, target_permissions)
                        operations.append(write_op)

        except Exception as e:
            logger.error(f"Error applying recursive permissions to {dir_path}: {e}")

        return operations

    def _get_elevation_method(self) -> ElevationMethod:
        """Get the appropriate elevation method for the current platform"""
        if self.diagnostic.platform == PlatformType.WINDOWS:
            return ElevationMethod.UAC
        else:
            return ElevationMethod.SUDO

    def _generate_repair_suggestions(self, file_path: str,
                                    current_result: FilePermissionResult) -> List[str]:
        """Generate suggestions based on repair results"""
        suggestions = []

        if not current_result.exists:
            suggestions.append(f"Create the missing path: mkdir -p {file_path}")

        if self.diagnostic.platform == PlatformType.WINDOWS:
            suggestions.extend([
                "Run the application as Administrator",
                "Check file security properties in Windows Explorer",
                "Ensure your user account has the necessary permissions"
            ])
        else:
            suggestions.extend([
                f"Use sudo to fix permissions: sudo chmod +rw {file_path}",
                "Change file ownership: sudo chown $USER:$USER {file_path}",
                "Check if the file is in a protected system directory"
            ])

        return suggestions

    def rollback_permissions(self, backup_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Rollback permissions using stored backup information
        """
        logger.info(f"Rolling back permissions (backup_id: {backup_id})")

        if backup_id:
            backups_to_rollback = [b for b in self.backups if b.backup_id == backup_id]
        else:
            # Rollback all backups
            backups_to_rollback = self.backups

        if not backups_to_rollback:
            return {
                'success': False,
                'error': 'No backups found for rollback',
                'rolled_back_count': 0
            }

        rolled_back_count = 0
        errors = []

        for backup in backups_to_rollback:
            try:
                path_obj = Path(backup.path)
                if not path_obj.exists():
                    logger.warning(f"Cannot rollback {backup.path} - path no longer exists")
                    continue

                # Restore permissions
                if backup.original_permissions:
                    target_mode = int(backup.original_permissions, 8)
                    os.chmod(backup.path, target_mode)

                # Restore ownership on Unix systems
                if UNIX_SUPPORT and self.diagnostic.platform != PlatformType.WINDOWS:
                    if backup.original_owner:
                        try:
                            uid = pwd.getpwnam(backup.original_owner).pw_uid
                            gid = grp.getgrnam(backup.original_group).gr_gid if backup.original_group else -1
                            os.chown(backup.path, uid, gid)
                        except Exception as e:
                            logger.warning(f"Could not restore ownership for {backup.path}: {e}")

                rolled_back_count += 1
                logger.info(f"Successfully rolled back permissions for {backup.path}")

            except Exception as e:
                error_msg = f"Error rolling back {backup.path}: {e}"
                logger.error(error_msg)
                errors.append(error_msg)

        return {
            'success': rolled_back_count > 0,
            'rolled_back_count': rolled_back_count,
            'total_backups': len(backups_to_rollback),
            'errors': errors
        }

    def verify_repair(self, file_path: str, expected_permissions: Optional[str] = None) -> Dict[str, Any]:
        """
        Verify that permission repairs were successful
        """
        logger.info(f"Verifying permission repair for: {file_path}")

        try:
            current_result = self.diagnostic.check_file_permissions(file_path)

            verification = {
                'path': file_path,
                'exists': current_result.exists,
                'readable': current_result.readable,
                'writable': current_result.writable,
                'executable': current_result.executable,
                'permissions': current_result.permissions,
                'issues': current_result.issues,
                'verification_passed': len(current_result.issues) == 0
            }

            if expected_permissions:
                verification['permissions_match'] = current_result.permissions == expected_permissions
                verification['verification_passed'] &= verification['permissions_match']

            return verification

        except Exception as e:
            return {
                'path': file_path,
                'verification_passed': False,
                'error': str(e)
            }

    def request_privilege_elevation(self, method: Optional[ElevationMethod] = None) -> Dict[str, Any]:
        """
        Request privilege elevation using platform-appropriate method
        """
        return self.elevation_request.request_elevation(method)

    def save_backup_state(self, file_path: str) -> Dict[str, Any]:
        """
        Save current backup state to a file for persistence
        """
        try:
            backup_data = {
                'backups': [asdict(backup) for backup in self.backups],
                'operations': [asdict(op) for op in self.operations],
                'timestamp': datetime.now().isoformat()
            }

            with open(file_path, 'w') as f:
                json.dump(backup_data, f, indent=2)

            return {
                'success': True,
                'file_path': file_path,
                'backups_count': len(self.backups),
                'operations_count': len(self.operations)
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def load_backup_state(self, file_path: str) -> Dict[str, Any]:
        """
        Load backup state from a file
        """
        try:
            with open(file_path, 'r') as f:
                backup_data = json.load(f)

            # Restore backups
            self.backups = [
                PermissionBackup(**backup)
                for backup in backup_data.get('backups', [])
            ]

            # Restore operations
            self.operations = [
                RepairOperation(**op)
                for op in backup_data.get('operations', [])
            ]

            return {
                'success': True,
                'backups_loaded': len(self.backups),
                'operations_loaded': len(self.operations)
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }