"""
智能安装策略选择器

This module provides intelligent installation method selection capabilities
including online/offline mode switching, network detection, and mirror source
selection for the one-click launcher.
"""

import os
import socket
import urllib.request
import urllib.error
import subprocess
import json
import time
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

from utils.logger import get_logger
from core.dependency_analyzer import ProjectDependency, DependencyAnalysis
from utils.progress_tracker import ProgressTracker

logger = get_logger(__name__)


class InstallationMode(Enum):
    """安装模式"""
    ONLINE = "online"           # 在线模式，使用包管理器
    OFFLINE = "offline"         # 离线模式，使用本地安装包
    HYBRID = "hybrid"           # 混合模式，优先离线，回退在线
    AUTO = "auto"              # 自动模式，根据网络状态选择


class NetworkStatus(Enum):
    """网络状态"""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    SLOW = "slow"
    UNSTABLE = "unstable"
    UNKNOWN = "unknown"


class PackageSourceType(Enum):
    """包源类型"""
    OFFICIAL = "official"       # 官方源
    MIRROR = "mirror"          # 镜像源
    LOCAL = "local"            # 本地文件
    CACHE = "cache"            # 缓存文件


@dataclass
class NetworkInfo:
    """网络信息"""
    status: NetworkStatus
    latency_ms: Optional[float] = None
    bandwidth_mbps: Optional[float] = None
    connection_type: Optional[str] = None
    dns_servers: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)


@dataclass
class PackageSource:
    """包源信息"""
    name: str
    url: str
    source_type: PackageSourceType
    ecosystem: str
    priority: int = 100
    is_available: bool = True
    response_time_ms: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class InstallationStrategy:
    """安装策略"""
    dependency: ProjectDependency
    mode: InstallationMode
    package_manager: str
    source: PackageSource
    install_command: List[str]
    fallback_sources: List[PackageSource] = field(default_factory=list)
    estimated_time_sec: Optional[int] = None
    confidence_score: float = 0.0


class NetworkDetector:
    """网络检测器"""

    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
        self.test_urls = [
            "https://pypi.org/simple/",
            "https://registry.npmjs.org/",
            "https://github.com",
            "https://google.com"
        ]

    def detect_network_status(self) -> NetworkInfo:
        """检测网络状态"""
        self.logger.info("开始检测网络状态...")

        # 1. 基本连接测试
        connectivity_result = self._test_connectivity()
        if not connectivity_result["connected"]:
            return NetworkInfo(status=NetworkStatus.DISCONNECTED)

        # 2. 延迟测试
        latency_result = self._test_latency()

        # 3. 带宽测试（简化版）
        bandwidth_result = self._test_bandwidth()

        # 4. 确定网络状态
        status = self._determine_status(connectivity_result, latency_result, bandwidth_result)

        network_info = NetworkInfo(
            status=status,
            latency_ms=latency_result.get("avg_latency"),
            bandwidth_mbps=bandwidth_result.get("bandwidth"),
            timestamp=time.time()
        )

        self.logger.info(f"网络状态检测完成: {status.value}")
        return network_info

    def _test_connectivity(self) -> Dict[str, Any]:
        """测试基本连接"""
        connected_urls = []
        failed_urls = []

        for url in self.test_urls:
            try:
                response = urllib.request.urlopen(url, timeout=5)
                if response.getcode() == 200:
                    connected_urls.append(url)
            except Exception as e:
                failed_urls.append(url)
                self.logger.debug(f"连接测试失败 {url}: {e}")

        return {
            "connected": len(connected_urls) > 0,
            "connected_urls": connected_urls,
            "failed_urls": failed_urls,
            "success_rate": len(connected_urls) / len(self.test_urls)
        }

    def _test_latency(self) -> Dict[str, Any]:
        """测试网络延迟"""
        latencies = []

        for url in self.test_urls[:3]:  # 测试前3个URL
            try:
                start_time = time.time()
                response = urllib.request.urlopen(url, timeout=5)
                end_time = time.time()

                if response.getcode() == 200:
                    latency = (end_time - start_time) * 1000  # 转换为毫秒
                    latencies.append(latency)
            except Exception as e:
                self.logger.debug(f"延迟测试失败 {url}: {e}")

        if latencies:
            return {
                "avg_latency": sum(latencies) / len(latencies),
                "min_latency": min(latencies),
                "max_latency": max(latencies),
                "sample_count": len(latencies)
            }
        else:
            return {"avg_latency": None}

    def _test_bandwidth(self) -> Dict[str, Any]:
        """测试网络带宽（简化版）"""
        try:
            # 使用小文件测试下载速度
            test_url = "https://httpbin.org/bytes/1024"  # 1KB 测试文件
            start_time = time.time()

            with urllib.request.urlopen(test_url, timeout=10) as response:
                data = response.read()
                end_time = time.time()

                if response.getcode() == 200:
                    size_kb = len(data) / 1024
                    time_sec = end_time - start_time
                    bandwidth_mbps = (size_kb / 1024) / time_sec * 8  # 转换为 Mbps

                    return {
                        "bandwidth": bandwidth_mbps,
                        "test_size_kb": size_kb,
                        "test_time_sec": time_sec
                    }
        except Exception as e:
            self.logger.debug(f"带宽测试失败: {e}")

        return {"bandwidth": None}

    def _determine_status(self, connectivity: Dict, latency: Dict, bandwidth: Dict) -> NetworkStatus:
        """确定网络状态"""
        success_rate = connectivity["success_rate"]

        if success_rate == 0:
            return NetworkStatus.DISCONNECTED
        elif success_rate < 0.5:
            return NetworkStatus.UNSTABLE
        else:
            avg_latency = latency.get("avg_latency")
            if avg_latency is None:
                return NetworkStatus.UNKNOWN
            elif avg_latency > 2000:  # 超过2秒
                return NetworkStatus.SLOW
            else:
                return NetworkStatus.CONNECTED


class MirrorSelector:
    """镜像源选择器"""

    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
        self._mirror_cache = {}

    def get_available_mirrors(self, ecosystem: str) -> List[PackageSource]:
        """获取可用的镜像源"""
        if ecosystem in self._mirror_cache:
            return self._mirror_cache[ecosystem]

        mirrors = self._load_mirrors_for_ecosystem(ecosystem)
        self._mirror_cache[ecosystem] = mirrors
        return mirrors

    def _load_mirrors_for_ecosystem(self, ecosystem: str) -> List[PackageSource]:
        """加载指定生态系统的镜像源"""
        if ecosystem == "python":
            return [
                PackageSource(
                    name="pypi-official",
                    url="https://pypi.org/simple/",
                    source_type=PackageSourceType.OFFICIAL,
                    ecosystem=ecosystem,
                    priority=100
                ),
                PackageSource(
                    name="pypi-tuna",
                    url="https://pypi.tuna.tsinghua.edu.cn/simple/",
                    source_type=PackageSourceType.MIRROR,
                    ecosystem=ecosystem,
                    priority=90
                ),
                PackageSource(
                    name="pypi-aliyun",
                    url="https://mirrors.aliyun.com/pypi/simple/",
                    source_type=PackageSourceType.MIRROR,
                    ecosystem=ecosystem,
                    priority=85
                ),
            ]
        elif ecosystem == "nodejs":
            return [
                PackageSource(
                    name="npm-official",
                    url="https://registry.npmjs.org/",
                    source_type=PackageSourceType.OFFICIAL,
                    ecosystem=ecosystem,
                    priority=100
                ),
                PackageSource(
                    name="npm-taobao",
                    url="https://registry.npmmirror.com/",
                    source_type=PackageSourceType.MIRROR,
                    ecosystem=ecosystem,
                    priority=90
                ),
                PackageSource(
                    name="npm-cnpm",
                    url="https://r.cnpmjs.org/",
                    source_type=PackageSourceType.MIRROR,
                    ecosystem=ecosystem,
                    priority=85
                ),
            ]
        else:
            return []

    def select_best_mirror(self, ecosystem: str, network_info: NetworkInfo) -> Optional[PackageSource]:
        """选择最佳镜像源"""
        mirrors = self.get_available_mirrors(ecosystem)
        if not mirrors:
            return None

        # 网络状况不好时优先选择镜像源
        if network_info.status in [NetworkStatus.SLOW, NetworkStatus.UNSTABLE]:
            mirror_mirrors = [m for m in mirrors if m.source_type == PackageSourceType.MIRROR]
            if mirror_mirrors:
                return max(mirror_mirrors, key=lambda m: m.priority)

        # 网络状况良好时测试并选择响应最快的源
        best_mirror = self._test_mirror_speed(mirrors)
        return best_mirror or mirrors[0]

    def _test_mirror_speed(self, mirrors: List[PackageSource]) -> Optional[PackageSource]:
        """测试镜像源速度"""
        tested_mirrors = []

        def test_mirror(mirror: PackageSource) -> Tuple[PackageSource, Optional[float]]:
            try:
                start_time = time.time()
                response = urllib.request.urlopen(mirror.url, timeout=3)
                end_time = time.time()

                if response.getcode() == 200:
                    response_time = (end_time - start_time) * 1000
                    return mirror, response_time
            except Exception as e:
                self.logger.debug(f"测试镜像源失败 {mirror.name}: {e}")

            return mirror, None

        # 并发测试
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(test_mirror, mirror) for mirror in mirrors[:4]]

            for future in as_completed(futures):
                mirror, response_time = future.result()
                if response_time is not None:
                    mirror.response_time_ms = response_time
                    tested_mirrors.append(mirror)

        if tested_mirrors:
            return min(tested_mirrors, key=lambda m: m.response_time_ms)

        return None


class InstallationStrategySelector:
    """
    安装策略选择器

    功能特性：
    - 智能模式选择（在线/离线/混合）
    - 网络状态检测
    - 镜像源选择
    - 安装方法决策
    - 回退机制
    """

    def __init__(self, config_manager: Optional[Any] = None):
        """
        初始化策略选择器

        Args:
            config_manager: 配置管理器
        """
        self.config_manager = config_manager
        self.logger = get_logger(self.__class__.__name__)
        self.network_detector = NetworkDetector()
        self.mirror_selector = MirrorSelector()

        # 策略缓存
        self._network_cache: Optional[NetworkInfo] = None
        self._cache_timestamp: float = 0
        self._cache_ttl: float = 300  # 5分钟缓存

    def select_installation_strategy(
        self,
        dependency: ProjectDependency,
        preferred_mode: Optional[InstallationMode] = None,
        progress_tracker: Optional[ProgressTracker] = None
    ) -> InstallationStrategy:
        """
        选择安装策略

        Args:
            dependency: 依赖项
            preferred_mode: 首选模式
            progress_tracker: 进度跟踪器

        Returns:
            安装策略
        """
        self.logger.info(f"为 {dependency.name} 选择安装策略...")

        # 1. 获取网络状态
        network_info = self._get_network_info()

        # 2. 确定安装模式
        mode = self._determine_installation_mode(preferred_mode, network_info)

        # 3. 选择包管理器
        package_manager = self._select_package_manager(dependency.ecosystem)

        # 4. 选择包源
        source = self._select_package_source(dependency.ecosystem, mode, network_info)

        # 5. 生成安装命令
        install_command = self._generate_install_command(
            dependency, package_manager, source, mode
        )

        # 6. 准备回退源
        fallback_sources = self._prepare_fallback_sources(
            dependency.ecosystem, source, mode
        )

        # 7. 估算安装时间
        estimated_time = self._estimate_installation_time(dependency, mode)

        # 8. 计算置信度
        confidence = self._calculate_confidence(dependency, mode, network_info)

        strategy = InstallationStrategy(
            dependency=dependency,
            mode=mode,
            package_manager=package_manager,
            source=source,
            install_command=install_command,
            fallback_sources=fallback_sources,
            estimated_time_sec=estimated_time,
            confidence_score=confidence
        )

        self.logger.info(f"策略选择完成: {mode.value}, 源: {source.name}, 置信度: {confidence:.2f}")
        return strategy

    def _get_network_info(self) -> NetworkInfo:
        """获取网络信息（带缓存）"""
        current_time = time.time()

        # 检查缓存是否有效
        if (self._network_cache and
            current_time - self._cache_timestamp < self._cache_ttl):
            return self._network_cache

        # 重新检测网络状态
        network_info = self.network_detector.detect_network_status()
        self._network_cache = network_info
        self._cache_timestamp = current_time

        return network_info

    def _determine_installation_mode(
        self,
        preferred_mode: Optional[InstallationMode],
        network_info: NetworkInfo
    ) -> InstallationMode:
        """确定安装模式"""
        if preferred_mode:
            return preferred_mode

        # 根据网络状态自动选择
        if network_info.status == NetworkStatus.DISCONNECTED:
            return InstallationMode.OFFLINE
        elif network_info.status in [NetworkStatus.SLOW, NetworkStatus.UNSTABLE]:
            return InstallationMode.HYBRID
        else:
            return InstallationMode.ONLINE

    def _select_package_manager(self, ecosystem: str) -> str:
        """选择包管理器"""
        if self.config_manager:
            manager = self.config_manager.get_package_manager(ecosystem)
            if manager != "unknown":
                return manager

        # 默认包管理器
        default_managers = {
            "python": "pip",
            "nodejs": "npm",
            "database": "system",
            "system": "system"
        }

        return default_managers.get(ecosystem, "unknown")

    def _select_package_source(
        self,
        ecosystem: str,
        mode: InstallationMode,
        network_info: NetworkInfo
    ) -> PackageSource:
        """选择包源"""
        if mode == InstallationMode.OFFLINE:
            # 离线模式使用本地源
            return PackageSource(
                name="local-cache",
                url="",
                source_type=PackageSourceType.LOCAL,
                ecosystem=ecosystem,
                priority=100
            )

        # 在线或混合模式选择最佳源
        mirror = self.mirror_selector.select_best_mirror(ecosystem, network_info)

        if mirror:
            return mirror

        # 回退到默认源
        return PackageSource(
            name="default",
            url="",
            source_type=PackageSourceType.OFFICIAL,
            ecosystem=ecosystem,
            priority=50
        )

    def _generate_install_command(
        self,
        dependency: ProjectDependency,
        package_manager: str,
        source: PackageSource,
        mode: InstallationMode
    ) -> List[str]:
        """生成安装命令"""
        if dependency.ecosystem == "python":
            return self._generate_python_command(dependency, package_manager, source, mode)
        elif dependency.ecosystem == "nodejs":
            return self._generate_nodejs_command(dependency, package_manager, source, mode)
        else:
            return []

    def _generate_python_command(
        self,
        dependency: ProjectDependency,
        package_manager: str,
        source: PackageSource,
        mode: InstallationMode
    ) -> List[str]:
        """生成 Python 安装命令"""
        if package_manager == "pip":
            command = ["pip", "install"]

            # 添加镜像源参数
            if mode != InstallationMode.OFFLINE and source.url:
                command.extend(["-i", source.url])

            # 添加依赖规格
            dep_spec = f"{dependency.name}{dependency.version_spec or ''}"
            command.append(dep_spec)

            return command
        else:
            # 其他包管理器（如 conda）
            return [package_manager, "install", dependency.name]

    def _generate_nodejs_command(
        self,
        dependency: ProjectDependency,
        package_manager: str,
        source: PackageSource,
        mode: InstallationMode
    ) -> List[str]:
        """生成 Node.js 安装命令"""
        if package_manager == "npm":
            command = ["npm", "install"]

            # 添加镜像源参数
            if mode != InstallationMode.OFFLINE and source.url:
                command.extend(["--registry", source.url])

            # 添加依赖规格
            dep_spec = f"{dependency.name}@{dependency.version_spec or 'latest'}"
            command.append(dep_spec)

            return command
        elif package_manager == "yarn":
            command = ["yarn", "add"]

            if mode != InstallationMode.OFFLINE and source.url:
                command.extend(["--registry", source.url])

            dep_spec = f"{dependency.name}@{dependency.version_spec or 'latest'}"
            command.append(dep_spec)

            return command
        else:
            return [package_manager, "install", dependency.name]

    def _prepare_fallback_sources(
        self,
        ecosystem: str,
        primary_source: PackageSource,
        mode: InstallationMode
    ) -> List[PackageSource]:
        """准备回退源"""
        all_sources = self.mirror_selector.get_available_mirrors(ecosystem)

        # 排除当前源并按优先级排序
        fallback_sources = [
            source for source in all_sources
            if source.name != primary_source.name
        ]

        fallback_sources.sort(key=lambda s: s.priority, reverse=True)

        return fallback_sources[:3]  # 最多保留3个回退源

    def _estimate_installation_time(
        self,
        dependency: ProjectDependency,
        mode: InstallationMode
    ) -> int:
        """估算安装时间（秒）"""
        # 基础时间
        base_time = {
            "python": 60,
            "nodejs": 120,
            "database": 180,
            "system": 300
        }

        base = base_time.get(dependency.ecosystem, 120)

        # 根据模式调整
        mode_multiplier = {
            InstallationMode.ONLINE: 1.0,
            InstallationMode.OFFLINE: 0.5,
            InstallationMode.HYBRID: 1.2,
            InstallationMode.AUTO: 1.0
        }

        multiplier = mode_multiplier.get(mode, 1.0)

        return int(base * multiplier)

    def _calculate_confidence(
        self,
        dependency: ProjectDependency,
        mode: InstallationMode,
        network_info: NetworkInfo
    ) -> float:
        """计算策略置信度"""
        confidence = 0.5  # 基础置信度

        # 根据网络状态调整
        network_scores = {
            NetworkStatus.CONNECTED: 0.3,
            NetworkStatus.SLOW: 0.1,
            NetworkStatus.UNSTABLE: 0.1,
            NetworkStatus.DISCONNECTED: -0.2,
            NetworkStatus.UNKNOWN: 0.0
        }

        confidence += network_scores.get(network_info.status, 0.0)

        # 根据模式调整
        mode_scores = {
            InstallationMode.ONLINE: 0.1,
            InstallationMode.OFFLINE: 0.0,
            InstallationMode.HYBRID: 0.2,
            InstallationMode.AUTO: 0.1
        }

        confidence += mode_scores.get(mode, 0.0)

        # 确保置信度在合理范围内
        return max(0.0, min(1.0, confidence))

    def batch_select_strategies(
        self,
        dependencies: List[ProjectDependency],
        preferred_mode: Optional[InstallationMode] = None,
        progress_tracker: Optional[ProgressTracker] = None
    ) -> List[InstallationStrategy]:
        """批量选择安装策略"""
        self.logger.info(f"批量选择 {len(dependencies)} 个依赖的安装策略...")

        strategies = []

        if progress_tracker:
            progress_tracker.start_installation()

        for i, dep in enumerate(dependencies):
            try:
                if progress_tracker:
                    progress_tracker.start_step(i)

                strategy = self.select_installation_strategy(dep, preferred_mode, progress_tracker)
                strategies.append(strategy)

                if progress_tracker:
                    progress_tracker.complete_step(i, True)

            except Exception as e:
                self.logger.error(f"为 {dep.name} 选择策略失败: {e}")

                if progress_tracker:
                    progress_tracker.complete_step(i, False, str(e))

        if progress_tracker:
            progress_tracker.complete_installation(len(strategies) == len(dependencies))

        self.logger.info(f"批量策略选择完成: {len(strategies)} 个策略")
        return strategies

    def get_strategy_summary(self, strategies: List[InstallationStrategy]) -> Dict[str, Any]:
        """获取策略摘要"""
        if not strategies:
            return {}

        modes = {}
        ecosystems = {}
        sources = {}
        total_confidence = 0

        for strategy in strategies:
            # 统计模式
            mode = strategy.mode.value
            modes[mode] = modes.get(mode, 0) + 1

            # 统计生态系统
            ecosystem = strategy.dependency.ecosystem
            ecosystems[ecosystem] = ecosystems.get(ecosystem, 0) + 1

            # 统计源类型
            source_type = strategy.source.source_type.value
            sources[source_type] = sources.get(source_type, 0) + 1

            total_confidence += strategy.confidence_score

        return {
            "total_strategies": len(strategies),
            "average_confidence": total_confidence / len(strategies),
            "modes_distribution": modes,
            "ecosystems_distribution": ecosystems,
            "sources_distribution": sources,
            "estimated_total_time_sec": sum(s.estimated_time_sec or 0 for s in strategies)
        }