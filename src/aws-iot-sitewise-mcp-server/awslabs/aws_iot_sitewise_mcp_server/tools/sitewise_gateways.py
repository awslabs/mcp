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

"""AWS IoT SiteWise Gateways and Time Series Management Tools."""

from awslabs.aws_iot_sitewise_mcp_server.client import create_sitewise_client
from awslabs.aws_iot_sitewise_mcp_server.tool_metadata import tool_metadata
from awslabs.aws_iot_sitewise_mcp_server.validation import (
    validate_asset_id,
)
from botocore.exceptions import ClientError
from mcp.server.fastmcp.tools import Tool
from pydantic import Field
from pydantic.fields import FieldInfo
from typing import Any, Dict, Optional


@tool_metadata(readonly=False)
def create_gateway(
    gateway_name: str = Field(..., description='A unique, friendly name for the gateway'),
    gateway_platform: Dict[str, Any] = Field(
        ..., description="The gateway's platform configuration"
    ),
    region: str = Field('us-east-1', description='AWS region'),
    tags: Optional[Dict[str, str]] = Field(None, description='Metadata tags for the gateway'),
) -> Dict[str, Any]:
    """Create a gateway in AWS IoT SiteWise.

    Args:
            gateway_name: A unique, friendly name for the gateway
            gateway_platform: The gateway's platform (Greengrass V1 or V2)
            region: AWS region (default: us-east-1)
            tags: A list of key-value pairs that contain metadata for the gateway

    Returns:
            Dictionary containing gateway creation response
    """
    try:
        client = create_sitewise_client(region)

        params: Dict[str, Any] = {
            'gatewayName': gateway_name,
            'gatewayPlatform': gateway_platform,
        }

        if tags:
            params['tags'] = tags

        response = client.create_gateway(**params)
        return {
            'success': True,
            'gateway_id': response['gatewayId'],
            'gateway_arn': response['gatewayArn'],
        }

    except ClientError as e:
        return {
            'success': False,
            'error': str(e),
            'error_code': e.response['Error']['Code'],
        }


@tool_metadata(readonly=True)
def describe_gateway(
    gateway_id: str = Field(..., description='The ID of the gateway device'),
    region: str = Field('us-east-1', description='AWS region'),
) -> Dict[str, Any]:
    """Retrieve information about a gateway.

    Args:
        gateway_id: The ID of the gateway device
        region: AWS region (default: us-east-1)

    Returns:
        Dictionary containing gateway information
    """
    try:
        client = create_sitewise_client(region)

        response = client.describe_gateway(gatewayId=gateway_id)

        return {
            'success': True,
            'gateway_id': response['gatewayId'],
            'gateway_name': response['gatewayName'],
            'gateway_arn': response['gatewayArn'],
            'gateway_platform': response['gatewayPlatform'],
            'gateway_capability_summaries': response['gatewayCapabilitySummaries'],
            'creation_date': response['creationDate'].isoformat(),
            'last_update_date': response['lastUpdateDate'].isoformat(),
        }

    except ClientError as e:
        return {
            'success': False,
            'error': str(e),
            'error_code': e.response['Error']['Code'],
        }


@tool_metadata(readonly=True)
def list_gateways(
    region: str = Field('us-east-1', description='AWS region'),
    next_token: Optional[str] = Field(
        None, description='The token to be used for the next set of paginated results'
    ),
    max_results: int = Field(50, description='The maximum number of results to return (1-250)'),
) -> Dict[str, Any]:
    """Retrieve a paginated list of gateways.

    Args:
        region: AWS region (default: us-east-1)
        next_token: The token to be used for the next set of paginated results
        max_results: The maximum number of results to return (
            1-250,
            default: 50)

    Returns:
        Dictionary containing list of gateways
    """
    try:
        client = create_sitewise_client(region)

        params: Dict[str, Any] = {'maxResults': max_results}
        if next_token:
            params['nextToken'] = next_token

        response = client.list_gateways(**params)

        return {
            'success': True,
            'gateway_summaries': response['gatewaySummaries'],
            'next_token': response.get('nextToken', ''),
        }

    except ClientError as e:
        return {
            'success': False,
            'error': str(e),
            'error_code': e.response['Error']['Code'],
        }


@tool_metadata(readonly=False)
def update_gateway(
    gateway_id: str = Field(..., description='The ID of the gateway to update'),
    gateway_name: str = Field(..., description='A unique, friendly name for the gateway'),
    region: str = Field('us-east-1', description='AWS region'),
) -> Dict[str, Any]:
    """Update a gateway's name.

    Args:
        gateway_id: The ID of the gateway to update
        gateway_name: A unique, friendly name for the gateway
        region: AWS region (default: us-east-1)

    Returns:
        Dictionary containing update response
    """
    try:
        client = create_sitewise_client(region)

        client.update_gateway(gatewayId=gateway_id, gatewayName=gateway_name)

        return {'success': True, 'message': 'Gateway updated successfully'}

    except ClientError as e:
        return {
            'success': False,
            'error': str(e),
            'error_code': e.response['Error']['Code'],
        }


@tool_metadata(readonly=False)
def delete_gateway(
    gateway_id: str = Field(..., description='The ID of the gateway to delete'),
    region: str = Field('us-east-1', description='AWS region'),
) -> Dict[str, Any]:
    """Delete a gateway.

    Args:
        gateway_id: The ID of the gateway to delete
        region: AWS region (default: us-east-1)

    Returns:
        Dictionary containing deletion response
    """
    try:
        client = create_sitewise_client(region)

        client.delete_gateway(gatewayId=gateway_id)
        return {'success': True, 'message': 'Gateway deleted successfully'}

    except ClientError as e:
        return {
            'success': False,
            'error': str(e),
            'error_code': e.response['Error']['Code'],
        }


@tool_metadata(readonly=True)
def describe_gateway_capability_configuration(
    gateway_id: str = Field(
        ..., description='The ID of the gateway that defines the capability configuration'
    ),
    capability_namespace: str = Field(
        ..., description='The namespace of the capability configuration'
    ),
    region: str = Field('us-east-1', description='AWS region'),
) -> Dict[str, Any]:
    """Retrieve information about a gateway capability configuration.

    Args:
        gateway_id: The ID of the gateway that defines the capability \
            configuration
        capability_namespace: The namespace of the capability configuration
        region: AWS region (default: us-east-1)

    Returns:
        Dictionary containing capability configuration information
    """
    try:
        client = create_sitewise_client(region)

        response = client.describe_gateway_capability_configuration(
            gatewayId=gateway_id, capabilityNamespace=capability_namespace
        )

        return {
            'success': True,
            'gateway_id': response['gatewayId'],
            'capability_namespace': response['capabilityNamespace'],
            'capability_configuration': response['capabilityConfiguration'],
            'capability_sync_status': response['capabilitySyncStatus'],
        }

    except ClientError as e:
        return {
            'success': False,
            'error': str(e),
            'error_code': e.response['Error']['Code'],
        }


@tool_metadata(readonly=False)
def update_gateway_capability_configuration(
    gateway_id: str = Field(..., description='The ID of the gateway to be updated'),
    capability_namespace: str = Field(
        ..., description='The namespace of the gateway capability configuration to be updated'
    ),
    capability_configuration: str = Field(
        ...,
        description='The JSON document that defines the configuration for the gateway capability',
    ),
    region: str = Field('us-east-1', description='AWS region'),
) -> Dict[str, Any]:
    """Update a gateway capability configuration.

    Args:
        gateway_id: The ID of the gateway to be updated
        capability_namespace: The namespace of the gateway capability \
            configuration to be updated
        capability_configuration: The JSON document that defines the \
            configuration for the gateway capability
        region: AWS region (default: us-east-1)

    Returns:
        Dictionary containing update response
    """
    try:
        client = create_sitewise_client(region)

        response = client.update_gateway_capability_configuration(
            gatewayId=gateway_id,
            capabilityNamespace=capability_namespace,
            capabilityConfiguration=capability_configuration,
        )

        return {
            'success': True,
            'capability_namespace': response['capabilityNamespace'],
            'capability_sync_status': response['capabilitySyncStatus'],
        }

    except ClientError as e:
        return {
            'success': False,
            'error': str(e),
            'error_code': e.response['Error']['Code'],
        }


@tool_metadata(readonly=True)
def list_time_series(
    region: str = Field('us-east-1', description='AWS region'),
    next_token: Optional[str] = Field(
        None, description='The token to be used for the next set of paginated results'
    ),
    max_results: int = Field(50, description='The maximum number of results to return (1-250)'),
    asset_id: Optional[str] = Field(
        None, description='The ID of the asset in which the asset property was created'
    ),
    alias_prefix: Optional[str] = Field(None, description='The alias prefix of the time series'),
    time_series_type: Optional[str] = Field(
        None, description='The type of the time series (ASSOCIATED, DISASSOCIATED)'
    ),
) -> Dict[str, Any]:
    """Retrieve a paginated list of time series (data streams).

    Args:
        region: AWS region (default: us-east-1)
        next_token: The token to be used for the next set of paginated results
        max_results: The maximum number of results to return (
            1-250,
            default: 50) \
        asset_id: The ID of the asset in which the asset \
                \
                \
                \
                property was created
        alias_prefix: The alias prefix of the time series
        time_series_type: The type of the time series (
            ASSOCIATED,
            DISASSOCIATED)

    Returns:
        Dictionary containing list of time series
    """
    try:
        # Validate parameters
        if asset_id and not isinstance(asset_id, FieldInfo):
            validate_asset_id(asset_id)

        client = create_sitewise_client(region)

        params: Dict[str, Any] = {'maxResults': max_results}

        if next_token:
            params['nextToken'] = next_token
        if asset_id:
            params['assetId'] = asset_id
        if alias_prefix:
            params['aliasPrefix'] = alias_prefix
        if time_series_type:
            params['timeSeriesType'] = time_series_type

        response = client.list_time_series(**params)

        return {
            'success': True,
            'time_series_summaries': response['TimeSeriesSummaries'],
            'next_token': response.get('nextToken', ''),
        }

    except ClientError as e:
        return {
            'success': False,
            'error': str(e),
            'error_code': e.response['Error']['Code'],
        }


@tool_metadata(readonly=True)
def describe_time_series(
    alias: Optional[str] = Field(None, description='The alias that identifies the time series'),
    asset_id: Optional[str] = Field(
        None, description='The ID of the asset in which the asset property was created'
    ),
    property_id: Optional[str] = Field(None, description='The ID of the asset property'),
    region: str = Field('us-east-1', description='AWS region'),
) -> Dict[str, Any]:
    """Retrieve information about a time series (data stream).

    Args:
        alias: The alias that identifies the time series
        asset_id: The ID of the asset in which the asset property was created
        property_id: The ID of the asset property
        region: AWS region (default: us-east-1)

    Returns:
        Dictionary containing time series information
    """
    try:
        # Validate parameters
        if asset_id and not isinstance(asset_id, FieldInfo):
            validate_asset_id(asset_id)

        client = create_sitewise_client(region)

        params: Dict[str, Any] = {}
        if alias:
            params['alias'] = alias
        if asset_id:
            params['assetId'] = asset_id
        if property_id:
            params['propertyId'] = property_id

        response = client.describe_time_series(**params)

        return {
            'success': True,
            'asset_id': response.get('assetId', ''),
            'property_id': response.get('propertyId', ''),
            'alias': response.get('alias', ''),
            'time_series_id': response['timeSeriesId'],
            'data_type': response['dataType'],
            'data_type_spec': response.get('dataTypeSpec', ''),
            'time_series_creation_date': response['timeSeriesCreationDate'].isoformat(),
            'time_series_last_update_date': response['timeSeriesLastUpdateDate'].isoformat(),
            'time_series_arn': response['timeSeriesArn'],
        }

    except ClientError as e:
        return {
            'success': False,
            'error': str(e),
            'error_code': e.response['Error']['Code'],
        }


@tool_metadata(readonly=False)
def associate_time_series_to_asset_property(
    alias: str = Field(..., description='The alias that identifies the time series'),
    asset_id: str = Field(
        ..., description='The ID of the asset in which the asset property was created'
    ),
    property_id: str = Field(..., description='The ID of the asset property'),
    region: str = Field('us-east-1', description='AWS region'),
    client_token: Optional[str] = Field(
        None, description='A unique case-sensitive identifier for the request'
    ),
) -> Dict[str, Any]:
    """Associate a time series (data stream) with an asset property.

    Args:
        alias: The alias that identifies the time series
        asset_id: The ID of the asset in which the asset property was created
        property_id: The ID of the asset property
        region: AWS region (default: us-east-1)
        client_token: A unique case-sensitive identifier for the request

    Returns:
        Dictionary containing association response
    """
    try:
        # Validate parameters
        if not isinstance(asset_id, FieldInfo):
            validate_asset_id(asset_id)

        client = create_sitewise_client(region)

        params: Dict[str, Any] = {
            'alias': alias,
            'assetId': asset_id,
            'propertyId': property_id,
        }

        if client_token:
            params['clientToken'] = client_token

        client.associate_time_series_to_asset_property(**params)
        return {'success': True, 'message': 'Time series associated successfully'}

    except ClientError as e:
        return {
            'success': False,
            'error': str(e),
            'error_code': e.response['Error']['Code'],
        }


@tool_metadata(readonly=False)
def disassociate_time_series_from_asset_property(
    alias: str = Field(..., description='The alias that identifies the time series'),
    asset_id: str = Field(
        ..., description='The ID of the asset in which the asset property was created'
    ),
    property_id: str = Field(..., description='The ID of the asset property'),
    region: str = Field('us-east-1', description='AWS region'),
    client_token: Optional[str] = Field(
        None, description='A unique case-sensitive identifier for the request'
    ),
) -> Dict[str, Any]:
    """Disassociate a time series (data stream) from an asset property.

    Args:
        alias: The alias that identifies the time series
        asset_id: The ID of the asset in which the asset property was created
        property_id: The ID of the asset property
        region: AWS region (default: us-east-1)
        client_token: A unique case-sensitive identifier for the request

    Returns:
        Dictionary containing disassociation response
    """
    try:
        # Validate parameters
        if not isinstance(asset_id, FieldInfo):
            validate_asset_id(asset_id)

        client = create_sitewise_client(region)

        params: Dict[str, Any] = {
            'alias': alias,
            'assetId': asset_id,
            'propertyId': property_id,
        }

        if client_token:
            params['clientToken'] = client_token

        client.disassociate_time_series_from_asset_property(**params)
        return {'success': True, 'message': 'Time series disassociated successfully'}

    except ClientError as e:
        return {
            'success': False,
            'error': str(e),
            'error_code': e.response['Error']['Code'],
        }


@tool_metadata(readonly=False)
def delete_time_series(
    alias: Optional[str] = Field(None, description='The alias that identifies the time series'),
    asset_id: Optional[str] = Field(
        None, description='The ID of the asset in which the asset property was created'
    ),
    property_id: Optional[str] = Field(None, description='The ID of the asset property'),
    region: str = Field('us-east-1', description='AWS region'),
    client_token: Optional[str] = Field(
        None, description='A unique case-sensitive identifier for the request'
    ),
) -> Dict[str, Any]:
    """Delete a time series (data stream).

    Args:
        alias: The alias that identifies the time series
        asset_id: The ID of the asset in which the asset property was created
        property_id: The ID of the asset property
        region: AWS region (default: us-east-1)
        client_token: A unique case-sensitive identifier for the request

    Returns:
        Dictionary containing deletion response
    """
    try:
        # Validate parameters
        if asset_id and not isinstance(asset_id, FieldInfo):
            validate_asset_id(asset_id)

        client = create_sitewise_client(region)

        params: Dict[str, Any] = {}
        if alias:
            params['alias'] = alias
        if asset_id:
            params['assetId'] = asset_id
        if property_id:
            params['propertyId'] = property_id
        if client_token:
            params['clientToken'] = client_token

        client.delete_time_series(**params)
        return {'success': True, 'message': 'Time series deleted successfully'}

    except ClientError as e:
        return {
            'success': False,
            'error': str(e),
            'error_code': e.response['Error']['Code'],
        }


# Create MCP tools
create_gateway_tool = Tool.from_function(
    fn=create_gateway,
    name='create_gateway',
    description=('Create a gateway in AWS IoT SiteWise to connect industrial data sources.'),
)

describe_gateway_tool = Tool.from_function(
    fn=describe_gateway,
    name='describe_gateway',
    description="""Retrieve detailed information about an AWS IoT SiteWise gateway.""",
)

list_gateways_tool = Tool.from_function(
    fn=list_gateways,
    name='list_gateways',
    description='Retrieve a paginated list of gateways in AWS IoT SiteWise.',
)

update_gateway_tool = Tool.from_function(
    fn=update_gateway,
    name='update_gateway',
    description="Update a gateway's name in AWS IoT SiteWise.",
)

delete_gateway_tool = Tool.from_function(
    fn=delete_gateway,
    name='delete_gateway',
    description='Delete a gateway from AWS IoT SiteWise.',
)

describe_gateway_capability_configuration_tool = Tool.from_function(
    fn=describe_gateway_capability_configuration,
    name='describe_gateway_capability_config',
    description=(
        'Retrieve information about a gateway capability configuration in AWS IoT SiteWise.'
    ),
)

update_gateway_capability_configuration_tool = Tool.from_function(
    fn=update_gateway_capability_configuration,
    name='update_gateway_capability_config',
    description="""Update a gateway capability configuration in AWS IoT SiteWise.""",
)

list_time_series_tool = Tool.from_function(
    fn=list_time_series,
    name='list_time_series',
    description=('Retrieve a paginated list of time series (data streams) in AWS IoT SiteWise.'),
)

describe_time_series_tool = Tool.from_function(
    fn=describe_time_series,
    name='describe_time_series',
    description=(
        'Retrieve detailed information about a time series (data stream) in AWS IoT SiteWise.'
    ),
)

associate_time_series_to_asset_property_tool = Tool.from_function(
    fn=associate_time_series_to_asset_property,
    name='link_time_series_asset_property',
    description=(
        'Associate a time series (data stream) with an asset property in AWS IoT SiteWise.'
    ),
)

disassociate_time_series_from_asset_property_tool = Tool.from_function(
    fn=disassociate_time_series_from_asset_property,
    name='unlink_time_series_asset_property',
    description=(
        'Disassociate a time series (data stream) from an asset property in AWS IoT SiteWise.'
    ),
)

delete_time_series_tool = Tool.from_function(
    fn=delete_time_series,
    name='delete_time_series',
    description='Delete a time series (data stream) from AWS IoT SiteWise.',
)
