"""Global pytest fixtures for Amazon RDS Monitoring MCP Server tests."""

import pytest
from awslabs.rds_control_plane_mcp_server.common.connection import (
    CloudwatchConnectionManager,
    PIConnectionManager,
    RDSConnectionManager,
)
from awslabs.rds_control_plane_mcp_server.common.context import RDSContext
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_rds_client():
    """Fixture providing a mock RDS client for tests.

    Resets the RDS connection before and after the test.
    Returns a mock client that's automatically patched into the RDSConnectionManager.
    """
    RDSConnectionManager._client = None

    mock_client = MagicMock()

    with patch.object(RDSConnectionManager, 'get_connection', return_value=mock_client) as _:
        yield mock_client

    RDSConnectionManager._client = None


@pytest.fixture
def mock_pi_client():
    """Fixture providing a mock PI (Performance Insights) client for tests.

    Resets the PI connection before and after the test.
    Returns a mock client that's automatically patched into the PIConnectionManager.
    """
    PIConnectionManager._client = None

    mock_client = MagicMock()

    with patch.object(PIConnectionManager, 'get_connection', return_value=mock_client) as _:
        yield mock_client

    PIConnectionManager._client = None


@pytest.fixture
def mock_cloudwatch_client():
    """Fixture providing a mock CloudWatch client for tests.

    Resets the CloudWatch connection before and after the test.
    Returns a mock client that's automatically patched into the CloudwatchConnectionManager.
    """
    CloudwatchConnectionManager._client = None

    mock_client = MagicMock()

    with patch.object(
        CloudwatchConnectionManager, 'get_connection', return_value=mock_client
    ) as _:
        yield mock_client

    CloudwatchConnectionManager._client = None


@pytest.fixture
def mock_all_clients(mock_rds_client, mock_pi_client, mock_cloudwatch_client):
    """Fixture that provides mock clients for all AWS services.

    This is a convenience fixture that combines all individual mock client fixtures.
    Use this when a test needs to interact with multiple AWS services.

    Returns:
        tuple: (mock_rds_client, mock_pi_client, mock_cloudwatch_client)
    """
    return (mock_rds_client, mock_pi_client, mock_cloudwatch_client)


@pytest.fixture
def mock_rds_context_allowed():
    """Mock RDS context to allow operations (readonly_mode returns False)."""
    with patch.object(RDSContext, 'readonly_mode', return_value=False) as mock:
        yield mock


@pytest.fixture
def mock_rds_context_readonly():
    """Mock RDS context to deny operations (readonly_mode returns True)."""
    with patch.object(RDSContext, 'readonly_mode', return_value=True) as mock:
        yield mock


@pytest.fixture
def mock_asyncio_thread():
    """Mock asyncio.to_thread for testing async operations."""
    with patch('asyncio.to_thread') as mock:
        yield mock
