"""
服务编排器

整合依赖分析、健康检查、端口管理、超时管理和配置管理的核心编排器。
提供完整的服务启动流程控制和监控功能。
"""

import asyncio
import sys
import os
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from core.service_dependency_analyzer import ServiceDependencyAnalyzer, ServiceInfo
from core.health_checker import HealthChecker, HealthCheckConfig
from core.port_manager import PortManager
from core.timeout_manager import TimeoutManager, TimeoutConfig
from core.service_configurator import ServiceConfigurator, Environment, ConfigFormat
from core.dependency_visualizer import DependencyVisualizer, VisualizationConfig
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class OrchestrationConfig:
    """编排配置"""
    config_file: str = "config/service-config.yaml"
    environment: str = "development"
    enable_visualization: bool = True
    output_directory: str = "output"
    parallel_startup: bool = False
    max_parallel_services: int = 3
    health_check_interval: float = 5.0
    startup_timeout_buffer: float = 1.2  # 启动超时缓冲系数


@dataclass
class ServiceStartupResult:
    """服务启动结果"""
    service_name: str
    success: bool
    start_time: datetime
    end_time: datetime
    duration: float
    error_message: Optional[str] = None
    allocated_port: Optional[int] = None
    retry_count: int = 0
    health_check_passed: bool = False


class ServiceOrchestrator:
    """
    服务编排器

    功能特性：
    - 服务依赖分析和启动序列计算
    - 端口冲突检测和自动分配
    - 健康检查和监控
    - 超时管理和重试机制
    - 配置管理和参数注入
    - 依赖可视化和报告生成
    """

    def __init__(self, config: Optional[OrchestrationConfig] = None):
        """
        初始化服务编排器

        Args:
            config: 编排配置
        """
        self.config = config or OrchestrationConfig()
        self.logger = get_logger(self.__class__.__name__)

        # 初始化各个组件
        self._initialize_components()

        # 服务状态跟踪
        self.service_status: Dict[str, ServiceStartupResult] = {}
        self.startup_sequence: List[str] = []

        # 创建输出目录
        Path(self.config.output_directory).mkdir(parents=True, exist_ok=True)

        self.logger.info("服务编排器初始化完成")

    def _initialize_components(self) -> None:
        """初始化各个组件"""
        # 配置管理器
        config_path = Path(self.config.output_directory).parent / self.config.config_file
        self.configurator = ServiceConfigurator(
            str(config_path),
            environment=Environment(self.config.environment)
        )

        # 依赖分析器
        self.dependency_analyzer = ServiceDependencyAnalyzer()

        # 端口管理器
        persistence_file = Path(self.config.output_directory) / "port_allocation.json"
        self.port_manager = PortManager(persistence_file=str(persistence_file))

        # 健康检查器
        health_config = HealthCheckConfig(
            timeout=30,
            max_retries=3,
            retry_delay=1.0
        )
        self.health_checker = HealthChecker(health_config)

        # 超时管理器
        timeout_config = TimeoutConfig(
            default_timeout=60,
            max_timeout=300,
            escalation_factor=1.5,
            max_retries=3
        )
        self.timeout_manager = TimeoutManager(timeout_config)

        # 依赖可视化器
        viz_config = VisualizationConfig(
            show_service_types=True,
            show_ports=True,
            show_startup_order=True,
            group_by_type=True
        )
        self.visualizer = DependencyVisualizer(viz_config)

    async def start_services(self, service_names: Optional[List[str]] = None) -> Dict[str, ServiceStartupResult]:
        """
        启动服务

        Args:
            service_names: 要启动的服务名称列表，None表示启动所有服务

        Returns:
            服务启动结果字典
        """
        try:
            self.logger.info("开始服务启动流程")

            # 1. 加载配置
            self.logger.info("步骤1: 加载服务配置")
            await self._load_configuration()

            # 2. 分析依赖关系
            self.logger.info("步骤2: 分析服务依赖关系")
            await self._analyze_dependencies()

            # 3. 分配端口
            self.logger.info("步骤3: 分配服务端口")
            await self._allocate_ports()

            # 4. 计算启动序列
            self.logger.info("步骤4: 计算启动序列")
            await self._calculate_startup_sequence()

            # 5. 启动服务
            self.logger.info("步骤5: 启动服务")
            if self.config.parallel_startup:
                results = await self._start_services_parallel(service_names)
            else:
                results = await self._start_services_sequential(service_names)

            # 6. 生成报告
            self.logger.info("步骤6: 生成启动报告")
            await self._generate_reports()

            self.logger.info(f"服务启动流程完成，成功: {sum(1 for r in results.values() if r.success)}/{len(results)}")
            return results

        except Exception as e:
            self.logger.error(f"服务启动流程失败: {e}")
            raise

    async def _load_configuration(self) -> None:
        """加载配置"""
        try:
            service_config = self.configurator.load_configuration()
            self.logger.info(f"成功加载配置，环境: {self.config.environment}")
        except Exception as e:
            self.logger.error(f"加载配置失败: {e}")
            raise

    async def _analyze_dependencies(self) -> None:
        """分析依赖关系"""
        # 添加所有服务到依赖分析器
        service_configs = self.configurator.get_all_service_configs()
        for service_config in service_configs.values():
            service_info = service_config.to_service_info()
            self.dependency_analyzer.add_service(service_info)

        # 分析依赖关系
        dependency_graph = await self.dependency_analyzer.analyze_dependencies()
        self.logger.info(f"依赖分析完成，服务数量: {len(dependency_graph.get_all_services())}")

    async def _allocate_ports(self) -> None:
        """分配端口"""
        service_configs = self.configurator.get_all_service_configs()

        for service_name, service_config in service_configs.items():
            if service_config.enabled and service_config.port:
                try:
                    # 检查端口是否可用
                    if not await self.port_manager.check_port_availability(service_config.port):
                        self.logger.warning(f"端口 {service_config.port} 被占用，为服务 {service_name} 分配新端口")
                        new_port = await self.port_manager.allocate_port(
                            preferred_port=service_config.port,
                            service_name=service_name
                        )
                        service_config.port = new_port
                        self.logger.info(f"为服务 {service_name} 分配端口: {new_port}")
                    else:
                        # 预留端口
                        self.port_manager.reserve_port(service_config.port, service_name)
                        self.logger.debug(f"预留端口 {service_config.port} 给服务 {service_name}")

                except Exception as e:
                    self.logger.error(f"为服务 {service_name} 分配端口失败: {e}")
                    raise

    async def _calculate_startup_sequence(self) -> None:
        """计算启动序列"""
        self.startup_sequence = await self.dependency_analyzer.calculate_startup_sequence()
        self.logger.info(f"启动序列: {' → '.join(self.startup_sequence)}")

    async def _start_services_sequential(self, service_names: Optional[List[str]] = None) -> Dict[str, ServiceStartupResult]:
        """顺序启动服务"""
        results = {}
        services_to_start = service_names or self.startup_sequence

        for service_name in services_to_start:
            if service_name not in self.configurator.get_all_service_configs():
                self.logger.warning(f"跳过未配置的服务: {service_name}")
                continue

            result = await self._start_single_service(service_name)
            results[service_name] = result

            if not result.success:
                self.logger.error(f"服务 {service_name} 启动失败，停止后续服务启动")
                break

        return results

    async def _start_services_parallel(self, service_names: Optional[List[str]] = None) -> Dict[str, ServiceStartupResult]:
        """并行启动服务"""
        results = {}
        services_to_start = service_names or self.startup_sequence

        # 按依赖层级分组
        dependency_groups = self._group_services_by_dependencies(services_to_start)

        for group in dependency_groups:
            # 并行启动同一层级的服务
            tasks = []
            for service_name in group:
                if service_name in self.configurator.get_all_service_configs():
                    task = asyncio.create_task(self._start_single_service(service_name))
                    tasks.append((service_name, task))

            # 等待当前层级所有服务启动完成
            for service_name, task in tasks:
                try:
                    result = await task
                    results[service_name] = result

                    if not result.success:
                        self.logger.error(f"服务 {service_name} 启动失败")

                except Exception as e:
                    self.logger.error(f"启动服务 {service_name} 时发生异常: {e}")
                    results[service_name] = ServiceStartupResult(
                        service_name=service_name,
                        success=False,
                        start_time=datetime.now(),
                        end_time=datetime.now(),
                        duration=0.0,
                        error_message=str(e)
                    )

        return results

    async def _start_single_service(self, service_name: str) -> ServiceStartupResult:
        """启动单个服务"""
        start_time = datetime.now()
        service_config = self.configurator.get_service_config(service_name)

        if not service_config or not service_config.enabled:
            return ServiceStartupResult(
                service_name=service_name,
                success=False,
                start_time=start_time,
                end_time=datetime.now(),
                duration=0.0,
                error_message="服务未启用或配置不存在"
            )

        self.logger.info(f"启动服务: {service_name}")

        try:
            # 1. 获取启动参数
            startup_params = self.configurator.get_startup_parameters(service_name)

            # 2. 构建启动函数
            async def startup_func():
                return await self._execute_service_startup(service_name, startup_params)

            # 3. 监控启动过程
            service_info = service_config.to_service_info()
            startup_result = await self.timeout_manager.monitor_startup(service_info, startup_func)

            # 4. 健康检查
            health_check_passed = False
            if startup_result.success:
                try:
                    health_result = await self.health_checker.check_service_health_with_retry(service_info)
                    health_check_passed = health_result.status.value == "healthy"
                    if not health_check_passed:
                        self.logger.warning(f"服务 {service_name} 启动成功但健康检查失败: {health_result.message}")
                except Exception as e:
                    self.logger.warning(f"服务 {service_name} 健康检查异常: {e}")

            # 5. 记录结果
            result = ServiceStartupResult(
                service_name=service_name,
                success=startup_result.success and health_check_passed,
                start_time=start_time,
                end_time=startup_result.end_time,
                duration=startup_result.duration,
                error_message=startup_result.error_message,
                allocated_port=service_config.port,
                retry_count=startup_result.retries,
                health_check_passed=health_check_passed
            )

            self.service_status[service_name] = result

            if result.success:
                self.logger.info(f"服务 {service_name} 启动成功 (耗时: {result.duration:.2f}s)")
            else:
                self.logger.error(f"服务 {service_name} 启动失败: {result.error_message}")

            return result

        except Exception as e:
            end_time = datetime.now()
            self.logger.error(f"启动服务 {service_name} 时发生异常: {e}")

            return ServiceStartupResult(
                service_name=service_name,
                success=False,
                start_time=start_time,
                end_time=end_time,
                duration=(end_time - start_time).total_seconds(),
                error_message=str(e)
            )

    async def _execute_service_startup(self, service_name: str, params) -> None:
        """执行服务启动"""
        # 这里应该实现实际的服务启动逻辑
        # 为了演示，我们只是模拟启动过程

        self.logger.debug(f"执行服务启动命令: {params.command} {' '.join(params.args)}")

        # 模拟启动时间
        await asyncio.sleep(2)

        # 在实际实现中，这里会：
        # 1. 启动子进程执行命令
        # 2. 监控进程状态
        # 3. 处理进程输出
        # 4. 等待进程就绪

    def _group_services_by_dependencies(self, service_names: List[str]) -> List[List[str]]:
        """按依赖关系对服务分组"""
        groups = []
        remaining_services = set(service_names)
        processed_services = set()

        while remaining_services:
            current_group = []

            for service_name in remaining_services:
                # 检查所有依赖是否已处理
                service_config = self.configurator.get_service_config(service_name)
                if service_config:
                    dependencies = set(service_config.dependencies)
                    if dependencies.issubset(processed_services):
                        current_group.append(service_name)

            if not current_group:
                # 如果没有可以启动的服务，可能存在循环依赖
                self.logger.warning("检测到可能的循环依赖，强制启动剩余服务")
                current_group = list(remaining_services)

            groups.append(current_group)
            processed_services.update(current_group)
            remaining_services -= set(current_group)

        return groups

    async def _generate_reports(self) -> None:
        """生成启动报告"""
        if not self.config.enable_visualization:
            return

        try:
            output_dir = Path(self.config.output_directory)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # 生成依赖图
            dot_file = output_dir / f"dependency_graph_{timestamp}.dot"
            self.visualizer.generate_dot_graph(self.dependency_analyzer.dependency_graph, str(dot_file))

            # 生成HTML报告
            html_file = output_dir / f"startup_report_{timestamp}.html"
            self.visualizer.generate_html_report(
                self.dependency_analyzer.dependency_graph,
                self.startup_sequence,
                str(html_file)
            )

            # 生成文本报告
            text_file = output_dir / f"startup_report_{timestamp}.txt"
            self.visualizer.generate_text_report(
                self.dependency_analyzer.dependency_graph,
                self.startup_sequence,
                str(text_file)
            )

            # 导出JSON数据
            json_file = output_dir / f"startup_data_{timestamp}.json"
            self.visualizer.export_json_data(
                self.dependency_analyzer.dependency_graph,
                self.startup_sequence,
                str(json_file)
            )

            self.logger.info(f"启动报告已生成到: {output_dir}")

        except Exception as e:
            self.logger.error(f"生成启动报告失败: {e}")

    def get_startup_summary(self) -> Dict[str, Any]:
        """获取启动摘要"""
        total_services = len(self.service_status)
        successful_services = sum(1 for result in self.service_status.values() if result.success)
        failed_services = total_services - successful_services

        total_duration = 0.0
        if self.service_status:
            total_duration = max(result.end_time for result in self.service_status.values()).timestamp() - \
                            min(result.start_time for result in self.service_status.values()).timestamp()

        return {
            'total_services': total_services,
            'successful_services': successful_services,
            'failed_services': failed_services,
            'success_rate': (successful_services / total_services * 100) if total_services > 0 else 0,
            'total_duration': total_duration,
            'startup_sequence': self.startup_sequence,
            'service_details': {
                name: {
                    'success': result.success,
                    'duration': result.duration,
                    'allocated_port': result.allocated_port,
                    'retry_count': result.retry_count,
                    'health_check_passed': result.health_check_passed,
                    'error_message': result.error_message
                }
                for name, result in self.service_status.items()
            }
        }

    async def stop_services(self, service_names: Optional[List[str]] = None) -> bool:
        """停止服务"""
        # 这里应该实现服务停止逻辑
        self.logger.info("服务停止功能待实现")
        return True

    async def restart_services(self, service_names: Optional[List[str]] = None) -> Dict[str, ServiceStartupResult]:
        """重启服务"""
        await self.stop_services(service_names)
        return await self.start_services(service_names)

    def get_service_status(self, service_name: str) -> Optional[ServiceStartupResult]:
        """获取服务状态"""
        return self.service_status.get(service_name)

    def get_all_service_status(self) -> Dict[str, ServiceStartupResult]:
        """获取所有服务状态"""
        return self.service_status.copy()


# 便利函数
async def start_all_services(config: Optional[OrchestrationConfig] = None) -> Dict[str, ServiceStartupResult]:
    """
    启动所有服务的便利函数

    Args:
        config: 编排配置

    Returns:
        服务启动结果字典
    """
    orchestrator = ServiceOrchestrator(config)
    return await orchestrator.start_services()


async def start_specific_services(service_names: List[str],
                                config: Optional[OrchestrationConfig] = None) -> Dict[str, ServiceStartupResult]:
    """
    启动指定服务的便利函数

    Args:
        service_names: 服务名称列表
        config: 编排配置

    Returns:
        服务启动结果字典
    """
    orchestrator = ServiceOrchestrator(config)
    return await orchestrator.start_services(service_names)


if __name__ == "__main__":
    # 示例用法
    async def main():
        config = OrchestrationConfig(
            environment="development",
            enable_visualization=True,
            parallel_startup=False
        )

        results = await start_all_services(config)

        print("\n=== 服务启动结果 ===")
        for service_name, result in results.items():
            status = "✅ 成功" if result.success else "❌ 失败"
            print(f"{service_name}: {status} (耗时: {result.duration:.2f}s)")
            if result.error_message:
                print(f"  错误: {result.error_message}")

    asyncio.run(main())