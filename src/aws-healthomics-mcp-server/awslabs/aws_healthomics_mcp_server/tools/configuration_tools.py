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

"""Configuration management tools for the AWS HealthOmics MCP server."""

from awslabs.aws_healthomics_mcp_server.consts import (
    CONFIGURATION_NAME_MAX_LENGTH,
    DEFAULT_MAX_RESULTS,
    ERROR_CONFIGURATION_NAME_TOO_LONG,
    ERROR_RESERVED_CONFIGURATION_NAME,
    RESERVED_CONFIGURATION_NAMES,
)
from awslabs.aws_healthomics_mcp_server.utils.aws_utils import (
    get_omics_client,
)
from awslabs.aws_healthomics_mcp_server.utils.error_utils import (
    handle_tool_error,
)
from awslabs.aws_healthomics_mcp_server.utils.validation_utils import (
    parse_tags,
)
from loguru import logger
from mcp.server.fastmcp import Context
from pydantic import Field
from typing import Any, Dict, Optional


async def create_configuration(
    ctx: Context,
    name: str = Field(
        ...,
        description='Configuration name (max 50 chars)',
    ),
    run_configurations: Optional[Dict[str, Any]] = Field(
        None,
        description='Run configuration settings (e.g. securityGroupIds and subnetIds)',
    ),
    description: Optional[str] = Field(
        None,
        description='Configuration description',
    ),
    tags: Optional[Dict[str, str]] = Field(
        None,
        description='Resource tags',
    ),
    aws_profile: Optional[str] = Field(
        None,
        description='AWS profile name for this operation. Overrides the default credential chain.',
    ),
    aws_region: Optional[str] = Field(
        None,
        description='AWS region for this operation. Overrides the server default.',
    ),
) -> Dict[str, Any]:
    """Create a new HealthOmics configuration.

    Args:
        ctx: MCP context for error reporting
        name: Configuration name (max 50 characters)
        run_configurations: Optional run configuration settings (e.g. securityGroupIds and subnetIds)
        description: Optional configuration description
        tags: Optional resource tags
        aws_profile: Optional AWS profile name override
        aws_region: Optional AWS region override

    Returns:
        Dictionary containing the created configuration information or error dict
    """
    try:
        # Validate name length
        if len(name) > CONFIGURATION_NAME_MAX_LENGTH:
            return await handle_tool_error(
                ctx,
                ValueError(
                    ERROR_CONFIGURATION_NAME_TOO_LONG.format(CONFIGURATION_NAME_MAX_LENGTH)
                ),
                'Error creating configuration',
            )

        # Validate name is not reserved (case-insensitive)
        if name.lower() in [n.lower() for n in RESERVED_CONFIGURATION_NAMES]:
            return await handle_tool_error(
                ctx,
                ValueError(ERROR_RESERVED_CONFIGURATION_NAME.format(name)),
                'Error creating configuration',
            )

        client = get_omics_client(region_name=aws_region, profile_name=aws_profile)

        params: Dict[str, Any] = {
            'name': name,
        }

        if run_configurations:
            params['runConfigurations'] = run_configurations

        if description:
            params['description'] = description

        if tags:
            try:
                params['tags'] = parse_tags(tags)
            except ValueError as e:
                return await handle_tool_error(ctx, e, 'Error parsing tags')

        logger.info(f'Creating configuration: {name}')
        response = client.create_configuration(**params)

        return {
            'arn': response.get('arn'),
            'uuid': response.get('uuid'),
            'name': response.get('name'),
            'status': response.get('status'),
            'creationTime': str(response.get('creationTime', '')),
        }
    except Exception as e:
        return await handle_tool_error(ctx, e, 'Error creating configuration')


async def get_configuration(
    ctx: Context,
    name: str = Field(
        ...,
        description='Configuration name',
    ),
    aws_profile: Optional[str] = Field(
        None,
        description='AWS profile name for this operation. Overrides the default credential chain.',
    ),
    aws_region: Optional[str] = Field(
        None,
        description='AWS region for this operation. Overrides the server default.',
    ),
) -> Dict[str, Any]:
    """Get details of a specific HealthOmics configuration.

    Args:
        ctx: MCP context for error reporting
        name: Configuration name
        aws_profile: Optional AWS profile name override
        aws_region: Optional AWS region override

    Returns:
        Dictionary containing the configuration details or error dict
    """
    try:
        client = get_omics_client(region_name=aws_region, profile_name=aws_profile)

        logger.info(f'Getting configuration: {name}')
        response = client.get_configuration(name=name)

        return {
            'arn': response.get('arn'),
            'uuid': response.get('uuid'),
            'name': response.get('name'),
            'runConfigurations': response.get('runConfigurations'),
            'status': response.get('status'),
            'creationTime': str(response.get('creationTime', '')),
            'tags': response.get('tags', {}),
        }
    except Exception as e:
        return await handle_tool_error(ctx, e, 'Error getting configuration')


async def list_configurations(
    ctx: Context,
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
    aws_profile: Optional[str] = Field(
        None,
        description='AWS profile name for this operation. Overrides the default credential chain.',
    ),
    aws_region: Optional[str] = Field(
        None,
        description='AWS region for this operation. Overrides the server default.',
    ),
) -> Dict[str, Any]:
    """List HealthOmics configurations.

    Args:
        ctx: MCP context for error reporting
        max_results: Maximum number of results to return
        next_token: Token for pagination
        aws_profile: Optional AWS profile name override
        aws_region: Optional AWS region override

    Returns:
        Dictionary containing configuration summaries and next token if available, or error dict
    """
    try:
        client = get_omics_client(region_name=aws_region, profile_name=aws_profile)

        params: Dict[str, Any] = {'maxResults': max_results}

        if next_token:
            params['nextToken'] = next_token

        logger.info('Listing configurations')
        response = client.list_configurations(**params)

        configurations = []
        for item in response.get('items', []):
            configurations.append(
                {
                    'arn': item.get('arn'),
                    'name': item.get('name'),
                    'description': item.get('description'),
                    'status': item.get('status'),
                    'creationTime': str(item.get('creationTime', '')),
                }
            )

        result: Dict[str, Any] = {'configurations': configurations}
        if 'nextToken' in response:
            result['nextToken'] = response['nextToken']

        return result
    except Exception as e:
        return await handle_tool_error(ctx, e, 'Error listing configurations')


async def delete_configuration(
    ctx: Context,
    name: str = Field(
        ...,
        description='Configuration name',
    ),
    aws_profile: Optional[str] = Field(
        None,
        description='AWS profile name for this operation. Overrides the default credential chain.',
    ),
    aws_region: Optional[str] = Field(
        None,
        description='AWS region for this operation. Overrides the server default.',
    ),
) -> Dict[str, Any]:
    """Delete a HealthOmics configuration.

    Args:
        ctx: MCP context for error reporting
        name: Configuration name
        aws_profile: Optional AWS profile name override
        aws_region: Optional AWS region override

    Returns:
        Dictionary containing the deletion confirmation or error dict
    """
    try:
        client = get_omics_client(region_name=aws_region, profile_name=aws_profile)

        logger.info(f'Deleting configuration: {name}')
        client.delete_configuration(name=name)

        return {
            'name': name,
            'status': 'DELETING',
        }
    except Exception as e:
        return await handle_tool_error(ctx, e, 'Error deleting configuration')
