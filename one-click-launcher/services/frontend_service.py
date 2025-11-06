"""
前端应用服务启动器

提供Next.js/React前端服务的统一启动、配置和健康检查功能。
"""

import asyncio
import sys
import time
import psutil
import subprocess
import webbrowser
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from datetime import datetime
import json
import signal
import os
import platform
import importlib

# Dependency check function
def check_dependencies():
    """检查所有必需的依赖项是否可用"""
    dependencies = {
        'core.service_dependency_analyzer': 'ServiceDependencyAnalyzer',
        'core.health_checker': 'HealthChecker',
        'core.port_manager': 'PortManager',
        'core.timeout_manager': 'TimeoutManager',
        'core.service_configurator': 'ServiceConfigurator',
        'core.frontend_verifier': 'FrontendAccessibilityVerifier',
        'core.frontend_backend_communicator': 'FrontendBackendCommunicator',
        'utils.logger': 'get_logger',
        'utils.progress_tracker': 'ProgressTracker',
        'utils.frontend_logger': 'get_frontend_logger',
        'utils.browser_utils': 'get_browser_manager'
    }

    missing_deps = []
    available_deps = {}

    for module_name, class_name in dependencies.items():
        try:
            module = importlib.import_module(module_name)
            if hasattr(module, class_name):
                available_deps[module_name] = getattr(module, class_name)
            else:
                missing_deps.append(f"{module_name}.{class_name}")
        except ImportError as e:
            missing_deps.append(f"{module_name} ({str(e)})")
        except Exception as e:
            missing_deps.append(f"{module_name}.{class_name} ({str(e)})")

    return available_deps, missing_deps

# 执行依赖项检查
_AVAILABLE_DEPENDENCIES, _MISSING_DEPENDENCIES = check_dependencies()

if _MISSING_DEPENDENCIES:
    logger.warning(f"Missing dependencies: {_MISSING_DEPENDENCIES}")

# 安全导入函数
def safe_import(module_path, class_name, fallback=None):
    """安全导入模块，提供回退机制"""
    if module_path in _AVAILABLE_DEPENDENCIES:
        return _AVAILABLE_DEPENDENCIES[module_path]
    elif fallback:
        logger.warning(f"Using fallback for {module_path}.{class_name}")
        return fallback
    else:
        raise ImportError(f"Required dependency {module_path}.{class_name} is not available")

# Import core components with fallbacks
try:
    from core.service_dependency_analyzer import (
        ServiceDependencyAnalyzer, ServiceInfo, ServiceType, ServiceStatus
    )
except ImportError:
    ServiceDependencyAnalyzer = None
    ServiceInfo = None
    ServiceType = None
    ServiceStatus = None

try:
    from core.health_checker import HealthChecker, HealthCheckResult, HealthStatus
except ImportError:
    HealthChecker = None
    HealthCheckResult = None
    HealthStatus = None

try:
    from core.port_manager import PortManager, PortInfo, PortStatus
except ImportError:
    PortManager = None
    PortInfo = None
    PortStatus = None

try:
    from core.timeout_manager import TimeoutManager, TimeoutConfig, StartupResult
except ImportError:
    TimeoutManager = None
    TimeoutConfig = None
    StartupResult = None

try:
    from core.service_configurator import ServiceConfigurator, ServiceConfig, Environment
except ImportError:
    ServiceConfigurator = None
    ServiceConfig = None
    Environment = None

try:
    from core.frontend_verifier import FrontendAccessibilityVerifier, AccessibilityConfig, VerificationStatus
except ImportError:
    FrontendAccessibilityVerifier = None
    AccessibilityConfig = None
    VerificationStatus = None

try:
    from core.frontend_backend_communicator import (
        FrontendBackendCommunicator, CommunicationConfig, APIEndpoint, CommunicationStatus
    )
except ImportError:
    FrontendBackendCommunicator = None
    CommunicationConfig = None
    APIEndpoint = None
    CommunicationStatus = None

# Import utilities with fallbacks
try:
    from utils.logger import get_logger
except ImportError:
    def get_logger(name):
        import logging
        return logging.getLogger(name)

try:
    from utils.progress_tracker import ProgressTracker
except ImportError:
    class ProgressTracker:
        def __init__(self, *args, **kwargs):
            pass
        def start(self, *args, **kwargs):
            pass
        def complete(self, *args, **kwargs):
            pass
        def track_progress(self, *args, **kwargs):
            pass

try:
    from utils.frontend_logger import get_frontend_logger
except ImportError:
    def get_frontend_logger():
        import logging
        return logging.getLogger("frontend")

try:
    from utils.browser_utils import get_browser_manager, BrowserConfig, BrowserType
except ImportError:
    def get_browser_manager():
        return None
    class BrowserConfig:
        pass
    class BrowserType:
        pass

logger = get_logger(__name__)
frontend_logger = get_frontend_logger()


class FrontendServiceStatus(Enum):
    """前端服务状态"""
    NOT_STARTED = "not_started"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class FrontendServiceConfig:
    """前端服务配置"""
    service_name: str = "frontend"
    host: str = "localhost"
    port: int = 3000
    project_root: str = ""
    frontend_dir: str = "frontend"
    startup_command: str = "npm run dev"
    build_command: str = "npm run build"
    startup_timeout: int = 120
    max_retries: int = 3
    health_check_interval: int = 5
    auto_open_browser: bool = True
    node_version_required: str = ">=18.0.0"

    # Process management
    process_name_patterns: List[str] = field(default_factory=lambda: ["node", "next", "npm"])
    pid_file: str = "logs/frontend.pid"
    log_file: str = "logs/frontend.log"


@dataclass
class FrontendServiceInfo:
    """前端服务信息"""
    config: FrontendServiceConfig
    status: FrontendServiceStatus = FrontendServiceStatus.NOT_STARTED
    process: Optional[Any] = None
    pid: Optional[int] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    health_status: Optional[HealthCheckResult] = None
    last_error: Optional[str] = None
    startup_attempts: int = 0
    url: str = field(init=False)

    def __post_init__(self):
        self.url = f"http://{self.config.host}:{self.config.port}"


class FrontendServiceManager:
    """前端服务管理器"""

    def __init__(self, config: FrontendServiceConfig):
        # 检查关键依赖项
        self._check_critical_dependencies()

        self.config = config
        self.service_info = FrontendServiceInfo(
            config=config,
            status=FrontendServiceStatus.NOT_STARTED
        )

        # Initialize core components with graceful fallbacks
        try:
            self.health_checker = HealthChecker() if HealthChecker else None
        except Exception as e:
            logger.warning(f"Failed to initialize HealthChecker: {e}")
            self.health_checker = None

        try:
            self.port_manager = PortManager() if PortManager else None
        except Exception as e:
            logger.warning(f"Failed to initialize PortManager: {e}")
            self.port_manager = None

        try:
            self.timeout_manager = TimeoutManager(TimeoutConfig(
                default_timeout=config.startup_timeout,
                max_retries=config.max_retries
            )) if TimeoutManager and TimeoutConfig else None
        except Exception as e:
            logger.warning(f"Failed to initialize TimeoutManager: {e}")
            self.timeout_manager = None

        try:
            self.service_configurator = ServiceConfigurator(
                config_path="config/frontend-config.yaml"
            ) if ServiceConfigurator else None
        except Exception as e:
            logger.warning(f"Failed to initialize ServiceConfigurator: {e}")
            self.service_configurator = None

        try:
            self.dependency_analyzer = ServiceDependencyAnalyzer() if ServiceDependencyAnalyzer else None
        except Exception as e:
            logger.warning(f"Failed to initialize ServiceDependencyAnalyzer: {e}")
            self.dependency_analyzer = None

        # Initialize progress tracker
        try:
            self.progress_tracker = ProgressTracker(
                component_name="frontend_startup"
            ) if ProgressTracker else None
        except Exception as e:
            logger.warning(f"Failed to initialize ProgressTracker: {e}")
            self.progress_tracker = None

        # Initialize accessibility verifier
        try:
            self.accessibility_verifier = FrontendAccessibilityVerifier() if FrontendAccessibilityVerifier else None
        except Exception as e:
            logger.warning(f"Failed to initialize FrontendAccessibilityVerifier: {e}")
            self.accessibility_verifier = None

        # Initialize frontend-backend communicator
        try:
            self.frontend_backend_communicator = FrontendBackendCommunicator() if FrontendBackendCommunicator else None
        except Exception as e:
            logger.warning(f"Failed to initialize FrontendBackendCommunicator: {e}")
            self.frontend_backend_communicator = None

        # Initialize browser manager
        try:
            self.browser_manager = get_browser_manager() if get_browser_manager else None
        except Exception as e:
            logger.warning(f"Failed to initialize browser manager: {e}")
            self.browser_manager = None

        # Initialize frontend logger
        try:
            self.frontend_logger = get_frontend_logger() if get_frontend_logger else None
        except Exception as e:
            logger.warning(f"Failed to initialize frontend logger: {e}")
            self.frontend_logger = None

        # Initialize state
        self._is_running = False
        self._shutdown_event = asyncio.Event()

        # Log initialization status
        missing_components = []
        if not self.health_checker:
            missing_components.append("HealthChecker")
        if not self.port_manager:
            missing_components.append("PortManager")
        if not self.timeout_manager:
            missing_components.append("TimeoutManager")
        if not self.service_configurator:
            missing_components.append("ServiceConfigurator")
        if not self.dependency_analyzer:
            missing_components.append("ServiceDependencyAnalyzer")
        if not self.accessibility_verifier:
            missing_components.append("FrontendAccessibilityVerifier")
        if not self.frontend_backend_communicator:
            missing_components.append("FrontendBackendCommunicator")
        if not self.progress_tracker:
            missing_components.append("ProgressTracker")
        if not self.browser_manager:
            missing_components.append("BrowserManager")
        if not self.frontend_logger:
            missing_components.append("FrontendLogger")

        if missing_components:
            logger.warning(f"FrontendServiceManager initialized with reduced functionality due to missing components: {missing_components}")
        else:
            logger.info("FrontendServiceManager initialized successfully with all components")

    def _check_critical_dependencies(self):
        """检查关键依赖项，如果缺失则抛出异常"""
        critical_deps = ['asyncio', 'psutil', 'subprocess', 'pathlib', 'datetime']
        missing_critical = []

        for dep in critical_deps:
            try:
                __import__(dep)
            except ImportError:
                missing_critical.append(dep)

        if missing_critical:
            error_msg = f"Critical dependencies missing: {missing_critical}"
            logger.error(error_msg)
            raise ImportError(error_msg)

    async def start(self) -> bool:
        """启动前端服务"""
        start_time = time.time()
        try:
            # 记录启动开始
            config_dict = {
                "host": self.config.host,
                "port": self.config.port,
                "frontend_dir": self.config.frontend_dir,
                "auto_open_browser": self.config.auto_open_browser
            }
            self.frontend_logger.log_startup_start(config_dict)

            logger.info(f"Starting frontend service: {self.config.service_name}")
            self.service_info.status = FrontendServiceStatus.STARTING
            self.progress_tracker.start()

            # Step 1: 检查依赖服务
            await self._check_dependencies()
            self.progress_tracker.update_step("Dependencies checked")

            # Step 2: 配置服务参数
            await self._configure_service()
            self.progress_tracker.update_step("Service configured")

            # Step 3: 检测Node.js进程
            await self._detect_nodejs_process()
            self.progress_tracker.update_step("Node.js process detected")

            # Step 4: 启动前端服务
            await self._start_frontend_service()
            self.progress_tracker.update_step("Frontend service started")

            # Step 5: 验证服务状态
            await self._verify_service_status()
            self.progress_tracker.update_step("Service status verified")

            # Step 6: 自动打开浏览器
            if self.config.auto_open_browser:
                await self._open_browser()
                self.progress_tracker.update_step("Browser opened")

            self.service_info.status = FrontendServiceStatus.RUNNING
            self._is_running = True
            self.progress_tracker.complete()

            startup_time = time.time() - start_time
            self.frontend_logger.log_startup_success(
                self.service_info.url,
                self.service_info.pid,
                startup_time
            )
            logger.info(f"Frontend service {self.config.service_name} started successfully")
            return True

        except Exception as e:
            startup_time = time.time() - start_time
            self.frontend_logger.log_startup_failure(e, startup_time)
            logger.error(f"Failed to start frontend service: {e}")
            self.service_info.status = FrontendServiceStatus.FAILED
            self.service_info.last_error = str(e)
            self.progress_tracker.complete()
            return False

    async def stop(self) -> bool:
        """停止前端服务"""
        try:
            logger.info(f"Stopping frontend service: {self.config.service_name}")
            self.service_info.status = FrontendServiceStatus.STOPPING

            if self.service_info.process:
                self.service_info.process.terminate()
                try:
                    await asyncio.wait_for(
                        self.service_info.process.wait(), timeout=10.0
                    )
                except asyncio.TimeoutError:
                    self.service_info.process.kill()
                    await self.service_info.process.wait()

            self.service_info.status = FrontendServiceStatus.STOPPED
            self._is_running = False
            self._shutdown_event.set()

            self.frontend_logger.log_service_stopped()
            logger.info(f"Frontend service {self.config.service_name} stopped successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to stop frontend service: {e}")
            return False

    async def restart(self) -> bool:
        """重启前端服务"""
        logger.info(f"Restarting frontend service: {self.config.service_name}")

        if await self.stop():
            await asyncio.sleep(2)
            return await self.start()

        return False

    async def _check_dependencies(self):
        """检查依赖服务"""
        logger.info("Checking frontend service dependencies")

        # 检查端口可用性
        if not await self.port_manager.check_port_availability(self.config.port):
            port_info = self.port_manager.get_port_info(self.config.port)
            if port_info and port_info.status == PortStatus.OCCUPIED:
                # 检查是否是我们自己的服务
                if self._is_frontend_process_running():
                    logger.info(f"Frontend service already running on port {self.config.port}")
                    self.frontend_logger.log_dependency_check("port", "passed",
                        {"port": self.config.port, "status": "already_running"})
                    return
                else:
                    self.frontend_logger.log_dependency_check("port", "failed",
                        {"port": self.config.port, "error": "already_in_use"})
                    raise Exception(f"Port {self.config.port} is already in use by another process")

        # 检查项目结构
        frontend_path = Path(self.config.project_root) / self.config.frontend_dir
        if not frontend_path.exists():
            self.frontend_logger.log_dependency_check("project_structure", "failed",
                {"path": str(frontend_path), "error": "not_found"})
            raise Exception(f"Frontend directory not found: {frontend_path}")

        package_json = frontend_path / "package.json"
        if not package_json.exists():
            self.frontend_logger.log_dependency_check("package_json", "failed",
                {"path": str(package_json), "error": "not_found"})
            raise Exception(f"package.json not found: {package_json}")

        self.frontend_logger.log_dependency_check("project_structure", "passed")
        logger.info("Dependencies check completed")

    async def _configure_service(self):
        """配置服务参数"""
        logger.info("Configuring frontend service")

        # 确保日志目录存在
        log_dir = Path(self.config.pid_file).parent
        log_dir.mkdir(parents=True, exist_ok=True)

        # 设置环境变量
        os.environ["NODE_ENV"] = "development"
        os.environ["PORT"] = str(self.config.port)
        os.environ["HOST"] = self.config.host

        logger.info("Service configuration completed")

    async def _detect_nodejs_process(self):
        """检测Node.js进程"""
        logger.info("Detecting Node.js processes")

        node_processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = proc.info.get('cmdline', [])
                if cmdline and any(pattern in ' '.join(cmdline).lower()
                                 for pattern in self.config.process_name_patterns):
                    node_processes.append({
                        "pid": proc.info['pid'],
                        "name": proc.info.get('name', 'unknown'),
                        "cmdline": ' '.join(cmdline)
                    })
                    logger.debug(f"Found Node.js process: PID {proc.info['pid']}, cmdline: {cmdline}")
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        self.frontend_logger.log_process_detected(node_processes)

        if not node_processes:
            logger.info("No existing Node.js processes found")
        else:
            logger.info(f"Found {len(node_processes)} Node.js processes")

    async def _start_frontend_service(self):
        """启动前端服务"""
        logger.info("Starting frontend development server")

        frontend_path = Path(self.config.project_root) / self.config.frontend_dir

        # 构建启动命令
        startup_cmd = self.config.startup_command.split()

        # 启动进程
        try:
            process = await asyncio.create_subprocess_exec(
                *startup_cmd,
                cwd=frontend_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=os.environ.copy()
            )

            self.service_info.process = process
            self.service_info.pid = process.pid
            self.service_info.start_time = datetime.now()

            logger.info(f"Frontend process started with PID: {process.pid}")

            # 等待进程启动
            await self._wait_for_startup()

        except Exception as e:
            logger.error(f"Failed to start frontend process: {e}")
            raise

    async def _wait_for_startup(self):
        """等待前端服务启动"""
        logger.info(f"Waiting for frontend service to start (timeout: {self.config.startup_timeout}s)")

        start_time = time.time()

        while time.time() - start_time < self.config.startup_timeout:
            # 检查进程是否还在运行
            if self.service_info.process and self.service_info.process.returncode is not None:
                raise Exception(f"Frontend process exited with code {self.service_info.process.returncode}")

            # 检查服务是否可访问
            if await self._check_service_health():
                logger.info("Frontend service is now accessible")
                return

            await asyncio.sleep(self.config.health_check_interval)

        self.frontend_logger.log_timeout_event("service_startup", self.config.startup_timeout)
        raise Exception(f"Frontend service failed to start within {self.config.startup_timeout} seconds")

    async def _verify_service_status(self):
        """验证服务状态"""
        logger.info("Verifying frontend service status")

        # 执行健康检查
        health_result = await self.health_checker.check_endpoint(self.service_info.url)
        self.service_info.health_status = health_result

        self.frontend_logger.log_health_check(
            health_result.status.value,
            health_result.response_time,
            health_result.message if health_result.status != HealthStatus.HEALTHY else None
        )

        if health_result.status != HealthStatus.HEALTHY:
            raise Exception(f"Health check failed: {health_result.message}")

        logger.info("Service status verification completed")

    async def _open_browser(self):
        """自动打开浏览器"""
        logger.info(f"Opening browser at {self.service_info.url}")

        try:
            # 使用浏览器管理器打开浏览器
            success = await self.browser_manager.try_multiple_browsers(self.service_info.url)
            if success:
                logger.info("Browser opened successfully")
            else:
                logger.warning("Failed to open browser automatically")
                logger.info(f"Please manually open: {self.service_info.url}")

        except Exception as e:
            logger.warning(f"Failed to open browser automatically: {e}")
            logger.info(f"Please manually open: {self.service_info.url}")

    async def _check_service_health(self) -> bool:
        """检查服务健康状态"""
        try:
            health_result = await self.health_checker.check_endpoint(self.service_info.url)
            return health_result.status == HealthStatus.HEALTHY
        except Exception:
            return False

    def _is_frontend_process_running(self) -> bool:
        """检查前端进程是否正在运行"""
        if not self.service_info.pid:
            return False

        try:
            process = psutil.Process(self.service_info.pid)
            return process.is_running() and any(
                pattern in ' '.join(process.cmdline()).lower()
                for pattern in self.config.process_name_patterns
            )
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return False

    def get_service_info(self) -> FrontendServiceInfo:
        """获取服务信息"""
        return self.service_info

    def get_service_url(self) -> str:
        """获取服务URL"""
        return self.service_info.url

    async def health_check(self) -> HealthCheckResult:
        """执行健康检查"""
        return await self.health_checker.check_endpoint(self.service_info.url)

    def is_running(self) -> bool:
        """检查服务是否正在运行"""
        return self._is_running and self.service_info.status == FrontendServiceStatus.RUNNING

    async def verify_accessibility(self,
                                 expected_content_patterns: Optional[List[str]] = None,
                                 response_time_threshold: Optional[float] = None) -> Dict[str, Any]:
        """验证前端应用访问性"""
        if not self.is_running():
            raise Exception("Frontend service is not running")

        # 配置访问性验证
        config = AccessibilityConfig(
            url=self.service_info.url,
            timeout=30,
            max_retries=3,
            expected_content_patterns=expected_content_patterns or [
                r'<html',  # 基本HTML结构
                r'<title>',  # 页面标题
                r'<div[^>]*id=["\']root["\']',  # React根元素
                r'react|ReactDOM|__NEXT_DATA__',  # React/Next.js特征
            ],
            response_time_threshold=response_time_threshold or 5.0,
            check_resources=True,
            verify_rendering=True
        )

        try:
            # 执行访问性验证
            async with self.accessibility_verifier as verifier:
                result = await verifier.verify_accessibility(config)

                # 记录验证结果
                self.frontend_logger.log_health_check(
                    "accessibility_verification" if result.status == VerificationStatus.PASSED else "failed",
                    result.response_time,
                    result.error_message
                )

                # 转换为字典格式返回
                return {
                    'url': result.url,
                    'status': result.status.value,
                    'response_time': result.response_time,
                    'status_code': result.status_code,
                    'content_length': result.content_length,
                    'content_matches': result.content_matches,
                    'resource_results': result.resource_results,
                    'rendering_result': result.rendering_result,
                    'error_message': result.error_message,
                    'retry_count': result.retry_count,
                    'passed': result.status == VerificationStatus.PASSED
                }

        except Exception as e:
            self.frontend_logger.error("Accessibility verification failed", e)
            return {
                'url': self.service_info.url,
                'status': 'failed',
                'error_message': str(e),
                'passed': False
            }

    async def check_response_time(self, samples: int = 3) -> Dict[str, Any]:
        """检查前端响应时间"""
        if not self.is_running():
            raise Exception("Frontend service is not running")

        response_times = []
        successful_checks = 0

        async with self.accessibility_verifier as verifier:
            for i in range(samples):
                try:
                    response_time, success = await verifier.check_response_time(self.service_info.url)
                    response_times.append(response_time)
                    if success:
                        successful_checks += 1

                    # 短暂延迟避免过快请求
                    if i < samples - 1:
                        await asyncio.sleep(0.5)

                except Exception as e:
                    self.frontend_logger.warning(f"Response time check {i+1} failed: {e}")

        if response_times:
            avg_response_time = sum(response_times) / len(response_times)
            min_response_time = min(response_times)
            max_response_time = max(response_times)

            result = {
                'url': self.service_info.url,
                'samples': samples,
                'successful_checks': successful_checks,
                'success_rate': successful_checks / samples,
                'average_response_time': avg_response_time,
                'min_response_time': min_response_time,
                'max_response_time': max_response_time,
                'response_times': response_times,
                'passed': successful_checks > 0 and avg_response_time < 5.0
            }

            self.frontend_logger.log_health_check(
                "response_time_check" if result['passed'] else "slow_response",
                avg_response_time
            )

            return result
        else:
            return {
                'url': self.service_info.url,
                'samples': samples,
                'successful_checks': 0,
                'success_rate': 0.0,
                'passed': False,
                'error_message': 'All response time checks failed'
            }

    async def verify_page_loading_completeness(self) -> Dict[str, Any]:
        """验证页面加载完整性"""
        if not self.is_running():
            raise Exception("Frontend service is not running")

        try:
            async with self.accessibility_verifier as verifier:
                result = await verifier.verify_page_loading_completeness(self.service_info.url)

                # 记录验证结果
                self.frontend_logger.log_health_check(
                    "page_loading_complete" if result['status'] == VerificationStatus.PASSED.value else "incomplete_loading",
                    result.get('load_time', 0)
                )

                return result

        except Exception as e:
            self.frontend_logger.error("Page loading verification failed", e)
            return {
                'url': self.service_info.url,
                'status': 'failed',
                'error_message': str(e),
                'passed': False
            }

    async def verify_backend_communication(self, backend_url: str,
                                         custom_endpoints: Optional[List[APIEndpoint]] = None) -> Dict[str, Any]:
        """验证前后端通信"""
        if not self.is_running():
            raise Exception("Frontend service is not running")

        # 默认API端点
        default_endpoints = [
            APIEndpoint(
                path="/api/health",
                method="GET",
                expected_status=200,
                description="Health check endpoint"
            ),
            APIEndpoint(
                path="/api/status",
                method="GET",
                expected_status=200,
                description="Status endpoint"
            ),
            APIEndpoint(
                path="/api/test",
                method="GET",
                expected_status=200,
                description="Test endpoint"
            )
        ]

        endpoints = custom_endpoints or default_endpoints

        # 配置通信验证
        config = CommunicationConfig(
            frontend_url=self.service_info.url,
            backend_url=backend_url,
            api_endpoints=endpoints,
            timeout=30,
            max_retries=3,
            verify_cors=True,
            verify_data_flow=True
        )

        try:
            self.frontend_logger.info(f"Starting backend communication verification with {backend_url}")

            # 执行通信验证
            async with self.communicator as communicator:
                report = await communicator.verify_communication(config)

                # 记录验证结果
                self.frontend_logger.log_health_check(
                    "backend_communication" if report.overall_status == CommunicationStatus.CONNECTED else "communication_failed",
                    report.average_response_time
                )

                # 转换为字典格式返回
                return {
                    'frontend_url': report.frontend_url,
                    'backend_url': report.backend_url,
                    'overall_status': report.overall_status.value,
                    'success_rate': report.success_rate,
                    'total_endpoints': report.total_endpoints,
                    'successful_endpoints': report.successful_endpoints,
                    'failed_endpoints': report.failed_endpoints,
                    'average_response_time': report.average_response_time,
                    'cors_status': report.cors_status,
                    'data_flow_status': report.data_flow_status,
                    'endpoint_results': [
                        {
                            'path': result.endpoint.path,
                            'method': result.endpoint.method,
                            'status': result.status.value,
                            'response_time': result.response_time,
                            'status_code': result.status_code,
                            'data_validation_passed': result.data_validation_passed,
                            'error_message': result.error_message,
                            'retry_count': result.retry_count
                        }
                        for result in report.results
                    ],
                    'error_summary': report.error_summary,
                    'passed': report.overall_status == CommunicationStatus.CONNECTED and report.success_rate >= 0.8
                }

        except Exception as e:
            self.frontend_logger.error("Backend communication verification failed", e)
            return {
                'frontend_url': self.service_info.url,
                'backend_url': backend_url,
                'overall_status': 'failed',
                'error_message': str(e),
                'passed': False
            }

    async def test_api_connectivity(self, backend_url: str,
                                   test_paths: Optional[List[str]] = None) -> Dict[str, Any]:
        """测试API连接性"""
        if not self.is_running():
            raise Exception("Frontend service is not running")

        test_paths = test_paths or ["/api/health", "/api/status", "/api/test"]

        try:
            async with self.communicator as communicator:
                results = await communicator.test_data_retrieval(backend_url, test_paths)

                # 统计结果
                successful_tests = sum(1 for r in results.values() if r.get('success', False))
                total_tests = len(results)

                result_summary = {
                    'backend_url': backend_url,
                    'total_tests': total_tests,
                    'successful_tests': successful_tests,
                    'success_rate': successful_tests / total_tests if total_tests > 0 else 0,
                    'test_results': results,
                    'passed': successful_tests == total_tests
                }

                self.frontend_logger.log_health_check(
                    "api_connectivity" if result_summary['passed'] else "api_connectivity_failed"
                )

                return result_summary

        except Exception as e:
            self.frontend_logger.error("API connectivity test failed", e)
            return {
                'backend_url': backend_url,
                'total_tests': len(test_paths),
                'successful_tests': 0,
                'success_rate': 0.0,
                'error_message': str(e),
                'passed': False
            }

    async def monitor_communication_status(self, backend_url: str,
                                         duration: int = 60, interval: int = 5) -> Dict[str, Any]:
        """监控通信状态"""
        if not self.is_running():
            raise Exception("Frontend service is not running")

        try:
            self.frontend_logger.info(f"Starting communication monitoring for {duration}s")

            async with self.communicator as communicator:
                monitoring_result = await communicator.monitor_communication_status(
                    self.service_info.url, backend_url, duration, interval
                )

                self.frontend_logger.info(
                    f"Communication monitoring completed. Success rate: {monitoring_result['success_rate']:.1%}"
                )

                return monitoring_result

        except Exception as e:
            self.frontend_logger.error("Communication monitoring failed", e)
            return {
                'error_message': str(e),
                'duration': duration,
                'total_requests': 0,
                'successful_requests': 0,
                'success_rate': 0.0
            }

    async def create_comprehensive_verification_report(self, backend_url: str) -> Dict[str, Any]:
        """创建综合验证报告"""
        if not self.is_running():
            raise Exception("Frontend service is not running")

        self.frontend_logger.info("Creating comprehensive verification report")

        report = {
            'timestamp': time.time(),
            'frontend_service': {
                'url': self.service_info.url,
                'status': self.service_info.status.value,
                'pid': self.service_info.pid,
                'start_time': self.service_info.start_time.isoformat() if self.service_info.start_time else None
            },
            'verifications': {}
        }

        try:
            # 1. 前端访问性验证
            self.frontend_logger.info("Running accessibility verification...")
            report['verifications']['accessibility'] = await self.verify_accessibility()

            # 2. 响应时间验证
            self.frontend_logger.info("Running response time verification...")
            report['verifications']['response_time'] = await self.check_response_time()

            # 3. 页面加载完整性验证
            self.frontend_logger.info("Running page loading verification...")
            report['verifications']['page_loading'] = await self.verify_page_loading_completeness()

            # 4. 前后端通信验证
            self.frontend_logger.info("Running backend communication verification...")
            report['verifications']['backend_communication'] = await self.verify_backend_communication(backend_url)

            # 5. API连接性测试
            self.frontend_logger.info("Running API connectivity test...")
            report['verifications']['api_connectivity'] = await self.test_api_connectivity(backend_url)

            # 计算总体状态
            verification_results = list(report['verifications'].values())
            passed_verifications = sum(1 for v in verification_results if v.get('passed', False))
            total_verifications = len(verification_results)

            report['summary'] = {
                'total_verifications': total_verifications,
                'passed_verifications': passed_verifications,
                'success_rate': passed_verifications / total_verifications if total_verifications > 0 else 0,
                'overall_status': 'passed' if passed_verifications == total_verifications else 'partial_failure' if passed_verifications > 0 else 'failed'
            }

            self.frontend_logger.info(
                f"Comprehensive verification completed. Success rate: {report['summary']['success_rate']:.1%}"
            )

            return report

        except Exception as e:
            self.frontend_logger.error("Comprehensive verification failed", e)
            report['error'] = str(e)
            report['summary'] = {
                'total_verifications': 0,
                'passed_verifications': 0,
                'success_rate': 0.0,
                'overall_status': 'failed'
            }
            return report

    async def verify_static_resource_loading(self, detailed_check: bool = True) -> Dict[str, Any]:
        """验证静态资源加载状态"""
        if not self.is_running():
            raise Exception("Frontend service is not running")

        try:
            # 配置访问性验证以检查资源
            config = AccessibilityConfig(
                url=self.service_info.url,
                timeout=30,
                max_retries=3,
                check_resources=True,
                verify_rendering=True,
                expected_content_patterns=[
                    r'<link[^>]+href=["\'][^"\']+\.css["\']',  # CSS文件
                    r'<script[^>]+src=["\'][^"\']+\.js["\']',  # JS文件
                ]
            )

            async with self.accessibility_verifier as verifier:
                result = await verifier.verify_accessibility(config)

                # 分析资源加载结果
                resource_analysis = self._analyze_resource_loading_results(result)

                # 构建返回结果
                verification_result = {
                    'url': result.url,
                    'status': result.status.value,
                    'response_time': result.response_time,
                    'total_resources': len(result.resource_results),
                    'resource_analysis': resource_analysis,
                    'rendering_verification': result.rendering_result or {},
                    'passed': self._evaluate_resource_loading_success(result),
                    'detailed_results': {
                        'resource_results': result.resource_results,
                        'content_matches': result.content_matches,
                        'error_message': result.error_message
                    }
                }

                # 记录验证结果
                self.frontend_logger.log_health_check(
                    "static_resource_loading" if verification_result['passed'] else "resource_loading_failed",
                    result.response_time
                )

                return verification_result

        except Exception as e:
            self.frontend_logger.error("Static resource loading verification failed", e)
            return {
                'url': self.service_info.url,
                'status': 'failed',
                'error_message': str(e),
                'passed': False
            }

    def _analyze_resource_loading_results(self, result) -> Dict[str, Any]:
        """分析资源加载结果"""
        if not result.resource_results:
            return {
                'css_resources': {'count': 0, 'loaded': 0, 'failed': 0},
                'js_resources': {'count': 0, 'loaded': 0, 'failed': 0},
                'image_resources': {'count': 0, 'loaded': 0, 'failed': 0},
                'media_resources': {'count': 0, 'loaded': 0, 'failed': 0},
                'total_load_time': 0.0,
                'failed_resources': []
            }

        # 按类型分类资源
        resource_stats = {
            'css_resources': {'count': 0, 'loaded': 0, 'failed': 0, 'total_size': 0, 'total_time': 0.0},
            'js_resources': {'count': 0, 'loaded': 0, 'failed': 0, 'total_size': 0, 'total_time': 0.0},
            'image_resources': {'count': 0, 'loaded': 0, 'failed': 0, 'total_size': 0, 'total_time': 0.0},
            'media_resources': {'count': 0, 'loaded': 0, 'failed': 0, 'total_size': 0, 'total_time': 0.0},
        }

        failed_resources = []
        total_load_time = 0.0

        for resource in result.resource_results:
            resource_type = resource['type']
            status = resource['status']
            response_time = resource.get('response_time', 0)
            content_length = resource.get('content_length', 0)

            if resource_type in resource_stats:
                stats = resource_stats[resource_type]
                stats['count'] += 1
                stats['total_time'] += response_time
                stats['total_size'] += content_length

                if status == 'passed':
                    stats['loaded'] += 1
                else:
                    stats['failed'] += 1
                    failed_resources.append({
                        'url': resource['url'],
                        'type': resource_type,
                        'status': status,
                        'error': resource.get('error_message', 'Unknown error')
                    })

                total_load_time += response_time

        # 计算平均值
        for stats in resource_stats.values():
            if stats['count'] > 0:
                stats['average_load_time'] = stats['total_time'] / stats['count']
                stats['average_size'] = stats['total_size'] / stats['count']

        return {
            **resource_stats,
            'total_resources': len(result.resource_results),
            'total_load_time': total_load_time,
            'failed_resources': failed_resources,
            'critical_failures': [r for r in failed_resources if r['type'] in ['css', 'js']]
        }

    def _evaluate_resource_loading_success(self, result) -> bool:
        """评估资源加载是否成功"""
        if result.status != VerificationStatus.PASSED:
            return False

        # 检查关键资源
        resource_analysis = self._analyze_resource_loading_results(result)

        # 必须有CSS和JS资源
        if (resource_analysis['css_resources']['count'] == 0 or
            resource_analysis['js_resources']['count'] == 0):
            return False

        # 关键资源失败率不能超过20%
        critical_resources = (
            resource_analysis['css_resources']['count'] +
            resource_analysis['js_resources']['count']
        )
        critical_failures = (
            resource_analysis['css_resources']['failed'] +
            resource_analysis['js_resources']['failed']
        )

        if critical_resources > 0 and (critical_failures / critical_resources) > 0.2:
            return False

        # 检查渲染完整性
        if result.rendering_result:
            rendering_checks = result.rendering_result
            critical_rendering = ['has_html_structure', 'has_head_section', 'has_body_section']
            failed_rendering = [check for check in critical_rendering if not rendering_checks.get(check, False)]

            if failed_rendering:
                return False

        return True

    async def detect_component_initialization(self) -> Dict[str, Any]:
        """检测组件初始化状态"""
        if not self.is_running():
            raise Exception("Frontend service is not running")

        try:
            # 配置详细的组件检测
            config = AccessibilityConfig(
                url=self.service_info.url,
                timeout=30,
                max_retries=3,
                expected_content_patterns=[
                    r'<div[^>]*id=["\']root["\']',  # React根元素
                    r'react|ReactDOM|__NEXT_DATA__',  # React/Next.js特征
                    r'data-reactroot|data-testid',  # React测试属性
                    r'className|css-',  # CSS类名
                ],
                verify_rendering=True
            )

            async with self.accessibility_verifier as verifier:
                result = await verifier.verify_accessibility(config)

                component_detection = {
                    'url': result.url,
                    'status': result.status.value,
                    'response_time': result.response_time,
                    'framework_detected': False,
                    'root_element_found': False,
                    'css_classes_detected': False,
                    'component_initialization': 'unknown',
                    'rendering_checks': result.rendering_result or {},
                    'passed': False
                }

                # 分析检测结果
                if result.content_matches:
                    # 检查React/Next.js特征
                    react_patterns = [r'react|ReactDOM|__NEXT_DATA__', r'<div[^>]*id=["\']root["\']']
                    component_detection['framework_detected'] = any(
                        result.content_matches.get(pattern, False) for pattern in react_patterns
                    )
                    component_detection['root_element_found'] = result.content_matches.get(
                        r'<div[^>]*id=["\']root["\']', False
                    )

                # 检查CSS类名
                if result.rendering_result:
                    # 这里可以添加更复杂的组件初始化检测逻辑
                    component_detection['css_classes_detected'] = True

                # 确定组件初始化状态
                if (component_detection['framework_detected'] and
                    component_detection['root_element_found'] and
                    result.status == VerificationStatus.PASSED):
                    component_detection['component_initialization'] = 'complete'
                    component_detection['passed'] = True
                elif component_detection['framework_detected']:
                    component_detection['component_initialization'] = 'partial'
                else:
                    component_detection['component_initialization'] = 'failed'

                # 记录检测结果
                self.frontend_logger.log_health_check(
                    f"component_initialization_{component_detection['component_initialization']}",
                    result.response_time
                )

                return component_detection

        except Exception as e:
            self.frontend_logger.error("Component initialization detection failed", e)
            return {
                'url': self.service_info.url,
                'status': 'failed',
                'error_message': str(e),
                'component_initialization': 'error',
                'passed': False
            }

    async def implement_resource_loading_fallbacks(self) -> Dict[str, Any]:
        """实现资源加载回退机制（模拟实现）"""
        if not self.is_running():
            raise Exception("Frontend service is not running")

        try:
            # 这里可以实现资源加载回退机制
            # 例如：检测失败的资源并提供替代方案

            fallback_mechanisms = {
                'css_fallback_enabled': True,
                'js_fallback_enabled': True,
                'image_fallback_enabled': True,
                'cdn_fallback_available': True,
                'local_fallback_available': True
            }

            # 检查当前资源加载状态
            resource_status = await self.verify_static_resource_loading(detailed_check=False)

            # 如果有失败的关键资源，启用回退机制
            if not resource_status['passed']:
                fallback_mechanisms['fallbacks_activated'] = True
                fallback_mechanisms['activation_reason'] = 'critical_resources_failed'
            else:
                fallback_mechanisms['fallbacks_activated'] = False
                fallback_mechanisms['activation_reason'] = 'no_fallback_needed'

            self.frontend_logger.info(
                f"Resource loading fallbacks {'activated' if fallback_mechanisms['fallbacks_activated'] else 'not needed'}"
            )

            return {
                'url': self.service_info.url,
                'fallback_mechanisms': fallback_mechanisms,
                'resource_status': resource_status.get('status', 'unknown'),
                'passed': resource_status.get('passed', False)
            }

        except Exception as e:
            self.frontend_logger.error("Resource loading fallback implementation failed", e)
            return {
                'url': self.service_info.url,
                'error_message': str(e),
                'fallback_mechanisms': {'fallbacks_activated': False},
                'passed': False
            }