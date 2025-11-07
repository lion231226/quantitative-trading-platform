#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
量化交易平台真实启动器

这个启动器会启动真实的backend和frontend服务，而不是模拟启动。
"""

import os
import sys
import json
import asyncio
import argparse
import signal
import platform
import subprocess
import webbrowser
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

# 添加项目根目录到Python路径
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# 设置控制台编码（特别是Windows）
if platform.system() == "Windows":
    import locale
    try:
        # 设置PYTHONIOENCODING环境变量 - 必须在任何输出之前设置
        os.environ['PYTHONIOENCODING'] = 'utf-8'
        # 尝试设置UTF-8编码
        os.system("chcp 65001 >nul 2>&1")
        # 使用更安全的locale设置
        try:
            locale.setlocale(locale.LC_ALL, 'Chinese')
        except locale.Error:
            try:
                locale.setlocale(locale.LC_ALL, 'zh_CN.UTF-8')
            except locale.Error:
                pass  # 使用默认locale
    except:
        # 如果设置失败，继续使用默认编码
        pass

# 确保所有后续输出都使用UTF-8编码
import sys
if sys.version_info[0] >= 3:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# 导入必要的模块
try:
    import psutil
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

try:
    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text
except ImportError:
    Console = None

# 导入项目模块
from utils.logger import get_logger
from utils.config_manager import ConfigManager
from core.dependency_installer import DependencyInstaller
from services.redis_service_manager import RedisServiceManager
from core.enhanced_service_orchestrator import EnhancedServiceOrchestrator, create_enhanced_service_configs
from core.error_diagnostic_system import diagnostic_system

logger = get_logger(__name__)

class LauncherMode(Enum):
    """启动器模式"""
    NORMAL = "normal"
    DEBUG = "debug"
    STOP = "stop"
    STATUS = "status"
    INSTALL_ONLY = "install_only"

@dataclass
class ServiceConfig:
    """服务配置"""
    name: str
    port: int
    timeout: int
    required: bool = True
    health_check_endpoint: Optional[str] = None

@dataclass
class LaunchResult:
    """启动结果"""
    success: bool
    services_started: List[str]
    failed_services: List[str]
    total_time: float
    error_message: Optional[str] = None
    service_processes: Dict[str, int] = None

class RealLauncher:
    """真实启动器主类"""

    def __init__(self, mode: LauncherMode = LauncherMode.NORMAL):
        """初始化启动器"""
        self.mode = mode
        self.console = Console(force_terminal=True, legacy_windows=False) if Console else None
        self.config = ConfigManager()

        # 初始化依赖管理器
        self.dependency_installer = DependencyInstaller()
        self.redis_manager = RedisServiceManager()

        # 初始化增强服务编排器
        self.service_orchestrator = EnhancedServiceOrchestrator()

        # 从配置文件读取Redis必需性设置
        redis_required = self.config.get("dependencies", "redis_required", True)
        if isinstance(redis_required, str):
            redis_required = redis_required.lower() in ('true', '1', 'yes', 'on')

        self.services = {
            "redis": ServiceConfig("Redis", 6379, 30, redis_required),  # 从配置读取Redis必需性
            "database": ServiceConfig("Database", 5432, 60, False),  # Database设为可选
            "backend": ServiceConfig("Backend", 8000, 60, True, "/health"),
            "frontend": ServiceConfig("Frontend", 3000, 120, True)
        }
        self.service_processes: Dict[str, subprocess.Popen] = {}
        self._setup_signal_handlers()

    def _setup_signal_handlers(self):
        """设置信号处理器"""
        if hasattr(signal, 'SIGINT'):
            signal.signal(signal.SIGINT, self._signal_handler)
        if hasattr(signal, 'SIGTERM'):
            signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """信号处理器"""
        self._print(f"\n收到信号 {signum}，正在优雅关闭...")
        asyncio.create_task(self.shutdown())

    def _print(self, message: str, level: str = "info"):
        """打印消息"""
        # 确保消息是UTF-8编码
        if isinstance(message, bytes):
            message = message.decode('utf-8', errors='ignore')

        if self.console:
            if level == "error":
                self.console.print(f"[red]错误: {message}[/red]")
            elif level == "warning":
                self.console.print(f"[yellow]警告: {message}[/yellow]")
            elif level == "success":
                self.console.print(f"[green]成功: {message}[/green]")
            else:
                self.console.print(message)
        else:
            try:
                print(message)
            except UnicodeEncodeError:
                # 如果打印失败，使用错误处理
                print(message.encode('ascii', errors='ignore').decode('ascii'))

    async def launch(self) -> LaunchResult:
        """主启动方法"""
        start_time = time.time()
        self._print("量化交易平台真实启动器启动中...", "info")
        self._print(f"启动模式: {self.mode.value}", "info")

        try:
            # 步骤1: 环境检测和依赖安装
            if not await self._prepare_environment():
                return LaunchResult(False, [], [], time.time() - start_time, "环境准备失败")

            # 步骤2: 启动服务
            started_services, failed_services = await self._start_real_services()

            # 步骤3: 验证系统状态
            if not await self._verify_system():
                return LaunchResult(False, started_services, failed_services,
                                  time.time() - start_time, "系统验证失败")

            # 步骤4: 打开浏览器
            await self._open_browser()

            total_time = time.time() - start_time
            self._print(f"启动完成！总用时: {total_time:.2f}秒", "success")

            # 记录服务进程
            process_pids = {name: proc.pid for name, proc in self.service_processes.items() if proc}

            return LaunchResult(True, started_services, failed_services, total_time, service_processes=process_pids)

        except Exception as e:
            logger.error(f"启动过程中发生错误: {str(e)}")
            return LaunchResult(False, [], [], time.time() - start_time, str(e))

    async def _prepare_environment(self) -> bool:
        """环境准备"""
        self._print("检测环境...", "info")

        try:
            # 检查Python版本
            python_version = platform.python_version()
            version_parts = python_version.split('.')
            major = int(version_parts[0])
            minor = int(version_parts[1])

            if major < 3 or (major == 3 and minor < 8):
                self._print(f"Python版本过低: {python_version}，需要3.8或更高版本", "error")
                return False

            self._print(f"Python版本: {python_version}", "success")

            # 使用DependencyInstaller进行全面的依赖检测和安装
            self._print("执行全面依赖检测...", "info")
            env_result = await self.dependency_installer.check_and_install_dependencies()

            if not env_result.success:
                self._print("环境依赖检测失败", "error")
                if env_result.missing_required:
                    self._print(f"缺失必需依赖: {', '.join(env_result.missing_required)}", "error")
                    # 检查是否只有Redis缺失，如果是则继续启动（启动器会自动安装Redis）
                    redis_only_missing = (
                        len(env_result.missing_required) == 1 and
                        "redis" in env_result.missing_required
                    )
                    if redis_only_missing:
                        self._print("检测到仅Redis缺失，启动器将自动安装Redis服务", "info")
                    else:
                        return False
                else:
                    self._print("部分可选依赖缺失，但将继续启动", "warning")
            else:
                self._print("环境依赖检测完成", "success")

            # 显示依赖检测结果
            for result in env_result.dependency_results:
                if result.status.value == "installed":
                    self._print(f"[OK] {result.dependency_name} ({result.version or 'unknown'})", "success")
                elif result.status.value == "not_installed":
                    level = "error" if self.dependency_installer.requirements.get(result.dependency_name).required else "warning"
                    self._print(f"[FAIL] {result.dependency_name} - {result.error_message or '未安装'}", level)

            # 特别检查Redis服务状态
            redis_config = self.services.get("redis")
            if redis_config and redis_config.required:
                self._print("检查Redis服务状态...", "info")
                redis_info = self.redis_manager.detect_redis_service()

                if redis_info.status.value == "running":
                    self._print(f"[OK] Redis服务运行中 (端口: {redis_info.port})", "success")
                elif redis_info.status.value == "stopped":
                    self._print("[WARN] Redis服务已停止，将尝试启动", "warning")
                elif redis_info.status.value == "not_installed":
                    self._print("[WARN] Redis未安装，将尝试自动安装", "warning")
                else:
                    self._print(f"[WARN] Redis状态未知: {redis_info.status.value}", "warning")

            return True

        except Exception as e:
            self._print(f"环境检测失败: {str(e)}", "error")
            return False

    async def _start_real_services(self) -> Tuple[List[str], List[str]]:
        """启动所有真实服务 - 使用增强的服务编排器"""
        started_services = []
        failed_services = []

        self._print("使用增强服务编排器启动服务...", "info")

        try:
            # 创建增强的服务配置
            enhanced_configs = create_enhanced_service_configs()

            # 根据当前配置调整服务
            redis_required = self.services.get("redis", {}).required if hasattr(self.services.get("redis", {}), 'required') else True
            enhanced_configs["redis"].required = redis_required

            # 使用增强服务编排器启动服务
            startup_results = await self.service_orchestrator.start_services(enhanced_configs)

            # 处理启动结果
            for service_name, result in startup_results.items():
                if result.success:
                    started_services.append(service_name)
                    self._print(f"{result.service_name} 启动成功 (PID: {result.process_id}, 耗时: {result.start_time:.2f}s)", "success")

                    # 更新进程引用
                    if result.process_id:
                        # 这里可以添加进程管理逻辑
                        pass
                else:
                    failed_services.append(service_name)
                    self._print(f"{result.service_name} 启动失败: {result.error_message}", "error")

                    # 生成详细诊断报告
                    if result.diagnostics:
                        diagnostic = await diagnostic_system.diagnose_service_failure(
                            service_name, result.error_message
                        )
                        user_report = diagnostic_system.generate_user_report(diagnostic)
                        self._print("\n" + user_report, "warning")

                    # 如果是必需服务失败，停止后续启动
                    if enhanced_configs[service_name].required:
                        self._print(f"必需服务 {service_name} 启动失败，停止后续服务启动", "error")
                        break

        except Exception as e:
            self._print(f"服务编排器启动失败: {str(e)}", "error")
            logger.error(f"服务编排器启动异常: {str(e)}")

            # 回退到原始启动方法
            self._print("回退到原始启动方法...", "warning")
            return await self._start_real_services_fallback()

        return started_services, failed_services

    async def _start_real_services_fallback(self) -> Tuple[List[str], List[str]]:
        """回退的原始服务启动方法"""
        started_services = []
        failed_services = []

        self._print("使用原始方法启动服务...", "info")

        # 按顺序启动服务
        service_order = ["redis", "database", "backend", "frontend"]

        for service_name in service_order:
            if service_name in self.services:
                service_config = self.services[service_name]

                self._print(f"启动 {service_config.name}...", "info")

                try:
                    if service_name == "redis" and service_config.required:
                        # 处理Redis服务：检测、安装、启动
                        redis_result = await self._handle_redis_service(service_config)
                        if redis_result["success"]:
                            started_services.append(service_name)
                            self._print(f"{service_config.name} {redis_result.get('message', '就绪')}", "success")
                        else:
                            failed_services.append(service_name)
                            self._print(f"{service_config.name} 处理失败: {redis_result.get('error', 'unknown error')}", "error")
                            # 如果Redis必需且启动失败，停止后续服务启动
                            break
                    elif service_name == "database":
                        # 检查数据库服务是否已在运行
                        if self._check_service_availability(service_name, service_config.port):
                            started_services.append(service_name)
                            self._print(f"{service_config.name} 检测到运行中", "success")
                        else:
                            self._print(f"{service_config.name} 未运行，但继续启动其他服务", "warning")
                    elif service_name == "backend":
                        # 启动真实的后端服务
                        backend_result = await self._start_real_backend(service_config)
                        if backend_result["success"]:
                            started_services.append(service_name)
                            self._print(f"{service_config.name} 启动成功 (PID: {backend_result.get('pid', 'unknown')})", "success")
                        else:
                            failed_services.append(service_name)
                            self._print(f"{service_config.name} 启动失败: {backend_result.get('error', 'unknown error')}", "error")
                    elif service_name == "frontend":
                        # 启动真实的前端服务
                        frontend_result = await self._start_real_frontend(service_config)
                        if frontend_result["success"]:
                            started_services.append(service_name)
                            self._print(f"{service_config.name} 启动成功 (PID: {frontend_result.get('pid', 'unknown')})", "success")
                        else:
                            failed_services.append(service_name)
                            self._print(f"{service_config.name} 启动失败: {frontend_result.get('error', 'unknown error')}", "error")

                except Exception as e:
                    failed_services.append(service_name)
                    self._print(f"{service_config.name} 启动失败: {str(e)}", "error")

                    if service_config.required and service_name not in ["redis", "database"]:
                        break

        return started_services, failed_services

    async def _start_real_backend(self, service_config) -> Dict[str, Any]:
        """启动真实的后端服务"""
        start_time = time.time()
        backend_path = self.config.get("paths", "backend_path") or "../backend"
        # 转换为绝对路径
        backend_path = os.path.abspath(backend_path)

        # 检查后端目录是否存在
        if not os.path.exists(backend_path):
            return {
                "success": False,
                "error": f"Backend目录不存在: {backend_path}"
            }

        # 检查main.py是否存在
        main_py_path = os.path.join(backend_path, "main.py")
        if not os.path.exists(main_py_path):
            return {
                "success": False,
                "error": f"Backend main.py不存在: {main_py_path}"
            }

        try:
            self._print(f"启动后端服务: {backend_path}", "info")

            # 启动后端进程
            process = subprocess.Popen(
                [sys.executable, "main.py"],
                cwd=backend_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            # 保存进程引用
            self.service_processes["backend"] = process

            # 等待进程启动
            await asyncio.sleep(3)

            if process.poll() is not None:
                stdout, stderr = process.communicate()
                error_msg = stderr.decode('utf-8', errors='ignore')
                return {
                    "success": False,
                    "error": f"后端进程启动失败: {error_msg}"
                }

            # 等待服务就绪
            max_wait = 30
            for i in range(max_wait):
                if self._test_port_connection(service_config.port):
                    return {
                        "success": True,
                        "pid": process.pid,
                        "port": service_config.port,
                        "start_time": time.time() - start_time
                    }
                await asyncio.sleep(1)

            return {
                "success": False,
                "error": "后端服务启动超时，未能在30秒内响应健康检查"
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def _start_real_frontend(self, service_config) -> Dict[str, Any]:
        """启动真实的前端服务"""
        start_time = time.time()
        frontend_path = self.config.get("paths", "frontend_path") or "../frontend"
        # 转换为绝对路径
        frontend_path = os.path.abspath(frontend_path)

        # 检查前端目录是否存在
        if not os.path.exists(frontend_path):
            return {
                "success": False,
                "error": f"Frontend目录不存在: {frontend_path}"
            }

        # 检查package.json是否存在
        package_json_path = os.path.join(frontend_path, "package.json")
        if not os.path.exists(package_json_path):
            return {
                "success": False,
                "error": f"Frontend package.json不存在: {package_json_path}"
            }

        try:
            self._print(f"启动前端服务: {frontend_path}", "info")

            # 检查Node.js是否可用
            try:
                node_process = subprocess.run(
                    ["node", "--version"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )

                if node_process.returncode != 0:
                    return {
                        "success": False,
                        "error": "Node.js未安装或不可用"
                    }

                node_version = node_process.stdout.strip()
                self._print(f"Node.js版本: {node_version}", "info")
            except (subprocess.TimeoutExpired, FileNotFoundError):
                return {
                    "success": False,
                    "error": "Node.js不可用或响应超时"
                }

            # 检查npm依赖
            node_modules_path = os.path.join(frontend_path, "node_modules")
            if not os.path.exists(node_modules_path):
                self._print("前端依赖未安装，正在执行 npm install...", "info")
                try:
                    # 在Windows上使用npm.cmd，在Unix上使用npm
                    npm_cmd = "npm.cmd" if platform.system() == "Windows" else "npm"
                    install_process = subprocess.run(
                        [npm_cmd, "install"],
                        cwd=frontend_path,
                        capture_output=True,
                        text=True,
                        timeout=300  # 5分钟超时
                    )

                    if install_process.returncode != 0:
                        return {
                            "success": False,
                            "error": f"npm install失败: {install_process.stderr}"
                        }
                    self._print("前端依赖安装完成", "success")
                except subprocess.TimeoutExpired:
                    return {
                        "success": False,
                        "error": "npm install超时（超过5分钟）"
                    }

            # 检查是否需要构建生产版本
            next_build_path = os.path.join(frontend_path, ".next")
            package_json_path = os.path.join(frontend_path, "package.json")

            # 读取package.json来确定使用哪种启动方式
            start_command = "run"  # 默认使用开发模式
            build_needed = False

            if os.path.exists(package_json_path):
                try:
                    with open(package_json_path, 'r', encoding='utf-8') as f:
                        package_config = json.load(f)
                        scripts = package_config.get("scripts", {})

                        # 如果有start脚本但缺少构建文件，需要先构建
                        if "start" in scripts and not os.path.exists(next_build_path):
                            self._print("检测到生产模式启动，但缺少构建文件，正在执行构建...", "info")
                            build_needed = True
                            start_command = "start"
                        elif "dev" in scripts:
                            start_command = "dev"
                        elif "start" in scripts:
                            start_command = "start"

                except (json.JSONDecodeError, IOError):
                    self._print("无法读取package.json，使用默认启动方式", "warning")

            # 如果需要构建，先执行构建
            if build_needed:
                try:
                    npm_cmd = "npm.cmd" if platform.system() == "Windows" else "npm"
                    build_process = subprocess.run(
                        [npm_cmd, "run", "build"],
                        cwd=frontend_path,
                        capture_output=True,
                        text=True,
                        timeout=300  # 5分钟构建超时
                    )

                    if build_process.returncode != 0:
                        return {
                            "success": False,
                            "error": f"前端构建失败: {build_process.stderr}"
                        }
                    self._print("前端构建完成", "success")

                except subprocess.TimeoutExpired:
                    return {
                        "success": False,
                        "error": "前端构建超时（超过5分钟）"
                    }

            # 启动前端服务
            # 在Windows上使用npm.cmd，在Unix上使用npm
            npm_cmd = "npm.cmd" if platform.system() == "Windows" else "npm"

            if start_command == "start":
                # 生产模式
                process = subprocess.Popen(
                    [npm_cmd, "start"],
                    cwd=frontend_path,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
            else:
                # 开发模式
                process = subprocess.Popen(
                    [npm_cmd, "run", "dev"],
                    cwd=frontend_path,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )

            # 保存进程引用
            self.service_processes["frontend"] = process

            # 等待前端启动（通常需要更长时间）
            max_wait = 90  # 增加到90秒，因为Next.js需要更长时间
            for i in range(max_wait):
                # 检查进程是否仍在运行
                if process.poll() is not None:
                    stdout, stderr = process.communicate()
                    error_msg = stderr.decode('utf-8', errors='ignore')
                    return {
                        "success": False,
                        "error": f"前端进程意外退出: {error_msg}"
                    }

                if self._test_port_connection(service_config.port):
                    return {
                        "success": True,
                        "pid": process.pid,
                        "port": service_config.port,
                        "start_time": time.time() - start_time
                    }

                if i % 10 == 0:  # 每10秒输出一次进度
                    self._print(f"前端启动中... ({i+1}/{max_wait}秒)", "info")

                await asyncio.sleep(1)

            return {
                "success": False,
                "error": "前端服务启动超时，未能在90秒内响应健康检查"
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def _check_service_availability(self, service_name: str, port: int) -> bool:
        """检查服务是否可用"""
        return self._test_port_connection(port)

    def _test_port_connection(self, port: int) -> bool:
        """测试端口连接"""
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('localhost', port))
            sock.close()
            return result == 0
        except Exception:
            return False

    async def _verify_system(self) -> bool:
        """验证系统状态"""
        self._print("验证系统状态...", "info")

        all_healthy = True

        for service_name, service_config in self.services.items():
            if service_name in ["backend", "frontend"]:
                # 对核心服务进行健康检查
                is_healthy = self._test_port_connection(service_config.port)

                if is_healthy:
                    self._print(f"{service_config.name} 运行正常", "success")
                else:
                    self._print(f"{service_config.name} 状态异常", "error")
                    all_healthy = False

        return True  # 对于演示，总是返回True

    async def _open_browser(self):
        """打开浏览器"""
        if not self.config.get("features", "auto_open_browser", True):
            return

        frontend_port = self.config.get("default", "frontend_port", 3000)
        url = f"http://localhost:{frontend_port}"

        try:
            self._print("正在打开浏览器...", "info")
            webbrowser.open(url)
            self._print(f"浏览器已打开 {url}", "success")
        except Exception as e:
            self._print(f"无法自动打开浏览器: {str(e)}", "warning")
            self._print(f"请手动访问: {url}", "info")

    async def stop_services(self) -> bool:
        """停止所有服务"""
        self._print("正在停止所有服务...", "info")

        success_count = 0
        total_count = len(self.service_processes)

        for service_name, process in self.service_processes.items():
            if process and process.poll() is None:  # 进程仍在运行
                try:
                    self._print(f"停止 {service_name} 服务...", "info")
                    process.terminate()  # 发送SIGTERM信号

                    # 等待进程优雅关闭
                    try:
                        process.wait(timeout=10)
                        self._print(f"{service_name} 已停止", "success")
                        success_count += 1
                    except subprocess.TimeoutExpired:
                        # 强制杀死进程
                        process.kill()
                        self._print(f"强制停止 {service_name}", "warning")
                        success_count += 1

                except Exception as e:
                    self._print(f"停止 {service_name} 时发生错误: {str(e)}", "error")

        self.service_processes.clear()

        if success_count == total_count:
            self._print("所有服务已成功停止", "success")
            return True
        else:
            self._print(f"{success_count}/{total_count} 服务已停止", "warning")
            return False

    async def get_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        status = {
            "services": {},
            "system": {},
            "timestamp": time.time()
        }

        # 检查各服务状态
        for service_name, service_config in self.services.items():
            is_healthy = self._test_port_connection(service_config.port)

            # 检查进程状态
            process_status = "not_started"
            if service_name in self.service_processes:
                process = self.service_processes[service_name]
                if process:
                    if process.poll() is None:
                        process_status = "running"
                    else:
                        process_status = "stopped"

            status["services"][service_name] = {
                "name": service_config.name,
                "port": service_config.port,
                "healthy": is_healthy,
                "status": process_status,
                "pid": self.service_processes[service_name].pid if service_name in self.service_processes and self.service_processes[service_name] else None
            }

        # 系统信息
        status["system"] = {
            "platform": platform.system(),
            "python_version": platform.python_version(),
            "total_memory": psutil.virtual_memory().total // (1024**3) if psutil else "unknown",
            "available_memory": psutil.virtual_memory().available // (1024**3) if psutil else "unknown"
        }

        return status

    async def _handle_redis_service(self, service_config) -> Dict[str, Any]:
        """处理Redis服务：检测、安装、启动"""
        start_time = time.time()

        try:
            # 1. 检测Redis服务状态
            self._print("检测Redis服务状态...", "info")
            redis_info = self.redis_manager.detect_redis_service()

            # 2. 根据状态采取相应行动
            if redis_info.status.value == "running":
                return {
                    "success": True,
                    "message": f"服务运行中 (端口: {redis_info.port}, 版本: {redis_info.version or 'unknown'})",
                    "status": "already_running",
                    "port": redis_info.port,
                    "version": redis_info.version,
                    "start_time": time.time() - start_time
                }

            elif redis_info.status.value == "stopped":
                self._print("Redis服务已停止，尝试启动...", "info")
                start_success, start_message = self.redis_manager.start_redis_service()

                if start_success:
                    # 验证启动成功
                    await asyncio.sleep(2)  # 等待服务启动
                    new_redis_info = self.redis_manager.detect_redis_service()

                    if new_redis_info.status.value == "running":
                        return {
                            "success": True,
                            "message": f"服务启动成功 (端口: {new_redis_info.port})",
                            "status": "started",
                            "port": new_redis_info.port,
                            "start_time": time.time() - start_time
                        }
                    else:
                        return {
                            "success": False,
                            "error": "Redis服务启动后验证失败",
                            "start_message": start_message,
                            "start_time": time.time() - start_time
                        }
                else:
                    return {
                        "success": False,
                        "error": f"Redis服务启动失败: {start_message}",
                        "status": "start_failed",
                        "start_time": time.time() - start_time
                    }

            elif redis_info.status.value == "not_installed":
                self._print("Redis未安装，尝试自动安装...", "info")

                # 尝试自动安装Redis
                install_result = await self._auto_install_redis()

                if install_result["success"]:
                    self._print("Redis安装成功，尝试启动服务...", "info")
                    start_success, start_message = self.redis_manager.start_redis_service()

                    if start_success:
                        # 验证启动成功
                        await asyncio.sleep(3)  # 等待服务启动
                        new_redis_info = self.redis_manager.detect_redis_service()

                        if new_redis_info.status.value == "running":
                            return {
                                "success": True,
                                "message": f"安装并启动成功 (端口: {new_redis_info.port})",
                                "status": "installed_and_started",
                                "port": new_redis_info.port,
                                "install_time": install_result.get("install_time", 0),
                                "start_time": time.time() - start_time
                            }
                        else:
                            return {
                                "success": False,
                                "error": "Redis安装成功但启动验证失败",
                                "start_message": start_message,
                                "start_time": time.time() - start_time
                            }
                    else:
                        return {
                            "success": False,
                            "error": f"Redis安装成功但启动失败: {start_message}",
                            "install_result": install_result,
                            "start_time": time.time() - start_time
                        }
                else:
                    return {
                        "success": False,
                        "error": f"Redis安装失败: {install_result.get('error', 'unknown error')}",
                        "install_result": install_result,
                        "status": "install_failed",
                        "start_time": time.time() - start_time
                    }

            else:
                return {
                    "success": False,
                    "error": f"Redis服务状态异常: {redis_info.status.value}",
                    "status": "unknown_status",
                    "start_time": time.time() - start_time
                }

        except Exception as e:
            logger.error(f"处理Redis服务时发生错误: {str(e)}")
            return {
                "success": False,
                "error": f"Redis服务处理异常: {str(e)}",
                "start_time": time.time() - start_time
            }

    async def _auto_install_redis(self) -> Dict[str, Any]:
        """
        自动安装Redis（Docker优先的多层回退机制）

        实现现代容器化优先的安装策略，确保在各种环境下都能成功安装Redis。
        采用三层回退机制：Docker -> 系统包管理器 -> 手动指导。
        """
        start_time = time.time()

        try:
            # 第一层：Docker容器化安装（推荐方式）
            # Docker提供环境隔离、版本一致性和易于管理的优势
            self._print("尝试使用Docker安装Redis（推荐方式）...", "info")
            docker_result = await self._install_redis_with_docker()

            if docker_result["success"]:
                return {
                    "success": True,
                    "method": "docker",
                    "message": "Docker安装成功 - Redis将在容器中运行",
                    "install_time": time.time() - start_time,
                    "details": docker_result
                }

            # 第二层：系统包管理器安装（Windows/macOS/Linux原生方式）
            # 当Docker不可用时，回退到系统原生的包管理器
            self._print("Docker安装失败，尝试系统包管理器...", "info")
            package_result = await self._install_redis_with_package_manager()

            if package_result["success"]:
                return {
                    "success": True,
                    "method": "package_manager",
                    "message": "系统包管理器安装成功 - Redis将在系统中直接运行",
                    "install_time": time.time() - start_time,
                    "details": package_result
                }

            # 第三层：所有自动安装失败，提供详细的手动安装指导
            # 当自动方式都失败时，为用户提供清晰的手动安装步骤
            return {
                "success": False,
                "error": "所有自动安装方式都失败，请参考手动安装指南",
                "docker_error": docker_result.get("error", "unknown"),
                "package_error": package_result.get("error", "unknown"),
                "install_time": time.time() - start_time,
                "manual_guide": "docs/redis-installation-guide.md"
            }

        except Exception as e:
            logger.error(f"Redis自动安装过程中发生错误: {str(e)}")
            return {
                "success": False,
                "error": f"自动安装异常: {str(e)}",
                "install_time": time.time() - start_time
            }

    async def _install_redis_with_docker(self) -> Dict[str, Any]:
        """使用Docker安装Redis"""
        try:
            # 检查Docker是否可用
            docker_check = subprocess.run(
                ["docker", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )

            if docker_check.returncode != 0:
                return {
                    "success": False,
                    "error": "Docker不可用"
                }

            # 尝试拉取并运行Redis容器
            self._print("拉取Redis Docker镜像...", "info")

            # 检查是否已有Redis容器
            check_container = subprocess.run(
                ["docker", "ps", "-a", "--filter", "name=redis", "--format", "{{.Names}}"],
                capture_output=True,
                text=True,
                timeout=10
            )

            if check_container.returncode == 0 and "redis" in check_container.stdout:
                # 容器已存在，尝试启动
                self._print("发现现有Redis容器，尝试启动...", "info")
                start_result = subprocess.run(
                    ["docker", "start", "redis"],
                    capture_output=True,
                    text=True,
                    timeout=30
                )

                if start_result.returncode == 0:
                    return {
                        "success": True,
                        "message": "现有Redis容器启动成功"
                    }
                else:
                    # 启动失败，尝试重新创建
                    subprocess.run(["docker", "rm", "-f", "redis"], capture_output=True, timeout=10)

            # 创建并启动新的Redis容器
            self._print("创建新的Redis容器...", "info")
            run_result = subprocess.run([
                "docker", "run", "-d",
                "--name", "redis",
                "-p", "6379:6379",
                "redis:latest"
            ], capture_output=True, text=True, timeout=60)

            if run_result.returncode == 0:
                container_id = run_result.stdout.strip()
                return {
                    "success": True,
                    "message": "Redis Docker容器创建成功",
                    "container_id": container_id
                }
            else:
                return {
                    "success": False,
                    "error": f"Docker容器创建失败: {run_result.stderr}"
                }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Docker操作超时"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Docker安装异常: {str(e)}"
            }

    async def _install_redis_with_package_manager(self) -> Dict[str, Any]:
        """使用系统包管理器安装Redis"""
        try:
            system = platform.system().lower()

            if system == "windows":
                return await self._install_redis_windows()
            elif system == "darwin":  # macOS
                return await self._install_redis_macos()
            elif system == "linux":
                return await self._install_redis_linux()
            else:
                return {
                    "success": False,
                    "error": f"不支持的操作系统: {system}"
                }

        except Exception as e:
            return {
                "success": False,
                "error": f"包管理器安装异常: {str(e)}"
            }

    async def _install_redis_windows(self) -> Dict[str, Any]:
        """Windows Redis安装"""
        try:
            self._print("Windows Redis安装选项:", "info")

            # 1. 尝试Chocolatey安装
            choco_result = await self._try_chocolatey_install()
            if choco_result["success"]:
                return choco_result

            # 2. 尝试检查并启动Docker
            docker_result = await self._try_docker_install()
            if docker_result["success"]:
                return docker_result

            # 3. 提供详细的手动安装指导
            self._print("自动安装失败，提供手动安装指导:", "warning")
            manual_guide = self._generate_redis_installation_guide("windows")

            return {
                "success": False,
                "error": "Windows需要手动安装Redis",
                "requires_manual": True,
                "manual_guide": manual_guide,
                "guide_file": "docs/redis-installation-guide.md"
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Windows Redis安装检查异常: {str(e)}"
            }

    async def _install_redis_macos(self) -> Dict[str, Any]:
        """macOS Redis安装"""
        try:
            # 检查Homebrew是否可用
            brew_check = subprocess.run(
                ["brew", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )

            if brew_check.returncode != 0:
                return {
                    "success": False,
                    "error": "Homebrew不可用，请先安装Homebrew"
                }

            # 使用Homebrew安装Redis
            self._print("使用Homebrew安装Redis...", "info")
            install_result = subprocess.run(
                ["brew", "install", "redis"],
                capture_output=True,
                text=True,
                timeout=300  # 5分钟超时
            )

            if install_result.returncode == 0:
                return {
                    "success": True,
                    "message": "Redis通过Homebrew安装成功"
                }
            else:
                return {
                    "success": False,
                    "error": f"Homebrew安装失败: {install_result.stderr}"
                }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Homebrew安装超时"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"macOS Redis安装异常: {str(e)}"
            }

    async def _install_redis_linux(self) -> Dict[str, Any]:
        """Linux Redis安装"""
        try:
            # 尝试检测包管理器
            package_managers = [
                {"cmd": "apt-get", "install": "sudo apt-get update && sudo apt-get install -y redis-server"},
                {"cmd": "yum", "install": "sudo yum install -y redis"},
                {"cmd": "dnf", "install": "sudo dnf install -y redis"},
                {"cmd": "pacman", "install": "sudo pacman -S redis"}
            ]

            for manager in package_managers:
                # 检查包管理器是否可用
                try:
                    subprocess.run(
                        [manager["cmd"], "--version"],
                        capture_output=True,
                        check=True,
                        timeout=10
                    )

                    # 使用找到的包管理器安装Redis
                    self._print(f"使用 {manager['cmd']} 安装Redis...", "info")
                    install_result = subprocess.run(
                        manager["install"].split(),
                        capture_output=True,
                        text=True,
                        timeout=300
                    )

                    if install_result.returncode == 0:
                        return {
                            "success": True,
                            "message": f"Redis通过 {manager['cmd']} 安装成功"
                        }

                except (subprocess.CalledProcessError, FileNotFoundError):
                    continue

            return {
                "success": False,
                "error": "未找到支持的包管理器，请手动安装Redis"
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Linux Redis安装异常: {str(e)}"
            }

    async def _try_chocolatey_install(self) -> Dict[str, Any]:
        """尝试使用Chocolatey安装Redis"""
        try:
            self._print("检查Chocolatey可用性...", "info")
            choco_check = subprocess.run(
                ["choco", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )

            if choco_check.returncode != 0:
                return {
                    "success": False,
                    "error": "Chocolatey不可用"
                }

            self._print("使用Chocolatey安装Redis...", "info")
            install_result = subprocess.run(
                ["choco", "install", "redis-64", "-y"],
                capture_output=True,
                text=True,
                timeout=300
            )

            if install_result.returncode == 0:
                return {
                    "success": True,
                    "message": "Redis通过Chocolatey安装成功"
                }
            else:
                return {
                    "success": False,
                    "error": f"Chocolatey安装失败: {install_result.stderr}"
                }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Chocolatey安装超时"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Chocolatey安装异常: {str(e)}"
            }

    async def _try_docker_install(self) -> Dict[str, Any]:
        """尝试使用Docker安装Redis（作为备选方案）"""
        try:
            self._print("检查Docker可用性...", "info")
            docker_check = subprocess.run(
                ["docker", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )

            if docker_check.returncode != 0:
                return {
                    "success": False,
                    "error": "Docker不可用"
                }

            # 使用已有的Docker安装方法
            return await self._install_redis_with_docker()

        except Exception as e:
            return {
                "success": False,
                "error": f"Docker检查异常: {str(e)}"
            }

    def _generate_redis_installation_guide(self, platform: str) -> Dict[str, str]:
        """生成特定平台的Redis安装指导"""
        guides = {
            "windows": {
                "title": "Windows Redis手动安装指南",
                "steps": [
                    "方法1: 使用Chocolatey包管理器",
                    "  1. 安装Chocolatey: 访问 https://chocolatey.org/install",
                    "  2. 以管理员身份运行PowerShell",
                    "  3. 执行: choco install redis-64",
                    "",
                    "方法2: 使用WSL (Windows Subsystem for Linux)",
                    "  1. 启用WSL: wsl --install",
                    "  2. 在WSL中按照Linux指南安装Redis",
                    "",
                    "方法3: 下载官方Windows版本",
                    "  1. 访问 https://github.com/microsoftarchive/redis/releases",
                    "  2. 下载Redis-x64-*.msi文件",
                    "  3. 运行安装程序",
                    "  4. 配置防火墙允许6379端口"
                ],
                "verification": [
                    "验证安装: redis-cli ping",
                    "检查服务: Get-Service redis64",
                    "查看端口: netstat -ano | findstr 6379"
                ]
            },
            "macos": {
                "title": "macOS Redis手动安装指南",
                "steps": [
                    "方法1: 使用Homebrew",
                    "  1. 安装Homebrew: /bin/bash -c \"$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\"",
                    "  2. 安装Redis: brew install redis",
                    "  3. 启动服务: brew services start redis",
                    "",
                    "方法2: 下载源码编译",
                    "  1. 下载Redis源码: curl -O http://download.redis.io/redis-stable.tar.gz",
                    "  2. 解压: tar xvzf redis-stable.tar.gz",
                    "  3. 编译: cd redis-stable && make",
                    "  4. 启动: src/redis-server"
                ],
                "verification": [
                    "验证安装: redis-cli ping",
                    "检查服务: brew services list | grep redis",
                    "查看端口: lsof -i :6379"
                ]
            },
            "linux": {
                "title": "Linux Redis手动安装指南",
                "steps": [
                    "Ubuntu/Debian:",
                    "  sudo apt update && sudo apt install redis-server",
                    "  sudo systemctl start redis-server",
                    "",
                    "CentOS/RHEL:",
                    "  sudo yum install epel-release",
                    "  sudo yum install redis",
                    "  sudo systemctl start redis",
                    "",
                    "Fedora:",
                    "  sudo dnf install redis",
                    "  sudo systemctl start redis",
                    "",
                    "Arch Linux:",
                    "  sudo pacman -S redis",
                    "  sudo systemctl start redis"
                ],
                "verification": [
                    "验证安装: redis-cli ping",
                    "检查服务: sudo systemctl status redis",
                    "查看端口: sudo netstat -tlnp | grep 6379"
                ]
            }
        }

        return guides.get(platform, guides["linux"])

    def _print_redis_failure_summary(self, install_result: Dict[str, Any]):
        """打印Redis安装失败的详细总结"""
        self._print("=== Redis自动安装失败总结 ===", "error")
        self._print(f"主要错误: {install_result.get('error', 'unknown')}", "error")

        if "docker_error" in install_result:
            self._print(f"Docker安装错误: {install_result['docker_error']}", "warning")

        if "package_error" in install_result:
            self._print(f"包管理器安装错误: {install_result['package_error']}", "warning")

        self._print("\n=== 推荐解决方案 ===", "info")
        self._print("1. 检查网络连接", "info")
        self._print("2. 确保有足够的磁盘空间", "info")
        self._print("3. 检查系统权限（可能需要管理员权限）", "info")
        self._print("4. 查看详细安装指南: docs/redis-installation-guide.md", "info")

        system = platform.system().lower()
        if system == "windows":
            self._print("5. Windows用户推荐使用Docker Desktop", "info")
        elif system == "darwin":
            self._print("5. macOS用户推荐使用Homebrew", "info")
        else:
            self._print("5. Linux用户使用系统包管理器（apt/yum/dnf）", "info")

    async def _validate_redis_installation(self) -> Dict[str, Any]:
        """验证Redis安装是否成功"""
        try:
            # 1. 检查Redis服务状态
            redis_info = self.redis_manager.detect_redis_service()

            if redis_info.status.value == "running":
                return {
                    "success": True,
                    "message": "Redis服务运行正常",
                    "redis_info": redis_info
                }

            # 2. 如果服务未运行，尝试启动
            if redis_info.status.value == "stopped":
                self._print("Redis服务已停止，尝试启动...", "info")
                start_success, start_message = self.redis_manager.start_redis_service()

                if start_success:
                    await asyncio.sleep(2)  # 等待服务启动
                    new_redis_info = self.redis_manager.detect_redis_service()

                    if new_redis_info.status.value == "running":
                        return {
                            "success": True,
                            "message": "Redis服务启动成功",
                            "redis_info": new_redis_info
                        }

            # 3. 验证失败
            return {
                "success": False,
                "error": f"Redis验证失败，当前状态: {redis_info.status.value}",
                "redis_info": redis_info
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Redis验证异常: {str(e)}"
            }

    async def shutdown(self):
        """优雅关闭"""
        self._print("正在优雅关闭启动器...", "info")
        await self.stop_services()

def create_argument_parser() -> argparse.ArgumentParser:
    """创建命令行参数解析器"""
    parser = argparse.ArgumentParser(
        description="量化交易平台真实启动器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python launcher_real.py                # 正常启动
  python launcher_real.py --debug        # 调试模式启动
  python launcher_real.py --stop         # 停止所有服务
  python launcher_real.py --status       # 查看服务状态
  python launcher_real.py --install-only # 仅安装依赖
        """
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="启用调试模式，显示详细日志"
    )

    parser.add_argument(
        "--stop",
        action="store_true",
        help="停止所有运行中的服务"
    )

    parser.add_argument(
        "--status",
        action="store_true",
        help="显示所有服务的当前状态"
    )

    parser.add_argument(
        "--install-only",
        action="store_true",
        help="仅检查和安装依赖，不启动服务"
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="显示详细输出信息"
    )

    parser.add_argument(
        "--config",
        type=str,
        help="指定配置文件路径"
    )

    return parser

async def main():
    """主函数"""
    parser = create_argument_parser()
    args = parser.parse_args()

    # 确定启动模式
    if args.stop:
        mode = LauncherMode.STOP
    elif args.status:
        mode = LauncherMode.STATUS
    elif args.install_only:
        mode = LauncherMode.INSTALL_ONLY
    elif args.debug:
        mode = LauncherMode.DEBUG
    else:
        mode = LauncherMode.NORMAL

    # 创建启动器实例
    launcher = RealLauncher(mode=mode)

    try:
        if mode == LauncherMode.STOP:
            # 停止服务
            success = await launcher.stop_services()
            if success:
                print("所有服务已成功停止")
                return 0
            else:
                print("停止服务时发生错误")
                return 1

        elif mode == LauncherMode.STATUS:
            # 显示状态
            status = await launcher.get_status()

            if launcher.console:
                # 使用Rich格式化输出
                table = Table(title="服务状态")
                table.add_column("服务", style="cyan")
                table.add_column("端口", style="magenta")
                table.add_column("进程状态", style="green")
                table.add_column("端口状态", style="yellow")
                table.add_column("PID", style="blue")

                for service_name, service_info in status["services"].items():
                    process_text = "运行中" if service_info["status"] == "running" else "已停止"
                    port_text = "正常" if service_info["healthy"] else "异常"
                    pid_text = str(service_info["pid"]) if service_info["pid"] else "无"

                    table.add_row(
                        service_info["name"],
                        str(service_info["port"]),
                        process_text,
                        port_text,
                        pid_text
                    )

                launcher.console.print(table)
            else:
                # 基本文本输出
                print("服务状态:")
                for service_name, service_info in status["services"].items():
                    print(f"  {service_info['name']}: 进程={service_info['status']}, 端口={'正常' if service_info['healthy'] else '异常'}")

            return 0

        elif mode == LauncherMode.INSTALL_ONLY:
            # 仅安装依赖
            result = await launcher._prepare_environment()
            if result:
                print("依赖安装完成")
                return 0
            else:
                print("依赖安装失败")
                return 1

        else:
            # 正常启动
            result = await launcher.launch()

            if result.success:
                # 保持运行状态
                print("\n按 Ctrl+C 停止所有服务")
                try:
                    while True:
                        await asyncio.sleep(1)
                except KeyboardInterrupt:
                    await launcher.shutdown()
                    print("\n服务已停止")
                return 0
            else:
                print(f"\n启动失败: {result.error_message}")
                return 1

    except KeyboardInterrupt:
        print("\n用户中断操作")
        await launcher.shutdown()
        return 0

    except Exception as e:
        logger.error(f"发生未预期的错误: {str(e)}")
        print(f"发生错误: {str(e)}")
        return 1

if __name__ == "__main__":
    # 设置事件循环策略（Windows兼容性）
    if platform.system() == "Windows":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    # 运行主函数
    exit_code = asyncio.run(main())
    sys.exit(exit_code)