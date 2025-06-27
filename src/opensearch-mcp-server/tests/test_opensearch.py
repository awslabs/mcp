"""Tests for the Opensearch module of opensearch-mcp-server."""

from awslabs.opensearch_mcp_server.opensearch import register_opensearch_tools
from unittest.mock import MagicMock, patch


class TestOpenSearchTools:
    """Test OpenSearch tools."""

    @patch('boto3.client')
    @patch('awslabs.opensearch_mcp_server.opensearch.AWSToolGenerator')
    def test_register_opensearch_tools(self, mock_aws_tool_generator, mock_boto3_client):
        """Test register_opensearch_tools function."""
        # Mock FastMCP
        mock_mcp = MagicMock()

        # Create a mock tool generator instance
        mock_generator_instance = MagicMock()
        mock_aws_tool_generator.return_value = mock_generator_instance

        # Call the function
        register_opensearch_tools(mock_mcp)

        # Verify AWSToolGenerator was instantiated
        mock_aws_tool_generator.assert_called_once()

        # Verify parameters safely without assuming position
        args, kwargs = mock_aws_tool_generator.call_args
        assert 'mcp' in kwargs or len(args) >= 3, 'MCP not passed to AWSToolGenerator'

        # Verify that generate() was called on the instance
        mock_generator_instance.generate.assert_called_once()
