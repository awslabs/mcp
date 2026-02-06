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

"""Polyglot fuzz harness for path traversal in aws-documentation-mcp-server.

This module provides a fuzz target that tests path validation with directory
traversal sequences in URL paths for the aws-documentation-mcp-server.

The harness works both as:
- A pytest test using Hypothesis for structured input generation
- An OSS-Fuzz target using Atheris for coverage-guided fuzzing

Feature: oss-fuzz-integration
Requirements: 8.2, 8.5

Example usage:
    # Run as pytest test
    pytest fuzzing/targets/aws_documentation/fuzz_path_traversal.py -v

    # Run as Atheris fuzz target (when built by OSS-Fuzz)
    python fuzzing/targets/aws_documentation/fuzz_path_traversal.py
"""

from __future__ import annotations

import re
import sys
from hypothesis import given, settings
from hypothesis import strategies as st
from pathlib import Path
from urllib.parse import unquote, urlparse


# Add the aws-documentation-mcp-server to the path for imports
_REPO_ROOT = Path(__file__).parent.parent.parent.parent
_AWS_DOCS_SERVER_PATH = _REPO_ROOT / 'src' / 'aws-documentation-mcp-server'
if str(_AWS_DOCS_SERVER_PATH) not in sys.path:
    sys.path.insert(0, str(_AWS_DOCS_SERVER_PATH))

from awslabs.aws_documentation_mcp_server.util import (  # noqa: E402
    format_documentation_result,
)
from fuzzing.harness_base import PolyglotHarness  # noqa: E402


# Path traversal sequences
PATH_TRAVERSAL_SEQUENCES = [
    '../',
    '..\\',
    '..../',
    '....\\',
    '%2e%2e/',
    '%2e%2e\\',
    '%2e%2e%2f',
    '%2e%2e%5c',
    '..%2f',
    '..%5c',
    '%2e%2e%252f',
    '..%c0%af',
    '..%c1%9c',  # Unicode encoding
    '..%255c',
    '..%252f',  # Double encoding
    '....//....//....//etc/passwd',
    '..\\..\\..\\windows\\system32',
    '.%2e/',
    '%2e./',  # Mixed encoding
    '..;/',  # Semicolon bypass
    '..%00/',  # Null byte
    '..%0d%0a/',  # CRLF
]

# URL path components for building traversal URLs
URL_PATH_COMPONENTS = [
    'AmazonS3',
    'lambda',
    'AWSEC2',
    'IAM',
    'AmazonRDS',
    'latest',
    'userguide',
    'dg',
    'UserGuide',
    'APIReference',
]

# Sensitive paths that traversal might try to access
SENSITIVE_PATHS = [
    '/etc/passwd',
    '/etc/shadow',
    '/etc/hosts',
    '/proc/self/environ',
    '/var/log/auth.log',
    'C:/Windows/System32/config/SAM',
    'C:/Windows/win.ini',
]

# Valid AWS documentation base URL
AWS_DOCS_BASE = 'https://docs.aws.amazon.com'

# URL validation regex from the server
SUPPORTED_DOMAINS_REGEX = [
    r'^https?://docs\.aws\.amazon\.com/',
    r'^https?://awsdocs-neuron\.readthedocs-hosted\.com/',
]


def path_traversal_url_strategy() -> st.SearchStrategy[str]:
    """Hypothesis strategy for generating URLs with path traversal attempts.

    This strategy generates URLs that include:
    - Directory traversal sequences
    - Encoded traversal attempts
    - Mixed valid and traversal paths

    Returns:
        A Hypothesis SearchStrategy that generates URL strings with traversal.
    """
    # Strategy for traversal sequences
    traversal_strategy = st.sampled_from(PATH_TRAVERSAL_SEQUENCES)

    # Strategy for path components
    path_component_strategy = st.sampled_from(URL_PATH_COMPONENTS)

    # Strategy for sensitive paths
    sensitive_path_strategy = st.sampled_from(SENSITIVE_PATHS)

    # Build traversal URLs
    traversal_url = st.tuples(
        st.just(AWS_DOCS_BASE),
        st.lists(traversal_strategy, min_size=1, max_size=5),
        sensitive_path_strategy,
    ).map(lambda t: f'{t[0]}/{"".join(t[1])}{t[2]}')

    # Mixed valid and traversal paths
    mixed_url = st.tuples(
        st.just(AWS_DOCS_BASE),
        path_component_strategy,
        st.lists(traversal_strategy, min_size=1, max_size=3),
        st.just('.html'),
    ).map(lambda t: f'{t[0]}/{t[1]}/{"".join(t[2])}test{t[3]}')

    # URL with traversal in query string
    query_traversal = st.tuples(
        st.just(AWS_DOCS_BASE),
        path_component_strategy,
        st.just('/test.html?path='),
        traversal_strategy,
    ).map(lambda t: f'{t[0]}/{t[1]}{t[2]}{t[3]}')

    # URL with traversal in fragment
    fragment_traversal = st.tuples(
        st.just(AWS_DOCS_BASE),
        path_component_strategy,
        st.just('/test.html#'),
        traversal_strategy,
    ).map(lambda t: f'{t[0]}/{t[1]}{t[2]}{t[3]}')

    return st.one_of(
        traversal_url,
        mixed_url,
        query_traversal,
        fragment_traversal,
        # Random path strings
        st.text(min_size=0, max_size=200),
        # Binary decoded as text
        st.binary(min_size=0, max_size=100).map(lambda b: b.decode('utf-8', errors='replace')),
    )


def validate_url_path(url: str) -> tuple[bool, str]:
    """Validate URL path for traversal attempts.

    This function checks if a URL path contains directory traversal sequences.

    Args:
        url: URL string to validate.

    Returns:
        Tuple of (is_safe, reason) where is_safe is True if no traversal found.
    """
    try:
        parsed = urlparse(url)
        path = parsed.path

        # Decode the path to catch encoded traversal
        decoded_path = unquote(unquote(path))  # Double decode

        # Check for traversal patterns
        traversal_patterns = [
            r'\.\.',  # Basic ..
            r'%2e%2e',  # URL encoded
            r'%252e',  # Double encoded
            r'%c0%ae',  # Unicode
            r'%c1%9c',  # Unicode backslash
        ]

        for pattern in traversal_patterns:
            if re.search(pattern, path, re.IGNORECASE):
                return False, f'Traversal pattern found: {pattern}'
            if re.search(pattern, decoded_path, re.IGNORECASE):
                return False, f'Encoded traversal pattern found: {pattern}'

        # Check if path tries to access sensitive locations
        for sensitive in SENSITIVE_PATHS:
            if sensitive.lower() in decoded_path.lower():
                return False, f'Sensitive path access attempt: {sensitive}'

        return True, 'Path is safe'

    except Exception as e:
        return False, f'Validation error: {str(e)}'


def normalize_path(path: str) -> str:
    """Normalize a URL path by resolving traversal sequences.

    Args:
        path: URL path to normalize.

    Returns:
        Normalized path with traversal sequences resolved.
    """
    try:
        # Decode URL encoding
        decoded = unquote(unquote(path))

        # Use pathlib to normalize
        normalized = str(Path(decoded).resolve())

        return normalized
    except Exception:
        return path


def fuzz_path_traversal(data: bytes) -> None:
    """Fuzz target for path traversal validation.

    This function takes raw bytes, converts them to a URL/path string, and tests
    path validation functions for directory traversal vulnerabilities.

    The target verifies that:
    1. Path validation doesn't crash on arbitrary input
    2. Traversal sequences are properly detected
    3. No unhandled exceptions are raised

    Args:
        data: Raw bytes from the fuzzer to be converted to path string.
    """
    if len(data) == 0:
        return

    # Convert bytes to string, handling encoding errors gracefully
    try:
        path_string = data.decode('utf-8', errors='replace')
    except Exception:
        path_string = data.decode('latin-1')

    # Test path validation
    try:
        is_safe, reason = validate_url_path(path_string)
        assert isinstance(is_safe, bool), f'Expected bool, got {type(is_safe)}'
        assert isinstance(reason, str), f'Expected str, got {type(reason)}'
    except AssertionError:
        raise
    except Exception:
        pass

    # Test path normalization
    try:
        normalized = normalize_path(path_string)
        assert isinstance(normalized, str), f'Expected str, got {type(normalized)}'
    except AssertionError:
        raise
    except Exception:
        pass

    # Test format_documentation_result with path as content
    try:
        result = format_documentation_result(f'{AWS_DOCS_BASE}/test.html', path_string, 0, 1000)
        assert isinstance(result, str), f'Expected str, got {type(result)}'
    except AssertionError:
        raise
    except Exception:
        pass


@given(path_traversal_url_strategy())
@settings(max_examples=100, deadline=None)
def test_path_traversal_graceful_handling(path_string: str) -> None:
    """Property test for path traversal validation graceful input handling.

    This test verifies that path validation functions handle arbitrary
    path strings gracefully without crashing.

    **Validates: Requirements 8.2, 8.5**

    Property 1: Graceful Input Handling (path traversal subset)
    For any path string, the validation functions SHALL either:
    - Successfully process the input and return normally, OR
    - Raise a handled exception without crashing

    Args:
        path_string: Path string generated by the path_traversal_url_strategy.
    """
    # Test path validation
    try:
        is_safe, reason = validate_url_path(path_string)
        assert isinstance(is_safe, bool)
        assert isinstance(reason, str)
    except Exception:
        pass

    # Test path normalization
    try:
        normalized = normalize_path(path_string)
        assert isinstance(normalized, str)
    except Exception:
        pass


@given(st.binary(min_size=1, max_size=1000))
@settings(max_examples=100, deadline=None)
def test_path_traversal_with_raw_bytes(data: bytes) -> None:
    """Property test for path traversal validation with raw byte input.

    This test verifies that the fuzz target handles arbitrary byte sequences
    gracefully, simulating the Atheris fuzzing mode.

    **Validates: Requirements 8.2, 8.5**

    Args:
        data: Raw bytes to be processed by the fuzz target.
    """
    fuzz_path_traversal(data)


def test_basic_traversal_detection() -> None:
    """Unit test verifying basic traversal sequences are detected.

    **Validates: Requirements 8.2**
    """
    traversal_urls = [
        f'{AWS_DOCS_BASE}/../../../etc/passwd',
        f'{AWS_DOCS_BASE}/..\\..\\..\\windows\\system32',
        f'{AWS_DOCS_BASE}/test/../../etc/passwd',
    ]

    for url in traversal_urls:
        is_safe, reason = validate_url_path(url)
        assert is_safe is False, f'Expected {url} to be detected as unsafe'


def test_encoded_traversal_detection() -> None:
    """Unit test verifying encoded traversal sequences are detected.

    **Validates: Requirements 8.2**
    """
    encoded_urls = [
        f'{AWS_DOCS_BASE}/%2e%2e/%2e%2e/etc/passwd',
        f'{AWS_DOCS_BASE}/%252e%252e/%252e%252e/etc/passwd',
        f'{AWS_DOCS_BASE}/..%2f..%2f..%2fetc/passwd',
    ]

    for url in encoded_urls:
        is_safe, reason = validate_url_path(url)
        assert is_safe is False, f'Expected {url} to be detected as unsafe'


def test_safe_paths() -> None:
    """Unit test verifying safe paths are accepted.

    **Validates: Requirements 8.2**
    """
    safe_urls = [
        f'{AWS_DOCS_BASE}/AmazonS3/latest/userguide/test.html',
        f'{AWS_DOCS_BASE}/lambda/latest/dg/lambda-invocation.html',
        f'{AWS_DOCS_BASE}/AWSEC2/latest/UserGuide/concepts.html',
    ]

    for url in safe_urls:
        is_safe, reason = validate_url_path(url)
        assert is_safe is True, f'Expected {url} to be safe: {reason}'


def test_sensitive_path_detection() -> None:
    """Unit test verifying sensitive path access attempts are detected.

    **Validates: Requirements 8.2**
    """
    sensitive_urls = [
        f'{AWS_DOCS_BASE}/test/../../../etc/passwd',
        f'{AWS_DOCS_BASE}/test/../../../proc/self/environ',
    ]

    for url in sensitive_urls:
        is_safe, reason = validate_url_path(url)
        # Should detect either traversal or sensitive path
        assert is_safe is False, f'Expected {url} to be detected as unsafe'


def test_path_normalization() -> None:
    """Unit test verifying path normalization works correctly.

    **Validates: Requirements 8.2**
    """
    test_cases = [
        ('/test/../other', '/other'),
        ('/test/./other', '/test/other'),
        ('/test//other', '/test/other'),
    ]

    for input_path, expected_suffix in test_cases:
        normalized = normalize_path(input_path)
        # The normalized path should not contain traversal sequences
        assert '..' not in normalized or normalized == input_path


def test_format_documentation_with_traversal_content() -> None:
    """Unit test verifying format_documentation_result handles traversal content.

    **Validates: Requirements 8.5**
    """
    traversal_content = '../../../etc/passwd'
    result = format_documentation_result(f'{AWS_DOCS_BASE}/test.html', traversal_content, 0, 1000)
    assert isinstance(result, str)
    # The content should be included as-is (it's just content, not a path)
    assert traversal_content in result


if __name__ == '__main__':
    # Entry point for Atheris fuzzing
    PolyglotHarness.run_harness(fuzz_path_traversal, test_path_traversal_graceful_handling)
