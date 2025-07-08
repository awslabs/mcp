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
from awslabs.s3_tables_mcp_server.engines.pyiceberg import PyIcebergConfig, PyIcebergEngine
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
        assert config.rest_signing_name == 'glue'
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
        config = PyIcebergConfig(warehouse='wh', uri='uri', region='region', namespace='ns')
        mock_catalog = MagicMock()
        mock_load_catalog.return_value = mock_catalog
        mock_session_instance = MagicMock()
        mock_session.return_value = mock_session_instance
        mock_daft_catalog.from_iceberg.return_value = 'daftcat'
        mock_table = MagicMock()
        mock_catalog.load_table.return_value = mock_table
        mock_schema = MagicMock()
        mock_table.schema.return_value.as_arrow.return_value = mock_schema
        mock_pa_table = MagicMock()
        mock_pa.Table.from_pylist.return_value = mock_pa_table
        engine = PyIcebergEngine(config)
        rows = [{'a': 1}, {'a': 2}]
        engine.append_rows('mytable', rows)
        mock_catalog.load_table.assert_called_once_with('ns.mytable')
        mock_table.schema.assert_called_once()
        mock_pa.Table.from_pylist.assert_called_once_with(rows, schema=mock_schema)
        mock_table.append.assert_called_once_with(mock_pa_table)

    @patch('awslabs.s3_tables_mcp_server.engines.pyiceberg.pa')
    @patch('awslabs.s3_tables_mcp_server.engines.pyiceberg.Session')
    @patch('awslabs.s3_tables_mcp_server.engines.pyiceberg.DaftCatalog')
    @patch('awslabs.s3_tables_mcp_server.engines.pyiceberg.pyiceberg_load_catalog')
    def test_append_rows_with_dot_in_table_name(
        self, mock_load_catalog, mock_daft_catalog, mock_session, mock_pa
    ):
        """Test appending rows to a table with a dot in its name."""
        config = PyIcebergConfig(warehouse='wh', uri='uri', region='region', namespace='ns')
        mock_catalog = MagicMock()
        mock_load_catalog.return_value = mock_catalog
        mock_session_instance = MagicMock()
        mock_session.return_value = mock_session_instance
        mock_daft_catalog.from_iceberg.return_value = 'daftcat'
        mock_table = MagicMock()
        mock_catalog.load_table.return_value = mock_table
        mock_schema = MagicMock()
        mock_table.schema.return_value.as_arrow.return_value = mock_schema
        mock_pa_table = MagicMock()
        mock_pa.Table.from_pylist.return_value = mock_pa_table
        engine = PyIcebergEngine(config)
        rows = [{'a': 1}]
        engine.append_rows('otherns.mytable', rows)
        mock_catalog.load_table.assert_called_once_with('otherns.mytable')
        mock_table.schema.assert_called_once()
        mock_pa.Table.from_pylist.assert_called_once_with(rows, schema=mock_schema)
        mock_table.append.assert_called_once_with(mock_pa_table)

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
