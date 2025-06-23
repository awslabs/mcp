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

"""Tests for the list_tags_for_resource module."""

import pytest
from awslabs.aws_msk_mcp_server.tools.read_config.list_tags_for_resource import (
    list_tags_for_resource,
)
from botocore.exceptions import ClientError
from unittest.mock import MagicMock


class TestListTagsForResource:
    """Tests for the list_tags_for_resource module."""

    def test_list_tags_for_resource_basic(self):
        """Test the list_tags_for_resource function with basic parameters."""
        # Arrange
        mock_client = MagicMock()
        expected_response = {
            'Tags': {'Environment': 'Production', 'Owner': 'DataTeam', 'Project': 'Analytics'}
        }
        mock_client.list_tags_for_resource.return_value = expected_response

        # Act
        resource_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        result = list_tags_for_resource(resource_arn, mock_client)

        # Assert
        mock_client.list_tags_for_resource.assert_called_once_with(ResourceArn=resource_arn)
        assert result == expected_response
        assert 'Tags' in result
        assert result['Tags']['Environment'] == 'Production'
        assert result['Tags']['Owner'] == 'DataTeam'
        assert result['Tags']['Project'] == 'Analytics'

    def test_list_tags_for_resource_empty_tags(self):
        """Test the list_tags_for_resource function with empty tags."""
        # Arrange
        mock_client = MagicMock()
        expected_response = {'Tags': {}}
        mock_client.list_tags_for_resource.return_value = expected_response

        # Act
        resource_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        result = list_tags_for_resource(resource_arn, mock_client)

        # Assert
        mock_client.list_tags_for_resource.assert_called_once_with(ResourceArn=resource_arn)
        assert result == expected_response
        assert 'Tags' in result
        assert len(result['Tags']) == 0

    def test_list_tags_for_resource_error(self):
        """Test the list_tags_for_resource function when the API call fails."""
        # Arrange
        mock_client = MagicMock()
        mock_client.list_tags_for_resource.side_effect = ClientError(
            {'Error': {'Code': 'ResourceNotFoundException', 'Message': 'Resource not found'}},
            'ListTagsForResource',
        )

        # Act & Assert
        resource_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        with pytest.raises(ClientError) as excinfo:
            list_tags_for_resource(resource_arn, mock_client)

        # Verify the error
        assert 'ResourceNotFoundException' in str(excinfo.value)
        assert 'Resource not found' in str(excinfo.value)
        mock_client.list_tags_for_resource.assert_called_once_with(ResourceArn=resource_arn)

    def test_list_tags_for_resource_missing_client(self):
        """Test the list_tags_for_resource function with a missing client."""
        # Act & Assert
        resource_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        with pytest.raises(ValueError) as excinfo:
            list_tags_for_resource(resource_arn, None)

        # Verify the error
        assert 'Client must be provided' in str(excinfo.value)
