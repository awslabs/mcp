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

"""Start migration tool for ElastiCache MCP server."""

from ...common.connection import ElastiCacheConnectionManager
from ...common.decorators import handle_exceptions
from ...common.server import mcp
from pydantic import BaseModel, ConfigDict, Field
from typing import Any, Dict, List, Union


class CustomerNodeEndpoint(BaseModel):
    """Customer node endpoint model."""

    Address: str = Field(..., description='The address of the node endpoint')
    Port: int = Field(..., description='The port of the node endpoint')
    model_config = ConfigDict(validate_by_name=True, arbitrary_types_allowed=True)


class StartMigrationRequest(BaseModel):
    """Request model for starting migration to an ElastiCache replication group."""

    model_config = ConfigDict(validate_by_name=True, arbitrary_types_allowed=True)

    replication_group_id: str = Field(
        ..., description='The ID of the replication group to which data should be migrated'
    )
    customer_node_endpoint_list: Union[str, List[CustomerNodeEndpoint]] = Field(
        ...,
        description='List of endpoints from which data should be migrated. For Valkey or Redis OSS (cluster mode disabled), the list should have only one element.',
    )


def prepare_request_dict(request: StartMigrationRequest) -> Dict[str, Any]:
    """Prepare the request dictionary for the AWS API.

    Args:
        request: The StartMigrationRequest object

    Returns:
        Dict containing the properly formatted request parameters
    """
    # Start with required parameters
    start_migration_request: Dict[str, Any] = {
        'ReplicationGroupId': request.replication_group_id,
    }

    # Process customer node endpoint list
    if isinstance(request.customer_node_endpoint_list, str):
        # Parse shorthand syntax: Address=string,Port=integer
        try:
            pairs = [
                p.strip() for p in request.customer_node_endpoint_list.split(',') if p.strip()
            ]
            endpoint = {}
            for pair in pairs:
                if '=' not in pair:
                    raise ValueError(
                        'Invalid endpoint format. Each parameter must be in key=value format'
                    )
                key, value = pair.split('=', 1)
                key = key.strip()
                value = value.strip()
                if not key or not value:
                    raise ValueError('Key or value cannot be empty')

                if key == 'Address':
                    endpoint['Address'] = value
                elif key == 'Port':
                    try:
                        endpoint['Port'] = int(value)
                    except ValueError:
                        raise ValueError(f'Port must be an integer: {value}')
                else:
                    raise ValueError(f'Invalid parameter: {key}')

            # Validate required fields
            if 'Address' not in endpoint:
                raise ValueError('Missing required field: Address')
            if 'Port' not in endpoint:
                raise ValueError('Missing required field: Port')

            start_migration_request['CustomerNodeEndpointList'] = [endpoint]
        except Exception as e:
            raise ValueError(
                f'Invalid endpoint shorthand syntax. Expected format: Address=string,Port=integer. Error: {str(e)}'
            )
    elif isinstance(request.customer_node_endpoint_list, list):
        # Handle list format
        if len(request.customer_node_endpoint_list) < 1:
            raise ValueError('CustomerNodeEndpointList should have at least one element')

        endpoints = [
            endpoint.model_dump(exclude_none=True)
            for endpoint in request.customer_node_endpoint_list
        ]
        start_migration_request['CustomerNodeEndpointList'] = endpoints
    else:
        raise ValueError(
            'CustomerNodeEndpointList must be a string or a list with at least one element'
        )

    return start_migration_request


@mcp.tool(name='start-migration')
@handle_exceptions
async def start_migration(request: StartMigrationRequest) -> Dict:
    """Start migration to an Amazon ElastiCache replication group.

    This tool starts migration from a Redis instance to an ElastiCache replication group.
    It initiates the data migration process from the specified endpoint(s) to
    the target replication group.

    Args:
        request: The StartMigrationRequest object containing:
            - replication_group_id: The ID of the replication group to which data should be migrated
            - customer_node_endpoint_list: List of endpoints from which data should be migrated.
              For Valkey or Redis OSS (cluster mode disabled), the list should have only one element.

    Returns:
        Dict containing information about the migration start result.
    """
    # Get ElastiCache client
    elasticache_client = ElastiCacheConnectionManager.get_connection()

    # Prepare request dictionary
    start_request = prepare_request_dict(request)

    # Start the migration
    response = elasticache_client.start_migration(**start_request)
    return response
