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
    r'(?i)\bsysproc\.\w+',  # system stored procedures
    r'(?i)\bsysinstallobjects\b',  # system object installer
]

READONLY_SUSPICIOUS_PATTERNS = [
    # Authorization catalog views — expose grants/roles. Block in read-only mode.
    r'(?i)\bsyscat\.(dbauth|tabauth|routineauth|surrogateauthids)\b',
]

# DOTALL so that '.*' / '.*?' (e.g. the UNION ... SELECT guard) match across
# newlines; without it an injected newline between tokens bypasses the pattern.
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
            while i < n and sql_text[i] != '\n':
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

    patterns = COMPILED_SUSPICIOUS_PATTERNS
    if readonly:
        patterns = COMPILED_SUSPICIOUS_PATTERNS + COMPILED_READONLY_SUSPICIOUS_PATTERNS

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
