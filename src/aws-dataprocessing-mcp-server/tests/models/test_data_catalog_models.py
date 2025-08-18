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
    # Extended response models
    CatalogSummary,
    ConnectionSummary,
    CreateCatalogResponse,
    # Connection response models
    CreateConnectionResponse,
    # Database response models
    CreateDatabaseResponse,
    # Partition response models
    CreatePartitionResponse,
    # Table response models
    CreateTableResponse,
    # Summary models
    DatabaseSummary,
    DeleteConnectionResponse,
    DeleteDatabaseResponse,
    DeleteTableResponse,
    GetCatalogResponse,
    GetConnectionResponse,
    GetDatabaseResponse,
    GetPartitionResponse,
    GetTableResponse,
    # Additional utility models
    GlueOperation,
    ListDatabasesResponse,
    ListTablesResponse,
    PartitionSummary,
    SearchTablesResponse,
    TableSummary,
    UpdateDatabaseResponse,
    UpdateTableResponse,
)
from mcp.types import TextContent
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


class TestDatabaseResponseModels:
    """Tests for the database response models."""

    def test_create_database_response(self):
        """Test creating a CreateDatabaseResponse."""
        response = CreateDatabaseResponse(
            isError=False,
            database_name='test-db',
            content=[TextContent(type='text', text='Successfully created database')],
        )
        assert response.isError is False
        assert response.database_name == 'test-db'
        assert response.operation == 'create'  # Default value
        assert len(response.content) == 1
        assert response.content[0].text == 'Successfully created database'

    def test_delete_database_response(self):
        """Test creating a DeleteDatabaseResponse."""
        response = DeleteDatabaseResponse(
            isError=False,
            database_name='test-db',
            content=[TextContent(type='text', text='Successfully deleted database')],
        )
        assert response.isError is False
        assert response.database_name == 'test-db'
        assert response.operation == 'delete'  # Default value
        assert len(response.content) == 1
        assert response.content[0].text == 'Successfully deleted database'

    def test_get_database_response(self):
        """Test creating a GetDatabaseResponse."""
        response = GetDatabaseResponse(
            isError=False,
            database_name='test-db',
            description='Test database',
            location_uri='s3://test-bucket/',
            parameters={'key1': 'value1'},
            creation_time='2023-01-01T00:00:00Z',
            catalog_id='123456789012',
            content=[TextContent(type='text', text='Successfully retrieved database')],
        )
        assert response.isError is False
        assert response.database_name == 'test-db'
        assert response.description == 'Test database'
        assert response.location_uri == 's3://test-bucket/'
        assert response.parameters == {'key1': 'value1'}
        assert response.creation_time == '2023-01-01T00:00:00Z'
        assert response.catalog_id == '123456789012'
        assert response.operation == 'get'  # Default value
        assert len(response.content) == 1
        assert response.content[0].text == 'Successfully retrieved database'

    def test_list_databases_response(self):
        """Test creating a ListDatabasesResponse."""
        db1 = DatabaseSummary(name='db1', description='Database 1')
        db2 = DatabaseSummary(name='db2', description='Database 2')

        response = ListDatabasesResponse(
            isError=False,
            databases=[db1, db2],
            count=2,
            catalog_id='123456789012',
            content=[TextContent(type='text', text='Successfully listed databases')],
        )
        assert response.isError is False
        assert len(response.databases) == 2
        assert response.databases[0].name == 'db1'
        assert response.databases[1].name == 'db2'
        assert response.count == 2
        assert response.catalog_id == '123456789012'
        assert response.operation == 'list'  # Default value
        assert len(response.content) == 1
        assert response.content[0].text == 'Successfully listed databases'

    def test_update_database_response(self):
        """Test creating an UpdateDatabaseResponse."""
        response = UpdateDatabaseResponse(
            isError=False,
            database_name='test-db',
            content=[TextContent(type='text', text='Successfully updated database')],
        )
        assert response.isError is False
        assert response.database_name == 'test-db'
        assert response.operation == 'update'  # Default value
        assert len(response.content) == 1
        assert response.content[0].text == 'Successfully updated database'


class TestTableResponseModels:
    """Tests for the table response models."""

    def test_create_table_response(self):
        """Test creating a CreateTableResponse."""
        response = CreateTableResponse(
            isError=False,
            database_name='test-db',
            table_name='test-table',
            content=[TextContent(type='text', text='Successfully created table')],
        )
        assert response.isError is False
        assert response.database_name == 'test-db'
        assert response.table_name == 'test-table'
        assert response.operation == 'create'  # Default value
        assert len(response.content) == 1
        assert response.content[0].text == 'Successfully created table'

    def test_delete_table_response(self):
        """Test creating a DeleteTableResponse."""
        response = DeleteTableResponse(
            isError=False,
            database_name='test-db',
            table_name='test-table',
            content=[TextContent(type='text', text='Successfully deleted table')],
        )
        assert response.isError is False
        assert response.database_name == 'test-db'
        assert response.table_name == 'test-table'
        assert response.operation == 'delete'  # Default value
        assert len(response.content) == 1
        assert response.content[0].text == 'Successfully deleted table'

    def test_get_table_response(self):
        """Test creating a GetTableResponse."""
        table_definition = {
            'Name': 'test-table',
            'DatabaseName': 'test-db',
            'StorageDescriptor': {
                'Columns': [{'Name': 'id', 'Type': 'int'}, {'Name': 'name', 'Type': 'string'}]
            },
        }

        response = GetTableResponse(
            isError=False,
            database_name='test-db',
            table_name='test-table',
            table_definition=table_definition,
            creation_time='2023-01-01T00:00:00Z',
            last_access_time='2023-01-02T00:00:00Z',
            content=[TextContent(type='text', text='Successfully retrieved table')],
        )
        assert response.isError is False
        assert response.database_name == 'test-db'
        assert response.table_name == 'test-table'
        assert response.table_definition == table_definition
        assert response.creation_time == '2023-01-01T00:00:00Z'
        assert response.last_access_time == '2023-01-02T00:00:00Z'
        assert response.operation == 'get'  # Default value
        assert len(response.content) == 1
        assert response.content[0].text == 'Successfully retrieved table'

    def test_list_tables_response(self):
        """Test creating a ListTablesResponse."""
        table1 = TableSummary(name='table1', database_name='test-db')
        table2 = TableSummary(name='table2', database_name='test-db')

        response = ListTablesResponse(
            isError=False,
            database_name='test-db',
            tables=[table1, table2],
            count=2,
            content=[TextContent(type='text', text='Successfully listed tables')],
        )
        assert response.isError is False
        assert response.database_name == 'test-db'
        assert len(response.tables) == 2
        assert response.tables[0].name == 'table1'
        assert response.tables[1].name == 'table2'
        assert response.count == 2
        assert response.operation == 'list'  # Default value
        assert len(response.content) == 1
        assert response.content[0].text == 'Successfully listed tables'

    def test_update_table_response(self):
        """Test creating an UpdateTableResponse."""
        response = UpdateTableResponse(
            isError=False,
            database_name='test-db',
            table_name='test-table',
            content=[TextContent(type='text', text='Successfully updated table')],
        )
        assert response.isError is False
        assert response.database_name == 'test-db'
        assert response.table_name == 'test-table'
        assert response.operation == 'update'  # Default value
        assert len(response.content) == 1
        assert response.content[0].text == 'Successfully updated table'

    def test_search_tables_response(self):
        """Test creating a SearchTablesResponse."""
        table1 = TableSummary(name='test_table1', database_name='db1')
        table2 = TableSummary(name='test_table2', database_name='db2')

        response = SearchTablesResponse(
            isError=False,
            tables=[table1, table2],
            search_text='test',
            count=2,
            content=[TextContent(type='text', text='Successfully searched tables')],
        )
        assert response.isError is False
        assert len(response.tables) == 2
        assert response.tables[0].name == 'test_table1'
        assert response.tables[1].name == 'test_table2'
        assert response.search_text == 'test'
        assert response.count == 2
        assert response.operation == 'search'  # Default value
        assert len(response.content) == 1
        assert response.content[0].text == 'Successfully searched tables'


class TestConnectionResponseModels:
    """Tests for the connection response models."""

    def test_create_connection_response(self):
        """Test creating a CreateConnectionResponse."""
        response = CreateConnectionResponse(
            isError=False,
            connection_name='test-conn',
            catalog_id='123456789012',
            content=[TextContent(type='text', text='Successfully created connection')],
        )
        assert response.isError is False
        assert response.connection_name == 'test-conn'
        assert response.catalog_id == '123456789012'
        assert response.operation == 'create'  # Default value
        assert len(response.content) == 1
        assert response.content[0].text == 'Successfully created connection'

    def test_delete_connection_response(self):
        """Test creating a DeleteConnectionResponse."""
        response = DeleteConnectionResponse(
            isError=False,
            connection_name='test-conn',
            catalog_id='123456789012',
            content=[TextContent(type='text', text='Successfully deleted connection')],
        )
        assert response.isError is False
        assert response.connection_name == 'test-conn'
        assert response.catalog_id == '123456789012'
        assert response.operation == 'delete'  # Default value
        assert len(response.content) == 1
        assert response.content[0].text == 'Successfully deleted connection'

    def test_get_connection_response(self):
        """Test creating a GetConnectionResponse."""
        response = GetConnectionResponse(
            isError=False,
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
            content=[TextContent(type='text', text='Successfully retrieved connection')],
        )
        assert response.isError is False
        assert response.connection_name == 'test-conn'
        assert response.connection_type == 'JDBC'
        assert (
            response.connection_properties['JDBC_CONNECTION_URL']
            == 'jdbc:mysql://localhost:3306/test'
        )
        assert response.connection_properties['USERNAME'] == 'test-user'
        assert response.physical_connection_requirements['AvailabilityZone'] == 'us-east-1a'
        assert response.creation_time == '2023-01-01T00:00:00Z'
        assert response.last_updated_time == '2023-01-02T00:00:00Z'
        assert response.last_updated_by == 'test-user'
        assert response.status == 'READY'
        assert response.status_reason == 'Connection is ready'
        assert response.last_connection_validation_time == '2023-01-03T00:00:00Z'
        assert response.catalog_id == '123456789012'
        assert response.operation == 'get'  # Default value
        assert len(response.content) == 1
        assert response.content[0].text == 'Successfully retrieved connection'


class TestPartitionResponseModels:
    """Tests for the partition response models."""

    def test_create_partition_response(self):
        """Test creating a CreatePartitionResponse."""
        response = CreatePartitionResponse(
            isError=False,
            database_name='test-db',
            table_name='test-table',
            partition_values=['2023', '01', '01'],
            content=[TextContent(type='text', text='Successfully created partition')],
        )
        assert response.isError is False
        assert response.database_name == 'test-db'
        assert response.table_name == 'test-table'
        assert response.partition_values == ['2023', '01', '01']
        assert response.operation == 'create'  # Default value
        assert len(response.content) == 1
        assert response.content[0].text == 'Successfully created partition'

    def test_get_partition_response(self):
        """Test creating a GetPartitionResponse."""
        partition_definition = {
            'Values': ['2023', '01', '01'],
            'StorageDescriptor': {
                'Location': 's3://test-bucket/test-db/test-table/year=2023/month=01/day=01/'
            },
            'Parameters': {'key1': 'value1'},
        }

        response = GetPartitionResponse(
            isError=False,
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
            content=[TextContent(type='text', text='Successfully retrieved partition')],
        )
        assert response.isError is False
        assert response.database_name == 'test-db'
        assert response.table_name == 'test-table'
        assert response.partition_values == ['2023', '01', '01']
        assert response.partition_definition == partition_definition
        assert response.creation_time == '2023-01-01T00:00:00Z'
        assert response.last_access_time == '2023-01-02T00:00:00Z'
        assert (
            response.storage_descriptor['Location']
            == 's3://test-bucket/test-db/test-table/year=2023/month=01/day=01/'
        )
        assert response.parameters == {'key1': 'value1'}
        assert response.operation == 'get'  # Default value
        assert len(response.content) == 1
        assert response.content[0].text == 'Successfully retrieved partition'


class TestCatalogResponseModels:
    """Tests for the catalog response models."""

    def test_create_catalog_response(self):
        """Test creating a CreateCatalogResponse."""
        response = CreateCatalogResponse(
            isError=False,
            catalog_id='test-catalog',
            content=[TextContent(type='text', text='Successfully created catalog')],
        )
        assert response.isError is False
        assert response.catalog_id == 'test-catalog'
        assert response.operation == 'create'  # Default value
        assert len(response.content) == 1
        assert response.content[0].text == 'Successfully created catalog'

    def test_get_catalog_response(self):
        """Test creating a GetCatalogResponse."""
        catalog_definition = {
            'Name': 'Test Catalog',
            'Description': 'Test catalog description',
            'Parameters': {'key1': 'value1'},
        }

        response = GetCatalogResponse(
            isError=False,
            catalog_id='test-catalog',
            catalog_definition=catalog_definition,
            name='Test Catalog',
            description='Test catalog description',
            parameters={'key1': 'value1'},
            create_time='2023-01-01T00:00:00Z',
            update_time='2023-01-02T00:00:00Z',
            content=[TextContent(type='text', text='Successfully retrieved catalog')],
        )
        assert response.isError is False
        assert response.catalog_id == 'test-catalog'
        assert response.catalog_definition == catalog_definition
        assert response.name == 'Test Catalog'
        assert response.description == 'Test catalog description'
        assert response.parameters == {'key1': 'value1'}
        assert response.create_time == '2023-01-01T00:00:00Z'
        assert response.update_time == '2023-01-02T00:00:00Z'
        assert response.operation == 'get'  # Default value
        assert len(response.content) == 1
        assert response.content[0].text == 'Successfully retrieved catalog'
