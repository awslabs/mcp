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

"""Table fragmentation analysis tools."""

import time
from ..connection.base_connection import DBConnector
from loguru import logger
from typing import Any, Dict, List


async def analyze_table_fragmentation(
    connection: DBConnector,
    threshold: float = 10.0
) -> Dict[str, Any]:
    """
    Analyze table fragmentation and provide optimization recommendations.

    Args:
        connection: Database connection instance
        threshold: Bloat percentage threshold for recommendations (default: 10.0%)

    Returns:
        Dictionary containing fragmentation analysis results
    """
    analysis_start = time.time()
    logger.info(f"Starting table fragmentation analysis with threshold {threshold}%")

    try:
        # Get table bloat information
        table_bloat = await _get_table_bloat(connection)

        # Get index bloat information
        index_bloat = await _get_index_bloat(connection)

        # Filter tables and indexes above threshold
        problematic_tables = [t for t in table_bloat if t.get("bloat_percent", 0) > threshold]
        problematic_indexes = [i for i in index_bloat if i.get("bloat_percent", 0) > threshold]

        # Generate recommendations
        recommendations = _generate_fragmentation_recommendations(
            problematic_tables, problematic_indexes, threshold
        )

        # Calculate summary statistics
        total_wasted_space = sum(t.get("wasted_bytes", 0) for t in table_bloat)
        total_wasted_space += sum(i.get("wasted_bytes", 0) for i in index_bloat)

        analysis_time = time.time() - analysis_start

        result = {
            "status": "success",
            "data": {
                "table_bloat": table_bloat,
                "index_bloat": index_bloat,
                "problematic_tables": problematic_tables,
                "problematic_indexes": problematic_indexes,
                "threshold_percent": threshold
            },
            "metadata": {
                "analysis_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "analysis_time_ms": round(analysis_time * 1000, 2),
                "total_tables_analyzed": len(table_bloat),
                "total_indexes_analyzed": len(index_bloat),
                "tables_above_threshold": len(problematic_tables),
                "indexes_above_threshold": len(problematic_indexes),
                "total_wasted_space_bytes": total_wasted_space
            },
            "recommendations": recommendations
        }

        logger.success("Table fragmentation analysis completed successfully")
        return result

    except Exception as e:
        logger.error(f"Table fragmentation analysis failed: {str(e)}")
        return {
            "status": "error",
            "error": {
                "step": "analyzing_table_fragmentation",
                "message": str(e),
                "suggestions": [
                    "Ensure database connection is active",
                    "Verify user has necessary permissions to access system catalogs",
                    "Check if pgstattuple extension is available for detailed bloat analysis"
                ]
            },
            "partial_data": {"threshold_percent": threshold}
        }


async def _get_table_bloat(connection: DBConnector) -> List[Dict[str, Any]]:
    """Get table bloat information using system statistics."""
    query = """
        SELECT
            schemaname,
            tablename,
            pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as total_size,
            pg_total_relation_size(schemaname||'.'||tablename) as total_bytes,
            pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) as table_size,
            pg_relation_size(schemaname||'.'||tablename) as table_bytes,
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
            last_autovacuum,
            last_analyze,
            last_autoanalyze
        FROM pg_stat_user_tables
        ORDER BY
            CASE
                WHEN n_live_tup > 0
                THEN 100.0 * n_dead_tup / (n_live_tup + n_dead_tup)
                ELSE 0
            END DESC
    """

    result = await connection.execute_query(query)
    table_bloat = []

    for row in result.get('records', []):
        bloat_info = {
            "schema": row[0]['stringValue'],
            "table": row[1]['stringValue'],
            "total_size": row[2]['stringValue'],
            "total_bytes": row[3]['longValue'] if not row[3].get('isNull') else 0,
            "table_size": row[4]['stringValue'],
            "table_bytes": row[5]['longValue'] if not row[5].get('isNull') else 0,
            "inserts": row[6]['longValue'] if not row[6].get('isNull') else 0,
            "updates": row[7]['longValue'] if not row[7].get('isNull') else 0,
            "deletes": row[8]['longValue'] if not row[8].get('isNull') else 0,
            "live_tuples": row[9]['longValue'] if not row[9].get('isNull') else 0,
            "dead_tuples": row[10]['longValue'] if not row[10].get('isNull') else 0,
            "bloat_percent": row[11]['doubleValue'] if not row[11].get('isNull') else 0,
            "last_vacuum": row[12]['stringValue'] if not row[12].get('isNull') else None,
            "last_autovacuum": row[13]['stringValue'] if not row[13].get('isNull') else None,
            "last_analyze": row[14]['stringValue'] if not row[14].get('isNull') else None,
            "last_autoanalyze": row[15]['stringValue'] if not row[15].get('isNull') else None
        }

        # Calculate estimated wasted space
        if bloat_info["bloat_percent"] > 0:
            bloat_info["wasted_bytes"] = int(bloat_info["table_bytes"] * bloat_info["bloat_percent"] / 100)
            bloat_info["wasted_size"] = _format_bytes(bloat_info["wasted_bytes"])
        else:
            bloat_info["wasted_bytes"] = 0
            bloat_info["wasted_size"] = "0 bytes"

        table_bloat.append(bloat_info)

    return table_bloat


async def _get_index_bloat(connection: DBConnector) -> List[Dict[str, Any]]:
    """Get index bloat information."""
    query = """
        SELECT
            schemaname,
            tablename,
            indexname,
            pg_size_pretty(pg_relation_size(indexrelid)) as index_size,
            pg_relation_size(indexrelid) as index_bytes,
            idx_scan as scans,
            idx_tup_read as tuples_read,
            idx_tup_fetch as tuples_fetched
        FROM pg_stat_user_indexes
        ORDER BY pg_relation_size(indexrelid) DESC
    """

    result = await connection.execute_query(query)
    index_bloat = []

    for row in result.get('records', []):
        index_info = {
            "schema": row[0]['stringValue'],
            "table": row[1]['stringValue'],
            "index": row[2]['stringValue'],
            "size": row[3]['stringValue'],
            "size_bytes": row[4]['longValue'] if not row[4].get('isNull') else 0,
            "scans": row[5]['longValue'] if not row[5].get('isNull') else 0,
            "tuples_read": row[6]['longValue'] if not row[6].get('isNull') else 0,
            "tuples_fetched": row[7]['longValue'] if not row[7].get('isNull') else 0
        }

        # Estimate bloat based on usage patterns
        # This is a simplified estimation - real bloat analysis would require pgstattuple
        if index_info["scans"] == 0 and index_info["size_bytes"] > 1024 * 1024:  # 1MB
            index_info["bloat_percent"] = 50.0  # Unused large index
            index_info["bloat_reason"] = "Unused index"
        elif index_info["tuples_read"] > 0 and index_info["tuples_fetched"] == 0:
            index_info["bloat_percent"] = 25.0  # Index scanned but no tuples fetched
            index_info["bloat_reason"] = "Low efficiency index"
        else:
            index_info["bloat_percent"] = 0.0
            index_info["bloat_reason"] = "Normal"

        # Calculate wasted space
        if index_info["bloat_percent"] > 0:
            index_info["wasted_bytes"] = int(index_info["size_bytes"] * index_info["bloat_percent"] / 100)
            index_info["wasted_size"] = _format_bytes(index_info["wasted_bytes"])
        else:
            index_info["wasted_bytes"] = 0
            index_info["wasted_size"] = "0 bytes"

        index_bloat.append(index_info)

    return index_bloat


def _format_bytes(bytes_value: int) -> str:
    """Format bytes into human-readable string."""
    if bytes_value < 1024:
        return f"{bytes_value} bytes"
    elif bytes_value < 1024 * 1024:
        return f"{bytes_value / 1024:.1f} KB"
    elif bytes_value < 1024 * 1024 * 1024:
        return f"{bytes_value / (1024 * 1024):.1f} MB"
    else:
        return f"{bytes_value / (1024 * 1024 * 1024):.1f} GB"


def _generate_fragmentation_recommendations(
    problematic_tables: List[Dict[str, Any]],
    problematic_indexes: List[Dict[str, Any]],
    threshold: float
) -> List[str]:
    """Generate recommendations based on fragmentation analysis."""
    recommendations = []

    # Table recommendations
    for table in problematic_tables:
        schema_table = f"{table['schema']}.{table['table']}"
        bloat_percent = table['bloat_percent']

        if bloat_percent > 50:
            recommendations.append(
                f"CRITICAL: Table '{schema_table}' has {bloat_percent:.1f}% bloat "
                f"({table['wasted_size']} wasted) - Consider VACUUM FULL or pg_repack"
            )
        elif bloat_percent > 25:
            recommendations.append(
                f"HIGH: Table '{schema_table}' has {bloat_percent:.1f}% bloat "
                f"({table['wasted_size']} wasted) - Run VACUUM or increase autovacuum frequency"
            )
        else:
            recommendations.append(
                f"MEDIUM: Table '{schema_table}' has {bloat_percent:.1f}% bloat "
                f"({table['wasted_size']} wasted) - Monitor and consider VACUUM"
            )

        # Check vacuum history
        if not table['last_vacuum'] and not table['last_autovacuum']:
            recommendations.append(
                f"Table '{schema_table}' has never been vacuumed - immediate VACUUM recommended"
            )

    # Index recommendations
    for index in problematic_indexes:
        schema_table = f"{index['schema']}.{index['table']}"
        index_name = index['index']

        if index['bloat_reason'] == "Unused index":
            recommendations.append(
                f"Consider dropping unused index '{index_name}' on table '{schema_table}' "
                f"(saves {index['size']})"
            )
        elif index['bloat_reason'] == "Low efficiency index":
            recommendations.append(
                f"Index '{index_name}' on table '{schema_table}' has low efficiency - "
                f"consider REINDEX or review index design"
            )

    # General recommendations
    if not recommendations:
        recommendations.append(
            f"All tables and indexes are below the {threshold}% bloat threshold - "
            f"fragmentation levels are acceptable"
        )
    else:
        recommendations.append(
            "Consider scheduling regular VACUUM operations to prevent future bloat buildup"
        )
        recommendations.append(
            "Review autovacuum settings to ensure they match your workload patterns"
        )

    return recommendations
