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
"""Tests for the github utility module."""

import json
import pytest
import requests
from awslabs.aws_serverless_mcp_server.utils.github import fetch_github_content
from unittest.mock import MagicMock, patch


class TestGithub:
    """Tests for the github utility module."""

    def test_fetch_github_content_success(self):
        """Test fetch_github_content with a successful response."""
        # Mock the response
        mock_response = MagicMock()
        mock_response.json.return_value = {'name': 'test-repo', 'description': 'Test repository'}
        mock_response.raise_for_status = MagicMock()

        # Patch requests.get to return our mock response
        with patch('requests.get', return_value=mock_response) as mock_get:
            # Call the function
            url = 'https://api.github.com/repos/aws/aws-sam-cli-app-templates'
            result = fetch_github_content(url)

            # Verify the result
            assert result == {'name': 'test-repo', 'description': 'Test repository'}

            # Verify requests.get was called correctly
            mock_get.assert_called_once_with(
                url, headers={'Accept': 'application/vnd.github+json'}, timeout=30
            )
            mock_response.raise_for_status.assert_called_once()
            mock_response.json.assert_called_once()

    def test_fetch_github_content_with_headers(self):
        """Test fetch_github_content with custom headers."""
        # Mock the response
        mock_response = MagicMock()
        mock_response.json.return_value = {'name': 'test-repo', 'description': 'Test repository'}
        mock_response.raise_for_status = MagicMock()

        # Patch requests.get to return our mock response
        with patch('requests.get', return_value=mock_response) as mock_get:
            # Call the function with custom headers
            url = 'https://api.github.com/repos/aws/aws-sam-cli-app-templates'
            headers = {'Authorization': 'token ghp_123456789'}
            result = fetch_github_content(url, headers=headers)

            # Verify the result
            assert result == {'name': 'test-repo', 'description': 'Test repository'}

            # Verify requests.get was called with merged headers
            expected_headers = {
                'Accept': 'application/vnd.github+json',
                'Authorization': 'token ghp_123456789',
            }
            mock_get.assert_called_once_with(url, headers=expected_headers, timeout=30)

    def test_fetch_github_content_request_exception(self):
        """Test fetch_github_content when a request exception occurs."""
        # Patch requests.get to raise an exception
        with patch('requests.get', side_effect=requests.RequestException('Connection error')):
            # Call the function and expect an exception
            url = 'https://api.github.com/repos/aws/aws-sam-cli-app-templates'
            with pytest.raises(
                ValueError, match='Failed to fetch or decode GitHub content: Connection error'
            ):
                fetch_github_content(url)

    def test_fetch_github_content_json_decode_error(self):
        """Test fetch_github_content when a JSON decode error occurs."""
        # Mock the response
        mock_response = MagicMock()
        mock_response.json.side_effect = json.JSONDecodeError('Invalid JSON', '', 0)
        mock_response.raise_for_status = MagicMock()

        # Patch requests.get to return our mock response
        with patch('requests.get', return_value=mock_response):
            # Call the function and expect an exception
            url = 'https://api.github.com/repos/aws/aws-sam-cli-app-templates'
            with pytest.raises(ValueError, match='Failed to fetch or decode GitHub content'):
                fetch_github_content(url)

    def test_fetch_github_content_http_error(self):
        """Test fetch_github_content when an HTTP error occurs."""
        # Mock the response
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.HTTPError(
            '404 Client Error: Not Found'
        )

        # Patch requests.get to return our mock response
        with patch('requests.get', return_value=mock_response):
            # Call the function and expect an exception
            url = 'https://api.github.com/repos/nonexistent/repo'
            with pytest.raises(ValueError, match='Failed to fetch or decode GitHub content'):
                fetch_github_content(url)
