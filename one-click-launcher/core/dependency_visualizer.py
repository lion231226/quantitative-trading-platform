"""
依赖关系可视化和报告工具

提供服务依赖关系的可视化、报告生成和文档输出功能。
支持多种输出格式和可视化选项。
"""

import os
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass
from pathlib import Path
import json
from datetime import datetime

from service_dependency_analyzer import ServiceDependencyGraph, ServiceInfo, ServiceType
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class VisualizationConfig:
    """可视化配置"""
    show_service_types: bool = True
    show_ports: bool = True
    show_health_endpoints: bool = False
    show_dependencies: bool = True
    show_startup_order: bool = True
    group_by_type: bool = True
    color_by_type: bool = True
    layout_engine: str = "dot"  # dot, neato, fdp, sfdp, twopi, circo


class DependencyVisualizer:
    """
    依赖关系可视化器

    功能特性：
    - 生成DOT格式的依赖图
    - 创建HTML可视化报告
    - 生成文本格式的依赖报告
    - 导出JSON格式数据
    - 支持多种可视化配置
    """

    def __init__(self, config: Optional[VisualizationConfig] = None):
        """
        初始化依赖可视化器

        Args:
            config: 可视化配置
        """
        self.config = config or VisualizationConfig()
        self.logger = get_logger(self.__class__.__name__)

        # 服务类型颜色映射
        self.type_colors = {
            ServiceType.DATABASE: "#ff6b6b",
            ServiceType.BACKEND_API: "#4ecdc4",
            ServiceType.FRONTEND: "#45b7d1",
            ServiceType.CACHE: "#96ceb4",
            ServiceType.MESSAGE_QUEUE: "#feca57",
            ServiceType.EXTERNAL_API: "#ff9ff3",
            ServiceType.UTILITY: "#dfe6e9"
        }

        # 服务类型图标映射
        self.type_icons = {
            ServiceType.DATABASE: "🗄️",
            ServiceType.BACKEND_API: "🔧",
            ServiceType.FRONTEND: "🌐",
            ServiceType.CACHE: "⚡",
            ServiceType.MESSAGE_QUEUE: "📨",
            ServiceType.EXTERNAL_API: "🌍",
            ServiceType.UTILITY: "🛠️"
        }

        self.logger.info("依赖可视化器初始化完成")

    def generate_dot_graph(self, dependency_graph: ServiceDependencyGraph,
                          output_path: Optional[str] = None) -> str:
        """
        生成DOT格式的依赖图

        Args:
            dependency_graph: 服务依赖图
            output_path: 输出文件路径（可选）

        Returns:
            DOT格式的图描述字符串
        """
        dot_lines = ["digraph ServiceDependencies {"]
        dot_lines.append("    rankdir=TB;")
        dot_lines.append("    splines=ortho;")
        dot_lines.append("    node [shape=box, style=filled, fontname=\"Arial\"];")
        dot_lines.append("    edge [fontname=\"Arial\", fontsize=10];")

        # 添加节点定义
        for service_name, service in dependency_graph.services.items():
            node_attrs = []

            # 基本属性
            label = service_name
            if self.config.show_service_types:
                label = f"{self.type_icons.get(service.service_type, '')} {service_name}"

            if self.config.show_ports and service.port:
                label += f"\\n:{service.port}"

            if self.config.show_startup_order and service.start_order:
                label += f"\\n#{service.start_order}"

            node_attrs.append(f'label="{label}"')

            # 颜色配置
            if self.config.color_by_type:
                color = self.type_colors.get(service.service_type, "#cccccc")
                node_attrs.append(f'fillcolor="{color}"')
                node_attrs.append('fontcolor="white"')

            # 节点样式
            if service.status.value == "failed":
                node_attrs.append('style="filled,dashed"')
            elif service.status.value == "disabled":
                node_attrs.append('style="filled,dotted"')

            dot_lines.append(f'    "{service_name}" [{", ".join(node_attrs)}];')

        # 按类型分组（如果启用）
        if self.config.group_by_type:
            type_groups = {}
            for service_name, service in dependency_graph.services.items():
                service_type = service.service_type.value
                if service_type not in type_groups:
                    type_groups[service_type] = []
                type_groups[service_type].append(service_name)

            for service_type, services in type_groups.items():
                if len(services) > 1:
                    cluster_name = f"cluster_{service_type}"
                    dot_lines.append(f'    subgraph {cluster_name} {{')
                    dot_lines.append(f'        label="{service_type}";')
                    dot_lines.append('        style=dashed;')
                    for service_name in services:
                        dot_lines.append(f'        "{service_name}";')
                    dot_lines.append('    }')

        # 添加依赖关系边
        if self.config.show_dependencies:
            for service_name in dependency_graph.get_all_services():
                dependencies = dependency_graph.get_dependencies(service_name)
                for dependency in dependencies:
                    if dependency in dependency_graph.services:
                        edge_style = ""
                        if service_name in dependency_graph.services and dependency in dependency_graph.services:
                            # 检查是否为强依赖（默认）
                            edge_style = '[color="#666666", weight=2]'
                        dot_lines.append(f'    "{dependency}" -> "{service_name}" {edge_style};')

        dot_lines.append("}")

        dot_content = "\n".join(dot_lines)

        # 保存到文件（如果指定了路径）
        if output_path:
            try:
                Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(dot_content)
                self.logger.info(f"DOT图已保存到: {output_path}")
            except Exception as e:
                self.logger.error(f"保存DOT图失败: {e}")

        return dot_content

    def generate_html_report(self, dependency_graph: ServiceDependencyGraph,
                           startup_sequence: List[str],
                           output_path: Optional[str] = None) -> str:
        """
        生成HTML格式的依赖报告

        Args:
            dependency_graph: 服务依赖图
            startup_sequence: 启动序列
            output_path: 输出文件路径（可选）

        Returns:
            HTML报告内容
        """
        html_content = self._build_html_report(dependency_graph, startup_sequence)

        # 保存到文件（如果指定了路径）
        if output_path:
            try:
                Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                self.logger.info(f"HTML报告已保存到: {output_path}")
            except Exception as e:
                self.logger.error(f"保存HTML报告失败: {e}")

        return html_content

    def _build_html_report(self, dependency_graph: ServiceDependencyGraph,
                          startup_sequence: List[str]) -> str:
        """构建HTML报告内容"""
        # 生成CSS样式
        css_styles = self._generate_css_styles()

        # 生成JavaScript代码
        js_code = self._generate_javascript_code()

        # 生成报告内容
        summary_section = self._generate_summary_section(dependency_graph, startup_sequence)
        services_section = self._generate_services_section(dependency_graph)
        dependencies_section = self._generate_dependencies_section(dependency_graph)
        startup_section = self._generate_startup_sequence_section(startup_sequence, dependency_graph)

        html_template = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>服务依赖关系报告</title>
    <style>{css_styles}</style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🔗 服务依赖关系报告</h1>
            <p class="subtitle">生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </header>

        <nav class="nav-tabs">
            <button class="tab-button active" onclick="showTab('summary')">📊 摘要</button>
            <button class="tab-button" onclick="showTab('services')">🔧 服务列表</button>
            <button class="tab-button" onclick="showTab('dependencies')">🔗 依赖关系</button>
            <button class="tab-button" onclick="showTab('startup')">🚀 启动序列</button>
        </nav>

        <main>
            <div id="summary" class="tab-content active">
                {summary_section}
            </div>

            <div id="services" class="tab-content">
                {services_section}
            </div>

            <div id="dependencies" class="tab-content">
                {dependencies_section}
            </div>

            <div id="startup" class="tab-content">
                {startup_section}
            </div>
        </main>
    </div>

    <script>{js_code}</script>
</body>
</html>
        """

        return html_template

    def _generate_css_styles(self) -> str:
        """生成CSS样式"""
        return """
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            background-color: #f5f5f5;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            min-height: 100vh;
            box-shadow: 0 0 10px rgba(0,0,0,0.1);
        }

        header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 2rem;
            text-align: center;
        }

        header h1 {
            font-size: 2.5rem;
            margin-bottom: 0.5rem;
        }

        .subtitle {
            opacity: 0.9;
            font-size: 1.1rem;
        }

        .nav-tabs {
            display: flex;
            background-color: #f8f9fa;
            border-bottom: 2px solid #dee2e6;
            padding: 0 2rem;
        }

        .tab-button {
            background: none;
            border: none;
            padding: 1rem 2rem;
            font-size: 1rem;
            cursor: pointer;
            transition: all 0.3s ease;
            border-bottom: 3px solid transparent;
            margin-bottom: -2px;
        }

        .tab-button:hover {
            background-color: #e9ecef;
        }

        .tab-button.active {
            border-bottom-color: #667eea;
            color: #667eea;
            font-weight: 600;
        }

        .tab-content {
            display: none;
            padding: 2rem;
            animation: fadeIn 0.3s ease-in;
        }

        .tab-content.active {
            display: block;
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .summary-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }

        .summary-card {
            background: #f8f9fa;
            padding: 1.5rem;
            border-radius: 8px;
            border-left: 4px solid #667eea;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }

        .summary-card h3 {
            color: #667eea;
            margin-bottom: 0.5rem;
        }

        .summary-card .number {
            font-size: 2rem;
            font-weight: bold;
            color: #333;
        }

        .services-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 1.5rem;
        }

        .service-card {
            background: white;
            border: 1px solid #dee2e6;
            border-radius: 8px;
            padding: 1.5rem;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }

        .service-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.15);
        }

        .service-header {
            display: flex;
            align-items: center;
            margin-bottom: 1rem;
        }

        .service-icon {
            font-size: 2rem;
            margin-right: 1rem;
        }

        .service-name {
            font-size: 1.2rem;
            font-weight: 600;
            color: #333;
        }

        .service-type {
            background: #667eea;
            color: white;
            padding: 0.25rem 0.75rem;
            border-radius: 12px;
            font-size: 0.8rem;
            margin-left: auto;
        }

        .service-details {
            color: #666;
            font-size: 0.9rem;
        }

        .service-details .detail-item {
            margin-bottom: 0.5rem;
        }

        .startup-sequence {
            background: #f8f9fa;
            border-radius: 8px;
            padding: 1.5rem;
        }

        .sequence-item {
            display: flex;
            align-items: center;
            padding: 1rem;
            background: white;
            border-radius: 6px;
            margin-bottom: 1rem;
            border-left: 4px solid #667eea;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }

        .sequence-number {
            background: #667eea;
            color: white;
            width: 30px;
            height: 30px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            margin-right: 1rem;
        }

        .dependency-graph {
            background: #f8f9fa;
            border-radius: 8px;
            padding: 1.5rem;
            overflow-x: auto;
        }

        .dependency-item {
            display: flex;
            align-items: center;
            padding: 0.75rem;
            background: white;
            border-radius: 4px;
            margin-bottom: 0.5rem;
            font-family: monospace;
        }

        .arrow {
            margin: 0 1rem;
            color: #667eea;
            font-weight: bold;
        }

        .alert {
            background: #fff3cd;
            border: 1px solid #ffeaa7;
            color: #856404;
            padding: 1rem;
            border-radius: 6px;
            margin-bottom: 1rem;
        }

        .alert-warning {
            background: #f8d7da;
            border-color: #f5c6cb;
            color: #721c24;
        }

        @media (max-width: 768px) {
            .container {
                margin: 0;
            }

            header {
                padding: 1rem;
            }

            header h1 {
                font-size: 1.8rem;
            }

            .nav-tabs {
                padding: 0 1rem;
                overflow-x: auto;
            }

            .tab-button {
                padding: 1rem;
                font-size: 0.9rem;
            }

            .tab-content {
                padding: 1rem;
            }

            .summary-grid,
            .services-grid {
                grid-template-columns: 1fr;
            }
        }
        """

    def _generate_javascript_code(self) -> str:
        """生成JavaScript代码"""
        return """
        function showTab(tabName) {
            // 隐藏所有标签内容
            const allContents = document.querySelectorAll('.tab-content');
            allContents.forEach(content => {
                content.classList.remove('active');
            });

            // 移除所有按钮的active类
            const allButtons = document.querySelectorAll('.tab-button');
            allButtons.forEach(button => {
                button.classList.remove('active');
            });

            // 显示选中的标签内容
            document.getElementById(tabName).classList.add('active');

            // 激活对应的按钮
            event.target.classList.add('active');
        }

        // 页面加载完成后的初始化
        document.addEventListener('DOMContentLoaded', function() {
            // 可以在这里添加更多的交互功能
            console.log('服务依赖关系报告已加载');
        });
        """

    def _generate_summary_section(self, dependency_graph: ServiceDependencyGraph,
                                 startup_sequence: List[str]) -> str:
        """生成摘要部分"""
        services = dependency_graph.get_all_services()
        total_services = len(services)

        # 统计服务类型
        type_counts = {}
        for service in services:
            service_type = dependency_graph.services[service].service_type.value
            type_counts[service_type] = type_counts.get(service_type, 0) + 1

        # 统计依赖关系
        total_dependencies = sum(len(dependency_graph.get_dependencies(service)) for service in services)
        services_with_deps = sum(1 for service in services if dependency_graph.get_dependencies(service))

        html = f"""
        <div class="summary-grid">
            <div class="summary-card">
                <h3>📦 服务总数</h3>
                <div class="number">{total_services}</div>
            </div>
            <div class="summary-card">
                <h3>🔗 依赖关系</h3>
                <div class="number">{total_dependencies}</div>
            </div>
            <div class="summary-card">
                <h3>🚀 启动步骤</h3>
                <div class="number">{len(startup_sequence)}</div>
            </div>
            <div class="summary-card">
                <h3>📊 有依赖的服务</h3>
                <div class="number">{services_with_deps}</div>
            </div>
        </div>

        <h3>🏷️ 服务类型分布</h3>
        <div class="summary-grid">
        """

        for service_type, count in type_counts.items():
            icon = self.type_icons.get(ServiceType(service_type), "📦")
            html += f"""
            <div class="summary-card">
                <h3>{icon} {service_type}</h3>
                <div class="number">{count}</div>
            </div>
            """

        html += "</div>"
        return html

    def _generate_services_section(self, dependency_graph: ServiceDependencyGraph) -> str:
        """生成服务列表部分"""
        html = '<div class="services-grid">'

        for service_name, service in dependency_graph.services.items():
            icon = self.type_icons.get(service.service_type, "📦")

            dependencies = dependency_graph.get_dependencies(service_name)
            dependents = dependency_graph.get_dependents(service_name)

            html += f"""
            <div class="service-card">
                <div class="service-header">
                    <div class="service-icon">{icon}</div>
                    <div class="service-name">{service_name}</div>
                    <div class="service-type">{service.service_type.value}</div>
                </div>
                <div class="service-details">
                    <div class="detail-item">
                        <strong>状态:</strong> {service.status.value}
                    </div>
                    <div class="detail-item">
                        <strong>主机:</strong> {service.host}
                    </div>
                    """

            if service.port:
                html += f"""
                    <div class="detail-item">
                        <strong>端口:</strong> {service.port}
                    </div>
                    """

            if service.start_order:
                html += f"""
                    <div class="detail-item">
                        <strong>启动顺序:</strong> #{service.start_order}
                    </div>
                    """

            if dependencies:
                html += f"""
                    <div class="detail-item">
                        <strong>依赖:</strong> {', '.join(dependencies)}
                    </div>
                    """

            if dependents:
                html += f"""
                    <div class="detail-item">
                        <strong>被依赖:</strong> {', '.join(dependents)}
                    </div>
                    """

            html += """
                </div>
            </div>
            """

        html += "</div>"
        return html

    def _generate_dependencies_section(self, dependency_graph: ServiceDependencyGraph) -> str:
        """生成依赖关系部分"""
        html = '<div class="dependency-graph">'

        for service_name in dependency_graph.get_all_services():
            dependencies = dependency_graph.get_dependencies(service_name)
            if dependencies:
                for dependency in dependencies:
                    if dependency in dependency_graph.services:
                        html += f"""
                        <div class="dependency-item">
                            <span>{dependency}</span>
                            <span class="arrow">→</span>
                            <span>{service_name}</span>
                        </div>
                        """

        if not any(dependency_graph.get_dependencies(service) for service in dependency_graph.get_all_services()):
            html += '<p>暂无依赖关系</p>'

        html += "</div>"
        return html

    def _generate_startup_sequence_section(self, startup_sequence: List[str],
                                         dependency_graph: ServiceDependencyGraph) -> str:
        """生成启动序列部分"""
        html = '<div class="startup-sequence">'

        for order, service_name in enumerate(startup_sequence, 1):
            if service_name in dependency_graph.services:
                service = dependency_graph.services[service_name]
                icon = self.type_icons.get(service.service_type, "📦")

                dependencies = dependency_graph.get_dependencies(service_name)
                deps_text = f" (依赖: {', '.join(dependencies)})" if dependencies else ""

                html += f"""
                <div class="sequence-item">
                    <div class="sequence-number">{order}</div>
                    <div class="service-icon">{icon}</div>
                    <div>
                        <strong>{service_name}</strong>
                        <span style="color: #666; margin-left: 0.5rem;">{deps_text}</span>
                    </div>
                </div>
                """

        html += "</div>"
        return html

    def generate_text_report(self, dependency_graph: ServiceDependencyGraph,
                           startup_sequence: List[str],
                           output_path: Optional[str] = None) -> str:
        """
        生成文本格式的依赖报告

        Args:
            dependency_graph: 服务依赖图
            startup_sequence: 启动序列
            output_path: 输出文件路径（可选）

        Returns:
            文本报告内容
        """
        lines = []
        lines.append("=" * 60)
        lines.append("🔗 服务依赖关系报告")
        lines.append("=" * 60)
        lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")

        # 摘要信息
        lines.append("📊 摘要信息")
        lines.append("-" * 30)
        services = dependency_graph.get_all_services()
        lines.append(f"服务总数: {len(services)}")

        total_dependencies = sum(len(dependency_graph.get_dependencies(service)) for service in services)
        lines.append(f"依赖关系总数: {total_dependencies}")
        lines.append(f"启动序列长度: {len(startup_sequence)}")
        lines.append("")

        # 服务类型统计
        lines.append("🏷️ 服务类型分布")
        lines.append("-" * 30)
        type_counts = {}
        for service in services:
            service_type = dependency_graph.services[service].service_type.value
            type_counts[service_type] = type_counts.get(service_type, 0) + 1

        for service_type, count in sorted(type_counts.items()):
            icon = self.type_icons.get(ServiceType(service_type), "📦")
            lines.append(f"{icon} {service_type}: {count}")
        lines.append("")

        # 启动序列
        lines.append("🚀 推荐启动序列")
        lines.append("-" * 30)
        for order, service_name in enumerate(startup_sequence, 1):
            if service_name in dependency_graph.services:
                service = dependency_graph.services[service_name]
                dependencies = dependency_graph.get_dependencies(service_name)
                deps_text = f" (依赖: {', '.join(dependencies)})" if dependencies else ""
                lines.append(f"{order:2d}. {service_name}{deps_text}")
        lines.append("")

        # 服务详情
        lines.append("🔧 服务详细信息")
        lines.append("-" * 30)
        for service_name, service in dependency_graph.services.items():
            lines.append(f"服务: {service_name}")
            lines.append(f"  类型: {service.service_type.value}")
            lines.append(f"  状态: {service.status.value}")
            lines.append(f"  主机: {service.host}")
            if service.port:
                lines.append(f"  端口: {service.port}")
            if service.health_endpoint:
                lines.append(f"  健康检查: {service.health_endpoint}")
            if service.start_order:
                lines.append(f"  启动顺序: #{service.start_order}")

            dependencies = dependency_graph.get_dependencies(service_name)
            if dependencies:
                lines.append(f"  依赖: {', '.join(dependencies)}")

            dependents = dependency_graph.get_dependents(service_name)
            if dependents:
                lines.append(f"  被依赖: {', '.join(dependents)}")

            lines.append("")

        # 依赖关系
        lines.append("🔗 依赖关系图")
        lines.append("-" * 30)
        has_dependencies = False
        for service_name in dependency_graph.get_all_services():
            dependencies = dependency_graph.get_dependencies(service_name)
            for dependency in dependencies:
                if dependency in dependency_graph.services:
                    lines.append(f"{dependency} → {service_name}")
                    has_dependencies = True

        if not has_dependencies:
            lines.append("暂无依赖关系")

        text_content = "\n".join(lines)

        # 保存到文件（如果指定了路径）
        if output_path:
            try:
                Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(text_content)
                self.logger.info(f"文本报告已保存到: {output_path}")
            except Exception as e:
                self.logger.error(f"保存文本报告失败: {e}")

        return text_content

    def export_json_data(self, dependency_graph: ServiceDependencyGraph,
                        startup_sequence: List[str],
                        output_path: Optional[str] = None) -> str:
        """
        导出JSON格式的数据

        Args:
            dependency_graph: 服务依赖图
            startup_sequence: 启动序列
            output_path: 输出文件路径（可选）

        Returns:
            JSON数据字符串
        """
        data = {
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'total_services': len(dependency_graph.get_all_services()),
                'total_dependencies': sum(len(dependency_graph.get_dependencies(service))
                                        for service in dependency_graph.get_all_services()),
                'startup_sequence_length': len(startup_sequence)
            },
            'dependency_graph': dependency_graph.to_dict(),
            'startup_sequence': startup_sequence,
            'summary': self._generate_summary_data(dependency_graph, startup_sequence)
        }

        json_content = json.dumps(data, indent=2, ensure_ascii=False)

        # 保存到文件（如果指定了路径）
        if output_path:
            try:
                Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(json_content)
                self.logger.info(f"JSON数据已保存到: {output_path}")
            except Exception as e:
                self.logger.error(f"保存JSON数据失败: {e}")

        return json_content

    def _generate_summary_data(self, dependency_graph: ServiceDependencyGraph,
                             startup_sequence: List[str]) -> Dict[str, Any]:
        """生成摘要数据"""
        services = dependency_graph.get_all_services()

        # 服务类型统计
        type_counts = {}
        for service in services:
            service_type = dependency_graph.services[service].service_type.value
            type_counts[service_type] = type_counts.get(service_type, 0) + 1

        # 依赖统计
        dependency_stats = {
            'total_dependencies': 0,
            'services_with_dependencies': 0,
            'services_with_no_dependencies': 0,
            'max_dependencies_per_service': 0,
            'services_with_most_dependencies': []
        }

        max_deps = 0
        for service in services:
            deps_count = len(dependency_graph.get_dependencies(service))
            dependency_stats['total_dependencies'] += deps_count

            if deps_count > 0:
                dependency_stats['services_with_dependencies'] += 1
            else:
                dependency_stats['services_with_no_dependencies'] += 1

            if deps_count > max_deps:
                max_deps = deps_count
                dependency_stats['services_with_most_dependencies'] = [service]
            elif deps_count == max_deps:
                dependency_stats['services_with_most_dependencies'].append(service)

        dependency_stats['max_dependencies_per_service'] = max_deps

        return {
            'service_types': type_counts,
            'dependency_statistics': dependency_stats,
            'startup_sequence': startup_sequence
        }