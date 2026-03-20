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

"""Browser session management tools for Bedrock AgentCore Browser MCP Server."""

from __future__ import annotations

from awslabs.amazon_bedrock_agentcore_browser_mcp_server.aws_client import (
    get_data_plane_client,
    handle_aws_errors,
)
from loguru import logger


@handle_aws_errors('start browser session')
def start_browser_session(
    browser_identifier: str = 'aws.browser.v1',
    name: str = 'mcp-browser-session',
    session_timeout_seconds: int = 900,
    viewport_width: int = 1456,
    viewport_height: int = 819,
    profile_identifier: str | None = None,
) -> dict:
    """Start a new ephemeral browser session.

    Creates an isolated browser instance and returns WebSocket endpoints for automation
    and live view streaming. Use the automation_endpoint with Playwright or CDP.

    Args:
        browser_identifier: Browser tool ID (default: "aws.browser.v1"). Use a custom ID
            for VPC-bound browsers.
        name: Human-readable session name.
        session_timeout_seconds: Auto-terminate after this many seconds (default: 900, max: 28800).
        viewport_width: Browser viewport width in pixels (default: 1456).
        viewport_height: Browser viewport height in pixels (default: 819).
        profile_identifier: Optional profile ID to restore cookies/storage from a saved profile.

    Returns:
        dict with session_id, browser_identifier, automation_endpoint, live_view_endpoint, created_at.
    """
    client = get_data_plane_client()

    params: dict = {
        'browserIdentifier': browser_identifier,
        'name': name,
        'sessionTimeoutSeconds': session_timeout_seconds,
        'viewPort': {'width': viewport_width, 'height': viewport_height},
    }

    if profile_identifier:
        params['profileConfiguration'] = {'profileIdentifier': profile_identifier}

    logger.info(f'Starting browser session: browser={browser_identifier}, name={name}')
    response = client.start_browser_session(**params)
    streams = response['streams']

    return {
        'session_id': response['sessionId'],
        'browser_identifier': browser_identifier,
        'automation_endpoint': streams['automationStream']['streamEndpoint'],
        'live_view_endpoint': streams['liveViewStream']['streamEndpoint'],
        'created_at': response['createdAt'],
    }


@handle_aws_errors('get browser session')
def get_browser_session(
    session_id: str,
    browser_identifier: str = 'aws.browser.v1',
) -> dict:
    """Get details about an existing browser session.

    Returns status, stream endpoints, viewport config, and timestamps.

    Args:
        session_id: Unique session identifier.
        browser_identifier: Browser tool ID (default: "aws.browser.v1").

    Returns:
        dict with session_id, status, automation_endpoint, live_view_endpoint, viewport, etc.
    """
    client = get_data_plane_client()

    logger.info(f'Getting browser session: session_id={session_id}')
    response = client.get_browser_session(
        browserIdentifier=browser_identifier,
        sessionId=session_id,
    )

    streams = response.get('streams', {})
    viewport = response.get('viewPort', {})

    return {
        'session_id': response['sessionId'],
        'browser_identifier': response['browserIdentifier'],
        'status': response.get('status'),
        'automation_endpoint': streams.get('automationStream', {}).get('streamEndpoint'),
        'live_view_endpoint': streams.get('liveViewStream', {}).get('streamEndpoint'),
        'viewport': {'width': viewport.get('width'), 'height': viewport.get('height')},
        'session_timeout_seconds': response.get('sessionTimeoutSeconds'),
        'created_at': response.get('createdAt'),
        'last_updated_at': response.get('lastUpdatedAt'),
    }


@handle_aws_errors('list browser sessions')
def list_browser_sessions(
    browser_identifier: str = 'aws.browser.v1',
    status: str | None = None,
    max_results: int = 10,
) -> dict:
    """List browser sessions, optionally filtered by status.

    Args:
        browser_identifier: Browser tool ID (default: "aws.browser.v1").
        status: Optional filter (e.g., "READY", "TERMINATED").
        max_results: Maximum sessions to return (default: 10).

    Returns:
        dict with sessions list and next_token for pagination.
    """
    client = get_data_plane_client()

    params: dict = {'browserIdentifier': browser_identifier, 'maxResults': max_results}
    if status:
        params['status'] = status

    logger.info(f'Listing browser sessions: browser={browser_identifier}, status={status}')
    response = client.list_browser_sessions(**params)

    sessions = [
        {
            'session_id': s.get('sessionId'),
            'name': s.get('name'),
            'status': s.get('status'),
            'created_at': s.get('createdAt'),
        }
        for s in response.get('sessionSummaries', [])
    ]

    return {'sessions': sessions, 'next_token': response.get('nextToken')}


@handle_aws_errors('stop browser session')
def stop_browser_session(
    session_id: str,
    browser_identifier: str = 'aws.browser.v1',
) -> dict:
    """Stop an active browser session and release resources.

    Once stopped, a session cannot be restarted. Create a new session instead.

    Args:
        session_id: Unique session identifier.
        browser_identifier: Browser tool ID (default: "aws.browser.v1").

    Returns:
        dict with session_id, browser_identifier, last_updated_at.
    """
    client = get_data_plane_client()

    logger.info(f'Stopping browser session: session_id={session_id}')
    response = client.stop_browser_session(
        browserIdentifier=browser_identifier,
        sessionId=session_id,
    )

    return {
        'session_id': response['sessionId'],
        'browser_identifier': response['browserIdentifier'],
        'last_updated_at': response['lastUpdatedAt'],
    }
