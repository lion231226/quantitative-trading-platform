"""
依赖分析器测试

This module contains comprehensive tests for the dependency analyzer
including file detection, parsing, conflict detection, and analysis.
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch

from core.dependency_analyzer import (
    DependencyAnalyzer,
    DependencyFileFormat,
    ProjectDependency,
    DependencyConflict
)
from config.config_manager import ConfigManager


class TestDependencyAnalyzer:
    """依赖分析器测试类"""

    @pytest.fixture
    def temp_project_dir(self):
        """创建临时项目目录"""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)

            # 创建 Python 依赖文件
            requirements_content = """
fastapi==0.111.0
uvicorn[standard]==0.29.0
pandas>=2.0.0
requests==2.32.3
"""
            (project_dir / "requirements.txt").write_text(requirements_content)

            # 创建 Node.js 依赖文件
            package_content = {
                "name": "test-project",
                "version": "1.0.0",
                "dependencies": {
                    "react": "^18.0.0",
                    "axios": "^1.7.0"
                },
                "devDependencies": {
                    "typescript": "^5.0.0",
                    "@types/node": "^20.0.0"
                }
            }
            import json
            (project_dir / "package.json").write_text(json.dumps(package_content, indent=2))

            # 创建 docker-compose 文件
            docker_content = """
version: '3.8'
services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
  app:
    build: .
"""
            (project_dir / "docker-compose.yml").write_text(docker_content)

            yield project_dir

    @pytest.fixture
    def analyzer(self, temp_project_dir):
        """创建依赖分析器实例"""
        config_manager = Mock()
        config_manager.get_project_root.return_value = str(temp_project_dir)
        return DependencyAnalyzer(str(temp_project_dir), config_manager)

    def test_detect_dependency_files(self, analyzer, temp_project_dir):
        """测试依赖文件检测"""
        discovered_files = analyzer.detect_dependency_files()

        assert len(discovered_files) > 0
        assert "requirements.txt" in [Path(f).name for files in discovered_files.values() for f in files]
        assert "package.json" in [Path(f).name for files in discovered_files.values() for f in files]

    def test_parse_requirements_txt(self, analyzer, temp_project_dir):
        """测试解析 requirements.txt"""
        requirements_file = temp_project_dir / "requirements.txt"
        content = requirements_file.read_text()

        dependencies = analyzer._parse_requirements_txt(content, str(requirements_file))

        assert len(dependencies) > 0
        fastapi_dep = next((dep for dep in dependencies if dep.name == "fastapi"), None)
        assert fastapi_dep is not None
        assert fastapi_dep.version_spec == "==0.111.0"
        assert fastapi_dep.ecosystem == "python"

    def test_parse_package_json(self, analyzer, temp_project_dir):
        """测试解析 package.json"""
        package_file = temp_project_dir / "package.json"
        content = package_file.read_text()

        dependencies, metadata = analyzer._parse_package_json(content, str(package_file))

        assert len(dependencies) > 0
        react_dep = next((dep for dep in dependencies if dep.name == "react"), None)
        assert react_dep is not None
        assert react_dep.version_spec == "^18.0.0"
        assert react_dep.ecosystem == "nodejs"
        assert not react_dep.is_dev_dependency

        # 检查开发依赖
        typescript_dep = next((dep for dep in dependencies if dep.name == "typescript"), None)
        assert typescript_dep is not None
        assert typescript_dep.is_dev_dependency

    def test_detect_database_services(self, analyzer):
        """测试数据库服务检测"""
        database_deps = analyzer._detect_database_services()
        # 应该检测到 redis 服务
        redis_dep = next((dep for dep in database_deps if dep.name == "redis"), None)
        assert redis_dep is not None
        assert redis_dep.ecosystem == "database"

    def test_analyze_dependencies(self, analyzer):
        """测试完整依赖分析"""
        analysis = analyzer.analyze_dependencies()

        assert analysis.total_dependencies > 0
        assert len(analysis.dependency_files) > 0
        assert "python" in analysis.dependencies_by_ecosystem
        assert "nodejs" in analysis.dependencies_by_ecosystem

    def test_detect_conflicts(self, analyzer):
        """测试冲突检测"""
        # 创建有冲突的依赖
        dependencies = [
            ProjectDependency("fastapi", "python", "==0.111.0", source_file="req1.txt"),
            ProjectDependency("fastapi", "python", "==0.110.0", source_file="req2.txt"),
        ]

        conflicts = analyzer._detect_conflicts(dependencies)

        assert len(conflicts) > 0
        conflict = conflicts[0]
        assert conflict.dependency_name == "fastapi"
        assert conflict.ecosystem == "python"

    def test_determine_installation_order(self, analyzer):
        """测试安装顺序确定"""
        dependencies = [
            ProjectDependency("system-dep", "system"),
            ProjectDependency("redis", "database"),
            ProjectDependency("fastapi", "python"),
            ProjectDependency("react", "nodejs"),
        ]

        order = analyzer._determine_installation_order(dependencies)

        assert len(order) == len(dependencies)
        # 系统依赖应该最先
        assert "system:system-dep" in order
        # 数据库依赖应该在 Python/Node.js 之前
        redis_index = order.index("database:redis")
        python_index = order.index("python:fastapi")
        assert redis_index < python_index

    def test_get_analysis_summary(self, analyzer):
        """测试分析摘要"""
        analysis = analyzer.analyze_dependencies()
        summary = analyzer.get_analysis_summary(analysis)

        assert "project_root" in summary
        assert "total_dependencies" in summary
        assert "ecosystems" in summary
        assert summary["total_dependencies"] == analysis.total_dependencies

    def test_export_analysis_report(self, analyzer, temp_project_dir):
        """测试导出分析报告"""
        analysis = analyzer.analyze_dependencies()
        report_path = temp_project_dir / "analysis_report.json"

        success = analyzer.export_analysis_report(analysis, str(report_path))

        assert success
        assert report_path.exists()

        # 验证报告内容
        import json
        with open(report_path) as f:
            report = json.load(f)

        assert "analysis_summary" in report
        assert "dependencies" in report
        assert "installation_order" in report

    def test_parse_python_requirement_line(self, analyzer):
        """测试解析 Python 依赖行"""
        test_cases = [
            ("fastapi==0.111.0", "fastapi", "==0.111.0"),
            ("pandas>=2.0.0", "pandas", ">=2.0.0"),
            ("requests", "requests", ""),
            ("numpy>=1.20.0,<2.0.0", "numpy", ">=1.20.0,<2.0.0"),
        ]

        for line, expected_name, expected_version in test_cases:
            dep = analyzer._parse_python_requirement_line(line, "test.txt")
            if expected_name:  # 只测试有效的解析结果
                assert dep is not None
                assert dep.name == expected_name
                assert dep.version_spec == expected_version

    def test_search_patterns_in_files(self, analyzer):
        """测试在文件中搜索模式"""
        # 创建测试文件
        test_file = analyzer.project_root / "test.py"
        test_file.write_text("import redis\nredis_host = 'localhost'")

        patterns = [r'redis://', r'redis_host']
        found = analyzer._search_patterns_in_files(patterns)

        assert found  # 应该找到 redis_host 模式

    def test_analysis_stats(self, analyzer):
        """测试分析统计"""
        analysis = analyzer.analyze_dependencies()
        stats = analyzer.analysis_stats

        assert "files_scanned" in stats
        assert "dependencies_found" in stats
        assert "conflicts_detected" in stats
        assert "analysis_time_ms" in stats
        assert stats["files_scanned"] > 0
        assert stats["dependencies_found"] == analysis.total_dependencies


if __name__ == "__main__":
    pytest.main([__file__, "-v"])