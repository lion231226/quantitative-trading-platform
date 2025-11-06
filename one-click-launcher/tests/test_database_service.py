"""
数据库服务测试

测试数据库服务启动器的各种功能，包括：
- Redis服务启动和检测
- PostgreSQL服务启动和检测
- 健康检查
- 数据库初始化
- 迁移执行
- 基础数据导入
- 性能验证
"""

import pytest
import asyncio
import json
import time
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

# Import the modules to test
import sys
sys.path.append(str(Path(__file__).parent.parent))

from services.database_service import (
    DatabaseServiceManager, DatabaseServiceConfig, DatabaseServiceResult,
    DatabaseServiceStatus
)

from services.redis_service_manager import RedisServiceStatus, RedisConnectionType
from services.postgresql_service_manager import PostgreSQLServiceStatus, PostgreSQLConnectionType


class TestDatabaseServiceManager:
    """数据库服务管理器测试"""

    @pytest.fixture
    def config(self):
        """测试配置"""
        return DatabaseServiceConfig(
            redis_enabled=True,
            postgresql_enabled=True,
            redis_port=6379,
            postgresql_port=5432,
            create_database=True,
            run_migrations=True,
            import_base_data=True,
            performance_check=True
        )

    @pytest.fixture
    def service_manager(self, config):
        """创建数据库服务管理器实例"""
        return DatabaseServiceManager(config)

    def test_init_with_default_config(self):
        """测试使用默认配置初始化"""
        manager = DatabaseServiceManager()
        assert manager.config.redis_enabled is True
        assert manager.config.postgresql_enabled is True
        assert manager.config.redis_port == 6379
        assert manager.config.postgresql_port == 5432

    def test_init_with_custom_config(self, config):
        """测试使用自定义配置初始化"""
        manager = DatabaseServiceManager(config)
        assert manager.config == config
        assert manager.redis_manager is not None
        assert manager.postgresql_manager is not None
        assert manager.port_manager is not None
        assert manager.timeout_manager is not None
        assert manager.health_checker is not None

    def test_init_with_config_file(self, tmp_path):
        """测试使用配置文件初始化"""
        config_file = tmp_path / "test_config.json"
        config_data = {
            "redis_enabled": False,
            "postgresql_enabled": True,
            "redis_port": 6380,
            "postgresql_port": 5433
        }

        with open(config_file, 'w') as f:
            json.dump(config_data, f)

        manager = DatabaseServiceManager(config_file=str(config_file))
        assert manager.config.redis_enabled is False
        assert manager.config.postgresql_enabled is True
        assert manager.config.redis_port == 6380
        assert manager.config.postgresql_port == 5433

    @pytest.mark.asyncio
    async def test_analyze_service_dependencies(self, service_manager):
        """测试服务依赖分析"""
        await service_manager._analyze_service_dependencies()

        dependency_graph = service_manager.dependency_analyzer.dependency_graph
        assert "redis" in dependency_graph.services
        assert "postgresql" in dependency_graph.services

        startup_sequence = await service_manager.dependency_analyzer.calculate_startup_sequence()
        assert len(startup_sequence) == 2
        assert startup_sequence[0] == "redis"
        assert startup_sequence[1] == "postgresql"

    @pytest.mark.asyncio
    async def test_prepare_ports_available(self, service_manager):
        """测试端口准备（端口可用情况）"""
        with patch.object(service_manager.port_manager, 'check_port_availability') as mock_check:
            mock_check.return_value = True

            await service_manager._prepare_ports()

            # 端口应该保持不变
            assert service_manager.config.redis_port == 6379
            assert service_manager.config.postgresql_port == 5432

    @pytest.mark.asyncio
    async def test_prepare_ports_conflict(self, service_manager):
        """测试端口准备（端口冲突情况）"""
        with patch.object(service_manager.port_manager, 'check_port_availability') as mock_check:
            with patch.object(service_manager.port_manager, 'allocate_port') as mock_allocate:
                # Redis端口被占用
                def check_side_effect(port):
                    return port != 6379  # 只有6379端口被占用

                mock_check.side_effect = check_side_effect
                mock_allocate.return_value = 6380

                await service_manager._prepare_ports()

                # Redis端口应该被重新分配
                assert service_manager.config.redis_port == 6380
                assert service_manager.config.postgresql_port == 5432

    @pytest.mark.asyncio
    async def test_start_redis_service_success(self, service_manager):
        """测试Redis服务启动成功"""
        mock_redis_info = Mock()
        mock_redis_info.status = RedisServiceStatus.RUNNING
        mock_redis_info.host = "localhost"
        mock_redis_info.port = 6379

        with patch.object(service_manager.redis_manager, 'detect_redis_service') as mock_detect:
            with patch.object(service_manager.redis_manager, 'start_redis_service') as mock_start:
                # 首次检测返回未运行
                mock_detect.return_value = Mock(status=RedisServiceStatus.STOPPED)
                # 启动成功
                mock_start.return_value = (True, "Redis started successfully")
                # 启动后检测返回运行中
                mock_detect.side_effect = [
                    Mock(status=RedisServiceStatus.STOPPED),
                    mock_redis_info
                ]

                result = await service_manager._start_redis_service()

                assert result.status == RedisServiceStatus.RUNNING
                assert result.host == "localhost"
                assert result.port == 6379

    @pytest.mark.asyncio
    async def test_start_redis_service_already_running(self, service_manager):
        """测试Redis服务已经运行"""
        mock_redis_info = Mock()
        mock_redis_info.status = RedisServiceStatus.RUNNING
        mock_redis_info.host = "localhost"
        mock_redis_info.port = 6379

        with patch.object(service_manager.redis_manager, 'detect_redis_service') as mock_detect:
            mock_detect.return_value = mock_redis_info

            result = await service_manager._start_redis_service()

            assert result.status == RedisServiceStatus.RUNNING
            assert result.host == "localhost"
            assert result.port == 6379

    @pytest.mark.asyncio
    async def test_start_postgresql_service_success(self, service_manager):
        """测试PostgreSQL服务启动成功"""
        mock_postgresql_info = Mock()
        mock_postgresql_info.status = PostgreSQLServiceStatus.RUNNING
        mock_postgresql_info.host = "localhost"
        mock_postgresql_info.port = 5432

        with patch.object(service_manager.postgresql_manager, 'detect_postgresql_service') as mock_detect:
            with patch.object(service_manager.postgresql_manager, 'start_postgresql_service') as mock_start:
                # 首次检测返回未运行
                mock_detect.return_value = Mock(status=PostgreSQLServiceStatus.STOPPED)
                # 启动成功
                mock_start.return_value = (True, "PostgreSQL started successfully")
                # 启动后检测返回运行中
                mock_detect.side_effect = [
                    Mock(status=PostgreSQLServiceStatus.STOPPED),
                    mock_postgresql_info
                ]

                result = await service_manager._start_postgresql_service()

                assert result.status == PostgreSQLServiceStatus.RUNNING
                assert result.host == "localhost"
                assert result.port == 5432

    @pytest.mark.asyncio
    async def test_initialize_database(self, service_manager):
        """测试数据库初始化"""
        result = DatabaseServiceResult(success=True)

        # 模拟PostgreSQL服务已运行
        mock_postgresql_info = Mock()
        mock_postgresql_info.status = PostgreSQLServiceStatus.RUNNING
        result.postgresql_status = mock_postgresql_info

        with patch.object(service_manager.postgresql_manager, 'detect_postgresql_service', return_value=mock_postgresql_info):
            # 测试迁移执行
            migration_result = await service_manager.execute_migrations("migrations")
            assert migration_result['success'] is True

            # 测试基础数据导入
            data_result = await service_manager.import_base_data("data")
            assert data_result['success'] is True

        # 应该没有错误
        assert len(result.errors) == 0

    @pytest.mark.asyncio
    async def test_run_migrations_with_files(self, service_manager):
        """测试运行迁移（有迁移文件）"""
        # 创建临时迁移文件
        migration_dir = Path("test_migrations")
        migration_dir.mkdir(exist_ok=True)

        try:
            (migration_dir / "001_test.sql").write_text("-- Test migration")
            (migration_dir / "002_test.sql").write_text("-- Test migration 2")

            # Mock PostgreSQL service as running
            mock_postgresql_info = Mock()
            mock_postgresql_info.status = PostgreSQLServiceStatus.RUNNING

            with patch('asyncio.sleep', return_value=None):
                with patch.object(service_manager.postgresql_manager, 'detect_postgresql_service', return_value=mock_postgresql_info):
                    result = await service_manager.execute_migrations(str(migration_dir))

            assert result['success'] is True
            assert len(result['executed_migrations']) == 2
            assert len(result['errors']) == 0

        finally:
            # 清理测试文件
            for f in migration_dir.glob("*.sql"):
                f.unlink()
            migration_dir.rmdir()

    @pytest.mark.asyncio
    async def test_run_migrations_no_files(self, service_manager):
        """测试运行迁移（无迁移文件）"""
        # 使用空目录
        empty_dir = Path("test_empty_migrations")
        empty_dir.mkdir(exist_ok=True)

        try:
            result = await service_manager.execute_migrations(str(empty_dir))

            assert result['success'] is True
            assert len(result['executed_migrations']) == 0
            assert len(result['errors']) == 0

        finally:
            empty_dir.rmdir()

    @pytest.mark.asyncio
    async def test_import_base_data_with_file(self, service_manager):
        """测试导入基础数据（有数据文件）"""
        result = DatabaseServiceResult(success=True)

        # 创建临时数据文件
        data_dir = Path("test_data")
        data_dir.mkdir(exist_ok=True)

        try:
            (data_dir / "base_data.json").write_text('{"test": "data"}')

            # Mock PostgreSQL service as running
            mock_postgresql_info = Mock()
            mock_postgresql_info.status = PostgreSQLServiceStatus.RUNNING

            with patch('asyncio.sleep', return_value=None):
                with patch.object(service_manager.postgresql_manager, 'detect_postgresql_service', return_value=mock_postgresql_info):
                    data_result = await service_manager.import_base_data(str(data_dir))

            assert data_result['success'] is True
            assert len(result.errors) == 0

        finally:
            # 清理测试文件
            for f in data_dir.glob("*.json"):
                f.unlink()
            data_dir.rmdir()

    @pytest.mark.asyncio
    async def test_import_base_data_no_file(self, service_manager):
        """测试导入基础数据（无数据文件）"""
        # 使用空目录
        empty_dir = Path("test_empty_data")
        empty_dir.mkdir(exist_ok=True)

        try:
            data_result = await service_manager.import_base_data(str(empty_dir))

            assert data_result['success'] is True
            assert len(data_result['imported_files']) == 0

        finally:
            empty_dir.rmdir()

    @pytest.mark.asyncio
    async def test_verify_performance(self, service_manager):
        """测试性能验证"""
        result = DatabaseServiceResult(success=True)

        # 模拟服务运行状态
        mock_redis_info = Mock()
        mock_redis_info.status = RedisServiceStatus.RUNNING
        mock_redis_info.host = "localhost"
        mock_redis_info.port = 6379

        mock_postgresql_info = Mock()
        mock_postgresql_info.status = PostgreSQLServiceStatus.RUNNING
        mock_postgresql_info.host = "localhost"
        mock_postgresql_info.port = 5432

        result.redis_status = mock_redis_info
        result.postgresql_status = mock_postgresql_info

        with patch('time.time', side_effect=[0, 0.05, 0, 0.15]):
            performance_result = await service_manager.run_performance_benchmark()

        assert 'redis' in result.performance_metrics
        assert 'postgresql' in result.performance_metrics
        assert result.performance_metrics['redis']['response_time_ms'] == 50.0
        assert result.performance_metrics['postgresql']['response_time_ms'] == 150.0
        assert result.performance_metrics['redis']['status'] == 'healthy'
        assert result.performance_metrics['postgresql']['status'] == 'healthy'

    @pytest.mark.asyncio
    async def test_final_health_check_success(self, service_manager):
        """测试最终健康检查（成功情况）"""
        result = DatabaseServiceResult(success=True)

        # 模拟服务运行状态
        mock_redis_info = Mock()
        mock_redis_info.status = RedisServiceStatus.RUNNING
        mock_redis_info.host = "localhost"
        mock_redis_info.port = 6379

        mock_postgresql_info = Mock()
        mock_postgresql_info.status = PostgreSQLServiceStatus.RUNNING
        mock_postgresql_info.host = "localhost"
        mock_postgresql_info.port = 5432

        result.redis_status = mock_redis_info
        result.postgresql_status = mock_postgresql_info

        # 模拟健康检查成功
        mock_health_result = Mock()
        mock_health_result.status.value = "healthy"
        mock_health_result.message = "Service is healthy"

        with patch.object(service_manager.health_checker, 'check_service_health') as mock_check:
            mock_check.return_value = mock_health_result

            health_status = await service_manager.get_service_status()

        assert len(result.errors) == 0
        assert 'redis' in service_manager._health_check_results
        assert 'postgresql' in service_manager._health_check_results

    @pytest.mark.asyncio
    async def test_final_health_check_failure(self, service_manager):
        """测试最终健康检查（失败情况）"""
        result = DatabaseServiceResult(success=True)

        # 模拟服务运行状态
        mock_redis_info = Mock()
        mock_redis_info.status = RedisServiceStatus.RUNNING
        mock_redis_info.host = "localhost"
        mock_redis_info.port = 6379

        result.redis_status = mock_redis_info

        # 模拟健康检查失败
        mock_health_result = Mock()
        mock_health_result.status.value = "unhealthy"
        mock_health_result.message = "Service is unhealthy"

        with patch.object(service_manager.health_checker, 'check_service_health') as mock_check:
            mock_check.return_value = mock_health_result

            health_status = await service_manager.get_service_status()

        assert len(result.errors) == 1
        assert "Redis健康检查失败" in result.errors[0]

    @pytest.mark.asyncio
    async def test_start_all_services_success(self, service_manager):
        """测试启动所有服务（成功情况）"""
        # 模拟所有服务启动成功
        with patch.object(service_manager, '_analyze_service_dependencies'):
            with patch.object(service_manager, '_prepare_ports'):
                with patch.object(service_manager, '_start_redis_service') as mock_redis:
                    with patch.object(service_manager, '_start_postgresql_service') as mock_postgresql:

                        # 设置模拟返回值
                        mock_redis_info = Mock()
                        mock_redis_info.status = RedisServiceStatus.RUNNING
                        mock_redis.return_value = mock_redis_info

                        mock_postgresql_info = Mock()
                        mock_postgresql_info.status = PostgreSQLServiceStatus.RUNNING
                        mock_postgresql.return_value = mock_postgresql_info

                        # 执行启动
                        result = await service_manager.start_all_services()

                        # 验证结果
                        assert result.success is True
                        assert result.overall_status == DatabaseServiceStatus.RUNNING
                        assert result.redis_status.status == RedisServiceStatus.RUNNING
                        assert result.postgresql_status.status == PostgreSQLServiceStatus.RUNNING
                        assert len(result.errors) == 0

    @pytest.mark.asyncio
    async def test_start_all_services_partial_failure(self, service_manager):
        """测试启动所有服务（部分失败）"""
        # 模拟PostgreSQL启动失败
        with patch.object(service_manager, '_analyze_service_dependencies'):
            with patch.object(service_manager, '_prepare_ports'):
                with patch.object(service_manager, '_start_redis_service') as mock_redis:
                    with patch.object(service_manager, '_start_postgresql_service') as mock_postgresql:

                        # Redis启动成功，PostgreSQL启动失败
                        mock_redis_info = Mock()
                        mock_redis_info.status = RedisServiceStatus.RUNNING
                        mock_redis.return_value = mock_redis_info

                        mock_postgresql_info = Mock()
                        mock_postgresql_info.status = PostgreSQLServiceStatus.ERROR
                        mock_postgresql.return_value = mock_postgresql_info

                        # 执行启动
                        result = await service_manager.start_all_services()

                        # 验证结果
                        assert result.success is False
                        assert result.overall_status == DatabaseServiceStatus.PARTIAL
                        assert result.redis_status.status == RedisServiceStatus.RUNNING
                        assert result.postgresql_status.status == PostgreSQLServiceStatus.ERROR
                        assert len(result.errors) > 0

    def test_get_service_status(self, service_manager):
        """测试获取服务状态"""
        with patch.object(service_manager.redis_manager, 'detect_redis_service') as mock_redis:
            with patch.object(service_manager.postgresql_manager, 'detect_postgresql_service') as mock_postgresql:

                mock_redis_info = Mock()
                mock_redis_info.to_dict.return_value = {"status": "running"}
                mock_redis.return_value = mock_redis_info

                mock_postgresql_info = Mock()
                mock_postgresql_info.to_dict.return_value = {"status": "running"}
                mock_postgresql.return_value = mock_postgresql_info

                status = asyncio.run(service_manager.get_service_status())

                assert 'redis' in status
                assert 'postgresql' in status
                assert 'health_checks' in status
                assert 'timestamp' in status

    def test_export_service_data(self, service_manager):
        """测试导出服务数据"""
        with patch.object(service_manager, 'get_service_status') as mock_status:
            mock_status.return_value = {"test": "data"}

            data = service_manager.export_service_data()

            assert 'config' in data
            assert 'service_status' in data
            assert 'port_data' in data
            assert 'timeout_data' in data
            assert 'timestamp' in data


class TestDatabaseServiceConfig:
    """数据库服务配置测试"""

    def test_default_config(self):
        """测试默认配置"""
        config = DatabaseServiceConfig()

        assert config.redis_enabled is True
        assert config.postgresql_enabled is True
        assert config.redis_port == 6379
        assert config.postgresql_port == 5432
        assert config.redis_host == "localhost"
        assert config.postgresql_host == "localhost"
        assert config.create_database is True
        assert config.run_migrations is True
        assert config.import_base_data is True
        assert config.performance_check is True

    def test_custom_config(self):
        """测试自定义配置"""
        config = DatabaseServiceConfig(
            redis_enabled=False,
            postgresql_port=5433,
            database_name="custom_db",
            performance_check=False
        )

        assert config.redis_enabled is False
        assert config.postgresql_enabled is True
        assert config.redis_port == 6379
        assert config.postgresql_port == 5433
        assert config.database_name == "custom_db"
        assert config.performance_check is False

    def test_config_to_dict(self):
        """测试配置转换为字典"""
        config = DatabaseServiceConfig(
            redis_port=6380,
            database_name="test_db"
        )

        config_dict = config.to_dict()

        assert isinstance(config_dict, dict)
        assert config_dict['redis_port'] == 6380
        assert config_dict['database_name'] == "test_db"
        assert config_dict['redis_enabled'] is True


class TestDatabaseServiceResult:
    """数据库服务结果测试"""

    def test_result_creation(self):
        """测试结果创建"""
        result = DatabaseServiceResult(success=True)

        assert result.success is True
        assert result.overall_status == DatabaseServiceStatus.NOT_STARTED
        assert result.start_time is not None
        assert result.end_time is None
        assert result.duration == 0.0
        assert isinstance(result.errors, list)
        assert isinstance(result.warnings, list)

    def test_overall_status_running(self):
        """测试整体状态 - 运行中"""
        result = DatabaseServiceResult(success=True)

        # 模拟Redis和PostgreSQL都运行
        mock_redis_info = Mock()
        mock_redis_info.status = RedisServiceStatus.RUNNING

        mock_postgresql_info = Mock()
        mock_postgresql_info.status = PostgreSQLServiceStatus.RUNNING

        result.redis_status = mock_redis_info
        result.postgresql_status = mock_postgresql_info

        assert result.overall_status == DatabaseServiceStatus.RUNNING

    def test_overall_status_partial(self):
        """测试整体状态 - 部分运行"""
        result = DatabaseServiceResult(success=True)

        # 模拟只有Redis运行
        mock_redis_info = Mock()
        mock_redis_info.status = RedisServiceStatus.RUNNING

        mock_postgresql_info = Mock()
        mock_postgresql_info.status = PostgreSQLServiceStatus.ERROR

        result.redis_status = mock_redis_info
        result.postgresql_status = mock_postgresql_info

        assert result.overall_status == DatabaseServiceStatus.PARTIAL

    def test_overall_status_stopped(self):
        """测试整体状态 - 停止"""
        result = DatabaseServiceResult(success=True)

        # 模拟两个服务都停止
        mock_redis_info = Mock()
        mock_redis_info.status = RedisServiceStatus.STOPPED

        mock_postgresql_info = Mock()
        mock_postgresql_info.status = PostgreSQLServiceStatus.STOPPED

        result.redis_status = mock_redis_info
        result.postgresql_status = mock_postgresql_info

        assert result.overall_status == DatabaseServiceStatus.STOPPED

    def test_result_to_dict(self):
        """测试结果转换为字典"""
        result = DatabaseServiceResult(success=True)

        mock_redis_info = Mock()
        mock_redis_info.to_dict.return_value = {"status": "running"}

        result.redis_status = mock_redis_info

        result_dict = result.to_dict()

        assert isinstance(result_dict, dict)
        assert result_dict['success'] is True
        assert 'overall_status' in result_dict
        assert 'redis_status' in result_dict
        assert 'postgresql_status' in result_dict
        assert 'start_time' in result_dict
        assert 'duration' in result_dict


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v"])