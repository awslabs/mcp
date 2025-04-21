#!/usr/bin/env python3
"""terraform MCP server implementation."""

import argparse
from awslabs.terraform_mcp_server.impl.resources import (
    terraform_aws_provider_assets_listing_impl,
    terraform_awscc_provider_resources_listing_impl,
)
from awslabs.terraform_mcp_server.impl.tools import (
    execute_terraform_command_impl,
    run_checkov_scan_impl,
    search_aws_provider_docs_impl,
    search_awscc_provider_docs_impl,
    search_specific_aws_ia_modules_impl,
    search_user_provided_module_impl,
)
from awslabs.terraform_mcp_server.models import (
    CheckovScanRequest,
    CheckovScanResult,
    ModuleSearchResult,
    SearchUserProvidedModuleRequest,
    SearchUserProvidedModuleResult,
    TerraformAWSCCProviderDocsResult,
    TerraformAWSProviderDocsResult,
    TerraformExecutionRequest,
    TerraformExecutionResult,
)
from awslabs.terraform_mcp_server.static import (
    AWS_TERRAFORM_BEST_PRACTICES,
    MCP_INSTRUCTIONS,
    TERRAFORM_WORKFLOW_GUIDE,
)
from mcp.server.fastmcp import FastMCP
from pydantic import Field
from typing import Any, Dict, List, Literal, Optional


mcp = FastMCP(
    'terraform_mcp_server',
    instructions=f'{MCP_INSTRUCTIONS}',
    dependencies=[
        'pydantic',
        'loguru',
        'requests',
        'beautifulsoup4',
        'PyPDF2',
    ],
)


# * Tools
@mcp.tool(name='ExecuteTerraformCommand')
async def execute_terraform_command(
    command: Literal['init', 'plan', 'validate', 'apply', 'destroy'] = Field(
        ..., description='Terraform command to execute'
    ),
    working_directory: str = Field(..., description='Directory containing Terraform files'),
    variables: Optional[Dict[str, str]] = Field(None, description='Terraform variables to pass'),
    aws_region: Optional[str] = Field(None, description='AWS region to use'),
    strip_ansi: bool = Field(True, description='Whether to strip ANSI color codes from output'),
) -> TerraformExecutionResult:
    """Execute Terraform workflow commands against an AWS account.

    This tool runs Terraform commands (init, plan, validate, apply, destroy) in the
    specified working directory, with optional variables and region settings.

    Parameters:
        command: Terraform command to execute
        working_directory: Directory containing Terraform files
        variables: Terraform variables to pass
        aws_region: AWS region to use
        strip_ansi: Whether to strip ANSI color codes from output

    Returns:
        A TerraformExecutionResult object containing command output and status
    """
    request = TerraformExecutionRequest(
        command=command,
        working_directory=working_directory,
        variables=variables,
        aws_region=aws_region,
        strip_ansi=strip_ansi,
    )
    return await execute_terraform_command_impl(request)


@mcp.tool(name='SearchAwsProviderDocs')
async def search_aws_provider_docs(
    asset_name: str = Field(
        ...,
        description='Name of the AWS service (asset) to look for (e.g., "aws_s3_bucket", "aws_lambda_function")',
    ),
    asset_type: str = Field(
        'resource',
        description="Type of documentation to search - 'resource' (default), 'data_source', or 'both'",
    ),
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
    asset_name: str = Field(
        ...,
        description='Name of the AWSCC service (asset) to look for (e.g., awscc_s3_bucket, awscc_lambda_function)',
    ),
    asset_type: str = Field(
        'resource',
        description="Type of documentation to search - 'resource' (default), 'data_source', or 'both'",
    ),
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
async def search_specific_aws_ia_modules(
    query: str = Field(
        ..., description='Optional search term to filter modules (empty returns all four modules)'
    ),
) -> List[ModuleSearchResult]:
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
async def run_checkov_scan(
    working_directory: str = Field(..., description='Directory containing Terraform files'),
    framework: str = Field(
        'terraform', description='Framework to scan (terraform, cloudformation, etc.)'
    ),
    check_ids: Optional[List[str]] = Field(None, description='Specific check IDs to run'),
    skip_check_ids: Optional[List[str]] = Field(None, description='Check IDs to skip'),
    output_format: str = Field('json', description='Output format (json, cli, etc.)'),
) -> CheckovScanResult:
    """Run Checkov security scan on Terraform code.

    This tool runs Checkov to scan Terraform code for security and compliance issues,
    identifying potential vulnerabilities and misconfigurations according to best practices.

    Checkov (https://www.checkov.io/) is an open-source static code analysis tool that
    can detect hundreds of security and compliance issues in infrastructure-as-code.

    Parameters:
        working_directory: Directory containing Terraform files to scan
        framework: Framework to scan (default: terraform)
        check_ids: Optional list of specific check IDs to run
        skip_check_ids: Optional list of check IDs to skip
        output_format: Format for scan results (default: json)

    Returns:
        A CheckovScanResult object containing scan results and identified vulnerabilities
    """
    request = CheckovScanRequest(
        working_directory=working_directory,
        framework=framework,
        check_ids=check_ids,
        skip_check_ids=skip_check_ids,
        output_format=output_format,
    )
    return await run_checkov_scan_impl(request)


@mcp.tool(name='SearchUserProvidedModule')
async def search_user_provided_module(
    module_url: str = Field(
        ..., description='URL or identifier of the Terraform module (e.g., "hashicorp/consul/aws")'
    ),
    version: Optional[str] = Field(None, description='Specific version of the module to analyze'),
    variables: Optional[Dict[str, Any]] = Field(
        None, description='Variables to use when analyzing the module'
    ),
) -> SearchUserProvidedModuleResult:
    """Search for a user-provided Terraform registry module and understand its inputs, outputs, and usage.

    This tool takes a Terraform registry module URL and analyzes its input variables,
    output variables, README, and other details to provide comprehensive information
    about the module.

    The module URL should be in the format "namespace/name/provider" (e.g., "hashicorp/consul/aws")
    or "registry.terraform.io/namespace/name/provider".

    Examples:
        - To search for the HashiCorp Consul module:
          search_user_provided_module(module_url='hashicorp/consul/aws')

        - To search for a specific version of a module:
          search_user_provided_module(module_url='terraform-aws-modules/vpc/aws', version='3.14.0')

        - To search for a module with specific variables:
          search_user_provided_module(
              module_url='terraform-aws-modules/eks/aws',
              variables={'cluster_name': 'my-cluster', 'vpc_id': 'vpc-12345'}
          )

    Parameters:
        module_url: URL or identifier of the Terraform module (e.g., "hashicorp/consul/aws")
        version: Optional specific version of the module to analyze
        variables: Optional dictionary of variables to use when analyzing the module

    Returns:
        A SearchUserProvidedModuleResult object containing module information
    """
    request = SearchUserProvidedModuleRequest(
        module_url=module_url,
        version=version,
        variables=variables,
    )
    return await search_user_provided_module_impl(request)


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
    return await terraform_aws_provider_assets_listing_impl()


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
