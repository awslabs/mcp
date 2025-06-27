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

# Defaults
DEFAULT_AWS_REGION = 'us-east-1'
DEFAULT_LOG_LEVEL = 'WARNING'

# Timeouts (seconds), etc
CLIENT_TIMEOUT = 60
DATA_CLIENT_TIMEOUT = 60
QUERY_TIMEOUT = 3600
QUERY_POLL_INTERVAL = 2

# Best practices

CLIENT_BEST_PRACTICES = """
## AWS Client Best Practices

### Authentication

- Default AWS credentials chain (IAM roles, ~/.aws/credentials, etc.).
- AWS_PROFILE environment variable (if set).
- AWS_REGION environment variable (if set).
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
WHERE database_name = {}
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
WHERE database_name = {} AND schema_name = {}
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
WHERE database_name = {} AND schema_name = {} AND table_name = {}
ORDER BY ordinal_position;
"""

# SQL guardrails

# Single-lines comments.
re_slc = r'--.*?$'


def re_mlc(g: str) -> str:
    """Multi-line comments, considering balanced recursion."""
    return rf'(?P<mlc{g}>(?:\/\*)(?:[^\/\*]|\/[^\*]|\*[^\/]|(?P>mlc{g}))*(?:\*\/))'


def re_sp(g: str) -> str:
    """Whitespaces, comments, semicolons which can occur between words."""
    return rf'({re_slc}|{re_mlc(g)}|\s|;)'


# We consider `(END|COMMIT|ROLLBACK|ABORT) [WORK|TRANSACTION]` as a breaker for the `BEGIN READ ONLY; {sql}; END;`
# guarding wrapper, having there might be variations of whitespaces and comments in the construct.
SUSPICIOUS_QUERY_REGEXP = (
    rf'(?im)^{re_sp(1)}*(END|COMMIT|ROLLBACK|ABORT)({re_sp(2)}+(WORK|TRANSACTION))?{re_sp(3)}*;'
)
