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
"""Tests for simple cp_api_connection functions."""

import pytest
from awslabs.postgres_mcp_server.connection.cp_api_connection import (
    internal_get_instance_properties,
)
from botocore.exceptions import ClientError
from unittest.mock import MagicMock, patch


class TestInternalGetInstanceProperties:
    """Tests for internal_get_instance_properties function."""

    @patch('awslabs.postgres_mcp_server.connection.cp_api_connection.internal_create_rds_client')
    def test_get_instance_properties_success(self, mock_create_client):
        """Test successfully getting instance properties."""
        mock_rds_client = MagicMock()
        mock_create_client.return_value = mock_rds_client

        mock_paginator = MagicMock()
        mock_rds_client.get_paginator.return_value = mock_paginator

        mock_paginator.paginate.return_value = [
            {
                'DBInstances': [
                    {
                        'DBInstanceIdentifier': 'other-instance',
                        'Endpoint': {'Address': 'other.us-east-1.rds.amazonaws.com'},
                    },
                    {
                        'DBInstanceIdentifier': 'test-instance',
                        'DBInstanceArn': 'arn:aws:rds:us-east-1:123456789012:db:test-instance',
                        'MasterUsername': 'postgres',
                        'Endpoint': {
                            'Address': 'test-instance.abc123.us-east-1.rds.amazonaws.com',
                            'Port': 5432,
                        },
                        'MasterUserSecret': {
                            'SecretArn': 'arn:aws:secretsmanager:us-east-1:123456789012:secret:test-secret'
                        },
                    },
                ]
            }
        ]

        result = internal_get_instance_properties(
            'test-instance.abc123.us-east-1.rds.amazonaws.com', 'us-east-1'
        )

        assert result['DBInstanceIdentifier'] == 'test-instance'
        assert result['MasterUsername'] == 'postgres'
        assert result['Endpoint']['Port'] == 5432
        mock_create_client.assert_called_once_with(region='us-east-1')

    @patch('awslabs.postgres_mcp_server.connection.cp_api_connection.internal_create_rds_client')
    def test_get_instance_properties_not_found(self, mock_create_client):
        """Test getting instance properties when instance not found."""
        mock_rds_client = MagicMock()
        mock_create_client.return_value = mock_rds_client

        mock_paginator = MagicMock()
        mock_rds_client.get_paginator.return_value = mock_paginator

        mock_paginator.paginate.return_value = [
            {
                'DBInstances': [
                    {
                        'DBInstanceIdentifier': 'other-instance',
                        'Endpoint': {'Address': 'other.us-east-1.rds.amazonaws.com'},
                    }
                ]
            }
        ]

        with pytest.raises(ValueError, match='AWS error fetching instance by endpoint'):
            internal_get_instance_properties(
                'nonexistent.us-east-1.rds.amazonaws.com', 'us-east-1'
            )

    @patch('awslabs.postgres_mcp_server.connection.cp_api_connection.internal_create_rds_client')
    def test_get_instance_properties_client_error(self, mock_create_client):
        """Test getting instance properties with AWS client error."""
        mock_rds_client = MagicMock()
        mock_create_client.return_value = mock_rds_client

        mock_paginator = MagicMock()
        mock_rds_client.get_paginator.return_value = mock_paginator

        mock_paginator.paginate.side_effect = ClientError(
            {'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}}, 'DescribeDBInstances'
        )

        with pytest.raises(ClientError):
            internal_get_instance_properties('test.us-east-1.rds.amazonaws.com', 'us-east-1')

    @patch('awslabs.postgres_mcp_server.connection.cp_api_connection.internal_create_rds_client')
    def test_get_instance_properties_generic_exception(self, mock_create_client):
        """Test getting instance properties with generic exception."""
        mock_rds_client = MagicMock()
        mock_create_client.return_value = mock_rds_client

        mock_paginator = MagicMock()
        mock_rds_client.get_paginator.return_value = mock_paginator

        mock_paginator.paginate.side_effect = Exception('Unexpected error')

        with pytest.raises(Exception, match='Unexpected error'):
            internal_get_instance_properties('test.us-east-1.rds.amazonaws.com', 'us-east-1')

    @patch('awslabs.postgres_mcp_server.connection.cp_api_connection.internal_create_rds_client')
    def test_get_instance_properties_multiple_pages(self, mock_create_client):
        """Test getting instance properties across multiple pages."""
        mock_rds_client = MagicMock()
        mock_create_client.return_value = mock_rds_client

        mock_paginator = MagicMock()
        mock_rds_client.get_paginator.return_value = mock_paginator

        # Simulate multiple pages
        mock_paginator.paginate.return_value = [
            {
                'DBInstances': [
                    {
                        'DBInstanceIdentifier': 'instance1',
                        'Endpoint': {'Address': 'instance1.us-east-1.rds.amazonaws.com'},
                    }
                ]
            },
            {
                'DBInstances': [
                    {
                        'DBInstanceIdentifier': 'target-instance',
                        'Endpoint': {'Address': 'target.us-east-1.rds.amazonaws.com'},
                        'MasterUsername': 'admin',
                    }
                ]
            },
        ]

        result = internal_get_instance_properties(
            'target.us-east-1.rds.amazonaws.com', 'us-east-1'
        )

        assert result['DBInstanceIdentifier'] == 'target-instance'
        assert result['MasterUsername'] == 'admin'
