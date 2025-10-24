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

"""Table Operations.

Handles table-level statistics and reload operations.
"""

from ..exceptions import DMSInvalidParameterException
from .dms_client import DMSClient
from .response_formatter import ResponseFormatter
from loguru import logger
from typing import Any, Dict, List, Optional


class TableOperations:
    """Manager for table-level operations."""

    def __init__(self, client: DMSClient):
        """Initialize table operations manager.

        Args:
            client: DMS client wrapper
        """
        self.client = client
        logger.debug('Initialized TableOperations')

    def get_table_statistics(
        self,
        task_arn: str,
        filters: Optional[List[Dict[str, Any]]] = None,
        max_results: int = 100,
        marker: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get table-level replication statistics.

        Args:
            task_arn: Task ARN
            filters: Optional filters (by schema, table, status)
            max_results: Maximum results per page
            marker: Pagination token

        Returns:
            Dictionary with table statistics and summary
        """
        logger.info('Getting table statistics', task_arn=task_arn)

        # Build API parameters
        params: Dict[str, Any] = {'ReplicationTaskArn': task_arn, 'MaxRecords': max_results}

        if filters:
            params['Filters'] = filters

        if marker:
            params['Marker'] = marker

        # Call API
        response = self.client.call_api('describe_table_statistics', **params)

        # Format table statistics
        stats = response.get('TableStatistics', [])
        formatted_stats = self.format_statistics(stats)

        # Calculate summary statistics
        summary: Dict[str, Any] = {
            'total_tables': len(formatted_stats),
            'total_inserts': sum(s.get('inserts', 0) for s in formatted_stats),
            'total_deletes': sum(s.get('deletes', 0) for s in formatted_stats),
            'total_updates': sum(s.get('updates', 0) for s in formatted_stats),
            'total_ddls': sum(s.get('ddls', 0) for s in formatted_stats),
            'total_full_load_rows': sum(s.get('full_load_rows', 0) for s in formatted_stats),
            'total_error_rows': sum(s.get('full_load_error_rows', 0) for s in formatted_stats),
        }

        # Calculate average completion
        completions = [
            s.get('completion_percent', 0)
            for s in formatted_stats
            if s.get('completion_percent') is not None
        ]
        if completions:
            summary['average_completion_percent'] = round(sum(completions) / len(completions), 2)
        else:
            summary['average_completion_percent'] = 0.0

        result = {
            'success': True,
            'data': {'tables': formatted_stats, 'summary': summary, 'count': len(formatted_stats)},
            'error': None,
        }

        # Add pagination info
        if response.get('Marker'):
            result['data']['next_marker'] = response['Marker']

        logger.info(f'Retrieved statistics for {len(formatted_stats)} tables')
        return result

    def reload_tables(
        self, task_arn: str, tables: List[Dict[str, Any]], reload_option: str = 'data-reload'
    ) -> Dict[str, Any]:
        """Reload specific tables during replication.

        Args:
            task_arn: Task ARN
            tables: List of tables [{schema_name, table_name}, ...]
            reload_option: Reload option (data-reload or validate-only)

        Returns:
            Reload operation status
        """
        logger.info('Reloading tables', task_arn=task_arn, table_count=len(tables))

        # Validate tables list not empty
        if not tables or len(tables) == 0:
            raise DMSInvalidParameterException(
                message='Tables list cannot be empty', details={'table_count': 0}
            )

        # Validate each table has required fields
        for idx, table in enumerate(tables):
            if 'SchemaName' not in table:
                raise DMSInvalidParameterException(
                    message=f"Table {idx} missing 'SchemaName'", details={'table_index': idx}
                )
            if 'TableName' not in table:
                raise DMSInvalidParameterException(
                    message=f"Table {idx} missing 'TableName'", details={'table_index': idx}
                )

        # Validate reload option
        valid_options = ['data-reload', 'validate-only']
        if reload_option not in valid_options:
            raise DMSInvalidParameterException(
                message=f'Invalid reload option: {reload_option}',
                details={'valid_options': valid_options},
            )

        # Build API parameters
        # Convert tables to TablesToReload format
        tables_to_reload = [
            {'SchemaName': table['SchemaName'], 'TableName': table['TableName']}
            for table in tables
        ]

        # Call API
        self.client.call_api(
            'reload_tables',
            ReplicationTaskArn=task_arn,
            TablesToReload=tables_to_reload,
            ReloadOption=reload_option,
        )

        result = {
            'success': True,
            'data': {
                'task_arn': task_arn,
                'tables_reloaded': len(tables),
                'reload_option': reload_option,
                'message': f'Table reload initiated for {len(tables)} tables',
            },
            'error': None,
        }

        logger.info(f'Initiated reload for {len(tables)} tables')
        return result

    def format_statistics(self, stats: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format table statistics for response.

        Args:
            stats: Raw statistics from API

        Returns:
            Formatted statistics list
        """
        formatted_list = []

        for stat in stats:
            formatted_stat = ResponseFormatter.format_table_stats(stat)

            # Add human-readable status descriptions
            table_state = formatted_stat.get('table_state', '')
            state_descriptions = {
                'Table completed': 'Full load and ongoing replication complete',
                'Table loading': 'Full load in progress',
                'Table does not exist': 'Table not found in source',
                'Table error': 'Error occurred during replication',
                'Before load': 'Waiting to start full load',
                'Full load': 'Full load in progress',
                'Table cancelled': 'Replication cancelled for this table',
            }

            if table_state in state_descriptions:
                formatted_stat['state_description'] = state_descriptions[table_state]

            formatted_list.append(formatted_stat)

        return formatted_list

    def get_replication_table_statistics(
        self,
        task_arn: Optional[str] = None,
        config_arn: Optional[str] = None,
        filters: Optional[List[Dict[str, Any]]] = None,
        max_results: int = 100,
        marker: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get table statistics for a replication task or configuration.

        Args:
            task_arn: Task ARN (for traditional DMS)
            config_arn: Config ARN (for DMS Serverless)
            filters: Optional filters
            max_results: Maximum results per page
            marker: Pagination token

        Returns:
            Dictionary with table statistics
        """
        if not task_arn and not config_arn:
            raise DMSInvalidParameterException(
                message='Must provide either task_arn or config_arn',
                details={'task_arn': task_arn, 'config_arn': config_arn},
            )

        logger.info(
            'Getting replication table statistics', task_arn=task_arn, config_arn=config_arn
        )

        # Build API parameters
        params: Dict[str, Any] = {'MaxRecords': max_results}

        if task_arn:
            params['ReplicationTaskArn'] = task_arn
        if config_arn:
            params['ReplicationConfigArn'] = config_arn
        if filters:
            params['Filters'] = filters
        if marker:
            params['Marker'] = marker

        # Call API
        response = self.client.call_api('describe_replication_table_statistics', **params)

        # Format table statistics
        stats = response.get('ReplicationTableStatistics', [])
        formatted_stats = self.format_statistics(stats)

        result = {
            'success': True,
            'data': {'tables': formatted_stats, 'count': len(formatted_stats)},
            'error': None,
        }

        # Add pagination info
        if response.get('Marker'):
            result['data']['next_marker'] = response['Marker']

        logger.info(f'Retrieved statistics for {len(formatted_stats)} tables')
        return result

    def reload_serverless_tables(
        self, config_arn: str, tables: List[Dict[str, Any]], reload_option: str = 'data-reload'
    ) -> Dict[str, Any]:
        """Reload specific tables in a serverless replication.

        Args:
            config_arn: Replication config ARN
            tables: List of tables [{SchemaName, TableName}, ...]
            reload_option: Reload option (data-reload or validate-only)

        Returns:
            Reload operation status
        """
        logger.info('Reloading serverless tables', config_arn=config_arn, table_count=len(tables))

        # Validate tables list not empty
        if not tables or len(tables) == 0:
            raise DMSInvalidParameterException(
                message='Tables list cannot be empty', details={'table_count': 0}
            )

        # Validate each table has required fields
        for idx, table in enumerate(tables):
            if 'SchemaName' not in table:
                raise DMSInvalidParameterException(
                    message=f"Table {idx} missing 'SchemaName'", details={'table_index': idx}
                )
            if 'TableName' not in table:
                raise DMSInvalidParameterException(
                    message=f"Table {idx} missing 'TableName'", details={'table_index': idx}
                )

        # Validate reload option
        valid_options = ['data-reload', 'validate-only']
        if reload_option not in valid_options:
            raise DMSInvalidParameterException(
                message=f'Invalid reload option: {reload_option}',
                details={'valid_options': valid_options},
            )

        # Call API
        self.client.call_api(
            'reload_tables',
            ReplicationConfigArn=config_arn,
            TablesToReload=tables,
            ReloadOption=reload_option,
        )

        result = {
            'success': True,
            'data': {
                'config_arn': config_arn,
                'tables_reloaded': len(tables),
                'reload_option': reload_option,
                'message': f'Table reload initiated for {len(tables)} tables',
            },
            'error': None,
        }

        logger.info(f'Initiated reload for {len(tables)} serverless tables')
        return result


# TODO: Add table validation status monitoring
# TODO: Add CDC position tracking per table
# TODO: Add table error analysis
