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

"""Tests for AWS IoT SiteWise Access Management Tools."""

import os
import pytest
import sys
from awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_access import (
    describe_default_encryption_configuration,
    describe_logging_options,
    describe_storage_configuration,
    put_default_encryption_configuration,
    put_logging_options,
    put_storage_configuration,
)
from botocore.exceptions import ClientError
from unittest.mock import Mock, patch


# Add the project root directory and its parent to Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(script_dir)
sys.path.insert(0, project_dir)
sys.path.insert(0, os.path.dirname(project_dir))
sys.path.insert(0, os.path.dirname(os.path.dirname(project_dir)))


class TestSiteWiseAccess:
    """Test cases for SiteWise access management tools."""

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_access.create_sitewise_client')
    def test_describe_default_encryption_configuration_success(self, mock_boto_client):
        """Test successful encryption configuration description."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        mock_response = {
            'encryptionType': 'SITEWISE_DEFAULT_ENCRYPTION',
            'kmsKeyId': '',
            'configurationStatus': {'state': 'ACTIVE'},
        }
        mock_client.describe_default_encryption_configuration.return_value = mock_response

        result = describe_default_encryption_configuration(region='us-east-1')

        assert result['success'] is True
        assert result['encryption_type'] == 'SITEWISE_DEFAULT_ENCRYPTION'

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_access.create_sitewise_client')
    def test_put_default_encryption_configuration_success(self, mock_boto_client):
        """Test successful encryption configuration update."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        mock_response = {
            'encryptionType': 'KMS_BASED_ENCRYPTION',
            'kmsKeyId': 'arn:aws:kms:us-east-1:123456789012:key/test-key',
            'configurationStatus': {'state': 'UPDATING'},
        }
        mock_client.put_default_encryption_configuration.return_value = mock_response

        result = put_default_encryption_configuration(
            encryption_type='KMS_BASED_ENCRYPTION',
            kms_key_id='arn:aws:kms:us-east-1:123456789012:key/test-key',
            region='us-east-1',
        )

        assert result['success'] is True
        assert result['encryption_type'] == 'KMS_BASED_ENCRYPTION'

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_access.create_sitewise_client')
    def test_describe_logging_options_success(self, mock_boto_client):
        """Test successful logging options description."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        mock_response = {'loggingOptions': {'level': 'INFO'}}
        mock_client.describe_logging_options.return_value = mock_response

        result = describe_logging_options(region='us-east-1')

        assert result['success'] is True
        assert 'logging_options' in result
        assert result['logging_options']['level'] == 'INFO'

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_access.create_sitewise_client')
    def test_put_logging_options_success(self, mock_boto_client):
        """Test successful logging options update."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        result = put_logging_options(
            logging_options={'level': 'ERROR'},
            region='us-east-1',
        )

        assert result['success'] is True
        assert 'successfully' in result['message']

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_access.create_sitewise_client')
    def test_describe_storage_configuration_success(self, mock_boto_client):
        """Test successful storage configuration description."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        mock_response = {
            'storageType': 'SITEWISE_DEFAULT_STORAGE',
            'configurationStatus': {'state': 'ACTIVE'},
        }
        mock_client.describe_storage_configuration.return_value = mock_response

        result = describe_storage_configuration(region='us-east-1')

        assert result['success'] is True
        assert result['storage_type'] == 'SITEWISE_DEFAULT_STORAGE'

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_access.create_sitewise_client')
    def test_put_storage_configuration_success(self, mock_boto_client):
        """Test successful storage configuration update."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        mock_response = {
            'storageType': 'MULTI_LAYER_STORAGE',
            'multiLayerStorage': {
                'customerManagedS3Storage': {'s3ResourceArn': 'arn:aws:s3:::test-bucket'}
            },
            'disassociatedDataStorage': 'ENABLED',
            'retentionPeriod': {'numberOfDays': 30},
            'configurationStatus': {'state': 'UPDATING'},
            'warmTier': 'ENABLED',
            'warmTierRetentionPeriod': {'numberOfDays': 90},
        }
        mock_client.put_storage_configuration.return_value = mock_response

        result = put_storage_configuration(
            storage_type='MULTI_LAYER_STORAGE',
            region='us-east-1',
        )

        assert result['success'] is True
        assert result['storage_type'] == 'MULTI_LAYER_STORAGE'

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_access.create_sitewise_client')
    def test_put_default_encryption_configuration_with_kms_key(self, mock_boto_client):
        """Test put default encryption configuration with KMS key parameter."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        mock_response = {
            'encryptionType': 'KMS_BASED_ENCRYPTION',
            'kmsKeyId': 'arn:aws:kms:us-east-1:<account-id>:key/test-key',
            'configurationStatus': {'state': 'ACTIVE'},
        }
        mock_client.put_default_encryption_configuration.return_value = mock_response

        # Test with KMS key
        result = put_default_encryption_configuration(
            encryption_type='KMS_BASED_ENCRYPTION',
            region='us-west-2',
            kms_key_id='arn:aws:kms:us-east-1:<account-id>:key/test-key56789012',
        )

        assert result['success'] is True
        assert result['encryption_type'] == 'KMS_BASED_ENCRYPTION'
        mock_client.put_default_encryption_configuration.assert_called_once_with(
            encryptionType='KMS_BASED_ENCRYPTION',
            kmsKeyId='arn:aws:kms:us-east-1:<account-id>:key/test-key56789012',
        )

        # Test without KMS key (SiteWise default)
        mock_client.reset_mock()
        mock_response['encryptionType'] = 'SITEWISE_DEFAULT_ENCRYPTION'
        mock_response.pop('kmsKeyId', None)
        result = put_default_encryption_configuration(
            encryption_type='SITEWISE_DEFAULT_ENCRYPTION', region='us-east-1', kms_key_id=None
        )

        assert result['success'] is True
        assert result['encryption_type'] == 'SITEWISE_DEFAULT_ENCRYPTION'
        mock_client.put_default_encryption_configuration.assert_called_once_with(
            encryptionType='SITEWISE_DEFAULT_ENCRYPTION'
        )

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_access.create_sitewise_client')
    def test_describe_storage_configuration_with_date_handling(self, mock_boto_client):
        """Test describe storage configuration with date handling."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        # Test with lastUpdateDate present
        mock_response = {
            'storageType': 'MULTI_LAYER_STORAGE',
            'multiLayerStorage': {
                'customerManagedS3Storage': {'s3ResourceArn': 'arn:aws:s3:::my-bucket'}
            },
            'disassociatedDataStorage': 'ENABLED',
            'retentionPeriod': {'numberOfDays': 30},
            'configurationStatus': {'state': 'ACTIVE'},
            'lastUpdateDate': Mock(),
        }
        mock_response['lastUpdateDate'].isoformat.return_value = '2023-01-01T00:00:00Z'
        mock_client.describe_storage_configuration.return_value = mock_response

        result = describe_storage_configuration(region='us-west-2')

        assert result['success'] is True
        assert result['last_update_date'] == '2023-01-01T00:00:00Z'

        # Test without lastUpdateDate
        mock_client.reset_mock()
        mock_response.pop('lastUpdateDate', None)
        result = describe_storage_configuration(region='us-east-1')

        assert result['success'] is True
        assert result['last_update_date'] == ''

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_access.create_sitewise_client')
    def test_put_storage_configuration_with_all_params(self, mock_boto_client):
        """Test put storage configuration with all optional parameters."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        mock_response = {
            'storageType': 'MULTI_LAYER_STORAGE',
            'multiLayerStorage': {
                'customerManagedS3Storage': {'s3ResourceArn': 'arn:aws:s3:::my-bucket'}
            },
            'disassociatedDataStorage': 'ENABLED',
            'retentionPeriod': {'numberOfDays': 30},
            'configurationStatus': {'state': 'ACTIVE'},
            'warmTier': 'ENABLED',
            'warmTierRetentionPeriod': {'numberOfDays': 7},
        }
        mock_client.put_storage_configuration.return_value = mock_response

        multi_layer_storage = {
            'customerManagedS3Storage': {'s3ResourceArn': 'arn:aws:s3:::my-bucket'}
        }
        retention_period = {'numberOfDays': 30}
        warm_tier_retention_period = {'numberOfDays': 7}

        # Test with all parameters
        result = put_storage_configuration(
            storage_type='MULTI_LAYER_STORAGE',
            region='us-west-2',
            multi_layer_storage=multi_layer_storage,
            disassociated_data_storage='ENABLED',
            retention_period=retention_period,
            warm_tier='ENABLED',
            warm_tier_retention_period=warm_tier_retention_period,
        )

        assert result['success'] is True
        mock_client.put_storage_configuration.assert_called_once_with(
            storageType='MULTI_LAYER_STORAGE',
            disassociatedDataStorage='ENABLED',
            warmTier='ENABLED',
            multiLayerStorage=multi_layer_storage,
            retentionPeriod=retention_period,
            warmTierRetentionPeriod=warm_tier_retention_period,
        )

        # Test with minimal parameters
        mock_client.reset_mock()
        result = put_storage_configuration(
            storage_type='SITEWISE_DEFAULT_STORAGE',
            region='us-east-1',
            multi_layer_storage=None,
            disassociated_data_storage='ENABLED',
            retention_period=None,
            warm_tier='ENABLED',
            warm_tier_retention_period=None,
        )

        assert result['success'] is True
        mock_client.put_storage_configuration.assert_called_once_with(
            storageType='SITEWISE_DEFAULT_STORAGE',
            disassociatedDataStorage='ENABLED',
            warmTier='ENABLED',
        )

    @patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_access.create_sitewise_client')
    def test_all_functions_client_error_handling(self, mock_boto_client):
        """Test that all functions handle ClientError exceptions properly."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        error_response = {
            'Error': {
                'Code': 'InternalFailureException',
                'Message': 'Internal server error',
            }
        }

        # Test describe_default_encryption_configuration error handling
        mock_client.describe_default_encryption_configuration.side_effect = ClientError(
            error_response, 'DescribeDefaultEncryptionConfiguration'
        )
        result = describe_default_encryption_configuration()
        assert result['success'] is False
        assert result['error_code'] == 'InternalFailureException'

        # Test put_default_encryption_configuration error handling
        mock_client.put_default_encryption_configuration.side_effect = ClientError(
            error_response, 'PutDefaultEncryptionConfiguration'
        )
        result = put_default_encryption_configuration(
            encryption_type='SITEWISE_DEFAULT_ENCRYPTION'
        )
        assert result['success'] is False
        assert result['error_code'] == 'InternalFailureException'

        # Test describe_logging_options error handling
        mock_client.describe_logging_options.side_effect = ClientError(
            error_response, 'DescribeLoggingOptions'
        )
        result = describe_logging_options()
        assert result['success'] is False
        assert result['error_code'] == 'InternalFailureException'

        # Test put_logging_options error handling
        mock_client.put_logging_options.side_effect = ClientError(
            error_response, 'PutLoggingOptions'
        )
        result = put_logging_options(logging_options={'level': 'INFO'})
        assert result['success'] is False
        assert result['error_code'] == 'InternalFailureException'

        # Test describe_storage_configuration error handling
        mock_client.describe_storage_configuration.side_effect = ClientError(
            error_response, 'DescribeStorageConfiguration'
        )
        result = describe_storage_configuration()
        assert result['success'] is False
        assert result['error_code'] == 'InternalFailureException'

        # Test put_storage_configuration error handling
        mock_client.put_storage_configuration.side_effect = ClientError(
            error_response, 'PutStorageConfiguration'
        )
        result = put_storage_configuration(storage_type='SITEWISE_DEFAULT_STORAGE')
        assert result['success'] is False
        assert result['error_code'] == 'InternalFailureException'


if __name__ == '__main__':
    pytest.main([__file__])
