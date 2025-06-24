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

"""PostgreSQL settings analysis tools."""

import time
from typing import Dict, List, Any, Optional
from loguru import logger
from ..connection.base_connection import DBConnector


async def show_postgresql_settings(
    connection: DBConnector,
    pattern: Optional[str] = None
) -> Dict[str, Any]:
    """
    Show PostgreSQL configuration settings with optional filtering.
    
    Args:
        connection: Database connection instance
        pattern: Optional pattern to filter settings (SQL LIKE pattern)
        
    Returns:
        Dictionary containing PostgreSQL settings analysis
    """
    analysis_start = time.time()
    logger.info(f"Starting PostgreSQL settings analysis with pattern: {pattern}")
    
    try:
        # Get PostgreSQL settings
        settings = await _get_postgresql_settings(connection, pattern)
        
        # Categorize settings
        categorized_settings = _categorize_settings(settings)
        
        # Analyze settings for potential issues
        analysis = _analyze_settings(settings)
        
        # Generate recommendations
        recommendations = _generate_settings_recommendations(analysis, settings)
        
        analysis_time = time.time() - analysis_start
        
        result = {
            "status": "success",
            "data": {
                "settings": settings,
                "categorized_settings": categorized_settings,
                "analysis": analysis,
                "filter_pattern": pattern
            },
            "metadata": {
                "analysis_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "analysis_time_ms": round(analysis_time * 1000, 2),
                "total_settings": len(settings),
                "filtered_settings": len(settings) if pattern else "all"
            },
            "recommendations": recommendations
        }
        
        logger.success("PostgreSQL settings analysis completed successfully")
        return result
        
    except Exception as e:
        logger.error(f"PostgreSQL settings analysis failed: {str(e)}")
        return {
            "status": "error",
            "error": {
                "step": "analyzing_postgresql_settings",
                "message": str(e),
                "suggestions": [
                    "Ensure database connection is active",
                    "Verify user has necessary permissions to access pg_settings",
                    "Check if the pattern syntax is correct (SQL LIKE pattern)"
                ]
            },
            "partial_data": {"filter_pattern": pattern}
        }


async def _get_postgresql_settings(
    connection: DBConnector,
    pattern: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Get PostgreSQL configuration settings."""
    base_query = """
        SELECT 
            name,
            setting,
            unit,
            category,
            short_desc,
            extra_desc,
            context,
            vartype,
            source,
            min_val,
            max_val,
            enumvals,
            boot_val,
            reset_val,
            pending_restart
        FROM pg_settings
    """
    
    if pattern:
        query = base_query + " WHERE name ILIKE :pattern ORDER BY category, name"
        params = [{'name': 'pattern', 'value': {'stringValue': f"%{pattern}%"}}]
    else:
        query = base_query + " ORDER BY category, name"
        params = None
    
    result = await connection.execute_query(query, params)
    settings = []
    
    for row in result.get('records', []):
        setting_info = {
            "name": row[0]['stringValue'],
            "setting": row[1]['stringValue'],
            "unit": row[2]['stringValue'] if not row[2].get('isNull') else None,
            "category": row[3]['stringValue'],
            "short_desc": row[4]['stringValue'],
            "extra_desc": row[5]['stringValue'] if not row[5].get('isNull') else None,
            "context": row[6]['stringValue'],
            "vartype": row[7]['stringValue'],
            "source": row[8]['stringValue'],
            "min_val": row[9]['stringValue'] if not row[9].get('isNull') else None,
            "max_val": row[10]['stringValue'] if not row[10].get('isNull') else None,
            "enumvals": row[11]['stringValue'] if not row[11].get('isNull') else None,
            "boot_val": row[12]['stringValue'] if not row[12].get('isNull') else None,
            "reset_val": row[13]['stringValue'] if not row[13].get('isNull') else None,
            "pending_restart": row[14]['booleanValue'] if not row[14].get('isNull') else False
        }
        
        # Add formatted value with unit
        if setting_info["unit"]:
            setting_info["formatted_value"] = f"{setting_info['setting']} {setting_info['unit']}"
        else:
            setting_info["formatted_value"] = setting_info["setting"]
        
        # Check if setting is at default value
        setting_info["is_default"] = setting_info["setting"] == setting_info["boot_val"]
        
        # Check if setting has been modified
        setting_info["is_modified"] = setting_info["setting"] != setting_info["reset_val"]
        
        settings.append(setting_info)
    
    return settings


def _categorize_settings(settings: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Categorize settings by their category."""
    categorized = {}
    
    for setting in settings:
        category = setting["category"]
        if category not in categorized:
            categorized[category] = []
        categorized[category].append(setting)
    
    return categorized


def _analyze_settings(settings: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze settings for potential issues and optimizations."""
    analysis = {
        "memory_settings": {},
        "performance_settings": {},
        "connection_settings": {},
        "logging_settings": {},
        "autovacuum_settings": {},
        "checkpoint_settings": {},
        "potential_issues": [],
        "custom_settings": [],
        "pending_restart_settings": []
    }
    
    # Key settings to analyze
    memory_settings = [
        'shared_buffers', 'work_mem', 'maintenance_work_mem', 
        'effective_cache_size', 'temp_buffers'
    ]
    
    performance_settings = [
        'max_connections', 'random_page_cost', 'seq_page_cost',
        'cpu_tuple_cost', 'cpu_index_tuple_cost', 'cpu_operator_cost'
    ]
    
    connection_settings = [
        'max_connections', 'superuser_reserved_connections',
        'listen_addresses', 'port'
    ]
    
    logging_settings = [
        'log_statement', 'log_min_duration_statement', 'log_checkpoints',
        'log_connections', 'log_disconnections', 'log_lock_waits'
    ]
    
    autovacuum_settings = [
        'autovacuum', 'autovacuum_max_workers', 'autovacuum_naptime',
        'autovacuum_vacuum_threshold', 'autovacuum_vacuum_scale_factor'
    ]
    
    checkpoint_settings = [
        'checkpoint_timeout', 'checkpoint_completion_target',
        'max_wal_size', 'min_wal_size'
    ]
    
    for setting in settings:
        name = setting["name"]
        value = setting["setting"]
        
        # Categorize important settings
        if name in memory_settings:
            analysis["memory_settings"][name] = setting
        elif name in performance_settings:
            analysis["performance_settings"][name] = setting
        elif name in connection_settings:
            analysis["connection_settings"][name] = setting
        elif name in logging_settings:
            analysis["logging_settings"][name] = setting
        elif name in autovacuum_settings:
            analysis["autovacuum_settings"][name] = setting
        elif name in checkpoint_settings:
            analysis["checkpoint_settings"][name] = setting
        
        # Check for potential issues
        if name == "shared_buffers" and setting["unit"] == "8kB":
            shared_buffers_mb = int(value) * 8 / 1024
            if shared_buffers_mb < 128:
                analysis["potential_issues"].append({
                    "setting": name,
                    "issue": f"shared_buffers is very low ({shared_buffers_mb:.0f}MB)",
                    "recommendation": "Consider increasing to 25% of available RAM"
                })
        
        elif name == "work_mem" and setting["unit"] == "kB":
            work_mem_mb = int(value) / 1024
            if work_mem_mb < 4:
                analysis["potential_issues"].append({
                    "setting": name,
                    "issue": f"work_mem is very low ({work_mem_mb:.1f}MB)",
                    "recommendation": "Consider increasing for better sort/hash performance"
                })
        
        elif name == "max_connections":
            if int(value) > 200:
                analysis["potential_issues"].append({
                    "setting": name,
                    "issue": f"max_connections is high ({value})",
                    "recommendation": "Consider using connection pooling"
                })
        
        elif name == "autovacuum" and value == "off":
            analysis["potential_issues"].append({
                "setting": name,
                "issue": "autovacuum is disabled",
                "recommendation": "Enable autovacuum to prevent table bloat"
            })
        
        # Track custom (non-default) settings
        if not setting["is_default"] and setting["source"] not in ["default", "override"]:
            analysis["custom_settings"].append(setting)
        
        # Track settings pending restart
        if setting["pending_restart"]:
            analysis["pending_restart_settings"].append(setting)
    
    return analysis


def _generate_settings_recommendations(
    analysis: Dict[str, Any],
    settings: List[Dict[str, Any]]
) -> List[str]:
    """Generate recommendations based on settings analysis."""
    recommendations = []
    
    # Memory recommendations
    memory_settings = analysis["memory_settings"]
    if "shared_buffers" in memory_settings:
        shared_buffers = memory_settings["shared_buffers"]
        if shared_buffers["unit"] == "8kB":
            shared_buffers_mb = int(shared_buffers["setting"]) * 8 / 1024
            if shared_buffers_mb < 128:
                recommendations.append(
                    f"Increase shared_buffers from {shared_buffers_mb:.0f}MB to 25% of available RAM"
                )
    
    # Performance recommendations
    if "max_connections" in analysis["connection_settings"]:
        max_conn = int(analysis["connection_settings"]["max_connections"]["setting"])
        if max_conn > 200:
            recommendations.append(
                f"Consider reducing max_connections from {max_conn} and using connection pooling"
            )
    
    # Autovacuum recommendations
    autovacuum_settings = analysis["autovacuum_settings"]
    if "autovacuum" in autovacuum_settings:
        if autovacuum_settings["autovacuum"]["setting"] == "off":
            recommendations.append("Enable autovacuum to prevent table bloat and maintain performance")
    
    # Logging recommendations
    logging_settings = analysis["logging_settings"]
    if "log_min_duration_statement" in logging_settings:
        log_duration = logging_settings["log_min_duration_statement"]["setting"]
        if log_duration == "-1":
            recommendations.append(
                "Consider enabling slow query logging by setting log_min_duration_statement"
            )
    
    # Checkpoint recommendations
    checkpoint_settings = analysis["checkpoint_settings"]
    if "checkpoint_completion_target" in checkpoint_settings:
        checkpoint_target = float(checkpoint_settings["checkpoint_completion_target"]["setting"])
        if checkpoint_target < 0.7:
            recommendations.append(
                f"Consider increasing checkpoint_completion_target from {checkpoint_target} to 0.9"
            )
    
    # Pending restart warnings
    if analysis["pending_restart_settings"]:
        pending_names = [s["name"] for s in analysis["pending_restart_settings"]]
        recommendations.append(
            f"Settings requiring restart: {', '.join(pending_names)} - restart PostgreSQL to apply"
        )
    
    # Potential issues
    for issue in analysis["potential_issues"]:
        recommendations.append(f"{issue['issue']} - {issue['recommendation']}")
    
    # General recommendations
    if len(analysis["custom_settings"]) > 20:
        recommendations.append(
            f"Many custom settings detected ({len(analysis['custom_settings'])}) - "
            f"review configuration for consistency"
        )
    
    if not recommendations:
        recommendations.append("PostgreSQL configuration appears to be well-tuned")
    
    return recommendations
