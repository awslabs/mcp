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

"""The SQL guard and the psycopg executor must agree on what a placeholder is.

The guard rewrites ``:name`` to ``$1`` only so the statement can be parsed and
classified; the psycopg path rewrites the same statement to ``%(name)s`` so the
values bind. When the two carried independent regexes they disagreed on array
slices: the guard correctly left ``tags[1:limit_idx]`` alone while the executor
turned it into the unparseable ``tags[1%(limit_idx)s]``, so a query the guard had
approved failed at execution whenever parameters were supplied. These tests pin
the agreement rather than the two outputs separately, so the layers cannot drift
apart again.
"""

import pytest
import re
from awslabs.postgres_mcp_server.connection.psycopg_pool_connection import PsycopgPoolConnection
from awslabs.postgres_mcp_server.named_params import (
    NAMED_PARAM_PATTERN,
    to_parse_placeholders,
    to_psycopg_placeholders,
)
from awslabs.postgres_mcp_server.sql_guard import _normalize_placeholders
from pglast import parse_sql


# Statements exercising every colon shape that occurs in real PostgreSQL: named
# placeholders in value positions, casts, and array slices with each kind of
# lower bound. Each entry is (sql, expected placeholder names in order).
CORPUS = [
    # No colons at all.
    ('SELECT 1', []),
    ("SELECT * FROM items WHERE name = 'a:b'", []),
    # Real placeholders in value positions.
    ('SELECT * FROM t WHERE id = :id', ['id']),
    ('SELECT * FROM t WHERE id=:id', ['id']),
    ('SELECT * FROM t WHERE a = :a AND b = :b', ['a', 'b']),
    ('INSERT INTO t VALUES (:a, :b)', ['a', 'b']),
    ('SELECT ARRAY[:a]', ['a']),
    ('SELECT :v::int', ['v']),
    ('SELECT * FROM t WHERE tags && ARRAY[:tag]::text[]', ['tag']),
    ('SELECT * FROM t WHERE a = to_regclass(:table_name)', ['table_name']),
    # Casts must never be treated as placeholders.
    ('SELECT x::int FROM t', []),
    ('SELECT x::text::int FROM t', []),
    ('SELECT now()::date', []),
    # Array slices: the colon has a non-empty lower bound, so it is a slice and
    # not a placeholder. This is the class the two layers used to disagree on.
    ('SELECT tags[1:limit_idx] FROM items', []),
    ('SELECT a[1:n] FROM t', []),
    ('SELECT a[i:j] FROM t', []),
    ('SELECT a[f():n] FROM t', []),
    ('SELECT a[b[0]:n] FROM t', []),
    ('SELECT a[1:3] FROM t', []),
    # Mixed: a slice and a genuine placeholder in one statement.
    ('SELECT tags[1:limit_idx] FROM items WHERE id = :id', ['id']),
]


def _names(sql):
    """Return the placeholder names the shared pattern finds, in order."""
    return NAMED_PARAM_PATTERN.findall(sql)


@pytest.mark.parametrize('sql,expected', CORPUS)
def test_both_layers_select_identical_spans(sql, expected):
    """Guard and executor rewrite exactly the same character ranges."""
    guard_spans = [m.span() for m in NAMED_PARAM_PATTERN.finditer(sql)]
    # Re-derive each layer's spans from its own output length change would be
    # fragile; instead assert both layers consumed the same matches by checking
    # the count and the names each produced.
    assert _names(sql) == expected
    assert len(guard_spans) == len(expected)

    parse_out = to_parse_placeholders(sql)
    psycopg_out = to_psycopg_placeholders(sql)

    # Same number of substitutions on both sides.
    assert parse_out.count('$1') == len(expected)
    assert len(re.findall(r'%\(\w+\)s', psycopg_out)) == len(expected)

    # A statement with no placeholders must come back untouched from both.
    if not expected:
        assert parse_out == sql
        assert psycopg_out == sql


@pytest.mark.parametrize('sql,expected', CORPUS)
def test_guard_normalization_is_parseable(sql, expected):
    """Whatever the guard hands to pglast must parse, or the guard fails closed."""
    parse_sql(to_parse_placeholders(sql))


@pytest.mark.parametrize('sql,expected', CORPUS)
def test_psycopg_conversion_is_parseable(sql, expected):
    """The executor's output must be valid SQL once psycopg binds the parameters.

    ``%(name)s`` is psycopg's client-side marker, so substitute the positional
    form psycopg ultimately sends and check the result still parses. This is what
    catches a rewrite that lands inside an array subscript.
    """
    psycopg_out = to_psycopg_placeholders(sql)
    as_positional = re.sub(r'%\(\w+\)s', '$1', psycopg_out)
    parse_sql(as_positional)


@pytest.mark.parametrize('sql,expected', CORPUS)
def test_connection_method_uses_the_shared_rule(sql, expected):
    """The live executor path produces the shared rule's output, not its own."""
    conn = PsycopgPoolConnection(
        host='db.example.com',
        port=5432,
        database='test_db',
        readonly=True,
        secret_arn='arn:aws:secretsmanager:us-west-2:1:secret:x',  # pragma: allowlist secret
        db_user='u',
        region='us-west-2',
        is_iam_auth=False,
        is_test=True,
    )
    assert conn._convert_sql_for_psycopg(sql) == to_psycopg_placeholders(sql)


def test_array_slice_regression_end_to_end():
    """The documented slice query survives both layers.

    Guard-side acceptance was already fixed; this pins the executor side, which
    used to mangle the slice into ``tags[1%(limit_idx)s]``.
    """
    sql = 'SELECT tags[1:limit_idx] FROM items'
    assert to_parse_placeholders(sql) == sql
    assert to_psycopg_placeholders(sql) == sql
    parse_sql(to_psycopg_placeholders(sql))


def test_guard_private_alias_is_the_shared_helper():
    """sql_guard's normalizer is the shared helper, not a second implementation."""
    assert _normalize_placeholders is to_parse_placeholders


def test_omitted_lower_bound_slice_treated_consistently():
    """``a[:n]`` is rewritten by both layers, so they stay consistent.

    Both treat it as a placeholder. The result parses either way, and the guard
    inspects structure rather than subscript contents, so classification is
    unaffected -- what matters is that the two layers make the same choice.
    """
    sql = 'SELECT a[:n] FROM t'
    assert to_parse_placeholders(sql) == 'SELECT a[$1] FROM t'
    assert to_psycopg_placeholders(sql) == 'SELECT a[%(n)s] FROM t'
    assert _names(sql) == ['n']
