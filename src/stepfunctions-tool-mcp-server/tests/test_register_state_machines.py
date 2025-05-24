"""Tests for the register_state_machines function."""

import logging
import pytest
from unittest.mock import MagicMock, patch


with pytest.MonkeyPatch().context() as CTX:
    CTX.setattr('boto3.Session', MagicMock)
    from awslabs.stepfunctions_tool_mcp_server.server import mcp, register_state_machines


class TestRegisterStateMachines:
    """Tests for the register_state_machines function."""

    @patch('awslabs.stepfunctions_tool_mcp_server.server.sfn_client')
    @patch('awslabs.stepfunctions_tool_mcp_server.server.STATE_MACHINE_PREFIX', 'prefix-')
    @patch('awslabs.stepfunctions_tool_mcp_server.server.create_state_machine_tool')
    def test_register_machines_with_prefix(self, mock_create_tool, mock_sfn_client):
        """Test registering state machines filtered by prefix."""
        # Set up test data
        mock_sfn_client.list_state_machines.return_value = {
            'stateMachines': [
                {
                    'name': 'test-state-machine',
                    'stateMachineArn': 'arn:aws:states:us-east-1:123456789012:stateMachine:test-state-machine',
                    'type': 'STANDARD',
                },
                {
                    'name': 'prefix-test-machine',
                    'stateMachineArn': 'arn:aws:states:us-east-1:123456789012:stateMachine:prefix-test-machine',
                    'type': 'STANDARD',
                },
            ]
        }

        # Call the function
        register_state_machines()

        # Verify results
        assert mock_create_tool.call_count == 1
        mock_create_tool.assert_called_with(
            'prefix-test-machine',
            'arn:aws:states:us-east-1:123456789012:stateMachine:prefix-test-machine',
            'STANDARD',
            'AWS Step Functions state machine: prefix-test-machine',
            None,
        )

    @patch('awslabs.stepfunctions_tool_mcp_server.server.sfn_client')
    @patch(
        'awslabs.stepfunctions_tool_mcp_server.server.STATE_MACHINE_LIST', ['machine1', 'machine2']
    )
    @patch('awslabs.stepfunctions_tool_mcp_server.server.create_state_machine_tool')
    def test_register_machines_with_list(self, mock_create_tool, mock_sfn_client):
        """Test registering state machines filtered by list."""
        # Set up test data
        mock_sfn_client.list_state_machines.return_value = {
            'stateMachines': [
                {
                    'name': 'machine1',
                    'stateMachineArn': 'arn:aws:states:us-east-1:123456789012:stateMachine:machine1',
                    'type': 'STANDARD',
                },
                {
                    'name': 'machine2',
                    'stateMachineArn': 'arn:aws:states:us-east-1:123456789012:stateMachine:machine2',
                    'type': 'STANDARD',
                },
                {
                    'name': 'machine3',
                    'stateMachineArn': 'arn:aws:states:us-east-1:123456789012:stateMachine:machine3',
                    'type': 'STANDARD',
                },
            ]
        }

        # Call the function
        register_state_machines()

        # Verify results
        assert mock_create_tool.call_count == 2
        mock_create_tool.assert_any_call(
            'machine1',
            'arn:aws:states:us-east-1:123456789012:stateMachine:machine1',
            'STANDARD',
            'AWS Step Functions state machine: machine1',
            None,
        )
        mock_create_tool.assert_any_call(
            'machine2',
            'arn:aws:states:us-east-1:123456789012:stateMachine:machine2',
            'STANDARD',
            'AWS Step Functions state machine: machine2',
            None,
        )

    @patch('awslabs.stepfunctions_tool_mcp_server.server.sfn_client')
    @patch('awslabs.stepfunctions_tool_mcp_server.server.STATE_MACHINE_TAG_KEY', 'test-key')
    @patch('awslabs.stepfunctions_tool_mcp_server.server.STATE_MACHINE_TAG_VALUE', 'test-value')
    @patch('awslabs.stepfunctions_tool_mcp_server.server.create_state_machine_tool')
    def test_register_machines_with_tags(self, mock_create_tool, mock_sfn_client):
        """Test registering state machines filtered by tags."""
        # Set up test data
        mock_sfn_client.list_state_machines.return_value = {
            'stateMachines': [
                {
                    'name': 'tagged-machine',
                    'stateMachineArn': 'arn:aws:states:us-east-1:123456789012:stateMachine:tagged-machine',
                    'type': 'STANDARD',
                },
            ]
        }
        mock_sfn_client.list_tags_for_resource.return_value = {
            'tags': [{'key': 'test-key', 'value': 'test-value'}]
        }

        # Call the function
        register_state_machines()

        # Verify results
        mock_create_tool.assert_called_once_with(
            'tagged-machine',
            'arn:aws:states:us-east-1:123456789012:stateMachine:tagged-machine',
            'STANDARD',
            'AWS Step Functions state machine: tagged-machine',
            None,
        )

    @patch('awslabs.stepfunctions_tool_mcp_server.server.sfn_client')
    @patch('awslabs.stepfunctions_tool_mcp_server.server.create_state_machine_tool')
    def test_register_machines_with_comments(self, mock_create_tool, mock_sfn_client):
        """Test registering state machines with workflow comments."""
        # Set up test data
        mock_sfn_client.list_state_machines.return_value = {
            'stateMachines': [
                {
                    'name': 'test-machine',
                    'stateMachineArn': 'arn:aws:states:us-east-1:123456789012:stateMachine:test-machine',
                    'type': 'STANDARD',
                },
            ]
        }
        mock_sfn_client.describe_state_machine.return_value = {
            'description': 'Test Description',
            'definition': '{"Comment": "Workflow Comment", "StartAt": "State1", "States": {"State1": {"Type": "Pass", "End": true}}}',
        }

        # Call the function
        register_state_machines()

        # Verify results
        mock_create_tool.assert_called_once_with(
            'test-machine',
            'arn:aws:states:us-east-1:123456789012:stateMachine:test-machine',
            'STANDARD',
            'Test Description\n\nWorkflow Description: Workflow Comment',
            None,
        )

    @patch('awslabs.stepfunctions_tool_mcp_server.server.sfn_client')
    @patch('awslabs.stepfunctions_tool_mcp_server.server.STATE_MACHINE_TAG_KEY', 'test-key')
    @patch('awslabs.stepfunctions_tool_mcp_server.server.STATE_MACHINE_TAG_VALUE', '')
    def test_register_machines_incomplete_tag_config(self, mock_sfn_client, caplog):
        """Test registering state machines with incomplete tag configuration."""
        # Set up test data
        mock_sfn_client.list_state_machines.return_value = {'stateMachines': []}

        # Call the function and check logging
        with caplog.at_level(logging.WARNING):
            register_state_machines()

            # Verify warning was logged
            assert (
                'Both STATE_MACHINE_TAG_KEY and STATE_MACHINE_TAG_VALUE must be set to filter by tag'
                in caplog.text
            )

    @patch('awslabs.stepfunctions_tool_mcp_server.server.sfn_client')
    def test_register_machines_error_handling(self, mock_sfn_client, caplog):
        """Test error handling during state machine registration."""
        # Set up mock to raise an exception
        mock_sfn_client.list_state_machines.side_effect = Exception('List error')

        # Call the function and check logging
        with caplog.at_level(logging.ERROR):
            register_state_machines()

            # Verify error was logged
            assert 'Error registering Step Functions state machines as tools' in caplog.text
            assert 'List error' in caplog.text

    def test_mcp_server_initialization(self):
        """Test MCP server initialization."""
        # Verify server configuration
        assert mcp.name == 'awslabs.stepfunctions-tool-mcp-server'
        assert (
            mcp.instructions is not None
            and 'Use AWS Step Functions state machines' in mcp.instructions
        )
        assert 'pydantic' in mcp.dependencies
        assert 'boto3' in mcp.dependencies
