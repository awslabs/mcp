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

"""Tests for browser session profile management tools."""

from awslabs.amazon_bedrock_agentcore_browser_mcp_server.tools.profiles import (
    save_browser_session_profile,
)
from unittest.mock import patch


class TestSaveBrowserSessionProfile:
    """Test cases for save_browser_session_profile."""

    @patch(
        'awslabs.amazon_bedrock_agentcore_browser_mcp_server.tools.profiles.get_data_plane_client'
    )
    def test_save_browser_session_profile_happy_path(
        self, mock_get_client, mock_save_browser_session_profile_response
    ):
        """Test successful profile save."""
        mock_client = mock_get_client.return_value
        mock_client.save_browser_session_profile.return_value = (
            mock_save_browser_session_profile_response
        )

        result = save_browser_session_profile(
            profile_identifier='test-profile', session_id='test-session-123'
        )

        assert result['profile_identifier'] == 'test-profile'
        assert result['browser_identifier'] == 'aws.browser.v1'
        assert result['session_id'] == 'test-session-123'
        assert result['last_updated_at'] == '2024-01-01T00:10:00Z'
        assert 'error' not in result

        mock_client.save_browser_session_profile.assert_called_once_with(
            profileIdentifier='test-profile',
            browserIdentifier='aws.browser.v1',
            sessionId='test-session-123',
        )

    @patch(
        'awslabs.amazon_bedrock_agentcore_browser_mcp_server.tools.profiles.get_data_plane_client'
    )
    def test_save_browser_session_profile_resource_not_found(
        self, mock_get_client, client_error_resource_not_found
    ):
        """Test save profile with ResourceNotFoundException."""
        mock_client = mock_get_client.return_value
        mock_client.save_browser_session_profile.side_effect = client_error_resource_not_found

        result = save_browser_session_profile(
            profile_identifier='test-profile', session_id='nonexistent-session'
        )

        assert result['error'] == 'ResourceNotFoundException'
        assert result['message'] == 'Session not found'
        assert 'profile_identifier' not in result

    @patch(
        'awslabs.amazon_bedrock_agentcore_browser_mcp_server.tools.profiles.get_data_plane_client'
    )
    def test_save_browser_session_profile_access_denied(
        self, mock_get_client, client_error_access_denied
    ):
        """Test save profile with AccessDeniedException."""
        mock_client = mock_get_client.return_value
        mock_client.save_browser_session_profile.side_effect = client_error_access_denied

        result = save_browser_session_profile(
            profile_identifier='test-profile', session_id='test-session-123'
        )

        assert result['error'] == 'AccessDeniedException'
        assert result['message'] == 'Access denied to resource'

    @patch(
        'awslabs.amazon_bedrock_agentcore_browser_mcp_server.tools.profiles.get_data_plane_client'
    )
    def test_save_browser_session_profile_unexpected_error(self, mock_get_client):
        """Test save profile with unexpected exception."""
        mock_client = mock_get_client.return_value
        mock_client.save_browser_session_profile.side_effect = MemoryError('Out of memory')

        result = save_browser_session_profile(
            profile_identifier='test-profile', session_id='test-session-123'
        )

        assert result['error'] == 'UnexpectedError'
        assert 'message' in result
