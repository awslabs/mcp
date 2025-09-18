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

"""Tests for AWS IoT SiteWise Asset Management Tools."""

import os
import pytest
import sys
from awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_assets import (
    associate_assets,
    create_asset,
    delete_asset,
    describe_asset,
    disassociate_assets,
    list_assets,
    list_associated_assets,
    update_asset,
)
from botocore.exceptions import ClientError
from unittest.mock import Mock, patch


# Add the project root directory and its parent to Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(script_dir)
sys.path.insert(0, project_dir)
sys.path.insert(0, os.path.dirname(project_dir))
sys.path.insert(0, os.path.dirname(os.path.dirname(project_dir)))


class TestSiteWiseAssets:
    """Test cases for SiteWise asset management tools."""

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_assets.create_sitewise_client')
    def test_create_asset_success(self, mock_boto_client):
        """Test successful asset creation."""
        # Mock the boto3 client
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        # Mock the response
        mock_response = {
            'assetId': 'test-asset-123',
            'assetArn': 'arn:aws:iotsitewise:us-east-1:123456789012:asset/test-asset-123',
            'assetStatus': {'state': 'CREATING'},
        }
        mock_client.create_asset.return_value = mock_response

        # Call the function
        result = create_asset(
            asset_name='Test Asset',
            asset_model_id='test-model-456',
            region='us-east-1',
            client_token=None,
            tags=None,
            asset_description=None,
            asset_id=None,
            asset_external_id=None,
        )

        # Verify the result
        assert result['success'] is True
        assert result['asset_id'] == 'test-asset-123'
        assert (
            result['asset_arn']
            == 'arn:aws:iotsitewise:us-east-1:123456789012:asset/test-asset-123'
        )

        # Verify the client was called correctly
        mock_client.create_asset.assert_called_once_with(
            assetName='Test Asset', assetModelId='test-model-456'
        )

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_assets.create_sitewise_client')
    def test_create_asset_failure(self, mock_boto_client):
        """Test asset creation failure."""
        # Mock the boto3 client
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        # Mock a ClientError
        error_response = {
            'Error': {
                'Code': 'ResourceNotFoundException',
                'Message': 'Asset model not found',
            }
        }
        mock_client.create_asset.side_effect = ClientError(error_response, 'CreateAsset')

        # Call the function
        result = create_asset(
            asset_name='Test Asset',
            asset_model_id='nonexistent-model',
            region='us-east-1',
            client_token=None,
            tags=None,
            asset_description=None,
            asset_id=None,
            asset_external_id=None,
        )

        # Verify the result
        assert result['success'] is False
        assert result['error_code'] == 'ResourceNotFoundException'
        assert 'Asset model not found' in result['error']

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_assets.create_sitewise_client')
    def test_create_asset_with_optional_params(self, mock_boto_client):
        """Test asset creation with optional parameters."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        mock_response = {
            'assetId': 'test-asset-123',
            'assetArn': 'arn:aws:iotsitewise:us-east-1:123456789012:asset/test-asset-123',
            'assetStatus': {'state': 'CREATING'},
        }
        mock_client.create_asset.return_value = mock_response

        result = create_asset(
            asset_name='Test Asset',
            asset_model_id='test-model-456',
            region='us-east-1',
            client_token='test-token',
            tags={'Environment': 'Test'},
            asset_description='Test description',
            asset_id='custom-id',
            asset_external_id='external-123',
        )

        assert result['success'] is True
        mock_client.create_asset.assert_called_once_with(
            assetName='Test Asset',
            assetModelId='test-model-456',
            clientToken='test-token',
            tags={'Environment': 'Test'},
            assetDescription='Test description',
            assetId='custom-id',
            assetExternalId='external-123',
        )

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_assets.create_sitewise_client')
    def test_describe_asset_success(self, mock_boto_client):
        """Test successful asset description."""
        # Mock the boto3 client
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        # Mock the response
        mock_response = {
            'assetId': 'test-asset-123',
            'assetArn': 'arn:aws:iotsitewise:us-east-1:123456789012:asset/test-asset-123',
            'assetName': 'Test Asset',
            'assetModelId': 'test-model-456',
            'assetProperties': [],
            'assetHierarchies': [],
            'assetCompositeModels': [],
            'assetStatus': {'state': 'ACTIVE'},
            'assetCreationDate': Mock(),
            'assetLastUpdateDate': Mock(),
            'assetDescription': 'Test asset description',
        }
        mock_response['assetCreationDate'].isoformat.return_value = '2023-01-01T00:00:00Z'
        mock_response['assetLastUpdateDate'].isoformat.return_value = '2023-01-01T00:00:00Z'
        mock_client.describe_asset.return_value = mock_response

        # Call the function
        result = describe_asset(
            asset_id='test-asset-123',
            region='us-east-1',
            exclude_properties=False,
        )

        # Verify the result
        assert result['success'] is True
        assert result['asset_id'] == 'test-asset-123'
        assert result['asset_name'] == 'Test Asset'
        assert result['asset_model_id'] == 'test-model-456'

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_assets.create_sitewise_client')
    def test_list_assets_success(self, mock_boto_client):
        """Test successful asset listing."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        mock_response = {
            'assetSummaries': [
                {'id': 'asset-1', 'name': 'Asset 1'},
                {'id': 'asset-2', 'name': 'Asset 2'},
            ],
            'nextToken': 'next-token-123',
        }
        mock_client.list_assets.return_value = mock_response

        result = list_assets(
            region='us-east-1',
            next_token=None,
            max_results=10,
            asset_model_id=None,
            filter_type=None,
        )

        assert result['success'] is True
        assert len(result['asset_summaries']) == 2
        assert result['next_token'] == 'next-token-123'

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_assets.create_sitewise_client')
    def test_update_asset_success(self, mock_boto_client):
        """Test successful asset update."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        mock_response = {'assetStatus': {'state': 'UPDATING'}}
        mock_client.update_asset.return_value = mock_response

        result = update_asset(
            asset_id='test-asset-123',
            asset_name='Updated Asset',
            region='us-east-1',
            client_token=None,
            asset_description=None,
            asset_external_id=None,
        )

        assert result['success'] is True
        assert result['asset_status']['state'] == 'UPDATING'

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_assets.create_sitewise_client')
    def test_delete_asset_success(self, mock_boto_client):
        """Test successful asset deletion."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        mock_response = {'assetStatus': {'state': 'DELETING'}}
        mock_client.delete_asset.return_value = mock_response

        result = delete_asset(
            asset_id='test-asset-123',
            region='us-east-1',
            client_token=None,
        )

        assert result['success'] is True
        assert result['asset_status']['state'] == 'DELETING'

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_assets.create_sitewise_client')
    def test_associate_assets_success(self, mock_boto_client):
        """Test successful asset association."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        result = associate_assets(
            asset_id='parent-asset-123',
            hierarchy_id='hierarchy-456',
            child_asset_id='child-asset-789',
            region='us-east-1',
            client_token=None,
        )

        assert result['success'] is True
        assert 'successfully' in result['message']

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_assets.create_sitewise_client')
    def test_disassociate_assets_success(self, mock_boto_client):
        """Test successful asset disassociation."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        result = disassociate_assets(
            asset_id='parent-asset-123',
            hierarchy_id='hierarchy-456',
            child_asset_id='child-asset-789',
            region='us-east-1',
            client_token=None,
        )

        assert result['success'] is True
        assert 'successfully' in result['message']

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_assets.create_sitewise_client')
    def test_list_associated_assets_success(self, mock_boto_client):
        """Test successful associated assets listing."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        mock_response = {
            'assetSummaries': [{'id': 'child-1'}, {'id': 'child-2'}],
            'nextToken': 'token-123',
        }
        mock_client.list_associated_assets.return_value = mock_response

        result = list_associated_assets(
            asset_id='parent-asset-123',
            region='us-east-1',
            hierarchy_id=None,
            traversal_direction='PARENT',
            next_token=None,
            max_results=50,
        )

        assert result['success'] is True
        assert len(result['asset_summaries']) == 2

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_assets.create_sitewise_client')
    def test_client_error_handling(self, mock_boto_client):
        """Test that ClientError exceptions are properly handled."""
        # Mock the boto3 client
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        # Mock various types of errors
        error_cases = [
            ('ResourceNotFoundException', 'Resource not found'),
            ('InvalidRequestException', 'Invalid request'),
            ('ThrottlingException', 'Request throttled'),
            ('InternalFailureException', 'Internal server error'),
        ]

        for error_code, error_message in error_cases:
            error_response = {'Error': {'Code': error_code, 'Message': error_message}}
            mock_client.create_asset.side_effect = ClientError(error_response, 'CreateAsset')

            # Call the function
            result = create_asset(
                asset_name='Test Asset',
                asset_model_id='test-model',
                region='us-east-1',
                client_token=None,
                tags=None,
                asset_description=None,
                asset_id=None,
                asset_external_id=None,
            )

            # Verify error handling
            assert result['success'] is False
            assert result['error_code'] == error_code
            assert error_message in result['error']

    def test_create_asset_validation_errors(self):
        """Test create asset validation error cases."""
        # Test asset description too long
        result = create_asset(
            asset_name='Test Asset',
            asset_model_id='test-model-456',
            region='us-east-1',
            client_token=None,
            tags=None,
            asset_description='x' * 2049,  # Exceeds 2048 character limit
            asset_id=None,
            asset_external_id=None,
        )
        assert result['success'] is False
        assert 'Asset description cannot exceed 2048 characters' in result['error']

        # Test client token too long
        result = create_asset(
            asset_name='Test Asset',
            asset_model_id='test-model-456',
            region='us-east-1',
            client_token='x' * 65,  # Exceeds 64 character limit
            tags=None,
            asset_description=None,
            asset_id=None,
            asset_external_id=None,
        )
        assert result['success'] is False
        assert 'Client token cannot exceed 64 characters' in result['error']

        # Test too many tags
        # Exceeds 50 tag limit
        too_many_tags = {f'key{i}': f'value{i}' for i in range(51)}
        result = create_asset(
            asset_name='Test Asset',
            asset_model_id='test-model-456',
            region='us-east-1',
            client_token=None,
            tags=too_many_tags,
            asset_description=None,
            asset_id=None,
            asset_external_id=None,
        )
        assert result['success'] is False
        assert 'Cannot have more than 50 tags per asset' in result['error']

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_assets.create_sitewise_client')
    def test_describe_asset_with_exclude_properties(self, mock_boto_client):
        """Test describe asset with exclude_properties parameter."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        mock_response = {
            'assetId': 'test-asset-123',
            'assetArn': 'arn:aws:iotsitewise:us-east-1:123456789012:asset/test-asset-123',
            'assetName': 'Test Asset',
            'assetModelId': 'test-model-456',
            'assetStatus': {'state': 'ACTIVE'},
            'assetCreationDate': Mock(),
            'assetLastUpdateDate': Mock(),
        }
        mock_response['assetCreationDate'].isoformat.return_value = '2023-01-01T00:00:00Z'
        mock_response['assetLastUpdateDate'].isoformat.return_value = '2023-01-01T00:00:00Z'
        mock_client.describe_asset.return_value = mock_response

        result = describe_asset(
            asset_id='test-asset-123',
            region='us-east-1',
            exclude_properties=True,
        )

        assert result['success'] is True
        mock_client.describe_asset.assert_called_once_with(
            assetId='test-asset-123', excludeProperties=True
        )

    def test_list_assets_validation_errors(self):
        """Test list assets validation error cases."""
        # Test invalid filter type
        result = list_assets(
            region='us-east-1',
            next_token=None,
            max_results=50,
            asset_model_id=None,
            filter_type='INVALID_FILTER',
        )
        assert result['success'] is False
        assert "Filter type must be 'ALL' or 'TOP_LEVEL'" in result['error']

        # Test next token too long
        # Exceeds 4096 character limit
        result = list_assets(
            region='us-east-1',
            next_token='x' * 4097,
            max_results=50,
            asset_model_id=None,
            filter_type=None,
        )
        assert result['success'] is False
        assert 'Next token too long' in result['error']

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_assets.create_sitewise_client')
    def test_list_assets_with_all_params(self, mock_boto_client):
        """Test list assets with all optional parameters."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        mock_response = {
            'assetSummaries': [{'id': 'asset-1', 'name': 'Asset 1'}],
            'nextToken': 'next-token-123',
        }
        mock_client.list_assets.return_value = mock_response

        result = list_assets(
            region='us-west-2',
            next_token='prev-token',
            max_results=100,
            asset_model_id='model-123',
            filter_type='TOP_LEVEL',
        )

        assert result['success'] is True
        mock_client.list_assets.assert_called_once_with(
            maxResults=100,
            nextToken='prev-token',
            assetModelId='model-123',
            filter='TOP_LEVEL',
        )

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_assets.create_sitewise_client')
    def test_update_asset_with_all_params(self, mock_boto_client):
        """Test update asset with all optional parameters."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        mock_response = {'assetStatus': {'state': 'UPDATING'}}
        mock_client.update_asset.return_value = mock_response

        result = update_asset(
            asset_id='test-asset-123',
            asset_name='Updated Asset',
            region='us-west-2',
            client_token='update-token',
            asset_description='Updated description',
            asset_external_id='ext-123',
        )

        assert result['success'] is True
        mock_client.update_asset.assert_called_once_with(
            assetId='test-asset-123',
            assetName='Updated Asset',
            clientToken='update-token',
            assetDescription='Updated description',
            assetExternalId='ext-123',
        )

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_assets.create_sitewise_client')
    def test_delete_asset_with_client_token(self, mock_boto_client):
        """Test delete asset with client token."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        mock_response = {'assetStatus': {'state': 'DELETING'}}
        mock_client.delete_asset.return_value = mock_response

        result = delete_asset(
            asset_id='test-asset-123', region='us-west-2', client_token='delete-token'
        )

        assert result['success'] is True
        mock_client.delete_asset.assert_called_once_with(
            assetId='test-asset-123', clientToken='delete-token'
        )

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_assets.create_sitewise_client')
    def test_associate_assets_with_client_token(self, mock_boto_client):
        """Test associate assets with client token."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        result = associate_assets(
            asset_id='parent-asset-123',
            hierarchy_id='hierarchy-456',
            child_asset_id='child-asset-789',
            region='us-west-2',
            client_token='associate-token',
        )

        assert result['success'] is True
        mock_client.associate_assets.assert_called_once_with(
            assetId='parent-asset-123',
            hierarchyId='hierarchy-456',
            childAssetId='child-asset-789',
            clientToken='associate-token',
        )

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_assets.create_sitewise_client')
    def test_disassociate_assets_with_client_token(self, mock_boto_client):
        """Test disassociate assets with client token."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        result = disassociate_assets(
            asset_id='parent-asset-123',
            hierarchy_id='hierarchy-456',
            child_asset_id='child-asset-789',
            region='us-west-2',
            client_token='disassociate-token',
        )

        assert result['success'] is True
        mock_client.disassociate_assets.assert_called_once_with(
            assetId='parent-asset-123',
            hierarchyId='hierarchy-456',
            childAssetId='child-asset-789',
            clientToken='disassociate-token',
        )

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_assets.create_sitewise_client')
    def test_list_associated_assets_with_all_params(self, mock_boto_client):
        """Test list associated assets with all optional parameters."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        mock_response = {
            'assetSummaries': [{'id': 'child-1'}, {'id': 'child-2'}],
            'nextToken': 'token-123',
        }
        mock_client.list_associated_assets.return_value = mock_response

        result = list_associated_assets(
            asset_id='parent-asset-123',
            region='us-west-2',
            hierarchy_id='hierarchy-456',
            traversal_direction='CHILD',
            next_token='prev-token',
            max_results=25,
        )

        assert result['success'] is True
        mock_client.list_associated_assets.assert_called_once_with(
            assetId='parent-asset-123',
            traversalDirection='CHILD',
            maxResults=25,
            hierarchyId='hierarchy-456',
            nextToken='prev-token',
        )

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_assets.create_sitewise_client')
    def test_additional_client_error_handling(self, mock_boto_client):
        """Test additional ClientError handling for all functions."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        error_response = {
            'Error': {
                'Code': 'InternalFailureException',
                'Message': 'Internal server error',
            }
        }

        # Test describe_asset error handling
        mock_client.describe_asset.side_effect = ClientError(error_response, 'DescribeAsset')
        result = describe_asset(
            asset_id='test-123',
            region='us-east-1',
            exclude_properties=False,
        )
        assert result['success'] is False
        assert result['error_code'] == 'InternalFailureException'

        # Test list_assets error handling
        mock_client.list_assets.side_effect = ClientError(error_response, 'ListAssets')
        result = list_assets(
            region='us-east-1',
            next_token=None,
            max_results=50,
            asset_model_id=None,
            filter_type=None,
        )
        assert result['success'] is False
        assert result['error_code'] == 'InternalFailureException'

        # Test update_asset error handling
        mock_client.update_asset.side_effect = ClientError(error_response, 'UpdateAsset')
        result = update_asset(
            asset_id='test-123',
            asset_name='Updated',
            region='us-east-1',
            client_token=None,
            asset_description=None,
            asset_external_id=None,
        )
        assert result['success'] is False
        assert result['error_code'] == 'InternalFailureException'

        # Test delete_asset error handling
        mock_client.delete_asset.side_effect = ClientError(error_response, 'DeleteAsset')
        result = delete_asset(
            asset_id='test-123',
            region='us-east-1',
            client_token=None,
        )
        assert result['success'] is False
        assert result['error_code'] == 'InternalFailureException'

        # Test associate_assets error handling
        mock_client.associate_assets.side_effect = ClientError(error_response, 'AssociateAssets')
        result = associate_assets(
            asset_id='parent',
            hierarchy_id='hier',
            child_asset_id='child',
            region='us-east-1',
            client_token=None,
        )
        assert result['success'] is False
        assert result['error_code'] == 'InternalFailureException'

        # Test disassociate_assets error handling
        mock_client.disassociate_assets.side_effect = ClientError(
            error_response, 'DisassociateAssets'
        )
        result = disassociate_assets(
            asset_id='parent',
            hierarchy_id='hier',
            child_asset_id='child',
            region='us-east-1',
            client_token=None,
        )
        assert result['success'] is False
        assert result['error_code'] == 'InternalFailureException'

        # Test list_associated_assets error handling
        mock_client.list_associated_assets.side_effect = ClientError(
            error_response, 'ListAssociatedAssets'
        )
        result = list_associated_assets(
            asset_id='test-123',
            region='us-east-1',
            hierarchy_id=None,
            traversal_direction='PARENT',
            next_token=None,
            max_results=50,
        )
        assert result['success'] is False
        assert result['error_code'] == 'InternalFailureException'


if __name__ == '__main__':
    pytest.main([__file__])
