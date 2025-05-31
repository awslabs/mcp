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
    # Metadata changes
    'COMMENT ON',
    'SECURITY LABEL',
    # Extensions and functions
    'CREATE EXTENSION',
    'CREATE FUNCTION',
    'INSTALL',
    # Storage-level
    'CLUSTER',
    'REINDEX',
    'VACUUM',
    'ANALYZE',
}

# Compile regex pattern
MUTATING_PATTERN = re.compile(
    r'(?i)\b(' + '|'.join(re.escape(k) for k in MUTATING_KEYWORDS) + r')\b'
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
    print(f"Suspicious patterns are ${SUSPICIOUS_PATTERNS}")
    # raise ValueError("Suspicious patterns are ${SUSPICIOUS_PATTERNS}")
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
