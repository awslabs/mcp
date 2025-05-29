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

"""awslabs CFN MCP Server implementation."""

import argparse
import json
from awslabs.cfn_mcp_server.aws_client import get_aws_client
from awslabs.cfn_mcp_server.cloud_control_utils import progress_event, validate_patch
from awslabs.cfn_mcp_server.context import Context
from awslabs.cfn_mcp_server.errors import ClientError, handle_aws_api_error
from awslabs.cfn_mcp_server.iac_generator import create_template as create_template_impl
from awslabs.cfn_mcp_server.schema_manager import schema_manager
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

    return progress_event(response['ProgressEvent'])


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

    return progress_event(response['ProgressEvent'])


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

    return progress_event(response['ProgressEvent'])


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

    return progress_event(response['ProgressEvent'])


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
