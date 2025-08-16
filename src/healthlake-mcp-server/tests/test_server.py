"""Tests for server creation and configuration."""

from awslabs.healthlake_mcp_server.server import create_healthlake_server


def test_server_creation():
    """Test server can be created without errors."""
    server = create_healthlake_server()
    assert server is not None
    assert server.name == 'healthlake-mcp-server'
