#!/usr/bin/env python3
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

"""HTTP server entry point using Streamable HTTP transport.

This implements the MCP Streamable HTTP transport as specified at:
https://modelcontextprotocol.io/specification/draft/basic/transports#streamable-http

Key features:
- Single /mcp endpoint supporting GET, POST, and DELETE methods
- Session management with MCP-Session-Id header
- Origin validation for DNS rebinding protection
- SSE streaming for server responses
"""

import argparse
import contextlib
import os
import sys
from collections.abc import AsyncIterator

from loguru import logger
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from mcp.server.transport_security import TransportSecuritySettings
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route
from starlette.types import ASGIApp, Receive, Scope, Send

from .server import ALL_TOOLS, create_healthlake_server


class MCPASGIApp:
    """ASGI wrapper for the MCP session manager.

    This wraps the StreamableHTTPSessionManager to work directly as an ASGI app,
    avoiding conflicts with Starlette's response handling.
    """

    def __init__(self, session_manager: StreamableHTTPSessionManager):
        """Initialize with the session manager."""
        self.session_manager = session_manager

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Handle ASGI requests by delegating to the session manager."""
        await self.session_manager.handle_request(scope, receive, send)


# Configure logging
logger.remove()
logger.add(sys.stderr, level=os.getenv('MCP_LOG_LEVEL', 'INFO'))


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='AWS HealthLake MCP Server (HTTP)')
    parser.add_argument(
        '--readonly',
        action='store_true',
        help='Run server in read-only mode (prevents all mutating operations)',
    )
    parser.add_argument(
        '--host',
        type=str,
        default=os.getenv('MCP_HOST', '0.0.0.0'),
        help='Host to bind to (default: 0.0.0.0)',
    )
    parser.add_argument(
        '--port',
        type=int,
        default=int(os.getenv('MCP_PORT', '8080')),
        help='Port to bind to (default: 8080)',
    )
    parser.add_argument(
        '--stateless',
        action='store_true',
        help='Run in stateless mode (no session tracking between requests)',
    )
    parser.add_argument(
        '--allowed-origins',
        type=str,
        default=os.getenv('MCP_ALLOWED_ORIGINS', ''),
        help='Comma-separated list of allowed origins for CORS (empty = allow all)',
    )
    parser.add_argument(
        '--allowed-tools',
        type=str,
        default=os.getenv('MCP_ALLOWED_TOOLS', ''),
        help=f'Comma-separated list of tools to expose. Available: {", ".join(sorted(ALL_TOOLS))}',
    )
    return parser.parse_args()


def create_app(
    read_only: bool = False,
    stateless: bool = False,
    allowed_origins: list[str] | None = None,
    allowed_tools: set[str] | None = None,
) -> Starlette:
    """Create the Starlette application with Streamable HTTP transport.

    Args:
        read_only: If True, only read operations are allowed
        stateless: If True, no session tracking between requests
        allowed_origins: List of allowed origins for security validation.
                        If None or empty, origin validation is disabled.
        allowed_tools: Set of specific tool names to expose.
                      If provided, only these tools will be available.

    Returns:
        Configured Starlette application
    """
    # Create the MCP server
    mcp_server = create_healthlake_server(read_only=read_only, allowed_tools=allowed_tools)

    # Configure transport security settings for Origin validation
    # Per spec: "Servers MUST validate the Origin header on all incoming connections
    # to prevent DNS rebinding attacks"
    security_settings = None
    if allowed_origins:
        security_settings = TransportSecuritySettings(
            allowed_origins=allowed_origins,
        )
        logger.info(f'Origin validation enabled for: {allowed_origins}')

    # Create the session manager for Streamable HTTP
    session_manager = StreamableHTTPSessionManager(
        app=mcp_server,
        stateless=stateless,
        json_response=False,  # Use SSE streaming for responses
        security_settings=security_settings,
    )

    # Wrap the session manager as an ASGI app
    mcp_asgi_app = MCPASGIApp(session_manager)

    async def health_check(request: Request) -> JSONResponse:
        """Health check endpoint for Kubernetes probes."""
        return JSONResponse({
            'status': 'healthy',
            'service': 'healthlake-mcp-server',
            'mode': 'read-only' if read_only else 'full-access',
            'transport': 'streamable-http',
        })

    async def readiness_check(request: Request) -> JSONResponse:
        """Readiness check endpoint for Kubernetes probes."""
        return JSONResponse({
            'status': 'ready',
            'service': 'healthlake-mcp-server',
        })

    @contextlib.asynccontextmanager
    async def lifespan(app: Starlette) -> AsyncIterator[None]:
        """Manage the lifecycle of the session manager."""
        async with session_manager.run():
            logger.info('Streamable HTTP session manager started')
            yield
            logger.info('Streamable HTTP session manager stopped')

    # Routes following MCP Streamable HTTP spec:
    # - /mcp: Single endpoint supporting GET, POST, DELETE (mounted as ASGI app)
    # - /health, /ready: Kubernetes probes (not part of MCP spec)
    routes = [
        Route('/health', health_check, methods=['GET']),
        Route('/ready', readiness_check, methods=['GET']),
        # MCP endpoint - mounted as ASGI app to handle responses directly
        # Supports GET, POST, DELETE per spec
        Mount('/mcp', app=mcp_asgi_app),
    ]

    return Starlette(routes=routes, lifespan=lifespan)


def main():
    """Main entry point for HTTP server."""
    import uvicorn

    args = parse_args()

    # Parse allowed origins
    allowed_origins = None
    if args.allowed_origins:
        allowed_origins = [o.strip() for o in args.allowed_origins.split(',') if o.strip()]

    # Parse allowed tools
    allowed_tools = None
    if args.allowed_tools:
        tools = {t.strip() for t in args.allowed_tools.split(',') if t.strip()}
        # Validate tool names
        invalid_tools = tools - ALL_TOOLS
        if invalid_tools:
            logger.error(f'Invalid tool names: {invalid_tools}')
            logger.error(f'Available tools: {sorted(ALL_TOOLS)}')
            sys.exit(1)
        allowed_tools = tools
        logger.info(f'Allowed tools: {sorted(allowed_tools)}')

    # Security warning per spec
    if args.host == '0.0.0.0' and not allowed_origins:
        logger.warning(
            'Server binding to all interfaces (0.0.0.0) without Origin validation. '
            'For production, use --allowed-origins or bind to localhost (127.0.0.1). '
            'See: https://modelcontextprotocol.io/specification/draft/basic/transports#security-warning'
        )

    logger.info(f'Starting HealthLake MCP Server (Streamable HTTP) on {args.host}:{args.port}')
    logger.info(f'MCP endpoint: http://{args.host}:{args.port}/mcp')

    if args.readonly:
        logger.info('Server running in READ-ONLY mode')
    elif not allowed_tools:
        logger.info('Server running in FULL ACCESS mode')

    if args.stateless:
        logger.info('Server running in STATELESS mode')

    app = create_app(
        read_only=args.readonly,
        stateless=args.stateless,
        allowed_origins=allowed_origins,
        allowed_tools=allowed_tools,
    )

    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        log_level=os.getenv('MCP_LOG_LEVEL', 'info').lower(),
    )


if __name__ == '__main__':
    main()
