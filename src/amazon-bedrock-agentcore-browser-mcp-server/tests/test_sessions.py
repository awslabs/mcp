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

"""Tests for browser session management tools."""

from awslabs.amazon_bedrock_agentcore_browser_mcp_server.tools.sessions import (
    get_automation_headers,
    get_browser_session,
    list_browser_sessions,
    start_browser_session,
    stop_browser_session,
)
from unittest.mock import patch


MOCK_HEADERS = {'Authorization': 'AWS4-HMAC-SHA256 ...', 'X-Amz-Date': '20260320T000000Z'}
SIGN_WS_PATH = (
    'awslabs.amazon_bedrock_agentcore_browser_mcp_server.tools.sessions.sign_websocket_headers'
)


class TestStartBrowserSession:
    """Test cases for start_browser_session."""

    @patch(SIGN_WS_PATH, return_value=MOCK_HEADERS)
    @patch(
        'awslabs.amazon_bedrock_agentcore_browser_mcp_server.tools.sessions.get_data_plane_client'
    )
    def test_start_browser_session_happy_path(
        self, mock_get_client, mock_sign, mock_start_browser_session_response
    ):
        """Test successful browser session start."""
        mock_client = mock_get_client.return_value
        mock_client.start_browser_session.return_value = mock_start_browser_session_response

        result = start_browser_session()

        assert result['session_id'] == 'test-session-123'
        assert result['browser_identifier'] == 'aws.browser.v1'
        assert result['automation_endpoint'] == 'wss://automation.example.com/session-123'
        assert result['automation_headers'] == MOCK_HEADERS
        assert result['live_view_endpoint'] == 'wss://liveview.example.com/session-123'
        assert result['created_at'] == '2024-01-01T00:00:00Z'
        assert 'error' not in result

        mock_client.start_browser_session.assert_called_once()
        call_args = mock_client.start_browser_session.call_args[1]
        assert call_args['browserIdentifier'] == 'aws.browser.v1'
        assert call_args['name'] == 'mcp-browser-session'
        assert 'profileConfiguration' not in call_args

    @patch(SIGN_WS_PATH, return_value=MOCK_HEADERS)
    @patch(
        'awslabs.amazon_bedrock_agentcore_browser_mcp_server.tools.sessions.get_data_plane_client'
    )
    def test_start_browser_session_with_profile(
        self, mock_get_client, mock_sign, mock_start_browser_session_response
    ):
        """Test starting session with profile identifier."""
        mock_client = mock_get_client.return_value
        mock_client.start_browser_session.return_value = mock_start_browser_session_response

        result = start_browser_session(profile_identifier='my-profile')

        assert result['session_id'] == 'test-session-123'
        assert 'error' not in result

        call_args = mock_client.start_browser_session.call_args[1]
        assert 'profileConfiguration' in call_args
        assert call_args['profileConfiguration']['profileIdentifier'] == 'my-profile'

    @patch(
        'awslabs.amazon_bedrock_agentcore_browser_mcp_server.tools.sessions.get_data_plane_client'
    )
    def test_start_browser_session_resource_not_found(
        self, mock_get_client, client_error_resource_not_found
    ):
        """Test start session with ResourceNotFoundException."""
        mock_client = mock_get_client.return_value
        mock_client.start_browser_session.side_effect = client_error_resource_not_found

        result = start_browser_session()

        assert result['error'] == 'ResourceNotFoundException'
        assert result['message'] == 'Session not found'
        assert 'session_id' not in result

    @patch(
        'awslabs.amazon_bedrock_agentcore_browser_mcp_server.tools.sessions.get_data_plane_client'
    )
    def test_start_browser_session_access_denied(
        self, mock_get_client, client_error_access_denied
    ):
        """Test start session with AccessDeniedException."""
        mock_client = mock_get_client.return_value
        mock_client.start_browser_session.side_effect = client_error_access_denied

        result = start_browser_session()

        assert result['error'] == 'AccessDeniedException'
        assert result['message'] == 'Access denied to resource'
        assert 'session_id' not in result

    @patch(
        'awslabs.amazon_bedrock_agentcore_browser_mcp_server.tools.sessions.get_data_plane_client'
    )
    def test_start_browser_session_unexpected_error(self, mock_get_client):
        """Test start session with unexpected exception."""
        mock_client = mock_get_client.return_value
        mock_client.start_browser_session.side_effect = ValueError('Unexpected error')

        result = start_browser_session()

        assert result['error'] == 'UnexpectedError'
        assert result['message'] == 'Unexpected error'
        assert 'session_id' not in result

    @patch(SIGN_WS_PATH, side_effect=RuntimeError('No credentials'))
    @patch(
        'awslabs.amazon_bedrock_agentcore_browser_mcp_server.tools.sessions.get_data_plane_client'
    )
    def test_start_browser_session_signing_failure(
        self, mock_get_client, mock_sign, mock_start_browser_session_response
    ):
        """Test that session starts successfully even when SigV4 signing fails."""
        mock_client = mock_get_client.return_value
        mock_client.start_browser_session.return_value = mock_start_browser_session_response

        result = start_browser_session()

        assert result['session_id'] == 'test-session-123'
        assert result['automation_headers'] == {}  # Empty due to signing failure
        assert 'error' not in result


class TestGetBrowserSession:
    """Test cases for get_browser_session."""

    @patch(SIGN_WS_PATH, return_value=MOCK_HEADERS)
    @patch(
        'awslabs.amazon_bedrock_agentcore_browser_mcp_server.tools.sessions.get_data_plane_client'
    )
    def test_get_browser_session_happy_path(
        self, mock_get_client, mock_sign, mock_get_browser_session_response
    ):
        """Test successful session retrieval."""
        mock_client = mock_get_client.return_value
        mock_client.get_browser_session.return_value = mock_get_browser_session_response

        result = get_browser_session('test-session-123')

        assert result['session_id'] == 'test-session-123'
        assert result['browser_identifier'] == 'aws.browser.v1'
        assert result['status'] == 'READY'
        assert result['automation_endpoint'] == 'wss://automation.example.com/session-123'
        assert result['automation_headers'] == MOCK_HEADERS
        assert result['live_view_endpoint'] == 'wss://liveview.example.com/session-123'
        assert result['viewport']['width'] == 1456
        assert result['viewport']['height'] == 819
        assert result['session_timeout_seconds'] == 900
        assert result['created_at'] == '2024-01-01T00:00:00Z'
        assert result['last_updated_at'] == '2024-01-01T00:05:00Z'
        assert 'error' not in result

        mock_client.get_browser_session.assert_called_once_with(
            browserIdentifier='aws.browser.v1', sessionId='test-session-123'
        )

    @patch(
        'awslabs.amazon_bedrock_agentcore_browser_mcp_server.tools.sessions.get_data_plane_client'
    )
    def test_get_browser_session_resource_not_found(
        self, mock_get_client, client_error_resource_not_found
    ):
        """Test get session with ResourceNotFoundException."""
        mock_client = mock_get_client.return_value
        mock_client.get_browser_session.side_effect = client_error_resource_not_found

        result = get_browser_session('nonexistent-session')

        assert result['error'] == 'ResourceNotFoundException'
        assert result['message'] == 'Session not found'
        assert 'session_id' not in result

    @patch(
        'awslabs.amazon_bedrock_agentcore_browser_mcp_server.tools.sessions.get_data_plane_client'
    )
    def test_get_browser_session_access_denied(self, mock_get_client, client_error_access_denied):
        """Test get session with AccessDeniedException."""
        mock_client = mock_get_client.return_value
        mock_client.get_browser_session.side_effect = client_error_access_denied

        result = get_browser_session('test-session-123')

        assert result['error'] == 'AccessDeniedException'
        assert result['message'] == 'Access denied to resource'

    @patch(
        'awslabs.amazon_bedrock_agentcore_browser_mcp_server.tools.sessions.get_data_plane_client'
    )
    def test_get_browser_session_unexpected_error(self, mock_get_client):
        """Test get session with unexpected exception."""
        mock_client = mock_get_client.return_value
        mock_client.get_browser_session.side_effect = RuntimeError('Database error')

        result = get_browser_session('test-session-123')

        assert result['error'] == 'UnexpectedError'
        assert result['message'] == 'Database error'

    @patch(SIGN_WS_PATH, side_effect=RuntimeError('No credentials'))
    @patch(
        'awslabs.amazon_bedrock_agentcore_browser_mcp_server.tools.sessions.get_data_plane_client'
    )
    def test_get_browser_session_signing_failure(
        self, mock_get_client, mock_sign, mock_get_browser_session_response
    ):
        """Test that get session succeeds even when SigV4 signing fails."""
        mock_client = mock_get_client.return_value
        mock_client.get_browser_session.return_value = mock_get_browser_session_response

        result = get_browser_session('test-session-123')

        assert result['session_id'] == 'test-session-123'
        assert result['automation_headers'] == {}  # Empty due to signing failure
        assert 'error' not in result


class TestListBrowserSessions:
    """Test cases for list_browser_sessions."""

    @patch(
        'awslabs.amazon_bedrock_agentcore_browser_mcp_server.tools.sessions.get_data_plane_client'
    )
    def test_list_browser_sessions_happy_path(
        self, mock_get_client, mock_list_browser_sessions_response
    ):
        """Test successful session listing."""
        mock_client = mock_get_client.return_value
        mock_client.list_browser_sessions.return_value = mock_list_browser_sessions_response

        result = list_browser_sessions()

        assert len(result['sessions']) == 2
        assert result['sessions'][0]['session_id'] == 'session-1'
        assert result['sessions'][0]['name'] == 'test-session-1'
        assert result['sessions'][0]['status'] == 'ACTIVE'
        assert result['sessions'][1]['session_id'] == 'session-2'
        assert result['next_token'] == 'next-page-token'
        assert 'error' not in result

        call_args = mock_client.list_browser_sessions.call_args[1]
        assert call_args['browserIdentifier'] == 'aws.browser.v1'
        assert call_args['maxResults'] == 10
        assert 'status' not in call_args

    @patch(
        'awslabs.amazon_bedrock_agentcore_browser_mcp_server.tools.sessions.get_data_plane_client'
    )
    def test_list_browser_sessions_with_status_filter(
        self, mock_get_client, mock_list_browser_sessions_response
    ):
        """Test session listing with status filter."""
        mock_client = mock_get_client.return_value
        mock_client.list_browser_sessions.return_value = mock_list_browser_sessions_response

        result = list_browser_sessions(status='ACTIVE')

        assert len(result['sessions']) == 2
        assert 'error' not in result

        call_args = mock_client.list_browser_sessions.call_args[1]
        assert call_args['status'] == 'ACTIVE'

    @patch(
        'awslabs.amazon_bedrock_agentcore_browser_mcp_server.tools.sessions.get_data_plane_client'
    )
    def test_list_browser_sessions_without_status(
        self, mock_get_client, mock_list_browser_sessions_response
    ):
        """Test session listing without status filter."""
        mock_client = mock_get_client.return_value
        mock_client.list_browser_sessions.return_value = mock_list_browser_sessions_response

        result = list_browser_sessions(status=None)

        assert len(result['sessions']) == 2

        call_args = mock_client.list_browser_sessions.call_args[1]
        assert 'status' not in call_args

    @patch(
        'awslabs.amazon_bedrock_agentcore_browser_mcp_server.tools.sessions.get_data_plane_client'
    )
    def test_list_browser_sessions_resource_not_found(
        self, mock_get_client, client_error_resource_not_found
    ):
        """Test list sessions with ResourceNotFoundException."""
        mock_client = mock_get_client.return_value
        mock_client.list_browser_sessions.side_effect = client_error_resource_not_found

        result = list_browser_sessions()

        assert result['error'] == 'ResourceNotFoundException'
        assert result['message'] == 'Session not found'
        assert 'sessions' not in result

    @patch(
        'awslabs.amazon_bedrock_agentcore_browser_mcp_server.tools.sessions.get_data_plane_client'
    )
    def test_list_browser_sessions_access_denied(
        self, mock_get_client, client_error_access_denied
    ):
        """Test list sessions with AccessDeniedException."""
        mock_client = mock_get_client.return_value
        mock_client.list_browser_sessions.side_effect = client_error_access_denied

        result = list_browser_sessions()

        assert result['error'] == 'AccessDeniedException'
        assert result['message'] == 'Access denied to resource'

    @patch(
        'awslabs.amazon_bedrock_agentcore_browser_mcp_server.tools.sessions.get_data_plane_client'
    )
    def test_list_browser_sessions_unexpected_error(self, mock_get_client):
        """Test list sessions with unexpected exception."""
        mock_client = mock_get_client.return_value
        mock_client.list_browser_sessions.side_effect = KeyError('missing_key')

        result = list_browser_sessions()

        assert result['error'] == 'UnexpectedError'
        assert 'missing_key' in result['message']


class TestStopBrowserSession:
    """Test cases for stop_browser_session."""

    @patch(
        'awslabs.amazon_bedrock_agentcore_browser_mcp_server.tools.sessions.get_data_plane_client'
    )
    def test_stop_browser_session_happy_path(
        self, mock_get_client, mock_stop_browser_session_response
    ):
        """Test successful session stop."""
        mock_client = mock_get_client.return_value
        mock_client.stop_browser_session.return_value = mock_stop_browser_session_response

        result = stop_browser_session('test-session-123')

        assert result['session_id'] == 'test-session-123'
        assert result['browser_identifier'] == 'aws.browser.v1'
        assert result['last_updated_at'] == '2024-01-01T00:10:00Z'
        assert 'error' not in result

        mock_client.stop_browser_session.assert_called_once_with(
            browserIdentifier='aws.browser.v1', sessionId='test-session-123'
        )

    @patch(
        'awslabs.amazon_bedrock_agentcore_browser_mcp_server.tools.sessions.get_data_plane_client'
    )
    def test_stop_browser_session_resource_not_found(
        self, mock_get_client, client_error_resource_not_found
    ):
        """Test stop session with ResourceNotFoundException."""
        mock_client = mock_get_client.return_value
        mock_client.stop_browser_session.side_effect = client_error_resource_not_found

        result = stop_browser_session('nonexistent-session')

        assert result['error'] == 'ResourceNotFoundException'
        assert result['message'] == 'Session not found'
        assert 'session_id' not in result

    @patch(
        'awslabs.amazon_bedrock_agentcore_browser_mcp_server.tools.sessions.get_data_plane_client'
    )
    def test_stop_browser_session_access_denied(self, mock_get_client, client_error_access_denied):
        """Test stop session with AccessDeniedException."""
        mock_client = mock_get_client.return_value
        mock_client.stop_browser_session.side_effect = client_error_access_denied

        result = stop_browser_session('test-session-123')

        assert result['error'] == 'AccessDeniedException'
        assert result['message'] == 'Access denied to resource'

    @patch(
        'awslabs.amazon_bedrock_agentcore_browser_mcp_server.tools.sessions.get_data_plane_client'
    )
    def test_stop_browser_session_unexpected_error(self, mock_get_client):
        """Test stop session with unexpected exception."""
        mock_client = mock_get_client.return_value
        mock_client.stop_browser_session.side_effect = IOError('Network timeout')

        result = stop_browser_session('test-session-123')

        assert result['error'] == 'UnexpectedError'
        assert result['message'] == 'Network timeout'


class TestGetAutomationHeaders:
    """Test cases for get_automation_headers."""

    @patch(SIGN_WS_PATH, return_value=MOCK_HEADERS)
    @patch(
        'awslabs.amazon_bedrock_agentcore_browser_mcp_server.tools.sessions.get_data_plane_client'
    )
    def test_get_automation_headers_happy_path(
        self, mock_get_client, mock_sign, mock_get_browser_session_response
    ):
        """Test successful header generation."""
        mock_client = mock_get_client.return_value
        mock_client.get_browser_session.return_value = mock_get_browser_session_response

        result = get_automation_headers('test-session-123')

        assert result['session_id'] == 'test-session-123'
        assert result['automation_endpoint'] == 'wss://automation.example.com/session-123'
        assert result['automation_headers'] == MOCK_HEADERS
        assert 'error' not in result

    @patch(
        'awslabs.amazon_bedrock_agentcore_browser_mcp_server.tools.sessions.get_data_plane_client'
    )
    def test_get_automation_headers_no_endpoint(self, mock_get_client):
        """Test when session has no automation endpoint."""
        mock_client = mock_get_client.return_value
        mock_client.get_browser_session.return_value = {
            'sessionId': 'test-session-123',
            'browserIdentifier': 'aws.browser.v1',
            'streams': {},
        }

        result = get_automation_headers('test-session-123')

        assert result['error'] == 'NoEndpoint'

    @patch(
        'awslabs.amazon_bedrock_agentcore_browser_mcp_server.tools.sessions.get_data_plane_client'
    )
    def test_get_automation_headers_client_error(
        self, mock_get_client, client_error_resource_not_found
    ):
        """Test with ResourceNotFoundException."""
        mock_client = mock_get_client.return_value
        mock_client.get_browser_session.side_effect = client_error_resource_not_found

        result = get_automation_headers('fake-session')

        assert result['error'] == 'ResourceNotFoundException'
