"""
System Information Collection Module

This module provides comprehensive system information collection capabilities
including hardware details, software environment, and diagnostic data.
"""

import os
import sys
import platform
import subprocess
import json
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import re

from .operating_system_detector import OperatingSystemDetector, SystemInfo
from utils.logger_new import get_logger

logger = get_logger(__name__)


@dataclass
class HardwareInfo:
    """Hardware information container"""
    cpu_name: str
    cpu_cores: int
    cpu_threads: int
    cpu_architecture: str
    total_memory: int  # MB
    available_memory: int  # MB
    disk_info: List[Dict[str, Any]]
    gpu_info: List[Dict[str, Any]]
    network_interfaces: List[Dict[str, Any]]


@dataclass
class SoftwareInfo:
    """Software environment information"""
    python_version: str
    python_executable: str
    installed_packages: Dict[str, str]
    environment_variables: Dict[str, str]
    running_processes: List[Dict[str, Any]]
    available_services: List[Dict[str, Any]]


@dataclass
class DiagnosticInfo:
    """Diagnostic information for troubleshooting"""
    error_logs: List[str]
    warning_logs: List[str]
    performance_metrics: Dict[str, Any]
    network_connectivity: Dict[str, Any]
    system_resources: Dict[str, Any]


@dataclass
class CompleteSystemInfo:
    """Complete system information including all components"""
    timestamp: float
    system_info: SystemInfo
    hardware: HardwareInfo
    software: SoftwareInfo
    diagnostic: DiagnosticInfo
    launcher_info: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'timestamp': self.timestamp,
            'system_info': self.system_info.to_dict(),
            'hardware': asdict(self.hardware),
            'software': asdict(self.software),
            'diagnostic': asdict(self.diagnostic),
            'launcher_info': self.launcher_info
        }

    def to_json(self, filepath: str) -> bool:
        """Save to JSON file"""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"Failed to save system info to {filepath}: {e}")
            return False


class SystemInfoCollector:
    """
    Comprehensive system information collector.

    Collects hardware, software, and diagnostic information
    for environment analysis and troubleshooting.
    """

    def __init__(self, os_detector: Optional[OperatingSystemDetector] = None):
        self.os_detector = os_detector or OperatingSystemDetector()
        self.system_info: Optional[SystemInfo] = None

    def collect_all(self) -> CompleteSystemInfo:
        """
        Collect comprehensive system information.

        Returns:
            CompleteSystemInfo: All system information
        """
        try:
            logger.info("Starting comprehensive system information collection")

            # Get basic system info
            self.system_info = self.os_detector.detect_os_info()

            # Collect detailed hardware info
            hardware = self._collect_hardware_info()

            # Collect software environment info
            software = self._collect_software_info()

            # Collect diagnostic info
            diagnostic = self._collect_diagnostic_info()

            # Collect launcher-specific info
            launcher_info = self._collect_launcher_info()

            complete_info = CompleteSystemInfo(
                timestamp=time.time(),
                system_info=self.system_info,
                hardware=hardware,
                software=software,
                diagnostic=diagnostic,
                launcher_info=launcher_info
            )

            logger.info("System information collection completed")
            return complete_info

        except Exception as e:
            logger.error(f"Failed to collect system information: {e}")
            raise

    def _collect_hardware_info(self) -> HardwareInfo:
        """Collect hardware information"""
        try:
            logger.debug("Collecting hardware information")

            # CPU information
            cpu_name, cpu_cores, cpu_threads = self._get_cpu_info()
            cpu_architecture = self.system_info.architecture.value

            # Memory information
            total_memory, available_memory = self._get_memory_info()

            # Disk information
            disk_info = self._get_disk_info()

            # GPU information
            gpu_info = self._get_gpu_info()

            # Network interfaces
            network_interfaces = self._get_network_info()

            return HardwareInfo(
                cpu_name=cpu_name,
                cpu_cores=cpu_cores,
                cpu_threads=cpu_threads,
                cpu_architecture=cpu_architecture,
                total_memory=total_memory,
                available_memory=available_memory,
                disk_info=disk_info,
                gpu_info=gpu_info,
                network_interfaces=network_interfaces
            )

        except Exception as e:
            logger.error(f"Failed to collect hardware info: {e}")
            # Return minimal info
            return HardwareInfo(
                cpu_name="Unknown",
                cpu_cores=0,
                cpu_threads=0,
                cpu_architecture=self.system_info.architecture.value,
                total_memory=0,
                available_memory=0,
                disk_info=[],
                gpu_info=[],
                network_interfaces=[]
            )

    def _collect_software_info(self) -> SoftwareInfo:
        """Collect software environment information"""
        try:
            logger.debug("Collecting software information")

            # Python environment
            python_version = platform.python_version()
            python_executable = sys.executable

            # Installed packages
            installed_packages = self._get_installed_packages()

            # Environment variables
            environment_variables = self._get_environment_variables()

            # Running processes
            running_processes = self._get_running_processes()

            # Available services
            available_services = self._get_available_services()

            return SoftwareInfo(
                python_version=python_version,
                python_executable=python_executable,
                installed_packages=installed_packages,
                environment_variables=environment_variables,
                running_processes=running_processes,
                available_services=available_services
            )

        except Exception as e:
            logger.error(f"Failed to collect software info: {e}")
            # Return minimal info
            return SoftwareInfo(
                python_version=platform.python_version(),
                python_executable=sys.executable,
                installed_packages={},
                environment_variables={},
                running_processes=[],
                available_services=[]
            )

    def _collect_diagnostic_info(self) -> DiagnosticInfo:
        """Collect diagnostic information"""
        try:
            logger.debug("Collecting diagnostic information")

            # Error and warning logs
            error_logs, warning_logs = self._get_recent_logs()

            # Performance metrics
            performance_metrics = self._get_performance_metrics()

            # Network connectivity
            network_connectivity = self._check_network_connectivity()

            # System resources
            system_resources = self._get_system_resources()

            return DiagnosticInfo(
                error_logs=error_logs,
                warning_logs=warning_logs,
                performance_metrics=performance_metrics,
                network_connectivity=network_connectivity,
                system_resources=system_resources
            )

        except Exception as e:
            logger.error(f"Failed to collect diagnostic info: {e}")
            # Return minimal info
            return DiagnosticInfo(
                error_logs=[f"Failed to collect diagnostic info: {e}"],
                warning_logs=[],
                performance_metrics={},
                network_connectivity={},
                system_resources={}
            )

    def _collect_launcher_info(self) -> Dict[str, Any]:
        """Collect launcher-specific information"""
        try:
            logger.debug("Collecting launcher information")

            launcher_path = Path(__file__).parent.parent
            launcher_config = {
                'launcher_version': '1.0.0',  # TODO: Get from version file
                'launcher_path': str(launcher_path),
                'python_version_required': '3.8+',
                'supported_platforms': ['Windows 10+', 'macOS 10.15+', 'Ubuntu 18.04+'],
                'required_dependencies': [
                    'psutil>=7.1.3',
                    'rich>=13.9.4',
                    'requests>=2.32.3'
                ],
                'configuration_files': self._find_config_files(),
                'startup_time': time.time()
            }

            return launcher_config

        except Exception as e:
            logger.error(f"Failed to collect launcher info: {e}")
            return {'error': str(e)}

    def _get_cpu_info(self) -> Tuple[str, int, int]:
        """Get CPU information"""
        try:
            import psutil

            # CPU name
            if self.system_info.os_type.value == 'windows':
                cpu_name = self._get_windows_cpu_name()
            elif self.system_info.os_type.value == 'macos':
                cpu_name = self._get_macos_cpu_name()
            else:  # Linux
                cpu_name = self._get_linux_cpu_name()

            # Core and thread count
            cpu_cores = psutil.cpu_count(logical=False) or 0
            cpu_threads = psutil.cpu_count(logical=True) or 0

            return cpu_name, cpu_cores, cpu_threads

        except Exception as e:
            logger.warning(f"Failed to get CPU info: {e}")
            return "Unknown CPU", 0, 0

    def _get_windows_cpu_name(self) -> str:
        """Get CPU name on Windows"""
        try:
            result = subprocess.run(
                ['wmic', 'cpu', 'get', 'name'],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                if len(lines) > 1:
                    return lines[1].strip()
        except Exception:
            pass
        return "Unknown CPU"

    def _get_macos_cpu_name(self) -> str:
        """Get CPU name on macOS"""
        try:
            result = subprocess.run(
                ['sysctl', '-n', 'machdep.cpu.brand_string'],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        return "Unknown CPU"

    def _get_linux_cpu_name(self) -> str:
        """Get CPU name on Linux"""
        try:
            with open('/proc/cpuinfo', 'r') as f:
                for line in f:
                    if line.startswith('model name'):
                        return line.split(':')[1].strip()
        except Exception:
            pass
        return "Unknown CPU"

    def _get_memory_info(self) -> Tuple[int, int]:
        """Get memory information in MB"""
        try:
            import psutil

            memory = psutil.virtual_memory()
            total_memory = memory.total // (1024 * 1024)  # Convert to MB
            available_memory = memory.available // (1024 * 1024)

            return total_memory, available_memory

        except Exception as e:
            logger.warning(f"Failed to get memory info: {e}")
            return 0, 0

    def _get_disk_info(self) -> List[Dict[str, Any]]:
        """Get disk information"""
        try:
            import psutil

            disk_info = []
            for partition in psutil.disk_partitions():
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    disk_info.append({
                        'device': partition.device,
                        'mountpoint': partition.mountpoint,
                        'fstype': partition.fstype,
                        'total': usage.total,
                        'used': usage.used,
                        'free': usage.free,
                        'percent': (usage.used / usage.total) * 100 if usage.total > 0 else 0
                    })
                except Exception:
                    continue

            return disk_info

        except Exception as e:
            logger.warning(f"Failed to get disk info: {e}")
            return []

    def _get_gpu_info(self) -> List[Dict[str, Any]]:
        """Get GPU information"""
        gpu_info = []

        try:
            if self.system_info.os_type.value == 'windows':
                # Try to get GPU info from WMI
                result = subprocess.run(
                    ['wmic', 'path', 'win32_VideoController', 'get', 'name'],
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    for line in lines[1:]:  # Skip header
                        gpu_name = line.strip()
                        if gpu_name:
                            gpu_info.append({'name': gpu_name, 'type': 'Integrated/Dedicated'})

            elif self.system_info.os_type.value == 'macos':
                # Try to get GPU info from system_profiler
                result = subprocess.run(
                    ['system_profiler', 'SPDisplaysDataType'],
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0:
                    output = result.stdout
                    # Parse GPU names from output
                    for line in output.split('\n'):
                        if 'Chipset Model:' in line:
                            gpu_name = line.split(':')[1].strip()
                            gpu_info.append({'name': gpu_name, 'type': 'Integrated'})

            else:  # Linux
                # Try to get GPU info from lspci
                try:
                    result = subprocess.run(
                        ['lspci', '|', 'grep', '-i', 'vga'],
                        shell=True, capture_output=True, text=True, timeout=10
                    )
                    if result.returncode == 0:
                        for line in result.stdout.strip().split('\n'):
                            if line:
                                gpu_info.append({'name': line.strip(), 'type': 'Unknown'})
                except Exception:
                    pass

        except Exception as e:
            logger.warning(f"Failed to get GPU info: {e}")

        return gpu_info

    def _get_network_info(self) -> List[Dict[str, Any]]:
        """Get network interface information"""
        try:
            import psutil

            network_info = []
            for interface, addrs in psutil.net_if_addrs().items():
                interface_info = {'name': interface, 'addresses': []}

                for addr in addrs:
                    interface_info['addresses'].append({
                        'family': str(addr.family),
                        'address': addr.address,
                        'netmask': addr.netmask,
                        'broadcast': addr.broadcast
                    })

                network_info.append(interface_info)

            return network_info

        except Exception as e:
            logger.warning(f"Failed to get network info: {e}")
            return []

    def _get_installed_packages(self) -> Dict[str, str]:
        """Get installed Python packages"""
        try:
            import pkg_resources

            packages = {}
            for dist in pkg_resources.working_set:
                packages[dist.project_name] = dist.version

            return packages

        except Exception as e:
            logger.warning(f"Failed to get installed packages: {e}")
            return {}

    def _get_environment_variables(self) -> Dict[str, str]:
        """Get relevant environment variables"""
        relevant_vars = [
            'PATH', 'HOME', 'USER', 'USERNAME', 'PYTHONPATH',
            'VIRTUAL_ENV', 'CONDA_DEFAULT_ENV', 'LANG', 'LC_ALL',
            'APPDATA', 'LOCALAPPDATA', 'PROGRAMDATA', 'TERM'
        ]

        env_vars = {}
        for var in relevant_vars:
            if var in os.environ:
                env_vars[var] = os.environ[var]

        return env_vars

    def _get_running_processes(self) -> List[Dict[str, Any]]:
        """Get running processes relevant to the launcher"""
        try:
            import psutil

            processes = []
            relevant_processes = [
                'python', 'node', 'redis', 'mongod', 'mysql', 'postgres',
                'nginx', 'apache', 'docker', 'git'
            ]

            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    proc_name = proc.info['name'].lower()
                    if any(relevant in proc_name for relevant in relevant_processes):
                        processes.append({
                            'pid': proc.info['pid'],
                            'name': proc.info['name'],
                            'cmdline': ' '.join(proc.info['cmdline'] or [])
                        })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            return processes

        except Exception as e:
            logger.warning(f"Failed to get running processes: {e}")
            return []

    def _get_available_services(self) -> List[Dict[str, Any]]:
        """Get available system services"""
        services = []

        try:
            if self.system_info.os_type.value == 'windows':
                # Windows services
                result = subprocess.run(
                    ['sc', 'query', 'state=running'],
                    capture_output=True, text=True, timeout=15
                )
                if result.returncode == 0:
                    lines = result.stdout.split('\n')
                    for line in lines:
                        if line.strip() and not line.startswith('SERVICE_NAME'):
                            parts = line.split()
                            if parts:
                                services.append({
                                    'name': parts[0],
                                    'status': 'running',
                                    'platform': 'windows'
                                })

            elif self.system_info.os_type.value == 'posix':
                # POSIX services
                try:
                    # Try systemctl first
                    result = subprocess.run(
                        ['systemctl', 'list-units', '--type=service', '--state=running'],
                        capture_output=True, text=True, timeout=15
                    )
                    if result.returncode == 0:
                        lines = result.stdout.split('\n')[1:]  # Skip header
                        for line in lines:
                            if '.service' in line and 'loaded active running' in line:
                                service_name = line.split('.service')[0].strip()
                                services.append({
                                    'name': service_name,
                                    'status': 'running',
                                    'platform': 'systemd'
                                })
                except Exception:
                    pass

        except Exception as e:
            logger.warning(f"Failed to get available services: {e}")

        return services

    def _get_recent_logs(self) -> Tuple[List[str], List[str]]:
        """Get recent error and warning logs"""
        # This is a simplified implementation
        # In a real implementation, you would read from log files
        error_logs = []
        warning_logs = []

        try:
            # Check for common log files
            log_paths = []

            if self.system_info.os_type.value == 'windows':
                log_paths = [
                    Path(os.environ.get('LOCALAPPDATA', '')) / 'Temp',
                    Path(os.environ.get('TEMP', ''))
                ]
            else:
                log_paths = [
                    Path('/var/log'),
                    Path.home() / '.local' / 'share'
                ]

            for log_path in log_paths:
                if log_path.exists():
                    for log_file in log_path.glob('*.log'):
                        try:
                            # Read last few lines of log file
                            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                                lines = f.readlines()[-10:]  # Last 10 lines
                                for line in lines:
                                    line_lower = line.lower()
                                    if 'error' in line_lower:
                                        error_logs.append(f"{log_file.name}: {line.strip()}")
                                    elif 'warning' in line_lower or 'warn' in line_lower:
                                        warning_logs.append(f"{log_file.name}: {line.strip()}")
                        except Exception:
                            continue

        except Exception as e:
            logger.warning(f"Failed to get recent logs: {e}")

        return error_logs[:20], warning_logs[:20]  # Limit to 20 each

    def _get_performance_metrics(self) -> Dict[str, Any]:
        """Get system performance metrics"""
        try:
            import psutil

            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1, percpu=True)

            # Memory usage
            memory = psutil.virtual_memory()

            # Disk I/O
            disk_io = psutil.disk_io_counters()

            # Network I/O
            network_io = psutil.net_io_counters()

            metrics = {
                'cpu_usage_percent': cpu_percent,
                'cpu_usage_average': sum(cpu_percent) / len(cpu_percent) if cpu_percent else 0,
                'memory_usage_percent': memory.percent,
                'memory_available_gb': memory.available / (1024**3),
                'swap_usage_percent': psutil.swap_memory().percent,
                'boot_time': psutil.boot_time()
            }

            if disk_io:
                metrics.update({
                    'disk_read_bytes': disk_io.read_bytes,
                    'disk_write_bytes': disk_io.write_bytes
                })

            if network_io:
                metrics.update({
                    'network_bytes_sent': network_io.bytes_sent,
                    'network_bytes_recv': network_io.bytes_recv
                })

            return metrics

        except Exception as e:
            logger.warning(f"Failed to get performance metrics: {e}")
            return {}

    def _check_network_connectivity(self) -> Dict[str, Any]:
        """Check network connectivity"""
        connectivity = {
            'internet_accessible': False,
            'dns_working': False,
            'local_network': False,
            'failed_checks': []
        }

        try:
            import socket
            import requests

            # Check DNS resolution
            try:
                socket.gethostbyname('google.com')
                connectivity['dns_working'] = True
            except Exception:
                connectivity['failed_checks'].append('DNS resolution failed')

            # Check internet connectivity
            try:
                response = requests.get('https://httpbin.org/ip', timeout=5)
                if response.status_code == 200:
                    connectivity['internet_accessible'] = True
            except Exception as e:
                connectivity['failed_checks'].append(f'Internet check failed: {e}')

            # Check local network
            try:
                socket.create_connection(('localhost', 80), timeout=2)
                connectivity['local_network'] = True
            except Exception:
                connectivity['failed_checks'].append('Local network check failed')

        except Exception as e:
            connectivity['failed_checks'].append(f'Network check error: {e}')

        return connectivity

    def _get_system_resources(self) -> Dict[str, Any]:
        """Get system resource information"""
        try:
            import psutil

            # Get process count
            process_count = len(psutil.pids())

            # Get open file handles
            try:
                open_files = psutil.Process().num_fds() if hasattr(psutil.Process(), 'num_fds') else 0
            except Exception:
                open_files = 0

            # Get system load (Unix-like systems)
            load_avg = None
            try:
                load_avg = os.getloadavg()
            except AttributeError:
                # Windows doesn't have getloadavg
                pass

            return {
                'process_count': process_count,
                'open_files': open_files,
                'load_average': load_avg,
                'uptime': time.time() - psutil.boot_time()
            }

        except Exception as e:
            logger.warning(f"Failed to get system resources: {e}")
            return {}

    def _find_config_files(self) -> List[Dict[str, Any]]:
        """Find launcher configuration files"""
        config_files = []

        try:
            launcher_path = Path(__file__).parent.parent

            # Look for common config files
            config_patterns = [
                '**/*.json',
                '**/*.yaml',
                '**/*.yml',
                '**/*.ini',
                '**/*.conf',
                '**/config/*'
            ]

            for pattern in config_patterns:
                for config_file in launcher_path.glob(pattern):
                    if config_file.is_file():
                        config_files.append({
                            'name': config_file.name,
                            'path': str(config_file),
                            'size': config_file.stat().st_size
                        })

        except Exception as e:
            logger.warning(f"Failed to find config files: {e}")

        return config_files

    def generate_diagnostics_report(self, output_path: str) -> bool:
        """
        Generate comprehensive diagnostics report.

        Args:
            output_path: Path to save the report

        Returns:
            bool: True if report generated successfully
        """
        try:
            system_info = self.collect_all()
            return system_info.to_json(output_path)

        except Exception as e:
            logger.error(f"Failed to generate diagnostics report: {e}")
            return False

    def get_system_summary(self) -> Dict[str, Any]:
        """Get a concise system summary"""
        try:
            if not self.system_info:
                self.system_info = self.os_detector.detect_os_info()

            summary = {
                'os': f"{self.system_info.os_type.value} {self.system_info.architecture.value}",
                'version': str(self.system_info.version),
                'python': self.system_info.python_version,
                'supported': self.system_info.is_supported(),
                'timestamp': time.time()
            }

            # Add hardware summary
            try:
                import psutil
                summary.update({
                    'cpu_cores': psutil.cpu_count(logical=False),
                    'memory_gb': psutil.virtual_memory().total / (1024**3)
                })
            except Exception:
                pass

            return summary

        except Exception as e:
            logger.error(f"Failed to get system summary: {e}")
            return {'error': str(e)}


# Convenience functions
def collect_system_info() -> CompleteSystemInfo:
    """Convenience function to collect complete system information"""
    collector = SystemInfoCollector()
    return collector.collect_all()


def generate_diagnostics_report(output_path: str) -> bool:
    """Convenience function to generate diagnostics report"""
    collector = SystemInfoCollector()
    return collector.generate_diagnostics_report(output_path)


def get_system_summary() -> Dict[str, Any]:
    """Convenience function to get system summary"""
    collector = SystemInfoCollector()
    return collector.get_system_summary()


if __name__ == "__main__":
    # Demo usage
    print("=== System Information Collector Demo ===")

    collector = SystemInfoCollector()

    # Get system summary
    summary = collector.get_system_summary()
    print("System Summary:")
    for key, value in summary.items():
        print(f"  {key}: {value}")

    # Generate diagnostics report
    report_path = "system_diagnostics.json"
    if collector.generate_diagnostics_report(report_path):
        print(f"\nDiagnostics report saved to: {report_path}")
    else:
        print("\nFailed to generate diagnostics report")