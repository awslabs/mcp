"""Tests for HealthImaging tool handler."""

import json
import pytest
from awslabs.healthimaging_mcp_server.healthimaging_operations import HealthImagingClient
from awslabs.healthimaging_mcp_server.server import ToolHandler
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def mock_healthimaging_client():
    """Create a mock HealthImaging client."""
    client = MagicMock(spec=HealthImagingClient)
    return client


@pytest.fixture
def tool_handler(mock_healthimaging_client):
    """Create a tool handler with mock client."""
    return ToolHandler(mock_healthimaging_client)


@pytest.mark.asyncio
async def test_handle_list_datastores(tool_handler, mock_healthimaging_client, sample_datastore):
    """Test listing datastores."""
    mock_healthimaging_client.list_datastores = AsyncMock(
        return_value={'datastoreSummaries': [sample_datastore]}
    )

    result = await tool_handler.handle_tool('list_datastores', {})

    assert len(result) == 1
    response_data = json.loads(result[0].text)
    assert 'datastoreSummaries' in response_data
    mock_healthimaging_client.list_datastores.assert_called_once_with(filter_status=None)


@pytest.mark.asyncio
async def test_handle_get_datastore(tool_handler, mock_healthimaging_client, sample_datastore):
    """Test getting a specific datastore."""
    mock_healthimaging_client.get_datastore_details = AsyncMock(
        return_value={'datastore': sample_datastore}
    )

    result = await tool_handler.handle_tool(
        'get_datastore_details', {'datastore_id': '12345678901234567890123456789012'}
    )

    assert len(result) == 1
    response_data = json.loads(result[0].text)
    assert 'datastore' in response_data
    mock_healthimaging_client.get_datastore_details.assert_called_once()


@pytest.mark.asyncio
async def test_handle_search_image_sets(tool_handler, mock_healthimaging_client, sample_image_set):
    """Test searching image sets."""
    mock_healthimaging_client.search_image_sets = AsyncMock(
        return_value={'imageSetsMetadataSummaries': [sample_image_set]}
    )

    result = await tool_handler.handle_tool(
        'search_image_sets',
        {'datastore_id': '12345678901234567890123456789012', 'max_results': 50},
    )

    assert len(result) == 1
    response_data = json.loads(result[0].text)
    assert 'imageSetsMetadataSummaries' in response_data
    mock_healthimaging_client.search_image_sets.assert_called_once()


@pytest.mark.asyncio
async def test_handle_get_image_set(tool_handler, mock_healthimaging_client, sample_image_set):
    """Test getting an image set."""
    mock_healthimaging_client.get_image_set = AsyncMock(return_value=sample_image_set)

    result = await tool_handler.handle_tool(
        'get_image_set',
        {
            'datastore_id': '12345678901234567890123456789012',
            'image_set_id': 'abcdef1234567890abcdef1234567890',
        },
    )

    assert len(result) == 1
    response_data = json.loads(result[0].text)
    assert response_data == sample_image_set
    mock_healthimaging_client.get_image_set.assert_called_once()


@pytest.mark.asyncio
async def test_handle_get_image_set_metadata(tool_handler, mock_healthimaging_client):
    """Test getting image set metadata."""
    metadata = '{"Study": {"DICOM": {"StudyInstanceUID": "1.2.3"}}}'
    mock_healthimaging_client.get_image_set_metadata = AsyncMock(return_value=metadata)

    result = await tool_handler.handle_tool(
        'get_image_set_metadata',
        {
            'datastore_id': '12345678901234567890123456789012',
            'image_set_id': 'abcdef1234567890abcdef1234567890',
        },
    )

    assert len(result) == 1
    response_data = json.loads(result[0].text)
    assert response_data == metadata
    mock_healthimaging_client.get_image_set_metadata.assert_called_once()


@pytest.mark.asyncio
async def test_validation_error(tool_handler):
    """Test validation error handling."""
    with pytest.raises(ValueError, match='Unknown tool'):
        await tool_handler.handle_tool('nonexistent_tool', {})
