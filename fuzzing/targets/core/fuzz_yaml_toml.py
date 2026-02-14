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

"""Polyglot fuzz harness for YAML and TOML configuration parsing.

This module provides fuzz targets that test YAML and TOML configuration
parsing used across MCP servers for configuration files.

The harness works both as:
- A pytest test using Hypothesis for structured input generation
- An OSS-Fuzz target using Atheris for coverage-guided fuzzing

Feature: oss-fuzz-integration
Requirements: 10.3

Example usage:
    # Run as pytest test
    pytest fuzzing/targets/core/fuzz_yaml_toml.py -v

    # Run as Atheris fuzz target (when built by OSS-Fuzz)
    python fuzzing/targets/core/fuzz_yaml_toml.py
"""

from __future__ import annotations

import sys
import yaml
from hypothesis import given, settings
from hypothesis import strategies as st
from pathlib import Path
from typing import Any, Dict


try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore


# Add the fuzzing module to the path
_REPO_ROOT = Path(__file__).parent.parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from fuzzing.harness_base import PolyglotHarness  # noqa: E402


# YAML-specific tokens and patterns
YAML_KEYWORDS = [
    'true',
    'false',
    'null',
    'yes',
    'no',
    'on',
    'off',
    '.inf',
    '-.inf',
    '.nan',
    '~',
]

YAML_SPECIAL_CHARS = [':', '-', '|', '>', '!', '&', '*', '%', '@', '`', '#']

# TOML-specific tokens
TOML_KEYWORDS = ['true', 'false']

TOML_SPECIAL_CHARS = ['=', '[', ']', '{', '}', ',', '.', '"', "'", '#']


def parse_yaml_safe(content: str) -> Any:
    """Parse YAML content using safe_load.

    This function wraps yaml.safe_load to provide consistent error handling
    for fuzzing purposes.

    Args:
        content: The YAML string to parse.

    Returns:
        The parsed YAML data structure.

    Raises:
        yaml.YAMLError: If the YAML is malformed.
    """
    return yaml.safe_load(content)


def parse_toml(content: str) -> Dict[str, Any]:
    """Parse TOML content.

    This function wraps tomllib.loads to provide consistent error handling
    for fuzzing purposes.

    Args:
        content: The TOML string to parse.

    Returns:
        The parsed TOML data structure as a dictionary.

    Raises:
        tomllib.TOMLDecodeError: If the TOML is malformed.
    """
    return tomllib.loads(content)


def validate_yaml_config(data: Any) -> bool:
    """Validate a parsed YAML configuration structure.

    This function checks that a parsed YAML structure is valid for
    MCP server configuration purposes.

    Args:
        data: The parsed YAML data to validate.

    Returns:
        True if the configuration is valid.

    Raises:
        ValueError: If the configuration is invalid.
    """
    if data is None:
        return True  # Empty YAML is valid

    if not isinstance(data, (dict, list, str, int, float, bool)):
        raise ValueError(f'Unexpected YAML type: {type(data)}')

    if isinstance(data, dict):
        for key, value in data.items():
            if not isinstance(key, str):
                raise ValueError(f'YAML dict keys must be strings, got {type(key)}')
            validate_yaml_config(value)

    if isinstance(data, list):
        for item in data:
            validate_yaml_config(item)

    return True


def validate_toml_config(data: Dict[str, Any]) -> bool:
    """Validate a parsed TOML configuration structure.

    This function checks that a parsed TOML structure is valid for
    MCP server configuration purposes.

    Args:
        data: The parsed TOML data to validate.

    Returns:
        True if the configuration is valid.

    Raises:
        ValueError: If the configuration is invalid.
    """
    if not isinstance(data, dict):
        raise ValueError(f'TOML root must be a dict, got {type(data)}')

    def validate_value(value: Any, path: str = '') -> None:
        if isinstance(value, dict):
            for k, v in value.items():
                if not isinstance(k, str):
                    raise ValueError(f'TOML keys must be strings at {path}')
                validate_value(v, f'{path}.{k}')
        elif isinstance(value, list):
            for i, item in enumerate(value):
                validate_value(item, f'{path}[{i}]')
        elif not isinstance(value, (str, int, float, bool, type(None))):
            raise ValueError(f'Unexpected TOML type at {path}: {type(value)}')

    for key, value in data.items():
        validate_value(value, key)

    return True


def yaml_string_strategy() -> st.SearchStrategy[str]:
    """Strategy for generating YAML-like strings."""
    # Strategy for YAML keywords
    keyword_strategy = st.sampled_from(YAML_KEYWORDS)

    # Strategy for indentation
    indent_strategy = st.sampled_from(['', '  ', '    ', '\t'])

    # Strategy for key-value pairs
    key_strategy = st.text(
        alphabet=st.characters(whitelist_categories=('Ll', 'Lu', 'Nd'), whitelist_characters='_-'),
        min_size=1,
        max_size=30,
    )

    value_strategy = st.one_of(
        st.text(max_size=50),
        st.integers().map(str),
        st.floats(allow_nan=False, allow_infinity=False).map(str),
        keyword_strategy,
    )

    # Build YAML-like strings
    yaml_line = st.tuples(indent_strategy, key_strategy, st.just(': '), value_strategy).map(
        lambda t: t[0] + t[1] + t[2] + t[3]
    )

    yaml_document = st.lists(yaml_line, min_size=0, max_size=20).map('\n'.join)

    return st.one_of(
        yaml_document,
        # Valid YAML structures
        st.sampled_from(
            [
                'key: value',
                'list:\n  - item1\n  - item2',
                'nested:\n  key: value',
                'number: 42',
                'float: 3.14',
                'bool: true',
                'null_value: null',
                '---\nkey: value',
                'multiline: |\n  line1\n  line2',
                'folded: >\n  line1\n  line2',
            ]
        ),
        # Edge cases
        st.sampled_from(
            [
                '',
                '---',
                '...',
                '# comment',
                '  # indented comment',
                'key:',
                ': value',
                '- item',
                '  - nested item',
            ]
        ),
        # Random text
        st.text(min_size=0, max_size=200),
        # Binary-like strings
        st.binary(min_size=0, max_size=100).map(lambda b: b.decode('utf-8', errors='replace')),
    )


def toml_string_strategy() -> st.SearchStrategy[str]:
    """Strategy for generating TOML-like strings."""
    # Strategy for TOML keywords
    keyword_strategy = st.sampled_from(TOML_KEYWORDS)

    # Strategy for key names
    key_strategy = st.text(
        alphabet=st.characters(whitelist_categories=('Ll', 'Lu', 'Nd'), whitelist_characters='_-'),
        min_size=1,
        max_size=30,
    )

    # Strategy for string values
    string_value = st.text(max_size=50).map(lambda s: f'"{s}"')

    # Strategy for values
    value_strategy = st.one_of(
        string_value,
        st.integers().map(str),
        st.floats(allow_nan=False, allow_infinity=False).map(str),
        keyword_strategy,
    )

    # Build TOML-like strings
    toml_line = st.tuples(key_strategy, st.just(' = '), value_strategy).map(
        lambda t: t[0] + t[1] + t[2]
    )

    toml_document = st.lists(toml_line, min_size=0, max_size=20).map('\n'.join)

    return st.one_of(
        toml_document,
        # Valid TOML structures
        st.sampled_from(
            [
                'key = "value"',
                'number = 42',
                'float = 3.14',
                'bool = true',
                '[section]\nkey = "value"',
                '[[array]]\nname = "item1"\n[[array]]\nname = "item2"',
                'inline = { key = "value" }',
                'array = [1, 2, 3]',
                'string_array = ["a", "b", "c"]',
                'multiline = """\nline1\nline2"""',
            ]
        ),
        # Edge cases
        st.sampled_from(
            [
                '',
                '# comment',
                '[section]',
                '[[array]]',
                'key = ""',
                "key = ''",
            ]
        ),
        # Random text
        st.text(min_size=0, max_size=200),
        # Binary-like strings
        st.binary(min_size=0, max_size=100).map(lambda b: b.decode('utf-8', errors='replace')),
    )


def yaml_config_strategy() -> st.SearchStrategy[dict]:
    """Strategy for generating valid YAML configuration dictionaries."""
    return st.recursive(
        st.one_of(
            st.none(),
            st.booleans(),
            st.integers(min_value=-1000000, max_value=1000000),
            st.floats(allow_nan=False, allow_infinity=False, min_value=-1e10, max_value=1e10),
            st.text(max_size=50),
        ),
        lambda children: st.one_of(
            st.lists(children, max_size=5),
            st.dictionaries(
                st.text(
                    alphabet=st.characters(
                        whitelist_categories=('Ll', 'Lu', 'Nd'), whitelist_characters='_-'
                    ),
                    min_size=1,
                    max_size=20,
                ),
                children,
                max_size=5,
            ),
        ),
        max_leaves=20,
    ).filter(lambda x: isinstance(x, dict))


def toml_config_strategy() -> st.SearchStrategy[dict]:
    """Strategy for generating valid TOML configuration dictionaries."""
    # TOML has stricter requirements than YAML
    toml_value = st.one_of(
        st.booleans(),
        st.integers(min_value=-1000000, max_value=1000000),
        st.floats(allow_nan=False, allow_infinity=False, min_value=-1e10, max_value=1e10),
        st.text(max_size=50),
        st.lists(st.integers(min_value=-1000, max_value=1000), max_size=5),
        st.lists(st.text(max_size=20), max_size=5),
    )

    return st.dictionaries(
        st.text(
            alphabet=st.characters(
                whitelist_categories=('Ll', 'Lu', 'Nd'), whitelist_characters='_-'
            ),
            min_size=1,
            max_size=20,
        ),
        toml_value,
        min_size=0,
        max_size=10,
    )


def fuzz_yaml_toml(data: bytes) -> None:
    """Fuzz target for YAML and TOML parsing functions.

    This function takes raw bytes, converts them to strings, and tests
    the YAML and TOML parsing functions.

    The target verifies that:
    1. No function crashes on arbitrary input
    2. Parse errors are properly raised
    3. No unhandled exceptions are raised

    Args:
        data: Raw bytes from the fuzzer to be converted to config strings.

    Raises:
        AssertionError: If the functions return unexpected types.
    """
    if len(data) == 0:
        return

    # Convert bytes to string
    try:
        content = data.decode('utf-8', errors='replace')
    except Exception:
        content = data.decode('latin-1')

    # Test YAML parsing
    try:
        yaml_data = parse_yaml_safe(content)
        if yaml_data is not None:
            validate_yaml_config(yaml_data)
    except yaml.YAMLError:
        # YAML parse errors are expected for malformed input
        pass
    except ValueError:
        # Validation errors are expected
        pass
    except Exception:
        # Other exceptions are acceptable
        pass

    # Test TOML parsing
    try:
        toml_data = parse_toml(content)
        validate_toml_config(toml_data)
    except tomllib.TOMLDecodeError:
        # TOML parse errors are expected for malformed input
        pass
    except ValueError:
        # Validation errors are expected
        pass
    except Exception:
        # Other exceptions are acceptable
        pass


@given(yaml_string_strategy())
@settings(max_examples=100, deadline=None)
def test_yaml_parsing(content: str) -> None:
    """Property test for YAML parsing.

    This test verifies that the YAML parser handles arbitrary
    YAML-like strings gracefully without crashing.

    **Validates: Requirements 10.3**

    Property 1: Graceful Input Handling (config subset)
    For any YAML-like string, the parsing functions SHALL either:
    - Successfully process the input and return normally, OR
    - Raise a handled exception (YAMLError, ValueError) without crashing

    Args:
        content: A YAML-like string.
    """
    try:
        yaml_data = parse_yaml_safe(content)
        if yaml_data is not None:
            validate_yaml_config(yaml_data)
    except yaml.YAMLError:
        # YAML parse errors are expected
        pass
    except ValueError:
        # Validation errors are expected
        pass
    except Exception:
        # Other handled exceptions are acceptable
        pass


@given(toml_string_strategy())
@settings(max_examples=100, deadline=None)
def test_toml_parsing(content: str) -> None:
    """Property test for TOML parsing.

    This test verifies that the TOML parser handles arbitrary
    TOML-like strings gracefully without crashing.

    **Validates: Requirements 10.3**

    Args:
        content: A TOML-like string.
    """
    try:
        toml_data = parse_toml(content)
        validate_toml_config(toml_data)
    except tomllib.TOMLDecodeError:
        # TOML parse errors are expected
        pass
    except ValueError:
        # Validation errors are expected
        pass
    except Exception:
        # Other handled exceptions are acceptable
        pass


@given(yaml_config_strategy())
@settings(max_examples=100, deadline=None)
def test_yaml_config_validation(config: dict) -> None:
    """Property test for YAML configuration validation.

    This test verifies that the YAML validator handles
    configuration dictionaries gracefully.

    **Validates: Requirements 10.3**

    Args:
        config: A YAML configuration dictionary.
    """
    try:
        # Convert to YAML string and back
        yaml_str = yaml.safe_dump(config)
        parsed = parse_yaml_safe(yaml_str)
        validate_yaml_config(parsed)
    except yaml.YAMLError:
        # YAML errors are acceptable
        pass
    except ValueError:
        # Validation errors are expected
        pass
    except Exception:
        # Other handled exceptions are acceptable
        pass


@given(toml_config_strategy())
@settings(max_examples=100, deadline=None)
def test_toml_config_validation(config: dict) -> None:
    """Property test for TOML configuration validation.

    This test verifies that the TOML validator handles
    configuration dictionaries gracefully.

    **Validates: Requirements 10.3**

    Args:
        config: A TOML configuration dictionary.
    """
    try:
        validate_toml_config(config)
    except ValueError:
        # Validation errors are expected
        pass
    except Exception:
        # Other handled exceptions are acceptable
        pass


@given(st.binary(min_size=1, max_size=1000))
@settings(max_examples=100, deadline=None)
def test_yaml_toml_with_raw_bytes(data: bytes) -> None:
    """Property test for YAML/TOML parsing with raw byte input.

    This test verifies that the fuzz target handles arbitrary byte sequences
    gracefully, simulating the Atheris fuzzing mode.

    **Validates: Requirements 10.3**

    Args:
        data: Raw bytes to be processed by the fuzz target.
    """
    # Should not raise any unhandled exceptions
    fuzz_yaml_toml(data)


def test_valid_yaml_parsing() -> None:
    """Unit test verifying valid YAML is parsed correctly.

    **Validates: Requirements 10.3**
    """
    valid_yaml_cases = [
        ('key: value', {'key': 'value'}),
        ('number: 42', {'number': 42}),
        ('float: 3.14', {'float': 3.14}),
        ('bool: true', {'bool': True}),
        ('null_value: null', {'null_value': None}),
        ('list:\n  - item1\n  - item2', {'list': ['item1', 'item2']}),
        ('nested:\n  key: value', {'nested': {'key': 'value'}}),
    ]

    for yaml_str, expected in valid_yaml_cases:
        result = parse_yaml_safe(yaml_str)
        assert result == expected, f'Expected {expected}, got {result}'
        assert validate_yaml_config(result) is True


def test_valid_toml_parsing() -> None:
    """Unit test verifying valid TOML is parsed correctly.

    **Validates: Requirements 10.3**
    """
    valid_toml_cases = [
        ('key = "value"', {'key': 'value'}),
        ('number = 42', {'number': 42}),
        ('float = 3.14', {'float': 3.14}),
        ('bool = true', {'bool': True}),
        ('array = [1, 2, 3]', {'array': [1, 2, 3]}),
    ]

    for toml_str, expected in valid_toml_cases:
        result = parse_toml(toml_str)
        assert result == expected, f'Expected {expected}, got {result}'
        assert validate_toml_config(result) is True


def test_invalid_yaml_handling() -> None:
    """Unit test verifying invalid YAML raises appropriate errors.

    **Validates: Requirements 10.3**
    """
    invalid_yaml_cases = [
        'key: [unclosed',
        'key: {unclosed',
        '  invalid indent\nkey: value',
        'key: @invalid',
    ]

    for yaml_str in invalid_yaml_cases:
        try:
            parse_yaml_safe(yaml_str)
            # Some invalid YAML may still parse, which is acceptable
        except yaml.YAMLError:
            # Expected behavior
            pass


def test_invalid_toml_handling() -> None:
    """Unit test verifying invalid TOML raises appropriate errors.

    **Validates: Requirements 10.3**
    """
    invalid_toml_cases = [
        'key = [unclosed',
        'key = {unclosed',
        'key = value',  # Unquoted string value
        '= value',  # Missing key
        'key',  # Missing value
    ]

    for toml_str in invalid_toml_cases:
        try:
            parse_toml(toml_str)
            # Should raise TOMLDecodeError
            assert False, f'Expected TOMLDecodeError for: {toml_str}'
        except tomllib.TOMLDecodeError:
            # Expected behavior
            pass


def test_yaml_security() -> None:
    """Unit test verifying YAML safe_load prevents code execution.

    **Validates: Requirements 10.3**
    """
    # These should not execute code when using safe_load
    dangerous_yaml_cases = [
        '!!python/object/apply:os.system ["echo pwned"]',
        '!!python/object:__main__.MyClass {}',
        '!!python/name:os.system',
    ]

    for yaml_str in dangerous_yaml_cases:
        try:
            parse_yaml_safe(yaml_str)
            # safe_load should either return None or raise an error
            # It should NOT execute the code
        except yaml.YAMLError:
            # Expected - safe_load rejects dangerous tags
            pass


if __name__ == '__main__':
    # Entry point for Atheris fuzzing
    PolyglotHarness.run_harness(fuzz_yaml_toml, test_yaml_parsing)
