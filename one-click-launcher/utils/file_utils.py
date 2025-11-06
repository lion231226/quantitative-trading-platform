"""
File utilities module for one-click launcher.

This module provides common file operations used throughout the application.
"""

import os
import shutil
from pathlib import Path
from typing import Optional


def ensure_dir(directory: str) -> bool:
    """
    Ensure that a directory exists, creating it if necessary.

    Args:
        directory: Directory path to ensure exists

    Returns:
        bool: True if directory exists or was created successfully
    """
    try:
        Path(directory).mkdir(parents=True, exist_ok=True)
        return True
    except Exception:
        return False


def read_file_text(file_path: str, encoding: str = 'utf-8') -> Optional[str]:
    """
    Read text content from a file.

    Args:
        file_path: Path to the file to read
        encoding: File encoding (default: utf-8)

    Returns:
        Optional[str]: File content or None if read failed
    """
    try:
        with open(file_path, 'r', encoding=encoding) as f:
            return f.read()
    except Exception:
        return None


def write_file_text(file_path: str, content: str, encoding: str = 'utf-8') -> bool:
    """
    Write text content to a file.

    Args:
        file_path: Path to the file to write
        content: Text content to write
        encoding: File encoding (default: utf-8)

    Returns:
        bool: True if write was successful
    """
    try:
        ensure_dir(os.path.dirname(file_path))
        with open(file_path, 'w', encoding=encoding) as f:
            f.write(content)
        return True
    except Exception:
        return False


def copy_file(source: str, destination: str) -> bool:
    """
    Copy a file from source to destination.

    Args:
        source: Source file path
        destination: Destination file path

    Returns:
        bool: True if copy was successful
    """
    try:
        ensure_dir(os.path.dirname(destination))
        shutil.copy2(source, destination)
        return True
    except Exception:
        return False


def delete_file(file_path: str) -> bool:
    """
    Delete a file if it exists.

    Args:
        file_path: Path to the file to delete

    Returns:
        bool: True if deletion was successful or file didn't exist
    """
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
        return True
    except Exception:
        return False


def file_exists(file_path: str) -> bool:
    """
    Check if a file exists.

    Args:
        file_path: Path to check

    Returns:
        bool: True if file exists
    """
    return os.path.isfile(file_path)


def get_file_size(file_path: str) -> int:
    """
    Get file size in bytes.

    Args:
        file_path: Path to the file

    Returns:
        int: File size in bytes, or 0 if file doesn't exist
    """
    try:
        return os.path.getsize(file_path)
    except Exception:
        return 0