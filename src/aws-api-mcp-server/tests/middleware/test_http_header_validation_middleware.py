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
        with pytest.raises(ClientError, match='Origin validation failed'):
            await middleware.on_request(context, call_next)
        call_next.assert_not_called()


@pytest.mark.parametrize(
    'host_value,allowed_origins',
    [
        ('example.com', 'example.com'),  # Exact match
        ('example.com:8080', 'example.com'),  # With port
        ('example.com', 'example.com,other.com'),  # Multiple allowed origins
        ('example.com', '*'),  # Wildcard
    ],
)
@patch('awslabs.aws_api_mcp_server.middleware.http_header_validation_middleware.get_http_headers')
@pytest.mark.asyncio
async def test_host_header_validation_passes(
    mock_get_headers: MagicMock,
    host_value: str,
    allowed_origins: str,
):
    """Test host header validation passes when origin is not present."""
    # No origin header, only host
    mock_get_headers.return_value = {'host': host_value}

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
    'host_value,allowed_origins',
    [
        ('forbidden.com', 'example.com'),
    ],
)
@patch('awslabs.aws_api_mcp_server.middleware.http_header_validation_middleware.get_http_headers')
@pytest.mark.asyncio
async def test_host_header_validation_fails(
    mock_get_headers: MagicMock,
    host_value: str,
    allowed_origins: str,
):
    """Test host header validation fails when origin is not present."""
    # No origin header, only host
    mock_get_headers.return_value = {'host': host_value}

    middleware = HTTPHeaderValidationMiddleware()
    context = MagicMock()
    call_next = AsyncMock(return_value='success')

    with patch(
        'awslabs.aws_api_mcp_server.middleware.http_header_validation_middleware.ALLOWED_ORIGINS',
        allowed_origins,
    ):
        with pytest.raises(ClientError, match='Origin validation failed'):
            await middleware.on_request(context, call_next)
        call_next.assert_not_called()


@patch('awslabs.aws_api_mcp_server.middleware.http_header_validation_middleware.get_http_headers')
@pytest.mark.asyncio
async def test_origin_takes_precedence_over_host(mock_get_headers: MagicMock):
    """Test that origin header takes precedence over host header."""
    # Both headers present
    mock_get_headers.return_value = {
        'origin': 'example.com',
        'host': 'other.com',
    }

    middleware = HTTPHeaderValidationMiddleware()
    context = MagicMock()
    call_next = AsyncMock(return_value='success')

    with patch(
        'awslabs.aws_api_mcp_server.middleware.http_header_validation_middleware.ALLOWED_ORIGINS',
        'example.com',
    ):
        # Should use origin (example.com) which is allowed
        result = await middleware.on_request(context, call_next)
        assert result == 'success'
        call_next.assert_called_once_with(context)


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
@patch('awslabs.aws_api_mcp_server.middleware.http_header_validation_middleware.logger')
@pytest.mark.asyncio
async def test_error_logging_on_validation_failure(
    mock_logger: MagicMock,
    mock_get_headers: MagicMock,
):
    """Test that validation failures are logged."""
    mock_get_headers.return_value = {'origin': 'forbidden.com'}

    middleware = HTTPHeaderValidationMiddleware()
    context = MagicMock()
    call_next = AsyncMock()

    with patch(
        'awslabs.aws_api_mcp_server.middleware.http_header_validation_middleware.ALLOWED_ORIGINS',
        'example.com',
    ):
        with pytest.raises(ClientError):
            await middleware.on_request(context, call_next)

    # Verify error was logged
    mock_logger.error.assert_called_once()
    error_msg = mock_logger.error.call_args[0][0]
    assert 'Origin validation failed' in error_msg
    assert 'forbidden.com' in error_msg


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
        with pytest.raises(ClientError, match='Origin validation failed'):
            await middleware.on_request(context, call_next)
