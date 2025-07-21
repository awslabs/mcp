import pytest
from awslabs.aws_api_mcp_server.core.common.config import get_server_directory
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
