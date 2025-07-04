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

import os
import sqlparse
from . import __version__
from .engines.athena import AthenaEngine
from .engines.config import AthenaConfig
from typing import Any, Dict, Optional


WRITE_OPERATIONS = {
    'ADD',
    'ALTER',
    'ANALYZE',
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


def _execute_database_query(
    table_bucket_arn: str,
    namespace: str,
    query: str,
    output_location: Optional[str] = None,
    workgroup: str = 'primary',
    region_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Internal helper function to execute database queries.

    Args:
        table_bucket_arn: The ARN of the table bucket containing the table
        namespace: The namespace containing the table
        query: Custom SQL query
        output_location: Optional S3 location for query results
        workgroup: Athena workgroup to use for query execution
        region_name: Optional AWS region name. If not provided, uses AWS_REGION environment variable

    Returns:
        Dict containing query results and metadata

    Raises:
        ValueError: If AWS_REGION is not set
        ConnectionError: If connection to Athena fails
    """
    # Get region from parameter or environment variable
    region = region_name or os.getenv('AWS_REGION')
    if not region:
        raise ValueError('AWS_REGION environment variable must be set')

    # Extract bucket name from ARN and get the last part after any slashes
    bucket_name = table_bucket_arn.split(':')[-1].split('/')[-1]

    # Extract account ID from ARN
    account_id = table_bucket_arn.split(':')[4]

    # Set default output location if not provided
    if output_location is None:
        output_location = f's3://aws-athena-query-results-{account_id}-{region}/'

    # Initialize Athena configuration with string values
    config = AthenaConfig(
        output_location=output_location,
        region=region,
        database=namespace,  # Use namespace as database name
        catalog=f's3tablescatalog/{bucket_name}',  # Use bucket name without 'bucket/' prefix
        workgroup=workgroup,  # workgroup is already a string
    )

    # Initialize Athena engine
    engine = AthenaEngine(config)

    # Test connection
    if not engine.test_connection():
        raise ConnectionError('Failed to connect to Athena')

    # Prepend version comment to the query
    version_comment = f'/* awslabs/mcp/s3-tables-mcp-server/{__version__} */'
    query_with_comment = f'{version_comment}\n{query}'

    results = engine.execute_query(query_with_comment)

    return {
        'status': 'success',
        'data': {
            'columns': results['columns'],
            'rows': results['rows'],
            'metadata': {
                'output_location': results['output_location'],
                'query_execution': results['query_execution'],
            },
        },
    }


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
    table_bucket_arn: str,
    namespace: str,
    query: str,
    output_location: Optional[str] = None,
    workgroup: str = 'primary',
    region_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Execute a read-only query against a database using Athena."""
    operations = _get_query_operations(query)
    disallowed = operations & WRITE_OPERATIONS
    if disallowed:
        raise ValueError(f'Write operations are not allowed in read-only queries: {disallowed}')
    return _execute_database_query(
        table_bucket_arn=table_bucket_arn,
        namespace=namespace,
        query=query,
        output_location=output_location,
        workgroup=workgroup,
        region_name=region_name,
    )


async def modify_database_resource(
    table_bucket_arn: str,
    namespace: str,
    query: str,
    output_location: Optional[str] = None,
    workgroup: str = 'primary',
    region_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Execute a query against a database using Athena, allowing write operations except destructive ones."""
    operations = _get_query_operations(query)
    disallowed = operations & DESTRUCTIVE_OPERATIONS
    if disallowed:
        raise ValueError(f'Destructive operations are not allowed in write queries: {disallowed}')
    return _execute_database_query(
        table_bucket_arn=table_bucket_arn,
        namespace=namespace,
        query=query,
        output_location=output_location,
        workgroup=workgroup,
        region_name=region_name,
    )
