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

"""Tests for the list_kafka_versions module."""

import pytest
from awslabs.aws_msk_mcp_server.tools.read_global.list_kafka_versions import list_kafka_versions
from botocore.exceptions import ClientError
from unittest.mock import MagicMock


class TestListKafkaVersions:
    """Tests for the list_kafka_versions module."""

    def test_list_kafka_versions_basic(self):
        """Test the list_kafka_versions function with basic parameters."""
        # Arrange
        mock_client = MagicMock()
        expected_response = {'KafkaVersions': ['2.8.1', '3.3.1', '3.4.0', '3.5.0']}
        mock_client.list_kafka_versions.return_value = expected_response

        # Act
        result = list_kafka_versions(mock_client)

        # Assert
        mock_client.list_kafka_versions.assert_called_once_with()
        assert result == expected_response
        assert 'KafkaVersions' in result
        assert len(result['KafkaVersions']) == 4
        assert '2.8.1' in result['KafkaVersions']
        assert '3.5.0' in result['KafkaVersions']

    def test_list_kafka_versions_empty_response(self):
        """Test the list_kafka_versions function with an empty response."""
        # Arrange
        mock_client = MagicMock()
        expected_response = {'KafkaVersions': []}
        mock_client.list_kafka_versions.return_value = expected_response

        # Act
        result = list_kafka_versions(mock_client)

        # Assert
        mock_client.list_kafka_versions.assert_called_once_with()
        assert result == expected_response
        assert 'KafkaVersions' in result
        assert len(result['KafkaVersions']) == 0

    def test_list_kafka_versions_error(self):
        """Test the list_kafka_versions function when the API call fails."""
        # Arrange
        mock_client = MagicMock()
        mock_client.list_kafka_versions.side_effect = ClientError(
            {'Error': {'Code': 'InternalServerError', 'Message': 'Internal server error'}},
            'ListKafkaVersions',
        )

        # Act & Assert
        with pytest.raises(ClientError) as excinfo:
            list_kafka_versions(mock_client)

        # Verify the error
        assert 'InternalServerError' in str(excinfo.value)
        assert 'Internal server error' in str(excinfo.value)
        mock_client.list_kafka_versions.assert_called_once_with()

    def test_list_kafka_versions_missing_client(self):
        """Test the list_kafka_versions function with a missing client."""
        # Act & Assert
        with pytest.raises(ValueError) as excinfo:
            list_kafka_versions(None)

        # Verify the error
        assert 'Client must be provided' in str(excinfo.value)
