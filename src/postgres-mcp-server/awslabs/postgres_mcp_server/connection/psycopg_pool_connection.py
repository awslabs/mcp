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

"""Psycopg connector for postgres MCP Server.

This connector provides direct connection to PostgreSQL databases using psycopg.
It supports both Aurora PostgreSQL and RDS PostgreSQL instances via direct connection
parameters (host, port, database, user, password) or via AWS Secrets Manager.
"""

import boto3
import json
from aiorwlock import RWLock
from awslabs.postgres_mcp_server import __user_agent__
from awslabs.postgres_mcp_server.connection.abstract_db_connection import AbstractDBConnection
from botocore.config import Config
from datetime import datetime, timedelta
from loguru import logger
from psycopg_pool import AsyncConnectionPool
from typing import Any, Dict, List, Optional, Tuple


class PsycopgPoolConnection(AbstractDBConnection):
    """Class that wraps DB connection using psycopg connection pool.

    This class can connect directly to any PostgreSQL database, including:
    - Aurora PostgreSQL (using the cluster endpoint)
    - RDS PostgreSQL (using the instance endpoint)
    - Self-hosted PostgreSQL

    It uses AWS Secrets Manager (secret_arn and region) for authentication.
    """

    def __init__(
        self,
        host: str,
        port: int,
        database: str,
        readonly: bool,
        secret_arn: str,
        db_user: str,
        region: str,
        is_iam_auth: bool = False,
        pool_expiry_min: int = 30,
        min_size: int = 1,
        max_size: int = 10,
        is_test: bool = False,
    ):
        """Initialize a new DB connection pool.

        Args:
            host: Database host (Aurora cluster endpoint or RDS instance endpoint)
            port: Database port
            database: Database name
            readonly: Whether connections should be read-only
            secret_arn: ARN of the secret containing credentials
            db_user: Database username
            region: AWS region for Secrets Manager
            is_iam_auth: Whether to use IAM authentication
            pool_expiry_min: Pool expiry time in minutes
            min_size: Minimum number of connections in the pool
            max_size: Maximum number of connections in the pool
            is_test: Whether this is a test connection
        """
        super().__init__(readonly)
        self.host = host
        self.port = port
        self.database = database
        self.min_size = min_size
        self.max_size = max_size
        self.region = region
        self.is_iam_auth = is_iam_auth
        self.user = db_user
        self.pool_expiry_min = pool_expiry_min
        self.secret_arn = secret_arn
        self.is_test = is_test
        self.pool: Optional['AsyncConnectionPool[Any]'] = None
        self.rw_lock = RWLock()
        self.created_time = datetime.now()

        if is_iam_auth:
            # if db_user is set, then it is IAM auth scenario and iam_auth_token must be set
            if not db_user:
                raise ValueError('db_user must be set when is_iam_auth is True')

            # set pool expiry before IAM auth token expiry of 15 minutes
            self.pool_expiry_min = 14
            logger.info(f'Use IAM auth for user: {db_user}')

    async def initialize_pool(self):
        """Initialize the connection pool."""
        async with self.rw_lock.reader_lock:
            if self.pool is not None:
                return

        async with self.rw_lock.writer_lock:
            if self.pool is not None:
                return

            logger.info(
                f'initialize_pool:\n'
                f'endpoint:{self.host}\n'
                f'port:{self.port}\n'
                f'region:{self.region}\n'
                f'db:{self.database}\n'
                f'user:{self.user}\n'
                f'is_iam_auth:{self.is_iam_auth}\n'
            )

            if self.is_iam_auth:
                logger.info(f'Retrieving IAM auth token for {self.user}')
                password = self.get_iam_auth_token()
            else:
                logger.info(f'Retrieving credentials from Secrets Manager: {self.secret_arn}')
                self.user, password = self._get_credentials_from_secret(
                    self.secret_arn, self.region, self.is_test
                )

            self.created_time = datetime.now()
            self.conninfo = f'host={self.host} port={self.port} dbname={self.database} user={self.user} password={password}'
            self.pool = AsyncConnectionPool(
                self.conninfo, min_size=self.min_size, max_size=self.max_size, open=False
            )

            # wait up to 30 seconds to fill the pool with connections
            await self.pool.open(True, 30)
            logger.info('Connection pool initialized successfully')

    async def _get_connection(self):
        """Get a database connection from the pool."""
        await self.check_expiry()

        async with self.rw_lock.reader_lock:
            if self.pool is None:
                raise ValueError('Failed to initialize connection pool')
            return self.pool.connection(timeout=15.0)

    async def check_expiry(self):
        """Check and handle pool expiry."""
        async with self.rw_lock.reader_lock:
            if self.pool and datetime.now() - self.created_time < timedelta(
                minutes=self.pool_expiry_min
            ):
                return

        await self.close()
        await self.initialize_pool()

    async def execute_query(
        self, sql: str, parameters: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Execute a SQL query using async connection."""
        try:
            async with await self._get_connection() as conn:
                async with conn.transaction():
                    if self.readonly_query:
                        logger.info('SET TRANSACTION READ ONLY')
                        await conn.execute('SET TRANSACTION READ ONLY')

                    # Create a cursor for better control
                    async with conn.cursor() as cursor:
                        # Execute the query
                        if parameters:
                            params = self._convert_parameters(parameters)
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
                            column_metadata = [{'name': col} for col in columns]
                            records = []

                            # Convert each row to the expected format
                            for row in rows:
                                record = []
                                for value in row:
                                    if value is None:
                                        record.append({'isNull': True})
                                    elif isinstance(value, str):
                                        record.append({'stringValue': value})
                                    elif isinstance(value, bool):
                                        record.append({'booleanValue': value})
                                    elif isinstance(value, int):
                                        record.append({'longValue': value})
                                    elif isinstance(value, float):
                                        record.append({'doubleValue': value})
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

    def _get_credentials_from_secret(
        self, secret_arn: str, region: str, is_test: bool = False
    ) -> Tuple[str, str]:
        """Get database credentials from AWS Secrets Manager."""
        if is_test:
            return 'test_user', 'test_password'

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

    async def close(self) -> None:
        """Close all connections in the pool."""
        async with self.rw_lock.writer_lock:
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

    async def get_pool_stats(self) -> Dict[str, int]:
        """Get current connection pool statistics."""
        async with self.rw_lock.reader_lock:
            if not hasattr(self, 'pool') or self.pool is None:
                return {'size': 0, 'min_size': self.min_size, 'max_size': self.max_size, 'idle': 0}

            # Access pool attributes safely
            size = getattr(self.pool, 'size', 0)
            min_size = getattr(self.pool, 'min_size', self.min_size)
            max_size = getattr(self.pool, 'max_size', self.max_size)
            idle = getattr(self.pool, 'idle', 0)

            return {'size': size, 'min_size': min_size, 'max_size': max_size, 'idle': idle}

    def get_iam_auth_token(self) -> str:
        """Generate an IAM authentication token for RDS database access."""
        rds_client = boto3.client(
            'rds', region_name=self.region, config=Config(user_agent_extra=__user_agent__)
        )
        return rds_client.generate_db_auth_token(
            DBHostname=self.host, Port=self.port, DBUsername=self.user, Region=self.region
        )
