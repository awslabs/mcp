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

"""Tests for the common_functions module."""

import pytest
from awslabs.aws_msk_mcp_server.tools.common_functions.common_functions import (
    check_mcp_generated_tag,
    get_cluster_name,
)
from unittest.mock import MagicMock


class TestCommonFunctions:
    """Tests for the common_functions module."""

    def test_check_mcp_generated_tag_with_tag(self):
        """Test check_mcp_generated_tag with a resource that has the tag."""
        # Arrange
        mock_client = MagicMock()
        mock_client.list_tags_for_resource.return_value = {'Tags': {'MCP Generated': 'true'}}

        # Act
        result = check_mcp_generated_tag(
            'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef', mock_client
        )

        # Assert
        assert result is True
        mock_client.list_tags_for_resource.assert_called_once_with(
            ResourceArn='arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        )

    def test_check_mcp_generated_tag_without_tag(self):
        """Test check_mcp_generated_tag with a resource that does not have the tag."""
        # Arrange
        mock_client = MagicMock()
        mock_client.list_tags_for_resource.return_value = {'Tags': {}}

        # Act
        result = check_mcp_generated_tag(
            'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef', mock_client
        )

        # Assert
        assert result is False
        mock_client.list_tags_for_resource.assert_called_once_with(
            ResourceArn='arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        )

    def test_check_mcp_generated_tag_with_false_tag(self):
        """Test check_mcp_generated_tag with a resource that has the tag set to false."""
        # Arrange
        mock_client = MagicMock()
        mock_client.list_tags_for_resource.return_value = {'Tags': {'MCP Generated': 'false'}}

        # Act
        result = check_mcp_generated_tag(
            'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef', mock_client
        )

        # Assert
        assert result is False
        mock_client.list_tags_for_resource.assert_called_once_with(
            ResourceArn='arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        )

    def test_check_mcp_generated_tag_with_case_insensitive_tag(self):
        """Test check_mcp_generated_tag with a resource that has the tag with different case."""
        # Arrange
        mock_client = MagicMock()
        mock_client.list_tags_for_resource.return_value = {'Tags': {'MCP Generated': 'TRUE'}}

        # Act
        result = check_mcp_generated_tag(
            'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef', mock_client
        )

        # Assert
        assert result is True
        mock_client.list_tags_for_resource.assert_called_once_with(
            ResourceArn='arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        )

    def test_check_mcp_generated_tag_with_no_client(self):
        """Test check_mcp_generated_tag with no client."""
        # Act & Assert
        with pytest.raises(ValueError, match='Client must be provided'):
            check_mcp_generated_tag(
                'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef', None
            )

    def test_get_cluster_name_with_arn(self):
        """Test get_cluster_name with an ARN."""
        # Act
        result = get_cluster_name(
            'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        )

        # Assert
        assert result == 'test-cluster'

    def test_get_cluster_name_with_direct_name(self):
        """Test get_cluster_name with a direct cluster name."""
        # Act
        result = get_cluster_name('test-cluster')

        # Assert
        assert result == 'test-cluster'

    def test_get_cluster_name_with_invalid_arn_format(self):
        """Test get_cluster_name with an invalid ARN format."""
        # Act & Assert
        with pytest.raises(ValueError, match='Invalid MSK cluster ARN format'):
            get_cluster_name('arn:aws:kafka:us-east-1:123456789012:cluster')

    def test_get_cluster_name_with_non_kafka_arn(self):
        """Test get_cluster_name with an ARN that does not start with arn:aws:kafka."""
        # Act
        result = get_cluster_name('arn:aws:s3:::my-bucket')

        # Assert
        assert result == 'arn:aws:s3:::my-bucket'
