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
"""GitHub search functionality for AWS Security Reference Architecture MCP Server."""

import asyncio
from typing import Any, Dict, List

import httpx
from fastmcp import Context
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential_jitter

from awslabs.aws_sra_mcp_server.consts import GITHUB_API_URL, SRA_REPOSITORIES
from awslabs.aws_sra_mcp_server.models import SearchResult
from awslabs.aws_sra_mcp_server.server_utils import log_truncation, read_documentation_html
from awslabs.aws_sra_mcp_server.util import format_result


# Define retry decorator for HTTP requests
@retry(
    retry=retry_if_exception_type((httpx.HTTPError, httpx.NetworkError, httpx.TimeoutException)),
    stop=stop_after_attempt(5),
    wait=wait_exponential_jitter(max=60),
)
async def _http_get_with_retry(client: httpx.AsyncClient, url: str, **kwargs) -> httpx.Response:
    """Make an HTTP GET request with exponential backoff retry logic."""
    return await client.get(url, **kwargs)


async def __get_commits_str(
    ctx: Context, repo_owner: str, repo_name: str, commit_shas: List[str]
) -> str:
    """
    Get commit details as a formatted string.

    Args:
        ctx: MCP context for logging and error handling
        repo_owner: Owner of the GitHub repository
        repo_name: Name of the GitHub repository
        commit_shas: List of commit SHAs to retrieve

    Returns:
        Formatted string with commit details
    """
    parts = ["\n\n## Commits\n\nBelow is information on commits\n\n"]
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            for sha in commit_shas:
                commit_url = f"{GITHUB_API_URL}/repos/{repo_owner}/{repo_name}/commits/{sha}"
                response = await _http_get_with_retry(client, commit_url)
                response.raise_for_status()
                commit_data = response.json()
                parts.append(f"### {commit_data['commit']['message']}\n\n")
                if "files" in commit_data:
                    for file in commit_data["files"]:
                        parts.append(f"**{file['filename']}:**\n\n")
                        parts.append("```\n")
                        parts.append(f"{file['patch']}\n")
                        parts.append("```\n\n")
                else:
                    parts.append("No files were changed")
            return "".join(parts)
    except Exception as e:
        await ctx.error(f"Error getting commit details: {e}")
        return ""


async def __get_comments_str(ctx: Context, comment_url: str) -> str:
    """
    Get comments as a formatted string.

    Args:
        ctx: MCP context for logging and error handling
        comment_url: URL to fetch comments from

    Returns:
        Formatted string with comments
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            parts = ["\n\n## Comments\n\nBelow is information on comments\n\n"]
            response = await _http_get_with_retry(client, comment_url)
            response.raise_for_status()
            comments_data = response.json()
            for d in comments_data:
                parts.append(f"{d['user']['login']}: {d['body']}\n\n")
            return "".join(parts)
        except Exception as e:
            await ctx.error(f"Error getting comment details: {e}")
            return ""


async def _search_code(
    client: httpx.AsyncClient, repo: str, search_phrase: str, limit: int, headers: Dict[str, str]
) -> List[Dict[str, Any]]:
    """Search code in a GitHub repository."""
    code_search_url = f"{GITHUB_API_URL}/search/code"
    params = {
        "q": f"{search_phrase} repo:{repo}",
        "per_page": (limit // 2),  # Split limit between repositories
    }

    try:
        response = await _http_get_with_retry(
            client, code_search_url, params=params, headers=headers
        )
        response.raise_for_status()
        data = response.json()
        return data.get("items", [])
    except Exception:
        return []


async def _search_issues_or_prs(
    client: httpx.AsyncClient,
    repo: str,
    search_phrase: str,
    limit: int,
    headers: Dict[str, str],
    is_pr: bool,
) -> List[Dict[str, Any]]:
    """Search issues or PRs in a GitHub repository."""
    issues_search_url = f"{GITHUB_API_URL}/search/issues"
    item_type = "is:pr" if is_pr else "is:issue"
    params = {
        "q": f"{search_phrase} repo:{repo} {item_type}",
        "per_page": (limit // 2),  # Split limit between repositories
    }

    try:
        response = await _http_get_with_retry(
            client, issues_search_url, params=params, headers=headers
        )
        response.raise_for_status()
        data = response.json()
        return data.get("items", [])
    except Exception:
        return []


async def search_github(
    ctx: Context, search_phrase: str, limit: int = 10, github_token: str | None = None
) -> List[SearchResult]:
    """
    Search GitHub repositories for AWS Security Reference Architecture content.

    Args:
        ctx: MCP context for logging and error handling
        search_phrase: Search phrase to use
        limit: Maximum number of results to return
        github_token: Optional GitHub access token for authentication

    Returns:
        List of search results from GitHub repositories
    """
    results = []

    # Create a client for GitHub API requests with timeout
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Set up headers with authorization if token is provided
        headers = {}
        if github_token:
            headers["Authorization"] = f"Bearer {github_token}"

        for repo in SRA_REPOSITORIES:
            try:
                # Execute all three searches concurrently using asyncio.gather
                code_items, issue_items, pr_items = await asyncio.gather(
                    _search_code(client, repo, search_phrase, limit, headers),
                    _search_issues_or_prs(client, repo, search_phrase, limit, headers, is_pr=False),
                    _search_issues_or_prs(client, repo, search_phrase, limit, headers, is_pr=True),
                )

                # Process code search results
                for i, item in enumerate(code_items):
                    result = SearchResult(
                        rank_order=i + 1,
                        url=item.get("html_url", ""),
                        title=f"[Code] {item.get('name', '')} - {repo}",
                        context=item.get("path", ""),
                    )
                    results.append(result)

                # Process issue search results
                for i, item in enumerate(issue_items):
                    body = item.get("body")
                    if body and isinstance(body, str) and len(body) > 200:
                        body = body[:200] + "..."

                    result = SearchResult(
                        rank_order=i + len(results) + 1,
                        url=item.get("html_url", ""),
                        title=f"[Issue] {item.get('title', '')} - {repo}",
                        context=body,
                    )
                    results.append(result)

                # Process PR search results
                for i, item in enumerate(pr_items):
                    body = item.get("body")
                    if body and isinstance(body, str) and len(body) > 200:
                        body = body[:200] + "..."
                    result = SearchResult(
                        rank_order=i + len(results) + 1,
                        url=item.get("html_url", ""),
                        title=f"[PR] {item.get('title', '')} - {repo}",
                        context=body,
                    )
                    results.append(result)

            except Exception as e:
                await ctx.error(f"Error searching GitHub repository {repo}: {e}")

    # Sort results by rank_order and limit to requested number
    results.sort(key=lambda x: x.rank_order)
    return results[:limit]


async def get_issue_markdown(
    ctx: Context, issue_url: str, max_length: int, start_index: int
) -> str:
    """
    Fetches the content of a GitHub Issue url and converts it to Markdown.

    Args:
        ctx: MCP context for logging and error handling
        issue_url: URL of the issue to retrieve
        max_length: Maximum number of characters to return
        start_index: Starting character index for pagination

    Returns:
        Markdown content of the GitHub issue
    """
    await ctx.debug(f"Getting issue details for: {issue_url}")
    sp = issue_url.split("/")

    owner = sp[3]
    repo = sp[4]
    issue_number = sp[-1]

    url = f"{GITHUB_API_URL}/repos/{owner}/{repo}/issues/{issue_number}"

    # Create a client for GitHub API requests
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await _http_get_with_retry(client, url)
            response.raise_for_status()

            data = response.json()
            title = data["title"]
            body = data["body"]
            parts = [f"# Issue: {title}\n\n{body}"]
            number_of_comments = data["comments"]
            if number_of_comments > 0:
                comment_url = f"{url}/comments"
                comments = await __get_comments_str(ctx, comment_url)
                parts.append(comments)
            content = "".join(parts)
            await log_truncation(ctx, content, start_index=start_index, max_length=max_length)
            return format_result(
                url=issue_url,
                content=content,
                start_index=start_index,
                max_length=max_length,
                content_type="GitHub Issue",
            )
        except Exception as e:
            await ctx.error(f"Error getting issue details: {e}")
            return ""


async def get_pr_markdown(ctx: Context, pr_url: str, max_length: int, start_index: int) -> str:
    """
    Fetches the content of a GitHub PR url and converts it to Markdown.

    Args:
        ctx: MCP context for logging and error handling
        pr_url: URL of the pull request to retrieve
        max_length: Maximum number of characters to return
        start_index: Starting character index for pagination

    Returns:
        Markdown content of the GitHub pull request
    """
    sp = pr_url.split("/")

    owner = sp[3]
    repo = sp[4]
    pr_number = sp[-1]

    url = f"{GITHUB_API_URL}/repos/{owner}/{repo}/pulls/{pr_number}"

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()

            title = data["title"]
            body = data["body"]
            parts = [f"# Pull Request: {title}\n\n{body}"]
            number_of_commits = data["commits"]
            number_of_comments = data["comments"]

            if number_of_commits > 0:
                commit_response = await client.get(f"{url}/commits")
                commit_response.raise_for_status()
                commit_data = commit_response.json()
                shas = [commit["sha"] for commit in commit_data]
                commits = await __get_commits_str(
                    ctx=ctx, repo_owner=owner, repo_name=repo, commit_shas=shas
                )
                parts.append(commits)
            if number_of_comments > 0:
                comment_url = f"{url}/comments"
                comments = await __get_comments_str(ctx, comment_url)
                parts.append(comments)
            content = "".join(parts)
            await log_truncation(ctx, content, start_index=start_index, max_length=max_length)
            return format_result(
                url=pr_url,
                content=content,
                start_index=start_index,
                max_length=max_length,
                content_type="Pull Request",
            )
        except Exception as e:
            await ctx.error(f"Error getting pull request details: {e}")
            return ""


async def get_raw_code(
    ctx: Context, code_url: str, max_length: int, start_index: int, session_uuid: str
) -> str:
    """
    Get raw code content from a GitHub URL.

    Args:
        ctx: MCP context for logging and error handling
        code_url: URL of the code file to retrieve
        max_length: Maximum number of characters to return
        start_index: Starting character index for pagination
        session_uuid: Session UUID for tracking requests

    Returns:
        Markdown content of the code file
    """
    raw_url = code_url.replace("github.com", "raw.githubusercontent.com")
    raw_url = raw_url.replace("/blob/", "/")

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(raw_url)
            response.raise_for_status()
            await log_truncation(ctx, response.text, start_index, max_length)
            return format_result(
                url=code_url,
                content=response.text,
                start_index=start_index,
                max_length=max_length,
                content_type="Code",
            )
        except Exception as e:
            await ctx.debug(f"Error getting raw code from {e}, falling back to HTML")
            return await read_documentation_html(
                ctx=ctx,
                url_str=code_url,
                max_length=max_length,
                start_index=start_index,
                session_uuid=session_uuid,
            )
