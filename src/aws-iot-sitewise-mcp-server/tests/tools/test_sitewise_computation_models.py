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

"""Tests for AWS IoT SiteWise Computation Models Tools."""

import os
import pytest
import sys
from awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_computation_models import (
    _determine_computation_model_configuration_type,
    create_anomaly_detection_model,
    create_computation_model,
    delete_computation_model,
    describe_computation_model,
    describe_computation_model_execution_summary,
    list_computation_model_data_binding_usages,
    list_computation_model_resolve_to_resources,
    list_computation_models,
    update_computation_model,
)
from botocore.exceptions import ClientError
from unittest.mock import Mock, patch


# Add the project root directory and its parent to Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(script_dir)
sys.path.insert(0, project_dir)
sys.path.insert(0, os.path.dirname(project_dir))
sys.path.insert(0, os.path.dirname(os.path.dirname(project_dir)))


class TestSiteWiseComputationModels:
    """Test cases for SiteWise computation models tools."""

    @patch(
        'awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_computation_models.create_sitewise_client'
    )
    def test_create_computation_model_success(self, mock_boto_client):
        """Test successful computation model creation."""
        # Mock the boto3 client
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        # Mock the response
        mock_response = {
            'computationModelId': '12345678-1234-1234-1234-123456789012',
            'computationModelArn': 'arn:aws:iotsitewise:us-east-1:123456789012:computation-model/12345678-1234-1234-1234-123456789012',
            'computationModelStatus': {'state': 'CREATING'},
        }
        mock_client.create_computation_model.return_value = mock_response

        # Test data
        computation_model_configuration = {
            'anomalyDetection': {
                'inputProperties': '${input_properties}',
                'resultProperty': '${result_property}',
            }
        }
        computation_model_data_binding = {
            'input_properties': {
                'list': [
                    {
                        'assetProperty': {
                            'assetId': '87654321-4321-4321-4321-210987654321',
                            'propertyId': '11111111-1111-1111-1111-111111111111',
                        }
                    }
                ]
            },
            'result_property': {
                'assetProperty': {
                    'assetId': '87654321-4321-4321-4321-210987654321',
                    'propertyId': '22222222-2222-2222-2222-222222222222',
                }
            },
        }

        # Call the function
        result = create_computation_model(
            computation_model_name='Test Computation Model',
            computation_model_configuration=computation_model_configuration,
            computation_model_data_binding=computation_model_data_binding,
            region='us-east-1',
        )

        # Verify the result
        assert result['success'] is True
        assert result['computationModelId'] == '12345678-1234-1234-1234-123456789012'
        assert 'computationModelArn' in result
        assert result['computationModelStatus']['state'] == 'CREATING'

        # Verify the client was called
        mock_client.create_computation_model.assert_called_once()

    @patch(
        'awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_computation_models.create_sitewise_client'
    )
    def test_create_computation_model_with_all_params(self, mock_boto_client):
        """Test computation model creation with all optional parameters."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        mock_response = {
            'computationModelId': '87654321-4321-4321-4321-210987654321',
            'computationModelArn': 'arn:aws:iotsitewise:us-east-1:123456789012:computation-model/87654321-4321-4321-4321-210987654321',
            'computationModelStatus': {'state': 'CREATING'},
        }
        mock_client.create_computation_model.return_value = mock_response

        computation_model_configuration = {
            'anomalyDetection': {
                'inputProperties': '${input_properties}',
                'resultProperty': '${result_property}',
            }
        }
        computation_model_data_binding = {
            'input_properties': {
                'list': [
                    {
                        'assetModelProperty': {
                            'assetModelId': '12345678-1234-1234-1234-123456789012',
                            'propertyId': '11111111-1111-1111-1111-111111111111',
                        }
                    }
                ]
            },
            'result_property': {
                'assetModelProperty': {
                    'assetModelId': '12345678-1234-1234-1234-123456789012',
                    'propertyId': '22222222-2222-2222-2222-222222222222',
                }
            },
        }

        result = create_computation_model(
            computation_model_name='Test Model with All Params',
            computation_model_configuration=computation_model_configuration,
            computation_model_data_binding=computation_model_data_binding,
            region='us-west-2',
            computation_model_description='Test description',
            client_token='12345678-1234-1234-1234-123456789012',
            tags={'Environment': 'Test', 'Type': 'AnomalyDetection'},
        )

        assert result['success'] is True
        mock_client.create_computation_model.assert_called_once()

    @patch(
        'awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_computation_models.create_sitewise_client'
    )
    def test_create_computation_model_client_error(self, mock_boto_client):
        """Test computation model creation with client error."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        error_response = {
            'Error': {
                'Code': 'InvalidRequestException',
                'Message': 'Invalid computation model configuration',
            }
        }
        mock_client.create_computation_model.side_effect = ClientError(
            error_response, 'CreateComputationModel'
        )

        computation_model_configuration = {
            'anomalyDetection': {
                'inputProperties': '${input_properties}',
                'resultProperty': '${result_property}',
            }
        }
        computation_model_data_binding = {
            'input_properties': {
                'list': [
                    {
                        'assetProperty': {
                            'assetId': '87654321-4321-4321-4321-210987654321',
                            'propertyId': '11111111-1111-1111-1111-111111111111',
                        }
                    }
                ]
            },
            'result_property': {
                'assetProperty': {
                    'assetId': '87654321-4321-4321-4321-210987654321',
                    'propertyId': '22222222-2222-2222-2222-222222222222',
                }
            },
        }

        result = create_computation_model(
            computation_model_name='Test Model',
            computation_model_configuration=computation_model_configuration,
            computation_model_data_binding=computation_model_data_binding,
        )

        assert result['success'] is False
        assert result['error_code'] == 'InvalidRequestException'
        assert 'Invalid computation model configuration' in result['error']

    def test_create_anomaly_detection_model_success(self):
        """Test successful anomaly detection model creation."""
        with patch(
            'awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_computation_models.create_computation_model'
        ) as mock_create:
            mock_create.return_value = {
                'success': True,
                'computationModelId': '12345678-1234-1234-1234-123456789012',
                'computationModelArn': 'arn:aws:iotsitewise:us-east-1:123456789012:computation-model/12345678-1234-1234-1234-123456789012',
                'computationModelStatus': {'state': 'CREATING'},
            }

            input_properties = [
                {
                    'assetProperty': {
                        'assetId': '87654321-4321-4321-4321-210987654321',
                        'propertyId': '11111111-1111-1111-1111-111111111111',
                    }
                },
                {
                    'assetProperty': {
                        'assetId': '87654321-4321-4321-4321-210987654321',
                        'propertyId': '22222222-2222-2222-2222-222222222222',
                    }
                },
            ]
            result_property = {
                'assetProperty': {
                    'assetId': '87654321-4321-4321-4321-210987654321',
                    'propertyId': '33333333-3333-3333-3333-333333333333',
                }
            }

            result = create_anomaly_detection_model(
                computation_model_name='Test Anomaly Detection',
                input_properties=input_properties,
                result_property=result_property,
                region='us-east-1',
                computation_model_description='Test anomaly detection model',
                tags={'Type': 'AnomalyDetection'},
            )

            assert result['success'] is True
            assert result['computationModelId'] == '12345678-1234-1234-1234-123456789012'

            # Verify the underlying create_computation_model was called with correct parameters
            mock_create.assert_called_once()
            call_args = mock_create.call_args
            assert call_args[1]['computation_model_name'] == 'Test Anomaly Detection'
            assert 'anomalyDetection' in call_args[1]['computation_model_configuration']
            assert 'input_properties' in call_args[1]['computation_model_data_binding']
            assert 'result_property' in call_args[1]['computation_model_data_binding']

    @patch(
        'awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_computation_models.create_sitewise_client'
    )
    def test_delete_computation_model_success(self, mock_boto_client):
        """Test successful computation model deletion."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        mock_response = {'computationModelStatus': {'state': 'DELETING'}}
        mock_client.delete_computation_model.return_value = mock_response

        result = delete_computation_model(
            computation_model_id='12345678-1234-1234-1234-123456789012',
            region='us-east-1',
        )

        assert result['success'] is True
        assert result['computationModelStatus']['state'] == 'DELETING'
        mock_client.delete_computation_model.assert_called_once()

    @patch(
        'awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_computation_models.create_sitewise_client'
    )
    def test_delete_computation_model_with_client_token(self, mock_boto_client):
        """Test computation model deletion with client token."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        mock_response = {'computationModelStatus': {'state': 'DELETING'}}
        mock_client.delete_computation_model.return_value = mock_response

        result = delete_computation_model(
            computation_model_id='87654321-4321-4321-4321-210987654321',
            region='us-west-2',
            client_token='12345678-1234-1234-1234-123456789012',
        )

        assert result['success'] is True
        mock_client.delete_computation_model.assert_called_once()

    @patch(
        'awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_computation_models.create_sitewise_client'
    )
    def test_update_computation_model_success(self, mock_boto_client):
        """Test successful computation model update."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        mock_response = {'computationModelStatus': {'state': 'UPDATING'}}
        mock_client.update_computation_model.return_value = mock_response

        computation_model_configuration = {
            'anomalyDetection': {
                'inputProperties': '${input_properties}',
                'resultProperty': '${result_property}',
            }
        }
        computation_model_data_binding = {
            'input_properties': {
                'list': [
                    {
                        'assetProperty': {
                            'assetId': '87654321-4321-4321-4321-210987654321',
                            'propertyId': '11111111-1111-1111-1111-111111111111',
                        }
                    }
                ]
            },
            'result_property': {
                'assetProperty': {
                    'assetId': '87654321-4321-4321-4321-210987654321',
                    'propertyId': '22222222-2222-2222-2222-222222222222',
                }
            },
        }

        result = update_computation_model(
            computation_model_id='12345678-1234-1234-1234-123456789012',
            computation_model_name='Updated Model',
            computation_model_configuration=computation_model_configuration,
            computation_model_data_binding=computation_model_data_binding,
            region='us-east-1',
        )

        assert result['success'] is True
        assert result['computationModelStatus']['state'] == 'UPDATING'
        mock_client.update_computation_model.assert_called_once()

    @patch(
        'awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_computation_models.create_sitewise_client'
    )
    def test_list_computation_models_success(self, mock_boto_client):
        """Test successful computation models listing."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        mock_response = {
            'computationModelSummaries': [
                {'computationModelId': 'model-1', 'computationModelName': 'Model 1'},
                {'computationModelId': 'model-2', 'computationModelName': 'Model 2'},
            ],
            'nextToken': 'next-token-123',
        }
        mock_client.list_computation_models.return_value = mock_response

        result = list_computation_models(region='us-east-1')

        assert result['success'] is True
        assert len(result['computationModelSummaries']) == 2
        assert result['nextToken'] == 'next-token-123'
        mock_client.list_computation_models.assert_called_once()

    @patch(
        'awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_computation_models.create_sitewise_client'
    )
    def test_list_computation_models_with_filters(self, mock_boto_client):
        """Test computation models listing with filters."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        mock_response = {
            'computationModelSummaries': [
                {'computationModelId': 'model-1', 'computationModelName': 'Anomaly Model 1'},
            ],
            'nextToken': None,
        }
        mock_client.list_computation_models.return_value = mock_response

        result = list_computation_models(
            region='us-west-2',
            computation_model_type='ANOMALY_DETECTION',
            max_results=50,
            next_token='cHJldi10b2tlbg==',
        )

        assert result['success'] is True
        assert len(result['computationModelSummaries']) == 1
        mock_client.list_computation_models.assert_called_once_with(
            computationModelType='ANOMALY_DETECTION',
            maxResults=50,
            nextToken='cHJldi10b2tlbg==',
        )

    @patch(
        'awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_computation_models.create_sitewise_client'
    )
    def test_describe_computation_model_success(self, mock_boto_client):
        """Test successful computation model description."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        mock_response = {
            'computationModelId': '12345678-1234-1234-1234-123456789012',
            'computationModelArn': 'arn:aws:iotsitewise:us-east-1:123456789012:computation-model/12345678-1234-1234-1234-123456789012',
            'computationModelName': 'Test Model',
            'computationModelDescription': 'Test description',
            'computationModelConfiguration': {
                'anomalyDetection': {
                    'inputProperties': '${input_properties}',
                    'resultProperty': '${result_property}',
                }
            },
            'computationModelDataBinding': {
                'input_properties': {
                    'list': [
                        {
                            'assetProperty': {
                                'assetId': '87654321-4321-4321-4321-210987654321',
                                'propertyId': '11111111-1111-1111-1111-111111111111',
                            }
                        }
                    ]
                },
                'result_property': {
                    'assetProperty': {
                        'assetId': '87654321-4321-4321-4321-210987654321',
                        'propertyId': '22222222-2222-2222-2222-222222222222',
                    }
                },
            },
            'computationModelStatus': {'state': 'ACTIVE'},
            'computationModelVersion': '1',
            'computationModelCreationDate': Mock(),
            'computationModelLastUpdateDate': Mock(),
            'actionDefinitions': [],
        }
        mock_response[
            'computationModelCreationDate'
        ].isoformat.return_value = '2023-01-01T00:00:00Z'
        mock_response[
            'computationModelLastUpdateDate'
        ].isoformat.return_value = '2023-01-01T00:00:00Z'
        mock_client.describe_computation_model.return_value = mock_response

        result = describe_computation_model(
            computation_model_id='12345678-1234-1234-1234-123456789012',
            region='us-east-1',
        )

        assert result['success'] is True
        assert result['computationModelId'] == '12345678-1234-1234-1234-123456789012'
        assert result['computationModelName'] == 'Test Model'
        assert result['computationModelStatus']['state'] == 'ACTIVE'
        mock_client.describe_computation_model.assert_called_once()

    @patch(
        'awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_computation_models.create_sitewise_client'
    )
    def test_list_computation_model_resolve_to_resources_success(self, mock_boto_client):
        """Test successful resolve to resources listing."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        mock_response = {
            'computationModelResolveToResourceSummaries': [
                {'resourceId': 'asset-1', 'resourceType': 'ASSET'},
                {'resourceId': 'asset-2', 'resourceType': 'ASSET'},
            ],
            'nextToken': 'next-token-456',
        }
        mock_client.list_computation_model_resolve_to_resources.return_value = mock_response

        result = list_computation_model_resolve_to_resources(
            computation_model_id='12345678-1234-1234-1234-123456789012',
            region='us-east-1',
        )

        assert result['success'] is True
        assert len(result['computationModelResolveToResourceSummaries']) == 2
        assert result['nextToken'] == 'next-token-456'

        mock_client.list_computation_model_resolve_to_resources.assert_called_once_with(
            computationModelId='12345678-1234-1234-1234-123456789012'
        )

    def test_determine_computation_model_configuration_type_with_hint(self):
        """Test configuration type determination with user-provided hint."""
        # Test asset model level hint
        result = _determine_computation_model_configuration_type(
            computation_model_id='12345678-1234-1234-1234-123456789012',
            region='us-east-1',
            configuration_type='asset_model_level',
        )
        assert result['success'] is True
        assert result['is_asset_model_level'] is True
        assert result['configuration_type'] == 'Asset Model Level Configuration'

        # Test asset level hint
        result = _determine_computation_model_configuration_type(
            computation_model_id='12345678-1234-1234-1234-123456789012',
            region='us-east-1',
            configuration_type='asset_level',
        )
        assert result['success'] is True
        assert result['is_asset_model_level'] is False
        assert result['configuration_type'] == 'Asset Level Configuration'

    @patch(
        'awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_computation_models.describe_computation_model'
    )
    def test_determine_computation_model_configuration_type_auto_detect_asset_model(
        self, mock_describe
    ):
        """Test configuration type auto-detection for asset model level."""
        mock_describe.return_value = {
            'success': True,
            'computationModelDataBinding': {
                'input_properties': {
                    'list': [
                        {
                            'assetModelProperty': {
                                'assetModelId': '12345678-1234-1234-1234-123456789012',
                                'propertyId': '11111111-1111-1111-1111-111111111111',
                            }
                        }
                    ]
                },
                'result_property': {
                    'assetModelProperty': {
                        'assetModelId': '12345678-1234-1234-1234-123456789012',
                        'propertyId': '22222222-2222-2222-2222-222222222222',
                    }
                },
            },
        }

        result = _determine_computation_model_configuration_type(
            computation_model_id='12345678-1234-1234-1234-123456789012',
            region='us-east-1',
        )

        assert result['success'] is True
        assert result['is_asset_model_level'] is True
        assert result['configuration_type'] == 'Asset Model Level Configuration'

    @patch(
        'awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_computation_models.describe_computation_model'
    )
    def test_determine_computation_model_configuration_type_auto_detect_asset_level(
        self, mock_describe
    ):
        """Test configuration type auto-detection for asset level."""
        mock_describe.return_value = {
            'success': True,
            'computationModelDataBinding': {
                'input_properties': {
                    'list': [
                        {
                            'assetProperty': {
                                'assetId': '87654321-4321-4321-4321-210987654321',
                                'propertyId': '11111111-1111-1111-1111-111111111111',
                            }
                        }
                    ]
                },
                'result_property': {
                    'assetProperty': {
                        'assetId': '87654321-4321-4321-4321-210987654321',
                        'propertyId': '22222222-2222-2222-2222-222222222222',
                    }
                },
            },
        }

        result = _determine_computation_model_configuration_type(
            computation_model_id='12345678-1234-1234-1234-123456789012',
            region='us-east-1',
        )

        assert result['success'] is True
        assert result['is_asset_model_level'] is False
        assert result['configuration_type'] == 'Asset Level Configuration'

    @patch(
        'awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_computation_models._determine_computation_model_configuration_type'
    )
    @patch(
        'awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_computation_models.create_sitewise_client'
    )
    def test_describe_computation_model_execution_summary_asset_model_level(
        self, mock_boto_client, mock_determine_type
    ):
        """Test execution summary for asset model level configuration."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        mock_determine_type.return_value = {
            'success': True,
            'is_asset_model_level': True,
            'configuration_type': 'Asset Model Level Configuration',
        }

        mock_response = {
            'computationModelId': '12345678-1234-1234-1234-123456789012',
            'computationModelExecutionSummary': {'status': 'ACTIVE'},
            'resolveTo': {
                'resourceId': '87654321-4321-4321-4321-210987654321',
                'resourceType': 'ASSET',
            },
        }
        mock_client.describe_computation_model_execution_summary.return_value = mock_response

        result = describe_computation_model_execution_summary(
            computation_model_id='12345678-1234-1234-1234-123456789012',
            region='us-east-1',
            resolve_to_resource_id='87654321-4321-4321-4321-210987654321',
            resolve_to_resource_type='ASSET',
        )

        assert result['success'] is True
        assert result['configurationType'] == 'Asset Model Level Configuration'
        assert 'resolveTo' in result
        mock_client.describe_computation_model_execution_summary.assert_called_once()

    @patch(
        'awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_computation_models._determine_computation_model_configuration_type'
    )
    @patch(
        'awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_computation_models.create_sitewise_client'
    )
    def test_describe_computation_model_execution_summary_asset_level(
        self, mock_boto_client, mock_determine_type
    ):
        """Test execution summary for asset level configuration."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        mock_determine_type.return_value = {
            'success': True,
            'is_asset_model_level': False,
            'configuration_type': 'Asset Level Configuration',
        }

        mock_response = {
            'computationModelId': '12345678-1234-1234-1234-123456789012',
            'computationModelExecutionSummary': {'status': 'ACTIVE'},
        }
        mock_client.describe_computation_model_execution_summary.return_value = mock_response

        result = describe_computation_model_execution_summary(
            computation_model_id='12345678-1234-1234-1234-123456789012',
            region='us-east-1',
            resolve_to_resource_id='87654321-4321-4321-4321-210987654321',  # Should be ignored
            resolve_to_resource_type='ASSET',  # Should be ignored
        )

        assert result['success'] is True
        assert result['configurationType'] == 'Asset Level Configuration'
        assert 'info' in result
        assert 'ignored' in result['info']

    @patch(
        'awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_computation_models.create_sitewise_client'
    )
    def test_list_computation_model_data_binding_usages_success(self, mock_boto_client):
        """Test successful data binding usages listing."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        mock_response = {
            'computationModelSummaries': [
                {'computationModelId': 'model-1', 'computationModelName': 'Model 1'},
            ],
            'nextToken': 'next-token-123',
        }
        mock_client.list_computation_model_data_binding_usages.return_value = mock_response

        data_binding_value_filter = {'asset': {'assetId': '12345678-1234-1234-1234-123456789012'}}

        result = list_computation_model_data_binding_usages(
            data_binding_value_filter=data_binding_value_filter,
            region='us-east-1',
        )

        assert result['success'] is True
        assert len(result['computationModelSummaries']) == 1
        assert result['nextToken'] == 'next-token-123'
        mock_client.list_computation_model_data_binding_usages.assert_called_once()

    @patch(
        'awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_computation_models.create_sitewise_client'
    )
    def test_list_computation_model_data_binding_usages_with_pagination(self, mock_boto_client):
        """Test data binding usages listing with pagination."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        mock_response = {
            'computationModelSummaries': [
                {'computationModelId': 'model-1', 'computationModelName': 'Model 1'},
                {'computationModelId': 'model-2', 'computationModelName': 'Model 2'},
            ],
            'nextToken': None,
        }
        mock_client.list_computation_model_data_binding_usages.return_value = mock_response

        data_binding_value_filter = {
            'assetProperty': {
                'assetId': '12345678-1234-1234-1234-123456789012',
                'propertyId': '87654321-4321-4321-4321-210987654321',
            }
        }

        result = list_computation_model_data_binding_usages(
            data_binding_value_filter=data_binding_value_filter,
            region='us-west-2',
            max_results=50,
            next_token='cHJldi10b2tlbg==',
        )

        assert result['success'] is True
        assert len(result['computationModelSummaries']) == 2
        assert result['nextToken'] is None
        mock_client.list_computation_model_data_binding_usages.assert_called_once_with(
            dataBindingValueFilter=data_binding_value_filter,
            maxResults=50,
            nextToken='cHJldi10b2tlbg==',
        )

    @patch(
        'awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_computation_models.create_sitewise_client'
    )
    def test_list_computation_model_resolve_to_resources_with_filters(self, mock_boto_client):
        """Test resolve to resources listing with filters."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        mock_response = {
            'computationModelResolveToResourceSummaries': [
                {'resourceId': 'asset-1', 'resourceType': 'ASSET'},
            ],
            'nextToken': None,
        }
        mock_client.list_computation_model_resolve_to_resources.return_value = mock_response

        result = list_computation_model_resolve_to_resources(
            computation_model_id='87654321-4321-4321-4321-210987654321',
            region='us-west-2',
            max_results=25,
            next_token='cHJldi10b2tlbg==',
        )

        assert result['success'] is True
        assert len(result['computationModelResolveToResourceSummaries']) == 1
        assert result['nextToken'] is None
        mock_client.list_computation_model_resolve_to_resources.assert_called_once_with(
            computationModelId='87654321-4321-4321-4321-210987654321',
            maxResults=25,
            nextToken='cHJldi10b2tlbg==',
        )

    # Error handling tests
    @patch(
        'awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_computation_models.create_sitewise_client'
    )
    def test_delete_computation_model_client_error(self, mock_boto_client):
        """Test computation model deletion with client error."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        error_response = {
            'Error': {
                'Code': 'ResourceNotFoundException',
                'Message': 'Computation model not found',
            }
        }
        mock_client.delete_computation_model.side_effect = ClientError(
            error_response, 'DeleteComputationModel'
        )

        result = delete_computation_model(
            computation_model_id='12345678-1234-1234-1234-123456789012',
        )

        assert result['success'] is False
        assert result['error_code'] == 'ResourceNotFoundException'
        assert 'Computation model not found' in result['error']

    @patch(
        'awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_computation_models.create_sitewise_client'
    )
    def test_update_computation_model_client_error(self, mock_boto_client):
        """Test computation model update with client error."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        error_response = {
            'Error': {
                'Code': 'ConflictException',
                'Message': 'Computation model is being updated',
            }
        }
        mock_client.update_computation_model.side_effect = ClientError(
            error_response, 'UpdateComputationModel'
        )

        computation_model_configuration = {
            'anomalyDetection': {
                'inputProperties': '${input_properties}',
                'resultProperty': '${result_property}',
            }
        }
        computation_model_data_binding = {
            'input_properties': {
                'list': [
                    {
                        'assetProperty': {
                            'assetId': '87654321-4321-4321-4321-210987654321',
                            'propertyId': '11111111-1111-1111-1111-111111111111',
                        }
                    }
                ]
            },
            'result_property': {
                'assetProperty': {
                    'assetId': '87654321-4321-4321-4321-210987654321',
                    'propertyId': '22222222-2222-2222-2222-222222222222',
                }
            },
        }

        result = update_computation_model(
            computation_model_id='12345678-1234-1234-1234-123456789012',
            computation_model_name='Updated Model',
            computation_model_configuration=computation_model_configuration,
            computation_model_data_binding=computation_model_data_binding,
        )

        assert result['success'] is False
        assert result['error_code'] == 'ConflictException'
        assert 'Computation model is being updated' in result['error']

    @patch(
        'awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_computation_models.create_sitewise_client'
    )
    def test_list_computation_models_client_error(self, mock_boto_client):
        """Test computation models listing with client error."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        error_response = {
            'Error': {
                'Code': 'ThrottlingException',
                'Message': 'Request was throttled',
            }
        }
        mock_client.list_computation_models.side_effect = ClientError(
            error_response, 'ListComputationModels'
        )

        result = list_computation_models()

        assert result['success'] is False
        assert result['error_code'] == 'ThrottlingException'
        assert 'Request was throttled' in result['error']

    @patch(
        'awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_computation_models.create_sitewise_client'
    )
    def test_describe_computation_model_client_error(self, mock_boto_client):
        """Test computation model description with client error."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        error_response = {
            'Error': {
                'Code': 'ResourceNotFoundException',
                'Message': 'Computation model not found',
            }
        }
        mock_client.describe_computation_model.side_effect = ClientError(
            error_response, 'DescribeComputationModel'
        )

        result = describe_computation_model(
            computation_model_id='12345678-1234-1234-1234-123456789012',
        )

        assert result['success'] is False
        assert result['error_code'] == 'ResourceNotFoundException'
        assert 'Computation model not found' in result['error']

    @patch(
        'awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_computation_models.describe_computation_model'
    )
    def test_determine_computation_model_configuration_type_describe_error(self, mock_describe):
        """Test configuration type determination when describe fails."""
        mock_describe.return_value = {
            'success': False,
            'error': 'Failed to describe computation model',
            'error_code': 'ResourceNotFoundException',
        }

        result = _determine_computation_model_configuration_type(
            computation_model_id='nonexistent-model-id',
            region='us-east-1',
        )

        assert result['success'] is False
        assert 'Failed to describe computation model' in result['error']

    @patch(
        'awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_computation_models._determine_computation_model_configuration_type'
    )
    @patch(
        'awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_computation_models.create_sitewise_client'
    )
    def test_describe_computation_model_execution_summary_client_error(
        self, mock_boto_client, mock_determine_type
    ):
        """Test execution summary with client error."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        mock_determine_type.return_value = {
            'success': True,
            'is_asset_model_level': True,
            'configuration_type': 'Asset Model Level Configuration',
        }

        error_response = {
            'Error': {
                'Code': 'InvalidRequestException',
                'Message': 'Invalid request parameters',
            }
        }
        mock_client.describe_computation_model_execution_summary.side_effect = ClientError(
            error_response, 'DescribeComputationModelExecutionSummary'
        )

        result = describe_computation_model_execution_summary(
            computation_model_id='12345678-1234-1234-1234-123456789012',
            resolve_to_resource_id='87654321-4321-4321-4321-210987654321',
            resolve_to_resource_type='ASSET',
        )

        assert result['success'] is False
        assert result['error_code'] == 'InvalidRequestException'
        assert 'Invalid request parameters' in result['error']

    @patch(
        'awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_computation_models.create_sitewise_client'
    )
    def test_list_computation_model_data_binding_usages_client_error(self, mock_boto_client):
        """Test data binding usages listing with client error."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        error_response = {
            'Error': {
                'Code': 'ValidationException',
                'Message': 'Invalid filter parameters',
            }
        }
        mock_client.list_computation_model_data_binding_usages.side_effect = ClientError(
            error_response, 'ListComputationModelDataBindingUsages'
        )

        # Use a valid filter structure that passes Pydantic validation but causes client error
        data_binding_value_filter = {'asset': {'assetId': '12345678-1234-1234-1234-123456789012'}}

        result = list_computation_model_data_binding_usages(
            data_binding_value_filter=data_binding_value_filter,
        )

        assert result['success'] is False
        assert result['error_code'] == 'ValidationException'
        assert 'Invalid filter parameters' in result['error']

    @patch(
        'awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_computation_models.create_sitewise_client'
    )
    def test_list_computation_model_resolve_to_resources_client_error(self, mock_boto_client):
        """Test resolve to resources listing with client error."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        error_response = {
            'Error': {
                'Code': 'AccessDeniedException',
                'Message': 'Access denied',
            }
        }
        mock_client.list_computation_model_resolve_to_resources.side_effect = ClientError(
            error_response, 'ListComputationModelResolveToResources'
        )

        result = list_computation_model_resolve_to_resources(
            computation_model_id='12345678-1234-1234-1234-123456789012',
        )

        assert result['success'] is False
        assert result['error_code'] == 'AccessDeniedException'
        assert 'Access denied' in result['error']

    # Edge case tests
    def test_create_anomaly_detection_model_with_minimal_params(self):
        """Test anomaly detection model creation with minimal parameters."""
        with patch(
            'awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_computation_models.create_computation_model'
        ) as mock_create:
            mock_create.return_value = {
                'success': True,
                'computationModelId': '12345678-1234-1234-1234-123456789012',
                'computationModelArn': 'arn:aws:iotsitewise:us-east-1:123456789012:computation-model/12345678-1234-1234-1234-123456789012',
                'computationModelStatus': {'state': 'CREATING'},
            }

            input_properties = [
                {
                    'assetProperty': {
                        'assetId': '87654321-4321-4321-4321-210987654321',
                        'propertyId': '11111111-1111-1111-1111-111111111111',
                    }
                }
            ]
            result_property = {
                'assetProperty': {
                    'assetId': '87654321-4321-4321-4321-210987654321',
                    'propertyId': '22222222-2222-2222-2222-222222222222',
                }
            }

            result = create_anomaly_detection_model(
                computation_model_name='Minimal Anomaly Detection',
                input_properties=input_properties,
                result_property=result_property,
            )

            assert result['success'] is True
            mock_create.assert_called_once()

    @patch(
        'awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_computation_models.describe_computation_model'
    )
    def test_determine_computation_model_configuration_type_mixed_bindings(self, mock_describe):
        """Test configuration type determination with mixed property bindings."""
        mock_describe.return_value = {
            'success': True,
            'computationModelDataBinding': {
                'input_properties': {
                    'list': [
                        {
                            'assetModelProperty': {
                                'assetModelId': '12345678-1234-1234-1234-123456789012',
                                'propertyId': '11111111-1111-1111-1111-111111111111',
                            }
                        },
                        {
                            'assetProperty': {
                                'assetId': '87654321-4321-4321-4321-210987654321',
                                'propertyId': '22222222-2222-2222-2222-222222222222',
                            }
                        },
                    ]
                },
                'result_property': {
                    'assetModelProperty': {
                        'assetModelId': '12345678-1234-1234-1234-123456789012',
                        'propertyId': '33333333-3333-3333-3333-333333333333',
                    }
                },
            },
        }

        result = _determine_computation_model_configuration_type(
            computation_model_id='12345678-1234-1234-1234-123456789012',
            region='us-east-1',
        )

        # Should detect as asset model level since result property is asset model property
        assert result['success'] is True
        assert result['is_asset_model_level'] is True
        assert result['configuration_type'] == 'Asset Model Level Configuration'

    @patch(
        'awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_computation_models.describe_computation_model'
    )
    def test_determine_computation_model_configuration_type_empty_bindings(self, mock_describe):
        """Test configuration type determination with empty data bindings."""
        mock_describe.return_value = {'success': True, 'computationModelDataBinding': {}}

        result = _determine_computation_model_configuration_type(
            computation_model_id='12345678-1234-1234-1234-123456789012',
            region='us-east-1',
        )

        # Should default to asset level when unable to determine
        assert result['success'] is True
        assert result['is_asset_model_level'] is False
        assert result['configuration_type'] == 'Asset Level Configuration'

    @patch(
        'awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_computation_models._determine_computation_model_configuration_type'
    )
    def test_describe_computation_model_execution_summary_determine_type_error(
        self, mock_determine_type
    ):
        """Test execution summary when configuration type determination fails."""
        mock_determine_type.return_value = {
            'success': False,
            'error': 'Failed to determine configuration type',
            'error_code': 'InternalError',
        }

        result = describe_computation_model_execution_summary(
            computation_model_id='12345678-1234-1234-1234-123456789012',
        )

        assert result['success'] is False
        assert 'Failed to determine configuration type' in result['error']
        assert result['error_code'] == 'InternalError'

    # Test parameter validation edge cases
    @patch(
        'awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_computation_models.create_sitewise_client'
    )
    def test_list_computation_models_empty_response(self, mock_boto_client):
        """Test computation models listing with empty response."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        mock_response = {
            'computationModelSummaries': [],
            'nextToken': None,
        }
        mock_client.list_computation_models.return_value = mock_response

        result = list_computation_models()

        assert result['success'] is True
        assert len(result['computationModelSummaries']) == 0
        assert result['nextToken'] is None

    @patch(
        'awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_computation_models.create_sitewise_client'
    )
    def test_list_computation_model_data_binding_usages_empty_response(self, mock_boto_client):
        """Test data binding usages listing with empty response."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        mock_response = {
            'computationModelSummaries': [],
            'nextToken': None,
        }
        mock_client.list_computation_model_data_binding_usages.return_value = mock_response

        data_binding_value_filter = {'asset': {'assetId': '12345678-1234-1234-1234-123456789012'}}

        result = list_computation_model_data_binding_usages(
            data_binding_value_filter=data_binding_value_filter,
        )

        assert result['success'] is True
        assert len(result['computationModelSummaries']) == 0
        assert result['nextToken'] is None

    @patch(
        'awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_computation_models.create_sitewise_client'
    )
    def test_list_computation_model_resolve_to_resources_empty_response(self, mock_boto_client):
        """Test resolve to resources listing with empty response."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        mock_response = {
            'computationModelResolveToResourceSummaries': [],
            'nextToken': None,
        }
        mock_client.list_computation_model_resolve_to_resources.return_value = mock_response

        result = list_computation_model_resolve_to_resources(
            computation_model_id='12345678-1234-1234-1234-123456789012',
        )

        assert result['success'] is True
        assert len(result['computationModelResolveToResourceSummaries']) == 0
        assert result['nextToken'] is None

    # Additional tests to improve coverage
    @patch(
        'awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_computation_models.create_sitewise_client'
    )
    def test_create_computation_model_validation_error(self, mock_boto_client):
        """Test create_computation_model with validation error."""
        # Mock the boto3 client to prevent actual AWS calls
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        # Test with invalid computation_model_configuration structure
        # This should raise a Pydantic ValidationError
        from pydantic import ValidationError

        with pytest.raises(ValidationError) as exc_info:
            create_computation_model(
                computation_model_name='Test Model',
                computation_model_configuration={'invalidKey': 'value'},  # Missing required fields
                computation_model_data_binding={'input_properties': {'list': []}},
            )

        # Verify the validation error contains the expected message
        assert 'ComputationModelConfiguration has 0 types defined' in str(exc_info.value)

        # Verify that the client was not called due to validation error
        mock_client.create_computation_model.assert_not_called()

    def test_delete_computation_model_validation_error(self):
        """Test delete_computation_model with validation error."""
        # Test with invalid computation_model_id format - should raise ValidationError
        from pydantic import ValidationError

        with pytest.raises(ValidationError) as exc_info:
            delete_computation_model(
                computation_model_id='invalid-id-format'  # This will trigger validation error
            )

        # Verify it's a Pydantic validation error for DeleteComputationModelRequest
        assert 'DeleteComputationModelRequest' in str(exc_info.value)
        assert 'computationModelId' in str(exc_info.value)
        assert 'must be exactly 36 characters' in str(exc_info.value)

    def test_update_computation_model_validation_error(self):
        """Test update_computation_model with validation error."""
        # Test with invalid computation_model_id format - should raise ValidationError
        from pydantic import ValidationError

        with pytest.raises(ValidationError) as exc_info:
            update_computation_model(
                computation_model_id='invalid-id-format',  # This will trigger validation error
                computation_model_name='Updated Model',
                computation_model_configuration={
                    'anomalyDetection': {
                        'inputProperties': '${input}',
                        'resultProperty': '${result}',
                    }
                },
                computation_model_data_binding={
                    'input': {
                        'assetProperty': {
                            'assetId': '12345678-1234-1234-1234-123456789012',
                            'propertyId': '11111111-1111-1111-1111-111111111111',
                        }
                    }
                },
            )

        # Verify it's a Pydantic validation error for UpdateComputationModelRequest
        assert 'UpdateComputationModelRequest' in str(exc_info.value)
        assert 'computationModelId' in str(exc_info.value)
        assert 'must be exactly 36 characters' in str(exc_info.value)

    def test_list_computation_models_validation_error(self):
        """Test list_computation_models with validation error."""
        # Test with invalid max_results value - should raise ValidationError
        from pydantic import ValidationError

        with pytest.raises(ValidationError) as exc_info:
            list_computation_models(
                max_results=300  # This exceeds the maximum allowed value
            )

        # Verify it's a Pydantic validation error for ListComputationModelsRequest
        assert 'ListComputationModelsRequest' in str(exc_info.value)
        assert 'maxResults' in str(exc_info.value)
        assert 'must be between 1 and 250' in str(exc_info.value)

    def test_describe_computation_model_validation_error(self):
        """Test describe_computation_model with validation error."""
        # Test with invalid computation_model_id format - should raise ValidationError
        from pydantic import ValidationError

        with pytest.raises(ValidationError) as exc_info:
            describe_computation_model(
                computation_model_id='invalid-id-format'  # This will trigger validation error
            )

        # Verify it's a Pydantic validation error for DescribeComputationModelRequest
        assert 'DescribeComputationModelRequest' in str(exc_info.value)
        assert 'computationModelId' in str(exc_info.value)
        assert 'must be exactly 36 characters' in str(exc_info.value)

    def test_list_computation_model_data_binding_usages_validation_error(self):
        """Test list_computation_model_data_binding_usages with validation error."""
        # Test with invalid data_binding_value_filter structure - should raise ValidationError
        from pydantic import ValidationError

        with pytest.raises(ValidationError) as exc_info:
            list_computation_model_data_binding_usages(
                data_binding_value_filter={'invalidKey': 'value'}  # Missing required fields
            )

        # Verify it's a Pydantic validation error for DataBindingValueFilter
        assert 'DataBindingValueFilter' in str(exc_info.value)
        assert (
            'must define exactly one of: asset, assetModel, assetProperty, or assetModelProperty'
            in str(exc_info.value)
        )

    def test_list_computation_model_resolve_to_resources_validation_error(self):
        """Test list_computation_model_resolve_to_resources with validation error."""
        # Test with invalid computation_model_id format - should raise ValidationError
        from pydantic import ValidationError

        with pytest.raises(ValidationError) as exc_info:
            list_computation_model_resolve_to_resources(
                computation_model_id='invalid-id-format'  # This will trigger validation error
            )

        # Verify it's a Pydantic validation error for ListComputationModelResolveToResourcesRequest
        assert 'ListComputationModelResolveToResourcesRequest' in str(exc_info.value)
        assert 'computationModelId' in str(exc_info.value)
        assert 'must be exactly 36 characters' in str(exc_info.value)

    def test_determine_computation_model_configuration_type_generic_exception(self):
        """Test _determine_computation_model_configuration_type with generic exception."""
        # Test with None configuration_type and invalid computation_model_id to trigger exception
        result = _determine_computation_model_configuration_type(
            computation_model_id='invalid-id-format',
            region='us-east-1',
            configuration_type=None,
        )

        # Verify it returns an error response
        assert result['success'] is False
        assert result['error_code'] == 'InternalError'
        assert 'Error determining configuration type' in result['error']

    def test_determine_computation_model_configuration_type_else_branch(self):
        """Test _determine_computation_model_configuration_type else branch for asset level."""
        # Test with configuration_type that doesn't match asset_model_level
        result = _determine_computation_model_configuration_type(
            computation_model_id='12345678-1234-1234-1234-123456789012',
            region='us-east-1',
            configuration_type='asset_level',  # This will trigger the else branch
        )

        assert result['success'] is True
        assert result['is_asset_model_level'] is False
        assert result['configuration_type'] == 'Asset Level Configuration'

    def test_create_computation_model_custom_validation_error(self):
        """Test create_computation_model CustomValidationError handling."""
        from awslabs.aws_iot_sitewise_mcp_server.validation import (
            ValidationError as CustomValidationError,
        )

        with patch(
            'awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_computation_models.ComputationModelConfiguration'
        ) as mock_config:
            mock_config.side_effect = CustomValidationError('Test validation error')

            result = create_computation_model(
                computation_model_name='Test Model',
                computation_model_configuration={
                    'anomalyDetection': {
                        'inputProperties': '${input}',
                        'resultProperty': '${result}',
                    }
                },
                computation_model_data_binding={
                    'input': {
                        'assetProperty': {
                            'assetId': '12345678-1234-1234-1234-123456789012',
                            'propertyId': '11111111-1111-1111-1111-111111111111',
                        }
                    }
                },
            )

            assert result['success'] is False
            assert result['error_code'] == 'ValidationException'
            assert 'Validation error: Test validation error' in result['error']

    def test_delete_computation_model_custom_validation_error(self):
        """Test delete_computation_model CustomValidationError handling."""
        from awslabs.aws_iot_sitewise_mcp_server.validation import (
            ValidationError as CustomValidationError,
        )

        with patch(
            'awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_computation_models.DeleteComputationModelRequest'
        ) as mock_request:
            mock_request.side_effect = CustomValidationError('Test validation error')

            result = delete_computation_model(
                computation_model_id='12345678-1234-1234-1234-123456789012'
            )

            assert result['success'] is False
            assert result['error_code'] == 'ValidationException'
            assert 'Validation error: Test validation error' in result['error']

    def test_update_computation_model_custom_validation_error(self):
        """Test update_computation_model CustomValidationError handling."""
        from awslabs.aws_iot_sitewise_mcp_server.validation import (
            ValidationError as CustomValidationError,
        )

        with patch(
            'awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_computation_models.ComputationModelConfiguration'
        ) as mock_config:
            mock_config.side_effect = CustomValidationError('Test validation error')

            result = update_computation_model(
                computation_model_id='12345678-1234-1234-1234-123456789012',
                computation_model_name='Updated Model',
                computation_model_configuration={
                    'anomalyDetection': {
                        'inputProperties': '${input}',
                        'resultProperty': '${result}',
                    }
                },
                computation_model_data_binding={
                    'input': {
                        'assetProperty': {
                            'assetId': '12345678-1234-1234-1234-123456789012',
                            'propertyId': '11111111-1111-1111-1111-111111111111',
                        }
                    }
                },
            )

            assert result['success'] is False
            assert result['error_code'] == 'ValidationException'
            assert 'Validation error: Test validation error' in result['error']

    def test_list_computation_models_custom_validation_error(self):
        """Test list_computation_models CustomValidationError handling."""
        from awslabs.aws_iot_sitewise_mcp_server.validation import (
            ValidationError as CustomValidationError,
        )

        with patch(
            'awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_computation_models.ListComputationModelsRequest'
        ) as mock_request:
            mock_request.side_effect = CustomValidationError('Test validation error')

            result = list_computation_models()

            assert result['success'] is False
            assert result['error_code'] == 'ValidationException'
            assert 'Validation error: Test validation error' in result['error']

    def test_describe_computation_model_custom_validation_error(self):
        """Test describe_computation_model CustomValidationError handling."""
        from awslabs.aws_iot_sitewise_mcp_server.validation import (
            ValidationError as CustomValidationError,
        )

        with patch(
            'awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_computation_models.DescribeComputationModelRequest'
        ) as mock_request:
            mock_request.side_effect = CustomValidationError('Test validation error')

            result = describe_computation_model(
                computation_model_id='12345678-1234-1234-1234-123456789012'
            )

            assert result['success'] is False
            assert result['error_code'] == 'ValidationException'
            assert 'Validation error: Test validation error' in result['error']

    def test_describe_computation_model_execution_summary_custom_validation_error(self):
        """Test describe_computation_model_execution_summary CustomValidationError handling."""
        from awslabs.aws_iot_sitewise_mcp_server.validation import (
            ValidationError as CustomValidationError,
        )

        with patch(
            'awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_computation_models._determine_computation_model_configuration_type'
        ) as mock_determine:
            mock_determine.return_value = {
                'success': True,
                'is_asset_model_level': True,
                'configuration_type': 'Asset Model Level Configuration',
            }

            with patch(
                'awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_computation_models.DescribeComputationModelExecutionSummaryRequest'
            ) as mock_request:
                mock_request.side_effect = CustomValidationError('Test validation error')

                result = describe_computation_model_execution_summary(
                    computation_model_id='12345678-1234-1234-1234-123456789012'
                )

                assert result['success'] is False
                assert result['error_code'] == 'ValidationException'
                assert 'Validation error: Test validation error' in result['error']

    def test_list_computation_model_data_binding_usages_custom_validation_error(self):
        """Test list_computation_model_data_binding_usages CustomValidationError handling."""
        from awslabs.aws_iot_sitewise_mcp_server.validation import (
            ValidationError as CustomValidationError,
        )

        with patch(
            'awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_computation_models.DataBindingValueFilter'
        ) as mock_filter:
            mock_filter.side_effect = CustomValidationError('Test validation error')

            result = list_computation_model_data_binding_usages(
                data_binding_value_filter={
                    'asset': {'assetId': '12345678-1234-1234-1234-123456789012'}
                }
            )

            assert result['success'] is False
            assert result['error_code'] == 'ValidationException'
            assert 'Validation error: Test validation error' in result['error']

    def test_list_computation_model_resolve_to_resources_custom_validation_error(self):
        """Test list_computation_model_resolve_to_resources CustomValidationError handling."""
        from awslabs.aws_iot_sitewise_mcp_server.validation import (
            ValidationError as CustomValidationError,
        )

        with patch(
            'awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_computation_models.ListComputationModelResolveToResourcesRequest'
        ) as mock_request:
            mock_request.side_effect = CustomValidationError('Test validation error')

            result = list_computation_model_resolve_to_resources(
                computation_model_id='12345678-1234-1234-1234-123456789012'
            )

            assert result['success'] is False
            assert result['error_code'] == 'ValidationException'
            assert 'Validation error: Test validation error' in result['error']

    @patch(
        'awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_computation_models.describe_computation_model'
    )
    def test_determine_computation_model_configuration_type_direct_asset_model_property(
        self, mock_describe
    ):
        """Test configuration type determination with direct assetModelProperty (lines 105-107)."""
        mock_describe.return_value = {
            'success': True,
            'computationModelDataBinding': {
                'result_property': {
                    'assetModelProperty': {
                        'assetModelId': '12345678-1234-1234-1234-123456789012',
                        'propertyId': '11111111-1111-1111-1111-111111111111',
                    }
                }
            },
        }

        result = _determine_computation_model_configuration_type(
            computation_model_id='12345678-1234-1234-1234-123456789012',
            region='us-east-1',
        )

        assert result['success'] is True
        assert result['is_asset_model_level'] is True
        assert result['configuration_type'] == 'Asset Model Level Configuration'

    @patch(
        'awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_computation_models._determine_computation_model_configuration_type'
    )
    @patch(
        'awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_computation_models.create_sitewise_client'
    )
    def test_describe_computation_model_execution_summary_asset_model_level_no_resolve_params(
        self, mock_boto_client, mock_determine_type
    ):
        """Test execution summary for asset model level without resolve parameters (line 726)."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        mock_determine_type.return_value = {
            'success': True,
            'is_asset_model_level': True,
            'configuration_type': 'Asset Model Level Configuration',
        }

        mock_response = {
            'computationModelId': '12345678-1234-1234-1234-123456789012',
            'computationModelExecutionSummary': {'status': 'ACTIVE'},
        }
        mock_client.describe_computation_model_execution_summary.return_value = mock_response

        # Call without resolve parameters to trigger line 726
        result = describe_computation_model_execution_summary(
            computation_model_id='12345678-1234-1234-1234-123456789012',
            region='us-east-1',
        )

        assert result['success'] is True
        assert result['configurationType'] == 'Asset Model Level Configuration'
        assert 'info' in result
        assert 'consider providing resolve parameters' in result['info']
        mock_client.describe_computation_model_execution_summary.assert_called_once()

    @patch(
        'awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_computation_models.describe_computation_model'
    )
    def test_determine_computation_model_configuration_type_non_dict_binding_value(
        self, mock_describe
    ):
        """Test configuration type determination with non-dict binding value (line 102->101 branch coverage)."""
        mock_describe.return_value = {
            'success': True,
            'computationModelDataBinding': {
                'input_properties': 'not_a_dict',  # This will trigger the isinstance(binding_value, dict) == False branch
                'result_property': {
                    'assetProperty': {
                        'assetId': '87654321-4321-4321-4321-210987654321',
                        'propertyId': '22222222-2222-2222-2222-222222222222',
                    }
                },
            },
        }

        result = _determine_computation_model_configuration_type(
            computation_model_id='12345678-1234-1234-1234-123456789012',
            region='us-east-1',
        )

        # Should default to asset level when binding_value is not a dict
        assert result['success'] is True
        assert result['is_asset_model_level'] is False
        assert result['configuration_type'] == 'Asset Level Configuration'
