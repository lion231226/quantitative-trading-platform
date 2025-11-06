"""
Database Connection Testing Module

This module provides comprehensive database connection testing capabilities
including connection health checks, read/write permission tests, and performance
metrics for Redis and PostgreSQL databases.
"""

import asyncio
import time
import json
import uuid
from typing import Dict, List, Optional, Tuple, Union, Any
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path

try:
    import redis
    from redis.exceptions import ConnectionError as RedisConnectionError, TimeoutError as RedisTimeoutError
    import asyncpg
    import psycopg2
    import psycopg2.extras
    from psycopg2 import OperationalError as Psycopg2OperationalError
except ImportError as e:
    redis = None
    RedisConnectionError = Exception
    RedisTimeoutError = Exception
    asyncpg = None
    psycopg2 = None
    Psycopg2OperationalError = Exception

from utils.logger import get_logger
from utils.progress_tracker import ProgressTracker
from core.operating_system_detector import OperatingSystemDetector

logger = get_logger(__name__)


class CustomJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder for enum types"""
    def default(self, obj):
        if isinstance(obj, (DatabaseType, TestStatus)):
            return obj.value
        return super().default(obj)


class DatabaseType(Enum):
    """Supported database types"""
    REDIS = "redis"
    POSTGRESQL = "postgresql"


class TestStatus(Enum):
    """Test status enumeration"""
    SUCCESS = "success"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    ERROR = "error"


def _validate_database_config(config: 'DatabaseTestConfig') -> 'DatabaseTestConfig':
    """
    Validate and sanitize database configuration parameters

    Args:
        config: Database configuration to validate

    Returns:
        Sanitized DatabaseTestConfig

    Raises:
        ValueError: If configuration parameters are invalid
    """
    import re
    import ipaddress

    # Validate host - prevent injection and ensure valid format
    if not config.host:
        raise ValueError("Database host cannot be empty")

    # Check for dangerous patterns in host
    dangerous_patterns = [';', '--', '/*', '*/', 'xp_', 'sp_', '\\', '/', '|', '&', '$', '`']
    host_lower = config.host.lower()
    for pattern in dangerous_patterns:
        if pattern in host_lower:
            raise ValueError(f"Invalid characters in database host: {pattern}")

    # Validate hostname or IP format
    try:
        # Try to parse as IP address
        ipaddress.ip_address(config.host)
    except ValueError:
        # Not an IP, check if it's a valid hostname
        if not re.match(r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$', config.host):
            raise ValueError(f"Invalid database host format: {config.host}")

    # Validate port range
    if not (1 <= config.port <= 65535):
        raise ValueError(f"Database port must be between 1 and 65535, got: {config.port}")

    # Validate database name - prevent SQL injection
    if config.database:
        if not re.match(r'^[a-zA-Z0-9_\-]+$', config.database):
            raise ValueError(f"Invalid database name format: {config.database}")
        if len(config.database) > 64:
            raise ValueError("Database name too long (max 64 characters)")

    # Validate username - prevent injection
    if config.username:
        # Allow alphanumeric, underscore, hyphen, but no dangerous characters
        if not re.match(r'^[a-zA-Z0-9_\-@\.]+$', config.username):
            raise ValueError(f"Invalid username format: {config.username}")
        if len(config.username) > 128:
            raise ValueError("Username too long (max 128 characters)")

    # Validate password length (don't validate content as it might contain valid special chars)
    if config.password and len(config.password) > 1024:
        raise ValueError("Password too long (max 1024 characters)")

    # Validate SSL mode
    valid_ssl_modes = ['disable', 'allow', 'prefer', 'require', 'verify-ca', 'verify-full']
    if config.ssl_mode not in valid_ssl_modes:
        raise ValueError(f"Invalid SSL mode: {config.ssl_mode}. Valid options: {valid_ssl_modes}")

    # Validate timeout
    if not (1 <= config.timeout <= 300):
        raise ValueError(f"Timeout must be between 1 and 300 seconds, got: {config.timeout}")

    # Validate max_connections
    if not (1 <= config.max_connections <= 1000):
        raise ValueError(f"Max connections must be between 1 and 1000, got: {config.max_connections}")

    return config


@dataclass
class DatabaseTestConfig:
    """Database test configuration"""
    host: str = "localhost"
    port: int = 5432
    database: str = "test"
    username: str = ""
    password: str = ""
    ssl_mode: str = "prefer"
    timeout: int = 10
    max_connections: int = 5

    def __post_init__(self):
        """Validate configuration after initialization"""
        _validate_database_config(self)


@dataclass
class DatabaseTestResult:
    """Database test result"""
    database_type: DatabaseType
    host: str
    port: int
    status: TestStatus
    connection_time: float
    read_time: Optional[float] = None
    write_time: Optional[float] = None
    error_message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


@dataclass
class DatabaseTestSummary:
    """Summary of all database tests"""
    total_tests: int
    successful_tests: int
    failed_tests: int
    results: List[DatabaseTestResult]
    overall_status: TestStatus
    test_duration: float


class DatabaseTester:
    """Database connection testing service"""

    def __init__(self, progress_tracker: Optional[ProgressTracker] = None):
        """
        Initialize database tester

        Args:
            progress_tracker: Progress tracker for test status updates
        """
        self.progress_tracker = progress_tracker
        self.os_detector = OperatingSystemDetector()
        self.timeout = 30

    def set_progress_tracker(self, tracker: ProgressTracker):
        """Set progress tracker for monitoring"""
        self.progress_tracker = tracker

    def _build_safe_connection_string(self, config: DatabaseTestConfig, db_type: DatabaseType) -> str:
        """
        Build a secure database connection string to prevent injection attacks

        Args:
            config: Validated database configuration
            db_type: Type of database (Redis or PostgreSQL)

        Returns:
            Safe connection string (for logging purposes only, not for actual connections)

        Raises:
            ValueError: If configuration contains invalid parameters
        """
        # Re-validate configuration before building connection string
        _validate_database_config(config)

        if db_type == DatabaseType.POSTGRESQL:
            # Build PostgreSQL connection string safely
            # Note: We use parameterized connections in actual code, this is just for logging
            escaped_host = config.host.replace("'", "''")
            escaped_dbname = config.database.replace("'", "''") if config.database else ""
            escaped_user = config.username.replace("'", "''") if config.username else ""

            connection_parts = [
                f"postgresql://{escaped_user}:{'*' * len(config.password) if config.password else ''}@{escaped_host}:{config.port}/{escaped_dbname}"
            ]

            # Add SSL mode parameter
            if config.ssl_mode and config.ssl_mode != "prefer":
                connection_parts.append(f"?sslmode={config.ssl_mode}")

            return "".join(connection_parts)

        elif db_type == DatabaseType.REDIS:
            # Build Redis connection string safely (for logging)
            escaped_host = config.host.replace("'", "''")
            return f"redis://:{'*' * len(config.password) if config.password else ''}@{escaped_host}:{config.port}"

        else:
            raise ValueError(f"Unsupported database type: {db_type}")

    def _sanitize_error_message(self, error_message: str, config: DatabaseTestConfig) -> str:
        """
        Sanitize error messages to prevent leaking sensitive information

        Args:
            error_message: Original error message
            config: Database configuration (to identify sensitive info)

        Returns:
            Sanitized error message safe for logging
        """
        if not error_message:
            return error_message

        # Remove password from error messages
        if config.password:
            error_message = error_message.replace(config.password, "***")

        # Remove other sensitive patterns
        sensitive_patterns = [
            r'password=[^\s&;]+',
            r'pwd=[^\s&;]+',
            r'secret=[^\s&;]+',
            r'token=[^\s&;]+',
            r'key=[^\s&;]+',
        ]

        import re
        for pattern in sensitive_patterns:
            error_message = re.sub(pattern, r'\1***', error_message, flags=re.IGNORECASE)

        return error_message

    async def test_redis_connection(self, config: DatabaseTestConfig) -> DatabaseTestResult:
        """
        Test Redis connection and basic operations

        Args:
            config: Redis connection configuration

        Returns:
            DatabaseTestResult with test details
        """
        start_time = time.time()

        if redis is None:
            return DatabaseTestResult(
                database_type=DatabaseType.REDIS,
                host=config.host,
                port=config.port,
                status=TestStatus.ERROR,
                connection_time=0.0,
                error_message="Redis module not available. Install with: pip install redis"
            )

        try:
            # Test connection
            client = redis.Redis(
                host=config.host,
                port=config.port,
                password=config.password if config.password else None,
                socket_timeout=config.timeout,
                socket_connect_timeout=config.timeout,
                decode_responses=True
            )

            connection_time = time.time() - start_time

            # Test basic operations
            test_key = f"test_key_{uuid.uuid4().hex[:8]}"
            test_value = f"test_value_{uuid.uuid4().hex}"

            # Write test
            write_start = time.time()
            client.set(test_key, test_value, ex=60)  # Auto-expire in 60 seconds
            write_time = time.time() - write_start

            # Read test
            read_start = time.time()
            retrieved_value = client.get(test_key)
            read_time = time.time() - read_start

            # Cleanup
            client.delete(test_key)

            # Verify data integrity
            if retrieved_value != test_value:
                return DatabaseTestResult(
                    database_type=DatabaseType.REDIS,
                    host=config.host,
                    port=config.port,
                    status=TestStatus.FAILURE,
                    connection_time=connection_time,
                    write_time=write_time,
                    read_time=read_time,
                    error_message="Data integrity check failed: retrieved value doesn't match written value",
                    details={
                        "written_value": test_value,
                        "retrieved_value": retrieved_value,
                        "memory_usage": client.info().get("used_memory_human"),
                        "connected_clients": client.info().get("connected_clients")
                    }
                )

            # Get server info
            server_info = client.info()

            return DatabaseTestResult(
                database_type=DatabaseType.REDIS,
                host=config.host,
                port=config.port,
                status=TestStatus.SUCCESS,
                connection_time=connection_time,
                write_time=write_time,
                read_time=read_time,
                details={
                    "redis_version": server_info.get("redis_version"),
                    "memory_usage": server_info.get("used_memory_human"),
                    "connected_clients": server_info.get("connected_clients"),
                    "uptime_in_seconds": server_info.get("uptime_in_seconds"),
                    "used_memory": server_info.get("used_memory"),
                    "maxmemory": server_info.get("maxmemory")
                }
            )

        except RedisConnectionError as e:
            # Check if it's actually a timeout based on error message
            error_message = str(e).lower()
            if "timeout" in error_message:
                return DatabaseTestResult(
                    database_type=DatabaseType.REDIS,
                    host=config.host,
                    port=config.port,
                    status=TestStatus.TIMEOUT,
                    connection_time=time.time() - start_time,
                    error_message=f"Redis connection timeout: {str(e)}"
                )
            else:
                return DatabaseTestResult(
                    database_type=DatabaseType.REDIS,
                    host=config.host,
                    port=config.port,
                    status=TestStatus.FAILURE,
                    connection_time=time.time() - start_time,
                    error_message=f"Redis connection failed: {str(e)}"
                )
        except RedisTimeoutError as e:
            return DatabaseTestResult(
                database_type=DatabaseType.REDIS,
                host=config.host,
                port=config.port,
                status=TestStatus.TIMEOUT,
                connection_time=time.time() - start_time,
                error_message=f"Redis connection timeout: {str(e)}"
            )
        except Exception as e:
            # Check if it's a timeout based on error message or exception type
            error_message = str(e).lower()
            exception_type = type(e).__name__.lower()
            if "timeout" in error_message or "timeout" in exception_type:
                return DatabaseTestResult(
                    database_type=DatabaseType.REDIS,
                    host=config.host,
                    port=config.port,
                    status=TestStatus.TIMEOUT,
                    connection_time=time.time() - start_time,
                    error_message=f"Redis connection timeout: {str(e)}"
                )
            else:
                return DatabaseTestResult(
                    database_type=DatabaseType.REDIS,
                    host=config.host,
                    port=config.port,
                    status=TestStatus.FAILURE,
                    connection_time=time.time() - start_time,
                    error_message=f"Redis connection failed: {str(e)}"
                )

    async def test_postgresql_connection(self, config: DatabaseTestConfig) -> DatabaseTestResult:
        """
        Test PostgreSQL connection and basic operations

        Args:
            config: PostgreSQL connection configuration

        Returns:
            DatabaseTestResult with test details
        """
        start_time = time.time()

        if psycopg2 is None:
            return DatabaseTestResult(
                database_type=DatabaseType.POSTGRESQL,
                host=config.host,
                port=config.port,
                status=TestStatus.ERROR,
                connection_time=0.0,
                error_message="PostgreSQL module not available. Install with: pip install psycopg2-binary"
            )

        try:
            # Build connection parameters safely using parameterized approach
            # This prevents SQL injection by avoiding string formatting
            connection_params = {
                'host': config.host,
                'port': config.port,
                'dbname': config.database,
                'user': config.username,
                'password': config.password,
                'sslmode': config.ssl_mode,
                'connect_timeout': config.timeout
            }

            # Test connection using parameterized connection
            conn_start = time.time()
            connection = psycopg2.connect(**connection_params)
            connection_time = time.time() - conn_start

            connection.autocommit = True
            cursor = connection.cursor()

            # Test basic operations
            test_id = uuid.uuid4().hex[:8]
            test_table = f"test_table_{test_id}"

            # Create test table
            create_start = time.time()
            cursor.execute(f"""
                CREATE TABLE {test_table} (
                    id SERIAL PRIMARY KEY,
                    test_data VARCHAR(100),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            create_time = time.time() - create_start

            # Write test
            write_start = time.time()
            test_data = f"test_data_{uuid.uuid4().hex}"
            cursor.execute(
                f"INSERT INTO {test_table} (test_data) VALUES (%s)",
                (test_data,)
            )
            write_time = time.time() - write_start

            # Read test
            read_start = time.time()
            cursor.execute(
                f"SELECT test_data FROM {test_table} WHERE test_data = %s",
                (test_data,)
            )
            result = cursor.fetchone()
            read_time = time.time() - read_start

            # Verify data integrity
            if not result or result[0] != test_data:
                return DatabaseTestResult(
                    database_type=DatabaseType.POSTGRESQL,
                    host=config.host,
                    port=config.port,
                    status=TestStatus.FAILURE,
                    connection_time=connection_time,
                    write_time=write_time,
                    read_time=read_time,
                    error_message="Data integrity check failed: retrieved data doesn't match written data",
                    details={
                        "written_data": test_data,
                        "retrieved_data": result[0] if result else None
                    }
                )

            # Get database information
            cursor.execute("SELECT version()")
            db_version = cursor.fetchone()[0]

            cursor.execute("SELECT current_database(), current_user")
            db_info = cursor.fetchone()

            # Cleanup
            cursor.execute(f"DROP TABLE {test_table}")
            cursor.close()
            connection.close()

            return DatabaseTestResult(
                database_type=DatabaseType.POSTGRESQL,
                host=config.host,
                port=config.port,
                status=TestStatus.SUCCESS,
                connection_time=connection_time,
                write_time=write_time,
                read_time=read_time,
                details={
                    "database_version": db_version,
                    "database_name": db_info[0] if db_info else None,
                    "current_user": db_info[1] if db_info else None,
                    "table_creation_time": create_time,
                    "ssl_mode": config.ssl_mode
                }
            )

        except Psycopg2OperationalError as e:
            error_msg = str(e).lower()
            # Only treat as timeout if it explicitly mentions timeout
            if "timeout" in error_msg:
                status = TestStatus.TIMEOUT
            else:
                status = TestStatus.FAILURE

            return DatabaseTestResult(
                database_type=DatabaseType.POSTGRESQL,
                host=config.host,
                port=config.port,
                status=status,
                connection_time=time.time() - start_time,
                error_message=f"PostgreSQL connection failed: {str(e)}"
            )
        except Exception as e:
            return DatabaseTestResult(
                database_type=DatabaseType.POSTGRESQL,
                host=config.host,
                port=config.port,
                status=TestStatus.ERROR,
                connection_time=time.time() - start_time,
                error_message=f"PostgreSQL test error: {str(e)}"
            )

    async def test_all_connections(self, configs: List[DatabaseTestConfig]) -> DatabaseTestSummary:
        """
        Test all database connections concurrently

        Args:
            configs: List of database configurations to test

        Returns:
            DatabaseTestSummary with all test results
        """
        if self.progress_tracker:
            self.progress_tracker.start_task("database_testing", "Testing database connections")

        start_time = time.time()
        results = []

        for i, config in enumerate(configs):
            # Determine database type from port
            if config.port == 6379:
                db_type = DatabaseType.REDIS
            elif config.port in [5432, 5433]:
                db_type = DatabaseType.POSTGRESQL
            else:
                # Default to PostgreSQL
                db_type = DatabaseType.POSTGRESQL

            if self.progress_tracker:
                self.progress_tracker.update_progress(
                    i + 1,
                    len(configs),
                    f"Testing {db_type.value} on {config.host}:{config.port}"
                )

            if db_type == DatabaseType.REDIS:
                result = await self.test_redis_connection(config)
            else:
                result = await self.test_postgresql_connection(config)

            results.append(result)

        # Calculate summary
        test_duration = time.time() - start_time
        successful_tests = sum(1 for r in results if r.status == TestStatus.SUCCESS)
        failed_tests = len(results) - successful_tests
        overall_status = TestStatus.SUCCESS if failed_tests == 0 else TestStatus.FAILURE

        summary = DatabaseTestSummary(
            total_tests=len(results),
            successful_tests=successful_tests,
            failed_tests=failed_tests,
            results=results,
            overall_status=overall_status,
            test_duration=test_duration
        )

        if self.progress_tracker:
            self.progress_tracker.complete_task(
                "database_testing",
                f"Database testing complete: {successful_tests}/{len(results)} tests passed"
            )

        return summary

    def get_default_redis_config(self, host: str = "localhost", port: int = 6379) -> DatabaseTestConfig:
        """Get default Redis test configuration"""
        return DatabaseTestConfig(
            host=host,
            port=port,
            timeout=10
        )

    def get_default_postgresql_config(
        self,
        host: str = "localhost",
        port: int = 5432,
        database: str = "postgres",
        username: str = "postgres",
        password: str = ""
    ) -> DatabaseTestConfig:
        """Get default PostgreSQL test configuration"""
        return DatabaseTestConfig(
            host=host,
            port=port,
            database=database,
            username=username,
            password=password,
            timeout=10
        )

    def generate_test_report(self, summary: DatabaseTestSummary) -> str:
        """
        Generate a human-readable test report

        Args:
            summary: Database test summary

        Returns:
            Formatted test report string
        """
        report_lines = [
            "=" * 60,
            "DATABASE CONNECTION TEST REPORT",
            "=" * 60,
            f"Test Duration: {summary.test_duration:.2f} seconds",
            f"Total Tests: {summary.total_tests}",
            f"Successful: {summary.successful_tests}",
            f"Failed: {summary.failed_tests}",
            f"Overall Status: {summary.overall_status.value.upper()}",
            "",
            "DETAILED RESULTS:",
            "-" * 40
        ]

        for result in summary.results:
            status_icon = "✅" if result.status == TestStatus.SUCCESS else "❌"
            report_lines.append(
                f"{status_icon} {result.database_type.value.upper()} - "
                f"{result.host}:{result.port} ({result.status.value})"
            )

            if result.status == TestStatus.SUCCESS:
                report_lines.extend([
                    f"   Connection Time: {result.connection_time:.3f}s",
                    f"   Write Time: {result.write_time:.3f}s" if result.write_time else "",
                    f"   Read Time: {result.read_time:.3f}s" if result.read_time else ""
                ])

                if result.details:
                    if result.database_type == DatabaseType.REDIS:
                        report_lines.extend([
                            f"   Redis Version: {result.details.get('redis_version', 'N/A')}",
                            f"   Memory Usage: {result.details.get('memory_usage', 'N/A')}",
                            f"   Connected Clients: {result.details.get('connected_clients', 'N/A')}"
                        ])
                    elif result.database_type == DatabaseType.POSTGRESQL:
                        report_lines.extend([
                            f"   Database: {result.details.get('database_name', 'N/A')}",
                            f"   User: {result.details.get('current_user', 'N/A')}",
                            f"   SSL Mode: {result.details.get('ssl_mode', 'N/A')}"
                        ])
            else:
                report_lines.append(f"   Error: {result.error_message}")

            report_lines.append("")

        return "\n".join(report_lines)

    def save_test_results(self, summary: DatabaseTestSummary, output_file: str) -> bool:
        """
        Save test results to JSON file

        Args:
            summary: Database test summary
            output_file: Path to output file

        Returns:
            True if successful, False otherwise
        """
        try:
            # Convert to serializable format
            results_data = {
                "test_summary": asdict(summary),
                "timestamp": time.time(),
                "test_count": summary.total_tests,
                "success_count": summary.successful_tests,
                "failure_count": summary.failed_tests,
                "overall_status": summary.overall_status.value,
                "duration": summary.test_duration
            }

            # Convert result objects to dictionaries
            results_data["test_summary"]["results"] = [
                {
                    **asdict(result),
                    "database_type": result.database_type.value,
                    "status": result.status.value
                }
                for result in summary.results
            ]

            # Write to file
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(results_data, f, indent=2, ensure_ascii=False, cls=CustomJSONEncoder)

            logger.info(f"Database test results saved to: {output_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to save test results: {str(e)}")
            return False