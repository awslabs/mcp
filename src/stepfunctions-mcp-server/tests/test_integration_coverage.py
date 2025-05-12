"""Additional integration tests to improve coverage for the lambda-mcp-server."""

import json
import pytest
from mcp.server.fastmcp import Context, FastMCP
from unittest.mock import AsyncMock, MagicMock, patch


with pytest.MonkeyPatch().context() as CTX:
    CTX.setattr('boto3.Session', MagicMock)
    from awslabs.lambda_mcp_server.server import (
        invoke_lambda_function_impl,
    )


class TestServerIntegrationCoverage:
    """Additional integration tests for the server module to improve coverage."""

    @pytest.mark.asyncio
    @patch('awslabs.lambda_mcp_server.server.lambda_client')
    async def test_lambda_function_binary_response(self, mock_lambda_client):
        """Test the Lambda function with binary response."""
        # Set up the mock
        mock_payload = MagicMock()
        mock_payload.read.return_value = b'\x80\x81\x82\x83'  # Invalid UTF-8 sequence
        mock_lambda_client.invoke.return_value = {
            'StatusCode': 200,
            'Payload': mock_payload,
        }

        # Create a mock context
        ctx = MagicMock(spec=Context)
        ctx.info = AsyncMock()
        ctx.error = AsyncMock()

        # Call the function
        result = await invoke_lambda_function_impl('binary-function', {'param': 'value'}, ctx)

        # Check that the Lambda function was invoked with the correct parameters
        mock_lambda_client.invoke.assert_called_once()

        # Check that the context methods were called
        ctx.info.assert_called()

        # Check the result
        assert 'Function binary-function returned payload:' in result
        assert "b'\\x80\\x81\\x82\\x83'" in result

    @pytest.mark.asyncio
    @patch('awslabs.lambda_mcp_server.server.lambda_client')
    async def test_lambda_function_empty_response(self, mock_lambda_client):
        """Test the Lambda function with empty response."""
        # Set up the mock
        mock_payload = MagicMock()
        mock_payload.read.return_value = b''
        mock_lambda_client.invoke.return_value = {
            'StatusCode': 200,
            'Payload': mock_payload,
        }

        # Create a mock context
        ctx = MagicMock(spec=Context)
        ctx.info = AsyncMock()
        ctx.error = AsyncMock()

        # Call the function
        result = await invoke_lambda_function_impl('empty-function', {'param': 'value'}, ctx)

        # Check that the Lambda function was invoked with the correct parameters
        mock_lambda_client.invoke.assert_called_once()

        # Check the result
        assert "Function empty-function returned payload: b''" == result


class TestToolFunctionalityCoverage:
    """Additional tests for the functionality of the Lambda tools to improve coverage."""

    @pytest.mark.asyncio
    @patch('awslabs.lambda_mcp_server.server.lambda_client')
    async def test_lambda_function_complex_json(self, mock_lambda_client):
        """Test the Lambda function with complex JSON response."""
        # Set up the mock with complex nested JSON
        complex_json = {
            'data': {
                'nested': {
                    'array': [1, 2, 3],
                    'object': {'key': 'value'},
                    'null': None,
                    'boolean': True,
                }
            },
            'metadata': {'timestamp': '2023-01-01T00:00:00Z', 'requestId': '12345'},
        }

        mock_payload = MagicMock()
        mock_payload.read.return_value = json.dumps(complex_json).encode()
        mock_lambda_client.invoke.return_value = {
            'StatusCode': 200,
            'Payload': mock_payload,
        }

        # Create a mock MCP server
        mock_mcp = MagicMock(spec=FastMCP)

        # Create a mock tool function
        async def mock_tool_function(parameters, ctx):
            return await invoke_lambda_function_impl('complex-json-function', parameters, ctx)

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
        assert 'Function complex-json-function returned:' in result
        assert '"data": {' in result
        assert '"nested": {' in result
        assert '"array": [' in result
        assert '"metadata": {' in result
