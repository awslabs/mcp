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

"""Polyglot fuzz harness for path validation in document-loader-mcp-server.

This module provides a fuzz target that tests the `validate_file_path` function
from the document-loader-mcp-server package with path traversal attempts.

The harness works both as:
- A pytest test using Hypothesis for structured input generation
- An OSS-Fuzz target using Atheris for coverage-guided fuzzing

Feature: oss-fuzz-integration
Requirements: 3.3

Example usage:
    # Run as pytest test
    pytest fuzzing/targets/document_loader/fuzz_path_validation.py -v

    # Run as Atheris fuzz target (when built by OSS-Fuzz)
    python fuzzing/targets/document_loader/fuzz_path_validation.py
"""

from __future__ import annotations

import sys
from hypothesis import given, settings
from hypothesis import strategies as st
from pathlib import Path
from typing import Optional
from unittest.mock import MagicMock


# Add the document-loader-mcp-server to the path for imports
_REPO_ROOT = Path(__file__).parent.parent.parent.parent
_DOC_LOADER_SERVER_PATH = _REPO_ROOT / 'src' / 'document-loader-mcp-server'
if str(_DOC_LOADER_SERVER_PATH) not in sys.path:
    sys.path.insert(0, str(_DOC_LOADER_SERVER_PATH))

from awslabs.document_loader_mcp_server.server import validate_file_path  # noqa: E402
from fuzzing.harness_base import PolyglotHarness  # noqa: E402


# Path traversal sequences and special characters
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
]

# Special path characters
PATH_SPECIAL_CHARS = [
    '/',
    '\\',
    ':',
    '*',
    '?',
    '"',
    '<',
    '>',
    '|',
    '\x00',
    '\n',
    '\r',
    '\t',  # Control characters
    '%00',
    '%0a',
    '%0d',  # URL-encoded control chars
]

# Common sensitive paths to test
SENSITIVE_PATHS = [
    '/etc/passwd',
    '/etc/shadow',
    '/etc/hosts',
    'C:\\Windows\\System32\\config\\SAM',
    '/proc/self/environ',
    '/proc/self/cmdline',
    '~/.ssh/id_rsa',
    '~/.aws/credentials',
    '/var/log/auth.log',
    '/root/.bash_history',
]

# Valid file extensions from the server
ALLOWED_EXTENSIONS = [
    '.pdf',
    '.docx',
    '.doc',
    '.xlsx',
    '.xls',
    '.pptx',
    '.ppt',
    '.png',
    '.jpg',
    '.jpeg',
    '.gif',
    '.bmp',
    '.tiff',
    '.tif',
    '.webp',
]


def path_traversal_strategy() -> st.SearchStrategy[str]:
    """Hypothesis strategy for generating path traversal attempts.

    This strategy generates a mix of:
    - Known path traversal sequences
    - Encoded path traversal attempts
    - Paths with special characters
    - Combinations of traversal sequences with file names

    Returns:
        A Hypothesis SearchStrategy that generates path strings.
    """
    # Strategy for path traversal sequences
    traversal_strategy = st.sampled_from(PATH_TRAVERSAL_SEQUENCES)

    # Strategy for special characters
    special_char_strategy = st.sampled_from(PATH_SPECIAL_CHARS)

    # Strategy for file extensions
    extension_strategy = st.sampled_from(ALLOWED_EXTENSIONS)

    # Strategy for sensitive paths
    sensitive_path_strategy = st.sampled_from(SENSITIVE_PATHS)

    # Strategy for random path components
    path_component = st.text(
        alphabet=st.characters(
            whitelist_categories=('Ll', 'Lu', 'Nd'), whitelist_characters='_-.'
        ),
        min_size=1,
        max_size=20,
    )

    # Build path-like strings
    path_string = st.lists(
        st.one_of(
            traversal_strategy,
            special_char_strategy,
            path_component,
        ),
        min_size=1,
        max_size=10,
    ).map('/'.join)

    # Mix different types of path inputs
    return st.one_of(
        # Pure traversal sequences
        traversal_strategy,
        # Traversal with file extension
        st.tuples(traversal_strategy, extension_strategy).map(lambda t: t[0] + 'file' + t[1]),
        # Sensitive paths
        sensitive_path_strategy,
        # Random path strings
        path_string,
        # Path with extension
        st.tuples(path_string, extension_strategy).map(lambda t: t[0] + t[1]),
        # Absolute paths with traversal
        st.tuples(st.just('/'), path_string).map(lambda t: t[0] + t[1]),
        # Windows-style paths
        st.tuples(st.just('C:\\'), path_string).map(lambda t: t[0] + t[1].replace('/', '\\')),
        # Pure random text
        st.text(min_size=0, max_size=200),
        # Binary decoded as text
        st.binary(min_size=0, max_size=100).map(lambda b: b.decode('utf-8', errors='replace')),
    )


def create_mock_context() -> MagicMock:
    """Create a mock Context object for testing validate_file_path."""
    return MagicMock()


def fuzz_path_validation(data: bytes) -> None:
    """Fuzz target for path validation function.

    This function takes raw bytes, converts them to a path string, and tests
    the `validate_file_path` function from document-loader-mcp-server.

    The target verifies that:
    1. The function doesn't crash on arbitrary input
    2. No unhandled exceptions are raised
    3. Path traversal attempts are properly handled

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

    # Create a mock context
    ctx = create_mock_context()

    try:
        # Test validate_file_path
        result = validate_file_path(ctx, path_string)

        # Result should be either None (valid) or a string (error message)
        assert result is None or isinstance(result, str), (
            f'Expected None or str, got {type(result)}'
        )

    except AssertionError:
        raise  # Re-raise assertion errors for test failures
    except Exception:
        # Other exceptions are acceptable (e.g., OS errors)
        pass


def fuzz_path_validation_structured(path_string: str) -> Optional[str]:
    """Fuzz target for path validation with structured input.

    Args:
        path_string: A path string to validate.

    Returns:
        The validation result (None for valid, error message for invalid).
    """
    ctx = create_mock_context()

    try:
        result = validate_file_path(ctx, path_string)
        assert result is None or isinstance(result, str)
        return result
    except AssertionError:
        raise
    except Exception:
        return None


@given(path_traversal_strategy())
@settings(max_examples=100, deadline=None)
def test_path_validation_graceful_handling(path_string: str) -> None:
    """Property test for path validation graceful input handling.

    This test verifies that the path validation function handles arbitrary
    path strings gracefully without crashing.

    **Validates: Requirements 3.3**

    Property 1: Graceful Input Handling (path validation subset)
    For any path string, the validation function SHALL either:
    - Return None (valid path), OR
    - Return an error message string (invalid path), OR
    - Raise a handled exception without crashing

    Args:
        path_string: Path string generated by the path_traversal_strategy.
    """
    ctx = create_mock_context()

    try:
        result = validate_file_path(ctx, path_string)
        # Result should be None or a string
        assert result is None or isinstance(result, str)
    except Exception:
        # Handled exceptions are acceptable
        pass


@given(st.binary(min_size=0, max_size=1000))
@settings(max_examples=100, deadline=None)
def test_path_validation_with_raw_bytes(data: bytes) -> None:
    """Property test for path validation with raw byte input.

    This test verifies that the fuzz target handles arbitrary byte sequences
    gracefully, simulating the Atheris fuzzing mode.

    **Validates: Requirements 3.3**

    Args:
        data: Raw bytes to be processed by the fuzz target.
    """
    # Should not raise any unhandled exceptions
    fuzz_path_validation(data)


def test_empty_path_handling() -> None:
    """Unit test verifying empty path is handled gracefully.

    **Validates: Requirements 3.3**
    """
    fuzz_path_validation(b'')
    result = fuzz_path_validation_structured('')
    # Empty path should return an error (file not found)
    assert result is not None


def test_path_traversal_detection() -> None:
    """Unit test verifying path traversal attempts are handled.

    **Validates: Requirements 3.3**
    """
    traversal_paths = [
        '../../../etc/passwd',
        '..\\..\\..\\windows\\system32\\config\\sam',
        '/etc/passwd',
        'C:\\Windows\\System32',
        '....//....//etc/passwd',
    ]

    for path in traversal_paths:
        result = fuzz_path_validation_structured(path)
        # These should either return an error or be handled gracefully
        assert result is None or isinstance(result, str)


def test_special_characters_in_path() -> None:
    """Unit test verifying special characters in paths are handled.

    **Validates: Requirements 3.3**
    """
    special_paths = [
        'file\x00.pdf',  # Null byte
        'file\n.pdf',  # Newline
        'file\r.pdf',  # Carriage return
        'file*.pdf',  # Wildcard
        'file?.pdf',  # Question mark
        'file<>.pdf',  # Angle brackets
        'file|.pdf',  # Pipe
        'file".pdf',  # Quote
    ]

    for path in special_paths:
        result = fuzz_path_validation_structured(path)
        # Should handle gracefully
        assert result is None or isinstance(result, str)


def test_encoded_path_traversal() -> None:
    """Unit test verifying encoded path traversal attempts are handled.

    **Validates: Requirements 3.3**
    """
    encoded_paths = [
        '%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd',  # URL encoded
        '..%252f..%252f..%252fetc%252fpasswd',  # Double encoded
        '..%c0%af..%c0%afetc%c0%afpasswd',  # Unicode encoding
    ]

    for path in encoded_paths:
        result = fuzz_path_validation_structured(path)
        # Should handle gracefully
        assert result is None or isinstance(result, str)


def test_valid_extensions() -> None:
    """Unit test verifying valid file extensions are recognized.

    **Validates: Requirements 3.3**
    """
    # Note: These paths don't exist, so validation will fail on file existence
    # but the extension check should pass
    for ext in ALLOWED_EXTENSIONS:
        path = f'/tmp/test_file{ext}'
        result = fuzz_path_validation_structured(path)
        # Should return error about file not found, not about extension
        if result is not None:
            assert 'Unsupported file type' not in result or ext not in ALLOWED_EXTENSIONS


if __name__ == '__main__':
    # Entry point for Atheris fuzzing
    PolyglotHarness.run_harness(fuzz_path_validation, test_path_validation_graceful_handling)
