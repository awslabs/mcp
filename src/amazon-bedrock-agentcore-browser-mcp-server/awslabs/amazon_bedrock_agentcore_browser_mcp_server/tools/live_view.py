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

"""Browser live view streaming tools."""

from awslabs.amazon_bedrock_agentcore_browser_mcp_server.aws_client import (
    get_data_plane_client,
    handle_aws_errors,
)
from loguru import logger


@handle_aws_errors('open live view')
def open_live_view(
    session_id: str,
    browser_identifier: str = 'aws.browser.v1',
    open_browser: bool = False,
) -> dict:
    """Get live view URL for real-time browser session monitoring.

    Returns an HTTPS URL that shows the browser's current state as a live stream.
    Optionally opens it in your local default browser.

    Args:
        session_id: ID of the active browser session to view.
        browser_identifier: Browser tool ID (default: "aws.browser.v1").
        open_browser: If True, automatically open the URL in the default browser.

    Returns:
        dict with live_view_url, session_id, status, opened_in_browser.
    """
    logger.info(f'Retrieving live view for session: {session_id}')
    client = get_data_plane_client()

    response = client.get_browser_session(
        browserIdentifier=browser_identifier,
        sessionId=session_id,
    )

    session_status = response.get('status')
    if session_status != 'READY':
        return {
            'error': 'SessionNotReady',
            'message': f'Session is not ready for live view. Current status: {session_status}',
        }

    live_view_url = response.get('streams', {}).get('liveViewStream', {}).get('streamEndpoint')
    if not live_view_url:
        return {
            'error': 'LiveViewUnavailable',
            'message': 'Live view stream endpoint not available in session response',
        }

    opened_in_browser = False
    if open_browser:
        import webbrowser

        try:
            webbrowser.open(live_view_url)
            opened_in_browser = True
            logger.info(f'Opened live view in browser: {live_view_url}')
        except Exception as e:
            logger.warning(f'Failed to open browser automatically: {e}')

    return {
        'live_view_url': live_view_url,
        'session_id': session_id,
        'status': session_status,
        'opened_in_browser': opened_in_browser,
    }
