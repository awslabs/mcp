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

"""awslabs frontend MCP Server implementation."""

from awslabs.frontend_mcp_server.utils.file_utils import load_markdown_file
from awslabs.frontend_mcp_server.consts import DEFAULT_SEARCH_LIMIT
from loguru import logger
from mcp.server.fastmcp import FastMCP
from pydantic import Field
from typing import Literal
from .tools import search_amplify_documentation


mcp = FastMCP(
    'awslabs.frontend-mcp-server',
    instructions='The Frontend MCP Server provides specialized tools for modern web application development. It offers guidance on React application setup, optimistic UI implementation, and authentication integration. Use these tools when you need expert advice on frontend development best practices.',
    dependencies=[
        'pydantic',
        'loguru',
    ],
)


@mcp.tool(name='GetReactDocsByTopic')
async def get_react_docs_by_topic(
    topic: Literal[
        'essential-knowledge',
        'troubleshooting'
    ] = Field(
        ...,
        description='The topic of React documentation to retrieve. Topics include: essential-knowledge, troubleshooting.',
    ),
) -> str:
    """Get specific AWS web application UI setup documentation by topic.

    Parameters:
        topic: The topic of React documentation to retrieve.
          - "essential-knowledge": Essential knowledge for working with React applications.
          - "troubleshooting": Common issues and solutions when generating code.
          - "amplify-gen2": Search the amplify gen2 documentation for code examples and best practices. 

    Returns:
        A markdown string containing the requested documentation
    """
    match topic:
        case 'essential-knowledge':
            return load_markdown_file('essential-knowledge.md')
        case 'troubleshooting':
            return load_markdown_file('troubleshooting.md')
        case _:
            raise ValueError(
                f'Invalid topic: {topic}. Must be one of: essential-knowledge, troubleshooting'
            )

@mcp.tool(name='SearchAmplifyGen2Docs')
def search_amplify_gen2_documentation_tool(query: str, limit: int = DEFAULT_SEARCH_LIMIT) -> str:
    """Search Amplify Gen2 documentation comprehensively across official docs and sample repositories.

    Args:
        query: Search query string (e.g., "authentication", "data modeling", "file upload")
        limit: Maximum number of results to return (default: 10)

    Returns:
        Comprehensive search results with URLs, relevance scores, and code examples
    """
    results = search_amplify_documentation(query, limit)
    
    # Format results as a readable string
    if not results:
        return f"No documentation found for query: '{query}'"
    
    formatted_results = []
    for i, result in enumerate(results, 1):
        formatted_result = f"""
{i}. **{result.get('title', 'Untitled')}**
   - Path: {result.get('path', 'N/A')}
   - URL: {result.get('url', 'N/A')}
   - Relevance: {result.get('relevance_score', 0):.2f}
   - Preview: {result.get('content_preview', 'No preview available')[:200]}...
"""
        formatted_results.append(formatted_result)
    
    return f"Found {len(results)} results for '{query}':\n" + "\n".join(formatted_results)

def main():
    """Run the MCP server with CLI argument support."""
    mcp.run()

    logger.trace('A trace message.')
    logger.debug('A debug message.')
    logger.info('An info message.')
    logger.success('A success message.')
    logger.warning('A warning message.')
    logger.error('An error message.')
    logger.critical('A critical message.')


if __name__ == '__main__':
    main()
