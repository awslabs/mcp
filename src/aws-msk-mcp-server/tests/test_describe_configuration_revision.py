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

"""Tests for the describe_configuration_revision module."""

import pytest
from awslabs.aws_msk_mcp_server.tools.read_config.describe_configuration_revision import (
    describe_configuration_revision,
)
from botocore.exceptions import ClientError
from unittest.mock import MagicMock


class TestDescribeConfigurationRevision:
    """Tests for the describe_configuration_revision module."""

    def test_describe_configuration_revision_basic(self):
        """Test the describe_configuration_revision function with basic parameters."""
        # Arrange
        mock_client = MagicMock()
        expected_response = {
            'Arn': 'arn:aws:kafka:us-east-1:123456789012:configuration/test-config/abcdef',
            'CreationTime': '2025-06-20T10:00:00.000Z',
            'Description': 'Initial configuration',
            'Revision': 1,
            'ServerProperties': 'auto.create.topics.enable=true\ndelete.topic.enable=true',
        }
        mock_client.describe_configuration_revision.return_value = expected_response

        # Act
        arn = 'arn:aws:kafka:us-east-1:123456789012:configuration/test-config/abcdef'
        revision = 1
        result = describe_configuration_revision(arn, revision, mock_client)

        # Assert
        mock_client.describe_configuration_revision.assert_called_once_with(
            Arn=arn, Revision=revision
        )
        assert result == expected_response
        assert (
            result['Arn']
            == 'arn:aws:kafka:us-east-1:123456789012:configuration/test-config/abcdef'
        )
        assert result['Revision'] == 1
        assert result['Description'] == 'Initial configuration'
        assert 'ServerProperties' in result
        assert 'auto.create.topics.enable=true' in result['ServerProperties']

    def test_describe_configuration_revision_error(self):
        """Test the describe_configuration_revision function when the API call fails."""
        # Arrange
        mock_client = MagicMock()
        mock_client.describe_configuration_revision.side_effect = ClientError(
            {
                'Error': {
                    'Code': 'ResourceNotFoundException',
                    'Message': 'Configuration revision not found',
                }
            },
            'DescribeConfigurationRevision',
        )

        # Act & Assert
        arn = 'arn:aws:kafka:us-east-1:123456789012:configuration/test-config/abcdef'
        revision = 1
        with pytest.raises(ClientError) as excinfo:
            describe_configuration_revision(arn, revision, mock_client)

        # Verify the error
        assert 'ResourceNotFoundException' in str(excinfo.value)
        assert 'Configuration revision not found' in str(excinfo.value)
        mock_client.describe_configuration_revision.assert_called_once_with(
            Arn=arn, Revision=revision
        )

    def test_describe_configuration_revision_missing_client(self):
        """Test the describe_configuration_revision function with a missing client."""
        # Act & Assert
        arn = 'arn:aws:kafka:us-east-1:123456789012:configuration/test-config/abcdef'
        revision = 1
        with pytest.raises(ValueError) as excinfo:
            describe_configuration_revision(arn, revision, None)

        # Verify the error
        assert 'Client must be provided' in str(excinfo.value)
