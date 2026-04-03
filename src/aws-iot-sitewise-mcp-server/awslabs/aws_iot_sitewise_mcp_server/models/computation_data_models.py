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

import re
from ..validation import (
    validate_computation_model_description,
    validate_computation_model_name,
)
from ..validation_utils import (
    validate_action_type,
    validate_client_token,
    validate_data_upload_frequency,
    validate_enum_value,
    validate_iana_timezone,
    validate_integer_range,
    validate_lookback_window,
    validate_max_results,
    validate_next_token,
    validate_positive_integer,
    validate_positive_timestamp,
    validate_regex_pattern,
    validate_retraining_frequency,
    validate_s3_bucket_name,
    validate_s3_prefix,
    validate_string_length,
    validate_string_value,
    validate_target_sampling_rate,
    validate_uuid_format,
    validate_variable_name,
)
from pydantic import BaseModel, field_validator, model_validator
from typing import Dict, List, Optional


class ComputationModelAnomalyDetectionConfiguration(BaseModel):
    """Configuration for anomaly detection computation model."""

    inputProperties: str
    resultProperty: str

    @field_validator('inputProperties', 'resultProperty')
    def validate_variable_format(cls, v):
        """Validate variable format constraints."""
        return validate_variable_name(v)


class ComputationModelConfiguration(BaseModel):
    """Configuration for computation model."""

    anomalyDetection: Optional[ComputationModelAnomalyDetectionConfiguration] = None

    @model_validator(mode='after')
    def validate_configuration_types(cls, values):
        """Validate that at least one configuration type is defined."""
        defined_types = [v for v in [values.anomalyDetection] if v is not None]
        if len(defined_types) == 0:
            raise ValueError(
                'ComputationModelConfiguration has 0 types defined, must define at least one configuration type'
            )
        return values


class AssetModelPropertyBindingValue(BaseModel):
    """Asset model property binding value."""

    assetModelId: str
    propertyId: str

    @field_validator('assetModelId', 'propertyId')
    def validate_uuid_format(cls, v):
        """Validate UUID format constraints."""
        return validate_uuid_format(v)


class AssetPropertyBindingValue(BaseModel):
    """Asset property binding value."""

    assetId: str
    propertyId: str

    @field_validator('assetId', 'propertyId')
    def validate_uuid_format(cls, v):
        """Validate UUID format constraints."""
        return validate_uuid_format(v)


class ComputationModelDataBindingListItem(BaseModel):
    """Individual item in a computation model data binding list."""

    assetModelProperty: Optional[AssetModelPropertyBindingValue] = None
    assetProperty: Optional[AssetPropertyBindingValue] = None

    @model_validator(mode='after')
    def validate_list_item(cls, values):
        """Validate that exactly one binding type is specified."""
        defined = [v for v in [values.assetModelProperty, values.assetProperty] if v is not None]
        if len(defined) != 1:
            raise ValueError(
                'ComputationModelDataBindingListItem must define exactly one of: '
                'assetModelProperty or assetProperty.'
            )
        return values


class ComputationModelDataBindingValue(BaseModel):
    """Data binding value for computation model."""

    assetModelProperty: Optional[AssetModelPropertyBindingValue] = None
    assetProperty: Optional[AssetPropertyBindingValue] = None
    list: Optional[List[ComputationModelDataBindingListItem]] = None

    @model_validator(mode='after')
    def validate_binding_value(cls, values):
        """Validate that exactly one binding type is specified."""
        defined = [
            v
            for v in [values.assetModelProperty, values.assetProperty, values.list]
            if v is not None
        ]
        if len(defined) != 1:
            raise ValueError(
                'ComputationModelDataBindingValue must define exactly one of: '
                'assetModelProperty, assetProperty, or list.'
            )
        return values


class CreateComputationModelRequest(BaseModel):
    """Request model for creating a computation model."""

    computationModelName: str
    computationModelConfiguration: ComputationModelConfiguration
    computationModelDataBinding: Dict[str, ComputationModelDataBindingValue]
    computationModelDescription: Optional[str] = None
    clientToken: Optional[str] = None
    tags: Optional[Dict[str, str]] = None

    @field_validator('computationModelName')
    def validate_name(cls, v):
        """Validate computation model name constraints."""
        try:
            validate_computation_model_name(v)
        except Exception as e:
            raise ValueError(str(e))
        return v

    @field_validator('computationModelDescription')
    def validate_description(cls, v):
        """Validate computation model description constraints."""
        if v:
            try:
                validate_computation_model_description(v)
            except Exception as e:
                raise ValueError(str(e))
        return v

    @field_validator('clientToken')
    def validate_client_token(cls, v):
        """Validate client token constraints."""
        return validate_client_token(v)

    @field_validator('computationModelDataBinding')
    def validate_data_binding_keys(cls, v):
        """Validate data binding key constraints."""
        for key in v.keys():
            validate_string_length(key, 1, 64, f'Data binding key "{key}"')
            validate_regex_pattern(
                key,
                re.compile(r'^[a-z][a-z0-9_]*$'),
                f'Data binding key "{key}"',
                '^[a-z][a-z0-9_]*$',
            )
        return v


class DeleteComputationModelRequest(BaseModel):
    """Request model for deleting a computation model."""

    computationModelId: str
    clientToken: Optional[str] = None

    @field_validator('computationModelId')
    def validate_computation_model_id(cls, v):
        """Validate computation model ID format constraints."""
        return validate_uuid_format(v, 'computationModelId')

    @field_validator('clientToken')
    def validate_client_token(cls, v):
        """Validate client token constraints."""
        return validate_client_token(v)


class UpdateComputationModelRequest(BaseModel):
    """Request model for updating a computation model."""

    computationModelId: str
    computationModelName: str
    computationModelConfiguration: ComputationModelConfiguration
    computationModelDataBinding: Dict[str, ComputationModelDataBindingValue]
    computationModelDescription: Optional[str] = None
    clientToken: Optional[str] = None

    @field_validator('computationModelId')
    def validate_computation_model_id(cls, v):
        """Validate computation model ID format constraints."""
        return validate_uuid_format(v, 'computationModelId')

    @field_validator('computationModelName')
    def validate_name(cls, v):
        """Validate computation model name constraints."""
        try:
            validate_computation_model_name(v)
        except Exception as e:
            raise ValueError(str(e))
        return v

    @field_validator('computationModelDescription')
    def validate_description(cls, v):
        """Validate computation model description constraints."""
        if v:
            try:
                validate_computation_model_description(v)
            except Exception as e:
                raise ValueError(str(e))
        return v

    @field_validator('clientToken')
    def validate_client_token(cls, v):
        """Validate client token constraints."""
        return validate_client_token(v)

    @field_validator('computationModelDataBinding')
    def validate_data_binding_keys(cls, v):
        """Validate data binding key constraints."""
        for key in v.keys():
            validate_string_length(key, 1, 64, f'Data binding key "{key}"')
            validate_regex_pattern(
                key,
                re.compile(r'^[a-z][a-z0-9_]*$'),
                f'Data binding key "{key}"',
                '^[a-z][a-z0-9_]*$',
            )
        return v


class DescribeComputationModelRequest(BaseModel):
    """Request model for describing a computation model."""

    computationModelId: str
    computationModelVersion: Optional[str] = None

    @field_validator('computationModelId')
    def validate_computation_model_id(cls, v):
        """Validate computation model ID format constraints."""
        return validate_uuid_format(v, 'computationModelId')

    @field_validator('computationModelVersion')
    def validate_computation_model_version(cls, v):
        """Validate computation model version constraints."""
        if v:
            valid_versions = ['LATEST', 'ACTIVE']
            # Check if it's a numeric version (1-9999999999)
            if v not in valid_versions and not (v.isdigit() and 1 <= int(v) <= 9999999999):
                raise ValueError(
                    'computationModelVersion must be LATEST, ACTIVE, or a positive integer between 1 and 9999999999'
                )
        return v


class DescribeComputationModelExecutionSummaryRequest(BaseModel):
    """Request model for describing a computation model execution summary."""

    computationModelId: str
    resolveToResourceId: Optional[str] = None
    resolveToResourceType: Optional[str] = None

    @field_validator('computationModelId')
    def validate_computation_model_id(cls, v):
        """Validate computation model ID format constraints."""
        return validate_uuid_format(v, 'computationModelId')

    @field_validator('resolveToResourceId')
    def validate_resolve_to_resource_id(cls, v):
        """Validate resolve to resource ID format constraints."""
        if v:
            return validate_uuid_format(v, 'resolveToResourceId')
        return v

    @field_validator('resolveToResourceType')
    def validate_resolve_to_resource_type(cls, v):
        """Validate resolve to resource type constraints."""
        if v:
            return validate_enum_value(v, ['ASSET'], 'resolveToResourceType')
        return v


class ListComputationModelsRequest(BaseModel):
    """Request model for listing computation models."""

    computationModelType: Optional[str] = None
    maxResults: Optional[int] = None
    nextToken: Optional[str] = None

    @field_validator('computationModelType')
    def validate_computation_model_type(cls, v):
        """Validate computation model type constraints."""
        if v:
            return validate_enum_value(v, ['ANOMALY_DETECTION'], 'computationModelType')
        return v

    @field_validator('maxResults')
    def validate_max_results(cls, v):
        """Validate max results constraints."""
        if v is not None:
            return validate_max_results(v)
        return v

    @field_validator('nextToken')
    def validate_next_token(cls, v):
        """Validate next token constraints."""
        if v is not None:
            return validate_next_token(v)
        return v


class ActionPayload(BaseModel):
    """Action payload for execution requests."""

    stringValue: str

    @field_validator('stringValue')
    def validate_string_value(cls, v):
        """Validate string value constraints."""
        return validate_string_value(v)


class LabelInputConfiguration(BaseModel):
    """Label input configuration for supervised learning."""

    bucketName: str
    prefix: str

    @field_validator('bucketName')
    def validate_bucket_name(cls, v):
        """Validate S3 bucket name constraints."""
        return validate_s3_bucket_name(v)

    @field_validator('prefix')
    def validate_prefix(cls, v):
        """Validate S3 object prefix constraints."""
        return validate_s3_prefix(v)


class ResultDestination(BaseModel):
    """Result destination configuration for model evaluation."""

    bucketName: str
    prefix: str

    @field_validator('bucketName')
    def validate_bucket_name(cls, v):
        """Validate S3 bucket name constraints."""
        return validate_s3_bucket_name(v)

    @field_validator('prefix')
    def validate_prefix(cls, v):
        """Validate S3 object prefix constraints."""
        return validate_s3_prefix(v)


class ModelEvaluationConfiguration(BaseModel):
    """Model evaluation configuration for pointwise diagnostics."""

    dataStartTime: int
    dataEndTime: int
    resultDestination: ResultDestination

    @field_validator('dataStartTime', 'dataEndTime')
    def validate_timestamps(cls, v):
        """Validate timestamp constraints."""
        return validate_positive_timestamp(v)

    @model_validator(mode='after')
    def validate_evaluation_time_range(cls, values):
        """Validate that evaluation end time is after start time."""
        start_time = values.dataStartTime
        end_time = values.dataEndTime

        if end_time <= start_time:
            raise ValueError('dataEndTime must be greater than dataStartTime.')

        return values


class ModelMetricsDestination(BaseModel):
    """Model metrics destination configuration for training metrics."""

    bucketName: str
    prefix: str

    @field_validator('bucketName')
    def validate_bucket_name(cls, v):
        """Validate S3 bucket name constraints."""
        return validate_s3_bucket_name(v)

    @field_validator('prefix')
    def validate_prefix(cls, v):
        """Validate S3 object prefix constraints."""
        return validate_s3_prefix(v)


class RetrainingConfiguration(BaseModel):
    """Retraining configuration for START_RETRAINING_SCHEDULER mode."""

    lookbackWindow: str
    retrainingFrequency: str
    promotion: Optional[str] = 'SERVICE_MANAGED'
    retrainingStartDate: Optional[int] = None

    @field_validator('lookbackWindow')
    def validate_lookback_window(cls, v):
        """Validate lookback window constraints."""
        return validate_lookback_window(v)

    @field_validator('retrainingFrequency')
    def validate_retraining_frequency(cls, v):
        """Validate retraining frequency constraints."""
        return validate_retraining_frequency(v)

    @field_validator('promotion')
    def validate_promotion(cls, v):
        """Validate promotion mode constraints."""
        if v is not None:
            return validate_enum_value(v, ['SERVICE_MANAGED', 'CUSTOMER_MANAGED'], 'promotion')
        return v

    @field_validator('retrainingStartDate')
    def validate_retraining_start_date(cls, v):
        """Validate retraining start date constraints."""
        if v is not None:
            return validate_positive_timestamp(v, 'retrainingStartDate')
        return v


class TrainingPayload(BaseModel):
    """Training payload for anomaly detection models."""

    trainingMode: str
    exportDataStartTime: Optional[int] = None
    exportDataEndTime: Optional[int] = None
    targetSamplingRate: Optional[str] = None
    labelInputConfiguration: Optional[LabelInputConfiguration] = None
    modelEvaluationConfiguration: Optional[ModelEvaluationConfiguration] = None
    modelMetricsDestination: Optional[ModelMetricsDestination] = None
    retrainingConfiguration: Optional[RetrainingConfiguration] = None

    @field_validator('trainingMode')
    def validate_training_mode(cls, v):
        """Validate training mode constraints."""
        return validate_enum_value(
            v,
            ['TRAIN_MODEL', 'START_RETRAINING_SCHEDULER', 'STOP_RETRAINING_SCHEDULER'],
            'trainingMode',
        )

    @field_validator('exportDataStartTime', 'exportDataEndTime')
    def validate_timestamps(cls, v):
        """Validate timestamp constraints."""
        if v is not None:
            return validate_positive_timestamp(v)
        return v

    @field_validator('targetSamplingRate')
    def validate_target_sampling_rate(cls, v):
        """Validate target sampling rate constraints."""
        if v is not None:
            return validate_target_sampling_rate(v)
        return v

    @model_validator(mode='after')
    def validate_time_range(cls, values):
        """Validate that end time is after start time."""
        start_time = values.exportDataStartTime
        end_time = values.exportDataEndTime

        if start_time is not None and end_time is not None:
            if end_time <= start_time:
                raise ValueError('exportDataEndTime must be greater than exportDataStartTime.')

        return values

    @model_validator(mode='after')
    def validate_training_mode_constraints(cls, values):
        """Validate training mode-specific parameter constraints."""
        training_mode = values.trainingMode

        # For TRAIN_MODEL, export_data_start_time and export_data_end_time are required
        if training_mode == 'TRAIN_MODEL':
            if values.exportDataStartTime is None or values.exportDataEndTime is None:
                raise ValueError(
                    'exportDataStartTime and exportDataEndTime are required for TRAIN_MODEL mode'
                )

        # For START_RETRAINING_SCHEDULER, retraining configuration is required
        elif training_mode == 'START_RETRAINING_SCHEDULER':
            if values.retrainingConfiguration is None:
                raise ValueError(
                    'retrainingConfiguration is required for START_RETRAINING_SCHEDULER mode'
                )

        # For STOP_RETRAINING_SCHEDULER, no additional parameters should be provided
        elif training_mode == 'STOP_RETRAINING_SCHEDULER':
            additional_params = [
                values.exportDataStartTime,
                values.exportDataEndTime,
                values.targetSamplingRate,
                values.labelInputConfiguration,
                values.modelEvaluationConfiguration,
                values.modelMetricsDestination,
                values.retrainingConfiguration,
            ]
            if any(param is not None for param in additional_params):
                raise ValueError(
                    'STOP_RETRAINING_SCHEDULER mode does not accept any additional parameters'
                )

        return values


class InferencePayload(BaseModel):
    """Inference payload for anomaly detection models."""

    inferenceMode: str
    dataUploadFrequency: Optional[str] = None
    dataDelayOffsetInMinutes: Optional[int] = None
    targetModelVersion: Optional[int] = None
    weeklyOperatingWindow: Optional[Dict[str, List[str]]] = None
    inferenceTimeZone: Optional[str] = None

    @field_validator('inferenceMode')
    def validate_inference_mode(cls, v):
        """Validate inference mode constraints."""
        return validate_enum_value(v, ['START', 'STOP'], 'inferenceMode')

    @field_validator('dataUploadFrequency')
    def validate_data_upload_frequency(cls, v):
        """Validate data upload frequency constraints."""
        if v is not None:
            return validate_data_upload_frequency(v)
        return v

    @field_validator('dataDelayOffsetInMinutes')
    def validate_data_delay_offset(cls, v):
        """Validate data delay offset constraints."""
        if v is not None:
            return validate_integer_range(v, 0, 60, 'dataDelayOffsetInMinutes')
        return v

    @field_validator('targetModelVersion')
    def validate_target_model_version(cls, v):
        """Validate target model version constraints."""
        if v is not None:
            return validate_positive_integer(v, 'targetModelVersion')
        return v

    @field_validator('weeklyOperatingWindow')
    def validate_weekly_operating_window(cls, v):
        """Validate weekly operating window constraints."""
        if v is not None:
            valid_days = [
                'monday',
                'tuesday',
                'wednesday',
                'thursday',
                'friday',
                'saturday',
                'sunday',
            ]
            time_range_pattern = re.compile(
                r'^([01]?[0-9]|2[0-3]):[0-5][0-9]-([01]?[0-9]|2[0-3]):[0-5][0-9]$'
            )

            for day, time_ranges in v.items():
                # Validate day names
                if day not in valid_days:
                    raise ValueError(
                        f'Invalid day "{day}". Must be one of: {", ".join(valid_days)}'
                    )

                # Validate time ranges
                if not isinstance(time_ranges, list) or len(time_ranges) == 0:
                    raise ValueError(f'Time ranges for "{day}" must be a non-empty list')

                for time_range in time_ranges:
                    if not isinstance(time_range, str):
                        raise ValueError(f'Time range "{time_range}" for "{day}" must be a string')

                    if not time_range_pattern.match(time_range):
                        raise ValueError(
                            f'Time range "{time_range}" for "{day}" must be in 24-hour format "HH:MM-HH:MM"'
                        )

                    # Validate that start time is before end time
                    start_time, end_time = time_range.split('-')
                    start_hour, start_min = map(int, start_time.split(':'))
                    end_hour, end_min = map(int, end_time.split(':'))

                    start_minutes = start_hour * 60 + start_min
                    end_minutes = end_hour * 60 + end_min

                    if start_minutes >= end_minutes:
                        raise ValueError(
                            f'Start time must be before end time in range "{time_range}" for "{day}"'
                        )

        return v

    @field_validator('inferenceTimeZone')
    def validate_inference_time_zone(cls, v):
        """Validate IANA timezone identifier constraints."""
        if v is not None:
            return validate_iana_timezone(v, 'inferenceTimeZone')
        return v

    @model_validator(mode='after')
    def validate_inference_mode_constraints(cls, values):
        """Validate inference mode-specific parameter constraints."""
        inference_mode = values.inferenceMode

        # For START mode, dataUploadFrequency is required
        if inference_mode == 'START':
            if values.dataUploadFrequency is None:
                raise ValueError('dataUploadFrequency is required for START inference mode')

        # For STOP mode, START-only parameters should not be provided
        elif inference_mode == 'STOP':
            start_only_params = [values.dataDelayOffsetInMinutes, values.targetModelVersion]
            if any(param is not None for param in start_only_params):
                raise ValueError(
                    'dataDelayOffsetInMinutes and targetModelVersion can only be used with START inference mode'
                )

        return values


class ResolveTo(BaseModel):
    """Resolve to resource for action execution."""

    assetId: str

    @field_validator('assetId')
    def validate_asset_id(cls, v):
        """Validate asset ID format constraints."""
        return validate_uuid_format(v, 'assetId')


class TargetResource(BaseModel):
    """Target resource for action execution."""

    assetId: Optional[str] = None
    computationModelId: Optional[str] = None

    @field_validator('assetId')
    def validate_asset_id(cls, v):
        """Validate asset ID format constraints."""
        if v:
            return validate_uuid_format(v, 'assetId')
        return v

    @field_validator('computationModelId')
    def validate_computation_model_id(cls, v):
        """Validate computation model ID format constraints."""
        if v:
            return validate_uuid_format(v, 'computationModelId')
        return v

    @model_validator(mode='after')
    def validate_target_resource(cls, values):
        """Validate that exactly one target resource type is specified."""
        defined = [v for v in [values.assetId, values.computationModelId] if v is not None]
        if len(defined) != 1:
            raise ValueError(
                'TargetResource must define exactly one of: assetId or computationModelId.'
            )
        return values


class ExecuteActionRequest(BaseModel):
    """Request model for executing an action."""

    actionDefinitionId: str
    actionPayload: ActionPayload
    targetResource: TargetResource
    clientToken: Optional[str] = None
    resolveTo: Optional[ResolveTo] = None

    @field_validator('actionDefinitionId')
    def validate_action_definition_id(cls, v):
        """Validate action definition ID format constraints."""
        return validate_uuid_format(v, 'actionDefinitionId')

    @field_validator('clientToken')
    def validate_client_token(cls, v):
        """Validate client token constraints."""
        return validate_client_token(v)


class ListActionsRequest(BaseModel):
    """Request model for listing actions."""

    targetResourceId: str
    targetResourceType: str
    maxResults: Optional[int] = None
    nextToken: Optional[str] = None
    resolveToResourceId: Optional[str] = None
    resolveToResourceType: Optional[str] = None

    @field_validator('targetResourceId')
    def validate_target_resource_id(cls, v):
        """Validate target resource ID format constraints."""
        return validate_uuid_format(v, 'targetResourceId')

    @field_validator('targetResourceType')
    def validate_target_resource_type(cls, v):
        """Validate target resource type constraints."""
        return validate_enum_value(v, ['ASSET', 'COMPUTATION_MODEL'], 'targetResourceType')

    @field_validator('maxResults')
    def validate_max_results(cls, v):
        """Validate max results constraints."""
        if v is not None:
            return validate_max_results(v)
        return v

    @field_validator('nextToken')
    def validate_next_token(cls, v):
        """Validate next token constraints."""
        if v is not None:
            return validate_next_token(v)
        return v

    @field_validator('resolveToResourceId')
    def validate_resolve_to_resource_id(cls, v):
        """Validate resolve to resource ID format constraints."""
        if v:
            return validate_uuid_format(v, 'resolveToResourceId')
        return v

    @field_validator('resolveToResourceType')
    def validate_resolve_to_resource_type(cls, v):
        """Validate resolve to resource type constraints."""
        if v:
            return validate_enum_value(v, ['ASSET'], 'resolveToResourceType')
        return v


class DescribeActionRequest(BaseModel):
    """Request model for describing an action."""

    actionId: str

    @field_validator('actionId')
    def validate_action_id(cls, v):
        """Validate action ID format constraints."""
        return validate_uuid_format(v, 'actionId')


class ListExecutionsRequest(BaseModel):
    """Request model for listing executions."""

    targetResourceId: str
    targetResourceType: str
    actionType: Optional[str] = None
    maxResults: Optional[int] = None
    nextToken: Optional[str] = None
    resolveToResourceId: Optional[str] = None
    resolveToResourceType: Optional[str] = None

    @field_validator('targetResourceId')
    def validate_target_resource_id(cls, v):
        """Validate target resource ID format constraints."""
        return validate_uuid_format(v, 'targetResourceId')

    @field_validator('targetResourceType')
    def validate_target_resource_type(cls, v):
        """Validate target resource type constraints."""
        return validate_enum_value(v, ['ASSET', 'COMPUTATION_MODEL'], 'targetResourceType')

    @field_validator('actionType')
    def validate_action_type(cls, v):
        """Validate action type format constraints."""
        if v:
            return validate_action_type(v)
        return v

    @field_validator('maxResults')
    def validate_max_results(cls, v):
        """Validate max results constraints."""
        if v is not None:
            return validate_max_results(v)
        return v

    @field_validator('nextToken')
    def validate_next_token(cls, v):
        """Validate next token constraints."""
        if v is not None:
            return validate_next_token(v)
        return v

    @field_validator('resolveToResourceId')
    def validate_resolve_to_resource_id(cls, v):
        """Validate resolve to resource ID format constraints."""
        if v:
            return validate_uuid_format(v, 'resolveToResourceId')
        return v

    @field_validator('resolveToResourceType')
    def validate_resolve_to_resource_type(cls, v):
        """Validate resolve to resource type constraints."""
        if v:
            return validate_enum_value(v, ['ASSET'], 'resolveToResourceType')
        return v


class DescribeExecutionRequest(BaseModel):
    """Request model for describing an execution."""

    executionId: str

    @field_validator('executionId')
    def validate_execution_id(cls, v):
        """Validate execution ID format constraints."""
        return validate_uuid_format(v, 'executionId')


class DataBindingValueFilter(BaseModel):
    """Data binding value filter for finding computation models that use a given resource."""

    asset: Optional[Dict[str, str]] = None
    assetModel: Optional[Dict[str, str]] = None
    assetProperty: Optional[Dict[str, str]] = None
    assetModelProperty: Optional[Dict[str, str]] = None

    @field_validator('asset')
    def validate_asset(cls, v):
        """Validate asset filter constraints."""
        if v:
            if 'assetId' not in v:
                raise ValueError('asset filter must contain assetId')
            validate_uuid_format(v['assetId'], 'assetId')
        return v

    @field_validator('assetModel')
    def validate_asset_model(cls, v):
        """Validate asset model filter constraints."""
        if v:
            if 'assetModelId' not in v:
                raise ValueError('assetModel filter must contain assetModelId')
            validate_uuid_format(v['assetModelId'], 'assetModelId')
        return v

    @field_validator('assetProperty')
    def validate_asset_property(cls, v):
        """Validate asset property filter constraints."""
        if v:
            if 'assetId' not in v or 'propertyId' not in v:
                raise ValueError('assetProperty filter must contain both assetId and propertyId')
            validate_uuid_format(v['assetId'], 'assetId')
            validate_uuid_format(v['propertyId'], 'propertyId')
        return v

    @field_validator('assetModelProperty')
    def validate_asset_model_property(cls, v):
        """Validate asset model property filter constraints."""
        if v:
            if 'assetModelId' not in v or 'propertyId' not in v:
                raise ValueError(
                    'assetModelProperty filter must contain both assetModelId and propertyId'
                )
            validate_uuid_format(v['assetModelId'], 'assetModelId')
            validate_uuid_format(v['propertyId'], 'propertyId')
        return v

    @model_validator(mode='after')
    def validate_filter(cls, values):
        """Validate that exactly one filter type is specified."""
        defined = [
            v
            for v in [
                values.asset,
                values.assetModel,
                values.assetProperty,
                values.assetModelProperty,
            ]
            if v is not None
        ]
        if len(defined) != 1:
            raise ValueError(
                'DataBindingValueFilter must define exactly one of: '
                'asset, assetModel, assetProperty, or assetModelProperty.'
            )
        return values


class ListComputationModelDataBindingUsagesRequest(BaseModel):
    """Request model for listing computation model data binding usages."""

    dataBindingValueFilter: DataBindingValueFilter
    maxResults: Optional[int] = None
    nextToken: Optional[str] = None

    @field_validator('maxResults')
    def validate_max_results(cls, v):
        """Validate max results constraints."""
        if v is not None:
            return validate_max_results(v)
        return v

    @field_validator('nextToken')
    def validate_next_token(cls, v):
        """Validate next token constraints."""
        if v is not None:
            return validate_next_token(v)
        return v


class ListComputationModelResolveToResourcesRequest(BaseModel):
    """Request model for listing computation model resolve to resources."""

    computationModelId: str
    maxResults: Optional[int] = None
    nextToken: Optional[str] = None

    @field_validator('computationModelId')
    def validate_computation_model_id(cls, v):
        """Validate computation model ID format constraints."""
        return validate_uuid_format(v, 'computationModelId')

    @field_validator('maxResults')
    def validate_max_results(cls, v):
        """Validate max results constraints."""
        if v is not None:
            return validate_max_results(v)
        return v

    @field_validator('nextToken')
    def validate_next_token(cls, v):
        """Validate next token constraints."""
        if v is not None:
            return validate_next_token(v)
        return v
