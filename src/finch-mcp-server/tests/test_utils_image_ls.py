"""Tests for the image_ls utility."""

from awslabs.finch_mcp_server.consts import STATUS_ERROR, STATUS_SUCCESS
from awslabs.finch_mcp_server.utils.image_ls import list_images
from unittest.mock import MagicMock, patch


class TestImageLs:
    """Tests for the image_ls utility."""

    @patch('awslabs.finch_mcp_server.utils.image_ls.execute_command')
    def test_list_images_success(self, mock_execute_command):
        """Test successful image listing."""
        # Mock the execute_command function to return a successful result
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = '{"Repository":"python","Tag":"3.9-alpine","ID":"sha256:abcdef123456","Created":"2023-01-01 12:00:00","Size":"45MB"}\n{"Repository":"nginx","Tag":"latest","ID":"sha256:fedcba654321","Created":"2023-01-02 12:00:00","Size":"135MB"}'
        mock_execute_command.return_value = mock_result

        # Call the function
        result = list_images()

        # Verify the result
        assert result['status'] == STATUS_SUCCESS
        assert 'Successfully listed images' in result['message']
        assert 'raw_output' in result
        assert result['raw_output'] == mock_result.stdout

        # Verify the command was called correctly
        mock_execute_command.assert_called_once_with(['finch', 'image', 'ls', '--format', 'json'])

    @patch('awslabs.finch_mcp_server.utils.image_ls.execute_command')
    def test_list_images_all(self, mock_execute_command):
        """Test image listing with all_images=True."""
        # Mock the execute_command function to return a successful result
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = '{"Repository":"python","Tag":"3.9-alpine","ID":"sha256:abcdef123456","Created":"2023-01-01 12:00:00","Size":"45MB"}\n{"Repository":"nginx","Tag":"latest","ID":"sha256:fedcba654321","Created":"2023-01-02 12:00:00","Size":"135MB"}\n{"Repository":"<none>","Tag":"<none>","ID":"sha256:123456789abc","Created":"2023-01-03 12:00:00","Size":"10MB"}'
        mock_execute_command.return_value = mock_result

        # Call the function with all_images=True
        result = list_images(all_images=True)

        # Verify the result
        assert result['status'] == STATUS_SUCCESS
        assert 'Successfully listed images' in result['message']
        assert 'raw_output' in result
        assert result['raw_output'] == mock_result.stdout

        # Verify the command was called correctly with -a flag
        mock_execute_command.assert_called_once_with(
            ['finch', 'image', 'ls', '--format', 'json', '-a']
        )

    @patch('awslabs.finch_mcp_server.utils.image_ls.execute_command')
    def test_list_images_filter(self, mock_execute_command):
        """Test image listing with filter_expr."""
        # Mock the execute_command function to return a successful result
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = '{"Repository":"python","Tag":"3.9-alpine","ID":"sha256:abcdef123456","Created":"2023-01-01 12:00:00","Size":"45MB"}'
        mock_execute_command.return_value = mock_result

        # Call the function with filter_expr
        result = list_images(filter_expr=['reference=python:3.9-alpine', 'dangling=false'])

        # Verify the result
        assert result['status'] == STATUS_SUCCESS
        assert 'Successfully listed images' in result['message']
        assert 'raw_output' in result
        assert result['raw_output'] == mock_result.stdout

        # Verify the command was called correctly with -f flags
        mock_execute_command.assert_called_once_with(
            [
                'finch',
                'image',
                'ls',
                '--format',
                'json',
                '-f',
                'reference=python:3.9-alpine',
                '-f',
                'dangling=false',
            ]
        )

    @patch('awslabs.finch_mcp_server.utils.image_ls.execute_command')
    def test_list_images_no_trunc(self, mock_execute_command):
        """Test image listing with no_trunc=True."""
        # Mock the execute_command function to return a successful result
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = '{"Repository":"python","Tag":"3.9-alpine","ID":"sha256:abcdef123456789abcdef123456789abcdef123456789abcdef123456789abcdef","Created":"2023-01-01 12:00:00","Size":"45MB"}'
        mock_execute_command.return_value = mock_result

        # Call the function with no_trunc=True
        result = list_images(no_trunc=True)

        # Verify the result
        assert result['status'] == STATUS_SUCCESS
        assert 'Successfully listed images' in result['message']
        assert 'raw_output' in result
        assert result['raw_output'] == mock_result.stdout

        # Verify the command was called correctly with --no-trunc flag
        mock_execute_command.assert_called_once_with(
            ['finch', 'image', 'ls', '--format', 'json', '--no-trunc']
        )

    @patch('awslabs.finch_mcp_server.utils.image_ls.execute_command')
    def test_list_images_quiet(self, mock_execute_command):
        """Test image listing with quiet=True."""
        # Mock the execute_command function to return a successful result
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = '{"ID":"sha256:abcdef123456"}\n{"ID":"sha256:fedcba654321"}'
        mock_execute_command.return_value = mock_result

        # Call the function with quiet=True
        result = list_images(quiet=True)

        # Verify the result
        assert result['status'] == STATUS_SUCCESS
        assert 'Successfully listed images' in result['message']
        assert 'raw_output' in result
        assert result['raw_output'] == mock_result.stdout

        # Verify the command was called correctly with -q flag
        mock_execute_command.assert_called_once_with(
            ['finch', 'image', 'ls', '--format', 'json', '-q']
        )

    @patch('awslabs.finch_mcp_server.utils.image_ls.execute_command')
    def test_list_images_digests(self, mock_execute_command):
        """Test image listing with digests=True."""
        # Mock the execute_command function to return a successful result
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = '{"Repository":"python","Tag":"3.9-alpine","Digest":"sha256:123456789abcdef","ID":"sha256:abcdef123456","Created":"2023-01-01 12:00:00","Size":"45MB"}'
        mock_execute_command.return_value = mock_result

        # Call the function with digests=True
        result = list_images(digests=True)

        # Verify the result
        assert result['status'] == STATUS_SUCCESS
        assert 'Successfully listed images' in result['message']
        assert 'raw_output' in result
        assert result['raw_output'] == mock_result.stdout

        # Verify the command was called correctly with --digests flag
        mock_execute_command.assert_called_once_with(
            ['finch', 'image', 'ls', '--format', 'json', '--digests']
        )

    @patch('awslabs.finch_mcp_server.utils.image_ls.execute_command')
    def test_list_images_multiple_options(self, mock_execute_command):
        """Test image listing with multiple options."""
        # Mock the execute_command function to return a successful result
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = '{"Repository":"python","Tag":"3.9-alpine","Digest":"sha256:123456789abcdef","ID":"sha256:abcdef123456789abcdef123456789abcdef123456789abcdef123456789abcdef","Created":"2023-01-01 12:00:00","Size":"45MB"}'
        mock_execute_command.return_value = mock_result

        # Call the function with multiple options
        result = list_images(all_images=True, digests=True, no_trunc=True)

        # Verify the result
        assert result['status'] == STATUS_SUCCESS
        assert 'Successfully listed images' in result['message']
        assert 'raw_output' in result
        assert result['raw_output'] == mock_result.stdout

        # Verify the command was called correctly with all flags
        mock_execute_command.assert_called_once_with(
            ['finch', 'image', 'ls', '--format', 'json', '-a', '--no-trunc', '--digests']
        )

    @patch('awslabs.finch_mcp_server.utils.image_ls.execute_command')
    def test_list_images_error(self, mock_execute_command):
        """Test image listing when command returns an error."""
        # Mock the execute_command function to return an error
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = 'Error: failed to list images'
        mock_execute_command.return_value = mock_result

        # Call the function
        result = list_images()

        # Verify the result
        assert result['status'] == STATUS_ERROR
        assert 'Failed to list images' in result['message']

        # Verify the command was called correctly
        mock_execute_command.assert_called_once_with(['finch', 'image', 'ls', '--format', 'json'])

    @patch('awslabs.finch_mcp_server.utils.image_ls.execute_command')
    def test_list_images_exception(self, mock_execute_command):
        """Test image listing when an exception occurs."""
        # Mock the execute_command function to raise an exception
        mock_execute_command.side_effect = Exception('Unexpected error')

        # Call the function
        result = list_images()

        # Verify the result
        assert result['status'] == STATUS_ERROR
        assert 'Error listing images: Unexpected error' in result['message']

        # Verify the command was called
        mock_execute_command.assert_called_once_with(['finch', 'image', 'ls', '--format', 'json'])
