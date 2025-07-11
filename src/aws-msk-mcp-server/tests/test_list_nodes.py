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

"""Tests for the list_nodes module."""

import pytest
from awslabs.aws_msk_mcp_server.tools.read_cluster.list_nodes import list_nodes
from botocore.exceptions import ClientError
from unittest.mock import MagicMock


class TestListNodes:
    """Tests for the list_nodes module."""

    def test_list_nodes_basic(self):
        """Test the list_nodes function with basic parameters."""
        # Arrange
        mock_client = MagicMock()
        expected_response = {
            'NodeInfoList': [
                {
                    'BrokerNodeInfo': {
                        'BrokerId': 1,
                        'ClientVpcIpAddress': '10.0.0.1',
                        'ClientSubnet': 'subnet-1',
                        'CurrentBrokerSoftwareInfo': {'KafkaVersion': '2.8.1'},
                    }
                },
                {
                    'BrokerNodeInfo': {
                        'BrokerId': 2,
                        'ClientVpcIpAddress': '10.0.0.2',
                        'ClientSubnet': 'subnet-2',
                        'CurrentBrokerSoftwareInfo': {'KafkaVersion': '2.8.1'},
                    }
                },
                {
                    'BrokerNodeInfo': {
                        'BrokerId': 3,
                        'ClientVpcIpAddress': '10.0.0.3',
                        'ClientSubnet': 'subnet-3',
                        'CurrentBrokerSoftwareInfo': {'KafkaVersion': '2.8.1'},
                    }
                },
            ]
        }
        mock_client.list_nodes.return_value = expected_response

        # Act
        cluster_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        result = list_nodes(cluster_arn, mock_client)

        # Assert
        mock_client.list_nodes.assert_called_once_with(ClusterArn=cluster_arn, MaxResults=10)
        assert result == expected_response
        assert len(result['NodeInfoList']) == 3
        assert result['NodeInfoList'][0]['BrokerNodeInfo']['BrokerId'] == 1
        assert result['NodeInfoList'][1]['BrokerNodeInfo']['BrokerId'] == 2
        assert result['NodeInfoList'][2]['BrokerNodeInfo']['BrokerId'] == 3

    def test_list_nodes_error(self):
        """Test the list_nodes function when the API call fails."""
        # Arrange
        mock_client = MagicMock()
        mock_client.list_nodes.side_effect = ClientError(
            {'Error': {'Code': 'ResourceNotFoundException', 'Message': 'Cluster not found'}},
            'ListNodes',
        )

        # Act & Assert
        cluster_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        with pytest.raises(ClientError) as excinfo:
            list_nodes(cluster_arn, mock_client)

        # Verify the error
        assert 'ResourceNotFoundException' in str(excinfo.value)
        assert 'Cluster not found' in str(excinfo.value)
        mock_client.list_nodes.assert_called_once_with(ClusterArn=cluster_arn, MaxResults=10)

    def test_list_nodes_missing_client(self):
        """Test the list_nodes function with a missing client."""
        # Act & Assert
        cluster_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        with pytest.raises(ValueError) as excinfo:
            list_nodes(cluster_arn, None)

        # Verify the error
        assert 'Client must be provided' in str(excinfo.value)

    def test_list_nodes_empty_response(self):
        """Test the list_nodes function with an empty response."""
        # Arrange
        mock_client = MagicMock()
        expected_response = {'NodeInfoList': []}
        mock_client.list_nodes.return_value = expected_response

        # Act
        cluster_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        result = list_nodes(cluster_arn, mock_client)

        # Assert
        mock_client.list_nodes.assert_called_once_with(ClusterArn=cluster_arn, MaxResults=10)
        assert result == expected_response
        assert len(result['NodeInfoList']) == 0
