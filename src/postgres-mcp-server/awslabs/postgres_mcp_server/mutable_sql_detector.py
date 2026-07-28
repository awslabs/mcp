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


MUTATING_KEYWORDS = {
    # DML
    'INSERT',
    'UPDATE',
    'DELETE',
    'MERGE',
    'TRUNCATE',
    'COPY',
    'LISTEN',
    'LOCK',
    'NOTIFY',
    'REFRESH',
    'PREPARE',
    # DDL
    'CREATE',
    'DROP',
    'ALTER',
    'RENAME',
    'IMPORT FOREIGN SCHEMA',
    # Permissions
    'GRANT',
    'REVOKE',
    # Metadata changes
    'COMMENT ON',
    'SECURITY LABEL',
    # Extensions and functions
    'CREATE EXTENSION',
    'CREATE FUNCTION',
    'INSTALL',
    'CALL',
    'EXECUTE',
    # Storage-level
    'CLUSTER',
    'REINDEX',
    'VACUUM',
    'ANALYZE',
    # Session-state mutation. SET alters GUCs for subsequent queries on
    # the same connection; RESET / DISCARD undo prior session hardening
    # and can re-enable behaviours an operator disabled. LOAD pulls a
    # shared library into the backend — RDS restricts which libraries
    # can load, but blocking the keyword keeps the contract explicit.
    'SET',
    'RESET',
    'DISCARD',
    'LOAD',
    # set_config(name, value, is_local) is the function form of SET and
    # mutates session state the same way, but the SET keyword above does
    # not match it ('set' is not on a word boundary in 'set_config').
    # List it here so it is blocked in read-only mode exactly like SET.
    # In write mode it is allowed for ordinary GUCs, except the two
    # security-critical settings which SECURITY_SET_CONFIG_PATTERN
    # rejects in both modes (see below). Stored uppercase to match the
    # other entries; matching is case-insensitive regardless.
    'SET_CONFIG',
    # Anonymous code execution. DO $$ ... $$ runs PL/pgSQL inside the
    # connection. Even under BEGIN READ ONLY the block's procedural
    # body still executes — pg_sleep loops, RAISE for side-channels,
    # PERFORM SECURITY DEFINER functions, etc. — so we reject it
    # whenever readonly_query is on.
    'DO',
}

# Compile regex pattern. Sort by length descending so multi-word
# keywords win over their single-word prefixes — otherwise 'CREATE
# EXTENSION' could match only 'CREATE' (and which one wins would depend
# on set iteration order, making detect_mutating_keywords
# non-deterministic across runs). The query is blocked either way, but
# sorting makes the reported keyword accurate and stable.
MUTATING_PATTERN = re.compile(
    r'(?i)\b('
    + '|'.join(re.escape(k) for k in sorted(MUTATING_KEYWORDS, key=len, reverse=True))
    + r')\b'
)

# A string literal immediately followed by a -- comment is a classic
# injection-truncation shape. This one heuristic is evaluated against the
# RAW SQL as well as the normalized text, because the comment normalizer
# folds away a genuine trailing -- (turning it into whitespace) — so the
# raw pass is what preserves the signal. The other patterns below run on
# the normalized text only, so keywords / semicolons that appear *inside*
# a comment are not mistaken for real ones.
COMMENT_INJECTION_PATTERN = r"(?i)'.*?--"

SUSPICIOUS_PATTERNS = [
    COMMENT_INJECTION_PATTERN,  # comment injection: a string followed by --
    r'(?i)\bor\b\s+\d+\s*=\s*\d+',  # numeric tautology e.g. OR 1=1
    r"(?i)\bor\b\s*'[^']+'\s*=\s*'[^']+'",  # string tautology e.g. OR '1'='1'
    r'(?i)\bunion\b.*\bselect\b',  # UNION SELECT
    r'(?i)\bdrop\b',  # DROP statement
    r'(?i)\btruncate\b',  # TRUNCATE
    r'(?i)\bgrant\b|\brevoke\b',  # GRANT or REVOKE
    r';\s*(?!($|\s*--|\s*/\*))(?=\S)',  # stacked queries, excluding semicolons followed by comments or whitespace
    r'(?i)\bsleep\s*\(',  # delay-based probes
    r'(?i)\bpg_sleep\s*\(',
    r'(?i)\bload_file\s*\(',
    r'(?i)\binto\s+outfile\b',
]


# Postgres functions that are dangerous regardless of read/write mode.
# Each one has high blast radius and no plausible legitimate use from an
# LLM-issued read query, so we reject them unconditionally (independent
# of the readonly_query toggle). This is defence-in-depth — the primary
# control is operator role permissions: the MCP server should not run
# as rds_superuser. If it does, this list keeps the worst footguns out
# of reach.
#
#   pg_cancel_backend / pg_terminate_backend
#       Kill or cancel other database sessions on the same cluster.
#       Direct DoS against any colocated workload.
#   pg_sleep / pg_sleep_for / pg_sleep_until
#       Hold a connection open. Looped or fan-out via DO blocks (also
#       blocked) becomes a connection-pool exhaustion attack.
#   pg_read_file / pg_read_binary_file / pg_ls_dir / pg_stat_file
#       Filesystem read primitives. On managed Postgres these are
#       usually scoped to log dirs but exposure should still be opt-in.
#   lo_import / lo_export
#       Read/write the host filesystem via large-object machinery.
#   pg_reload_conf / pg_rotate_logfile
#       Server-wide configuration / log control.
#   pg_advisory_lock family (8 functions)
#       Application-level coordination primitives. Frameworks like
#       Flyway and Liquibase use these to serialize DDL migrations;
#       homegrown job queues use them for leader election. An LLM that
#       acquires a competing lock holds it for the rest of the session
#       (or transaction, for the _xact_ variants), blocking legitimate
#       callers and DoS-ing the application. Pool reuse makes this
#       worse: a session-scope lock outlives the query that took it.
#   pg_notify
#       Sends a NOTIFY on a channel. Combined with LISTEN (already
#       blocked as a mutating keyword) this is a side-channel for
#       coordinating outside the MCP. Low-utility for read queries.
#   dblink family (dblink, dblink_connect, dblink_connect_u,
#   dblink_exec, dblink_send_query, dblink_open, dblink_fetch,
#   dblink_close, dblink_get_connections)
#       Open outbound TCP connections from the database backend to an
#       arbitrary host:port. This is a Server-Side Request Forgery
#       primitive: a read query can reach the instance
#       metadata service (169.254.169.254) to steal IAM credentials,
#       probe or connect to internal VPC services, or exfiltrate query
#       results to an attacker-controlled host. The extension is in
#       Aurora/RDS shared_preload_libraries and can be enabled with
#       CREATE EXTENSION dblink, so block the call sites unconditionally.
#       dblink_connect_u is the unprivileged-auth variant and is the
#       most dangerous of the set. None have a plausible use from an
#       LLM-issued read query.
DANGEROUS_FUNCTIONS = {
    'pg_cancel_backend',
    'pg_terminate_backend',
    'pg_sleep',
    'pg_sleep_for',
    'pg_sleep_until',
    'pg_read_file',
    'pg_read_binary_file',
    'pg_ls_dir',
    'pg_stat_file',
    'lo_import',
    'lo_export',
    'pg_reload_conf',
    'pg_rotate_logfile',
    # Advisory-lock family — see comment above.
    'pg_advisory_lock',
    'pg_advisory_lock_shared',
    'pg_advisory_xact_lock',
    'pg_advisory_xact_lock_shared',
    'pg_try_advisory_lock',
    'pg_try_advisory_lock_shared',
    'pg_try_advisory_xact_lock',
    'pg_try_advisory_xact_lock_shared',
    # NOTIFY-channel side-channel.
    'pg_notify',
    # dblink family — SSRF primitive. See comment above.
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

# Match the function name optionally preceded by a schema qualifier
# (pg_catalog.pg_terminate_backend(...)) and any whitespace before the
# opening paren. Word boundaries prevent matches on identifiers like
# my_pg_sleep_helper. Double-quoted spellings ("pg_sleep"(1)) are folded
# to their bare form by strip_quoted_identifiers() before this pattern
# runs (see check_sql_injection_risk), so the quoted and unquoted calls
# are detected identically.
#
# Sort alternation by length descending: regex alternation is
# left-to-right, so for prefix-overlapping names (pg_advisory_lock /
# pg_advisory_lock_shared) we must list the longer one first to make
# the longer match win. The trailing \s*\( already disambiguates in
# practice, but explicit ordering is a defence against future patterns
# where the disambiguator might not be enough.
DANGEROUS_FUNCTION_PATTERN = re.compile(
    r'(?i)(?:\b\w+\.)?\b('
    + '|'.join(re.escape(fn) for fn in sorted(DANGEROUS_FUNCTIONS, key=len, reverse=True))
    + r')\s*\('
)


# Session GUCs that disable security controls. Setting either of these
# silently changes what subsequent queries see/do on the connection:
#   row_security = off
#       Disables row-level security policy enforcement. If the MCP role
#       owns the table (or is superuser), subsequent SELECTs return
#       unfiltered rows, defeating RLS-based data access control.
#   session_replication_role = replica
#       Suppresses trigger firing — including audit-logging, validation,
#       and cascading security triggers — and alters RLS evaluation.
# These are rejected regardless of read/write mode. SET as a general
# keyword is already blocked in read-only mode via MUTATING_KEYWORDS;
# this check additionally blocks these two specific GUCs even when the
# server runs with writes enabled. The optional SESSION / LOCAL modifier
# and either assignment form (= or TO) are matched.
# Two syntaxes set a GUC and BOTH must be blocked:
#   1. The SET statement:        SET row_security = off
#   2. The set_config() function: SELECT set_config('row_security','off',false)
# set_config() is the function form of SET and reaches the same backend
# machinery, so blocking only the SET keyword leaves a bypass:
# a read query can call set_config('row_security','off',false) to defeat
# RLS-based multi-tenant isolation. SECURITY_GUC_PATTERN matches the SET
# form; SECURITY_SET_CONFIG_PATTERN matches the function form. Both run
# in check_sql_injection_risk so these two settings are rejected
# regardless of read/write mode.
#
# Note the division of labour for the function form:
#   - SECURITY_SET_CONFIG_PATTERN (here): rejects set_config targeting
#     row_security / session_replication_role in BOTH modes.
#   - 'set_config' in MUTATING_KEYWORDS: rejects set_config targeting
#     ANY GUC in read-only mode only.
# So a write-enabled server may still call set_config for ordinary GUCs
# (e.g. set_config('app.tenant_id', ...)) but never for the two
# security-critical ones.
SECURITY_SENSITIVE_GUCS = {
    'row_security',
    'session_replication_role',
}

SECURITY_GUC_PATTERN = re.compile(
    r'(?i)\bset\b\s+(?:(?:session|local)\s+)?('
    + '|'.join(re.escape(g) for g in SECURITY_SENSITIVE_GUCS)
    + r')\b'
)

# Function form: set_config('<guc>', '<value>', <is_local>). The GUC
# name is a string literal (single quotes in valid SQL; we also accept
# double quotes defensively). An optional schema qualifier
# (pg_catalog.set_config) and whitespace before the paren are tolerated,
# mirroring DANGEROUS_FUNCTION_PATTERN.
SECURITY_SET_CONFIG_PATTERN = re.compile(
    r'(?i)(?:\b\w+\.)?\bset_config\s*\(\s*[\'"]('
    + '|'.join(re.escape(g) for g in SECURITY_SENSITIVE_GUCS)
    + r')[\'"]'
)

# COPY ... TO PROGRAM / COPY ... FROM PROGRAM executes an arbitrary shell
# command on the database host (remote command execution). It
# requires the COPY privilege plus pg_execute_server_program (or
# superuser), but where those are held it is a direct RCE primitive —
# COPY t TO PROGRAM 'curl ...' or COPY t FROM PROGRAM 'whoami'. COPY is
# already a mutating keyword (rejected in read-only mode), but PROGRAM
# turns it into RCE that must be blocked even when writes are enabled, so
# it gets a mode-independent check here. The .* (DOTALL) spans the table
# list / column list / WITH options between COPY and the TO|FROM PROGRAM
# clause. Plain COPY ... TO '/file' (no PROGRAM) is not matched.
#
# Anchored at the start of the (comment-normalized) statement: COPY is
# only valid as the first token of a statement, so anchoring avoids
# flagging the literal text "COPY ... TO PROGRAM" when it appears inside
# a string value mid-query, without creating a bypass — a leading comment
# folds to whitespace and a stacked ';COPY ...' is already rejected by
# the stacked-query pattern.
COPY_PROGRAM_PATTERN = re.compile(r'(?is)^\s*copy\b.*\b(?:to|from)\s+program\b')


# PostgreSQL treats a double-quoted identifier the same as the bare name
# ("pg_sleep" is the function pg_sleep), but the detection regexes anchor
# on word boundaries and a name-then-paren adjacency that a closing quote
# breaks: "pg_sleep"(1) slips past DANGEROUS_FUNCTION_PATTERN and
# set_config("row_security",...) / SET "row_security" slip past the GUC
# patterns, defeating the whole blocklist. Fold the quotes off
# simple identifiers before matching so quoted and unquoted spellings are
# detected identically.
#
# The bare name is re-inserted PADDED WITH SPACES, not bare. A double
# quote is also a token separator in PostgreSQL, so SELECT"pg_sleep"(1)
# is a valid call (the " ends the SELECT token). Simply deleting the
# quotes would merge the neighbours into SELECTpg_sleep and destroy the
# word boundary the patterns rely on — re-introducing the very bypass we
# are closing. Surrounding the name with spaces preserves the token
# boundaries while still removing the quotes. Collapsing any resulting
# double spaces is unnecessary: every pattern tolerates \s*/\s+.
#
# Only \w+ identifiers are unwrapped — that covers every blocklisted
# function and GUC name (all plain ASCII words). The substitution is
# lexical, not a full SQL parse: a double-quoted word that happens to
# sit inside a single-quoted string literal is unwrapped too. That can
# only ever *remove* quote characters (and add spaces), so the worst
# case is a harmless over-block of a contrived literal — never a missed
# detection. An identifier that needs embedded quotes or non-word
# characters cannot spell a blocklisted name, so leaving those untouched
# is safe. This is detection-only normalization; the original SQL is
# what executes.
_QUOTED_IDENTIFIER_PATTERN = re.compile(r'"(\w+)"')


def strip_quoted_identifiers(sql: str) -> str:
    """Fold double-quoted identifiers to their bare, space-padded form.

    e.g. SELECT "pg_sleep"(1) -> SELECT  pg_sleep (1), and the no-space
    form SELECT"pg_sleep"(1) -> SELECT pg_sleep (1). Padding with spaces
    keeps the surrounding tokens from merging (a double quote is itself a
    token separator in PostgreSQL). Applied before the function / GUC /
    suspicious-pattern checks so a double-quoted spelling cannot bypass
    them. Not used for query execution.
    """
    return _QUOTED_IDENTIFIER_PATTERN.sub(r' \1 ', sql)


def strip_sql_comments(sql: str) -> str:
    """Replace SQL comments with a space, ignoring comment-like text in literals.

    PostgreSQL treats both ``/* ... */`` block comments (which nest) and
    ``-- ... <eol>`` line comments as whitespace, so ``INTO/**/OUTFILE``,
    ``pg_sleep/**/(1)`` and ``SET/**/row_security`` all execute normally
    while slipping past regexes that expect literal whitespace between
    tokens. Folding each comment to a single space — rather than
    deleting it — both restores the keyword adjacency the patterns expect
    and prevents neighbouring tokens from merging.

    The scan is literal-aware: a ``--`` or ``/*`` appearing inside a
    single-quoted string, a double-quoted identifier, or a dollar-quoted
    string ($tag$...$tag$) is preserved, so a comment marker that is
    really data is not mistaken for a comment. This is detection-only
    normalization; the original SQL is what executes.

    Known limitations (best-effort, see README security note): backslash
    escapes inside E'' strings and other exotic lexer corners are not
    modelled. True fidelity needs a real parser.
    """
    out = []
    i = 0
    n = len(sql)
    while i < n:
        ch = sql[i]

        # Single-quoted string literal: '' is an embedded quote.
        if ch == "'":
            out.append(ch)
            i += 1
            while i < n:
                out.append(sql[i])
                if sql[i] == "'":
                    if i + 1 < n and sql[i + 1] == "'":
                        out.append("'")
                        i += 2
                        continue
                    i += 1
                    break
                i += 1
            continue

        # Double-quoted identifier: "" is an embedded quote.
        if ch == '"':
            out.append(ch)
            i += 1
            while i < n:
                out.append(sql[i])
                if sql[i] == '"':
                    if i + 1 < n and sql[i + 1] == '"':
                        out.append('"')
                        i += 2
                        continue
                    i += 1
                    break
                i += 1
            continue

        # Dollar-quoted string: $tag$ ... $tag$ (tag may be empty: $$).
        if ch == '$':
            m = re.match(r'\$\w*\$', sql[i:])
            if m:
                tag = m.group(0)
                end = sql.find(tag, i + len(tag))
                if end == -1:
                    out.append(sql[i:])  # unterminated — copy verbatim
                    break
                out.append(sql[i : end + len(tag)])
                i = end + len(tag)
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

    Folds comments to whitespace then unwraps double-quoted identifiers,
    so that ``INTO/**/OUTFILE`` and ``"pg_sleep"(1)`` are seen by the
    patterns the same way ``INTO OUTFILE`` / ``pg_sleep(1)`` are. Used for
    detection only; never for execution.
    """
    return strip_quoted_identifiers(strip_sql_comments(sql))


def detect_mutating_keywords(sql_text: str) -> list[str]:
    """Return a list of mutating keywords found in the SQL.

    The SQL is comment-normalized first so a comment wedged between the
    words of a multi-word keyword (IMPORT/**/FOREIGN/**/SCHEMA) or before
    a function paren cannot hide the keyword from the read-only gate.
    """
    matches = MUTATING_PATTERN.findall(normalize_for_detection(sql_text))
    return list({m.upper() for m in matches})  # Deduplicated and normalized to uppercase


def check_sql_injection_risk(sql: str) -> list[dict]:
    """Check for potential SQL injection risks in sql query.

    Args:
        sql: query string

    Returns:
        dictionaries containing detected security issue
    """
    issues = []

    # Canonicalize first: fold comments to whitespace and unwrap
    # double-quoted identifiers. A quoted spelling like "pg_sleep"(1) or a
    # comment wedged between tokens (INTO/**/OUTFILE, SET/**/row_security,
    # pg_sleep/**/(1)) is semantically identical to the plain form in
    # PostgreSQL but otherwise slips past the word-boundary / adjacency
    # anchors below. All subsequent regex checks run on the
    # normalized text; the original sql is preserved for messages.
    normalized_sql = normalize_for_detection(sql)

    # COPY ... TO/FROM PROGRAM is server-side command execution.
    # COPY alone is gated in read-only mode as a mutating keyword, but the
    # PROGRAM form is RCE that must be rejected even with writes enabled.
    if COPY_PROGRAM_PATTERN.search(normalized_sql):
        issues.append(
            {
                'type': 'sql',
                'message': (
                    'COPY ... TO/FROM PROGRAM rejected: this executes an arbitrary '
                    'command on the database host (remote code execution) and is '
                    'blocked regardless of read/write mode.'
                ),
                'severity': 'high',
            }
        )
        return issues

    # Security-GUC check first — these disable RLS / triggers and are
    # rejected in both read and write mode. Named explicitly so the
    # operator sees which GUC was blocked rather than a generic message.
    guc_match = SECURITY_GUC_PATTERN.search(normalized_sql) or SECURITY_SET_CONFIG_PATTERN.search(
        normalized_sql
    )
    if guc_match:
        issues.append(
            {
                'type': 'sql',
                'message': (
                    f'Security-sensitive session setting rejected: {guc_match.group(1)}. '
                    'Changing this setting (via SET or set_config) disables a '
                    'data-access or integrity control (RLS / triggers) and is '
                    'blocked regardless of read/write mode.'
                ),
                'severity': 'high',
            }
        )
        return issues

    # Dangerous-function check next so the rejection reason names the
    # specific function instead of one of the generic suspicious
    # patterns (e.g. pg_sleep would otherwise hit the 'sleep(' pattern
    # with a vaguer message).
    fn_match = DANGEROUS_FUNCTION_PATTERN.search(normalized_sql)
    if fn_match:
        issues.append(
            {
                'type': 'sql',
                'message': (
                    f'Dangerous function call rejected: {fn_match.group(1)}. '
                    'This function has cluster-wide side effects (DoS, filesystem '
                    'access, server control) and is blocked regardless of read/write mode.'
                ),
                'severity': 'high',
            }
        )
        return issues

    # Suspicious-pattern heuristics run against the normalized text, so a
    # keyword or semicolon that appears only inside a comment (which the
    # normalizer has folded to whitespace) is not mistaken for a real one.
    # The comment-injection heuristic is the exception: a genuine trailing
    # -- is removed by normalization, so it is additionally tested against
    # the raw SQL.
    flagged = any(re.search(pattern, normalized_sql) for pattern in SUSPICIOUS_PATTERNS)
    flagged = flagged or bool(re.search(COMMENT_INJECTION_PATTERN, sql))
    if flagged:
        issues.append(
            {
                'type': 'sql',
                'message': f'Suspicious pattern in query: {sql}',
                'severity': 'high',
            }
        )
    return issues
