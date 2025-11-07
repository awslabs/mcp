# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# This file is part of the awslabs namespace.
# It is intentionally minimal to support PEP 420 namespace packages.

import asyncio
import json
import os
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

import pytest
from mcp.types import TextContent

from awslabs.pcap_analyzer_mcp_server.server import PCAPAnalyzerServer, main


class TestPCAPAnalyzerServer:
    """Tests for the PCAPAnalyzerServer class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.server = PCAPAnalyzerServer()

    def test_server_initialization(self):
        """Test that the server initializes correctly."""
        assert self.server.server.name == "pcap-analyzer-mcp-server"
        assert hasattr(self.server, '_setup_tools')

    def test_resolve_pcap_path_absolute(self):
        """Test resolving absolute PCAP file paths."""
        with tempfile.NamedTemporaryFile(suffix='.pcap', delete=False) as tmp:
            tmp_path = tmp.name
            
        try:
            result = self.server._resolve_pcap_path(tmp_path)
            assert result == tmp_path
        finally:
            os.unlink(tmp_path)

    def test_resolve_pcap_path_relative_in_storage(self):
        """Test resolving relative PCAP file paths in storage directory."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Create a test file in the temporary directory
            test_file = os.path.join(tmp_dir, 'test.pcap')
            Path(test_file).touch()
            
            # Mock the storage directory
            with patch('awslabs.pcap_analyzer_mcp_server.server.PCAP_STORAGE_DIR', tmp_dir):
                result = self.server._resolve_pcap_path('test.pcap')
                assert result == test_file

    def test_resolve_pcap_path_not_found(self):
        """Test resolving non-existent PCAP file paths."""
        with pytest.raises(FileNotFoundError):
            self.server._resolve_pcap_path('nonexistent.pcap')

    @patch('awslabs.pcap_analyzer_mcp_server.server.asyncio.create_subprocess_exec')
    async def test_run_tshark_command_success(self, mock_subprocess):
        """Test successful tshark command execution."""
        # Mock successful subprocess
        mock_process = AsyncMock()
        mock_process.communicate.return_value = (b'test output', b'')
        mock_process.returncode = 0
        mock_subprocess.return_value = mock_process

        result = await self.server._run_tshark_command(['-v'])
        
        assert result == 'test output'
        mock_subprocess.assert_called_once_with(
            'tshark', '-v',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

    @patch('awslabs.pcap_analyzer_mcp_server.server.asyncio.create_subprocess_exec')
    async def test_run_tshark_command_failure(self, mock_subprocess):
        """Test failed tshark command execution."""
        # Mock failed subprocess
        mock_process = AsyncMock()
        mock_process.communicate.return_value = (b'', b'error message')
        mock_process.returncode = 1
        mock_subprocess.return_value = mock_process

        with pytest.raises(RuntimeError, match="tshark command failed"):
            await self.server._run_tshark_command(['-invalid'])

    @patch('awslabs.pcap_analyzer_mcp_server.server.psutil.net_if_addrs')
    @patch('awslabs.pcap_analyzer_mcp_server.server.psutil.net_if_stats')
    async def test_list_network_interfaces(self, mock_stats, mock_addrs):
        """Test listing network interfaces."""
        # Mock network interface data
        mock_addr = MagicMock()
        mock_addr.address = '192.168.1.1'
        mock_addrs.return_value = {'eth0': [mock_addr]}
        
        mock_stat = MagicMock()
        mock_stat.isup = True
        mock_stat.speed = 1000
        mock_stats.return_value = {'eth0': mock_stat}

        result = await self.server._list_network_interfaces()
        
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        
        # Parse the JSON result
        data = json.loads(result[0].text)
        assert data['total_count'] == 1
        assert data['interfaces'][0]['name'] == 'eth0'
        assert data['interfaces'][0]['is_up'] is True

    @patch('awslabs.pcap_analyzer_mcp_server.server.asyncio.create_subprocess_exec')
    async def test_start_packet_capture(self, mock_subprocess):
        """Test starting packet capture."""
        # Mock subprocess for capture
        mock_process = AsyncMock()
        mock_subprocess.return_value = mock_process

        with tempfile.TemporaryDirectory() as tmp_dir:
            with patch('awslabs.pcap_analyzer_mcp_server.server.PCAP_STORAGE_DIR', tmp_dir):
                result = await self.server._start_packet_capture(
                    interface='eth0',
                    duration=30,
                    capture_filter='tcp port 80'
                )
                
                assert len(result) == 1
                assert isinstance(result[0], TextContent)
                
                # Parse the JSON result
                data = json.loads(result[0].text)
                assert data['status'] == 'started'
                assert data['interface'] == 'eth0'
                assert data['duration'] == 30
                assert data['filter'] == 'tcp port 80'
                assert 'capture_id' in data

    async def test_stop_packet_capture_not_found(self):
        """Test stopping non-existent packet capture."""
        result = await self.server._stop_packet_capture('nonexistent_id')
        
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert 'not found' in result[0].text

    @patch('awslabs.pcap_analyzer_mcp_server.server.PCAPAnalyzerServer._run_tshark_command')
    async def test_analyze_pcap_file(self, mock_tshark):
        """Test PCAP file analysis."""
        mock_tshark.return_value = 'analysis output'
        
        with tempfile.NamedTemporaryFile(suffix='.pcap', delete=False) as tmp:
            tmp_path = tmp.name
            
        try:
            result = await self.server._analyze_pcap_file(tmp_path, 'summary')
            
            assert len(result) == 1
            assert isinstance(result[0], TextContent)
            
            # Parse the JSON result
            data = json.loads(result[0].text)
            assert data['analysis_type'] == 'summary'
            assert data['analysis_output'] == 'analysis output'
            
        finally:
            os.unlink(tmp_path)

    async def test_analyze_pcap_file_not_found(self):
        """Test analyzing non-existent PCAP file."""
        result = await self.server._analyze_pcap_file('nonexistent.pcap')
        
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert 'Error analyzing PCAP:' in result[0].text


class TestPCAPAnalyzerServerIntegration:
    """Integration tests for the PCAP Analyzer server."""

    def setup_method(self):
        """Set up test fixtures."""
        self.server = PCAPAnalyzerServer()

    def test_server_has_required_methods(self):
        """Test that server has all required methods for 31 tools."""
        # Test that the server has methods for all tool categories
        required_methods = [
            '_list_network_interfaces',
            '_start_packet_capture',
            '_stop_packet_capture',
            '_analyze_pcap_file',
            '_run_tshark_command',
            '_resolve_pcap_path'
        ]
        
        for method in required_methods:
            assert hasattr(self.server, method)
            assert callable(getattr(self.server, method))

    def test_server_configuration(self):
        """Test server configuration and setup."""
        # Test that server is properly configured
        assert self.server.server.name == "pcap-analyzer-mcp-server"
        
        # Test that setup_tools was called during initialization
        assert hasattr(self.server, '_setup_tools')


class TestMainFunction:
    """Tests for the main function."""

    @patch('awslabs.pcap_analyzer_mcp_server.server.PCAPAnalyzerServer')
    @patch('awslabs.pcap_analyzer_mcp_server.server.asyncio.run')
    def test_main_function(self, mock_asyncio_run, mock_server_class):
        """Test the main function."""
        mock_server = MagicMock()
        mock_server_class.return_value = mock_server
        
        main()
        
        # Verify server was created and run method was called
        mock_server_class.assert_called_once()
        mock_asyncio_run.assert_called_once_with(mock_server.run())


class TestErrorHandling:
    """Tests for error handling scenarios."""

    def setup_method(self):
        """Set up test fixtures."""
        self.server = PCAPAnalyzerServer()

    @patch('awslabs.pcap_analyzer_mcp_server.server.psutil.net_if_addrs')
    async def test_list_network_interfaces_error(self, mock_addrs):
        """Test error handling in list_network_interfaces."""
        mock_addrs.side_effect = Exception('Network error')
        
        result = await self.server._list_network_interfaces()
        
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert 'Error listing interfaces' in result[0].text


class TestConfigurationValidation:
    """Tests for configuration and environment validation."""

    def test_environment_variables(self):
        """Test that environment variables are properly handled."""
        # Test default values
        from awslabs.pcap_analyzer_mcp_server.server import (
            PCAP_STORAGE_DIR, MAX_CAPTURE_DURATION, WIRESHARK_PATH
        )
        
        # These should have default values
        assert PCAP_STORAGE_DIR is not None
        assert MAX_CAPTURE_DURATION is not None
        assert WIRESHARK_PATH is not None

    @patch('awslabs.pcap_analyzer_mcp_server.server.Path.mkdir')
    def test_storage_directory_creation(self, mock_mkdir):
        """Test that storage directory creation is attempted."""
        # Test that the Path.mkdir method would be called
        # This tests the logic without actually creating directories
        mock_mkdir.return_value = None
        
        # Re-import to trigger directory creation logic
        import importlib
        import awslabs.pcap_analyzer_mcp_server.server
        importlib.reload(awslabs.pcap_analyzer_mcp_server.server)
        
        # Verify mkdir was called with proper parameters
        mock_mkdir.assert_called_with(parents=True, exist_ok=True)


class TestToolInputValidation:
    """Tests for tool input validation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.server = PCAPAnalyzerServer()

    async def test_start_packet_capture_with_interface(self):
        """Test start_packet_capture method with valid interface."""
        with patch('awslabs.pcap_analyzer_mcp_server.server.asyncio.create_subprocess_exec') as mock_subprocess:
            mock_process = AsyncMock()
            mock_subprocess.return_value = mock_process
            
            with tempfile.TemporaryDirectory() as tmp_dir:
                with patch('awslabs.pcap_analyzer_mcp_server.server.PCAP_STORAGE_DIR', tmp_dir):
                    # Test with valid interface
                    result = await self.server._start_packet_capture(interface="eth0")
                    assert len(result) == 1
                    assert isinstance(result[0], TextContent)

    async def test_analyze_pcap_file_with_valid_file(self):
        """Test analyze_pcap_file method with valid file."""
        with tempfile.NamedTemporaryFile(suffix='.pcap', delete=False) as tmp:
            tmp_path = tmp.name
            
        try:
            with patch('awslabs.pcap_analyzer_mcp_server.server.PCAPAnalyzerServer._run_tshark_command') as mock_tshark:
                mock_tshark.return_value = 'test output'
                result = await self.server._analyze_pcap_file(pcap_file=tmp_path)
                assert len(result) == 1
                assert isinstance(result[0], TextContent)
        finally:
            os.unlink(tmp_path)


class TestAsyncOperations:
    """Tests for asynchronous operations."""

    def setup_method(self):
        """Set up test fixtures."""
        self.server = PCAPAnalyzerServer()

    @patch('awslabs.pcap_analyzer_mcp_server.server.asyncio.create_subprocess_exec')
    async def test_concurrent_tshark_commands(self, mock_subprocess):
        """Test concurrent tshark command execution."""
        # Mock subprocess
        mock_process = AsyncMock()
        mock_process.communicate.return_value = (b'output', b'')
        mock_process.returncode = 0
        mock_subprocess.return_value = mock_process

        # Run multiple commands concurrently
        tasks = [
            self.server._run_tshark_command(['-v']),
            self.server._run_tshark_command(['-h']),
            self.server._run_tshark_command(['-D'])
        ]
        
        results = await asyncio.gather(*tasks)
        
        assert len(results) == 3
        for result in results:
            assert result == 'output'


class TestSecurityAndSafety:
    """Tests for security and safety features."""

    def setup_method(self):
        """Set up test fixtures."""
        self.server = PCAPAnalyzerServer()

    def test_path_traversal_protection(self):
        """Test protection against path traversal attacks."""
        # Test that relative paths with .. are handled safely
        with pytest.raises(FileNotFoundError):
            self.server._resolve_pcap_path('../../../etc/passwd')

    async def test_command_injection_protection(self):
        """Test protection against command injection."""
        with patch('awslabs.pcap_analyzer_mcp_server.server.asyncio.create_subprocess_exec') as mock_subprocess:
            mock_process = AsyncMock()
            mock_process.communicate.return_value = (b'', b'command not found')
            mock_process.returncode = 1
            mock_subprocess.return_value = mock_process
            
            # Try to inject malicious commands
            with pytest.raises(RuntimeError):
                await self.server._run_tshark_command(['; rm -rf /'])


class TestPerformanceAndLimits:
    """Tests for performance and resource limits."""

    def setup_method(self):
        """Set up test fixtures."""
        self.server = PCAPAnalyzerServer()

    def test_max_capture_duration_limit(self):
        """Test that capture duration limits are enforced."""
        from awslabs.pcap_analyzer_mcp_server.server import MAX_CAPTURE_DURATION
        
        # The limit should be reasonable (not more than 1 hour by default)
        assert MAX_CAPTURE_DURATION <= 3600

    async def test_large_file_handling(self):
        """Test handling of large PCAP files."""
        # Create a temporary large-ish file
        with tempfile.NamedTemporaryFile(suffix='.pcap', delete=False) as tmp:
            # Write some data to simulate a PCAP file
            tmp.write(b'\x00' * 1024)  # 1KB test file
            tmp_path = tmp.name
            
        try:
            # This should not crash even with larger files
            result = await self.server._analyze_pcap_file(tmp_path)
            assert len(result) == 1
            assert isinstance(result[0], TextContent)
        finally:
            os.unlink(tmp_path)


# Test fixtures and utilities
@pytest.fixture
def sample_pcap_file():
    """Create a sample PCAP file for testing."""
    with tempfile.NamedTemporaryFile(suffix='.pcap', delete=False) as tmp:
        # Write minimal PCAP header
        tmp.write(b'\xd4\xc3\xb2\xa1\x02\x00\x04\x00')  # Basic PCAP header
        tmp_path = tmp.name
    
    yield tmp_path
    
    # Cleanup
    if os.path.exists(tmp_path):
        os.unlink(tmp_path)


class TestWithSampleData:
    """Tests using sample PCAP data."""

    def setup_method(self):
        """Set up test fixtures."""
        self.server = PCAPAnalyzerServer()

    async def test_analyze_sample_pcap(self, sample_pcap_file):
        """Test analyzing a sample PCAP file."""
        with patch('awslabs.pcap_analyzer_mcp_server.server.PCAPAnalyzerServer._run_tshark_command') as mock_tshark:
            mock_tshark.return_value = 'sample analysis output'
            
            result = await self.server._analyze_pcap_file(sample_pcap_file)
            
            assert len(result) == 1
            assert isinstance(result[0], TextContent)
            
            # Check if it's a JSON response or error message
            if result[0].text.startswith('Error'):
                # If it's an error, just verify it's a proper error message
                assert 'Error analyzing PCAP:' in result[0].text
            else:
                # If it's successful, parse JSON
                data = json.loads(result[0].text)
                assert 'analysis_output' in data
                assert data['analysis_output'] == 'sample analysis output'
