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

"""Tests for browser discovery and management tools."""

from awslabs.amazon_bedrock_agentcore_browser_mcp_server.tools.browsers import (
    get_browser,
    list_browsers,
)
from unittest.mock import patch


class TestListBrowsers:
    """Test cases for list_browsers."""

    @patch(
        'awslabs.amazon_bedrock_agentcore_browser_mcp_server.tools.browsers.get_control_plane_client'
    )
    def test_list_browsers_happy_path(self, mock_get_client, mock_list_browsers_response):
        """Test successful browser listing."""
        mock_client = mock_get_client.return_value
        mock_client.list_browsers.return_value = mock_list_browsers_response

        result = list_browsers()

        assert len(result['browsers']) == 2
        assert result['browsers'][0]['browser_id'] == 'aws.browser.v1'
        assert result['browsers'][0]['name'] == 'AWS Browser v1'
        assert result['browsers'][0]['status'] == 'ACTIVE'
        assert result['browsers'][0]['type'] == 'SYSTEM'
        assert result['browsers'][1]['browser_id'] == 'custom-browser-1'
        assert result['browsers'][1]['type'] == 'CUSTOM'
        assert result['next_token'] == 'next-page-token'
        assert 'error' not in result

        call_args = mock_client.list_browsers.call_args[1]
        assert call_args['maxResults'] == 10
        assert 'type' not in call_args

    @patch(
        'awslabs.amazon_bedrock_agentcore_browser_mcp_server.tools.browsers.get_control_plane_client'
    )
    def test_list_browsers_with_type_filter(self, mock_get_client, mock_list_browsers_response):
        """Test browser listing with browser_type filter."""
        mock_client = mock_get_client.return_value
        mock_client.list_browsers.return_value = mock_list_browsers_response

        result = list_browsers(browser_type='CUSTOM')

        assert len(result['browsers']) == 2
        assert 'error' not in result

        call_args = mock_client.list_browsers.call_args[1]
        assert call_args['type'] == 'CUSTOM'

    @patch(
        'awslabs.amazon_bedrock_agentcore_browser_mcp_server.tools.browsers.get_control_plane_client'
    )
    def test_list_browsers_without_type_filter(self, mock_get_client, mock_list_browsers_response):
        """Test browser listing without type filter."""
        mock_client = mock_get_client.return_value
        mock_client.list_browsers.return_value = mock_list_browsers_response

        result = list_browsers(browser_type=None)

        assert len(result['browsers']) == 2

        call_args = mock_client.list_browsers.call_args[1]
        assert 'type' not in call_args

    @patch(
        'awslabs.amazon_bedrock_agentcore_browser_mcp_server.tools.browsers.get_control_plane_client'
    )
    def test_list_browsers_resource_not_found(
        self, mock_get_client, client_error_resource_not_found
    ):
        """Test list browsers with ResourceNotFoundException."""
        mock_client = mock_get_client.return_value
        mock_client.list_browsers.side_effect = client_error_resource_not_found

        result = list_browsers()

        assert result['error'] == 'ResourceNotFoundException'
        assert result['message'] == 'Session not found'
        assert 'browsers' not in result

    @patch(
        'awslabs.amazon_bedrock_agentcore_browser_mcp_server.tools.browsers.get_control_plane_client'
    )
    def test_list_browsers_access_denied(self, mock_get_client, client_error_access_denied):
        """Test list browsers with AccessDeniedException."""
        mock_client = mock_get_client.return_value
        mock_client.list_browsers.side_effect = client_error_access_denied

        result = list_browsers()

        assert result['error'] == 'AccessDeniedException'
        assert result['message'] == 'Access denied to resource'

    @patch(
        'awslabs.amazon_bedrock_agentcore_browser_mcp_server.tools.browsers.get_control_plane_client'
    )
    def test_list_browsers_unexpected_error(self, mock_get_client):
        """Test list browsers with unexpected exception."""
        mock_client = mock_get_client.return_value
        mock_client.list_browsers.side_effect = TypeError('Invalid type')

        result = list_browsers()

        assert result['error'] == 'UnexpectedError'
        assert 'message' in result


class TestGetBrowser:
    """Test cases for get_browser."""

    @patch(
        'awslabs.amazon_bedrock_agentcore_browser_mcp_server.tools.browsers.get_control_plane_client'
    )
    def test_get_browser_happy_path(self, mock_get_client, mock_get_browser_response):
        """Test successful browser retrieval."""
        mock_client = mock_get_client.return_value
        mock_client.get_browser.return_value = mock_get_browser_response

        result = get_browser('aws.browser.v1')

        assert result['browser_id'] == 'aws.browser.v1'
        assert result['name'] == 'AWS Browser v1'
        assert result['description'] == 'AWS-managed browser instance'
        assert result['status'] == 'ACTIVE'
        assert result['type'] == 'SYSTEM'
        assert result['network_configuration'] is None
        assert result['created_at'] == '2024-01-01T00:00:00Z'
        assert 'error' not in result

        mock_client.get_browser.assert_called_once_with(browserId='aws.browser.v1')

    @patch(
        'awslabs.amazon_bedrock_agentcore_browser_mcp_server.tools.browsers.get_control_plane_client'
    )
    def test_get_browser_resource_not_found(
        self, mock_get_client, client_error_resource_not_found
    ):
        """Test get browser with ResourceNotFoundException."""
        mock_client = mock_get_client.return_value
        mock_client.get_browser.side_effect = client_error_resource_not_found

        result = get_browser('nonexistent-browser')

        assert result['error'] == 'ResourceNotFoundException'
        assert result['message'] == 'Session not found'
        assert 'browser_id' not in result

    @patch(
        'awslabs.amazon_bedrock_agentcore_browser_mcp_server.tools.browsers.get_control_plane_client'
    )
    def test_get_browser_access_denied(self, mock_get_client, client_error_access_denied):
        """Test get browser with AccessDeniedException."""
        mock_client = mock_get_client.return_value
        mock_client.get_browser.side_effect = client_error_access_denied

        result = get_browser('aws.browser.v1')

        assert result['error'] == 'AccessDeniedException'
        assert result['message'] == 'Access denied to resource'

    @patch(
        'awslabs.amazon_bedrock_agentcore_browser_mcp_server.tools.browsers.get_control_plane_client'
    )
    def test_get_browser_unexpected_error(self, mock_get_client):
        """Test get browser with unexpected exception."""
        mock_client = mock_get_client.return_value
        mock_client.get_browser.side_effect = ConnectionError('Network unreachable')

        result = get_browser('aws.browser.v1')

        assert result['error'] == 'UnexpectedError'
        assert 'message' in result
