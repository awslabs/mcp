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
    # DDL
    'CREATE',
    'DROP',
    'ALTER',
    'RENAME',
    # Permissions
    'GRANT',
    'REVOKE',
    # Auditing (Oracle-specific)
    'AUDIT',
    'NOAUDIT',
    # Metadata changes
    'COMMENT ON',
    # Recycle bin
    'PURGE',
    # Data recovery (Oracle-specific)
    'FLASHBACK',
    # Statistics
    'ANALYZE',
    'ASSOCIATE STATISTICS',
    'DISASSOCIATE STATISTICS',
    # Locking
    'LOCK TABLE',
    # Stored procedure invocation
    'CALL',
    # PL/SQL anonymous blocks — can wrap arbitrary operations
    'BEGIN',
    'DECLARE',
    # Session privilege escalation
    'SET ROLE',
    # System administration
    'ADMINISTER',
    # Execution plan — writes to PLAN_TABLE
    'EXPLAIN PLAN',
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
    r"(?i)\bor\b\s*'[^']+'\s*=\s*'[^']+'",  # string tautology e.g. OR '1'='1'
    r'(?i)\bunion\b.*\bselect\b',  # UNION SELECT
    r';\s*(?!($|\s*--|\s*/\*))(?=\S)',  # stacked queries
    r'(?i)\bsleep\s*\(',  # delay-based probes
    r'(?i)\bdbms_\w+',  # DBMS packages (dbms_scheduler, dbms_pipe, dbms_sql, dbms_lock etc)
    r'(?i)\butl_\w+',  # UTL packages (utl_file, utl_http, utl_smtp etc)
    # Oracle-specific high-risk patterns
    r'(?i)\bexecute\s+immediate\b',  # dynamic SQL execution
    r'(?i)\balter\s+system\b',  # instance-level parameter changes
    r'(?i)\balter\s+session\b',  # session parameter changes
    r'(?i)\bcreate\s+directory\b',  # enables filesystem access via UTL_FILE
    r'(?i)\bcreate\s+database\s+link\b',  # remote database connections
    r'(?i)\bcreate\s+or\s+replace\b',  # silent object replacement
    r'(?i)\bautonomous_transaction\b',  # transaction isolation bypass
    r'(?i)\bowa_util\b',  # Oracle Web Application Server utilities
    r'(?i)\bhtp\.\w+',  # Oracle HTTP toolkit
    r'(?i)\bhtf\.\w+',  # Oracle HTML generation toolkit
    r'(?i)\bcreate\s+java\b',  # Java stored procedures — arbitrary code execution
    r'(?i)\bxmltype\s*\(',  # XMLTYPE constructor — XXE attack vector
    r"(?i)q'\s*[\[{(<|!]",  # Oracle alternative quoting — can hide injection from pattern matching
    r'(?i)\bsys\.\w+\$',  # SYS internal tables — password hashes, link credentials
    r'(?i)\b(v\$|gv\$|dba_)\w+',  # Sensitive dictionary views — instance metadata, user credentials
    r'(?i)\b(httpuritype|uritype)\b',  # SSRF / data exfiltration via HTTP requests from SQL
    r'(?i)\bctxsys\.\w+',  # Oracle Text schema — known OS command injection vector
    r'(?i)\bconnect\s+by\s+\d+\s*=\s*\d+',  # CONNECT BY tautology — DoS via infinite recursion
    r'(?i)\bconnect\s+by\s+level\b',  # CONNECT BY LEVEL — DoS via unbounded row generation
    r'(?i)\bconnect\s+by\s+rownum\b',  # CONNECT BY ROWNUM — DoS via unbounded row generation
]

COMPILED_SUSPICIOUS_PATTERNS = [re.compile(p) for p in SUSPICIOUS_PATTERNS]

TRANSACTION_CONTROL_PATTERN = re.compile(r'(?i)\b(COMMIT|ROLLBACK|SAVEPOINT|SET\s+TRANSACTION)\b')


def _strip_sql_comments(sql_text: str) -> str:
    """Remove SQL comments while preserving string literal contents.

    Parses character-by-character to correctly handle ``--`` and ``/*``
    that appear inside single-quoted Oracle string literals (including
    Oracle alternative quoting ``q'X...X'``) and double-quoted
    identifiers.  Comment markers inside strings or identifiers are
    left untouched; only true comments are replaced with a single space.
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
                    break
                result.append(sql_text[i])
                i += 1
            continue

        # --- single-quoted string literal ---
        if sql_text[i] == "'":
            # Check for Oracle alternative quoting: q'<delim>...<delim>'
            # The prefix is q' or Q' and we already consumed up to the quote.
            if i >= 1 and sql_text[i - 1] in ('q', 'Q'):
                open_delim = sql_text[i + 1] if i + 1 < n else None
                close_delim = (
                    {'[': ']', '{': '}', '(': ')', '<': '>'}.get(open_delim, open_delim)
                    if open_delim
                    else None
                )
                # Replace the 'q' we already appended with the full literal
                result.append("'")
                i += 2  # skip past quote + open delimiter
                # Scan for close_delim followed by '
                while i < n:
                    if sql_text[i] == close_delim and i + 1 < n and sql_text[i + 1] == "'":
                        result.append(sql_text[i])
                        result.append("'")
                        i += 2
                        break
                    result.append(sql_text[i])
                    i += 1
                continue

            # Standard single-quoted string: '' is an escaped quote
            result.append("'")
            i += 1
            while i < n:
                if sql_text[i] == "'":
                    result.append("'")
                    i += 1
                    # '' is an escaped single quote — stay in string
                    if i < n and sql_text[i] == "'":
                        result.append("'")
                        i += 1
                        continue
                    break  # end of string literal
                result.append(sql_text[i])
                i += 1
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


def check_sql_injection_risk(sql: str) -> list[dict]:
    """Check for potential SQL injection risks in sql query.

    Args:
        sql: query string

    Returns:
        dictionaries containing detected security issue
    """
    issues = []
    stripped = _strip_sql_comments(sql)

    for compiled_pattern in COMPILED_SUSPICIOUS_PATTERNS:
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
    """Detect transaction control statements that could bypass read-only enforcement.

    In read-only mode the server wraps queries with SET TRANSACTION READ ONLY
    and issues a ROLLBACK after execution. An injected COMMIT or other
    transaction control statement could defeat this protection.

    Args:
        sql: query string

    Returns:
        list of detected transaction control keywords (uppercase, deduplicated)
    """
    stripped = _strip_sql_comments(sql)
    matches = TRANSACTION_CONTROL_PATTERN.findall(stripped)
    return list({m.upper() for m in matches})
