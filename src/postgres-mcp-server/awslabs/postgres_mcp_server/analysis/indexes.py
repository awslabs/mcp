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

"""Index recommendation analysis tools."""

import time
import re
from typing import Dict, List, Any
from loguru import logger
from ..connection.base_connection import DBConnector


async def recommend_indexes(
    connection: DBConnector,
    query: str
) -> Dict[str, Any]:
    """
    Recommend indexes for a given SQL query.
    
    Args:
        connection: Database connection instance
        query: SQL query to analyze for index recommendations
        
    Returns:
        Dictionary containing index recommendations
    """
    analysis_start = time.time()
    logger.info(f"Starting index recommendation analysis for query: {query[:100]}...")
    
    try:
        # Parse the query to identify tables and columns
        query_analysis = _parse_query_for_indexes(query)
        
        # Get current indexes for the tables involved
        current_indexes = await _get_current_indexes(connection, query_analysis["tables"])
        
        # Analyze query execution plan
        execution_plan = await _analyze_query_plan_for_indexes(connection, query)
        
        # Generate index recommendations
        recommendations = _generate_index_recommendations(
            query_analysis, current_indexes, execution_plan
        )
        
        # Estimate impact of recommended indexes
        impact_analysis = await _estimate_index_impact(connection, recommendations, query)
        
        analysis_time = time.time() - analysis_start
        
        result = {
            "status": "success",
            "data": {
                "query": query,
                "query_analysis": query_analysis,
                "current_indexes": current_indexes,
                "execution_plan_summary": execution_plan,
                "recommended_indexes": recommendations,
                "impact_analysis": impact_analysis
            },
            "metadata": {
                "analysis_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "analysis_time_ms": round(analysis_time * 1000, 2),
                "tables_analyzed": len(query_analysis["tables"])
            },
            "recommendations": _format_index_recommendations(recommendations)
        }
        
        logger.success("Index recommendation analysis completed successfully")
        return result
        
    except Exception as e:
        logger.error(f"Index recommendation analysis failed: {str(e)}")
        return {
            "status": "error",
            "error": {
                "step": "analyzing_index_recommendations",
                "message": str(e),
                "suggestions": [
                    "Ensure the query syntax is valid",
                    "Verify database connection is active",
                    "Check if user has necessary permissions to access table metadata"
                ]
            },
            "partial_data": {"query": query}
        }


def _parse_query_for_indexes(query: str) -> Dict[str, Any]:
    """Parse SQL query to identify tables, columns, and conditions for index analysis."""
    query_lower = query.lower()
    
    # Extract tables from FROM and JOIN clauses
    tables = set()
    
    # Find FROM clause
    from_match = re.search(r'\bfrom\s+([^\s,]+)', query_lower)
    if from_match:
        tables.add(from_match.group(1).strip())
    
    # Find JOIN clauses
    join_matches = re.findall(r'\bjoin\s+([^\s,]+)', query_lower)
    for match in join_matches:
        tables.add(match.strip())
    
    # Extract WHERE conditions
    where_conditions = []
    where_match = re.search(r'\bwhere\s+(.+?)(?:\bgroup\s+by|\border\s+by|\blimit|\bhaving|$)', query_lower, re.DOTALL)
    if where_match:
        where_clause = where_match.group(1).strip()
        # Simple parsing of conditions (can be enhanced)
        conditions = re.split(r'\s+and\s+|\s+or\s+', where_clause)
        for condition in conditions:
            # Extract column names from conditions like "column = value" or "column > value"
            col_match = re.search(r'([a-zA-Z_][a-zA-Z0-9_]*)\s*[=<>!]+', condition)
            if col_match:
                where_conditions.append({
                    "column": col_match.group(1),
                    "condition": condition.strip(),
                    "operator": re.search(r'[=<>!]+', condition).group() if re.search(r'[=<>!]+', condition) else "="
                })
    
    # Extract ORDER BY columns
    order_by_columns = []
    order_match = re.search(r'\border\s+by\s+([^;]+)', query_lower)
    if order_match:
        order_clause = order_match.group(1).strip()
        order_parts = [part.strip() for part in order_clause.split(',')]
        for part in order_parts:
            col_match = re.search(r'([a-zA-Z_][a-zA-Z0-9_]*)', part)
            if col_match:
                direction = "DESC" if "desc" in part else "ASC"
                order_by_columns.append({
                    "column": col_match.group(1),
                    "direction": direction
                })
    
    # Extract GROUP BY columns
    group_by_columns = []
    group_match = re.search(r'\bgroup\s+by\s+([^;]+?)(?:\border\s+by|\blimit|\bhaving|$)', query_lower)
    if group_match:
        group_clause = group_match.group(1).strip()
        group_parts = [part.strip() for part in group_clause.split(',')]
        for part in group_parts:
            col_match = re.search(r'([a-zA-Z_][a-zA-Z0-9_]*)', part)
            if col_match:
                group_by_columns.append(col_match.group(1))
    
    return {
        "tables": list(tables),
        "where_conditions": where_conditions,
        "order_by_columns": order_by_columns,
        "group_by_columns": group_by_columns,
        "query_type": _determine_query_type(query_lower)
    }


def _determine_query_type(query_lower: str) -> str:
    """Determine the type of SQL query."""
    if query_lower.strip().startswith('select'):
        return 'SELECT'
    elif query_lower.strip().startswith('insert'):
        return 'INSERT'
    elif query_lower.strip().startswith('update'):
        return 'UPDATE'
    elif query_lower.strip().startswith('delete'):
        return 'DELETE'
    else:
        return 'UNKNOWN'


async def _get_current_indexes(
    connection: DBConnector,
    tables: List[str]
) -> Dict[str, List[Dict[str, Any]]]:
    """Get current indexes for the specified tables."""
    current_indexes = {}
    
    for table in tables:
        try:
            # Get indexes for this table
            index_query = """
                SELECT
                    i.relname as index_name,
                    a.attname as column_name,
                    ix.indisunique as is_unique,
                    ix.indisprimary as is_primary,
                    am.amname as index_type,
                    pg_size_pretty(pg_relation_size(i.oid)) as size
                FROM pg_class t
                JOIN pg_index ix ON t.oid = ix.indrelid
                JOIN pg_class i ON i.oid = ix.indexrelid
                JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = ANY(ix.indkey)
                JOIN pg_am am ON i.relam = am.oid
                WHERE t.relname = :table_name
                ORDER BY i.relname, a.attnum
            """
            
            params = [{'name': 'table_name', 'value': {'stringValue': table}}]
            result = await connection.execute_query(index_query, params)
            
            table_indexes = []
            for row in result.get('records', []):
                table_indexes.append({
                    "name": row[0]['stringValue'],
                    "column": row[1]['stringValue'],
                    "unique": row[2]['booleanValue'] if not row[2].get('isNull') else False,
                    "primary": row[3]['booleanValue'] if not row[3].get('isNull') else False,
                    "type": row[4]['stringValue'],
                    "size": row[5]['stringValue'] if not row[5].get('isNull') else '0 bytes'
                })
            
            current_indexes[table] = table_indexes
            
        except Exception as e:
            logger.warning(f"Failed to get indexes for table {table}: {str(e)}")
            current_indexes[table] = []
    
    return current_indexes


async def _analyze_query_plan_for_indexes(
    connection: DBConnector,
    query: str
) -> Dict[str, Any]:
    """Analyze query execution plan to identify index opportunities."""
    try:
        explain_query = f"EXPLAIN (ANALYZE, BUFFERS) {query}"
        result = await connection.execute_query(explain_query)
        
        plan_analysis = {
            "sequential_scans": [],
            "expensive_sorts": [],
            "hash_joins": [],
            "nested_loops": []
        }
        
        for row in result.get('records', []):
            plan_line = row[0]['stringValue']
            
            # Look for sequential scans
            if "Seq Scan" in plan_line:
                table_match = re.search(r'on\s+([a-zA-Z_][a-zA-Z0-9_]*)', plan_line)
                if table_match:
                    plan_analysis["sequential_scans"].append(table_match.group(1))
            
            # Look for expensive sorts
            if "Sort" in plan_line and "cost=" in plan_line:
                cost_match = re.search(r'cost=[\d.]+\.\.(\d+\.?\d*)', plan_line)
                if cost_match and float(cost_match.group(1)) > 1000:
                    plan_analysis["expensive_sorts"].append(plan_line)
            
            # Look for hash joins
            if "Hash Join" in plan_line:
                plan_analysis["hash_joins"].append(plan_line)
            
            # Look for nested loops
            if "Nested Loop" in plan_line:
                plan_analysis["nested_loops"].append(plan_line)
        
        return plan_analysis
        
    except Exception as e:
        logger.warning(f"Failed to analyze query plan: {str(e)}")
        return {"error": str(e)}


def _generate_index_recommendations(
    query_analysis: Dict[str, Any],
    current_indexes: Dict[str, List[Dict[str, Any]]],
    execution_plan: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Generate index recommendations based on query analysis."""
    recommendations = []
    
    # Recommend indexes for WHERE clause conditions
    for condition in query_analysis.get("where_conditions", []):
        column = condition["column"]
        
        # Check if index already exists for this column
        has_index = False
        for table in query_analysis["tables"]:
            table_indexes = current_indexes.get(table, [])
            if any(idx["column"] == column for idx in table_indexes):
                has_index = True
                break
        
        if not has_index:
            recommendations.append({
                "type": "single_column",
                "column": column,
                "reason": f"WHERE clause condition: {condition['condition']}",
                "priority": "high" if condition["operator"] == "=" else "medium",
                "sql": f"CREATE INDEX idx_{column} ON table_name ({column});"
            })
    
    # Recommend indexes for ORDER BY columns
    if query_analysis.get("order_by_columns"):
        order_columns = [col["column"] for col in query_analysis["order_by_columns"]]
        
        # Check if composite index exists
        has_composite = False
        for table in query_analysis["tables"]:
            table_indexes = current_indexes.get(table, [])
            # Simple check - can be enhanced to check actual composite indexes
            if len([idx for idx in table_indexes if idx["column"] in order_columns]) >= len(order_columns):
                has_composite = True
                break
        
        if not has_composite and len(order_columns) > 1:
            recommendations.append({
                "type": "composite",
                "columns": order_columns,
                "reason": "ORDER BY clause optimization",
                "priority": "medium",
                "sql": f"CREATE INDEX idx_composite ON table_name ({', '.join(order_columns)});"
            })
    
    # Recommend indexes based on execution plan
    if "sequential_scans" in execution_plan:
        for table in execution_plan["sequential_scans"]:
            if table in query_analysis["tables"]:
                # Find columns that could benefit from indexing
                where_columns = [cond["column"] for cond in query_analysis.get("where_conditions", [])]
                for column in where_columns:
                    recommendations.append({
                        "type": "performance",
                        "column": column,
                        "table": table,
                        "reason": f"Sequential scan detected on table {table}",
                        "priority": "high",
                        "sql": f"CREATE INDEX idx_{table}_{column} ON {table} ({column});"
                    })
    
    # Remove duplicates
    unique_recommendations = []
    seen = set()
    for rec in recommendations:
        key = (rec.get("column", ""), rec.get("table", ""), rec["type"])
        if key not in seen:
            seen.add(key)
            unique_recommendations.append(rec)
    
    return unique_recommendations


async def _estimate_index_impact(
    connection: DBConnector,
    recommendations: List[Dict[str, Any]],
    query: str
) -> Dict[str, Any]:
    """Estimate the impact of recommended indexes."""
    impact_analysis = {
        "estimated_improvements": [],
        "storage_overhead": "Unknown",
        "maintenance_overhead": "Low to Medium"
    }
    
    try:
        # Get current query cost
        explain_query = f"EXPLAIN {query}"
        result = await connection.execute_query(explain_query)
        
        current_cost = 0
        for row in result.get('records', []):
            plan_line = row[0]['stringValue']
            cost_match = re.search(r'cost=[\d.]+\.\.(\d+\.?\d*)', plan_line)
            if cost_match:
                current_cost = max(current_cost, float(cost_match.group(1)))
        
        # Estimate improvements
        for rec in recommendations:
            if rec["priority"] == "high":
                estimated_improvement = "30-70% query performance improvement"
            elif rec["priority"] == "medium":
                estimated_improvement = "10-30% query performance improvement"
            else:
                estimated_improvement = "5-15% query performance improvement"
            
            impact_analysis["estimated_improvements"].append({
                "recommendation": rec["reason"],
                "improvement": estimated_improvement
            })
        
        impact_analysis["current_query_cost"] = current_cost
        
    except Exception as e:
        logger.warning(f"Failed to estimate index impact: {str(e)}")
        impact_analysis["error"] = str(e)
    
    return impact_analysis


def _format_index_recommendations(recommendations: List[Dict[str, Any]]) -> List[str]:
    """Format index recommendations as human-readable strings."""
    formatted = []
    
    for rec in recommendations:
        if rec["type"] == "single_column":
            formatted.append(f"Create index on column '{rec['column']}' - {rec['reason']}")
        elif rec["type"] == "composite":
            columns_str = "', '".join(rec["columns"])
            formatted.append(f"Create composite index on columns '{columns_str}' - {rec['reason']}")
        elif rec["type"] == "performance":
            formatted.append(f"Create index on table '{rec['table']}' column '{rec['column']}' - {rec['reason']}")
        else:
            formatted.append(f"Index recommendation: {rec['reason']}")
    
    if not formatted:
        formatted.append("No specific index recommendations - query appears to be using indexes effectively")
    
    return formatted
