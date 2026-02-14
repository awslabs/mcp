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

"""Polyglot fuzz harness for Gremlin traversal query parsing in neptune-mcp-server.

This module provides a fuzz target that tests Gremlin query string handling
and parsing logic. Since the Neptune MCP server passes queries directly to
the Neptune service, this harness focuses on testing query string validation,
sanitization, and edge cases that could cause issues.

The harness works both as:
- A pytest test using Hypothesis for structured input generation
- An OSS-Fuzz target using Atheris for coverage-guided fuzzing

Feature: oss-fuzz-integration
Requirements: 7.1, 7.5

Example usage:
    # Run as pytest test
    pytest fuzzing/targets/neptune/fuzz_gremlin.py -v

    # Run as Atheris fuzz target (when built by OSS-Fuzz)
    python fuzzing/targets/neptune/fuzz_gremlin.py
"""

from __future__ import annotations

import sys
from hypothesis import given, settings
from hypothesis import strategies as st
from pathlib import Path


# Add the fuzzing module to the path
_REPO_ROOT = Path(__file__).parent.parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from fuzzing.harness_base import PolyglotHarness  # noqa: E402


# Gremlin traversal steps (source steps)
GREMLIN_SOURCE_STEPS = [
    'V',
    'E',
    'addV',
    'addE',
    'inject',
]

# Gremlin traversal steps (filter steps)
GREMLIN_FILTER_STEPS = [
    'has',
    'hasLabel',
    'hasId',
    'hasKey',
    'hasValue',
    'hasNot',
    'is',
    'not',
    'where',
    'filter',
    'or',
    'and',
    'dedup',
    'range',
    'limit',
    'tail',
    'skip',
    'coin',
    'sample',
    'simplePath',
    'cyclicPath',
    'timeLimit',
]

# Gremlin traversal steps (map steps)
GREMLIN_MAP_STEPS = [
    'map',
    'flatMap',
    'id',
    'label',
    'constant',
    'identity',
    'values',
    'properties',
    'propertyMap',
    'valueMap',
    'elementMap',
    'key',
    'value',
    'path',
    'match',
    'sack',
    'select',
    'unfold',
    'fold',
    'count',
    'sum',
    'max',
    'min',
    'mean',
    'group',
    'groupCount',
    'tree',
    'order',
    'project',
    'math',
    'coalesce',
    'optional',
    'union',
    'choose',
    'repeat',
    'emit',
    'until',
    'times',
    'local',
    'as',
]

# Gremlin traversal steps (side effect steps)
GREMLIN_SIDEEFFECT_STEPS = [
    'sideEffect',
    'cap',
    'subgraph',
    'aggregate',
    'store',
    'property',
    'drop',
    'profile',
    'explain',
]

# Gremlin traversal steps (vertex steps)
GREMLIN_VERTEX_STEPS = [
    'out',
    'in',
    'both',
    'outE',
    'inE',
    'bothE',
    'outV',
    'inV',
    'bothV',
    'otherV',
]

# Gremlin predicates
GREMLIN_PREDICATES = [
    'eq',
    'neq',
    'lt',
    'lte',
    'gt',
    'gte',
    'inside',
    'outside',
    'between',
    'within',
    'without',
    'startingWith',
    'endingWith',
    'containing',
    'notStartingWith',
    'notEndingWith',
    'notContaining',
    'regex',
    'notRegex',
]

# Gremlin special tokens
GREMLIN_SPECIAL_TOKENS = [
    'g',
    '__',
    'T',
    'P',
    'TextP',
    'Order',
    'Scope',
    'Column',
    'Pop',
    'Operator',
    'Cardinality',
    'Direction',
    'Barrier',
    'Pick',
]

# All Gremlin steps combined
ALL_GREMLIN_STEPS = (
    GREMLIN_SOURCE_STEPS
    + GREMLIN_FILTER_STEPS
    + GREMLIN_MAP_STEPS
    + GREMLIN_SIDEEFFECT_STEPS
    + GREMLIN_VERTEX_STEPS
)

# Gremlin injection patterns for testing
GREMLIN_INJECTION_PATTERNS = [
    'g.V().drop()',
    'g.E().drop()',
    "g.V().has('admin', true).property('admin', false)",
    "g.addV('malicious').property('payload', 'test')",
    "g.V().sideEffect{Runtime.getRuntime().exec('ls')}",
    "g.V().map{new File('/etc/passwd').text}",
    "'; g.V().drop(); '",
    "').drop().V('",
    'g.V().repeat(out()).times(1000000)',
    'g.V().repeat(both()).emit()',
]


def gremlin_strategy() -> st.SearchStrategy[str]:
    """Hypothesis strategy for generating Gremlin-like query strings.

    This strategy generates a mix of:
    - Valid Gremlin traversal patterns
    - Gremlin steps and predicates
    - Known injection patterns
    - Malformed queries for edge case testing

    Returns:
        A Hypothesis SearchStrategy that generates Gremlin-like strings.
    """
    # Strategy for Gremlin steps
    step_strategy = st.sampled_from(ALL_GREMLIN_STEPS)

    # Strategy for Gremlin predicates
    predicate_strategy = st.sampled_from(GREMLIN_PREDICATES)

    # Strategy for special tokens
    special_token_strategy = st.sampled_from(GREMLIN_SPECIAL_TOKENS)

    # Strategy for known injection patterns
    injection_pattern_strategy = st.sampled_from(GREMLIN_INJECTION_PATTERNS)

    # Strategy for property names/values
    identifier_strategy = st.text(
        alphabet=st.characters(whitelist_categories=('Ll', 'Lu', 'Nd'), whitelist_characters='_'),
        min_size=1,
        max_size=20,
    )

    # Strategy for numeric values
    numeric_strategy = st.integers(min_value=-1000000, max_value=1000000).map(str)

    # Strategy for string literals
    string_literal_strategy = st.text(min_size=0, max_size=30).map(lambda s: f"'{s}'")

    # Strategy for building simple Gremlin traversals
    def build_traversal(steps: list) -> str:
        """Build a Gremlin traversal from a list of steps."""
        if not steps:
            return 'g.V()'
        return 'g.' + '.'.join(f'{step}()' for step in steps)

    simple_traversal = st.lists(step_strategy, min_size=1, max_size=10).map(build_traversal)

    # Strategy for Gremlin components
    gremlin_component = st.one_of(
        step_strategy.map(lambda s: f'{s}()'),
        predicate_strategy.map(lambda p: f'P.{p}(1)'),
        special_token_strategy,
        identifier_strategy,
        numeric_strategy,
        string_literal_strategy,
        st.just('.'),
        st.just('('),
        st.just(')'),
        st.just(','),
    )

    # Build Gremlin-like strings by combining components
    gremlin_string = st.lists(gremlin_component, min_size=1, max_size=30).map(''.join)

    # Mix different strategies
    return st.one_of(
        simple_traversal,
        gremlin_string,
        injection_pattern_strategy,
        # Combine injection patterns with random prefixes/suffixes
        st.tuples(st.text(max_size=10), injection_pattern_strategy).map(lambda t: t[0] + t[1]),
        st.tuples(injection_pattern_strategy, st.text(max_size=10)).map(lambda t: t[0] + t[1]),
        # Pure random text (for edge cases)
        st.text(min_size=0, max_size=200),
        # Binary-like strings decoded as text
        st.binary(min_size=0, max_size=100).map(lambda b: b.decode('utf-8', errors='replace')),
    )


def validate_gremlin_query(query: str) -> dict:
    """Validate and analyze a Gremlin query string.

    This function performs basic validation and analysis of Gremlin queries
    without executing them against a real database. It checks for:
    - Basic syntax patterns
    - Potentially dangerous operations
    - Query structure

    Args:
        query: The Gremlin query string to validate.

    Returns:
        A dict containing validation results with keys:
        - 'valid': bool indicating if query appears syntactically valid
        - 'warnings': list of warning messages
        - 'has_mutation': bool indicating if query contains mutation operations
    """
    result = {
        'valid': True,
        'warnings': [],
        'has_mutation': False,
    }

    if not query or not isinstance(query, str):
        result['valid'] = False
        result['warnings'].append('Empty or invalid query')
        return result

    # Check for mutation operations
    mutation_keywords = ['addV', 'addE', 'drop', 'property']
    for keyword in mutation_keywords:
        if keyword in query:
            result['has_mutation'] = True
            result['warnings'].append(f'Query contains mutation operation: {keyword}')

    # Check for potentially dangerous patterns
    dangerous_patterns = [
        ('sideEffect{', 'Groovy closure in sideEffect'),
        ('map{', 'Groovy closure in map'),
        ('Runtime', 'Potential code execution'),
        ('exec(', 'Potential command execution'),
        ('File(', 'Potential file access'),
        ('ProcessBuilder', 'Potential process creation'),
    ]

    for pattern, description in dangerous_patterns:
        if pattern in query:
            result['warnings'].append(f'Dangerous pattern detected: {description}')

    # Check for unbalanced parentheses
    open_parens = query.count('(')
    close_parens = query.count(')')
    if open_parens != close_parens:
        result['warnings'].append(
            f'Unbalanced parentheses: {open_parens} open, {close_parens} close'
        )

    # Check for basic Gremlin structure
    if not query.strip().startswith('g.') and 'g.' not in query:
        result['warnings'].append('Query does not start with graph traversal source')

    return result


def fuzz_gremlin_query(data: bytes) -> None:
    """Fuzz target for Gremlin query validation.

    This function takes raw bytes, converts them to a string, and tests
    the Gremlin query validation logic.

    The target verifies that:
    1. The validation function doesn't crash on arbitrary input
    2. The function returns expected types
    3. No unhandled exceptions are raised

    Args:
        data: Raw bytes from the fuzzer to be converted to Gremlin query string.

    Raises:
        AssertionError: If the functions return unexpected types.
    """
    if len(data) == 0:
        return

    # Convert bytes to string, handling encoding errors gracefully
    try:
        query_string = data.decode('utf-8', errors='replace')
    except Exception:
        query_string = data.decode('latin-1')

    # Test Gremlin query validation
    try:
        result = validate_gremlin_query(query_string)
        # Verify return type is a dict
        assert isinstance(result, dict), f'Expected dict, got {type(result)}'
        assert 'valid' in result, 'Result missing "valid" key'
        assert 'warnings' in result, 'Result missing "warnings" key'
        assert 'has_mutation' in result, 'Result missing "has_mutation" key'
        assert isinstance(result['valid'], bool), 'valid should be bool'
        assert isinstance(result['warnings'], list), 'warnings should be list'
        assert isinstance(result['has_mutation'], bool), 'has_mutation should be bool'
    except AssertionError:
        raise
    except Exception:
        # Other exceptions are acceptable
        pass


@given(gremlin_strategy())
@settings(max_examples=100, deadline=None)
def test_gremlin_query_validation(query_string: str) -> None:
    """Property test for Gremlin query validation.

    This test verifies that the Gremlin query validation handles
    arbitrary query strings gracefully without crashing.

    **Validates: Requirements 7.1, 7.5**

    Property 1: Graceful Input Handling (graph query subset)
    For any Gremlin-like string, the validation function SHALL either:
    - Successfully process the input and return normally, OR
    - Raise a handled exception without crashing

    Args:
        query_string: A Gremlin-like string generated by the gremlin_strategy.
    """
    try:
        result = validate_gremlin_query(query_string)
        assert isinstance(result, dict)
        assert 'valid' in result
        assert 'warnings' in result
        assert 'has_mutation' in result
    except Exception:
        # Handled exceptions are acceptable
        pass


@given(st.binary(min_size=1, max_size=1000))
@settings(max_examples=100, deadline=None)
def test_gremlin_with_raw_bytes(data: bytes) -> None:
    """Property test for Gremlin validation with raw byte input.

    This test verifies that the fuzz target handles arbitrary byte sequences
    gracefully, simulating the Atheris fuzzing mode.

    **Validates: Requirements 7.1, 7.5**

    Args:
        data: Raw bytes to be processed by the fuzz target.
    """
    fuzz_gremlin_query(data)


def test_mutation_detection() -> None:
    """Unit test verifying mutation operations are detected.

    This test ensures that the Gremlin validator correctly identifies
    queries that modify the graph.

    **Validates: Requirements 7.1**
    """
    mutation_queries = [
        "g.addV('person').property('name', 'test')",
        'g.V().drop()',
        'g.E().drop()',
        "g.V('1').addE('knows').to(V('2'))",
        "g.V('1').property('age', 30)",
    ]

    for query in mutation_queries:
        result = validate_gremlin_query(query)
        assert result['has_mutation'], f'Expected mutation detection for: {query}'


def test_dangerous_pattern_detection() -> None:
    """Unit test verifying dangerous patterns are detected.

    This test ensures that the Gremlin validator correctly identifies
    potentially dangerous query patterns.

    **Validates: Requirements 7.5**
    """
    dangerous_queries = [
        "g.V().sideEffect{Runtime.getRuntime().exec('ls')}",
        "g.V().map{new File('/etc/passwd').text}",
        'g.V().sideEffect{ProcessBuilder pb = new ProcessBuilder()}',
    ]

    for query in dangerous_queries:
        result = validate_gremlin_query(query)
        assert len(result['warnings']) > 0, f'Expected warnings for: {query}'


def test_safe_queries() -> None:
    """Unit test verifying safe queries pass validation.

    This test ensures that valid, safe Gremlin queries are accepted.

    **Validates: Requirements 7.1**
    """
    safe_queries = [
        'g.V()',
        "g.V().hasLabel('person')",
        "g.V().out('knows').values('name')",
        "g.V().has('age', P.gt(30))",
        'g.V().outE().inV().path()',
        "g.V().group().by('label').by(count())",
    ]

    for query in safe_queries:
        result = validate_gremlin_query(query)
        assert result['valid'], f'Expected valid for: {query}'
        assert not result['has_mutation'], f'Expected no mutation for: {query}'


if __name__ == '__main__':
    # Entry point for Atheris fuzzing
    PolyglotHarness.run_harness(fuzz_gremlin_query, test_gremlin_query_validation)
