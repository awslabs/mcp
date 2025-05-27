"""Tests for the VM utility module."""

from awslabs.finch_mcp_server.consts import (
    STATUS_ERROR,
    STATUS_SUCCESS,
    VM_STATE_NONEXISTENT,
    VM_STATE_RUNNING,
    VM_STATE_STOPPED,
)
from awslabs.finch_mcp_server.utils.vm import (
    check_finch_installation,
    configure_ecr,
    get_vm_status,
    initialize_vm,
    is_vm_nonexistent,
    is_vm_running,
    is_vm_stopped,
    start_stopped_vm,
    stop_vm,
    validate_vm_state,
)
from unittest.mock import MagicMock, mock_open, patch


class TestVmStatusChecks:
    """Tests for VM status check functions."""

    def test_is_vm_nonexistent(self):
        """Test is_vm_nonexistent function."""
        # Test with nonexistent in stdout
        process_stdout = MagicMock()
        process_stdout.stdout = 'VM is nonexistent'
        process_stdout.stderr = ''
        assert is_vm_nonexistent(process_stdout) is True

        # Test with nonexistent in stderr
        process_stderr = MagicMock()
        process_stderr.stdout = ''
        process_stderr.stderr = 'Error: VM is nonexistent'
        assert is_vm_nonexistent(process_stderr) is True

        # Test with no nonexistent mention
        process_none = MagicMock()
        process_none.stdout = 'VM is running'
        process_none.stderr = ''
        assert is_vm_nonexistent(process_none) is False

    def test_is_vm_stopped(self):
        """Test is_vm_stopped function."""
        # Test with stopped in stdout
        process_stdout = MagicMock()
        process_stdout.stdout = 'VM is stopped'
        process_stdout.stderr = ''
        assert is_vm_stopped(process_stdout) is True

        # Test with stopped in stderr
        process_stderr = MagicMock()
        process_stderr.stdout = ''
        process_stderr.stderr = 'Error: VM is stopped'
        assert is_vm_stopped(process_stderr) is True

        # Test with no stopped mention
        process_none = MagicMock()
        process_none.stdout = 'VM is running'
        process_none.stderr = ''
        assert is_vm_stopped(process_none) is False

    def test_is_vm_running(self):
        """Test is_vm_running function."""
        # Test with running in stdout
        process_stdout = MagicMock()
        process_stdout.stdout = 'VM is running'
        process_stdout.stderr = ''
        assert is_vm_running(process_stdout) is True

        # Test with running in stderr
        process_stderr = MagicMock()
        process_stderr.stdout = ''
        process_stderr.stderr = 'Error: VM is running'
        assert is_vm_running(process_stderr) is True

        # Test with no running mention
        process_none = MagicMock()
        process_none.stdout = 'VM is stopped'
        process_none.stderr = ''
        assert is_vm_running(process_none) is False


class TestVmOperations:
    """Tests for VM operation functions."""

    @patch('awslabs.finch_mcp_server.utils.vm.execute_command')
    def test_get_vm_status(self, mock_execute_command):
        """Test get_vm_status function."""
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = 'VM is running'
        mock_execute_command.return_value = mock_process

        result = get_vm_status()

        assert result.returncode == 0
        assert result.stdout == 'VM is running'
        mock_execute_command.assert_called_once_with(['finch', 'vm', 'status'])

    @patch('sys.platform', 'darwin')  # Mock as macOS
    @patch('awslabs.finch_mcp_server.utils.vm.execute_command')
    def test_initialize_vm_success(self, mock_execute_command):
        """Test initialize_vm function success case."""
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = 'VM initialized successfully'
        mock_execute_command.return_value = mock_process

        result = initialize_vm()

        assert result['status'] == STATUS_SUCCESS
        assert 'initialized successfully' in result['message']
        mock_execute_command.assert_called_once_with(['finch', 'vm', 'init'])

    @patch('sys.platform', 'darwin')  # Mock as macOS
    @patch('awslabs.finch_mcp_server.utils.vm.execute_command')
    def test_initialize_vm_failure(self, mock_execute_command):
        """Test initialize_vm function failure case."""
        mock_process = MagicMock()
        mock_process.returncode = 1
        mock_process.stderr = 'Failed to initialize VM'
        mock_execute_command.return_value = mock_process

        result = initialize_vm()

        assert result['status'] == STATUS_ERROR
        assert 'Failed to initialize' in result['message']
        mock_execute_command.assert_called_once_with(['finch', 'vm', 'init'])

    @patch('sys.platform', 'linux')  # Mock as Linux
    def test_initialize_vm_linux(self):
        """Test initialize_vm function on Linux."""
        result = initialize_vm()

        assert result['status'] == STATUS_SUCCESS
        assert 'No VM operation required' in result['message']

    @patch('sys.platform', 'darwin')  # Mock as macOS
    @patch('awslabs.finch_mcp_server.utils.vm.execute_command')
    def test_start_stopped_vm_success(self, mock_execute_command):
        """Test start_stopped_vm function success case."""
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = 'VM started successfully'
        mock_execute_command.return_value = mock_process

        result = start_stopped_vm()

        assert result['status'] == STATUS_SUCCESS
        assert 'started successfully' in result['message']
        mock_execute_command.assert_called_once_with(['finch', 'vm', 'start'])

    @patch('sys.platform', 'darwin')  # Mock as macOS
    @patch('awslabs.finch_mcp_server.utils.vm.execute_command')
    def test_start_stopped_vm_failure(self, mock_execute_command):
        """Test start_stopped_vm function failure case."""
        mock_process = MagicMock()
        mock_process.returncode = 1
        mock_process.stderr = 'Failed to start VM'
        mock_execute_command.return_value = mock_process

        result = start_stopped_vm()

        assert result['status'] == STATUS_ERROR
        assert 'Failed to start' in result['message']
        mock_execute_command.assert_called_once_with(['finch', 'vm', 'start'])

    @patch('sys.platform', 'linux')  # Mock as Linux
    def test_start_stopped_vm_linux(self):
        """Test start_stopped_vm function on Linux."""
        result = start_stopped_vm()

        assert result['status'] == STATUS_SUCCESS
        assert 'No VM operation required' in result['message']

    @patch('sys.platform', 'darwin')  # Mock as macOS
    @patch('awslabs.finch_mcp_server.utils.vm.execute_command')
    def test_stop_vm_success(self, mock_execute_command):
        """Test stop_vm function success case."""
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = 'VM stopped successfully'
        mock_execute_command.return_value = mock_process

        result = stop_vm()

        assert result['status'] == STATUS_SUCCESS
        assert 'stopped successfully' in result['message']
        mock_execute_command.assert_called_once_with(['finch', 'vm', 'stop'])

    @patch('sys.platform', 'darwin')  # Mock as macOS
    @patch('awslabs.finch_mcp_server.utils.vm.execute_command')
    def test_stop_vm_force(self, mock_execute_command):
        """Test stop_vm function with force=True."""
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = 'VM stopped successfully'
        mock_execute_command.return_value = mock_process

        result = stop_vm(force=True)

        assert result['status'] == STATUS_SUCCESS
        assert 'stopped successfully' in result['message']
        mock_execute_command.assert_called_once_with(['finch', 'vm', 'stop', '--force'])

    @patch('sys.platform', 'linux')  # Mock as Linux
    def test_stop_vm_linux(self):
        """Test stop_vm function on Linux."""
        result = stop_vm()

        assert result['status'] == STATUS_SUCCESS
        assert 'No VM operation required' in result['message']


class TestFinchInstallation:
    """Tests for Finch installation check."""

    @patch('awslabs.finch_mcp_server.utils.vm.which')
    def test_check_finch_installation_installed(self, mock_which):
        """Test check_finch_installation when Finch is installed."""
        mock_which.return_value = '/usr/local/bin/finch'

        result = check_finch_installation()

        assert result['status'] == STATUS_SUCCESS
        assert 'Finch is installed' in result['message']
        mock_which.assert_called_once_with('finch')

    @patch('awslabs.finch_mcp_server.utils.vm.which')
    def test_check_finch_installation_not_installed(self, mock_which):
        """Test check_finch_installation when Finch is not installed."""
        mock_which.return_value = None

        result = check_finch_installation()

        assert result['status'] == STATUS_ERROR
        assert 'Finch is not installed' in result['message']
        mock_which.assert_called_once_with('finch')

    @patch('awslabs.finch_mcp_server.utils.vm.which')
    def test_check_finch_installation_exception(self, mock_which):
        """Test check_finch_installation when an exception occurs."""
        mock_which.side_effect = Exception('Unexpected error')

        result = check_finch_installation()

        assert result['status'] == STATUS_ERROR
        assert 'Error checking Finch installation' in result['message']
        mock_which.assert_called_once_with('finch')


class TestEcrConfiguration:
    """Tests for ECR configuration functions."""

    @patch('os.path.exists')
    @patch('os.path.expanduser')
    @patch('builtins.open', new_callable=mock_open)
    @patch('yaml.safe_load')
    @patch('yaml.dump')
    def test_configure_ecr_existing_config(
        self,
        mock_yaml_dump,
        mock_yaml_load,
        mock_open,
        mock_expanduser,
        mock_exists,
    ):
        """Test configure_ecr with existing configuration files."""
        mock_exists.return_value = True
        mock_expanduser.side_effect = lambda path: path.replace('~', '/home/user')
        mock_yaml_load.return_value = {'creds_helpers': ['ecr-login']}

        result, changed = configure_ecr()

        mock_exists.assert_called()
        mock_expanduser.assert_called()
        mock_yaml_load.assert_called_once()
        mock_yaml_dump.assert_not_called()
        mock_open.assert_called_once()

        assert result['status'] == STATUS_SUCCESS
        assert 'ECR was already configured correctly' in result['message']
        assert changed is False

    @patch('os.path.exists')
    @patch('os.path.expanduser')
    @patch('builtins.open', new_callable=mock_open)
    @patch('yaml.safe_load')
    @patch('yaml.dump')
    def test_configure_ecr_update_config(
        self,
        mock_yaml_dump,
        mock_yaml_load,
        mock_open,
        mock_expanduser,
        mock_exists,
    ):
        """Test configure_ecr when updating existing configuration files."""
        mock_exists.return_value = True
        mock_expanduser.side_effect = lambda path: path.replace('~', '/home/user')
        mock_yaml_load.return_value = {'creds_helpers': ['docker-credential-helper']}

        result, changed = configure_ecr()

        mock_exists.assert_called()
        mock_expanduser.assert_called()
        mock_yaml_load.assert_called_once()
        mock_yaml_dump.assert_called_once()

        expected_yaml = {'creds_helpers': ['docker-credential-helper', 'ecr-login']}
        assert mock_yaml_dump.call_args[0][0] == expected_yaml

        assert result['status'] == STATUS_SUCCESS
        assert 'ECR configuration updated successfully' in result['message']
        assert changed is True

    @patch('os.path.exists')
    @patch('os.path.expanduser')
    @patch('builtins.open')
    def test_configure_ecr_exception(self, mock_open, mock_expanduser, mock_exists):
        """Test configure_ecr when an exception occurs."""
        mock_exists.return_value = True
        mock_expanduser.side_effect = lambda path: path.replace('~', '/home/user')
        mock_open.side_effect = Exception('File access error')

        result, changed = configure_ecr()

        mock_exists.assert_called()
        mock_expanduser.assert_called()
        mock_open.assert_called_once()

        assert result['status'] == STATUS_ERROR
        assert 'Failed to update finch YAML file' in result['message']
        assert changed is False


class TestVmStateValidation:
    """Tests for VM state validation."""

    @patch('awslabs.finch_mcp_server.utils.vm.get_vm_status')
    @patch('awslabs.finch_mcp_server.utils.vm.is_vm_running')
    @patch('awslabs.finch_mcp_server.utils.vm.is_vm_stopped')
    @patch('awslabs.finch_mcp_server.utils.vm.is_vm_nonexistent')
    def test_validate_vm_state_running(
        self,
        mock_is_nonexistent,
        mock_is_stopped,
        mock_is_running,
        mock_get_status,
    ):
        """Test validate_vm_state with running state."""
        mock_get_status.return_value = MagicMock()
        mock_is_running.return_value = True
        mock_is_stopped.return_value = False
        mock_is_nonexistent.return_value = False

        result = validate_vm_state(VM_STATE_RUNNING)

        assert result['status'] == STATUS_SUCCESS
        assert 'Validation passed' in result['message']

    @patch('awslabs.finch_mcp_server.utils.vm.get_vm_status')
    @patch('awslabs.finch_mcp_server.utils.vm.is_vm_running')
    @patch('awslabs.finch_mcp_server.utils.vm.is_vm_stopped')
    @patch('awslabs.finch_mcp_server.utils.vm.is_vm_nonexistent')
    def test_validate_vm_state_stopped(
        self,
        mock_is_nonexistent,
        mock_is_stopped,
        mock_is_running,
        mock_get_status,
    ):
        """Test validate_vm_state with stopped state."""
        mock_get_status.return_value = MagicMock()
        mock_is_running.return_value = False
        mock_is_stopped.return_value = True
        mock_is_nonexistent.return_value = False

        result = validate_vm_state(VM_STATE_STOPPED)

        assert result['status'] == STATUS_SUCCESS
        assert 'Validation passed' in result['message']

    @patch('awslabs.finch_mcp_server.utils.vm.get_vm_status')
    @patch('awslabs.finch_mcp_server.utils.vm.is_vm_running')
    @patch('awslabs.finch_mcp_server.utils.vm.is_vm_stopped')
    @patch('awslabs.finch_mcp_server.utils.vm.is_vm_nonexistent')
    def test_validate_vm_state_nonexistent(
        self,
        mock_is_nonexistent,
        mock_is_stopped,
        mock_is_running,
        mock_get_status,
    ):
        """Test validate_vm_state with nonexistent state."""
        mock_get_status.return_value = MagicMock()
        mock_is_running.return_value = False
        mock_is_stopped.return_value = False
        mock_is_nonexistent.return_value = True

        result = validate_vm_state(VM_STATE_NONEXISTENT)

        assert result['status'] == STATUS_SUCCESS
        assert 'Validation passed' in result['message']

    @patch('awslabs.finch_mcp_server.utils.vm.get_vm_status')
    @patch('awslabs.finch_mcp_server.utils.vm.is_vm_running')
    @patch('awslabs.finch_mcp_server.utils.vm.is_vm_stopped')
    @patch('awslabs.finch_mcp_server.utils.vm.is_vm_nonexistent')
    def test_validate_vm_state_mismatch(
        self,
        mock_is_nonexistent,
        mock_is_stopped,
        mock_is_running,
        mock_get_status,
    ):
        """Test validate_vm_state with state mismatch."""
        mock_get_status.return_value = MagicMock()
        mock_is_running.return_value = True
        mock_is_stopped.return_value = False
        mock_is_nonexistent.return_value = False

        result = validate_vm_state(VM_STATE_STOPPED)

        assert result['status'] == STATUS_ERROR
        assert 'Validation failed' in result['message']

    @patch('awslabs.finch_mcp_server.utils.vm.get_vm_status')
    def test_validate_vm_state_exception(self, mock_get_status):
        """Test validate_vm_state when an exception occurs."""
        mock_get_status.side_effect = Exception('Unexpected error')

        result = validate_vm_state(VM_STATE_RUNNING)

        assert result['status'] == STATUS_ERROR
        assert 'Error validating VM state' in result['message']
