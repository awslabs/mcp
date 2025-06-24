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

"""Connection pool manager for PostgreSQL MCP Server."""

import asyncio
import os
from typing import Dict, Optional, Union, Any
from loguru import logger
from .base_connection import DBConnector
from .rds_connector import RDSDataAPIConnector
from .postgres_driver import PostgresDriver
from .connection_factory import ConnectionFactory


class ConnectionPoolManager:
    """Manages connection pools for different connection types."""
    
    def __init__(self):
        """Initialize the connection pool manager."""
        self._pools: Dict[str, Dict[str, Any]] = {}
        self._pool_lock = asyncio.Lock()
        self.min_size = int(os.getenv('POSTGRES_POOL_MIN_SIZE', '5'))
        self.max_size = int(os.getenv('POSTGRES_POOL_MAX_SIZE', '30'))
        self.timeout = int(os.getenv('POSTGRES_POOL_TIMEOUT', '30'))
        
    async def get_connection(
        self,
        secret_arn: str,
        region_name: str = "us-west-2",
        resource_arn: Optional[str] = None,
        database: Optional[str] = None,
        hostname: Optional[str] = None,
        port: Optional[int] = None,
        readonly: bool = True
    ) -> DBConnector:
        """
        Get a connection from the pool or create a new one.
        
        Args:
            secret_arn: ARN of the secret containing credentials
            region_name: AWS region name
            resource_arn: ARN of the RDS cluster or instance
            database: Database name
            hostname: Database hostname
            port: Database port
            readonly: Whether connection is read-only
            
        Returns:
            Database connection instance
            
        Raises:
            ValueError: If connection parameters are invalid
            Exception: If connection creation fails
        """
        # Determine connection type
        connection_type = ConnectionFactory.determine_connection_type(
            resource_arn=resource_arn,
            hostname=hostname,
            secret_arn=secret_arn,
            database=database
        )
        
        # Validate parameters
        is_valid, error_msg = ConnectionFactory.validate_connection_params(
            connection_type=connection_type,
            secret_arn=secret_arn,
            resource_arn=resource_arn,
            database=database,
            hostname=hostname,
            region_name=region_name
        )
        
        if not is_valid:
            raise ValueError(error_msg)
        
        # Create pool key
        pool_key = ConnectionFactory.create_pool_key(
            connection_type=connection_type,
            resource_arn=resource_arn,
            hostname=hostname,
            port=port,
            database=database,
            secret_arn=secret_arn
        )
        
        async with self._pool_lock:
            # Get or create pool
            if pool_key not in self._pools:
                self._pools[pool_key] = {
                    'connections': [],
                    'in_use': set(),
                    'connection_type': connection_type,
                    'params': {
                        'secret_arn': secret_arn,
                        'region_name': region_name,
                        'resource_arn': resource_arn,
                        'database': database,
                        'hostname': hostname,
                        'port': port or 5432,
                        'readonly': readonly
                    }
                }
                logger.info(f"Created new connection pool: {pool_key}")
            
            pool = self._pools[pool_key]
            
            # Try to get an available connection
            available_connections = [
                conn for conn in pool['connections'] 
                if conn not in pool['in_use']
            ]
            
            for connection in available_connections:
                # Health check the connection
                if await connection.health_check():
                    pool['in_use'].add(connection)
                    logger.debug(f"Reusing healthy connection from pool: {pool_key}")
                    return connection
                else:
                    # Remove unhealthy connection
                    pool['connections'].remove(connection)
                    await connection.disconnect()
                    logger.warning(f"Removed unhealthy connection from pool: {pool_key}")
            
            # Create new connection if pool is not at max capacity
            if len(pool['connections']) < self.max_size:
                connection = await self._create_connection(
                    connection_type, pool['params']
                )
                
                if connection and await connection.connect():
                    pool['connections'].append(connection)
                    pool['in_use'].add(connection)
                    logger.info(f"Created new connection for pool: {pool_key}")
                    return connection
                else:
                    raise Exception(f"Failed to create connection for pool: {pool_key}")
            
            # If we reach here, pool is at capacity and no connections available
            raise Exception(f"Connection pool at capacity and no available connections: {pool_key}")
    
    async def return_connection(
        self,
        connection: DBConnector
    ):
        """
        Return a connection to the pool.
        
        Args:
            connection: Database connection to return
        """
        async with self._pool_lock:
            for pool_key, pool in self._pools.items():
                if connection in pool['in_use']:
                    pool['in_use'].remove(connection)
                    logger.debug(f"Returned connection to pool: {pool_key}")
                    return
            
            logger.warning("Attempted to return connection not found in any pool")
    
    async def _create_connection(
        self,
        connection_type: str,
        params: Dict[str, Any]
    ) -> DBConnector:
        """
        Create a new connection based on type and parameters.
        
        Args:
            connection_type: Type of connection to create ('rds_data_api' or 'psycopg_driver')
            params: Connection parameters
            
        Returns:
            New connection instance
        """
        # Use the ConnectionFactory to create the appropriate connection
        return ConnectionFactory.create_connection(
            resource_arn=params.get('resource_arn'),
            hostname=params.get('hostname'),
            port=params.get('port', 5432),
            secret_arn=params['secret_arn'],
            database=params['database'],
            region=params['region_name'],
            readonly=params['readonly']
        )
    
    async def close_all_connections(self):
        """Close all connections in all pools."""
        async with self._pool_lock:
            for pool_key, pool in self._pools.items():
                logger.info(f"Closing all connections in pool: {pool_key}")
                for connection in pool['connections']:
                    try:
                        await connection.disconnect()
                    except Exception as e:
                        logger.warning(f"Error closing connection: {str(e)}")
                
                pool['connections'].clear()
                pool['in_use'].clear()
            
            self._pools.clear()
            logger.info("All connection pools closed")
    
    def get_pool_stats(self) -> Dict[str, Dict[str, Any]]:
        """
        Get statistics for all connection pools.
        
        Returns:
            Dictionary containing pool statistics
        """
        stats = {}
        for pool_key, pool in self._pools.items():
            stats[pool_key] = {
                'total_connections': len(pool['connections']),
                'in_use_connections': len(pool['in_use']),
                'available_connections': len(pool['connections']) - len(pool['in_use']),
                'connection_type': pool['connection_type']
            }
        return stats


# Global connection pool manager instance
connection_pool_manager = ConnectionPoolManager()
