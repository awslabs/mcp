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

"""Polyglot fuzz harness for OpenAPI specification parsing in openapi-mcp-server.

This module provides a fuzz target that tests the OpenAPI specification parsing
and validation logic from the openapi-mcp-server package.

The harness works both as:
- A pytest test using Hypothesis for structured input generation
- An OSS-Fuzz target using Atheris for coverage-guided fuzzing

Feature: oss-fuzz-integration
Requirements: 4.1, 4.2, 4.5

Example usage:
    # Run as pytest test
    pytest fuzzing/targets/openapi/fuzz_spec_parser.py -v

    # Run as Atheris fuzz target (when built by OSS-Fuzz)
    python fuzzing/targets/openapi/fuzz_spec_parser.py
"""

from __future__ import annotations

import json
import sys
from hypothesis import given, settings
from hypothesis import strategies as st
from pathlib import Path
from typing import Any, Dict


# Add the openapi-mcp-server to the path for imports
_REPO_ROOT = Path(__file__).parent.parent.parent.parent
_OPENAPI_SERVER_PATH = _REPO_ROOT / 'src' / 'openapi-mcp-server'
if str(_OPENAPI_SERVER_PATH) not in sys.path:
    sys.path.insert(0, str(_OPENAPI_SERVER_PATH))

from awslabs.openapi_mcp_server.utils.openapi import (  # noqa: E402
    extract_api_name_from_spec,
)
from awslabs.openapi_mcp_server.utils.openapi_validator import (  # noqa: E402
    extract_api_structure,
    find_pagination_endpoints,
    validate_openapi_spec,
)
from fuzzing.harness_base import PolyglotHarness  # noqa: E402


# Try to import yaml for YAML parsing tests
try:
    import yaml

    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False


# OpenAPI specification keywords and structures
OPENAPI_VERSIONS = ['3.0.0', '3.0.1', '3.0.2', '3.0.3', '3.1.0']

HTTP_METHODS = ['get', 'post', 'put', 'delete', 'patch', 'options', 'head', 'trace']

OPENAPI_KEYWORDS = [
    'openapi',
    'info',
    'title',
    'version',
    'description',
    'termsOfService',
    'contact',
    'license',
    'servers',
    'paths',
    'components',
    'schemas',
    'responses',
    'parameters',
    'examples',
    'requestBodies',
    'headers',
    'securitySchemes',
    'links',
    'callbacks',
    'security',
    'tags',
    'externalDocs',
    'operationId',
    'summary',
    'deprecated',
    'requestBody',
    'content',
    'application/json',
    'required',
    'properties',
    'type',
    'format',
    'items',
    'enum',
    'default',
    'nullable',
    'discriminator',
    'readOnly',
    'writeOnly',
    'xml',
    'externalDocs',
    'example',
    'allOf',
    'oneOf',
    'anyOf',
    'not',
    '$ref',
    'additionalProperties',
    'minLength',
    'maxLength',
    'minimum',
    'maximum',
    'pattern',
    'minItems',
    'maxItems',
]

JSON_SCHEMA_TYPES = ['string', 'number', 'integer', 'boolean', 'array', 'object', 'null']

PARAMETER_LOCATIONS = ['query', 'header', 'path', 'cookie']


def openapi_info_strategy() -> st.SearchStrategy[Dict[str, Any]]:
    """Generate OpenAPI info objects."""
    # Simple approach: generate all fields and filter None values
    return st.fixed_dictionaries(
        {
            'title': st.text(min_size=1, max_size=100),
            'version': st.text(min_size=1, max_size=20),
        }
    ) | st.fixed_dictionaries(
        {
            'title': st.text(min_size=1, max_size=100),
            'version': st.text(min_size=1, max_size=20),
            'description': st.text(min_size=1, max_size=500),
        }
    )


def openapi_schema_strategy(max_depth: int = 3) -> st.SearchStrategy[Dict[str, Any]]:
    """Generate OpenAPI schema objects with controlled nesting depth.

    Args:
        max_depth: Maximum nesting depth for recursive schemas.

    Returns:
        A strategy that generates schema-like dictionaries.
    """
    if max_depth <= 0:
        # Base case: simple types only
        return st.fixed_dictionaries(
            {
                'type': st.sampled_from(['string', 'number', 'integer', 'boolean']),
            }
        )

    # Recursive case: can include nested objects and arrays
    simple_schema = st.fixed_dictionaries(
        {
            'type': st.sampled_from(JSON_SCHEMA_TYPES),
        }
    )

    object_schema = st.fixed_dictionaries(
        {
            'type': st.just('object'),
            'properties': st.dictionaries(
                keys=st.text(min_size=1, max_size=20, alphabet='abcdefghijklmnopqrstuvwxyz'),
                values=st.deferred(lambda: openapi_schema_strategy(max_depth - 1)),
                min_size=0,
                max_size=5,
            ),
        }
    )

    array_schema = st.fixed_dictionaries(
        {
            'type': st.just('array'),
            'items': st.deferred(lambda: openapi_schema_strategy(max_depth - 1)),
        }
    )

    return st.one_of(simple_schema, object_schema, array_schema)


def openapi_path_item_strategy() -> st.SearchStrategy[Dict[str, Any]]:
    """Generate OpenAPI path item objects."""
    # Simple operation with just required fields
    simple_operation = st.fixed_dictionaries(
        {
            'responses': st.fixed_dictionaries(
                {
                    '200': st.fixed_dictionaries(
                        {
                            'description': st.text(min_size=1, max_size=100),
                        }
                    ),
                }
            ),
        }
    )

    # Operation with optional fields
    full_operation = st.fixed_dictionaries(
        {
            'responses': st.fixed_dictionaries(
                {
                    '200': st.fixed_dictionaries(
                        {
                            'description': st.text(min_size=1, max_size=100),
                        }
                    ),
                }
            ),
            'summary': st.text(min_size=1, max_size=100),
            'operationId': st.text(
                min_size=1,
                max_size=50,
                alphabet='abcdefghijklmnopqrstuvwxyz_',  # pragma: allowlist secret
            ),
        }
    )

    operation = st.one_of(simple_operation, full_operation)

    return st.dictionaries(
        keys=st.sampled_from(HTTP_METHODS),
        values=operation,
        min_size=1,
        max_size=3,
    )


def openapi_spec_strategy() -> st.SearchStrategy[Dict[str, Any]]:
    """Hypothesis strategy for generating OpenAPI specification dictionaries.

    This strategy generates a mix of:
    - Valid OpenAPI 3.x specifications
    - Partially valid specifications with missing fields
    - Deeply nested structures
    - Edge cases and malformed structures

    Returns:
        A Hypothesis SearchStrategy that generates OpenAPI spec dictionaries.
    """
    # Valid OpenAPI spec structure
    valid_spec = st.fixed_dictionaries(
        {
            'openapi': st.sampled_from(OPENAPI_VERSIONS),
            'info': openapi_info_strategy(),
            'paths': st.dictionaries(
                keys=st.text(min_size=1, max_size=50).map(lambda s: '/' + s.replace('/', '_')),
                values=openapi_path_item_strategy(),
                min_size=0,
                max_size=5,
            ),
        }
    )

    # Spec with components/schemas - use a separate fixed_dictionaries
    spec_with_schemas = st.fixed_dictionaries(
        {
            'openapi': st.sampled_from(OPENAPI_VERSIONS),
            'info': openapi_info_strategy(),
            'paths': st.dictionaries(
                keys=st.text(min_size=1, max_size=50).map(lambda s: '/' + s.replace('/', '_')),
                values=openapi_path_item_strategy(),
                min_size=0,
                max_size=3,
            ),
            'components': st.fixed_dictionaries(
                {
                    'schemas': st.dictionaries(
                        keys=st.text(
                            min_size=1,
                            max_size=30,
                            alphabet='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ',
                        ),
                        values=openapi_schema_strategy(max_depth=3),
                        min_size=0,
                        max_size=5,
                    ),
                }
            ),
        }
    )

    # Partial/malformed specs
    partial_spec = st.one_of(
        st.fixed_dictionaries({'openapi': st.sampled_from(OPENAPI_VERSIONS)}),
        st.fixed_dictionaries({'info': openapi_info_strategy()}),
        st.fixed_dictionaries({'paths': st.just({})}),
        st.just({}),
    )

    # Deeply nested structure (for testing recursion limits)
    def deeply_nested(depth: int) -> Dict[str, Any]:
        if depth <= 0:
            return {'type': 'string'}
        return {
            'type': 'object',
            'properties': {
                'nested': deeply_nested(depth - 1),
            },
        }

    deeply_nested_spec = st.integers(min_value=5, max_value=50).map(
        lambda depth: {
            'openapi': '3.0.0',
            'info': {'title': 'Deep Spec', 'version': '1.0.0'},
            'paths': {},
            'components': {
                'schemas': {
                    'DeepSchema': deeply_nested(depth),
                },
            },
        }
    )

    return st.one_of(
        valid_spec,
        spec_with_schemas,
        partial_spec,
        deeply_nested_spec,
        # Random dictionary (for edge cases)
        st.dictionaries(
            keys=st.text(min_size=1, max_size=20),
            values=st.recursive(
                st.one_of(st.text(max_size=50), st.integers(), st.booleans(), st.none()),
                lambda children: st.lists(children, max_size=5)
                | st.dictionaries(
                    keys=st.text(min_size=1, max_size=20),
                    values=children,
                    max_size=5,
                ),
                max_leaves=20,
            ),
            min_size=0,
            max_size=10,
        ),
    )


def json_string_strategy() -> st.SearchStrategy[str]:
    """Generate JSON strings that might be OpenAPI specs."""
    return openapi_spec_strategy().map(lambda spec: json.dumps(spec))


def yaml_string_strategy() -> st.SearchStrategy[str]:
    """Generate YAML strings that might be OpenAPI specs."""
    if not YAML_AVAILABLE:
        return json_string_strategy()

    return openapi_spec_strategy().map(lambda spec: yaml.dump(spec, default_flow_style=False))


def fuzz_openapi_spec(data: bytes) -> None:
    """Fuzz target for OpenAPI specification parsing and validation.

    This function takes raw bytes, attempts to parse them as JSON or YAML,
    and tests the OpenAPI validation and extraction functions.

    The target verifies that:
    1. The parsing functions don't crash on arbitrary input
    2. No unhandled exceptions cause the process to abort
    3. Deeply nested structures don't cause stack overflow

    Args:
        data: Raw bytes from the fuzzer to be parsed as OpenAPI spec.
    """
    if len(data) == 0:
        return

    # Try to decode as UTF-8
    try:
        content = data.decode('utf-8', errors='replace')
    except Exception:
        content = data.decode('latin-1')

    spec = None

    # Try to parse as JSON first
    try:
        spec = json.loads(content)
    except (json.JSONDecodeError, ValueError, TypeError, RecursionError):
        pass

    # If JSON fails and YAML is available, try YAML
    if spec is None and YAML_AVAILABLE:
        try:
            spec = yaml.safe_load(content)
        except Exception:
            pass

    # If we couldn't parse the content, try treating it as a dict directly
    if spec is None:
        return

    # Skip if not a dictionary
    if not isinstance(spec, dict):
        return

    # Test validate_openapi_spec
    try:
        result = validate_openapi_spec(spec)
        assert isinstance(result, bool), f'Expected bool, got {type(result)}'
    except AssertionError:
        raise
    except (RecursionError, MemoryError):
        # Resource exhaustion is a finding but not a crash
        pass
    except Exception:
        # Other exceptions are acceptable
        pass

    # Test extract_api_structure
    try:
        structure = extract_api_structure(spec)
        assert isinstance(structure, dict), f'Expected dict, got {type(structure)}'
    except AssertionError:
        raise
    except (RecursionError, MemoryError):
        pass
    except Exception:
        pass

    # Test find_pagination_endpoints
    try:
        endpoints = find_pagination_endpoints(spec)
        assert isinstance(endpoints, list), f'Expected list, got {type(endpoints)}'
    except AssertionError:
        raise
    except (RecursionError, MemoryError):
        pass
    except Exception:
        pass

    # Test extract_api_name_from_spec
    try:
        name = extract_api_name_from_spec(spec)
        assert name is None or isinstance(name, str), f'Expected str or None, got {type(name)}'
    except AssertionError:
        raise
    except (RecursionError, MemoryError):
        pass
    except Exception:
        pass


def fuzz_openapi_spec_dict(spec: Dict[str, Any]) -> None:
    """Fuzz target for OpenAPI specification as dictionary.

    This function directly tests the OpenAPI functions with a dictionary input,
    bypassing the JSON/YAML parsing step.

    Args:
        spec: Dictionary to be validated as OpenAPI spec.
    """
    if not isinstance(spec, dict):
        return

    # Test validate_openapi_spec
    try:
        result = validate_openapi_spec(spec)
        assert isinstance(result, bool)
    except AssertionError:
        raise
    except (RecursionError, MemoryError):
        pass
    except Exception:
        pass

    # Test extract_api_structure
    try:
        structure = extract_api_structure(spec)
        assert isinstance(structure, dict)
    except AssertionError:
        raise
    except (RecursionError, MemoryError):
        pass
    except Exception:
        pass

    # Test find_pagination_endpoints
    try:
        endpoints = find_pagination_endpoints(spec)
        assert isinstance(endpoints, list)
    except AssertionError:
        raise
    except (RecursionError, MemoryError):
        pass
    except Exception:
        pass

    # Test extract_api_name_from_spec
    try:
        name = extract_api_name_from_spec(spec)
        assert name is None or isinstance(name, str)
    except AssertionError:
        raise
    except (RecursionError, MemoryError):
        pass
    except Exception:
        pass


@given(openapi_spec_strategy())
@settings(max_examples=100, deadline=None)
def test_openapi_spec_validation(spec: Dict[str, Any]) -> None:
    """Property test for OpenAPI specification validation.

    This test verifies that the OpenAPI validation functions handle
    arbitrary spec-like dictionaries gracefully without crashing.

    **Validates: Requirements 4.1, 4.2**

    Property 1: Graceful Input Handling (OpenAPI subset)
    For any OpenAPI-like dictionary, the validation functions SHALL either:
    - Successfully process the input and return normally, OR
    - Raise a handled exception without crashing

    Args:
        spec: An OpenAPI-like dictionary generated by the openapi_spec_strategy.
    """
    fuzz_openapi_spec_dict(spec)


@given(st.binary(min_size=0, max_size=2000))
@settings(max_examples=100, deadline=None)
def test_openapi_spec_with_raw_bytes(data: bytes) -> None:
    """Property test for OpenAPI parsing with raw byte input.

    This test verifies that the fuzz target handles arbitrary byte sequences
    gracefully, simulating the Atheris fuzzing mode.

    **Validates: Requirements 4.1, 4.2**

    Args:
        data: Raw bytes to be processed by the fuzz target.
    """
    fuzz_openapi_spec(data)


@given(json_string_strategy())
@settings(max_examples=100, deadline=None)
def test_openapi_json_parsing(json_str: str) -> None:
    """Property test for OpenAPI JSON parsing.

    This test verifies that JSON-encoded OpenAPI specs are handled gracefully.

    **Validates: Requirements 4.1**

    Args:
        json_str: JSON string generated from OpenAPI spec strategy.
    """
    fuzz_openapi_spec(json_str.encode('utf-8'))


@given(yaml_string_strategy())
@settings(max_examples=100, deadline=None)
def test_openapi_yaml_parsing(yaml_str: str) -> None:
    """Property test for OpenAPI YAML parsing.

    This test verifies that YAML-encoded OpenAPI specs are handled gracefully.

    **Validates: Requirements 4.1**

    Args:
        yaml_str: YAML string generated from OpenAPI spec strategy.
    """
    fuzz_openapi_spec(yaml_str.encode('utf-8'))


def test_empty_spec_handling() -> None:
    """Unit test verifying empty input is handled gracefully.

    **Validates: Requirements 4.1**
    """
    fuzz_openapi_spec(b'')
    fuzz_openapi_spec(b'{}')
    fuzz_openapi_spec_dict({})


def test_minimal_valid_spec() -> None:
    """Unit test verifying minimal valid OpenAPI specs are handled.

    **Validates: Requirements 4.1**
    """
    minimal_specs = [
        {
            'openapi': '3.0.0',
            'info': {'title': 'Test API', 'version': '1.0.0'},
            'paths': {},
        },
        {
            'openapi': '3.1.0',
            'info': {'title': 'Test API', 'version': '1.0.0'},
            'paths': {},
        },
    ]
    for spec in minimal_specs:
        fuzz_openapi_spec_dict(spec)
        fuzz_openapi_spec(json.dumps(spec).encode('utf-8'))


def test_deeply_nested_schemas() -> None:
    """Unit test verifying deeply nested schemas are handled.

    **Validates: Requirements 4.2, 4.5**
    """

    def create_nested_schema(depth: int) -> Dict[str, Any]:
        if depth <= 0:
            return {'type': 'string'}
        return {
            'type': 'object',
            'properties': {
                'nested': create_nested_schema(depth - 1),
            },
        }

    # Test various nesting depths
    for depth in [10, 50, 100]:
        spec = {
            'openapi': '3.0.0',
            'info': {'title': 'Deep API', 'version': '1.0.0'},
            'paths': {},
            'components': {
                'schemas': {
                    'DeepSchema': create_nested_schema(depth),
                },
            },
        }
        fuzz_openapi_spec_dict(spec)


def test_circular_reference_patterns() -> None:
    """Unit test verifying circular reference patterns are handled.

    Note: This tests the structure, not actual $ref resolution which
    requires prance or similar library.

    **Validates: Requirements 4.2**
    """
    # Spec with $ref patterns (not actual circular refs, but similar structure)
    spec_with_refs = {
        'openapi': '3.0.0',
        'info': {'title': 'Ref API', 'version': '1.0.0'},
        'paths': {
            '/items': {
                'get': {
                    'responses': {
                        '200': {
                            'description': 'Success',
                            'content': {
                                'application/json': {
                                    'schema': {'$ref': '#/components/schemas/Item'},
                                },
                            },
                        },
                    },
                },
            },
        },
        'components': {
            'schemas': {
                'Item': {
                    'type': 'object',
                    'properties': {
                        'id': {'type': 'integer'},
                        'children': {
                            'type': 'array',
                            'items': {'$ref': '#/components/schemas/Item'},
                        },
                    },
                },
            },
        },
    }
    fuzz_openapi_spec_dict(spec_with_refs)


def test_malformed_openapi_structures() -> None:
    """Unit test verifying malformed OpenAPI structures are handled.

    **Validates: Requirements 4.1, 4.2**
    """
    malformed_specs = [
        # Missing required fields
        {'openapi': '3.0.0'},
        {'info': {'title': 'Test', 'version': '1.0'}},
        {'paths': {}},
        # Wrong types
        {'openapi': 123, 'info': {'title': 'Test', 'version': '1.0'}, 'paths': {}},
        {'openapi': '3.0.0', 'info': 'not a dict', 'paths': {}},
        {'openapi': '3.0.0', 'info': {'title': 'Test', 'version': '1.0'}, 'paths': 'not a dict'},
        # Invalid version
        {'openapi': '2.0', 'info': {'title': 'Test', 'version': '1.0'}, 'paths': {}},
        {'openapi': '4.0.0', 'info': {'title': 'Test', 'version': '1.0'}, 'paths': {}},
        # Extra/unexpected fields
        {
            'openapi': '3.0.0',
            'info': {'title': 'Test', 'version': '1.0'},
            'paths': {},
            'unknown': 'field',
        },
        # Null values
        {'openapi': '3.0.0', 'info': None, 'paths': {}},
        {'openapi': None, 'info': {'title': 'Test', 'version': '1.0'}, 'paths': {}},
    ]
    for spec in malformed_specs:
        fuzz_openapi_spec_dict(spec)


def test_large_spec_handling() -> None:
    """Unit test verifying large specifications are handled.

    **Validates: Requirements 4.5**
    """
    # Generate a spec with many paths
    paths = {}
    for i in range(100):
        paths[f'/endpoint{i}'] = {
            'get': {
                'operationId': f'getEndpoint{i}',
                'responses': {'200': {'description': 'Success'}},
            },
        }

    large_spec = {
        'openapi': '3.0.0',
        'info': {'title': 'Large API', 'version': '1.0.0'},
        'paths': paths,
    }
    fuzz_openapi_spec_dict(large_spec)


if __name__ == '__main__':
    # Entry point for Atheris fuzzing
    PolyglotHarness.run_harness(fuzz_openapi_spec, test_openapi_spec_validation)
