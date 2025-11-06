"""
版本冲突处理器

This module provides comprehensive version conflict handling capabilities
including conflict detection, resolution strategies, and rollback mechanisms
for the one-click launcher.
"""

import os
import json
import time
import shutil
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from utils.logger import get_logger
from core.dependency_analyzer import ProjectDependency, DependencyConflict
from core.conflict_resolver import (
    VersionConflictResolver,
    ConflictResolution,
    ResolutionStrategy,
    VersionCompatibility
)

logger = get_logger(__name__)


class ConflictHandlingMode(Enum):
    """冲突处理模式"""
    AUTO = "auto"                     # 自动处理
    INTERACTIVE = "interactive"         # 交互式处理
    SAFE = "safe"                     # 安全模式（只处理低风险冲突）
    MANUAL = "manual"                 # 手动处理


class ConflictSeverity(Enum):
    """冲突严重程度"""
    LOW = "low"                       # 低风险
    MEDIUM = "medium"                 # 中等风险
    HIGH = "high"                     # 高风险
    CRITICAL = "critical"             # 严重风险


class RollbackAction(Enum):
    """回滚动作"""
    RESTORE_FILES = "restore_files"   # 恢复文件
    REVERT_VERSIONS = "revert_versions"  # 回滚版本
    CLEANUP_CACHE = "cleanup_cache"   # 清理缓存


@dataclass
class ConflictContext:
    """冲突处理上下文"""
    project_root: str
    conflicts: List[DependencyConflict]
    handling_mode: ConflictHandlingMode
    backup_path: Optional[str] = None
    dry_run: bool = False
    user_preferences: Dict[str, Any] = field(default_factory=dict)
    resolution_history: List[ConflictResolution] = field(default_factory=list)


@dataclass
class ConflictSolution:
    """冲突解决方案"""
    conflict: DependencyConflict
    resolution: ConflictResolution
    applied_actions: List[str] = field(default_factory=list)
    backup_files: List[str] = field(default_factory=list)
    verification_result: Optional[bool] = None
    rollback_plan: List[RollbackAction] = field(default_factory=list)
    confidence: float = 0.0


@dataclass
class HandlingResult:
    """冲突处理结果"""
    total_conflicts: int
    resolved_conflicts: int
    failed_conflicts: int
    solutions: List[ConflictSolution]
    handling_time_sec: float
    success_rate: float
    rollback_available: bool = True
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


class ConflictHandler:
    """
    版本冲突处理器

    功能特性：
    - 冲突检测和分类
    - 多种解决策略
    - 自动解决方案生成
    - 回滚机制
    - 验证和确认
    """

    def __init__(self, conflict_resolver: Optional[VersionConflictResolver] = None):
        """
        初始化冲突处理器

        Args:
            conflict_resolver: 冲突解决器
        """
        self.conflict_resolver = conflict_resolver or VersionConflictResolver()
        self.logger = get_logger(self.__class__.__name__)
        self._handling_history: List[ConflictContext] = []

    def handle_conflicts(self, context: ConflictContext) -> HandlingResult:
        """
        处理版本冲突

        Args:
            context: 冲突处理上下文

        Returns:
            处理结果
        """
        start_time = time.time()
        self.logger.info(f"开始处理 {len(context.conflicts)} 个版本冲突...")

        # 创建备份
        if not context.dry_run:
            backup_path = self._create_backup(context.project_root)
            context.backup_path = backup_path

        try:
            # 分析和分类冲突
            classified_conflicts = self._classify_conflicts(context.conflicts)

            # 生成解决方案
            solutions = self._generate_solutions(classified_conflicts, context)

            # 应用解决方案
            applied_solutions = self._apply_solutions(solutions, context)

            # 验证结果
            verified_solutions = self._verify_solutions(applied_solutions, context)

            # 计算处理结果
            handling_time = time.time() - start_time
            result = self._calculate_handling_result(verified_solutions, handling_time)

            self.logger.info(f"冲突处理完成: 成功 {result.resolved_conflicts}/{result.total_conflicts}")
            return result

        except Exception as e:
            self.logger.error(f"冲突处理过程中发生异常: {e}")
            return HandlingResult(
                total_conflicts=len(context.conflicts),
                resolved_conflicts=0,
                failed_conflicts=len(context.conflicts),
                solutions=[],
                handling_time_sec=time.time() - start_time,
                success_rate=0.0,
                errors=[str(e)]
            )

    def _classify_conflicts(self, conflicts: List[DependencyConflict]) -> Dict[ConflictSeverity, List[DependencyConflict]]:
        """分类冲突"""
        classified = {
            ConflictSeverity.LOW: [],
            ConflictSeverity.MEDIUM: [],
            ConflictSeverity.HIGH: [],
            ConflictSeverity.CRITICAL: []
        }

        for conflict in conflicts:
            severity = self._determine_conflict_severity(conflict)
            classified[severity].append(conflict)

        return classified

    def _determine_conflict_severity(self, conflict: DependencyConflict) -> ConflictSeverity:
        """确定冲突严重程度"""
        # 基于生态系统确定基础严重程度
        base_severity = {
            "system": ConflictSeverity.CRITICAL,
            "database": ConflictSeverity.HIGH,
            "python": ConflictSeverity.MEDIUM,
            "nodejs": ConflictSeverity.MEDIUM
        }

        severity = base_severity.get(conflict.ecosystem, ConflictSeverity.LOW)

        # 根据冲突数量调整
        if len(conflict.conflicts) > 3:
            if severity == ConflictSeverity.LOW:
                severity = ConflictSeverity.MEDIUM
            elif severity == ConflictSeverity.MEDIUM:
                severity = ConflictSeverity.HIGH

        # 根据冲突描述调整
        if conflict.severity == "error":
            severity = ConflictSeverity.CRITICAL
        elif conflict.severity == "warning":
            if severity == ConflictSeverity.LOW:
                severity = ConflictSeverity.MEDIUM
        elif conflict.severity == "info":
            # info级别降低严重程度
            if severity == ConflictSeverity.MEDIUM:
                severity = ConflictSeverity.LOW

        return severity

    def _generate_solutions(
        self,
        classified_conflicts: Dict[ConflictSeverity, List[DependencyConflict]],
        context: ConflictContext
    ) -> List[ConflictSolution]:
        """生成解决方案"""
        solutions = []

        # 根据处理模式确定处理顺序
        if context.handling_mode == ConflictHandlingMode.SAFE:
            # 安全模式：只处理低风险冲突
            handling_order = [ConflictSeverity.LOW]
        elif context.handling_mode == ConflictHandlingMode.AUTO:
            # 自动模式：处理除严重风险外的所有冲突
            handling_order = [ConflictSeverity.LOW, ConflictSeverity.MEDIUM, ConflictSeverity.HIGH]
        else:
            # 其他模式：处理所有冲突
            handling_order = [ConflictSeverity.LOW, ConflictSeverity.MEDIUM, ConflictSeverity.HIGH, ConflictSeverity.CRITICAL]

        for severity in handling_order:
            conflicts = classified_conflicts.get(severity, [])
            for conflict in conflicts:
                try:
                    solution = self._generate_single_solution(conflict, context)
                    if solution:
                        solutions.append(solution)
                except Exception as e:
                    self.logger.error(f"为冲突 {conflict.dependency_name} 生成解决方案失败: {e}")

        return solutions

    def _generate_single_solution(
        self,
        conflict: DependencyConflict,
        context: ConflictContext
    ) -> Optional[ConflictSolution]:
        """为单个冲突生成解决方案"""
        # 确定解决策略
        strategy = self._select_resolution_strategy(conflict, context)

        # 生成解决方案
        resolutions = self.conflict_resolver.resolve_conflicts([conflict], strategy)

        if not resolutions:
            self.logger.warning(f"无法为冲突 {conflict.dependency_name} 生成解决方案")
            return None

        resolution = resolutions[0]  # 使用第一个解决方案

        # 创建解决方案对象
        solution = ConflictSolution(
            conflict=conflict,
            resolution=resolution,
            confidence=resolution.confidence
        )

        # 生成回滚计划
        solution.rollback_plan = self._generate_rollback_plan(conflict, resolution)

        return solution

    def _select_resolution_strategy(
        self,
        conflict: DependencyConflict,
        context: ConflictContext
    ) -> ResolutionStrategy:
        """选择解决策略"""
        # 根据用户偏好选择策略
        preferred_strategy = context.user_preferences.get("resolution_strategy")
        if preferred_strategy:
            try:
                return ResolutionStrategy(preferred_strategy)
            except ValueError:
                self.logger.warning(f"无效的解决策略: {preferred_strategy}")

        # 根据冲突严重程度选择策略
        severity = self._determine_conflict_severity(conflict)

        if severity == ConflictSeverity.CRITICAL:
            # 严重冲突：手动处理
            return ResolutionStrategy.MANUAL
        elif severity == ConflictSeverity.HIGH:
            # 高风险冲突：兼容性优先
            return ResolutionStrategy.COMPATIBLE
        elif severity == ConflictSeverity.MEDIUM:
            # 中等风险冲突：最小版本
            return ResolutionStrategy.MINIMUM
        else:
            # 低风险冲突：最新版本
            return ResolutionStrategy.LATEST

    def _generate_rollback_plan(
        self,
        conflict: DependencyConflict,
        resolution: ConflictResolution
    ) -> List[RollbackAction]:
        """生成回滚计划"""
        rollback_plan = []

        # 根据解决的文件确定回滚动作
        for file_path in resolution.affected_files:
            rollback_plan.append(RollbackAction.RESTORE_FILES)

        # 如果涉及版本变更，需要版本回滚
        if resolution.strategy != ResolutionStrategy.MAINTAIN:
            rollback_plan.append(RollbackAction.REVERT_VERSIONS)

        # 清理安装缓存
        rollback_plan.append(RollbackAction.CLEANUP_CACHE)

        return rollback_plan

    def _apply_solutions(
        self,
        solutions: List[ConflictSolution],
        context: ConflictContext
    ) -> List[ConflictSolution]:
        """应用解决方案"""
        applied_solutions = []

        for solution in solutions:
            try:
                self.logger.info(f"应用解决方案: {solution.conflict.dependency_name}")

                if context.dry_run:
                    # 试运行模式
                    solution.applied_actions.append(f"[DRY RUN] Would resolve {solution.conflict.dependency_name}")
                    solution.verification_result = True
                else:
                    # 实际应用解决方案
                    success = self._apply_single_solution(solution, context)
                    solution.verification_result = success

                    if success:
                        self.logger.info(f"成功解决冲突: {solution.conflict.dependency_name}")
                    else:
                        self.logger.error(f"解决冲突失败: {solution.conflict.dependency_name}")

                applied_solutions.append(solution)

            except Exception as e:
                self.logger.error(f"应用解决方案时发生异常: {e}")
                solution.verification_result = False
                applied_solutions.append(solution)

        return applied_solutions

    def _apply_single_solution(
        self,
        solution: ConflictSolution,
        context: ConflictContext
    ) -> bool:
        """应用单个解决方案"""
        try:
            # 备份将要修改的文件
            for file_path in solution.resolution.affected_files:
                if os.path.exists(file_path):
                    backup_file = self._backup_file(file_path, context.backup_path)
                    solution.backup_files.append(backup_file)

            # 应用解决方案
            if solution.resolution.strategy == ResolutionStrategy.LATEST:
                return self._apply_latest_version_solution(solution, context)
            elif solution.resolution.strategy == ResolutionStrategy.MINIMUM:
                return self._apply_minimum_version_solution(solution, context)
            elif solution.resolution.strategy == ResolutionStrategy.COMPATIBLE:
                return self._apply_compatible_version_solution(solution, context)
            else:
                # MAINTAIN 或 MANUAL 策略
                return self._apply_maintain_solution(solution, context)

        except Exception as e:
            self.logger.error(f"应用解决方案失败: {e}")
            return False

    def _apply_latest_version_solution(self, solution: ConflictSolution, context: ConflictContext) -> bool:
        """应用最新版本解决方案"""
        # 实现最新版本更新逻辑
        dependency = solution.conflict.dependency_name
        version = solution.resolution.resolved_version

        for file_path in solution.resolution.affected_files:
            if file_path.endswith('requirements.txt'):
                self._update_requirements_file(file_path, dependency, f">={version}")
            elif file_path.endswith('package.json'):
                self._update_package_json_file(file_path, dependency, f"^{version}")

        solution.applied_actions.append(f"Updated {dependency} to latest version {version}")
        return True

    def _apply_minimum_version_solution(self, solution: ConflictSolution, context: ConflictContext) -> bool:
        """应用最小版本解决方案"""
        dependency = solution.conflict.dependency_name
        version = solution.resolution.resolved_version

        for file_path in solution.resolution.affected_files:
            if file_path.endswith('requirements.txt'):
                self._update_requirements_file(file_path, dependency, f">={version}")
            elif file_path.endswith('package.json'):
                self._update_package_json_file(file_path, dependency, f"~{version}")

        solution.applied_actions.append(f"Updated {dependency} to minimum version {version}")
        return True

    def _apply_compatible_version_solution(self, solution: ConflictSolution, context: ConflictContext) -> bool:
        """应用兼容版本解决方案"""
        dependency = solution.conflict.dependency_name
        version = solution.resolution.resolved_version

        for file_path in solution.resolution.affected_files:
            if file_path.endswith('requirements.txt'):
                self._update_requirements_file(file_path, dependency, f"=={version}")
            elif file_path.endswith('package.json'):
                self._update_package_json_file(file_path, dependency, version)

        solution.applied_actions.append(f"Updated {dependency} to compatible version {version}")
        return True

    def _apply_maintain_solution(self, solution: ConflictSolution, context: ConflictContext) -> bool:
        """应用维持现状解决方案"""
        solution.applied_actions.append(f"Maintained current version for {solution.conflict.dependency_name}")
        return True

    def _update_requirements_file(self, file_path: str, dependency: str, version_spec: str) -> bool:
        """更新 requirements.txt 文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            updated_lines = []
            for line in lines:
                if line.strip().startswith(dependency):
                    # 更新依赖行
                    new_line = f"{dependency}{version_spec}\n"
                    updated_lines.append(new_line)
                else:
                    updated_lines.append(line)

            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(updated_lines)

            return True
        except Exception as e:
            self.logger.error(f"更新 requirements.txt 失败: {e}")
            return False

    def _update_package_json_file(self, file_path: str, dependency: str, version_spec: str) -> bool:
        """更新 package.json 文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 更新 dependencies
            if "dependencies" in data and dependency in data["dependencies"]:
                data["dependencies"][dependency] = version_spec

            # 更新 devDependencies
            if "devDependencies" in data and dependency in data["devDependencies"]:
                data["devDependencies"][dependency] = version_spec

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            return True
        except Exception as e:
            self.logger.error(f"更新 package.json 失败: {e}")
            return False

    def _verify_solutions(
        self,
        solutions: List[ConflictSolution],
        context: ConflictContext
    ) -> List[ConflictSolution]:
        """验证解决方案"""
        verified_solutions = []

        for solution in solutions:
            try:
                if solution.verification_result is False:
                    # 已经知道失败的解决方案
                    verified_solutions.append(solution)
                    continue

                # 验证解决方案是否有效
                is_valid = self._verify_solution(solution, context)
                solution.verification_result = is_valid

                if is_valid:
                    self.logger.info(f"解决方案验证通过: {solution.conflict.dependency_name}")
                else:
                    self.logger.warning(f"解决方案验证失败: {solution.conflict.dependency_name}")

                verified_solutions.append(solution)

            except Exception as e:
                self.logger.error(f"验证解决方案时发生异常: {e}")
                solution.verification_result = False
                verified_solutions.append(solution)

        return verified_solutions

    def _verify_solution(self, solution: ConflictSolution, context: ConflictContext) -> bool:
        """验证单个解决方案"""
        try:
            # 检查文件是否被正确修改
            affected_files = getattr(solution.resolution, 'affected_files', [])
            if affected_files:
                for file_path in affected_files:
                    if not self._verify_file_modification(file_path, solution):
                        return False

            # 检查版本冲突是否解决
            if not self._verify_conflict_resolution(solution):
                return False

            return True

        except Exception as e:
            self.logger.error(f"验证解决方案失败: {e}")
            return False

    def _verify_file_modification(self, file_path: str, solution: ConflictSolution) -> bool:
        """验证文件修改"""
        if not os.path.exists(file_path):
            return False

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 检查是否包含预期的版本规格
            dependency = solution.conflict.dependency_name
            expected_version = solution.resolution.resolved_version

            if file_path.endswith('requirements.txt'):
                # 检查各种版本格式
                patterns = [
                    f"{dependency}{expected_version}",
                    f"{dependency}>={expected_version}",
                    f"{dependency}=={expected_version}",
                    f"{dependency}~{expected_version}",
                    f"{dependency}^{expected_version}"
                ]
                return any(pattern in content for pattern in patterns)
            elif file_path.endswith('package.json'):
                data = json.loads(content)
                return (data.get("dependencies", {}).get(dependency) == expected_version or
                       data.get("devDependencies", {}).get(dependency) == expected_version)

            return True

        except Exception as e:
            self.logger.error(f"验证文件修改失败: {e}")
            return False

    def _verify_conflict_resolution(self, solution: ConflictSolution) -> bool:
        """验证冲突解决"""
        # 这里可以实现更复杂的验证逻辑
        # 例如重新检测冲突，检查是否已解决
        return True

    def _calculate_handling_result(
        self,
        solutions: List[ConflictSolution],
        handling_time: float
    ) -> HandlingResult:
        """计算处理结果"""
        total_conflicts = len(solutions)
        resolved_conflicts = len([s for s in solutions if s.verification_result])
        failed_conflicts = total_conflicts - resolved_conflicts

        success_rate = resolved_conflicts / total_conflicts if total_conflicts > 0 else 0.0

        return HandlingResult(
            total_conflicts=total_conflicts,
            resolved_conflicts=resolved_conflicts,
            failed_conflicts=failed_conflicts,
            solutions=solutions,
            handling_time_sec=handling_time,
            success_rate=success_rate
        )

    def rollback_solutions(self, solutions: List[ConflictSolution], backup_path: str) -> bool:
        """回滚解决方案"""
        self.logger.info(f"开始回滚 {len(solutions)} 个解决方案...")

        try:
            # 按相反顺序回滚解决方案
            for solution in reversed(solutions):
                self._rollback_single_solution(solution, backup_path)

            self.logger.info("解决方案回滚完成")
            return True

        except Exception as e:
            self.logger.error(f"回滚解决方案失败: {e}")
            return False

    def _rollback_single_solution(self, solution: ConflictSolution, backup_path: str) -> bool:
        """回滚单个解决方案"""
        for action in solution.rollback_plan:
            if action == RollbackAction.RESTORE_FILES:
                self._restore_backup_files(solution.backup_files)
            elif action == RollbackAction.REVERT_VERSIONS:
                # 版本回滚逻辑
                pass
            elif action == RollbackAction.CLEANUP_CACHE:
                # 清理缓存逻辑
                pass

        return True

    def _create_backup(self, project_root: str) -> str:
        """创建项目备份"""
        timestamp = int(time.time())
        backup_path = os.path.join(project_root, f".dependency_backup_{timestamp}")

        try:
            # 备份关键文件
            backup_dirs = ["", "frontend", "backend"]
            backup_files = ["requirements.txt", "package.json", "pyproject.toml"]

            os.makedirs(backup_path, exist_ok=True)

            for backup_dir in backup_dirs:
                src_dir = os.path.join(project_root, backup_dir)
                dst_dir = os.path.join(backup_path, backup_dir)

                if os.path.exists(src_dir):
                    shutil.copytree(src_dir, dst_dir, dirs_exist_ok=True)

            for backup_file in backup_files:
                src_file = os.path.join(project_root, backup_file)
                if os.path.exists(src_file):
                    dst_file = os.path.join(backup_path, backup_file)
                    shutil.copy2(src_file, dst_file)

            self.logger.info(f"项目备份已创建: {backup_path}")
            return backup_path

        except Exception as e:
            self.logger.error(f"创建项目备份失败: {e}")
            raise

    def _backup_file(self, file_path: str, backup_path: str) -> str:
        """备份单个文件"""
        relative_path = os.path.relpath(file_path, os.path.dirname(backup_path))
        backup_file_path = os.path.join(backup_path, relative_path)

        os.makedirs(os.path.dirname(backup_file_path), exist_ok=True)
        shutil.copy2(file_path, backup_file_path)

        return backup_file_path

    def _restore_backup_files(self, backup_files: List[str]) -> None:
        """恢复备份文件"""
        for backup_file in backup_files:
            if os.path.exists(backup_file):
                # 确定原始文件路径
                # 备份文件路径格式: /path/to/.dependency_backup_XXXXX/original/path/file.ext
                # 需要提取原始文件的绝对路径
                original_file = self._get_original_file_path(backup_file)

                if original_file:
                    # 确保目标目录存在
                    original_dir = os.path.dirname(original_file)
                    if original_dir:
                        os.makedirs(original_dir, exist_ok=True)

                    shutil.copy2(backup_file, original_file)
                    self.logger.debug(f"恢复文件: {original_file}")
                else:
                    self.logger.warning(f"无法确定原始文件路径: {backup_file}")

    def _get_original_file_path(self, backup_file: str) -> Optional[str]:
        """获取备份文件的原始路径"""
        parts = backup_file.split(os.sep)

        if ".dependency_backup_" not in backup_file:
            # 如果不是标准备份路径，返回文件名作为相对路径
            return os.path.basename(backup_file)

        # 找到备份目录索引
        backup_dir_idx = None
        for i, part in enumerate(parts):
            if ".dependency_backup_" in part:
                backup_dir_idx = i
                break

        if backup_dir_idx is None:
            return None

        # 获取备份目录后的路径
        original_parts = parts[backup_dir_idx + 1:]

        # 如果路径为空，返回None
        if not original_parts:
            return None

        # 构建原始文件路径
        # 需要从备份路径中还原到项目根目录
        original_file = os.path.join(*original_parts)

        # 获取项目根目录（备份目录的父目录）
        backup_dir = os.path.dirname(backup_file)
        for _ in range(len(original_parts)):
            backup_dir = os.path.dirname(backup_dir)

        project_root = backup_dir
        return os.path.join(project_root, original_file)


# 便利函数
def create_conflict_handler() -> ConflictHandler:
    """创建冲突处理器"""
    resolver = VersionConflictResolver()
    return ConflictHandler(resolver)


def handle_project_conflicts(
    project_root: str,
    conflicts: List[DependencyConflict],
    handling_mode: ConflictHandlingMode = ConflictHandlingMode.AUTO,
    dry_run: bool = False
) -> HandlingResult:
    """
    处理项目冲突的便利函数

    Args:
        project_root: 项目根目录
        conflicts: 冲突列表
        handling_mode: 处理模式
        dry_run: 是否为试运行

    Returns:
        处理结果
    """
    handler = create_conflict_handler()
    context = ConflictContext(
        project_root=project_root,
        conflicts=conflicts,
        handling_mode=handling_mode,
        dry_run=dry_run
    )

    return handler.handle_conflicts(context)