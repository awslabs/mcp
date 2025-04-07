#!/usr/bin/env python3
"""terraform MCP server implementation."""

import argparse
import sys
import os

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from mcp.server.fastmcp import FastMCP
from awslabs.terraform_mcp_server.impl.resources import (
    terraform_aws_provider_resources_listing_impl,
    terraform_awscc_provider_resources_listing_impl,
)
from awslabs.terraform_mcp_server.impl.tools import (
    execute_terraform_command_impl,
    search_aws_provider_docs_impl,
    search_awscc_provider_docs_impl,
    search_specific_aws_ia_modules_impl,
    run_checkov_scan_impl,
    run_checkov_fix_impl,
)
from awslabs.terraform_mcp_server.models import (
    ModuleSearchResult,
    ProviderDocsResult,
    TerraformExecutionRequest,
    TerraformExecutionResult,
    CheckovScanRequest,
    CheckovScanResult,
    CheckovFixRequest,
    CheckovFixResult,
)
from awslabs.terraform_mcp_server.static import MCP_INSTRUCTIONS, TERRAFORM_WORKFLOW_GUIDE, AWS_TERRAFORM_BEST_PRACTICES
from typing import List, Optional


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


@mcp.tool(name='SearchAwsccProviderDocs')
async def search_awscc_provider_docs(
    resource_type: str, attribute: Optional[str] = None
) -> List[ProviderDocsResult]:
    """Search AWSCC provider documentation for resources and attributes.

    This tool searches the Terraform AWSCC provider documentation for information about
    specific resource types and their attributes.

    Parameters:
        resource_type: AWSCC resource type (e.g., 'awscc_s3_bucket', 'awscc_lambda_function')
        attribute: Optional specific attribute to search for

    Returns:
        A list of matching documentation entries with details
    """
    return await search_awscc_provider_docs_impl(resource_type, attribute)


@mcp.tool(name='SearchSpecificAwsIaModules')
async def search_specific_aws_ia_modules(query: str = "") -> List[ModuleSearchResult]:
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
    name='terraform_workflow_guide',
    uri='terraform://workflow_guide',
    description='Guide for Terraform workflow commands and best practices',
    mime_type='text/markdown',
)
async def terraform_workflow_guide() -> str:
    """Provides guidance on Terraform workflow commands."""
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
