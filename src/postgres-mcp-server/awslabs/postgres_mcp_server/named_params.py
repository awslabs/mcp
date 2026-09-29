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

"""Single definition of which ``:name`` sequences are parameter placeholders.

Aurora / RDS Data API style named placeholders (``:name``) are not valid
PostgreSQL syntax, so two different layers have to find them and rewrite them:

* the SQL policy guard rewrites them to ``$1`` purely so ``pglast`` can parse the
  statement and classify it (the ORIGINAL SQL is what executes); and
* the psycopg (PG Wire) execution path rewrites them to psycopg's ``%(name)s``
  so the values are bound as real parameters.

Both must agree on *which* colons are placeholders. When they disagreed, the
guard's stricter rule accepted ``SELECT tags[1:limit_idx] FROM items`` as an
array slice while the executor rewrote it to the unparseable
``SELECT tags[1%(limit_idx)s] FROM items``, so a query the guard had approved
failed at execution whenever parameters were supplied. The pattern therefore
lives here once and both layers import it; only the replacement text differs.

Pattern rationale: the negative lookbehind refuses to rewrite a colon preceded by
``:`` (the ``::`` cast operator), a word character, ``]``, or ``)``. None of
those prefixes can begin a real ``:name`` placeholder, but each occurs before an
array-slice colon whose lower bound is non-empty (``a[1:n]``, ``a[i:j]``,
``a[f():n]``, ``a[b[0]:n]``). Leaving the slice colon alone lets the slice parse
as ordinary SQL. A placeholder in a value position is still matched: ``= :id``,
``id=:id``, ``(:a, :b)``, ``ARRAY[:a]``, ``:v::int``. (A slice with an omitted
lower bound, ``a[:n]``, is treated as a placeholder by both layers -- it still
parses and still binds, so the two remain consistent.)
"""

import re


# The one definition of a named placeholder. Callers supply their own
# replacement; they must not re-derive the matching rule.
NAMED_PARAM_PATTERN = re.compile(r'(?<![\w:\]\)]):([a-zA-Z_]\w*)')


def to_parse_placeholders(sql: str) -> str:
    """Rewrite ``:name`` to ``$1`` so the SQL can be parsed for classification.

    ``$1`` occupies a value position, so it never changes the statement type,
    function names, or GUC targets the guard inspects. The substitution is not
    literal-aware, so a ``:name``-shaped sequence inside a string literal is
    rewritten too; that is safe for the same reason -- ``$1`` inside quotes
    remains part of the string literal.

    Args:
        sql: The statement text as supplied by the caller.

    Returns:
        str: The statement with named placeholders replaced by ``$1``.
    """
    return NAMED_PARAM_PATTERN.sub('$1', sql)


def to_psycopg_placeholders(sql: str) -> str:
    """Rewrite ``:name`` to psycopg's ``%(name)s`` binding syntax.

    Args:
        sql: The statement text as supplied by the caller.

    Returns:
        str: The statement with named placeholders in psycopg form.
    """
    return NAMED_PARAM_PATTERN.sub(r'%(\1)s', sql)
