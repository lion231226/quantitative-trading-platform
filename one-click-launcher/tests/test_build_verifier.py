"""
Tests for BuildVerifier module

This test suite covers:
- Build tool detection
- Cross-platform command execution
- Timeout handling and retries
- Build error analysis
- Build artifact validation
- Dependency checking
- Progress tracking integration
"""

import pytest
import asyncio
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from core.build_verifier import (
    BuildVerifier,
    BuildTool,
    BuildResult,
    BuildError
)
from utils.progress_tracker import ProgressTracker


class TestBuildVerifier:
    """Test suite for BuildVerifier class"""

    @pytest.fixture
    def verifier(self):
        """Create a BuildVerifier instance for testing"""
        return BuildVerifier(timeout=30, max_retries=2)

    @pytest.fixture
    def mock_progress_tracker(self):
        """Create a mock progress tracker"""
        tracker = Mock(spec=ProgressTracker)
        tracker.update_progress = Mock()
        return tracker

    @pytest.fixture
    def temp_node_project(self):
        """Create a temporary Node.js project for testing"""
        temp_dir = tempfile.mkdtemp()
        project_path = Path(temp_dir)

        # Create package.json with build script
        package_json = {
            "name": "test-project",
            "version": "1.0.0",
            "scripts": {
                "build": "echo 'Build successful' && mkdir -p dist && echo 'test' > dist/bundle.js"
            },
            "devDependencies": {
                "webpack": "^5.0.0"
            }
        }

        with open(project_path / "package.json", "w") as f:
            json.dump(package_json, f)

        yield project_path

        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def temp_python_project(self):
        """Create a temporary Python project for testing"""
        temp_dir = tempfile.mkdtemp()
        project_path = Path(temp_dir)

        # Create setup.py
        setup_py = """
from setuptools import setup, find_packages

setup(
    name="test-project",
    version="1.0.0",
    packages=find_packages()
)
"""
        with open(project_path / "setup.py", "w") as f:
            f.write(setup_py)

        # Create a simple Python module
        (project_path / "test_module.py").write_text("def hello(): return 'world'")

        yield project_path

        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.mark.asyncio
    async def test_detect_build_tool_npm(self, verifier, temp_node_project):
        """Test detection of npm as build tool"""
        # Create package-lock.json to indicate npm usage
        (temp_node_project / "package-lock.json").write_text("{}")

        tool = verifier.detect_build_tool(str(temp_node_project))
        assert tool == BuildTool.NPM

    @pytest.mark.asyncio
    async def test_detect_build_tool_yarn(self, verifier, temp_node_project):
        """Test detection of yarn as build tool"""
        # Create yarn.lock to indicate yarn usage
        (temp_node_project / "yarn.lock").write_text("test lock file")

        tool = verifier.detect_build_tool(str(temp_node_project))
        assert tool == BuildTool.YARN

    @pytest.mark.asyncio
    async def test_detect_build_tool_pnpm(self, verifier, temp_node_project):
        """Test detection of pnpm as build tool"""
        # Create pnpm-lock.yaml to indicate pnpm usage
        (temp_node_project / "pnpm-lock.yaml").write_text("test lock file")

        tool = verifier.detect_build_tool(str(temp_node_project))
        assert tool == BuildTool.PNPM

    @pytest.mark.asyncio
    async def test_detect_build_tool_python(self, verifier, temp_python_project):
        """Test detection of Python as build tool"""
        tool = verifier.detect_build_tool(str(temp_python_project))
        assert tool == BuildTool.PYTHON

    @pytest.mark.asyncio
    async def test_detect_build_tool_none(self, verifier):
        """Test detection fails for project without build configuration"""
        temp_dir = tempfile.mkdtemp()
        project_path = Path(temp_dir)

        try:
            tool = verifier.detect_build_tool(str(project_path))
            assert tool is None
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.mark.asyncio
    async def test_get_build_command(self, verifier):
        """Test getting appropriate build commands for different tools"""
        # Mock the OS detector
        mock_system_info = Mock()
        mock_system_info.os_type.value = 'linux'

        with patch.object(verifier, 'os_detector') as mock_detector:
            mock_detector.detect_os_info.return_value = mock_system_info

            npm_cmd = verifier.get_build_command(BuildTool.NPM)
            assert npm_cmd == ['npm', 'run', 'build']

            python_cmd = verifier.get_build_command(BuildTool.PYTHON)
            assert python_cmd == ['python3', '-m', 'compileall', '.']

    @pytest.mark.asyncio
    async def test_execute_build_command_success(self, verifier):
        """Test successful build command execution"""
        # Mock subprocess and OS detection
        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate.return_value = (b"Build success", b"")

        mock_os_info = Mock()
        mock_os_info.os_type.value = 'linux'  # Use exec path on Unix-like systems

        with patch('asyncio.create_subprocess_exec', return_value=mock_process), \
             patch.object(verifier.os_detector, 'detect_os_info', return_value=mock_os_info):

            exit_code, stdout, stderr, duration = await verifier.execute_build_command(
                ['echo', 'test'], '/tmp', BuildTool.NPM
            )

        assert exit_code == 0
        assert "Build success" in stdout
        assert stderr == "" or stderr == b""
        assert duration > 0

    @pytest.mark.asyncio
    async def test_execute_build_command_timeout(self, verifier):
        """Test build command execution with timeout"""
        # Mock asyncio.wait_for to raise TimeoutError
        mock_process = AsyncMock()
        mock_process.kill = AsyncMock()
        mock_process.wait = AsyncMock(return_value=None)

        mock_os_info = Mock()
        mock_os_info.os_type.value = 'linux'  # Use exec path on Unix-like systems

        with patch('asyncio.create_subprocess_exec', return_value=mock_process), \
             patch('asyncio.wait_for', side_effect=asyncio.TimeoutError()), \
             patch.object(verifier.os_detector, 'detect_os_info', return_value=mock_os_info):

            exit_code, stdout, stderr, duration = await verifier.execute_build_command(
                ['sleep', '10'], '/tmp', BuildTool.NPM
            )

        assert exit_code == -1
        assert "timed out" in stderr

    @pytest.mark.asyncio
    async def test_analyze_build_error_module_not_found(self, verifier):
        """Test error analysis for missing module"""
        stdout = "Build failed"
        stderr = "Error: Cannot find module 'express'"

        error = verifier.analyze_build_error(stdout, stderr, BuildTool.NPM)

        assert error.error_type == 'npm_missing_dependency'
        assert 'npm install' in error.solution
        assert error.severity == 'high'

    @pytest.mark.asyncio
    async def test_analyze_build_error_memory(self, verifier):
        """Test error analysis for out of memory error"""
        stdout = ""
        stderr = "JavaScript heap out of memory"

        error = verifier.analyze_build_error(stdout, stderr, BuildTool.NPM)

        assert error.error_type == 'build_out_of_memory'
        assert 'NODE_OPTIONS' in error.solution
        assert 'max-old-space-size' in error.solution

    @pytest.mark.asyncio
    async def test_analyze_build_error_unknown(self, verifier):
        """Test error analysis for unknown error"""
        stdout = "Some unknown error"
        stderr = "Weird error message"

        error = verifier.analyze_build_error(stdout, stderr, BuildTool.NPM)

        assert error.error_type == 'unknown_build_error'
        assert error.severity == 'medium'

    @pytest.mark.asyncio
    async def test_validate_build_artifacts_nodejs(self, verifier, temp_node_project):
        """Test validation of Node.js build artifacts"""
        # Create dist directory with files
        dist_dir = temp_node_project / "dist"
        dist_dir.mkdir()
        (dist_dir / "bundle.js").write_text("test content")

        result = verifier.validate_build_artifacts(str(temp_node_project), BuildTool.NPM)
        assert result is True

    @pytest.mark.asyncio
    async def test_validate_build_artifacts_missing(self, verifier, temp_node_project):
        """Test validation when build artifacts are missing"""
        result = verifier.validate_build_artifacts(str(temp_node_project), BuildTool.NPM)
        assert result is False

    @pytest.mark.asyncio
    async def test_validate_build_artifacts_python(self, verifier, temp_python_project):
        """Test validation of Python build artifacts"""
        # Create __pycache__ directory
        pycache_dir = temp_python_project / "__pycache__"
        pycache_dir.mkdir()
        (pycache_dir / "test_module.pyc").write_text("compiled")

        result = verifier.validate_build_artifacts(str(temp_python_project), BuildTool.PYTHON)
        assert result is True

    @pytest.mark.asyncio
    async def test_check_dependencies_nodejs(self, verifier, temp_node_project):
        """Test checking Node.js dependencies"""
        # Create node_modules directory
        (temp_node_project / "node_modules").mkdir()

        result = verifier.check_dependencies(str(temp_node_project), BuildTool.NPM)
        assert result is True

    @pytest.mark.asyncio
    async def test_check_dependencies_python(self, verifier, temp_python_project):
        """Test checking Python dependencies"""
        result = verifier.check_dependencies(str(temp_python_project), BuildTool.PYTHON)
        assert result is True  # setup.py exists

    @pytest.mark.asyncio
    async def test_verify_build_success(self, verifier, temp_node_project, mock_progress_tracker):
        """Test successful build verification"""
        verifier.set_progress_tracker(mock_progress_tracker)

        # Mock the command execution to return success
        mock_result = (0, "Build success", "", 1.0)
        with patch.object(verifier, 'execute_build_command', return_value=mock_result), \
             patch.object(verifier, 'validate_build_artifacts', return_value=True), \
             patch.object(verifier, 'check_dependencies', return_value=True):

            result = await verifier.verify_build(str(temp_node_project))

        assert result.success is True
        assert result.tool == BuildTool.NPM
        assert result.exit_code == 0
        assert result.artifacts_validated is True
        assert result.dependencies_checked is True

        # Verify progress tracker was called
        assert mock_progress_tracker.update_progress.called

    @pytest.mark.asyncio
    async def test_verify_build_failure_no_tool(self, verifier, mock_progress_tracker):
        """Test build verification when no build tool is found"""
        verifier.set_progress_tracker(mock_progress_tracker)

        temp_dir = tempfile.mkdtemp()
        try:
            result = await verifier.verify_build(temp_dir)

            assert result.success is False
            assert result.error_analysis is not None
            assert result.error_analysis['error_type'] == 'no_build_tool'
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.mark.asyncio
    async def test_verify_build_failure_with_retry(self, verifier, temp_node_project, mock_progress_tracker):
        """Test build verification with retry mechanism"""
        verifier.set_progress_tracker(mock_progress_tracker)
        verifier.max_retries = 2

        # Mock command execution to fail first time, succeed second time
        mock_results = [
            (1, "Build failed", "Error", 1.0),  # First attempt fails
            (0, "Build success", "", 1.0)      # Second attempt succeeds
        ]

        with patch.object(verifier, 'execute_build_command', side_effect=mock_results), \
             patch.object(verifier, 'validate_build_artifacts', return_value=True), \
             patch.object(verifier, 'check_dependencies', return_value=True), \
             patch('asyncio.sleep'):  # Speed up retry delays

            result = await verifier.verify_build(str(temp_node_project))

        assert result.success is True
        assert result.exit_code == 0

    @pytest.mark.asyncio
    async def test_verify_multiple_builds(self, verifier, temp_node_project, temp_python_project, mock_progress_tracker):
        """Test verification of multiple builds in parallel"""
        verifier.set_progress_tracker(mock_progress_tracker)

        project_paths = [str(temp_node_project), str(temp_python_project)]

        # Mock successful builds
        mock_result = (0, "Build success", "", 1.0)
        with patch.object(verifier, 'execute_build_command', return_value=mock_result), \
             patch.object(verifier, 'validate_build_artifacts', return_value=True), \
             patch.object(verifier, 'check_dependencies', return_value=True):

            results = await verifier.verify_multiple_builds(project_paths)

        assert len(results) == 2
        assert all(result.success for result in results)

    @pytest.mark.asyncio
    async def test_verify_multiple_builds_with_exception(self, verifier, temp_node_project, mock_progress_tracker):
        """Test verification of multiple builds with one exception"""
        verifier.set_progress_tracker(mock_progress_tracker)

        project_paths = [str(temp_node_project), "/nonexistent/path"]

        # Mock successful build for first project
        mock_result = (0, "Build success", "", 1.0)
        with patch.object(verifier, 'execute_build_command', return_value=mock_result), \
             patch.object(verifier, 'validate_build_artifacts', return_value=True), \
             patch.object(verifier, 'check_dependencies', return_value=True):

            results = await verifier.verify_multiple_builds(project_paths)

        assert len(results) == 2
        assert results[0].success is True
        assert results[1].success is False
        assert "does not exist" in results[1].stderr.lower() or "no such file" in results[1].stderr.lower() or "no supported build tool" in results[1].stderr.lower()

    def test_build_result_dataclass(self):
        """Test BuildResult dataclass creation and attributes"""
        result = BuildResult(
            success=True,
            tool=BuildTool.NPM,
            command="npm run build",
            exit_code=0,
            stdout="Build output",
            stderr="",
            duration=2.5,
            artifacts_validated=True,
            dependencies_checked=True
        )

        assert result.success is True
        assert result.tool == BuildTool.NPM
        assert result.artifacts_validated is True

    def test_build_error_dataclass(self):
        """Test BuildError dataclass creation and attributes"""
        error = BuildError(
            error_type='test_error',
            severity='high',
            message='Test error message',
            solution='Test solution',
            details={'key': 'value'}
        )

        assert error.error_type == 'test_error'
        assert error.severity == 'high'
        assert error.solution == 'Test solution'
        assert error.details['key'] == 'value'


class TestBuildVerifierIntegration:
    """Integration tests for BuildVerifier with real commands"""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_real_npm_build_verification(self):
        """Test with real npm project (if npm is available)"""
        # Skip if npm is not available
        import shutil
        if not shutil.which('npm'):
            pytest.skip("npm not available")

        verifier = BuildVerifier(timeout=60)

        # Create a temporary Node.js project
        temp_dir = tempfile.mkdtemp()
        project_path = Path(temp_dir)

        try:
            # Create package.json
            package_json = {
                "name": "integration-test",
                "version": "1.0.0",
                "scripts": {
                    "build": "mkdir -p build && echo 'integration test' > build/output.txt"
                }
            }

            with open(project_path / "package.json", "w") as f:
                json.dump(package_json, f)

            # Run build verification
            result = await verifier.verify_build(str(project_path))

            assert result.success is True
            assert result.tool == BuildTool.NPM
            assert result.artifacts_validated is True

            # Verify build artifacts exist
            assert (project_path / "build" / "output.txt").exists()

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_real_python_build_verification(self):
        """Test with real Python project"""
        verifier = BuildVerifier(timeout=60)

        # Create a temporary Python project
        temp_dir = tempfile.mkdtemp()
        project_path = Path(temp_dir)

        try:
            # Create setup.py
            setup_py = """
from setuptools import setup, find_packages

setup(
    name="integration-test",
    version="1.0.0",
    packages=find_packages()
)
"""
            with open(project_path / "setup.py", "w") as f:
                f.write(setup_py)

            # Create a Python module
            (project_path / "test_module.py").write_text("def hello(): return 'world'")

            # Run build verification
            result = await verifier.verify_build(str(project_path))

            assert result.success is True
            assert result.tool == BuildTool.PYTHON
            assert result.artifacts_validated is True

            # Verify __pycache__ directory was created
            assert any(project_path.rglob('__pycache__'))

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)