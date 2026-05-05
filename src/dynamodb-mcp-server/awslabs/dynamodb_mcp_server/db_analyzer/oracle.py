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

"""Oracle database analyzer plugin."""

from awslabs.dynamodb_mcp_server.common import validate_source_identifier
from awslabs.dynamodb_mcp_server.db_analyzer.base_plugin import DatabasePlugin
from datetime import datetime
from loguru import logger
from typing import Any, Dict


COMPREHENSIVE_TABLE_ANALYSIS = 'comprehensive_table_analysis'
COMPREHENSIVE_INDEX_ANALYSIS = 'comprehensive_index_analysis'
COLUMN_ANALYSIS = 'column_analysis'
CONSTRAINT_ANALYSIS = 'constraint_analysis'
FOREIGN_KEY_ANALYSIS = 'foreign_key_analysis'
QUERY_PERFORMANCE_STATS_AWR = 'query_performance_stats'
QUERY_PERFORMANCE_STATS_VSQL = 'query_performance_stats_vsql'


_oracle_analysis_queries = {
    COMPREHENSIVE_TABLE_ANALYSIS: {
        'name': 'Comprehensive Table Analysis',
        'description': 'Complete table statistics including structure, size, and I/O',
        'category': 'information_schema',
        'sql': """SELECT
  t.TABLE_NAME as table_name,
  t.NUM_ROWS as row_count,
  t.AVG_ROW_LEN as avg_row_length_bytes,
  NVL(s.data_size_bytes, 0) as data_size_bytes,
  NVL(ix.index_size_bytes, 0) as index_size_bytes,
  ROUND(NVL(s.data_size_bytes, 0)/1024/1024, 2) as data_size_mb,
  ROUND(NVL(ix.index_size_bytes, 0)/1024/1024, 2) as index_size_mb,
  ROUND((NVL(s.data_size_bytes, 0) + NVL(ix.index_size_bytes, 0))/1024/1024, 2) as total_size_mb,
  (SELECT COUNT(*) FROM DBA_TAB_COLUMNS c
   WHERE c.OWNER = t.OWNER AND c.TABLE_NAME = t.TABLE_NAME) as column_count,
  (SELECT COUNT(*) FROM DBA_CONSTRAINTS ac
   WHERE ac.OWNER = t.OWNER AND ac.TABLE_NAME = t.TABLE_NAME
   AND ac.CONSTRAINT_TYPE = 'R') as fk_count,
  NVL(m.INSERTS, 0) as inserts,
  NVL(m.UPDATES, 0) as updates,
  NVL(m.DELETES, 0) as deletes,
  t.LAST_ANALYZED as last_analyzed
FROM DBA_TABLES t
LEFT JOIN (
  SELECT SEGMENT_NAME, OWNER, SUM(BYTES) as data_size_bytes
  FROM DBA_SEGMENTS
  WHERE SEGMENT_TYPE IN ('TABLE', 'TABLE PARTITION', 'TABLE SUBPARTITION')
  GROUP BY SEGMENT_NAME, OWNER
) s ON s.SEGMENT_NAME = t.TABLE_NAME AND s.OWNER = t.OWNER
LEFT JOIN (
  SELECT ai.TABLE_OWNER, ai.TABLE_NAME, SUM(seg.total_bytes) as index_size_bytes
  FROM DBA_INDEXES ai
  JOIN (
    SELECT SEGMENT_NAME, OWNER, SUM(BYTES) as total_bytes
    FROM DBA_SEGMENTS
    WHERE SEGMENT_TYPE IN ('INDEX', 'INDEX PARTITION', 'INDEX SUBPARTITION')
    GROUP BY SEGMENT_NAME, OWNER
  ) seg ON seg.SEGMENT_NAME = ai.INDEX_NAME AND seg.OWNER = ai.OWNER
  GROUP BY ai.TABLE_OWNER, ai.TABLE_NAME
) ix ON ix.TABLE_OWNER = t.OWNER AND ix.TABLE_NAME = t.TABLE_NAME
LEFT JOIN DBA_TAB_MODIFICATIONS m ON m.TABLE_OWNER = t.OWNER AND m.TABLE_NAME = t.TABLE_NAME
WHERE t.OWNER = UPPER('{target_owner}')
  AND t.TABLE_NAME NOT LIKE 'BIN$%'
ORDER BY t.NUM_ROWS DESC NULLS LAST""",
        'parameters': ['target_owner'],
    },
    COMPREHENSIVE_INDEX_ANALYSIS: {
        'name': 'Comprehensive Index Analysis',
        'description': 'Complete index statistics including structure and usage',
        'category': 'information_schema',
        'sql': """SELECT
  ai.TABLE_NAME as table_name,
  ai.INDEX_NAME as index_name,
  aic.COLUMN_NAME as column_name,
  aic.COLUMN_POSITION as column_position,
  ai.UNIQUENESS as uniqueness,
  ai.INDEX_TYPE as index_type,
  ai.NUM_ROWS as num_rows,
  ai.DISTINCT_KEYS as distinct_keys,
  ai.LEAF_BLOCKS as leaf_blocks,
  ai.CLUSTERING_FACTOR as clustering_factor,
  ai.STATUS as status,
  ai.LAST_ANALYZED as last_analyzed,
  seg.index_size_bytes as index_size_bytes
FROM DBA_INDEXES ai
JOIN DBA_IND_COLUMNS aic ON ai.INDEX_NAME = aic.INDEX_NAME AND ai.OWNER = aic.INDEX_OWNER
LEFT JOIN (
  SELECT SEGMENT_NAME, OWNER, SUM(BYTES) as index_size_bytes
  FROM DBA_SEGMENTS
  WHERE SEGMENT_TYPE IN ('INDEX', 'INDEX PARTITION', 'INDEX SUBPARTITION')
  GROUP BY SEGMENT_NAME, OWNER
) seg ON seg.SEGMENT_NAME = ai.INDEX_NAME AND seg.OWNER = ai.OWNER
WHERE ai.OWNER = UPPER('{target_owner}')
  AND ai.TABLE_NAME NOT LIKE 'BIN$%'
ORDER BY ai.TABLE_NAME, ai.INDEX_NAME, aic.COLUMN_POSITION""",
        'parameters': ['target_owner'],
    },
    COLUMN_ANALYSIS: {
        'name': 'Column Information Analysis',
        'description': 'Returns all column definitions including data types, nullability, and defaults',
        'category': 'information_schema',
        'sql': """SELECT
  c.TABLE_NAME as table_name,
  c.COLUMN_NAME as column_name,
  c.COLUMN_ID as position,
  c.DATA_DEFAULT as default_value,
  c.NULLABLE as nullable,
  c.DATA_TYPE as data_type,
  c.DATA_LENGTH as data_length,
  c.DATA_PRECISION as numeric_precision,
  c.DATA_SCALE as numeric_scale,
  c.CHAR_LENGTH as char_max_length,
  c.DATA_TYPE || CASE
    WHEN c.DATA_PRECISION IS NOT NULL THEN '(' || c.DATA_PRECISION || ',' || c.DATA_SCALE || ')'
    WHEN c.CHAR_LENGTH > 0 THEN '(' || c.CHAR_LENGTH || ')'
    ELSE ''
  END as column_type,
  cs.NUM_DISTINCT as num_distinct,
  cs.AVG_COL_LEN as avg_col_len,
  cs.HISTOGRAM as histogram_type,
  cs.NUM_BUCKETS as num_buckets
FROM DBA_TAB_COLUMNS c
LEFT JOIN DBA_TAB_COL_STATISTICS cs
  ON cs.OWNER = c.OWNER AND cs.TABLE_NAME = c.TABLE_NAME AND cs.COLUMN_NAME = c.COLUMN_NAME
WHERE c.OWNER = UPPER('{target_owner}')
  AND c.TABLE_NAME NOT LIKE 'BIN$%'
ORDER BY c.TABLE_NAME, c.COLUMN_ID""",
        'parameters': ['target_owner'],
    },
    FOREIGN_KEY_ANALYSIS: {
        'name': 'Foreign Key Relationship Analysis',
        'description': 'Returns foreign key relationships with constraint names and table/column mappings',
        'category': 'information_schema',
        'sql': """SELECT
  c.CONSTRAINT_NAME as constraint_name,
  c.TABLE_NAME as child_table,
  cc.COLUMN_NAME as child_column,
  r.TABLE_NAME as parent_table,
  rc.COLUMN_NAME as parent_column,
  c.DELETE_RULE as delete_rule
FROM DBA_CONSTRAINTS c
JOIN DBA_CONS_COLUMNS cc ON c.CONSTRAINT_NAME = cc.CONSTRAINT_NAME AND c.OWNER = cc.OWNER
JOIN DBA_CONSTRAINTS r ON c.R_CONSTRAINT_NAME = r.CONSTRAINT_NAME AND c.R_OWNER = r.OWNER
JOIN DBA_CONS_COLUMNS rc ON r.CONSTRAINT_NAME = rc.CONSTRAINT_NAME AND r.OWNER = rc.OWNER
  AND cc.POSITION = rc.POSITION
WHERE c.CONSTRAINT_TYPE = 'R'
  AND c.OWNER = UPPER('{target_owner}')
  AND c.TABLE_NAME NOT LIKE 'BIN$%'
ORDER BY c.TABLE_NAME, cc.COLUMN_NAME""",
        'parameters': ['target_owner'],
    },
    CONSTRAINT_ANALYSIS: {
        'name': 'Primary Key and Unique Constraint Analysis',
        'description': 'Returns primary key and unique constraints with column mappings for entity identification and partition key selection',
        'category': 'information_schema',
        'sql': """SELECT
  c.TABLE_NAME as table_name,
  c.CONSTRAINT_NAME as constraint_name,
  c.CONSTRAINT_TYPE as constraint_type,
  cc.COLUMN_NAME as column_name,
  cc.POSITION as column_position
FROM DBA_CONSTRAINTS c
JOIN DBA_CONS_COLUMNS cc ON c.CONSTRAINT_NAME = cc.CONSTRAINT_NAME AND c.OWNER = cc.OWNER
WHERE c.CONSTRAINT_TYPE IN ('P', 'U')
  AND c.OWNER = UPPER('{target_owner}')
  AND c.TABLE_NAME NOT LIKE 'BIN$%'
ORDER BY c.TABLE_NAME, c.CONSTRAINT_TYPE, c.CONSTRAINT_NAME, cc.POSITION""",
        'parameters': ['target_owner'],
    },
    QUERY_PERFORMANCE_STATS_AWR: {
        'name': 'Query Performance Statistics',
        'description': 'Historical SQL performance from AWR (DBA_HIST_SQLSTAT). Requires Enterprise Edition + Diagnostics Pack. Falls back to query_performance_stats_vsql on Standard/XE',
        'category': 'performance_schema',
        'sql': """SELECT
  ss.sql_id,
  CAST(DBMS_LOB.SUBSTR(st.sql_text, 200, 1) AS VARCHAR2(200)) as query_pattern,
  SUM(ss.executions_delta) as total_executions,
  ROUND(SUM(ss.elapsed_time_delta) / NULLIF(SUM(ss.executions_delta), 0) / 1000, 2) as avg_latency_ms,
  ROUND(SUM(ss.elapsed_time_delta) / 1000, 2) as total_time_ms,
  ROUND(SUM(ss.rows_processed_delta) / NULLIF(SUM(ss.executions_delta), 0), 2) as avg_rows_returned,
  ROUND(SUM(ss.buffer_gets_delta) / NULLIF(SUM(ss.executions_delta), 0), 2) as avg_buffer_gets,
  ROUND(SUM(ss.disk_reads_delta) / NULLIF(SUM(ss.executions_delta), 0), 2) as avg_disk_reads,
  ROUND(SUM(ss.cpu_time_delta) / NULLIF(SUM(ss.executions_delta), 0) / 1000, 2) as avg_cpu_time_ms,
  MIN(sn.begin_interval_time) as first_seen,
  MAX(sn.end_interval_time) as last_seen,
  ss.parsing_schema_name as schema_name,
  CASE
    WHEN (MAX(sn.end_interval_time) - MIN(sn.begin_interval_time)) > INTERVAL '0' SECOND
    THEN ROUND(SUM(ss.executions_delta) /
      (EXTRACT(DAY FROM (MAX(sn.end_interval_time) - MIN(sn.begin_interval_time))) * 86400 +
       EXTRACT(HOUR FROM (MAX(sn.end_interval_time) - MIN(sn.begin_interval_time))) * 3600 +
       EXTRACT(MINUTE FROM (MAX(sn.end_interval_time) - MIN(sn.begin_interval_time))) * 60 +
       EXTRACT(SECOND FROM (MAX(sn.end_interval_time) - MIN(sn.begin_interval_time)))), 6)
    ELSE NULL
  END as calculated_rps
FROM DBA_HIST_SQLSTAT ss
JOIN DBA_HIST_SQLTEXT st ON ss.sql_id = st.sql_id AND ss.dbid = st.dbid
JOIN DBA_HIST_SNAPSHOT sn ON ss.snap_id = sn.snap_id AND ss.dbid = sn.dbid AND ss.instance_number = sn.instance_number
WHERE ss.parsing_schema_name = UPPER('{target_owner}')
  AND ss.executions_delta > 0
  AND sn.begin_interval_time >= SYSTIMESTAMP - INTERVAL '30' DAY
  AND st.command_type IN (2, 3, 6, 7)
  AND st.sql_text NOT LIKE '%SYS.%'
GROUP BY ss.sql_id, CAST(DBMS_LOB.SUBSTR(st.sql_text, 200, 1) AS VARCHAR2(200)), ss.parsing_schema_name
ORDER BY SUM(ss.elapsed_time_delta) DESC""",
        'parameters': ['target_owner'],
    },
    QUERY_PERFORMANCE_STATS_VSQL: {
        'name': 'Query Performance Statistics (V$SQL Fallback)',
        'description': 'Real-time SQL performance from V$SQL cursor cache. Used when AWR (DBA_HIST) is unavailable (Standard Edition, XE, or no Diagnostics Pack license)',
        'category': 'performance_schema',
        'sql': """SELECT
  sq.sql_id,
  CAST(DBMS_LOB.SUBSTR(sq.sql_fulltext, 200, 1) AS VARCHAR2(200)) as query_pattern,
  sq.executions as total_executions,
  ROUND(sq.elapsed_time / NULLIF(sq.executions, 0) / 1000, 2) as avg_latency_ms,
  ROUND(sq.elapsed_time / 1000, 2) as total_time_ms,
  ROUND(sq.rows_processed / NULLIF(sq.executions, 0), 2) as avg_rows_returned,
  ROUND(sq.buffer_gets / NULLIF(sq.executions, 0), 2) as avg_buffer_gets,
  ROUND(sq.disk_reads / NULLIF(sq.executions, 0), 2) as avg_disk_reads,
  ROUND(sq.cpu_time / NULLIF(sq.executions, 0) / 1000, 2) as avg_cpu_time_ms,
  sq.first_load_time as first_seen,
  sq.last_active_time as last_seen,
  sq.parsing_schema_name as schema_name,
  NULL as calculated_rps
FROM V$SQL sq
WHERE sq.parsing_schema_name = UPPER('{target_owner}')
  AND sq.executions > 0
  AND sq.command_type IN (2, 3, 6, 7)
  AND sq.sql_text NOT LIKE '/* SQL Analyze%'
  AND sq.sql_text NOT LIKE '%SYS.%'
ORDER BY sq.elapsed_time DESC""",
        'parameters': ['target_owner'],
    },
}


class OraclePlugin(DatabasePlugin):
    """Oracle-specific database analyzer plugin."""

    def get_queries(self) -> Dict[str, Any]:
        """Get all Oracle analysis queries."""
        return _oracle_analysis_queries

    def get_database_display_name(self) -> str:
        """Get the display name of the database type."""
        return 'Oracle'

    def apply_result_limit(self, sql: str, max_results: int) -> str:
        """Apply result limit using Oracle FETCH FIRST syntax (12c+)."""
        sql = sql.rstrip(';')
        return f'{sql} FETCH FIRST {max_results} ROWS ONLY;'

    def get_recommended_command(self, source_identifier: str, output_file: str) -> str:
        """Get Oracle-specific command."""
        return f'sqlplus -s <username>@<host>:1521/<service_name> @{output_file} > results.txt'

    def get_run_instructions(
        self, source_identifier: str, output_file: str, source_db_type: str
    ) -> str:
        """Get Oracle-specific instructions for running the generated SQL file."""
        instructions = super().get_run_instructions(source_identifier, output_file, source_db_type)
        return (
            instructions
            + f"""
    NOTE: Requires DBA privilege for DBA_SEGMENTS.
      Queries filter by OWNER = '{source_identifier.upper()}' so running as DBA is safe.
    IMPORTANT: source_identifier must be the schema/owner name (e.g. {source_identifier}), not the PDB/service name.
    NOTE: query_performance_stats uses AWR (DBA_HIST_SQLSTAT) which requires Enterprise Edition + Diagnostics Pack.
      query_performance_stats_vsql is a V$SQL fallback that works on all editions.
      If AWR returns data, prefer it over V$SQL. If AWR is empty, use V$SQL instead."""
        )

    def write_queries_to_file(
        self, source_identifier: str, max_results: int, output_file: str
    ) -> str:
        """Generate SQL file with Oracle-specific prerequisites and resilient ordering.

        Overrides base class to:
        - Inject prerequisite checks at the top
        - Place DBMS_STATS.FLUSH_DATABASE_MONITORING_INFO before table analysis
        - Order queries so information_schema queries run first
        - Place query_performance_stats (AWR) and query_performance_stats_vsql (V$SQL fallback) last
        - Use DBA_SEGMENTS for accurate cross-schema size data
        - Use DBA_HIST_SQLSTAT for historical performance data when available (Enterprise Edition)
        - Fall back to V$SQL cursor cache for Standard Edition / XE

        Args:
            source_identifier: Target schema/owner name
            max_results: Maximum results per query
            output_file: Path to output SQL file

        Returns:
            Path to generated file
        """
        validate_source_identifier(source_identifier)

        queries = self.get_queries()
        upper_owner = source_identifier.upper()

        # Schema queries first, then V$SQL (all editions), then AWR (Enterprise only).
        # AWR errors on Standard/XE are expected; V$SQL provides fallback data.
        query_order = [
            COMPREHENSIVE_TABLE_ANALYSIS,
            COMPREHENSIVE_INDEX_ANALYSIS,
            COLUMN_ANALYSIS,
            CONSTRAINT_ANALYSIS,
            FOREIGN_KEY_ANALYSIS,
            QUERY_PERFORMANCE_STATS_VSQL,
            QUERY_PERFORMANCE_STATS_AWR,
        ]

        sql_content = [
            f'-- {self.get_database_display_name()} Database Analysis Queries',
            f'-- Target Owner: {source_identifier}',
            '-- NOTE: For Oracle, this is the schema/owner name, not the PDB.',
            f"--   Connect to your PDB, but queries filter by OWNER = '{upper_owner}'.",
            f'-- Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
            '',
            '-- EXECUTION INSTRUCTIONS:',
            '-- 1. Review all queries before execution',
            '-- 2. Run during off-peak hours if possible',
            '-- 3. Each query has a FETCH FIRST clause to prevent excessive results',
            '-- 4. query_performance_stats requires Enterprise Edition + Diagnostics Pack (AWR)',
            '-- 5. query_performance_stats_vsql is the V$SQL fallback for Standard/XE editions',
            '-- 6. All queries use DBA_* dictionary views (requires DBA privilege)',
            '-- 7. Table/index size queries use DBA_SEGMENTS (requires DBA privilege).',
            '--    Connect as a DBA user or grant SELECT_CATALOG_ROLE.',
            '',
            '-- sqlplus formatting: prevent line wrapping and produce pipe-separated output',
            'SET LINESIZE 32767',
            'SET PAGESIZE 50000',
            'SET LONG 1000',
            'SET TRIMSPOOL ON',
            'SET TAB OFF',
            "SET COLSEP '|'",
            '',
            '-- Trim wide VARCHAR2(128) dictionary columns to reasonable display widths',
            'COLUMN table_name FORMAT A40',
            'COLUMN index_name FORMAT A40',
            'COLUMN column_name FORMAT A40',
            'COLUMN constraint_name FORMAT A40',
            'COLUMN constraint_type FORMAT A2',
            'COLUMN child_table FORMAT A40',
            'COLUMN child_column FORMAT A40',
            'COLUMN parent_table FORMAT A40',
            'COLUMN parent_column FORMAT A40',
            'COLUMN delete_rule FORMAT A15',
            'COLUMN uniqueness FORMAT A10',
            'COLUMN index_type FORMAT A12',
            'COLUMN status FORMAT A10',
            'COLUMN nullable FORMAT A1',
            'COLUMN data_type FORMAT A30',
            'COLUMN column_type FORMAT A40',
            'COLUMN histogram_type FORMAT A15',
            'COLUMN schema_name FORMAT A30',
            'COLUMN query_pattern FORMAT A200',
            '',
            '-- ============================================',
            '-- PREREQUISITES',
            '-- ============================================',
            '',
            '-- Check prerequisites first.',
            '-- visible_tables=0 means the user lacks SELECT on the target schema objects.',
            '-- tables_without_stats>0 means you should run:',
            f"--   EXEC DBMS_STATS.GATHER_SCHEMA_STATS('{upper_owner}');",
            "SELECT '-- QUERY_NAME_START: prerequisites_check' AS marker FROM DUAL;",
            'SELECT',
            f"  (SELECT COUNT(*) FROM DBA_TABLES WHERE OWNER = '{upper_owner}') as visible_tables,",
            f"  (SELECT COUNT(*) FROM DBA_TABLES WHERE OWNER = '{upper_owner}'"
            f' AND LAST_ANALYZED IS NOT NULL) as tables_with_stats,',
            f"  (SELECT COUNT(*) FROM DBA_TABLES WHERE OWNER = '{upper_owner}'"
            f' AND LAST_ANALYZED IS NULL) as tables_without_stats,',
            f"  (SELECT MIN(LAST_ANALYZED) FROM DBA_TABLES WHERE OWNER = '{upper_owner}'"
            f' AND LAST_ANALYZED IS NOT NULL) as oldest_stats_date',
            'FROM DUAL;',
            "SELECT '-- QUERY_NAME_END: prerequisites_check' AS marker FROM DUAL;",
            '',
            '-- Flush DML tracking so inserts/updates/deletes counts are current.',
            '-- DBA user has the required privileges for this.',
            '-- If this fails, DML counts may be stale or zero. Everything else still works.',
            'BEGIN DBMS_STATS.FLUSH_DATABASE_MONITORING_INFO; END;',
            '/',
            '',
            '-- Generated for DynamoDB Data Modeling',
            '',
        ]

        total_queries = len(query_order)
        query_number = 0

        for query_name in query_order:
            query_info = queries.get(query_name)
            if not query_info:
                logger.warning(
                    f"Query '{query_name}' in query_order not found in queries dict, skipping"
                )
                continue

            query_number += 1

            sql_content.append('')
            sql_content.append('-- ============================================')
            sql_content.append(f'-- QUERY {query_number}/{total_queries}: {query_name}')
            sql_content.append('-- ============================================')
            sql_content.append(f'-- Description: {query_info.get("description", "N/A")}')
            sql_content.append(f'-- Category: {query_info.get("category", "N/A")}')

            # Add contextual comments for performance queries
            if query_name == QUERY_PERFORMANCE_STATS_AWR:
                sql_content.append('-- === AWR (ENTERPRISE EDITION ONLY) ===')
                sql_content.append('-- Requires Enterprise Edition + Diagnostics Pack license.')
                sql_content.append(
                    '-- On Standard/XE/Free this will error — the V$SQL query above already has data.'
                )
            elif query_name == QUERY_PERFORMANCE_STATS_VSQL:
                sql_content.append('-- === V$SQL (ALL EDITIONS) ===')
                sql_content.append(
                    '-- Uses the cursor cache (V$SQL). Works on all Oracle editions.'
                )
                sql_content.append(
                    '-- If the AWR query below also returns data, prefer AWR for longer history.'
                )

            sql_content.append(f"SELECT '-- QUERY_NAME_START: {query_name}' AS marker FROM DUAL;")

            sql = query_info['sql']
            if 'target_owner' in query_info.get('parameters', []):
                sql = sql.format(target_owner=source_identifier)

            sql = self.apply_result_limit(sql, max_results)

            sql_content.append(sql)

            sql_content.append(f"SELECT '-- QUERY_NAME_END: {query_name}' AS marker FROM DUAL;")
            sql_content.append('')

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(sql_content))

        return output_file

    def parse_results_from_file(self, result_file_path: str) -> Dict[str, Any]:
        """Parse Oracle query results with AWR/V$SQL fallback logic."""
        results = super().parse_results_from_file(result_file_path)

        awr_data = results.get(QUERY_PERFORMANCE_STATS_AWR, {}).get('data', [])
        vsql_data = results.get(QUERY_PERFORMANCE_STATS_VSQL, {}).get('data', [])

        if not awr_data and vsql_data:
            results[QUERY_PERFORMANCE_STATS_AWR] = {
                'description': 'Query Performance Statistics (from V$SQL fallback)',
                'data': vsql_data,
            }

        results.pop(QUERY_PERFORMANCE_STATS_VSQL, None)
        return results

    async def execute_managed_mode(self, connection_params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute Oracle analysis in managed mode."""
        raise NotImplementedError(
            'Managed mode is not yet implemented for Oracle. Please use self_service mode.'
        )
