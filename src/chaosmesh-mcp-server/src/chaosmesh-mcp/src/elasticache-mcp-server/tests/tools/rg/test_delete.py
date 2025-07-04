"""Tests for delete_replication_group function."""

import pytest
from awslabs.elasticache_mcp_server.context import Context
from awslabs.elasticache_mcp_server.tools.rg import delete_replication_group
from unittest.mock import MagicMock, patch


@pytest.mark.asyncio
async def test_delete_replication_group_readonly_mode():
    """Test deleting a replication group in readonly mode."""
    with patch.object(Context, 'readonly_mode', return_value=True):
        response = await delete_replication_group(replication_group_id='test-rg')
        assert 'error' in response
        assert 'readonly mode' in response['error']


@pytest.fixture
def mock_elasticache_client():
    """Create a mock ElastiCache client."""
    with patch(
        'awslabs.elasticache_mcp_server.common.connection.ElastiCacheConnectionManager.get_connection'
    ) as mock_get_connection:
        mock_client = MagicMock()
        mock_get_connection.return_value = mock_client
        yield mock_client


class TestDeleteReplicationGroup:
    """Tests for the delete_replication_group function."""

    @pytest.mark.asyncio
    async def test_delete_basic_replication_group(self, mock_elasticache_client):
        """Test deleting a replication group with basic parameters."""
        expected_response = {
            'ReplicationGroup': {'ReplicationGroupId': 'test-rg', 'Status': 'deleting'}
        }

        mock_elasticache_client.delete_replication_group.return_value = expected_response

        response = await delete_replication_group(replication_group_id='test-rg')

        mock_elasticache_client.delete_replication_group.assert_called_once_with(
            ReplicationGroupId='test-rg'
        )
        assert response == expected_response

    @pytest.mark.asyncio
    async def test_delete_replication_group_with_all_params(self, mock_elasticache_client):
        """Test deleting a replication group with all optional parameters."""
        expected_response = {
            'ReplicationGroup': {'ReplicationGroupId': 'test-rg', 'Status': 'deleting'}
        }

        mock_elasticache_client.delete_replication_group.return_value = expected_response

        response = await delete_replication_group(
            replication_group_id='test-rg',
            retain_primary_cluster=True,
            final_snapshot_name='final-snapshot',
        )

        mock_elasticache_client.delete_replication_group.assert_called_once_with(
            ReplicationGroupId='test-rg',
            RetainPrimaryCluster='true',
            FinalSnapshotIdentifier='final-snapshot',
        )
        assert response == expected_response

    @pytest.mark.asyncio
    async def test_delete_replication_group_not_found(self, mock_elasticache_client):
        """Test deleting a replication group that doesn't exist."""
        exception_class = 'ReplicationGroupNotFoundFault'
        error_message = 'Replication group nonexistent-rg not found'
        mock_exception = type(exception_class, (Exception,), {})
        setattr(mock_elasticache_client.exceptions, exception_class, mock_exception)
        mock_elasticache_client.delete_replication_group.side_effect = mock_exception(
            error_message
        )

        response = await delete_replication_group(replication_group_id='nonexistent-rg')

        mock_elasticache_client.delete_replication_group.assert_called_once_with(
            ReplicationGroupId='nonexistent-rg'
        )
        assert 'error' in response
        assert error_message in response['error']
