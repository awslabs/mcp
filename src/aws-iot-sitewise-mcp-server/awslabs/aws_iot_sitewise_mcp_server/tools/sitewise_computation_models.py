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

"""AWS IoT SiteWise Computation Models Tools."""

import uuid
from awslabs.aws_iot_sitewise_mcp_server.client import create_sitewise_client
from awslabs.aws_iot_sitewise_mcp_server.models.computation_data_models import (
    ComputationModelConfiguration,
    ComputationModelDataBindingValue,
    CreateComputationModelRequest,
    DataBindingValueFilter,
    DeleteComputationModelRequest,
    DescribeComputationModelExecutionSummaryRequest,
    DescribeComputationModelRequest,
    ListComputationModelDataBindingUsagesRequest,
    ListComputationModelResolveToResourcesRequest,
    ListComputationModelsRequest,
    UpdateComputationModelRequest,
)
from awslabs.aws_iot_sitewise_mcp_server.tool_metadata import tool_metadata
from awslabs.aws_iot_sitewise_mcp_server.validation import (
    ValidationError as CustomValidationError,
)
from botocore.exceptions import ClientError
from mcp.server.fastmcp.tools import Tool
from typing import Any, Dict, List, Optional


def _determine_computation_model_configuration_type(
    computation_model_id: str,
    region: str = 'us-east-1',
    configuration_type: Optional[str] = None,
) -> Dict[str, Any]:
    """Internal utility function to determine computation model configuration type with smart optimization.

    This function handles the complete logic for determining computation model configuration type:
    1. If configuration_type is provided by user, uses it directly (performance optimization)
    2. If not provided, calls describe_computation_model API and analyzes data binding

    Args:
        computation_model_id: The ID of the computation model
        region: AWS region
        configuration_type: Optional user-provided configuration type hint

    Returns:
        Dictionary containing:
        - success: bool - Whether the operation was successful
        - is_asset_model_level: bool - True if Asset Model Level, False if Asset Level
        - configuration_type: str - Human-readable configuration type
        - error: str - Error message if unsuccessful
        - error_code: str - Error code if unsuccessful
    """
    try:
        # Smart optimization: If user provided configuration type, use it directly
        if configuration_type is not None:
            if configuration_type.lower() in [
                'asset_model_level',
                'asset model level configuration',
            ]:
                return {
                    'success': True,
                    'is_asset_model_level': True,
                    'configuration_type': 'Asset Model Level Configuration',
                }
            else:
                return {
                    'success': True,
                    'is_asset_model_level': False,
                    'configuration_type': 'Asset Level Configuration',
                }

        # Auto-detection: Call describe_computation_model to get data binding
        describe_result = describe_computation_model(
            computation_model_id=computation_model_id, region=region
        )

        if not describe_result.get('success'):
            return {
                'success': False,
                'error': f'Failed to describe computation model: {describe_result.get("error")}',
                'error_code': describe_result.get('error_code'),
            }

        data_binding = describe_result.get('computationModelDataBinding', {})

        # Analyze data binding to determine configuration type
        # Asset model level uses assetModelProperty bindings, asset level uses assetProperty bindings
        is_asset_model_level = False
        detected_configuration_type = 'Asset Level Configuration'

        for binding_value in data_binding.values():
            if isinstance(binding_value, dict):
                # Check for assetModelProperty in any binding value
                if 'assetModelProperty' in binding_value:
                    is_asset_model_level = True
                    detected_configuration_type = 'Asset Model Level Configuration'
                    break
                # Check for list of bindings
                elif 'list' in binding_value and isinstance(binding_value['list'], list):
                    for item in binding_value['list']:
                        if isinstance(item, dict) and 'assetModelProperty' in item:
                            is_asset_model_level = True
                            detected_configuration_type = 'Asset Model Level Configuration'
                            break
                    if is_asset_model_level:
                        break

        return {
            'success': True,
            'is_asset_model_level': is_asset_model_level,
            'configuration_type': detected_configuration_type,
        }

    except Exception as e:
        return {
            'success': False,
            'error': f'Error determining configuration type: {str(e)}',
            'error_code': 'InternalError',
        }


@tool_metadata(readonly=False)
def create_computation_model(
    computation_model_name: str,
    computation_model_configuration: Dict[str, Any],
    computation_model_data_binding: Dict[str, Any],
    region: str = 'us-east-1',
    computation_model_description: Optional[str] = None,
    client_token: Optional[str] = None,
    tags: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """Create a computation model in AWS IoT SiteWise.

    Computation models enable advanced analytics and custom data processing
    on your asset data in AWS IoT SiteWise.

    You can configure computation models in two ways:

    1. **Asset Model Level Configuration**:
    - Uses `assetModelProperty` in data binding
    - Defines reusable computation logic for all assets of the same model
    - Must later be associated to specific assets using the ExecuteAction API

    2. **Asset Level Configuration**:
    - Uses `assetProperty` in data binding
    - Defines computation logic directly for specific asset instances
    - Ready to execute immediately, without additional binding steps

    Args:
        computation_model_name: The name of the computation model (required)
        computation_model_configuration: The computation model configuration (required)
        computation_model_data_binding: The variable bindings for the model (required)
        region: AWS region (default: us-east-1)
        computation_model_description: Optional description of the computation model
        client_token: Optional unique identifier for idempotent requests
        tags: Optional metadata tags for the computation model

    Returns:
        Dictionary containing the computation model creation response.

    Notes:
        - Use this tool to create any computation model type by specifying the appropriate
        configuration and data bindings.
        - For specific computation types (e.g., anomaly detection), use a specialized tool
        that wraps this generic function for convenience.
    """
    try:
        # Convert raw dictionaries to Pydantic models for validation
        config_model = ComputationModelConfiguration(**computation_model_configuration)

        # Convert data binding dictionary to Pydantic models
        data_binding_models = {}
        for key, value in computation_model_data_binding.items():
            data_binding_models[key] = ComputationModelDataBindingValue(**value)

        # Create and validate the complete request using Pydantic model
        request_model = CreateComputationModelRequest(
            computationModelName=computation_model_name,
            computationModelConfiguration=config_model,
            computationModelDataBinding=data_binding_models,
            computationModelDescription=computation_model_description,
            clientToken=client_token or str(uuid.uuid4()),
            tags=tags,
        )

        # Initialize the SiteWise client using the centralized client creation
        client = create_sitewise_client(region)

        # Convert Pydantic model to dictionary for AWS API call
        request_payload = request_model.model_dump(exclude_none=True)

        # Call the AWS API
        response = client.create_computation_model(**request_payload)

        return {
            'success': True,
            'computationModelId': response['computationModelId'],
            'computationModelArn': response['computationModelArn'],
            'computationModelStatus': response['computationModelStatus'],
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
def create_anomaly_detection_model(
    computation_model_name: str,
    input_properties: List[Dict[str, Any]],
    result_property: Dict[str, Any],
    region: str = 'us-east-1',
    computation_model_description: Optional[str] = None,
    tags: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """Create an anomaly detection computation model in AWS IoT SiteWise.

    Anomaly detection computation models enable you to automatically detect unusual
    patterns in asset property data. You can configure them either at the **asset model level**
    (for reuse across similar assets) or at the **asset level** (for specific assets).

    Property requirements:

    To set up anomaly detection, you must have the following requirements:

        At least one input property that is of either DOUBLE or INTEGER data type. It is either a measurement or transform property, and is used to train the model.

        A result property of STRING data type. It must be a measurement property, and stores the anomaly detection results.

    There are two ways to configure anomaly detection models:

    1. **Asset Model Level Configuration**:
       - Uses AssetModelPropertyBindingValue in data binding
       - Defines computation logic at the asset model level
       - Must be tied to specific assets later via ExecuteAction API
       - Reusable across multiple assets of the same model type
       - Use when you want to define computation logic once and apply to multiple assets

    2. **Asset Level Configuration**:
       - Uses AssetPropertyBindingValue in data binding
       - Defines computation logic for specific asset instances
       - Ready to execute immediately, no additional binding needed
       - Tied directly to specific asset properties
       - Use when you want computation logic for specific assets only

    Args:
        computation_model_name: The name of the computation model (required)
        input_properties: A list of asset or asset model property bindings used as inputs.
                         All IDs (assetModelId, assetId, propertyId) must be UUIDs, not names.
        result_property: The asset or asset model property where the result will be stored.
                        All IDs (assetModelId, assetId, propertyId) must be UUIDs, not names.
        region: AWS region (default: us-east-1)
        computation_model_description: Optional human-readable description
        tags: Optional metadata tags for the computation model

    Returns:
        Dictionary containing computation model creation response

    Example 1 - Asset Model Level Configuration:
        input_properties = [
            {"assetModelProperty": {"assetModelId": "12345678-1234-1234-1234-123456789012", "propertyId": "11111111-1111-1111-1111-111111111111"}},
            {"assetModelProperty": {"assetModelId": "12345678-1234-1234-1234-123456789012", "propertyId": "22222222-2222-2222-2222-222222222222"}}
        ]

        result_property = {
            "assetModelProperty": {"assetModelId": "12345678-1234-1234-1234-123456789012", "propertyId": "33333333-3333-3333-3333-333333333333"}
        }

    Example 2 - Asset Level Configuration:
        input_properties = [
            {"assetProperty": {"assetId": "87654321-4321-4321-4321-210987654321", "propertyId": "11111111-1111-1111-1111-111111111111"}},
            {"assetProperty": {"assetId": "87654321-4321-4321-4321-210987654321", "propertyId": "22222222-2222-2222-2222-222222222222"}}
        ]

        result_property = {
            "assetProperty": {"assetId": "87654321-4321-4321-4321-210987654321", "propertyId": "33333333-3333-3333-3333-333333333333"}
        }

    Decision Guide:
    - Use **Asset Model Level** for reusable logic across many assets of the same model.
    - Use **Asset Level** for computation logic tied to specific asset instances.
    - **Important**: All IDs (assetModelId, assetId, propertyId) must be UUIDs, not names.
      Use list_asset_models and describe_asset_model to get the correct UUIDs.

    Note: inputProperties and resultProperty must be single variable references like "${variablename}".
    For multiple input properties, use a single variable that maps to a "list" structure in the data binding.
    Do NOT use comma-separated variables like "${var1}, ${var2}" - this is invalid.
    """
    computation_model_configuration = {
        'anomalyDetection': {
            'inputProperties': '${input_properties}',
            'resultProperty': '${result_property}',
        }
    }

    computation_model_data_binding = {
        'input_properties': {'list': input_properties},
        'result_property': result_property,
    }

    # Delegate to the generic function
    return create_computation_model(
        computation_model_name=computation_model_name,
        computation_model_configuration=computation_model_configuration,
        computation_model_data_binding=computation_model_data_binding,
        region=region,
        computation_model_description=computation_model_description,
        tags=tags,
    )


@tool_metadata(readonly=False)
def delete_computation_model(
    computation_model_id: str,
    region: str = 'us-east-1',
    client_token: Optional[str] = None,
) -> Dict[str, Any]:
    """Delete a computation model in AWS IoT SiteWise.

    This action permanently deletes a computation model and cannot be undone.

    Args:
        computation_model_id: The ID of the computation model to delete (required, must be in UUID format)
        region: AWS region (default: us-east-1)
        client_token: Optional unique identifier for idempotent requests

    Returns:
        Dictionary containing the computation model deletion response.

    Note:
        - This operation is irreversible
        - Returns HTTP 202 with DELETING status on success
    """
    try:
        # Create and validate the request using Pydantic model
        request_model = DeleteComputationModelRequest(
            computationModelId=computation_model_id,
            clientToken=client_token or str(uuid.uuid4()),
        )

        # Initialize the SiteWise client using the centralized client creation
        client = create_sitewise_client(region)

        # Convert Pydantic model to dictionary for AWS API call
        request_payload = request_model.model_dump(exclude_none=True)

        # Call the AWS API
        response = client.delete_computation_model(**request_payload)

        return {
            'success': True,
            'computationModelStatus': response['computationModelStatus'],
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
def update_computation_model(
    computation_model_id: str,
    computation_model_name: str,
    computation_model_configuration: Dict[str, Any],
    computation_model_data_binding: Dict[str, Any],
    region: str = 'us-east-1',
    computation_model_description: Optional[str] = None,
    client_token: Optional[str] = None,
) -> Dict[str, Any]:
    """Update a computation model in AWS IoT SiteWise.

    Updates the configuration, data binding, name, or description of an existing
    computation model. The computation model must be in ACTIVE state to be updated.

    Args:
        computation_model_id: The ID of the computation model to update (required, must be in UUID format)
        computation_model_name: The new name of the computation model (required)
        computation_model_configuration: The new computation model configuration (required)
        computation_model_data_binding: The new variable bindings for the model (required)
        region: AWS region (default: us-east-1)
        computation_model_description: Optional new description of the computation model
        client_token: Optional unique identifier for idempotent requests

    Returns:
        Dictionary containing the computation model update response.

    Note:
        - The computation model must be in ACTIVE state
        - Returns HTTP 202 with UPDATING status on success
        - All configuration and data binding parameters are required even if unchanged
    """
    try:
        # Convert raw dictionaries to Pydantic models for validation
        config_model = ComputationModelConfiguration(**computation_model_configuration)

        # Convert data binding dictionary to Pydantic models
        data_binding_models = {}
        for key, value in computation_model_data_binding.items():
            data_binding_models[key] = ComputationModelDataBindingValue(**value)

        # Create and validate the complete request using Pydantic model
        request_model = UpdateComputationModelRequest(
            computationModelId=computation_model_id,
            computationModelName=computation_model_name,
            computationModelConfiguration=config_model,
            computationModelDataBinding=data_binding_models,
            computationModelDescription=computation_model_description,
            clientToken=client_token or str(uuid.uuid4()),
        )

        # Initialize the SiteWise client using the centralized client creation
        client = create_sitewise_client(region)

        # Convert Pydantic model to dictionary for AWS API call
        request_payload = request_model.model_dump(exclude_none=True)

        # Call the AWS API
        response = client.update_computation_model(**request_payload)

        return {
            'success': True,
            'computationModelStatus': response['computationModelStatus'],
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
def list_computation_models(
    region: str = 'us-east-1',
    computation_model_type: Optional[str] = None,
    max_results: Optional[int] = None,
    next_token: Optional[str] = None,
) -> Dict[str, Any]:
    """List computation models in AWS IoT SiteWise.

    Retrieves a paginated list of computation models in your AWS account.
    You can filter by computation model type and control pagination.

    Args:
        region: AWS region (default: us-east-1)
        computation_model_type: Optional filter by computation model type (e.g., 'ANOMALY_DETECTION')
        max_results: Optional maximum number of results to return (1-250, default: AWS default)
        next_token: Optional token for pagination to get the next set of results

    Returns:
        Dictionary containing the list of computation models and pagination info.

    Example:
        # List all computation models
        result = list_computation_models()

        # List only anomaly detection models with pagination
        result = list_computation_models(
            computation_model_type='ANOMALY_DETECTION',
            max_results=50
        )

        # Get next page of results
        result = list_computation_models(next_token=previous_result['nextToken'])
    """
    try:
        # Create and validate the request using Pydantic model
        request_model = ListComputationModelsRequest(
            computationModelType=computation_model_type,
            maxResults=max_results,
            nextToken=next_token,
        )

        # Initialize the SiteWise client using the centralized client creation
        client = create_sitewise_client(region)

        # Convert Pydantic model to dictionary for AWS API call
        request_payload = request_model.model_dump(exclude_none=True)

        # Call the AWS API
        response = client.list_computation_models(**request_payload)

        return {
            'success': True,
            'computationModelSummaries': response.get('computationModelSummaries', []),
            'nextToken': response.get('nextToken'),
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
def describe_computation_model(
    computation_model_id: str,
    region: str = 'us-east-1',
    computation_model_version: Optional[str] = None,
) -> Dict[str, Any]:
    """Describe a computation model in AWS IoT SiteWise.

    Retrieves detailed information about a specific computation model, including
    its configuration, data bindings, status, and metadata.

    Args:
        computation_model_id: The ID of the computation model to describe (required, must be in UUID format)
        region: AWS region (default: us-east-1)
        computation_model_version: Optional version of the computation model
                                 (LATEST, ACTIVE, or specific version number)

    Returns:
        Dictionary containing the computation model details.

    Example:
        # Describe the latest version of a computation model
        result = describe_computation_model('12345678-1234-1234-1234-123456789012')

        # Describe a specific version
        result = describe_computation_model(
            computation_model_id='12345678-1234-1234-1234-123456789012',
            computation_model_version='1'
        )

        # Describe the active version
        result = describe_computation_model(
            computation_model_id='12345678-1234-1234-1234-123456789012',
            computation_model_version='ACTIVE'
        )
    """
    try:
        # Create and validate the request using Pydantic model
        request_model = DescribeComputationModelRequest(
            computationModelId=computation_model_id,
            computationModelVersion=computation_model_version,
        )

        # Initialize the SiteWise client using the centralized client creation
        client = create_sitewise_client(region)

        # Convert Pydantic model to dictionary for AWS API call
        request_payload = request_model.model_dump(exclude_none=True)

        # Call the AWS API
        response = client.describe_computation_model(**request_payload)

        return {
            'success': True,
            'computationModelId': response['computationModelId'],
            'computationModelArn': response['computationModelArn'],
            'computationModelName': response['computationModelName'],
            'computationModelDescription': response.get('computationModelDescription'),
            'computationModelConfiguration': response['computationModelConfiguration'],
            'computationModelDataBinding': response['computationModelDataBinding'],
            'computationModelStatus': response['computationModelStatus'],
            'computationModelVersion': response['computationModelVersion'],
            'computationModelCreationDate': response['computationModelCreationDate'],
            'computationModelLastUpdateDate': response['computationModelLastUpdateDate'],
            'actionDefinitions': response.get('actionDefinitions', []),
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
def describe_computation_model_execution_summary(
    computation_model_id: str,
    region: str = 'us-east-1',
    resolve_to_resource_id: Optional[str] = None,
    resolve_to_resource_type: Optional[str] = None,
    configuration_type: Optional[str] = None,
) -> Dict[str, Any]:
    """Describe a computation model execution summary in AWS IoT SiteWise.

    This tool intelligently determines whether to use resolve parameters based on the
    computation model configuration:
    - For Asset Model Level Configuration: Uses resolve parameters if provided to get execution summary for specific assets
    - For Asset Level Configuration: Ignores resolve parameters as they're not needed (already tied to specific assets)

    **Smart Optimization**: If you know the configuration type, provide it via the `configuration_type`
    parameter to avoid an additional API call to describe_computation_model for type detection.

    Args:
        computation_model_id: The ID of the computation model (required, must be in UUID format)
        region: AWS region (default: us-east-1)
        resolve_to_resource_id: Optional ID of the resolved resource (only used for asset model level configurations)
        resolve_to_resource_type: Optional type of the resolved resource (ASSET, only used for asset model level configurations)
        configuration_type: Optional configuration type hint to avoid auto-detection API call.
                          Use 'asset_model_level' or 'asset model level configuration' for Asset Model Level,
                          or 'asset_level' or 'asset level configuration' for Asset Level.
                          If not provided, the function will auto-detect by calling describe_computation_model.

    Returns:
        Dictionary containing the computation model execution summary and configuration type information.

    Example:
        # Auto-detect configuration type (makes additional API call)
        result = describe_computation_model_execution_summary(
            '12345678-1234-1234-1234-123456789012'
        )

        # Optimized: Provide known configuration type to skip auto-detection
        result = describe_computation_model_execution_summary(
            computation_model_id='12345678-1234-1234-1234-123456789012',
            configuration_type='asset_model_level'
        )

        # Asset model level configuration resolved to a specific asset
        result = describe_computation_model_execution_summary(
            computation_model_id='12345678-1234-1234-1234-123456789012',
            resolve_to_resource_id='87654321-4321-4321-4321-210987654321',
            resolve_to_resource_type='ASSET',
            configuration_type='asset_model_level'  # Skip auto-detection for better performance
        )

        # Asset level configuration (resolve parameters will be ignored)
        result = describe_computation_model_execution_summary(
            computation_model_id='12345678-1234-1234-1234-123456789012',
            configuration_type='asset_level'  # Skip auto-detection for better performance
        )

    Performance Tips:
        - Use configuration_type parameter when you know the computation model type to avoid extra API calls
        - For Asset Model Level configurations, consider providing resolve parameters for specific asset context
        - For Asset Level configurations, resolve parameters are automatically ignored (already tied to specific assets)
    """
    try:
        # Use the comprehensive internal utility function to determine configuration type
        config_result = _determine_computation_model_configuration_type(
            computation_model_id=computation_model_id,
            region=region,
            configuration_type=configuration_type,
        )

        if not config_result.get('success'):
            return {
                'success': False,
                'error': config_result.get('error'),
                'error_code': config_result.get('error_code'),
            }

        is_asset_model_level = config_result.get('is_asset_model_level')
        configuration_type = config_result.get('configuration_type')

        # Build the execution summary request based on configuration type
        if is_asset_model_level and (resolve_to_resource_id or resolve_to_resource_type):
            # For asset model level configurations, use resolve parameters if provided
            request_model = DescribeComputationModelExecutionSummaryRequest(
                computationModelId=computation_model_id,
                resolveToResourceId=resolve_to_resource_id,
                resolveToResourceType=resolve_to_resource_type,
            )
        else:
            # For asset level configurations or asset model level without resolve parameters, don't use resolve parameters
            request_model = DescribeComputationModelExecutionSummaryRequest(
                computationModelId=computation_model_id,
            )

        # Initialize the SiteWise client using the centralized client creation
        client = create_sitewise_client(region)

        # Convert Pydantic model to dictionary for AWS API call
        request_payload = request_model.model_dump(exclude_none=True)

        # Call the AWS API
        response = client.describe_computation_model_execution_summary(**request_payload)

        result = {
            'success': True,
            'computationModelId': response['computationModelId'],
            'computationModelExecutionSummary': response['computationModelExecutionSummary'],
            'resolveTo': response.get('resolveTo'),
            'configurationType': configuration_type,
        }

        # Add informational message about parameter usage
        if not is_asset_model_level and (resolve_to_resource_id or resolve_to_resource_type):
            result['info'] = (
                'Resolve parameters ignored for Asset Level Configuration (already tied to specific assets)'
            )
        elif is_asset_model_level and not (resolve_to_resource_id or resolve_to_resource_type):
            result['info'] = (
                'Asset Model Level Configuration - consider providing resolve parameters for specific asset context'
            )

        return result

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
def list_computation_model_data_binding_usages(
    data_binding_value_filter: Dict[str, Any],
    region: str = 'us-east-1',
    max_results: Optional[int] = None,
    next_token: Optional[str] = None,
) -> Dict[str, Any]:
    """Find computation models that use a given resource in data binding.

    This API helps you find computation models which are bound to a given resource:
    - Asset model (fetch all computation models where any of this asset model's properties are bound)
    - Asset (fetch all computation models where any of this asset's properties are bound)
    - Asset model property (fetch all computation models where this property is bound)
    - Asset property (fetch all computation models where this property is bound)

    Args:
        data_binding_value_filter: Filter to specify which resource to search for (required)
        region: AWS region (default: us-east-1)
        max_results: Optional maximum number of results to return (1-250)
        next_token: Optional token for pagination to get the next set of results

    Returns:
        Dictionary containing the list of computation models that use the specified resource.

    Filter Examples:
        # Find computation models using any property from a specific asset
        data_binding_value_filter = {
            "asset": {
                "assetId": "12345678-1234-1234-1234-123456789012"
            }
        }

        # Find computation models using any property from a specific asset model
        data_binding_value_filter = {
            "assetModel": {
                "assetModelId": "12345678-1234-1234-1234-123456789012"
            }
        }

        # Find computation models using a specific asset property
        data_binding_value_filter = {
            "assetProperty": {
                "assetId": "12345678-1234-1234-1234-123456789012",
                "propertyId": "87654321-4321-4321-4321-210987654321"
            }
        }

        # Find computation models using a specific asset model property
        data_binding_value_filter = {
            "assetModelProperty": {
                "assetModelId": "12345678-1234-1234-1234-123456789012",
                "propertyId": "87654321-4321-4321-4321-210987654321"
            }
        }

    Usage Examples:
        # Find all computation models using properties from a specific asset
        result = list_computation_model_data_binding_usages(
            data_binding_value_filter={
                "asset": {"assetId": "12345678-1234-1234-1234-123456789012"}
            }
        )

        # Find computation models using a specific asset property with pagination
        result = list_computation_model_data_binding_usages(
            data_binding_value_filter={
                "assetProperty": {
                    "assetId": "12345678-1234-1234-1234-123456789012",
                    "propertyId": "87654321-4321-4321-4321-210987654321"
                }
            },
            max_results=50
        )

    Use Cases:
        - Check if an asset property is already bound to a computation model before binding it elsewhere
        - Find all computation models that depend on a specific asset or asset model
        - Audit which computation models are using properties from a particular asset
        - Identify dependencies before deleting or modifying assets/properties
    """
    try:
        # Create and validate the data binding value filter
        filter_model = DataBindingValueFilter(**data_binding_value_filter)

        # Create and validate the request using Pydantic model
        request_model = ListComputationModelDataBindingUsagesRequest(
            dataBindingValueFilter=filter_model,
            maxResults=max_results,
            nextToken=next_token,
        )

        # Initialize the SiteWise client using the centralized client creation
        client = create_sitewise_client(region)

        # Convert Pydantic model to dictionary for AWS API call
        request_payload = request_model.model_dump(exclude_none=True)

        # Call the AWS API
        response = client.list_computation_model_data_binding_usages(**request_payload)

        return {
            'success': True,
            'computationModelSummaries': response.get('computationModelSummaries', []),
            'nextToken': response.get('nextToken'),
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
def list_computation_model_resolve_to_resources(
    computation_model_id: str,
    region: str = 'us-east-1',
    max_results: Optional[int] = None,
    next_token: Optional[str] = None,
) -> Dict[str, Any]:
    """List computation model resolve to resources in AWS IoT SiteWise.

    Retrieves a paginated list of resources that a computation model resolves to.
    This shows the specific assets or other resources that are associated with
    the computation model through resolve-to relationships.

    Args:
        computation_model_id: The ID of the computation model (required, must be in UUID format)
        region: AWS region (default: us-east-1)
        max_results: Optional maximum number of results to return (1-250)
        next_token: Optional token for pagination to get the next set of results

    Returns:
        Dictionary containing the list of resolve-to resources and pagination info.

    Example:
        # List all resolve-to resources for a computation model
        result = list_computation_model_resolve_to_resources(
            computation_model_id='12345678-1234-1234-1234-123456789012'
        )

        # List resolve-to resources with pagination
        result = list_computation_model_resolve_to_resources(
            computation_model_id='12345678-1234-1234-1234-123456789012',
            max_results=50
        )

        # Get next page of results
        result = list_computation_model_resolve_to_resources(
            computation_model_id='12345678-1234-1234-1234-123456789012',
            next_token=previous_result['nextToken']
        )

        # The response includes:
        # - success: Boolean indicating if the operation succeeded
        # - computationModelResolveToResourceSummaries: List of resources the computation model resolves to
        # - nextToken: Token for pagination (if more results available)
    """
    try:
        # Create and validate the request using Pydantic model
        request_model = ListComputationModelResolveToResourcesRequest(
            computationModelId=computation_model_id,
            maxResults=max_results,
            nextToken=next_token,
        )

        # Initialize the SiteWise client using the centralized client creation
        client = create_sitewise_client(region)

        # Convert Pydantic model to dictionary for AWS API call
        request_payload = request_model.model_dump(exclude_none=True)

        # Call the AWS API
        response = client.list_computation_model_resolve_to_resources(**request_payload)

        return {
            'success': True,
            'computationModelResolveToResourceSummaries': response.get(
                'computationModelResolveToResourceSummaries', []
            ),
            'nextToken': response.get('nextToken'),
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


# Create MCP tools
create_computation_model_tool = Tool.from_function(
    fn=create_computation_model,
    name='create_computation_model',
    description=(
        'Create a computation model in AWS IoT SiteWise. '
        'Supports any computation model type by specifying configuration and data bindings. '
        'Use specialized tools (e.g., create_anomaly_detection_model) for common computation types.'
    ),
)


create_anomaly_detection_model_tool = Tool.from_function(
    fn=create_anomaly_detection_model,
    name='create_anomaly_detection_model',
    description=(
        'Simplified tool for creating an Anomaly Detection computation model '
        'in AWS IoT SiteWise. Wraps the generic computation model creation with '
        'predefined configuration for anomaly detection logic.'
    ),
)


delete_computation_model_tool = Tool.from_function(
    fn=delete_computation_model,
    name='delete_computation_model',
    description=(
        'Delete a computation model in AWS IoT SiteWise. '
        'This action permanently deletes the computation model and cannot be undone.'
    ),
)


update_computation_model_tool = Tool.from_function(
    fn=update_computation_model,
    name='update_computation_model',
    description=(
        'Update a computation model in AWS IoT SiteWise. '
        'Updates the configuration, data binding, name, or description of an existing '
        'computation model. The computation model must be in ACTIVE state to be updated.'
    ),
)


list_computation_models_tool = Tool.from_function(
    fn=list_computation_models,
    name='list_computation_models',
    description=(
        'List computation models in AWS IoT SiteWise. '
        'Retrieves a paginated list of computation models with optional filtering by type.'
    ),
)


describe_computation_model_tool = Tool.from_function(
    fn=describe_computation_model,
    name='describe_computation_model',
    description=(
        'Describe a computation model in AWS IoT SiteWise. '
        'Retrieves detailed information about a specific computation model including '
        'configuration, data bindings, status, and metadata.'
    ),
)


describe_computation_model_execution_summary_tool = Tool.from_function(
    fn=describe_computation_model_execution_summary,
    name='describe_computation_model_execution_summary',
    description=(
        'Describe a computation model execution summary in AWS IoT SiteWise. '
        'Retrieves information about the execution summary of a computation model, '
        'including execution details and the resource it resolves to.'
    ),
)


list_computation_model_data_binding_usages_tool = Tool.from_function(
    fn=list_computation_model_data_binding_usages,
    name='list_computation_model_data_binding_usages',
    description=(
        'List computation model data binding usages in AWS IoT SiteWise. '
        'Retrieves a paginated list of data binding usages showing how the computation '
        "model's data bindings are being used across assets and asset models."
    ),
)


list_computation_model_resolve_to_resources_tool = Tool.from_function(
    fn=list_computation_model_resolve_to_resources,
    name='list_computation_model_resolve_to_resources',
    description=(
        'List computation model resolve to resources in AWS IoT SiteWise. '
        'Retrieves a paginated list of resources that a computation model resolves to, '
        'showing specific assets or other resources associated through resolve-to relationships.'
    ),
)
