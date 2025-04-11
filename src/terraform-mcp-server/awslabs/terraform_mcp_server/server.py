#!/usr/bin/env python3
"""terraform MCP server implementation."""

import argparse
import os
import sys
from typing import List


# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from awslabs.terraform_mcp_server.impl.resources import (
    terraform_aws_provider_resources_listing_impl,
    terraform_awscc_provider_resources_listing_impl,
)
from awslabs.terraform_mcp_server.impl.tools import (
    execute_terraform_command_impl,
    run_checkov_scan_impl,
    search_aws_provider_docs_impl,
    search_awscc_provider_docs_impl,
    search_specific_aws_ia_modules_impl,
)
from awslabs.terraform_mcp_server.models import (
    CheckovScanRequest,
    CheckovScanResult,
    ModuleSearchResult,
    TerraformAWSProviderDocsResult,
    TerraformAWSCCProviderDocsResult,
    TerraformExecutionRequest,
    TerraformExecutionResult,
)
from awslabs.terraform_mcp_server.static import (
    AWS_TERRAFORM_BEST_PRACTICES,
    MCP_INSTRUCTIONS,
    TERRAFORM_WORKFLOW_GUIDE,
)
from mcp.server.fastmcp import FastMCP


mcp = FastMCP(
    'terraform_mcp_server',
    instructions=f'{MCP_INSTRUCTIONS}',
    dependencies=['pydantic', 'loguru', 'requests', 'beautifulsoup4', 'PyPDF2'],
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


@mcp.tool(name='SearchAwsProviderDocs')
async def search_aws_provider_docs(
    asset_name: str, asset_type: str = 'resource'
) -> List[TerraformAWSProviderDocsResult]:
    """Search AWS provider documentation for resources and attributes.

    This tool searches the Terraform AWS provider documentation for information about
    a specific asset in the AWS Provider Documentation, assets can be either resources or data sources. It retrieves comprehensive details including descriptions, example code snippets, argument references, and attribute references.

    Use the 'asset_type' parameter to specify if you are looking for information about provider resources, data sources, or both. Valid values are 'resource', 'data_source' or 'both'.
    
    The tool will automatically handle prefixes - you can search for either 'aws_s3_bucket' or 's3_bucket'.

    Examples:
        - To get documentation for an S3 bucket resource:
          search_aws_provider_docs(asset_name='aws_s3_bucket')
        
        - To search only for data sources:
          search_aws_provider_docs(asset_name='aws_ami', asset_type='data_source')
        
        - To search for both resource and data source documentation of a given name:
          search_aws_provider_docs(asset_name='aws_instance', asset_type='both')

    Parameters:
        asset_name: Name of the service (asset) to look for (e.g., 'aws_s3_bucket', 'aws_lambda_function')
        asset_type: Type of documentation to search - 'resource' (default), 'data_source', or 'both'

    Returns:
        A list of matching documentation entries with details including:
        - Resource name and description
        - URL to the official documentation
        - Example code snippets
        - Arguments with descriptions
        - Attributes with descriptions
    """
    return await search_aws_provider_docs_impl(asset_name, asset_type)


@mcp.tool(name='SearchAwsccProviderDocs')
async def search_awscc_provider_docs(
    asset_name: str, asset_type: str = 'resource'
) -> List[TerraformAWSCCProviderDocsResult]:
    """Search AWSCC provider documentation for resources and attributes.

    The AWSCC provider is based on the AWS Cloud Control API
    and provides a more consistent interface to AWS resources compared to the standard AWS provider.

    This tool searches the Terraform AWSCC provider documentation for information about
    a specific asset in the AWSCC Provider Documentation, assets can be either resources or data sources. It retrieves comprehensive details including descriptions, example code snippets, and schema references.

    Use the 'asset_type' parameter to specify if you are looking for information about provider resources, data sources, or both. Valid values are 'resource', 'data_source' or 'both'.
    
    The tool will automatically handle prefixes - you can search for either 'awscc_s3_bucket' or 's3_bucket'.

    Examples:
        - To get documentation for an S3 bucket resource:
          search_awscc_provider_docs(asset_name='awscc_s3_bucket')
          search_awscc_provider_docs(asset_name='awscc_s3_bucket', asset_type='resource')

        - To search only for data sources:
          search_aws_provider_docs(asset_name='awscc_appsync_api', kind='data_source')
        
        - To search for both resource and data source documentation of a given name:
          search_aws_provider_docs(asset_name='awscc_appsync_api', kind='both')
        
        - Search of a resource without the prefix:
          search_awscc_provider_docs(resource_type='ec2_instance')

    Parameters:
        asset_name: Name of the AWSCC Provider resource or data source to look for (e.g., 'awscc_s3_bucket', 'awscc_lambda_function')
        asset_type: Type of documentation to search - 'resource' (default), 'data_source', or 'both'. Some resources and data sources share the same name

    Returns:
        A list of matching documentation entries with details including:
        - Resource name and description
        - URL to the official documentation
        - Example code snippets
        - Schema information (required, optional, read-only, and nested structures attributes)
    """
    return await search_awscc_provider_docs_impl(asset_name, asset_type)


@mcp.tool(name='SearchSpecificAwsIaModules')
async def search_specific_aws_ia_modules(query: str = '') -> List[ModuleSearchResult]:
    """Search for specific AWS-IA Terraform modules.

    This tool checks for information about four specific AWS-IA modules:
    - aws-ia/bedrock/aws - Amazon Bedrock module for generative AI applications
    - aws-ia/opensearch-serverless/aws - OpenSearch Serverless collection for vector search
    - aws-ia/sagemaker-endpoint/aws - SageMaker endpoint deployment module
    - aws-ia/serverless-streamlit-app/aws - Serverless Streamlit application deployment

    It returns detailed information about these modules, including their README content,
    variables.tf content, and submodules when available.

    The search is performed across module names, descriptions, README content, and variable
    definitions. This allows you to find modules based on their functionality or specific
    configuration options.

    Examples:
        - To get information about all four modules:
          search_specific_aws_ia_modules()
        
        - To find modules related to Bedrock:
          search_specific_aws_ia_modules(query='bedrock')
        
        - To find modules related to vector search:
          search_specific_aws_ia_modules(query='vector search')
        
        - To find modules with specific configuration options:
          search_specific_aws_ia_modules(query='endpoint_name')

    Parameters:
        query: Optional search term to filter modules (empty returns all four modules)

    Returns:
        A list of matching modules with their details, including:
        - Basic module information (name, namespace, version)
        - Module documentation (README content)
        - Input and output parameter counts
        - Variables from variables.tf with descriptions and default values
        - Submodules information
        - Version details and release information
    """
    return await search_specific_aws_ia_modules_impl(query)


@mcp.tool(name='RunCheckovScan')
async def run_checkov_scan(request: CheckovScanRequest) -> CheckovScanResult:
    """Run Checkov security scan on Terraform code.

    This tool runs Checkov to scan Terraform code for security and compliance issues,
    identifying potential vulnerabilities and misconfigurations according to best practices.

    Checkov (https://www.checkov.io/) is an open-source static code analysis tool that
    can detect hundreds of security and compliance issues in infrastructure-as-code.

    Parameters:
        request: Details about the Checkov scan to execute, including:
            - working_directory: Directory containing Terraform files to scan
            - framework: Framework to scan (default: terraform)
            - check_ids: Optional list of specific check IDs to run
            - skip_check_ids: Optional list of check IDs to skip
            - output_format: Format for scan results (default: json)

    Returns:
        A CheckovScanResult object containing scan results and identified vulnerabilities
    """
    return await run_checkov_scan_impl(request)

# * Resources
@mcp.resource(
    name='terraform_development_workflow',
    uri='terraform://development_workflow',
    description='Terraform Development Workflow Guide with integrated validation and security scanning',
    mime_type='text/markdown',
)
async def terraform_development_workflow() -> str:
    """Provides guidance for developing Terraform code and integrates with Terraform workflow commands."""
    return f'{TERRAFORM_WORKFLOW_GUIDE}'


@mcp.resource(
    name='terraform_aws_provider_resources_listing',
    uri='terraform://aws_provider_resources_listing',
    description='Comprehensive listing of AWS provider resources and data sources by service category',
    mime_type='text/markdown',
)
async def terraform_aws_provider_resources_listing() -> str:
    """Provides an up-to-date categorized listing of all AWS provider resources and data sources."""
    return await terraform_aws_provider_resources_listing_impl()


@mcp.resource(
    name='terraform_awscc_provider_resources_listing',
    uri='terraform://awscc_provider_resources_listing',
    description='Comprehensive listing of AWSCC provider resources and data sources by service category',
    mime_type='text/markdown',
)
async def terraform_awscc_provider_resources_listing() -> str:
    """Provides an up-to-date categorized listing of all AWSCC provider resources and data sources."""
    return await terraform_awscc_provider_resources_listing_impl()


@mcp.resource(
    name='terraform_aws_best_practices',
    uri='terraform://aws_best_practices',
    description='AWS Terraform Provider Best Practices from AWS Prescriptive Guidance',
    mime_type='text/markdown',
)
async def terraform_aws_best_practices() -> str:
    """Provides AWS Terraform Provider Best Practices guidance."""
    return f'{AWS_TERRAFORM_BEST_PRACTICES}'


# Add parameter descriptions for tools
# SearchAwsProviderDocs
aws_docs_tool = mcp._tool_manager.get_tool('SearchAwsProviderDocs')
aws_docs_tool.parameters['properties']['asset_name']['description'] = (
    'Name of the AWS service (asset) to look for (e.g., "aws_s3_bucket", "aws_lambda_function")'
)
aws_docs_tool.parameters['properties']['asset_type']['description'] = (
    "Type of documentation to search - 'resource', 'data_source', or 'both' (default)"
)

# SearchAwsccProviderDocs
awscc_docs_tool = mcp._tool_manager.get_tool('SearchAwsccProviderDocs')
awscc_docs_tool.parameters['properties']['asset_name']['description'] = (
    'Name of the AWSCC service (asset) to look for (e.g., awscc_s3_bucket, awscc_lambda_function)'
)
awscc_docs_tool.parameters['properties']['asset_type']['description'] = (
    "Type of documentation to search - 'resource', 'data_source', or 'both' (default)"
)

# SearchSpecificAwsIaModules
modules_tool = mcp._tool_manager.get_tool('SearchSpecificAwsIaModules')
modules_tool.parameters['properties']['query']['description'] = (
    'Optional search term to filter modules (empty returns all four modules)'
)

# ExecuteTerraformCommand
terraform_tool = mcp._tool_manager.get_tool('ExecuteTerraformCommand')
terraform_tool.parameters['properties']['request']['description'] = (
    'Details about the Terraform command to execute'
)

# Since request is a complex object with nested properties, update its schema
if 'properties' in terraform_tool.parameters['properties']['request']:
    props = terraform_tool.parameters['properties']['request']['properties']
    if 'command' in props:
        props['command']['description'] = (
            'Terraform command to execute (init, plan, validate, apply, destroy)'
        )
    if 'working_directory' in props:
        props['working_directory']['description'] = 'Directory containing Terraform files'
    if 'variables' in props:
        props['variables']['description'] = 'Terraform variables to pass'
    if 'aws_region' in props:
        props['aws_region']['description'] = 'AWS region to use'
    if 'strip_ansi' in props:
        props['strip_ansi']['description'] = 'Whether to strip ANSI color codes from output'

# RunCheckovScan
checkov_scan_tool = mcp._tool_manager.get_tool('RunCheckovScan')
checkov_scan_tool.parameters['properties']['request']['description'] = (
    'Details about the Checkov scan to execute'
)

# Since request is a complex object with nested properties, update its schema
if 'properties' in checkov_scan_tool.parameters['properties']['request']:
    props = checkov_scan_tool.parameters['properties']['request']['properties']
    if 'working_directory' in props:
        props['working_directory']['description'] = 'Directory containing Terraform files to scan'
    if 'framework' in props:
        props['framework']['description'] = 'Framework to scan (terraform, cloudformation, etc.)'
    if 'check_ids' in props:
        props['check_ids']['description'] = 'Optional list of specific check IDs to run'
    if 'skip_check_ids' in props:
        props['skip_check_ids']['description'] = 'Optional list of check IDs to skip'
    if 'output_format' in props:
        props['output_format']['description'] = 'Format for scan results (default: json)'


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
