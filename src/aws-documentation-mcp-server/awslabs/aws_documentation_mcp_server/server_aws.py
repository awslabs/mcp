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
"""awslabs AWS Documentation MCP Server implementation."""

import httpx
import json
import re
import uuid

# Import models
from awslabs.aws_documentation_mcp_server.models import (
    RecommendationResult,
    SearchResult,
)
from awslabs.aws_documentation_mcp_server.server_utils import (
    DEFAULT_USER_AGENT,
    read_documentation_impl,
)

# Import utility functions
from awslabs.aws_documentation_mcp_server.util import (
    parse_recommendation_results,
)
from loguru import logger
from mcp.server.fastmcp import Context, FastMCP
from pydantic import Field
from typing import List


SEARCH_API_URL = 'https://proxy.search.docs.aws.amazon.com/search'
RECOMMENDATIONS_API_URL = 'https://contentrecs-api.docs.aws.amazon.com/v1/recommendations'
SESSION_UUID = str(uuid.uuid4())

mcp = FastMCP(
    'awslabs.aws-documentation-mcp-server',
    instructions="""
    # AWS Documentation MCP Server

    This server provides tools to access public AWS documentation, search for content, and get recommendations.

    ## Best Practices

    - For long documentation pages, make multiple calls to `read_documentation` with different `start_index` values for pagination
    - For very long documents (>30,000 characters), stop reading if you've found the needed information
    - When searching, use specific technical terms rather than general phrases
    - Use `recommend` tool to discover related content that might not appear in search results
    - For recent updates to a service, get an URL for any page in that service, then check the **New** section of the `recommend` tool output on that URL
    - If multiple searches with similar terms yield insufficient results, pivot to using `recommend` to find related pages.
    - Always cite the documentation URL when providing information to users

    ## Tool Selection Guide

    - Use `search_documentation` when: You need to find documentation about a specific AWS service or feature
    - Use `read_documentation` when: You have a specific documentation URL and need its content
    - Use `recommend` when: You want to find related content to a documentation page you're already viewing or need to find newly released information
    - Use `recommend` as a fallback when: Multiple searches have not yielded the specific information needed
    """,
    dependencies=[
        'pydantic',
        'httpx',
        'beautifulsoup4',
    ],
)


@mcp.tool()
async def read_documentation(
    ctx: Context,
    url: str = Field(description='URL of the AWS documentation page to read'),
    max_length: int = Field(
        default=5000,
        description='Maximum number of characters to return.',
        gt=0,
        lt=1000000,
    ),
    start_index: int = Field(
        default=0,
        description='On return output starting at this character index, useful if a previous fetch was truncated and more content is required.',
        ge=0,
    ),
) -> str:
    """Fetch and convert an AWS documentation page to markdown format.

    ## Usage

    This tool retrieves the content of an AWS documentation page and converts it to markdown format.
    For long documents, you can make multiple calls with different start_index values to retrieve
    the entire content in chunks.

    ## URL Requirements

    - Must be from the docs.aws.amazon.com domain
    - Must end with .html

    ## Example URLs

    - https://docs.aws.amazon.com/AmazonS3/latest/userguide/bucketnamingrules.html
    - https://docs.aws.amazon.com/lambda/latest/dg/lambda-invocation.html

    ## Output Format

    The output is formatted as markdown text with:
    - Preserved headings and structure
    - Code blocks for examples
    - Lists and tables converted to markdown format

    ## Handling Long Documents

    If the response indicates the document was truncated, you have several options:

    1. **Continue Reading**: Make another call with start_index set to the end of the previous response
    2. **Stop Early**: For very long documents (>30,000 characters), if you've already found the specific information needed, you can stop reading

    Args:
        ctx: MCP context for logging and error handling
        url: URL of the AWS documentation page to read
        max_length: Maximum number of characters to return
        start_index: On return output starting at this character index

    Returns:
        Markdown content of the AWS documentation
    """
    # Validate that URL is from docs.aws.amazon.com and ends with .html
    url_str = str(url)
    if not re.match(r'^https?://docs\.aws\.amazon\.com/', url_str):
        await ctx.error(f'Invalid URL: {url_str}. URL must be from the docs.aws.amazon.com domain')
        raise ValueError('URL must be from the docs.aws.amazon.com domain')
    if not url_str.endswith('.html'):
        await ctx.error(f'Invalid URL: {url_str}. URL must end with .html')
        raise ValueError('URL must end with .html')

    return await read_documentation_impl(ctx, url_str, max_length, start_index, SESSION_UUID)


@mcp.tool()
async def search_documentation(
    ctx: Context,
    search_phrase: str = Field(description='Search phrase to use'),
    limit: int = Field(
        default=10,
        description='Maximum number of results to return',
        ge=1,
        le=50,
    ),
) -> List[SearchResult]:
    """Search AWS documentation using the official AWS Documentation Search API.

    ## Usage

    This tool searches across all AWS documentation for pages matching your search phrase.
    Use it to find relevant documentation when you don't have a specific URL.

    ## Search Tips

    - Use specific technical terms rather than general phrases
    - Include service names to narrow results (e.g., "S3 bucket versioning" instead of just "versioning")
    - Use quotes for exact phrase matching (e.g., "AWS Lambda function URLs")
    - Include abbreviations and alternative terms to improve results

    ## Result Interpretation

    Each result includes:
    - rank_order: The relevance ranking (lower is more relevant)
    - url: The documentation page URL
    - title: The page title
    - context: A brief excerpt or summary (if available)

    Args:
        ctx: MCP context for logging and error handling
        search_phrase: Search phrase to use
        limit: Maximum number of results to return

    Returns:
        List of search results with URLs, titles, and context snippets
    """
    logger.debug(f'Searching AWS documentation for: {search_phrase}')

    request_body = {
        'textQuery': {
            'input': search_phrase,
        },
        'contextAttributes': [{'key': 'domain', 'value': 'docs.aws.amazon.com'}],
        'acceptSuggestionBody': 'RawText',
        'locales': ['en_us'],
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                SEARCH_API_URL,
                json=request_body,
                headers={
                    'Content-Type': 'application/json',
                    'User-Agent': DEFAULT_USER_AGENT,
                    'X-MCP-Session-Id': SESSION_UUID,
                },
                timeout=30,
            )
        except httpx.HTTPError as e:
            error_msg = f'Error searching AWS docs: {str(e)}'
            logger.error(error_msg)
            await ctx.error(error_msg)
            return [SearchResult(rank_order=1, url='', title=error_msg, context=None)]

        if response.status_code >= 400:
            error_msg = f'Error searching AWS docs - status code {response.status_code}'
            logger.error(error_msg)
            await ctx.error(error_msg)
            return [
                SearchResult(
                    rank_order=1,
                    url='',
                    title=error_msg,
                    context=None,
                )
            ]

        try:
            data = response.json()
        except json.JSONDecodeError as e:
            error_msg = f'Error parsing search results: {str(e)}'
            logger.error(error_msg)
            await ctx.error(error_msg)
            return [
                SearchResult(
                    rank_order=1,
                    url='',
                    title=error_msg,
                    context=None,
                )
            ]

    results = []
    if 'suggestions' in data:
        for i, suggestion in enumerate(data['suggestions'][:limit]):
            if 'textExcerptSuggestion' in suggestion:
                text_suggestion = suggestion['textExcerptSuggestion']
                context = None

                # Add context if available
                if 'summary' in text_suggestion:
                    context = text_suggestion['summary']
                elif 'suggestionBody' in text_suggestion:
                    context = text_suggestion['suggestionBody']

                results.append(
                    SearchResult(
                        rank_order=i + 1,
                        url=text_suggestion.get('link', ''),
                        title=text_suggestion.get('title', ''),
                        context=context,
                    )
                )

    logger.debug(f'Found {len(results)} search results for: {search_phrase}')
    return results


@mcp.tool()
async def recommend(
    ctx: Context,
    url: str = Field(description='URL of the AWS documentation page to get recommendations for'),
) -> List[RecommendationResult]:
    """Get content recommendations for an AWS documentation page.

    ## Usage

    This tool provides recommendations for related AWS documentation pages based on a given URL.
    Use it to discover additional relevant content that might not appear in search results.

    ## Recommendation Types

    The recommendations include four categories:

    1. **Highly Rated**: Popular pages within the same AWS service
    2. **New**: Recently added pages within the same AWS service - useful for finding newly released features
    3. **Similar**: Pages covering similar topics to the current page
    4. **Journey**: Pages commonly viewed next by other users

    ## When to Use

    - After reading a documentation page to find related content
    - When exploring a new AWS service to discover important pages
    - To find alternative explanations of complex concepts
    - To discover the most popular pages for a service
    - To find newly released information by using a service's welcome page URL and checking the **New** recommendations

    ## Finding New Features

    To find newly released information about a service:
    1. Find any page belong to that service, typically you can try the welcome page
    2. Call this tool with that URL
    3. Look specifically at the **New** recommendation type in the results

    ## Result Interpretation

    Each recommendation includes:
    - url: The documentation page URL
    - title: The page title
    - context: A brief description (if available)

    Args:
        ctx: MCP context for logging and error handling
        url: URL of the AWS documentation page to get recommendations for

    Returns:
        List of recommended pages with URLs, titles, and context
    """
    url_str = str(url)
    logger.debug(f'Getting recommendations for: {url_str}')

    recommendation_url = f'{RECOMMENDATIONS_API_URL}?path={url_str}'

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                recommendation_url,
                headers={'User-Agent': DEFAULT_USER_AGENT},
                timeout=30,
            )
        except httpx.HTTPError as e:
            error_msg = f'Error getting recommendations: {str(e)}'
            logger.error(error_msg)
            await ctx.error(error_msg)
            return [RecommendationResult(url='', title=error_msg, context=None)]

        if response.status_code >= 400:
            error_msg = f'Error getting recommendations - status code {response.status_code}'
            logger.error(error_msg)
            await ctx.error(error_msg)
            return [
                RecommendationResult(
                    url='',
                    title=error_msg,
                    context=None,
                )
            ]

        try:
            data = response.json()
        except json.JSONDecodeError as e:
            error_msg = f'Error parsing recommendations: {str(e)}'
            logger.error(error_msg)
            await ctx.error(error_msg)
            return [RecommendationResult(url='', title=error_msg, context=None)]

    results = parse_recommendation_results(data)
    logger.debug(f'Found {len(results)} recommendations for: {url_str}')
    return results


def main():
    """Run the MCP server with CLI argument support."""
    logger.info('Starting AWS Documentation MCP Server')
    mcp.run()


if __name__ == '__main__':
    main()
