# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.

"""awslabs frontend MCP Server implementation."""

from awslabs.frontend_mcp_server.utils.file_utils import load_markdown_file
from loguru import logger
from mcp.server.fastmcp import FastMCP
from pydantic import Field
from typing import Literal


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
        'troubleshooting',
    ] = Field(
        ...,
        description='The topic of React documentation to retrieve. Topics include: essential-knowledge, troubleshooting, basic-ui, authentication, routing, customizing, creating-components.',
    ),
) -> str:
    """Get specific AWS web application UI setup documentation by topic.

    Parameters:
        topic: The topic of React documentation to retrieve.
          - "essential-knowledge": Essential knowledge for working with React applications.
          - "troubleshooting": Common issues and solutions when generating code.

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
                f'Invalid topic: {topic}. Must be one of: essential-knowledge, basic-ui, authentication, routing, customizing, creating-components'
            )


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
