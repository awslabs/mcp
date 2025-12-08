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

"""RDS Data API connector for postgres MCP Server."""

import asyncio
import boto3
from awslabs.postgres_mcp_server.connection.abstract_db_connection import AbstractDBConnection
from loguru import logger
from typing import Any, Dict, List, Optional


class RDSDataAPIConnection(AbstractDBConnection):
    """Class that wraps DB connection client by RDS API."""

    def __init__(
        self,
        cluster_arn: str,
        secret_arn: str,
        database: str,
        region: str,
        readonly: bool,
        is_test: bool = False,
    ):
        """Initialize a new DB connection.

        Args:
            cluster_arn: The ARN of the RDS cluster
            secret_arn: The ARN of the secret containing credentials
            database: The name of the database to connect to
            region: The AWS region where the RDS instance is located
            readonly: Whether the connection should be read-only
            is_test: Whether this is a test connection
        """
        super().__init__(readonly)
        self.cluster_arn = cluster_arn
        self.secret_arn = secret_arn
        self.database = database
        if not is_test:
            self.data_client = boto3.client('rds-data', region_name=region)

    async def execute_query(
        self, sql: str, parameters: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Execute a SQL query using RDS Data API.

        Args:
            sql: The SQL query to execute
            parameters: Optional parameters for the query

        Returns:
            Dict containing query results with column metadata and records
        """
        if self.readonly_query:
            return await asyncio.to_thread(self._execute_readonly_query, sql, parameters)
        else:
            execute_params = {
                'resourceArn': self.cluster_arn,
                'secretArn': self.secret_arn,
                'database': self.database,
                'sql': sql,
                'includeResultMetadata': True,
            }

            if parameters:
                execute_params['parameters'] = parameters

            return await asyncio.to_thread(self.data_client.execute_statement, **execute_params)

    def _execute_readonly_query(
        self, query: str, parameters: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Execute a query under readonly transaction.

        Args:
            query: query to run
            parameters: parameters

        Returns:
            Dict containing query results with column metadata and records
        """
        tx_id = ''
        try:
            # Begin read-only transaction
            tx = self.data_client.begin_transaction(
                resourceArn=self.cluster_arn,
                secretArn=self.secret_arn,
                database=self.database,
            )

            tx_id = tx['transactionId']

            self.data_client.execute_statement(
                resourceArn=self.cluster_arn,
                secretArn=self.secret_arn,
                database=self.database,
                sql='SET TRANSACTION READ ONLY',
                transactionId=tx_id,
            )

            execute_params = {
                'resourceArn': self.cluster_arn,
                'secretArn': self.secret_arn,
                'database': self.database,
                'sql': query,
                'includeResultMetadata': True,
                'transactionId': tx_id,
            }

            if parameters is not None:
                execute_params['parameters'] = parameters

            result = self.data_client.execute_statement(**execute_params)

            self.data_client.commit_transaction(
                resourceArn=self.cluster_arn,
                secretArn=self.secret_arn,
                transactionId=tx_id,
            )
            return result
        except Exception as e:
            if tx_id:
                self.data_client.rollback_transaction(
                    resourceArn=self.cluster_arn,
                    secretArn=self.secret_arn,
                    transactionId=tx_id,
                )
            raise e

    async def close(self) -> None:
        """Close the database connection asynchronously."""
        # RDS Data API doesn't maintain persistent connections
        pass

    async def check_connection_health(self) -> bool:
        """Check if the RDS Data API connection is healthy.

        Returns:
            bool: True if the connection is healthy, False otherwise
        """
        try:
            result = await self.execute_query('SELECT 1')
            return len(result.get('records', [])) > 0
        except Exception as e:
            logger.error(f'RDS Data API connection health check failed: {str(e)}')
            return False
