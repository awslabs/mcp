"""Tests for ToolHandler dispatch logic."""

import pytest
from awslabs.healthlake_mcp_server.server import ToolHandler
from unittest.mock import AsyncMock, Mock


@pytest.fixture
def mock_client():
    """Mock HealthLake client."""
    client = Mock()
    client.list_datastores = AsyncMock(return_value={'DatastorePropertiesList': []})
    client.read_resource = AsyncMock(return_value={'resourceType': 'Patient'})
    client.search_resources = AsyncMock(return_value={'resourceType': 'Bundle'})
    return client


def test_tool_handler_initialization(mock_client):
    """Test ToolHandler initializes with correct handlers."""
    handler = ToolHandler(mock_client)

    assert len(handler.handlers) == 11
    assert 'list_datastores' in handler.handlers
    assert 'search_fhir_resources' in handler.handlers
    assert 'read_fhir_resource' in handler.handlers


@pytest.mark.asyncio
async def test_unknown_tool_raises_error(mock_client):
    """Test unknown tool name raises ValueError."""
    handler = ToolHandler(mock_client)

    with pytest.raises(ValueError, match='Unknown tool'):
        await handler.handle_tool('nonexistent_tool', {})


@pytest.mark.asyncio
async def test_list_datastores_handler(mock_client):
    """Test list_datastores handler calls client correctly."""
    handler = ToolHandler(mock_client)

    result = await handler.handle_tool('list_datastores', {})

    mock_client.list_datastores.assert_called_once_with(filter_status=None)
    assert len(result) == 1  # Returns TextContent list


@pytest.mark.asyncio
async def test_read_handler_with_validation(mock_client, sample_args):
    """Test read handler validates datastore ID."""
    handler = ToolHandler(mock_client)

    result = await handler.handle_tool('read_fhir_resource', sample_args)

    mock_client.read_resource.assert_called_once()
    assert len(result) == 1


@pytest.mark.asyncio
async def test_search_handler_with_count_validation(mock_client, sample_datastore_id):
    """Test search handler validates count parameter."""
    handler = ToolHandler(mock_client)
    args = {'datastore_id': sample_datastore_id, 'resource_type': 'Patient', 'count': 50}

    result = await handler.handle_tool('search_fhir_resources', args)

    mock_client.search_resources.assert_called_once()
    assert len(result) == 1
