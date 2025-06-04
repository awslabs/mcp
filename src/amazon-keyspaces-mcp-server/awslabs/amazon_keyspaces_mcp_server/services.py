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
"""Service classes for Keyspaces MCP Server."""

import logging
import re
from .client import UnifiedCassandraClient
from .models import KeyspaceInfo, QueryAnalysisResult, TableInfo
from typing import Any, Dict, List


logger = logging.getLogger(__name__)


class DataService:
    """Service for data access operations: currently read-only operations are allowed."""

    def __init__(self, cassandra_client: UnifiedCassandraClient):
        """Initialize the service with the given client."""
        self.cassandra_client = cassandra_client
        logger.info(
            f'SchemaService initialized. Using Keyspaces: {cassandra_client.is_using_keyspaces()}'
        )

    def execute_read_only_query(self, keyspace_name: str, query: str) -> Dict[str, Any]:
        """Execute a read-only SELECT query against the database."""
        logger.info(f'Executing read-only query on keyspace {keyspace_name}: {query}')

        # If keyspace is specified, qualify the query with the keyspace
        full_query = query
        if keyspace_name:
            # Check if the query already has a keyspace qualifier
            if not re.search(r'from\s+' + re.escape(keyspace_name.lower()) + r'\.', query.lower()):
                # Simple heuristic to add keyspace qualifier
                # This is a basic implementation and might not handle all CQL syntax variations
                from_index = query.lower().find('from ')
                if from_index >= 0:
                    table_name_start = from_index + 5  # "from " is 5 chars
                    while table_name_start < len(query) and query[table_name_start].isspace():
                        table_name_start += 1

                    # Find the end of the table name
                    table_name_end = table_name_start
                    while (
                        table_name_end < len(query)
                        and not query[table_name_end].isspace()
                        and query[table_name_end] not in ('(', ';')
                    ):
                        table_name_end += 1

                    if table_name_start < table_name_end:
                        table_name = query[table_name_start:table_name_end]
                        # Only add keyspace if the table name doesn't already have one
                        if '.' not in table_name:
                            full_query = (
                                query[:table_name_start]
                                + keyspace_name
                                + '.'
                                + query[table_name_start:]
                            )

        return self.cassandra_client.execute_read_only_query(full_query)


class SchemaService:
    """Service for schema-related operations."""

    def __init__(self, cassandra_client: UnifiedCassandraClient):
        """Initialize the service with the given client."""
        self.cassandra_client = cassandra_client
        logger.info(
            f'SchemaService initialized. Using Keyspaces: {cassandra_client.is_using_keyspaces()}'
        )

    def list_keyspaces(self) -> List[KeyspaceInfo]:
        """List all keyspaces in the database."""
        logger.info('Listing keyspaces')
        return self.cassandra_client.list_keyspaces()

    def list_tables(self, keyspace_name: str) -> List[TableInfo]:
        """List all tables in a keyspace."""
        logger.info(f'Listing tables for keyspace: {keyspace_name}')
        return self.cassandra_client.list_tables(keyspace_name)

    def describe_keyspace(self, keyspace_name: str) -> Dict[str, Any]:
        """Get detailed information about a keyspace."""
        logger.info(f'Describing keyspace: {keyspace_name}')
        return self.cassandra_client.describe_keyspace(keyspace_name)

    def describe_table(self, keyspace_name: str, table_name: str) -> Dict[str, Any]:
        """Get detailed information about a table."""
        logger.info(f'Describing table: {keyspace_name}.{table_name}')
        return self.cassandra_client.describe_table(keyspace_name, table_name)


class QueryAnalysisService:
    """Service for analyzing CQL query performance."""

    def __init__(self, cassandra_client: UnifiedCassandraClient, schema_service: SchemaService):
        """Initialize the service with the given client and schema service."""
        self.cassandra_client = cassandra_client
        self.schema_service = schema_service
        logger.info('QueryAnalysisService initialized')

    def analyze_query(self, keyspace_name: str, query: str) -> QueryAnalysisResult:
        """Analyze a CQL query for performance characteristics."""
        logger.info(f'Analyzing query for keyspace {keyspace_name}: {query}')

        result = QueryAnalysisResult(query=query)

        try:
            # Normalize query for analysis (remove extra whitespace, convert to lowercase for pattern matching)
            normalized_query = self._normalize_query(query)

            # Extract table name from the query
            table_name = self._extract_table_name(normalized_query)
            result.table_name = table_name

            if not table_name:
                result.performance_assessment = 'Unable to determine table name from query'
                result.recommendations.append(
                    'Ensure the query follows standard CQL SELECT syntax'
                )
                return result

            # Get table schema information
            tables = self.schema_service.list_tables(keyspace_name)
            table_info = next((t for t in tables if t.name.lower() == table_name.lower()), None)

            if not table_info:
                result.performance_assessment = (
                    f"Table '{table_name}' not found in keyspace '{keyspace_name}'"
                )
                result.recommendations.append('Verify the table name and keyspace are correct')
                return result

            # Get table details
            table_details = self.schema_service.describe_table(keyspace_name, table_name)

            # Extract WHERE conditions
            where_conditions = self._extract_where_conditions(normalized_query)

            # Check for ALLOW FILTERING
            uses_allow_filtering = 'allow filtering' in normalized_query
            result.uses_allow_filtering = uses_allow_filtering

            # Get partition key and clustering columns
            partition_key_columns = self._extract_partition_key_columns(table_details)
            clustering_columns = self._extract_clustering_columns(table_details)

            # Check if partition key is used in WHERE clause
            uses_partition_key = self._check_partition_key_usage(
                partition_key_columns, where_conditions
            )
            result.uses_partition_key = uses_partition_key

            # Check if clustering columns are used efficiently
            uses_clustering_columns = self._check_clustering_column_usage(
                clustering_columns, where_conditions
            )
            result.uses_clustering_columns = uses_clustering_columns

            # Check for secondary index usage
            uses_secondary_index = self._check_secondary_index_usage(
                table_details, where_conditions
            )
            result.uses_secondary_index = uses_secondary_index

            # Determine if this is a full table scan
            is_full_table_scan = not uses_partition_key and not uses_secondary_index
            result.is_full_table_scan = is_full_table_scan

            # Generate performance assessment
            self._generate_performance_assessment(
                result, partition_key_columns, clustering_columns
            )

            return result
        except Exception as e:
            logger.error(f'Error analyzing query: {str(e)}')
            result.performance_assessment = f'Error analyzing query: {str(e)}'
            return result

    def _normalize_query(self, query: str) -> str:
        """Normalize a query for analysis."""
        return query.strip().lower()

    def _extract_table_name(self, query: str) -> str:
        """Extract the table name from a query."""
        # Pattern to match table name in a SELECT query
        # This is a simplified approach and might need refinement for complex queries
        pattern = r'\s+from\s+([\w_\.]+)'
        match = re.search(pattern, query)

        if match:
            table_ref = match.group(1)
            # Handle cases where table is prefixed with keyspace name
            if '.' in table_ref:
                return table_ref.split('.', 1)[1]
            return table_ref

        return ''

    def _extract_where_conditions(self, query: str) -> List[str]:
        """Extract WHERE conditions from a query."""
        conditions = []

        # Check if query has WHERE clause
        where_index = query.find(' where ')
        if where_index == -1:
            return conditions

        # Extract the WHERE clause
        where_clause = query[where_index + 7 :]

        # Remove any ORDER BY, LIMIT, ALLOW FILTERING clauses
        where_clause = re.sub(r'\s+order\s+by\s+.*', '', where_clause)
        where_clause = re.sub(r'\s+limit\s+.*', '', where_clause)
        where_clause = re.sub(r'\s+allow\s+filtering.*', '', where_clause)

        # Split by AND to get individual conditions
        parts = re.split(r'\s+and\s+', where_clause)

        for part in parts:
            # Extract column name from condition
            # This is a simplified approach and might need refinement for complex conditions
            condition_parts = re.split(r'\s*[=<>]\s*', part)
            if condition_parts:
                conditions.append(condition_parts[0].strip())

        return conditions

    def _extract_partition_key_columns(self, table_details: Dict[str, Any]) -> List[str]:
        """Extract partition key columns from table details."""
        partition_keys = []

        # Extract partition key columns from table details
        columns = table_details.get('columns', [])

        for column in columns:
            if column.get('is_partition_key'):
                partition_keys.append(column.get('name'))

        return partition_keys

    def _extract_clustering_columns(self, table_details: Dict[str, Any]) -> List[str]:
        """Extract clustering columns from table details."""
        clustering_columns = []

        # Extract clustering columns from table details
        columns = table_details.get('columns', [])

        for column in columns:
            if column.get('is_clustering_column'):
                clustering_columns.append(column.get('name'))

        return clustering_columns

    def _check_partition_key_usage(
        self, partition_key_columns: List[str], where_conditions: List[str]
    ) -> bool:
        """Check if all partition key columns are used in WHERE conditions."""
        return all(
            pk.lower() in [cond.lower() for cond in where_conditions]
            for pk in partition_key_columns
        )

    def _check_clustering_column_usage(
        self, clustering_columns: List[str], where_conditions: List[str]
    ) -> bool:
        """Check if any clustering columns are used in WHERE conditions."""
        return any(
            cc.lower() in [cond.lower() for cond in where_conditions] for cc in clustering_columns
        )

    def _check_secondary_index_usage(
        self, table_details: Dict[str, Any], where_conditions: List[str]
    ) -> bool:
        """Check if any secondary indexes are used in WHERE conditions."""
        indexes = table_details.get('indexes', [])

        if not indexes:
            return False

        for index in indexes:
            options = index.get('options', {})
            if 'target' in options:
                # Extract column name from target
                target = options['target']
                column_match = re.search(r'^\"?([^\"]+)\"?', target)
                if column_match:
                    indexed_column = column_match.group(1)
                    if indexed_column.lower() in [cond.lower() for cond in where_conditions]:
                        return True

        return False

    def _generate_performance_assessment(
        self,
        result: QueryAnalysisResult,
        partition_key_columns: List[str],
        clustering_columns: List[str],
    ) -> None:
        """Generate a performance assessment for a query."""
        assessment = []

        # Assess based on partition key usage
        if not result.uses_partition_key:
            assessment.append(
                'HIGH COST QUERY: This query does not filter on all partition key columns. '
                'It will require scanning multiple partitions, which is expensive in Cassandra/Keyspaces.\n'
            )

            result.recommendations.append(
                f'Include all partition key columns in your WHERE clause: {", ".join(partition_key_columns)}'
            )
        else:
            assessment.append(
                'EFFICIENT PARTITION KEY USAGE: This query correctly filters on all partition key columns, '
                'which allows Cassandra to efficiently locate the relevant data partitions.\n'
            )

        # Assess based on clustering column usage
        if not result.uses_clustering_columns and clustering_columns:
            assessment.append(
                'POTENTIAL OPTIMIZATION: This query does not filter on any clustering columns. '
                'Adding filters on clustering columns can further improve performance by reducing the amount of data read within partitions.\n'
            )

            result.recommendations.append(
                f'Consider adding filters on clustering columns when possible: {", ".join(clustering_columns)}'
            )
        elif result.uses_clustering_columns:
            assessment.append(
                'EFFICIENT CLUSTERING COLUMN USAGE: This query filters on clustering columns, '
                'which helps Cassandra efficiently locate data within partitions.\n'
            )

        # Assess based on ALLOW FILTERING usage
        if result.uses_allow_filtering:
            assessment.append(
                'WARNING - ALLOW FILTERING: This query uses ALLOW FILTERING, which can be extremely expensive '
                'as it may force Cassandra to scan and filter large amounts of data.\n'
            )

            result.recommendations.append('Avoid using ALLOW FILTERING in production environments')
            result.recommendations.append(
                'Consider creating a secondary index for the filtered columns or redesign your data model'
            )

        # Assess based on secondary index usage
        if result.uses_secondary_index:
            assessment.append(
                'SECONDARY INDEX USAGE: This query uses a secondary index. '
                'Secondary indexes in Cassandra are not as efficient as in relational databases '
                'and may still require scanning multiple partitions.\n'
            )

            result.recommendations.append(
                'Monitor the performance of queries using secondary indexes'
            )
            result.recommendations.append(
                'Consider denormalizing your data model instead of relying on secondary indexes for frequently used queries'
            )

        # Assess based on full table scan
        if result.is_full_table_scan:
            assessment.append(
                'CRITICAL PERFORMANCE ISSUE - FULL TABLE SCAN: This query will perform a full table scan, '
                'which is extremely expensive in Cassandra/Keyspaces and should be avoided in production.\n'
            )

            result.recommendations.append('Redesign your query to include partition key filters')
            result.recommendations.append(
                'Consider creating a materialized view or a new table with a different primary key structure'
            )

        result.performance_assessment = '\n'.join(assessment)
