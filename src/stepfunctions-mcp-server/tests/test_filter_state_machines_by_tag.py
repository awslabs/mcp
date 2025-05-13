"""Tests for the filter_state_machines_by_tag function."""

import logging
import pytest
from unittest.mock import MagicMock, patch


with pytest.MonkeyPatch().context() as CTX:
    CTX.setattr('boto3.Session', MagicMock)
    from awslabs.stepfunctions_mcp_server.server import filter_state_machines_by_tag


class TestFilterStateMachines:
    """Tests for the filter_state_machines_by_tag function."""

    @patch('awslabs.stepfunctions_mcp_server.server.sfn_client')
    def test_filter_state_machines_matching_tags(self, mock_sfn_client):
        """Test filtering state machines with matching tags."""
        # Set up test data
        state_machines = [
            {
                'name': 'test-state-machine-1',
                'stateMachineArn': 'arn:aws:states:us-east-1:123456789012:stateMachine:test-state-machine-1',
            },
            {
                'name': 'test-state-machine-2',
                'stateMachineArn': 'arn:aws:states:us-east-1:123456789012:stateMachine:test-state-machine-2',
            },
            {
                'name': 'prefix-test-state-machine-3',
                'stateMachineArn': 'arn:aws:states:us-east-1:123456789012:stateMachine:prefix-test-state-machine-3',
            },
        ]

        # Set up mock responses
        mock_sfn_client.list_tags_for_resource.side_effect = [
            {'tags': [{'key': 'test-key', 'value': 'test-value'}]},  # First state machine
            {'tags': []},  # Second state machine
            {'tags': [{'key': 'test-key', 'value': 'test-value'}]},  # Third state machine
        ]

        # Call the function
        result = filter_state_machines_by_tag(state_machines, 'test-key', 'test-value')

        # Verify results
        assert len(result) == 2
        assert result[0]['name'] == 'test-state-machine-1'
        assert result[1]['name'] == 'prefix-test-state-machine-3'

        # Verify mock calls
        assert mock_sfn_client.list_tags_for_resource.call_count == 3

    @patch('awslabs.stepfunctions_mcp_server.server.sfn_client')
    def test_filter_state_machines_no_matching_tags(self, mock_sfn_client):
        """Test filtering state machines with no matching tags."""
        # Set up test data
        state_machines = [
            {
                'name': 'test-state-machine-1',
                'stateMachineArn': 'arn:aws:states:us-east-1:123456789012:stateMachine:test-state-machine-1',
            },
            {
                'name': 'test-state-machine-2',
                'stateMachineArn': 'arn:aws:states:us-east-1:123456789012:stateMachine:test-state-machine-2',
            },
        ]

        # Set up mock responses
        mock_sfn_client.list_tags_for_resource.return_value = {'tags': []}

        # Call the function
        result = filter_state_machines_by_tag(
            state_machines, 'non-existent-key', 'non-existent-value'
        )

        # Verify results
        assert len(result) == 0

        # Verify mock calls
        assert mock_sfn_client.list_tags_for_resource.call_count == 2

    @patch('awslabs.stepfunctions_mcp_server.server.sfn_client')
    def test_filter_state_machines_error_handling(self, mock_sfn_client, caplog):
        """Test error handling when getting tags."""
        # Set up test data
        state_machines = [
            {
                'name': 'test-state-machine-1',
                'stateMachineArn': 'arn:aws:states:us-east-1:123456789012:stateMachine:test-state-machine-1',
            },
        ]

        # Set up mock to raise an exception
        mock_sfn_client.list_tags_for_resource.side_effect = Exception('Access denied')

        # Call the function and check logging
        with caplog.at_level(logging.WARNING):
            result = filter_state_machines_by_tag(state_machines, 'test-key', 'test-value')

            # Verify results
            assert len(result) == 0

            # Verify warning was logged
            assert 'Error getting tags for state machine test-state-machine-1' in caplog.text
            assert 'Access denied' in caplog.text

        # Verify mock calls
        mock_sfn_client.list_tags_for_resource.assert_called_once()

    @patch('awslabs.stepfunctions_mcp_server.server.sfn_client')
    def test_filter_state_machines_mixed_responses(self, mock_sfn_client):
        """Test filtering state machines with mixed tag responses."""
        # Set up test data
        state_machines = [
            {
                'name': 'success-machine',
                'stateMachineArn': 'arn:aws:states:us-east-1:123456789012:stateMachine:success-machine',
            },
            {
                'name': 'error-machine',
                'stateMachineArn': 'arn:aws:states:us-east-1:123456789012:stateMachine:error-machine',
            },
            {
                'name': 'empty-tags-machine',
                'stateMachineArn': 'arn:aws:states:us-east-1:123456789012:stateMachine:empty-tags-machine',
            },
        ]

        # Set up mixed mock responses
        mock_sfn_client.list_tags_for_resource.side_effect = [
            {'tags': [{'key': 'test-key', 'value': 'test-value'}]},  # Success case
            Exception('Access denied'),  # Error case
            {'tags': []},  # Empty tags case
        ]

        # Call the function
        result = filter_state_machines_by_tag(state_machines, 'test-key', 'test-value')

        # Verify results
        assert len(result) == 1
        assert result[0]['name'] == 'success-machine'

        # Verify mock calls
        assert mock_sfn_client.list_tags_for_resource.call_count == 3
