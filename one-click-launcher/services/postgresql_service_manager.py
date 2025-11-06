"""
PostgreSQL Service Detection and Management Module

This module provides comprehensive PostgreSQL service detection and management capabilities
including cross-platform service status detection, version compatibility checking,
connection testing, and configuration management.
"""

import os
import sys
import subprocess
import platform
import re
import json
import socket
import time
import psutil
from typing import Dict, List, Optional, Tuple, Union, Any
from dataclasses import dataclass, asdict
from enum import Enum
import shutil
from pathlib import Path

# Import required modules
try:
    import psycopg2
    import psycopg2.extras
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False

from utils.logger import get_logger
from core.operating_system_detector import OperatingSystem, Architecture, OperatingSystemDetector

logger = get_logger(__name__)


class PostgreSQLServiceStatus(Enum):
    """PostgreSQL service status values"""
    RUNNING = "running"
    STOPPED = "stopped"
    INSTALLING = "installing"
    ERROR = "error"
    NOT_INSTALLED = "not_installed"
    UNKNOWN = "unknown"


class PostgreSQLConnectionType(Enum):
    """PostgreSQL connection types"""
    LOCAL = "local"
    REMOTE = "remote"
    DOCKER = "docker"
    CLUSTER = "cluster"


@dataclass
class PostgreSQLServiceInfo:
    """PostgreSQL service information"""
    status: PostgreSQLServiceStatus
    connection_type: PostgreSQLConnectionType
    host: str
    port: int
    version: Optional[str] = None
    service_name: Optional[str] = None
    container_name: Optional[str] = None
    data_directory: Optional[str] = None
    config_file: Optional[str] = None
    log_file: Optional[str] = None
    pid_file: Optional[str] = None
    username: Optional[str] = None
    database: Optional[str] = None
    uptime_seconds: Optional[int] = None
    max_connections: Optional[int] = None
    current_connections: Optional[int] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        result = asdict(self)
        result['status'] = self.status.value
        result['connection_type'] = self.connection_type.value
        return result


@dataclass
class PostgreSQLConnectionConfig:
    """PostgreSQL connection configuration"""
    host: str = "localhost"
    port: int = 5432
    database: str = "postgres"
    username: str = "postgres"
    password: Optional[str] = None
    sslmode: str = "prefer"
    connect_timeout: float = 10.0
    application_name: str = "one_click_launcher"
    sslcert: Optional[str] = None
    sslkey: Optional[str] = None
    sslrootcert: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        result = asdict(self)
        # Don't include password in dictionary for security
        if result.get('password'):
            result['password'] = '***'
        return result


@dataclass
class PostgreSQLVersion:
    """PostgreSQL version information"""
    major: int
    minor: int
    patch: int = 0
    full_version: str = ""
    is_compatible: bool = True

    def __str__(self) -> str:
        return self.full_version or f"{self.major}.{self.minor}.{self.patch}"

    def meets_minimum(self, min_major: int, min_minor: int = 0) -> bool:
        """Check if version meets minimum requirements"""
        return (self.major, self.minor) >= (min_major, min_minor)


class PostgreSQLServiceManager:
    """
    Comprehensive PostgreSQL service detection and management.

    Features:
    - Cross-platform PostgreSQL service detection (Windows services, macOS Brew, Linux systemd)
    - Docker container PostgreSQL detection and management
    - Version detection and compatibility checking
    - Connection testing and authentication validation
    - Configuration file management and validation
    """

    # Default PostgreSQL configuration
    DEFAULT_POSTGRESQL_PORT = 5432
    DEFAULT_POSTGRESQL_HOST = "localhost"
    CONNECTION_TIMEOUT = 10.0
    MINIMUM_SUPPORTED_VERSION = (10, 0)  # PostgreSQL 10+

    # Platform-specific service names
    WINDOWS_SERVICE_NAMES = [
        "postgresql-x64-16", "postgresql-x64-15", "postgresql-x64-14",
        "postgresql-x64-13", "postgresql-x64-12", "postgresql-x64-11",
        "postgresql-x64-10", "postgresql-x64-9.6", "postgresql-x64-9.5",
        "postgresql", "postgres", "PostgreSQL"
    ]
    MACOS_SERVICE_NAMES = ["postgresql", "postgres", "org.postgresql.postgres"]
    LINUX_SERVICE_NAMES = [
        "postgresql", "postgresql-16", "postgresql-15", "postgresql-14",
        "postgresql-13", "postgresql-12", "postgresql-11", "postgresql-10",
        "postgresql-9.6", "postgresql-9.5", "postgres"
    ]

    # Docker container name patterns
    DOCKER_CONTAINER_PATTERNS = ["postgres", "postgresql", "postgres-container"]

    # Common PostgreSQL data directory paths
    COMMON_DATA_PATHS = {
        OperatingSystem.WINDOWS: [
            "C:\\Program Files\\PostgreSQL",
            "C:\\Program Files (x86)\\PostgreSQL",
            "C:\\PostgreSQL",
            "C:\\data\\postgresql"
        ],
        OperatingSystem.MACOS: [
            "/usr/local/var/postgres",
            "/var/lib/postgresql",
            "/opt/homebrew/var/postgres",
            "/Library/PostgreSQL"
        ],
        OperatingSystem.LINUX: [
            "/var/lib/postgresql",
            "/var/lib/pgsql",
            "/usr/local/pgsql/data",
            "/opt/postgresql/data"
        ]
    }

    # Common configuration file paths
    COMMON_CONFIG_PATHS = {
        OperatingSystem.WINDOWS: [
            "C:\\Program Files\\PostgreSQL\\data\\postgresql.conf",
            "C:\\Program Files (x86)\\PostgreSQL\\data\\postgresql.conf"
        ],
        OperatingSystem.MACOS: [
            "/usr/local/var/postgres/postgresql.conf",
            "/opt/homebrew/var/postgres/postgresql.conf",
            "/var/lib/postgresql/postgresql.conf"
        ],
        OperatingSystem.LINUX: [
            "/var/lib/postgresql/*/data/postgresql.conf",
            "/var/lib/pgsql/*/data/postgresql.conf",
            "/etc/postgresql/*/main/postgresql.conf"
        ]
    }

    def __init__(self):
        """Initialize PostgreSQL Service Manager"""
        self.os_detector = OperatingSystemDetector()
        self.system_info = self.os_detector.detect_os_info()
        self._connection = None

        logger.info(f"PostgreSQLServiceManager initialized for {self.system_info.os_type.value} {self.system_info.architecture.value}")

    def detect_postgresql_service(self) -> PostgreSQLServiceInfo:
        """
        Detect PostgreSQL service status across different platforms and installation methods.

        Returns:
            PostgreSQLServiceInfo: Comprehensive PostgreSQL service information
        """
        logger.info("Starting PostgreSQL service detection")

        # Check for Docker containers first
        docker_info = self._detect_docker_postgresql()
        if docker_info and docker_info.status != PostgreSQLServiceStatus.NOT_INSTALLED:
            logger.info("Found PostgreSQL running in Docker container")
            return docker_info

        # Check for local PostgreSQL service based on platform
        if self.system_info.os_type == OperatingSystem.WINDOWS:
            service_info = self._detect_windows_postgresql_service()
        elif self.system_info.os_type == OperatingSystem.MACOS:
            service_info = self._detect_macos_postgresql_service()
        elif self.system_info.os_type == OperatingSystem.LINUX:
            service_info = self._detect_linux_postgresql_service()
        else:
            service_info = PostgreSQLServiceInfo(
                status=PostgreSQLServiceStatus.UNKNOWN,
                connection_type=PostgreSQLConnectionType.LOCAL,
                host=self.DEFAULT_POSTGRESQL_HOST,
                port=self.DEFAULT_POSTGRESQL_PORT
            )

        # If no service found, try direct connection test
        if service_info.status == PostgreSQLServiceStatus.NOT_INSTALLED:
            connection_info = self._test_postgresql_connection(
                self.DEFAULT_POSTGRESQL_HOST,
                self.DEFAULT_POSTGRESQL_PORT
            )
            if connection_info:
                service_info = connection_info
                service_info.connection_type = PostgreSQLConnectionType.LOCAL

        logger.info(f"PostgreSQL service detection completed: {service_info.status.value}")
        return service_info

    def _detect_windows_postgresql_service(self) -> PostgreSQLServiceInfo:
        """Detect PostgreSQL service on Windows using sc query and process detection"""
        logger.debug("Detecting PostgreSQL service on Windows")

        service_info = PostgreSQLServiceInfo(
            status=PostgreSQLServiceStatus.NOT_INSTALLED,
            connection_type=PostgreSQLConnectionType.LOCAL,
            host=self.DEFAULT_POSTGRESQL_HOST,
            port=self.DEFAULT_POSTGRESQL_PORT
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
                            service_info.status = PostgreSQLServiceStatus.RUNNING
                            service_info.service_name = service_name
                        elif "STOPPED" in result.stdout:
                            service_info.status = PostgreSQLServiceStatus.STOPPED
                            service_info.service_name = service_name

                        # Extract additional service info
                        self._extract_windows_postgresql_service_info(result.stdout, service_info)
                        break

                except subprocess.TimeoutExpired:
                    logger.warning(f"Timeout querying Windows service: {service_name}")
                except FileNotFoundError:
                    logger.debug("sc command not found, Windows service detection not available")
                    break

        except Exception as e:
            logger.error(f"Error detecting Windows PostgreSQL service: {e}")

        # Check for PostgreSQL processes
        if service_info.status == PostgreSQLServiceStatus.NOT_INSTALLED:
            process_info = self._check_postgresql_process()
            if process_info:
                service_info.status = PostgreSQLServiceStatus.RUNNING
                service_info.service_name = process_info.get('name', 'postgres')

        # Check port occupancy using netstat
        if service_info.status in [PostgreSQLServiceStatus.RUNNING, PostgreSQLServiceStatus.STOPPED]:
            port_info = self._check_port_occupancy(self.DEFAULT_POSTGRESQL_PORT)
            if port_info:
                service_info.port = port_info['port']
                if port_info.get('process_name'):
                    service_info.service_name = port_info['process_name']

        # Try to find data directory and config file
        if service_info.status != PostgreSQLServiceStatus.NOT_INSTALLED:
            self._find_postgresql_installation_paths(service_info)

        return service_info

    def _detect_macos_postgresql_service(self) -> PostgreSQLServiceInfo:
        """Detect PostgreSQL service on macOS using brew services and process detection"""
        logger.debug("Detecting PostgreSQL service on macOS")

        service_info = PostgreSQLServiceInfo(
            status=PostgreSQLServiceStatus.NOT_INSTALLED,
            connection_type=PostgreSQLConnectionType.LOCAL,
            host=self.DEFAULT_POSTGRESQL_HOST,
            port=self.DEFAULT_POSTGRESQL_PORT
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
                                service_info.status = PostgreSQLServiceStatus.RUNNING
                            elif status == "stopped":
                                service_info.status = PostgreSQLServiceStatus.STOPPED
                            elif status == "error":
                                service_info.status = PostgreSQLServiceStatus.ERROR
                            elif status == "none":
                                service_info.status = PostgreSQLServiceStatus.NOT_INSTALLED

                            break
            else:
                logger.debug("brew services command failed, trying alternative detection")

        except subprocess.TimeoutExpired:
            logger.warning("Timeout checking brew services")
        except FileNotFoundError:
            logger.debug("brew command not found, using alternative detection methods")
        except Exception as e:
            logger.error(f"Error detecting macOS PostgreSQL service: {e}")

        # Check for PostgreSQL process using ps
        if service_info.status == PostgreSQLServiceStatus.NOT_INSTALLED:
            process_info = self._check_postgresql_process()
            if process_info:
                service_info.status = PostgreSQLServiceStatus.RUNNING
                service_info.service_name = process_info.get('name', 'postgres')

        # Check port occupancy
        port_info = self._check_port_occupancy(self.DEFAULT_POSTGRESQL_PORT)
        if port_info:
            service_info.port = port_info['port']

        # Try to find data directory and config file
        if service_info.status != PostgreSQLServiceStatus.NOT_INSTALLED:
            self._find_postgresql_installation_paths(service_info)

        return service_info

    def _detect_linux_postgresql_service(self) -> PostgreSQLServiceInfo:
        """Detect PostgreSQL service on Linux using systemctl and service commands"""
        logger.debug("Detecting PostgreSQL service on Linux")

        service_info = PostgreSQLServiceInfo(
            status=PostgreSQLServiceStatus.NOT_INSTALLED,
            connection_type=PostgreSQLConnectionType.LOCAL,
            host=self.DEFAULT_POSTGRESQL_HOST,
            port=self.DEFAULT_POSTGRESQL_PORT
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
                            service_info.status = PostgreSQLServiceStatus.RUNNING
                        elif status == "inactive":
                            service_info.status = PostgreSQLServiceStatus.STOPPED
                        elif status == "failed":
                            service_info.status = PostgreSQLServiceStatus.ERROR
                    else:
                        service_info.status = PostgreSQLServiceStatus.STOPPED

                    # Get additional service info
                    self._extract_systemd_postgresql_service_info(service_name, service_info)
                    break

        except subprocess.TimeoutExpired:
            logger.warning("Timeout checking systemctl services")
        except FileNotFoundError:
            logger.debug("systemctl not found, trying service command")

        # Fallback to service command (sysvinit systems)
        if service_info.status == PostgreSQLServiceStatus.NOT_INSTALLED:
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
                            service_info.status = PostgreSQLServiceStatus.RUNNING
                        elif "stopped" in result.stdout.lower():
                            service_info.status = PostgreSQLServiceStatus.STOPPED
                        elif "not running" in result.stdout.lower():
                            service_info.status = PostgreSQLServiceStatus.STOPPED

                        break

            except subprocess.TimeoutExpired:
                logger.warning("Timeout checking service command")
            except FileNotFoundError:
                logger.debug("service command not found")
            except Exception as e:
                logger.error(f"Error with service command: {e}")

        # Check for PostgreSQL process
        if service_info.status == PostgreSQLServiceStatus.NOT_INSTALLED:
            process_info = self._check_postgresql_process()
            if process_info:
                service_info.status = PostgreSQLServiceStatus.RUNNING
                service_info.service_name = process_info.get('name', 'postgres')

        # Check port occupancy
        port_info = self._check_port_occupancy(self.DEFAULT_POSTGRESQL_PORT)
        if port_info:
            service_info.port = port_info['port']

        # Try to find data directory and config file
        if service_info.status != PostgreSQLServiceStatus.NOT_INSTALLED:
            self._find_postgresql_installation_paths(service_info)

        return service_info

    def _detect_docker_postgresql(self) -> Optional[PostgreSQLServiceInfo]:
        """Detect PostgreSQL running in Docker containers"""
        logger.debug("Detecting PostgreSQL in Docker containers")

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

                        # Check if this is a PostgreSQL container
                        if (any(pattern in container_name for pattern in self.DOCKER_CONTAINER_PATTERNS) or
                            'postgres' in container_image):

                            # Get container details
                            service_info = PostgreSQLServiceInfo(
                                status=PostgreSQLServiceStatus.RUNNING,
                                connection_type=PostgreSQLConnectionType.DOCKER,
                                host=self.DEFAULT_POSTGRESQL_HOST,
                                port=self.DEFAULT_POSTGRESQL_PORT,
                                container_name=container['Names']
                            )

                            # Get port mappings
                            ports = container.get('Ports', '')
                            if ports:
                                port_match = re.search(r'(\d+)->5432/tcp', ports)
                                if port_match:
                                    service_info.port = int(port_match.group(1))

                            # Get PostgreSQL version from container
                            version_info = self._get_docker_postgresql_version(container['Names'])
                            if version_info:
                                service_info.version = str(version_info)

                            return service_info

                    except json.JSONDecodeError:
                        continue

        except subprocess.CalledProcessError:
            logger.debug("Docker not available or not running")
        except subprocess.TimeoutExpired:
            logger.warning("Timeout checking Docker containers")
        except Exception as e:
            logger.error(f"Error detecting Docker PostgreSQL: {e}")

        return None

    def _test_postgresql_connection(self, host: str, port: int,
                                  database: str = "postgres",
                                  username: str = "postgres",
                                  password: Optional[str] = None) -> Optional[PostgreSQLServiceInfo]:
        """Test PostgreSQL connection and gather information"""
        logger.debug(f"Testing PostgreSQL connection to {host}:{port}/{database}")

        if not PSYCOPG2_AVAILABLE:
            logger.warning(f"psycopg2 package not available, PSYCOPG2_AVAILABLE={PSYCOPG2_AVAILABLE}, using basic connection test")
            return self._test_basic_postgresql_connection(host, port)

        logger.info(f"PSYCOPG2_AVAILABLE={PSYCOPG2_AVAILABLE}, proceeding with psycopg2 connection test")

        try:
            logger.info("Creating PostgreSQL connection config")
            config = PostgreSQLConnectionConfig(
                host=host,
                port=port,
                database=database,
                username=username,
                password=password,
                connect_timeout=self.CONNECTION_TIMEOUT
            )

            # Build connection string
            conn_string = (
                f"host={config.host} "
                f"port={config.port} "
                f"dbname={config.database} "
                f"user={config.username} "
                f"connect_timeout={config.connect_timeout}"
            )

            if config.password:
                conn_string += f" password={config.password}"

            # Test connection
            logger.info("Attempting psycopg2.connect")
            import psycopg2
            connection = psycopg2.connect(conn_string)
            connection.autocommit = True
            logger.info("Connection established, creating cursor")

            with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                logger.info("Cursor created, executing version query")
                # Get PostgreSQL version
                cursor.execute("SELECT version()")
                version_row = cursor.fetchone()
                version_str = version_row['version'] if version_row else ""
                parsed_version = self._parse_postgresql_version(version_str)
                logger.info(f"Version query completed: {version_str}")

                # Get connection info
                logger.info("Executing connection info query")
                cursor.execute("""
                    SELECT
                        current_database() as database,
                        current_user as username,
                        (SELECT count(*) FROM pg_stat_activity) as current_connections,
                        (SELECT setting FROM pg_settings WHERE name = 'max_connections') as max_connections,
                        (SELECT setting FROM pg_settings WHERE name = 'data_directory') as data_directory
                """)
                info_row = cursor.fetchone()
                logger.info("Connection info query completed")

                logger.info(f"Creating PostgreSQLServiceInfo with parsed_version={parsed_version}, info_row={info_row}")
                service_info = PostgreSQLServiceInfo(
                    status=PostgreSQLServiceStatus.RUNNING,
                    connection_type=PostgreSQLConnectionType.LOCAL,
                    host=host,
                    port=port,
                    version=str(parsed_version) if parsed_version else None,
                    database=info_row['database'] if info_row else database,
                    username=info_row['username'] if info_row else username,
                    data_directory=info_row['data_directory'] if info_row else None,
                    current_connections=info_row['current_connections'] if info_row else None,
                    max_connections=int(info_row['max_connections']) if info_row and info_row['max_connections'] else None
                )
                logger.info(f"PostgreSQLServiceInfo created successfully: {service_info}")

            connection.close()
            logger.info("Connection closed, returning service_info")
            return service_info

        except Exception as e:
            # Handle psycopg2 specific errors if module is available
            if PSYCOPG2_AVAILABLE:
                try:
                    if isinstance(e, psycopg2.OperationalError):
                        logger.debug(f"PostgreSQL connection failed: {e}")
                        return None
                    elif isinstance(e, psycopg2.Error):
                        logger.warning(f"PostgreSQL error: {e}")
                        return None
                except:
                    pass  # If psycopg2 exception classes are not available

            # Generic error handling
            logger.error(f"Error testing PostgreSQL connection: {e}")
            return None

    def _test_basic_postgresql_connection(self, host: str, port: int) -> Optional[PostgreSQLServiceInfo]:
        """Basic PostgreSQL connection test using socket"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.CONNECTION_TIMEOUT)
            result = sock.connect_ex((host, port))
            sock.close()

            if result == 0:
                return PostgreSQLServiceInfo(
                    status=PostgreSQLServiceStatus.RUNNING,
                    connection_type=PostgreSQLConnectionType.LOCAL,
                    host=host,
                    port=port
                )
            else:
                return None

        except Exception as e:
            logger.error(f"Error in basic PostgreSQL connection test: {e}")
            return None

    def _check_postgresql_process(self) -> Optional[Dict]:
        """Check for PostgreSQL process using psutil"""
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if 'postgres' in proc.info['name'].lower() or \
                       any('postgres' in arg.lower() for arg in proc.info.get('cmdline', [])):
                        return {
                            'pid': proc.info['pid'],
                            'name': proc.info['name'],
                            'cmdline': ' '.join(proc.info.get('cmdline', []))
                        }
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

        except Exception as e:
            logger.error(f"Error checking PostgreSQL process: {e}")

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

    def _find_postgresql_installation_paths(self, service_info: PostgreSQLServiceInfo):
        """Find PostgreSQL data directory and configuration files"""
        try:
            # Check common data directory paths
            for path_pattern in self.COMMON_DATA_PATHS.get(self.system_info.os_type, []):
                if os.path.exists(path_pattern):
                    if self.system_info.os_type == OperatingSystem.LINUX and '*' in path_pattern:
                        # Handle version-specific paths
                        import glob
                        for path in glob.glob(path_pattern):
                            if os.path.exists(path) and os.path.isdir(path):
                                service_info.data_directory = path
                                break
                    else:
                        service_info.data_directory = path_pattern
                    break

            # Check common configuration file paths
            for path_pattern in self.COMMON_CONFIG_PATHS.get(self.system_info.os_type, []):
                if self.system_info.os_type == OperatingSystem.LINUX and '*' in path_pattern:
                    # Handle version-specific paths
                    import glob
                    for path in glob.glob(path_pattern):
                        if os.path.exists(path):
                            service_info.config_file = path
                            break
                else:
                    if os.path.exists(path_pattern):
                        service_info.config_file = path_pattern
                        break

        except Exception as e:
            logger.error(f"Error finding PostgreSQL installation paths: {e}")

    def _extract_windows_postgresql_service_info(self, sc_output: str, service_info: PostgreSQLServiceInfo):
        """Extract additional service information from sc query output"""
        try:
            for line in sc_output.split('\n'):
                if 'SERVICE_NAME:' in line:
                    service_info.service_name = line.split(':')[1].strip()
                elif 'STATE:' in line:
                    # Additional state parsing if needed
                    pass
        except Exception as e:
            logger.error(f"Error extracting Windows PostgreSQL service info: {e}")

    def _extract_systemd_postgresql_service_info(self, service_name: str, service_info: PostgreSQLServiceInfo):
        """Extract additional service information from systemctl"""
        try:
            # Get service status details
            result = subprocess.run(
                ['systemctl', 'show', service_name, '--property=ExecStart,FragmentPath,Environment'],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if line.startswith('ExecStart='):
                        exec_start = line.split('=', 1)[1]
                        service_info.data_directory = self._extract_data_dir_from_command(exec_start)
                    elif line.startswith('FragmentPath='):
                        service_path = line.split('=', 1)[1]
                        service_info.config_file = service_path
                    elif line.startswith('Environment=PGDATA='):
                        data_dir = line.split('=', 1)[1]
                        service_info.data_directory = data_dir

        except Exception as e:
            logger.error(f"Error extracting systemd PostgreSQL service info: {e}")

    def _extract_data_dir_from_command(self, command: str) -> Optional[str]:
        """Extract data directory from PostgreSQL command"""
        try:
            # Look for -D argument (data directory)
            parts = command.split()
            for i, part in enumerate(parts):
                if part == '-D' and i + 1 < len(parts):
                    return parts[i + 1]
                elif part.startswith('-D'):
                    return part[2:]
        except Exception as e:
            logger.error(f"Error extracting data directory from command: {e}")

        return None

    def _get_docker_postgresql_version(self, container_name: str) -> Optional[PostgreSQLVersion]:
        """Get PostgreSQL version from Docker container"""
        try:
            result = subprocess.run(
                ['docker', 'exec', container_name, 'psql', '--version'],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                return self._parse_postgresql_version(result.stdout)

        except Exception as e:
            logger.error(f"Error getting Docker PostgreSQL version: {e}")

        return None

    def _parse_postgresql_version(self, version_str: str) -> Optional[PostgreSQLVersion]:
        """Parse PostgreSQL version string"""
        try:
            # Match version patterns like "PostgreSQL 13.4" or "PostgreSQL 14.0 (Debian 14.0-1)"
            match = re.search(r'PostgreSQL (\d+)\.(\d+)(?:\.(\d+))?', version_str)
            if match:
                major = int(match.group(1))
                minor = int(match.group(2))
                patch = int(match.group(3)) if match.group(3) else 0

                version = PostgreSQLVersion(
                    major=major,
                    minor=minor,
                    patch=patch,
                    full_version=f"{major}.{minor}.{patch}",
                    is_compatible=(major, minor) >= self.MINIMUM_SUPPORTED_VERSION
                )

                return version

        except Exception as e:
            logger.error(f"Error parsing PostgreSQL version: {e}")

        return None

    def validate_postgresql_configuration(self, config: PostgreSQLConnectionConfig) -> Tuple[bool, List[str]]:
        """
        Validate PostgreSQL connection configuration.

        Args:
            config: PostgreSQL connection configuration

        Returns:
            Tuple[bool, List[str]]: (is_valid, error_messages)
        """
        errors = []

        # Validate host
        if not config.host:
            errors.append("PostgreSQL host is required")

        # Validate port
        if not isinstance(config.port, int) or config.port < 1 or config.port > 65535:
            errors.append("PostgreSQL port must be an integer between 1 and 65535")

        # Validate database name
        if not config.database:
            errors.append("PostgreSQL database name is required")

        # Validate username
        if not config.username:
            errors.append("PostgreSQL username is required")

        # Validate timeout
        if config.connect_timeout <= 0:
            errors.append("Connection timeout must be greater than 0")

        # Test connection if basic validation passes
        if not errors:
            connection_info = self._test_postgresql_connection(
                config.host,
                config.port,
                config.database,
                config.username,
                config.password
            )
            if not connection_info:
                errors.append(f"Cannot connect to PostgreSQL at {config.host}:{config.port}/{config.database}")

        return len(errors) == 0, errors

    def get_postgresql_info(self, config: Optional[PostgreSQLConnectionConfig] = None) -> Optional[Dict]:
        """
        Get comprehensive PostgreSQL information.

        Args:
            config: Optional PostgreSQL connection configuration

        Returns:
            Dict with PostgreSQL information or None if connection fails
        """
        if config is None:
            # Use detected service info
            service_info = self.detect_postgresql_service()
            config = PostgreSQLConnectionConfig(
                host=service_info.host,
                port=service_info.port,
                database=service_info.database or "postgres",
                username=service_info.username or "postgres"
            )

        if not PSYCOPG2_AVAILABLE:
            logger.warning("psycopg2 package not available for detailed info")
            return None

        try:
            # Build connection string
            conn_string = (
                f"host={config.host} "
                f"port={config.port} "
                f"dbname={config.database} "
                f"user={config.username} "
                f"connect_timeout={config.connect_timeout}"
            )

            if config.password:
                conn_string += f" password={config.password}"

            connection = psycopg2.connect(conn_string)
            connection.autocommit = True

            with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                # Get comprehensive database information
                cursor.execute("""
                    SELECT
                        version() as full_version,
                        current_database() as database_name,
                        current_user() as current_user,
                        inet_server_addr() as server_ip,
                        inet_server_port() as server_port,
                        (SELECT count(*) FROM pg_stat_activity) as active_connections,
                        (SELECT setting FROM pg_settings WHERE name = 'max_connections') as max_connections,
                        (SELECT setting FROM pg_settings WHERE name = 'data_directory') as data_directory,
                        (SELECT setting FROM pg_settings WHERE name = 'config_file') as config_file,
                        (SELECT setting FROM pg_settings WHERE name = 'hba_file') as hba_file,
                        (SELECT setting FROM pg_settings WHERE name = 'shared_buffers') as shared_buffers,
                        (SELECT setting FROM pg_settings WHERE name = 'effective_cache_size') as effective_cache_size,
                        pg_size_pretty(pg_database_size(current_database())) as database_size
                """)
                info = cursor.fetchone()

                # Get database list
                cursor.execute("""
                    SELECT datname, pg_size_pretty(pg_database_size(datname)) as size
                    FROM pg_database
                    WHERE datistemplate = false
                    ORDER BY pg_database_size(datname) DESC
                """)
                databases = cursor.fetchall()

                organized_info = {
                    'server': {
                        'version': self._parse_postgresql_version(info['full_version']).__dict__ if info['full_version'] else None,
                        'full_version': info['full_version'],
                        'server_ip': info['server_ip'],
                        'server_port': info['server_port'],
                        'data_directory': info['data_directory'],
                        'config_file': info['config_file'],
                        'hba_file': info['hba_file']
                    },
                    'connection': {
                        'database_name': info['database_name'],
                        'current_user': info['current_user'],
                        'database_size': info['database_size']
                    },
                    'performance': {
                        'active_connections': info['active_connections'],
                        'max_connections': int(info['max_connections']),
                        'shared_buffers': info['shared_buffers'],
                        'effective_cache_size': info['effective_cache_size']
                    },
                    'databases': [dict(db) for db in databases]
                }

            connection.close()
            return organized_info

        except Exception as e:
            logger.error(f"Error getting PostgreSQL info: {e}")
            return None

    def check_version_compatibility(self, version_str: str) -> Tuple[bool, str]:
        """
        Check if PostgreSQL version meets minimum requirements.

        Args:
            version_str: PostgreSQL version string

        Returns:
            Tuple[bool, str]: (is_compatible, message)
        """
        try:
            parsed_version = self._parse_postgresql_version(version_str)
            if not parsed_version:
                return False, f"Unable to parse version: {version_str}"

            if not parsed_version.is_compatible:
                min_version_str = f"{self.MINIMUM_SUPPORTED_VERSION[0]}.{self.MINIMUM_SUPPORTED_VERSION[1]}"
                return False, f"PostgreSQL {parsed_version} is not supported. Minimum version: {min_version_str}"

            return True, f"PostgreSQL {parsed_version} is compatible"

        except Exception as e:
            logger.error(f"Error checking version compatibility: {e}")
            return False, f"Error checking version compatibility: {str(e)}"

    def start_postgresql_service(self) -> Tuple[bool, str]:
        """
        Attempt to start PostgreSQL service using platform-specific commands.

        Returns:
            Tuple[bool, str]: (success, message)
        """
        logger.info("Attempting to start PostgreSQL service")

        try:
            if self.system_info.os_type == OperatingSystem.WINDOWS:
                return self._start_windows_postgresql()
            elif self.system_info.os_type == OperatingSystem.MACOS:
                return self._start_macos_postgresql()
            elif self.system_info.os_type == OperatingSystem.LINUX:
                return self._start_linux_postgresql()
            else:
                return False, f"Starting PostgreSQL service not supported on {self.system_info.os_type.value}"

        except Exception as e:
            logger.error(f"Error starting PostgreSQL service: {e}")
            return False, f"Error starting PostgreSQL service: {str(e)}"

    def _start_windows_postgresql(self) -> Tuple[bool, str]:
        """Start PostgreSQL service on Windows"""
        try:
            service_info = self._detect_windows_postgresql_service()
            if service_info.service_name:
                result = subprocess.run(
                    ['sc', 'start', service_info.service_name],
                    capture_output=True,
                    text=True,
                    timeout=30
                )

                if result.returncode == 0:
                    return True, f"PostgreSQL service '{service_info.service_name}' started successfully"
                else:
                    return False, f"Failed to start PostgreSQL service: {result.stderr}"
            else:
                return False, "PostgreSQL service not found on Windows"

        except Exception as e:
            return False, f"Error starting Windows PostgreSQL service: {str(e)}"

    def _start_macos_postgresql(self) -> Tuple[bool, str]:
        """Start PostgreSQL service on macOS"""
        try:
            result = subprocess.run(
                ['brew', 'services', 'start', 'postgresql'],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                return True, "PostgreSQL service started via brew services"
            else:
                return False, f"Failed to start PostgreSQL via brew: {result.stderr}"

        except Exception as e:
            return False, f"Error starting macOS PostgreSQL service: {str(e)}"

    def _start_linux_postgresql(self) -> Tuple[bool, str]:
        """Start PostgreSQL service on Linux"""
        try:
            # Try systemctl first
            result = subprocess.run(
                ['systemctl', 'start', 'postgresql'],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                return True, "PostgreSQL service started via systemctl"
            else:
                # Try service command
                result = subprocess.run(
                    ['service', 'postgresql', 'start'],
                    capture_output=True,
                    text=True,
                    timeout=30
                )

                if result.returncode == 0:
                    return True, "PostgreSQL service started via service command"
                else:
                    return False, f"Failed to start PostgreSQL service: {result.stderr}"

        except Exception as e:
            return False, f"Error starting Linux PostgreSQL service: {str(e)}"