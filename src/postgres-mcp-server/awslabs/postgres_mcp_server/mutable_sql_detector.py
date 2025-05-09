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

SUSPICIOUS_PATTERNS = [
    r"(?i)'.*?--",
    r"(?i)'.*?or\s+1=1",
    r'(?i)\bunion\b.*\bselect\b',
    r'(?i)\bdrop\b',
    r'(?i)\btruncate\b',
    r'(?i)\bgrant\b|\brevoke\b',
    r'(?i);',
    r"(?i)or\s+['\"]?\d+=\d+",
]

# Compile regex pattern
MUTATING_PATTERN = re.compile(
    r'(?i)\b(' + '|'.join(re.escape(k) for k in MUTATING_KEYWORDS) + r')\b'
)


def remove_comments(sql: str) -> str:
    """Remove SQL comments from the input string.

    Args:
        sql: The SQL string to process

    Returns:
        The SQL string with all comments removed
    """
    sql = re.sub(r'--.*?$', '', sql, flags=re.MULTILINE)
    sql = re.sub(r'/\*.*?\*/', '', sql, flags=re.DOTALL)
    return sql


def remove_strings(sql: str) -> str:
    """Remove string literals from the SQL query.

    Args:
        sql: The SQL string to process

    Returns:
        The SQL string with all string literals removed
    """
    # Remove single-quoted and double-quoted string literals
    return re.sub(r"('([^']|'')*')|(\"([^\"]|\"\")*\")", '', sql)


def detect_mutating_keywords(sql_text: str) -> list[str]:
    """Return a list of mutating keywords found in the SQL (excluding comments)."""
    cleaned_sql = remove_comments(sql_text)
    cleaned_sql = remove_strings(cleaned_sql)
    matches = MUTATING_PATTERN.findall(cleaned_sql)
    return list({m.upper() for m in matches})  # Deduplicated and normalized to uppercase


def check_sql_injection_risk(parameters: list[dict] | None) -> list[dict]:
    """Check for potential SQL injection risks in query parameters.

    Args:
        parameters: List of parameter dictionaries containing name and value pairs

    Returns:
        List of dictionaries containing detected security issues
    """
    issues = []

    if parameters is not None:
        for param in parameters:
            value = next(iter(param['value'].values()))
            for pattern in SUSPICIOUS_PATTERNS:
                if re.search(pattern, str(value)):
                    issues.append(
                        {
                            'type': 'parameter',
                            'parameter_name': param['name'],
                            'message': f'Suspicious pattern in value: {value}',
                            'severity': 'high',
                        }
                    )
                    break

    return issues
