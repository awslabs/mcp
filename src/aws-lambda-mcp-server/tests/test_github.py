# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.
"""Tests for the github module."""

import pytest
import json
from unittest.mock import patch, AsyncMock, MagicMock
import httpx
from awslabs.aws_lambda_mcp_server.utils.github import (
    fetch_github_content, fetch_github_directory, search_github_repo
)


class TestGithubUtils:
    """Tests for the github utility functions."""

    @pytest.mark.asyncio
    async def test_fetch_github_content_success(self):
        """Test successful GitHub content fetch."""
        # Mock response data
        mock_content = {
            "content": "SGVsbG8sIHdvcmxkIQ==",  # Base64 encoded "Hello, world!"
            "encoding": "base64"
        }
        
        # Create a mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_content
        
        # Mock the httpx.AsyncClient.get method
        with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            
            # Call the function
            result = await fetch_github_content("owner", "repo", "path/to/file.txt")
            
            # Verify the result
            assert result == "Hello, world!"
            
            # Verify the API call
            mock_get.assert_called_once()
            args, kwargs = mock_get.call_args
            assert "https://api.github.com/repos/owner/repo/contents/path/to/file.txt" in args[0]

    @pytest.mark.asyncio
    async def test_fetch_github_content_not_found(self):
        """Test GitHub content fetch with 404 response."""
        # Create a mock response for 404
        mock_response = MagicMock()
        mock_response.status_code = 404
        
        # Mock the httpx.AsyncClient.get method
        with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            
            # Call the function
            result = await fetch_github_content("owner", "repo", "nonexistent/file.txt")
            
            # Verify the result is None
            assert result is None

    @pytest.mark.asyncio
    async def test_fetch_github_content_error(self):
        """Test GitHub content fetch with error."""
        # Mock the httpx.AsyncClient.get method to raise an exception
        with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = httpx.RequestError("Connection error")
            
            # Call the function
            result = await fetch_github_content("owner", "repo", "path/to/file.txt")
            
            # Verify the result is None
            assert result is None

    @pytest.mark.asyncio
    async def test_fetch_github_directory_success(self):
        """Test successful GitHub directory fetch."""
        # Mock response data
        mock_contents = [
            {
                "name": "file1.txt",
                "path": "path/to/file1.txt",
                "type": "file",
                "download_url": "https://raw.githubusercontent.com/owner/repo/main/path/to/file1.txt"
            },
            {
                "name": "file2.txt",
                "path": "path/to/file2.txt",
                "type": "file",
                "download_url": "https://raw.githubusercontent.com/owner/repo/main/path/to/file2.txt"
            },
            {
                "name": "subdir",
                "path": "path/to/subdir",
                "type": "dir"
            }
        ]
        
        # Create a mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_contents
        
        # Mock the httpx.AsyncClient.get method
        with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            
            # Call the function
            result = await fetch_github_directory("owner", "repo", "path/to")
            
            # Verify the result
            assert len(result) == 3
            assert result[0]["name"] == "file1.txt"
            assert result[0]["type"] == "file"
            assert result[1]["name"] == "file2.txt"
            assert result[1]["type"] == "file"
            assert result[2]["name"] == "subdir"
            assert result[2]["type"] == "dir"
            
            # Verify the API call
            mock_get.assert_called_once()
            args, kwargs = mock_get.call_args
            assert "https://api.github.com/repos/owner/repo/contents/path/to" in args[0]

    @pytest.mark.asyncio
    async def test_fetch_github_directory_not_found(self):
        """Test GitHub directory fetch with 404 response."""
        # Create a mock response for 404
        mock_response = MagicMock()
        mock_response.status_code = 404
        
        # Mock the httpx.AsyncClient.get method
        with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            
            # Call the function
            result = await fetch_github_directory("owner", "repo", "nonexistent/dir")
            
            # Verify the result is an empty list
            assert result == []

    @pytest.mark.asyncio
    async def test_fetch_github_directory_error(self):
        """Test GitHub directory fetch with error."""
        # Mock the httpx.AsyncClient.get method to raise an exception
        with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = httpx.RequestError("Connection error")
            
            # Call the function
            result = await fetch_github_directory("owner", "repo", "path/to")
            
            # Verify the result is an empty list
            assert result == []

    @pytest.mark.asyncio
    async def test_search_github_repo_success(self):
        """Test successful GitHub repo search."""
        # Mock response data
        mock_search_result = {
            "total_count": 2,
            "items": [
                {
                    "name": "repo1",
                    "full_name": "owner/repo1",
                    "html_url": "https://github.com/owner/repo1",
                    "description": "Repository 1"
                },
                {
                    "name": "repo2",
                    "full_name": "owner/repo2",
                    "html_url": "https://github.com/owner/repo2",
                    "description": "Repository 2"
                }
            ]
        }
        
        # Create a mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_search_result
        
        # Mock the httpx.AsyncClient.get method
        with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            
            # Call the function
            result = await search_github_repo("search query", limit=2)
            
            # Verify the result
            assert len(result) == 2
            assert result[0]["name"] == "repo1"
            assert result[0]["full_name"] == "owner/repo1"
            assert result[1]["name"] == "repo2"
            assert result[1]["full_name"] == "owner/repo2"
            
            # Verify the API call
            mock_get.assert_called_once()
            args, kwargs = mock_get.call_args
            assert "https://api.github.com/search/repositories" in args[0]
            assert "q=search+query" in args[0]
            assert "per_page=2" in args[0]

    @pytest.mark.asyncio
    async def test_search_github_repo_error(self):
        """Test GitHub repo search with error."""
        # Mock the httpx.AsyncClient.get method to raise an exception
        with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = httpx.RequestError("Connection error")
            
            # Call the function
            result = await search_github_repo("search query")
            
            # Verify the result is an empty list
            assert result == []

    @pytest.mark.asyncio
    async def test_search_github_repo_rate_limit(self):
        """Test GitHub repo search with rate limit error."""
        # Create a mock response for rate limit
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.json.return_value = {
            "message": "API rate limit exceeded"
        }
        
        # Mock the httpx.AsyncClient.get method
        with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            
            # Call the function
            result = await search_github_repo("search query")
            
            # Verify the result is an empty list
            assert result == []
