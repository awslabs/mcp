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

"""Tests for the file processor module."""

import pytest
import uuid
from awslabs.s3_tables_mcp_server.file_processor import (
    convert_value,
    create_pyarrow_schema_from_iceberg,
    import_csv_to_table,
    preview_csv_structure,
    process_chunk,
    validate_s3_url,
)
from datetime import date, datetime, time
from decimal import Decimal
from pyiceberg.schema import Schema
from pyiceberg.types import (
    BinaryType,
    BooleanType,
    DateType,
    DecimalType,
    DoubleType,
    FixedType,
    FloatType,
    IntegerType,
    ListType,
    LongType,
    MapType,
    NestedField,
    StringType,
    StructType,
    TimestampType,
    TimestamptzType,
    TimeType,
    UUIDType,
)
from unittest.mock import MagicMock, patch


class TestValidateS3Url:
    """Test the validate_s3_url function."""

    def test_valid_s3_url(self):
        """Test that valid S3 URLs are correctly parsed."""
        s3_url = 's3://my-bucket/path/to/file.csv'
        is_valid, error_msg, bucket, key = validate_s3_url(s3_url)

        assert is_valid is True
        assert error_msg is None
        assert bucket == 'my-bucket'
        assert key == 'path/to/file.csv'

    def test_valid_s3_url_with_special_characters(self):
        """Test S3 URL with special characters in key."""
        s3_url = 's3://my-bucket/path/with spaces/and-special_chars/file.csv'
        is_valid, error_msg, bucket, key = validate_s3_url(s3_url)

        assert is_valid is True
        assert error_msg is None
        assert bucket == 'my-bucket'
        assert key == 'path/with spaces/and-special_chars/file.csv'

    def test_invalid_scheme(self):
        """Test URL with invalid scheme."""
        s3_url = 'https://my-bucket/file.csv'
        is_valid, error_msg, bucket, key = validate_s3_url(s3_url)

        assert is_valid is False
        assert error_msg is not None
        assert 'Invalid URL scheme: https' in error_msg
        assert bucket is None
        assert key is None

    def test_missing_bucket(self):
        """Test URL with missing bucket name."""
        s3_url = 's3:///path/to/file.csv'
        is_valid, error_msg, bucket, key = validate_s3_url(s3_url)

        assert is_valid is False
        assert error_msg is not None
        assert 'Missing bucket name' in error_msg
        assert bucket is None
        assert key is None

    def test_missing_key(self):
        """Test URL with missing object key."""
        s3_url = 's3://my-bucket/'
        is_valid, error_msg, bucket, key = validate_s3_url(s3_url)

        assert is_valid is False
        assert error_msg is not None
        assert 'Missing object key' in error_msg
        assert bucket is None
        assert key is None

    def test_url_with_colon_in_key(self):
        """Test that a URL with a colon in the key is parsed correctly."""
        s3_url = 's3://my-bucket/path/to/file.csv:invalid'
        is_valid, error_msg, bucket, key = validate_s3_url(s3_url)

        assert is_valid is True
        assert error_msg is None
        assert bucket == 'my-bucket'
        assert key == 'path/to/file.csv:invalid'


class TestPreviewCsvStructure:
    """Test the preview_csv_structure function."""

    @pytest.fixture
    def mock_s3_client(self):
        """Create a mock S3 client."""
        return MagicMock()

    def test_successful_preview(self, mock_s3_client):
        """Test successful CSV preview."""
        # Mock CSV content
        csv_content = 'id,name,age\n1,John,25\n2,Jane,30'

        mock_response = MagicMock()
        mock_response['Body'].read.return_value = csv_content.encode('utf-8')
        mock_s3_client.get_object.return_value = mock_response

        with patch('awslabs.s3_tables_mcp_server.file_processor.get_s3_client') as mock_get_client:
            mock_get_client.return_value = mock_s3_client

            result = preview_csv_structure('s3://my-bucket/data.csv')

            assert result['headers'] == ['id', 'name', 'age']
            assert result['first_row'] == {'id': '1', 'name': 'John', 'age': '25'}
            assert result['total_columns'] == 3
            assert result['file_name'] == 'data.csv'

            mock_s3_client.get_object.assert_called_once_with(
                Bucket='my-bucket', Key='data.csv', Range='bytes=0-32768'
            )

    def test_preview_with_empty_file(self, mock_s3_client):
        """Test preview of empty CSV file."""
        mock_response = MagicMock()
        mock_response['Body'].read.return_value = ''.encode('utf-8')
        mock_s3_client.get_object.return_value = mock_response

        with patch('awslabs.s3_tables_mcp_server.file_processor.get_s3_client') as mock_get_client:
            mock_get_client.return_value = mock_s3_client

            result = preview_csv_structure('s3://my-bucket/empty.csv')

            assert result['status'] == 'error'
            assert 'File is empty' in result['error']

    def test_preview_with_no_data_rows(self, mock_s3_client):
        """Test preview of CSV with only headers."""
        csv_content = 'id,name,age\n'

        mock_response = MagicMock()
        mock_response['Body'].read.return_value = csv_content.encode('utf-8')
        mock_s3_client.get_object.return_value = mock_response

        with patch('awslabs.s3_tables_mcp_server.file_processor.get_s3_client') as mock_get_client:
            mock_get_client.return_value = mock_s3_client

            result = preview_csv_structure('s3://my-bucket/headers_only.csv')

            assert result['headers'] == ['id', 'name', 'age']
            assert result['first_row'] == {}
            assert result['total_columns'] == 3
            assert result['file_name'] == 'headers_only.csv'

    def test_invalid_s3_url(self):
        """Test preview with invalid S3 URL."""
        result = preview_csv_structure('invalid-url')

        assert result['status'] == 'error'
        assert 'Invalid URL scheme' in result['error']

    def test_non_csv_file(self):
        """Test preview of non-CSV file."""
        result = preview_csv_structure('s3://my-bucket/data.txt')

        assert result['status'] == 'error'
        assert 'is not a CSV file' in result['error']

    def test_s3_client_exception(self, mock_s3_client):
        """Test preview when S3 client raises exception."""
        mock_s3_client.get_object.side_effect = Exception('S3 error')

        with patch('awslabs.s3_tables_mcp_server.file_processor.get_s3_client') as mock_get_client:
            mock_get_client.return_value = mock_s3_client

            result = preview_csv_structure('s3://my-bucket/data.csv')

            assert result['status'] == 'error'
            assert 'S3 error' in result['error']


class TestConvertValue:
    """Test the convert_value function."""

    def test_boolean_type_true(self):
        """Test boolean conversion with true values."""
        assert convert_value('true', BooleanType()) is True
        assert convert_value('1', BooleanType()) is True
        assert convert_value('yes', BooleanType()) is True

    def test_boolean_type_false(self):
        """Test boolean conversion with false values."""
        assert convert_value('false', BooleanType()) is False
        assert convert_value('0', BooleanType()) is False
        assert convert_value('no', BooleanType()) is False

    def test_integer_type(self):
        """Test integer conversion."""
        assert convert_value('123', IntegerType()) == 123
        assert convert_value('-456', IntegerType()) == -456

    def test_long_type(self):
        """Test long conversion."""
        assert convert_value('123456789', LongType()) == 123456789

    def test_float_type(self):
        """Test float conversion."""
        assert convert_value('123.45', FloatType()) == 123.45
        assert convert_value('-67.89', FloatType()) == -67.89

    def test_double_type(self):
        """Test double conversion."""
        assert convert_value('123.456789', DoubleType()) == 123.456789

    def test_decimal_type(self):
        """Test decimal conversion."""
        result = convert_value('123.45', DecimalType(10, 2))
        assert isinstance(result, Decimal)
        assert result == Decimal('123.45')

    def test_date_type(self):
        """Test date conversion."""
        result = convert_value('2023-12-25', DateType())
        assert isinstance(result, date)
        assert result == date(2023, 12, 25)

    def test_time_type(self):
        """Test time conversion."""
        result = convert_value('14:30:45', TimeType())
        assert isinstance(result, time)
        assert result == time(14, 30, 45)

    def test_timestamp_type(self):
        """Test timestamp conversion."""
        result = convert_value('2023-12-25T14:30:45', TimestampType())
        assert isinstance(result, datetime)
        assert result == datetime(2023, 12, 25, 14, 30, 45)

    def test_timestamptz_type(self):
        """Test timestamptz conversion."""
        result = convert_value('2023-12-25T14:30:45', TimestamptzType())
        assert isinstance(result, datetime)

    def test_string_type(self):
        """Test string conversion."""
        assert convert_value('hello world', StringType()) == 'hello world'
        assert convert_value('123', StringType()) == '123'

    def test_uuid_type(self):
        """Test UUID conversion."""
        uuid_str = '550e8400-e29b-41d4-a716-446655440000'
        result = convert_value(uuid_str, UUIDType())
        assert isinstance(result, uuid.UUID)

    def test_binary_type(self):
        """Test binary conversion."""
        hex_str = '48656c6c6f'  # "Hello" in hex
        result = convert_value(hex_str, BinaryType())
        assert isinstance(result, bytes)
        assert result == b'Hello'

    def test_fixed_type(self):
        """Test fixed type conversion."""
        hex_str = '48656c6c6f'  # "Hello" in hex
        result = convert_value(hex_str, FixedType(5))
        assert isinstance(result, bytes)

    def test_list_type(self):
        """Test list type conversion."""
        list_str = '1,2,3,4,5'
        result = convert_value(list_str, ListType(element_id=1, element_type=IntegerType()))
        assert result == [1, 2, 3, 4, 5]

    def test_map_type(self):
        """Test map type conversion."""
        map_str = 'key1:value1,key2:value2'
        result = convert_value(
            map_str, MapType(key_id=1, key_type=StringType(), value_id=2, value_type=StringType())
        )
        assert result == {'key1': 'value1', 'key2': 'value2'}

    def test_struct_type_raises_error(self):
        """Test that struct type raises NotImplementedError."""
        with pytest.raises(NotImplementedError, match='Nested structs need structured input'):
            convert_value('{"field": "value"}', StructType())

    def test_unsupported_type_raises_error(self):
        """Test that unsupported types raise ValueError."""

        class UnsupportedType:
            pass

        with pytest.raises(ValueError, match='Unsupported Iceberg type'):
            convert_value('value', UnsupportedType())

    def test_null_or_empty_values(self):
        """Test handling of null or empty values."""
        assert convert_value(None, StringType()) is None
        assert convert_value('', StringType()) is None
        assert convert_value('', IntegerType()) is None

    def test_conversion_errors(self):
        """Test conversion errors for invalid values."""
        with pytest.raises(ValueError):
            convert_value('not_a_number', IntegerType())

        with pytest.raises(ValueError):
            convert_value('not_a_date', DateType())

        with pytest.raises(ValueError):
            convert_value('not_a_uuid', UUIDType())


class TestCreatePyarrowSchemaFromIceberg:
    """Test the create_pyarrow_schema_from_iceberg function."""

    def test_basic_types(self):
        """Test conversion of basic Iceberg types to PyArrow schema."""
        iceberg_schema = Schema(
            NestedField(1, 'bool_field', BooleanType(), required=True),
            NestedField(2, 'int_field', IntegerType(), required=True),
            NestedField(3, 'long_field', LongType(), required=True),
            NestedField(4, 'float_field', FloatType(), required=True),
            NestedField(5, 'double_field', DoubleType(), required=True),
            NestedField(6, 'string_field', StringType(), required=True),
            NestedField(7, 'date_field', DateType(), required=True),
            NestedField(8, 'time_field', TimeType(), required=True),
            NestedField(9, 'timestamp_field', TimestampType(), required=True),
        )

        pa_schema = create_pyarrow_schema_from_iceberg(iceberg_schema)

        assert len(pa_schema) == 9
        assert pa_schema.field(0).name == 'bool_field'
        assert pa_schema.field(1).name == 'int_field'
        assert pa_schema.field(2).name == 'long_field'

    def test_decimal_type(self):
        """Test decimal type conversion."""
        iceberg_schema = Schema(NestedField(1, 'decimal_field', DecimalType(10, 2), required=True))

        pa_schema = create_pyarrow_schema_from_iceberg(iceberg_schema)

        assert len(pa_schema) == 1
        assert pa_schema.field(0).name == 'decimal_field'

    def test_fixed_type(self):
        """Test fixed type conversion."""
        iceberg_schema = Schema(NestedField(1, 'fixed_field', FixedType(10), required=True))

        pa_schema = create_pyarrow_schema_from_iceberg(iceberg_schema)

        assert len(pa_schema) == 1
        assert pa_schema.field(0).name == 'fixed_field'

    def test_required_and_optional_fields(self):
        """Test handling of required and optional fields."""
        iceberg_schema = Schema(
            NestedField(1, 'required_field', StringType(), required=True),
            NestedField(2, 'optional_field', StringType(), required=False),
        )

        pa_schema = create_pyarrow_schema_from_iceberg(iceberg_schema)

        assert pa_schema.field(0).nullable is False  # Required field
        assert pa_schema.field(1).nullable is True  # Optional field

    def test_invalid_decimal_format(self):
        """Test error handling for invalid decimal format."""
        # Create a mock field with invalid decimal type string
        mock_field = MagicMock()
        mock_field.name = 'invalid_decimal'
        mock_field.field_type.__str__ = lambda self: 'decimal(invalid)'
        mock_field.required = True

        mock_schema = MagicMock()
        mock_schema.fields = [mock_field]

        with pytest.raises(ValueError, match='Invalid decimal type format'):
            create_pyarrow_schema_from_iceberg(mock_schema)

    def test_unsupported_type(self):
        """Test error handling for unsupported types."""
        # Create a mock field with unsupported type
        mock_field = MagicMock()
        mock_field.name = 'unsupported_field'
        mock_field.field_type.__str__ = lambda self: 'unsupported_type'
        mock_field.required = True

        mock_schema = MagicMock()
        mock_schema.fields = [mock_field]

        with pytest.raises(ValueError, match='Unsupported Iceberg type'):
            create_pyarrow_schema_from_iceberg(mock_schema)


class TestProcessChunk:
    """Test the process_chunk function."""

    def test_successful_chunk_processing(self):
        """Test successful processing of a data chunk."""
        # Mock data
        chunk = [{'id': 1, 'name': 'John', 'age': 25}, {'id': 2, 'name': 'Jane', 'age': 30}]

        # Mock table
        mock_table = MagicMock()
        mock_schema = MagicMock()
        mock_table.schema.return_value = mock_schema

        # Mock PyArrow schema and table creation
        with (
            patch(
                'awslabs.s3_tables_mcp_server.file_processor.create_pyarrow_schema_from_iceberg'
            ) as mock_create_schema,
            patch('awslabs.s3_tables_mcp_server.file_processor.pa.Table') as mock_pa_table_class,
        ):
            mock_pa_schema = MagicMock()
            mock_create_schema.return_value = mock_pa_schema

            mock_pa_table = MagicMock()
            mock_pa_table_class.from_pylist.return_value = mock_pa_table

            result = process_chunk(chunk, mock_table, 'Test Chunk')

            assert result['status'] == 'success'
            assert 'Successfully processed 2 rows' in result['message']

            mock_pa_table_class.from_pylist.assert_called_once_with(chunk, schema=mock_pa_schema)
            mock_table.append.assert_called_once_with(mock_pa_table)

    def test_chunk_processing_error(self):
        """Test chunk processing when an error occurs."""
        chunk = [{'id': 1, 'name': 'John'}]
        mock_table = MagicMock()
        mock_table.schema.side_effect = Exception('Schema error')

        result = process_chunk(chunk, mock_table, 'Test Chunk')

        assert result['status'] == 'error'
        assert 'Error inserting test chunk' in result['error']


class TestImportCsvToTable:
    """Test the import_csv_to_table function."""

    @pytest.fixture
    def mock_s3_client(self):
        """Create a mock S3 client."""
        return MagicMock()

    @pytest.fixture
    def mock_catalog(self):
        """Create a mock Iceberg catalog."""
        return MagicMock()

    @pytest.fixture
    def mock_table(self):
        """Create a mock Iceberg table."""
        return MagicMock()

    @pytest.fixture
    def mock_schema(self):
        """Create a mock Iceberg schema."""
        return Schema(
            NestedField(1, 'id', IntegerType(), required=True),
            NestedField(2, 'name', StringType(), required=True),
        )

    @pytest.mark.asyncio
    async def test_successful_import(self, mock_s3_client, mock_catalog, mock_table, mock_schema):
        """Test successful CSV import."""
        csv_content = 'id,name\n1,John\n2,Jane'
        mock_s3_response = MagicMock()
        mock_s3_response['Body'].read.return_value = csv_content.encode('utf-8')
        mock_s3_client.get_object.return_value = mock_s3_response
        mock_table.schema.return_value = mock_schema
        with (
            patch(
                'awslabs.s3_tables_mcp_server.file_processor.get_s3_client'
            ) as mock_get_s3_client,
            patch('awslabs.s3_tables_mcp_server.file_processor.load_catalog') as mock_load_catalog,
            patch(
                'awslabs.s3_tables_mcp_server.file_processor.process_chunk'
            ) as mock_process_chunk,
        ):
            mock_get_s3_client.return_value = mock_s3_client
            mock_load_catalog.return_value = mock_catalog
            mock_catalog.load_table.return_value = mock_table
            mock_process_chunk.return_value = {'status': 'success', 'message': 'Processed chunk'}
            result = await import_csv_to_table(
                warehouse='dummy-warehouse',
                region='us-west-2',
                namespace='test_namespace',
                table_name='test_table',
                s3_url='s3://source-bucket/data.csv',
            )
            assert result['status'] == 'success'
            assert result['rows_processed'] == 2
            assert result['file_processed'] == 'data.csv'
            assert result['csv_headers'] == ['id', 'name']

    @pytest.mark.asyncio
    async def test_invalid_s3_url(self):
        """Test import with invalid S3 URL."""
        result = await import_csv_to_table(
            warehouse='dummy-warehouse',
            region='us-west-2',
            namespace='test_namespace',
            table_name='test_table',
            s3_url='invalid-url',
        )
        assert result['status'] == 'error'
        assert 'Invalid URL scheme' in result['error']

    @pytest.mark.asyncio
    async def test_non_csv_file(self):
        """Test import of non-CSV file."""
        result = await import_csv_to_table(
            warehouse='dummy-warehouse',
            region='us-west-2',
            namespace='test_namespace',
            table_name='test_table',
            s3_url='s3://source-bucket/data.txt',
        )
        assert result['status'] == 'error'
        assert 'is not a CSV file' in result['error']

    @pytest.mark.asyncio
    async def test_csv_missing_required_columns(
        self, mock_s3_client, mock_catalog, mock_table, mock_schema
    ):
        """Test import when CSV is missing required columns."""
        csv_content = 'id\n1\n2'
        mock_s3_response = MagicMock()
        mock_s3_response['Body'].read.return_value = csv_content.encode('utf-8')
        mock_s3_client.get_object.return_value = mock_s3_response
        mock_table.schema.return_value = mock_schema
        with (
            patch(
                'awslabs.s3_tables_mcp_server.file_processor.get_s3_client'
            ) as mock_get_s3_client,
            patch('awslabs.s3_tables_mcp_server.file_processor.load_catalog') as mock_load_catalog,
        ):
            mock_get_s3_client.return_value = mock_s3_client
            mock_load_catalog.return_value = mock_catalog
            mock_catalog.load_table.return_value = mock_table
            result = await import_csv_to_table(
                warehouse='dummy-warehouse',
                region='us-west-2',
                namespace='test_namespace',
                table_name='test_table',
                s3_url='s3://source-bucket/data.csv',
            )
            assert result['status'] == 'error'
            assert 'CSV is missing required columns: name' in result['error']

    @pytest.mark.asyncio
    async def test_csv_no_headers(self, mock_s3_client, mock_catalog, mock_table, mock_schema):
        """Test import when CSV has no headers."""
        csv_content = '1,John\n2,Jane'
        mock_s3_response = MagicMock()
        mock_s3_response['Body'].read.return_value = csv_content.encode('utf-8')
        mock_s3_client.get_object.return_value = mock_s3_response
        mock_table.schema.return_value = mock_schema
        with (
            patch(
                'awslabs.s3_tables_mcp_server.file_processor.get_s3_client'
            ) as mock_get_s3_client,
            patch('awslabs.s3_tables_mcp_server.file_processor.load_catalog') as mock_load_catalog,
            patch(
                'awslabs.s3_tables_mcp_server.file_processor.csv.DictReader'
            ) as mock_dict_reader,
        ):
            mock_get_s3_client.return_value = mock_s3_client
            mock_load_catalog.return_value = mock_catalog
            mock_catalog.load_table.return_value = mock_table
            mock_reader = MagicMock()
            mock_reader.fieldnames = None
            mock_dict_reader.return_value = mock_reader
            result = await import_csv_to_table(
                warehouse='dummy-warehouse',
                region='us-west-2',
                namespace='test_namespace',
                table_name='test_table',
                s3_url='s3://source-bucket/data.csv',
            )
            assert result['status'] == 'error'
            assert 'CSV file has no headers' in result['error']

    @pytest.mark.asyncio
    async def test_required_field_missing_in_row(
        self, mock_s3_client, mock_catalog, mock_table, mock_schema
    ):
        """Test import when a required field is missing in a row."""
        csv_content = 'id,name\n1,John\n2,'
        mock_s3_response = MagicMock()
        mock_s3_response['Body'].read.return_value = csv_content.encode('utf-8')
        mock_s3_client.get_object.return_value = mock_s3_response
        mock_table.schema.return_value = mock_schema
        with (
            patch(
                'awslabs.s3_tables_mcp_server.file_processor.get_s3_client'
            ) as mock_get_s3_client,
            patch('awslabs.s3_tables_mcp_server.file_processor.load_catalog') as mock_load_catalog,
        ):
            mock_get_s3_client.return_value = mock_s3_client
            mock_load_catalog.return_value = mock_catalog
            mock_catalog.load_table.return_value = mock_table
            result = await import_csv_to_table(
                warehouse='dummy-warehouse',
                region='us-west-2',
                namespace='test_namespace',
                table_name='test_table',
                s3_url='s3://source-bucket/data.csv',
            )
            assert result['status'] == 'error'
            assert 'Required field name is missing or empty in row 2' in result['error']

    @pytest.mark.asyncio
    async def test_value_conversion_error(
        self, mock_s3_client, mock_catalog, mock_table, mock_schema
    ):
        """Test import when value conversion fails."""
        csv_content = 'id,name\n1,John\nabc,Jane'
        mock_s3_response = MagicMock()
        mock_s3_response['Body'].read.return_value = csv_content.encode('utf-8')
        mock_s3_client.get_object.return_value = mock_s3_response
        mock_table.schema.return_value = mock_schema
        with (
            patch(
                'awslabs.s3_tables_mcp_server.file_processor.get_s3_client'
            ) as mock_get_s3_client,
            patch('awslabs.s3_tables_mcp_server.file_processor.load_catalog') as mock_load_catalog,
        ):
            mock_get_s3_client.return_value = mock_s3_client
            mock_load_catalog.return_value = mock_catalog
            mock_catalog.load_table.return_value = mock_table
            result = await import_csv_to_table(
                warehouse='dummy-warehouse',
                region='us-west-2',
                namespace='test_namespace',
                table_name='test_table',
                s3_url='s3://source-bucket/data.csv',
            )
            assert result['status'] == 'error'
            assert 'Error converting value for field id in row 2' in result['error']

    @pytest.mark.asyncio
    async def test_chunk_processing_error(
        self, mock_s3_client, mock_catalog, mock_table, mock_schema
    ):
        """Test import when chunk processing fails."""
        csv_content = 'id,name\n1,John\n2,Jane\n3,Bob\n4,Alice\n5,Charlie'
        mock_s3_response = MagicMock()
        mock_s3_response['Body'].read.return_value = csv_content.encode('utf-8')
        mock_s3_client.get_object.return_value = mock_s3_response
        mock_table.schema.return_value = mock_schema
        with (
            patch(
                'awslabs.s3_tables_mcp_server.file_processor.get_s3_client'
            ) as mock_get_s3_client,
            patch('awslabs.s3_tables_mcp_server.file_processor.load_catalog') as mock_load_catalog,
            patch(
                'awslabs.s3_tables_mcp_server.file_processor.process_chunk'
            ) as mock_process_chunk,
        ):
            mock_get_s3_client.return_value = mock_s3_client
            mock_load_catalog.return_value = mock_catalog
            mock_catalog.load_table.return_value = mock_table
            mock_process_chunk.return_value = {
                'status': 'error',
                'error': 'Chunk processing failed',
            }
            result = await import_csv_to_table(
                warehouse='dummy-warehouse',
                region='us-west-2',
                namespace='test_namespace',
                table_name='test_table',
                s3_url='s3://source-bucket/data.csv',
            )
            assert result['status'] == 'error'
            assert 'Chunk processing failed' in result['error']

    @pytest.mark.asyncio
    async def test_custom_region_parameter(
        self, mock_s3_client, mock_catalog, mock_table, mock_schema
    ):
        """Test import with custom region parameter."""
        csv_content = 'id,name\n1,John'
        mock_s3_response = MagicMock()
        mock_s3_response['Body'].read.return_value = csv_content.encode('utf-8')
        mock_s3_client.get_object.return_value = mock_s3_response
        mock_table.schema.return_value = mock_schema
        with (
            patch(
                'awslabs.s3_tables_mcp_server.file_processor.get_s3_client'
            ) as mock_get_s3_client,
            patch('awslabs.s3_tables_mcp_server.file_processor.load_catalog') as mock_load_catalog,
            patch(
                'awslabs.s3_tables_mcp_server.file_processor.process_chunk'
            ) as mock_process_chunk,
        ):
            mock_get_s3_client.return_value = mock_s3_client
            mock_load_catalog.return_value = mock_catalog
            mock_catalog.load_table.return_value = mock_table
            mock_process_chunk.return_value = {'status': 'success', 'message': 'Processed chunk'}
            result = await import_csv_to_table(
                warehouse='dummy-warehouse',
                region='us-east-1',
                namespace='test_namespace',
                table_name='test_table',
                s3_url='s3://source-bucket/data.csv',
            )
            assert result['status'] == 'success'
            mock_load_catalog.assert_called_once()
            call_args = mock_load_catalog.call_args[1]
            assert call_args['rest.signing-region'] == 'us-east-1'
