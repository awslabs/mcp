import pyarrow as pa
import pytest
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

    # Create a real PyArrow table that matches our test data
    real_pyarrow_table = pa.table(
        {'id': [1, 2, 3], 'name': ['Alice', 'Bob', 'Charlie'], 'age': [30, 25, 35]}
    )

    # Mock the catalog to return the table
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
        patch(
            'awslabs.s3_tables_mcp_server.engines.pyiceberg.pj.read_json',
            return_value=real_pyarrow_table,
        ),
    ):
        # Create the engine
        engine = PyIcebergEngine(config)

        # Append rows to the table
        engine.append_rows(table_name, rows)

        # Verify the catalog was used to load the table with the correct full name
        expected_full_table_name = f'{config.namespace}.{table_name}'
        mock_catalog.load_table.assert_called_once_with(expected_full_table_name)

        # Verify the table append was called with the PyArrow table
        mock_table.append.assert_called_once_with(real_pyarrow_table)


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

    # Mock the catalog to return the table
    mock_catalog.load_table.return_value = mock_table

    # Mock the catalog loading and session creation
    with (
        patch(
            'awslabs.s3_tables_mcp_server.engines.pyiceberg.pyiceberg_load_catalog',
            return_value=mock_catalog,
        ),
        patch('awslabs.s3_tables_mcp_server.engines.pyiceberg.Session', return_value=mock_session),
        patch('awslabs.s3_tables_mcp_server.engines.pyiceberg.DaftCatalog'),
        patch(
            'awslabs.s3_tables_mcp_server.engines.pyiceberg.pj.read_json',
            side_effect=pa.ArrowInvalid('Schema mismatch detected'),
        ),
    ):
        # Create the engine
        engine = PyIcebergEngine(config)

        # Test data
        table_name = 'test_table'
        rows = [{'id': 1, 'name': 'Alice', 'age': 30}, {'id': 2, 'name': 'Bob', 'age': 25}]

        # Verify that append_rows raises an Exception with the schema mismatch message
        with pytest.raises(Exception) as exc_info:
            engine.append_rows(table_name, rows)

        # Verify the error message contains the wrapper text and schema mismatch information
        assert 'Error appending rows' in str(exc_info.value)
        assert 'Schema mismatch detected' in str(exc_info.value)

        # Verify that the catalog operations were attempted before the exception
        expected_full_table_name = f'{config.namespace}.{table_name}'
        mock_catalog.load_table.assert_called_once_with(expected_full_table_name)


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

    # Create a real PyArrow table that matches our test data
    real_pyarrow_table = pa.table(
        {'id': [1, 2, 3], 'name': ['Alice', 'Bob', 'Charlie'], 'age': [30, 25, 35]}
    )

    # Mock the catalog to return the table
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
        patch(
            'awslabs.s3_tables_mcp_server.engines.pyiceberg.pj.read_json',
            return_value=real_pyarrow_table,
        ),
    ):
        # Create the engine
        engine = PyIcebergEngine(config)

        # Append rows to the table
        engine.append_rows(table_name, rows)

        # Verify the catalog was used to load the table with the original table name (no namespace prepending)
        # This tests the else branch where full_table_name = table_name
        mock_catalog.load_table.assert_called_once_with(table_name)

        # Verify the table append was called with the PyArrow table
        mock_table.append.assert_called_once_with(real_pyarrow_table)
