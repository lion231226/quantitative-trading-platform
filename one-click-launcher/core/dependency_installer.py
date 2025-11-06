#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
依赖安装器 - 系统依赖检测和自动安装

提供完整的系统环境检测、依赖项检查和自动安装功能。
支持跨平台操作，包括Windows、macOS和Linux。
"""

import os
import sys
import asyncio
import subprocess
import platform
import time
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

# 核心导入
from core.environment_detector import EnvironmentDetector, SystemInfo, DependencyStatus
from core.operating_system_detector import OperatingSystemDetector, OperatingSystem, Architecture
from utils.logger import get_logger
from utils.config_manager import ConfigManager

logger = get_logger(__name__)
config = ConfigManager()

class DependencyType(Enum):
    """依赖类型"""
    PYTHON_PACKAGE = "python_package"
    SYSTEM_PACKAGE = "system_package"
    EXTERNAL_TOOL = "external_tool"
    SERVICE = "service"

class InstallationStatus(Enum):
    """安装状态"""
    NOT_INSTALLED = "not_installed"
    INSTALLED = "installed"
    OUTDATED = "outdated"
    INSTALLING = "installing"
    FAILED = "failed"
    SKIPPED = "skipped"

@dataclass
class DependencyRequirement:
    """依赖需求定义"""
    name: str
    dependency_type: DependencyType
    min_version: Optional[str] = None
    max_version: Optional[str] = None
    required: bool = True
    install_command: Optional[str] = None
    check_command: Optional[str] = None
    version_extract_pattern: Optional[str] = None

@dataclass
class InstallationResult:
    """安装结果"""
    dependency_name: str
    status: InstallationStatus
    version: Optional[str] = None
    error_message: Optional[str] = None
    install_time: float = 0.0

@dataclass
class EnvironmentCheckResult:
    """环境检查结果"""
    success: bool
    system_info: SystemInfo
    dependency_results: List[InstallationResult]
    missing_required: List[str]
    total_time: float
    error_message: Optional[str] = None

class DependencyInstaller:
    """依赖安装器主类"""

    def __init__(self):
        """初始化依赖安装器"""
        self.env_detector = EnvironmentDetector()
        self.os_detector = OperatingSystemDetector()
        self.system_info = None
        self._setup_dependency_requirements()

    def _setup_dependency_requirements(self):
        """设置依赖需求"""
        self.requirements = {
            # Python 依赖
            "python": DependencyRequirement(
                name="python",
                dependency_type=DependencyType.EXTERNAL_TOOL,
                min_version="3.8",
                required=True,
                check_command="python --version",
                version_extract_pattern=r"Python (\d+\.\d+\.\d+)"
            ),
            "pip": DependencyRequirement(
                name="pip",
                dependency_type=DependencyType.SYSTEM_PACKAGE,
                required=True,
                check_command="pip --version",
                version_extract_pattern=r"pip (\d+\.\d+\.\d+)"
            ),
            "psutil": DependencyRequirement(
                name="psutil",
                dependency_type=DependencyType.PYTHON_PACKAGE,
                required=True,
                install_command="pip install psutil"
            ),
            "rich": DependencyRequirement(
                name="rich",
                dependency_type=DependencyType.PYTHON_PACKAGE,
                required=True,
                install_command="pip install rich"
            ),
            "requests": DependencyRequirement(
                name="requests",
                dependency_type=DependencyType.PYTHON_PACKAGE,
                required=True,
                install_command="pip install requests"
            ),

            # Node.js 依赖
            "node": DependencyRequirement(
                name="node",
                dependency_type=DependencyType.EXTERNAL_TOOL,
                min_version="16.0.0",
                required=True,
                check_command="node --version",
                version_extract_pattern=r"v(\d+\.\d+\.\d+)"
            ),
            "npm": DependencyRequirement(
                name="npm",
                dependency_type=DependencyType.EXTERNAL_TOOL,
                required=True,
                check_command="npm --version",
                version_extract_pattern=r"(\d+\.\d+\.\d+)"
            ),

            # 开发工具
            "git": DependencyRequirement(
                name="git",
                dependency_type=DependencyType.EXTERNAL_TOOL,
                required=True,
                check_command="git --version",
                version_extract_pattern=r"git version (\d+\.\d+\.\d+)"
            ),

            # 数据库服务
            "redis": DependencyRequirement(
                name="redis",
                dependency_type=DependencyType.SERVICE,
                required=False,
                check_command="redis-server --version",
                version_extract_pattern=r"Redis server v=(\d+\.\d+\.\d+)"
            ),

            # PostgreSQL数据库
            "postgresql": DependencyRequirement(
                name="postgresql",
                dependency_type=DependencyType.SERVICE,
                required=False,
                check_command="psql --version",
                version_extract_pattern=r"psql \(PostgreSQL\) (\d+\.\d+)"
            )
        }

    async def check_and_install_dependencies(self) -> EnvironmentCheckResult:
        """检查并安装所有依赖"""
        start_time = time.time()

        try:
            # 检测系统环境
            self.system_info = await self._detect_system_environment()

            if not self.system_info:
                return EnvironmentCheckResult(
                    False, None, [], [], time.time() - start_time,
                    "无法检测系统环境"
                )

            # 检查所有依赖
            dependency_results = await self._check_all_dependencies()

            # 安装缺失的依赖
            await self._install_missing_dependencies(dependency_results)

            # 重新检查缺失的依赖
            missing_required = [
                result.dependency_name for result in dependency_results
                if result.status in [InstallationStatus.NOT_INSTALLED, InstallationStatus.FAILED]
                and self.requirements[result.dependency_name].required
            ]

            success = len(missing_required) == 0

            return EnvironmentCheckResult(
                success=success,
                system_info=self.system_info,
                dependency_results=dependency_results,
                missing_required=missing_required,
                total_time=time.time() - start_time
            )

        except Exception as e:
            logger.error(f"依赖检查安装失败: {str(e)}")
            return EnvironmentCheckResult(
                False, None, [], [], time.time() - start_time,
                f"依赖安装错误: {str(e)}"
            )

    async def _detect_system_environment(self) -> Optional[SystemInfo]:
        """检测系统环境"""
        try:
            # 获取基本系统信息
            system_info = self.env_detector.detect_all()

            # 检测操作系统详细信息
            os_info = self.os_detector.detect_system()

            logger.info(f"系统环境: {system_info.platform} {system_info.python_version}")
            return system_info

        except Exception as e:
            logger.error(f"环境检测失败: {str(e)}")
            return None

    async def _check_all_dependencies(self) -> List[InstallationResult]:
        """检查所有依赖"""
        results = []

        for name, requirement in self.requirements.items():
            try:
                result = await self._check_single_dependency(requirement)
                results.append(result)
            except Exception as e:
                logger.error(f"检查依赖 {name} 出错: {str(e)}")
                results.append(InstallationResult(
                    dependency_name=name,
                    status=InstallationStatus.FAILED,
                    error_message=str(e)
                ))

        return results

    async def _check_single_dependency(self, requirement: DependencyRequirement) -> InstallationResult:
        """检查单个依赖"""
        start_time = time.time()

        try:
            if requirement.dependency_type == DependencyType.PYTHON_PACKAGE:
                return await self._check_python_package(requirement)
            elif requirement.dependency_type == DependencyType.EXTERNAL_TOOL:
                return await self._check_external_tool(requirement)
            elif requirement.dependency_type == DependencyType.SERVICE:
                return await self._check_service(requirement)
            else:
                return InstallationResult(
                    dependency_name=requirement.name,
                    status=InstallationStatus.SKIPPED,
                    error_message=f"未知依赖类型: {requirement.dependency_type}"
                )

        except Exception as e:
            logger.error(f"检查依赖 {requirement.name} 出错: {str(e)}")
            return InstallationResult(
                dependency_name=requirement.name,
                status=InstallationStatus.FAILED,
                error_message=str(e),
                install_time=time.time() - start_time
            )

    async def _check_python_package(self, requirement: DependencyRequirement) -> InstallationResult:
        """检查 Python 包"""
        try:
            # 使用 importlib 检查包是否安装
            import importlib

            try:
                module = importlib.import_module(requirement.name)
                version = getattr(module, '__version__', None)

                if version:
                    status = InstallationStatus.INSTALLED
                else:
                    status = InstallationStatus.INSTALLED  # 即使没有版本号也算安装
                    version = "unknown"

                return InstallationResult(
                    dependency_name=requirement.name,
                    status=status,
                    version=version
                )

            except ImportError:
                return InstallationResult(
                    dependency_name=requirement.name,
                    status=InstallationStatus.NOT_INSTALLED
                )

        except Exception as e:
            return InstallationResult(
                dependency_name=requirement.name,
                status=InstallationStatus.FAILED,
                error_message=str(e)
            )

    async def _check_external_tool(self, requirement: DependencyRequirement) -> InstallationResult:
        """检查外部工具"""
        try:
            if not requirement.check_command:
                return InstallationResult(
                    dependency_name=requirement.name,
                    status=InstallationStatus.FAILED,
                    error_message="缺少检查命令"
                )

            # 执行检查命令
            process = await asyncio.create_subprocess_shell(
                requirement.check_command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                output = stdout.decode('utf-8', errors='ignore')

                # 提取版本信息
                version = None
                if requirement.version_extract_pattern:
                    import re
                    match = re.search(requirement.version_extract_pattern, output)
                    if match:
                        version = match.group(1)

                return InstallationResult(
                    dependency_name=requirement.name,
                    status=InstallationStatus.INSTALLED,
                    version=version or "unknown"
                )
            else:
                return InstallationResult(
                    dependency_name=requirement.name,
                    status=InstallationStatus.NOT_INSTALLED
                )

        except Exception as e:
            return InstallationResult(
                dependency_name=requirement.name,
                status=InstallationStatus.FAILED,
                error_message=str(e)
            )

    async def _check_service(self, requirement: DependencyRequirement) -> InstallationResult:
        """检查系统服务"""
        try:
            if not requirement.check_command:
                return InstallationResult(
                    dependency_name=requirement.name,
                    status=InstallationStatus.FAILED,
                    error_message="缺少检查命令"
                )

            # 执行检查命令
            process = await asyncio.create_subprocess_shell(
                requirement.check_command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                output = stdout.decode('utf-8', errors='ignore')

                # 提取版本信息
                version = None
                if requirement.version_extract_pattern:
                    import re
                    match = re.search(requirement.version_extract_pattern, output)
                    if match:
                        version = match.group(1)

                return InstallationResult(
                    dependency_name=requirement.name,
                    status=InstallationStatus.INSTALLED,
                    version=version or "unknown"
                )
            else:
                return InstallationResult(
                    dependency_name=requirement.name,
                    status=InstallationStatus.NOT_INSTALLED
                )

        except Exception as e:
            return InstallationResult(
                dependency_name=requirement.name,
                status=InstallationStatus.FAILED,
                error_message=str(e)
            )

    async def _install_missing_dependencies(self, dependency_results: List[InstallationResult]):
        """安装缺失的依赖"""
        for result in dependency_results:
            if result.status == InstallationStatus.NOT_INSTALLED:
                requirement = self.requirements.get(result.dependency_name)

                if requirement and requirement.required and requirement.install_command:
                    logger.info(f"尝试安装缺失依赖: {requirement.name}")
                    install_result = await self._install_single_dependency(requirement)

                    # 更新结果
                    result.status = install_result.status
                    result.version = install_result.version
                    result.error_message = install_result.error_message
                    result.install_time = install_result.install_time

    async def _install_single_dependency(self, requirement: DependencyRequirement) -> InstallationResult:
        """安装单个依赖"""
        start_time = time.time()

        try:
            if not requirement.install_command:
                return InstallationResult(
                    dependency_name=requirement.name,
                    status=InstallationStatus.FAILED,
                    error_message="缺少安装命令"
                )

            logger.info(f"执行安装命令: {requirement.install_command}")

            # 执行安装命令
            process = await asyncio.create_subprocess_shell(
                requirement.install_command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                logger.info(f"依赖 {requirement.name} 安装成功")

                # 重新检查版本信息
                check_result = await self._check_single_dependency(requirement)

                return InstallationResult(
                    dependency_name=requirement.name,
                    status=InstallationStatus.INSTALLED,
                    version=check_result.version,
                    install_time=time.time() - start_time
                )
            else:
                error_output = stderr.decode('utf-8', errors='ignore')
                logger.error(f"依赖 {requirement.name} 安装失败: {error_output}")

                return InstallationResult(
                    dependency_name=requirement.name,
                    status=InstallationStatus.FAILED,
                    error_message=f"安装失败: {error_output}",
                    install_time=time.time() - start_time
                )

        except Exception as e:
            logger.error(f"安装依赖 {requirement.name} 出错: {str(e)}")
            return InstallationResult(
                dependency_name=requirement.name,
                status=InstallationStatus.FAILED,
                error_message=str(e),
                install_time=time.time() - start_time
            )

    def get_dependency_status(self) -> Dict[str, Any]:
        """获取依赖状态信息"""
        if not self.system_info:
            return {"error": "未获取系统信息"}

        return {
            "system": {
                "platform": self.system_info.platform,
                "architecture": self.system_info.architecture,
                "python_version": self.system_info.python_version
            },
            "dependencies_count": len(self.requirements),
            "required_dependencies": len([r for r in self.requirements.values() if r.required])
        }

    async def validate_environment(self) -> bool:
        """验证环境是否满足基本要求"""
        try:
            # 检查 Python 版本
            python_version = self.system_info.python_version if self.system_info else None
            if not python_version:
                return False

            # 检查版本要求
            version_parts = python_version.split('.')
            if len(version_parts) >= 2:
                major = int(version_parts[0])
                minor = int(version_parts[1])

                if major < 3 or (major == 3 and minor < 8):
                    return False

            return True

        except Exception:
            return False