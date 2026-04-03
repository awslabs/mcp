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


from awslabs.aws_dataprocessing_mcp_server.models.athena_models import (
    BatchGetNamedQueryData,
    BatchGetQueryExecutionData,
    CreateDataCatalogData,
    CreateNamedQueryData,
    CreateWorkGroupData,
    DeleteDataCatalogData,
    DeleteNamedQueryData,
    DeleteWorkGroupData,
    GetDatabaseData,
    GetDataCatalogData,
    GetNamedQueryData,
    GetQueryExecutionData,
    GetQueryResultsData,
    GetQueryRuntimeStatisticsData,
    GetTableMetadataData,
    GetWorkGroupData,
    ListDatabasesData,
    ListDataCatalogsData,
    ListNamedQueriesData,
    ListQueryExecutionsData,
    ListTableMetadataData,
    ListWorkGroupsData,
    StartQueryExecutionData,
    StopQueryExecutionData,
    UpdateDataCatalogData,
    UpdateNamedQueryData,
    UpdateWorkGroupData,
)


# Test data
sample_dict = {'key': 'value'}
sample_list = [{'id': 1}, {'id': 2}]


class TestQueryExecutionData:
    """Test class for Athena query execution data models."""

    def test_batch_get_query_execution_data(self):
        """Test the BatchGetQueryExecutionData model."""
        data = BatchGetQueryExecutionData(
            query_executions=sample_list,
            unprocessed_query_execution_ids=[],
            operation='batch-get-query-execution',
        )
        assert data.query_executions == sample_list
        assert data.unprocessed_query_execution_ids == []
        assert data.operation == 'batch-get-query-execution'

    def test_get_query_execution_data(self):
        """Test the GetQueryExecutionData model."""
        data = GetQueryExecutionData(
            query_execution_id='query-123',
            query_execution=sample_dict,
            operation='get-query-execution',
        )
        assert data.query_execution_id == 'query-123'
        assert data.query_execution == sample_dict
        assert data.operation == 'get-query-execution'

    def test_get_query_results_data(self):
        """Test the GetQueryResultsData model."""
        data = GetQueryResultsData(
            query_execution_id='query-123',
            result_set=sample_dict,
            next_token='next-page',
            update_count=10,
            operation='get-query-results',
        )
        assert data.query_execution_id == 'query-123'
        assert data.result_set == sample_dict
        assert data.next_token == 'next-page'
        assert data.update_count == 10
        assert data.operation == 'get-query-results'

    def test_get_query_runtime_statistics_data(self):
        """Test the GetQueryRuntimeStatisticsData model."""
        data = GetQueryRuntimeStatisticsData(
            query_execution_id='query-123',
            statistics=sample_dict,
            operation='get-query-runtime-statistics',
        )
        assert data.query_execution_id == 'query-123'
        assert data.statistics == sample_dict
        assert data.operation == 'get-query-runtime-statistics'

    def test_list_query_executions_data(self):
        """Test the ListQueryExecutionsData model."""
        data = ListQueryExecutionsData(
            query_execution_ids=['query-1', 'query-2'],
            count=2,
            next_token='next-page',
            operation='list-query-executions',
        )
        assert data.query_execution_ids == ['query-1', 'query-2']
        assert data.count == 2
        assert data.next_token == 'next-page'
        assert data.operation == 'list-query-executions'

    def test_start_query_execution_data(self):
        """Test the StartQueryExecutionData model."""
        data = StartQueryExecutionData(
            query_execution_id='query-123', operation='start-query-execution'
        )
        assert data.query_execution_id == 'query-123'
        assert data.operation == 'start-query-execution'

    def test_stop_query_execution_data(self):
        """Test the StopQueryExecutionData model."""
        data = StopQueryExecutionData(
            query_execution_id='query-123', operation='stop-query-execution'
        )
        assert data.query_execution_id == 'query-123'
        assert data.operation == 'stop-query-execution'


class TestNamedQueryData:
    """Test class for Athena named query data models."""

    def test_batch_get_named_query_data(self):
        """Test the BatchGetNamedQueryData model."""
        data = BatchGetNamedQueryData(
            named_queries=sample_list,
            unprocessed_named_query_ids=[],
            operation='batch-get-named-query',
        )
        assert data.named_queries == sample_list
        assert data.unprocessed_named_query_ids == []
        assert data.operation == 'batch-get-named-query'

    def test_create_named_query_data(self):
        """Test the CreateNamedQueryData model."""
        data = CreateNamedQueryData(named_query_id='query-123', operation='create-named-query')
        assert data.named_query_id == 'query-123'
        assert data.operation == 'create-named-query'

    def test_delete_named_query_data(self):
        """Test the DeleteNamedQueryData model."""
        data = DeleteNamedQueryData(named_query_id='query-123', operation='delete-named-query')
        assert data.named_query_id == 'query-123'
        assert data.operation == 'delete-named-query'

    def test_get_named_query_data(self):
        """Test the GetNamedQueryData model."""
        data = GetNamedQueryData(
            named_query_id='query-123', named_query=sample_dict, operation='get-named-query'
        )
        assert data.named_query_id == 'query-123'
        assert data.named_query == sample_dict
        assert data.operation == 'get-named-query'

    def test_list_named_queries_data(self):
        """Test the ListNamedQueriesData model."""
        data = ListNamedQueriesData(
            named_query_ids=['query-1', 'query-2'],
            count=2,
            next_token='next-page',
            operation='list-named-queries',
        )
        assert data.named_query_ids == ['query-1', 'query-2']
        assert data.count == 2
        assert data.next_token == 'next-page'
        assert data.operation == 'list-named-queries'

    def test_update_named_query_data(self):
        """Test the UpdateNamedQueryData model."""
        data = UpdateNamedQueryData(named_query_id='query-123', operation='update-named-query')
        assert data.named_query_id == 'query-123'
        assert data.operation == 'update-named-query'


def test_optional_fields():
    """Test data models with optional fields."""
    # Test data with optional next_token
    results_data = GetQueryResultsData(
        query_execution_id='query-123',
        result_set=sample_dict,
        next_token=None,
        update_count=None,
        operation='get-query-results',
    )
    assert results_data.next_token is None
    assert results_data.update_count is None

    # Test data with optional next_token in list data
    list_data = ListQueryExecutionsData(
        query_execution_ids=['query-1', 'query-2'],
        count=2,
        next_token=None,
        operation='list-query-executions',
    )
    assert list_data.next_token is None

    # Test data with optional next_token in named queries list data
    named_list_data = ListNamedQueriesData(
        named_query_ids=['query-1', 'query-2'],
        count=2,
        next_token=None,
        operation='list-named-queries',
    )
    assert named_list_data.next_token is None


def test_complex_data_structures():
    """Test data models with more complex data structures."""
    # Complex query execution
    complex_execution = {
        'QueryExecutionId': 'query-123',
        'Query': 'SELECT * FROM table',
        'StatementType': 'DML',
        'ResultConfiguration': {'OutputLocation': 's3://bucket/path'},
        'QueryExecutionContext': {'Database': 'test_db'},
        'Status': {
            'State': 'SUCCEEDED',
            'SubmissionDateTime': '2023-01-01T00:00:00.000Z',
            'CompletionDateTime': '2023-01-01T00:01:00.000Z',
        },
        'Statistics': {
            'EngineExecutionTimeInMillis': 5000,
            'DataScannedInBytes': 1024,
            'TotalExecutionTimeInMillis': 6000,
        },
        'WorkGroup': 'primary',
    }

    # Complex result set
    complex_result_set = {
        'ResultSetMetadata': {
            'ColumnInfo': [
                {'Name': 'col1', 'Type': 'varchar'},
                {'Name': 'col2', 'Type': 'integer'},
            ]
        },
        'Rows': [
            {'Data': [{'VarCharValue': 'header1'}, {'VarCharValue': 'header2'}]},
            {'Data': [{'VarCharValue': 'value1'}, {'VarCharValue': '42'}]},
        ],
    }

    # Complex statistics
    complex_statistics = {
        'EngineExecutionTimeInMillis': 5000,
        'DataScannedInBytes': 1024,
        'TotalExecutionTimeInMillis': 6000,
        'QueryQueueTimeInMillis': 100,
        'ServiceProcessingTimeInMillis': 50,
        'QueryPlanningTimeInMillis': 200,
        'QueryStages': [
            {
                'StageId': 0,
                'State': 'SUCCEEDED',
                'OutputBytes': 1024,
                'OutputRows': 10,
                'InputBytes': 2048,
                'InputRows': 20,
                'ExecutionTime': 5000,
            }
        ],
    }

    # Test with complex query execution
    execution_data = GetQueryExecutionData(
        query_execution_id='query-123',
        query_execution=complex_execution,
        operation='get-query-execution',
    )
    assert execution_data.query_execution['Status']['State'] == 'SUCCEEDED'
    assert execution_data.query_execution['Statistics']['DataScannedInBytes'] == 1024

    # Test with complex result set
    results_data = GetQueryResultsData(
        query_execution_id='query-123',
        result_set=complex_result_set,
        operation='get-query-results',
    )
    assert len(results_data.result_set['Rows']) == 2
    assert results_data.result_set['ResultSetMetadata']['ColumnInfo'][0]['Name'] == 'col1'

    # Test with complex statistics
    statistics_data = GetQueryRuntimeStatisticsData(
        query_execution_id='query-123',
        statistics=complex_statistics,
        operation='get-query-runtime-statistics',
    )
    assert statistics_data.statistics['DataScannedInBytes'] == 1024
    assert statistics_data.statistics['QueryStages'][0]['OutputRows'] == 10


class TestDataCatalogData:
    """Test class for Athena data catalog data models."""

    def test_create_data_catalog_data(self):
        """Test the CreateDataCatalogData model."""
        data = CreateDataCatalogData(name='test-catalog', operation='create')
        assert data.name == 'test-catalog'
        assert data.operation == 'create'

    def test_delete_data_catalog_data(self):
        """Test the DeleteDataCatalogData model."""
        data = DeleteDataCatalogData(name='test-catalog', operation='delete')
        assert data.name == 'test-catalog'
        assert data.operation == 'delete'

    def test_get_data_catalog_data(self):
        """Test the GetDataCatalogData model."""
        catalog_details = {
            'Name': 'test-catalog',
            'Type': 'LAMBDA',
            'Description': 'Test catalog description',
            'Parameters': {'function': 'lambda-function-name'},
            'Status': 'ACTIVE',
            'ConnectionType': 'DIRECT',
        }
        data = GetDataCatalogData(data_catalog=catalog_details, operation='get')
        assert data.data_catalog == catalog_details
        assert data.data_catalog['Name'] == 'test-catalog'
        assert data.operation == 'get'

    def test_list_data_catalogs_data(self):
        """Test the ListDataCatalogsData model."""
        catalogs = [
            {
                'CatalogName': 'catalog1',
                'Type': 'LAMBDA',
                'Status': 'ACTIVE',
                'ConnectionType': 'DIRECT',
            },
            {
                'CatalogName': 'catalog2',
                'Type': 'GLUE',
                'Status': 'ACTIVE',
                'ConnectionType': 'DIRECT',
            },
        ]
        data = ListDataCatalogsData(
            data_catalogs=catalogs, count=2, next_token='next-page', operation='list'
        )
        assert data.data_catalogs == catalogs
        assert data.count == 2
        assert data.next_token == 'next-page'
        assert data.operation == 'list'

    def test_update_data_catalog_data(self):
        """Test the UpdateDataCatalogData model."""
        data = UpdateDataCatalogData(name='test-catalog', operation='update')
        assert data.name == 'test-catalog'
        assert data.operation == 'update'

    def test_get_database_data(self):
        """Test the GetDatabaseData model."""
        database_details = {
            'Name': 'test-database',
            'Description': 'Test database description',
            'Parameters': {'created_by': 'test-user'},
        }
        data = GetDatabaseData(database=database_details, operation='get')
        assert data.database == database_details
        assert data.database['Name'] == 'test-database'
        assert data.operation == 'get'

    def test_get_table_metadata_data(self):
        """Test the GetTableMetadataData model."""
        table_metadata = {
            'Name': 'test-table',
            'CreateTime': '2023-01-01T00:00:00.000Z',
            'LastAccessTime': '2023-01-02T00:00:00.000Z',
            'TableType': 'EXTERNAL_TABLE',
            'Columns': [
                {'Name': 'id', 'Type': 'int'},
                {'Name': 'name', 'Type': 'string'},
            ],
            'PartitionKeys': [{'Name': 'date', 'Type': 'string'}],
            'Parameters': {'EXTERNAL': 'TRUE'},
        }
        data = GetTableMetadataData(table_metadata=table_metadata, operation='get')
        assert data.table_metadata == table_metadata
        assert data.table_metadata['Name'] == 'test-table'
        assert len(data.table_metadata['Columns']) == 2
        assert data.operation == 'get'

    def test_list_databases_data(self):
        """Test the ListDatabasesData model."""
        databases = [
            {
                'Name': 'database1',
                'Description': 'First test database',
                'Parameters': {'created_by': 'user1'},
            },
            {
                'Name': 'database2',
                'Description': 'Second test database',
                'Parameters': {'created_by': 'user2'},
            },
        ]
        data = ListDatabasesData(
            database_list=databases, count=2, next_token='next-page', operation='list'
        )
        assert data.database_list == databases
        assert data.count == 2
        assert data.next_token == 'next-page'
        assert data.operation == 'list'

    def test_list_table_metadata_data(self):
        """Test the ListTableMetadataData model."""
        tables = [
            {
                'Name': 'table1',
                'CreateTime': '2023-01-01T00:00:00.000Z',
                'TableType': 'EXTERNAL_TABLE',
                'Columns': [{'Name': 'id', 'Type': 'int'}],
            },
            {
                'Name': 'table2',
                'CreateTime': '2023-01-02T00:00:00.000Z',
                'TableType': 'MANAGED_TABLE',
                'Columns': [{'Name': 'name', 'Type': 'string'}],
            },
        ]
        data = ListTableMetadataData(
            table_metadata_list=tables, count=2, next_token='next-page', operation='list'
        )
        assert data.table_metadata_list == tables
        assert data.count == 2
        assert data.next_token == 'next-page'
        assert data.operation == 'list'


class TestWorkGroupData:
    """Test class for Athena work group data models."""

    def test_create_work_group_data(self):
        """Test the CreateWorkGroupData model."""
        data = CreateWorkGroupData(work_group_name='test-workgroup', operation='create-work-group')
        assert data.work_group_name == 'test-workgroup'
        assert data.operation == 'create-work-group'

    def test_delete_work_group_data(self):
        """Test the DeleteWorkGroupData model."""
        data = DeleteWorkGroupData(work_group_name='test-workgroup', operation='delete-work-group')
        assert data.work_group_name == 'test-workgroup'
        assert data.operation == 'delete-work-group'

    def test_get_work_group_data(self):
        """Test the GetWorkGroupData model."""
        work_group_details = {
            'Name': 'test-workgroup',
            'State': 'ENABLED',
            'Configuration': {
                'ResultConfiguration': {'OutputLocation': 's3://bucket/path'},
                'EnforceWorkGroupConfiguration': True,
                'PublishCloudWatchMetricsEnabled': True,
                'BytesScannedCutoffPerQuery': 10000000,
                'RequesterPaysEnabled': False,
            },
            'Description': 'Test work group',
            'CreationTime': '2023-01-01T00:00:00.000Z',
        }
        data = GetWorkGroupData(work_group=work_group_details, operation='get-work-group')
        assert data.work_group == work_group_details
        assert data.work_group['Name'] == 'test-workgroup'
        assert data.operation == 'get-work-group'

    def test_list_work_groups_data(self):
        """Test the ListWorkGroupsData model."""
        work_groups = [
            {
                'Name': 'workgroup1',
                'State': 'ENABLED',
                'Description': 'First test work group',
            },
            {
                'Name': 'workgroup2',
                'State': 'DISABLED',
                'Description': 'Second test work group',
            },
        ]
        data = ListWorkGroupsData(
            work_groups=work_groups, count=2, next_token='next-page', operation='list-work-groups'
        )
        assert data.work_groups == work_groups
        assert data.count == 2
        assert data.next_token == 'next-page'
        assert data.operation == 'list-work-groups'

    def test_update_work_group_data(self):
        """Test the UpdateWorkGroupData model."""
        data = UpdateWorkGroupData(work_group_name='test-workgroup', operation='update-work-group')
        assert data.work_group_name == 'test-workgroup'
        assert data.operation == 'update-work-group'


def test_model_serialization():
    """Test that all data models can be serialized using model_dump()."""
    # Test a simple data model
    create_data = CreateDataCatalogData(name='test-catalog', operation='create')
    dumped = create_data.model_dump()
    assert dumped['name'] == 'test-catalog'
    assert dumped['operation'] == 'create'

    # Test a complex data model
    complex_data = GetQueryResultsData(
        query_execution_id='query-123',
        result_set={'columns': [{'name': 'col1', 'type': 'varchar'}]},
        next_token='next-page',
        update_count=10,
        operation='get-query-results',
    )
    dumped_complex = complex_data.model_dump()
    assert dumped_complex['query_execution_id'] == 'query-123'
    assert dumped_complex['result_set']['columns'][0]['name'] == 'col1'
    assert dumped_complex['next_token'] == 'next-page'
    assert dumped_complex['update_count'] == 10
    assert dumped_complex['operation'] == 'get-query-results'
