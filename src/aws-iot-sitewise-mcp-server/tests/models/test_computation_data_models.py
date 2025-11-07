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

"""Tests for AWS IoT SiteWise Computation Data Models."""

import pytest
from awslabs.aws_iot_sitewise_mcp_server.models.computation_data_models import (
    ActionPayload,
    AssetModelPropertyBindingValue,
    AssetPropertyBindingValue,
    ComputationModelAnomalyDetectionConfiguration,
    ComputationModelConfiguration,
    ComputationModelDataBindingListItem,
    ComputationModelDataBindingValue,
    CreateComputationModelRequest,
    DataBindingValueFilter,
    DeleteComputationModelRequest,
    DescribeActionRequest,
    DescribeComputationModelExecutionSummaryRequest,
    DescribeComputationModelRequest,
    DescribeExecutionRequest,
    ExecuteActionRequest,
    InferencePayload,
    LabelInputConfiguration,
    ListActionsRequest,
    ListComputationModelDataBindingUsagesRequest,
    ListComputationModelResolveToResourcesRequest,
    ListComputationModelsRequest,
    ListExecutionsRequest,
    ModelEvaluationConfiguration,
    ModelMetricsDestination,
    ResolveTo,
    ResultDestination,
    RetrainingConfiguration,
    TargetResource,
    TrainingPayload,
    UpdateComputationModelRequest,
)
from pydantic import ValidationError


class TestBasicModels:
    """Test cases for basic model validation."""

    def test_action_payload_validation(self):
        """Test ActionPayload model validation."""
        # Valid action payload
        payload = ActionPayload(stringValue='test-value')
        assert payload.stringValue == 'test-value'

        # Invalid empty string value
        with pytest.raises(ValidationError):
            ActionPayload(stringValue='')

        # Invalid long string value
        with pytest.raises(ValidationError):
            ActionPayload(stringValue='A' * 1025)

    def test_asset_model_property_binding_value_validation(self):
        """Test AssetModelPropertyBindingValue model validation."""
        # Valid binding value
        binding = AssetModelPropertyBindingValue(
            assetModelId='12345678-1234-1234-1234-123456789012',
            propertyId='87654321-4321-4321-4321-210987654321',
        )
        assert binding.assetModelId == '12345678-1234-1234-1234-123456789012'
        assert binding.propertyId == '87654321-4321-4321-4321-210987654321'

        # Invalid asset model ID
        with pytest.raises(ValidationError):
            AssetModelPropertyBindingValue(
                assetModelId='invalid-uuid', propertyId='87654321-4321-4321-4321-210987654321'
            )

        # Invalid property ID
        with pytest.raises(ValidationError):
            AssetModelPropertyBindingValue(
                assetModelId='12345678-1234-1234-1234-123456789012', propertyId='invalid-uuid'
            )

    def test_asset_property_binding_value_validation(self):
        """Test AssetPropertyBindingValue model validation."""
        # Valid binding value
        binding = AssetPropertyBindingValue(
            assetId='12345678-1234-1234-1234-123456789012',
            propertyId='87654321-4321-4321-4321-210987654321',
        )
        assert binding.assetId == '12345678-1234-1234-1234-123456789012'
        assert binding.propertyId == '87654321-4321-4321-4321-210987654321'

        # Invalid asset ID
        with pytest.raises(ValidationError):
            AssetPropertyBindingValue(
                assetId='invalid-uuid', propertyId='87654321-4321-4321-4321-210987654321'
            )

        # Invalid property ID
        with pytest.raises(ValidationError):
            AssetPropertyBindingValue(
                assetId='12345678-1234-1234-1234-123456789012', propertyId='invalid-uuid'
            )

    def test_resolve_to_validation(self):
        """Test ResolveTo model validation."""
        # Valid resolve to
        resolve_to = ResolveTo(assetId='12345678-1234-1234-1234-123456789012')
        assert resolve_to.assetId == '12345678-1234-1234-1234-123456789012'

        # Invalid asset ID
        with pytest.raises(ValidationError):
            ResolveTo(assetId='invalid-uuid')


class TestComputationModelConfiguration:
    """Test cases for computation model configuration models."""

    def test_anomaly_detection_configuration_validation(self):
        """Test ComputationModelAnomalyDetectionConfiguration validation."""
        # Valid configuration
        config = ComputationModelAnomalyDetectionConfiguration(
            inputProperties='${input_data}', resultProperty='${anomaly_result}'
        )
        assert config.inputProperties == '${input_data}'
        assert config.resultProperty == '${anomaly_result}'

        # Invalid input properties format
        with pytest.raises(ValidationError):
            ComputationModelAnomalyDetectionConfiguration(
                inputProperties='invalid_format', resultProperty='${anomaly_result}'
            )

        # Invalid result property format
        with pytest.raises(ValidationError):
            ComputationModelAnomalyDetectionConfiguration(
                inputProperties='${input_data}', resultProperty='invalid_format'
            )

    def test_computation_model_configuration_validation(self):
        """Test ComputationModelConfiguration validation."""
        # Valid configuration with anomaly detection
        anomaly_config = ComputationModelAnomalyDetectionConfiguration(
            inputProperties='${input_data}', resultProperty='${anomaly_result}'
        )
        config = ComputationModelConfiguration(anomalyDetection=anomaly_config)
        assert config.anomalyDetection is not None

        # Invalid configuration without any configuration type - should raise ValidationError
        with pytest.raises(ValidationError) as exc_info:
            ComputationModelConfiguration()
        assert 'ComputationModelConfiguration has 0 types defined' in str(exc_info.value)


class TestDataBindingModels:
    """Test cases for data binding models."""

    def test_computation_model_data_binding_list_item_validation(self):
        """Test ComputationModelDataBindingListItem validation."""
        # Valid with asset model property
        asset_model_binding = AssetModelPropertyBindingValue(
            assetModelId='12345678-1234-1234-1234-123456789012',
            propertyId='87654321-4321-4321-4321-210987654321',
        )
        list_item = ComputationModelDataBindingListItem(assetModelProperty=asset_model_binding)
        assert list_item.assetModelProperty is not None
        assert list_item.assetProperty is None

        # Valid with asset property
        asset_binding = AssetPropertyBindingValue(
            assetId='12345678-1234-1234-1234-123456789012',
            propertyId='87654321-4321-4321-4321-210987654321',
        )
        list_item2 = ComputationModelDataBindingListItem(assetProperty=asset_binding)
        assert list_item2.assetProperty is not None
        assert list_item2.assetModelProperty is None

        # Invalid - no binding specified
        with pytest.raises(ValidationError):
            ComputationModelDataBindingListItem()

        # Invalid - both bindings specified
        with pytest.raises(ValidationError):
            ComputationModelDataBindingListItem(
                assetModelProperty=asset_model_binding, assetProperty=asset_binding
            )

    def test_computation_model_data_binding_value_validation(self):
        """Test ComputationModelDataBindingValue validation."""
        # Valid with asset model property
        asset_model_binding = AssetModelPropertyBindingValue(
            assetModelId='12345678-1234-1234-1234-123456789012',
            propertyId='87654321-4321-4321-4321-210987654321',
        )
        binding_value = ComputationModelDataBindingValue(assetModelProperty=asset_model_binding)
        assert binding_value.assetModelProperty is not None

        # Valid with asset property
        asset_binding = AssetPropertyBindingValue(
            assetId='12345678-1234-1234-1234-123456789012',
            propertyId='87654321-4321-4321-4321-210987654321',
        )
        binding_value2 = ComputationModelDataBindingValue(assetProperty=asset_binding)
        assert binding_value2.assetProperty is not None

        # Valid with list
        list_item = ComputationModelDataBindingListItem(assetModelProperty=asset_model_binding)
        binding_value3 = ComputationModelDataBindingValue(list=[list_item])
        assert binding_value3.list is not None

        # Invalid - no binding specified
        with pytest.raises(ValidationError):
            ComputationModelDataBindingValue()

        # Invalid - multiple bindings specified
        with pytest.raises(ValidationError):
            ComputationModelDataBindingValue(
                assetModelProperty=asset_model_binding, assetProperty=asset_binding
            )


class TestTargetResource:
    """Test cases for TargetResource model."""

    def test_target_resource_validation(self):
        """Test TargetResource validation."""
        # Valid with asset ID
        target = TargetResource(assetId='12345678-1234-1234-1234-123456789012')
        assert target.assetId == '12345678-1234-1234-1234-123456789012'
        assert target.computationModelId is None

        # Valid with computation model ID
        target2 = TargetResource(computationModelId='87654321-4321-4321-4321-210987654321')
        assert target2.computationModelId == '87654321-4321-4321-4321-210987654321'
        assert target2.assetId is None

        # Invalid - no target specified
        with pytest.raises(ValidationError):
            TargetResource()

        # Invalid - both targets specified
        with pytest.raises(ValidationError):
            TargetResource(
                assetId='12345678-1234-1234-1234-123456789012',
                computationModelId='87654321-4321-4321-4321-210987654321',
            )

        # Invalid asset ID format
        with pytest.raises(ValidationError):
            TargetResource(assetId='invalid-uuid')

        # Invalid computation model ID format
        with pytest.raises(ValidationError):
            TargetResource(computationModelId='invalid-uuid')


class TestS3ConfigurationModels:
    """Test cases for S3 configuration models."""

    def test_label_input_configuration_validation(self):
        """Test LabelInputConfiguration validation."""
        # Valid configuration
        config = LabelInputConfiguration(bucketName='my-bucket', prefix='labels/data')
        assert config.bucketName == 'my-bucket'
        assert config.prefix == 'labels/data'

        # Invalid bucket name
        with pytest.raises(ValidationError):
            LabelInputConfiguration(bucketName='Invalid_Bucket_Name', prefix='labels/data')

        # Invalid prefix - empty
        with pytest.raises(ValidationError):
            LabelInputConfiguration(bucketName='my-bucket', prefix='')

    def test_result_destination_validation(self):
        """Test ResultDestination validation."""
        # Valid destination
        dest = ResultDestination(bucketName='results-bucket', prefix='evaluation/results')
        assert dest.bucketName == 'results-bucket'
        assert dest.prefix == 'evaluation/results'

        # Invalid bucket name - too short
        with pytest.raises(ValidationError):
            ResultDestination(bucketName='ab', prefix='evaluation/results')

    def test_model_metrics_destination_validation(self):
        """Test ModelMetricsDestination validation."""
        # Valid destination
        dest = ModelMetricsDestination(bucketName='metrics-bucket', prefix='training/metrics')
        assert dest.bucketName == 'metrics-bucket'
        assert dest.prefix == 'training/metrics'


class TestModelEvaluationConfiguration:
    """Test cases for ModelEvaluationConfiguration model."""

    def test_model_evaluation_configuration_validation(self):
        """Test ModelEvaluationConfiguration validation."""
        # Valid configuration
        result_dest = ResultDestination(bucketName='results-bucket', prefix='evaluation/results')
        config = ModelEvaluationConfiguration(
            dataStartTime=1640995200,  # 2022-01-01 00:00:00 UTC
            dataEndTime=1641081600,  # 2022-01-02 00:00:00 UTC
            resultDestination=result_dest,
        )
        assert config.dataStartTime == 1640995200
        assert config.dataEndTime == 1641081600

        # Invalid - end time before start time
        with pytest.raises(ValidationError):
            ModelEvaluationConfiguration(
                dataStartTime=1641081600,  # 2022-01-02 00:00:00 UTC
                dataEndTime=1640995200,  # 2022-01-01 00:00:00 UTC
                resultDestination=result_dest,
            )

        # Invalid - end time equal to start time
        with pytest.raises(ValidationError):
            ModelEvaluationConfiguration(
                dataStartTime=1640995200, dataEndTime=1640995200, resultDestination=result_dest
            )

        # Invalid timestamp - negative
        with pytest.raises(ValidationError):
            ModelEvaluationConfiguration(
                dataStartTime=-1, dataEndTime=1641081600, resultDestination=result_dest
            )


class TestRetrainingConfiguration:
    """Test cases for RetrainingConfiguration model."""

    def test_retraining_configuration_validation(self):
        """Test RetrainingConfiguration validation."""
        # Valid configuration
        config = RetrainingConfiguration(lookbackWindow='P180D', retrainingFrequency='P30D')
        assert config.lookbackWindow == 'P180D'
        assert config.retrainingFrequency == 'P30D'
        assert config.promotion == 'SERVICE_MANAGED'

        # Valid with custom promotion
        config2 = RetrainingConfiguration(
            lookbackWindow='P360D', retrainingFrequency='P60D', promotion='CUSTOMER_MANAGED'
        )
        assert config2.promotion == 'CUSTOMER_MANAGED'

        # Valid with retraining start date
        config3 = RetrainingConfiguration(
            lookbackWindow='P180D', retrainingFrequency='P30D', retrainingStartDate=1640995200
        )
        assert config3.retrainingStartDate == 1640995200

        # Invalid lookback window
        with pytest.raises(ValidationError):
            RetrainingConfiguration(
                lookbackWindow='P100D',  # Not in valid list
                retrainingFrequency='P30D',
            )

        # Invalid retraining frequency - too short
        with pytest.raises(ValidationError):
            RetrainingConfiguration(
                lookbackWindow='P180D',
                retrainingFrequency='P10D',  # Less than 30 days
            )

        # Invalid promotion mode
        with pytest.raises(ValidationError):
            RetrainingConfiguration(
                lookbackWindow='P180D', retrainingFrequency='P30D', promotion='INVALID_MODE'
            )

        # Invalid retraining start date - negative
        with pytest.raises(ValidationError):
            RetrainingConfiguration(
                lookbackWindow='P180D', retrainingFrequency='P30D', retrainingStartDate=-1
            )


class TestTrainingPayload:
    """Test cases for TrainingPayload model."""

    def test_training_payload_train_model_validation(self):
        """Test TrainingPayload validation for TRAIN_MODEL mode."""
        # Valid TRAIN_MODEL payload
        payload = TrainingPayload(
            trainingMode='TRAIN_MODEL',
            exportDataStartTime=1640995200,
            exportDataEndTime=1641081600,
        )
        assert payload.trainingMode == 'TRAIN_MODEL'

        # Invalid TRAIN_MODEL - missing required timestamps
        with pytest.raises(ValidationError):
            TrainingPayload(trainingMode='TRAIN_MODEL')

        # Invalid TRAIN_MODEL - missing start time
        with pytest.raises(ValidationError):
            TrainingPayload(trainingMode='TRAIN_MODEL', exportDataEndTime=1641081600)

        # Invalid TRAIN_MODEL - end time before start time
        with pytest.raises(ValidationError):
            TrainingPayload(
                trainingMode='TRAIN_MODEL',
                exportDataStartTime=1641081600,
                exportDataEndTime=1640995200,
            )

    def test_training_payload_retraining_scheduler_validation(self):
        """Test TrainingPayload validation for START_RETRAINING_SCHEDULER mode."""
        # Valid START_RETRAINING_SCHEDULER payload
        retraining_config = RetrainingConfiguration(
            lookbackWindow='P180D', retrainingFrequency='P30D'
        )
        payload = TrainingPayload(
            trainingMode='START_RETRAINING_SCHEDULER', retrainingConfiguration=retraining_config
        )
        assert payload.trainingMode == 'START_RETRAINING_SCHEDULER'

        # Invalid START_RETRAINING_SCHEDULER - missing retraining configuration
        with pytest.raises(ValidationError):
            TrainingPayload(trainingMode='START_RETRAINING_SCHEDULER')

    def test_training_payload_stop_retraining_scheduler_validation(self):
        """Test TrainingPayload validation for STOP_RETRAINING_SCHEDULER mode."""
        # Valid STOP_RETRAINING_SCHEDULER payload
        payload = TrainingPayload(trainingMode='STOP_RETRAINING_SCHEDULER')
        assert payload.trainingMode == 'STOP_RETRAINING_SCHEDULER'

        # Invalid STOP_RETRAINING_SCHEDULER - with additional parameters
        with pytest.raises(ValidationError):
            TrainingPayload(
                trainingMode='STOP_RETRAINING_SCHEDULER', exportDataStartTime=1640995200
            )

        # Invalid STOP_RETRAINING_SCHEDULER - with retraining configuration
        retraining_config = RetrainingConfiguration(
            lookbackWindow='P180D', retrainingFrequency='P30D'
        )
        with pytest.raises(ValidationError):
            TrainingPayload(
                trainingMode='STOP_RETRAINING_SCHEDULER', retrainingConfiguration=retraining_config
            )

    def test_training_payload_optional_fields_validation(self):
        """Test TrainingPayload optional fields validation."""
        # Valid with target sampling rate
        payload = TrainingPayload(
            trainingMode='TRAIN_MODEL',
            exportDataStartTime=1640995200,
            exportDataEndTime=1641081600,
            targetSamplingRate='PT1M',
        )
        assert payload.targetSamplingRate == 'PT1M'

        # Invalid target sampling rate
        with pytest.raises(ValidationError):
            TrainingPayload(
                trainingMode='TRAIN_MODEL',
                exportDataStartTime=1640995200,
                exportDataEndTime=1641081600,
                targetSamplingRate='INVALID_RATE',
            )

    def test_training_mode_validation(self):
        """Test training mode validation."""
        # Invalid training mode
        with pytest.raises(ValidationError):
            TrainingPayload(trainingMode='INVALID_MODE')


class TestInferencePayload:
    """Test cases for InferencePayload model."""

    def test_inference_payload_start_validation(self):
        """Test InferencePayload validation for START mode."""
        # Valid START payload
        payload = InferencePayload(inferenceMode='START', dataUploadFrequency='PT1H')
        assert payload.inferenceMode == 'START'
        assert payload.dataUploadFrequency == 'PT1H'

        # Invalid START - missing required dataUploadFrequency
        with pytest.raises(ValidationError):
            InferencePayload(inferenceMode='START')

        # Valid START with optional parameters
        payload2 = InferencePayload(
            inferenceMode='START',
            dataUploadFrequency='PT30M',
            dataDelayOffsetInMinutes=15,
            targetModelVersion=1,
        )
        assert payload2.dataDelayOffsetInMinutes == 15
        assert payload2.targetModelVersion == 1

    def test_inference_payload_stop_validation(self):
        """Test InferencePayload validation for STOP mode."""
        # Valid STOP payload
        payload = InferencePayload(inferenceMode='STOP')
        assert payload.inferenceMode == 'STOP'

        # Invalid STOP - with START-only parameters
        with pytest.raises(ValidationError):
            InferencePayload(inferenceMode='STOP', dataDelayOffsetInMinutes=15)

        with pytest.raises(ValidationError):
            InferencePayload(inferenceMode='STOP', targetModelVersion=1)

    def test_inference_payload_optional_fields_validation(self):
        """Test InferencePayload optional fields validation."""
        # Valid data delay offset
        payload = InferencePayload(
            inferenceMode='START', dataUploadFrequency='PT1H', dataDelayOffsetInMinutes=30
        )
        assert payload.dataDelayOffsetInMinutes == 30

        # Invalid data delay offset - too high
        with pytest.raises(ValidationError):
            InferencePayload(
                inferenceMode='START', dataUploadFrequency='PT1H', dataDelayOffsetInMinutes=61
            )

        # Invalid data delay offset - negative
        with pytest.raises(ValidationError):
            InferencePayload(
                inferenceMode='START', dataUploadFrequency='PT1H', dataDelayOffsetInMinutes=-1
            )

        # Invalid target model version - zero
        with pytest.raises(ValidationError):
            InferencePayload(
                inferenceMode='START', dataUploadFrequency='PT1H', targetModelVersion=0
            )

    def test_weekly_operating_window_validation(self):
        """Test weekly operating window validation."""
        # Valid weekly operating window
        window = {
            'monday': ['09:00-17:00'],
            'tuesday': ['09:00-12:00', '13:00-17:00'],
            'friday': ['10:00-16:00'],
        }
        payload = InferencePayload(
            inferenceMode='START', dataUploadFrequency='PT1H', weeklyOperatingWindow=window
        )
        assert payload.weeklyOperatingWindow == window

        # Invalid day name
        with pytest.raises(ValidationError):
            InferencePayload(
                inferenceMode='START',
                dataUploadFrequency='PT1H',
                weeklyOperatingWindow={'invalid_day': ['09:00-17:00']},
            )

        # Invalid time format - invalid hour
        with pytest.raises(ValidationError):
            InferencePayload(
                inferenceMode='START',
                dataUploadFrequency='PT1H',
                weeklyOperatingWindow={'monday': ['25:00-17:00']},  # Invalid hour
            )

        # Invalid time range - start after end
        with pytest.raises(ValidationError):
            InferencePayload(
                inferenceMode='START',
                dataUploadFrequency='PT1H',
                weeklyOperatingWindow={'monday': ['17:00-09:00']},
            )

        # Invalid time range - start equals end
        with pytest.raises(ValidationError):
            InferencePayload(
                inferenceMode='START',
                dataUploadFrequency='PT1H',
                weeklyOperatingWindow={'monday': ['09:00-09:00']},
            )

        # Invalid empty time ranges list
        with pytest.raises(ValidationError):
            InferencePayload(
                inferenceMode='START',
                dataUploadFrequency='PT1H',
                weeklyOperatingWindow={'monday': []},
            )

    def test_inference_timezone_validation(self):
        """Test inference timezone validation."""
        # Valid timezone
        payload = InferencePayload(
            inferenceMode='START', dataUploadFrequency='PT1H', inferenceTimeZone='America/New_York'
        )
        assert payload.inferenceTimeZone == 'America/New_York'

        # Valid UTC timezone
        payload2 = InferencePayload(
            inferenceMode='START', dataUploadFrequency='PT1H', inferenceTimeZone='UTC'
        )
        assert payload2.inferenceTimeZone == 'UTC'

        # Invalid timezone format
        with pytest.raises(ValidationError):
            InferencePayload(
                inferenceMode='START',
                dataUploadFrequency='PT1H',
                inferenceTimeZone='invalid/timezone',
            )


class TestRequestModels:
    """Test cases for request models."""

    def test_create_computation_model_request_validation(self):
        """Test CreateComputationModelRequest validation."""
        # Valid request
        anomaly_config = ComputationModelAnomalyDetectionConfiguration(
            inputProperties='${input_data}', resultProperty='${anomaly_result}'
        )
        config = ComputationModelConfiguration(anomalyDetection=anomaly_config)

        asset_model_binding = AssetModelPropertyBindingValue(
            assetModelId='12345678-1234-1234-1234-123456789012',
            propertyId='87654321-4321-4321-4321-210987654321',
        )
        data_binding_value = ComputationModelDataBindingValue(
            assetModelProperty=asset_model_binding
        )

        request = CreateComputationModelRequest(
            computationModelName='Test Model',
            computationModelConfiguration=config,
            computationModelDataBinding={'input_data': data_binding_value},
        )
        assert request.computationModelName == 'Test Model'

        # Invalid name - empty
        with pytest.raises(ValidationError):
            CreateComputationModelRequest(
                computationModelName='',
                computationModelConfiguration=config,
                computationModelDataBinding={'input_data': data_binding_value},
            )

        # Invalid name - too long
        with pytest.raises(ValidationError):
            CreateComputationModelRequest(
                computationModelName='A' * 257,
                computationModelConfiguration=config,
                computationModelDataBinding={'input_data': data_binding_value},
            )

        # Invalid name - invalid characters
        with pytest.raises(ValidationError):
            CreateComputationModelRequest(
                computationModelName='Invalid%Name',  # % is not allowed
                computationModelConfiguration=config,
                computationModelDataBinding={'input_data': data_binding_value},
            )

        # Invalid data binding key format
        with pytest.raises(ValidationError):
            CreateComputationModelRequest(
                computationModelName='Test Model',
                computationModelConfiguration=config,
                computationModelDataBinding={'InvalidKey': data_binding_value},
            )

    def test_delete_computation_model_request_validation(self):
        """Test DeleteComputationModelRequest validation."""
        # Valid request
        request = DeleteComputationModelRequest(
            computationModelId='12345678-1234-1234-1234-123456789012'
        )
        assert request.computationModelId == '12345678-1234-1234-1234-123456789012'

        # Invalid computation model ID
        with pytest.raises(ValidationError):
            DeleteComputationModelRequest(computationModelId='invalid-uuid')

    def test_describe_computation_model_request_validation(self):
        """Test DescribeComputationModelRequest validation."""
        # Valid request with version
        request = DescribeComputationModelRequest(
            computationModelId='12345678-1234-1234-1234-123456789012',
            computationModelVersion='LATEST',
        )
        assert request.computationModelVersion == 'LATEST'

        # Valid request with numeric version
        request2 = DescribeComputationModelRequest(
            computationModelId='12345678-1234-1234-1234-123456789012',
            computationModelVersion='123',
        )
        assert request2.computationModelVersion == '123'

        # Invalid version - too high
        with pytest.raises(ValidationError):
            DescribeComputationModelRequest(
                computationModelId='12345678-1234-1234-1234-123456789012',
                computationModelVersion='10000000000',
            )

        # Invalid version - invalid string
        with pytest.raises(ValidationError):
            DescribeComputationModelRequest(
                computationModelId='12345678-1234-1234-1234-123456789012',
                computationModelVersion='INVALID',
            )

    def test_list_computation_models_request_validation(self):
        """Test ListComputationModelsRequest validation."""
        # Valid request
        request = ListComputationModelsRequest(
            computationModelType='ANOMALY_DETECTION', maxResults=50
        )
        assert request.computationModelType == 'ANOMALY_DETECTION'
        assert request.maxResults == 50

        # Invalid computation model type
        with pytest.raises(ValidationError):
            ListComputationModelsRequest(computationModelType='INVALID_TYPE')

        # Invalid max results - too high
        with pytest.raises(ValidationError):
            ListComputationModelsRequest(maxResults=251)

    def test_execute_action_request_validation(self):
        """Test ExecuteActionRequest validation."""
        # Valid request
        payload = ActionPayload(stringValue='test-action')
        target = TargetResource(assetId='12345678-1234-1234-1234-123456789012')

        request = ExecuteActionRequest(
            actionDefinitionId='87654321-4321-4321-4321-210987654321',
            actionPayload=payload,
            targetResource=target,
        )
        assert request.actionDefinitionId == '87654321-4321-4321-4321-210987654321'

        # Invalid action definition ID
        with pytest.raises(ValidationError):
            ExecuteActionRequest(
                actionDefinitionId='invalid-uuid', actionPayload=payload, targetResource=target
            )

    def test_list_actions_request_validation(self):
        """Test ListActionsRequest validation."""
        # Valid request
        request = ListActionsRequest(
            targetResourceId='12345678-1234-1234-1234-123456789012', targetResourceType='ASSET'
        )
        assert request.targetResourceType == 'ASSET'

        # Invalid target resource type
        with pytest.raises(ValidationError):
            ListActionsRequest(
                targetResourceId='12345678-1234-1234-1234-123456789012',
                targetResourceType='INVALID_TYPE',
            )

        # Invalid target resource ID
        with pytest.raises(ValidationError):
            ListActionsRequest(targetResourceId='invalid-uuid', targetResourceType='ASSET')

    def test_describe_action_request_validation(self):
        """Test DescribeActionRequest validation."""
        # Valid request
        request = DescribeActionRequest(actionId='12345678-1234-1234-1234-123456789012')
        assert request.actionId == '12345678-1234-1234-1234-123456789012'

        # Invalid action ID
        with pytest.raises(ValidationError):
            DescribeActionRequest(actionId='invalid-uuid')

    def test_list_executions_request_validation(self):
        """Test ListExecutionsRequest validation."""
        # Valid request
        request = ListExecutionsRequest(
            targetResourceId='12345678-1234-1234-1234-123456789012',
            targetResourceType='COMPUTATION_MODEL',
        )
        assert request.targetResourceType == 'COMPUTATION_MODEL'

        # Valid with action type
        request2 = ListExecutionsRequest(
            targetResourceId='12345678-1234-1234-1234-123456789012',
            targetResourceType='ASSET',
            actionType='TRAINING',
        )
        assert request2.actionType == 'TRAINING'

        # Invalid target resource type
        with pytest.raises(ValidationError):
            ListExecutionsRequest(
                targetResourceId='12345678-1234-1234-1234-123456789012',
                targetResourceType='INVALID_TYPE',
            )

    def test_describe_execution_request_validation(self):
        """Test DescribeExecutionRequest validation."""
        # Valid request
        request = DescribeExecutionRequest(executionId='12345678-1234-1234-1234-123456789012')
        assert request.executionId == '12345678-1234-1234-1234-123456789012'

        # Invalid execution ID
        with pytest.raises(ValidationError):
            DescribeExecutionRequest(executionId='invalid-uuid')

    def test_describe_computation_model_execution_summary_request_validation(self):
        """Test DescribeComputationModelExecutionSummaryRequest validation."""
        # Valid request
        request = DescribeComputationModelExecutionSummaryRequest(
            computationModelId='12345678-1234-1234-1234-123456789012'
        )
        assert request.computationModelId == '12345678-1234-1234-1234-123456789012'

        # Valid with resolve to parameters
        request2 = DescribeComputationModelExecutionSummaryRequest(
            computationModelId='12345678-1234-1234-1234-123456789012',
            resolveToResourceId='87654321-4321-4321-4321-210987654321',
            resolveToResourceType='ASSET',
        )
        assert request2.resolveToResourceId == '87654321-4321-4321-4321-210987654321'
        assert request2.resolveToResourceType == 'ASSET'

        # Invalid computation model ID
        with pytest.raises(ValidationError):
            DescribeComputationModelExecutionSummaryRequest(computationModelId='invalid-uuid')

        # Invalid resolve to resource type
        with pytest.raises(ValidationError):
            DescribeComputationModelExecutionSummaryRequest(
                computationModelId='12345678-1234-1234-1234-123456789012',
                resolveToResourceType='INVALID_TYPE',
            )

    def test_update_computation_model_request_validation(self):
        """Test UpdateComputationModelRequest validation."""
        # Valid request
        anomaly_config = ComputationModelAnomalyDetectionConfiguration(
            inputProperties='${input_data}', resultProperty='${anomaly_result}'
        )
        config = ComputationModelConfiguration(anomalyDetection=anomaly_config)

        asset_model_binding = AssetModelPropertyBindingValue(
            assetModelId='12345678-1234-1234-1234-123456789012',
            propertyId='87654321-4321-4321-4321-210987654321',
        )
        data_binding_value = ComputationModelDataBindingValue(
            assetModelProperty=asset_model_binding
        )

        request = UpdateComputationModelRequest(
            computationModelId='12345678-1234-1234-1234-123456789012',
            computationModelName='Updated Model',
            computationModelConfiguration=config,
            computationModelDataBinding={'input_data': data_binding_value},
        )
        assert request.computationModelName == 'Updated Model'

        # Invalid computation model ID
        with pytest.raises(ValidationError):
            UpdateComputationModelRequest(
                computationModelId='invalid-uuid',
                computationModelName='Updated Model',
                computationModelConfiguration=config,
                computationModelDataBinding={'input_data': data_binding_value},
            )

        # Invalid name format
        with pytest.raises(ValidationError):
            UpdateComputationModelRequest(
                computationModelId='12345678-1234-1234-1234-123456789012',
                computationModelName='Invalid%Name',  # % is not allowed
                computationModelConfiguration=config,
                computationModelDataBinding={'input_data': data_binding_value},
            )


class TestDataBindingValueFilter:
    """Test cases for DataBindingValueFilter model."""

    def test_data_binding_value_filter_asset_validation(self):
        """Test DataBindingValueFilter validation with asset filter."""
        # Valid asset filter
        filter_obj = DataBindingValueFilter(
            asset={'assetId': '12345678-1234-1234-1234-123456789012'}
        )
        assert filter_obj.asset is not None
        assert filter_obj.assetModel is None
        assert filter_obj.assetProperty is None
        assert filter_obj.assetModelProperty is None

        # Invalid asset filter - missing assetId (should pass validation as empty dict is allowed)
        filter_obj2 = DataBindingValueFilter(asset={})
        assert filter_obj2.asset == {}

        # Invalid asset filter - invalid UUID (only validates if assetId is present)
        with pytest.raises(ValidationError):
            DataBindingValueFilter(asset={'assetId': 'invalid-uuid'})

    def test_data_binding_value_filter_asset_model_validation(self):
        """Test DataBindingValueFilter validation with asset model filter."""
        # Valid asset model filter
        filter_obj = DataBindingValueFilter(
            assetModel={'assetModelId': '12345678-1234-1234-1234-123456789012'}
        )
        assert filter_obj.assetModel is not None
        assert filter_obj.asset is None

        # Invalid asset model filter - missing assetModelId (should pass validation as empty dict is allowed)
        filter_obj2 = DataBindingValueFilter(assetModel={})
        assert filter_obj2.assetModel == {}

        # Invalid asset model filter - invalid UUID (only validates if assetModelId is present)
        with pytest.raises(ValidationError):
            DataBindingValueFilter(assetModel={'assetModelId': 'invalid-uuid'})

    def test_data_binding_value_filter_asset_property_validation(self):
        """Test DataBindingValueFilter validation with asset property filter."""
        # Valid asset property filter
        filter_obj = DataBindingValueFilter(
            assetProperty={
                'assetId': '12345678-1234-1234-1234-123456789012',
                'propertyId': '87654321-4321-4321-4321-210987654321',
            }
        )
        assert filter_obj.assetProperty is not None

        # Invalid asset property filter - missing assetId
        with pytest.raises(ValidationError):
            DataBindingValueFilter(
                assetProperty={'propertyId': '87654321-4321-4321-4321-210987654321'}
            )

        # Invalid asset property filter - missing propertyId
        with pytest.raises(ValidationError):
            DataBindingValueFilter(
                assetProperty={'assetId': '12345678-1234-1234-1234-123456789012'}
            )

        # Invalid asset property filter - invalid assetId UUID
        with pytest.raises(ValidationError):
            DataBindingValueFilter(
                assetProperty={
                    'assetId': 'invalid-uuid',
                    'propertyId': '87654321-4321-4321-4321-210987654321',
                }
            )

        # Invalid asset property filter - invalid propertyId UUID
        with pytest.raises(ValidationError):
            DataBindingValueFilter(
                assetProperty={
                    'assetId': '12345678-1234-1234-1234-123456789012',
                    'propertyId': 'invalid-uuid',
                }
            )

    def test_data_binding_value_filter_asset_model_property_validation(self):
        """Test DataBindingValueFilter validation with asset model property filter."""
        # Valid asset model property filter
        filter_obj = DataBindingValueFilter(
            assetModelProperty={
                'assetModelId': '12345678-1234-1234-1234-123456789012',
                'propertyId': '87654321-4321-4321-4321-210987654321',
            }
        )
        assert filter_obj.assetModelProperty is not None

        # Invalid asset model property filter - missing assetModelId
        with pytest.raises(ValidationError):
            DataBindingValueFilter(
                assetModelProperty={'propertyId': '87654321-4321-4321-4321-210987654321'}
            )

        # Invalid asset model property filter - missing propertyId
        with pytest.raises(ValidationError):
            DataBindingValueFilter(
                assetModelProperty={'assetModelId': '12345678-1234-1234-1234-123456789012'}
            )

        # Invalid asset model property filter - invalid assetModelId UUID
        with pytest.raises(ValidationError):
            DataBindingValueFilter(
                assetModelProperty={
                    'assetModelId': 'invalid-uuid',
                    'propertyId': '87654321-4321-4321-4321-210987654321',
                }
            )

        # Invalid asset model property filter - invalid propertyId UUID
        with pytest.raises(ValidationError):
            DataBindingValueFilter(
                assetModelProperty={
                    'assetModelId': '12345678-1234-1234-1234-123456789012',
                    'propertyId': 'invalid-uuid',
                }
            )

    def test_data_binding_value_filter_validation_constraints(self):
        """Test DataBindingValueFilter validation constraints."""
        # Invalid - no filter specified
        with pytest.raises(ValidationError):
            DataBindingValueFilter()

        # Invalid - multiple filters specified
        with pytest.raises(ValidationError):
            DataBindingValueFilter(
                asset={'assetId': '12345678-1234-1234-1234-123456789012'},
                assetModel={'assetModelId': '87654321-4321-4321-4321-210987654321'},
            )


class TestAdditionalRequestModels:
    """Test cases for additional request models."""

    def test_list_computation_model_data_binding_usages_request_validation(self):
        """Test ListComputationModelDataBindingUsagesRequest validation."""
        # Valid request with asset filter
        filter_obj = DataBindingValueFilter(
            asset={'assetId': '12345678-1234-1234-1234-123456789012'}
        )
        request = ListComputationModelDataBindingUsagesRequest(
            dataBindingValueFilter=filter_obj, maxResults=50
        )
        assert request.maxResults == 50

        # Valid request with asset model property filter
        filter_obj2 = DataBindingValueFilter(
            assetModelProperty={
                'assetModelId': '12345678-1234-1234-1234-123456789012',
                'propertyId': '87654321-4321-4321-4321-210987654321',
            }
        )
        request2 = ListComputationModelDataBindingUsagesRequest(dataBindingValueFilter=filter_obj2)
        assert request2.dataBindingValueFilter is not None

        # Invalid max results - too high
        with pytest.raises(ValidationError):
            ListComputationModelDataBindingUsagesRequest(
                dataBindingValueFilter=filter_obj, maxResults=251
            )

        # Invalid max results - zero
        with pytest.raises(ValidationError):
            ListComputationModelDataBindingUsagesRequest(
                dataBindingValueFilter=filter_obj, maxResults=0
            )

    def test_list_computation_model_resolve_to_resources_request_validation(self):
        """Test ListComputationModelResolveToResourcesRequest validation."""
        # Valid request
        request = ListComputationModelResolveToResourcesRequest(
            computationModelId='12345678-1234-1234-1234-123456789012', maxResults=100
        )
        assert request.computationModelId == '12345678-1234-1234-1234-123456789012'
        assert request.maxResults == 100

        # Valid request with next token (base64 encoded)
        request2 = ListComputationModelResolveToResourcesRequest(
            computationModelId='12345678-1234-1234-1234-123456789012',
            nextToken='bmV4dFBhZ2VUb2tlbg==',
        )
        assert request2.nextToken == 'bmV4dFBhZ2VUb2tlbg=='

        # Invalid computation model ID
        with pytest.raises(ValidationError):
            ListComputationModelResolveToResourcesRequest(computationModelId='invalid-uuid')

        # Invalid max results - too high
        with pytest.raises(ValidationError):
            ListComputationModelResolveToResourcesRequest(
                computationModelId='12345678-1234-1234-1234-123456789012', maxResults=251
            )

        # Invalid max results - zero
        with pytest.raises(ValidationError):
            ListComputationModelResolveToResourcesRequest(
                computationModelId='12345678-1234-1234-1234-123456789012', maxResults=0
            )


class TestAdditionalValidationScenarios:
    """Test cases for additional validation scenarios to improve coverage."""

    def test_retraining_configuration_none_promotion_validation(self):
        """Test RetrainingConfiguration with None promotion value."""
        # Test line 415 - promotion validation with None
        config = RetrainingConfiguration(
            lookbackWindow='P180D', retrainingFrequency='P30D', promotion=None
        )
        assert config.promotion is None

    def test_retraining_configuration_none_retraining_start_date_validation(self):
        """Test RetrainingConfiguration with None retrainingStartDate value."""
        # Test line 422 - retrainingStartDate validation with None
        config = RetrainingConfiguration(
            lookbackWindow='P180D', retrainingFrequency='P30D', retrainingStartDate=None
        )
        assert config.retrainingStartDate is None

    def test_training_payload_none_timestamp_validation(self):
        """Test TrainingPayload with None timestamp values."""
        # Test lines 484->493 - timestamp validation with None values
        payload = TrainingPayload(
            trainingMode='STOP_RETRAINING_SCHEDULER',
            exportDataStartTime=None,
            exportDataEndTime=None,
        )
        assert payload.exportDataStartTime is None
        assert payload.exportDataEndTime is None

    def test_training_payload_none_target_sampling_rate_validation(self):
        """Test TrainingPayload with None targetSamplingRate value."""
        # Test line 550 - targetSamplingRate validation with None
        payload = TrainingPayload(
            trainingMode='STOP_RETRAINING_SCHEDULER', targetSamplingRate=None
        )
        assert payload.targetSamplingRate is None

    def test_inference_payload_none_data_upload_frequency_validation(self):
        """Test InferencePayload with None dataUploadFrequency value."""
        # Test lines 586->594 - dataUploadFrequency validation with None
        payload = InferencePayload(inferenceMode='STOP', dataUploadFrequency=None)
        assert payload.dataUploadFrequency is None

    def test_inference_payload_none_data_delay_offset_validation(self):
        """Test InferencePayload with None dataDelayOffsetInMinutes value."""
        # Test line 619 - dataDelayOffsetInMinutes validation with None
        payload = InferencePayload(
            inferenceMode='STOP', dataUploadFrequency=None, dataDelayOffsetInMinutes=None
        )
        assert payload.dataDelayOffsetInMinutes is None

    def test_inference_payload_none_target_model_version_validation(self):
        """Test InferencePayload with None targetModelVersion value."""
        # Test line 626 - targetModelVersion validation with None
        payload = InferencePayload(
            inferenceMode='STOP', dataUploadFrequency=None, targetModelVersion=None
        )
        assert payload.targetModelVersion is None

    def test_inference_payload_none_weekly_operating_window_validation(self):
        """Test InferencePayload with None weeklyOperatingWindow value."""
        # Test line 804 - weeklyOperatingWindow validation with None
        payload = InferencePayload(
            inferenceMode='START', dataUploadFrequency='PT1H', weeklyOperatingWindow=None
        )
        assert payload.weeklyOperatingWindow is None

    def test_inference_payload_none_inference_time_zone_validation(self):
        """Test InferencePayload with None inferenceTimeZone value."""
        # Test line 813 - inferenceTimeZone validation with None
        payload = InferencePayload(
            inferenceMode='START', dataUploadFrequency='PT1H', inferenceTimeZone=None
        )
        assert payload.inferenceTimeZone is None

    def test_inference_payload_start_mode_constraints_validation(self):
        """Test InferencePayload START mode constraints validation."""
        # Test lines 820->825 - START mode constraints
        # Valid START mode with required dataUploadFrequency
        payload = InferencePayload(inferenceMode='START', dataUploadFrequency='PT1H')
        assert payload.inferenceMode == 'START'
        assert payload.dataUploadFrequency == 'PT1H'

    def test_inference_payload_stop_mode_constraints_validation(self):
        """Test InferencePayload STOP mode constraints validation."""
        # Test lines 830->835 - STOP mode constraints
        # Valid STOP mode without START-only parameters
        payload = InferencePayload(inferenceMode='STOP')
        assert payload.inferenceMode == 'STOP'

        # Test that STOP mode allows weeklyOperatingWindow and inferenceTimeZone
        payload2 = InferencePayload(
            inferenceMode='STOP',
            weeklyOperatingWindow={'monday': ['09:00-17:00']},
            inferenceTimeZone='UTC',
        )
        assert payload2.weeklyOperatingWindow is not None
        assert payload2.inferenceTimeZone == 'UTC'

        # Test STOP mode constraint violations - should raise errors
        with pytest.raises(ValidationError):
            InferencePayload(
                inferenceMode='STOP',
                dataDelayOffsetInMinutes=15,  # This should trigger line 832-834
            )

        with pytest.raises(ValidationError):
            InferencePayload(
                inferenceMode='STOP',
                targetModelVersion=1,  # This should trigger line 832-834
            )

    def test_data_binding_value_filter_empty_dict_validation(self):
        """Test DataBindingValueFilter with empty dictionaries to trigger specific validation paths."""
        # Test asset filter with empty dict - should trigger validation but pass
        filter_obj = DataBindingValueFilter(asset={})
        assert filter_obj.asset == {}

        # Test assetModel filter with empty dict - should trigger validation but pass
        filter_obj2 = DataBindingValueFilter(assetModel={})
        assert filter_obj2.assetModel == {}

        # Test asset filter validation path with missing assetId
        with pytest.raises(ValidationError):
            DataBindingValueFilter(asset={'wrongKey': 'value'})

        # Test assetModel filter validation path with missing assetModelId
        with pytest.raises(ValidationError):
            DataBindingValueFilter(assetModel={'wrongKey': 'value'})

    def test_inference_payload_start_mode_required_frequency_validation(self):
        """Test InferencePayload START mode dataUploadFrequency requirement."""
        # Test lines 820->825 - START mode constraint validation
        # This should trigger the validation error for missing dataUploadFrequency
        with pytest.raises(ValidationError):
            InferencePayload(inferenceMode='START')  # Missing required dataUploadFrequency

    def test_training_payload_timestamp_validation_edge_cases(self):
        """Test TrainingPayload timestamp validation edge cases."""
        # Test lines 484->493 - timestamp validation with specific None handling
        # Create payload that triggers the timestamp validation path
        payload = TrainingPayload(
            trainingMode='TRAIN_MODEL',
            exportDataStartTime=1640995200,
            exportDataEndTime=1641081600,
            targetSamplingRate=None,  # This should trigger line 550
        )
        assert payload.exportDataStartTime == 1640995200
        assert payload.exportDataEndTime == 1641081600
        assert payload.targetSamplingRate is None

    def test_inference_payload_validation_edge_cases(self):
        """Test InferencePayload validation edge cases."""
        # Test lines 586->594, 619, 626 - None value validation paths
        payload = InferencePayload(
            inferenceMode='STOP',
            dataUploadFrequency=None,  # Line 586->594
            dataDelayOffsetInMinutes=None,  # Line 619
            targetModelVersion=None,  # Line 626
        )
        assert payload.dataUploadFrequency is None
        assert payload.dataDelayOffsetInMinutes is None
        assert payload.targetModelVersion is None

    def test_inference_payload_mode_constraint_edge_cases(self):
        """Test InferencePayload mode constraint edge cases."""
        # Test lines 820->825 and 830->835 - mode constraint validation paths

        # Test START mode with valid dataUploadFrequency (line 820->825)
        payload_start = InferencePayload(inferenceMode='START', dataUploadFrequency='PT1H')
        assert payload_start.inferenceMode == 'START'

        # Test STOP mode constraint validation (line 830->835)
        payload_stop = InferencePayload(inferenceMode='STOP')
        assert payload_stop.inferenceMode == 'STOP'

        # Test STOP mode with invalid START-only parameters
        with pytest.raises(ValidationError) as exc_info:
            InferencePayload(inferenceMode='STOP', dataDelayOffsetInMinutes=30)
        assert 'can only be used with START inference mode' in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            InferencePayload(inferenceMode='STOP', targetModelVersion=2)
        assert 'can only be used with START inference mode' in str(exc_info.value)

    def test_training_payload_timestamp_validation_with_none_values(self):
        """Test TrainingPayload timestamp validation with None values to cover lines 484->493."""
        # Test the specific None validation paths in lines 484->493
        # This should fail validation since TRAIN_MODEL requires both timestamps
        with pytest.raises(ValidationError):
            TrainingPayload(
                trainingMode='TRAIN_MODEL',
                exportDataStartTime=None,  # This should trigger line 484->493
                exportDataEndTime=1641081600,
            )

        # Test with both None values for TRAIN_MODEL - should also fail
        with pytest.raises(ValidationError):
            TrainingPayload(
                trainingMode='TRAIN_MODEL',
                exportDataStartTime=None,  # Line 484->493
                exportDataEndTime=None,  # Line 484->493
            )

        # Test with both None values for STOP_RETRAINING_SCHEDULER - should pass
        payload2 = TrainingPayload(
            trainingMode='STOP_RETRAINING_SCHEDULER',
            exportDataStartTime=None,  # Line 484->493
            exportDataEndTime=None,  # Line 484->493
        )
        assert payload2.exportDataStartTime is None
        assert payload2.exportDataEndTime is None

    def test_training_payload_target_sampling_rate_none_validation(self):
        """Test TrainingPayload targetSamplingRate None validation to cover line 550."""
        # Test line 550 - targetSamplingRate validation with None
        payload = TrainingPayload(
            trainingMode='STOP_RETRAINING_SCHEDULER',
            targetSamplingRate=None,  # This should trigger line 550
        )
        assert payload.targetSamplingRate is None

        # Test with valid value to ensure validation works
        payload2 = TrainingPayload(
            trainingMode='TRAIN_MODEL',
            exportDataStartTime=1640995200,
            exportDataEndTime=1641081600,
            targetSamplingRate='PT1M',  # Valid value
        )
        assert payload2.targetSamplingRate == 'PT1M'

    def test_inference_payload_data_upload_frequency_none_validation(self):
        """Test InferencePayload dataUploadFrequency None validation to cover lines 586->594."""
        # Test lines 586->594 - dataUploadFrequency validation with None
        payload = InferencePayload(
            inferenceMode='STOP',
            dataUploadFrequency=None,  # This should trigger lines 586->594
        )
        assert payload.dataUploadFrequency is None

        # Test with valid value
        payload2 = InferencePayload(
            inferenceMode='START',
            dataUploadFrequency='PT1H',  # Valid value
        )
        assert payload2.dataUploadFrequency == 'PT1H'

    def test_inference_payload_data_delay_offset_none_validation(self):
        """Test InferencePayload dataDelayOffsetInMinutes None validation to cover line 619."""
        # Test line 619 - dataDelayOffsetInMinutes validation with None
        payload = InferencePayload(
            inferenceMode='START',
            dataUploadFrequency='PT1H',
            dataDelayOffsetInMinutes=None,  # This should trigger line 619
        )
        assert payload.dataDelayOffsetInMinutes is None

        # Test with valid value
        payload2 = InferencePayload(
            inferenceMode='START',
            dataUploadFrequency='PT1H',
            dataDelayOffsetInMinutes=30,  # Valid value
        )
        assert payload2.dataDelayOffsetInMinutes == 30

    def test_inference_payload_target_model_version_none_validation(self):
        """Test InferencePayload targetModelVersion None validation to cover line 626."""
        # Test line 626 - targetModelVersion validation with None
        payload = InferencePayload(
            inferenceMode='START',
            dataUploadFrequency='PT1H',
            targetModelVersion=None,  # This should trigger line 626
        )
        assert payload.targetModelVersion is None

        # Test with valid value
        payload2 = InferencePayload(
            inferenceMode='START',
            dataUploadFrequency='PT1H',
            targetModelVersion=5,  # Valid value
        )
        assert payload2.targetModelVersion == 5

    def test_inference_payload_start_mode_validation_paths(self):
        """Test InferencePayload START mode validation to cover lines 820->825."""
        # Test lines 820->825 - START mode constraint validation
        # Valid START mode with required dataUploadFrequency
        payload = InferencePayload(inferenceMode='START', dataUploadFrequency='PT30M')
        assert payload.inferenceMode == 'START'
        assert payload.dataUploadFrequency == 'PT30M'

        # Test START mode missing required dataUploadFrequency - should trigger validation error
        with pytest.raises(
            ValidationError, match='dataUploadFrequency is required for START inference mode'
        ):
            InferencePayload(inferenceMode='START')

    def test_inference_payload_stop_mode_validation_paths(self):
        """Test InferencePayload STOP mode validation to cover lines 830->835."""
        # Test lines 830->835 - STOP mode constraint validation
        # Valid STOP mode
        payload = InferencePayload(inferenceMode='STOP')
        assert payload.inferenceMode == 'STOP'

        # Test STOP mode with START-only parameters - should trigger validation errors
        with pytest.raises(ValidationError, match='can only be used with START inference mode'):
            InferencePayload(
                inferenceMode='STOP',
                dataDelayOffsetInMinutes=15,  # START-only parameter
            )

        with pytest.raises(ValidationError, match='can only be used with START inference mode'):
            InferencePayload(
                inferenceMode='STOP',
                targetModelVersion=3,  # START-only parameter
            )

        # Test STOP mode with both START-only parameters
        with pytest.raises(ValidationError, match='can only be used with START inference mode'):
            InferencePayload(
                inferenceMode='STOP', dataDelayOffsetInMinutes=20, targetModelVersion=2
            )


class TestEdgeCases:
    """Test cases for edge cases and additional validation scenarios."""

    def test_create_computation_model_request_description_validation(self):
        """Test CreateComputationModelRequest description validation edge cases."""
        # Valid request with description
        anomaly_config = ComputationModelAnomalyDetectionConfiguration(
            inputProperties='${input_data}', resultProperty='${anomaly_result}'
        )
        config = ComputationModelConfiguration(anomalyDetection=anomaly_config)

        asset_model_binding = AssetModelPropertyBindingValue(
            assetModelId='12345678-1234-1234-1234-123456789012',
            propertyId='87654321-4321-4321-4321-210987654321',
        )
        data_binding_value = ComputationModelDataBindingValue(
            assetModelProperty=asset_model_binding
        )

        request = CreateComputationModelRequest(
            computationModelName='Test Model',
            computationModelConfiguration=config,
            computationModelDataBinding={'input_data': data_binding_value},
            computationModelDescription='Valid description with allowed characters 123 _-#$*!@',
        )
        assert request.computationModelDescription is not None

        # Invalid description - too long
        with pytest.raises(ValidationError):
            CreateComputationModelRequest(
                computationModelName='Test Model',
                computationModelConfiguration=config,
                computationModelDataBinding={'input_data': data_binding_value},
                computationModelDescription='A' * 2049,  # Too long
            )

        # Invalid description - invalid characters
        with pytest.raises(ValidationError):
            CreateComputationModelRequest(
                computationModelName='Test Model',
                computationModelConfiguration=config,
                computationModelDataBinding={'input_data': data_binding_value},
                computationModelDescription='Invalid%Description',  # % is not allowed
            )

    def test_update_computation_model_request_description_validation(self):
        """Test UpdateComputationModelRequest description validation edge cases."""
        # Valid request with description
        anomaly_config = ComputationModelAnomalyDetectionConfiguration(
            inputProperties='${input_data}', resultProperty='${anomaly_result}'
        )
        config = ComputationModelConfiguration(anomalyDetection=anomaly_config)

        asset_model_binding = AssetModelPropertyBindingValue(
            assetModelId='12345678-1234-1234-1234-123456789012',
            propertyId='87654321-4321-4321-4321-210987654321',
        )
        data_binding_value = ComputationModelDataBindingValue(
            assetModelProperty=asset_model_binding
        )

        request = UpdateComputationModelRequest(
            computationModelId='12345678-1234-1234-1234-123456789012',
            computationModelName='Updated Model',
            computationModelConfiguration=config,
            computationModelDataBinding={'input_data': data_binding_value},
            computationModelDescription='Valid updated description',
        )
        assert request.computationModelDescription is not None

        # Invalid description - too long
        with pytest.raises(ValidationError):
            UpdateComputationModelRequest(
                computationModelId='12345678-1234-1234-1234-123456789012',
                computationModelName='Updated Model',
                computationModelConfiguration=config,
                computationModelDataBinding={'input_data': data_binding_value},
                computationModelDescription='A' * 2049,  # Too long
            )

        # Invalid description - invalid characters
        with pytest.raises(ValidationError):
            UpdateComputationModelRequest(
                computationModelId='12345678-1234-1234-1234-123456789012',
                computationModelName='Updated Model',
                computationModelConfiguration=config,
                computationModelDataBinding={'input_data': data_binding_value},
                computationModelDescription='Invalid%Description',  # % is not allowed
            )

    def test_describe_computation_model_execution_summary_request_edge_cases(self):
        """Test DescribeComputationModelExecutionSummaryRequest edge cases."""
        # Valid request with None resolve to resource ID (should pass validation)
        request = DescribeComputationModelExecutionSummaryRequest(
            computationModelId='12345678-1234-1234-1234-123456789012',
            resolveToResourceId=None,
            resolveToResourceType=None,
        )
        assert request.resolveToResourceId is None
        assert request.resolveToResourceType is None

        # Invalid resolve to resource ID - invalid UUID
        with pytest.raises(ValidationError):
            DescribeComputationModelExecutionSummaryRequest(
                computationModelId='12345678-1234-1234-1234-123456789012',
                resolveToResourceId='invalid-uuid',
            )

    def test_list_actions_request_edge_cases(self):
        """Test ListActionsRequest edge cases."""
        # Valid request with None resolve to parameters
        request = ListActionsRequest(
            targetResourceId='12345678-1234-1234-1234-123456789012',
            targetResourceType='ASSET',
            resolveToResourceId=None,
            resolveToResourceType=None,
        )
        assert request.resolveToResourceId is None
        assert request.resolveToResourceType is None

        # Invalid resolve to resource ID - invalid UUID
        with pytest.raises(ValidationError):
            ListActionsRequest(
                targetResourceId='12345678-1234-1234-1234-123456789012',
                targetResourceType='ASSET',
                resolveToResourceId='invalid-uuid',
            )

    def test_list_executions_request_edge_cases(self):
        """Test ListExecutionsRequest edge cases."""
        # Valid request with None resolve to parameters
        request = ListExecutionsRequest(
            targetResourceId='12345678-1234-1234-1234-123456789012',
            targetResourceType='COMPUTATION_MODEL',
            resolveToResourceId=None,
            resolveToResourceType=None,
        )
        assert request.resolveToResourceId is None
        assert request.resolveToResourceType is None

        # Invalid resolve to resource ID - invalid UUID
        with pytest.raises(ValidationError):
            ListExecutionsRequest(
                targetResourceId='12345678-1234-1234-1234-123456789012',
                targetResourceType='COMPUTATION_MODEL',
                resolveToResourceId='invalid-uuid',
            )


if __name__ == '__main__':
    pytest.main([__file__])
