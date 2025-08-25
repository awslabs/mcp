"""Tests for server creation and configuration."""

import os
from awslabs.healthlake_mcp_server.server import create_healthlake_server
from unittest.mock import MagicMock, patch


@patch('awslabs.healthlake_mcp_server.fhir_operations.boto3.Session')
def test_server_creation(mock_session):
    """Test server can be created without errors."""
    # Mock the boto3 session and client
    mock_session_instance = MagicMock()
    mock_healthlake_client = MagicMock()
    mock_session.return_value = mock_session_instance
    mock_session_instance.client.return_value = mock_healthlake_client

    if 'AWS_REGION' not in os.environ:
        os.environ['AWS_REGION'] = 'us-east-1'

    server = create_healthlake_server()
    assert server is not None
    assert server.name == 'healthlake-mcp-server'
