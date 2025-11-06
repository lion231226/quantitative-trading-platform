"""
版本冲突处理器测试

This module contains comprehensive tests for the conflict handler
including conflict classification, resolution strategies, and rollback mechanisms.
"""

import pytest
import tempfile
import json
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from core.conflict_handler import (
    ConflictHandler,
    ConflictContext,
    ConflictSolution,
    HandlingResult,
    ConflictHandlingMode,
    ConflictSeverity,
    RollbackAction
)
from core.dependency_analyzer import ProjectDependency, DependencyConflict
from core.conflict_resolver import ConflictResolution, ResolutionStrategy
from core.installation_strategy import PackageSource, PackageSourceType


class TestConflictHandler:
    """冲突处理器测试"""

    @pytest.fixture
    def handler(self):
        """创建冲突处理器实例"""
        from core.conflict_handler import ConflictHandler
        return ConflictHandler()

    @pytest.fixture
    def sample_conflicts(self):
        """创建示例冲突"""
        return [
            DependencyConflict(
                dependency_name="fastapi",
                ecosystem="python",
                conflicts=[("==0.111.0", "req1.txt"), ("==0.110.0", "req2.txt")],
                severity="warning",
                description="FastAPI 版本冲突"
            ),
            DependencyConflict(
                dependency_name="react",
                ecosystem="nodejs",
                conflicts=[("^18.0.0", "package.json"), ("^17.0.0", "package-lock.json")],
                severity="warning",
                description="React 版本冲突"
            )
        ]

    @pytest.fixture
    def temp_project_dir(self):
        """创建临时项目目录"""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)

            # 创建 requirements.txt
            req_content = """
fastapi==0.111.0
uvicorn==0.29.0
"""
            (project_dir / "requirements.txt").write_text(req_content)

            # 创建 package.json
            package_content = {
                "name": "test-project",
                "dependencies": {
                    "react": "^18.0.0",
                    "axios": "^1.7.0"
                }
            }
            (project_dir / "package.json").write_text(json.dumps(package_content, indent=2))

            yield project_dir

    def test_classify_conflicts(self, handler, sample_conflicts):
        """测试冲突分类"""
        classified = handler._classify_conflicts(sample_conflicts)

        assert ConflictSeverity.LOW in classified
        assert ConflictSeverity.MEDIUM in classified
        assert ConflictSeverity.HIGH in classified
        assert ConflictSeverity.CRITICAL in classified

    def test_determine_conflict_severity(self, handler):
        """测试确定冲突严重程度"""
        # 系统冲突
        system_conflict = DependencyConflict(
            dependency_name="python",
            ecosystem="system",
            conflicts=[("3.8.0", "file1"), ("3.9.0", "file2")],
            severity="error",
            description="Python 版本冲突"
        )
        severity = handler._determine_conflict_severity(system_conflict)
        assert severity == ConflictSeverity.CRITICAL

        # Python 冲突
        python_conflict = DependencyConflict(
            dependency_name="fastapi",
            ecosystem="python",
            conflicts=[("0.111.0", "file1"), ("0.110.0", "file2")],
            severity="warning",
            description="FastAPI 版本冲突"
        )
        severity = handler._determine_conflict_severity(python_conflict)
        assert severity in [ConflictSeverity.MEDIUM, ConflictSeverity.LOW]

    def test_select_resolution_strategy(self, handler):
        """测试选择解决策略"""
        context = ConflictContext(
            project_root="/test",
            conflicts=[],
            handling_mode=ConflictHandlingMode.AUTO
        )

        # 低风险冲突
        low_conflict = DependencyConflict(
            dependency_name="test-lib",
            ecosystem="python",
            conflicts=[("1.0.0", "file1")],
            severity="info",
            description="低风险冲突"
        )
        strategy = handler._select_resolution_strategy(low_conflict, context)
        assert strategy == ResolutionStrategy.LATEST

        # 严重冲突
        critical_conflict = DependencyConflict(
            dependency_name="system-lib",
            ecosystem="system",
            conflicts=[("1.0.0", "file1")],
            severity="error",
            description="严重冲突"
        )
        strategy = handler._select_resolution_strategy(critical_conflict, context)
        assert strategy == ResolutionStrategy.MANUAL

    def test_generate_rollback_plan(self, handler):
        """测试生成回滚计划"""
        conflict = DependencyConflict(
            dependency_name="test-lib",
            ecosystem="python",
            conflicts=[("1.0.0", "requirements.txt")],
            severity="warning",
            description="测试冲突"
        )

        resolution = ConflictResolution(
            dependency_name="test-lib",
            ecosystem="python",
            strategy=ResolutionStrategy.LATEST,
            resolved_version="2.0.0",
            confidence=0.8,
            explanation="升级到最新版本",
            affected_files=["requirements.txt"]
        )

        rollback_plan = handler._generate_rollback_plan(conflict, resolution)

        assert RollbackAction.RESTORE_FILES in rollback_plan
        assert RollbackAction.REVERT_VERSIONS in rollback_plan
        assert RollbackAction.CLEANUP_CACHE in rollback_plan

    def test_update_requirements_file(self, handler, temp_project_dir):
        """测试更新 requirements.txt 文件"""
        req_file = temp_project_dir / "requirements.txt"

        success = handler._update_requirements_file(
            str(req_file), "fastapi", ">=0.112.0"
        )

        assert success is True
        updated_content = req_file.read_text()
        assert "fastapi>=0.112.0" in updated_content

    def test_update_package_json_file(self, handler, temp_project_dir):
        """测试更新 package.json 文件"""
        package_file = temp_project_dir / "package.json"

        success = handler._update_package_json_file(
            str(package_file), "react", "^19.0.0"
        )

        assert success is True
        updated_data = json.loads(package_file.read_text())
        assert updated_data["dependencies"]["react"] == "^19.0.0"

    def test_verify_file_modification(self, handler, temp_project_dir):
        """测试验证文件修改"""
        req_file = temp_project_dir / "requirements.txt"
        original_content = req_file.read_text()

        # 修改文件
        handler._update_requirements_file(str(req_file), "fastapi", ">=0.112.0")

        # 创建解决方案
        conflict = DependencyConflict(
            dependency_name="fastapi",
            ecosystem="python",
            conflicts=[("==0.111.0", "requirements.txt")],
            severity="warning",
            description="FastAPI 冲突"
        )

        resolution = ConflictResolution(
            dependency_name="fastapi",
            ecosystem="python",
            strategy=ResolutionStrategy.LATEST,
            resolved_version="0.112.0",
            confidence=0.8,
            explanation="升级版本",
            affected_files=[str(req_file)]
        )

        solution = ConflictSolution(
            conflict=conflict,
            resolution=resolution
        )

        # 验证修改
        is_valid = handler._verify_file_modification(str(req_file), solution)
        assert is_valid is True

    def test_handle_conflicts_dry_run(self, handler, sample_conflicts):
        """试运行模式处理冲突"""
        context = ConflictContext(
            project_root="/test",
            conflicts=sample_conflicts,
            handling_mode=ConflictHandlingMode.AUTO,
            dry_run=True
        )

        with patch.object(handler, '_generate_single_solution') as mock_generate:
            # 模拟解决方案生成 - 为每个冲突创建一个解决方案
            def generate_solution_side_effect(conflict, ctx):
                mock_resolution = Mock()
                mock_resolution.affected_files = []  # 添加affected_files属性
                mock_solution = ConflictSolution(
                    conflict=conflict,
                    resolution=mock_resolution
                )
                mock_solution.verification_result = True
                return mock_solution

            mock_generate.side_effect = generate_solution_side_effect

            result = handler.handle_conflicts(context)

            assert result.total_conflicts == len(sample_conflicts)
            assert isinstance(result, HandlingResult)
            assert result.handling_time_sec > 0

    def test_handle_conflicts_with_backup(self, handler, sample_conflicts, temp_project_dir):
        """测试处理冲突（带备份）"""
        context = ConflictContext(
            project_root=str(temp_project_dir),
            conflicts=sample_conflicts[:1],  # 只处理一个冲突
            handling_mode=ConflictHandlingMode.AUTO,
            dry_run=False
        )

        with patch.object(handler, '_generate_single_solution') as mock_generate, \
             patch.object(handler, '_apply_single_solution') as mock_apply:

            # 模拟解决方案
            mock_solution = ConflictSolution(
                conflict=sample_conflicts[0],
                resolution=Mock()
            )
            mock_solution.verification_result = True
            mock_generate.return_value = mock_solution
            mock_apply.return_value = True

            result = handler.handle_conflicts(context)

            assert result.total_conflicts == 1
            assert context.backup_path is not None
            assert os.path.exists(context.backup_path)

    def test_calculate_handling_result(self, handler):
        """测试计算处理结果"""
        solutions = [
            ConflictSolution(
                conflict=Mock(),
                resolution=Mock()
            ),
            ConflictSolution(
                conflict=Mock(),
                resolution=Mock()
            )
        ]

        # 设置验证结果
        solutions[0].verification_result = True
        solutions[1].verification_result = False

        result = handler._calculate_handling_result(solutions, 10.5)

        assert result.total_conflicts == 2
        assert result.resolved_conflicts == 1
        assert result.failed_conflicts == 1
        assert result.success_rate == 0.5
        assert result.handling_time_sec == 10.5

    def test_create_backup(self, handler, temp_project_dir):
        """测试创建备份"""
        backup_path = handler._create_backup(str(temp_project_dir))

        assert os.path.exists(backup_path)
        assert os.path.exists(os.path.join(backup_path, "requirements.txt"))
        assert os.path.exists(os.path.join(backup_path, "package.json"))

    def test_backup_file(self, handler, temp_project_dir):
        """测试备份单个文件"""
        source_file = temp_project_dir / "requirements.txt"
        backup_path = temp_project_dir / "backup"

        backup_file = handler._backup_file(str(source_file), str(backup_path))

        assert os.path.exists(backup_file)
        assert os.path.basename(backup_file) == "requirements.txt"

    def test_rollback_solutions(self, handler, temp_project_dir):
        """测试回滚解决方案"""
        # 创建解决方案
        solution = ConflictSolution(
            conflict=Mock(),
            resolution=Mock()
        )
        solution.rollback_plan = [RollbackAction.RESTORE_FILES]

        # 创建备份
        backup_path = handler._create_backup(str(temp_project_dir))
        solution.backup_files = [os.path.join(backup_path, "requirements.txt")]

        # 修改原文件
        req_file = temp_project_dir / "requirements.txt"
        handler._update_requirements_file(str(req_file), "fastapi", ">=0.112.0")

        # 回滚
        success = handler.rollback_solutions([solution], str(backup_path))

        assert success is True

    def test_rollback_single_solution(self, handler, temp_project_dir):
        """测试回滚单个解决方案"""
        solution = ConflictSolution(
            conflict=Mock(),
            resolution=Mock()
        )
        solution.rollback_plan = [RollbackAction.RESTORE_FILES]

        # 创建备份
        backup_path = handler._create_backup(str(temp_project_dir))
        solution.backup_files = [os.path.join(backup_path, "requirements.txt")]

        # 修改原文件
        req_file = temp_project_dir / "requirements.txt"
        handler._update_requirements_file(str(req_file), "fastapi", ">=0.112.0")

        # 回滚
        success = handler._rollback_single_solution(solution, str(backup_path))

        assert success is True


def test_create_conflict_handler():
    """测试创建冲突处理器"""
    from core.conflict_handler import create_conflict_handler

    handler = create_conflict_handler()
    assert isinstance(handler, ConflictHandler)


def test_handle_project_conflicts():
    """测试处理项目冲突的便利函数"""
    from core.conflict_handler import handle_project_conflicts, ConflictHandlingMode

    # 创建模拟冲突
    conflict = DependencyConflict(
        dependency_name="test-lib",
        ecosystem="python",
        conflicts=[("1.0.0", "req.txt")],
        severity="warning",
        description="测试冲突"
    )

    with patch('core.conflict_handler.create_conflict_handler') as mock_create:
        mock_handler = Mock()
        mock_result = Mock(spec=HandlingResult)
        mock_handler.handle_conflicts.return_value = mock_result
        mock_create.return_value = mock_handler

        result = handle_project_conflicts(
            "/test/project",
            [conflict],
            ConflictHandlingMode.AUTO,
            dry_run=True
        )

        assert result == mock_result
        mock_handler.handle_conflicts.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])