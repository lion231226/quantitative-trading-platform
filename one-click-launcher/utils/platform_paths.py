"""
Platform-specific path handling and file operations abstraction.

This module provides cross-platform compatibility for path operations,
file system interactions, and platform-specific behaviors.
"""

import os
import sys
import stat
import shutil
import tempfile
from pathlib import Path, PurePath, PureWindowsPath, PurePosixPath
from typing import Union, List, Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum
import mimetypes

# File utilities will be implemented directly to avoid encoding issues
def ensure_dir(path: str) -> bool:
    """Create directory if it doesn't exist"""
    try:
        Path(path).mkdir(parents=True, exist_ok=True)
        return True
    except Exception:
        return False

def file_exists(path: str) -> bool:
    """Check if file exists"""
    return Path(path).exists() and Path(path).is_file()


class Platform(Enum):
    """Supported platforms"""
    WINDOWS = "windows"
    POSIX = "posix"  # macOS, Linux, Unix


@dataclass
class PathConfig:
    """Platform-specific path configuration"""
    path_separator: str
    executable_extension: str
    script_extension: str
    library_extension: str
    config_dirs: List[str]
    data_dirs: List[str]
    temp_dir: str
    home_dir: str
    case_sensitive: bool
    max_path_length: int


class PlatformPathHandler:
    """
    Cross-platform path handling and file operations.

    Provides unified interface for path operations across different platforms
    while respecting platform-specific behaviors and limitations.
    """

    def __init__(self):
        self.platform = self._detect_platform()
        self.config = self._get_platform_config()

    def _detect_platform(self) -> Platform:
        """Detect the current platform"""
        if os.name == 'nt':
            return Platform.WINDOWS
        else:
            return Platform.POSIX

    def _get_platform_config(self) -> PathConfig:
        """Get platform-specific configuration"""
        if self.platform == Platform.WINDOWS:
            return PathConfig(
                path_separator='\\',
                executable_extension='.exe',
                script_extension='.bat',
                library_extension='.dll',
                config_dirs=[os.environ.get('APPDATA', ''),
                           os.environ.get('LOCALAPPDATA', '')],
                data_dirs=[os.environ.get('PROGRAMDATA', '')],
                temp_dir=tempfile.gettempdir(),
                home_dir=os.path.expanduser('~'),
                case_sensitive=False,
                max_path_length=260  # Windows MAX_PATH limitation
            )
        else:  # POSIX
            return PathConfig(
                path_separator='/',
                executable_extension='',
                script_extension='.sh',
                library_extension='.so' if sys.platform != 'darwin' else '.dylib',
                config_dirs=[os.path.expanduser('~/.config'), '/etc'],
                data_dirs=[os.path.expanduser('~/.local/share'), '/usr/local/share'],
                temp_dir=tempfile.gettempdir(),
                home_dir=os.path.expanduser('~'),
                case_sensitive=True,
                max_path_length=4096
            )

    def normalize_path(self, path: Union[str, Path]) -> Path:
        """
        Normalize path for the current platform.

        Args:
            path: Path to normalize

        Returns:
            Path: Platform-normalized path
        """
        if isinstance(path, str):
            path = Path(path)

        # Convert to appropriate path type
        if self.platform == Platform.WINDOWS:
            # Ensure Windows-style paths
            if not isinstance(path, PureWindowsPath):
                path = Path(path)
        else:
            # Ensure POSIX-style paths
            if isinstance(path, PureWindowsPath):
                path = Path(str(path).replace('\\', '/'))

        return path.resolve()

    def join_paths(self, *paths: Union[str, Path]) -> Path:
        """
        Join multiple path components using platform-appropriate separator.

        Args:
            *paths: Path components to join

        Returns:
            Path: Joined path
        """
        normalized_paths = [self.normalize_path(p) for p in paths]
        return Path(*normalized_paths)

    def get_executable_path(self, base_name: str) -> Path:
        """
        Get executable path with platform-appropriate extension.

        Args:
            base_name: Base name of the executable

        Returns:
            Path: Executable path with extension
        """
        executable = base_name + self.config.executable_extension
        return self.normalize_path(executable)

    def get_script_path(self, base_name: str) -> Path:
        """
        Get script path with platform-appropriate extension.

        Args:
            base_name: Base name of the script

        Returns:
            Path: Script path with extension
        """
        script = base_name + self.config.script_extension
        return self.normalize_path(script)

    def get_library_path(self, base_name: str) -> Path:
        """
        Get library path with platform-appropriate extension.

        Args:
            base_name: Base name of the library

        Returns:
            Path: Library path with extension
        """
        library = base_name + self.config.library_extension
        return self.normalize_path(library)

    def find_executable(self, name: str) -> Optional[Path]:
        """
        Find executable in system PATH.

        Args:
            name: Executable name (with or without extension)

        Returns:
            Optional[Path]: Path to executable if found
        """
        # Add platform extension if not provided
        if not name.endswith(self.config.executable_extension):
            name = self.get_executable_path(name).name

        # Search in PATH
        path_dirs = os.environ.get('PATH', '').split(os.pathsep)

        for path_dir in path_dirs:
            if path_dir:
                executable_path = self.join_paths(path_dir, name)
                if file_exists(str(executable_path)) and os.access(str(executable_path), os.X_OK):
                    return executable_path

        return None

    def get_temp_directory(self, prefix: str = 'launcher_') -> Path:
        """
        Get a temporary directory for the current platform.

        Args:
            prefix: Prefix for temporary directory name

        Returns:
            Path: Temporary directory path
        """
        import uuid
        temp_name = f"{prefix}{uuid.uuid4().hex[:8]}"
        return self.normalize_path(Path(self.config.temp_dir) / temp_name)

    def get_config_directory(self, app_name: str = 'launcher') -> Path:
        """
        Get platform-appropriate configuration directory.

        Args:
            app_name: Application name

        Returns:
            Path: Configuration directory path
        """
        if self.platform == Platform.WINDOWS:
            config_dir = self.join_paths(self.config.config_dirs[0], app_name)
        else:  # POSIX
            config_dir = self.join_paths(self.config.config_dirs[0], app_name)

        # Ensure directory exists
        ensure_dir(str(config_dir))
        return config_dir

    def get_data_directory(self, app_name: str = 'launcher') -> Path:
        """
        Get platform-appropriate data directory.

        Args:
            app_name: Application name

        Returns:
            Path: Data directory path
        """
        if self.platform == Platform.WINDOWS:
            data_dir = self.join_paths(self.config.config_dirs[1], app_name)
        else:  # POSIX
            data_dir = self.join_paths(self.config.data_dirs[0], app_name)

        # Ensure directory exists
        ensure_dir(str(data_dir))
        return data_dir

    def is_case_sensitive(self) -> bool:
        """Check if the filesystem is case-sensitive"""
        return self.config.case_sensitive

    def validate_path_length(self, path: Union[str, Path]) -> bool:
        """
        Validate that path doesn't exceed platform limits.

        Args:
            path: Path to validate

        Returns:
            bool: True if path is valid length
        """
        path_str = str(path)
        return len(path_str) <= self.config.max_path_length

    def get_relative_path(self, path: Union[str, Path], base: Union[str, Path]) -> Path:
        """
        Get relative path from base to path.

        Args:
            path: Target path
            base: Base path

        Returns:
            Path: Relative path
        """
        path_abs = self.normalize_path(path).absolute()
        base_abs = self.normalize_path(base).absolute()

        try:
            return path_abs.relative_to(base_abs)
        except ValueError:
            # Path is not relative to base, return absolute path
            return path_abs

    def copy_file(self, src: Union[str, Path], dst: Union[str, Path],
                  preserve_metadata: bool = True) -> bool:
        """
        Copy file with platform-specific handling.

        Args:
            src: Source path
            dst: Destination path
            preserve_metadata: Whether to preserve file metadata

        Returns:
            bool: True if copy succeeded
        """
        try:
            src_path = self.normalize_path(src)
            dst_path = self.normalize_path(dst)

            # Ensure destination directory exists
            ensure_dir(str(dst_path.parent))

            if preserve_metadata:
                shutil.copy2(str(src_path), str(dst_path))
            else:
                shutil.copy(str(src_path), str(dst_path))

            return True

        except Exception as e:
            print(f"Failed to copy {src} to {dst}: {e}")
            return False

    def move_file(self, src: Union[str, Path], dst: Union[str, Path]) -> bool:
        """
        Move file with platform-specific handling.

        Args:
            src: Source path
            dst: Destination path

        Returns:
            bool: True if move succeeded
        """
        try:
            src_path = self.normalize_path(src)
            dst_path = self.normalize_path(dst)

            # Ensure destination directory exists
            ensure_dir(str(dst_path.parent))

            shutil.move(str(src_path), str(dst_path))
            return True

        except Exception as e:
            print(f"Failed to move {src} to {dst}: {e}")
            return False

    def make_executable(self, path: Union[str, Path]) -> bool:
        """
        Make file executable (POSIX only).

        Args:
            path: Path to file

        Returns:
            bool: True if succeeded or not needed
        """
        if self.platform == Platform.WINDOWS:
            return True  # Not applicable on Windows

        try:
            path_str = str(self.normalize_path(path))
            st = os.stat(path_str)
            os.chmod(path_str, st.st_mode | stat.S_IEXEC)
            return True

        except Exception as e:
            print(f"Failed to make {path} executable: {e}")
            return False

    def get_file_type(self, path: Union[str, Path]) -> str:
        """
        Get file type using platform-appropriate methods.

        Args:
            path: Path to file

        Returns:
            str: File MIME type or generic description
        """
        try:
            path_str = str(self.normalize_path(path))
            mime_type, _ = mimetypes.guess_type(path_str)

            if mime_type:
                return mime_type

            # Fallback to extension-based detection
            ext = Path(path_str).suffix.lower()
            extension_map = {
                '.exe': 'application/x-executable',
                '.bat': 'application/x-bat',
                '.sh': 'application/x-sh',
                '.py': 'text/x-python',
                '.js': 'application/javascript',
                '.json': 'application/json',
                '.yaml': 'application/x-yaml',
                '.yml': 'application/x-yaml',
                '.md': 'text/markdown',
                '.txt': 'text/plain',
            }

            return extension_map.get(ext, 'application/octet-stream')

        except Exception:
            return 'application/octet-stream'

    def get_environment_paths(self) -> List[str]:
        """
        Get system PATH environment variable entries.

        Returns:
            List[str]: List of PATH directories
        """
        path_env = os.environ.get('PATH', '')
        return [p for p in path_env.split(os.pathsep) if p]

    def search_in_path(self, pattern: str) -> List[Path]:
        """
        Search for files matching pattern in system PATH.

        Args:
            pattern: File pattern to search for

        Returns:
            List[Path]: List of matching files
        """
        matches = []
        path_dirs = self.get_environment_paths()

        for path_dir in path_dirs:
            try:
                path_abs = self.normalize_path(path_dir)
                if path_abs.exists():
                    for file_path in path_abs.glob(pattern):
                        if file_path.is_file():
                            matches.append(file_path)
            except Exception:
                continue

        return matches

    def get_user_paths(self) -> Dict[str, Path]:
        """
        Get platform-specific user directories.

        Returns:
            Dict[str, Path]: Dictionary of user paths
        """
        user_paths = {
            'home': self.normalize_path(self.config.home_dir),
            'desktop': self.normalize_path(Path(self.config.home_dir) / 'Desktop'),
            'documents': self.normalize_path(Path(self.config.home_dir) / 'Documents'),
            'downloads': self.normalize_path(Path(self.config.home_dir) / 'Downloads'),
        }

        if self.platform == Platform.WINDOWS:
            # Add Windows-specific paths
            user_paths.update({
                'appdata': self.normalize_path(os.environ.get('APPDATA', '')),
                'localappdata': self.normalize_path(os.environ.get('LOCALAPPDATA', '')),
                'program_files': self.normalize_path(os.environ.get('ProgramFiles', 'C:\\Program Files')),
                'program_files_x86': self.normalize_path(os.environ.get('ProgramFiles(x86)', 'C:\\Program Files (x86)')),
            })
        else:  # POSIX
            # Add POSIX-specific paths
            user_paths.update({
                'config': self.normalize_path(Path(self.config.home_dir) / '.config'),
                'local': self.normalize_path(Path(self.config.home_dir) / '.local'),
                'cache': self.normalize_path(Path(self.config.home_dir) / '.cache'),
            })

        return user_paths

    def format_path_string(self, path: Union[str, Path]) -> str:
        """
        Format path string for display in current platform.

        Args:
            path: Path to format

        Returns:
            str: Formatted path string
        """
        normalized = self.normalize_path(path)
        return str(normalized)

    def create_platform_script(self, commands: List[str], output_path: Union[str, Path],
                              shebang: Optional[str] = None) -> bool:
        """
        Create platform-specific script file.

        Args:
            commands: List of commands to include in script
            output_path: Path for the output script
            shebang: Optional shebang line (POSIX only)

        Returns:
            bool: True if script creation succeeded
        """
        try:
            output_path = self.normalize_path(output_path)
            ensure_dir(str(output_path.parent))

            if self.platform == Platform.WINDOWS:
                # Create batch file
                script_content = ['@echo off'] + commands + ['@echo on']
                script_text = '\n'.join(script_content)
            else:  # POSIX
                # Create shell script
                if shebang:
                    script_lines = [shebang] + commands
                else:
                    script_lines = ['#!/bin/bash'] + commands

                script_text = '\n'.join(script_lines)

            # Write script file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(script_text)

            # Make executable on POSIX
            if self.platform == Platform.POSIX:
                self.make_executable(output_path)

            return True

        except Exception as e:
            print(f"Failed to create script at {output_path}: {e}")
            return False


# Global instance for convenience
_platform_handler = None

def get_platform_handler() -> PlatformPathHandler:
    """Get or create platform handler instance"""
    global _platform_handler
    if _platform_handler is None:
        _platform_handler = PlatformPathHandler()
    return _platform_handler


# Convenience functions
def normalize_path(path: Union[str, Path]) -> Path:
    """Normalize path for current platform"""
    return get_platform_handler().normalize_path(path)


def join_paths(*paths: Union[str, Path]) -> Path:
    """Join paths using platform-appropriate separator"""
    return get_platform_handler().join_paths(*paths)


def find_executable(name: str) -> Optional[Path]:
    """Find executable in system PATH"""
    return get_platform_handler().find_executable(name)


def get_config_directory(app_name: str = 'launcher') -> Path:
    """Get configuration directory"""
    return get_platform_handler().get_config_directory(app_name)


def get_data_directory(app_name: str = 'launcher') -> Path:
    """Get data directory"""
    return get_platform_handler().get_data_directory(app_name)


def is_windows() -> bool:
    """Check if running on Windows"""
    return get_platform_handler().platform == Platform.WINDOWS


def is_posix() -> bool:
    """Check if running on POSIX system"""
    return get_platform_handler().platform == Platform.POSIX


if __name__ == "__main__":
    # Demo usage
    handler = PlatformPathHandler()

    print(f"Platform: {handler.platform.value}")
    print(f"Path separator: {handler.config.path_separator}")
    print(f"Executable extension: {handler.config.executable_extension}")
    print(f"Case sensitive: {handler.config.case_sensitive}")

    print("\n=== User Paths ===")
    user_paths = handler.get_user_paths()
    for name, path in user_paths.items():
        print(f"{name}: {path}")

    print("\n=== Executable Search ===")
    python_path = handler.find_executable('python')
    print(f"Python found at: {python_path}")

    print("\n=== Temp Directory ===")
    temp_dir = handler.get_temp_directory()
    print(f"Created temp directory: {temp_dir}")