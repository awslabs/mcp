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

"""Tests for replication task operations."""

import pytest
from awslabs.dms_mcp_server.context import Context
from awslabs.dms_mcp_server.models import (
    ReplicationTaskListResponse,
    ReplicationTaskResponse,
)
from awslabs.dms_mcp_server.tools.tasks import (
    create_replication_task,
    describe_replication_tasks,
    describe_table_statistics,
    reload_replication_task_tables,
    start_replication_task,
    stop_replication_task,
)
from botocore.exceptions import ClientError
from unittest.mock import Mock, patch


@pytest.fixture
def mock_dms_client():
    """Mock DMS client for testing."""
    with patch('awslabs.dms_mcp_server.tools.tasks.get_dms_client') as mock_get_client:
        mock_dms = Mock()
        mock_get_client.return_value = mock_dms

        # Mock describe_replication_tasks response
        mock_dms.describe_replication_tasks.return_value = {
            'ReplicationTasks': [
                {
                    'ReplicationTaskIdentifier': 'test-task',
                    'SourceEndpointArn': 'arn:aws:dms:us-east-1:123456789012:endpoint:source',
                    'TargetEndpointArn': 'arn:aws:dms:us-east-1:123456789012:endpoint:target',
                    'ReplicationInstanceArn': 'arn:aws:dms:us-east-1:123456789012:rep:test-instance',
                    'MigrationType': 'full-load',
                    'TableMappings': '{"rules":[{"rule-type":"selection","rule-id":"1","rule-name":"1","object-locator":{"schema-name":"%","table-name":"%"},"rule-action":"include"}]}',
                    'ReplicationTaskSettings': '{}',
                    'Status': 'ready',
                    'LastFailureMessage': None,
                    'StopReason': None,
                    'ReplicationTaskCreationDate': '2023-01-01T00:00:00Z',
                    'ReplicationTaskStartDate': None,
                    'CdcStartPosition': None,
                    'CdcStopPosition': None,
                    'RecoveryCheckpoint': None,
                    'ReplicationTaskArn': 'arn:aws:dms:us-east-1:123456789012:task:test-task',
                    'ReplicationTaskStats': {
                        'FullLoadProgressPercent': 0,
                        'ElapsedTimeMillis': 0,
                        'TablesLoaded': 0,
                        'TablesLoading': 0,
                        'TablesQueued': 0,
                        'TablesErrored': 0,
                    },
                }
            ],
            'Marker': None,
        }

        # Mock describe_table_statistics response
        mock_dms.describe_table_statistics.return_value = {
            'ReplicationTaskArn': 'arn:aws:dms:us-east-1:123456789012:task:test-task',
            'TableStatistics': [
                {
                    'SchemaName': 'public',
                    'TableName': 'users',
                    'Inserts': 1000,
                    'Deletes': 10,
                    'Updates': 50,
                    'Ddls': 1,
                    'FullLoadRows': 1000,
                    'FullLoadCondtnlChkFailedRows': 0,
                    'FullLoadErrorRows': 0,
                    'FullLoadStartTime': '2023-01-01T00:00:00Z',
                    'FullLoadEndTime': '2023-01-01T01:00:00Z',
                    'FullLoadReloaded': False,
                    'LastUpdateTime': '2023-01-01T01:00:00Z',
                    'TableState': 'Table completed',
                    'ValidationPendingRecords': 0,
                    'ValidationFailedRecords': 0,
                    'ValidationSuspendedRecords': 0,
                    'ValidationState': 'Not enabled',
                }
            ],
            'Marker': None,
        }

        # Mock reload_tables response (returns empty response)
        mock_dms.reload_tables.return_value = {}

        # Mock create_replication_task response
        mock_dms.create_replication_task.return_value = {
            'ReplicationTask': {
                'ReplicationTaskIdentifier': 'new-task',
                'SourceEndpointArn': 'arn:aws:dms:us-east-1:123456789012:endpoint:source',
                'TargetEndpointArn': 'arn:aws:dms:us-east-1:123456789012:endpoint:target',
                'ReplicationInstanceArn': 'arn:aws:dms:us-east-1:123456789012:rep:test-instance',
                'MigrationType': 'full-load',
                'TableMappings': '{"rules":[{"rule-type":"selection","rule-id":"1","rule-name":"1","object-locator":{"schema-name":"public","table-name":"%"},"rule-action":"include"}]}',
                'ReplicationTaskSettings': '{"TargetMetadata":{"TargetSchema":"","SupportLobs":true}}',
                'Status': 'creating',
                'ReplicationTaskArn': 'arn:aws:dms:us-east-1:123456789012:task:new-task',
                'ReplicationTaskCreationDate': '2023-01-01T00:00:00Z',
            }
        }

        # Mock start_replication_task response
        mock_dms.start_replication_task.return_value = {
            'ReplicationTask': {
                'ReplicationTaskIdentifier': 'started-task',
                'SourceEndpointArn': 'arn:aws:dms:us-east-1:123456789012:endpoint:source',
                'TargetEndpointArn': 'arn:aws:dms:us-east-1:123456789012:endpoint:target',
                'ReplicationInstanceArn': 'arn:aws:dms:us-east-1:123456789012:rep:test-instance',
                'MigrationType': 'full-load-and-cdc',
                'TableMappings': '{"rules":[{"rule-type":"selection","rule-id":"1","rule-name":"1","object-locator":{"schema-name":"public","table-name":"%"},"rule-action":"include"}]}',
                'ReplicationTaskSettings': '{"TargetMetadata":{"TargetSchema":"","SupportLobs":true}}',
                'Status': 'starting',
                'ReplicationTaskArn': 'arn:aws:dms:us-east-1:123456789012:task:started-task',
                'ReplicationTaskCreationDate': '2023-01-01T00:00:00Z',
                'ReplicationTaskStartDate': '2023-01-01T01:00:00Z',
            }
        }

        # Mock stop_replication_task response
        mock_dms.stop_replication_task.return_value = {
            'ReplicationTask': {
                'ReplicationTaskIdentifier': 'stopped-task',
                'SourceEndpointArn': 'arn:aws:dms:us-east-1:123456789012:endpoint:source',
                'TargetEndpointArn': 'arn:aws:dms:us-east-1:123456789012:endpoint:target',
                'ReplicationInstanceArn': 'arn:aws:dms:us-east-1:123456789012:rep:test-instance',
                'MigrationType': 'full-load-and-cdc',
                'TableMappings': '{"rules":[{"rule-type":"selection","rule-id":"1","rule-name":"1","object-locator":{"schema-name":"public","table-name":"%"},"rule-action":"include"}]}',
                'ReplicationTaskSettings': '{"TargetMetadata":{"TargetSchema":"","SupportLobs":true}}',
                'Status': 'stopping',
                'ReplicationTaskArn': 'arn:aws:dms:us-east-1:123456789012:task:stopped-task',
                'ReplicationTaskCreationDate': '2023-01-01T00:00:00Z',
                'ReplicationTaskStartDate': '2023-01-01T01:00:00Z',
            }
        }

        yield mock_dms


@pytest.mark.asyncio
class TestDescribeReplicationTasks:
    """Tests for describe_replication_tasks function."""

    async def test_describe_all_tasks(self, mock_dms_client):
        """Test describing all replication tasks."""
        result = await describe_replication_tasks()

        assert isinstance(result, ReplicationTaskListResponse)
        assert len(result.replication_tasks) == 1
        assert result.replication_tasks[0].replication_task_identifier == 'test-task'
        assert result.replication_tasks[0].migration_type == 'full-load'
        assert result.replication_tasks[0].status == 'ready'

        mock_dms_client.describe_replication_tasks.assert_called_once()

    async def test_describe_tasks_with_filters(self, mock_dms_client):
        """Test describing tasks with filters."""
        await describe_replication_tasks(
            replication_task_identifier='test-task',
            replication_instance_arn=None,
            migration_type='full-load',
            max_records=20,
            marker=None,
            with_statistics=False,
        )

        call_args = mock_dms_client.describe_replication_tasks.call_args[1]
        assert 'Filters' in call_args
        # Only 2 filters should be created: replication-task-id and migration-type
        # replication_instance_arn=None should not create a filter
        assert len(call_args['Filters']) == 2

    async def test_describe_tasks_with_statistics(self, mock_dms_client):
        """Test describing tasks with statistics included."""
        await describe_replication_tasks(with_statistics=True)

        call_args = mock_dms_client.describe_replication_tasks.call_args[1]
        assert call_args['WithoutSettings'] is False


@pytest.mark.asyncio
class TestDescribeTableStatistics:
    """Tests for describe_table_statistics function."""

    async def test_describe_table_statistics(self, mock_dms_client):
        """Test describing table statistics."""
        result = await describe_table_statistics(
            replication_task_arn='arn:aws:dms:us-east-1:123456789012:task:test-task'
        )

        assert isinstance(result, dict)
        assert (
            result['replication_task_arn'] == 'arn:aws:dms:us-east-1:123456789012:task:test-task'
        )
        assert result['total_tables'] == 1
        assert 'table_statistics' in result

        table_stat = result['table_statistics'][0]
        assert table_stat['schema_name'] == 'public'
        assert table_stat['table_name'] == 'users'
        assert table_stat['insert_count'] == 1000
        assert table_stat['delete_count'] == 10
        assert table_stat['update_count'] == 50

    async def test_describe_table_statistics_with_filters(self, mock_dms_client):
        """Test describing table statistics with filters."""
        filters = [{'Name': 'schema-name', 'Values': ['public']}]
        await describe_table_statistics(
            replication_task_arn='arn:aws:dms:us-east-1:123456789012:task:test-task',
            filters=filters,
        )

        call_args = mock_dms_client.describe_table_statistics.call_args[1]
        assert call_args['Filters'] == filters


@pytest.mark.asyncio
class TestReloadReplicationTaskTables:
    """Tests for reload_replication_task_tables function."""

    async def test_reload_requires_write_access(self, mock_dms_client):
        """Test that reload requires write access."""
        Context.initialize(readonly=True)

        with pytest.raises(ValueError, match='Your DMS MCP server does not allow writes'):
            await reload_replication_task_tables(
                replication_task_arn='arn:aws:dms:us-east-1:123456789012:task:test-task',
                tables_to_reload=[{'schema-name': 'public', 'table-name': 'users'}],
            )

    async def test_reload_tables_success(self, mock_dms_client):
        """Test successful table reload."""
        Context.initialize(readonly=False)

        result = await reload_replication_task_tables(
            replication_task_arn='arn:aws:dms:us-east-1:123456789012:task:test-task',
            tables_to_reload=[{'schema-name': 'public', 'table-name': 'users'}],
            reload_option='data-reload',
        )

        assert isinstance(result, str)
        assert 'public.users' in result
        assert 'data-reload' in result

        call_args = mock_dms_client.reload_tables.call_args[1]
        assert (
            call_args['ReplicationTaskArn'] == 'arn:aws:dms:us-east-1:123456789012:task:test-task'
        )
        assert call_args['TablesToReload'] == [{'SchemaName': 'public', 'TableName': 'users'}]
        assert call_args['ReloadOption'] == 'data-reload'

    async def test_reload_tables_invalid_format(self, mock_dms_client):
        """Test reload with invalid table format."""
        Context.initialize(readonly=False)

        with pytest.raises(
            ValueError, match="Each table must have 'schema-name' and 'table-name' keys"
        ):
            await reload_replication_task_tables(
                replication_task_arn='arn:aws:dms:us-east-1:123456789012:task:test-task',
                tables_to_reload=[{'schema': 'public', 'table': 'users'}],  # Wrong keys
            )


@pytest.mark.asyncio
class TestCreateReplicationTask:
    """Tests for create_replication_task function."""

    async def test_create_requires_write_access(self, mock_dms_client):
        """Test that create requires write access."""
        Context.initialize(readonly=True)

        with pytest.raises(ValueError, match='Your DMS MCP server does not allow writes'):
            await create_replication_task(
                replication_task_identifier='test-task',
                source_endpoint_arn='arn:aws:dms:us-east-1:123456789012:endpoint:source',
                target_endpoint_arn='arn:aws:dms:us-east-1:123456789012:endpoint:target',
                replication_instance_arn='arn:aws:dms:us-east-1:123456789012:rep:test-instance',
                migration_type='full-load',
                table_mappings='{"rules":[{"rule-type":"selection","rule-id":"1","rule-name":"1","object-locator":{"schema-name":"public","table-name":"%"},"rule-action":"include"}]}',
            )

    async def test_create_task_success(self, mock_dms_client):
        """Test successful task creation."""
        Context.initialize(readonly=False)

        result = await create_replication_task(
            replication_task_identifier='new-task',
            source_endpoint_arn='arn:aws:dms:us-east-1:123456789012:endpoint:source',
            target_endpoint_arn='arn:aws:dms:us-east-1:123456789012:endpoint:target',
            replication_instance_arn='arn:aws:dms:us-east-1:123456789012:rep:test-instance',
            migration_type='full-load',
            table_mappings='{"rules":[{"rule-type":"selection","rule-id":"1","rule-name":"1","object-locator":{"schema-name":"public","table-name":"%"},"rule-action":"include"}]}',
            replication_task_settings=None,
            cdc_start_time=None,
            cdc_start_position=None,
            tags=None,
        )

        assert isinstance(result, ReplicationTaskResponse)
        assert result.replication_task_identifier == 'new-task'
        assert result.migration_type == 'full-load'
        assert result.status == 'creating'

        call_args = mock_dms_client.create_replication_task.call_args[1]
        assert call_args['ReplicationTaskIdentifier'] == 'new-task'
        assert (
            call_args['SourceEndpointArn'] == 'arn:aws:dms:us-east-1:123456789012:endpoint:source'
        )
        assert (
            call_args['TargetEndpointArn'] == 'arn:aws:dms:us-east-1:123456789012:endpoint:target'
        )


@pytest.mark.asyncio
class TestStartReplicationTask:
    """Tests for start_replication_task function."""

    async def test_start_requires_write_access(self, mock_dms_client):
        """Test that start requires write access."""
        Context.initialize(readonly=True)

        with pytest.raises(ValueError, match='Your DMS MCP server does not allow writes'):
            await start_replication_task(
                replication_task_arn='arn:aws:dms:us-east-1:123456789012:task:test-task',
                start_replication_task_type='start-replication',
            )

    async def test_start_task_success(self, mock_dms_client):
        """Test successful task start."""
        Context.initialize(readonly=False)

        result = await start_replication_task(
            replication_task_arn='arn:aws:dms:us-east-1:123456789012:task:test-task',
            start_replication_task_type='start-replication',
        )

        assert isinstance(result, ReplicationTaskResponse)
        assert result.replication_task_identifier == 'started-task'
        assert result.status == 'starting'

        call_args = mock_dms_client.start_replication_task.call_args[1]
        assert (
            call_args['ReplicationTaskArn'] == 'arn:aws:dms:us-east-1:123456789012:task:test-task'
        )
        assert call_args['StartReplicationTaskType'] == 'start-replication'


@pytest.mark.asyncio
class TestStopReplicationTask:
    """Tests for stop_replication_task function."""

    async def test_stop_requires_write_access(self, mock_dms_client):
        """Test that stop requires write access."""
        Context.initialize(readonly=True)

        with pytest.raises(ValueError, match='Your DMS MCP server does not allow writes'):
            await stop_replication_task(
                replication_task_arn='arn:aws:dms:us-east-1:123456789012:task:test-task'
            )

    async def test_stop_task_success(self, mock_dms_client):
        """Test successful task stop."""
        Context.initialize(readonly=False)

        result = await stop_replication_task(
            replication_task_arn='arn:aws:dms:us-east-1:123456789012:task:test-task'
        )

        assert isinstance(result, ReplicationTaskResponse)
        assert result.replication_task_identifier == 'stopped-task'
        assert result.status == 'stopping'

        call_args = mock_dms_client.stop_replication_task.call_args[1]
        assert (
            call_args['ReplicationTaskArn'] == 'arn:aws:dms:us-east-1:123456789012:task:test-task'
        )

    async def test_create_task_invalid_table_mappings_json(self, mock_dms_client):
        """Test create_replication_task with invalid table_mappings JSON."""
        Context.initialize(readonly=False)

        with pytest.raises(ValueError, match='table_mappings must be valid JSON'):
            await create_replication_task(
                replication_task_identifier='test-task',
                source_endpoint_arn='arn:aws:dms:us-east-1:123456789012:endpoint:source',
                target_endpoint_arn='arn:aws:dms:us-east-1:123456789012:endpoint:target',
                replication_instance_arn='arn:aws:dms:us-east-1:123456789012:rep:test-instance',
                migration_type='full-load',
                table_mappings='invalid_json',  # Invalid JSON
                replication_task_settings=None,
                cdc_start_time=None,
                cdc_start_position=None,
                tags=None,
            )

    async def test_create_task_invalid_settings_json(self, mock_dms_client):
        """Test create_replication_task with invalid replication_task_settings JSON."""
        Context.initialize(readonly=False)

        with pytest.raises(ValueError, match='replication_task_settings must be valid JSON'):
            await create_replication_task(
                replication_task_identifier='test-task',
                source_endpoint_arn='arn:aws:dms:us-east-1:123456789012:endpoint:source',
                target_endpoint_arn='arn:aws:dms:us-east-1:123456789012:endpoint:target',
                replication_instance_arn='arn:aws:dms:us-east-1:123456789012:rep:test-instance',
                migration_type='full-load',
                table_mappings='{"rules": []}',
                replication_task_settings='invalid_json',  # Invalid JSON
                cdc_start_time=None,
                cdc_start_position=None,
                tags=None,
            )

    async def test_create_task_invalid_tags_json(self, mock_dms_client):
        """Test create_replication_task with invalid tags JSON."""
        Context.initialize(readonly=False)

        with pytest.raises(ValueError, match='tags must be valid JSON format'):
            await create_replication_task(
                replication_task_identifier='test-task',
                source_endpoint_arn='arn:aws:dms:us-east-1:123456789012:endpoint:source',
                target_endpoint_arn='arn:aws:dms:us-east-1:123456789012:endpoint:target',
                replication_instance_arn='arn:aws:dms:us-east-1:123456789012:rep:test-instance',
                migration_type='full-load',
                table_mappings='{"rules": []}',
                replication_task_settings=None,
                cdc_start_time=None,
                cdc_start_position=None,
                tags='invalid_json',  # Invalid JSON
            )

    async def test_start_task_aws_error(self, mock_dms_client):
        """Test start_replication_task with AWS error."""
        Context.initialize(readonly=False)

        mock_dms_client.start_replication_task.side_effect = ClientError(
            {
                'Error': {
                    'Code': 'InvalidResourceStateFault',
                    'Message': 'Task not in correct state',
                }
            },
            'StartReplicationTask',
        )

        with pytest.raises(ValueError, match='Failed to start replication task'):
            await start_replication_task(
                replication_task_arn='arn:aws:dms:us-east-1:123456789012:task:test-task',
                start_replication_task_type='start-replication',
            )

    async def test_stop_task_aws_error(self, mock_dms_client):
        """Test stop_replication_task with AWS error."""
        Context.initialize(readonly=False)

        mock_dms_client.stop_replication_task.side_effect = ClientError(
            {'Error': {'Code': 'ResourceNotFoundFault', 'Message': 'Task not found'}},
            'StopReplicationTask',
        )

        with pytest.raises(ValueError, match='Failed to stop replication task'):
            await stop_replication_task(
                replication_task_arn='arn:aws:dms:us-east-1:123456789012:task:nonexistent-task'
            )

    async def test_create_task_with_all_optional_params(self, mock_dms_client):
        """Test create_replication_task with all optional parameters."""
        Context.initialize(readonly=False)

        mock_dms_client.create_replication_task.return_value = {
            'ReplicationTask': {
                'ReplicationTaskIdentifier': 'test-task',
                'ReplicationTaskArn': 'arn:aws:dms:us-east-1:123456789012:task:test-task',
                'SourceEndpointArn': 'arn:aws:dms:us-east-1:123456789012:endpoint:source',
                'TargetEndpointArn': 'arn:aws:dms:us-east-1:123456789012:endpoint:target',
                'ReplicationInstanceArn': 'arn:aws:dms:us-east-1:123456789012:rep:test-instance',
                'MigrationType': 'full-load-and-cdc',
                'Status': 'creating',
            }
        }

        result = await create_replication_task(
            replication_task_identifier='test-task',
            source_endpoint_arn='arn:aws:dms:us-east-1:123456789012:endpoint:source',
            target_endpoint_arn='arn:aws:dms:us-east-1:123456789012:endpoint:target',
            replication_instance_arn='arn:aws:dms:us-east-1:123456789012:rep:test-instance',
            migration_type='full-load-and-cdc',
            table_mappings='{"rules": [{"rule-type": "selection", "rule-id": "1", "rule-name": "1", "object-locator": {"schema-name": "%", "table-name": "%"}, "rule-action": "include"}]}',
            replication_task_settings='{"TargetMetadata": {"TargetSchema": ""}}',
            cdc_start_time='2023-01-01T00:00:00Z',
            cdc_start_position='00000001:00000000:00000000',
            tags='[{"Key": "Environment", "Value": "test"}]',
        )

        assert isinstance(result, ReplicationTaskResponse)

        # Verify all optional parameters were passed
        call_args = mock_dms_client.create_replication_task.call_args[1]
        assert call_args['ReplicationTaskSettings'] == '{"TargetMetadata": {"TargetSchema": ""}}'
        assert call_args['CdcStartTime'] == '2023-01-01T00:00:00Z'
        assert call_args['CdcStartPosition'] == '00000001:00000000:00000000'
        assert 'Tags' in call_args
