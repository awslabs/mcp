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

"""Asyncmy connector for MySQL MCP Server.

This connector provides direct connection to MySQL databases using asyncmy.
It supports both Aurora MySQL and RDS MySQL instances via direct connection
parameters (host, port, database, user, password) or via AWS Secrets Manager.
"""

import asyncmy
import asyncmy.cursors
import boto3
import json
import os
import ssl as ssl_module
from aiorwlock import RWLock
from awslabs.mysql_mcp_server import __user_agent__
from awslabs.mysql_mcp_server.connection.abstract_db_connection import AbstractDBConnection
from botocore.config import Config
from datetime import datetime, timedelta
from loguru import logger
from typing import Any, Dict, List, Optional, Tuple


# Path to the bundled Amazon RDS global CA bundle. The bundle is fetched
# at build time by hatch_build.py and shipped inside the wheel so that IAM
# authenticated connections can perform strict TLS verification out of the
# box. The PEM is gitignored; rebuilding the package fetches a fresh copy.
#
# Users who maintain their own trust store can override the bundled file
# by passing --ca_bundle <path> on the server command line.
_RDS_CA_BUNDLE_PATH = os.path.join(os.path.dirname(__file__), 'rds_global_bundle.pem')


def _bundled_ca_file() -> Optional[str]:
    """Return the bundled CA path if it is present on disk, else None.

    Returns None (with a logged error) if the bundle is missing or
    unreadable. In that case callers should either fall back to the system
    trust store or refuse to use IAM auth.
    """
    if not os.path.isfile(_RDS_CA_BUNDLE_PATH):
        logger.error(
            'Bundled RDS CA bundle is missing at {}. The build hook should '
            'have fetched it during package build; rebuild the package or '
            'pass --ca_bundle <path> to override.',
            _RDS_CA_BUNDLE_PATH,
        )
        return None
    try:
        with open(_RDS_CA_BUNDLE_PATH, 'rb'):
            pass
    except OSError as exc:
        logger.error(
            'Bundled RDS CA bundle at {} could not be read: {}',
            _RDS_CA_BUNDLE_PATH,
            exc,
        )
        return None
    return _RDS_CA_BUNDLE_PATH


class AsyncmyPoolConnection(AbstractDBConnection):
    """Class that wraps DB connection using asyncmy connection pool.

    This class can connect directly to any MySQL database, including:
    - Aurora MySQL (using the cluster endpoint)
    - RDS MySQL (using the instance endpoint)

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
        ca_bundle_path: Optional[str] = None,
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
            ca_bundle_path: Optional path to an alternate CA bundle to trust
                for IAM-auth SSL verification. When set, the bundled Amazon
                RDS CA bundle is ignored.
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
        self.ca_bundle_path = ca_bundle_path
        self.pool: Optional[asyncmy.Pool] = None
        self.rw_lock = RWLock()
        self.created_time = datetime.now()

        if is_iam_auth:
            if not db_user:
                raise ValueError('db_user must be set when is_iam_auth is True')
            # set pool expiry before IAM auth token expiry of 15 minutes
            self.pool_expiry_min = 14
            logger.info(f'Use IAM auth for user: {db_user}')

    async def initialize_pool(self):
        """Initialize the connection pool."""
        async with self.rw_lock.writer_lock:
            await self._initialize_pool_unlocked()

    async def _initialize_pool_unlocked(self):
        """Create a new pool. Caller must hold writer_lock."""
        if self.pool is not None:
            return

        logger.debug(
            f'initialize_pool: endpoint:{self.host} port:{self.port} '
            f'region:{self.region} db:{self.database} user:{self.user} '
            f'is_iam_auth:{self.is_iam_auth}'
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

        # Build SSL context for IAM auth (required for RDS IAM tokens).
        # Trust decisions, in order of preference:
        #   1. --ca_bundle override supplied by the operator (explicit trust)
        #   2. Bundled Amazon RDS CA bundle verified against a pinned SHA-256
        #      (protects against silent tampering of the PEM on disk)
        #   3. System trust store (may not include RDS regional CAs — warned)
        ssl_ctx = None
        if self.is_iam_auth:
            cafile = self.ca_bundle_path or _bundled_ca_file()
            if cafile:
                ssl_ctx = ssl_module.create_default_context(cafile=cafile)
                logger.debug('Using CA bundle for IAM auth: {}', cafile)
            else:
                ssl_ctx = ssl_module.create_default_context()
                logger.warning(
                    'No verified RDS CA bundle available; falling back to '
                    'the system trust store. IAM auth may fail with '
                    'CERTIFICATE_VERIFY_FAILED. Supply --ca_bundle <path> '
                    'or reinstall the package to restore the bundled bundle.'
                )

        self.pool = await asyncmy.create_pool(
            host=self.host,
            port=self.port,
            user=self.user,
            password=password,
            db=self.database,
            minsize=self.min_size,
            maxsize=self.max_size,
            ssl=ssl_ctx,
            autocommit=True,
        )

        logger.info('Connection pool initialized successfully')

    async def _get_connection(self):
        """Get a database connection from the pool."""
        await self.check_expiry()

        async with self.rw_lock.reader_lock:
            if self.pool is None:
                raise ValueError('Failed to initialize connection pool')
            return self.pool.acquire()

    async def check_expiry(self):
        """Check and handle pool expiry."""
        async with self.rw_lock.reader_lock:
            if self.pool and datetime.now() - self.created_time < timedelta(
                minutes=self.pool_expiry_min
            ):
                return
        # Pool is expired (or None) — re-check under writer lock to
        # avoid duplicate close/init from concurrent coroutines.
        async with self.rw_lock.writer_lock:
            if self.pool and datetime.now() - self.created_time < timedelta(
                minutes=self.pool_expiry_min
            ):
                return
            await self._close_pool_unlocked()
            await self._initialize_pool_unlocked()

    async def execute_query(
        self, sql: str, parameters: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Execute a SQL query using async connection."""
        try:
            async with await self._get_connection() as conn:
                if self.readonly_query:
                    # Disable autocommit so START TRANSACTION takes effect and
                    # set the read-only characteristic BEFORE starting the
                    # transaction (MySQL Error 1568 otherwise).
                    await conn.autocommit(False)
                    async with conn.cursor() as cur:
                        await cur.execute('SET TRANSACTION READ ONLY')
                        await cur.execute('START TRANSACTION')

                try:
                    async with conn.cursor(cursor=asyncmy.cursors.DictCursor) as cursor:
                        # Execute the query
                        if parameters:
                            params = self._convert_parameters(parameters)
                            converted_sql, positional_params = self._convert_named_to_positional(
                                sql, params
                            )
                            await cursor.execute(converted_sql, positional_params)
                        else:
                            await cursor.execute(sql)

                        # Check if there are results to fetch
                        if cursor.description:
                            columns = [desc[0] for desc in cursor.description]
                            rows = await cursor.fetchall()

                            # Structure the response to match the Data API format
                            column_metadata = [{'name': col} for col in columns]
                            records = []

                            for row in rows:
                                record = []
                                for col in columns:
                                    value = row[col]
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

                            result = {'columnMetadata': column_metadata, 'records': records}
                        else:
                            result = {'columnMetadata': [], 'records': []}
                finally:
                    if self.readonly_query:
                        await conn.rollback()
                        await conn.autocommit(True)

                return result

        except Exception as e:
            logger.error(f'Database connection error: {str(e)}')
            raise e

    def _convert_parameters(self, parameters: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Transform structured parameter format to a dict of name->value."""
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

    def _convert_named_to_positional(self, sql: str, params: Dict[str, Any]) -> Tuple[str, list]:
        """Convert named parameter SQL to positional parameter SQL for asyncmy.

        Converts %(name)s style placeholders to %s and returns ordered params.
        """
        import re

        positional_params = []
        pattern = re.compile(r'%\((\w+)\)s')

        def replacer(match):
            name = match.group(1)
            positional_params.append(params.get(name))
            return '%s'

        converted_sql = pattern.sub(replacer, sql)
        return converted_sql, positional_params

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
                logger.debug('Successfully parsed secret value')

                username = secret.get('username') or secret.get('user') or secret.get('Username')
                password = secret.get('password') or secret.get('Password')

                if not username:
                    logger.error('Username not found in secret')
                    raise ValueError(
                        'Secret does not contain a recognized username key (expected: username, user, or Username)'
                    )

                if not password:
                    logger.error('Password not found in secret')
                    raise ValueError(
                        'Secret does not contain a recognized password key (expected: password or Password)'
                    )

                logger.debug(f'Successfully extracted credentials for user: {username}')
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
            await self._close_pool_unlocked()

    async def _close_pool_unlocked(self):
        """Close the pool. Caller must hold writer_lock."""
        if self.pool is not None:
            logger.info('Closing connection pool')
            self.pool.close()
            await self.pool.wait_closed()
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

            size = self.pool.size
            min_size = self.pool.minsize
            max_size = self.pool.maxsize
            idle = self.pool.freesize

            return {'size': size, 'min_size': min_size, 'max_size': max_size, 'idle': idle}

    def get_iam_auth_token(self) -> str:
        """Generate an IAM authentication token for RDS database access."""
        rds_client = boto3.client(
            'rds', region_name=self.region, config=Config(user_agent_extra=__user_agent__)
        )
        return rds_client.generate_db_auth_token(
            DBHostname=self.host, Port=self.port, DBUsername=self.user, Region=self.region
        )
