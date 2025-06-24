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

"""Query performance analysis tools."""

import time
from typing import Dict, List, Any
from loguru import logger
from ..connection.base_connection import DBConnector


async def analyze_query_performance(
    connection: DBConnector,
    query: str
) -> Dict[str, Any]:
    """
    Analyze query performance and provide optimization recommendations.
    
    Args:
        connection: Database connection instance
        query: SQL query to analyze
        
    Returns:
        Dictionary containing performance analysis results
    """
    analysis_start = time.time()
    logger.info(f"Starting query performance analysis for: {query[:100]}...")
    
    try:
        # Get query execution plan
        explain_plan = await _get_execution_plan(connection, query)
        
        # Analyze the plan
        plan_analysis = _analyze_execution_plan(explain_plan)
        
        # Get query statistics if available
        query_stats = await _get_query_statistics(connection, query)
        
        # Generate recommendations
        recommendations = _generate_performance_recommendations(plan_analysis, query_stats)
        
        analysis_time = time.time() - analysis_start
        
        result = {
            "status": "success",
            "data": {
                "query": query,
                "execution_plan": explain_plan,
                "plan_analysis": plan_analysis,
                "query_statistics": query_stats
            },
            "metadata": {
                "analysis_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "analysis_time_ms": round(analysis_time * 1000, 2)
            },
            "recommendations": recommendations
        }
        
        logger.success("Query performance analysis completed successfully")
        return result
        
    except Exception as e:
        logger.error(f"Query performance analysis failed: {str(e)}")
        return {
            "status": "error",
            "error": {
                "step": "analyzing_query_performance",
                "message": str(e),
                "suggestions": [
                    "Ensure the query syntax is valid",
                    "Verify database connection is active",
                    "Check if user has necessary permissions to run EXPLAIN"
                ]
            },
            "partial_data": {"query": query}
        }


async def _get_execution_plan(
    connection: DBConnector,
    query: str
) -> List[Dict[str, Any]]:
    """Get the execution plan for a query."""
    explain_query = f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {query}"
    
    try:
        result = await connection.execute_query(explain_query)
        
        # Extract the JSON plan from the result
        if result.get('records'):
            plan_json = result['records'][0][0]['stringValue']
            import json
            return json.loads(plan_json)
        else:
            return []
            
    except Exception as e:
        logger.warning(f"Failed to get detailed execution plan, trying basic EXPLAIN: {str(e)}")
        
        # Fallback to basic EXPLAIN
        basic_explain = f"EXPLAIN {query}"
        result = await connection.execute_query(basic_explain)
        
        plan_lines = []
        for row in result.get('records', []):
            plan_lines.append({"Plan": row[0]['stringValue']})
        
        return plan_lines


def _analyze_execution_plan(plan: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze the execution plan and extract key metrics."""
    if not plan:
        return {"error": "No execution plan available"}
    
    analysis = {
        "total_cost": 0,
        "execution_time_ms": 0,
        "rows_processed": 0,
        "expensive_operations": [],
        "scan_types": [],
        "join_types": [],
        "index_usage": []
    }
    
    try:
        # Handle JSON format plan
        if isinstance(plan, list) and len(plan) > 0 and "Plan" in plan[0]:
            root_plan = plan[0]["Plan"]
            _extract_plan_metrics(root_plan, analysis)
        else:
            # Handle text format plan
            for line in plan:
                if isinstance(line, dict) and "Plan" in line:
                    plan_text = line["Plan"]
                    _extract_text_plan_metrics(plan_text, analysis)
    
    except Exception as e:
        logger.warning(f"Error analyzing execution plan: {str(e)}")
        analysis["error"] = str(e)
    
    return analysis


def _extract_plan_metrics(plan_node: Dict[str, Any], analysis: Dict[str, Any]):
    """Extract metrics from a JSON execution plan node."""
    # Extract basic metrics
    if "Total Cost" in plan_node:
        analysis["total_cost"] = max(analysis["total_cost"], plan_node["Total Cost"])
    
    if "Actual Total Time" in plan_node:
        analysis["execution_time_ms"] += plan_node["Actual Total Time"]
    
    if "Actual Rows" in plan_node:
        analysis["rows_processed"] += plan_node["Actual Rows"]
    
    # Identify expensive operations
    node_type = plan_node.get("Node Type", "")
    if "Total Cost" in plan_node and plan_node["Total Cost"] > 1000:
        analysis["expensive_operations"].append({
            "operation": node_type,
            "cost": plan_node["Total Cost"],
            "rows": plan_node.get("Actual Rows", 0)
        })
    
    # Track scan types
    if "Scan" in node_type:
        analysis["scan_types"].append(node_type)
    
    # Track join types
    if "Join" in node_type:
        analysis["join_types"].append(node_type)
    
    # Track index usage
    if "Index" in node_type:
        index_name = plan_node.get("Index Name", "unknown")
        analysis["index_usage"].append({
            "index_name": index_name,
            "scan_type": node_type
        })
    
    # Recursively process child plans
    for child in plan_node.get("Plans", []):
        _extract_plan_metrics(child, analysis)


def _extract_text_plan_metrics(plan_text: str, analysis: Dict[str, Any]):
    """Extract basic metrics from text execution plan."""
    # Basic pattern matching for text plans
    if "Seq Scan" in plan_text:
        analysis["scan_types"].append("Sequential Scan")
    elif "Index Scan" in plan_text:
        analysis["scan_types"].append("Index Scan")
    elif "Bitmap" in plan_text:
        analysis["scan_types"].append("Bitmap Scan")
    
    if "Hash Join" in plan_text:
        analysis["join_types"].append("Hash Join")
    elif "Nested Loop" in plan_text:
        analysis["join_types"].append("Nested Loop")
    elif "Merge Join" in plan_text:
        analysis["join_types"].append("Merge Join")


async def _get_query_statistics(
    connection: DBConnector,
    query: str
) -> Dict[str, Any]:
    """Get query statistics from pg_stat_statements if available."""
    try:
        # Check if pg_stat_statements extension is available
        check_extension = """
            SELECT EXISTS (
                SELECT 1 FROM pg_extension WHERE extname = 'pg_stat_statements'
            )
        """
        
        result = await connection.execute_query(check_extension)
        has_extension = result['records'][0][0]['booleanValue'] if result.get('records') else False
        
        if not has_extension:
            return {"error": "pg_stat_statements extension not available"}
        
        # Get statistics for similar queries
        stats_query = """
            SELECT 
                calls,
                total_exec_time,
                mean_exec_time,
                rows,
                100.0 * shared_blks_hit / nullif(shared_blks_hit + shared_blks_read, 0) AS hit_percent
            FROM pg_stat_statements 
            WHERE query ILIKE %s
            LIMIT 1
        """
        
        # Use a pattern to match similar queries
        query_pattern = f"%{query.split()[0]}%"  # Match queries starting with same keyword
        params = [{'name': 'pattern', 'value': {'stringValue': query_pattern}}]
        
        result = await connection.execute_query(stats_query, params)
        
        if result.get('records'):
            row = result['records'][0]
            return {
                "calls": row[0]['longValue'] if not row[0].get('isNull') else 0,
                "total_exec_time": row[1]['doubleValue'] if not row[1].get('isNull') else 0,
                "mean_exec_time": row[2]['doubleValue'] if not row[2].get('isNull') else 0,
                "rows": row[3]['longValue'] if not row[3].get('isNull') else 0,
                "cache_hit_percent": row[4]['doubleValue'] if not row[4].get('isNull') else 0
            }
        else:
            return {"message": "No statistics available for this query pattern"}
            
    except Exception as e:
        logger.warning(f"Failed to get query statistics: {str(e)}")
        return {"error": str(e)}


def _generate_performance_recommendations(
    plan_analysis: Dict[str, Any],
    query_stats: Dict[str, Any]
) -> List[str]:
    """Generate performance recommendations based on analysis."""
    recommendations = []
    
    # Analyze scan types
    scan_types = plan_analysis.get("scan_types", [])
    if "Sequential Scan" in scan_types:
        recommendations.append("Query uses sequential scans - consider adding indexes on frequently filtered columns")
    
    # Analyze join types
    join_types = plan_analysis.get("join_types", [])
    if "Nested Loop" in join_types and plan_analysis.get("rows_processed", 0) > 10000:
        recommendations.append("Nested loop joins on large datasets - consider optimizing join conditions or adding indexes")
    
    # Analyze expensive operations
    expensive_ops = plan_analysis.get("expensive_operations", [])
    if expensive_ops:
        for op in expensive_ops:
            recommendations.append(f"Expensive operation detected: {op['operation']} (cost: {op['cost']}) - consider optimization")
    
    # Analyze query statistics
    if "cache_hit_percent" in query_stats and query_stats["cache_hit_percent"] < 95:
        recommendations.append(f"Low buffer cache hit ratio ({query_stats['cache_hit_percent']:.1f}%) - consider increasing shared_buffers")
    
    if "mean_exec_time" in query_stats and query_stats["mean_exec_time"] > 1000:
        recommendations.append(f"High average execution time ({query_stats['mean_exec_time']:.2f}ms) - query optimization recommended")
    
    # General recommendations
    if not recommendations:
        recommendations.append("Query appears to be well-optimized based on available metrics")
    
    return recommendations
