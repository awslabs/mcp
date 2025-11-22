"""Tests for DSQL knowledge server proxy tools."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from awslabs.aurora_dsql_mcp_server.server import (
    dsql_search_documentation,
    dsql_read_documentation,
    dsql_recommend,
    _proxy_to_knowledge_server,
)


@pytest.fixture
def mock_ctx():
    """Create a mock context."""
    ctx = MagicMock()
    ctx.error = AsyncMock()
    return ctx


@pytest.mark.asyncio
async def test_proxy_to_knowledge_server_success(mock_ctx):
    """Test successful proxy request."""
    with patch('httpx.AsyncClient') as mock_client:
        mock_response = MagicMock()
        mock_response.json.return_value = {'result': {'data': 'test'}}
        mock_response.raise_for_status = MagicMock()

        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            return_value=mock_response
        )

        result = await _proxy_to_knowledge_server('test_method', {'param': 'value'}, mock_ctx)

        assert result == {'data': 'test'}


@pytest.mark.asyncio
async def test_proxy_to_knowledge_server_uses_timeout(mock_ctx):
    """Test that proxy uses configured timeout."""
    import awslabs.aurora_dsql_mcp_server.server as server_module

    # Set custom timeout
    original_timeout = server_module.knowledge_timeout
    server_module.knowledge_timeout = 60.0

    try:
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = {'result': {'data': 'test'}}
            mock_response.raise_for_status = MagicMock()

            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            await _proxy_to_knowledge_server('test_method', {'param': 'value'}, mock_ctx)

            # Verify AsyncClient was called with custom timeout
            mock_client.assert_called_once_with(timeout=60.0)
    finally:
        # Restore original timeout
        server_module.knowledge_timeout = original_timeout


@pytest.mark.asyncio
async def test_proxy_to_knowledge_server_error(mock_ctx):
    """Test proxy request with server error."""
    with patch('httpx.AsyncClient') as mock_client:
        mock_response = MagicMock()
        mock_response.json.return_value = {'error': {'message': 'Server error'}}
        mock_response.raise_for_status = MagicMock()

        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            return_value=mock_response
        )

        with pytest.raises(Exception, match='Server error'):
            await _proxy_to_knowledge_server('test_method', {'param': 'value'}, mock_ctx)


@pytest.mark.asyncio
async def test_proxy_to_knowledge_server_unavailable(mock_ctx):
    """Test proxy request when server is unavailable."""
    import httpx

    with patch('httpx.AsyncClient') as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            side_effect=httpx.HTTPError('Connection failed')
        )

        with pytest.raises(Exception, match='currently unavailable'):
            await _proxy_to_knowledge_server('test_method', {'param': 'value'}, mock_ctx)


@pytest.mark.asyncio
async def test_dsql_search_documentation(mock_ctx):
    """Test dsql_search_documentation tool."""
    with patch('awslabs.aurora_dsql_mcp_server.server._proxy_to_knowledge_server') as mock_proxy:
        mock_proxy.return_value = {'results': []}

        result = await dsql_search_documentation('test query', None, mock_ctx)

        mock_proxy.assert_called_once_with(
            'dsql_search_documentation',
            {'search_phrase': 'test query'},
            mock_ctx
        )
        assert result == {'results': []}


@pytest.mark.asyncio
async def test_dsql_search_documentation_with_limit(mock_ctx):
    """Test dsql_search_documentation tool with limit parameter."""
    with patch('awslabs.aurora_dsql_mcp_server.server._proxy_to_knowledge_server') as mock_proxy:
        mock_proxy.return_value = {'results': []}

        result = await dsql_search_documentation('test query', 10, mock_ctx)

        mock_proxy.assert_called_once_with(
            'dsql_search_documentation',
            {'search_phrase': 'test query', 'limit': 10},
            mock_ctx
        )
        assert result == {'results': []}


@pytest.mark.asyncio
async def test_dsql_read_documentation(mock_ctx):
    """Test dsql_read_documentation tool."""
    with patch('awslabs.aurora_dsql_mcp_server.server._proxy_to_knowledge_server') as mock_proxy:
        mock_proxy.return_value = {'content': 'doc content'}

        result = await dsql_read_documentation('getting-started', None, None, mock_ctx)

        mock_proxy.assert_called_once_with(
            'dsql_read_documentation',
            {'url': 'getting-started'},
            mock_ctx
        )
        assert result == {'content': 'doc content'}


@pytest.mark.asyncio
async def test_dsql_read_documentation_with_start_index(mock_ctx):
    """Test dsql_read_documentation tool with start_index parameter."""
    with patch('awslabs.aurora_dsql_mcp_server.server._proxy_to_knowledge_server') as mock_proxy:
        mock_proxy.return_value = {'content': 'doc content'}

        result = await dsql_read_documentation('getting-started', 100, None, mock_ctx)

        mock_proxy.assert_called_once_with(
            'dsql_read_documentation',
            {'url': 'getting-started', 'start_index': 100},
            mock_ctx
        )
        assert result == {'content': 'doc content'}


@pytest.mark.asyncio
async def test_dsql_read_documentation_with_max_length(mock_ctx):
    """Test dsql_read_documentation tool with max_length parameter."""
    with patch('awslabs.aurora_dsql_mcp_server.server._proxy_to_knowledge_server') as mock_proxy:
        mock_proxy.return_value = {'content': 'doc content'}

        result = await dsql_read_documentation('getting-started', None, 500, mock_ctx)

        mock_proxy.assert_called_once_with(
            'dsql_read_documentation',
            {'url': 'getting-started', 'max_length': 500},
            mock_ctx
        )
        assert result == {'content': 'doc content'}


@pytest.mark.asyncio
async def test_dsql_read_documentation_with_all_parameters(mock_ctx):
    """Test dsql_read_documentation tool with all optional parameters."""
    with patch('awslabs.aurora_dsql_mcp_server.server._proxy_to_knowledge_server') as mock_proxy:
        mock_proxy.return_value = {'content': 'doc content'}

        result = await dsql_read_documentation('getting-started', 100, 500, mock_ctx)

        mock_proxy.assert_called_once_with(
            'dsql_read_documentation',
            {'url': 'getting-started', 'start_index': 100, 'max_length': 500},
            mock_ctx
        )
        assert result == {'content': 'doc content'}


@pytest.mark.asyncio
async def test_dsql_recommend(mock_ctx):
    """Test dsql_recommend tool."""
    with patch('awslabs.aurora_dsql_mcp_server.server._proxy_to_knowledge_server') as mock_proxy:
        mock_proxy.return_value = {'recommendations': []}

        result = await dsql_recommend('best practices', mock_ctx)

        mock_proxy.assert_called_once_with(
            'dsql_recommend',
            {'url': 'best practices'},
            mock_ctx
        )
        assert result == {'recommendations': []}


@pytest.mark.asyncio
async def test_proxy_uses_configured_server_endpoint(mock_ctx):
    """Test that proxy uses the configured knowledge server endpoint."""
    import awslabs.aurora_dsql_mcp_server.server as server_module

    # Set custom server
    original_server = server_module.knowledge_server
    server_module.knowledge_server = 'https://custom.example.com'

    try:
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = {'result': {'data': 'test'}}
            mock_response.raise_for_status = MagicMock()

            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            await _proxy_to_knowledge_server('test_method', {'param': 'value'}, mock_ctx)

            # Verify the custom server was used
            post_call = mock_client.return_value.__aenter__.return_value.post
            post_call.assert_called_once()
            assert post_call.call_args[0][0] == 'https://custom.example.com'
    finally:
        # Restore original server
        server_module.knowledge_server = original_server
