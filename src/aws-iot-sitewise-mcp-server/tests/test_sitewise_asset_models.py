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

"""Tests for AWS IoT SiteWise Asset Model Management Tools."""

import os
import pytest
import sys
from awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_asset_models import (
    create_asset_model,
    create_asset_model_composite_model,
    delete_asset_model,
    describe_asset_model,
    list_asset_model_properties,
    list_asset_models,
    update_asset_model,
)
from botocore.exceptions import ClientError
from unittest.mock import Mock, patch


# Add the project root directory and its parent to Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(script_dir)
sys.path.insert(0, project_dir)
sys.path.insert(0, os.path.dirname(project_dir))
sys.path.insert(0, os.path.dirname(os.path.dirname(project_dir)))


class TestSiteWiseAssetModels:
    """Test cases for SiteWise asset model management tools."""

    @patch(
        'awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_asset_models.create_sitewise_client'
    )
    def test_create_asset_model_success(self, mock_create_client):
        """Test successful asset model creation."""
        # Mock the boto3 client
        mock_client = Mock()
        mock_create_client.return_value = mock_client

        # Mock the response
        mock_response = {
            'assetModelId': 'test-model-123',
            'assetModelArn': 'arn:aws:iotsitewise:us-east-1:123456789012:asset-model/test-model-123',
            'assetModelStatus': {'state': 'CREATING'},
        }
        mock_client.create_asset_model.return_value = mock_response

        # Call the function
        result = create_asset_model(
            asset_model_name='Test Model',
            region='us-east-1',
            asset_model_description=None,
            asset_model_properties=None,
            asset_model_hierarchies=None,
            asset_model_composite_models=None,
            client_token=None,
            tags=None,
            asset_model_id=None,
            asset_model_external_id=None,
            asset_model_type='ASSET_MODEL',
        )

        # Verify the result
        assert result['success'] is True
        assert result['asset_model_id'] == 'test-model-123'
        assert (
            result['asset_model_arn']
            == 'arn:aws:iotsitewise:us-east-1:123456789012:asset-model/test-model-123'
        )

    @patch(
        'awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_asset_models.create_sitewise_client'
    )
    def test_describe_asset_model_success(self, mock_create_client):
        """Test successful asset model description."""
        mock_client = Mock()
        mock_create_client.return_value = mock_client

        mock_response = {
            'assetModelId': 'test-model-123',
            'assetModelArn': 'arn:aws:iotsitewise:us-east-1:123456789012:asset-model/test-model-123',
            'assetModelName': 'Test Model',
            'assetModelDescription': 'Test description',
            'assetModelProperties': [],
            'assetModelHierarchies': [],
            'assetModelCompositeModels': [],
            'assetModelStatus': {'state': 'ACTIVE'},
            'assetModelType': 'ASSET_MODEL',
            'assetModelCreationDate': Mock(),
            'assetModelLastUpdateDate': Mock(),
            'assetModelVersion': '1',
            'assetModelVersionDescription': 'Initial version',
            'assetModelExternalId': 'external-123',
        }
        mock_response['assetModelCreationDate'].isoformat.return_value = '2023-01-01T00:00:00Z'
        mock_response['assetModelLastUpdateDate'].isoformat.return_value = '2023-01-01T00:00:00Z'
        mock_client.describe_asset_model.return_value = mock_response

        result = describe_asset_model(
            asset_model_id='test-model-123',
            region='us-east-1',
            exclude_properties=False,
            asset_model_version='LATEST',
        )

        assert result['success'] is True
        assert result['asset_model_id'] == 'test-model-123'
        assert result['asset_model_name'] == 'Test Model'

    @patch(
        'awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_asset_models.create_sitewise_client'
    )
    def test_list_asset_models_success(self, mock_create_client):
        """Test successful asset model listing."""
        mock_client = Mock()
        mock_create_client.return_value = mock_client

        mock_response = {
            'assetModelSummaries': [
                {'id': 'model-1', 'name': 'Model 1'},
                {'id': 'model-2', 'name': 'Model 2'},
            ],
            'nextToken': 'token-123',
        }
        mock_client.list_asset_models.return_value = mock_response

        result = list_asset_models(
            region='us-east-1', next_token=None, max_results=50, asset_model_types=None
        )

        assert result['success'] is True
        assert len(result['asset_model_summaries']) == 2

    @patch(
        'awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_asset_models.create_sitewise_client'
    )
    def test_update_asset_model_success(self, mock_create_client):
        """Test successful asset model update."""
        mock_client = Mock()
        mock_create_client.return_value = mock_client

        mock_response = {'assetModelStatus': {'state': 'UPDATING'}}
        mock_client.update_asset_model.return_value = mock_response

        result = update_asset_model(
            asset_model_id='test-model-123',
            asset_model_name='Updated Model',
            region='us-east-1',
            asset_model_description=None,
            asset_model_properties=None,
            asset_model_hierarchies=None,
            asset_model_composite_models=None,
            client_token=None,
            asset_model_external_id=None,
        )

        assert result['success'] is True
        assert result['asset_model_status']['state'] == 'UPDATING'

    @patch(
        'awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_asset_models.create_sitewise_client'
    )
    def test_delete_asset_model_success(self, mock_create_client):
        """Test successful asset model deletion."""
        mock_client = Mock()
        mock_create_client.return_value = mock_client

        mock_response = {'assetModelStatus': {'state': 'DELETING'}}
        mock_client.delete_asset_model.return_value = mock_response

        result = delete_asset_model(
            asset_model_id='test-model-123', region='us-east-1', client_token=None
        )

        assert result['success'] is True
        assert result['asset_model_status']['state'] == 'DELETING'

    @patch(
        'awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_asset_models.create_sitewise_client'
    )
    def test_list_asset_model_properties_success(self, mock_create_client):
        """Test successful asset model properties listing."""
        mock_client = Mock()
        mock_create_client.return_value = mock_client

        mock_response = {
            'assetModelPropertySummaries': [
                {'id': 'prop-1', 'name': 'Property 1'},
                {'id': 'prop-2', 'name': 'Property 2'},
            ],
            'nextToken': 'token-123',
        }
        mock_client.list_asset_model_properties.return_value = mock_response

        result = list_asset_model_properties(
            asset_model_id='test-model-123',
            region='us-east-1',
            next_token=None,
            max_results=50,
            asset_model_version='LATEST',
            filter_type=None,
        )

        assert result['success'] is True
        assert len(result['asset_model_property_summaries']) == 2

    @patch(
        'awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_asset_models.create_sitewise_client'
    )
    def test_create_asset_model_composite_model_success(self, mock_create_client):
        """Test successful composite model creation."""
        mock_client = Mock()
        mock_create_client.return_value = mock_client

        mock_response = {
            'assetModelCompositeModelId': 'composite-123',
            'assetModelCompositeModelPath': [{'id': 'path-1'}],
            'assetModelStatus': {'state': 'UPDATING'},
        }
        mock_client.create_asset_model_composite_model.return_value = mock_response

        result = create_asset_model_composite_model(
            asset_model_id='test-model-123',
            asset_model_composite_model_name='Test Composite',
            asset_model_composite_model_type='AWS/ALARM',
            region='us-east-1',
            asset_model_composite_model_description=None,
            asset_model_composite_model_properties=None,
            client_token=None,
            asset_model_composite_model_id=None,
            asset_model_composite_model_external_id=None,
            parent_asset_model_composite_model_id=None,
            composed_asset_model_id=None,
        )

        assert result['success'] is True
        assert result['asset_model_composite_model_id'] == 'composite-123'

    @patch(
        'awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_asset_models.create_sitewise_client'
    )
    def test_asset_model_validation_errors(self, mock_create_client):
        """Test validation error handling in asset models."""
        mock_client = Mock()
        mock_create_client.return_value = mock_client

        # Mock a successful response for cases that pass validation
        mock_response = {
            'assetModelId': 'test-model-123',
            'assetModelArn': 'arn:aws:iotsitewise:us-east-1:123456789012:asset-model/test-model-123',
            'assetModelStatus': {'state': 'CREATING'},
        }
        mock_client.create_asset_model.return_value = mock_response

        # Test various validation failures that happen during parameter
        # validation
        result = create_asset_model(
            asset_model_name='Test Model',
            region='us-east-1',
            asset_model_description='a' * 2049,  # Exceeds limit
            asset_model_properties=None,
            asset_model_hierarchies=None,
            asset_model_composite_models=None,
            client_token=None,
            tags=None,
            asset_model_id=None,
            asset_model_external_id=None,
            asset_model_type='ASSET_MODEL',
        )
        assert result['success'] is False
        assert result['error_code'] == 'ValidationException'

        # Test too many tags
        result = create_asset_model(
            asset_model_name='Test Model',
            region='us-east-1',
            asset_model_description=None,
            asset_model_properties=None,
            asset_model_hierarchies=None,
            asset_model_composite_models=None,
            client_token=None,
            tags={f'key{i}': f'value{i}' for i in range(51)},  # Exceeds limit
            asset_model_id=None,
            asset_model_external_id=None,
            asset_model_type='ASSET_MODEL',
        )
        assert result['success'] is False
        assert result['error_code'] == 'ValidationException'

    @patch(
        'awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_asset_models.create_sitewise_client'
    )
    def test_client_error_handling(self, mock_create_client):
        """Test ClientError handling."""
        mock_client = Mock()
        mock_create_client.return_value = mock_client

        error_response = {
            'Error': {'Code': 'ConflictException', 'Message': 'Model already exists'}
        }
        mock_client.create_asset_model.side_effect = ClientError(
            error_response, 'CreateAssetModel'
        )

        result = create_asset_model(
            asset_model_name='Test Model',
            region='us-east-1',
            asset_model_description=None,
            asset_model_properties=None,
            asset_model_hierarchies=None,
            asset_model_composite_models=None,
            client_token=None,
            tags=None,
            asset_model_id=None,
            asset_model_external_id=None,
            asset_model_type='ASSET_MODEL',
        )

        assert result['success'] is False
        assert result['error_code'] == 'ConflictException'

    def test_create_asset_model_validation_errors(self):
        """Test create asset model validation error cases."""
        # Test asset model description too long
        result = create_asset_model(
            asset_model_name='Test Model',
            region='us-east-1',
            asset_model_description='x' * 2049,  # Exceeds 2048 character limit
            asset_model_properties=None,
            asset_model_hierarchies=None,
            asset_model_composite_models=None,
            client_token=None,
            tags=None,
            asset_model_id=None,
            asset_model_external_id=None,
            asset_model_type='ASSET_MODEL',
        )
        assert result['success'] is False
        assert 'Asset model description cannot exceed 2048 characters' in result['error']

        # Test client token too long
        result = create_asset_model(
            asset_model_name='Test Model',
            region='us-east-1',
            asset_model_description=None,
            asset_model_properties=None,
            asset_model_hierarchies=None,
            asset_model_composite_models=None,
            client_token='x' * 65,  # Exceeds 64 character limit
            tags=None,
            asset_model_id=None,
            asset_model_external_id=None,
            asset_model_type='ASSET_MODEL',
        )
        assert result['success'] is False
        assert 'Client token cannot exceed 64 characters' in result['error']

        # Test too many tags
        # Exceeds 50 tag limit
        too_many_tags = {f'key{i}': f'value{i}' for i in range(51)}
        result = create_asset_model(
            asset_model_name='Test Model',
            region='us-east-1',
            asset_model_description=None,
            asset_model_properties=None,
            asset_model_hierarchies=None,
            asset_model_composite_models=None,
            client_token=None,
            tags=too_many_tags,
            asset_model_id=None,
            asset_model_external_id=None,
            asset_model_type='ASSET_MODEL',
        )
        assert result['success'] is False
        assert 'Cannot have more than 50 tags per asset model' in result['error']

        # Test too many hierarchies
        too_many_hierarchies = [{'name': f'hierarchy{i}'} for i in range(11)]  # Exceeds 10 limit
        result = create_asset_model(
            asset_model_name='Test Model',
            region='us-east-1',
            asset_model_description=None,
            asset_model_properties=None,
            asset_model_hierarchies=too_many_hierarchies,
            asset_model_composite_models=None,
            client_token=None,
            tags=None,
            asset_model_id=None,
            asset_model_external_id=None,
            asset_model_type='ASSET_MODEL',
        )
        assert result['success'] is False
        assert 'Cannot have more than 10 hierarchies per asset model' in result['error']

        # Test too many composite models
        too_many_composite = [{'name': f'composite{i}'} for i in range(11)]  # Exceeds 10 limit
        result = create_asset_model(
            asset_model_name='Test Model',
            region='us-east-1',
            asset_model_description=None,
            asset_model_properties=None,
            asset_model_hierarchies=None,
            asset_model_composite_models=too_many_composite,
            client_token=None,
            tags=None,
            asset_model_id=None,
            asset_model_external_id=None,
            asset_model_type='ASSET_MODEL',
        )
        assert result['success'] is False
        assert 'Cannot have more than 10 composite models per asset model' in result['error']

    @patch(
        'awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_asset_models.validate_asset_model_properties'
    )
    @patch(
        'awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_asset_models.create_sitewise_client'
    )
    def test_create_asset_model_with_all_params(self, mock_create_client, mock_validate_props):
        """Test create asset model with all optional parameters."""
        mock_client = Mock()
        mock_create_client.return_value = mock_client
        # Mock the validation to pass
        mock_validate_props.return_value = None

        mock_response = {
            'assetModelId': 'test-model-123',
            'assetModelArn': 'arn:aws:iotsitewise:us-east-1:123456789012:asset-model/test-model-123',
            'assetModelStatus': {'state': 'CREATING'},
        }
        mock_client.create_asset_model.return_value = mock_response

        result = create_asset_model(
            asset_model_name='Test Model',
            region='us-west-2',
            asset_model_description='Test description',
            asset_model_properties=[{'name': 'property1', 'dataType': 'DOUBLE'}],
            asset_model_hierarchies=[{'name': 'hierarchy1'}],
            asset_model_composite_models=[{'name': 'composite1'}],
            client_token='test-token',
            tags={'Environment': 'Test'},
            asset_model_id='custom-model-id',
            asset_model_external_id='ext-123',
            asset_model_type='COMPONENT_MODEL',
        )

        assert result['success'] is True
        mock_client.create_asset_model.assert_called_once_with(
            assetModelName='Test Model',
            assetModelType='COMPONENT_MODEL',
            assetModelDescription='Test description',
            assetModelProperties=[{'name': 'property1', 'dataType': 'DOUBLE'}],
            assetModelHierarchies=[{'name': 'hierarchy1'}],
            assetModelCompositeModels=[{'name': 'composite1'}],
            clientToken='test-token',
            tags={'Environment': 'Test'},
            assetModelId='custom-model-id',
            assetModelExternalId='ext-123',
        )

    def test_describe_asset_model_validation_errors(self):
        """Test describe asset model validation error cases."""
        # Test invalid asset model version
        result = describe_asset_model(
            asset_model_id='test-model-123',
            region='us-east-1',
            exclude_properties=False,
            asset_model_version='INVALID_VERSION',
        )
        assert result['success'] is False
        assert "Asset model version must be 'LATEST' or 'ACTIVE'" in result['error']

    @patch(
        'awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_asset_models.create_sitewise_client'
    )
    def test_describe_asset_model_with_all_params(self, mock_create_client):
        """Test describe asset model with all optional parameters."""
        mock_client = Mock()
        mock_create_client.return_value = mock_client

        mock_response = {
            'assetModelId': 'test-model-123',
            'assetModelArn': 'arn:aws:iotsitewise:us-east-1:123456789012:asset-model/test-model-123',
            'assetModelName': 'Test Model',
            'assetModelDescription': 'Test description',
            'assetModelProperties': [],
            'assetModelHierarchies': [],
            'assetModelCompositeModels': [],
            'assetModelStatus': {'state': 'ACTIVE'},
            'assetModelType': 'ASSET_MODEL',
            'assetModelCreationDate': Mock(),
            'assetModelLastUpdateDate': Mock(),
            'assetModelVersion': '1',
            'assetModelVersionDescription': 'Version 1',
            'assetModelExternalId': 'ext-123',
        }
        mock_response['assetModelCreationDate'].isoformat.return_value = '2023-01-01T00:00:00Z'
        mock_response['assetModelLastUpdateDate'].isoformat.return_value = '2023-01-01T00:00:00Z'
        mock_client.describe_asset_model.return_value = mock_response

        result = describe_asset_model(
            asset_model_id='test-model-123',
            region='us-west-2',
            exclude_properties=True,
            asset_model_version='ACTIVE',
        )

        assert result['success'] is True
        mock_client.describe_asset_model.assert_called_once_with(
            assetModelId='test-model-123',
            assetModelVersion='ACTIVE',
            excludeProperties=True,
        )

    def test_list_asset_models_validation_errors(self):
        """Test list asset models validation error cases."""
        # Test next token too long
        # Exceeds 4096 character limit
        result = list_asset_models(
            region='us-east-1',
            next_token='x' * 4097,
            max_results=50,
            asset_model_types=None,
        )
        assert result['success'] is False
        assert 'Next token too long' in result['error']

        # Test invalid asset model type
        result = list_asset_models(
            region='us-east-1',
            next_token=None,
            max_results=50,
            asset_model_types=['INVALID_TYPE'],
        )
        assert result['success'] is False
        assert "Asset model type must be 'ASSET_MODEL' or 'COMPONENT_MODEL'" in result['error']

    @patch(
        'awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_asset_models.create_sitewise_client'
    )
    def test_list_asset_models_with_all_params(self, mock_create_client):
        """Test list asset models with all optional parameters."""
        mock_client = Mock()
        mock_create_client.return_value = mock_client

        mock_response = {
            'assetModelSummaries': [{'id': 'model-1', 'name': 'Model 1'}],
            'nextToken': 'next-token-123',
        }
        mock_client.list_asset_models.return_value = mock_response

        result = list_asset_models(
            region='us-west-2',
            next_token='prev-token',
            max_results=100,
            asset_model_types=['ASSET_MODEL', 'COMPONENT_MODEL'],
        )

        assert result['success'] is True
        mock_client.list_asset_models.assert_called_once_with(
            maxResults=100,
            nextToken='prev-token',
            assetModelTypes=['ASSET_MODEL', 'COMPONENT_MODEL'],
        )

    def test_update_asset_model_validation_errors(self):
        """Test update asset model validation error cases."""
        # Test asset model description too long
        result = update_asset_model(
            asset_model_id='test-model-123',
            asset_model_name='Updated Model',
            region='us-east-1',
            asset_model_description='x' * 2049,  # Exceeds 2048 character limit
            asset_model_properties=None,
            asset_model_hierarchies=None,
            asset_model_composite_models=None,
            client_token=None,
            asset_model_external_id=None,
        )
        assert result['success'] is False
        assert 'Asset model description cannot exceed 2048 characters' in result['error']

        # Test client token too long
        result = update_asset_model(
            asset_model_id='test-model-123',
            asset_model_name='Updated Model',
            region='us-east-1',
            asset_model_description=None,
            asset_model_properties=None,
            asset_model_hierarchies=None,
            asset_model_composite_models=None,
            client_token='x' * 65,  # Exceeds 64 character limit
            asset_model_external_id=None,
        )
        assert result['success'] is False
        assert 'Client token cannot exceed 64 characters' in result['error']

        # Test too many hierarchies
        too_many_hierarchies = [{'name': f'hierarchy{i}'} for i in range(11)]  # Exceeds 10 limit
        result = update_asset_model(
            asset_model_id='test-model-123',
            asset_model_name='Updated Model',
            region='us-east-1',
            asset_model_description=None,
            asset_model_properties=None,
            asset_model_hierarchies=too_many_hierarchies,
            asset_model_composite_models=None,
            client_token=None,
            asset_model_external_id=None,
        )
        assert result['success'] is False
        assert 'Cannot have more than 10 hierarchies per asset model' in result['error']

        # Test too many composite models
        too_many_composite = [{'name': f'composite{i}'} for i in range(11)]  # Exceeds 10 limit
        result = update_asset_model(
            asset_model_id='test-model-123',
            asset_model_name='Updated Model',
            region='us-east-1',
            asset_model_description=None,
            asset_model_properties=None,
            asset_model_hierarchies=None,
            asset_model_composite_models=too_many_composite,
            client_token=None,
            asset_model_external_id=None,
        )
        assert result['success'] is False
        assert 'Cannot have more than 10 composite models per asset model' in result['error']

    @patch(
        'awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_asset_models.validate_asset_model_properties'
    )
    @patch(
        'awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_asset_models.create_sitewise_client'
    )
    def test_update_asset_model_with_all_params(self, mock_create_client, mock_validate_props):
        """Test update asset model with all optional parameters."""
        mock_client = Mock()
        mock_create_client.return_value = mock_client
        # Mock the validation to pass
        mock_validate_props.return_value = None

        mock_response = {'assetModelStatus': {'state': 'UPDATING'}}
        mock_client.update_asset_model.return_value = mock_response

        result = update_asset_model(
            asset_model_id='test-model-123',
            asset_model_name='Updated Model',
            region='us-west-2',
            asset_model_description='Updated description',
            asset_model_properties=[{'name': 'property1', 'dataType': 'DOUBLE'}],
            asset_model_hierarchies=[{'name': 'hierarchy1'}],
            asset_model_composite_models=[{'name': 'composite1'}],
            client_token='update-token',
            asset_model_external_id='ext-456',
        )

        assert result['success'] is True
        mock_client.update_asset_model.assert_called_once_with(
            assetModelId='test-model-123',
            assetModelName='Updated Model',
            assetModelDescription='Updated description',
            assetModelProperties=[{'name': 'property1', 'dataType': 'DOUBLE'}],
            assetModelHierarchies=[{'name': 'hierarchy1'}],
            assetModelCompositeModels=[{'name': 'composite1'}],
            clientToken='update-token',
            assetModelExternalId='ext-456',
        )

    def test_delete_asset_model_validation_errors(self):
        """Test delete asset model validation error cases."""
        # Test client token too long
        result = delete_asset_model(
            asset_model_id='test-model-123',
            region='us-east-1',
            client_token='x' * 65,  # Exceeds 64 character limit
        )
        assert result['success'] is False
        assert 'Client token cannot exceed 64 characters' in result['error']

    @patch(
        'awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_asset_models.create_sitewise_client'
    )
    def test_delete_asset_model_with_client_token(self, mock_create_client):
        """Test delete asset model with client token."""
        mock_client = Mock()
        mock_create_client.return_value = mock_client

        mock_response = {'assetModelStatus': {'state': 'DELETING'}}
        mock_client.delete_asset_model.return_value = mock_response

        result = delete_asset_model(
            asset_model_id='test-model-123',
            region='us-west-2',
            client_token='delete-token',
        )

        assert result['success'] is True
        mock_client.delete_asset_model.assert_called_once_with(
            assetModelId='test-model-123', clientToken='delete-token'
        )

    def test_list_asset_model_properties_validation_errors(self):
        """Test list asset model properties validation error cases."""
        # Test next token too long
        result = list_asset_model_properties(
            asset_model_id='test-model-123',
            region='us-east-1',
            next_token='x' * 4097,  # Exceeds 4096 character limit
            max_results=50,
            asset_model_version='LATEST',
            filter_type=None,
        )
        assert result['success'] is False
        assert 'Next token too long' in result['error']

        # Test invalid asset model version
        result = list_asset_model_properties(
            asset_model_id='test-model-123',
            region='us-east-1',
            next_token=None,
            max_results=50,
            asset_model_version='INVALID_VERSION',
            filter_type=None,
        )
        assert result['success'] is False
        assert "Asset model version must be 'LATEST' or 'ACTIVE'" in result['error']

        # Test invalid filter type
        result = list_asset_model_properties(
            asset_model_id='test-model-123',
            region='us-east-1',
            next_token=None,
            max_results=50,
            asset_model_version='LATEST',
            filter_type='INVALID_FILTER',
        )
        assert result['success'] is False
        assert "Filter type must be 'ALL' or 'BASE'" in result['error']

    @patch(
        'awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_asset_models.create_sitewise_client'
    )
    def test_list_asset_model_properties_with_all_params(self, mock_create_client):
        """Test list asset model properties with all optional parameters."""
        mock_client = Mock()
        mock_create_client.return_value = mock_client

        mock_response = {
            'assetModelPropertySummaries': [{'id': 'prop-1', 'name': 'Property 1'}],
            'nextToken': 'next-token-123',
        }
        mock_client.list_asset_model_properties.return_value = mock_response

        result = list_asset_model_properties(
            asset_model_id='test-model-123',
            region='us-west-2',
            next_token='prev-token',
            max_results=100,
            asset_model_version='ACTIVE',
            filter_type='BASE',
        )

        assert result['success'] is True
        mock_client.list_asset_model_properties.assert_called_once_with(
            assetModelId='test-model-123',
            maxResults=100,
            assetModelVersion='ACTIVE',
            nextToken='prev-token',
            filter='BASE',
        )

    def test_create_asset_model_composite_model_validation_errors(self):
        """Test create asset model composite model validation error cases."""
        # Test composite model description too long
        result = create_asset_model_composite_model(
            asset_model_id='test-model-123',
            asset_model_composite_model_name='Test Composite',
            asset_model_composite_model_type='alarms',
            region='us-east-1',
            asset_model_composite_model_description='x' * 2049,  # Exceeds 2048 character limit
            asset_model_composite_model_properties=None,
            client_token=None,
            asset_model_composite_model_id=None,
            asset_model_composite_model_external_id=None,
            parent_asset_model_composite_model_id=None,
            composed_asset_model_id=None,
        )
        assert result['success'] is False
        assert 'Composite model description cannot exceed 2048 characters' in result['error']

        # Test client token too long
        result = create_asset_model_composite_model(
            asset_model_id='test-model-123',
            asset_model_composite_model_name='Test Composite',
            asset_model_composite_model_type='alarms',
            region='us-east-1',
            asset_model_composite_model_description=None,
            asset_model_composite_model_properties=None,
            client_token='x' * 65,  # Exceeds 64 character limit
            asset_model_composite_model_id=None,
            asset_model_composite_model_external_id=None,
            parent_asset_model_composite_model_id=None,
            composed_asset_model_id=None,
        )
        assert result['success'] is False
        assert 'Client token cannot exceed 64 characters' in result['error']

        # Test too many properties in composite model
        too_many_properties = [{'name': f'prop{i}'} for i in range(201)]  # Exceeds 200 limit
        result = create_asset_model_composite_model(
            asset_model_id='test-model-123',
            asset_model_composite_model_name='Test Composite',
            asset_model_composite_model_type='alarms',
            region='us-east-1',
            asset_model_composite_model_description=None,
            asset_model_composite_model_properties=too_many_properties,
            client_token=None,
            asset_model_composite_model_id=None,
            asset_model_composite_model_external_id=None,
            parent_asset_model_composite_model_id=None,
            composed_asset_model_id=None,
        )
        assert result['success'] is False
        assert 'Cannot have more than 200 properties per composite model' in result['error']

    @patch(
        'awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_asset_models.create_sitewise_client'
    )
    def test_create_asset_model_composite_model_with_all_params(self, mock_create_client):
        """Test create asset model composite model with all optional parameters."""
        mock_client = Mock()
        mock_create_client.return_value = mock_client

        mock_response = {
            'assetModelCompositeModelId': 'composite-123',
            'assetModelCompositeModelPath': ['path1', 'path2'],
            'assetModelStatus': {'state': 'UPDATING'},
        }
        mock_client.create_asset_model_composite_model.return_value = mock_response

        result = create_asset_model_composite_model(
            asset_model_id='test-model-123',
            asset_model_composite_model_name='Test Composite',
            asset_model_composite_model_type='alarms',
            region='us-west-2',
            asset_model_composite_model_description='Test composite description',
            asset_model_composite_model_properties=[{'name': 'property1', 'dataType': 'DOUBLE'}],
            client_token='composite-token',
            asset_model_composite_model_id='custom-composite-id',
            asset_model_composite_model_external_id='ext-composite-123',
            parent_asset_model_composite_model_id='parent-composite-123',
            composed_asset_model_id='composed-model-123',
        )

        assert result['success'] is True
        mock_client.create_asset_model_composite_model.assert_called_once_with(
            assetModelId='test-model-123',
            assetModelCompositeModelName='Test Composite',
            assetModelCompositeModelType='alarms',
            assetModelCompositeModelDescription='Test composite description',
            assetModelCompositeModelProperties=[{'name': 'property1', 'dataType': 'DOUBLE'}],
            clientToken='composite-token',
            assetModelCompositeModelId='custom-composite-id',
            assetModelCompositeModelExternalId='ext-composite-123',
            parentAssetModelCompositeModelId='parent-composite-123',
            composedAssetModelId='composed-model-123',
        )

    @patch(
        'awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_asset_models.create_sitewise_client'
    )
    def test_all_functions_client_error_handling(self, mock_create_client):
        """Test that all functions handle ClientError exceptions properly."""
        mock_client = Mock()
        mock_create_client.return_value = mock_client

        error_response = {
            'Error': {
                'Code': 'InternalFailureException',
                'Message': 'Internal server error',
            }
        }

        # Test describe_asset_model error handling
        mock_client.describe_asset_model.side_effect = ClientError(
            error_response, 'DescribeAssetModel'
        )
        result = describe_asset_model(
            asset_model_id='test-123',
            region='us-east-1',
            exclude_properties=False,
            asset_model_version='LATEST',
        )
        assert result['success'] is False
        assert result['error_code'] == 'InternalFailureException'

        # Test list_asset_models error handling
        mock_client.list_asset_models.side_effect = ClientError(error_response, 'ListAssetModels')
        result = list_asset_models(
            region='us-east-1',
            next_token=None,
            max_results=50,
            asset_model_types=None,
        )
        assert result['success'] is False
        assert result['error_code'] == 'InternalFailureException'

        # Test update_asset_model error handling
        mock_client.update_asset_model.side_effect = ClientError(
            error_response, 'UpdateAssetModel'
        )
        result = update_asset_model(
            asset_model_id='test-123',
            asset_model_name='Updated',
            region='us-east-1',
            asset_model_description=None,
            asset_model_properties=None,
            asset_model_hierarchies=None,
            asset_model_composite_models=None,
            client_token=None,
            asset_model_external_id=None,
        )
        assert result['success'] is False
        assert result['error_code'] == 'InternalFailureException'

        # Test delete_asset_model error handling
        mock_client.delete_asset_model.side_effect = ClientError(
            error_response, 'DeleteAssetModel'
        )
        result = delete_asset_model(
            asset_model_id='test-123',
            region='us-east-1',
            client_token=None,
        )
        assert result['success'] is False
        assert result['error_code'] == 'InternalFailureException'

        # Test list_asset_model_properties error handling
        mock_client.list_asset_model_properties.side_effect = ClientError(
            error_response, 'ListAssetModelProperties'
        )
        result = list_asset_model_properties(
            asset_model_id='test-123',
            region='us-east-1',
            next_token=None,
            max_results=50,
            asset_model_version='LATEST',
            filter_type=None,
        )
        assert result['success'] is False
        assert result['error_code'] == 'InternalFailureException'

        # Test create_asset_model_composite_model error handling
        mock_client.create_asset_model_composite_model.side_effect = ClientError(
            error_response, 'CreateAssetModelCompositeModel'
        )
        result = create_asset_model_composite_model(
            asset_model_id='test-123',
            asset_model_composite_model_name='Test Composite',
            asset_model_composite_model_type='alarms',
            region='us-east-1',
            asset_model_composite_model_description=None,
            asset_model_composite_model_properties=None,
            client_token=None,
            asset_model_composite_model_id=None,
            asset_model_composite_model_external_id=None,
            parent_asset_model_composite_model_id=None,
            composed_asset_model_id=None,
        )
        assert result['success'] is False
        assert result['error_code'] == 'InternalFailureException'


if __name__ == '__main__':
    pytest.main([__file__])
