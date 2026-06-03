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

SUSPICIOUS_PATTERNS = [
    r"(?i)'.*?--",  # comment injection
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
}

# Match the function name optionally preceded by a schema qualifier
# (pg_catalog.pg_terminate_backend(...)) and any whitespace before the
# opening paren. Word boundaries prevent matches on identifiers like
# my_pg_sleep_helper. Quoted identifiers ("pg_sleep") are NOT matched —
# this is a known limitation of regex-based detection.
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
SECURITY_SENSITIVE_GUCS = {
    'row_security',
    'session_replication_role',
}

SECURITY_GUC_PATTERN = re.compile(
    r'(?i)\bset\b\s+(?:(?:session|local)\s+)?('
    + '|'.join(re.escape(g) for g in SECURITY_SENSITIVE_GUCS)
    + r')\b'
)


def detect_mutating_keywords(sql_text: str) -> list[str]:
    """Return a list of mutating keywords found in the SQL (excluding comments)."""
    matches = MUTATING_PATTERN.findall(sql_text)
    return list({m.upper() for m in matches})  # Deduplicated and normalized to uppercase


def check_sql_injection_risk(sql: str) -> list[dict]:
    """Check for potential SQL injection risks in sql query.

    Args:
        sql: query string

    Returns:
        dictionaries containing detected security issue
    """
    issues = []

    # Security-GUC check first — these disable RLS / triggers and are
    # rejected in both read and write mode. Named explicitly so the
    # operator sees which GUC was blocked rather than a generic message.
    guc_match = SECURITY_GUC_PATTERN.search(sql)
    if guc_match:
        issues.append(
            {
                'type': 'sql',
                'message': (
                    f'Security-sensitive SET rejected: {guc_match.group(1)}. '
                    'Changing this session setting disables a data-access or '
                    'integrity control (RLS / triggers) and is blocked regardless '
                    'of read/write mode.'
                ),
                'severity': 'high',
            }
        )
        return issues

    # Dangerous-function check next so the rejection reason names the
    # specific function instead of one of the generic suspicious
    # patterns (e.g. pg_sleep would otherwise hit the 'sleep(' pattern
    # with a vaguer message).
    fn_match = DANGEROUS_FUNCTION_PATTERN.search(sql)
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

    for pattern in SUSPICIOUS_PATTERNS:
        if re.search(pattern, sql):
            issues.append(
                {
                    'type': 'sql',
                    'message': f'Suspicious pattern in query: {sql}',
                    'severity': 'high',
                }
            )
            break
    return issues
