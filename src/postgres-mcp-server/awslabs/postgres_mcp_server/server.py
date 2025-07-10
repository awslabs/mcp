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

"""PostgreSQL MCP Server implementation."""

import argparse
import asyncio
import sys
from .connection import ConnectionFactory, DBConnector
from .mutable_sql_detector import check_sql_injection_risk, detect_mutating_keywords
from loguru import logger
from mcp.server.fastmcp import Context, FastMCP
from pydantic import Field
from typing import Annotated, Any, Dict, List, Optional


async def fetch_table_schema(db_connection: DBConnector, table_name: str) -> List[Dict[str, Any]]:
    """
    Fetch table schema information from PostgreSQL.
    
    Args:
        db_connection: Database connection
        table_name: Name of the table to get schema for
        
    Returns:
        List of column information dictionaries
    """
    # SQL query to get table schema information
    query = """
    SELECT 
        a.attname as column_name,
        pg_catalog.format_type(a.atttypid, a.atttypmod) as data_type,
        (SELECT pg_catalog.col_description(c.oid, a.attnum) FROM pg_catalog.pg_class c 
         WHERE c.oid = a.attrelid AND c.relname = :table_name) as column_comment,
        a.attnotnull as is_not_null,
        CASE WHEN p.contype = 'p' THEN true ELSE false END as is_primary_key
    FROM 
        pg_catalog.pg_attribute a
    LEFT JOIN 
        pg_catalog.pg_constraint p ON p.conrelid = a.attrelid AND a.attnum = ANY(p.conkey) AND p.contype = 'p'
    WHERE 
        a.attrelid = (SELECT c.oid FROM pg_catalog.pg_class c JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace 
                      WHERE c.relname = :table_name AND n.nspname = current_schema())
        AND a.attnum > 0
        AND NOT a.attisdropped
    ORDER BY 
        a.attnum;
    """
    
    # Parameters for the query
    parameters = [
        {
            "name": "table_name",
            "value": {"stringValue": table_name}
        }
    ]
    
    try:
        # Execute the query
        result = await db_connection.execute_query(query, parameters)
        return parse_execute_response(result)
    except Exception as e:
        logger.error(f"Error fetching table schema: {str(e)}")
        raise


# Error message constants
UNEXPECTED_ERROR_KEY = 'run_query unexpected error'
WRITE_QUERY_PROHIBITED_KEY = (
    'Your MCP tool only allows readonly query. '
    'If you want to write, change the MCP configuration per README.md'
)
QUERY_INJECTION_RISK_KEY = 'Your query contains risky injection patterns'

# Initialize MCP server
mcp = FastMCP("PostgreSQL MCP Server")

# Global database connection
db_connection: Optional[DBConnector] = None


def extract_cell(cell: Dict[str, Any]) -> Any:
    """Extract the scalar or array value from a single cell."""
    if cell.get('isNull'):
        return None
    for key in (
        'stringValue',
        'longValue',
        'doubleValue',
        'booleanValue',
        'blobValue',
        'arrayValue',
    ):
        if key in cell:
            return cell[key]
    return None


def parse_execute_response(response: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Convert RDS Data API execute_statement response to list of rows."""
    columns = [col['name'] for col in response.get('columnMetadata', [])]
    records = []

    for row in response.get('records', []):
        row_data = {
            col: extract_cell(cell)
            for col, cell in zip(columns, row)
        }
        records.append(row_data)

    return records


@mcp.tool(
    name='run_query',
    description='Run a SQL query using unified database connection'
)
async def run_query(
    sql: Annotated[str, Field(description='The SQL query to run')],
    ctx: Context,
    query_parameters: Annotated[
        Optional[List[Dict[str, Any]]],
        Field(description='Parameters for the SQL query')
    ] = None,
) -> List[Dict[str, Any]]:
    """Run a SQL query using unified database connection with security validation."""
    global db_connection

    try:
        if db_connection is None:
            error_msg = "No database connection available. Please configure the database first."
            await ctx.error(error_msg)
            return [{'error': error_msg}]

        if db_connection.readonly_query:
            matches = detect_mutating_keywords(sql)
            if matches:
                logger.info(f'Query rejected - readonly mode, detected keywords: {matches}')
                await ctx.error(WRITE_QUERY_PROHIBITED_KEY)
                return [{'error': WRITE_QUERY_PROHIBITED_KEY}]

        issues = check_sql_injection_risk(sql)
        if issues:
            logger.info(f'Query rejected - injection risk: {issues}')
            error_details = {
                'message': 'Query contains suspicious patterns',
                'details': issues
            }
            await ctx.error(str(error_details))
            return [{'error': QUERY_INJECTION_RISK_KEY}]

        # Execute query directly - connection is handled internally
        logger.info("Executing query...")

        logger.info(
            f'run_query: connection_type:{db_connection.connection_info["type"]}, '
            f'readonly:{db_connection.readonly_query}'
        )

        # Execute query using parameterized approach
        response = await db_connection.execute_query(sql, query_parameters)

        logger.success('Query executed successfully')
        return parse_execute_response(response)

    except Exception as e:
        logger.exception(UNEXPECTED_ERROR_KEY)
        error_details = f'{type(e).__name__}: {str(e)}'
        await ctx.error(str({'message': error_details}))
        return [{'error': UNEXPECTED_ERROR_KEY}]


@mcp.tool(
    name='get_table_schema',
    description='Fetch table columns and comments from Postgres using RDS Data API'
)
async def get_table_schema(
    table_name: Annotated[str, Field(description='name of the table')],
    ctx: Context
) -> List[Dict[str, Any]]:
    """Get a table's schema information given the table name."""
    global db_connection

    try:
        if db_connection is None:
            error_msg = "No database connection available"
            await ctx.error(error_msg)
            return [{'error': error_msg}]

        # Use the implemented fetch_table_schema function
        result = await fetch_table_schema(db_connection, table_name)
        return result

    except Exception as e:
        logger.exception("Error fetching table schema")
        error_details = f'{type(e).__name__}: {str(e)}'
        await ctx.error(str({'message': error_details}))
        return [{'error': 'Failed to fetch table schema'}]


@mcp.tool(
    name='health_check',
    description='Check if the server is running and responsive'
)
async def health_check(ctx: Context) -> Dict[str, Any]:
    """Check if the server is running and responsive."""
    global db_connection

    try:
        if db_connection is None:
            return {
                'status': 'error',
                'message': 'No database connection available',
                'connection_status': 'not_configured'
            }

        # Test basic connectivity
        connection_info = db_connection.connection_info
        connection_type = connection_info.get('type', 'Unknown')

        # Use a simple test query
        test_result = await run_query("SELECT 1 as health_check", ctx)
        connection_test = (
            len(test_result) > 0 and
            'error' not in test_result[0]
        )

        return {
            'status': 'healthy' if connection_test else 'unhealthy',
            'connection_type': connection_type,
            'connection_status': 'connected' if connection_test else 'failed',
            'readonly_mode': db_connection.readonly_query,
            'server_info': 'PostgreSQL MCP Server v1.0.2'
        }

    except Exception as e:
        logger.exception("Health check failed")
        return {
            'status': 'error',
            'message': f'Health check failed: {str(e)}',
            'connection_status': 'error'
        }



async def main() -> None:
    """Main entry point for the PostgreSQL MCP Server."""
    global db_connection

    parser = argparse.ArgumentParser(
        description='PostgreSQL MCP Server'
    )

    # Connection method 1: RDS Data API
    parser.add_argument(
        '--resource_arn',
        help='ARN of the RDS cluster (for RDS Data API)'
    )

    # Connection method 2: Direct PostgreSQL
    parser.add_argument(
        '--hostname',
        help='Database hostname (for direct PostgreSQL connection)'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=5432,
        help='Database port (default: 5432)'
    )

    # Common parameters
    parser.add_argument(
        '--secret_arn',
        required=True,
        help='ARN of the Secrets Manager secret for database credentials'
    )
    parser.add_argument(
        '--database',
        required=True,
        help='Database name'
    )
    parser.add_argument(
        '--region',
        required=True,
        help='AWS region'
    )
    parser.add_argument(
        '--readonly',
        required=True,
        help='Enforce readonly SQL statements'
    )

    args = parser.parse_args()

    # Validate connection parameters
    if not args.resource_arn and not args.hostname:
        parser.error(
            "Either --resource_arn (for RDS Data API) or "
            "--hostname (for direct PostgreSQL) must be provided"
        )

    if args.resource_arn and args.hostname:
        parser.error(
            "Cannot specify both --resource_arn and --hostname. "
            "Choose one connection method."
        )

    # Create database connection using ConnectionFactory
    readonly = args.readonly == 'true'
    connection_target = (
        args.resource_arn if args.resource_arn
        else f"{args.hostname}:{args.port}"
    )

    try:
        # Create the appropriate connection
        db_connection = ConnectionFactory.create_connection(
            resource_arn=args.resource_arn,
            hostname=args.hostname,
            port=args.port,
            secret_arn=args.secret_arn,
            database=args.database,
            region=args.region,
            readonly=readonly
        )

        connection_type = db_connection.connection_info['type']
        connection_display = connection_type.replace('_', ' ').title()
        logger.info(
            f'PostgreSQL MCP Server starting with {connection_display} '
            f'connection to {connection_target}, DATABASE:{args.database}, '
            f'READONLY:{readonly}'
        )

    except Exception:
        logger.exception(
            'Failed to initialize database connection. Exiting.'
        )
        sys.exit(1)

    # Test database connection with optimized approach
    class DummyCtx:
        async def error(self, message):
            pass

    ctx = DummyCtx()

    try:
        connection_type = db_connection.connection_info['type']
        connection_display = connection_type.replace('_', ' ').title()

        # Test with a simple query for all connection types
        response = await run_query('SELECT 1', ctx)
        if (isinstance(response, list) and len(response) == 1 and
            isinstance(response[0], dict) and 'error' in response[0]):
            logger.error(
                f'Failed to validate {connection_display} database connection. Exiting.'
            )
            sys.exit(1)

        logger.success(
            f'{connection_display} database connection validated successfully'
        )

    except Exception:
        logger.exception(
            'Database connection validation failed. Exiting.'
        )
        sys.exit(1)

    # Run the MCP server
    await mcp.run_stdio_async()


if __name__ == "__main__":
    asyncio.run(main())
