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

"""Redshift MCP Server constants."""

# System
CLIENT_CONNECT_TIMEOUT = 60
CLIENT_READ_TIMEOUT = 600
CLIENT_RETRIES = {'max_attempts': 5, 'mode': 'adaptive'}
CLIENT_USER_AGENT_NAME = 'awslabs/mcp/redshift-mcp-server'
DEFAULT_LOG_LEVEL = 'WARNING'
QUERY_TIMEOUT = 3600
QUERY_POLL_INTERVAL = 1
SESSION_KEEPALIVE = 600

# Best practices

CLIENT_BEST_PRACTICES = """
## AWS Client Best Practices

### Authentication and Configuration

- Default AWS credentials chain (IAM roles, ~/.aws/credentials, etc.).
- AWS_PROFILE environment variable (if set).
- Region configuration (in order of precedence):
  - AWS_REGION environment variable (highest priority)
  - AWS_DEFAULT_REGION environment variable
  - Region specified in AWS profile configuration

### Error Handling

- Always print out AWS client errors in full to help diagnose configuration issues.
- For region-related errors, suggest checking AWS_REGION, AWS_DEFAULT_REGION, or AWS profile configuration.
- For credential errors, suggest verifying AWS credentials setup and permissions.
"""

REDSHIFT_BEST_PRACTICES = """
## Amazon Redshift Best Practices

### Query Guidelines

- Always specify the database and schema when referencing objects to avoid ambiguity.
- Leverage distribution in WHERE and JOIN predicates and sort keys in ORDER BY for optimal query performance.
- Use LIMIT clauses for exploratory queries to avoid large result sets.
- Analyze table to update table statistics if it is not updated or too off before making a decision on the query structure.
- Prefer explicitly specifying columns in SELECT over "*" for better performance.

### Connection Guidelines

- We are use the Redshift API and Redshift Data API.
- Leverage IAM authentication when possible instead of secrets (database passwords).
"""

# SQL queries

DATABASES_SQL = """
SELECT
    database_name,
    database_owner,
    database_type,
    database_acl,
    database_options,
    database_isolation_level
FROM pg_catalog.svv_redshift_databases
ORDER BY database_name;
"""

SCHEMAS_SQL = """
SELECT
    database_name,
    schema_name,
    schema_owner,
    schema_type,
    schema_acl,
    source_database,
    schema_option
FROM pg_catalog.svv_all_schemas
WHERE database_name = :database_name
ORDER BY schema_name;
"""

TABLES_SQL = """
SELECT
    database_name,
    schema_name,
    table_name,
    table_acl,
    table_type,
    remarks,
    NULL AS external_location,
    NULL AS external_parameters
FROM pg_catalog.svv_redshift_tables
WHERE database_name = :database_name AND schema_name = :schema_name

UNION ALL

SELECT
    redshift_database_name AS database_name,
    schemaname AS schema_name,
    tablename AS table_name,
    NULL AS table_acl,
    'EXTERNAL TABLE' AS table_type,
    NULL AS remarks,
    location AS external_location,
    parameters AS external_parameters
FROM pg_catalog.svv_external_tables
WHERE redshift_database_name = :database_name AND schemaname = :schema_name

ORDER BY table_name;
"""

# Regular (non-superuser) users can query pg_stat_user_tables, but they'll only see
# stats for tables they have permissions on.
TABLES_EXTRA_SQL = """
SELECT
    n.nspname AS schema_name,
    c.relname AS table_name,
    CASE
        WHEN ci.releffectivediststyle = 0 THEN 'EVEN'
        WHEN ci.releffectivediststyle = 1 THEN 'KEY'
        WHEN ci.releffectivediststyle = 8 THEN 'ALL'
        WHEN ci.releffectivediststyle = 10 THEN 'AUTO(ALL)'
        WHEN ci.releffectivediststyle = 11 THEN 'AUTO(EVEN)'
        WHEN ci.releffectivediststyle = 12 THEN 'AUTO(KEY)'
        ELSE 'UNKNOWN'
    END AS diststyle,
    c.reltuples::bigint AS estimated_row_count,
    s.seq_scan AS sequential_scans,
    s.seq_tup_read AS sequential_tuples_read,
    s.n_tup_ins AS rows_inserted,
    s.n_tup_upd AS rows_updated,
    s.n_tup_del AS rows_deleted,
    s.n_live_tup AS live_row_count,
    s.n_dead_tup AS dead_row_count,
    s.last_analyze AS last_analyze_time,
    s.last_autoanalyze AS last_autoanalyze_time,
    s.analyze_count AS analyze_count,
    s.autoanalyze_count AS autoanalyze_count,
    s.n_mod_since_analyze AS rows_modified_since_analyze
FROM pg_catalog.pg_class c
JOIN pg_catalog.pg_namespace n ON c.relnamespace = n.oid
JOIN pg_catalog.pg_class_info ci ON c.oid = ci.reloid
LEFT JOIN pg_catalog.pg_stat_user_tables s ON c.oid = s.relid
WHERE n.nspname = :schema_name
  AND c.relkind = 'r'
ORDER BY c.relname;
"""

COLUMNS_SQL = """
SELECT
    database_name,
    schema_name,
    table_name,
    column_name,
    ordinal_position,
    column_default,
    is_nullable,
    data_type,
    NULL AS character_maximum_length,
    NULL AS numeric_precision,
    NULL AS numeric_scale,
    remarks,
    encoding AS redshift_encoding,
    distkey AS redshift_is_distkey,
    sortkey AS redshift_sortkey_position,
    NULL AS external_type,
    NULL AS external_partition_key
FROM pg_catalog.svv_redshift_columns
WHERE database_name = :database_name AND schema_name = :schema_name AND table_name = :table_name

UNION ALL

SELECT
    redshift_database_name AS database_name,
    schemaname AS schema_name,
    tablename AS table_name,
    columnname AS column_name,
    columnnum AS ordinal_position,
    NULL AS column_default,
    is_nullable,
    external_type AS data_type,
    NULL AS character_maximum_length,
    NULL AS numeric_precision,
    NULL AS numeric_scale,
    NULL AS remarks,
    NULL AS redshift_encoding,
    NULL AS redshift_is_distkey,
    NULL AS redshift_sortkey_position,
    external_type AS external_type,
    part_key AS external_partition_key
FROM pg_catalog.svv_external_columns
WHERE redshift_database_name = :database_name AND schemaname = :schema_name AND tablename = :table_name

ORDER BY ordinal_position;
"""

# Regular (non-superuser) users can query pg_stats, but they'll only see
# stats for tables they have permissions on.
# Used in execution plan analysis to enrich columns with planner statistics.
COLUMN_STATS_SQL = """
SELECT
    attname AS column_name,
    n_distinct,
    null_frac,
    avg_width,
    correlation
FROM pg_catalog.pg_stats
WHERE schemaname = :schema_name
  AND tablename = :table_name
ORDER BY attname;
"""

# SQL guardrails

# Single-lines comments.
re_slc = r'--.*?$'


def re_mlc(g: int) -> str:
    """Multi-line comments, considering balanced recursion."""
    return rf'(?P<mlc{g}>(?:\/\*)(?:[^\/\*]|\/[^\*]|\*[^\/]|(?P>mlc{g}))*(?:\*\/))'


def re_sp(g: int) -> str:
    """Whitespaces, comments, semicolons which can occur between words."""
    return rf'({re_slc}|{re_mlc(g)}|\s|;)'


# We consider `(END|COMMIT|ROLLBACK|ABORT) [WORK|TRANSACTION]` as a breaker for the `BEGIN READ ONLY; {sql}; END;`
# guarding wrapper, having there might be variations of whitespaces and comments in the construct.
SUSPICIOUS_QUERY_REGEXP = rf'(?im)(^|;){re_sp(1)}*(END|COMMIT|ROLLBACK|ABORT)({re_sp(2)}+(WORK|TRANSACTION))?{re_sp(3)}*;'
