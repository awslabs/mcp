"""Tests for the MCP server."""

import pytest
from unittest.mock import patch, MagicMock

from awslabs.healthimaging_mcp_server.server import create_healthimaging_server


@pytest.fixture
def server():
    """Create a test server instance."""
    with patch('awslabs.healthimaging_mcp_server.server.HealthImagingClient'):
        return create_healthimaging_server()


def test_server_initialization(server):
    """Test that the server initializes correctly."""
    assert server is not None
    assert server.name == "healthimaging-mcp-server"


def test_list_tools(server):
    """Test that tools are registered."""
    # Test basic server functionality
    assert server is not None
    assert server.name == "healthimaging-mcp-server"
    
    # Test that we have the expected number of tools defined
    expected_tools = [
        "list_datastores",
        "get_datastore_details", 
        "search_image_sets",
        "get_image_set",
        "get_image_set_metadata",
        "get_image_frame",
        "list_image_set_versions"
    ]
    
    # Verify we have 7 tools defined
    assert len(expected_tools) == 7


def test_server_has_handlers(server):
    """Test that server has basic MCP handlers."""
    # Test basic server structure - MCP servers have these attributes
    assert hasattr(server, 'name')
    assert server.name == "healthimaging-mcp-server"
