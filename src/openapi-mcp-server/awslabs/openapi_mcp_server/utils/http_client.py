# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""HTTP client utilities for the OpenAPI MCP Server.

This module provides enhanced HTTP client functionality with retry logic
and other improvements. It can use different backends based on configuration.
"""

import asyncio
import httpx
from awslabs.openapi_mcp_server import logger
from awslabs.openapi_mcp_server.utils.config import (
    HTTP_MAX_CONNECTIONS,
    HTTP_MAX_KEEPALIVE,
    USE_TENACITY,
)
from awslabs.openapi_mcp_server.utils.metrics_provider import api_call_timer
from typing import Any, Dict, Optional, Union


# Try to import tenacity if enabled
TENACITY_AVAILABLE = False
tenacity = None
if USE_TENACITY:
    try:
        import tenacity

        TENACITY_AVAILABLE = True
        logger.info('tenacity retry logic enabled')
    except ImportError:
        logger.warning('tenacity requested but not installed. Install with: pip install tenacity')


class HttpClientFactory:
    """Factory for creating HTTP clients with enhanced functionality."""

    @staticmethod
    def create_client(
        base_url: str,
        headers: Optional[Dict[str, str]] = None,
        auth: Optional[httpx.Auth] = None,
        cookies: Optional[Dict[str, str]] = None,
        timeout: Union[float, httpx.Timeout] = 30.0,
        follow_redirects: bool = True,
        max_connections: Optional[int] = None,
        max_keepalive: Optional[int] = None,
    ) -> httpx.AsyncClient:
        """Create an HTTP client with enhanced functionality.

        Args:
            base_url: Base URL for the client
            headers: Optional headers to include in requests
            auth: Optional authentication to use
            cookies: Optional cookies to include in requests
            timeout: Request timeout in seconds
            follow_redirects: Whether to follow redirects
            max_connections: Maximum number of connections (defaults to config value)
            max_keepalive: Maximum number of keepalive connections (defaults to config value)

        Returns:
            httpx.AsyncClient: The HTTP client

        """
        # Use configuration values if not explicitly provided
        max_connections = max_connections if max_connections is not None else HTTP_MAX_CONNECTIONS
        max_keepalive = max_keepalive if max_keepalive is not None else HTTP_MAX_KEEPALIVE

        # Log detailed auth information
        if auth:
            auth_type = type(auth).__name__
            has_session_manager = hasattr(auth, 'session_manager') if auth else False

            logger.debug(f'Creating HTTP client with auth type: {auth_type}')

            # For CognitoAuth, verify the session manager and token
            if has_session_manager and hasattr(auth, 'session_manager'):
                session_manager = getattr(auth, 'session_manager')
                is_authenticated = (
                    session_manager.is_authenticated()
                    if hasattr(session_manager, 'is_authenticated')
                    else False
                )
                logger.debug(f'Auth has session_manager, authenticated: {is_authenticated}')

                # Try to get and log the token
                if hasattr(session_manager, 'get_access_token'):
                    token = session_manager.get_access_token()
                    has_token = token is not None
                    logger.debug(f'Session manager has access token: {has_token}')

                    if token:
                        # Mask token for security
                        masked_token = (
                            token[:10] + '...' + token[-10:] if len(token) > 30 else token
                        )
                        logger.debug(f'Access token from session manager: {masked_token}')

                        # Add token to default headers if not already there
                        if headers is None:
                            headers = {}

                        # Only add if not already in headers
                        if 'Authorization' not in headers:
                            headers['Authorization'] = f'Bearer {token}'
                            logger.debug('Added Authorization header from session token')

        # Log the final headers that will be used (safely)
        if headers:
            safe_headers = {}
            for key, value in headers.items():
                if key.lower() == 'authorization' and value:
                    if isinstance(value, str) and value.startswith('Bearer '):
                        token_part = value[7:]
                        masked_token = (
                            token_part[:10] + '...' + token_part[-10:]
                            if len(token_part) > 30
                            else token_part
                        )
                        safe_headers[key] = f'Bearer {masked_token}'
                    else:
                        safe_headers[key] = '[MASKED]'
                else:
                    safe_headers[key] = value
            logger.debug(f'Creating client with headers: {safe_headers}')

        # Create client with connection pooling
        client = httpx.AsyncClient(
            base_url=base_url,
            headers=headers,
            auth=auth,
            cookies=cookies,
            timeout=timeout if isinstance(timeout, httpx.Timeout) else httpx.Timeout(timeout),
            follow_redirects=follow_redirects,
            limits=httpx.Limits(
                max_connections=max_connections,
                max_keepalive_connections=max_keepalive,
            ),
        )

        logger.info(
            f'Created HTTP client for {base_url} with max_connections={max_connections}, '
            f'max_keepalive={max_keepalive}'
        )

        # Verify client has auth after creation
        client_has_auth = hasattr(client, 'auth') and client.auth is not None
        logger.debug(f'Created client has auth: {client_has_auth}')
        if client_has_auth:
            logger.debug(f'Client auth type: {type(client.auth).__name__}')

        return client


async def make_request_with_retry(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    max_retries: int = 3,
    retry_delay: float = 1.0,
    **kwargs: Any,
) -> httpx.Response:
    """Make an HTTP request with retry logic.

    Args:
        client: The HTTP client
        method: HTTP method
        url: URL to request
        max_retries: Maximum number of retries
        retry_delay: Base delay between retries in seconds
        **kwargs: Additional arguments to pass to the request

    Returns:
        httpx.Response: The HTTP response

    Raises:
        httpx.HTTPError: If the request fails after all retries

    """
    # Use tenacity if available and enabled
    if USE_TENACITY and TENACITY_AVAILABLE and tenacity is not None:

        @tenacity.retry(
            stop=tenacity.stop_after_attempt(max_retries),
            wait=tenacity.wait_exponential(
                multiplier=retry_delay, min=retry_delay, max=retry_delay * 10
            ),
            retry=tenacity.retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
            before_sleep=lambda retry_state: logger.warning(
                f'Request failed, retrying ({retry_state.attempt_number}/{max_retries}): {retry_state.outcome.exception() if retry_state.outcome else "Unknown error"}'
            ),
        )
        @api_call_timer
        async def _make_request():
            response = await client.request(method, url, **kwargs)
            response.raise_for_status()
            return response

        return await _make_request()

    # Otherwise, use simple retry logic
    @api_call_timer
    async def _make_request_simple():
        for attempt in range(max_retries):
            try:
                response = await client.request(method, url, **kwargs)
                response.raise_for_status()
                return response
            except (httpx.TimeoutException, httpx.ConnectError) as e:
                if attempt < max_retries - 1:
                    delay = retry_delay * (2**attempt)  # Exponential backoff
                    logger.warning(f'Request failed, retrying ({attempt + 1}/{max_retries}): {e}')
                    await asyncio.sleep(delay)
                else:
                    logger.error(f'Request failed after {max_retries} attempts: {e}')
                    raise
            except httpx.HTTPStatusError as e:
                # Don't retry on status errors (4xx, 5xx)
                logger.error(f'Request failed with status {e.response.status_code}: {e}')
                raise

        # This should never be reached
        raise RuntimeError('Unexpected error in retry logic')

    return await _make_request_simple()


# Simple function for making a single request without retries
@api_call_timer
async def make_request(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    **kwargs: Any,
) -> httpx.Response:
    """Make an HTTP request without retry logic.

    Args:
        client: The HTTP client
        method: HTTP method
        url: URL to request
        **kwargs: Additional arguments to pass to the request

    Returns:
        httpx.Response: The HTTP response

    Raises:
        httpx.HTTPError: If the request fails

    """
    response = await client.request(method, url, **kwargs)
    response.raise_for_status()
    return response
