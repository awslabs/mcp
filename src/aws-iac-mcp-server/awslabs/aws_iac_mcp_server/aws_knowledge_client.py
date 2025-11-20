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
from .knowledge_models import KnowledgeResponse, KnowledgeResult
from fastmcp.client import Client
from fastmcp.client.client import CallToolResult
from mcp.types import TextContent
from typing import Optional


class AWSKnowledgeClient:
    """Client for interacting with AWS Knowledge MCP server."""

    def __init__(self, endpoint: Optional[str] = None):
        """Initialize the AWS Knowledge client.
        
        Args:
            endpoint: Optional endpoint URL for the knowledge service.
        """
        self.endpoint = endpoint or os.environ.get(
            'KNOWLEDGE_MCP_ENDPOINT', 'https://knowledge-mcp.global.api.aws'
        )
        self.search_tool = 'aws___search_documentation'
        self.read_tool = 'aws___read_documentation'

    async def search_documentation(
        self, search_phrase: str, topic: str, limit: int = 10
    ) -> KnowledgeResponse:
        """Search AWS documentation.
        
        Args:
            search_phrase: The search query.
            topic: The topic to search within.
            limit: Maximum number of results to return.
            
        Returns:
            KnowledgeResponse containing search results.
        """
        try:
            aws_knowledge_mcp_client = Client(self.endpoint)

            async with aws_knowledge_mcp_client:
                request = {'search_phrase': search_phrase, 'limit': limit, 'topics': [topic]}

                result = await aws_knowledge_mcp_client.call_tool(self.search_tool, request)
                return self._parse_search_result(result)

        except Exception as e:
            return KnowledgeResponse(error=str(e), results=[])

    def _parse_search_result(self, result: CallToolResult) -> KnowledgeResponse:
        try:
            if result.is_error:
                error_msg = f'Tool call returned an error: {result.content}'
                return KnowledgeResponse(error=error_msg, results=[])

            if not result.content or len(result.content) == 0:
                return KnowledgeResponse(error='Empty response from tool', results=[])

            content = result.content[0]
            if not isinstance(content, TextContent):
                error_msg = f'Content is not text type: {type(content)}'
                return KnowledgeResponse(error=error_msg, results=[])

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

            return KnowledgeResponse(error=None, results=results)

        except json.JSONDecodeError as e:
            error_msg = f'Failed to parse JSON response: {str(e)}'
            return KnowledgeResponse(error=error_msg, results=[])
        except (KeyError, IndexError) as e:
            error_msg = f'Unexpected response structure: {str(e)}'
            return KnowledgeResponse(error=error_msg, results=[])
        except Exception as e:
            error_msg = f'Error parsing result: {str(e)}'
            return KnowledgeResponse(error=error_msg, results=[])
