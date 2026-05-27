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

"""Tests for mutable_sql_detector module."""

from awslabs.mysql_mcp_server.mutable_sql_detector import (
    check_sql_injection_risk,
    detect_mutating_keywords,
)


class TestDetectMutatingKeywords:
    """Tests for detect_mutating_keywords function."""

    def test_replace_statement_blocked(self):
        """REPLACE INTO is a mutating DML statement and should be detected."""
        result = detect_mutating_keywords('REPLACE INTO users (id, name) VALUES (1, "John")')
        assert 'REPLACE' in result

    def test_replace_function_allowed(self):
        """REPLACE() string function in SELECT should not be detected as mutating."""
        result = detect_mutating_keywords(
            "SELECT REPLACE(product_name, 'Old', 'New') FROM products"
        )
        assert 'REPLACE' not in result
        assert result == []

    def test_replace_function_nested(self):
        """Nested REPLACE() function calls should not be detected as mutating."""
        result = detect_mutating_keywords(
            "SELECT REPLACE(REPLACE(email, '@old.com', '@new.com'), '.', '_') FROM users"
        )
        assert 'REPLACE' not in result
        assert result == []

    def test_replace_function_with_spaces(self):
        """REPLACE  ( with spaces before parenthesis should be treated as function."""
        result = detect_mutating_keywords("SELECT REPLACE  (col, 'a', 'b') FROM t")
        assert 'REPLACE' not in result
        assert result == []

    def test_replace_function_in_where_clause(self):
        """REPLACE() in WHERE clause should not be detected as mutating."""
        result = detect_mutating_keywords(
            "SELECT * FROM products WHERE REPLACE(bucket_name, ' ', '_') = 'normalized_value'"
        )
        assert 'REPLACE' not in result
        assert result == []

    def test_replace_function_lowercase(self):
        """Lowercase replace() function should not be detected as mutating."""
        result = detect_mutating_keywords(
            "SELECT replace(name, 'old', 'new') FROM users"
        )
        assert 'REPLACE' not in result
        assert result == []

    def test_insert_detected(self):
        """INSERT statements should be detected."""
        result = detect_mutating_keywords('INSERT INTO users VALUES (1, "John")')
        assert 'INSERT' in result

    def test_update_detected(self):
        """UPDATE statements should be detected."""
        result = detect_mutating_keywords("UPDATE users SET name = 'Jane' WHERE id = 1")
        assert 'UPDATE' in result

    def test_delete_detected(self):
        """DELETE statements should be detected."""
        result = detect_mutating_keywords('DELETE FROM users WHERE id = 1')
        assert 'DELETE' in result

    def test_select_allowed(self):
        """Plain SELECT should not be detected as mutating."""
        result = detect_mutating_keywords('SELECT * FROM users WHERE id = 1')
        assert result == []

    def test_ddl_detected(self):
        """DDL statements should be detected."""
        result = detect_mutating_keywords('CREATE TABLE users (id INT)')
        assert 'DDL' in result

    def test_drop_detected(self):
        """DROP statements should be detected."""
        result = detect_mutating_keywords('DROP TABLE users')
        assert 'DDL' in result
        assert 'DROP' in result


class TestCheckSqlInjectionRisk:
    """Tests for check_sql_injection_risk function."""

    def test_safe_query(self):
        """Normal queries should not trigger injection detection."""
        result = check_sql_injection_risk('SELECT * FROM users WHERE id = 1')
        assert result == []

    def test_union_select_detected(self):
        """UNION SELECT injection should be detected."""
        result = check_sql_injection_risk('SELECT * FROM users UNION SELECT * FROM passwords')
        assert len(result) > 0

    def test_stacked_queries_detected(self):
        """Stacked queries should be detected."""
        result = check_sql_injection_risk('SELECT 1; DROP TABLE users')
        assert len(result) > 0
