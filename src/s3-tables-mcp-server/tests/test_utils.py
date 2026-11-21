import awslabs.s3_tables_mcp_server.utils as utils
import os
import pytest
from unittest.mock import MagicMock, patch


@pytest.mark.asyncio
async def test_handle_exceptions_success():
    """Test that handle_exceptions decorator returns the correct result when no exception is raised."""

    @utils.handle_exceptions
    async def good_func(x):
        return x * 2

    result = await good_func(3)
    assert result == 6


@pytest.mark.asyncio
async def test_handle_exceptions_exception():
    """Test that handle_exceptions decorator catches exceptions and returns an error dict."""

    @utils.handle_exceptions
    async def bad_func(x):
        raise ValueError('fail')

    result = await bad_func(1)
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


@pytest.fixture
def clean_endpoint_env(monkeypatch):
    """Isolate endpoint resolution from the developer's own AWS configuration."""
    for variable in (
        'AWS_USE_FIPS_ENDPOINT',
        'AWS_USE_DUALSTACK_ENDPOINT',
        'AWS_ENDPOINT_URL',
        'AWS_ENDPOINT_URL_S3TABLES',
        'AWS_REGION',
        'AWS_DEFAULT_REGION',
        'AWS_PROFILE',
        'AWS_DEFAULT_PROFILE',
    ):
        monkeypatch.delenv(variable, raising=False)
    monkeypatch.setenv('AWS_CONFIG_FILE', os.devnull)
    monkeypatch.setenv('AWS_SHARED_CREDENTIALS_FILE', os.devnull)
    return monkeypatch


@pytest.fixture
def captured_catalog_config():
    """Patch ``load_catalog`` and expose the keyword arguments it was called with."""
    with patch('pyiceberg.catalog.load_catalog') as mock_load_catalog:
        mock_catalog = MagicMock()
        mock_load_catalog.return_value = mock_catalog
        mock_catalog._session = MagicMock()
        mock_catalog._session.headers = {}
        yield mock_load_catalog


@pytest.mark.parametrize(
    ('region', 'expected_uri'),
    [
        ('eu-west-1', 'https://s3tables.eu-west-1.amazonaws.com/iceberg'),
        ('cn-north-1', 'https://s3tables.cn-north-1.amazonaws.com.cn/iceberg'),
        ('us-iso-east-1', 'https://s3tables.us-iso-east-1.c2s.ic.gov/iceberg'),
    ],
)
def test_pyiceberg_load_catalog(region, expected_uri, clean_endpoint_env, captured_catalog_config):
    """Test pyiceberg_load_catalog uses the partition endpoint and fixed SigV4 settings."""
    utils.__version__ = '1.2.3'
    result = utils.pyiceberg_load_catalog(
        catalog_name='cat',
        warehouse='wh',
        region=region,
    )
    captured_catalog_config.assert_called_once_with(
        'cat',
        **{
            'type': 'rest',
            'warehouse': 'wh',
            'uri': expected_uri,
            'rest.sigv4-enabled': 'true',
            'rest.signing-name': 's3tables',
            'rest.signing-region': region,
        },
    )
    assert result == captured_catalog_config.return_value
    assert (
        captured_catalog_config.return_value._session.headers['User-Agent']
        == 'md/awslabs#mcp#s3-tables-mcp-server#1.2.3 cfg/mode#ro'
    )


@pytest.mark.parametrize(
    ('environment', 'expected_uri'),
    [
        ({}, 'https://s3tables.us-west-2.amazonaws.com/iceberg'),
        (
            {'AWS_USE_FIPS_ENDPOINT': 'true'},
            'https://s3tables-fips.us-west-2.amazonaws.com/iceberg',
        ),
        (
            {'AWS_USE_DUALSTACK_ENDPOINT': 'true'},
            'https://s3tables.us-west-2.api.aws/iceberg',
        ),
        (
            {'AWS_ENDPOINT_URL_S3TABLES': 'https://s3tables.internal.example/'},
            'https://s3tables.internal.example/iceberg',
        ),
    ],
    ids=['standard', 'fips', 'dualstack', 'operator-endpoint'],
)
def test_pyiceberg_load_catalog_honors_operator_endpoint_configuration(
    environment, expected_uri, clean_endpoint_env, captured_catalog_config
):
    """Test trusted operator endpoint configuration selects the catalog destination.

    FIPS is the case that matters most: a FIPS-configured operator must not have
    catalog traffic silently sent to the standard endpoint. These settings come
    from the environment or AWS profile, never from MCP tool input.
    """
    for name, value in environment.items():
        clean_endpoint_env.setenv(name, value)

    utils.pyiceberg_load_catalog(catalog_name='cat', warehouse='wh', region='us-west-2')

    assert captured_catalog_config.call_args.kwargs['uri'] == expected_uri


@pytest.mark.parametrize(
    'environment', [{}, {'AWS_USE_FIPS_ENDPOINT': 'true'}], ids=['standard', 'fips']
)
def test_pyiceberg_load_catalog_endpoint_matches_s3tables_client(
    environment, clean_endpoint_env, captured_catalog_config
):
    """Test the catalog endpoint agrees with the S3 Tables client's own endpoint."""
    for name, value in environment.items():
        clean_endpoint_env.setenv(name, value)

    utils.pyiceberg_load_catalog(catalog_name='cat', warehouse='wh', region='us-west-2')

    client_endpoint = utils.get_s3tables_client('us-west-2').meta.endpoint_url
    assert captured_catalog_config.call_args.kwargs['uri'] == f'{client_endpoint}/iceberg'


def test_pyiceberg_load_catalog_signs_for_resolved_region(
    clean_endpoint_env, captured_catalog_config
):
    """Test the signing region matches the region the endpoint was resolved for."""
    clean_endpoint_env.setenv('AWS_REGION', 'eu-central-1')

    utils.pyiceberg_load_catalog(catalog_name='cat', warehouse='wh', region='')

    kwargs = captured_catalog_config.call_args.kwargs
    assert kwargs['uri'] == 'https://s3tables.eu-central-1.amazonaws.com/iceberg'
    assert kwargs['rest.signing-region'] == 'eu-central-1'


@pytest.mark.parametrize(
    'region',
    [
        'https://example.com',
        'us-west-2#@example.com',
        '192.0.2.1',
        'us-west-2/../other.example',
        'us west 2',
    ],
)
def test_pyiceberg_load_catalog_rejects_malformed_region(
    region, clean_endpoint_env, captured_catalog_config
):
    """Test region values that are not host labels fail before catalog loading.

    URLs, IP addresses, and anything else outside ``[A-Za-z0-9-]`` cannot
    reach PyIceberg, so no request is issued.
    """
    with pytest.raises(ValueError, match='Unable to resolve S3 Tables endpoint'):
        utils.pyiceberg_load_catalog(catalog_name='cat', warehouse='wh', region=region)

    captured_catalog_config.assert_not_called()


def test_pyiceberg_load_catalog_keeps_unknown_regions_on_aws_suffix(
    clean_endpoint_env, captured_catalog_config
):
    """Test a region-shaped but unknown value still resolves under an AWS-owned suffix.

    Endpoint resolution does not verify that a region exists, so the invariant
    this path guarantees is the destination suffix, not region validity.
    """
    utils.pyiceberg_load_catalog(catalog_name='cat', warehouse='wh', region='us-fake-1')

    assert (
        captured_catalog_config.call_args.kwargs['uri']
        == 'https://s3tables.us-fake-1.amazonaws.com/iceberg'
    )
