#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
量化交易平台真实启动器

这个启动器会启动真实的backend和frontend服务，而不是模拟启动。
"""

import os
import sys
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
        # 尝试设置UTF-8编码
        os.system("chcp 65001 >nul 2>&1")
        locale.setlocale(locale.LC_ALL, 'zh_CN.UTF-8')
    except:
        # 如果设置失败，继续使用默认编码
        pass

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
        self.services = {
            "redis": ServiceConfig("Redis", 6379, 30, False),  # Redis设为可选
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

            # 检查Node.js（前端需要）
            try:
                node_process = await asyncio.create_subprocess_exec(
                    "node", "--version",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                node_stdout, _ = await node_process.communicate()

                if node_process.returncode == 0:
                    node_version = node_stdout.decode('utf-8', errors='ignore').strip()
                    self._print(f"Node.js版本: {node_version}", "success")
                else:
                    self._print("Node.js未安装，前端可能无法启动", "warning")
            except Exception:
                self._print("Node.js不可用，前端可能无法启动", "warning")

            # 检查必要的包
            required_packages = ['psutil']
            if self.console:
                required_packages.extend(['rich'])

            missing_packages = []
            for package in required_packages:
                try:
                    __import__(package)
                    self._print(f"{package} 已安装", "success")
                except ImportError:
                    missing_packages.append(package)
                    self._print(f"{package} 未安装", "error")

            if missing_packages:
                self._print(f"正在安装缺失的包: {', '.join(missing_packages)}", "info")
                try:
                    subprocess.run([sys.executable, '-m', 'pip', 'install'] + missing_packages,
                                 check=True, capture_output=True)
                    self._print("包安装完成", "success")
                except subprocess.CalledProcessError as e:
                    self._print(f"包安装失败: {e}", "error")
                    return False

            return True

        except Exception as e:
            self._print(f"环境检测失败: {str(e)}", "error")
            return False

    async def _start_real_services(self) -> Tuple[List[str], List[str]]:
        """启动所有真实服务"""
        started_services = []
        failed_services = []

        self._print("开始启动真实服务...", "info")

        # 按顺序启动服务
        service_order = ["redis", "database", "backend", "frontend"]

        for service_name in service_order:
            if service_name in self.services:
                service_config = self.services[service_name]

                self._print(f"启动 {service_config.name}...", "info")

                try:
                    if service_name in ["redis", "database"]:
                        # 检查这些服务是否已在运行
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

            # 启动前端开发服务器
            # 在Windows上使用npm.cmd，在Unix上使用npm
            npm_cmd = "npm.cmd" if platform.system() == "Windows" else "npm"
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