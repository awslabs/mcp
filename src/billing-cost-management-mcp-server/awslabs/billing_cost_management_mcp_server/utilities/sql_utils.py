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

"""SQL utilities for AWS Billing and Cost Management MCP Server.

This module provides utilities for working with SQLite databases,
including database connection management, table creation, and
converting large API responses to SQLite tables.

Security model:
- SQL injection prevention through table name validation (validate_table_name)
- Centralized SQL statement construction (create_safe_sql_statement)
- Parameter binding for all data values
- Query validation to prevent harmful operations
"""

import atexit
import json
import os
import re
import sqlite3
import uuid
from .logging_utils import get_context_logger, get_logger
from datetime import datetime
from fastmcp import Context
from typing import Any, Dict, List, Optional, Tuple


# Configure logger for this module
logger = get_logger(__name__)


# Constants for SQL conversion
SQL_CONVERSION_THRESHOLD = int(
    os.getenv('MCP_SQL_THRESHOLD', 25 * 1024)
)  # 25KB default (lowered from 50KB)
FORCE_SQL_CONVERSION = os.getenv('MCP_FORCE_SQL', 'false').lower() == 'true'

# Session database path singleton
_SESSION_DB_PATH = None


def should_convert_to_sql(response_size: int) -> bool:
    """Determine if response should be converted to SQL based on config.

    Converts responses larger than SQL_CONVERSION_THRESHOLD (default 25KB) to SQL
    to prevent context window overflow and improve performance.

    Args:
        response_size: Size of the response in bytes

    Returns:
        bool: True if the response should be converted to SQL

    Environment Variables:
        MCP_SQL_THRESHOLD: Override the default threshold (in bytes)
        MCP_FORCE_SQL: If 'true', always convert to SQL regardless of size
    """
    if FORCE_SQL_CONVERSION:
        return True
    return response_size > SQL_CONVERSION_THRESHOLD


def get_session_db_path() -> str:
    """Get the path to the session database.

    Creates the sessions directory if it doesn't exist.
    Registers a cleanup function to delete the database on exit.

    Returns:
        str: Path to the SQLite database file
    """
    global _SESSION_DB_PATH

    if _SESSION_DB_PATH is None:
        # Generate a unique session ID
        session_id = str(uuid.uuid4())[:8]

        # Get the base directory for the session database
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        session_dir = os.path.join(base_dir, 'sessions')

        # Create sessions directory if it doesn't exist
        os.makedirs(session_dir, exist_ok=True)

        # Set the database path
        _SESSION_DB_PATH = os.path.join(session_dir, f'session_{session_id}.db')

        # Register cleanup function
        atexit.register(cleanup_session_db)

    return _SESSION_DB_PATH


def cleanup_session_db() -> None:
    """Clean up the session database on exit."""
    global _SESSION_DB_PATH

    if _SESSION_DB_PATH and os.path.exists(_SESSION_DB_PATH):
        try:
            os.remove(_SESSION_DB_PATH)
            logger.debug(f'Removed session database: {_SESSION_DB_PATH}')
        except Exception as e:
            logger.warning(f'Failed to remove session database: {str(e)}')


def get_db_connection() -> Tuple[sqlite3.Connection, sqlite3.Cursor]:
    """Get a connection to the session database.

    Creates the schema_info table if it doesn't exist.

    Returns:
        Tuple[sqlite3.Connection, sqlite3.Cursor]: Database connection and cursor
    """
    # Get database path
    db_path = get_session_db_path()

    # Create connection and cursor
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create schema_info table to track created tables if it doesn't exist
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS schema_info (
        table_name TEXT PRIMARY KEY,
        created_at TEXT,
        operation TEXT,
        query TEXT,
        row_count INTEGER
    )
    """)

    # Commit the changes
    conn.commit()

    return conn, cursor


def validate_table_name(table_name: str) -> bool:
    """Validate table name for SQL injection prevention.

    Args:
        table_name: Name of the table to validate

    Returns:
        bool: True if the table name is valid

    Raises:
        ValueError: If the table name contains invalid characters
    """
    # Only allow alphanumeric characters and underscores
    if not re.match(r'^[a-zA-Z0-9_]+$', table_name):
        raise ValueError(
            f'Invalid table name: {table_name}. Table names must only contain letters, numbers, and underscores.'
        )
    return True


def create_safe_sql_statement(
    statement_type: str, table_name: str, *args, limit: Optional[int] = None
) -> str:
    """Create a SQL statement with validated table name.

    Args:
        statement_type: Type of SQL statement (CREATE, SELECT, INSERT, etc.)
        table_name: Name of the table (will be validated)
        *args: Additional SQL statement parts
        limit: Optional LIMIT clause value

    Returns:
        str: A safe SQL statement

    Raises:
        ValueError: If the table name is invalid
    """
    validate_table_name(table_name)

    if statement_type.upper() == 'CREATE':
        return f'CREATE TABLE {table_name} ({", ".join(args)})'
    elif statement_type.upper() == 'SELECT':
        base_sql = f'SELECT {", ".join(args)} FROM {table_name}'
        if limit is not None and isinstance(limit, int) and limit > 0:
            base_sql += f' LIMIT {limit}'
        return base_sql
    elif statement_type.upper() == 'INSERT':
        return f'INSERT INTO {table_name} {args[0]}'
    else:
        return f'{statement_type} {table_name} {" ".join(args)}'


def create_table(cursor: sqlite3.Cursor, table_name: str, schema: List[str]) -> None:
    """Create a table with the specified schema.

    Args:
        cursor: SQLite cursor
        table_name: Name of the table to create
        schema: List of column definitions (e.g., ["id INTEGER", "name TEXT"])

    Raises:
        ValueError: If the table name contains invalid characters
    """
    # Validate table name for SQL injection prevention
    validate_table_name(table_name)

    # Create a safe SQL statement
    sql = create_safe_sql_statement('CREATE', table_name, *schema)

    # Execute the safe SQL statement
    cursor.execute(sql)


def insert_data(cursor: sqlite3.Cursor, table_name: str, data: Optional[List[List[Any]]]) -> int:
    """Insert data into a table.

    Args:
        cursor: SQLite cursor
        table_name: Name of the table
        data: List of rows to insert

    Returns:
        int: Number of rows inserted

    Raises:
        ValueError: If the table name contains invalid characters
    """
    if not data or not data[0]:
        return 0

    # Validate table name for SQL injection prevention
    validate_table_name(table_name)

    # Create placeholders for prepared statement
    placeholders = ', '.join(['?' for _ in range(len(data[0]))])
    # Build the query safely
    insert_sql = create_safe_sql_statement('INSERT', table_name, f'VALUES ({placeholders})')

    # Insert data
    for row in data:
        cursor.execute(insert_sql, row)

    return len(data)


def register_table_in_schema_info(
    cursor: sqlite3.Cursor, table_name: str, operation: str, query: str, row_count: int
) -> None:
    """Register a table in the schema_info table.

    Args:
        cursor: SQLite cursor
        table_name: Name of the table
        operation: Operation that created the table
        query: Query used to create the table
        row_count: Number of rows in the table
    """
    now = datetime.now().isoformat()

    cursor.execute(
        'INSERT OR REPLACE INTO schema_info VALUES (?, ?, ?, ?, ?)',
        (table_name, now, operation, query, row_count),
    )


def validate_sql_query(query: str) -> bool:
    """Validate SQL query for security issues.

    Args:
        query: SQL query to validate

    Returns:
        bool: True if the query is valid

    Raises:
        ValueError: If the query contains potentially harmful operations
    """
    dangerous_patterns = [
        r'\bDROP\b.*\bTABLE\b',
        r'\bDELETE\b.*\bFROM\b',
        r'\bTRUNCATE\b.*\bTABLE\b',
        r'\bALTER\b.*\bTABLE\b',
        r'\bEXEC\b',
        r'\bSYSTEM\b',
        r';.*\b',
    ]

    query_upper = query.upper()
    for pattern in dangerous_patterns:
        if re.search(pattern, query_upper, re.IGNORECASE):
            raise ValueError(f'Query contains potentially harmful operations: {query}')

    return True


def execute_query(cursor: sqlite3.Cursor, query: str) -> Tuple[List[str], List[Tuple]]:
    """Execute a SQL query.

    Args:
        cursor: SQLite cursor
        query: SQL query to execute

    Returns:
        Tuple[List[str], List[Tuple]]: Column names and rows

    Raises:
        ValueError: If the query contains potentially harmful operations
    """
    # Validate query for security issues
    validate_sql_query(query)
    cursor.execute(query)

    # Get column names
    column_names = (
        [description[0] for description in cursor.description] if cursor.description else []
    )

    # Get rows
    rows = cursor.fetchall()

    return column_names, rows


def _get_specialized_converter(operation_name: str) -> Optional[str]:
    """Get specific converter function for API.

    Args:
        operation_name: Name of the API operation

    Returns:
        Optional[str]: Type of specialized converter to use, or None for generic
    """
    # Map of operation names to specialized converter types
    converters = {
        'aws_pricing_get_products': 'pricing_products',
        'cost_explorer_get_cost_and_usage': 'cost_and_usage',
        'cost_explorer_get_cost_and_usage_with_resources': 'cost_and_usage',
        'cost_explorer_get_dimension_values': 'dimension_values',
        'cost_explorer_get_cost_forecast': 'forecast',
        'cost_explorer_get_usage_forecast': 'forecast',
        'cost_explorer_get_tags': 'tags',
        'cost_explorer_get_cost_categories': 'cost_categories',
    }

    return converters.get(operation_name)


async def convert_response_if_needed(
    ctx: Context, response: Dict[str, Any], api_name: str, **metadata
) -> Dict[str, Any]:
    """Convert API response to SQL if it exceeds size threshold.

    Args:
        ctx: MCP context
        response: API response data
        api_name: Name of the API operation (e.g., 'aws_pricing_get_products')
        **metadata: Additional metadata to include in response

    Returns:
        Either SQL table info or formatted response
    """
    # Get context logger for consistent logging
    ctx_logger = get_context_logger(ctx, __name__)

    try:
        # Calculate response size
        response_size = len(json.dumps(response).encode('utf-8'))

        if should_convert_to_sql(response_size):
            # Convert large response to SQL
            await ctx_logger.info(
                f'Response size {response_size / 1024:.2f}KB exceeds threshold, converting to SQL'
            )
            return await convert_api_response_to_table(ctx, response, api_name, **metadata)
        else:
            # Return original response with size info
            await ctx_logger.debug(
                f'Response size {response_size / 1024:.2f}KB below threshold, returning directly'
            )
            return {'status': 'success', 'data': response, 'response_size_bytes': response_size}
    except Exception as e:
        error_message = f'Error processing response for {api_name}: {str(e)}'
        await ctx_logger.error(error_message, exc_info=True)
        # Return error response with original data to ensure no data loss
        return {
            'status': 'error',
            'message': error_message,
            'data': response,
            'response_size_bytes': len(json.dumps(response).encode('utf-8')),
        }


async def convert_api_response_to_table(
    ctx: Context, response: Dict[str, Any], operation_name: str, **metadata
) -> Dict[str, Any]:
    """Convert a large API response to a SQLite table.

    This function stores API response data in a SQLite table for easier querying
    with the session_sql tool.

    Args:
        ctx: MCP context
        response: API response to convert
        operation_name: Name of the operation (used for table name prefix)
        **metadata: Additional metadata to store with the table

    Returns:
        Dict[str, Any]: Response with information about the created table
    """
    await ctx.info(
        f'Response size: {len(json.dumps(response).encode("utf-8")) / 1024:.1f}KB - Converting to SQL table'
    )

    # Get converter for specific API type
    converter_type = _get_specialized_converter(operation_name)

    # Generate a unique table name
    table_id = str(uuid.uuid4())[:8]
    table_name = f'{operation_name}_{table_id}'

    # Get database connection
    conn, cursor = get_db_connection()

    try:
        rows_inserted = 0

        # Create table and insert data based on response type
        if converter_type == 'pricing_products' and 'PriceList' in response:
            # AWS Pricing API response
            schema = [
                'service_code TEXT',
                'product_family TEXT',
                'sku TEXT',
                'attributes TEXT',
                'pricing_terms TEXT',
            ]
            sql = create_safe_sql_statement('CREATE', table_name, *schema)
            cursor.execute(sql)

            # Insert pricing data
            price_list = response.get('PriceList', [])
            for product_json in price_list:
                product = json.loads(product_json)

                # Use validated table name
                validate_table_name(table_name)
                insert_sql = create_safe_sql_statement(
                    'INSERT',
                    table_name,
                    '(service_code, product_family, sku, attributes, pricing_terms) VALUES (?, ?, ?, ?, ?)',
                )
                cursor.execute(
                    insert_sql,
                    (
                        metadata.get('service_code', ''),
                        product.get('product', {}).get('productFamily'),
                        product.get('product', {}).get('sku'),
                        json.dumps(product.get('product', {}).get('attributes', {})),
                        json.dumps(product.get('terms', {})),
                    ),
                )
                rows_inserted += 1

        elif converter_type == 'cost_and_usage' and 'ResultsByTime' in response:
            # Cost Explorer GetCostAndUsage response
            schema = [
                'time_period_start TEXT',
                'time_period_end TEXT',
                'estimated BOOLEAN',
                'group_key_1 TEXT',
                'group_key_2 TEXT',
                'group_key_3 TEXT',
                'metric_name TEXT',
                'amount REAL',
                'unit TEXT',
            ]
            sql = create_safe_sql_statement('CREATE', table_name, *schema)
            cursor.execute(sql)

            for result_by_time in response.get('ResultsByTime', []):
                time_period = result_by_time.get('TimePeriod', {})
                start = time_period.get('Start')
                end = time_period.get('End')
                estimated = result_by_time.get('Estimated', False)

                # Handle grouped data
                for group in result_by_time.get('Groups', []):
                    keys = group.get('Keys', [])
                    padded_keys = (keys + [None, None, None])[:3]

                    for metric_name, metric_data in group.get('Metrics', {}).items():
                        # Use validated table name
                        validate_table_name(table_name)
                        insert_sql = create_safe_sql_statement(
                            'INSERT',
                            table_name,
                            '(time_period_start, time_period_end, estimated, group_key_1, group_key_2, group_key_3, metric_name, amount, unit) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                        )
                        cursor.execute(
                            insert_sql,
                            (
                                start,
                                end,
                                estimated,
                                padded_keys[0],
                                padded_keys[1],
                                padded_keys[2],
                                metric_name,
                                float(metric_data.get('Amount', 0)),
                                metric_data.get('Unit'),
                            ),
                        )
                        rows_inserted += 1

                # Handle total data
                for metric_name, metric_data in result_by_time.get('Total', {}).items():
                    # Use validated table name
                    validate_table_name(table_name)
                    insert_sql = create_safe_sql_statement(
                        'INSERT',
                        table_name,
                        '(time_period_start, time_period_end, estimated, group_key_1, group_key_2, group_key_3, metric_name, amount, unit) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                    )
                    cursor.execute(
                        insert_sql,
                        (
                            start,
                            end,
                            estimated,
                            None,
                            None,
                            None,
                            metric_name,
                            float(metric_data.get('Amount', 0)),
                            metric_data.get('Unit'),
                        ),
                    )
                    rows_inserted += 1

        elif converter_type == 'dimension_values' and 'DimensionValues' in response:
            # Cost Explorer GetDimensionValues response
            schema = ['value TEXT', 'attributes TEXT']
            # We use create_safe_sql_statement which validates table_name to prevent SQL injection
            sql = create_safe_sql_statement('CREATE', table_name, *schema)
            # nosem: python.lang.security.audit.formatted-sql-query.formatted-sql-query
            # nosem: python.sqlalchemy.security.sqlalchemy-execute-raw-query.sqlalchemy-execute-raw-query
            cursor.execute(sql)

            for dim_value in response.get('DimensionValues', []):
                insert_sql = create_safe_sql_statement(
                    'INSERT', table_name, '(value, attributes) VALUES (?, ?)'
                )
                cursor.execute(
                    insert_sql,
                    (dim_value.get('Value'), json.dumps(dim_value.get('Attributes', {}))),
                )
                rows_inserted += 1

        elif converter_type == 'forecast' and 'ForecastResultsByTime' in response:
            # Cost Explorer forecast responses
            schema = [
                'time_period_start TEXT',
                'time_period_end TEXT',
                'mean_value REAL',
                'lower_bound REAL',
                'upper_bound REAL',
            ]
            sql = create_safe_sql_statement('CREATE', table_name, *schema)
            cursor.execute(sql)

            for forecast in response.get('ForecastResultsByTime', []):
                time_period = forecast.get('TimePeriod', {})
                # Use validated table name
                validate_table_name(table_name)
                insert_sql = create_safe_sql_statement(
                    'INSERT',
                    table_name,
                    '(time_period_start, time_period_end, mean_value, lower_bound, upper_bound) VALUES (?, ?, ?, ?, ?)',
                )
                cursor.execute(
                    insert_sql,
                    (
                        time_period.get('Start'),
                        time_period.get('End'),
                        float(forecast.get('MeanValue', 0)),
                        float(forecast.get('PredictionIntervalLowerBound', 0)),
                        float(forecast.get('PredictionIntervalUpperBound', 0)),
                    ),
                )
                rows_inserted += 1

        elif converter_type == 'tags' and 'Tags' in response:
            # Cost Explorer GetTags response
            schema = ['tag_value TEXT']
            sql = create_safe_sql_statement('CREATE', table_name, *schema)
            cursor.execute(sql)

            # Use validated table name
            validate_table_name(table_name)
            for tag in response.get('Tags', []):
                insert_sql = create_safe_sql_statement(
                    'INSERT', table_name, '(tag_value) VALUES (?)'
                )
                cursor.execute(insert_sql, (tag,))
                rows_inserted += 1

        elif converter_type == 'cost_categories' and (
            'CostCategoryNames' in response or 'CostCategoryValues' in response
        ):
            # Cost Explorer GetCostCategories response
            schema = ['category_type TEXT', 'category_value TEXT']
            sql = create_safe_sql_statement('CREATE', table_name, *schema)
            cursor.execute(sql)

            for name in response.get('CostCategoryNames', []):
                # Use validated table name
                validate_table_name(table_name)
                insert_sql = create_safe_sql_statement(
                    'INSERT', table_name, '(category_type, category_value) VALUES (?, ?)'
                )
                cursor.execute(insert_sql, ('name', name))
                rows_inserted += 1

            for value in response.get('CostCategoryValues', []):
                # Use validated table name
                validate_table_name(table_name)
                insert_sql = create_safe_sql_statement(
                    'INSERT', table_name, '(category_type, category_value) VALUES (?, ?)'
                )
                cursor.execute(insert_sql, ('value', value))
                rows_inserted += 1

        else:
            # Generic fallback for unknown response types
            schema = ['key TEXT', 'value TEXT']
            sql = create_safe_sql_statement('CREATE', table_name, *schema)
            cursor.execute(sql)

            # Flatten response to key-value pairs
            def flatten_dict(d, parent_key='', sep='_'):
                items = []
                for k, v in d.items():
                    new_key = f'{parent_key}{sep}{k}' if parent_key else k
                    if isinstance(v, dict):
                        items.extend(flatten_dict(v, new_key, sep=sep).items())
                    elif isinstance(v, list):
                        items.append((new_key, json.dumps(v)))
                    else:
                        items.append((new_key, str(v)))
                return dict(items)

            flattened = flatten_dict(response)

            for key, value in flattened.items():
                # Use validated table name
                validate_table_name(table_name)
                insert_sql = create_safe_sql_statement(
                    'INSERT', table_name, '(key, value) VALUES (?, ?)'
                )
                cursor.execute(insert_sql, (key, value))
                rows_inserted += 1

        conn.commit()

        # Get preview
        sql = create_safe_sql_statement('SELECT', table_name, '*', limit=5)
        cursor.execute(sql)
        preview_rows = cursor.fetchall()

        # Get column names for preview
        columns = [description[0] for description in cursor.description]

        # Format preview as list of dictionaries
        preview = []
        for row in preview_rows:
            preview_item = {}
            for i, col in enumerate(columns):
                preview_item[col] = row[i]
            preview.append(preview_item)

        # Register table in schema info
        register_table_in_schema_info(
            cursor, table_name, operation_name, json.dumps(metadata), rows_inserted
        )

        await ctx.info(f'Converted {rows_inserted} rows to SQL table: {table_name}')

        # Get sample queries based on table type with enhanced examples
        # Start with a basic query for all tables
        base_query = create_safe_sql_statement('SELECT', table_name, '*') + ' LIMIT 10'
        sample_queries = [
            {
                'name': 'Basic query',
                'description': 'Retrieve the first 10 rows from the table',
                'sql': base_query,
            }
        ]

        # Add specialized queries based on table type
        if converter_type == 'cost_and_usage':
            # Cost Explorer cost_and_usage queries

            # Total cost by service/dimension
            cost_query = (
                create_safe_sql_statement(
                    'SELECT', table_name, 'group_key_1, SUM(amount) as total_cost, unit'
                )
                + ' GROUP BY group_key_1, unit ORDER BY total_cost DESC'
            )
            sample_queries.append(
                {
                    'name': 'Total cost by service/dimension',
                    'description': 'Summarizes costs by the primary dimension (usually service)',
                    'sql': cost_query,
                }
            )

            # Cost trends over time
            trend_query = (
                create_safe_sql_statement(
                    'SELECT', table_name, 'time_period_start, SUM(amount) as daily_cost'
                )
                + ' GROUP BY time_period_start ORDER BY time_period_start'
            )
            sample_queries.append(
                {
                    'name': 'Cost trend over time',
                    'description': 'Shows cost pattern across the time period',
                    'sql': trend_query,
                }
            )

            # Top 5 services/resources
            top_items_query = (
                create_safe_sql_statement(
                    'SELECT', table_name, 'group_key_1, SUM(amount) as total_cost'
                )
                + ' GROUP BY group_key_1 ORDER BY total_cost DESC LIMIT 5'
            )
            sample_queries.append(
                {
                    'name': 'Top 5 cost items',
                    'description': 'Shows the 5 highest-cost items',
                    'sql': top_items_query,
                }
            )

        elif converter_type == 'dimension_values':
            # DimensionValues queries

            # Basic alphabetical list
            value_query = (
                create_safe_sql_statement('SELECT', table_name, 'value') + ' ORDER BY value'
            )
            sample_queries.append(
                {
                    'name': 'Values in alphabetical order',
                    'description': 'Lists all dimension values alphabetically',
                    'sql': value_query,
                }
            )

            # Values with attributes
            attr_query = (
                create_safe_sql_statement('SELECT', table_name, 'value, attributes')
                + ' ORDER BY value'
            )
            sample_queries.append(
                {
                    'name': 'Values with attributes',
                    'description': 'Shows values with their attributes as JSON',
                    'sql': attr_query,
                }
            )

        elif converter_type == 'pricing_products':
            # AWS Pricing queries

            # Count by product family
            product_query = (
                create_safe_sql_statement(
                    'SELECT', table_name, 'product_family, COUNT(*) as product_count'
                )
                + ' GROUP BY product_family ORDER BY product_count DESC'
            )
            sample_queries.append(
                {
                    'name': 'Products by family',
                    'description': 'Counts products in each product family',
                    'sql': product_query,
                }
            )

            # EC2 instance types (if applicable)
            ec2_query = (
                create_safe_sql_statement('SELECT', table_name, 'sku, attributes, pricing_terms')
                + " WHERE attributes LIKE '%instanceType%' LIMIT 10"
            )
            sample_queries.append(
                {
                    'name': 'EC2 instance types',
                    'description': 'Shows EC2 instance types with pricing data',
                    'sql': ec2_query,
                }
            )

        elif converter_type == 'forecast':
            # Cost Explorer forecast queries

            # Forecast trend
            forecast_query = (
                create_safe_sql_statement(
                    'SELECT', table_name, 'time_period_start, mean_value, lower_bound, upper_bound'
                )
                + ' ORDER BY time_period_start'
            )
            sample_queries.append(
                {
                    'name': 'Forecast trend',
                    'description': 'Shows forecast values with confidence bounds over time',
                    'sql': forecast_query,
                }
            )

        elif converter_type == 'tags':
            # Tags-related queries
            tags_query = (
                create_safe_sql_statement('SELECT', table_name, 'tag_value')
                + " WHERE tag_value LIKE '%env%' OR tag_value LIKE '%project%' OR tag_value LIKE '%name%'"
            )
            sample_queries.append(
                {
                    'name': 'Common tags',
                    'description': 'Finds common tags like environment, project, or name',
                    'sql': tags_query,
                }
            )

        else:
            # Generic key-value pair queries for other types
            key_query = (
                create_safe_sql_statement('SELECT', table_name, 'key, value')
                + " WHERE key LIKE '%total%' OR key LIKE '%cost%' OR key LIKE '%amount%'"
            )
            sample_queries.append(
                {
                    'name': 'Cost-related fields',
                    'description': 'Finds key-value pairs related to costs or totals',
                    'sql': key_query,
                }
            )

        # Return info about the stored data
        db_path = get_session_db_path()

        return {
            'status': 'success',
            'data_stored': True,
            'session_db': db_path,
            'table_name': table_name,
            'schema': columns,
            'row_count': rows_inserted,
            'sample_queries': sample_queries,
            'preview': preview,
            **metadata,
        }

    except Exception as e:
        error_message = f'Error converting response to SQL: {str(e)}'
        # Use context logger for consistent error reporting
        ctx_logger = get_context_logger(ctx, __name__)
        await ctx_logger.error(error_message, exc_info=True)
        raise
    finally:
        # Close connection if it was successfully created
        if 'conn' in locals() and conn is not None:
            try:
                conn.close()
                logger.debug('Closed database connection')
            except Exception as e:
                logger.warning(f'Error closing database connection: {str(e)}')


async def execute_session_sql(
    ctx: Context,
    query: str,
    schema: Optional[List[str]] = None,
    data: Optional[List[List[Any]]] = None,
    table_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Execute SQL query on the session database.

    Optionally adds user data to the database before querying.

    Args:
        ctx: MCP context
        query: SQL query to execute
        schema: Optional column definitions for user data
        data: Optional array of data rows to add before querying
        table_name: Optional name for user data table

    Returns:
        Dict[str, Any]: Query results
    """
    # Initialize connection to None in case of early exception
    conn = None
    try:
        # Get database connection
        conn, cursor = get_db_connection()

        # If user provided data, add it to the database first
        if data and schema:
            if not table_name:
                table_name = f'user_data_{str(uuid.uuid4())[:8]}'

            await ctx.info(f'Adding {len(data)} rows to table: {table_name}')

            # Create table with provided schema
            create_table(cursor, table_name, schema)

            # Insert data
            if data:
                insert_data(cursor, table_name, data)

            conn.commit()
            await ctx.info(f'Created table {table_name} with {len(data)} rows')

        # Execute the main query
        await ctx.info(f'Executing SQL query: {query[:100]}...')

        # Get query type (read or write)
        query_upper = query.strip().upper()
        is_write_operation = any(
            query_upper.startswith(cmd)
            for cmd in ['INSERT', 'UPDATE', 'DELETE', 'CREATE', 'DROP', 'ALTER']
        )

        # Execute the query with validation
        validate_sql_query(query)
        cursor.execute(query)

        # Commit if this is a write operation
        if is_write_operation:
            conn.commit()

        # Get results
        columns = (
            [description[0] for description in cursor.description] if cursor.description else []
        )
        rows = cursor.fetchall()

        # Convert to list of dictionaries
        results = []
        for row in rows:
            results.append(dict(zip(columns, row)))

        # Get database path
        db_path = get_session_db_path()

        # Create response
        response = {
            'status': 'success',
            'results': results,
            'row_count': len(results),
            'columns': columns,
            'database_path': db_path,
        }

        # Include table info if data was added
        if data and schema:
            response['created_table'] = table_name
            response['rows_added'] = len(data)

        return response

    except Exception as e:
        error_message = f'Error executing SQL query: {str(e)}'
        # Use context logger for consistent error reporting
        ctx_logger = get_context_logger(ctx, __name__)
        await ctx_logger.error(error_message, exc_info=True)
        return {'status': 'error', 'message': error_message}

    finally:
        # Close connection only if it was successfully opened
        if conn is not None:
            try:
                conn.close()
                logger.debug('Closed database connection')
            except Exception as e:
                error_message = f'Error closing database connection: {str(e)}'
                # Use context logger for consistent error reporting
                ctx_logger = get_context_logger(ctx, __name__)
                await ctx_logger.error(error_message)
