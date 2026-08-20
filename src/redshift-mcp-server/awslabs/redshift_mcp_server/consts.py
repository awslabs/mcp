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

# SQL discovery commands. Results are read positionally; {placeholders} are
# filled with quoted identifiers by the caller.
DATABASES_SQL = 'SHOW DATABASES;'
SCHEMAS_SQL = 'SHOW SCHEMAS FROM DATABASE {database};'
TABLES_SQL = 'SHOW TABLES FROM SCHEMA {database}.{schema};'
COLUMNS_SQL = 'SHOW COLUMNS FROM TABLE {database}.{schema}.{table};'

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
