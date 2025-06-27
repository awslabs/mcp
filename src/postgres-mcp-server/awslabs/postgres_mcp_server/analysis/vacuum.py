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

"""Vacuum statistics analysis tools."""

import time
from ..connection.base_connection import DBConnector
from loguru import logger
from typing import Any, Dict, List


async def analyze_vacuum_stats(
    connection: DBConnector
) -> Dict[str, Any]:
    """
    Analyze vacuum statistics and provide recommendations for vacuum settings.

    Args:
        connection: Database connection instance

    Returns:
        Dictionary containing vacuum analysis results
    """
    analysis_start = time.time()
    logger.info("Starting vacuum statistics analysis")

    try:
        # Get vacuum statistics for tables
        vacuum_stats = await _get_vacuum_statistics(connection)

        # Get autovacuum settings
        autovacuum_settings = await _get_autovacuum_settings(connection)

        # Analyze vacuum performance
        vacuum_analysis = _analyze_vacuum_performance(vacuum_stats)

        # Generate recommendations
        recommendations = _generate_vacuum_recommendations(
            vacuum_stats, autovacuum_settings, vacuum_analysis
        )

        analysis_time = time.time() - analysis_start

        result = {
            "status": "success",
            "data": {
                "vacuum_statistics": vacuum_stats,
                "autovacuum_settings": autovacuum_settings,
                "vacuum_analysis": vacuum_analysis
            },
            "metadata": {
                "analysis_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "analysis_time_ms": round(analysis_time * 1000, 2),
                "tables_analyzed": len(vacuum_stats)
            },
            "recommendations": recommendations
        }

        logger.success("Vacuum statistics analysis completed successfully")
        return result

    except Exception as e:
        logger.error(f"Vacuum statistics analysis failed: {str(e)}")
        return {
            "status": "error",
            "error": {
                "step": "analyzing_vacuum_statistics",
                "message": str(e),
                "suggestions": [
                    "Ensure database connection is active",
                    "Verify user has necessary permissions to access pg_stat_user_tables",
                    "Check if autovacuum is enabled in PostgreSQL configuration"
                ]
            },
            "partial_data": {}
        }


async def _get_vacuum_statistics(connection: DBConnector) -> List[Dict[str, Any]]:
    """Get vacuum statistics for all user tables."""
    query = """
        SELECT
            schemaname,
            relname as tablename,
            n_tup_ins as inserts,
            n_tup_upd as updates,
            n_tup_del as deletes,
            n_live_tup as live_tuples,
            n_dead_tup as dead_tuples,
            last_vacuum,
            last_autovacuum,
            vacuum_count,
            autovacuum_count,
            last_analyze,
            last_autoanalyze,
            analyze_count,
            autoanalyze_count,
            pg_size_pretty(pg_total_relation_size(schemaname||'.'||relname)) as table_size,
            pg_total_relation_size(schemaname||'.'||relname) as table_bytes
        FROM pg_stat_user_tables
        ORDER BY pg_total_relation_size(schemaname||'.'||relname) DESC
    """

    result = await connection.execute_query(query)
    vacuum_stats = []

    for row in result.get('records', []):
        stats = {
            "schema": row[0]['stringValue'],
            "table": row[1]['stringValue'],
            "inserts": row[2]['longValue'] if not row[2].get('isNull') else 0,
            "updates": row[3]['longValue'] if not row[3].get('isNull') else 0,
            "deletes": row[4]['longValue'] if not row[4].get('isNull') else 0,
            "live_tuples": row[5]['longValue'] if not row[5].get('isNull') else 0,
            "dead_tuples": row[6]['longValue'] if not row[6].get('isNull') else 0,
            "last_vacuum": row[7]['stringValue'] if not row[7].get('isNull') else None,
            "last_autovacuum": row[8]['stringValue'] if not row[8].get('isNull') else None,
            "vacuum_count": row[9]['longValue'] if not row[9].get('isNull') else 0,
            "autovacuum_count": row[10]['longValue'] if not row[10].get('isNull') else 0,
            "last_analyze": row[11]['stringValue'] if not row[11].get('isNull') else None,
            "last_autoanalyze": row[12]['stringValue'] if not row[12].get('isNull') else None,
            "analyze_count": row[13]['longValue'] if not row[13].get('isNull') else 0,
            "autoanalyze_count": row[14]['longValue'] if not row[14].get('isNull') else 0,
            "table_size": row[15]['stringValue'],
            "table_bytes": row[16]['longValue'] if not row[16].get('isNull') else 0
        }

        # Calculate derived metrics
        total_tuples = stats["live_tuples"] + stats["dead_tuples"]
        if total_tuples > 0:
            stats["dead_tuple_percent"] = round(100.0 * stats["dead_tuples"] / total_tuples, 2)
        else:
            stats["dead_tuple_percent"] = 0.0

        stats["total_modifications"] = stats["inserts"] + stats["updates"] + stats["deletes"]
        stats["total_vacuum_operations"] = stats["vacuum_count"] + stats["autovacuum_count"]
        stats["total_analyze_operations"] = stats["analyze_count"] + stats["autoanalyze_count"]

        vacuum_stats.append(stats)

    return vacuum_stats


async def _get_autovacuum_settings(connection: DBConnector) -> Dict[str, Any]:
    """Get autovacuum configuration settings."""
    query = """
        SELECT
            name,
            setting,
            unit,
            short_desc
        FROM pg_settings
        WHERE name LIKE 'autovacuum%' OR name IN (
            'vacuum_cost_delay',
            'vacuum_cost_limit',
            'vacuum_cost_page_hit',
            'vacuum_cost_page_miss',
            'vacuum_cost_page_dirty'
        )
        ORDER BY name
    """

    result = await connection.execute_query(query)
    settings = {}

    for row in result.get('records', []):
        name = row[0]['stringValue']
        setting = row[1]['stringValue']
        unit = row[2]['stringValue'] if not row[2].get('isNull') else None
        description = row[3]['stringValue']

        settings[name] = {
            "value": setting,
            "unit": unit,
            "description": description
        }

    return settings


def _analyze_vacuum_performance(vacuum_stats: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze vacuum performance across all tables."""
    analysis = {
        "tables_needing_vacuum": [],
        "tables_needing_analyze": [],
        "high_churn_tables": [],
        "vacuum_frequency_issues": [],
        "summary": {
            "total_tables": len(vacuum_stats),
            "tables_with_dead_tuples": 0,
            "avg_dead_tuple_percent": 0,
            "tables_never_vacuumed": 0,
            "tables_never_analyzed": 0
        }
    }

    total_dead_percent = 0
    tables_with_dead = 0

    for stats in vacuum_stats:
        schema_table = f"{stats['schema']}.{stats['table']}"

        # Check for tables needing vacuum
        if stats["dead_tuple_percent"] > 20:
            analysis["tables_needing_vacuum"].append({
                "table": schema_table,
                "dead_tuple_percent": stats["dead_tuple_percent"],
                "dead_tuples": stats["dead_tuples"],
                "last_vacuum": stats["last_vacuum"] or stats["last_autovacuum"]
            })

        # Check for tables needing analyze
        if not stats["last_analyze"] and not stats["last_autoanalyze"] and stats["total_modifications"] > 1000:
            analysis["tables_needing_analyze"].append({
                "table": schema_table,
                "modifications": stats["total_modifications"],
                "never_analyzed": True
            })

        # Check for high churn tables
        if stats["total_modifications"] > 100000:
            analysis["high_churn_tables"].append({
                "table": schema_table,
                "modifications": stats["total_modifications"],
                "vacuum_operations": stats["total_vacuum_operations"],
                "modifications_per_vacuum": (
                    stats["total_modifications"] / max(stats["total_vacuum_operations"], 1)
                )
            })

        # Check vacuum frequency
        if (stats["total_modifications"] > 10000 and
            stats["total_vacuum_operations"] == 0):
            analysis["vacuum_frequency_issues"].append({
                "table": schema_table,
                "modifications": stats["total_modifications"],
                "issue": "Never vacuumed despite high modification count"
            })

        # Update summary statistics
        if stats["dead_tuples"] > 0:
            tables_with_dead += 1
            total_dead_percent += stats["dead_tuple_percent"]

        if not stats["last_vacuum"] and not stats["last_autovacuum"]:
            analysis["summary"]["tables_never_vacuumed"] += 1

        if not stats["last_analyze"] and not stats["last_autoanalyze"]:
            analysis["summary"]["tables_never_analyzed"] += 1

    analysis["summary"]["tables_with_dead_tuples"] = tables_with_dead
    if tables_with_dead > 0:
        analysis["summary"]["avg_dead_tuple_percent"] = round(total_dead_percent / tables_with_dead, 2)

    return analysis


def _generate_vacuum_recommendations(
    vacuum_stats: List[Dict[str, Any]],
    autovacuum_settings: Dict[str, Any],
    vacuum_analysis: Dict[str, Any]
) -> List[str]:
    """Generate vacuum optimization recommendations."""
    recommendations = []

    # Check autovacuum enablement
    autovacuum_enabled = autovacuum_settings.get("autovacuum", {}).get("value", "off")
    if autovacuum_enabled.lower() == "off":
        recommendations.append(
            "CRITICAL: Autovacuum is disabled - enable it immediately with 'autovacuum = on'"
        )

    # Tables needing immediate vacuum
    if vacuum_analysis["tables_needing_vacuum"]:
        for table_info in vacuum_analysis["tables_needing_vacuum"][:5]:  # Top 5
            recommendations.append(
                f"HIGH: Table '{table_info['table']}' has {table_info['dead_tuple_percent']}% dead tuples - "
                f"run VACUUM immediately"
            )

    # Tables needing analyze
    if vacuum_analysis["tables_needing_analyze"]:
        for table_info in vacuum_analysis["tables_needing_analyze"][:3]:  # Top 3
            recommendations.append(
                f"MEDIUM: Table '{table_info['table']}' has never been analyzed with "
                f"{table_info['modifications']} modifications - run ANALYZE"
            )

    # High churn tables
    if vacuum_analysis["high_churn_tables"]:
        for table_info in vacuum_analysis["high_churn_tables"][:3]:  # Top 3
            if table_info["modifications_per_vacuum"] > 50000:
                recommendations.append(
                    f"Consider more frequent vacuuming for high-churn table '{table_info['table']}' "
                    f"({table_info['modifications_per_vacuum']:.0f} modifications per vacuum)"
                )

    # Autovacuum tuning recommendations
    vacuum_threshold = autovacuum_settings.get("autovacuum_vacuum_threshold", {}).get("value")
    if vacuum_threshold and int(vacuum_threshold) > 100:
        recommendations.append(
            f"Consider lowering autovacuum_vacuum_threshold from {vacuum_threshold} for smaller tables"
        )

    vacuum_scale_factor = autovacuum_settings.get("autovacuum_vacuum_scale_factor", {}).get("value")
    if vacuum_scale_factor and float(vacuum_scale_factor) > 0.2:
        recommendations.append(
            f"Consider lowering autovacuum_vacuum_scale_factor from {vacuum_scale_factor} "
            f"for more frequent vacuuming"
        )

    # Cost-based vacuum tuning
    vacuum_cost_delay = autovacuum_settings.get("autovacuum_vacuum_cost_delay", {}).get("value")
    if vacuum_cost_delay and int(vacuum_cost_delay) > 20:
        recommendations.append(
            f"High autovacuum_vacuum_cost_delay ({vacuum_cost_delay}ms) may slow vacuum operations - "
            f"consider reducing for faster vacuuming"
        )

    # General recommendations
    if vacuum_analysis["summary"]["tables_never_vacuumed"] > 0:
        recommendations.append(
            f"{vacuum_analysis['summary']['tables_never_vacuumed']} tables have never been vacuumed - "
            f"review autovacuum configuration"
        )

    if not recommendations:
        recommendations.append(
            "Vacuum operations appear to be working well - no immediate action required"
        )
    else:
        recommendations.append(
            "Monitor vacuum operations regularly and adjust autovacuum settings based on workload patterns"
        )

    return recommendations
