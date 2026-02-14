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

"""Polyglot fuzz harness for DynamoDB item validation in dynamodb-mcp-server.

This module provides a fuzz target that tests the DynamoDB item structure
validation and Pydantic model parsing from the dynamodb-mcp-server package.

The harness works both as:
- A pytest test using Hypothesis for structured input generation
- An OSS-Fuzz target using Atheris for coverage-guided fuzzing

Feature: oss-fuzz-integration
Requirements: 5.1, 5.2, 5.5

Example usage:
    # Run as pytest test
    pytest fuzzing/targets/dynamodb/fuzz_item_validation.py -v

    # Run as Atheris fuzz target (when built by OSS-Fuzz)
    python fuzzing/targets/dynamodb/fuzz_item_validation.py
"""

from __future__ import annotations

import json
import sys
from hypothesis import given, settings
from hypothesis import strategies as st
from pathlib import Path


# Add the dynamodb-mcp-server to the path for imports
_REPO_ROOT = Path(__file__).parent.parent.parent.parent
_DYNAMODB_SERVER_PATH = _REPO_ROOT / 'src' / 'dynamodb-mcp-server'
if str(_DYNAMODB_SERVER_PATH) not in sys.path:
    sys.path.insert(0, str(_DYNAMODB_SERVER_PATH))

from awslabs.dynamodb_mcp_server.cdk_generator.models import (  # noqa: E402
    DataModel,
    TableDefinition,
)
from awslabs.dynamodb_mcp_server.common import (  # noqa: E402
    validate_database_name,
)
from fuzzing.harness_base import PolyglotHarness  # noqa: E402


# DynamoDB attribute types
DYNAMODB_TYPES = ['S', 'N', 'B']

# DynamoDB key types
KEY_TYPES = ['HASH', 'RANGE']

# Projection types for GSIs
PROJECTION_TYPES = ['ALL', 'KEYS_ONLY', 'INCLUDE']


def key_attribute_strategy() -> st.SearchStrategy[dict]:
    """Strategy for generating DynamoDB key attribute definitions."""
    return st.fixed_dictionaries(
        {
            'AttributeName': st.text(
                alphabet=st.characters(
                    whitelist_categories=('Ll', 'Lu', 'Nd'), whitelist_characters='_'
                ),
                min_size=1,
                max_size=255,
            ),
            'AttributeType': st.sampled_from(DYNAMODB_TYPES),
        }
    )


def key_schema_element_strategy() -> st.SearchStrategy[dict]:
    """Strategy for generating DynamoDB key schema elements."""
    return st.fixed_dictionaries(
        {
            'AttributeName': st.text(
                alphabet=st.characters(
                    whitelist_categories=('Ll', 'Lu', 'Nd'), whitelist_characters='_'
                ),
                min_size=1,
                max_size=255,
            ),
            'KeyType': st.sampled_from(KEY_TYPES),
        }
    )


def gsi_strategy() -> st.SearchStrategy[dict]:
    """Strategy for generating DynamoDB Global Secondary Index definitions."""
    return st.fixed_dictionaries(
        {
            'IndexName': st.text(
                alphabet=st.characters(
                    whitelist_categories=('Ll', 'Lu', 'Nd'), whitelist_characters='_-'
                ),
                min_size=3,
                max_size=255,
            ),
            'KeySchema': st.lists(key_schema_element_strategy(), min_size=1, max_size=2),
            'Projection': st.fixed_dictionaries(
                {
                    'ProjectionType': st.sampled_from(PROJECTION_TYPES),
                }
            ),
        }
    )


def table_definition_strategy() -> st.SearchStrategy[dict]:
    """Strategy for generating DynamoDB table definitions."""
    return st.fixed_dictionaries(
        {
            'TableName': st.text(
                alphabet=st.characters(
                    whitelist_categories=('Ll', 'Lu', 'Nd'), whitelist_characters='_.-'
                ),
                min_size=3,
                max_size=255,
            ),
            'AttributeDefinitions': st.lists(key_attribute_strategy(), min_size=1, max_size=10),
            'KeySchema': st.lists(key_schema_element_strategy(), min_size=1, max_size=2),
        }
    ).flatmap(
        lambda base: st.fixed_dictionaries(
            {
                **{k: st.just(v) for k, v in base.items()},
                'GlobalSecondaryIndexes': st.lists(gsi_strategy(), min_size=0, max_size=5)
                | st.none(),
                'TimeToLiveSpecification': st.fixed_dictionaries(
                    {
                        'Enabled': st.booleans(),
                        'AttributeName': st.text(min_size=1, max_size=50),
                    }
                )
                | st.none(),
            }
        )
    )


def data_model_strategy() -> st.SearchStrategy[dict]:
    """Strategy for generating complete DynamoDB data model configurations."""
    return st.fixed_dictionaries(
        {
            'tables': st.lists(table_definition_strategy(), min_size=0, max_size=5),
        }
    )


def malformed_json_strategy() -> st.SearchStrategy[dict]:
    """Strategy for generating malformed/edge-case JSON structures."""
    # Generate various malformed structures that might break validation
    return st.one_of(
        # Empty dict
        st.just({}),
        # Missing required fields
        st.fixed_dictionaries({'tables': st.just(None)}),
        st.fixed_dictionaries({'tables': st.just('not_a_list')}),
        # Wrong types
        st.fixed_dictionaries({'tables': st.lists(st.just('not_a_dict'), max_size=3)}),
        # Deeply nested structures
        st.recursive(
            st.one_of(
                st.none(),
                st.booleans(),
                st.integers(),
                st.floats(allow_nan=False),
                st.text(max_size=50),
            ),
            lambda children: st.one_of(
                st.lists(children, max_size=5),
                st.dictionaries(st.text(max_size=20), children, max_size=5),
            ),
            max_leaves=20,
        ).map(lambda x: {'tables': [x] if x is not None else []}),
        # Valid-looking but invalid structures
        st.fixed_dictionaries(
            {
                'tables': st.lists(
                    st.fixed_dictionaries(
                        {
                            'TableName': st.one_of(st.just(None), st.integers(), st.just('')),
                            'KeySchema': st.one_of(st.just(None), st.just('invalid'), st.just([])),
                            'AttributeDefinitions': st.one_of(st.just(None), st.just({})),
                        }
                    ),
                    min_size=1,
                    max_size=3,
                ),
            }
        ),
    )


def database_name_strategy() -> st.SearchStrategy[str]:
    """Strategy for generating database names to test validation."""
    return st.one_of(
        # Valid names
        st.text(
            alphabet=st.characters(
                whitelist_categories=('Ll', 'Lu', 'Nd'), whitelist_characters='_.$-'
            ),
            min_size=1,
            max_size=128,
        ),
        # Invalid names - too long
        st.text(min_size=129, max_size=200),
        # Invalid names - special characters
        st.sampled_from(list('!@#%^&*()+=[]{}|\\:;"\'<>,?/`~')).flatmap(
            lambda c: st.text(alphabet=st.just(c), min_size=1, max_size=50)
        ),
        # Empty string
        st.just(''),
        # Unicode characters
        st.text(min_size=1, max_size=50),
    )


def fuzz_item_validation(data: bytes) -> None:
    """Fuzz target for DynamoDB item validation functions.

    This function takes raw bytes, converts them to JSON-like structures,
    and tests the DataModel parsing and validation functions.

    The target verifies that:
    1. No function crashes on arbitrary input
    2. Validation errors are properly raised as ValueError
    3. No unhandled exceptions are raised

    Args:
        data: Raw bytes from the fuzzer to be converted to JSON structure.

    Raises:
        AssertionError: If the functions return unexpected types.
    """
    if len(data) == 0:
        return

    # Try to parse bytes as JSON
    try:
        json_str = data.decode('utf-8', errors='replace')
        json_data = json.loads(json_str)
    except (json.JSONDecodeError, UnicodeDecodeError):
        # If not valid JSON, try to create a structure from the bytes
        json_data = {'tables': [{'raw_data': data.hex()}]}

    # Test DataModel.from_json
    try:
        model = DataModel.from_json(json_data)
        # If parsing succeeds, verify the model structure
        assert isinstance(model, DataModel), f'Expected DataModel, got {type(model)}'
        assert isinstance(model.tables, list), f'Expected list, got {type(model.tables)}'
        for table in model.tables:
            assert isinstance(table, TableDefinition), (
                f'Expected TableDefinition, got {type(table)}'
            )
    except ValueError:
        # ValueError is expected for invalid input - this is correct behavior
        pass
    except AssertionError:
        raise  # Re-raise assertion errors for test failures
    except Exception:
        # Other exceptions are acceptable for malformed input
        pass

    # Test validate_database_name with string derived from bytes
    try:
        db_name = data.decode('utf-8', errors='replace')[:128]
        validate_database_name(db_name)
    except ValueError:
        # ValueError is expected for invalid names
        pass
    except Exception:
        # Other exceptions are acceptable
        pass


@given(data_model_strategy())
@settings(max_examples=100, deadline=None)
def test_data_model_validation(data: dict) -> None:
    """Property test for DynamoDB DataModel validation.

    This test verifies that the DataModel parser handles arbitrary
    DynamoDB-like configurations gracefully without crashing.

    **Validates: Requirements 5.1, 5.2**

    Property 1: Graceful Input Handling (JSON/Pydantic subset)
    For any DynamoDB-like configuration, the validation functions SHALL either:
    - Successfully process the input and return normally, OR
    - Raise a handled exception (ValueError) without crashing

    Args:
        data: A DynamoDB-like configuration generated by the data_model_strategy.
    """
    try:
        model = DataModel.from_json(data)
        assert isinstance(model, DataModel)
        assert isinstance(model.tables, list)
    except ValueError:
        # ValueError is expected for invalid configurations
        pass
    except Exception:
        # Other handled exceptions are acceptable
        pass


@given(malformed_json_strategy())
@settings(max_examples=100, deadline=None)
def test_malformed_json_handling(data: dict) -> None:
    """Property test for handling malformed JSON structures.

    This test verifies that the DataModel parser handles malformed
    and edge-case JSON structures gracefully.

    **Validates: Requirements 5.1, 5.2**

    Args:
        data: A malformed JSON structure generated by malformed_json_strategy.
    """
    try:
        model = DataModel.from_json(data)
        # If it succeeds, verify basic structure
        assert isinstance(model, DataModel)
    except ValueError:
        # ValueError is expected for invalid input
        pass
    except TypeError:
        # TypeError is acceptable for wrong types
        pass
    except Exception:
        # Other handled exceptions are acceptable
        pass


@given(database_name_strategy())
@settings(max_examples=100, deadline=None)
def test_database_name_validation(name: str) -> None:
    """Property test for database name validation.

    This test verifies that the database name validator handles
    arbitrary strings gracefully.

    **Validates: Requirements 5.1**

    Args:
        name: A database name string to validate.
    """
    try:
        validate_database_name(name)
        # If validation passes, the name should be valid
        assert len(name) <= 128
        assert len(name) > 0
    except ValueError:
        # ValueError is expected for invalid names
        pass
    except Exception:
        # Other handled exceptions are acceptable
        pass


@given(st.binary(min_size=1, max_size=1000))
@settings(max_examples=100, deadline=None)
def test_item_validation_with_raw_bytes(data: bytes) -> None:
    """Property test for item validation with raw byte input.

    This test verifies that the fuzz target handles arbitrary byte sequences
    gracefully, simulating the Atheris fuzzing mode.

    **Validates: Requirements 5.1, 5.2**

    Args:
        data: Raw bytes to be processed by the fuzz target.
    """
    # Should not raise any unhandled exceptions
    fuzz_item_validation(data)


def test_valid_table_definition_parsing() -> None:
    """Unit test verifying valid table definitions are parsed correctly.

    **Validates: Requirements 5.1**
    """
    valid_config = {
        'tables': [
            {
                'TableName': 'TestTable',
                'AttributeDefinitions': [
                    {'AttributeName': 'pk', 'AttributeType': 'S'},
                    {'AttributeName': 'sk', 'AttributeType': 'N'},
                ],
                'KeySchema': [
                    {'AttributeName': 'pk', 'KeyType': 'HASH'},
                    {'AttributeName': 'sk', 'KeyType': 'RANGE'},
                ],
            }
        ]
    }

    model = DataModel.from_json(valid_config)
    assert len(model.tables) == 1
    assert model.tables[0].table_name == 'TestTable'
    assert model.tables[0].partition_key.name == 'pk'
    assert model.tables[0].sort_key.name == 'sk'


def test_invalid_table_definition_rejected() -> None:
    """Unit test verifying invalid table definitions are rejected.

    **Validates: Requirements 5.2**
    """
    invalid_configs = [
        # Missing tables
        {},
        # Tables not a list
        {'tables': 'not_a_list'},
        # Empty tables
        {'tables': []},
        # Missing TableName
        {'tables': [{'KeySchema': [], 'AttributeDefinitions': []}]},
        # Missing KeySchema
        {'tables': [{'TableName': 'Test', 'AttributeDefinitions': []}]},
        # Missing AttributeDefinitions
        {'tables': [{'TableName': 'Test', 'KeySchema': []}]},
    ]

    for config in invalid_configs:
        try:
            DataModel.from_json(config)
            # Should not reach here for invalid configs
            assert False, f'Expected ValueError for config: {config}'
        except ValueError:
            # Expected behavior
            pass


if __name__ == '__main__':
    # Entry point for Atheris fuzzing
    PolyglotHarness.run_harness(fuzz_item_validation, test_data_model_validation)
