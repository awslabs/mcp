"""Tests specifically targeting the register_state_machines function."""

import logging
import pytest
from unittest.mock import MagicMock, patch


with pytest.MonkeyPatch().context() as CTX:
    CTX.setattr('boto3.Session', MagicMock)
    from awslabs.stepfunctions_mcp_server.server import register_state_machines


class TestRegisterStateMachinesSpecific:
    """Tests specifically for the register_state_machines function."""

    @patch('awslabs.stepfunctions_mcp_server.server.STATE_MACHINE_TAG_KEY', 'test-key')
    @patch('awslabs.stepfunctions_mcp_server.server.STATE_MACHINE_TAG_VALUE', '')
    @patch('awslabs.stepfunctions_mcp_server.server.create_state_machine_tool')
    def test_register_with_only_tag_key(self, mock_create_state_machine_tool, mock_lambda_client, caplog):
        """Test registering Step Functions state machines with only tag key set."""
        with patch('awslabs.stepfunctions_mcp_server.server.lambda_client', mock_lambda_client):
            with caplog.at_level(logging.WARNING):
                # Call the function
                register_state_machines()

                # Should not register any state machines
                assert mock_create_state_machine_tool.call_count == 0

                # Should log a warning - this specifically targets line 229
                assert (
                    'Both STATE_MACHINE_TAG_KEY and STATE_MACHINE_TAG_VALUE must be set to filter by tag'
                    in caplog.text
                )

    @patch('awslabs.stepfunctions_mcp_server.server.STATE_MACHINE_TAG_KEY', '')
    @patch('awslabs.stepfunctions_mcp_server.server.STATE_MACHINE_TAG_VALUE', 'test-value')
    @patch('awslabs.stepfunctions_mcp_server.server.create_state_machine_tool')
    def test_register_with_only_tag_value(
        self, mock_create_state_machine_tool, mock_lambda_client, caplog
    ):
        """Test registering Step Functions state machines with only tag value set."""
        with patch('awslabs.stepfunctions_mcp_server.server.lambda_client', mock_lambda_client):
            with caplog.at_level(logging.WARNING):
                # Call the function
                register_state_machines()

                # Should not register any state machines
                assert mock_create_state_machine_tool.call_count == 0

                # Should log a warning - this specifically targets line 229
                assert (
                    'Both STATE_MACHINE_TAG_KEY and STATE_MACHINE_TAG_VALUE must be set to filter by tag'
                    in caplog.text
                )
