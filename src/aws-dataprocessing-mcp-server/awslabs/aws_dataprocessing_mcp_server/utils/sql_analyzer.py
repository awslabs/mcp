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

"""SQL Query Analyzer for detecting write operations and preventing SQL injection."""

import re
from typing import Optional


class SqlAnalyzer:
    """Utility class for analyzing SQL queries to detect write operations."""

    # Pre-compiled regex patterns for better performance
    # Patterns for write operations that modify data or schema
    WRITE_OPERATION_PATTERNS = [
        # Data modification operations
        r'\b(?:INSERT|UPDATE|DELETE|TRUNCATE|MERGE|REPLACE|UPSERT)\b',
        # Schema modification operations (DDL) - more specific than generic CREATE|DROP|ALTER
        r'\b(?:CREATE|DROP|ALTER)\s+(?:TABLE|VIEW|INDEX|TRIGGER|PROCEDURE|FUNCTION|EVENT)\b',
        # Generic DDL operations (fallback for less common objects)
        r'\b(?:CREATE|DROP|ALTER)\b',
        # Table operations
        r'\b(?:RENAME\s+TABLE)\b',
        # Permission and security operations
        r'\b(?:GRANT|REVOKE)\b',
        # Procedure calls that might modify data
        r'\b(?:CALL|EXEC(?:UTE)?)\b',
        # CTAS and similar operations
        r'\b(?:CREATE\s+TABLE\s+AS\s+SELECT|CREATE\s+VIEW\s+AS\s+SELECT)\b',
        # Import/Export operations - enhanced with specific LOAD operations
        r'\b(?:COPY|IMPORT|EXPORT|BULK\s+INSERT)\b',
        r'\b(?:LOAD\s+DATA|LOAD\s+XML)\b',
        # Plugin operations
        r'\b(?:INSTALL\s+PLUGIN|UNINSTALL\s+PLUGIN)\b',
    ]

    # Compiled regex patterns for performance optimization
    _COMPILED_WRITE_PATTERNS = None
    _COMPILED_READ_PATTERNS = None

    # Patterns for read-only operations that are explicitly allowed
    READ_ONLY_OPERATION_PATTERNS = [
        r'\b(?:SELECT|WITH|SHOW|DESCRIBE|DESC|EXPLAIN|ANALYZE)\b',
    ]

    @classmethod
    def _get_compiled_write_patterns(cls):
        """Get compiled write operation patterns for better performance."""
        if cls._COMPILED_WRITE_PATTERNS is None:
            cls._COMPILED_WRITE_PATTERNS = [
                re.compile(pattern, re.IGNORECASE | re.VERBOSE)
                for pattern in cls.WRITE_OPERATION_PATTERNS
            ]
        return cls._COMPILED_WRITE_PATTERNS

    @classmethod
    def _get_compiled_read_patterns(cls):
        """Get compiled read-only operation patterns for better performance."""
        if cls._COMPILED_READ_PATTERNS is None:
            cls._COMPILED_READ_PATTERNS = [
                re.compile(pattern, re.IGNORECASE | re.VERBOSE)
                for pattern in cls.READ_ONLY_OPERATION_PATTERNS
            ]
        return cls._COMPILED_READ_PATTERNS

    @classmethod
    def _remove_sql_comments(cls, sql: str) -> str:
        """Remove SQL comments from the query string.

        Args:
            sql: The SQL query string

        Returns:
            SQL string with comments removed
        """
        # Remove multi-line comments /* ... */
        sql = re.sub(r'/\*.*?\*/', ' ', sql, flags=re.DOTALL)

        # Remove single-line comments -- ...
        sql = re.sub(r'--.*$', ' ', sql, flags=re.MULTILINE)

        return sql

    @classmethod
    def _normalize_whitespace(cls, sql: str) -> str:
        """Normalize whitespace in SQL string.

        Args:
            sql: The SQL query string

        Returns:
            SQL string with normalized whitespace
        """
        # Replace multiple whitespace characters with single space
        sql = re.sub(r'\s+', ' ', sql)

        # Remove leading and trailing whitespace
        sql = sql.strip()

        return sql

    @classmethod
    def _preprocess_sql(cls, sql: str) -> str:
        """Preprocess SQL by removing comments and normalizing whitespace.

        Args:
            sql: The raw SQL query string

        Returns:
            Cleaned and normalized SQL string
        """
        if not sql:
            return ''

        # Remove comments first
        cleaned_sql = cls._remove_sql_comments(sql)

        # Normalize whitespace
        cleaned_sql = cls._normalize_whitespace(cleaned_sql)

        return cleaned_sql

    @classmethod
    def contains_write_operations(cls, sql: Optional[str]) -> bool:
        """Check if SQL contains write operations that modify data or schema.

        This method analyzes SQL queries to detect operations that would modify
        data, schema, or system state. It's designed to prevent SQL injection
        attacks that use comments to bypass simple keyword detection.

        Args:
            sql: The SQL query string to analyze

        Returns:
            True if the query contains write operations, False otherwise

        Examples:
            >>> SqlAnalyzer.contains_write_operations('SELECT * FROM table')
            False
            >>> SqlAnalyzer.contains_write_operations('INSERT INTO table VALUES (1,2,3)')
            True
            >>> SqlAnalyzer.contains_write_operations(
            ...     'INSERT /* SELECT */ INTO table VALUES (1,2,3)'
            ... )
            True
            >>> SqlAnalyzer.contains_write_operations(
            ...     'WITH cte AS (SELECT * FROM t1) SELECT * FROM cte'
            ... )
            False
        """
        if not sql:
            return False

        # Preprocess SQL to remove comments and normalize whitespace
        cleaned_sql = cls._preprocess_sql(sql)

        if not cleaned_sql:
            return False

        # Use compiled patterns for better performance
        compiled_patterns = cls._get_compiled_write_patterns()

        # Check for write operation patterns using compiled regex
        for compiled_pattern in compiled_patterns:
            if compiled_pattern.search(cleaned_sql):
                return True

        return False

    @classmethod
    def is_read_only_query(cls, sql: Optional[str]) -> bool:
        """Check if SQL is a read-only query.

        This method determines if a query is safe to execute in read-only mode.
        It uses a whitelist approach, only allowing explicitly safe operations.

        Args:
            sql: The SQL query string to analyze

        Returns:
            True if the query is read-only, False otherwise
        """
        if not sql:
            return False

        # Preprocess SQL to remove comments and normalize whitespace
        cleaned_sql = cls._preprocess_sql(sql)

        if not cleaned_sql:
            return False

        # First check if it contains any write operations
        if cls.contains_write_operations(sql):
            return False

        # Then check if it starts with a read-only operation
        # We look for the first SQL keyword after preprocessing
        first_keyword_match = re.match(r'^\s*(\w+)', cleaned_sql, re.IGNORECASE | re.VERBOSE)
        if not first_keyword_match:
            return False

        first_keyword = first_keyword_match.group(1)

        # Use compiled patterns for better performance
        compiled_read_patterns = cls._get_compiled_read_patterns()

        # Check against read-only patterns using compiled regex
        for compiled_pattern in compiled_read_patterns:
            if compiled_pattern.match(first_keyword):
                return True

        return False

    @classmethod
    def get_query_type(cls, sql: Optional[str]) -> str:
        """Get the type of SQL query after preprocessing.

        Args:
            sql: The SQL query string to analyze

        Returns:
            The first SQL keyword found, or 'UNKNOWN' if none found
        """
        if not sql:
            return 'UNKNOWN'

        # Preprocess SQL to remove comments and normalize whitespace
        cleaned_sql = cls._preprocess_sql(sql)

        if not cleaned_sql:
            return 'UNKNOWN'

        # Convert to uppercase and extract first keyword
        upper_sql = cleaned_sql.upper()
        first_keyword_match = re.match(r'^\s*(\w+)', upper_sql)

        if first_keyword_match:
            return first_keyword_match.group(1)

        return 'UNKNOWN'
