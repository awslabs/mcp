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

"""pymssql connection pool for mssql MCP Server."""

import asyncio
import boto3
import json
from aiorwlock import RWLock
from awslabs.mssql_mcp_server.connection.abstract_db_connection import AbstractDBConnection
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from loguru import logger
from typing import Any, Dict, List, Optional, Tuple, Union


class PymssqlPoolConnection(AbstractDBConnection):
    """Direct connection to SQL Server using pymssql connection pool."""

    def __init__(
        self,
        host: str,
        port: int,
        database: str,
        readonly: bool,
        secret_arn: str,
        region: str,
        pool_expiry_min: int = 30,
        min_size: int = 1,
        max_size: int = 10,
        is_test: bool = False,
        encryption: str = 'require',
    ):
        """Initialize the pymssql connection pool."""
        super().__init__(readonly)
        self.host = host
        self.port = port
        self.database = database
        self.min_size = min_size
        self.max_size = max_size
        self.region = region
        self.pool_expiry_min = pool_expiry_min
        self.secret_arn = secret_arn
        self.is_test = is_test
        self.encryption = encryption
        self.user: str = ''
        self._pool: Optional[asyncio.Queue] = None
        self.rw_lock = RWLock()
        self.created_time = datetime.now()

    async def initialize_pool(self):
        """Initialize the connection pool."""
        async with self.rw_lock.reader_lock:
            if self._pool is not None:
                return

        async with self.rw_lock.writer_lock:
            if self._pool is not None:
                return

            logger.info(
                f'initialize_pool:\n'
                f'endpoint:{self.host}\n'
                f'port:{self.port}\n'
                f'region:{self.region}\n'
                f'db:{self.database}\n'
            )

            logger.info(f'Retrieving credentials from Secrets Manager: {self.secret_arn}')
            self.user, password = self._get_credentials_from_secret(
                self.secret_arn, self.region, self.is_test
            )

            self.created_time = datetime.now()

            # Create queue with capacity for max_size connections
            self._pool = asyncio.Queue(maxsize=self.max_size)

            # Pre-fill with min_size connections
            errors = []
            for _ in range(self.min_size):
                try:
                    conn = await asyncio.to_thread(
                        self._create_raw_connection, self.user, password
                    )
                    await self._pool.put(conn)
                except Exception as e:
                    errors.append(e)

            if errors and self._pool.empty():
                self._pool = None
                raise errors[0]

            logger.info(
                f'Connection pool initialized at {self.created_time.isoformat()}, '
                f'host={self.host}, db={self.database}, '
                f'expiry_min={self.pool_expiry_min}, size={self._pool.qsize()}'
            )

    def _create_raw_connection(self, user: str, password: str):
        """Create a single pymssql connection (synchronous)."""
        import pymssql

        return pymssql.connect(
            server=self.host,
            port=str(self.port),
            user=user,
            password=password,
            database=self.database,
            encryption=self.encryption,
            autocommit=not self.readonly_query,
            login_timeout=15,
            timeout=30,
        )

    @asynccontextmanager
    async def _get_connection(self):
        """Async context manager that yields an exclusive pymssql connection from pool."""
        await self.check_expiry()

        async with self.rw_lock.reader_lock:
            if self._pool is None:
                raise ValueError('Failed to initialize connection pool')

        conn = await asyncio.wait_for(self._pool.get(), timeout=15.0)
        try:
            yield conn
            # Return healthy connection to pool
            await self._pool.put(conn)
        except Exception:
            # Connection may be broken; try to replace it
            try:
                await asyncio.to_thread(conn.close)
            except Exception:
                pass
            try:
                fresh_user, fresh_password = await asyncio.to_thread(
                    self._get_credentials_from_secret, self.secret_arn, self.region, self.is_test
                )
                self.user = fresh_user
                new_conn = await asyncio.to_thread(
                    self._create_raw_connection, fresh_user, fresh_password
                )
                await self._pool.put(new_conn)
            except Exception as replace_err:
                logger.warning(f'Failed to replace broken connection: {replace_err}')
            raise

    async def check_expiry(self):
        """Check and handle pool expiry."""
        async with self.rw_lock.reader_lock:
            if self._pool and datetime.now() - self.created_time < timedelta(
                minutes=self.pool_expiry_min
            ):
                return

        age_seconds = (datetime.now() - self.created_time).total_seconds()
        logger.warning(
            f'check_expiry: pool expired or None. '
            f'age={age_seconds:.1f}s, expiry={self.pool_expiry_min * 60}s, '
            f'host={self.host}, db={self.database}'
        )
        await self.close()
        await self.initialize_pool()

    async def execute_query(
        self, sql: str, parameters: Optional[Union[List[Dict[str, Any]], Tuple]] = None
    ) -> Dict[str, Any]:
        """Execute a SQL query using pymssql via asyncio.to_thread."""
        try:
            async with self._get_connection() as conn:

                def _run_sync():
                    cursor = conn.cursor()
                    if self.readonly_query:
                        cursor.execute('SET TRANSACTION ISOLATION LEVEL READ COMMITTED')
                    if parameters:
                        if isinstance(parameters, tuple):
                            cursor.execute(sql, parameters)
                        else:
                            positional_params = list(self._convert_parameters(parameters).values())
                            cursor.execute(sql, positional_params)
                    else:
                        cursor.execute(sql)

                    description = cursor.description
                    rows = cursor.fetchall() if description else []
                    # End any implicit read transaction to keep connection clean.
                    # Skip in write mode: autocommit=True means no open transaction exists
                    # and calling rollback() causes SQL Server error 3902.
                    if self.readonly_query:
                        conn.rollback()
                    return description, rows

                description, rows = await asyncio.to_thread(_run_sync)

                if description:
                    columns = [desc[0] for desc in description]
                    column_metadata = [{'name': col} for col in columns]
                    records = []
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
                                record.append({'stringValue': str(value)})
                        records.append(record)
                    return {'columnMetadata': column_metadata, 'records': records}
                else:
                    return {'columnMetadata': [], 'records': []}

        except Exception as e:
            logger.exception(f'Database connection error: {str(e)}')
            raise

    def _convert_parameters(self, parameters: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Transform structured parameter format to ordered dict for positional binding."""
        result = {}
        for param in parameters:
            name = param.get('name')
            value = param.get('value', {})
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
            logger.info(f'Creating Secrets Manager client in region {region}')
            session = boto3.Session()
            client = session.client(service_name='secretsmanager', region_name=region)
            logger.info(f'Retrieving secret value for {secret_arn}')
            get_secret_value_response = client.get_secret_value(SecretId=secret_arn)
            logger.info('Successfully retrieved secret value')

            if 'SecretString' in get_secret_value_response:
                secret = json.loads(get_secret_value_response['SecretString'])
                logger.info(f'Secret keys: {", ".join(secret.keys())}')
                username = secret.get('username') or secret.get('user') or secret.get('Username')
                password = secret.get('password') or secret.get('Password')
                if not username:
                    raise ValueError(
                        f'Secret does not contain username. Available keys: {", ".join(secret.keys())}'
                    )
                if not password:
                    raise ValueError(
                        f'Secret does not contain password. Available keys: {", ".join(secret.keys())}'
                    )
                logger.info(f'Successfully extracted credentials for user: {username}')
                return username, password
            else:
                raise ValueError('Secret does not contain a SecretString')
        except Exception as e:
            logger.exception(f'Failed to retrieve credentials from Secrets Manager: {str(e)}')
            raise ValueError(f'Failed to retrieve credentials from Secrets Manager: {str(e)}')

    async def close(self) -> None:
        """Close all connections in the pool."""
        async with self.rw_lock.writer_lock:
            if self._pool is not None:
                logger.info(f'Closing connection pool at {datetime.now().isoformat()}')
                while not self._pool.empty():
                    try:
                        conn = self._pool.get_nowait()
                        await asyncio.to_thread(conn.close)
                    except Exception as e:
                        logger.warning(f'Error closing connection: {e}')
                self._pool = None
                logger.info('Connection pool closed successfully')

    async def check_connection_health(self) -> bool:
        """Check if the connection is healthy."""
        try:
            result = await self.execute_query('SELECT 1')
            return len(result.get('records', [])) > 0
        except Exception as e:
            logger.exception(f'Connection health check failed: {str(e)}')
            return False
