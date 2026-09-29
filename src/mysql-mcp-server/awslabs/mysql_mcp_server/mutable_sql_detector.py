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


# Statement-leading verbs that are non-read / state-affecting, and that are
# also common identifiers or functions.
#
# "State-affecting" is broader than "mutates data": some entries change data
# or server/replication state (IMPORT, REPLACE, CHANGE, PURGE, SHUTDOWN, ...)
# while others are transaction control that a read-only session still must
# not issue (BEGIN, COMMIT, ROLLBACK, SAVEPOINT, RELEASE, and DO with no
# side-effecting call). ``DO expr`` returns no result set yet can have side
# effects (e.g. ``DO GET_LOCK(...)``).
#
# Unlike MUTATING_KEYWORDS above (matched anywhere), these are matched only
# at statement start, because several are ordinary words (``start``,
# ``stop``, ``change``, ``release``, ``do``) and ``REPLACE`` is a string
# function, so a bare ``\b`` anywhere-match would reject benign reads like
# ``SELECT start FROM t`` or ``SELECT REPLACE(col, 'a', 'b')``. Anchoring to
# statement start avoids that while still blocking the verb form.
STATEMENT_START_MUTATING_KEYWORDS = {
    # DML / expression execution
    'IMPORT',  # IMPORT TABLE — bulk import from .ibd files
    # Any statement-leading REPLACE (REPLACE ... SET / REPLACE ... VALUES).
    # REPLACE INTO is also in MUTATING_KEYWORDS; both firing on
    # ``REPLACE INTO ...`` is harmless (deduped by the caller).
    'REPLACE',
    'DO',  # DO expr — runs expressions / side-effecting stored functions
    # Transaction control
    'START',  # START TRANSACTION / START REPLICA / START GROUP_REPLICATION
    'BEGIN',  # alias for START TRANSACTION
    'COMMIT',  # makes pending mutations durable
    'ROLLBACK',  # ROLLBACK / ROLLBACK TO SAVEPOINT
    'SAVEPOINT',  # creates a named transaction savepoint
    'RELEASE',  # RELEASE SAVEPOINT
    'XA',  # XA START/END/PREPARE/COMMIT/ROLLBACK — distributed transactions
    # Replication management
    'CHANGE',  # CHANGE REPLICATION SOURCE TO / CHANGE REPLICATION FILTER
    'PURGE',  # PURGE BINARY LOGS — deletes binlog files from disk
    'STOP',  # STOP REPLICA / STOP GROUP_REPLICATION
    'BINLOG',  # BINLOG 'base64-event' — injects a raw binary log event
    # Server administration
    'CLONE',  # CLONE LOCAL / CLONE INSTANCE — copies the data directory
    'RESTART',  # restarts the server process
    'SHUTDOWN',  # terminates the server
    # Session / server state (no data mutation, but not a read). SET is
    # already blocked via MUTATING_KEYWORDS; USE is the session-state sibling.
    'USE',  # USE <db> — switches the session's default database
    'CACHE',  # CACHE INDEX ... IN ... — assigns table indexes to a key cache
    'LOAD INDEX',  # LOAD INDEX INTO CACHE ... — preloads indexes into a key cache
}

# Sorted for stable, hash-seed-independent output. Unlike MUTATING_PATTERN,
# ordering is not required for correctness here: no entry is a prefix of
# another and a statement has exactly one leading verb, so alternation order
# cannot change which keyword matches.
_STATEMENT_START_KEYWORDS_BY_LENGTH = sorted(
    STATEMENT_START_MUTATING_KEYWORDS, key=len, reverse=True
)
# Anchor to statement start: start of the (comment-stripped) SQL or right
# after a ``;``. No re.MULTILINE, so a mid-statement newline is not a new
# anchor. The single capturing group makes ``findall`` return the keyword.
#
# Known coupling: a ``;`` inside a string literal (string literals are not
# comment-stripped) also matches the ``;`` branch — e.g.
# ``WHERE note = 'do it; commit later'`` reports ``COMMIT``. This is a false
# positive in isolation, but such input is independently rejected by the
# stacked-queries entry in SUSPICIOUS_PATTERNS, so there is no live
# over-block; the "no false positive" property here relies on that rule
# staying at least as strict.
STATEMENT_START_MUTATING_PATTERN = re.compile(
    r'(?i)(?:^|;)\s*('
    + '|'.join(re.escape(k) for k in _STATEMENT_START_KEYWORDS_BY_LENGTH)
    + r')\b'
)

# Functions with server-side / session side effects that are dangerous in a
# read context regardless of how they are invoked — ``DO f()``, ``SELECT f()``,
# inside a WHERE clause, etc. Blocking the statement verb alone (e.g. ``DO``)
# is not enough because the read-shaped form ``SELECT GET_LOCK(...)`` calls the
# same function. These parallel the existing ``sleep()`` / ``benchmark()`` /
# ``load_file()`` entries and are rejected in BOTH read and write mode:
#
#   get_lock / release_lock / release_all_locks
#       Acquire/release server-wide advisory (named) locks — a side effect
#       that can stall other sessions. (Note: is_free_lock / is_used_lock are
#       read-only status probes and are deliberately NOT listed.)
#   master_pos_wait / source_pos_wait / wait_for_executed_gtid_set /
#   wait_until_sql_thread_after_gtids
#       Block the session until replication reaches a position — a stalling
#       side effect, same class as sleep().
#   sys_exec / sys_eval
#       sys-schema / UDF helpers that run OS commands / arbitrary code.
#
# Matching is anchored to a following ``(`` so a column or alias with the same
# name (e.g. ``SELECT get_lock FROM t``) is not flagged. ``LAST_INSERT_ID`` is
# handled by a separate pattern below because only its argument form has a
# side effect.
SIDE_EFFECTING_FUNCTIONS = {
    'get_lock',
    'release_lock',
    'release_all_locks',
    'master_pos_wait',
    'source_pos_wait',
    'wait_for_executed_gtid_set',
    'wait_until_sql_thread_after_gtids',
    'sys_exec',
    'sys_eval',
}

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
    # side-effecting functions (advisory locks, replication waits, code exec);
    # anchored to ``(`` so same-named identifiers are not matched
    r'(?i)\b(?:' + '|'.join(sorted(SIDE_EFFECTING_FUNCTIONS)) + r')\s*\(',
    # LAST_INSERT_ID(expr) sets the session value (side effect); the no-arg
    # read form LAST_INSERT_ID() is allowed
    r'(?i)\blast_insert_id\s*\(\s*[^)\s]',
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


def _strip_mysql_hash_comments(sql: str) -> str:
    r"""Remove MySQL ``#`` line comments while preserving string literals.

    sqlparse only strips the space-prefixed ``# `` form, leaving the no-space
    ``#x`` form intact (which would let a ``#x\n`` prefix hide a
    statement-leading verb, e.g. ``#x\nDO GET_LOCK(...)``). A blind
    ``#[^\n]*`` strip is NOT safe: a ``#`` inside a ``'...'`` / ``"..."``
    string literal or a ``` `...` ``` identifier is data, not a comment
    (``'#sale'``, ``'#ffffff'``), and stripping to end-of-line there would
    delete trailing real SQL — hiding a mutation such as
    ``WHERE c = '#foo'; DROP TABLE t``.

    This scanner therefore strips ``#...EOL`` only when the ``#`` is outside
    any quoted region. Quote tracking honours MySQL's default escaping:
    backslash escapes inside ``'...'`` / ``"..."`` (the server does not set
    NO_BACKSLASH_ESCAPES) and doubled-quote escapes (``''``, ``""``,
    ``` `` ```). ``--`` and ``/* */`` are already removed by sqlparse before
    this runs.
    """
    out: list[str] = []
    i, n = 0, len(sql)
    quote: str | None = None
    while i < n:
        ch = sql[i]
        if quote is not None:
            out.append(ch)
            # Backslash escape (not inside backtick identifiers): the next
            # char is part of the string, never a closing quote.
            if ch == '\\' and quote != '`' and i + 1 < n:
                out.append(sql[i + 1])
                i += 2
                continue
            if ch == quote:
                # A doubled quote is an escaped quote, still inside the string.
                if i + 1 < n and sql[i + 1] == quote:
                    out.append(sql[i + 1])
                    i += 2
                    continue
                quote = None
            i += 1
            continue
        if ch in ("'", '"', '`'):
            quote = ch
            out.append(ch)
            i += 1
            continue
        if ch == '#':
            # Comment to end of line; drop up to (but not including) the
            # newline so a mutation on a later line is still scanned.
            while i < n and sql[i] != '\n':
                i += 1
            continue
        out.append(ch)
        i += 1
    return ''.join(out)


def _strip_comments_for_scan(sql: str) -> str:
    """Normalise SQL for keyword/pattern scanning by removing comments.

    ``sqlparse.format(strip_comments=True)`` removes ``-- ...``, ``/* ... */``
    and the space-prefixed ``# ...`` form while respecting string literals.
    It does NOT remove the no-space MySQL ``#`` line comment, so a
    string-literal-aware pass (see ``_strip_mysql_hash_comments``) removes any
    residual ``#`` comment without touching ``#`` characters inside string
    literals or identifiers.
    """
    stripped = sqlparse.format(sql, strip_comments=True)
    return _strip_mysql_hash_comments(stripped)


def detect_mutating_keywords(sql_text: str) -> list[str]:
    r"""Return a list of mutating keywords found in the SQL (excluding comments).

    SQL inline comments (`/* ... */`, `-- ...`, `# ...`) are treated as
    whitespace by the database parser but as opaque characters by Python
    regex. To prevent bypasses such as `LOAD/**/DATA INFILE ...`, the SQL
    is normalised by `_strip_comments_for_scan` before the keyword scan so
    a comment between adjacent keywords no longer hides the multi-word
    match (e.g. `LOAD DATA`, `RENAME TABLE`). That helper also removes the
    no-space MySQL `#` line comment (`#x\n...`), which sqlparse leaves in
    place and which would otherwise hide a statement-leading verb from the
    anchored scan (e.g. `#x\nDO GET_LOCK(...)`).

    MySQL conditional comments (`/*!50000 ... */`) are handled separately:
    sqlparse strips them entirely, so a payload like
    ``/*!50000 DELETE FROM users */`` would otherwise have its body
    stripped before the regex runs and the function would return ``[]``.
    Any presence of the ``/*!`` marker is therefore treated as a mutation
    in its own right (MySQL 5.0+ executes the body server-side, so the
    conservative answer for a readonly gate is "yes, this mutates").
    A non-keyword sentinel is returned so callers' ``bool(matches)``
    checks fire without misreporting a specific keyword.

    Two scans run against the comment-stripped SQL: ``MUTATING_PATTERN``
    (keywords anywhere) and ``STATEMENT_START_MUTATING_PATTERN`` (verbs that
    are also common identifiers, matched only at statement start).
    """
    if re.search(MYSQL_CONDITIONAL_COMMENT_PATTERN, sql_text):
        # Defence in depth: keep this function correct in isolation, even
        # when callers do not also invoke check_sql_injection_risk.
        return ['MYSQL_CONDITIONAL_COMMENT']
    sql_for_check = _strip_comments_for_scan(sql_text)
    matches = MUTATING_PATTERN.findall(sql_for_check)
    matches += STATEMENT_START_MUTATING_PATTERN.findall(sql_for_check)
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

    # Stage 2: strip ordinary comments (including no-space MySQL ``#``),
    # then run the regex sweep.
    sql_for_check = _strip_comments_for_scan(sql)

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
