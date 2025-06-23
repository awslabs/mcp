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

"""Tests for the describe_cluster module."""

import pytest
from awslabs.aws_msk_mcp_server.tools.read_cluster.describe_cluster import describe_cluster
from botocore.exceptions import ClientError
from unittest.mock import MagicMock


class TestDescribeCluster:
    """Tests for the describe_cluster module."""

    def test_describe_cluster_basic(self):
        """Test the describe_cluster function with basic parameters."""
        # Arrange
        mock_client = MagicMock()
        expected_response = {
            'ClusterInfo': {
                'ClusterArn': 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef',
                'ClusterName': 'test-cluster',
                'State': 'ACTIVE',
                'CreationTime': '2025-06-20T10:00:00.000Z',
                'CurrentVersion': '1',
            }
        }
        mock_client.describe_cluster_v2.return_value = expected_response

        # Act
        cluster_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        result = describe_cluster(cluster_arn, mock_client)

        # Assert
        mock_client.describe_cluster_v2.assert_called_once_with(ClusterArn=cluster_arn)
        assert result == expected_response

    def test_describe_cluster_error(self):
        """Test the describe_cluster function when the API call fails."""
        # Arrange
        mock_client = MagicMock()
        mock_client.describe_cluster_v2.side_effect = ClientError(
            {'Error': {'Code': 'ResourceNotFoundException', 'Message': 'Cluster not found'}},
            'DescribeClusterV2',
        )

        # Act & Assert
        cluster_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        with pytest.raises(ClientError) as excinfo:
            describe_cluster(cluster_arn, mock_client)

        # Verify the error
        assert 'ResourceNotFoundException' in str(excinfo.value)
        assert 'Cluster not found' in str(excinfo.value)
        mock_client.describe_cluster_v2.assert_called_once_with(ClusterArn=cluster_arn)

    def test_describe_cluster_missing_client(self):
        """Test the describe_cluster function with a missing client."""
        # Act & Assert
        cluster_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        with pytest.raises(ValueError) as excinfo:
            describe_cluster(cluster_arn, None)

        # Verify the error
        assert 'Client must be provided' in str(excinfo.value)
