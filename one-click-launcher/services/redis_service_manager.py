"""
Redis Service Detection and Management Module

This module provides comprehensive Redis service detection and management capabilities
including cross-platform service status detection, connection testing, and configuration management.
"""

import os
import sys
import subprocess
import platform
import re
import json
import socket
import time
from typing import Dict, List, Optional, Tuple, Union, Any
from dataclasses import dataclass, asdict
from enum import Enum
import shutil
from pathlib import Path

# Import required modules
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

from utils.logger import get_logger
from core.operating_system_detector import OperatingSystem, Architecture, OperatingSystemDetector

logger = get_logger(__name__)


class RedisServiceStatus(Enum):
    """Redis service status values"""
    RUNNING = "running"
    STOPPED = "stopped"
    INSTALLING = "installing"
    ERROR = "error"
    NOT_INSTALLED = "not_installed"
    UNKNOWN = "unknown"


class RedisConnectionType(Enum):
    """Redis connection types"""
    LOCAL = "local"
    REMOTE = "remote"
    DOCKER = "docker"
    CLUSTER = "cluster"


@dataclass
class RedisServiceInfo:
    """Redis service information"""
    status: RedisServiceStatus
    connection_type: RedisConnectionType
    host: str
    port: int
    version: Optional[str] = None
    service_name: Optional[str] = None
    container_name: Optional[str] = None
    config_file: Optional[str] = None
    data_dir: Optional[str] = None
    log_file: Optional[str] = None
    pid_file: Optional[str] = None
    uptime_seconds: Optional[int] = None
    memory_usage: Optional[str] = None
    connected_clients: Optional[int] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        result = asdict(self)
        result['status'] = self.status.value
        result['connection_type'] = self.connection_type.value
        return result


@dataclass
class RedisConnectionConfig:
    """Redis connection configuration"""
    host: str = "localhost"
    port: int = 6379
    password: Optional[str] = None
    database: int = 0
    socket_timeout: float = 5.0
    socket_connect_timeout: float = 5.0
    max_connections: int = 10
    retry_on_timeout: bool = True
    health_check_interval: int = 30

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        result = asdict(self)
        # Don't include password in dictionary for security
        if result.get('password'):
            result['password'] = '***'
        return result


class RedisServiceManager:
    """
    Comprehensive Redis service detection and management.

    Features:
    - Cross-platform Redis service detection (Windows services, macOS Brew, Linux systemd)
    - Docker container Redis detection and management
    - Connection testing and configuration validation
    - Version detection and compatibility checking
    - Service status monitoring
    """

    # Default Redis configuration
    DEFAULT_REDIS_PORT = 6379
    DEFAULT_REDIS_HOST = "localhost"
    CONNECTION_TIMEOUT = 5.0

    # Platform-specific service names
    WINDOWS_SERVICE_NAMES = ["Redis", "redis", "RedisServer"]
    MACOS_SERVICE_NAMES = ["redis", "redis-server"]
    LINUX_SERVICE_NAMES = ["redis", "redis-server", "redis_6379"]

    # Docker container name patterns
    DOCKER_CONTAINER_PATTERNS = ["redis", "redis-server", "redis-container"]

    def __init__(self):
        """Initialize Redis Service Manager"""
        self.os_detector = OperatingSystemDetector()
        self.system_info = self.os_detector.detect_os_info()
        self._redis_client = None

        logger.info(f"RedisServiceManager initialized for {self.system_info.os_type.value} {self.system_info.architecture.value}")

    def detect_redis_service(self) -> RedisServiceInfo:
        """
        Detect Redis service status across different platforms and installation methods.

        Returns:
            RedisServiceInfo: Comprehensive Redis service information
        """
        logger.info("Starting Redis service detection")

        # Check for Docker containers first
        docker_info = self._detect_docker_redis()
        if docker_info and docker_info.status != RedisServiceStatus.NOT_INSTALLED:
            logger.info("Found Redis running in Docker container")
            return docker_info

        # Check for local Redis service based on platform
        if self.system_info.os_type == OperatingSystem.WINDOWS:
            service_info = self._detect_windows_redis_service()
        elif self.system_info.os_type == OperatingSystem.MACOS:
            service_info = self._detect_macos_redis_service()
        elif self.system_info.os_type == OperatingSystem.LINUX:
            service_info = self._detect_linux_redis_service()
        else:
            service_info = RedisServiceInfo(
                status=RedisServiceStatus.UNKNOWN,
                connection_type=RedisConnectionType.LOCAL,
                host=self.DEFAULT_REDIS_HOST,
                port=self.DEFAULT_REDIS_PORT
            )

        # If no service found, try direct connection test
        if service_info.status == RedisServiceStatus.NOT_INSTALLED:
            connection_info = self._test_redis_connection(
                self.DEFAULT_REDIS_HOST,
                self.DEFAULT_REDIS_PORT
            )
            if connection_info:
                service_info = connection_info
                service_info.connection_type = RedisConnectionType.LOCAL

        logger.info(f"Redis service detection completed: {service_info.status.value}")
        return service_info

    def _detect_windows_redis_service(self) -> RedisServiceInfo:
        """Detect Redis service on Windows using sc query and netstat"""
        logger.debug("Detecting Redis service on Windows")

        service_info = RedisServiceInfo(
            status=RedisServiceStatus.NOT_INSTALLED,
            connection_type=RedisConnectionType.LOCAL,
            host=self.DEFAULT_REDIS_HOST,
            port=self.DEFAULT_REDIS_PORT
        )

        try:
            # Check Windows services using sc query
            for service_name in self.WINDOWS_SERVICE_NAMES:
                try:
                    result = subprocess.run(
                        ['sc', 'query', service_name],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )

                    if result.returncode == 0:
                        # Parse service status from output
                        if "RUNNING" in result.stdout:
                            service_info.status = RedisServiceStatus.RUNNING
                            service_info.service_name = service_name
                        elif "STOPPED" in result.stdout:
                            service_info.status = RedisServiceStatus.STOPPED
                            service_info.service_name = service_name

                        # Extract additional service info
                        self._extract_windows_service_info(result.stdout, service_info)
                        break

                except subprocess.TimeoutExpired:
                    logger.warning(f"Timeout querying Windows service: {service_name}")
                except FileNotFoundError:
                    logger.debug("sc command not found, Windows service detection not available")
                    break

        except Exception as e:
            logger.error(f"Error detecting Windows Redis service: {e}")

        # Check port occupancy using netstat
        if service_info.status in [RedisServiceStatus.RUNNING, RedisServiceStatus.STOPPED]:
            port_info = self._check_port_occupancy(self.DEFAULT_REDIS_PORT)
            if port_info:
                service_info.port = port_info['port']
                if port_info.get('process_name'):
                    service_info.service_name = port_info['process_name']

        return service_info

    def _detect_macos_redis_service(self) -> RedisServiceInfo:
        """Detect Redis service on macOS using brew services"""
        logger.debug("Detecting Redis service on macOS")

        service_info = RedisServiceInfo(
            status=RedisServiceStatus.NOT_INSTALLED,
            connection_type=RedisConnectionType.LOCAL,
            host=self.DEFAULT_REDIS_HOST,
            port=self.DEFAULT_REDIS_PORT
        )

        try:
            # Check brew services
            result = subprocess.run(
                ['brew', 'services', 'list'],
                capture_output=True,
                text=True,
                timeout=15
            )

            if result.returncode == 0:
                # Parse brew services output
                for line in result.stdout.split('\n'):
                    if any(service in line.lower() for service in self.MACOS_SERVICE_NAMES):
                        parts = line.split()
                        if len(parts) >= 2:
                            service_name = parts[0]
                            status = parts[1].lower()

                            service_info.service_name = service_name

                            if status == "started":
                                service_info.status = RedisServiceStatus.RUNNING
                            elif status == "stopped":
                                service_info.status = RedisServiceStatus.STOPPED
                            elif status == "error":
                                service_info.status = RedisServiceStatus.ERROR
                            elif status == "none":
                                service_info.status = RedisServiceStatus.NOT_INSTALLED

                            break
            else:
                logger.debug("brew services command failed, trying alternative detection")

        except subprocess.TimeoutExpired:
            logger.warning("Timeout checking brew services")
        except FileNotFoundError:
            logger.debug("brew command not found, using alternative detection methods")
        except Exception as e:
            logger.error(f"Error detecting macOS Redis service: {e}")

        # Check for Redis process using ps
        if service_info.status == RedisServiceStatus.NOT_INSTALLED:
            process_info = self._check_redis_process()
            if process_info:
                service_info.status = RedisServiceStatus.RUNNING
                service_info.service_name = process_info.get('name')
                service_info.pid_file = str(process_info.get('pid'))

        # Check port occupancy
        port_info = self._check_port_occupancy(self.DEFAULT_REDIS_PORT)
        if port_info:
            service_info.port = port_info['port']

        return service_info

    def _detect_linux_redis_service(self) -> RedisServiceInfo:
        """Detect Redis service on Linux using systemctl and service commands"""
        logger.debug("Detecting Redis service on Linux")

        service_info = RedisServiceInfo(
            status=RedisServiceStatus.NOT_INSTALLED,
            connection_type=RedisConnectionType.LOCAL,
            host=self.DEFAULT_REDIS_HOST,
            port=self.DEFAULT_REDIS_PORT
        )

        # Try systemctl first (systemd systems)
        try:
            for service_name in self.LINUX_SERVICE_NAMES:
                # Check if service exists
                exists_result = subprocess.run(
                    ['systemctl', 'list-unit-files', f'{service_name}.service'],
                    capture_output=True,
                    text=True,
                    timeout=10
                )

                if exists_result.returncode == 0 and service_name in exists_result.stdout:
                    # Get service status
                    status_result = subprocess.run(
                        ['systemctl', 'is-active', service_name],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )

                    service_info.service_name = service_name

                    if status_result.returncode == 0:
                        status = status_result.stdout.strip()
                        if status == "active":
                            service_info.status = RedisServiceStatus.RUNNING
                        elif status == "inactive":
                            service_info.status = RedisServiceStatus.STOPPED
                        elif status == "failed":
                            service_info.status = RedisServiceStatus.ERROR
                    else:
                        service_info.status = RedisServiceStatus.STOPPED

                    # Get additional service info
                    self._extract_systemd_service_info(service_name, service_info)
                    break

        except subprocess.TimeoutExpired:
            logger.warning("Timeout checking systemctl services")
        except FileNotFoundError:
            logger.debug("systemctl not found, trying service command")

        # Fallback to service command (sysvinit systems)
        if service_info.status == RedisServiceStatus.NOT_INSTALLED:
            try:
                for service_name in self.LINUX_SERVICE_NAMES:
                    result = subprocess.run(
                        ['service', service_name, 'status'],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )

                    if result.returncode == 0:
                        service_info.service_name = service_name

                        # Parse status from output
                        if "running" in result.stdout.lower() or "is running" in result.stdout.lower():
                            service_info.status = RedisServiceStatus.RUNNING
                        elif "stopped" in result.stdout.lower():
                            service_info.status = RedisServiceStatus.STOPPED
                        elif "not running" in result.stdout.lower():
                            service_info.status = RedisServiceStatus.STOPPED

                        break

            except subprocess.TimeoutExpired:
                logger.warning("Timeout checking service command")
            except FileNotFoundError:
                logger.debug("service command not found")
            except Exception as e:
                logger.error(f"Error with service command: {e}")

        # Check port occupancy
        port_info = self._check_port_occupancy(self.DEFAULT_REDIS_PORT)
        if port_info:
            service_info.port = port_info['port']

        return service_info

    def _detect_docker_redis(self) -> Optional[RedisServiceInfo]:
        """Detect Redis running in Docker containers"""
        logger.debug("Detecting Redis in Docker containers")

        try:
            # Check if Docker is available
            subprocess.run(['docker', '--version'], capture_output=True, check=True, timeout=5)

            # List running containers
            result = subprocess.run(
                ['docker', 'ps', '--format', 'json'],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                containers = result.stdout.strip().split('\n')

                for container_line in containers:
                    if not container_line.strip():
                        continue

                    try:
                        container = json.loads(container_line)
                        container_name = container.get('Names', '').lower()
                        container_image = container.get('Image', '').lower()

                        # Check if this is a Redis container
                        if (any(pattern in container_name for pattern in self.DOCKER_CONTAINER_PATTERNS) or
                            'redis' in container_image):

                            # Get container details
                            service_info = RedisServiceInfo(
                                status=RedisServiceStatus.RUNNING,
                                connection_type=RedisConnectionType.DOCKER,
                                host=self.DEFAULT_REDIS_HOST,
                                port=self.DEFAULT_REDIS_PORT,
                                container_name=container['Names']
                            )

                            # Get port mappings
                            ports = container.get('Ports', '')
                            if ports:
                                port_match = re.search(r'(\d+)->6379/tcp', ports)
                                if port_match:
                                    service_info.port = int(port_match.group(1))

                            # Get Redis version from container
                            version_info = self._get_docker_redis_version(container['Names'])
                            if version_info:
                                service_info.version = version_info

                            return service_info

                    except json.JSONDecodeError:
                        continue

        except subprocess.CalledProcessError:
            logger.debug("Docker not available or not running")
        except subprocess.TimeoutExpired:
            logger.warning("Timeout checking Docker containers")
        except Exception as e:
            logger.error(f"Error detecting Docker Redis: {e}")

        return None

    def _test_redis_connection(self, host: str, port: int, password: Optional[str] = None) -> Optional[RedisServiceInfo]:
        """Test Redis connection and gather information"""
        logger.debug(f"Testing Redis connection to {host}:{port}")

        if not REDIS_AVAILABLE:
            logger.warning("redis-python package not available, using basic connection test")
            return self._test_basic_redis_connection(host, port)

        try:
            config = RedisConnectionConfig(
                host=host,
                port=port,
                password=password,
                socket_timeout=self.CONNECTION_TIMEOUT,
                socket_connect_timeout=self.CONNECTION_TIMEOUT
            )

            client = redis.Redis(
                host=config.host,
                port=config.port,
                password=config.password,
                socket_timeout=config.socket_timeout,
                socket_connect_timeout=config.socket_connect_timeout,
                decode_responses=True
            )

            # Test connection
            client.ping()

            # Get Redis info
            info = client.info()

            service_info = RedisServiceInfo(
                status=RedisServiceStatus.RUNNING,
                connection_type=RedisConnectionType.LOCAL,
                host=host,
                port=port,
                version=info.get('redis_version'),
                uptime_seconds=info.get('uptime_in_seconds'),
                memory_usage=info.get('used_memory_human'),
                connected_clients=info.get('connected_clients')
            )

            return service_info

        except redis.ConnectionError as e:
            logger.debug(f"Redis connection failed: {e}")
            return None
        except redis.AuthenticationError as e:
            logger.warning(f"Redis authentication failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Error testing Redis connection: {e}")
            return None

    def _test_basic_redis_connection(self, host: str, port: int) -> Optional[RedisServiceInfo]:
        """Basic Redis connection test using socket"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.CONNECTION_TIMEOUT)
            result = sock.connect_ex((host, port))
            sock.close()

            if result == 0:
                return RedisServiceInfo(
                    status=RedisServiceStatus.RUNNING,
                    connection_type=RedisConnectionType.LOCAL,
                    host=host,
                    port=port
                )
            else:
                return None

        except Exception as e:
            logger.error(f"Error in basic Redis connection test: {e}")
            return None

    def _check_port_occupancy(self, port: int) -> Optional[Dict]:
        """Check if a port is occupied and by which process"""
        try:
            if self.system_info.os_type == OperatingSystem.WINDOWS:
                result = subprocess.run(
                    ['netstat', '-ano'],
                    capture_output=True,
                    text=True,
                    timeout=10
                )

                for line in result.stdout.split('\n'):
                    if f':{port}' in line and 'LISTENING' in line:
                        parts = line.split()
                        if len(parts) >= 5:
                            pid = parts[-1]
                            process_name = self._get_process_name_by_pid(pid)
                            return {'port': port, 'pid': pid, 'process_name': process_name}
            else:
                result = subprocess.run(
                    ['netstat', '-tlnp'],
                    capture_output=True,
                    text=True,
                    timeout=10
                )

                for line in result.stdout.split('\n'):
                    if f':{port}' in line and 'LISTEN' in line:
                        parts = line.split()
                        if len(parts) >= 7:
                            pid_process = parts[-1].split('/')
                            if len(pid_process) == 2:
                                pid = pid_process[0]
                                process_name = pid_process[1]
                                return {'port': port, 'pid': pid, 'process_name': process_name}

        except Exception as e:
            logger.error(f"Error checking port occupancy: {e}")

        return None

    def _get_process_name_by_pid(self, pid: str) -> Optional[str]:
        """Get process name by PID (Windows only)"""
        try:
            result = subprocess.run(
                ['tasklist', '/FI', f'PID eq {pid}', '/FO', 'CSV'],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                lines = result.stdout.split('\n')
                if len(lines) >= 2:
                    process_line = lines[1]
                    if process_line:
                        parts = process_line.split(',')
                        if len(parts) >= 2:
                            return parts[0].strip('"')

        except Exception as e:
            logger.error(f"Error getting process name for PID {pid}: {e}")

        return None

    def _check_redis_process(self) -> Optional[Dict]:
        """Check for Redis process using ps command"""
        try:
            result = subprocess.run(
                ['ps', 'aux'],
                capture_output=True,
                text=True,
                timeout=10
            )

            for line in result.stdout.split('\n'):
                if 'redis-server' in line and 'grep' not in line:
                    parts = line.split()
                    if len(parts) >= 2:
                        return {
                            'user': parts[0],
                            'pid': parts[1],
                            'name': 'redis-server',
                            'command': ' '.join(parts[10:])
                        }

        except Exception as e:
            logger.error(f"Error checking Redis process: {e}")

        return None

    def _extract_windows_service_info(self, sc_output: str, service_info: RedisServiceInfo):
        """Extract additional service information from sc query output"""
        try:
            for line in sc_output.split('\n'):
                if 'SERVICE_NAME:' in line:
                    service_info.service_name = line.split(':')[1].strip()
                elif 'STATE:' in line:
                    # Additional state parsing if needed
                    pass
        except Exception as e:
            logger.error(f"Error extracting Windows service info: {e}")

    def _extract_systemd_service_info(self, service_name: str, service_info: RedisServiceInfo):
        """Extract additional service information from systemctl"""
        try:
            # Get service status details
            result = subprocess.run(
                ['systemctl', 'show', service_name, '--property=ExecStart,FragmentPath'],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if line.startswith('ExecStart='):
                        exec_start = line.split('=', 1)[1]
                        service_info.config_file = self._extract_config_from_command(exec_start)
                    elif line.startswith('FragmentPath='):
                        service_path = line.split('=', 1)[1]
                        service_info.config_file = service_path

        except Exception as e:
            logger.error(f"Error extracting systemd service info: {e}")

    def _extract_config_from_command(self, command: str) -> Optional[str]:
        """Extract config file path from Redis command"""
        try:
            # Look for config file argument
            if '--config' in command:
                parts = command.split()
                for i, part in enumerate(parts):
                    if part == '--config' and i + 1 < len(parts):
                        return parts[i + 1]
                    elif part.startswith('--config='):
                        return part.split('=', 1)[1]
        except Exception as e:
            logger.error(f"Error extracting config from command: {e}")

        return None

    def _get_docker_redis_version(self, container_name: str) -> Optional[str]:
        """Get Redis version from Docker container"""
        try:
            result = subprocess.run(
                ['docker', 'exec', container_name, 'redis-server', '--version'],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                version_match = re.search(r'v=([\d.]+)', result.stdout)
                if version_match:
                    return version_match.group(1)

        except Exception as e:
            logger.error(f"Error getting Docker Redis version: {e}")

        return None

    def validate_redis_configuration(self, config: RedisConnectionConfig) -> Tuple[bool, List[str]]:
        """
        Validate Redis connection configuration.

        Args:
            config: Redis connection configuration

        Returns:
            Tuple[bool, List[str]]: (is_valid, error_messages)
        """
        errors = []

        # Validate host
        if not config.host:
            errors.append("Redis host is required")

        # Validate port
        if not isinstance(config.port, int) or config.port < 1 or config.port > 65535:
            errors.append("Redis port must be an integer between 1 and 65535")

        # Validate timeout values
        if config.socket_timeout <= 0:
            errors.append("Socket timeout must be greater than 0")

        if config.socket_connect_timeout <= 0:
            errors.append("Socket connect timeout must be greater than 0")

        # Test connection if basic validation passes
        if not errors:
            connection_info = self._test_redis_connection(config.host, config.port, config.password)
            if not connection_info:
                errors.append(f"Cannot connect to Redis at {config.host}:{config.port}")

        return len(errors) == 0, errors

    def get_redis_info(self, config: Optional[RedisConnectionConfig] = None) -> Optional[Dict]:
        """
        Get comprehensive Redis information.

        Args:
            config: Optional Redis connection configuration

        Returns:
            Dict with Redis information or None if connection fails
        """
        if config is None:
            # Use detected service info
            service_info = self.detect_redis_service()
            config = RedisConnectionConfig(
                host=service_info.host,
                port=service_info.port
            )

        if not REDIS_AVAILABLE:
            logger.warning("redis-python package not available for detailed info")
            return None

        try:
            client = redis.Redis(
                host=config.host,
                port=config.port,
                password=config.password,
                socket_timeout=config.socket_timeout,
                socket_connect_timeout=config.socket_connect_timeout,
                decode_responses=True
            )

            # Get all Redis info
            info = client.info()

            # Organize information
            organized_info = {
                'server': {
                    'version': info.get('redis_version'),
                    'mode': info.get('redis_mode'),
                    'os': info.get('os'),
                    'arch_bits': info.get('arch_bits'),
                    'uptime_in_seconds': info.get('uptime_in_seconds'),
                    'uptime_in_days': info.get('uptime_in_days')
                },
                'memory': {
                    'used_memory': info.get('used_memory'),
                    'used_memory_human': info.get('used_memory_human'),
                    'used_memory_rss': info.get('used_memory_rss'),
                    'used_memory_peak': info.get('used_memory_peak'),
                    'used_memory_peak_human': info.get('used_memory_peak_human')
                },
                'clients': {
                    'connected_clients': info.get('connected_clients'),
                    'client_recent_max_input_buffer': info.get('client_recent_max_input_buffer'),
                    'client_recent_max_output_buffer': info.get('client_recent_max_output_buffer')
                },
                'stats': {
                    'total_connections_received': info.get('total_connections_received'),
                    'total_commands_processed': info.get('total_commands_processed'),
                    'instantaneous_ops_per_sec': info.get('instantaneous_ops_per_sec'),
                    'keyspace_hits': info.get('keyspace_hits'),
                    'keyspace_misses': info.get('keyspace_misses')
                },
                'persistence': {
                    'loading': info.get('loading'),
                    'rdb_changes_since_last_save': info.get('rdb_changes_since_last_save'),
                    'rdb_bgsave_in_progress': info.get('rdb_bgsave_in_progress'),
                    'rdb_last_save_time': info.get('rdb_last_save_time')
                }
            }

            return organized_info

        except Exception as e:
            logger.error(f"Error getting Redis info: {e}")
            return None

    def start_redis_service(self) -> Tuple[bool, str]:
        """
        Attempt to start Redis service using platform-specific commands.

        Returns:
            Tuple[bool, str]: (success, message)
        """
        logger.info("Attempting to start Redis service")

        try:
            if self.system_info.os_type == OperatingSystem.WINDOWS:
                return self._start_windows_redis()
            elif self.system_info.os_type == OperatingSystem.MACOS:
                return self._start_macos_redis()
            elif self.system_info.os_type == OperatingSystem.LINUX:
                return self._start_linux_redis()
            else:
                return False, f"Starting Redis service not supported on {self.system_info.os_type.value}"

        except Exception as e:
            logger.error(f"Error starting Redis service: {e}")
            return False, f"Error starting Redis service: {str(e)}"

    def _start_windows_redis(self) -> Tuple[bool, str]:
        """Start Redis service on Windows"""
        try:
            service_info = self._detect_windows_redis_service()
            if service_info.service_name:
                result = subprocess.run(
                    ['sc', 'start', service_info.service_name],
                    capture_output=True,
                    text=True,
                    timeout=30
                )

                if result.returncode == 0:
                    return True, f"Redis service '{service_info.service_name}' started successfully"
                else:
                    return False, f"Failed to start Redis service: {result.stderr}"
            else:
                return False, "Redis service not found on Windows"

        except Exception as e:
            return False, f"Error starting Windows Redis service: {str(e)}"

    def _start_macos_redis(self) -> Tuple[bool, str]:
        """Start Redis service on macOS"""
        try:
            result = subprocess.run(
                ['brew', 'services', 'start', 'redis'],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                return True, "Redis service started via brew services"
            else:
                return False, f"Failed to start Redis via brew: {result.stderr}"

        except Exception as e:
            return False, f"Error starting macOS Redis service: {str(e)}"

    def _start_linux_redis(self) -> Tuple[bool, str]:
        """Start Redis service on Linux"""
        try:
            # Try systemctl first
            result = subprocess.run(
                ['systemctl', 'start', 'redis'],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                return True, "Redis service started via systemctl"
            else:
                # Try service command
                result = subprocess.run(
                    ['service', 'redis', 'start'],
                    capture_output=True,
                    text=True,
                    timeout=30
                )

                if result.returncode == 0:
                    return True, "Redis service started via service command"
                else:
                    return False, f"Failed to start Redis service: {result.stderr}"

        except Exception as e:
            return False, f"Error starting Linux Redis service: {str(e)}"