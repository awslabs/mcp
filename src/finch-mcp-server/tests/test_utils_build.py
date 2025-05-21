"""Tests for the build utility module."""

from awslabs.finch_mcp_server.consts import STATUS_ERROR, STATUS_SUCCESS
from awslabs.finch_mcp_server.utils.build import build_image, contains_ecr_reference
from unittest.mock import MagicMock, mock_open, patch


class TestContainsEcrReference:
    """Tests for the contains_ecr_reference function."""

    @patch('os.path.exists')
    @patch(
        'builtins.open',
        new_callable=mock_open,
        read_data='FROM 123456789012.dkr.ecr.us-west-2.amazonaws.com/base:latest',
    )
    def test_contains_ecr_reference_true(self, mock_file, mock_exists):
        """Test that ECR reference is detected correctly."""
        mock_exists.return_value = True

        result = contains_ecr_reference('/path/to/Dockerfile')

        assert result is True
        mock_exists.assert_called_once_with('/path/to/Dockerfile')
        mock_file.assert_called_once_with('/path/to/Dockerfile', 'r')

    @patch('os.path.exists')
    @patch(
        'builtins.open', new_callable=mock_open, read_data='FROM docker.io/library/nginx:latest'
    )
    def test_contains_ecr_reference_false(self, mock_file, mock_exists):
        """Test that non-ECR reference is detected correctly."""
        mock_exists.return_value = True

        result = contains_ecr_reference('/path/to/Dockerfile')

        assert result is False
        mock_exists.assert_called_once_with('/path/to/Dockerfile')
        mock_file.assert_called_once_with('/path/to/Dockerfile', 'r')

    @patch('os.path.exists')
    def test_contains_ecr_reference_file_not_found(self, mock_exists):
        """Test handling of non-existent Dockerfile."""
        mock_exists.return_value = False

        result = contains_ecr_reference('/path/to/nonexistent/Dockerfile')

        assert result is False
        mock_exists.assert_called_once_with('/path/to/nonexistent/Dockerfile')

    @patch('os.path.exists')
    @patch('builtins.open')
    def test_contains_ecr_reference_exception(self, mock_file, mock_exists):
        """Test handling of exceptions when reading Dockerfile."""
        mock_exists.return_value = True
        mock_file.side_effect = Exception('File read error')

        result = contains_ecr_reference('/path/to/Dockerfile')

        assert result is False
        mock_exists.assert_called_once_with('/path/to/Dockerfile')
        mock_file.assert_called_once_with('/path/to/Dockerfile', 'r')


class TestBuildImage:
    """Tests for the build_image function."""

    @patch('os.path.exists')
    @patch('awslabs.finch_mcp_server.utils.build.execute_command')
    @patch('awslabs.finch_mcp_server.utils.build.format_result')
    def test_build_image_success(self, mock_format_result, mock_execute_command, mock_exists):
        """Test successful image build."""
        # Setup mocks
        mock_exists.return_value = True
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = 'Successfully built image'
        mock_execute_command.return_value = mock_process
        mock_format_result.return_value = {
            'status': STATUS_SUCCESS,
            'message': 'Successfully built image from /path/to/Dockerfile',
            'stdout': 'Successfully built image',
        }

        # Call function
        result = build_image(
            dockerfile_path='/path/to/Dockerfile',
            context_path='/path/to/context',
            tags=['myimage:latest'],
            platforms=['linux/amd64'],
            target='build-stage',
            no_cache=True,
            pull=True,
            add_hosts=['host1:192.168.1.1'],
            allow=['network.host'],
            build_contexts=['source=git://github.com/user/repo.git'],
            outputs='type=docker',
            cache_from=['type=registry,ref=myregistry/myimage'],
            cache_to=['type=inline'],
            quiet=False,
            progress='plain',
        )

        # Verify results
        assert result['status'] == STATUS_SUCCESS
        assert 'Successfully built image from /path/to/Dockerfile' in result['message']

        # Verify command construction
        mock_execute_command.assert_called_once()
        command_args = mock_execute_command.call_args[0][0]

        assert command_args[0:3] == ['finch', 'image', 'build']
        assert '-f' in command_args
        assert '/path/to/Dockerfile' in command_args
        assert '-t' in command_args
        assert 'myimage:latest' in command_args
        assert '--platform' in command_args
        assert 'linux/amd64' in command_args
        assert '--target' in command_args
        assert 'build-stage' in command_args
        assert '--no-cache' in command_args
        assert '--pull' in command_args
        assert '--add-host' in command_args
        assert 'host1:192.168.1.1' in command_args
        assert '--allow' in command_args
        assert 'network.host' in command_args
        assert '--build-context' in command_args
        assert 'source=git://github.com/user/repo.git' in command_args
        assert '--output' in command_args
        assert 'type=docker' in command_args
        assert '--cache-from' in command_args
        assert 'type=registry,ref=myregistry/myimage' in command_args
        assert '--cache-to' in command_args
        assert 'type=inline' in command_args
        assert '--progress' in command_args
        assert 'plain' in command_args
        assert '/path/to/context' in command_args

    @patch('os.path.exists')
    @patch('awslabs.finch_mcp_server.utils.build.execute_command')
    @patch('awslabs.finch_mcp_server.utils.build.format_result')
    def test_build_image_failure(self, mock_format_result, mock_execute_command, mock_exists):
        """Test failed image build."""
        # Setup mocks
        mock_exists.return_value = True
        mock_process = MagicMock()
        mock_process.returncode = 1
        mock_process.stderr = 'Build failed: error in Dockerfile'
        mock_execute_command.return_value = mock_process
        mock_format_result.return_value = {
            'status': STATUS_ERROR,
            'message': 'Failed to build image: Build failed: error in Dockerfile',
            'stderr': 'Build failed: error in Dockerfile',
        }

        # Call function
        result = build_image(
            dockerfile_path='/path/to/Dockerfile', context_path='/path/to/context'
        )

        # Verify results
        assert result['status'] == STATUS_ERROR
        assert 'Failed to build image' in result['message']

    @patch('os.path.exists')
    @patch('awslabs.finch_mcp_server.utils.build.format_result')
    def test_build_image_dockerfile_not_found(self, mock_format_result, mock_exists):
        """Test handling of non-existent Dockerfile."""
        # Setup mocks
        mock_exists.side_effect = lambda path: path != '/path/to/Dockerfile'
        mock_format_result.return_value = {
            'status': STATUS_ERROR,
            'message': 'Dockerfile not found at /path/to/Dockerfile',
        }

        # Call function
        result = build_image(
            dockerfile_path='/path/to/Dockerfile', context_path='/path/to/context'
        )

        # Verify results
        assert result['status'] == STATUS_ERROR
        assert 'Dockerfile not found' in result['message']
        mock_format_result.assert_called_with(
            STATUS_ERROR, 'Dockerfile not found at /path/to/Dockerfile'
        )

    @patch('os.path.exists')
    @patch('awslabs.finch_mcp_server.utils.build.format_result')
    def test_build_image_context_not_found(self, mock_format_result, mock_exists):
        """Test handling of non-existent context directory."""
        # Setup mocks
        mock_exists.side_effect = lambda path: path != '/path/to/context'
        mock_format_result.return_value = {
            'status': STATUS_ERROR,
            'message': 'Context directory not found at /path/to/context',
        }

        # Call function
        result = build_image(
            dockerfile_path='/path/to/Dockerfile', context_path='/path/to/context'
        )

        # Verify results
        assert result['status'] == STATUS_ERROR
        assert 'Context directory not found' in result['message']
        mock_format_result.assert_called_with(
            STATUS_ERROR, 'Context directory not found at /path/to/context'
        )

    @patch('os.path.exists')
    @patch('awslabs.finch_mcp_server.utils.build.execute_command')
    @patch('awslabs.finch_mcp_server.utils.build.format_result')
    def test_build_image_exception(self, mock_format_result, mock_execute_command, mock_exists):
        """Test handling of exceptions during build."""
        # Setup mocks
        mock_exists.return_value = True
        mock_execute_command.side_effect = Exception('Command execution error')
        mock_format_result.return_value = {
            'status': STATUS_ERROR,
            'message': 'Error building image: Command execution error',
        }

        # Call function
        result = build_image(
            dockerfile_path='/path/to/Dockerfile', context_path='/path/to/context'
        )

        # Verify results
        assert result['status'] == STATUS_ERROR
        assert 'Error building image' in result['message']
        mock_format_result.assert_called_with(
            STATUS_ERROR, 'Error building image: Command execution error'
        )
