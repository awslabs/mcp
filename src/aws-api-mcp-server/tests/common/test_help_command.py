import pytest
from awslabs.aws_api_mcp_server.core.common.help_command import (
    _clean_description,
    _clean_text,
    generate_help_document,
)
from unittest.mock import MagicMock, patch


class MockDoc:
    """Mock class for ReSTDocument."""

    def __init__(self, content=b''):
        """Initialize the mock document."""
        self.content = content

    def getvalue(self):
        """Get the value of the document."""
        return self.content


def test_clean_text():
    """Test cleaning text."""
    assert _clean_text('  hello   world  ') == 'hello world'
    assert _clean_text('hello\nworld') == 'hello world'


def test_clean_description():
    """Test cleaning description."""
    desc = '=== Description ===\n\nThis is a description.'
    assert _clean_description(desc) == 'This is a description.'

    desc = 'This is a description.'
    assert _clean_description(desc) == 'This is a description.'


@patch('awslabs.aws_api_mcp_server.core.common.help_command.driver')
def test_generate_help_document_unknown_command(mock_driver):
    """Test generating help document for unknown command."""
    service_name = 'unknown'
    operation_name = 'op'

    mock_command_table = MagicMock()
    mock_driver._get_command_table.return_value = mock_command_table

    mock_command_table.__getitem__.return_value = (
        MagicMock()
    )  # Neither BasicCommand nor ServiceCommand

    result = generate_help_document(service_name, operation_name)
    assert result is None


@pytest.mark.parametrize(
    'service_name, operation_name, expected_text, expected_params',
    [
        ('s3', 'ls', 'List S3 objects and common prefixes', ['recursive', 'page-size']),
        (
            'ec2',
            'describe-instances',
            'Describes the specified instances',
            ['filters', 'instance-ids'],
        ),
        ('lambda', 'list-functions', 'Returns a list of Lambda functions', ['max-items']),
        ('sts', 'get-caller-identity', 'Returns details about the IAM user', []),
        ('dynamodb', 'list-tables', 'Returns an array of table names', ['max-items']),
        ('iam', 'get-user', 'Retrieves information about the specified IAM user', ['user-name']),
        ('sns', 'publish', 'Sends a message to an Amazon SNS topic', ['topic-arn', 'message']),
        (
            'sqs',
            'send-message',
            'Delivers a message to the specified queue',
            ['queue-url', 'message-body'],
        ),
    ],
)
def test_generate_help_document_real_aws_commands(
    service_name, operation_name, expected_text, expected_params
):
    """Test generating help documents for real AWS CLI commands."""
    result = generate_help_document(service_name, operation_name)

    assert result is not None
    assert result['command'] == f'aws {service_name} {operation_name}'
    assert expected_text in result['description']

    for param in expected_params:
        assert param in result['parameters']
