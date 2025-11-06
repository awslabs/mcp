#!/usr/bin/env python3
"""
Tests for PCAP Analyzer MCP Server
"""

from unittest.mock import MagicMock, Mock, patch

import pytest

from awslabs.pcap_analyzer_mcp_server.pcap_analyzer_server import (
    check_tshark_available,
    get_network_interfaces,
    mcp,
    sanitize_path,
    validate_display_filter,
    validate_interface_name,
    validate_pcap_filename,
    validate_search_pattern,
)


class TestValidationFunctions:
    """Test security validation functions"""

    def test_validate_interface_name_valid(self):
        """Test valid interface names"""
        assert validate_interface_name("en0") is True
        assert validate_interface_name("eth0") is True
        assert validate_interface_name("wlan0") is True
        assert validate_interface_name("lo0") is True

    def test_validate_interface_name_invalid(self):
        """Test invalid interface names"""
        assert validate_interface_name("") is False
        assert validate_interface_name(None) is False
        assert validate_interface_name("eth0; rm -rf /") is False
        assert validate_interface_name("eth0|cat /etc/passwd") is False

    def test_validate_pcap_filename_valid(self):
        """Test valid PCAP filenames"""
        assert validate_pcap_filename("test.pcap") is True
        assert validate_pcap_filename("capture_123.pcap") is True
        assert validate_pcap_filename("network-analysis.pcap") is True

    def test_validate_pcap_filename_invalid(self):
        """Test invalid PCAP filenames"""
        assert validate_pcap_filename("") is False
        assert validate_pcap_filename(None) is False
        assert validate_pcap_filename("../etc/passwd.pcap") is False
        assert validate_pcap_filename("test.txt") is False
        assert validate_pcap_filename("/tmp/test.pcap") is False

    def test_validate_display_filter_valid(self):
        """Test valid display filters"""
        assert validate_display_filter("") is True
        assert validate_display_filter("tcp.port == 80") is True
        assert validate_display_filter("ip.src == 192.168.1.1") is True

    def test_validate_display_filter_invalid(self):
        """Test invalid display filters"""
        assert validate_display_filter("tcp.port == 80; rm -rf /") is False
        assert validate_display_filter("tcp.port == 80|cat /etc/passwd") is False
        assert validate_display_filter("tcp.port == 80`whoami`") is False

    def test_validate_search_pattern_valid(self):
        """Test valid search patterns"""
        assert validate_search_pattern("GET") is True
        assert validate_search_pattern("POST") is True
        assert validate_search_pattern("HTTP/1.1") is True

    def test_validate_search_pattern_invalid(self):
        """Test invalid search patterns"""
        assert validate_search_pattern("") is False
        assert validate_search_pattern(None) is False
        assert validate_search_pattern("GET; rm -rf /") is False
        assert validate_search_pattern("GET|cat /etc/passwd") is False


class TestNetworkFunctions:
    """Test network-related functions"""

    @patch("awslabs.pcap_analyzer_mcp_server.pcap_analyzer_server.safe_subprocess_run")
    def test_check_tshark_available_success(self, mock_subprocess):
        """Test successful tshark availability check"""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result

        assert check_tshark_available() is True

    @patch("awslabs.pcap_analyzer_mcp_server.pcap_analyzer_server.safe_subprocess_run")
    def test_check_tshark_available_failure(self, mock_subprocess):
        """Test failed tshark availability check"""
        mock_subprocess.side_effect = FileNotFoundError()

        assert check_tshark_available() is False

    @patch("awslabs.pcap_analyzer_mcp_server.pcap_analyzer_server.safe_subprocess_run")
    def test_get_network_interfaces_success(self, mock_subprocess):
        """Test successful network interface retrieval"""
        mock_result = Mock()
        mock_result.stdout = "1. en0 (Wi-Fi)\n2. lo0 (Loopback)\n"
        mock_subprocess.return_value = mock_result

        interfaces = get_network_interfaces()
        assert len(interfaces) == 2
        assert interfaces[0]["id"] == "1"
        assert interfaces[0]["name"] == "en0 (Wi-Fi)"

    @patch("awslabs.pcap_analyzer_mcp_server.pcap_analyzer_server.safe_subprocess_run")
    def test_get_network_interfaces_failure(self, mock_subprocess):
        """Test failed network interface retrieval"""
        mock_subprocess.side_effect = Exception("Command failed")

        interfaces = get_network_interfaces()
        assert len(interfaces) == 1
        assert "error" in interfaces[0]


class TestMCPServerIntegration:
    """Test MCP server integration and configuration"""

    def test_mcp_server_initialization(self):
        """Test that MCP server initializes correctly"""
        assert mcp is not None
        assert mcp.name == "pcap-analyzer"

    def test_sanitize_path_security(self):
        """Test path sanitization security"""
        # Test that dangerous path patterns are rejected
        with pytest.raises(ValueError, match="Invalid or unsafe path"):
            sanitize_path("../../../etc/passwd")

        # Test empty path
        result = sanitize_path("")
        assert result == ""

        # Test that path validation works
        with pytest.raises(ValueError):
            sanitize_path("invalid\x00path")

    def test_environment_variable_validation(self):
        """Test environment variable validation"""
        import os

        # Test valid directory path
        import tempfile

        from awslabs.pcap_analyzer_mcp_server.pcap_analyzer_server import (
            validate_directory_path,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            result = validate_directory_path(temp_dir)
            # Use realpath to handle macOS /var -> /private/var symlink
            assert os.path.realpath(result) == os.path.realpath(temp_dir)

        # Test invalid directory path
        with pytest.raises(ValueError):
            validate_directory_path("")

    def test_server_constants(self):
        """Test server configuration constants"""
        from awslabs.pcap_analyzer_mcp_server.pcap_analyzer_server import (
            CAPTURE_TIMEOUT,
            MAX_CAPTURE_SIZE,
        )

        assert MAX_CAPTURE_SIZE == "100MB"
        assert CAPTURE_TIMEOUT == 300
        assert isinstance(CAPTURE_TIMEOUT, int)
        assert CAPTURE_TIMEOUT > 0


# Helper function for async mocking
class AsyncMock(MagicMock):
    async def __call__(self, *args, **kwargs):
        return super(AsyncMock, self).__call__(*args, **kwargs)


if __name__ == "__main__":
    pytest.main([__file__])
