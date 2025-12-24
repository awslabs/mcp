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
"""AWS Documentation search functionality for AWS Security Reference Architecture MCP Server."""

from asyncio import gather
from typing import Any, Dict, List

from fastmcp import Context
from httpx import AsyncClient

from awslabs.aws_sra_mcp_server.consts import (
    DEFAULT_USER_AGENT,
    MAX_CONCURRENT_REQUESTS,
    RECOMMENDATIONS_API_URL,
    SEARCH_API_URL,
    SESSION_UUID,
)
from awslabs.aws_sra_mcp_server.models import RecommendationResult, SearchResult


def parse_recommendation_results(data: Dict[str, Any]) -> List[RecommendationResult]:
    """Parse recommendation API response into RecommendationResult objects.

    Args:
        data: Raw API response data

    Returns:
        List of recommendation results
    """
    results = []

    def process_items(items, context_generator):
        for item in items:
            context = context_generator(item)
            results.append(
                RecommendationResult(
                    url=item.get("url", ""), title=item.get("assetTitle", ""), context=context
                )
            )

    if "highlyRated" in data and "items" in data["highlyRated"]:
        process_items(data["highlyRated"]["items"], lambda item: item.get("abstract"))

    if "journey" in data and "items" in data["journey"]:
        for intent_group in data["journey"]["items"]:
            intent = intent_group.get("intent", "")
            if "urls" in intent_group:
                process_items(
                    intent_group["urls"],
                    lambda _, inner_intent=intent: f"Intent: {inner_intent}"
                    if inner_intent
                    else None,
                )

    if "new" in data and "items" in data["new"]:
        process_items(
            data["new"]["items"],
            lambda item: f"New content added on {item.get('dateCreated', '')}"
            if item.get("dateCreated")
            else "New content",
        )

    if "similar" in data and "items" in data["similar"]:
        process_items(
            data["similar"]["items"], lambda item: item.get("abstract", "Similar content")
        )

    return results


def parse_search_results(data: Dict[str, Any], limit: int = 10) -> List[SearchResult]:
    """
    Parse search API response into SearchResult objects.

    Args:
        data: Raw API response data
        limit: Maximum number of results to return
    """
    return [
        SearchResult(
            rank_order=i + 1,
            url=suggestion["textExcerptSuggestion"].get("link", ""),
            title=suggestion["textExcerptSuggestion"].get("title", ""),
            context=suggestion["textExcerptSuggestion"].get("summary")
            or suggestion["textExcerptSuggestion"].get("suggestionBody")
            or suggestion["textExcerptSuggestion"].get("context", ""),
        )
        for i, suggestion in enumerate(data.get("suggestions", [])[:limit])
        if "textExcerptSuggestion" in suggestion
    ]


async def _execute_search_request(client: AsyncClient, search_phrase: str) -> Dict[str, Any]:
    """Execute a search request to AWS documentation API."""
    request_body = {
        "textQuery": {
            "input": search_phrase,
        },
        "contextAttributes": [
            {"key": "aws-docs-search-guide", "value": "AWS Security Reference Architecture"}
        ],  # Limits to SRA Docs only
        "acceptSuggestionBody": "RawText",
        "locales": ["en_us"],
    }

    search_url_with_session = f"{SEARCH_API_URL}?session={SESSION_UUID}"

    headers = {
        "Content-Type": "application/json",
        "User-Agent": DEFAULT_USER_AGENT,
        "X-MCP-Session-Id": SESSION_UUID,
    }

    try:
        response = await client.post(search_url_with_session, json=request_body, headers=headers)
        response.raise_for_status()
        return response.json()
    except Exception:
        return {}


async def _execute_recommendation_request(
    ctx: Context, client: AsyncClient, url: str
) -> Dict[str, Any]:
    """Execute a recommendation request to AWS documentation API."""
    recommendation_url = f"{RECOMMENDATIONS_API_URL}?path={url}&session={SESSION_UUID}"
    headers = {"User-Agent": DEFAULT_USER_AGENT}

    try:
        response = await client.get(recommendation_url, headers=headers)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        await ctx.error(f"Error executing recommendation request: {e}")
        return {}


async def search_sra_documentation(
    ctx: Context, search_phrase: str, limit: int = 10
) -> List[SearchResult]:
    """
    Search SRA documentation

    Args:
        ctx: MCP context for logging and error handling
        search_phrase: Search phrase to use
        limit: Maximum number of results to return

    Returns:
        List of search results from AWS documentation
    """
    await ctx.debug(f"Searching AWS documentation for: {search_phrase}")

    # Create a client for AWS documentation search with timeout
    async with AsyncClient(timeout=30.0) as client:
        try:
            data = await _execute_search_request(client, search_phrase)
            return parse_search_results(data, limit)
        except Exception as e:
            await ctx.error(f"Error searching AWS documentation: {e}")
            return []


async def get_recommendations(ctx: Context, url: str) -> List[RecommendationResult]:
    """
    Get content recommendations for an AWS documentation page.

    Args:
        ctx: MCP context for logging and error handling
        url: URL of the AWS documentation page

    Returns:
        List of recommended pages
    """
    await ctx.debug(f"Getting recommendations for: {url}")

    # Create a client for AWS documentation recommendations with timeout
    async with AsyncClient(timeout=30.0) as client:
        try:
            data = await _execute_recommendation_request(ctx, client, url)
            return parse_recommendation_results(data)
        except Exception as e:
            await ctx.error(f"Error getting recommendations: {e}")
            return []


async def get_multiple_recommendations(
    ctx: Context, urls: List[str]
) -> Dict[str, List[RecommendationResult]]:
    """
    Get content recommendations for multiple AWS documentation pages concurrently.

    Args:
        ctx: MCP context for logging and error handling
        urls: List of URLs to get recommendations for

    Returns:
        Dictionary mapping URLs to their recommendation results
    """
    await ctx.debug(f"Getting recommendations for {len(urls)} URLs")

    results = {}

    # Create a client for AWS documentation recommendations with timeout
    #  amazonq-ignore-next-line
    async with AsyncClient(timeout=30.0) as client:
        try:
            # Execute requests in batches to avoid overwhelming the API
            for i in range(0, len(urls), MAX_CONCURRENT_REQUESTS):
                batch = urls[i : i + MAX_CONCURRENT_REQUESTS]
                batch_tasks = [_execute_recommendation_request(ctx, client, url) for url in batch]
                batch_results = await gather(*batch_tasks)

                # Process results for this batch
                for url, data in zip(batch, batch_results):
                    results[url] = parse_recommendation_results(data)

            return results
        except Exception as e:
            await ctx.error(f"Error getting multiple recommendations: {e}")
            return {url: [] for url in urls}
