"""Tests for the common utility module."""

import pytest
from awslabs.finch_mcp_server.utils.common import (
    execute_command,
    format_result,
    get_dangerous_patterns,
)
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

        result = execute_command(['finch', 'vm', 'status'])

        assert result.returncode == 0
        assert result.stdout == 'Command output'
        assert result.stderr == ''
        mock_subprocess_run.assert_called_once_with(
            ['finch', 'vm', 'status'], capture_output=True, text=True, env=mock_env
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

        result = execute_command(['finch', 'info'], env=custom_env)

        assert result.returncode == 0

        mock_subprocess_run.assert_called_once_with(
            ['finch', 'info'], capture_output=True, text=True, env=custom_env
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
            result = execute_command(['finch', 'version'])

        assert result.returncode == 0
        assert result.stdout == 'Command output'
        assert result.stderr == 'Warning message'

        mock_logger.debug.assert_any_call('Command executed: finch version')
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

        result = execute_command(['finch', 'nonexistent_subcommand'])

        assert result.returncode == 1
        assert result.stderr == 'Command not found'

        mock_subprocess_run.assert_called_once()

    @patch('os.environ.copy')
    def test_execute_command_rejects_non_finch_commands(self, mock_environ_copy):
        """Test execute_command rejects non-finch commands."""
        mock_env = {'PATH': '/usr/bin', 'USER': 'testuser'}
        mock_environ_copy.return_value = mock_env

        with patch('awslabs.finch_mcp_server.utils.common.logger') as mock_logger:
            with pytest.raises(ValueError) as excinfo:
                execute_command(['echo', 'hello'])

        assert 'Security violation: Only finch commands are allowed' in str(excinfo.value)
        mock_logger.error.assert_called_once()

    @patch('os.environ.copy')
    def test_execute_command_rejects_empty_command(self, mock_environ_copy):
        """Test execute_command rejects empty command list."""
        mock_env = {'PATH': '/usr/bin', 'USER': 'testuser'}
        mock_environ_copy.return_value = mock_env

        with patch('awslabs.finch_mcp_server.utils.common.logger') as mock_logger:
            with pytest.raises(ValueError) as excinfo:
                execute_command([])

        assert 'Security violation: Only finch commands are allowed' in str(excinfo.value)
        mock_logger.error.assert_called_once()

    @patch('os.environ.copy')
    def test_execute_command_rejects_docker_command(self, mock_environ_copy):
        """Test execute_command rejects docker command."""
        mock_env = {'PATH': '/usr/bin', 'USER': 'testuser'}
        mock_environ_copy.return_value = mock_env

        with patch('awslabs.finch_mcp_server.utils.common.logger') as mock_logger:
            with pytest.raises(ValueError) as excinfo:
                execute_command(['docker', 'run', '-it', 'ubuntu:latest', 'bash'])

        assert 'Security violation: Only finch commands are allowed' in str(excinfo.value)
        mock_logger.error.assert_called_once()


class TestFormatResult:
    """Tests for the format_result function."""

    def test_format_result_basic(self):
        """Test format_result with basic parameters."""
        result = format_result('success', 'Operation completed successfully')

        assert result['status'] == 'success'
        assert result['message'] == 'Operation completed successfully'
        assert len(result) == 2


class TestDangerousPatterns:
    """Tests for the get_dangerous_patterns function."""

    def test_get_dangerous_patterns(self):
        """Test that get_dangerous_patterns returns a non-empty list."""
        patterns = get_dangerous_patterns()
        assert isinstance(patterns, list)
        assert len(patterns) > 0
        assert '|' in patterns
        assert 'sudo' in patterns


class TestCommandExecution:
    """Tests for the execute_command function."""

    @patch('subprocess.run')
    def test_execute_command_with_safe_command(self, mock_subprocess_run):
        """Test that execute_command works with safe commands."""
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = 'Finch version 1.0.0'
        mock_process.stderr = ''
        mock_subprocess_run.return_value = mock_process

        try:
            result = execute_command(['finch', 'version'])
            assert result.returncode == 0
            assert result.stdout == 'Finch version 1.0.0'
            assert result.stderr == ''
            mock_subprocess_run.assert_called_once()
        except ValueError:
            pytest.fail('execute_command raised ValueError unexpectedly with safe command')

    @patch('subprocess.run')
    def test_execute_command_with_dangerous_pattern(self, mock_subprocess_run):
        """Test that execute_command raises ValueError with dangerous patterns."""
        # The mock should not be called because the validation should fail before subprocess.run is called
        with pytest.raises(ValueError) as excinfo:
            execute_command(['finch', 'version', '|', 'grep', 'version'])
        assert 'Security violation' in str(excinfo.value)
        assert 'Potentially dangerous pattern' in str(excinfo.value)
        mock_subprocess_run.assert_not_called()

    @patch('subprocess.run')
    def test_execute_command_with_non_finch_command(self, mock_subprocess_run):
        """Test that execute_command raises ValueError with non-finch commands."""
        # The mock should not be called because the validation should fail before subprocess.run is called
        with pytest.raises(ValueError) as excinfo:
            execute_command(['ls', '-la'])
        assert 'Security violation' in str(excinfo.value)
        assert 'Only finch commands are allowed' in str(excinfo.value)
        mock_subprocess_run.assert_not_called()
