"""
Tests for Database Tester Module
"""

import pytest
import asyncio
import json
import tempfile
import uuid
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from pathlib import Path

from core.database_tester import (
    DatabaseTester, DatabaseTestConfig, DatabaseTestResult, DatabaseTestSummary,
    DatabaseType, TestStatus
)


class TestDatabaseTestConfig:
    """Test DatabaseTestConfig dataclass"""

    def test_default_config(self):
        """Test default configuration values"""
        config = DatabaseTestConfig()
        assert config.host == "localhost"
        assert config.port == 5432
        assert config.database == "test"
        assert config.username == ""
        assert config.password == ""
        assert config.ssl_mode == "prefer"
        assert config.timeout == 10
        assert config.max_connections == 5

    def test_custom_config(self):
        """Test custom configuration values"""
        config = DatabaseTestConfig(
            host="custom-host",
            port=3306,
            database="custom_db",
            username="user",
            password="pass",
            ssl_mode="require",
            timeout=30,
            max_connections=10
        )
        assert config.host == "custom-host"
        assert config.port == 3306
        assert config.database == "custom_db"
        assert config.username == "user"
        assert config.password == "pass"
        assert config.ssl_mode == "require"
        assert config.timeout == 30
        assert config.max_connections == 10


class TestDatabaseTestResult:
    """Test DatabaseTestResult dataclass"""

    def test_result_creation(self):
        """Test database test result creation"""
        result = DatabaseTestResult(
            database_type=DatabaseType.REDIS,
            host="localhost",
            port=6379,
            status=TestStatus.SUCCESS,
            connection_time=0.5,
            read_time=0.1,
            write_time=0.2,
            details={"version": "6.2.0"}
        )
        assert result.database_type == DatabaseType.REDIS
        assert result.host == "localhost"
        assert result.port == 6379
        assert result.status == TestStatus.SUCCESS
        assert result.connection_time == 0.5
        assert result.read_time == 0.1
        assert result.write_time == 0.2
        assert result.details["version"] == "6.2.0"

    def test_result_with_error(self):
        """Test database test result with error"""
        result = DatabaseTestResult(
            database_type=DatabaseType.POSTGRESQL,
            host="localhost",
            port=5432,
            status=TestStatus.FAILURE,
            connection_time=5.0,
            error_message="Connection refused"
        )
        assert result.status == TestStatus.FAILURE
        assert result.error_message == "Connection refused"
        assert result.read_time is None
        assert result.write_time is None


class TestDatabaseTester:
    """Test DatabaseTester class"""

    @pytest.fixture
    def tester(self):
        """Create database tester instance"""
        return DatabaseTester()

    @pytest.fixture
    def mock_progress_tracker(self):
        """Create mock progress tracker"""
        tracker = Mock()
        tracker.start_task = Mock()
        tracker.update_progress = Mock()
        tracker.complete_task = Mock()
        return tracker

    def test_init(self, tester):
        """Test database tester initialization"""
        assert tester.progress_tracker is None
        assert tester.os_detector is not None
        assert tester.timeout == 30

    def test_set_progress_tracker(self, tester, mock_progress_tracker):
        """Test setting progress tracker"""
        tester.set_progress_tracker(mock_progress_tracker)
        assert tester.progress_tracker == mock_progress_tracker

    @pytest.mark.asyncio
    async def test_redis_connection_success(self, tester):
        """Test successful Redis connection"""
        config = DatabaseTestConfig(host="localhost", port=6379)

        # Mock Redis client
        mock_client = Mock()
        mock_client.info.return_value = {
            "redis_version": "6.2.0",
            "used_memory_human": "1.5M",
            "connected_clients": 2,
            "uptime_in_seconds": 3600
        }

        with patch('core.database_tester.redis') as mock_redis:
            mock_redis.Redis.return_value = mock_client
            mock_client.set.return_value = True
            # Mock get to return the same value that was set - use a fixed test value
            stored_values = {}
            def mock_get(key):
                return stored_values.get(key, None)
            def mock_set(key, value, ex=None):
                stored_values[key] = value
                return True
            mock_client.get.side_effect = mock_get
            mock_client.set.side_effect = mock_set

            result = await tester.test_redis_connection(config)

        assert result.status == TestStatus.SUCCESS
        assert result.database_type == DatabaseType.REDIS
        assert result.host == "localhost"
        assert result.port == 6379
        assert result.connection_time > 0
        assert result.read_time > 0
        assert result.write_time > 0
        assert result.details is not None
        assert result.details["redis_version"] == "6.2.0"

    @pytest.mark.asyncio
    async def test_redis_connection_failure(self, tester):
        """Test Redis connection failure"""
        config = DatabaseTestConfig(host="localhost", port=6379)

        with patch('core.database_tester.redis') as mock_redis:
            mock_redis.ConnectionError = Exception
            mock_redis.Redis.side_effect = mock_redis.ConnectionError("Connection refused")

            result = await tester.test_redis_connection(config)

        assert result.status == TestStatus.FAILURE
        assert result.error_message == "Redis connection failed: Connection refused"

    @pytest.mark.asyncio
    async def test_redis_connection_timeout(self, tester):
        """Test Redis connection timeout"""
        config = DatabaseTestConfig(host="localhost", port=6379)

        with patch('core.database_tester.redis') as mock_redis:
            mock_redis.TimeoutError = Exception
            mock_redis.Redis.side_effect = Exception("Connection timeout")

            result = await tester.test_redis_connection(config)

        assert result.status == TestStatus.TIMEOUT
        assert result.error_message == "Redis connection timeout: Connection timeout"

    @pytest.mark.asyncio
    async def test_redis_module_unavailable(self, tester):
        """Test Redis module unavailable"""
        config = DatabaseTestConfig(host="localhost", port=6379)

        with patch('core.database_tester.redis', None):
            result = await tester.test_redis_connection(config)

        assert result.status == TestStatus.ERROR
        assert "Redis module not available" in result.error_message

    @pytest.mark.asyncio
    async def test_postgresql_connection_success(self, tester):
        """Test successful PostgreSQL connection"""
        config = DatabaseTestConfig(
            host="localhost",
            port=5432,
            database="test_db",
            username="user",
            password="pass"
        )

        # Mock psycopg2
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_connection.cursor.return_value = mock_cursor

        # Store test data for integrity check
        stored_test_data = None

        # Track query types to return appropriate data
        query_types = []

        def mock_execute(query, params=None):
            # Store the test data when inserting
            if "INSERT INTO" in query and params:
                nonlocal stored_test_data
                stored_test_data = params[0]
            # Track query type for fetchone
            query_types.append(query.strip().upper())

        def mock_fetchone():
            # Return appropriate data based on the last query type
            if not query_types:
                return ("test_data",)  # default fallback

            last_query = query_types[-1]

            if "SELECT" in last_query and "VERSION()" in last_query:
                return ("PostgreSQL 13.0",)  # version query
            elif "SELECT" in last_query and "CURRENT_DATABASE" in last_query:
                return ("test_db", "user")   # database info query
            elif "SELECT" in last_query and "TEST_DATA FROM" in last_query:
                return (stored_test_data,) if stored_test_data is not None else ("test_data",)  # read test query
            else:
                return ("test_data",)  # default fallback

        mock_cursor.execute = mock_execute
        mock_cursor.fetchone = mock_fetchone

        with patch('core.database_tester.psycopg2') as mock_psycopg2:
            mock_psycopg2.connect.return_value = mock_connection

            result = await tester.test_postgresql_connection(config)

        assert result.status == TestStatus.SUCCESS
        assert result.database_type == DatabaseType.POSTGRESQL
        assert result.host == "localhost"
        assert result.port == 5432
        assert result.connection_time > 0
        assert result.read_time > 0
        assert result.write_time > 0
        assert result.details is not None
        assert "PostgreSQL 13.0" in result.details["database_version"]
        assert result.details["database_name"] == "test_db"

    @pytest.mark.asyncio
    async def test_postgresql_connection_failure(self, tester):
        """Test PostgreSQL connection failure"""
        config = DatabaseTestConfig(
            host="localhost",
            port=5432,
            database="test_db",
            username="user",
            password="pass"
        )

        with patch('core.database_tester.psycopg2') as mock_psycopg2:
            mock_psycopg2.OperationalError = Exception
            mock_psycopg2.connect.side_effect = mock_psycopg2.OperationalError("Connection refused")

            result = await tester.test_postgresql_connection(config)

        assert result.status == TestStatus.FAILURE
        assert "PostgreSQL connection failed" in result.error_message

    @pytest.mark.asyncio
    async def test_postgresql_connection_timeout(self, tester):
        """Test PostgreSQL connection timeout"""
        config = DatabaseTestConfig(
            host="localhost",
            port=5432,
            database="test_db",
            username="user",
            password="pass"
        )

        with patch('core.database_tester.psycopg2') as mock_psycopg2:
            mock_psycopg2.OperationalError = Exception
            mock_psycopg2.connect.side_effect = mock_psycopg2.OperationalError("Connection timeout")

            result = await tester.test_postgresql_connection(config)

        assert result.status == TestStatus.TIMEOUT
        assert "PostgreSQL connection failed" in result.error_message

    @pytest.mark.asyncio
    async def test_postgresql_module_unavailable(self, tester):
        """Test PostgreSQL module unavailable"""
        config = DatabaseTestConfig(host="localhost", port=5432)

        with patch('core.database_tester.psycopg2', None):
            result = await tester.test_postgresql_connection(config)

        assert result.status == TestStatus.ERROR
        assert "PostgreSQL module not available" in result.error_message

    @pytest.mark.asyncio
    async def test_postgresql_data_integrity_failure(self, tester):
        """Test PostgreSQL data integrity check failure"""
        config = DatabaseTestConfig(
            host="localhost",
            port=5432,
            database="test_db",
            username="user",
            password="pass"
        )

        mock_connection = Mock()
        mock_cursor = Mock()
        mock_connection.cursor.return_value = mock_cursor
        # Simulate data mismatch
        mock_cursor.fetchone.side_effect = [
            ("PostgreSQL 13.0",),  # version
            ("test_db", "user"),   # database info
            ("wrong_data",)         # read test result - doesn't match written data
        ]

        with patch('core.database_tester.psycopg2') as mock_psycopg2:
            mock_psycopg2.connect.return_value = mock_connection

            result = await tester.test_postgresql_connection(config)

        assert result.status == TestStatus.FAILURE
        assert "Data integrity check failed" in result.error_message

    @pytest.mark.asyncio
    async def test_all_connections_success(self, tester, mock_progress_tracker):
        """Test testing all connections successfully"""
        tester.set_progress_tracker(mock_progress_tracker)

        redis_config = DatabaseTestConfig(host="localhost", port=6379)
        postgres_config = DatabaseTestConfig(
            host="localhost",
            port=5432,
            database="test_db",
            username="user",
            password="pass"
        )

        # Mock Redis success
        with patch.object(tester, 'test_redis_connection') as mock_redis:
            mock_redis.return_value = DatabaseTestResult(
                database_type=DatabaseType.REDIS,
                host="localhost",
                port=6379,
                status=TestStatus.SUCCESS,
                connection_time=0.1
            )

            # Mock PostgreSQL success
            with patch.object(tester, 'test_postgresql_connection') as mock_postgres:
                mock_postgres.return_value = DatabaseTestResult(
                    database_type=DatabaseType.POSTGRESQL,
                    host="localhost",
                    port=5432,
                    status=TestStatus.SUCCESS,
                    connection_time=0.2
                )

                summary = await tester.test_all_connections([redis_config, postgres_config])

        assert summary.total_tests == 2
        assert summary.successful_tests == 2
        assert summary.failed_tests == 0
        assert summary.overall_status == TestStatus.SUCCESS
        assert len(summary.results) == 2

        # Verify progress tracker calls
        mock_progress_tracker.start_task.assert_called_once_with("database_testing", "Testing database connections")
        mock_progress_tracker.update_progress.assert_called()
        mock_progress_tracker.complete_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_all_connections_mixed_results(self, tester):
        """Test testing all connections with mixed results"""
        redis_config = DatabaseTestConfig(host="localhost", port=6379)
        postgres_config = DatabaseTestConfig(
            host="localhost",
            port=5432,
            database="test_db",
            username="user",
            password="pass"
        )

        # Mock Redis success
        with patch.object(tester, 'test_redis_connection') as mock_redis:
            mock_redis.return_value = DatabaseTestResult(
                database_type=DatabaseType.REDIS,
                host="localhost",
                port=6379,
                status=TestStatus.SUCCESS,
                connection_time=0.1
            )

            # Mock PostgreSQL failure
            with patch.object(tester, 'test_postgresql_connection') as mock_postgres:
                mock_postgres.return_value = DatabaseTestResult(
                    database_type=DatabaseType.POSTGRESQL,
                    host="localhost",
                    port=5432,
                    status=TestStatus.FAILURE,
                    connection_time=5.0,
                    error_message="Connection refused"
                )

                summary = await tester.test_all_connections([redis_config, postgres_config])

        assert summary.total_tests == 2
        assert summary.successful_tests == 1
        assert summary.failed_tests == 1
        assert summary.overall_status == TestStatus.FAILURE
        assert len(summary.results) == 2

    def test_get_default_redis_config(self, tester):
        """Test getting default Redis configuration"""
        config = tester.get_default_redis_config()
        assert config.host == "localhost"
        assert config.port == 6379
        assert config.timeout == 10

        config = tester.get_default_redis_config(host="redis.example.com", port=6380)
        assert config.host == "redis.example.com"
        assert config.port == 6380

    def test_get_default_postgresql_config(self, tester):
        """Test getting default PostgreSQL configuration"""
        config = tester.get_default_postgresql_config()
        assert config.host == "localhost"
        assert config.port == 5432
        assert config.database == "postgres"
        assert config.username == "postgres"
        assert config.password == ""
        assert config.timeout == 10

        config = tester.get_default_postgresql_config(
            host="db.example.com",
            port=5433,
            database="mydb",
            username="myuser",
            password="mypass"
        )
        assert config.host == "db.example.com"
        assert config.port == 5433
        assert config.database == "mydb"
        assert config.username == "myuser"
        assert config.password == "mypass"

    def test_generate_test_report_success(self, tester):
        """Test generating test report for successful tests"""
        summary = DatabaseTestSummary(
            total_tests=2,
            successful_tests=2,
            failed_tests=0,
            results=[
                DatabaseTestResult(
                    database_type=DatabaseType.REDIS,
                    host="localhost",
                    port=6379,
                    status=TestStatus.SUCCESS,
                    connection_time=0.1,
                    read_time=0.05,
                    write_time=0.03,
                    details={"redis_version": "6.2.0", "memory_usage": "1.5M"}
                ),
                DatabaseTestResult(
                    database_type=DatabaseType.POSTGRESQL,
                    host="localhost",
                    port=5432,
                    status=TestStatus.SUCCESS,
                    connection_time=0.2,
                    read_time=0.1,
                    write_time=0.08,
                    details={"database_name": "test_db", "current_user": "user"}
                )
            ],
            overall_status=TestStatus.SUCCESS,
            test_duration=0.5
        )

        report = tester.generate_test_report(summary)

        assert "DATABASE CONNECTION TEST REPORT" in report
        assert "Total Tests: 2" in report
        assert "Successful: 2" in report
        assert "Failed: 0" in report
        assert "Overall Status: SUCCESS" in report
        assert "✅ REDIS - localhost:6379 (success)" in report
        assert "✅ POSTGRESQL - localhost:5432 (success)" in report
        assert "Redis Version: 6.2.0" in report
        assert "Database: test_db" in report

    def test_generate_test_report_failures(self, tester):
        """Test generating test report with failures"""
        summary = DatabaseTestSummary(
            total_tests=1,
            successful_tests=0,
            failed_tests=1,
            results=[
                DatabaseTestResult(
                    database_type=DatabaseType.REDIS,
                    host="localhost",
                    port=6379,
                    status=TestStatus.FAILURE,
                    connection_time=5.0,
                    error_message="Connection refused"
                )
            ],
            overall_status=TestStatus.FAILURE,
            test_duration=5.0
        )

        report = tester.generate_test_report(summary)

        assert "Overall Status: FAILURE" in report
        assert "❌ REDIS - localhost:6379 (failure)" in report
        assert "Error: Connection refused" in report

    def test_save_test_results_success(self, tester):
        """Test saving test results to file"""
        summary = DatabaseTestSummary(
            total_tests=1,
            successful_tests=1,
            failed_tests=0,
            results=[
                DatabaseTestResult(
                    database_type=DatabaseType.REDIS,
                    host="localhost",
                    port=6379,
                    status=TestStatus.SUCCESS,
                    connection_time=0.1,
                    details={"version": "6.2.0"}
                )
            ],
            overall_status=TestStatus.SUCCESS,
            test_duration=0.1
        )

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as tmp_file:
            output_file = tmp_file.name

        try:
            success = tester.save_test_results(summary, output_file)
            assert success is True

            # Verify file contents
            with open(output_file, 'r') as f:
                data = json.load(f)

            assert data["test_count"] == 1
            assert data["success_count"] == 1
            assert data["failure_count"] == 0
            assert data["overall_status"] == "success"
            assert len(data["test_summary"]["results"]) == 1
            assert data["test_summary"]["results"][0]["database_type"] == "redis"

        finally:
            # Cleanup
            Path(output_file).unlink(missing_ok=True)

    def test_save_test_results_failure(self, tester):
        """Test saving test results with invalid path"""
        summary = DatabaseTestSummary(
            total_tests=0,
            successful_tests=0,
            failed_tests=0,
            results=[],
            overall_status=TestStatus.SUCCESS,
            test_duration=0.0
        )

        # Try to save to an invalid path
        invalid_path = "/invalid/path/that/does/not/exist/results.json"
        success = tester.save_test_results(summary, invalid_path)
        assert success is False


class TestDatabaseTesterIntegration:
    """Integration tests for DatabaseTester"""

    @pytest.fixture
    def tester(self):
        """Create database tester instance for integration tests"""
        return DatabaseTester()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_real_redis_mock(self, tester):
        """Test Redis testing with real-like mock data"""
        config = DatabaseTestConfig(host="localhost", port=6379)

        # Create comprehensive mock
        mock_client = Mock()
        mock_client.info.return_value = {
            "redis_version": "6.2.6",
            "used_memory_human": "2.1M",
            "connected_clients": 3,
            "uptime_in_seconds": 7200,
            "used_memory": 2150400,
            "maxmemory": 0
        }
        # Mock set/get operations with data consistency
        stored_values = {}
        def mock_set(key, value, ex=None):
            stored_values[key] = value
            return True
        def mock_get(key):
            return stored_values.get(key, None)
        def mock_delete(key):
            return stored_values.pop(key, None)

        mock_client.set = mock_set
        mock_client.get = mock_get
        mock_client.delete = mock_delete

        with patch('core.database_tester.redis') as mock_redis:
            mock_redis.Redis.return_value = mock_client

            result = await tester.test_redis_connection(config)

        assert result.status == TestStatus.SUCCESS
        assert result.connection_time > 0
        assert result.read_time > 0
        assert result.write_time > 0
        assert result.details["redis_version"] == "6.2.6"
        assert result.details["memory_usage"] == "2.1M"
        assert result.details["connected_clients"] == 3

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_real_postgresql_mock(self, tester):
        """Test PostgreSQL testing with real-like mock data"""
        config = DatabaseTestConfig(
            host="localhost",
            port=5432,
            database="testdb",
            username="testuser",
            password="testpass",
            ssl_mode="require"
        )

        mock_connection = Mock()
        mock_cursor = Mock()
        mock_connection.cursor.return_value = mock_cursor

        # Store test data for integrity check
        stored_test_data = None

        def mock_execute(query, params=None):
            # Store the test data when inserting
            if "INSERT INTO" in query and params:
                nonlocal stored_test_data
                stored_test_data = params[0]

        def mock_fetchone():
            # Return appropriate data based on the query context
            # First call: version, second call: database info, third call: read test
            if mock_fetchone.call_count == 1:
                return ("PostgreSQL 14.1, compiled by Visual C++ build 1914, 64-bit",)
            elif mock_fetchone.call_count == 2:
                return ("testdb", "testuser")
            else:
                return (stored_test_data,) if stored_test_data else ("test_data_integration",)

        mock_cursor.execute = mock_execute
        mock_cursor.fetchone = mock_fetchone
        mock_cursor.call_count = 0

        with patch('core.database_tester.psycopg2') as mock_psycopg2:
            mock_psycopg2.connect.return_value = mock_connection
            mock_psycopg2.OperationalError = Exception

            result = await tester.test_postgresql_connection(config)

        assert result.status == TestStatus.SUCCESS
        assert result.connection_time > 0
        assert result.read_time > 0
        assert result.write_time > 0
        assert "PostgreSQL 14.1" in result.details["database_version"]
        assert result.details["database_name"] == "testdb"
        assert result.details["current_user"] == "testuser"
        assert result.details["ssl_mode"] == "require"