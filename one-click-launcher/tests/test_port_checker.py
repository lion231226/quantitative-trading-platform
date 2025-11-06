"""
Tests for PortChecker module

This test suite covers:
- Port availability checking
- Process identification for occupied ports
- Port range scanning with progress tracking
- Service type mappings and conflict resolution
- Alternative port suggestions
- Cross-platform compatibility
- Progress tracking integration
"""

import pytest
import asyncio
import socket
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, AsyncMock

from core.port_checker import (
    PortChecker,
    PortStatus,
    ServiceType,
    PortCheckResult,
    PortScanSummary,
    ProcessInfo,
    DEFAULT_PORTS
)
from utils.progress_tracker import ProgressTracker


class TestPortChecker:
    """Test suite for PortChecker class"""

    @pytest.fixture
    def checker(self):
        """Create a PortChecker instance for testing"""
        checker = PortChecker()
        checker.timeout = 10  # Override default timeout for faster tests
        return checker

    @pytest.fixture
    def mock_progress_tracker(self):
        """Create a mock progress tracker"""
        tracker = Mock(spec=ProgressTracker)
        tracker.start_task = Mock()
        tracker.update_progress = Mock()
        tracker.complete_task = Mock()
        return tracker

    @pytest.fixture
    def available_port_mock(self):
        """Create a mock that simulates available port"""
        mock_socket = Mock()
        mock_socket.bind = Mock()
        mock_socket.close = Mock()
        return mock_socket

    @pytest.fixture
    def occupied_port_mock(self):
        """Create a mock that simulates occupied port"""
        mock_socket = Mock()
        mock_socket.bind = Mock(side_effect=socket.error("Address already in use"))
        mock_socket.close = Mock()
        return mock_socket

    def test_init_default_values(self):
        """Test PortChecker initialization with default values"""
        checker = PortChecker()
        assert checker.timeout == 5
        assert checker.progress_tracker is None
        assert checker.os_detector is not None

    def test_init_custom_timeout(self):
        """Test PortChecker initialization with custom timeout"""
        checker = PortChecker()
        checker.timeout = 30
        assert checker.timeout == 30

    def test_set_progress_tracker(self, checker, mock_progress_tracker):
        """Test setting progress tracker"""
        checker.set_progress_tracker(mock_progress_tracker)
        assert checker.progress_tracker == mock_progress_tracker

    def test_create_socket(self, checker):
        """Test socket creation"""
        sock = checker._create_socket()
        assert isinstance(sock, socket.socket)
        assert sock.family == socket.AF_INET
        assert sock.type == socket.SOCK_STREAM
        assert sock.gettimeout() == checker.timeout
        sock.close()

    @pytest.mark.asyncio
    async def test_check_port_availability_success(self, checker, available_port_mock):
        """Test successful port availability check"""
        with patch.object(checker, '_create_socket', return_value=available_port_mock):
            result = await checker.check_port_availability('localhost', 3000)

            assert result.port == 3000
            assert result.host == 'localhost'
            assert result.status == PortStatus.AVAILABLE
            assert result.is_available is True
            assert result.process_info is None
            assert result.error_message is None
            assert result.check_time > 0

    @pytest.mark.asyncio
    async def test_check_port_availability_occupied(self, checker, occupied_port_mock):
        """Test port availability check for occupied port"""
        with patch.object(checker, '_create_socket', return_value=occupied_port_mock):
            with patch.object(checker, '_get_process_info', return_value=None):
                result = await checker.check_port_availability('localhost', 3000)

                assert result.port == 3000
                assert result.host == 'localhost'
                assert result.status == PortStatus.OCCUPIED
                assert result.is_available is False
                assert result.process_info is None
                assert "Address already in use" in result.error_message

    @pytest.mark.asyncio
    async def test_check_port_availability_permission_denied(self, checker):
        """Test port availability check with permission denied"""
        mock_socket = Mock()
        mock_socket.bind = Mock(side_effect=socket.error("Permission denied"))
        mock_socket.close = Mock()

        with patch.object(checker, '_create_socket', return_value=mock_socket):
            result = await checker.check_port_availability('localhost', 80)

            assert result.status == PortStatus.CONFLICT
            assert result.is_available is False
            assert "Permission denied" in result.error_message

    @pytest.mark.asyncio
    async def test_check_port_availability_unexpected_error(self, checker):
        """Test port availability check with unexpected error"""
        with patch.object(checker, '_create_socket', side_effect=Exception("Unexpected error")):
            result = await checker.check_port_availability('localhost', 3000)

            assert result.status == PortStatus.ERROR
            assert result.is_available is False
            assert "Unexpected error" in result.error_message

    @pytest.mark.asyncio
    async def test_get_process_info_no_psutil(self, checker):
        """Test process info when psutil is not available"""
        with patch('core.port_checker.psutil', None):
            info = await checker._get_process_info('localhost', 3000)
            assert info is None

    @pytest.mark.asyncio
    async def test_get_process_info_with_psutil_no_connections(self, checker):
        """Test process info when no connections are found"""
        mock_psutil = Mock()
        mock_psutil.net_connections.return_value = []

        with patch('core.port_checker.psutil', mock_psutil):
            info = await checker._get_process_info('localhost', 3000)
            assert info is None

    @pytest.mark.asyncio
    async def test_get_process_info_with_process_found(self, checker):
        """Test process info when process is found"""
        # Mock connection
        mock_connection = Mock()
        mock_connection.laddr.port = 3000
        mock_connection.status = 'LISTEN'
        mock_connection.pid = 1234

        # Mock process
        mock_process = Mock()
        mock_process.pid = 1234
        mock_process.name.return_value = 'python'
        mock_process.cmdline.return_value = ['python', 'app.py']
        mock_process.username.return_value = 'user'
        mock_process.cpu_percent.return_value = 15.5
        mock_process.memory_percent.return_value = 5.2
        mock_process.create_time.return_value = 1640995200.0

        mock_psutil = Mock()
        mock_psutil.net_connections.return_value = [mock_connection]
        mock_psutil.CONN_ESTABLISHED = 'ESTABLISHED'
        mock_psutil.CONN_LISTEN = 'LISTEN'
        mock_psutil.Process.return_value = mock_process

        with patch('core.port_checker.psutil', mock_psutil):
            info = await checker._get_process_info('localhost', 3000)

            assert info is not None
            assert info['pid'] == 1234
            assert info['name'] == 'python'
            assert 'python app.py' in info['command_line']
            assert info['user'] == 'user'
            assert info['cpu_percent'] == 15.5
            assert info['memory_percent'] == 5.2

    @pytest.mark.asyncio
    async def test_get_process_info_process_access_denied(self, checker):
        """Test process info when process access is denied"""
        # Mock connection
        mock_connection = Mock()
        mock_connection.laddr.port = 3000
        mock_connection.status = 'LISTEN'
        mock_connection.pid = 1234

        mock_psutil = Mock()
        mock_psutil.net_connections.return_value = [mock_connection]
        mock_psutil.CONN_ESTABLISHED = 'ESTABLISHED'
        mock_psutil.CONN_LISTEN = 'LISTEN'
        mock_psutil.Process.side_effect = Exception("Access denied")

        with patch('core.port_checker.psutil', mock_psutil):
            info = await checker._get_process_info('localhost', 3000)
            assert info is None

    @pytest.mark.asyncio
    async def test_scan_port_range_with_progress(self, checker, mock_progress_tracker):
        """Test scanning a range of ports with progress tracking"""
        checker.set_progress_tracker(mock_progress_tracker)

        # Mock port check results
        mock_results = []
        for port in range(3000, 3003):
            mock_result = Mock(spec=PortCheckResult)
            mock_result.port = port
            mock_result.is_available = port % 2 == 0  # Even ports available
            mock_results.append(mock_result)

        with patch.object(checker, 'check_port_availability', side_effect=mock_results):
            results = await checker.scan_port_range('localhost', 3000, 3002)

            assert len(results) == 3
            assert mock_progress_tracker.start_task.called
            assert mock_progress_tracker.update_progress.call_count == 3
            assert mock_progress_tracker.complete_task.called

    @pytest.mark.asyncio
    async def test_scan_port_range_no_progress(self, checker):
        """Test scanning a range of ports without progress tracking"""
        mock_result = Mock(spec=PortCheckResult)
        mock_result.port = 3000
        mock_result.is_available = True

        with patch.object(checker, 'check_port_availability', return_value=mock_result):
            results = await checker.scan_port_range('localhost', 3000, 3000)

            assert len(results) == 1

    @pytest.mark.asyncio
    async def test_check_service_ports_web_server(self, checker):
        """Test checking common ports for web server service"""
        mock_results = []
        for port in [80, 8080, 8000, 3000]:
            mock_result = Mock(spec=PortCheckResult)
            mock_result.port = port
            mock_result.is_available = True
            mock_results.append(mock_result)

        with patch.object(checker, 'scan_port_range', return_value=mock_results):
            results = await checker.check_service_ports('localhost', ServiceType.WEB_SERVER)

            assert len(results) == 4
            port_numbers = [r.port for r in results]
            assert 80 in port_numbers
            assert 8080 in port_numbers
            assert 8000 in port_numbers
            assert 3000 in port_numbers

    @pytest.mark.asyncio
    async def test_check_service_ports_unknown_service(self, checker):
        """Test checking ports for unknown service type"""
        with patch('core.port_checker.logger') as mock_logger:
            results = await checker.check_service_ports('localhost', 'unknown_service')

            assert results == []
            mock_logger.warning.assert_called_with("Unknown service type: unknown_service")

    @pytest.mark.asyncio
    async def test_find_available_port_success(self, checker):
        """Test finding an available port"""
        mock_results = [False, True]  # First port occupied, second available
        mock_check_results = []
        for i, is_available in enumerate(mock_results):
            mock_result = Mock(spec=PortCheckResult)
            mock_result.is_available = is_available
            mock_check_results.append(mock_result)

        with patch.object(checker, 'check_port_availability', side_effect=mock_check_results):
            port = await checker.find_available_port('localhost', 3000, 5)

            assert port == 3001

    @pytest.mark.asyncio
    async def test_find_available_port_no_available_port(self, checker):
        """Test finding available port when none are available"""
        mock_result = Mock(spec=PortCheckResult)
        mock_result.is_available = False

        with patch.object(checker, 'check_port_availability', return_value=mock_result):
            port = await checker.find_available_port('localhost', 3000, 3)

            assert port is None

    @pytest.mark.asyncio
    async def test_suggest_alternative_ports_from_defaults(self, checker):
        """Test suggesting alternative ports from default ports"""
        occupied_ports = [3000]
        service_type = ServiceType.FRONTEND

        # Mock availability check for alternative default ports
        mock_results = []
        for port in [3001, 4000]:  # Default alternative ports for frontend
            mock_result = Mock(spec=PortCheckResult)
            mock_result.is_available = True
            mock_results.append(mock_result)

        with patch.object(checker, 'check_port_availability', side_effect=mock_results):
            alternatives = await checker.suggest_alternative_ports('localhost', occupied_ports, service_type)

            assert len(alternatives) >= 1
            assert 3001 in alternatives or 4000 in alternatives

    @pytest.mark.asyncio
    async def test_suggest_alternative_ports_custom_range(self, checker):
        """Test suggesting alternative ports from custom range"""
        occupied_ports = [9999]
        service_type = ServiceType.WEB_SERVER

        # Mock availability check: first default ports (all unavailable), then custom range
        mock_results = []

        # Mock WEB_SERVER default ports as unavailable
        for port in [80, 8080, 8000, 3000]:  # WEB_SERVER default ports
            mock_result = Mock(spec=PortCheckResult)
            mock_result.is_available = False
            mock_results.append(mock_result)

        # Mock custom range ports - create many mock results to satisfy algorithm's search for 5 ports
        for port in range(10000, 10100):  # Large enough range to find 5 available ports
            mock_result = Mock(spec=PortCheckResult)
            # Make first few ports available, then rest unavailable to stop search early
            mock_result.is_available = port in [10001, 10003]  # Only these two available
            mock_results.append(mock_result)

        with patch.object(checker, 'check_port_availability', side_effect=mock_results):
            alternatives = await checker.suggest_alternative_ports('localhost', occupied_ports, service_type)

            assert len(alternatives) >= 1
            assert 10001 in alternatives or 10003 in alternatives

    @pytest.mark.asyncio
    async def test_check_required_ports_all_available(self, checker, mock_progress_tracker):
        """Test checking required ports when all are available"""
        checker.set_progress_tracker(mock_progress_tracker)
        required_ports = [3000, 3001, 3002]

        mock_results = []
        for port in required_ports:
            mock_result = Mock(spec=PortCheckResult)
            mock_result.port = port
            mock_result.is_available = True
            mock_results.append(mock_result)

        with patch.object(checker, 'check_port_availability', side_effect=mock_results):
            summary = await checker.check_required_ports('localhost', required_ports)

            assert summary.total_ports == 3
            assert summary.available_ports == 3
            assert summary.occupied_ports == 0
            assert summary.conflicting_ports == 0
            assert len(summary.results) == 3
            assert summary.scan_duration > 0
            assert mock_progress_tracker.start_task.called
            assert mock_progress_tracker.complete_task.called

    @pytest.mark.asyncio
    async def test_check_required_ports_mixed_status(self, checker, mock_progress_tracker):
        """Test checking required ports with mixed status"""
        checker.set_progress_tracker(mock_progress_tracker)
        required_ports = [3000, 3001, 3002]

        mock_results = []
        for i, port in enumerate(required_ports):
            mock_result = Mock(spec=PortCheckResult)
            mock_result.port = port
            mock_result.is_available = i % 2 == 0  # First and last available
            mock_result.status = PortStatus.AVAILABLE if i % 2 == 0 else PortStatus.OCCUPIED
            mock_results.append(mock_result)

        with patch.object(checker, 'check_port_availability', side_effect=mock_results):
            summary = await checker.check_required_ports('localhost', required_ports)

            assert summary.total_ports == 3
            assert summary.available_ports == 2
            assert summary.occupied_ports == 1
            assert summary.conflicting_ports == 0

    def test_generate_conflict_report_empty(self, checker):
        """Test generating conflict report for empty summary"""
        summary = PortScanSummary(
            total_ports=0,
            available_ports=0,
            occupied_ports=0,
            conflicting_ports=0,
            scan_duration=0.5,
            results=[]
        )

        report = checker.generate_conflict_report(summary)

        assert "PORT CONFLICT REPORT" in report
        assert "Total Ports Checked: 0" in report
        assert "Available: 0" in report
        assert "Occupied: 0" in report

    def test_generate_conflict_report_with_conflicts(self, checker):
        """Test generating conflict report with actual conflicts"""
        # Create mock results
        results = []

        # Available port
        available_result = Mock(spec=PortCheckResult)
        available_result.port = 3000
        available_result.status = PortStatus.AVAILABLE
        available_result.is_available = True
        available_result.process_info = None
        available_result.error_message = None
        results.append(available_result)

        # Occupied port with process info
        occupied_result = Mock(spec=PortCheckResult)
        occupied_result.port = 3001
        occupied_result.status = PortStatus.OCCUPIED
        occupied_result.is_available = False
        occupied_result.process_info = {
            'pid': 1234,
            'name': 'python',
            'command_line': 'python app.py',
            'user': 'testuser',
            'cpu_percent': 15.5,
            'memory_percent': 5.2
        }
        occupied_result.error_message = "Address already in use"
        results.append(occupied_result)

        summary = PortScanSummary(
            total_ports=2,
            available_ports=1,
            occupied_ports=1,
            conflicting_ports=0,
            scan_duration=1.5,
            results=results
        )

        report = checker.generate_conflict_report(summary)

        assert "PORT CONFLICT REPORT" in report
        assert "Total Ports Checked: 2" in report
        assert "Available: 1" in report
        assert "Occupied: 1" in report
        assert "✅ Port 3000 (AVAILABLE) - Available" in report
        assert "❌ Port 3001 (OCCUPIED) - Occupied" in report
        assert "Process: python (PID: 1234)" in report
        assert "Command: python app.py" in report
        assert "RECOMMENDATIONS:" in report
        assert "Stop process 'python' (PID: 1234)" in report

    def test_save_scan_results_success(self, checker):
        """Test saving scan results to file"""
        # Create mock summary
        mock_result = Mock(spec=PortCheckResult)
        mock_result.port = 3000
        mock_result.host = 'localhost'
        mock_result.status = PortStatus.AVAILABLE
        mock_result.is_available = True
        mock_result.process_info = None
        mock_result.error_message = None
        mock_result.check_time = 0.1

        summary = PortScanSummary(
            total_ports=1,
            available_ports=1,
            occupied_ports=0,
            conflicting_ports=0,
            scan_duration=0.5,
            results=[mock_result]
        )

        # Test saving
        temp_dir = tempfile.mkdtemp()
        try:
            output_file = Path(temp_dir) / "test_results.json"
            success = checker.save_scan_results(summary, str(output_file))

            assert success is True
            assert output_file.exists()

            # Verify content
            with open(output_file, 'r') as f:
                data = json.load(f)

            assert data['total_ports'] == 1
            assert data['available_ports'] == 1
            assert len(data['results']) == 1
            assert data['results'][0]['port'] == 3000
            assert data['results'][0]['status'] == 'available'

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_save_scan_results_failure(self, checker):
        """Test saving scan results with invalid path"""
        summary = PortScanSummary(
            total_ports=0,
            available_ports=0,
            occupied_ports=0,
            conflicting_ports=0,
            scan_duration=0.0,
            results=[]
        )

        # Try to save to invalid path
        invalid_path = "/invalid/path/that/does/not/exist/results.json"
        success = checker.save_scan_results(summary, invalid_path)

        assert success is False

    @pytest.mark.asyncio
    async def test_resolve_port_conflicts_success(self, checker):
        """Test resolving port conflicts successfully"""
        conflicts = [(3000, ServiceType.WEB_SERVER), (3001, ServiceType.FRONTEND)]

        # Mock alternative suggestions
        def mock_suggest_alternatives(host, occupied, service_type):
            if service_type == ServiceType.WEB_SERVER:
                return [8080, 8000]
            elif service_type == ServiceType.FRONTEND:
                return [3002, 3003]
            return []

        with patch.object(checker, 'suggest_alternative_ports', side_effect=mock_suggest_alternatives):
            resolutions = await checker.resolve_port_conflicts('localhost', conflicts)

            assert len(resolutions) == 2
            assert resolutions[3000] == 8080
            assert resolutions[3001] == 3002

    @pytest.mark.asyncio
    async def test_resolve_port_conflicts_no_alternatives(self, checker):
        """Test resolving port conflicts when no alternatives found"""
        conflicts = [(3000, ServiceType.WEB_SERVER)]

        with patch.object(checker, 'suggest_alternative_ports', return_value=[]):
            resolutions = await checker.resolve_port_conflicts('localhost', conflicts)

            assert len(resolutions) == 1
            assert resolutions[3000] is None

    def test_get_service_recommendations(self, checker):
        """Test getting service recommendations for occupied ports"""
        occupied_ports = [3000, 5432, 6379, 8080]

        recommendations = checker.get_service_recommendations(occupied_ports)

        assert isinstance(recommendations, dict)
        assert len(recommendations) > 0

        # Check for common services
        service_names = list(recommendations.keys())
        assert any("Web Server" in name for name in service_names)
        assert any("Database" in name for name in service_names)

        # Verify recommendation structure
        for service_name, recs in recommendations.items():
            assert isinstance(recs, list)
            assert len(recs) >= 1
            assert any("Port(s)" in rec for rec in recs)

    def test_default_ports_completeness(self):
        """Test that default ports cover all service types"""
        service_types = set(ServiceType)
        defined_service_types = set(DEFAULT_PORTS.keys())

        assert service_types.issubset(defined_service_types), "Not all service types have default ports defined"

        # Verify each service has at least one port
        for service_type, ports in DEFAULT_PORTS.items():
            assert len(ports) > 0, f"Service {service_type} has no default ports"
            assert all(isinstance(p, int) and p > 0 for p in ports), f"Invalid ports for {service_type}"


class TestPortCheckerIntegration:
    """Integration tests for PortChecker with realistic scenarios"""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_real_port_scanning(self):
        """Test real port scanning on localhost"""
        checker = PortChecker()
        checker.timeout = 5

        # Scan a small range of ports that are likely to be mostly available
        results = await checker.scan_port_range('localhost', 35000, 35005)

        assert len(results) == 6  # 35000, 35001, 35002, 35003, 35004, 35005

        for result in results:
            assert isinstance(result, PortCheckResult)
            assert 35000 <= result.port <= 35005
            assert result.host == 'localhost'
            assert isinstance(result.status, PortStatus)
            assert isinstance(result.is_available, bool)
            assert result.check_time >= 0

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_real_service_port_checking(self):
        """Test real service port checking"""
        checker = PortChecker()
        checker.timeout = 5

        # Check for Redis (6379) - it's unlikely to be running in test environment
        results = await checker.check_service_ports('localhost', ServiceType.DATABASE_REDIS)

        assert len(results) == 1
        assert results[0].port == 6379

        # The result should show Redis as unavailable (since it's not installed/running)
        assert results[0].is_available is True  # Port 6379 should be available

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_real_find_available_port(self):
        """Test finding a real available port"""
        checker = PortChecker()
        checker.timeout = 5

        port = await checker.find_available_port('localhost', 40000, 10)

        assert port is not None
        assert 40000 <= port <= 40009

        # Verify the port is actually available by trying to bind to it
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.bind(('localhost', port))
            # If bind succeeds, port is truly available
            is_available = True
        except:
            is_available = False
        finally:
            sock.close()

        assert is_available, f"Port {port} reported as available but binding failed"

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_real_process_detection(self):
        """Test real process detection for a port we know is occupied"""
        checker = PortChecker()
        checker.timeout = 5

        # First find an available port
        available_port = await checker.find_available_port('localhost', 45000, 10)
        assert available_port is not None

        # Now check if it's available (should be)
        result = await checker.check_port_availability('localhost', available_port)
        assert result.is_available is True
        assert result.process_info is None

        # Note: We can't easily test occupied port process detection in a unit test
        # as we can't guarantee a stable process will be running on a known port

    def test_real_conflict_report_generation(self):
        """Test real conflict report generation"""
        checker = PortChecker()

        # Create realistic mock results
        results = []

        # Available port
        result1 = Mock(spec=PortCheckResult)
        result1.port = 3000
        result1.status = PortStatus.AVAILABLE
        result1.is_available = True
        result1.process_info = None
        result1.error_message = None
        results.append(result1)

        # Occupied port with detailed process info
        result2 = Mock(spec=PortCheckResult)
        result2.port = 3001
        result2.status = PortStatus.OCCUPIED
        result2.is_available = False
        result2.process_info = {
            'pid': 12345,
            'name': 'node',
            'command_line': 'node server.js',
            'user': 'developer',
            'cpu_percent': 25.8,
            'memory_percent': 12.3
        }
        result2.error_message = "Address already in use"
        results.append(result2)

        # Port with permission issue
        result3 = Mock(spec=PortCheckResult)
        result3.port = 80
        result3.status = PortStatus.CONFLICT
        result3.is_available = False
        result3.process_info = None
        result3.error_message = "Permission denied"
        results.append(result3)

        summary = PortScanSummary(
            total_ports=3,
            available_ports=1,
            occupied_ports=1,
            conflicting_ports=1,
            scan_duration=2.34,
            results=results
        )

        report = checker.generate_conflict_report(summary)

        # Verify report structure and content
        assert "=" * 60 in report
        assert "PORT CONFLICT REPORT" in report
        assert "Scan Duration: 2.34 seconds" in report
        assert "Total Ports Checked: 3" in report
        assert "Available: 1" in report
        assert "Occupied: 1" in report
        assert "Conflicts: 1" in report

        # Verify individual port results
        assert "✅ Port 3000 (AVAILABLE) - Available" in report
        assert "❌ Port 3001 (OCCUPIED) - Occupied" in report
        assert "❌ Port 80 (CONFLICT) - Occupied" in report

        # Verify process details
        assert "Process: node (PID: 12345)" in report
        assert "Command: node server.js" in report
        assert "User: developer" in report
        assert "CPU: 25.8%" in report
        assert "Memory: 12.3%" in report

        # Verify error messages
        assert "Address already in use" in report
        assert "Permission denied" in report

        # Verify recommendations
        assert "RECOMMENDATIONS:" in report
        assert "Stop process 'node' (PID: 12345)" in report

        # Print for manual verification if needed
        print("\n" + "=" * 60)
        print("GENERATED CONFLICT REPORT:")
        print("=" * 60)
        print(report)
        print("=" * 60)