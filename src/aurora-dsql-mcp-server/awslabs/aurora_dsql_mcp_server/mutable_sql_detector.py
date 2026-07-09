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


# -- Mutating keyword set for quick string matching --
MUTATING_KEYWORDS = {
    'INSERT',
    'UPDATE',
    'DELETE',
    'REPLACE',
    'TRUNCATE',
    'CREATE',
    'DROP',
    'ALTER',
    'RENAME',
    'GRANT',
    'REVOKE',
    'LOAD DATA',
    'LOAD XML',
    'INSTALL PLUGIN',
    'UNINSTALL PLUGIN',
    'COPY',
    'MERGE',
    'UPSERT',
}

MUTATING_PATTERN = re.compile(
    r'(?i)\b(' + '|'.join(re.escape(k) for k in MUTATING_KEYWORDS) + r')\b'
)

# -- Regex for DDL statements --
DDL_REGEX = re.compile(
    r"""
    ^\s*(
        CREATE\s+(TABLE|VIEW|INDEX|TRIGGER|PROCEDURE|FUNCTION|EVENT|SCHEMA|DATABASE|ROLE|USER)|
        DROP\s+(TABLE|VIEW|INDEX|TRIGGER|PROCEDURE|FUNCTION|EVENT|SCHEMA|DATABASE|ROLE|USER)|
        ALTER\s+(TABLE|VIEW|TRIGGER|PROCEDURE|FUNCTION|EVENT|SCHEMA|DATABASE|ROLE|USER)|
        RENAME\s+(TABLE)|
        TRUNCATE
    )\b
    """,
    re.IGNORECASE | re.VERBOSE,
)

# -- Regex for permission-related statements --
PERMISSION_REGEX = re.compile(
    r"""
    ^\s*(
        GRANT(\s+ROLE)?|
        REVOKE(\s+ROLE)?|
        CREATE\s+(USER|ROLE)|
        DROP\s+(USER|ROLE)|
        SET\s+DEFAULT\s+ROLE|
        SET\s+PASSWORD|
        ALTER\s+USER|
        RENAME\s+USER
    )\b
    """,
    re.IGNORECASE | re.VERBOSE,
)

# -- Regex for system/control-level operations --
SYSTEM_REGEX = re.compile(
    r"""
    ^\s*(
        SET\s+(GLOBAL|PERSIST|SESSION)|
        RESET\s+(PERSIST|MASTER|SLAVE)|
        FLUSH\s+(PRIVILEGES|HOSTS|LOGS|STATUS|TABLES)?|
        INSTALL\s+PLUGIN|UNINSTALL\s+PLUGIN|
        CHANGE\s+MASTER\s+TO|
        START\s+SLAVE|STOP\s+SLAVE|
        SET\s+GTID_PURGED|
        PURGE\s+BINARY\s+LOGS|
        LOAD\s+DATA\s+INFILE|
        SELECT\s.*\bINTO\s+OUTFILE|
        USE\s+\w+|
        SET\s+autocommit|
        COPY\s.*\bFROM|
        COPY\s.*\bTO
    )\b
    """,
    re.IGNORECASE | re.VERBOSE,
)
# NOTE: the SELECT / COPY branches use ``\s.*\b<kw>`` rather than ``\s+.*\s+<kw>``.
# The nested ``\s+ .* \s+`` form is catastrophic-backtracking ReDoS: on a run of
# whitespace with no trailing keyword, the engine explores exponentially many ways
# to split the whitespace among the three quantifiers (~1.5 KB of spaces blocked the
# event loop for seconds). ``\s.*\b<kw>`` matches the same statements without the
# ambiguous whitespace partition.

# -- Regex for statement-level operations that mutate table / catalog / server state --
# These are ordinary PostgreSQL statements (not MySQL-flavored) that write or act on
# durable state and have no place in a read-only query. They are matched ANCHORED at
# statement start (``^\s*``) rather than as bare keywords, because several of the words
# also appear legitimately mid-query — most importantly ``ANALYZE`` in
# ``EXPLAIN ANALYZE ... SELECT`` (the DSQL query-plan workflow), and ``COMMENT`` /
# ``CLUSTER`` / ``REFRESH`` as column or table names. Anchoring blocks the statement
# form while leaving those reads untouched.
#
# Mirrors the postgres-mcp-server sibling's mutating-keyword set. Aurora DSQL rejects
# almost all of these at the engine today (FeatureNotSupported / ReadOnlySqlTransaction),
# so this is primarily forward-looking defense-in-depth: if a future DSQL release adds
# one of them, the read-only gate already refuses it. ``CALL`` and ``DO`` are the
# highest-value entries — both execute a procedure / anonymous PL/pgSQL body the
# read-only gate cannot see into.
STATEMENT_KEYWORD_REGEX = re.compile(
    r"""
    ^\s*(
        CALL|                         # invoke a stored procedure (opaque body)
        DO|                           # anonymous PL/pgSQL block (opaque body)
        VACUUM|ANALYZE|               # storage / statistics maintenance
        REINDEX|CLUSTER|              # index rebuild / physical reorder
        REFRESH|                      # REFRESH MATERIALIZED VIEW
        COMMENT\s+ON|                 # catalog metadata mutation
        SECURITY\s+LABEL|             # security-label mutation
        IMPORT\s+FOREIGN\s+SCHEMA|    # creates local objects
        LOAD|                         # load a shared library into the backend
        DISCARD                       # DISCARD ALL/PLANS/TEMP/SEQUENCES (session reset)
    )\b
    """,
    re.IGNORECASE | re.VERBOSE,
)

# Sequence-mutation functions: setval() changes a sequence's value (durable), nextval()
# advances it (side-effecting). Matched anywhere (like set_config) since they appear as
# subquery/projection calls. DSQL blocks them inside a read-only transaction today
# (ReadOnlySqlTransaction), so this is belt-and-suspenders.
SEQUENCE_FUNCTION_REGEX = re.compile(r'(?i)\b(?:setval|nextval)\s*\(')

# -- Regex for Postgres session-state (GUC) mutation --
# A `BEGIN TRANSACTION READ ONLY` only blocks writes to database TABLES; it does NOT
# block changes to session/GUC state. Statements like `SET search_path = ...`, its
# keyword-syntax variants (`SET ROLE`, `SET SCHEMA`, `SET NAMES`, ...), the session
# commands `RESET` / `DISCARD` / `LISTEN` / `NOTIFY` / `LOCK` / `EXECUTE`, and the
# function form `set_config(...)` all mutate or act on session/connection state and are
# permitted by Postgres inside a read-only transaction. They must be caught here to
# preserve read-only semantics.
#
# Matching strategy (mirrors the postgres-mcp-server sibling's keyword approach rather
# than an assignment-shape regex):
#   - Statement-leading keywords are anchored with `^\s*`, so a keyword that merely
#     appears as string DATA (e.g. `... LIKE '%SET ROLE%'`) is NOT a statement and is
#     not matched. detect_mutating_keywords runs this regex on literal-BLANKED text
#     (the shared boundary helper models E'...' escapes and dollar-quotes correctly),
#     so a literal that merely mentions `set_config(` is blanked away and not matched.
#   - `SET` matches any target EXCEPT `SET TRANSACTION ...` (via the
#     `(?!TRANSACTION\b)` lookahead), the legitimate way to assert read-only mode /
#     isolation (see test_session_mutation_no_false_positives). A `SET TRANSACTION
#     ... READ WRITE` escalation is NOT exempt — it has its own dedicated branch
#     above. `SET SESSION CHARACTERISTICS ...` is NOT exempt (only a literal
#     `SET TRANSACTION` lead is), so it is blocked; that is acceptable in read-only
#     mode. Note `SET SESSION <guc>` is still blocked — only the transaction-config lead
#     is conditionally exempt.
#   - `set_config(` is matched anywhere (not anchored) so it is caught even when embedded
#     as a subquery, e.g. `SELECT set_config('search_path', 'pg_temp', false)`.
#   - PREPARE / DECLARE (cursor) / DEALLOCATE act on session-scoped prepared
#     statements and cursors that a plain RESET ALL does not clear, so they are
#     blocked in read-only mode as well (defense-in-depth; DSQL rejects most today).
SESSION_MUTATION_REGEX = re.compile(
    r"""
    (
        \bset_config\s*\(                    # set_config(...) / pg_catalog.set_config(...), any position
      | ^\s*SET\s+TRANSACTION\b[\s\S]*?READ\s+WRITE\b   # SET TRANSACTION ... READ WRITE (escalation) — blocked (spans newlines)
      | ^\s*SET\s+(?!TRANSACTION\b)\S        # SET <anything> except `SET TRANSACTION ...`
      | ^\s*RESET\b                          # RESET <name> / RESET ALL
      | ^\s*DISCARD\b                        # DISCARD ALL / PLANS / TEMP / SEQUENCES
      | ^\s*(LISTEN|NOTIFY|UNLISTEN)\b       # async-notification channels (session state)
      | ^\s*LOCK\b                           # explicit table locks
      | ^\s*(PREPARE|DEALLOCATE)\b           # prepared statements (session-scoped, not cleared by RESET ALL)
      | ^\s*DECLARE\b[^\n]*\bCURSOR\b        # DECLARE ... CURSOR (esp. WITH HOLD — survives COMMIT)
      | ^\s*EXECUTE\b                        # run a prepared statement (opaque; may mutate)
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)

# -- Transaction control statements that could be used for SQL injection --
TRANSACTION_CONTROL_REGEX = re.compile(
    r"""
    ^\s*(
        BEGIN(\s+TRANSACTION)?(\s+READ\s+ONLY)?|
        COMMIT(\s+TRANSACTION)?|
        ROLLBACK(\s+TRANSACTION)?|
        SAVEPOINT|
        RELEASE\s+SAVEPOINT|
        START\s+TRANSACTION
    )\b
    """,
    re.IGNORECASE | re.VERBOSE,
)

# -- Suspicious pattern detection (SQL injection, stacked queries, etc.) --
# Each entry is (pattern, label). The label is surfaced back to callers via
# check_sql_injection_risk so operators can diagnose false positives without
# having to read server logs.
#
# Patterns are split into two tiers:
#   INJECTION_PATTERNS — shapes that indicate injection attempts and never
#       appear in legitimate single-statement SQL. Safe to check in both
#       read-only and write modes.
#   KEYWORD_PATTERNS — keyword-level checks that overlap with legitimate
#       DDL/DML (DROP, TRUNCATE, GRANT, COPY, UNION SELECT). Only checked
#       in read-only mode, where these operations are prohibited.
INJECTION_PATTERNS = [
    # NOTE: comment injection ('...'--) is handled by a dedicated linear per-line
    # scan in check_sql_injection_risk (not a regex here) to avoid O(n^2) ReDoS on
    # quote-heavy input. It is intentionally not in this list.
    (r'(?i)\bor\b\s+\d+\s*=\s*\d+', 'numeric_tautology'),
    (r"(?i)\bor\b\s*'[^']+'\s*=\s*'[^']+'", 'string_tautology'),
    (r';\s*(?!($|\s*--|\s*/\*))(?=\S)', 'stacked_query'),
    (r'(?i)\bsleep\s*\(', 'sleep_time_based'),
    # pg_sleep, pg_sleep_for, and pg_sleep_until all hold a backend
    # connection open. Aurora DSQL permits all three (unlike the wider
    # dangerous-function family, which it blocks at the engine), and a
    # looped / fanned-out call is a connection-exhaustion (DoS) vector,
    # so match every spelling. Blocked in both read and write mode.
    (r'(?i)\bpg_sleep(?:_for|_until)?\s*\(', 'pg_sleep_time_based'),
    (r'(?i)\bload_file\s*\(', 'load_file'),
    (r'(?i)\binto\s+outfile\b', 'into_outfile'),
    # A transaction-control keyword followed by a stacked statement. Anchored at
    # statement start and bounded to a single line (``[^\n]*``) to avoid the
    # O(n^2) backtracking of the old ``\b(begin|commit|rollback)\b.*;\s*\w+`` on
    # inputs with many such keywords. The general stacked-query pattern below
    # already catches multi-statement SQL; this names the transaction-control case.
    (
        r'(?i)^\s*(begin|commit|rollback)\b[^\n]*;\s*\w+',
        'transaction_control_with_extra_statement',
    ),
]

KEYWORD_PATTERNS = [
    # NOTE: union_select is handled by a dedicated two-substring presence check in
    # check_sql_injection_risk (not a regex here): the old ``\bunion\b.*\bselect\b``
    # is O(n^2) on ``union``-heavy input (the greedy ``.*`` restarts at every
    # ``union``). It is intentionally not in this list.
    (r'(?i)\bdrop\b', 'drop'),
    (r'(?i)\btruncate\b', 'truncate'),
    (r'(?i)\bgrant\b|\brevoke\b', 'grant_revoke'),
    # COPY ... FROM / TO anchored at statement start (``^\s*copy``) and single-line
    # (``[^\n]*``) — the old ``\bcopy\s+.*\s+from`` was O(n^2) on ``copy``-heavy
    # input. A real COPY statement always leads its statement; a literal mentioning
    # "copy ... from" is blanked before this scan.
    (r'(?i)^\s*copy\b[^\n]*\bfrom\b', 'copy_from'),
    (r'(?i)^\s*copy\b[^\n]*\bto\b', 'copy_to'),
]

SUSPICIOUS_PATTERNS = INJECTION_PATTERNS + KEYWORD_PATTERNS

# Labels of the keyword-tier patterns (DROP, TRUNCATE, GRANT, UNION SELECT, COPY).
# These match bare keywords, so they run against literal-blanked text; the label set
# is derived once at import (not rebuilt per call) so check_sql_injection_risk can
# route each pattern to the right target text.
KEYWORD_LABELS = frozenset(label for _, label in KEYWORD_PATTERNS)

# Standalone-keyword presence checks used by the linear union_select heuristic
# (see check_sql_injection_risk) — two O(n) substring searches instead of the
# O(n^2) ``\bunion\b.*\bselect\b`` regex.
_UNION_RE = re.compile(r'(?i)\bunion\b')
_SELECT_RE = re.compile(r'(?i)\bselect\b')

# Statement-separating semicolon (a `;` followed by more SQL, not just a trailing
# comment/whitespace). Linear; used by detect_transaction_bypass_attempt to catch
# stacked statements. Same shape as the 'stacked_query' INJECTION_PATTERN.
_STACKED_STATEMENT_RE = re.compile(r';\s*(?!($|\s*--|\s*/\*))(?=\S)')


# -- Postgres functions that are dangerous regardless of read/write mode --
# Each has high blast radius and no plausible legitimate use from an
# LLM-issued read query, so they are rejected unconditionally.
#
# NOTE ON AURORA DSQL: DSQL currently blocks MOST of these at the engine
# level — dblink, pg_read_file, advisory locks, pg_cancel/terminate_backend,
# etc. fail with FeatureNotSupported / InsufficientPrivilege before this
# check would matter. They are listed here anyway as forward-looking
# defense-in-depth: DSQL is actively gaining Postgres compatibility, and if
# a future release enables one of these the MCP read-only gate should
# already block it rather than silently opening a hole. This also keeps the
# detector consistent with the postgres-mcp-server sibling.
#
# The one family DSQL DOES currently allow is pg_sleep / pg_sleep_for /
# pg_sleep_until (connection-hold / DoS) — those are matched by the
# 'pg_sleep_time_based' entry in INJECTION_PATTERNS above, not here.
#
#   pg_cancel_backend / pg_terminate_backend — kill/cancel other sessions (DoS).
#   pg_read_file / pg_read_binary_file / pg_ls_dir / pg_stat_file — filesystem read.
#   lo_import / lo_export — read/write host filesystem via large objects.
#   pg_reload_conf / pg_rotate_logfile — server-wide config / log control.
#   pg_advisory_lock family — session/xact locks that outlive a query on a
#       pooled connection and can DoS an application that relies on them.
#   pg_notify — NOTIFY-channel side-channel (pairs with LISTEN).
#   dblink family — outbound TCP from the backend: an SSRF primitive (can
#       reach 169.254.169.254 for IAM creds, probe internal VPC services,
#       or exfiltrate results). dblink_connect_u is the most dangerous.
DANGEROUS_FUNCTIONS = {
    'pg_cancel_backend',
    'pg_terminate_backend',
    'pg_read_file',
    'pg_read_binary_file',
    'pg_ls_dir',
    'pg_stat_file',
    'lo_import',
    'lo_export',
    'pg_reload_conf',
    'pg_rotate_logfile',
    'pg_advisory_lock',
    'pg_advisory_lock_shared',
    'pg_advisory_xact_lock',
    'pg_advisory_xact_lock_shared',
    'pg_try_advisory_lock',
    'pg_try_advisory_lock_shared',
    'pg_try_advisory_xact_lock',
    'pg_try_advisory_xact_lock_shared',
    'pg_advisory_unlock',
    'pg_advisory_unlock_shared',
    'pg_advisory_unlock_all',
    'pg_notify',
    'dblink',
    'dblink_connect',
    'dblink_connect_u',
    'dblink_exec',
    'dblink_send_query',
    'dblink_open',
    'dblink_fetch',
    'dblink_close',
    'dblink_get_connections',
}

# Match the function name, optionally schema-qualified
# (pg_catalog.pg_terminate_backend(...)), with any whitespace before the
# opening paren. Word boundaries prevent matches on identifiers like
# my_pg_sleep_helper. Alternation is sorted longest-first so prefix-
# overlapping names (pg_advisory_lock / pg_advisory_lock_shared) report the
# longer, more specific match.
DANGEROUS_FUNCTION_PATTERN = re.compile(
    r'(?i)(?:\b\w+\.)?\b('
    + '|'.join(re.escape(fn) for fn in sorted(DANGEROUS_FUNCTIONS, key=len, reverse=True))
    + r')\s*\('
)

# -- Session GUCs that disable security controls --
# Setting either silently changes what subsequent queries see/do on the
# connection, so they are rejected in BOTH read and write mode:
#   row_security = off — disables row-level security policy enforcement.
#   session_replication_role = replica — suppresses trigger firing (audit,
#       validation, cascading) and alters RLS evaluation.
# DSQL currently rejects both at the engine (FeatureNotSupported); listed
# here as forward-looking defense-in-depth, mirroring the postgres sibling.
# Two syntaxes set a GUC and BOTH are matched: the `SET <guc> = ...`
# statement (SECURITY_GUC_PATTERN) and the `set_config('<guc>', ...)`
# function form (SECURITY_SET_CONFIG_PATTERN).
SECURITY_SENSITIVE_GUCS = {
    'row_security',
    'session_replication_role',
}

SECURITY_GUC_PATTERN = re.compile(
    r'(?i)\bset\b\s+(?:(?:session|local)\s+)?('
    + '|'.join(re.escape(g) for g in SECURITY_SENSITIVE_GUCS)
    + r')\b'
)

SECURITY_SET_CONFIG_PATTERN = re.compile(
    r'(?i)(?:\b\w+\.)?\bset_config\s*\(\s*[\'"]('
    + '|'.join(re.escape(g) for g in SECURITY_SENSITIVE_GUCS)
    + r')[\'"]'
)

# COPY ... TO/FROM PROGRAM executes an arbitrary shell command on the
# database host (RCE). DSQL currently rejects it (FeatureNotSupported);
# matched here as defense-in-depth and blocked regardless of read/write
# mode. The .* (DOTALL) spans the table/column list and WITH options.
# Anchored at statement start: COPY is only valid as the first token, so
# anchoring avoids flagging the literal text inside a string value.
COPY_PROGRAM_PATTERN = re.compile(r'(?is)^\s*copy\b.*\b(?:to|from)\s+program\b')


_QUOTED_IDENTIFIER_PATTERN = re.compile(r'"(\w+)"')

# Opening tag of a dollar-quoted string ($tag$, tag may be empty: $$). Compiled once
# and matched with .match(sql, pos) so the lexer never slices sql[i:] (which would
# copy an O(n) tail on every `$` and make a `$`-heavy string O(n^2)).
_DOLLAR_TAG_RE = re.compile(r'\$\w*\$')


def strip_quoted_identifiers(sql: str) -> str:
    """Fold double-quoted identifiers to their bare, space-padded form.

    e.g. SELECT "pg_sleep"(1) -> SELECT  pg_sleep (1), and the no-space
    form SELECT"set_config"(...) -> SELECT set_config (...). PostgreSQL
    treats a double-quoted identifier the same as the bare name, but the
    detection regexes anchor on word boundaries and a name-then-paren
    adjacency that a closing quote breaks. Padding with spaces (rather than
    deleting the quotes) keeps neighbouring tokens from merging, since a
    double quote is itself a token separator. Detection-only; the original
    SQL is what executes.
    """
    return _QUOTED_IDENTIFIER_PATTERN.sub(r' \1 ', sql)


def _is_escape_string_open(sql: str, quote_idx: int) -> bool:
    r"""Return True if the single quote at ``quote_idx`` opens a PostgreSQL E'...' string.

    In an escape string (``E'...'`` / ``e'...'``) a backslash is special: ``\'`` is
    an escaped quote and ``\\`` an escaped backslash. In an ordinary string
    (``standard_conforming_strings = on``, the default) backslashes are literal and
    only ``''`` escapes a quote. The literal-boundary scanner must know which rule
    applies, so this detects the ``E`` / ``e`` prefix immediately before the opening
    quote, requiring it to be its own token (not the tail of an identifier like
    ``value``).
    """
    if quote_idx == 0:
        return False
    prev = sql[quote_idx - 1]
    if prev not in ('E', 'e'):
        return False
    # The E/e must be a standalone token, not the last char of an identifier
    # (e.g. the 'e' in "true'" must not be read as an escape-string prefix).
    return quote_idx - 1 == 0 or not (sql[quote_idx - 2].isalnum() or sql[quote_idx - 2] == '_')


def _end_of_single_quote(sql: str, i: int) -> int:
    r"""Return the index just past the closing quote of the single-quoted literal at ``i``.

    ``sql[i]`` must be the opening ``'``. Handles the ``''`` doubled-quote escape
    (all strings) and, for ``E'...'`` escape strings, the ``\'`` / ``\\`` backslash
    escapes so the literal terminates exactly where PostgreSQL terminates it. Returns
    ``len(sql)`` for an unterminated literal. Correct boundaries are essential: a
    scanner that mis-detects the close (e.g. reading ``E'\''`` as still-open) would
    swallow the rest of the statement and hide a following dangerous call from the
    detectors.
    """
    n = len(sql)
    escape = _is_escape_string_open(sql, i)
    i += 1  # move past the opening quote
    while i < n:
        ch = sql[i]
        if escape and ch == '\\' and i + 1 < n:
            i += 2  # backslash-escaped char stays inside the E'...' literal
            continue
        if ch == "'":
            if i + 1 < n and sql[i + 1] == "'":
                i += 2  # doubled-quote escape stays inside the literal
                continue
            return i + 1  # index just past the closing quote
        i += 1
    return n  # unterminated literal


def _end_of_dollar_quote(sql: str, i: int) -> int | None:
    """Return the index just past a dollar-quoted string at ``i``, or ``None`` if not one.

    ``$tag$ ... $tag$`` (tag may be empty: ``$$``). Backslashes and quotes inside a
    dollar-quoted body are literal — only the matching closing ``$tag$`` ends it.
    Returns ``len(sql)`` if the opening tag is present but never closed, or ``None``
    if ``sql[i]`` does not begin a dollar-quote tag.
    """
    m = _DOLLAR_TAG_RE.match(sql, i)
    if not m:
        return None
    tag = m.group(0)
    end = sql.find(tag, i + len(tag))
    if end == -1:
        return len(sql)  # unterminated
    return end + len(tag)


def _end_of_double_quote(sql: str, i: int) -> int:
    """Return the index just past the closing quote of the double-quoted identifier at ``i``.

    ``sql[i]`` must be the opening ``"``. Handles the ``""`` doubled-quote escape
    inside a quoted identifier. Returns ``len(sql)`` for an unterminated identifier.
    A single quote (``'``) inside a ``"..."`` identifier is literal data, not the
    start of a string literal — every literal-aware scanner must skip the whole
    identifier so an apostrophe in a column alias (``"o'clock"``) cannot be misread
    as opening a string and swallow the rest of the statement.
    """
    n = len(sql)
    i += 1  # move past the opening double quote
    while i < n:
        if sql[i] == '"':
            if i + 1 < n and sql[i + 1] == '"':
                i += 2  # doubled-quote escape stays inside the identifier
                continue
            return i + 1
        i += 1
    return n  # unterminated


def strip_sql_comments(sql: str) -> str:
    """Replace SQL comments with a space, ignoring comment-like text in literals.

    PostgreSQL treats both ``/* ... */`` block comments (which nest) and
    ``-- ... <eol>`` line comments as whitespace, so ``SET/**/search_path``,
    ``pg_sleep/**/(1)`` and ``set_config/**/(...)`` execute normally while
    slipping past regexes that expect literal whitespace between tokens.
    Folding each comment to a single space restores the keyword adjacency
    the patterns expect and prevents neighbouring tokens from merging.

    The scan is literal-aware: a ``--`` or ``/*`` inside a single-quoted
    string, a double-quoted identifier, or a dollar-quoted string
    ($tag$...$tag$) is preserved, so a comment marker that is really data is
    not mistaken for a comment. This also fixes the raw-text false positives
    where a mutating keyword inside a string literal (``SELECT 'INSERT INTO'``)
    was wrongly rejected. Detection-only; the original SQL is what executes.

    Why hand-rolled instead of ``sqlparse.format(strip_comments=True)``:
    ``sqlparse`` is a non-validating tokenizer, not a Postgres lexer. It does
    not fold nested block comments (``/* /* */ */``), does not model
    dollar-quoted strings, and — critically for us — strips comments WITHOUT
    knowing they sit inside a string literal, so it would corrupt a literal
    like ``'a -- b'`` and could change which text the detector sees versus
    what the database executes. Its stripped output also still contains the
    literals, so it does not address the keyword-in-literal false positives.
    Matching what actually executes requires literal- and dollar-quote-aware
    handling regardless, so a small self-contained scanner (mirroring the
    postgres-mcp-server sibling) is both more correct here and one fewer
    third-party dependency to track — sqlparse is intentionally NOT used.

    Literal boundaries (single-quote incl. ``E'...'`` backslash escapes, double-quote,
    dollar-quote) are located by the shared ``_end_of_single_quote`` /
    ``_end_of_double_quote`` / ``_end_of_dollar_quote`` helpers so this function and
    ``blank_string_literals`` cannot drift in how they detect where a literal ends.
    """
    out = []
    i = 0
    n = len(sql)
    while i < n:
        ch = sql[i]

        # Single-quoted string literal (incl. E'...' escape strings): copy verbatim.
        if ch == "'":
            end = _end_of_single_quote(sql, i)
            out.append(sql[i:end])
            i = end
            continue

        # Double-quoted identifier ("" is an embedded quote): copy verbatim.
        if ch == '"':
            end = _end_of_double_quote(sql, i)
            out.append(sql[i:end])
            i = end
            continue

        # Dollar-quoted string: $tag$ ... $tag$ (tag may be empty: $$).
        if ch == '$':
            end = _end_of_dollar_quote(sql, i)
            if end is not None:
                out.append(sql[i:end])
                i = end
                continue

        # Line comment: -- to end of line.
        if ch == '-' and i + 1 < n and sql[i + 1] == '-':
            nl = sql.find('\n', i)
            out.append(' ')
            i = n if nl == -1 else nl
            continue

        # Block comment: /* ... */ with nesting.
        if ch == '/' and i + 1 < n and sql[i + 1] == '*':
            depth = 1
            i += 2
            while i < n and depth > 0:
                if sql[i] == '/' and i + 1 < n and sql[i + 1] == '*':
                    depth += 1
                    i += 2
                elif sql[i] == '*' and i + 1 < n and sql[i + 1] == '/':
                    depth -= 1
                    i += 2
                else:
                    i += 1
            out.append(' ')
            continue

        out.append(ch)
        i += 1

    return ''.join(out)


def normalize_for_detection(sql: str) -> str:
    """Canonicalize SQL for the regex detectors.

    Folds comments to whitespace then unwraps double-quoted identifiers, so
    that ``SET/**/search_path`` and ``"set_config"(...)`` are seen by the
    patterns the same way ``SET search_path`` / ``set_config(...)`` are.
    Detection only; never used for execution.
    """
    return strip_quoted_identifiers(strip_sql_comments(sql))


def blank_string_literals(sql: str) -> str:
    r"""Replace the CONTENTS of string literals with a space.

    A mutating keyword inside a string literal is data, never an executable
    statement (``SELECT 'INSERT INTO' AS action`` is a pure read), so the
    literal contents must not trip the mutating-keyword / bare-name scans.
    Blanking only the contents — keeping the surrounding quotes and the rest of
    the SQL — means real statements are unaffected (``INSERT INTO t VALUES ('x')``
    still matches INSERT because the INSERT is outside the literal).

    Injection heuristics keep literals intact because tautologies like
    ``OR '1'='1'`` live inside them. Blanking literal contents can only ever
    REMOVE keyword matches, so it cannot hide a real mutation — the executable
    SQL is always outside the quotes.

    Literal boundaries are located by the shared ``_end_of_single_quote`` /
    ``_end_of_double_quote`` / ``_end_of_dollar_quote`` helpers, so this handles
    the same cases ``strip_sql_comments`` does: doubled-quote escapes (``''``),
    ``E'...'`` backslash escapes, double-quoted identifiers, and dollar-quoted
    strings. Getting these boundaries right matters two ways: (1) a scanner that
    mis-read ``E'\''`` as still-open would swallow the rest of the statement and
    hide a following dangerous call; (2) a ``'`` inside a double-quoted identifier
    (``"o'clock"``) must NOT be treated as opening a string literal, or the same
    swallow happens. Single-quoted and dollar-quoted CONTENTS are blanked;
    double-quoted identifiers are copied verbatim (an identifier is not a string
    value, and its keyword-shaped names are handled by strip_quoted_identifiers
    upstream). Detection only; the original SQL is what executes.
    """
    out = []
    i = 0
    n = len(sql)
    while i < n:
        ch = sql[i]
        if ch == "'":
            end = _end_of_single_quote(sql, i)
            # Keep the opening quote, blank the contents, keep the closing quote
            # (if the literal was terminated). Padding with a space preserves the
            # token boundary the surrounding patterns rely on.
            out.append("'")
            if sql[end - 1 : end] == "'" and end - 1 > i:
                out.append(' ')
                out.append("'")
            else:
                # Unterminated literal — emit a blank and stop.
                out.append(' ')
            i = end
            continue
        if ch == '"':
            # Double-quoted identifier: copy verbatim so an apostrophe inside it
            # is not misread as opening a string literal.
            end = _end_of_double_quote(sql, i)
            out.append(sql[i:end])
            i = end
            continue
        if ch == '$':
            end = _end_of_dollar_quote(sql, i)
            if end is not None:
                # Blank the dollar-quoted body but keep a token boundary.
                out.append(' ')
                i = end
                continue
        out.append(ch)
        i += 1
    return ''.join(out)


def detect_mutating_keywords(sql: str) -> list[str]:
    """Return a list of mutating keywords found in the SQL (excluding comments).

    The SQL is comment-normalized and quoted-identifier-unwrapped first, so a
    comment wedged between tokens (``SET/**/search_path``) or a double-quoted
    spelling (``"set_config"(...)``) cannot hide a keyword from the read-only
    gate, and a keyword that appears only inside a string literal
    (``SELECT 'INSERT INTO' AS x``) is not mistaken for a real one.
    """
    # Normalize comments and unwrap double-quoted identifiers, then blank string /
    # dollar-quoted literal CONTENTS. Every detector below runs on this blanked text:
    #   - The DDL / PERMISSION / SYSTEM / TRANSACTION_CONTROL / STATEMENT_KEYWORD
    #     regexes and the SET / RESET / ... branches of SESSION_MUTATION_REGEX are
    #     anchored at statement start (``^\s*``). Blanking only rewrites content
    #     INSIDE quotes and leaves the statement's leading tokens verbatim at index
    #     0, so anchoring still fires correctly (it does not rely on absolute
    #     positions elsewhere being preserved — normalization may shift them).
    #   - The un-anchored ``set_config(`` branch of SESSION_MUTATION_REGEX and the
    #     bare-keyword MUTATING_PATTERN scan WOULD otherwise match text that is merely
    #     string DATA (``SELECT 'set_config(' AS x``, ``SELECT 'INSERT INTO' AS x``).
    #     Blanking removes that data so it cannot produce a false positive.
    # Because the shared boundary helper models ``E'...'`` escapes and dollar-quotes,
    # a real call after an escape literal (``SELECT E'\'', set_config(...)``) is still
    # seen — blanking terminates the literal exactly where PostgreSQL does.
    blanked = blank_string_literals(normalize_for_detection(sql))
    matched = []

    if DDL_REGEX.search(blanked):
        matched.append('DDL')

    if PERMISSION_REGEX.search(blanked):
        matched.append('PERMISSION')

    if SYSTEM_REGEX.search(blanked):
        matched.append('SYSTEM')

    if SESSION_MUTATION_REGEX.search(blanked):
        matched.append('SESSION_MUTATION')

    if STATEMENT_KEYWORD_REGEX.search(blanked) or SEQUENCE_FUNCTION_REGEX.search(blanked):
        matched.append('STATEMENT_KEYWORD')

    if TRANSACTION_CONTROL_REGEX.search(blanked):
        matched.append('TRANSACTION_CONTROL')

    keyword_matches = MUTATING_PATTERN.findall(blanked)
    if keyword_matches:
        # Deduplicate and normalize casing
        matched.extend(sorted({k.upper() for k in keyword_matches}))

    return matched


def check_sql_injection_risk(sql: str, read_only: bool = True) -> list[dict]:
    """Check for potential SQL injection risks in sql query.

    Args:
        sql: query string
        read_only: when True (default), checks both injection-shape patterns
            and keyword-level patterns (DROP, TRUNCATE, etc.). When False,
            only checks injection-shape patterns — keyword-level patterns
            overlap with legitimate DDL/DML in write mode.

    Returns:
        A list containing at most one dictionary describing the first suspicious
        pattern that matched. Each dictionary has keys:
          - type: always 'sql'
          - label: a stable identifier for the matched pattern (e.g.
            'comment_injection', 'stacked_query', 'dangerous_function',
            'security_sensitive_guc', 'copy_program'). Callers can compare
            this against a known set without regex-parsing the message.
          - message: a human-readable summary (does not include the raw regex
            to avoid leaking filter internals to callers).
          - severity: always 'high'.
    """
    # Canonicalize first: fold comments to whitespace and unwrap double-quoted
    # identifiers. A quoted spelling ("pg_sleep"(1)) or a comment wedged
    # between tokens (pg_sleep/**/(1), SET/**/row_security) is semantically
    # identical to the plain form in PostgreSQL but otherwise slips past the
    # word-boundary / adjacency anchors below. All regex checks run on the
    # normalized text; the original sql is preserved for the raw comment pass.
    normalized_sql = normalize_for_detection(sql)

    # Bare-name patterns (a function/GUC name that could appear inside a string
    # literal as mere data) run against literal-blanked text so a query like
    # `... WHERE prosrc LIKE '%dblink(%'` or `... ILIKE '%SET row_security%'`
    # is not falsely rejected. Anchored / call-shaped patterns
    # (COPY_PROGRAM_PATTERN, SECURITY_SET_CONFIG_PATTERN) do not need this —
    # a literal cannot spell the anchored statement / set_config( call shape.
    blanked_sql = blank_string_literals(normalized_sql)

    # Mode-independent checks first (these are dangerous in BOTH read and
    # write mode) so the rejection names the specific reason.

    # COPY ... TO/FROM PROGRAM — server-side command execution (RCE).
    if COPY_PROGRAM_PATTERN.search(normalized_sql):
        return [
            {
                'type': 'sql',
                'label': 'copy_program',
                'message': 'Suspicious pattern detected: copy_program',
                'severity': 'high',
            }
        ]

    # Security-sensitive GUCs (row_security / session_replication_role) via
    # either the SET statement or the set_config() function form. The bare
    # `SET <guc>` form is checked on blanked text (the GUC name could be data);
    # the set_config('<guc>', ...) call shape cannot appear as a bare literal.
    if SECURITY_GUC_PATTERN.search(blanked_sql) or SECURITY_SET_CONFIG_PATTERN.search(
        normalized_sql
    ):
        return [
            {
                'type': 'sql',
                'label': 'security_sensitive_guc',
                'message': 'Suspicious pattern detected: security_sensitive_guc',
                'severity': 'high',
            }
        ]

    # High-blast-radius functions (DoS, filesystem, server control, SSRF).
    # Checked on blanked text so a function name quoted as data
    # (LIKE '%dblink(%') is not mistaken for a real call.
    if DANGEROUS_FUNCTION_PATTERN.search(blanked_sql):
        return [
            {
                'type': 'sql',
                'label': 'dangerous_function',
                'message': 'Suspicious pattern detected: dangerous_function',
                'severity': 'high',
            }
        ]

    # Keyword-level heuristics (DROP, TRUNCATE, GRANT, UNION SELECT, COPY) match
    # bare keywords, so they run against literal-blanked text (KEYWORD_LABELS,
    # derived once at import) — a keyword that is merely string data
    # (SELECT ... WHERE x LIKE '%DROP%') is not a real statement and must not be
    # flagged. Injection-shape patterns (tautologies, stacked queries)
    # intentionally keep literals intact because their signal lives inside the
    # quotes (OR '1'='1').
    # Comment-injection heuristic: a quote followed by a `--` comment ON THE SAME
    # LINE, tested against the RAW sql (normalization folds away the trailing `--`
    # this keys on). This reproduces the old ``'.*?--`` regex, which was compiled
    # WITHOUT re.DOTALL — so `.` never crossed a newline and it only matched a quote
    # and `--` on one line. It is done as a bounded per-line str.find scan rather
    # than that regex because ``'.*?--`` is O(n^2) on quote-heavy input (each quote
    # reopens the lazy ``.*?`` search), a CPU-exhaustion (ReDoS) vector. Walking the
    # string line by line (bounded finds, no split allocation) for "a quote, then a
    # `--` after it on the same line" is linear overall and preserves the
    # same-line semantics (so a string literal on one line and an ordinary SQL
    # line-comment on a later line is NOT falsely flagged). Runs in both modes,
    # mirroring the other mode-independent early-return checks above.
    line_start, sql_len = 0, len(sql)
    while line_start < sql_len:
        nl = sql.find('\n', line_start)
        line_end = sql_len if nl == -1 else nl
        quote_at = sql.find("'", line_start, line_end)
        if quote_at != -1 and sql.find('--', quote_at, line_end) != -1:
            return [
                {
                    'type': 'sql',
                    'label': 'comment_injection',
                    'message': 'Suspicious pattern detected: comment_injection',
                    'severity': 'high',
                }
            ]
        line_start = line_end + 1

    # UNION SELECT (keyword tier, read-only only): flag if both `union` and `select`
    # appear. Done as two independent substring presence checks rather than the old
    # ``\bunion\b.*\bselect\b`` regex, which is O(n^2) on ``union``-heavy input (the
    # greedy ``.*`` restarts the scan at every ``union``). Requiring both keywords
    # (in any order) is sufficient for a block decision and is linear. Runs on the
    # literal-blanked text so a keyword quoted as data is not flagged.
    if read_only and _UNION_RE.search(blanked_sql) and _SELECT_RE.search(blanked_sql):
        return [
            {
                'type': 'sql',
                'label': 'union_select',
                'message': 'Suspicious pattern detected: union_select',
                'severity': 'high',
            }
        ]

    patterns = SUSPICIOUS_PATTERNS if read_only else INJECTION_PATTERNS
    for pattern, label in patterns:
        # Keyword patterns use the literal-blanked text; all other
        # (injection-shape) patterns run on the normalized text so keywords /
        # semicolons inside a comment are not mistaken for real ones.
        target = blanked_sql if label in KEYWORD_LABELS else normalized_sql
        if re.search(pattern, target):
            return [
                {
                    'type': 'sql',
                    'label': label,
                    'message': f'Suspicious pattern detected: {label}',
                    'severity': 'high',
                }
            ]
    return []


def detect_transaction_bypass_attempt(sql: str) -> bool:
    """Detect attempts to bypass read-only transaction controls.

    This specifically looks for patterns that could be used to commit
    a read-only transaction and start a new writable transaction.

    Args:
        sql: query string

    Returns:
        True if a bypass attempt is detected, False otherwise
    """
    # Normalize first so a comment-split stacked query (COMMIT/**/;INSERT ...)
    # or a semicolon hidden inside a comment is evaluated on the same text the
    # database would execute.
    sql = normalize_for_detection(sql)

    # A COMMIT/ROLLBACK-then-more bypass always contains a statement-separating
    # semicolon, so the linear stacked-statement scan below fully covers it. (The
    # former dedicated ``\bcommit\b.*?;...`` regex was redundant with this scan and
    # O(n^2) on commit-heavy input — a ReDoS vector — so it was removed.)
    return bool(_STACKED_STATEMENT_RE.search(sql))
