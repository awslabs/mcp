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
    'UNINSTALL',
    # Storage-level
    'OPTIMIZE',
    'REPAIR',
    'ANALYZE',
    # Session / server config — SET as a general keyword is rejected in
    # read-only mode. Specific security-sensitive variables are also
    # rejected in write mode via SECURITY_SENSITIVE_VAR_PATTERN below.
    # Matches the Postgres sibling's model. The blanket SET block
    # rejects benign forms (SET @var, SET NAMES, SET sql_mode) too;
    # an LLM-driven read flow has SQL-native alternatives for all of
    # them and the closed-by-construction shape is worth the trade-off.
    'SET',
    # Stored-program execution. CALL invokes a procedure that can
    # INSERT/UPDATE/DELETE/GRANT inside its body — the readonly gate
    # cannot see what's in the procedure, so the safe answer is to
    # reject the call site.
    'CALL',
    # Dynamic SQL: PREPARE/EXECUTE/DEALLOCATE round-trips bypass the
    # static keyword scan because the payload lives in a user variable.
    # Each statement is rejected individually; even if PREPARE were
    # missed, EXECUTE on its own is enough to fire the gate.
    'PREPARE',
    'EXECUTE',
    'DEALLOCATE',
    # Direct storage-engine access. HANDLER bypasses the SQL layer's
    # transaction semantics entirely.
    'HANDLER',
    # Lock and admin state changes. LOCK / UNLOCK acquire write locks
    # that survive the readonly transaction and affect concurrent
    # workloads. FLUSH / RESET change server-wide state (privileges,
    # binlog position, query log). KILL terminates other sessions.
    'LOCK',
    'LOCK TABLES',
    'UNLOCK',
    'UNLOCK TABLES',
    'FLUSH',
    'RESET',
    'KILL',
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


# Session variables that disable integrity / security controls. Setting
# any of these silently changes what subsequent statements on the same
# connection do, so they are rejected in BOTH read-only and write mode:
#
#   sql_log_bin = 0
#       Disables binary logging for the session. A subsequent INSERT /
#       UPDATE / DELETE will not appear in the binlog, defeating
#       replication, point-in-time recovery, and audit pipelines that
#       consume the binlog.
#   foreign_key_checks = 0
#       Skips referential-integrity validation. Subsequent writes can
#       leave orphaned rows that violate declared FK constraints.
#   unique_checks = 0
#       Skips uniqueness validation on InnoDB inserts. Allows duplicate
#       rows to be inserted past a UNIQUE index.
#
# These are session settings, so blocking the SET that toggles them is
# the only practical defence against an LLM that has --allow_write_query
# enabled. The Postgres sibling uses the same pattern for row_security
# and session_replication_role; this is the MySQL analogue.
SECURITY_SENSITIVE_VARS = {
    'sql_log_bin',
    'foreign_key_checks',
    'unique_checks',
}

# Match SET ... <var> ... where <var> is one of SECURITY_SENSITIVE_VARS,
# accepting the modifier permutations MySQL allows:
#   SET sql_log_bin = 0
#   SET SESSION sql_log_bin = 0
#   SET LOCAL sql_log_bin = 0
#   SET GLOBAL sql_log_bin = 0
#   SET @@sql_log_bin = 0
#   SET @@session.sql_log_bin = 0
#   SET @@global.sql_log_bin = 0
#   SET @@local.sql_log_bin = 0
# The trailing \b prevents matches on prefixed identifiers (e.g.
# sql_log_bin_extra). Quoted identifiers (`sql_log_bin`) are NOT
# matched — a known regex limitation, mirroring the Postgres sibling.
#
# Multi-variable SET statements (MySQL allows comma-separated assignments
# in a single SET — ``SET @x = 1, sql_log_bin = 0``) are handled by the
# optional ``(?:.{0,500}?,\s*)?`` group: non-greedy, bounded to 500 chars
# to prevent catastrophic backtracking, and ``re.DOTALL`` lets it span
# newlines between assignments. The engine extends the wildcard as needed
# to land on a security-sensitive variable in any position of the list,
# so payloads like ``SET @x = 1, @y = 2, sql_log_bin = 0`` are caught.
#
# Known limitation: ``UPDATE t SET sql_log_bin = 0`` would false-positive
# (the regex matches as if it were a session-variable SET). Real-world
# risk is essentially zero — no realistic schema names a column after a
# well-known MySQL session variable — and the cost is rejecting one
# unusual query in write mode, not a security leak. Closing this would
# require sqlparse tokenisation to distinguish statement-level SET from
# UPDATE's SET clause; deemed not worth the complexity at this time.
SECURITY_SENSITIVE_VAR_PATTERN = re.compile(
    r'\bset\b\s+'
    r'(?:.{0,500}?,\s*)?'  # optionally skip preceding assignments in the same SET
    r'(?:(?:session|local|global)\s+)?'
    r'(?:@@(?:session\.|local\.|global\.)?)?'
    r'(' + '|'.join(re.escape(v) for v in SECURITY_SENSITIVE_VARS) + r')\b',
    re.IGNORECASE | re.DOTALL,
)


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

    Stage 2 also includes a security-sensitive-variable check that
    rejects ``SET sql_log_bin``, ``SET foreign_key_checks``, and
    ``SET unique_checks`` regardless of read/write mode. These session
    settings disable integrity / security controls and an LLM-driven
    flow should never be able to flip them — even when the operator has
    enabled writes via ``--allow_write_query``. Pattern mirrors the
    Postgres sibling's ``SECURITY_SENSITIVE_GUCS`` design.

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

    # Stage 2a: reject SET of security-sensitive session variables in
    # both read and write mode. These disable integrity / security
    # controls (binlog, FK checks, uniqueness) for the rest of the
    # session, so an LLM should never be able to flip them — even when
    # the operator has explicitly enabled writes.
    var_match = SECURITY_SENSITIVE_VAR_PATTERN.search(sql_for_check)
    if var_match:
        issues.append(
            {
                'type': 'sql',
                'message': (
                    f'Security-sensitive SET rejected: {var_match.group(1)}. '
                    'Changing this session setting disables an integrity or '
                    'security control (binary logging / referential integrity / '
                    'uniqueness) and is blocked regardless of read/write mode.'
                ),
                'severity': 'high',
            }
        )
        return issues

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
