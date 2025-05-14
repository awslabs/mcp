"""Tests for the API discovery module."""

import pytest
from awslabs.openapi_mcp_server.api.discovery import (
    ApiInfo,
    ApiStats,
    ToolInfo,
    get_api_info,
    get_api_stats,
    get_api_tools,
    register_discovery_tools,
)
from unittest.mock import AsyncMock, MagicMock, patch


def test_api_info_model():
    """Test the ApiInfo model."""
    api_info = ApiInfo(
        name='test-api',
        title='Test API',
        version='1.0.0',
        description='Test API description',
        base_url='https://example.com/api',
        paths=10,
        operations=20,
        schemas=5,
    )

    assert api_info.name == 'test-api'
    assert api_info.title == 'Test API'
    assert api_info.version == '1.0.0'
    assert api_info.description == 'Test API description'
    assert api_info.base_url == 'https://example.com/api'
    assert api_info.paths == 10
    assert api_info.operations == 20
    assert api_info.schemas == 5


def test_tool_info_model():
    """Test the ToolInfo model."""
    tool_info = ToolInfo(
        name='test_tool',
        description='Test tool description',
        method='GET',
        path='/test',
        parameters=[{'name': 'param1', 'type': 'string', 'required': True}],
        usage_count=5,
        error_rate=0.1,
        avg_duration_ms=100.0,
    )

    assert tool_info.name == 'test_tool'
    assert tool_info.description == 'Test tool description'
    assert tool_info.method == 'GET'
    assert tool_info.path == '/test'
    assert len(tool_info.parameters) == 1
    assert tool_info.parameters[0]['name'] == 'param1'
    assert tool_info.usage_count == 5
    assert tool_info.error_rate == 0.1
    assert tool_info.avg_duration_ms == 100.0


def test_api_stats_model():
    """Test the ApiStats model."""
    api_stats = ApiStats(
        total_calls=100,
        error_count=10,
        error_rate=0.1,
        unique_paths=5,
        recent_errors=[{'path': '/test', 'status_code': 500}],
    )

    assert api_stats.total_calls == 100
    assert api_stats.error_count == 10
    assert api_stats.error_rate == 0.1
    assert api_stats.unique_paths == 5
    assert len(api_stats.recent_errors) == 1
    assert api_stats.recent_errors[0]['path'] == '/test'


@pytest.mark.asyncio
async def test_get_api_info():
    """Test the get_api_info function."""
    # Create mock OpenAPI spec
    openapi_spec = {
        'info': {
            'title': 'Test API',
            'version': '1.0.0',
            'description': 'Test API description',
        },
        'paths': {
            '/test1': {},
            '/test2': {},
        },
        'components': {
            'schemas': {
                'Schema1': {},
                'Schema2': {},
            }
        },
    }

    # Call the function
    api_info = await get_api_info(
        api_name='test-api',
        openapi_spec=openapi_spec,
        base_url='https://example.com/api',
    )

    # Verify the result
    assert api_info.name == 'test-api'
    assert api_info.title == 'Test API'
    assert api_info.version == '1.0.0'
    assert api_info.description == 'Test API description'
    assert api_info.base_url == 'https://example.com/api'
    assert api_info.paths == 2
    assert api_info.schemas == 2


@pytest.mark.asyncio
async def test_get_api_tools():
    """Test the get_api_tools function."""
    # Create mock server
    server = MagicMock()

    # Create mock tools
    tool1 = MagicMock()
    tool1.name = 'test-api_tool1'
    tool1.description = 'HTTP GET /test1\nTest tool 1 description'

    tool2 = MagicMock()
    tool2.name = 'test-api_tool2'
    tool2.description = 'HTTP POST /test2\nTest tool 2 description'

    # Set up server.get_tools to return our mock tools
    server.get_tools = AsyncMock(
        return_value={
            'test-api_tool1': tool1,
            'test-api_tool2': tool2,
            'other-api_tool': MagicMock(),  # This should be filtered out
        }
    )

    # Mock the metrics
    with patch('awslabs.openapi_mcp_server.api.discovery.metrics') as mock_metrics:
        mock_metrics.get_tool_stats.return_value = {
            'test-api_tool1': {
                'count': 5,
                'error_rate': 0.0,
                'avg_duration_ms': 100.0,
            },
            'test-api_tool2': {
                'count': 10,
                'error_rate': 0.2,
                'avg_duration_ms': 200.0,
            },
        }

        # Call the function
        tools = await get_api_tools(server=server, api_name='test-api')

        # Verify the result
        assert len(tools) == 2

        assert tools[0].name == 'test-api_tool1'
        assert tools[0].method == 'GET'
        assert tools[0].path == '/test1'
        assert tools[0].usage_count == 5
        assert tools[0].error_rate == 0.0
        assert tools[0].avg_duration_ms == 100.0

        assert tools[1].name == 'test-api_tool2'
        assert tools[1].method == 'POST'
        assert tools[1].path == '/test2'
        assert tools[1].usage_count == 10
        assert tools[1].error_rate == 0.2
        assert tools[1].avg_duration_ms == 200.0


@pytest.mark.asyncio
async def test_get_api_stats():
    """Test the get_api_stats function."""
    # Mock the metrics
    with patch('awslabs.openapi_mcp_server.api.discovery.metrics') as mock_metrics:
        mock_metrics.get_summary.return_value = {
            'api_calls': {
                'total': 100,
                'errors': 10,
                'error_rate': 0.1,
                'paths': 5,
            },
            'tool_usage': {
                'total': 50,
                'errors': 5,
                'error_rate': 0.1,
                'tools': 3,
            },
        }

        mock_metrics.get_recent_errors.return_value = [
            {'path': '/test1', 'status_code': 500},
            {'path': '/test2', 'status_code': 404},
        ]

        # Call the function
        stats = await get_api_stats()

        # Verify the result
        assert stats.total_calls == 100
        assert stats.error_count == 10
        assert stats.error_rate == 0.1
        assert stats.unique_paths == 5
        assert len(stats.recent_errors) == 2
        assert stats.recent_errors[0]['path'] == '/test1'
        assert stats.recent_errors[1]['path'] == '/test2'


def test_register_discovery_tools():
    """Test the register_discovery_tools function."""
    # Create mock server
    server = MagicMock()

    # Create mock OpenAPI spec
    openapi_spec = {
        'info': {
            'title': 'Test API',
            'version': '1.0.0',
        },
    }

    # Call the function
    register_discovery_tools(
        server=server,
        api_name='test-api',
        openapi_spec=openapi_spec,
        base_url='https://example.com/api',
    )

    # Verify that tools were registered
    assert server.add_tool.call_count == 3
