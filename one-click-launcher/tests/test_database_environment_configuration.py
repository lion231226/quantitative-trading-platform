"""
Comprehensive tests for database environment configuration module.

This test suite covers:
- Redis service detection and management
- PostgreSQL service detection and management
- Docker environment integration
- Database configuration management
- Database installation options
- Integration testing for complete workflow
"""

import pytest
import unittest
from unittest.mock import Mock, patch, MagicMock, call
import tempfile
import os
import sys
import json
import subprocess
import socket
from pathlib import Path

# Add the parent directory to the path to import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from services.redis_service_manager import (
    RedisServiceManager, RedisServiceStatus, RedisConnectionType,
    RedisServiceInfo, RedisConnectionConfig
)
from services.postgresql_service_manager import (
    PostgreSQLServiceManager, PostgreSQLServiceStatus, PostgreSQLConnectionType,
    PostgreSQLServiceInfo, PostgreSQLConnectionConfig, PostgreSQLVersion
)
from services.docker_manager import (
    DockerManager, DockerStatus, ContainerStatus, ContainerInfo,
    DockerContainerConfig, DockerVolumeConfig, DockerNetworkConfig
)
from core.database_configurator import (
    DatabaseConfigurator, DatabaseType, ConfigurationMode,
    DatabaseConfiguration, SecurityConfig, PortMapping
)
from services.database_installer import (
    DatabaseInstaller, InstallationMethod, InstallationStatus,
    InstallationOptions, InstallationResult, InstallationProgress
)
from core.operating_system_detector import OperatingSystem, Architecture


class TestRedisServiceManager(unittest.TestCase):
    """Test Redis service detection and management"""

    def setUp(self):
        """Set up test fixtures"""
        with patch('services.redis_service_manager.OperatingSystemDetector'):
            self.redis_manager = RedisServiceManager()
            self.redis_manager.system_info = Mock()
            self.redis_manager.system_info.os_type = OperatingSystem.LINUX

    def test_detect_redis_service_running_linux(self):
        """Test Redis service detection on Linux when running"""
        # Mock Docker detection to fail (docker --version fails)
        mock_docker_fail = Mock()
        mock_docker_fail.returncode = 1
        mock_docker_fail.stdout = ""

        # Mock systemctl list-unit-files to show service exists
        mock_exists_result = Mock()
        mock_exists_result.returncode = 0
        mock_exists_result.stdout = "redis-server.service"

        # Mock systemctl is-active to show service is active
        mock_status_result = Mock()
        mock_status_result.returncode = 0
        mock_status_result.stdout = "active"

        # Need to mock: Docker detection (2 calls) + Linux service detection (9 calls) = 11 calls total
        mock_results = [
            mock_docker_fail, Mock(),  # Docker detection fails (--version and ps)
            mock_exists_result, mock_status_result, Mock(),  # redis-server (found)
            Mock(returncode=1), Mock(returncode=1), Mock(),  # redis (not found)
            Mock(returncode=1), Mock(returncode=1), Mock()   # redis_6379 (not found)
        ]

        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = mock_results
            with patch.object(self.redis_manager, '_check_port_occupancy', return_value={'port': 6379}):
                service_info = self.redis_manager.detect_redis_service()

        self.assertEqual(service_info.status, RedisServiceStatus.RUNNING)
        self.assertEqual(service_info.connection_type, RedisConnectionType.LOCAL)
        self.assertEqual(service_info.port, 6379)

    def test_detect_redis_service_stopped_linux(self):
        """Test Redis service detection on Linux when stopped"""
        # Mock Docker detection to fail (docker --version fails)
        mock_docker_fail = Mock()
        mock_docker_fail.returncode = 1
        mock_docker_fail.stdout = ""

        # Mock systemctl list-unit-files to show service exists
        mock_exists_result = Mock()
        mock_exists_result.returncode = 0
        mock_exists_result.stdout = "redis-server.service"

        # Mock systemctl is-active to show service is inactive
        mock_status_result = Mock()
        mock_status_result.returncode = 0
        mock_status_result.stdout = "inactive"

        # Need to mock: Docker detection (2 calls) + Linux service detection (9 calls) = 11 calls total
        mock_results = [
            mock_docker_fail, Mock(),  # Docker detection fails (--version and ps)
            mock_exists_result, mock_status_result, Mock(),  # redis-server (found)
            Mock(returncode=1), Mock(returncode=1), Mock(),  # redis (not found)
            Mock(returncode=1), Mock(returncode=1), Mock()   # redis_6379 (not found)
        ]

        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = mock_results
            with patch.object(self.redis_manager, '_check_port_occupancy', return_value={'port': 6379}):
                service_info = self.redis_manager.detect_redis_service()

        self.assertEqual(service_info.status, RedisServiceStatus.STOPPED)
        self.assertEqual(service_info.connection_type, RedisConnectionType.LOCAL)

    def test_detect_redis_service_not_installed(self):
        """Test Redis service detection when not installed"""
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "Unit redis.service could not be found"

        with patch('subprocess.run', return_value=mock_result):
            with patch.object(self.redis_manager, '_check_port_occupancy', return_value=None):
                with patch.object(self.redis_manager, '_check_redis_process', return_value=None):
                    service_info = self.redis_manager.detect_redis_service()

        self.assertEqual(service_info.status, RedisServiceStatus.NOT_INSTALLED)

    def test_detect_redis_windows_service(self):
        """Test Redis service detection on Windows"""
        self.redis_manager.system_info.os_type = OperatingSystem.WINDOWS

        mock_sc_result = Mock()
        mock_sc_result.returncode = 0
        mock_sc_result.stdout = "SERVICE_NAME: Redis\nSTATE: 4  RUNNING"

        with patch('subprocess.run', return_value=mock_sc_result):
            with patch.object(self.redis_manager, '_check_port_occupancy', return_value={'port': 6379}):
                service_info = self.redis_manager._detect_windows_redis_service()

        self.assertEqual(service_info.status, RedisServiceStatus.RUNNING)
        self.assertEqual(service_info.service_name, "Redis")

    def test_detect_redis_docker_container(self):
        """Test Redis detection in Docker container"""
        mock_docker_result = Mock()
        mock_docker_result.returncode = 0
        mock_docker_result.stdout = '{"Names": "redis-container", "Image": "redis:latest", "Ports": "6379/tcp"}'

        with patch('subprocess.run', return_value=mock_docker_result):
            with patch.object(self.redis_manager, '_get_docker_redis_version', return_value=None):
                service_info = self.redis_manager._detect_docker_redis()

        self.assertIsNotNone(service_info)
        self.assertEqual(service_info.status, RedisServiceStatus.RUNNING)
        self.assertEqual(service_info.connection_type, RedisConnectionType.DOCKER)
        self.assertEqual(service_info.container_name, "redis-container")

    def test_redis_connection_testing(self):
        """Test Redis connection testing"""
        with patch('services.redis_service_manager.REDIS_AVAILABLE', True):
            with patch('redis.Redis') as mock_redis:
                mock_client = Mock()
                mock_redis.return_value = mock_client
                mock_client.ping.return_value = True
                mock_client.info.return_value = {
                    'redis_version': '7.0.0',
                    'uptime_in_seconds': 3600,
                    'used_memory_human': '1.5M',
                    'connected_clients': 5
                }

                service_info = self.redis_manager._test_redis_connection('localhost', 6379)

                self.assertIsNotNone(service_info)
                self.assertEqual(service_info.status, RedisServiceStatus.RUNNING)
                self.assertEqual(service_info.version, '7.0.0')
                self.assertEqual(service_info.uptime_seconds, 3600)

    def test_redis_configuration_validation(self):
        """Test Redis configuration validation"""
        config = RedisConnectionConfig(
            host="localhost",
            port=6379,
            password="testpass"
        )

        with patch.object(self.redis_manager, '_test_redis_connection', return_value=Mock()):
            is_valid, errors = self.redis_manager.validate_redis_configuration(config)

        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

    def test_redis_configuration_validation_invalid_port(self):
        """Test Redis configuration validation with invalid port"""
        config = RedisConnectionConfig(
            host="localhost",
            port=99999,  # Invalid port
            password="testpass"
        )

        is_valid, errors = self.redis_manager.validate_redis_configuration(config)

        self.assertFalse(is_valid)
        self.assertGreater(len(errors), 0)
        self.assertTrue(any("port" in error.lower() for error in errors))

    def test_start_redis_service_linux(self):
        """Test starting Redis service on Linux"""
        self.redis_manager.system_info.os_type = OperatingSystem.LINUX

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Redis started successfully"

        with patch('subprocess.run', return_value=mock_result):
            success, message = self.redis_manager.start_redis_service()

        self.assertTrue(success)
        self.assertIn("started", message)


class TestPostgreSQLServiceManager(unittest.TestCase):
    """Test PostgreSQL service detection and management"""

    def setUp(self):
        """Set up test fixtures"""
        with patch('services.postgresql_service_manager.OperatingSystemDetector'):
            self.postgresql_manager = PostgreSQLServiceManager()
            self.postgresql_manager.system_info = Mock()
            self.postgresql_manager.system_info.os_type = OperatingSystem.LINUX

    def test_detect_postgresql_service_running_linux(self):
        """Test PostgreSQL service detection on Linux when running"""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "postgresql.service - PostgreSQL database\nLoaded: loaded\nActive: active (running)"

        with patch('subprocess.run', return_value=mock_result):
            with patch.object(self.postgresql_manager, '_check_port_occupancy', return_value={'port': 5432}):
                service_info = self.postgresql_manager.detect_postgresql_service()

        self.assertEqual(service_info.status, PostgreSQLServiceStatus.RUNNING)
        self.assertEqual(service_info.connection_type, PostgreSQLConnectionType.LOCAL)
        self.assertEqual(service_info.port, 5432)

    def test_detect_postgresql_service_not_installed(self):
        """Test PostgreSQL service detection when not installed"""
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "Unit postgresql.service could not be found"

        with patch('subprocess.run', return_value=mock_result):
            with patch.object(self.postgresql_manager, '_check_port_occupancy', return_value=None):
                with patch.object(self.postgresql_manager, '_check_postgresql_process', return_value=None):
                    service_info = self.postgresql_manager.detect_postgresql_service()

        self.assertEqual(service_info.status, PostgreSQLServiceStatus.NOT_INSTALLED)

    def test_detect_postgresql_docker_container(self):
        """Test PostgreSQL detection in Docker container"""
        mock_docker_result = Mock()
        mock_docker_result.returncode = 0
        mock_docker_result.stdout = '{"Names": "postgres-container", "Image": "postgres:15", "Ports": "5432/tcp"}'

        with patch('subprocess.run', return_value=mock_docker_result):
            with patch.object(self.postgresql_manager, '_get_docker_postgresql_version',
                            return_value=PostgreSQLVersion(15, 0, 0, "15.0.0")):
                service_info = self.postgresql_manager._detect_docker_postgresql()

        self.assertIsNotNone(service_info)
        self.assertEqual(service_info.status, PostgreSQLServiceStatus.RUNNING)
        self.assertEqual(service_info.connection_type, PostgreSQLConnectionType.DOCKER)
        self.assertEqual(service_info.container_name, "postgres-container")

    def test_postgresql_connection_testing(self):
        """Test PostgreSQL connection testing"""
        # Mock psycopg2 module and set PSYCOPG2_AVAILABLE to True
        mock_psycopg2 = Mock()
        # Add exception classes to the mock
        mock_psycopg2.OperationalError = Exception
        mock_psycopg2.Error = Exception
        mock_psycopg2.extras = Mock()
        mock_psycopg2.extras.RealDictCursor = Mock()  # This is the cursor factory

        with patch.dict('sys.modules', {'psycopg2': mock_psycopg2}):
            # Import the module to patch the variable
            import services.postgresql_service_manager as pg_module
            original_value = pg_module.PSYCOPG2_AVAILABLE
            pg_module.PSYCOPG2_AVAILABLE = True

            try:
                # Mock the connection and cursor
                mock_connect = Mock()
                mock_cursor = Mock()
                mock_psycopg2.connect.return_value = mock_connect
                mock_connect.cursor.return_value = mock_cursor
                mock_connect.autocommit = True

                # Make cursor work as context manager
                mock_cursor.__enter__ = Mock(return_value=mock_cursor)
                mock_cursor.__exit__ = Mock(return_value=None)

                mock_cursor.fetchone.side_effect = [
                    {'version': 'PostgreSQL 15.0'},
                    {'database': 'postgres', 'username': 'postgres', 'current_connections': 5,
                     'max_connections': '100', 'data_directory': '/var/lib/postgresql/data'}
                ]

                service_info = self.postgresql_manager._test_postgresql_connection(
                    'localhost', 5432, 'postgres', 'postgres', 'password'
                )

                # Debug output
                print(f"Service info returned: {service_info}")
                self.assertIsNotNone(service_info)
                self.assertEqual(service_info.status, PostgreSQLServiceStatus.RUNNING)
                self.assertEqual(service_info.database, 'postgres')
                self.assertEqual(service_info.username, 'postgres')

            finally:
                # Restore original value
                pg_module.PSYCOPG2_AVAILABLE = original_value

    def test_postgresql_version_parsing(self):
        """Test PostgreSQL version parsing"""
        version_str = "PostgreSQL 15.3 (Debian 15.3-1.pgdg120+1)"
        version = self.postgresql_manager._parse_postgresql_version(version_str)

        self.assertIsNotNone(version)
        self.assertEqual(version.major, 15)
        self.assertEqual(version.minor, 3)
        self.assertEqual(version.patch, 0)
        self.assertTrue(version.is_compatible)

    def test_postgresql_version_compatibility_check(self):
        """Test PostgreSQL version compatibility checking"""
        # Compatible version
        is_compatible, message = self.postgresql_manager.check_version_compatibility("PostgreSQL 15.0")
        self.assertTrue(is_compatible)
        self.assertIn("compatible", message)

        # Incompatible version
        is_compatible, message = self.postgresql_manager.check_version_compatibility("PostgreSQL 9.6")
        self.assertFalse(is_compatible)
        self.assertIn("not supported", message)

    def test_postgresql_configuration_validation(self):
        """Test PostgreSQL configuration validation"""
        config = PostgreSQLConnectionConfig(
            host="localhost",
            port=5432,
            database="postgres",
            username="postgres",
            password="testpass"
        )

        with patch.object(self.postgresql_manager, '_test_postgresql_connection', return_value=Mock()):
            is_valid, errors = self.postgresql_manager.validate_postgresql_configuration(config)

        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

    def test_start_postgresql_service_linux(self):
        """Test starting PostgreSQL service on Linux"""
        self.postgresql_manager.system_info.os_type = OperatingSystem.LINUX

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "PostgreSQL started successfully"

        with patch('subprocess.run', return_value=mock_result):
            success, message = self.postgresql_manager.start_postgresql_service()

        self.assertTrue(success)
        self.assertIn("started", message)


class TestDockerManager(unittest.TestCase):
    """Test Docker environment detection and management"""

    def setUp(self):
        """Set up test fixtures"""
        with patch('services.docker_manager.OperatingSystemDetector'):
            self.docker_manager = DockerManager()
            self.docker_manager.system_info = Mock()
            self.docker_manager.system_info.os_type = OperatingSystem.LINUX

    def test_detect_docker_environment_running(self):
        """Test Docker environment detection when running"""
        mock_version_result = Mock()
        mock_version_result.returncode = 0
        mock_version_result.stdout = "Docker version 24.0.6"

        mock_info_result = Mock()
        mock_info_result.returncode = 0
        mock_info_result.stdout = "Containers: 5\nImages: 10"

        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = [mock_version_result, mock_info_result, Mock(), Mock(), Mock(), Mock()]
            docker_info = self.docker_manager.detect_docker_environment()

        self.assertEqual(docker_info.status, DockerStatus.RUNNING)
        self.assertEqual(docker_info.version, "24.0.6")
        self.assertTrue(docker_info.docker_daemon_running)

    def test_detect_docker_environment_not_installed(self):
        """Test Docker environment detection when not installed"""
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "docker: command not found"

        with patch('subprocess.run', return_value=mock_result):
            docker_info = self.docker_manager.detect_docker_environment()

        self.assertEqual(docker_info.status, DockerStatus.NOT_INSTALLED)
        self.assertFalse(docker_info.docker_daemon_running)
        self.assertIn("not found", docker_info.error_message)

    def test_detect_database_containers(self):
        """Test detection of database containers"""
        mock_redis_container = '{"Names": "redis-test", "Image": "redis:latest", "Status": "Up 2 hours", "Ports": "6379/tcp"}'
        mock_postgres_container = '{"Names": "postgres-test", "Image": "postgres:15", "Status": "Up 1 hour", "Ports": "5432/tcp"}'

        mock_running_result = Mock()
        mock_running_result.returncode = 0
        mock_running_result.stdout = f"{mock_redis_container}\n{mock_postgres_container}"

        mock_stopped_result = Mock()
        mock_stopped_result.returncode = 0
        mock_stopped_result.stdout = ""

        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = [mock_running_result, mock_stopped_result]
            containers = self.docker_manager.detect_database_containers()

        self.assertEqual(len(containers), 2)
        self.assertIn("redis-test", [c.name for c in containers])
        self.assertIn("postgres-test", [c.name for c in containers])

    def test_create_redis_container(self):
        """Test creating Redis container"""
        config = DockerContainerConfig(
            image="redis:latest",
            name="test-redis",
            ports={6379: 6379},
            environment={"REDIS_PASSWORD": "testpass"}
        )

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "container123"

        with patch('subprocess.run', return_value=mock_result):
            success, message = self.docker_manager.create_redis_container(config)

        self.assertTrue(success)
        self.assertIn("created successfully", message)

    def test_create_postgresql_container(self):
        """Test creating PostgreSQL container"""
        config = DockerContainerConfig(
            image="postgres:15",
            name="test-postgres",
            ports={5432: 5432},
            environment={"POSTGRES_PASSWORD": "testpass"}
        )

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "container456"

        with patch('subprocess.run', return_value=mock_result):
            success, message = self.docker_manager.create_postgresql_container(config)

        self.assertTrue(success)
        self.assertIn("created successfully", message)

    def test_start_stop_container(self):
        """Test starting and stopping containers"""
        mock_start_result = Mock()
        mock_start_result.returncode = 0
        mock_start_result.stdout = "test-container"

        mock_stop_result = Mock()
        mock_stop_result.returncode = 0
        mock_stop_result.stdout = "test-container"

        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = [mock_start_result, mock_stop_result]

            # Test start
            success, message = self.docker_manager.start_container("test-container")
            self.assertTrue(success)
            self.assertIn("started successfully", message)

            # Test stop
            success, message = self.docker_manager.stop_container("test-container")
            self.assertTrue(success)
            self.assertIn("stopped successfully", message)

    def test_create_volume_and_network(self):
        """Test creating Docker volumes and networks"""
        volume_config = DockerVolumeConfig(name="test-volume")
        network_config = DockerNetworkConfig(name="test-network")

        mock_volume_result = Mock()
        mock_volume_result.returncode = 0
        mock_volume_result.stdout = "test-volume"

        mock_network_result = Mock()
        mock_network_result.returncode = 0
        mock_network_result.stdout = "test-network"

        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = [mock_volume_result, mock_network_result]

            # Test volume creation
            success, message = self.docker_manager.create_volume(volume_config)
            self.assertTrue(success)
            self.assertIn("created successfully", message)

            # Test network creation
            success, message = self.docker_manager.create_network(network_config)
            self.assertTrue(success)
            self.assertIn("created successfully", message)

    def test_validate_docker_environment(self):
        """Test Docker environment validation"""
        # Valid environment
        mock_version_result = Mock()
        mock_version_result.returncode = 0
        mock_version_result.stdout = "Docker version 24.0.6"

        mock_info_result = Mock()
        mock_info_result.returncode = 0
        mock_info_result.stdout = "Docker is running"

        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = [mock_version_result, mock_info_result]
            is_valid, errors = self.docker_manager.validate_docker_environment()

        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

        # Invalid environment
        mock_invalid_result = Mock()
        mock_invalid_result.returncode = 1
        mock_invalid_result.stderr = "docker: command not found"

        with patch('subprocess.run', return_value=mock_invalid_result):
            is_valid, errors = self.docker_manager.validate_docker_environment()

        self.assertFalse(is_valid)
        self.assertGreater(len(errors), 0)


class TestDatabaseConfigurator(unittest.TestCase):
    """Test database configuration management"""

    def setUp(self):
        """Set up test fixtures"""
        with patch('core.database_configurator.OperatingSystemDetector'):
            with patch('core.database_configurator.ConfigManager'):
                with patch('core.database_configurator.RedisServiceManager'):
                    with patch('core.database_configurator.PostgreSQLServiceManager'):
                        with patch('core.database_configurator.DockerManager'):
                            self.configurator = DatabaseConfigurator()
                            self.configurator.system_info = Mock()
                            self.configurator.system_info.os_type = OperatingSystem.LINUX

    def test_detect_available_ports(self):
        """Test available port detection"""
        database_types = [DatabaseType.REDIS, DatabaseType.POSTGRESQL]

        with patch.object(self.configurator, '_is_port_available') as mock_port_check:
            # Mock port availability: Redis available, PostgreSQL not available
            def port_available_side_effect(port):
                return port == 6379  # Only Redis port is available

            mock_port_check.side_effect = port_available_side_effect

            with patch.object(self.configurator, '_find_available_port', return_value=5433):
                port_mappings = self.configurator.detect_available_ports(database_types)

        self.assertEqual(len(port_mappings), 2)
        self.assertEqual(port_mappings[DatabaseType.REDIS].actual_port, 6379)
        self.assertFalse(port_mappings[DatabaseType.REDIS].is_conflict)
        self.assertEqual(port_mappings[DatabaseType.POSTGRESQL].actual_port, 5433)
        self.assertTrue(port_mappings[DatabaseType.POSTGRESQL].is_conflict)

    def test_generate_secure_password(self):
        """Test secure password generation"""
        password = self.configurator.generate_secure_password(length=16, include_special=True)

        self.assertEqual(len(password), 16)
        self.assertTrue(any(c.islower() for c in password))  # Has lowercase
        self.assertTrue(any(c.isupper() for c in password))  # Has uppercase
        self.assertTrue(any(c.isdigit() for c in password))  # Has digit
        self.assertTrue(any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password))  # Has special

    def test_configure_data_directory(self):
        """Test data directory configuration"""
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = self.configurator.configure_data_directory(
                DatabaseType.POSTGRESQL,
                custom_path=temp_dir,
                create_if_missing=True
            )

            self.assertEqual(data_dir, temp_dir)
            self.assertTrue(os.path.exists(temp_dir))
            self.assertTrue(os.access(temp_dir, os.W_OK))

    def test_create_database_configuration_local(self):
        """Test creating local database configuration"""
        port_mapping = PortMapping(
            database_type=DatabaseType.POSTGRESQL,
            default_port=5432,
            actual_port=5432,
            is_conflict=False
        )

        data_directory = "/tmp/postgres_data"
        security_config = SecurityConfig(password_length=16)

        with patch.object(self.configurator, 'generate_secure_password', return_value="testpass123"):
            with patch.object(self.configurator, '_generate_config_file_path', return_value="/tmp/postgres.conf"):
                with patch.object(self.configurator, '_generate_config_file'):
                    config = self.configurator.create_database_configuration(
                        database_type=DatabaseType.POSTGRESQL,
                        mode=ConfigurationMode.LOCAL,
                        port_mapping=port_mapping,
                        data_directory=data_directory,
                        security_config=security_config
                    )

        self.assertEqual(config.database_type, DatabaseType.POSTGRESQL)
        self.assertEqual(config.mode, ConfigurationMode.LOCAL)
        self.assertEqual(config.data_directory, data_directory)
        self.assertEqual(config.password, "testpass123")
        self.assertIsInstance(config.connection_config, PostgreSQLConnectionConfig)
        self.assertIsNone(config.docker_config)

    def test_create_database_configuration_docker(self):
        """Test creating Docker database configuration"""
        port_mapping = PortMapping(
            database_type=DatabaseType.REDIS,
            default_port=6379,
            actual_port=6379,
            is_conflict=False
        )

        data_directory = "/tmp/redis_data"
        security_config = SecurityConfig(password_length=16)

        with patch.object(self.configurator, 'generate_secure_password', return_value="testpass123"):
            with patch.object(self.configurator, '_generate_config_file_path', return_value="/tmp/redis.conf"):
                with patch.object(self.configurator, '_generate_config_file'):
                    config = self.configurator.create_database_configuration(
                        database_type=DatabaseType.REDIS,
                        mode=ConfigurationMode.DOCKER,
                        port_mapping=port_mapping,
                        data_directory=data_directory,
                        security_config=security_config
                    )

        self.assertEqual(config.database_type, DatabaseType.REDIS)
        self.assertEqual(config.mode, ConfigurationMode.DOCKER)
        self.assertIsNotNone(config.docker_config)
        self.assertIsNotNone(config.volume_config)
        self.assertIsNotNone(config.network_config)
        self.assertEqual(config.docker_config.name, "redis_container")

    def test_validate_configuration(self):
        """Test configuration validation"""
        # Valid configuration
        config = DatabaseConfiguration(
            database_type=DatabaseType.POSTGRESQL,
            mode=ConfigurationMode.LOCAL,
            connection_config=PostgreSQLConnectionConfig(
                host="localhost",
                port=5432,
                database="postgres",
                username="postgres"
            ),
            data_directory="/tmp/postgres_data",
            config_file="/tmp/postgres.conf"
        )

        with patch.object(self.configurator, '_is_port_available', return_value=True):
            with tempfile.TemporaryDirectory() as temp_dir:
                config.data_directory = temp_dir
                is_valid, errors = self.configurator.validate_configuration(config)

        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

        # Invalid configuration (missing data directory)
        config.data_directory = "/nonexistent/directory"
        is_valid, errors = self.configurator.validate_configuration(config)

        self.assertFalse(is_valid)
        self.assertGreater(len(errors), 0)

    def test_apply_local_configuration(self):
        """Test applying local configuration"""
        config = DatabaseConfiguration(
            database_type=DatabaseType.REDIS,
            mode=ConfigurationMode.LOCAL,
            connection_config=RedisConnectionConfig(host="localhost", port=6379),
            data_directory="/tmp/redis_data",
            config_file="/tmp/redis.conf",
            log_file="/tmp/redis.log",
            pid_file="/tmp/redis.pid"
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            config.data_directory = temp_dir
            config.log_file = os.path.join(temp_dir, "redis.log")
            config.pid_file = os.path.join(temp_dir, "redis.pid")

            success, message = self.configurator.apply_configuration(config)

        self.assertTrue(success)
        self.assertIn("applied", message)

    def test_apply_docker_configuration(self):
        """Test applying Docker configuration"""
        docker_config = DockerContainerConfig(
            image="redis:latest",
            name="test-redis",
            ports={6379: 6379}
        )

        volume_config = DockerVolumeConfig(name="redis_data")
        network_config = DockerNetworkConfig(name="redis_network")

        with tempfile.TemporaryDirectory() as temp_dir:
            config = DatabaseConfiguration(
                database_type=DatabaseType.REDIS,
                mode=ConfigurationMode.DOCKER,
                connection_config=RedisConnectionConfig(host="localhost", port=6379),
                docker_config=docker_config,
                volume_config=volume_config,
                network_config=network_config,
                data_directory=temp_dir,
                config_file=os.path.join(temp_dir, "redis.conf")
            )

            # Mock Docker environment detection
            with patch.object(self.configurator.docker_manager, 'detect_docker_environment', return_value={'available': True, 'version': '20.10.0'}):
                with patch.object(self.configurator.docker_manager, 'create_network', return_value=(True, "Network created")):
                    with patch.object(self.configurator.docker_manager, 'create_volume', return_value=(True, "Volume created")):
                        with patch.object(self.configurator.docker_manager, 'create_redis_container', return_value=(True, "Container created")):
                            success, message = self.configurator.apply_configuration(config)

        self.assertTrue(success)
        self.assertIn("applied", message)


class TestDatabaseInstaller(unittest.TestCase):
    """Test database installation management"""

    def setUp(self):
        """Set up test fixtures"""
        with patch('services.database_installer.OperatingSystemDetector'):
            with patch('services.database_installer.RedisServiceManager'):
                with patch('services.database_installer.PostgreSQLServiceManager'):
                    with patch('services.database_installer.DockerManager'):
                        with patch('services.database_installer.DatabaseConfigurator'):
                            with patch('services.database_installer.ProgressTracker'):
                                self.installer = DatabaseInstaller()
                                self.installer.system_info = Mock()
                                self.installer.system_info.os_type = OperatingSystem.LINUX

    def test_get_available_installation_methods_docker_available(self):
        """Test getting available installation methods when Docker is available"""
        with patch.object(self.installer.docker_manager, 'detect_docker_environment') as mock_docker:
            mock_docker_info = Mock()
            mock_docker_info.status = DockerStatus.RUNNING
            mock_docker.return_value = mock_docker_info

            with patch.object(self.installer, '_can_install_locally', return_value=True):
                methods = self.installer.get_available_installation_methods(DatabaseType.REDIS)

        self.assertIn(InstallationMethod.DOCKER, methods)
        self.assertIn(InstallationMethod.LOCAL, methods)

    def test_select_installation_method_prefer_docker(self):
        """Test installation method selection preferring Docker"""
        with patch.object(self.installer, 'get_available_installation_methods') as mock_methods:
            mock_methods.return_value = [InstallationMethod.DOCKER, InstallationMethod.LOCAL]

            with patch.object(self.installer.docker_manager, 'detect_docker_environment') as mock_docker:
                mock_docker_info = Mock()
                mock_docker_info.status = DockerStatus.RUNNING
                mock_docker.return_value = mock_docker_info

                method, reasoning = self.installer.select_installation_method(DatabaseType.REDIS)

        self.assertEqual(method, InstallationMethod.DOCKER)
        self.assertIn("Docker is running", reasoning)

    def test_install_database_docker_success(self):
        """Test successful Docker database installation"""
        options = InstallationOptions(
            database_type=DatabaseType.REDIS,
            installation_method=InstallationMethod.DOCKER,
            docker_image="redis:latest",
            auto_start=True
        )

        mock_docker_info = Mock()
        mock_docker_info.status = DockerStatus.RUNNING

        with patch.object(self.installer.docker_manager, 'detect_docker_environment', return_value=mock_docker_info):
            with patch.object(self.installer, '_pull_docker_image'):
                with patch.object(self.installer, '_create_docker_volume', return_value="redis_data"):
                    with patch.object(self.installer, '_create_docker_container_config'):
                        with patch.object(self.installer.docker_manager, 'create_redis_container', return_value=(True, "Container created")):
                            with patch.object(self.installer, '_verify_docker_installation', return_value={"status": "running"}):
                                result = self.installer.install_database(options)

        self.assertTrue(result.success)
        self.assertEqual(result.database_type, DatabaseType.REDIS)
        self.assertEqual(result.installation_method, InstallationMethod.DOCKER)

    def test_install_database_local_success(self):
        """Test successful local database installation"""
        options = InstallationOptions(
            database_type=DatabaseType.POSTGRESQL,
            installation_method=InstallationMethod.LOCAL,
            install_directory="/tmp/postgres_install",
            auto_start=True
        )

        with patch.object(self.installer, '_download_database', return_value="/tmp/postgres.tar.gz"):
            with patch.object(self.installer, '_extract_database'):
                with patch.object(self.installer, '_configure_local_database', return_value={"config_path": "/tmp/postgres.conf"}):
                    with patch.object(self.installer, '_perform_local_installation', return_value=True):
                        with patch.object(self.installer, '_start_local_service', return_value=True):
                            with patch.object(self.installer, '_verify_local_installation', return_value={"status": "running"}):
                                result = self.installer.install_database(options)

        self.assertTrue(result.success)
        self.assertEqual(result.database_type, DatabaseType.POSTGRESQL)
        self.assertEqual(result.installation_method, InstallationMethod.LOCAL)

    def test_install_database_validation_error(self):
        """Test database installation with validation error"""
        options = InstallationOptions(
            database_type=DatabaseType.REDIS,
            installation_method=InstallationMethod.DOCKER
        )

        with patch.object(self.installer, '_validate_installation_options', return_value=(False, ["Invalid option"])):
            result = self.installer.install_database(options)

        self.assertFalse(result.success)
        self.assertIn("Invalid installation options", result.error_message)

    def test_check_existing_installation_found(self):
        """Test checking for existing installation when found"""
        mock_service_info = Mock()
        mock_service_info.status = RedisServiceStatus.RUNNING
        mock_service_info.version = "7.0.0"
        mock_service_info.to_dict.return_value = {"status": "running", "port": 6379}

        with patch.object(self.installer.redis_manager, 'detect_redis_service', return_value=mock_service_info):
            existing = self.installer._check_existing_installation(DatabaseType.REDIS)

        self.assertIsNotNone(existing)
        self.assertEqual(existing['version'], "7.0.0")
        self.assertIn('connection_info', existing)

    def test_check_existing_installation_not_found(self):
        """Test checking for existing installation when not found"""
        mock_service_info = Mock()
        mock_service_info.status = RedisServiceStatus.NOT_INSTALLED

        with patch.object(self.installer.redis_manager, 'detect_redis_service', return_value=mock_service_info):
            existing = self.installer._check_existing_installation(DatabaseType.REDIS)

        self.assertIsNone(existing)

    def test_get_installation_progress(self):
        """Test getting installation progress"""
        # Set current progress directly
        test_progress = InstallationProgress(
            status=InstallationStatus.INSTALLING,
            progress_percentage=50.0,
            current_step="Installing database"
        )
        self.installer.current_progress = test_progress

        progress = self.installer.get_installation_progress(DatabaseType.REDIS)

        self.assertIsNotNone(progress)
        self.assertEqual(progress.status, InstallationStatus.INSTALLING)
        self.assertEqual(progress.progress_percentage, 50.0)
        self.assertEqual(progress.current_step, "Installing database")


class TestIntegrationWorkflow(unittest.TestCase):
    """Integration tests for complete database setup workflow"""

    def setUp(self):
        """Set up test fixtures"""
        # Create a mock system info
        mock_system_info = Mock()
        mock_system_info.os_type = OperatingSystem.LINUX
        mock_system_info.architecture = Architecture.X64

        # Mock all external dependencies with detect_os method
        with patch('services.redis_service_manager.OperatingSystemDetector') as mock_redis_os:
            with patch('services.postgresql_service_manager.OperatingSystemDetector') as mock_pg_os:
                with patch('services.docker_manager.OperatingSystemDetector') as mock_docker_os:
                    with patch('core.database_configurator.OperatingSystemDetector') as mock_config_os:
                        with patch('services.database_installer.OperatingSystemDetector') as mock_installer_os:
                            # Configure mocks to return system info
                            mock_redis_os.return_value.detect_os.return_value = mock_system_info
                            mock_pg_os.return_value.detect_os.return_value = mock_system_info
                            mock_docker_os.return_value.detect_os.return_value = mock_system_info
                            mock_config_os.return_value.detect_os.return_value = mock_system_info
                            mock_installer_os.return_value.detect_os.return_value = mock_system_info

                            # Initialize managers
                            self.redis_manager = RedisServiceManager()
                            self.postgresql_manager = PostgreSQLServiceManager()
                            self.docker_manager = DockerManager()
                            self.configurator = DatabaseConfigurator()
                            self.installer = DatabaseInstaller()

                            # Set consistent OS type
                            os_type = OperatingSystem.LINUX
                            for manager in [self.redis_manager, self.postgresql_manager,
                                           self.docker_manager, self.configurator, self.installer]:
                                manager.system_info = Mock()
                                manager.system_info.os_type = os_type

    def test_complete_redis_setup_workflow(self):
        """Test complete Redis setup workflow from detection to installation"""
        # Step 1: Detect existing Redis service
        with patch.object(self.redis_manager, 'detect_redis_service') as mock_detect:
            mock_detect.return_value = Mock(
                status=RedisServiceStatus.NOT_INSTALLED,
                connection_type=RedisConnectionType.LOCAL
            )

            service_info = self.redis_manager.detect_redis_service()
            self.assertEqual(service_info.status, RedisServiceStatus.NOT_INSTALLED)

        # Step 2: Check Docker availability
        with patch.object(self.docker_manager, 'detect_docker_environment') as mock_docker:
            mock_docker_info = Mock()
            mock_docker_info.status = DockerStatus.RUNNING
            mock_docker.return_value = mock_docker_info

            docker_info = self.docker_manager.detect_docker_environment()
            self.assertEqual(docker_info.status, DockerStatus.RUNNING)

        # Step 3: Select installation method
        with patch.object(self.installer, 'get_available_installation_methods') as mock_methods:
            mock_methods.return_value = [InstallationMethod.DOCKER, InstallationMethod.LOCAL]

            with patch.object(self.docker_manager, 'detect_docker_environment', return_value=mock_docker_info):
                method, reasoning = self.installer.select_installation_method(DatabaseType.REDIS)
                self.assertEqual(method, InstallationMethod.DOCKER)

        # Step 4: Configure installation
        with patch.object(self.configurator, 'detect_available_ports') as mock_ports:
            mock_ports.return_value = {
                DatabaseType.REDIS: PortMapping(
                    database_type=DatabaseType.REDIS,
                    default_port=6379,
                    actual_port=6379,
                    is_conflict=False
                )
            }

            with patch.object(self.configurator, 'configure_data_directory', return_value="/tmp/redis_data"):
                with patch.object(self.configurator, 'generate_secure_password', return_value="testpass123"):
                    port_mappings = self.configurator.detect_available_ports([DatabaseType.REDIS])
                    self.assertEqual(port_mappings[DatabaseType.REDIS].actual_port, 6379)

        # Step 5: Install Redis
        options = InstallationOptions(
            database_type=DatabaseType.REDIS,
            installation_method=InstallationMethod.DOCKER,
            docker_image="redis:latest",
            auto_start=True
        )

        with patch.object(self.installer.docker_manager, 'detect_docker_environment', return_value=mock_docker_info):
            with patch.object(self.installer, '_pull_docker_image'):
                with patch.object(self.installer, '_create_docker_volume', return_value="redis_data"):
                    with patch.object(self.installer, '_create_docker_container_config'):
                        with patch.object(self.docker_manager, 'create_redis_container', return_value=(True, "Container created")):
                            with patch.object(self.installer, '_verify_docker_installation', return_value={"status": "running"}):
                                result = self.installer.install_database(options)

        self.assertTrue(result.success)
        self.assertEqual(result.database_type, DatabaseType.REDIS)

        # Step 6: Verify installation
        with patch.object(self.redis_manager, 'detect_redis_service') as mock_verify:
            mock_verify.return_value = Mock(
                status=RedisServiceStatus.RUNNING,
                connection_type=RedisConnectionType.DOCKER,
                container_name="redis_container",
                port=6379
            )

            verification = self.redis_manager.detect_redis_service()
            self.assertEqual(verification.status, RedisServiceStatus.RUNNING)
            self.assertEqual(verification.connection_type, RedisConnectionType.DOCKER)

    def test_complete_postgresql_setup_workflow(self):
        """Test complete PostgreSQL setup workflow from detection to installation"""
        # Step 1: Detect existing PostgreSQL service
        with patch.object(self.postgresql_manager, 'detect_postgresql_service') as mock_detect:
            mock_detect.return_value = Mock(
                status=PostgreSQLServiceStatus.NOT_INSTALLED,
                connection_type=PostgreSQLConnectionType.LOCAL
            )

            service_info = self.postgresql_manager.detect_postgresql_service()
            self.assertEqual(service_info.status, PostgreSQLServiceStatus.NOT_INSTALLED)

        # Step 2: Create local installation (as Docker alternative)
        options = InstallationOptions(
            database_type=DatabaseType.POSTGRESQL,
            installation_method=InstallationMethod.LOCAL,
            install_directory="/tmp/postgres_install",
            auto_start=True
        )

        with patch.object(self.installer, '_download_database', return_value="/tmp/postgres.tar.gz"):
            with patch.object(self.installer, '_extract_database'):
                with patch.object(self.installer, '_configure_local_database', return_value={"config_path": "/tmp/postgres.conf"}):
                    with patch.object(self.installer, '_perform_local_installation', return_value=True):
                        with patch.object(self.installer, '_start_local_service', return_value=True):
                            with patch.object(self.installer, '_verify_local_installation', return_value={"status": "running"}):
                                result = self.installer.install_database(options)

        self.assertTrue(result.success)
        self.assertEqual(result.database_type, DatabaseType.POSTGRESQL)
        self.assertEqual(result.installation_method, InstallationMethod.LOCAL)

        # Step 3: Test PostgreSQL connection
        with patch('services.postgresql_service_manager.PSYCOPG2_AVAILABLE', True):
            with patch('services.postgresql_service_manager.psycopg2') as mock_psycopg2:
                mock_connection = Mock()
                mock_cursor = Mock()
                mock_psycopg2.connect.return_value = mock_connection
                mock_connection.cursor.return_value = mock_cursor
                mock_connection.autocommit = True

                mock_cursor.fetchone.side_effect = [
                    {'version': 'PostgreSQL 15.0'},
                    {'database_name': 'postgres', 'current_user': 'postgres', 'active_connections': 1}
                ]

                connection_info = self.postgresql_manager._test_postgresql_connection(
                    'localhost', 5432, 'postgres', 'postgres', 'password'
                )

                self.assertIsNotNone(connection_info)
                self.assertEqual(connection_info.status, PostgreSQLServiceStatus.RUNNING)

    def test_hybrid_installation_workflow(self):
        """Test hybrid installation workflow (both local and Docker)"""
        options = InstallationOptions(
            database_type=DatabaseType.REDIS,
            installation_method=InstallationMethod.HYBRID,
            install_directory="/tmp/redis_local",
            docker_image="redis:latest",
            auto_start=True
        )

        # Mock local installation
        with patch.object(self.installer, '_download_database', return_value="/tmp/redis.tar.gz"):
            with patch.object(self.installer, '_extract_database'):
                with patch.object(self.installer, '_configure_local_database', return_value={"config_path": "/tmp/redis.conf"}):
                    with patch.object(self.installer, '_perform_local_installation', return_value=True):
                        with patch.object(self.installer, '_start_local_service', return_value=True):
                            with patch.object(self.installer, '_verify_local_installation', return_value={"status": "running"}):

                                # Mock Docker installation
                                with patch.object(self.installer.docker_manager, 'detect_docker_environment') as mock_docker:
                                    mock_docker_info = Mock()
                                    mock_docker_info.status = DockerStatus.RUNNING
                                    mock_docker.return_value = mock_docker_info

                                    with patch.object(self.installer, '_pull_docker_image'):
                                        with patch.object(self.installer, '_create_docker_volume', return_value="redis_data"):
                                            with patch.object(self.installer, '_create_docker_container_config'):
                                                with patch.object(self.docker_manager, 'create_redis_container', return_value=(True, "Container created")):
                                                    with patch.object(self.installer, '_verify_docker_installation', return_value={"status": "running"}):

                                                        result = self.installer.install_database(options)

        self.assertTrue(result.success)
        self.assertEqual(result.installation_method, InstallationMethod.HYBRID)
        self.assertIn("Local:", result.install_path)
        self.assertIn("Docker:", result.install_path)

    def test_error_handling_workflow(self):
        """Test error handling in installation workflow"""
        options = InstallationOptions(
            database_type=DatabaseType.POSTGRESQL,
            installation_method=InstallationMethod.DOCKER,
            docker_image="nonexistent:latest"
        )

        # Mock Docker not running
        with patch.object(self.installer.docker_manager, 'detect_docker_environment') as mock_docker:
            mock_docker_info = Mock()
            mock_docker_info.status = DockerStatus.STOPPED
            mock_docker.return_value = mock_docker_info

            result = self.installer.install_database(options)

        self.assertFalse(result.success)
        self.assertIn("Docker is not running", result.error_message)

    def test_configuration_validation_workflow(self):
        """Test configuration validation throughout workflow"""
        # Test invalid port configuration
        with patch.object(self.configurator, '_is_port_available', return_value=False):
            port_mappings = self.configurator.detect_available_ports([DatabaseType.REDIS])
            redis_mapping = port_mappings[DatabaseType.REDIS]

            self.assertTrue(redis_mapping.is_conflict)
            self.assertNotEqual(redis_mapping.actual_port, redis_mapping.default_port)

        # Test configuration validation with invalid data
        config = DatabaseConfiguration(
            database_type=DatabaseType.POSTGRESQL,
            mode=ConfigurationMode.LOCAL,
            connection_config=PostgreSQLConnectionConfig(
                host="localhost",
                port=99999,  # Invalid port
                database="postgres",
                username="postgres"
            ),
            data_directory="/nonexistent"
        )

        is_valid, errors = self.configurator.validate_configuration(config)
        self.assertFalse(is_valid)
        self.assertGreater(len(errors), 0)

    def test_progress_tracking_workflow(self):
        """Test progress tracking throughout installation"""
        progress_updates = []

        def progress_callback(progress):
            progress_updates.append(progress)

        installer = DatabaseInstaller(progress_callback=progress_callback)

        options = InstallationOptions(
            database_type=DatabaseType.REDIS,
            installation_method=InstallationMethod.DOCKER,
            docker_image="redis:latest"
        )

        # Mock successful installation
        with patch.object(installer.docker_manager, 'detect_docker_environment') as mock_docker:
            mock_docker_info = Mock()
            mock_docker_info.status = DockerStatus.RUNNING
            mock_docker.return_value = mock_docker_info

            with patch.object(installer, '_pull_docker_image'):
                with patch.object(installer, '_create_docker_volume', return_value="redis_data"):
                    with patch.object(installer, '_create_docker_container_config'):
                        with patch.object(installer.docker_manager, 'create_redis_container', return_value=(True, "Container created")):
                            with patch.object(installer, '_verify_docker_installation', return_value={"status": "running"}):

                                result = installer.install_database(options)

        # Verify progress was tracked
        self.assertGreater(len(progress_updates), 0)
        self.assertEqual(progress_updates[-1].status, InstallationStatus.COMPLETED)
        self.assertEqual(progress_updates[-1].progress_percentage, 100.0)


if __name__ == '__main__':
    # Create test suite
    test_suite = unittest.TestSuite()

    # Add test cases
    test_classes = [
        TestRedisServiceManager,
        TestPostgreSQLServiceManager,
        TestDockerManager,
        TestDatabaseConfigurator,
        TestDatabaseInstaller,
        TestIntegrationWorkflow
    ]

    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)

    # Print summary
    print(f"\nTest Summary:")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")

    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1)