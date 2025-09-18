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

"""AWS IoT SiteWise Assets Management Tools."""

from awslabs.aws_iot_sitewise_mcp_server.client import create_sitewise_client
from awslabs.aws_iot_sitewise_mcp_server.tool_metadata import tool_metadata
from awslabs.aws_iot_sitewise_mcp_server.validation import (
    ValidationError,
    validate_asset_id,
    validate_asset_model_id,
    validate_asset_name,
    validate_max_results,
    validate_region,
    validate_service_quotas,
)
from botocore.exceptions import ClientError
from mcp.server.fastmcp.tools import Tool
from pydantic import Field
from pydantic.fields import FieldInfo
from typing import Any, Dict, Optional


@tool_metadata(readonly=False)
def create_asset(
    asset_name: str = Field(..., description='A friendly name for the asset'),
    asset_model_id: str = Field(
        ..., description='The ID of the asset model from which to create the asset'
    ),
    region: str = Field('us-east-1', description='AWS region'),
    client_token: Optional[str] = Field(
        None, description='A unique case-sensitive identifier for the request'
    ),
    tags: Optional[Dict[str, str]] = Field(None, description='Metadata tags for the asset'),
    asset_description: Optional[str] = Field(None, description='A description for the asset'),
    asset_id: Optional[str] = Field(None, description='The ID of the asset'),
    asset_external_id: Optional[str] = Field(None, description='An external ID for the asset'),
) -> Dict[str, Any]:
    """Create a new asset in AWS IoT SiteWise.

    Args:
            asset_name: A friendly name for the asset
            asset_model_id: The ID of the asset model from which to \
                create the \
                \
                asset
            region: AWS region (default: us-east-1)
            client_token: A unique case-sensitive identifier for the request
            tags: A list of key-value pairs that contain metadata for the asset
            asset_description: A description for the asset
            asset_id: The ID to assign to the asset
            asset_external_id: An external ID to assign to the asset

    Returns:
            Dictionary containing asset creation response
    """
    try:
        # Validate parameters
        validate_asset_name(asset_name)
        validate_asset_model_id(asset_model_id)
        validate_region(region)

        if asset_id:
            validate_asset_id(asset_id)

        if asset_description and len(asset_description) > 2048:
            raise ValidationError('Asset description cannot exceed 2048 characters')

        if client_token and len(client_token) > 64:
            raise ValidationError('Client token cannot exceed 64 characters')

        if tags and len(tags) > 50:
            raise ValidationError('Cannot have more than 50 tags per asset')

        # Check service quotas (approximate)
        validate_service_quotas('create_asset')

        client = create_sitewise_client(region)

        params: Dict[str, Any] = {
            'assetName': asset_name,
            'assetModelId': asset_model_id,
        }

        if client_token:
            params['clientToken'] = client_token
        if tags:
            params['tags'] = tags
        if asset_description:
            params['assetDescription'] = asset_description
        if asset_id:
            params['assetId'] = asset_id
        if asset_external_id:
            params['assetExternalId'] = asset_external_id

        response = client.create_asset(**params)
        return {
            'success': True,
            'asset_id': response['assetId'],
            'asset_arn': response['assetArn'],
            'asset_status': response['assetStatus'],
        }

    except ValidationError as e:
        return {
            'success': False,
            'error': f'Validation error: {str(e)}',
            'error_code': 'ValidationException',
        }
    except ClientError as e:
        return {
            'success': False,
            'error': str(e),
            'error_code': e.response['Error']['Code'],
        }


@tool_metadata(readonly=True)
def describe_asset(
    asset_id: str = Field(..., description='The ID of the asset'),
    region: str = Field('us-east-1', description='AWS region'),
    exclude_properties: bool = Field(
        False, description='Whether to exclude asset properties from the response'
    ),
) -> Dict[str, Any]:
    """Retrieve information about an asset.

    Args:
        asset_id: The ID of the asset
        region: AWS region (default: us-east-1)
        exclude_properties: Whether to exclude asset properties from the \
            response

    Returns:
        Dictionary containing asset information
    """
    try:
        # Validate parameters
        if not isinstance(region, FieldInfo):
            validate_region(region)
        if not isinstance(asset_id, FieldInfo):
            validate_asset_id(asset_id)

        client = create_sitewise_client(region)

        params: Dict[str, Any] = {'assetId': asset_id}
        if exclude_properties:
            params['excludeProperties'] = exclude_properties

        response = client.describe_asset(**params)

        return {
            'success': True,
            'asset_id': response['assetId'],
            'asset_arn': response['assetArn'],
            'asset_name': response['assetName'],
            'asset_model_id': response['assetModelId'],
            'asset_properties': response.get('assetProperties', []),
            'asset_hierarchies': response.get('assetHierarchies', []),
            'asset_composite_models': response.get('assetCompositeModels', []),
            'asset_status': response['assetStatus'],
            'asset_creation_date': response['assetCreationDate'].isoformat(),
            'asset_last_update_date': response['assetLastUpdateDate'].isoformat(),
            'asset_description': response.get('assetDescription', ''),
            'asset_external_id': response.get('assetExternalId', ''),
        }

    except ClientError as e:
        return {
            'success': False,
            'error': str(e),
            'error_code': e.response['Error']['Code'],
        }


@tool_metadata(readonly=True)
def list_assets(
    region: str = Field('us-east-1', description='AWS region'),
    next_token: Optional[str] = Field(
        None, description='The token to be used for the next set of paginated results'
    ),
    max_results: int = Field(50, description='The maximum number of results to return (1-250)'),
    asset_model_id: Optional[str] = Field(
        None, description='The ID of the asset model by which to filter the list of assets'
    ),
    filter_type: Optional[str] = Field(None, description='Filter assets by ALL or TOP_LEVEL'),
) -> Dict[str, Any]:
    """Retrieve a paginated list of asset summaries.

    Args:
        region: AWS region (default: us-east-1)
        next_token: The token to be used for the next set of paginated results
        max_results: The maximum number of results to return (1-250, default: 50)
        asset_model_id: The ID of the asset model by which to filter the list of assets
        filter_type: The filter for the requested list of assets (ALL, TOP_LEVEL)

    Returns:
        Dictionary containing list of assets
    """
    try:
        # Validate parameters
        validate_region(region)
        validate_max_results(max_results, min_val=1, max_val=250)

        if asset_model_id:
            validate_asset_model_id(asset_model_id)

        if filter_type and filter_type not in ['ALL', 'TOP_LEVEL']:
            raise ValidationError("Filter type must be 'ALL' or 'TOP_LEVEL'")

        if next_token and len(next_token) > 4096:
            raise ValidationError('Next token too long')

        client = create_sitewise_client(region)

        params: Dict[str, Any] = {'maxResults': max_results}

        if next_token:
            params['nextToken'] = next_token
        if asset_model_id:
            params['assetModelId'] = asset_model_id
        if filter_type:
            params['filter'] = filter_type

        response = client.list_assets(**params)

        return {
            'success': True,
            'asset_summaries': response['assetSummaries'],
            'next_token': response.get('nextToken', ''),
        }

    except ValidationError as e:
        return {
            'success': False,
            'error': f'Validation error: {str(e)}',
            'error_code': 'ValidationException',
        }
    except ClientError as e:
        return {
            'success': False,
            'error': str(e),
            'error_code': e.response['Error']['Code'],
        }


@tool_metadata(readonly=False)
def update_asset(
    asset_id: str = Field(..., description='The ID of the asset to update'),
    asset_name: str = Field(..., description='A friendly name for the asset'),
    region: str = Field('us-east-1', description='AWS region'),
    client_token: Optional[str] = Field(
        None, description='A unique case-sensitive identifier for the request'
    ),
    asset_description: Optional[str] = Field(None, description='A description for the asset'),
    asset_external_id: Optional[str] = Field(
        None, description='An external ID to assign to the asset'
    ),
) -> Dict[str, Any]:
    """Update an asset's name, description, and external ID.

    Args:
        asset_id: The ID of the asset to update
        asset_name: A friendly name for the asset
        region: AWS region (default: us-east-1)
        client_token: A unique case-sensitive identifier for the request
        asset_description: A description for the asset
        asset_external_id: An external ID to assign to the asset

    Returns:
        Dictionary containing update response
    """
    try:
        # Validate parameters
        if not isinstance(region, FieldInfo):
            validate_region(region)
        if not isinstance(asset_id, FieldInfo):
            validate_asset_id(asset_id)
        if not isinstance(asset_name, FieldInfo):
            validate_asset_name(asset_name)

        client = create_sitewise_client(region)

        params: Dict[str, Any] = {'assetId': asset_id, 'assetName': asset_name}

        if client_token:
            params['clientToken'] = client_token
        if asset_description:
            params['assetDescription'] = asset_description
        if asset_external_id:
            params['assetExternalId'] = asset_external_id

        response = client.update_asset(**params)
        return {'success': True, 'asset_status': response['assetStatus']}

    except ClientError as e:
        return {
            'success': False,
            'error': str(e),
            'error_code': e.response['Error']['Code'],
        }


@tool_metadata(readonly=False)
def delete_asset(
    asset_id: str = Field(..., description='The ID of the asset to delete'),
    region: str = Field('us-east-1', description='AWS region'),
    client_token: Optional[str] = Field(
        None, description='A unique case-sensitive identifier for the request'
    ),
) -> Dict[str, Any]:
    """Delete an asset.

    Args:
        asset_id: The ID of the asset to delete
        region: AWS region (default: us-east-1)
        client_token: A unique case-sensitive identifier for the request

    Returns:
        Dictionary containing deletion response
    """
    try:
        # Validate parameters
        if not isinstance(region, FieldInfo):
            validate_region(region)
        if not isinstance(asset_id, FieldInfo):
            validate_asset_id(asset_id)

        client = create_sitewise_client(region)

        params: Dict[str, Any] = {'assetId': asset_id}
        if client_token:
            params['clientToken'] = client_token

        response = client.delete_asset(**params)
        return {'success': True, 'asset_status': response['assetStatus']}

    except ClientError as e:
        return {
            'success': False,
            'error': str(e),
            'error_code': e.response['Error']['Code'],
        }


@tool_metadata(readonly=False)
def associate_assets(
    asset_id: str = Field(..., description='The ID of the parent asset'),
    hierarchy_id: str = Field(
        ...,
        description='The ID of the hierarchy by which the child asset is associated to the parent',
    ),
    child_asset_id: str = Field(..., description='The ID of the child asset to be associated'),
    region: str = Field('us-east-1', description='AWS region'),
    client_token: Optional[str] = Field(
        None, description='A unique case-sensitive identifier for the request'
    ),
) -> Dict[str, Any]:
    """Associate a child asset with the given parent asset through a hierarchy.

    Args:
        asset_id: The ID of the parent asset
        hierarchy_id: The ID of a hierarchy in the parent asset's model
        child_asset_id: The ID of the child asset to be associated
        region: AWS region (default: us-east-1)
        client_token: A unique case-sensitive identifier for the request

    Returns:
        Dictionary containing association response
    """
    try:
        # Validate parameters
        if not isinstance(region, FieldInfo):
            validate_region(region)
        if not isinstance(asset_id, FieldInfo):
            validate_asset_id(asset_id)
        if not isinstance(child_asset_id, FieldInfo):
            validate_asset_id(child_asset_id)

        client = create_sitewise_client(region)

        params: Dict[str, Any] = {
            'assetId': asset_id,
            'hierarchyId': hierarchy_id,
            'childAssetId': child_asset_id,
        }

        if client_token:
            params['clientToken'] = client_token

        client.associate_assets(**params)
        return {'success': True, 'message': 'Assets associated successfully'}

    except ClientError as e:
        return {
            'success': False,
            'error': str(e),
            'error_code': e.response['Error']['Code'],
        }


@tool_metadata(readonly=False)
def disassociate_assets(
    asset_id: str = Field(..., description='The ID of the parent asset'),
    hierarchy_id: str = Field(
        ..., description="The ID of a hierarchy in the parent asset's model"
    ),
    child_asset_id: str = Field(..., description='The ID of the child asset to be disassociated'),
    region: str = Field('us-east-1', description='AWS region'),
    client_token: Optional[str] = Field(
        None, description='A unique case-sensitive identifier for the request'
    ),
) -> Dict[str, Any]:
    """Disassociate a child asset from the given parent asset through a hierarchy.

    Args:
        asset_id: The ID of the parent asset
        hierarchy_id: The ID of a hierarchy in the parent asset's model
        child_asset_id: The ID of the child asset to be disassociated
        region: AWS region (default: us-east-1)
        client_token: A unique case-sensitive identifier for the request

    Returns:
        Dictionary containing disassociation response
    """
    try:
        # Validate parameters
        if not isinstance(region, FieldInfo):
            validate_region(region)
        if not isinstance(asset_id, FieldInfo):
            validate_asset_id(asset_id)
        if not isinstance(child_asset_id, FieldInfo):
            validate_asset_id(child_asset_id)

        client = create_sitewise_client(region)

        params: Dict[str, Any] = {
            'assetId': asset_id,
            'hierarchyId': hierarchy_id,
            'childAssetId': child_asset_id,
        }

        if client_token:
            params['clientToken'] = client_token

        client.disassociate_assets(**params)
        return {'success': True, 'message': 'Assets disassociated successfully'}

    except ClientError as e:
        return {
            'success': False,
            'error': str(e),
            'error_code': e.response['Error']['Code'],
        }


@tool_metadata(readonly=True)
def list_associated_assets(
    asset_id: str = Field(..., description='The ID of the asset to query'),
    region: str = Field('us-east-1', description='AWS region'),
    hierarchy_id: Optional[str] = Field(
        None, description='The ID of the hierarchy by which child assets are associated'
    ),
    traversal_direction: str = Field(
        'PARENT', description='The direction to list associated assets (PARENT, CHILD)'
    ),
    next_token: Optional[str] = Field(
        None, description='The token to be used for the next set of paginated results'
    ),
    max_results: int = Field(50, description='The maximum number of results to return (1-250)'),
) -> Dict[str, Any]:
    """Retrieve a paginated list of associated assets.

    Args:
        asset_id: The ID of the asset to query
        region: AWS region (default: us-east-1)
        hierarchy_id: The ID of the hierarchy by which child assets are \
            associated
        traversal_direction: The direction to list associated assets (
            PARENT,
            CHILD) \
        next_token: The token to be used for the next set of \
                \
                \
                paginated results
        max_results: The maximum number of results to return (
            1-250,
            default: 50)

    Returns:
        Dictionary containing list of associated assets
    """
    try:
        # Validate parameters
        if not isinstance(region, FieldInfo):
            validate_region(region)
        if not isinstance(asset_id, FieldInfo):
            validate_asset_id(asset_id)
        if not isinstance(max_results, FieldInfo):
            validate_max_results(max_results)

        client = create_sitewise_client(region)

        params: Dict[str, Any] = {
            'assetId': asset_id,
            'traversalDirection': traversal_direction,
            'maxResults': max_results,
        }

        if hierarchy_id:
            params['hierarchyId'] = hierarchy_id
        if next_token:
            params['nextToken'] = next_token

        response = client.list_associated_assets(**params)

        return {
            'success': True,
            'asset_summaries': response['assetSummaries'],
            'next_token': response.get('nextToken', ''),
        }

    except ClientError as e:
        return {
            'success': False,
            'error': str(e),
            'error_code': e.response['Error']['Code'],
        }


# Create MCP tools
create_asset_tool = Tool.from_function(
    fn=create_asset,
    name='create_asset',
    description='Create a new asset in AWS IoT SiteWise from an asset model.',
)

describe_asset_tool = Tool.from_function(
    fn=describe_asset,
    name='describe_asset',
    description='Retrieve detailed information about an AWS IoT SiteWise \
        asset.',
)

list_assets_tool = Tool.from_function(
    fn=list_assets,
    name='list_assets',
    description=('Retrieve a paginated list of asset summaries from AWS IoT SiteWise.'),
)

update_asset_tool = Tool.from_function(
    fn=update_asset,
    name='update_asset',
    description=("Update an asset's name, description, and external ID in AWS IoT SiteWise."),
)

delete_asset_tool = Tool.from_function(
    fn=delete_asset,
    name='delete_asset',
    description='Delete an asset from AWS IoT SiteWise.',
)

associate_assets_tool = Tool.from_function(
    fn=associate_assets,
    name='associate_assets',
    description=(
        'Associate a child asset with a parent asset through a hierarchy in AWS IoT SiteWise.'
    ),
)

disassociate_assets_tool = Tool.from_function(
    fn=disassociate_assets,
    name='disassociate_assets',
    description=(
        'Disassociate a child asset from a parent asset through a hierarchy in AWS IoT SiteWise.'
    ),
)

list_associated_assets_tool = Tool.from_function(
    fn=list_associated_assets,
    name='list_associated_assets',
    description=(
        'Retrieve a paginated list of assets associated with a given asset in AWS IoT SiteWise.'
    ),
)
