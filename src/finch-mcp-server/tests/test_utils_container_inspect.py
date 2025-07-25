"""Tests for the container_inspect utility."""

from awslabs.finch_mcp_server.utils.container_inspect import (
    inspect_container,
    validate_container_id,
)
from unittest.mock import MagicMock, patch


class TestContainerInspect:
    """Tests for the container_inspect utility."""

    @patch('awslabs.finch_mcp_server.utils.container_inspect.validate_container_id')
    @patch('awslabs.finch_mcp_server.utils.container_inspect.execute_command')
    def test_inspect_container_success(self, mock_execute_command, mock_validate_container_id):
        """Test successful container inspection."""
        # Mock validation to always succeed
        mock_validate_container_id.return_value = (True, '')

        # Mock the execute_command function to return a successful result
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = '[{"Id":"test-container-id-1","Name":"/test-container","State":{"Status":"running","Running":true},"Config":{"Image":"python:3.9-alpine"}}]'
        mock_execute_command.return_value = mock_result

        # Call the function
        result = inspect_container('test-container')

        # Verify the result
        assert result['status'] == 'success'
        assert 'Successfully inspected container test-container' in result['message']
        assert 'raw_output' in result
        assert result['raw_output'] == mock_result.stdout

        # Verify the command was called correctly
        mock_execute_command.assert_called_once_with(
            ['finch', 'container', 'inspect', '--format', 'json', 'test-container']
        )

    @patch('awslabs.finch_mcp_server.utils.container_inspect.validate_container_id')
    @patch('awslabs.finch_mcp_server.utils.container_inspect.execute_command')
    def test_inspect_container_with_format(self, mock_execute_command, mock_validate_container_id):
        """Test container inspection with custom format."""
        # Mock validation to always succeed
        mock_validate_container_id.return_value = (True, '')

        # Mock the execute_command function to return a successful result
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = 'running'
        mock_execute_command.return_value = mock_result

        # Call the function with custom format
        result = inspect_container('test-container', format_str='{{.State.Status}}')

        # Verify the result
        assert result['status'] == 'success'
        assert 'Successfully inspected container test-container' in result['message']
        assert 'raw_output' in result
        assert result['raw_output'] == 'running'

        # Verify the command was called correctly with custom format
        mock_execute_command.assert_called_once_with(
            ['finch', 'container', 'inspect', '--format', '{{.State.Status}}', 'test-container']
        )

    @patch('awslabs.finch_mcp_server.utils.container_inspect.validate_container_id')
    @patch('awslabs.finch_mcp_server.utils.container_inspect.execute_command')
    def test_inspect_container_by_id(self, mock_execute_command, mock_validate_container_id):
        """Test container inspection by container ID."""
        # Mock validation to always succeed
        mock_validate_container_id.return_value = (True, '')

        # Mock the execute_command function to return a successful result
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = '[{"Id":"test-container-id-1","Name":"/test-container","State":{"Status":"running","Running":true}}]'
        mock_execute_command.return_value = mock_result

        # Call the function with container ID
        result = inspect_container('test-container-id-1')

        # Verify the result
        assert result['status'] == 'success'
        assert 'Successfully inspected container test-container-id-1' in result['message']
        assert 'raw_output' in result
        assert result['raw_output'] == mock_result.stdout

        # Verify the command was called correctly
        mock_execute_command.assert_called_once_with(
            ['finch', 'container', 'inspect', '--format', 'json', 'test-container-id-1']
        )

    @patch('awslabs.finch_mcp_server.utils.container_inspect.validate_container_id')
    @patch('awslabs.finch_mcp_server.utils.container_inspect.execute_command')
    def test_inspect_container_error(self, mock_execute_command, mock_validate_container_id):
        """Test container inspection when command returns an error."""
        # Mock validation to always succeed
        mock_validate_container_id.return_value = (True, '')

        # Mock the execute_command function to return an error
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = 'Error: No such container: nonexistent-container'
        mock_execute_command.return_value = mock_result

        # Call the function
        result = inspect_container('nonexistent-container')

        # Verify the result
        assert result['status'] == 'error'
        assert 'Failed to inspect container' in result['message']
        assert 'No such container' in result['message']

        # Verify the command was called correctly
        mock_execute_command.assert_called_once_with(
            ['finch', 'container', 'inspect', '--format', 'json', 'nonexistent-container']
        )

    @patch('awslabs.finch_mcp_server.utils.container_inspect.validate_container_id')
    @patch('awslabs.finch_mcp_server.utils.container_inspect.execute_command')
    def test_inspect_container_exception(self, mock_execute_command, mock_validate_container_id):
        """Test container inspection when an exception occurs."""
        # Mock validation to always succeed
        mock_validate_container_id.return_value = (True, '')

        # Mock the execute_command function to raise an exception
        mock_execute_command.side_effect = Exception('Unexpected error')

        # Call the function
        result = inspect_container('test-container')

        # Verify the result
        assert result['status'] == 'error'
        assert 'Error inspecting container: Unexpected error' in result['message']

        # Verify the command was called
        mock_execute_command.assert_called_once_with(
            ['finch', 'container', 'inspect', '--format', 'json', 'test-container']
        )

    @patch('awslabs.finch_mcp_server.utils.container_inspect.validate_container_id')
    @patch('awslabs.finch_mcp_server.utils.container_inspect.execute_command')
    def test_inspect_container_empty_output(
        self, mock_execute_command, mock_validate_container_id
    ):
        """Test container inspection with empty output."""
        # Mock validation to always succeed
        mock_validate_container_id.return_value = (True, '')

        # Mock the execute_command function to return empty output
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ''
        mock_execute_command.return_value = mock_result

        # Call the function
        result = inspect_container('test-container')

        # Verify the result
        assert result['status'] == 'success'
        assert 'Successfully inspected container test-container' in result['message']
        assert 'raw_output' in result
        assert result['raw_output'] == ''

        # Verify the command was called correctly
        mock_execute_command.assert_called_once_with(
            ['finch', 'container', 'inspect', '--format', 'json', 'test-container']
        )

    @patch('awslabs.finch_mcp_server.utils.container_inspect.validate_container_id')
    def test_inspect_container_validation_failure(self, mock_validate_container_id):
        """Test container inspection when validation fails."""
        # Mock validation to fail
        mock_validate_container_id.return_value = (
            False,
            'Invalid container ID format: invalid-id',
        )

        # Call the function
        result = inspect_container('invalid-id')

        # Verify the result
        assert result['status'] == 'error'
        assert 'Invalid container ID: Invalid container ID format: invalid-id' in result['message']

        # Verify validation was called
        mock_validate_container_id.assert_called_once_with('invalid-id')


class TestValidateContainerId:
    """Tests for the validate_container_id function."""

    def test_validate_container_id_valid_hex_format(self):
        """Test validation with valid hex container ID format."""
        with patch(
            'awslabs.finch_mcp_server.utils.container_inspect.list_containers'
        ) as mock_list_containers:
            # Mock list_containers to return a container that matches
            mock_list_containers.return_value = {
                'status': 'success',
                'raw_output': '{"ID":"abcdef123456","Names":"test-container"}',  # pragma: allowlist secret
            }

            result = validate_container_id('abcdef123456')

            assert result[0] is True
            assert result[1] == ''

    def test_validate_container_id_valid_name_format(self):
        """Test validation with valid container name format."""
        with patch(
            'awslabs.finch_mcp_server.utils.container_inspect.list_containers'
        ) as mock_list_containers:
            # Mock list_containers to return a container that matches
            mock_list_containers.return_value = {
                'status': 'success',
                'raw_output': '{"ID":"abcdef123456","Names":"test-container"}',  # pragma: allowlist secret
            }

            result = validate_container_id('test-container')

            assert result[0] is True
            assert result[1] == ''

    def test_validate_container_id_invalid_format(self):
        """Test validation with invalid container ID format."""
        result = validate_container_id('invalid@container!')

        assert result[0] is False
        assert 'Invalid container ID format' in result[1]

    def test_validate_container_id_list_containers_error(self):
        """Test validation when list_containers returns an error."""
        with patch(
            'awslabs.finch_mcp_server.utils.container_inspect.list_containers'
        ) as mock_list_containers:
            # Mock list_containers to return an error
            mock_list_containers.return_value = {
                'status': 'error',
                'message': 'Failed to list containers',
            }

            result = validate_container_id('test-container')

            # Should return True (fail open) when list_containers fails
            assert result[0] is True
            assert result[1] == ''

    def test_validate_container_id_empty_container_list(self):
        """Test validation when container list is empty."""
        with patch(
            'awslabs.finch_mcp_server.utils.container_inspect.list_containers'
        ) as mock_list_containers:
            # Mock list_containers to return empty output
            mock_list_containers.return_value = {'status': 'success', 'raw_output': ''}

            result = validate_container_id('test-container')

            assert result[0] is False
            assert 'No containers found in the system' in result[1]

    def test_validate_container_id_container_not_found(self):
        """Test validation when container is not found in the list."""
        with patch(
            'awslabs.finch_mcp_server.utils.container_inspect.list_containers'
        ) as mock_list_containers:
            # Mock list_containers to return containers that don't match
            mock_list_containers.return_value = {
                'status': 'success',
                'raw_output': '{"ID":"different123","Names":"different-container"}',
            }

            result = validate_container_id('test-container')

            assert result[0] is False
            assert 'Container not found: test-container' in result[1]

    def test_validate_container_id_id_prefix_match(self):
        """Test validation with container ID prefix match."""
        with patch(
            'awslabs.finch_mcp_server.utils.container_inspect.list_containers'
        ) as mock_list_containers:
            # Mock list_containers to return a container with longer ID
            mock_list_containers.return_value = {
                'status': 'success',
                'raw_output': '{"ID":"abcdef123456789","Names":"test-container"}',  # pragma: allowlist secret
            }

            result = validate_container_id('abcdef')

            assert result[0] is True
            assert result[1] == ''

    def test_validate_container_id_name_match(self):
        """Test validation with container name match."""
        with patch(
            'awslabs.finch_mcp_server.utils.container_inspect.list_containers'
        ) as mock_list_containers:
            # Mock list_containers to return a container with matching name
            mock_list_containers.return_value = {
                'status': 'success',
                'raw_output': '{"ID":"abcdef123456","Names":"test-container"}',  # pragma: allowlist secret
            }

            result = validate_container_id('test-container')

            assert result[0] is True
            assert result[1] == ''

    def test_validate_container_id_exception_handling(self):
        """Test validation when an exception occurs during container listing."""
        with patch(
            'awslabs.finch_mcp_server.utils.container_inspect.list_containers'
        ) as mock_list_containers:
            # Mock list_containers to raise an exception
            mock_list_containers.side_effect = Exception('Unexpected error')

            result = validate_container_id('test-container')

            assert result[0] is False
            assert 'Error validating container ID: Unexpected error' in result[1]

    def test_validate_container_id_json_parsing_multiple_containers(self):
        """Test validation with multiple containers in JSON output."""
        with patch(
            'awslabs.finch_mcp_server.utils.container_inspect.list_containers'
        ) as mock_list_containers:
            # Mock list_containers to return multiple containers
            mock_list_containers.return_value = {
                'status': 'success',
                'raw_output': '{"ID":"container1","Names":"first-container"}\n{"ID":"container2","Names":"test-container"}',
            }

            result = validate_container_id('test-container')

            assert result[0] is True
            assert result[1] == ''
