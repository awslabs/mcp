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

"""AWS Bedrock Data Automation MCP Server implementation."""

from awslabs.aws_bedrock_data_automation_mcp_server.helpers import (
    get_project,
    invoke_data_automation_and_get_results,
    list_projects,
)
from loguru import logger
from mcp.server.fastmcp import FastMCP
from typing import Optional


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
    projectArn: str,
) -> dict:
    """Get details of a data automation project.

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
    assetPath: str,
    projectArn: Optional[str] = None,
) -> dict:
    """Analyze an asset using a data automation project.

    This tool extracts insights from unstructured content (documents, images, videos, audio)
    using Amazon Bedrock Data Automation.

    Args:
        assetPath: The path to the asset.
        projectArn: The ARN of the project. Uses default public project if not provided.

    Returns:
        The analysis results.
    """
    try:
        results = await invoke_data_automation_and_get_results(assetPath, projectArn)
        if results is None:
            raise ValueError('Data automation job failed or returned no results')
        return results
    except Exception as e:
        logger.error(f'Error analyzing asset: {e}')
        raise ValueError(f'Error analyzing asset: {str(e)}')


def main():
    """Run the MCP server with CLI argument support."""
    logger.info('Starting AWS Bedrock Data Automation MCP Server')
    mcp.run()


if __name__ == '__main__':
    main()
