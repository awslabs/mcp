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
    @patch('awslabs.finch_mcp_server.utils.vm.format_result')
    def test_initialize_vm_success(self, mock_format_result, mock_execute_command):
        """Test initialize_vm function success case."""
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = 'VM initialized successfully'
        mock_execute_command.return_value = mock_process

        mock_format_result.return_value = {
            'status': STATUS_SUCCESS,
            'message': 'Finch VM was initialized successfully.',
        }

        result = initialize_vm()

        assert result['status'] == STATUS_SUCCESS
        assert 'initialized successfully' in result['message']
        mock_execute_command.assert_called_once_with(['finch', 'vm', 'init'])

    @patch('sys.platform', 'darwin')  # Mock as macOS
    @patch('awslabs.finch_mcp_server.utils.vm.execute_command')
    @patch('awslabs.finch_mcp_server.utils.vm.format_result')
    def test_initialize_vm_failure(self, mock_format_result, mock_execute_command):
        """Test initialize_vm function failure case."""
        mock_process = MagicMock()
        mock_process.returncode = 1
        mock_process.stderr = 'Failed to initialize VM'
        mock_execute_command.return_value = mock_process

        mock_format_result.return_value = {
            'status': STATUS_ERROR,
            'message': 'Failed to initialize Finch VM: Failed to initialize VM',
        }

        result = initialize_vm()

        assert result['status'] == STATUS_ERROR
        assert 'Failed to initialize' in result['message']
        mock_execute_command.assert_called_once_with(['finch', 'vm', 'init'])

    @patch('sys.platform', 'linux')  # Mock as Linux
    @patch('awslabs.finch_mcp_server.utils.vm.format_result')
    def test_initialize_vm_linux(self, mock_format_result):
        """Test initialize_vm function on Linux."""
        mock_format_result.return_value = {
            'status': STATUS_SUCCESS,
            'message': 'No VM operation required on Linux.',
        }

        result = initialize_vm()

        assert result['status'] == STATUS_SUCCESS
        assert 'No VM operation required' in result['message']

    @patch('sys.platform', 'darwin')  # Mock as macOS
    @patch('awslabs.finch_mcp_server.utils.vm.execute_command')
    @patch('awslabs.finch_mcp_server.utils.vm.format_result')
    def test_start_stopped_vm_success(self, mock_format_result, mock_execute_command):
        """Test start_stopped_vm function success case."""
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = 'VM started successfully'
        mock_execute_command.return_value = mock_process

        mock_format_result.return_value = {
            'status': STATUS_SUCCESS,
            'message': 'Finch VM was stopped and has been started successfully.',
        }

        result = start_stopped_vm()

        assert result['status'] == STATUS_SUCCESS
        assert 'started successfully' in result['message']
        mock_execute_command.assert_called_once_with(['finch', 'vm', 'start'])

    @patch('sys.platform', 'darwin')  # Mock as macOS
    @patch('awslabs.finch_mcp_server.utils.vm.execute_command')
    @patch('awslabs.finch_mcp_server.utils.vm.format_result')
    def test_start_stopped_vm_failure(self, mock_format_result, mock_execute_command):
        """Test start_stopped_vm function failure case."""
        mock_process = MagicMock()
        mock_process.returncode = 1
        mock_process.stderr = 'Failed to start VM'
        mock_execute_command.return_value = mock_process

        mock_format_result.return_value = {
            'status': STATUS_ERROR,
            'message': 'Failed to start Finch VM: Failed to start VM',
        }

        result = start_stopped_vm()

        assert result['status'] == STATUS_ERROR
        assert 'Failed to start' in result['message']
        mock_execute_command.assert_called_once_with(['finch', 'vm', 'start'])

    @patch('sys.platform', 'linux')  # Mock as Linux
    @patch('awslabs.finch_mcp_server.utils.vm.format_result')
    def test_start_stopped_vm_linux(self, mock_format_result):
        """Test start_stopped_vm function on Linux."""
        mock_format_result.return_value = {
            'status': STATUS_SUCCESS,
            'message': 'No VM operation required on Linux.',
        }

        result = start_stopped_vm()

        assert result['status'] == STATUS_SUCCESS
        assert 'No VM operation required' in result['message']

    @patch('sys.platform', 'darwin')  # Mock as macOS
    @patch('awslabs.finch_mcp_server.utils.vm.execute_command')
    @patch('awslabs.finch_mcp_server.utils.vm.format_result')
    def test_stop_vm_success(self, mock_format_result, mock_execute_command):
        """Test stop_vm function success case."""
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = 'VM stopped successfully'
        mock_execute_command.return_value = mock_process

        mock_format_result.return_value = {
            'status': STATUS_SUCCESS,
            'message': 'Finch VM has been stopped successfully.',
        }

        result = stop_vm()

        assert result['status'] == STATUS_SUCCESS
        assert 'stopped successfully' in result['message']
        mock_execute_command.assert_called_once_with(['finch', 'vm', 'stop'])

    @patch('sys.platform', 'darwin')  # Mock as macOS
    @patch('awslabs.finch_mcp_server.utils.vm.execute_command')
    @patch('awslabs.finch_mcp_server.utils.vm.format_result')
    def test_stop_vm_force(self, mock_format_result, mock_execute_command):
        """Test stop_vm function with force=True."""
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = 'VM stopped successfully'
        mock_execute_command.return_value = mock_process

        mock_format_result.return_value = {
            'status': STATUS_SUCCESS,
            'message': 'Finch VM has been stopped successfully.',
        }

        result = stop_vm(force=True)

        assert result['status'] == STATUS_SUCCESS
        assert 'stopped successfully' in result['message']
        mock_execute_command.assert_called_once_with(['finch', 'vm', 'stop', '--force'])

    @patch('sys.platform', 'linux')  # Mock as Linux
    @patch('awslabs.finch_mcp_server.utils.vm.format_result')
    def test_stop_vm_linux(self, mock_format_result):
        """Test stop_vm function on Linux."""
        mock_format_result.return_value = {
            'status': STATUS_SUCCESS,
            'message': 'No VM operation required on Linux.',
        }

        result = stop_vm()

        assert result['status'] == STATUS_SUCCESS
        assert 'No VM operation required' in result['message']


class TestFinchInstallation:
    """Tests for Finch installation check."""

    @patch('awslabs.finch_mcp_server.utils.vm.which')
    @patch('awslabs.finch_mcp_server.utils.vm.format_result')
    def test_check_finch_installation_installed(self, mock_format_result, mock_which):
        """Test check_finch_installation when Finch is installed."""
        mock_which.return_value = '/usr/local/bin/finch'
        mock_format_result.return_value = {
            'status': STATUS_SUCCESS,
            'message': 'Finch is installed.',
        }

        result = check_finch_installation()

        assert result['status'] == STATUS_SUCCESS
        assert 'Finch is installed' in result['message']
        mock_which.assert_called_once_with('finch')

    @patch('awslabs.finch_mcp_server.utils.vm.which')
    @patch('awslabs.finch_mcp_server.utils.vm.format_result')
    def test_check_finch_installation_not_installed(self, mock_format_result, mock_which):
        """Test check_finch_installation when Finch is not installed."""
        mock_which.return_value = None
        mock_format_result.return_value = {
            'status': STATUS_ERROR,
            'message': 'Finch is not installed.',
        }

        result = check_finch_installation()

        assert result['status'] == STATUS_ERROR
        assert 'Finch is not installed' in result['message']
        mock_which.assert_called_once_with('finch')

    @patch('awslabs.finch_mcp_server.utils.vm.which')
    @patch('awslabs.finch_mcp_server.utils.vm.format_result')
    def test_check_finch_installation_exception(self, mock_format_result, mock_which):
        """Test check_finch_installation when an exception occurs."""
        mock_which.side_effect = Exception('Unexpected error')
        mock_format_result.return_value = {
            'status': STATUS_ERROR,
            'message': 'Error checking Finch installation: Unexpected error',
        }

        result = check_finch_installation()

        assert result['status'] == STATUS_ERROR
        assert 'Error checking Finch installation' in result['message']
        mock_which.assert_called_once_with('finch')


class TestEcrConfiguration:
    """Tests for ECR configuration functions."""

    @patch('os.path.exists')
    @patch('os.path.expanduser')
    @patch('os.makedirs')
    @patch('builtins.open', new_callable=mock_open)
    @patch('json.load')
    @patch('json.dump')
    @patch('yaml.safe_load')
    @patch('yaml.dump')
    @patch('awslabs.finch_mcp_server.utils.vm.format_result')
    def test_configure_ecr_new_config(
        self,
        mock_format_result,
        mock_yaml_dump,
        mock_yaml_load,
        mock_json_dump,
        mock_json_load,
        mock_open,
        mock_makedirs,
        mock_expanduser,
        mock_exists,
    ):
        """Test configure_ecr when creating new configuration files."""
        # Setup mocks
        mock_exists.side_effect = lambda path: False  # No files exist
        mock_expanduser.side_effect = lambda path: path.replace('~', '/home/user')
        mock_format_result.return_value = {
            'status': STATUS_SUCCESS,
            'message': 'ECR configuration updated successfully using PyYAML.',
            'changed': True,
        }

        # Call function
        result = configure_ecr()

        # Verify results
        assert result['status'] == STATUS_SUCCESS
        assert 'ECR configuration updated successfully' in result['message']
        assert result['changed'] is True

        # Verify directory creation
        mock_makedirs.assert_called_once()

        # Verify JSON file creation
        mock_json_dump.assert_called_once()
        assert mock_json_dump.call_args[0][0] == {'credsStore': 'ecr-login'}

    @patch('os.path.exists')
    @patch('os.path.expanduser')
    @patch('builtins.open', new_callable=mock_open)
    @patch('json.load')
    @patch('json.dump')
    @patch('yaml.safe_load')
    @patch('yaml.dump')
    @patch('awslabs.finch_mcp_server.utils.vm.format_result')
    def test_configure_ecr_existing_config(
        self,
        mock_format_result,
        mock_yaml_dump,
        mock_yaml_load,
        mock_json_dump,
        mock_json_load,
        mock_open,
        mock_expanduser,
        mock_exists,
    ):
        """Test configure_ecr with existing configuration files."""
        # Setup mocks
        mock_exists.return_value = True
        mock_expanduser.side_effect = lambda path: path.replace('~', '/home/user')
        mock_json_load.return_value = {'credsStore': 'ecr-login'}
        mock_yaml_load.return_value = {'creds_helpers': ['ecr-login']}
        mock_format_result.return_value = {
            'status': STATUS_SUCCESS,
            'message': 'ECR was already configured correctly.',
            'changed': False,
        }

        # Call function
        result = configure_ecr()

        # Verify results
        assert result['status'] == STATUS_SUCCESS
        assert 'ECR was already configured correctly' in result['message']
        assert result['changed'] is False

        # Verify no changes were made
        mock_json_dump.assert_not_called()
        mock_yaml_dump.assert_not_called()

    @patch('os.path.exists')
    @patch('os.path.expanduser')
    @patch('builtins.open', new_callable=mock_open)
    @patch('json.load')
    @patch('json.dump')
    @patch('yaml.safe_load')
    @patch('yaml.dump')
    @patch('awslabs.finch_mcp_server.utils.vm.format_result')
    def test_configure_ecr_update_config(
        self,
        mock_format_result,
        mock_yaml_dump,
        mock_yaml_load,
        mock_json_dump,
        mock_json_load,
        mock_open,
        mock_expanduser,
        mock_exists,
    ):
        """Test configure_ecr when updating existing configuration files."""
        # Setup mocks
        mock_exists.return_value = True
        mock_expanduser.side_effect = lambda path: path.replace('~', '/home/user')
        mock_json_load.return_value = {'credsStore': 'docker-credential-helper'}
        mock_yaml_load.return_value = {'creds_helpers': ['docker-credential-helper']}
        mock_format_result.return_value = {
            'status': STATUS_SUCCESS,
            'message': 'ECR configuration updated successfully using PyYAML.',
            'changed': True,
        }

        # Call function
        result = configure_ecr()

        # Verify results
        assert result['status'] == STATUS_SUCCESS
        assert 'ECR configuration updated successfully' in result['message']
        assert result['changed'] is True

        # Verify changes were made
        mock_json_dump.assert_called_once()
        assert mock_json_dump.call_args[0][0] == {'credsStore': 'ecr-login'}
        mock_yaml_dump.assert_called_once()

    @patch('os.path.exists')
    @patch('os.path.expanduser')
    @patch('builtins.open')
    @patch('awslabs.finch_mcp_server.utils.vm.format_result')
    def test_configure_ecr_exception(
        self, mock_format_result, mock_open, mock_expanduser, mock_exists
    ):
        """Test configure_ecr when an exception occurs."""
        # Setup mocks
        mock_exists.return_value = True
        mock_expanduser.side_effect = lambda path: path.replace('~', '/home/user')
        mock_open.side_effect = Exception('File access error')
        mock_format_result.return_value = {
            'status': STATUS_ERROR,
            'message': 'Failed to configure ECR: File access error',
        }

        # Call function
        result = configure_ecr()

        # Verify results
        assert result['status'] == STATUS_ERROR
        assert 'Failed to configure ECR' in result['message']


class TestVmStateValidation:
    """Tests for VM state validation."""

    @patch('awslabs.finch_mcp_server.utils.vm.get_vm_status')
    @patch('awslabs.finch_mcp_server.utils.vm.is_vm_running')
    @patch('awslabs.finch_mcp_server.utils.vm.is_vm_stopped')
    @patch('awslabs.finch_mcp_server.utils.vm.is_vm_nonexistent')
    @patch('awslabs.finch_mcp_server.utils.vm.format_result')
    def test_validate_vm_state_running(
        self,
        mock_format_result,
        mock_is_nonexistent,
        mock_is_stopped,
        mock_is_running,
        mock_get_status,
    ):
        """Test validate_vm_state with running state."""
        # Setup mocks
        mock_get_status.return_value = MagicMock()
        mock_is_running.return_value = True
        mock_is_stopped.return_value = False
        mock_is_nonexistent.return_value = False
        mock_format_result.return_value = {
            'status': STATUS_SUCCESS,
            'message': 'Validation passed: Finch VM is running as expected.',
            'validated': True,
        }

        # Call function
        result = validate_vm_state(VM_STATE_RUNNING)

        # Verify results
        assert result['status'] == STATUS_SUCCESS
        assert 'Validation passed' in result['message']
        assert result['validated'] is True

    @patch('awslabs.finch_mcp_server.utils.vm.get_vm_status')
    @patch('awslabs.finch_mcp_server.utils.vm.is_vm_running')
    @patch('awslabs.finch_mcp_server.utils.vm.is_vm_stopped')
    @patch('awslabs.finch_mcp_server.utils.vm.is_vm_nonexistent')
    @patch('awslabs.finch_mcp_server.utils.vm.format_result')
    def test_validate_vm_state_stopped(
        self,
        mock_format_result,
        mock_is_nonexistent,
        mock_is_stopped,
        mock_is_running,
        mock_get_status,
    ):
        """Test validate_vm_state with stopped state."""
        # Setup mocks
        mock_get_status.return_value = MagicMock()
        mock_is_running.return_value = False
        mock_is_stopped.return_value = True
        mock_is_nonexistent.return_value = False
        mock_format_result.return_value = {
            'status': STATUS_SUCCESS,
            'message': 'Validation passed: Finch VM is stopped as expected.',
            'validated': True,
        }

        # Call function
        result = validate_vm_state(VM_STATE_STOPPED)

        # Verify results
        assert result['status'] == STATUS_SUCCESS
        assert 'Validation passed' in result['message']
        assert result['validated'] is True

    @patch('awslabs.finch_mcp_server.utils.vm.get_vm_status')
    @patch('awslabs.finch_mcp_server.utils.vm.is_vm_running')
    @patch('awslabs.finch_mcp_server.utils.vm.is_vm_stopped')
    @patch('awslabs.finch_mcp_server.utils.vm.is_vm_nonexistent')
    @patch('awslabs.finch_mcp_server.utils.vm.format_result')
    def test_validate_vm_state_nonexistent(
        self,
        mock_format_result,
        mock_is_nonexistent,
        mock_is_stopped,
        mock_is_running,
        mock_get_status,
    ):
        """Test validate_vm_state with nonexistent state."""
        # Setup mocks
        mock_get_status.return_value = MagicMock()
        mock_is_running.return_value = False
        mock_is_stopped.return_value = False
        mock_is_nonexistent.return_value = True
        mock_format_result.return_value = {
            'status': STATUS_SUCCESS,
            'message': 'Validation passed: Finch VM is nonexistent as expected.',
            'validated': True,
        }

        # Call function
        result = validate_vm_state(VM_STATE_NONEXISTENT)

        # Verify results
        assert result['status'] == STATUS_SUCCESS
        assert 'Validation passed' in result['message']
        assert result['validated'] is True

    @patch('awslabs.finch_mcp_server.utils.vm.get_vm_status')
    @patch('awslabs.finch_mcp_server.utils.vm.is_vm_running')
    @patch('awslabs.finch_mcp_server.utils.vm.is_vm_stopped')
    @patch('awslabs.finch_mcp_server.utils.vm.is_vm_nonexistent')
    @patch('awslabs.finch_mcp_server.utils.vm.format_result')
    def test_validate_vm_state_mismatch(
        self,
        mock_format_result,
        mock_is_nonexistent,
        mock_is_stopped,
        mock_is_running,
        mock_get_status,
    ):
        """Test validate_vm_state with state mismatch."""
        # Setup mocks
        mock_get_status.return_value = MagicMock()
        mock_is_running.return_value = True
        mock_is_stopped.return_value = False
        mock_is_nonexistent.return_value = False
        mock_format_result.return_value = {
            'status': STATUS_ERROR,
            'message': 'Validation failed: Expected Finch VM to be stopped, but it is running.',
            'validated': False,
        }

        # Call function
        result = validate_vm_state(VM_STATE_STOPPED)

        # Verify results
        assert result['status'] == STATUS_ERROR
        assert 'Validation failed' in result['message']
        assert result['validated'] is False

    @patch('awslabs.finch_mcp_server.utils.vm.get_vm_status')
    @patch('awslabs.finch_mcp_server.utils.vm.format_result')
    def test_validate_vm_state_exception(self, mock_format_result, mock_get_status):
        """Test validate_vm_state when an exception occurs."""
        # Setup mocks
        mock_get_status.side_effect = Exception('Unexpected error')
        mock_format_result.return_value = {
            'status': STATUS_ERROR,
            'message': 'Error validating VM state: Unexpected error',
            'validated': False,
        }

        # Call function
        result = validate_vm_state(VM_STATE_RUNNING)

        # Verify results
        assert result['status'] == STATUS_ERROR
        assert 'Error validating VM state' in result['message']
        assert result['validated'] is False
