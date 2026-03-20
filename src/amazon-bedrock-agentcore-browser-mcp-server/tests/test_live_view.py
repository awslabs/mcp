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

"""Tests for browser live view streaming tools."""

from awslabs.amazon_bedrock_agentcore_browser_mcp_server.tools.live_view import open_live_view
from unittest.mock import patch


class TestOpenLiveView:
    """Test cases for open_live_view."""

    @patch(
        'awslabs.amazon_bedrock_agentcore_browser_mcp_server.tools.live_view.get_data_plane_client'
    )
    def test_open_live_view_happy_path(self, mock_get_client, mock_get_browser_session_response):
        """Test successful live view URL retrieval."""
        mock_client = mock_get_client.return_value
        mock_client.get_browser_session.return_value = mock_get_browser_session_response

        result = open_live_view('test-session-123')

        assert result['live_view_url'] == 'wss://liveview.example.com/session-123'
        assert result['session_id'] == 'test-session-123'
        assert result['status'] == 'READY'
        assert result['opened_in_browser'] is False
        assert 'error' not in result

        mock_client.get_browser_session.assert_called_once_with(
            browserIdentifier='aws.browser.v1', sessionId='test-session-123'
        )

    @patch('webbrowser.open')
    @patch(
        'awslabs.amazon_bedrock_agentcore_browser_mcp_server.tools.live_view.get_data_plane_client'
    )
    def test_open_live_view_with_open_browser_true(
        self, mock_get_client, mock_webbrowser_open, mock_get_browser_session_response
    ):
        """Test live view with open_browser=True."""
        mock_client = mock_get_client.return_value
        mock_client.get_browser_session.return_value = mock_get_browser_session_response

        result = open_live_view('test-session-123', open_browser=True)

        assert result['live_view_url'] == 'wss://liveview.example.com/session-123'
        assert result['opened_in_browser'] is True
        assert 'error' not in result

        mock_webbrowser_open.assert_called_once_with('wss://liveview.example.com/session-123')

    @patch('webbrowser.open')
    @patch(
        'awslabs.amazon_bedrock_agentcore_browser_mcp_server.tools.live_view.get_data_plane_client'
    )
    def test_open_live_view_with_open_browser_false(
        self, mock_get_client, mock_webbrowser_open, mock_get_browser_session_response
    ):
        """Test live view with open_browser=False."""
        mock_client = mock_get_client.return_value
        mock_client.get_browser_session.return_value = mock_get_browser_session_response

        result = open_live_view('test-session-123', open_browser=False)

        assert result['live_view_url'] == 'wss://liveview.example.com/session-123'
        assert result['opened_in_browser'] is False

        mock_webbrowser_open.assert_not_called()

    @patch('webbrowser.open')
    @patch(
        'awslabs.amazon_bedrock_agentcore_browser_mcp_server.tools.live_view.get_data_plane_client'
    )
    def test_open_live_view_webbrowser_exception(
        self, mock_get_client, mock_webbrowser_open, mock_get_browser_session_response
    ):
        """Test live view when webbrowser.open raises exception."""
        mock_client = mock_get_client.return_value
        mock_client.get_browser_session.return_value = mock_get_browser_session_response
        mock_webbrowser_open.side_effect = OSError('No browser available')

        result = open_live_view('test-session-123', open_browser=True)

        # Should still return success with opened_in_browser=False
        assert result['live_view_url'] == 'wss://liveview.example.com/session-123'
        assert result['opened_in_browser'] is False
        assert 'error' not in result

    @patch(
        'awslabs.amazon_bedrock_agentcore_browser_mcp_server.tools.live_view.get_data_plane_client'
    )
    def test_open_live_view_session_not_ready(
        self, mock_get_client, mock_get_browser_session_response
    ):
        """Test live view when session is not in READY status."""
        mock_response = mock_get_browser_session_response.copy()
        mock_response['status'] = 'STARTING'

        mock_client = mock_get_client.return_value
        mock_client.get_browser_session.return_value = mock_response

        result = open_live_view('test-session-123')

        assert result['error'] == 'SessionNotReady'
        assert 'not ready' in result['message'].lower()
        assert 'STARTING' in result['message']
        assert 'live_view_url' not in result

    @patch(
        'awslabs.amazon_bedrock_agentcore_browser_mcp_server.tools.live_view.get_data_plane_client'
    )
    def test_open_live_view_no_live_view_url(
        self, mock_get_client, mock_get_browser_session_response
    ):
        """Test live view when live view URL is not in response."""
        mock_response = mock_get_browser_session_response.copy()
        mock_response['streams']['liveViewStream'] = {}  # No streamEndpoint

        mock_client = mock_get_client.return_value
        mock_client.get_browser_session.return_value = mock_response

        result = open_live_view('test-session-123')

        assert result['error'] == 'LiveViewUnavailable'
        assert 'not available' in result['message'].lower()
        assert 'live_view_url' not in result

    @patch(
        'awslabs.amazon_bedrock_agentcore_browser_mcp_server.tools.live_view.get_data_plane_client'
    )
    def test_open_live_view_client_error(self, mock_get_client, client_error_resource_not_found):
        """Test live view with ClientError from get_browser_session."""
        mock_client = mock_get_client.return_value
        mock_client.get_browser_session.side_effect = client_error_resource_not_found

        result = open_live_view('nonexistent-session')

        assert result['error'] == 'ResourceNotFoundException'
        assert result['message'] == 'Session not found'
        assert 'live_view_url' not in result

    @patch(
        'awslabs.amazon_bedrock_agentcore_browser_mcp_server.tools.live_view.get_data_plane_client'
    )
    def test_open_live_view_access_denied(self, mock_get_client, client_error_access_denied):
        """Test live view with AccessDeniedException."""
        mock_client = mock_get_client.return_value
        mock_client.get_browser_session.side_effect = client_error_access_denied

        result = open_live_view('test-session-123')

        assert result['error'] == 'AccessDeniedException'
        assert result['message'] == 'Access denied to resource'

    @patch(
        'awslabs.amazon_bedrock_agentcore_browser_mcp_server.tools.live_view.get_data_plane_client'
    )
    def test_open_live_view_unexpected_error(self, mock_get_client):
        """Test live view with unexpected exception."""
        mock_client = mock_get_client.return_value
        mock_client.get_browser_session.side_effect = AttributeError('NoneType error')

        result = open_live_view('test-session-123')

        assert result['error'] == 'UnexpectedError'
        assert 'message' in result
