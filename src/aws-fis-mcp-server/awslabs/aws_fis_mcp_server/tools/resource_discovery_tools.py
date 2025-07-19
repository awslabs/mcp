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

import time
from mcp.server.fastmcp import Context
from pydantic import Field
from typing import Any, Dict, List, Optional


"""AWS Resource Discovery Tools.

This section provides MCP tools for discovering AWS resources using CloudFormation and
Resource Explorer services. These tools enable the identification of potential targets
for fault injection experiments across the AWS account.

The tools offer methods to list resources from different sources, create and manage
Resource Explorer views, and filter resources based on specific criteria. They handle
pagination for large result sets and provide structured responses suitable for
consumption by LLMs.

This consolidated approach allows for more flexible resource discovery, making it easier
to design comprehensive resilience testing scenarios regardless of how resources were
provisioned.
"""


async def list_cfn_stacks(ctx: Context) -> Dict[str, Any]:
    """Retrieve all AWS CloudFormation Stacks.

    This tool lists all CloudFormation stacks in the current AWS account and region,
    providing information that can help identify potential targets for fault injection.

    Returns:
        Dict containing CloudFormation stack information
    """
    try:
        all_stacks = []
        from awslabs.aws_fis_mcp_server.server import cloudformation

        if cloudformation is None:
            raise Exception(
                'AWS CloudFormation client not initialized. Please ensure the server is properly configured.'
            )
        cfn = cloudformation
        response = cfn.list_stacks()
        all_stacks.extend(response.get('StackSummaries', []))

        # Handle pagination
        while 'NextToken' in response:
            response = cfn.list_stacks(NextToken=response['NextToken'])
            all_stacks.extend(response.get('StackSummaries', []))

        return {'stacks': all_stacks}
    except Exception as e:
        await ctx.error(f'Error listing CloudFormation stacks: {str(e)}')
        raise


async def get_stack_resources(
    ctx: Context,
    stack_name: str = Field(
        ..., description='Name of the CloudFormation stack to retrieve resources from'
    ),
) -> Dict[str, List[Dict[str, Any]]]:
    """Retrieves the resources that have been created by an individual stack.

    This tool lists all resources within a specific CloudFormation stack,
    which can be useful for identifying potential targets for fault injection experiments.

    Args:
        ctx: The MCP context for logging and communication
        stack_name: Name of the CloudFormation stack

    Returns:
        Dict containing stack resources
    """
    try:
        all_resources = []
        from awslabs.aws_fis_mcp_server.server import cloudformation

        if cloudformation is None:
            raise Exception(
                'AWS CloudFormation client not initialized. Please ensure the server is properly configured.'
            )
        cfn = cloudformation
        response = cfn.list_stack_resources(StackName=stack_name)
        all_resources.extend(response.get('StackResourceSummaries', []))

        # Handle pagination
        while 'NextToken' in response:
            response = cfn.list_stack_resources(
                StackName=stack_name, NextToken=response['NextToken']
            )
            all_resources.extend(response.get('StackResourceSummaries', []))

        return {'resources': all_resources}
    except Exception as e:
        await ctx.error(f'Error getting stack resources: {str(e)}')
        raise


async def list_views(ctx: Context) -> List[Dict[str, Any]]:
    """List Resource Explorer views.

    This tool retrieves all Resource Explorer views in the current AWS account and region,
    which can be used to find and filter resources for fault injection experiments.

    Returns:
        List of Resource Explorer views
    """
    try:
        all_views = []
        from awslabs.aws_fis_mcp_server.server import resource_explorer

        if resource_explorer is None:
            raise Exception(
                'AWS Resource Explorer client not initialized. Please ensure the server is properly configured.'
            )
        response = resource_explorer.list_views()
        all_views.extend(response.get('Views', []))

        # Handle pagination
        while 'NextToken' in response:
            response = resource_explorer.list_views(NextToken=response['NextToken'])
            all_views.extend(response.get('Views', []))

        return all_views
    except Exception as e:
        await ctx.error(f'Error listing Resource Explorer views: {str(e)}')
        raise


async def search_resources(
    ctx: Context,
    query_string: str = Field(..., description='The query string to search for resources'),
    view_arn: str = Field(..., description='The ARN of the Resource Explorer view to use'),
    max_results: int = Field(100, description='Maximum number of results to return'),
    next_token: Optional[str] = Field(None, description='Token for pagination'),
) -> Dict[str, Any]:
    """Search for AWS resources using Resource Explorer.

    This tool searches for AWS resources using Resource Explorer based on a query string
    and view ARN. It can be used to find specific resources for fault injection experiments.

    Args:
        ctx: The MCP context for logging and communication
        query_string: The query string to search for resources
        view_arn: The ARN of the Resource Explorer view to use
        max_results: Maximum number of results to return (default: 100)
        next_token: Token for pagination (optional)

    Returns:
        Dict containing search results and pagination information
    """
    try:
        # Build search parameters
        search_params = {
            'QueryString': query_string,
            'ViewArn': view_arn,
            'MaxResults': max_results,
        }

        # Add next token if provided
        if next_token:
            search_params['NextToken'] = next_token

        # Execute search
        from awslabs.aws_fis_mcp_server.server import resource_explorer

        if resource_explorer is None:
            raise Exception(
                'AWS Resource Explorer client not initialized. Please ensure the server is properly configured.'
            )
        response = resource_explorer.search(**search_params)

        # Format results
        result = {
            'resources': response.get('Resources', []),
            'query_string': query_string,
            'view_arn': view_arn,
            'count': len(response.get('Resources', [])),
        }

        # Only include next_token if it exists in the response
        if 'NextToken' in response:
            result['next_token'] = response['NextToken']

        await ctx.info(f'Found {result["count"]} resources matching query: {query_string}')
        return result
    except Exception as e:
        await ctx.error(f'Error searching resources: {str(e)}')
        raise


async def create_view(
    ctx: Context,
    query: str = Field(..., description='Filter string for the view'),
    view_name: str = Field(..., description='Name of the view'),
    name: str = Field(..., description='Required name for the view (will be added as Name tag)'),
    tags: Optional[Dict[str, str]] = Field(
        None, description='Optional additional tags to apply to the view'
    ),
    scope: Optional[str] = Field(None, description='Scope of the view'),
    client_token: Optional[str] = Field(None, description='Client token for idempotency'),
) -> Dict[str, Any]:
    """Create a Resource Explorer view.

    This tool creates a new Resource Explorer view that can be used to find
    and filter resources for fault injection experiments.

    Args:
        ctx: The MCP context for logging and communication
        query: Filter string for the view
        view_name: Name of the view
        name: Required name for the view (will be added as Name tag)
        tags: Optional additional tags to apply to the view
        scope: Scope of the view
        client_token: Client token for idempotency

    Returns:
        Dict containing the created view details

    Raises:
        Exception: For AWS API errors or when writes are disabled
    """
    global allow_writes
    from awslabs.aws_fis_mcp_server.server import allow_writes, resource_explorer

    if resource_explorer is None:
        raise Exception(
            'AWS Resource Explorer client not initialized. Please ensure the server is properly configured.'
        )

    # Check if writes are allowed
    if not allow_writes:
        error_msg = 'Write operations are disabled. Use --allow-writes flag to enable Resource Explorer view creation.'
        await ctx.error(error_msg)
        raise Exception(error_msg)

    try:
        # Start with Name tag as required
        view_tags = {'Name': name}

        # Add any additional tags if provided
        if tags:
            view_tags.update(tags)

        # Generate client token if not provided
        if not client_token:
            client_token = f'create-view-{int(time.time())}'

        response = resource_explorer.create_view(
            ClientToken=client_token,
            Filters={'FilterString': query},
            Scope=scope,
            Tags=view_tags,
            ViewName=view_name,
        )

        await ctx.info(f'Created Resource Explorer view "{name}" with name: {view_name}')
        return response
    except Exception as e:
        await ctx.error(f'Error creating Resource Explorer view: {str(e)}')
        raise


async def discover_relationships(
    ctx: Context,
    resource_type: str = Field(
        ...,
        description='AWS resource type (e.g., AWS::EC2::Instance, AWS::ElasticLoadBalancingV2::LoadBalancer)',
    ),
    resource_id: str = Field(..., description='AWS resource ID to discover relationships for'),
    limit: Optional[int] = Field(
        10, description='Maximum number of configuration items to retrieve'
    ),
    chronological_order: Optional[str] = Field(
        'Reverse', description='Order of configuration items (Reverse or Forward)'
    ),
) -> Dict[str, Any]:
    """Discover relationships for a specific AWS resource using AWS Config.

    This tool retrieves the configuration history for a specific AWS resource
    and returns its relationships with other resources. This is useful for
    understanding resource dependencies, such as finding which subnet an ALB
    is placed in or which security groups are attached to an instance.

    Args:
        ctx: The MCP context for logging and communication
        resource_type: AWS resource type (e.g., AWS::EC2::Instance)
        resource_id: AWS resource ID to discover relationships for
        limit: Maximum number of configuration items to retrieve
        chronological_order: Order of configuration items (Reverse or Forward)

    Returns:
        Dict containing resource relationships and configuration details
    """
    try:
        # Get resource configuration history
        params = {
            'resourceType': resource_type,
            'resourceId': resource_id,
            'chronologicalOrder': chronological_order,
        }

        if limit:
            params['limit'] = limit

        from awslabs.aws_fis_mcp_server.server import aws_config_client

        if aws_config_client is None:
            raise Exception(
                'AWS Config client not initialized. Please ensure the server is properly configured.'
            )
        response = aws_config_client.get_resource_config_history(**params)

        result = {
            'resource_type': resource_type,
            'resource_id': resource_id,
            'relationships': [],
            'configuration_items': [],
        }

        # Process configuration items
        config_items = response.get('configurationItems', [])

        if not config_items:
            result['message'] = 'No configuration items found for the specified resource'
            return result

        # Extract relationships from the most recent configuration item
        latest_config = config_items[0] if config_items else {}
        relationships = latest_config.get('relationships', [])

        result['relationships'] = relationships

        # Include configuration item details (without sensitive data)
        for item in config_items:
            config_summary = {
                'configuration_item_capture_time': str(
                    item.get('configurationItemCaptureTime', '')
                ),
                'configuration_state_id': item.get('configurationStateId'),
                'aws_region': item.get('awsRegion'),
                'availability_zone': item.get('availabilityZone'),
                'resource_creation_time': str(item.get('resourceCreationTime', '')),
                'tags': item.get('tags', {}),
                'relationships_count': len(item.get('relationships', [])),
            }
            result['configuration_items'].append(config_summary)

        # Add summary statistics
        result['summary'] = {
            'total_relationships': len(relationships),
            'total_configuration_items': len(config_items),
            'relationship_types': list({rel.get('relationshipName', '') for rel in relationships}),
        }

        await ctx.info(
            f'Found {len(relationships)} relationships for {resource_type} {resource_id}'
        )
        return result

    except Exception as e:
        await ctx.error(f'Error discovering resource relationships: {str(e)}')
        raise
