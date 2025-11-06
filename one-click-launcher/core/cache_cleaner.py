"""
Cache Cleaner and Temporary File Cleanup Module

This module provides comprehensive cache corruption detection, safe cleanup mechanisms,
and multi-platform cache path identification and cleanup.
"""

import os
import sys
import platform
import shutil
import hashlib
import json
import gzip
import sqlite3
import tempfile
import time
import subprocess
from typing import Dict, List, Optional, Tuple, Union, Any, Set
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
from datetime import datetime, timedelta

from utils.logger import get_logger
from utils.progress_tracker import ProgressTracker

logger = get_logger(__name__)


class CacheType(Enum):
    """Types of cache that can be cleaned"""
    BROWSER_CACHE = "browser_cache"
    SYSTEM_TEMP = "system_temp"
    APPLICATION_CACHE = "application_cache"
    LOG_FILES = "log_files"
    DATABASE_CACHE = "database_cache"
    PACKAGE_CACHE = "package_cache"
    DOCKER_CACHE = "docker_cache"
    NODE_MODULES = "node_modules"
    PYTHON_CACHE = "python_cache"


class CleanupPolicy(Enum):
    """Cleanup policies for different scenarios"""
    SAFE = "safe"  # Only remove clearly safe files
    MODERATE = "moderate"  # Remove most temp files, keep important cache
    AGGRESSIVE = "aggressive"  # Remove almost all cache and temp files
    CUSTOM = "custom"  # User-defined rules


@dataclass
class CacheEntry:
    """Represents a cache file or directory entry"""
    path: str
    cache_type: CacheType
    size_bytes: int
    last_modified: datetime
    last_accessed: Optional[datetime]
    is_corrupted: bool
    is_safe_to_delete: bool
    risk_level: str  # 'low', 'medium', 'high'
    description: str


@dataclass
class CleanupOperation:
    """Represents a cleanup operation"""
    operation_id: str
    cache_type: CacheType
    target_path: str
    operation_type: str  # 'delete', 'compress', 'move'
    original_size: int
    space_freed: int
    status: str  # 'pending', 'completed', 'failed', 'skipped'
    error_message: Optional[str]
    timestamp: datetime
    backup_path: Optional[str]


@dataclass
class CleanupResult:
    """Result of a cache cleanup operation"""
    success: bool
    total_space_freed: int
    files_processed: int
    directories_processed: int
    errors: List[str]
    operations: List[CleanupOperation]
    cleanup_policy: CleanupPolicy
    duration_seconds: float


class CacheCorruptionDetector:
    """Detects corrupted cache files"""

    def __init__(self):
        self.corruption_indicators = {
            'json': self._is_json_corrupted,
            'sqlite': self._is_sqlite_corrupted,
            'gzip': self._is_gzip_corrupted,
            'binary': self._is_binary_corrupted,
        }

    def check_corruption(self, file_path: str) -> Tuple[bool, str]:
        """
        Check if a cache file is corrupted
        Returns (is_corrupted, reason)
        """
        if not os.path.isfile(file_path):
            return False, "File does not exist"

        try:
            # Check file size
            if os.path.getsize(file_path) == 0:
                return True, "Empty file"

            # Check by extension
            ext = Path(file_path).suffix.lower()

            if ext == '.json':
                return self.corruption_indicators['json'](file_path)
            elif ext in ['.db', '.sqlite', '.sqlite3']:
                return self.corruption_indicators['sqlite'](file_path)
            elif ext == '.gz':
                return self.corruption_indicators['gzip'](file_path)
            else:
                return self.corruption_indicators['binary'](file_path)

        except Exception as e:
            return True, f"Error checking corruption: {e}"

    def _is_json_corrupted(self, file_path: str) -> Tuple[bool, str]:
        """Check if JSON file is corrupted"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                json.load(f)
            return False, "JSON file is valid"
        except json.JSONDecodeError as e:
            return True, f"Invalid JSON: {e}"
        except Exception as e:
            return True, f"Error reading JSON file: {e}"

    def _is_sqlite_corrupted(self, file_path: str) -> Tuple[bool, str]:
        """Check if SQLite database is corrupted"""
        try:
            conn = sqlite3.connect(file_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            cursor.fetchone()
            conn.close()
            return False, "SQLite database is valid"
        except sqlite3.DatabaseError as e:
            return True, f"SQLite database corrupted: {e}"
        except Exception as e:
            return True, f"Error reading SQLite database: {e}"

    def _is_gzip_corrupted(self, file_path: str) -> Tuple[bool, str]:
        """Check if gzip file is corrupted"""
        try:
            with gzip.open(file_path, 'rb') as f:
                f.read(1024)  # Read first 1KB to test
            return False, "Gzip file is valid"
        except (gzip.BadGzipFile, OSError) as e:
            return True, f"Gzip file corrupted: {e}"
        except Exception as e:
            return True, f"Error reading gzip file: {e}"

    def _is_binary_corrupted(self, file_path: str) -> Tuple[bool, str]:
        """Check if binary file is corrupted using basic heuristics"""
        try:
            size = os.path.getsize(file_path)

            # Check if file is too large for cache (likely corrupted)
            if size > 1024 * 1024 * 1024:  # 1GB
                return True, "File too large for cache"

            # Try to read first bytes
            with open(file_path, 'rb') as f:
                header = f.read(16)

            # Check if file is all zeros (common corruption pattern)
            if all(b == 0 for b in header):
                return True, "File appears to be empty/zeroed"

            return False, "Binary file appears valid"

        except Exception as e:
            return True, f"Error checking binary file: {e}"


class SafeFileCleaner:
    """Safely cleans files with comprehensive checks"""

    def __init__(self, dry_run: bool = True):
        self.dry_run = dry_run
        self.protected_patterns = {
            # System critical files
            r'^/etc/', r'^/usr/', r'^/bin/', r'^/sbin/', r'^/lib/', r'^/lib64/',
            r'^C:\\Windows\\', r'^C:\\Program Files\\', r'^C:\\Program Files (x86)\\',

            # Important user data
            r'.*\.important$', r'.*\.critical$', r'.*\.config\.(save|backup)$',

            # Database files that shouldn't be auto-deleted
            r'.*\.db$', r'.*\.sqlite$', r'.*\.sqlite3$',

            # User documents
            r'.*\.doc$', r'.*\.docx$', r'.*\.pdf$', r'.*\.xls$', r'.*\.xlsx$',
        }

    def is_safe_to_delete(self, file_path: str, cache_type: CacheType) -> Tuple[bool, str]:
        """
        Determine if a file is safe to delete
        Returns (is_safe, reason)
        """
        path_obj = Path(file_path)

        # Check if file exists
        if not path_obj.exists():
            return False, "File does not exist"

        # Check against protected patterns
        import re
        for pattern in self.protected_patterns:
            if re.match(pattern, file_path, re.IGNORECASE):
                return False, f"File matches protected pattern: {pattern}"

        # Check file age
        try:
            stat_info = path_obj.stat()
            file_age = datetime.now() - datetime.fromtimestamp(stat_info.st_mtime)

            # Very recent files might be in use
            if file_age < timedelta(minutes=5):
                return False, "File is too recent (might be in use)"

            # Important system files shouldn't be deleted regardless of age
            if self._is_system_file(file_path):
                return False, "File appears to be a system file"

        except Exception as e:
            return False, f"Error checking file properties: {e}"

        # Check based on cache type
        if cache_type == CacheType.BROWSER_CACHE:
            return self._is_browser_cache_safe(file_path)
        elif cache_type == CacheType.APPLICATION_CACHE:
            return self._is_application_cache_safe(file_path)
        elif cache_type == CacheType.SYSTEM_TEMP:
            return self._is_temp_file_safe(file_path)
        elif cache_type == CacheType.PYTHON_CACHE:
            return self._is_python_cache_safe(file_path)
        elif cache_type == CacheType.NODE_MODULES:
            return self._is_node_modules_safe(file_path)
        else:
            return True, "File appears safe to delete"

    def _is_system_file(self, file_path: str) -> bool:
        """Check if file appears to be a system file"""
        system_indicators = [
            '/System/', '/Library/', '/Windows/', '/Program Files/',
            'system32', 'SysWOW64', 'drivers', 'etc'
        ]

        return any(indicator.lower() in file_path.lower() for indicator in system_indicators)

    def _is_browser_cache_safe(self, file_path: str) -> Tuple[bool, str]:
        """Check if browser cache file is safe to delete"""
        browser_cache_patterns = [
            'cache/', 'Cache/', 'Cache2/', 'Cache4/', 'startupCache/',
            '.cache/', 'Caches/', 'GPUCache/', 'ShaderCache/',
            'chrome_cache/', 'firefox_cache/', 'edge_cache/'
        ]

        if any(pattern in file_path for pattern in browser_cache_patterns):
            return True, "Browser cache file - safe to delete"

        return False, "File doesn't appear to be browser cache"

    def _is_application_cache_safe(self, file_path: str) -> Tuple[bool, str]:
        """Check if application cache file is safe to delete"""
        # 规范化路径分隔符以支持跨平台
        normalized_path = file_path.replace('\\', '/')

        # 首先检查保护模式，如果匹配保护模式则不安全
        import re
        for pattern in self.protected_patterns:
            if re.match(pattern, file_path, re.IGNORECASE):
                return False, f"File matches protected pattern: {pattern}"

        # 检查文件名是否包含重要关键词
        important_keywords = ['important', 'critical', 'config', 'backup']
        filename = os.path.basename(file_path).lower()
        if any(keyword in filename for keyword in important_keywords):
            return False, "File appears to be important based on filename"

        app_cache_patterns = [
            'cache/', 'tmp/', 'temp/', '.tmp/', 'logs/',
            '.cache/', '__pycache__/', 'node_modules/', '.next/',
            'dist/', 'build/', '.vscode/', '.idea/'
        ]

        if any(pattern in normalized_path for pattern in app_cache_patterns):
            return True, "Application cache file - safe to delete"

        return False, "File doesn't appear to be application cache"

    def _is_temp_file_safe(self, file_path: str) -> Tuple[bool, str]:
        """Check if temporary file is safe to delete"""
        temp_patterns = [
            '/tmp/', '/var/tmp/', 'temp/', 'tmp/', '.tmp',
            'tempfile', 'temporary', 'cache_temp'
        ]

        if any(pattern in file_path for pattern in temp_patterns):
            return True, "Temporary file - safe to delete"

        return False, "File doesn't appear to be temporary"

    def _is_python_cache_safe(self, file_path: str) -> Tuple[bool, str]:
        """Check if Python cache file is safe to delete"""
        python_cache_patterns = [
            '__pycache__/', '.pyc', '.pyo', '.pyd',
            '.pytest_cache/', '.mypy_cache/', '.tox/', 'pip-cache/'
        ]

        if any(pattern in file_path for pattern in python_cache_patterns):
            return True, "Python cache file - safe to delete"

        return False, "File doesn't appear to be Python cache"

    def _is_node_modules_safe(self, file_path: str) -> Tuple[bool, str]:
        """Check if Node.js module is safe to delete"""
        if 'node_modules/' in file_path:
            return True, "Node.js module - can be reinstalled"

        return False, "File doesn't appear to be Node.js module"

    def delete_file_safely(self, file_path: str, backup_dir: Optional[str] = None) -> Tuple[bool, str, Optional[str]]:
        """
        Safely delete a file with optional backup
        Returns (success, message, backup_path)
        """
        if self.dry_run:
            return True, f"DRY RUN: Would delete {file_path}", None

        try:
            # Create backup if requested
            backup_path = None
            if backup_dir:
                backup_path = self._create_backup(file_path, backup_dir)

            # Delete the file
            if os.path.isfile(file_path):
                os.remove(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)

            return True, f"Successfully deleted {file_path}", backup_path

        except Exception as e:
            return False, f"Error deleting {file_path}: {e}", None

    def _create_backup(self, file_path: str, backup_dir: str) -> str:
        """Create a backup of the file before deletion"""
        os.makedirs(backup_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.basename(file_path)
        backup_filename = f"{timestamp}_{filename}"
        backup_path = os.path.join(backup_dir, backup_filename)

        if os.path.isfile(file_path):
            shutil.copy2(file_path, backup_path)
        elif os.path.isdir(file_path):
            shutil.copytree(file_path, backup_path)

        return backup_path


class CacheCleaner:
    """Main cache cleaner orchestrator"""

    def __init__(self, progress_tracker: Optional[ProgressTracker] = None,
                 dry_run: bool = False,
                 backup_dir: Optional[str] = None):
        self.progress_tracker = progress_tracker
        self.dry_run = dry_run
        self.backup_dir = backup_dir or tempfile.mkdtemp(prefix="cache_cleanup_backup_")
        self.corruption_detector = CacheCorruptionDetector()
        self.file_cleaner = SafeFileCleaner(dry_run=dry_run)
        self.platform = self._detect_platform()
        self.cache_paths = self._get_cache_paths()

    def _detect_platform(self) -> str:
        """Detect the current platform"""
        return platform.system().lower()

    def _get_cache_paths(self) -> Dict[CacheType, List[str]]:
        """Get platform-specific cache paths"""
        if self.platform == "windows":
            return self._get_windows_cache_paths()
        elif self.platform == "darwin":
            return self._get_macos_cache_paths()
        else:
            return self._get_linux_cache_paths()

    def _get_windows_cache_paths(self) -> Dict[CacheType, List[str]]:
        """Get Windows cache paths"""
        import winreg

        paths = {
            CacheType.SYSTEM_TEMP: [
                os.environ.get('TEMP', 'C:\\temp'),
                os.environ.get('TMP', 'C:\\tmp'),
                'C:\\Windows\\Temp',
                'C:\\Windows\\Prefetch'
            ],
            CacheType.BROWSER_CACHE: self._get_windows_browser_cache(),
            CacheType.APPLICATION_CACHE: [
                os.path.expandvars('%LOCALAPPDATA%\\Temp'),
                os.path.expandvars('%APPDATA%\\..\\Local\\Temp'),
            ],
            CacheType.PYTHON_CACHE: self._get_python_cache_paths(),
            CacheType.NODE_MODULES: self._get_node_modules_paths(),
        }

        return paths

    def _get_windows_browser_cache(self) -> List[str]:
        """Get Windows browser cache paths"""
        browser_paths = []

        try:
            # Chrome
            local_app_data = os.path.expandvars('%LOCALAPPDATA%')
            chrome_cache = os.path.join(local_app_data, 'Google\\Chrome\\User Data\\Default\\Cache')
            if os.path.exists(chrome_cache):
                browser_paths.append(chrome_cache)

            # Firefox
            app_data = os.path.expandvars('%APPDATA%')
            firefox_cache = os.path.join(app_data, 'Mozilla\\Firefox\\Profiles')
            if os.path.exists(firefox_cache):
                for profile in os.listdir(firefox_cache):
                    cache_path = os.path.join(firefox_cache, profile, 'cache2')
                    if os.path.exists(cache_path):
                        browser_paths.append(cache_path)

            # Edge
            edge_cache = os.path.join(local_app_data, 'Microsoft\\Edge\\User Data\\Default\\Cache')
            if os.path.exists(edge_cache):
                browser_paths.append(edge_cache)

        except Exception as e:
            logger.warning(f"Error detecting browser cache paths: {e}")

        return browser_paths

    def _get_macos_cache_paths(self) -> Dict[CacheType, List[str]]:
        """Get macOS cache paths"""
        home = os.path.expanduser('~')

        return {
            CacheType.SYSTEM_TEMP: [
                '/tmp',
                '/var/tmp',
                os.path.join(home, 'Library/Caches'),
            ],
            CacheType.BROWSER_CACHE: [
                os.path.join(home, 'Library/Caches/Google/Chrome'),
                os.path.join(home, 'Library/Caches/Firefox'),
                os.path.join(home, 'Library/Caches/Microsoft Edge'),
            ],
            CacheType.APPLICATION_CACHE: [
                os.path.join(home, 'Library/Application Support'),
                os.path.join(home, 'Library/Preferences'),
            ],
            CacheType.PYTHON_CACHE: self._get_python_cache_paths(),
            CacheType.NODE_MODULES: self._get_node_modules_paths(),
        }

    def _get_linux_cache_paths(self) -> Dict[CacheType, List[str]]:
        """Get Linux cache paths"""
        home = os.path.expanduser('~')

        return {
            CacheType.SYSTEM_TEMP: [
                '/tmp',
                '/var/tmp',
                '/var/cache',
            ],
            CacheType.BROWSER_CACHE: [
                os.path.join(home, '.cache/google-chrome'),
                os.path.join(home, '.cache/mozilla/firefox'),
                os.path.join(home, '.cache/microsoft-edge'),
            ],
            CacheType.APPLICATION_CACHE: [
                os.path.join(home, '.cache'),
                '/var/cache',
            ],
            CacheType.PYTHON_CACHE: self._get_python_cache_paths(),
            CacheType.NODE_MODULES: self._get_node_modules_paths(),
        }

    def _get_python_cache_paths(self) -> List[str]:
        """Get Python cache paths"""
        paths = []

        try:
            # __pycache__ directories
            for root, dirs, files in os.walk('.'):
                if '__pycache__' in dirs:
                    paths.append(os.path.join(root, '__pycache__'))

            # pip cache
            import pip
            if hasattr(pip, 'main'):
                result = subprocess.run(['pip', 'cache', 'dir'],
                                     capture_output=True, text=True)
                if result.returncode == 0:
                    paths.append(result.stdout.strip())

        except Exception as e:
            logger.warning(f"Error detecting Python cache paths: {e}")

        return paths

    def _get_node_modules_paths(self) -> List[str]:
        """Get Node.js modules paths"""
        paths = []

        try:
            for root, dirs, files in os.walk('.'):
                if 'node_modules' in dirs:
                    paths.append(os.path.join(root, 'node_modules'))

        except Exception as e:
            logger.warning(f"Error detecting Node.js modules paths: {e}")

        return paths

    def scan_cache_directories(self, cache_types: Optional[List[CacheType]] = None) -> List[CacheEntry]:
        """
        Scan cache directories and identify files for cleanup
        """
        if cache_types is None:
            cache_types = list(CacheType)

        if self.progress_tracker:
            self.progress_tracker._log("Starting cache directory scan (0%)")

        entries = []
        total_scanned = 0

        for cache_type in cache_types:
            if cache_type not in self.cache_paths:
                continue

            paths = self.cache_paths[cache_type]

            for path in paths:
                if not os.path.exists(path):
                    continue

                try:
                    path_entries = self._scan_directory(path, cache_type)
                    entries.extend(path_entries)
                    total_scanned += len(path_entries)

                    if self.progress_tracker:
                        progress = min(95, (total_scanned / 1000) * 100)  # Rough progress estimate
                        self.progress_tracker._log(f"Scanned {total_scanned} files ({progress:.0f}%)")

                except Exception as e:
                    logger.error(f"Error scanning directory {path}: {e}")

        if self.progress_tracker:
            self.progress_tracker._log(f"Cache scan completed. Found {len(entries)} entries (100%)")

        return entries

    def _scan_directory(self, directory: str, cache_type: CacheType) -> List[CacheEntry]:
        """Scan a single directory for cache entries"""
        entries = []

        try:
            for root, dirs, files in os.walk(directory):
                # Files
                for file_name in files:
                    file_path = os.path.join(root, file_name)
                    entry = self._create_cache_entry(file_path, cache_type)
                    if entry:
                        entries.append(entry)

                # Directories
                for dir_name in dirs:
                    dir_path = os.path.join(root, dir_name)
                    entry = self._create_cache_entry(dir_path, cache_type)
                    if entry:
                        entries.append(entry)

        except Exception as e:
            logger.error(f"Error scanning {directory}: {e}")

        return entries

    def _create_cache_entry(self, path: str, cache_type: CacheType) -> Optional[CacheEntry]:
        """Create a cache entry for a file or directory"""
        try:
            path_obj = Path(path)
            stat_info = path_obj.stat()

            # Check corruption for files
            is_corrupted = False
            if path_obj.is_file():
                is_corrupted, _ = self.corruption_detector.check_corruption(path)

            # Check if safe to delete
            is_safe_to_delete, reason = self.file_cleaner.is_safe_to_delete(path, cache_type)

            # Determine risk level
            risk_level = self._assess_risk_level(path, cache_type, is_corrupted, is_safe_to_delete)

            # Get file access time if available
            last_accessed = None
            if hasattr(stat_info, 'st_atime'):
                last_accessed = datetime.fromtimestamp(stat_info.st_atime)

            entry = CacheEntry(
                path=path,
                cache_type=cache_type,
                size_bytes=stat_info.st_size,
                last_modified=datetime.fromtimestamp(stat_info.st_mtime),
                last_accessed=last_accessed,
                is_corrupted=is_corrupted,
                is_safe_to_delete=is_safe_to_delete,
                risk_level=risk_level,
                description=reason
            )

            return entry

        except Exception as e:
            logger.error(f"Error creating cache entry for {path}: {e}")
            return None

    def _assess_risk_level(self, path: str, cache_type: CacheType,
                         is_corrupted: bool, is_safe_to_delete: bool) -> str:
        """Assess the risk level of deleting a cache entry"""

        if not is_safe_to_delete:
            return "high"

        if is_corrupted:
            return "low"  # Corrupted files are safe to delete

        # Check file age
        try:
            file_age = datetime.now() - datetime.fromtimestamp(os.path.getmtime(path))

            # Old files are lower risk to delete
            if file_age > timedelta(days=30):
                return "low"
            elif file_age > timedelta(days=7):
                return "medium"
            else:
                return "medium"

        except Exception:
            return "medium"

    def cleanup_cache(self, cache_types: Optional[List[CacheType]] = None,
                     policy: CleanupPolicy = CleanupPolicy.SAFE,
                     force: bool = False) -> CleanupResult:
        """
        Clean up cache files according to policy
        """
        start_time = time.time()

        logger.info(f"Starting cache cleanup with policy: {policy.value}")

        if self.progress_tracker:
            self.progress_tracker._log("Starting cache cleanup (0%)")

        # Scan cache directories
        entries = self.scan_cache_directories(cache_types)

        # Filter entries based on policy
        filtered_entries = self._filter_entries_by_policy(entries, policy, force)

        # Perform cleanup operations
        operations = []
        total_space_freed = 0
        errors = []
        files_processed = 0
        directories_processed = 0

        for i, entry in enumerate(filtered_entries):
            try:
                operation = self._cleanup_entry(entry)
                operations.append(operation)

                if operation.status == 'completed':
                    total_space_freed += operation.space_freed
                    if os.path.isfile(entry.path):
                        files_processed += 1
                    else:
                        directories_processed += 1
                elif operation.status == 'failed':
                    errors.append(operation.error_message)

                if self.progress_tracker:
                    progress = (i + 1) / len(filtered_entries) * 100
                    self.progress_tracker._log(f"Processed {i + 1}/{len(filtered_entries)} entries ({progress:.0f}%)")

            except Exception as e:
                error_msg = f"Error processing {entry.path}: {e}"
                errors.append(error_msg)
                logger.error(error_msg)

        duration = time.time() - start_time
        success = len(errors) == 0

        if self.progress_tracker:
            self.progress_tracker._log(f"Cache cleanup completed (100%)")

        result = CleanupResult(
            success=success,
            total_space_freed=total_space_freed,
            files_processed=files_processed,
            directories_processed=directories_processed,
            errors=errors,
            operations=operations,
            cleanup_policy=policy,
            duration_seconds=duration
        )

        self._log_cleanup_result(result)
        return result

    def _filter_entries_by_policy(self, entries: List[CacheEntry],
                                policy: CleanupPolicy, force: bool) -> List[CacheEntry]:
        """Filter cache entries based on cleanup policy"""

        if force:
            return entries  # Force cleanup ignores safety checks

        filtered = []

        for entry in entries:
            include = False

            if policy == CleanupPolicy.SAFE:
                # Only safe, corrupted, or very old files
                include = (
                    entry.is_safe_to_delete or
                    entry.is_corrupted or
                    entry.risk_level == 'low'
                )
            elif policy == CleanupPolicy.MODERATE:
                # Include most cache files except high-risk
                include = entry.risk_level != 'high'
            elif policy == CleanupPolicy.AGGRESSIVE:
                # Include everything except critical system files
                include = entry.risk_level != 'critical'
            else:  # CUSTOM
                # Apply custom rules (can be extended)
                include = entry.is_safe_to_delete

            if include:
                filtered.append(entry)

        return filtered

    def _cleanup_entry(self, entry: CacheEntry) -> CleanupOperation:
        """Clean up a single cache entry"""
        operation_id = f"cleanup_{int(datetime.now().timestamp())}"

        try:
            original_size = entry.size_bytes

            # Perform the cleanup
            success, message, backup_path = self.file_cleaner.delete_file_safely(
                entry.path, self.backup_dir
            )

            if success:
                status = 'completed'
                space_freed = original_size
                error_message = None
            else:
                status = 'failed'
                space_freed = 0
                error_message = message
                backup_path = None

            return CleanupOperation(
                operation_id=operation_id,
                cache_type=entry.cache_type,
                target_path=entry.path,
                operation_type='delete',
                original_size=original_size,
                space_freed=space_freed,
                status=status,
                error_message=error_message,
                timestamp=datetime.now(),
                backup_path=backup_path
            )

        except Exception as e:
            return CleanupOperation(
                operation_id=operation_id,
                cache_type=entry.cache_type,
                target_path=entry.path,
                operation_type='delete',
                original_size=entry.size_bytes,
                space_freed=0,
                status='failed',
                error_message=str(e),
                timestamp=datetime.now(),
                backup_path=None
            )

    def _log_cleanup_result(self, result: CleanupResult):
        """Log the cleanup result"""
        space_freed_mb = result.total_space_freed / (1024 * 1024)

        logger.info(f"Cache cleanup completed:")
        logger.info(f"  Success: {result.success}")
        logger.info(f"  Space freed: {space_freed_mb:.2f} MB")
        logger.info(f"  Files processed: {result.files_processed}")
        logger.info(f"  Directories processed: {result.directories_processed}")
        logger.info(f"  Duration: {result.duration_seconds:.2f} seconds")
        logger.info(f"  Errors: {len(result.errors)}")

        if result.errors:
            logger.error("Cleanup errors:")
            for error in result.errors[:10]:  # Log first 10 errors
                logger.error(f"  - {error}")

    def schedule_periodic_cleanup(self, interval_hours: int = 24,
                                cache_types: Optional[List[CacheType]] = None,
                                policy: CleanupPolicy = CleanupPolicy.SAFE):
        """
        Schedule periodic cleanup (placeholder for implementation)
        """
        logger.info(f"Periodic cleanup scheduled every {interval_hours} hours")
        # This would be implemented with a scheduler like APScheduler
        # For now, just log the intent

    def get_cleanup_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about available cache for cleanup
        """
        try:
            entries = self.scan_cache_directories()

            stats = {
                'total_entries': len(entries),
                'total_size_bytes': sum(entry.size_bytes for entry in entries),
                'corrupted_files': sum(1 for entry in entries if entry.is_corrupted),
                'safe_to_delete': sum(1 for entry in entries if entry.is_safe_to_delete),
                'risk_breakdown': {
                    'low': sum(1 for entry in entries if entry.risk_level == 'low'),
                    'medium': sum(1 for entry in entries if entry.risk_level == 'medium'),
                    'high': sum(1 for entry in entries if entry.risk_level == 'high'),
                },
                'cache_type_breakdown': {}
            }

            for cache_type in CacheType:
                type_entries = [entry for entry in entries if entry.cache_type == cache_type]
                stats['cache_type_breakdown'][cache_type.value] = {
                    'count': len(type_entries),
                    'size_bytes': sum(entry.size_bytes for entry in type_entries)
                }

            # Add human-readable sizes
            stats['total_size_mb'] = stats['total_size_bytes'] / (1024 * 1024)
            stats['total_size_gb'] = stats['total_size_mb'] / 1024

            return stats

        except Exception as e:
            logger.error(f"Error getting cleanup statistics: {e}")
            return {'error': str(e)}