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
from enum import Enum


# ---------------------------------------------
# Query Classification Enums and Regex
# ---------------------------------------------


class QueryType(Enum):
    """Query Type."""

    SAFE = 'SAFE'
    MUTATING_DDL = 'MUTATING_DDL'
    PERMISSION_MODIFYING = 'PERMISSION_MODIFYING'
    SYSTEM_MODIFYING = 'SYSTEM_MODIFYING'


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

# ---------------------------------------------
# Comment Removal
# ---------------------------------------------


def remove_sql_comments(sql: str) -> str:
    """Removes --, #, and /* */ style comments from SQL."""
    sql = re.sub(r'--.*?$', '', sql, flags=re.MULTILINE)
    sql = re.sub(r'#.*?$', '', sql, flags=re.MULTILINE)
    sql = re.sub(r'/\*.*?\*/', '', sql, flags=re.DOTALL)
    return sql.strip()


# ---------------------------------------------
# Query Classifier with Comment Handling
# ---------------------------------------------


def classify_query(raw_query: str) -> tuple[QueryType, str]:
    """Classify a query with following returns."""
    cleaned = remove_sql_comments(raw_query).strip().split(';')[0]

    if DDL_REGEX.match(cleaned):
        return QueryType.MUTATING_DDL, raw_query
    elif PERMISSION_REGEX.match(cleaned):
        return QueryType.PERMISSION_MODIFYING, raw_query
    elif SYSTEM_REGEX.match(cleaned):
        return QueryType.SYSTEM_MODIFYING, raw_query
    else:
        return QueryType.SAFE, cleaned


# ---------------------------------------------
# SQL Injection Detection in Parameters
# ---------------------------------------------

SUSPICIOUS_PATTERNS = [
    r'(?i)\bOR\b\s+\d+\s*=\s*\d+',  # OR 1=1
    r"(?i)'?\s*OR\s*'[^']*'\s*=\s*'[^']*",  # ' OR 'a'='a'
    r'(?i)UNION\s+SELECT',  # UNION SELECT
    r'(?i)(--|#)',  # comment
    r'(?i)/\*!.*?\*/',
    r'(?i);',  # stacked query
    r'(?i)SLEEP\s*\(',  # delay injection
    r'(?i)LOAD_FILE\s*\(',
    r'(?i)INTO\s+OUTFILE',
]


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
