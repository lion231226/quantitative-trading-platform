"""
依赖版本冲突解决器

This module provides comprehensive version conflict detection and resolution
capabilities including semantic version analysis, compatibility checking,
and automated conflict resolution for the one-click launcher.
"""

import re
from datetime import datetime
import json
from typing import Dict, List, Optional, Tuple, Set, Any, Union
from dataclasses import dataclass, field
from enum import Enum

# 尝试导入 semantic_version，如果没有则使用简化版本
try:
    from semantic_version import Version, SimpleSpec
except ImportError:
    # 简化的版本实现
    class Version:
        def __init__(self, version_str: str):
            parts = version_str.split('.')
            self.major = int(parts[0]) if len(parts) > 0 and parts[0].isdigit() else 0
            self.minor = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
            self.patch = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 0

        def __str__(self):
            return f"{self.major}.{self.minor}.{self.patch}"

        def __lt__(self, other):
            if self.major != other.major:
                return self.major < other.major
            if self.minor != other.minor:
                return self.minor < other.minor
            return self.patch < other.patch

        def __le__(self, other):
            return self < other or self == other

        def __eq__(self, other):
            return (self.major == other.major and
                    self.minor == other.minor and
                    self.patch == other.patch)

        def __gt__(self, other):
            return not self <= other

        def __ge__(self, other):
            return not self < other

    class SimpleSpec:
        def __init__(self, spec_str: str):
            self.spec_str = spec_str

        def __contains__(self, version: Version) -> bool:
            # 简化的版本匹配
            if "==" in self.spec_str:
                expected = self.spec_str.replace("==", "").strip()
                return str(version) == expected
            return True

from utils.logger import get_logger
from core.dependency_analyzer import ProjectDependency, DependencyConflict

logger = get_logger(__name__)


class ConflictSeverity(Enum):
    """冲突严重程度"""
    ERROR = "error"        # 严重冲突，必须解决
    WARNING = "warning"    # 警告，建议解决
    INFO = "info"         # 信息，可选解决


class ResolutionStrategy(Enum):
    """解决策略"""
    LATEST = "latest"           # 使用最新版本
    MINIMUM = "minimum"         # 使用最低兼容版本
    MAINTAIN = "maintain"       # 保持现有版本
    COMPATIBLE = "compatible"   # 选择兼容版本
    MANUAL = "manual"           # 手动选择


@dataclass
class VersionConstraint:
    """版本约束"""
    raw_spec: str
    spec_obj: Optional[SimpleSpec] = None
    is_range: bool = False
    min_version: Optional[Version] = None
    max_version: Optional[Version] = None

    def __post_init__(self):
        """解析版本约束"""
        if self.raw_spec:
            try:
                self.spec_obj = SimpleSpec(self.raw_spec)
                self._parse_range()
            except Exception as e:
                logger.debug(f"解析版本约束失败 {self.raw_spec}: {e}")

    def _parse_range(self):
        """解析版本范围"""
        if not self.raw_spec:
            return

        # 解析常见的版本范围格式
        range_patterns = [
            (r'>=([\d.]+)\s*<([\d.]+)', lambda m: (Version(m.group(1)), Version(m.group(2)))),
            (r'>([\d.]+)\s*<([\d.]+)', lambda m: (Version(m.group(1)), Version(m.group(2)))),
            (r'>=([\d.]+)', lambda m: (Version(m.group(1)), None)),
            (r'>([\d.]+)', lambda m: (Version(m.group(1)), None)),
            (r'<=[\d.]+)', lambda m: (None, Version(m.group(1)))),
            (r'<([\d.]+)', lambda m: (None, Version(m.group(1)))),
        ]

        for pattern, parser in range_patterns:
            match = re.search(pattern, self.raw_spec)
            if match:
                min_v, max_v = parser(match)
                self.min_version = min_v
                self.max_version = max_v
                self.is_range = True
                break


@dataclass
class ConflictResolution:
    """冲突解决方案"""
    dependency_name: str
    ecosystem: str
    strategy: ResolutionStrategy
    resolved_version: str
    confidence: float  # 0.0 - 1.0
    explanation: str
    affected_files: List[str]
    alternative_solutions: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class VersionCompatibility:
    """版本兼容性信息"""
    version1: str
    version2: str
    is_compatible: bool
    compatibility_score: float  # 0.0 - 1.0
    breaking_changes: List[str] = field(default_factory=list)
    upgrade_path: List[str] = field(default_factory=list)


class VersionConflictResolver:
    """
    版本冲突解决器

    功能特性：
    - 语义化版本分析
    - 兼容性检查
    - 自动冲突解决
    - 解决方案生成
    - 升级路径规划
    """

    # 版本兼容性规则
    COMPATIBILITY_RULES = {
        # Python: 主版本不兼容，次版本向后兼容
        "python": {
            "major_breaking": True,
            "minor_breaking": False,
            "patch_breaking": False,
            "prerelease_breaking": True
        },
        # Node.js: 遵循语义化版本
        "nodejs": {
            "major_breaking": True,
            "minor_breaking": False,
            "patch_breaking": False,
            "prerelease_breaking": True
        },
        # 数据库: 主版本通常不兼容
        "database": {
            "major_breaking": True,
            "minor_breaking": True,  # 数据库次版本可能不兼容
            "patch_breaking": False,
            "prerelease_breaking": True
        }
    }

    # 常见包的兼容性信息
    KNOWN_COMPATIBILITY = {
        "fastapi": {
            "0.100.0": {"compatible_with": ">=0.100.0,<1.0.0"},
            "0.104.0": {"compatible_with": ">=0.104.0,<1.0.0"},
        },
        "react": {
            "17.0.0": {"compatible_with": ">=17.0.0,<18.0.0"},
            "18.0.0": {"compatible_with": ">=18.0.0,<19.0.0"},
        },
        "next": {
            "13.0.0": {"compatible_with": ">=13.0.0,<14.0.0"},
            "14.0.0": {"compatible_with": ">=14.0.0,<15.0.0"},
        }
    }

    def __init__(self):
        """初始化冲突解决器"""
        self.logger = get_logger(self.__class__.__name__)
        self.resolution_history: List[ConflictResolution] = []

    def detect_conflicts(self, dependencies: List[ProjectDependency]) -> List[DependencyConflict]:
        """
        检测版本冲突

        Args:
            dependencies: 依赖列表

        Returns:
            检测到的冲突列表
        """
        self.logger.info("开始检测版本冲突...")

        conflicts = []

        # 1. 检测同一依赖的多个版本规格
        conflicts.extend(self._detect_version_spec_conflicts(dependencies))

        # 2. 检测生态系统冲突
        conflicts.extend(self._detect_ecosystem_conflicts(dependencies))

        # 3. 检测已知的不兼容组合
        conflicts.extend(self._detect_known_incompatibilities(dependencies))

        # 4. 检测版本约束冲突
        conflicts.extend(self._detect_constraint_conflicts(dependencies))

        self.logger.info(f"冲突检测完成，发现 {len(conflicts)} 个冲突")
        return conflicts

    def _detect_version_spec_conflicts(self, dependencies: List[ProjectDependency]) -> List[DependencyConflict]:
        """检测版本规格冲突"""
        conflicts = []

        # 按生态系统和名称分组
        dep_groups = {}
        for dep in dependencies:
            key = f"{dep.ecosystem}:{dep.name}"
            dep_groups.setdefault(key, []).append(dep)

        for dep_key, group in dep_groups.items():
            if len(group) <= 1:
                continue

            ecosystem, name = dep_key.split(':', 1)

            # 收集版本规格
            version_specs = []
            for dep in group:
                if dep.version_spec:
                    version_specs.append((dep.version_spec, dep.source_file))

            if len(version_specs) > 1:
                # 检查规格是否冲突
                unique_specs = list(set(spec[0] for spec in version_specs))

                if len(unique_specs) > 1:
                    # 尝试解析和比较版本规格
                    constraints = []
                    for spec, source_file in version_specs:
                        constraint = VersionConstraint(raw_spec=spec)
                        constraints.append((constraint, source_file))

                    # 检查约束是否可以同时满足
                    if not self._are_constraints_compatible(constraints):
                        severity = self._determine_conflict_severity(name, ecosystem, constraints)

                        conflict = DependencyConflict(
                            dependency_name=name,
                            ecosystem=ecosystem,
                            conflicts=[(spec, source) for spec, source in version_specs],
                            severity=severity.value,
                            description=f"{name} 的版本规格冲突: {', '.join(unique_specs)}",
                            suggested_resolution=self._suggest_resolution(name, ecosystem, constraints)
                        )
                        conflicts.append(conflict)

        return conflicts

    def _detect_ecosystem_conflicts(self, dependencies: List[ProjectDependency]) -> List[DependencyConflict]:
        """检测生态系统冲突"""
        conflicts = []

        # 检查 Python/Node.js 版本要求冲突
        python_constraints = []
        nodejs_constraints = []

        for dep in dependencies:
            if dep.name.lower() == "python":
                if dep.version_spec:
                    python_constraints.append((dep.version_spec, dep.source_file))
            elif dep.name.lower() == "node":
                if dep.version_spec:
                    nodejs_constraints.append((dep.version_spec, dep.source_file))

        # 检查 Python 版本冲突
        if len(python_constraints) > 1:
            unique_python_specs = list(set(spec[0] for spec in python_constraints))
            if len(unique_python_specs) > 1:
                conflict = DependencyConflict(
                    dependency_name="python",
                    ecosystem="system",
                    conflicts=python_constraints,
                    severity="error",
                    description=f"Python 版本要求冲突: {', '.join(unique_python_specs)}",
                    suggested_resolution="统一 Python 版本要求"
                )
                conflicts.append(conflict)

        # 检查 Node.js 版本冲突
        if len(nodejs_constraints) > 1:
            unique_nodejs_specs = list(set(spec[0] for spec in nodejs_constraints))
            if len(unique_nodejs_specs) > 1:
                conflict = DependencyConflict(
                    dependency_name="node",
                    ecosystem="system",
                    conflicts=nodejs_constraints,
                    severity="error",
                    description=f"Node.js 版本要求冲突: {', '.join(unique_nodejs_specs)}",
                    suggested_resolution="统一 Node.js 版本要求"
                )
                conflicts.append(conflict)

        return conflicts

    def _detect_known_incompatibilities(self, dependencies: List[ProjectDependency]) -> List[DependencyConflict]:
        """检测已知的不兼容组合"""
        conflicts = []

        # 检查 React/Next.js 版本兼容性
        react_version = None
        next_version = None

        for dep in dependencies:
            if dep.name == "react" and dep.version_spec:
                react_version = dep.version_spec
            elif dep.name == "next" and dep.version_spec:
                next_version = dep.version_spec

        if react_version and next_version:
            # 检查 React 18 和 Next.js <13 的兼容性问题
            if "18" in react_version and any(v in next_version for v in ["12", "11", "10"]):
                conflict = DependencyConflict(
                    dependency_name="react-nextjs",
                    ecosystem="nodejs",
                    conflicts=[
                        (f"react {react_version}", "package.json"),
                        (f"next {next_version}", "package.json")
                    ],
                    severity="warning",
                    description="React 18 需要 Next.js >=13",
                    suggested_resolution="升级 Next.js 到 13+ 或降级 React 到 17"
                )
                conflicts.append(conflict)

        return conflicts

    def _detect_constraint_conflicts(self, dependencies: List[ProjectDependency]) -> List[DependencyConflict]:
        """检测版本约束冲突"""
        conflicts = []

        for dep in dependencies:
            if not dep.version_spec:
                continue

            # 检查不合理的版本约束
            if self._is_unreasonable_constraint(dep.version_spec):
                conflict = DependencyConflict(
                    dependency_name=dep.name,
                    ecosystem=dep.ecosystem,
                    conflicts=[(dep.version_spec, dep.source_file)],
                    severity="warning",
                    description=f"不合理的版本约束: {dep.version_spec}",
                    suggested_resolution="检查并修正版本约束格式"
                )
                conflicts.append(conflict)

        return conflicts

    def _are_constraints_compatible(self, constraints: List[Tuple[VersionConstraint, str]]) -> bool:
        """检查版本约束是否兼容"""
        if len(constraints) <= 1:
            return True

        # 尝试找到同时满足所有约束的版本
        all_specs = []
        for constraint, _ in constraints:
            if constraint.spec_obj:
                all_specs.append(constraint.spec_obj)

        if not all_specs:
            return True  # 无法解析的约束，假定兼容

        # 这里简化处理，实际应该更复杂的交集计算
        # 对于多个约束，检查是否有明显的冲突
        for i, (constraint1, _) in enumerate(constraints):
            for constraint2, _ in constraints[i+1:]:
                if self._constraints_conflict(constraint1, constraint2):
                    return False

        return True

    def _constraints_conflict(self, constraint1: VersionConstraint, constraint2: VersionConstraint) -> bool:
        """检查两个约束是否冲突"""
        if not constraint1.spec_obj or not constraint2.spec_obj:
            return False

        # 简化的冲突检测
        # 检查是否有一个明确的版本要求冲突
        if constraint1.is_range and constraint2.is_range:
            # 检查范围是否重叠
            return not self._ranges_overlap(constraint1, constraint2)
        elif constraint1.is_range:
            # 检查范围是否包含另一个约束的版本
            return False  # 简化处理
        elif constraint2.is_range:
            return False  # 简化处理
        else:
            # 检查具体版本是否相同
            return constraint1.raw_spec != constraint2.raw_spec

    def _ranges_overlap(self, range1: VersionConstraint, range2: VersionConstraint) -> bool:
        """检查两个版本范围是否重叠"""
        if not range1.is_range or not range2.is_range:
            return False

        # 简化的范围重叠检查
        min1 = range1.min_version
        max1 = range1.max_version
        min2 = range2.min_version
        max2 = range2.max_version

        if min1 and max2 and min1 > max2:
            return False
        if min2 and max1 and min2 > max1:
            return False

        return True

    def _determine_conflict_severity(self, name: str, ecosystem: str, constraints: List[Tuple[VersionConstraint, str]]) -> ConflictSeverity:
        """确定冲突严重程度"""
        # 系统依赖冲突最严重
        if ecosystem == "system":
            return ConflictSeverity.ERROR

        # 检查是否是主要依赖
        critical_deps = ["react", "next", "fastapi", "django", "flask"]
        if name.lower() in critical_deps:
            return ConflictSeverity.ERROR

        # 检查约束差异程度
        versions = []
        for constraint, _ in constraints:
            if constraint.raw_spec:
                # 提取版本号
                version_match = re.search(r'(\d+\.\d+)', constraint.raw_spec)
                if version_match:
                    versions.append(version_match.group(1))

        if versions:
            # 检查主版本是否不同
            major_versions = set(v.split('.')[0] for v in versions)
            if len(major_versions) > 1:
                return ConflictSeverity.ERROR

        return ConflictSeverity.WARNING

    def _suggest_resolution(self, name: str, ecosystem: str, constraints: List[Tuple[VersionConstraint, str]]) -> str:
        """建议解决方案"""
        if not constraints:
            return "无法提供解决建议"

        # 收集所有版本约束
        versions = []
        for constraint, _ in constraints:
            if constraint.raw_spec:
                # 尝试提取版本号
                version_match = re.search(r'(\d+\.\d+\.\d+)', constraint.raw_spec)
                if version_match:
                    versions.append(Version(version_match.group(1)))

        if versions:
            # 建议使用最新版本
            latest_version = max(versions)
            return f"建议使用版本 {latest_version}"

        return "请手动检查并统一版本规格"

    def _is_unreasonable_constraint(self, version_spec: str) -> bool:
        """检查是否是不合理的版本约束"""
        # 检查明显不合理的约束
        unreasonable_patterns = [
            r'>\d+\.\d+\.\d+ <\d+\.\d+\.\d+',  # 范围约束格式错误
            r'==\d+\.\d+\.\d+.*!=\d+\.\d+\.\d+',  # 同时要求等于和不等于
            r'<\d+\.\d+\.\d+ >\d+\.\d+\.\d+',  # 范围方向错误
        ]

        for pattern in unreasonable_patterns:
            if re.search(pattern, version_spec):
                return True

        return False

    def resolve_conflicts(self, conflicts: List[DependencyConflict], strategy: ResolutionStrategy = ResolutionStrategy.LATEST) -> List[ConflictResolution]:
        """
        解决冲突

        Args:
            conflicts: 冲突列表
            strategy: 解决策略

        Returns:
            解决方案列表
        """
        self.logger.info(f"开始解决 {len(conflicts)} 个冲突，策略: {strategy.value}")

        resolutions = []

        for conflict in conflicts:
            try:
                resolution = self._resolve_single_conflict(conflict, strategy)
                if resolution:
                    resolutions.append(resolution)
                    self.resolution_history.append(resolution)
            except Exception as e:
                self.logger.error(f"解决冲突 {conflict.dependency_name} 时出错: {e}")

        self.logger.info(f"冲突解决完成，生成 {len(resolutions)} 个解决方案")
        return resolutions

    def _resolve_single_conflict(self, conflict: DependencyConflict, strategy: ResolutionStrategy) -> Optional[ConflictResolution]:
        """解决单个冲突"""
        if not conflict.conflicts:
            return None

        # 收集版本信息
        versions = []
        for version_spec, source_file in conflict.conflicts:
            version_match = re.search(r'(\d+\.\d+\.\d+)', version_spec)
            if version_match:
                try:
                    version = Version(version_match.group(1))
                    versions.append((version, version_spec, source_file))
                except Exception:
                    continue

        if not versions:
            return None

        # 根据策略选择版本
        if strategy == ResolutionStrategy.LATEST:
            resolved_version = str(max(v[0] for v in versions))
            confidence = 0.8
            explanation = f"选择最新版本 {resolved_version}"
        elif strategy == ResolutionStrategy.MINIMUM:
            resolved_version = str(min(v[0] for v in versions))
            confidence = 0.7
            explanation = f"选择最低兼容版本 {resolved_version}"
        elif strategy == ResolutionStrategy.COMPATIBLE:
            # 选择最兼容的版本
            resolved_version = self._find_most_compatible_version(versions)
            confidence = 0.9
            explanation = f"选择最兼容版本 {resolved_version}"
        else:
            # MAINTAIN 或其他策略
            resolved_version = versions[0][1]  # 保持第一个
            confidence = 0.6
            explanation = f"保持现有版本 {resolved_version}"

        return ConflictResolution(
            dependency_name=conflict.dependency_name,
            ecosystem=conflict.ecosystem,
            strategy=strategy,
            resolved_version=resolved_version,
            confidence=confidence,
            explanation=explanation,
            affected_files=list(set(source_file for _, _, source_file in versions)),
            alternative_solutions=self._generate_alternative_solutions(versions)
        )

    def _find_most_compatible_version(self, versions: List[Tuple[Version, str, str]]) -> str:
        """找到最兼容的版本"""
        if not versions:
            return ""

        # 简化处理：选择中位数版本
        sorted_versions = sorted(v[0] for v in versions)
        if len(sorted_versions) % 2 == 1:
            return str(sorted_versions[len(sorted_versions) // 2])
        else:
            # 偶数个版本，选择较小的一个
            return str(sorted_versions[len(sorted_versions) // 2 - 1])

    def _generate_alternative_solutions(self, versions: List[Tuple[Version, str, str]]) -> List[Dict[str, Any]]:
        """生成替代解决方案"""
        alternatives = []

        if len(versions) > 1:
            # 按版本排序
            sorted_versions = sorted(versions, key=lambda x: x[0])

            # 生成几个选项
            for i in range(min(3, len(sorted_versions))):
                version, version_spec, source_file = sorted_versions[i]
                alternatives.append({
                    "version": str(version),
                    "spec": version_spec,
                    "source_file": source_file,
                    "confidence": 0.8 - (i * 0.2),
                    "description": f"使用版本 {version} ({version_spec})"
                })

        return alternatives

    def generate_lock_file(self, dependencies: List[ProjectDependency], resolved_versions: Dict[str, str]) -> str:
        """
        生成依赖锁定文件

        Args:
            dependencies: 依赖列表
            resolved_versions: 解决的版本映射

        Returns:
            锁定文件内容
        """
        lock_content = {
            "version": 1,
            "generated_at": str(datetime.now()),
            "dependencies": {}
        }

        for dep in dependencies:
            key = f"{dep.ecosystem}:{dep.name}"
            version = resolved_versions.get(key, dep.version_spec)

            if version:
                lock_content["dependencies"][key] = {
                    "version": version,
                    "ecosystem": dep.ecosystem,
                    "name": dep.name,
                    "source_file": dep.source_file,
                    "is_dev": dep.is_dev_dependency
                }

        return json.dumps(lock_content, indent=2, ensure_ascii=False)

    def check_compatibility(self, version1: str, version2: str, ecosystem: str) -> VersionCompatibility:
        """
        检查两个版本的兼容性

        Args:
            version1: 版本1
            version2: 版本2
            ecosystem: 生态系统

        Returns:
            兼容性信息
        """
        try:
            v1 = Version(version1)
            v2 = Version(version2)
        except Exception as e:
            return VersionCompatibility(
                version1=version1,
                version2=version2,
                is_compatible=False,
                compatibility_score=0.0,
                breaking_changes=[f"版本格式错误: {e}"]
            )

        rules = self.COMPATIBILITY_RULES.get(ecosystem, self.COMPATIBILITY_RULES["nodejs"])

        is_compatible = True
        compatibility_score = 1.0
        breaking_changes = []

        # 检查主版本
        if rules["major_breaking"] and v1.major != v2.major:
            is_compatible = False
            compatibility_score = 0.2
            breaking_changes.append(f"主版本不兼容: {v1.major} vs {v2.major}")

        # 检查次版本
        if is_compatible and rules["minor_breaking"] and v1.minor != v2.minor:
            compatibility_score = 0.7
            breaking_changes.append(f"次版本可能不兼容: {v1.minor} vs {v2.minor}")

        # 计算升级路径
        upgrade_path = self._calculate_upgrade_path(v1, v2)

        return VersionCompatibility(
            version1=version1,
            version2=version2,
            is_compatible=is_compatible,
            compatibility_score=compatibility_score,
            breaking_changes=breaking_changes,
            upgrade_path=upgrade_path
        )

    def _calculate_upgrade_path(self, from_version: Version, to_version: Version) -> List[str]:
        """计算升级路径"""
        if from_version == to_version:
            return []

        path = []
        current = from_version

        # 简化的升级路径计算
        while current < to_version:
            if current.major < to_version.major:
                # 主版本升级
                next_minor = 0
                next_patch = 0
                next_major = current.major + 1
                current = Version(f"{next_major}.{next_minor}.{next_patch}")
            elif current.minor < to_version.minor:
                # 次版本升级
                next_minor = current.minor + 1
                next_patch = 0
                current = Version(f"{current.major}.{next_minor}.{next_patch}")
            elif current.patch < to_version.patch:
                # 补丁版本升级
                next_patch = current.patch + 1
                current = Version(f"{current.major}.{current.minor}.{next_patch}")
            else:
                break

            path.append(str(current))
            if current >= to_version:
                break

        return path

    def get_resolution_summary(self, resolutions: List[ConflictResolution]) -> Dict[str, Any]:
        """获取解决摘要"""
        if not resolutions:
            return {
                "total_resolutions": 0,
                "successful_resolutions": 0,
                "strategies_used": [],
                "average_confidence": 0.0
            }

        strategies_used = list(set(r.strategy.value for r in resolutions))
        avg_confidence = sum(r.confidence for r in resolutions) / len(resolutions)

        return {
            "total_resolutions": len(resolutions),
            "successful_resolutions": len([r for r in resolutions if r.confidence > 0.5]),
            "strategies_used": strategies_used,
            "average_confidence": avg_confidence,
            "ecosystems_resolved": list(set(r.ecosystem for r in resolutions)),
            "high_confidence_resolutions": len([r for r in resolutions if r.confidence > 0.8])
        }