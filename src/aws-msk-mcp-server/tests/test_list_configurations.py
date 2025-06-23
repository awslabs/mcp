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

"""Tests for the list_configurations module."""

import pytest
from awslabs.aws_msk_mcp_server.tools.read_global.list_configurations import list_configurations
from botocore.exceptions import ClientError
from unittest.mock import MagicMock


class TestListConfigurations:
    """Tests for the list_configurations module."""

    def test_list_configurations_basic(self):
        """Test the list_configurations function with basic parameters."""
        # Arrange
        mock_client = MagicMock()
        expected_response = {
            'ConfigurationInfoList': [
                {
                    'Arn': 'arn:aws:kafka:us-east-1:123456789012:configuration/test-config-1/abcdef',
                    'Name': 'test-config-1',
                    'CreationTime': '2025-06-20T10:00:00.000Z',
                    'KafkaVersions': ['2.8.1', '3.3.1'],
                    'LatestRevision': {'Revision': 1, 'CreationTime': '2025-06-20T10:00:00.000Z'},
                },
                {
                    'Arn': 'arn:aws:kafka:us-east-1:123456789012:configuration/test-config-2/ghijkl',
                    'Name': 'test-config-2',
                    'CreationTime': '2025-06-20T11:00:00.000Z',
                    'KafkaVersions': ['3.3.1', '3.4.0'],
                    'LatestRevision': {'Revision': 2, 'CreationTime': '2025-06-20T11:30:00.000Z'},
                },
            ]
        }
        mock_client.list_configurations.return_value = expected_response

        # Act
        result = list_configurations(mock_client)

        # Assert
        mock_client.list_configurations.assert_called_once_with(MaxResults=10)
        assert result == expected_response
        assert 'ConfigurationInfoList' in result
        assert len(result['ConfigurationInfoList']) == 2
        assert result['ConfigurationInfoList'][0]['Name'] == 'test-config-1'
        assert result['ConfigurationInfoList'][1]['Name'] == 'test-config-2'

    def test_list_configurations_with_pagination(self):
        """Test the list_configurations function with pagination parameters."""
        # Arrange
        mock_client = MagicMock()
        expected_response = {
            'ConfigurationInfoList': [
                {
                    'Arn': 'arn:aws:kafka:us-east-1:123456789012:configuration/test-config-1/abcdef',
                    'Name': 'test-config-1',
                    'CreationTime': '2025-06-20T10:00:00.000Z',
                    'KafkaVersions': ['2.8.1', '3.3.1'],
                    'LatestRevision': {'Revision': 1, 'CreationTime': '2025-06-20T10:00:00.000Z'},
                }
            ],
            'NextToken': 'next-token-value',
        }
        mock_client.list_configurations.return_value = expected_response

        # Act
        max_results = 5
        next_token = 'token'
        result = list_configurations(mock_client, max_results, next_token)

        # Assert
        mock_client.list_configurations.assert_called_once_with(
            MaxResults=max_results, NextToken=next_token
        )
        assert result == expected_response
        assert 'ConfigurationInfoList' in result
        assert 'NextToken' in result
        assert result['NextToken'] == 'next-token-value'

    def test_list_configurations_empty_response(self):
        """Test the list_configurations function with an empty response."""
        # Arrange
        mock_client = MagicMock()
        expected_response = {'ConfigurationInfoList': []}
        mock_client.list_configurations.return_value = expected_response

        # Act
        result = list_configurations(mock_client)

        # Assert
        mock_client.list_configurations.assert_called_once_with(MaxResults=10)
        assert result == expected_response
        assert 'ConfigurationInfoList' in result
        assert len(result['ConfigurationInfoList']) == 0

    def test_list_configurations_error(self):
        """Test the list_configurations function when the API call fails."""
        # Arrange
        mock_client = MagicMock()
        mock_client.list_configurations.side_effect = ClientError(
            {'Error': {'Code': 'InternalServerError', 'Message': 'Internal server error'}},
            'ListConfigurations',
        )

        # Act & Assert
        with pytest.raises(ClientError) as excinfo:
            list_configurations(mock_client)

        # Verify the error
        assert 'InternalServerError' in str(excinfo.value)
        assert 'Internal server error' in str(excinfo.value)
        mock_client.list_configurations.assert_called_once_with(MaxResults=10)

    def test_list_configurations_missing_client(self):
        """Test the list_configurations function with a missing client."""
        # Act & Assert
        with pytest.raises(ValueError) as excinfo:
            list_configurations(None)

        # Verify the error
        assert 'Client must be provided' in str(excinfo.value)
