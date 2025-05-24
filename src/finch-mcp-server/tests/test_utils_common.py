"""Tests for the common utility module."""

from awslabs.finch_mcp_server.utils.common import execute_command, format_result
from unittest.mock import MagicMock, patch


class TestExecuteCommand:
    """Tests for the execute_command function."""

    @patch('subprocess.run')
    @patch('os.environ.copy')
    def test_execute_command_with_default_env(self, mock_environ_copy, mock_subprocess_run):
        """Test execute_command with default environment."""
        mock_env = {'PATH': '/usr/bin', 'USER': 'testuser'}
        mock_environ_copy.return_value = mock_env
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = 'Command output'
        mock_process.stderr = ''
        mock_subprocess_run.return_value = mock_process

        result = execute_command(['echo', 'hello'])

        assert result.returncode == 0
        assert result.stdout == 'Command output'
        assert result.stderr == ''
        mock_subprocess_run.assert_called_once_with(
            ['echo', 'hello'], capture_output=True, text=True, env=mock_env
        )

        assert 'HOME' in mock_env

    @patch('subprocess.run')
    def test_execute_command_with_custom_env(self, mock_subprocess_run):
        """Test execute_command with custom environment."""
        custom_env = {'PATH': '/custom/bin', 'CUSTOM_VAR': 'value'}
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = 'Command output'
        mock_process.stderr = ''
        mock_subprocess_run.return_value = mock_process

        result = execute_command(['echo', 'hello'], env=custom_env)

        assert result.returncode == 0

        mock_subprocess_run.assert_called_once_with(
            ['echo', 'hello'], capture_output=True, text=True, env=custom_env
        )

    @patch('subprocess.run')
    @patch('os.environ.copy')
    @patch('os.environ')
    def test_execute_command_with_debug_logging(
        self, mock_environ, mock_environ_copy, mock_subprocess_run
    ):
        """Test execute_command with debug logging enabled."""
        mock_environ.get.return_value = 'debug'
        mock_env = {'PATH': '/usr/bin', 'USER': 'testuser'}
        mock_environ_copy.return_value = mock_env
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = 'Command output'
        mock_process.stderr = 'Warning message'
        mock_subprocess_run.return_value = mock_process

        with patch('awslabs.finch_mcp_server.utils.common.logger') as mock_logger:
            result = execute_command(['echo', 'hello'])

        assert result.returncode == 0
        assert result.stdout == 'Command output'
        assert result.stderr == 'Warning message'

        mock_logger.debug.assert_any_call('Command executed: echo hello')
        mock_logger.debug.assert_any_call('Return code: 0')
        mock_logger.debug.assert_any_call('STDOUT: Command output')
        mock_logger.debug.assert_any_call('STDERR: Warning message')

    @patch('subprocess.run')
    @patch('os.environ.copy')
    def test_execute_command_with_error(self, mock_environ_copy, mock_subprocess_run):
        """Test execute_command with command error."""
        mock_env = {'PATH': '/usr/bin', 'USER': 'testuser'}
        mock_environ_copy.return_value = mock_env
        mock_process = MagicMock()
        mock_process.returncode = 1
        mock_process.stdout = ''
        mock_process.stderr = 'Command not found'
        mock_subprocess_run.return_value = mock_process

        result = execute_command(['nonexistent_command'])

        assert result.returncode == 1
        assert result.stderr == 'Command not found'

        mock_subprocess_run.assert_called_once()


class TestFormatResult:
    """Tests for the format_result function."""

    def test_format_result_basic(self):
        """Test format_result with basic parameters."""
        result = format_result('success', 'Operation completed successfully')

        assert result['status'] == 'success'
        assert result['message'] == 'Operation completed successfully'
        assert len(result) == 2  # Only status and message

    def test_format_result_with_additional_params(self):
        """Test format_result with additional parameters."""
        result = format_result('success', 'Operation completed successfully')

        assert result['status'] == 'success'
        assert result['message'] == 'Operation completed successfully'
        assert len(result) == 2  # Only status and message

    def test_format_result_with_error_status(self):
        """Test format_result with error status."""
        result = format_result('error', 'Operation failed: access denied')

        assert result['status'] == 'error'
        assert result['message'] == 'Operation failed: access denied'
        assert len(result) == 2  # Only status and message
