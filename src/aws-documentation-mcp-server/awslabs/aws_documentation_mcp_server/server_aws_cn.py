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
"""awslabs AWS China Documentation MCP Server implementation."""

import httpx
import re
from awslabs.aws_documentation_mcp_server.server_utils import (
    DEFAULT_USER_AGENT,
    read_documentation_impl,
)

# Import utility functions
from awslabs.aws_documentation_mcp_server.util import (
    extract_content_from_html,
    format_documentation_result,
    is_html_content,
)
from loguru import logger
from mcp.server.fastmcp import Context, FastMCP
from pydantic import AnyUrl, Field
from typing import Union


mcp = FastMCP(
    'awslabs.aws-documentation-mcp-server',
    instructions="""
    # AWS China Documentation MCP Server

    This server provides tools to access public AWS China documentation, and get service differences between AWS China and global regions.

    ## Best Practices

    - Always use `get_available_services` first to checkout available services and their documentation URLs
    - If a service is available, checkout the documentation URL for that service to see the feature differences and other documentation URLs
    - For long documentation pages, make multiple calls to `read_documentation` with different `start_index` values for pagination
    - For very long documents (>30,000 characters), stop reading if you've found the needed information
    - Always cite the documentation URL when providing information to users

    ## Tool Selection Guide

    - Use `get_available_services` when: You need to know what services are available in AWS China
    - Use `read_documentation` when: You have a specific documentation URL and need its content
    """,
    dependencies=[
        'pydantic',
        'httpx',
        'beautifulsoup4',
    ],
)


@mcp.tool()
async def read_documentation(
    ctx: Context,
    url: Union[AnyUrl, str] = Field(description='URL of the AWS China documentation page to read'),
    max_length: int = Field(
        default=5000,
        description='Maximum number of characters to return.',
        gt=0,
        lt=1000000,
    ),
    start_index: int = Field(
        default=0,
        description='On return output starting at this character index, useful if a previous fetch was truncated and more content is required.',
        ge=0,
    ),
) -> str:
    """Fetch and convert an AWS China documentation page to markdown format.

    ## Usage

    This tool retrieves the content of an AWS China documentation page and converts it to markdown format.
    For long documents, you can make multiple calls with different start_index values to retrieve
    the entire content in chunks.

    ## URL Requirements

    - Must be from the docs.amazonaws.cn domain
    - Must end with .html

    ## Example URLs

    - https://docs.amazonaws.cn/en_us/AmazonS3/latest/userguide/bucketnamingrules.html
    - https://docs.amazonaws.cn/en_us/lambda/latest/dg/lambda-invocation.html

    ## Output Format

    The output is formatted as markdown text with:
    - Preserved headings and structure
    - Code blocks for examples
    - Lists and tables converted to markdown format

    ## Handling Long Documents

    If the response indicates the document was truncated, you have several options:

    1. **Continue Reading**: Make another call with start_index set to the end of the previous response
    2. **Stop Early**: For very long documents (>30,000 characters), if you've already found the specific information needed, you can stop reading

    Args:
        ctx: MCP context for logging and error handling
        url: URL of the AWS China documentation page to read
        max_length: Maximum number of characters to return
        start_index: On return output starting at this character index

    Returns:
        Markdown content of the AWS China documentation
    """
    # Validate that URL is from docs.amazonaws.cn and ends with .html
    url_str = str(url)
    if not re.match(r'^https?://docs\.amazonaws\.cn/', url_str):
        error_msg = f'Invalid URL: {url_str}. URL must be from the docs.amazonaws.cn domain'
        await ctx.error(error_msg)
        return error_msg
    if not url_str.endswith('.html'):
        error_msg = f'Invalid URL: {url_str}. URL must end with .html'
        await ctx.error(error_msg)
        return error_msg

    return await read_documentation_impl(ctx, url_str, max_length, start_index)


@mcp.tool()
async def get_available_services(
    ctx: Context,
) -> str:
    """Fetch available services from AWS China documentation.

    ## Usage

    Available services in AWS China are different from global AWS services.
    This tool retrieves a list of available services and their documentation URLs.

    ## Output Format

    The output is formatted as markdown text with:
    - Preserved headings and structure
    - Code blocks for examples
    - Lists and tables converted to markdown format

    Args:
        ctx: MCP context for logging and error handling

    Returns:
        Markdown content of the AWS China documentation about available services
    """
    url_str = 'https://docs.amazonaws.cn/en_us/aws/latest/userguide/services.html'
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                url_str,
                follow_redirects=True,
                headers={'User-Agent': DEFAULT_USER_AGENT},
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

    # Format the content without truncation
    MAX_DOCUMENTATION_LENGTH = 2**1000
    result = format_documentation_result(
        url_str, content, start_index=0, max_length=MAX_DOCUMENTATION_LENGTH
    )

    return result


def main():
    """Run the MCP server with CLI argument support."""
    # Log startup information
    logger.info('Starting AWS China Documentation MCP Server')

    mcp.run()


if __name__ == '__main__':
    main()
