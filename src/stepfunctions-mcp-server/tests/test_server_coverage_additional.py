"""Additional tests specifically targeting remaining uncovered lines in the server module."""

import logging
import pytest
from unittest.mock import MagicMock, patch


with pytest.MonkeyPatch().context() as CTX:
    CTX.setattr('boto3.Session', MagicMock)
    from awslabs.stepfunctions_mcp_server.server import (
        register_state_machines,
    )


class TestRegisterStateMachinesAdditionalCoverage:
    """Additional tests specifically for the register_state_machines function."""

    @patch(
        'os.environ',
        {
            'STATE_MACHINE_TAG_KEY': 'test-key',
            'STATE_MACHINE_TAG_VALUE': '',
        },
    )
    @patch('awslabs.stepfunctions_mcp_server.server.STATE_MACHINE_TAG_KEY', 'test-key')
    @patch('awslabs.stepfunctions_mcp_server.server.STATE_MACHINE_TAG_VALUE', '')
    def test_register_with_incomplete_tag_config_direct_env(self, mock_lambda_client, caplog):
        """Test registering Step Functions state machines with incomplete tag configuration using direct environment variables."""
        with patch('awslabs.stepfunctions_mcp_server.server.lambda_client', mock_lambda_client):
            with caplog.at_level(logging.WARNING):
                # Call the function
                register_state_machines()

                # Should log a warning
                assert (
                    'Both STATE_MACHINE_TAG_KEY and STATE_MACHINE_TAG_VALUE must be set to filter by tag'
                    in caplog.text
                )

                # This should specifically target line 229 in server.py
                assert (
                    len([record for record in caplog.records if record.levelname == 'WARNING']) > 0
                )
