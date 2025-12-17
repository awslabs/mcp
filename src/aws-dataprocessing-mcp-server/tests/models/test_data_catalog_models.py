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

"""Tests for the Data Catalog models."""

import pytest
from awslabs.aws_dataprocessing_mcp_server.models.data_catalog_models import (
    BatchOperationResult,
    # Summary models
    CatalogSummary,
    ConnectionSummary,
    CrawlerRun,
    CreateCatalogData,
    CreateConnectionData,
    # Data models
    CreateDatabaseData,
    CreatePartitionData,
    CreateTableData,
    DatabaseSummary,
    DataQualityResult,
    DeleteCatalogData,
    DeleteConnectionData,
    DeleteDatabaseData,
    DeletePartitionData,
    DeleteTableData,
    GetCatalogData,
    GetConnectionData,
    GetDatabaseData,
    GetPartitionData,
    GetTableData,
    GlueJobRun,
    # Utility models
    GlueOperation,
    ImportCatalogData,
    ListCatalogsData,
    ListConnectionsData,
    ListDatabasesData,
    ListPartitionsData,
    ListTablesData,
    PartitionSummary,
    SearchTablesData,
    TableSummary,
    UpdateConnectionData,
    UpdateDatabaseData,
    UpdatePartitionData,
    UpdateTableData,
)
from pydantic import ValidationError


class TestGlueOperation:
    """Tests for the GlueOperation enum."""

    def test_enum_values(self):
        """Test that the enum has the expected values."""
        assert GlueOperation.CREATE == 'create'
        assert GlueOperation.DELETE == 'delete'
        assert GlueOperation.GET == 'get'
        assert GlueOperation.LIST == 'list'
        assert GlueOperation.UPDATE == 'update'
        assert GlueOperation.SEARCH == 'search'
        assert GlueOperation.IMPORT == 'import'


class TestDatabaseSummary:
    """Tests for the DatabaseSummary model."""

    def test_create_with_required_fields(self):
        """Test creating a DatabaseSummary with only required fields."""
        db_summary = DatabaseSummary(name='test-db')
        assert db_summary.name == 'test-db'
        assert db_summary.description is None
        assert db_summary.location_uri is None
        assert db_summary.parameters == {}
        assert db_summary.creation_time is None

    def test_create_with_all_fields(self):
        """Test creating a DatabaseSummary with all fields."""
        db_summary = DatabaseSummary(
            name='test-db',
            description='Test database',
            location_uri='s3://test-bucket/',
            parameters={'key1': 'value1', 'key2': 'value2'},
            creation_time='2023-01-01T00:00:00Z',
        )
        assert db_summary.name == 'test-db'
        assert db_summary.description == 'Test database'
        assert db_summary.location_uri == 's3://test-bucket/'
        assert db_summary.parameters == {'key1': 'value1', 'key2': 'value2'}
        assert db_summary.creation_time == '2023-01-01T00:00:00Z'

    def test_missing_required_fields(self):
        """Test that creating a DatabaseSummary without required fields raises an error."""
        with pytest.raises(ValidationError):
            # Missing name parameter
            DatabaseSummary(
                description='Test', location_uri='s3://test', creation_time='2023-01-01'
            )


class TestTableSummary:
    """Tests for the TableSummary model."""

    def test_create_with_required_fields(self):
        """Test creating a TableSummary with only required fields."""
        table_summary = TableSummary(name='test-table', database_name='test-db')
        assert table_summary.name == 'test-table'
        assert table_summary.database_name == 'test-db'
        assert table_summary.owner is None
        assert table_summary.creation_time is None
        assert table_summary.update_time is None
        assert table_summary.last_access_time is None
        assert table_summary.storage_descriptor == {}
        assert table_summary.partition_keys == []

    def test_create_with_all_fields(self):
        """Test creating a TableSummary with all fields."""
        table_summary = TableSummary(
            name='test-table',
            database_name='test-db',
            owner='test-owner',
            creation_time='2023-01-01T00:00:00Z',
            update_time='2023-01-02T00:00:00Z',
            last_access_time='2023-01-03T00:00:00Z',
            storage_descriptor={
                'Columns': [{'Name': 'id', 'Type': 'int'}, {'Name': 'name', 'Type': 'string'}]
            },
            partition_keys=[
                {'Name': 'year', 'Type': 'string'},
                {'Name': 'month', 'Type': 'string'},
            ],
        )
        assert table_summary.name == 'test-table'
        assert table_summary.database_name == 'test-db'
        assert table_summary.owner == 'test-owner'
        assert table_summary.creation_time == '2023-01-01T00:00:00Z'
        assert table_summary.update_time == '2023-01-02T00:00:00Z'
        assert table_summary.last_access_time == '2023-01-03T00:00:00Z'
        assert table_summary.storage_descriptor['Columns'][0]['Name'] == 'id'
        assert table_summary.storage_descriptor['Columns'][1]['Type'] == 'string'
        assert table_summary.partition_keys[0]['Name'] == 'year'
        assert table_summary.partition_keys[1]['Type'] == 'string'

    def test_missing_required_fields(self):
        """Test that creating a TableSummary without required fields raises an error."""
        with pytest.raises(ValidationError):
            TableSummary(name='test-table')

        with pytest.raises(ValidationError):
            TableSummary(database_name='test-db')

        with pytest.raises(ValidationError):
            TableSummary()


class TestConnectionSummary:
    """Tests for the ConnectionSummary model."""

    def test_create_with_required_fields(self):
        """Test creating a ConnectionSummary with only required fields."""
        conn_summary = ConnectionSummary(name='test-conn', connection_type='JDBC')
        assert conn_summary.name == 'test-conn'
        assert conn_summary.connection_type == 'JDBC'
        assert conn_summary.connection_properties == {}
        assert conn_summary.physical_connection_requirements is None
        assert conn_summary.creation_time is None
        assert conn_summary.last_updated_time is None

    def test_create_with_all_fields(self):
        """Test creating a ConnectionSummary with all fields."""
        conn_summary = ConnectionSummary(
            name='test-conn',
            connection_type='JDBC',
            connection_properties={
                'JDBC_CONNECTION_URL': 'jdbc:mysql://localhost:3306/test',
                'USERNAME': 'test-user',
                'PASSWORD': 'test-password',  # pragma: allowlist secret
            },
            physical_connection_requirements={
                'AvailabilityZone': 'us-east-1a',
                'SecurityGroupIdList': ['sg-12345'],
                'SubnetId': 'subnet-12345',
            },
            creation_time='2023-01-01T00:00:00Z',
            last_updated_time='2023-01-02T00:00:00Z',
        )
        assert conn_summary.name == 'test-conn'
        assert conn_summary.connection_type == 'JDBC'
        assert (
            conn_summary.connection_properties['JDBC_CONNECTION_URL']
            == 'jdbc:mysql://localhost:3306/test'
        )
        assert conn_summary.connection_properties['USERNAME'] == 'test-user'
        assert (
            conn_summary.connection_properties['PASSWORD']
            == 'test-password'  # pragma: allowlist secret
        )
        assert conn_summary.physical_connection_requirements['AvailabilityZone'] == 'us-east-1a'
        assert conn_summary.physical_connection_requirements['SecurityGroupIdList'] == ['sg-12345']
        assert conn_summary.physical_connection_requirements['SubnetId'] == 'subnet-12345'
        assert conn_summary.creation_time == '2023-01-01T00:00:00Z'
        assert conn_summary.last_updated_time == '2023-01-02T00:00:00Z'

    def test_missing_required_fields(self):
        """Test that creating a ConnectionSummary without required fields raises an error."""
        with pytest.raises(ValidationError):
            # Missing connection_type parameter
            ConnectionSummary(
                name='test-conn',
                physical_connection_requirements={},
                creation_time='2023-01-01',
                last_updated_time='2023-01-02',
            )

        with pytest.raises(ValidationError):
            # Missing name parameter
            ConnectionSummary(
                connection_type='JDBC',
                physical_connection_requirements={},
                creation_time='2023-01-01',
                last_updated_time='2023-01-02',
            )

        with pytest.raises(ValidationError):
            # Missing both required parameters
            ConnectionSummary(
                physical_connection_requirements={},
                creation_time='2023-01-01',
                last_updated_time='2023-01-02',
            )


class TestPartitionSummary:
    """Tests for the PartitionSummary model."""

    def test_create_with_required_fields(self):
        """Test creating a PartitionSummary with only required fields."""
        partition_summary = PartitionSummary(
            values=['2023', '01', '01'], database_name='test-db', table_name='test-table'
        )
        assert partition_summary.values == ['2023', '01', '01']
        assert partition_summary.database_name == 'test-db'
        assert partition_summary.table_name == 'test-table'
        assert partition_summary.creation_time is None
        assert partition_summary.last_access_time is None
        assert partition_summary.storage_descriptor == {}
        assert partition_summary.parameters == {}

    def test_create_with_all_fields(self):
        """Test creating a PartitionSummary with all fields."""
        partition_summary = PartitionSummary(
            values=['2023', '01', '01'],
            database_name='test-db',
            table_name='test-table',
            creation_time='2023-01-01T00:00:00Z',
            last_access_time='2023-01-02T00:00:00Z',
            storage_descriptor={
                'Location': 's3://test-bucket/test-db/test-table/year=2023/month=01/day=01/'
            },
            parameters={'key1': 'value1', 'key2': 'value2'},
        )
        assert partition_summary.values == ['2023', '01', '01']
        assert partition_summary.database_name == 'test-db'
        assert partition_summary.table_name == 'test-table'
        assert partition_summary.creation_time == '2023-01-01T00:00:00Z'
        assert partition_summary.last_access_time == '2023-01-02T00:00:00Z'
        assert (
            partition_summary.storage_descriptor['Location']
            == 's3://test-bucket/test-db/test-table/year=2023/month=01/day=01/'
        )
        assert partition_summary.parameters == {'key1': 'value1', 'key2': 'value2'}

    def test_missing_required_fields(self):
        """Test that creating a PartitionSummary without required fields raises an error."""
        with pytest.raises(ValidationError):
            # Missing table_name parameter
            PartitionSummary(
                values=['2023', '01', '01'],
                database_name='test-db',
                creation_time='2023-01-01',
                last_access_time='2023-01-02',
            )

        with pytest.raises(ValidationError):
            # Missing database_name parameter
            PartitionSummary(
                values=['2023', '01', '01'],
                table_name='test-table',
                creation_time='2023-01-01',
                last_access_time='2023-01-02',
            )

        with pytest.raises(ValidationError):
            # Missing values parameter
            PartitionSummary(
                database_name='test-db',
                table_name='test-table',
                creation_time='2023-01-01',
                last_access_time='2023-01-02',
            )

        with pytest.raises(ValidationError):
            # Missing all required parameters
            PartitionSummary(creation_time='2023-01-01', last_access_time='2023-01-02')


class TestCatalogSummary:
    """Tests for the CatalogSummary model."""

    def test_create_with_required_fields(self):
        """Test creating a CatalogSummary with only required fields."""
        catalog_summary = CatalogSummary(catalog_id='test-catalog')
        assert catalog_summary.catalog_id == 'test-catalog'
        assert catalog_summary.name is None
        assert catalog_summary.description is None
        assert catalog_summary.parameters == {}
        assert catalog_summary.create_time is None

    def test_create_with_all_fields(self):
        """Test creating a CatalogSummary with all fields."""
        catalog_summary = CatalogSummary(
            catalog_id='test-catalog',
            name='Test Catalog',
            description='Test catalog description',
            parameters={'key1': 'value1', 'key2': 'value2'},
            create_time='2023-01-01T00:00:00Z',
        )
        assert catalog_summary.catalog_id == 'test-catalog'
        assert catalog_summary.name == 'Test Catalog'
        assert catalog_summary.description == 'Test catalog description'
        assert catalog_summary.parameters == {'key1': 'value1', 'key2': 'value2'}
        assert catalog_summary.create_time == '2023-01-01T00:00:00Z'

    def test_missing_required_fields(self):
        """Test that creating a CatalogSummary without required fields raises an error."""
        with pytest.raises(ValidationError):
            # Missing catalog_id parameter
            CatalogSummary(
                name='Test Catalog', description='Test description', create_time='2023-01-01'
            )


class TestDatabaseDataModels:
    """Tests for the database data models."""

    def test_create_database_data(self):
        """Test creating a CreateDatabaseData."""
        data = CreateDatabaseData(database_name='test-db')
        assert data.database_name == 'test-db'
        assert data.operation == 'create'  # Default value

    def test_delete_database_data(self):
        """Test creating a DeleteDatabaseData."""
        data = DeleteDatabaseData(database_name='test-db')
        assert data.database_name == 'test-db'
        assert data.operation == 'delete'  # Default value

    def test_get_database_data(self):
        """Test creating a GetDatabaseData."""
        data = GetDatabaseData(
            database_name='test-db',
            description='Test database',
            location_uri='s3://test-bucket/',
            parameters={'key1': 'value1'},
            creation_time='2023-01-01T00:00:00Z',
            catalog_id='123456789012',
        )
        assert data.database_name == 'test-db'
        assert data.description == 'Test database'
        assert data.location_uri == 's3://test-bucket/'
        assert data.parameters == {'key1': 'value1'}
        assert data.creation_time == '2023-01-01T00:00:00Z'
        assert data.catalog_id == '123456789012'
        assert data.operation == 'get'  # Default value

    def test_list_databases_data(self):
        """Test creating a ListDatabasesData."""
        db1 = DatabaseSummary(name='db1', description='Database 1')
        db2 = DatabaseSummary(name='db2', description='Database 2')

        data = ListDatabasesData(
            databases=[db1, db2],
            count=2,
            catalog_id='123456789012',
            next_token='next-page-token',
        )
        assert len(data.databases) == 2
        assert data.databases[0].name == 'db1'
        assert data.databases[1].name == 'db2'
        assert data.count == 2
        assert data.catalog_id == '123456789012'
        assert data.next_token == 'next-page-token'
        assert data.operation == 'list'  # Default value

    def test_update_database_data(self):
        """Test creating an UpdateDatabaseData."""
        data = UpdateDatabaseData(database_name='test-db')
        assert data.database_name == 'test-db'
        assert data.operation == 'update'  # Default value


class TestTableDataModels:
    """Tests for the table data models."""

    def test_create_table_data(self):
        """Test creating a CreateTableData."""
        data = CreateTableData(database_name='test-db', table_name='test-table')
        assert data.database_name == 'test-db'
        assert data.table_name == 'test-table'
        assert data.operation == 'create'  # Default value

    def test_delete_table_data(self):
        """Test creating a DeleteTableData."""
        data = DeleteTableData(database_name='test-db', table_name='test-table')
        assert data.database_name == 'test-db'
        assert data.table_name == 'test-table'
        assert data.operation == 'delete'  # Default value

    def test_get_table_data(self):
        """Test creating a GetTableData."""
        table_definition = {
            'Name': 'test-table',
            'DatabaseName': 'test-db',
            'StorageDescriptor': {
                'Columns': [{'Name': 'id', 'Type': 'int'}, {'Name': 'name', 'Type': 'string'}]
            },
        }

        data = GetTableData(
            database_name='test-db',
            table_name='test-table',
            table_definition=table_definition,
            creation_time='2023-01-01T00:00:00Z',
            last_access_time='2023-01-02T00:00:00Z',
            storage_descriptor={
                'Columns': [{'Name': 'id', 'Type': 'int'}, {'Name': 'name', 'Type': 'string'}]
            },
            partition_keys=[{'Name': 'year', 'Type': 'string'}],
        )
        assert data.database_name == 'test-db'
        assert data.table_name == 'test-table'
        assert data.table_definition == table_definition
        assert data.creation_time == '2023-01-01T00:00:00Z'
        assert data.last_access_time == '2023-01-02T00:00:00Z'
        assert data.operation == 'get'  # Default value

    def test_list_tables_data(self):
        """Test creating a ListTablesData."""
        table1 = TableSummary(name='table1', database_name='test-db')
        table2 = TableSummary(name='table2', database_name='test-db')

        data = ListTablesData(
            database_name='test-db',
            tables=[table1, table2],
            count=2,
        )
        assert data.database_name == 'test-db'
        assert len(data.tables) == 2
        assert data.tables[0].name == 'table1'
        assert data.tables[1].name == 'table2'
        assert data.count == 2
        assert data.operation == 'list'  # Default value

    def test_update_table_data(self):
        """Test creating an UpdateTableData."""
        data = UpdateTableData(database_name='test-db', table_name='test-table')
        assert data.database_name == 'test-db'
        assert data.table_name == 'test-table'
        assert data.operation == 'update'  # Default value

    def test_search_tables_data(self):
        """Test creating a SearchTablesData."""
        table1 = TableSummary(name='test_table1', database_name='db1')
        table2 = TableSummary(name='test_table2', database_name='db2')

        data = SearchTablesData(
            tables=[table1, table2],
            search_text='test',
            count=2,
            next_token='next-page-token',
        )
        assert len(data.tables) == 2
        assert data.tables[0].name == 'test_table1'
        assert data.tables[1].name == 'test_table2'
        assert data.search_text == 'test'
        assert data.count == 2
        assert data.next_token == 'next-page-token'
        assert data.operation == 'search'  # Default value


class TestConnectionDataModels:
    """Tests for the connection data models."""

    def test_create_connection_data(self):
        """Test creating a CreateConnectionData."""
        data = CreateConnectionData(
            connection_name='test-conn',
            catalog_id='123456789012',
        )
        assert data.connection_name == 'test-conn'
        assert data.catalog_id == '123456789012'
        assert data.operation == 'create'  # Default value

    def test_delete_connection_data(self):
        """Test creating a DeleteConnectionData."""
        data = DeleteConnectionData(
            connection_name='test-conn',
            catalog_id='123456789012',
        )
        assert data.connection_name == 'test-conn'
        assert data.catalog_id == '123456789012'
        assert data.operation == 'delete'  # Default value

    def test_get_connection_data(self):
        """Test creating a GetConnectionData."""
        data = GetConnectionData(
            connection_name='test-conn',
            connection_type='JDBC',
            connection_properties={
                'JDBC_CONNECTION_URL': 'jdbc:mysql://localhost:3306/test',
                'USERNAME': 'test-user',
            },
            physical_connection_requirements={
                'AvailabilityZone': 'us-east-1a',
                'SecurityGroupIdList': ['sg-12345'],
                'SubnetId': 'subnet-12345',
            },
            creation_time='2023-01-01T00:00:00Z',
            last_updated_time='2023-01-02T00:00:00Z',
            last_updated_by='test-user',
            status='READY',
            status_reason='Connection is ready',
            last_connection_validation_time='2023-01-03T00:00:00Z',
            catalog_id='123456789012',
        )
        assert data.connection_name == 'test-conn'
        assert data.connection_type == 'JDBC'
        assert (
            data.connection_properties['JDBC_CONNECTION_URL'] == 'jdbc:mysql://localhost:3306/test'
        )
        assert data.connection_properties['USERNAME'] == 'test-user'
        assert data.physical_connection_requirements['AvailabilityZone'] == 'us-east-1a'
        assert data.creation_time == '2023-01-01T00:00:00Z'
        assert data.last_updated_time == '2023-01-02T00:00:00Z'
        assert data.last_updated_by == 'test-user'
        assert data.status == 'READY'
        assert data.status_reason == 'Connection is ready'
        assert data.last_connection_validation_time == '2023-01-03T00:00:00Z'
        assert data.catalog_id == '123456789012'
        assert data.operation == 'get'  # Default value

    def test_list_connections_data(self):
        """Test creating a ListConnectionsData."""
        conn1 = ConnectionSummary(name='conn1', connection_type='JDBC')
        conn2 = ConnectionSummary(name='conn2', connection_type='KAFKA')

        data = ListConnectionsData(
            connections=[conn1, conn2],
            count=2,
            catalog_id='123456789012',
            next_token='next-page-token',
        )
        assert len(data.connections) == 2
        assert data.connections[0].name == 'conn1'
        assert data.connections[1].name == 'conn2'
        assert data.count == 2
        assert data.catalog_id == '123456789012'
        assert data.next_token == 'next-page-token'
        assert data.operation == 'list'  # Default value

    def test_update_connection_data(self):
        """Test creating an UpdateConnectionData."""
        data = UpdateConnectionData(
            connection_name='test-conn',
            catalog_id='123456789012',
        )
        assert data.connection_name == 'test-conn'
        assert data.catalog_id == '123456789012'
        assert data.operation == 'update'  # Default value


class TestPartitionDataModels:
    """Tests for the partition data models."""

    def test_create_partition_data(self):
        """Test creating a CreatePartitionData."""
        data = CreatePartitionData(
            database_name='test-db',
            table_name='test-table',
            partition_values=['2023', '01', '01'],
        )
        assert data.database_name == 'test-db'
        assert data.table_name == 'test-table'
        assert data.partition_values == ['2023', '01', '01']
        assert data.operation == 'create'  # Default value

    def test_delete_partition_data(self):
        """Test creating a DeletePartitionData."""
        data = DeletePartitionData(
            database_name='test-db',
            table_name='test-table',
            partition_values=['2023', '01', '01'],
        )
        assert data.database_name == 'test-db'
        assert data.table_name == 'test-table'
        assert data.partition_values == ['2023', '01', '01']
        assert data.operation == 'delete'  # Default value

    def test_get_partition_data(self):
        """Test creating a GetPartitionData."""
        partition_definition = {
            'Values': ['2023', '01', '01'],
            'StorageDescriptor': {
                'Location': 's3://test-bucket/test-db/test-table/year=2023/month=01/day=01/'
            },
            'Parameters': {'key1': 'value1'},
        }

        data = GetPartitionData(
            database_name='test-db',
            table_name='test-table',
            partition_values=['2023', '01', '01'],
            partition_definition=partition_definition,
            creation_time='2023-01-01T00:00:00Z',
            last_access_time='2023-01-02T00:00:00Z',
            storage_descriptor={
                'Location': 's3://test-bucket/test-db/test-table/year=2023/month=01/day=01/'
            },
            parameters={'key1': 'value1'},
        )
        assert data.database_name == 'test-db'
        assert data.table_name == 'test-table'
        assert data.partition_values == ['2023', '01', '01']
        assert data.partition_definition == partition_definition
        assert data.creation_time == '2023-01-01T00:00:00Z'
        assert data.last_access_time == '2023-01-02T00:00:00Z'
        assert (
            data.storage_descriptor['Location']
            == 's3://test-bucket/test-db/test-table/year=2023/month=01/day=01/'
        )
        assert data.parameters == {'key1': 'value1'}
        assert data.operation == 'get'  # Default value

    def test_list_partitions_data(self):
        """Test creating a ListPartitionsData."""
        partition1 = PartitionSummary(
            values=['2023', '01', '01'], database_name='test-db', table_name='test-table'
        )
        partition2 = PartitionSummary(
            values=['2023', '01', '02'], database_name='test-db', table_name='test-table'
        )

        data = ListPartitionsData(
            database_name='test-db',
            table_name='test-table',
            partitions=[partition1, partition2],
            count=2,
            expression='year = 2023',
            next_token='next-page-token',
        )
        assert data.database_name == 'test-db'
        assert data.table_name == 'test-table'
        assert len(data.partitions) == 2
        assert data.partitions[0].values == ['2023', '01', '01']
        assert data.partitions[1].values == ['2023', '01', '02']
        assert data.count == 2
        assert data.expression == 'year = 2023'
        assert data.next_token == 'next-page-token'
        assert data.operation == 'list'  # Default value

    def test_update_partition_data(self):
        """Test creating an UpdatePartitionData."""
        data = UpdatePartitionData(
            database_name='test-db',
            table_name='test-table',
            partition_values=['2023', '01', '01'],
        )
        assert data.database_name == 'test-db'
        assert data.table_name == 'test-table'
        assert data.partition_values == ['2023', '01', '01']
        assert data.operation == 'update'  # Default value


class TestCatalogDataModels:
    """Tests for the catalog data models."""

    def test_create_catalog_data(self):
        """Test creating a CreateCatalogData."""
        data = CreateCatalogData(catalog_id='test-catalog')
        assert data.catalog_id == 'test-catalog'
        assert data.operation == 'create'  # Default value

    def test_delete_catalog_data(self):
        """Test creating a DeleteCatalogData."""
        data = DeleteCatalogData(catalog_id='test-catalog')
        assert data.catalog_id == 'test-catalog'
        assert data.operation == 'delete'  # Default value

    def test_get_catalog_data(self):
        """Test creating a GetCatalogData."""
        catalog_definition = {
            'Name': 'Test Catalog',
            'Description': 'Test catalog description',
            'Parameters': {'key1': 'value1'},
        }

        data = GetCatalogData(
            catalog_id='test-catalog',
            catalog_definition=catalog_definition,
            name='Test Catalog',
            description='Test catalog description',
            parameters={'key1': 'value1'},
            create_time='2023-01-01T00:00:00Z',
            update_time='2023-01-02T00:00:00Z',
        )
        assert data.catalog_id == 'test-catalog'
        assert data.catalog_definition == catalog_definition
        assert data.name == 'Test Catalog'
        assert data.description == 'Test catalog description'
        assert data.parameters == {'key1': 'value1'}
        assert data.create_time == '2023-01-01T00:00:00Z'
        assert data.update_time == '2023-01-02T00:00:00Z'
        assert data.operation == 'get'  # Default value

    def test_list_catalogs_data(self):
        """Test creating a ListCatalogsData."""
        catalog1 = CatalogSummary(catalog_id='catalog1', name='Catalog 1')
        catalog2 = CatalogSummary(catalog_id='catalog2', name='Catalog 2')

        data = ListCatalogsData(
            catalogs=[catalog1, catalog2],
            count=2,
        )
        assert len(data.catalogs) == 2
        assert data.catalogs[0].catalog_id == 'catalog1'
        assert data.catalogs[1].catalog_id == 'catalog2'
        assert data.count == 2
        assert data.operation == 'list'  # Default value

    def test_import_catalog_data(self):
        """Test creating an ImportCatalogData."""
        data = ImportCatalogData(catalog_id='test-catalog')
        assert data.catalog_id == 'test-catalog'
        assert data.operation == 'import'  # Default value


class TestUtilityModels:
    """Tests for utility models."""

    def test_glue_job_run(self):
        """Test creating a GlueJobRun."""
        job_run = GlueJobRun(
            job_run_id='jr_12345',
            job_name='test-job',
            job_run_state='SUCCEEDED',
            started_on='2023-01-01T10:00:00Z',
            completed_on='2023-01-01T10:30:00Z',
            execution_time=1800,
            error_message=None,
        )
        assert job_run.job_run_id == 'jr_12345'
        assert job_run.job_name == 'test-job'
        assert job_run.job_run_state == 'SUCCEEDED'
        assert job_run.started_on == '2023-01-01T10:00:00Z'
        assert job_run.completed_on == '2023-01-01T10:30:00Z'
        assert job_run.execution_time == 1800
        assert job_run.error_message is None

    def test_batch_operation_result(self):
        """Test creating a BatchOperationResult."""
        result = BatchOperationResult(
            total_requested=10,
            successful=8,
            failed=2,
            errors=[
                {'table': 'table1', 'error': 'Access denied'},
                {'table': 'table2', 'error': 'Table not found'},
            ],
        )
        assert result.total_requested == 10
        assert result.successful == 8
        assert result.failed == 2
        assert len(result.errors) == 2
        assert result.errors[0]['table'] == 'table1'
        assert result.errors[1]['error'] == 'Table not found'

    def test_data_quality_result(self):
        """Test creating a DataQualityResult."""
        result = DataQualityResult(
            result_id='dq_12345',
            score=0.85,
            started_on='2023-01-01T10:00:00Z',
            completed_on='2023-01-01T10:15:00Z',
            rule_results=[
                {'rule': 'completeness', 'passed': True, 'score': 0.9},
                {'rule': 'uniqueness', 'passed': False, 'score': 0.8},
            ],
        )
        assert result.result_id == 'dq_12345'
        assert result.score == 0.85
        assert result.started_on == '2023-01-01T10:00:00Z'
        assert result.completed_on == '2023-01-01T10:15:00Z'
        assert len(result.rule_results) == 2
        assert result.rule_results[0]['rule'] == 'completeness'
        assert result.rule_results[1]['passed'] is False

    def test_crawler_run(self):
        """Test creating a CrawlerRun."""
        run = CrawlerRun(
            crawler_name='test-crawler',
            state='SUCCEEDED',
            start_time='2023-01-01T10:00:00Z',
            end_time='2023-01-01T10:20:00Z',
            tables_created=5,
            tables_updated=2,
            tables_deleted=1,
        )
        assert run.crawler_name == 'test-crawler'
        assert run.state == 'SUCCEEDED'
        assert run.start_time == '2023-01-01T10:00:00Z'
        assert run.end_time == '2023-01-01T10:20:00Z'
        assert run.tables_created == 5
        assert run.tables_updated == 2
        assert run.tables_deleted == 1
