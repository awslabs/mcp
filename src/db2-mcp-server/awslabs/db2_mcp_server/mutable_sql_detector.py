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

"""SQL mutation and injection detection for Db2.

Adapted from the Oracle MCP server's detector for Db2 SQL dialect: Db2 uses
ANSI single-quoted string literals (``''`` escaping), double-quoted
identifiers, and ``--`` / ``/* */`` comments. Oracle-only constructs
(alternative ``q'`` quoting, ``DUAL``, ``DBMS_``/``UTL_`` packages, ``CONNECT
BY``) are removed; Db2-specific risks (``ADMIN_CMD``) are added.
"""

import re


# Characters that terminate a ``--`` line comment, for the purposes of this scanner.
#
# This is Python's universal-newline set (what ``str.splitlines()`` splits on), used
# in preference to a hand-maintained list because it is well-defined and maintained.
#
# DEFENCE IN DEPTH, NOT A KNOWN HOLE. It was suggested that breaking only on '\n' was
# an exploitable read-only bypass -- that a bare CR would end the comment for Db2
# while this scanner swallowed the remainder, letting e.g.
# ``SELECT 1 --x\rGRANT DBADM ON DATABASE TO USER x`` reach the server unexamined.
# That was tested and is NOT the case, at least on the version measured:
#
#   Verified on DB2/LINUXX8664 12.01.0400 via ibm_db 3.2.9, two independent probes
#   each with a passing LF control: Db2 treats a bare CR as ordinary comment text.
#     `SELECT 1 AS A FROM SYSIBM.SYSDUMMY1 --x<CR>)))`            -> succeeds
#     `... FROM (...) T --x<CR>WHERE A = 99`                      -> WHERE NOT applied
#   The same statements with <LF> respectively raise SQL0104N and apply the WHERE.
#
# So for CR the pre-existing behaviour already matched the server's. The broader set
# is kept anyway because it is strictly fail-closed (treating a character as a
# terminator can only cause MORE of the statement to be analysed, never less), it
# costs nothing real (a *bare* CR does not occur in practice; CRLF is unaffected
# either way), and it guards against two things not measured here: any component in
# the path normalising CR to LF, and other Db2 versions/engines or the remaining
# terminators in this set, whose lexer behaviour is untested.
_LINE_TERMINATORS = frozenset('\n\r\x0b\x0c\x1c\x1d\x1e\x85\u2028\u2029')


MUTATING_KEYWORDS = {
    # DML
    'INSERT',
    'UPDATE',
    'DELETE',
    'MERGE',
    'TRUNCATE',
    # DDL
    'CREATE',
    'DROP',
    'ALTER',
    'RENAME',
    # Permissions
    'GRANT',
    'REVOKE',
    'TRANSFER OWNERSHIP',
    # Metadata changes
    'COMMENT ON',
    # Locking
    'LOCK TABLE',
    # Stored procedure invocation (CALL SYSPROC.ADMIN_CMD can run admin ops)
    'CALL',
    # SQL PL anonymous blocks — can wrap arbitrary operations
    'BEGIN',
    'DECLARE',
    # Session / object state
    'SET',
    'SET INTEGRITY',
    # Db2 admin / maintenance operations (executed via ADMIN_CMD)
    'REORG',
    'RUNSTATS',
    'IMPORT',
    'LOAD',
    'EXPORT',
    'FLUSH',
    'REFRESH',
}


def _keyword_to_pattern(k: str) -> str:
    return r'\s+'.join(re.escape(word) for word in k.split())


# Sort multi-word keywords first so they match before their single-word prefixes
_sorted_keywords = sorted(MUTATING_KEYWORDS, key=lambda k: -len(k.split()))

MUTATING_PATTERN = re.compile(
    r'(?i)\b(' + '|'.join(_keyword_to_pattern(k) for k in _sorted_keywords) + r')\b'
)

# Operations that stay blocked even with --allow_write_query.
#
# `--allow_write_query` gates OFF detect_mutating_keywords and
# detect_transaction_bypass_attempt entirely, so before this list SUSPICIOUS_PATTERNS was
# the only guard left in write mode -- and it contained no DDL, no GRANT/REVOKE and no
# session-setting pattern. Measured with readonly=False, all of these were ALLOWED, and
# _execute_locked commits in write mode:
#
#     DROP TABLE CUSTOMERS
#     TRUNCATE TABLE CUSTOMERS IMMEDIATE
#     GRANT DBADM ON DATABASE TO USER ATTACKER
#     REVOKE CONNECT ON DATABASE FROM PUBLIC
#     SET SESSION AUTHORIZATION HR_ADMIN
#
# Write mode is meant to mean "DML allowed", not "all guards off": the documented purpose
# is INSERT/UPDATE/DELETE, so a prompt-injected or simply mistaken model should not be
# able to drop a table or grant itself DBADM. postgres-mcp-server and mysql-mcp-server
# keep their DDL/privilege/session patterns mode-independent for the same reason.
#
# SET SESSION AUTHORIZATION is the most serious of these because it is not a one-shot
# write: the connection is cached and long-lived, so the identity switch PERSISTS for
# every subsequent tool call on that connection.
#
# An operator who genuinely needs DDL through this server should use a dedicated tool,
# not an MCP endpoint an LLM drives.
ALWAYS_BLOCKED_PATTERNS = [
    # DDL -- schema destruction/alteration is never in scope for this server.
    r'(?i)\bdrop\s+(table|view|index|schema|database|tablespace|sequence|alias|trigger|function|procedure|module|type)\b',
    r'(?i)\btruncate\s+table\b',
    r'(?i)\bcreate\s+(or\s+replace\s+)?(function|procedure|trigger|module)\b',
    r'(?i)\balter\s+(table|tablespace|database|sequence|function|procedure|module)\b',
    r'(?i)\brename\s+(table|index|tablespace)\b',
    # Privilege changes.
    r'(?i)\bgrant\b\s+\w+',
    r'(?i)\brevoke\b\s+\w+',
    r'(?i)\btransfer\s+ownership\b',
    # Identity / session state that outlives the statement on a cached connection.
    r'(?i)\bset\s+session\s+authorization\b',
    r'(?i)\bset\s+current\s+sqlid\b',
]

SUSPICIOUS_PATTERNS = [
    r"(?i)'.*?--",  # comment injection
    r'(?i)\bor\b\s+\d+\s*=\s*\d+',  # numeric tautology e.g. OR 1=1
    r"(?i)\bor\b\s*'[^']*'\s*=\s*'[^']*'",  # string tautology e.g. OR '1'='1' (also matches ''='' after literal stripping)
    # UNION ... SELECT. Intentionally conservative: this also rejects some legitimate
    # read-only analytics (e.g. `SELECT a FROM t1 UNION SELECT a FROM t2`). UNION is a
    # classic exfiltration vector, so the server keeps the block by design and documents
    # the limitation in the README (see "SQL restrictions"). DOTALL so a newline between
    # UNION and SELECT cannot bypass it.
    r'(?i)\bunion\b.*\bselect\b',
    r';\s*(?!($|\s*--|\s*/\*))(?=\S)',  # stacked queries
    r'(?i)\bsleep\s*\(',  # delay-based probes
    # Db2-specific high-risk patterns
    r'(?i)\badmin_cmd\b',  # SYSPROC.ADMIN_CMD — runs arbitrary admin commands
    r'(?i)\bexecute\s+immediate\b',  # dynamic SQL execution (SQL PL)
    r'(?i)\bdbms_\w+',  # Db2 DBMS_* compatibility packages (e.g. DBMS_PIPE)
    # System stored procedures. Quotes and whitespace around the '.' are tolerated:
    # the previous r'\bsysproc\.\w+' required a word character immediately after the
    # dot, so SYSPROC."ADMIN_GET_TAB_INFO" (a delimited routine name) slipped past while
    # the unquoted spelling was blocked -- the same quoting hole already closed for the
    # authorization-catalog list below.
    r'(?i)\b"?sysproc"?\s*\.\s*"?\w+',
    # UTL_* file/HTTP/SMTP packages. The sibling \bdbms_\w+ guard was present but this
    # one was dropped, so UTL_FILE.FOPEN was allowed while DBMS_PIPE was blocked.
    r'(?i)\butl_\w+',
    r'(?i)\bsysinstallobjects\b',  # system object installer
]

READONLY_SUSPICIOUS_PATTERNS = [
    # Authorization catalog views -- expose grants/roles. Blocked in read-only mode as a
    # confidentiality measure (this is not part of the read-only write-prevention
    # guarantee).
    #
    # Matched by object-name SHAPE rather than an enumerated list. The previous
    # enumeration named 4 views (DBAUTH, TABAUTH, ROUTINEAUTH, SURROGATEAUTHIDS) out of
    # roughly 16 that carry the same grant data; MEASURED against this detector, all of
    # SCHEMAAUTH, ROLEAUTH, COLAUTH, PACKAGEAUTH and the SYSIBM.SYSDBAUTH base table
    # were allowed through while DBAUTH was blocked. An enumeration silently misses
    # every name it omits, so match \w*auth\w* instead.
    #
    # Optional quotes and whitespace around the '.' are tolerated so a delimited
    # identifier (SYSCAT."DBAUTH") or a spaced qualifier (SYSCAT . DBAUTH) cannot step
    # around the block. NOTE: that those forms resolve to the same object is INFERRED
    # from ordinary SQL identifier rules -- it has not been executed against a live
    # engine. Tolerating them is free and fail-closed, so it is done regardless, but the
    # evasion itself is unverified and should not be cited as measured. (The enumeration
    # gap above needs no such premise: those are simply different object names.)
    #
    # Anchored to the system qualifiers so a user table whose name merely contains
    # "AUTH" (e.g. APP.AUTHORS) is not caught -- see the false-positive test.
    r'(?i)\b"?(?:syscat|sysibm|sysibmadm)"?\s*\.\s*"?\w*auth\w*"?',
    # Federated wrapper options -- can expose remote server credentials.
    r'(?i)\b"?syscat"?\s*\.\s*"?(?:useroptions|serveroptions)"?\b',
    # Grant-bearing admin views whose names contain no 'AUTH', so the shape pattern
    # above does not reach them (found while pinning the false-positive boundary).
    r'(?i)\b"?sysibmadm"?\s*\.\s*"?privileges"?\b',
]

# DOTALL so that '.*' / '.*?' (e.g. the UNION ... SELECT guard) match across
# newlines; without it an injected newline between tokens bypasses the pattern.
COMPILED_ALWAYS_BLOCKED_PATTERNS = [re.compile(p, re.DOTALL) for p in ALWAYS_BLOCKED_PATTERNS]
COMPILED_SUSPICIOUS_PATTERNS = [re.compile(p, re.DOTALL) for p in SUSPICIOUS_PATTERNS]
COMPILED_READONLY_SUSPICIOUS_PATTERNS = [
    re.compile(p, re.DOTALL) for p in READONLY_SUSPICIOUS_PATTERNS
]

TRANSACTION_CONTROL_PATTERN = re.compile(
    r'(?i)\b(COMMIT|ROLLBACK|SAVEPOINT|RELEASE\s+SAVEPOINT)\b'
)


def _strip_sql_comments(sql_text: str) -> str:
    """Remove SQL comments and string-literal contents for security analysis.

    Parses character-by-character so that ``--`` and ``/*`` inside single-quoted
    Db2 string literals or double-quoted identifiers are not treated as comments.
    Comments become a single space; string-literal contents become ``''`` so that
    keywords inside string values do not trigger false positives. Double-quoted
    identifiers are preserved as-is (they name schema objects worth checking).
    """
    result: list[str] = []
    i = 0
    n = len(sql_text)

    while i < n:
        # --- double-quoted identifier ---
        if sql_text[i] == '"':
            result.append('"')
            i += 1
            while i < n:
                if sql_text[i] == '"':
                    result.append('"')
                    i += 1
                    if i < n and sql_text[i] == '"':
                        result.append('"')
                        i += 1
                        continue
                    break
                result.append(sql_text[i])
                i += 1
            continue

        # --- single-quoted string literal ('' is an escaped quote) ---
        if sql_text[i] == "'":
            i += 1
            while i < n:
                if sql_text[i] == "'":
                    i += 1
                    if i < n and sql_text[i] == "'":
                        i += 1
                        continue
                    break
                i += 1
            result.append("''")
            continue

        # --- block comment /* ... */ ---
        if sql_text[i] == '/' and i + 1 < n and sql_text[i + 1] == '*':
            i += 2
            while i < n:
                if sql_text[i] == '*' and i + 1 < n and sql_text[i + 1] == '/':
                    i += 2
                    break
                i += 1
            result.append(' ')
            continue

        # --- line comment -- ... ---
        if sql_text[i] == '-' and i + 1 < n and sql_text[i + 1] == '-':
            i += 2
            # Stop at ANY line terminator, not just '\n' -- see _LINE_TERMINATORS.
            while i < n and sql_text[i] not in _LINE_TERMINATORS:
                i += 1
            result.append(' ')
            continue

        result.append(sql_text[i])
        i += 1

    return ''.join(result)


def detect_mutating_keywords(sql_text: str) -> list[str]:
    """Return a list of mutating keywords found in the SQL (excluding comments)."""
    stripped = _strip_sql_comments(sql_text)
    matches = MUTATING_PATTERN.findall(stripped)
    return list({m.upper() for m in matches})


def check_sql_injection_risk(sql: str, readonly: bool = False) -> list[dict]:
    """Check for potential SQL injection risks in a query.

    Args:
        sql: query string
        readonly: when True, also checks for sensitive authorization-catalog access

    Returns:
        list of dictionaries describing each detected security issue
    """
    issues = []
    stripped = _strip_sql_comments(sql)

    # ALWAYS_BLOCKED_PATTERNS apply in BOTH modes -- see the comment on that list.
    # --allow_write_query turns off the mutating-keyword and transaction screens, so
    # without these DDL, GRANT/REVOKE and SET SESSION AUTHORIZATION had no guard at all
    # in write mode.
    patterns = COMPILED_ALWAYS_BLOCKED_PATTERNS + COMPILED_SUSPICIOUS_PATTERNS
    if readonly:
        patterns = patterns + COMPILED_READONLY_SUSPICIOUS_PATTERNS

    for compiled_pattern in patterns:
        if compiled_pattern.search(stripped):
            issues.append(
                {
                    'type': 'sql',
                    'message': f'Suspicious pattern in query: {sql}',
                    'severity': 'high',
                }
            )
            break
    return issues


def detect_transaction_bypass_attempt(sql: str) -> list[str]:
    """Detect transaction-control statements that could bypass read-only enforcement.

    In read-only mode the server runs with autocommit off and issues a ROLLBACK
    after execution. An injected COMMIT could defeat that protection.

    Args:
        sql: query string

    Returns:
        list of detected transaction control keywords (uppercase, deduplicated)
    """
    stripped = _strip_sql_comments(sql)
    matches = TRANSACTION_CONTROL_PATTERN.findall(stripped)
    return list({m.upper().split()[0] for m in matches})
