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

"""Tests for the tag_resource module."""

import pytest
from awslabs.aws_msk_mcp_server.tools.mutate_config.tag_resource import tag_resource
from botocore.exceptions import ClientError
from unittest.mock import MagicMock


class TestTagResource:
    """Tests for the tag_resource module."""

    def test_tag_resource_basic(self):
        """Test the tag_resource function with basic parameters."""
        # Arrange
        mock_client = MagicMock()
        expected_response = {}  # Empty response on success
        mock_client.tag_resource.return_value = expected_response

        # Act
        resource_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        tags = {'Environment': 'Production', 'Owner': 'DataTeam'}
        result = tag_resource(resource_arn, tags, mock_client)

        # Assert
        mock_client.tag_resource.assert_called_once_with(ResourceArn=resource_arn, Tags=tags)
        assert result == expected_response

    def test_tag_resource_error(self):
        """Test the tag_resource function when the API call fails."""
        # Arrange
        mock_client = MagicMock()
        mock_client.tag_resource.side_effect = ClientError(
            {'Error': {'Code': 'ResourceNotFoundException', 'Message': 'Resource not found'}},
            'TagResource',
        )

        # Act & Assert
        resource_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        tags = {'Environment': 'Production', 'Owner': 'DataTeam'}
        with pytest.raises(ClientError) as excinfo:
            tag_resource(resource_arn, tags, mock_client)

        # Verify the error
        assert 'ResourceNotFoundException' in str(excinfo.value)
        assert 'Resource not found' in str(excinfo.value)
        mock_client.tag_resource.assert_called_once_with(ResourceArn=resource_arn, Tags=tags)

    def test_tag_resource_missing_client(self):
        """Test the tag_resource function with a missing client."""
        # Act & Assert
        resource_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        tags = {'Environment': 'Production', 'Owner': 'DataTeam'}
        with pytest.raises(ValueError) as excinfo:
            tag_resource(resource_arn, tags, None)

        # Verify the error
        assert 'Client must be provided' in str(excinfo.value)
