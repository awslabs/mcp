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
from .client import UnifiedCassandraClient
from .config import AppConfig
from .consts import (
    MAX_DISPLAY_ROWS,
    SERVER_NAME,
    SERVER_VERSION,
    UNSAFE_OPERATIONS,
)
from .llm_context import (
    build_keyspace_details_context,
    build_list_keyspaces_context,
    build_list_tables_context,
    build_query_analysis_context,
    build_query_result_context,
    build_table_details_context,
)
from .services import DataService, QueryAnalysisService, SchemaService
from loguru import logger
from mcp.server.fastmcp import Context, FastMCP
from pydantic import Field
from typing import Any, Optional


# Remove all default handlers then add our own
logger.remove()
logger.add(sys.stderr, level='INFO')

mcp = FastMCP(name=SERVER_NAME, version=SERVER_VERSION)

# Global handle to hold the proxy to the specific db client
_proxy = None


def get_proxy():
    """Returns a singleton instance of the main Keyspaces MCP server implementation.

    The singleton is initialized lazily.
    """
    global _proxy
    if _proxy is None:
        # Load configuration
        app_config = AppConfig.from_env()

        # Initialize client
        cassandra_client = UnifiedCassandraClient(app_config.database_config)

        # Initialize services
        data_service = DataService(cassandra_client)
        schema_service = SchemaService(cassandra_client)
        query_analysis_service = QueryAnalysisService(cassandra_client, schema_service)

        _proxy = KeyspacesMcpStdioServer(data_service, query_analysis_service, schema_service)

    return _proxy


@mcp.tool(
    name='listKeyspaces',
    description='Lists all keyspaces in the Cassandra/Keyspaces database - args: none',
)
def list_keyspaces(
    ctx: Optional[Context] = None,
) -> str:
    """Lists all keyspaces in the Cassandra/Keyspaces database."""
    return get_proxy().handle_list_keyspaces(ctx)


@mcp.tool(
    name='listTables',
    description='Lists all tables in a specified keyspace - args: keyspace',
)
def list_tables(
    keyspace: str = Field(..., description='The keyspace to list tables from.'),
    ctx: Optional[Context] = None,
) -> str:
    """Lists all tables in a specified keyspace."""
    return get_proxy()._handle_list_tables(keyspace, ctx)


@mcp.tool(
    name='describeKeyspace',
    description='Gets detailed information about a keyspace - args: keyspace',
)
def describe_keyspace(
    keyspace: str = Field(..., description='The keyspace to retrieve metadata for.'),
    ctx: Optional[Context] = None,
) -> str:
    """Gets detailed information about a keyspace."""
    return get_proxy()._handle_describe_keyspace(keyspace, ctx)


@mcp.tool(
    name='describeTable',
    description='Gets detailed information about a table - args: keyspace, table',
)
def describe_table(
    keyspace: str = Field(..., description='The keyspace containing the table'),
    table: str = Field(..., description='The name of the table to describe'),
    ctx: Optional[Context] = None,
) -> str:
    """Gets detailed information about a table."""
    return get_proxy()._handle_describe_table(keyspace, table, ctx)


@mcp.tool(
    name='executeQuery',
    description='Executes a read-only SELECT query against the database - args: keyspace, query',
)
def execute_query(
    keyspace: str = Field(..., description='The keyspace to execute the query against'),
    query: str = Field(..., description='The CQL SELECT query to execute'),
    ctx: Optional[Context] = None,
) -> str:
    """Executes a read-only (SELECT) query against the database."""
    return get_proxy()._handle_execute_query(keyspace, query, ctx)


@mcp.tool(
    name='analyzeQueryPerformance',
    description='Analyzes the performance characteristics of a CQL query - args: keyspace, query',
)
def analyze_query_performance(
    keyspace: str = Field(..., description='The keyspace to analyze the query against'),
    query: str = Field(..., description='The CQL query to analyze for performance'),
    ctx: Optional[Context] = None,
) -> str:
    """Analyzes the performance characteristics of a CQL query."""
    return get_proxy()._handle_analyze_query_performance(keyspace, query, ctx)


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

    def handle_list_keyspaces(self, ctx: Optional[Any] = None) -> str:
        """Handle the listKeyspaces tool."""
        try:
            keyspaces = self.schema_service.list_keyspaces()

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
                ctx.info('Adding contextual information about Cassandra/Keyspaces')  # type: ignore[unused-coroutine]
                formatted_text += build_list_keyspaces_context(keyspaces)

            return formatted_text
        except Exception as e:
            logger.error(f'Error listing keyspaces: {str(e)}')
            raise Exception(f'Error listing keyspaces: {str(e)}')

    def _handle_list_tables(self, keyspace: str, ctx: Optional[Context] = None) -> str:
        """Handle the listTables tool."""
        try:
            if not keyspace:
                raise Exception('Keyspace name is required')

            tables = self.schema_service.list_tables(keyspace)

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
                ctx.info(f'Adding contextual information about tables in keyspace {keyspace}')  # type: ignore[unused-coroutine]
                formatted_text += build_list_tables_context(keyspace, tables)

            return formatted_text
        except Exception as e:
            logger.error(f'Error listing tables: {str(e)}')
            raise Exception(f'Error listing tables: {str(e)}')

    def _handle_describe_keyspace(self, keyspace: str, ctx: Optional[Context] = None) -> str:
        """Handle the describeKeyspace tool."""
        try:
            if not keyspace:
                raise Exception('Keyspace name is required')

            keyspace_details = self.schema_service.describe_keyspace(keyspace)

            # Format keyspace details as markdown
            formatted_text = f'## Keyspace: `{keyspace}`\n\n'

            # Add replication strategy
            replication = keyspace_details.get('replication', {})
            formatted_text += '### Replication\n\n'
            formatted_text += f'- **Strategy**: `{replication.get("class", "Unknown")}`\n'

            # Add replication factor or datacenter details
            if 'SimpleStrategy' in replication.get('class', ''):
                formatted_text += f'- **Replication Factor**: `{replication.get("replication_factor", "Unknown")}`\n'
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
                ctx.info('Adding contextual information about replication strategies')  # type: ignore[unused-coroutine]
                formatted_text += build_keyspace_details_context(keyspace_details)

            return formatted_text
        except Exception as e:
            logger.error(f'Error describing keyspace: {str(e)}')
            raise Exception(f'Error describing keyspace: {str(e)}')

    def _handle_describe_table(
        self, keyspace: str, table: str, ctx: Optional[Context] = None
    ) -> str:
        """Handle the describeTable tool."""
        try:
            if not keyspace:
                raise Exception('Keyspace name is required')

            if not table:
                raise Exception('Table name is required')

            table_details = self.schema_service.describe_table(keyspace, table)

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
                    'Adding contextual information about Cassandra data types and primary keys'
                )  # type: ignore[unused-coroutine]
                formatted_text += build_table_details_context(table_details)

            return formatted_text
        except Exception as e:
            logger.error(f'Error describing table: {str(e)}')
            raise Exception(f'Error describing table: {str(e)}')

    def _handle_execute_query(
        self, keyspace: str, query: str, ctx: Optional[Context] = None
    ) -> str:
        """Handle the executeQuery tool."""
        try:
            if not keyspace:
                raise Exception('Keyspace name is required')

            if not query:
                raise Exception('Query is required')

            # Validate that this is a read-only query
            trimmed_query = query.strip().lower()
            if not trimmed_query.startswith('select '):
                raise Exception('Only SELECT queries are allowed for read-only execution')

            # Check for any modifications that might be disguised as SELECT
            if any(op in trimmed_query for op in UNSAFE_OPERATIONS):
                raise Exception('Query contains potentially unsafe operations')

            # Execute the query using the DataService
            query_results = self.data_service.execute_read_only_query(keyspace, query)

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
                    formatted_text += f'\n_Note: Showing {display_limit} of {len(rows)} total rows. Use LIMIT in your query to restrict results._'
            else:
                formatted_text += 'No rows returned.'

            # Add contextual information about CQL queries
            if ctx:
                ctx.info('Adding contextual information about CQL queries')  # type: ignore[unused-coroutine]
                formatted_text += build_query_result_context(query_results)

            return formatted_text
        except ValueError as e:
            # This is thrown for non-SELECT queries
            logger.warning(f'Invalid query attempt: {str(e)}')
            raise Exception(str(e))
        except Exception as e:
            logger.error(f'Error executing query: {str(e)}')
            raise Exception(f'Error executing query: {str(e)}')

    def _handle_analyze_query_performance(
        self, keyspace: str, query: str, ctx: Optional[Context] = None
    ) -> str:
        """Handle the analyzeQueryPerformance tool."""
        try:
            if not keyspace:
                raise Exception('Keyspace name is required')

            if not query:
                raise Exception('Query is required')

            analysis_result = self.query_analysis_service.analyze_query(keyspace, query)

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
                ctx.info('Adding contextual information about query performance in Cassandra')  # type: ignore[unused-coroutine]
                formatted_text += build_query_analysis_context(analysis_result)

            return formatted_text
        except Exception as e:
            logger.error(f'Error analyzing query: {str(e)}')
            raise Exception(f'Error analyzing query: {str(e)}')


def main():
    """Run the MCP server."""
    mcp.run()


if __name__ == '__main__':
    main()
