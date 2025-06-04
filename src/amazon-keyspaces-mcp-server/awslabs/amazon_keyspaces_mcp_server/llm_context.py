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
"""LLM context builder for Keyspaces MCP Server."""

from .models import KeyspaceInfo, QueryAnalysisResult, TableInfo
from typing import Any, Dict, List


def build_list_keyspaces_context(keyspaces: List[KeyspaceInfo]) -> str:
    """Provide LLM context for Amazon Keyspaces and Apache Cassandra."""
    context = {
        'cassandra_knowledge': build_cassandra_knowledge(),
        'amazon_keyspaces_knowledge': build_amazon_keyspaces_knowledge(),
    }

    # Add keyspace-specific guidance
    list_keyspaces_guidance = {
        'compatibility': 'Amazon Keyspaces is compatible with Apache Cassandra 3.11. This means that it supports most '
        'of the same CQL language features and is driver-protocol compatible with Cassandra 3.11.',
        'limitations': "Amazon Keyspaces doesn't support all Apache Cassandra 3.11 features. Unsupported features "
        'include logged batches, materialized views, indexes, aggregate functions like COUNT and SUM, prepared '
        'statements for DDL operations, DROP COLUMN, TRUNCATE TABLE, user-defined functions, the inequality operator '
        'for user-defined types, or the IN keyword in INSERT and UPDATE statements. Keyspaces uses AWS IAM for '
        "authentication and authorization, and not Cassandra's security configuration and commands. Additionally, "
        'some operations that are synchronous in Cassandra are asynchronous in Keyspaces, such as DDL operations '
        'and range delete operations.',
        'replication_strategy': 'In Cassandra, common replication strategies include SimpleStrategy and NetworkTopologyStrategy. '
        'Amazon Keyspaces uses a single-region replication strategy with 3x replication for durability.',
        'naming_conventions': 'Keyspace names typically use snake_case and represent logical data domains.',
    }
    context['list_keyspaces_guidance'] = list_keyspaces_guidance

    return dict_to_markdown(context)


def build_list_tables_context(keyspace_name: str, tables: List[TableInfo]) -> str:
    """Provide LLM context for tables."""
    context = {
        'cassandra_knowledge': build_cassandra_knowledge(),
        'amazon_keyspaces_knowledge': build_amazon_keyspaces_knowledge(),
    }

    # Add table-specific guidance
    tables_guidance = {
        'data_modeling': 'In Cassandra, tables are containers for related data, similar to tablesin relational databases. '
        'However, Cassandra tables  are optimized for specific access patterns based on their primary key '
        'design. The primary key determines how data is distributed physically in the database, and the '
        'attributes that can be specified for efficient query execution. Primary keys consist of a '
        'partition key (which determines data distribution) and optional cluster columns which determine '
        'how data is ordered within a partition.',
        'naming_conventions': 'Table names typically use snake_case and should be descriptive of the entity they represent.',
    }
    context['tables_guidance'] = tables_guidance

    return dict_to_markdown(context)


def build_keyspace_details_context(keyspace_details: Dict[str, Any]) -> str:
    """Provide LLM context for keyspace details."""
    context = {
        'cassandra_knowledge': build_cassandra_knowledge(),
        'amazon_keyspaces_knowledge': build_amazon_keyspaces_knowledge(),
    }

    # Add keyspace-specific guidance
    keyspace_guidance = {
        'replication_strategy': 'Replication strategy determines how data is distributed across nodes. '
        'Amazon Keyspaces manages replication automatically for high availability.',
        'durable_writes': 'Durable writes ensure data is written to the commit log before acknowledging the write. '
        'This provides durability in case of node failures.',
    }
    context['keyspace_guidance'] = keyspace_guidance

    return dict_to_markdown(context)


def build_table_details_context(table_details: Dict[str, Any]) -> str:
    """Provide LLM context for table details."""
    context = {
        'cassandra_knowledge': build_cassandra_knowledge(),
        'amazon_keyspaces_knowledge': build_amazon_keyspaces_knowledge(),
    }

    # Check if there's already Keyspaces-specific context
    if '_keyspaces_context' in table_details:
        # Use the context provided by the client
        context['service_characteristics'] = table_details['_keyspaces_context'].get(
            'service_characteristics'
        )

        # Remove it from the public data
        table_details.pop('_keyspaces_context')

    # Add table-specific guidance
    table_guidance = {
        'partition_key': 'Partition keys determine data distribution across the cluster. '
        'Queries are most efficient when they include the partition key.',
        'clustering_columns': 'Clustering columns determine the sort order within a partition. '
        'They enable range queries within a partition.',
        'secondary_indexes': 'Secondary indexes should be used sparingly in Cassandra. '
        'They are best for low-cardinality columns and can impact write performance.',
    }
    context['table_guidance'] = table_guidance

    return dict_to_markdown(context)


def build_query_result_context(query_results: Dict[str, Any]) -> str:
    """Provide LLM context for query results."""
    context = {
        'cassandra_knowledge': build_cassandra_knowledge(),
        'amazon_keyspaces_knowledge': build_amazon_keyspaces_knowledge(),
    }

    # Add query-specific guidance
    query_guidance = {
        'performance_considerations': 'Cassandra queries are most efficient when they include the partition key. '
        'Queries without a partition key may require a full table scan, which can be '
        'inefficient for large tables.',
        'pagination': 'For large result sets, consider using pagination with the LIMIT clause and token-based paging '
        'to avoid loading too many rows in memory.',
        'consistency_level': 'The consistency level determines how many replicas must acknowledge a read request '
        'before returning data. Higher consistency levels provide stronger guarantees but may '
        'increase latency.',
    }

    context['query_guidance'] = query_guidance

    row_count = query_results.get('row_count', 0)

    result_guidance = {}
    if row_count == 0:
        result_guidance['empty_result'] = (
            'No rows were returned. This could mean either no matching data exists '
            'or the query conditions were too restrictive.'
        )
    elif row_count > 100:
        result_guidance['large_result'] = (
            'A large number of rows were returned. Consider adding more specific '
            'filtering conditions or using pagination for better performance.'
        )

    context['result_guidance'] = result_guidance

    return dict_to_markdown(context)


def build_query_analysis_context(analysis_result: QueryAnalysisResult) -> str:
    """Provide LLM context for query analysis results."""
    context: Dict[str, Any] = {
        'cassandra knowledge': build_cassandra_knowledge(),
        'amazon keyspaces knowledge': build_amazon_keyspaces_knowledge(),
    }

    # Add query performance guidance
    performance_guidance = {
        'Partition key importance': "In Cassandra/Keyspaces, queries that don't filter on partition key require scanning all partitions, "
        + 'which is extremely expensive and should be avoided.',
        'clustering_column_usage': 'After partition keys, clustering columns should be used in WHERE clauses to further narrow down the data '
        + 'that needs to be read within a partition.',
        'allow_filtering_warning': 'The ALLOW FILTERING clause forces Cassandra to scan potentially all partitions, '
        + 'which is very inefficient and should be avoided in production.',
        'secondary_indexes': 'Secondary indexes in Cassandra are not as efficient as in relational databases. '
        + 'They still require reading from multiple partitions and should be used sparingly.',
        'full_table_scan': 'Full table scans in Cassandra are extremely expensive operations that should be avoided. '
        + 'Always design your data model and queries to avoid scanning entire tables.',
    }

    context['performance_guidance'] = performance_guidance

    # Add query-specific context
    query_context = {
        'uses_partition_key': analysis_result.uses_partition_key,
        'uses_clustering_columns': analysis_result.uses_clustering_columns,
        'uses_allow_filtering': analysis_result.uses_allow_filtering,
        'uses_secondary_index': analysis_result.uses_secondary_index,
        'is_full_table_scan': analysis_result.is_full_table_scan,
    }

    context['query_context'] = query_context

    return dict_to_markdown(context)


def build_cassandra_knowledge() -> Dict[str, str]:
    """Provide general Cassandra knowledge."""
    knowledge = {
        'data_model': 'Cassandra uses a wide-column store data model optimized for write performance and horizontal '
        'scalability.',
        'query_patterns': 'Cassandra is optimized for high write throughput and queries that specify the partition key.',
        'limitations': 'Cassandra has limited support for joins, aggregations, and transactions. '
        'Data modeling should denormalize data to support specific query patterns.',
        'keyspaces_vs_cassandra': 'Amazon Keyspaces is a managed Cassandra-compatible service with some differences '
        'in performance characteristics and feature support compared to self-managed'
        'Cassandra.',
    }

    return knowledge


def build_amazon_keyspaces_knowledge() -> Dict[str, str]:
    """Provide Amazon Keyspaces specific knowledge."""
    knowledge = {
        'compatibility': 'Amazon Keyspaces is compatible with Apache Cassandra 3.11. This means that it supports most '
        'of the same CQL language features and is driver-protocol compatible with Cassandra 3.11.',
        'differences_from_cassandra': "Amazon Keyspaces doesn't support all Apache Cassandra 3.11 features. Unsupported "
        'features include logged batches, materialized views, indexes, aggregate functions like COUNT and'
        'SUM, prepared statements for DDL operations, DROP COLUMN, TRUNCATE TABLE, user-defined functions,'
        'the inequality operator '
        'for user-defined types, or the IN keyword in INSERT and UPDATE statements. Keyspaces uses AWS IAM for '
        "authentication and authorization, and not Cassandra's security configuration and commands. Additionally, "
        'some operations that are synchronous in Cassandra are asynchronous in Keyspaces, such as DDL operations '
        'and range delete operations.',
    }

    return knowledge


def dict_to_markdown(data: Dict[str, Any], level: int = 0) -> str:
    """Convert a nested dictionary to a well-formatted Markdown string.

    Args:
        data: The dictionary to format
        level: The current nesting level (used for recursion)

    Returns:
        A formatted Markdown string
    """
    result = []

    # Process each key-value pair
    for key, value in data.items():
        # Format the key as a header (with appropriate level)
        # Convert snake_case to Title Case
        header_text = key.replace('_', ' ').title()
        header_level = min(level + 2, 6)  # H2 to H6 (avoid going beyond H6)
        header = '#' * header_level + ' ' + header_text

        # Process the value based on its type
        if isinstance(value, dict):
            # Recursively format nested dictionaries
            result.append(f'\n{header}\n')
            result.append(dict_to_markdown(value, level + 1))
        elif isinstance(value, (list, tuple)):
            # Format lists as bullet points
            result.append(f'\n{header}\n')
            for item in value:
                if isinstance(item, dict):
                    result.append(dict_to_markdown(item, level + 1))
                else:
                    result.append(f'- {item}\n')
        elif isinstance(value, bool):
            # Format booleans
            result.append(f'\n{header}: {"Yes" if value else "No"}\n')
        else:
            # Format strings and other types
            result.append(f'\n{header}\n\n{value}\n')

    return '\n'.join(result)
