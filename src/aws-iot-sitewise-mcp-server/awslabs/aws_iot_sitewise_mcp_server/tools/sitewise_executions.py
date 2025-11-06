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

"""AWS IoT SiteWise Execution Tools."""

import json
import uuid
from awslabs.aws_iot_sitewise_mcp_server.client import create_sitewise_client
from awslabs.aws_iot_sitewise_mcp_server.models.computation_data_models import (
    ActionPayload,
    DescribeActionRequest,
    DescribeExecutionRequest,
    ExecuteActionRequest,
    InferencePayload,
    LabelInputConfiguration,
    ListActionsRequest,
    ListExecutionsRequest,
    ModelEvaluationConfiguration,
    ModelMetricsDestination,
    ResolveTo,
    ResultDestination,
    RetrainingConfiguration,
    TargetResource,
    TrainingPayload,
)
from awslabs.aws_iot_sitewise_mcp_server.tool_metadata import tool_metadata
from awslabs.aws_iot_sitewise_mcp_server.validation import (
    ValidationError as CustomValidationError,
)
from botocore.exceptions import ClientError
from mcp.server.fastmcp.tools import Tool
from typing import Any, Dict, Optional


@tool_metadata(readonly=False)
def execute_action(
    action_definition_id: str,
    action_payload: Dict[str, Any],
    target_resource: Dict[str, Any],
    region: str = 'us-east-1',
    client_token: Optional[str] = None,
    resolve_to: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Execute an action on a target resource in AWS IoT SiteWise.

    This API executes an action on a target resource. Actions are typically used to
    bind computation models to specific assets or to trigger specific operations
    on resources.

    Args:
        action_definition_id: The ID of the action definition (required)
        action_payload: The JSON payload of the action containing stringValue (required)
        target_resource: The resource the action will be taken on (required)
                        Must contain either assetId or computationModelId
        region: AWS region (default: us-east-1)
        client_token: Optional unique identifier for idempotent requests
        resolve_to: Optional detailed resource this action resolves to
                   Must contain assetId if provided

    Returns:
        Dictionary containing the action execution response.

    Example:
        # Execute action on a computation model
        result = execute_action(
            action_definition_id='12345678-1234-1234-1234-123456789012',
            action_payload={'stringValue': '{"key": "value"}'},
            target_resource={'computationModelId': '87654321-4321-4321-4321-210987654321'},
            resolve_to={'assetId': '11111111-1111-1111-1111-111111111111'}
        )

        # Execute action on an asset
        result = execute_action(
            action_definition_id='12345678-1234-1234-1234-123456789012',
            action_payload={'stringValue': '{"operation": "start"}'},
            target_resource={'assetId': '87654321-4321-4321-4321-210987654321'}
        )
    """
    try:
        # Convert raw dictionaries to Pydantic models for validation
        payload_model = ActionPayload(**action_payload)
        target_resource_model = TargetResource(**target_resource)

        resolve_to_model = None
        if resolve_to:
            resolve_to_model = ResolveTo(**resolve_to)

        # Create and validate the complete request using Pydantic model
        request_model = ExecuteActionRequest(
            actionDefinitionId=action_definition_id,
            actionPayload=payload_model,
            targetResource=target_resource_model,
            clientToken=client_token or str(uuid.uuid4()),
            resolveTo=resolve_to_model,
        )

        # Initialize the SiteWise client using the centralized client creation
        client = create_sitewise_client(region)

        # Convert Pydantic model to dictionary for AWS API call
        request_payload = request_model.model_dump(exclude_none=True)

        # Call the AWS API
        response = client.execute_action(**request_payload)

        return {
            'success': True,
            'actionId': response['actionId'],
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
def list_actions(
    target_resource_id: str,
    target_resource_type: str,
    region: str = 'us-east-1',
    max_results: Optional[int] = None,
    next_token: Optional[str] = None,
    resolve_to_resource_id: Optional[str] = None,
    resolve_to_resource_type: Optional[str] = None,
) -> Dict[str, Any]:
    """List actions for a specific target resource in AWS IoT SiteWise.

    Retrieves a paginated list of actions associated with a specific target resource.
    You can filter by resolved resource and control pagination.

    Args:
        target_resource_id: The ID of the target resource (required)
        target_resource_type: The type of resource - ASSET or COMPUTATION_MODEL (required)
        region: AWS region (default: us-east-1)
        max_results: Optional maximum number of results to return (1-250)
        next_token: Optional token for pagination to get the next set of results
        resolve_to_resource_id: Optional ID of the resolved resource
        resolve_to_resource_type: Optional type of the resolved resource (ASSET)

    Returns:
        Dictionary containing the list of actions and pagination info.

    Example:
        # List all actions for a computation model
        result = list_actions(
            target_resource_id='12345678-1234-1234-1234-123456789012',
            target_resource_type='COMPUTATION_MODEL'
        )

        # List actions for an asset with pagination
        result = list_actions(
            target_resource_id='87654321-4321-4321-4321-210987654321',
            target_resource_type='ASSET',
            max_results=50
        )

        # List actions resolved to a specific asset
        result = list_actions(
            target_resource_id='12345678-1234-1234-1234-123456789012',
            target_resource_type='COMPUTATION_MODEL',
            resolve_to_resource_id='11111111-1111-1111-1111-111111111111',
            resolve_to_resource_type='ASSET'
        )

        # Get next page of results
        result = list_actions(
            target_resource_id='12345678-1234-1234-1234-123456789012',
            target_resource_type='COMPUTATION_MODEL',
            next_token=previous_result['nextToken']
        )
    """
    try:
        # Create and validate the request using Pydantic model
        request_model = ListActionsRequest(
            targetResourceId=target_resource_id,
            targetResourceType=target_resource_type,
            maxResults=max_results,
            nextToken=next_token,
            resolveToResourceId=resolve_to_resource_id,
            resolveToResourceType=resolve_to_resource_type,
        )

        # Initialize the SiteWise client using the centralized client creation
        client = create_sitewise_client(region)

        # Convert Pydantic model to dictionary for AWS API call
        request_payload = request_model.model_dump(exclude_none=True)

        # Call the AWS API
        response = client.list_actions(**request_payload)

        return {
            'success': True,
            'actionSummaries': response.get('actionSummaries', []),
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
def describe_action(
    action_id: str,
    region: str = 'us-east-1',
) -> Dict[str, Any]:
    """Describe an action in AWS IoT SiteWise.

    Retrieves detailed information about a specific action, including
    its definition, payload, target resource, execution time, and resolution details.

    Args:
        action_id: The ID of the action to describe (required)
        region: AWS region (default: us-east-1)

    Returns:
        Dictionary containing the action details.

    Example:
        # Describe a specific action
        result = describe_action('12345678-1234-1234-1234-123456789012')

        # The response includes:
        # - actionId: The ID of the action
        # - actionDefinitionId: The ID of the action definition
        # - actionPayload: The JSON payload of the action
        # - targetResource: The resource the action was taken on
        # - resolveTo: The detailed resource this action resolves to (if applicable)
        # - executionTime: The time the action was executed
    """
    try:
        # Create and validate the request using Pydantic model
        request_model = DescribeActionRequest(
            actionId=action_id,
        )

        # Initialize the SiteWise client using the centralized client creation
        client = create_sitewise_client(region)

        # Convert Pydantic model to dictionary for AWS API call
        request_payload = request_model.model_dump(exclude_none=True)

        # Call the AWS API
        response = client.describe_action(**request_payload)

        return {
            'success': True,
            'actionId': response['actionId'],
            'actionDefinitionId': response['actionDefinitionId'],
            'actionPayload': response['actionPayload'],
            'targetResource': response['targetResource'],
            'resolveTo': response.get('resolveTo'),
            'executionTime': response['executionTime'],
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
def execute_training_action(
    training_action_definition_id: str,
    training_mode: str,
    target_resource: Dict[str, Any],
    region: str = 'us-east-1',
    export_data_start_time: Optional[int] = None,
    export_data_end_time: Optional[int] = None,
    target_sampling_rate: Optional[str] = None,
    label_bucket_name: Optional[str] = None,
    label_s3_prefix: Optional[str] = None,
    evaluation_start_time: Optional[int] = None,
    evaluation_end_time: Optional[int] = None,
    evaluation_bucket_name: Optional[str] = None,
    evaluation_s3_prefix: Optional[str] = None,
    metrics_bucket_name: Optional[str] = None,
    metrics_s3_prefix: Optional[str] = None,
    lookback_window: Optional[str] = None,
    retraining_frequency: Optional[str] = None,
    promotion: Optional[str] = None,
    retraining_start_date: Optional[int] = None,
    client_token: Optional[str] = None,
    resolve_to: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Execute a training action for anomaly detection models in AWS IoT SiteWise.

    This specialized function handles training actions on anomaly detection computation models.
    It supports five optional configurations: target sampling rate, labeled data for supervised
    learning, model evaluation for pointwise diagnostics, model metrics for training insights,
    and retraining scheduler configuration for automated retraining.

    Note: Get the training_action_definition_id from describe_computation_model response's
    actionDefinitions array (actionType: "AWS/ANOMALY_DETECTION_TRAINING").

    Args:
        training_action_definition_id: ID of the training action definition (required)
        training_mode: Training mode - TRAIN_MODEL, START_RETRAINING_SCHEDULER, or STOP_RETRAINING_SCHEDULER (required)
        target_resource: Resource containing computationModelId (required, computationModelId must be in UUID format)
        region: AWS region (default: us-east-1)

        # TRAIN_MODEL mode parameters:
        export_data_start_time: Unix epoch timestamp for training data start (REQUIRED for TRAIN_MODEL)
        export_data_end_time: Unix epoch timestamp for training data end (REQUIRED for TRAIN_MODEL)
        target_sampling_rate: Sampling rate (PT1S to PT1H) - higher rates offer detail but increase cost (optional for TRAIN_MODEL)
        label_bucket_name: S3 bucket for labeled training data CSV (optional for TRAIN_MODEL, requires label_s3_prefix)
        label_s3_prefix: S3 prefix for labeled training data CSV (optional for TRAIN_MODEL, requires label_bucket_name)
        evaluation_start_time: Unix epoch timestamp for evaluation data start (optional for TRAIN_MODEL, requires all evaluation params)
        evaluation_end_time: Unix epoch timestamp for evaluation data end (optional for TRAIN_MODEL, requires all evaluation params)
        evaluation_bucket_name: S3 bucket for evaluation results (optional for TRAIN_MODEL, requires all evaluation params)
        evaluation_s3_prefix: S3 prefix for evaluation results (optional for TRAIN_MODEL, requires all evaluation params)
        metrics_bucket_name: S3 bucket for comprehensive training metrics (optional for TRAIN_MODEL, requires metrics_s3_prefix)
        metrics_s3_prefix: S3 prefix for training metrics JSON (optional for TRAIN_MODEL, requires metrics_bucket_name)

        # START_RETRAINING_SCHEDULER mode parameters:
        lookback_window: Historical data window for retraining (P180D, P360D, P540D, P720D) (REQUIRED for START_RETRAINING_SCHEDULER)
        retraining_frequency: How often to retrain (P30D to P1Y) (REQUIRED for START_RETRAINING_SCHEDULER)
        promotion: Model promotion mode (SERVICE_MANAGED, CUSTOMER_MANAGED) (optional for START_RETRAINING_SCHEDULER, defaults to SERVICE_MANAGED)
        retraining_start_date: Unix epoch timestamp for when retraining should start (optional for START_RETRAINING_SCHEDULER)

        # STOP_RETRAINING_SCHEDULER mode parameters:
        # No additional parameters required or accepted for STOP_RETRAINING_SCHEDULER mode

        # Common optional parameters:
        client_token: Optional unique identifier for idempotent requests
        resolve_to: Optional resource containing assetId

    Returns:
        Dictionary containing action execution response with trainingPayload for reference.

    Example:
        # Basic training
        result = execute_training_action(
            training_action_definition_id='12345678-1234-1234-1234-123456789012',
            training_mode='TRAIN_MODEL',
            target_resource={'computationModelId': '87654321-4321-4321-4321-210987654321'},
            export_data_start_time=1717225200,
            export_data_end_time=1722789360
        )

        # Start retraining scheduler
        result = execute_training_action(
            training_action_definition_id='12345678-1234-1234-1234-123456789012',
            training_mode='START_RETRAINING_SCHEDULER',
            target_resource={'computationModelId': '87654321-4321-4321-4321-210987654321'},
            lookback_window='P360D',
            retraining_frequency='P30D',
            promotion='SERVICE_MANAGED',
            retraining_start_date=1730332800
        )

        # Stop retraining scheduler (no additional parameters needed)
        result = execute_training_action(
            training_action_definition_id='12345678-1234-1234-1234-123456789012',
            training_mode='STOP_RETRAINING_SCHEDULER',
            target_resource={'computationModelId': '87654321-4321-4321-4321-210987654321'}
        )

        # Complete training with all configurations
        result = execute_training_action(
            training_action_definition_id='12345678-1234-1234-1234-123456789012',
            training_mode='TRAIN_MODEL',
            target_resource={'computationModelId': '87654321-4321-4321-4321-210987654321'},
            export_data_start_time=1717225200,
            export_data_end_time=1722789360,
            target_sampling_rate='PT5M',
            label_bucket_name='anomaly-detection-data-bucket',
            label_s3_prefix='Labels/model-id/Labels.csv',
            evaluation_start_time=1719817200,
            evaluation_end_time=1720422000,
            evaluation_bucket_name='anomaly-detection-eval-bucket',
            evaluation_s3_prefix='Evaluations/model-id/',
            metrics_bucket_name='anomaly-detection-metrics-bucket',
            metrics_s3_prefix='ModelMetrics/model-id/',
            resolve_to={'assetId': '11111111-1111-1111-1111-111111111111'}
        )
    """
    try:
        # Create label input configuration if both bucket and prefix are provided
        label_input_config = None
        if label_bucket_name is not None and label_s3_prefix is not None:
            label_input_config = LabelInputConfiguration(
                bucketName=label_bucket_name,
                prefix=label_s3_prefix,
            )
        elif label_bucket_name or label_s3_prefix:
            # If only one is provided, raise an error
            raise CustomValidationError(
                'Both label_bucket_name and label_s3_prefix must be provided together for supervised learning'
            )

        # Create model evaluation configuration if all evaluation parameters are provided
        model_evaluation_config = None
        evaluation_params = [
            evaluation_start_time,
            evaluation_end_time,
            evaluation_bucket_name,
            evaluation_s3_prefix,
        ]
        evaluation_params_provided = [param is not None for param in evaluation_params]

        if all(evaluation_params_provided):
            # All evaluation parameters provided - create configuration
            # Validation: we know these are not None because all() passed
            if (
                evaluation_bucket_name is None
                or evaluation_s3_prefix is None
                or evaluation_start_time is None
                or evaluation_end_time is None
            ):
                raise CustomValidationError(
                    'Internal error: evaluation parameters should not be None when all are provided'
                )

            result_destination = ResultDestination(
                bucketName=evaluation_bucket_name,
                prefix=evaluation_s3_prefix,
            )
            model_evaluation_config = ModelEvaluationConfiguration(
                dataStartTime=evaluation_start_time,
                dataEndTime=evaluation_end_time,
                resultDestination=result_destination,
            )
        elif any(evaluation_params_provided):
            # Only some evaluation parameters provided - raise an error
            raise CustomValidationError(
                'All four evaluation parameters (evaluation_start_time, evaluation_end_time, evaluation_bucket_name, evaluation_s3_prefix) must be provided together for pointwise diagnostics'
            )

        # Create model metrics destination if both metrics parameters are provided
        model_metrics_destination = None
        if metrics_bucket_name and metrics_s3_prefix:
            model_metrics_destination = ModelMetricsDestination(
                bucketName=metrics_bucket_name,
                prefix=metrics_s3_prefix,
            )
        elif metrics_bucket_name or metrics_s3_prefix:
            # If only one is provided, raise an error
            raise CustomValidationError(
                'Both metrics_bucket_name and metrics_s3_prefix must be provided together for model metrics'
            )

        # Create retraining configuration for START_RETRAINING_SCHEDULER mode
        retraining_config = None
        if training_mode == 'START_RETRAINING_SCHEDULER':
            # Validation: these are required for START_RETRAINING_SCHEDULER mode
            if lookback_window is None:
                raise CustomValidationError(
                    'lookback_window is required for START_RETRAINING_SCHEDULER mode'
                )
            if retraining_frequency is None:
                raise CustomValidationError(
                    'retraining_frequency is required for START_RETRAINING_SCHEDULER mode'
                )

            retraining_config = RetrainingConfiguration(
                lookbackWindow=lookback_window,
                retrainingFrequency=retraining_frequency,
                promotion=promotion
                or 'SERVICE_MANAGED',  # Default to SERVICE_MANAGED if not provided
                retrainingStartDate=retraining_start_date,
            )

        # Create and validate the training payload
        training_payload = TrainingPayload(
            trainingMode=training_mode,
            exportDataStartTime=export_data_start_time,
            exportDataEndTime=export_data_end_time,
            targetSamplingRate=target_sampling_rate,
            labelInputConfiguration=label_input_config,
            modelEvaluationConfiguration=model_evaluation_config,
            modelMetricsDestination=model_metrics_destination,
            retrainingConfiguration=retraining_config,
        )

        # Convert to JSON string for the action payload
        payload_json = training_payload.model_dump(exclude_none=True)
        action_payload = {'stringValue': json.dumps(payload_json)}

        # Call the execute_action function
        result = execute_action(
            action_definition_id=training_action_definition_id,
            action_payload=action_payload,
            target_resource=target_resource,
            region=region,
            client_token=client_token,
            resolve_to=resolve_to,
        )

        # Add the training payload to the response for reference
        if result.get('success'):
            result['trainingPayload'] = payload_json

        return result

    except CustomValidationError as e:
        return {
            'success': False,
            'error': f'Validation error: {str(e)}',
            'error_code': 'ValidationException',
        }
    except Exception as e:
        return {
            'success': False,
            'error': f'Error creating training payload: {str(e)}',
            'error_code': 'InternalError',
        }


@tool_metadata(readonly=False)
def execute_inference_action(
    inference_action_definition_id: str,
    inference_mode: str,
    target_resource: Dict[str, Any],
    region: str = 'us-east-1',
    data_upload_frequency: Optional[str] = None,
    data_delay_offset_in_minutes: Optional[int] = None,
    target_model_version: Optional[int] = None,
    weekly_operating_window: Optional[Dict[str, Any]] = None,
    inference_time_zone: Optional[str] = None,
    client_token: Optional[str] = None,
    resolve_to: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Execute an inference action for anomaly detection models in AWS IoT SiteWise.

    This is a specialized function for executing inference actions on anomaly detection
    computation models. It handles the specific payload format required for inference
    operations and delegates to the execute_action function.

    Note: Get the inference_action_definition_id from describe_computation_model response's
    actionDefinitions array (actionType: "AWS/ANOMALY_DETECTION_INFERENCE").

    Args:
        inference_action_definition_id: The ID of the inference action definition (required)
        inference_mode: The inference mode - START or STOP (required)
        target_resource: Resource containing computationModelId (required, computationModelId must be in UUID format)
        region: AWS region (default: us-east-1)

        # START mode parameters:
        data_upload_frequency: Data upload frequency (PT5M, PT10M, PT15M, PT30M, PT1H, PT2H, PT3H, PT4H, PT5H, PT6H, PT7H, PT8H, PT9H, PT10H, PT11H, PT12H, PT1D) (REQUIRED for START mode)
        data_delay_offset_in_minutes: Delay offset in minutes (0-60) (optional for START mode only, not allowed for STOP mode)
        target_model_version: Model version to activate (positive integer) (optional for START mode only, not allowed for STOP mode)
        weekly_operating_window: Flexible scheduling window with day-to-time range mappings (optional for START mode)
                                Dict with day names (monday-sunday) as keys and list of time ranges as values
                                Time ranges in 24-hour format "HH:MM-HH:MM" (e.g., {"monday": ["10:00-11:00", "13:00-15:00"]})
        inference_time_zone: IANA timezone identifier for inference scheduling (optional for START mode)
                            Uses Time Zone Database maintained by IANA to align inference with local working hours
                            Examples: "America/Chicago", "Europe/London", "UTC", "GMT+05:30"

        # STOP mode parameters:
        # No additional parameters required or accepted for STOP mode

        # Common optional parameters:
        client_token: Optional unique identifier for idempotent requests
        resolve_to: Optional detailed resource this action resolves to
                   Must contain assetId if provided

    Returns:
        Dictionary containing the action execution response.

    Example:
        # Start inference on a computation model with all optional parameters
        result = execute_inference_action(
            inference_action_definition_id='12345678-1234-1234-1234-123456789012',
            inference_mode='START',
            target_resource={'computationModelId': '87654321-4321-4321-4321-210987654321'},
            data_upload_frequency='PT15M',
            data_delay_offset_in_minutes=30,
            target_model_version=3,
            weekly_operating_window={
                "monday": ["10:00-11:00", "13:00-15:00"],
                "tuesday": ["11:00-13:00"]
            },
            inference_time_zone='America/Chicago',
            resolve_to={'assetId': '11111111-1111-1111-1111-111111111111'}
        )

        # Stop inference
        result = execute_inference_action(
            inference_action_definition_id='12345678-1234-1234-1234-123456789012',
            inference_mode='STOP',
            target_resource={'computationModelId': '87654321-4321-4321-4321-210987654321'}
        )
    """
    try:
        # Create and validate the inference payload
        inference_payload = InferencePayload(
            inferenceMode=inference_mode,
            dataUploadFrequency=data_upload_frequency,
            dataDelayOffsetInMinutes=data_delay_offset_in_minutes,
            targetModelVersion=target_model_version,
            weeklyOperatingWindow=weekly_operating_window,
            inferenceTimeZone=inference_time_zone,
        )

        # Convert to JSON string for the action payload
        payload_json = inference_payload.model_dump(exclude_none=True)
        action_payload = {'stringValue': json.dumps(payload_json)}

        # Call the execute_action function
        result = execute_action(
            action_definition_id=inference_action_definition_id,
            action_payload=action_payload,
            target_resource=target_resource,
            region=region,
            client_token=client_token,
            resolve_to=resolve_to,
        )

        # Add the inference payload to the response for reference
        if result.get('success'):
            result['inferencePayload'] = payload_json

        return result

    except CustomValidationError as e:
        return {
            'success': False,
            'error': f'Validation error: {str(e)}',
            'error_code': 'ValidationException',
        }
    except Exception as e:
        return {
            'success': False,
            'error': f'Error creating inference payload: {str(e)}',
            'error_code': 'InternalError',
        }


@tool_metadata(readonly=True)
def list_executions(
    target_resource_id: str,
    target_resource_type: str,
    region: str = 'us-east-1',
    action_type: Optional[str] = None,
    max_results: Optional[int] = None,
    next_token: Optional[str] = None,
    resolve_to_resource_id: Optional[str] = None,
    resolve_to_resource_type: Optional[str] = None,
) -> Dict[str, Any]:
    """List executions for a specific target resource in AWS IoT SiteWise.

    Retrieves a paginated list of executions that occurred after performing execute actions
    on the specified target resource. This shows the progress status, error information,
    and execution details for training actions, inference schedules, and other action types.

    Args:
        target_resource_id: The ID of the target resource to list executions for (required, must be in UUID format)
        target_resource_type: The type of resource - ASSET or COMPUTATION_MODEL (required)
        region: AWS region (default: us-east-1)
        action_type: Optional type of action executed to filter results
        max_results: Optional maximum number of results to return (1-250)
        next_token: Optional token for pagination to get the next set of results
        resolve_to_resource_id: Optional ID of the resolved resource
        resolve_to_resource_type: Optional type of the resolved resource (ASSET)

    Returns:
        Dictionary containing the list of executions and pagination info.

    Example:
        # List all executions for a computation model
        result = list_executions(
            target_resource_id='12345678-1234-1234-1234-123456789012',
            target_resource_type='COMPUTATION_MODEL'
        )

        # List executions for an asset with pagination
        result = list_executions(
            target_resource_id='87654321-4321-4321-4321-210987654321',
            target_resource_type='ASSET',
            max_results=50
        )

        # List executions filtered by action type
        result = list_executions(
            target_resource_id='12345678-1234-1234-1234-123456789012',
            target_resource_type='COMPUTATION_MODEL',
            action_type='AWS/ANOMALY_DETECTION_TRAINING'
        )

        # List executions resolved to a specific asset
        result = list_executions(
            target_resource_id='12345678-1234-1234-1234-123456789012',
            target_resource_type='COMPUTATION_MODEL',
            resolve_to_resource_id='11111111-1111-1111-1111-111111111111',
            resolve_to_resource_type='ASSET'
        )

        # Get next page of results
        result = list_executions(
            target_resource_id='12345678-1234-1234-1234-123456789012',
            target_resource_type='COMPUTATION_MODEL',
            next_token=previous_result['nextToken']
        )
    """
    try:
        # Create and validate the request using Pydantic model
        request_model = ListExecutionsRequest(
            targetResourceId=target_resource_id,
            targetResourceType=target_resource_type,
            actionType=action_type,
            maxResults=max_results,
            nextToken=next_token,
            resolveToResourceId=resolve_to_resource_id,
            resolveToResourceType=resolve_to_resource_type,
        )

        # Initialize the SiteWise client using the centralized client creation
        client = create_sitewise_client(region)

        # Convert Pydantic model to dictionary for AWS API call
        request_payload = request_model.model_dump(exclude_none=True)

        # Call the AWS API
        response = client.list_executions(**request_payload)

        return {
            'success': True,
            'executionSummaries': response.get('executionSummaries', []),
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
def describe_execution(
    execution_id: str,
    region: str = 'us-east-1',
) -> Dict[str, Any]:
    """Describe an execution in AWS IoT SiteWise.

    Retrieves detailed information about a specific execution, including execution details,
    status, timestamps, target resource information, and execution results. This provides
    comprehensive information about the execution process.

    Args:
        execution_id: The ID of the execution to describe (required)
        region: AWS region (default: us-east-1)

    Returns:
        Dictionary containing the execution details.

    Example:
        # Describe a specific execution
        result = describe_execution('87654321-4321-4321-4321-210987654321')

        # The response includes:
        # - executionId: The ID of the execution
        # - actionType: The type of action executed
        # - executionStatus: Current status with state information
        # - executionStartTime: When the execution started (Unix timestamp)
        # - executionEndTime: When the execution completed (Unix timestamp, if finished)
        # - executionDetails: Detailed information about the execution (key-value pairs)
        # - executionResult: The result of the execution (key-value pairs)
        # - targetResource: The resource the action was taken on
        # - resolveTo: The detailed resource this execution resolves to (if applicable)
        # - executionEntityVersion: Entity version used for the execution
        # - targetResourceVersion: Version of the target resource
    """
    try:
        # Create and validate the request using Pydantic model
        request_model = DescribeExecutionRequest(
            executionId=execution_id,
        )

        # Initialize the SiteWise client using the centralized client creation
        client = create_sitewise_client(region)

        # Convert Pydantic model to dictionary for AWS API call
        request_payload = request_model.model_dump(exclude_none=True)

        # Call the AWS API
        response = client.describe_execution(**request_payload)

        return {
            'success': True,
            'executionId': response['executionId'],
            'actionType': response.get('actionType'),
            'executionStatus': response.get('executionStatus'),
            'executionStartTime': response.get('executionStartTime'),
            'executionEndTime': response.get('executionEndTime'),
            'executionDetails': response.get('executionDetails'),
            'executionResult': response.get('executionResult'),
            'targetResource': response.get('targetResource'),
            'resolveTo': response.get('resolveTo'),
            'executionEntityVersion': response.get('executionEntityVersion'),
            'targetResourceVersion': response.get('targetResourceVersion'),
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
execute_action_tool = Tool.from_function(
    fn=execute_action,
    name='execute_action',
    description=(
        'Execute an action on a target resource in AWS IoT SiteWise. '
        'Actions are typically used to bind computation models to specific assets '
        'or to trigger specific operations on resources.'
    ),
)


list_actions_tool = Tool.from_function(
    fn=list_actions,
    name='list_actions',
    description=(
        'List actions for a specific target resource in AWS IoT SiteWise. '
        'Retrieves a paginated list of actions with optional filtering by resolved resource.'
    ),
)


describe_action_tool = Tool.from_function(
    fn=describe_action,
    name='describe_action',
    description=(
        'Describe an action in AWS IoT SiteWise. '
        'Retrieves detailed information about a specific action including '
        'definition, payload, target resource, execution time, and resolution details.'
    ),
)


execute_training_action_tool = Tool.from_function(
    fn=execute_training_action,
    name='execute_training_action',
    description=(
        'Execute a training action for anomaly detection models in AWS IoT SiteWise. '
        'This specialized function handles training operations (TRAIN_MODEL, START_RETRAINING_SCHEDULER, STOP_RETRAINING_SCHEDULER) '
        'with proper payload formatting for anomaly detection computation models.'
    ),
)


execute_inference_action_tool = Tool.from_function(
    fn=execute_inference_action,
    name='execute_inference_action',
    description=(
        'Execute an inference action for anomaly detection models in AWS IoT SiteWise. '
        'This specialized function handles inference operations (START, STOP) '
        'with proper payload formatting and data upload frequency configuration.'
    ),
)


list_executions_tool = Tool.from_function(
    fn=list_executions,
    name='list_executions',
    description=(
        'List executions for a specific action in AWS IoT SiteWise. '
        'Retrieves a paginated list of executions that occurred after performing an execute action. '
        'Shows progress status, error information, and execution details for all action types.'
    ),
)


describe_execution_tool = Tool.from_function(
    fn=describe_execution,
    name='describe_execution',
    description=(
        'Describe an execution in AWS IoT SiteWise. '
        'Retrieves detailed information about a specific execution including '
        'status, timestamps, execution details, and error information for all execution types.'
    ),
)
