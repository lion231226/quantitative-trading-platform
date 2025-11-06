"""
Cross-platform file operations abstraction.

This module provides a unified interface for file operations that work
consistently across different platforms while handling platform-specific
behaviors like permissions, attributes, and limitations.
"""

import os
import shutil
import stat
import tempfile
import hashlib
import json
import csv
from pathlib import Path, PurePath
from typing import Union, List, Optional, Dict, Any, BinaryIO, TextIO
from dataclasses import dataclass
from enum import Enum
import time
from contextlib import contextmanager

from .platform_paths import PlatformPathHandler, get_platform_handler
from .logger_new import get_logger

logger = get_logger(__name__)


class FileMode(Enum):
    """File operation modes"""
    READ = 'r'
    WRITE = 'w'
    APPEND = 'a'
    READ_WRITE = 'r+'
    BINARY_READ = 'rb'
    BINARY_WRITE = 'wb'
    BINARY_APPEND = 'ab'
    BINARY_READ_WRITE = 'rb+'


class FileOperation(Enum):
    """File operation types"""
    COPY = 'copy'
    MOVE = 'move'
    DELETE = 'delete'
    CREATE = 'create'
    READ = 'read'
    WRITE = 'write'


@dataclass
class FileInfo:
    """File information container"""
    path: Path
    size: int
    created: float
    modified: float
    accessed: float
    is_file: bool
    is_directory: bool
    is_executable: bool
    is_readable: bool
    is_writable: bool
    permissions: Optional[str] = None
    owner: Optional[str] = None
    group: Optional[str] = None

    @classmethod
    def from_path(cls, path: Path) -> 'FileInfo':
        """Create FileInfo from path"""
        try:
            stat_info = path.stat()

            # Check file type
            is_file = path.is_file()
            is_directory = path.is_dir()

            # Check permissions
            is_readable = os.access(path, os.R_OK)
            is_writable = os.access(path, os.W_OK)
            is_executable = os.access(path, os.X_OK)

            # Format permissions (Unix-like systems)
            permissions = None
            if hasattr(stat_info, 'st_mode'):
                permissions = oct(stat_info.st_mode)[-3:]

            return cls(
                path=path,
                size=stat_info.st_size,
                created=stat_info.st_ctime,
                modified=stat_info.st_mtime,
                accessed=stat_info.st_atime,
                is_file=is_file,
                is_directory=is_directory,
                is_executable=is_executable,
                is_readable=is_readable,
                is_writable=is_writable,
                permissions=permissions
            )

        except Exception as e:
            logger.error(f"Failed to get file info for {path}: {e}")
            return cls(
                path=path,
                size=0,
                created=0,
                modified=0,
                accessed=0,
                is_file=False,
                is_directory=False,
                is_executable=False,
                is_readable=False,
                is_writable=False
            )


@dataclass
class CopyOptions:
    """Options for file copy operations"""
    preserve_metadata: bool = True
    overwrite: bool = False
    verify_integrity: bool = False
    buffer_size: int = 65536  # 64KB
    show_progress: bool = False


@dataclass
class MoveOptions:
    """Options for file move operations"""
    overwrite: bool = False
    atomic: bool = False
    create_backup: bool = False


class FileOperations:
    """
    Cross-platform file operations with unified interface.

    Provides safe, consistent file operations that handle platform-specific
    behaviors and edge cases.
    """

    def __init__(self, platform_handler: Optional[PlatformPathHandler] = None):
        self.platform_handler = platform_handler or get_platform_handler()

    def get_file_info(self, path: Union[str, Path]) -> Optional[FileInfo]:
        """
        Get comprehensive file information.

        Args:
            path: Path to file or directory

        Returns:
            Optional[FileInfo]: File information or None if error
        """
        try:
            normalized_path = self.platform_handler.normalize_path(path)
            if not normalized_path.exists():
                return None

            return FileInfo.from_path(normalized_path)

        except Exception as e:
            logger.error(f"Failed to get file info for {path}: {e}")
            return None

    def file_exists(self, path: Union[str, Path]) -> bool:
        """
        Check if file exists.

        Args:
            path: Path to check

        Returns:
            bool: True if file exists
        """
        try:
            normalized_path = self.platform_handler.normalize_path(path)
            return normalized_path.exists() and normalized_path.is_file()
        except Exception:
            return False

    def directory_exists(self, path: Union[str, Path]) -> bool:
        """
        Check if directory exists.

        Args:
            path: Path to check

        Returns:
            bool: True if directory exists
        """
        try:
            normalized_path = self.platform_handler.normalize_path(path)
            return normalized_path.exists() and normalized_path.is_dir()
        except Exception:
            return False

    def create_directory(self, path: Union[str, Path], parents: bool = True,
                        exist_ok: bool = True) -> bool:
        """
        Create directory with proper error handling.

        Args:
            path: Directory path to create
            parents: Create parent directories if needed
            exist_ok: Don't raise error if directory exists

        Returns:
            bool: True if creation succeeded
        """
        try:
            normalized_path = self.platform_handler.normalize_path(path)
            normalized_path.mkdir(parents=parents, exist_ok=exist_ok)
            return True

        except Exception as e:
            logger.error(f"Failed to create directory {path}: {e}")
            return False

    def copy_file(self, src: Union[str, Path], dst: Union[str, Path],
                 options: Optional[CopyOptions] = None) -> bool:
        """
        Copy file with comprehensive options.

        Args:
            src: Source file path
            dst: Destination file path
            options: Copy operation options

        Returns:
            bool: True if copy succeeded
        """
        if options is None:
            options = CopyOptions()

        try:
            src_path = self.platform_handler.normalize_path(src)
            dst_path = self.platform_handler.normalize_path(dst)

            # Validate source
            if not self.file_exists(src_path):
                logger.error(f"Source file does not exist: {src_path}")
                return False

            # Check destination overwrite
            if self.file_exists(dst_path) and not options.overwrite:
                logger.error(f"Destination file exists and overwrite disabled: {dst_path}")
                return False

            # Ensure destination directory exists
            self.create_directory(dst_path.parent)

            # Copy file
            if options.preserve_metadata:
                shutil.copy2(str(src_path), str(dst_path))
            else:
                shutil.copy(str(src_path), str(dst_path))

            # Verify integrity if requested
            if options.verify_integrity:
                if not self._verify_copy_integrity(src_path, dst_path):
                    logger.error(f"Copy integrity verification failed: {src_path} -> {dst_path}")
                    return False

            logger.info(f"Successfully copied {src_path} to {dst_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to copy {src} to {dst}: {e}")
            return False

    def move_file(self, src: Union[str, Path], dst: Union[str, Path],
                 options: Optional[MoveOptions] = None) -> bool:
        """
        Move file with comprehensive options.

        Args:
            src: Source file path
            dst: Destination file path
            options: Move operation options

        Returns:
            bool: True if move succeeded
        """
        if options is None:
            options = MoveOptions()

        try:
            src_path = self.platform_handler.normalize_path(src)
            dst_path = self.platform_handler.normalize_path(dst)

            # Validate source
            if not self.file_exists(src_path):
                logger.error(f"Source file does not exist: {src_path}")
                return False

            # Check destination overwrite
            if self.file_exists(dst_path) and not options.overwrite:
                logger.error(f"Destination file exists and overwrite disabled: {dst_path}")
                return False

            # Create backup if requested
            if options.create_backup and self.file_exists(dst_path):
                backup_path = self.platform_handler.join_paths(
                    dst_path.parent, f"{dst_path.stem}.backup{dst_path.suffix}"
                )
                self.copy_file(dst_path, backup_path)

            # Ensure destination directory exists
            self.create_directory(dst_path.parent)

            # Move file
            shutil.move(str(src_path), str(dst_path))

            logger.info(f"Successfully moved {src_path} to {dst_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to move {src} to {dst}: {e}")
            return False

    def delete_file(self, path: Union[str, Path], secure: bool = False) -> bool:
        """
        Delete file with optional secure deletion.

        Args:
            path: File path to delete
            secure: Use secure deletion (overwrite before delete)

        Returns:
            bool: True if deletion succeeded
        """
        try:
            normalized_path = self.platform_handler.normalize_path(path)

            if not self.file_exists(normalized_path):
                return True  # Already doesn't exist

            if secure:
                self._secure_delete(normalized_path)
            else:
                normalized_path.unlink()

            logger.info(f"Successfully deleted {normalized_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete {path}: {e}")
            return False

    def read_text_file(self, path: Union[str, Path], encoding: str = 'utf-8',
                      errors: str = 'replace') -> Optional[str]:
        """
        Read text file with proper encoding handling.

        Args:
            path: File path
            encoding: File encoding
            errors: Encoding error handling strategy

        Returns:
            Optional[str]: File content or None if error
        """
        try:
            normalized_path = self.platform_handler.normalize_path(path)

            with open(normalized_path, 'r', encoding=encoding, errors=errors) as f:
                return f.read()

        except Exception as e:
            logger.error(f"Failed to read text file {path}: {e}")
            return None

    def write_text_file(self, path: Union[str, Path], content: str,
                       encoding: str = 'utf-8', create_dirs: bool = True) -> bool:
        """
        Write text file with proper encoding handling.

        Args:
            path: File path
            content: Content to write
            encoding: File encoding
            create_dirs: Create parent directories if needed

        Returns:
            bool: True if write succeeded
        """
        try:
            normalized_path = self.platform_handler.normalize_path(path)

            if create_dirs:
                self.create_directory(normalized_path.parent)

            with open(normalized_path, 'w', encoding=encoding) as f:
                f.write(content)

            logger.info(f"Successfully wrote text file {normalized_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to write text file {path}: {e}")
            return False

    def read_json_file(self, path: Union[str, Path], encoding: str = 'utf-8') -> Optional[Dict[str, Any]]:
        """
        Read JSON file with proper error handling.

        Args:
            path: File path
            encoding: File encoding

        Returns:
            Optional[Dict]: Parsed JSON or None if error
        """
        try:
            content = self.read_text_file(path, encoding)
            if content is None:
                return None

            return json.loads(content)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON file {path}: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to read JSON file {path}: {e}")
            return None

    def write_json_file(self, path: Union[str, Path], data: Dict[str, Any],
                       encoding: str = 'utf-8', indent: int = 2,
                       create_dirs: bool = True) -> bool:
        """
        Write JSON file with proper formatting.

        Args:
            path: File path
            data: Data to write
            encoding: File encoding
            indent: JSON indentation
            create_dirs: Create parent directories if needed

        Returns:
            bool: True if write succeeded
        """
        try:
            content = json.dumps(data, indent=indent, ensure_ascii=False)
            return self.write_text_file(path, content, encoding, create_dirs)

        except Exception as e:
            logger.error(f"Failed to write JSON file {path}: {e}")
            return False

    def read_csv_file(self, path: Union[str, Path], encoding: str = 'utf-8',
                     **csv_kwargs) -> Optional[List[Dict[str, str]]]:
        """
        Read CSV file with proper error handling.

        Args:
            path: File path
            encoding: File encoding
            **csv_kwargs: Additional arguments for csv.reader

        Returns:
            Optional[List[Dict]]: CSV data as list of dictionaries or None if error
        """
        try:
            normalized_path = self.platform_handler.normalize_path(path)

            with open(normalized_path, 'r', encoding=encoding, newline='') as f:
                reader = csv.DictReader(f, **csv_kwargs)
                return list(reader)

        except Exception as e:
            logger.error(f"Failed to read CSV file {path}: {e}")
            return None

    def write_csv_file(self, path: Union[str, Path], data: List[Dict[str, str]],
                      fieldnames: Optional[List[str]] = None, encoding: str = 'utf-8',
                      **csv_kwargs) -> bool:
        """
        Write CSV file with proper error handling.

        Args:
            path: File path
            data: Data to write
            fieldnames: Column names (inferred from first row if None)
            encoding: File encoding
            **csv_kwargs: Additional arguments for csv.writer

        Returns:
            bool: True if write succeeded
        """
        try:
            if not data:
                return True

            if fieldnames is None:
                fieldnames = list(data[0].keys())

            normalized_path = self.platform_handler.normalize_path(path)
            self.create_directory(normalized_path.parent)

            with open(normalized_path, 'w', encoding=encoding, newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames, **csv_kwargs)
                writer.writeheader()
                writer.writerows(data)

            logger.info(f"Successfully wrote CSV file {normalized_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to write CSV file {path}: {e}")
            return False

    def calculate_file_hash(self, path: Union[str, Path], algorithm: str = 'sha256') -> Optional[str]:
        """
        Calculate file hash for integrity verification.

        Args:
            path: File path
            algorithm: Hash algorithm (md5, sha1, sha256, sha512)

        Returns:
            Optional[str]: File hash or None if error
        """
        try:
            normalized_path = self.platform_handler.normalize_path(path)

            if not self.file_exists(normalized_path):
                return None

            hash_obj = hashlib.new(algorithm)

            with open(normalized_path, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    hash_obj.update(chunk)

            return hash_obj.hexdigest()

        except Exception as e:
            logger.error(f"Failed to calculate hash for {path}: {e}")
            return None

    def find_files(self, directory: Union[str, Path], pattern: str = '*',
                  recursive: bool = True) -> List[Path]:
        """
        Find files matching pattern in directory.

        Args:
            directory: Directory to search
            pattern: Glob pattern to match
            recursive: Search recursively

        Returns:
            List[Path]: List of matching file paths
        """
        try:
            normalized_dir = self.platform_handler.normalize_path(directory)

            if not self.directory_exists(normalized_dir):
                return []

            if recursive:
                matches = list(normalized_dir.rglob(pattern))
            else:
                matches = list(normalized_dir.glob(pattern))

            # Return only files (not directories)
            return [path for path in matches if path.is_file()]

        except Exception as e:
            logger.error(f"Failed to find files in {directory}: {e}")
            return []

    def get_directory_size(self, path: Union[str, Path]) -> int:
        """
        Get total size of directory.

        Args:
            path: Directory path

        Returns:
            int: Total size in bytes
        """
        try:
            normalized_path = self.platform_handler.normalize_path(path)

            if not self.directory_exists(normalized_path):
                return 0

            total_size = 0
            for item in normalized_path.rglob('*'):
                if item.is_file():
                    total_size += item.stat().st_size

            return total_size

        except Exception as e:
            logger.error(f"Failed to get directory size for {path}: {e}")
            return 0

    def clean_directory(self, path: Union[str, Path], keep_hidden: bool = True) -> bool:
        """
        Clean directory contents.

        Args:
            path: Directory path to clean
            keep_hidden: Keep hidden files and directories

        Returns:
            bool: True if cleaning succeeded
        """
        try:
            normalized_path = self.platform_handler.normalize_path(path)

            if not self.directory_exists(normalized_path):
                return True

            for item in normalized_path.iterdir():
                try:
                    # Skip hidden files if requested
                    if keep_hidden and item.name.startswith('.'):
                        continue

                    if item.is_file():
                        item.unlink()
                    elif item.is_dir():
                        shutil.rmtree(str(item))

                except Exception as e:
                    logger.warning(f"Failed to delete {item}: {e}")
                    continue

            logger.info(f"Successfully cleaned directory {normalized_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to clean directory {path}: {e}")
            return False

    @contextmanager
    def temporary_directory(self, prefix: str = 'launcher_'):
        """
        Context manager for temporary directory.

        Args:
            prefix: Prefix for temporary directory name

        Yields:
            Path: Temporary directory path
        """
        temp_dir = None
        try:
            temp_dir = self.platform_handler.get_temp_directory(prefix)
            self.create_directory(temp_dir)
            yield temp_dir
        finally:
            if temp_dir and self.directory_exists(temp_dir):
                try:
                    shutil.rmtree(str(temp_dir))
                except Exception as e:
                    logger.warning(f"Failed to cleanup temporary directory {temp_dir}: {e}")

    def _verify_copy_integrity(self, src: Path, dst: Path) -> bool:
        """Verify copy integrity using file hashes"""
        src_hash = self.calculate_file_hash(src)
        dst_hash = self.calculate_file_hash(dst)

        return src_hash is not None and dst_hash is not None and src_hash == dst_hash

    def _secure_delete(self, path: Path, passes: int = 3) -> None:
        """Securely delete file by overwriting"""
        try:
            file_size = path.stat().st_size

            for pass_num in range(passes):
                # Generate pattern for this pass
                if pass_num % 3 == 0:
                    pattern = b'\x00' * file_size
                elif pass_num % 3 == 1:
                    pattern = b'\xFF' * file_size
                else:
                    import random
                    pattern = bytes(random.getrandbits(8) for _ in range(file_size))

                with open(path, 'r+b') as f:
                    f.write(pattern)
                    f.flush()
                    os.fsync(f.fileno())

            # Final deletion
            path.unlink()

        except Exception as e:
            logger.error(f"Failed to securely delete {path}: {e}")
            # Fallback to regular deletion
            try:
                path.unlink()
            except Exception:
                pass


# Global instance for convenience
_file_operations = None

def get_file_operations() -> FileOperations:
    """Get or create file operations instance"""
    global _file_operations
    if _file_operations is None:
        _file_operations = FileOperations()
    return _file_operations


# Convenience functions
def read_text_file(path: Union[str, Path], encoding: str = 'utf-8') -> Optional[str]:
    """Read text file"""
    return get_file_operations().read_text_file(path, encoding)


def write_text_file(path: Union[str, Path], content: str, encoding: str = 'utf-8') -> bool:
    """Write text file"""
    return get_file_operations().write_text_file(path, content, encoding)


def read_json_file(path: Union[str, Path]) -> Optional[Dict[str, Any]]:
    """Read JSON file"""
    return get_file_operations().read_json_file(path)


def write_json_file(path: Union[str, Path], data: Dict[str, Any]) -> bool:
    """Write JSON file"""
    return get_file_operations().write_json_file(path, data)


if __name__ == "__main__":
    # Demo usage
    ops = FileOperations()

    print("=== File Operations Demo ===")

    # Test file info
    current_file = Path(__file__)
    info = ops.get_file_info(current_file)
    if info:
        print(f"File: {info.path}")
        print(f"Size: {info.size} bytes")
        print(f"Readable: {info.is_readable}")
        print(f"Writable: {info.is_writable}")

    # Test temp directory
    with ops.temporary_directory() as temp_dir:
        print(f"Created temp directory: {temp_dir}")

        # Write test file
        test_file = temp_dir / "test.txt"
        ops.write_text_file(test_file, "Hello, World!")

        # Read it back
        content = ops.read_text_file(test_file)
        print(f"File content: {content}")

    print("Temporary directory cleaned up")