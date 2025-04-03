#!/usr/bin/env python3
"""terraform MCP server implementation."""

import argparse
from mcp.server.fastmcp import FastMCP
from terraform_mcp_server.impl.resources import (
    terraform_aws_modules_listing_impl,
    terraform_aws_provider_resources_listing_impl,
)
from terraform_mcp_server.impl.tools import (
    execute_terraform_command_impl,
    search_aws_provider_docs_impl,
    search_terraform_aws_modules_impl,
)
from terraform_mcp_server.models import (
    ModuleSearchResult,
    ProviderDocsResult,
    TerraformExecutionRequest,
    TerraformExecutionResult,
)
from terraform_mcp_server.static import MCP_INSTRUCTIONS, TERRAFORM_WORKFLOW_GUIDE
from typing import List, Optional


mcp = FastMCP(
    'terraform_mcp_server',
    instructions=f'{MCP_INSTRUCTIONS}',
    dependencies=['pydantic', 'loguru', 'requests', 'beautifulsoup4'],
)


# * Tools
@mcp.tool(name='ExecuteTerraformCommand')
async def execute_terraform_command(
    request: TerraformExecutionRequest,
) -> TerraformExecutionResult:
    """Execute Terraform workflow commands against an AWS account.

    This tool runs Terraform commands (init, plan, validate, apply, destroy) in the
    specified working directory, with optional variables and region settings.

    Parameters:
        request: Details about the Terraform command to execute

    Returns:
        A TerraformExecutionResult object containing command output and status
    """
    return await execute_terraform_command_impl(request)


@mcp.tool(name='SearchTerraformAwsModules')
async def search_terraform_aws_modules(query: str, limit: int = 3) -> List[ModuleSearchResult]:
    """Search for AWS Terraform modules in the Terraform Registry.

    This tool searches the Terraform Registry for AWS modules that match the query
    and returns comprehensive information about them, including README content.

    Parameters:
        query: Search term for modules (e.g., "vpc", "ecs", "lambda")
        limit: Maximum number of results to return (default: 3)

    Returns:
        A list of matching modules with their details, including:
        - Basic module information (name, namespace, version)
        - Module documentation (README content)
        - Input and output parameter counts
    """
    return await search_terraform_aws_modules_impl(query, limit)


@mcp.tool(name='SearchAwsProviderDocs')
async def search_aws_provider_docs(
    resource_type: str, attribute: Optional[str] = None
) -> List[ProviderDocsResult]:
    """Search AWS provider documentation for resources and attributes.

    This tool searches the Terraform AWS provider documentation for information about
    specific resource types and their attributes.

    Parameters:
        resource_type: AWS resource type (e.g., 'aws_s3_bucket', 'aws_lambda_function')
        attribute: Optional specific attribute to search for

    Returns:
        A list of matching documentation entries with details
    """
    return await search_aws_provider_docs_impl(resource_type, attribute)


# * Resources
@mcp.resource(
    name='terraform_workflow_guide',
    uri='terraform://workflow_guide',
    description='Guide for Terraform workflow commands and best practices',
    mime_type='text/markdown',
)
async def terraform_workflow_guide() -> str:
    """Provides guidance on Terraform workflow commands."""
    return f'{TERRAFORM_WORKFLOW_GUIDE}'


@mcp.resource(
    name='terraform_aws_modules_listing',
    uri='terraform://aws_modules_listing',
    description='Comprehensive listing of terraform-aws-modules with descriptions and statistics',
    mime_type='text/markdown',
)
async def terraform_aws_modules_listing() -> str:
    """Provides an up-to-date listing of all terraform-aws-modules."""
    return await terraform_aws_modules_listing_impl()


@mcp.resource(
    name='terraform_aws_provider_resources_listing',
    uri='terraform://aws_provider_resources_listing',
    description='Comprehensive listing of AWS provider resources and data sources by service category',
    mime_type='text/markdown',
)
async def terraform_aws_provider_resources_listing() -> str:
    """Provides an up-to-date categorized listing of all AWS provider resources and data sources."""
    return await terraform_aws_provider_resources_listing_impl()


def main():
    """Run the MCP server with CLI argument support."""
    parser = argparse.ArgumentParser(description='A Model Context Protocol (MCP) server')
    parser.add_argument('--sse', action='store_true', help='Use SSE transport')
    parser.add_argument('--port', type=int, default=8888, help='Port to run the server on')

    args = parser.parse_args()

    # Run server with appropriate transport
    if args.sse:
        mcp.settings.port = args.port
        mcp.run(transport='sse')
    else:
        mcp.run()


if __name__ == '__main__':
    main()
