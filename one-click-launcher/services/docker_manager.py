"""
Docker Environment Detection and Management Module

This module provides comprehensive Docker environment detection and management capabilities
including Docker installation verification, container management, and Docker network/volume configuration.
"""

import os
import sys
import subprocess
import platform
import re
import json
import time
import shutil
from typing import Dict, List, Optional, Tuple, Union, Any
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path

# Import required modules
try:
    import docker
    DOCKER_PY_AVAILABLE = True
except ImportError:
    DOCKER_PY_AVAILABLE = False

from utils.logger import get_logger
from core.operating_system_detector import OperatingSystem, Architecture, OperatingSystemDetector

logger = get_logger(__name__)


class DockerStatus(Enum):
    """Docker status values"""
    RUNNING = "running"
    STOPPED = "stopped"
    INSTALLING = "installing"
    ERROR = "error"
    NOT_INSTALLED = "not_installed"
    UNKNOWN = "unknown"


class ContainerStatus(Enum):
    """Docker container status values"""
    RUNNING = "running"
    STOPPED = "stopped"
    PAUSED = "paused"
    RESTARTING = "restarting"
    REMOVING = "removing"
    DEAD = "dead"
    CREATED = "created"
    EXITED = "exited"
    NOT_FOUND = "not_found"
    UNKNOWN = "unknown"


@dataclass
class DockerInfo:
    """Docker installation and runtime information"""
    status: DockerStatus
    version: Optional[str] = None
    api_version: Optional[str] = None
    docker_compose_version: Optional[str] = None
    total_containers: int = 0
    running_containers: int = 0
    total_images: int = 0
    total_volumes: int = 0
    total_networks: int = 0
    docker_daemon_running: bool = False
    docker_socket_path: Optional[str] = None
    error_message: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        result = asdict(self)
        result['status'] = self.status.value
        return result


@dataclass
class ContainerInfo:
    """Docker container information"""
    container_id: str
    name: str
    image: str
    status: ContainerStatus
    ports: Dict[str, str]
    volumes: List[str]
    networks: List[str]
    created_at: Optional[str] = None
    started_at: Optional[str] = None
    environment: Optional[Dict[str, str]] = None
    labels: Optional[Dict[str, str]] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        result = asdict(self)
        result['status'] = self.status.value
        return result


@dataclass
class DockerContainerConfig:
    """Docker container configuration"""
    image: str
    name: str
    ports: Dict[str, int]  # container_port: host_port
    environment: Optional[Dict[str, str]] = None
    volumes: Optional[Dict[str, str]] = None  # host_path: container_path
    networks: Optional[List[str]] = None
    restart_policy: str = "unless-stopped"
    detach: bool = True
    auto_remove: bool = False

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)


@dataclass
class DockerVolumeConfig:
    """Docker volume configuration"""
    name: str
    driver: str = "local"
    driver_opts: Optional[Dict[str, str]] = None
    labels: Optional[Dict[str, str]] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)


@dataclass
class DockerNetworkConfig:
    """Docker network configuration"""
    name: str
    driver: str = "bridge"
    subnet: Optional[str] = None
    gateway: Optional[str] = None
    labels: Optional[Dict[str, str]] = None
    internal: bool = False

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)


class DockerManager:
    """
    Comprehensive Docker environment detection and management.

    Features:
    - Docker installation detection and version checking
    - Docker daemon status monitoring
    - Container management (start, stop, restart, remove)
    - Volume and network management
    - Database container management (Redis, PostgreSQL)
    - Cross-platform Docker support
    """

    # Default Docker settings
    DEFAULT_DOCKER_SOCKET = "/var/run/docker.sock"
    DEFAULT_DOCKER_HOST = "unix:///var/run/docker.sock"
    CONTAINER_START_TIMEOUT = 30
    CONTAINER_STOP_TIMEOUT = 10

    # Database container image patterns
    REDIS_IMAGES = ["redis:latest", "redis:7", "redis:6", "redis:alpine"]
    POSTGRESQL_IMAGES = ["postgres:latest", "postgres:15", "postgres:14", "postgres:13"]

    # Container name patterns
    DATABASE_CONTAINER_PATTERNS = [
        "redis", "postgresql", "postgres", "db", "database",
        "redis-container", "postgres-container", "db-container"
    ]

    def __init__(self):
        """Initialize Docker Manager"""
        self.os_detector = OperatingSystemDetector()
        self.system_info = self.os_detector.detect_os()
        self._docker_client = None

        logger.info(f"DockerManager initialized for {self.system_info.os_type.value} {self.system_info.architecture.value}")

    def detect_docker_environment(self) -> DockerInfo:
        """
        Detect Docker installation and runtime status.

        Returns:
            DockerInfo: Comprehensive Docker environment information
        """
        logger.info("Starting Docker environment detection")

        docker_info = DockerInfo(status=DockerStatus.UNKNOWN)

        try:
            # Check Docker CLI availability
            version_result = subprocess.run(
                ['docker', '--version'],
                capture_output=True,
                text=True,
                timeout=10
            )

            if version_result.returncode != 0:
                docker_info.status = DockerStatus.NOT_INSTALLED
                docker_info.error_message = "Docker CLI not found"
                return docker_info

            # Parse Docker version
            docker_info.version = self._parse_docker_version(version_result.stdout)

            # Check Docker daemon status
            daemon_result = subprocess.run(
                ['docker', 'info'],
                capture_output=True,
                text=True,
                timeout=15
            )

            if daemon_result.returncode == 0:
                docker_info.status = DockerStatus.RUNNING
                docker_info.docker_daemon_running = True

                # Parse additional Docker info
                self._parse_docker_info(daemon_result.stdout, docker_info)
            else:
                docker_info.status = DockerStatus.STOPPED
                docker_info.docker_daemon_running = False
                docker_info.error_message = "Docker daemon not running"

            # Check Docker Compose
            compose_result = subprocess.run(
                ['docker-compose', '--version'],
                capture_output=True,
                text=True,
                timeout=10
            )

            if compose_result.returncode == 0:
                docker_info.docker_compose_version = self._parse_docker_compose_version(compose_result.stdout)

            # Get container and resource statistics
            self._get_docker_statistics(docker_info)

        except subprocess.TimeoutExpired:
            docker_info.status = DockerStatus.ERROR
            docker_info.error_message = "Docker command timeout"
        except FileNotFoundError:
            docker_info.status = DockerStatus.NOT_INSTALLED
            docker_info.error_message = "Docker CLI not found"
        except Exception as e:
            docker_info.status = DockerStatus.ERROR
            docker_info.error_message = f"Error detecting Docker: {str(e)}"
            logger.error(f"Error detecting Docker environment: {e}")

        logger.info(f"Docker environment detection completed: {docker_info.status.value}")
        return docker_info

    def detect_database_containers(self) -> List[ContainerInfo]:
        """
        Detect database containers (Redis, PostgreSQL) running in Docker.

        Returns:
            List[ContainerInfo]: List of database containers
        """
        logger.info("Detecting database containers")

        containers = []

        try:
            # Get all running containers
            result = subprocess.run(
                ['docker', 'ps', '--format', 'json'],
                capture_output=True,
                text=True,
                timeout=15
            )

            if result.returncode == 0:
                container_lines = result.stdout.strip().split('\n')

                for container_line in container_lines:
                    if not container_line.strip():
                        continue

                    try:
                        container_data = json.loads(container_line)
                        container_info = self._parse_container_info(container_data)

                        # Check if this is a database container
                        if self._is_database_container(container_info):
                            containers.append(container_info)

                    except json.JSONDecodeError as e:
                        logger.warning(f"Error parsing container JSON: {e}")
                        continue

            # Also check stopped containers
            stopped_result = subprocess.run(
                ['docker', 'ps', '-a', '--format', 'json'],
                capture_output=True,
                text=True,
                timeout=15
            )

            if stopped_result.returncode == 0:
                container_lines = stopped_result.stdout.strip().split('\n')

                for container_line in container_lines:
                    if not container_line.strip():
                        continue

                    try:
                        container_data = json.loads(container_line)
                        container_info = self._parse_container_info(container_data)

                        # Only add stopped database containers not already in the list
                        if (self._is_database_container(container_info) and
                            container_info.status == ContainerStatus.STOPPED and
                            not any(c.container_id == container_info.container_id for c in containers)):
                            containers.append(container_info)

                    except json.JSONDecodeError as e:
                        logger.warning(f"Error parsing stopped container JSON: {e}")
                        continue

        except subprocess.TimeoutExpired:
            logger.warning("Timeout detecting database containers")
        except Exception as e:
            logger.error(f"Error detecting database containers: {e}")

        logger.info(f"Found {len(containers)} database containers")
        return containers

    def create_redis_container(self, config: DockerContainerConfig) -> Tuple[bool, str]:
        """
        Create and start a Redis container.

        Args:
            config: Container configuration

        Returns:
            Tuple[bool, str]: (success, message)
        """
        logger.info(f"Creating Redis container: {config.name}")

        try:
            # Use default Redis image if not specified
            if not config.image:
                config.image = self.REDIS_IMAGES[0]

            # Build docker run command
            cmd = ['docker', 'run']

            if config.detach:
                cmd.append('-d')

            if config.auto_remove:
                cmd.append('--rm')

            # Add restart policy
            cmd.extend(['--restart', config.restart_policy])

            # Add name
            cmd.extend(['--name', config.name])

            # Add ports
            for container_port, host_port in config.ports.items():
                cmd.extend(['-p', f"{host_port}:{container_port}"])

            # Add environment variables
            if config.environment:
                for key, value in config.environment.items():
                    cmd.extend(['-e', f"{key}={value}"])

            # Add volumes
            if config.volumes:
                for host_path, container_path in config.volumes.items():
                    cmd.extend(['-v', f"{host_path}:{container_path}"])

            # Add networks
            if config.networks:
                for network in config.networks:
                    cmd.extend(['--network', network])

            # Add image
            cmd.append(config.image)

            # Run container
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=self.CONTAINER_START_TIMEOUT)

            if result.returncode == 0:
                container_id = result.stdout.strip()
                logger.info(f"Redis container created successfully: {container_id}")
                return True, f"Redis container '{config.name}' created successfully"
            else:
                error_msg = result.stderr.strip()
                logger.error(f"Failed to create Redis container: {error_msg}")
                return False, f"Failed to create Redis container: {error_msg}"

        except subprocess.TimeoutExpired:
            error_msg = f"Timeout creating Redis container '{config.name}'"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Error creating Redis container: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def create_postgresql_container(self, config: DockerContainerConfig) -> Tuple[bool, str]:
        """
        Create and start a PostgreSQL container.

        Args:
            config: Container configuration

        Returns:
            Tuple[bool, str]: (success, message)
        """
        logger.info(f"Creating PostgreSQL container: {config.name}")

        try:
            # Use default PostgreSQL image if not specified
            if not config.image:
                config.image = self.POSTGRESQL_IMAGES[0]

            # Set default environment variables for PostgreSQL
            if not config.environment:
                config.environment = {}

            if 'POSTGRES_DB' not in config.environment:
                config.environment['POSTGRES_DB'] = 'postgres'
            if 'POSTGRES_USER' not in config.environment:
                config.environment['POSTGRES_USER'] = 'postgres'
            if 'POSTGRES_PASSWORD' not in config.environment:
                config.environment['POSTGRES_PASSWORD'] = 'postgres'

            # Build docker run command
            cmd = ['docker', 'run']

            if config.detach:
                cmd.append('-d')

            if config.auto_remove:
                cmd.append('--rm')

            # Add restart policy
            cmd.extend(['--restart', config.restart_policy])

            # Add name
            cmd.extend(['--name', config.name])

            # Add ports
            for container_port, host_port in config.ports.items():
                cmd.extend(['-p', f"{host_port}:{container_port}"])

            # Add environment variables
            for key, value in config.environment.items():
                cmd.extend(['-e', f"{key}={value}"])

            # Add volumes
            if config.volumes:
                for host_path, container_path in config.volumes.items():
                    cmd.extend(['-v', f"{host_path}:{container_path}"])

            # Add networks
            if config.networks:
                for network in config.networks:
                    cmd.extend(['--network', network])

            # Add image
            cmd.append(config.image)

            # Run container
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=self.CONTAINER_START_TIMEOUT)

            if result.returncode == 0:
                container_id = result.stdout.strip()
                logger.info(f"PostgreSQL container created successfully: {container_id}")
                return True, f"PostgreSQL container '{config.name}' created successfully"
            else:
                error_msg = result.stderr.strip()
                logger.error(f"Failed to create PostgreSQL container: {error_msg}")
                return False, f"Failed to create PostgreSQL container: {error_msg}"

        except subprocess.TimeoutExpired:
            error_msg = f"Timeout creating PostgreSQL container '{config.name}'"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Error creating PostgreSQL container: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def start_container(self, container_name: str) -> Tuple[bool, str]:
        """Start a Docker container"""
        try:
            result = subprocess.run(
                ['docker', 'start', container_name],
                capture_output=True,
                text=True,
                timeout=self.CONTAINER_START_TIMEOUT
            )

            if result.returncode == 0:
                return True, f"Container '{container_name}' started successfully"
            else:
                return False, f"Failed to start container: {result.stderr.strip()}"

        except subprocess.TimeoutExpired:
            return False, f"Timeout starting container '{container_name}'"
        except Exception as e:
            return False, f"Error starting container: {str(e)}"

    def stop_container(self, container_name: str) -> Tuple[bool, str]:
        """Stop a Docker container"""
        try:
            result = subprocess.run(
                ['docker', 'stop', container_name],
                capture_output=True,
                text=True,
                timeout=self.CONTAINER_STOP_TIMEOUT
            )

            if result.returncode == 0:
                return True, f"Container '{container_name}' stopped successfully"
            else:
                return False, f"Failed to stop container: {result.stderr.strip()}"

        except subprocess.TimeoutExpired:
            return False, f"Timeout stopping container '{container_name}'"
        except Exception as e:
            return False, f"Error stopping container: {str(e)}"

    def restart_container(self, container_name: str) -> Tuple[bool, str]:
        """Restart a Docker container"""
        try:
            result = subprocess.run(
                ['docker', 'restart', container_name],
                capture_output=True,
                text=True,
                timeout=self.CONTAINER_START_TIMEOUT
            )

            if result.returncode == 0:
                return True, f"Container '{container_name}' restarted successfully"
            else:
                return False, f"Failed to restart container: {result.stderr.strip()}"

        except subprocess.TimeoutExpired:
            return False, f"Timeout restarting container '{container_name}'"
        except Exception as e:
            return False, f"Error restarting container: {str(e)}"

    def remove_container(self, container_name: str, force: bool = False) -> Tuple[bool, str]:
        """Remove a Docker container"""
        try:
            cmd = ['docker', 'rm']
            if force:
                cmd.append('-f')
            cmd.append(container_name)

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)

            if result.returncode == 0:
                return True, f"Container '{container_name}' removed successfully"
            else:
                return False, f"Failed to remove container: {result.stderr.strip()}"

        except subprocess.TimeoutExpired:
            return False, f"Timeout removing container '{container_name}'"
        except Exception as e:
            return False, f"Error removing container: {str(e)}"

    def create_volume(self, config: DockerVolumeConfig) -> Tuple[bool, str]:
        """Create a Docker volume"""
        try:
            cmd = ['docker', 'volume', 'create']

            # Add driver if not default
            if config.driver != "local":
                cmd.extend(['--driver', config.driver])

            # Add driver options
            if config.driver_opts:
                for key, value in config.driver_opts.items():
                    cmd.extend(['--opt', f"{key}={value}"])

            # Add labels
            if config.labels:
                for key, value in config.labels.items():
                    cmd.extend(['--label', f"{key}={value}"])

            # Add volume name
            cmd.append(config.name)

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)

            if result.returncode == 0:
                return True, f"Volume '{config.name}' created successfully"
            else:
                return False, f"Failed to create volume: {result.stderr.strip()}"

        except subprocess.TimeoutExpired:
            return False, f"Timeout creating volume '{config.name}'"
        except Exception as e:
            return False, f"Error creating volume: {str(e)}"

    def create_network(self, config: DockerNetworkConfig) -> Tuple[bool, str]:
        """Create a Docker network"""
        try:
            cmd = ['docker', 'network', 'create']

            # Add driver if not default
            if config.driver != "bridge":
                cmd.extend(['--driver', config.driver])

            # Add subnet
            if config.subnet:
                cmd.extend(['--subnet', config.subnet])

            # Add gateway
            if config.gateway:
                cmd.extend(['--gateway', config.gateway])

            # Add internal flag
            if config.internal:
                cmd.append('--internal')

            # Add labels
            if config.labels:
                for key, value in config.labels.items():
                    cmd.extend(['--label', f"{key}={value}"])

            # Add network name
            cmd.append(config.name)

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)

            if result.returncode == 0:
                return True, f"Network '{config.name}' created successfully"
            else:
                return False, f"Failed to create network: {result.stderr.strip()}"

        except subprocess.TimeoutExpired:
            return False, f"Timeout creating network '{config.name}'"
        except Exception as e:
            return False, f"Error creating network: {str(e)}"

    def list_volumes(self) -> List[Dict]:
        """List Docker volumes"""
        try:
            result = subprocess.run(
                ['docker', 'volume', 'ls', '--format', 'json'],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                volumes = []
                for line in result.stdout.strip().split('\n'):
                    if line.strip():
                        try:
                            volume_data = json.loads(line)
                            volumes.append(volume_data)
                        except json.JSONDecodeError:
                            continue
                return volumes
            else:
                return []

        except Exception as e:
            logger.error(f"Error listing volumes: {e}")
            return []

    def list_networks(self) -> List[Dict]:
        """List Docker networks"""
        try:
            result = subprocess.run(
                ['docker', 'network', 'ls', '--format', 'json'],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                networks = []
                for line in result.stdout.strip().split('\n'):
                    if line.strip():
                        try:
                            network_data = json.loads(line)
                            networks.append(network_data)
                        except json.JSONDecodeError:
                            continue
                return networks
            else:
                return []

        except Exception as e:
            logger.error(f"Error listing networks: {e}")
            return []

    def get_container_logs(self, container_name: str, tail: int = 50) -> str:
        """Get container logs"""
        try:
            result = subprocess.run(
                ['docker', 'logs', '--tail', str(tail), container_name],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                return result.stdout
            else:
                return f"Error getting logs: {result.stderr.strip()}"

        except subprocess.TimeoutExpired:
            return f"Timeout getting logs for container '{container_name}'"
        except Exception as e:
            return f"Error getting logs: {str(e)}"

    def _parse_docker_version(self, version_str: str) -> str:
        """Parse Docker version string"""
        try:
            match = re.search(r'Docker version (\d+\.\d+\.\d+)', version_str)
            if match:
                return match.group(1)
        except Exception as e:
            logger.error(f"Error parsing Docker version: {e}")
        return version_str.strip()

    def _parse_docker_compose_version(self, version_str: str) -> str:
        """Parse Docker Compose version string"""
        try:
            match = re.search(r'docker-compose version (\d+\.\d+\.\d+)', version_str)
            if match:
                return match.group(1)
        except Exception as e:
            logger.error(f"Error parsing Docker Compose version: {e}")
        return version_str.strip()

    def _parse_docker_info(self, info_str: str, docker_info: DockerInfo):
        """Parse Docker info output"""
        try:
            lines = info_str.split('\n')
            for line in lines:
                if 'Server Version:' in line:
                    docker_info.api_version = line.split(':')[1].strip()
                elif 'Docker Root Dir:' in line:
                    pass  # Could store root directory if needed
        except Exception as e:
            logger.error(f"Error parsing Docker info: {e}")

    def _get_docker_statistics(self, docker_info: DockerInfo):
        """Get Docker statistics (containers, images, volumes, networks)"""
        try:
            # Get container count
            containers_result = subprocess.run(
                ['docker', 'ps', '-a', '--format', '{{.ID}}'],
                capture_output=True,
                text=True,
                timeout=10
            )
            if containers_result.returncode == 0:
                docker_info.total_containers = len([line for line in containers_result.stdout.strip().split('\n') if line.strip()])

            # Get running container count
            running_result = subprocess.run(
                ['docker', 'ps', '--format', '{{.ID}}'],
                capture_output=True,
                text=True,
                timeout=10
            )
            if running_result.returncode == 0:
                docker_info.running_containers = len([line for line in running_result.stdout.strip().split('\n') if line.strip()])

            # Get image count
            images_result = subprocess.run(
                ['docker', 'images', '--format', '{{.ID}}'],
                capture_output=True,
                text=True,
                timeout=10
            )
            if images_result.returncode == 0:
                docker_info.total_images = len([line for line in images_result.stdout.strip().split('\n') if line.strip()])

            # Get volume count
            volumes_result = subprocess.run(
                ['docker', 'volume', 'ls', '--format', '{{.Name}}'],
                capture_output=True,
                text=True,
                timeout=10
            )
            if volumes_result.returncode == 0:
                docker_info.total_volumes = len([line for line in volumes_result.stdout.strip().split('\n') if line.strip()])

            # Get network count
            networks_result = subprocess.run(
                ['docker', 'network', 'ls', '--format', '{{.Name}}'],
                capture_output=True,
                text=True,
                timeout=10
            )
            if networks_result.returncode == 0:
                docker_info.total_networks = len([line for line in networks_result.stdout.strip().split('\n') if line.strip()])

        except Exception as e:
            logger.error(f"Error getting Docker statistics: {e}")

    def _parse_container_info(self, container_data: Dict) -> ContainerInfo:
        """Parse container information from Docker output"""
        try:
            # Parse status
            status_str = container_data.get('Status', '').lower()
            if 'running' in status_str:
                status = ContainerStatus.RUNNING
            elif 'stopped' in status_str or 'exited' in status_str:
                status = ContainerStatus.STOPPED
            elif 'paused' in status_str:
                status = ContainerStatus.PAUSED
            elif 'restarting' in status_str:
                status = ContainerStatus.RESTARTING
            elif 'removing' in status_str:
                status = ContainerStatus.REMOVING
            elif 'dead' in status_str:
                status = ContainerStatus.DEAD
            elif 'created' in status_str:
                status = ContainerStatus.CREATED
            else:
                status = ContainerStatus.UNKNOWN

            # Parse ports
            ports = {}
            ports_str = container_data.get('Ports', '')
            if ports_str:
                for port_mapping in ports_str.split(','):
                    if '->' in port_mapping:
                        parts = port_mapping.strip().split('->')
                        if len(parts) == 2:
                            host_port = parts[0].split(':')[0]
                            container_port = parts[1].split('/')[0]
                            ports[container_port] = host_port

            # Parse volumes
            volumes = []
            volumes_str = container_data.get('Mounts', '')
            if volumes_str:
                # This would need more sophisticated parsing for complex mount structures
                pass

            # Parse networks
            networks = []
            networks_str = container_data.get('Networks', '')
            if networks_str:
                networks = [network.strip() for network in networks_str.split(',') if network.strip()]

            return ContainerInfo(
                container_id=container_data.get('ID', ''),
                name=container_data.get('Names', ''),
                image=container_data.get('Image', ''),
                status=status,
                ports=ports,
                volumes=volumes,
                networks=networks,
                created_at=container_data.get('CreatedAt'),
                started_at=None  # Would need additional parsing
            )

        except Exception as e:
            logger.error(f"Error parsing container info: {e}")
            return ContainerInfo(
                container_id='',
                name='',
                image='',
                status=ContainerStatus.UNKNOWN,
                ports={},
                volumes=[],
                networks=[]
            )

    def _is_database_container(self, container_info: ContainerInfo) -> bool:
        """Check if a container is a database container"""
        image_lower = container_info.image.lower()
        name_lower = container_info.name.lower()

        # Check image names
        if 'redis' in image_lower or 'postgres' in image_lower:
            return True

        # Check container names
        for pattern in self.DATABASE_CONTAINER_PATTERNS:
            if pattern in name_lower:
                return True

        return False

    def validate_docker_environment(self) -> Tuple[bool, List[str]]:
        """
        Validate Docker environment setup.

        Returns:
            Tuple[bool, List[str]]: (is_valid, error_messages)
        """
        errors = []

        try:
            # Check Docker CLI
            result = subprocess.run(
                ['docker', '--version'],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                errors.append("Docker CLI is not installed or not in PATH")
            else:
                # Check Docker daemon
                daemon_result = subprocess.run(
                    ['docker', 'info'],
                    capture_output=True,
                    text=True,
                    timeout=15
                )

                if daemon_result.returncode != 0:
                    errors.append("Docker daemon is not running")

        except subprocess.TimeoutExpired:
            errors.append("Docker commands are timing out")
        except FileNotFoundError:
            errors.append("Docker CLI is not installed")
        except Exception as e:
            errors.append(f"Error validating Docker environment: {str(e)}")

        return len(errors) == 0, errors