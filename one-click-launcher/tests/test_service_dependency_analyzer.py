"""
服务依赖分析器测试

测试服务依赖图管理、启动序列计算、循环依赖检测等功能。
"""

import pytest
import asyncio
from unittest.mock import Mock, patch
import tempfile
import json
from pathlib import Path
import sys

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from core.service_dependency_analyzer import (
    ServiceDependencyAnalyzer, ServiceInfo, ServiceType, ServiceStatus,
    ServiceDependencyGraph, ValidationResult
)


class TestServiceInfo:
    """测试ServiceInfo类"""

    def test_service_info_creation(self):
        """测试服务信息创建"""
        service = ServiceInfo(
            name="test-service",
            service_type=ServiceType.BACKEND_API,
            host="localhost",
            port=8000,
            dependencies=["redis"]
        )

        assert service.name == "test-service"
        assert service.service_type == ServiceType.BACKEND_API
        assert service.host == "localhost"
        assert service.port == 8000
        assert service.dependencies == ["redis"]
        assert service.status == ServiceStatus.UNKNOWN

    def test_service_info_to_dict(self):
        """测试服务信息转换为字典"""
        service = ServiceInfo(
            name="test-service",
            service_type=ServiceType.BACKEND_API,
            port=8000
        )

        data = service.to_dict()
        assert data['name'] == "test-service"
        assert data['service_type'] == "backend_api"
        assert data['port'] == 8000

    def test_service_info_from_dict(self):
        """测试从字典创建服务信息"""
        data = {
            'name': 'test-service',
            'service_type': 'backend_api',
            'host': 'localhost',
            'port': 8000,
            'dependencies': ['redis'],
            'startup_timeout': 60
        }

        service = ServiceInfo.from_dict(data)
        assert service.name == "test-service"
        assert service.service_type == ServiceType.BACKEND_API
        assert service.host == "localhost"
        assert service.port == 8000
        assert service.dependencies == ["redis"]
        assert service.startup_timeout == 60


class TestServiceDependencyGraph:
    """测试ServiceDependencyGraph类"""

    def test_add_service(self):
        """测试添加服务"""
        graph = ServiceDependencyGraph()
        service = ServiceInfo(name="test", service_type=ServiceType.BACKEND_API)

        graph.add_service(service)
        assert "test" in graph.services
        assert graph.services["test"] == service
        assert "test" in graph.dependency_matrix
        assert "test" in graph.reverse_dependency_matrix

    def test_add_dependency(self):
        """测试添加依赖关系"""
        graph = ServiceDependencyGraph()
        service1 = ServiceInfo(name="service1", service_type=ServiceType.BACKEND_API)
        service2 = ServiceInfo(name="service2", service_type=ServiceType.DATABASE)

        graph.add_service(service1)
        graph.add_service(service2)
        graph.add_dependency("service1", "service2")

        assert "service2" in graph.get_dependencies("service1")
        assert "service1" in graph.get_dependents("service2")

    def test_get_all_services(self):
        """测试获取所有服务"""
        graph = ServiceDependencyGraph()
        service1 = ServiceInfo(name="service1", service_type=ServiceType.BACKEND_API)
        service2 = ServiceInfo(name="service2", service_type=ServiceType.DATABASE)

        graph.add_service(service1)
        graph.add_service(service2)

        services = graph.get_all_services()
        assert len(services) == 2
        assert "service1" in services
        assert "service2" in services

    def test_to_dict(self):
        """测试转换为字典"""
        graph = ServiceDependencyGraph()
        service = ServiceInfo(name="test", service_type=ServiceType.BACKEND_API)
        graph.add_service(service)

        data = graph.to_dict()
        assert 'services' in data
        assert 'dependency_matrix' in data
        assert 'reverse_dependency_matrix' in data
        assert 'test' in data['services']


class TestServiceDependencyAnalyzer:
    """测试ServiceDependencyAnalyzer类"""

    @pytest.fixture
    def analyzer(self):
        """创建分析器实例"""
        return ServiceDependencyAnalyzer()

    @pytest.fixture
    def sample_services(self):
        """创建示例服务"""
        return [
            ServiceInfo(
                name="redis",
                service_type=ServiceType.CACHE,
                port=6379,
                dependencies=[]
            ),
            ServiceInfo(
                name="backend",
                service_type=ServiceType.BACKEND_API,
                port=8000,
                dependencies=["redis"]
            ),
            ServiceInfo(
                name="frontend",
                service_type=ServiceType.FRONTEND,
                port=3000,
                dependencies=["backend"]
            )
        ]

    def test_analyzer_initialization(self, analyzer):
        """测试分析器初始化"""
        assert analyzer.dependency_graph is not None
        assert analyzer.progress_tracker is not None
        assert analyzer.config == {}

    def test_add_service(self, analyzer, sample_services):
        """测试添加服务"""
        for service in sample_services:
            analyzer.add_service(service)

        assert len(analyzer.dependency_graph.get_all_services()) == 3
        assert "redis" in analyzer.dependency_graph.services
        assert "backend" in analyzer.dependency_graph.services
        assert "frontend" in analyzer.dependency_graph.services

    @pytest.mark.asyncio
    async def test_analyze_dependencies(self, analyzer, sample_services):
        """测试依赖分析"""
        # 添加服务
        for service in sample_services:
            analyzer.add_service(service)

        # 执行分析
        graph = await analyzer.analyze_dependencies()

        assert graph is not None
        assert len(graph.get_all_services()) == 3

    @pytest.mark.asyncio
    async def test_calculate_startup_sequence(self, analyzer, sample_services):
        """测试启动序列计算"""
        # 添加服务
        for service in sample_services:
            analyzer.add_service(service)

        # 计算启动序列
        sequence = await analyzer.calculate_startup_sequence()

        assert len(sequence) == 3
        assert sequence[0] == "redis"  # 无依赖
        assert sequence[1] == "backend"  # 依赖redis
        assert sequence[2] == "frontend"  # 依赖backend

    @pytest.mark.asyncio
    async def test_circular_dependency_detection(self, analyzer):
        """测试循环依赖检测"""
        # 创建循环依赖的服务
        service1 = ServiceInfo(name="service1", service_type=ServiceType.BACKEND_API, dependencies=["service2"])
        service2 = ServiceInfo(name="service2", service_type=ServiceType.DATABASE, dependencies=["service1"])

        analyzer.add_service(service1)
        analyzer.add_service(service2)

        # 检测循环依赖应该抛出异常
        with pytest.raises(ValueError, match="检测到循环依赖"):
            await analyzer.calculate_startup_sequence()

    def test_validate_dependencies(self, analyzer, sample_services):
        """测试依赖验证"""
        # 添加服务
        for service in sample_services:
            analyzer.add_service(service)

        # 验证依赖
        result = analyzer.validate_dependencies()

        assert result.is_valid  # 应该是有效的

        # 添加不存在的依赖
        service = ServiceInfo(name="invalid", service_type=ServiceType.BACKEND_API, dependencies=["nonexistent"])
        analyzer.add_service(service)

        result = analyzer.validate_dependencies()
        assert not result.is_valid  # 应该是无效的
        assert any("不存在" in error for error in result.errors)

    def test_get_service_priority(self, analyzer):
        """测试服务优先级获取"""
        # 需要先添加服务到依赖图中，这样才能获取服务类型
        db_service = ServiceInfo(name="db_service", service_type=ServiceType.DATABASE)
        api_service = ServiceInfo(name="api_service", service_type=ServiceType.BACKEND_API)
        frontend_service = ServiceInfo(name="frontend_service", service_type=ServiceType.FRONTEND)

        analyzer.add_service(db_service)
        analyzer.add_service(api_service)
        analyzer.add_service(frontend_service)

        # 测试不同服务类型的优先级
        db_priority = analyzer._get_service_priority("db_service")
        api_priority = analyzer._get_service_priority("api_service")
        frontend_priority = analyzer._get_service_priority("frontend_service")

        # 数据库应该有最高优先级（数值最小）
        assert db_priority < api_priority
        assert api_priority < frontend_priority

    def test_get_dependency_summary(self, analyzer, sample_services):
        """测试依赖摘要"""
        # 添加服务
        for service in sample_services:
            analyzer.add_service(service)

        summary = analyzer.get_dependency_summary()

        assert summary['total_services'] == 3
        assert summary['service_types']['cache'] == 1
        assert summary['service_types']['backend_api'] == 1
        assert summary['service_types']['frontend'] == 1
        assert summary['services_with_no_dependencies'] == 1  # redis
        assert summary['dependency_count'] == 2  # backend依赖redis, frontend依赖backend

    def test_save_and_load_dependency_graph(self, analyzer, sample_services):
        """测试保存和加载依赖图"""
        # 添加服务
        for service in sample_services:
            analyzer.add_service(service)

        # 保存到临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name

        try:
            # 保存
            success = analyzer.save_dependency_graph(temp_path)
            assert success
            assert Path(temp_path).exists()

            # 创建新的分析器并加载
            new_analyzer = ServiceDependencyAnalyzer()
            success = new_analyzer.load_dependency_graph(temp_path)
            assert success

            # 验证加载的数据
            assert len(new_analyzer.dependency_graph.get_all_services()) == 3
            assert "redis" in new_analyzer.dependency_graph.services

        finally:
            # 清理临时文件
            Path(temp_path).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_complex_dependency_graph(self, analyzer):
        """测试复杂依赖图"""
        # 创建复杂的依赖关系
        services = [
            ServiceInfo(name="db", service_type=ServiceType.DATABASE, dependencies=[]),
            ServiceInfo(name="cache", service_type=ServiceType.CACHE, dependencies=[]),
            ServiceInfo(name="queue", service_type=ServiceType.MESSAGE_QUEUE, dependencies=[]),
            ServiceInfo(name="auth", service_type=ServiceType.BACKEND_API, dependencies=["db", "cache"]),
            ServiceInfo(name="api", service_type=ServiceType.BACKEND_API, dependencies=["db", "auth"]),
            ServiceInfo(name="worker", service_type=ServiceType.UTILITY, dependencies=["db", "queue"]),
            ServiceInfo(name="frontend", service_type=ServiceType.FRONTEND, dependencies=["api", "auth"])
        ]

        for service in services:
            analyzer.add_service(service)

        # 验证依赖关系
        result = analyzer.validate_dependencies()
        assert result.is_valid

        # 计算启动序列
        sequence = await analyzer.calculate_startup_sequence()

        assert len(sequence) == 7
        # 基础服务应该先启动
        assert sequence[0] in ["db", "cache", "queue"]
        # frontend或worker应该最后启动（它们都依赖前序服务）
        assert sequence[-1] in ["frontend", "worker"]

    def test_service_with_multiple_dependencies(self, analyzer):
        """测试多依赖服务"""
        services = [
            ServiceInfo(name="service1", service_type=ServiceType.DATABASE, dependencies=[]),
            ServiceInfo(name="service2", service_type=ServiceType.CACHE, dependencies=[]),
            ServiceInfo(name="service3", service_type=ServiceType.BACKEND_API, dependencies=["service1", "service2"])
        ]

        for service in services:
            analyzer.add_service(service)

        sequence = asyncio.run(analyzer.calculate_startup_sequence())

        assert len(sequence) == 3
        assert sequence[2] == "service3"  # 多依赖服务应该最后启动
        assert set(sequence[:2]) == {"service1", "service2"}  # 前两个应该是基础服务

    def test_empty_dependency_graph(self, analyzer):
        """测试空依赖图"""
        sequence = asyncio.run(analyzer.calculate_startup_sequence())
        assert sequence == []

    def test_single_service_no_dependencies(self, analyzer):
        """测试单个无依赖服务"""
        service = ServiceInfo(name="single", service_type=ServiceType.UTILITY, dependencies=[])
        analyzer.add_service(service)

        sequence = asyncio.run(analyzer.calculate_startup_sequence())
        assert sequence == ["single"]

        # 验证启动顺序被设置
        assert analyzer.dependency_graph.services["single"].start_order == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])