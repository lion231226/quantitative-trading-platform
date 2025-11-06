#!/usr/bin/env python3
"""
依赖版本冲突检测和解决模块

提供跨平台的依赖版本检查、冲突检测、兼容性验证和自动解决功能。
支持Python pip、Node.js npm、系统级依赖等多种依赖管理工具。
"""

import asyncio
import os
import sys
import subprocess
import json
import re
import platform
from typing import Dict, List, Optional, Tuple, Union, Any, Set
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
try:
    from packaging import version
except ImportError:
    # 如果packaging库不可用，使用简单的版本比较
    version = None

try:
    import yaml
except ImportError:
    # 如果yaml库不可用，跳过yaml文件解析
    yaml = None
from concurrent.futures import ThreadPoolExecutor, as_completed

from utils.logger import get_logger
from utils.progress_tracker import ProgressTracker

logger = get_logger(__name__)


class DependencyType(Enum):
    """依赖类型枚举"""
    PYTHON_PIP = "python_pip"
    NODE_NPM = "node_npm"
    SYSTEM_PACKAGE = "system_package"
    DOCKER = "docker"
    DATABASE = "database"
    RUNTIME = "runtime"


class ConflictSeverity(Enum):
    """冲突严重程度枚举"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ResolutionType(Enum):
    """解决类型枚举"""
    UPGRADE = "upgrade"
    DOWNGRADE = "downgrade"
    REPLACE = "replace"
    REMOVE = "remove"
    PIN = "pin"
    IGNORE = "ignore"


@dataclass
class DependencyInfo:
    """依赖信息"""
    name: str
    current_version: Optional[str] = None
    required_version: Optional[str] = None
    dependency_type: DependencyType = DependencyType.PYTHON_PIP
    installed: bool = False
    compatible: bool = True
    conflicts: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class VersionConflict:
    """版本冲突信息"""
    dependency_name: str
    dependency_type: DependencyType
    current_version: Optional[str]
    required_version: Optional[str]
    conflict_type: str
    severity: ConflictSeverity
    description: str
    affected_dependencies: List[str] = field(default_factory=list)
    resolution_options: List[Dict[str, Any]] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DependencyResolution:
    """依赖解决信息"""
    conflict: VersionConflict
    resolution_type: ResolutionType
    target_version: Optional[str]
    command: str
    description: str
    risks: List[str] = field(default_factory=list)
    benefits: List[str] = field(default_factory=list)
    automated: bool = False


@dataclass
class DependencyAnalysisResult:
    """依赖分析结果"""
    timestamp: str
    total_dependencies: int
    compatible_dependencies: int
    conflicting_dependencies: int
    missing_dependencies: int
    conflicts: List[VersionConflict] = field(default_factory=list)
    resolutions: List[DependencyResolution] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)


class DependencyConflictDetector:
    """依赖冲突检测器"""

    def __init__(self, progress_tracker: Optional[ProgressTracker] = None):
        self.progress_tracker = progress_tracker
        self.platform = platform.system().lower()
        self.executor = ThreadPoolExecutor(max_workers=10)

        # 缓存
        self._package_cache = {}
        self._version_cache = {}

    def _log(self, message: str, level: str = "info"):
        """记录日志"""
        if self.progress_tracker:
            self.progress_tracker._log(message)
        else:
            getattr(logger, level)(message)

    async def analyze_dependencies(self, project_path: str = None) -> DependencyAnalysisResult:
        """分析项目依赖冲突"""
        from datetime import datetime

        self._log("Starting comprehensive dependency conflict analysis")

        if project_path is None:
            project_path = os.getcwd()

        result = DependencyAnalysisResult(
            timestamp=datetime.now().isoformat(),
            total_dependencies=0,
            compatible_dependencies=0,
            conflicting_dependencies=0,
            missing_dependencies=0
        )

        # 1. 扫描项目依赖
        if self.progress_tracker:
            self.progress_tracker._log("Scanning project dependencies (20%)")
        dependencies = await self._scan_project_dependencies(project_path)
        result.total_dependencies = len(dependencies)

        # 2. 检查依赖安装状态
        if self.progress_tracker:
            self.progress_tracker._log("Checking dependency installation status (40%)")
        await self._check_installation_status(dependencies)

        # 3. 验证版本兼容性
        if self.progress_tracker:
            self.progress_tracker._log("Validating version compatibility (60%)")
        conflicts = await self._detect_version_conflicts(dependencies)
        result.conflicts = conflicts
        result.conflicting_dependencies = len(conflicts)

        # 4. 生成解决方案
        if self.progress_tracker:
            self.progress_tracker._log("Generating resolution options (80%)")
        resolutions = await self._generate_resolutions(conflicts)
        result.resolutions = resolutions

        # 5. 统计兼容依赖
        result.compatible_dependencies = len([d for d in dependencies if d.compatible])
        result.missing_dependencies = len([d for d in dependencies if not d.installed])

        # 6. 生成建议
        if self.progress_tracker:
            self.progress_tracker._log("Generating recommendations (90%)")
        result.recommendations = self._generate_recommendations(result)
        result.summary = self._generate_summary(result)

        if self.progress_tracker:
            self.progress_tracker._log("Dependency analysis completed (100%)")

        return result

    async def _scan_project_dependencies(self, project_path: str) -> List[DependencyInfo]:
        """扫描项目依赖"""
        dependencies = []

        # 扫描Python依赖
        python_deps = await self._scan_python_dependencies(project_path)
        dependencies.extend(python_deps)

        # 扫描Node.js依赖
        node_deps = await self._scan_node_dependencies(project_path)
        dependencies.extend(node_deps)

        # 扫描系统依赖
        system_deps = await self._scan_system_dependencies(project_path)
        dependencies.extend(system_deps)

        return dependencies

    async def _scan_python_dependencies(self, project_path: str) -> List[DependencyInfo]:
        """扫描Python依赖"""
        dependencies = []

        # 扫描requirements.txt
        requirements_file = os.path.join(project_path, "requirements.txt")
        if os.path.exists(requirements_file):
            deps = await self._parse_requirements_file(requirements_file)
            dependencies.extend(deps)

        # 扫描pyproject.toml
        pyproject_file = os.path.join(project_path, "pyproject.toml")
        if os.path.exists(pyproject_file):
            deps = await self._parse_pyproject_file(pyproject_file)
            dependencies.extend(deps)

        # 扫描setup.py
        setup_file = os.path.join(project_path, "setup.py")
        if os.path.exists(setup_file):
            deps = await self._parse_setup_file(setup_file)
            dependencies.extend(deps)

        # 扫描Pipfile
        pipfile = os.path.join(project_path, "Pipfile")
        if os.path.exists(pipfile):
            deps = await self._parse_pipfile(pipfile)
            dependencies.extend(deps)

        return dependencies

    async def _parse_requirements_file(self, file_path: str) -> List[DependencyInfo]:
        """解析requirements.txt文件"""
        dependencies = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            for line in lines:
                line = line.strip()
                if line and not line.startswith('#') and not line.startswith('-'):
                    dep = self._parse_requirement_line(line)
                    if dep:
                        dependencies.append(dep)

        except Exception as e:
            self._log(f"Error parsing requirements.txt: {e}", "error")

        return dependencies

    def _parse_requirement_line(self, line: str) -> Optional[DependencyInfo]:
        """解析单行依赖要求"""
        # 解析格式：package_name==1.0.0, package_name>=1.0.0,<2.0.0
        patterns = [
            r'^([a-zA-Z0-9\-_\.]+)([><=!~]+)(.+)$',  # package_name==1.0.0
            r'^([a-zA-Z0-9\-_\.]+)$',  # package_name (no version specified)
        ]

        for pattern in patterns:
            match = re.match(pattern, line)
            if match:
                name = match.group(1).lower()
                if len(match.groups()) > 1:
                    required_version = match.group(2) + match.group(3)
                else:
                    required_version = None

                return DependencyInfo(
                    name=name,
                    required_version=required_version,
                    dependency_type=DependencyType.PYTHON_PIP
                )

        return None

    async def _parse_pyproject_file(self, file_path: str) -> List[DependencyInfo]:
        """解析pyproject.toml文件"""
        dependencies = []

        try:
            # 尝试导入toml库
            try:
                import tomllib
            except ImportError:
                try:
                    import tomli as tomllib
                except ImportError:
                    self._log("tomllib/tomli not available, skipping pyproject.toml parsing", "warning")
                    return dependencies

            with open(file_path, 'rb') as f:
                data = tomllib.load(f)

            # 解析dependencies
            deps = data.get('project', {}).get('dependencies', [])
            for dep in deps:
                parsed = self._parse_requirement_line(dep)
                if parsed:
                    dependencies.append(parsed)

            # 解析optional dependencies
            optional_deps = data.get('project', {}).get('optional-dependencies', {})
            for group_name, deps in optional_deps.items():
                for dep in deps:
                    parsed = self._parse_requirement_line(dep)
                    if parsed:
                        parsed.metadata['optional_group'] = group_name
                        dependencies.append(parsed)

        except Exception as e:
            self._log(f"Error parsing pyproject.toml: {e}", "error")

        return dependencies

    async def _parse_setup_file(self, file_path: str) -> List[DependencyInfo]:
        """解析setup.py文件"""
        dependencies = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 简单的正则表达式解析install_requires
            install_requires_pattern = r'install_requires\s*=\s*\[(.*?)\]'
            match = re.search(install_requires_pattern, content, re.DOTALL)
            if match:
                requires_str = match.group(1)
                # 提取引号中的内容
                packages = re.findall(r'["\']([^"\']+)["\']', requires_str)
                for pkg in packages:
                    parsed = self._parse_requirement_line(pkg)
                    if parsed:
                        dependencies.append(parsed)

        except Exception as e:
            self._log(f"Error parsing setup.py: {e}", "error")

        return dependencies

    async def _parse_pipfile(self, file_path: str) -> List[DependencyInfo]:
        """解析Pipfile"""
        dependencies = []

        try:
            # 尝试导入toml库
            try:
                import tomllib
            except ImportError:
                try:
                    import tomli as tomllib
                except ImportError:
                    self._log("tomllib/tomli not available, skipping Pipfile parsing", "warning")
                    return dependencies

            with open(file_path, 'rb') as f:
                data = tomllib.load(f)

            # 解析packages
            packages = data.get('packages', {})
            for name, version_spec in packages.items():
                if isinstance(version_spec, str):
                    required_version = version_spec
                elif isinstance(version_spec, dict):
                    required_version = version_spec.get('version')
                else:
                    required_version = None

                dependencies.append(DependencyInfo(
                    name=name,
                    required_version=required_version,
                    dependency_type=DependencyType.PYTHON_PIP,
                    metadata={'pipfile': True}
                ))

        except Exception as e:
            self._log(f"Error parsing Pipfile: {e}", "error")

        return dependencies

    async def _scan_node_dependencies(self, project_path: str) -> List[DependencyInfo]:
        """扫描Node.js依赖"""
        dependencies = []

        # 扫描package.json
        package_json = os.path.join(project_path, "package.json")
        if os.path.exists(package_json):
            deps = await self._parse_package_json(package_json)
            dependencies.extend(deps)

        # 扫描yarn.lock
        yarn_lock = os.path.join(project_path, "yarn.lock")
        if os.path.exists(yarn_lock):
            deps = await self._parse_yarn_lock(yarn_lock)
            dependencies.extend(deps)

        return dependencies

    async def _parse_package_json(self, file_path: str) -> List[DependencyInfo]:
        """解析package.json文件"""
        dependencies = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 解析dependencies
            deps = data.get('dependencies', {})
            for name, version_spec in deps.items():
                dependencies.append(DependencyInfo(
                    name=name,
                    required_version=version_spec,
                    dependency_type=DependencyType.NODE_NPM,
                    metadata={'package_type': 'dependency'}
                ))

            # 解析devDependencies
            dev_deps = data.get('devDependencies', {})
            for name, version_spec in dev_deps.items():
                dependencies.append(DependencyInfo(
                    name=name,
                    required_version=version_spec,
                    dependency_type=DependencyType.NODE_NPM,
                    metadata={'package_type': 'devDependency'}
                ))

            # 解析peerDependencies
            peer_deps = data.get('peerDependencies', {})
            for name, version_spec in peer_deps.items():
                dependencies.append(DependencyInfo(
                    name=name,
                    required_version=version_spec,
                    dependency_type=DependencyType.NODE_NPM,
                    metadata={'package_type': 'peerDependency'}
                ))

        except Exception as e:
            self._log(f"Error parsing package.json: {e}", "error")

        return dependencies

    async def _parse_yarn_lock(self, file_path: str) -> List[DependencyInfo]:
        """解析yarn.lock文件"""
        dependencies = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 简单的正则表达式解析
            package_pattern = r'^"([^@]+@[^"]+)":\s*\n\s*version\s+"([^"]+)"'
            matches = re.findall(package_pattern, content, re.MULTILINE)

            for package_full, version in matches:
                if '@' in package_full:
                    name, version_spec = package_full.rsplit('@', 1)
                else:
                    name = package_full
                    version_spec = version

                dependencies.append(DependencyInfo(
                    name=name,
                    current_version=version,
                    dependency_type=DependencyType.NODE_NPM,
                    installed=True,
                    metadata={'yarn_lock': True}
                ))

        except Exception as e:
            self._log(f"Error parsing yarn.lock: {e}", "error")

        return dependencies

    async def _scan_system_dependencies(self, project_path: str) -> List[DependencyInfo]:
        """扫描系统依赖"""
        dependencies = []

        # 扫描Docker相关
        dockerfile = os.path.join(project_path, "Dockerfile")
        if os.path.exists(dockerfile):
            deps = await self._parse_dockerfile(dockerfile)
            dependencies.extend(deps)

        # 扫描docker-compose.yml
        docker_compose = os.path.join(project_path, "docker-compose.yml")
        if os.path.exists(docker_compose):
            deps = await self._parse_docker_compose(docker_compose)
            dependencies.extend(deps)

        return dependencies

    async def _parse_dockerfile(self, file_path: str) -> List[DependencyInfo]:
        """解析Dockerfile"""
        dependencies = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            for line in lines:
                line = line.strip()
                if line.startswith('FROM '):
                    image = line[5:].strip()
                    dependencies.append(DependencyInfo(
                        name=f"docker_image_{image}",
                        dependency_type=DependencyType.DOCKER,
                        installed=True,
                        metadata={'docker_image': image}
                    ))

        except Exception as e:
            self._log(f"Error parsing Dockerfile: {e}", "error")

        return dependencies

    async def _parse_docker_compose(self, file_path: str) -> List[DependencyInfo]:
        """解析docker-compose.yml"""
        dependencies = []

        try:
            if yaml is not None:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)

                services = data.get('services', {})
                for service_name, service_config in services.items():
                    image = service_config.get('image')
                    if image:
                        dependencies.append(DependencyInfo(
                            name=f"docker_service_{service_name}",
                            dependency_type=DependencyType.DOCKER,
                            installed=True,
                            metadata={'docker_image': image, 'service_name': service_name}
                        ))
            else:
                self._log("yaml library not available, skipping docker-compose.yml parsing", "warning")

        except Exception as e:
            self._log(f"Error parsing docker-compose.yml: {e}", "error")

        return dependencies

    async def _check_installation_status(self, dependencies: List[DependencyInfo]):
        """检查依赖安装状态"""
        loop = asyncio.get_event_loop()
        tasks = []

        for dep in dependencies:
            if dep.dependency_type == DependencyType.PYTHON_PIP:
                task = loop.run_in_executor(
                    self.executor,
                    self._check_python_package,
                    dep
                )
                tasks.append(task)
            elif dep.dependency_type == DependencyType.NODE_NPM:
                task = loop.run_in_executor(
                    self.executor,
                    self._check_node_package,
                    dep
                )
                tasks.append(task)

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    def _check_python_package(self, dep: DependencyInfo):
        """检查Python包安装状态"""
        try:
            import importlib.metadata
            version = importlib.metadata.version(dep.name)
            dep.current_version = version
            dep.installed = True
        except importlib.metadata.PackageNotFoundError:
            dep.installed = False
        except Exception as e:
            self._log(f"Error checking Python package {dep.name}: {e}", "error")
            dep.installed = False

    def _check_node_package(self, dep: DependencyInfo):
        """检查Node.js包安装状态"""
        try:
            # 尝试使用npm list
            result = subprocess.run(
                ['npm', 'list', dep.name, '--depth=0', '--json'],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                data = json.loads(result.stdout)
                dependencies = data.get('dependencies', {})
                if dep.name in dependencies:
                    dep.current_version = dependencies[dep.name].get('version')
                    dep.installed = True
                else:
                    dep.installed = False
            else:
                dep.installed = False

        except FileNotFoundError:
            # npm not available
            dep.installed = False
        except Exception as e:
            self._log(f"Error checking Node.js package {dep.name}: {e}", "error")
            dep.installed = False

    async def _detect_version_conflicts(self, dependencies: List[DependencyInfo]) -> List[VersionConflict]:
        """检测版本冲突"""
        conflicts = []

        # 1. 检查缺失依赖
        for dep in dependencies:
            if not dep.installed:
                conflict = VersionConflict(
                    dependency_name=dep.name,
                    dependency_type=dep.dependency_type,
                    current_version=None,
                    required_version=dep.required_version,
                    conflict_type="missing_dependency",
                    severity=ConflictSeverity.HIGH,
                    description=f"Required dependency '{dep.name}' is not installed",
                    resolution_options=[
                        {
                            "type": "install",
                            "command": self._get_install_command(dep),
                            "description": f"Install {dep.name}"
                        }
                    ]
                )
                conflicts.append(conflict)

        # 2. 检查版本兼容性
        for dep in dependencies:
            if dep.installed and dep.required_version:
                compatibility = self._check_version_compatibility(
                    dep.current_version,
                    dep.required_version
                )
                if not compatibility:
                    severity = self._assess_conflict_severity(dep)
                    conflict = VersionConflict(
                        dependency_name=dep.name,
                        dependency_type=dep.dependency_type,
                        current_version=dep.current_version,
                        required_version=dep.required_version,
                        conflict_type="version_mismatch",
                        severity=severity,
                        description=f"Version conflict: installed {dep.current_version}, required {dep.required_version}",
                        resolution_options=self._generate_version_resolution_options(dep)
                    )
                    conflicts.append(conflict)

        # 3. 检查依赖间的冲突
        inter_conflicts = await self._check_inter_dependency_conflicts(dependencies)
        conflicts.extend(inter_conflicts)

        return conflicts

    def _check_version_compatibility(self, current: str, required: str) -> bool:
        """检查版本兼容性"""
        try:
            # 解析版本要求
            if '>=' in required or '<=' in required or '>' in required or '<' in required:
                # 复杂版本要求
                return self._check_complex_version_requirement(current, required)
            elif '==' in required:
                # 精确版本要求
                required_version = required.split('==')[1].strip()
                return current == required_version
            elif '~=' in required:
                # 兼容版本要求 (~=1.2.3 == >=1.2.3, <1.3.0)
                base_version = required.split('~=')[1].strip()
                return self._check_compatible_version(current, base_version)
            elif '^' in required:
                # 主版本兼容要求 (^1.2.3 == >=1.2.3, <2.0.0)
                base_version = required.split('^')[1].strip()
                return self._check_caret_version(current, base_version)
            else:
                # 简单版本号
                return current.startswith(required)

        except Exception as e:
            self._log(f"Error checking version compatibility: {e}", "error")
            return True  # 默认认为兼容

    def _check_complex_version_requirement(self, current: str, required: str) -> bool:
        """检查复杂版本要求"""
        try:
            # 分割多个条件
            conditions = re.split(r',\s*', required)

            for condition in conditions:
                if not self._evaluate_single_version_condition(current, condition):
                    return False

            return True
        except Exception:
            return False

    def _evaluate_single_version_condition(self, current: str, condition: str) -> bool:
        """评估单个版本条件"""
        operators = ['>=', '<=', '>', '<', '==', '!=']

        for op in operators:
            if condition.startswith(op):
                target_version = condition[len(op):].strip()
                return self._compare_versions(current, target_version, op)

        return False

    def _compare_versions(self, v1: str, v2: str, operator: str) -> bool:
        """比较版本号"""
        try:
            if version is not None:
                version1 = version.parse(v1)
                version2 = version.parse(v2)

                if operator == '>=':
                    return version1 >= version2
                elif operator == '<=':
                    return version1 <= version2
                elif operator == '>':
                    return version1 > version2
                elif operator == '<':
                    return version1 < version2
                elif operator == '==':
                    return version1 == version2
                elif operator == '!=':
                    return version1 != version2
            else:
                # 简单的字符串比较作为后备
                if operator == '==':
                    return v1 == v2
                elif operator == '!=':
                    return v1 != v2
                else:
                    # 对于其他操作符，使用简单的数值比较
                    try:
                        v1_parts = [int(x) for x in v1.split('.')]
                        v2_parts = [int(x) for x in v2.split('.')]

                        # 补齐版本号长度
                        max_len = max(len(v1_parts), len(v2_parts))
                        v1_parts.extend([0] * (max_len - len(v1_parts)))
                        v2_parts.extend([0] * (max_len - len(v2_parts)))

                        if operator == '>=':
                            return v1_parts >= v2_parts
                        elif operator == '<=':
                            return v1_parts <= v2_parts
                        elif operator == '>':
                            return v1_parts > v2_parts
                        elif operator == '<':
                            return v1_parts < v2_parts
                    except:
                        return v1 == v2  # 回退到相等比较

            return False
        except Exception:
            return False

    def _check_compatible_version(self, current: str, base: str) -> bool:
        """检查兼容版本 (~=)"""
        try:
            if version is not None:
                current_ver = version.parse(current)
                base_ver = version.parse(base)

                # ~=1.2.3 表示 >=1.2.3, <1.3.0
                if current_ver >= base_ver:
                    next_major = f"{base_ver.major}.{base_ver.minor + 1}.0"
                    return current_ver < version.parse(next_major)
            else:
                # 简单版本比较
                return self._simple_version_check(current, base, 'compatible')

            return False
        except Exception:
            return False

    def _check_caret_version(self, current: str, base: str) -> bool:
        """检查主版本兼容 (^)"""
        try:
            if version is not None:
                current_ver = version.parse(current)
                base_ver = version.parse(base)

                # ^1.2.3 表示 >=1.2.3, <2.0.0
                if current_ver >= base_ver:
                    next_major = f"{base_ver.major + 1}.0.0"
                    return current_ver < version.parse(next_major)
            else:
                # 简单版本比较
                return self._simple_version_check(current, base, 'caret')

            return False
        except Exception:
            return False

    def _simple_version_check(self, current: str, base: str, check_type: str) -> bool:
        """简单版本检查（当packaging库不可用时）"""
        try:
            current_parts = [int(x) for x in current.split('.')]
            base_parts = [int(x) for x in base.split('.')]

            # 补齐版本号长度
            max_len = max(len(current_parts), len(base_parts))
            current_parts.extend([0] * (max_len - len(current_parts)))
            base_parts.extend([0] * (max_len - len(base_parts)))

            if check_type == 'compatible':
                # ~=1.2.3: >=1.2.3, <1.3.0
                if current_parts >= base_parts:
                    if current_parts[0] == base_parts[0] and current_parts[1] == base_parts[1]:
                        return True
                return False
            elif check_type == 'caret':
                # ^1.2.3: >=1.2.3, <2.0.0
                if current_parts >= base_parts:
                    if current_parts[0] == base_parts[0]:
                        return True
                return False

            return current_parts >= base_parts
        except:
            return False

    def _assess_conflict_severity(self, dep: DependencyInfo) -> ConflictSeverity:
        """评估冲突严重程度"""
        # 基于依赖类型和重要性评估严重程度
        critical_packages = ['django', 'flask', 'express', 'react', 'vue', 'angular']

        if dep.name.lower() in critical_packages:
            return ConflictSeverity.CRITICAL

        # 检查是否是开发依赖
        if dep.metadata.get('package_type') == 'devDependency':
            return ConflictSeverity.LOW

        # 检查版本差异程度
        if dep.current_version and dep.required_version:
            try:
                if version is not None:
                    current_ver = version.parse(dep.current_version)
                    required_ver = version.parse(dep.required_version.split(',')[0].strip('>=<==!~^ '))

                    if current_ver.major != required_ver.major:
                        return ConflictSeverity.HIGH
                    elif current_ver.minor != required_ver.minor:
                        return ConflictSeverity.MEDIUM
                else:
                    # 简单版本比较
                    current_parts = [int(x) for x in dep.current_version.split('.')]
                    required_parts = [int(x) for x in dep.required_version.split(',')[0].strip('>=<==!~^ ').split('.')]

                    # 补齐长度
                    max_len = max(len(current_parts), len(required_parts))
                    current_parts.extend([0] * (max_len - len(current_parts)))
                    required_parts.extend([0] * (max_len - len(required_parts)))

                    if len(current_parts) >= 1 and len(required_parts) >= 1:
                        if current_parts[0] != required_parts[0]:
                            return ConflictSeverity.HIGH
                    if len(current_parts) >= 2 and len(required_parts) >= 2:
                        if current_parts[1] != required_parts[1]:
                            return ConflictSeverity.MEDIUM
            except Exception:
                pass

        return ConflictSeverity.MEDIUM

    def _generate_version_resolution_options(self, dep: DependencyInfo) -> List[Dict[str, Any]]:
        """生成版本解决选项"""
        options = []

        # 升级选项
        if dep.current_version and dep.required_version:
            try:
                required_clean = dep.required_version.split(',')[0].strip('>=<==!~^ ')
                if version is not None:
                    required_ver = version.parse(required_clean)
                    current_ver = version.parse(dep.current_version)

                    if current_ver < required_ver:
                        options.append({
                            "type": "upgrade",
                            "command": self._get_upgrade_command(dep, str(required_ver)),
                            "description": f"Upgrade {dep.name} from {dep.current_version} to {dep.required_version}",
                            "automated": True
                        })
                else:
                    # 简单版本比较
                    if self._compare_versions(dep.current_version, required_clean, '<'):
                        options.append({
                            "type": "upgrade",
                            "command": self._get_upgrade_command(dep, required_clean),
                            "description": f"Upgrade {dep.name} from {dep.current_version} to {dep.required_version}",
                            "automated": True
                        })
            except Exception:
                pass

        # 降级选项
        if dep.current_version and dep.required_version:
            try:
                required_clean = dep.required_version.split(',')[0].strip('>=<==!~^ ')
                if version is not None:
                    required_ver = version.parse(required_clean)
                    current_ver = version.parse(dep.current_version)

                    if current_ver > required_ver:
                        options.append({
                            "type": "downgrade",
                            "command": self._get_downgrade_command(dep, str(required_ver)),
                            "description": f"Downgrade {dep.name} from {dep.current_version} to {dep.required_version}",
                            "automated": True
                        })
                else:
                    # 简单版本比较
                    if self._compare_versions(dep.current_version, required_clean, '>'):
                        options.append({
                            "type": "downgrade",
                            "command": self._get_downgrade_command(dep, required_clean),
                            "description": f"Downgrade {dep.name} from {dep.current_version} to {dep.required_version}",
                            "automated": True
                        })
            except Exception:
                pass

        # 重新安装选项
        options.append({
            "type": "reinstall",
            "command": self._get_reinstall_command(dep),
            "description": f"Reinstall {dep.name} to fix potential corruption",
            "automated": True
        })

        return options

    def _get_install_command(self, dep: DependencyInfo) -> str:
        """获取安装命令"""
        if dep.dependency_type == DependencyType.PYTHON_PIP:
            if dep.required_version:
                return f"pip install {dep.name}{dep.required_version}"
            else:
                return f"pip install {dep.name}"
        elif dep.dependency_type == DependencyType.NODE_NPM:
            if dep.required_version:
                return f"npm install {dep.name}@{dep.required_version}"
            else:
                return f"npm install {dep.name}"

        return f"# Install {dep.name}"

    def _get_upgrade_command(self, dep: DependencyInfo, target_version: str) -> str:
        """获取升级命令"""
        if dep.dependency_type == DependencyType.PYTHON_PIP:
            return f"pip install --upgrade {dep.name}=={target_version}"
        elif dep.dependency_type == DependencyType.NODE_NPM:
            return f"npm install {dep.name}@{target_version}"

        return f"# Upgrade {dep.name} to {target_version}"

    def _get_downgrade_command(self, dep: DependencyInfo, target_version: str) -> str:
        """获取降级命令"""
        if dep.dependency_type == DependencyType.PYTHON_PIP:
            return f"pip install {dep.name}=={target_version}"
        elif dep.dependency_type == DependencyType.NODE_NPM:
            return f"npm install {dep.name}@{target_version}"

        return f"# Downgrade {dep.name} to {target_version}"

    def _get_reinstall_command(self, dep: DependencyInfo) -> str:
        """获取重新安装命令"""
        if dep.dependency_type == DependencyType.PYTHON_PIP:
            version_spec = f"=={dep.current_version}" if dep.current_version else ""
            return f"pip uninstall {dep.name} -y && pip install {dep.name}{version_spec}"
        elif dep.dependency_type == DependencyType.NODE_NPM:
            return f"npm uninstall {dep.name} && npm install {dep.name}"

        return f"# Reinstall {dep.name}"

    async def _check_inter_dependency_conflicts(self, dependencies: List[DependencyInfo]) -> List[VersionConflict]:
        """检查依赖间的冲突"""
        conflicts = []

        # 检查Python包的已知冲突
        python_conflicts = await self._check_python_package_conflicts(dependencies)
        conflicts.extend(python_conflicts)

        # 检查Node.js包的已知冲突
        node_conflicts = await self._check_node_package_conflicts(dependencies)
        conflicts.extend(node_conflicts)

        return conflicts

    async def _check_python_package_conflicts(self, dependencies: List[DependencyInfo]) -> List[VersionConflict]:
        """检查Python包冲突"""
        conflicts = []

        # 已知的Python包冲突
        known_conflicts = {
            ('tensorflow', 'torch'): 'TensorFlow and PyTorch may have conflicting CUDA requirements',
            ('django', 'flask'): 'Django and Flask are competing web frameworks',
            ('pytest', 'nose'): 'pytest and nose are competing testing frameworks',
            ('sqlalchemy', 'django'): 'SQLAlchemy may conflict with Django ORM',
        }

        installed_packages = [dep for dep in dependencies if dep.installed and dep.dependency_type == DependencyType.PYTHON_PIP]
        package_names = [dep.name.lower() for dep in installed_packages]

        for (pkg1, pkg2), description in known_conflicts.items():
            if pkg1 in package_names and pkg2 in package_names:
                conflict = VersionConflict(
                    dependency_name=f"{pkg1}_vs_{pkg2}",
                    dependency_type=DependencyType.PYTHON_PIP,
                    current_version=None,
                    required_version=None,
                    conflict_type="package_conflict",
                    severity=ConflictSeverity.MEDIUM,
                    description=description,
                    affected_dependencies=[pkg1, pkg2],
                    resolution_options=[
                        {
                            "type": "remove_conflict",
                            "command": f"# Choose either {pkg1} or {pkg2}, not both",
                            "description": f"Remove either {pkg1} or {pkg2} to resolve conflict"
                        }
                    ]
                )
                conflicts.append(conflict)

        return conflicts

    async def _check_node_package_conflicts(self, dependencies: List[DependencyInfo]) -> List[VersionConflict]:
        """检查Node.js包冲突"""
        conflicts = []

        # 已知的Node.js包冲突
        known_conflicts = {
            ('react', 'vue'): 'React and Vue.js are competing frameworks',
            ('webpack', 'vite'): 'webpack and Vite are competing build tools',
            ('mobx', 'redux'): 'MobX and Redux are competing state management solutions',
        }

        installed_packages = [dep for dep in dependencies if dep.installed and dep.dependency_type == DependencyType.NODE_NPM]
        package_names = [dep.name.lower() for dep in installed_packages]

        for (pkg1, pkg2), description in known_conflicts.items():
            if pkg1 in package_names and pkg2 in package_names:
                conflict = VersionConflict(
                    dependency_name=f"{pkg1}_vs_{pkg2}",
                    dependency_type=DependencyType.NODE_NPM,
                    current_version=None,
                    required_version=None,
                    conflict_type="package_conflict",
                    severity=ConflictSeverity.MEDIUM,
                    description=description,
                    affected_dependencies=[pkg1, pkg2],
                    resolution_options=[
                        {
                            "type": "remove_conflict",
                            "command": f"# Choose either {pkg1} or {pkg2}, not both",
                            "description": f"Remove either {pkg1} or {pkg2} to resolve conflict"
                        }
                    ]
                )
                conflicts.append(conflict)

        return conflicts

    async def _generate_resolutions(self, conflicts: List[VersionConflict]) -> List[DependencyResolution]:
        """生成解决方案"""
        resolutions = []

        for conflict in conflicts:
            # 选择最佳解决方案
            best_option = self._select_best_resolution_option(conflict)

            if best_option:
                resolution = DependencyResolution(
                    conflict=conflict,
                    resolution_type=ResolutionType(best_option.get('type', 'upgrade')),
                    target_version=best_option.get('target_version'),
                    command=best_option.get('command', ''),
                    description=best_option.get('description', ''),
                    automated=best_option.get('automated', False)
                )
                resolutions.append(resolution)

        return resolutions

    def _select_best_resolution_option(self, conflict: VersionConflict) -> Optional[Dict[str, Any]]:
        """选择最佳解决方案选项"""
        options = conflict.resolution_options

        if not options:
            return None

        # 优先级：自动化 > 升级 > 降级 > 重装
        priority_order = ['upgrade', 'downgrade', 'reinstall', 'install', 'remove_conflict']

        for priority in priority_order:
            for option in options:
                if option.get('type') == priority:
                    return option

        return options[0]  # 返回第一个选项

    def _generate_recommendations(self, result: DependencyAnalysisResult) -> List[str]:
        """生成建议"""
        recommendations = []

        # 基于冲突数量生成建议
        if result.conflicting_dependencies > 0:
            recommendations.append(f"发现 {result.conflicting_dependencies} 个依赖冲突，建议优先解决高严重程度冲突")

        if result.missing_dependencies > 0:
            recommendations.append(f"发现 {result.missing_dependencies} 个缺失依赖，建议安装这些依赖")

        # 基于冲突类型生成建议
        conflict_types = set(conflict.conflict_type for conflict in result.conflicts)

        if 'missing_dependency' in conflict_types:
            recommendations.append("运行依赖安装命令来安装缺失的包")

        if 'version_mismatch' in conflict_types:
            recommendations.append("考虑使用虚拟环境来管理不同项目的依赖版本")

        if 'package_conflict' in conflict_types:
            recommendations.append("审查项目架构，避免使用功能重复的包")

        # 生成最佳实践建议
        if result.total_dependencies > 50:
            recommendations.append("项目依赖较多，建议定期审查和清理不必要的依赖")

        recommendations.append("建议使用依赖锁定文件（requirements.txt, package-lock.json等）来确保可重现的构建")
        recommendations.append("定期更新依赖到最新稳定版本以获得安全修复和性能改进")

        return recommendations

    def _generate_summary(self, result: DependencyAnalysisResult) -> Dict[str, Any]:
        """生成摘要"""
        summary = {
            'analysis_timestamp': result.timestamp,
            'dependency_health': 'healthy' if result.conflicting_dependencies == 0 else 'needs_attention',
            'total_packages': result.total_dependencies,
            'installed_packages': result.total_dependencies - result.missing_dependencies,
            'compatible_packages': result.compatible_dependencies,
            'conflicting_packages': result.conflicting_dependencies,
            'missing_packages': result.missing_dependencies,
            'conflict_severity_breakdown': {
                'critical': len([c for c in result.conflicts if c.severity == ConflictSeverity.CRITICAL]),
                'high': len([c for c in result.conflicts if c.severity == ConflictSeverity.HIGH]),
                'medium': len([c for c in result.conflicts if c.severity == ConflictSeverity.MEDIUM]),
                'low': len([c for c in result.conflicts if c.severity == ConflictSeverity.LOW])
            },
            'dependency_types': {
                'python_pip': len([r for r in result.resolutions if r.conflict.dependency_type == DependencyType.PYTHON_PIP]),
                'node_npm': len([r for r in result.resolutions if r.conflict.dependency_type == DependencyType.NODE_NPM]),
                'docker': len([r for r in result.resolutions if r.conflict.dependency_type == DependencyType.DOCKER])
            },
            'automated_resolutions': len([r for r in result.resolutions if r.automated])
        }

        return summary

    async def apply_resolution(self, resolution: DependencyResolution, auto_confirm: bool = False) -> bool:
        """应用解决方案"""
        if not auto_confirm:
            self._log(f"Would execute: {resolution.command}")
            return True

        try:
            self._log(f"Executing resolution: {resolution.description}")

            # 执行命令
            result = subprocess.run(
                resolution.command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=300
            )

            if result.returncode == 0:
                self._log(f"Resolution applied successfully: {resolution.description}")
                return True
            else:
                self._log(f"Resolution failed: {result.stderr}", "error")
                return False

        except subprocess.TimeoutExpired:
            self._log(f"Resolution timed out: {resolution.command}", "error")
            return False
        except Exception as e:
            self._log(f"Error applying resolution: {e}", "error")
            return False

    async def generate_dependency_report(self, project_path: str = None, output_file: str = None) -> str:
        """生成依赖报告"""
        result = await self.analyze_dependencies(project_path)

        # 生成报告内容
        report_lines = [
            "# 依赖冲突检测报告",
            f"生成时间: {result.timestamp}",
            f"项目路径: {project_path or os.getcwd()}",
            "",
            "## 摘要",
            f"- 总依赖数: {result.total_dependencies}",
            f"- 兼容依赖: {result.compatible_dependencies}",
            f"- 冲突依赖: {result.conflicting_dependencies}",
            f"- 缺失依赖: {result.missing_dependencies}",
            f"- 依赖健康度: {result.summary.get('dependency_health', 'unknown')}",
            "",
            "## 冲突详情"
        ]

        for conflict in result.conflicts:
            report_lines.extend([
                f"### {conflict.dependency_name}",
                f"- 类型: {conflict.conflict_type}",
                f"- 严重程度: {conflict.severity.value}",
                f"- 当前版本: {conflict.current_version or '未安装'}",
                f"- 要求版本: {conflict.required_version or '未知'}",
                f"- 描述: {conflict.description}",
                ""
            ])

        report_lines.extend([
            "## 解决方案",
            ""
        ])

        for resolution in result.resolutions:
            report_lines.extend([
                f"### {resolution.conflict.dependency_name}",
                f"- 操作: {resolution.resolution_type.value}",
                f"- 命令: `{resolution.command}`",
                f"- 描述: {resolution.description}",
                f"- 自动化: {'是' if resolution.automated else '否'}",
                ""
            ])

        report_lines.extend([
            "## 建议",
            ""
        ])

        for i, rec in enumerate(result.recommendations, 1):
            report_lines.append(f"{i}. {rec}")

        report_content = "\n".join(report_lines)

        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(report_content)
            self._log(f"Dependency report saved to: {output_file}")

        return report_content

    async def __aenter__(self):
        """异步上下文管理器入口"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        if self.executor:
            self.executor.shutdown(wait=False)


# 便利函数
async def quick_dependency_check(project_path: str = None) -> DependencyAnalysisResult:
    """快速依赖检查"""
    async with DependencyConflictDetector() as detector:
        return await detector.analyze_dependencies(project_path)


async def fix_common_issues(project_path: str = None, auto_confirm: bool = False) -> List[bool]:
    """修复常见问题"""
    async with DependencyConflictDetector() as detector:
        result = await detector.analyze_dependencies(project_path)

        results = []
        for resolution in result.resolutions:
            if resolution.automated and resolution.conflict.severity in [ConflictSeverity.HIGH, ConflictSeverity.CRITICAL]:
                success = await detector.apply_resolution(resolution, auto_confirm)
                results.append(success)

        return results