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

"""Build SQL for the Aurora DSQL MCP tools without parameter binding.

The `readonly_query` and `transact` tools do not accept bound parameters. This
module is the required substitute: every interpolated value MUST pass through a
validator, and `build()` rejects raw strings by construction.

Usage:
    from safe_query import build, allow, regex, ident, keyword, integer, literal
    from safe_query import TENANT_SLUG, UUID

    sql = build(
        "SELECT * FROM {tbl} WHERE tenant_id = {tid} AND entity_id = {eid}",
        tbl=ident("entities"),
        tid=regex(user_tenant, TENANT_SLUG),
        eid=regex(user_eid, UUID),
    )
    readonly_query(sql)

    sql = build(
        "INSERT INTO entities (entity_id, tenant_id, name) "
        "VALUES ({eid}, {tid}, {name})",
        eid=regex(new_id, UUID),
        tid=regex(tenant, TENANT_SLUG),
        name=literal(user_supplied_name),   # free text — dollar-quoted
    )
    transact([sql])

Design rules:
    - Raw strings passed to build() raise UnsafeSQLError. That is the point.
    - Format validation does NOT prove authorization; authorize separately.
    - Server-side filters (readonly mode) catch textbook injection only, and
      they are disabled entirely in --allow-writes mode. Validation here is
      the primary defense, not a backup.
"""

import re
import secrets
import string
from typing import AbstractSet, Any, Pattern


TENANT_SLUG: Pattern[str] = re.compile(r'[a-z0-9-]{1,64}')
UUID: Pattern[str] = re.compile(
    r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
    re.IGNORECASE,
)
INT: Pattern[str] = re.compile(r'-?[0-9]{1,19}')
_IDENT: Pattern[str] = re.compile(r'[a-z_][a-z0-9_]{0,62}', re.IGNORECASE)


class UnsafeSQLError(ValueError):
    """A value failed validation. Never catch and fall back — fix the caller."""


class Safe:
    """A value that has passed validation and is safe to interpolate.

    `build()` accepts only Safe instances. This is how the module prevents
    `build("... {x} ...", x=user_input)` from ever working.
    """

    __slots__ = ('_sql',)

    def __init__(self, sql: str) -> None:
        """Store a validated SQL fragment."""
        self._sql = sql

    def __str__(self) -> str:
        """Return the validated SQL fragment."""
        return self._sql


def allow(value: Any, allowed: AbstractSet[str], *, label: str = 'value') -> Safe:
    """Allowlist-validate and emit as a single-quoted string literal."""
    if value not in allowed:
        raise UnsafeSQLError(f'{label} not in allowlist: {value!r}')
    # Allowlisted values originate from developer-controlled sets; the escape
    # is belt-and-braces in case someone puts a quote in the set.
    return Safe("'" + str(value).replace("'", "''") + "'")


def keyword(value: str, allowed: AbstractSet[str], *, label: str = 'keyword') -> Safe:
    """Allowlist-validate a SQL keyword and emit it unquoted.

    Use for ASC/DESC, AND/OR, or other places where a string literal would be
    syntactically wrong.
    """
    if value not in allowed:
        raise UnsafeSQLError(f'{label} not in allowlist: {value!r}')
    return Safe(value)


def regex(value: Any, pattern: Pattern[str], *, label: str = 'value') -> Safe:
    """Regex-validate with re.fullmatch and emit as a single-quoted literal.

    Rejects values containing a single quote or backslash. `regex()` is for
    strict-format values (UUIDs, slugs, dates) that never legitimately need
    embedded quotes or backslashes; free text belongs in `literal()`, which
    dollar-quotes and sidesteps escaping entirely.
    """
    if not isinstance(value, str) or not pattern.fullmatch(value):
        raise UnsafeSQLError(f'{label} failed pattern {pattern.pattern!r}: {value!r}')
    if "'" in value:
        raise UnsafeSQLError(
            f'{label} contains a single quote; use literal() for free text: {value!r}'
        )
    if '\\' in value:
        raise UnsafeSQLError(
            f'{label} contains a backslash; use literal() for values '
            f'needing special characters: {value!r}'
        )
    return Safe("'" + value + "'")


def ident(name: str) -> Safe:
    """Validate a SQL identifier (table or column) and emit it double-quoted."""
    if not isinstance(name, str) or not _IDENT.fullmatch(name):
        raise UnsafeSQLError(f'invalid identifier: {name!r}')
    return Safe('"' + name + '"')


def integer(value: Any) -> Safe:
    """Validate an integer. Accepts int or numeric string; rejects bool."""
    if isinstance(value, bool):
        raise UnsafeSQLError(f'expected int, got bool: {value!r}')
    if isinstance(value, int):
        return Safe(str(value))
    if isinstance(value, str) and INT.fullmatch(value):
        return Safe(value)
    raise UnsafeSQLError(f'invalid integer: {value!r}')


def literal(value: str) -> Safe:
    """Emit free text as a PostgreSQL dollar-quoted literal.

    Picks a random tag until it does not appear inside `value`, which sidesteps
    quote-escaping entirely. Use for descriptions, names, comments — values
    without a strict format.
    """
    if not isinstance(value, str):
        raise UnsafeSQLError(f'expected str, got {type(value).__name__}')
    for _ in range(8):
        tag = 'dq_' + secrets.token_hex(4)
        boundary = f'${tag}$'
        if boundary not in value:
            return Safe(f'{boundary}{value}{boundary}')
    # Eight 32-bit-random tag collisions implies adversarial input.
    raise UnsafeSQLError('could not generate a unique dollar-quote tag')


def build(template: str, **parts: Safe) -> str:
    """Substitute validated parts into a SQL template.

    Template uses `{name}` placeholders (str.format syntax). Every placeholder
    MUST map to a Safe value; raw strings raise UnsafeSQLError so the
    `build("... {t} ...", t=user_input)` anti-pattern fails loudly.

    Also rejects template/kwargs mismatch: a missing key would otherwise raise
    `KeyError` (invisible to callers catching `UnsafeSQLError`), and an extra
    key would be silently ignored — dropping, for example, a tenant filter
    from the query.
    """
    for key, value in parts.items():
        if not isinstance(value, Safe):
            raise UnsafeSQLError(
                f'{key!r} must be a Safe value from allow/regex/ident/'
                f'keyword/integer/literal; got {type(value).__name__}'
            )
    expected: set[str] = set()
    for _, fname, fspec, conv in string.Formatter().parse(template):
        if fname is None:
            continue
        if fname == '' or fname.isdigit():
            raise UnsafeSQLError(
                f'template contains a positional placeholder {{{fname or ""}}}; '
                f'use named placeholders like {{name}}'
            )
        if conv:
            raise UnsafeSQLError(
                f'placeholder {{{fname}!{conv}}} uses a conversion flag; '
                f'Safe values must be interpolated without conversion'
            )
        if fspec:
            raise UnsafeSQLError(
                f'placeholder {{{fname}:{fspec}}} uses a format spec; '
                f'Safe values must be interpolated without formatting'
            )
        expected.add(fname)
    provided = set(parts.keys())
    if expected != provided:
        missing = expected - provided
        extra = provided - expected
        raise UnsafeSQLError(
            f'template/kwargs mismatch: missing {sorted(missing)}, extra {sorted(extra)}'
        )
    try:
        return template.format(**{k: str(v) for k, v in parts.items()})
    except (KeyError, IndexError) as exc:
        raise UnsafeSQLError(
            f'template references a key not in kwargs (possibly in a format spec): {exc}'
        ) from exc


if __name__ == '__main__':
    # Self-test. Run with: python safe_query.py

    # Happy paths
    assert str(allow('tenant-1', {'tenant-1'})) == "'tenant-1'"
    assert str(keyword('ASC', {'ASC', 'DESC'})) == 'ASC'
    assert str(regex('a-1', TENANT_SLUG)) == "'a-1'"
    assert str(ident('entities')) == '"entities"'
    assert str(integer(42)) == '42'
    assert str(integer('-7')) == '-7'
    assert str(literal("o'reilly")).startswith('$dq_') and "o'reilly" in str(literal("o'reilly"))

    sql = build(
        'SELECT * FROM {t} WHERE tenant_id = {tid}',
        t=ident('entities'),
        tid=regex('acme', TENANT_SLUG),
    )
    assert sql == 'SELECT * FROM "entities" WHERE tenant_id = \'acme\''

    # regex() with a label still works (happy path moved out of rejections)
    assert str(regex('abc', TENANT_SLUG, label='tenant')) == "'abc'"

    # Rejections — every lambda MUST raise UnsafeSQLError
    _permissive = re.compile(r'.+')
    for bad_call in (
        lambda: allow('evil', {'tenant-1'}),
        lambda: keyword('DROP', {'ASC', 'DESC'}),
        lambda: regex("'; DROP TABLE t; --", TENANT_SLUG),
        lambda: ident('x" OR 1=1 --'),
        lambda: integer('1; DROP'),
        lambda: integer(True),
        lambda: literal(123),  # wrong type
        lambda: build('SELECT {x}', x='raw string'),  # core invariant
        # regex() rejects embedded single quotes even when the pattern matches
        lambda: regex("x' OR 1=1 --", _permissive),
        lambda: regex("it's", _permissive),
        lambda: regex("'", _permissive),
        # regex() rejects backslashes
        lambda: regex('abc\\', _permissive),
        # build() rejects template/kwargs mismatch
        lambda: build('SELECT {x}', x=ident('col'), y=ident('extra')),  # extra
        lambda: build('SELECT {x} FROM {y}', x=ident('col')),  # missing
        # build() rejects format conversions, specs, and positional placeholders
        lambda: build('SELECT {x!r}', x=ident('col')),
        lambda: build('SELECT {x:>30}', x=ident('col')),
        lambda: build('SELECT {}', x=ident('col')),
        lambda: build('SELECT {0}', x=ident('col')),
    ):
        try:
            bad_call()
            raise AssertionError(f'expected UnsafeSQLError from {bad_call}')
        except UnsafeSQLError:
            pass

    print('safe_query self-test passed')
