"""Tests for the get_schema_arn_from_state_machine_arn function."""

import logging
import pytest
from unittest.mock import MagicMock, patch


with pytest.MonkeyPatch().context() as CTX:
    CTX.setattr('boto3.Session', MagicMock)
    from awslabs.stepfunctions_mcp_server.server import get_schema_arn_from_state_machine_arn


class TestGetSchemaArn:
    """Tests for schema ARN retrieval from state machine tags."""

    @patch('awslabs.stepfunctions_mcp_server.server.sfn_client')
    @patch(
        'awslabs.stepfunctions_mcp_server.server.STATE_MACHINE_INPUT_SCHEMA_ARN_TAG_KEY',
        'schema-arn-tag',
    )
    def test_get_schema_arn_success(self, mock_sfn_client):
        """Test successful retrieval of schema ARN from state machine tags."""
        # Set up test data
        state_machine_arn = 'arn:aws:states:us-east-1:123456789012:stateMachine:test-state-machine'
        schema_arn = 'arn:aws:schemas:us-east-1:123456789012:schema/registry/schema'

        # Set up mock response
        mock_sfn_client.list_tags_for_resource.return_value = {
            'tags': [{'key': 'schema-arn-tag', 'value': schema_arn}]
        }

        # Call the function
        result = get_schema_arn_from_state_machine_arn(state_machine_arn)

        # Verify results
        assert result == schema_arn
        mock_sfn_client.list_tags_for_resource.assert_called_once_with(
            resourceArn=state_machine_arn
        )

    @patch('awslabs.stepfunctions_mcp_server.server.sfn_client')
    @patch('awslabs.stepfunctions_mcp_server.server.STATE_MACHINE_INPUT_SCHEMA_ARN_TAG_KEY', None)
    def test_get_schema_arn_no_tag_key(self, mock_sfn_client):
        """Test when schema ARN tag key is not configured."""
        # Set up test data
        state_machine_arn = 'arn:aws:states:us-east-1:123456789012:stateMachine:test-state-machine'

        # Call the function
        result = get_schema_arn_from_state_machine_arn(state_machine_arn)

        # Verify results
        assert result is None
        mock_sfn_client.list_tags_for_resource.assert_not_called()

    @patch('awslabs.stepfunctions_mcp_server.server.sfn_client')
    @patch(
        'awslabs.stepfunctions_mcp_server.server.STATE_MACHINE_INPUT_SCHEMA_ARN_TAG_KEY',
        'schema-arn-tag',
    )
    def test_get_schema_arn_tag_not_found(self, mock_sfn_client):
        """Test when schema ARN tag is not found on the state machine."""
        # Set up test data
        state_machine_arn = 'arn:aws:states:us-east-1:123456789012:stateMachine:test-state-machine'

        # Set up mock response with different tag
        mock_sfn_client.list_tags_for_resource.return_value = {
            'tags': [{'key': 'different-tag', 'value': 'some-value'}]
        }

        # Call the function
        result = get_schema_arn_from_state_machine_arn(state_machine_arn)

        # Verify results
        assert result is None
        mock_sfn_client.list_tags_for_resource.assert_called_once_with(
            resourceArn=state_machine_arn
        )

    @patch('awslabs.stepfunctions_mcp_server.server.sfn_client')
    @patch(
        'awslabs.stepfunctions_mcp_server.server.STATE_MACHINE_INPUT_SCHEMA_ARN_TAG_KEY',
        'schema-arn-tag',
    )
    def test_get_schema_arn_error_handling(self, mock_sfn_client, caplog):
        """Test error handling during tag retrieval."""
        # Set up test data
        state_machine_arn = 'arn:aws:states:us-east-1:123456789012:stateMachine:test-state-machine'

        # Set up mock to raise an exception
        mock_sfn_client.list_tags_for_resource.side_effect = Exception('Tag retrieval error')

        # Call the function and check logging
        with caplog.at_level(logging.WARNING):
            result = get_schema_arn_from_state_machine_arn(state_machine_arn)

            # Verify results
            assert result is None
            assert 'Error checking tags for state machine' in caplog.text
            assert 'Tag retrieval error' in caplog.text

        # Verify mock calls
        mock_sfn_client.list_tags_for_resource.assert_called_once_with(
            resourceArn=state_machine_arn
        )

    @patch('awslabs.stepfunctions_mcp_server.server.sfn_client')
    @patch(
        'awslabs.stepfunctions_mcp_server.server.STATE_MACHINE_INPUT_SCHEMA_ARN_TAG_KEY',
        'schema-arn-tag',
    )
    def test_get_schema_arn_empty_tags(self, mock_sfn_client):
        """Test when state machine has no tags."""
        # Set up test data
        state_machine_arn = 'arn:aws:states:us-east-1:123456789012:stateMachine:test-state-machine'

        # Set up mock response with empty tags
        mock_sfn_client.list_tags_for_resource.return_value = {'tags': []}

        # Call the function
        result = get_schema_arn_from_state_machine_arn(state_machine_arn)

        # Verify results
        assert result is None
        mock_sfn_client.list_tags_for_resource.assert_called_once_with(
            resourceArn=state_machine_arn
        )
