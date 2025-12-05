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
"""awslabs MCP Server implementation for Amazon Keyspaces (for Apache Cassandra)."""

import sys
from typing import Any, Optional

from fastmcp import Context, FastMCP
from loguru import logger

from .client import UnifiedCassandraClient
from .config import AppConfig
from .consts import (
    MAX_DISPLAY_ROWS,
    SERVER_NAME,
    SERVER_VERSION,
    UNSAFE_OPERATIONS,
)
from .exceptions import (
    QueryExecutionError,
    QuerySecurityError,
    SchemaError,
    ValidationError,
)
from .llm_context import (
    build_keyspace_details_context,
    build_list_keyspaces_context,
    build_list_tables_context,
    build_query_analysis_context,
    build_query_result_context,
    build_table_details_context,
)
from .models import KeyspaceInput, QueryInput, TableInput
from .services import DataService, QueryAnalysisService, SchemaService


# Remove all default handlers then add our own
logger.remove()
logger.add(sys.stderr, level='INFO')


mcp = FastMCP(
    name=SERVER_NAME,
    version=SERVER_VERSION,
    instructions="""
# Amazon Keyspaces MCP Server

This MCP server enables interaction with Amazon Keyspaces (for Apache Cassandra) and Apache Cassandra databases through natural language.

## Available Tools

- **listKeyspaces**: Lists all keyspaces in the database
- **listTables**: Lists tables in a specific keyspace
- **describeKeyspace**: Gets detailed keyspace information including replication strategy
- **describeTable**: Gets table schema including columns, data types, and primary keys
- **executeQuery**: Executes read-only SELECT queries
- **analyzeQueryPerformance**: Analyzes query performance and provides optimization recommendations

## Usage Guidelines

1. Start by listing keyspaces to understand the database structure
2. Use describeTable to understand table schemas before querying
3. Only SELECT queries are permitted for data safety
4. Use analyzeQueryPerformance to optimize queries before execution

## Resources

- **keyspaces://developer-guide**: Complete developer guide with best practices
- **keyspaces://cql-reference**: CQL language reference for Keyspaces
- **keyspaces://api-reference**: AWS Keyspaces API documentation
- **keyspaces://streams-api**: Keyspaces Streams API reference
- **keyspaces://code-examples**: Sample code repository
""",
)


@mcp.resource('keyspaces://developer-guide')
def get_developer_guide() -> str:
    """Amazon Keyspaces Developer Guide with best practices and tutorials."""
    return """# Amazon Keyspaces Developer Guide

Complete guide for developing applications with Amazon Keyspaces.

**Documentation**: https://docs.aws.amazon.com/pdfs/keyspaces/latest/devguide/AmazonKeyspaces.pdf

## Key Topics

### Getting Started
- Setting up credentials and connections
- Creating keyspaces and tables
- Loading data

### Data Modeling
- Partition key design
- Clustering column strategies
- Denormalization patterns

### Performance
- Read/write capacity modes
- Auto-scaling configuration
- Query optimization

### Security
- IAM authentication
- Encryption at rest and in transit
- VPC endpoints

### Monitoring
- CloudWatch metrics
- CloudTrail logging
- Point-in-time recovery

Refer to the full PDF for detailed examples and best practices.
"""


@mcp.resource('keyspaces://cql-reference')
def get_cql_reference() -> str:
    """CQL language reference for Amazon Keyspaces."""
    return """# Amazon Keyspaces CQL Reference

Cassandra Query Language (CQL) syntax and operations supported by Keyspaces.

**Documentation**: https://docs.aws.amazon.com/pdfs/keyspaces/latest/devguide/AmazonKeyspaces.pdf

## Supported CQL Operations

### Data Definition (DDL)
- CREATE/ALTER/DROP KEYSPACE
- CREATE/ALTER/DROP TABLE
- CREATE/DROP INDEX

### Data Manipulation (DML)
- SELECT (with WHERE, ORDER BY, LIMIT)
- INSERT, UPDATE, DELETE
- BATCH operations

### Data Types
- Primitive: text, int, bigint, boolean, decimal, timestamp, uuid
- Collections: list, set, map
- Special: frozen, tuple

### Limitations
- No materialized views
- No user-defined functions
- No aggregate functions (COUNT, SUM)
- No TRUNCATE TABLE

See full PDF for complete syntax and examples.
"""


@mcp.resource('keyspaces://api-reference')
def get_api_reference() -> str:
    """AWS Keyspaces API Reference for management operations."""
    return """# Amazon Keyspaces API Reference

Complete API documentation for Amazon Keyspaces management operations.

**Documentation**: https://docs.aws.amazon.com/pdfs/keyspaces/latest/APIReference/keyspaces-api.pdf

## Key API Operations

### Keyspace Management
- CreateKeyspace, DeleteKeyspace, GetKeyspace, ListKeyspaces

### Table Management  
- CreateTable, DeleteTable, GetTable, UpdateTable, ListTables, RestoreTable

### Configuration
- GetTableAutoScalingSettings
- TagResource, UntagResource, ListTagsForResource

### Capacity Modes
- PAY_PER_REQUEST: Serverless, pay per request
- PROVISIONED: Fixed capacity with auto-scaling support

### Encryption
- AWS_OWNED_KMS_KEY (default)
- CUSTOMER_MANAGED_KMS_KEY

### Point-in-Time Recovery
- Continuous backups for up to 35 days
- Restore to any point within recovery window

For detailed schemas, parameters, and examples, refer to the full PDF documentation.
"""


@mcp.resource('keyspaces://streams-api')
def get_streams_api() -> str:
    """Amazon Keyspaces Streams API Reference for change data capture."""
    return """# Amazon Keyspaces Streams API Reference

API for capturing and processing change data from Keyspaces tables.

**Documentation**: https://docs.aws.amazon.com/pdfs/keyspaces/latest/StreamsAPIReference/keyspaces-streams-api.pdf

## Overview

Keyspaces Streams captures item-level changes (inserts, updates, deletes) in near real-time.

## Key Operations

### Stream Management
- GetRecords: Read change records from a stream
- DescribeStream: Get stream metadata
- ListStreams: List available streams

### Use Cases
- Real-time analytics
- Data replication
- Audit logging
- Event-driven architectures

### Integration
- AWS Lambda triggers
- Kinesis Data Streams
- Custom consumers

Refer to the full PDF for detailed API specifications and examples.
"""


@mcp.resource('keyspaces://code-examples')
def get_code_examples() -> str:
    """Amazon Keyspaces code examples and sample applications."""
    return """# Amazon Keyspaces Code Examples

Sample code and reference implementations for common use cases.

**Repository**: https://github.com/aws-samples/amazon-keyspaces-examples

## Available Examples

### Connection Patterns
- Python, Java, Node.js drivers
- IAM authentication
- SSL/TLS configuration

### Data Operations
- CRUD operations
- Batch processing
- Pagination

### Advanced Features
- Point-in-time recovery
- Auto-scaling setup
- Multi-region replication

### Integration Examples
- Lambda functions
- ECS/EKS deployments
- Spring Boot applications

Clone the repository for complete, runnable examples with detailed README files.
"""


@mcp.resource('cassandra://cql-reference')
def get_cassandra_cql_reference() -> str:
    """Apache Cassandra CQL reference documentation."""
    return """# Apache Cassandra CQL Reference

Complete CQL language reference for Apache Cassandra.

**Documentation**: https://cassandra.apache.org/doc/trunk/cassandra/developing/cql/index.html

## Key Sections

### CQL Basics
- Definitions: https://cassandra.apache.org/doc/trunk/cassandra/developing/cql/definitions.html
- Data Types: https://cassandra.apache.org/doc/trunk/cassandra/developing/cql/types.html

### Operations
- DDL (Data Definition): https://cassandra.apache.org/doc/trunk/cassandra/developing/cql/ddl.html
- DML (Data Manipulation): https://cassandra.apache.org/doc/trunk/cassandra/developing/cql/dml.html
- Operators: https://cassandra.apache.org/doc/trunk/cassandra/developing/cql/operators.html

### Advanced Features
- Indexing: https://cassandra.apache.org/doc/trunk/cassandra/developing/cql/indexing/indexing-concepts.html
- Materialized Views: https://cassandra.apache.org/doc/trunk/cassandra/developing/cql/mvs.html
- Functions: https://cassandra.apache.org/doc/trunk/cassandra/developing/cql/functions.html
- JSON Support: https://cassandra.apache.org/doc/trunk/cassandra/developing/cql/json.html

### Reference
- CQL Commands: https://cassandra.apache.org/doc/trunk/cassandra/reference/cql-commands/commands-toc.html
- Single File Reference: https://cassandra.apache.org/doc/trunk/cassandra/developing/cql/cql_singlefile.html
"""


@mcp.resource('cassandra://data-modeling')
def get_cassandra_data_modeling() -> str:
    """Apache Cassandra data modeling guide."""
    return """# Apache Cassandra Data Modeling

Comprehensive guide to data modeling in Cassandra.

**Documentation**: https://cassandra.apache.org/doc/trunk/cassandra/developing/data-modeling/index.html

## Key Topics

### Conceptual Modeling
- Introduction: https://cassandra.apache.org/doc/trunk/cassandra/developing/data-modeling/intro.html
- Concepts: https://cassandra.apache.org/doc/trunk/cassandra/developing/data-modeling/data-modeling_conceptual.html

### Design Process
- RDBMS Design: https://cassandra.apache.org/doc/trunk/cassandra/developing/data-modeling/data-modeling_rdbms.html
- Query Patterns: https://cassandra.apache.org/doc/trunk/cassandra/developing/data-modeling/data-modeling_queries.html
- Logical Modeling: https://cassandra.apache.org/doc/trunk/cassandra/developing/data-modeling/data-modeling_logical.html
- Physical Modeling: https://cassandra.apache.org/doc/trunk/cassandra/developing/data-modeling/data-modeling_physical.html

### Best Practices
- Evaluation: https://cassandra.apache.org/doc/trunk/cassandra/developing/data-modeling/data-modeling_refining.html
- Schema Definition: https://cassandra.apache.org/doc/trunk/cassandra/developing/data-modeling/data-modeling_schema.html
"""


# Global handle to hold the proxy to the specific database client
_PROXY = None


async def get_proxy():
    """Returns a singleton instance of the main Keyspaces MCP server implementation.

    The singleton is initialized lazily when first accessed (ensuring event loop is running).
    """
    global _PROXY  # pylint: disable=global-statement
    if _PROXY is None:
        # Load configuration
        app_config = AppConfig.from_env()

        # Initialize client
        cassandra_client = UnifiedCassandraClient(app_config.database_config)

        # Initialize services
        data_service = DataService(cassandra_client)
        schema_service = SchemaService(cassandra_client)
        query_analysis_service = QueryAnalysisService(cassandra_client, schema_service)

        _PROXY = KeyspacesMcpStdioServer(data_service, query_analysis_service, schema_service)

    return _PROXY


@mcp.tool(
    name='listKeyspaces',
    description='Lists all keyspaces in the Cassandra/Keyspaces database - args: none',
)
async def list_keyspaces(
    ctx: Optional[Context] = None,
) -> str:
    """Lists all keyspaces in the Cassandra/Keyspaces database."""
    proxy = await get_proxy()
    return await proxy._handle_list_keyspaces(ctx)  # pylint: disable=protected-access


@mcp.tool(
    name='listTables',
    description='Lists all tables in a specified keyspace - args: keyspace',
)
async def list_tables(
    input: KeyspaceInput,  # pylint: disable=redefined-builtin
    ctx: Optional[Context] = None,
) -> str:
    """Lists all tables in a specified keyspace."""
    proxy = await get_proxy()
    return await proxy._handle_list_tables(input.keyspace, ctx)  # pylint: disable=protected-access


@mcp.tool(
    name='describeKeyspace',
    description='Gets detailed information about a keyspace - args: keyspace',
)
async def describe_keyspace(
    input: KeyspaceInput,  # pylint: disable=redefined-builtin
    ctx: Optional[Context] = None,
) -> str:
    """Gets detailed information about a keyspace."""
    proxy = await get_proxy()
    return await proxy._handle_describe_keyspace(input.keyspace, ctx)  # pylint: disable=protected-access


@mcp.tool(
    name='describeTable',
    description='Gets detailed information about a table - args: keyspace, table',
)
async def describe_table(
    input: TableInput,  # pylint: disable=redefined-builtin
    ctx: Optional[Context] = None,
) -> str:
    """Gets detailed information about a table."""
    proxy = await get_proxy()
    return await proxy._handle_describe_table(input.keyspace, input.table, ctx)  # pylint: disable=protected-access


@mcp.tool(
    name='executeQuery',
    description='Executes a read-only SELECT query against the database - args: keyspace, query',
)
async def execute_query(
    input: QueryInput,  # pylint: disable=redefined-builtin
    ctx: Optional[Context] = None,
) -> str:
    """Executes a read-only (SELECT) query against the database."""
    proxy = await get_proxy()
    return await proxy._handle_execute_query(input.keyspace, input.query, ctx)  # pylint: disable=protected-access


@mcp.tool(
    name='analyzeQueryPerformance',
    description='Analyzes the performance characteristics of a CQL query - args: keyspace, query',
)
async def analyze_query_performance(
    input: QueryInput,  # pylint: disable=redefined-builtin
    ctx: Optional[Context] = None,
) -> str:
    """Analyzes the performance characteristics of a CQL query."""
    proxy = await get_proxy()
    return await proxy._handle_analyze_query_performance(  # pylint: disable=protected-access
        input.keyspace, input.query, ctx
    )


class KeyspacesMcpStdioServer:
    """MCP Server implementation that communicates via STDIO for Amazon Q CLI compatibility."""

    def __init__(
        self,
        data_service: DataService,
        query_analysis_service: QueryAnalysisService,
        schema_service: SchemaService,
    ):
        """Initialize the server with the given services."""
        self.data_service = data_service
        self.query_analysis_service = query_analysis_service
        self.schema_service = schema_service

    async def _handle_list_keyspaces(self, ctx: Optional[Any] = None) -> str:
        """Handle the listKeyspaces tool."""
        try:
            keyspaces = await self.schema_service.list_keyspaces()

            # Format keyspace names as a markdown list for better display
            keyspace_names = [k.name for k in keyspaces]
            formatted_text = '## Available Keyspaces\n\n'
            if keyspace_names:
                for name in keyspace_names:
                    formatted_text += f'- `{name}`\n'
            else:
                formatted_text += 'No keyspaces found.\n'

            # Add contextual information about Cassandra/Keyspaces
            if ctx:
                ctx.info(
                    'Adding contextual information about Cassandra/Keyspaces'
                )  # type: ignore[unused-coroutine]
                formatted_text += build_list_keyspaces_context(keyspaces)

            return formatted_text
        except Exception as e:
            logger.error(f'Error listing keyspaces: {str(e)}')
            raise SchemaError('Unable to retrieve keyspace information') from e

    async def _handle_list_tables(self, keyspace: str, ctx: Optional[Context] = None) -> str:
        """Handle the listTables tool."""
        try:
            if not keyspace:
                raise ValidationError('Keyspace name is required')

            tables = await self.schema_service.list_tables(keyspace)

            # Format table names as a markdown list for better display
            table_names = [t.name for t in tables]
            formatted_text = f'## Tables in Keyspace `{keyspace}`\n\n'
            if table_names:
                for name in table_names:
                    formatted_text += f'- `{name}`\n'
            else:
                formatted_text += 'No tables found in this keyspace.\n'

            # Add contextual information about tables in Cassandra
            if ctx:
                ctx.info(
                    f'Adding contextual information about tables in keyspace {keyspace}'
                )  # type: ignore[unused-coroutine]
                formatted_text += build_list_tables_context(keyspace, tables)

            return formatted_text
        except Exception as e:
            logger.error(f'Error listing tables: {str(e)}')
            raise SchemaError('Unable to retrieve table information') from e

    async def _handle_describe_keyspace(
        self, keyspace: str, ctx: Optional[Context] = None
    ) -> str:
        """Handle the describeKeyspace tool."""
        try:
            if not keyspace:
                raise ValidationError('Keyspace name is required')

            keyspace_details = await self.schema_service.describe_keyspace(keyspace)

            # Format keyspace details as markdown
            formatted_text = f'## Keyspace: `{keyspace}`\n\n'

            # Add replication strategy
            replication = keyspace_details.get('replication', {})
            formatted_text += '### Replication\n\n'
            formatted_text += f'- **Strategy**: `{replication.get("class", "Unknown")}`\n'

            # Add replication factor or datacenter details
            if 'SimpleStrategy' in replication.get('class', ''):
                rf = replication.get("replication_factor", "Unknown")
                formatted_text += f'- **Replication Factor**: `{rf}`\n'
            elif 'NetworkTopologyStrategy' in replication.get('class', ''):
                formatted_text += '- **Datacenter Replication**:\n'
                for dc, factor in replication.items():
                    if dc != 'class':
                        formatted_text += f'  - `{dc}`: `{factor}`\n'

            # Add durable writes
            durable_writes = keyspace_details.get('durable_writes', True)
            formatted_text += f'\n- **Durable Writes**: `{durable_writes}`\n'

            # Add contextual information about replication strategies
            if ctx:
                ctx.info(
                    'Adding contextual information about replication strategies'
                )  # type: ignore[unused-coroutine]
                formatted_text += build_keyspace_details_context(keyspace_details)

            return formatted_text
        except Exception as e:
            logger.error(f'Error describing keyspace: {str(e)}')
            raise SchemaError('Unable to retrieve keyspace details') from e

    async def _handle_describe_table(
        self, keyspace: str, table: str, ctx: Optional[Context] = None
    ) -> str:
        """Handle the describeTable tool."""
        try:
            if not keyspace:
                raise ValidationError('Keyspace name is required')

            if not table:
                raise ValidationError('Table name is required')

            table_details = await self.schema_service.describe_table(keyspace, table)

            # Format table details as markdown
            formatted_text = f'## Table: `{keyspace}.{table}`\n\n'

            # Add columns section
            formatted_text += '### Columns\n\n'
            formatted_text += '| Name | Type | Kind |\n'
            formatted_text += '|------|------|------|\n'

            columns = table_details.get('columns', [])
            for column in columns:
                col_name = column.get('name', 'Unknown')
                col_type = column.get('type', 'Unknown')
                col_kind = column.get('kind')

                formatted_text += f'| `{col_name}` | `{col_type}` | `{col_kind}` |\n'

            # Add primary key section
            formatted_text += '\n### Primary Key\n\n'

            partition_key = table_details.get('partition_key', [])
            clustering_columns = table_details.get('clustering_columns', [])

            formatted_text += '**Partition Key**:\n'
            if partition_key:
                for pk in partition_key:
                    formatted_text += f'- `{pk}`\n'
            else:
                formatted_text += '- None defined\n'

            formatted_text += '\n**Clustering Columns**:\n'
            if clustering_columns:
                for cc in clustering_columns:
                    formatted_text += f'- `{cc}`\n'
            else:
                formatted_text += '- None defined\n'

            # Add table options if available
            if 'options' in table_details:
                formatted_text += '\n### Table Options\n\n'
                options = table_details.get('options', {})
                for option_name, option_value in options.items():
                    formatted_text += f'- **{option_name}**: `{option_value}`\n'

            # Add contextual information about Cassandra data types and primary keys
            if ctx:
                ctx.info(
                    'Adding contextual information about Cassandra data types and '
                    'primary keys'
                )  # type: ignore[unused-coroutine]
                formatted_text += build_table_details_context(table_details)

            return formatted_text
        except Exception as e:
            logger.error(f'Error describing table: {str(e)}')
            raise SchemaError('Unable to retrieve table details') from e

    async def _handle_execute_query(
        self, keyspace: str, query: str, ctx: Optional[Context] = None
    ) -> str:
        """Handle the executeQuery tool."""
        try:
            if not keyspace:
                raise ValidationError('Keyspace name is required')

            if not query:
                raise ValidationError('Query is required')

            # Validate that this is a read-only query
            trimmed_query = query.strip().lower()
            if not trimmed_query.startswith('select '):
                raise QuerySecurityError('Only SELECT queries are allowed for read-only execution')

            # Check for any modifications that might be disguised as SELECT
            if any(op in trimmed_query for op in UNSAFE_OPERATIONS):
                raise QuerySecurityError('Query contains potentially unsafe operations')

            # Execute the query using the DataService
            query_results = await self.data_service.execute_read_only_query(keyspace, query)

            # Format the results for display
            formatted_text = '## Query Results\n\n'
            formatted_text += f'**Query:** `{query}`\n\n'

            columns = query_results.get('columns', [])
            rows = query_results.get('rows', [])
            row_count = query_results.get('row_count', 0)

            formatted_text += f'**Row Count:** {row_count}\n\n'

            if row_count > 0:
                # Create a markdown table for the results
                # Header row
                formatted_text += '| ' + ' | '.join(columns) + ' |\n'

                # Separator row
                formatted_text += '| ' + ' | '.join(['---'] * len(columns)) + ' |\n'

                # Data rows (limit to first few rows for readability)
                display_limit = min(len(rows), MAX_DISPLAY_ROWS)
                for i in range(display_limit):
                    row = rows[i]
                    row_values = []
                    for column in columns:
                        value = row.get(column)
                        row_values.append('null' if value is None else str(value))
                    formatted_text += '| ' + ' | '.join(row_values) + ' |\n'

                # Add note if results were truncated
                if len(rows) > display_limit:
                    note = (
                        f'\n_Note: Showing {display_limit} of {len(rows)} total rows. '
                        'Use LIMIT in your query to restrict results._'
                    )
                    formatted_text += note
            else:
                formatted_text += 'No rows returned.'

            # Add contextual information about CQL queries
            if ctx:
                ctx.info(
                    'Adding contextual information about CQL queries'
                )  # type: ignore[unused-coroutine]
                formatted_text += build_query_result_context(query_results)

            return formatted_text
        except (ValidationError, QuerySecurityError):
            raise
        except Exception as e:
            logger.error(f'Error executing query: {str(e)}')
            raise QueryExecutionError('Unable to execute query') from e

    async def _handle_analyze_query_performance(
        self, keyspace: str, query: str, ctx: Optional[Context] = None
    ) -> str:
        """Handle the analyzeQueryPerformance tool."""
        try:
            if not keyspace:
                raise ValidationError('Keyspace name is required')

            if not query:
                raise ValidationError('Query is required')

            analysis_result = await self.query_analysis_service.analyze_query(keyspace, query)

            # Build a user-friendly response
            formatted_text = '## Query Analysis Results\n\n'
            formatted_text += f'**Query:** `{query}`\n\n'
            formatted_text += f'**Table:** `{analysis_result.table_name}`\n\n'
            formatted_text += '### Performance Assessment\n\n'
            formatted_text += f'{analysis_result.performance_assessment}\n\n'

            if analysis_result.recommendations:
                formatted_text += '### Recommendations\n\n'
                for recommendation in analysis_result.recommendations:
                    formatted_text += f'- {recommendation}\n'

            # Add contextual information about query performance in Cassandra
            if ctx:
                ctx.info(
                    'Adding contextual information about query performance in Cassandra'
                )  # type: ignore[unused-coroutine]
                formatted_text += build_query_analysis_context(analysis_result)

            return formatted_text
        except ValidationError:
            raise
        except Exception as e:
            logger.error(f'Error analyzing query: {str(e)}')
            raise QueryExecutionError('Unable to analyze query') from e


def main():
    """Run the MCP server."""
    import asyncio  # pylint: disable=import-outside-toplevel

    # Validate connection before starting server
    try:
        proxy = asyncio.run(get_proxy())
        asyncio.run(proxy.schema_service.cassandra_client.get_session())
        logger.success('Successfully validated database connection')
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.error(f'Failed to connect to database: {e}')
        sys.exit(1)

    mcp.run()


if __name__ == '__main__':
    main()
