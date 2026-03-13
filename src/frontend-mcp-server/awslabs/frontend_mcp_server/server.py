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
from loguru import logger
from mcp.server.fastmcp import FastMCP
from pydantic import Field
from typing import Literal


DEPRECATION_NOTICE = (
    'DEPRECATION NOTICE: The Frontend MCP Server (awslabs.frontend-mcp-server) is '
    'deprecated and will no longer receive updates, bug fixes, or new features. '
    'This server only serves static React/Amplify documentation that modern AI assistants '
    'already have knowledge of. Consider using project-level documentation or Kiro specs instead.'
)

mcp = FastMCP(
    'awslabs.frontend-mcp-server',
    instructions=DEPRECATION_NOTICE
    + ' '
    + 'The Frontend MCP Server provides specialized tools for modern web application development. It offers guidance on React application setup, optimistic UI implementation, and authentication integration. Use these tools when you need expert advice on frontend development best practices.',
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
        description='The topic of React documentation to retrieve. Topics include: essential-knowledge, troubleshooting.',
    ),
) -> str:
    """[DEPRECATED] Get specific AWS web application UI setup documentation by topic.

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
                f'Invalid topic: {topic}. Must be one of: essential-knowledge, troubleshooting'
            )


def main():
    """Run the MCP server with CLI argument support."""
    import warnings

    warnings.warn(DEPRECATION_NOTICE, FutureWarning, stacklevel=2)
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
