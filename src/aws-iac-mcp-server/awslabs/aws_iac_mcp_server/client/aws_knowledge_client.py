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

import json
import os
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
KNOWLEDGE_MCP_READ_DOCUMENTATION_TOOL = 'aws___read_documentation'


async def search_documentation(
    search_phrase: str, topic: str, limit: int = 10
) -> List[KnowledgeResult]:
    """Search AWS documentation.

    Args:
        search_phrase: The search query.
        topic: The topic to search within.
        limit: Maximum number of results to return.

    Returns:
        List of KnowledgeResult containing search results.
    """
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
        # For dev team troubleshooting
        logger.error(f'Error searching documentation: {str(e)}')
        raise e


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


async def read_documentation(url: str, start_index: int = 0) -> List[KnowledgeResult]:
    """Read AWS documentation from a specific URL.

    Args:
        url: The documentation URL to read.
        start_index: Starting character index for pagination.

    Returns:
        List of KnowledgeResult containing the documentation content.
    """
    try:
        logger.info(f'Connecting to AWS Knowledge MCP at {KNOWLEDGE_MCP_ENDPOINT}')
        aws_knowledge_mcp_client = Client(KNOWLEDGE_MCP_ENDPOINT)

        async with aws_knowledge_mcp_client:
            result = await aws_knowledge_mcp_client.call_tool(
                KNOWLEDGE_MCP_READ_DOCUMENTATION_TOOL, {'url': url, 'start_index': start_index}
            )
            logger.info(f'Received result: {result}')
            return _parse_read_documentation_result(result)
    except Exception as e:
        # For dev team troubleshooting
        logger.error(f'Error reading documentation: {str(e)}')
        raise e


def _parse_read_documentation_result(result: CallToolResult) -> List[KnowledgeResult]:
    if result.is_error:
        raise Exception(f'Tool call returned an error: {result.content}')

    if not result.content or len(result.content) == 0:
        raise Exception('Empty response from tool')

    content = result.content[0]
    if not isinstance(content, TextContent):
        raise Exception(f'Content is not text type: {type(content)}')

    result_content_json = json.loads(content.text)
    content_str = result_content_json['content']['result']

    # TODO: fix/update response structure
    results = [KnowledgeResult(rank=1, title='', url='', context=content_str)]

    return results
