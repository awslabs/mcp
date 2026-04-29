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
        SELECT\s+.*\s+INTO\s+OUTFILE|
        USE\s+\w+|
        SET\s+autocommit|
        COPY\s+.*\s+FROM|
        COPY\s+.*\s+TO
    )\b
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
    (r"(?i)'.*?--", 'comment_injection'),
    (r'(?i)\bor\b\s+\d+\s*=\s*\d+', 'numeric_tautology'),
    (r"(?i)\bor\b\s*'[^']+'\s*=\s*'[^']+'", 'string_tautology'),
    (r';\s*(?!($|\s*--|\s*/\*))(?=\S)', 'stacked_query'),
    (r'(?i)\bsleep\s*\(', 'sleep_time_based'),
    (r'(?i)\bpg_sleep\s*\(', 'pg_sleep_time_based'),
    (r'(?i)\bload_file\s*\(', 'load_file'),
    (r'(?i)\binto\s+outfile\b', 'into_outfile'),
    (r'(?i)\b(begin|commit|rollback)\b.*;\s*\w+', 'transaction_control_with_extra_statement'),
]

KEYWORD_PATTERNS = [
    (r'(?i)\bunion\b.*\bselect\b', 'union_select'),
    (r'(?i)\bdrop\b', 'drop'),
    (r'(?i)\btruncate\b', 'truncate'),
    (r'(?i)\bgrant\b|\brevoke\b', 'grant_revoke'),
    (r'(?i)\bcopy\s+.*\s+from\b', 'copy_from'),
    (r'(?i)\bcopy\s+.*\s+to\b', 'copy_to'),
]

SUSPICIOUS_PATTERNS = INJECTION_PATTERNS + KEYWORD_PATTERNS


def detect_mutating_keywords(sql: str) -> list[str]:
    """Return a list of mutating keywords found in the SQL (excluding comments)."""
    matched = []

    if DDL_REGEX.search(sql):
        matched.append('DDL')

    if PERMISSION_REGEX.search(sql):
        matched.append('PERMISSION')

    if SYSTEM_REGEX.search(sql):
        matched.append('SYSTEM')

    if TRANSACTION_CONTROL_REGEX.search(sql):
        matched.append('TRANSACTION_CONTROL')

    # Match individual keywords from MUTATING_KEYWORDS
    keyword_matches = MUTATING_PATTERN.findall(sql)
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
            'comment_injection', 'stacked_query'). Callers can compare
            this against a known set without regex-parsing the message.
          - message: a human-readable summary (does not include the raw regex
            to avoid leaking filter internals to callers).
          - severity: always 'high'.
    """
    patterns = SUSPICIOUS_PATTERNS if read_only else INJECTION_PATTERNS
    for pattern, label in patterns:
        if re.search(pattern, sql):
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
    # Look for COMMIT followed by other statements
    commit_bypass_pattern = re.compile(r'(?i)\bcommit\b.*?;\s*(?!($|\s*--|\s*/\*))\w+', re.DOTALL)

    # Look for multiple statements separated by semicolons
    multiple_statements = re.compile(r';\s*(?!($|\s*--|\s*/\*))(?=\S)')

    return bool(commit_bypass_pattern.search(sql)) or len(multiple_statements.findall(sql)) > 0
