"""Tests for the common utility module."""

from awslabs.finch_mcp_server.utils.common import execute_command, format_result
from unittest.mock import MagicMock, patch


class TestExecuteCommand:
    """Tests for the execute_command function."""

    @patch('subprocess.run')
    @patch('os.environ.copy')
    def test_execute_command_with_default_env(self, mock_environ_copy, mock_subprocess_run):
        """Test execute_command with default environment."""
        # Setup mocks
        mock_env = {'PATH': '/usr/bin', 'USER': 'testuser'}
        mock_environ_copy.return_value = mock_env
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = 'Command output'
        mock_process.stderr = ''
        mock_subprocess_run.return_value = mock_process

        # Call function
        result = execute_command(['echo', 'hello'])

        # Verify results
        assert result.returncode == 0
        assert result.stdout == 'Command output'
        assert result.stderr == ''

        # Verify subprocess.run was called correctly
        mock_subprocess_run.assert_called_once_with(
            ['echo', 'hello'], capture_output=True, text=True, env=mock_env
        )

        # Verify HOME was set in environment
        assert 'HOME' in mock_env

    @patch('subprocess.run')
    def test_execute_command_with_custom_env(self, mock_subprocess_run):
        """Test execute_command with custom environment."""
        # Setup mocks
        custom_env = {'PATH': '/custom/bin', 'CUSTOM_VAR': 'value'}
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = 'Command output'
        mock_process.stderr = ''
        mock_subprocess_run.return_value = mock_process

        # Call function
        result = execute_command(['echo', 'hello'], env=custom_env)

        # Verify results
        assert result.returncode == 0

        # Verify subprocess.run was called with custom environment
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
        # Setup mocks
        mock_environ.get.return_value = 'debug'
        mock_env = {'PATH': '/usr/bin', 'USER': 'testuser'}
        mock_environ_copy.return_value = mock_env
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = 'Command output'
        mock_process.stderr = 'Warning message'
        mock_subprocess_run.return_value = mock_process

        # Call function with mocked logger
        with patch('awslabs.finch_mcp_server.utils.common.logger') as mock_logger:
            result = execute_command(['echo', 'hello'])

        # Verify results
        assert result.returncode == 0
        assert result.stdout == 'Command output'
        assert result.stderr == 'Warning message'

        # Verify debug logging
        mock_logger.debug.assert_any_call('Command executed: echo hello')
        mock_logger.debug.assert_any_call('Return code: 0')
        mock_logger.debug.assert_any_call('STDOUT: Command output')
        mock_logger.debug.assert_any_call('STDERR: Warning message')

    @patch('subprocess.run')
    @patch('os.environ.copy')
    def test_execute_command_with_error(self, mock_environ_copy, mock_subprocess_run):
        """Test execute_command with command error."""
        # Setup mocks
        mock_env = {'PATH': '/usr/bin', 'USER': 'testuser'}
        mock_environ_copy.return_value = mock_env
        mock_process = MagicMock()
        mock_process.returncode = 1
        mock_process.stdout = ''
        mock_process.stderr = 'Command not found'
        mock_subprocess_run.return_value = mock_process

        # Call function
        result = execute_command(['nonexistent_command'])

        # Verify results
        assert result.returncode == 1
        assert result.stderr == 'Command not found'

        # Verify subprocess.run was called correctly
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
        result = format_result(
            'success',
            'Operation completed successfully',
            repository_uri='123456789012.dkr.ecr.us-west-2.amazonaws.com/repo',
            exists=True,
            count=5,
        )

        assert result['status'] == 'success'
        assert result['message'] == 'Operation completed successfully'
        assert result['repository_uri'] == '123456789012.dkr.ecr.us-west-2.amazonaws.com/repo'
        assert result['exists'] is True
        assert result['count'] == 5
        assert len(result) == 5  # status, message, and 3 additional params

    def test_format_result_filters_sensitive_data(self):
        """Test format_result filters out stdout and stderr."""
        result = format_result(
            'success',
            'Operation completed successfully',
            stdout='Command output with sensitive data',
            stderr='Error output with sensitive data',
            repository_uri='123456789012.dkr.ecr.us-west-2.amazonaws.com/repo',
        )

        assert result['status'] == 'success'
        assert result['message'] == 'Operation completed successfully'
        assert result['repository_uri'] == '123456789012.dkr.ecr.us-west-2.amazonaws.com/repo'
        assert 'stdout' not in result
        assert 'stderr' not in result
        assert len(result) == 3  # status, message, and repository_uri

    def test_format_result_with_error_status(self):
        """Test format_result with error status."""
        result = format_result('error', 'Operation failed: access denied', code=403)

        assert result['status'] == 'error'
        assert result['message'] == 'Operation failed: access denied'
        assert result['code'] == 403
        assert len(result) == 3  # status, message, and code
