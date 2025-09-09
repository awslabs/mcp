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

"""Replication task operations for DMS MCP Server."""

import json
from awslabs.dms_mcp_server.aws_client import (
    get_dms_client,
    handle_aws_error,
)
from awslabs.dms_mcp_server.common.server import mcp
from awslabs.dms_mcp_server.consts import (
    DEFAULT_MAX_RECORDS,
    RELOAD_OPTIONS,
)
from awslabs.dms_mcp_server.context import Context
from awslabs.dms_mcp_server.models import (
    ReplicationTaskListResponse,
    ReplicationTaskResponse,
)
from loguru import logger
from pydantic import Field
from typing import Any, Dict, List, Literal, Optional


@mcp.tool()
async def describe_replication_tasks(
    replication_task_identifier: Optional[str] = Field(
        default=None, description='Filter by specific replication task identifier'
    ),
    replication_instance_arn: Optional[str] = Field(
        default=None, description='Filter by replication instance ARN'
    ),
    migration_type: Optional[Literal['full-load', 'cdc', 'full-load-and-cdc']] = Field(
        default=None, description='Filter by migration type'
    ),
    max_records: int = Field(
        default=DEFAULT_MAX_RECORDS, description='Maximum number of records to return'
    ),
    marker: Optional[str] = Field(default=None, description='Pagination token'),
    with_statistics: bool = Field(default=False, description='Include task statistics'),
) -> ReplicationTaskListResponse:
    """Describe one or more DMS replication tasks."""
    try:
        dms_client = get_dms_client()

        describe_params = {'MaxRecords': max_records, 'WithoutSettings': not with_statistics}

        filters = []
        if replication_task_identifier:
            filters.append(
                {'Name': 'replication-task-id', 'Values': [replication_task_identifier]}
            )
        if replication_instance_arn:
            filters.append(
                {'Name': 'replication-instance-arn', 'Values': [replication_instance_arn]}
            )
        if migration_type:
            filters.append({'Name': 'migration-type', 'Values': [migration_type]})
        if filters:
            describe_params['Filters'] = filters
        if marker:
            describe_params['Marker'] = marker

        response = dms_client.describe_replication_tasks(**describe_params)

        tasks = []
        for task in response['ReplicationTasks']:
            task_response = ReplicationTaskResponse(
                replication_task_identifier=task['ReplicationTaskIdentifier'],
                replication_task_arn=task['ReplicationTaskArn'],
                source_endpoint_arn=task['SourceEndpointArn'],
                target_endpoint_arn=task['TargetEndpointArn'],
                replication_instance_arn=task['ReplicationInstanceArn'],
                migration_type=task['MigrationType'],
                table_mappings=task.get('TableMappings', ''),
                replication_task_settings=task.get('ReplicationTaskSettings'),
                status=task['Status'],
                replication_task_creation_date=task.get('ReplicationTaskCreationDate'),
                replication_task_start_date=task.get('ReplicationTaskStartDate'),
                cdc_start_position=task.get('CdcStartPosition'),
                recovery_checkpoint=task.get('RecoveryCheckpoint'),
            )
            tasks.append(task_response)

        return ReplicationTaskListResponse(replication_tasks=tasks, marker=response.get('Marker'))

    except Exception as e:
        error_msg = handle_aws_error(e)
        logger.error(f'Failed to describe replication tasks: {error_msg}')
        raise ValueError(f'Failed to describe replication tasks: {error_msg}')


@mcp.tool()
async def describe_table_statistics(
    replication_task_arn: str = Field(description='The ARN of the replication task'),
    max_records: int = Field(
        default=DEFAULT_MAX_RECORDS, description='Maximum number of records to return'
    ),
    marker: Optional[str] = Field(default=None, description='Pagination token'),
    filters: Optional[List[Dict[str, Any]]] = Field(
        default=None, description='Filters to apply to table statistics'
    ),
) -> Dict[str, Any]:
    """Get table statistics for a DMS replication task.

    This provides detailed statistics about the replication progress for each table
    including row counts, errors, and validation status.
    """
    try:
        dms_client = get_dms_client()

        describe_params = {'ReplicationTaskArn': replication_task_arn, 'MaxRecords': max_records}

        if marker:
            describe_params['Marker'] = marker
        if filters:
            describe_params['Filters'] = filters

        response = dms_client.describe_table_statistics(**describe_params)

        # Process and format the statistics for better readability
        table_stats = []
        for stat in response.get('TableStatistics', []):
            table_stat = {
                'schema_name': stat.get('SchemaName'),
                'table_name': stat.get('TableName'),
                'table_state': stat.get('TableState'),
                'insert_count': stat.get('Inserts', 0),
                'delete_count': stat.get('Deletes', 0),
                'update_count': stat.get('Updates', 0),
                'ddl_count': stat.get('Ddls', 0),
                'full_load_rows': stat.get('FullLoadRows', 0),
                'full_load_condtnl_chk_failed_rows': stat.get('FullLoadCondtnlChkFailedRows', 0),
                'full_load_error_rows': stat.get('FullLoadErrorRows', 0),
                'full_load_start_time': stat.get('FullLoadStartTime'),
                'full_load_end_time': stat.get('FullLoadEndTime'),
                'last_update_time': stat.get('LastUpdateTime'),
                'validation_state': stat.get('ValidationState'),
                'validation_pending_records': stat.get('ValidationPendingRecords', 0),
                'validation_failed_records': stat.get('ValidationFailedRecords', 0),
                'validation_suspended_records': stat.get('ValidationSuspendedRecords', 0),
            }
            table_stats.append(table_stat)

        return {
            'replication_task_arn': replication_task_arn,
            'table_statistics': table_stats,
            'marker': response.get('Marker'),
            'total_tables': len(table_stats),
        }

    except Exception as e:
        error_msg = handle_aws_error(e)
        logger.error(f'Failed to describe table statistics: {error_msg}')
        raise ValueError(f'Failed to describe table statistics: {error_msg}')


@mcp.tool()
async def reload_replication_task_tables(
    replication_task_arn: str = Field(description='The ARN of the replication task'),
    tables_to_reload: List[Dict[str, str]] = Field(
        description="List of tables to reload. Each table should have 'schema-name' and 'table-name' keys"
    ),
    reload_option: Optional[Literal['data-reload', 'validate-only']] = Field(
        default=RELOAD_OPTIONS['DATA_RELOAD'],
        description='The reload option to apply to the selected tables',
    ),
) -> str:
    """Reload specific tables in a DMS replication task.

    This operation selectively reloads tables during an ongoing replication task.
    Use this when you need to reload specific tables that may have encountered issues
    or when you want to refresh data for specific tables.

    Args:
        replication_task_arn: The ARN of the replication task
        tables_to_reload: List of tables to reload, each with schema-name and table-name
        reload_option: Either 'data-reload' (default) to reload data, or 'validate-only' to validate without reloading

    Example:
        tables_to_reload = [
            {"schema-name": "public", "table-name": "users"},
            {"schema-name": "public", "table-name": "orders"}
        ]
    """
    # Check if write operations are allowed
    Context.require_write_access()

    try:
        dms_client = get_dms_client()

        # Validate and transform table structure
        aws_tables = []
        for table in tables_to_reload:
            if 'schema-name' not in table or 'table-name' not in table:
                raise ValueError("Each table must have 'schema-name' and 'table-name' keys")

            # Transform to AWS API format (PascalCase)
            aws_table = {'SchemaName': table['schema-name'], 'TableName': table['table-name']}
            aws_tables.append(aws_table)

        reload_params = {'ReplicationTaskArn': replication_task_arn, 'TablesToReload': aws_tables}

        if reload_option:
            reload_params['ReloadOption'] = reload_option

        dms_client.reload_tables(**reload_params)

        # Extract task identifier from ARN for better user feedback
        task_id = (
            replication_task_arn.split(':')[-1]
            if ':' in replication_task_arn
            else replication_task_arn
        )
        table_names = [
            f'{table["schema-name"]}.{table["table-name"]}' for table in tables_to_reload
        ]

        return f"Reload initiated for tables {', '.join(table_names)} in replication task '{task_id}'. Reload option: {reload_option}"

    except Exception as e:
        error_msg = handle_aws_error(e)
        logger.error(f'Failed to reload tables: {error_msg}')
        raise ValueError(f'Failed to reload tables: {error_msg}')


@mcp.tool()
async def create_replication_task(
    replication_task_identifier: str = Field(
        description='A unique identifier for the replication task'
    ),
    source_endpoint_arn: str = Field(description='The ARN of the source endpoint'),
    target_endpoint_arn: str = Field(description='The ARN of the target endpoint'),
    replication_instance_arn: str = Field(description='The ARN of the replication instance'),
    migration_type: str = Field(
        description='The type of migration (full-load, cdc, or full-load-and-cdc)'
    ),
    table_mappings: str = Field(description='The table mappings in JSON format'),
    replication_task_settings: Optional[str] = Field(
        default=None, description='The replication task settings in JSON format'
    ),
    cdc_start_time: Optional[str] = Field(
        default=None, description='CDC start time (ISO 8601 format)'
    ),
    cdc_start_position: Optional[str] = Field(default=None, description='CDC start position'),
    tags: Optional[str] = Field(default=None, description='Resource tags in JSON format'),
) -> ReplicationTaskResponse:
    """Create a new DMS replication task.

    This creates a new replication task that migrates data from a source to a target endpoint
    using the specified replication instance.

    Args:
        replication_task_identifier: Unique name for the replication task
        source_endpoint_arn: ARN of the source database endpoint
        target_endpoint_arn: ARN of the target database endpoint
        replication_instance_arn: ARN of the replication instance to use
        migration_type: Type of migration ('full-load', 'cdc', or 'full-load-and-cdc')
        table_mappings: JSON string defining which tables/schemas to migrate
        replication_task_settings: Optional JSON string with task configuration
        cdc_start_time: Optional start time for CDC (Change Data Capture)
        cdc_start_position: Optional start position for CDC
        tags: Optional resource tags in JSON format

    Example:
        table_mappings = '{"rules": [{"rule-type": "selection", "rule-id": "1",
                         "rule-name": "1", "object-locator": {"schema-name": "%",
                         "table-name": "%"}, "rule-action": "include"}]}'
    """
    # Check if write operations are allowed
    Context.require_write_access()

    try:
        dms_client = get_dms_client()

        # Validate table_mappings JSON
        try:
            json.loads(table_mappings)
        except json.JSONDecodeError:
            raise ValueError('table_mappings must be valid JSON')

        create_params = {
            'ReplicationTaskIdentifier': replication_task_identifier,
            'SourceEndpointArn': source_endpoint_arn,
            'TargetEndpointArn': target_endpoint_arn,
            'ReplicationInstanceArn': replication_instance_arn,
            'MigrationType': migration_type,
            'TableMappings': table_mappings,
        }

        # Add optional parameters
        if replication_task_settings:
            try:
                json.loads(replication_task_settings)
                create_params['ReplicationTaskSettings'] = replication_task_settings
            except json.JSONDecodeError:
                raise ValueError('replication_task_settings must be valid JSON')
        if cdc_start_time:
            create_params['CdcStartTime'] = cdc_start_time
        if cdc_start_position:
            create_params['CdcStartPosition'] = cdc_start_position
        if tags:
            try:
                tags_list = json.loads(tags)
                create_params['Tags'] = tags_list
            except json.JSONDecodeError:
                raise ValueError('tags must be valid JSON format')

        response = dms_client.create_replication_task(**create_params)
        task = response['ReplicationTask']

        return ReplicationTaskResponse(
            replication_task_identifier=task['ReplicationTaskIdentifier'],
            replication_task_arn=task['ReplicationTaskArn'],
            source_endpoint_arn=task['SourceEndpointArn'],
            target_endpoint_arn=task['TargetEndpointArn'],
            replication_instance_arn=task['ReplicationInstanceArn'],
            migration_type=task['MigrationType'],
            table_mappings=task.get('TableMappings', ''),
            replication_task_settings=task.get('ReplicationTaskSettings'),
            status=task['Status'],
            replication_task_creation_date=task.get('ReplicationTaskCreationDate'),
            replication_task_start_date=task.get('ReplicationTaskStartDate'),
            cdc_start_position=task.get('CdcStartPosition'),
            recovery_checkpoint=task.get('RecoveryCheckpoint'),
        )

    except Exception as e:
        error_msg = handle_aws_error(e)
        logger.error(f'Failed to create replication task: {error_msg}')
        raise ValueError(f'Failed to create replication task: {error_msg}')


@mcp.tool()
async def start_replication_task(
    replication_task_arn: str = Field(description='The ARN of the replication task to start'),
    start_replication_task_type: str = Field(
        description='The type of start operation (start-replication, resume-processing, reload-target)'
    ),
) -> ReplicationTaskResponse:
    """Start a DMS replication task.

    This starts a replication task that has been created but not yet started,
    or resumes/reloads an existing task.

    Args:
        replication_task_arn: ARN of the replication task to start
        start_replication_task_type: Type of start operation:
            - 'start-replication': Start a new replication task
            - 'resume-processing': Resume a paused task
            - 'reload-target': Reload the target database and restart replication

    Example:
        Start a new replication task:
        start_replication_task_type = "start-replication"

        Resume a paused task:
        start_replication_task_type = "resume-processing"
    """
    # Check if write operations are allowed
    Context.require_write_access()

    try:
        dms_client = get_dms_client()

        # Validate start_replication_task_type
        valid_types = ['start-replication', 'resume-processing', 'reload-target']
        if start_replication_task_type not in valid_types:
            raise ValueError(
                f'start_replication_task_type must be one of: {", ".join(valid_types)}'
            )

        response = dms_client.start_replication_task(
            ReplicationTaskArn=replication_task_arn,
            StartReplicationTaskType=start_replication_task_type,
        )
        task = response['ReplicationTask']

        return ReplicationTaskResponse(
            replication_task_identifier=task['ReplicationTaskIdentifier'],
            replication_task_arn=task['ReplicationTaskArn'],
            source_endpoint_arn=task['SourceEndpointArn'],
            target_endpoint_arn=task['TargetEndpointArn'],
            replication_instance_arn=task['ReplicationInstanceArn'],
            migration_type=task['MigrationType'],
            table_mappings=task.get('TableMappings', ''),
            replication_task_settings=task.get('ReplicationTaskSettings'),
            status=task['Status'],
            replication_task_creation_date=task.get('ReplicationTaskCreationDate'),
            replication_task_start_date=task.get('ReplicationTaskStartDate'),
            cdc_start_position=task.get('CdcStartPosition'),
            recovery_checkpoint=task.get('RecoveryCheckpoint'),
        )

    except Exception as e:
        error_msg = handle_aws_error(e)
        logger.error(f'Failed to start replication task: {error_msg}')
        raise ValueError(f'Failed to start replication task: {error_msg}')


@mcp.tool()
async def stop_replication_task(
    replication_task_arn: str = Field(description='The ARN of the replication task to stop'),
) -> ReplicationTaskResponse:
    """Stop a running DMS replication task.

    This stops a replication task that is currently running. The task can be
    restarted later using start_replication_task with 'resume-processing'.

    Args:
        replication_task_arn: ARN of the replication task to stop

    Example:
        Stop a running replication task to pause migration:
        stop_replication_task(replication_task_arn="arn:aws:dms:...")
    """
    # Check if write operations are allowed
    Context.require_write_access()

    try:
        dms_client = get_dms_client()

        response = dms_client.stop_replication_task(ReplicationTaskArn=replication_task_arn)
        task = response['ReplicationTask']

        return ReplicationTaskResponse(
            replication_task_identifier=task['ReplicationTaskIdentifier'],
            replication_task_arn=task['ReplicationTaskArn'],
            source_endpoint_arn=task['SourceEndpointArn'],
            target_endpoint_arn=task['TargetEndpointArn'],
            replication_instance_arn=task['ReplicationInstanceArn'],
            migration_type=task['MigrationType'],
            table_mappings=task.get('TableMappings', ''),
            replication_task_settings=task.get('ReplicationTaskSettings'),
            status=task['Status'],
            replication_task_creation_date=task.get('ReplicationTaskCreationDate'),
            replication_task_start_date=task.get('ReplicationTaskStartDate'),
            cdc_start_position=task.get('CdcStartPosition'),
            recovery_checkpoint=task.get('RecoveryCheckpoint'),
        )

    except Exception as e:
        error_msg = handle_aws_error(e)
        logger.error(f'Failed to stop replication task: {error_msg}')
        raise ValueError(f'Failed to stop replication task: {error_msg}')
