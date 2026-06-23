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

SVV_REDSHIFT_DATABASES_QUERY = """
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

SVV_ALL_SCHEMAS_QUERY = """
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

SVV_ALL_TABLES_QUERY = """
SELECT
    database_name,
    schema_name,
    table_name,
    table_acl,
    table_type,
    remarks
FROM pg_catalog.svv_all_tables
WHERE database_name = :database_name AND schema_name = :schema_name
ORDER BY table_name;
"""

SVV_ALL_COLUMNS_QUERY = """
SELECT
    database_name,
    schema_name,
    table_name,
    column_name,
    ordinal_position,
    column_default,
    is_nullable,
    data_type,
    character_maximum_length,
    numeric_precision,
    numeric_scale,
    remarks
FROM pg_catalog.svv_all_columns
WHERE database_name = :database_name AND schema_name = :schema_name AND table_name = :table_name
ORDER BY ordinal_position;
"""

# SQL guardrails

# Read-only guard limits and deny-list (used by sql_guard.py; sqlglot AST-based).

# Maximum SQL length accepted before parsing; longer input is rejected (fail closed).
MAX_SQL_LEN = 65_536

# Operations denied in read-only mode. Each keyword maps to a sqlglot AST node type
# (or bare-command name) in sql_guard.py; matched structurally, not by leading text.
# Fixed internal constant -- not operator-configurable.
READ_ONLY_DENY_LIST = frozenset(
    {
        'UNLOAD',
        'BEGIN',
        'START',
        'COMMIT',
        'END',
        'ROLLBACK',
        'ABORT',
        'TRUNCATE',
        'CALL',
        'GRANT',
        'REVOKE',
        'VACUUM',
        'ANALYZE',
        'COMMENT',
        'CANCEL',
    }
)
