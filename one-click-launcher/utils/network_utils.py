"""
网络工具模块

提供网络连接检测、HTTP请求、包管理器可达性检查等功能。
"""

import asyncio
import socket
import os
import subprocess
import re
from typing import Optional, Tuple, Dict, List, Any
import urllib.request
import urllib.error
import json
from dataclasses import dataclass
from enum import Enum

from utils.logger import get_logger

logger = get_logger(__name__)


class NetworkStatus(Enum):
    """Network connection status"""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    PROXY_DETECTED = "proxy_detected"
    FIREWALL_BLOCKED = "firewall_blocked"
    UNKNOWN = "unknown"


class PackageManagerType(Enum):
    """Package manager types"""
    NPM = "npm"
    PIP = "pip"
    GIT = "git"


@dataclass
class ProxyConfig:
    """Proxy configuration information"""
    enabled: bool
    http_proxy: Optional[str] = None
    https_proxy: Optional[str] = None
    no_proxy: Optional[List[str]] = None
    proxy_auth: Optional[bool] = None


@dataclass
class PackageManagerStatus:
    """Package manager accessibility status"""
    name: str
    type: PackageManagerType
    accessible: bool
    response_time: Optional[float] = None
    error_message: Optional[str] = None
    test_url: Optional[str] = None


@dataclass
class NetworkInfo:
    """Comprehensive network information"""
    status: NetworkStatus
    internet_connected: bool
    proxy_config: ProxyConfig
    package_managers: Dict[PackageManagerType, PackageManagerStatus]
    local_ip: Optional[str] = None
    connection_method: Optional[str] = None


async def check_internet_connection(timeout: int = 5) -> bool:
    """检查网络连接状态"""
    test_urls = [
        "https://www.baidu.com",
        "https://www.google.com"
    ]

    for url in test_urls:
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: urllib.request.urlopen(url, timeout=timeout)
            )
            logger.info(f"网络连接正常 (通过 {url} 验证)")
            return True
        except Exception as e:
            logger.debug(f"网络检测失败 {url}: {e}")
            continue

    logger.warning("网络连接异常或不可用")
    return False


async def check_port_available(host: str = "localhost", port: int = 80, timeout: int = 3) -> bool:
    """检查端口是否可用"""
    try:
        loop = asyncio.get_event_loop()

        def check_socket():
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(timeout)
                result = sock.connect_ex((host, port))
                return result != 0

        is_available = await loop.run_in_executor(None, check_socket)
        return is_available

    except Exception as e:
        logger.error(f"检查端口 {host}:{port} 失败: {e}")
        return False


def get_local_ip() -> Optional[str]:
    """获取本地IP地址"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
    except Exception as e:
        logger.error(f"获取本地IP失败: {e}")
        return None


def is_valid_port(port: int) -> bool:
    """验证端口号是否有效"""
    return 1 <= port <= 65535


class NetworkChecker:
    """Comprehensive network checking and diagnostics class"""

    # Test URLs for different services
    TEST_URLS = {
        "general": [
            "https://www.google.com",
            "https://www.baidu.com",
            "https://httpbin.org/get"
        ],
        "npm": [
            "https://registry.npmjs.org",
            "https://www.npmjs.com"
        ],
        "pip": [
            "https://pypi.org/simple",
            "https://pypi.org"
        ],
        "git": [
            "https://github.com",
            "https://gitlab.com",
            "https://bitbucket.org"
        ]
    }

    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)

    def detect_proxy_config(self) -> ProxyConfig:
        """
        Detect proxy configuration from environment variables and system settings.

        Returns:
            ProxyConfig object with detected proxy settings
        """
        http_proxy = (
            os.environ.get("HTTP_PROXY") or
            os.environ.get("http_proxy") or
            os.environ.get("ALL_PROXY") or
            os.environ.get("all_proxy")
        )

        https_proxy = (
            os.environ.get("HTTPS_PROXY") or
            os.environ.get("https_proxy")
        )

        no_proxy_env = (
            os.environ.get("NO_PROXY") or
            os.environ.get("no_proxy")
        )

        no_proxy_list = []
        if no_proxy_env:
            no_proxy_list = [item.strip() for item in no_proxy_env.split(",") if item.strip()]

        proxy_enabled = bool(http_proxy or https_proxy)

        # Check for proxy authentication
        proxy_auth = False
        if http_proxy and "@" in http_proxy:
            proxy_auth = True
        elif https_proxy and "@" in https_proxy:
            proxy_auth = True

        config = ProxyConfig(
            enabled=proxy_enabled,
            http_proxy=http_proxy,
            https_proxy=https_proxy,
            no_proxy=no_proxy_list,
            proxy_auth=proxy_auth
        )

        if proxy_enabled:
            self.logger.info(f"Proxy configuration detected: HTTP={http_proxy}, HTTPS={https_proxy}")
        else:
            self.logger.debug("No proxy configuration detected")

        return config

    async def test_url_accessibility(self, url: str, timeout: int = 10) -> Tuple[bool, float, str]:
        """
        Test if a URL is accessible.

        Args:
            url: URL to test
            timeout: Request timeout in seconds

        Returns:
            Tuple of (accessible, response_time, error_message)
        """
        import time
        start_time = time.time()

        try:
            # Create request with appropriate headers
            request = urllib.request.Request(
                url,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Accept': 'application/json, text/plain, */*',
                    'Accept-Language': 'en-US,en;q=0.9',
                }
            )

            # Make the request
            with urllib.request.urlopen(request, timeout=timeout) as response:
                response_time = time.time() - start_time
                response_data = response.read(1024)  # Read first 1KB

                if response.status == 200:
                    self.logger.debug(f"URL accessible: {url} ({response_time:.2f}s)")
                    return True, response_time, ""
                else:
                    error_msg = f"HTTP {response.status}"
                    self.logger.warning(f"URL returned error: {url} - {error_msg}")
                    return False, response_time, error_msg

        except urllib.error.HTTPError as e:
            response_time = time.time() - start_time
            error_msg = f"HTTP {e.code}: {e.reason}"
            self.logger.warning(f"HTTP error for {url}: {error_msg}")
            return False, response_time, error_msg

        except urllib.error.URLError as e:
            response_time = time.time() - start_time
            error_msg = f"URL Error: {str(e.reason)}"
            self.logger.warning(f"URL error for {url}: {error_msg}")
            return False, response_time, error_msg

        except Exception as e:
            response_time = time.time() - start_time
            error_msg = f"Unexpected error: {str(e)}"
            self.logger.error(f"Unexpected error testing {url}: {error_msg}")
            return False, response_time, error_msg

    async def check_package_manager_accessibility(self,
                                                 package_manager: PackageManagerType,
                                                 timeout: int = 15) -> PackageManagerStatus:
        """
        Check if a package manager's repositories are accessible.

        Args:
            package_manager: Type of package manager to check
            timeout: Request timeout in seconds

        Returns:
            PackageManagerStatus with accessibility information
        """
        test_urls = self.TEST_URLS.get(package_manager.value, [])
        if not test_urls:
            return PackageManagerStatus(
                name=package_manager.value,
                type=package_manager,
                accessible=False,
                error_message="No test URLs configured"
            )

        # Test multiple URLs for reliability
        accessible_count = 0
        total_time = 0
        errors = []

        for url in test_urls:
            accessible, response_time, error = await self.test_url_accessibility(url, timeout)
            if accessible:
                accessible_count += 1
                total_time += response_time
            else:
                errors.append(f"{url}: {error}")

        # Consider accessible if at least one URL works
        is_accessible = accessible_count > 0
        avg_response_time = total_time / accessible_count if accessible_count > 0 else None
        test_url = test_urls[0]  # Primary test URL

        if not is_accessible:
            error_message = "; ".join(errors[:3])  # Limit error message length
        else:
            error_message = None

        status = PackageManagerStatus(
            name=package_manager.value,
            type=package_manager,
            accessible=is_accessible,
            response_time=avg_response_time,
            error_message=error_message,
            test_url=test_url
        )

        self.logger.info(
            f"{package_manager.value} accessibility: {'✓' if is_accessible else '✗'} "
            f"({avg_response_time:.2f}s if accessible)"
        )

        return status

    async def check_all_package_managers(self, timeout: int = 15) -> Dict[PackageManagerType, PackageManagerStatus]:
        """
        Check accessibility for all supported package managers.

        Args:
            timeout: Request timeout for each test

        Returns:
            Dictionary mapping package manager types to their status
        """
        self.logger.info("Checking package manager accessibility...")

        results = {}
        package_managers = [PackageManagerType.NPM, PackageManagerType.PIP, PackageManagerType.GIT]

        # Run checks in parallel for efficiency
        tasks = [
            self.check_package_manager_accessibility(pm, timeout)
            for pm in package_managers
        ]

        statuses = await asyncio.gather(*tasks, return_exceptions=True)

        for i, package_manager in enumerate(package_managers):
            if isinstance(statuses[i], Exception):
                self.logger.error(f"Error checking {package_manager.value}: {statuses[i]}")
                results[package_manager] = PackageManagerStatus(
                    name=package_manager.value,
                    type=package_manager,
                    accessible=False,
                    error_message=f"Check failed: {str(statuses[i])}"
                )
            else:
                results[package_manager] = statuses[i]

        return results

    def detect_offline_mode(self) -> bool:
        """
        Detect if the system is in offline mode.

        Returns:
            True if offline mode is detected
        """
        # Check various indicators of offline mode
        offline_indicators = []

        # Check for explicit offline mode settings
        offline_env_vars = [
            "OFFLINE_MODE",
            "WORK_OFFLINE",
            "PYTHONOFFLINE",
            "NPM_CONFIG_OFFLINE"
        ]

        for var in offline_env_vars:
            if os.environ.get(var, "").lower() in ["true", "1", "yes"]:
                offline_indicators.append(f"Environment variable {var} set")
                self.logger.info(f"Offline mode detected via {var}")

        # Check network interface status
        try:
            # Try to get local network interfaces
            result = subprocess.run(
                ["ip", "link", "show"] if os.name != "nt" else ["netsh", "interface", "show", "interface"],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                # Look for active network interfaces
                output = result.stdout.lower()
                active_indicators = ["up", "connected", "running"]

                has_active_interface = any(indicator in output for indicator in active_indicators)
                if not has_active_interface:
                    offline_indicators.append("No active network interfaces detected")
        except:
            pass  # Network interface check failed, continue with other checks

        # Check if we can resolve basic hostnames
        try:
            import socket
            socket.gethostbyname("google.com")
            socket.gethostbyname("localhost")
        except socket.gaierror:
            offline_indicators.append("DNS resolution failed")

        is_offline = len(offline_indicators) > 0

        if is_offline:
            self.logger.warning(f"Offline mode detected: {', '.join(offline_indicators)}")
        else:
            self.logger.debug("No offline mode indicators found")

        return is_offline

    async def get_comprehensive_network_info(self, timeout: int = 15) -> NetworkInfo:
        """
        Get comprehensive network information including connectivity, proxy, and package manager status.

        Args:
            timeout: Timeout for network requests

        Returns:
            NetworkInfo object with comprehensive network status
        """
        self.logger.info("Getting comprehensive network information...")

        # Check basic internet connectivity
        internet_connected = await check_internet_connection(timeout)

        # Determine network status
        if not internet_connected:
            status = NetworkStatus.DISCONNECTED
        else:
            status = NetworkStatus.CONNECTED

        # Detect proxy configuration
        proxy_config = self.detect_proxy_config()
        if proxy_config.enabled and status == NetworkStatus.CONNECTED:
            status = NetworkStatus.PROXY_DETECTED

        # Check package manager accessibility
        package_managers = await self.check_all_package_managers(timeout)

        # Get local IP
        local_ip = get_local_ip()

        # Detect connection method (simplified)
        connection_method = "direct"
        if proxy_config.enabled:
            connection_method = "proxy"
        elif self.detect_offline_mode():
            connection_method = "offline"
            status = NetworkStatus.DISCONNECTED

        network_info = NetworkInfo(
            status=status,
            internet_connected=internet_connected,
            proxy_config=proxy_config,
            package_managers=package_managers,
            local_ip=local_ip,
            connection_method=connection_method
        )

        self.logger.info(
            f"Network status: {status.value}, "
            f"Internet: {'✓' if internet_connected else '✗'}, "
            f"Proxy: {'✓' if proxy_config.enabled else '✗'}, "
            f"Local IP: {local_ip}"
        )

        return network_info

    def is_package_manager_accessible(self, package_manager: PackageManagerType,
                                     network_info: Optional[NetworkInfo] = None) -> bool:
        """
        Quick check if a package manager is accessible.

        Args:
            package_manager: Package manager type to check
            network_info: Previously gathered network info (optional)

        Returns:
            True if package manager is accessible
        """
        if network_info and package_manager in network_info.package_managers:
            return network_info.package_managers[package_manager].accessible

        # Fallback to basic connectivity check
        return check_internet_connection()