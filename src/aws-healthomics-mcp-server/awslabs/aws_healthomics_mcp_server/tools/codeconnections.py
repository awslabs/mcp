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

"""CodeConnections management tools for the AWS HealthOmics MCP server.

This module provides tools to help users set up AWS CodeConnections for use
with HealthOmics workflows. AWS CodeConnections provide secure connections
to third-party Git providers (GitHub, GitLab, Bitbucket, etc.) that are
required for the workflow-repository-integration feature.
"""

import botocore
import botocore.exceptions
from awslabs.aws_healthomics_mcp_server.consts import DEFAULT_MAX_RESULTS
from awslabs.aws_healthomics_mcp_server.utils.aws_utils import get_codeconnections_client
from awslabs.aws_healthomics_mcp_server.utils.validation_utils import (
    validate_connection_arn,
    validate_provider_type,
)
from loguru import logger
from mcp.server.fastmcp import Context
from pydantic import Field
from typing import Any, Dict, Optional


def generate_console_url(region: str) -> str:
    """Generate the AWS Console URL for CodeConnections.

    This function creates a URL that directs users to the AWS Console
    CodeConnections page where they can complete OAuth authorization
    for their Git provider connections.

    Args:
        region: AWS region for the connection (e.g., 'us-east-1', 'eu-west-1')

    Returns:
        Console URL for the CodeConnections page in the specified region

    Example:
        >>> generate_console_url('us-east-1')
        'https://us-east-1.console.aws.amazon.com/codesuite/settings/connections?region=us-east-1'
    """
    return (
        f'https://{region}.console.aws.amazon.com/codesuite/settings/connections?region={region}'
    )


def get_status_guidance(status: str) -> str:
    """Get guidance message based on connection status.

    This function returns appropriate guidance messages for users based on
    the current status of their CodeConnection. The guidance helps users
    understand what actions they need to take or what capabilities are
    available.

    Args:
        status: The connection status (PENDING, AVAILABLE, ERROR)

    Returns:
        Guidance message for the user explaining the status and next steps

    Example:
        >>> get_status_guidance('PENDING')
        'This connection requires OAuth authorization. ...'
        >>> get_status_guidance('AVAILABLE')
        'This connection is ready to use with HealthOmics workflows. ...'
        >>> get_status_guidance('ERROR')
        'This connection has encountered an error. ...'
    """
    guidance = {
        'PENDING': (
            'This connection requires OAuth authorization. '
            'Please visit the AWS Console URL provided to complete the authorization process. '
            'Once authorized, the connection status will change to AVAILABLE.'
        ),
        'AVAILABLE': (
            'This connection is ready to use with HealthOmics workflows. '
            'You can use the connection ARN with the definition_repository.connection_arn parameter '
            'when creating workflows from Git repositories.'
        ),
        'ERROR': (
            'This connection has encountered an error. '
            'Please check the AWS Console for more details or try creating a new connection.'
        ),
    }
    return guidance.get(status, f'Unknown status: {status}')


async def list_codeconnections(
    ctx: Context,
    provider_type_filter: Optional[str] = Field(
        None,
        description='Filter by provider type: Bitbucket, GitHub, GitHubEnterpriseServer, GitLab, GitLabSelfManaged',
    ),
    max_results: int = Field(
        DEFAULT_MAX_RESULTS,
        description='Maximum number of results to return',
        ge=1,
        le=100,
    ),
    next_token: Optional[str] = Field(
        None,
        description='Token for pagination from a previous response',
    ),
) -> Dict[str, Any]:
    """List available CodeConnections.

    This function retrieves existing CodeConnections that can be used with
    HealthOmics workflows. Connections can be filtered by provider type and
    results are paginated.

    Args:
        ctx: MCP context for error reporting
        provider_type_filter: Optional filter by Git provider type
        max_results: Maximum number of results to return (default: 100)
        next_token: Token for pagination from a previous response

    Returns:
        Dictionary containing:
        - connections: List of connection objects with connection_arn, connection_name,
          connection_status, provider_type, and ready_for_workflows flag
        - nextToken: Token for retrieving the next page (if more results exist)

    Raises:
        ValueError: If provider_type_filter is invalid
        botocore.exceptions.BotoCoreError: If AWS API call fails
    """
    # Handle Field objects for optional parameters (FastMCP compatibility)
    if hasattr(provider_type_filter, 'default') and not isinstance(
        provider_type_filter, (str, type(None))
    ):
        provider_type_filter = getattr(provider_type_filter, 'default', None)

    if hasattr(max_results, 'default') and not isinstance(max_results, int):
        max_results = getattr(max_results, 'default', DEFAULT_MAX_RESULTS)

    if hasattr(next_token, 'default') and not isinstance(next_token, (str, type(None))):
        next_token = getattr(next_token, 'default', None)

    # Validate provider_type_filter if provided
    if provider_type_filter:
        await validate_provider_type(ctx, provider_type_filter)

    client = get_codeconnections_client()

    # Build API parameters
    params: Dict[str, Any] = {'MaxResults': max_results}

    if provider_type_filter:
        params['ProviderTypeFilter'] = provider_type_filter

    if next_token:
        params['NextToken'] = next_token

    try:
        response = client.list_connections(**params)

        # Transform the response to a more user-friendly format
        connections = []
        for connection in response.get('Connections', []):
            connection_status = connection.get('ConnectionStatus')
            connections.append(
                {
                    'connection_arn': connection.get('ConnectionArn'),
                    'connection_name': connection.get('ConnectionName'),
                    'connection_status': connection_status,
                    'provider_type': connection.get('ProviderType'),
                    'ready_for_workflows': connection_status == 'AVAILABLE',
                }
            )

        result: Dict[str, Any] = {'connections': connections}

        # Include next_token for pagination if more results exist
        if 'NextToken' in response:
            result['nextToken'] = response['NextToken']

        return result

    except botocore.exceptions.ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        error_msg = e.response.get('Error', {}).get('Message', str(e))
        error_message = f'AWS error listing CodeConnections: {error_code} - {error_msg}'
        logger.error(error_message)
        await ctx.error(error_message)
        raise
    except botocore.exceptions.BotoCoreError as e:
        error_message = f'AWS error listing CodeConnections: {str(e)}'
        logger.error(error_message)
        await ctx.error(error_message)
        raise
    except Exception as e:
        error_message = f'Unexpected error listing CodeConnections: {str(e)}'
        logger.error(error_message)
        await ctx.error(error_message)
        raise


async def create_codeconnection(
    ctx: Context,
    connection_name: str = Field(
        ...,
        description='Name for the new connection',
    ),
    provider_type: str = Field(
        ...,
        description='Git provider type: Bitbucket, GitHub, GitHubEnterpriseServer, GitLab, GitLabSelfManaged',
    ),
    tags: Optional[Dict[str, str]] = Field(
        None,
        description='Optional tags to apply to the connection',
    ),
) -> Dict[str, Any]:
    """Create a new CodeConnection.

    This function creates a new AWS CodeConnection for connecting to a
    third-party Git provider. The connection will be created in PENDING
    status and requires OAuth authorization in the AWS Console to become
    AVAILABLE.

    Args:
        ctx: MCP context for error reporting
        connection_name: Name for the new connection
        provider_type: Git provider type (Bitbucket, GitHub, GitHubEnterpriseServer,
            GitLab, GitLabSelfManaged)
        tags: Optional tags to apply to the connection

    Returns:
        Dictionary containing:
        - connection_arn: ARN of the created connection
        - console_url: AWS Console URL for completing OAuth authorization
        - guidance: Instructions for completing the connection setup

    Raises:
        ValueError: If provider_type is invalid
        botocore.exceptions.BotoCoreError: If AWS API call fails
    """
    # Handle Field objects for optional parameters (FastMCP compatibility)
    if hasattr(tags, 'default') and not isinstance(tags, (dict, type(None))):
        tags = getattr(tags, 'default', None)

    # Validate provider_type
    await validate_provider_type(ctx, provider_type)

    client = get_codeconnections_client()

    # Build API parameters
    params: Dict[str, Any] = {
        'ConnectionName': connection_name,
        'ProviderType': provider_type,
    }

    if tags:
        # Convert tags dict to list of Tag objects for the API
        params['Tags'] = [{'Key': k, 'Value': v} for k, v in tags.items()]

    try:
        response = client.create_connection(**params)

        # Extract connection ARN from response
        connection_arn = response.get('ConnectionArn')

        # Extract region from the connection ARN
        # ARN format: arn:aws:codeconnections:{region}:{account}:connection/{id}
        arn_parts = connection_arn.split(':')
        region = arn_parts[3] if len(arn_parts) > 3 else 'us-east-1'

        # Generate console URL for OAuth authorization
        console_url = generate_console_url(region)

        # Get guidance for PENDING status (new connections are always PENDING)
        guidance = get_status_guidance('PENDING')

        return {
            'connection_arn': connection_arn,
            'console_url': console_url,
            'guidance': guidance,
        }

    except botocore.exceptions.ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        error_msg = e.response.get('Error', {}).get('Message', str(e))
        error_message = f'AWS error creating CodeConnection: {error_code} - {error_msg}'
        logger.error(error_message)
        await ctx.error(error_message)
        raise
    except botocore.exceptions.BotoCoreError as e:
        error_message = f'AWS error creating CodeConnection: {str(e)}'
        logger.error(error_message)
        await ctx.error(error_message)
        raise
    except Exception as e:
        error_message = f'Unexpected error creating CodeConnection: {str(e)}'
        logger.error(error_message)
        await ctx.error(error_message)
        raise


async def get_codeconnection(
    ctx: Context,
    connection_arn: str = Field(
        ...,
        description='ARN of the connection to retrieve',
    ),
) -> Dict[str, Any]:
    """Get details about a specific CodeConnection.

    This function retrieves detailed information about a specific AWS
    CodeConnection, including its current status and guidance on next steps.
    Use this to check if a connection is ready for use with HealthOmics
    workflows or if OAuth authorization is still required.

    Args:
        ctx: MCP context for error reporting
        connection_arn: ARN of the connection to retrieve

    Returns:
        Dictionary containing:
        - connection_arn: ARN of the connection
        - connection_name: Name of the connection
        - connection_status: Status (PENDING, AVAILABLE, ERROR)
        - provider_type: Git provider type
        - owner_account_id: AWS account that owns the connection
        - host_arn: ARN of the host (for self-managed providers, if present)
        - guidance: Status-based guidance message for the user

    Raises:
        ValueError: If connection_arn format is invalid
        botocore.exceptions.ClientError: If connection is not found or AWS API call fails
        botocore.exceptions.BotoCoreError: If AWS API call fails
    """
    # Validate connection_arn format
    await validate_connection_arn(ctx, connection_arn)

    client = get_codeconnections_client()

    try:
        response = client.get_connection(ConnectionArn=connection_arn)

        # Extract connection details from response
        connection = response.get('Connection', {})
        connection_status = connection.get('ConnectionStatus')

        # Build result with all required fields
        result: Dict[str, Any] = {
            'connection_arn': connection.get('ConnectionArn'),
            'connection_name': connection.get('ConnectionName'),
            'connection_status': connection_status,
            'provider_type': connection.get('ProviderType'),
            'owner_account_id': connection.get('OwnerAccountId'),
            'guidance': get_status_guidance(connection_status),
        }

        # Include host_arn if present (for self-managed providers)
        host_arn = connection.get('HostArn')
        if host_arn:
            result['host_arn'] = host_arn

        return result

    except botocore.exceptions.ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        error_msg = e.response.get('Error', {}).get('Message', str(e))

        # Handle connection not found specifically
        if error_code == 'ResourceNotFoundException':
            error_message = f'Connection not found: {connection_arn}'
            logger.error(error_message)
            await ctx.error(error_message)
            raise

        error_message = f'AWS error getting CodeConnection: {error_code} - {error_msg}'
        logger.error(error_message)
        await ctx.error(error_message)
        raise
    except botocore.exceptions.BotoCoreError as e:
        error_message = f'AWS error getting CodeConnection: {str(e)}'
        logger.error(error_message)
        await ctx.error(error_message)
        raise
    except Exception as e:
        error_message = f'Unexpected error getting CodeConnection: {str(e)}'
        logger.error(error_message)
        await ctx.error(error_message)
        raise
