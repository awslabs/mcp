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

from typing import Any, Dict


# SQL Query Templates for MySQL
mysql_analysis_queries = {
    'performance_schema_check': {
        'name': 'Performance Schema Status Check',
        'description': 'Returns the status of the performance_schema system variable (ON/OFF)',
        'sql': 'SELECT @@performance_schema;',
        'parameters': [],
    },
    'query_pattern_analysis': {
        'name': 'Query Pattern Analysis',
        'description': 'Returns query patterns from Performance Schema with execution counts, calculated RPS, average execution time, average rows examined per execution, scan counts, execution timeframes, and SQL complexity classification',
        'sql': """SELECT
  -- Basic pattern information
  DIGEST_TEXT as query_pattern,
  COUNT_STAR as frequency,
  -- Timing information
  FIRST_SEEN as first_seen,
  LAST_SEEN as last_seen
FROM performance_schema.events_statements_summary_by_digest
WHERE SCHEMA_NAME = '{target_database}'
AND COUNT_STAR > 0
AND LAST_SEEN >= DATE_SUB(NOW(), INTERVAL {pattern_analysis_days} DAY)
-- Exclude system and administrative queries
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
AND DIGEST_TEXT NOT LIKE '%configured_database%'
AND DIGEST_TEXT NOT LIKE 'FLUSH %'
AND DIGEST_TEXT NOT LIKE 'RESET %'
AND DIGEST_TEXT NOT LIKE 'OPTIMIZE %'
AND DIGEST_TEXT NOT LIKE 'ANALYZE %'
AND DIGEST_TEXT NOT LIKE 'CHECK %'
AND DIGEST_TEXT NOT LIKE 'REPAIR %'
AND DIGEST_TEXT NOT LIKE '%@@default_storage_engine%'
AND DIGEST_TEXT NOT LIKE '%@%:=%'
AND DIGEST_TEXT NOT LIKE '%MD5%'
AND DIGEST_TEXT NOT LIKE '%SHA%'
AND DIGEST_TEXT NOT LIKE '%CONCAT_WS%'
ORDER BY frequency DESC;""",
        'parameters': ['target_database', 'pattern_analysis_days'],
    },
    'table_analysis': {
        'name': 'Table Structure Analysis',
        'description': 'Returns table statistics including row counts, data size in MB, index size in MB, column counts, foreign key counts, and creation/modification timestamps',
        'sql': """SELECT
  TABLE_NAME,
  TABLE_ROWS,
  -- Storage sizes in MB
  ROUND(DATA_LENGTH/1024/1024, 2) as datamb,
  ROUND(INDEX_LENGTH/1024/1024, 2) as indexmb,
  -- Count columns in this table
  (SELECT COUNT(*) FROM information_schema.COLUMNS c
   WHERE c.TABLE_SCHEMA = t.TABLE_SCHEMA AND c.TABLE_NAME = t.TABLE_NAME) as columncount,
  -- Count foreign keys in this table
  (SELECT COUNT(*) FROM information_schema.KEY_COLUMN_USAGE k
   WHERE k.TABLE_SCHEMA = t.TABLE_SCHEMA AND k.TABLE_NAME = t.TABLE_NAME
   AND k.REFERENCED_TABLE_NAME IS NOT NULL) as fkcount,
  CREATE_TIME,
  UPDATE_TIME
FROM information_schema.TABLES t
WHERE TABLE_SCHEMA = '{target_database}'
ORDER BY TABLE_ROWS DESC;""",
        'parameters': ['target_database'],
    },
    'column_analysis': {
        'name': 'Column Information Analysis',
        'description': 'Returns all column definitions including table name, column name, data type, nullability, key type, default value, and extra attributes',
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
        'description': 'Returns index structure details including table name, index name, column name, uniqueness flag, and column position within each index',
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
        'description': 'Returns foreign key relationships including constraint names, child/parent table and column mappings, referential action rules, and estimated relationship cardinality',
        'sql': """SELECT
  kcu.CONSTRAINT_NAME,
  kcu.TABLE_NAME as child_table,
  kcu.COLUMN_NAME as child_column,
  kcu.REFERENCED_TABLE_NAME as parent_table,
  kcu.REFERENCED_COLUMN_NAME as parent_column,
  rc.UPDATE_RULE,
  rc.DELETE_RULE,
  -- Estimate relationship cardinality based on unique constraints
  CASE
    WHEN EXISTS (
      SELECT 1 FROM information_schema.STATISTICS s
      WHERE s.TABLE_SCHEMA = '{target_database}'
      AND s.TABLE_NAME = kcu.TABLE_NAME
      AND s.COLUMN_NAME = kcu.COLUMN_NAME
      AND s.NON_UNIQUE = 0  -- Unique constraint exists
      AND (SELECT COUNT(*) FROM information_schema.KEY_COLUMN_USAGE kcu2
           WHERE kcu2.CONSTRAINT_NAME = s.INDEX_NAME
           AND kcu2.TABLE_SCHEMA = s.TABLE_SCHEMA) = 1  -- Single column constraint
    ) THEN '1:1 or 1:0..1'
    ELSE '1:Many'
  END as estimated_cardinality
FROM information_schema.KEY_COLUMN_USAGE kcu
LEFT JOIN information_schema.REFERENTIAL_CONSTRAINTS rc
  ON kcu.CONSTRAINT_NAME = rc.CONSTRAINT_NAME
  AND kcu.CONSTRAINT_SCHEMA = rc.CONSTRAINT_SCHEMA
WHERE kcu.TABLE_SCHEMA = '{target_database}'
  AND kcu.REFERENCED_TABLE_NAME IS NOT NULL  -- Only foreign key constraints
ORDER BY kcu.TABLE_NAME, kcu.COLUMN_NAME;""",
        'parameters': ['target_database'],
    },
    'database_objects': {
        'name': 'Database Objects Summary',
        'description': 'Returns object counts and concatenated names grouped by object type: tables, triggers, stored procedures, and functions',
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
}


def get_query_resource(query_name: str, max_query_results: int, **params) -> Dict[str, Any]:
    """Get a SQL query resource with parameters substituted."""
    if query_name not in mysql_analysis_queries:
        raise ValueError(f"Query '{query_name}' not found")

    query_info = mysql_analysis_queries[query_name].copy()

    # Substitute parameters in SQL
    if params:
        query_info['sql'] = query_info['sql'].format(**params)

    # Apply LIMIT to all queries
    sql = query_info['sql'].rstrip(';')
    query_info['sql'] = f'{sql} LIMIT {max_query_results};'

    return query_info
