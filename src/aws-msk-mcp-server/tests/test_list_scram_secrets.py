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

"""Tests for the list_scram_secrets module."""

import pytest
from awslabs.aws_msk_mcp_server.tools.read_cluster.list_scram_secrets import list_scram_secrets
from botocore.exceptions import ClientError
from unittest.mock import MagicMock


class TestListScramSecrets:
    """Tests for the list_scram_secrets module."""

    def test_list_scram_secrets_basic(self):
        """Test the list_scram_secrets function with basic parameters."""
        # Arrange
        mock_client = MagicMock()
        expected_response = {
            'SecretArnList': [
                'arn:aws:secretsmanager:us-east-1:123456789012:secret:test-secret-1',
                'arn:aws:secretsmanager:us-east-1:123456789012:secret:test-secret-2',
            ]
        }
        mock_client.list_scram_secrets.return_value = expected_response

        # Act
        cluster_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        result = list_scram_secrets(cluster_arn, mock_client)

        # Assert
        mock_client.list_scram_secrets.assert_called_once_with(ClusterArn=cluster_arn)
        assert result == expected_response
        assert 'SecretArnList' in result
        assert len(result['SecretArnList']) == 2
        assert (
            'arn:aws:secretsmanager:us-east-1:123456789012:secret:test-secret-1'
            in result['SecretArnList']
        )
        assert (
            'arn:aws:secretsmanager:us-east-1:123456789012:secret:test-secret-2'
            in result['SecretArnList']
        )

    def test_list_scram_secrets_with_pagination(self):
        """Test the list_scram_secrets function with pagination parameters."""
        # Arrange
        mock_client = MagicMock()
        expected_response = {
            'SecretArnList': [
                'arn:aws:secretsmanager:us-east-1:123456789012:secret:test-secret-1'
            ],
            'NextToken': 'next-token-value',
        }
        mock_client.list_scram_secrets.return_value = expected_response

        # Act
        cluster_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        max_results = 5
        next_token = 'token'
        result = list_scram_secrets(cluster_arn, mock_client, max_results, next_token)

        # Assert
        mock_client.list_scram_secrets.assert_called_once_with(
            ClusterArn=cluster_arn, MaxResults=max_results, NextToken=next_token
        )
        assert result == expected_response
        assert 'SecretArnList' in result
        assert 'NextToken' in result
        assert result['NextToken'] == 'next-token-value'

    def test_list_scram_secrets_empty_response(self):
        """Test the list_scram_secrets function with an empty response."""
        # Arrange
        mock_client = MagicMock()
        expected_response = {'SecretArnList': []}
        mock_client.list_scram_secrets.return_value = expected_response

        # Act
        cluster_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        result = list_scram_secrets(cluster_arn, mock_client)

        # Assert
        mock_client.list_scram_secrets.assert_called_once_with(ClusterArn=cluster_arn)
        assert result == expected_response
        assert 'SecretArnList' in result
        assert len(result['SecretArnList']) == 0

    def test_list_scram_secrets_error(self):
        """Test the list_scram_secrets function when the API call fails."""
        # Arrange
        mock_client = MagicMock()
        mock_client.list_scram_secrets.side_effect = ClientError(
            {'Error': {'Code': 'ResourceNotFoundException', 'Message': 'Cluster not found'}},
            'ListScramSecrets',
        )

        # Act & Assert
        cluster_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        with pytest.raises(ClientError) as excinfo:
            list_scram_secrets(cluster_arn, mock_client)

        # Verify the error
        assert 'ResourceNotFoundException' in str(excinfo.value)
        assert 'Cluster not found' in str(excinfo.value)
        mock_client.list_scram_secrets.assert_called_once_with(ClusterArn=cluster_arn)

    def test_list_scram_secrets_missing_client(self):
        """Test the list_scram_secrets function with a missing client."""
        # Act & Assert
        cluster_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        with pytest.raises(ValueError) as excinfo:
            list_scram_secrets(cluster_arn, None)

        # Verify the error
        assert 'Client must be provided' in str(excinfo.value)
