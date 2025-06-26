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

"""Direct PostgreSQL driver implementation using psycopg."""

import asyncio
import json
import boto3
from typing import Dict, List, Optional, Any
from loguru import logger
from botocore.exceptions import ClientError

try:
    import psycopg2
    import psycopg2.extras
    PSYCOPG2_AVAILABLE = True
except ImportError:
    psycopg2 = None
    PSYCOPG2_AVAILABLE = False

from .base_connection import DBConnector


class PostgresDriver(DBConnector):
    """Driver for direct PostgreSQL connections using psycopg."""
    
    def __init__(
        self,
        hostname: str,
        database: str,
        secret_arn: str,
        region_name: str,
        port: int = 5432,
        readonly: bool = True
    ):
        """
        Initialize PostgreSQL driver with lazy connection.
        
        Args:
            hostname: Database hostname
            database: Database name
            secret_arn: ARN of the secret containing credentials
            region_name: AWS region name
            port: Database port
            readonly: Whether connection is read-only
        """
        if not PSYCOPG2_AVAILABLE:
            raise ImportError(
                "psycopg2-binary is required for direct PostgreSQL connections. "
                "Install with: pip install psycopg2-binary or pip install .[postgres]"
            )
            
        self.hostname = hostname
        self.database = database
        self.secret_arn = secret_arn
        self.region_name = region_name
        self.port = port
        self.readonly = readonly
        self._connection = None
        self._credentials = None
        self._credentials_cached = False
        self._connection_validated = False
        
        logger.info(f"PostgreSQL driver initialized (lazy) for {hostname}:{port}/{database}")
        
    def is_connected(self) -> bool:
        """Check if the connection is active."""
        if self._connection is None:
            return False
        try:
            # Test connection with a simple query
            with self._connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            return True
        except (psycopg2.Error, psycopg2.OperationalError):
            return False
    
    async def _get_credentials(self) -> Dict[str, str]:
        """Get database credentials from AWS Secrets Manager with caching."""
        if not self._credentials_cached:
            try:
                sm_client = boto3.client('secretsmanager', region_name=self.region_name)
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
        return self._credentials
    
    async def connect(self) -> bool:
        """
        Establish connection to PostgreSQL database with optimized retry logic.
        
        Returns:
            True if connection successful, False otherwise
        """
        if self.is_connected():
            return True
            
        try:
            logger.info(f"Establishing connection to PostgreSQL: {self.hostname}:{self.port}/{self.database}")
            credentials = await self._get_credentials()
            
            connection_params = {
                'host': self.hostname,
                'port': self.port,
                'database': self.database,
                'user': credentials.get('username'),
                'password': credentials.get('password'),
                'connect_timeout': 10,  # Reduced from 30 to 10 seconds
                'application_name': 'postgres-mcp-server'
            }
            
            self._connection = await asyncio.to_thread(
                psycopg2.connect, **connection_params
            )
            
            # Set autocommit for read-only operations
            if self.readonly:
                self._connection.autocommit = True
            
            self._connection_validated = True
            logger.success(f"Successfully connected to PostgreSQL: {self.hostname}:{self.port}/{self.database}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {str(e)}")
            self._connection = None
            self._connection_validated = False
            return False
    
    async def test_connection_parameters(self) -> bool:
        """
        Test if connection parameters are valid without establishing full connection.
        
        This is used for startup validation.
        
        Returns:
            True if parameters seem valid, False otherwise
        """
        try:
            # Just test if we can retrieve credentials
            await self._get_credentials()
            logger.info(f"Connection parameters validated for {self.hostname}:{self.port}/{self.database}")
            return True
        except Exception as e:
            logger.error(f"Connection parameter validation failed: {str(e)}")
            return False
    
    async def disconnect(self):
        """Disconnect from PostgreSQL database."""
        if self._connection:
            try:
                await asyncio.to_thread(self._connection.close)
                logger.info("Disconnected from PostgreSQL")
            except Exception as e:
                logger.warning(f"Error during disconnect: {str(e)}")
            finally:
                self._connection = None
    
    async def execute_query(
        self,
        query: str,
        parameters: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Execute a query using direct PostgreSQL connection with connection retry.
        
        Args:
            query: SQL query to execute
            parameters: Query parameters (converted from RDS Data API format)
            
        Returns:
            Query result dictionary in RDS Data API format for compatibility
            
        Raises:
            psycopg2.Error: If database operation fails
            Exception: For other errors
        """
        # Ensure connection is established
        if not self.is_connected():
            logger.info("Establishing database connection for query execution...")
            connected = await self.connect()
            if not connected:
                raise Exception("Failed to establish database connection")
        
        try:
            with self._connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                # Convert RDS Data API parameters to psycopg2 format
                pg_params = self._convert_parameters(parameters) if parameters else None
                
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
                    
        except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
            # Connection might be lost, try to reconnect once
            logger.warning(f"Connection error, attempting to reconnect: {str(e)}")
            self._connection = None
            self._connection_validated = False
            
            # Retry once
            connected = await self.connect()
            if connected:
                return await self.execute_query(query, parameters)
            else:
                raise Exception(f"Failed to reconnect to database: {str(e)}")
                
        except psycopg2.Error as e:
            logger.error(f"PostgreSQL query error: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during query execution: {str(e)}")
            raise
    
    def _convert_parameters(self, rds_params: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Convert RDS Data API parameters to psycopg2 format."""
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
    
    def _format_response(self, rows: List[Dict], description) -> Dict[str, Any]:
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
        Perform health check on the connection.
        
        Returns:
            True if connection is healthy, False otherwise
        """
        try:
            await self.execute_query("SELECT 1")
            return True
        except Exception as e:
            logger.warning(f"Health check failed for PostgreSQL: {str(e)}")
            return False
    
    @property
    def connection_info(self) -> Dict[str, Any]:
        """Get connection information."""
        return {
            'type': 'psycopg_driver',
            'hostname': self.hostname,
            'port': self.port,
            'database': self.database,
            'readonly': self.readonly,
            'connected': self.is_connected()
        }
