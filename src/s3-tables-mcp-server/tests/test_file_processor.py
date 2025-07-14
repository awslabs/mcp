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

"""Unit tests for file_processor.py."""

import pyarrow as pa
import pytest
import uuid
from awslabs.s3_tables_mcp_server import file_processor
from datetime import date, datetime, time
from decimal import Decimal
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
    StringType,
    TimestampType,
    TimestamptzType,
    TimeType,
    UUIDType,
)
from unittest.mock import MagicMock, patch


class TestValidateS3Url:
    """Unit tests for S3 URL validation logic in file_processor."""

    def test_valid_s3_url(self):
        """Test that a valid S3 URL is correctly parsed and validated."""
        url = 's3://my-bucket/my/key.csv'
        valid, error, bucket, key = file_processor.validate_s3_url(url)
        assert valid is True
        assert error is None
        assert bucket == 'my-bucket'
        assert key == 'my/key.csv'

    @pytest.mark.parametrize(
        'url,expected_error',
        [
            ('http://bucket/key', "Invalid URL scheme: http. Must be 's3://'"),
            ('s3://', 'Missing bucket name in S3 URL'),
            ('s3://bucket', 'Missing object key in S3 URL'),
            ('not-a-url', "Invalid URL scheme: . Must be 's3://'"),
        ],
    )
    def test_invalid_s3_url(self, url, expected_error):
        """Test that invalid S3 URLs are correctly identified and return appropriate errors."""
        valid, error, bucket, key = file_processor.validate_s3_url(url)
        assert valid is False
        assert expected_error in error
        assert bucket is None
        assert key is None

    def test_validate_s3_url_exception(self):
        """Test that an exception in urlparse is handled gracefully in validate_s3_url."""
        # Passing a non-string (e.g., int) will cause urlparse to raise an exception
        value = 12345
        valid, error, bucket, key = file_processor.validate_s3_url(value)  # type: ignore[arg-type]
        assert valid is False
        assert error is not None
        assert 'Error parsing S3 URL' in error
        assert bucket is None
        assert key is None


class TestPreviewCsvStructure:
    """Unit tests for previewing CSV structure from S3 in file_processor."""

    @patch('awslabs.s3_tables_mcp_server.file_processor.get_s3_client')
    def test_preview_csv_structure_success(self, mock_get_s3_client):
        """Test successful preview of a CSV file structure from S3."""
        s3_url = 's3://bucket/test.csv'
        csv_content = 'col1,col2\nval1,val2\n'
        mock_s3 = MagicMock()
        mock_s3.get_object.return_value = {
            'Body': MagicMock(read=MagicMock(return_value=csv_content.encode('utf-8')))
        }
        mock_get_s3_client.return_value = mock_s3
        result = file_processor.preview_csv_structure(s3_url)
        assert result['headers'] == ['col1', 'col2']
        assert result['first_row'] == {'col1': 'val1', 'col2': 'val2'}
        assert result['total_columns'] == 2
        assert result['file_name'] == 'test.csv'

    def test_preview_csv_structure_invalid_url(self):
        """Test that an invalid S3 URL returns an error when previewing CSV structure."""
        s3_url = 'not-a-url'
        result = file_processor.preview_csv_structure(s3_url)
        assert result['status'] == 'error'
        assert 'Invalid URL scheme' in result['error']

    def test_preview_csv_structure_non_csv(self):
        """Test that a non-CSV file returns an error when previewing CSV structure."""
        s3_url = 's3://bucket/file.txt'
        result = file_processor.preview_csv_structure(s3_url)
        assert result['status'] == 'error'
        assert 'is not a CSV file' in result['error']

    @patch('awslabs.s3_tables_mcp_server.file_processor.get_s3_client')
    def test_preview_csv_structure_s3_error(self, mock_get_s3_client):
        """Test that an S3 error is handled and returns an error when previewing CSV structure."""
        s3_url = 's3://bucket/test.csv'
        mock_s3 = MagicMock()
        mock_s3.get_object.side_effect = Exception('S3 error')
        mock_get_s3_client.return_value = mock_s3
        result = file_processor.preview_csv_structure(s3_url)
        assert result['status'] == 'error'
        assert 'S3 error' in result['error']

    @patch('awslabs.s3_tables_mcp_server.file_processor.get_s3_client')
    def test_preview_csv_structure_empty_file(self, mock_get_s3_client):
        """Test that an empty CSV file returns an error when previewing CSV structure."""
        s3_url = 's3://bucket/test.csv'
        mock_s3 = MagicMock()
        mock_s3.get_object.return_value = {
            'Body': MagicMock(read=MagicMock(return_value=''.encode('utf-8')))
        }
        mock_get_s3_client.return_value = mock_s3
        result = file_processor.preview_csv_structure(s3_url)
        assert result['status'] == 'error'
        assert 'File is empty' in result['error']

    @patch('awslabs.s3_tables_mcp_server.file_processor.validate_s3_url')
    def test_preview_csv_structure_bucket_or_key_none(self, mock_validate_s3_url):
        """Test that preview_csv_structure returns an error if bucket or key is None after validation."""
        mock_validate_s3_url.return_value = (True, None, None, None)
        s3_url = 's3://bucket/key.csv'
        result = file_processor.preview_csv_structure(s3_url)
        assert result['status'] == 'error'
        assert 'bucket or key is None' in result['error']


class TestConvertValue:
    """Unit tests for value conversion logic in file_processor."""

    def test_boolean_type(self):
        """Test conversion of various string representations to boolean values."""
        assert file_processor.convert_value('true', BooleanType()) is True
        assert file_processor.convert_value('False', BooleanType()) is False
        assert file_processor.convert_value('1', BooleanType()) is True
        assert file_processor.convert_value('0', BooleanType()) is False
        assert file_processor.convert_value('', BooleanType()) is None
        assert file_processor.convert_value(None, BooleanType()) is None

    def test_integer_types(self):
        """Test conversion of string values to integer and long types."""
        assert file_processor.convert_value('42', IntegerType()) == 42
        assert file_processor.convert_value('123', LongType()) == 123
        assert file_processor.convert_value('', IntegerType()) is None

    def test_float_types(self):
        """Test conversion of string values to float and double types."""
        assert file_processor.convert_value('3.14', FloatType()) == 3.14
        assert file_processor.convert_value('2.718', DoubleType()) == 2.718
        assert file_processor.convert_value('', DoubleType()) is None

    def test_decimal_type(self):
        """Test conversion of string values to decimal type."""
        assert file_processor.convert_value('1.23', DecimalType(10, 2)) == Decimal('1.23')
        assert file_processor.convert_value('', DecimalType(10, 2)) is None

    def test_date_time_types(self):
        """Test conversion of string values to date, time, timestamp, and timestamptz types."""
        assert file_processor.convert_value('2023-01-01', DateType()) == date(2023, 1, 1)
        assert file_processor.convert_value('12:34:56', TimeType()) == time(12, 34, 56)
        assert file_processor.convert_value(
            '2023-01-01T12:34:56', TimestampType()
        ) == datetime.fromisoformat('2023-01-01T12:34:56')
        assert file_processor.convert_value(
            '2023-01-01T12:34:56', TimestamptzType()
        ) == datetime.fromisoformat('2023-01-01T12:34:56')

    def test_string_and_uuid(self):
        """Test conversion of string values to string and UUID types."""
        assert file_processor.convert_value('hello', StringType()) == 'hello'
        u = str(uuid.uuid4())
        assert file_processor.convert_value(u, UUIDType()) == uuid.UUID(u)

    def test_binary_and_fixed(self):
        """Test conversion of hex string values to binary and fixed types."""
        hexstr = '68656c6c6f'  # 'hello' in hex
        assert file_processor.convert_value(hexstr, BinaryType()) == b'hello'
        assert file_processor.convert_value(hexstr, FixedType(5)) == b'hello'

    def test_list_type(self):
        """Test conversion of comma-separated string to a list of integers."""
        # ListType(element_id, element_type, element_required=True)
        lt = ListType(element_id=1, element_type=IntegerType(), element_required=True)
        assert file_processor.convert_value('1,2,3', lt) == [1, 2, 3]

    def test_map_type(self):
        """Test conversion of colon-separated key-value pairs to a map of string to integer."""
        # MapType(key_id, key_type, value_id, value_type, value_required=True)
        mt = MapType(
            key_id=1,
            key_type=StringType(),
            value_id=2,
            value_type=IntegerType(),
            value_required=True,
        )
        assert file_processor.convert_value('a:1,b:2', mt) == {'a': 1, 'b': 2}

    def test_unsupported_type(self):
        """Test that an unsupported type raises a ValueError during conversion."""

        class DummyType:
            pass

        with pytest.raises(ValueError):
            file_processor.convert_value('x', DummyType())


class TestCreatePyarrowSchemaFromIceberg:
    """Unit tests for creating pyarrow schema from Iceberg schema in file_processor."""

    class DummyField:
        def __init__(self, name, field_type, required=True):
            """Initialize DummyField with name, field_type, and required flag."""
            self.name = name
            self.field_type = field_type
            self.required = required

    class DummySchema:
        def __init__(self, fields):
            """Initialize DummySchema with a list of fields."""
            self.fields = fields

    def test_basic_types(self):
        """Test creation of a pyarrow schema from Iceberg schema with basic types."""
        fields = [
            self.DummyField('a', IntegerType()),
            self.DummyField('b', StringType()),
            self.DummyField('c', BooleanType(), required=False),
        ]
        schema = self.DummySchema(fields)
        pa_schema = file_processor.create_pyarrow_schema_from_iceberg(schema)
        assert pa_schema.field('a').type == pa.int32()
        assert pa_schema.field('b').type == pa.string()
        assert pa_schema.field('c').type == pa.bool_()
        assert pa_schema.field('c').nullable is True

    def test_decimal_type(self):
        """Test creation of a pyarrow schema from Iceberg schema with a decimal type."""
        fields = [self.DummyField('d', DecimalType(10, 2))]
        schema = self.DummySchema(fields)
        pa_schema = file_processor.create_pyarrow_schema_from_iceberg(schema)
        assert pa.types.is_decimal(pa_schema.field('d').type)


class TestProcessChunk:
    """Unit tests for processing data chunks and appending to tables in file_processor."""

    class DummyTable:
        def __init__(self):
            """Initialize DummyTable with an empty appended list and schema."""
            self.appended = []

            class DummySchema:
                def __init__(self):
                    """Initialize DummySchema with test fields."""
                    self.fields = [
                        TestProcessChunk.DummyField('a', IntegerType()),
                        TestProcessChunk.DummyField('b', StringType()),
                    ]

                def __call__(self):
                    """Return self when called (for schema compatibility)."""
                    return self

            self.schema = DummySchema()

        def schema(self):
            """Return the schema for the DummyTable."""
            return self.schema

        def append(self, table_data):
            """Append table_data to the appended list."""
            self.appended.append(table_data)

    class DummyField:
        def __init__(self, name, field_type, required=True):
            """Initialize DummyField with name, field_type, and required flag."""
            self.name = name
            self.field_type = field_type
            self.required = required

    def test_process_chunk_success(self):
        """Test successful processing and appending of a chunk to the table."""
        table = self.DummyTable()
        chunk = [{'a': 1, 'b': 'x'}, {'a': 2, 'b': 'y'}]
        result = file_processor.process_chunk(chunk, table)
        assert result['status'] == 'success'
        assert len(table.appended) == 1

    def test_process_chunk_error(self):
        """Test that an error during table append is handled and returns an error status."""

        class BadTable(self.DummyTable):
            def append(self, table_data):
                raise Exception('append failed')

        table = BadTable()
        chunk = [{'a': 1, 'b': 'x'}]
        result = file_processor.process_chunk(chunk, table)
        assert result['status'] == 'error'
        assert 'append failed' in result['error']


class TestImportCsvToTable:
    """Unit tests for import_csv_to_table in file_processor."""

    @pytest.mark.asyncio
    @patch('awslabs.s3_tables_mcp_server.file_processor.get_s3_client')
    @patch('awslabs.s3_tables_mcp_server.file_processor.pyiceberg_load_catalog')
    async def test_import_csv_to_table_success(self, mock_load_catalog, mock_get_s3_client):
        """Test successful import of a valid CSV file into a table."""
        # Arrange
        warehouse = 's3://warehouse/'
        region = 'us-west-2'
        namespace = 'ns'
        table_name = 'tbl'
        s3_url = 's3://bucket/file.csv'
        csv_content = 'id,name\n1,Alice\n2,Bob\n'
        # Mock S3
        mock_s3 = MagicMock()
        mock_s3.get_object.return_value = {
            'Body': MagicMock(read=MagicMock(return_value=csv_content.encode('utf-8')))
        }
        mock_get_s3_client.return_value = mock_s3

        # Mock Iceberg table
        class DummyField:
            def __init__(self, name, field_type, required=True):
                self.name = name
                self.field_type = field_type
                self.required = required

        class DummySchema:
            def __init__(self):
                self.fields = [DummyField('id', IntegerType()), DummyField('name', StringType())]

        class DummyTable:
            def __init__(self):
                self.appended = []

            def schema(self):
                return DummySchema()

            def append(self, table_data):
                self.appended.append(table_data)

        class DummyCatalog:
            def load_table(self, full_name):
                return DummyTable()

        mock_load_catalog.return_value = DummyCatalog()
        # Act
        result = await file_processor.import_csv_to_table(
            warehouse, region, namespace, table_name, s3_url
        )
        # Assert
        assert result['status'] == 'success'
        assert result['rows_processed'] == 2
        assert result['file_processed'] == 'file.csv'
        assert result['csv_headers'] == ['id', 'name']

    @pytest.mark.asyncio
    async def test_import_csv_to_table_invalid_s3_url(self):
        """Test that an invalid S3 URL returns an error when importing CSV to table."""
        # Act
        result = await file_processor.import_csv_to_table('w', 'r', 'ns', 'tbl', 'not-a-url')
        # Assert
        assert result['status'] == 'error'
        assert 'Invalid URL scheme' in result['error']

    @pytest.mark.asyncio
    async def test_import_csv_to_table_non_csv(self):
        """Test that a non-CSV file returns an error when importing CSV to table."""
        # Act
        result = await file_processor.import_csv_to_table(
            'w', 'r', 'ns', 'tbl', 's3://bucket/file.txt'
        )
        # Assert
        assert result['status'] == 'error'
        assert 'is not a CSV file' in result['error']

    @pytest.mark.asyncio
    @patch('awslabs.s3_tables_mcp_server.file_processor.get_s3_client')
    @patch('awslabs.s3_tables_mcp_server.file_processor.pyiceberg_load_catalog')
    async def test_import_csv_to_table_missing_required_column(
        self, mock_load_catalog, mock_get_s3_client
    ):
        """Test that missing required columns in the CSV returns an error when importing."""
        # Arrange
        s3_url = 's3://bucket/file.csv'
        csv_content = 'id\n1\n2\n'
        mock_s3 = MagicMock()
        mock_s3.get_object.return_value = {
            'Body': MagicMock(read=MagicMock(return_value=csv_content.encode('utf-8')))
        }
        mock_get_s3_client.return_value = mock_s3

        class DummyField:
            def __init__(self, name, field_type, required=True):
                self.name = name
                self.field_type = field_type
                self.required = required

        class DummySchema:
            def __init__(self):
                self.fields = [DummyField('id', IntegerType()), DummyField('name', StringType())]

        class DummyTable:
            def schema(self):
                return DummySchema()

        class DummyCatalog:
            def load_table(self, full_name):
                return DummyTable()

        mock_load_catalog.return_value = DummyCatalog()
        # Act
        result = await file_processor.import_csv_to_table('w', 'r', 'ns', 'tbl', s3_url)
        # Assert
        assert result['status'] == 'error'
        assert 'missing required columns' in result['error'].lower()

    @pytest.mark.asyncio
    @patch('awslabs.s3_tables_mcp_server.file_processor.get_s3_client')
    @patch('awslabs.s3_tables_mcp_server.file_processor.pyiceberg_load_catalog')
    async def test_import_csv_to_table_missing_required_field_in_row(
        self, mock_load_catalog, mock_get_s3_client
    ):
        """Test that missing required field in a row returns an error when importing."""
        # Arrange
        s3_url = 's3://bucket/file.csv'
        csv_content = 'id,name\n1,\n2,Bob\n'
        mock_s3 = MagicMock()
        mock_s3.get_object.return_value = {
            'Body': MagicMock(read=MagicMock(return_value=csv_content.encode('utf-8')))
        }
        mock_get_s3_client.return_value = mock_s3

        class DummyField:
            def __init__(self, name, field_type, required=True):
                self.name = name
                self.field_type = field_type
                self.required = required

        class DummySchema:
            def __init__(self):
                self.fields = [DummyField('id', IntegerType()), DummyField('name', StringType())]

        class DummyTable:
            def schema(self):
                return DummySchema()

        class DummyCatalog:
            def load_table(self, full_name):
                return DummyTable()

        mock_load_catalog.return_value = DummyCatalog()
        # Act
        result = await file_processor.import_csv_to_table('w', 'r', 'ns', 'tbl', s3_url)
        # Assert
        assert result['status'] == 'error'
        assert 'required field name is missing' in result['error'].lower()

    @pytest.mark.asyncio
    @patch('awslabs.s3_tables_mcp_server.file_processor.get_s3_client')
    @patch('awslabs.s3_tables_mcp_server.file_processor.pyiceberg_load_catalog')
    async def test_import_csv_to_table_type_conversion_error(
        self, mock_load_catalog, mock_get_s3_client
    ):
        """Test that a type conversion error in the CSV returns an error when importing."""
        # Arrange
        s3_url = 's3://bucket/file.csv'
        csv_content = 'id,name\nnot_an_int,Alice\n'
        mock_s3 = MagicMock()
        mock_s3.get_object.return_value = {
            'Body': MagicMock(read=MagicMock(return_value=csv_content.encode('utf-8')))
        }
        mock_get_s3_client.return_value = mock_s3

        class DummyField:
            def __init__(self, name, field_type, required=True):
                self.name = name
                self.field_type = field_type
                self.required = required

        class DummySchema:
            def __init__(self):
                self.fields = [DummyField('id', IntegerType()), DummyField('name', StringType())]

        class DummyTable:
            def schema(self):
                return DummySchema()

        class DummyCatalog:
            def load_table(self, full_name):
                return DummyTable()

        mock_load_catalog.return_value = DummyCatalog()
        # Act
        result = await file_processor.import_csv_to_table('w', 'r', 'ns', 'tbl', s3_url)
        # Assert
        assert result['status'] == 'error'
        assert 'error converting value for field id' in result['error'].lower()

    @pytest.mark.asyncio
    @patch('awslabs.s3_tables_mcp_server.file_processor.get_s3_client')
    @patch('awslabs.s3_tables_mcp_server.file_processor.pyiceberg_load_catalog')
    async def test_import_csv_to_table_s3_error(self, mock_load_catalog, mock_get_s3_client):
        """Test that an S3 error is handled and returns an error when importing CSV to table."""
        # Arrange
        s3_url = 's3://bucket/file.csv'
        mock_s3 = MagicMock()
        mock_s3.get_object.side_effect = Exception('S3 error')
        mock_get_s3_client.return_value = mock_s3

        class DummyField:
            def __init__(self, name, field_type, required=True):
                self.name = name
                self.field_type = field_type
                self.required = required

        class DummySchema:
            def __init__(self):
                self.fields = [DummyField('id', IntegerType()), DummyField('name', StringType())]

        class DummyTable:
            def schema(self):
                return DummySchema()

        class DummyCatalog:
            def load_table(self, full_name):
                return DummyTable()

        mock_load_catalog.return_value = DummyCatalog()
        # Act
        result = await file_processor.import_csv_to_table('w', 'r', 'ns', 'tbl', s3_url)
        # Assert
        assert result['status'] == 'error'
        assert 's3 error' in result['error'].lower()

    @pytest.mark.asyncio
    @patch('awslabs.s3_tables_mcp_server.file_processor.get_s3_client')
    @patch('awslabs.s3_tables_mcp_server.file_processor.pyiceberg_load_catalog')
    async def test_import_csv_to_table_table_append_error(
        self, mock_load_catalog, mock_get_s3_client
    ):
        """Test that an error during table append is handled and returns an error when importing."""
        # Arrange
        s3_url = 's3://bucket/file.csv'
        csv_content = 'id,name\n1,Alice\n'
        mock_s3 = MagicMock()
        mock_s3.get_object.return_value = {
            'Body': MagicMock(read=MagicMock(return_value=csv_content.encode('utf-8')))
        }
        mock_get_s3_client.return_value = mock_s3

        class DummyField:
            def __init__(self, name, field_type, required=True):
                self.name = name
                self.field_type = field_type
                self.required = required

        class DummySchema:
            def __init__(self):
                self.fields = [DummyField('id', IntegerType()), DummyField('name', StringType())]

        class BadTable:
            def schema(self):
                return DummySchema()

            def append(self, table_data):
                raise Exception('append failed')

        class DummyCatalog:
            def load_table(self, full_name):
                return BadTable()

        mock_load_catalog.return_value = DummyCatalog()
        # Act
        result = await file_processor.import_csv_to_table('w', 'r', 'ns', 'tbl', s3_url)
        # Assert
        assert result['status'] == 'error'
        assert 'append failed' in result['error'].lower()
