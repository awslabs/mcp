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

"""Tests for the list_clusters module."""

import pytest
from awslabs.aws_msk_mcp_server.tools.read_global.list_clusters import list_clusters
from botocore.exceptions import ClientError
from unittest.mock import MagicMock


class TestListClusters:
    """Tests for the list_clusters module."""

    def test_list_clusters_basic(self):
        """Test the list_clusters function with basic parameters."""
        # Arrange
        mock_client = MagicMock()
        expected_response = {
            'ClusterInfoList': [
                {
                    'ClusterArn': 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster-1/abcdef',
                    'ClusterName': 'test-cluster-1',
                    'CreationTime': '2025-06-20T10:00:00.000Z',
                    'CurrentVersion': '1',
                    'State': 'ACTIVE',
                    'ClusterType': 'PROVISIONED',
                },
                {
                    'ClusterArn': 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster-2/ghijkl',
                    'ClusterName': 'test-cluster-2',
                    'CreationTime': '2025-06-20T11:00:00.000Z',
                    'CurrentVersion': '1',
                    'State': 'ACTIVE',
                    'ClusterType': 'SERVERLESS',
                },
            ]
        }
        mock_client.list_clusters_v2.return_value = expected_response

        # Act
        result = list_clusters(mock_client)

        # Assert
        mock_client.list_clusters_v2.assert_called_once_with(MaxResults=10)
        assert result == expected_response
        assert 'ClusterInfoList' in result
        assert len(result['ClusterInfoList']) == 2
        assert result['ClusterInfoList'][0]['ClusterName'] == 'test-cluster-1'
        assert result['ClusterInfoList'][1]['ClusterName'] == 'test-cluster-2'

    def test_list_clusters_with_filters(self):
        """Test the list_clusters function with filters."""
        # Arrange
        mock_client = MagicMock()
        expected_response = {
            'ClusterInfoList': [
                {
                    'ClusterArn': 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster-1/abcdef',
                    'ClusterName': 'test-cluster-1',
                    'CreationTime': '2025-06-20T10:00:00.000Z',
                    'CurrentVersion': '1',
                    'State': 'ACTIVE',
                    'ClusterType': 'PROVISIONED',
                }
            ]
        }
        mock_client.list_clusters_v2.return_value = expected_response

        # Act
        cluster_name_filter = 'test'
        cluster_type_filter = 'PROVISIONED'
        result = list_clusters(mock_client, cluster_name_filter, cluster_type_filter)

        # Assert
        mock_client.list_clusters_v2.assert_called_once_with(
            MaxResults=10,
            ClusterNameFilter=cluster_name_filter,
            ClusterTypeFilter=cluster_type_filter,
        )
        assert result == expected_response
        assert 'ClusterInfoList' in result
        assert len(result['ClusterInfoList']) == 1
        assert result['ClusterInfoList'][0]['ClusterName'] == 'test-cluster-1'
        assert result['ClusterInfoList'][0]['ClusterType'] == 'PROVISIONED'

    def test_list_clusters_with_pagination(self):
        """Test the list_clusters function with pagination parameters."""
        # Arrange
        mock_client = MagicMock()
        expected_response = {
            'ClusterInfoList': [
                {
                    'ClusterArn': 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster-1/abcdef',
                    'ClusterName': 'test-cluster-1',
                    'CreationTime': '2025-06-20T10:00:00.000Z',
                    'CurrentVersion': '1',
                    'State': 'ACTIVE',
                    'ClusterType': 'PROVISIONED',
                }
            ],
            'NextToken': 'next-token-value',
        }
        mock_client.list_clusters_v2.return_value = expected_response

        # Act
        max_results = 5
        next_token = 'token'
        result = list_clusters(mock_client, max_results=max_results, next_token=next_token)

        # Assert
        mock_client.list_clusters_v2.assert_called_once_with(
            MaxResults=max_results, NextToken=next_token
        )
        assert result == expected_response
        assert 'ClusterInfoList' in result
        assert 'NextToken' in result
        assert result['NextToken'] == 'next-token-value'

    def test_list_clusters_empty_response(self):
        """Test the list_clusters function with an empty response."""
        # Arrange
        mock_client = MagicMock()
        expected_response = {'ClusterInfoList': []}
        mock_client.list_clusters_v2.return_value = expected_response

        # Act
        result = list_clusters(mock_client)

        # Assert
        mock_client.list_clusters_v2.assert_called_once_with(MaxResults=10)
        assert result == expected_response
        assert 'ClusterInfoList' in result
        assert len(result['ClusterInfoList']) == 0

    def test_list_clusters_error(self):
        """Test the list_clusters function when the API call fails."""
        # Arrange
        mock_client = MagicMock()
        mock_client.list_clusters_v2.side_effect = ClientError(
            {'Error': {'Code': 'InternalServerError', 'Message': 'Internal server error'}},
            'ListClustersV2',
        )

        # Act & Assert
        with pytest.raises(ClientError) as excinfo:
            list_clusters(mock_client)

        # Verify the error
        assert 'InternalServerError' in str(excinfo.value)
        assert 'Internal server error' in str(excinfo.value)
        mock_client.list_clusters_v2.assert_called_once_with(MaxResults=10)

    def test_list_clusters_missing_client(self):
        """Test the list_clusters function with a missing client."""
        # Act & Assert
        with pytest.raises(ValueError) as excinfo:
            list_clusters(None)

        # Verify the error
        assert 'Client must be provided' in str(excinfo.value)
