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

"""AWS Bedrock Data Automation MCP Server implementation."""

from awslabs.aws_bedrock_data_automation_mcp_server.helpers import (
    get_project,
    invoke_data_automation_and_get_results,
    list_projects,
)
from loguru import logger
from mcp.server.fastmcp import FastMCP
from pydantic import Field
from typing import Annotated


mcp = FastMCP(
    'awslabs.aws-bedrock-data-automation-mcp-server',
    instructions="""
    AWS Bedrock Data Automation MCP Server provides tools to interact with Amazon Bedrock Data Automation.

    This server enables you to:
    - List available data automation projects
    - Get details about specific data automation projects
    - Analyze assets (documents, images, videos, audio) using data automation projects

    Use these tools to extract insights from unstructured content using Amazon Bedrock Data Automation.
    """,
    dependencies=[
        'pydantic',
        'loguru',
        'boto3',
    ],
)


@mcp.tool(name='getprojects')
async def get_projects_tool() -> dict:
    """Get a list of data automation projects.

    ## Usage

    Use this tool to retrieve a list of all available data automation projects in your account.
    This is typically the first step when working with data automation to discover what projects
    are available for use.

    ## Example

    ```python
    # Get all available data automation projects
    projects = await getprojects()
    ```

    ## Output Format

    The output is a dictionary containing:
    - `projects`: A list of project objects, each with:
      - `projectArn`: The Amazon Resource Name (ARN) of the project
      - `projectName`: The name of the project
      - `projectStage`: The stage of the project (e.g., DRAFT, PUBLISHED)
      - `creationTime`: When the project was created
      - `lastModifiedTime`: When the project was last modified

    Returns:
        A dict containing a list of data automation projects.
    """
    try:
        projects = await list_projects()
        return {'projects': projects}
    except Exception as e:
        logger.error(f'Error listing projects: {e}')
        raise ValueError(f'Error listing projects: {str(e)}')


@mcp.tool(name='getprojectdetails')
async def get_project_details_tool(
    projectArn: Annotated[str, Field(description='The ARN of the project')],
) -> dict:
    """Get details of a data automation project.

    ## Usage

    Use this tool to retrieve detailed information about a specific data automation project
    after you've identified its ARN using the `getprojects` tool.

    ## Example

    ```python
    # Get details for a specific project
    project_details = await getprojectdetails(
        projectArn='arn:aws:bedrock:us-west-2:123456789012:data-automation-project/my-project'
    )
    ```

    ## Output Format

    The output is a dictionary containing comprehensive project details including:
    - Basic project information (name, ARN, stage)
    - Configuration settings
    - Input/output specifications
    - Associated blueprints
    - Creation and modification timestamps

    Args:
        projectArn: The ARN of the project.

    Returns:
        The project details.
    """
    try:
        project_details = await get_project(projectArn)
        return project_details
    except Exception as e:
        logger.error(f'Error getting project details: {e}')
        raise ValueError(f'Error getting project details: {str(e)}')


@mcp.tool(name='analyzeasset')
async def analyze_asset_tool(
    assetPath: Annotated[str, Field(description='The path to the asset')],
    projectArn: Annotated[
        str | None,
        Field(description='The ARN of the project. Uses default public project if not provided'),
    ] = None,
) -> dict:
    """Analyze an asset using a data automation project.

    This tool extracts insights from unstructured content (documents, images, videos, audio)
    using Amazon Bedrock Data Automation.

    ## Usage

    Use this tool to analyze various types of assets (documents, images, videos, audio files)
    using a data automation project. You can specify a particular project to use for analysis
    or let the system use a default public project if none is provided.

    ## Supported Asset Types

    - Documents: PDF, DOCX, TXT, etc.
    - Images: JPG, PNG, etc.
    - Videos: MP4, MOV, etc.
    - Audio: MP3, WAV, etc.

    ## Examples

    ```python
    # Analyze a document using the default public project
    results = await analyzeasset(assetPath='/path/to/document.pdf')

    # Analyze an image using a specific project
    results = await analyzeasset(
        assetPath='/path/to/image.jpg',
        projectArn='arn:aws:bedrock:us-west-2:123456789012:data-automation-project/my-project',
    )
    ```

    ## Output Format

    The output is a dictionary containing the analysis results, which vary based on:
    - The type of asset being analyzed
    - The capabilities of the data automation project used
    - The specific insights extracted (text, entities, sentiment, etc.)

    Args:
        assetPath: The path to the asset.
        projectArn: The ARN of the project. Uses default public project if not provided.

    Returns:
        The analysis results.
    """
    try:
        results = await invoke_data_automation_and_get_results(assetPath, projectArn)
        return results if results is not None else {}
    except Exception as e:
        logger.error(f'Error analyzing asset: {e}')
        raise ValueError(f'Error analyzing asset: {str(e)}')


def main():
    """Run the MCP server with CLI argument support."""
    logger.info('Starting AWS Bedrock Data Automation MCP Server')
    mcp.run()


if __name__ == '__main__':
    main()
