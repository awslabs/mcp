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
from ..knowledge_models import CDKToolResponse, KnowledgeResult
from dataclasses import asdict
from fastmcp.tools.tool_transform import forward
from mcp.types import TextContent
from typing import List


def parse_read_result(result) -> List[KnowledgeResult]:
    """Parse read documentation result from remote MCP server.

    Args:
        result: The result from the remote read_documentation tool (ToolResult from forward()).

    Returns:
        List of KnowledgeResult objects (single item with content).

    Raises:
        Exception: If the result is an error or has invalid format.
    """
    # Handle ToolResult from forward()
    if hasattr(result, 'isError') and result.isError:
        raise Exception(f'Tool call returned an error: {result.content}')

    # Get content from ToolResult
    content_list = result.content if hasattr(result, 'content') else [result]

    if not content_list or len(content_list) == 0:
        raise Exception('Empty response from tool')

    content = content_list[0]
    if not isinstance(content, TextContent):
        raise Exception(f'Content is not text type: {type(content)}')

    result_content_json = json.loads(content.text)
    content_str = result_content_json['content']['result']

    # Return as single KnowledgeResult with content
    results = [KnowledgeResult(rank=1, title='', url='', context=content_str)]

    return results


def transform_read_result(next_step_guidance: str):
    """Create a transformer for read documentation results.

    Args:
        next_step_guidance: Guidance message to include in response.

    Returns:
        An async transformer function.
    """

    async def transformer(**kwargs) -> str:
        """Transform read documentation result from remote MCP server.

        Returns:
            JSON string with CDKToolResponse format.
        """
        # Invoke the remote tool and get the result
        # https://gofastmcp.com/patterns/tool-transformation#passing-arguments-with-kwargs
        result = await forward(**kwargs)

        # Transform to the required format
        knowledge_response = parse_read_result(result)
        response = CDKToolResponse(
            knowledge_response=knowledge_response, next_step_guidance=next_step_guidance
        )
        return json.dumps(asdict(response))

    return transformer
