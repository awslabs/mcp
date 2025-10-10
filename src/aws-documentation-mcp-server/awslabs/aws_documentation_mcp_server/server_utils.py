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
import httpx
import os
from awslabs.aws_documentation_mcp_server.models import SearchResult
from awslabs.aws_documentation_mcp_server.util import (
    extract_content_from_html,
    format_documentation_result,
    is_html_content,
)
from collections import deque
from importlib.metadata import version
from loguru import logger
from mcp.server.fastmcp import Context
from typing import Optional
from urllib.parse import quote


try:
    __version__ = version('awslabs.aws-documentation-mcp-server')
except Exception:
    from . import __version__


# Allow User-Agent override via environment variable
BASE_USER_AGENT = os.getenv(
    'MCP_USER_AGENT',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36',
)
DEFAULT_USER_AGENT = (
    f'{BASE_USER_AGENT} ModelContextProtocol/{__version__} (AWS Documentation Server)'
)


async def read_documentation_impl(
    ctx: Context,
    url_str: str,
    max_length: int,
    start_index: int,
    session_uuid: str,
) -> str:
    """The implementation of the read_documentation tool."""
    logger.debug(f'Fetching documentation from {url_str}')

    url_with_session = f'{url_str}?session={session_uuid}'

    query_id = get_query_id_from_cache(url_str)
    if query_id:
        url_with_session += f'&query_id={query_id}'
        logger.debug(f'Using query_id {query_id}')

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                url_with_session,
                follow_redirects=True,
                headers={
                    'User-Agent': DEFAULT_USER_AGENT,
                    'X-MCP-Session-Id': session_uuid,
                },
                timeout=30,
            )
        except httpx.HTTPError as e:
            error_msg = f'Failed to fetch {url_str}: {str(e)}'
            logger.error(error_msg)
            await ctx.error(error_msg)
            return error_msg

        if response.status_code >= 400:
            error_msg = f'Failed to fetch {url_str} - status code {response.status_code}'
            logger.error(error_msg)
            await ctx.error(error_msg)
            return error_msg

        page_raw = response.text
        content_type = response.headers.get('content-type', '')

    if is_html_content(page_raw, content_type):
        content = extract_content_from_html(page_raw)
    else:
        content = page_raw

    result = format_documentation_result(url_str, content, start_index, max_length)

    # Log if content was truncated
    if len(content) > start_index + max_length:
        logger.debug(
            f'Content truncated at {start_index + max_length} of {len(content)} characters'
        )

    return result


SEARCH_RESULT_CACHE = deque(maxlen=3)


def add_search_result_cache_item(search_results: list[SearchResult]) -> None:
    """Adds list of SearchResult items to cache.

    Add search results to the front of the cache, to ensure that
    the most recent query ID is ahead for duplicate URLs.

    Args:
        search_results: List returned by the search_documentation tool

    Returns:
        None; updates the global SEARCH_RESULT_CACHE

    """
    SEARCH_RESULT_CACHE.appendleft(search_results)


def get_query_id_from_cache(url: str) -> Optional[str]:
    """Fetches query_id from url in cache, if exists.

    Search the cache for a SearchResult type that contains the `url`
    passed into the function. If `url` found, return the query_id.

    Args:
        url: String representing the URL that is made for the read request

    Returns:
        Query ID of URL, or None

    """
    for _, search_results in enumerate(SEARCH_RESULT_CACHE):
        for search_result in search_results:
            if search_result.url == url:
                # Sanitization of query_id just in case
                query_id = quote(search_result.query_id)
                return query_id

    return None
