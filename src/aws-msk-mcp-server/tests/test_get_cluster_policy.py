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

"""Tests for the get_cluster_policy module."""

import json
import pytest
from awslabs.aws_msk_mcp_server.tools.read_cluster.get_cluster_policy import get_cluster_policy
from botocore.exceptions import ClientError
from unittest.mock import MagicMock


class TestGetClusterPolicy:
    """Tests for the get_cluster_policy module."""

    def test_get_cluster_policy_basic(self):
        """Test the get_cluster_policy function with basic parameters."""
        # Arrange
        mock_client = MagicMock()
        policy_json = {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Effect': 'Allow',
                    'Principal': {'AWS': 'arn:aws:iam::123456789012:role/ExampleRole'},
                    'Action': ['kafka:GetBootstrapBrokers', 'kafka:DescribeCluster'],
                    'Resource': 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/*',
                }
            ],
        }
        expected_response = {'CurrentVersion': '1', 'Policy': json.dumps(policy_json)}
        mock_client.get_cluster_policy.return_value = expected_response

        # Act
        cluster_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        result = get_cluster_policy(cluster_arn, mock_client)

        # Assert
        mock_client.get_cluster_policy.assert_called_once_with(ClusterArn=cluster_arn)
        assert result == expected_response

        # Verify that the policy can be parsed as JSON
        parsed_policy = json.loads(result['Policy'])
        assert parsed_policy['Version'] == '2012-10-17'
        assert len(parsed_policy['Statement']) == 1
        assert parsed_policy['Statement'][0]['Effect'] == 'Allow'
        assert (
            parsed_policy['Statement'][0]['Principal']['AWS']
            == 'arn:aws:iam::123456789012:role/ExampleRole'
        )
        assert 'kafka:GetBootstrapBrokers' in parsed_policy['Statement'][0]['Action']
        assert 'kafka:DescribeCluster' in parsed_policy['Statement'][0]['Action']

    def test_get_cluster_policy_not_found(self):
        """Test the get_cluster_policy function when the policy is not found."""
        # Arrange
        mock_client = MagicMock()
        mock_client.get_cluster_policy.side_effect = ClientError(
            {'Error': {'Code': 'NotFoundException', 'Message': 'Policy not found'}},
            'GetClusterPolicy',
        )

        # Act & Assert
        cluster_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        with pytest.raises(ClientError) as excinfo:
            get_cluster_policy(cluster_arn, mock_client)

        # Verify the error
        assert 'NotFoundException' in str(excinfo.value)
        assert 'Policy not found' in str(excinfo.value)
        mock_client.get_cluster_policy.assert_called_once_with(ClusterArn=cluster_arn)

    def test_get_cluster_policy_missing_client(self):
        """Test the get_cluster_policy function with a missing client."""
        # Act & Assert
        cluster_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        with pytest.raises(ValueError) as excinfo:
            get_cluster_policy(cluster_arn, None)

        # Verify the error
        assert 'Client must be provided' in str(excinfo.value)

    def test_get_cluster_policy_invalid_policy_json(self):
        """Test the get_cluster_policy function with an invalid policy JSON."""
        # Arrange
        mock_client = MagicMock()
        expected_response = {'CurrentVersion': '1', 'Policy': 'invalid-json'}
        mock_client.get_cluster_policy.return_value = expected_response

        # Act
        cluster_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        result = get_cluster_policy(cluster_arn, mock_client)

        # Assert
        mock_client.get_cluster_policy.assert_called_once_with(ClusterArn=cluster_arn)
        assert result == expected_response

        # Verify that the policy cannot be parsed as JSON
        with pytest.raises(json.JSONDecodeError):
            json.loads(result['Policy'])
