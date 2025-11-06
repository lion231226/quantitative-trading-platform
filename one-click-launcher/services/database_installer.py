"""
Database Installation Management Module

This module provides comprehensive database installation capabilities including
local and Docker-based installation methods, progress tracking, and error handling.
"""

import os
import sys
import subprocess
import platform
import re
import json
import time
import shutil
import urllib.request
import zipfile
import tarfile
from typing import Dict, List, Optional, Tuple, Union, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import threading

from utils.logger import get_logger
from utils.progress_tracker import ProgressTracker
from core.operating_system_detector import OperatingSystem, Architecture, OperatingSystemDetector
from core.database_configurator import (
    DatabaseConfiguration, DatabaseType, ConfigurationMode,
    DatabaseConfigurator, SecurityConfig
)
from services.redis_service_manager import RedisServiceManager
from services.postgresql_service_manager import PostgreSQLServiceManager
from services.docker_manager import DockerManager, DockerContainerConfig

logger = get_logger(__name__)


class InstallationMethod(Enum):
    """Database installation methods"""
    LOCAL = "local"
    DOCKER = "docker"
    HYBRID = "hybrid"
    EXTERNAL = "external"


class InstallationStatus(Enum):
    """Installation status values"""
    PENDING = "pending"
    DOWNLOADING = "downloading"
    EXTRACTING = "extracting"
    CONFIGURING = "configuring"
    INSTALLING = "installing"
    STARTING = "starting"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class InstallationProgress:
    """Installation progress information"""
    status: InstallationStatus
    progress_percentage: float = 0.0
    current_step: str = ""
    total_steps: int = 0
    completed_steps: int = 0
    error_message: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    elapsed_time: float = 0.0
    estimated_remaining_time: float = 0.0

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        result = asdict(self)
        result['status'] = self.status.value
        return result


@dataclass
class InstallationOptions:
    """Database installation options"""
    database_type: DatabaseType
    installation_method: InstallationMethod
    version: Optional[str] = None
    install_directory: Optional[str] = None
    data_directory: Optional[str] = None
    config_directory: Optional[str] = None
    auto_start: bool = True
    create_service: bool = True
    security_config: Optional[SecurityConfig] = None
    additional_config: Optional[Dict[str, Any]] = None
    docker_image: Optional[str] = None
    skip_download: bool = False
    force_reinstall: bool = False

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        result = asdict(self)
        result['database_type'] = self.database_type.value
        result['installation_method'] = self.installation_method.value
        return result


@dataclass
class InstallationResult:
    """Database installation result"""
    success: bool
    database_type: DatabaseType
    installation_method: InstallationMethod
    installed_version: Optional[str] = None
    install_path: Optional[str] = None
    config_path: Optional[str] = None
    service_name: Optional[str] = None
    connection_info: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    installation_time: float = 0.0
    warnings: List[str] = None

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        result = asdict(self)
        result['database_type'] = self.database_type.value
        result['installation_method'] = self.installation_method.value
        return result


class DatabaseInstaller:
    """
    Comprehensive database installation manager.

    Features:
    - Local database installation (Redis, PostgreSQL)
    - Docker-based database installation
    - Installation method selection interface
    - Progress tracking and status reporting
    - Error handling and recovery
    - Cross-platform installation support
    - Installation verification and validation
    """

    # Database download URLs and versions
    DATABASE_DOWNLOADS = {
        DatabaseType.REDIS: {
            'windows': {
                '7.2': 'https://github.com/microsoftarchive/redis/releases/download/win-3.0.504/Redis-x64-3.0.504.msi',
                'latest': 'https://github.com/microsoftarchive/redis/releases/download/win-3.0.504/Redis-x64-3.0.504.msi'
            },
            'macos': {
                '7.2': 'brew install redis',  # Use Homebrew
                'latest': 'brew install redis'
            },
            'linux': {
                '7.2': 'http://download.redis.io/releases/redis-7.2.3.tar.gz',
                'latest': 'http://download.redis.io/releases/redis-7.2.3.tar.gz'
            }
        },
        DatabaseType.POSTGRESQL: {
            'windows': {
                '15': 'https://get.enterprisedb.com/postgresql/postgresql-15.4-1-windows-x64.exe',
                '14': 'https://get.enterprisedb.com/postgresql/postgresql-14.9-1-windows-x64.exe',
                'latest': 'https://get.enterprisedb.com/postgresql/postgresql-15.4-1-windows-x64.exe'
            },
            'macos': {
                '15': 'brew install postgresql@15',
                '14': 'brew install postgresql@14',
                'latest': 'brew install postgresql'
            },
            'linux': {
                '15': 'https://ftp.postgresql.org/pub/source/v15.4/postgresql-15.4.tar.gz',
                '14': 'https://ftp.postgresql.org/pub/source/v14.9/postgresql-14.9.tar.gz',
                'latest': 'https://ftp.postgresql.org/pub/source/v15.4/postgresql-15.4.tar.gz'
            }
        }
    }

    # Default installation directories
    DEFAULT_INSTALL_DIRS = {
        OperatingSystem.WINDOWS: {
            DatabaseType.REDIS: "C:\\Redis",
            DatabaseType.POSTGRESQL: "C:\\Program Files\\PostgreSQL"
        },
        OperatingSystem.MACOS: {
            DatabaseType.REDIS: "/usr/local/opt/redis",
            DatabaseType.POSTGRESQL: "/usr/local/opt/postgresql"
        },
        OperatingSystem.LINUX: {
            DatabaseType.REDIS: "/opt/redis",
            DatabaseType.POSTGRESQL: "/opt/postgresql"
        }
    }

    def __init__(self, progress_callback: Optional[Callable[[InstallationProgress], None]] = None):
        """Initialize Database Installer"""
        self.os_detector = OperatingSystemDetector()
        self.system_info = self.os_detector.detect_os()

        # Initialize service managers
        self.redis_manager = RedisServiceManager()
        self.postgresql_manager = PostgreSQLServiceManager()
        self.docker_manager = DockerManager()
        self.configurator = DatabaseConfigurator()

        # Progress tracking
        self.progress_tracker = ProgressTracker("Database Installer")
        self.progress_callback = progress_callback
        self.current_progress = InstallationProgress(status=InstallationStatus.PENDING)

        # Installation tracking
        self.active_installations = {}
        self.installation_threads = {}

        logger.info(f"DatabaseInstaller initialized for {self.system_info.os_type.value}")

    def get_available_installation_methods(self, database_type: DatabaseType) -> List[InstallationMethod]:
        """
        Get available installation methods for a database type.

        Args:
            database_type: Type of database

        Returns:
            List[InstallationMethod]: Available installation methods
        """
        methods = []

        # Check Docker availability
        docker_info = self.docker_manager.detect_docker_environment()
        if docker_info.status.value in ["running", "stopped"]:
            methods.append(InstallationMethod.DOCKER)

        # Check local installation possibility
        if self._can_install_locally(database_type):
            methods.append(InstallationMethod.LOCAL)

        # Hybrid mode
        if len(methods) >= 2:
            methods.append(InstallationMethod.HYBRID)

        # External (existing installation)
        methods.append(InstallationMethod.EXTERNAL)

        return methods

    def select_installation_method(self, database_type: DatabaseType) -> Tuple[InstallationMethod, str]:
        """
        Present installation method selection interface.

        Args:
            database_type: Type of database

        Returns:
            Tuple[InstallationMethod, str]: (selected_method, reasoning)
        """
        available_methods = self.get_available_installation_methods(database_type)

        # Check for existing installation
        existing_installation = self._check_existing_installation(database_type)

        if existing_installation:
            logger.info(f"Found existing {database_type.value} installation")
            return InstallationMethod.EXTERNAL, "Using existing installation"

        # Prioritize Docker if available
        if InstallationMethod.DOCKER in available_methods:
            docker_info = self.docker_manager.detect_docker_environment()
            if docker_info.status.value == "running":
                return InstallationMethod.DOCKER, "Docker is running and available"

        # Use local installation as fallback
        if InstallationMethod.LOCAL in available_methods:
            return InstallationMethod.LOCAL, "Local installation selected as preferred method"

        # Default to Docker if available
        if InstallationMethod.DOCKER in available_methods:
            return InstallationMethod.DOCKER, "Docker installation selected"

        raise RuntimeError(f"No installation methods available for {database_type.value}")

    def install_database(self, options: InstallationOptions) -> InstallationResult:
        """
        Install database with specified options.

        Args:
            options: Installation options

        Returns:
            InstallationResult: Installation result
        """
        logger.info(f"Starting {options.database_type.value} installation using {options.installation_method.value}")

        # Initialize progress
        self.current_progress = InstallationProgress(
            status=InstallationStatus.PENDING,
            start_time=time.time()
        )
        self._update_progress()

        try:
            # Validate installation options
            is_valid, errors = self._validate_installation_options(options)
            if not is_valid:
                return InstallationResult(
                    success=False,
                    database_type=options.database_type,
                    installation_method=options.installation_method,
                    error_message=f"Invalid installation options: {', '.join(errors)}"
                )

            # Check for existing installation
            if not options.force_reinstall:
                existing = self._check_existing_installation(options.database_type)
                if existing and options.installation_method != InstallationMethod.EXTERNAL:
                    logger.info(f"Existing installation found: {existing}")
                    return InstallationResult(
                        success=True,
                        database_type=options.database_type,
                        installation_method=InstallationMethod.EXTERNAL,
                        installed_version=existing.get('version'),
                        install_path=existing.get('path'),
                        connection_info=existing.get('connection_info'),
                        warnings=["Using existing installation"]
                    )

            # Perform installation based on method
            start_time = time.time()

            if options.installation_method == InstallationMethod.LOCAL:
                result = self._install_local_database(options)
            elif options.installation_method == InstallationMethod.DOCKER:
                result = self._install_docker_database(options)
            elif options.installation_method == InstallationMethod.HYBRID:
                result = self._install_hybrid_database(options)
            elif options.installation_method == InstallationMethod.EXTERNAL:
                result = self._configure_external_database(options)
            else:
                raise ValueError(f"Unsupported installation method: {options.installation_method}")

            # Calculate installation time
            result.installation_time = time.time() - start_time

            # Final progress update
            self.current_progress.status = InstallationStatus.COMPLETED if result.success else InstallationStatus.FAILED
            self.current_progress.progress_percentage = 100.0 if result.success else 0.0
            self.current_progress.end_time = time.time()
            self.current_progress.elapsed_time = self.current_progress.end_time - self.current_progress.start_time
            self._update_progress()

            logger.info(f"Installation completed: {result.success}")
            return result

        except Exception as e:
            error_msg = f"Installation failed: {str(e)}"
            logger.error(error_msg)

            self.current_progress.status = InstallationStatus.FAILED
            self.current_progress.error_message = error_msg
            self.current_progress.end_time = time.time()
            self.current_progress.elapsed_time = self.current_progress.end_time - self.current_progress.start_time
            self._update_progress()

            return InstallationResult(
                success=False,
                database_type=options.database_type,
                installation_method=options.installation_method,
                error_message=error_msg,
                installation_time=time.time() - (self.current_progress.start_time or time.time())
            )

    def _install_local_database(self, options: InstallationOptions) -> InstallationResult:
        """Install database locally"""
        logger.info(f"Installing {options.database_type.value} locally")

        try:
            # Set installation directory
            if not options.install_directory:
                default_dirs = self.DEFAULT_INSTALL_DIRS.get(self.system_info.os_type, {})
                options.install_directory = default_dirs.get(options.database_type, f"/opt/{options.database_type.value}")

            # Progress steps
            steps = [
                ("Preparing installation", 10),
                ("Downloading database", 30),
                ("Extracting files", 20),
                ("Configuring database", 15),
                ("Installing database", 15),
                ("Starting service", 10)
            ]

            self._set_progress_steps(steps)

            # Step 1: Preparing installation
            self._update_step_progress("Preparing installation")
            os.makedirs(options.install_directory, exist_ok=True)

            # Step 2: Download database
            if not options.skip_download:
                self._update_step_progress("Downloading database")
                download_path = self._download_database(options)
            else:
                download_path = None

            # Step 3: Extract files
            self._update_step_progress("Extracting files")
            if download_path and (download_path.endswith('.zip') or download_path.endswith('.tar.gz')):
                self._extract_database(download_path, options.install_directory)

            # Step 4: Configure database
            self._update_step_progress("Configuring database")
            config_result = self._configure_local_database(options)

            # Step 5: Install database
            self._update_step_progress("Installing database")
            install_result = self._perform_local_installation(options)

            # Step 6: Start service
            if options.auto_start:
                self._update_step_progress("Starting service")
                start_result = self._start_local_service(options)
            else:
                start_result = True

            # Verify installation
            if start_result:
                verification_result = self._verify_local_installation(options)
            else:
                verification_result = None

            return InstallationResult(
                success=install_result and start_result,
                database_type=options.database_type,
                installation_method=InstallationMethod.LOCAL,
                installed_version=options.version or "latest",
                install_path=options.install_directory,
                config_path=config_result.get('config_path'),
                service_name=config_result.get('service_name'),
                connection_info=verification_result
            )

        except Exception as e:
            logger.error(f"Local installation failed: {e}")
            return InstallationResult(
                success=False,
                database_type=options.database_type,
                installation_method=InstallationMethod.LOCAL,
                error_message=str(e)
            )

    def _install_docker_database(self, options: InstallationOptions) -> InstallationResult:
        """Install database using Docker"""
        logger.info(f"Installing {options.database_type.value} using Docker")

        try:
            # Progress steps
            steps = [
                ("Checking Docker environment", 10),
                ("Pulling Docker image", 40),
                ("Creating Docker volumes", 15),
                ("Configuring container", 15),
                ("Starting container", 15),
                ("Verifying installation", 5)
            ]

            self._set_progress_steps(steps)

            # Step 1: Check Docker environment
            self._update_step_progress("Checking Docker environment")
            docker_info = self.docker_manager.detect_docker_environment()
            if docker_info.status.value not in ["running"]:
                raise RuntimeError("Docker is not running")

            # Step 2: Pull Docker image
            self._update_step_progress("Pulling Docker image")
            image_name = options.docker_image or self._get_default_docker_image(options.database_type)
            self._pull_docker_image(image_name)

            # Step 3: Create Docker volumes
            self._update_step_progress("Creating Docker volumes")
            data_volume = self._create_docker_volume(options)

            # Step 4: Configure container
            self._update_step_progress("Configuring container")
            container_config = self._create_docker_container_config(options, data_volume)

            # Step 5: Start container
            self._update_step_progress("Starting container")
            if options.database_type == DatabaseType.REDIS:
                success, message = self.docker_manager.create_redis_container(container_config)
            elif options.database_type == DatabaseType.POSTGRESQL:
                success, message = self.docker_manager.create_postgresql_container(container_config)
            else:
                raise ValueError(f"Unsupported database type: {options.database_type}")

            if not success:
                raise RuntimeError(f"Failed to start container: {message}")

            # Step 6: Verify installation
            self._update_step_progress("Verifying installation")
            verification_result = self._verify_docker_installation(options, container_config.name)

            return InstallationResult(
                success=True,
                database_type=options.database_type,
                installation_method=InstallationMethod.DOCKER,
                installed_version=image_name.split(':')[1] if ':' in image_name else "latest",
                install_path=f"Docker container: {container_config.name}",
                connection_info=verification_result
            )

        except Exception as e:
            logger.error(f"Docker installation failed: {e}")
            return InstallationResult(
                success=False,
                database_type=options.database_type,
                installation_method=InstallationMethod.DOCKER,
                error_message=str(e)
            )

    def _install_hybrid_database(self, options: InstallationOptions) -> InstallationResult:
        """Install database using hybrid approach"""
        logger.info(f"Installing {options.database_type.value} using hybrid approach")

        try:
            # For hybrid, we install both local and Docker
            # Local installation for development
            local_options = InstallationOptions(**asdict(options))
            local_options.installation_method = InstallationMethod.LOCAL

            local_result = self._install_local_database(local_options)

            # Docker installation for production/testing
            docker_options = InstallationOptions(**asdict(options))
            docker_options.installation_method = InstallationMethod.DOCKER

            docker_result = self._install_docker_database(docker_options)

            # Combine results
            return InstallationResult(
                success=local_result.success and docker_result.success,
                database_type=options.database_type,
                installation_method=InstallationMethod.HYBRID,
                installed_version=options.version or "latest",
                install_path=f"Local: {local_result.install_path}, Docker: {docker_result.install_path}",
                config_path=local_result.config_path,
                service_name=local_result.service_name,
                connection_info={
                    'local': local_result.connection_info,
                    'docker': docker_result.connection_info
                },
                warnings=local_result.warnings + docker_result.warnings
            )

        except Exception as e:
            logger.error(f"Hybrid installation failed: {e}")
            return InstallationResult(
                success=False,
                database_type=options.database_type,
                installation_method=InstallationMethod.HYBRID,
                error_message=str(e)
            )

    def _configure_external_database(self, options: InstallationOptions) -> InstallationResult:
        """Configure external database installation"""
        logger.info(f"Configuring external {options.database_type.value} installation")

        try:
            # Detect existing installation
            existing = self._check_existing_installation(options.database_type)
            if not existing:
                raise RuntimeError(f"No existing {options.database_type.value} installation found")

            # Create configuration for existing installation
            config = self.configurator.create_database_configuration(
                database_type=options.database_type,
                mode=ConfigurationMode.REMOTE,
                port_mapping=None,  # Will use detected port
                data_directory=options.data_directory or existing.get('data_directory'),
                security_config=options.security_config
            )

            # Test connection
            if options.database_type == DatabaseType.REDIS:
                connection_info = self.redis_manager._test_redis_connection(
                    config.connection_config.host,
                    config.connection_config.port,
                    config.connection_config.password
                )
            elif options.database_type == DatabaseType.POSTGRESQL:
                connection_info = self.postgresql_manager._test_postgresql_connection(
                    config.connection_config.host,
                    config.connection_config.port,
                    config.connection_config.database,
                    config.connection_config.username,
                    config.connection_config.password
                )
            else:
                connection_info = None

            return InstallationResult(
                success=connection_info is not None,
                database_type=options.database_type,
                installation_method=InstallationMethod.EXTERNAL,
                installed_version=existing.get('version'),
                install_path=existing.get('path'),
                config_path=config.config_file,
                connection_info=connection_info.to_dict() if connection_info else None
            )

        except Exception as e:
            logger.error(f"External configuration failed: {e}")
            return InstallationResult(
                success=False,
                database_type=options.database_type,
                installation_method=InstallationMethod.EXTERNAL,
                error_message=str(e)
            )

    def _validate_installation_options(self, options: InstallationOptions) -> Tuple[bool, List[str]]:
        """Validate installation options"""
        errors = []

        if not options.database_type:
            errors.append("Database type is required")

        if not options.installation_method:
            errors.append("Installation method is required")

        # Validate installation method availability
        available_methods = self.get_available_installation_methods(options.database_type)
        if options.installation_method not in available_methods:
            errors.append(f"Installation method {options.installation_method.value} is not available")

        # Validate directories
        if options.install_directory and not os.path.isabs(options.install_directory):
            errors.append("Installation directory must be an absolute path")

        if options.data_directory and not os.path.isabs(options.data_directory):
            errors.append("Data directory must be an absolute path")

        return len(errors) == 0, errors

    def _can_install_locally(self, database_type: DatabaseType) -> bool:
        """Check if local installation is possible"""
        # Check platform support
        if database_type == DatabaseType.REDIS:
            return True  # Redis can be installed on all platforms
        elif database_type == DatabaseType.POSTGRESQL:
            return self.system_info.os_type in [OperatingSystem.WINDOWS, OperatingSystem.MACOS, OperatingSystem.LINUX]
        else:
            return False

    def _check_existing_installation(self, database_type: DatabaseType) -> Optional[Dict[str, Any]]:
        """Check for existing database installation"""
        try:
            if database_type == DatabaseType.REDIS:
                service_info = self.redis_manager.detect_redis_service()
                if service_info.status.value in ["running", "stopped"]:
                    return {
                        'version': service_info.version,
                        'path': service_info.config_file,
                        'port': service_info.port,
                        'connection_info': service_info.to_dict()
                    }
            elif database_type == DatabaseType.POSTGRESQL:
                service_info = self.postgresql_manager.detect_postgresql_service()
                if service_info.status.value in ["running", "stopped"]:
                    return {
                        'version': service_info.version,
                        'path': service_info.config_file,
                        'port': service_info.port,
                        'connection_info': service_info.to_dict()
                    }

        except Exception as e:
            logger.error(f"Error checking existing installation: {e}")

        return None

    def _set_progress_steps(self, steps: List[Tuple[str, int]]):
        """Set progress steps with weights"""
        self.progress_tracker = ProgressTracker("Database Installation Steps")
        for step_name, weight in steps:
            self.progress_tracker.add_step(step_name, weight)

    def _update_step_progress(self, step_name: str):
        """Update progress for current step"""
        self.progress_tracker.update_progress(step_name, "in_progress")
        self.current_progress.current_step = step_name
        self.current_progress.progress_percentage = self.progress_tracker.get_progress_percentage()
        self.current_progress.completed_steps = self.progress_tracker.get_completed_steps()
        self.current_progress.total_steps = self.progress_tracker.get_total_steps()
        self._update_progress()

    def _update_progress(self):
        """Update progress and call callback if provided"""
        if self.progress_callback:
            try:
                self.progress_callback(self.current_progress)
            except Exception as e:
                logger.error(f"Error in progress callback: {e}")

    def _download_database(self, options: InstallationOptions) -> str:
        """Download database software"""
        downloads = self.DATABASE_DOWNLOADS.get(options.database_type, {})
        platform_downloads = downloads.get(self.system_info.os_type.value, {})

        version = options.version or "latest"
        download_url = platform_downloads.get(version)

        if not download_url:
            raise ValueError(f"No download URL found for {options.database_type.value} {version} on {self.system_info.os_type.value}")

        # Handle special cases like brew install
        if download_url.startswith("brew "):
            return self._install_with_brew(download_url)

        # Download file
        filename = download_url.split('/')[-1]
        download_path = os.path.join(options.install_directory, filename)

        logger.info(f"Downloading {options.database_type.value} from {download_url}")
        urllib.request.urlretrieve(download_url, download_path)

        return download_path

    def _install_with_brew(self, command: str) -> str:
        """Install using Homebrew"""
        logger.info(f"Installing with Homebrew: {command}")
        result = subprocess.run(command.split(), capture_output=True, text=True, check=True)
        return "brew_installation"

    def _extract_database(self, archive_path: str, extract_path: str):
        """Extract database archive"""
        logger.info(f"Extracting {archive_path} to {extract_path}")

        if archive_path.endswith('.zip'):
            with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                zip_ref.extractall(extract_path)
        elif archive_path.endswith('.tar.gz') or archive_path.endswith('.tgz'):
            with tarfile.open(archive_path, 'r:gz') as tar_ref:
                tar_ref.extractall(extract_path)
        else:
            raise ValueError(f"Unsupported archive format: {archive_path}")

    def _configure_local_database(self, options: InstallationOptions) -> Dict[str, str]:
        """Configure local database installation"""
        # Create configuration using DatabaseConfigurator
        data_directory = options.data_directory or os.path.join(options.install_directory, "data")
        os.makedirs(data_directory, exist_ok=True)

        # This is a simplified version - in real implementation,
        # we would use the DatabaseConfigurator more extensively
        config_path = os.path.join(options.install_directory, f"{options.database_type.value}.conf")

        return {
            'config_path': config_path,
            'data_directory': data_directory
        }

    def _perform_local_installation(self, options: InstallationOptions) -> bool:
        """Perform the actual local installation"""
        # This is a simplified version - real implementation would
        # handle platform-specific installation procedures
        logger.info(f"Performing local installation of {options.database_type.value}")
        return True

    def _start_local_service(self, options: InstallationOptions) -> bool:
        """Start local database service"""
        try:
            if options.database_type == DatabaseType.REDIS:
                success, message = self.redis_manager.start_redis_service()
            elif options.database_type == DatabaseType.POSTGRESQL:
                success, message = self.postgresql_manager.start_postgresql_service()
            else:
                return False

            return success
        except Exception as e:
            logger.error(f"Error starting local service: {e}")
            return False

    def _verify_local_installation(self, options: InstallationOptions) -> Optional[Dict[str, Any]]:
        """Verify local installation"""
        try:
            if options.database_type == DatabaseType.REDIS:
                service_info = self.redis_manager.detect_redis_service()
                return service_info.to_dict() if service_info else None
            elif options.database_type == DatabaseType.POSTGRESQL:
                service_info = self.postgresql_manager.detect_postgresql_service()
                return service_info.to_dict() if service_info else None
        except Exception as e:
            logger.error(f"Error verifying local installation: {e}")

        return None

    def _get_default_docker_image(self, database_type: DatabaseType) -> str:
        """Get default Docker image for database type"""
        if database_type == DatabaseType.REDIS:
            return "redis:latest"
        elif database_type == DatabaseType.POSTGRESQL:
            return "postgres:latest"
        else:
            return f"{database_type.value}:latest"

    def _pull_docker_image(self, image_name: str):
        """Pull Docker image"""
        logger.info(f"Pulling Docker image: {image_name}")
        result = subprocess.run(['docker', 'pull', image_name], capture_output=True, text=True, check=True, timeout=300)

    def _create_docker_volume(self, options: InstallationOptions) -> str:
        """Create Docker volume for database data"""
        volume_name = f"{options.database_type.value}_data"

        volume_config = {
            'name': volume_name,
            'driver': 'local',
            'labels': {
                'created_by': 'one_click_launcher',
                'database': options.database_type.value
            }
        }

        success, message = self.docker_manager.create_volume(volume_config)
        if not success:
            raise RuntimeError(f"Failed to create Docker volume: {message}")

        return volume_name

    def _create_docker_container_config(self, options: InstallationOptions, volume_name: str) -> DockerContainerConfig:
        """Create Docker container configuration"""
        container_name = f"{options.database_type.value}_launcher"

        # Default port mapping
        default_ports = {
            DatabaseType.REDIS: {6379: 6379},
            DatabaseType.POSTGRESQL: {5432: 5432}
        }

        ports = default_ports.get(options.database_type, {})

        # Environment variables
        environment = {}
        if options.database_type == DatabaseType.POSTGRESQL:
            environment.update({
                'POSTGRES_DB': 'postgres',
                'POSTGRES_USER': 'postgres',
                'POSTGRES_PASSWORD': options.security_config and 'password' or 'postgres'
            })

        # Additional config
        if options.additional_config and 'environment' in options.additional_config:
            environment.update(options.additional_config['environment'])

        return DockerContainerConfig(
            image=options.docker_image or self._get_default_docker_image(options.database_type),
            name=container_name,
            ports=ports,
            environment=environment,
            volumes={volume_name: self._get_container_data_path(options.database_type)},
            restart_policy="unless-stopped",
            detach=True
        )

    def _get_container_data_path(self, database_type: DatabaseType) -> str:
        """Get data path inside container"""
        if database_type == DatabaseType.REDIS:
            return "/data"
        elif database_type == DatabaseType.POSTGRESQL:
            return "/var/lib/postgresql/data"
        else:
            return "/data"

    def _verify_docker_installation(self, options: InstallationOptions, container_name: str) -> Optional[Dict[str, Any]]:
        """Verify Docker installation"""
        try:
            # Wait for container to start
            time.sleep(5)

            # Check container status
            result = subprocess.run(['docker', 'ps', '--filter', f'name={container_name}', '--format', 'json'],
                                  capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                containers = result.stdout.strip().split('\n')
                if containers and containers[0]:
                    container_info = json.loads(containers[0])
                    return {
                        'container_id': container_info.get('ID'),
                        'name': container_info.get('Names'),
                        'status': container_info.get('Status'),
                        'ports': container_info.get('Ports')
                    }

        except Exception as e:
            logger.error(f"Error verifying Docker installation: {e}")

        return None

    def cancel_installation(self, database_type: DatabaseType) -> bool:
        """Cancel ongoing installation"""
        # Implementation for cancellation logic
        logger.info(f"Cancelling {database_type.value} installation")
        return True

    def get_installation_progress(self, database_type: DatabaseType) -> Optional[InstallationProgress]:
        """Get current installation progress"""
        return self.current_progress if self.current_progress else None