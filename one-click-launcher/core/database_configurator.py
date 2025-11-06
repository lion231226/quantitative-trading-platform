"""
Database Configuration Management Module

This module provides comprehensive database configuration management capabilities
including automatic port detection, secure password generation, data directory configuration,
and configuration file template management.
"""

import os
import sys
import subprocess
import platform
import re
import json
import secrets
import string
import socket
import stat
import tempfile
from typing import Dict, List, Optional, Tuple, Union, Any
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import configparser
import yaml

from utils.logger import get_logger
from utils.config_manager import ConfigManager
from core.operating_system_detector import OperatingSystem, Architecture, OperatingSystemDetector
from services.redis_service_manager import RedisConnectionConfig, RedisServiceManager
from services.postgresql_service_manager import PostgreSQLConnectionConfig, PostgreSQLServiceManager
from services.docker_manager import DockerManager, DockerContainerConfig, DockerVolumeConfig, DockerNetworkConfig

logger = get_logger(__name__)


class DatabaseType(Enum):
    """Supported database types"""
    REDIS = "redis"
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    MONGODB = "mongodb"


class ConfigurationMode(Enum):
    """Database configuration modes"""
    LOCAL = "local"
    DOCKER = "docker"
    REMOTE = "remote"
    HYBRID = "hybrid"


@dataclass
class DatabaseConfiguration:
    """Complete database configuration"""
    database_type: DatabaseType
    mode: ConfigurationMode
    connection_config: Union[RedisConnectionConfig, PostgreSQLConnectionConfig]
    data_directory: Optional[str] = None
    config_file: Optional[str] = None
    log_file: Optional[str] = None
    pid_file: Optional[str] = None
    password: Optional[str] = None
    additional_config: Optional[Dict[str, Any]] = None
    docker_config: Optional[DockerContainerConfig] = None
    volume_config: Optional[DockerVolumeConfig] = None
    network_config: Optional[DockerNetworkConfig] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        result = asdict(self)
        result['database_type'] = self.database_type.value
        result['mode'] = self.mode.value

        # Handle password masking
        if result.get('password'):
            result['password'] = '***'

        # Convert connection config
        if self.connection_config:
            result['connection_config'] = self.connection_config.to_dict()

        # Convert docker configs
        if self.docker_config:
            result['docker_config'] = self.docker_config.to_dict()
        if self.volume_config:
            result['volume_config'] = self.volume_config.to_dict()
        if self.network_config:
            result['network_config'] = self.network_config.to_dict()

        return result


@dataclass
class PortMapping:
    """Port mapping configuration"""
    database_type: DatabaseType
    default_port: int
    actual_port: int
    is_conflict: bool = False
    alternative_ports: List[int] = None

    def __post_init__(self):
        if self.alternative_ports is None:
            self.alternative_ports = []


@dataclass
class SecurityConfig:
    """Security configuration for databases"""
    password_length: int = 32
    password_complexity: bool = True
    use_ssl: bool = False
    ssl_cert_path: Optional[str] = None
    ssl_key_path: Optional[str] = None
    ssl_ca_path: Optional[str] = None
    allowed_hosts: List[str] = None
    authentication_method: str = "password"

    def __post_init__(self):
        if self.allowed_hosts is None:
            self.allowed_hosts = ["localhost", "127.0.0.1"]


class DatabaseConfigurator:
    """
    Comprehensive database configuration management.

    Features:
    - Automatic port detection and conflict resolution
    - Secure password generation and management
    - Data directory configuration and permissions setup
    - Configuration file template generation and management
    - Cross-platform configuration support
    - Docker and local installation configuration
    """

    # Default port ranges for database services
    DEFAULT_PORTS = {
        DatabaseType.REDIS: 6379,
        DatabaseType.POSTGRESQL: 5432,
        DatabaseType.MYSQL: 3306,
        DatabaseType.MONGODB: 27017
    }

    # Port ranges to check for conflicts
    PORT_RANGE_START = 6400
    PORT_RANGE_END = 6500

    # Default data directory paths
    DEFAULT_DATA_PATHS = {
        OperatingSystem.WINDOWS: {
            DatabaseType.REDIS: "C:\\data\\redis",
            DatabaseType.POSTGRESQL: "C:\\data\\postgresql",
            DatabaseType.MYSQL: "C:\\data\\mysql",
            DatabaseType.MONGODB: "C:\\data\\mongodb"
        },
        OperatingSystem.MACOS: {
            DatabaseType.REDIS: "/usr/local/var/redis",
            DatabaseType.POSTGRESQL: "/usr/local/var/postgresql",
            DatabaseType.MYSQL: "/usr/local/var/mysql",
            DatabaseType.MONGODB: "/usr/local/var/mongodb"
        },
        OperatingSystem.LINUX: {
            DatabaseType.REDIS: "/var/lib/redis",
            DatabaseType.POSTGRESQL: "/var/lib/postgresql",
            DatabaseType.MYSQL: "/var/lib/mysql",
            DatabaseType.MONGODB: "/var/lib/mongodb"
        }
    }

    # Configuration file templates
    CONFIG_TEMPLATES = {
        DatabaseType.REDIS: {
            'basic': '''
# Redis configuration file
port {port}
bind {bind_address}
dir {data_directory}
dbfilename dump.rdb
save 900 1
save 300 10
save 60 10000
appendonly yes
appendfilename "appendonly.aof"
''',
            'security': '''
# Redis security configuration
requirepass {password}
protected-mode yes
''',
            'performance': '''
# Redis performance configuration
maxmemory {max_memory}
maxmemory-policy allkeys-lru
tcp-keepalive 300
timeout 0
'''
        },
        DatabaseType.POSTGRESQL: {
            'basic': '''
# PostgreSQL configuration file
listen_addresses = '{bind_address}'
port = {port}
data_directory = '{data_directory}'
hba_file = '{hba_file}'
ident_file = '{ident_file}'
''',
            'connections': '''
# Connection settings
max_connections = {max_connections}
superuser_reserved_connections = 3
authentication_timeout = 1min
''',
            'memory': '''
# Memory settings
shared_buffers = {shared_buffers}
effective_cache_size = {effective_cache_size}
work_mem = 4MB
maintenance_work_mem = 64MB
'''
        }
    }

    def __init__(self, config_manager: Optional[ConfigManager] = None):
        """Initialize Database Configurator"""
        self.os_detector = OperatingSystemDetector()
        self.system_info = self.os_detector.detect_os()
        self.config_manager = config_manager or ConfigManager()

        # Initialize service managers
        self.redis_manager = RedisServiceManager()
        self.postgresql_manager = PostgreSQLServiceManager()
        self.docker_manager = DockerManager()

        # Track used ports
        self.used_ports = set()

        logger.info(f"DatabaseConfigurator initialized for {self.system_info.os_type.value}")

    def detect_available_ports(self, database_types: List[DatabaseType]) -> Dict[DatabaseType, PortMapping]:
        """
        Detect available ports for database services.

        Args:
            database_types: List of database types to check

        Returns:
            Dict[DatabaseType, PortMapping]: Port mappings for each database type
        """
        logger.info("Detecting available ports for database services")

        port_mappings = {}

        for db_type in database_types:
            default_port = self.DEFAULT_PORTS[db_type]

            # Check if default port is available
            is_available = self._is_port_available(default_port)

            if is_available:
                actual_port = default_port
                is_conflict = False
            else:
                # Find alternative port
                actual_port = self._find_available_port()
                is_conflict = True

            # Generate alternative ports
            alternative_ports = self._generate_alternative_ports(default_port, 5)

            port_mapping = PortMapping(
                database_type=db_type,
                default_port=default_port,
                actual_port=actual_port,
                is_conflict=is_conflict,
                alternative_ports=alternative_ports
            )

            port_mappings[db_type] = port_mapping
            self.used_ports.add(actual_port)

        logger.info(f"Port detection completed. Mapped: {[f'{k.value}:{v.actual_port}' for k, v in port_mappings.items()]}")
        return port_mappings

    def generate_secure_password(self, length: int = 32, include_special: bool = True) -> str:
        """
        Generate a secure password for database authentication.

        Args:
            length: Password length
            include_special: Whether to include special characters

        Returns:
            str: Generated secure password
        """
        logger.debug(f"Generating secure password with length {length}")

        # Define character sets
        lowercase = string.ascii_lowercase
        uppercase = string.ascii_uppercase
        digits = string.digits
        special = "!@#$%^&*()_+-=[]{}|;:,.<>?" if include_special else ""

        # Ensure all character types are included
        password_chars = [
            secrets.choice(lowercase),
            secrets.choice(uppercase),
            secrets.choice(digits),
        ]

        if include_special:
            password_chars.append(secrets.choice(special))

        # Fill remaining length with random characters from all sets
        all_chars = lowercase + uppercase + digits + special
        remaining_length = length - len(password_chars)

        for _ in range(remaining_length):
            password_chars.append(secrets.choice(all_chars))

        # Shuffle the password characters
        secrets.SystemRandom().shuffle(password_chars)

        password = ''.join(password_chars)

        logger.debug("Secure password generated successfully")
        return password

    def configure_data_directory(self, database_type: DatabaseType,
                               custom_path: Optional[str] = None,
                               create_if_missing: bool = True) -> str:
        """
        Configure and create data directory for database.

        Args:
            database_type: Type of database
            custom_path: Custom data directory path
            create_if_missing: Whether to create directory if it doesn't exist

        Returns:
            str: Configured data directory path
        """
        logger.info(f"Configuring data directory for {database_type.value}")

        if custom_path:
            data_directory = custom_path
        else:
            default_paths = self.DEFAULT_DATA_PATHS.get(self.system_info.os_type, {})
            data_directory = default_paths.get(database_type, f"/tmp/{database_type.value}_data")

        # Create directory if it doesn't exist
        if create_if_missing and not os.path.exists(data_directory):
            try:
                os.makedirs(data_directory, exist_ok=True)
                logger.info(f"Created data directory: {data_directory}")

                # Set appropriate permissions
                self._set_directory_permissions(data_directory, database_type)

            except Exception as e:
                logger.error(f"Failed to create data directory {data_directory}: {e}")
                # Fallback to temporary directory
                temp_dir = tempfile.mkdtemp(prefix=f"{database_type.value}_")
                data_directory = temp_dir
                logger.warning(f"Using temporary directory: {data_directory}")

        # Validate directory is writable
        if not os.access(data_directory, os.W_OK):
            raise PermissionError(f"Data directory {data_directory} is not writable")

        logger.info(f"Data directory configured: {data_directory}")
        return data_directory

    def create_database_configuration(self, database_type: DatabaseType,
                                    mode: ConfigurationMode,
                                    port_mapping: PortMapping,
                                    data_directory: str,
                                    security_config: Optional[SecurityConfig] = None,
                                    additional_config: Optional[Dict[str, Any]] = None) -> DatabaseConfiguration:
        """
        Create complete database configuration.

        Args:
            database_type: Type of database
            mode: Configuration mode (local, docker, remote, hybrid)
            port_mapping: Port mapping configuration
            data_directory: Data directory path
            security_config: Security configuration
            additional_config: Additional configuration parameters

        Returns:
            DatabaseConfiguration: Complete database configuration
        """
        logger.info(f"Creating {database_type.value} configuration in {mode.value} mode")

        # Generate security config if not provided
        if security_config is None:
            security_config = SecurityConfig()

        # Generate password
        password = self.generate_secure_password(
            security_config.password_length,
            security_config.password_complexity
        )

        # Create connection configuration
        if database_type == DatabaseType.REDIS:
            connection_config = RedisConnectionConfig(
                host="localhost",
                port=port_mapping.actual_port,
                password=password
            )
        elif database_type == DatabaseType.POSTGRESQL:
            connection_config = PostgreSQLConnectionConfig(
                host="localhost",
                port=port_mapping.actual_port,
                database="postgres",
                username="postgres",
                password=password
            )
        else:
            raise ValueError(f"Unsupported database type: {database_type}")

        # Create Docker configuration if needed
        docker_config = None
        volume_config = None
        network_config = None

        if mode in [ConfigurationMode.DOCKER, ConfigurationMode.HYBRID]:
            docker_config = self._create_docker_config(
                database_type, port_mapping, security_config, additional_config
            )

            # Create volume config for persistent data
            volume_config = DockerVolumeConfig(
                name=f"{database_type.value}_data",
                labels={"created_by": "one_click_launcher", "database": database_type.value}
            )

            # Create network config
            network_config = DockerNetworkConfig(
                name=f"{database_type.value}_network",
                labels={"created_by": "one_click_launcher", "database": database_type.value}
            )

        # Create file paths
        config_file = self._generate_config_file_path(database_type, data_directory)
        log_file = self._generate_log_file_path(database_type, data_directory)
        pid_file = self._generate_pid_file_path(database_type, data_directory)

        # Create database configuration
        db_config = DatabaseConfiguration(
            database_type=database_type,
            mode=mode,
            connection_config=connection_config,
            data_directory=data_directory,
            config_file=config_file,
            log_file=log_file,
            pid_file=pid_file,
            password=password,
            additional_config=additional_config or {},
            docker_config=docker_config,
            volume_config=volume_config,
            network_config=network_config
        )

        # Generate configuration file
        self._generate_config_file(db_config, security_config)

        logger.info(f"Database configuration created for {database_type.value}")
        return db_config

    def validate_configuration(self, config: DatabaseConfiguration) -> Tuple[bool, List[str]]:
        """
        Validate database configuration.

        Args:
            config: Database configuration to validate

        Returns:
            Tuple[bool, List[str]]: (is_valid, error_messages)
        """
        errors = []

        # Validate basic configuration
        if not config.data_directory:
            errors.append("Data directory is required")

        if not config.config_file:
            errors.append("Configuration file path is required")

        # Validate data directory
        if config.data_directory:
            if not os.path.exists(config.data_directory):
                errors.append(f"Data directory does not exist: {config.data_directory}")
            elif not os.access(config.data_directory, os.W_OK):
                errors.append(f"Data directory is not writable: {config.data_directory}")

        # Validate connection configuration
        if config.database_type == DatabaseType.REDIS:
            if not isinstance(config.connection_config, RedisConnectionConfig):
                errors.append("Invalid Redis connection configuration")
        elif config.database_type == DatabaseType.POSTGRESQL:
            if not isinstance(config.connection_config, PostgreSQLConnectionConfig):
                errors.append("Invalid PostgreSQL connection configuration")

        # Validate port availability
        if config.connection_config:
            if not self._is_port_available(config.connection_config.port):
                errors.append(f"Port {config.connection_config.port} is not available")

        # Validate Docker configuration if present
        if config.mode in [ConfigurationMode.DOCKER, ConfigurationMode.HYBRID]:
            if not config.docker_config:
                errors.append("Docker configuration is required for Docker mode")

            # Validate Docker environment
            docker_info = self.docker_manager.detect_docker_environment()
            if docker_info.status != "running":
                errors.append("Docker is not running or not available")

        return len(errors) == 0, errors

    def apply_configuration(self, config: DatabaseConfiguration) -> Tuple[bool, str]:
        """
        Apply database configuration.

        Args:
            config: Database configuration to apply

        Returns:
            Tuple[bool, str]: (success, message)
        """
        logger.info(f"Applying configuration for {config.database_type.value}")

        try:
            # Validate configuration first
            is_valid, errors = self.validate_configuration(config)
            if not is_valid:
                error_msg = f"Configuration validation failed: {', '.join(errors)}"
                logger.error(error_msg)
                return False, error_msg

            # Apply configuration based on mode
            if config.mode == ConfigurationMode.LOCAL:
                return self._apply_local_configuration(config)
            elif config.mode == ConfigurationMode.DOCKER:
                return self._apply_docker_configuration(config)
            elif config.mode == ConfigurationMode.HYBRID:
                return self._apply_hybrid_configuration(config)
            else:
                return False, f"Unsupported configuration mode: {config.mode}"

        except Exception as e:
            error_msg = f"Error applying configuration: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def _apply_local_configuration(self, config: DatabaseConfiguration) -> Tuple[bool, str]:
        """Apply local database configuration"""
        try:
            # Configuration file is already generated
            # For local configuration, we mainly need to ensure directories exist
            # and configuration files are in place

            # Create log directory if needed
            log_dir = os.path.dirname(config.log_file)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir, exist_ok=True)

            # Create pid directory if needed
            pid_dir = os.path.dirname(config.pid_file)
            if pid_dir and not os.path.exists(pid_dir):
                os.makedirs(pid_dir, exist_ok=True)

            return True, f"Local configuration applied for {config.database_type.value}"

        except Exception as e:
            return False, f"Error applying local configuration: {str(e)}"

    def _apply_docker_configuration(self, config: DatabaseConfiguration) -> Tuple[bool, str]:
        """Apply Docker database configuration"""
        try:
            # Create Docker network if needed
            if config.network_config:
                success, message = self.docker_manager.create_network(config.network_config)
                if not success:
                    return False, f"Failed to create Docker network: {message}"

            # Create Docker volume if needed
            if config.volume_config:
                success, message = self.docker_manager.create_volume(config.volume_config)
                if not success:
                    return False, f"Failed to create Docker volume: {message}"

            # Update Docker container config with volume and network
            if config.docker_config:
                if config.volume_config:
                    if not config.docker_config.volumes:
                        config.docker_config.volumes = {}
                    config.docker_config.volumes[config.volume_config.name] = self._get_container_data_path(config.database_type)

                if config.network_config and not config.docker_config.networks:
                    config.docker_config.networks = [config.network_config.name]

                # Create/start container
                if config.database_type == DatabaseType.REDIS:
                    success, message = self.docker_manager.create_redis_container(config.docker_config)
                elif config.database_type == DatabaseType.POSTGRESQL:
                    success, message = self.docker_manager.create_postgresql_container(config.docker_config)
                else:
                    return False, f"Unsupported database type for Docker: {config.database_type}"

                if not success:
                    return False, f"Failed to create Docker container: {message}"

            return True, f"Docker configuration applied for {config.database_type.value}"

        except Exception as e:
            return False, f"Error applying Docker configuration: {str(e)}"

    def _apply_hybrid_configuration(self, config: DatabaseConfiguration) -> Tuple[bool, str]:
        """Apply hybrid database configuration"""
        try:
            # Apply local configuration first
            local_success, local_message = self._apply_local_configuration(config)
            if not local_success:
                return False, f"Local configuration failed: {local_message}"

            # Apply Docker configuration if present
            if config.docker_config:
                docker_success, docker_message = self._apply_docker_configuration(config)
                if not docker_success:
                    return False, f"Docker configuration failed: {docker_message}"

            return True, f"Hybrid configuration applied for {config.database_type.value}"

        except Exception as e:
            return False, f"Error applying hybrid configuration: {str(e)}"

    def _is_port_available(self, port: int) -> bool:
        """Check if a port is available"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                result = sock.connect_ex(('localhost', port))
                return result != 0
        except Exception as e:
            logger.error(f"Error checking port {port}: {e}")
            return False

    def _find_available_port(self) -> int:
        """Find an available port within the configured range"""
        for port in range(self.PORT_RANGE_START, self.PORT_RANGE_END):
            if self._is_port_available(port) and port not in self.used_ports:
                return port

        # If no port found in range, find any available port
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(('', 0))
            port = sock.getsockname()[1]
            return port

    def _generate_alternative_ports(self, base_port: int, count: int) -> List[int]:
        """Generate alternative ports"""
        alternatives = []
        current = base_port + 1

        while len(alternatives) < count and current < self.PORT_RANGE_END:
            if self._is_port_available(current):
                alternatives.append(current)
            current += 1

        return alternatives

    def _set_directory_permissions(self, directory: str, database_type: DatabaseType):
        """Set appropriate permissions for database directory"""
        try:
            if self.system_info.os_type == OperatingSystem.LINUX:
                # Set ownership for database directories
                if database_type == DatabaseType.POSTGRESQL:
                    # PostgreSQL typically runs as postgres user
                    try:
                        subprocess.run(['chown', '-R', 'postgres:postgres', directory], check=False)
                        subprocess.run(['chmod', '-R', '700', directory], check=False)
                    except Exception as e:
                        logger.warning(f"Could not set PostgreSQL directory permissions: {e}")
                elif database_type == DatabaseType.REDIS:
                    # Redis typically runs as redis user
                    try:
                        subprocess.run(['chown', '-R', 'redis:redis', directory], check=False)
                        subprocess.run(['chmod', '-R', '755', directory], check=False)
                    except Exception as e:
                        logger.warning(f"Could not set Redis directory permissions: {e}")
                else:
                    # Default permissions
                    os.chmod(directory, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)

        except Exception as e:
            logger.error(f"Error setting directory permissions: {e}")

    def _generate_config_file_path(self, database_type: DatabaseType, data_directory: str) -> str:
        """Generate configuration file path"""
        if database_type == DatabaseType.REDIS:
            return os.path.join(data_directory, "redis.conf")
        elif database_type == DatabaseType.POSTGRESQL:
            return os.path.join(data_directory, "postgresql.conf")
        else:
            return os.path.join(data_directory, f"{database_type.value}.conf")

    def _generate_log_file_path(self, database_type: DatabaseType, data_directory: str) -> str:
        """Generate log file path"""
        return os.path.join(data_directory, f"{database_type.value}.log")

    def _generate_pid_file_path(self, database_type: DatabaseType, data_directory: str) -> str:
        """Generate PID file path"""
        return os.path.join(data_directory, f"{database_type.value}.pid")

    def _create_docker_config(self, database_type: DatabaseType,
                             port_mapping: PortMapping,
                             security_config: SecurityConfig,
                             additional_config: Optional[Dict[str, Any]]) -> DockerContainerConfig:
        """Create Docker container configuration"""
        container_name = f"{database_type.value}_container"

        # Map ports
        ports = {}
        if database_type == DatabaseType.REDIS:
            ports[6379] = port_mapping.actual_port
        elif database_type == DatabaseType.POSTGRESQL:
            ports[5432] = port_mapping.actual_port

        # Environment variables
        environment = {}
        if database_type == DatabaseType.POSTGRESQL:
            environment.update({
                'POSTGRES_DB': 'postgres',
                'POSTGRES_USER': 'postgres',
                'POSTGRES_PASSWORD': self.generate_secure_password()
            })
        elif database_type == DatabaseType.REDIS:
            environment['REDIS_PASSWORD'] = self.generate_secure_password()

        # Add additional environment variables
        if additional_config and 'environment' in additional_config:
            environment.update(additional_config['environment'])

        # Select image
        image = additional_config.get('image') if additional_config else None
        if not image:
            if database_type == DatabaseType.REDIS:
                image = "redis:latest"
            elif database_type == DatabaseType.POSTGRESQL:
                image = "postgres:latest"

        return DockerContainerConfig(
            image=image,
            name=container_name,
            ports=ports,
            environment=environment,
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

    def _generate_config_file(self, config: DatabaseConfiguration, security_config: SecurityConfig):
        """Generate configuration file content"""
        try:
            templates = self.CONFIG_TEMPLATES.get(config.database_type, {})

            # Build configuration content
            config_content = ""

            # Basic configuration
            if 'basic' in templates:
                basic_config = templates['basic'].format(
                    port=config.connection_config.port,
                    bind_address="127.0.0.1",
                    data_directory=config.data_directory,
                    hba_file=os.path.join(config.data_directory, "pg_hba.conf"),
                    ident_file=os.path.join(config.data_directory, "pg_ident.conf")
                )
                config_content += basic_config

            # Security configuration
            if 'security' in templates and config.password:
                security_template = templates['security'].format(
                    password=config.password
                )
                config_content += security_template

            # Performance configuration
            if 'performance' in templates:
                perf_config = templates['performance'].format(
                    max_memory="256mb",
                    shared_buffers="128MB",
                    effective_cache_size="4GB"
                )
                config_content += perf_config

            # Add additional configuration
            if config.additional_config:
                for key, value in config.additional_config.items():
                    if key != 'environment' and key != 'image':
                        config_content += f"\n# {key}\n{value}\n"

            # Write configuration file
            with open(config.config_file, 'w') as f:
                f.write(config_content)

            logger.info(f"Configuration file generated: {config.config_file}")

        except Exception as e:
            logger.error(f"Error generating configuration file: {e}")
            raise

    def get_configuration_summary(self, config: DatabaseConfiguration) -> Dict[str, Any]:
        """Get configuration summary"""
        return {
            'database_type': config.database_type.value,
            'mode': config.mode.value,
            'host': config.connection_config.host,
            'port': config.connection_config.port,
            'data_directory': config.data_directory,
            'config_file': config.config_file,
            'has_docker_config': config.docker_config is not None,
            'has_volume_config': config.volume_config is not None,
            'created_at': config.created_at,
            'updated_at': config.updated_at
        }