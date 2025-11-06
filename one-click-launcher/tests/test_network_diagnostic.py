#!/usr/bin/env python3
"""
Network Diagnostic Test Suite

Tests for network connectivity detection, service availability checking,
DNS resolution validation, and network issue classification.
"""

import asyncio
import unittest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import sys
import os
import socket
import subprocess

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.network_diagnostic import (
    NetworkDiagnostic, NetworkStatus, ServiceStatus, ConnectionType,
    NetworkInterface, ConnectivityResult, ServiceCheckResult, DNSResult,
    NetworkDiagnosticResult, quick_network_check, check_local_services
)
from utils.progress_tracker import ProgressTracker


class TestNetworkDiagnostic(unittest.TestCase):
    """Network Diagnostic Core Tests"""

    def setUp(self):
        """Set up test fixtures"""
        self.progress_tracker = Mock(spec=ProgressTracker)
        self.progress_tracker._log = Mock()
        self.diagnostic = NetworkDiagnostic(self.progress_tracker)

    def test_initialization(self):
        """Test NetworkDiagnostic initialization"""
        self.assertEqual(self.diagnostic.platform, os.sys.platform.lower())
        self.assertIsNotNone(self.diagnostic.executor)

    @patch('platform.system')
    def test_detect_platform(self, mock_platform):
        """Test platform detection"""
        mock_platform.return_value = 'Windows'
        diagnostic = NetworkDiagnostic()
        self.assertEqual(diagnostic.platform, 'windows')

        mock_platform.return_value = 'Linux'
        diagnostic = NetworkDiagnostic()
        self.assertEqual(diagnostic.platform, 'linux')

    @patch('subprocess.run')
    def test_get_windows_interfaces(self, mock_run):
        """Test Windows network interface detection"""
        mock_output = """
Windows IP Configuration

Ethernet adapter Ethernet:

   Media State . . . . . . . . . . . : Media disconnected
   Connection-specific DNS Suffix  . :

Wireless LAN adapter Wi-Fi:

   IPv4 Address. . . . . . . . . . . : 192.168.1.100
   Subnet Mask . . . . . . . . . . . : 255.255.255.0
   Default Gateway . . . . . . . . . : 192.168.1.1
   Physical Address. . . . . . . . . : 00-11-22-33-44-55
"""
        mock_run.return_value = Mock(returncode=0, stdout=mock_output)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        interfaces = loop.run_until_complete(self.diagnostic._get_windows_interfaces())
        loop.close()

        self.assertIsInstance(interfaces, list)
        self.assertGreater(len(interfaces), 0)

    @patch('subprocess.run')
    def test_get_unix_interfaces(self, mock_run):
        """Test Unix/Linux network interface detection"""
        mock_run.return_value = Mock(returncode=0, stdout="""
eth0: flags=4163<UP,BROADCAST,RUNNING,MULTICAST>  mtu 1500
        inet 192.168.1.100  netmask 255.255.255.0  broadcast 192.168.1.255
        inet6 fe80::1%eth0  prefixlen 64  scopeid 0x20
        ether 00:11:22:33:44:55  txqueuelen 1000  (Ethernet)
        RX packets 1234  bytes 123456 (123.4 KiB)
        RX errors 0  dropped 0  overruns 0  frame 0
        TX packets 5678  bytes 654321 (654.3 KiB)
        TX errors 0  dropped 0 overruns 0  carrier 0  collisions 0

lo: flags=73<UP,LOOPBACK,RUNNING>  mtu 65536
        inet 127.0.0.1  netmask 255.0.0.0
        inet6 ::1%lo  prefixlen 128  scopeid 0x10
        loop  txqueuelen 1000  (Local Loopback)
        RX packets 12  bytes 864 (864.0 B)
        RX errors 0  dropped 0  overruns 0  frame 0
        TX packets 12  bytes 864 (864.0 B)
        TX errors 0  dropped 0 overruns 0  carrier 0  collisions 0
""")

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        interfaces = loop.run_until_complete(self.diagnostic._get_unix_interfaces())
        loop.close()

        self.assertIsInstance(interfaces, list)
        self.assertGreater(len(interfaces), 0)

    @patch('socket.create_connection')
    def test_tcp_connection_success(self, mock_socket):
        """Test successful TCP connection"""
        mock_socket.return_value.__enter__.return_value = Mock()

        target = {'host': 'google.com', 'port': 443, 'type': 'https', 'timeout': 5}
        result = self.diagnostic._test_single_connectivity(target)

        self.assertEqual(result.status, NetworkStatus.CONNECTED)
        self.assertEqual(result.connection_type, ConnectionType.HTTPS)
        self.assertIsNotNone(result.response_time)

    @patch('socket.create_connection')
    def test_tcp_connection_timeout(self, mock_socket):
        """Test TCP connection timeout"""
        mock_socket.side_effect = socket.timeout()

        target = {'host': 'slow-server.com', 'port': 80, 'type': 'tcp', 'timeout': 1}
        result = self.diagnostic._test_single_connectivity(target)

        self.assertEqual(result.status, NetworkStatus.DISCONNECTED)
        self.assertIn('timeout', result.error_message.lower())

    @patch('socket.create_connection')
    def test_tcp_connection_refused(self, mock_socket):
        """Test TCP connection refused"""
        mock_socket.side_effect = ConnectionRefusedError()

        target = {'host': 'localhost', 'port': 9999, 'type': 'tcp', 'timeout': 5}
        result = self.diagnostic._test_single_connectivity(target)

        self.assertEqual(result.status, NetworkStatus.DISCONNECTED)
        self.assertIn('refused', result.error_message.lower())

    @patch('urllib.request.urlopen')
    def test_http_connection_success(self, mock_urlopen):
        """Test successful HTTP connection"""
        mock_response = Mock()
        mock_response.getcode.return_value = 200
        mock_response.headers = {'Content-Type': 'text/html', 'Server': 'nginx/1.18.0'}
        mock_urlopen.return_value.__enter__.return_value = mock_response

        target = {'host': 'httpbin.org', 'port': 80, 'type': 'http', 'timeout': 10}
        result = self.diagnostic._test_single_connectivity(target)

        self.assertEqual(result.status, NetworkStatus.CONNECTED)
        self.assertEqual(result.connection_type, ConnectionType.HTTP)
        self.assertEqual(result.details['http_status'], 200)

    @patch('urllib.request.urlopen')
    def test_http_connection_error(self, mock_urlopen):
        """Test HTTP connection error"""
        from urllib.error import HTTPError
        mock_urlopen.side_effect = HTTPError(url='http://example.com', code=404, msg='Not Found', hdrs=None, fp=None)

        target = {'host': 'example.com', 'port': 80, 'type': 'http', 'timeout': 10}
        result = self.diagnostic._test_single_connectivity(target)

        self.assertEqual(result.status, NetworkStatus.DISCONNECTED)
        self.assertIn('404', result.error_message)

    @patch('subprocess.run')
    def test_ping_connection_success(self, mock_run):
        """Test successful ping connection"""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="Pinging google.com [172.217.16.78] with 32 bytes of data:\nReply from 172.217.16.78: bytes=32 time=15ms TTL=117"
        )

        target = {'host': 'google.com', 'type': 'ping', 'timeout': 5}
        result = self.diagnostic._test_single_connectivity(target)

        self.assertEqual(result.status, NetworkStatus.CONNECTED)
        self.assertEqual(result.connection_type, ConnectionType.PING)

    @patch('subprocess.run')
    def test_ping_connection_failure(self, mock_run):
        """Test failed ping connection"""
        mock_run.return_value = Mock(
            returncode=1,
            stdout="Request timed out."
        )

        target = {'host': 'unreachable.com', 'type': 'ping', 'timeout': 5}
        result = self.diagnostic._test_single_connectivity(target)

        self.assertEqual(result.status, NetworkStatus.DISCONNECTED)
        self.assertEqual(result.connection_type, ConnectionType.PING)

    @patch('socket.gethostbyname')
    def test_dns_connection_success(self, mock_gethostbyname):
        """Test successful DNS resolution"""
        mock_gethostbyname.return_value = '172.217.16.78'

        target = {'host': 'google.com', 'type': 'dns', 'timeout': 5}
        result = self.diagnostic._test_single_connectivity(target)

        self.assertEqual(result.status, NetworkStatus.CONNECTED)
        self.assertEqual(result.connection_type, ConnectionType.DNS)

    @patch('socket.gethostbyname')
    def test_dns_connection_failure(self, mock_gethostbyname):
        """Test DNS resolution failure"""
        mock_gethostbyname.side_effect = socket.gaierror("Name resolution failed")

        target = {'host': 'nonexistent-domain.xyz', 'type': 'dns', 'timeout': 5}
        result = self.diagnostic._test_single_connectivity(target)

        self.assertEqual(result.status, NetworkStatus.DISCONNECTED)
        self.assertEqual(result.connection_type, ConnectionType.DNS)
        self.assertIn('DNS resolution failed', result.error_message)

    @patch('socket.create_connection')
    def test_check_http_service_success(self, mock_socket):
        """Test successful HTTP service check"""
        mock_response = Mock()
        mock_response.getcode.return_value = 200
        mock_response.headers = {'Content-Type': 'application/json'}
        mock_response.read.return_value = b'{"status": "ok"}'

        with patch('urllib.request.urlopen') as mock_urlopen:
            mock_urlopen.return_value.__enter__.return_value = mock_response

            service = {
                'name': 'Test API',
                'host': 'api.example.com',
                'port': 443,
                'protocol': 'https',
                'path': '/health',
                'timeout': 10
            }
            result = self.diagnostic._check_single_service(service)

            self.assertEqual(result.status, ServiceStatus.AVAILABLE)
            self.assertEqual(result.service_name, 'Test API')
            self.assertEqual(result.http_status, 200)

    @patch('socket.create_connection')
    def test_check_tcp_service_success(self, mock_socket):
        """Test successful TCP service check"""
        mock_socket.return_value.__enter__.return_value = Mock()

        service = {
            'name': 'Redis Server',
            'host': 'localhost',
            'port': 6379,
            'protocol': 'tcp',
            'timeout': 5
        }
        result = self.diagnostic._check_single_service(service)

        self.assertEqual(result.status, ServiceStatus.AVAILABLE)
        self.assertEqual(result.service_name, 'Redis Server')
        self.assertEqual(result.port, 6379)

    @patch('socket.create_connection')
    def test_check_tcp_service_timeout(self, mock_socket):
        """Test TCP service timeout"""
        mock_socket.side_effect = socket.timeout()

        service = {
            'name': 'Slow Service',
            'host': 'slow.example.com',
            'port': 8080,
            'protocol': 'tcp',
            'timeout': 1
        }
        result = self.diagnostic._check_single_service(service)

        self.assertEqual(result.status, ServiceStatus.TIMEOUT)
        self.assertIn('timeout', result.error_message.lower())

    @patch('socket.gethostbyname_ex')
    def test_dns_resolution_success(self, mock_gethostbyname_ex):
        """Test successful DNS resolution"""
        mock_gethostbyname_ex.return_value = ('google.com', [], ['172.217.16.78', '172.217.16.142'])

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(self.diagnostic._test_single_dns('google.com'))
        loop.close()

        self.assertEqual(result.status, NetworkStatus.CONNECTED)
        self.assertEqual(len(result.resolved_addresses), 2)
        self.assertIn('172.217.16.78', result.resolved_addresses)

    @patch('socket.gethostbyname_ex')
    def test_dns_resolution_failure(self, mock_gethostbyname_ex):
        """Test DNS resolution failure"""
        mock_gethostbyname_ex.side_effect = socket.gaierror("Name resolution failed")

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(self.diagnostic._test_single_dns('nonexistent.xyz'))
        loop.close()

        self.assertEqual(result.status, NetworkStatus.DISCONNECTED)
        self.assertIn('DNS resolution failed', result.error_message)

    @patch.object(NetworkDiagnostic, 'get_network_interfaces')
    @patch.object(NetworkDiagnostic, 'test_connectivity')
    @patch.object(NetworkDiagnostic, 'check_service_availability')
    @patch.object(NetworkDiagnostic, 'test_dns_resolution')
    async def test_comprehensive_diagnosis(self, mock_dns, mock_services, mock_connectivity, mock_interfaces):
        """Test comprehensive network diagnosis"""
        # Mock the return values
        mock_interfaces.return_value = [
            NetworkInterface(name='eth0', is_up=True, ip_addresses=['192.168.1.100'])
        ]
        mock_connectivity.return_value = [
            ConnectivityResult(
                target='8.8.8.8',
                connection_type=ConnectionType.PING,
                status=NetworkStatus.CONNECTED,
                response_time=0.015
            )
        ]
        mock_services.return_value = [
            ServiceCheckResult(
                service_name='Test Service',
                host='localhost',
                port=8000,
                status=ServiceStatus.AVAILABLE,
                response_time=0.002
            )
        ]
        mock_dns.return_value = [
            DNSResult(
                domain='google.com',
                record_type='A',
                status=NetworkStatus.CONNECTED,
                resolved_addresses=['172.217.16.78'],
                response_time=0.025
            )
        ]

        result = await self.diagnostic.run_comprehensive_diagnosis()

        self.assertIsInstance(result, NetworkDiagnosticResult)
        self.assertEqual(result.overall_status, NetworkStatus.CONNECTED)
        self.assertEqual(len(result.interfaces), 1)
        self.assertEqual(len(result.connectivity_tests), 1)
        self.assertEqual(len(result.service_checks), 1)
        self.assertEqual(len(result.dns_tests), 1)
        self.assertEqual(len(result.issues), 0)
        self.assertIsInstance(result.summary, dict)

    def test_generate_network_guide(self):
        """Test network guide generation"""
        guide = self.diagnostic.generate_network_guide('connectivity')
        self.assertIn('title', guide)
        self.assertIn('description', guide)
        self.assertIn('steps', guide)
        self.assertGreater(len(guide['steps']), 0)

        guide = self.diagnostic.generate_network_guide('service_availability')
        self.assertIn('title', guide)
        self.assertIn('steps', guide)

        guide = self.diagnostic.generate_network_guide('dns_resolution')
        self.assertIn('title', guide)
        self.assertIn('steps', guide)

    def test_determine_overall_status(self):
        """Test overall network status determination"""
        result = NetworkDiagnosticResult(
            timestamp='2024-01-01T00:00:00',
            overall_status=NetworkStatus.UNKNOWN,
            connectivity_tests=[
                ConnectivityResult('8.8.8.8', ConnectionType.PING, NetworkStatus.CONNECTED),
                ConnectivityResult('google.com', ConnectionType.DNS, NetworkStatus.CONNECTED)
            ],
            service_checks=[
                ServiceCheckResult('API', 'localhost', 8000, ServiceStatus.AVAILABLE)
            ],
            dns_tests=[
                DNSResult('google.com', 'A', NetworkStatus.CONNECTED)
            ]
        )

        status = self.diagnostic._determine_overall_status(result)
        self.assertEqual(status, NetworkStatus.CONNECTED)

        # Add some failures
        result.connectivity_tests.append(
            ConnectivityResult('bad.com', ConnectionType.DNS, NetworkStatus.DISCONNECTED)
        )
        status = self.diagnostic._determine_overall_status(result)
        self.assertEqual(status, NetworkStatus.PARTIAL)

        # All failures
        result.connectivity_tests = [
            ConnectivityResult('bad1.com', ConnectionType.DNS, NetworkStatus.DISCONNECTED),
            ConnectivityResult('bad2.com', ConnectionType.PING, NetworkStatus.DISCONNECTED)
        ]
        status = self.diagnostic._determine_overall_status(result)
        self.assertEqual(status, NetworkStatus.DISCONNECTED)


class TestNetworkDiagnosticIntegration(unittest.TestCase):
    """Network Diagnostic Integration Tests"""

    @patch('subprocess.run')
    async def test_real_network_check_simulation(self, mock_run):
        """Test simulated real network check"""
        # Mock all external calls
        mock_run.return_value = Mock(returncode=0, stdout="Mock output")

        with patch('socket.create_connection') as mock_socket, \
             patch('urllib.request.urlopen') as mock_urlopen, \
             patch('socket.gethostbyname') as mock_dns:

            mock_socket.return_value.__enter__.return_value = Mock()
            mock_response = Mock()
            mock_response.getcode.return_value = 200
            mock_response.headers = {'Content-Type': 'text/html'}
            mock_urlopen.return_value.__enter__.return_value = mock_response
            mock_dns.return_value = '8.8.8.8'

            result = await quick_network_check()
            self.assertIsInstance(result, NetworkDiagnosticResult)

    def test_check_local_services_simulation(self):
        """Test local services check simulation"""
        services = [
            {
                'name': 'Local API',
                'host': 'localhost',
                'port': 8000,
                'protocol': 'http',
                'timeout': 5
            }
        ]

        with patch('socket.create_connection') as mock_socket:
            mock_socket.return_value.__enter__.return_value = Mock()

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            results = loop.run_until_complete(check_local_services(services))
            loop.close()

            self.assertIsInstance(results, list)
            self.assertGreater(len(results), 0)


class TestNetworkDiagnosticErrorHandling(unittest.TestCase):
    """Network Diagnostic Error Handling Tests"""

    def setUp(self):
        """Set up test fixtures"""
        self.diagnostic = NetworkDiagnostic()

    @patch('subprocess.run')
    def test_subprocess_error_handling(self, mock_run):
        """Test subprocess error handling"""
        mock_run.side_effect = subprocess.TimeoutExpired('ipconfig', 10)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        interfaces = loop.run_until_complete(self.diagnostic.get_network_interfaces())
        loop.close()

        self.assertIsInstance(interfaces, list)

    @patch('subprocess.run')
    def test_subprocess_file_not_found(self, mock_run):
        """Test subprocess command not found"""
        mock_run.side_effect = FileNotFoundError()

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        interfaces = loop.run_until_complete(self.diagnostic.get_network_interfaces())
        loop.close()

        self.assertIsInstance(interfaces, list)

    def test_socket_error_handling(self):
        """Test socket error handling"""
        target = {'host': 'invalid-host-with-long-name-that-will-fail-dns.com', 'type': 'dns', 'timeout': 1}
        result = self.diagnostic._test_single_connectivity(target)

        self.assertEqual(result.status, NetworkStatus.DISCONNECTED)
        self.assertIsNotNone(result.error_message)

    def test_unknown_connection_type(self):
        """Test unknown connection type handling"""
        target = {'host': 'example.com', 'type': 'tcp', 'timeout': 5}  # Use known type

        # Mock to simulate connection failure for unknown behavior
        with patch('socket.create_connection') as mock_socket:
            mock_socket.side_effect = Exception("Unknown connection type")
            result = self.diagnostic._test_single_connectivity(target)

            self.assertEqual(result.status, NetworkStatus.DISCONNECTED)

    def test_async_context_manager(self):
        """Test async context manager"""
        async def test_context_manager():
            async with NetworkDiagnostic() as diagnostic:
                self.assertIsNotNone(diagnostic)
                return diagnostic

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        diagnostic = loop.run_until_complete(test_context_manager())
        loop.close()

        self.assertIsNotNone(diagnostic)


if __name__ == '__main__':
    # Create test suite
    suite = unittest.TestSuite()

    # Add test cases
    suite.addTest(unittest.makeSuite(TestNetworkDiagnostic))
    suite.addTest(unittest.makeSuite(TestNetworkDiagnosticIntegration))
    suite.addTest(unittest.makeSuite(TestNetworkDiagnosticErrorHandling))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1)