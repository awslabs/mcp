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

"""Tests for the PyIcebergEngine module."""

import pytest
from awslabs.s3_tables_mcp_server.engines.pyiceberg import PyIcebergConfig, PyIcebergEngine
from unittest.mock import MagicMock, patch


class TestPyIcebergEngine:
    """Test the PyIcebergEngine class."""

    @pytest.fixture
    def mock_config(self):
        """Fixture that returns a mock PyIcebergConfig for testing."""
        return PyIcebergConfig(
            warehouse='test-warehouse',
            uri='https://test-uri',
            region='us-west-2',
            namespace='test_namespace',
            catalog_name='test_catalog',
            rest_signing_name='glue',
            rest_sigv4_enabled='true',
        )

    @pytest.fixture
    def engine_with_mocks(self, mock_config):
        """Fixture that returns a PyIcebergEngine instance with mocked dependencies."""
        with (
            patch(
                'awslabs.s3_tables_mcp_server.engines.pyiceberg.load_catalog'
            ) as mock_load_catalog,
            patch('awslabs.s3_tables_mcp_server.engines.pyiceberg.Session') as mock_Session,
            patch(
                'awslabs.s3_tables_mcp_server.engines.pyiceberg.DaftCatalog'
            ) as mock_DaftCatalog,
        ):
            mock_catalog = MagicMock()
            mock_load_catalog.return_value = mock_catalog
            mock_session = MagicMock()
            mock_Session.return_value = mock_session
            mock_daft_catalog = MagicMock()
            mock_DaftCatalog.from_iceberg.return_value = mock_daft_catalog
            engine = PyIcebergEngine(mock_config)
            return engine, mock_session, mock_catalog, mock_daft_catalog

    def test_init_success(self, mock_config):
        """Test successful initialization of PyIcebergEngine."""
        with (
            patch(
                'awslabs.s3_tables_mcp_server.engines.pyiceberg.load_catalog'
            ) as mock_load_catalog,
            patch('awslabs.s3_tables_mcp_server.engines.pyiceberg.Session') as mock_Session,
            patch(
                'awslabs.s3_tables_mcp_server.engines.pyiceberg.DaftCatalog'
            ) as mock_DaftCatalog,
        ):
            mock_catalog = MagicMock()
            mock_load_catalog.return_value = mock_catalog
            mock_session = MagicMock()
            mock_Session.return_value = mock_session
            mock_daft_catalog = MagicMock()
            mock_DaftCatalog.from_iceberg.return_value = mock_daft_catalog
            engine = PyIcebergEngine(mock_config)
            assert engine.config == mock_config
            assert engine._catalog == mock_catalog
            assert engine._session == mock_session
            mock_load_catalog.assert_called_once_with(
                'test_catalog',
                **{
                    'type': 'rest',
                    'warehouse': 'test-warehouse',
                    'uri': 'https://test-uri',
                    'rest.sigv4-enabled': 'true',
                    'rest.signing-name': 'glue',
                    'rest.signing-region': 'us-west-2',
                },
            )
            mock_session.attach.assert_called_once()
            mock_session.set_namespace.assert_called_once_with('test_namespace')

    def test_init_connection_failure(self, mock_config):
        """Test initialization failure when load_catalog raises an exception."""
        with patch(
            'awslabs.s3_tables_mcp_server.engines.pyiceberg.load_catalog'
        ) as mock_load_catalog:
            mock_load_catalog.side_effect = Exception('Connection failed')
            with pytest.raises(
                ConnectionError,
                match='Failed to initialize PyIceberg connection: Connection failed',
            ):
                PyIcebergEngine(mock_config)

    def test_execute_query_success(self, engine_with_mocks):
        """Test successful execution of a query using PyIcebergEngine."""
        engine, mock_session, *_ = engine_with_mocks
        mock_result = MagicMock()
        mock_df = MagicMock()
        mock_result.collect.return_value = mock_df
        mock_session.sql.return_value = mock_result
        mock_df.column_names = ['id', 'name']
        mock_df.to_pylist.return_value = [
            {'id': 1, 'name': 'test1'},
            {'id': 2, 'name': 'test2'},
        ]
        result = engine.execute_query('SELECT * FROM test_table')
        assert result['columns'] == ['id', 'name']
        assert result['rows'] == [[1, 'test1'], [2, 'test2']]
        mock_session.sql.assert_called_once_with('SELECT * FROM test_table')
        mock_result.collect.assert_called_once()
        mock_df.to_pylist.assert_called_once()

    def test_execute_query_no_session(self, mock_config):
        """Test that execute_query raises ConnectionError if session is None."""
        engine = PyIcebergEngine.__new__(PyIcebergEngine)
        engine.config = mock_config
        engine._session = None
        with pytest.raises(ConnectionError, match='No active session for PyIceberg/Daft'):
            engine.execute_query('SELECT * FROM test_table')

    def test_execute_query_failure(self, engine_with_mocks):
        """Test that execute_query raises an exception on query error."""
        engine, mock_session, *_ = engine_with_mocks
        mock_session.sql.side_effect = Exception('Query error')
        with pytest.raises(Exception, match='Error executing query: Query error'):
            engine.execute_query('SELECT * FROM test_table')

    def test_test_connection_success(self, engine_with_mocks):
        """Test that test_connection returns True when namespaces are listed successfully."""
        engine, mock_session, *_ = engine_with_mocks
        mock_session.list_namespaces.return_value = ['ns1', 'ns2']
        assert engine.test_connection() is True
        mock_session.list_namespaces.assert_called_once()

    def test_test_connection_failure(self, engine_with_mocks):
        """Test that test_connection returns False when listing namespaces fails."""
        engine, mock_session, *_ = engine_with_mocks
        mock_session.list_namespaces.side_effect = Exception('List failed')
        assert engine.test_connection() is False
        mock_session.list_namespaces.assert_called_once()

    def test_append_rows_no_catalog(self, mock_config):
        """Test that append_rows raises ConnectionError if catalog is None."""
        engine = PyIcebergEngine.__new__(PyIcebergEngine)
        engine.config = mock_config
        engine._catalog = None
        with pytest.raises(ConnectionError, match='No active catalog for PyIceberg'):
            engine.append_rows('mytable', [{'a': 1}])

    def test_append_rows_failure(self, engine_with_mocks):
        """Test that append_rows raises an exception if loading table fails."""
        engine, _, mock_catalog, _ = engine_with_mocks
        mock_catalog.load_table.side_effect = Exception('load error')
        with pytest.raises(Exception, match='Error appending rows: load error'):
            engine.append_rows('mytable', [{'a': 1}])
