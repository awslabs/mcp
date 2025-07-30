"""Tests for the container_ls utility."""

from awslabs.finch_mcp_server.consts import STATUS_ERROR, STATUS_SUCCESS
from awslabs.finch_mcp_server.utils.container_ls import list_containers
from unittest.mock import MagicMock, patch


class TestContainerLs:
    """Tests for the container_ls utility."""

    @patch('awslabs.finch_mcp_server.utils.container_ls.execute_command')
    def test_list_containers_success(self, mock_execute_command):
        """Test successful container listing."""
        # Mock the execute_command function to return a successful result
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = '{"ID":"test-container-1","Image":"python:3.9-alpine","Command":"python app.py","Created":"2023-01-01 12:00:00","Status":"Up 2 hours","Ports":"8080/tcp","Names":"my-python-app"}\n{"ID":"test-container-2","Image":"nginx:latest","Command":"nginx -g daemon off;","Created":"2023-01-02 12:00:00","Status":"Up 1 hour","Ports":"80/tcp, 443/tcp","Names":"my-nginx"}'
        mock_execute_command.return_value = mock_result

        # Call the function
        result = list_containers()

        # Verify the result
        assert result['status'] == STATUS_SUCCESS
        assert 'Successfully listed containers' in result['message']
        assert 'raw_output' in result
        assert result['raw_output'] == mock_result.stdout

        # Verify the command was called correctly
        mock_execute_command.assert_called_once_with(
            ['finch', 'container', 'ls', '--all', '--format', 'json']
        )

    @patch('awslabs.finch_mcp_server.utils.container_ls.execute_command')
    def test_list_containers_all(self, mock_execute_command):
        """Test container listing with all_containers=True."""
        # Mock the execute_command function to return a successful result
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = '{"ID":"test-container-1","Image":"python:3.9-alpine","Command":"python app.py","Created":"2023-01-01 12:00:00","Status":"Up 2 hours","Ports":"8080/tcp","Names":"my-python-app"}\n{"ID":"test-container-2","Image":"nginx:latest","Command":"nginx -g daemon off;","Created":"2023-01-02 12:00:00","Status":"Exited (0) 1 hour ago","Ports":"80/tcp, 443/tcp","Names":"my-nginx"}'
        mock_execute_command.return_value = mock_result

        result = list_containers(all_containers=True)

        # Verify the result
        assert result['status'] == STATUS_SUCCESS
        assert 'Successfully listed containers' in result['message']
        assert 'raw_output' in result
        assert result['raw_output'] == mock_result.stdout

        # Verify the command was called correctly with --all flag
        mock_execute_command.assert_called_once_with(
            ['finch', 'container', 'ls', '--all', '--format', 'json']
        )

    @patch('awslabs.finch_mcp_server.utils.container_ls.execute_command')
    def test_list_containers_filter(self, mock_execute_command):
        """Test container listing with filter_expr."""
        # Mock the execute_command function to return a successful result
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = '{"ID":"test-container-1","Image":"python:3.9-alpine","Command":"python app.py","Created":"2023-01-01 12:00:00","Status":"Up 2 hours","Ports":"8080/tcp","Names":"my-python-app"}'
        mock_execute_command.return_value = mock_result

        # Call the function with filter_expr
        result = list_containers(filter_expr=['status=running', 'label=app=web'])

        # Verify the result
        assert result['status'] == STATUS_SUCCESS
        assert 'Successfully listed containers' in result['message']
        assert 'raw_output' in result
        assert result['raw_output'] == mock_result.stdout

        # Verify the command was called correctly with --filter flags
        mock_execute_command.assert_called_once_with(
            [
                'finch',
                'container',
                'ls',
                '--all',
                '--filter',
                'status=running',
                '--filter',
                'label=app=web',
                '--format',
                'json',
            ]
        )

    @patch('awslabs.finch_mcp_server.utils.container_ls.execute_command')
    def test_list_containers_last(self, mock_execute_command):
        """Test container listing with last parameter."""
        # Mock the execute_command function to return a successful result
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = '{"ID":"test-container-2","Image":"nginx:latest","Command":"nginx -g daemon off;","Created":"2023-01-02 12:00:00","Status":"Up 1 hour","Ports":"80/tcp, 443/tcp","Names":"my-nginx"}'
        mock_execute_command.return_value = mock_result

        # Call the function with last=1
        result = list_containers(last=1)

        # Verify the result
        assert result['status'] == STATUS_SUCCESS
        assert 'Successfully listed containers' in result['message']
        assert 'raw_output' in result
        assert result['raw_output'] == mock_result.stdout

        # Verify the command was called correctly with --last flag
        mock_execute_command.assert_called_once_with(
            ['finch', 'container', 'ls', '--all', '--format', 'json', '--last', '1']
        )

    @patch('awslabs.finch_mcp_server.utils.container_ls.execute_command')
    def test_list_containers_latest(self, mock_execute_command):
        """Test container listing with latest=True."""
        # Mock the execute_command function to return a successful result
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = '{"ID":"test-container-2","Image":"nginx:latest","Command":"nginx -g daemon off;","Created":"2023-01-02 12:00:00","Status":"Up 1 hour","Ports":"80/tcp, 443/tcp","Names":"my-nginx"}'
        mock_execute_command.return_value = mock_result

        # Call the function with latest=True
        result = list_containers(latest=True)

        # Verify the result
        assert result['status'] == STATUS_SUCCESS
        assert 'Successfully listed containers' in result['message']
        assert 'raw_output' in result
        assert result['raw_output'] == mock_result.stdout

        # Verify the command was called correctly with --latest flag
        mock_execute_command.assert_called_once_with(
            ['finch', 'container', 'ls', '--all', '--format', 'json', '--latest']
        )

    @patch('awslabs.finch_mcp_server.utils.container_ls.execute_command')
    def test_list_containers_no_trunc(self, mock_execute_command):
        """Test container listing with no_trunc=True."""
        # Mock the execute_command function to return a successful result
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = '{"ID":"test-container-full-id","Image":"python:3.9-alpine","Command":"python app.py","Created":"2023-01-01 12:00:00","Status":"Up 2 hours","Ports":"8080/tcp","Names":"my-python-app"}'
        mock_execute_command.return_value = mock_result

        # Call the function with no_trunc=True
        result = list_containers(no_trunc=True)

        # Verify the result
        assert result['status'] == STATUS_SUCCESS
        assert 'Successfully listed containers' in result['message']
        assert 'raw_output' in result
        assert result['raw_output'] == mock_result.stdout

        # Verify the command was called correctly with --no-trunc flag
        mock_execute_command.assert_called_once_with(
            ['finch', 'container', 'ls', '--all', '--format', 'json', '--no-trunc']
        )

    @patch('awslabs.finch_mcp_server.utils.container_ls.execute_command')
    def test_list_containers_quiet(self, mock_execute_command):
        """Test container listing with quiet=True."""
        # Mock the execute_command function to return a successful result
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = '{"ID":"test-container-1"}\n{"ID":"test-container-2"}'
        mock_execute_command.return_value = mock_result

        # Call the function with quiet=True
        result = list_containers(quiet=True)

        # Verify the result
        assert result['status'] == STATUS_SUCCESS
        assert 'Successfully listed containers' in result['message']
        assert 'raw_output' in result
        assert result['raw_output'] == mock_result.stdout

        # Verify the command was called correctly with --quiet flag
        mock_execute_command.assert_called_once_with(
            ['finch', 'container', 'ls', '--all', '--format', 'json', '--quiet']
        )

    @patch('awslabs.finch_mcp_server.utils.container_ls.execute_command')
    def test_list_containers_size(self, mock_execute_command):
        """Test container listing with size=True."""
        # Mock the execute_command function to return a successful result
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = '{"ID":"test-container-1","Image":"python:3.9-alpine","Command":"python app.py","Created":"2023-01-01 12:00:00","Status":"Up 2 hours","Ports":"8080/tcp","Names":"my-python-app","Size":"10MB"}'
        mock_execute_command.return_value = mock_result

        # Call the function with size=True
        result = list_containers(size=True)

        # Verify the result
        assert result['status'] == STATUS_SUCCESS
        assert 'Successfully listed containers' in result['message']
        assert 'raw_output' in result
        assert result['raw_output'] == mock_result.stdout

        # Verify the command was called correctly with --size flag
        mock_execute_command.assert_called_once_with(
            ['finch', 'container', 'ls', '--all', '--format', 'json', '--size']
        )

    @patch('awslabs.finch_mcp_server.utils.container_ls.execute_command')
    def test_list_containers_multiple_options(self, mock_execute_command):
        """Test container listing with multiple options."""
        # Mock the execute_command function to return a successful result
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = '{"ID":"test-container-1","Image":"python:3.9-alpine","Command":"python app.py","Created":"2023-01-01 12:00:00","Status":"Up 2 hours","Ports":"8080/tcp","Names":"my-python-app","Size":"10MB"}'
        mock_execute_command.return_value = mock_result

        # Call the function with multiple options
        result = list_containers(all_containers=True, size=True, no_trunc=True)

        # Verify the result
        assert result['status'] == STATUS_SUCCESS
        assert 'Successfully listed containers' in result['message']
        assert 'raw_output' in result
        assert result['raw_output'] == mock_result.stdout

        # Verify the command was called correctly with all flags
        mock_execute_command.assert_called_once_with(
            ['finch', 'container', 'ls', '--all', '--format', 'json', '--no-trunc', '--size']
        )

    @patch('awslabs.finch_mcp_server.utils.container_ls.execute_command')
    def test_list_containers_error(self, mock_execute_command):
        """Test container listing when command returns an error."""
        # Mock the execute_command function to return an error
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = 'Error: failed to list containers'
        mock_execute_command.return_value = mock_result

        # Call the function
        result = list_containers()

        # Verify the result
        assert result['status'] == STATUS_ERROR
        assert 'Failed to list containers' in result['message']

        # Verify the command was called correctly
        mock_execute_command.assert_called_once_with(
            ['finch', 'container', 'ls', '--all', '--format', 'json']
        )

    @patch('awslabs.finch_mcp_server.utils.container_ls.execute_command')
    def test_list_containers_exception(self, mock_execute_command):
        """Test container listing when an exception occurs."""
        # Mock the execute_command function to raise an exception
        mock_execute_command.side_effect = Exception('Unexpected error')

        # Call the function
        result = list_containers()

        # Verify the result
        assert result['status'] == STATUS_ERROR
        assert 'Error listing containers: Unexpected error' in result['message']

        # Verify the command was called
        mock_execute_command.assert_called_once_with(
            ['finch', 'container', 'ls', '--all', '--format', 'json']
        )
