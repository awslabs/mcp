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

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from awslabs.aws_sra_mcp_server.github import (
    SRA_REPOSITORIES,
    get_issue_markdown,
    get_pr_markdown,
    get_raw_code,
    search_github,
)


@pytest.mark.asyncio
async def test_search_code_exception():
    """Test _search_code with exception."""
    from awslabs.aws_sra_mcp_server.github import _search_code

    mock_client = AsyncMock()
    mock_client.get.side_effect = Exception("API Error")

    result = await _search_code(
        mock_client, "awslabs/sra-verify", "test", 10, {"Authorization": "Bearer token"}
    )

    assert result == []


@pytest.mark.asyncio
async def test_search_issues_or_prs_exception():
    """Test _search_issues_or_prs with exception."""
    from awslabs.aws_sra_mcp_server.github import _search_issues_or_prs

    mock_client = AsyncMock()
    mock_client.get.side_effect = Exception("API Error")

    result = await _search_issues_or_prs(
        mock_client,
        "awslabs/sra-verify",
        "test",
        10,
        {"Authorization": "Bearer token"},
        is_pr=False,
    )

    assert result == []


@pytest.mark.asyncio
@patch("awslabs.aws_sra_mcp_server.github.httpx.AsyncClient")
async def test_search_github_success(mock_client, mock_context):
    """Test search_github function success."""
    mock_code_response = MagicMock()
    mock_code_response.status_code = 200
    mock_code_response.json.return_value = {
        "items": [
            {
                "name": "example.py",
                "path": "src/example.py",
                "html_url": "https://github.com/awslabs/sra-verify/blob/main/src/example.py",
            }
        ]
    }

    mock_issues_response = MagicMock()
    mock_issues_response.status_code = 200
    mock_issues_response.json.return_value = {
        "items": [
            {
                "title": "Security issue example",
                "html_url": "https://github.com/awslabs/sra-verify/issues/1",
                "body": "This is an example security issue",
            }
        ]
    }

    mock_client_instance = AsyncMock()

    def mock_get(url, **kwargs):
        if "search/code" in url:
            return mock_code_response
        elif "search/issues" in url:
            return mock_issues_response
        return MagicMock()

    mock_client_instance.__aenter__.return_value.get.side_effect = mock_get
    mock_client.return_value = mock_client_instance

    results = await search_github(mock_context, "security", limit=10)

    assert len(results) >= 2
    code_results = [r for r in results if "[Code]" in r.title]
    issue_results = [r for r in results if "[Issue]" in r.title]
    assert len(code_results) >= 1
    assert len(issue_results) >= 1


@pytest.mark.asyncio
@patch("awslabs.aws_sra_mcp_server.github.httpx.AsyncClient")
async def test_search_github_with_token(mock_client, mock_context):
    """Test search_github function with GitHub token."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"items": []}

    mock_client_instance = AsyncMock()
    mock_client_instance.__aenter__.return_value.get.return_value = mock_response
    mock_client.return_value = mock_client_instance

    await search_github(mock_context, "security", limit=10, github_token="test-token")

    calls = mock_client_instance.__aenter__.return_value.get.call_args_list
    for call in calls:
        headers = call[1].get("headers", {})
        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer test-token"


@pytest.mark.asyncio
@patch("awslabs.aws_sra_mcp_server.github.httpx.AsyncClient")
async def test_search_github_error_handling(mock_client, mock_context):
    """Test search_github error handling."""
    mock_client_instance = AsyncMock()
    mock_client_instance.__aenter__.return_value.get.side_effect = Exception("API Error")
    mock_client.return_value = mock_client_instance

    results = await search_github(mock_context, "security", limit=10)

    assert results == []


@pytest.mark.asyncio
async def test_sra_repositories_constant():
    """Test SRA_REPOSITORIES constant."""
    assert "awslabs/sra-verify" in SRA_REPOSITORIES
    assert "aws-samples/aws-security-reference-architecture-examples" in SRA_REPOSITORIES


@pytest.mark.asyncio
@patch("awslabs.aws_sra_mcp_server.github._http_get_with_retry")
async def test_get_issue_markdown_success(mock_http_get, mock_context):
    """Test get_issue_markdown success."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "title": "Test Issue Title",
        "body": "Test issue body content",
        "comments": 0,
    }
    mock_http_get.return_value = mock_response

    result = await get_issue_markdown(
        mock_context,
        "https://github.com/awslabs/sra-verify/issues/123",
        max_length=1000,
        start_index=0,
    )

    assert "Test Issue Title" in result
    assert "Test issue body content" in result
    assert "AWS Security Reference Architecture GitHub Issue" in result


@pytest.mark.asyncio
@patch("awslabs.aws_sra_mcp_server.github._http_get_with_retry")
@patch("awslabs.aws_sra_mcp_server.github.__get_comments_str")
async def test_get_issue_markdown_with_comments(mock_get_comments, mock_http_get, mock_context):
    """Test get_issue_markdown with comments."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "title": "Test Issue Title",
        "body": "Test issue body content",
        "comments": 2,
    }
    mock_http_get.return_value = mock_response
    mock_get_comments.return_value = "\n\n## Comments\n\nuser1: Comment 1\n\nuser2: Comment 2\n\n"

    result = await get_issue_markdown(
        mock_context,
        "https://github.com/awslabs/sra-verify/issues/123",
        max_length=1000,
        start_index=0,
    )

    assert "Test Issue Title" in result
    assert "Comments" in result
    assert "user1: Comment 1" in result
    mock_get_comments.assert_called_once()


@pytest.mark.asyncio
@patch("awslabs.aws_sra_mcp_server.github._http_get_with_retry")
async def test_get_issue_markdown_exception(mock_http_get, mock_context):
    """Test get_issue_markdown exception handling."""
    mock_http_get.side_effect = Exception("API Error")

    result = await get_issue_markdown(
        mock_context,
        "https://github.com/awslabs/sra-verify/issues/123",
        max_length=1000,
        start_index=0,
    )

    assert result == ""
    assert len(mock_context.errors) == 1
    assert "Error getting issue details" in mock_context.errors[0]


@pytest.mark.asyncio
@patch("awslabs.aws_sra_mcp_server.github.httpx.AsyncClient")
async def test_get_pr_markdown_success(mock_client, mock_context):
    """Test get_pr_markdown success."""
    mock_pr_response = MagicMock()
    mock_pr_response.json.return_value = {
        "title": "Test PR Title",
        "body": "Test PR body content",
        "commits": 0,
        "comments": 0,
    }
    mock_pr_response.raise_for_status.return_value = None

    mock_client_instance = AsyncMock()
    mock_client_instance.__aenter__.return_value.get.return_value = mock_pr_response
    mock_client.return_value = mock_client_instance

    result = await get_pr_markdown(
        mock_context,
        "https://github.com/awslabs/sra-verify/pull/456",
        max_length=1000,
        start_index=0,
    )

    assert "Test PR Title" in result
    assert "Test PR body content" in result
    assert "AWS Security Reference Architecture Pull Request" in result


@pytest.mark.asyncio
@patch("awslabs.aws_sra_mcp_server.github.httpx.AsyncClient")
@patch("awslabs.aws_sra_mcp_server.github.__get_commits_str")
async def test_get_pr_markdown_with_commits(mock_get_commits, mock_client, mock_context):
    """Test get_pr_markdown with commits."""
    mock_pr_response = MagicMock()
    mock_pr_response.json.return_value = {
        "title": "Test PR Title",
        "body": "Test PR body content",
        "commits": 2,
        "comments": 0,
    }
    mock_pr_response.raise_for_status.return_value = None

    mock_commits_response = MagicMock()
    mock_commits_response.json.return_value = [{"sha": "abc123"}, {"sha": "def456"}]
    mock_commits_response.raise_for_status.return_value = None

    mock_client_instance = AsyncMock()
    mock_client_instance.__aenter__.return_value.get.side_effect = [
        mock_pr_response,
        mock_commits_response,
    ]
    mock_client.return_value = mock_client_instance
    mock_get_commits.return_value = "\n\n## Commits\n\nCommit details here\n\n"

    result = await get_pr_markdown(
        mock_context,
        "https://github.com/awslabs/sra-verify/pull/456",
        max_length=1000,
        start_index=0,
    )

    assert "Test PR Title" in result
    assert "Commits" in result
    mock_get_commits.assert_called_once()


@pytest.mark.asyncio
@patch("awslabs.aws_sra_mcp_server.github.httpx.AsyncClient")
async def test_get_pr_markdown_exception(mock_client, mock_context):
    """Test get_pr_markdown exception handling."""
    mock_client_instance = AsyncMock()
    mock_client_instance.__aenter__.return_value.get.side_effect = Exception("API Error")
    mock_client.return_value = mock_client_instance

    result = await get_pr_markdown(
        mock_context,
        "https://github.com/awslabs/sra-verify/pull/456",
        max_length=1000,
        start_index=0,
    )

    assert result == ""
    assert len(mock_context.errors) == 1
    assert "Error getting pull request details" in mock_context.errors[0]


@pytest.mark.asyncio
@patch("awslabs.aws_sra_mcp_server.github.httpx.AsyncClient")
async def test_get_raw_code_success(mock_client, mock_context):
    """Test get_raw_code success."""
    mock_response = MagicMock()
    mock_response.text = "print('Hello, World!')\n# This is test code"
    mock_response.raise_for_status.return_value = None

    mock_client_instance = AsyncMock()
    mock_client_instance.__aenter__.return_value.get.return_value = mock_response
    mock_client.return_value = mock_client_instance

    result = await get_raw_code(
        mock_context,
        "https://github.com/awslabs/sra-verify/blob/main/test.py",
        max_length=1000,
        start_index=0,
        session_uuid="test-session",
    )

    assert "print('Hello, World!')" in result
    assert "This is test code" in result
    assert "AWS Security Reference Architecture Code" in result


@pytest.mark.asyncio
@patch("awslabs.aws_sra_mcp_server.github.httpx.AsyncClient")
@patch("awslabs.aws_sra_mcp_server.github.read_documentation_html")
async def test_get_raw_code_fallback_to_html(mock_read_html, mock_client, mock_context):
    """Test get_raw_code fallback to HTML."""
    mock_client_instance = AsyncMock()
    mock_client_instance.__aenter__.return_value.get.side_effect = Exception("Raw API Error")
    mock_client.return_value = mock_client_instance
    mock_read_html.return_value = "HTML fallback content"

    result = await get_raw_code(
        mock_context,
        "https://github.com/awslabs/sra-verify/blob/main/test.py",
        max_length=1000,
        start_index=0,
        session_uuid="test-session",
    )

    assert result == "HTML fallback content"
    mock_read_html.assert_called_once()


@pytest.mark.asyncio
@patch("awslabs.aws_sra_mcp_server.github.httpx.AsyncClient")
async def test_http_get_with_retry_success(mock_client):
    """Test _http_get_with_retry success."""
    from awslabs.aws_sra_mcp_server.github import _http_get_with_retry

    mock_response = MagicMock()
    mock_client_instance = AsyncMock()
    mock_client_instance.get.return_value = mock_response

    result = await _http_get_with_retry(mock_client_instance, "https://api.github.com/test")

    assert result == mock_response
    mock_client_instance.get.assert_called_once_with("https://api.github.com/test")


@pytest.mark.asyncio
@patch("awslabs.aws_sra_mcp_server.github.httpx.AsyncClient")
async def test_http_get_with_retry_eventual_success(mock_client):
    """Test _http_get_with_retry eventual success after retries."""
    from awslabs.aws_sra_mcp_server.github import _http_get_with_retry

    mock_response = MagicMock()
    mock_client_instance = AsyncMock()
    mock_client_instance.get.side_effect = [
        httpx.NetworkError("Network error"),
        httpx.TimeoutException("Timeout"),
        mock_response,
    ]

    result = await _http_get_with_retry(mock_client_instance, "https://api.github.com/test")

    assert result == mock_response
    assert mock_client_instance.get.call_count == 3


@pytest.mark.asyncio
@patch("awslabs.aws_sra_mcp_server.github.httpx.AsyncClient")
async def test_http_get_with_retry_max_attempts(mock_client):
    """Test _http_get_with_retry max retry attempts."""
    from tenacity import RetryError

    from awslabs.aws_sra_mcp_server.github import _http_get_with_retry

    mock_client_instance = AsyncMock()
    mock_client_instance.get.side_effect = httpx.NetworkError("Persistent network error")

    with pytest.raises(RetryError):
        await _http_get_with_retry(mock_client_instance, "https://api.github.com/test")

    assert mock_client_instance.get.call_count == 5


@pytest.mark.asyncio
@patch("awslabs.aws_sra_mcp_server.github._http_get_with_retry")
async def test_get_commits_str_exception(mock_http_get, mock_context):
    """Test __get_commits_str exception handling."""
    from awslabs.aws_sra_mcp_server.github import __get_commits_str

    mock_http_get.side_effect = Exception("API Error")

    result = await __get_commits_str(mock_context, "test", "repo", ["abc123"])

    assert result == ""
    assert len(mock_context.errors) == 1


@pytest.mark.asyncio
@patch("awslabs.aws_sra_mcp_server.github._http_get_with_retry")
async def test_get_commits_str_no_files(mock_http_get, mock_context):
    """Test __get_commits_str with commit that has no files."""
    from awslabs.aws_sra_mcp_server.github import __get_commits_str

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "commit": {"message": "Test commit message"}
        # No "files" key at all
    }
    mock_response.raise_for_status.return_value = None
    mock_http_get.return_value = mock_response

    result = await __get_commits_str(mock_context, "test", "repo", ["abc123"])

    assert "Test commit message" in result
    assert "No files were changed" in result


@pytest.mark.asyncio
@patch("awslabs.aws_sra_mcp_server.github._http_get_with_retry")
async def test_get_comments_str_exception(mock_http_get, mock_context):
    """Test __get_comments_str exception handling."""
    from awslabs.aws_sra_mcp_server.github import __get_comments_str

    mock_http_get.side_effect = Exception("API Error")

    result = await __get_comments_str(
        mock_context, "https://api.github.com/repos/test/repo/issues/1/comments"
    )

    assert result == ""
    assert len(mock_context.errors) == 1


@pytest.mark.asyncio
@patch("awslabs.aws_sra_mcp_server.github._search_issues_or_prs")
@patch("awslabs.aws_sra_mcp_server.github._search_code")
@patch("awslabs.aws_sra_mcp_server.github.httpx.AsyncClient")
async def test_search_github_repository_exception(
    mock_client, mock_search_code, mock_search_issues, mock_context
):
    """Test search_github with repository-specific exception."""
    mock_client_instance = AsyncMock()
    mock_client.return_value = mock_client_instance

    # Mock one search function to raise an exception
    mock_search_code.side_effect = Exception("Repository error")
    mock_search_issues.return_value = []

    results = await search_github(mock_context, "security", limit=10)

    # Should still return results despite the exception
    assert isinstance(results, list)
    assert len(mock_context.errors) > 0
