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

"""Tests for the list_configuration_revisions module."""

import pytest
from awslabs.aws_msk_mcp_server.tools.read_config.list_configuration_revisions import (
    list_configuration_revisions,
)
from botocore.exceptions import ClientError
from unittest.mock import MagicMock


class TestListConfigurationRevisions:
    """Tests for the list_configuration_revisions module."""

    def test_list_configuration_revisions_basic(self):
        """Test the list_configuration_revisions function with basic parameters."""
        # Arrange
        mock_client = MagicMock()
        expected_response = {
            'Revisions': [
                {
                    'CreationTime': '2025-06-20T10:00:00.000Z',
                    'Description': 'Initial configuration',
                    'Revision': 1,
                }
            ]
        }
        mock_client.list_configuration_revisions.return_value = expected_response

        # Act
        config_arn = 'arn:aws:kafka:us-east-1:123456789012:configuration/test-config/abcdef'
        result = list_configuration_revisions(config_arn, mock_client, None)

        # Assert
        mock_client.list_configuration_revisions.assert_called_once_with(
            Arn=config_arn, MaxResults=10
        )
        assert result == expected_response
        assert 'Revisions' in result
        assert len(result['Revisions']) == 1
        assert result['Revisions'][0]['Revision'] == 1
        assert result['Revisions'][0]['Description'] == 'Initial configuration'

    def test_list_configuration_revisions_with_pagination(self):
        """Test the list_configuration_revisions function with pagination parameters."""
        # Arrange
        mock_client = MagicMock()
        expected_response = {
            'Revisions': [
                {
                    'CreationTime': '2025-06-20T10:00:00.000Z',
                    'Description': 'Initial configuration',
                    'Revision': 1,
                }
            ],
            'NextToken': 'next-token-value',
        }
        mock_client.list_configuration_revisions.return_value = expected_response

        # Act
        config_arn = 'arn:aws:kafka:us-east-1:123456789012:configuration/test-config/abcdef'
        max_results = 5
        next_token = 'token'
        result = list_configuration_revisions(config_arn, mock_client, next_token, max_results)

        # Assert
        mock_client.list_configuration_revisions.assert_called_once_with(
            Arn=config_arn, MaxResults=max_results, NextToken=next_token
        )
        assert result == expected_response
        assert 'Revisions' in result
        assert 'NextToken' in result
        assert result['NextToken'] == 'next-token-value'

    def test_list_configuration_revisions_empty_response(self):
        """Test the list_configuration_revisions function with an empty response."""
        # Arrange
        mock_client = MagicMock()
        expected_response = {'Revisions': []}
        mock_client.list_configuration_revisions.return_value = expected_response

        # Act
        config_arn = 'arn:aws:kafka:us-east-1:123456789012:configuration/test-config/abcdef'
        result = list_configuration_revisions(config_arn, mock_client, None)

        # Assert
        mock_client.list_configuration_revisions.assert_called_once_with(
            Arn=config_arn, MaxResults=10
        )
        assert result == expected_response
        assert 'Revisions' in result
        assert len(result['Revisions']) == 0

    def test_list_configuration_revisions_error(self):
        """Test the list_configuration_revisions function when the API call fails."""
        # Arrange
        mock_client = MagicMock()
        mock_client.list_configuration_revisions.side_effect = ClientError(
            {'Error': {'Code': 'ResourceNotFoundException', 'Message': 'Configuration not found'}},
            'ListConfigurationRevisions',
        )

        # Act & Assert
        config_arn = 'arn:aws:kafka:us-east-1:123456789012:configuration/test-config/abcdef'
        with pytest.raises(ClientError) as excinfo:
            list_configuration_revisions(config_arn, mock_client, None)

        # Verify the error
        assert 'ResourceNotFoundException' in str(excinfo.value)
        assert 'Configuration not found' in str(excinfo.value)
        mock_client.list_configuration_revisions.assert_called_once_with(
            Arn=config_arn, MaxResults=10
        )

    def test_list_configuration_revisions_missing_client(self):
        """Test the list_configuration_revisions function with a missing client."""
        # Act & Assert
        config_arn = 'arn:aws:kafka:us-east-1:123456789012:configuration/test-config/abcdef'
        with pytest.raises(ValueError) as excinfo:
            list_configuration_revisions(config_arn, None, None)

        # Verify the error
        assert 'Client must be provided' in str(excinfo.value)
        assert 'This function should only be called from get_configuration_info' in str(
            excinfo.value
        )

    def test_list_configuration_revisions_multiple_revisions(self):
        """Test the list_configuration_revisions function with multiple revisions."""
        # Arrange
        mock_client = MagicMock()
        expected_response = {
            'Revisions': [
                {
                    'CreationTime': '2025-06-20T10:00:00.000Z',
                    'Description': 'Initial configuration',
                    'Revision': 1,
                },
                {
                    'CreationTime': '2025-06-21T10:00:00.000Z',
                    'Description': 'Updated configuration',
                    'Revision': 2,
                },
                {
                    'CreationTime': '2025-06-22T10:00:00.000Z',
                    'Description': 'Final configuration',
                    'Revision': 3,
                },
            ]
        }
        mock_client.list_configuration_revisions.return_value = expected_response

        # Act
        config_arn = 'arn:aws:kafka:us-east-1:123456789012:configuration/test-config/abcdef'
        result = list_configuration_revisions(config_arn, mock_client, None)

        # Assert
        mock_client.list_configuration_revisions.assert_called_once_with(
            Arn=config_arn, MaxResults=10
        )
        assert result == expected_response
        assert 'Revisions' in result
        assert len(result['Revisions']) == 3
        assert result['Revisions'][0]['Revision'] == 1
        assert result['Revisions'][1]['Revision'] == 2
        assert result['Revisions'][2]['Revision'] == 3
        assert result['Revisions'][0]['Description'] == 'Initial configuration'
        assert result['Revisions'][1]['Description'] == 'Updated configuration'
        assert result['Revisions'][2]['Description'] == 'Final configuration'
