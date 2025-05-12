"""Test fixtures for the stepfunctions-mcp-server tests."""

import json
import pytest
from unittest.mock import MagicMock


@pytest.fixture
def mock_lambda_client():
    """Create a mock boto3 client (will be updated to Step Functions client in phase 2)."""
    mock_client = MagicMock()

    # Mock list_functions response (will be updated to list_state_machines in phase 2)
    mock_client.list_functions.return_value = {
        'Functions': [
            {
                'FunctionName': 'test-state-machine-1',
                'FunctionArn': 'arn:aws:states:us-east-1:123456789012:stateMachine:test-state-machine-1',
                'Description': 'Test state machine 1 description',
            },
            {
                'FunctionName': 'test-state-machine-2',
                'FunctionArn': 'arn:aws:states:us-east-1:123456789012:stateMachine:test-state-machine-2',
                'Description': 'Test state machine 2 description',
            },
            {
                'FunctionName': 'prefix-test-state-machine-3',
                'FunctionArn': 'arn:aws:states:us-east-1:123456789012:stateMachine:prefix-test-state-machine-3',
                'Description': 'Test state machine 3 with prefix',
            },
            {
                'FunctionName': 'other-state-machine',
                'FunctionArn': 'arn:aws:states:us-east-1:123456789012:stateMachine:other-state-machine',
                'Description': '',  # Empty description
            },
        ]
    }

    # Mock list_tags response
    def mock_list_tags(Resource):
        if 'test-state-machine-1' in Resource:
            return {'Tags': {'test-key': 'test-value'}}
        elif 'test-state-machine-2' in Resource:
            return {'Tags': {'other-key': 'other-value'}}
        elif 'prefix-test-state-machine-3' in Resource:
            return {'Tags': {'test-key': 'test-value'}}
        else:
            return {'Tags': {}}

    mock_client.list_tags.side_effect = mock_list_tags

    # Mock invoke response (will be updated to start_execution in phase 2)
    def mock_invoke(FunctionName, InvocationType, Payload):
        if FunctionName == 'test-state-machine-1':
            mock_payload = MagicMock()
            mock_payload.read.return_value = json.dumps({'result': 'success'}).encode()
            return {
                'StatusCode': 200,
                'Payload': mock_payload,
            }
        elif FunctionName == 'test-state-machine-2':
            mock_payload = MagicMock()
            mock_payload.read.return_value = b'Non-JSON response'
            return {
                'StatusCode': 200,
                'Payload': mock_payload,
            }
        elif FunctionName == 'error-state-machine':
            mock_payload = MagicMock()
            mock_payload.read.return_value = json.dumps({'error': 'State machine error'}).encode()
            return {
                'StatusCode': 200,
                'FunctionError': 'Handled',
                'Payload': mock_payload,
            }
        else:
            mock_payload = MagicMock()
            mock_payload.read.return_value = json.dumps({}).encode()
            return {
                'StatusCode': 200,
                'Payload': mock_payload,
            }

    mock_client.invoke.side_effect = mock_invoke

    return mock_client
