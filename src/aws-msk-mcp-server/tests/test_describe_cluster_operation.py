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

"""Tests for the describe_cluster_operation module."""

import pytest
from awslabs.aws_msk_mcp_server.tools.read_cluster.describe_cluster_operation import (
    describe_cluster_operation,
)
from botocore.exceptions import ClientError
from unittest.mock import MagicMock


class TestDescribeClusterOperation:
    """Tests for the describe_cluster_operation module."""

    def test_describe_cluster_operation_basic(self):
        """Test the describe_cluster_operation function with basic parameters."""
        # Arrange
        mock_client = MagicMock()
        expected_response = {
            'ClusterOperationInfo': {
                'ClusterArn': 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef',
                'ClusterOperationArn': 'arn:aws:kafka:us-east-1:123456789012:cluster-operation/test-cluster/abcdef/operation',
                'OperationType': 'UPDATE',
                'OperationState': 'COMPLETED',
                'CreationTime': '2025-06-20T10:00:00.000Z',
                'EndTime': '2025-06-20T10:30:00.000Z',
            }
        }
        mock_client.describe_cluster_operation_v2.return_value = expected_response

        # Act
        cluster_operation_arn = (
            'arn:aws:kafka:us-east-1:123456789012:cluster-operation/test-cluster/abcdef/operation'
        )
        result = describe_cluster_operation(cluster_operation_arn, mock_client)

        # Assert
        mock_client.describe_cluster_operation_v2.assert_called_once_with(
            ClusterOperationArn=cluster_operation_arn
        )
        assert result == expected_response

    def test_describe_cluster_operation_error(self):
        """Test the describe_cluster_operation function when the API call fails."""
        # Arrange
        mock_client = MagicMock()
        mock_client.describe_cluster_operation_v2.side_effect = ClientError(
            {
                'Error': {
                    'Code': 'ResourceNotFoundException',
                    'Message': 'Cluster operation not found',
                }
            },
            'DescribeClusterOperationV2',
        )

        # Act & Assert
        cluster_operation_arn = (
            'arn:aws:kafka:us-east-1:123456789012:cluster-operation/test-cluster/abcdef/operation'
        )
        with pytest.raises(ClientError) as excinfo:
            describe_cluster_operation(cluster_operation_arn, mock_client)

        # Verify the error
        assert 'ResourceNotFoundException' in str(excinfo.value)
        assert 'Cluster operation not found' in str(excinfo.value)
        mock_client.describe_cluster_operation_v2.assert_called_once_with(
            ClusterOperationArn=cluster_operation_arn
        )

    def test_describe_cluster_operation_missing_client(self):
        """Test the describe_cluster_operation function with a missing client."""
        # Act & Assert
        cluster_operation_arn = (
            'arn:aws:kafka:us-east-1:123456789012:cluster-operation/test-cluster/abcdef/operation'
        )
        with pytest.raises(ValueError) as excinfo:
            describe_cluster_operation(cluster_operation_arn, None)

        # Verify the error
        assert 'Client must be provided' in str(excinfo.value)
