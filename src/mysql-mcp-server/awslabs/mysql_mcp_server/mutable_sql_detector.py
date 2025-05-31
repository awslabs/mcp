# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.

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
}

MUTATING_PATTERN = re.compile(
    r'(?i)\b(' + '|'.join(re.escape(k) for k in MUTATING_KEYWORDS) + r')\b'
)

# -- Regex for DDL statements --
DDL_REGEX = re.compile(
    r"""
    ^\s*(
        CREATE\s+(TABLE|VIEW|INDEX|TRIGGER|PROCEDURE|FUNCTION|EVENT)|
        DROP\s+(TABLE|VIEW|INDEX|TRIGGER|PROCEDURE|FUNCTION|EVENT)|
        ALTER\s+(TABLE|VIEW|TRIGGER|PROCEDURE|FUNCTION|EVENT)|
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
        SET\s+autocommit
    )\b
    """,
    re.IGNORECASE | re.VERBOSE,
)

# -- Suspicious pattern detection (SQL injection, stacked queries, etc.) --
SUSPICIOUS_PATTERNS = [
    r"(?i)'.*?--",  # comment injection
    r'(?i)\bor\b\s+\d+\s*=\s*\d+',  # numeric tautology
    r"(?i)\bor\b\s*'[^']+'\s*=\s*'[^']+'",  # string tautology
    r'(?i)\bunion\b.*\bselect\b',  # UNION SELECT
    r'(?i)\bdrop\b',  # DROP
    r'(?i)\btruncate\b',  # TRUNCATE
    r'(?i)\bgrant\b|\brevoke\b',  # GRANT or REVOKE
    r';\s*(?!($|\s*--|\s*/\*))(?=\S)',  # stacked queries, excluding semicolons followed by comments or whitespace
    r'(?i)\bsleep\s*\(',  # time-based injection
    r'(?i)\bload_file\s*\(',  # file read
    r'(?i)\binto\s+outfile\b',  # file write
]


def detect_mutating_keywords(sql: str) -> list[str]:
    """Return a list of mutating keywords found in the SQL (excluding comments)."""
    matched = []

    if DDL_REGEX.search(sql):
        matched.append('DDL')

    if PERMISSION_REGEX.search(sql):
        matched.append('PERMISSION')

    if SYSTEM_REGEX.search(sql):
        matched.append('SYSTEM')

    # Match individual keywords from MUTATING_KEYWORDS
    keyword_matches = MUTATING_PATTERN.findall(sql)
    if keyword_matches:
        # Deduplicate and normalize casing
        matched.extend(sorted({k.upper() for k in keyword_matches}))

    return matched


def check_sql_injection_risk(sql: str) -> list[dict]:
    """Check for potential SQL injection risks in sql query.

    Args:
        sql: query string

    Returns:
        dictionaries containing detected security issue
    """
    issues = []
    for pattern in SUSPICIOUS_PATTERNS:
        if re.search(pattern, sql):
            issues.append(
                {
                    'type': 'sql',
                    'message': f'Suspicious pattern: {pattern}',
                    'severity': 'high',
                }
            )
            break
    return issues
