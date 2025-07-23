import pytest
from pyiceberg.exceptions import NoSuchTableError
from unittest.mock import MagicMock, patch


@pytest.mark.asyncio
async def test_import_parquet_to_table_success():
    """Test import_parquet_to_table successfully imports Parquet data into an existing table."""
    from awslabs.s3_tables_mcp_server.file_processor import parquet as parquet_mod

    warehouse = 'warehouse-arn'
    region = 'us-west-2'
    namespace = 'testns'
    table_name = 'testtable'
    s3_url = 's3://bucket/file.parquet'
    uri = 'https://s3tables.us-west-2.amazonaws.com/iceberg'
    catalog_name = 's3tablescatalog'
    rest_signing_name = 's3tables'
    rest_sigv4_enabled = 'true'

    # Mock objects
    mock_catalog = MagicMock()
    mock_table = MagicMock()
    mock_iceberg_schema = MagicMock()
    mock_iceberg_schema.fields = [MagicMock(name='col1'), MagicMock(name='col2')]
    mock_iceberg_schema.fields[0].name = 'col1'
    mock_iceberg_schema.fields[1].name = 'col2'
    mock_table.schema.return_value = mock_iceberg_schema
    mock_catalog.load_table.return_value = mock_table

    mock_s3_client = MagicMock()
    mock_s3_client.get_object.return_value = {
        'Body': MagicMock(read=MagicMock(return_value=b'data'))
    }

    mock_parquet_table = MagicMock()
    mock_parquet_table.schema.names = ['col1', 'col2']
    mock_parquet_table.num_rows = 42

    with (
        patch.object(
            parquet_mod, 'pyiceberg_load_catalog', return_value=mock_catalog
        ) as mock_load_catalog,
        patch.object(
            parquet_mod, 'get_s3_client', return_value=mock_s3_client
        ) as mock_get_s3_client,
        patch('pyarrow.parquet.read_table', return_value=mock_parquet_table) as mock_read_parquet,
    ):
        result = await parquet_mod.import_parquet_to_table(
            warehouse=warehouse,
            region=region,
            namespace=namespace,
            table_name=table_name,
            s3_url=s3_url,
            uri=uri,
            catalog_name=catalog_name,
            rest_signing_name=rest_signing_name,
            rest_sigv4_enabled=rest_sigv4_enabled,
        )
        assert result['status'] == 'success'
        assert result['rows_processed'] == 42
        assert result['file_processed'] == 'file.parquet'
        assert result['table_created'] is False
        assert 'Successfully imported' in result['message']
        mock_load_catalog.assert_called_once()
        mock_get_s3_client.assert_called_once()
        mock_read_parquet.assert_called_once()
        mock_table.append.assert_called_once_with(mock_parquet_table)


@pytest.mark.asyncio
async def test_import_parquet_to_table_create_new_table():
    """Test import_parquet_to_table successfully creates a new table when it doesn't exist."""
    from awslabs.s3_tables_mcp_server.file_processor import parquet as parquet_mod

    warehouse = 'warehouse-arn'
    region = 'us-west-2'
    namespace = 'testns'
    table_name = 'testtable'
    s3_url = 's3://bucket/file.parquet'
    uri = 'https://s3tables.us-west-2.amazonaws.com/iceberg'
    catalog_name = 's3tablescatalog'
    rest_signing_name = 's3tables'
    rest_sigv4_enabled = 'true'

    # Mock objects
    mock_catalog = MagicMock()
    mock_table = MagicMock()

    # Mock load_table to raise NoSuchTableError (table doesn't exist)
    mock_catalog.load_table.side_effect = NoSuchTableError('Table not found')
    # Mock create_table to return the new table
    mock_catalog.create_table.return_value = mock_table

    mock_s3_client = MagicMock()
    mock_s3_client.get_object.return_value = {
        'Body': MagicMock(read=MagicMock(return_value=b'data'))
    }

    mock_parquet_table = MagicMock()
    mock_parquet_table.schema.names = ['col1', 'col2']
    mock_parquet_table.num_rows = 42
    mock_parquet_schema = MagicMock()
    mock_parquet_table.schema = mock_parquet_schema

    with (
        patch.object(
            parquet_mod, 'pyiceberg_load_catalog', return_value=mock_catalog
        ) as mock_load_catalog,
        patch.object(
            parquet_mod, 'get_s3_client', return_value=mock_s3_client
        ) as mock_get_s3_client,
        patch('pyarrow.parquet.read_table', return_value=mock_parquet_table) as mock_read_parquet,
    ):
        result = await parquet_mod.import_parquet_to_table(
            warehouse=warehouse,
            region=region,
            namespace=namespace,
            table_name=table_name,
            s3_url=s3_url,
            uri=uri,
            catalog_name=catalog_name,
            rest_signing_name=rest_signing_name,
            rest_sigv4_enabled=rest_sigv4_enabled,
        )

        assert result['status'] == 'success'
        assert result['rows_processed'] == 42
        assert result['file_processed'] == 'file.parquet'
        assert result['table_created'] is True
        assert 'Successfully imported' in result['message']
        assert 'created new table' in result['message']
        mock_load_catalog.assert_called_once()
        mock_get_s3_client.assert_called_once()
        mock_read_parquet.assert_called_once()
        mock_catalog.create_table.assert_called_once_with(
            identifier=f'{namespace}.{table_name}', schema=mock_parquet_schema
        )
        mock_table.append.assert_called_once_with(mock_parquet_table)


@pytest.mark.asyncio
async def test_import_parquet_to_table_create_table_error():
    """Test import_parquet_to_table returns error when table creation fails."""
    from awslabs.s3_tables_mcp_server.file_processor import parquet as parquet_mod

    warehouse = 'warehouse-arn'
    region = 'us-west-2'
    namespace = 'testns'
    table_name = 'testtable'
    s3_url = 's3://bucket/file.parquet'
    uri = 'https://s3tables.us-west-2.amazonaws.com/iceberg'
    catalog_name = 's3tablescatalog'
    rest_signing_name = 's3tables'
    rest_sigv4_enabled = 'true'

    # Mock objects
    mock_catalog = MagicMock()

    # Mock load_table to raise NoSuchTableError (table doesn't exist)
    mock_catalog.load_table.side_effect = NoSuchTableError('Table not found')
    # Mock create_table to raise an exception (table creation fails)
    mock_catalog.create_table.side_effect = Exception('Permission denied')

    mock_s3_client = MagicMock()
    mock_s3_client.get_object.return_value = {
        'Body': MagicMock(read=MagicMock(return_value=b'data'))
    }

    mock_parquet_table = MagicMock()
    mock_parquet_table.schema.names = ['col1', 'col2']
    mock_parquet_table.num_rows = 42
    mock_parquet_schema = MagicMock()
    mock_parquet_table.schema = mock_parquet_schema

    with (
        patch.object(
            parquet_mod, 'pyiceberg_load_catalog', return_value=mock_catalog
        ) as mock_load_catalog,
        patch.object(
            parquet_mod, 'get_s3_client', return_value=mock_s3_client
        ) as mock_get_s3_client,
        patch('pyarrow.parquet.read_table', return_value=mock_parquet_table) as mock_read_parquet,
    ):
        result = await parquet_mod.import_parquet_to_table(
            warehouse=warehouse,
            region=region,
            namespace=namespace,
            table_name=table_name,
            s3_url=s3_url,
            uri=uri,
            catalog_name=catalog_name,
            rest_signing_name=rest_signing_name,
            rest_sigv4_enabled=rest_sigv4_enabled,
        )

        assert result['status'] == 'error'
        assert 'Failed to create table' in result['error']
        assert 'Permission denied' in result['error']
        mock_load_catalog.assert_called_once()
        mock_get_s3_client.assert_called_once()
        mock_read_parquet.assert_called_once()
        mock_catalog.create_table.assert_called_once_with(
            identifier=f'{namespace}.{table_name}', schema=mock_parquet_schema
        )


@pytest.mark.asyncio
async def test_import_parquet_to_table_general_exception():
    """Test import_parquet_to_table returns error when a general exception occurs."""
    from awslabs.s3_tables_mcp_server.file_processor import parquet as parquet_mod

    warehouse = 'warehouse-arn'
    region = 'us-west-2'
    namespace = 'testns'
    table_name = 'testtable'
    s3_url = 's3://bucket/file.parquet'
    uri = 'https://s3tables.us-west-2.amazonaws.com/iceberg'
    catalog_name = 's3tablescatalog'
    rest_signing_name = 's3tables'
    rest_sigv4_enabled = 'true'

    # Mock pyiceberg_load_catalog to raise a general exception
    with patch.object(
        parquet_mod, 'pyiceberg_load_catalog', side_effect=Exception('Connection timeout')
    ) as mock_load_catalog:
        result = await parquet_mod.import_parquet_to_table(
            warehouse=warehouse,
            region=region,
            namespace=namespace,
            table_name=table_name,
            s3_url=s3_url,
            uri=uri,
            catalog_name=catalog_name,
            rest_signing_name=rest_signing_name,
            rest_sigv4_enabled=rest_sigv4_enabled,
        )

        assert result['status'] == 'error'
        assert result['error'] == 'Connection timeout'
        mock_load_catalog.assert_called_once()
