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

"""awslabs CFN MCP Server implementation."""

import argparse
import json
from awslabs.cfn_mcp_server.aws_client import get_aws_client
from awslabs.cfn_mcp_server.cloud_control_utils import progress_event, validate_patch
from awslabs.cfn_mcp_server.context import Context
from awslabs.cfn_mcp_server.errors import ClientError, handle_aws_api_error
from awslabs.cfn_mcp_server.iac_generator import create_template as create_template_impl
from awslabs.cfn_mcp_server.impl.tools import (
    handle_start_resource_scan,
    list_related_resources_impl,
    list_resources_by_filter_impl,
)
from awslabs.cfn_mcp_server.schema_manager import schema_manager
from awslabs.cfn_mcp_server.stack_analysis.stack_analyzer import StackAnalyzer
from mcp.server.fastmcp import FastMCP
from pydantic import Field


mcp = FastMCP(
    'awslabs.cfn-mcp-server',
    instructions="""
    # CloudFormation MCP

    This MCP allows you to:
    1. Read and List all of your AWS resources by the CloudFormation type name (e.g. AWS::S3::Bucket)
    2. Create/Update/Delete your AWS resources
    """,
    dependencies=['pydantic', 'loguru', 'boto3', 'botocore'],
)


@mcp.tool()
async def get_resource_schema_information(
    resource_type: str = Field(
        description='The AWS resource type (e.g., "AWS::S3::Bucket", "AWS::RDS::DBInstance")'
    ),
    region: str | None = Field(
        description='The AWS region that the operation should be performed in', default=None
    ),
) -> dict:
    """Get schema information for an AWS resource.

    Parameters:
        resource_type: The AWS resource type (e.g., "AWS::S3::Bucket")

    Returns:
        The resource schema information
    """
    if not resource_type:
        raise ClientError('Please provide a resource type (e.g., AWS::S3::Bucket)')

    sm = schema_manager()
    schema = await sm.get_schema(resource_type, region)
    return schema


@mcp.tool()
async def list_resources(
    resource_type: str = Field(
        description='The AWS resource type (e.g., "AWS::S3::Bucket", "AWS::RDS::DBInstance")'
    ),
    region: str | None = Field(
        description='The AWS region that the operation should be performed in', default=None
    ),
) -> list:
    """List AWS resources of a specified type.

    Parameters:
        resource_type: The AWS resource type (e.g., "AWS::S3::Bucket", "AWS::RDS::DBInstance")
        region: AWS region to use (e.g., "us-east-1", "us-west-2")

    Returns:
        A list of resource identifiers
    """
    if not resource_type:
        raise ClientError('Please provide a resource type (e.g., AWS::S3::Bucket)')

    cloudcontrol = get_aws_client('cloudcontrol', region)
    paginator = cloudcontrol.get_paginator('list_resources')

    results = []
    page_iterator = paginator.paginate(TypeName=resource_type)
    try:
        for page in page_iterator:
            results.extend(page['ResourceDescriptions'])
    except Exception as e:
        raise handle_aws_api_error(e)

    return [response['Identifier'] for response in results]


@mcp.tool()
async def get_resource(
    resource_type: str = Field(
        description='The AWS resource type (e.g., "AWS::S3::Bucket", "AWS::RDS::DBInstance")'
    ),
    identifier: str = Field(
        description='The primary identifier of the resource to get (e.g., bucket name for S3 buckets)'
    ),
    region: str | None = Field(
        description='The AWS region that the operation should be performed in', default=None
    ),
) -> dict:
    """Get details of a specific AWS resource.

    Parameters:
        resource_type: The AWS resource type (e.g., "AWS::S3::Bucket")
        identifier: The primary identifier of the resource to get (e.g., bucket name for S3 buckets)
        region: AWS region to use (e.g., "us-east-1", "us-west-2")

    Returns:
        Detailed information about the specified resource with a consistent structure:
        {
            "identifier": The resource identifier,
            "properties": The detailed information about the resource
        }
    """
    if not resource_type:
        raise ClientError('Please provide a resource type (e.g., AWS::S3::Bucket)')

    if not identifier:
        raise ClientError('Please provide a resource identifier')

    cloudcontrol = get_aws_client('cloudcontrol', region)
    try:
        result = cloudcontrol.get_resource(TypeName=resource_type, Identifier=identifier)
        return {
            'identifier': result['ResourceDescription']['Identifier'],
            'properties': result['ResourceDescription']['Properties'],
        }
    except Exception as e:
        raise handle_aws_api_error(e)


@mcp.tool()
async def update_resource(
    resource_type: str = Field(
        description='The AWS resource type (e.g., "AWS::S3::Bucket", "AWS::RDS::DBInstance")'
    ),
    identifier: str = Field(
        description='The primary identifier of the resource to get (e.g., bucket name for S3 buckets)'
    ),
    patch_document: list = Field(
        description='A list of RFC 6902 JSON Patch operations to apply', default=[]
    ),
    region: str | None = Field(
        description='The AWS region that the operation should be performed in', default=None
    ),
) -> dict:
    """Update an AWS resource.

    Parameters:
        resource_type: The AWS resource type (e.g., "AWS::S3::Bucket")
        identifier: The primary identifier of the resource to update
        patch_document: A list of RFC 6902 JSON Patch operations to apply
        region: AWS region to use (e.g., "us-east-1", "us-west-2")

    Returns:
        Information about the updated resource with a consistent structure:
        {
            "status": Status of the operation ("SUCCESS", "PENDING", "FAILED", etc.)
            "resource_type": The AWS resource type
            "identifier": The resource identifier
            "is_complete": Boolean indicating whether the operation is complete
            "status_message": Human-readable message describing the result
            "request_token": A token that allows you to track long running operations via the get_resource_request_status tool
            "resource_info": Optional information about the resource properties
        }
    """
    if not resource_type:
        raise ClientError('Please provide a resource type (e.g., AWS::S3::Bucket)')

    if not identifier:
        raise ClientError('Please provide a resource identifier')

    if not patch_document:
        raise ClientError('Please provide a patch document for the update')

    if Context.readonly_mode():
        raise ClientError(
            'You have configured this tool in readonly mode. To make this change you will have to update your configuration.'
        )

    validate_patch(patch_document)
    cloudcontrol_client = get_aws_client('cloudcontrol', region)

    # Convert patch document to JSON string for the API
    patch_document_str = json.dumps(patch_document)

    # Update the resource
    try:
        response = cloudcontrol_client.update_resource(
            TypeName=resource_type, Identifier=identifier, PatchDocument=patch_document_str
        )
    except Exception as e:
        raise handle_aws_api_error(e)

    return progress_event(response['ProgressEvent'], None)


@mcp.tool()
async def create_resource(
    resource_type: str = Field(
        description='The AWS resource type (e.g., "AWS::S3::Bucket", "AWS::RDS::DBInstance")'
    ),
    properties: dict = Field(description='A dictionary of properties for the resource'),
    region: str | None = Field(
        description='The AWS region that the operation should be performed in', default=None
    ),
) -> dict:
    """Create an AWS resource.

    Parameters:
        resource_type: The AWS resource type (e.g., "AWS::S3::Bucket")
        properties: A dictionary of properties for the resource
        region: AWS region to use (e.g., "us-east-1", "us-west-2")

    Returns:
        Information about the created resource with a consistent structure:
        {
            "status": Status of the operation ("SUCCESS", "PENDING", "FAILED", etc.)
            "resource_type": The AWS resource type
            "identifier": The resource identifier
            "is_complete": Boolean indicating whether the operation is complete
            "status_message": Human-readable message describing the result
            "request_token": A token that allows you to track long running operations via the get_resource_request_status tool
            "resource_info": Optional information about the resource properties
        }
    """
    if not resource_type:
        raise ClientError('Please provide a resource type (e.g., AWS::S3::Bucket)')

    if not properties:
        raise ClientError('Please provide the properties for the desired resource')

    if Context.readonly_mode():
        raise ClientError(
            'You have configured this tool in readonly mode. To make this change you will have to update your configuration.'
        )

    cloudcontrol_client = get_aws_client('cloudcontrol', region)
    try:
        response = cloudcontrol_client.create_resource(
            TypeName=resource_type, DesiredState=json.dumps(properties)
        )
    except Exception as e:
        raise handle_aws_api_error(e)

    return progress_event(response['ProgressEvent'], None)


@mcp.tool()
async def delete_resource(
    resource_type: str = Field(
        description='The AWS resource type (e.g., "AWS::S3::Bucket", "AWS::RDS::DBInstance")'
    ),
    identifier: str = Field(
        description='The primary identifier of the resource to get (e.g., bucket name for S3 buckets)'
    ),
    region: str | None = Field(
        description='The AWS region that the operation should be performed in', default=None
    ),
) -> dict:
    """Delete an AWS resource.

    Parameters:
        resource_type: The AWS resource type (e.g., "AWS::S3::Bucket")
        identifier: The primary identifier of the resource to delete (e.g., bucket name for S3 buckets)
        region: AWS region to use (e.g., "us-east-1", "us-west-2")

    Returns:
        Information about the deletion operation with a consistent structure:
        {
            "status": Status of the operation ("SUCCESS", "PENDING", "FAILED", "NOT_FOUND", etc.)
            "resource_type": The AWS resource type
            "identifier": The resource identifier
            "is_complete": Boolean indicating whether the operation is complete
            "status_message": Human-readable message describing the result
            "request_token": A token that allows you to track long running operations via the get_resource_request_status tool
        }
    """
    if not resource_type:
        raise ClientError('Please provide a resource type (e.g., AWS::S3::Bucket)')

    if not identifier:
        raise ClientError('Please provide a resource identifier')

    if Context.readonly_mode():
        raise ClientError(
            'You have configured this tool in readonly mode. To make this change you will have to update your configuration.'
        )

    cloudcontrol_client = get_aws_client('cloudcontrol', region)
    try:
        response = cloudcontrol_client.delete_resource(
            TypeName=resource_type, Identifier=identifier
        )
    except Exception as e:
        raise handle_aws_api_error(e)

    return progress_event(response['ProgressEvent'], None)


@mcp.tool()
async def get_resource_request_status(
    request_token: str = Field(
        description='The request_token returned from the long running operation'
    ),
    region: str | None = Field(
        description='The AWS region that the operation should be performed in', default=None
    ),
) -> dict:
    """Get the status of a long running operation with the request token.

    Args:
        request_token: The request_token returned from the long running operation
        region: AWS region to use (e.g., "us-east-1", "us-west-2")

    Returns:
        Detailed information about the request status structured as
        {
            "status": Status of the operation ("SUCCESS", "PENDING", "FAILED", "NOT_FOUND", etc.)
            "resource_type": The AWS resource type
            "identifier": The resource identifier
            "is_complete": Boolean indicating whether the operation is complete
            "status_message": Human-readable message describing the result
            "request_token": A token that allows you to track long running operations via the get_resource_request_status tool
            "error_code": A code associated with any errors if the request failed
            "retry_after": A duration to wait before retrying the request
        }
    """
    if not request_token:
        raise ClientError('Please provide a request token to track the request')

    cloudcontrol_client = get_aws_client('cloudcontrol', region)
    try:
        response = cloudcontrol_client.get_resource_request_status(
            RequestToken=request_token,
        )
    except Exception as e:
        raise handle_aws_api_error(e)

    return progress_event(response['ProgressEvent'], response.get('HooksProgressEvent', None))


@mcp.tool()
async def create_template(
    template_name: str | None = Field(None, description='Name for the generated template'),
    resources: list | None = Field(
        None,
        description="List of resources to include in the template, each with 'ResourceType' and 'ResourceIdentifier'",
    ),
    output_format: str = Field(
        'YAML', description='Output format for the template (JSON or YAML)'
    ),
    deletion_policy: str = Field(
        'RETAIN',
        description='Default DeletionPolicy for resources in the template (RETAIN, DELETE, or SNAPSHOT)',
    ),
    update_replace_policy: str = Field(
        'RETAIN',
        description='Default UpdateReplacePolicy for resources in the template (RETAIN, DELETE, or SNAPSHOT)',
    ),
    template_id: str | None = Field(
        None,
        description='ID of an existing template generation process to check status or retrieve template',
    ),
    save_to_file: str | None = Field(
        None, description='Path to save the generated template to a file'
    ),
    region: str | None = Field(
        description='The AWS region that the operation should be performed in', default=None
    ),
) -> dict:
    """Create a CloudFormation template from existing resources using the IaC Generator API.

    This tool allows you to generate CloudFormation templates from existing AWS resources
    that are not already managed by CloudFormation. The template generation process is
    asynchronous, so you can check the status of the process and retrieve the template
    once it's complete. You can pass up to 500 resources at a time.

    Examples:
    1. Start template generation for an S3 bucket:
       create_template(
           template_name="my-template",
           resources=[{"ResourceType": "AWS::S3::Bucket", "ResourceIdentifier": {"BucketName": "my-bucket"}}],
           deletion_policy="RETAIN",
           update_replace_policy="RETAIN"
       )

    2. Check status of template generation:
       create_template(template_id="arn:aws:cloudformation:us-east-1:123456789012:generatedtemplate/abcdef12-3456-7890-abcd-ef1234567890")

    3. Retrieve and save generated template:
       create_template(
           template_id="arn:aws:cloudformation:us-east-1:123456789012:generatedtemplate/abcdef12-3456-7890-abcd-ef1234567890",
           save_to_file="/path/to/template.yaml",
           output_format="YAML"
       )
    """
    return await create_template_impl(
        template_name=template_name,
        resources=resources,
        output_format=output_format,
        deletion_policy=deletion_policy,
        update_replace_policy=update_replace_policy,
        template_id=template_id,
        save_to_file=save_to_file,
        region_name=region,
    )


@mcp.tool()
async def list_resources_by_filter(
    resource_identifier: str | None = Field(
        default=None,
        description='Filter by specific resource identifier (e.g., "my-bucket-name")',
    ),
    resource_scan_id: str | None = Field(
        default=None,
        description='Resource scan ID to use for filtering resources. If not provided, the latest completed scan will be used.',
    ),
    resource_type_prefix: str | None = Field(
        default=None,
        description='Filter by resource type prefix (e.g., "AWS::S3::" to get all S3 resources)',
    ),
    tag_key: str | None = Field(default=None, description='Filter resources by tag key'),
    tag_value: str | None = Field(
        default=None,
        description='Filter resources by tag value (requires tag_key to be specified)',
    ),
    limit: int = Field(
        default=100,
        description='Maximum number of resources to return',
    ),
    next_token: str | None = Field(
        default=None, description='Pagination token from previous response to get next page'
    ),
    region: str | None = Field(
        description='The AWS region that the operation should be performed in', default=None
    ),
) -> dict:
    """List AWS resources with filtering support.

    To preserve tokens usage, this tool allows you to filter resources by type resourcetypeprefix,
    tag key, and tag value. It returns a paginated list of resource identifiers. It is recommended
    to use the filtering parameters to reduce the number of resources returned,

    This tool uses AWS CloudFormation's resource scan API with server-side filtering.

    Parameters:
        resource_identifier: Filter by specific resource identifier (optional)
        resource_scan_id: Resource scan ID to use for filtering resources. (optional)
                           If not provided, the latest completed scan will be used even if it's partial or full scan.
        resource_type_prefix: Filter by resource type prefix (optional)
        tag_key: Filter resources by tag key (optional)
        tag_value: Filter resources by tag value (optional, requires tag_key)
        limit: Maximum number of resources to return (1-100, AWS API limit)
        next_token: AWS pagination token from previous response (optional)
        region: AWS region to use (optional)

    Returns:
        Resource identifiers with filtering applied at the AWS API level and pagination metadata
    """
    return await list_resources_by_filter_impl(
        resource_identifier=resource_identifier,
        resource_scan_id=resource_scan_id,
        resource_type_prefix=resource_type_prefix,
        tag_key=tag_key,
        tag_value=tag_value,
        limit=limit,
        next_token=next_token,
        region=region,
    )


@mcp.tool()
async def list_related_resources(
    resources: list = Field(
        description='List of resources to find related resources for. Each resource should have resource_type and resource_identifier keys.'
    ),
    resource_scan_id: str | None = Field(
        default=None,
        description='Resource scan ID to use for finding related resources. If not provided, the latest completed scan will be used.',
    ),
    max_results: int = Field(
        default=100,
        description='Maximum number of related resources to return (default: 100, max: 100 due to AWS API limits)',
    ),
    next_token: str | None = Field(
        default=None, description='Pagination token from previous response to get next page'
    ),
    region: str | None = Field(
        description='The AWS region that the operation should be performed in', default=None
    ),
) -> dict:
    """List AWS resources related to the specified list of resources or resource.

    This tool uses AWS CloudFormation's list_resource_scan_related_resources API
    to find resources that are related to the specified input resources.

    Note: Call with one resource at a time if you want explicitly related resources

    Parameters:
        resources: List of resources to find related resources for. Each resource should have
                  'resource_type' and 'resource_identifier' keys. Maximum 100 resources.
        resource_scan_id: Resource scan ID to use for finding related resources.
                         If not provided, the latest completed scan will be used even if it's partial or full scan.
        max_results: Maximum number of related resources to return (1-100, AWS API limit)
        next_token: AWS pagination token from previous response (optional)
        region: AWS region to use (optional)

    Returns:
        Related resources grouped by managed/unmanaged status with pagination metadata

    Example:
        resources = [
            {
                "resource_type": "AWS::S3::Bucket",
                "resource_identifier": {"BucketName": "my-bucket"}
            }
        ]
    """
    return await list_related_resources_impl(
        resources=resources,
        resource_scan_id=resource_scan_id,
        max_results=max_results,
        next_token=next_token,
        region=region,
    )


@mcp.tool()
async def start_resource_scan(
    resource_types: list | None = Field(
        default=None,
        description='The AWS resource types to scan (e.g., "AWS::S3::Bucket", "AWS::RDS::DBInstance")',
    ),
    region: str | None = Field(
        description='The AWS region that the operation should be performed in', default=None
    ),
) -> dict:
    """Start a resource scan for a specific AWS resource types or the entire account.

    Parameters:
        resource_type: The AWS resource types to scan (e.g., "AWS::S3::Bucket", "AWS::EC2::*", or a list of resource types)
        Provide an empty list [] to scan the entire account
        region: AWS region to use (e.g., "us-east-1", "us-west-2")

    Returns:
        Information about the started scan with a consistent structure:
        {
            "scan_id": The unique identifier for the started scan
        }
    """
    return await handle_start_resource_scan(
        resource_types=resource_types,
        region=region,
    )


@mcp.tool()
async def analyze_stack(
    stack_name: str = Field(description='The name of the CloudFormation stack to analyze'),
    region: str | None = Field(
        description='The AWS region that the operation should be performed in', default=None
    ),
) -> dict:
    """Analyze a CloudFormation stack and return detailed information about its resources.

    Parameters:
        stack_name: The name of the CloudFormation stack to analyze
        region: AWS region to use (e.g., "us-east-1", "us-west-2")

    Returns:
        Detailed information about the stack and its resources in three distinct sections:
        1. Resources in the given stack
        2. Performs analysis on stack resources against a resource scan
        3. Related resources that are not managed by CloudFormation
        4. Related resources that are managed by different stacks

    Raises:
        ClientError: If the stack name is not provided or if the stack does not exist in the specified region.
        ClientError: If there is an error during the analysis process.

    """
    if not stack_name:
        raise ClientError('Please provide a stack name')

    try:
        # Initialize the stack analyzer
        analyzer = StackAnalyzer(region or 'us-east-1')  # Provide a default region

        # Get stack analysis
        stack_analysis = analyzer.analyze_stack(stack_name)

        # Check if there was an error in the analysis
        if 'error' in stack_analysis:
            error_message = stack_analysis['error']
            if 'not found' in error_message.lower() or 'does not exist' in error_message.lower():
                raise ClientError(
                    f'Stack "{stack_name}" was not found. Please check the stack name and region.'
                )
            else:
                raise ClientError(error_message)
        # Get best practices
        best_practices = StackAnalyzer.get_best_cfn_practices()

        # Extract the resources data for better structure
        resources_data = stack_analysis.get('resources', {})
        related_resources = stack_analysis.get('related_resources', [])

        # Enhance related resources with summary for better Q analysis
        related_resources_summary = {
            'total_count': len(related_resources),
            'resource_types': {},
            'sample_resources': related_resources if related_resources else [],
            'description': 'Resources that are related to stack resources but not managed by this stack',
        }

        # Categorize related resources by type
        for resource in related_resources:
            resource_type = resource.get('ResourceType', 'Unknown')
            if resource_type not in related_resources_summary['resource_types']:
                related_resources_summary['resource_types'][resource_type] = 0
            related_resources_summary['resource_types'][resource_type] += 1

        result = {
            'stack_info': stack_analysis.get('stack_info'),
            'stack_status': stack_analysis.get('stack_status'),
            'creation_time': stack_analysis.get('creation_time'),
            'last_updated_time': stack_analysis.get('last_updated_time'),
            'outputs': stack_analysis.get('outputs', []),
            'parameters': stack_analysis.get('parameters', []),
            # Stack resource matching results
            'prompt': f'Analyze the CloudFormation stack "{stack_name}" and its resources Offer insights on the stack resources, related resources, and best practices.',
            'stack_name': resources_data.get('stack_name'),
            'resource_scan_id': resources_data.get('resource_scan_id'),
            'matched_resources': resources_data.get('matched_resources', []),
            'unmatched_resources': resources_data.get('unmatched_resources', []),
            # Enhanced related resources section for better Q analysis
            'related_resources': related_resources,
            'related_resources_summary': related_resources_summary,
            # Account-wide resource summary
            'account_summary': stack_analysis.get('account_summary', {}),
            'best_practices': best_practices,
            # Analysis highlights for Q to focus on
            'analysis_highlights': {
                'stack_resources': {
                    'total_in_stack': len(resources_data.get('matched_resources', []))
                    + len(resources_data.get('unmatched_resources', [])),
                    'matched_in_scan': len(resources_data.get('matched_resources', [])),
                    'unmatched_in_scan': len(resources_data.get('unmatched_resources', [])),
                    'match_percentage': round(
                        (
                            len(resources_data.get('matched_resources', []))
                            / max(
                                1,
                                len(resources_data.get('matched_resources', []))
                                + len(resources_data.get('unmatched_resources', [])),
                            )
                        )
                        * 100,
                        2,
                    ),
                },
                'related_resources': {
                    'total_found': len(related_resources),
                    'unique_types': len(related_resources_summary['resource_types']),
                    'description': 'These are AWS resources that have relationships with your stack resources but are not directly managed by this CloudFormation stack',
                },
                'account_overview': {
                    'total_resources': stack_analysis.get('account_summary', {})
                    .get('overall_summary', {})
                    .get('total_resources', 0),
                    'unmanaged_percentage': stack_analysis.get('account_summary', {})
                    .get('overall_summary', {})
                    .get('unmanaged_percentage', 0),
                    'managed_percentage': stack_analysis.get('account_summary', {})
                    .get('overall_summary', {})
                    .get('managed_percentage', 0),
                },
            },
        }

        return result
    except Exception as e:
        raise ClientError(f'Error analyzing stack "{stack_name}": {str(e)}')


def main():
    """Run the MCP server with CLI argument support."""
    parser = argparse.ArgumentParser(
        description='An AWS Labs Model Context Protocol (MCP) server for doing common cloudformation tasks and for managing your resources in your AWS account'
    )
    parser.add_argument(
        '--readonly',
        action=argparse.BooleanOptionalAction,
        help='Prevents the MCP server from performing mutating operations',
    )

    args = parser.parse_args()
    Context.initialize(args.readonly)
    mcp.run()


if __name__ == '__main__':
    main()
