"""Tests for the main function."""

import pytest
from unittest.mock import MagicMock, patch


with pytest.MonkeyPatch().context() as CTX:
    CTX.setattr('boto3.Session', MagicMock)
    from awslabs.stepfunctions_tool_mcp_server.server import main


class TestMain:
    """Tests for the main function."""

    @patch('awslabs.stepfunctions_tool_mcp_server.server.register_state_machines')
    @patch('awslabs.stepfunctions_tool_mcp_server.server.mcp')
    @patch('argparse.ArgumentParser.parse_args')
    def test_main_stdio_transport(self, mock_parse_args, mock_mcp, mock_register):
        """Test main function with stdio transport."""
        # Set up test data
        mock_parse_args.return_value = MagicMock()

        # Call the function
        main()

        # Verify results
        mock_register.assert_called_once()
        mock_mcp.run.assert_called_once_with()
