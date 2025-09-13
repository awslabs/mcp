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

"""Database connection singleton for postgres MCP Server.

This singleton can initialize one of two connection strategies based on the
arguments provided to `initialize`:

- RDS Data API (`RDSDataAPIConnection`) when `resource_arn` is provided
- Direct psycopg pooled connection (`PsycopgPoolConnection`) when
  `resource_arn` is None and `host`/`port` are provided
"""

import asyncio
from awslabs.postgres_mcp_server.connection.rds_api_connection import RDSDataAPIConnection
from awslabs.postgres_mcp_server.connection.psycopg_pool_connection import PsycopgPoolConnection
from loguru import logger


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
        host: str | None = None,
        port: int | None = None,
    ):
        """Initialize a new DB connection singleton.

        Args:
            secret_arn: The ARN of the secret containing credentials
            database: The name of the database to connect to
            region: The AWS region for RDS/Secrets Manager
            readonly: Whether the connection should be read-only (default: True)
            is_test: Whether this is a test connection (default: False)
            resource_arn: The ARN of the RDS cluster (use RDS Data API if provided)
            host: Database hostname (required if resource_arn is None)
            port: Database port (required if resource_arn is None)
        """
        if resource_arn:
            # RDS Data API path
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
            # Direct psycopg connection path
            if not all([host, port, secret_arn, database, region]):
                raise ValueError(
                    'Missing required connection parameters for direct PostgreSQL connection. '
                    'Please provide host, port, secret_arn, database, and region.'
                )

            self._db_connection = PsycopgPoolConnection(
                host=host,  # type: ignore[arg-type]
                port=port,  # type: ignore[arg-type]
                database=database,
                readonly=readonly,
                secret_arn=secret_arn,
                region=region,
                is_test=is_test,
            )

    @classmethod
    def initialize(
        cls,
        resource_arn: str | None,
        secret_arn: str,
        database: str,
        region: str,
        readonly: bool = True,
        is_test: bool = False,
        host: str | None = None,
        port: int | None = None,
    ):
        """Initialize the singleton instance if it doesn't exist.

        Args:
            resource_arn: The ARN of the RDS cluster (if provided, uses RDS Data API)
            secret_arn: The ARN of the secret containing credentials
            database: The name of the database to connect to
            region: The AWS region where the RDS instance/Secrets Manager is located
            readonly: Whether the connection should be read-only (default: True)
            is_test: Whether this is a test connection (default: False)
            host: Database hostname (required if resource_arn is None)
            port: Database port (required if resource_arn is None)
        """
        if cls._instance is None:
            cls._instance = cls(
                secret_arn=secret_arn,
                database=database,
                region=region,
                readonly=readonly,
                is_test=is_test,
                resource_arn=resource_arn,
                host=host,
                port=port,
            )

    @classmethod
    def get(cls):
        """Get the singleton instance."""
        if cls._instance is None:
            raise RuntimeError('DBConnectionSingleton is not initialized.')
        return cls._instance

    @property
    def db_connection(self):
        """Get the database connection."""
        return self._db_connection

    @classmethod
    def cleanup(cls):
        """Clean up resources when shutting down."""
        if cls._instance and cls._instance._db_connection:
            # Handle calling async close method from sync context
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # If we're in an async context, create a task
                    asyncio.create_task(cls._instance._db_connection.close())
                else:
                    # If we're in a sync context, run the coroutine to completion
                    loop.run_until_complete(cls._instance._db_connection.close())
            except Exception as e:
                logger.error(f'Error during connection cleanup: {str(e)}')
