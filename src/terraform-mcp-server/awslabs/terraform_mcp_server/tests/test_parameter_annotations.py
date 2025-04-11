"""Test script for verifying parameter annotations in MCP tools."""

import json
import sys
from awslabs.terraform_mcp_server.server import mcp
from pathlib import Path


# Add project root to path to allow importing the server
project_root = str(Path(__file__).parent.parent.parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)


def print_tool_parameters():
    """Print the parameters for each tool after annotations are added."""
    tool_names = [
        'SearchAwsProviderDocs',
        'ExecuteTerraformCommand',
        'SearchAwsccProviderDocs',
        'SearchSpecificAwsIaModules',
        'RunCheckovScan',
    ]

    print('\n=== Current Tool Parameter Schemas ===\n')
    for tool_name in tool_names:
        try:
            tool = mcp._tool_manager.get_tool(tool_name)
            if tool is None:
                print(f'Tool {tool_name} not found')
                continue
                
            if not hasattr(tool, 'parameters') or tool.parameters is None:
                print(f'Tool {tool_name} has no parameters schema')
                continue
                
            print(f'=== {tool_name} Parameters Schema ===')
            print(json.dumps(tool.parameters, indent=2))
            print('\n')
        except Exception as e:
            print(f'Error getting tool {tool_name}: {e}')


def add_parameter_annotations():
    """Add parameter annotations to the MCP tools."""
    print('Adding parameter annotations to MCP tools...\n')

    # Add parameter descriptions for SearchAwsProviderDocs
    search_tool = mcp._tool_manager.get_tool('SearchAwsProviderDocs')
    if search_tool is not None and hasattr(search_tool, 'parameters') and search_tool.parameters is not None:
        if 'properties' in search_tool.parameters and 'asset_name' in search_tool.parameters['properties']:
            search_tool.parameters['properties']['asset_name']['description'] = (
                'Name of the AWS service (asset) to look for (e.g., "aws_s3_bucket", "aws_lambda_function")'
            )
        if 'properties' in search_tool.parameters and 'asset_type' in search_tool.parameters['properties']:
            search_tool.parameters['properties']['asset_type']['description'] = (
                "Type of documentation to search - 'resource', 'data_source', or 'both' (default)"
            )

    # Add parameter descriptions for SearchAwsccProviderDocs
    awscc_docs_tool = mcp._tool_manager.get_tool('SearchAwsccProviderDocs')
    if awscc_docs_tool is not None and hasattr(awscc_docs_tool, 'parameters') and awscc_docs_tool.parameters is not None:
        if 'properties' in awscc_docs_tool.parameters and 'asset_name' in awscc_docs_tool.parameters['properties']:
            awscc_docs_tool.parameters['properties']['asset_name']['description'] = (
                'Name of the AWSCC service (asset) to look for (e.g., awscc_s3_bucket, awscc_lambda_function)'
            )
        if 'properties' in awscc_docs_tool.parameters and 'asset_type' in awscc_docs_tool.parameters['properties']:
            awscc_docs_tool.parameters['properties']['asset_type']['description'] = (
                "Type of documentation to search - 'resource', 'data_source', or 'both' (default)"
            )

    # Add parameter descriptions for SearchSpecificAwsIaModules
    modules_tool = mcp._tool_manager.get_tool('SearchSpecificAwsIaModules')
    if modules_tool is not None and hasattr(modules_tool, 'parameters') and modules_tool.parameters is not None:
        if 'properties' in modules_tool.parameters and 'query' in modules_tool.parameters['properties']:
            modules_tool.parameters['properties']['query']['description'] = (
                'Optional search term to filter modules (empty returns all four modules)'
            )

    # Add parameter descriptions for ExecuteTerraformCommand
    terraform_tool = mcp._tool_manager.get_tool('ExecuteTerraformCommand')
    if terraform_tool is not None and hasattr(terraform_tool, 'parameters') and terraform_tool.parameters is not None:
        if 'properties' in terraform_tool.parameters and 'request' in terraform_tool.parameters['properties']:
            terraform_tool.parameters['properties']['request']['description'] = (
                'Details about the Terraform command to execute'
            )

            # Since request is a complex object with nested properties, update its schema
            if ('properties' in terraform_tool.parameters['properties']['request'] and 
                'properties' in terraform_tool.parameters['properties']['request']['properties']):
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

    # Add parameter descriptions for RunCheckovScan
    checkov_scan_tool = mcp._tool_manager.get_tool('RunCheckovScan')
    if checkov_scan_tool is not None and hasattr(checkov_scan_tool, 'parameters') and checkov_scan_tool.parameters is not None:
        if 'properties' in checkov_scan_tool.parameters and 'request' in checkov_scan_tool.parameters['properties']:
            checkov_scan_tool.parameters['properties']['request']['description'] = (
                'Details about the Checkov scan to execute'
            )

            # Since request is a complex object with nested properties, update its schema
            if ('properties' in checkov_scan_tool.parameters['properties']['request'] and 
                'properties' in checkov_scan_tool.parameters['properties']['request']['properties']):
                props = checkov_scan_tool.parameters['properties']['request']['properties']
                if 'working_directory' in props:
                    props['working_directory']['description'] = (
                        'Directory containing Terraform files to scan'
                    )
                if 'framework' in props:
                    props['framework']['description'] = (
                        'Framework to scan (terraform, cloudformation, etc.)'
                    )
                if 'check_ids' in props:
                    props['check_ids']['description'] = 'Optional list of specific check IDs to run'
                if 'skip_check_ids' in props:
                    props['skip_check_ids']['description'] = 'Optional list of check IDs to skip'
                if 'output_format' in props:
                    props['output_format']['description'] = 'Format for scan results (default: json)'

    print('Parameter annotations added successfully.\n')


def main():
    """Run the parameter annotation test."""
    print('=== Terraform MCP Parameter Annotation Test ===\n')

    # Print original parameter schemas
    print('Original parameter schemas:')
    print_tool_parameters()

    # Add parameter annotations
    add_parameter_annotations()

    # Print updated parameter schemas
    print('Updated parameter schemas:')
    print_tool_parameters()


if __name__ == '__main__':
    main()
