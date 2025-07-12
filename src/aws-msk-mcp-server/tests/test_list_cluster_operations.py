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

"""Tests for the list_cluster_operations module."""

import pytest
from awslabs.aws_msk_mcp_server.tools.read_cluster.list_cluster_operations import (
    list_cluster_operations,
)
from botocore.exceptions import ClientError
from unittest.mock import MagicMock


class TestListClusterOperations:
    """Tests for the list_cluster_operations module."""

    def test_list_cluster_operations_basic(self):
        """Test the list_cluster_operations function with basic parameters."""
        # Arrange
        mock_client = MagicMock()
        expected_response = {
            'ClusterOperationInfoList': [
                {
                    'ClusterArn': 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef',
                    'ClusterOperationArn': 'arn:aws:kafka:us-east-1:123456789012:cluster-operation/test-cluster/abcdef/operation',
                    'OperationType': 'UPDATE',
                    'OperationState': 'COMPLETED',
                    'CreationTime': '2025-06-20T10:00:00.000Z',
                    'EndTime': '2025-06-20T10:30:00.000Z',
                }
            ]
        }
        mock_client.list_cluster_operations_v2.return_value = expected_response

        # Act
        cluster_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        result = list_cluster_operations(cluster_arn, mock_client)

        # Assert
        mock_client.list_cluster_operations_v2.assert_called_once_with(
            ClusterArn=cluster_arn, MaxResults=10
        )
        assert result == expected_response
        assert 'ClusterOperationInfoList' in result
        assert len(result['ClusterOperationInfoList']) == 1
        assert result['ClusterOperationInfoList'][0]['OperationType'] == 'UPDATE'
        assert result['ClusterOperationInfoList'][0]['OperationState'] == 'COMPLETED'

    def test_list_cluster_operations_with_pagination(self):
        """Test the list_cluster_operations function with pagination parameters."""
        # Arrange
        mock_client = MagicMock()
        expected_response = {
            'ClusterOperationInfoList': [
                {
                    'ClusterArn': 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef',
                    'ClusterOperationArn': 'arn:aws:kafka:us-east-1:123456789012:cluster-operation/test-cluster/abcdef/operation',
                    'OperationType': 'UPDATE',
                    'OperationState': 'COMPLETED',
                    'CreationTime': '2025-06-20T10:00:00.000Z',
                    'EndTime': '2025-06-20T10:30:00.000Z',
                }
            ],
            'NextToken': 'next-token-value',
        }
        mock_client.list_cluster_operations_v2.return_value = expected_response

        # Act
        cluster_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        max_results = 5
        next_token = 'token'
        result = list_cluster_operations(cluster_arn, mock_client, max_results, next_token)

        # Assert
        mock_client.list_cluster_operations_v2.assert_called_once_with(
            ClusterArn=cluster_arn, MaxResults=max_results, NextToken=next_token
        )
        assert result == expected_response
        assert 'ClusterOperationInfoList' in result
        assert 'NextToken' in result
        assert result['NextToken'] == 'next-token-value'

    def test_list_cluster_operations_empty_response(self):
        """Test the list_cluster_operations function with an empty response."""
        # Arrange
        mock_client = MagicMock()
        expected_response = {'ClusterOperationInfoList': []}
        mock_client.list_cluster_operations_v2.return_value = expected_response

        # Act
        cluster_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        result = list_cluster_operations(cluster_arn, mock_client)

        # Assert
        mock_client.list_cluster_operations_v2.assert_called_once_with(
            ClusterArn=cluster_arn, MaxResults=10
        )
        assert result == expected_response
        assert 'ClusterOperationInfoList' in result
        assert len(result['ClusterOperationInfoList']) == 0

    def test_list_cluster_operations_error(self):
        """Test the list_cluster_operations function when the API call fails."""
        # Arrange
        mock_client = MagicMock()
        mock_client.list_cluster_operations_v2.side_effect = ClientError(
            {'Error': {'Code': 'ResourceNotFoundException', 'Message': 'Cluster not found'}},
            'ListClusterOperationsV2',
        )

        # Act & Assert
        cluster_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        with pytest.raises(ClientError) as excinfo:
            list_cluster_operations(cluster_arn, mock_client)

        # Verify the error
        assert 'ResourceNotFoundException' in str(excinfo.value)
        assert 'Cluster not found' in str(excinfo.value)
        mock_client.list_cluster_operations_v2.assert_called_once_with(
            ClusterArn=cluster_arn, MaxResults=10
        )

    def test_list_cluster_operations_missing_client(self):
        """Test the list_cluster_operations function with a missing client."""
        # Act & Assert
        cluster_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        with pytest.raises(ValueError) as excinfo:
            list_cluster_operations(cluster_arn, None)

        # Verify the error
        assert 'Client must be provided' in str(excinfo.value)
