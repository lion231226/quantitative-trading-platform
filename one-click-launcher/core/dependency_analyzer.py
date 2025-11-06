"""
项目依赖分析器

This module provides comprehensive dependency analysis capabilities
including detection of project dependency files, version conflict analysis,
and installation priority management for the one-click launcher.
"""

import os
import re
import json
import subprocess
from typing import Dict, List, Optional, Tuple, Set, Any, Union
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import threading
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed

from utils.logger import get_logger
from core.dependency_checker import DependencyInfo, DependencyType, VersionInfo, VersionComparator

logger = get_logger(__name__)


class DependencyFileFormat(Enum):
    """支持的依赖文件格式"""
    PYTHON_REQUIREMENTS = "requirements.txt"
    PYTHON_SETUP = "setup.py"
    PYTHON_PYPROJECT = "pyproject.toml"
    NODEJS_PACKAGE = "package.json"
    NODEJS_YARN = "yarn.lock"
    NODEJS_PNPM = "pnpm-lock.yaml"
    DOCKER_COMPOSE = "docker-compose.yml"
    DOCKER_COMPOSE_YAML = "docker-compose.yaml"
    ENVIRONMENT = ".env"


@dataclass
class DependencyFile:
    """依赖文件信息"""
    path: str
    format: DependencyFileFormat
    exists: bool = True
    content: Optional[str] = None
    dependencies: List['ProjectDependency'] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProjectDependency:
    """项目依赖项"""
    name: str
    ecosystem: str  # python, nodejs, database, system
    version_spec: Optional[str] = None
    version_info: Optional[VersionInfo] = None
    is_dev_dependency: bool = False
    is_optional: bool = False
    source_file: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        if self.version_spec:
            return f"{self.name}{self.version_spec}"
        return self.name

    @property
    def display_name(self) -> str:
        """显示名称，包含生态系统"""
        return f"{self.ecosystem}:{self.name}"


@dataclass
class DependencyConflict:
    """依赖冲突信息"""
    dependency_name: str
    ecosystem: str
    conflicts: List[Tuple[str, str]]  # (version_spec, source_file)
    severity: str  # "error", "warning", "info"
    description: str
    suggested_resolution: Optional[str] = None


@dataclass
class DependencyAnalysis:
    """依赖分析结果"""
    project_root: str
    dependency_files: List[DependencyFile]
    all_dependencies: List[ProjectDependency]
    conflicts: List[DependencyConflict]
    installation_order: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def total_dependencies(self) -> int:
        return len(self.all_dependencies)

    @property
    def dependencies_by_ecosystem(self) -> Dict[str, List[ProjectDependency]]:
        result = {}
        for dep in self.all_dependencies:
            result.setdefault(dep.ecosystem, []).append(dep)
        return result

    @property
    def has_conflicts(self) -> bool:
        return len(self.conflicts) > 0


class DependencyAnalyzer:
    """
    项目依赖分析器

    功能特性：
    - 自动检测项目依赖文件
    - 解析多种格式的依赖配置
    - 版本冲突检测和分析
    - 安装优先级排序
    - 并发分析优化
    """

    # 支持的依赖文件模式
    DEPENDENCY_FILE_PATTERNS = {
        DependencyFileFormat.PYTHON_REQUIREMENTS: [
            "requirements.txt",
            "requirements/*.txt",
            "requirements-*.txt",
            "requirements-dev.txt",
            "requirements-prod.txt"
        ],
        DependencyFileFormat.PYTHON_SETUP: ["setup.py"],
        DependencyFileFormat.PYTHON_PYPROJECT: ["pyproject.toml"],
        DependencyFileFormat.NODEJS_PACKAGE: ["package.json"],
        DependencyFileFormat.NODEJS_YARN: ["yarn.lock"],
        DependencyFileFormat.NODEJS_PNPM: ["pnpm-lock.yaml"],
        DependencyFileFormat.DOCKER_COMPOSE: [
            "docker-compose.yml",
            "docker-compose.yaml"
        ],
        DependencyFileFormat.ENVIRONMENT: [".env*", "*.env"]
    }

    # 数据库服务检测模式
    DATABASE_SERVICE_PATTERNS = {
        "redis": ["redis", "redis-cache", "redis-db"],
        "postgresql": ["postgres", "postgresql", "psql"],
        "mysql": ["mysql", "mariadb"],
        "mongodb": ["mongo", "mongodb"],
        "sqlite": ["sqlite", "sqlite3"]
    }

    def __init__(self, project_root: str, config_manager: Optional[Any] = None):
        """
        初始化依赖分析器

        Args:
            project_root: 项目根目录
            config_manager: 配置管理器（可选）
        """
        self.project_root = Path(project_root).resolve()
        self.config_manager = config_manager
        self.logger = get_logger(self.__class__.__name__)
        self._lock = threading.Lock()

        # 分析统计
        self.analysis_stats = {
            "files_scanned": 0,
            "dependencies_found": 0,
            "conflicts_detected": 0,
            "analysis_time_ms": 0
        }

        self.logger.info(f"初始化依赖分析器，项目根目录: {self.project_root}")

    def detect_dependency_files(self) -> Dict[str, List[str]]:
        """
        检测项目中的依赖文件

        Returns:
            字典，键为文件格式，值为文件路径列表
        """
        self.logger.info("开始检测项目依赖文件...")

        discovered_files = {}
        with ThreadPoolExecutor(max_workers=4) as executor:
            # 并发搜索各种类型的依赖文件
            future_to_format = {}

            for file_format, patterns in self.DEPENDENCY_FILE_PATTERNS.items():
                future = executor.submit(self._search_files_by_patterns, patterns)
                future_to_format[future] = file_format

            for future in as_completed(future_to_format):
                file_format = future_to_format[future]
                try:
                    files = future.result()
                    if files:
                        discovered_files[file_format.value] = files
                        self.logger.debug(f"发现 {file_format.value}: {len(files)} 个文件")
                except Exception as e:
                    self.logger.error(f"搜索 {file_format.value} 文件时出错: {e}")

        self.analysis_stats["files_scanned"] = sum(len(files) for files in discovered_files.values())
        self.logger.info(f"依赖文件检测完成，共发现 {self.analysis_stats['files_scanned']} 个文件")

        return discovered_files

    def _search_files_by_patterns(self, patterns: List[str]) -> List[str]:
        """根据模式搜索文件"""
        found_files = []

        for pattern in patterns:
            # 处理通配符模式
            if "*" in pattern:
                try:
                    import glob
                    search_path = self.project_root / pattern
                    matches = glob.glob(str(search_path), recursive=True)
                    found_files.extend([f for f in matches if os.path.isfile(f)])
                except Exception as e:
                    self.logger.debug(f"搜索模式 {pattern} 时出错: {e}")
            else:
                # 精确文件名搜索
                file_path = self.project_root / pattern
                if file_path.exists() and file_path.is_file():
                    found_files.append(str(file_path))
                else:
                    # 在子目录中搜索
                    try:
                        for found in self.project_root.rglob(pattern):
                            if found.is_file():
                                found_files.append(str(found))
                    except Exception as e:
                        self.logger.debug(f"递归搜索 {pattern} 时出错: {e}")

        # 去重并排序
        return sorted(list(set(found_files)))

    def analyze_dependencies(self) -> DependencyAnalysis:
        """
        分析项目依赖

        Returns:
            完整的依赖分析结果
        """
        import time
        start_time = time.time()

        self.logger.info("开始分析项目依赖...")

        # 1. 检测依赖文件
        discovered_files = self.detect_dependency_files()

        # 2. 解析依赖文件
        dependency_files = []
        all_dependencies = []

        with ThreadPoolExecutor(max_workers=4) as executor:
            file_futures = []

            for file_format, file_paths in discovered_files.items():
                for file_path in file_paths:
                    future = executor.submit(self._parse_dependency_file, file_path, file_format)
                    file_futures.append((future, file_path, file_format))

            for future, file_path, file_format in file_futures:
                try:
                    dep_file = future.result()
                    dependency_files.append(dep_file)
                    all_dependencies.extend(dep_file.dependencies)
                    self.logger.debug(f"解析完成: {file_path} ({len(dep_file.dependencies)} 个依赖)")
                except Exception as e:
                    self.logger.error(f"解析文件 {file_path} 时出错: {e}")

        # 3. 检测数据库服务依赖
        database_deps = self._detect_database_services()
        all_dependencies.extend(database_deps)

        # 4. 检测版本冲突
        conflicts = self._detect_conflicts(all_dependencies)

        # 5. 确定安装顺序
        installation_order = self._determine_installation_order(all_dependencies)

        # 构建分析结果
        analysis = DependencyAnalysis(
            project_root=str(self.project_root),
            dependency_files=dependency_files,
            all_dependencies=all_dependencies,
            conflicts=conflicts,
            installation_order=installation_order,
            metadata={
                "analysis_timestamp": start_time,
                "analyzer_version": "1.0.0",
                "project_name": self.project_root.name
            }
        )

        # 更新统计信息
        self.analysis_stats.update({
            "dependencies_found": len(all_dependencies),
            "conflicts_detected": len(conflicts),
            "analysis_time_ms": int((time.time() - start_time) * 1000)
        })

        self.logger.info(f"依赖分析完成: {len(all_dependencies)} 个依赖, {len(conflicts)} 个冲突")
        return analysis

    def _parse_dependency_file(self, file_path: str, file_format: str) -> DependencyFile:
        """解析单个依赖文件"""
        path_obj = Path(file_path)
        format_enum = DependencyFileFormat(file_format)

        try:
            with open(path_obj, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            self.logger.warning(f"无法读取文件 {file_path}: {e}")
            return DependencyFile(
                path=file_path,
                format=format_enum,
                exists=False,
                metadata={"error": str(e)}
            )

        dependencies = []
        metadata = {"file_size": len(content)}

        # 根据文件格式解析依赖
        if format_enum == DependencyFileFormat.PYTHON_REQUIREMENTS:
            dependencies = self._parse_requirements_txt(content, file_path)
        elif format_enum == DependencyFileFormat.PYTHON_PYPROJECT:
            dependencies = self._parse_pyproject_toml(content, file_path)
        elif format_enum == DependencyFileFormat.NODEJS_PACKAGE:
            dependencies, pkg_metadata = self._parse_package_json(content, file_path)
            metadata.update(pkg_metadata)
        elif format_enum == DependencyFileFormat.DOCKER_COMPOSE:
            dependencies = self._parse_docker_compose(content, file_path)

        return DependencyFile(
            path=file_path,
            format=format_enum,
            exists=True,
            content=content,
            dependencies=dependencies,
            metadata=metadata
        )

    def _parse_requirements_txt(self, content: str, file_path: str) -> List[ProjectDependency]:
        """解析 requirements.txt 文件"""
        dependencies = []
        is_dev = "dev" in file_path.lower() or "test" in file_path.lower()

        for line_num, line in enumerate(content.split('\n'), 1):
            line = line.strip()

            # 跳过空行和注释
            if not line or line.startswith('#'):
                continue

            # 跳过 -r 包含的其他文件
            if line.startswith('-r '):
                continue

            # 解析依赖规格
            try:
                dep = self._parse_python_requirement_line(line, file_path, is_dev)
                if dep:
                    dependencies.append(dep)
            except Exception as e:
                self.logger.debug(f"解析 requirements 第 {line_num} 行失败: {line} ({e})")

        return dependencies

    def _parse_python_requirement_line(self, line: str, source_file: str, is_dev: bool = False) -> Optional[ProjectDependency]:
        """解析单行 Python 依赖规格"""
        # 基本的包名和版本匹配模式
        pattern = r'^([a-zA-Z0-9][a-zA-Z0-9\-_\.]*)([><=!~]+.*)?$'
        match = re.match(pattern, line.strip())

        if not match:
            return None

        name = match.group(1)
        version_spec = match.group(2) or ""

        # 清理包名
        name = re.sub(r'[-_]+', '-', name).lower()

        return ProjectDependency(
            name=name,
            ecosystem="python",
            version_spec=version_spec,
            is_dev_dependency=is_dev,
            source_file=source_file,
            metadata={"original_line": line}
        )

    def _parse_package_json(self, content: str, file_path: str) -> Tuple[List[ProjectDependency], Dict[str, Any]]:
        """解析 package.json 文件"""
        try:
            package_data = json.loads(content)
        except json.JSONDecodeError as e:
            self.logger.error(f"解析 package.json 失败: {e}")
            return [], {"error": str(e)}

        dependencies = []
        metadata = {
            "package_name": package_data.get("name", ""),
            "package_version": package_data.get("version", ""),
            "engines": package_data.get("engines", {})
        }

        # 解析生产依赖
        for name, version in package_data.get("dependencies", {}).items():
            dependencies.append(ProjectDependency(
                name=name,
                ecosystem="nodejs",
                version_spec=version,
                is_dev_dependency=False,
                source_file=file_path
            ))

        # 解析开发依赖
        for name, version in package_data.get("devDependencies", {}).items():
            dependencies.append(ProjectDependency(
                name=name,
                ecosystem="nodejs",
                version_spec=version,
                is_dev_dependency=True,
                source_file=file_path
            ))

        return dependencies, metadata

    def _parse_pyproject_toml(self, content: str, file_path: str) -> List[ProjectDependency]:
        """解析 pyproject.toml 文件（简化版本）"""
        dependencies = []

        # 简单的 TOML 解析（生产环境建议使用 toml 库）
        try:
            # 查找 [project.dependencies] 部分
            project_match = re.search(r'\[project\](.*?)(?=\[|$)', content, re.DOTALL)
            if project_match:
                project_section = project_match.group(1)
                # 查找 dependencies 数组
                deps_match = re.search(r'dependencies\s*=\s*\[(.*?)\]', project_section, re.DOTALL)
                if deps_match:
                    deps_content = deps_match.group(1)
                    # 提取引号内的依赖
                    for line in deps_content.split('\n'):
                        line = line.strip().strip('"').strip("'")
                        if line and not line.startswith('#'):
                            dep = self._parse_python_requirement_line(line, file_path)
                            if dep:
                                dependencies.append(dep)
        except Exception as e:
            self.logger.debug(f"解析 pyproject.toml 时出错: {e}")

        return dependencies

    def _parse_docker_compose(self, content: str, file_path: str) -> List[ProjectDependency]:
        """解析 docker-compose 文件中的数据库服务"""
        dependencies = []

        for service_name, patterns in self.DATABASE_SERVICE_PATTERNS.items():
            for pattern in patterns:
                if re.search(rf'\b{pattern}\b', content, re.IGNORECASE):
                    dependencies.append(ProjectDependency(
                        name=service_name,
                        ecosystem="database",
                        source_file=file_path,
                        metadata={"detected_in_compose": True}
                    ))
                    break

        return dependencies

    def _detect_database_services(self) -> List[ProjectDependency]:
        """检测数据库服务依赖"""
        database_deps = []

        # 检查配置文件和源代码中的数据库连接
        config_patterns = {
            "redis": [r'redis://', r'redis_host', r'redis_port'],
            "postgresql": [r'postgresql://', r'postgres://', r'db_host.*postgres'],
            "mysql": [r'mysql://', r'mysql_host'],
            "mongodb": [r'mongodb://', r'mongo_host']
        }

        for service_name, patterns in config_patterns.items():
            try:
                if self._search_patterns_in_files(patterns):
                    database_deps.append(ProjectDependency(
                        name=service_name,
                        ecosystem="database",
                        metadata={"detected_in_config": True}
                    ))
            except Exception as e:
                self.logger.debug(f"检测 {service_name} 服务时出错: {e}")

        return database_deps

    def _search_patterns_in_files(self, patterns: List[str]) -> bool:
        """在项目文件中搜索模式"""
        search_extensions = ['.py', '.js', '.ts', '.json', '.yaml', '.yml', '.env', '.ini']

        try:
            for ext in search_extensions:
                for file_path in self.project_root.rglob(f"*{ext}"):
                    if file_path.is_file() and not any(skip in str(file_path) for skip in ['.git', 'node_modules', '__pycache__']):
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                                for pattern in patterns:
                                    if re.search(pattern, content, re.IGNORECASE):
                                        return True
                        except Exception:
                            continue  # 忽略无法读取的文件
        except Exception as e:
            self.logger.debug(f"搜索文件模式时出错: {e}")

        return False

    def detect_conflicts(self, dependencies: List[ProjectDependency]) -> List[DependencyConflict]:
        """检测版本冲突"""
        return self._detect_conflicts(dependencies)

    def _detect_conflicts(self, dependencies: List[ProjectDependency]) -> List[DependencyConflict]:
        """检测依赖版本冲突"""
        conflicts = []

        # 按生态系统和名称分组
        dep_groups = {}
        for dep in dependencies:
            key = f"{dep.ecosystem}:{dep.name}"
            dep_groups.setdefault(key, []).append(dep)

        for dep_key, group in dep_groups.items():
            if len(group) > 1:
                # 检查版本规格冲突
                version_specs = [(dep.version_spec or "any", dep.source_file) for dep in group]
                unique_specs = list(set(spec[0] for spec in version_specs))

                if len(unique_specs) > 1:
                    ecosystem, name = dep_key.split(':', 1)
                    conflict = DependencyConflict(
                        dependency_name=name,
                        ecosystem=ecosystem,
                        conflicts=version_specs,
                        severity="warning",
                        description=f"发现 {name} 的多个版本规格",
                        suggested_resolution="统一版本规格以避免潜在冲突"
                    )
                    conflicts.append(conflict)

        return conflicts

    def _determine_installation_order(self, dependencies: List[ProjectDependency]) -> List[str]:
        """确定依赖安装顺序"""
        # 按生态系统分组并排序
        ecosystem_order = {
            "system": 0,      # 系统依赖最先
            "database": 1,    # 数据库服务
            "python": 2,      # Python 环境
            "nodejs": 3       # Node.js 环境
        }

        # 按生态系统分组
        grouped = {}
        for dep in dependencies:
            grouped.setdefault(dep.ecosystem, []).append(dep)

        # 确定安装顺序
        installation_order = []
        for ecosystem in sorted(grouped.keys(), key=lambda x: ecosystem_order.get(x, 999)):
            deps = grouped[ecosystem]
            # 按名称排序
            deps.sort(key=lambda x: x.name)
            installation_order.extend(f"{dep.ecosystem}:{dep.name}" for dep in deps)

        return installation_order

    def get_analysis_summary(self, analysis: DependencyAnalysis) -> Dict[str, Any]:
        """获取分析摘要"""
        summary = {
            "project_root": analysis.project_root,
            "total_dependencies": analysis.total_dependencies,
            "total_files": len(analysis.dependency_files),
            "conflicts_count": len(analysis.conflicts),
            "ecosystems": list(analysis.dependencies_by_ecosystem.keys()),
            "dependencies_by_ecosystem": {
                ecosystem: len(deps)
                for ecosystem, deps in analysis.dependencies_by_ecosystem.items()
            },
            "installation_steps": len(analysis.installation_order),
            "analysis_stats": self.analysis_stats
        }

        return summary

    def export_analysis_report(self, analysis: DependencyAnalysis, output_path: str) -> bool:
        """导出分析报告"""
        try:
            report = {
                "analysis_summary": self.get_analysis_summary(analysis),
                "dependency_files": [
                    {
                        "path": df.path,
                        "format": df.format.value,
                        "exists": df.exists,
                        "dependencies_count": len(df.dependencies),
                        "metadata": df.metadata
                    }
                    for df in analysis.dependency_files
                ],
                "dependencies": [
                    {
                        "name": dep.name,
                        "ecosystem": dep.ecosystem,
                        "version_spec": dep.version_spec,
                        "is_dev": dep.is_dev_dependency,
                        "source_file": dep.source_file
                    }
                    for dep in analysis.all_dependencies
                ],
                "conflicts": [
                    {
                        "dependency": conflict.dependency_name,
                        "ecosystem": conflict.ecosystem,
                        "severity": conflict.severity,
                        "description": conflict.description,
                        "conflicts": conflict.conflicts
                    }
                    for conflict in analysis.conflicts
                ],
                "installation_order": analysis.installation_order
            }

            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)

            self.logger.info(f"分析报告已导出到: {output_path}")
            return True

        except Exception as e:
            self.logger.error(f"导出分析报告失败: {e}")
            return False