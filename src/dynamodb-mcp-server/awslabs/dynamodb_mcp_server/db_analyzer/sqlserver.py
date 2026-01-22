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

"""SQL Server database analyzer plugin."""

import re
from awslabs.dynamodb_mcp_server.db_analyzer.base_plugin import DatabasePlugin
from typing import Any, Dict


_sqlserver_analysis_queries = {
    'comprehensive_table_analysis': {
        'name': 'Comprehensive Table Analysis',
        'description': 'Complete table statistics including structure, size, and I/O',
        'category': 'information_schema',
        'sql': """SELECT
  t.name as table_name,
  MAX(p.rows) as row_count,
  SUM(CASE WHEN idx.index_id < 2 THEN ps.used_page_count ELSE 0 END) * 8 as data_size_kb,
  SUM(CASE WHEN idx.index_id >= 2 THEN ps.used_page_count ELSE 0 END) * 8 as index_size_kb,
  SUM(ps.used_page_count) * 8 as total_size_kb,
  ROUND(SUM(CASE WHEN idx.index_id < 2 THEN ps.used_page_count ELSE 0 END) * 8.0 / 1024, 2) as data_size_mb,
  ROUND(SUM(CASE WHEN idx.index_id >= 2 THEN ps.used_page_count ELSE 0 END) * 8.0 / 1024, 2) as index_size_mb,
  ROUND(SUM(ps.used_page_count) * 8.0 / 1024, 2) as total_size_mb,
  MAX(ISNULL(i.user_seeks, 0)) as index_seeks,
  MAX(ISNULL(i.user_scans, 0)) as table_scans,
  MAX(ISNULL(i.user_lookups, 0)) as index_lookups,
  MAX(ISNULL(i.user_updates, 0)) as updates
FROM sys.tables t
INNER JOIN sys.indexes idx ON t.object_id = idx.object_id
INNER JOIN sys.partitions p ON idx.object_id = p.object_id AND idx.index_id = p.index_id
INNER JOIN sys.dm_db_partition_stats ps ON idx.object_id = ps.object_id AND idx.index_id = ps.index_id
LEFT JOIN sys.dm_db_index_usage_stats i ON idx.object_id = i.object_id AND idx.index_id = i.index_id AND i.database_id = DB_ID()
WHERE t.is_ms_shipped = 0
GROUP BY t.name
ORDER BY MAX(p.rows) DESC;""",
        'parameters': ['target_database'],
    },
    'comprehensive_index_analysis': {
        'name': 'Comprehensive Index Analysis',
        'description': 'Complete index statistics including structure and usage',
        'category': 'information_schema',
        'sql': """SELECT
  OBJECT_NAME(i.object_id) as table_name,
  i.name as index_name,
  i.type_desc as index_type,
  i.is_unique as is_unique,
  ISNULL(s.user_seeks, 0) as seeks,
  ISNULL(s.user_scans, 0) as scans,
  ISNULL(s.user_lookups, 0) as lookups,
  ISNULL(s.user_updates, 0) as updates,
  SUM(ps.used_page_count) * 8 as index_size_kb
FROM sys.indexes i
LEFT JOIN sys.dm_db_index_usage_stats s ON i.object_id = s.object_id AND i.index_id = s.index_id AND s.database_id = DB_ID()
LEFT JOIN sys.dm_db_partition_stats ps ON i.object_id = ps.object_id AND i.index_id = ps.index_id
WHERE OBJECTPROPERTY(i.object_id, 'IsUserTable') = 1
GROUP BY i.object_id, i.name, i.type_desc, i.is_unique, s.user_seeks, s.user_scans, s.user_lookups, s.user_updates
ORDER BY OBJECT_NAME(i.object_id), i.name;""",
        'parameters': ['target_database'],
    },
    'column_analysis': {
        'name': 'Column Information Analysis',
        'description': 'Returns all column definitions including data types, nullability, and defaults',
        'category': 'information_schema',
        'sql': """SELECT
  TABLE_NAME as table_name,
  COLUMN_NAME as column_name,
  ORDINAL_POSITION as position,
  COLUMN_DEFAULT as default_value,
  IS_NULLABLE as nullable,
  DATA_TYPE as data_type,
  CHARACTER_MAXIMUM_LENGTH as char_max_length,
  NUMERIC_PRECISION as numeric_precision,
  NUMERIC_SCALE as numeric_scale
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_CATALOG = '{target_database}'
ORDER BY TABLE_NAME, ORDINAL_POSITION;""",
        'parameters': ['target_database'],
    },
    'foreign_key_analysis': {
        'name': 'Foreign Key Relationship Analysis',
        'description': 'Returns foreign key relationships with constraint names and table/column mappings',
        'category': 'information_schema',
        'sql': """SELECT
  fk.name as constraint_name,
  OBJECT_NAME(fk.parent_object_id) as child_table,
  COL_NAME(fkc.parent_object_id, fkc.parent_column_id) as child_column,
  OBJECT_NAME(fk.referenced_object_id) as parent_table,
  COL_NAME(fkc.referenced_object_id, fkc.referenced_column_id) as parent_column,
  fk.update_referential_action_desc as update_rule,
  fk.delete_referential_action_desc as delete_rule
FROM sys.foreign_keys fk
INNER JOIN sys.foreign_key_columns fkc ON fk.object_id = fkc.constraint_object_id
ORDER BY child_table, child_column;""",
        'parameters': ['target_database'],
    },
    'query_performance_stats': {
        'name': 'Query Performance Statistics',
        'description': 'Unified view of query execution including stored procedures with metrics',
        'category': 'performance_schema',
        'sql': """SELECT
  'QUERY' as source_type,
  SUBSTRING(
    st.text,
    (qs.statement_start_offset/2) + 1,
    ((CASE qs.statement_end_offset
      WHEN -1 THEN DATALENGTH(st.text)
      ELSE qs.statement_end_offset
    END - qs.statement_start_offset)/2) + 1
  ) as query_pattern,
  NULL as procedure_name,
  qs.execution_count as total_executions,
  ROUND(qs.total_elapsed_time / 1000.0 / qs.execution_count, 2) as avg_latency_ms,
  ROUND(qs.min_elapsed_time / 1000.0, 2) as min_latency_ms,
  ROUND(qs.max_elapsed_time / 1000.0, 2) as max_latency_ms,
  ROUND(qs.total_elapsed_time / 1000.0, 2) as total_time_ms,
  ROUND(CAST(qs.total_rows as FLOAT) / qs.execution_count, 2) as avg_rows_returned,
  ROUND(CAST(qs.total_logical_reads as FLOAT) / qs.execution_count, 2) as avg_logical_reads,
  ROUND(CAST(qs.total_physical_reads as FLOAT) / qs.execution_count, 2) as avg_physical_reads,
  ROUND(qs.total_worker_time / 1000.0 / qs.execution_count, 2) as avg_cpu_time_ms,
  qs.creation_time as first_seen,
  qs.last_execution_time as last_seen,
  CASE
    WHEN DATEDIFF(SECOND, qs.creation_time, qs.last_execution_time) > 0
    THEN ROUND(
      CAST(qs.execution_count as FLOAT) /
      DATEDIFF(SECOND, qs.creation_time, qs.last_execution_time),
      2
    )
    ELSE NULL
  END as calculated_rps
FROM sys.dm_exec_query_stats qs
CROSS APPLY sys.dm_exec_sql_text(qs.sql_handle) st
WHERE st.dbid = DB_ID('{target_database}')
  AND qs.execution_count > 0
  -- Filter out system catalog views (FROM sys.xxx pattern)
  AND st.text NOT LIKE '%FROM sys.%' AND st.text NOT LIKE '%JOIN sys.%'
  AND st.text NOT LIKE '%INFORMATION_SCHEMA%'
  -- Filter out DMVs (dm_exec_, dm_db_, dm_os_, dm_tran_ prefixes)
  AND st.text NOT LIKE '%dm[_]exec[_]%' ESCAPE '['
  AND st.text NOT LIKE '%dm[_]db[_]%' ESCAPE '['
  AND st.text NOT LIKE '%dm[_]os[_]%' ESCAPE '['
  AND st.text NOT LIKE '%dm[_]tran[_]%' ESCAPE '['
  -- Filter out system metadata functions
  AND st.text NOT LIKE '%OBJECT[_]NAME(%' ESCAPE '['
  AND st.text NOT LIKE '%OBJECT[_]ID(%' ESCAPE '['
  AND st.text NOT LIKE '%COL[_]NAME(%' ESCAPE '['
  AND st.text NOT LIKE '%OBJECTPROPERTY(%'
  AND st.text NOT LIKE '%DB[_]ID(%' ESCAPE '['
  AND st.text NOT LIKE '%DB[_]NAME(%' ESCAPE '['
  -- Filter out utility/maintenance commands
  AND st.text NOT LIKE 'SET %' AND st.text NOT LIKE 'DBCC %'
  AND st.text NOT LIKE 'BACKUP %' AND st.text NOT LIKE 'RESTORE %'
  AND st.text NOT LIKE 'CHECKPOINT%' AND st.text NOT LIKE 'WAITFOR %'
  AND st.text NOT LIKE 'USE %' AND st.text NOT LIKE 'PRINT %'
  AND st.text NOT LIKE 'RAISERROR%' AND st.text NOT LIKE 'THROW%'
  -- Filter out DDL (focus on DML for access patterns)
  AND st.text NOT LIKE 'CREATE %' AND st.text NOT LIKE 'ALTER %'
  AND st.text NOT LIKE 'DROP %' AND st.text NOT LIKE 'TRUNCATE %'
  AND st.text NOT LIKE 'GRANT %' AND st.text NOT LIKE 'REVOKE %' AND st.text NOT LIKE 'DENY %'
  -- Filter out transaction control
  AND st.text NOT LIKE 'BEGIN TRAN%' AND st.text NOT LIKE 'COMMIT%'
  AND st.text NOT LIKE 'ROLLBACK%' AND st.text NOT LIKE 'SAVE TRAN%'
  -- Filter out system stored procedures (sp_xxx pattern)
  AND st.text NOT LIKE '%sp[_]who%' ESCAPE '['
  AND st.text NOT LIKE '%sp[_]help%' ESCAPE '['
  AND st.text NOT LIKE '%sp[_]executesql%' ESCAPE '['

UNION ALL

SELECT
  'PROCEDURE' as source_type,
  'PROCEDURE: ' + OBJECT_NAME(ps.object_id, ps.database_id) as query_pattern,
  OBJECT_NAME(ps.object_id, ps.database_id) as procedure_name,
  ps.execution_count as total_executions,
  ROUND(ps.total_elapsed_time / 1000.0 / ps.execution_count, 2) as avg_latency_ms,
  ROUND(ps.min_elapsed_time / 1000.0, 2) as min_latency_ms,
  ROUND(ps.max_elapsed_time / 1000.0, 2) as max_latency_ms,
  ROUND(ps.total_elapsed_time / 1000.0, 2) as total_time_ms,
  NULL as avg_rows_returned,
  ROUND(CAST(ps.total_logical_reads as FLOAT) / ps.execution_count, 2) as avg_logical_reads,
  ROUND(CAST(ps.total_physical_reads as FLOAT) / ps.execution_count, 2) as avg_physical_reads,
  ROUND(ps.total_worker_time / 1000.0 / ps.execution_count, 2) as avg_cpu_time_ms,
  ps.cached_time as first_seen,
  ps.last_execution_time as last_seen,
  CASE
    WHEN DATEDIFF(SECOND, ps.cached_time, ps.last_execution_time) > 0
    THEN ROUND(
      CAST(ps.execution_count as FLOAT) /
      DATEDIFF(SECOND, ps.cached_time, ps.last_execution_time),
      2
    )
    ELSE NULL
  END as calculated_rps
FROM sys.dm_exec_procedure_stats ps
WHERE ps.database_id = DB_ID('{target_database}')
  AND ps.execution_count > 0
  AND ps.type IN ('P', 'PC')
  AND OBJECT_NAME(ps.object_id, ps.database_id) IS NOT NULL
ORDER BY total_time_ms DESC;""",
        'parameters': ['target_database'],
    },
}


class SQLServerPlugin(DatabasePlugin):
    """SQL Server-specific database analyzer plugin."""

    def get_queries(self) -> Dict[str, Any]:
        """Get all SQL Server analysis queries."""
        return _sqlserver_analysis_queries

    def get_database_display_name(self) -> str:
        """Get the display name of the database type."""
        return 'SQL Server'

    def apply_result_limit(self, sql: str, max_results: int) -> str:
        """Apply result limit using SQL Server TOP syntax.

        SQL Server uses TOP instead of LIMIT.

        Args:
            sql: SQL query string
            max_results: Maximum number of results

        Returns:
            SQL query with TOP applied
        """
        return re.sub(
            r'\bSELECT\b', f'SELECT TOP {max_results}', sql, count=1, flags=re.IGNORECASE
        )

    # write_queries_to_file is inherited from DatabasePlugin base class

    # parse_results_from_file is inherited from DatabasePlugin base class

    async def execute_managed_mode(self, connection_params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute SQL Server analysis in managed mode.

        Note: Managed mode not yet implemented for SQL Server.
        """
        raise NotImplementedError(
            'Managed mode is not yet implemented for SQL Server. Please use self_service mode.'
        )
