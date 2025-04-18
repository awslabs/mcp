"""Integration tests for the lambda-mcp-server."""

import pytest
from awslabs.lambda_mcp_server.server import (
    invoke_lambda_function_impl,
    mcp,
    register_lambda_functions,
)
from mcp.server.fastmcp import Context, FastMCP
from unittest.mock import AsyncMock, MagicMock, patch


class TestServerIntegration:
    """Integration tests for the server module."""

    @patch('awslabs.lambda_mcp_server.server.lambda_client')
    def test_mcp_initialization(self, mock_lambda_client):
        """Test that the MCP server is initialized correctly."""
        # Check that the MCP server has the correct name
        assert mcp.name == 'awslabs.lambda-mcp-server'

        # Check that the MCP server has instructions
        assert 'Use AWS Lambda functions' in mcp.instructions

        # Check that the MCP server has dependencies
        assert 'pydantic' in mcp.dependencies
        assert 'boto3' in mcp.dependencies

    @patch('awslabs.lambda_mcp_server.server.create_lambda_tool')
    @patch('awslabs.lambda_mcp_server.server.lambda_client')
    def test_tool_registration(self, mock_lambda_client, mock_create_lambda_tool, mock_env_vars):
        """Test that Lambda functions are registered as tools."""
        # Set up the mock
        mock_lambda_client.list_functions.return_value = {
            'Functions': [
                {
                    'FunctionName': 'test-function',
                    'FunctionArn': 'arn:aws:lambda:us-east-1:123456789012:function:test-function',
                    'Description': 'Test function description',
                },
            ]
        }

        # Call the function
        register_lambda_functions()

        # Check that create_lambda_tool was called with the correct arguments
        mock_create_lambda_tool.assert_called_once_with(
            'test-function', 'Test function description'
        )

    @pytest.mark.asyncio
    @patch('awslabs.lambda_mcp_server.server.lambda_client')
    async def test_tool_invocation(self, mock_lambda_client):
        """Test invoking a Lambda function through the MCP tool."""
        # Set up the mock
        mock_payload = MagicMock()
        mock_payload.read.return_value = b'{"result": "success"}'
        mock_lambda_client.invoke.return_value = {
            'StatusCode': 200,
            'Payload': mock_payload,
        }

        # Create a mock context
        ctx = MagicMock(spec=Context)
        ctx.info = AsyncMock()
        ctx.error = AsyncMock()

        # Call the function
        result = await invoke_lambda_function_impl('test-function', {'param': 'value'}, ctx)

        # Check that the Lambda function was invoked with the correct parameters
        mock_lambda_client.invoke.assert_called_once()

        # Check that the context methods were called
        ctx.info.assert_called()

        # Check the result
        assert 'Function test-function returned:' in result
        assert '"result": "success"' in result


class TestToolFunctionality:
    """Tests for the functionality of the Lambda tools."""

    @pytest.mark.asyncio
    @patch('awslabs.lambda_mcp_server.server.lambda_client')
    async def test_lambda_function_tool(self, mock_lambda_client):
        """Test the Lambda function tool."""
        # Set up the mock
        mock_payload = MagicMock()
        mock_payload.read.return_value = b'{"result": "success"}'
        mock_lambda_client.invoke.return_value = {
            'StatusCode': 200,
            'Payload': mock_payload,
        }

        # Create a mock MCP server
        mock_mcp = MagicMock(spec=FastMCP)

        # Create a mock tool function
        async def mock_tool_function(parameters, ctx):
            return await invoke_lambda_function_impl('test-function', parameters, ctx)

        # Create a mock context
        ctx = MagicMock(spec=Context)
        ctx.info = AsyncMock()
        ctx.error = AsyncMock()

        # Call the function
        with patch('awslabs.lambda_mcp_server.server.mcp', mock_mcp):
            result = await mock_tool_function({'param': 'value'}, ctx)

        # Check that the Lambda function was invoked with the correct parameters
        mock_lambda_client.invoke.assert_called_once()

        # Check the result
        assert 'Function test-function returned:' in result
        assert '"result": "success"' in result

    @pytest.mark.asyncio
    @patch('awslabs.lambda_mcp_server.server.lambda_client')
    async def test_lambda_function_tool_error(self, mock_lambda_client):
        """Test the Lambda function tool with an error."""
        # Set up the mock
        mock_payload = MagicMock()
        mock_payload.read.return_value = b'{"error": "Function error"}'
        mock_lambda_client.invoke.return_value = {
            'StatusCode': 200,
            'FunctionError': 'Handled',
            'Payload': mock_payload,
        }

        # Create a mock MCP server
        mock_mcp = MagicMock(spec=FastMCP)

        # Create a mock tool function
        async def mock_tool_function(parameters, ctx):
            return await invoke_lambda_function_impl('error-function', parameters, ctx)

        # Create a mock context
        ctx = MagicMock(spec=Context)
        ctx.info = AsyncMock()
        ctx.error = AsyncMock()

        # Call the function
        with patch('awslabs.lambda_mcp_server.server.mcp', mock_mcp):
            result = await mock_tool_function({'param': 'value'}, ctx)

        # Check that the Lambda function was invoked with the correct parameters
        mock_lambda_client.invoke.assert_called_once()

        # Check that the context methods were called
        ctx.info.assert_called()
        ctx.error.assert_called_once()

        # Check the result
        assert 'Function error-function returned with error:' in result
