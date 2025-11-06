"""
后端服务集成测试

测试后端服务启动、API端点验证、数据库连接和错误处理等功能。
"""

import pytest
import asyncio
import time
import os
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path

from services.backend_service import (
    BackendServiceManager, BackendServiceConfig, BackendServiceStatus, BackendServiceInfo
)
from core.health_checker import HealthStatus
from utils.api_utils import EndpointCheckResult
from utils.logger import get_logger

logger = get_logger(__name__)


class TestBackendServiceManager:
    """后端服务管理器测试"""

    @pytest.fixture
    def backend_config(self):
        """后端服务配置fixture"""
        return BackendServiceConfig(
            service_name="test_backend",
            host="localhost",
            port=8001,  # Use different port for testing
            backend_type="fastapi",
            working_directory="backend",
            startup_script="main.py",
            startup_timeout=10,
            health_check_interval=2,
            max_retries=2,
            redis_host="localhost",
            redis_port=6379,
            postgres_host="localhost",
            postgres_port=5432
        )

    @pytest.fixture
    def backend_manager(self, backend_config):
        """后端服务管理器fixture"""
        return BackendServiceManager(backend_config)

    @pytest.mark.asyncio
    async def test_backend_service_initialization(self, backend_manager, backend_config):
        """测试后端服务初始化"""
        assert backend_manager.config == backend_config
        assert backend_manager.service_info.status == BackendServiceStatus.NOT_STARTED
        assert backend_manager.service_info.config == backend_config
        assert backend_manager.service_info.process_id is None
        assert not backend_manager._is_running

    @pytest.mark.asyncio
    async def test_dependencies_check_success(self, backend_manager):
        """测试依赖检查成功"""
        with patch.object(backend_manager.health_checker, 'check_service_health') as mock_check:
            # Mock successful dependency checks
            mock_check.return_value = Mock(
                status=HealthStatus.HEALTHY,
                message="Service is healthy"
            )

            # Should not raise exception
            await backend_manager._check_dependencies()

            # Verify dependencies were checked
            assert mock_check.call_count == 2  # Redis and PostgreSQL

    @pytest.mark.asyncio
    async def test_dependencies_check_failure(self, backend_manager):
        """测试依赖检查失败"""
        with patch.object(backend_manager.health_checker, 'check_service_health') as mock_check:
            # Mock failed dependency check
            mock_check.return_value = Mock(
                status=HealthStatus.UNHEALTHY,
                message="Service is unhealthy"
            )

            # Should raise exception
            with pytest.raises(Exception, match="Dependency redis is not healthy"):
                await backend_manager._check_dependencies()

    @pytest.mark.asyncio
    async def test_service_configuration(self, backend_manager):
        """测试服务配置"""
        with patch.object(backend_manager.service_configurator, 'load_env_file') as mock_load_env, \
             patch.object(backend_manager.port_manager, 'check_port_availability') as mock_check_port, \
             patch('os.environ', {}):

            # Mock port availability check
            mock_check_port.return_value = True

            await backend_manager._configure_service()

            # Verify environment variables were set
            assert os.environ.get("LOG_LEVEL") == backend_manager.config.log_level
            assert os.environ.get("REDIS_HOST") == backend_manager.config.redis_host
            assert os.environ.get("REDIS_PORT") == str(backend_manager.config.redis_port)

            # Verify port was checked
            mock_check_port.assert_called_once_with(
                backend_manager.config.port
            )

    @pytest.mark.asyncio
    async def test_backend_process_start_success(self, backend_manager):
        """测试后端进程启动成功"""
        with patch('subprocess.Popen') as mock_popen, \
             patch('psutil.Process') as mock_psutil_process, \
             patch.object(backend_manager, '_is_process_running') as mock_is_running:

            # Mock subprocess start
            mock_process = Mock()
            mock_process.pid = 12345
            mock_popen.return_value = mock_process

            # Mock process status check
            mock_psutil_process.return_value.is_running.return_value = True
            mock_psutil_process.return_value.status.return_value = "running"
            mock_is_running.return_value = True

            await backend_manager._start_backend_process()

            # Verify process was started
            mock_popen.assert_called_once()
            assert backend_manager.service_info.process_id == 12345
            mock_is_running.assert_called_once()

    @pytest.mark.asyncio
    async def test_backend_process_start_failure(self, backend_manager):
        """测试后端进程启动失败"""
        with patch('subprocess.Popen') as mock_popen, \
             patch.object(backend_manager, '_is_process_running') as mock_is_running:

            # Mock subprocess start
            mock_process = Mock()
            mock_process.pid = 12345
            mock_popen.return_value = mock_process

            # Mock process status check (process died)
            mock_is_running.return_value = False

            # Should raise exception
            with pytest.raises(Exception, match="Backend process failed to start"):
                await backend_manager._start_backend_process()

    @pytest.mark.asyncio
    async def test_api_endpoints_verification_success(self, backend_manager):
        """测试API端点验证成功"""
        with patch.object(backend_manager, '_check_health_endpoint') as mock_health, \
             patch.object(backend_manager, '_check_docs_endpoint') as mock_docs:

            # Mock successful endpoint checks
            mock_health.return_value = Mock(
                status=HealthStatus.HEALTHY,
                response_time=0.5
            )
            mock_docs.return_value = Mock(
                status=HealthStatus.HEALTHY
            )

            # Should not raise exception
            await backend_manager._verify_api_endpoints()

            # Verify endpoints were checked
            mock_health.assert_called_once()
            mock_docs.assert_called_once()

    @pytest.mark.asyncio
    async def test_api_endpoints_verification_health_failure(self, backend_manager):
        """测试API健康端点验证失败"""
        with patch.object(backend_manager, '_check_health_endpoint') as mock_health:
            # Mock failed health check
            mock_health.return_value = Mock(
                status=HealthStatus.UNHEALTHY,
                message="Health check failed"
            )

            # Should raise exception
            with pytest.raises(Exception, match="Health endpoint verification failed"):
                await backend_manager._verify_api_endpoints()

    @pytest.mark.asyncio
    async def test_api_endpoints_verification_docs_failure(self, backend_manager):
        """测试API文档端点验证失败"""
        with patch.object(backend_manager, '_check_health_endpoint') as mock_health, \
             patch.object(backend_manager, '_check_docs_endpoint') as mock_docs:

            # Mock successful health check but failed docs check
            mock_health.return_value = Mock(
                status=HealthStatus.HEALTHY
            )
            mock_docs.return_value = Mock(
                status=HealthStatus.UNHEALTHY,
                message="Docs endpoint failed"
            )

            # Should raise exception
            with pytest.raises(Exception, match="Docs endpoint verification failed"):
                await backend_manager._verify_api_endpoints()

    @pytest.mark.asyncio
    async def test_api_endpoints_verification_slow_response(self, backend_manager):
        """测试API端点响应时间过慢"""
        with patch.object(backend_manager, '_check_health_endpoint') as mock_health, \
             patch.object(backend_manager, '_check_docs_endpoint') as mock_docs:

            # Mock successful checks but slow response time
            mock_health.return_value = Mock(
                status=HealthStatus.HEALTHY,
                response_time=3.0  # Over 2 second threshold
            )
            mock_docs.return_value = Mock(
                status=HealthStatus.HEALTHY
            )

            # Should raise exception for slow response
            with pytest.raises(Exception, match="Health endpoint response time too slow"):
                await backend_manager._verify_api_endpoints()

    @pytest.mark.asyncio
    async def test_application_state_initialization(self, backend_manager):
        """测试应用状态初始化"""
        await backend_manager._initialize_application_state()

        # Verify startup log was updated
        assert any("Application state initialized" in log
                  for log in backend_manager.service_info.startup_log)

    @pytest.mark.asyncio
    async def test_process_running_check_true(self, backend_manager):
        """测试进程运行检查 - 运行中"""
        backend_manager.service_info.process_id = 12345

        with patch('psutil.Process') as mock_psutil_process:
            mock_process = Mock()
            mock_process.is_running.return_value = True
            mock_process.status.return_value = "running"
            mock_psutil_process.return_value = mock_process

            result = await backend_manager._is_process_running()
            assert result is True

    @pytest.mark.asyncio
    async def test_process_running_check_false(self, backend_manager):
        """测试进程运行检查 - 未运行"""
        backend_manager.service_info.process_id = 12345

        with patch('psutil.Process') as mock_psutil_process:
            # Mock process not found
            mock_psutil_process.side_effect = Exception("No such process")

            result = await backend_manager._is_process_running()
            assert result is False

    @pytest.mark.asyncio
    async def test_process_running_check_no_pid(self, backend_manager):
        """测试进程运行检查 - 无PID"""
        backend_manager.service_info.process_id = None

        result = await backend_manager._is_process_running()
        assert result is False

    @pytest.mark.asyncio
    async def test_backend_service_start_success(self, backend_manager):
        """测试后端服务启动成功"""
        with patch.object(backend_manager, '_check_dependencies') as mock_deps, \
             patch.object(backend_manager, '_configure_service') as mock_config, \
             patch.object(backend_manager, '_start_backend_process') as mock_start, \
             patch.object(backend_manager, '_verify_api_endpoints') as mock_verify, \
             patch.object(backend_manager, '_initialize_application_state') as mock_init:

            # Mock all steps to succeed
            mock_deps.return_value = None
            mock_config.return_value = None
            mock_start.return_value = None
            mock_verify.return_value = None
            mock_init.return_value = None

            result = await backend_manager.start()

            assert result is True
            assert backend_manager.service_info.status == BackendServiceStatus.RUNNING
            assert backend_manager._is_running is True
            assert backend_manager.service_info.start_time is not None

            # Verify all steps were called
            mock_deps.assert_called_once()
            mock_config.assert_called_once()
            mock_start.assert_called_once()
            mock_verify.assert_called_once()
            mock_init.assert_called_once()

    @pytest.mark.asyncio
    async def test_backend_service_start_failure(self, backend_manager):
        """测试后端服务启动失败"""
        with patch.object(backend_manager, '_check_dependencies') as mock_deps:
            # Mock dependency check failure
            mock_deps.side_effect = Exception("Dependency check failed")

            result = await backend_manager.start()

            assert result is False
            assert backend_manager.service_info.status == BackendServiceStatus.FAILED
            assert backend_manager.service_info.error_message == "Dependency check failed"
            assert not backend_manager._is_running

    @pytest.mark.asyncio
    async def test_backend_service_stop_success(self, backend_manager):
        """测试后端服务停止成功"""
        # Set up running service
        backend_manager.service_info.status = BackendServiceStatus.RUNNING
        backend_manager.service_info.process_id = 12345
        backend_manager._is_running = True

        with patch.object(backend_manager, '_stop_backend_process') as mock_stop:
            await backend_manager.stop()

            assert backend_manager.service_info.status == BackendServiceStatus.STOPPED
            assert not backend_manager._is_running
            mock_stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_health_check_comprehensive_success(self, backend_manager):
        """测试综合健康检查成功"""
        # Set up running service
        backend_manager.service_info.process_id = 12345

        with patch.object(backend_manager, '_is_process_running') as mock_process, \
             patch.object(backend_manager, '_check_health_endpoint') as mock_health, \
             patch.object(backend_manager, '_check_docs_endpoint') as mock_docs, \
             patch.object(backend_manager, '_check_database_connections') as mock_db:

            # Mock all checks to succeed
            mock_process.return_value = True
            mock_health.return_value = Mock(
                status=HealthStatus.HEALTHY,
                to_dict=lambda: {"status": "healthy"}
            )
            mock_docs.return_value = Mock(
                status=HealthStatus.HEALTHY,
                to_dict=lambda: {"status": "healthy"}
            )
            mock_db.return_value = Mock(
                status=HealthStatus.HEALTHY,
                to_dict=lambda: {"status": "healthy"}
            )

            result = await backend_manager.health_check()

            assert result.status == HealthStatus.HEALTHY
            assert result.service_name == backend_manager.config.service_name
            assert "All checks passed" in result.message

            # Verify all checks were called
            mock_process.assert_called_once()
            mock_health.assert_called_once()
            mock_docs.assert_called_once()
            mock_db.assert_called_once()

    @pytest.mark.asyncio
    async def test_health_check_process_not_running(self, backend_manager):
        """测试健康检查 - 进程未运行"""
        backend_manager.service_info.process_id = 12345

        with patch.object(backend_manager, '_is_process_running') as mock_process:
            mock_process.return_value = False

            result = await backend_manager.health_check()

            assert result.status == HealthStatus.UNHEALTHY
            assert "Backend process is not running" in result.message

    @pytest.mark.asyncio
    async def test_health_check_database_failure(self, backend_manager):
        """测试健康检查 - 数据库连接失败"""
        # Set up running service
        backend_manager.service_info.process_id = 12345

        with patch.object(backend_manager, '_is_process_running') as mock_process, \
             patch.object(backend_manager, '_check_health_endpoint') as mock_health, \
             patch.object(backend_manager, '_check_docs_endpoint') as mock_docs, \
             patch.object(backend_manager, '_check_database_connections') as mock_db:

            # Mock process and API checks to succeed, but database to fail
            mock_process.return_value = True
            mock_health.return_value = Mock(
                status=HealthStatus.HEALTHY,
                to_dict=lambda: {"status": "healthy"}
            )
            mock_docs.return_value = Mock(
                status=HealthStatus.HEALTHY,
                to_dict=lambda: {"status": "healthy"}
            )
            mock_db.return_value = Mock(
                status=HealthStatus.UNHEALTHY,
                message="Database connection failed",
                to_dict=lambda: {"status": "unhealthy", "message": "Database connection failed"}
            )

            result = await backend_manager.health_check()

            assert result.status == HealthStatus.UNHEALTHY
            assert "Database: Database connection failed" in result.message

    @pytest.mark.asyncio
    async def test_get_service_status(self, backend_manager):
        """测试获取服务状态"""
        status = await backend_manager.get_status()
        assert isinstance(status, BackendServiceInfo)
        assert status == backend_manager.service_info

    @pytest.mark.asyncio
    async def test_restart_service(self, backend_manager):
        """测试重启服务"""
        with patch.object(backend_manager, 'stop') as mock_stop, \
             patch.object(backend_manager, 'start') as mock_start:

            mock_stop.return_value = True
            mock_start.return_value = True

            result = await backend_manager.restart()

            assert result is True
            assert backend_manager.service_info.restart_count == 1
            mock_stop.assert_called_once()
            mock_start.assert_called_once()


class TestAPIUtils:
    """API工具测试"""

    @pytest.mark.asyncio
    async def test_check_endpoint_success(self):
        """测试端点检查成功"""
        from utils.api_utils import APIUtils

        with patch('aiohttp.ClientSession.request') as mock_request:
            # Mock successful response
            mock_response = Mock()
            mock_response.status = 200
            mock_response.headers = {'content-length': '100'}
            mock_response.text = AsyncMock(return_value="OK")

            mock_request.return_value.__aenter__.return_value = mock_response

            async with APIUtils() as api_utils:
                result = await api_utils.check_endpoint("http://localhost:8000/health")

            assert result.is_accessible is True
            assert result.status_code == 200
            assert result.content_length == 100
            assert result.error_message is None

    @pytest.mark.asyncio
    async def test_check_endpoint_failure(self):
        """测试端点检查失败"""
        from utils.api_utils import APIUtils

        with patch('aiohttp.ClientSession.request') as mock_request:
            # Mock connection error
            import aiohttp
            mock_request.side_effect = aiohttp.ClientError("Connection refused")

            async with APIUtils() as api_utils:
                result = await api_utils.check_endpoint("http://localhost:8000/health")

            assert result.is_accessible is False
            assert result.status_code is None
            assert "Connection error" in result.error_message

    @pytest.mark.asyncio
    async def test_check_endpoint_timeout(self):
        """测试端点检查超时"""
        from utils.api_utils import APIUtils

        with patch('aiohttp.ClientSession.request') as mock_request:
            # Mock timeout
            mock_request.side_effect = asyncio.TimeoutError()

            async with APIUtils(timeout=5) as api_utils:
                result = await api_utils.check_endpoint("http://localhost:8000/health")

            assert result.is_accessible is False
            assert result.status_code is None
            assert "Request timeout after 5s" in result.error_message


# Integration tests

@pytest.mark.integration
class TestBackendServiceIntegration:
    """后端服务集成测试"""

    @pytest.mark.asyncio
    async def test_complete_backend_startup_flow(self):
        """测试完整后端启动流程"""
        # This test would require actual backend service to be available
        # For now, we'll test the flow with mocked dependencies

        config = BackendServiceConfig(
            service_name="integration_test_backend",
            host="localhost",
            port=8002,
            startup_timeout=5
        )

        manager = BackendServiceManager(config)

        # Mock all external dependencies
        with patch.object(manager, '_check_dependencies') as mock_deps, \
             patch.object(manager, '_configure_service') as mock_config, \
             patch.object(manager, '_start_backend_process') as mock_start, \
             patch.object(manager, '_verify_api_endpoints') as mock_verify, \
             patch.object(manager, '_initialize_application_state') as mock_init:

            # Configure mocks to succeed
            mock_deps.return_value = None
            mock_config.return_value = None
            mock_start.return_value = None
            mock_verify.return_value = None
            mock_init.return_value = None

            # Start the service
            result = await manager.start()

            assert result is True
            assert manager.service_info.status == BackendServiceStatus.RUNNING

            # Test health check
            with patch.object(manager, '_is_process_running') as mock_process, \
                 patch.object(manager, '_check_health_endpoint') as mock_health, \
                 patch.object(manager, '_check_docs_endpoint') as mock_docs, \
                 patch.object(manager, '_check_database_connections') as mock_db:

                mock_process.return_value = True
                mock_health.return_value = Mock(
                    status=HealthStatus.HEALTHY,
                    to_dict=lambda: {"status": "healthy"}
                )
                mock_docs.return_value = Mock(
                    status=HealthStatus.HEALTHY,
                    to_dict=lambda: {"status": "healthy"}
                )
                mock_db.return_value = Mock(
                    status=HealthStatus.HEALTHY,
                    to_dict=lambda: {"status": "healthy"}
                )

                health_result = await manager.health_check()
                assert health_result.status == HealthStatus.HEALTHY

            # Stop the service
            with patch.object(manager, '_stop_backend_process') as mock_stop:
                stop_result = await manager.stop()
                assert stop_result is True
                assert manager.service_info.status == BackendServiceStatus.STOPPED