import pyarrow as pa
import pytest
from datetime import date
from unittest.mock import MagicMock, patch


@pytest.mark.asyncio
async def test_execute_query_success():
    """Test PyIcebergEngine.execute_query successfully executes a SQL query and returns results."""
    from awslabs.s3_tables_mcp_server.engines.pyiceberg import PyIcebergConfig, PyIcebergEngine

    # Test configuration
    config = PyIcebergConfig(
        warehouse='arn:aws:s3tables:us-west-2:123456789012:bucket/test-bucket',
        uri='https://s3tables.us-west-2.amazonaws.com/iceberg',
        region='us-west-2',
        namespace='test_namespace',
        catalog_name='s3tablescatalog',
        rest_signing_name='s3tables',
        rest_sigv4_enabled='true',
    )

    # Mock objects
    mock_catalog = MagicMock()
    mock_session = MagicMock()
    mock_result = MagicMock()
    mock_df = MagicMock()

    # Mock the result data
    mock_df.column_names = ['id', 'name', 'value']
    mock_df.to_pylist.return_value = [
        {'id': 1, 'name': 'Alice', 'value': 100.5},
        {'id': 2, 'name': 'Bob', 'value': 200.0},
        {'id': 3, 'name': 'Charlie', 'value': 150.75},
    ]
    mock_result.collect.return_value = mock_df
    mock_session.sql.return_value = mock_result

    # Mock the catalog loading and session creation
    with (
        patch(
            'awslabs.s3_tables_mcp_server.engines.pyiceberg.pyiceberg_load_catalog',
            return_value=mock_catalog,
        ) as mock_load_catalog,
        patch(
            'awslabs.s3_tables_mcp_server.engines.pyiceberg.Session', return_value=mock_session
        ) as mock_session_class,
        patch('awslabs.s3_tables_mcp_server.engines.pyiceberg.DaftCatalog'),
    ):
        # Create the engine
        engine = PyIcebergEngine(config)

        # Execute a test query
        query = 'SELECT * FROM test_table LIMIT 10'
        result = engine.execute_query(query)

        # Verify the result structure
        assert result['columns'] == ['id', 'name', 'value']
        assert len(result['rows']) == 3
        assert result['rows'][0] == [1, 'Alice', 100.5]
        assert result['rows'][1] == [2, 'Bob', 200.0]
        assert result['rows'][2] == [3, 'Charlie', 150.75]

        # Verify the mocks were called correctly
        mock_load_catalog.assert_called_once_with(
            's3tablescatalog',
            'arn:aws:s3tables:us-west-2:123456789012:bucket/test-bucket',
            'https://s3tables.us-west-2.amazonaws.com/iceberg',
            'us-west-2',
            's3tables',
            'true',
        )
        mock_session_class.assert_called_once()
        mock_session.attach.assert_called_once()
        mock_session.set_namespace.assert_called_once_with('test_namespace')
        mock_session.sql.assert_called_once_with(query)
        mock_result.collect.assert_called_once()
        mock_df.to_pylist.assert_called_once()


@pytest.mark.asyncio
async def test_initialize_connection_exception():
    """Test PyIcebergEngine raises ConnectionError when initialization fails."""
    from awslabs.s3_tables_mcp_server.engines.pyiceberg import PyIcebergConfig, PyIcebergEngine

    # Test configuration
    config = PyIcebergConfig(
        warehouse='arn:aws:s3tables:us-west-2:123456789012:bucket/test-bucket',
        uri='https://s3tables.us-west-2.amazonaws.com/iceberg',
        region='us-west-2',
        namespace='test_namespace',
        catalog_name='s3tablescatalog',
        rest_signing_name='s3tables',
        rest_sigv4_enabled='true',
    )

    # Mock pyiceberg_load_catalog to raise an exception during initialization
    with patch(
        'awslabs.s3_tables_mcp_server.engines.pyiceberg.pyiceberg_load_catalog',
        side_effect=Exception('Authentication failed'),
    ) as mock_load_catalog:
        # Verify that creating the engine raises a ConnectionError
        with pytest.raises(ConnectionError) as exc_info:
            PyIcebergEngine(config)

        # Verify the error message contains the original exception
        assert 'Failed to initialize PyIceberg connection' in str(exc_info.value)
        assert 'Authentication failed' in str(exc_info.value)

        # Verify the mock was called with the correct parameters
        mock_load_catalog.assert_called_once_with(
            's3tablescatalog',
            'arn:aws:s3tables:us-west-2:123456789012:bucket/test-bucket',
            'https://s3tables.us-west-2.amazonaws.com/iceberg',
            'us-west-2',
            's3tables',
            'true',
        )


@pytest.mark.asyncio
async def test_execute_query_no_active_session():
    """Test PyIcebergEngine.execute_query raises ConnectionError when there's no active session."""
    from awslabs.s3_tables_mcp_server.engines.pyiceberg import PyIcebergConfig, PyIcebergEngine

    # Test configuration
    config = PyIcebergConfig(
        warehouse='arn:aws:s3tables:us-west-2:123456789012:bucket/test-bucket',
        uri='https://s3tables.us-west-2.amazonaws.com/iceberg',
        region='us-west-2',
        namespace='test_namespace',
        catalog_name='s3tablescatalog',
        rest_signing_name='s3tables',
        rest_sigv4_enabled='true',
    )

    # Mock objects for successful initialization
    mock_catalog = MagicMock()
    mock_session = MagicMock()

    # Mock the catalog loading and session creation
    with (
        patch(
            'awslabs.s3_tables_mcp_server.engines.pyiceberg.pyiceberg_load_catalog',
            return_value=mock_catalog,
        ),
        patch('awslabs.s3_tables_mcp_server.engines.pyiceberg.Session', return_value=mock_session),
        patch('awslabs.s3_tables_mcp_server.engines.pyiceberg.DaftCatalog'),
    ):
        # Create the engine
        engine = PyIcebergEngine(config)

        # Manually set the session to None to simulate no active session
        engine._session = None

        # Verify that execute_query raises a ConnectionError
        with pytest.raises(ConnectionError) as exc_info:
            engine.execute_query('SELECT * FROM test_table')

        # Verify the error message
        assert 'No active session for PyIceberg/Daft' in str(exc_info.value)

        # Verify that the session.sql method was not called since the check failed early
        mock_session.sql.assert_not_called()


@pytest.mark.asyncio
async def test_execute_query_none_result():
    """Test PyIcebergEngine.execute_query raises Exception when query execution returns None result."""
    from awslabs.s3_tables_mcp_server.engines.pyiceberg import PyIcebergConfig, PyIcebergEngine

    # Test configuration
    config = PyIcebergConfig(
        warehouse='arn:aws:s3tables:us-west-2:123456789012:bucket/test-bucket',
        uri='https://s3tables.us-west-2.amazonaws.com/iceberg',
        region='us-west-2',
        namespace='test_namespace',
        catalog_name='s3tablescatalog',
        rest_signing_name='s3tables',
        rest_sigv4_enabled='true',
    )

    # Mock objects for successful initialization
    mock_catalog = MagicMock()
    mock_session = MagicMock()

    # Mock session.sql to return None (simulating query execution failure)
    mock_session.sql.return_value = None

    # Mock the catalog loading and session creation
    with (
        patch(
            'awslabs.s3_tables_mcp_server.engines.pyiceberg.pyiceberg_load_catalog',
            return_value=mock_catalog,
        ),
        patch('awslabs.s3_tables_mcp_server.engines.pyiceberg.Session', return_value=mock_session),
        patch('awslabs.s3_tables_mcp_server.engines.pyiceberg.DaftCatalog'),
    ):
        # Create the engine
        engine = PyIcebergEngine(config)

        # Verify that execute_query raises an Exception when result is None
        with pytest.raises(Exception) as exc_info:
            engine.execute_query('SELECT * FROM test_table')

        # Verify the error message
        assert 'Query execution returned None result' in str(exc_info.value)

        # Verify that session.sql was called with the query
        mock_session.sql.assert_called_once_with('SELECT * FROM test_table')


@pytest.mark.asyncio
async def test_test_connection_success():
    """Test PyIcebergEngine.test_connection returns True when connection is successful."""
    from awslabs.s3_tables_mcp_server.engines.pyiceberg import PyIcebergConfig, PyIcebergEngine

    # Test configuration
    config = PyIcebergConfig(
        warehouse='arn:aws:s3tables:us-west-2:123456789012:bucket/test-bucket',
        uri='https://s3tables.us-west-2.amazonaws.com/iceberg',
        region='us-west-2',
        namespace='test_namespace',
        catalog_name='s3tablescatalog',
        rest_signing_name='s3tables',
        rest_sigv4_enabled='true',
    )

    # Mock objects for successful initialization
    mock_catalog = MagicMock()
    mock_session = MagicMock()

    # Mock list_namespaces to return successfully
    mock_session.list_namespaces.return_value = ['namespace1', 'namespace2']

    # Mock the catalog loading and session creation
    with (
        patch(
            'awslabs.s3_tables_mcp_server.engines.pyiceberg.pyiceberg_load_catalog',
            return_value=mock_catalog,
        ),
        patch('awslabs.s3_tables_mcp_server.engines.pyiceberg.Session', return_value=mock_session),
        patch('awslabs.s3_tables_mcp_server.engines.pyiceberg.DaftCatalog'),
    ):
        # Create the engine
        engine = PyIcebergEngine(config)

        # Test the connection
        result = engine.test_connection()

        # Verify the result
        assert result is True

        # Verify that list_namespaces was called
        mock_session.list_namespaces.assert_called_once()


@pytest.mark.asyncio
async def test_test_connection_no_session():
    """Test PyIcebergEngine.test_connection returns False when there's no active session."""
    from awslabs.s3_tables_mcp_server.engines.pyiceberg import PyIcebergConfig, PyIcebergEngine

    # Test configuration
    config = PyIcebergConfig(
        warehouse='arn:aws:s3tables:us-west-2:123456789012:bucket/test-bucket',
        uri='https://s3tables.us-west-2.amazonaws.com/iceberg',
        region='us-west-2',
        namespace='test_namespace',
        catalog_name='s3tablescatalog',
        rest_signing_name='s3tables',
        rest_sigv4_enabled='true',
    )

    # Mock objects for successful initialization
    mock_catalog = MagicMock()
    mock_session = MagicMock()

    # Mock the catalog loading and session creation
    with (
        patch(
            'awslabs.s3_tables_mcp_server.engines.pyiceberg.pyiceberg_load_catalog',
            return_value=mock_catalog,
        ),
        patch('awslabs.s3_tables_mcp_server.engines.pyiceberg.Session', return_value=mock_session),
        patch('awslabs.s3_tables_mcp_server.engines.pyiceberg.DaftCatalog'),
    ):
        # Create the engine
        engine = PyIcebergEngine(config)

        # Manually set the session to None to simulate no active session
        engine._session = None

        # Test the connection
        result = engine.test_connection()

        # Verify the result
        assert result is False

        # Verify that list_namespaces was not called since the check failed early
        mock_session.list_namespaces.assert_not_called()


@pytest.mark.asyncio
async def test_test_connection_exception():
    """Test PyIcebergEngine.test_connection returns False when list_namespaces raises an exception."""
    from awslabs.s3_tables_mcp_server.engines.pyiceberg import PyIcebergConfig, PyIcebergEngine

    # Test configuration
    config = PyIcebergConfig(
        warehouse='arn:aws:s3tables:us-west-2:123456789012:bucket/test-bucket',
        uri='https://s3tables.us-west-2.amazonaws.com/iceberg',
        region='us-west-2',
        namespace='test_namespace',
        catalog_name='s3tablescatalog',
        rest_signing_name='s3tables',
        rest_sigv4_enabled='true',
    )

    # Mock objects for successful initialization
    mock_catalog = MagicMock()
    mock_session = MagicMock()

    # Mock list_namespaces to raise an exception
    mock_session.list_namespaces.side_effect = Exception('Connection timeout')

    # Mock the catalog loading and session creation
    with (
        patch(
            'awslabs.s3_tables_mcp_server.engines.pyiceberg.pyiceberg_load_catalog',
            return_value=mock_catalog,
        ),
        patch('awslabs.s3_tables_mcp_server.engines.pyiceberg.Session', return_value=mock_session),
        patch('awslabs.s3_tables_mcp_server.engines.pyiceberg.DaftCatalog'),
    ):
        # Create the engine
        engine = PyIcebergEngine(config)

        # Test the connection
        result = engine.test_connection()

        # Verify the result
        assert result is False

        # Verify that list_namespaces was called
        mock_session.list_namespaces.assert_called_once()


@pytest.mark.asyncio
async def test_append_rows_success():
    """Test PyIcebergEngine.append_rows successfully appends rows to an Iceberg table."""
    from awslabs.s3_tables_mcp_server.engines.pyiceberg import PyIcebergConfig, PyIcebergEngine

    # Test configuration
    config = PyIcebergConfig(
        warehouse='arn:aws:s3tables:us-west-2:123456789012:bucket/test-bucket',
        uri='https://s3tables.us-west-2.amazonaws.com/iceberg',
        region='us-west-2',
        namespace='test_namespace',
        catalog_name='s3tablescatalog',
        rest_signing_name='s3tables',
        rest_sigv4_enabled='true',
    )

    # Mock objects for successful initialization
    mock_catalog = MagicMock()
    mock_session = MagicMock()
    mock_table = MagicMock()
    mock_schema = MagicMock()

    # Create a real PyArrow schema that matches our test data
    real_pyarrow_schema = pa.schema(
        [('id', pa.int64()), ('name', pa.string()), ('age', pa.int64())]
    )

    # Mock the table schema to return a real PyArrow schema
    mock_table.schema.return_value = mock_schema
    mock_schema.as_arrow.return_value = real_pyarrow_schema
    mock_catalog.load_table.return_value = mock_table

    # Test data
    table_name = 'test_table'
    rows = [
        {'id': 1, 'name': 'Alice', 'age': 30},
        {'id': 2, 'name': 'Bob', 'age': 25},
        {'id': 3, 'name': 'Charlie', 'age': 35},
    ]

    # Mock the catalog loading and session creation
    with (
        patch(
            'awslabs.s3_tables_mcp_server.engines.pyiceberg.pyiceberg_load_catalog',
            return_value=mock_catalog,
        ),
        patch('awslabs.s3_tables_mcp_server.engines.pyiceberg.Session', return_value=mock_session),
        patch('awslabs.s3_tables_mcp_server.engines.pyiceberg.DaftCatalog'),
    ):
        # Create the engine
        engine = PyIcebergEngine(config)

        # Mock the _convert_row_to_schema_types method to return converted rows
        converted_rows = [
            {'id': 1, 'name': 'Alice', 'age': 30},
            {'id': 2, 'name': 'Bob', 'age': 25},
            {'id': 3, 'name': 'Charlie', 'age': 35},
        ]
        engine._convert_row_to_schema_types = MagicMock(side_effect=converted_rows)

        # Append rows to the table
        engine.append_rows(table_name, rows)

        # Verify the catalog was used to load the table with the correct full name
        expected_full_table_name = f'{config.namespace}.{table_name}'
        mock_catalog.load_table.assert_called_once_with(expected_full_table_name)

        # Verify the table schema was retrieved
        mock_table.schema.assert_called_once()
        mock_schema.as_arrow.assert_called_once()

        # Verify the data conversion was called for each row
        assert engine._convert_row_to_schema_types.call_count == 3

        # Verify the table append was called (with a real PyArrow table)
        mock_table.append.assert_called_once()
        # Get the actual PyArrow table that was passed to append
        actual_pyarrow_table = mock_table.append.call_args[0][0]
        # Verify it's a real PyArrow table with the expected data
        assert hasattr(actual_pyarrow_table, 'num_rows')
        assert actual_pyarrow_table.num_rows == 3


@pytest.mark.asyncio
async def test_append_rows_no_active_catalog():
    """Test PyIcebergEngine.append_rows raises ConnectionError when there's no active catalog."""
    from awslabs.s3_tables_mcp_server.engines.pyiceberg import PyIcebergConfig, PyIcebergEngine

    # Test configuration
    config = PyIcebergConfig(
        warehouse='arn:aws:s3tables:us-west-2:123456789012:bucket/test-bucket',
        uri='https://s3tables.us-west-2.amazonaws.com/iceberg',
        region='us-west-2',
        namespace='test_namespace',
        catalog_name='s3tablescatalog',
        rest_signing_name='s3tables',
        rest_sigv4_enabled='true',
    )

    # Mock objects for successful initialization
    mock_catalog = MagicMock()
    mock_session = MagicMock()

    # Mock the catalog loading and session creation
    with (
        patch(
            'awslabs.s3_tables_mcp_server.engines.pyiceberg.pyiceberg_load_catalog',
            return_value=mock_catalog,
        ),
        patch('awslabs.s3_tables_mcp_server.engines.pyiceberg.Session', return_value=mock_session),
        patch('awslabs.s3_tables_mcp_server.engines.pyiceberg.DaftCatalog'),
    ):
        # Create the engine
        engine = PyIcebergEngine(config)

        # Manually set the catalog to None to simulate no active catalog
        engine._catalog = None

        # Test data
        table_name = 'test_table'
        rows = [{'id': 1, 'name': 'Alice', 'age': 30}, {'id': 2, 'name': 'Bob', 'age': 25}]

        # Verify that append_rows raises a ConnectionError
        with pytest.raises(ConnectionError) as exc_info:
            engine.append_rows(table_name, rows)

        # Verify the error message
        assert 'No active catalog for PyIceberg' in str(exc_info.value)

        # Verify that no catalog operations were performed since the check failed early
        mock_catalog.load_table.assert_not_called()


@pytest.mark.asyncio
async def test_append_rows_general_exception():
    """Test PyIcebergEngine.append_rows raises Exception when a general exception occurs during appending."""
    from awslabs.s3_tables_mcp_server.engines.pyiceberg import PyIcebergConfig, PyIcebergEngine

    # Test configuration
    config = PyIcebergConfig(
        warehouse='arn:aws:s3tables:us-west-2:123456789012:bucket/test-bucket',
        uri='https://s3tables.us-west-2.amazonaws.com/iceberg',
        region='us-west-2',
        namespace='test_namespace',
        catalog_name='s3tablescatalog',
        rest_signing_name='s3tables',
        rest_sigv4_enabled='true',
    )

    # Mock objects for successful initialization
    mock_catalog = MagicMock()
    mock_session = MagicMock()
    mock_table = MagicMock()
    mock_schema = MagicMock()

    # Mock the table schema
    mock_table.schema.return_value = mock_schema
    mock_schema.as_arrow.return_value = MagicMock()  # Mock schema for this test
    mock_catalog.load_table.return_value = mock_table

    # Mock the catalog loading and session creation
    with (
        patch(
            'awslabs.s3_tables_mcp_server.engines.pyiceberg.pyiceberg_load_catalog',
            return_value=mock_catalog,
        ),
        patch('awslabs.s3_tables_mcp_server.engines.pyiceberg.Session', return_value=mock_session),
        patch('awslabs.s3_tables_mcp_server.engines.pyiceberg.DaftCatalog'),
    ):
        # Create the engine
        engine = PyIcebergEngine(config)

        # Mock the _convert_row_to_schema_types method to raise an exception
        engine._convert_row_to_schema_types = MagicMock(
            side_effect=Exception('Data conversion failed')
        )

        # Test data
        table_name = 'test_table'
        rows = [{'id': 1, 'name': 'Alice', 'age': 30}, {'id': 2, 'name': 'Bob', 'age': 25}]

        # Verify that append_rows raises an Exception with the wrapped error message
        with pytest.raises(Exception) as exc_info:
            engine.append_rows(table_name, rows)

        # Verify the error message contains the wrapper text and original exception
        assert 'Error appending rows' in str(exc_info.value)
        assert 'Data conversion failed' in str(exc_info.value)

        # Verify that the catalog operations were attempted before the exception
        expected_full_table_name = f'{config.namespace}.{table_name}'
        mock_catalog.load_table.assert_called_once_with(expected_full_table_name)
        mock_table.schema.assert_called_once()
        mock_schema.as_arrow.assert_called_once()

        # Verify that the data conversion was attempted (and failed)
        assert engine._convert_row_to_schema_types.call_count == 1


@pytest.mark.asyncio
async def test_append_rows_with_namespace_in_table_name():
    """Test PyIcebergEngine.append_rows uses table_name directly when it already contains a namespace."""
    from awslabs.s3_tables_mcp_server.engines.pyiceberg import PyIcebergConfig, PyIcebergEngine

    # Test configuration
    config = PyIcebergConfig(
        warehouse='arn:aws:s3tables:us-west-2:123456789012:bucket/test-bucket',
        uri='https://s3tables.us-west-2.amazonaws.com/iceberg',
        region='us-west-2',
        namespace='test_namespace',
        catalog_name='s3tablescatalog',
        rest_signing_name='s3tables',
        rest_sigv4_enabled='true',
    )

    # Mock objects for successful initialization
    mock_catalog = MagicMock()
    mock_session = MagicMock()
    mock_table = MagicMock()
    mock_schema = MagicMock()

    # Create a real PyArrow schema that matches our test data
    real_pyarrow_schema = pa.schema(
        [('id', pa.int64()), ('name', pa.string()), ('age', pa.int64())]
    )

    # Mock the table schema to return a real PyArrow schema
    mock_table.schema.return_value = mock_schema
    mock_schema.as_arrow.return_value = real_pyarrow_schema
    mock_catalog.load_table.return_value = mock_table

    # Test data with table name that already contains a namespace
    table_name = 'other_namespace.test_table'  # Already has namespace
    rows = [
        {'id': 1, 'name': 'Alice', 'age': 30},
        {'id': 2, 'name': 'Bob', 'age': 25},
        {'id': 3, 'name': 'Charlie', 'age': 35},
    ]

    # Mock the catalog loading and session creation
    with (
        patch(
            'awslabs.s3_tables_mcp_server.engines.pyiceberg.pyiceberg_load_catalog',
            return_value=mock_catalog,
        ),
        patch('awslabs.s3_tables_mcp_server.engines.pyiceberg.Session', return_value=mock_session),
        patch('awslabs.s3_tables_mcp_server.engines.pyiceberg.DaftCatalog'),
    ):
        # Create the engine
        engine = PyIcebergEngine(config)

        # Mock the _convert_row_to_schema_types method to return converted rows
        converted_rows = [
            {'id': 1, 'name': 'Alice', 'age': 30},
            {'id': 2, 'name': 'Bob', 'age': 25},
            {'id': 3, 'name': 'Charlie', 'age': 35},
        ]
        engine._convert_row_to_schema_types = MagicMock(side_effect=converted_rows)

        # Append rows to the table
        engine.append_rows(table_name, rows)

        # Verify the catalog was used to load the table with the original table name (no namespace prepending)
        # This tests the else branch where full_table_name = table_name
        mock_catalog.load_table.assert_called_once_with(table_name)

        # Verify the table schema was retrieved
        mock_table.schema.assert_called_once()
        mock_schema.as_arrow.assert_called_once()

        # Verify the data conversion was called for each row
        assert engine._convert_row_to_schema_types.call_count == 3

        # Verify the table append was called (with a real PyArrow table)
        mock_table.append.assert_called_once()
        # Get the actual PyArrow table that was passed to append
        actual_pyarrow_table = mock_table.append.call_args[0][0]
        # Verify it's a real PyArrow table with the expected data
        assert hasattr(actual_pyarrow_table, 'num_rows')
        assert actual_pyarrow_table.num_rows == 3


@pytest.mark.asyncio
async def test_convert_row_to_schema_types_comprehensive():
    """Test PyIcebergEngine._convert_row_to_schema_types with all different data type branches."""
    from awslabs.s3_tables_mcp_server.engines.pyiceberg import PyIcebergConfig, PyIcebergEngine

    # Test configuration
    config = PyIcebergConfig(
        warehouse='arn:aws:s3tables:us-west-2:123456789012:bucket/test-bucket',
        uri='https://s3tables.us-west-2.amazonaws.com/iceberg',
        region='us-west-2',
        namespace='test_namespace',
        catalog_name='s3tablescatalog',
        rest_signing_name='s3tables',
        rest_sigv4_enabled='true',
    )

    # Mock objects for successful initialization
    mock_catalog = MagicMock()
    mock_session = MagicMock()

    # Mock the catalog loading and session creation
    with (
        patch(
            'awslabs.s3_tables_mcp_server.engines.pyiceberg.pyiceberg_load_catalog',
            return_value=mock_catalog,
        ),
        patch('awslabs.s3_tables_mcp_server.engines.pyiceberg.Session', return_value=mock_session),
        patch('awslabs.s3_tables_mcp_server.engines.pyiceberg.DaftCatalog'),
    ):
        # Create the engine
        engine = PyIcebergEngine(config)

        # Test 1: Date type conversion (string to date)
        schema_date = pa.schema([('birth_date', pa.date32())])
        row_date = {'birth_date': '2023-01-15'}
        result_date = engine._convert_row_to_schema_types(row_date, schema_date)
        assert isinstance(result_date['birth_date'], date)
        assert result_date['birth_date'] == date(2023, 1, 15)

        # Test 2: Date type with non-string value (should keep original)
        row_date_non_string = {'birth_date': date(2023, 1, 15)}
        result_date_non_string = engine._convert_row_to_schema_types(
            row_date_non_string, schema_date
        )
        assert isinstance(result_date_non_string['birth_date'], date)
        assert result_date_non_string['birth_date'] == date(2023, 1, 15)

        # Test 4: Integer types - non-digit strings should keep original
        schema_int = pa.schema(
            [('id', pa.int64()), ('age', pa.int32()), ('score', pa.int16()), ('flag', pa.int8())]
        )
        row_int_non_digit = {'id': 'abc', 'age': '25.5'}
        result_int_non_digit = engine._convert_row_to_schema_types(row_int_non_digit, schema_int)
        assert result_int_non_digit['id'] == 'abc'  # Should keep original
        assert result_int_non_digit['age'] == '25.5'  # Should keep original

        # Test 5: Float types - string to float conversion
        schema_float = pa.schema([('price', pa.float64()), ('rating', pa.float32())])
        row_float = {'price': '99.99', 'rating': '-4.5'}
        result_float = engine._convert_row_to_schema_types(row_float, schema_float)
        assert result_float['price'] == '99.99'
        assert result_float['rating'] == '-4.5'

        # Test 6: Float types - non-numeric strings should keep original
        row_float_non_numeric = {'price': 'expensive', 'rating': 'good'}
        result_float_non_numeric = engine._convert_row_to_schema_types(
            row_float_non_numeric, schema_float
        )
        assert result_float_non_numeric['price'] == 'expensive'  # Should keep original
        assert result_float_non_numeric['rating'] == 'good'  # Should keep original

        # Test 7: String type - should keep original value
        schema_string = pa.schema([('name', pa.string())])
        row_string = {'name': 'Alice'}
        result_string = engine._convert_row_to_schema_types(row_string, schema_string)
        assert result_string['name'] == 'Alice'  # Should keep original

        # Test 8: Field not in schema - should keep original value
        schema_partial = pa.schema([('id', pa.int64())])
        row_extra = {'extra_field': 'extra_value'}
        result_extra = engine._convert_row_to_schema_types(row_extra, schema_partial)
        assert result_extra['extra_field'] == 'extra_value'  # Should keep original

        # Test 9: Exception handling - should keep original value on conversion error
        schema_error = pa.schema([('bad_date', pa.date32())])
        row_error = {'bad_date': 'invalid-date-format'}
        result_error = engine._convert_row_to_schema_types(row_error, schema_error)
        assert result_error['bad_date'] == 'invalid-date-format'  # Should keep original on error

        # Test 10: Mixed types in one row
        schema_mixed = pa.schema(
            [
                ('id', pa.int64()),
                ('name', pa.string()),
                ('price', pa.float64()),
                ('birth_date', pa.date32()),
            ]
        )
        row_mixed = {'id': '456', 'name': 'Bob', 'price': '29.99', 'birth_date': '1990-05-20'}
        result_mixed = engine._convert_row_to_schema_types(row_mixed, schema_mixed)
        assert result_mixed['id'] == '456'
        assert result_mixed['name'] == 'Bob'
        assert result_mixed['price'] == '29.99'
        assert isinstance(result_mixed['birth_date'], date)
        assert result_mixed['birth_date'] == date(1990, 5, 20)

        # Test 11: Timestamp type conversion (ISO8601 string to datetime)
        from datetime import datetime

        schema_timestamp = pa.schema([('event_time', pa.timestamp('us'))])
        row_timestamp_iso = {'event_time': '2023-07-21T10:26:00'}
        result_timestamp_iso = engine._convert_row_to_schema_types(
            row_timestamp_iso, schema_timestamp
        )
        assert isinstance(result_timestamp_iso['event_time'], datetime)
        assert result_timestamp_iso['event_time'] == datetime(2023, 7, 21, 10, 26, 0)

        # Test 12: Timestamp type conversion (fallback format)
        row_timestamp_fallback = {'event_time': '2023-07-21 10:26:00'}
        result_timestamp_fallback = engine._convert_row_to_schema_types(
            row_timestamp_fallback, schema_timestamp
        )
        assert isinstance(result_timestamp_fallback['event_time'], datetime)
        assert result_timestamp_fallback['event_time'] == datetime(2023, 7, 21, 10, 26, 0)

        # Test 13: Timestamp type with bad string (should keep original)
        row_timestamp_bad = {'event_time': 'not-a-timestamp'}
        result_timestamp_bad = engine._convert_row_to_schema_types(
            row_timestamp_bad, schema_timestamp
        )
        assert (
            result_timestamp_bad['event_time'] == 'not-a-timestamp'
        )  # Should keep original on error
