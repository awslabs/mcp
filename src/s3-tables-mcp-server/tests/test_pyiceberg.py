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

    # Create a real PyArrow schema
    arrow_schema = pa.schema(
        [pa.field('id', pa.int64()), pa.field('name', pa.string()), pa.field('age', pa.int64())]
    )

    # Mock the table schema
    mock_iceberg_schema = MagicMock()
    mock_iceberg_schema.as_arrow.return_value = arrow_schema
    mock_table.schema.return_value = mock_iceberg_schema

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
    ):
        # Create the engine
        engine = PyIcebergEngine(config)

        # Append rows to the table
        engine.append_rows(table_name, rows)

        # Verify the catalog was used to load the table with the correct full name
        expected_full_table_name = f'{config.namespace}.{table_name}'
        mock_catalog.load_table.assert_called_once_with(expected_full_table_name)

        # Verify the table append was called
        mock_table.append.assert_called_once()


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

    # Create a real PyArrow schema with mismatched types to trigger error
    arrow_schema = pa.schema(
        [
            pa.field('id', pa.string()),  # Mismatched type - expecting string but getting int
            pa.field('name', pa.string()),
            pa.field('age', pa.string()),  # Mismatched type
        ]
    )

    # Mock the table schema
    mock_iceberg_schema = MagicMock()
    mock_iceberg_schema.as_arrow.return_value = arrow_schema
    mock_table.schema.return_value = mock_iceberg_schema

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
    ):
        # Create the engine
        engine = PyIcebergEngine(config)

        # Test data
        table_name = 'test_table'
        rows = [{'id': 1, 'name': 'Alice', 'age': 30}, {'id': 2, 'name': 'Bob', 'age': 25}]

        # Verify that append_rows raises an Exception with the schema mismatch message
        with pytest.raises(Exception) as exc_info:
            engine.append_rows(table_name, rows)

        # Verify the error message contains the wrapper text
        assert 'Error appending rows' in str(exc_info.value)

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

    # Create a real PyArrow schema
    arrow_schema = pa.schema(
        [pa.field('id', pa.int64()), pa.field('name', pa.string()), pa.field('age', pa.int64())]
    )

    # Mock the table schema
    mock_iceberg_schema = MagicMock()
    mock_iceberg_schema.as_arrow.return_value = arrow_schema
    mock_table.schema.return_value = mock_iceberg_schema

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
    ):
        # Create the engine
        engine = PyIcebergEngine(config)

        # Append rows to the table
        engine.append_rows(table_name, rows)

        # Verify the catalog was used to load the table with the original table name (no namespace prepending)
        # This tests the else branch where full_table_name = table_name
        mock_catalog.load_table.assert_called_once_with(table_name)

        # Verify the table append was called
        mock_table.append.assert_called_once()


@pytest.mark.asyncio
async def test_convert_temporal_fields_date():
    """Test convert_temporal_fields converts date strings correctly."""
    from awslabs.s3_tables_mcp_server.engines.pyiceberg import convert_temporal_fields
    from datetime import date

    arrow_schema = pa.schema([pa.field('id', pa.int64()), pa.field('birth_date', pa.date32())])

    rows = [
        {'id': 1, 'birth_date': '2025-03-14'},
        {'id': 2, 'birth_date': '1990-01-01'},
    ]

    converted = convert_temporal_fields(rows, arrow_schema)

    assert converted[0]['id'] == 1
    assert converted[0]['birth_date'] == date(2025, 3, 14)
    assert converted[1]['id'] == 2
    assert converted[1]['birth_date'] == date(1990, 1, 1)


@pytest.mark.asyncio
async def test_convert_temporal_fields_time():
    """Test convert_temporal_fields converts time strings correctly."""
    from awslabs.s3_tables_mcp_server.engines.pyiceberg import convert_temporal_fields
    from datetime import time

    arrow_schema = pa.schema([pa.field('id', pa.int64()), pa.field('event_time', pa.time64('us'))])

    rows = [
        {'id': 1, 'event_time': '17:10:34.123456'},
        {'id': 2, 'event_time': '09:23:47'},
    ]

    converted = convert_temporal_fields(rows, arrow_schema)

    assert converted[0]['id'] == 1
    assert converted[0]['event_time'] == time(17, 10, 34, 123456)
    assert converted[1]['id'] == 2
    assert converted[1]['event_time'] == time(9, 23, 47)


@pytest.mark.asyncio
async def test_convert_temporal_fields_timestamp_no_tz():
    """Test convert_temporal_fields converts timestamp without timezone correctly."""
    from awslabs.s3_tables_mcp_server.engines.pyiceberg import convert_temporal_fields
    from datetime import datetime

    arrow_schema = pa.schema(
        [pa.field('id', pa.int64()), pa.field('created_at', pa.timestamp('us'))]
    )

    rows = [
        {'id': 1, 'created_at': '2025-03-14 17:10:34.123456'},
        {'id': 2, 'created_at': '2025-03-14T17:10:34'},
        {'id': 3, 'created_at': '2025-03-14 17:10:34'},
    ]

    converted = convert_temporal_fields(rows, arrow_schema)

    assert converted[0]['created_at'] == datetime(2025, 3, 14, 17, 10, 34, 123456)
    assert converted[1]['created_at'] == datetime(2025, 3, 14, 17, 10, 34)
    assert converted[2]['created_at'] == datetime(2025, 3, 14, 17, 10, 34)


@pytest.mark.asyncio
async def test_convert_temporal_fields_timestamp_with_tz():
    """Test convert_temporal_fields converts timestamp with timezone correctly."""
    from awslabs.s3_tables_mcp_server.engines.pyiceberg import convert_temporal_fields
    from datetime import datetime, timezone

    arrow_schema = pa.schema(
        [pa.field('id', pa.int64()), pa.field('created_at', pa.timestamp('us', tz='UTC'))]
    )

    rows = [
        {'id': 1, 'created_at': '2025-03-14 17:10:34.123456+00:00'},
        {'id': 2, 'created_at': '2025-03-14T17:10:34+00:00'},
    ]

    converted = convert_temporal_fields(rows, arrow_schema)

    expected_dt1 = datetime(2025, 3, 14, 17, 10, 34, 123456, tzinfo=timezone.utc)
    expected_dt2 = datetime(2025, 3, 14, 17, 10, 34, tzinfo=timezone.utc)

    assert converted[0]['created_at'] == expected_dt1
    assert converted[1]['created_at'] == expected_dt2


@pytest.mark.asyncio
async def test_convert_temporal_fields_nanosecond_truncation():
    """Test convert_temporal_fields truncates nanoseconds to microseconds."""
    from awslabs.s3_tables_mcp_server.engines.pyiceberg import convert_temporal_fields
    from datetime import datetime

    arrow_schema = pa.schema(
        [pa.field('id', pa.int64()), pa.field('created_at', pa.timestamp('us'))]
    )

    rows = [
        {'id': 1, 'created_at': '2025-03-14 17:10:34.123456789'},
    ]

    converted = convert_temporal_fields(rows, arrow_schema)

    # Nanoseconds should be truncated to microseconds
    assert converted[0]['created_at'] == datetime(2025, 3, 14, 17, 10, 34, 123456)


@pytest.mark.asyncio
async def test_convert_temporal_fields_non_string_passthrough():
    """Test convert_temporal_fields passes through non-string values."""
    from awslabs.s3_tables_mcp_server.engines.pyiceberg import convert_temporal_fields
    from datetime import date, datetime

    arrow_schema = pa.schema(
        [
            pa.field('id', pa.int64()),
            pa.field('birth_date', pa.date32()),
            pa.field('created_at', pa.timestamp('us')),
        ]
    )

    # Already converted values
    existing_date = date(2025, 3, 14)
    existing_datetime = datetime(2025, 3, 14, 17, 10, 34)

    rows = [
        {'id': 1, 'birth_date': existing_date, 'created_at': existing_datetime},
        {'id': None, 'birth_date': None, 'created_at': None},
    ]

    converted = convert_temporal_fields(rows, arrow_schema)

    assert converted[0]['birth_date'] is existing_date
    assert converted[0]['created_at'] is existing_datetime
    assert converted[1]['id'] is None
    assert converted[1]['birth_date'] is None
    assert converted[1]['created_at'] is None


@pytest.mark.asyncio
async def test_convert_temporal_fields_mixed_types():
    """Test convert_temporal_fields handles mixed temporal and non-temporal fields."""
    from awslabs.s3_tables_mcp_server.engines.pyiceberg import convert_temporal_fields
    from datetime import date, datetime, time

    arrow_schema = pa.schema(
        [
            pa.field('id', pa.int64()),
            pa.field('name', pa.string()),
            pa.field('birth_date', pa.date32()),
            pa.field('event_time', pa.time64('us')),
            pa.field('created_at', pa.timestamp('us')),
            pa.field('score', pa.float64()),
        ]
    )

    rows = [
        {
            'id': 1,
            'name': 'Alice',
            'birth_date': '2025-03-14',
            'event_time': '17:10:34',
            'created_at': '2025-03-14 17:10:34',
            'score': 95.5,
        }
    ]

    converted = convert_temporal_fields(rows, arrow_schema)

    assert converted[0]['id'] == 1
    assert converted[0]['name'] == 'Alice'
    assert converted[0]['birth_date'] == date(2025, 3, 14)
    assert converted[0]['event_time'] == time(17, 10, 34)
    assert converted[0]['created_at'] == datetime(2025, 3, 14, 17, 10, 34)
    assert converted[0]['score'] == 95.5


@pytest.mark.asyncio
async def test_convert_temporal_fields_invalid_timestamp_tz():
    """Test convert_temporal_fields raises error for invalid timestamp with timezone."""
    from awslabs.s3_tables_mcp_server.engines.pyiceberg import convert_temporal_fields

    arrow_schema = pa.schema(
        [pa.field('id', pa.int64()), pa.field('created_at', pa.timestamp('us', tz='UTC'))]
    )

    rows = [
        {'id': 1, 'created_at': 'invalid-timestamp'},
    ]

    with pytest.raises(ValueError) as exc_info:
        convert_temporal_fields(rows, arrow_schema)

    assert 'Could not parse timestamp with timezone' in str(exc_info.value)
    assert 'invalid-timestamp' in str(exc_info.value)


@pytest.mark.asyncio
async def test_convert_temporal_fields_all_formats():
    """Test convert_temporal_fields with all supported temporal formats."""
    from awslabs.s3_tables_mcp_server.engines.pyiceberg import convert_temporal_fields
    from datetime import date, datetime, time, timezone

    # Test all temporal formats in one comprehensive test
    arrow_schema = pa.schema(
        [
            pa.field('id', pa.int64()),
            pa.field('date_field', pa.date32()),
            pa.field('time_field', pa.time64('us')),
            pa.field('timestamp_field', pa.timestamp('us')),
            pa.field('timestamptz_field', pa.timestamp('us', tz='UTC')),
            pa.field('timestamp_ns_field', pa.timestamp('ns')),
            pa.field('timestamptz_ns_field', pa.timestamp('ns', tz='UTC')),
        ]
    )

    rows = [
        {
            'id': 1,
            'date_field': '2025-03-14',
            'time_field': '17:10:34.123456',
            'timestamp_field': '2025-03-14 17:10:34.123456',
            'timestamptz_field': '2025-03-14 17:10:34.123456-07:00',
            'timestamp_ns_field': '2025-03-14 17:10:34.123456789',
            'timestamptz_ns_field': '2025-03-14 17:10:34.123456789-07:00',
        }
    ]

    converted = convert_temporal_fields(rows, arrow_schema)

    # Verify date
    assert converted[0]['date_field'] == date(2025, 3, 14)

    # Verify time
    assert converted[0]['time_field'] == time(17, 10, 34, 123456)

    # Verify timestamp without timezone
    assert converted[0]['timestamp_field'] == datetime(2025, 3, 14, 17, 10, 34, 123456)

    # Verify timestamptz - should be converted to UTC
    # Input: 2025-03-14 17:10:34.123456-07:00
    # Expected UTC: 2025-03-15 00:10:34.123456+00:00
    expected_timestamptz = datetime(2025, 3, 15, 0, 10, 34, 123456, tzinfo=timezone.utc)
    assert converted[0]['timestamptz_field'] == expected_timestamptz

    # Verify timestamp_ns - nanoseconds truncated to microseconds
    assert converted[0]['timestamp_ns_field'] == datetime(2025, 3, 14, 17, 10, 34, 123456)

    # Verify timestamptz_ns - nanoseconds truncated and converted to UTC
    expected_timestamptz_ns = datetime(2025, 3, 15, 0, 10, 34, 123456, tzinfo=timezone.utc)
    assert converted[0]['timestamptz_ns_field'] == expected_timestamptz_ns


@pytest.mark.asyncio
async def test_convert_temporal_fields_date_format():
    """Test date format: 2025-03-14."""
    from awslabs.s3_tables_mcp_server.engines.pyiceberg import convert_temporal_fields
    from datetime import date

    arrow_schema = pa.schema([pa.field('date_col', pa.date32())])
    rows = [{'date_col': '2025-03-14'}]

    converted = convert_temporal_fields(rows, arrow_schema)

    assert converted[0]['date_col'] == date(2025, 3, 14)


@pytest.mark.asyncio
async def test_convert_temporal_fields_time_format():
    """Test time format: 17:10:34.123456."""
    from awslabs.s3_tables_mcp_server.engines.pyiceberg import convert_temporal_fields
    from datetime import time

    arrow_schema = pa.schema([pa.field('time_col', pa.time64('us'))])
    rows = [{'time_col': '17:10:34.123456'}]

    converted = convert_temporal_fields(rows, arrow_schema)

    assert converted[0]['time_col'] == time(17, 10, 34, 123456)


@pytest.mark.asyncio
async def test_convert_temporal_fields_timestamp_format():
    """Test timestamp format: 2025-03-14 17:10:34.123456."""
    from awslabs.s3_tables_mcp_server.engines.pyiceberg import convert_temporal_fields
    from datetime import datetime

    arrow_schema = pa.schema([pa.field('ts_col', pa.timestamp('us'))])
    rows = [{'ts_col': '2025-03-14 17:10:34.123456'}]

    converted = convert_temporal_fields(rows, arrow_schema)

    assert converted[0]['ts_col'] == datetime(2025, 3, 14, 17, 10, 34, 123456)


@pytest.mark.asyncio
async def test_convert_temporal_fields_timestamptz_format():
    """Test timestamptz format: 2025-03-14 17:10:34.123456-07:00.

    Input: 2025-03-14 17:10:34.123456-07:00 (PDT)
    Expected UTC: 2025-03-15 00:10:34.123456+00:00
    """
    from awslabs.s3_tables_mcp_server.engines.pyiceberg import convert_temporal_fields
    from datetime import datetime, timezone

    arrow_schema = pa.schema([pa.field('tstz_col', pa.timestamp('us', tz='UTC'))])
    rows = [{'tstz_col': '2025-03-14 17:10:34.123456-07:00'}]

    converted = convert_temporal_fields(rows, arrow_schema)

    # Should be converted to UTC: 2025-03-15 00:10:34.123456+00:00
    expected = datetime(2025, 3, 15, 0, 10, 34, 123456, tzinfo=timezone.utc)
    assert converted[0]['tstz_col'] == expected


@pytest.mark.asyncio
async def test_convert_temporal_fields_timestamp_ns_format():
    """Test timestamp_ns format: 2025-03-14 17:10:34.123456789.

    Nanoseconds should be truncated to microseconds for Python datetime.
    """
    from awslabs.s3_tables_mcp_server.engines.pyiceberg import convert_temporal_fields
    from datetime import datetime

    arrow_schema = pa.schema([pa.field('ts_ns_col', pa.timestamp('ns'))])
    rows = [{'ts_ns_col': '2025-03-14 17:10:34.123456789'}]

    converted = convert_temporal_fields(rows, arrow_schema)

    # Nanoseconds truncated to microseconds
    assert converted[0]['ts_ns_col'] == datetime(2025, 3, 14, 17, 10, 34, 123456)


@pytest.mark.asyncio
async def test_convert_temporal_fields_timestamptz_ns_format():
    """Test timestamptz_ns format: 2025-03-14 17:10:34.123456789-07:00.

    Input: 2025-03-14 17:10:34.123456789-07:00 (PDT, nanosecond precision)
    Expected UTC: 2025-03-15 00:10:34.123456+00:00 (truncated to microseconds)
    """
    from awslabs.s3_tables_mcp_server.engines.pyiceberg import convert_temporal_fields
    from datetime import datetime, timezone

    arrow_schema = pa.schema([pa.field('tstz_ns_col', pa.timestamp('ns', tz='UTC'))])
    rows = [{'tstz_ns_col': '2025-03-14 17:10:34.123456789-07:00'}]

    converted = convert_temporal_fields(rows, arrow_schema)

    # Should be converted to UTC with nanoseconds truncated to microseconds
    expected = datetime(2025, 3, 15, 0, 10, 34, 123456, tzinfo=timezone.utc)
    assert converted[0]['tstz_ns_col'] == expected


@pytest.mark.asyncio
async def test_convert_temporal_fields_timestamptz_various_offsets():
    """Test timestamptz with various timezone offsets."""
    from awslabs.s3_tables_mcp_server.engines.pyiceberg import convert_temporal_fields
    from datetime import datetime, timezone

    arrow_schema = pa.schema(
        [pa.field('id', pa.int64()), pa.field('tstz_col', pa.timestamp('us', tz='UTC'))]
    )

    rows = [
        # UTC (no offset)
        {'id': 1, 'tstz_col': '2025-03-14 17:10:34.123456+00:00'},
        # PDT (-07:00)
        {'id': 2, 'tstz_col': '2025-03-14 17:10:34.123456-07:00'},
        # EST (-05:00)
        {'id': 3, 'tstz_col': '2025-03-14 17:10:34.123456-05:00'},
        # CET (+01:00)
        {'id': 4, 'tstz_col': '2025-03-14 17:10:34.123456+01:00'},
        # JST (+09:00)
        {'id': 5, 'tstz_col': '2025-03-14 17:10:34.123456+09:00'},
    ]

    converted = convert_temporal_fields(rows, arrow_schema)

    # All should be converted to UTC
    assert converted[0]['tstz_col'] == datetime(
        2025, 3, 14, 17, 10, 34, 123456, tzinfo=timezone.utc
    )
    assert converted[1]['tstz_col'] == datetime(
        2025, 3, 15, 0, 10, 34, 123456, tzinfo=timezone.utc
    )
    assert converted[2]['tstz_col'] == datetime(
        2025, 3, 14, 22, 10, 34, 123456, tzinfo=timezone.utc
    )
    assert converted[3]['tstz_col'] == datetime(
        2025, 3, 14, 16, 10, 34, 123456, tzinfo=timezone.utc
    )
    assert converted[4]['tstz_col'] == datetime(
        2025, 3, 14, 8, 10, 34, 123456, tzinfo=timezone.utc
    )


@pytest.mark.asyncio
async def test_convert_temporal_fields_timestamp_t_separator():
    """Test timestamp with T separator: 2025-03-14T17:10:34.123456."""
    from awslabs.s3_tables_mcp_server.engines.pyiceberg import convert_temporal_fields
    from datetime import datetime

    arrow_schema = pa.schema([pa.field('ts_col', pa.timestamp('us'))])
    rows = [{'ts_col': '2025-03-14T17:10:34.123456'}]

    converted = convert_temporal_fields(rows, arrow_schema)

    assert converted[0]['ts_col'] == datetime(2025, 3, 14, 17, 10, 34, 123456)


@pytest.mark.asyncio
async def test_convert_temporal_fields_timestamptz_t_separator():
    """Test timestamptz with T separator: 2025-03-14T17:10:34.123456-07:00."""
    from awslabs.s3_tables_mcp_server.engines.pyiceberg import convert_temporal_fields
    from datetime import datetime, timezone

    arrow_schema = pa.schema([pa.field('tstz_col', pa.timestamp('us', tz='UTC'))])
    rows = [{'tstz_col': '2025-03-14T17:10:34.123456-07:00'}]

    converted = convert_temporal_fields(rows, arrow_schema)

    expected = datetime(2025, 3, 15, 0, 10, 34, 123456, tzinfo=timezone.utc)
    assert converted[0]['tstz_col'] == expected
