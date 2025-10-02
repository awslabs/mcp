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

"""Source Database Analysis SQL Query Resources for DynamoDB Data Modeling."""

import os
from typing import Any, Dict


# SQL Query Templates for MySQL
mysql_analysis_queries = {
    'database_identification': {
        'name': 'Database Identification',
        'description': 'Identifies the currently configured database connection to confirm which database will be analyzed',
        'sql': 'SELECT DATABASE() as configured_database;',
        'parameters': [],
    },
    'performance_schema_check': {
        'name': 'Performance Schema Status Check',
        'description': 'Verifies if MySQL Performance Schema is enabled, which is required for query pattern analysis and RPS calculations',
        'sql': "SHOW VARIABLES LIKE 'performance_schema';",
        'parameters': [],
    },
    'pattern_analysis': {
        'name': 'Query Pattern Analysis',
        'description': 'Analyzes normalized query patterns from Performance Schema over specified time period, calculating RPS, execution times, scan patterns, and complexity classification for DynamoDB Data Modeling',
        'sql': """SELECT
  DIGEST_TEXT as query_pattern,
  COUNT_STAR as frequency,
  ROUND(COUNT_STAR / ({analysis_days} * 24 * 3600), 4) as calculated_rps,
  ROUND(AVG_TIMER_WAIT/1000000000, 6) as avg_execution_time,
  ROUND(SUM_ROWS_EXAMINED/COUNT_STAR, 1) as avg_rows_per_query,
  SUM_SELECT_SCAN as full_table_scans,
  SUM_SELECT_FULL_JOIN as full_joins,
  FIRST_SEEN as first_seen,
  LAST_SEEN as last_seen,
  CASE
    WHEN DIGEST_TEXT LIKE 'SELECT%FROM%WHERE%' AND DIGEST_TEXT NOT LIKE '%JOIN%' THEN 'Single Table Search'
    WHEN DIGEST_TEXT LIKE '%JOIN%' THEN 'JOIN Query'
    WHEN DIGEST_TEXT LIKE '%JOIN%'
        AND (DIGEST_TEXT LIKE '%GROUP BY%' OR DIGEST_TEXT LIKE '%ORDER BY%'
            OR DIGEST_TEXT LIKE '%HAVING%') THEN 'Complex JOIN'
    WHEN DIGEST_TEXT REGEXP '^CALL [a-zA-Z_][a-zA-Z0-9_]*' THEN 'Stored Procedure'
    WHEN DIGEST_TEXT LIKE 'SELECT%' THEN 'Simple SELECT'
    ELSE 'Other'
  END as complexity_type,
  CASE
    WHEN DIGEST_TEXT LIKE '%WHERE%id%=%' THEN 'Likely Primary Key'
    WHEN DIGEST_TEXT LIKE '%WHERE%' AND DIGEST_TEXT LIKE '%=%' THEN 'Likely Indexed'
    WHEN DIGEST_TEXT LIKE '%WHERE%' AND DIGEST_TEXT LIKE '%LIKE%' THEN 'Potential Full Scan'
    ELSE 'Unknown Index Usage'
  END as index_usage_hint
FROM performance_schema.events_statements_summary_by_digest
WHERE SCHEMA_NAME = '{target_database}'
AND COUNT_STAR > 5
AND LAST_SEEN >= DATE_SUB(NOW(), INTERVAL {analysis_days} DAY)
AND DIGEST_TEXT NOT LIKE 'SET%'
AND DIGEST_TEXT NOT LIKE 'USE %'
AND DIGEST_TEXT NOT LIKE 'SHOW%'
AND DIGEST_TEXT NOT LIKE '/* RDS Data API */%'
AND DIGEST_TEXT NOT LIKE '%information_schema%'
AND DIGEST_TEXT NOT LIKE '%performance_schema%'
AND DIGEST_TEXT NOT LIKE '%mysql.%'
AND DIGEST_TEXT NOT LIKE 'SELECT @@%'
AND DIGEST_TEXT NOT LIKE '%sys.%'
AND DIGEST_TEXT NOT LIKE 'select ?'
AND DIGEST_TEXT NOT LIKE '%mysql.general_log%'
AND DIGEST_TEXT NOT LIKE 'DESCRIBE %'
AND DIGEST_TEXT NOT LIKE 'EXPLAIN %'
AND DIGEST_TEXT NOT LIKE 'configured_database'
ORDER BY frequency DESC;""",
        'parameters': ['target_database', 'analysis_days'],
    },
    'table_analysis': {
        'name': 'Table Structure Analysis',
        'description': 'Analyzes table sizes, row counts, data/index storage usage, column counts, and foreign key relationships to understand database structure and identify largest tables',
        'sql': """SELECT
  TABLE_NAME,
  TABLE_ROWS,
  ROUND(DATA_LENGTH/1024/1024, 2) as datamb,
  ROUND(INDEX_LENGTH/1024/1024, 2) as indexmb,
  (SELECT COUNT(*) FROM information_schema.COLUMNS c WHERE c.TABLE_SCHEMA = t.TABLE_SCHEMA AND c.TABLE_NAME = t.TABLE_NAME) as columncount,
  (SELECT COUNT(*) FROM information_schema.KEY_COLUMN_USAGE k WHERE k.TABLE_SCHEMA = t.TABLE_SCHEMA AND k.TABLE_NAME = t.TABLE_NAME AND k.REFERENCED_TABLE_NAME IS NOT NULL) as fkcount,
  CREATE_TIME,
  UPDATE_TIME
FROM information_schema.TABLES t
WHERE TABLE_SCHEMA = '{target_database}'
ORDER BY TABLE_ROWS DESC;""",
        'parameters': ['target_database'],
    },
    'column_analysis': {
        'name': 'Column Information Analysis',
        'description': 'Detailed analysis of column structures, data types, nullability, keys, and defaults to understand attribute patterns and identify potential DynamoDB attribute mappings and data type conversions',
        'sql': """SELECT
  TABLE_NAME,
  COLUMN_NAME,
  COLUMN_TYPE,
  IS_NULLABLE,
  COLUMN_KEY,
  COLUMN_DEFAULT,
  EXTRA
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = '{target_database}'
ORDER BY TABLE_NAME, ORDINAL_POSITION;""",
        'parameters': ['target_database'],
    },
    'index_analysis': {
        'name': 'Index Statistics Analysis',
        'description': 'Analyzes index structures, compositions, and uniqueness constraints to identify access patterns and determine optimal DynamoDB key design and Global Secondary Index requirements',
        'sql': """SELECT
  TABLE_NAME,
  INDEX_NAME,
  COLUMN_NAME,
  NON_UNIQUE,
  SEQ_IN_INDEX
FROM information_schema.STATISTICS
WHERE TABLE_SCHEMA = '{target_database}'
ORDER BY TABLE_NAME, INDEX_NAME, SEQ_IN_INDEX;""",
        'parameters': ['target_database'],
    },
    'foreign_key_analysis': {
        'name': 'Foreign Key Relationship Analysis',
        'description': 'Analyzes foreign key constraints, referential integrity rules, and relationship cardinalities to understand entity relationships and design appropriate DynamoDB item collections and access patterns',
        'sql': """SELECT
  kcu.CONSTRAINT_NAME,
  kcu.TABLE_NAME as child_table,
  kcu.COLUMN_NAME as child_column,
  kcu.REFERENCED_TABLE_NAME as parent_table,
  kcu.REFERENCED_COLUMN_NAME as parent_column,
  rc.UPDATE_RULE,
  rc.DELETE_RULE,
  CASE
    WHEN EXISTS (
      SELECT 1 FROM information_schema.STATISTICS s
      WHERE s.TABLE_SCHEMA = '{target_database}'
      AND s.TABLE_NAME = kcu.TABLE_NAME
      AND s.COLUMN_NAME = kcu.COLUMN_NAME
      AND s.NON_UNIQUE = 0
    ) THEN '1:1 or 1:0..1'
    ELSE '1:Many'
  END as estimated_cardinality
FROM information_schema.KEY_COLUMN_USAGE kcu
LEFT JOIN information_schema.REFERENTIAL_CONSTRAINTS rc
  ON kcu.CONSTRAINT_NAME = rc.CONSTRAINT_NAME
  AND kcu.CONSTRAINT_SCHEMA = rc.CONSTRAINT_SCHEMA
WHERE kcu.TABLE_SCHEMA = '{target_database}'
  AND kcu.REFERENCED_TABLE_NAME IS NOT NULL
ORDER BY kcu.TABLE_NAME, kcu.COLUMN_NAME;""",
        'parameters': ['target_database'],
    },
    'database_objects': {
        'name': 'Database Objects Summary',
        'description': 'Comprehensive inventory of database objects including tables, triggers, stored procedures, and functions to identify complexity and potential application logic that needs to be redesigned for DynamoDB',
        'sql': """SELECT
  'Tables' as object_type,
  COUNT(*) as count,
  GROUP_CONCAT(TABLE_NAME) as names
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = '{target_database}'
UNION ALL
SELECT
  'Triggers' as object_type,
  COUNT(*) as count,
  COALESCE(GROUP_CONCAT(TRIGGER_NAME), 'None') as names
FROM information_schema.TRIGGERS
WHERE TRIGGER_SCHEMA = '{target_database}'
UNION ALL
SELECT
  'Stored Procedures' as object_type,
  COUNT(*) as count,
  COALESCE(GROUP_CONCAT(ROUTINE_NAME), 'None') as names
FROM information_schema.ROUTINES
WHERE ROUTINE_SCHEMA = '{target_database}'
AND ROUTINE_TYPE = 'PROCEDURE'
UNION ALL
SELECT
  'Functions' as object_type,
  COUNT(*) as count,
  COALESCE(GROUP_CONCAT(ROUTINE_NAME), 'None') as names
FROM information_schema.ROUTINES
WHERE ROUTINE_SCHEMA = '{target_database}'
AND ROUTINE_TYPE = 'FUNCTION';""",
        'parameters': ['target_database'],
    },
    'rps_calculation': {
        'name': 'RPS and Traffic Analysis',
        'description': 'Calculates requests per second (RPS) and analyzes traffic patterns by date/hour, read/write ratios, and query distribution to determine DynamoDB capacity requirements and identify peak usage periods for scaling planning',
        'sql': """SELECT
  DATE(LAST_SEEN) as analysis_date,
  HOUR(LAST_SEEN) as analysis_hour,
  SUM(COUNT_STAR) as total_queries,
  SUM(COUNT_STAR) / 3600 as avg_rps_this_hour,
  COUNT(DISTINCT DIGEST) as unique_query_patterns,
  SUM(COUNT_STAR / ({analysis_days} * 24 * 3600)) as estimated_average_rps,
  MAX(COUNT_STAR) as highest_pattern_frequency,
  COUNT(DISTINCT DIGEST) as unique_query_patterns,
  SUM(CASE WHEN DIGEST_TEXT LIKE 'SELECT%' THEN COUNT_STAR ELSE 0 END) as read_queries,
  SUM(CASE WHEN DIGEST_TEXT NOT LIKE 'SELECT%' THEN COUNT_STAR ELSE 0 END) as write_queries
FROM performance_schema.events_statements_summary_by_digest
WHERE SCHEMA_NAME = '{target_database}'
  AND LAST_SEEN >= DATE_SUB(NOW(), INTERVAL {analysis_days} DAY)
  AND COUNT_STAR > 0
  AND DIGEST_TEXT NOT LIKE 'SET%'
  AND DIGEST_TEXT NOT LIKE 'USE %'
  AND DIGEST_TEXT NOT LIKE 'SHOW%'
  AND DIGEST_TEXT NOT LIKE '/* RDS Data API */%'
  AND DIGEST_TEXT NOT LIKE '%information_schema%'
  AND DIGEST_TEXT NOT LIKE '%performance_schema%'
  AND DIGEST_TEXT NOT LIKE '%mysql.%'
  AND DIGEST_TEXT NOT LIKE 'SELECT @@%'
  AND DIGEST_TEXT NOT LIKE '%sys.%'
  AND DIGEST_TEXT NOT LIKE 'select ?'
  AND DIGEST_TEXT NOT LIKE '%mysql.general_log%'
  AND DIGEST_TEXT NOT LIKE 'DESCRIBE %'
  AND DIGEST_TEXT NOT LIKE 'EXPLAIN %'
  AND DIGEST_TEXT NOT LIKE 'configured_database'
GROUP BY DATE(LAST_SEEN), HOUR(LAST_SEEN)
ORDER BY analysis_date DESC, analysis_hour DESC;""",
        'parameters': ['target_database', 'analysis_days'],
    },
}


def get_query_resource(query_name: str, **params) -> Dict[str, Any]:
    """Get a SQL query resource with parameters substituted."""
    if query_name not in mysql_analysis_queries:
        raise ValueError(f"Query '{query_name}' not found")

    query_info = mysql_analysis_queries[query_name].copy()

    # Substitute parameters in SQL
    if params:
        query_info['sql'] = query_info['sql'].format(**params)

    # Add configurable LIMIT to prevent context overflow
    max_results = int(os.getenv('MYSQL_MAX_QUERY_RESULTS', '500'))
    limit_queries = [
        'pattern_analysis',
        'column_analysis',
        'index_analysis',
        'foreign_key_analysis',
    ]

    if query_name in limit_queries and not query_info['sql'].upper().endswith(';'):
        query_info['sql'] += f' LIMIT {max_results};'
    elif query_name in limit_queries and query_info['sql'].upper().endswith(';'):
        query_info['sql'] = query_info['sql'][:-1] + f' LIMIT {max_results};'

    return query_info
