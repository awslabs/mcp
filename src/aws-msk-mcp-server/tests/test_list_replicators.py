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

"""Tests for the list_replicators module."""

import pytest
from awslabs.aws_msk_mcp_server.tools.replicator.list_replicators import list_replicators
from botocore.exceptions import ClientError
from unittest.mock import MagicMock


class TestListReplicators:
    """Tests for the list_replicators module."""

    def test_list_replicators_basic(self):
        """Test the list_replicators function with basic parameters."""
        # Arrange
        mock_client = MagicMock()
        expected_response = {
            'ReplicatorInfoList': [
                {
                    'ReplicatorArn': 'arn:aws:kafka:us-east-1:123456789012:replicator/test-replicator-1/abcdef',
                    'ReplicatorName': 'test-replicator-1',
                    'ReplicatorState': 'ACTIVE',
                    'CreationTime': '2025-06-20T10:00:00.000Z',
                },
                {
                    'ReplicatorArn': 'arn:aws:kafka:us-east-1:123456789012:replicator/test-replicator-2/abcdef',
                    'ReplicatorName': 'test-replicator-2',
                    'ReplicatorState': 'CREATING',
                    'CreationTime': '2025-06-20T11:00:00.000Z',
                },
            ]
        }
        mock_client.list_replicators.return_value = expected_response

        # Act
        result = list_replicators(mock_client)

        # Assert
        mock_client.list_replicators.assert_called_once_with()
        assert result == expected_response

    def test_list_replicators_with_pagination(self):
        """Test the list_replicators function with pagination parameters."""
        # Arrange
        mock_client = MagicMock()
        expected_response = {
            'ReplicatorInfoList': [
                {
                    'ReplicatorArn': 'arn:aws:kafka:us-east-1:123456789012:replicator/test-replicator-3/abcdef',
                    'ReplicatorName': 'test-replicator-3',
                    'ReplicatorState': 'ACTIVE',
                    'CreationTime': '2025-06-20T12:00:00.000Z',
                }
            ],
            'NextToken': 'next-token-value',
        }
        mock_client.list_replicators.return_value = expected_response

        # Act
        max_results = 10
        next_token = 'token-value'
        result = list_replicators(mock_client, max_results, next_token)

        # Assert
        mock_client.list_replicators.assert_called_once_with(
            MaxResults=max_results, NextToken=next_token
        )
        assert result == expected_response

    def test_list_replicators_empty_response(self):
        """Test the list_replicators function with an empty response."""
        # Arrange
        mock_client = MagicMock()
        expected_response = {'ReplicatorInfoList': []}
        mock_client.list_replicators.return_value = expected_response

        # Act
        result = list_replicators(mock_client)

        # Assert
        mock_client.list_replicators.assert_called_once_with()
        assert result == expected_response
        assert len(result['ReplicatorInfoList']) == 0

    def test_list_replicators_error(self):
        """Test the list_replicators function when the API call fails."""
        # Arrange
        mock_client = MagicMock()
        mock_client.list_replicators.side_effect = ClientError(
            {'Error': {'Code': 'InternalServerError', 'Message': 'Internal server error'}},
            'ListReplicators',
        )

        # Act & Assert
        with pytest.raises(ClientError) as excinfo:
            list_replicators(mock_client)

        # Verify the error
        assert 'InternalServerError' in str(excinfo.value)
        assert 'Internal server error' in str(excinfo.value)
        mock_client.list_replicators.assert_called_once_with()

    def test_list_replicators_missing_client(self):
        """Test the list_replicators function with a missing client."""
        # Act & Assert
        with pytest.raises(ValueError) as excinfo:
            list_replicators(None)

        # Verify the error
        assert 'Client must be provided' in str(excinfo.value)
