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
"""AWS Security Reference Architecture MCP Server implementation."""

import asyncio
import os
import re
from typing import List

from fastmcp import Context, FastMCP
from fastmcp.server.elicitation import (
    AcceptedElicitation,
    CancelledElicitation,
    DeclinedElicitation,
)
from mcp import McpError
from pydantic import Field

from awslabs.aws_sra_mcp_server.aws_documentation import (
    get_recommendations,
    search_sra_documentation,
)
from awslabs.aws_sra_mcp_server.consts import SECURITY_KEYWORDS, SESSION_UUID

# Import search functionality
from awslabs.aws_sra_mcp_server.github import (
    get_issue_markdown,
    get_pr_markdown,
    get_raw_code,
    search_github,
)

# Import models
from awslabs.aws_sra_mcp_server.models import (
    RecommendationResult,
    SearchResult,
)
from awslabs.aws_sra_mcp_server.server_utils import (
    read_documentation_html,
    read_documentation_markdown,
    read_other,
)

MCP = FastMCP(
    "awslabs.aws-sra-mcp-server",
    instructions="""
    # AWS Security Reference Architecture MCP Server

    This server provides tools to access AWS Security Reference Architecture (SRA) documentation,
    search for security and compliance content, and get recommendations.

    ## What is AWS Security Reference Architecture?

    The AWS Security Reference Architecture (SRA) is a holistic set of guidelines for deploying the
    full complement of AWS security services in a multi-account environment. It provides
    prescriptive guidance on how to architect a security foundation across AWS accounts and AWS
    Organizations.

    ## Best Practices

    - For long documentation pages, make multiple calls to `read_documentation` with different
      `start_index` values for pagination
    - For very long documents (>30,000 characters), stop reading if you've found the needed
      information
    - When searching, use specific security and compliance terms rather than general phrases
    - Use `recommend` tool to discover related content that might not appear in search results
    - For recent updates to security services, get an URL for any page in that service, then check
      the **New** section of the `recommend` tool output on that URL
    - Always cite the documentation URL when providing security information to users

    ## Tool Selection Guide

    - Use `search_security_and_compliance_best_practices_content` when: You need to find
      documentation about AWS security services, compliance, or security best practices
    - Use `read_security_and_compliance_best_practices_content` when: You have a specific security
      documentation URL and need its content
    - Use `recommend` when: You want to find related security content to a documentation page you're
      already viewing
    """,
    dependencies=[
        "pydantic",
        "httpx",
        "beautifulsoup4",
    ],
)


async def get_github_token(ctx: Context) -> str | None:
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        await ctx.warning("GITHUB_TOKEN not set in environment variables")
        try:
            result = await ctx.elicit(
                message="GITHUB_TOKEN not set in environment variables. Provide a GITHUB_TOKEN.",
                response_type=str,
            )
            if isinstance(result, AcceptedElicitation):
                token = result.data
                print("Received GITHUB TOKEN from user. Continuing")
                return token
            elif isinstance(result, DeclinedElicitation):
                print("User declined to provide GITHUB TOKEN. Continuing without GitHub search.")
                return ""
            elif isinstance(result, CancelledElicitation):
                print("User cancelled. Exiting.")
                return None
            else:
                return None
        except McpError as e:
            if "Elicitation not supported" not in e.args:
                await ctx.error(f"Error eliciting GITHUB_TOKEN: {e}")
            return None
    else:
        return token


@MCP.tool()
async def read_content(
    ctx: Context,
    url: str = Field(
        description="URL of the AWS Security Reference Architecture documentation page to read"
    ),
    max_length: int = Field(
        default=5000,
        description="Maximum number of characters to return.",
        gt=0,
        lt=1000000,
    ),
    start_index: int = Field(
        default=0,
        # ruff: noqa: E501
        description="On return output starting at this character index, useful if a previous fetch was truncated and more content is required.",
        ge=0,
    ),
) -> str:
    """Fetch security and compliance best practices content stored in the AWS Security Reference
    Architecture and convert it into markdown format.

    ## Usage

    This tool retrieves the content of an AWS Security Reference Architecture content stores and
    converts it to markdown format. For long documents, you can make multiple calls with different
    start_index values to retrieve the entire content in chunks.

    ## URL Requirements

    - Must be from the docs.aws.amazon.com domain, code, issues, or pull requests from github
    - Preferably related to Security Reference Architecture, security services or compliance

    ## Example URLs

    - https://docs.aws.amazon.com/prescriptive-guidance/latest/security-reference-architecture/welcome.html
    - https://github.com/awslabs/sra-verify/blob/af737628e43a16f755f0aa45cb15474009819f73/sraverify/sraverify/services/securityhub/checks/sra_securityhub_10.py
    - https://github.com/aws-samples/aws-security-reference-architecture-examples/issues/233
    - https://github.com/aws-samples/aws-security-reference-architecture-examples/pull/167

    ## Output Format

    The output is formatted as markdown text with:
    - Preserved headings and structure
    - Code blocks for examples
    - Lists and tables converted to markdown format

    ## Handling Long Documents

    If the response indicates the document was truncated, you have several options:

    1. **Continue Reading**: Make another call with start_index set to the end of the previous
       response
    2. **Stop Early**: For very long documents (>30,000 characters), if you've already found the
       specific information needed, you can stop reading

    Args:
        ctx: MCP context for logging and error handling
        url: URL of the AWS Security Reference Architecture content to read
        max_length: Maximum number of characters to return
        start_index: On return output starting at this character index

    Returns:
        Markdown content of the AWS Security Reference Architecture documentation
    """
    # Validate that URL is from docs.aws.amazon.com and ends with .html
    url_str = str(url)
    if not re.match(r"^https?://docs\.aws\.amazon\.com/", url_str) and not re.match(
        r"^https?://github\.com/", url_str
    ):
        await ctx.error(
            f"Invalid URL: {url_str}. URL must be from the docs.aws.amazon.com domain or GitHub"
        )
        raise ValueError("URL must be from the docs.aws.amazon.com domain or GitHub")
    if url_str.endswith(".html"):
        return await read_documentation_html(ctx, url_str, max_length, start_index, SESSION_UUID)
    elif url_str.endswith(".md"):
        return await read_documentation_markdown(
            ctx, url_str, max_length, start_index, SESSION_UUID
        )
    elif re.search(r"issues/\d+(?=$|[/?#])", url_str):
        return await get_issue_markdown(ctx, url_str, max_length, start_index)
    elif re.search(r"pull/\d+(?=$|[/?#])", url_str):
        return await get_pr_markdown(ctx, url_str, max_length, start_index)
    elif re.match(r"^https?://github\.com/", url_str):
        return await get_raw_code(ctx, url_str, max_length, start_index, SESSION_UUID)
    else:
        return await read_other(ctx, url_str, max_length, start_index, SESSION_UUID)


@MCP.tool()
async def search_content(
    ctx: Context,
    search_phrase: str = Field(
        description="Search phrase to use for finding security and compliance documentation"
    ),
    limit: int = Field(
        default=10,
        description="Maximum number of results to return",
        ge=1,
        le=50,
    ),
) -> List[SearchResult]:
    """Search security and compliance best practices content stored in the AWS Security Reference
     Architecture prescriptive guidance and GitHub repositories.

    ## Usage

    This tool searches across multiple sources:
    1. AWS Security Reference Architecture as well as security and compliance related documentation
    2. GitHub code repositories:
       awslabs/sra-verify and aws-samples/aws-security-reference-architecture-examples

    It returns results from both sources prioritizing an equal mix of documentation and content
    from GitHub (i.e., code, issues, and pull requests).

    ## Search Tips

    - Use specific security and compliance terms rather than general phrases
    - Use quotes for exact phrase matching (e.g., "Security Hub" or "Security Account")
    - Include security or compliance related abbreviations like "SRA", "NIST 800-53", "PCI DSS",
      "HIPAA", etc.
    - Add "security" or "compliance" to your search terms to focus on security-related content
    - For GitHub-specific searches, include terms like "code", "implementation", "example",
      "issues", "pull requests", "problems", and "solutions"

    ## Result Interpretation

    Each result includes:
    - rank_order: The relevance ranking (lower is more relevant)
    - url: The prescriptive guidance page URL or GitHub URL
    - title: The page title or GitHub resource title
    - context: A brief excerpt or summary (if available)

    GitHub results are prefixed with:
    - [Code]: For code files in the repositories
    - [Issue]: For GitHub issues
    - [PR]: For pull requests
    - [Commit]: For commit messages

    Args:
        ctx: MCP context for logging and error handling
        search_phrase: Search phrase to use for finding security and compliance documentation
        limit: Maximum number of results to return
    Returns:
        List of security-focused search results with URLs, titles, and context snippets
    """
    await ctx.debug(
        f"Searching AWS Security Reference Architecture documentation for: {search_phrase}"
    )

    try:
        # Set timeout for the entire search operation (60 seconds)
        async with asyncio.timeout(60):
            # Search AWS documentation with timeout
            aws_docs_task = asyncio.create_task(search_sra_documentation(ctx, search_phrase, limit))

            # Get GitHub token
            token = await get_github_token(ctx)

            # Search GitHub repositories with timeout
            github_task = asyncio.create_task(search_github(ctx, search_phrase, limit, token))

            # Wait for both searches to complete or timeout
            aws_docs_results, github_results = await asyncio.gather(
                aws_docs_task, github_task, return_exceptions=True
            )

            # Handle exceptions from tasks
            if isinstance(aws_docs_results, Exception):
                await ctx.error(f"AWS docs search failed: {aws_docs_results}")
                aws_docs_results = []

            if isinstance(github_results, Exception):
                await ctx.error(f"GitHub search failed: {github_results}")
                github_results = []
            elif isinstance(github_results, List):
                await ctx.debug(f"Found {len(github_results)} GitHub results for: {search_phrase}")

            # If both searches failed, return an error
            if not aws_docs_results and not github_results:
                error_msg = "Failed to retrieve search results from both AWS and GitHub content"
                await ctx.error(error_msg)
                return [SearchResult(rank_order=1, url="", title=error_msg, context=None)]

    except asyncio.TimeoutError:
        error_msg = f"Search operation timed out after 60 seconds for: {search_phrase}"
        await ctx.error(error_msg)
        return [SearchResult(rank_order=1, url="", title=error_msg, context=None)]
    except Exception as e:
        error_msg = f"Error searching documentation: {str(e)}"
        await ctx.error(error_msg)
        return [SearchResult(rank_order=1, url="", title=error_msg, context=None)]

    # Combine and filter results
    aws_docs_filtered_results = []

    # Filter AWS documentation results
    if isinstance(aws_docs_results, List):
        for result in aws_docs_results:
            # Check if any security keyword is in the URL, title, or context
            is_security_related = any(
                keyword in result.url.lower()
                or keyword in result.title.lower()
                or (result.context and keyword in result.context.lower())
                for keyword in SECURITY_KEYWORDS
            )

            # Add to combined results if security-related or if we don't have enough results yet
            if is_security_related or len(aws_docs_filtered_results) < limit:
                aws_docs_filtered_results.append(result)

    # Compute Limits -- deprioritize docs over gh content
    docs_limit = limit // 2 if limit % 2 == 0 else (limit // 2) - 1
    gh_limit = limit // 2 if limit % 2 == 0 else (limit // 2) + 1

    # Filter by Limit
    combined_results = aws_docs_filtered_results[:docs_limit]
    if docs_limit > len(aws_docs_filtered_results):
        gh_limit = limit - len(aws_docs_filtered_results)

    if isinstance(github_results, List):
        combined_results += github_results[:gh_limit]

    # Sort by rank_order and limit results
    combined_results.sort(key=lambda x: x.rank_order)

    await ctx.debug(
        f"Found {len(combined_results)} security-focused search results for: {search_phrase}"
    )
    return combined_results


@MCP.tool()
async def recommend(
    ctx: Context,
    url: str = Field(description="URL of the SRA page to get recommendations for"),
    limit: int = Field(
        default=10,
        description="Maximum number of results to return",
        ge=1,
        le=50,
    ),
) -> List[RecommendationResult]:
    """Get security and compliance content recommendations for AWS Security Reference Architecture
    content.

    ## Usage

    This tool provides recommendations for related AWS security and compliance best practices based
    on a given URL. Use it to discover additional relevant security and compliance content that
    might not appear in search results.

    ## Recommendation Types

    The recommendations include four categories:

    1. **Highly Rated**: Popular security and compliance pages
    2. **New**: Recently added security and compliance pages
    3. **Similar**: Pages covering similar security anc compliance topics
    4. **Journey**: Pages commonly viewed next by other security and compliance professionals

    ## When to Use

    - After reading a security and compliance content to find related content
    - When exploring a new AWS security or compliance service to discover important content
    - To find alternative explanations of complex security and compliance concepts
    - To discover the most popular security and compliance content for a service
    - To find new security and compliance details for services.

    ## Finding New Security Features

    To find newly released security or compliance information associated with AWS:
    1. Find any page belonging to an AWS service, typically you can try the welcome page
    2. Call this tool with that URL
    3. Look specifically at the **New** recommendation type in the results

    ## Result Interpretation

    Each recommendation includes:
    - url: The documentation page URL
    - title: The page title
    - context: A brief description (if available)

    Args:
        ctx: MCP context for logging and error handling
        url: URL of the SRA documentation page to get recommendations for
        limit: Maximum number of results to return
    Returns:
        List of recommended security pages with URLs, titles, and context
    """
    url_str = str(url)
    await ctx.debug(f"Getting security recommendations for: {url_str}")

    try:
        results = await get_recommendations(ctx, url_str)
    except Exception as e:
        error_msg = f"Error getting security recommendations: {str(e)}"
        await ctx.error(error_msg)
        return [RecommendationResult(url="", title=error_msg, context=None)]

    # Filter results to prioritize security-related content

    security_results = []
    for result in results:
        # Check if any security keyword is in the URL, title, or context
        is_security_related = any(
            keyword in result.url.lower()
            or keyword in result.title.lower()
            or (result.context and keyword in result.context.lower())
            for keyword in SECURITY_KEYWORDS
        )

        if is_security_related:
            security_results.append(result)

    # If we don't have enough security-related results, include some of the original results
    if len(security_results) < limit and results:
        remaining_results = [r for r in results if r not in security_results]
        security_results.extend(remaining_results[: limit - len(security_results)])

    if len(security_results) > 0:
        await ctx.debug(
            f"Found {len(security_results)} using security-focused recommendations for: {url_str}"
        )
    else:
        await ctx.debug(
            f"No security-focused recommendations for: {url_str}. Filtered results using {','.join(SECURITY_KEYWORDS)} keywords"
        )
    return security_results


def main():
    """Run the MCP server with CLI argument support."""
    MCP.run()


if __name__ == "__main__":
    main()
