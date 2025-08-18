import pytest
from awslabs.aws_api_mcp_server.core.common.config import get_region, get_server_directory
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
