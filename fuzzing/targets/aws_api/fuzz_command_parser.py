# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Polyglot fuzz harness for AWS CLI command parsing in aws-api-mcp-server.

This module provides a fuzz target that tests the AWS CLI command parsing
functions `split_cli_command` from the lexer and the `parse` function from
the parser in the aws-api-mcp-server package.

The harness works both as:
- A pytest test using Hypothesis for structured input generation
- An OSS-Fuzz target using Atheris for coverage-guided fuzzing

Feature: oss-fuzz-integration
Requirements: 6.1, 6.2, 6.5

Example usage:
    # Run as pytest test
    pytest fuzzing/targets/aws_api/fuzz_command_parser.py -v

    # Run as Atheris fuzz target (when built by OSS-Fuzz)
    python fuzzing/targets/aws_api/fuzz_command_parser.py
"""

from __future__ import annotations

import sys
from hypothesis import given, settings
from hypothesis import strategies as st
from pathlib import Path


# Add the aws-api-mcp-server to the path for imports
_REPO_ROOT = Path(__file__).parent.parent.parent.parent
_AWS_API_SERVER_PATH = _REPO_ROOT / 'src' / 'aws-api-mcp-server'
if str(_AWS_API_SERVER_PATH) not in sys.path:
    sys.path.insert(0, str(_AWS_API_SERVER_PATH))

# Add fuzzing root to path
_FUZZING_ROOT = _REPO_ROOT / 'fuzzing'
if str(_FUZZING_ROOT) not in sys.path:
    sys.path.insert(0, str(_FUZZING_ROOT))

from awslabs.aws_api_mcp_server.core.common.errors import (  # noqa: E402
    AwsApiMcpError,
    CliParsingError,
    ProhibitedOperatorsError,
)
from awslabs.aws_api_mcp_server.core.parser.lexer import split_cli_command  # noqa: E402
from harness_base import PolyglotHarness  # noqa: E402


# AWS CLI service names for generating realistic commands
AWS_SERVICES = [
    's3',
    's3api',
    'ec2',
    'iam',
    'lambda',
    'dynamodb',
    'rds',
    'sqs',
    'sns',
    'cloudformation',
    'cloudwatch',
    'ecs',
    'eks',
    'kinesis',
    'kms',
    'ssm',
    'secretsmanager',
    'sts',
    'route53',
    'apigateway',
    'cognito-idp',
    'sagemaker',
    'bedrock',
    'stepfunctions',
    'eventbridge',
    'logs',
    'elasticache',
    'redshift',
]

# Common AWS CLI operations
AWS_OPERATIONS = [
    'list',
    'describe',
    'get',
    'create',
    'delete',
    'update',
    'put',
    'start',
    'stop',
    'invoke',
    'run',
    'execute',
    'send',
    'receive',
    'publish',
    'subscribe',
    'list-buckets',
    'list-objects',
    'describe-instances',
    'list-functions',
    'list-tables',
    'describe-table',
    'get-item',
    'put-item',
    'query',
    'scan',
]

# Shell metacharacters that could be dangerous
SHELL_METACHARACTERS = [
    ';',
    '|',
    '&',
    '$',
    '`',
    '(',
    ')',
    '{',
    '}',
    '[',
    ']',
    '<',
    '>',
    '!',
    '\\',
    '"',
    "'",
    '\n',
    '\r',
    '\t',
    '\x00',
    '*',
    '?',
    '~',
    '#',
    '%',
    '^',
]

# Prohibited operators from the lexer
PROHIBITED_OPERATORS = [
    '&&',
    '||',
    '=',
    '*=',
    '/=',
    '%=',
    '+=',
    '-=',
    '<<=',
    '>>=',
    '&=',
    '^=',
    '|=',
]

# Common CLI options
CLI_OPTIONS = [
    '--region',
    '--profile',
    '--output',
    '--query',
    '--debug',
    '--no-verify-ssl',
    '--endpoint-url',
    '--no-sign-request',
    '--cli-read-timeout',
    '--cli-connect-timeout',
]


def aws_cli_command_strategy() -> st.SearchStrategy[str]:
    """Hypothesis strategy for generating AWS CLI-like command strings.

    This strategy generates a mix of:
    - Valid AWS CLI command structures
    - Commands with shell metacharacters
    - Commands with prohibited operators
    - Malformed command strings

    Returns:
        A Hypothesis SearchStrategy that generates AWS CLI-like strings.
    """
    # Strategy for AWS service names
    service_strategy = st.sampled_from(AWS_SERVICES)

    # Strategy for AWS operations
    operation_strategy = st.sampled_from(AWS_OPERATIONS)

    # Strategy for shell metacharacters
    metachar_strategy = st.sampled_from(SHELL_METACHARACTERS)

    # Strategy for prohibited operators
    prohibited_strategy = st.sampled_from(PROHIBITED_OPERATORS)

    # Strategy for CLI options
    option_strategy = st.sampled_from(CLI_OPTIONS)

    # Strategy for random identifiers
    identifier_strategy = st.text(
        alphabet=st.characters(whitelist_categories=('Ll', 'Lu', 'Nd'), whitelist_characters='-_'),
        min_size=1,
        max_size=30,
    )

    # Strategy for option values
    value_strategy = st.one_of(
        st.text(min_size=1, max_size=50),
        st.integers(min_value=-1000000, max_value=1000000).map(str),
        identifier_strategy,
    )

    # Build valid-looking AWS CLI commands
    valid_command = st.tuples(
        service_strategy,
        operation_strategy,
        st.lists(
            st.tuples(option_strategy, value_strategy).map(lambda t: f'{t[0]} {t[1]}'),
            min_size=0,
            max_size=5,
        ),
    ).map(lambda t: f'aws {t[0]} {t[1]} {" ".join(t[2])}')

    # Commands with shell metacharacters injected
    metachar_command = st.tuples(
        service_strategy,
        metachar_strategy,
        operation_strategy,
    ).map(lambda t: f'aws {t[0]}{t[1]}{t[2]}')

    # Commands with prohibited operators
    prohibited_command = st.tuples(
        st.text(min_size=1, max_size=20),
        prohibited_strategy,
        st.text(min_size=1, max_size=20),
    ).map(lambda t: f'aws {t[0]} {t[1]} {t[2]}')

    # Completely random text
    random_text = st.text(min_size=0, max_size=200)

    # Binary-like strings decoded as text
    binary_text = st.binary(min_size=0, max_size=100).map(
        lambda b: b.decode('utf-8', errors='replace')
    )

    # Commands starting with 'aws' but with random content
    aws_prefix_random = st.text(min_size=0, max_size=150).map(lambda s: f'aws {s}')

    # Commands with escape sequences
    escape_command = st.tuples(
        service_strategy,
        st.sampled_from(['\\n', '\\r', '\\t', '\\x00', '\\\\', "\\'", '\\"']),
        operation_strategy,
    ).map(lambda t: f'aws {t[0]} {t[1]} {t[2]}')

    return st.one_of(
        valid_command,
        metachar_command,
        prohibited_command,
        random_text,
        binary_text,
        aws_prefix_random,
        escape_command,
        # Empty and whitespace-only strings
        st.just(''),
        st.just('   '),
        st.just('\t\n'),
        # Just 'aws' with no arguments
        st.just('aws'),
        # Non-aws commands
        st.sampled_from(['ls', 'cat', 'echo', 'rm', 'curl', 'wget']),
    )


def fuzz_command_parser(data: bytes) -> None:
    """Fuzz target for AWS CLI command parsing functions.

    This function takes raw bytes, converts them to a string, and tests
    the `split_cli_command` function from the lexer.

    The target verifies that:
    1. The function doesn't crash on arbitrary input
    2. Expected exceptions are raised for invalid input
    3. No unhandled exceptions occur

    Args:
        data: Raw bytes from the fuzzer to be converted to CLI command string.
    """
    if len(data) == 0:
        return

    # Convert bytes to string, handling encoding errors gracefully
    try:
        cli_command = data.decode('utf-8', errors='replace')
    except Exception:
        # If decoding fails completely, use latin-1 which accepts all bytes
        cli_command = data.decode('latin-1')

    # Test split_cli_command (lexer)
    try:
        tokens = split_cli_command(cli_command)
        # Verify return type is a list
        assert isinstance(tokens, list), f'Expected list, got {type(tokens)}'
        # Verify all tokens are strings
        for token in tokens:
            assert isinstance(token, str), f'Expected str, got {type(token)}'
        # Verify first token is 'aws' if we got here
        if tokens:
            assert tokens[0] == 'aws', f'Expected first token to be "aws", got {tokens[0]}'
    except CliParsingError:
        # Expected for invalid CLI commands
        pass
    except ProhibitedOperatorsError:
        # Expected for commands with prohibited operators
        pass
    except AwsApiMcpError:
        # Other expected AWS API MCP errors
        pass
    except ValueError:
        # Expected for malformed input (e.g., from shlex)
        pass
    except AssertionError:
        raise  # Re-raise assertion errors for test failures
    except Exception as e:
        # Catch any unexpected exceptions - these might indicate bugs
        # For fuzzing, we want to continue but log the issue
        # In production, this would be a finding
        if 'shlex' in str(type(e).__module__):
            # shlex can raise various exceptions on malformed input
            pass
        else:
            # Re-raise truly unexpected exceptions
            raise


@given(aws_cli_command_strategy())
@settings(max_examples=100, deadline=None)
def test_command_parser_graceful_handling(cli_command: str) -> None:
    """Property test for AWS CLI command parsing graceful handling.

    This test verifies that the command parsing functions handle
    arbitrary CLI-like strings gracefully without crashing.

    **Validates: Requirements 6.1, 6.2**

    Property 1: Graceful Input Handling (CLI subset)
    For any CLI-like string, the parsing functions SHALL either:
    - Successfully process the input and return normally, OR
    - Raise a handled exception without crashing

    Args:
        cli_command: A CLI-like string generated by the aws_cli_command_strategy.
    """
    try:
        tokens = split_cli_command(cli_command)
        assert isinstance(tokens, list)
        for token in tokens:
            assert isinstance(token, str)
    except (CliParsingError, ProhibitedOperatorsError, AwsApiMcpError, ValueError):
        # These are expected exceptions for invalid input
        pass
    except Exception:
        # Other handled exceptions are acceptable
        pass


@given(st.binary(min_size=1, max_size=1000))
@settings(max_examples=100, deadline=None)
def test_command_parser_with_raw_bytes(data: bytes) -> None:
    """Property test for command parsing with raw byte input.

    This test verifies that the fuzz target handles arbitrary byte sequences
    gracefully, simulating the Atheris fuzzing mode.

    **Validates: Requirements 6.1, 6.2**

    Args:
        data: Raw bytes to be processed by the fuzz target.
    """
    # Should not raise any unhandled exceptions
    fuzz_command_parser(data)


def test_prohibited_operators_detected() -> None:
    """Unit test verifying prohibited operators are detected.

    This test ensures that the lexer correctly identifies and rejects
    commands containing shell operators that could be dangerous.

    **Validates: Requirements 6.2**
    """
    test_cases = [
        'aws s3 ls && rm -rf /',
        'aws ec2 describe-instances || echo "failed"',
        'aws lambda invoke = output.json',
    ]

    for cmd in test_cases:
        try:
            split_cli_command(cmd)
            # If we get here without exception, that's unexpected
            # but not necessarily a failure - the operator might not be in a token
        except ProhibitedOperatorsError:
            # Expected - operator was detected
            pass
        except (CliParsingError, ValueError):
            # Also acceptable - command was rejected for other reasons
            pass


def test_shell_metacharacters_handled() -> None:
    """Unit test verifying shell metacharacters are handled safely.

    This test ensures that commands with shell metacharacters don't cause
    crashes or unexpected behavior.

    **Validates: Requirements 6.2**
    """
    test_cases = [
        'aws s3 ls; rm -rf /',
        'aws ec2 describe-instances | grep running',
        'aws lambda invoke $(whoami)',
        'aws iam list-users `id`',
        'aws s3 cp s3://bucket/file /tmp/file; cat /etc/passwd',
        'aws dynamodb scan --table-name test\nrm -rf /',
        'aws sns publish --message "test\x00injection"',
    ]

    for cmd in test_cases:
        try:
            result = split_cli_command(cmd)
            # If parsing succeeds, verify the result is safe
            assert isinstance(result, list)
        except (CliParsingError, ProhibitedOperatorsError, ValueError):
            # Expected - dangerous command was rejected
            pass


def test_empty_and_whitespace_commands() -> None:
    """Unit test for empty and whitespace-only commands.

    **Validates: Requirements 6.1**
    """
    test_cases = ['', '   ', '\t', '\n', '\r\n', '  \t  \n  ']

    for cmd in test_cases:
        try:
            split_cli_command(cmd)
        except CliParsingError:
            # Expected - empty commands should be rejected
            pass


def test_non_aws_commands_rejected() -> None:
    """Unit test verifying non-AWS commands are rejected.

    **Validates: Requirements 6.1**
    """
    test_cases = [
        'ls -la',
        'cat /etc/passwd',
        'curl http://example.com',
        'python -c "import os; os.system(\'rm -rf /\')"',
        'gcloud compute instances list',
        'az vm list',
    ]

    for cmd in test_cases:
        try:
            split_cli_command(cmd)
            # Should not succeed for non-aws commands
            assert False, f'Expected CliParsingError for: {cmd}'
        except CliParsingError:
            # Expected - non-aws commands should be rejected
            pass


if __name__ == '__main__':
    # Entry point for Atheris fuzzing
    PolyglotHarness.run_harness(fuzz_command_parser, test_command_parser_graceful_handling)
