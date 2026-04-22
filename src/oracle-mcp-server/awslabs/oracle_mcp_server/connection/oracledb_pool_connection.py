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

"""oracledb connection pool for oracle MCP Server."""

import boto3
import json
import oracledb
import ssl
from aiorwlock import RWLock
from awslabs.oracle_mcp_server.connection.abstract_db_connection import AbstractDBConnection
from datetime import datetime, timedelta
from loguru import logger
from typing import Any, Dict, List, Optional, Tuple


class OracledbPoolConnection(AbstractDBConnection):
    """Direct connection to Oracle Database using oracledb async connection pool.

    Uses python-oracledb thin mode (no Oracle Instant Client required).
    Supports both service_name and SID connection styles.
    """

    def __init__(
        self,
        host: str,
        port: int,
        database: str,
        readonly: bool,
        secret_arn: str,
        region: str,
        service_name: Optional[str] = None,
        sid: Optional[str] = None,
        pool_expiry_min: int = 30,
        min_size: int = 1,
        max_size: int = 10,
        is_test: bool = False,
        ssl_encryption: str = 'require',
        call_timeout_ms: int = 30000,
    ):
        """Initialize an Oracle connection pool configuration."""
        super().__init__(readonly)
        if service_name and sid:
            raise ValueError('Provide either service_name or sid, not both')
        if not service_name and not sid:
            raise ValueError('Either service_name or sid must be provided')

        self.host = host
        self.port = port
        self.database = database
        self.min_size = min_size
        self.max_size = max_size
        self.region = region
        self.pool_expiry_min = pool_expiry_min
        self.secret_arn = secret_arn
        self.is_test = is_test
        self.service_name = service_name
        self.sid = sid
        self.ssl_encryption = ssl_encryption
        self.call_timeout_ms = call_timeout_ms
        self.pool: Optional[oracledb.AsyncConnectionPool] = None
        self.rw_lock = RWLock()
        self.created_time = datetime.now()

        # Build DSN using Oracle connect descriptor format
        protocol = 'TCPS' if ssl_encryption in ('require', 'noverify') else 'TCP'
        if service_name:
            connect_data = f'(SERVICE_NAME={service_name})'
        else:
            connect_data = f'(SID={sid})'
        self.dsn = (
            f'(DESCRIPTION='
            f'(ADDRESS=(PROTOCOL={protocol})(HOST={host})(PORT={port}))'
            f'(CONNECT_DATA={connect_data}))'
        )

    def _get_ssl_kwargs(self) -> dict:
        """Return SSL-related keyword arguments for oracledb connections."""
        if self.ssl_encryption == 'require':
            ctx = ssl.create_default_context()
            return {
                'ssl_context': ctx,
                'ssl_server_dn_match': True,
            }
        if self.ssl_encryption == 'noverify':
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            return {
                'ssl_context': ctx,
                'ssl_server_dn_match': False,
            }
        return {}

    async def initialize_pool(self):
        """Initialize the Oracle connection pool."""
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
                f'dsn:{self.dsn}\n'
                f'region:{self.region}\n'
                f'db:{self.database}\n'
                f'ssl_encryption:{self.ssl_encryption}\n'
            )

            logger.info(f'Retrieving credentials from Secrets Manager: {self.secret_arn}')
            user, password = self._get_credentials_from_secret(
                self.secret_arn, self.region, self.is_test
            )

            self.created_time = datetime.now()

            try:
                pool_kwargs = {
                    'user': user,
                    'password': password,
                    'dsn': self.dsn,
                    'min': self.min_size,
                    'max': self.max_size,
                    'increment': 1,
                }
                pool_kwargs.update(self._get_ssl_kwargs())
                self.pool = oracledb.create_pool_async(**pool_kwargs)
            except Exception as e:
                logger.error(f'Failed to open Oracle connection pool: {type(e).__name__}')
                self.pool = None
                raise

            logger.info(
                f'Oracle connection pool initialized at {self.created_time.isoformat()}, '
                f'host={self.host}, dsn={self.dsn}, expiry_min={self.pool_expiry_min}'
            )

    async def check_expiry(self):
        """Check and handle pool expiry with retry on reinitialization failure."""
        async with self.rw_lock.reader_lock:
            if self.pool and datetime.now() - self.created_time < timedelta(
                minutes=self.pool_expiry_min
            ):
                return

        age_seconds = (datetime.now() - self.created_time).total_seconds()
        logger.warning(
            f'check_expiry: pool expired or None. '
            f'age={age_seconds:.1f}s, expiry={self.pool_expiry_min * 60}s, '
            f'host={self.host}, dsn={self.dsn}'
        )
        await self.close()

        last_error = None
        for attempt in range(3):
            try:
                await self.initialize_pool()
                return
            except Exception as e:
                last_error = e
                logger.warning(f'Pool reinitialization attempt {attempt + 1}/3 failed: {e}')
        raise ValueError(f'Failed to reinitialize pool after 3 attempts: {last_error}')

    async def execute_query(
        self, sql: str, parameters: Optional[List[Dict[str, Any]]] = None, max_rows: int = 0
    ) -> List[Dict[str, Any]]:
        """Execute a SQL query using async Oracle connection.

        Returns a list of row dicts mapping column names to native Python values.
        """
        try:
            await self.check_expiry()

            async with self.rw_lock.reader_lock:
                if self.pool is None:
                    raise ValueError('Failed to initialize connection pool')

            async with self.pool.acquire() as conn:
                conn.call_timeout = self.call_timeout_ms
                if self.readonly_query:
                    logger.info('SET TRANSACTION READ ONLY')
                    await conn.execute('SET TRANSACTION READ ONLY')

                async with conn.cursor() as cursor:
                    if parameters:
                        named_params = self._convert_parameters(parameters)
                        await cursor.execute(sql, named_params)
                    else:
                        await cursor.execute(sql)

                    if cursor.description:
                        columns = [desc[0] for desc in cursor.description]
                        if max_rows > 0:
                            rows = await cursor.fetchmany(max_rows + 1)
                        else:
                            rows = await cursor.fetchall()

                        if self.readonly_query:
                            await conn.rollback()

                        results = []
                        for row in rows:
                            record = {}
                            for col, value in zip(columns, row):
                                if value is None:
                                    record[col] = None
                                elif isinstance(value, (str, bool, int, float, bytes)):
                                    record[col] = value
                                else:
                                    record[col] = str(value)
                            results.append(record)

                        return results
                    else:
                        if self.readonly_query:
                            await conn.rollback()
                        else:
                            await conn.commit()
                        return []

        except Exception as e:
            logger.exception(f'Database connection error: {str(e)}')
            raise

    def _convert_parameters(self, parameters: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Transform structured parameter format to oracledb named parameter dict."""
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
            return 'test_user', 'test_password'  # pragma: allowlist secret

        try:
            logger.info(f'Creating Secrets Manager client in region {region}')
            session = boto3.Session()
            client = session.client(service_name='secretsmanager', region_name=region)
            logger.info(f'Retrieving secret value for {secret_arn}')
            get_secret_value_response = client.get_secret_value(SecretId=secret_arn)
            logger.info('Successfully retrieved secret value')

            if 'SecretString' in get_secret_value_response:
                secret = json.loads(get_secret_value_response['SecretString'])
                logger.debug(f'Secret keys: {", ".join(secret.keys())}')
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
                logger.debug(f'Successfully extracted credentials for user: {username}')
                return username, password
            else:
                raise ValueError('Secret does not contain a SecretString')
        except Exception as e:
            logger.exception(f'Failed to retrieve credentials from Secrets Manager: {str(e)}')
            raise ValueError(f'Failed to retrieve credentials from Secrets Manager: {str(e)}')

    def validate_sync(self) -> None:
        """Validate the Oracle connection synchronously using a one-shot oracledb.connect().

        This avoids asyncio.run(), which would bind the pool's RWLock to a temporary
        event loop that gets closed before mcp.run() starts its own loop.
        """
        user, password = self._get_credentials_from_secret(
            self.secret_arn, self.region, self.is_test
        )
        connect_kwargs = {'user': user, 'password': password, 'dsn': self.dsn}
        connect_kwargs.update(self._get_ssl_kwargs())

        with oracledb.connect(**connect_kwargs) as conn:
            with conn.cursor() as cursor:
                cursor.execute('SELECT 1 FROM DUAL')
                cursor.fetchone()

    async def close(self) -> None:
        """Close the Oracle connection pool."""
        async with self.rw_lock.writer_lock:
            if self.pool is not None:
                logger.info(f'Closing Oracle connection pool at {datetime.now().isoformat()}')
                await self.pool.close()
                self.pool = None
                logger.info('Oracle connection pool closed successfully')

    async def check_connection_health(self) -> bool:
        """Check if the Oracle connection is healthy using SELECT 1 FROM DUAL."""
        try:
            result = await self.execute_query('SELECT 1 FROM DUAL')
            return len(result) > 0
        except Exception as e:
            logger.exception(f'Connection health check failed: {str(e)}')
            return False
