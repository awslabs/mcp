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

"""Tests for test_migration function."""

import pytest
from awslabs.elasticache_mcp_server.tools.rg import test_migration
from awslabs.elasticache_mcp_server.tools.rg.test_migration import (
    CustomerNodeEndpoint,
    MigrationTestRequest,
)
from unittest.mock import MagicMock, patch


def create_test_request(**kwargs) -> MigrationTestRequest:
    """Create a test request with default values."""
    defaults = {
        'replication_group_id': 'test-rg',
        'customer_node_endpoint_list': [CustomerNodeEndpoint(Address='10.0.0.1', Port=6379)],
    }
    defaults.update(kwargs)
    return MigrationTestRequest(**defaults)


@pytest.fixture
def mock_elasticache_client():
    """Create a mock ElastiCache client."""
    with patch(
        'awslabs.elasticache_mcp_server.common.connection.ElastiCacheConnectionManager.get_connection'
    ) as mock_get_connection:
        mock_client = MagicMock()
        mock_get_connection.return_value = mock_client
        yield mock_client


class TestTestMigration:
    """Tests for the test_migration function."""

    @pytest.mark.asyncio
    async def test_test_migration_basic(self, mock_elasticache_client):
        """Test testing migration with basic parameters."""
        expected_response = {
            'ReplicationGroup': {'ReplicationGroupId': 'test-rg', 'Status': 'available'},
            'TestMigration': {'Status': 'successful'},
        }

        mock_elasticache_client.test_migration.return_value = expected_response

        request = create_test_request()

        response = await test_migration(request)

        mock_elasticache_client.test_migration.assert_called_once_with(
            ReplicationGroupId='test-rg',
            CustomerNodeEndpointList=[{'Address': '10.0.0.1', 'Port': 6379}],
        )
        assert response == expected_response

    @pytest.mark.asyncio
    async def test_test_migration_with_shorthand_endpoint(self, mock_elasticache_client):
        """Test testing migration with shorthand endpoint syntax."""
        expected_response = {
            'ReplicationGroup': {'ReplicationGroupId': 'test-rg', 'Status': 'available'},
            'TestMigration': {'Status': 'successful'},
        }

        mock_elasticache_client.test_migration.return_value = expected_response

        # Test shorthand syntax
        shorthand = 'Address=10.0.0.1,Port=6379'

        request = create_test_request(customer_node_endpoint_list=shorthand)

        response = await test_migration(request)

        mock_elasticache_client.test_migration.assert_called_once_with(
            ReplicationGroupId='test-rg',
            CustomerNodeEndpointList=[{'Address': '10.0.0.1', 'Port': 6379}],
        )
        assert response == expected_response

    @pytest.mark.asyncio
    async def test_test_migration_with_invalid_shorthand_endpoint(self, mock_elasticache_client):
        """Test testing migration with invalid shorthand endpoint syntax."""
        # Test missing Address
        request = create_test_request(customer_node_endpoint_list='Port=6379')

        exception_class = 'ValueError'
        error_message = 'Missing required field: Address'
        mock_exception = type(exception_class, (Exception,), {})
        setattr(mock_elasticache_client.exceptions, exception_class, mock_exception)
        mock_elasticache_client.test_migration.side_effect = mock_exception(error_message)

        response = await test_migration(request)
        assert 'error' in response
        assert error_message in response['error']

        # Test missing Port
        request = create_test_request(customer_node_endpoint_list='Address=10.0.0.1')

        exception_class = 'ValueError'
        error_message = 'Missing required field: Port'
        mock_exception = type(exception_class, (Exception,), {})
        setattr(mock_elasticache_client.exceptions, exception_class, mock_exception)
        mock_elasticache_client.test_migration.side_effect = mock_exception(error_message)

        response = await test_migration(request)
        assert 'error' in response
        assert error_message in response['error']

        # Test invalid Port
        request = create_test_request(customer_node_endpoint_list='Address=10.0.0.1,Port=invalid')

        exception_class = 'ValueError'
        error_message = 'Port must be an integer: invalid'
        mock_exception = type(exception_class, (Exception,), {})
        setattr(mock_elasticache_client.exceptions, exception_class, mock_exception)
        mock_elasticache_client.test_migration.side_effect = mock_exception(error_message)

        response = await test_migration(request)
        assert 'error' in response
        assert error_message in response['error']

        # Test invalid parameter
        request = create_test_request(
            customer_node_endpoint_list='Address=10.0.0.1,InvalidParam=value'
        )

        exception_class = 'ValueError'
        error_message = 'Invalid parameter: InvalidParam'
        mock_exception = type(exception_class, (Exception,), {})
        setattr(mock_elasticache_client.exceptions, exception_class, mock_exception)
        mock_elasticache_client.test_migration.side_effect = mock_exception(error_message)

        response = await test_migration(request)
        assert 'error' in response
        assert error_message in response['error']

    @pytest.mark.asyncio
    async def test_test_migration_with_multiple_endpoints(self, mock_elasticache_client):
        """Test testing migration with multiple endpoints (should fail)."""
        # Test multiple endpoints
        request = create_test_request(
            customer_node_endpoint_list=[
                CustomerNodeEndpoint(Address='10.0.0.1', Port=6379),
                CustomerNodeEndpoint(Address='10.0.0.2', Port=6379),
            ]
        )

        exception_class = 'ValueError'
        error_message = 'CustomerNodeEndpointList should have exactly one element'
        mock_exception = type(exception_class, (Exception,), {})
        setattr(mock_elasticache_client.exceptions, exception_class, mock_exception)
        mock_elasticache_client.test_migration.side_effect = mock_exception(error_message)

        response = await test_migration(request)
        assert 'error' in response
        assert error_message in response['error']

    @pytest.mark.asyncio
    async def test_test_migration_aws_exceptions(self, mock_elasticache_client):
        """Test testing migration with various AWS exceptions."""
        # Test replication group not found
        request = create_test_request(replication_group_id='non-existent-rg')

        exception_class = 'ReplicationGroupNotFoundFault'
        error_message = 'An error occurred: ReplicationGroupNotFoundFault'
        mock_exception = type(exception_class, (Exception,), {})
        setattr(mock_elasticache_client.exceptions, exception_class, mock_exception)
        mock_elasticache_client.test_migration.side_effect = mock_exception(error_message)

        response = await test_migration(request)
        assert 'error' in response
        assert error_message in response['error']

        # Test invalid state
        request = create_test_request()

        exception_class = 'InvalidReplicationGroupStateFault'
        error_message = 'An error occurred: InvalidReplicationGroupStateFault'
        mock_exception = type(exception_class, (Exception,), {})
        setattr(mock_elasticache_client.exceptions, exception_class, mock_exception)
        mock_elasticache_client.test_migration.side_effect = mock_exception(error_message)

        response = await test_migration(request)
        assert 'error' in response
        assert error_message in response['error']

        # Test invalid parameter
        request = create_test_request()

        exception_class = 'InvalidParameterValueException'
        error_message = 'An error occurred: InvalidParameterValueException'
        mock_exception = type(exception_class, (Exception,), {})
        setattr(mock_elasticache_client.exceptions, exception_class, mock_exception)
        mock_elasticache_client.test_migration.side_effect = mock_exception(error_message)

        response = await test_migration(request)
        assert 'error' in response
        assert error_message in response['error']
