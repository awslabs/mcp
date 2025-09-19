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

"""Tests for the Database Migration Service MCP Server."""

import pytest
from awslabs.dms_mcp_server.context import Context
from awslabs.dms_mcp_server.models import (
    EndpointListResponse,
    ReplicationInstanceListResponse,
    ReplicationTaskListResponse,
)
from awslabs.dms_mcp_server.tools.endpoints import describe_endpoints
from awslabs.dms_mcp_server.tools.instances import (
    describe_replication_instances,
)
from awslabs.dms_mcp_server.tools.tasks import describe_replication_tasks
from unittest.mock import Mock, patch


@pytest.fixture
def mock_dms_client():
    """Mock DMS client for testing."""
    # Patch get_dms_client in all tool modules
    patches = [
        patch('awslabs.dms_mcp_server.tools.instances.get_dms_client'),
        patch('awslabs.dms_mcp_server.tools.endpoints.get_dms_client'),
        patch('awslabs.dms_mcp_server.tools.tasks.get_dms_client'),
    ]

    with (
        patches[0] as mock_get_client_instances,
        patches[1] as mock_get_client_endpoints,
        patches[2] as mock_get_client_tasks,
    ):
        mock_dms = Mock()
        mock_get_client_instances.return_value = mock_dms
        mock_get_client_endpoints.return_value = mock_dms
        mock_get_client_tasks.return_value = mock_dms

        # Mock common responses
        mock_dms.describe_replication_instances.return_value = {
            'ReplicationInstances': [
                {
                    'ReplicationInstanceIdentifier': 'test-instance',
                    'ReplicationInstanceArn': 'arn:aws:dms:us-east-1:123456789012:rep:test-instance',
                    'ReplicationInstanceClass': 'dms.t3.micro',
                    'EngineVersion': '3.4.7',
                    'ReplicationInstanceStatus': 'available',
                    'AllocatedStorage': 20,
                    'MultiAZ': False,
                    'AutoMinorVersionUpgrade': True,
                }
            ],
            'Marker': None,
        }

        mock_dms.describe_endpoints.return_value = {
            'Endpoints': [
                {
                    'EndpointIdentifier': 'test-endpoint',
                    'EndpointArn': 'arn:aws:dms:us-east-1:123456789012:endpoint:test-endpoint',
                    'EndpointType': 'source',
                    'EngineName': 'mysql',
                    'Status': 'active',
                }
            ],
            'Marker': None,
        }

        mock_dms.describe_replication_tasks.return_value = {
            'ReplicationTasks': [
                {
                    'ReplicationTaskIdentifier': 'test-task',
                    'ReplicationTaskArn': 'arn:aws:dms:us-east-1:123456789012:task:test-task',
                    'SourceEndpointArn': 'arn:aws:dms:us-east-1:123456789012:endpoint:test-source',
                    'TargetEndpointArn': 'arn:aws:dms:us-east-1:123456789012:endpoint:test-target',
                    'ReplicationInstanceArn': 'arn:aws:dms:us-east-1:123456789012:rep:test-instance',
                    'MigrationType': 'full-load',
                    'TableMappings': '{}',
                    'Status': 'ready',
                }
            ],
            'Marker': None,
        }

        yield mock_dms


@pytest.mark.asyncio
class TestDescribeReplicationInstances:
    """Tests for replication instance operations."""

    async def test_describe_all_instances(self, mock_dms_client):
        """Test describing all replication instances."""
        # Act
        result = await describe_replication_instances(
            replication_instance_identifier=None, max_records=20, marker=None
        )

        # Assert
        assert isinstance(result, ReplicationInstanceListResponse)
        assert len(result.replication_instances) == 1
        assert result.replication_instances[0].replication_instance_identifier == 'test-instance'
        assert result.replication_instances[0].replication_instance_class == 'dms.t3.micro'
        assert result.replication_instances[0].replication_instance_status == 'available'

    async def test_describe_specific_instance(self, mock_dms_client):
        """Test describing a specific replication instance."""
        # Act
        await describe_replication_instances(
            replication_instance_identifier='test-instance', max_records=20, marker=None
        )

        # Assert
        mock_dms_client.describe_replication_instances.assert_called_once()
        call_args = mock_dms_client.describe_replication_instances.call_args[1]
        assert 'Filters' in call_args
        assert call_args['Filters'][0]['Name'] == 'replication-instance-id'
        assert call_args['Filters'][0]['Values'] == ['test-instance']

    async def test_describe_with_pagination(self, mock_dms_client):
        """Test describing replication instances with pagination."""
        # Act
        await describe_replication_instances(
            replication_instance_identifier=None, max_records=50, marker='test-marker'
        )

        # Assert
        call_args = mock_dms_client.describe_replication_instances.call_args[1]
        assert call_args['MaxRecords'] == 50
        assert call_args['Marker'] == 'test-marker'


@pytest.mark.asyncio
class TestDescribeEndpoints:
    """Tests for endpoint operations."""

    async def test_describe_all_endpoints(self, mock_dms_client):
        """Test describing all endpoints."""
        # Act
        result = await describe_endpoints(
            endpoint_identifier=None,
            endpoint_type=None,
            engine_name=None,
            max_records=20,
            marker=None,
        )

        # Assert
        assert isinstance(result, EndpointListResponse)
        assert len(result.endpoints) == 1
        assert result.endpoints[0].endpoint_identifier == 'test-endpoint'
        assert result.endpoints[0].endpoint_type == 'source'
        assert result.endpoints[0].engine_name == 'mysql'

    async def test_describe_endpoints_with_filters(self, mock_dms_client):
        """Test describing endpoints with filters."""
        # Act
        await describe_endpoints(
            endpoint_identifier='test-endpoint',
            endpoint_type='source',
            engine_name='mysql',
            max_records=20,
            marker=None,
        )

        # Assert
        call_args = mock_dms_client.describe_endpoints.call_args[1]
        assert 'Filters' in call_args
        assert len(call_args['Filters']) == 3


@pytest.mark.asyncio
class TestDescribeReplicationTasks:
    """Tests for replication task operations."""

    async def test_describe_all_tasks(self, mock_dms_client):
        """Test describing all replication tasks."""
        # Act
        result = await describe_replication_tasks(
            replication_task_identifier=None,
            replication_instance_arn=None,
            migration_type=None,
            max_records=20,
            marker=None,
            with_statistics=False,
        )

        # Assert
        assert isinstance(result, ReplicationTaskListResponse)
        assert len(result.replication_tasks) == 1
        assert result.replication_tasks[0].replication_task_identifier == 'test-task'
        assert result.replication_tasks[0].migration_type == 'full-load'

    async def test_describe_tasks_with_filters(self, mock_dms_client):
        """Test describing replication tasks with filters."""
        # Act
        await describe_replication_tasks(
            replication_task_identifier='test-task',
            replication_instance_arn=None,
            migration_type='full-load',
            max_records=20,
            marker=None,
            with_statistics=False,
        )

        # Assert
        call_args = mock_dms_client.describe_replication_tasks.call_args[1]
        assert 'Filters' in call_args
        assert (
            len(call_args['Filters']) == 2
        )  # replication_task_identifier + migration_type (replication_instance_arn=None doesn't create filter)


class TestWriteAccess:
    """Tests for write access control."""

    def test_require_write_access_enabled(self):
        """Test write access when enabled."""
        # Arrange
        Context.initialize(readonly=False)

        # Act & Assert - should not raise
        Context.require_write_access()

    def test_require_write_access_disabled(self):
        """Test write access when disabled."""
        # Arrange
        Context.initialize(readonly=True)

        # Act & Assert - should raise
        with pytest.raises(ValueError, match='Your DMS MCP server does not allow writes'):
            Context.require_write_access()
