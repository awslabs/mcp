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

import asyncio
import httpx
import json
import os
import random
import sys
from ..knowledge_models import KnowledgeResult
from fastmcp.client import Client
from fastmcp.client.client import CallToolResult
from loguru import logger
from mcp.types import TextContent
from typing import List


logger.remove()
logger.add(sys.stderr, level=os.getenv('FASTMCP_LOG_LEVEL', 'WARNING'))

KNOWLEDGE_MCP_ENDPOINT = os.environ.get(
    'KNOWLEDGE_MCP_ENDPOINT', 'https://knowledge-mcp.global.api.aws'
)
KNOWLEDGE_MCP_SEARCH_DOCUMENTATION_TOOL = 'aws___search_documentation'
MAX_RETRIES = 3
BASE_BACKOFF_SECONDS = 16
MAX_BACKOFF_SECONDS = 60


def _is_rate_limit_error(exc: Exception) -> bool:
    """Return True if the exception represents an HTTP 429 rate-limit response."""
    if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code == 429:
        return True
    msg = str(exc).lower()
    return '429' in msg or 'too many requests' in msg


async def search_documentation(
    search_phrase: str, topic: str, limit: int = 10
) -> List[KnowledgeResult]:
    """Search AWS documentation with automatic retry on rate limiting.

    Retries up to MAX_RETRIES times when the Knowledge MCP server returns
    HTTP 429 (rate limited). Uses exponential backoff with jitter between
    attempts. Non-rate-limit errors are raised immediately.

    Args:
        search_phrase: The search query.
        topic: The topic to search within.
        limit: Maximum number of results to return.

    Returns:
        List of KnowledgeResult containing search results.
    """
    for attempt in range(MAX_RETRIES):
        try:
            aws_knowledge_mcp_client = Client(KNOWLEDGE_MCP_ENDPOINT)

            async with aws_knowledge_mcp_client:
                request = {'search_phrase': search_phrase, 'limit': limit, 'topics': [topic]}

                result = await aws_knowledge_mcp_client.call_tool(
                    KNOWLEDGE_MCP_SEARCH_DOCUMENTATION_TOOL, request
                )
                logger.info(f'Received result: {result}')
                return _parse_search_documentation_result(result)
        except Exception as e:
            if _is_rate_limit_error(e) and attempt < MAX_RETRIES - 1:
                backoff = min(BASE_BACKOFF_SECONDS * (2**attempt), MAX_BACKOFF_SECONDS)
                jitter = random.uniform(0, backoff * 0.1)
                wait_time = backoff + jitter
                logger.warning(
                    f'Rate limited by Knowledge MCP server '
                    f'(attempt {attempt + 1}/{MAX_RETRIES}). '
                    f'Retrying in {wait_time:.1f}s...'
                )
                await asyncio.sleep(wait_time)
            else:
                logger.error(f'Error searching documentation: {str(e)}')
                raise


def _parse_search_documentation_result(result: CallToolResult) -> List[KnowledgeResult]:
    if result.is_error:
        raise Exception(f'Tool call returned an error: {result.content}')

    if not result.content or len(result.content) == 0:
        raise Exception('Empty response from tool')

    content = result.content[0]
    if not isinstance(content, TextContent):
        raise Exception(f'Content is not text type: {type(content)}')

    result_content_json = json.loads(content.text)
    raw_results = result_content_json['content']['result']

    results = [
        KnowledgeResult(
            rank=item['rank_order'],
            title=item['title'],
            url=item['url'],
            context=item['context'],
        )
        for item in raw_results
    ]

    return results
