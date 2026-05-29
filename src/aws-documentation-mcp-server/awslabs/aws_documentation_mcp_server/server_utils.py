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
from awslabs.aws_documentation_mcp_server.models import (
    SearchResponse,
    SearchTableResponse,
    TableResult,
)
from awslabs.aws_documentation_mcp_server.util import (
    extract_content_from_html,
    extract_sections_from_html,
    format_documentation_result,
    is_html_content,
    truncate_large_tables,
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
        content = truncate_large_tables(content, url=url_str)
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


def add_search_result_cache_item(search_response: SearchResponse) -> None:
    """Adds list of SearchResult items to cache.

    Add search results to the front of the cache, to ensure that
    the most recent query ID is ahead for duplicate URLs.

    Args:
        search_response: SearchResponse object returned by the search_documentation tool

    Returns:
        None; updates the global SEARCH_RESULT_CACHE

    """
    SEARCH_RESULT_CACHE.appendleft(search_response)


def get_query_id_from_cache(url: str) -> Optional[str]:
    """Fetches query_id from url in cache, if exists.

    Search the cache for a SearchResult type that contains the `url`
    passed into the function. If `url` found, return the query_id.

    Args:
        url: String representing the URL that is made for the read request

    Returns:
        Query ID of URL, or None

    """
    for _, search_response in enumerate(SEARCH_RESULT_CACHE):
        for search_result in search_response.search_results:
            if search_result.url == url:
                # Sanitization of query_id just in case
                query_id = quote(search_response.query_id)
                return query_id

    return None


async def read_sections_impl(
    ctx: Context,
    url_str: str,
    section_titles: list[str],
    session_uuid: str,
) -> str:
    """The implementation of the read_sections tool."""
    logger.debug(f'Fetching sections {section_titles} from {url_str}')

    url_with_session = f'{url_str}?session={session_uuid}'
    sections_param = ','.join(quote(title.strip(), safe='') for title in section_titles)
    url_with_session += f'&sections={sections_param}'

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

    if not is_html_content(page_raw, content_type):
        return 'Cannot extract sections from non-HTML content. Please use the read_documentation tool instead to get the full document content.'

    try:
        filtered_content = extract_sections_from_html(page_raw, section_titles)
    except ValueError as e:
        error_msg = str(e)
        logger.error(error_msg)
        await ctx.error(error_msg)
        raise

    try:
        markdown = extract_content_from_html(filtered_content)
        markdown = truncate_large_tables(markdown, url=url_str)

        # detect tagged error responses
        if markdown.startswith('<e>') and markdown.endswith('</e>'):
            # strip only the outer wrapper tags
            error_msg = markdown[3:-4]
            raise ValueError(error_msg)

    except Exception as e:
        error_msg = str(e)
        logger.error(error_msg)
        await ctx.error(error_msg)
        raise

    return markdown


async def search_table_impl(
    ctx: Context,
    url_str: str,
    section_title: str,
    query: str,
    max_rows: int,
    session_uuid: str,
) -> SearchTableResponse:
    """The implementation of the search_table tool."""
    from awslabs.aws_documentation_mcp_server.table_utils import (
        filter_table_rows,
        parse_html_tables,
    )

    logger.debug(f'Searching tables in section "{section_title}" of {url_str} for "{query}"')

    url_with_session = (
        f'{url_str}?session={session_uuid}&tool=search_table&query={quote(query, safe="")}'
    )
    if section_title:
        url_with_session += f'&section={quote(section_title, safe="")}'

    query_id = get_query_id_from_cache(url_str)
    if query_id:
        url_with_session += f'&query_id={query_id}'

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
            return SearchTableResponse(
                url=url_str,
                section_title=section_title or '',
                query=query,
                tables_searched=0,
                tables_with_matches=0,
                results=[],
                hint=error_msg,
            )

        if response.status_code >= 400:
            error_msg = f'Failed to fetch {url_str} - status code {response.status_code}'
            logger.error(error_msg)
            await ctx.error(error_msg)
            return SearchTableResponse(
                url=url_str,
                section_title=section_title or '',
                query=query,
                tables_searched=0,
                tables_with_matches=0,
                results=[],
                hint=error_msg,
            )

        page_raw = response.text

    table_data = parse_html_tables(page_raw, section_title if section_title else None)

    if table_data is None:
        return SearchTableResponse(
            url=url_str,
            section_title=section_title or '',
            query=query,
            tables_searched=0,
            tables_with_matches=0,
            results=[],
            hint='No tables found on this page.',
        )

    if 'error' in table_data:
        sections_list = ', '.join(f'"{s}"' for s in table_data.get('available_sections', []))
        return SearchTableResponse(
            url=url_str,
            section_title=section_title or '',
            query=query,
            tables_searched=0,
            tables_with_matches=0,
            results=[],
            hint=f'{table_data["error"]}. Available sections: {sections_list}',
        )

    # Handle multi-table response (multiple tables in section or page)
    if 'tables' in table_data:
        tables_list = table_data['tables']
        detected_section = table_data.get('detected_section')
    else:
        # Single table — wrap it in the same format
        tables_list = [table_data]
        detected_section = table_data.get('detected_section')

    effective_section = section_title or detected_section or '(all tables)'
    results_per_table = []
    for t in tables_list:
        matches = filter_table_rows(t['rows'], query)
        if matches:
            results_per_table.append(
                TableResult(
                    table_heading=t.get('table_heading'),
                    columns=t['columns'],
                    total_rows=len(t['rows']),
                    matched_rows=len(matches),
                    showing=min(len(matches), max_rows),
                    rows=matches[:max_rows],
                )
            )

    hint = None
    if not results_per_table:
        hint = (
            'No rows matched all query words. Try fewer or broader terms, '
            'or check spelling. Each word must appear somewhere in the row.'
        )

    return SearchTableResponse(
        url=url_str,
        section_title=effective_section,
        query=query,
        tables_searched=len(tables_list),
        tables_with_matches=len(results_per_table),
        results=results_per_table,
        hint=hint,
    )
