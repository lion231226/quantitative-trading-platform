"""
Test suite for System Information Collector module.

This test suite validates the comprehensive system information collection
including hardware details, software environment, and diagnostic data.
"""

import unittest
from unittest.mock import patch, MagicMock, mock_open
import sys
import os
import time
from pathlib import Path
import json

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.system_info_collector import (
    SystemInfoCollector, HardwareInfo, SoftwareInfo, DiagnosticInfo,
    CompleteSystemInfo, collect_system_info, generate_diagnostics_report,
    get_system_summary
)
from core.operating_system_detector import SystemInfo, OperatingSystem, Architecture, OSVersion


class TestSystemInfoCollector(unittest.TestCase):
    """Test cases for SystemInfoCollector class"""

    def setUp(self):
        """Set up test fixtures"""
        self.mock_os_detector = MagicMock()
        self.collector = SystemInfoCollector(self.mock_os_detector)

    def test_collect_all_integration(self):
        """Test complete system information collection"""
        # Mock OS detector response
        mock_system_info = SystemInfo(
            os_type=OperatingSystem.WINDOWS,
            architecture=Architecture.X64,
            version=OSVersion(major=10, minor=0),
            python_version="3.11.0",
            python_executable="C:\\Python311\\python.exe",
            platform_details={},
            compatibility={'os_supported': True}
        )
        self.mock_os_detector.detect_os_info.return_value = mock_system_info

        # Mock individual collection methods
        with patch.object(self.collector, '_collect_hardware_info') as mock_hardware:
            with patch.object(self.collector, '_collect_software_info') as mock_software:
                with patch.object(self.collector, '_collect_diagnostic_info') as mock_diagnostic:
                    with patch.object(self.collector, '_collect_launcher_info') as mock_launcher:

                        # Setup mock return values
                        mock_hardware.return_value = HardwareInfo(
                            cpu_name="Test CPU",
                            cpu_cores=4,
                            cpu_threads=8,
                            cpu_architecture="x64",
                            total_memory=8192,
                            available_memory=4096,
                            disk_info=[],
                            gpu_info=[],
                            network_interfaces=[]
                        )

                        mock_software.return_value = SoftwareInfo(
                            python_version="3.11.0",
                            python_executable="C:\\Python311\\python.exe",
                            installed_packages={},
                            environment_variables={},
                            running_processes=[],
                            available_services=[]
                        )

                        mock_diagnostic.return_value = DiagnosticInfo(
                            error_logs=[],
                            warning_logs=[],
                            performance_metrics={},
                            network_connectivity={},
                            system_resources={}
                        )

                        mock_launcher.return_value = {'test': 'value'}

                        # Collect all information
                        result = self.collector.collect_all()

                        # Verify structure
                        self.assertIsInstance(result, CompleteSystemInfo)
                        self.assertEqual(result.system_info, mock_system_info)
                        self.assertIsInstance(result.hardware, HardwareInfo)
                        self.assertIsInstance(result.software, SoftwareInfo)
                        self.assertIsInstance(result.diagnostic, DiagnosticInfo)
                        self.assertIsInstance(result.launcher_info, dict)

    def test_collect_hardware_info_success(self):
        """Test successful hardware information collection"""
        # Mock psutil
        with patch('core.system_info_collector.psutil') as mock_psutil:
            # Setup psutil mocks
            mock_psutil.cpu_count.return_value = 4
            mock_psutil.virtual_memory.return_value = MagicMock(
                total=8589934592,  # 8GB
                available=4294967296  # 4GB
            )
            mock_psutil.disk_partitions.return_value = []
            mock_psutil.net_if_addrs.return_value = {}

            # Mock OS info
            self.mock_os_detector.system_info = SystemInfo(
                os_type=OperatingSystem.LINUX,
                architecture=Architecture.X64,
                version=OSVersion(major=20, minor=4),
                python_version="3.8.0",
                python_executable="/usr/bin/python3",
                platform_details={},
                compatibility={}
            )

            with patch.object(self.collector, '_get_linux_cpu_name', return_value="Test CPU"):
                result = self.collector._collect_hardware_info()

                self.assertIsInstance(result, HardwareInfo)
                self.assertEqual(result.cpu_name, "Test CPU")
                self.assertEqual(result.cpu_cores, 4)
                self.assertEqual(result.total_memory, 8192)  # 8GB in MB
                self.assertEqual(result.available_memory, 4096)  # 4GB in MB

    def test_collect_hardware_info_with_psutil_error(self):
        """Test hardware information collection with psutil error"""
        with patch('core.system_info_collector.psutil') as mock_psutil:
            mock_psutil.cpu_count.side_effect = Exception("psutil error")

            # Mock OS info
            self.mock_os_detector.system_info = SystemInfo(
                os_type=OperatingSystem.WINDOWS,
                architecture=Architecture.X64,
                version=OSVersion(major=10, minor=0),
                python_version="3.11.0",
                python_executable="python",
                platform_details={},
                compatibility={}
            )

            result = self.collector._collect_hardware_info()

            # Should return minimal info
            self.assertEqual(result.cpu_name, "Unknown")
            self.assertEqual(result.cpu_cores, 0)
            self.assertEqual(result.total_memory, 0)

    def test_collect_software_info_success(self):
        """Test successful software information collection"""
        # Mock pkg_resources
        with patch('core.system_info_collector.pkg_resources') as mock_pkg:
            # Setup mock package
            mock_dist = MagicMock()
            mock_dist.project_name = "test-package"
            mock_dist.version = "1.0.0"
            mock_pkg.working_set = [mock_dist]

            with patch.dict(os.environ, {'PATH': '/usr/bin', 'HOME': '/home/test'}):
                result = self.collector._collect_software_info()

                self.assertIsInstance(result, SoftwareInfo)
                self.assertEqual(result.python_version, platform.python_version())
                self.assertEqual(result.python_executable, sys.executable)
                self.assertEqual(result.installed_packages["test-package"], "1.0.0")
                self.assertIn('PATH', result.environment_variables)
                self.assertIn('HOME', result.environment_variables)

    def test_collect_diagnostic_info_success(self):
        """Test successful diagnostic information collection"""
        with patch('core.system_info_collector.psutil') as mock_psutil:
            # Setup psutil mocks
            mock_psutil.cpu_percent.return_value = [25.0, 30.0, 20.0]
            mock_psutil.virtual_memory.return_value = MagicMock(percent=50.0)
            mock_psutil.swap_memory.return_value = MagicMock(percent=10.0)
            mock_psutil.boot_time.return_value = time.time() - 86400  # 1 day ago
            mock_psutil.disk_io_counters.return_value = MagicMock(
                read_bytes=1000000, write_bytes=500000
            )
            mock_psutil.net_io_counters.return_value = MagicMock(
                bytes_sent=2000000, bytes_recv=5000000
            )

            with patch('core.system_info_collector.socket.gethostbyname') as mock_dns:
                with patch('core.system_info_collector.requests.get') as mock_request:
                    # Setup network mocks
                    mock_dns.return_value = "127.0.0.1"
                    mock_response = MagicMock()
                    mock_response.status_code = 200
                    mock_request.return_value = mock_response

                    result = self.collector._collect_diagnostic_info()

                    self.assertIsInstance(result, DiagnosticInfo)
                    self.assertIn('cpu_usage_percent', result.performance_metrics)
                    self.assertIn('memory_usage_percent', result.performance_metrics)
                    self.assertTrue(result.network_connectivity['dns_working'])
                    self.assertTrue(result.network_connectivity['internet_accessible'])

    def test_get_cpu_info_windows(self):
        """Test CPU info collection on Windows"""
        self.mock_os_detector.system_info = SystemInfo(
            os_type=OperatingSystem.WINDOWS,
            architecture=Architecture.X64,
            version=OSVersion(major=10, minor=0),
            python_version="3.11.0",
            python_executable="python",
            platform_details={},
            compatibility={}
        )

        with patch('core.system_info_collector.psutil') as mock_psutil:
            mock_psutil.cpu_count.return_value = (4, 8)  # (cores, threads)

            with patch.object(self.collector, '_get_windows_cpu_name', return_value="Intel Core i7"):
                cpu_name, cores, threads = self.collector._get_cpu_info()

                self.assertEqual(cpu_name, "Intel Core i7")
                self.assertEqual(cores, 4)
                self.assertEqual(threads, 8)

    def test_get_cpu_info_macos(self):
        """Test CPU info collection on macOS"""
        self.mock_os_detector.system_info = SystemInfo(
            os_type=OperatingSystem.MACOS,
            architecture=Architecture.ARM64,
            version=OSVersion(major=12, minor=0),
            python_version="3.9.0",
            python_executable="/usr/bin/python3",
            platform_details={},
            compatibility={}
        )

        with patch('core.system_info_collector.psutil') as mock_psutil:
            mock_psutil.cpu_count.return_value = (8, 8)

            with patch.object(self.collector, '_get_macos_cpu_name', return_value="Apple M1"):
                cpu_name, cores, threads = self.collector._get_cpu_info()

                self.assertEqual(cpu_name, "Apple M1")
                self.assertEqual(cores, 8)
                self.assertEqual(threads, 8)

    def test_get_disk_info(self):
        """Test disk information collection"""
        with patch('core.system_info_collector.psutil') as mock_psutil:
            # Mock partition
            mock_partition = MagicMock()
            mock_partition.device = "/dev/sda1"
            mock_partition.mountpoint = "/"
            mock_partition.fstype = "ext4"

            # Mock usage
            mock_usage = MagicMock()
            mock_usage.total = 1000000000000  # 1TB
            mock_usage.used = 500000000000    # 500GB
            mock_usage.free = 500000000000    # 500GB

            mock_psutil.disk_partitions.return_value = [mock_partition]
            mock_psutil.disk_usage.return_value = mock_usage

            result = self.collector._get_disk_info()

            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]['device'], "/dev/sda1")
            self.assertEqual(result[0]['total'], 1000000000000)
            self.assertEqual(result[0]['percent'], 50.0)

    def test_get_network_info(self):
        """Test network interface information collection"""
        with patch('core.system_info_collector.psutil') as mock_psutil:
            # Mock network address
            mock_addr = MagicMock()
            mock_addr.family = "AF_INET"
            mock_addr.address = "192.168.1.100"
            mock_addr.netmask = "255.255.255.0"
            mock_addr.broadcast = "192.168.1.255"

            mock_psutil.net_if_addrs.return_value = {
                "eth0": [mock_addr]
            }

            result = self.collector._get_network_info()

            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]['name'], "eth0")
            self.assertEqual(len(result[0]['addresses']), 1)

    def test_get_installed_packages(self):
        """Test installed Python packages collection"""
        with patch('core.system_info_collector.pkg_resources') as mock_pkg:
            # Create mock distributions
            mock_dists = []
            for i in range(3):
                mock_dist = MagicMock()
                mock_dist.project_name = f"package-{i}"
                mock_dist.version = f"1.{i}.0"
                mock_dists.append(mock_dist)

            mock_pkg.working_set = mock_dists

            result = self.collector._get_installed_packages()

            self.assertEqual(len(result), 3)
            self.assertEqual(result["package-0"], "1.0.0")
            self.assertEqual(result["package-1"], "1.1.0")
            self.assertEqual(result["package-2"], "1.2.0")

    def test_generate_diagnostics_report(self):
        """Test diagnostics report generation"""
        # Mock complete system info
        mock_system_info = SystemInfo(
            os_type=OperatingSystem.LINUX,
            architecture=Architecture.X64,
            version=OSVersion(major=20, minor=4),
            python_version="3.8.0",
            python_executable="/usr/bin/python3",
            platform_details={},
            compatibility={}
        )

        with patch.object(self.collector, 'collect_all') as mock_collect:
            mock_collect.return_value = CompleteSystemInfo(
                timestamp=time.time(),
                system_info=mock_system_info,
                hardware=HardwareInfo(
                    cpu_name="Test CPU", cpu_cores=4, cpu_threads=8,
                    cpu_architecture="x64", total_memory=8192, available_memory=4096,
                    disk_info=[], gpu_info=[], network_interfaces=[]
                ),
                software=SoftwareInfo(
                    python_version="3.8.0", python_executable="/usr/bin/python3",
                    installed_packages={}, environment_variables={},
                    running_processes=[], available_services=[]
                ),
                diagnostic=DiagnosticInfo(
                    error_logs=[], warning_logs=[],
                    performance_metrics={}, network_connectivity={},
                    system_resources={}
                ),
                launcher_info={}
            )

            with patch('builtins.open', mock_open()) as mock_file:
                result = self.collector.generate_diagnostics_report('/tmp/test_report.json')

                self.assertTrue(result)
                mock_file.assert_called_once_with('/tmp/test_report.json', 'w', encoding='utf-8')

    def test_get_system_summary(self):
        """Test system summary generation"""
        # Mock OS detector
        mock_system_info = SystemInfo(
            os_type=OperatingSystem.WINDOWS,
            architecture=Architecture.X64,
            version=OSVersion(major=10, minor=0),
            python_version="3.11.0",
            python_executable="C:\\Python311\\python.exe",
            platform_details={},
            compatibility={'os_supported': True}
        )
        self.mock_os_detector.detect_os_info.return_value = mock_system_info
        self.collector.system_info = mock_system_info

        with patch('core.system_info_collector.psutil') as mock_psutil:
            mock_psutil.cpu_count.return_value = 4
            mock_psutil.virtual_memory.return_value = MagicMock(
                total=8589934592  # 8GB
            )

            result = self.collector.get_system_summary()

            self.assertEqual(result['os'], 'windows x64')
            self.assertEqual(result['version'], '10.0')
            self.assertEqual(result['python'], '3.11.0')
            self.assertTrue(result['supported'])
            self.assertEqual(result['cpu_cores'], 4)
            self.assertAlmostEqual(result['memory_gb'], 8.0, places=1)


class TestConvenienceFunctions(unittest.TestCase):
    """Test convenience functions"""

    @patch('core.system_info_collector.SystemInfoCollector')
    def test_collect_system_info_function(self, mock_collector_class):
        """Test collect_system_info convenience function"""
        mock_collector = MagicMock()
        mock_collector_class.return_value = mock_collector

        mock_complete_info = MagicMock()
        mock_collector.collect_all.return_value = mock_complete_info

        result = collect_system_info()

        self.assertEqual(result, mock_complete_info)
        mock_collector.collect_all.assert_called_once()

    @patch('core.system_info_collector.SystemInfoCollector')
    def test_generate_diagnostics_report_function(self, mock_collector_class):
        """Test generate_diagnostics_report convenience function"""
        mock_collector = MagicMock()
        mock_collector_class.return_value = mock_collector
        mock_collector.generate_diagnostics_report.return_value = True

        result = generate_diagnostics_report('/tmp/test.json')

        self.assertTrue(result)
        mock_collector.generate_diagnostics_report.assert_called_once_with('/tmp/test.json')

    @patch('core.system_info_collector.SystemInfoCollector')
    def test_get_system_summary_function(self, mock_collector_class):
        """Test get_system_summary convenience function"""
        mock_collector = MagicMock()
        mock_collector_class.return_value = mock_collector
        mock_collector.get_system_summary.return_value = {'test': 'summary'}

        result = get_system_summary()

        self.assertEqual(result['test'], 'summary')
        mock_collector.get_system_summary.assert_called_once()


class TestCompleteSystemInfo(unittest.TestCase):
    """Test CompleteSystemInfo dataclass"""

    def test_to_dict_conversion(self):
        """Test CompleteSystemInfo to_dict conversion"""
        system_info = SystemInfo(
            os_type=OperatingSystem.LINUX,
            architecture=Architecture.X64,
            version=OSVersion(major=20, minor=4),
            python_version="3.8.0",
            python_executable="/usr/bin/python3",
            platform_details={},
            compatibility={}
        )

        hardware = HardwareInfo(
            cpu_name="Test CPU", cpu_cores=4, cpu_threads=8,
            cpu_architecture="x64", total_memory=8192, available_memory=4096,
            disk_info=[], gpu_info=[], network_interfaces=[]
        )

        software = SoftwareInfo(
            python_version="3.8.0", python_executable="/usr/bin/python3",
            installed_packages={}, environment_variables={},
            running_processes=[], available_services=[]
        )

        diagnostic = DiagnosticInfo(
            error_logs=[], warning_logs=[],
            performance_metrics={}, network_connectivity={},
            system_resources={}
        )

        complete_info = CompleteSystemInfo(
            timestamp=time.time(),
            system_info=system_info,
            hardware=hardware,
            software=software,
            diagnostic=diagnostic,
            launcher_info={}
        )

        result = complete_info.to_dict()

        self.assertIn('timestamp', result)
        self.assertIn('system_info', result)
        self.assertIn('hardware', result)
        self.assertIn('software', result)
        self.assertIn('diagnostic', result)
        self.assertIn('launcher_info', result)

        # Check nested structure
        self.assertEqual(result['system_info']['os_type'], 'linux')
        self.assertEqual(result['hardware']['cpu_name'], 'Test CPU')
        self.assertEqual(result['software']['python_version'], '3.8.0')

    def test_to_json_saving(self):
        """Test CompleteSystemInfo to_json saving"""
        complete_info = CompleteSystemInfo(
            timestamp=time.time(),
            system_info=SystemInfo(
                os_type=OperatingSystem.LINUX,
                architecture=Architecture.X64,
                version=OSVersion(major=20, minor=4),
                python_version="3.8.0",
                python_executable="/usr/bin/python3",
                platform_details={},
                compatibility={}
            ),
            hardware=HardwareInfo(
                cpu_name="Test CPU", cpu_cores=4, cpu_threads=8,
                cpu_architecture="x64", total_memory=8192, available_memory=4096,
                disk_info=[], gpu_info=[], network_interfaces=[]
            ),
            software=SoftwareInfo(
                python_version="3.8.0", python_executable="/usr/bin/python3",
                installed_packages={}, environment_variables={},
                running_processes=[], available_services=[]
            ),
            diagnostic=DiagnosticInfo(
                error_logs=[], warning_logs=[],
                performance_metrics={}, network_connectivity={},
                system_resources={}
            ),
            launcher_info={}
        )

        with patch('builtins.open', mock_open()) as mock_file:
            with patch('json.dump') as mock_dump:
                result = complete_info.to_json('/tmp/test.json')

                self.assertTrue(result)
                mock_file.assert_called_once_with('/tmp/test.json', 'w', encoding='utf-8')
                mock_dump.assert_called_once()


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error handling"""

    def setUp(self):
        self.mock_os_detector = MagicMock()
        self.collector = SystemInfoCollector(self.mock_os_detector)

    def test_collect_all_with_exception(self):
        """Test collection with exceptions"""
        self.mock_os_detector.detect_os_info.side_effect = Exception("Detection failed")

        with self.assertRaises(Exception):
            self.collector.collect_all()

    def test_windows_cpu_name_fallback(self):
        """Test Windows CPU name fallback when WMI fails"""
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = subprocess.SubprocessError("WMI failed")

            result = self.collector._get_windows_cpu_name()
            self.assertEqual(result, "Unknown CPU")

    def test_macos_cpu_name_fallback(self):
        """Test macOS CPU name fallback when sysctl fails"""
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = subprocess.SubprocessError("sysctl failed")

            result = self.collector._get_macos_cpu_name()
            self.assertEqual(result, "Unknown CPU")

    def test_linux_cpu_name_fallback(self):
        """Test Linux CPU name fallback when /proc/cpuinfo unavailable"""
        with patch('builtins.open', side_effect= FileNotFoundError("/proc/cpuinfo not found")):
            result = self.collector._get_linux_cpu_name()
            self.assertEqual(result, "Unknown CPU")

    def test_network_connectivity_failures(self):
        """Test network connectivity check with failures"""
        with patch('core.system_info_collector.socket.gethostbyname', side_effect=Exception("DNS failed")):
            with patch('core.system_info_collector.requests.get', side_effect=Exception("Network failed")):
                with patch('socket.create_connection', side_effect=Exception("Connection failed")):

                    result = self.collector._check_network_connectivity()

                    self.assertFalse(result['dns_working'])
                    self.assertFalse(result['internet_accessible'])
                    self.assertFalse(result['local_network'])
                    self.assertEqual(len(result['failed_checks']), 3)


if __name__ == '__main__':
    unittest.main()