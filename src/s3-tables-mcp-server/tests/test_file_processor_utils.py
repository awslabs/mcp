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

"""Tests for file processor utility functions."""

import pyarrow as pa
import pytest
from awslabs.s3_tables_mcp_server.file_processor.utils import (
    convert_column_names_to_snake_case,
    import_file_to_table,
)
from unittest.mock import MagicMock, patch


class TestConvertColumnNamesToSnakeCase:
    """Test cases for convert_column_names_to_snake_case function."""

    def test_basic_schema_conversion(self):
        """Test basic schema conversion."""
        original_schema = pa.schema(
            [
                pa.field('firstName', pa.string()),
                pa.field('lastName', pa.string()),
                pa.field('customerID', pa.int64()),
            ]
        )

        converted_schema = convert_column_names_to_snake_case(original_schema)

        expected_names = ['first_name', 'last_name', 'customer_id']
        assert converted_schema.names == expected_names

        # Verify field types are preserved
        assert converted_schema.field('first_name').type == pa.string()
        assert converted_schema.field('last_name').type == pa.string()
        assert converted_schema.field('customer_id').type == pa.int64()

    def test_duplicate_detection(self):
        """Test duplicate column name detection after conversion."""
        # These will both convert to 'first_name'
        schema_with_duplicates = pa.schema(
            [
                pa.field('firstName', pa.string()),
                pa.field('first_name', pa.string()),
                pa.field('First Name', pa.string()),
            ]
        )

        with pytest.raises(ValueError) as exc_info:
            convert_column_names_to_snake_case(schema_with_duplicates)

        error_message = str(exc_info.value)
        assert 'Duplicate column names after case conversion' in error_message
        assert str(schema_with_duplicates.names) in error_message
        assert "['first_name', 'first_name', 'first name']" in error_message

    def test_complex_schema_conversion(self):
        """Test conversion with complex column names."""
        original_schema = pa.schema(
            [
                pa.field('Product Price-USD', pa.float64()),
                pa.field('Customer@Email', pa.string()),
                pa.field('XMLHttpRequestID', pa.int64()),
                pa.field('1stColumn', pa.string()),
            ]
        )

        converted_schema = convert_column_names_to_snake_case(original_schema)

        expected_names = [
            'product price_usd',
            'customer@email',
            'xml_http_request_id',
            '1st_column',
        ]
        assert converted_schema.names == expected_names

    def test_metadata_preservation(self):
        """Test that field and schema metadata is preserved."""
        field_metadata = {'description': 'Customer first name'}
        schema_metadata = {'version': '1.0'}

        original_schema = pa.schema(
            [
                pa.field('firstName', pa.string(), metadata=field_metadata),
            ],
            metadata=schema_metadata,
        )

        converted_schema = convert_column_names_to_snake_case(original_schema)

        # PyArrow stores metadata as bytes, so we need to compare appropriately
        assert converted_schema.metadata == original_schema.metadata
        assert (
            converted_schema.field('first_name').metadata
            == original_schema.field('firstName').metadata
        )

    def test_nullable_preservation(self):
        """Test that nullable property is preserved."""
        original_schema = pa.schema(
            [
                pa.field('firstName', pa.string(), nullable=True),
                pa.field('lastName', pa.string(), nullable=False),
            ]
        )

        converted_schema = convert_column_names_to_snake_case(original_schema)

        assert converted_schema.field('first_name').nullable is True
        assert converted_schema.field('last_name').nullable is False

    def test_duplicate_detection_detailed_error_messages(self):
        """Test detailed error messages for duplicate column names."""
        # Test case 1: CamelCase and snake_case collision
        schema1 = pa.schema(
            [
                pa.field('firstName', pa.string()),
                pa.field('first_name', pa.string()),
            ]
        )

        with pytest.raises(ValueError) as exc_info:
            convert_column_names_to_snake_case(schema1)

        error_message = str(exc_info.value)
        assert 'Duplicate column names after case conversion' in error_message
        assert str(schema1.names) in error_message
        assert "['first_name', 'first_name']" in error_message

        # Test case 2: Multiple variations converting to same name
        schema2 = pa.schema(
            [
                pa.field('CustomerID', pa.string()),
                pa.field('customer_id', pa.string()),
                pa.field('Customer ID', pa.string()),
            ]
        )

        with pytest.raises(ValueError) as exc_info:
            convert_column_names_to_snake_case(schema2)

        error_message = str(exc_info.value)
        assert 'Duplicate column names after case conversion' in error_message
        assert str(schema2.names) in error_message
        assert "['customer_id', 'customer_id', 'customer id']" in error_message

        # Test case 3: Multiple duplicate groups
        schema3 = pa.schema(
            [
                pa.field('firstName', pa.string()),
                pa.field('first_name', pa.string()),
                pa.field('lastName', pa.string()),
                pa.field('last_name', pa.string()),
            ]
        )

        with pytest.raises(ValueError) as exc_info:
            convert_column_names_to_snake_case(schema3)

        error_message = str(exc_info.value)
        assert 'Duplicate column names after case conversion' in error_message
        assert str(schema3.names) in error_message
        assert "['first_name', 'first_name', 'last_name', 'last_name']" in error_message

    def test_empty_schema(self):
        """Test handling of empty schema."""
        empty_schema = pa.schema([])
        converted_schema = convert_column_names_to_snake_case(empty_schema)
        assert converted_schema.names == []
        assert len(converted_schema) == 0

    def test_single_column_schema(self):
        """Test handling of single column schema."""
        single_schema = pa.schema([pa.field('FirstName', pa.string())])
        converted_schema = convert_column_names_to_snake_case(single_schema)
        assert converted_schema.names == ['first_name']

    def test_all_data_types_preservation(self):
        """Test that all PyArrow data types are preserved during conversion."""
        original_schema = pa.schema(
            [
                pa.field('StringField', pa.string()),
                pa.field('IntField', pa.int64()),
                pa.field('FloatField', pa.float64()),
                pa.field('BoolField', pa.bool_()),
                pa.field('DateField', pa.date32()),
                pa.field('TimestampField', pa.timestamp('us')),
                pa.field('ListField', pa.list_(pa.int32())),
                pa.field('StructField', pa.struct([('subfield', pa.string())])),
            ]
        )

        converted_schema = convert_column_names_to_snake_case(original_schema)

        expected_names = [
            'string_field',
            'int_field',
            'float_field',
            'bool_field',
            'date_field',
            'timestamp_field',
            'list_field',
            'struct_field',
        ]
        assert converted_schema.names == expected_names

        # Verify all types are preserved
        assert converted_schema.field('string_field').type == pa.string()
        assert converted_schema.field('int_field').type == pa.int64()
        assert converted_schema.field('float_field').type == pa.float64()
        assert converted_schema.field('bool_field').type == pa.bool_()
        assert converted_schema.field('date_field').type == pa.date32()
        assert converted_schema.field('timestamp_field').type == pa.timestamp('us')
        assert converted_schema.field('list_field').type == pa.list_(pa.int32())
        assert converted_schema.field('struct_field').type == pa.struct(
            [('subfield', pa.string())]
        )

    def test_edge_case_column_names(self):
        """Test edge case column names that might cause issues."""
        # Test individual edge cases that don't create duplicates
        individual_cases = [
            ('', ''),
            ('_', '_'),
            ('___', '___'),
            ('123', '123'),
            ('!@#$%', '!@#$%'),
        ]

        for original, expected in individual_cases:
            schema = pa.schema([pa.field(original, pa.string())])
            converted_schema = convert_column_names_to_snake_case(schema)
            assert converted_schema.names == [expected], (
                f"Failed for '{original}' -> expected '{expected}', got '{converted_schema.names[0]}'"
            )

    def test_edge_case_column_names_with_duplicates(self):
        """Test that edge case column names properly trigger duplicate detection."""
        # These edge cases will all convert to '_column', which should trigger duplicate detection
        edge_case_schema = pa.schema(
            [
                pa.field('_', pa.string()),
                pa.field('_', pa.string()),
                pa.field('!@#$%', pa.string()),
                pa.field('!@#$%', pa.string()),
            ]
        )

        with pytest.raises(ValueError) as exc_info:
            convert_column_names_to_snake_case(edge_case_schema)

        error_message = str(exc_info.value)
        assert 'Duplicate column names after case conversion' in error_message
        assert str(edge_case_schema.names) in error_message
        assert "['_', '_', '!@#$%', '!@#$%']" in error_message


@pytest.mark.asyncio
async def test_import_file_to_table_success():
    """Test successful import_file_to_table when table exists."""
    import pyarrow as pa

    warehouse = 'test-warehouse'
    region = 'us-west-2'
    namespace = 'testns'
    table_name = 'testtable'
    s3_url = 's3://bucket/test.csv'
    uri = 'http://localhost:8181'
    catalog_name = 's3tablescatalog'
    rest_signing_name = 's3tables'
    rest_sigv4_enabled = 'true'
    preserve_case = False

    # Mock S3 client and response
    mock_s3_client = MagicMock()
    mock_body = MagicMock()
    mock_body.read.return_value = b'dummy-bytes'
    mock_s3_client.get_object.return_value = {'Body': mock_body}

    # Mock pyiceberg catalog and table
    mock_table = MagicMock()
    mock_table.metadata.table_uuid = 'fake-uuid'
    mock_table.append = MagicMock()
    mock_catalog = MagicMock()
    mock_catalog.load_table.side_effect = [mock_table]
    mock_catalog.create_table.side_effect = Exception('Should not be called')  # Should not create

    # Use a real pyarrow schema for the dummy table
    initial_schema = pa.schema(
        [
            pa.field('col1', pa.string()),
            pa.field('col2', pa.string()),
        ]
    )

    class DummyPyArrowTable:
        def __init__(self, schema, num_rows=2):
            self.schema = schema
            self.num_rows = num_rows

        def rename_columns(self, names):
            # Return a new DummyPyArrowTable with updated schema
            new_schema = pa.schema([pa.field(name, pa.string()) for name in names])
            return DummyPyArrowTable(new_schema, self.num_rows)

    dummy_pyarrow_table = DummyPyArrowTable(initial_schema)

    def mock_create_pyarrow_table(file_like):
        return dummy_pyarrow_table

    with (
        patch(
            'awslabs.s3_tables_mcp_server.file_processor.utils.pyiceberg_load_catalog',
            return_value=mock_catalog,
        ),
        patch(
            'awslabs.s3_tables_mcp_server.file_processor.utils.get_s3_client',
            return_value=mock_s3_client,
        ),
    ):
        result = await import_file_to_table(
            warehouse=warehouse,
            region=region,
            namespace=namespace,
            table_name=table_name,
            s3_url=s3_url,
            uri=uri,
            create_pyarrow_table=mock_create_pyarrow_table,
            catalog_name=catalog_name,
            rest_signing_name=rest_signing_name,
            rest_sigv4_enabled=rest_sigv4_enabled,
            preserve_case=preserve_case,
        )

    assert result['status'] == 'success'
    assert result['rows_processed'] == 2
    assert result['file_processed'] == 'test.csv'
    assert result['table_created'] is False
    assert result['table_uuid'] == 'fake-uuid'
    assert result['columns'] == ['col_1', 'col_2']


@pytest.mark.asyncio
async def test_import_file_to_table_column_conversion_error():
    """Test import_file_to_table handles column name conversion error."""
    import pyarrow as pa

    warehouse = 'test-warehouse'
    region = 'us-west-2'
    namespace = 'testns'
    table_name = 'testtable'
    s3_url = 's3://bucket/test.csv'
    uri = 'http://localhost:8181'
    catalog_name = 's3tablescatalog'
    rest_signing_name = 's3tables'
    rest_sigv4_enabled = 'true'
    preserve_case = False

    # Mock S3 client and response
    mock_s3_client = MagicMock()
    mock_body = MagicMock()
    mock_body.read.return_value = b'dummy-bytes'
    mock_s3_client.get_object.return_value = {'Body': mock_body}

    # Mock pyiceberg catalog and table
    mock_table = MagicMock()
    mock_table.metadata.table_uuid = 'fake-uuid'
    mock_table.append = MagicMock()
    mock_catalog = MagicMock()
    mock_catalog.load_table.side_effect = [mock_table]
    mock_catalog.create_table.side_effect = Exception('Should not be called')

    # Use a real pyarrow schema for the dummy table
    initial_schema = pa.schema(
        [
            pa.field('col1', pa.string()),
            pa.field('col2', pa.string()),
        ]
    )

    class DummyPyArrowTable:
        def __init__(self, schema, num_rows=2):
            self.schema = schema
            self.num_rows = num_rows

        def rename_columns(self, names):
            new_schema = pa.schema([pa.field(name, pa.string()) for name in names])
            return DummyPyArrowTable(new_schema, self.num_rows)

    dummy_pyarrow_table = DummyPyArrowTable(initial_schema)

    def mock_create_pyarrow_table(file_like):
        return dummy_pyarrow_table

    # Patch convert_column_names_to_snake_case to raise an exception
    with (
        patch(
            'awslabs.s3_tables_mcp_server.file_processor.utils.pyiceberg_load_catalog',
            return_value=mock_catalog,
        ),
        patch(
            'awslabs.s3_tables_mcp_server.file_processor.utils.get_s3_client',
            return_value=mock_s3_client,
        ),
        patch(
            'awslabs.s3_tables_mcp_server.file_processor.utils.convert_column_names_to_snake_case',
            side_effect=Exception('bad columns'),
        ),
    ):
        result = await import_file_to_table(
            warehouse=warehouse,
            region=region,
            namespace=namespace,
            table_name=table_name,
            s3_url=s3_url,
            uri=uri,
            create_pyarrow_table=mock_create_pyarrow_table,
            catalog_name=catalog_name,
            rest_signing_name=rest_signing_name,
            rest_sigv4_enabled=rest_sigv4_enabled,
            preserve_case=preserve_case,
        )

    assert result['status'] == 'error'
    assert 'Column name conversion failed' in result['error']
    assert 'bad columns' in result['error']


@pytest.mark.asyncio
async def test_import_file_to_table_create_table_success():
    """Test import_file_to_table creates a new table successfully."""
    import pyarrow as pa
    from pyiceberg.exceptions import NoSuchTableError

    warehouse = 'test-warehouse'
    region = 'us-west-2'
    namespace = 'testns'
    table_name = 'testtable'
    s3_url = 's3://bucket/test.csv'
    uri = 'http://localhost:8181'
    catalog_name = 's3tablescatalog'
    rest_signing_name = 's3tables'
    rest_sigv4_enabled = 'true'
    preserve_case = False

    # Mock S3 client and response
    mock_s3_client = MagicMock()
    mock_body = MagicMock()
    mock_body.read.return_value = b'dummy-bytes'
    mock_s3_client.get_object.return_value = {'Body': mock_body}

    # Use a real pyarrow schema for the dummy table
    initial_schema = pa.schema(
        [
            pa.field('col1', pa.string()),
            pa.field('col2', pa.string()),
        ]
    )

    class DummyPyArrowTable:
        def __init__(self, schema, num_rows=2):
            self.schema = schema
            self.num_rows = num_rows

        def rename_columns(self, names):
            new_schema = pa.schema([pa.field(name, pa.string()) for name in names])
            return DummyPyArrowTable(new_schema, self.num_rows)

    dummy_pyarrow_table = DummyPyArrowTable(initial_schema)

    def mock_create_pyarrow_table(file_like):
        return dummy_pyarrow_table

    # Mock pyiceberg catalog and table
    mock_table = MagicMock()
    mock_table.metadata.table_uuid = 'fake-uuid'
    mock_table.append = MagicMock()
    mock_catalog = MagicMock()
    # First call to load_table raises NoSuchTableError, then create_table returns mock_table
    mock_catalog.load_table.side_effect = NoSuchTableError('not found')
    mock_catalog.create_table.return_value = mock_table

    with (
        patch(
            'awslabs.s3_tables_mcp_server.file_processor.utils.pyiceberg_load_catalog',
            return_value=mock_catalog,
        ),
        patch(
            'awslabs.s3_tables_mcp_server.file_processor.utils.get_s3_client',
            return_value=mock_s3_client,
        ),
    ):
        result = await import_file_to_table(
            warehouse=warehouse,
            region=region,
            namespace=namespace,
            table_name=table_name,
            s3_url=s3_url,
            uri=uri,
            create_pyarrow_table=mock_create_pyarrow_table,
            catalog_name=catalog_name,
            rest_signing_name=rest_signing_name,
            rest_sigv4_enabled=rest_sigv4_enabled,
            preserve_case=preserve_case,
        )

    assert result['status'] == 'success'
    assert result['rows_processed'] == 2
    assert result['file_processed'] == 'test.csv'
    assert result['table_created'] is True
    assert result['table_uuid'] == 'fake-uuid'
    assert result['columns'] == ['col_1', 'col_2']


@pytest.mark.asyncio
async def test_import_file_to_table_create_table_failure():
    """Test import_file_to_table handles failure to create a new table."""
    import pyarrow as pa
    from pyiceberg.exceptions import NoSuchTableError

    warehouse = 'test-warehouse'
    region = 'us-west-2'
    namespace = 'testns'
    table_name = 'testtable'
    s3_url = 's3://bucket/test.csv'
    uri = 'http://localhost:8181'
    catalog_name = 's3tablescatalog'
    rest_signing_name = 's3tables'
    rest_sigv4_enabled = 'true'
    preserve_case = False

    # Mock S3 client and response
    mock_s3_client = MagicMock()
    mock_body = MagicMock()
    mock_body.read.return_value = b'dummy-bytes'
    mock_s3_client.get_object.return_value = {'Body': mock_body}

    # Use a real pyarrow schema for the dummy table
    initial_schema = pa.schema(
        [
            pa.field('col1', pa.string()),
            pa.field('col2', pa.string()),
        ]
    )

    class DummyPyArrowTable:
        def __init__(self, schema, num_rows=2):
            self.schema = schema
            self.num_rows = num_rows

        def rename_columns(self, names):
            new_schema = pa.schema([pa.field(name, pa.string()) for name in names])
            return DummyPyArrowTable(new_schema, self.num_rows)

    dummy_pyarrow_table = DummyPyArrowTable(initial_schema)

    def mock_create_pyarrow_table(file_like):
        return dummy_pyarrow_table

    # Mock pyiceberg catalog and table
    mock_catalog = MagicMock()
    # First call to load_table raises NoSuchTableError, then create_table raises Exception
    mock_catalog.load_table.side_effect = NoSuchTableError('not found')
    mock_catalog.create_table.side_effect = Exception('create failed')

    with (
        patch(
            'awslabs.s3_tables_mcp_server.file_processor.utils.pyiceberg_load_catalog',
            return_value=mock_catalog,
        ),
        patch(
            'awslabs.s3_tables_mcp_server.file_processor.utils.get_s3_client',
            return_value=mock_s3_client,
        ),
    ):
        result = await import_file_to_table(
            warehouse=warehouse,
            region=region,
            namespace=namespace,
            table_name=table_name,
            s3_url=s3_url,
            uri=uri,
            create_pyarrow_table=mock_create_pyarrow_table,
            catalog_name=catalog_name,
            rest_signing_name=rest_signing_name,
            rest_sigv4_enabled=rest_sigv4_enabled,
            preserve_case=preserve_case,
        )

    assert result['status'] == 'error'
    assert 'Failed to create table' in result['error']
    assert 'create failed' in result['error']


@pytest.mark.asyncio
async def test_import_file_to_table_general_exception():
    """Test import_file_to_table handles a general exception."""
    warehouse = 'test-warehouse'
    region = 'us-west-2'
    namespace = 'testns'
    table_name = 'testtable'
    s3_url = 's3://bucket/test.csv'
    uri = 'http://localhost:8181'
    catalog_name = 's3tablescatalog'
    rest_signing_name = 's3tables'
    rest_sigv4_enabled = 'true'
    preserve_case = False

    # Patch pyiceberg_load_catalog to raise a general exception
    with patch(
        'awslabs.s3_tables_mcp_server.file_processor.utils.pyiceberg_load_catalog',
        side_effect=Exception('general failure'),
    ):
        # create_pyarrow_table is not called, but must be provided
        def dummy_create_pyarrow_table(file_like):
            raise AssertionError('Should not be called')

        result = await import_file_to_table(
            warehouse=warehouse,
            region=region,
            namespace=namespace,
            table_name=table_name,
            s3_url=s3_url,
            uri=uri,
            create_pyarrow_table=dummy_create_pyarrow_table,
            catalog_name=catalog_name,
            rest_signing_name=rest_signing_name,
            rest_sigv4_enabled=rest_sigv4_enabled,
            preserve_case=preserve_case,
        )

    assert result['status'] == 'error'
    assert 'general failure' in result['error']
