"""Tests for the version utility."""

from awslabs.finch_mcp_server.consts import STATUS_ERROR, STATUS_SUCCESS
from awslabs.finch_mcp_server.utils.version import get_version
from unittest.mock import MagicMock, patch


class TestVersion:
    """Tests for the version utility."""

    @patch('awslabs.finch_mcp_server.utils.version.execute_command')
    def test_get_version_success(self, mock_execute_command):
        """Test successful version retrieval."""
        # Mock the execute_command function to return a successful result
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = 'Finch version 1.0.0 (build 12345)'
        mock_execute_command.return_value = mock_result

        # Call the function
        result = get_version()

        # Verify the result
        assert result['status'] == STATUS_SUCCESS
        assert 'Successfully retrieved Finch version' in result['message']
        assert 'Finch version 1.0.0' in result['version']

        # Verify the command was called correctly
        mock_execute_command.assert_called_once_with(['finch', 'version'])

    @patch('awslabs.finch_mcp_server.utils.version.execute_command')
    def test_get_version_error(self, mock_execute_command):
        """Test version retrieval when command returns an error."""
        # Mock the execute_command function to return an error
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = 'Error: failed to get version'
        mock_execute_command.return_value = mock_result

        # Call the function
        result = get_version()

        # Verify the result
        assert result['status'] == STATUS_ERROR
        assert 'Failed to get version' in result['message']

        # Verify the command was called correctly
        mock_execute_command.assert_called_once_with(['finch', 'version'])

    @patch('awslabs.finch_mcp_server.utils.version.execute_command')
    def test_get_version_exception(self, mock_execute_command):
        """Test version retrieval when an exception occurs."""
        # Mock the execute_command function to raise an exception
        mock_execute_command.side_effect = Exception('Unexpected error')

        # Call the function
        result = get_version()

        # Verify the result
        assert result['status'] == STATUS_ERROR
        assert 'Error getting version: Unexpected error' in result['message']

        # Verify the command was called
        mock_execute_command.assert_called_once_with(['finch', 'version'])
