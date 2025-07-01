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

"""RDS Data API connector implementation."""

import asyncio
import boto3
from .base_connection import DBConnector
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


class RDSDataAPIConnector(DBConnector):
    """Connector for RDS Data API connections."""

    def __init__(
        self,
        resource_arn: str,
        secret_arn: str,
        database: str,
        region_name: str,
        readonly: bool = True
    ):
        """
        Initialize RDS Data API connector.

        Args:
            resource_arn: ARN of the RDS cluster or instance
            secret_arn: ARN of the secret containing credentials
            database: Database name
            region_name: AWS region name
            readonly: Whether connection is read-only
        """
        self.resource_arn = resource_arn
        self.secret_arn = secret_arn
        self.database = database
        self.region_name = region_name
        self.readonly = readonly
        self._client = None
        self._connected = False

    @property
    def client(self):
        """Get or create the RDS Data API client using the singleton pattern."""
        if self._client is None:
            self._client = Boto3ClientSingleton.get_client('rds-data', self.region_name)
        return self._client


    async def execute_query(
        self,
        query: str,
        parameters: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Execute a query using RDS Data API.

        Args:
            query: SQL query to execute
            parameters: Query parameters

        Returns:
            Query result dictionary

        Raises:
            ClientError: If AWS API call fails
            Exception: For other errors
        """
        # Don't auto-connect here to avoid recursion - let the caller handle connection
        execute_params = {
            'resourceArn': self.resource_arn,
            'secretArn': self.secret_arn,
            'database': self.database,
            'sql': query,
            'includeResultMetadata': True,
        }

        if parameters:
            execute_params['parameters'] = parameters

        if self.readonly:
            return await self._execute_readonly_query(execute_params)
        else:
            return await asyncio.to_thread(
                self.client.execute_statement, **execute_params
            )

    async def _execute_readonly_query(self, execute_params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute query in read-only transaction."""
        tx_id = None
        try:
            # Begin read-only transaction
            tx_response = await asyncio.to_thread(
                self.client.begin_transaction,
                resourceArn=self.resource_arn,
                secretArn=self.secret_arn,
                database=self.database
            )
            tx_id = tx_response['transactionId']

            # Set transaction to read-only
            await asyncio.to_thread(
                self.client.execute_statement,
                resourceArn=self.resource_arn,
                secretArn=self.secret_arn,
                database=self.database,
                sql='SET TRANSACTION READ ONLY',
                transactionId=tx_id
            )

            # Execute the actual query
            execute_params['transactionId'] = tx_id
            result = await asyncio.to_thread(
                self.client.execute_statement, **execute_params
            )

            # Commit transaction
            await asyncio.to_thread(
                self.client.commit_transaction,
                resourceArn=self.resource_arn,
                secretArn=self.secret_arn,
                transactionId=tx_id
            )

            return result

        except Exception as e:
            if tx_id:
                try:
                    await asyncio.to_thread(
                        self.client.rollback_transaction,
                        resourceArn=self.resource_arn,
                        secretArn=self.secret_arn,
                        transactionId=tx_id
                    )
                except Exception as rollback_error:
                    logger.error(f"Failed to rollback transaction: {rollback_error}")
            raise e

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
            logger.warning(f"Health check failed for RDS Data API: {str(e)}")
            return False

    @property
    def connection_info(self) -> Dict[str, Any]:
        """Get connection information."""
        return {
            'type': 'rds_data_api',
            'resource_arn': self.resource_arn,
            'database': self.database,
            'region': self.region_name,
            'readonly': self.readonly,
            'connected': self._connected
        }
