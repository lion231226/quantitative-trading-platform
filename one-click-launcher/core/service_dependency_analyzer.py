"""
服务依赖分析器

用于分析服务依赖关系、计算启动序列和管理服务依赖图的核心模块。
支持有向无环图(DAG)建模、拓扑排序和循环依赖检测。
"""

import asyncio
from typing import Dict, List, Set, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json
from pathlib import Path
import logging

from utils.logger import get_logger
from utils.progress_tracker import ProgressTracker

logger = get_logger(__name__)


class ServiceType(Enum):
    """服务类型枚举"""
    DATABASE = "database"
    BACKEND_API = "backend_api"
    FRONTEND = "frontend"
    CACHE = "cache"
    MESSAGE_QUEUE = "message_queue"
    EXTERNAL_API = "external_api"
    UTILITY = "utility"


class ServiceStatus(Enum):
    """服务状态枚举"""
    UNKNOWN = "unknown"
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    FAILED = "failed"
    DISABLED = "disabled"


@dataclass
class ServiceInfo:
    """服务信息"""
    name: str
    service_type: ServiceType
    host: str = "localhost"
    port: Optional[int] = None
    health_endpoint: Optional[str] = None
    startup_timeout: int = 60
    dependencies: List[str] = field(default_factory=list)
    start_order: Optional[int] = None
    status: ServiceStatus = ServiceStatus.UNKNOWN
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if isinstance(self.service_type, str):
            self.service_type = ServiceType(self.service_type)
        if isinstance(self.status, str):
            self.status = ServiceStatus(self.status)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'name': self.name,
            'service_type': self.service_type.value,
            'host': self.host,
            'port': self.port,
            'health_endpoint': self.health_endpoint,
            'startup_timeout': self.startup_timeout,
            'dependencies': self.dependencies,
            'start_order': self.start_order,
            'status': self.status.value,
            'metadata': self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ServiceInfo':
        """从字典创建服务信息"""
        return cls(**data)


@dataclass
class ValidationResult:
    """验证结果"""
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def add_error(self, error: str) -> None:
        """添加错误"""
        self.errors.append(error)
        self.is_valid = False

    def add_warning(self, warning: str) -> None:
        """添加警告"""
        self.warnings.append(warning)


@dataclass
class ServiceDependencyGraph:
    """服务依赖图"""
    services: Dict[str, ServiceInfo] = field(default_factory=dict)
    dependency_matrix: Dict[str, List[str]] = field(default_factory=dict)
    reverse_dependency_matrix: Dict[str, List[str]] = field(default_factory=dict)

    def add_service(self, service: ServiceInfo) -> None:
        """添加服务到依赖图"""
        self.services[service.name] = service
        if service.name not in self.dependency_matrix:
            self.dependency_matrix[service.name] = []
        if service.name not in self.reverse_dependency_matrix:
            self.reverse_dependency_matrix[service.name] = []

    def add_dependency(self, service_name: str, dependency_name: str) -> None:
        """添加依赖关系"""
        if service_name not in self.dependency_matrix:
            self.dependency_matrix[service_name] = []
        if dependency_name not in self.reverse_dependency_matrix:
            self.reverse_dependency_matrix[dependency_name] = []

        if dependency_name not in self.dependency_matrix[service_name]:
            self.dependency_matrix[service_name].append(dependency_name)
        if service_name not in self.reverse_dependency_matrix[dependency_name]:
            self.reverse_dependency_matrix[dependency_name].append(service_name)

        # 更新服务信息中的依赖列表
        if service_name in self.services:
            if dependency_name not in self.services[service_name].dependencies:
                self.services[service_name].dependencies.append(dependency_name)

    def get_dependencies(self, service_name: str) -> List[str]:
        """获取服务的依赖列表"""
        return self.dependency_matrix.get(service_name, [])

    def get_dependents(self, service_name: str) -> List[str]:
        """获取依赖于指定服务的服务列表"""
        return self.reverse_dependency_matrix.get(service_name, [])

    def get_all_services(self) -> List[str]:
        """获取所有服务名称"""
        return list(self.services.keys())

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'services': {name: service.to_dict() for name, service in self.services.items()},
            'dependency_matrix': self.dependency_matrix,
            'reverse_dependency_matrix': self.reverse_dependency_matrix
        }


class ServiceDependencyAnalyzer:
    """
    服务依赖分析器

    功能特性：
    - 服务依赖图管理
    - 启动序列计算（拓扑排序）
    - 循环依赖检测
    - 依赖关系验证
    - 进度跟踪集成
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化服务依赖分析器

        Args:
            config: 配置字典
        """
        self.config = config or {}
        self.logger = get_logger(self.__class__.__name__)
        self.progress_tracker = ProgressTracker(
            component_name="service_dependency_analysis",
            log_callback=self._log_callback
        )

        # 依赖图
        self.dependency_graph = ServiceDependencyGraph()

        # 配置参数
        self.max_startup_depth = self.config.get('max_startup_depth', 10)
        self.default_timeout = self.config.get('default_timeout', 60)

        self.logger.info("服务依赖分析器初始化完成")

    def _log_callback(self, message: str) -> None:
        """进度跟踪器日志回调"""
        self.logger.info(message)

    def add_service(self, service_info: ServiceInfo) -> None:
        """
        添加服务到依赖分析器

        Args:
            service_info: 服务信息
        """
        self.dependency_graph.add_service(service_info)

        # 添加已有的依赖关系
        for dependency in service_info.dependencies:
            self.dependency_graph.add_dependency(service_info.name, dependency)

        self.logger.debug(f"添加服务: {service_info.name} (类型: {service_info.service_type.value})")

    async def analyze_dependencies(self) -> ServiceDependencyGraph:
        """
        分析服务依赖关系

        Returns:
            服务依赖图
        """
        self.progress_tracker.start_installation()

        try:
            # 步骤1: 验证服务定义
            self.progress_tracker.start_step(0)
            validation_result = self._validate_service_definitions()
            if not validation_result.is_valid:
                raise ValueError(f"服务定义验证失败: {', '.join(validation_result.errors)}")
            self.progress_tracker.complete_step(0, success=True)

            # 步骤2: 检测循环依赖
            self.progress_tracker.start_step(1)
            circular_deps = await self._detect_circular_dependencies()
            if circular_deps:
                raise ValueError(f"检测到循环依赖: {', '.join(circular_deps)}")
            self.progress_tracker.complete_step(1, success=True)

            # 步骤3: 计算启动序列
            self.progress_tracker.start_step(2)
            startup_sequence = await self.calculate_startup_sequence()
            self.progress_tracker.complete_step(2, success=True)

            # 步骤4: 验证依赖完整性
            self.progress_tracker.start_step(3)
            integrity_result = await self._validate_dependency_integrity()
            if not integrity_result.is_valid:
                self.logger.warning(f"依赖完整性警告: {', '.join(integrity_result.warnings)}")
            self.progress_tracker.complete_step(3, success=True)

            self.progress_tracker.complete_installation(success=True)
            return self.dependency_graph

        except Exception as e:
            self.progress_tracker.complete_installation(success=False, error_message=str(e))
            raise

    async def calculate_startup_sequence(self) -> List[str]:
        """
        计算服务启动序列（拓扑排序）

        Returns:
            按启动顺序排列的服务名称列表
        """
        # 使用Kahn算法进行拓扑排序
        in_degree = {service: 0 for service in self.dependency_graph.get_all_services()}

        # 计算每个服务的入度
        for service in self.dependency_graph.get_all_services():
            for dependency in self.dependency_graph.get_dependencies(service):
                if dependency in in_degree:
                    in_degree[service] += 1

        # 找到所有入度为0的服务
        queue = [service for service, degree in in_degree.items() if degree == 0]
        startup_sequence = []

        while queue:
            # 按服务类型和优先级排序
            queue.sort(key=lambda x: self._get_service_priority(x))
            current = queue.pop(0)
            startup_sequence.append(current)

            # 更新依赖于此服务的服务的入度
            for dependent in self.dependency_graph.get_dependents(current):
                if dependent in in_degree:
                    in_degree[dependent] -= 1
                    if in_degree[dependent] == 0:
                        queue.append(dependent)

        # 检查是否所有服务都已处理（检测循环依赖）
        if len(startup_sequence) != len(self.dependency_graph.get_all_services()):
            remaining = set(self.dependency_graph.get_all_services()) - set(startup_sequence)
            raise ValueError(f"检测到循环依赖，涉及服务: {', '.join(remaining)}")

        # 更新服务的启动顺序
        for order, service_name in enumerate(startup_sequence):
            if service_name in self.dependency_graph.services:
                self.dependency_graph.services[service_name].start_order = order + 1

        self.logger.info(f"计算启动序列完成: {' → '.join(startup_sequence)}")
        return startup_sequence

    def _get_service_priority(self, service_name: str) -> int:
        """
        获取服务启动优先级

        Args:
            service_name: 服务名称

        Returns:
            优先级数值（越小优先级越高）
        """
        if service_name not in self.dependency_graph.services:
            return 999

        service = self.dependency_graph.services[service_name]

        # 定义服务类型优先级
        type_priorities = {
            ServiceType.DATABASE: 1,
            ServiceType.CACHE: 2,
            ServiceType.MESSAGE_QUEUE: 3,
            ServiceType.BACKEND_API: 4,
            ServiceType.EXTERNAL_API: 5,
            ServiceType.FRONTEND: 6,
            ServiceType.UTILITY: 7
        }

        return type_priorities.get(service.service_type, 999)

    def validate_dependencies(self) -> ValidationResult:
        """
        验证服务依赖关系

        Returns:
            验证结果
        """
        result = ValidationResult(is_valid=True)

        # 验证所有依赖的服务都存在
        for service_name in self.dependency_graph.get_all_services():
            dependencies = self.dependency_graph.get_dependencies(service_name)
            for dependency in dependencies:
                if dependency not in self.dependency_graph.services:
                    result.add_error(f"服务 '{service_name}' 依赖的服务 '{dependency}' 不存在")

        # 验证端口配置
        for service_name, service in self.dependency_graph.services.items():
            if service.service_type in [ServiceType.BACKEND_API, ServiceType.DATABASE, ServiceType.CACHE]:
                if not service.port:
                    result.add_warning(f"服务 '{service_name}' 应该配置端口号")

        # 验证健康检查端点
        for service_name, service in self.dependency_graph.services.items():
            if service.service_type in [ServiceType.BACKEND_API] and not service.health_endpoint:
                result.add_warning(f"Backend API服务 '{service_name}' 建议配置健康检查端点")

        return result

    async def _detect_circular_dependencies(self) -> List[str]:
        """
        检测循环依赖

        Returns:
            循环依赖的服务名称列表
        """
        visited = set()
        rec_stack = set()
        circular_deps = []

        def dfs(service: str, path: List[str]) -> bool:
            if service in rec_stack:
                # 找到循环依赖
                cycle_start = path.index(service)
                cycle = path[cycle_start:] + [service]
                circular_deps.extend(cycle)
                return True

            if service in visited:
                return False

            visited.add(service)
            rec_stack.add(service)
            path.append(service)

            # 访问所有依赖
            for dependency in self.dependency_graph.get_dependencies(service):
                if dfs(dependency, path.copy()):
                    return True

            rec_stack.remove(service)
            return False

        # 对所有服务执行DFS
        for service in self.dependency_graph.get_all_services():
            if service not in visited:
                dfs(service, [])

        return circular_deps

    def _validate_service_definitions(self) -> ValidationResult:
        """
        验证服务定义

        Returns:
            验证结果
        """
        result = ValidationResult(is_valid=True)

        for service_name, service in self.dependency_graph.services.items():
            # 验证服务名称
            if not service_name or not service_name.strip():
                result.add_error("服务名称不能为空")

            # 验证启动超时
            if service.startup_timeout <= 0:
                result.add_error(f"服务 '{service_name}' 的启动超时时间必须大于0")

            # 验证主机地址
            if not service.host:
                result.add_error(f"服务 '{service_name}' 的主机地址不能为空")

        return result

    async def _validate_dependency_integrity(self) -> ValidationResult:
        """
        验证依赖完整性

        Returns:
            验证结果
        """
        result = ValidationResult(is_valid=True)

        # 检查是否存在孤儿依赖（依赖关系中存在但服务定义中不存在）
        all_services = set(self.dependency_graph.get_all_services())

        for service_name in self.dependency_graph.dependency_matrix:
            for dependency in self.dependency_graph.dependency_matrix[service_name]:
                if dependency not in all_services:
                    result.add_warning(f"发现孤儿依赖: '{service_name}' → '{dependency}'")

        # 检查启动深度
        startup_sequence = await self.calculate_startup_sequence()
        if len(startup_sequence) > self.max_startup_depth:
            result.add_warning(f"启动序列深度 ({len(startup_sequence)}) 超过建议的最大深度 ({self.max_startup_depth})")

        return result

    def get_dependency_summary(self) -> Dict[str, Any]:
        """
        获取依赖关系摘要

        Returns:
            依赖关系摘要信息
        """
        services = self.dependency_graph.get_all_services()

        summary = {
            'total_services': len(services),
            'service_types': {},
            'dependency_count': 0,
            'max_dependencies': 0,
            'services_with_no_dependencies': 0,
            'services_with_most_dependencies': [],
        }

        for service_name in services:
            service = self.dependency_graph.services[service_name]
            dependencies_count = len(self.dependency_graph.get_dependencies(service_name))

            # 统计服务类型
            service_type = service.service_type.value
            summary['service_types'][service_type] = summary['service_types'].get(service_type, 0) + 1

            # 统计依赖数量
            if dependencies_count > 0:
                summary['dependency_count'] += dependencies_count
                if dependencies_count > summary['max_dependencies']:
                    summary['max_dependencies'] = dependencies_count
                    summary['services_with_most_dependencies'] = [service_name]
                elif dependencies_count == summary['max_dependencies']:
                    summary['services_with_most_dependencies'].append(service_name)
            else:
                summary['services_with_no_dependencies'] += 1

        return summary

    def save_dependency_graph(self, filepath: str) -> bool:
        """
        保存依赖图到文件

        Args:
            filepath: 文件路径

        Returns:
            是否成功保存
        """
        try:
            path = Path(filepath)
            path.parent.mkdir(parents=True, exist_ok=True)

            with open(path, 'w', encoding='utf-8') as f:
                json.dump(self.dependency_graph.to_dict(), f, indent=2, ensure_ascii=False)

            self.logger.info(f"依赖图已保存到: {filepath}")
            return True
        except Exception as e:
            self.logger.error(f"保存依赖图失败: {e}")
            return False

    def load_dependency_graph(self, filepath: str) -> bool:
        """
        从文件加载依赖图

        Args:
            filepath: 文件路径

        Returns:
            是否成功加载
        """
        try:
            path = Path(filepath)
            if not path.exists():
                return False

            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 重建依赖图
            self.dependency_graph = ServiceDependencyGraph()

            # 加载服务信息
            for service_name, service_data in data.get('services', {}).items():
                service = ServiceInfo.from_dict(service_data)
                self.dependency_graph.add_service(service)

            # 加载依赖关系
            dependency_matrix = data.get('dependency_matrix', {})
            for service_name, dependencies in dependency_matrix.items():
                for dependency in dependencies:
                    self.dependency_graph.add_dependency(service_name, dependency)

            self.logger.info(f"依赖图已从文件加载: {filepath}")
            return True
        except Exception as e:
            self.logger.error(f"加载依赖图失败: {e}")
            return False

    def get_progress(self) -> Any:
        """获取当前分析进度"""
        return self.progress_tracker.get_progress()