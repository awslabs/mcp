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

"""Database connection singleton for MySQL and MariaDB MCP Server."""

from awslabs.mysql_mcp_server.connection.asyncmy_pool_connection import AsyncmyPoolConnection
from awslabs.mysql_mcp_server.connection.rds_data_api_connection import RDSDataAPIConnection


class DBConnectionSingleton:
    """Manages a single database connection instance across the application."""

    _instance = None

    def __init__(
        self,
        secret_arn: str,
        database: str,
        region: str,
        readonly: bool = True,
        is_test: bool = False,
        resource_arn: str | None = None,
        hostname: str | None = None,
        port: int | None = None,
    ):
        """Initialize a new DB connection singleton using one of the two connection types.

        1. RDS Data API Connection by specifying resource ARN
        2. Direct MySQL or MariaDB connection by specifying hostname and port

        Args:
            secret_arn: The ARN of the secret containing credentials
            database: The name of the database to connect to
            region: The AWS region where the RDS instance is located
            readonly: Whether the connection should be read-only (default: True)
            resource_arn: The ARN of the RDS cluster (for using RDS Data API)
            hostname: Database hostname (for using direct MySQL connection)
            port: Database port (for using direct MySQL connection)
            is_test: Whether this is a test connection (default: False)
        """
        if resource_arn:
            if not all([resource_arn, secret_arn, database, region]):
                raise ValueError(
                    'Missing required connection parameters for RDS Data API. '
                    'Please provide resource_arn, secret_arn, database, and region.'
                )

            self._db_connection = RDSDataAPIConnection(
                cluster_arn=resource_arn,
                secret_arn=secret_arn,
                database=database,
                region=region,
                readonly=readonly,
                is_test=is_test,
            )
        else:
            # Direct connection to MySQL/MariaDB
            if not all([hostname, port, secret_arn, database, region]):
                raise ValueError(
                    'Missing required connection parameters for direct MySQL connection. '
                    'Please provide hostname, port, secret_arn, database, and region.'
                )
            assert hostname is not None
            assert port is not None

            self._db_connection = AsyncmyPoolConnection(
                hostname=hostname,
                port=port,
                secret_arn=secret_arn,
                database=database,
                region=region,
                readonly=readonly,
            )

    @classmethod
    def initialize(
        cls,
        secret_arn: str,
        database: str,
        region: str,
        readonly: bool = True,
        is_test: bool = False,
        resource_arn: str | None = None,
        hostname: str | None = None,
        port: int | None = None,
    ):
        """Initialize the singleton instance if it doesn't exist.

        Args:
            resource_arn: The ARN of the RDS cluster (for using RDS Data API)
            hostname: Database hostname (for using direct MySQL/MariaDB connection)
            port: Database port (for using direct MySQL/MariaDB connection)
            secret_arn: The ARN of the secret containing credentials
            database: The name of the database to connect to
            region: The AWS region where the RDS instance is located
            readonly: Whether the connection should be read-only (default: True)
            is_test: Whether this is a test connection (default: False)
        """
        if cls._instance is None:
            cls._instance = cls(
                secret_arn=secret_arn,
                database=database,
                region=region,
                readonly=readonly,
                resource_arn=resource_arn,
                hostname=hostname,
                port=port,
                is_test=is_test,
            )

    @classmethod
    def get(cls):
        """Get the singleton instance.

        Returns:
            DBConnectionSingleton: The singleton instance
        Raises:
            RuntimeError: If the singleton has not been initialized
        """
        if cls._instance is None:
            raise RuntimeError('DBConnectionSingleton is not initialized.')
        return cls._instance

    @property
    def db_connection(self):
        """Get the database connection.

        Returns:
            DBConnection: The database connection instance
        """
        return self._db_connection
