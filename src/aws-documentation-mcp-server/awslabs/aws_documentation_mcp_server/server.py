"""awslabs AWS Documentation MCP Server implementation."""

import argparse
import httpx
import json

# Import models
from awslabs.aws_documentation_mcp_server.models import (
    ReadDocumentationParams,
    RecommendationResult,
    RecommendParams,
    SearchDocumentationParams,
    SearchResult,
)

# Import utility functions
from awslabs.aws_documentation_mcp_server.util import (
    extract_content_from_html,
    format_documentation_result,
    is_html_content,
    parse_recommendation_results,
)
from mcp.server.fastmcp import FastMCP
from typing import List


DEFAULT_USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 ModelContextProtocol/1.0 (AWS Documentation Server)'
SEARCH_API_URL = 'https://proxy.search.docs.aws.amazon.com/search'
RECOMMENDATIONS_API_URL = 'https://contentrecs-api.docs.aws.amazon.com/v1/recommendations'


mcp = FastMCP(
    'awslabs.aws-documentation-mcp-server',
    instructions='An MCP server that provides tools and resources to access AWS documentation',
    dependencies=[
        'pydantic',
    ],
    log_level='ERROR',
)


@mcp.tool()
async def read_documentation(params: ReadDocumentationParams) -> str:
    """Return a markdown version of the AWS documentation at the specified URL.

    Args:
        params: Parameters for reading AWS documentation

    Returns:
        Markdown content of the AWS documentation
    """
    url = str(params.url)
    max_length = params.max_length
    start_index = params.start_index

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                url,
                follow_redirects=True,
                headers={'User-Agent': DEFAULT_USER_AGENT},
                timeout=30,
            )
        except httpx.HTTPError as e:
            return f'Failed to fetch {url}: {str(e)}'

        if response.status_code >= 400:
            return f'Failed to fetch {url} - status code {response.status_code}'

        page_raw = response.text
        content_type = response.headers.get('content-type', '')

    if is_html_content(page_raw, content_type):
        content = extract_content_from_html(page_raw)
    else:
        content = page_raw

    return format_documentation_result(url, content, start_index, max_length)


@mcp.tool()
async def search_documentation(params: SearchDocumentationParams) -> List[SearchResult]:
    """Search AWS documentation using the official AWS Documentation Search API.

    Args:
        params: Parameters for searching AWS documentation

    Returns:
        List of search results
    """
    search_phrase = params.search_phrase
    limit = params.limit

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
                headers={'Content-Type': 'application/json', 'User-Agent': DEFAULT_USER_AGENT},
                timeout=30,
            )
        except httpx.HTTPError as e:
            return [
                SearchResult(
                    rank_order=1, url='', title=f'Error searching AWS docs: {str(e)}', context=None
                )
            ]

        if response.status_code >= 400:
            return [
                SearchResult(
                    rank_order=1,
                    url='',
                    title=f'Error searching AWS docs - status code {response.status_code}',
                    context=None,
                )
            ]

        try:
            data = response.json()
        except json.JSONDecodeError as e:
            return [
                SearchResult(
                    rank_order=1,
                    url='',
                    title=f'Error parsing search results: {str(e)}',
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

    return results


@mcp.tool()
async def recommend(params: RecommendParams) -> List[RecommendationResult]:
    """Get content recommendations for an AWS documentation page.

    Args:
        params: Parameters for getting content recommendations

    Returns:
        List of recommended pages
    """
    url = str(params.url)
    recommendation_url = f'{RECOMMENDATIONS_API_URL}?path={url}'

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                recommendation_url,
                headers={'User-Agent': DEFAULT_USER_AGENT},
                timeout=30,
            )
        except httpx.HTTPError as e:
            return [
                RecommendationResult(
                    url='', title=f'Error getting recommendations: {str(e)}', context=None
                )
            ]

        if response.status_code >= 400:
            return [
                RecommendationResult(
                    url='',
                    title=f'Error getting recommendations - status code {response.status_code}',
                    context=None,
                )
            ]

        try:
            data = response.json()
        except json.JSONDecodeError as e:
            return [
                RecommendationResult(
                    url='', title=f'Error parsing recommendations: {str(e)}', context=None
                )
            ]

    return parse_recommendation_results(data)


def main():
    """Run the MCP server with CLI argument support."""
    parser = argparse.ArgumentParser(
        description='An AWS Labs Model Context Protocol (MCP) server for AWS Documentation'
    )
    parser.add_argument('--sse', action='store_true', help='Use SSE transport')
    parser.add_argument('--port', type=int, default=8888, help='Port to run the server on')

    args = parser.parse_args()

    # Run server with appropriate transport
    if args.sse:
        mcp.settings.port = args.port
        mcp.run(transport='sse')
    else:
        mcp.run()


if __name__ == '__main__':
    main()
