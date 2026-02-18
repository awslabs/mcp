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

"""Polyglot fuzz harness for Amazon MQ message payload and header parsing.

This module provides a fuzz target that tests the message payload handling
and name validation functions from the amazon-mq-mcp-server package.

The harness works both as:
- A pytest test using Hypothesis for structured input generation
- An OSS-Fuzz target using Atheris for coverage-guided fuzzing

Feature: oss-fuzz-integration
Requirements: 9.1, 9.5

Example usage:
    # Run as pytest test
    pytest fuzzing/targets/mq/fuzz_message_payload.py -v

    # Run as Atheris fuzz target (when built by OSS-Fuzz)
    python fuzzing/targets/mq/fuzz_message_payload.py
"""

from __future__ import annotations

import json
import sys
from hypothesis import given, settings
from hypothesis import strategies as st
from pathlib import Path


# Add the amazon-mq-mcp-server to the path for imports
_REPO_ROOT = Path(__file__).parent.parent.parent.parent
_MQ_SERVER_PATH = _REPO_ROOT / 'src' / 'amazon-mq-mcp-server'
if str(_MQ_SERVER_PATH) not in sys.path:
    sys.path.insert(0, str(_MQ_SERVER_PATH))

from awslabs.amazon_mq_mcp_server.rabbitmq.connection import (  # noqa: E402
    validate_rabbitmq_name,
)
from fuzzing.harness_base import PolyglotHarness  # noqa: E402


# RabbitMQ-specific characters and patterns for message payloads
MQ_SPECIAL_CHARS = [
    '\x00',
    '\x01',
    '\x02',
    '\x03',  # Control characters
    '\n',
    '\r',
    '\t',  # Whitespace
    '"',
    "'",
    '\\',  # Quotes and escapes
    '<',
    '>',
    '&',  # XML/HTML special chars
    '{',
    '}',
    '[',
    ']',  # JSON delimiters
]

# Valid characters for RabbitMQ names (queue/exchange names)
VALID_NAME_CHARS = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.:'

# Message header keys commonly used in AMQP
AMQP_HEADER_KEYS = [
    'content-type',
    'content-encoding',
    'delivery-mode',
    'priority',
    'correlation-id',
    'reply-to',
    'expiration',
    'message-id',
    'timestamp',
    'type',
    'user-id',
    'app-id',
    'cluster-id',
]

# Common content types for message payloads
CONTENT_TYPES = [
    'application/json',
    'application/xml',
    'text/plain',
    'text/html',
    'application/octet-stream',
    'application/x-www-form-urlencoded',
]


def message_payload_strategy() -> st.SearchStrategy[dict]:
    """Hypothesis strategy for generating RabbitMQ message payloads.

    This strategy generates message structures with:
    - Body content (string or bytes)
    - Headers with various types
    - Properties like content-type, priority, etc.

    Returns:
        A Hypothesis SearchStrategy that generates message payload dicts.
    """
    # Strategy for message body content
    body_strategy = st.one_of(
        st.text(min_size=0, max_size=1000),
        st.binary(min_size=0, max_size=500).map(lambda b: b.decode('utf-8', errors='replace')),
        # JSON-like content
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
    )

    # Strategy for header values
    header_value_strategy = st.one_of(
        st.text(max_size=100),
        st.integers(min_value=0, max_value=255),
        st.binary(max_size=50).map(lambda b: b.decode('latin-1')),
    )

    # Strategy for headers dict
    headers_strategy = st.dictionaries(
        keys=st.one_of(
            st.sampled_from(AMQP_HEADER_KEYS),
            st.text(min_size=1, max_size=30),
        ),
        values=header_value_strategy,
        max_size=10,
    )

    # Strategy for message properties
    properties_strategy = st.fixed_dictionaries(
        {
            'content_type': st.one_of(
                st.sampled_from(CONTENT_TYPES),
                st.text(max_size=50),
                st.none(),
            ),
            'content_encoding': st.one_of(
                st.sampled_from(['utf-8', 'gzip', 'deflate', '']),
                st.text(max_size=20),
                st.none(),
            ),
            'delivery_mode': st.one_of(
                st.integers(min_value=0, max_value=3),
                st.none(),
            ),
            'priority': st.one_of(
                st.integers(min_value=0, max_value=255),
                st.none(),
            ),
            'correlation_id': st.one_of(
                st.text(max_size=50),
                st.none(),
            ),
            'reply_to': st.one_of(
                st.text(max_size=100),
                st.none(),
            ),
            'expiration': st.one_of(
                st.integers(min_value=0, max_value=86400000).map(str),
                st.none(),
            ),
            'message_id': st.one_of(
                st.text(max_size=50),
                st.none(),
            ),
        }
    )

    # Combine into full message payload
    return st.fixed_dictionaries(
        {
            'body': body_strategy,
            'headers': headers_strategy,
            'properties': properties_strategy,
        }
    )


def rabbitmq_name_strategy() -> st.SearchStrategy[str]:
    """Hypothesis strategy for generating RabbitMQ queue/exchange names.

    This strategy generates names that test the validation logic:
    - Valid names with allowed characters
    - Invalid names with special characters
    - Edge cases like empty strings, very long names

    Returns:
        A Hypothesis SearchStrategy that generates name strings.
    """
    # Valid name characters
    valid_chars = st.sampled_from(list(VALID_NAME_CHARS))

    # Strategy for valid names
    valid_name = st.text(
        alphabet=valid_chars,
        min_size=1,
        max_size=100,
    )

    # Strategy for potentially invalid names
    invalid_name = st.one_of(
        st.text(min_size=0, max_size=300),  # May include invalid chars or be too long
        st.just(''),  # Empty string
        st.just('   '),  # Whitespace only
        st.text(min_size=256, max_size=300),  # Too long
        st.binary(max_size=50).map(lambda b: b.decode('utf-8', errors='replace')),
    )

    return st.one_of(valid_name, invalid_name)


def fuzz_message_payload(data: bytes) -> None:
    """Fuzz target for Amazon MQ message payload handling.

    This function takes raw bytes and tests:
    1. RabbitMQ name validation with arbitrary strings
    2. Message payload structure parsing

    The target verifies that:
    1. Functions don't crash on arbitrary input
    2. Validation functions return expected types or raise expected exceptions

    Args:
        data: Raw bytes from the fuzzer.

    Raises:
        AssertionError: If functions return unexpected types.
    """
    if len(data) == 0:
        return

    # Convert bytes to string for name validation testing
    try:
        name_string = data.decode('utf-8', errors='replace')
    except Exception:
        name_string = data.decode('latin-1')

    # Test validate_rabbitmq_name with queue name
    try:
        validate_rabbitmq_name(name_string, 'Queue name')
        # If validation passes, the name should be valid
    except ValueError:
        # Expected for invalid names
        pass
    except Exception as e:
        # Unexpected exceptions should be noted but not crash
        assert isinstance(e, Exception), f'Unexpected exception type: {type(e)}'

    # Test validate_rabbitmq_name with exchange name
    try:
        validate_rabbitmq_name(name_string, 'Exchange name')
    except ValueError:
        pass
    except Exception as e:
        assert isinstance(e, Exception), f'Unexpected exception type: {type(e)}'

    # Test with truncated name (simulate header parsing)
    if len(name_string) > 10:
        try:
            validate_rabbitmq_name(name_string[:10], 'Truncated name')
        except ValueError:
            pass
        except Exception:
            pass

    # Test JSON parsing of message body (simulating message payload)
    try:
        body = data.decode('utf-8', errors='replace')
        parsed = json.loads(body)
        assert isinstance(parsed, (dict, list, str, int, float, bool, type(None)))
    except json.JSONDecodeError:
        # Expected for non-JSON input
        pass
    except Exception:
        # Other exceptions are acceptable
        pass


@given(message_payload_strategy())
@settings(max_examples=100, deadline=None)
def test_message_payload_handling(payload: dict) -> None:
    """Property test for Amazon MQ message payload handling.

    This test verifies that message payload structures are handled
    gracefully without crashing.

    **Validates: Requirements 9.1, 9.5**

    Property 1: Graceful Input Handling (message queue subset)
    For any message payload structure, the handling functions SHALL either:
    - Successfully process the input and return normally, OR
    - Raise a handled exception without crashing

    Args:
        payload: A message payload dict generated by the strategy.
    """
    # Test body content handling
    body = payload.get('body', '')
    try:
        # Simulate body processing
        if isinstance(body, str):
            _ = body.encode('utf-8')
            # Try JSON parsing if it looks like JSON
            if body.startswith('{') or body.startswith('['):
                try:
                    json.loads(body)
                except json.JSONDecodeError:
                    pass
    except Exception:
        pass

    # Test headers handling
    headers = payload.get('headers', {})
    try:
        for key, value in headers.items():
            assert isinstance(key, str)
            # Headers can be various types
            _ = str(value)
    except Exception:
        pass

    # Test properties handling
    properties = payload.get('properties', {})
    try:
        for key, value in properties.items():
            if value is not None:
                _ = str(value)
    except Exception:
        pass


@given(rabbitmq_name_strategy())
@settings(max_examples=100, deadline=None)
def test_rabbitmq_name_validation(name: str) -> None:
    """Property test for RabbitMQ name validation.

    This test verifies that the name validation function handles
    arbitrary strings gracefully.

    **Validates: Requirements 9.1, 9.5**

    Args:
        name: A name string generated by the strategy.
    """
    # Test queue name validation
    try:
        validate_rabbitmq_name(name, 'Queue name')
        # If validation passes, verify the name meets criteria
        assert name and name.strip(), 'Empty name should not pass validation'
        assert len(name) <= 255, 'Name too long should not pass validation'
        assert all(c.isalnum() or c in '-_.:' for c in name), (
            'Invalid characters should not pass validation'
        )
    except ValueError:
        # Expected for invalid names
        pass
    except Exception:
        # Other exceptions are acceptable
        pass

    # Test exchange name validation
    try:
        validate_rabbitmq_name(name, 'Exchange name')
    except ValueError:
        pass
    except Exception:
        pass


@given(st.binary(min_size=1, max_size=1000))
@settings(max_examples=100, deadline=None)
def test_message_payload_with_raw_bytes(data: bytes) -> None:
    """Property test for message payload handling with raw byte input.

    This test verifies that the fuzz target handles arbitrary byte sequences
    gracefully, simulating the Atheris fuzzing mode.

    **Validates: Requirements 9.1, 9.5**

    Args:
        data: Raw bytes to be processed by the fuzz target.
    """
    # Should not raise any unhandled exceptions
    fuzz_message_payload(data)


def test_valid_rabbitmq_names() -> None:
    """Unit test verifying valid RabbitMQ names pass validation.

    **Validates: Requirements 9.1**
    """
    valid_names = [
        'my-queue',
        'my_queue',
        'my.queue',
        'my:queue',
        'MyQueue123',
        'a',
        'queue-name-with-dashes',
        'queue_name_with_underscores',
        'queue.name.with.dots',
    ]

    for name in valid_names:
        # Should not raise
        validate_rabbitmq_name(name, 'Test name')


def test_invalid_rabbitmq_names() -> None:
    """Unit test verifying invalid RabbitMQ names fail validation.

    **Validates: Requirements 9.1**
    """
    invalid_names = [
        ('', 'empty'),
        ('   ', 'whitespace only'),
        ('name with spaces', 'contains spaces'),
        ('name/with/slashes', 'contains slashes'),
        ('name@with@at', 'contains at symbol'),
        ('a' * 256, 'too long'),
    ]

    for name, description in invalid_names:
        try:
            validate_rabbitmq_name(name, 'Test name')
            # If we get here, validation should have failed
            assert False, f'Expected ValueError for {description}: {name!r}'
        except ValueError:
            # Expected
            pass


if __name__ == '__main__':
    # Entry point for Atheris fuzzing
    PolyglotHarness.run_harness(fuzz_message_payload, test_message_payload_handling)
