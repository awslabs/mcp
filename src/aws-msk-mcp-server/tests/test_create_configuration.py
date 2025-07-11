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

"""Tests for the create_configuration module."""

import pytest
from awslabs.aws_msk_mcp_server.tools.mutate_config.create_configuration import (
    create_configuration,
)
from botocore.exceptions import ClientError
from unittest.mock import MagicMock


class TestCreateConfiguration:
    """Tests for the create_configuration module."""

    def test_create_configuration_basic(self):
        """Test the create_configuration function with basic parameters."""
        # Arrange
        mock_client = MagicMock()
        expected_response = {
            'Arn': 'arn:aws:kafka:us-east-1:123456789012:configuration/test-config/abcdef',
            'Name': 'test-config',
            'CreationTime': '2025-06-20T10:00:00.000Z',
            'LatestRevision': {'Revision': 1, 'CreationTime': '2025-06-20T10:00:00.000Z'},
        }
        mock_client.create_configuration.return_value = expected_response

        # Act
        name = 'test-config'
        server_properties = 'auto.create.topics.enable=true\ndelete.topic.enable=true'
        description = 'Test configuration'
        result = create_configuration(name, server_properties, mock_client, description)

        # Assert
        mock_client.create_configuration.assert_called_once_with(
            Name=name, ServerProperties=server_properties, Description=description
        )
        assert result == expected_response
        assert (
            result['Arn']
            == 'arn:aws:kafka:us-east-1:123456789012:configuration/test-config/abcdef'
        )
        assert result['Name'] == 'test-config'
        assert 'LatestRevision' in result
        assert result['LatestRevision']['Revision'] == 1

    def test_create_configuration_with_kafka_versions(self):
        """Test the create_configuration function with Kafka versions."""
        # Arrange
        mock_client = MagicMock()
        expected_response = {
            'Arn': 'arn:aws:kafka:us-east-1:123456789012:configuration/test-config/abcdef',
            'Name': 'test-config',
            'CreationTime': '2025-06-20T10:00:00.000Z',
            'KafkaVersions': ['2.8.1', '3.3.1'],
            'LatestRevision': {'Revision': 1, 'CreationTime': '2025-06-20T10:00:00.000Z'},
        }
        mock_client.create_configuration.return_value = expected_response

        # Act
        name = 'test-config'
        server_properties = 'auto.create.topics.enable=true\ndelete.topic.enable=true'
        description = 'Test configuration'
        kafka_versions = ['2.8.1', '3.3.1']
        result = create_configuration(
            name, server_properties, mock_client, description, kafka_versions
        )

        # Assert
        mock_client.create_configuration.assert_called_once_with(
            Name=name,
            ServerProperties=server_properties,
            Description=description,
            KafkaVersions=kafka_versions,
        )
        assert result == expected_response
        assert (
            result['Arn']
            == 'arn:aws:kafka:us-east-1:123456789012:configuration/test-config/abcdef'
        )
        assert result['Name'] == 'test-config'
        assert result['KafkaVersions'] == ['2.8.1', '3.3.1']
        assert 'LatestRevision' in result
        assert result['LatestRevision']['Revision'] == 1

    def test_create_configuration_without_description(self):
        """Test the create_configuration function without a description."""
        # Arrange
        mock_client = MagicMock()
        expected_response = {
            'Arn': 'arn:aws:kafka:us-east-1:123456789012:configuration/test-config/abcdef',
            'Name': 'test-config',
            'CreationTime': '2025-06-20T10:00:00.000Z',
            'LatestRevision': {'Revision': 1, 'CreationTime': '2025-06-20T10:00:00.000Z'},
        }
        mock_client.create_configuration.return_value = expected_response

        # Act
        name = 'test-config'
        server_properties = 'auto.create.topics.enable=true\ndelete.topic.enable=true'
        description = None
        result = create_configuration(name, server_properties, mock_client, description)

        # Assert
        mock_client.create_configuration.assert_called_once_with(
            Name=name, ServerProperties=server_properties
        )
        assert result == expected_response
        assert (
            result['Arn']
            == 'arn:aws:kafka:us-east-1:123456789012:configuration/test-config/abcdef'
        )
        assert result['Name'] == 'test-config'
        assert 'LatestRevision' in result
        assert result['LatestRevision']['Revision'] == 1

    def test_create_configuration_error(self):
        """Test the create_configuration function when the API call fails."""
        # Arrange
        mock_client = MagicMock()
        mock_client.create_configuration.side_effect = ClientError(
            {'Error': {'Code': 'InternalServerError', 'Message': 'Internal server error'}},
            'CreateConfiguration',
        )

        # Act & Assert
        name = 'test-config'
        server_properties = 'auto.create.topics.enable=true\ndelete.topic.enable=true'
        description = 'Test configuration'
        with pytest.raises(ClientError) as excinfo:
            create_configuration(name, server_properties, mock_client, description)

        # Verify the error
        assert 'InternalServerError' in str(excinfo.value)
        assert 'Internal server error' in str(excinfo.value)
        mock_client.create_configuration.assert_called_once_with(
            Name=name, ServerProperties=server_properties, Description=description
        )

    def test_create_configuration_missing_client(self):
        """Test the create_configuration function with a missing client."""
        # Act & Assert
        name = 'test-config'
        server_properties = 'auto.create.topics.enable=true\ndelete.topic.enable=true'
        description = 'Test configuration'
        with pytest.raises(ValueError) as excinfo:
            create_configuration(name, server_properties, None, description)

        # Verify the error
        assert 'Client must be provided' in str(excinfo.value)
