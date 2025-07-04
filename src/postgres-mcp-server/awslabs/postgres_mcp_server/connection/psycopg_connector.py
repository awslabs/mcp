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

import asyncio
import boto3
import json
from loguru import logger
from typing import Any, Dict, List, Optional, Tuple, Union, TYPE_CHECKING

if TYPE_CHECKING:
    from psycopg_pool import AsyncConnectionPool

from awslabs.postgres_mcp_server.connection.abstract_class import AbstractDBConnection


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
        region: str,
        min_size: int = 1,
        max_size: int = 10,
        is_test: bool = False
    ):
        """Initialize a new DB connection pool.

        Args:
            host: Database host (Aurora cluster endpoint or RDS instance endpoint)
            port: Database port
            database: Database name
            readonly: Whether connections should be read-only
            secret_arn: ARN of the secret containing credentials
            region: AWS region for Secrets Manager
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
        self.pool: Optional["AsyncConnectionPool[Any]"] = None
        
        # Get credentials from Secrets Manager
        logger.info(f"Retrieving credentials from Secrets Manager: {secret_arn}")
        self.user, self.password = self._get_credentials_from_secret(secret_arn, region, is_test)
        logger.info(f"Successfully retrieved credentials for user: {self.user}")
        
        # Store connection info
        if not is_test:
            self.conninfo = f"host={host} port={port} dbname={database} user={self.user} password={self.password}"
            logger.info("Connection parameters stored")
    
    async def _get_connection(self):
        """Get a database connection."""
        import psycopg
        return await psycopg.AsyncConnection.connect(self.conninfo)
    
    async def execute_query(
        self, 
        sql: str, 
        parameters: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Execute a SQL query using async connection."""
        try:
            async with await self._get_connection() as conn:
                async with conn.transaction():
                    if self.readonly_query:
                        await conn.execute("SET TRANSACTION READ ONLY")
                    
                    # Execute the query
                    if parameters:
                        params = self._convert_parameters(parameters)
                        result = await conn.execute(sql, params)
                    else:
                        result = await conn.execute(sql)
                    
                    # If there are results to fetch
                    if result.description:
                        # Get column names
                        columns = [desc[0] for desc in result.description]
                        
                        # Fetch all rows
                        rows = await result.fetchall()
                        
                        # Format the response similar to RDS Data API
                        column_metadata = [{"name": col} for col in columns]
                        records = []
                        
                        # Convert each row to the expected format
                        for row in rows:
                            record = []
                            for value in row:
                                if value is None:
                                    record.append({"isNull": True})
                                elif isinstance(value, str):
                                    record.append({"stringValue": value})
                                elif isinstance(value, int):
                                    record.append({"longValue": value})
                                elif isinstance(value, float):
                                    record.append({"doubleValue": value})
                                elif isinstance(value, bool):
                                    record.append({"booleanValue": value})
                                elif isinstance(value, bytes):
                                    record.append({"blobValue": value})
                                else:
                                    # Convert other types to string
                                    record.append({"stringValue": str(value)})
                            records.append(record)
                        
                        return {"columnMetadata": column_metadata, "records": records}
                    else:
                        # No results (e.g., for INSERT, UPDATE, etc.)
                        return {"columnMetadata": [], "records": []}
                        
        except Exception as e:
            logger.error(f"Database connection error: {str(e)}")
            raise e

    def _convert_parameters(self, parameters: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Convert query parameters from RDS Data API format to psycopg format."""
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
    
    def _get_credentials_from_secret(self, secret_arn: str, region: str, is_test: bool = False) -> Tuple[str, str]:
        """Get database credentials from AWS Secrets Manager."""
        if is_test:
            return "test_user", "test_password"
        
        try:
            # Create a Secrets Manager client
            logger.info(f"Creating Secrets Manager client in region {region}")
            session = boto3.session.Session()
            client = session.client(
                service_name='secretsmanager',
                region_name=region
            )
            
            # Get the secret value
            logger.info(f"Retrieving secret value for {secret_arn}")
            get_secret_value_response = client.get_secret_value(
                SecretId=secret_arn
            )
            logger.info("Successfully retrieved secret value")
            
            # Parse the secret string
            if 'SecretString' in get_secret_value_response:
                secret = json.loads(get_secret_value_response['SecretString'])
                logger.info(f"Secret keys: {', '.join(secret.keys())}")
                
                # Extract username and password
                username = secret.get('username') or secret.get('user') or secret.get('Username')
                password = secret.get('password') or secret.get('Password')
                
                if not username:
                    logger.error(f"Username not found in secret. Available keys: {', '.join(secret.keys())}")
                    raise ValueError(f"Secret does not contain username. Available keys: {', '.join(secret.keys())}")
                
                if not password:
                    logger.error("Password not found in secret")
                    raise ValueError(f"Secret does not contain password. Available keys: {', '.join(secret.keys())}")
                
                logger.info(f"Successfully extracted credentials for user: {username}")
                return username, password
            else:
                logger.error("Secret does not contain a SecretString")
                raise ValueError("Secret does not contain a SecretString")
        except Exception as e:
            logger.error(f"Error retrieving secret: {str(e)}")
            raise ValueError(f"Failed to retrieve credentials from Secrets Manager: {str(e)}")
    
    async def close(self) -> None:
        """Close connections."""
        pass
            
    async def check_connection_health(self) -> bool:
        """Check if the connection is healthy."""
        try:
            result = await self.execute_query("SELECT 1")
            return len(result.get("records", [])) > 0
        except Exception as e:
            logger.error(f"Connection health check failed: {str(e)}")
            return False