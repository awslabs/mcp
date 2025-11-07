import pytest
from awslabs.aws_api_mcp_server.middleware.http_header_validation_middleware import (
    HTTPHeaderValidationMiddleware,
)
from fastmcp.exceptions import ClientError
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.parametrize(
    'origin_value,allowed_origins',
    [
        ('example.com', 'example.com'),  # Exact match
        ('example.com:3000', 'example.com'),  # With port
        ('example.com', 'example.com,other.com'),  # Multiple allowed origins
        ('other.com', 'example.com,other.com'),  # Second in list
        ('example.com', '*'),  # Wildcard
        ('any-domain.com', '*'),  # Wildcard allows any
    ],
)
@patch('awslabs.aws_api_mcp_server.middleware.http_header_validation_middleware.get_http_headers')
@pytest.mark.asyncio
async def test_origin_header_validation_passes(
    mock_get_headers: MagicMock,
    origin_value: str,
    allowed_origins: str,
):
    """Test origin header validation passes for allowed origins."""
    mock_get_headers.return_value = {'origin': origin_value}

    middleware = HTTPHeaderValidationMiddleware()
    context = MagicMock()
    call_next = AsyncMock(return_value='success')

    with patch(
        'awslabs.aws_api_mcp_server.middleware.http_header_validation_middleware.ALLOWED_ORIGINS',
        allowed_origins,
    ):
        result = await middleware.on_request(context, call_next)
        assert result == 'success'
        call_next.assert_called_once_with(context)


@pytest.mark.parametrize(
    'origin_value,allowed_origins',
    [
        ('forbidden.com', 'example.com'),  # Not in allowed list
        ('forbidden.com', 'example.com,other.com'),  # Not in multiple allowed
        ('sub.example.com', 'example.com'),  # Subdomain not matched
    ],
)
@patch('awslabs.aws_api_mcp_server.middleware.http_header_validation_middleware.get_http_headers')
@pytest.mark.asyncio
async def test_origin_header_validation_fails(
    mock_get_headers: MagicMock,
    origin_value: str,
    allowed_origins: str,
):
    """Test origin header validation fails for disallowed origins."""
    mock_get_headers.return_value = {'origin': origin_value}

    middleware = HTTPHeaderValidationMiddleware()
    context = MagicMock()
    call_next = AsyncMock(return_value='success')

    with patch(
        'awslabs.aws_api_mcp_server.middleware.http_header_validation_middleware.ALLOWED_ORIGINS',
        allowed_origins,
    ):
        with pytest.raises(ClientError, match='Origin header validation failed'):
            await middleware.on_request(context, call_next)
        call_next.assert_not_called()


@pytest.mark.parametrize(
    'host_value,allowed_hosts',
    [
        ('example.com', 'example.com'),  # Exact match
        ('example.com:8080', 'example.com'),  # With port
        ('example.com', 'example.com,other.com'),  # Multiple allowed hosts
        ('other.com', 'example.com,other.com'),  # Second in list
        ('example.com', '*'),  # Wildcard
        ('any-domain.com', '*'),  # Wildcard allows any
        ('127.0.0.1', '127.0.0.1'),  # IP address
        ('localhost:3000', 'localhost'),  # localhost with port
    ],
)
@patch('awslabs.aws_api_mcp_server.middleware.http_header_validation_middleware.get_http_headers')
@pytest.mark.asyncio
async def test_host_header_validation_passes(
    mock_get_headers: MagicMock,
    host_value: str,
    allowed_hosts: str,
):
    """Test host header validation passes for allowed hosts."""
    # No origin header, only host
    mock_get_headers.return_value = {'host': host_value}

    middleware = HTTPHeaderValidationMiddleware()
    context = MagicMock()
    call_next = AsyncMock(return_value='success')

    with patch(
        'awslabs.aws_api_mcp_server.middleware.http_header_validation_middleware.ALLOWED_HOSTS',
        allowed_hosts,
    ):
        result = await middleware.on_request(context, call_next)
        assert result == 'success'
        call_next.assert_called_once_with(context)


@pytest.mark.parametrize(
    'host_value,allowed_hosts',
    [
        ('forbidden.com', 'example.com'),  # Not in allowed list
        ('malicious.com', '127.0.0.1'),
        ('other.com:8080', 'example.com'),
        ('forbidden.com', 'example.com,other.com'),  # Not in multiple allowed
        ('sub.example.com', 'example.com'),  # Subdomain not matched
    ],
)
@patch('awslabs.aws_api_mcp_server.middleware.http_header_validation_middleware.get_http_headers')
@pytest.mark.asyncio
async def test_host_header_validation_fails(
    mock_get_headers: MagicMock,
    host_value: str,
    allowed_hosts: str,
):
    """Test host header validation fails for disallowed hosts."""
    # No origin header, only host
    mock_get_headers.return_value = {'host': host_value}

    middleware = HTTPHeaderValidationMiddleware()
    context = MagicMock()
    call_next = AsyncMock(return_value='success')

    with patch(
        'awslabs.aws_api_mcp_server.middleware.http_header_validation_middleware.ALLOWED_HOSTS',
        allowed_hosts,
    ):
        with pytest.raises(ClientError, match='Host header validation failed'):
            await middleware.on_request(context, call_next)
        call_next.assert_not_called()


@patch('awslabs.aws_api_mcp_server.middleware.http_header_validation_middleware.get_http_headers')
@pytest.mark.asyncio
async def test_both_headers_validated_independently(mock_get_headers: MagicMock):
    """Test that both host and origin headers are validated independently."""
    # Both headers present
    mock_get_headers.return_value = {
        'origin': 'example.com',
        'host': 'example.com',
    }

    middleware = HTTPHeaderValidationMiddleware()
    context = MagicMock()
    call_next = AsyncMock(return_value='success')

    with (
        patch(
            'awslabs.aws_api_mcp_server.middleware.http_header_validation_middleware.ALLOWED_ORIGINS',
            'example.com',
        ),
        patch(
            'awslabs.aws_api_mcp_server.middleware.http_header_validation_middleware.ALLOWED_HOSTS',
            'example.com',
        ),
    ):
        # Both should pass validation
        result = await middleware.on_request(context, call_next)
        assert result == 'success'
        call_next.assert_called_once_with(context)


@patch('awslabs.aws_api_mcp_server.middleware.http_header_validation_middleware.get_http_headers')
@pytest.mark.asyncio
async def test_host_fails_validation_when_both_present(mock_get_headers: MagicMock):
    """Test that host validation fails even when origin is valid."""
    # Both headers present, origin valid but host invalid
    mock_get_headers.return_value = {
        'origin': 'example.com',
        'host': 'malicious.com',
    }

    middleware = HTTPHeaderValidationMiddleware()
    context = MagicMock()
    call_next = AsyncMock(return_value='success')

    with (
        patch(
            'awslabs.aws_api_mcp_server.middleware.http_header_validation_middleware.ALLOWED_ORIGINS',
            'example.com',
        ),
        patch(
            'awslabs.aws_api_mcp_server.middleware.http_header_validation_middleware.ALLOWED_HOSTS',
            'example.com',
        ),
    ):
        # Should fail on host validation
        with pytest.raises(ClientError, match='Host header validation failed'):
            await middleware.on_request(context, call_next)
        call_next.assert_not_called()


@patch('awslabs.aws_api_mcp_server.middleware.http_header_validation_middleware.get_http_headers')
@pytest.mark.asyncio
async def test_origin_fails_validation_when_both_present(mock_get_headers: MagicMock):
    """Test that origin validation fails even when host is valid."""
    # Both headers present, host valid but origin invalid
    mock_get_headers.return_value = {
        'origin': 'malicious.com',
        'host': 'example.com',
    }

    middleware = HTTPHeaderValidationMiddleware()
    context = MagicMock()
    call_next = AsyncMock(return_value='success')

    with (
        patch(
            'awslabs.aws_api_mcp_server.middleware.http_header_validation_middleware.ALLOWED_ORIGINS',
            'example.com',
        ),
        patch(
            'awslabs.aws_api_mcp_server.middleware.http_header_validation_middleware.ALLOWED_HOSTS',
            'example.com',
        ),
    ):
        # Should fail on origin validation
        with pytest.raises(ClientError, match='Origin header validation failed'):
            await middleware.on_request(context, call_next)
        call_next.assert_not_called()


@patch('awslabs.aws_api_mcp_server.middleware.http_header_validation_middleware.get_http_headers')
@pytest.mark.asyncio
async def test_no_origin_or_host_headers(mock_get_headers: MagicMock):
    """Test that request passes through when neither origin nor host headers are present."""
    mock_get_headers.return_value = {}

    middleware = HTTPHeaderValidationMiddleware()
    context = MagicMock()
    call_next = AsyncMock(return_value='success')

    result = await middleware.on_request(context, call_next)
    assert result == 'success'
    call_next.assert_called_once_with(context)


@pytest.mark.parametrize(
    'origin_with_port,expected_hostname',
    [
        ('example.com:3000', 'example.com'),
        ('example.com:8080', 'example.com'),
        ('localhost:5000', 'localhost'),
        ('192.168.1.1:8000', '192.168.1.1'),
        ('example.com', 'example.com'),
    ],
)
@patch('awslabs.aws_api_mcp_server.middleware.http_header_validation_middleware.get_http_headers')
@pytest.mark.asyncio
async def test_port_removal_from_origin(
    mock_get_headers: MagicMock,
    origin_with_port: str,
    expected_hostname: str,
):
    """Test that port is correctly removed from origin/host before validation."""
    mock_get_headers.return_value = {'origin': origin_with_port}

    middleware = HTTPHeaderValidationMiddleware()
    context = MagicMock()
    call_next = AsyncMock(return_value='success')

    with patch(
        'awslabs.aws_api_mcp_server.middleware.http_header_validation_middleware.ALLOWED_ORIGINS',
        expected_hostname,
    ):
        result = await middleware.on_request(context, call_next)
        assert result == 'success'
        call_next.assert_called_once_with(context)


@patch('awslabs.aws_api_mcp_server.middleware.http_header_validation_middleware.get_http_headers')
@pytest.mark.asyncio
async def test_empty_allowed_origins(mock_get_headers: MagicMock):
    """Test behavior when ALLOWED_ORIGINS is empty."""
    mock_get_headers.return_value = {'origin': 'example.com'}

    middleware = HTTPHeaderValidationMiddleware()
    context = MagicMock()
    call_next = AsyncMock()

    with patch(
        'awslabs.aws_api_mcp_server.middleware.http_header_validation_middleware.ALLOWED_ORIGINS',
        '',
    ):
        # Should fail validation with empty allowed origins
        with pytest.raises(ClientError, match='Origin header validation failed'):
            await middleware.on_request(context, call_next)
