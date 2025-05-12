"""Tests specifically targeting the register_lambda_functions function."""

import logging
import pytest
from unittest.mock import MagicMock, patch


with pytest.MonkeyPatch().context() as CTX:
    CTX.setattr('boto3.Session', MagicMock)
    from awslabs.lambda_mcp_server.server import register_lambda_functions


class TestRegisterLambdaFunctionsSpecific:
    """Tests specifically for the register_lambda_functions function."""

    @patch('awslabs.lambda_mcp_server.server.FUNCTION_TAG_KEY', 'test-key')
    @patch('awslabs.lambda_mcp_server.server.FUNCTION_TAG_VALUE', '')
    @patch('awslabs.lambda_mcp_server.server.create_lambda_tool')
    def test_register_with_only_tag_key(self, mock_create_lambda_tool, mock_lambda_client, caplog):
        """Test registering Lambda functions with only tag key set."""
        with patch('awslabs.lambda_mcp_server.server.lambda_client', mock_lambda_client):
            with caplog.at_level(logging.WARNING):
                # Call the function
                register_lambda_functions()

                # Should not register any functions
                assert mock_create_lambda_tool.call_count == 0

                # Should log a warning - this specifically targets line 229
                assert (
                    'Both FUNCTION_TAG_KEY and FUNCTION_TAG_VALUE must be set to filter by tag'
                    in caplog.text
                )

    @patch('awslabs.lambda_mcp_server.server.FUNCTION_TAG_KEY', '')
    @patch('awslabs.lambda_mcp_server.server.FUNCTION_TAG_VALUE', 'test-value')
    @patch('awslabs.lambda_mcp_server.server.create_lambda_tool')
    def test_register_with_only_tag_value(
        self, mock_create_lambda_tool, mock_lambda_client, caplog
    ):
        """Test registering Lambda functions with only tag value set."""
        with patch('awslabs.lambda_mcp_server.server.lambda_client', mock_lambda_client):
            with caplog.at_level(logging.WARNING):
                # Call the function
                register_lambda_functions()

                # Should not register any functions
                assert mock_create_lambda_tool.call_count == 0

                # Should log a warning - this specifically targets line 229
                assert (
                    'Both FUNCTION_TAG_KEY and FUNCTION_TAG_VALUE must be set to filter by tag'
                    in caplog.text
                )
