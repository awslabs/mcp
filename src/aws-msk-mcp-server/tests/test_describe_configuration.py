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

"""Tests for the describe_configuration module."""

import pytest
from awslabs.aws_msk_mcp_server.tools.read_config.describe_configuration import (
    describe_configuration,
)
from botocore.exceptions import ClientError
from unittest.mock import MagicMock


class TestDescribeConfiguration:
    """Tests for the describe_configuration module."""

    def test_describe_configuration_basic(self):
        """Test the describe_configuration function with basic parameters."""
        # Arrange
        mock_client = MagicMock()
        expected_response = {
            'Arn': 'arn:aws:kafka:us-east-1:123456789012:configuration/test-config/abcdef',
            'Name': 'test-config',
            'Description': 'Test configuration',
            'KafkaVersions': ['2.8.1', '3.3.1'],
            'CreationTime': '2025-06-20T10:00:00.000Z',
            'LatestRevision': {
                'Revision': 1,
                'CreationTime': '2025-06-20T10:00:00.000Z',
                'Description': 'Initial configuration',
            },
            'State': 'ACTIVE',
        }
        mock_client.describe_configuration.return_value = expected_response

        # Act
        arn = 'arn:aws:kafka:us-east-1:123456789012:configuration/test-config/abcdef'
        result = describe_configuration(arn, mock_client)

        # Assert
        mock_client.describe_configuration.assert_called_once_with(Arn=arn)
        assert result == expected_response
        assert (
            result['Arn']
            == 'arn:aws:kafka:us-east-1:123456789012:configuration/test-config/abcdef'
        )
        assert result['Name'] == 'test-config'
        assert result['KafkaVersions'] == ['2.8.1', '3.3.1']
        assert result['State'] == 'ACTIVE'
        assert 'LatestRevision' in result
        assert result['LatestRevision']['Revision'] == 1

    def test_describe_configuration_error(self):
        """Test the describe_configuration function when the API call fails."""
        # Arrange
        mock_client = MagicMock()
        mock_client.describe_configuration.side_effect = ClientError(
            {'Error': {'Code': 'ResourceNotFoundException', 'Message': 'Configuration not found'}},
            'DescribeConfiguration',
        )

        # Act & Assert
        arn = 'arn:aws:kafka:us-east-1:123456789012:configuration/test-config/abcdef'
        with pytest.raises(ClientError) as excinfo:
            describe_configuration(arn, mock_client)

        # Verify the error
        assert 'ResourceNotFoundException' in str(excinfo.value)
        assert 'Configuration not found' in str(excinfo.value)
        mock_client.describe_configuration.assert_called_once_with(Arn=arn)

    def test_describe_configuration_missing_client(self):
        """Test the describe_configuration function with a missing client."""
        # Act & Assert
        arn = 'arn:aws:kafka:us-east-1:123456789012:configuration/test-config/abcdef'
        with pytest.raises(ValueError) as excinfo:
            describe_configuration(arn, None)

        # Verify the error
        assert 'Client must be provided' in str(excinfo.value)
