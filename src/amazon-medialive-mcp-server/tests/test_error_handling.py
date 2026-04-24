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

"""Property-based tests for error handling.

Tests Properties 22 and 23 from the design document.
"""

import hypothesis.strategies as st
import os
import re
import sys
from hypothesis import given, settings


sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from awslabs.amazon_medialive_mcp_server.errors import (
    handle_client_error,
    handle_general_error,
)
from botocore.exceptions import ClientError


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

error_code_strategy = st.text(
    alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')),
    min_size=1,
    max_size=50,
)

error_message_strategy = st.text(
    min_size=1,
    max_size=200,
    alphabet=st.characters(whitelist_categories=('L', 'N', 'P', 'Z')),
)

# The generic error message returned by handle_general_error — used to filter
# out generated strings that would trivially appear as substrings of it.
_GENERIC_ERROR_MSG = 'An unexpected error occurred. Check server logs for details.'

# Strategy for exception messages that may contain internal details.
# We filter out strings that are substrings of the generic error message,
# since the property under test is that the *original* exception message
# is not leaked — not that every possible short string is absent.
internal_detail_strategy = st.one_of(
    st.text(
        min_size=1, max_size=100, alphabet=st.characters(whitelist_categories=('L', 'N', 'P', 'Z'))
    ),
    st.from_regex(r'/[a-z]+/[a-z]+/[a-z]+\.[a-z]+', fullmatch=True),
    st.from_regex(r'File \"[a-z_]+\.py\", line [0-9]+', fullmatch=True),
    st.from_regex(r'[A-Z][a-z]+Error: [a-z ]+', fullmatch=True),
    st.from_regex(r'Traceback \(most recent call last\)', fullmatch=True),
    st.from_regex(r'class [A-Z][a-zA-Z]+\.[a-z_]+', fullmatch=True),
).filter(lambda s: s not in _GENERIC_ERROR_MSG)


# ---------------------------------------------------------------------------
# Property 22: ClientError responses contain error code and message
# ---------------------------------------------------------------------------


# Feature: medialive-mcp-server, Property 22: ClientError responses contain error code and message
# **Validates: Requirements 15.7, 20.1**
@given(code=error_code_strategy, message=error_message_strategy)
@settings(max_examples=100)
def test_client_error_responses_contain_code_and_message(code, message):
    """For any boto3 ClientError raised during tool execution, the structured.

    error response returned to the caller shall contain both the error code
    and the error message extracted from the exception.
    """
    error = ClientError(
        {'Error': {'Code': code, 'Message': message}, 'ResponseMetadata': {}},
        'OperationName',
    )

    result = handle_client_error(error)

    assert 'code' in result, f"Response missing 'code' key. Got keys: {list(result.keys())}"
    assert 'message' in result, f"Response missing 'message' key. Got keys: {list(result.keys())}"
    assert result['code'] == code, f'Expected error code {code!r}, got {result["code"]!r}'
    assert result['message'] == message, (
        f'Expected error message {message!r}, got {result["message"]!r}'
    )


# ---------------------------------------------------------------------------
# Property 23: Unexpected errors do not expose internal details
# ---------------------------------------------------------------------------


# Feature: medialive-mcp-server, Property 23: Unexpected errors do not expose internal details
# **Validates: Requirements 15.8, 20.3**
@given(exc_message=internal_detail_strategy)
@settings(max_examples=100)
def test_unexpected_errors_do_not_expose_internal_details(exc_message):
    """For any unexpected exception raised during tool execution, the response.

    returned to the caller shall be a generic error message that does not
    contain stack traces or internal implementation details.
    """
    error = Exception(exc_message)

    result = handle_general_error(error)

    response_str = str(result)

    assert exc_message not in result.get('message', ''), (
        f'Internal exception message {exc_message!r} was exposed in response message'
    )

    assert 'Traceback' not in response_str, "Response contains stack trace indicator 'Traceback'"

    file_path_pattern = re.compile(r'\.py\b.*line \d+')
    assert not file_path_pattern.search(response_str), (
        f'Response contains file path/line number pattern: {response_str}'
    )

    class_pattern = re.compile(r'\bclass [A-Z]')
    assert not class_pattern.search(response_str), (
        f'Response contains class name pattern: {response_str}'
    )
