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

"""Endpoint operations for DMS MCP Server."""

from awslabs.dms_mcp_server.aws_client import (
    get_dms_client,
    handle_aws_error,
)
from awslabs.dms_mcp_server.common.server import mcp
from awslabs.dms_mcp_server.consts import DEFAULT_MAX_RECORDS
from awslabs.dms_mcp_server.context import Context
from awslabs.dms_mcp_server.models import (
    ConnectionListResponse,
    ConnectionResponse,
    ConnectionTestResponse,
    CreateEndpointResponse,
    EndpointListResponse,
    EndpointResponse,
)
from loguru import logger
from pydantic import Field
from typing import Any, Dict, List, Literal, Optional


@mcp.tool()
async def describe_endpoints(
    endpoint_identifier: Optional[str] = Field(
        default=None, description='Filter by specific endpoint identifier'
    ),
    endpoint_type: Optional[Literal['source', 'target']] = Field(
        default=None, description='Filter by endpoint type'
    ),
    engine_name: Optional[str] = Field(default=None, description='Filter by engine name'),
    max_records: int = Field(
        default=DEFAULT_MAX_RECORDS, description='Maximum number of records to return'
    ),
    marker: Optional[str] = Field(default=None, description='Pagination token'),
) -> EndpointListResponse:
    """Describe one or more DMS endpoints.

    When endpoint_identifier or endpoint_type or engine_name is provided, only endpoints with an exact match will be returned.
    If no matching endpoints are found, an empty list will be returned.
    """
    try:
        dms_client = get_dms_client()

        describe_params = {'MaxRecords': max_records}

        filters = []
        if endpoint_identifier is not None:
            filters.append({'Name': 'endpoint-id', 'Values': [endpoint_identifier]})
        if endpoint_type is not None:
            filters.append({'Name': 'endpoint-type', 'Values': [endpoint_type]})
        if engine_name is not None:
            filters.append({'Name': 'engine-name', 'Values': [engine_name]})
        if filters:
            describe_params['Filters'] = filters
        if marker is not None:
            describe_params['Marker'] = marker

        response = dms_client.describe_endpoints(**describe_params)

        endpoints = [
            EndpointResponse(
                endpoint_identifier=endpoint['EndpointIdentifier'],
                endpoint_arn=endpoint['EndpointArn'],
                endpoint_type=endpoint['EndpointType'],
                engine_name=endpoint['EngineName'],
                username=endpoint.get('Username'),
                server_name=endpoint.get('ServerName'),
                port=endpoint.get('Port'),
                database_name=endpoint.get('DatabaseName'),
                status=endpoint['Status'],
                ssl_mode=endpoint.get('SslMode'),
            )
            for endpoint in response['Endpoints']
        ]

        return EndpointListResponse(endpoints=endpoints, marker=response.get('Marker'))

    except Exception as e:
        error_msg = handle_aws_error(e)
        logger.error(f'Failed to describe endpoints: {error_msg}')
        raise ValueError(f'Failed to describe endpoints: {error_msg}')


@mcp.tool()
async def test_connection(
    replication_instance_arn: str = Field(description='The ARN of the replication instance'),
    endpoint_arn: str = Field(description='The ARN of the endpoint to test'),
) -> ConnectionTestResponse:
    """Test the connection between a replication instance and an endpoint."""
    try:
        dms_client = get_dms_client()

        response = dms_client.test_connection(
            ReplicationInstanceArn=replication_instance_arn, EndpointArn=endpoint_arn
        )

        connection = response['Connection']
        return ConnectionTestResponse(
            replication_instance_arn=connection['ReplicationInstanceArn'],
            endpoint_arn=connection['EndpointArn'],
            status=connection['Status'],
            last_failure_message=connection.get('LastFailureMessage'),
        )

    except Exception as e:
        error_msg = handle_aws_error(e)
        logger.error(f'Failed to test connection: {error_msg}')
        raise ValueError(f'Failed to test connection: {error_msg}')


@mcp.tool()
async def describe_connections(
    filters: Optional[List[Dict[str, Any]]] = Field(
        default=None, description='Filters to apply to the connection list'
    ),
    max_records: int = Field(
        default=DEFAULT_MAX_RECORDS, description='Maximum number of records to return'
    ),
    marker: Optional[str] = Field(default=None, description='Pagination token'),
) -> ConnectionListResponse:
    """Describe connections between replication instances and endpoints.

    Returns information about the connections that have been created between replication instances and endpoints.
    Connections are created when you test connectivity between a replication instance and an endpoint.

    Args:
        filters: Optional filters to apply to the connection list. Each filter is a dictionary with:
                - Name (string): The filter name. Valid values: 'endpoint-arn' | 'replication-instance-arn'
                - Values (list): List of string values to filter by
        max_records: Maximum number of records to return (20-100)
        marker: Pagination token from previous request

    Example filters:
        [
            {
                "Name": "endpoint-arn",
                "Values": ["arn:aws:dms:region:account:endpoint:endpoint-id"]
            },
            {
                "Name": "replication-instance-arn",
                "Values": ["arn:aws:dms:region:account:rep:instance-id"]
            }
        ]
    """
    try:
        dms_client = get_dms_client()

        describe_params = {'MaxRecords': max_records}

        # Validate and add filters if provided
        if filters:
            # Validate filter format
            valid_filter_names = {'endpoint-arn', 'replication-instance-arn'}
            for filter_item in filters:
                if not isinstance(filter_item, dict):
                    raise ValueError('Each filter must be a dictionary')

                if 'Name' not in filter_item or 'Values' not in filter_item:
                    raise ValueError("Each filter must have 'Name' and 'Values' keys")

                filter_name = filter_item['Name']
                if filter_name not in valid_filter_names:
                    raise ValueError(
                        f"Invalid filter name '{filter_name}'. Valid names: {', '.join(valid_filter_names)}"
                    )

                if not isinstance(filter_item['Values'], list):
                    raise ValueError("Filter 'Values' must be a list")

                if not filter_item['Values']:
                    raise ValueError("Filter 'Values' cannot be empty")

            describe_params['Filters'] = filters

        if marker:
            describe_params['Marker'] = marker

        response = dms_client.describe_connections(**describe_params)

        connections = [
            ConnectionResponse(
                replication_instance_arn=connection['ReplicationInstanceArn'],
                endpoint_arn=connection['EndpointArn'],
                status=connection['Status'],
                last_failure_message=connection.get('LastFailureMessage'),
                endpoint_identifier=connection['EndpointIdentifier'],
                replication_instance_identifier=connection['ReplicationInstanceIdentifier'],
            )
            for connection in response['Connections']
        ]

        return ConnectionListResponse(connections=connections, marker=response.get('Marker'))

    except Exception as e:
        error_msg = handle_aws_error(e)
        logger.error(f'Failed to describe connections: {error_msg}')
        raise ValueError(f'Failed to describe connections: {error_msg}')


@mcp.tool()
async def create_endpoint(
    endpoint_identifier: str = Field(description='A unique name for the endpoint identifier'),
    endpoint_type: Literal['source', 'target'] = Field(
        description='The type of endpoint (source or target)'
    ),
    engine_name: Literal[
        'mysql', 'oracle', 'postgres', 'mariadb', 'aurora', 'aurora-postgresql'
    ] = Field(
        description='The type of engine for the endpoint (mysql, oracle, postgres, mariadb, aurora, aurora-postgresql)'
    ),
    username: str = Field(
        description='The user name to be used to log in to the endpoint database'
    ),
    password: str = Field(
        description='The password to be used to log in to the endpoint database'
    ),
    server_name: str = Field(
        description='The name of the server where the endpoint database resides'
    ),
    port: int = Field(description='The port used by the endpoint database'),
    database_name: str = Field(description='The name of the endpoint database'),
    ssl_mode: Optional[Literal['none', 'require', 'verify-ca', 'verify-full']] = Field(
        default='none',
        description='The Secure Sockets Layer (SSL) mode to use for the SSL connection',
    ),
    extra_connection_attributes: Optional[str] = Field(
        default=None, description='Additional connection attributes'
    ),
    kms_key_id: Optional[str] = Field(
        default=None,
        description='An AWS KMS key identifier that is used to encrypt the connection parameters for the endpoint',
    ),
    tags: Optional[str] = Field(
        default=None, description='One or more tags to be assigned to the endpoint (JSON format)'
    ),
) -> CreateEndpointResponse:
    """Create a new DMS endpoint.

    This creates a new endpoint that can be used as a source or target for DMS replication tasks.
    The endpoint defines connection information for a database that participates in a migration task.

    Args:
        endpoint_identifier: Unique name for the endpoint
        endpoint_type: Whether this is a 'source' or 'target' endpoint
        engine_name: Database engine type (mysql, oracle, postgres, mariadb, aurora, aurora-postgresql)
        username: Database username for authentication
        password: Database password for authentication
        server_name: Database server hostname or IP address
        port: Database server port number
        database_name: Name of the database
        ssl_mode: SSL connection mode for security
        extra_connection_attributes: Additional connection parameters
        kms_key_id: KMS key for encrypting connection parameters
        tags: Resource tags in JSON format

    Example:
        Create a MySQL source endpoint:
        endpoint_identifier = "mysql-source-endpoint"
        endpoint_type = "source"
        engine_name = "mysql"
        server_name = "mysql.example.com"
        port = 3306
        database_name = "production"
        username = "dms_user"
        password = "secure_password" # pragma: allowlist secret
    """
    # Check if write operations are allowed
    Context.require_write_access()

    try:
        dms_client = get_dms_client()

        create_params = {
            'EndpointIdentifier': endpoint_identifier,
            'EndpointType': endpoint_type,
            'EngineName': engine_name,
            'Username': username,
            'Password': password,
            'ServerName': server_name,
            'Port': port,
            'DatabaseName': database_name,
            'SslMode': ssl_mode,
        }

        # Add optional parameters only if provided (following MSK pattern)
        if extra_connection_attributes:
            create_params['ExtraConnectionAttributes'] = extra_connection_attributes
        if kms_key_id:
            create_params['KmsKeyId'] = kms_key_id
        if tags:
            import json

            try:
                tags_list = json.loads(tags)
                create_params['Tags'] = tags_list
            except json.JSONDecodeError:
                raise ValueError('tags must be valid JSON format')

        response = dms_client.create_endpoint(**create_params)
        endpoint = response['Endpoint']

        endpoint_response = EndpointResponse(
            endpoint_identifier=endpoint['EndpointIdentifier'],
            endpoint_arn=endpoint['EndpointArn'],
            endpoint_type=endpoint['EndpointType'],
            engine_name=endpoint['EngineName'],
            username=endpoint.get('Username'),
            server_name=endpoint.get('ServerName'),
            port=endpoint.get('Port'),
            database_name=endpoint.get('DatabaseName'),
            status=endpoint['Status'],
            ssl_mode=endpoint.get('SslMode'),
        )

        return CreateEndpointResponse(endpoint=endpoint_response)

    except Exception as e:
        error_msg = handle_aws_error(e)
        logger.error(f'Failed to create endpoint: {error_msg}')
        raise ValueError(f'Failed to create endpoint: {error_msg}')
