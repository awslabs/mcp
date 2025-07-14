import pytest
import re
from awslabs.aws_api_mcp_server.core.common.errors import CliParsingError, ProhibitedOperatorsError
from awslabs.aws_api_mcp_server.core.parser.lexer import split_cli_command


@pytest.mark.parametrize(
    'command,expected_tokens',
    [
        ('aws s3 ls', ['aws', 's3', 'ls']),
        (
            'aws cloud9 list-environments --debug',
            ['aws', 'cloud9', 'list-environments', '--debug'],
        ),
        (
            'aws cloud9 list-environments --endpoint http://a.txt',
            ['aws', 'cloud9', 'list-environments', '--endpoint', 'http://a.txt'],
        ),
    ],
)
def test_split_cli_command_successfully(command, expected_tokens):
    """Test that split_cli_command tokenizes valid CLI commands correctly."""
    tokens = split_cli_command(command)
    assert tokens == expected_tokens


@pytest.mark.parametrize(
    'command,error,error_args',
    [
        ('aws s3 && rm -rf', ProhibitedOperatorsError, ['&&']),
        ('aws s3 || rm -rf', ProhibitedOperatorsError, ['||']),
        ('', CliParsingError, None),
        ('ecs rm', CliParsingError, 'The provided CLI command is not an AWS command'),
        ('aws s3 "', CliParsingError, 'No closing quotation'),
    ],
)
def test_split_cli_command_unsuccessfully(command, error, error_args):
    """Test that split_cli_command raises errors for invalid or prohibited CLI commands."""
    message = None
    if error_args:
        message = re.escape(str(error(error_args)))
    with pytest.raises(error, match=message):
        split_cli_command(command)
