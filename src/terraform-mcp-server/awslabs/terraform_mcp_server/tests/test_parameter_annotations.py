#!/usr/bin/env python3
"""Test script for verifying parameter annotations in MCP tools."""

import json
import sys
from pathlib import Path


# Add project root to path to allow importing the server
project_root = str(Path(__file__).parent.parent.parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import the server module
from awslabs.terraform_mcp_server.server import mcp


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
    search_tool.parameters['properties']['asset_name']['description'] = (
        'Name of the AWS service (asset) to look for (e.g., "aws_s3_bucket", "aws_lambda_function")'
    )
    search_tool.parameters['properties']['asset_type']['description'] = (
        'Type of documentation to search - \'resource\', \'data_source\', or \'both\' (default)'
    )

    # Add parameter descriptions for SearchAwsccProviderDocs
    awscc_docs_tool = mcp._tool_manager.get_tool('SearchAwsccProviderDocs')
    awscc_docs_tool.parameters['properties']['asset_name']['description'] = (
        'Name of the AWSCC service (asset) to look for (e.g., awscc_s3_bucket, awscc_lambda_function)'
    )
    awscc_docs_tool.parameters['properties']['asset_type']['description'] = (
        'Type of documentation to search - \'resource\', \'data_source\', or \'both\' (default)'
    )

    # Add parameter descriptions for SearchSpecificAwsIaModules
    modules_tool = mcp._tool_manager.get_tool('SearchSpecificAwsIaModules')
    modules_tool.parameters['properties']['query']['description'] = (
        'Optional search term to filter modules (empty returns all four modules)'
    )

    # Add parameter descriptions for ExecuteTerraformCommand
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

    # Add parameter descriptions for RunCheckovScan
    checkov_scan_tool = mcp._tool_manager.get_tool('RunCheckovScan')
    checkov_scan_tool.parameters['properties']['request']['description'] = (
        'Details about the Checkov scan to execute'
    )

    # Since request is a complex object with nested properties, update its schema
    if 'properties' in checkov_scan_tool.parameters['properties']['request']:
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
