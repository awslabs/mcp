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

"""Database query operations for S3 Tables MCP Server.

This module provides functions for executing queries against S3 Tables using Athena.
It handles query execution, result retrieval, and proper formatting of responses.
"""

import sqlparse
from .engines.pyiceberg import PyIcebergConfig, PyIcebergEngine
from typing import Any, Dict


WRITE_OPERATIONS = {
    'ADD',
    'ALTER',
    'ANALYZE',
    'BEGIN',
    'COMMIT',
    'COPY',
    'CREATE',
    'DELETE',
    'DROP',
    'EXPORT',
    'GRANT',
    'IMPORT',
    'INSERT',
    'LOAD',
    'LOCK',
    'MERGE',
    'MSCK',
    'REDUCE',
    'REFRESH',
    'REPLACE',
    'RESET',
    'REVOKE',
    'ROLLBACK',
    'SET',
    'START',
    'TRUNCATE',
    'UNCACHE',
    'UNLOCK',
    'UPDATE',
    'UPSERT',
    'VACUUM',
    'VALUES',
    'WRITE',
}

READ_OPERATIONS = {
    'DESC',
    'DESCRIBE',
    'EXPLAIN',
    'LIST',
    'SELECT',
    'SHOW',
    'USE',
}

# Disallowed destructive operations for write
DESTRUCTIVE_OPERATIONS = {'DELETE', 'DROP', 'MERGE', 'REPLACE', 'TRUNCATE', 'VACUUM'}


def _get_query_operations(query: str) -> set:
    """Extract all top-level SQL operations from the query as a set."""
    parsed = sqlparse.parse(query)
    operations = set()
    for stmt in parsed:
        tokens = [token.value.upper() for token in stmt.tokens if not token.is_whitespace]
        for token in tokens:
            if token.isalpha():
                operations.add(token)
    return operations


async def query_database_resource(
    warehouse: str,
    region: str,
    namespace: str,
    query: str,
    uri: str = 'https://s3tables.us-west-2.amazonaws.com/iceberg',
    catalog_name: str = 's3tablescatalog',
    rest_signing_name: str = 's3tables',
    rest_sigv4_enabled: str = 'true',
) -> Dict[str, Any]:
    """Execute a read-only query against a database using PyIceberg."""
    operations = _get_query_operations(query)
    disallowed = operations & WRITE_OPERATIONS
    if disallowed:
        raise ValueError(f'Write operations are not allowed in read-only queries: {disallowed}')
    config = PyIcebergConfig(
        warehouse=warehouse,
        uri=uri,
        region=region,
        namespace=namespace,
        catalog_name=catalog_name,
        rest_signing_name=rest_signing_name,
        rest_sigv4_enabled=rest_sigv4_enabled,
    )
    engine = PyIcebergEngine(config)
    result = engine.execute_query(query)
    return result


async def append_rows_to_table_resource(
    warehouse: str,
    region: str,
    namespace: str,
    table_name: str,
    rows: list,
    uri: str = 'https://s3tables.us-west-2.amazonaws.com/iceberg',
    catalog_name: str = 's3tablescatalog',
    rest_signing_name: str = 's3tables',
    rest_sigv4_enabled: str = 'true',
) -> Dict[str, Any]:
    """Append rows to an Iceberg table using PyIceberg."""
    config = PyIcebergConfig(
        warehouse=warehouse,
        uri=uri,
        region=region,
        namespace=namespace,
        catalog_name=catalog_name,
        rest_signing_name=rest_signing_name,
        rest_sigv4_enabled=rest_sigv4_enabled,
    )
    engine = PyIcebergEngine(config)
    engine.append_rows(table_name, rows)
    return {'status': 'success', 'rows_appended': len(rows)}
