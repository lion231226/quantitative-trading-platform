"""
安装验证器

提供全面的安装验证功能，包括版本检查、功能验证、环境变量验证等。
支持多种开发工具的安装验证。
"""

import os
import subprocess
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import tempfile

from utils.logger import get_logger
from core.operating_system_detector import OperatingSystemDetector
from core.dependency_checker import DependencyChecker, DependencyStatus, VersionInfo

logger = get_logger(__name__)


class VerificationStatus(Enum):
    """验证状态枚举"""
    NOT_VERIFIED = "not_verified"
    VERIFYING = "verifying"
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    SKIPPED = "skipped"


@dataclass
class VerificationResult:
    """验证结果"""
    component: str
    status: VerificationStatus
    version: Optional[str] = None
    expected_version: Optional[str] = None
    install_path: Optional[str] = None
    executable_path: Optional[str] = None
    error_message: Optional[str] = None
    warning_messages: List[str] = None
    verification_details: Dict[str, Any] = None
    performance_metrics: Dict[str, float] = None

    def __post_init__(self):
        if self.warning_messages is None:
            self.warning_messages = []
        if self.verification_details is None:
            self.verification_details = {}
        if self.performance_metrics is None:
            self.performance_metrics = {}

    @property
    def is_successful(self) -> bool:
        """检查验证是否成功"""
        return self.status == VerificationStatus.PASSED

    @property
    def has_warnings(self) -> bool:
        """检查是否有警告"""
        return len(self.warning_messages) > 0

    def add_warning(self, message: str) -> None:
        """添加警告消息"""
        self.warning_messages.append(message)
        if self.status == VerificationStatus.PASSED:
            self.status = VerificationStatus.WARNING

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'component': self.component,
            'status': self.status.value,
            'version': self.version,
            'expected_version': self.expected_version,
            'install_path': self.install_path,
            'executable_path': self.executable_path,
            'error_message': self.error_message,
            'warning_messages': self.warning_messages,
            'verification_details': self.verification_details,
            'performance_metrics': self.performance_metrics,
            'is_successful': self.is_successful,
            'has_warnings': self.has_warnings
        }


@dataclass
class EnvironmentVariable:
    """环境变量信息"""
    name: str
    value: Optional[str] = None
    should_exist: bool = True
    should_contain: Optional[str] = None
    description: str = ""


class InstallationVerifier:
    """
    安装验证器

    功能特性：
    - 验证开发工具安装状态
    - 检查版本兼容性
    - 验证环境变量配置
    - 功能测试和性能基准
    - 生成详细的验证报告
    """

    def __init__(self, os_detector: Optional[OperatingSystemDetector] = None):
        """
        初始化安装验证器

        Args:
            os_detector: 操作系统检测器实例
        """
        self.os_detector = os_detector or OperatingSystemDetector()
        self.system_info = self.os_detector.detect_os_info()
        self.dependency_checker = DependencyChecker(self.system_info.os_type)
        self.logger = get_logger(self.__class__.__name__)

        # 性能基准数据
        self.performance_benchmarks = {
            'nodejs': {
                'startup_time_max': 2.0,  # 秒
                'memory_usage_max': 50 * 1024 * 1024,  # 50MB
                'simple_script_time_max': 0.1  # 秒
            },
            'python': {
                'startup_time_max': 1.5,  # 秒
                'memory_usage_max': 40 * 1024 * 1024,  # 40MB
                'simple_script_time_max': 0.05  # 秒
            },
            'git': {
                'init_time_max': 0.5,  # 秒
                'config_time_max': 0.1  # 秒
            }
        }

        self.logger.info(f"初始化安装验证器 - 平台: {self.system_info.os_type.value} {self.system_info.architecture.value}")

    async def verify_all(self, components: List[str] = None) -> Dict[str, VerificationResult]:
        """
        验证所有指定组件的安装

        Args:
            components: 要验证的组件列表，None 表示验证所有组件

        Returns:
            验证结果字典
        """
        if components is None:
            components = ['nodejs', 'python', 'git']

        results = {}
        self.logger.info(f"开始验证组件: {', '.join(components)}")

        for component in components:
            try:
                self.logger.info(f"验证 {component}...")
                if component == 'nodejs':
                    results[component] = await self.verify_nodejs()
                elif component == 'python':
                    results[component] = await self.verify_python()
                elif component == 'git':
                    results[component] = await self.verify_git()
                else:
                    self.logger.warning(f"不支持的组件: {component}")
                    results[component] = VerificationResult(
                        component=component,
                        status=VerificationStatus.FAILED,
                        error_message=f"不支持的组件: {component}"
                    )
            except Exception as e:
                self.logger.error(f"验证 {component} 失败: {e}")
                results[component] = VerificationResult(
                    component=component,
                    status=VerificationStatus.FAILED,
                    error_message=str(e)
                )

        return results

    async def verify_nodejs(self, expected_version: Optional[str] = None) -> VerificationResult:
        """
        验证 Node.js 安装

        Args:
            expected_version: 期望的版本

        Returns:
            验证结果
        """
        result = VerificationResult(
            component="Node.js",
            status=VerificationStatus.VERIFYING,
            expected_version=expected_version
        )

        try:
            self.logger.info("验证 Node.js 安装...")

            # 基本安装检查
            dependency_info = self.dependency_checker.check_nodejs()
            if dependency_info.status != DependencyStatus.INSTALLED:
                result.status = VerificationStatus.FAILED
                result.error_message = dependency_info.error_message or "Node.js 未正确安装"
                return result

            result.version = str(dependency_info.version)
            result.executable_path = dependency_info.executable_path
            result.install_path = dependency_info.install_path

            # 版本检查
            if expected_version:
                if not self._check_version_requirement(result.version, expected_version):
                    result.add_warning(f"版本 {result.version} 可能不满足期望版本 {expected_version}")

            # 功能验证
            await self._verify_nodejs_functionality(result)

            # 环境变量验证
            await self._verify_nodejs_environment(result)

            # 性能测试
            await self._benchmark_nodejs_performance(result)

            if result.status != VerificationStatus.FAILED:
                result.status = VerificationStatus.PASSED

            self.logger.info(f"Node.js 验证完成: {result.status.value}")
            return result

        except Exception as e:
            self.logger.error(f"Node.js 验证失败: {e}")
            result.status = VerificationStatus.FAILED
            result.error_message = str(e)
            return result

    async def verify_python(self, expected_version: Optional[str] = None) -> VerificationResult:
        """
        验证 Python 安装

        Args:
            expected_version: 期望的版本

        Returns:
            验证结果
        """
        result = VerificationResult(
            component="Python",
            status=VerificationStatus.VERIFYING,
            expected_version=expected_version
        )

        try:
            self.logger.info("验证 Python 安装...")

            # 基本安装检查
            dependency_info = self.dependency_checker.check_python()
            if dependency_info.status != DependencyStatus.INSTALLED:
                result.status = VerificationStatus.FAILED
                result.error_message = dependency_info.error_message or "Python 未正确安装"
                return result

            result.version = str(dependency_info.version)
            result.executable_path = dependency_info.executable_path
            result.install_path = dependency_info.install_path

            # 版本检查
            if expected_version:
                if not self._check_version_requirement(result.version, expected_version):
                    result.add_warning(f"版本 {result.version} 可能不满足期望版本 {expected_version}")

            # 功能验证
            await self._verify_python_functionality(result)

            # 环境变量验证
            await self._verify_python_environment(result)

            # 性能测试
            await self._benchmark_python_performance(result)

            if result.status != VerificationStatus.FAILED:
                result.status = VerificationStatus.PASSED

            self.logger.info(f"Python 验证完成: {result.status.value}")
            return result

        except Exception as e:
            self.logger.error(f"Python 验证失败: {e}")
            result.status = VerificationStatus.FAILED
            result.error_message = str(e)
            return result

    async def verify_git(self, expected_version: Optional[str] = None) -> VerificationResult:
        """
        验证 Git 安装

        Args:
            expected_version: 期望的版本

        Returns:
            验证结果
        """
        result = VerificationResult(
            component="Git",
            status=VerificationStatus.VERIFYING,
            expected_version=expected_version
        )

        try:
            self.logger.info("验证 Git 安装...")

            # 基本安装检查
            dependency_info = self.dependency_checker.check_git()
            if dependency_info.status != DependencyStatus.INSTALLED:
                result.status = VerificationStatus.FAILED
                result.error_message = dependency_info.error_message or "Git 未正确安装"
                return result

            result.version = str(dependency_info.version)
            result.executable_path = dependency_info.executable_path
            result.install_path = dependency_info.install_path

            # 版本检查
            if expected_version:
                if not self._check_version_requirement(result.version, expected_version):
                    result.add_warning(f"版本 {result.version} 可能不满足期望版本 {expected_version}")

            # 功能验证
            await self._verify_git_functionality(result)

            # 环境变量验证
            await self._verify_git_environment(result)

            # 性能测试
            await self._benchmark_git_performance(result)

            if result.status != VerificationStatus.FAILED:
                result.status = VerificationStatus.PASSED

            self.logger.info(f"Git 验证完成: {result.status.value}")
            return result

        except Exception as e:
            self.logger.error(f"Git 验证失败: {e}")
            result.status = VerificationStatus.FAILED
            result.error_message = str(e)
            return result

    async def _verify_nodejs_functionality(self, result: VerificationResult) -> None:
        """验证 Node.js 功能"""
        try:
            # 检查 NPM 是否可用
            npm_result = subprocess.run(['npm', '--version'],
                                      capture_output=True, text=True, timeout=30)
            if npm_result.returncode == 0:
                result.verification_details['npm_version'] = npm_result.stdout.strip()
            else:
                result.add_warning("NPM 不可用")

            # 测试简单的 JavaScript 执行
            test_script = 'console.log("Hello World");'
            js_result = subprocess.run(['node', '-e', test_script],
                                      capture_output=True, text=True, timeout=10)
            if js_result.returncode == 0 and js_result.stdout.strip() == "Hello World":
                result.verification_details['js_execution'] = True
            else:
                result.status = VerificationStatus.FAILED
                result.error_message = "JavaScript 执行测试失败"

            # 测试模块系统
            module_test = 'const fs = require("fs"); console.log(typeof fs.readFile);'
            module_result = subprocess.run(['node', '-e', module_test],
                                         capture_output=True, text=True, timeout=10)
            if module_result.returncode == 0 and 'function' in module_result.stdout:
                result.verification_details['module_system'] = True
            else:
                result.add_warning("模块系统测试失败")

        except Exception as e:
            result.status = VerificationStatus.FAILED
            result.error_message = f"Node.js 功能验证失败: {e}"

    async def _verify_python_functionality(self, result: VerificationResult) -> None:
        """验证 Python 功能"""
        try:
            # 检查 pip 是否可用
            pip_result = subprocess.run(['pip', '--version'],
                                      capture_output=True, text=True, timeout=30)
            if pip_result.returncode == 0:
                result.verification_details['pip_version'] = pip_result.stdout.strip()
            else:
                # 尝试 pip3
                pip3_result = subprocess.run(['pip3', '--version'],
                                            capture_output=True, text=True, timeout=30)
                if pip3_result.returncode == 0:
                    result.verification_details['pip_version'] = pip3_result.stdout.strip()
                else:
                    result.add_warning("pip/pip3 不可用")

            # 测试简单的 Python 执行
            test_script = 'print("Hello World")'
            py_result = subprocess.run(['python', '-c', test_script],
                                      capture_output=True, text=True, timeout=10)
            if py_result.returncode == 0 and py_result.stdout.strip() == "Hello World":
                result.verification_details['python_execution'] = True
            else:
                # 尝试 python3
                py3_result = subprocess.run(['python3', '-c', test_script],
                                           capture_output=True, text=True, timeout=10)
                if py3_result.returncode == 0 and py3_result.stdout.strip() == "Hello World":
                    result.verification_details['python_execution'] = True
                    result.executable_path = "python3"
                else:
                    result.status = VerificationStatus.FAILED
                    result.error_message = "Python 执行测试失败"

            # 测试标准库
            stdlib_test = 'import json, os, sys; print("OK")'
            stdlib_result = subprocess.run([result.executable_path or 'python', '-c', stdlib_test],
                                         capture_output=True, text=True, timeout=10)
            if stdlib_result.returncode == 0 and stdlib_result.stdout.strip() == "OK":
                result.verification_details['standard_library'] = True
            else:
                result.add_warning("标准库测试失败")

        except Exception as e:
            result.status = VerificationStatus.FAILED
            result.error_message = f"Python 功能验证失败: {e}"

    async def _verify_git_functionality(self, result: VerificationResult) -> None:
        """验证 Git 功能"""
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                os.chdir(temp_dir)

                # 测试 git init
                init_result = subprocess.run(['git', 'init'],
                                           capture_output=True, text=True, timeout=30)
                if init_result.returncode == 0:
                    result.verification_details['git_init'] = True
                else:
                    result.status = VerificationStatus.FAILED
                    result.error_message = "git init 失败"
                    return

                # 测试 git config
                config_result = subprocess.run(['git', 'config', 'user.name', 'Test User'],
                                             capture_output=True, text=True, timeout=10)
                if config_result.returncode == 0:
                    result.verification_details['git_config'] = True
                else:
                    result.add_warning("git config 失败")

                # 创建测试文件并提交
                test_file = 'test.txt'
                with open(test_file, 'w') as f:
                    f.write('Test content')

                add_result = subprocess.run(['git', 'add', test_file],
                                           capture_output=True, text=True, timeout=10)
                commit_result = subprocess.run(['git', 'commit', '-m', 'Test commit'],
                                              capture_output=True, text=True, timeout=10)

                if add_result.returncode == 0 and commit_result.returncode == 0:
                    result.verification_details['git_commit'] = True
                else:
                    result.add_warning("git commit 测试失败")

                # 测试 git status
                status_result = subprocess.run(['git', 'status'],
                                             capture_output=True, text=True, timeout=10)
                if status_result.returncode == 0:
                    result.verification_details['git_status'] = True

        except Exception as e:
            result.status = VerificationStatus.FAILED
            result.error_message = f"Git 功能验证失败: {e}"

    async def _verify_nodejs_environment(self, result: VerificationResult) -> None:
        """验证 Node.js 环境变量"""
        env_vars = [
            EnvironmentVariable("NODE_PATH", should_exist=False),
            EnvironmentVariable("NODE_ENV", should_exist=False),
            EnvironmentVariable("PATH", should_contain="node", description="应包含 Node.js 路径")
        ]

        await self._verify_environment_variables(env_vars, result)

    async def _verify_python_environment(self, result: VerificationResult) -> None:
        """验证 Python 环境变量"""
        env_vars = [
            EnvironmentVariable("PYTHONPATH", should_exist=False),
            EnvironmentVariable("PYTHONHOME", should_exist=False),
            EnvironmentVariable("PATH", should_contain="python", description="应包含 Python 路径")
        ]

        await self._verify_environment_variables(env_vars, result)

    async def _verify_git_environment(self, result: VerificationResult) -> None:
        """验证 Git 环境变量"""
        env_vars = [
            EnvironmentVariable("GIT_HOME", should_exist=False),
            EnvironmentVariable("PATH", should_contain="git", description="应包含 Git 路径")
        ]

        await self._verify_environment_variables(env_vars, result)

    async def _verify_environment_variables(self, env_vars: List[EnvironmentVariable], result: VerificationResult) -> None:
        """验证环境变量"""
        env_details = {}

        for env_var in env_vars:
            value = os.environ.get(env_var.name)
            env_details[env_var.name] = {
                'exists': value is not None,
                'value': value if value else '',
                'should_exist': env_var.should_exist,
                'should_contain': env_var.should_contain,
                'description': env_var.description
            }

            if env_var.should_exist and value is None:
                result.add_warning(f"环境变量 {env_var.name} 不存在: {env_var.description}")

            if env_var.should_contain and value and env_var.should_contain.lower() not in value.lower():
                result.add_warning(f"环境变量 {env_var.name} 不包含 {env_var.should_contain}: {env_var.description}")

        result.verification_details['environment_variables'] = env_details

    async def _benchmark_nodejs_performance(self, result: VerificationResult) -> None:
        """Node.js 性能基准测试"""
        try:
            import time

            # 启动时间测试
            start_time = time.time()
            startup_result = subprocess.run(['node', '--version'],
                                          capture_output=True, text=True, timeout=10)
            startup_time = time.time() - start_time
            result.performance_metrics['startup_time'] = startup_time

            if startup_time > self.performance_benchmarks['nodejs']['startup_time_max']:
                result.add_warning(f"Node.js 启动时间较慢: {startup_time:.2f}s")

            # 简单脚本执行时间
            simple_script = 'console.log("perf_test");'
            start_time = time.time()
            perf_result = subprocess.run(['node', '-e', simple_script],
                                       capture_output=True, text=True, timeout=10)
            script_time = time.time() - start_time
            result.performance_metrics['simple_script_time'] = script_time

            if script_time > self.performance_benchmarks['nodejs']['simple_script_time_max']:
                result.add_warning(f"简单脚本执行时间较慢: {script_time:.3f}s")

        except Exception as e:
            result.add_warning(f"性能基准测试失败: {e}")

    async def _benchmark_python_performance(self, result: VerificationResult) -> None:
        """Python 性能基准测试"""
        try:
            import time

            # 启动时间测试
            start_time = time.time()
            startup_result = subprocess.run([result.executable_path or 'python', '--version'],
                                          capture_output=True, text=True, timeout=10)
            startup_time = time.time() - start_time
            result.performance_metrics['startup_time'] = startup_time

            if startup_time > self.performance_benchmarks['python']['startup_time_max']:
                result.add_warning(f"Python 启动时间较慢: {startup_time:.2f}s")

            # 简单脚本执行时间
            simple_script = 'print("perf_test")'
            start_time = time.time()
            perf_result = subprocess.run([result.executable_path or 'python', '-c', simple_script],
                                       capture_output=True, text=True, timeout=10)
            script_time = time.time() - start_time
            result.performance_metrics['simple_script_time'] = script_time

            if script_time > self.performance_benchmarks['python']['simple_script_time_max']:
                result.add_warning(f"简单脚本执行时间较慢: {script_time:.3f}s")

        except Exception as e:
            result.add_warning(f"性能基准测试失败: {e}")

    async def _benchmark_git_performance(self, result: VerificationResult) -> None:
        """Git 性能基准测试"""
        try:
            import time

            with tempfile.TemporaryDirectory() as temp_dir:
                os.chdir(temp_dir)

                # Git 初始化时间
                start_time = time.time()
                init_result = subprocess.run(['git', 'init'],
                                           capture_output=True, text=True, timeout=30)
                init_time = time.time() - start_time
                result.performance_metrics['init_time'] = init_time

                if init_time > self.performance_benchmarks['git']['init_time_max']:
                    result.add_warning(f"git init 时间较慢: {init_time:.2f}s")

                # Git 配置时间
                start_time = time.time()
                config_result = subprocess.run(['git', 'config', 'user.name', 'Test'],
                                             capture_output=True, text=True, timeout=10)
                config_time = time.time() - start_time
                result.performance_metrics['config_time'] = config_time

                if config_time > self.performance_benchmarks['git']['config_time_max']:
                    result.add_warning(f"git config 时间较慢: {config_time:.3f}s")

        except Exception as e:
            result.add_warning(f"Git 性能基准测试失败: {e}")

    def _check_version_requirement(self, current_version: str, required_version: str) -> bool:
        """
        检查版本是否满足要求

        Args:
            current_version: 当前版本
            required_version: 要求的版本

        Returns:
            是否满足要求
        """
        try:
            current = VersionInfo.from_string(current_version.lstrip('v'))
            required = VersionInfo.from_string(required_version.lstrip('v'))

            return current.major >= required.major and \
                   (current.major > required.major or current.minor >= required.minor)
        except Exception:
            return False

    def generate_verification_report(self, results: Dict[str, VerificationResult]) -> str:
        """
        生成验证报告

        Args:
            results: 验证结果字典

        Returns:
            格式化的验证报告
        """
        report_lines = [
            "=== 安装验证报告 ===",
            f"生成时间: {subprocess.run(['date'], capture_output=True, text=True).stdout.strip()}",
            f"操作系统: {self.system_info.os_type.value} {self.system_info.architecture.value}",
            ""
        ]

        # 总体状态
        total_components = len(results)
        successful_components = sum(1 for r in results.values() if r.is_successful)
        failed_components = sum(1 for r in results.values() if r.status == VerificationStatus.FAILED)
        warning_components = sum(1 for r in results.values() if r.has_warnings)

        report_lines.extend([
            f"总体状态: {successful_components}/{total_components} 组件验证通过",
            f"成功: {successful_components}, 失败: {failed_components}, 警告: {warning_components}",
            ""
        ])

        # 详细结果
        for component, result in results.items():
            status_icon = {
                VerificationStatus.PASSED: "✅",
                VerificationStatus.FAILED: "❌",
                VerificationStatus.WARNING: "⚠️",
                VerificationStatus.SKIPPED: "⏭️"
            }.get(result.status, "❓")

            report_lines.extend([
                f"{status_icon} {component}",
                f"   状态: {result.status.value}",
                f"   版本: {result.version or '未知'}",
            ])

            if result.executable_path:
                report_lines.append(f"   可执行文件: {result.executable_path}")

            if result.install_path:
                report_lines.append(f"   安装路径: {result.install_path}")

            if result.error_message:
                report_lines.append(f"   错误: {result.error_message}")

            if result.warning_messages:
                for warning in result.warning_messages:
                    report_lines.append(f"   警告: {warning}")

            if result.performance_metrics:
                report_lines.append("   性能指标:")
                for metric, value in result.performance_metrics.items():
                    if isinstance(value, float):
                        report_lines.append(f"     {metric}: {value:.3f}s")
                    else:
                        report_lines.append(f"     {metric}: {value}")

            report_lines.append("")

        return "\n".join(report_lines)

    def save_verification_report(self, results: Dict[str, VerificationResult], filepath: str) -> bool:
        """
        保存验证报告到文件

        Args:
            results: 验证结果字典
            filepath: 文件路径

        Returns:
            是否成功保存
        """
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)

            # 保存 JSON 格式
            json_data = {
                'timestamp': subprocess.run(['date'], capture_output=True, text=True).stdout.strip(),
                'system_info': self.system_info.to_dict(),
                'results': {name: result.to_dict() for name, result in results.items()}
            }

            json_path = filepath.replace('.txt', '.json')
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False)

            # 保存文本格式
            text_report = self.generate_verification_report(results)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(text_report)

            self.logger.info(f"验证报告已保存到: {filepath}")
            return True

        except Exception as e:
            self.logger.error(f"保存验证报告失败: {e}")
            return False