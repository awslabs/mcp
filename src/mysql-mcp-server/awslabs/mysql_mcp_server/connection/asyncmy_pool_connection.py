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

"""Python connector for MySQL and MariaDB MCP Server.

This connector provides direct connection to MySQL/MariaDB databases using asyncmy.
It supports both Aurora MySQL and RDS Mysql/MariaDB instances via direct connection.
"""

import boto3
import json
from asyncmy import Pool, create_pool
from awslabs.mysql_mcp_server.connection.abstract_db_connection import AbstractDBConnection
from loguru import logger
from typing import Any, Dict, List, Optional, Tuple


class AsyncmyPoolConnection(AbstractDBConnection):
    """Class that wraps DB connection using asyncmy connection pool.

    This class can connect directly to any MySQL and MariaDB database, including:
    - Aurora MySQL (using the cluster endpoint)
    - RDS MySQL and RDS MariaDB (using the instance endpoint)
    - Self-hosted MySQL and MariaDB

    It uses AWS Secrets Manager (secret_arn and region) for authentication.
    """

    def __init__(
        self,
        hostname: str,
        port: int,
        database: str,
        readonly: bool,
        secret_arn: str,
        region: str,
        min_size: int = 1,
        max_size: int = 10,
    ):
        """Initialize a new DB connection pool.

        Args:
            hostname: Database host (Aurora cluster endpoint or RDS instance endpoint)
            port: Database port (default 3306)
            database: Database name
            readonly: Whether connections should be read-only
            secret_arn: ARN of the secret containing credentials
            region: AWS region for Secrets Manager
            min_size: Minimum number of connections in the pool
            max_size: Maximum number of connections in the pool
        """
        super().__init__(readonly)
        self.hostname = hostname
        self.port = port
        self.min_size = min_size
        self.max_size = max_size
        self.pool: Optional[Pool] = None
        self.database = database

        # Get credentials from Secrets Manager
        logger.info(f'Retrieving credentials from Secrets Manager: {secret_arn}')
        self.user, self.password = _get_credentials_from_secret(secret_arn, region)
        logger.info(f'Successfully retrieved credentials for user: {self.user}')

    async def initialize_pool(self):
        """Initialize the connection pool."""
        if self.pool is None:
            logger.info(
                f'Initializing connection pool with min_size={self.min_size}, max_size={self.max_size}'
            )

            self.pool = await create_pool(
                minsize=self.min_size,
                maxsize=self.max_size,
                host=self.hostname,
                port=self.port,
                user=self.user,
                password=self.password,
                db=self.database,
                autocommit=True,
            )

            logger.info('Connection pool initialized successfully')

            if self._readonly:
                await self._set_all_connections_readonly()

    async def _set_all_connections_readonly(self):
        """Set all connections in the pool to read-only mode."""
        if self.pool is None:
            logger.warning('Connection pool is not initialized, cannot set read-only mode')
            return

        try:
            async with self.pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute('SET SESSION TRANSACTION READ ONLY;')
                    logger.info('Successfully set connection to read-only mode')
        except Exception as e:
            logger.warning(f'Failed to set connections to read-only mode: {str(e)}')
            logger.warning('Continuing without setting read-only mode')

    async def _get_connection(self):
        """Get a database connection from the pool."""
        if self.pool is None:
            await self.initialize_pool()

        if self.pool is None:
            raise ValueError('Failed to initialize connection pool')

        return self.pool.acquire()

    async def execute_query(
        self, sql: str, parameters: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Execute a SQL query using async connection."""
        try:
            async with await self._get_connection() as conn:
                async with conn.cursor() as cursor:
                    if self._readonly:
                        await cursor.execute('SET TRANSACTION READ ONLY')
                    # Execute the query
                    if parameters:
                        params = list(_convert_parameters(self, parameters).values())
                        await cursor.execute(sql, params)
                    else:
                        await cursor.execute(sql)

                    # Check if there are results to fetch by examining the cursor's description
                    if cursor.description:
                        # Get column names
                        columns = [desc[0] for desc in cursor.description]

                        # Fetch all rows
                        rows = await cursor.fetchall()

                        # Structure the response to match the interface contract required by server.py
                        column_metadata = [{'label': col} for col in columns]
                        records = []

                        # Convert each row to the expected format
                        for row in rows:
                            record = []
                            for value in row:
                                if value is None:
                                    record.append({'isNull': True})
                                elif isinstance(value, str):
                                    record.append({'stringValue': value})
                                elif isinstance(value, int):
                                    record.append({'longValue': value})
                                elif isinstance(value, float):
                                    record.append({'doubleValue': value})
                                elif isinstance(value, bool):
                                    record.append({'booleanValue': value})
                                elif isinstance(value, bytes):
                                    record.append({'blobValue': value})
                                else:
                                    # Convert other types to string
                                    record.append({'stringValue': str(value)})
                            records.append(record)

                        return {'columnMetadata': column_metadata, 'records': records}
                    else:
                        # No results (e.g., for INSERT, UPDATE, etc.)
                        return {'columnMetadata': [], 'records': []}

        except Exception as e:
            logger.error(f'Database connection error: {str(e)}')
            raise e

    async def close(self) -> None:
        """Close all connections in the pool."""
        if self.pool is not None:
            logger.info('Closing connection pool')
            await self.pool.close()
            self.pool = None
            logger.info('Connection pool closed successfully')

    async def check_connection_health(self) -> bool:
        """Check if the connection is healthy."""
        try:
            result = await self.execute_query('SELECT 1')
            return len(result.get('records', [])) > 0
        except Exception as e:
            logger.error(f'Connection health check failed: {str(e)}')
            return False


def _convert_parameters(self, parameters: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Transform structured parameter format to psycopg's native parameter format."""
    result = {}
    for param in parameters:
        name = param.get('name')
        value = param.get('value', {})

        # Extract the value based on its type
        if 'stringValue' in value:
            result[name] = value['stringValue']
        elif 'longValue' in value:
            result[name] = value['longValue']
        elif 'doubleValue' in value:
            result[name] = value['doubleValue']
        elif 'booleanValue' in value:
            result[name] = value['booleanValue']
        elif 'blobValue' in value:
            result[name] = value['blobValue']
        elif 'isNull' in value and value['isNull']:
            result[name] = None

    return result


def _get_credentials_from_secret(secret_arn: str, region: str) -> Tuple[str, str]:
    """Get database credentials from AWS Secrets Manager."""
    try:
        # Create a Secrets Manager client
        logger.info(f'Creating Secrets Manager client in region {region}')
        session = boto3.Session()
        client = session.client(service_name='secretsmanager', region_name=region)

        # Get the secret value
        logger.info(f'Retrieving secret value for {secret_arn}')
        get_secret_value_response = client.get_secret_value(SecretId=secret_arn)
        logger.info('Successfully retrieved secret value')

        # Parse the secret string
        if 'SecretString' in get_secret_value_response:
            secret = json.loads(get_secret_value_response['SecretString'])
            logger.info(f'Secret keys: {", ".join(secret.keys())}')

            # Extract username and password
            username = secret.get('username') or secret.get('user') or secret.get('Username')
            password = secret.get('password') or secret.get('Password')

            if not username:
                logger.error(
                    f'Username not found in secret. Available keys: {", ".join(secret.keys())}'
                )
                raise ValueError(
                    f'Secret does not contain username. Available keys: {", ".join(secret.keys())}'
                )

            if not password:
                logger.error('Password not found in secret')
                raise ValueError(
                    f'Secret does not contain password. Available keys: {", ".join(secret.keys())}'
                )

            logger.info(f'Successfully extracted credentials for user: {username}')
            return username, password
        else:
            logger.error('Secret does not contain a SecretString')
            raise ValueError('Secret does not contain a SecretString')
    except Exception as e:
        logger.error(f'Error retrieving secret: {str(e)}')
        raise ValueError(f'Failed to retrieve credentials from Secrets Manager: {str(e)}')
