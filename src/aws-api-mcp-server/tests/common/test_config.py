import awslabs.aws_api_mcp_server.core.common.config as config_module
import importlib
import pytest
from awslabs.aws_api_mcp_server.core.common.config import (
    FileAccessMode,
    get_file_access_mode,
    get_region,
    get_server_directory,
    get_transport_from_env,
    get_user_agent_extra,
)
from importlib.metadata import PackageNotFoundError
from unittest.mock import MagicMock, patch


@pytest.mark.parametrize(
    'os_name,uname_sysname,expected_tempdir',
    [
        ('nt', 'Windows', '/tmp'),
        ('posix', 'Darwin', '/private/var/folders/rq/'),
    ],
)
@patch('awslabs.aws_api_mcp_server.core.common.config.Path')
@patch('tempfile.gettempdir')
@patch('os.uname')
@patch('os.name')
def test_get_server_directory_windows_macos(
    mock_os_name: MagicMock,
    mock_uname: MagicMock,
    mock_tempdir: MagicMock,
    mock_path: MagicMock,
    os_name: str,
    uname_sysname: str,
    expected_tempdir: str,
):
    """Test get_server_directory for Windows and macOS platforms."""
    mock_os_name.return_value = os_name
    mock_uname.return_value.sysname = uname_sysname
    mock_tempdir.return_value = expected_tempdir

    mock_path_instance = MagicMock()
    mock_path_instance.__truediv__ = lambda self, other: f'{expected_tempdir}/{other}'
    mock_path_instance.__str__ = lambda: expected_tempdir
    mock_path.return_value = mock_path_instance

    result = get_server_directory()

    assert f'{expected_tempdir}/aws-api-mcp' in str(result)


@pytest.mark.parametrize(
    'aws_region,profile_name,profile_region,default_region,expected_region',
    [
        (
            'us-west-1',
            'profile1',
            'eu-west-1',
            'ap-south-1',
            'us-west-1',
        ),  # AWS_REGION takes precedence
        (None, 'profile1', 'eu-west-1', 'ap-south-1', 'eu-west-1'),  # Profile region used
        (None, 'profile1', None, 'ap-south-1', 'us-east-1'),  # Profile has no region, fallback
        (None, None, None, 'ap-south-1', 'ap-south-1'),  # Default session region used
        (None, None, None, None, 'us-east-1'),  # All None, fallback used
    ],
)
@patch('awslabs.aws_api_mcp_server.core.common.config.boto3.Session')
def test_get_region_parametrized(
    mock_session_class: MagicMock,
    aws_region: str,
    profile_name: str,
    profile_region: str,
    default_region: str,
    expected_region: str,
):
    """Parametrized test for various combinations of region sources."""
    profile_session = MagicMock()
    profile_session.region_name = profile_region

    default_session = MagicMock()
    default_session.region_name = default_region

    # Configure mock_session_class to return different sessions based on arguments
    def session_side_effect(*args, **kwargs):
        if 'profile_name' in kwargs:
            return profile_session
        return default_session

    mock_session_class.side_effect = session_side_effect

    with patch('awslabs.aws_api_mcp_server.core.common.config.AWS_REGION', aws_region):
        result = get_region(profile_name)

    assert result == expected_region


@pytest.mark.parametrize(
    'transport_value,expected',
    [
        ('stdio', 'stdio'),
        ('streamable-http', 'streamable-http'),
    ],
)
def test_get_transport_from_env_valid_values(monkeypatch, transport_value, expected):
    """Test get_transport_from_env with valid transport values."""
    monkeypatch.setenv('AWS_API_MCP_TRANSPORT', transport_value)

    # For streamable-http, AUTH_TYPE must be explicitly set to 'no-auth'
    if transport_value == 'streamable-http':
        monkeypatch.setenv('AUTH_TYPE', 'no-auth')
    else:
        monkeypatch.delenv('AUTH_TYPE', raising=False)

    result = get_transport_from_env()

    assert result == expected


def test_get_transport_from_env_default_value(monkeypatch):
    """Test get_transport_from_env returns default value when env var is not set."""
    # Ensure the environment variable is not set
    monkeypatch.delenv('AWS_API_MCP_TRANSPORT', raising=False)
    monkeypatch.delenv('AUTH_TYPE', raising=False)

    result = get_transport_from_env()

    assert result == 'stdio'


@pytest.mark.parametrize(
    'invalid_transport',
    [
        'http',
        'websocket',
        'tcp',
        'invalid',
        'STDIO',
        'STREAMABLE-HTTP',
        '',
        'stdio-http',
    ],
)
def test_get_transport_from_env_invalid_values(monkeypatch, invalid_transport):
    """Test get_transport_from_env raises ValueError for invalid transport values."""
    monkeypatch.setenv('AWS_API_MCP_TRANSPORT', invalid_transport)
    monkeypatch.delenv('AUTH_TYPE', raising=False)

    with pytest.raises(ValueError, match=f'Invalid transport: {invalid_transport}'):
        get_transport_from_env()


def test_get_transport_from_env_streamable_http_requires_auth_type(monkeypatch):
    """Ensure streamable-http transport fails without explicit AUTH_TYPE=no-auth."""
    monkeypatch.setenv('AWS_API_MCP_TRANSPORT', 'streamable-http')
    monkeypatch.delenv('AUTH_TYPE', raising=False)

    with pytest.raises(
        ValueError,
        match="requires AUTH_TYPE environment variable to be explicitly set to 'no-auth'",
    ):
        get_transport_from_env()


def test_get_transport_from_env_streamable_http_with_wrong_auth_type(monkeypatch):
    """Ensure streamable-http transport fails when AUTH_TYPE is not no-auth."""
    monkeypatch.setenv('AWS_API_MCP_TRANSPORT', 'streamable-http')
    monkeypatch.setenv('AUTH_TYPE', 'basic')

    with pytest.raises(
        ValueError,
        match="requires AUTH_TYPE environment variable to be explicitly set to 'no-auth'",
    ):
        get_transport_from_env()


def test_get_transport_from_env_streamable_http_with_no_auth(monkeypatch):
    """Ensure streamable-http transport succeeds when AUTH_TYPE=no-auth."""
    monkeypatch.setenv('AWS_API_MCP_TRANSPORT', 'streamable-http')
    monkeypatch.setenv('AUTH_TYPE', 'no-auth')

    assert get_transport_from_env() == 'streamable-http'


@patch('awslabs.aws_api_mcp_server.core.common.config.OPT_IN_TELEMETRY', False)
def test_user_agent_without_telemetry():
    """Test user agent when telemetry is disabled."""
    user_agent = get_user_agent_extra()
    assert 'cfg/ro#' not in user_agent
    assert 'cfg/consent#' not in user_agent
    assert 'cfg/scripts#' not in user_agent


@patch('awslabs.aws_api_mcp_server.core.common.config.get_context')
@patch('awslabs.aws_api_mcp_server.core.common.config.OPT_IN_TELEMETRY', False)
def test_user_agent_with_context(mock_get_context):
    """Test user agent when context is present."""
    # Create mock context with fastmcp name and client params
    mock_context = MagicMock()
    mock_context.fastmcp.name = 'test-fastmcp'
    mock_context.session.client_params.clientInfo.name = 'test-client'
    mock_context.session.client_params.clientInfo.version = '1.0.0'

    mock_get_context.return_value = mock_context

    user_agent = get_user_agent_extra()

    # Verify context information is included in user agent
    assert 'via/test-fastmcp' in user_agent
    assert 'MCPClient/test-client-1.0.0' in user_agent
    assert 'awslabs/mcp/AWS-API-MCP-server/' in user_agent


@patch('awslabs.aws_api_mcp_server.core.common.config.get_context')
@patch('awslabs.aws_api_mcp_server.core.common.config.OPT_IN_TELEMETRY', False)
def test_user_agent_with_context_no_client_params(mock_get_context):
    """Test user agent when context is present but client_params is None."""
    # Create mock context with fastmcp name but no client params
    mock_context = MagicMock()
    mock_context.fastmcp.name = 'test-fastmcp'
    mock_context.session.client_params = None

    mock_get_context.return_value = mock_context

    user_agent = get_user_agent_extra()

    # Verify fastmcp name is included but client info is not
    assert 'via/test-fastmcp' in user_agent
    assert 'MCPClient/' not in user_agent
    assert 'awslabs/mcp/AWS-API-MCP-server/' in user_agent


@patch('importlib.metadata.version')
def test_package_version_fallback_to_unknown(mock_version):
    """Test that PACKAGE_VERSION falls back to 'unknown' when package not found."""
    original_version = config_module.PACKAGE_VERSION

    mock_version.side_effect = PackageNotFoundError()
    importlib.reload(config_module)

    assert config_module.PACKAGE_VERSION == 'unknown'

    user_agent = config_module.get_user_agent_extra()
    assert 'awslabs/mcp/AWS-API-MCP-server/unknown' in user_agent

    # Restore original state
    config_module.PACKAGE_VERSION = original_version


@pytest.mark.parametrize(
    'env_value,expected_mode',
    [
        ('unrestricted', FileAccessMode.UNRESTRICTED),
        ('true', FileAccessMode.UNRESTRICTED),
        ('yes', FileAccessMode.UNRESTRICTED),
        ('1', FileAccessMode.UNRESTRICTED),
        ('Unrestricted', FileAccessMode.UNRESTRICTED),
        ('True', FileAccessMode.UNRESTRICTED),
        ('YES', FileAccessMode.UNRESTRICTED),
        ('TRUE', FileAccessMode.UNRESTRICTED),
    ],
)
def test_get_file_access_mode_unrestricted(monkeypatch, env_value, expected_mode):
    """Test that 'true', 'yes', '1' map to FileAccessMode.UNRESTRICTED (case-insensitive)."""
    monkeypatch.setenv('AWS_API_MCP_ALLOW_UNRESTRICTED_LOCAL_FILE_ACCESS', env_value)
    result = get_file_access_mode()
    assert result == expected_mode


@pytest.mark.parametrize(
    'env_value,expected_mode',
    [
        ('false', FileAccessMode.WORKDIR),
        ('no', FileAccessMode.WORKDIR),
        ('0', FileAccessMode.WORKDIR),
        ('workdir', FileAccessMode.WORKDIR),
        ('False', FileAccessMode.WORKDIR),
        ('NO', FileAccessMode.WORKDIR),
        ('WORKDIR', FileAccessMode.WORKDIR),
        ('Workdir', FileAccessMode.WORKDIR),
    ],
)
def test_get_file_access_mode_workdir(monkeypatch, env_value, expected_mode):
    """Test that 'false', 'no', '0', 'workdir' map to FileAccessMode.WORKDIR (case-insensitive)."""
    monkeypatch.setenv('AWS_API_MCP_ALLOW_UNRESTRICTED_LOCAL_FILE_ACCESS', env_value)
    result = get_file_access_mode()
    assert result == expected_mode


@pytest.mark.parametrize(
    'env_value,expected_mode',
    [
        ('no-access', FileAccessMode.NO_ACCESS),
        ('NO-ACCESS', FileAccessMode.NO_ACCESS),
        ('No-Access', FileAccessMode.NO_ACCESS),
    ],
)
def test_get_file_access_mode_no_access(monkeypatch, env_value, expected_mode):
    """Test that 'no-access' maps to FileAccessMode.NO_ACCESS (case-insensitive)."""
    monkeypatch.setenv('AWS_API_MCP_ALLOW_UNRESTRICTED_LOCAL_FILE_ACCESS', env_value)
    result = get_file_access_mode()
    assert result == expected_mode


def test_get_file_access_mode_default(monkeypatch):
    """Test that default value is FileAccessMode.WORKDIR when env var is not set."""
    monkeypatch.delenv('AWS_API_MCP_ALLOW_UNRESTRICTED_LOCAL_FILE_ACCESS', raising=False)
    result = get_file_access_mode()
    assert result == FileAccessMode.WORKDIR


@pytest.mark.parametrize(
    'env_value',
    [
        'invalid',
        'random',
        'unknown',
        '',
        'yes_access',
    ],
)
def test_get_file_access_mode_unknown_defaults_to_workdir(monkeypatch, env_value):
    """Test that unknown values default to FileAccessMode.WORKDIR."""
    monkeypatch.setenv('AWS_API_MCP_ALLOW_UNRESTRICTED_LOCAL_FILE_ACCESS', env_value)
    result = get_file_access_mode()
    assert result == FileAccessMode.WORKDIR
