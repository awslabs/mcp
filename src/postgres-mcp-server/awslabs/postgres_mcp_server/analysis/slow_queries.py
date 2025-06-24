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

"""Slow query identification and analysis tools."""

import time
from typing import Dict, List, Any
from loguru import logger
from ..connection.base_connection import DBConnector


async def identify_slow_queries(
    connection: DBConnector,
    min_execution_time: float = 100.0,
    limit: int = 20
) -> Dict[str, Any]:
    """
    Identify slow-running queries in the database.
    
    Args:
        connection: Database connection instance
        min_execution_time: Minimum execution time in milliseconds (default: 100ms)
        limit: Maximum number of queries to return (default: 20)
        
    Returns:
        Dictionary containing slow query analysis results
    """
    analysis_start = time.time()
    logger.info(f"Starting slow query analysis (min_time: {min_execution_time}ms, limit: {limit})")
    
    try:
        # Check if pg_stat_statements extension is available
        extension_available = await _check_pg_stat_statements(connection)
        
        if not extension_available:
            return {
                "status": "error",
                "error": {
                    "step": "checking_pg_stat_statements",
                    "message": "pg_stat_statements extension is not available",
                    "suggestions": [
                        "Install pg_stat_statements extension: CREATE EXTENSION pg_stat_statements;",
                        "Add 'pg_stat_statements' to shared_preload_libraries in postgresql.conf",
                        "Restart PostgreSQL server after configuration change",
                        "For RDS instances, modify the parameter group and restart the instance"
                    ]
                },
                "partial_data": {}
            }
        
        # Get slow queries from pg_stat_statements
        slow_queries = await _get_slow_queries(connection, min_execution_time, limit)
        
        # Analyze query patterns
        query_analysis = _analyze_query_patterns(slow_queries)
        
        # Get current running queries
        current_queries = await _get_current_long_running_queries(connection)
        
        # Generate recommendations
        recommendations = _generate_slow_query_recommendations(slow_queries, query_analysis)
        
        analysis_time = time.time() - analysis_start
        
        result = {
            "status": "success",
            "data": {
                "slow_queries": slow_queries,
                "query_patterns": query_analysis,
                "current_long_running": current_queries,
                "min_execution_time_ms": min_execution_time,
                "limit": limit
            },
            "metadata": {
                "analysis_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "analysis_time_ms": round(analysis_time * 1000, 2),
                "slow_queries_found": len(slow_queries),
                "current_long_running": len(current_queries)
            },
            "recommendations": recommendations
        }
        
        logger.success("Slow query analysis completed successfully")
        return result
        
    except Exception as e:
        logger.error(f"Slow query analysis failed: {str(e)}")
        return {
            "status": "error",
            "error": {
                "step": "analyzing_slow_queries",
                "message": str(e),
                "suggestions": [
                    "Ensure database connection is active",
                    "Verify user has necessary permissions to access pg_stat_statements",
                    "Check if pg_stat_statements extension is properly configured"
                ]
            },
            "partial_data": {
                "min_execution_time_ms": min_execution_time,
                "limit": limit
            }
        }


async def _check_pg_stat_statements(connection: DBConnector) -> bool:
    """Check if pg_stat_statements extension is available and enabled."""
    try:
        query = "SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'pg_stat_statements')"
        result = await connection.execute_query(query)
        
        if result.get('records'):
            return result['records'][0][0]['booleanValue']
        return False
        
    except Exception as e:
        logger.warning(f"Failed to check pg_stat_statements availability: {str(e)}")
        return False


async def _get_slow_queries(
    connection: DBConnector,
    min_execution_time: float,
    limit: int
) -> List[Dict[str, Any]]:
    """Get slow queries from pg_stat_statements."""
    query = """
        SELECT 
            query,
            calls,
            total_exec_time,
            mean_exec_time,
            max_exec_time,
            min_exec_time,
            stddev_exec_time,
            rows,
            100.0 * shared_blks_hit / nullif(shared_blks_hit + shared_blks_read, 0) AS hit_percent,
            shared_blks_read,
            shared_blks_hit,
            shared_blks_dirtied,
            shared_blks_written,
            local_blks_read,
            local_blks_hit,
            temp_blks_read,
            temp_blks_written
        FROM pg_stat_statements 
        WHERE mean_exec_time >= :min_time
        ORDER BY mean_exec_time DESC
        LIMIT :limit_count
    """
    
    params = [
        {'name': 'min_time', 'value': {'doubleValue': min_execution_time}},
        {'name': 'limit_count', 'value': {'longValue': limit}}
    ]
    
    result = await connection.execute_query(query, params)
    slow_queries = []
    
    for row in result.get('records', []):
        query_info = {
            "query": row[0]['stringValue'],
            "calls": row[1]['longValue'] if not row[1].get('isNull') else 0,
            "total_exec_time_ms": row[2]['doubleValue'] if not row[2].get('isNull') else 0,
            "mean_exec_time_ms": row[3]['doubleValue'] if not row[3].get('isNull') else 0,
            "max_exec_time_ms": row[4]['doubleValue'] if not row[4].get('isNull') else 0,
            "min_exec_time_ms": row[5]['doubleValue'] if not row[5].get('isNull') else 0,
            "stddev_exec_time_ms": row[6]['doubleValue'] if not row[6].get('isNull') else 0,
            "rows_returned": row[7]['longValue'] if not row[7].get('isNull') else 0,
            "cache_hit_percent": row[8]['doubleValue'] if not row[8].get('isNull') else 0,
            "shared_blocks_read": row[9]['longValue'] if not row[9].get('isNull') else 0,
            "shared_blocks_hit": row[10]['longValue'] if not row[10].get('isNull') else 0,
            "shared_blocks_dirtied": row[11]['longValue'] if not row[11].get('isNull') else 0,
            "shared_blocks_written": row[12]['longValue'] if not row[12].get('isNull') else 0,
            "local_blocks_read": row[13]['longValue'] if not row[13].get('isNull') else 0,
            "local_blocks_hit": row[14]['longValue'] if not row[14].get('isNull') else 0,
            "temp_blocks_read": row[15]['longValue'] if not row[15].get('isNull') else 0,
            "temp_blocks_written": row[16]['longValue'] if not row[16].get('isNull') else 0
        }
        
        # Calculate derived metrics
        if query_info["calls"] > 0:
            query_info["avg_rows_per_call"] = query_info["rows_returned"] / query_info["calls"]
        else:
            query_info["avg_rows_per_call"] = 0
        
        # Classify query performance
        if query_info["mean_exec_time_ms"] > 5000:
            query_info["performance_category"] = "Critical"
        elif query_info["mean_exec_time_ms"] > 1000:
            query_info["performance_category"] = "Poor"
        elif query_info["mean_exec_time_ms"] > 500:
            query_info["performance_category"] = "Moderate"
        else:
            query_info["performance_category"] = "Acceptable"
        
        # Identify query type
        query_info["query_type"] = _identify_query_type(query_info["query"])
        
        slow_queries.append(query_info)
    
    return slow_queries


async def _get_current_long_running_queries(
    connection: DBConnector
) -> List[Dict[str, Any]]:
    """Get currently running long queries."""
    query = """
        SELECT 
            pid,
            usename,
            application_name,
            client_addr,
            state,
            query_start,
            state_change,
            EXTRACT(EPOCH FROM (now() - query_start)) * 1000 as duration_ms,
            query
        FROM pg_stat_activity 
        WHERE state = 'active' 
        AND query_start < now() - interval '30 seconds'
        AND query NOT LIKE '%pg_stat_activity%'
        ORDER BY query_start
    """
    
    result = await connection.execute_query(query)
    current_queries = []
    
    for row in result.get('records', []):
        current_queries.append({
            "pid": row[0]['longValue'] if not row[0].get('isNull') else 0,
            "username": row[1]['stringValue'] if not row[1].get('isNull') else 'unknown',
            "application": row[2]['stringValue'] if not row[2].get('isNull') else 'unknown',
            "client_addr": row[3]['stringValue'] if not row[3].get('isNull') else 'local',
            "state": row[4]['stringValue'],
            "query_start": row[5]['stringValue'] if not row[5].get('isNull') else None,
            "state_change": row[6]['stringValue'] if not row[6].get('isNull') else None,
            "duration_ms": row[7]['doubleValue'] if not row[7].get('isNull') else 0,
            "query": row[8]['stringValue'][:200] + "..." if len(row[8]['stringValue']) > 200 else row[8]['stringValue']
        })
    
    return current_queries


def _identify_query_type(query: str) -> str:
    """Identify the type of SQL query."""
    query_lower = query.lower().strip()
    
    if query_lower.startswith('select'):
        if 'join' in query_lower:
            return 'SELECT with JOINs'
        elif 'group by' in query_lower:
            return 'SELECT with GROUP BY'
        elif 'order by' in query_lower:
            return 'SELECT with ORDER BY'
        else:
            return 'SELECT'
    elif query_lower.startswith('insert'):
        return 'INSERT'
    elif query_lower.startswith('update'):
        return 'UPDATE'
    elif query_lower.startswith('delete'):
        return 'DELETE'
    elif query_lower.startswith('with'):
        return 'CTE (Common Table Expression)'
    else:
        return 'Other'


def _analyze_query_patterns(slow_queries: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze patterns in slow queries."""
    patterns = {
        "query_types": {},
        "performance_categories": {},
        "high_io_queries": [],
        "low_cache_hit_queries": [],
        "temp_file_queries": [],
        "summary": {
            "total_slow_queries": len(slow_queries),
            "avg_execution_time": 0,
            "total_calls": 0,
            "total_execution_time": 0
        }
    }
    
    total_exec_time = 0
    total_calls = 0
    
    for query in slow_queries:
        # Count query types
        query_type = query["query_type"]
        patterns["query_types"][query_type] = patterns["query_types"].get(query_type, 0) + 1
        
        # Count performance categories
        perf_cat = query["performance_category"]
        patterns["performance_categories"][perf_cat] = patterns["performance_categories"].get(perf_cat, 0) + 1
        
        # Identify high I/O queries
        total_blocks = (query["shared_blocks_read"] + query["shared_blocks_written"] + 
                       query["temp_blocks_read"] + query["temp_blocks_written"])
        if total_blocks > 10000:
            patterns["high_io_queries"].append({
                "query": query["query"][:100] + "...",
                "total_blocks": total_blocks,
                "mean_exec_time": query["mean_exec_time_ms"]
            })
        
        # Identify low cache hit queries
        if query["cache_hit_percent"] < 90 and query["shared_blocks_read"] > 1000:
            patterns["low_cache_hit_queries"].append({
                "query": query["query"][:100] + "...",
                "cache_hit_percent": query["cache_hit_percent"],
                "blocks_read": query["shared_blocks_read"]
            })
        
        # Identify queries using temp files
        if query["temp_blocks_read"] > 0 or query["temp_blocks_written"] > 0:
            patterns["temp_file_queries"].append({
                "query": query["query"][:100] + "...",
                "temp_blocks_read": query["temp_blocks_read"],
                "temp_blocks_written": query["temp_blocks_written"]
            })
        
        # Update summary
        total_exec_time += query["total_exec_time_ms"]
        total_calls += query["calls"]
    
    patterns["summary"]["total_calls"] = total_calls
    patterns["summary"]["total_execution_time"] = total_exec_time
    if len(slow_queries) > 0:
        patterns["summary"]["avg_execution_time"] = total_exec_time / len(slow_queries)
    
    return patterns


def _generate_slow_query_recommendations(
    slow_queries: List[Dict[str, Any]],
    query_analysis: Dict[str, Any]
) -> List[str]:
    """Generate recommendations based on slow query analysis."""
    recommendations = []
    
    if not slow_queries:
        recommendations.append("No slow queries found above the specified threshold - performance looks good")
        return recommendations
    
    # Critical queries
    critical_queries = [q for q in slow_queries if q["performance_category"] == "Critical"]
    if critical_queries:
        recommendations.append(
            f"CRITICAL: {len(critical_queries)} queries with >5 second average execution time - "
            f"immediate optimization required"
        )
    
    # High I/O queries
    if query_analysis["high_io_queries"]:
        recommendations.append(
            f"HIGH: {len(query_analysis['high_io_queries'])} queries performing excessive I/O - "
            f"consider adding indexes or optimizing query structure"
        )
    
    # Low cache hit queries
    if query_analysis["low_cache_hit_queries"]:
        recommendations.append(
            f"MEDIUM: {len(query_analysis['low_cache_hit_queries'])} queries with low cache hit ratio - "
            f"consider increasing shared_buffers or optimizing data access patterns"
        )
    
    # Temp file usage
    if query_analysis["temp_file_queries"]:
        recommendations.append(
            f"MEDIUM: {len(query_analysis['temp_file_queries'])} queries using temporary files - "
            f"consider increasing work_mem or optimizing sort/hash operations"
        )
    
    # Query type specific recommendations
    query_types = query_analysis["query_types"]
    if query_types.get("SELECT with JOINs", 0) > 5:
        recommendations.append(
            "Consider optimizing JOIN operations - ensure proper indexes on join columns"
        )
    
    if query_types.get("SELECT with GROUP BY", 0) > 3:
        recommendations.append(
            "Multiple slow GROUP BY queries detected - consider indexes on grouping columns"
        )
    
    # General recommendations
    recommendations.append(
        "Review and optimize the top 5 slowest queries for maximum performance impact"
    )
    
    recommendations.append(
        "Monitor pg_stat_statements regularly to track query performance trends"
    )
    
    return recommendations
