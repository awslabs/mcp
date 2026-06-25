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

import re
import sqlparse


MUTATING_KEYWORDS = {
    # DML
    'INSERT',
    'UPDATE',
    'DELETE',
    'MERGE',
    'TRUNCATE',
    'REPLACE INTO',
    'LOAD DATA',
    'LOAD XML',
    # DDL
    'CREATE',
    'DROP',
    'ALTER',
    'RENAME',
    'RENAME TABLE',
    # Permissions
    'GRANT',
    'REVOKE',
    # Extensions and functions
    'CREATE FUNCTION',
    'CREATE PROCEDURE',
    'INSTALL',
    # Storage-level
    'OPTIMIZE',
    'REPAIR',
    'ANALYZE',
}

# Compile regex pattern.
#
# Keywords are sorted longest-first so that multi-word entries
# (e.g. ``RENAME TABLE``, ``LOAD DATA``, ``CREATE FUNCTION``) match before
# their single-word prefixes (``RENAME``, ``LOAD``, ``CREATE``). Python's
# ``re`` uses leftmost-first alternation, not leftmost-longest, so without
# this ordering the prefix can win the race and the longer keyword is
# never reported. Iterating ``MUTATING_KEYWORDS`` directly would also be
# non-deterministic across runs because Python ``set`` iteration order is
# hash-seed dependent.
_MUTATING_KEYWORDS_BY_LENGTH = sorted(MUTATING_KEYWORDS, key=len, reverse=True)
MUTATING_PATTERN = re.compile(
    r'(?i)\b(' + '|'.join(re.escape(k) for k in _MUTATING_KEYWORDS_BY_LENGTH) + r')\b'
)

SUSPICIOUS_PATTERNS = [
    r"(?i)'.*?--",  # comment injection
    r'(?i)\bor\b\s+\d+\s*=\s*\d+',  # numeric tautology e.g. OR 1=1
    r"(?i)\bor\b\s*'[^']+'\s*=\s*'[^']+'",  # string tautology e.g. OR '1'='1'
    r'(?i)\bunion\b.*\bselect\b',  # UNION SELECT
    r'(?i)\bdrop\b',  # DROP statement
    r'(?i)\btruncate\b',  # TRUNCATE
    r'(?i)\bgrant\b|\brevoke\b',  # GRANT or REVOKE
    r';\s*(?!($|\s*--|\s*/\*))(?=\S)',  # stacked queries
    r'(?i)\bsleep\s*\(',  # delay-based probes
    r'(?i)\bbenchmark\s*\(',  # MySQL-specific delay probe
    r'(?i)\bload_file\s*\(',
    r'(?i)\binto\s+outfile\b',
    r'(?i)\binto\s+dumpfile\b',  # MySQL-specific file write
]

# MySQL conditional comment marker (`/*!`). MySQL 5.0+ executes the contents
# of these blocks while sqlparse strips them, so the detector would otherwise
# never see what the database is going to run. We treat any presence of `/*!`
# as a suspicious pattern in its own right; there is no benign reason for an
# LLM-generated query to use a MySQL conditional comment through this server.
MYSQL_CONDITIONAL_COMMENT_PATTERN = r'/\*!'


def detect_mutating_keywords(sql_text: str) -> list[str]:
    """Return a list of mutating keywords found in the SQL (excluding comments).

    SQL inline comments (`/* ... */`, `-- ...`, `# ...`) are treated as
    whitespace by the database parser but as opaque characters by Python
    regex. To prevent bypasses such as `LOAD/**/DATA INFILE ...`, the SQL
    is normalised with `sqlparse.format(strip_comments=True)` before the
    keyword scan so a comment between adjacent keywords no longer hides
    the multi-word match (e.g. `LOAD DATA`, `RENAME TABLE`).

    MySQL conditional comments (`/*!50000 ... */`) are handled separately:
    sqlparse strips them entirely, so a payload like
    ``/*!50000 DELETE FROM users */`` would otherwise have its body
    stripped before the regex runs and the function would return ``[]``.
    Any presence of the ``/*!`` marker is therefore treated as a mutation
    in its own right (MySQL 5.0+ executes the body server-side, so the
    conservative answer for a readonly gate is "yes, this mutates").
    A non-keyword sentinel is returned so callers' ``bool(matches)``
    checks fire without misreporting a specific keyword.
    """
    if re.search(MYSQL_CONDITIONAL_COMMENT_PATTERN, sql_text):
        # Defence in depth: keep this function correct in isolation, even
        # when callers do not also invoke check_sql_injection_risk.
        return ['MYSQL_CONDITIONAL_COMMENT']
    sql_for_check = sqlparse.format(sql_text, strip_comments=True)
    matches = MUTATING_PATTERN.findall(sql_for_check)
    return list({m.upper() for m in matches})


def check_sql_injection_risk(sql: str) -> list[dict]:
    r"""Check for potential SQL injection risks in sql query.

    Comment-based bypasses are mitigated in two stages:

    1. MySQL conditional comments (``/*!50000 ... */``) are checked against
       the raw SQL first. sqlparse would strip them before any pattern
       gets a chance to match, so the check has to happen pre-strip.
    2. The remaining suspicious patterns run against the comment-stripped
       SQL so that ``INTO/**/OUTFILE``, ``INTO -- x\n DUMPFILE``, etc. all
       normalise to their bare form and the existing regexes match.

    Patterns are deliberately NOT applied to the raw SQL as a fallback,
    to avoid false-positives on benign queries whose comment text happens
    to contain forbidden keywords (e.g. ``-- export INTO OUTFILE later``).

    Args:
        sql: query string

    Returns:
        dictionaries containing detected security issue
    """
    issues = []

    # Stage 1: reject MySQL conditional comments before sqlparse strips them.
    if re.search(MYSQL_CONDITIONAL_COMMENT_PATTERN, sql):
        issues.append(
            {
                'type': 'sql',
                'message': f'Suspicious pattern in query: {sql}',
                'severity': 'high',
            }
        )
        return issues

    # Stage 2: strip ordinary comments, then run the regex sweep.
    sql_for_check = sqlparse.format(sql, strip_comments=True)
    for pattern in SUSPICIOUS_PATTERNS:
        if re.search(pattern, sql_for_check):
            issues.append(
                {
                    'type': 'sql',
                    'message': f'Suspicious pattern in query: {sql}',
                    'severity': 'high',
                }
            )
            break
    return issues
