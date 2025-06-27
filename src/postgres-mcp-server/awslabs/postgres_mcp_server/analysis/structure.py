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

"""Database structure analysis tools."""

from ..connection.base_connection import DBConnector
from loguru import logger
from typing import Any, Dict, List


async def analyze_database_structure(
    connection: DBConnector
) -> Dict[str, Any]:
    """
    Analyze the database structure and provide comprehensive insights.

    Args:
        connection: Database connection instance

    Returns:
        Dictionary containing structured analysis results
    """
    logger.info("Starting comprehensive database structure analysis")

    try:
        # Get schemas
        schemas = await _get_schemas(connection)

        # Get tables with detailed information
        tables = await _get_tables_detailed(connection)

        # Get relationships
        relationships = await _get_relationships(connection)

        # Get indexes
        indexes = await _get_indexes(connection)

        # Get views
        views = await _get_views(connection)

        # Get functions and procedures
        functions = await _get_functions(connection)

        # Generate recommendations
        recommendations = _generate_structure_recommendations(tables, indexes, relationships)

        result = {
            "status": "success",
            "data": {
                "schemas": schemas,
                "tables": tables,
                "relationships": relationships,
                "indexes": indexes,
                "views": views,
                "functions": functions
            },
            "metadata": {
                "analysis_timestamp": logger.info("Database structure analysis completed"),
                "total_schemas": len(schemas),
                "total_tables": len(tables),
                "total_relationships": len(relationships),
                "total_indexes": len(indexes)
            },
            "recommendations": recommendations
        }

        logger.success("Database structure analysis completed successfully")
        return result

    except Exception as e:
        logger.error(f"Database structure analysis failed: {str(e)}")
        return {
            "status": "error",
            "error": {
                "step": "analyzing_database_structure",
                "message": str(e),
                "suggestions": [
                    "Ensure database connection is active",
                    "Verify user has necessary permissions to access system catalogs",
                    "Check if database is accessible and not under maintenance"
                ]
            },
            "partial_data": {}
        }


async def _get_schemas(connection: DBConnector) -> List[str]:
    """Get all schemas in the database."""
    query = """
        SELECT schema_name
        FROM information_schema.schemata
        WHERE schema_name NOT IN ('information_schema', 'pg_catalog', 'pg_toast')
        ORDER BY schema_name
    """

    result = await connection.execute_query(query)
    return [row[0]['stringValue'] for row in result.get('records', [])]


async def _get_tables_detailed(connection: DBConnector) -> List[Dict[str, Any]]:
    """Get detailed information about all tables."""
    query = """
        SELECT
            t.table_schema,
            t.table_name,
            pg_size_pretty(pg_total_relation_size(c.oid)) as size,
            pg_total_relation_size(c.oid) as size_bytes,
            c.reltuples::bigint as estimated_rows,
            obj_description(c.oid) as table_comment
        FROM information_schema.tables t
        JOIN pg_class c ON c.relname = t.table_name
        JOIN pg_namespace n ON n.oid = c.relnamespace AND n.nspname = t.table_schema
        WHERE t.table_type = 'BASE TABLE'
        AND t.table_schema NOT IN ('information_schema', 'pg_catalog', 'pg_toast')
        ORDER BY t.table_schema, t.table_name
    """

    result = await connection.execute_query(query)
    tables = []

    for row in result.get('records', []):
        table_info = {
            "schema": row[0]['stringValue'],
            "name": row[1]['stringValue'],
            "size": row[2]['stringValue'] if not row[2].get('isNull') else '0 bytes',
            "size_bytes": row[3]['longValue'] if not row[3].get('isNull') else 0,
            "estimated_rows": row[4]['longValue'] if not row[4].get('isNull') else 0,
            "comment": row[5]['stringValue'] if not row[5].get('isNull') else None
        }

        # Get column information for this table
        table_info["columns"] = await _get_table_columns(connection, table_info["schema"], table_info["name"])
        tables.append(table_info)

    return tables


async def _get_table_columns(connection: DBConnector, schema: str, table: str) -> List[Dict[str, Any]]:
    """Get column information for a specific table."""
    query = """
        SELECT
            column_name,
            data_type,
            is_nullable,
            column_default,
            character_maximum_length,
            numeric_precision,
            numeric_scale,
            col_description(pgc.oid, a.attnum) as column_comment
        FROM information_schema.columns c
        JOIN pg_class pgc ON pgc.relname = c.table_name
        JOIN pg_namespace n ON n.oid = pgc.relnamespace AND n.nspname = c.table_schema
        JOIN pg_attribute a ON a.attrelid = pgc.oid AND a.attname = c.column_name
        WHERE c.table_schema = :schema AND c.table_name = :table
        ORDER BY c.ordinal_position
    """

    params = [
        {'name': 'schema', 'value': {'stringValue': schema}},
        {'name': 'table', 'value': {'stringValue': table}}
    ]

    result = await connection.execute_query(query, params)
    columns = []

    for row in result.get('records', []):
        columns.append({
            "name": row[0]['stringValue'],
            "data_type": row[1]['stringValue'],
            "nullable": row[2]['stringValue'] == 'YES',
            "default": row[3]['stringValue'] if not row[3].get('isNull') else None,
            "max_length": row[4]['longValue'] if not row[4].get('isNull') else None,
            "precision": row[5]['longValue'] if not row[5].get('isNull') else None,
            "scale": row[6]['longValue'] if not row[6].get('isNull') else None,
            "comment": row[7]['stringValue'] if not row[7].get('isNull') else None
        })

    return columns


async def _get_relationships(connection: DBConnector) -> List[Dict[str, Any]]:
    """Get foreign key relationships between tables."""
    query = """
        SELECT
            tc.constraint_name,
            tc.table_schema as parent_schema,
            tc.table_name as parent_table,
            kcu.column_name as parent_column,
            ccu.table_schema as child_schema,
            ccu.table_name as child_table,
            ccu.column_name as child_column,
            rc.update_rule,
            rc.delete_rule
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
            ON tc.constraint_name = kcu.constraint_name
            AND tc.table_schema = kcu.table_schema
        JOIN information_schema.constraint_column_usage ccu
            ON ccu.constraint_name = tc.constraint_name
            AND ccu.table_schema = tc.table_schema
        JOIN information_schema.referential_constraints rc
            ON tc.constraint_name = rc.constraint_name
            AND tc.table_schema = rc.constraint_schema
        WHERE tc.constraint_type = 'FOREIGN KEY'
        ORDER BY tc.table_schema, tc.table_name, tc.constraint_name
    """

    result = await connection.execute_query(query)
    relationships = []

    for row in result.get('records', []):
        relationships.append({
            "constraint_name": row[0]['stringValue'],
            "parent_schema": row[1]['stringValue'],
            "parent_table": row[2]['stringValue'],
            "parent_column": row[3]['stringValue'],
            "child_schema": row[4]['stringValue'],
            "child_table": row[5]['stringValue'],
            "child_column": row[6]['stringValue'],
            "update_rule": row[7]['stringValue'],
            "delete_rule": row[8]['stringValue']
        })

    return relationships


async def _get_indexes(connection: DBConnector) -> List[Dict[str, Any]]:
    """Get index information for all tables."""
    query = """
        SELECT
            schemaname,
            tablename,
            indexname,
            indexdef,
            pg_size_pretty(pg_relation_size(indexrelid)) as size
        FROM pg_indexes
        WHERE schemaname NOT IN ('information_schema', 'pg_catalog', 'pg_toast')
        ORDER BY schemaname, tablename, indexname
    """

    result = await connection.execute_query(query)
    indexes = []

    for row in result.get('records', []):
        indexes.append({
            "schema": row[0]['stringValue'],
            "table": row[1]['stringValue'],
            "name": row[2]['stringValue'],
            "definition": row[3]['stringValue'],
            "size": row[4]['stringValue'] if not row[4].get('isNull') else '0 bytes'
        })

    return indexes


async def _get_views(connection: DBConnector) -> List[Dict[str, Any]]:
    """Get view information."""
    query = """
        SELECT
            table_schema,
            table_name,
            view_definition
        FROM information_schema.views
        WHERE table_schema NOT IN ('information_schema', 'pg_catalog', 'pg_toast')
        ORDER BY table_schema, table_name
    """

    result = await connection.execute_query(query)
    views = []

    for row in result.get('records', []):
        views.append({
            "schema": row[0]['stringValue'],
            "name": row[1]['stringValue'],
            "definition": row[2]['stringValue']
        })

    return views


async def _get_functions(connection: DBConnector) -> List[Dict[str, Any]]:
    """Get function and procedure information."""
    query = """
        SELECT
            n.nspname as schema_name,
            p.proname as function_name,
            pg_get_function_result(p.oid) as return_type,
            pg_get_function_arguments(p.oid) as arguments,
            CASE p.prokind
                WHEN 'f' THEN 'function'
                WHEN 'p' THEN 'procedure'
                WHEN 'a' THEN 'aggregate'
                WHEN 'w' THEN 'window'
                ELSE 'unknown'
            END as function_type
        FROM pg_proc p
        JOIN pg_namespace n ON p.pronamespace = n.oid
        WHERE n.nspname NOT IN ('information_schema', 'pg_catalog', 'pg_toast')
        ORDER BY n.nspname, p.proname
    """

    result = await connection.execute_query(query)
    functions = []

    for row in result.get('records', []):
        functions.append({
            "schema": row[0]['stringValue'],
            "name": row[1]['stringValue'],
            "return_type": row[2]['stringValue'] if not row[2].get('isNull') else None,
            "arguments": row[3]['stringValue'] if not row[3].get('isNull') else None,
            "type": row[4]['stringValue']
        })

    return functions


def _generate_structure_recommendations(tables: List[Dict[str, Any]], indexes: List[Dict[str, Any]], relationships: List[Dict[str, Any]]) -> List[str]:
    """Generate recommendations based on database structure analysis."""
    recommendations = []

    # Check for tables without primary keys
    for table in tables:
        has_pk = any(col.get('constraint_type') == 'PRIMARY KEY' for col in table.get('columns', []))
        if not has_pk:
            recommendations.append(f"Table '{table['schema']}.{table['name']}' appears to lack a primary key")

    # Check for large tables without indexes
    table_index_map = {}
    for index in indexes:
        key = f"{index['schema']}.{index['table']}"
        if key not in table_index_map:
            table_index_map[key] = []
        table_index_map[key].append(index)

    for table in tables:
        table_key = f"{table['schema']}.{table['name']}"
        table_indexes = table_index_map.get(table_key, [])

        if table['estimated_rows'] > 10000 and len(table_indexes) <= 1:  # Only primary key
            recommendations.append(f"Large table '{table_key}' ({table['estimated_rows']} rows) has few indexes - consider adding indexes for frequently queried columns")

    # Check for orphaned tables (no relationships)
    tables_with_fk = set()
    for rel in relationships:
        tables_with_fk.add(f"{rel['parent_schema']}.{rel['parent_table']}")
        tables_with_fk.add(f"{rel['child_schema']}.{rel['child_table']}")

    for table in tables:
        table_key = f"{table['schema']}.{table['name']}"
        if table_key not in tables_with_fk and table['estimated_rows'] > 0:
            recommendations.append(f"Table '{table_key}' has no foreign key relationships - verify if this is intentional")

    return recommendations
