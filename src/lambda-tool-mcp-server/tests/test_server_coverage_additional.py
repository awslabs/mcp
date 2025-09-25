"""Additional tests specifically targeting remaining uncovered lines in the server module."""

import logging
import pytest
from unittest.mock import MagicMock, patch


with pytest.MonkeyPatch().context() as CTX:
    CTX.setattr('boto3.Session', MagicMock)
    from awslabs.lambda_tool_mcp_server.server import (
        register_lambda_functions,
    )


class TestRegisterLambdaFunctionsAdditionalCoverage:
    """Additional tests specifically for the register_lambda_functions function."""

    @patch(
        'os.environ',
        {
            'FUNCTION_TAG_KEY': 'test-key',
            'FUNCTION_TAG_VALUE': '',
        },
    )
    @patch('awslabs.lambda_tool_mcp_server.server.FUNCTION_TAG_KEY', 'test-key')
    @patch('awslabs.lambda_tool_mcp_server.server.FUNCTION_TAG_VALUE', '')
    def test_register_with_incomplete_tag_config_direct_env(self, mock_lambda_client, caplog):
        """Test registering Lambda functions with incomplete tag configuration using direct environment variables."""
        with patch('awslabs.lambda_tool_mcp_server.server.lambda_client', mock_lambda_client):
            with caplog.at_level(logging.WARNING):
                # Call the function
                register_lambda_functions()

                # Should log a warning
                assert (
                    'Both FUNCTION_TAG_KEY and FUNCTION_TAG_VALUE must be set to filter by tag'
                    in caplog.text
                )

                # This should specifically target line 229 in server.py
                assert (
                    len([record for record in caplog.records if record.levelname == 'WARNING']) > 0
                )
