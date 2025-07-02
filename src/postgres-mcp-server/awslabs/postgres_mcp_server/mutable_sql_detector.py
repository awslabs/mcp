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

"""
SQL mutation detection for PostgreSQL MCP server.

This module provides functions to detect SQL statements that would modify the database.
"""

import re
from typing import List, Optional

# List of SQL keywords that indicate a mutating operation
MUTATING_KEYWORDS = [
    r'^\s*INSERT\s+',
    r'^\s*UPDATE\s+',
    r'^\s*DELETE\s+',
    r'^\s*DROP\s+',
    r'^\s*ALTER\s+',
    r'^\s*CREATE\s+',
    r'^\s*TRUNCATE\s+',
    r'^\s*GRANT\s+',
    r'^\s*REVOKE\s+',
    r'^\s*VACUUM\s+',
    r'^\s*REINDEX\s+',
    r'^\s*CLUSTER\s+',
    r'^\s*RESET\s+',
    r'^\s*LOAD\s+',
    r'^\s*COPY\s+.*\s+TO\s+',
]

# SQL injection patterns to check for
SQL_INJECTION_PATTERNS = [
    r';\s*DROP\s+',
    r';\s*DELETE\s+',
    r';\s*INSERT\s+',
    r';\s*UPDATE\s+',
    r';\s*ALTER\s+',
    r';\s*CREATE\s+',
    r'--',
    r'/\*.*\*/',
    r'UNION\s+SELECT',
    r'UNION\s+ALL\s+SELECT',
    r'OR\s+1\s*=\s*1',
    r'OR\s+\'1\'\s*=\s*\'1\'',
    r'OR\s+\'a\'\s*=\s*\'a\'',
    r'OR\s+[\'"].*[\'"]=[\'"].*[\'"]',
]

def detect_mutating_keywords(sql: str) -> List[str]:
    """
    Detect SQL keywords that would modify the database.
    
    Args:
        sql: The SQL statement to check
        
    Returns:
        List of detected mutating keywords
    """
    sql = sql.upper()
    matches = []
    
    for pattern in MUTATING_KEYWORDS:
        if re.search(pattern, sql, re.IGNORECASE):
            # Extract the actual keyword that matched
            keyword = re.search(pattern, sql, re.IGNORECASE).group(0).strip()
            matches.append(keyword)
    
    return matches

def check_sql_injection_risk(sql: str) -> List[dict]:
    """
    Check for potential SQL injection patterns in the query.
    
    Args:
        sql: The SQL statement to check
        
    Returns:
        List of detected issues with pattern and reason
    """
    issues = []
    
    for pattern in SQL_INJECTION_PATTERNS:
        matches = re.finditer(pattern, sql, re.IGNORECASE)
        for match in matches:
            issues.append({
                'pattern': match.group(0),
                'position': match.start(),
                'reason': f"Potential SQL injection pattern detected: {match.group(0)}"
            })
    
    return issues

def validate_read_only_query(sql: str) -> tuple[bool, Optional[str]]:
    """
    Validate that a query is read-only.
    
    Args:
        sql: The SQL statement to check
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check for mutating keywords
    mutating_matches = detect_mutating_keywords(sql)
    if mutating_matches:
        return False, f"Query contains mutating operations: {', '.join(mutating_matches)}"
    
    # Check for SQL injection risks
    injection_risks = check_sql_injection_risk(sql)
    if injection_risks:
        risk_messages = [risk['reason'] for risk in injection_risks]
        return False, f"Query contains potential SQL injection risks: {'; '.join(risk_messages)}"
    
    # Check if the query starts with allowed operations
    allowed_prefixes = ['SELECT', 'EXPLAIN', 'SHOW', 'WITH']
    sql_upper = sql.upper().strip()
    
    if not any(sql_upper.startswith(prefix) for prefix in allowed_prefixes):
        return False, f"Query must start with one of: {', '.join(allowed_prefixes)}"
    
    return True, None
