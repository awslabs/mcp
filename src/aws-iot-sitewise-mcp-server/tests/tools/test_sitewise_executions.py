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

"""Tests for AWS IoT SiteWise Executions Tools."""

import os
import pytest
import sys
from awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_executions import (
    describe_action,
    describe_execution,
    execute_action,
    execute_inference_action,
    execute_training_action,
    list_actions,
    list_executions,
)
from botocore.exceptions import ClientError
from unittest.mock import Mock, patch


# Add the project root directory and its parent to Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(script_dir)
sys.path.insert(0, project_dir)
sys.path.insert(0, os.path.dirname(project_dir))
sys.path.insert(0, os.path.dirname(os.path.dirname(project_dir)))


class TestSiteWiseExecutions:
    """Test cases for SiteWise executions tools."""

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_executions.create_sitewise_client')
    def test_execute_action_success(self, mock_boto_client):
        """Test successful action execution."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        mock_response = {
            'actionId': '12345678-1234-1234-1234-123456789012',
        }
        mock_client.execute_action.return_value = mock_response

        action_payload = {'stringValue': '{"key": "value"}'}
        target_resource = {'computationModelId': '87654321-4321-4321-4321-210987654321'}

        result = execute_action(
            action_definition_id='11111111-1111-1111-1111-111111111111',
            action_payload=action_payload,
            target_resource=target_resource,
            region='us-east-1',
        )

        assert result['success'] is True
        assert result['actionId'] == '12345678-1234-1234-1234-123456789012'
        mock_client.execute_action.assert_called_once()

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_executions.create_sitewise_client')
    def test_execute_action_with_all_params(self, mock_boto_client):
        """Test action execution with all optional parameters."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        mock_response = {
            'actionId': '87654321-4321-4321-4321-210987654321',
        }
        mock_client.execute_action.return_value = mock_response

        action_payload = {'stringValue': '{"operation": "start"}'}
        target_resource = {'assetId': '12345678-1234-1234-1234-123456789012'}
        resolve_to = {'assetId': '11111111-1111-1111-1111-111111111111'}

        result = execute_action(
            action_definition_id='22222222-2222-2222-2222-222222222222',
            action_payload=action_payload,
            target_resource=target_resource,
            region='us-west-2',
            client_token='12345678-1234-1234-1234-123456789012',
            resolve_to=resolve_to,
        )

        assert result['success'] is True
        assert result['actionId'] == '87654321-4321-4321-4321-210987654321'
        mock_client.execute_action.assert_called_once()

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_executions.create_sitewise_client')
    def test_execute_action_client_error(self, mock_boto_client):
        """Test action execution with client error."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        error_response = {
            'Error': {
                'Code': 'InvalidRequestException',
                'Message': 'Invalid action payload',
            }
        }
        mock_client.execute_action.side_effect = ClientError(error_response, 'ExecuteAction')

        action_payload = {'stringValue': '{"key": "value"}'}
        target_resource = {'computationModelId': '87654321-4321-4321-4321-210987654321'}

        result = execute_action(
            action_definition_id='11111111-1111-1111-1111-111111111111',
            action_payload=action_payload,
            target_resource=target_resource,
        )

        assert result['success'] is False
        assert result['error_code'] == 'InvalidRequestException'
        assert 'Invalid action payload' in result['error']

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_executions.create_sitewise_client')
    def test_list_actions_success(self, mock_boto_client):
        """Test successful actions listing."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        mock_response = {
            'actionSummaries': [
                {'actionId': 'action-1', 'actionDefinitionId': 'def-1'},
                {'actionId': 'action-2', 'actionDefinitionId': 'def-2'},
            ],
            'nextToken': 'next-token-123',
        }
        mock_client.list_actions.return_value = mock_response

        result = list_actions(
            target_resource_id='12345678-1234-1234-1234-123456789012',
            target_resource_type='COMPUTATION_MODEL',
            region='us-east-1',
        )

        assert result['success'] is True
        assert len(result['actionSummaries']) == 2
        assert result['nextToken'] == 'next-token-123'
        mock_client.list_actions.assert_called_once()

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_executions.create_sitewise_client')
    def test_list_actions_with_filters(self, mock_boto_client):
        """Test actions listing with filters."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        mock_response = {
            'actionSummaries': [
                {'actionId': 'action-1', 'actionDefinitionId': 'def-1'},
            ],
            'nextToken': None,
        }
        mock_client.list_actions.return_value = mock_response

        result = list_actions(
            target_resource_id='87654321-4321-4321-4321-210987654321',
            target_resource_type='ASSET',
            region='us-west-2',
            max_results=50,
            next_token='cHJldi10b2tlbg==',
            resolve_to_resource_id='11111111-1111-1111-1111-111111111111',
            resolve_to_resource_type='ASSET',
        )

        assert result['success'] is True
        assert len(result['actionSummaries']) == 1
        assert result['nextToken'] is None
        mock_client.list_actions.assert_called_once_with(
            targetResourceId='87654321-4321-4321-4321-210987654321',
            targetResourceType='ASSET',
            maxResults=50,
            nextToken='cHJldi10b2tlbg==',
            resolveToResourceId='11111111-1111-1111-1111-111111111111',
            resolveToResourceType='ASSET',
        )

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_executions.create_sitewise_client')
    def test_list_actions_client_error(self, mock_boto_client):
        """Test actions listing with client error."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        error_response = {
            'Error': {
                'Code': 'ResourceNotFoundException',
                'Message': 'Target resource not found',
            }
        }
        mock_client.list_actions.side_effect = ClientError(error_response, 'ListActions')

        result = list_actions(
            target_resource_id='12345678-1234-1234-1234-123456789012',
            target_resource_type='COMPUTATION_MODEL',
        )

        assert result['success'] is False
        assert result['error_code'] == 'ResourceNotFoundException'
        assert 'Target resource not found' in result['error']

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_executions.create_sitewise_client')
    def test_describe_action_success(self, mock_boto_client):
        """Test successful action description."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        mock_response = {
            'actionId': '12345678-1234-1234-1234-123456789012',
            'actionDefinitionId': '87654321-4321-4321-4321-210987654321',
            'actionPayload': {'stringValue': '{"key": "value"}'},
            'targetResource': {'computationModelId': '11111111-1111-1111-1111-111111111111'},
            'resolveTo': {'assetId': '22222222-2222-2222-2222-222222222222'},
            'executionTime': Mock(),
        }
        mock_response['executionTime'].isoformat.return_value = '2023-01-01T00:00:00Z'
        mock_client.describe_action.return_value = mock_response

        result = describe_action(
            action_id='12345678-1234-1234-1234-123456789012',
            region='us-east-1',
        )

        assert result['success'] is True
        assert result['actionId'] == '12345678-1234-1234-1234-123456789012'
        assert result['actionDefinitionId'] == '87654321-4321-4321-4321-210987654321'
        assert result['actionPayload']['stringValue'] == '{"key": "value"}'
        assert 'targetResource' in result
        assert 'resolveTo' in result
        mock_client.describe_action.assert_called_once()

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_executions.create_sitewise_client')
    def test_describe_action_client_error(self, mock_boto_client):
        """Test action description with client error."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        error_response = {
            'Error': {
                'Code': 'ResourceNotFoundException',
                'Message': 'Action not found',
            }
        }
        mock_client.describe_action.side_effect = ClientError(error_response, 'DescribeAction')

        result = describe_action(
            action_id='12345678-1234-1234-1234-123456789012',
        )

        assert result['success'] is False
        assert result['error_code'] == 'ResourceNotFoundException'
        assert 'Action not found' in result['error']

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_executions.execute_action')
    def test_execute_training_action_train_model_success(self, mock_execute_action):
        """Test successful training action execution in TRAIN_MODEL mode."""
        mock_execute_action.return_value = {
            'success': True,
            'actionId': '12345678-1234-1234-1234-123456789012',
        }

        target_resource = {'computationModelId': '87654321-4321-4321-4321-210987654321'}

        result = execute_training_action(
            training_action_definition_id='11111111-1111-1111-1111-111111111111',
            training_mode='TRAIN_MODEL',
            target_resource=target_resource,
            export_data_start_time=1717225200,
            export_data_end_time=1722789360,
            region='us-east-1',
        )

        assert result['success'] is True
        assert result['actionId'] == '12345678-1234-1234-1234-123456789012'
        assert 'trainingPayload' in result
        assert result['trainingPayload']['trainingMode'] == 'TRAIN_MODEL'
        assert result['trainingPayload']['exportDataStartTime'] == 1717225200
        assert result['trainingPayload']['exportDataEndTime'] == 1722789360

        # Verify execute_action was called with correct parameters
        mock_execute_action.assert_called_once()
        call_args = mock_execute_action.call_args
        assert call_args[1]['action_definition_id'] == '11111111-1111-1111-1111-111111111111'
        assert 'stringValue' in call_args[1]['action_payload']

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_executions.execute_action')
    def test_execute_training_action_with_all_configs(self, mock_execute_action):
        """Test training action with all optional configurations."""
        mock_execute_action.return_value = {
            'success': True,
            'actionId': '87654321-4321-4321-4321-210987654321',
        }

        target_resource = {'computationModelId': '12345678-1234-1234-1234-123456789012'}
        resolve_to = {'assetId': '11111111-1111-1111-1111-111111111111'}

        result = execute_training_action(
            training_action_definition_id='22222222-2222-2222-2222-222222222222',
            training_mode='TRAIN_MODEL',
            target_resource=target_resource,
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
            client_token='12345678-1234-1234-1234-123456789012',
            resolve_to=resolve_to,
        )

        assert result['success'] is True
        assert 'trainingPayload' in result
        payload = result['trainingPayload']
        assert payload['targetSamplingRate'] == 'PT5M'
        assert 'labelInputConfiguration' in payload
        assert 'modelEvaluationConfiguration' in payload
        assert 'modelMetricsDestination' in payload

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_executions.execute_action')
    def test_execute_training_action_start_retraining_scheduler(self, mock_execute_action):
        """Test training action in START_RETRAINING_SCHEDULER mode."""
        mock_execute_action.return_value = {
            'success': True,
            'actionId': '12345678-1234-1234-1234-123456789012',
        }

        target_resource = {'computationModelId': '87654321-4321-4321-4321-210987654321'}

        result = execute_training_action(
            training_action_definition_id='11111111-1111-1111-1111-111111111111',
            training_mode='START_RETRAINING_SCHEDULER',
            target_resource=target_resource,
            lookback_window='P360D',
            retraining_frequency='P30D',
            promotion='SERVICE_MANAGED',
            retraining_start_date=1730332800,
        )

        assert result['success'] is True
        assert 'trainingPayload' in result
        payload = result['trainingPayload']
        assert payload['trainingMode'] == 'START_RETRAINING_SCHEDULER'
        assert 'retrainingConfiguration' in payload
        assert payload['retrainingConfiguration']['lookbackWindow'] == 'P360D'
        assert payload['retrainingConfiguration']['retrainingFrequency'] == 'P30D'

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_executions.execute_action')
    def test_execute_training_action_stop_retraining_scheduler(self, mock_execute_action):
        """Test training action in STOP_RETRAINING_SCHEDULER mode."""
        mock_execute_action.return_value = {
            'success': True,
            'actionId': '12345678-1234-1234-1234-123456789012',
        }

        target_resource = {'computationModelId': '87654321-4321-4321-4321-210987654321'}

        result = execute_training_action(
            training_action_definition_id='11111111-1111-1111-1111-111111111111',
            training_mode='STOP_RETRAINING_SCHEDULER',
            target_resource=target_resource,
        )

        assert result['success'] is True
        assert 'trainingPayload' in result
        payload = result['trainingPayload']
        assert payload['trainingMode'] == 'STOP_RETRAINING_SCHEDULER'

    def test_execute_training_action_validation_error_partial_label_config(self):
        """Test training action with partial label configuration."""
        target_resource = {'computationModelId': '87654321-4321-4321-4321-210987654321'}

        result = execute_training_action(
            training_action_definition_id='11111111-1111-1111-1111-111111111111',
            training_mode='TRAIN_MODEL',
            target_resource=target_resource,
            export_data_start_time=1717225200,
            export_data_end_time=1722789360,
            label_bucket_name='bucket-name',  # Missing label_s3_prefix
        )

        assert result['success'] is False
        assert result['error_code'] == 'ValidationException'
        assert (
            'Both label_bucket_name and label_s3_prefix must be provided together'
            in result['error']
        )

    def test_execute_training_action_validation_error_partial_evaluation_config(self):
        """Test training action with partial evaluation configuration."""
        target_resource = {'computationModelId': '87654321-4321-4321-4321-210987654321'}

        result = execute_training_action(
            training_action_definition_id='11111111-1111-1111-1111-111111111111',
            training_mode='TRAIN_MODEL',
            target_resource=target_resource,
            export_data_start_time=1717225200,
            export_data_end_time=1722789360,
            evaluation_start_time=1719817200,  # Missing other evaluation params
        )

        assert result['success'] is False
        assert result['error_code'] == 'ValidationException'
        assert 'All four evaluation parameters' in result['error']

    def test_execute_training_action_validation_error_partial_metrics_config(self):
        """Test training action with partial metrics configuration."""
        target_resource = {'computationModelId': '87654321-4321-4321-4321-210987654321'}

        result = execute_training_action(
            training_action_definition_id='11111111-1111-1111-1111-111111111111',
            training_mode='TRAIN_MODEL',
            target_resource=target_resource,
            export_data_start_time=1717225200,
            export_data_end_time=1722789360,
            metrics_bucket_name='bucket-name',  # Missing metrics_s3_prefix
        )

        assert result['success'] is False
        assert result['error_code'] == 'ValidationException'
        assert (
            'Both metrics_bucket_name and metrics_s3_prefix must be provided together'
            in result['error']
        )

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_executions.execute_action')
    def test_execute_inference_action_start_success(self, mock_execute_action):
        """Test successful inference action execution in START mode."""
        mock_execute_action.return_value = {
            'success': True,
            'actionId': '12345678-1234-1234-1234-123456789012',
        }

        target_resource = {'computationModelId': '87654321-4321-4321-4321-210987654321'}

        result = execute_inference_action(
            inference_action_definition_id='11111111-1111-1111-1111-111111111111',
            inference_mode='START',
            target_resource=target_resource,
            data_upload_frequency='PT15M',
            region='us-east-1',
        )

        assert result['success'] is True
        assert result['actionId'] == '12345678-1234-1234-1234-123456789012'
        assert 'inferencePayload' in result
        assert result['inferencePayload']['inferenceMode'] == 'START'
        assert result['inferencePayload']['dataUploadFrequency'] == 'PT15M'

        # Verify execute_action was called with correct parameters
        mock_execute_action.assert_called_once()
        call_args = mock_execute_action.call_args
        assert call_args[1]['action_definition_id'] == '11111111-1111-1111-1111-111111111111'
        assert 'stringValue' in call_args[1]['action_payload']

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_executions.execute_action')
    def test_execute_inference_action_with_all_params(self, mock_execute_action):
        """Test inference action with all optional parameters."""
        mock_execute_action.return_value = {
            'success': True,
            'actionId': '87654321-4321-4321-4321-210987654321',
        }

        target_resource = {'computationModelId': '12345678-1234-1234-1234-123456789012'}
        resolve_to = {'assetId': '11111111-1111-1111-1111-111111111111'}
        weekly_operating_window = {
            'monday': ['10:00-11:00', '13:00-15:00'],
            'tuesday': ['11:00-13:00'],
        }

        result = execute_inference_action(
            inference_action_definition_id='22222222-2222-2222-2222-222222222222',
            inference_mode='START',
            target_resource=target_resource,
            data_upload_frequency='PT30M',
            data_delay_offset_in_minutes=30,
            target_model_version=3,
            weekly_operating_window=weekly_operating_window,
            inference_time_zone='America/Chicago',
            client_token='12345678-1234-1234-1234-123456789012',
            resolve_to=resolve_to,
        )

        assert result['success'] is True
        assert 'inferencePayload' in result
        payload = result['inferencePayload']
        assert payload['dataDelayOffsetInMinutes'] == 30
        assert payload['targetModelVersion'] == 3
        assert payload['weeklyOperatingWindow'] == weekly_operating_window
        assert payload['inferenceTimeZone'] == 'America/Chicago'

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_executions.execute_action')
    def test_execute_inference_action_stop_mode(self, mock_execute_action):
        """Test inference action in STOP mode."""
        mock_execute_action.return_value = {
            'success': True,
            'actionId': '12345678-1234-1234-1234-123456789012',
        }

        target_resource = {'computationModelId': '87654321-4321-4321-4321-210987654321'}

        result = execute_inference_action(
            inference_action_definition_id='11111111-1111-1111-1111-111111111111',
            inference_mode='STOP',
            target_resource=target_resource,
        )

        assert result['success'] is True
        assert 'inferencePayload' in result
        payload = result['inferencePayload']
        assert payload['inferenceMode'] == 'STOP'

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_executions.create_sitewise_client')
    def test_list_executions_success(self, mock_boto_client):
        """Test successful executions listing."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        mock_response = {
            'executionSummaries': [
                {'executionId': 'exec-1', 'actionType': 'AWS/ANOMALY_DETECTION_TRAINING'},
                {'executionId': 'exec-2', 'actionType': 'AWS/ANOMALY_DETECTION_INFERENCE'},
            ],
            'nextToken': 'next-token-456',
        }
        mock_client.list_executions.return_value = mock_response

        result = list_executions(
            target_resource_id='12345678-1234-1234-1234-123456789012',
            target_resource_type='COMPUTATION_MODEL',
            region='us-east-1',
        )

        assert result['success'] is True
        assert len(result['executionSummaries']) == 2
        assert result['nextToken'] == 'next-token-456'
        mock_client.list_executions.assert_called_once()

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_executions.create_sitewise_client')
    def test_list_executions_with_filters(self, mock_boto_client):
        """Test executions listing with filters."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        mock_response = {
            'executionSummaries': [
                {'executionId': 'exec-1', 'actionType': 'AWS/ANOMALY_DETECTION_TRAINING'},
            ],
            'nextToken': None,
        }
        mock_client.list_executions.return_value = mock_response

        result = list_executions(
            target_resource_id='87654321-4321-4321-4321-210987654321',
            target_resource_type='ASSET',
            region='us-west-2',
            action_type='AWS/ANOMALY_DETECTION_TRAINING',
            max_results=25,
            next_token='cHJldi10b2tlbg==',
            resolve_to_resource_id='11111111-1111-1111-1111-111111111111',
            resolve_to_resource_type='ASSET',
        )

        assert result['success'] is True
        assert len(result['executionSummaries']) == 1
        assert result['nextToken'] is None
        mock_client.list_executions.assert_called_once_with(
            targetResourceId='87654321-4321-4321-4321-210987654321',
            targetResourceType='ASSET',
            actionType='AWS/ANOMALY_DETECTION_TRAINING',
            maxResults=25,
            nextToken='cHJldi10b2tlbg==',
            resolveToResourceId='11111111-1111-1111-1111-111111111111',
            resolveToResourceType='ASSET',
        )

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_executions.create_sitewise_client')
    def test_list_executions_client_error(self, mock_boto_client):
        """Test executions listing with client error."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        error_response = {
            'Error': {
                'Code': 'AccessDeniedException',
                'Message': 'Access denied',
            }
        }
        mock_client.list_executions.side_effect = ClientError(error_response, 'ListExecutions')

        result = list_executions(
            target_resource_id='12345678-1234-1234-1234-123456789012',
            target_resource_type='COMPUTATION_MODEL',
        )

        assert result['success'] is False
        assert result['error_code'] == 'AccessDeniedException'
        assert 'Access denied' in result['error']

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_executions.create_sitewise_client')
    def test_describe_execution_success(self, mock_boto_client):
        """Test successful execution description."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        mock_response = {
            'executionId': '12345678-1234-1234-1234-123456789012',
            'actionType': 'AWS/ANOMALY_DETECTION_TRAINING',
            'executionStatus': {'state': 'SUCCEEDED'},
            'executionStartTime': Mock(),
            'executionEndTime': Mock(),
            'executionDetails': {'key': 'value'},
            'executionResult': {'result': 'success'},
            'targetResource': {'computationModelId': '87654321-4321-4321-4321-210987654321'},
            'resolveTo': {'assetId': '11111111-1111-1111-1111-111111111111'},
            'executionEntityVersion': '1',
            'targetResourceVersion': '2',
        }
        mock_response['executionStartTime'].isoformat.return_value = '2023-01-01T00:00:00Z'
        mock_response['executionEndTime'].isoformat.return_value = '2023-01-01T01:00:00Z'
        mock_client.describe_execution.return_value = mock_response

        result = describe_execution(
            execution_id='12345678-1234-1234-1234-123456789012',
            region='us-east-1',
        )

        assert result['success'] is True
        assert result['executionId'] == '12345678-1234-1234-1234-123456789012'
        assert result['actionType'] == 'AWS/ANOMALY_DETECTION_TRAINING'
        assert result['executionStatus']['state'] == 'SUCCEEDED'
        assert 'executionDetails' in result
        assert 'executionResult' in result
        assert 'targetResource' in result
        assert 'resolveTo' in result
        mock_client.describe_execution.assert_called_once()

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_executions.create_sitewise_client')
    def test_describe_execution_client_error(self, mock_boto_client):
        """Test execution description with client error."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        error_response = {
            'Error': {
                'Code': 'ResourceNotFoundException',
                'Message': 'Execution not found',
            }
        }
        mock_client.describe_execution.side_effect = ClientError(
            error_response, 'DescribeExecution'
        )

        result = describe_execution(
            execution_id='12345678-1234-1234-1234-123456789012',
        )

        assert result['success'] is False
        assert result['error_code'] == 'ResourceNotFoundException'
        assert 'Execution not found' in result['error']

    # Edge case tests
    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_executions.create_sitewise_client')
    def test_list_actions_empty_response(self, mock_boto_client):
        """Test actions listing with empty response."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        mock_response = {
            'actionSummaries': [],
            'nextToken': None,
        }
        mock_client.list_actions.return_value = mock_response

        result = list_actions(
            target_resource_id='12345678-1234-1234-1234-123456789012',
            target_resource_type='COMPUTATION_MODEL',
        )

        assert result['success'] is True
        assert len(result['actionSummaries']) == 0
        assert result['nextToken'] is None

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_executions.create_sitewise_client')
    def test_list_executions_empty_response(self, mock_boto_client):
        """Test executions listing with empty response."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        mock_response = {
            'executionSummaries': [],
            'nextToken': None,
        }
        mock_client.list_executions.return_value = mock_response

        result = list_executions(
            target_resource_id='12345678-1234-1234-1234-123456789012',
            target_resource_type='COMPUTATION_MODEL',
        )

        assert result['success'] is True
        assert len(result['executionSummaries']) == 0
        assert result['nextToken'] is None

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_executions.execute_action')
    def test_execute_training_action_execute_action_failure(self, mock_execute_action):
        """Test training action when underlying execute_action fails."""
        mock_execute_action.return_value = {
            'success': False,
            'error': 'Action execution failed',
            'error_code': 'InvalidRequestException',
        }

        target_resource = {'computationModelId': '87654321-4321-4321-4321-210987654321'}

        result = execute_training_action(
            training_action_definition_id='11111111-1111-1111-1111-111111111111',
            training_mode='TRAIN_MODEL',
            target_resource=target_resource,
            export_data_start_time=1717225200,
            export_data_end_time=1722789360,
        )

        assert result['success'] is False
        assert result['error'] == 'Action execution failed'
        assert result['error_code'] == 'InvalidRequestException'
        assert 'trainingPayload' not in result

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_executions.execute_action')
    def test_execute_inference_action_execute_action_failure(self, mock_execute_action):
        """Test inference action when underlying execute_action fails."""
        mock_execute_action.return_value = {
            'success': False,
            'error': 'Action execution failed',
            'error_code': 'InvalidRequestException',
        }

        target_resource = {'computationModelId': '87654321-4321-4321-4321-210987654321'}

        result = execute_inference_action(
            inference_action_definition_id='11111111-1111-1111-1111-111111111111',
            inference_mode='START',
            target_resource=target_resource,
            data_upload_frequency='PT15M',
        )

        assert result['success'] is False
        assert result['error'] == 'Action execution failed'
        assert result['error_code'] == 'InvalidRequestException'
        assert 'inferencePayload' not in result

    def test_execute_training_action_minimal_params(self):
        """Test training action with minimal parameters for STOP_RETRAINING_SCHEDULER."""
        with patch(
            'awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_executions.execute_action'
        ) as mock_execute_action:
            mock_execute_action.return_value = {
                'success': True,
                'actionId': '12345678-1234-1234-1234-123456789012',
            }

            target_resource = {'computationModelId': '87654321-4321-4321-4321-210987654321'}

            result = execute_training_action(
                training_action_definition_id='11111111-1111-1111-1111-111111111111',
                training_mode='STOP_RETRAINING_SCHEDULER',
                target_resource=target_resource,
            )

            assert result['success'] is True
            assert 'trainingPayload' in result
            payload = result['trainingPayload']
            assert payload['trainingMode'] == 'STOP_RETRAINING_SCHEDULER'
            # Should not have any other configuration for STOP mode
            assert (
                'retrainingConfiguration' not in payload
                or payload.get('retrainingConfiguration') is None
            )

    def test_execute_inference_action_minimal_params(self):
        """Test inference action with minimal parameters for STOP mode."""
        with patch(
            'awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_executions.execute_action'
        ) as mock_execute_action:
            mock_execute_action.return_value = {
                'success': True,
                'actionId': '12345678-1234-1234-1234-123456789012',
            }

            target_resource = {'computationModelId': '87654321-4321-4321-4321-210987654321'}

            result = execute_inference_action(
                inference_action_definition_id='11111111-1111-1111-1111-111111111111',
                inference_mode='STOP',
                target_resource=target_resource,
            )

            assert result['success'] is True
            assert 'inferencePayload' in result
            payload = result['inferencePayload']
            assert payload['inferenceMode'] == 'STOP'
            # Should not have data_upload_frequency for STOP mode
            assert (
                'dataUploadFrequency' not in payload or payload.get('dataUploadFrequency') is None
            )

    # Additional tests to improve coverage
    def test_execute_action_validation_error(self):
        """Test execute_action with validation error."""
        # Test with invalid action_payload structure - should raise ValidationError
        from pydantic import ValidationError

        with pytest.raises(ValidationError) as exc_info:
            execute_action(
                action_definition_id='invalid-id',  # This will trigger validation error
                action_payload={'invalidKey': 'value'},  # Missing stringValue
                target_resource={'computationModelId': '87654321-4321-4321-4321-210987654321'},
            )

        # Verify it's a Pydantic validation error for ActionPayload
        assert 'ActionPayload' in str(exc_info.value)
        assert 'stringValue' in str(exc_info.value)
        assert 'Field required' in str(exc_info.value)

    def test_list_actions_validation_error(self):
        """Test list_actions with validation error."""
        # Test with invalid target_resource_type - should raise ValidationError
        from pydantic import ValidationError

        with pytest.raises(ValidationError) as exc_info:
            list_actions(
                target_resource_id='12345678-1234-1234-1234-123456789012',
                target_resource_type='INVALID_TYPE',  # This will trigger validation error
            )

        # Verify it's a Pydantic validation error for ListActionsRequest
        assert 'ListActionsRequest' in str(exc_info.value)
        assert 'targetResourceType' in str(exc_info.value)
        assert 'must be one of: ASSET, COMPUTATION_MODEL' in str(exc_info.value)

    def test_describe_action_validation_error(self):
        """Test describe_action with validation error."""
        # Test with invalid action_id format - should raise ValidationError
        from pydantic import ValidationError

        with pytest.raises(ValidationError) as exc_info:
            describe_action(
                action_id='invalid-id-format'  # This will trigger validation error
            )

        # Verify it's a Pydantic validation error for DescribeActionRequest
        assert 'DescribeActionRequest' in str(exc_info.value)
        assert 'actionId' in str(exc_info.value)
        assert 'must be exactly 36 characters' in str(exc_info.value)

    def test_execute_training_action_generic_exception(self):
        """Test execute_training_action with generic exception."""
        # Test with invalid training_mode to trigger generic exception
        result = execute_training_action(
            training_action_definition_id='12345678-1234-1234-1234-123456789012',
            training_mode='INVALID_MODE',  # This will trigger validation error in TrainingPayload
            target_resource={'computationModelId': '87654321-4321-4321-4321-210987654321'},
            export_data_start_time=1717225200,
            export_data_end_time=1722789360,
        )

        # Verify it returns an error response
        assert result['success'] is False
        assert result['error_code'] == 'InternalError'
        assert 'Error creating training payload' in result['error']

    def test_execute_inference_action_generic_exception(self):
        """Test execute_inference_action with generic exception."""
        # Test with invalid inference_mode to trigger generic exception
        result = execute_inference_action(
            inference_action_definition_id='12345678-1234-1234-1234-123456789012',
            inference_mode='INVALID_MODE',  # This will trigger validation error in InferencePayload
            target_resource={'computationModelId': '87654321-4321-4321-4321-210987654321'},
            data_upload_frequency='PT15M',
        )

        # Verify it returns an error response
        assert result['success'] is False
        assert result['error_code'] == 'InternalError'
        assert 'Error creating inference payload' in result['error']

    def test_execute_training_action_partial_label_config_only_prefix(self):
        """Test training action with only label_s3_prefix provided (missing bucket)."""
        target_resource = {'computationModelId': '87654321-4321-4321-4321-210987654321'}

        result = execute_training_action(
            training_action_definition_id='11111111-1111-1111-1111-111111111111',
            training_mode='TRAIN_MODEL',
            target_resource=target_resource,
            export_data_start_time=1717225200,
            export_data_end_time=1722789360,
            label_s3_prefix='Labels/model-id/Labels.csv',  # Missing label_bucket_name
        )

        assert result['success'] is False
        assert result['error_code'] == 'ValidationException'
        assert (
            'Both label_bucket_name and label_s3_prefix must be provided together'
            in result['error']
        )

    def test_execute_training_action_partial_evaluation_config_only_start_time(self):
        """Test training action with only evaluation_start_time provided (missing other evaluation params)."""
        target_resource = {'computationModelId': '87654321-4321-4321-4321-210987654321'}

        result = execute_training_action(
            training_action_definition_id='11111111-1111-1111-1111-111111111111',
            training_mode='TRAIN_MODEL',
            target_resource=target_resource,
            export_data_start_time=1717225200,
            export_data_end_time=1722789360,
            evaluation_start_time=1719817200,  # Missing other evaluation params
        )

        assert result['success'] is False
        assert result['error_code'] == 'ValidationException'
        assert 'All four evaluation parameters' in result['error']

    def test_execute_training_action_partial_metrics_config_only_prefix(self):
        """Test training action with only metrics_s3_prefix provided (missing bucket)."""
        target_resource = {'computationModelId': '87654321-4321-4321-4321-210987654321'}

        result = execute_training_action(
            training_action_definition_id='11111111-1111-1111-1111-111111111111',
            training_mode='TRAIN_MODEL',
            target_resource=target_resource,
            export_data_start_time=1717225200,
            export_data_end_time=1722789360,
            metrics_s3_prefix='ModelMetrics/model-id/',  # Missing metrics_bucket_name
        )

        assert result['success'] is False
        assert result['error_code'] == 'ValidationException'
        assert (
            'Both metrics_bucket_name and metrics_s3_prefix must be provided together'
            in result['error']
        )

    def test_list_executions_validation_exception_handling(self):
        """Test list_executions CustomValidationError handling."""
        # This will trigger a CustomValidationError due to invalid target_resource_type
        # but we need to test the CustomValidationError path in the function
        from awslabs.aws_iot_sitewise_mcp_server.validation import (
            ValidationError as CustomValidationError,
        )

        with patch(
            'awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_executions.ListExecutionsRequest'
        ) as mock_request:
            mock_request.side_effect = CustomValidationError('Test validation error')

            result = list_executions(
                target_resource_id='12345678-1234-1234-1234-123456789012',
                target_resource_type='COMPUTATION_MODEL',
            )

            assert result['success'] is False
            assert result['error_code'] == 'ValidationException'
            assert 'Validation error: Test validation error' in result['error']

    def test_describe_execution_validation_exception_handling(self):
        """Test describe_execution CustomValidationError handling."""
        # This will trigger a CustomValidationError
        from awslabs.aws_iot_sitewise_mcp_server.validation import (
            ValidationError as CustomValidationError,
        )

        with patch(
            'awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_executions.DescribeExecutionRequest'
        ) as mock_request:
            mock_request.side_effect = CustomValidationError('Test validation error')

            result = describe_execution(execution_id='12345678-1234-1234-1234-123456789012')

            assert result['success'] is False
            assert result['error_code'] == 'ValidationException'
            assert 'Validation error: Test validation error' in result['error']

    def test_list_executions_validation_error(self):
        """Test list_executions with validation error."""
        # Test with invalid target_resource_type - should raise ValidationError
        from pydantic import ValidationError

        with pytest.raises(ValidationError) as exc_info:
            list_executions(
                target_resource_id='12345678-1234-1234-1234-123456789012',
                target_resource_type='INVALID_TYPE',  # This will trigger validation error
            )

        # Verify it's a Pydantic validation error for ListExecutionsRequest
        assert 'ListExecutionsRequest' in str(exc_info.value)
        assert 'targetResourceType' in str(exc_info.value)
        assert 'must be one of: ASSET, COMPUTATION_MODEL' in str(exc_info.value)

    def test_describe_execution_validation_error(self):
        """Test describe_execution with validation error."""
        # Test with invalid execution_id format - should raise ValidationError
        from pydantic import ValidationError

        with pytest.raises(ValidationError) as exc_info:
            describe_execution(
                execution_id='invalid-id-format'  # This will trigger validation error
            )

        # Verify it's a Pydantic validation error for DescribeExecutionRequest
        assert 'DescribeExecutionRequest' in str(exc_info.value)
        assert 'executionId' in str(exc_info.value)
        assert 'must be exactly 36 characters' in str(exc_info.value)

    def test_execute_action_custom_validation_error(self):
        """Test execute_action CustomValidationError handling (line 123)."""
        from awslabs.aws_iot_sitewise_mcp_server.validation import (
            ValidationError as CustomValidationError,
        )

        with patch(
            'awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_executions.ExecuteActionRequest'
        ) as mock_request:
            mock_request.side_effect = CustomValidationError('Test validation error')

            result = execute_action(
                action_definition_id='12345678-1234-1234-1234-123456789012',
                action_payload={'stringValue': '{"key": "value"}'},
                target_resource={'computationModelId': '87654321-4321-4321-4321-210987654321'},
            )

            assert result['success'] is False
            assert result['error_code'] == 'ValidationException'
            assert 'Validation error: Test validation error' in result['error']

    def test_list_actions_custom_validation_error(self):
        """Test list_actions CustomValidationError handling (line 219)."""
        from awslabs.aws_iot_sitewise_mcp_server.validation import (
            ValidationError as CustomValidationError,
        )

        with patch(
            'awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_executions.ListActionsRequest'
        ) as mock_request:
            mock_request.side_effect = CustomValidationError('Test validation error')

            result = list_actions(
                target_resource_id='12345678-1234-1234-1234-123456789012',
                target_resource_type='COMPUTATION_MODEL',
            )

            assert result['success'] is False
            assert result['error_code'] == 'ValidationException'
            assert 'Validation error: Test validation error' in result['error']

    def test_describe_action_custom_validation_error(self):
        """Test describe_action CustomValidationError handling (line 287)."""
        from awslabs.aws_iot_sitewise_mcp_server.validation import (
            ValidationError as CustomValidationError,
        )

        with patch(
            'awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_executions.DescribeActionRequest'
        ) as mock_request:
            mock_request.side_effect = CustomValidationError('Test validation error')

            result = describe_action(action_id='12345678-1234-1234-1234-123456789012')

            assert result['success'] is False
            assert result['error_code'] == 'ValidationException'
            assert 'Validation error: Test validation error' in result['error']

    def test_execute_inference_action_custom_validation_error(self):
        """Test execute_inference_action CustomValidationError handling (line 622)."""
        from awslabs.aws_iot_sitewise_mcp_server.validation import (
            ValidationError as CustomValidationError,
        )

        with patch(
            'awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_executions.InferencePayload'
        ) as mock_payload:
            mock_payload.side_effect = CustomValidationError('Test validation error')

            result = execute_inference_action(
                inference_action_definition_id='12345678-1234-1234-1234-123456789012',
                inference_mode='START',
                target_resource={'computationModelId': '87654321-4321-4321-4321-210987654321'},
                data_upload_frequency='PT15M',
            )

            assert result['success'] is False
            assert result['error_code'] == 'ValidationException'
            assert 'Validation error: Test validation error' in result['error']

    # Tests for new validation logic that replaced assert statements
    def test_execute_training_action_evaluation_params_internal_error(self):
        """Test training action internal error when evaluation parameters are unexpectedly None."""
        # This test covers the edge case where the all() check passes but individual parameters are None
        # This is a defensive programming scenario that should theoretically never happen
        # but we test it to ensure the error handling works correctly

        target_resource = {'computationModelId': '87654321-4321-4321-4321-210987654321'}

        # Test the case where we provide some evaluation parameters but not all
        # This should trigger the validation error before reaching the internal error
        result = execute_training_action(
            training_action_definition_id='11111111-1111-1111-1111-111111111111',
            training_mode='TRAIN_MODEL',
            target_resource=target_resource,
            export_data_start_time=1717225200,
            export_data_end_time=1722789360,
            evaluation_start_time=1719817200,  # Provided
            evaluation_end_time=1720422000,  # Provided
            evaluation_bucket_name=None,  # Missing - should trigger validation error
            evaluation_s3_prefix=None,  # Missing - should trigger validation error
        )

        assert result['success'] is False
        assert result['error_code'] == 'ValidationException'
        assert 'All four evaluation parameters' in result['error']

    def test_execute_training_action_missing_lookback_window_for_retraining(self):
        """Test training action validation error when lookback_window is missing for START_RETRAINING_SCHEDULER."""
        target_resource = {'computationModelId': '87654321-4321-4321-4321-210987654321'}

        result = execute_training_action(
            training_action_definition_id='11111111-1111-1111-1111-111111111111',
            training_mode='START_RETRAINING_SCHEDULER',
            target_resource=target_resource,
            # Missing lookback_window - should trigger validation error
            retraining_frequency='P30D',
        )

        assert result['success'] is False
        assert result['error_code'] == 'ValidationException'
        assert 'lookback_window is required for START_RETRAINING_SCHEDULER mode' in result['error']

    def test_execute_training_action_missing_retraining_frequency_for_retraining(self):
        """Test training action validation error when retraining_frequency is missing for START_RETRAINING_SCHEDULER."""
        target_resource = {'computationModelId': '87654321-4321-4321-4321-210987654321'}

        result = execute_training_action(
            training_action_definition_id='11111111-1111-1111-1111-111111111111',
            training_mode='START_RETRAINING_SCHEDULER',
            target_resource=target_resource,
            lookback_window='P360D',
            # Missing retraining_frequency - should trigger validation error
        )

        assert result['success'] is False
        assert result['error_code'] == 'ValidationException'
        assert (
            'retraining_frequency is required for START_RETRAINING_SCHEDULER mode'
            in result['error']
        )

    def test_execute_training_action_missing_both_retraining_params(self):
        """Test training action validation error when both retraining params are missing for START_RETRAINING_SCHEDULER."""
        target_resource = {'computationModelId': '87654321-4321-4321-4321-210987654321'}

        result = execute_training_action(
            training_action_definition_id='11111111-1111-1111-1111-111111111111',
            training_mode='START_RETRAINING_SCHEDULER',
            target_resource=target_resource,
            # Missing both lookback_window and retraining_frequency
        )

        assert result['success'] is False
        assert result['error_code'] == 'ValidationException'
        # Should catch the first missing parameter (lookback_window)
        assert 'lookback_window is required for START_RETRAINING_SCHEDULER mode' in result['error']

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_executions.execute_action')
    def test_execute_training_action_retraining_scheduler_with_valid_params(
        self, mock_execute_action
    ):
        """Test training action START_RETRAINING_SCHEDULER mode with valid parameters passes validation."""
        mock_execute_action.return_value = {
            'success': True,
            'actionId': '12345678-1234-1234-1234-123456789012',
        }

        target_resource = {'computationModelId': '87654321-4321-4321-4321-210987654321'}

        result = execute_training_action(
            training_action_definition_id='11111111-1111-1111-1111-111111111111',
            training_mode='START_RETRAINING_SCHEDULER',
            target_resource=target_resource,
            lookback_window='P360D',  # Valid parameter
            retraining_frequency='P30D',  # Valid parameter
            promotion='SERVICE_MANAGED',
            retraining_start_date=1730332800,
        )

        assert result['success'] is True
        assert result['actionId'] == '12345678-1234-1234-1234-123456789012'
        assert 'trainingPayload' in result
        payload = result['trainingPayload']
        assert payload['trainingMode'] == 'START_RETRAINING_SCHEDULER'
        assert 'retrainingConfiguration' in payload
        assert payload['retrainingConfiguration']['lookbackWindow'] == 'P360D'
        assert payload['retrainingConfiguration']['retrainingFrequency'] == 'P30D'

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_executions.execute_action')
    def test_execute_training_action_evaluation_config_all_params_valid(self, mock_execute_action):
        """Test training action with all evaluation parameters provided passes validation."""
        mock_execute_action.return_value = {
            'success': True,
            'actionId': '12345678-1234-1234-1234-123456789012',
        }

        target_resource = {'computationModelId': '87654321-4321-4321-4321-210987654321'}

        result = execute_training_action(
            training_action_definition_id='11111111-1111-1111-1111-111111111111',
            training_mode='TRAIN_MODEL',
            target_resource=target_resource,
            export_data_start_time=1717225200,
            export_data_end_time=1722789360,
            # All evaluation parameters provided - should pass validation
            evaluation_start_time=1719817200,
            evaluation_end_time=1720422000,
            evaluation_bucket_name='eval-bucket',
            evaluation_s3_prefix='eval-prefix/',
        )

        assert result['success'] is True
        assert result['actionId'] == '12345678-1234-1234-1234-123456789012'
        assert 'trainingPayload' in result
        payload = result['trainingPayload']
        assert 'modelEvaluationConfiguration' in payload
        assert payload['modelEvaluationConfiguration']['dataStartTime'] == 1719817200
        assert payload['modelEvaluationConfiguration']['dataEndTime'] == 1720422000
        assert (
            payload['modelEvaluationConfiguration']['resultDestination']['bucketName']
            == 'eval-bucket'
        )
        assert (
            payload['modelEvaluationConfiguration']['resultDestination']['prefix']
            == 'eval-prefix/'
        )

    def test_execute_training_action_evaluation_config_partial_params_combinations(self):
        """Test training action with various partial evaluation parameter combinations."""
        target_resource = {'computationModelId': '87654321-4321-4321-4321-210987654321'}

        # Test with only start_time and end_time (missing bucket params)
        result = execute_training_action(
            training_action_definition_id='11111111-1111-1111-1111-111111111111',
            training_mode='TRAIN_MODEL',
            target_resource=target_resource,
            export_data_start_time=1717225200,
            export_data_end_time=1722789360,
            evaluation_start_time=1719817200,
            evaluation_end_time=1720422000,
            # Missing evaluation_bucket_name and evaluation_s3_prefix
        )

        assert result['success'] is False
        assert result['error_code'] == 'ValidationException'
        assert 'All four evaluation parameters' in result['error']

        # Test with only bucket params (missing time params)
        result = execute_training_action(
            training_action_definition_id='11111111-1111-1111-1111-111111111111',
            training_mode='TRAIN_MODEL',
            target_resource=target_resource,
            export_data_start_time=1717225200,
            export_data_end_time=1722789360,
            evaluation_bucket_name='eval-bucket',
            evaluation_s3_prefix='eval-prefix/',
            # Missing evaluation_start_time and evaluation_end_time
        )

        assert result['success'] is False
        assert result['error_code'] == 'ValidationException'
        assert 'All four evaluation parameters' in result['error']

        # Test with three out of four params
        result = execute_training_action(
            training_action_definition_id='11111111-1111-1111-1111-111111111111',
            training_mode='TRAIN_MODEL',
            target_resource=target_resource,
            export_data_start_time=1717225200,
            export_data_end_time=1722789360,
            evaluation_start_time=1719817200,
            evaluation_end_time=1720422000,
            evaluation_bucket_name='eval-bucket',
            # Missing evaluation_s3_prefix
        )

        assert result['success'] is False
        assert result['error_code'] == 'ValidationException'
        assert 'All four evaluation parameters' in result['error']
