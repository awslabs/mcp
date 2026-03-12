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

"""Browser session lifecycle tools wrapping Bedrock AgentCore APIs.

Uses the bedrock-agentcore SDK (BrowserClient) for session management
and SigV4-signed API calls. The SDK handles boto3 client creation,
endpoint resolution, and user-agent tagging.
"""

from .browser_client import get_browser_client
from .connection_manager import (
    BrowserConnectionManager,
)
from .models import (
    BrowserSessionResponse,
    BrowserSessionSummary,
    SessionListResponse,
)
from .snapshot_manager import (
    SnapshotManager,
)
from bedrock_agentcore.tools.config import (
    BrowserExtension,
    ProfileConfiguration,
    ProxyConfiguration,
)
from loguru import logger
from mcp.server.fastmcp import Context
from os import getenv
from pydantic import Field
from typing import Annotated


DEFAULT_BROWSER_IDENTIFIER = getenv('BROWSER_IDENTIFIER', 'aws.browser.v1')


def _to_str(value) -> str:
    """Convert a value to string. Handles boto3 datetime objects."""
    if value is None:
        return ''
    return str(value) if not isinstance(value, str) else value


class BrowserSessionTools:
    """Tools for managing AgentCore Browser sessions."""

    def __init__(
        self,
        connection_manager: BrowserConnectionManager | None = None,
        snapshot_manager: SnapshotManager | None = None,
    ):
        """Initialize with optional connection and snapshot managers."""
        self._connection_manager = connection_manager
        self._snapshot_manager = snapshot_manager

    def register(self, mcp):
        """Register all session tools with the MCP server."""
        mcp.tool(name='start_browser_session')(self.start_browser_session)
        mcp.tool(name='get_browser_session')(self.get_browser_session)
        mcp.tool(name='stop_browser_session')(self.stop_browser_session)
        mcp.tool(name='list_browser_sessions')(self.list_browser_sessions)

    async def start_browser_session(
        self,
        ctx: Context,
        browser_identifier: Annotated[
            str,
            Field(
                description=(
                    'AgentCore browser resource identifier. '
                    'Use "aws.browser.v1" for the default browser.'
                )
            ),
        ] = DEFAULT_BROWSER_IDENTIFIER,
        viewport_width: Annotated[
            int,
            Field(description='Browser viewport width in pixels'),
        ] = 1456,
        viewport_height: Annotated[
            int,
            Field(description='Browser viewport height in pixels'),
        ] = 819,
        timeout_seconds: Annotated[
            int,
            Field(
                description=(
                    'Session idle timeout in seconds — the session expires after this many '
                    'seconds of inactivity (no tool calls). Default 900 (15 min), max 28800 '
                    '(8 hours). Active sessions persist as long as there is interaction '
                    'within each timeout window.'
                )
            ),
        ] = 900,
        proxy_configuration: Annotated[
            ProxyConfiguration | None,
            Field(
                description=(
                    'Proxy configuration for routing browser traffic through external proxy '
                    'servers. Supports multiple proxies with domain-based routing and bypass rules.'
                )
            ),
        ] = None,
        profile_configuration: Annotated[
            ProfileConfiguration | None,
            Field(
                description=(
                    'Profile configuration for persisting cookies and local storage across '
                    'sessions. Pass a profile identifier created via the AgentCore control plane.'
                )
            ),
        ] = None,
        extensions: Annotated[
            list[BrowserExtension] | None,
            Field(
                description='List of browser extensions to load from S3 into the session.',
            ),
        ] = None,
        region: Annotated[
            str,
            Field(description='AWS region for AgentCore APIs'),
        ] = 'us-east-1',
    ) -> BrowserSessionResponse:
        """Start a cloud browser session via Amazon Bedrock AgentCore.

        Creates an isolated browser session running in a Firecracker microVM.
        Returns the session ID and automation stream URL for subsequent browser
        interaction tools.

        Usage:
        1. Call this tool first to start a browser session.
        2. Use the returned session_id with browser interaction tools
           (browser_navigate, browser_click, browser_snapshot, etc.).
        3. Call stop_browser_session when done.
        """
        logger.info(
            f'Starting browser session: browser={browser_identifier}, timeout={timeout_seconds}s'
        )

        try:
            client = get_browser_client(region)

            if not (100 <= viewport_width <= 7680) or not (100 <= viewport_height <= 4320):
                raise ValueError(
                    f'Viewport dimensions out of bounds. '
                    f'Width must be 100-7680, height must be 100-4320. '
                    f'Got {viewport_width}x{viewport_height}.'
                )

            params: dict = {
                'browserIdentifier': browser_identifier,
                'sessionTimeoutSeconds': timeout_seconds,
                'viewPort': {
                    'width': viewport_width,
                    'height': viewport_height,
                },
            }
            if proxy_configuration:
                params['proxyConfiguration'] = proxy_configuration.to_dict()
            if profile_configuration:
                params['profileConfiguration'] = profile_configuration.to_dict()
            if extensions:
                params['extensions'] = [e.to_dict() for e in extensions]

            response = client.data_plane_client.start_browser_session(**params)

            session_id = response.get('sessionId', '')
            streams = response.get('streams', {})
            automation = streams.get('automationStream', {})
            live_view = streams.get('liveViewStream', {})

            logger.info(f'Browser session started: session_id={session_id}')

            # Auto-connect Playwright to the automation stream
            if self._connection_manager and automation.get('streamEndpoint'):
                try:
                    await self._connection_manager.connect(
                        session_id,
                        browser_identifier=browser_identifier,
                        region=region,
                    )
                    logger.info(f'Playwright connected to session {session_id}')
                except Exception as connect_err:
                    logger.error(
                        f'Playwright connect failed for session {session_id}, '
                        f'stopping orphaned session: {connect_err}'
                    )
                    try:
                        client.data_plane_client.stop_browser_session(
                            browserIdentifier=browser_identifier, sessionId=session_id
                        )
                    except Exception as cleanup_err:
                        logger.error(
                            f'Failed to stop orphaned session {session_id}: {cleanup_err}'
                        )
                    raise connect_err

            return BrowserSessionResponse(
                session_id=session_id,
                status='ACTIVE',
                browser_identifier=response.get('browserIdentifier', browser_identifier),
                automation_stream_url=automation.get('streamEndpoint'),
                live_view_url=live_view.get('streamEndpoint'),
                viewport_width=viewport_width,
                viewport_height=viewport_height,
                created_at=_to_str(response.get('createdAt')),
                message=f'Browser session {session_id} started successfully.',
            )

        except Exception as e:
            error_msg = f'Error starting browser session: {e}'
            logger.error(error_msg)
            await ctx.error(error_msg)
            raise

    async def get_browser_session(
        self,
        ctx: Context,
        session_id: Annotated[
            str,
            Field(description='Browser session identifier returned by start_browser_session'),
        ],
        browser_identifier: Annotated[
            str,
            Field(description='AgentCore browser resource identifier'),
        ] = DEFAULT_BROWSER_IDENTIFIER,
        region: Annotated[
            str,
            Field(description='AWS region for AgentCore APIs'),
        ] = 'us-east-1',
    ) -> BrowserSessionResponse:
        """Get the status and metadata of a browser session.

        Returns session status, stream endpoints, viewport dimensions,
        and creation timestamp.
        """
        logger.info(f'Getting browser session: session_id={session_id}')

        try:
            client = get_browser_client(region)
            response = client.get_session(
                browser_id=browser_identifier,
                session_id=session_id,
            )

            streams = response.get('streams', {})
            automation = streams.get('automationStream', {})
            live_view = streams.get('liveViewStream', {})
            viewport = response.get('viewPort', {})

            return BrowserSessionResponse(
                session_id=response.get('sessionId', session_id),
                status=response.get('status', 'UNKNOWN'),
                browser_identifier=response.get('browserIdentifier', browser_identifier),
                automation_stream_url=automation.get('streamEndpoint'),
                live_view_url=live_view.get('streamEndpoint'),
                viewport_width=viewport.get('width'),
                viewport_height=viewport.get('height'),
                created_at=_to_str(response.get('createdAt')),
                message=f'Session {session_id} status: {response.get("status", "UNKNOWN")}',
            )

        except Exception as e:
            error_msg = f'Error getting browser session {session_id}: {e}'
            logger.error(error_msg)
            await ctx.error(error_msg)
            raise

    async def stop_browser_session(
        self,
        ctx: Context,
        session_id: Annotated[
            str,
            Field(description='Browser session identifier to terminate'),
        ],
        browser_identifier: Annotated[
            str,
            Field(description='AgentCore browser resource identifier'),
        ] = DEFAULT_BROWSER_IDENTIFIER,
        region: Annotated[
            str,
            Field(description='AWS region for AgentCore APIs'),
        ] = 'us-east-1',
    ) -> BrowserSessionResponse:
        """Stop a browser session and release resources.

        Terminates the browser session and its underlying microVM.
        The session cannot be resumed after stopping.
        """
        logger.info(f'Stopping browser session: session_id={session_id}')

        try:
            # Disconnect Playwright and clean up snapshot state
            if self._connection_manager:
                await self._connection_manager.disconnect(session_id)
            if self._snapshot_manager:
                self._snapshot_manager.cleanup_session(session_id)

            client = get_browser_client(region)
            client.data_plane_client.stop_browser_session(
                browserIdentifier=browser_identifier,
                sessionId=session_id,
            )

            logger.info(f'Browser session stopped: session_id={session_id}')

            return BrowserSessionResponse(
                session_id=session_id,
                status='TERMINATED',
                browser_identifier=browser_identifier,
                message=f'Browser session {session_id} terminated.',
            )

        except Exception as e:
            error_msg = f'Error stopping browser session {session_id}: {e}'
            logger.error(error_msg)
            await ctx.error(error_msg)
            raise

    async def list_browser_sessions(
        self,
        ctx: Context,
        browser_identifier: Annotated[
            str,
            Field(description='AgentCore browser resource identifier'),
        ] = DEFAULT_BROWSER_IDENTIFIER,
        max_results: Annotated[
            int,
            Field(description='Maximum number of sessions to return'),
        ] = 20,
        region: Annotated[
            str,
            Field(description='AWS region for AgentCore APIs'),
        ] = 'us-east-1',
    ) -> SessionListResponse:
        """List active browser sessions.

        Returns a summary of all browser sessions for the specified
        browser resource, including session IDs, status, and creation times.
        """
        logger.info(f'Listing browser sessions: browser={browser_identifier}')

        try:
            client = get_browser_client(region)
            response = client.list_sessions(
                browser_id=browser_identifier,
                max_results=max_results,
            )

            sessions_data = response.get('items', [])
            sessions = [
                BrowserSessionSummary(
                    session_id=s.get('sessionId', ''),
                    status=s.get('status', 'UNKNOWN'),
                    created_at=_to_str(s.get('createdAt')),
                )
                for s in sessions_data[:max_results]
            ]

            return SessionListResponse(
                sessions=sessions,
                has_more=len(sessions_data) > max_results,
                message=f'Found {len(sessions)} session(s).',
            )

        except Exception as e:
            error_msg = f'Error listing browser sessions: {e}'
            logger.error(error_msg)
            await ctx.error(error_msg)
            raise
