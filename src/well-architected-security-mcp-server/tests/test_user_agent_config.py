"""Tests for USER_AGENT_CONFIG usage across all modules."""

from unittest import mock

import pytest
from botocore.config import Config

from awslabs.well_architected_security_mcp_server import __version__
from awslabs.well_architected_security_mcp_server.util.network_security import (
    USER_AGENT_CONFIG as NETWORK_USER_AGENT_CONFIG,
)
from awslabs.well_architected_security_mcp_server.util.resource_utils import (
    USER_AGENT_CONFIG as RESOURCE_USER_AGENT_CONFIG,
)
from awslabs.well_architected_security_mcp_server.util.security_services import USER_AGENT_CONFIG
from awslabs.well_architected_security_mcp_server.util.storage_security import (
    USER_AGENT_CONFIG as STORAGE_USER_AGENT_CONFIG,
)


def test_user_agent_config_is_properly_configured():
    """Test that USER_AGENT_CONFIG is properly configured with the correct user agent string."""
    expected_user_agent = f"awslabs/mcp/well-architected-security-mcp-server/{__version__}"

    # Test security_services config
    assert isinstance(USER_AGENT_CONFIG, Config)
    assert USER_AGENT_CONFIG.user_agent_extra == expected_user_agent  # type: ignore[attr-defined]

    # Test storage_security config
    assert isinstance(STORAGE_USER_AGENT_CONFIG, Config)
    assert STORAGE_USER_AGENT_CONFIG.user_agent_extra == expected_user_agent  # type: ignore[attr-defined]

    # Test network_security config
    assert isinstance(NETWORK_USER_AGENT_CONFIG, Config)
    assert NETWORK_USER_AGENT_CONFIG.user_agent_extra == expected_user_agent  # type: ignore[attr-defined]

    # Test resource_utils config
    assert isinstance(RESOURCE_USER_AGENT_CONFIG, Config)
    assert RESOURCE_USER_AGENT_CONFIG.user_agent_extra == expected_user_agent  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_security_services_uses_user_agent_config():
    """Test that security services functions use the USER_AGENT_CONFIG."""
    from awslabs.well_architected_security_mcp_server.util.security_services import (
        check_access_analyzer,
    )

    mock_ctx = mock.AsyncMock()
    mock_session = mock.MagicMock()
    mock_client = mock.MagicMock()
    mock_session.client.return_value = mock_client

    # Mock the response
    mock_client.list_analyzers.return_value = {"analyzers": []}

    # Call the function
    await check_access_analyzer("us-east-1", mock_session, mock_ctx)

    # Verify that the client was created with the config parameter
    mock_session.client.assert_called_with(
        "accessanalyzer", region_name="us-east-1", config=USER_AGENT_CONFIG
    )


@pytest.mark.asyncio
async def test_storage_security_uses_user_agent_config():
    """Test that storage security functions use the USER_AGENT_CONFIG."""
    from awslabs.well_architected_security_mcp_server.util.storage_security import (
        find_storage_resources,
    )

    mock_ctx = mock.AsyncMock()
    mock_session = mock.MagicMock()
    mock_client = mock.MagicMock()
    mock_session.client.return_value = mock_client

    # Mock the response
    mock_client.list_views.return_value = {"Views": []}

    # Call the function
    services = ["s3"]
    await find_storage_resources("us-east-1", mock_session, services, mock_ctx)

    # Verify that the client was created with the config parameter
    mock_session.client.assert_called_with(
        "resource-explorer-2", region_name="us-east-1", config=STORAGE_USER_AGENT_CONFIG
    )


@pytest.mark.asyncio
async def test_network_security_uses_user_agent_config():
    """Test that network security functions use the USER_AGENT_CONFIG."""
    from awslabs.well_architected_security_mcp_server.util.network_security import (
        find_network_resources,
    )

    mock_ctx = mock.AsyncMock()
    mock_session = mock.MagicMock()
    mock_client = mock.MagicMock()
    mock_session.client.return_value = mock_client

    # Mock the response
    mock_client.list_views.return_value = {"Views": []}

    # Call the function
    services = ["elb"]
    await find_network_resources("us-east-1", mock_session, services, mock_ctx)

    # Verify that the client was created with the config parameter
    mock_session.client.assert_called_with(
        "resource-explorer-2", region_name="us-east-1", config=NETWORK_USER_AGENT_CONFIG
    )


@pytest.mark.asyncio
async def test_resource_utils_uses_user_agent_config():
    """Test that resource utils functions use the USER_AGENT_CONFIG."""
    from awslabs.well_architected_security_mcp_server.util.resource_utils import (
        list_services_in_region,
    )

    mock_ctx = mock.AsyncMock()
    mock_session = mock.MagicMock()
    mock_client = mock.MagicMock()
    mock_session.client.return_value = mock_client

    # Mock the response
    mock_client.list_views.return_value = {"Views": []}

    # Call the function
    await list_services_in_region("us-east-1", mock_session, mock_ctx)

    # Verify that the client was created with the config parameter
    mock_session.client.assert_called_with(
        "resource-explorer-2", region_name="us-east-1", config=RESOURCE_USER_AGENT_CONFIG
    )
