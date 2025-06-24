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


def validate_read_only_query(query: str) -> bool:
    """Validate that the query is read-only.

    Args:
        query: The SQL query to validate

    Returns:
        bool: True if the query is read-only, False otherwise

    Raises:
        ValueError: If the query contains write operations
    """

    def contains_write_operation(sql: str) -> bool:
        """Check if SQL contains write operations using sqlparse.

        Args:
            sql: The SQL query to check

        Returns:
            bool: True if the query contains write operations, False otherwise
        """
        parsed = sqlparse.parse(sql)
        write_keywords = {
            'INSERT',
            'UPDATE',
            'DELETE',
            'CREATE',
            'ALTER',
            'DROP',
            'TRUNCATE',
            'MERGE',
            'REPLACE',
            'VACUUM',
            'LOAD',
            'COPY',
            'WRITE',
            'UPSERT',
        }

        for stmt in parsed:
            tokens = [token.value.upper() for token in stmt.tokens if not token.is_whitespace]
            if any(token in write_keywords for token in tokens):
                return True
        return False

    if contains_write_operation(query):
        raise ValueError('Write operations are not allowed in read-only queries')

    return True


def _execute_database_query(
    table_bucket_arn: str,
    namespace: str,
    query: str,
    output_location: Optional[str] = None,
    workgroup: str = 'primary',
    validate_read_only: bool = True,
    region_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Internal helper function to execute database queries.

    Args:
        table_bucket_arn: The ARN of the table bucket containing the table
        namespace: The namespace containing the table
        query: Custom SQL query
        output_location: Optional S3 location for query results
        workgroup: Athena workgroup to use for query execution
        validate_read_only: Whether to validate that the query is read-only
        region_name: Optional AWS region name. If not provided, uses AWS_REGION environment variable

    Returns:
        Dict containing query results and metadata

    Raises:
        ValueError: If AWS_REGION is not set or query contains write operations
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

    # Validate that the query is read-only if required
    if validate_read_only:
        validate_read_only_query(query)

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


async def query_database_resource(
    table_bucket_arn: str,
    namespace: str,
    query: str,
    output_location: Optional[str] = None,
    workgroup: str = 'primary',
    region_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Execute a read-only query against a database using Athena.

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
        ValueError: If AWS_REGION is not set or query contains write operations
        ConnectionError: If connection to Athena fails
    """
    return _execute_database_query(
        table_bucket_arn=table_bucket_arn,
        namespace=namespace,
        query=query,
        output_location=output_location,
        workgroup=workgroup,
        validate_read_only=True,
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
    """Execute a query against a database using Athena, allowing write operations.

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
    return _execute_database_query(
        table_bucket_arn=table_bucket_arn,
        namespace=namespace,
        query=query,
        output_location=output_location,
        workgroup=workgroup,
        validate_read_only=False,
        region_name=region_name,
    )
