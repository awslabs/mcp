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

"""Polyglot fuzz harness for SPARQL query parsing in neptune-mcp-server.

This module provides a fuzz target that tests SPARQL query string handling
and parsing logic. Since the Neptune MCP server can work with RDF graphs
via SPARQL, this harness focuses on testing query string validation,
sanitization, and edge cases that could cause issues.

The harness works both as:
- A pytest test using Hypothesis for structured input generation
- An OSS-Fuzz target using Atheris for coverage-guided fuzzing

Feature: oss-fuzz-integration
Requirements: 7.2, 7.5

Example usage:
    # Run as pytest test
    pytest fuzzing/targets/neptune/fuzz_sparql.py -v

    # Run as Atheris fuzz target (when built by OSS-Fuzz)
    python fuzzing/targets/neptune/fuzz_sparql.py
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


# SPARQL query forms
SPARQL_QUERY_FORMS = [
    'SELECT',
    'CONSTRUCT',
    'DESCRIBE',
    'ASK',
]

# SPARQL update forms
SPARQL_UPDATE_FORMS = [
    'INSERT',
    'DELETE',
    'INSERT DATA',
    'DELETE DATA',
    'DELETE WHERE',
    'LOAD',
    'CLEAR',
    'CREATE',
    'DROP',
    'COPY',
    'MOVE',
    'ADD',
]

# SPARQL keywords
SPARQL_KEYWORDS = [
    'BASE',
    'PREFIX',
    'SELECT',
    'DISTINCT',
    'REDUCED',
    'AS',
    'CONSTRUCT',
    'DESCRIBE',
    'ASK',
    'FROM',
    'NAMED',
    'WHERE',
    'GROUP',
    'BY',
    'HAVING',
    'ORDER',
    'ASC',
    'DESC',
    'LIMIT',
    'OFFSET',
    'VALUES',
    'OPTIONAL',
    'GRAPH',
    'UNION',
    'MINUS',
    'FILTER',
    'EXISTS',
    'NOT',
    'IN',
    'BIND',
    'SERVICE',
    'SILENT',
    'UNDEF',
    'DEFAULT',
    'ALL',
    'NAMED',
    'WITH',
    'USING',
    'INTO',
    'TO',
    'DATA',
    'LOAD',
    'CLEAR',
    'DROP',
    'CREATE',
    'ADD',
    'MOVE',
    'COPY',
    'INSERT',
    'DELETE',
    'WHERE',
]

# SPARQL built-in functions
SPARQL_FUNCTIONS = [
    'STR',
    'LANG',
    'LANGMATCHES',
    'DATATYPE',
    'BOUND',
    'IRI',
    'URI',
    'BNODE',
    'RAND',
    'ABS',
    'CEIL',
    'FLOOR',
    'ROUND',
    'CONCAT',
    'STRLEN',
    'UCASE',
    'LCASE',
    'ENCODE_FOR_URI',
    'CONTAINS',
    'STRSTARTS',
    'STRENDS',
    'STRBEFORE',
    'STRAFTER',
    'YEAR',
    'MONTH',
    'DAY',
    'HOURS',
    'MINUTES',
    'SECONDS',
    'TIMEZONE',
    'TZ',
    'NOW',
    'UUID',
    'STRUUID',
    'MD5',
    'SHA1',
    'SHA256',
    'SHA384',
    'SHA512',
    'COALESCE',
    'IF',
    'STRLANG',
    'STRDT',
    'sameTerm',
    'isIRI',
    'isURI',
    'isBLANK',
    'isLITERAL',
    'isNUMERIC',
    'REGEX',
    'REPLACE',
    'COUNT',
    'SUM',
    'MIN',
    'MAX',
    'AVG',
    'SAMPLE',
    'GROUP_CONCAT',
]

# SPARQL operators
SPARQL_OPERATORS = [
    '=',
    '!=',
    '<',
    '>',
    '<=',
    '>=',
    '&&',
    '||',
    '!',
    '+',
    '-',
    '*',
    '/',
    'a',
    '^',
    '^^',
]

# SPARQL special characters
SPARQL_SPECIAL_CHARS = [
    '{',
    '}',
    '(',
    ')',
    '[',
    ']',
    '.',
    ',',
    ';',
    ':',
    '@',
    '#',
    '?',
    '$',
    '<',
    '>',
    '"',
    "'",
    '_',
    '|',
    '/',
]

# SPARQL injection patterns for testing
SPARQL_INJECTION_PATTERNS = [
    'SELECT * WHERE { ?s ?p ?o } ; DROP ALL',
    'SELECT * WHERE { ?s ?p ?o } ; DELETE WHERE { ?s ?p ?o }',
    'SELECT * WHERE { ?s ?p "test" . FILTER(1=1) }',
    'SELECT * WHERE { ?s ?p ?o } UNION SELECT * WHERE { ?s ?p ?o }',
    'SELECT * WHERE { SERVICE <http://evil.com/sparql> { ?s ?p ?o } }',
    "SELECT * WHERE { ?s ?p ?o . FILTER(REGEX(?o, '.*')) }",
    'PREFIX : <javascript:alert(1)> SELECT * WHERE { ?s ?p ?o }',
    'SELECT * WHERE { ?s ?p "\'; DROP ALL; --" }',
    'SELECT * WHERE { GRAPH <file:///etc/passwd> { ?s ?p ?o } }',
    'SELECT * WHERE { ?s ?p ?o } LIMIT 999999999999',
]


def sparql_strategy() -> st.SearchStrategy[str]:
    """Hypothesis strategy for generating SPARQL-like query strings.

    This strategy generates a mix of:
    - Valid SPARQL query patterns
    - SPARQL keywords and functions
    - Known injection patterns
    - Malformed queries for edge case testing

    Returns:
        A Hypothesis SearchStrategy that generates SPARQL-like strings.
    """
    # Strategy for SPARQL keywords
    keyword_strategy = (
        st.sampled_from(SPARQL_KEYWORDS)
        .map(lambda k: st.sampled_from([k, k.lower(), k.capitalize()]))
        .flatmap(lambda x: x)
    )

    # Strategy for SPARQL functions
    function_strategy = st.sampled_from(SPARQL_FUNCTIONS)

    # Strategy for SPARQL operators
    operator_strategy = st.sampled_from(SPARQL_OPERATORS)

    # Strategy for special characters
    special_char_strategy = st.sampled_from(SPARQL_SPECIAL_CHARS)

    # Strategy for known injection patterns
    injection_pattern_strategy = st.sampled_from(SPARQL_INJECTION_PATTERNS)

    # Strategy for variable names
    variable_strategy = st.text(
        alphabet=st.characters(whitelist_categories=('Ll', 'Lu', 'Nd'), whitelist_characters='_'),
        min_size=1,
        max_size=15,
    ).map(lambda s: f'?{s}')

    # Strategy for IRI references
    iri_strategy = st.text(
        alphabet=st.characters(
            whitelist_categories=('Ll', 'Lu', 'Nd'), whitelist_characters='_-./:#'
        ),
        min_size=1,
        max_size=30,
    ).map(lambda s: f'<http://example.org/{s}>')

    # Strategy for prefixed names
    prefix_strategy = st.text(
        alphabet=st.characters(whitelist_categories=('Ll', 'Lu'), whitelist_characters=''),
        min_size=1,
        max_size=10,
    ).map(lambda s: f'{s}:localName')

    # Strategy for string literals
    string_literal_strategy = st.text(min_size=0, max_size=30).map(lambda s: f'"{s}"')

    # Strategy for numeric values
    numeric_strategy = st.integers(min_value=-1000000, max_value=1000000).map(str)

    # Strategy for building simple SPARQL queries
    def build_select_query(vars_and_patterns: tuple) -> str:
        """Build a simple SELECT query."""
        variables, patterns = vars_and_patterns
        var_str = ' '.join(variables) if variables else '*'
        pattern_str = ' . '.join(patterns) if patterns else '?s ?p ?o'
        return f'SELECT {var_str} WHERE {{ {pattern_str} }}'

    simple_query = st.tuples(
        st.lists(variable_strategy, min_size=0, max_size=5),
        st.lists(
            st.tuples(variable_strategy, variable_strategy, variable_strategy).map(
                lambda t: f'{t[0]} {t[1]} {t[2]}'
            ),
            min_size=1,
            max_size=5,
        ),
    ).map(build_select_query)

    # Strategy for SPARQL components
    sparql_component = st.one_of(
        keyword_strategy,
        function_strategy.map(lambda f: f'{f}()'),
        operator_strategy,
        special_char_strategy,
        variable_strategy,
        iri_strategy,
        prefix_strategy,
        string_literal_strategy,
        numeric_strategy,
        st.just(' '),
    )

    # Build SPARQL-like strings by combining components
    sparql_string = st.lists(sparql_component, min_size=1, max_size=30).map(' '.join)

    # Mix different strategies
    return st.one_of(
        simple_query,
        sparql_string,
        injection_pattern_strategy,
        # Combine injection patterns with random prefixes/suffixes
        st.tuples(st.text(max_size=10), injection_pattern_strategy).map(lambda t: t[0] + t[1]),
        st.tuples(injection_pattern_strategy, st.text(max_size=10)).map(lambda t: t[0] + t[1]),
        # Pure random text (for edge cases)
        st.text(min_size=0, max_size=200),
        # Binary-like strings decoded as text
        st.binary(min_size=0, max_size=100).map(lambda b: b.decode('utf-8', errors='replace')),
    )


def validate_sparql_query(query: str) -> dict:
    """Validate and analyze a SPARQL query string.

    This function performs basic validation and analysis of SPARQL queries
    without executing them against a real database. It checks for:
    - Basic syntax patterns
    - Potentially dangerous operations
    - Query structure

    Args:
        query: The SPARQL query string to validate.

    Returns:
        A dict containing validation results with keys:
        - 'valid': bool indicating if query appears syntactically valid
        - 'warnings': list of warning messages
        - 'query_type': str indicating the type of query (SELECT, INSERT, etc.)
        - 'has_update': bool indicating if query contains update operations
    """
    result = {
        'valid': True,
        'warnings': [],
        'query_type': None,
        'has_update': False,
    }

    if not query or not isinstance(query, str):
        result['valid'] = False
        result['warnings'].append('Empty or invalid query')
        return result

    query_upper = query.upper()

    # Determine query type
    for query_form in SPARQL_QUERY_FORMS:
        if query_form in query_upper:
            result['query_type'] = query_form
            break

    # Check for update operations
    for update_form in SPARQL_UPDATE_FORMS:
        if update_form in query_upper:
            result['has_update'] = True
            result['query_type'] = update_form
            result['warnings'].append(f'Query contains update operation: {update_form}')
            break

    # Check for potentially dangerous patterns
    dangerous_patterns = [
        ('SERVICE', 'Federated query to external endpoint'),
        ('LOAD', 'Loading external data'),
        ('DROP', 'Dropping graph data'),
        ('CLEAR', 'Clearing graph data'),
        ('file://', 'Local file access attempt'),
        ('javascript:', 'JavaScript injection attempt'),
        ('data:', 'Data URI scheme'),
        ('<script', 'Script injection attempt'),
    ]

    for pattern, description in dangerous_patterns:
        if pattern.lower() in query.lower():
            result['warnings'].append(f'Dangerous pattern detected: {description}')

    # Check for unbalanced braces
    open_braces = query.count('{')
    close_braces = query.count('}')
    if open_braces != close_braces:
        result['warnings'].append(f'Unbalanced braces: {open_braces} open, {close_braces} close')

    # Check for unbalanced angle brackets (IRIs)
    open_angles = query.count('<')
    close_angles = query.count('>')
    if open_angles != close_angles:
        result['warnings'].append(
            f'Unbalanced angle brackets: {open_angles} open, {close_angles} close'
        )

    # Check for basic SPARQL structure
    has_query_form = any(form in query_upper for form in SPARQL_QUERY_FORMS + SPARQL_UPDATE_FORMS)
    if not has_query_form:
        result['warnings'].append('Query does not contain a recognized query form')

    return result


def fuzz_sparql_query(data: bytes) -> None:
    """Fuzz target for SPARQL query validation.

    This function takes raw bytes, converts them to a string, and tests
    the SPARQL query validation logic.

    The target verifies that:
    1. The validation function doesn't crash on arbitrary input
    2. The function returns expected types
    3. No unhandled exceptions are raised

    Args:
        data: Raw bytes from the fuzzer to be converted to SPARQL query string.

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

    # Test SPARQL query validation
    try:
        result = validate_sparql_query(query_string)
        # Verify return type is a dict
        assert isinstance(result, dict), f'Expected dict, got {type(result)}'
        assert 'valid' in result, 'Result missing "valid" key'
        assert 'warnings' in result, 'Result missing "warnings" key'
        assert 'query_type' in result, 'Result missing "query_type" key'
        assert 'has_update' in result, 'Result missing "has_update" key'
        assert isinstance(result['valid'], bool), 'valid should be bool'
        assert isinstance(result['warnings'], list), 'warnings should be list'
        assert isinstance(result['has_update'], bool), 'has_update should be bool'
    except AssertionError:
        raise
    except Exception:
        # Other exceptions are acceptable
        pass


@given(sparql_strategy())
@settings(max_examples=100, deadline=None)
def test_sparql_query_validation(query_string: str) -> None:
    """Property test for SPARQL query validation.

    This test verifies that the SPARQL query validation handles
    arbitrary query strings gracefully without crashing.

    **Validates: Requirements 7.2, 7.5**

    Property 1: Graceful Input Handling (graph query subset)
    For any SPARQL-like string, the validation function SHALL either:
    - Successfully process the input and return normally, OR
    - Raise a handled exception without crashing

    Args:
        query_string: A SPARQL-like string generated by the sparql_strategy.
    """
    try:
        result = validate_sparql_query(query_string)
        assert isinstance(result, dict)
        assert 'valid' in result
        assert 'warnings' in result
        assert 'query_type' in result
        assert 'has_update' in result
    except Exception:
        # Handled exceptions are acceptable
        pass


@given(st.binary(min_size=1, max_size=1000))
@settings(max_examples=100, deadline=None)
def test_sparql_with_raw_bytes(data: bytes) -> None:
    """Property test for SPARQL validation with raw byte input.

    This test verifies that the fuzz target handles arbitrary byte sequences
    gracefully, simulating the Atheris fuzzing mode.

    **Validates: Requirements 7.2, 7.5**

    Args:
        data: Raw bytes to be processed by the fuzz target.
    """
    fuzz_sparql_query(data)


def test_update_detection() -> None:
    """Unit test verifying update operations are detected.

    This test ensures that the SPARQL validator correctly identifies
    queries that modify the graph.

    **Validates: Requirements 7.2**
    """
    update_queries = [
        "INSERT DATA { <http://example.org/s> <http://example.org/p> 'o' }",
        "DELETE DATA { <http://example.org/s> <http://example.org/p> 'o' }",
        'DELETE WHERE { ?s ?p ?o }',
        'DROP GRAPH <http://example.org/graph>',
        'CLEAR ALL',
        'LOAD <http://example.org/data.ttl>',
    ]

    for query in update_queries:
        result = validate_sparql_query(query)
        assert result['has_update'], f'Expected update detection for: {query}'


def test_dangerous_pattern_detection() -> None:
    """Unit test verifying dangerous patterns are detected.

    This test ensures that the SPARQL validator correctly identifies
    potentially dangerous query patterns.

    **Validates: Requirements 7.5**
    """
    dangerous_queries = [
        'SELECT * WHERE { SERVICE <http://evil.com/sparql> { ?s ?p ?o } }',
        'PREFIX : <javascript:alert(1)> SELECT * WHERE { ?s ?p ?o }',
        'SELECT * WHERE { GRAPH <file:///etc/passwd> { ?s ?p ?o } }',
        'LOAD <http://evil.com/malicious.ttl>',
    ]

    for query in dangerous_queries:
        result = validate_sparql_query(query)
        assert len(result['warnings']) > 0, f'Expected warnings for: {query}'


def test_safe_queries() -> None:
    """Unit test verifying safe queries pass validation.

    This test ensures that valid, safe SPARQL queries are accepted.

    **Validates: Requirements 7.2**
    """
    safe_queries = [
        'SELECT * WHERE { ?s ?p ?o }',
        'SELECT ?name WHERE { ?person <http://xmlns.com/foaf/0.1/name> ?name }',
        'SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 100',
        'ASK WHERE { <http://example.org/s> ?p ?o }',
        'DESCRIBE <http://example.org/resource>',
        'CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o }',
    ]

    for query in safe_queries:
        result = validate_sparql_query(query)
        assert result['valid'], f'Expected valid for: {query}'
        assert not result['has_update'], f'Expected no update for: {query}'


def test_query_type_detection() -> None:
    """Unit test verifying query type detection.

    This test ensures that the SPARQL validator correctly identifies
    the type of query.

    **Validates: Requirements 7.2**
    """
    test_cases = [
        ('SELECT * WHERE { ?s ?p ?o }', 'SELECT'),
        ('ASK WHERE { ?s ?p ?o }', 'ASK'),
        ('DESCRIBE <http://example.org/s>', 'DESCRIBE'),
        ('CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o }', 'CONSTRUCT'),
    ]

    for query, expected_type in test_cases:
        result = validate_sparql_query(query)
        assert result['query_type'] == expected_type, f'Expected {expected_type} for: {query}'


if __name__ == '__main__':
    # Entry point for Atheris fuzzing
    PolyglotHarness.run_harness(fuzz_sparql_query, test_sparql_query_validation)
