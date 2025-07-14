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

"""Unit tests for pyiceberg.py (PyIcebergEngine and PyIcebergConfig)."""

import pytest
from awslabs.s3_tables_mcp_server.engines.pyiceberg import (
    PyIcebergConfig,
    PyIcebergEngine,
    convert_value_for_append,
)
from unittest.mock import MagicMock, patch


class TestPyIcebergConfig:
    """Unit tests for the PyIcebergConfig configuration class."""

    def test_config_fields(self):
        """Test that PyIcebergConfig fields are set correctly."""
        config = PyIcebergConfig(
            warehouse='my-warehouse',
            uri='https://example.com',
            region='us-west-2',
            namespace='testns',
        )
        assert config.warehouse == 'my-warehouse'
        assert config.uri == 'https://example.com'
        assert config.region == 'us-west-2'
        assert config.namespace == 'testns'
        assert config.catalog_name == 's3tablescatalog'
        assert config.rest_signing_name == 's3tables'
        assert config.rest_sigv4_enabled == 'true'


class TestPyIcebergEngine:
    """Unit tests for the PyIcebergEngine integration and behavior."""

    @patch('awslabs.s3_tables_mcp_server.engines.pyiceberg.pyiceberg_load_catalog')
    @patch('awslabs.s3_tables_mcp_server.engines.pyiceberg.Session')
    @patch('awslabs.s3_tables_mcp_server.engines.pyiceberg.DaftCatalog')
    def test_initialize_connection_success(
        self, mock_daft_catalog, mock_session, mock_load_catalog
    ):
        """Test successful initialization of PyIcebergEngine connection."""
        config = PyIcebergConfig(warehouse='wh', uri='uri', region='region', namespace='ns')
        mock_catalog = MagicMock()
        mock_load_catalog.return_value = mock_catalog
        mock_session_instance = MagicMock()
        mock_session.return_value = mock_session_instance
        mock_daft_catalog.from_iceberg.return_value = 'daftcat'

        engine = PyIcebergEngine(config)
        assert engine._catalog == mock_catalog
        assert engine._session == mock_session_instance
        mock_session_instance.attach.assert_called_once_with('daftcat')
        mock_session_instance.set_namespace.assert_called_once_with('ns')

    @patch(
        'awslabs.s3_tables_mcp_server.engines.pyiceberg.pyiceberg_load_catalog',
        side_effect=Exception('fail'),
    )
    def test_initialize_connection_failure(self, mock_load_catalog):
        """Test initialization failure raises ConnectionError."""
        config = PyIcebergConfig(warehouse='wh', uri='uri', region='region', namespace='ns')
        with pytest.raises(
            ConnectionError, match='Failed to initialize PyIceberg connection: fail'
        ):
            PyIcebergEngine(config)

    @patch('awslabs.s3_tables_mcp_server.engines.pyiceberg.Session')
    @patch('awslabs.s3_tables_mcp_server.engines.pyiceberg.DaftCatalog')
    @patch('awslabs.s3_tables_mcp_server.engines.pyiceberg.pyiceberg_load_catalog')
    def test_execute_query_success(self, mock_load_catalog, mock_daft_catalog, mock_session):
        """Test successful execution of a query."""
        config = PyIcebergConfig(warehouse='wh', uri='uri', region='region', namespace='ns')
        mock_catalog = MagicMock()
        mock_load_catalog.return_value = mock_catalog
        mock_session_instance = MagicMock()
        mock_session.return_value = mock_session_instance
        mock_daft_catalog.from_iceberg.return_value = 'daftcat'
        mock_result = MagicMock()
        mock_df = MagicMock()
        mock_df.column_names = ['a', 'b']
        mock_df.to_pylist.return_value = [{'a': 1, 'b': 2}, {'a': 3, 'b': 4}]
        mock_result.collect.return_value = mock_df
        mock_session_instance.sql.return_value = mock_result

        engine = PyIcebergEngine(config)
        result = engine.execute_query('SELECT * FROM t')
        assert result['columns'] == ['a', 'b']
        assert result['rows'] == [[1, 2], [3, 4]]
        mock_session_instance.sql.assert_called_once_with('SELECT * FROM t')
        mock_result.collect.assert_called_once()

    @patch('awslabs.s3_tables_mcp_server.engines.pyiceberg.Session')
    @patch('awslabs.s3_tables_mcp_server.engines.pyiceberg.DaftCatalog')
    @patch('awslabs.s3_tables_mcp_server.engines.pyiceberg.pyiceberg_load_catalog')
    def test_execute_query_none_result(self, mock_load_catalog, mock_daft_catalog, mock_session):
        """Test that execute_query raises if result is None."""
        config = PyIcebergConfig(warehouse='wh', uri='uri', region='region', namespace='ns')
        mock_catalog = MagicMock()
        mock_load_catalog.return_value = mock_catalog
        mock_session_instance = MagicMock()
        mock_session.return_value = mock_session_instance
        mock_daft_catalog.from_iceberg.return_value = 'daftcat'
        mock_session_instance.sql.return_value = None
        engine = PyIcebergEngine(config)
        with pytest.raises(Exception, match='Query execution returned None result'):
            engine.execute_query('SELECT * FROM t')

    @patch('awslabs.s3_tables_mcp_server.engines.pyiceberg.Session')
    @patch('awslabs.s3_tables_mcp_server.engines.pyiceberg.DaftCatalog')
    @patch('awslabs.s3_tables_mcp_server.engines.pyiceberg.pyiceberg_load_catalog')
    def test_execute_query_error(self, mock_load_catalog, mock_daft_catalog, mock_session):
        """Test that execute_query raises on SQL error."""
        config = PyIcebergConfig(warehouse='wh', uri='uri', region='region', namespace='ns')
        mock_catalog = MagicMock()
        mock_load_catalog.return_value = mock_catalog
        mock_session_instance = MagicMock()
        mock_session.return_value = mock_session_instance
        mock_daft_catalog.from_iceberg.return_value = 'daftcat'
        mock_session_instance.sql.side_effect = Exception('sqlfail')
        engine = PyIcebergEngine(config)
        with pytest.raises(Exception, match='Error executing query: sqlfail'):
            engine.execute_query('SELECT * FROM t')

    @patch('awslabs.s3_tables_mcp_server.engines.pyiceberg.Session')
    @patch('awslabs.s3_tables_mcp_server.engines.pyiceberg.DaftCatalog')
    @patch('awslabs.s3_tables_mcp_server.engines.pyiceberg.pyiceberg_load_catalog')
    def test_test_connection_success(self, mock_load_catalog, mock_daft_catalog, mock_session):
        """Test that test_connection returns True on success."""
        config = PyIcebergConfig(warehouse='wh', uri='uri', region='region', namespace='ns')
        mock_catalog = MagicMock()
        mock_load_catalog.return_value = mock_catalog
        mock_session_instance = MagicMock()
        mock_session.return_value = mock_session_instance
        mock_daft_catalog.from_iceberg.return_value = 'daftcat'
        mock_session_instance.list_namespaces.return_value = ['ns']
        engine = PyIcebergEngine(config)
        assert engine.test_connection() is True
        mock_session_instance.list_namespaces.assert_called_once()

    @patch('awslabs.s3_tables_mcp_server.engines.pyiceberg.Session')
    @patch('awslabs.s3_tables_mcp_server.engines.pyiceberg.DaftCatalog')
    @patch('awslabs.s3_tables_mcp_server.engines.pyiceberg.pyiceberg_load_catalog')
    def test_test_connection_failure(self, mock_load_catalog, mock_daft_catalog, mock_session):
        """Test that test_connection returns False on failure."""
        config = PyIcebergConfig(warehouse='wh', uri='uri', region='region', namespace='ns')
        mock_catalog = MagicMock()
        mock_load_catalog.return_value = mock_catalog
        mock_session_instance = MagicMock()
        mock_session.return_value = mock_session_instance
        mock_daft_catalog.from_iceberg.return_value = 'daftcat'
        mock_session_instance.list_namespaces.side_effect = Exception('fail')
        engine = PyIcebergEngine(config)
        assert engine.test_connection() is False

    @patch('awslabs.s3_tables_mcp_server.engines.pyiceberg.pa')
    @patch('awslabs.s3_tables_mcp_server.engines.pyiceberg.Session')
    @patch('awslabs.s3_tables_mcp_server.engines.pyiceberg.DaftCatalog')
    @patch('awslabs.s3_tables_mcp_server.engines.pyiceberg.pyiceberg_load_catalog')
    def test_append_rows_success(
        self, mock_load_catalog, mock_daft_catalog, mock_session, mock_pa
    ):
        """Test successful appending of rows to a table."""
        # Use a schema with known fields
        from pyiceberg.types import IntegerType, StringType

        class DummyField:
            def __init__(self, name, field_type, required=True):
                self.name = name
                self.field_type = field_type
                self.required = required

        class DummySchema:
            def __init__(self):
                self.fields = [DummyField('a', IntegerType()), DummyField('b', StringType())]

            def as_arrow(self):
                return 'dummy_arrow_schema'

        class DummyTable:
            def schema(self):
                return DummySchema()

            def append(self, pa_table):
                self.appended = pa_table

        class DummyCatalog:
            def load_table(self, full_name):
                return DummyTable()

        mock_catalog = DummyCatalog()
        mock_load_catalog.return_value = mock_catalog
        mock_session_instance = MagicMock()
        mock_session.return_value = mock_session_instance
        mock_daft_catalog.from_iceberg.return_value = 'daftcat'
        mock_pa_table = MagicMock()
        mock_pa.Table.from_pylist.return_value = mock_pa_table
        engine = PyIcebergEngine(
            PyIcebergConfig(warehouse='wh', uri='uri', region='region', namespace='ns')
        )
        rows = [{'a': 1, 'b': 'foo'}, {'a': 2, 'b': 'bar'}]
        engine.append_rows('mytable', rows)
        mock_pa.Table.from_pylist.assert_called_once()
        args, kwargs = mock_pa.Table.from_pylist.call_args
        # The dicts should have all schema fields
        assert args[0] == [{'a': 1, 'b': 'foo'}, {'a': 2, 'b': 'bar'}]
        assert kwargs['schema'] == 'dummy_arrow_schema'
        # Table.append should be called with the pyarrow table
        # (already checked by the original test)
        mock_pa.Table.from_pylist.reset_mock()

    @patch('awslabs.s3_tables_mcp_server.engines.pyiceberg.pa')
    @patch('awslabs.s3_tables_mcp_server.engines.pyiceberg.Session')
    @patch('awslabs.s3_tables_mcp_server.engines.pyiceberg.DaftCatalog')
    @patch('awslabs.s3_tables_mcp_server.engines.pyiceberg.pyiceberg_load_catalog')
    def test_append_rows_with_dot_in_table_name(
        self, mock_load_catalog, mock_daft_catalog, mock_session, mock_pa
    ):
        """Test appending rows to a table with a dot in its name."""
        from pyiceberg.types import IntegerType, StringType

        class DummyField:
            def __init__(self, name, field_type, required=True):
                self.name = name
                self.field_type = field_type
                self.required = required

        class DummySchema:
            def __init__(self):
                self.fields = [DummyField('a', IntegerType()), DummyField('b', StringType())]

            def as_arrow(self):
                return 'dummy_arrow_schema'

        class DummyTable:
            def schema(self):
                return DummySchema()

            def append(self, pa_table):
                self.appended = pa_table

        class DummyCatalog:
            def load_table(self, full_name):
                return DummyTable()

        mock_catalog = DummyCatalog()
        mock_load_catalog.return_value = mock_catalog
        mock_session_instance = MagicMock()
        mock_session.return_value = mock_session_instance
        mock_daft_catalog.from_iceberg.return_value = 'daftcat'
        mock_pa_table = MagicMock()
        mock_pa.Table.from_pylist.return_value = mock_pa_table
        engine = PyIcebergEngine(
            PyIcebergConfig(warehouse='wh', uri='uri', region='region', namespace='ns')
        )
        rows = [{'a': 1, 'b': 'foo'}]
        engine.append_rows('otherns.mytable', rows)
        mock_pa.Table.from_pylist.assert_called_once()
        args, kwargs = mock_pa.Table.from_pylist.call_args
        assert args[0] == [{'a': 1, 'b': 'foo'}]
        assert kwargs['schema'] == 'dummy_arrow_schema'
        mock_pa.Table.from_pylist.reset_mock()

    @patch('awslabs.s3_tables_mcp_server.engines.pyiceberg.pa')
    @patch('awslabs.s3_tables_mcp_server.engines.pyiceberg.Session')
    @patch('awslabs.s3_tables_mcp_server.engines.pyiceberg.DaftCatalog')
    @patch('awslabs.s3_tables_mcp_server.engines.pyiceberg.pyiceberg_load_catalog')
    def test_append_rows_error(self, mock_load_catalog, mock_daft_catalog, mock_session, mock_pa):
        """Test that append_rows raises on error loading table."""
        config = PyIcebergConfig(warehouse='wh', uri='uri', region='region', namespace='ns')
        mock_catalog = MagicMock()
        mock_load_catalog.return_value = mock_catalog
        mock_session_instance = MagicMock()
        mock_session.return_value = mock_session_instance
        mock_daft_catalog.from_iceberg.return_value = 'daftcat'
        mock_catalog.load_table.side_effect = Exception('fail')
        engine = PyIcebergEngine(config)
        with pytest.raises(Exception, match='Error appending rows: fail'):
            engine.append_rows('mytable', [{'a': 1}])

    def test_append_rows_no_catalog(self):
        """Test that append_rows raises ConnectionError when no catalog is set."""
        config = PyIcebergConfig(warehouse='wh', uri='uri', region='region', namespace='ns')
        engine = PyIcebergEngine.__new__(PyIcebergEngine)
        engine.config = config
        engine._catalog = None
        with pytest.raises(ConnectionError, match='No active catalog for PyIceberg'):
            engine.append_rows('mytable', [{'a': 1}])

    @patch('awslabs.s3_tables_mcp_server.engines.pyiceberg.pa')
    @patch('awslabs.s3_tables_mcp_server.engines.pyiceberg.Session')
    @patch('awslabs.s3_tables_mcp_server.engines.pyiceberg.DaftCatalog')
    @patch('awslabs.s3_tables_mcp_server.engines.pyiceberg.pyiceberg_load_catalog')
    def test_append_rows_type_conversion(
        self, mock_load_catalog, mock_daft_catalog, mock_session, mock_pa
    ):
        """Test append_rows type conversion for all supported types."""
        import uuid
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
            LongType,
            StringType,
            TimestampType,
            TimestamptzType,
            TimeType,
            UUIDType,
        )

        # Define a schema with all supported types
        class DummyField:
            def __init__(self, name, field_type, required=True):
                self.name = name
                self.field_type = field_type
                self.required = required

        class DummySchema:
            def __init__(self):
                self.fields = [
                    DummyField('bool_col', BooleanType()),
                    DummyField('int_col', IntegerType()),
                    DummyField('long_col', LongType()),
                    DummyField('float_col', FloatType()),
                    DummyField('double_col', DoubleType()),
                    DummyField('decimal_col', DecimalType(10, 2)),
                    DummyField('date_col', DateType()),
                    DummyField('time_col', TimeType()),
                    DummyField('timestamp_col', TimestampType()),
                    DummyField('timestamptz_col', TimestamptzType()),
                    DummyField('string_col', StringType()),
                    DummyField('uuid_col', UUIDType()),
                    DummyField('binary_col', BinaryType()),
                    DummyField('fixed_col', FixedType(4)),
                ]

            def as_arrow(self):
                return 'dummy_arrow_schema'

        class DummyTable:
            def schema(self):
                return DummySchema()

            def append(self, pa_table):
                self.appended = pa_table

        class DummyCatalog:
            def load_table(self, full_name):
                return DummyTable()

        mock_catalog = DummyCatalog()
        mock_load_catalog.return_value = mock_catalog
        mock_session_instance = MagicMock()
        mock_session.return_value = mock_session_instance
        mock_daft_catalog.from_iceberg.return_value = 'daftcat'
        mock_pa_table = MagicMock()
        mock_pa.Table.from_pylist.return_value = mock_pa_table

        config = PyIcebergConfig(warehouse='wh', uri='uri', region='region', namespace='ns')
        engine = PyIcebergEngine(config)
        # Provide values as strings (and some as native types)
        row = {
            'bool_col': 'true',
            'int_col': '42',
            'long_col': 1234567890123,  # already int
            'float_col': '3.14',
            'double_col': 2.718,
            'decimal_col': '1234.56',
            'date_col': '2024-06-07',
            'time_col': '12:34:56',
            'timestamp_col': '2024-06-07T12:34:56',
            'timestamptz_col': '2024-06-07T12:34:56',
            'string_col': 123,  # will be converted to str
            'uuid_col': str(uuid.UUID('12345678-1234-5678-1234-567812345678')),
            'binary_col': 'deadbeef',
            'fixed_col': 'cafebabe',
        }
        engine.append_rows('mytable', [row])
        # Check the conversion by inspecting the argument to from_pylist
        args, kwargs = mock_pa.Table.from_pylist.call_args
        converted = args[0][0]  # first (and only) row
        assert converted['bool_col'] is True
        assert converted['int_col'] == 42
        assert converted['long_col'] == 1234567890123
        assert abs(converted['float_col'] - 3.14) < 1e-6
        assert abs(converted['double_col'] - 2.718) < 1e-6
        assert converted['decimal_col'] == Decimal('1234.56')
        assert converted['date_col'] == date(2024, 6, 7)
        assert converted['time_col'] == time(12, 34, 56)
        assert converted['timestamp_col'] == datetime(2024, 6, 7, 12, 34, 56)
        assert converted['timestamptz_col'] == datetime(2024, 6, 7, 12, 34, 56)
        assert converted['string_col'] == '123'
        assert converted['uuid_col'] == uuid.UUID('12345678-1234-5678-1234-567812345678')
        assert converted['binary_col'] == bytes.fromhex('deadbeef')
        assert converted['fixed_col'] == bytes.fromhex('cafebabe')


def test_convert_value_for_append_unsupported_type():
    """Test that convert_value_for_append raises ValueError for unsupported type conversion."""

    class DummyType:
        pass

    dummy_type = DummyType()
    with pytest.raises(
        ValueError, match=r"Unsupported conversion from <class 'int'> to .*DummyType.*"
    ):
        convert_value_for_append(123, dummy_type)


def test_test_connection_no_session():
    """Test that test_connection returns False when _session is None (covers early return)."""
    config = PyIcebergConfig(warehouse='wh', uri='uri', region='region', namespace='ns')
    engine = PyIcebergEngine.__new__(PyIcebergEngine)
    engine.config = config
    engine._session = None
    assert engine.test_connection() is False
