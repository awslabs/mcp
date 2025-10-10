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

"""AWS IoT SiteWise Asset Models Management Tools."""

from awslabs.aws_iot_sitewise_mcp_server.client import create_sitewise_client
from awslabs.aws_iot_sitewise_mcp_server.tool_metadata import tool_metadata
from awslabs.aws_iot_sitewise_mcp_server.validation import (
    ValidationError,
    validate_asset_model_id,
    validate_asset_model_properties,
    validate_max_results,
    validate_region,
    validate_service_quotas,
)
from botocore.exceptions import ClientError
from mcp.server.fastmcp.tools import Tool
from pydantic import Field
from typing import Any, Dict, List, Optional


@tool_metadata(readonly=False)
def create_asset_model(
    asset_model_name: str = Field(..., description='A unique, friendly name for the asset model'),
    region: str = Field('us-east-1', description='AWS region'),
    asset_model_description: Optional[str] = Field(
        None, description='A description for the asset model'
    ),
    asset_model_properties: Optional[List[Dict]] = Field(
        None, description='List of asset model properties'
    ),
    asset_model_hierarchies: Optional[List[Dict]] = Field(
        None, description='List of asset model hierarchies'
    ),
    asset_model_composite_models: Optional[List[Dict]] = Field(
        None, description='List of composite models'
    ),
    client_token: Optional[str] = Field(
        None, description='A unique case-sensitive identifier for the request'
    ),
    tags: Optional[Dict[str, str]] = Field(None, description='Metadata tags for the asset model'),
    asset_model_id: Optional[str] = Field(
        None, description='The ID of the asset model (for update operations)'
    ),
    asset_model_external_id: Optional[str] = Field(
        None, description='An external ID for the asset model'
    ),
    asset_model_type: str = Field(
        'ASSET_MODEL', description='The type of asset model (ASSET_MODEL or COMPONENT_MODEL)'
    ),
) -> Dict[str, Any]:
    """Create an asset model in AWS IoT SiteWise.

    Args:
        asset_model_name: A unique, friendly name for the asset model
        region: AWS region (default: us-east-1)
        asset_model_description: A description for the asset model
        asset_model_properties: The property definitions of the asset model
        asset_model_hierarchies: The hierarchy definitions of the asset model
        asset_model_composite_models: The composite models that are part of \
            this asset model
        client_token: A unique case-sensitive identifier for the request
        tags: A list of key-value pairs that contain metadata for the asset \
            model
        asset_model_id: The ID to assign to the asset model
        asset_model_external_id: An external ID to assign to the asset model
        asset_model_type: The type of asset model (
            ASSET_MODEL,
            COMPONENT_MODEL)

    Returns:
        Dictionary containing asset model creation response
    """
    try:
        # Validate parameters
        validate_region(region)

        if asset_model_id:
            validate_asset_model_id(asset_model_id)

        if asset_model_description and len(asset_model_description) > 2048:
            raise ValidationError('Asset model description cannot exceed 2048 characters')

        if client_token and len(client_token) > 64:
            raise ValidationError('Client token cannot exceed 64 characters')

        if tags and len(tags) > 50:
            raise ValidationError('Cannot have more than 50 tags per asset model')

        if asset_model_properties:
            validate_asset_model_properties(asset_model_properties)

        if asset_model_hierarchies and len(asset_model_hierarchies) > 10:
            raise ValidationError('Cannot have more than 10 hierarchies per asset model')

        if asset_model_composite_models and len(asset_model_composite_models) > 10:
            raise ValidationError('Cannot have more than 10 composite models per asset model')

        # Check service quotas
        validate_service_quotas('create_asset_model')

        client = create_sitewise_client(region)

        params: Dict[str, Any] = {
            'assetModelName': asset_model_name,
            'assetModelType': asset_model_type,
        }

        if asset_model_description:
            params['assetModelDescription'] = asset_model_description
        if asset_model_properties:
            params['assetModelProperties'] = asset_model_properties
        if asset_model_hierarchies:
            params['assetModelHierarchies'] = asset_model_hierarchies
        if asset_model_composite_models:
            params['assetModelCompositeModels'] = asset_model_composite_models
        if client_token:
            params['clientToken'] = client_token
        if tags:
            params['tags'] = tags
        if asset_model_id:
            params['assetModelId'] = asset_model_id
        if asset_model_external_id:
            params['assetModelExternalId'] = asset_model_external_id

        response = client.create_asset_model(**params)
        return {
            'success': True,
            'asset_model_id': response['assetModelId'],
            'asset_model_arn': response['assetModelArn'],
            'asset_model_status': response['assetModelStatus'],
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
def describe_asset_model(
    asset_model_id: str = Field(..., description='The ID of the asset model'),
    region: str = Field('us-east-1', description='AWS region'),
    exclude_properties: bool = Field(
        False, description='Whether to exclude asset model properties'
    ),
    asset_model_version: str = Field(
        'LATEST', description='The version of the asset model (LATEST, ACTIVE)'
    ),
) -> Dict[str, Any]:
    """Retrieve information about an asset model.

    Args:
        asset_model_id: The ID of the asset model
        region: AWS region (default: us-east-1)
        exclude_properties: Whether to exclude asset model properties
        asset_model_version: The version of the asset model (LATEST, ACTIVE)

    Returns:
        Dictionary containing asset model information
    """
    try:
        # Validate parameters
        validate_region(region)
        validate_asset_model_id(asset_model_id)

        if asset_model_version not in ['LATEST', 'ACTIVE']:
            raise ValidationError("Asset model version must be 'LATEST' or 'ACTIVE'")

        client = create_sitewise_client(region)

        params: Dict[str, Any] = {
            'assetModelId': asset_model_id,
            'assetModelVersion': asset_model_version,
        }

        if exclude_properties:
            params['excludeProperties'] = exclude_properties

        response = client.describe_asset_model(**params)

        return {
            'success': True,
            'asset_model_id': response['assetModelId'],
            'asset_model_arn': response['assetModelArn'],
            'asset_model_name': response['assetModelName'],
            'asset_model_description': response.get('assetModelDescription', ''),
            'asset_model_properties': response.get('assetModelProperties', []),
            'asset_model_hierarchies': response.get('assetModelHierarchies', []),
            'asset_model_composite_models': response.get('assetModelCompositeModels', []),
            'asset_model_status': response['assetModelStatus'],
            'asset_model_type': response['assetModelType'],
            'asset_model_creation_date': response['assetModelCreationDate'].isoformat(),
            'asset_model_last_update_date': response['assetModelLastUpdateDate'].isoformat(),
            'asset_model_version': response.get('assetModelVersion', ''),
            'asset_model_version_description': response.get('assetModelVersionDescription', ''),
            'asset_model_external_id': response.get('assetModelExternalId', ''),
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
def list_asset_models(
    region: str = Field('us-east-1', description='AWS region'),
    next_token: Optional[str] = Field(
        None, description='The token to be used for the next set of paginated results'
    ),
    max_results: int = Field(50, description='The maximum number of results to return (1-250)'),
    asset_model_types: Optional[List[str]] = Field(
        None, description='The type of asset model (ASSET_MODEL, COMPONENT_MODEL)'
    ),
) -> Dict[str, Any]:
    """Retrieve a paginated list of summaries for all asset models.

    Args:
        region: AWS region (default: us-east-1)
        next_token: The token to be used for the next set of paginated results
        max_results: The maximum number of results to return (1-250, default: 50)
        asset_model_types: The type of asset model (ASSET_MODEL, COMPONENT_MODEL)

    Returns:
        Dictionary containing list of asset models
    """
    try:
        # Validate parameters
        validate_region(region)
        validate_max_results(max_results, min_val=1, max_val=250)

        if next_token and len(next_token) > 4096:
            raise ValidationError('Next token too long')

        if asset_model_types:
            for asset_type in asset_model_types:
                if asset_type not in ['ASSET_MODEL', 'COMPONENT_MODEL']:
                    raise ValidationError(
                        "Asset model type must be 'ASSET_MODEL' or 'COMPONENT_MODEL'"
                    )

        client = create_sitewise_client(region)

        params: Dict[str, Any] = {'maxResults': max_results}

        if next_token:
            params['nextToken'] = next_token
        if asset_model_types:
            params['assetModelTypes'] = asset_model_types

        response = client.list_asset_models(**params)

        return {
            'success': True,
            'asset_model_summaries': response['assetModelSummaries'],
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
def update_asset_model(
    asset_model_id: str = Field(..., description='The ID of the asset model to update'),
    asset_model_name: str = Field(..., description='A unique, friendly name for the asset model'),
    region: str = Field('us-east-1', description='AWS region'),
    asset_model_description: Optional[str] = Field(
        None, description='A description for the asset model'
    ),
    asset_model_properties: Optional[List[Dict]] = Field(
        None, description='List of asset model properties'
    ),
    asset_model_hierarchies: Optional[List[Dict]] = Field(
        None, description='List of asset model hierarchies'
    ),
    asset_model_composite_models: Optional[List[Dict]] = Field(
        None, description='List of composite models'
    ),
    client_token: Optional[str] = Field(
        None, description='A unique case-sensitive identifier for the request'
    ),
    asset_model_external_id: Optional[str] = Field(
        None, description='An external ID for the asset model'
    ),
) -> Dict[str, Any]:
    """Update an asset model.

    Args:
        asset_model_id: The ID of the asset model to update
        asset_model_name: A unique, friendly name for the asset model
        region: AWS region (default: us-east-1)
        asset_model_description: A description for the asset model
        asset_model_properties: The updated property definitions of the asset \
            model
        asset_model_hierarchies: The updated hierarchy definitions of the \
            asset model
        asset_model_composite_models: The updated composite models
        client_token: A unique case-sensitive identifier for the request
        asset_model_external_id: An external ID to assign to the asset model

    Returns:
        Dictionary containing update response
    """
    try:
        # Validate parameters
        validate_region(region)
        validate_asset_model_id(asset_model_id)

        if asset_model_description and len(asset_model_description) > 2048:
            raise ValidationError('Asset model description cannot exceed 2048 characters')

        if client_token and len(client_token) > 64:
            raise ValidationError('Client token cannot exceed 64 characters')

        if asset_model_properties:
            validate_asset_model_properties(asset_model_properties)

        if asset_model_hierarchies and len(asset_model_hierarchies) > 10:
            raise ValidationError('Cannot have more than 10 hierarchies per asset model')

        if asset_model_composite_models and len(asset_model_composite_models) > 10:
            raise ValidationError('Cannot have more than 10 composite models per asset model')

        client = create_sitewise_client(region)

        params: Dict[str, Any] = {
            'assetModelId': asset_model_id,
            'assetModelName': asset_model_name,
        }

        if asset_model_description:
            params['assetModelDescription'] = asset_model_description
        if asset_model_properties:
            params['assetModelProperties'] = asset_model_properties
        if asset_model_hierarchies:
            params['assetModelHierarchies'] = asset_model_hierarchies
        if asset_model_composite_models:
            params['assetModelCompositeModels'] = asset_model_composite_models
        if client_token:
            params['clientToken'] = client_token
        if asset_model_external_id:
            params['assetModelExternalId'] = asset_model_external_id

        response = client.update_asset_model(**params)
        return {'success': True, 'asset_model_status': response['assetModelStatus']}

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
def delete_asset_model(
    asset_model_id: str = Field(..., description='The ID of the asset model to delete'),
    region: str = Field('us-east-1', description='AWS region'),
    client_token: Optional[str] = Field(
        None, description='A unique case-sensitive identifier for the request'
    ),
) -> Dict[str, Any]:
    """Delete an asset model.

    Args:
        asset_model_id: The ID of the asset model to delete
        region: AWS region (default: us-east-1)
        client_token: A unique case-sensitive identifier for the request

    Returns:
        Dictionary containing deletion response
    """
    try:
        # Validate parameters
        validate_region(region)
        validate_asset_model_id(asset_model_id)

        if client_token and len(client_token) > 64:
            raise ValidationError('Client token cannot exceed 64 characters')

        client = create_sitewise_client(region)

        params: Dict[str, Any] = {'assetModelId': asset_model_id}
        if client_token:
            params['clientToken'] = client_token

        response = client.delete_asset_model(**params)
        return {'success': True, 'asset_model_status': response['assetModelStatus']}

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
def list_asset_model_properties(
    asset_model_id: str = Field(..., description='The ID of the asset model'),
    region: str = Field('us-east-1', description='AWS region'),
    next_token: Optional[str] = Field(
        None, description='The token to be used for the next set of paginated results'
    ),
    max_results: int = Field(50, description='The maximum number of results to return (1-250)'),
    asset_model_version: str = Field(
        'LATEST', description='The version of the asset model (LATEST, ACTIVE)'
    ),
    filter_type: Optional[str] = Field(None, description='Filter properties by type (ALL, BASE)'),
) -> Dict[str, Any]:
    """Retrieve a paginated list of properties associated with an asset model.

    Args:
        asset_model_id: The ID of the asset model
        region: AWS region (default: us-east-1)
        next_token: The token to be used for the next set of paginated results
        max_results: The maximum number of results to return (
            1-250,
            default: 50) \
        asset_model_version: The version of the asset model (
                LATEST,
                ACTIVE)
        filter_type: Filters the requested list of asset model properties (
            ALL,
            BASE)

    Returns:
        Dictionary containing list of asset model properties
    """
    try:
        # Validate parameters
        validate_region(region)
        validate_asset_model_id(asset_model_id)
        validate_max_results(max_results, min_val=1, max_val=250)

        if next_token and len(next_token) > 4096:
            raise ValidationError('Next token too long')

        if asset_model_version not in ['LATEST', 'ACTIVE']:
            raise ValidationError("Asset model version must be 'LATEST' or 'ACTIVE'")

        if filter_type and filter_type not in ['ALL', 'BASE']:
            raise ValidationError("Filter type must be 'ALL' or 'BASE'")

        client = create_sitewise_client(region)

        params: Dict[str, Any] = {
            'assetModelId': asset_model_id,
            'maxResults': max_results,
            'assetModelVersion': asset_model_version,
        }

        if next_token:
            params['nextToken'] = next_token
        if filter_type:
            params['filter'] = filter_type

        response = client.list_asset_model_properties(**params)

        return {
            'success': True,
            'asset_model_property_summaries': response['assetModelPropertySummaries'],
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
def create_asset_model_composite_model(
    asset_model_id: str = Field(
        ..., description='The ID of the asset model this composite model is a part of'
    ),
    asset_model_composite_model_name: str = Field(
        ..., description='A unique, friendly name for the composite model'
    ),
    asset_model_composite_model_type: str = Field(
        ..., description='The type of the composite model'
    ),
    region: str = Field('us-east-1', description='AWS region'),
    asset_model_composite_model_description: Optional[str] = Field(
        None, description='A description for the composite model'
    ),
    asset_model_composite_model_properties: Optional[List[Dict]] = Field(
        None, description='List of composite model properties'
    ),
    client_token: Optional[str] = Field(
        None, description='A unique case-sensitive identifier for the request'
    ),
    asset_model_composite_model_id: Optional[str] = Field(
        None, description='The ID of the composite model'
    ),
    asset_model_composite_model_external_id: Optional[str] = Field(
        None, description='An external ID for the composite model'
    ),
    parent_asset_model_composite_model_id: Optional[str] = Field(
        None, description='The ID of the parent composite model'
    ),
    composed_asset_model_id: Optional[str] = Field(
        None, description='The ID of the composed asset model'
    ),
) -> Dict[str, Any]:
    """Create a composite model for an existing asset model.

    Args:
        asset_model_id: The ID of the asset model this composite model is \
            a part \
            \
            \
            of
        asset_model_composite_model_name: A unique, friendly name for the \
            composite model
        asset_model_composite_model_type: The type of the composite model
        region: AWS region (default: us-east-1)
        asset_model_composite_model_description: The description of the \
            composite model
        asset_model_composite_model_properties: The property definitions of \
            the composite model
        client_token: A unique case-sensitive identifier for the request
        asset_model_composite_model_id: The ID to assign to the composite model
        asset_model_composite_model_external_id: An external ID to assign to \
            the composite model
        parent_asset_model_composite_model_id: The ID of the parent composite \
            model
        composed_asset_model_id: The ID of a component model which is reused \
            to create this composite model

    Returns:
        Dictionary containing composite model creation response
    """
    try:
        # Validate parameters
        validate_region(region)
        validate_asset_model_id(asset_model_id)

        if (
            asset_model_composite_model_description
            and len(asset_model_composite_model_description) > 2048
        ):
            raise ValidationError('Composite model description cannot exceed 2048 characters')

        if client_token and len(client_token) > 64:
            raise ValidationError('Client token cannot exceed 64 characters')

        if asset_model_composite_model_properties:
            if len(asset_model_composite_model_properties) > 200:
                raise ValidationError('Cannot have more than 200 properties per composite model')

        client = create_sitewise_client(region)

        params: Dict[str, Any] = {
            'assetModelId': asset_model_id,
            'assetModelCompositeModelName': asset_model_composite_model_name,
            'assetModelCompositeModelType': asset_model_composite_model_type,
        }

        if asset_model_composite_model_description:
            params['assetModelCompositeModelDescription'] = asset_model_composite_model_description
        if asset_model_composite_model_properties:
            params['assetModelCompositeModelProperties'] = asset_model_composite_model_properties
        if client_token:
            params['clientToken'] = client_token
        if asset_model_composite_model_id:
            params['assetModelCompositeModelId'] = asset_model_composite_model_id
        if asset_model_composite_model_external_id:
            params['assetModelCompositeModelExternalId'] = asset_model_composite_model_external_id
        if parent_asset_model_composite_model_id:
            params['parentAssetModelCompositeModelId'] = parent_asset_model_composite_model_id
        if composed_asset_model_id:
            params['composedAssetModelId'] = composed_asset_model_id

        response = client.create_asset_model_composite_model(**params)
        return {
            'success': True,
            'asset_model_composite_model_id': response['assetModelCompositeModelId'],
            'asset_model_composite_model_path': response['assetModelCompositeModelPath'],
            'asset_model_status': response['assetModelStatus'],
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


# Create MCP tools
create_asset_model_tool = Tool.from_function(
    fn=create_asset_model,
    name='create_asset_model',
    description=(
        'Create an asset model in AWS IoT SiteWise that defines the '
        'structure and properties for assets.'
    ),
)

describe_asset_model_tool = Tool.from_function(
    fn=describe_asset_model,
    name='describe_asset_model',
    description=('Retrieve detailed information about an AWS IoT SiteWise asset model.'),
)

list_asset_models_tool = Tool.from_function(
    fn=list_asset_models,
    name='list_asset_models',
    description=('Retrieve a paginated list of asset model summaries from AWS IoT SiteWise.'),
)

update_asset_model_tool = Tool.from_function(
    fn=update_asset_model,
    name='update_asset_model',
    description=(
        "Update an asset model's properties, hierarchies, and "
        'composite models in AWS IoT SiteWise.'
    ),
)

delete_asset_model_tool = Tool.from_function(
    fn=delete_asset_model,
    name='delete_asset_model',
    description='Delete an asset model from AWS IoT SiteWise.',
)

list_asset_model_properties_tool = Tool.from_function(
    fn=list_asset_model_properties,
    name='list_asset_model_properties',
    description=(
        'Retrieve a paginated list of properties associated with an '
        'asset model in AWS IoT SiteWise.'
    ),
)

create_asset_model_composite_model_tool = Tool.from_function(
    fn=create_asset_model_composite_model,
    name='create_asset_model_composite_model',
    description=('Create a composite model for an existing asset model in AWS IoT SiteWise.'),
)
