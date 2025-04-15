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
import argparse
# import dotenv
import json
import loguru
import sys
from awslabs.core_mcp_server.static import PROMPT_UNDERSTANDING
from mcp.server.fastmcp import FastMCP
from typing import Dict, List, TypedDict



class ContentItem(TypedDict):
    """A TypedDict representing a single content item in an MCP response.

    This class defines the structure for content items used in MCP server responses.
    Each content item contains a type identifier and the actual content text.

    Attributes:
        type (str): The type identifier for the content (e.g., 'text', 'error')
        text (str): The actual content text
    """

    type: str
    text: str


class McpResponse(TypedDict, total=False):
    """A TypedDict representing an MCP server response.

    This class defines the structure for responses returned by MCP server tools.
    It supports optional fields through total=False, allowing responses to omit
    the isError field when not needed.

    Attributes:
        content (List[ContentItem]): List of content items in the response
        isError (bool, optional): Flag indicating if the response represents an error
    """

    content: List[ContentItem]
    isError: bool


# Set up logging
logger = loguru.logger

logger.remove()
logger.add(sys.stderr, level='DEBUG')


mcp = FastMCP(
    'mcp-core MCP server.  This is the starting point for all solutions created',
    dependencies=[
        'loguru',
    ],
)


@mcp.tool(name='prompt_understanding')
async def get_prompt_understanding() -> str:
    """MCP-CORE Prompt Understanding.

    ALWAYS Use this tool first to understand the user's query and translate it into AWS expert advice.
    """
    return PROMPT_UNDERSTANDING



def main() -> None:
    """Run the MCP server."""
    parser = argparse.ArgumentParser(
        description='A Model Context Protocol (MCP) server for mcp-core'
    )
    parser.add_argument('--sse', action='store_true', help='Use SSE transport')
    parser.add_argument('--port', type=int, default=8888, help='Port to run the server on')
    args = parser.parse_args()

    # Run server with appropriate transport
    if args.sse:
        mcp.settings.port = args.port
        mcp.run(transport='sse')
    else:
        mcp.run()


if __name__ == '__main__':  # pragma: no cover
    main()
