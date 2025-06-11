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

"""Factory for creating database connections."""

from typing import Dict, Any, Optional, Union
from loguru import logger


class ConnectionFactory:
    """Factory to create the appropriate connection based on provided parameters."""
    
    @staticmethod
    async def create_connection(config: Dict[str, Any]):
        """Create a connection based on the provided configuration.
        
        Args:
            config: Configuration with endpoint and/or resource_arn
            
        Returns:
            The appropriate connection object
            
        Raises:
            ValueError: If insufficient connection parameters are provided
        """
        # Extract configuration parameters
        reader_endpoint = config.get('reader_endpoint')
        writer_endpoint = config.get('writer_endpoint')
        port = config.get('port', 5432)
        database = config.get('database')
        resource_arn = config.get('resource_arn')
        secret_arn = config.get('secret_arn')
        region = config.get('region')
        readonly = config.get('readonly', True)
        min_connections = config.get('min_connections', 1)
        max_connections = config.get('max_connections', 10)
        
        # Decision logic for connection type
        # For direct connection, we need:
        # - secret_arn and region
        # - If readonly is True, we need reader_endpoint
        # - If readonly is False, we need writer_endpoint
        if secret_arn and region and ((readonly and reader_endpoint) or (not readonly and writer_endpoint)):
            try:
                # Try direct connection with psycopg3
                from .psycopg_connection import PostgresConfig, PostgresDirectConnection
                
                connection_config = PostgresConfig(
                    reader_endpoint=reader_endpoint or "",  # Use empty string if None
                    writer_endpoint=writer_endpoint or "",  # Use empty string if None
                    port=port,
                    database=database,
                    secret_arn=secret_arn,
                    region=region,
                    readonly=readonly,
                    min_connections=min_connections,
                    max_connections=max_connections
                )
                
                connection = PostgresDirectConnection(connection_config)
                await connection.initialize()
                logger.info(f'Successfully connected to PostgreSQL using psycopg3')
                return connection
            except Exception as e:
                logger.warning(f'Failed to connect using psycopg3: {str(e)}')
                
                # If direct connection fails and resource_arn is provided, fall back to RDS Data API
                if resource_arn:
                    logger.info('Falling back to RDS Data API')
                    from .server import DBConnection
                    return DBConnection(
                        cluster_arn=resource_arn,
                        secret_arn=secret_arn,
                        database=database,
                        region=region,
                        readonly=readonly
                    )
                else:
                    # Re-raise the exception if we can't fall back
                    raise
        elif resource_arn and secret_arn and region:
            # Use RDS Data API
            logger.info(f'Using RDS Data API with resource ARN: {resource_arn}')
            from .server import DBConnection
            return DBConnection(
                cluster_arn=resource_arn,
                secret_arn=secret_arn,
                database=database,
                region=region,
                readonly=readonly
            )
        else:
            # Not enough information to create a connection
            raise ValueError(
                'Insufficient connection parameters. Provide either reader_endpoint/writer_endpoint with secret_arn or resource_arn/secret_arn.'
            )
