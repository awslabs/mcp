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

"""Tests for the update_configuration module."""

import pytest
from awslabs.aws_msk_mcp_server.tools.mutate_config.update_configuration import (
    update_configuration,
)
from botocore.exceptions import ClientError
from unittest.mock import MagicMock


class TestUpdateConfiguration:
    """Tests for the update_configuration module."""

    def test_update_configuration_basic(self):
        """Test the update_configuration function with basic parameters."""
        # Arrange
        mock_client = MagicMock()
        expected_response = {
            'Arn': 'arn:aws:kafka:us-east-1:123456789012:configuration/test-config/abcdef',
            'LatestRevision': {
                'Revision': 2,
                'CreationTime': '2025-06-20T11:00:00.000Z',
                'Description': 'Updated configuration',
            },
        }
        mock_client.update_configuration.return_value = expected_response

        # Act
        arn = 'arn:aws:kafka:us-east-1:123456789012:configuration/test-config/abcdef'
        server_properties = (
            'auto.create.topics.enable=true\ndelete.topic.enable=true\nlog.retention.hours=24'
        )
        description = 'Updated configuration'
        result = update_configuration(arn, server_properties, mock_client, description)

        # Assert
        mock_client.update_configuration.assert_called_once_with(
            Arn=arn, ServerProperties=server_properties, Description=description
        )
        assert result == expected_response
        assert (
            result['Arn']
            == 'arn:aws:kafka:us-east-1:123456789012:configuration/test-config/abcdef'
        )
        assert 'LatestRevision' in result
        assert result['LatestRevision']['Revision'] == 2
        assert result['LatestRevision']['Description'] == 'Updated configuration'

    def test_update_configuration_without_description(self):
        """Test the update_configuration function without a description."""
        # Arrange
        mock_client = MagicMock()
        expected_response = {
            'Arn': 'arn:aws:kafka:us-east-1:123456789012:configuration/test-config/abcdef',
            'LatestRevision': {'Revision': 2, 'CreationTime': '2025-06-20T11:00:00.000Z'},
        }
        mock_client.update_configuration.return_value = expected_response

        # Act
        arn = 'arn:aws:kafka:us-east-1:123456789012:configuration/test-config/abcdef'
        server_properties = (
            'auto.create.topics.enable=true\ndelete.topic.enable=true\nlog.retention.hours=24'
        )
        description = None
        result = update_configuration(arn, server_properties, mock_client, description)

        # Assert
        mock_client.update_configuration.assert_called_once_with(
            Arn=arn, ServerProperties=server_properties
        )
        assert result == expected_response
        assert (
            result['Arn']
            == 'arn:aws:kafka:us-east-1:123456789012:configuration/test-config/abcdef'
        )
        assert 'LatestRevision' in result
        assert result['LatestRevision']['Revision'] == 2

    def test_update_configuration_error(self):
        """Test the update_configuration function when the API call fails."""
        # Arrange
        mock_client = MagicMock()
        mock_client.update_configuration.side_effect = ClientError(
            {'Error': {'Code': 'ResourceNotFoundException', 'Message': 'Configuration not found'}},
            'UpdateConfiguration',
        )

        # Act & Assert
        arn = 'arn:aws:kafka:us-east-1:123456789012:configuration/test-config/abcdef'
        server_properties = (
            'auto.create.topics.enable=true\ndelete.topic.enable=true\nlog.retention.hours=24'
        )
        description = 'Updated configuration'
        with pytest.raises(ClientError) as excinfo:
            update_configuration(arn, server_properties, mock_client, description)

        # Verify the error
        assert 'ResourceNotFoundException' in str(excinfo.value)
        assert 'Configuration not found' in str(excinfo.value)
        mock_client.update_configuration.assert_called_once_with(
            Arn=arn, ServerProperties=server_properties, Description=description
        )

    def test_update_configuration_missing_client(self):
        """Test the update_configuration function with a missing client."""
        # Act & Assert
        arn = 'arn:aws:kafka:us-east-1:123456789012:configuration/test-config/abcdef'
        server_properties = (
            'auto.create.topics.enable=true\ndelete.topic.enable=true\nlog.retention.hours=24'
        )
        description = 'Updated configuration'
        with pytest.raises(ValueError) as excinfo:
            update_configuration(arn, server_properties, None, description)

        # Verify the error
        assert 'Client must be provided' in str(excinfo.value)
