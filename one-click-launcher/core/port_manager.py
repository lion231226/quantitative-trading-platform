"""
端口管理器

提供端口扫描、冲突检测、自动分配和冲突解决功能。
支持端口范围管理、持久化存储和用户确认机制。
"""

import asyncio
import socket
import psutil
import json
from typing import Dict, List, Optional, Any, Set, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
import time
from pathlib import Path
from datetime import datetime

from utils.logger import get_logger

logger = get_logger(__name__)


class PortStatus(Enum):
    """端口状态枚举"""
    FREE = "free"
    OCCUPIED = "occupied"
    RESERVED = "reserved"
    IN_USE = "in_use"
    CONFLICT = "conflict"
    UNKNOWN = "unknown"


@dataclass
class PortInfo:
    """端口信息"""
    port: int
    host: str = "localhost"
    status: PortStatus = PortStatus.UNKNOWN
    process_name: Optional[str] = None
    process_pid: Optional[int] = None
    service_name: Optional[str] = None
    last_checked: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'port': self.port,
            'host': self.host,
            'status': self.status.value,
            'process_name': self.process_name,
            'process_pid': self.process_pid,
            'service_name': self.service_name,
            'last_checked': self.last_checked.isoformat() if self.last_checked else None,
            'metadata': self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PortInfo':
        """从字典创建端口信息"""
        port_info = cls(
            port=data['port'],
            host=data.get('host', 'localhost'),
            status=PortStatus(data.get('status', 'unknown')),
            process_name=data.get('process_name'),
            process_pid=data.get('process_pid'),
            service_name=data.get('service_name'),
            metadata=data.get('metadata', {})
        )
        if data.get('last_checked'):
            port_info.last_checked = datetime.fromisoformat(data['last_checked'])
        return port_info


@dataclass
class PortRange:
    """端口范围"""
    start_port: int
    end_port: int
    name: str = ""
    description: str = ""
    excluded_ports: Set[int] = field(default_factory=set)

    def __post_init__(self):
        if self.start_port > self.end_port:
            raise ValueError("起始端口不能大于结束端口")
        if self.start_port < 1 or self.end_port > 65535:
            raise ValueError("端口必须在1-65535范围内")

    def contains(self, port: int) -> bool:
        """检查端口是否在范围内"""
        return self.start_port <= port <= self.end_port and port not in self.excluded_ports

    def get_available_ports(self, count: int = 1) -> List[int]:
        """获取范围内的可用端口列表"""
        available_ports = []
        for port in range(self.start_port, self.end_port + 1):
            if port not in self.excluded_ports:
                available_ports.append(port)
                if len(available_ports) >= count:
                    break
        return available_ports


@dataclass
class PortConflict:
    """端口冲突信息"""
    port: int
    host: str
    conflicting_processes: List[Dict[str, Any]] = field(default_factory=list)
    requested_by: Optional[str] = None
    resolution_options: List[str] = field(default_factory=list)
    recommended_action: Optional[str] = None


class PortManager:
    """
    端口管理器

    功能特性：
    - 端口扫描和状态检测
    - 冲突检测和解决
    - 自动端口分配
    - 端口预留和释放
    - 配置持久化
    """

    def __init__(self, port_ranges: Optional[List[Tuple[int, int]]] = None,
                 host: str = "localhost",
                 persistence_file: Optional[str] = None):
        """
        初始化端口管理器

        Args:
            port_ranges: 端口范围列表
            host: 主机地址
            persistence_file: 持久化文件路径
        """
        self.host = host
        self.persistence_file = persistence_file

        # 设置默认端口范围
        if port_ranges is None:
            port_ranges = [
                (8000, 8999),  # 应用服务端口
                (3000, 3999),  # 前端开发端口
                (5000, 5999),  # API服务端口
                (9000, 9999),  # 管理服务端口
            ]

        # 创建端口范围对象
        self.port_ranges = [
            PortRange(start, end, f"Range-{i+1}")
            for i, (start, end) in enumerate(port_ranges)
        ]

        # 端口状态缓存
        self.port_cache: Dict[int, PortInfo] = {}

        # 预留端口
        self.reserved_ports: Dict[int, str] = {}

        # 配置信息
        self.config = {
            'scan_timeout': 1.0,
            'cache_ttl': 300,  # 缓存有效期（秒）
            'max_allocation_attempts': 100,
            'prefer_lower_ports': True,
            'avoid_system_ports': True,
            'excluded_ports': {80, 443, 22, 21, 23, 25, 53, 110, 143, 993, 995}
        }

        self.logger = get_logger(self.__class__.__name__)

        # 加载持久化数据
        if self.persistence_file:
            self._load_persistence_data()

        self.logger.info(f"端口管理器初始化完成，主机: {host}")

    async def scan_ports(self, ports: Optional[List[int]] = None,
                        refresh_cache: bool = False) -> Dict[int, PortInfo]:
        """
        扫描端口状态

        Args:
            ports: 要扫描的端口列表，None表示扫描所有配置的范围
            refresh_cache: 是否刷新缓存

        Returns:
            端口状态字典
        """
        if ports is None:
            # 扫描所有配置的端口范围
            ports = []
            for port_range in self.port_ranges:
                ports.extend(range(port_range.start_port, port_range.end_port + 1))

        results = {}

        # 并发扫描端口
        semaphore = asyncio.Semaphore(100)  # 限制并发数
        tasks = []

        async def scan_single_port(port: int) -> Tuple[int, PortInfo]:
            async with semaphore:
                return port, await self._scan_single_port(port, refresh_cache)

        for port in ports:
            if port in self.config['excluded_ports']:
                continue
            task = asyncio.create_task(scan_single_port(port))
            tasks.append(task)

        # 等待所有扫描完成
        for task in asyncio.as_completed(tasks):
            port, port_info = await task
            results[port] = port_info

        self.logger.debug(f"端口扫描完成，共扫描 {len(results)} 个端口")
        return results

    async def _scan_single_port(self, port: int, refresh_cache: bool = False) -> PortInfo:
        """扫描单个端口"""
        current_time = datetime.now()

        # 检查缓存
        if not refresh_cache and port in self.port_cache:
            cached_info = self.port_cache[port]
            if (current_time - cached_info.last_checked).seconds < self.config['cache_ttl']:
                return cached_info

        port_info = PortInfo(port=port, host=self.host, last_checked=current_time)

        try:
            # 尝试连接端口
            future = asyncio.open_connection(self.host, port, timeout=self.config['scan_timeout'])
            reader, writer = await asyncio.wait_for(future, timeout=self.config['scan_timeout'])

            # 连接成功，端口被占用
            port_info.status = PortStatus.OCCUPIED

            # 尝试获取占用进程信息
            try:
                for conn in psutil.net_connections():
                    if (conn.laddr.port == port and
                        conn.status == psutil.CONN_LISTEN and
                        conn.pid):
                        try:
                            process = psutil.Process(conn.pid)
                            port_info.process_name = process.name()
                            port_info.process_pid = conn.pid
                            port_info.metadata.update({
                                'process_cmdline': process.cmdline(),
                                'process_create_time': process.create_time(),
                                'process_username': process.username()
                            })
                            break
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass
            except Exception as e:
                self.logger.debug(f"获取端口 {port} 进程信息失败: {e}")

            # 关闭连接
            writer.close()
            await writer.wait_closed()

        except asyncio.TimeoutError:
            # 连接超时，可能端口被防火墙阻止
            port_info.status = PortStatus.UNKNOWN
            port_info.metadata['timeout'] = True

        except (ConnectionRefusedError, OSError):
            # 连接被拒绝，端口可用
            port_info.status = PortStatus.FREE

        except Exception as e:
            self.logger.warning(f"扫描端口 {port} 时发生异常: {e}")
            port_info.status = PortStatus.UNKNOWN
            port_info.metadata['error'] = str(e)

        # 检查是否为预留端口
        if port in self.reserved_ports:
            port_info.status = PortStatus.RESERVED
            port_info.service_name = self.reserved_ports[port]

        # 更新缓存
        self.port_cache[port] = port_info

        return port_info

    async def allocate_port(self, preferred_port: Optional[int] = None,
                          service_name: Optional[str] = None,
                          port_range: Optional[PortRange] = None) -> int:
        """
        分配可用端口

        Args:
            preferred_port: 首选端口
            service_name: 服务名称
            port_range: 指定的端口范围

        Returns:
            分配的端口号

        Raises:
            ValueError: 无法分配端口
        """
        if preferred_port:
            # 检查首选端口是否可用
            port_info = await self._scan_single_port(preferred_port)
            if port_info.status == PortStatus.FREE:
                # 预留端口
                if service_name:
                    self.reserve_port(preferred_port, service_name)
                return preferred_port
            else:
                self.logger.warning(f"首选端口 {preferred_port} 不可用 ({port_info.status.value})")

        # 在指定范围内或所有范围内查找可用端口
        search_ranges = [port_range] if port_range else self.port_ranges

        for range_obj in search_ranges:
            available_ports = range_obj.get_available_ports(self.config['max_allocation_attempts'])

            if not self.config['prefer_lower_ports']:
                available_ports.reverse()

            for port in available_ports:
                if port in self.config['excluded_ports']:
                    continue

                port_info = await self._scan_single_port(port)
                if port_info.status == PortStatus.FREE:
                    # 预留端口
                    if service_name:
                        self.reserve_port(port, service_name)
                    self.logger.info(f"为服务 {service_name} 分配端口: {port}")
                    return port

        raise ValueError(f"无法在指定范围内分配可用端口")

    async def resolve_conflict(self, port: int, service_name: str,
                             resolution_callback: Optional[Callable[[PortConflict], str]] = None) -> int:
        """
        解决端口冲突

        Args:
            port: 冲突端口
            service_name: 服务名称
            resolution_callback: 冲突解决回调函数

        Returns:
            解决后的端口号

        Raises:
            ValueError: 无法解决冲突
        """
        port_info = await self._scan_single_port(port)

        if port_info.status == PortStatus.FREE:
            return port

        # 创建冲突信息
        conflict = PortConflict(
            port=port,
            host=self.host,
            requested_by=service_name,
            conflicting_processes=[]
        )

        if port_info.process_name and port_info.process_pid:
            conflict.conflicting_processes.append({
                'name': port_info.process_name,
                'pid': port_info.process_pid,
                'details': port_info.metadata
            })

        # 生成解决选项
        conflict.resolution_options = [
            f"自动分配新端口",
            f"终止占用进程 (PID: {port_info.process_pid})",
            f"跳过此服务"
        ]

        conflict.recommended_action = "自动分配新端口"

        # 调用解决回调
        if resolution_callback:
            choice = resolution_callback(conflict)
            if choice == "自动分配新端口":
                new_port = await self.allocate_port(service_name=service_name)
                self.logger.info(f"端口冲突已解决，为服务 {service_name} 分配新端口: {new_port}")
                return new_port
            elif choice.startswith("终止占用进程"):
                try:
                    if port_info.process_pid:
                        psutil.Process(port_info.process_pid).terminate()
                        await asyncio.sleep(2)  # 等待进程终止
                        # 重新检查端口
                        port_info = await self._scan_single_port(port)
                        if port_info.status == PortStatus.FREE:
                            self.reserve_port(port, service_name)
                            self.logger.info(f"终止进程后成功占用端口: {port}")
                            return port
                except Exception as e:
                    self.logger.error(f"终止进程失败: {e}")
                    raise ValueError(f"无法终止占用进程: {e}")
            elif choice == "跳过此服务":
                raise ValueError(f"用户选择跳过服务 {service_name}")

        # 默认行为：自动分配新端口
        new_port = await self.allocate_port(service_name=service_name)
        self.logger.warning(f"端口 {port} 冲突，自动为服务 {service_name} 分配新端口: {new_port}")
        return new_port

    def reserve_port(self, port: int, service_name: str) -> None:
        """
        预留端口

        Args:
            port: 端口号
            service_name: 服务名称
        """
        self.reserved_ports[port] = service_name

        # 更新缓存中的端口状态
        if port in self.port_cache:
            self.port_cache[port].status = PortStatus.RESERVED
            self.port_cache[port].service_name = service_name

        self.logger.debug(f"预留端口 {port} 给服务 {service_name}")

        # 保存持久化数据
        if self.persistence_file:
            self._save_persistence_data()

    def release_port(self, port: int) -> None:
        """
        释放端口

        Args:
            port: 端口号
        """
        if port in self.reserved_ports:
            service_name = self.reserved_ports.pop(port)
            self.logger.debug(f"释放端口 {port} (原服务: {service_name})")

            # 更新缓存中的端口状态
            if port in self.port_cache:
                self.port_cache[port].status = PortStatus.FREE
                self.port_cache[port].service_name = None

            # 保存持久化数据
            if self.persistence_file:
                self._save_persistence_data()

    def get_reserved_ports(self) -> Dict[int, str]:
        """获取所有预留端口"""
        return self.reserved_ports.copy()

    def get_port_info(self, port: int, refresh: bool = False) -> Optional[PortInfo]:
        """
        获取端口信息

        Args:
            port: 端口号
            refresh: 是否刷新缓存

        Returns:
            端口信息
        """
        if refresh or port not in self.port_cache:
            # 这里可以添加异步刷新逻辑，但为了简化接口暂时使用同步方式
            pass
        return self.port_cache.get(port)

    async def check_port_availability(self, port: int) -> bool:
        """
        检查端口是否可用

        Args:
            port: 端口号

        Returns:
            是否可用
        """
        port_info = await self._scan_single_port(port)
        return port_info.status == PortStatus.FREE

    def get_port_usage_summary(self) -> Dict[str, Any]:
        """
        获取端口使用情况摘要

        Returns:
            端口使用摘要
        """
        total_ports = 0
        free_ports = 0
        occupied_ports = 0
        reserved_ports = 0
        unknown_ports = 0

        for port_range in self.port_ranges:
            for port in range(port_range.start_port, port_range.end_port + 1):
                if port in self.config['excluded_ports']:
                    continue

                total_ports += 1
                if port in self.reserved_ports:
                    reserved_ports += 1
                elif port in self.port_cache:
                    status = self.port_cache[port].status
                    if status == PortStatus.FREE:
                        free_ports += 1
                    elif status == PortStatus.OCCUPIED:
                        occupied_ports += 1
                    else:
                        unknown_ports += 1
                else:
                    # 未扫描的端口计入未知
                    unknown_ports += 1

        return {
            'total_ports': total_ports,
            'free_ports': free_ports,
            'occupied_ports': occupied_ports,
            'reserved_ports': reserved_ports,
            'unknown_ports': unknown_ports,
            'availability_percentage': (free_ports / total_ports * 100) if total_ports > 0 else 0,
            'reserved_details': self.reserved_ports.copy()
        }

    def _save_persistence_data(self) -> None:
        """保存持久化数据"""
        if not self.persistence_file:
            return

        try:
            data = {
                'reserved_ports': self.reserved_ports,
                'config': self.config,
                'port_ranges': [
                    {
                        'start_port': pr.start_port,
                        'end_port': pr.end_port,
                        'name': pr.name,
                        'description': pr.description,
                        'excluded_ports': list(pr.excluded_ports)
                    }
                    for pr in self.port_ranges
                ],
                'timestamp': datetime.now().isoformat()
            }

            path = Path(self.persistence_file)
            path.parent.mkdir(parents=True, exist_ok=True)

            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            self.logger.debug(f"端口管理器数据已保存到: {self.persistence_file}")

        except Exception as e:
            self.logger.error(f"保存持久化数据失败: {e}")

    def _load_persistence_data(self) -> None:
        """加载持久化数据"""
        if not self.persistence_file:
            return

        try:
            path = Path(self.persistence_file)
            if not path.exists():
                return

            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 加载预留端口
            self.reserved_ports = {
                int(port): service_name
                for port, service_name in data.get('reserved_ports', {}).items()
            }

            # 加载配置
            if 'config' in data:
                self.config.update(data['config'])

            # 加载端口范围
            if 'port_ranges' in data:
                self.port_ranges = []
                for pr_data in data['port_ranges']:
                    port_range = PortRange(
                        start_port=pr_data['start_port'],
                        end_port=pr_data['end_port'],
                        name=pr_data.get('name', ''),
                        description=pr_data.get('description', ''),
                        excluded_ports=set(pr_data.get('excluded_ports', []))
                    )
                    self.port_ranges.append(port_range)

            self.logger.debug(f"端口管理器数据已从文件加载: {self.persistence_file}")

        except Exception as e:
            self.logger.error(f"加载持久化数据失败: {e}")

    def clear_cache(self) -> None:
        """清空端口状态缓存"""
        self.port_cache.clear()
        self.logger.debug("端口状态缓存已清空")

    def export_port_data(self, include_cache: bool = False) -> Dict[str, Any]:
        """
        导出端口管理数据

        Args:
            include_cache: 是否包含缓存数据

        Returns:
            端口管理数据
        """
        data = {
            'host': self.host,
            'reserved_ports': self.reserved_ports.copy(),
            'config': self.config.copy(),
            'port_ranges': [
                {
                    'start_port': pr.start_port,
                    'end_port': pr.end_port,
                    'name': pr.name,
                    'description': pr.description,
                    'excluded_ports': list(pr.excluded_ports)
                }
                for pr in self.port_ranges
            ],
            'usage_summary': self.get_port_usage_summary()
        }

        if include_cache:
            data['port_cache'] = {
                port: port_info.to_dict()
                for port, port_info in self.port_cache.items()
            }

        return data