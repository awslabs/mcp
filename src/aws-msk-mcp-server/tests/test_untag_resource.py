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

"""Tests for the untag_resource module."""

import pytest
from awslabs.aws_msk_mcp_server.tools.mutate_config.untag_resource import untag_resource
from botocore.exceptions import ClientError
from unittest.mock import MagicMock


class TestUntagResource:
    """Tests for the untag_resource module."""

    def test_untag_resource_basic(self):
        """Test the untag_resource function with basic parameters."""
        # Arrange
        mock_client = MagicMock()
        expected_response = {}  # Empty response on success
        mock_client.untag_resource.return_value = expected_response

        # Act
        resource_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        tag_keys = ['Environment', 'Owner']
        result = untag_resource(resource_arn, tag_keys, mock_client)

        # Assert
        mock_client.untag_resource.assert_called_once_with(
            ResourceArn=resource_arn, TagKeys=tag_keys
        )
        assert result == expected_response

    def test_untag_resource_error(self):
        """Test the untag_resource function when the API call fails."""
        # Arrange
        mock_client = MagicMock()
        mock_client.untag_resource.side_effect = ClientError(
            {'Error': {'Code': 'ResourceNotFoundException', 'Message': 'Resource not found'}},
            'UntagResource',
        )

        # Act & Assert
        resource_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        tag_keys = ['Environment', 'Owner']
        with pytest.raises(ClientError) as excinfo:
            untag_resource(resource_arn, tag_keys, mock_client)

        # Verify the error
        assert 'ResourceNotFoundException' in str(excinfo.value)
        assert 'Resource not found' in str(excinfo.value)
        mock_client.untag_resource.assert_called_once_with(
            ResourceArn=resource_arn, TagKeys=tag_keys
        )

    def test_untag_resource_missing_client(self):
        """Test the untag_resource function with a missing client."""
        # Act & Assert
        resource_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        tag_keys = ['Environment', 'Owner']
        with pytest.raises(ValueError) as excinfo:
            untag_resource(resource_arn, tag_keys, None)

        # Verify the error
        assert 'Client must be provided' in str(excinfo.value)
