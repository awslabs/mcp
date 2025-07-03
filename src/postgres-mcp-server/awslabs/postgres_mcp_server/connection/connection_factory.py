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

"""Connection factory for determining connection types and creating connections."""

import os
from .base_connection import DBConnector
from .psycopg_connector import PsycopgConnector
from .rds_connector import RDSDataAPIConnector, Boto3ClientSingleton
from loguru import logger
from typing import Any, Dict, Optional, Tuple


# Default pool configuration from environment variables
DEFAULT_MIN_SIZE = int(os.getenv('POSTGRES_POOL_MIN_SIZE', '4'))
DEFAULT_MAX_SIZE = int(os.getenv('POSTGRES_POOL_MAX_SIZE', '30'))
DEFAULT_TIMEOUT = float(os.getenv('POSTGRES_POOL_TIMEOUT', '30.0'))


class ConnectionFactory:
    """
    Factory class for determining connection types and creating appropriate connections.
    
    This factory creates instances of database connectors based on the provided parameters.
    The connectors use singleton patterns internally to ensure efficient resource usage:
    
    1. Boto3ClientSingleton: Ensures that boto3 clients are reused across the application,
       maintaining HTTP keep-alive connections and reducing the overhead of creating new clients.
       
    Note: The psycopg3 ConnectionPool already manages connection pooling internally,
    so no additional singleton pattern is needed for connection pools.
    """

    @staticmethod
    def determine_connection_type(
        resource_arn: Optional[str] = None,
        hostname: Optional[str] = None,
        secret_arn: Optional[str] = None,
        database: Optional[str] = None
    ) -> str:
        """
        Determine the connection type based on provided parameters.

        Args:
            resource_arn: ARN of the RDS cluster or instance
            hostname: Database hostname
            secret_arn: ARN of the secret containing credentials
            database: Database name

        Returns:
            Connection type: 'rds_data_api' or 'psycopg_pool'

        Raises:
            ValueError: If neither resource_arn nor hostname is provided
        """
        if resource_arn:
            logger.info("Using RDS Data API connection (resource_arn provided)")
            return "rds_data_api"
        elif hostname:
            logger.info("Using PostgreSQL connection with connection pool (hostname provided)")
            return "psycopg_pool"
        else:
            raise ValueError("Either resource_arn or hostname must be provided")

    @staticmethod
    def create_connection(
        resource_arn: Optional[str] = None,
        hostname: Optional[str] = None,
        port: int = 5432,
        secret_arn: Optional[str] = None,
        database: Optional[str] = None,
        region: Optional[str] = None,
        readonly: bool = True
    ) -> DBConnector:
        """
        Create and return the appropriate connection object.

        Args:
            resource_arn: ARN of the RDS cluster or instance
            hostname: Database hostname
            port: Database port
            secret_arn: ARN of the secret containing credentials
            database: Database name
            region: AWS region name
            readonly: Whether connection is read-only

        Returns:
            DBConnector: An instance of the appropriate connector class

        Raises:
            ValueError: If neither resource_arn nor hostname is provided
        """
        connection_type = ConnectionFactory.determine_connection_type(
            resource_arn=resource_arn,
            hostname=hostname
        )

        # Validate parameters
        is_valid, error_msg = ConnectionFactory.validate_connection_params(
            connection_type=connection_type,
            secret_arn=secret_arn,
            resource_arn=resource_arn,
            database=database,
            hostname=hostname,
            region_name=region
        )

        if not is_valid:
            raise ValueError(error_msg)

        if connection_type == "rds_data_api":
            if not resource_arn or not secret_arn or not database or not region:
                raise ValueError("RDS Data API requires resource_arn, secret_arn, database, and region")
            return RDSDataAPIConnector(
                resource_arn=resource_arn,
                secret_arn=secret_arn,
                database=database,
                region_name=region,
                readonly=readonly
            )
        elif connection_type == "psycopg_pool":
            if not hostname or not database or not secret_arn or not region:
                raise ValueError("PostgreSQL connector requires hostname, database, secret_arn, and region")
            
            return PsycopgConnector(
                hostname=hostname,
                port=port,
                database=database,
                secret_arn=secret_arn,
                region_name=region,
                readonly=readonly,
                min_size=DEFAULT_MIN_SIZE,
                max_size=DEFAULT_MAX_SIZE,
                timeout=DEFAULT_TIMEOUT
            )
        else:
            raise ValueError(f"Unknown connection type: {connection_type}")

    @staticmethod
    def create_pool_key(
        connection_type: str,
        resource_arn: Optional[str] = None,
        hostname: Optional[str] = None,
        port: Optional[int] = None,
        database: Optional[str] = None,
        secret_arn: Optional[str] = None
    ) -> str:
        """
        Create a unique pool key for connection pooling.

        Args:
            connection_type: Type of connection ('rds_data_api' or 'psycopg_driver')
            resource_arn: ARN of the RDS cluster or instance
            hostname: Database hostname
            port: Database port
            database: Database name
            secret_arn: ARN of the secret containing credentials

        Returns:
            Unique pool key string
        """
        if connection_type == "rds_data_api":
            secret_hash = hash(secret_arn) if secret_arn else 0
            return f"rds://{resource_arn}/{database}#{secret_hash}"
        elif connection_type == "psycopg_pool":
            port = port or 5432
            secret_hash = hash(secret_arn) if secret_arn else 0
            return f"postgres://{hostname}:{port}/{database}#{secret_hash}"
        else:
            raise ValueError(f"Unknown connection type: {connection_type}")

    @staticmethod
    def get_connection_config() -> Dict[str, Any]:
        """
        Get connection configuration from environment variables.

        Returns:
            Dictionary containing connection configuration
        """
        return {
            'secret_arn': os.getenv('POSTGRES_SECRET_ARN'),
            'resource_arn': os.getenv('POSTGRES_RESOURCE_ARN'),
            'database': os.getenv('POSTGRES_DATABASE'),
            'hostname': os.getenv('POSTGRES_HOSTNAME'),
            'port': int(os.getenv('POSTGRES_PORT', '5432')),
            'region_name': os.getenv('POSTGRES_REGION', 'us-west-2'),
            'readonly': os.getenv('POSTGRES_READONLY', 'true').lower() == 'true',
            'min_size': DEFAULT_MIN_SIZE,
            'max_size': DEFAULT_MAX_SIZE,
            'timeout': DEFAULT_TIMEOUT
        }

    @staticmethod
    def validate_connection_params(
        connection_type: str,
        secret_arn: Optional[str] = None,
        resource_arn: Optional[str] = None,
        database: Optional[str] = None,
        hostname: Optional[str] = None,
        region_name: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Validate connection parameters for the given connection type.

        Args:
            connection_type: Type of connection
            secret_arn: ARN of the secret containing credentials
            resource_arn: ARN of the RDS cluster or instance
            database: Database name
            hostname: Database hostname
            region_name: AWS region name

        Returns:
            Tuple of (is_valid, error_message)
        """
        if connection_type == "rds_data_api":
            if not all([resource_arn, secret_arn, database, region_name]):
                missing = []
                if not resource_arn:
                    missing.append('resource_arn')
                if not secret_arn:
                    missing.append('secret_arn')
                if not database:
                    missing.append('database')
                if not region_name:
                    missing.append('region_name')
                return False, f"Missing required parameters for RDS Data API: {', '.join(missing)}"

        elif connection_type == "psycopg_pool":
            if not all([hostname, database, secret_arn, region_name]):
                missing = []
                if not hostname:
                    missing.append('hostname')
                if not database:
                    missing.append('database')
                if not secret_arn:
                    missing.append('secret_arn')
                if not region_name:
                    missing.append('region_name')
                return False, f"Missing required parameters for PostgreSQL connection pool: {', '.join(missing)}"

        else:
            return False, f"Unknown connection type: {connection_type}"

        return True, ""
