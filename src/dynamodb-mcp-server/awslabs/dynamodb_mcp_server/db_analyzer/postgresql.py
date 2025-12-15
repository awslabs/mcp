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

"""PostgreSQL database analyzer plugin."""

from awslabs.dynamodb_mcp_server.db_analyzer.base_plugin import DatabasePlugin
from typing import Any, Dict


_postgresql_analysis_queries = {
    'pg_stat_statements_check': {
        'name': 'pg_stat_statements Extension Check',
        'description': 'Check if pg_stat_statements extension is installed and enabled',
        'category': 'internal',
        'sql': """SELECT
                      CASE WHEN COUNT(*) > 0 THEN 1 ELSE 0 END as enabled
                  FROM pg_extension
                  WHERE extname = 'pg_stat_statements';""",
        'parameters': [],
    },
    'comprehensive_table_analysis': {
        'name': 'Comprehensive Table Analysis',
        'description': 'Complete table statistics including structure, size, and I/O',
        'category': 'information_schema',
        'sql': """SELECT
  pst.relname as table_name,
  pst.n_live_tup as row_count,
  pg_total_relation_size(c.oid) as total_size_bytes,
  pg_relation_size(c.oid) as data_size_bytes,
  pg_total_relation_size(c.oid) - pg_relation_size(c.oid) as index_size_bytes,
  ROUND(pg_relation_size(c.oid)::numeric/1024/1024, 2) as data_size_mb,
  ROUND((pg_total_relation_size(c.oid) - pg_relation_size(c.oid))::numeric/1024/1024, 2)
    as index_size_mb,
  ROUND(pg_total_relation_size(c.oid)::numeric/1024/1024, 2) as total_size_mb,
  pst.seq_scan as sequential_scans,
  pst.seq_tup_read as sequential_rows_read,
  pst.idx_scan as index_scans,
  pst.idx_tup_fetch as index_rows_fetched,
  pst.n_tup_ins as inserts,
  pst.n_tup_upd as updates,
  pst.n_tup_del as deletes,
  pst.n_tup_hot_upd as hot_updates,
  pst.n_live_tup as live_tuples,
  pst.n_dead_tup as dead_tuples
FROM pg_stat_user_tables pst
JOIN pg_class c ON c.relname = pst.relname
  AND c.relnamespace = (SELECT oid FROM pg_namespace WHERE nspname = pst.schemaname)
ORDER BY pst.n_live_tup DESC;""",
        'parameters': [],
    },
    'comprehensive_index_analysis': {
        'name': 'Comprehensive Index Analysis',
        'description': 'Complete index statistics including structure and usage',
        'category': 'information_schema',
        'sql': """SELECT
  psi.relname as table_name,
  psi.indexrelname as index_name,
  psi.idx_scan as index_scans,
  psi.idx_tup_read as tuples_read,
  psi.idx_tup_fetch as tuples_fetched,
  pg_size_pretty(pg_relation_size(psi.indexrelid)) as index_size,
  pg_relation_size(psi.indexrelid) as index_size_bytes
FROM pg_stat_user_indexes psi
ORDER BY psi.relname, psi.indexrelname;""",
        'parameters': [],
    },
    'column_analysis': {
        'name': 'Column Information Analysis',
        'description': 'Returns all column definitions including data types, nullability, and defaults',
        'category': 'information_schema',
        'sql': """SELECT
  table_name,
  column_name,
  ordinal_position as position,
  column_default as default_value,
  is_nullable as nullable,
  data_type,
  character_maximum_length as char_max_length,
  numeric_precision,
  numeric_scale,
  udt_name as column_type
FROM information_schema.columns
WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
ORDER BY table_name, ordinal_position;""",
        'parameters': [],
    },
    'foreign_key_analysis': {
        'name': 'Foreign Key Relationship Analysis',
        'description': 'Returns foreign key relationships with constraint names and table/column mappings',
        'category': 'information_schema',
        'sql': """SELECT
  tc.constraint_name,
  tc.table_name as child_table,
  kcu.column_name as child_column,
  ccu.table_name as parent_table,
  ccu.column_name as parent_column,
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
  ON rc.constraint_name = tc.constraint_name
  AND rc.constraint_schema = tc.table_schema
WHERE tc.constraint_type = 'FOREIGN KEY'
  AND tc.table_schema NOT IN ('pg_catalog', 'information_schema')
ORDER BY tc.table_name, kcu.column_name;""",
        'parameters': [],
    },
    'query_performance_stats': {
        'name': 'Query Performance Statistics',
        'description': 'Query execution statistics with performance metrics from pg_stat_statements',
        'category': 'performance_schema',
        'sql': """SELECT
  LEFT(pss.query, 200) as query_pattern,
  pss.calls as executions,
  ROUND((pss.total_exec_time / NULLIF(pss.calls, 0))::numeric, 2) as avg_latency_ms,
  ROUND(pss.total_exec_time::numeric, 2) as total_time_ms,
  pss.rows as rows_affected,
  ROUND((pss.rows::numeric / NULLIF(pss.calls, 0)), 2) as avg_rows_returned,
  pss.shared_blks_hit as cache_hits,
  pss.shared_blks_read as disk_reads,
  ROUND((pss.shared_blks_hit::numeric /
    NULLIF(pss.shared_blks_hit + pss.shared_blks_read, 0) * 100), 2) as cache_hit_ratio_pct,
  pss.temp_blks_read as temp_blocks_read,
  pss.temp_blks_written as temp_blocks_written,
  ROUND(pss.blk_read_time::numeric, 2) as io_read_time_ms,
  ROUND(pss.blk_write_time::numeric, 2) as io_write_time_ms,
  COALESCE(psd.stats_reset, pg_postmaster_start_time()) as first_seen,
  now() as last_seen,
  ROUND((pss.calls::numeric / NULLIF(EXTRACT(EPOCH FROM
    (now() - COALESCE(psd.stats_reset, pg_postmaster_start_time()))), 0)), 6) as estimated_rps
FROM pg_stat_statements pss
JOIN pg_stat_database psd ON pss.dbid = psd.datid
WHERE pss.dbid = (SELECT oid FROM pg_database WHERE datname = current_database())
  -- Filter out PostgreSQL system catalogs and views (explicit list to avoid filtering user tables with pg_ prefix)
  AND pss.query NOT LIKE '%pg_catalog%'
  AND pss.query NOT LIKE '%pg_stat_statements%'
  AND pss.query NOT LIKE '%pg_stat_user_tables%'
  AND pss.query NOT LIKE '%pg_stat_user_indexes%'
  AND pss.query NOT LIKE '%pg_stat_user_functions%'
  AND pss.query NOT LIKE '%pg_stat_database%'
  AND pss.query NOT LIKE '%pg_stat_activity%'
  AND pss.query NOT LIKE '%pg_class%'
  AND pss.query NOT LIKE '%pg_namespace%'
  AND pss.query NOT LIKE '%pg_attribute%'
  AND pss.query NOT LIKE '%pg_index%'
  AND pss.query NOT LIKE '%pg_constraint%'
  AND pss.query NOT LIKE '%pg_type%'
  AND pss.query NOT LIKE '%pg_extension%'
  AND pss.query NOT LIKE '%pg_database%'
  AND pss.query NOT LIKE '%pg_tables%'
  AND pss.query NOT LIKE '%pg_indexes%'
  AND pss.query NOT LIKE '%pg_views%'
  AND pss.query NOT LIKE '%pg_locks%'
  AND pss.query NOT LIKE '%pg_settings%'
  -- Filter out PostgreSQL system functions
  AND pss.query NOT LIKE '%pg_relation_size%'
  AND pss.query NOT LIKE '%pg_total_relation_size%'
  AND pss.query NOT LIKE '%pg_size_pretty%'
  AND pss.query NOT LIKE '%pg_postmaster_start_time%'
  AND pss.query NOT LIKE '%pg_sleep%'
  -- Filter out information_schema
  AND pss.query NOT LIKE '%information_schema%'
  -- Filter out session/transaction control
  AND pss.query !~* '^(SET|SHOW|RESET|BEGIN|COMMIT|ROLLBACK|SAVEPOINT|RELEASE|DEALLOCATE|DISCARD)\\s'
  AND pss.query !~* '^(LISTEN|NOTIFY|UNLISTEN)\\s'
  -- Filter out utility/maintenance commands
  AND pss.query !~* '^(VACUUM|ANALYZE|REINDEX|CLUSTER|CHECKPOINT|EXPLAIN)\\s'
  -- Filter out DDL (focus on DML for access patterns)
  AND pss.query !~* '^(CREATE|ALTER|DROP|TRUNCATE|COMMENT|GRANT|REVOKE)\\s'
ORDER BY pss.total_exec_time DESC;""",
        'parameters': [],
    },
}


class PostgreSQLPlugin(DatabasePlugin):
    """PostgreSQL-specific database analyzer plugin."""

    def get_queries(self) -> Dict[str, Any]:
        """Get all PostgreSQL analysis queries."""
        return _postgresql_analysis_queries

    def get_database_display_name(self) -> str:
        """Get the display name of the database type."""
        return 'PostgreSQL'

    # write_queries_to_file and apply_result_limit are inherited from DatabasePlugin base class

    # parse_results_from_file is inherited from DatabasePlugin base class

    async def execute_managed_mode(self, connection_params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute PostgreSQL analysis in managed mode.

        Note: Managed mode not yet implemented for PostgreSQL.
        """
        raise NotImplementedError(
            'Managed mode is not yet implemented for PostgreSQL. Please use self_service mode.'
        )
