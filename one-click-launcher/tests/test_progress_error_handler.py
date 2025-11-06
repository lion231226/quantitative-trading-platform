"""
进度跟踪和错误处理器测试

This module contains comprehensive tests for the progress and error handling system
including error classification, recovery strategies, and progress tracking.
"""

import pytest
import tempfile
import json
import time
from unittest.mock import Mock, patch, MagicMock

from core.progress_error_handler import (
    ProgressErrorHandler,
    ErrorClassifier,
    RecoveryStrategy,
    ErrorInfo,
    ProgressSnapshot,
    ProgressReport,
    ErrorSeverity,
    ErrorCategory,
    RecoveryAction
)
from core.dependency_analyzer import ProjectDependency
from core.batch_installer import InstallationResult, InstallationStatus


class TestErrorClassifier:
    """错误分类器测试"""

    @pytest.fixture
    def classifier(self):
        """创建错误分类器实例"""
        return ErrorClassifier()

    def test_classify_network_error(self, classifier):
        """测试网络错误分类"""
        error = ConnectionError("Connection refused")
        category = classifier.classify_error(error)

        assert category == ErrorCategory.NETWORK

    def test_classify_filesystem_error(self, classifier):
        """测试文件系统错误分类"""
        error = FileNotFoundError("No such file or directory")
        category = classifier.classify_error(error)

        assert category == ErrorCategory.FILESYSTEM

    def test_classify_dependency_error(self, classifier):
        """测试依赖错误分类"""
        error = ImportError("Module not found")
        category = classifier.classify_error(error)

        assert category == ErrorCategory.DEPENDENCY

    def test_determine_severity(self, classifier):
        """测试确定错误严重程度"""
        # 系统错误应该是严重级别
        system_error = SystemError("System error")
        severity = classifier.determine_severity(system_error, ErrorCategory.SYSTEM)

        assert severity == ErrorSeverity.CRITICAL

        # 网络错误应该是警告级别
        network_error = ConnectionError("Network timeout")
        severity = classifier.determine_severity(network_error, ErrorCategory.NETWORK)

        assert severity == ErrorSeverity.WARNING

    def test_classify_with_context(self, classifier):
        """测试带上下文的错误分类"""
        error = Exception("Unknown error")
        context = {"operation": "network download", "url": "https://example.com"}

        category = classifier.classify_error(error, context)
        assert category == ErrorCategory.NETWORK


class TestRecoveryStrategy:
    """恢复策略测试"""

    @pytest.fixture
    def strategy(self):
        """创建恢复策略实例"""
        return RecoveryStrategy()

    def test_suggest_recovery_action_network(self, strategy):
        """测试网络错误恢复建议"""
        error = ErrorInfo(
            error_id="test-1",
            timestamp=time.time(),
            severity=ErrorSeverity.WARNING,
            category=ErrorCategory.NETWORK,
            message="Network timeout"
        )

        action = strategy.suggest_recovery_action(error)
        assert action in [RecoveryAction.RETRY, RecoveryAction.FALLBACK]

    def test_suggest_recovery_action_critical(self, strategy):
        """测试严重错误恢复建议"""
        error = ErrorInfo(
            error_id="test-2",
            timestamp=time.time(),
            severity=ErrorSeverity.CRITICAL,
            category=ErrorCategory.SYSTEM,
            message="System crash"
        )

        action = strategy.suggest_recovery_action(error)
        assert action == RecoveryAction.ABORT

    def test_generate_suggestions_network(self, strategy):
        """测试网络错误恢复建议"""
        error = ErrorInfo(
            error_id="test-3",
            timestamp=time.time(),
            severity=ErrorSeverity.WARNING,
            category=ErrorCategory.NETWORK,
            message="Connection refused"
        )

        suggestions = strategy.generate_suggestions(error)
        assert len(suggestions) > 0
        assert any("网络" in suggestion or "network" in suggestion.lower() for suggestion in suggestions)

    def test_generate_suggestions_filesystem(self, strategy):
        """测试文件系统错误恢复建议"""
        error = ErrorInfo(
            error_id="test-4",
            timestamp=time.time(),
            severity=ErrorSeverity.ERROR,
            category=ErrorCategory.FILESYSTEM,
            message="Permission denied"
        )

        suggestions = strategy.generate_suggestions(error)
        assert len(suggestions) > 0
        assert any("权限" in suggestion or "permission" in suggestion.lower() for suggestion in suggestions)


class TestProgressErrorHandler:
    """进度错误处理器测试"""

    @pytest.fixture
    def handler(self):
        """创建进度错误处理器实例"""
        # 使用唯一的session_id避免测试间冲突
        import uuid
        session_id = f"test-session-{uuid.uuid4().hex[:8]}"
        handler = ProgressErrorHandler(session_id)
        yield handler
        # 清理资源
        if hasattr(handler, 'cleanup'):
            handler.cleanup()

    @pytest.fixture
    def sample_dependency(self):
        """创建示例依赖"""
        return ProjectDependency(
            name="test-package",
            ecosystem="python",
            version_spec="==1.0.0",
            source_file="requirements.txt"
        )

    def test_initialization(self, handler):
        """测试初始化"""
        assert handler.session_id == "test-session"
        assert handler.start_time > 0
        assert handler.end_time is None
        assert len(handler.errors) == 0
        assert len(handler.warnings) == 0

    def test_create_progress_tracker(self, handler):
        """测试创建进度跟踪器"""
        tracker = handler.create_progress_tracker("test-component", total_steps=3)

        assert tracker is not None
        assert "test-component" in handler.progress_trackers
        assert len(tracker.progress_info.steps) == 3

    def test_track_progress(self, handler):
        """测试跟踪进度"""
        handler.create_progress_tracker("test-component", total_steps=3)

        handler.track_progress("test-component", 0)
        handler.complete_step("test-component", 0, True)

        progress = handler.get_current_progress()
        assert progress.component_progress["test-component"] > 0

    def test_handle_error(self, handler):
        """测试处理错误"""
        error = ConnectionError("Network timeout")
        error_info = handler.handle_error(error, component="test-component")

        assert error_info is not None
        assert error_info.message == "Network timeout"
        assert error_info.category == ErrorCategory.NETWORK
        assert error_info.severity == ErrorSeverity.WARNING
        assert len(handler.errors) > 0

    def test_handle_warning(self, handler):
        """测试处理警告"""
        error = UserWarning("Deprecated feature")
        with patch.object(handler.error_classifier, 'determine_severity', return_value=ErrorSeverity.WARNING):
            error_info = handler.handle_error(error, component="test-component")

        assert error_info is not None
        assert len(handler.warnings) > 0
        assert len(handler.errors) == 0

    def test_handle_installation_result_success(self, handler, sample_dependency):
        """测试处理成功的安装结果"""
        result = InstallationResult(
            dependency=sample_dependency,
            strategy=Mock(),
            status=InstallationStatus.COMPLETED,
            start_time=time.time(),
            end_time=time.time() + 1,
            success=True
        )

        # 应该不产生错误
        handler.handle_installation_result(result)
        assert len(handler.errors) == 0

    def test_handle_installation_result_failure(self, handler, sample_dependency):
        """测试处理失败的安装结果"""
        result = InstallationResult(
            dependency=sample_dependency,
            strategy=Mock(),
            status=InstallationStatus.FAILED,
            start_time=time.time(),
            end_time=time.time() + 1,
            success=False,
            error_message="Installation failed"
        )

        handler.handle_installation_result(result)
        assert len(handler.errors) == 1

    def test_retry_error(self, handler):
        """测试重试错误"""
        error = ConnectionError("Network timeout")
        error_info = handler.handle_error(error, component="test-component")

        # 第一次重试应该成功
        assert handler.retry_error(error_info.error_id) is True
        assert error_info.retry_count == 1

        # 达到最大重试次数后应该失败
        error_info.retry_count = error_info.max_retries
        assert handler.retry_error(error_info.error_id) is False

    def test_get_current_progress(self, handler):
        """测试获取当前进度"""
        handler.create_progress_tracker("test-component")
        progress = handler.get_current_progress()

        assert isinstance(progress, ProgressSnapshot)
        assert progress.timestamp > 0
        assert progress.overall_progress >= 0.0
        assert progress.current_phase == "installation"

    def test_get_progress_summary(self, handler):
        """测试获取进度摘要"""
        handler.create_progress_tracker("test-component")
        summary = handler.get_progress_summary()

        assert "session_id" in summary
        assert "elapsed_time_sec" in summary
        assert "overall_progress" in summary
        assert "total_errors" in summary
        assert "total_warnings" in summary

    def test_generate_report(self, handler):
        """测试生成报告"""
        handler.create_progress_tracker("test-component")

        # 添加一个错误
        error = ConnectionError("Test error")
        handler.handle_error(error, component="test-component")

        report = handler.generate_report()

        assert isinstance(report, ProgressReport)
        assert report.session_id == handler.session_id
        assert report.start_time == handler.start_time
        assert len(report.errors) == 1
        assert report.success_rate >= 0.0

    def test_save_report(self, handler):
        """测试保存报告"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name

        try:
            handler.create_progress_tracker("test-component")
            success = handler.save_report(temp_path)

            assert success is True
            assert os.path.exists(temp_path)

            # 验证报告内容
            with open(temp_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            assert "session_id" in data
            assert "summary" in data
            assert "success_rate" in data

        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_finish_session(self, handler):
        """测试结束会话"""
        assert handler.end_time is None

        handler.finish_session()

        assert handler.end_time is not None
        assert handler.end_time >= handler.start_time

    def test_get_user_friendly_feedback(self, handler):
        """测试获取用户友好的反馈"""
        feedback = handler.get_user_friendly_feedback()

        assert isinstance(feedback, str)
        assert len(feedback) > 0

        # 添加错误后的反馈
        error = ConnectionError("Test error")
        handler.handle_error(error, component="test-component")

        feedback_with_error = handler.get_user_friendly_feedback()
        assert "❌" in feedback_with_error or "错误" in feedback_with_error

    def test_multiple_components_progress(self, handler):
        """测试多组件进度跟踪"""
        handler.create_progress_tracker("component1", total_steps=2)
        handler.create_progress_tracker("component2", total_steps=3)

        # 跟踪组件1的进度
        handler.track_progress("component1", 0)
        handler.complete_step("component1", 0, True)

        # 跟踪组件2的进度
        handler.track_progress("component2", 0)
        handler.complete_step("component2", 0, True)

        progress = handler.get_current_progress()
        assert len(progress.component_progress) == 2
        assert "component1" in progress.component_progress
        assert "component2" in progress.component_progress


def test_create_progress_error_handler():
    """测试创建进度错误处理器"""
    handler = create_progress_error_handler()
    assert isinstance(handler, ProgressErrorHandler)
    assert handler.session_id is not None


def test_track_dependency_installation():
    """测试跟踪依赖安装的便利函数"""
    from core.progress_error_handler import track_dependency_installation

    handler = create_progress_error_handler()
    dependency = ProjectDependency("test-pkg", "python", "==1.0.0", "requirements.txt")

    # 模拟安装函数
    def mock_install():
        time.sleep(0.1)
        result = Mock()
        result.success = True
        return result

    # 成功安装
    result = track_dependency_installation(handler, dependency, mock_install)
    assert result.success is True

    # 失败安装
    def mock_install_fail():
        raise Exception("Installation failed")

    with pytest.raises(Exception):
        track_dependency_installation(handler, dependency, mock_install_fail)

    assert len(handler.errors) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])