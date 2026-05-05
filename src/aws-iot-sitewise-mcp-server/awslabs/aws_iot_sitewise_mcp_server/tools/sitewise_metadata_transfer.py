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

"""AWS IoT SiteWise Bulk Metadata Transfer Job Tools."""

from awslabs.aws_iot_sitewise_mcp_server.client import create_twinmaker_client
from awslabs.aws_iot_sitewise_mcp_server.models.metadata_transfer_data_models import (
    Asset,
    AssetModel,
    BulkImportSchema,
)
from awslabs.aws_iot_sitewise_mcp_server.tool_metadata import tool_metadata
from awslabs.aws_iot_sitewise_mcp_server.validation import (
    ValidationError as CustomValidationError,
)
from awslabs.aws_iot_sitewise_mcp_server.validation import (
    validate_asset_id,
    validate_asset_model_id,
    validate_region,
    validate_safe_identifier,
    validate_string_for_injection,
)
from botocore.exceptions import ClientError
from mcp.server.fastmcp.tools import Tool
from pydantic import Field, ValidationError
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
#  Tool definition
# ---------------------------------------------------------------------------


@tool_metadata(readonly=True)
def create_bulk_import_schema(
    asset_models: Optional[List[dict]] = None, assets: Optional[List[dict]] = None
) -> Dict[str, Any]:
    """Construct and validate a bulk import schema.

    Args:
        asset_models: List of asset model definitions. Each must include:
            - assetModelName: string
            - assetModelExternalId: string (required for asset references)
            - assetModelProperties: list with name, externalId, dataType, type
            - assetModelHierarchies: list with name, externalId, childAssetModelExternalId
        assets: List of asset definitions. Each must include:
            - assetName: string
            - assetExternalId: string
            - assetModelExternalId: string (must match an asset model)
            - assetProperties: list with externalId (matching model property), alias
            - assetHierarchies: list with externalId (matching model hierarchy), childAssetExternalId

    Returns:
        dict: Validated JSON structure for AWS IoT SiteWise bulk import.
    """
    asset_models = asset_models or []
    assets = assets or []

    try:
        validated_models = []
        for i, am in enumerate(asset_models):
            try:
                validated_models.append(AssetModel(**am))
            except ValidationError as e:
                raise ValueError(f'AssetModel {i} validation failed: {e.errors()}') from e
            except Exception as e:
                raise ValueError(f'AssetModel {i}: {str(e)}') from e

        validated_assets = []
        for i, a in enumerate(assets):
            try:
                validated_assets.append(Asset(**a))
            except ValidationError as e:
                raise ValueError(f'Asset {i} validation failed: {e.errors()}') from e
            except Exception as e:
                raise ValueError(f'Asset {i}: {str(e)}') from e

        schema = BulkImportSchema(assetModels=validated_models, assets=validated_assets)

        return schema.model_dump(exclude_none=True)

    except Exception as e:
        # Return structured error message and working examples
        return {
            'error': str(e),
            'example_asset_model': {
                'assetModelName': 'ExampleModel',
                'assetModelExternalId': 'example-model',
                'assetModelProperties': [
                    {
                        'name': 'Temperature',
                        'externalId': 'temp-prop',
                        'dataType': 'DOUBLE',
                        'type': {
                            'measurement': {
                                'processingConfig': {'forwardingConfig': {'state': 'ENABLED'}}
                            }
                        },
                    }
                ],
                'assetModelHierarchies': [
                    {
                        'name': 'Children',
                        'externalId': 'children-hierarchy',
                        'childAssetModelExternalId': 'child-model',
                    }
                ],
            },
            'example_asset': {
                'assetName': 'ExampleAsset',
                'assetExternalId': 'example-asset',
                'assetModelExternalId': 'example-model',
                'assetProperties': [{'externalId': 'temp-prop', 'alias': '/example/temperature'}],
                'assetHierarchies': [
                    {'externalId': 'children-hierarchy', 'childAssetExternalId': 'child-asset'}
                ],
            },
        }


@tool_metadata(readonly=False)
def create_metadata_transfer_job(
    transfer_direction: str = Field(
        ...,
        description='Direction of transfer: "s3_to_sitewise" (import from S3 to IoT SiteWise) or "sitewise_to_s3" (export from IoT SiteWise to S3)',
    ),
    s3_bucket_name: str = Field(..., description='S3 bucket name.'),
    s3_object_key: Optional[str] = Field(
        None,
        description='S3 object key/path (e.g., "metadata/assets.json"). If not provided, will use default path.',
    ),
    export_all_resources: bool = Field(
        False,
        description='For sitewise_to_s3: Export all IoT SiteWise resources (asset models, assets, etc.) using bulk export filters',
    ),
    asset_model_id: Optional[str] = Field(
        None, description='For sitewise_to_s3: Specific asset model ID to export.'
    ),
    asset_id: Optional[str] = Field(
        None, description='For sitewise_to_s3: Specific asset ID to export.'
    ),
    include_child_assets: bool = Field(
        True,
        description='For asset exports: Include child assets in hierarchy (includeOffspring). Cannot be True when include_asset_model is True.',
    ),
    include_asset_model: bool = Field(
        False,
        description='For asset exports: Include asset model definition (includeAssetModel). Cannot be True when include_child_assets is True.',
    ),
    region: str = Field('us-east-1', description='AWS region'),
    metadata_transfer_job_id: Optional[str] = Field(None, description='Optional custom job ID'),
    description: Optional[str] = Field(None, description='Job description'),
) -> Dict[str, Any]:
    """Create a new metadata transfer job for bulk import/export operations between S3 and IoT SiteWise.

    This tool provides a user-friendly way to set up metadata transfer jobs with support for bulk export
    using IoT SiteWise source configuration filters, avoiding the need for individual API calls.

    Args:
        transfer_direction: Direction of transfer:
            - "s3_to_sitewise": Import metadata from S3 to IoT SiteWise
            - "sitewise_to_s3": Export metadata from IoT SiteWise to S3
        s3_bucket_name: S3 bucket name. If not provided, the agent should list available S3 buckets.
        s3_object_key: S3 object key/path. If not provided, will use sensible defaults.
        export_all_resources: For sitewise_to_s3: Export all IoT SiteWise resources using bulk filters
        asset_model_id: For sitewise_to_s3: Specific asset model ID to export
        asset_id: For sitewise_to_s3: Specific asset ID to export
        include_child_assets: For asset exports: Include child assets in hierarchy (includeOffspring). Cannot be True when include_asset_model is True.
        include_asset_model: For asset exports: Include asset model definition (includeAssetModel). Cannot be True when include_child_assets is True.
        region: AWS region (default: us-east-1)
        metadata_transfer_job_id: Optional custom job ID
        description: Optional job description

    Returns:
        Dictionary containing job creation response or guidance for next steps

    Examples:
        # Import from S3 to IoT SiteWise
        create_metadata_transfer_job(
            transfer_direction="s3_to_sitewise",
            s3_bucket_name="my-sitewise-metadata",
            s3_object_key="bulk-import/assets.json"
        )

        # Export ALL IoT SiteWise resources to S3 (bulk export)
        create_metadata_transfer_job(
            transfer_direction="sitewise_to_s3",
            s3_bucket_name="my-sitewise-exports",
            export_all_resources=True
        )

        # Export specific asset model and asset
        create_metadata_transfer_job(
            transfer_direction="sitewise_to_s3",
            s3_bucket_name="my-sitewise-exports",
            asset_model_id="a1b2c3d4-5678-90ab-cdef-1234567890ab",
            asset_id="f1e2d3c4-b5a6-9078-1234-567890abcdef"
        )
    """
    try:
        validate_region(region)

        # Validate transfer direction
        if transfer_direction not in ['s3_to_sitewise', 'sitewise_to_s3']:
            return {
                'success': False,
                'error': 'Invalid transfer direction. Must be "s3_to_sitewise" or "sitewise_to_s3"',
                'available_directions': {
                    's3_to_sitewise': 'Import metadata from S3 to IoT SiteWise (bulk import)',
                    'sitewise_to_s3': 'Export metadata from IoT SiteWise to S3 (backup/migration)',
                },
            }

        # Validate S3 bucket name for security
        validate_safe_identifier(s3_bucket_name, 'S3 bucket name')

        # Validate S3 object key if provided
        if s3_object_key:
            validate_string_for_injection(s3_object_key, 'S3 object key')

        # Validate asset model ID if provided
        if asset_model_id:
            validate_asset_model_id(asset_model_id)

        # Validate asset ID if provided
        if asset_id:
            validate_asset_id(asset_id)

        # Validate job ID if provided
        if metadata_transfer_job_id:
            validate_safe_identifier(metadata_transfer_job_id, 'Metadata transfer job ID')

        # Validate description if provided
        if description:
            validate_string_for_injection(description, 'Job description')
            if len(description) > 2048:
                raise CustomValidationError('Job description cannot exceed 2048 characters')

        # Validate AWS API constraint: cannot have both include_child_assets and include_asset_model as True
        if include_child_assets and include_asset_model:
            return {
                'success': False,
                'error': 'AWS API constraint: cannot set both include_child_assets and include_asset_model to True. Choose one based on your export needs.',
                'recommendations': {
                    'for_asset_hierarchy_export': 'Set include_child_assets=True, include_asset_model=False',
                    'for_asset_model_export': 'Set include_child_assets=False, include_asset_model=True',
                },
            }

        # Set default object key if not provided
        if not s3_object_key:
            if transfer_direction == 's3_to_sitewise':
                s3_object_key = 'metadata-import/bulk-import-schema.json'
            else:  # sitewise_to_s3
                # For exports, use a folder path (not a specific file)
                # AWS will create the actual file within this folder
                s3_object_key = 'metadata-export/'

        # Build source and destination configurations based on transfer direction
        if transfer_direction == 's3_to_sitewise':
            sources = [
                {
                    'type': 's3',
                    's3Configuration': {
                        'location': f'arn:aws:s3:::{s3_bucket_name}/{s3_object_key}'
                    },
                }
            ]
            destination = {'type': 'iotsitewise'}
        else:  # sitewise_to_s3
            # Build IoT SiteWise source configuration
            iot_sitewise_config = {}

            # Add filters only if specific resources are requested
            # For export_all_resources=True, use empty config to export everything
            if not export_all_resources and (asset_model_id or asset_id):
                filters = []

                if asset_model_id:
                    # Filter for specific asset model
                    filters.append(
                        {
                            'filterByAssetModel': {
                                'assetModelId': asset_model_id,
                                'includeOffspring': True,
                                'includeAssets': True,
                            }
                        }
                    )

                if asset_id:
                    # Filter for specific asset using user-specified parameters
                    filters.append(
                        {
                            'filterByAsset': {
                                'assetId': asset_id,
                                'includeOffspring': include_child_assets,
                                'includeAssetModel': include_asset_model,
                            }
                        }
                    )

                iot_sitewise_config['filters'] = filters

            # For export_all_resources=True, leave iot_sitewise_config empty {}
            # This tells AWS to export all IoT SiteWise resources

            sources = [{'type': 'iotsitewise', 'iotSiteWiseConfiguration': iot_sitewise_config}]

            destination = {
                'type': 's3',
                's3Configuration': {'location': f'arn:aws:s3:::{s3_bucket_name}/{s3_object_key}'},
            }

        # Create the metadata transfer job
        client = create_twinmaker_client(region)

        params: Dict[str, Any] = {
            'sources': sources,
            'destination': destination,
        }

        if metadata_transfer_job_id:
            params['metadataTransferJobId'] = metadata_transfer_job_id
        if description:
            params['description'] = description
        else:
            # Set a default description based on transfer direction
            if transfer_direction == 's3_to_sitewise':
                params['description'] = (
                    f'Import metadata from S3 bucket {s3_bucket_name} to IoT SiteWise'
                )
            else:
                params['description'] = (
                    f'Export metadata from IoT SiteWise to S3 bucket {s3_bucket_name}'
                )

        response = client.create_metadata_transfer_job(**params)

        return {
            'success': True,
            'metadata_transfer_job_id': response['metadataTransferJobId'],
            'arn': response['arn'],
            'creation_date_time': response['creationDateTime'],
            'status': response['status'],
            'transfer_direction': transfer_direction,
            's3_location': f's3://{s3_bucket_name}/{s3_object_key}',
            'next_steps': {
                's3_to_sitewise': 'Upload your bulk import schema JSON file to the S3 location above, then monitor the job status.',
                'sitewise_to_s3': 'The export will begin automatically. Monitor the job status and check the S3 location for results.',
            }.get(transfer_direction),
        }

    except CustomValidationError as e:
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
def cancel_metadata_transfer_job(
    metadata_transfer_job_id: str = Field(
        ..., description='The metadata transfer job ID to cancel'
    ),
    region: str = Field('us-east-1', description='AWS region'),
) -> Dict[str, Any]:
    """Cancel a metadata transfer job.

    Args:
        metadata_transfer_job_id: The ID of the metadata transfer job to cancel
        region: AWS region (default: us-east-1)

    Returns:
        Dictionary containing cancellation response
    """
    try:
        validate_region(region)

        if not metadata_transfer_job_id:
            raise CustomValidationError('Metadata transfer job ID is required')

        client = create_twinmaker_client(region)

        response = client.cancel_metadata_transfer_job(
            metadataTransferJobId=metadata_transfer_job_id
        )

        return {
            'success': True,
            'metadata_transfer_job_id': response['metadataTransferJobId'],
            'arn': response['arn'],
            'update_date_time': response['updateDateTime'],
            'status': response['status'],
            'message': 'Metadata transfer job cancelled successfully',
        }

    except CustomValidationError as e:
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
def get_metadata_transfer_job(
    metadata_transfer_job_id: str = Field(
        ..., description='The metadata transfer job ID to retrieve'
    ),
    region: str = Field('us-east-1', description='AWS region'),
) -> Dict[str, Any]:
    """Get details of a metadata transfer job.

    Args:
        metadata_transfer_job_id: The ID of the metadata transfer job to retrieve
        region: AWS region (default: us-east-1)

    Returns:
        Dictionary containing job details
    """
    try:
        validate_region(region)

        if not metadata_transfer_job_id:
            raise CustomValidationError('Metadata transfer job ID is required')

        client = create_twinmaker_client(region)

        response = client.get_metadata_transfer_job(metadataTransferJobId=metadata_transfer_job_id)

        return {
            'success': True,
            'metadata_transfer_job_id': response['metadataTransferJobId'],
            'arn': response['arn'],
            'description': response.get('description', ''),
            'sources': response['sources'],
            'destination': response['destination'],
            'report_url': response.get('reportUrl', ''),
            'creation_date_time': response['creationDateTime'],
            'update_date_time': response['updateDateTime'],
            'status': response['status'],
            'progress': response.get('progress', {}),
        }

    except CustomValidationError as e:
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
def list_metadata_transfer_jobs(
    source_type: str = Field(
        ..., description='Filter by source type (s3, iotsitewise) - REQUIRED'
    ),
    destination_type: str = Field(
        ..., description='Filter by destination type (s3, iotsitewise) - REQUIRED'
    ),
    region: str = Field('us-east-1', description='AWS region'),
    max_results: int = Field(50, description='Maximum number of results to return (1-200)'),
    next_token: Optional[str] = Field(None, description='Token for pagination'),
) -> Dict[str, Any]:
    """List metadata transfer jobs.

    Args:
        source_type: Filter by source type (s3, iotsitewise) - REQUIRED
        destination_type: Filter by destination type (s3, iotsitewise) - REQUIRED
        region: AWS region (default: us-east-1)
        max_results: Maximum number of results to return (1-200, default: 50)
        next_token: Token for pagination

    Returns:
        Dictionary containing list of metadata transfer jobs
    """
    try:
        validate_region(region)

        if max_results < 1 or max_results > 200:
            raise CustomValidationError('max_results must be between 1 and 200')

        # Validate required parameters
        valid_types = ['s3', 'iotsitewise']
        if source_type not in valid_types:
            raise CustomValidationError(f'source_type must be one of: {", ".join(valid_types)}')
        if destination_type not in valid_types:
            raise CustomValidationError(
                f'destination_type must be one of: {", ".join(valid_types)}'
            )

        client = create_twinmaker_client(region)

        params: Dict[str, Any] = {
            'sourceType': source_type,
            'destinationType': destination_type,
            'maxResults': max_results,
        }

        if next_token:
            params['nextToken'] = next_token

        response = client.list_metadata_transfer_jobs(**params)

        return {
            'success': True,
            'metadata_transfer_job_summaries': response['metadataTransferJobSummaries'],
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


# Create MCP tools
create_bulk_import_schema_tool = Tool.from_function(
    fn=create_bulk_import_schema,
    name='create_bulk_import_schema',
    description='Create a structured JSON schema for AWS IoT SiteWise bulk import operations using dataclasses to ensure correct format.',
)

create_metadata_transfer_job_tool = Tool.from_function(
    fn=create_metadata_transfer_job,
    name='create_metadata_transfer_job',
    description='Create a new metadata transfer job for bulk import operations in AWS IoT SiteWise.',
)

cancel_metadata_transfer_job_tool = Tool.from_function(
    fn=cancel_metadata_transfer_job,
    name='cancel_metadata_transfer_job',
    description='Cancel a running metadata transfer job in AWS IoT SiteWise.',
)

get_metadata_transfer_job_tool = Tool.from_function(
    fn=get_metadata_transfer_job,
    name='get_metadata_transfer_job',
    description='Get detailed information about a metadata transfer job in AWS IoT SiteWise.',
)

list_metadata_transfer_jobs_tool = Tool.from_function(
    fn=list_metadata_transfer_jobs,
    name='list_metadata_transfer_jobs',
    description='List metadata transfer jobs. Requires sourceType and destinationType parameters to filter results.',
)
