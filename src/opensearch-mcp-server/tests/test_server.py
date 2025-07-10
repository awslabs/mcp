"""Tests for the opensearch-mcp-server."""

from awslabs.opensearch_mcp_server.server import main, mcp
from unittest.mock import MagicMock, patch


class TestServerModule:
    """Test server module."""

    def test_mcp_initialization(self):
        """Test that the MCP server is initialized correctly."""
        assert mcp.name == 'awslabs.opensearch-mcp-server'

        assert 'pydantic' in mcp.dependencies
        assert 'boto3' in mcp.dependencies

    @patch('boto3.Session')
    @patch('awslabs.opensearch_mcp_server.server.mcp')
    @patch('argparse.ArgumentParser.parse_args')
    def test_main_without_sse(self, mock_parse_args, mock_mcp, mock_session):
        """Test main function without SSE."""
        # Setup mock
        mock_args = MagicMock()
        mock_args.sse = False
        mock_parse_args.return_value = mock_args

        # Mock boto3 session to prevent credential lookup
        mock_session_instance = MagicMock()
        mock_session.return_value = mock_session_instance

        # Call main
        main()

        # Assert run was called without transport
        mock_mcp.run.assert_called_once_with()

    @patch('boto3.Session')
    @patch('awslabs.opensearch_mcp_server.server.mcp')
    @patch('awslabs.opensearch_mcp_server.server.register_opensearch_tools')
    @patch('awslabs.opensearch_mcp_server.server.register_opensearchserverless_tools')
    @patch('awslabs.opensearch_mcp_server.server.register_osis_tools')
    def test_main_with_allow_resource_creation(
        self,
        mock_register_osis,
        mock_register_opensearchserverless,
        mock_register_opensearch,
        mock_mcp,
        mock_session,
    ):
        """Test main function with --allow-resource-creation flag."""
        # Setup mock with allow_resource_creation=True
        mock_args = MagicMock()
        mock_args.sse = False
        mock_args.allow_resource_creation = True
        mock_args.port = 8888

        # Mock boto3 session to prevent credential lookup
        mock_session_instance = MagicMock()
        mock_session.return_value = mock_session_instance

        # Call main
        main()

        mock_register_osis.assert_called_once_with(mock_mcp)
        mock_register_opensearchserverless.assert_called_once_with(mock_mcp)
        mock_register_opensearch.assert_called_once_with(mock_mcp)
