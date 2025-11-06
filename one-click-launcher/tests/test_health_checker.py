"""
健康检查器测试

测试HTTP健康检查、连接检查、进程检查和重试机制。
"""

import pytest
import asyncio
import aiohttp
from unittest.mock import Mock, patch, AsyncMock
import psutil
from datetime import datetime
import sys

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from core.health_checker import (
    HealthChecker, HealthCheckConfig, HealthStatus, HealthCheckResult,
    ServiceInfo, ServiceType
)
from pathlib import Path


class TestHealthCheckResult:
    """测试HealthCheckResult类"""

    def test_health_check_result_creation(self):
        """测试健康检查结果创建"""
        result = HealthCheckResult(
            status=HealthStatus.HEALTHY,
            service_name="test-service",
            check_type="http",
            response_time=0.5,
            message="检查成功"
        )

        assert result.status == HealthStatus.HEALTHY
        assert result.service_name == "test-service"
        assert result.check_type == "http"
        assert result.response_time == 0.5
        assert result.message == "检查成功"
        assert isinstance(result.timestamp, datetime)

    def test_health_check_result_to_dict(self):
        """测试健康检查结果转换为字典"""
        result = HealthCheckResult(
            status=HealthStatus.HEALTHY,
            service_name="test-service",
            check_type="http",
            response_time=0.5
        )

        data = result.to_dict()
        assert data['status'] == "healthy"
        assert data['service_name'] == "test-service"
        assert data['check_type'] == "http"
        assert data['response_time'] == 0.5
        assert 'timestamp' in data


class TestHealthChecker:
    """测试HealthChecker类"""

    @pytest.fixture
    def checker(self):
        """创建健康检查器实例"""
        config = HealthCheckConfig(
            timeout=5,
            max_retries=2,
            retry_delay=0.1  # 缩短测试时间
        )
        return HealthChecker(config)

    @pytest.mark.asyncio
    async def test_http_health_check_success(self, checker):
        """测试HTTP健康检查成功"""
        # 模拟成功的HTTP响应
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text.return_value = "OK"
        mock_response.headers = {"Content-Type": "text/plain"}

        mock_session = AsyncMock()
        mock_session.request.return_value.__aenter__.return_value = mock_response

        with patch('aiohttp.ClientSession') as mock_client_session:
            mock_client_session.return_value.__aenter__.return_value = mock_session

            result = await checker.check_http_health("http://localhost:8000/health")

            assert result.status == HealthStatus.HEALTHY
            assert result.service_name == "localhost:8000"
            assert result.check_type == "http"
            assert result.response_time is not None
            assert "200" in result.message

    @pytest.mark.asyncio
    async def test_http_health_check_failure(self, checker):
        """测试HTTP健康检查失败"""
        # 模拟连接错误
        with patch('aiohttp.ClientSession') as mock_client_session:
            mock_client_session.side_effect = aiohttp.ClientConnectorError("Connection refused")

            result = await checker.check_http_health("http://localhost:8000/health")

            assert result.status == HealthStatus.CONNECTION_ERROR
            assert "Connection refused" in result.message

    @pytest.mark.asyncio
    async def test_http_health_check_timeout(self, checker):
        """测试HTTP健康检查超时"""
        # 模拟超时
        with patch('aiohttp.ClientSession') as mock_client_session:
            mock_client_session.side_effect = asyncio.TimeoutError()

            result = await checker.check_http_health("http://localhost:8000/health")

            assert result.status == HealthStatus.TIMEOUT
            assert "超时" in result.message

    @pytest.mark.asyncio
    async def test_connection_health_check_success(self, checker):
        """测试连接健康检查成功"""
        # 模拟成功的连接
        mock_reader = AsyncMock()
        mock_writer = AsyncMock()
        mock_writer.get_extra_info.return_value = ("127.0.0.1", 12345)

        with patch('asyncio.open_connection', return_value=(mock_reader, mock_writer)):
            result = await checker.check_connection_health("localhost", 8000)

            assert result.status == HealthStatus.HEALTHY
            assert result.service_name == "localhost:8000"
            assert result.check_type == "connection"
            assert result.response_time is not None

    @pytest.mark.asyncio
    async def test_connection_health_check_failure(self, checker):
        """测试连接健康检查失败"""
        # 模拟连接被拒绝
        with patch('asyncio.open_connection', side_effect=ConnectionRefusedError()):
            result = await checker.check_connection_health("localhost", 8000)

            assert result.status == HealthStatus.CONNECTION_ERROR
            assert "连接被拒绝" in result.message

    @pytest.mark.asyncio
    async def test_process_health_check_success(self, checker):
        """测试进程健康检查成功"""
        # 模拟进程
        mock_process = Mock()
        mock_process.pid = 1234
        mock_process.name.return_value = "python"
        mock_process.status.return_value = psutil.STATUS_RUNNING
        mock_process.cpu_percent.return_value = 5.0
        mock_process.memory_info.return_value = Mock(rss=1024*1024*10)  # 10MB
        mock_process.create_time.return_value = 1234567890
        mock_process.cmdline.return_value = ["python", "app.py"]

        with patch('psutil.process_iter') as mock_iter:
            mock_iter.return_value = [Mock(info={'pid': 1234, 'name': 'python', 'cmdline': ['python', 'app.py']})]
            with patch('psutil.Process', return_value=mock_process):
                result = await checker.check_process_health("python")

                assert result.status == HealthStatus.HEALTHY
                assert result.service_name == "python"
                assert result.check_type == "process"
                assert "找到 1 个健康进程" in result.message

    @pytest.mark.asyncio
    async def test_process_health_check_not_found(self, checker):
        """测试进程健康检查未找到进程"""
        with patch('psutil.process_iter', return_value=[]):
            result = await checker.check_process_health("nonexistent")

            assert result.status == HealthStatus.UNHEALTHY
            assert "未找到进程" in result.message

    @pytest.mark.asyncio
    async def test_service_health_check_backend_api(self, checker):
        """测试Backend API服务健康检查"""
        service = ServiceInfo(
            name="backend-api",
            service_type=ServiceType.BACKEND_API,
            host="localhost",
            port=8000,
            health_endpoint="/health"
        )

        # 模拟HTTP健康检查成功
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_session = AsyncMock()
        mock_session.request.return_value.__aenter__.return_value = mock_response

        with patch('aiohttp.ClientSession') as mock_client_session:
            mock_client_session.return_value.__aenter__.return_value = mock_session

            result = await checker.check_service_health(service)

            assert result.check_type == "http"
            # 由于mock设置，结果应该是成功的

    @pytest.mark.asyncio
    async def test_service_health_check_database(self, checker):
        """测试数据库服务健康检查"""
        service = ServiceInfo(
            name="redis",
            service_type=ServiceType.CACHE,
            host="localhost",
            port=6379
        )

        # 模拟连接检查成功
        mock_reader = AsyncMock()
        mock_writer = AsyncMock()

        with patch('asyncio.open_connection', return_value=(mock_reader, mock_writer)):
            result = await checker.check_service_health(service)

            assert result.check_type == "connection"

    @pytest.mark.asyncio
    async def test_service_health_check_with_retry_success(self, checker):
        """测试带重试的服务健康检查成功"""
        service = ServiceInfo(
            name="test-service",
            service_type=ServiceType.BACKEND_API,
            host="localhost",
            port=8000
        )

        # 模拟第一次失败，第二次成功
        call_count = 0

        async def mock_check_service_health(service_info):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return HealthCheckResult(
                    status=HealthStatus.UNHEALTHY,
                    service_name=service_info.name,
                    check_type="http",
                    message="模拟失败"
                )
            else:
                return HealthCheckResult(
                    status=HealthStatus.HEALTHY,
                    service_name=service_info.name,
                    check_type="http",
                    message="成功"
                )

        with patch.object(checker, 'check_service_health', side_effect=mock_check_service_health):
            result = await checker.check_service_health_with_retry(service)

            assert result.status == HealthStatus.HEALTHY
            assert call_count == 2  # 应该调用了两次

    @pytest.mark.asyncio
    async def test_service_health_check_with_retry_failure(self, checker):
        """测试带重试的服务健康检查失败"""
        service = ServiceInfo(
            name="test-service",
            service_type=ServiceType.BACKEND_API,
            host="localhost",
            port=8000
        )

        # 模拟始终失败
        with patch.object(checker, 'check_service_health', return_value=HealthCheckResult(
            status=HealthStatus.UNHEALTHY,
            service_name=service.name,
            check_type="http",
            message="始终失败"
        )):
            result = await checker.check_service_health_with_retry(service)

            assert result.status == HealthStatus.UNHEALTHY
            assert result.retry_count == checker.config.max_retries

    @pytest.mark.asyncio
    async def test_check_multiple_services(self, checker):
        """测试检查多个服务"""
        services = [
            ServiceInfo(name="service1", service_type=ServiceType.BACKEND_API, host="localhost", port=8001),
            ServiceInfo(name="service2", service_type=ServiceType.DATABASE, host="localhost", port=8002)
        ]

        # 模拟健康检查结果
        async def mock_check_service_health_with_retry(service):
            return HealthCheckResult(
                status=HealthStatus.HEALTHY,
                service_name=service.name,
                check_type="mock",
                message="模拟成功"
            )

        with patch.object(checker, 'check_service_health_with_retry', side_effect=mock_check_service_health_with_retry):
            results = await checker.check_multiple_services(services)

            assert len(results) == 2
            assert "service1" in results
            assert "service2" in results
            assert all(result.status == HealthStatus.HEALTHY for result in results.values())

    def test_update_health_cache(self, checker):
        """测试更新健康状态缓存"""
        result = HealthCheckResult(
            status=HealthStatus.HEALTHY,
            service_name="test-service",
            check_type="http",
            response_time=0.5
        )

        checker._update_health_cache("test-service", result)

        assert "test-service" in checker.health_cache
        assert checker.health_cache["test-service"] == result
        assert "test-service" in checker.check_history
        assert len(checker.check_history["test-service"]) == 1

        # 检查统计信息更新
        assert "test-service" in checker.check_stats
        stats = checker.check_stats["test-service"]
        assert stats['total_checks'] == 1
        assert stats['healthy_checks'] == 1
        assert stats['uptime_percentage'] == 100.0

    def test_get_health_summary(self, checker):
        """测试获取健康检查摘要"""
        # 添加一些检查结果
        results = [
            HealthCheckResult(status=HealthStatus.HEALTHY, service_name="service1", check_type="http"),
            HealthCheckResult(status=HealthStatus.UNHEALTHY, service_name="service2", check_type="connection"),
            HealthCheckResult(status=HealthStatus.HEALTHY, service_name="service3", check_type="process")
        ]

        for result in results:
            checker._update_health_cache(result.service_name, result)

        summary = checker.get_health_summary()

        assert summary['total_services'] == 3
        assert summary['healthy_services'] == 2
        assert summary['unhealthy_services'] == 1
        assert summary['health_percentage'] == pytest.approx(66.67, rel=1e-2)

    def test_get_service_health_history(self, checker):
        """测试获取服务健康检查历史"""
        service_name = "test-service"

        # 添加多个检查结果
        for i in range(5):
            result = HealthCheckResult(
                status=HealthStatus.HEALTHY if i % 2 == 0 else HealthStatus.UNHEALTHY,
                service_name=service_name,
                check_type="http"
            )
            checker._update_health_cache(service_name, result)

        # 获取历史记录
        history = checker.get_service_health_history(service_name)
        assert len(history) == 5

        # 获取限制数量的历史记录
        limited_history = checker.get_service_health_history(service_name, limit=3)
        assert len(limited_history) == 3

    def test_clear_cache_and_history(self, checker):
        """测试清空缓存和历史记录"""
        # 添加一些数据
        result = HealthCheckResult(
            status=HealthStatus.HEALTHY,
            service_name="test-service",
            check_type="http"
        )
        checker._update_health_cache("test-service", result)

        assert len(checker.health_cache) > 0
        assert len(checker.check_history) > 0

        # 清空缓存
        checker.clear_cache()
        assert len(checker.health_cache) == 0
        assert len(checker.check_history) > 0  # 历史记录应该保留

        # 清空历史记录
        checker.clear_history()
        assert len(checker.check_history) == 0
        assert len(checker.check_stats) == 0

    def test_extract_service_name_from_url(self, checker):
        """测试从URL提取服务名称"""
        # 测试带端口的URL
        service_name = checker._extract_service_name_from_url("http://localhost:8000/health")
        assert service_name == "localhost:8000"

        # 测试不带端口的URL
        service_name = checker._extract_service_name_from_url("http://api.example.com/health")
        assert service_name == "api.example.com"

        # 测试无效URL
        service_name = checker._extract_service_name_from_url("invalid-url")
        assert service_name == "unknown"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])