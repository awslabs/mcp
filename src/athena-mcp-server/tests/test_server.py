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

"""Test the Athena MCP server implementation."""

import pytest
from awslabs.athena_mcp_server.models import (
    ErrorResponse,
    ListDatabasesResponse,
    ListDataCatalogsResponse,
    ListTablesResponse,
    ListWorkgroupsResponse,
    QueryResults,
    TableInfo,
    WorkgroupDetailsResponse,
)
from awslabs.athena_mcp_server.server import (
    _get_athena_client,
    _handle_athena_error,
    execute_query,
    get_query_results,
    get_table_metadata,
    get_work_group,
    list_data_catalogs,
    list_databases,
    list_tables,
    list_work_groups,
)
from botocore.exceptions import ClientError
from datetime import datetime


@pytest.fixture
def mock_athena_client(mocker):
    """Create a mock Athena client."""
    mock_client = mocker.MagicMock()
    mocker.patch('awslabs.athena_mcp_server.server.boto3.client', return_value=mock_client)

    yield mock_client

    # Clear the LRU cache after mocked tests finish to ensure live integration
    # tests and subsequent tests get fresh, real boto3 clients instead of
    # cached mock clients that would cause validation errors
    _get_athena_client.cache_clear()


@pytest.fixture
def sample_query_execution():
    """Sample query execution response."""
    return {
        'QueryExecutionId': 'test-execution-id-123',
        'Query': 'SELECT * FROM test_table LIMIT 10',
        'Status': {
            'State': 'SUCCEEDED',
            'StateChangeReason': 'Query completed successfully',
            'SubmissionDateTime': datetime(2024, 1, 1, 12, 0, 0),
            'CompletionDateTime': datetime(2024, 1, 1, 12, 0, 30),
        },
        'Statistics': {
            'DataScannedInBytes': 1024,
            'EngineExecutionTimeInMillis': 5000,
        },
        'WorkGroup': 'primary',
        'ResultConfiguration': {
            'OutputLocation': 's3://test-bucket/results/',
        },
    }


@pytest.fixture
def sample_query_results():
    """Sample query results response."""
    return {
        'ResultSet': {
            'ResultSetMetadata': {
                'ColumnInfo': [
                    {'Name': 'id', 'Type': 'bigint', 'Nullable': 'NULLABLE'},
                    {'Name': 'name', 'Type': 'varchar', 'Nullable': 'NULLABLE'},
                    {
                        'Name': 'score',
                        'Type': 'double',
                        'Precision': 10,
                        'Scale': 2,
                        'Nullable': 'NULLABLE',
                    },
                ]
            },
            'Rows': [
                {
                    'Data': [
                        {'VarCharValue': 'id'},
                        {'VarCharValue': 'name'},
                        {'VarCharValue': 'score'},
                    ]
                },
                {
                    'Data': [
                        {'VarCharValue': '1'},
                        {'VarCharValue': 'Alice'},
                        {'VarCharValue': '95.5'},
                    ]
                },
                {
                    'Data': [
                        {'VarCharValue': '2'},
                        {},  # NULL value
                        {'VarCharValue': '87.3'},
                    ]
                },
            ],
        },
        'NextToken': 'next-page-token',
    }


class TestExecuteQuery:
    """Test query execution functionality."""

    @pytest.mark.parametrize(
        'optional_params',
        [
            {},
            {
                'workgroup': 'test-workgroup',
                'database': 'test_db',
                'output_location': 's3://some-bucket/results/',
            },
        ],
    )
    @pytest.mark.asyncio
    async def test_execute_query_success(
        self, mock_athena_client, sample_query_execution, sample_query_results, optional_params
    ):
        """Test successful query execution with various parameter combinations."""
        mock_athena_client.start_query_execution.return_value = {
            'QueryExecutionId': 'test-execution-id-123'
        }
        mock_athena_client.get_query_execution.return_value = {
            'QueryExecution': sample_query_execution
        }
        mock_athena_client.get_query_results.return_value = sample_query_results

        result = await execute_query('SELECT * FROM test_table LIMIT 10', **optional_params)

        assert isinstance(result, QueryResults)
        assert len(result.column_info) == 3
        assert result.column_info[0].name == 'id'
        assert result.column_info[0].type == 'bigint'
        assert len(result.rows) == 2
        assert result.rows[0] == {'id': '1', 'name': 'Alice', 'score': '95.5'}
        assert result.rows[1] == {'id': '2', 'name': None, 'score': '87.3'}
        assert result.total_rows == 2
        assert result.next_token == 'next-page-token'
        assert result.query_execution_id == 'test-execution-id-123'
        assert result.data_scanned_in_bytes == 1024
        assert result.execution_time_in_millis == 5000

    @pytest.mark.asyncio
    async def test_execute_query_client_error(self, mock_athena_client):
        """Test query execution with client error."""
        mock_athena_client.start_query_execution.side_effect = ClientError(
            {'Error': {'Code': 'InvalidRequestException', 'Message': 'Invalid SQL syntax'}},
            'StartQueryExecution',
        )
        with pytest.raises(RuntimeError, match='InvalidRequestException.*Invalid SQL syntax'):
            await execute_query('SELECT * FROM invalid_table')

    @pytest.mark.asyncio
    async def test_execute_query_failed_query(self, mock_athena_client):
        """Test query execution with failed query."""
        failed_execution = {
            'QueryExecutionId': 'test-execution-id-123',
            'Query': 'SELECT * FROM nonexistent_table',
            'Status': {
                'State': 'FAILED',
                'StateChangeReason': 'Table not found',
            },
        }
        mock_athena_client.start_query_execution.return_value = {
            'QueryExecutionId': 'test-execution-id-123'
        }
        mock_athena_client.get_query_execution.return_value = {'QueryExecution': failed_execution}
        with pytest.raises(RuntimeError, match='Query failed: Table not found'):
            await execute_query('SELECT * FROM nonexistent_table')

    @pytest.mark.asyncio
    async def test_execute_query_timeout(self, mock_athena_client):
        """Test query execution timeout."""
        running_execution = {
            'QueryExecutionId': 'test-execution-id-123',
            'Query': 'SELECT * FROM large_table',
            'Status': {
                'State': 'RUNNING',
            },
        }
        mock_athena_client.start_query_execution.return_value = {
            'QueryExecutionId': 'test-execution-id-123'
        }
        mock_athena_client.get_query_execution.return_value = {'QueryExecution': running_execution}
        with pytest.raises(RuntimeError, match='Query timed out after 1 seconds'):
            await execute_query('SELECT * FROM large_table', timeout_seconds=1)
        mock_athena_client.stop_query_execution.assert_called_once_with(
            QueryExecutionId='test-execution-id-123'
        )


class TestGetQueryResults:
    """Test query results retrieval."""

    @pytest.mark.parametrize(
        'next_token,num_expected_rows',
        [
            ('', 2),  # No pagination, header skipped
            ('previous-token', 3),  # With pagination, header included
        ],
    )
    @pytest.mark.asyncio
    async def test_get_query_results(
        self, mock_athena_client, sample_query_results, next_token, num_expected_rows
    ):
        """Test query results retrieval with and without pagination."""
        mock_athena_client.get_query_results.return_value = sample_query_results

        result = await get_query_results(
            query_execution_id='test-execution-id-123',
            next_token=next_token,
        )

        assert isinstance(result, QueryResults)
        assert len(result.column_info) == 3
        assert result.column_info[0].name == 'id'
        assert result.column_info[0].type == 'bigint'
        assert result.column_info[1].name == 'name'
        assert result.column_info[1].type == 'varchar'
        assert result.column_info[2].name == 'score'
        assert result.column_info[2].type == 'double'
        assert result.column_info[2].precision == 10
        assert result.column_info[2].scale == 2

        assert len(result.rows) == num_expected_rows
        if next_token:  # Don't skip the first row if this is not the first page (in practice pages after the first page don't have a header row)
            assert result.rows[0] == {'id': 'id', 'name': 'name', 'score': 'score'}
            assert result.rows[1] == {'id': '1', 'name': 'Alice', 'score': '95.5'}
            assert result.rows[2] == {'id': '2', 'name': None, 'score': '87.3'}
        else:  # First page gets first row skipped (since it's a header row)
            assert result.rows[0] == {'id': '1', 'name': 'Alice', 'score': '95.5'}
            assert result.rows[1] == {'id': '2', 'name': None, 'score': '87.3'}
        assert result.total_rows == num_expected_rows
        assert result.next_token == 'next-page-token'

        assert result.query_execution_id == 'test-execution-id-123'
        assert result.data_scanned_in_bytes is None
        assert result.execution_time_in_millis is None


class TestListDatabases:
    """Test database listing functionality."""

    @pytest.mark.asyncio
    async def test_list_databases_success(self, mock_athena_client):
        """Test successful database listing."""
        mock_athena_client.list_databases.return_value = {
            'DatabaseList': [
                {'Name': 'default', 'Description': 'Default database'},
                {
                    'Name': 'analytics',
                    'Description': 'Analytics database',
                    'Parameters': {'owner': 'team'},
                },
            ],
            'NextToken': 'next-db-token',
        }
        result = await list_databases()
        assert isinstance(result, ListDatabasesResponse)
        assert len(result.databases) == 2
        assert result.databases[0]['name'] == 'default'
        assert result.databases[0]['description'] == 'Default database'
        assert result.databases[0]['parameters'] is None
        assert result.databases[1]['name'] == 'analytics'
        assert result.databases[1]['description'] == 'Analytics database'
        assert result.databases[1]['parameters'] == {'owner': 'team'}
        assert result.next_token == 'next-db-token'


class TestListTables:
    """Test table listing functionality."""

    @pytest.mark.asyncio
    async def test_list_tables_success(self, mock_athena_client):
        """Test successful table listing."""
        mock_athena_client.list_table_metadata.return_value = {
            'TableMetadataList': [
                {
                    'Name': 'users',
                    'TableType': 'EXTERNAL_TABLE',
                    'CreateTime': datetime(2024, 1, 1),
                    'Columns': [{'Name': 'id', 'Type': 'bigint'}],
                    'PartitionKeys': [],
                },
                {
                    'Name': 'orders',
                    'TableType': 'EXTERNAL_TABLE',
                    'CreateTime': datetime(2024, 1, 2),
                    'Columns': [{'Name': 'order_id', 'Type': 'varchar'}],
                    'PartitionKeys': [{'Name': 'date', 'Type': 'string'}],
                },
            ],
        }
        result = await list_tables('test_database')
        assert isinstance(result, ListTablesResponse)
        assert len(result.tables) == 2
        assert result.tables[0].name == 'users'
        assert result.tables[0].table_type.value == 'EXTERNAL_TABLE'
        assert result.tables[0].create_time == datetime(2024, 1, 1)
        assert result.tables[0].last_access_time is None
        assert result.tables[0].columns_count == 1
        assert result.tables[0].partition_keys_count == 0
        assert result.tables[1].name == 'orders'
        assert result.tables[1].table_type.value == 'EXTERNAL_TABLE'
        assert result.tables[1].create_time == datetime(2024, 1, 2)
        assert result.tables[1].last_access_time is None
        assert result.tables[1].columns_count == 1
        assert result.tables[1].partition_keys_count == 1


class TestGetTableMetadata:
    """Test table metadata retrieval."""

    @pytest.mark.asyncio
    async def test_get_table_metadata_success(self, mock_athena_client):
        """Test successful table metadata retrieval."""
        mock_athena_client.get_table_metadata.return_value = {
            'TableMetadata': {
                'Name': 'users',
                'TableType': 'EXTERNAL_TABLE',
                'CreateTime': datetime(2024, 1, 1),
                'Columns': [
                    {'Name': 'id', 'Type': 'bigint', 'Nullable': False},
                    {'Name': 'name', 'Type': 'varchar', 'Nullable': True},
                ],
                'PartitionKeys': [{'Name': 'year', 'Type': 'string'}],
                'StorageDescriptor': {
                    'Location': 's3://data-bucket/users/',
                    'InputFormat': 'org.apache.hadoop.mapred.TextInputFormat',
                    'OutputFormat': 'org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat',
                    'SerdeInfo': {
                        'SerializationLibrary': 'org.apache.hadoop.hive.serde2.lazy.LazySimpleSerDe'
                    },
                },
                'Parameters': {'classification': 'csv'},
            }
        }
        result = await get_table_metadata('test_db', 'users')
        assert isinstance(result, TableInfo)
        assert result.name == 'users'
        assert result.table_type == 'EXTERNAL_TABLE'
        assert result.create_time == datetime(2024, 1, 1)
        assert result.last_access_time is None

        # Verify columns
        assert len(result.columns) == 2
        assert result.columns[0].name == 'id'
        assert result.columns[0].type == 'bigint'
        assert result.columns[0].nullable is False
        assert result.columns[1].name == 'name'
        assert result.columns[1].type == 'varchar'
        assert result.columns[1].nullable is True

        # Verify partition keys
        assert len(result.partition_keys) == 1
        assert result.partition_keys[0].name == 'year'
        assert result.partition_keys[0].type == 'string'

        # Verify storage and metadata
        assert result.location == 's3://data-bucket/users/'
        assert result.input_format == 'org.apache.hadoop.mapred.TextInputFormat'
        assert result.output_format == 'org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat'
        assert result.serde_info == {
            'SerializationLibrary': 'org.apache.hadoop.hive.serde2.lazy.LazySimpleSerDe'
        }
        assert result.parameters == {'classification': 'csv'}


class TestErrorHandling:
    """Test error handling functionality."""

    @pytest.mark.parametrize(
        'error,expected_code,expected_message,expected_type',
        [
            (
                ClientError(
                    {'Error': {'Code': 'ThrottlingException', 'Message': 'Rate exceeded'}},
                    'GetQueryExecution',
                ),
                'ThrottlingException',
                'Rate exceeded',
                'ClientError',
            ),
            (
                ValueError('Something went wrong'),
                'InternalError',
                'Something went wrong',
                'ValueError',
            ),
        ],
    )
    def test_handle_athena_error(self, error, expected_code, expected_message, expected_type):
        """Test error handling for different error types."""
        error_response = _handle_athena_error(error)
        assert isinstance(error_response, ErrorResponse)
        assert error_response.error_code == expected_code
        assert error_response.error_message == expected_message
        assert error_response.error_type == expected_type


class TestWorkgroupOperations:
    """Test workgroup management functionality."""

    @pytest.mark.asyncio
    async def test_list_work_groups_success(self, mock_athena_client):
        """Test successful workgroup listing."""
        mock_athena_client.list_work_groups.return_value = {
            'WorkGroups': [
                {
                    'Name': 'primary',
                    'State': 'ENABLED',
                    'Description': 'Default workgroup',
                    'CreationTime': datetime(2024, 1, 1),
                },
                {
                    'Name': 'analytics-team',
                    'State': 'ENABLED',
                    'Description': 'Analytics team workgroup',
                    'CreationTime': datetime(2024, 1, 2),
                },
            ],
            'NextToken': 'next-workgroup-token',
        }
        result = await list_work_groups()
        assert isinstance(result, ListWorkgroupsResponse)
        assert len(result.workgroups) == 2
        assert result.workgroups[0].name == 'primary'
        assert result.workgroups[0].state.value == 'ENABLED'
        assert result.workgroups[0].description == 'Default workgroup'
        assert result.workgroups[0].creation_time == datetime(2024, 1, 1)
        assert result.workgroups[1].name == 'analytics-team'
        assert result.workgroups[1].state.value == 'ENABLED'
        assert result.workgroups[1].description == 'Analytics team workgroup'
        assert result.workgroups[1].creation_time == datetime(2024, 1, 2)
        assert result.next_token == 'next-workgroup-token'

    @pytest.mark.asyncio
    async def test_get_work_group_success(self, mock_athena_client):
        """Test successful workgroup details retrieval."""
        mock_athena_client.get_work_group.return_value = {
            'WorkGroup': {
                'Name': 'analytics-team',
                'State': 'ENABLED',
                'Description': 'Analytics team workgroup',
                'CreationTime': datetime(2024, 1, 1),
                'Configuration': {
                    'ResultConfiguration': {
                        'OutputLocation': 's3://analytics-results/',
                        'EncryptionConfiguration': {
                            'EncryptionOption': 'SSE_S3',
                        },
                    },
                    'EnforceWorkGroupConfiguration': True,
                    'PublishCloudWatchMetrics': True,
                    'BytesScannedCutoffPerQuery': 1000000000,
                    'RequesterPaysEnabled': False,
                    'EngineVersion': {
                        'SelectedEngineVersion': 'Athena engine version 3',
                    },
                },
            }
        }
        result = await get_work_group('analytics-team')
        assert isinstance(result, WorkgroupDetailsResponse)
        assert result.name == 'analytics-team'
        assert result.state.value == 'ENABLED'
        assert result.description == 'Analytics team workgroup'
        assert result.creation_time == datetime(2024, 1, 1)
        assert (
            result.configuration['result_configuration']['output_location']
            == 's3://analytics-results/'
        )
        assert result.configuration['result_configuration']['encryption_configuration'] == {
            'EncryptionOption': 'SSE_S3'
        }
        assert result.configuration['enforce_work_group_configuration'] is True
        assert result.configuration['publish_cloud_watch_metrics'] is True
        assert result.configuration['bytes_scanned_cutoff_per_query'] == 1000000000
        assert result.configuration['requester_pays_enabled'] is False
        assert result.configuration['engine_version'] == {
            'SelectedEngineVersion': 'Athena engine version 3'
        }


class TestDataCatalogOperations:
    """Test data catalog functionality."""

    @pytest.mark.asyncio
    async def test_list_data_catalogs_success(self, mock_athena_client):
        """Test successful data catalog listing."""
        mock_athena_client.list_data_catalogs.return_value = {
            'DataCatalogsSummary': [
                {
                    'CatalogName': 'AwsDataCatalog',
                    'Type': 'GLUE',
                },
                {
                    'CatalogName': 'custom-catalog',
                    'Type': 'HIVE',
                },
                {
                    'CatalogName': 'external-catalog',
                    'Type': 'LAMBDA',
                },
            ],
            'NextToken': 'next-catalog-token',
        }
        result = await list_data_catalogs()
        assert isinstance(result, ListDataCatalogsResponse)
        assert len(result.data_catalogs) == 3
        assert result.data_catalogs[0].catalog_name == 'AwsDataCatalog'
        assert result.data_catalogs[0].type.value == 'GLUE'
        assert result.data_catalogs[1].catalog_name == 'custom-catalog'
        assert result.data_catalogs[1].type.value == 'HIVE'
        assert result.data_catalogs[2].catalog_name == 'external-catalog'
        assert result.data_catalogs[2].type.value == 'LAMBDA'
        assert result.next_token == 'next-catalog-token'


class TestQueryValidationIntegration:
    """Test SQL query validation integration with server functions."""

    @pytest.mark.asyncio
    async def test_execute_query_validation_integration(self, mock_athena_client):
        """Test that execute_query properly validates queries."""
        with pytest.raises(ValueError, match='not permitted'):
            await execute_query('DROP TABLE users')
        mock_athena_client.start_query_execution.assert_not_called()


class TestQueryResultFormatting:
    """Test query result formatting for different query types."""

    @pytest.mark.parametrize(
        'query,aws_columns,aws_rows,expected_result',
        [
            (
                'SELECT id, name FROM users LIMIT 2',
                [
                    {'Name': 'id', 'Type': 'bigint', 'Nullable': 'UNKNOWN'},
                    {'Name': 'name', 'Type': 'varchar', 'Nullable': 'UNKNOWN'},
                ],
                [
                    {'Data': [{'VarCharValue': 'id'}, {'VarCharValue': 'name'}]},  # header
                    {'Data': [{'VarCharValue': '1'}, {'VarCharValue': 'Alice'}]},
                    {'Data': [{'VarCharValue': '2'}, {}]},  # NULL value
                ],
                {
                    'column_count': 2,
                    'column_names': ['id', 'name'],
                    'row_count': 2,
                    'rows': [
                        {'id': '1', 'name': 'Alice'},
                        {'id': '2', 'name': None},
                    ],
                },
            ),
            # SHOW TABLES result should format as single text cell
            (
                'SHOW TABLES IN database1',
                [{'Name': 'tab_name', 'Type': 'string', 'Nullable': 'UNKNOWN'}],
                [
                    {'Data': [{'VarCharValue': 'table1'}]},  # data (no header)
                    {'Data': [{'VarCharValue': 'table2'}]},
                    {'Data': [{'VarCharValue': 'table3'}]},
                ],
                {
                    'column_count': 1,
                    'column_names': ['tab_name'],
                    'row_count': 1,
                    'rows': [
                        {'tab_name': 'table1\ntable2\ntable3'},
                    ],
                },
            ),
            # DESCRIBE result should format as single text cell
            (
                'DESCRIBE users',
                [
                    {'Name': 'col_name', 'Type': 'string', 'Nullable': 'UNKNOWN'},
                    {'Name': 'data_type', 'Type': 'string', 'Nullable': 'UNKNOWN'},
                    {'Name': 'comment', 'Type': 'string', 'Nullable': 'UNKNOWN'},
                ],
                [
                    {'Data': [{'VarCharValue': 'id\tbigint\tfrom deserializer'}]},
                    {'Data': [{'VarCharValue': 'name\tstring\tfrom deserializer'}]},
                    {'Data': [{'VarCharValue': 'created_at\ttimestamp\tfrom deserializer'}]},
                ],
                {
                    'column_count': 1,
                    'column_names': ['col_name'],
                    'row_count': 1,
                    'rows': [
                        {
                            'col_name': 'id\tbigint\tfrom deserializer\nname\tstring\tfrom deserializer\ncreated_at\ttimestamp\tfrom deserializer'
                        }
                    ],
                },
            ),
            # EXPLAIN result should format as single text cell
            (
                'EXPLAIN SELECT COUNT(*) FROM users',
                [{'Name': 'Query Plan', 'Type': 'varchar', 'Nullable': 'UNKNOWN'}],
                [
                    {'Data': [{'VarCharValue': 'Query Plan'}]},
                    {'Data': [{'VarCharValue': 'Fragment 0 [SINGLE]'}]},
                    {'Data': [{'VarCharValue': '    Output layout: [count]'}]},
                ],
                {
                    'column_count': 1,
                    'column_names': ['Query Plan'],
                    'row_count': 1,
                    'rows': [
                        {
                            'Query Plan': 'Query Plan\nFragment 0 [SINGLE]\n    Output layout: [count]'
                        }
                    ],
                },
            ),
        ],
    )
    @pytest.mark.asyncio
    async def test_query_result_formatting(
        self, mock_athena_client, query, aws_columns, aws_rows, expected_result
    ):
        """Test query result formatting for different query types."""
        execution = {
            'QueryExecutionId': 'test-id',
            'Status': {'State': 'SUCCEEDED'},
            'Statistics': {'DataScannedInBytes': 100, 'EngineExecutionTimeInMillis': 500},
        }
        results = {
            'ResultSet': {
                'ResultSetMetadata': {'ColumnInfo': aws_columns},
                'Rows': aws_rows,
            },
        }
        mock_athena_client.start_query_execution.return_value = {'QueryExecutionId': 'test-id'}
        mock_athena_client.get_query_execution.return_value = {'QueryExecution': execution}
        mock_athena_client.get_query_results.return_value = results
        result = await execute_query(query)
        assert len(result.column_info) == expected_result['column_count']
        assert [col.name for col in result.column_info] == expected_result['column_names']
        assert len(result.rows) == expected_result['row_count']
        assert result.rows == expected_result['rows']
