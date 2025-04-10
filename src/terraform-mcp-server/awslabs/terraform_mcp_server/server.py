#!/usr/bin/env python3
"""terraform MCP server implementation."""

import argparse
import os
import sys
from typing import List, Optional


# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from awslabs.terraform_mcp_server.impl.resources import (
    terraform_aws_provider_resources_listing_impl,
    terraform_awscc_provider_resources_listing_impl,
)
from awslabs.terraform_mcp_server.impl.tools import (
    execute_terraform_command_impl,
    run_checkov_fix_impl,
    run_checkov_scan_impl,
    search_aws_provider_docs_impl,
    search_awscc_provider_docs_impl,
    search_specific_aws_ia_modules_impl,
)
from awslabs.terraform_mcp_server.models import (
    CheckovFixRequest,
    CheckovFixResult,
    CheckovScanRequest,
    CheckovScanResult,
    ModuleSearchResult,
    ProviderDocsResult,
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
    resource_type: str, attribute: Optional[str] = None, kind: str = 'both'
) -> List[ProviderDocsResult]:
    """Search AWS provider documentation for resources and attributes.

    This tool searches the Terraform AWS provider documentation for information about
    specific resource types and their attributes.

    Use the 'kind' parameter to specify if you are looking for information about provider resources, data sources, or both.

    Parameters:
        resource_type: AWS resource type (e.g., 'aws_s3_bucket', 'aws_lambda_function')
        attribute: Optional specific attribute to search for
        kind: Type of documentation to search - 'resource', 'data_source', or 'both' (default)

    Returns:
        A list of matching documentation entries with details
    """
    return await search_aws_provider_docs_impl(resource_type, attribute, kind)


@mcp.tool(name='SearchAwsccProviderDocs')
async def search_awscc_provider_docs(
    resource_type: str, attribute: Optional[str] = None
) -> List[ProviderDocsResult]:
    """Search AWSCC provider documentation for resources and attributes.

    This tool searches the Terraform AWSCC provider documentation for information about
    specific resource types and their attributes.

    Use the 'kind' parameter to specify if you are looking for information about provider resources, data sources, or both.

    Parameters:
        resource_type: AWSCC resource type (e.g., 'awscc_s3_bucket', 'awscc_lambda_function')
        attribute: Optional specific attribute to search for

    Returns:
        A list of matching documentation entries with details
    """
    return await search_awscc_provider_docs_impl(resource_type, attribute)


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

    Parameters:
        query: Optional search term to filter modules (empty returns all four modules)

    Returns:
        A list of matching modules with their details, including:
        - Basic module information (name, namespace, version)
        - Module documentation (README content)
        - Input and output parameter counts
        - Variables from variables.tf with descriptions and default values
        - Submodules information
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
            - auto_fix: Whether to attempt automatic fixes (default: false)

    Returns:
        A CheckovScanResult object containing scan results and identified vulnerabilities
    """
    return await run_checkov_scan_impl(request)


@mcp.tool(name='FixCheckovVulnerabilities')
async def fix_checkov_vulnerabilities(request: CheckovFixRequest) -> CheckovFixResult:
    """Fix security vulnerabilities found by Checkov in Terraform code.

    This tool attempts to automatically fix security and compliance issues identified
    by Checkov in Terraform code. It applies recommended fixes for supported checks.

    Parameters:
        request: Details about the vulnerabilities to fix, including:
            - working_directory: Directory containing Terraform files to fix
            - vulnerability_ids: List of vulnerability IDs to fix
            - backup_files: Whether to create backup files before fixing

    Returns:
        A CheckovFixResult object containing fix results, including which vulnerabilities
        were successfully fixed and which could not be automatically remediated
    """
    return await run_checkov_fix_impl(request)


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
search_tool = mcp._tool_manager.get_tool('SearchAwsProviderDocs')
search_tool.parameters['properties']['resource_type']['description'] = (
    'AWS resource type (e.g., aws_s3_bucket, aws_lambda_function)'
)
search_tool.parameters['properties']['attribute']['description'] = (
    'Optional specific attribute to search for within the resource type documentation'
)
search_tool.parameters['properties']['kind']['description'] = (
    "Type of documentation to search - 'resource', 'data_source', or 'both' (default)"
)

# SearchAwsccProviderDocs
awscc_docs_tool = mcp._tool_manager.get_tool('SearchAwsccProviderDocs')
awscc_docs_tool.parameters['properties']['resource_type']['description'] = (
    'AWSCC resource type (e.g., awscc_s3_bucket, awscc_lambda_function)'
)
awscc_docs_tool.parameters['properties']['attribute']['description'] = (
    'Optional specific attribute to search for within the resource type documentation'
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
    if 'auto_fix' in props:
        props['auto_fix']['description'] = 'Whether to attempt automatic fixes (default: false)'

# FixCheckovVulnerabilities
checkov_fix_tool = mcp._tool_manager.get_tool('FixCheckovVulnerabilities')
checkov_fix_tool.parameters['properties']['request']['description'] = (
    'Details about the vulnerabilities to fix'
)

# Since request is a complex object with nested properties, update its schema
if 'properties' in checkov_fix_tool.parameters['properties']['request']:
    props = checkov_fix_tool.parameters['properties']['request']['properties']
    if 'working_directory' in props:
        props['working_directory']['description'] = 'Directory containing Terraform files to fix'
    if 'vulnerability_ids' in props:
        props['vulnerability_ids']['description'] = 'List of vulnerability IDs to fix'
    if 'backup_files' in props:
        props['backup_files']['description'] = 'Whether to create backup files before fixing'


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
