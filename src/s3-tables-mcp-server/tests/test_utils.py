import awslabs.s3_tables_mcp_server.utils as utils
from unittest.mock import MagicMock, patch


def test_handle_exceptions_success():
    """Test that handle_exceptions decorator returns the correct result when no exception is raised."""

    @utils.handle_exceptions
    async def good_func(x):
        return x * 2

    import asyncio

    result = asyncio.get_event_loop().run_until_complete(good_func(3))
    assert result == 6


def test_handle_exceptions_exception():
    """Test that handle_exceptions decorator catches exceptions and returns an error dict."""

    @utils.handle_exceptions
    async def bad_func(x):
        raise ValueError('fail')

    import asyncio

    result = asyncio.get_event_loop().run_until_complete(bad_func(1))
    assert result['error'] == 'fail'
    assert result['tool'] == 'bad_func'


def test_get_s3tables_client():
    """Test get_s3tables_client returns a boto3 client with correct parameters."""
    with (
        patch('awslabs.s3_tables_mcp_server.utils.boto3.Session') as mock_session,
        patch('awslabs.s3_tables_mcp_server.utils.Config') as mock_config,
    ):
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client
        # Patch __version__ directly
        utils.__version__ = '1.2.3'
        client = utils.get_s3tables_client(region_name='eu-west-1')
        mock_session.return_value.client.assert_called_once_with(
            's3tables', region_name='eu-west-1', config=mock_config()
        )
        assert client == mock_client


def test_get_s3_client():
    """Test get_s3_client returns a boto3 S3 client with default region if not specified."""
    with (
        patch('awslabs.s3_tables_mcp_server.utils.boto3.Session') as mock_session,
        patch('awslabs.s3_tables_mcp_server.utils.Config') as mock_config,
    ):
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client
        utils.__version__ = '1.2.3'
        client = utils.get_s3_client(region_name=None)
        mock_session.return_value.client.assert_called_once_with(
            's3', region_name='us-east-1', config=mock_config()
        )
        assert client == mock_client


def test_get_sts_client_env(monkeypatch):
    """Test get_sts_client uses AWS_REGION from environment if region_name is None."""
    with (
        patch('awslabs.s3_tables_mcp_server.utils.boto3.Session') as mock_session,
        patch('awslabs.s3_tables_mcp_server.utils.Config') as mock_config,
    ):
        monkeypatch.setenv('AWS_REGION', 'ap-south-1')
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client
        utils.__version__ = '1.2.3'
        client = utils.get_sts_client(region_name=None)
        mock_session.return_value.client.assert_called_once_with(
            'sts', region_name='ap-south-1', config=mock_config()
        )
        assert client == mock_client


def test_get_athena_client_default():
    """Test get_athena_client returns a boto3 Athena client with default region if not specified."""
    with (
        patch('awslabs.s3_tables_mcp_server.utils.boto3.Session') as mock_session,
        patch('awslabs.s3_tables_mcp_server.utils.Config') as mock_config,
    ):
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client
        utils.__version__ = '1.2.3'
        client = utils.get_athena_client()
        mock_session.return_value.client.assert_called_once_with(
            'athena', region_name='us-east-1', config=mock_config()
        )
        assert client == mock_client


def test_pyiceberg_load_catalog(monkeypatch):
    """Test pyiceberg_load_catalog loads catalog and sets custom User-Agent header."""
    # Patch the load_catalog function in the pyiceberg.catalog module
    with patch('pyiceberg.catalog.load_catalog') as mock_load_catalog:
        mock_catalog = MagicMock()
        mock_load_catalog.return_value = mock_catalog
        # Simulate _session.headers as a dict
        mock_catalog._session = MagicMock()
        mock_catalog._session.headers = {}
        utils.__version__ = '1.2.3'
        result = utils.pyiceberg_load_catalog(
            catalog_name='cat',
            warehouse='wh',
            uri='http://uri',
            region='eu-west-1',
            rest_signing_name='foo',
            rest_sigv4_enabled='false',
        )
        mock_load_catalog.assert_called_once()
        assert result == mock_catalog
        assert (
            mock_catalog._session.headers['User-Agent']
            == 'awslabs/mcp/s3-tables-mcp-server/1.2.3/ro'
        )
