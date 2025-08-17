"""Tests for server creation and configuration."""

import os
from awslabs.healthlake_mcp_server.server import create_healthlake_server


def test_server_creation():
    """Test server can be created without errors."""
    if 'AWS_REGION' not in os.environ:
        os.environ['AWS_REGION'] = 'us-east-1'
    server = create_healthlake_server()
    assert server is not None
    assert server.name == 'healthlake-mcp-server'
