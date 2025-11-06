"""
简化的数据库服务测试

测试数据库服务启动器的基本功能
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

    def test_config_to_dict(self):
        """测试配置转换为字典"""
        config = DatabaseServiceConfig(redis_port=6380, database_name="test_db")
        config_dict = config.to_dict()

        assert isinstance(config_dict, dict)
        assert config_dict['redis_port'] == 6380
        assert config_dict['database_name'] == "test_db"


class TestDatabaseServiceResult:
    """数据库服务结果测试"""

    def test_result_creation(self):
        """测试结果创建"""
        result = DatabaseServiceResult(success=True)

        assert result.success is True
        assert result.overall_status == DatabaseServiceStatus.NOT_STARTED
        assert result.start_time is not None
        assert isinstance(result.errors, list)
        assert isinstance(result.warnings, list)

    def test_result_to_dict(self):
        """测试结果转换为字典"""
        result = DatabaseServiceResult(success=True)
        result_dict = result.to_dict()

        assert isinstance(result_dict, dict)
        assert result_dict['success'] is True
        assert 'overall_status' in result_dict


class TestDatabaseServiceManager:
    """数据库服务管理器测试"""

    @pytest.fixture
    def config(self):
        """测试配置"""
        return DatabaseServiceConfig(
            redis_enabled=True,
            postgresql_enabled=True,
            redis_port=6379,
            postgresql_port=5432
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

    @pytest.mark.asyncio
    async def test_analyze_service_dependencies(self, service_manager):
        """测试服务依赖分析"""
        await service_manager._analyze_service_dependencies()

        dependency_graph = service_manager.dependency_analyzer.dependency_graph
        assert "redis" in dependency_graph.services
        assert "postgresql" in dependency_graph.services

    @pytest.mark.asyncio
    async def test_prepare_ports_available(self, service_manager):
        """测试端口准备（端口可用情况）"""
        with patch.object(service_manager.port_manager, 'check_port_availability') as mock_check:
            mock_check.return_value = True
            await service_manager._prepare_ports()
            assert service_manager.config.redis_port == 6379
            assert service_manager.config.postgresql_port == 5432

    @pytest.mark.asyncio
    async def test_start_redis_service_success(self, service_manager):
        """测试Redis服务启动成功"""
        with patch.object(service_manager.redis_manager, 'detect_redis_service') as mock_detect:
            with patch.object(service_manager.redis_manager, 'start_redis_service') as mock_start:
                mock_detect.return_value = Mock(status="running")
                mock_start.return_value = (True, "Redis started successfully")

                result = await service_manager._start_redis_service()
                assert result.status == "running"

    @pytest.mark.asyncio
    async def test_start_postgresql_service_success(self, service_manager):
        """测试PostgreSQL服务启动成功"""
        with patch.object(service_manager.postgresql_manager, 'detect_postgresql_service') as mock_detect:
            with patch.object(service_manager.postgresql_manager, 'start_postgresql_service') as mock_start:
                mock_detect.return_value = Mock(status="running")
                mock_start.return_value = (True, "PostgreSQL started successfully")

                result = await service_manager._start_postgresql_service()
                assert result.status == "running"

    @pytest.mark.asyncio
    async def test_initialize_database(self, service_manager):
        """测试数据库初始化"""
        result = DatabaseServiceResult(success=True)
        mock_postgresql_info = Mock(status="running")
        result.postgresql_status = mock_postgresql_info

        with patch('asyncio.sleep', return_value=None):
            await service_manager._initialize_database(result)

        assert len(result.errors) == 0

    @pytest.mark.asyncio
    async def test_run_migrations_with_files(self, service_manager):
        """测试运行迁移（有迁移文件）"""
        result = DatabaseServiceResult(success=True)

        migration_dir = Path("one-click-launcher/migrations")
        migration_dir.mkdir(parents=True, exist_ok=True)

        try:
            (migration_dir / "001_test.sql").write_text("-- Test migration")
            (migration_dir / "002_test.sql").write_text("-- Test migration 2")

            with patch('asyncio.sleep', return_value=None):
                await service_manager._run_migrations(result)

            assert result.migration_results['executed_migrations'] == 2
            assert len(result.errors) == 0

        finally:
            for f in migration_dir.glob("*.sql"):
                f.unlink()

    @pytest.mark.asyncio
    async def test_verify_performance(self, service_manager):
        """测试性能验证"""
        result = DatabaseServiceResult(success=True)

        mock_redis_info = Mock(status="running")
        mock_postgresql_info = Mock(status="running")
        result.redis_status = mock_redis_info
        result.postgresql_status = mock_postgresql_info

        with patch('time.time', side_effect=[0, 0.05, 0, 0.15]):
            await service_manager._verify_performance(result)

        assert 'redis' in result.performance_metrics
        assert 'postgresql' in result.performance_metrics

    def test_export_service_data(self, service_manager):
        """测试导出服务数据"""
        with patch.object(service_manager, 'get_service_status') as mock_status:
            mock_status.return_value = {"test": "data"}
            data = service_manager.export_service_data()

            assert 'config' in data
            assert 'service_status' in data
            assert 'timestamp' in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])