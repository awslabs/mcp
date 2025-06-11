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

"""Tests for complete_migration function."""

import pytest
from awslabs.elasticache_mcp_server.context import Context
from awslabs.elasticache_mcp_server.tools.rg import complete_migration
from awslabs.elasticache_mcp_server.tools.rg.complete_migration import CompleteMigrationRequest
from unittest.mock import MagicMock, patch


@pytest.mark.asyncio
async def test_complete_migration_readonly_mode():
    """Test completing migration in readonly mode."""
    with patch.object(Context, 'readonly_mode', return_value=True):
        request = CompleteMigrationRequest(replication_group_id='test-rg')
        result = await complete_migration(request)
        assert 'error' in result
        assert 'readonly mode' in result['error']


def create_test_request(**kwargs) -> CompleteMigrationRequest:
    """Create a test request with default values."""
    defaults = {
        'replication_group_id': 'test-rg',
        'force': None,
    }
    defaults.update(kwargs)
    return CompleteMigrationRequest(**defaults)


@pytest.fixture
def mock_elasticache_client():
    """Create a mock ElastiCache client."""
    with patch(
        'awslabs.elasticache_mcp_server.common.connection.ElastiCacheConnectionManager.get_connection'
    ) as mock_get_connection:
        mock_client = MagicMock()
        mock_get_connection.return_value = mock_client
        yield mock_client


class TestCompleteMigration:
    """Tests for the complete_migration function."""

    @pytest.mark.asyncio
    async def test_complete_migration_basic(self, mock_elasticache_client):
        """Test completing migration with basic parameters."""
        expected_response = {
            'ReplicationGroup': {'ReplicationGroupId': 'test-rg', 'Status': 'available'},
            'Migration': {'Status': 'completed'},
        }

        mock_elasticache_client.complete_migration.return_value = expected_response

        request = create_test_request()

        response = await complete_migration(request)

        mock_elasticache_client.complete_migration.assert_called_once_with(
            ReplicationGroupId='test-rg',
        )
        assert response == expected_response

    @pytest.mark.asyncio
    async def test_complete_migration_with_force(self, mock_elasticache_client):
        """Test completing migration with force parameter."""
        expected_response = {
            'ReplicationGroup': {'ReplicationGroupId': 'test-rg', 'Status': 'available'},
            'Migration': {'Status': 'completed'},
        }

        mock_elasticache_client.complete_migration.return_value = expected_response

        # Test with force=True
        request = create_test_request(force=True)

        response = await complete_migration(request)

        mock_elasticache_client.complete_migration.assert_called_once_with(
            ReplicationGroupId='test-rg',
            Force=True,
        )
        assert response == expected_response

        # Reset mock
        mock_elasticache_client.reset_mock()

        # Test with force=False
        request = create_test_request(force=False)

        response = await complete_migration(request)

        mock_elasticache_client.complete_migration.assert_called_once_with(
            ReplicationGroupId='test-rg',
            Force=False,
        )
        assert response == expected_response

    @pytest.mark.asyncio
    async def test_complete_migration_aws_exceptions(self, mock_elasticache_client):
        """Test completing migration with various AWS exceptions."""
        # Test replication group not found
        request = create_test_request(replication_group_id='non-existent-rg')

        exception_class = 'ReplicationGroupNotFoundFault'
        error_message = 'An error occurred: ReplicationGroupNotFoundFault'
        mock_exception = type(exception_class, (Exception,), {})
        setattr(mock_elasticache_client.exceptions, exception_class, mock_exception)
        mock_elasticache_client.complete_migration.side_effect = mock_exception(error_message)

        response = await complete_migration(request)
        assert 'error' in response
        assert error_message in response['error']

        # Test invalid state
        request = create_test_request()

        exception_class = 'InvalidReplicationGroupStateFault'
        error_message = 'An error occurred: InvalidReplicationGroupStateFault'
        mock_exception = type(exception_class, (Exception,), {})
        setattr(mock_elasticache_client.exceptions, exception_class, mock_exception)
        mock_elasticache_client.complete_migration.side_effect = mock_exception(error_message)

        response = await complete_migration(request)
        assert 'error' in response
        assert error_message in response['error']

        # Test invalid parameter
        request = create_test_request()

        exception_class = 'InvalidParameterValueException'
        error_message = 'An error occurred: InvalidParameterValueException'
        mock_exception = type(exception_class, (Exception,), {})
        setattr(mock_elasticache_client.exceptions, exception_class, mock_exception)
        mock_elasticache_client.complete_migration.side_effect = mock_exception(error_message)

        response = await complete_migration(request)
        assert 'error' in response
        assert error_message in response['error']

        # Test migration not in progress
        request = create_test_request()

        exception_class = 'MigrationNotFoundFault'
        error_message = 'An error occurred: MigrationNotFoundFault'
        mock_exception = type(exception_class, (Exception,), {})
        setattr(mock_elasticache_client.exceptions, exception_class, mock_exception)
        mock_elasticache_client.complete_migration.side_effect = mock_exception(error_message)

        response = await complete_migration(request)
        assert 'error' in response
        assert error_message in response['error']
