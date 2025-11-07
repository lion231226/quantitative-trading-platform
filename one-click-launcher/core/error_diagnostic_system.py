#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
错误诊断系统 - 提供详细的启动失败诊断信息

实现结构化错误日志记录、故障排除指导和
用户友好的错误报告功能。
"""

import os
import sys
import json
import traceback
import platform
import subprocess
import psutil
import socket
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime
from pathlib import Path

from utils.logger import get_logger
from utils.config_manager import ConfigManager

logger = get_logger(__name__)
config = ConfigManager()

class ErrorSeverity(Enum):
    """错误严重程度"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ErrorCategory(Enum):
    """错误类别"""
    DEPENDENCY_MISSING = "dependency_missing"
    PORT_CONFLICT = "port_conflict"
    SERVICE_STARTUP = "service_startup"
    HEALTH_CHECK = "health_check"
    NETWORK = "network"
    PERMISSION = "permission"
    CONFIGURATION = "configuration"
    SYSTEM_RESOURCE = "system_resource"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"

@dataclass
class ErrorSolution:
    """错误解决方案"""
    title: str
    description: str
    auto_fixable: bool = False
    fix_command: Optional[str] = None
    manual_steps: List[str] = None
    related_docs: List[str] = None

    def __post_init__(self):
        if self.manual_steps is None:
            self.manual_steps = []
        if self.related_docs is None:
            self.related_docs = []

@dataclass
class DiagnosticInfo:
    """诊断信息"""
    service_name: str
    error_category: ErrorCategory
    severity: ErrorSeverity
    error_message: str
    detailed_cause: str
    timestamp: datetime
    system_info: Dict[str, Any]
    solutions: List[ErrorSolution]
    related_logs: List[str] = None
    diagnostics_data: Dict[str, Any] = None

    def __post_init__(self):
        if self.related_logs is None:
            self.related_logs = []
        if self.diagnostics_data is None:
            self.diagnostics_data = {}

class ErrorDiagnosticSystem:
    """错误诊断系统"""

    def __init__(self):
        """初始化错误诊断系统"""
        self.diagnostics_history = []
        self.known_issues_db = self._load_known_issues_database()
        self._setup_directories()

    def _setup_directories(self):
        """设置目录结构"""
        self.logs_dir = Path(config.get("paths", "logs_path", "./logs"))
        self.diagnostics_dir = Path(config.get("paths", "logs_path", "./logs")) / "diagnostics"

        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.diagnostics_dir.mkdir(parents=True, exist_ok=True)

    def _load_known_issues_database(self) -> Dict[str, List[Dict[str, Any]]]:
        """加载已知问题数据库"""
        return {
            "port_conflict": [
                {
                    "pattern": ["Address already in use", "port.*already.*in.*use", "bind.*failed"],
                    "solutions": [
                        ErrorSolution(
                            title="终止占用端口的进程",
                            description="找到并终止占用端口的进程",
                            auto_fixable=True,
                            manual_steps=[
                                "Windows: netstat -ano | findstr :<port>",
                                "Linux/macOS: lsof -i :<port> 或 netstat -tulpn | grep :<port>",
                                "终止进程: taskkill /PID <PID> /F (Windows) 或 kill -9 <PID> (Linux/macOS)"
                            ]
                        ),
                        ErrorSolution(
                            title="更改服务端口配置",
                            description="修改配置文件中的端口设置",
                            manual_steps=[
                                "编辑 config/config.ini 文件",
                                "修改对应的端口配置",
                                "重新启动服务"
                            ],
                            related_docs=["docs/configuration-guide.md"]
                        )
                    ]
                }
            ],
            "dependency_missing": [
                {
                    "pattern": ["ModuleNotFoundError", "ImportError", "command not found", "not recognized"],
                    "solutions": [
                        ErrorSolution(
                            title="安装缺失的依赖",
                            description="根据错误信息安装缺失的依赖包",
                            auto_fixable=True,
                            manual_steps=[
                                "Python依赖: pip install <package_name>",
                                "Node.js依赖: npm install <package_name>",
                                "系统依赖: 使用系统包管理器安装"
                            ]
                        )
                    ]
                }
            ],
            "service_startup": [
                {
                    "pattern": ["Failed to start", "startup failed", "Error starting service"],
                    "solutions": [
                        ErrorSolution(
                            title="检查服务配置",
                            description="验证服务配置和路径设置",
                            manual_steps=[
                                "检查配置文件语法",
                                "验证文件路径存在性",
                                "检查权限设置",
                                "查看详细错误日志"
                            ]
                        )
                    ]
                }
            ],
            "network": [
                {
                    "pattern": ["Connection refused", "Network unreachable", "timeout"],
                    "solutions": [
                        ErrorSolution(
                            title="检查网络连接",
                            description="诊断网络连接问题",
                            manual_steps=[
                                "检查防火墙设置",
                                "验证网络连通性",
                                "检查代理设置",
                                "确认服务是否在运行"
                            ]
                        )
                    ]
                }
            ]
        }

    async def diagnose_service_failure(self, service_name: str, error_message: str,
                                     exception: Optional[Exception] = None,
                                     process: Optional[subprocess.Popen] = None) -> DiagnosticInfo:
        """诊断服务启动失败"""
        timestamp = datetime.now()

        # 收集系统信息
        system_info = await self._collect_system_info()

        # 分析错误类型
        error_category = self._classify_error(error_message, exception)
        severity = self._determine_severity(error_category, service_name)

        # 详细原因分析
        detailed_cause = await self._analyze_detailed_cause(
            service_name, error_message, exception, process, system_info
        )

        # 生成解决方案
        solutions = await self._generate_solutions(
            service_name, error_category, error_message, system_info
        )

        # 收集相关日志
        related_logs = await self._collect_related_logs(service_name, timestamp)

        # 收集诊断数据
        diagnostics_data = await self._collect_diagnostics_data(service_name, system_info)

        diagnostic = DiagnosticInfo(
            service_name=service_name,
            error_category=error_category,
            severity=severity,
            error_message=error_message,
            detailed_cause=detailed_cause,
            timestamp=timestamp,
            system_info=system_info,
            solutions=solutions,
            related_logs=related_logs,
            diagnostics_data=diagnostics_data
        )

        # 保存诊断记录
        await self._save_diagnostic(diagnostic)

        return diagnostic

    def _classify_error(self, error_message: str, exception: Optional[Exception] = None) -> ErrorCategory:
        """分类错误类型"""
        error_text = error_message.lower()

        if exception:
            exception_text = str(exception).lower()
            error_text += " " + exception_text

        # 优先分类明确的网络连接问题 - 避免与端口冲突混淆
        if any(keyword in error_text for keyword in ["connection refused", "network unreachable", "connection reset"]):
            return ErrorCategory.NETWORK

        # 检查明确的端口占用问题
        if any(keyword in error_text for keyword in ["address already in use", "port.*already.*in.*use", "bind.*failed"]):
            return ErrorCategory.PORT_CONFLICT

        # 检查其他已知问题模式
        for category, issues in self.known_issues_db.items():
            # 跳过已处理的分类避免重复
            if category in ["network", "port_conflict"]:
                continue
            for issue in issues:
                for pattern in issue["pattern"]:
                    if any(p in error_text for p in pattern.lower().split(".*")):
                        return ErrorCategory(category)

        # 默认分类逻辑 - 处理剩余情况
        if any(keyword in error_text for keyword in ["port", "bind", "address"]):
            return ErrorCategory.PORT_CONFLICT
        elif any(keyword in error_text for keyword in ["module", "import", "not found", "command not found"]):
            return ErrorCategory.DEPENDENCY_MISSING
        elif any(keyword in error_text for keyword in ["timeout", "timed out"]):
            return ErrorCategory.TIMEOUT
        elif any(keyword in error_text for keyword in ["permission", "access denied", "unauthorized"]):
            return ErrorCategory.PERMISSION
        elif any(keyword in error_text for keyword in ["memory", "disk", "resource"]):
            return ErrorCategory.SYSTEM_RESOURCE
        else:
            return ErrorCategory.UNKNOWN

    def _determine_severity(self, error_category: ErrorCategory, service_name: str) -> ErrorSeverity:
        """确定错误严重程度"""
        critical_services = ["redis", "backend", "frontend"]

        if service_name in critical_services:
            if error_category in [ErrorCategory.DEPENDENCY_MISSING, ErrorCategory.SYSTEM_RESOURCE]:
                return ErrorSeverity.CRITICAL
            elif error_category in [ErrorCategory.PORT_CONFLICT, ErrorCategory.SERVICE_STARTUP]:
                return ErrorSeverity.HIGH
            else:
                return ErrorSeverity.MEDIUM
        else:
            if error_category in [ErrorCategory.SYSTEM_RESOURCE]:
                return ErrorSeverity.HIGH
            elif error_category in [ErrorCategory.DEPENDENCY_MISSING, ErrorCategory.SERVICE_STARTUP]:
                return ErrorSeverity.MEDIUM
            else:
                return ErrorSeverity.LOW

    async def _collect_system_info(self) -> Dict[str, Any]:
        """收集系统信息"""
        try:
            return {
                "platform": platform.system(),
                "platform_release": platform.release(),
                "platform_version": platform.version(),
                "architecture": platform.machine(),
                "hostname": platform.node(),
                "processor": platform.processor(),
                "python_version": platform.python_version(),
                "memory_total": psutil.virtual_memory().total // (1024**3),  # GB
                "memory_available": psutil.virtual_memory().available // (1024**3),  # GB
                "disk_usage": {
                    path.mountpoint: {
                        "total": disk.total // (1024**3),  # GB
                        "used": disk.used // (1024**3),   # GB
                        "free": disk.free // (1024**3)    # GB
                    }
                    for path in psutil.disk_partitions()
                    for disk in [psutil.disk_usage(path.mountpoint)]
                },
                "cpu_count": psutil.cpu_count(),
                "cpu_percent": psutil.cpu_percent(interval=1),
                "network_connections": len(psutil.net_connections()),
                "running_processes": len(psutil.pids())
            }
        except Exception as e:
            logger.error(f"收集系统信息失败: {str(e)}")
            return {"error": str(e)}

    async def _analyze_detailed_cause(self, service_name: str, error_message: str,
                                   exception: Optional[Exception],
                                   process: Optional[subprocess.Popen],
                                   system_info: Dict[str, Any]) -> str:
        """分析详细原因"""
        causes = []

        # 分析进程相关原因
        if process:
            if process.poll() is not None:
                causes.append(f"进程已退出，返回码: {process.returncode}")

                # 尝试获取进程输出
                try:
                    stdout, stderr = process.communicate()
                    if stderr:
                        causes.append(f"进程错误输出: {stderr.decode('utf-8', errors='ignore')}")
                except:
                    pass

        # 分析系统资源原因
        if system_info.get("memory_available", 0) < 1:  # 小于1GB
            causes.append("系统可用内存不足")

        cpu_percent = system_info.get("cpu_percent", 0)
        if cpu_percent > 90:
            causes.append(f"CPU使用率过高 ({cpu_percent}%)")

        # 分析网络相关原因
        network_connections = system_info.get("network_connections", 0)
        if network_connections > 1000:
            causes.append(f"网络连接数过多 ({network_connections})")

        # 分析特定服务原因
        if service_name == "redis":
            causes.extend(await self._analyze_redis_specific_causes(error_message, system_info))
        elif service_name == "backend":
            causes.extend(await self._analyze_backend_specific_causes(error_message, system_info))
        elif service_name == "frontend":
            causes.extend(await self._analyze_frontend_specific_causes(error_message, system_info))

        return "; ".join(causes) if causes else "未能确定具体原因"

    async def _analyze_redis_specific_causes(self, error_message: str, system_info: Dict[str, Any]) -> List[str]:
        """分析Redis特定原因"""
        causes = []

        # 检查Redis是否已运行
        try:
            import redis
            r = redis.Redis(host='localhost', port=6379, db=0, socket_connect_timeout=2)
            r.ping()
            causes.append("Redis已在运行，可能存在端口冲突")
        except:
            pass

        # 检查Redis配置文件
        redis_conf_paths = [
            "/etc/redis/redis.conf",
            "/usr/local/etc/redis.conf",
            "redis.conf"
        ]

        for conf_path in redis_conf_paths:
            if os.path.exists(conf_path):
                causes.append(f"发现Redis配置文件: {conf_path}")
                break

        return causes

    async def _analyze_backend_specific_causes(self, error_message: str, system_info: Dict[str, Any]) -> List[str]:
        """分析后端特定原因"""
        causes = []

        # 检查Python依赖
        try:
            import fastapi
            import uvicorn
        except ImportError as e:
            causes.append(f"Python依赖缺失: {str(e)}")

        # 检查后端路径
        backend_path = config.get("paths", "backend_path", "../backend")
        backend_path = os.path.abspath(backend_path)

        if not os.path.exists(backend_path):
            causes.append(f"后端路径不存在: {backend_path}")
        elif not os.path.exists(os.path.join(backend_path, "main.py")):
            causes.append("后端main.py文件不存在")

        return causes

    async def _analyze_frontend_specific_causes(self, error_message: str, system_info: Dict[str, Any]) -> List[str]:
        """分析前端特定原因"""
        causes = []

        # 检查Node.js
        try:
            node_process = subprocess.run(["node", "--version"],
                                       capture_output=True, text=True, timeout=10)
            if node_process.returncode != 0:
                causes.append("Node.js不可用")
        except:
            causes.append("Node.js未安装或不可用")

        # 检查npm
        try:
            npm_cmd = "npm.cmd" if platform.system() == "Windows" else "npm"
            npm_process = subprocess.run([npm_cmd, "--version"],
                                      capture_output=True, text=True, timeout=10)
            if npm_process.returncode != 0:
                causes.append("npm不可用")
        except:
            causes.append("npm未安装或不可用")

        # 检查前端路径
        frontend_path = config.get("paths", "frontend_path", "../frontend")
        frontend_path = os.path.abspath(frontend_path)

        if not os.path.exists(frontend_path):
            causes.append(f"前端路径不存在: {frontend_path}")
        elif not os.path.exists(os.path.join(frontend_path, "package.json")):
            causes.append("package.json文件不存在")

        return causes

    async def _generate_solutions(self, service_name: str, error_category: ErrorCategory,
                                error_message: str, system_info: Dict[str, Any]) -> List[ErrorSolution]:
        """生成解决方案"""
        solutions = []

        # 基于错误类别的通用解决方案
        if error_category in self.known_issues_db:
            for issue in self.known_issues_db[error_category]:
                for pattern in issue["pattern"]:
                    if any(p.lower() in error_message.lower() for p in pattern.split(".*")):
                        solutions.extend(issue["solutions"])
                        break

        # 基于系统信息的解决方案
        if system_info.get("memory_available", 0) < 1:
            solutions.append(ErrorSolution(
                title="释放系统内存",
                description="系统内存不足，建议释放内存",
                manual_steps=[
                    "关闭不必要的应用程序",
                    "重启系统",
                    "增加虚拟内存"
                ]
            ))

        # 基于服务的特定解决方案
        if service_name == "redis":
            solutions.extend(await self._generate_redis_solutions(error_message))
        elif service_name == "backend":
            solutions.extend(await self._generate_backend_solutions(error_message))
        elif service_name == "frontend":
            solutions.extend(await self._generate_frontend_solutions(error_message))

        return solutions

    async def _generate_redis_solutions(self, error_message: str) -> List[ErrorSolution]:
        """生成Redis解决方案"""
        solutions = []

        if "port" in error_message.lower():
            solutions.append(ErrorSolution(
                title="更改Redis端口",
                description="修改Redis配置使用不同的端口",
                manual_steps=[
                    "编辑redis.conf文件",
                    "修改port配置（例如：port 6380）",
                    "重启Redis服务"
                ]
            ))

        solutions.append(ErrorSolution(
            title="重新安装Redis",
            description="完全重新安装Redis服务",
            manual_steps=[
                "停止现有Redis服务",
                "卸载Redis",
                "重新下载并安装Redis",
                "配置Redis服务"
            ],
            related_docs=["docs/redis-installation-guide.md"]
        ))

        return solutions

    async def _generate_backend_solutions(self, error_message: str) -> List[ErrorSolution]:
        """生成后端解决方案"""
        solutions = []

        if "module" in error_message.lower() or "import" in error_message.lower():
            solutions.append(ErrorSolution(
                title="安装Python依赖",
                description="安装缺失的Python包",
                auto_fixable=True,
                fix_command="pip install -r requirements.txt",
                manual_steps=[
                    "进入backend目录",
                    "运行: pip install -r requirements.txt",
                    "如果失败，尝试: pip install --upgrade pip",
                    "重新安装: pip install -r requirements.txt"
                ]
            ))

        solutions.append(ErrorSolution(
            title="检查后端配置",
            description="验证后端服务配置",
            manual_steps=[
                "检查config.ini中的backend_path配置",
                "确认main.py文件存在",
                "检查Python环境变量"
            ]
        ))

        return solutions

    async def _generate_frontend_solutions(self, error_message: str) -> List[ErrorSolution]:
        """生成前端解决方案"""
        solutions = []

        if "node" in error_message.lower() or "npm" in error_message.lower():
            solutions.append(ErrorSolution(
                title="安装Node.js依赖",
                description="重新安装前端依赖",
                auto_fixable=True,
                fix_command="npm install",
                manual_steps=[
                    "进入frontend目录",
                    "删除node_modules文件夹和package-lock.json",
                    "运行: npm install",
                    "如果失败，清理npm缓存: npm cache clean --force"
                ]
            ))

        solutions.append(ErrorSolution(
            title="检查Node.js版本",
            description="确认Node.js版本兼容性",
            manual_steps=[
                "检查版本: node --version",
                "最低要求: Node.js 18.0.0+",
                "如版本过低，请升级Node.js"
            ]
        ))

        return solutions

    async def _collect_related_logs(self, service_name: str, timestamp: datetime) -> List[str]:
        """收集相关日志"""
        logs = []

        try:
            # 收集启动器日志
            launcher_log = self.logs_dir / "launcher.log"
            if launcher_log.exists():
                logs.append(str(launcher_log))

            # 收集服务特定日志
            service_log = self.logs_dir / f"{service_name}.log"
            if service_log.exists():
                logs.append(str(service_log))

            # 收集最近的错误日志
            error_log_pattern = self.logs_dir / f"*error*{timestamp.strftime('%Y%m%d')}*"
            for log_file in self.logs_dir.glob(error_log_pattern.name):
                logs.append(str(log_file))

        except Exception as e:
            logger.error(f"收集相关日志失败: {str(e)}")

        return logs

    async def _collect_diagnostics_data(self, service_name: str, system_info: Dict[str, Any]) -> Dict[str, Any]:
        """收集诊断数据"""
        data = {
            "timestamp": datetime.now().isoformat(),
            "service_name": service_name,
            "port_status": await self._check_service_ports(service_name),
            "process_list": await self._get_running_processes(),
            "network_status": await self._check_network_status()
        }

        return data

    async def _check_service_ports(self, service_name: str) -> Dict[str, bool]:
        """检查服务端口状态"""
        port_status = {}

        service_ports = {
            "redis": 6379,
            "backend": 8000,
            "frontend": 3000
        }

        if service_name in service_ports:
            port = service_ports[service_name]
            port_status[f"port_{port}"] = await self._is_port_open("localhost", port)

        return port_status

    async def _is_port_open(self, host: str, port: int) -> bool:
        """检查端口是否开放"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except:
            return False

    async def _get_running_processes(self) -> List[Dict[str, Any]]:
        """获取运行中的进程列表"""
        processes = []

        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    processes.append({
                        "pid": proc.info['pid'],
                        "name": proc.info['name'],
                        "cmdline": proc.info['cmdline']
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception as e:
            logger.error(f"获取进程列表失败: {str(e)}")

        return processes

    async def _check_network_status(self) -> Dict[str, Any]:
        """检查网络状态"""
        try:
            return {
                "connections_count": len(psutil.net_connections()),
                "interfaces": list(psutil.net_if_addrs().keys()),
                "io_counters": psutil.net_io_counters()._asdict() if psutil.net_io_counters() else {}
            }
        except Exception as e:
            return {"error": str(e)}

    async def _save_diagnostic(self, diagnostic: DiagnosticInfo):
        """保存诊断记录"""
        try:
            # 保存到内存历史
            self.diagnostics_history.append(diagnostic)

            # 保存到文件
            timestamp_str = diagnostic.timestamp.strftime("%Y%m%d_%H%M%S")
            filename = f"diagnostic_{diagnostic.service_name}_{timestamp_str}.json"
            filepath = self.diagnostics_dir / filename

            diagnostic_dict = asdict(diagnostic)
            diagnostic_dict["timestamp"] = diagnostic.timestamp.isoformat()
            diagnostic_dict["error_category"] = diagnostic.error_category.value
            diagnostic_dict["severity"] = diagnostic.severity.value

            for solution in diagnostic_dict["solutions"]:
                solution["error_category"] = solution["error_category"] if hasattr(solution, "error_category") else None

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(diagnostic_dict, f, indent=2, ensure_ascii=False)

            logger.info(f"诊断记录已保存: {filepath}")

        except Exception as e:
            logger.error(f"保存诊断记录失败: {str(e)}")

    def generate_user_report(self, diagnostic: DiagnosticInfo) -> str:
        """生成用户友好的错误报告"""
        report = []
        report.append("=" * 60)
        report.append(f"服务启动失败诊断报告")
        report.append("=" * 60)
        report.append(f"服务名称: {diagnostic.service_name}")
        report.append(f"错误类别: {diagnostic.error_category.value}")
        report.append(f"严重程度: {diagnostic.severity.value}")
        report.append(f"发生时间: {diagnostic.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")

        report.append("错误信息:")
        report.append(f"  {diagnostic.error_message}")
        report.append("")

        if diagnostic.detailed_cause:
            report.append("详细原因:")
            report.append(f"  {diagnostic.detailed_cause}")
            report.append("")

        report.append("解决方案:")
        for i, solution in enumerate(diagnostic.solutions, 1):
            report.append(f"  {i}. {solution.title}")
            report.append(f"     {solution.description}")

            if solution.auto_fixable and solution.fix_command:
                report.append(f"     自动修复命令: {solution.fix_command}")

            if solution.manual_steps:
                report.append("     手动步骤:")
                for step in solution.manual_steps:
                    report.append(f"       - {step}")

            if solution.related_docs:
                report.append(f"     相关文档: {', '.join(solution.related_docs)}")
            report.append("")

        report.append("系统信息:")
        sys_info = diagnostic.system_info
        report.append(f"  操作系统: {sys_info.get('platform', 'Unknown')}")
        report.append(f"  Python版本: {sys_info.get('python_version', 'Unknown')}")
        report.append(f"  可用内存: {sys_info.get('memory_available', 0)} GB")
        report.append(f"  CPU使用率: {sys_info.get('cpu_percent', 0)}%")
        report.append("")

        if diagnostic.related_logs:
            report.append("相关日志文件:")
            for log_file in diagnostic.related_logs:
                report.append(f"  - {log_file}")
            report.append("")

        report.append("如需进一步协助，请提供此诊断报告。")
        report.append("=" * 60)

        return "\n".join(report)

    def get_diagnostic_history(self, service_name: Optional[str] = None,
                             limit: int = 10) -> List[DiagnosticInfo]:
        """获取诊断历史"""
        history = self.diagnostics_history

        if service_name:
            history = [d for d in history if d.service_name == service_name]

        # 按时间倒序排列，返回最新的记录
        history.sort(key=lambda x: x.timestamp, reverse=True)
        return history[:limit]

# 全局诊断系统实例
diagnostic_system = ErrorDiagnosticSystem()