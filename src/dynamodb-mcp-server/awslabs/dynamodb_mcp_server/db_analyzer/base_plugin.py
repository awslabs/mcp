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

#!/usr/bin/env python3

"""Base plugin interface for database analyzers."""

import os
from abc import ABC, abstractmethod
from awslabs.dynamodb_mcp_server.common import validate_database_name
from datetime import datetime
from typing import Any, Dict


class DatabasePlugin(ABC):
    """Base class for database-specific analyzer plugins."""

    @abstractmethod
    def get_queries(self) -> Dict[str, Any]:
        """Get all analysis queries for this database type.

        Returns:
            Dictionary of query definitions with metadata
        """
        pass

    @abstractmethod
    def get_database_display_name(self) -> str:
        """Get the display name of the database type.

        Returns:
            Database type name (e.g., 'MySQL', 'PostgreSQL', 'SQL Server')
        """
        pass

    def apply_result_limit(self, sql: str, max_results: int) -> str:
        """Apply result limit to SQL query.

        Default implementation uses LIMIT syntax (MySQL/PostgreSQL).
        Override for databases with different syntax (e.g., SQL Server uses TOP).

        Args:
            sql: SQL query string
            max_results: Maximum number of results

        Returns:
            SQL query with limit applied
        """
        sql = sql.rstrip(';')
        return f'{sql} LIMIT {max_results};'

    def write_queries_to_file(
        self, target_database: str, max_results: int, output_file: str
    ) -> str:
        """Generate SQL file with all analysis queries.

        Database-specific behavior is handled through get_database_display_name() and
        apply_result_limit() methods.

        Args:
            target_database: Target database/schema name
            max_results: Maximum results per query
            output_file: Path to output SQL file

        Returns:
            Path to generated file
        """
        # Validate database name before using it
        validate_database_name(target_database)

        queries = self.get_queries()

        sql_content = [
            f'-- {self.get_database_display_name()} Database Analysis Queries',
            f'-- Target Database: {target_database}',
            f'-- Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
            '',
            '-- EXECUTION INSTRUCTIONS:',
            '-- 1. Review all queries before execution',
            '-- 2. Run during off-peak hours if possible',
            '-- 3. Each query has a LIMIT clause to prevent excessive results',
            '',
            '-- Generated for DynamoDB Data Modeling\n',
        ]

        total_queries = sum(1 for q in queries.values() if q.get('category') != 'internal')
        query_number = 0

        for query_name, query_info in queries.items():
            # Skip internal queries
            if query_info.get('category') == 'internal':
                continue

            query_number += 1

            sql_content.append('')
            sql_content.append('-- ============================================')
            sql_content.append(f'-- QUERY {query_number}/{total_queries}: {query_name}')
            sql_content.append('-- ============================================')
            sql_content.append(f'-- Description: {query_info.get("description", "N/A")}')
            sql_content.append(f'-- Category: {query_info.get("category", "N/A")}')

            # Add marker as a SELECT statement that outputs to results
            sql_content.append(f"SELECT '-- QUERY_NAME_START: {query_name}' AS marker;")

            sql = query_info['sql']
            # Substitute target_database parameter
            if 'target_database' in query_info.get('parameters', []):
                sql = sql.format(target_database=target_database)

            # Apply result limit (database-specific)
            sql = self.apply_result_limit(sql, max_results)

            sql_content.append(sql)

            # Add end marker as a SELECT statement
            sql_content.append(f"SELECT '-- QUERY_NAME_END: {query_name}' AS marker;")
            sql_content.append('')

        # Write to file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(sql_content))

        return output_file

    def parse_results_from_file(self, result_file_path: str) -> Dict[str, Any]:
        """Parse query results from user-provided file.

        It parses results with QUERY_NAME_START/END markers and supports
        both pipe-separated and tab-separated formats.

        Args:
            result_file_path: Path to file containing query results

        Returns:
            Dictionary mapping query names to result data in standard format
        """
        # Validate path to prevent path traversal attacks
        # Use absolute path and check for path traversal patterns
        if '..' in result_file_path:
            raise ValueError(f'Path traversal detected in result file path: {result_file_path}')

        result_file_path = os.path.abspath(result_file_path)

        if not os.path.exists(result_file_path):
            raise FileNotFoundError(f'Result file not found: {result_file_path}')

        with open(result_file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        results = {}
        current_query = None
        current_headers = []
        current_data = []

        lines = content.split('\n')
        i = 0

        while i < len(lines):
            line = lines[i].strip()

            # Skip empty lines
            if not line:
                if current_query and current_data:
                    results[current_query] = {
                        'description': f'Results for {current_query}',
                        'data': current_data,
                    }
                    current_query = None
                    current_headers = []
                    current_data = []
                i += 1
                continue

            # Check for query name markers
            if line.startswith('--'):
                if 'QUERY_NAME_START:' in line:
                    # Save previous query if exists
                    if current_query and current_data:
                        results[current_query] = {
                            'description': f'Results for {current_query}',
                            'data': current_data,
                        }
                    # Extract query name from marker
                    current_query = line.split('QUERY_NAME_START:')[1].strip()
                    current_headers = []
                    current_data = []
                elif 'QUERY_NAME_END:' in line:
                    # Save current query results (even if empty)
                    if current_query:
                        results[current_query] = {
                            'description': f'Results for {current_query}',
                            'data': current_data,
                        }
                        current_query = None
                        current_headers = []
                        current_data = []
                i += 1
                continue

            # Skip separator lines
            if all(c in '-+| ' for c in line):
                i += 1
                continue

            # Skip row count lines
            if line.startswith('(') and 'row' in line.lower():
                i += 1
                continue

            # Parse data row (support both tab and pipe separated)
            if '\t' in line:
                values = [v.strip() for v in line.split('\t')]
            elif '|' in line:
                parts = line.split('|')
                if parts and not parts[0].strip():
                    parts = parts[1:]
                if parts and not parts[-1].strip():
                    parts = parts[:-1]
                values = [v.strip() for v in parts]
            else:
                i += 1
                continue

            if not values:
                i += 1
                continue

            # Check if this is a marker row (from SELECT '-- QUERY_NAME_START: ...' AS marker)
            if len(values) > 0 and 'QUERY_NAME_START:' in values[0]:
                # Save previous query if exists
                if current_query and current_data:
                    results[current_query] = {
                        'description': f'Results for {current_query}',
                        'data': current_data,
                    }
                # Extract query name from marker value
                marker_text = values[0]
                if 'QUERY_NAME_START:' in marker_text:
                    current_query = marker_text.split('QUERY_NAME_START:')[1].strip()
                    current_headers = []
                    current_data = []
                i += 1
                continue
            elif len(values) > 0 and 'QUERY_NAME_END:' in values[0]:
                # Save current query results (even if empty)
                if current_query:
                    results[current_query] = {
                        'description': f'Results for {current_query}',
                        'data': current_data,
                    }
                    current_query = None
                    current_headers = []
                    current_data = []
                i += 1
                continue

            # First line is headers
            if not current_headers:
                current_headers = values
                # Skip if this is the marker column header
                if len(current_headers) == 1 and current_headers[0].lower() == 'marker':
                    current_headers = []
            else:
                # Data row
                if len(values) == len(current_headers):
                    row_dict = {}
                    for header, value in zip(current_headers, values):
                        if value.lower() in ['null', 'none', '']:
                            row_dict[header] = None
                        elif value.replace('.', '', 1).replace('-', '', 1).isdigit():
                            try:
                                if '.' in value:
                                    row_dict[header] = float(value)
                                else:
                                    row_dict[header] = int(value)
                            except ValueError:
                                row_dict[header] = value
                        else:
                            row_dict[header] = value
                    current_data.append(row_dict)

            i += 1

        # Save last query
        if current_query and current_data:
            results[current_query] = {
                'description': f'Results for {current_query}',
                'data': current_data,
            }

        return results

    @abstractmethod
    async def execute_managed_mode(self, connection_params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute analysis in managed mode (direct database connection).

        Args:
            connection_params: Database connection parameters

        Returns:
            Analysis result dictionary with results, errors, and metadata
        """
        pass

    def get_queries_by_category(self, category: str) -> list[str]:
        """Get list of query names for a specific category.

        Args:
            category: Query category ('information_schema', 'performance_schema', 'internal')

        Returns:
            List of query names in the specified category
        """
        queries = self.get_queries()
        return [
            query_name
            for query_name, query_info in queries.items()
            if query_info.get('category') == category
        ]

    def get_query_descriptions(self) -> Dict[str, str]:
        """Get mapping of query names to their descriptions.

        Returns:
            Dictionary mapping query names to human-readable descriptions
        """
        queries = self.get_queries()
        descriptions = {}
        for query_name, query_info in queries.items():
            # Skip internal queries (like performance_schema_check)
            if query_info.get('category') != 'internal':
                descriptions[query_name] = query_info.get(
                    'description', 'No description available'
                )
        return descriptions

    def get_schema_queries(self) -> list[str]:
        """Get list of schema-related query names."""
        return self.get_queries_by_category('information_schema')

    def get_performance_queries(self) -> list[str]:
        """Get list of performance-related query names."""
        return self.get_queries_by_category('performance_schema')
