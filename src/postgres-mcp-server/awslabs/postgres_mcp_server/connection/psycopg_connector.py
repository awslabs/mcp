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

"""PostgreSQL connector implementation using psycopg3 connection pool."""

import asyncio
import boto3
import json
import os
from botocore.exceptions import ClientError
from loguru import logger
from typing import Any, Dict, List, Optional


class Boto3ClientSingleton:
    """Singleton class for boto3 clients to ensure HTTP keep-alive connections."""
    
    _instances = {}
    
    @classmethod
    def get_client(cls, service_name: str, region_name: str) -> Any:
        """
        Get or create a boto3 client instance.
        
        Args:
            service_name: AWS service name
            region_name: AWS region name
            
        Returns:
            Boto3 client instance
        """
        key = f"{service_name}:{region_name}"
        if key not in cls._instances:
            logger.info(f"Creating new boto3 client for {service_name} in {region_name}")
            cls._instances[key] = boto3.client(service_name, region_name=region_name)
        return cls._instances[key]


try:
    import psycopg
    from psycopg_pool import ConnectionPool
    PSYCOPG3_AVAILABLE = True
except ImportError:
    psycopg = None  # type: ignore[assignment]
    ConnectionPool = None  # type: ignore[assignment]
    NullConnectionPool = None  # type: ignore[assignment]
    PSYCOPG3_AVAILABLE = False

from .base_connection import DBConnector


class PsycopgConnector(DBConnector):
    """Connector for PostgreSQL using psycopg3 connection pool."""

    def __init__(
        self,
        hostname: str,
        database: str,
        secret_arn: str,
        region_name: str,
        port: int = 5432,
        readonly: bool = True,
        min_size: Optional[int] = None,
        max_size: Optional[int] = None,
        timeout: float = 30.0
    ):
        """
        Initialize PostgreSQL connector with psycopg3 connection pool.

        Args:
            hostname: Database hostname
            database: Database name
            secret_arn: ARN of the secret containing credentials
            region_name: AWS region name
            port: Database port
            readonly: Whether connection is read-only
            min_size: Minimum pool size (default from env var POSTGRES_POOL_MIN_SIZE or 4)
            max_size: Maximum pool size (default from env var POSTGRES_POOL_MAX_SIZE or 30)
            timeout: Connection timeout in seconds
        """
        if not PSYCOPG3_AVAILABLE:
            raise ImportError(
                "psycopg and psycopg_pool are required for PostgreSQL connections with connection pool. "
                "Install with: pip install 'psycopg>=3.3.0.dev1' 'psycopg_pool>=3.2.0' "
                "or pip install .[postgres]"
            )

        self.hostname = hostname
        self.database = database
        self.secret_arn = secret_arn
        self.region_name = region_name
        self.port = port
        self.readonly = readonly
        
        # Get pool configuration from environment variables or use defaults
        self.min_size = min_size if min_size is not None else int(os.getenv('POSTGRES_POOL_MIN_SIZE', '4'))
        self.max_size = max_size if max_size is not None else int(os.getenv('POSTGRES_POOL_MAX_SIZE', '30'))
        self.timeout = timeout
        
        self._pool = None
        self._credentials = None
        self._credentials_cached = False
        
        logger.info(f"PostgreSQL connector initialized for {hostname}:{port}/{database} "
                   f"with pool size {self.min_size}-{self.max_size}")

    async def _get_credentials(self) -> Dict[str, str]:
        """Get database credentials from AWS Secrets Manager with caching."""
        if not self._credentials_cached:
            try:
                sm_client = Boto3ClientSingleton.get_client('secretsmanager', self.region_name)
                response = await asyncio.to_thread(
                    sm_client.get_secret_value,
                    SecretId=self.secret_arn
                )
                self._credentials = json.loads(response['SecretString'])
                self._credentials_cached = True
                logger.info("Successfully retrieved and cached credentials from Secrets Manager")
            except ClientError as e:
                logger.error(f"Failed to retrieve credentials: {str(e)}")
                raise
        return self._credentials or {}
        
    async def _ensure_pool(self):
        """Ensure the connection pool is initialized."""
        if self._pool is not None:
            return
            
        try:
            logger.info(f"Initializing connection pool to PostgreSQL: {self.hostname}:{self.port}/{self.database}")
            credentials = await self._get_credentials()

            # Build connection string
            conninfo = (
                f"host={self.hostname} "
                f"port={self.port} "
                f"dbname={self.database} "
                f"user={credentials.get('username')} "
                f"password={credentials.get('password')} "
                f"connect_timeout=10 "
                f"application_name=postgres-mcp-server"
            )

            # Configure connection pool
            pool_kwargs = {
                'conninfo': conninfo,
                'min_size': self.min_size,
                'max_size': self.max_size,
                'timeout': self.timeout
            }

            # Create the connection pool
            self._pool = await asyncio.to_thread(
                ConnectionPool, **pool_kwargs
            )
            
            logger.success(f"Successfully initialized connection pool to PostgreSQL: {self.hostname}:{self.port}/{self.database}")
        except Exception as e:
            logger.error(f"Failed to initialize connection pool: {str(e)}")
            self._pool = None
            raise

    async def execute_query(
        self,
        query: str,
        parameters: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Execute a query using psycopg3 connection pool.

        Args:
            query: SQL query to execute
            parameters: Query parameters (converted from RDS Data API format)

        Returns:
            Query result dictionary in RDS Data API format for compatibility

        Raises:
            psycopg.Error: If database operation fails
            Exception: For other errors
        """
        # Ensure pool is initialized
        await self._ensure_pool()

        try:
            # Get connection from pool
            conn = await asyncio.to_thread(self._pool.getconn)
            
            try:
                # Convert RDS Data API parameters to psycopg format
                pg_params = self._convert_parameters(parameters) if parameters else None

                # Set read-only mode if needed
                if self.readonly:
                    await asyncio.to_thread(
                        lambda: conn.execute("SET TRANSACTION READ ONLY")
                    )

                # Execute query
                with conn.cursor(row_factory=psycopg.rows.dict_row) as cursor:
                    await asyncio.to_thread(cursor.execute, query, pg_params)

                    # Fetch results if it's a SELECT query
                    if cursor.description:
                        rows = await asyncio.to_thread(cursor.fetchall)
                        return self._format_response(rows, cursor.description)
                    else:
                        # For non-SELECT queries, return affected row count
                        return {
                            'numberOfRecordsUpdated': cursor.rowcount,
                            'records': [],
                            'columnMetadata': []
                        }
            finally:
                # Return connection to pool
                await asyncio.to_thread(self._pool.putconn, conn)

        except Exception as e:
            # Handle connection errors
            if PSYCOPG3_AVAILABLE and psycopg and isinstance(e, (psycopg.OperationalError, psycopg.InterfaceError)):
                # Connection might be lost, try to reconnect once
                logger.warning(f"Connection error, attempting to reconnect: {str(e)}")
                self._pool = None
                
                # Retry once
                await self._ensure_pool()
                return await self.execute_query(query, parameters)
            elif PSYCOPG3_AVAILABLE and psycopg and isinstance(e, psycopg.Error):
                logger.error(f"PostgreSQL query error: {str(e)}")
                raise
            else:
                # General exception handling
                logger.error(f"Unexpected error during query execution: {str(e)}")
                raise

    def _convert_parameters(self, rds_params: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Convert RDS Data API parameters to psycopg format."""
        pg_params = {}
        for param in rds_params:
            name = param.get('name')
            value_dict = param.get('value', {})

            # Extract value based on type
            if 'stringValue' in value_dict:
                pg_params[name] = value_dict['stringValue']
            elif 'longValue' in value_dict:
                pg_params[name] = value_dict['longValue']
            elif 'doubleValue' in value_dict:
                pg_params[name] = value_dict['doubleValue']
            elif 'booleanValue' in value_dict:
                pg_params[name] = value_dict['booleanValue']
            elif 'isNull' in value_dict and value_dict['isNull']:
                pg_params[name] = None
            else:
                pg_params[name] = str(value_dict)

        return pg_params

    def _format_response(self, rows: List[Dict[str, Any]], description) -> Dict[str, Any]:
        """Format PostgreSQL response to match RDS Data API format."""
        # Create column metadata
        column_metadata = []
        for desc in description:
            column_metadata.append({
                'name': desc.name,
                'type': desc.type_code,
                'typeName': self._get_type_name(desc.type_code)
            })

        # Convert rows to RDS Data API format
        records = []
        for row in rows:
            record = []
            for col_name in [desc.name for desc in description]:
                value = row[col_name]
                record.append(self._format_cell_value(value))
            records.append(record)

        return {
            'records': records,
            'columnMetadata': column_metadata,
            'numberOfRecordsUpdated': 0
        }

    def _format_cell_value(self, value: Any) -> Dict[str, Any]:
        """Format a cell value to RDS Data API format."""
        if value is None:
            return {'isNull': True}
        elif isinstance(value, str):
            return {'stringValue': value}
        elif isinstance(value, int):
            return {'longValue': value}
        elif isinstance(value, float):
            return {'doubleValue': value}
        elif isinstance(value, bool):
            return {'booleanValue': value}
        else:
            return {'stringValue': str(value)}

    def _get_type_name(self, type_code: int) -> str:
        """Get PostgreSQL type name from type code."""
        # Basic type mapping - can be extended
        type_mapping = {
            23: 'INTEGER',
            25: 'TEXT',
            1043: 'VARCHAR',
            16: 'BOOLEAN',
            701: 'FLOAT8',
            1114: 'TIMESTAMP'
        }
        return type_mapping.get(type_code, 'UNKNOWN')

    async def health_check(self) -> bool:
        """
        Perform health check on the connection pool.

        Returns:
            True if connection is healthy, False otherwise
        """
        try:
            # Ensure pool is initialized
            await self._ensure_pool()
            return True
        except Exception as e:
            logger.warning(f"Health check failed for PostgreSQL: {str(e)}")
            return False


    @property
    def connection_info(self) -> Dict[str, Any]:
        """Get connection information."""
        pool_stats = {}
        if self._pool:
            try:
                stats = self._pool.get_stats()
                pool_stats = {
                    'pool_size': stats.get('pool_size', 0),
                    'available': stats.get('available', 0),
                    'requests': stats.get('requests', 0),
                    'requests_waiting': stats.get('requests_waiting', 0)
                }
            except Exception:
                pass
                
        return {
            'type': 'psycopg_pool',
            'hostname': self.hostname,
            'port': self.port,
            'database': self.database,
            'readonly': self.readonly,
            'min_size': self.min_size,
            'max_size': self.max_size,
            'pool_stats': pool_stats
        }
