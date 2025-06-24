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
import boto3
import json
import sys
from typing import Annotated, Any, Dict, List, Optional

from loguru import logger
from mcp.server.fastmcp import Context, FastMCP
from pydantic import Field
from botocore.exceptions import BotoCoreError

from .connection import DBConnector, ConnectionFactory
from .mutable_sql_detector import detect_mutating_keywords, check_sql_injection_risk
from botocore.exceptions import ClientError


# Error message constants
CLIENT_ERROR_KEY = 'run_query ClientError code'
UNEXPECTED_ERROR_KEY = 'run_query unexpected error'
WRITE_QUERY_PROHIBITED_KEY = 'Your MCP tool only allows readonly query. If you want to write, change the MCP configuration per README.md'
QUERY_INJECTION_RISK_KEY = 'Your query contains risky injection patterns'

# Initialize MCP server
mcp = FastMCP("PostgreSQL MCP Server")

# Global database connection
db_connection = None


def extract_cell(cell: dict):
    """Extracts the scalar or array value from a single cell."""
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


def parse_execute_response(response: dict) -> list[dict]:
    """Convert RDS Data API execute_statement response to list of rows."""
    columns = [col['name'] for col in response.get('columnMetadata', [])]
    records = []

    for row in response.get('records', []):
        row_data = {col: extract_cell(cell) for col, cell in zip(columns, row)}
        records.append(row_data)

    return records


@mcp.tool(name='run_query', description='Run a SQL query using unified database connection')
async def run_query(
    sql: Annotated[str, Field(description='The SQL query to run')],
    ctx: Context,
    query_parameters: Annotated[
        Optional[List[Dict[str, Any]]], Field(description='Parameters for the SQL query')
    ] = None,
) -> list[dict]:
    """Run a SQL query using unified database connection (RDS Data API or Direct PostgreSQL)."""
    global db_connection
    
    try:
        if db_connection is None:
            await ctx.error("No database connection available. Please configure the database first.")
            return [{'error': 'No database connection available'}]

        if db_connection.readonly_query:
            matches = detect_mutating_keywords(sql)
            if matches:
                logger.info(f'Query rejected - readonly mode, detected keywords: {matches}')
                await ctx.error(WRITE_QUERY_PROHIBITED_KEY)
                return [{'error': WRITE_QUERY_PROHIBITED_KEY}]

        issues = check_sql_injection_risk(sql)
        if issues:
            logger.info(f'Query rejected - injection risk: {issues}')
            await ctx.error(str({'message': 'Query contains suspicious patterns', 'details': issues}))
            return [{'error': QUERY_INJECTION_RISK_KEY}]

        # Ensure connection is established
        if not db_connection.is_connected():
            logger.info("Establishing database connection for query execution...")
            connected = await db_connection.connect()
            if not connected:
                raise Exception("Failed to establish database connection")

        logger.info(f'run_query: connection_type:{db_connection.connection_info["type"]}, readonly:{db_connection.readonly_query}, SQL:{sql}')

        # Execute query
        response = await db_connection.execute_query(sql, query_parameters)

        logger.success('Query executed successfully')
        return parse_execute_response(response)
    except Exception as e:
        logger.exception(UNEXPECTED_ERROR_KEY)
        error_details = f'{type(e).__name__}: {str(e)}'
        await ctx.error(str({'message': error_details}))
        return [{'error': UNEXPECTED_ERROR_KEY}]


@mcp.tool(name='get_table_schema', description='Fetch table columns and comments from Postgres using RDS Data API')
async def get_table_schema(
    table_name: Annotated[str, Field(description='name of the table')], ctx: Context
) -> list[dict]:
    """Get a table's schema information given the table name."""
    logger.info(f'get_table_schema: {table_name}')

    sql = """
        SELECT
            a.attname AS column_name,
            pg_catalog.format_type(a.atttypid, a.atttypmod) AS data_type,
            col_description(a.attrelid, a.attnum) AS column_comment,
            NOT a.attnotnull AS is_nullable,
            pg_get_expr(d.adbin, d.adrelid) AS column_default
        FROM
            pg_attribute a
        LEFT JOIN pg_attrdef d ON a.attrelid = d.adrelid AND a.attnum = d.adnum
        WHERE
            a.attrelid = to_regclass(:table_name)
            AND a.attnum > 0
            AND NOT a.attisdropped
        ORDER BY a.attnum
    """

    params = [{'name': 'table_name', 'value': {'stringValue': table_name}}]
    return await run_query(sql=sql, ctx=ctx, query_parameters=params)


@mcp.tool(name='analyze_database_structure', description='Analyze the database structure and provide insights on schema design, indexes, and potential optimizations')
async def analyze_database_structure(
    ctx: Context,
    debug: Annotated[bool, Field(description='Whether to include debug information')] = False
) -> str:
    """Analyze the database structure and provide optimization insights."""
    try:
        logger.info("Starting database structure analysis")
        
        # Get schemas
        schemas_sql = """
            SELECT schema_name 
            FROM information_schema.schemata 
            WHERE schema_name NOT IN ('information_schema', 'pg_catalog', 'pg_toast')
            ORDER BY schema_name
        """
        schemas_result = await run_query(schemas_sql, ctx)
        schemas = [row['schema_name'] for row in schemas_result if 'error' not in row]
        
        # Get tables with detailed information
        tables_sql = """
            SELECT 
                t.table_schema,
                t.table_name,
                pg_size_pretty(pg_total_relation_size(quote_ident(t.table_schema)||'.'||quote_ident(t.table_name))) as size,
                pg_total_relation_size(quote_ident(t.table_schema)||'.'||quote_ident(t.table_name)) as size_bytes,
                COALESCE(c.reltuples, 0)::bigint as estimated_rows
            FROM information_schema.tables t
            LEFT JOIN pg_class c ON c.relname = t.table_name
            LEFT JOIN pg_namespace n ON n.oid = c.relnamespace AND n.nspname = t.table_schema
            WHERE t.table_type = 'BASE TABLE'
            AND t.table_schema NOT IN ('information_schema', 'pg_catalog', 'pg_toast')
            ORDER BY t.table_schema, t.table_name
        """
        tables_result = await run_query(tables_sql, ctx)
        
        # Get indexes
        indexes_sql = """
            SELECT
                schemaname,
                tablename,
                indexname,
                indexdef
            FROM pg_indexes
            WHERE schemaname NOT IN ('information_schema', 'pg_catalog', 'pg_toast')
            ORDER BY schemaname, tablename, indexname
        """
        indexes_result = await run_query(indexes_sql, ctx)
        
        # Format results
        result = {
            "status": "success",
            "data": {
                "schemas": schemas,
                "tables": [row for row in tables_result if 'error' not in row],
                "indexes": [row for row in indexes_result if 'error' not in row]
            },
            "metadata": {
                "analysis_timestamp": "2025-06-19T13:35:00Z",
                "total_schemas": len(schemas),
                "total_tables": len([row for row in tables_result if 'error' not in row]),
                "total_indexes": len([row for row in indexes_result if 'error' not in row])
            },
            "recommendations": [
                "Database structure analysis completed successfully",
                "Review table sizes and consider partitioning for large tables",
                "Ensure proper indexing on frequently queried columns"
            ]
        }
        
        logger.success("Database structure analysis completed")
        return json.dumps(result, indent=2 if debug else None)
        
    except Exception as e:
        logger.error(f"Database structure analysis failed: {str(e)}")
        return json.dumps({"status": "error", "error": str(e)})


@mcp.tool(name='show_postgresql_settings', description='Show PostgreSQL configuration settings with optional filtering')
async def show_postgresql_settings(
    ctx: Context,
    pattern: Annotated[Optional[str], Field(description='Pattern to filter settings (SQL LIKE pattern)')] = None,
    debug: Annotated[bool, Field(description='Include debug information')] = False
) -> str:
    """Show PostgreSQL configuration settings with optional filtering."""
    try:
        logger.info(f"Getting PostgreSQL settings with pattern: {pattern}")
        
        if pattern:
            settings_sql = f"""
                SELECT 
                    name,
                    setting,
                    unit,
                    category,
                    short_desc,
                    context,
                    vartype,
                    source
                FROM pg_settings
                WHERE name ILIKE '%{pattern}%'
                ORDER BY category, name
            """
        else:
            settings_sql = """
                SELECT 
                    name,
                    setting,
                    unit,
                    category,
                    short_desc,
                    context,
                    vartype,
                    source
                FROM pg_settings
                ORDER BY category, name
            """
        
        settings_result = await run_query(settings_sql, ctx)
        
        # Categorize settings
        categorized = {}
        for row in settings_result:
            if 'error' not in row:
                category = row.get('category', 'Unknown')
                if category not in categorized:
                    categorized[category] = []
                categorized[category].append(row)
        
        result = {
            "status": "success",
            "data": {
                "settings": [row for row in settings_result if 'error' not in row],
                "categorized_settings": categorized,
                "filter_pattern": pattern
            },
            "metadata": {
                "analysis_timestamp": "2025-06-19T13:35:00Z",
                "total_settings": len([row for row in settings_result if 'error' not in row]),
                "categories": len(categorized)
            },
            "recommendations": [
                "Review memory settings for optimization opportunities",
                "Check connection limits and adjust if needed",
                "Ensure logging settings match your monitoring requirements"
            ]
        }
        
        logger.success("PostgreSQL settings analysis completed")
        return json.dumps(result, indent=2 if debug else None)
        
    except Exception as e:
        logger.error(f"PostgreSQL settings analysis failed: {str(e)}")
        return json.dumps({"status": "error", "error": str(e)})


@mcp.tool(name='identify_slow_queries', description='Identify slow-running queries in the database')
async def identify_slow_queries(
    ctx: Context,
    min_execution_time: Annotated[float, Field(description='Minimum execution time in milliseconds')] = 100.0,
    limit: Annotated[int, Field(description='Maximum number of queries to return')] = 20,
    debug: Annotated[bool, Field(description='Include debug information')] = False
) -> str:
    """Identify slow-running queries in the database."""
    try:
        logger.info(f"Identifying slow queries (min_time: {min_execution_time}ms, limit: {limit})")
        
        # Check if pg_stat_statements extension is available
        check_extension_sql = """
            SELECT EXISTS (
                SELECT 1 FROM pg_extension WHERE extname = 'pg_stat_statements'
            ) as extension_exists
        """
        
        extension_result = await run_query(check_extension_sql, ctx)
        has_extension = False
        if extension_result and len(extension_result) > 0 and 'error' not in extension_result[0]:
            has_extension = extension_result[0].get('extension_exists', False)
        
        if not has_extension:
            return json.dumps({
                "status": "error",
                "error": {
                    "step": "checking_pg_stat_statements",
                    "message": "pg_stat_statements extension is not available",
                    "suggestions": [
                        "Install pg_stat_statements extension: CREATE EXTENSION pg_stat_statements;",
                        "Add 'pg_stat_statements' to shared_preload_libraries in postgresql.conf",
                        "Restart PostgreSQL server after configuration change"
                    ]
                }
            })
        
        # Get slow queries from pg_stat_statements
        slow_queries_sql = f"""
            SELECT 
                query,
                calls,
                total_exec_time,
                mean_exec_time,
                max_exec_time,
                min_exec_time,
                rows
            FROM pg_stat_statements 
            WHERE mean_exec_time >= {min_execution_time}
            ORDER BY mean_exec_time DESC
            LIMIT {limit}
        """
        
        slow_queries_result = await run_query(slow_queries_sql, ctx)
        
        result = {
            "status": "success",
            "data": {
                "slow_queries": [row for row in slow_queries_result if 'error' not in row],
                "min_execution_time_ms": min_execution_time,
                "limit": limit
            },
            "metadata": {
                "analysis_timestamp": "2025-06-19T13:35:00Z",
                "slow_queries_found": len([row for row in slow_queries_result if 'error' not in row])
            },
            "recommendations": [
                "Review the slowest queries for optimization opportunities",
                "Consider adding indexes for frequently filtered columns",
                "Analyze query execution plans for expensive operations"
            ]
        }
        
        logger.success("Slow query analysis completed")
        return json.dumps(result, indent=2 if debug else None)
        
    except Exception as e:
        logger.error(f"Slow query analysis failed: {str(e)}")
        return json.dumps({"status": "error", "error": str(e)})


@mcp.tool(name='analyze_table_fragmentation', description='Analyze table fragmentation and provide optimization recommendations')
async def analyze_table_fragmentation(
    ctx: Context,
    threshold: Annotated[float, Field(description='Bloat percentage threshold for recommendations')] = 10.0,
    debug: Annotated[bool, Field(description='Include debug information')] = False
) -> str:
    """Analyze table fragmentation and provide optimization recommendations."""
    try:
        logger.info(f"Analyzing table fragmentation with threshold {threshold}%")
        
        # Get table bloat information using pg_stat_user_tables
        bloat_sql = """
            SELECT 
                schemaname,
                relname as tablename,
                n_tup_ins as inserts,
                n_tup_upd as updates,
                n_tup_del as deletes,
                n_live_tup as live_tuples,
                n_dead_tup as dead_tuples,
                CASE 
                    WHEN n_live_tup > 0 
                    THEN round(100.0 * n_dead_tup / (n_live_tup + n_dead_tup), 2)
                    ELSE 0 
                END as bloat_percent,
                last_vacuum,
                last_autovacuum
            FROM pg_stat_user_tables
            ORDER BY 
                CASE 
                    WHEN n_live_tup > 0 
                    THEN 100.0 * n_dead_tup / (n_live_tup + n_dead_tup)
                    ELSE 0 
                END DESC
        """
        
        bloat_result = await run_query(bloat_sql, ctx)
        
        # Filter tables above threshold
        problematic_tables = []
        for row in bloat_result:
            if 'error' not in row:
                # Convert bloat_percent from string to float for comparison
                bloat_percent_value = row.get('bloat_percent', '0')
                try:
                    # Handle both string and numeric values
                    if isinstance(bloat_percent_value, str):
                        bloat_percent_float = float(bloat_percent_value)
                    else:
                        bloat_percent_float = float(bloat_percent_value) if bloat_percent_value is not None else 0.0
                    
                    if bloat_percent_float > threshold:
                        # Add the converted value back to the row for consistency
                        row['bloat_percent_numeric'] = bloat_percent_float
                        problematic_tables.append(row)
                except (ValueError, TypeError):
                    # If conversion fails, skip this row but log it
                    logger.warning(f"Could not convert bloat_percent '{bloat_percent_value}' to float for table {row.get('tablename', 'unknown')}")
                    continue
        
        result = {
            "status": "success",
            "data": {
                "table_bloat": [row for row in bloat_result if 'error' not in row],
                "problematic_tables": problematic_tables,
                "threshold_percent": threshold
            },
            "metadata": {
                "analysis_timestamp": "2025-06-19T13:40:00Z",
                "total_tables_analyzed": len([row for row in bloat_result if 'error' not in row]),
                "tables_above_threshold": len(problematic_tables)
            },
            "recommendations": [
                f"Found {len(problematic_tables)} tables above {threshold}% bloat threshold",
                "Consider running VACUUM on tables with high dead tuple percentages",
                "Review autovacuum settings for frequently updated tables",
                "Monitor vacuum operations and adjust frequency as needed"
            ]
        }
        
        logger.success("Table fragmentation analysis completed")
        return json.dumps(result, indent=2 if debug else None)
        
    except Exception as e:
        logger.error(f"Table fragmentation analysis failed: {str(e)}")
        return json.dumps({"status": "error", "error": str(e)})


@mcp.tool(name='analyze_query_performance', description='Analyze query performance and provide optimization recommendations')
async def analyze_query_performance(
    ctx: Context,
    query: Annotated[str, Field(description='SQL query to analyze')],
    debug: Annotated[bool, Field(description='Include debug information')] = False
) -> str:
    """Analyze query performance and provide optimization recommendations."""
    try:
        logger.info(f"Analyzing query performance for: {query[:100]}...")
        
        # Get query execution plan
        explain_sql = f"EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT) {query}"
        
        try:
            explain_result = await run_query(explain_sql, ctx)
            execution_plan = [row for row in explain_result if 'error' not in row]
        except Exception as e:
            # Fallback to basic EXPLAIN if ANALYZE fails
            logger.warning(f"EXPLAIN ANALYZE failed, trying basic EXPLAIN: {str(e)}")
            basic_explain_sql = f"EXPLAIN {query}"
            explain_result = await run_query(basic_explain_sql, ctx)
            execution_plan = [row for row in explain_result if 'error' not in row]
        
        # Analyze the plan for common issues
        recommendations = []
        expensive_operations = []
        
        for row in execution_plan:
            plan_line = str(row.get('QUERY PLAN', ''))
            
            if 'Seq Scan' in plan_line:
                recommendations.append("Query uses sequential scans - consider adding indexes on filtered columns")
            
            if 'Nested Loop' in plan_line and 'rows=' in plan_line:
                recommendations.append("Nested loop joins detected - verify join conditions and indexes")
            
            if 'Sort' in plan_line and 'cost=' in plan_line:
                recommendations.append("Expensive sort operations detected - consider indexes for ORDER BY clauses")
            
            if 'Hash' in plan_line:
                recommendations.append("Hash operations detected - monitor memory usage for large datasets")
        
        if not recommendations:
            recommendations.append("Query execution plan looks reasonable - no obvious optimization opportunities")
        
        result = {
            "status": "success",
            "data": {
                "query": query,
                "execution_plan": execution_plan,
                "expensive_operations": expensive_operations
            },
            "metadata": {
                "analysis_timestamp": "2025-06-19T13:40:00Z",
                "plan_lines": len(execution_plan)
            },
            "recommendations": recommendations
        }
        
        logger.success("Query performance analysis completed")
        return json.dumps(result, indent=2 if debug else None)
        
    except Exception as e:
        logger.error(f"Query performance analysis failed: {str(e)}")
        return json.dumps({"status": "error", "error": str(e)})


@mcp.tool(name='health_check', description='Check if the server is running and responsive')
async def health_check(ctx: Context) -> Dict[str, Any]:
    """Check if the server is running and responsive."""
    global db_connection
    
    try:
        # Test database connectivity
        connection_test = False
        connection_type = "Unknown"
        try:
            if db_connection:
                connection_info = db_connection.connection_info
                connection_type = connection_info.get('type', 'Unknown')
                test_result = await run_query("SELECT 1 as health_check", ctx)
                connection_test = len(test_result) > 0 and 'error' not in test_result[0]
        except Exception as e:
            logger.warning(f"Health check database test failed: {str(e)}")
        
        database_type = f"PostgreSQL via {connection_type.replace('_', ' ').title()}"
        
        return {
            "status": "healthy" if connection_test else "unhealthy",
            "timestamp": "2025-06-19T15:00:00Z",
            "database_connection": connection_test,
            "server_version": "unified-v1.0",
            "tools_available": 10,
            "database_type": database_type,
            "connection_type": connection_type
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": "2025-06-19T15:00:00Z"
        }


@mcp.tool(name='analyze_vacuum_stats', description='Analyze vacuum statistics and provide recommendations for vacuum settings')
async def analyze_vacuum_stats(
    ctx: Context,
    debug: Annotated[bool, Field(description='Include debug information')] = False
) -> str:
    """Analyze vacuum statistics and provide recommendations for vacuum settings."""
    try:
        logger.info("Analyzing vacuum statistics")
        
        # Get vacuum statistics from pg_stat_user_tables
        vacuum_stats_sql = """
            SELECT 
                schemaname,
                relname as tablename,
                n_tup_ins as total_inserts,
                n_tup_upd as total_updates,
                n_tup_del as total_deletes,
                n_live_tup as live_tuples,
                n_dead_tup as dead_tuples,
                last_vacuum,
                last_autovacuum,
                vacuum_count,
                autovacuum_count,
                CASE 
                    WHEN n_live_tup > 0 
                    THEN round(100.0 * n_dead_tup / (n_live_tup + n_dead_tup), 2)
                    ELSE 0 
                END as dead_tuple_percent
            FROM pg_stat_user_tables
            WHERE n_tup_ins + n_tup_upd + n_tup_del > 0
            ORDER BY 
                CASE 
                    WHEN n_live_tup > 0 
                    THEN 100.0 * n_dead_tup / (n_live_tup + n_dead_tup)
                    ELSE 0 
                END DESC
        """
        
        vacuum_result = await run_query(vacuum_stats_sql, ctx)
        
        # Analyze vacuum settings
        vacuum_settings_sql = """
            SELECT 
                name,
                setting,
                unit,
                short_desc
            FROM pg_settings 
            WHERE name LIKE '%vacuum%' OR name LIKE '%autovacuum%'
            ORDER BY name
        """
        
        settings_result = await run_query(vacuum_settings_sql, ctx)
        
        # Generate recommendations
        recommendations = []
        tables_needing_vacuum = []
        
        for row in vacuum_result:
            if 'error' not in row:
                dead_percent_value = row.get('dead_tuple_percent', '0')
                try:
                    if isinstance(dead_percent_value, str):
                        dead_percent = float(dead_percent_value)
                    else:
                        dead_percent = float(dead_percent_value) if dead_percent_value is not None else 0.0
                    
                    if dead_percent > 20:  # More than 20% dead tuples
                        tables_needing_vacuum.append({
                            'table': f"{row.get('schemaname', '')}.{row.get('tablename', '')}",
                            'dead_percent': dead_percent,
                            'last_vacuum': row.get('last_vacuum'),
                            'last_autovacuum': row.get('last_autovacuum')
                        })
                except (ValueError, TypeError):
                    continue
        
        if tables_needing_vacuum:
            recommendations.append(f"Found {len(tables_needing_vacuum)} tables with >20% dead tuples needing vacuum")
            recommendations.append("Consider running VACUUM on tables with high dead tuple percentages")
        else:
            recommendations.append("All tables have healthy vacuum statistics")
        
        recommendations.extend([
            "Monitor autovacuum settings for optimal performance",
            "Consider adjusting autovacuum_vacuum_threshold for busy tables",
            "Review vacuum scheduling during low-traffic periods"
        ])
        
        result = {
            "status": "success",
            "data": {
                "vacuum_statistics": [row for row in vacuum_result if 'error' not in row],
                "vacuum_settings": [row for row in settings_result if 'error' not in row],
                "tables_needing_vacuum": tables_needing_vacuum
            },
            "metadata": {
                "analysis_timestamp": "2025-06-19T14:10:00Z",
                "total_tables_analyzed": len([row for row in vacuum_result if 'error' not in row]),
                "tables_needing_vacuum": len(tables_needing_vacuum)
            },
            "recommendations": recommendations
        }
        
        logger.success("Vacuum statistics analysis completed")
        return json.dumps(result, indent=2 if debug else None)
        
    except Exception as e:
        logger.error(f"Vacuum statistics analysis failed: {str(e)}")
        return json.dumps({"status": "error", "error": str(e)})


@mcp.tool(name='recommend_indexes', description='Recommend indexes for database optimization based on query patterns')
async def recommend_indexes(
    ctx: Context,
    query: Annotated[Optional[str], Field(description='Specific query to analyze for index recommendations')] = None,
    debug: Annotated[bool, Field(description='Include debug information')] = False
) -> str:
    """Recommend indexes for database optimization based on query patterns."""
    try:
        logger.info(f"Generating index recommendations" + (f" for query: {query[:100]}..." if query else ""))
        
        # Get current indexes
        current_indexes_sql = """
            SELECT 
                schemaname,
                tablename,
                indexname,
                indexdef,
                CASE 
                    WHEN indexdef LIKE '%UNIQUE%' THEN 'UNIQUE'
                    WHEN indexdef LIKE '%btree%' THEN 'BTREE'
                    WHEN indexdef LIKE '%gin%' THEN 'GIN'
                    WHEN indexdef LIKE '%gist%' THEN 'GIST'
                    ELSE 'OTHER'
                END as index_type
            FROM pg_indexes
            WHERE schemaname NOT IN ('information_schema', 'pg_catalog', 'pg_toast')
            ORDER BY schemaname, tablename, indexname
        """
        
        indexes_result = await run_query(current_indexes_sql, ctx)
        
        # Get table statistics for index recommendations
        table_stats_sql = """
            SELECT 
                schemaname,
                tablename,
                attname as column_name,
                n_distinct,
                correlation
            FROM pg_stats
            WHERE schemaname NOT IN ('information_schema', 'pg_catalog', 'pg_toast')
            AND n_distinct IS NOT NULL
            ORDER BY schemaname, tablename, n_distinct DESC
        """
        
        stats_result = await run_query(table_stats_sql, ctx)
        
        # Generate recommendations based on statistics
        recommendations = []
        index_suggestions = []
        
        # Group stats by table
        table_stats = {}
        for row in stats_result:
            if 'error' not in row:
                table_key = f"{row.get('schemaname', '')}.{row.get('tablename', '')}"
                if table_key not in table_stats:
                    table_stats[table_key] = []
                table_stats[table_key].append(row)
        
        # Analyze each table for index opportunities
        for table_name, columns in table_stats.items():
            high_cardinality_cols = []
            
            for col in columns:
                try:
                    n_distinct = col.get('n_distinct', 0)
                    if isinstance(n_distinct, str):
                        n_distinct = float(n_distinct)
                    else:
                        n_distinct = float(n_distinct) if n_distinct is not None else 0
                    
                    if n_distinct > 100:  # High cardinality
                        high_cardinality_cols.append({
                            'column': col.get('column_name'),
                            'n_distinct': n_distinct,
                            'correlation': col.get('correlation')
                        })
                except (ValueError, TypeError):
                    continue
            
            # Generate suggestions for this table
            if high_cardinality_cols:
                for col in high_cardinality_cols[:2]:  # Top 2 high cardinality columns
                    index_suggestions.append({
                        'table': table_name,
                        'suggested_index': f"CREATE INDEX idx_{table_name.split('.')[-1]}_{col['column']} ON {table_name} ({col['column']})",
                        'reason': f"High cardinality column ({col['n_distinct']} distinct values) - good for equality searches",
                        'priority': 'HIGH'
                    })
        
        # If a specific query was provided, analyze it
        if query:
            try:
                explain_result = await run_query(f"EXPLAIN {query}", ctx)
                for row in explain_result:
                    if 'error' not in row:
                        plan_line = str(row.get('QUERY PLAN', ''))
                        if 'Seq Scan' in plan_line:
                            recommendations.append(f"Query uses sequential scan - consider adding indexes on filtered columns")
                        if 'Sort' in plan_line:
                            recommendations.append(f"Query requires sorting - consider indexes on ORDER BY columns")
            except Exception as e:
                logger.warning(f"Could not analyze specific query: {e}")
        
        if not recommendations:
            recommendations = [
                "Review high-cardinality columns for index opportunities",
                "Consider composite indexes for multi-column WHERE clauses",
                "Monitor query performance after adding new indexes",
                "Remove unused indexes to improve write performance"
            ]
        
        result = {
            "status": "success",
            "data": {
                "current_indexes": [row for row in indexes_result if 'error' not in row],
                "table_statistics": [row for row in stats_result if 'error' not in row],
                "index_suggestions": index_suggestions,
                "analyzed_query": query
            },
            "metadata": {
                "analysis_timestamp": "2025-06-19T14:10:00Z",
                "tables_analyzed": len(table_stats),
                "index_suggestions_count": len(index_suggestions)
            },
            "recommendations": recommendations
        }
        
        logger.success("Index recommendations analysis completed")
        return json.dumps(result, indent=2 if debug else None)
        
    except Exception as e:
        logger.error(f"Index recommendations analysis failed: {str(e)}")
        return json.dumps({"status": "error", "error": str(e)})


def main():
    """Main entry point for the MCP server application."""
    global db_connection
    
    parser = argparse.ArgumentParser(
        description='PostgreSQL MCP Server'
    )
    
    # Connection method 1: RDS Data API
    parser.add_argument('--resource_arn', help='ARN of the RDS cluster (for RDS Data API)')
    
    # Connection method 2: Direct PostgreSQL
    parser.add_argument('--hostname', help='Database hostname (for direct PostgreSQL connection)')
    parser.add_argument('--port', type=int, default=5432, help='Database port (default: 5432)')
    
    # Common parameters
    parser.add_argument('--secret_arn', required=True, help='ARN of the Secrets Manager secret for database credentials')
    parser.add_argument('--database', required=True, help='Database name')
    parser.add_argument('--region', required=True, help='AWS region')
    parser.add_argument('--readonly', required=True, help='Enforce readonly SQL statements')
    
    args = parser.parse_args()

    # Validate connection parameters
    if not args.resource_arn and not args.hostname:
        parser.error("Either --resource_arn (for RDS Data API) or --hostname (for direct PostgreSQL) must be provided")
    
    if args.resource_arn and args.hostname:
        parser.error("Cannot specify both --resource_arn and --hostname. Choose one connection method.")

    # Create database connection using ConnectionFactory
    readonly = args.readonly == 'true'
    connection_target = args.resource_arn if args.resource_arn else f"{args.hostname}:{args.port}"
    
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
        logger.info(f'PostgreSQL MCP Server starting with {connection_display} connection to {connection_target}, DATABASE:{args.database}, READONLY:{readonly}')
            
    except Exception as e:
        logger.exception(f'Failed to initialize {connection_display} database connection. Exiting.')
        sys.exit(1)

    # Test database connection with optimized approach
    class DummyCtx:
        async def error(self, message):
            pass

    ctx = DummyCtx()
    
    try:
        connection_type = db_connection.connection_info['type']
        connection_display = connection_type.replace('_', ' ').title()
        
        if connection_type == "rds_data_api":
            # For RDS Data API, test with actual query (fast)
            response = asyncio.run(run_query('SELECT 1', ctx))
            if isinstance(response, list) and len(response) == 1 and isinstance(response[0], dict) and 'error' in response[0]:
                logger.error(f'Failed to validate {connection_display} database connection. Exiting.')
                sys.exit(1)
        else:
            # For Direct PostgreSQL, just validate parameters (fast)
            connection_valid = asyncio.run(db_connection.test_connection_parameters() if hasattr(db_connection, 'test_connection_parameters') else db_connection.connect())
            if not connection_valid:
                logger.warning(f'{connection_display} connection parameters validation failed.')
                logger.warning('Connection will be established on first query.')
            else:
                logger.info(f'{connection_display} connection parameters validated successfully.')
        
    except Exception as e:
        logger.warning(f'Connection validation failed: {str(e)}')
        logger.warning('Server will start anyway - connection will be attempted on first query.')

    logger.success(f'PostgreSQL MCP Server initialized with {connection_display}')
    logger.info('Starting enhanced PostgreSQL MCP Server with stdio transport')
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
