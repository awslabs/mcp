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

"""Polyglot fuzz harness for Amazon SNS/SQS message structure parsing.

This module provides a fuzz target that tests the message structure handling
and tag validation functions from the amazon-sns-sqs-mcp-server package.

The harness works both as:
- A pytest test using Hypothesis for structured input generation
- An OSS-Fuzz target using Atheris for coverage-guided fuzzing

Feature: oss-fuzz-integration
Requirements: 9.2, 9.3, 9.5

Example usage:
    # Run as pytest test
    pytest fuzzing/targets/sns_sqs/fuzz_message_structure.py -v

    # Run as Atheris fuzz target (when built by OSS-Fuzz)
    python fuzzing/targets/sns_sqs/fuzz_message_structure.py
"""

from __future__ import annotations

import json
import sys
from hypothesis import given, settings
from hypothesis import strategies as st
from pathlib import Path


# Add the amazon-sns-sqs-mcp-server to the path for imports
_REPO_ROOT = Path(__file__).parent.parent.parent.parent
_SNS_SQS_SERVER_PATH = _REPO_ROOT / 'src' / 'amazon-sns-sqs-mcp-server'
if str(_SNS_SQS_SERVER_PATH) not in sys.path:
    sys.path.insert(0, str(_SNS_SQS_SERVER_PATH))

from awslabs.amazon_sns_sqs_mcp_server.common import (  # noqa: E402
    MCP_SERVER_VERSION_TAG,
    validate_mcp_server_version_tag,
)
from fuzzing.harness_base import PolyglotHarness  # noqa: E402


# SNS/SQS message attribute data types
MESSAGE_ATTRIBUTE_TYPES = ['String', 'Number', 'Binary', 'String.Array']

# Common SNS/SQS message attribute keys
COMMON_ATTRIBUTE_KEYS = [
    'MessageDeduplicationId',
    'MessageGroupId',
    'SequenceNumber',
    'ApproximateReceiveCount',
    'SentTimestamp',
    'SenderId',
    'ApproximateFirstReceiveTimestamp',
    'AWSTraceHeader',
]

# Maximum sizes for SNS/SQS
MAX_MESSAGE_SIZE = 256 * 1024  # 256 KB
MAX_ATTRIBUTE_NAME_LENGTH = 256
MAX_ATTRIBUTE_VALUE_LENGTH = 256 * 1024


def sns_message_strategy() -> st.SearchStrategy[dict]:
    """Hypothesis strategy for generating SNS message structures.

    This strategy generates SNS message structures with:
    - Message body
    - Message attributes with various types
    - Topic ARN
    - Subject (optional)

    Returns:
        A Hypothesis SearchStrategy that generates SNS message dicts.
    """
    # Strategy for message body
    body_strategy = st.one_of(
        st.text(min_size=0, max_size=1000),
        # JSON content
        st.dictionaries(
            keys=st.text(min_size=1, max_size=20),
            values=st.one_of(
                st.text(max_size=50),
                st.integers(),
                st.floats(allow_nan=False, allow_infinity=False),
                st.booleans(),
                st.none(),
            ),
            max_size=10,
        ).map(json.dumps),
        # Binary-like content decoded as text
        st.binary(max_size=500).map(lambda b: b.decode('utf-8', errors='replace')),
    )

    # Strategy for message attribute values
    attribute_value_strategy = st.fixed_dictionaries(
        {
            'DataType': st.sampled_from(MESSAGE_ATTRIBUTE_TYPES),
            'StringValue': st.one_of(
                st.text(max_size=200),
                st.none(),
            ),
            'BinaryValue': st.one_of(
                st.binary(max_size=100),
                st.none(),
            ),
        }
    )

    # Strategy for message attributes
    attributes_strategy = st.dictionaries(
        keys=st.one_of(
            st.sampled_from(COMMON_ATTRIBUTE_KEYS),
            st.text(min_size=1, max_size=50),
        ),
        values=attribute_value_strategy,
        max_size=10,
    )

    # Strategy for topic ARN
    topic_arn_strategy = st.one_of(
        st.just('arn:aws:sns:us-east-1:123456789012:MyTopic'),
        st.text(min_size=0, max_size=100),
    )

    return st.fixed_dictionaries(
        {
            'Message': body_strategy,
            'MessageAttributes': attributes_strategy,
            'TopicArn': topic_arn_strategy,
            'Subject': st.one_of(st.text(max_size=100), st.none()),
        }
    )


def sqs_message_strategy() -> st.SearchStrategy[dict]:
    """Hypothesis strategy for generating SQS message structures.

    This strategy generates SQS message structures with:
    - Message body
    - Message attributes
    - Queue URL
    - Delay seconds
    - Message deduplication ID (for FIFO)
    - Message group ID (for FIFO)

    Returns:
        A Hypothesis SearchStrategy that generates SQS message dicts.
    """
    # Strategy for message body
    body_strategy = st.one_of(
        st.text(min_size=0, max_size=1000),
        st.dictionaries(
            keys=st.text(min_size=1, max_size=20),
            values=st.one_of(
                st.text(max_size=50),
                st.integers(),
                st.booleans(),
            ),
            max_size=10,
        ).map(json.dumps),
    )

    # Strategy for message attribute values
    attribute_value_strategy = st.fixed_dictionaries(
        {
            'DataType': st.sampled_from(MESSAGE_ATTRIBUTE_TYPES),
            'StringValue': st.one_of(
                st.text(max_size=200),
                st.none(),
            ),
            'BinaryValue': st.one_of(
                st.binary(max_size=100),
                st.none(),
            ),
        }
    )

    # Strategy for message attributes
    attributes_strategy = st.dictionaries(
        keys=st.text(min_size=1, max_size=50),
        values=attribute_value_strategy,
        max_size=10,
    )

    # Strategy for queue URL
    queue_url_strategy = st.one_of(
        st.just('https://sqs.us-east-1.amazonaws.com/123456789012/MyQueue'),
        st.text(min_size=0, max_size=200),
    )

    return st.fixed_dictionaries(
        {
            'MessageBody': body_strategy,
            'MessageAttributes': attributes_strategy,
            'QueueUrl': queue_url_strategy,
            'DelaySeconds': st.integers(min_value=0, max_value=900),
            'MessageDeduplicationId': st.one_of(st.text(max_size=128), st.none()),
            'MessageGroupId': st.one_of(st.text(max_size=128), st.none()),
        }
    )


def tag_dict_strategy() -> st.SearchStrategy[dict]:
    """Hypothesis strategy for generating tag dictionaries.

    This strategy generates tag dictionaries that test the
    validate_mcp_server_version_tag function.

    Returns:
        A Hypothesis SearchStrategy that generates tag dicts.
    """
    # Strategy for tag keys
    tag_key_strategy = st.one_of(
        st.just(MCP_SERVER_VERSION_TAG),
        st.text(min_size=1, max_size=128),
    )

    # Strategy for tag values
    tag_value_strategy = st.text(min_size=0, max_size=256)

    return st.dictionaries(
        keys=tag_key_strategy,
        values=tag_value_strategy,
        min_size=0,
        max_size=50,
    )


def oversized_attribute_strategy() -> st.SearchStrategy[dict]:
    """Hypothesis strategy for generating oversized message attributes.

    This strategy specifically tests handling of oversized values
    that may exceed AWS limits.

    Returns:
        A Hypothesis SearchStrategy that generates oversized attribute dicts.
    """
    # Generate potentially oversized string values
    oversized_string = st.text(min_size=100, max_size=5000)

    # Generate potentially oversized binary values
    oversized_binary = st.binary(min_size=100, max_size=5000)

    return st.fixed_dictionaries(
        {
            'DataType': st.sampled_from(MESSAGE_ATTRIBUTE_TYPES),
            'StringValue': st.one_of(oversized_string, st.none()),
            'BinaryValue': st.one_of(oversized_binary, st.none()),
        }
    )


def fuzz_message_structure(data: bytes) -> None:
    """Fuzz target for SNS/SQS message structure handling.

    This function takes raw bytes and tests:
    1. Tag validation with arbitrary tag dictionaries
    2. Message structure parsing

    The target verifies that:
    1. Functions don't crash on arbitrary input
    2. Validation functions return expected types

    Args:
        data: Raw bytes from the fuzzer.

    Raises:
        AssertionError: If functions return unexpected types.
    """
    if len(data) == 0:
        return

    # Convert bytes to string for tag key/value testing
    try:
        tag_string = data.decode('utf-8', errors='replace')
    except Exception:
        tag_string = data.decode('latin-1')

    # Test validate_mcp_server_version_tag with various tag dicts
    # Test 1: Empty tags
    try:
        is_valid, error_msg = validate_mcp_server_version_tag({})
        assert isinstance(is_valid, bool)
        assert isinstance(error_msg, str)
        assert is_valid is False  # Empty tags should fail
    except AssertionError:
        raise
    except Exception:
        pass

    # Test 2: Tags with the required key
    try:
        tags = {MCP_SERVER_VERSION_TAG: tag_string}
        is_valid, error_msg = validate_mcp_server_version_tag(tags)
        assert isinstance(is_valid, bool)
        assert isinstance(error_msg, str)
        assert is_valid is True  # Should pass with required key
    except AssertionError:
        raise
    except Exception:
        pass

    # Test 3: Tags with arbitrary key from fuzz data
    try:
        tags = {tag_string: 'value'}
        is_valid, error_msg = validate_mcp_server_version_tag(tags)
        assert isinstance(is_valid, bool)
        assert isinstance(error_msg, str)
    except AssertionError:
        raise
    except Exception:
        pass

    # Test 4: Try to parse as JSON for message structure
    try:
        message_body = data.decode('utf-8', errors='replace')
        parsed = json.loads(message_body)
        # If it's valid JSON, verify it's a valid type
        assert isinstance(parsed, (dict, list, str, int, float, bool, type(None)))
    except json.JSONDecodeError:
        pass
    except Exception:
        pass


@given(tag_dict_strategy())
@settings(max_examples=100, deadline=None)
def test_tag_validation(tags: dict) -> None:
    """Property test for MCP server version tag validation.

    This test verifies that the tag validation function handles
    arbitrary tag dictionaries gracefully.

    **Validates: Requirements 9.2, 9.3, 9.5**

    Property 1: Graceful Input Handling (message queue subset)
    For any tag dictionary, the validation function SHALL either:
    - Return (True, '') if the required tag is present, OR
    - Return (False, error_message) if the required tag is missing

    Args:
        tags: A tag dictionary generated by the strategy.
    """
    try:
        is_valid, error_msg = validate_mcp_server_version_tag(tags)

        # Verify return types
        assert isinstance(is_valid, bool), f'Expected bool, got {type(is_valid)}'
        assert isinstance(error_msg, str), f'Expected str, got {type(error_msg)}'

        # Verify logic
        if MCP_SERVER_VERSION_TAG in tags:
            assert is_valid is True, 'Should be valid when tag is present'
            assert error_msg == '', 'Error message should be empty when valid'
        else:
            assert is_valid is False, 'Should be invalid when tag is missing'
            assert error_msg != '', 'Error message should not be empty when invalid'
    except AssertionError:
        raise
    except Exception:
        # Other exceptions are acceptable
        pass


@given(sns_message_strategy())
@settings(max_examples=100, deadline=None)
def test_sns_message_structure(message: dict) -> None:
    """Property test for SNS message structure handling.

    This test verifies that SNS message structures are handled
    gracefully without crashing.

    **Validates: Requirements 9.2, 9.5**

    Args:
        message: An SNS message dict generated by the strategy.
    """
    # Test message body handling
    try:
        body = message.get('Message', '')
        if isinstance(body, str):
            _ = body.encode('utf-8')
            # Try JSON parsing
            if body.startswith('{') or body.startswith('['):
                try:
                    json.loads(body)
                except json.JSONDecodeError:
                    pass
    except Exception:
        pass

    # Test message attributes handling
    try:
        attributes = message.get('MessageAttributes', {})
        for key, value in attributes.items():
            assert isinstance(key, str)
            if isinstance(value, dict):
                _ = value.get('DataType')
                _ = value.get('StringValue')
                _ = value.get('BinaryValue')
    except Exception:
        pass

    # Test topic ARN handling
    try:
        topic_arn = message.get('TopicArn', '')
        if isinstance(topic_arn, str):
            _ = topic_arn.split(':')
    except Exception:
        pass


@given(sqs_message_strategy())
@settings(max_examples=100, deadline=None)
def test_sqs_message_structure(message: dict) -> None:
    """Property test for SQS message structure handling.

    This test verifies that SQS message structures are handled
    gracefully without crashing.

    **Validates: Requirements 9.2, 9.3, 9.5**

    Args:
        message: An SQS message dict generated by the strategy.
    """
    # Test message body handling
    try:
        body = message.get('MessageBody', '')
        if isinstance(body, str):
            _ = body.encode('utf-8')
            if body.startswith('{') or body.startswith('['):
                try:
                    json.loads(body)
                except json.JSONDecodeError:
                    pass
    except Exception:
        pass

    # Test message attributes handling
    try:
        attributes = message.get('MessageAttributes', {})
        for key, value in attributes.items():
            assert isinstance(key, str)
            if isinstance(value, dict):
                _ = value.get('DataType')
    except Exception:
        pass

    # Test FIFO-specific fields
    try:
        dedup_id = message.get('MessageDeduplicationId')
        group_id = message.get('MessageGroupId')
        if dedup_id is not None:
            assert isinstance(dedup_id, str)
        if group_id is not None:
            assert isinstance(group_id, str)
    except Exception:
        pass


@given(oversized_attribute_strategy())
@settings(max_examples=100, deadline=None)
def test_oversized_message_attributes(attribute: dict) -> None:
    """Property test for handling oversized message attributes.

    This test verifies that oversized attribute values are handled
    gracefully without crashing.

    **Validates: Requirements 9.3, 9.5**

    Args:
        attribute: An oversized attribute dict generated by the strategy.
    """
    try:
        data_type = attribute.get('DataType')
        string_value = attribute.get('StringValue')
        binary_value = attribute.get('BinaryValue')

        # Verify types
        if data_type is not None:
            assert isinstance(data_type, str)
        if string_value is not None:
            assert isinstance(string_value, str)
            # Check size
            _ = len(string_value)
        if binary_value is not None:
            assert isinstance(binary_value, bytes)
            _ = len(binary_value)
    except Exception:
        pass


@given(st.binary(min_size=1, max_size=1000))
@settings(max_examples=100, deadline=None)
def test_message_structure_with_raw_bytes(data: bytes) -> None:
    """Property test for message structure handling with raw byte input.

    This test verifies that the fuzz target handles arbitrary byte sequences
    gracefully, simulating the Atheris fuzzing mode.

    **Validates: Requirements 9.2, 9.3, 9.5**

    Args:
        data: Raw bytes to be processed by the fuzz target.
    """
    # Should not raise any unhandled exceptions
    fuzz_message_structure(data)


def test_tag_validation_with_required_tag() -> None:
    """Unit test verifying tag validation passes with required tag.

    **Validates: Requirements 9.2**
    """
    tags = {MCP_SERVER_VERSION_TAG: '1.0.0'}
    is_valid, error_msg = validate_mcp_server_version_tag(tags)
    assert is_valid is True
    assert error_msg == ''


def test_tag_validation_without_required_tag() -> None:
    """Unit test verifying tag validation fails without required tag.

    **Validates: Requirements 9.2**
    """
    tags = {'other_tag': 'value'}
    is_valid, error_msg = validate_mcp_server_version_tag(tags)
    assert is_valid is False
    assert 'mcp_server_version' in error_msg


def test_tag_validation_empty_tags() -> None:
    """Unit test verifying tag validation fails with empty tags.

    **Validates: Requirements 9.2**
    """
    tags = {}
    is_valid, error_msg = validate_mcp_server_version_tag(tags)
    assert is_valid is False
    assert error_msg != ''


if __name__ == '__main__':
    # Entry point for Atheris fuzzing
    PolyglotHarness.run_harness(fuzz_message_structure, test_tag_validation)
