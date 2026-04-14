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
    'DBCC',
    'KILL',
    'SHUTDOWN',
    'RECONFIGURE',
    # Permissions
    'GRANT',
    'REVOKE',
    'DENY',
    # SQL Server-specific DDL
    'BACKUP',
    'RESTORE',
    'BULK INSERT',
    # Allows access to external data sources / linked servers
    'OPENROWSET',
    'OPENDATASOURCE',
    'OPENQUERY',
    'OPENXML',
    # Deprecated but functional T-SQL DML
    'UPDATETEXT',
    'WRITETEXT',
    # Trigger control
    'DISABLE TRIGGER',
    'ENABLE TRIGGER',
    # Stored procedure execution
    'EXEC',
    'EXECUTE',
    # Transaction control — can commit writes before Python-level rollback fires
    'COMMIT',
    # Connection context — changes active database on pooled connections
    'USE',
    # Database maintenance — flushes dirty pages to disk
    'CHECKPOINT',
    # Service Broker — writes to conversation infrastructure
    'BEGIN DIALOG',
    'BEGIN CONVERSATION',
    'END CONVERSATION',
}


def _keyword_to_pattern(k: str) -> str:
    return r'\s+'.join(re.escape(word) for word in k.split())


MUTATING_PATTERN = re.compile(
    r'(?i)\b(' + '|'.join(_keyword_to_pattern(k) for k in MUTATING_KEYWORDS) + r')\b'
)

_BLOCK_COMMENT_RE = re.compile(r'/\*.*?\*/', re.DOTALL)
_LINE_COMMENT_RE = re.compile(r'--[^\n]*')


def _strip_sql_comments(sql_text: str) -> str:
    """Remove SQL comments (-- line comments and /* block comments */) from SQL text."""
    result = _BLOCK_COMMENT_RE.sub(' ', sql_text)
    result = _LINE_COMMENT_RE.sub(' ', result)
    return result


SUSPICIOUS_PATTERNS = [
    r"(?i)'.*?--",  # comment injection
    r'(?i)\bor\b\s+\d+\s*=\s*\d+',  # numeric tautology e.g. OR 1=1
    r"(?i)\bor\b\s*'[^']+'\s*=\s*'[^']+'",  # string tautology e.g. OR '1'='1'
    r'(?i)\bunion\b.*\bselect\b',  # UNION SELECT
    r';\s*(?!($|\s*--|\s*/\*))(?=\S)',  # stacked queries, excluding semicolons followed by comments or whitespace
    r'(?i)\bwaitfor\b',  # SQL Server timing attacks (DELAY and TIME variants)
    r'(?i)\bsp_\w+',  # system stored procedures
    r'(?i)\bxp_\w+',  # extended stored procedures (high risk: xp_cmdshell etc)
    r'(?i)\brds_\w+',  # RDS stored procedures (rds_backup_database, rds_restore_database, etc)
    r'(?i)\bexec(?:ute)?\s*\(',  # EXEC('string') or EXECUTE('string') dynamic SQL injection
    r'(?i)\bset\s+context_info\b',  # non-transactional session state write (survives rollback)
    r'(?i)\bset\s+(?:noexec|parseonly|fmtonly|rowcount|implicit_transactions)\b',  # session poisoning (survives rollback, corrupts pooled connections)
    r'(?i)\braiserror\b[\s\S]*?\bwith\s+log\b',  # non-transactional write to SQL Server and Windows event logs
]


_SELECT_INTO_RE = re.compile(r'(?is)\bselect\b.*?\binto\b')

# Tokens that may validly begin a T-SQL batch in read-only mode.
# Any first token NOT in this set is treated as an implicit stored procedure call.
_SAFE_READONLY_FIRST_TOKENS = frozenset(
    {
        # DQL
        'SELECT',
        'WITH',
        # Variable / session
        'DECLARE',
        'SET',
        'PRINT',
        # Control flow
        'IF',
        'ELSE',
        'BEGIN',
        'END',
        'WHILE',
        'GOTO',
        'RETURN',
        'BREAK',
        'CONTINUE',
        'TRY',
        'CATCH',
        # Error handling
        'RAISERROR',
        'THROW',
        # Transaction control (COMMIT blocked separately)
        'ROLLBACK',
        'SAVE',
        # Cursor operations
        'OPEN',
        'CLOSE',
        'FETCH',
        'DEALLOCATE',
        # Context revert
        'REVERT',
        # Keywords in MUTATING_KEYWORDS / SUSPICIOUS_PATTERNS — included so the
        # specific keyword check fires instead of a generic "implicit proc" flag.
        'INSERT',
        'UPDATE',
        'DELETE',
        'MERGE',
        'TRUNCATE',
        'CREATE',
        'DROP',
        'ALTER',
        'EXEC',
        'EXECUTE',
        'GRANT',
        'REVOKE',
        'DENY',
        'COMMIT',
        'USE',
        'BACKUP',
        'RESTORE',
        'BULK',
        'DBCC',
        'KILL',
        'SHUTDOWN',
        'RECONFIGURE',
        'CHECKPOINT',
        'OPENROWSET',
        'OPENDATASOURCE',
        'OPENQUERY',
        'OPENXML',
        'UPDATETEXT',
        'WRITETEXT',
        'DISABLE',
        'ENABLE',
        'WAITFOR',
    }
)

_FIRST_TOKEN_RE = re.compile(r'\w+')


def _is_implicit_procedure_call(stripped_sql: str) -> bool:
    """Detect if comment-stripped SQL starts with an implicit stored procedure call.

    In SQL Server, a stored procedure can be called without the EXEC keyword
    when its name is the first statement in a batch.  Any leading identifier
    that is not a recognised T-SQL keyword is treated as a procedure name.
    """
    text = stripped_sql.strip()
    if not text:
        return False
    match = _FIRST_TOKEN_RE.match(text)
    if not match:
        return False  # starts with non-word char (e.g. parenthesis, @variable)
    first_token = match.group().upper()
    return first_token not in _SAFE_READONLY_FIRST_TOKENS


def detect_mutating_keywords(sql_text: str) -> list[str]:
    """Return a list of mutating keywords found in the SQL (excluding comments)."""
    stripped = _strip_sql_comments(sql_text)
    matches = MUTATING_PATTERN.findall(stripped)
    result = list({m.upper() for m in matches})  # Deduplicated and normalized to uppercase
    # SELECT ... INTO creates a new table and is not covered by the keyword pattern above.
    if _SELECT_INTO_RE.search(stripped):
        result.append('SELECT INTO')
    if _is_implicit_procedure_call(stripped):
        result.append('IMPLICIT PROCEDURE CALL')
    return result


def check_sql_injection_risk(sql: str) -> list[dict]:
    """Check for potential SQL injection risks in sql query.

    Args:
        sql: query string

    Returns:
        dictionaries containing detected security issue
    """
    # Run patterns against both original and comment-stripped SQL.
    # The original is needed for comment-injection detection (e.g. '.*?--).
    # The stripped version is needed to catch evasions that hide keywords
    # inside SQL comments (e.g. stacked queries disguised as ;<newline>--<newline>COMMIT).
    stripped = _strip_sql_comments(sql)
    issues = []
    for pattern in SUSPICIOUS_PATTERNS:
        if re.search(pattern, sql) or re.search(pattern, stripped):
            issues.append(
                {
                    'type': 'sql',
                    'message': f'Suspicious pattern in query: {sql}',
                    'severity': 'high',
                }
            )
            break
    return issues
