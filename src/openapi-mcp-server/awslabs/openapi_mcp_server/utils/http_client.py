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
"""HTTP client construction for the OpenAPI MCP Server."""

import httpx
from awslabs.openapi_mcp_server import logger
from awslabs.openapi_mcp_server.utils.config import HTTP_MAX_CONNECTIONS, HTTP_MAX_KEEPALIVE
from typing import Dict, Optional, Union


def create_http_client(
    base_url: str,
    headers: Optional[Dict[str, str]] = None,
    auth: Optional[httpx.Auth] = None,
    cookies: Optional[Dict[str, str]] = None,
    timeout: Union[float, httpx.Timeout] = 30.0,
    follow_redirects: bool = True,
    max_connections: Optional[int] = None,
    max_keepalive: Optional[int] = None,
) -> httpx.AsyncClient:
    """Create an ``httpx.AsyncClient`` for calling the target API.

    This builds the client that ``FastMCP.from_openapi``/``OpenAPIProvider`` use
    to issue requests, wiring up authentication headers/auth/cookies, a request
    timeout, and connection pooling limits.

    Args:
        base_url: Base URL for the client.
        headers: Optional headers to include in requests.
        auth: Optional httpx authentication to use.
        cookies: Optional cookies to include in requests.
        timeout: Request timeout in seconds (or an ``httpx.Timeout``).
        follow_redirects: Whether to follow redirects.
        max_connections: Maximum number of connections (defaults to config value).
        max_keepalive: Maximum number of keepalive connections (defaults to config value).

    Returns:
        httpx.AsyncClient: The configured HTTP client.

    """
    max_connections = max_connections if max_connections is not None else HTTP_MAX_CONNECTIONS
    max_keepalive = max_keepalive if max_keepalive is not None else HTTP_MAX_KEEPALIVE

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

    logger.debug(
        f'Created HTTP client for {base_url} '
        f'(max_connections={max_connections}, max_keepalive={max_keepalive})'
    )
    return client
