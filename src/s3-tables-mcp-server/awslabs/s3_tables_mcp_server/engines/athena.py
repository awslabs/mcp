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

import time
from ..utils import get_athena_client
from pydantic import BaseModel
from typing import Any, Dict, Optional


class AthenaConfig(BaseModel):
    """Configuration for Athena connection."""

    output_location: str  # The S3 location where Athena query results will be stored (required)
    workgroup: Optional[str] = None  # The Athena workgroup to use for queries
    region: Optional[str] = None  # The AWS region where Athena is running
    database: Optional[str] = None  # The Athena database to use
    catalog: Optional[str] = None  # The Athena catalog to use


class AthenaEngine:
    """Engine for interacting with Amazon Athena service.

    This class provides functionality to execute queries and manage workgroups
    in Amazon Athena using the provided configuration.
    """

    def __init__(self, config: AthenaConfig):
        """Initialize Athena engine with configuration.

        Args:
            config: Athena configuration containing connection parameters
        """
        self.config = config
        self._client = None
        self._initialize_connection()

    def _initialize_connection(self):
        """Initialize the Athena connection using the provided configuration."""
        try:
            # Initialize Athena client using the utility function
            self._client = get_athena_client(region_name=self.config.region)

        except Exception as e:
            raise ConnectionError(f'Failed to initialize Athena connection: {str(e)}')

    def execute_query(self, query: str) -> Dict[str, Any]:
        """Execute a query against Athena.

        Args:
            query: SQL query to execute

        Returns:
            Dict containing:
                - columns: List of column names
                - rows: List of rows, where each row is a list of values
                - query_execution_id: The ID of the query execution
                - output_location: The S3 location where results are stored
                - query_execution: Filtered query execution details including:
                    - QueryExecutionId
                    - Query
                    - StatementType
                    - ResultConfiguration
                    - QueryExecutionContext
                    - WorkGroup
                    - EngineVersion
                    - SubstatementType
        """
        if not self._client:
            raise ConnectionError('No active connection to Athena')

        try:
            # Start query execution
            response = self._client.start_query_execution(
                QueryString=query,
                QueryExecutionContext={
                    'Database': self.config.database,
                    'Catalog': self.config.catalog,
                },
                WorkGroup=self.config.workgroup,
                ResultConfiguration={'OutputLocation': self.config.output_location},
            )

            query_execution_id = response['QueryExecutionId']

            # Wait for query to complete
            while True:
                query_status = self._client.get_query_execution(
                    QueryExecutionId=query_execution_id
                )
                state = query_status['QueryExecution']['Status']['State']

                if state in ['SUCCEEDED', 'FAILED', 'CANCELLED']:
                    break

                time.sleep(1)  # Wait 1 second before checking again

            if state == 'FAILED':
                error_message = query_status['QueryExecution']['Status'].get(
                    'StateChangeReason', 'Unknown error'
                )
                raise Exception(f'Query failed: {error_message}')

            if state == 'CANCELLED':
                raise Exception('Query was cancelled')

            # Get results
            results = self._client.get_query_results(QueryExecutionId=query_execution_id)

            # Filter query execution details
            query_execution = query_status['QueryExecution']
            filtered_execution = {
                'QueryExecutionId': query_execution['QueryExecutionId'],
                'Query': query_execution['Query'],
                'StatementType': query_execution['StatementType'],
                'ResultConfiguration': query_execution['ResultConfiguration'],
                'QueryExecutionContext': query_execution['QueryExecutionContext'],
                'WorkGroup': query_execution['WorkGroup'],
                'EngineVersion': query_execution['EngineVersion'],
                'SubstatementType': query_execution['SubstatementType'],
            }

            # Process results
            if not results['ResultSet']['Rows']:
                return {
                    'columns': [],
                    'rows': [],
                    'query_execution_id': query_execution_id,
                    'output_location': self.config.output_location,
                    'query_execution': filtered_execution,
                }

            # Get column names from ResultSetMetadata
            columns = [
                col['Name'] for col in results['ResultSet']['ResultSetMetadata']['ColumnInfo']
            ]

            # Get data from rows (skip header row)
            rows = []
            for row in results['ResultSet']['Rows'][1:]:
                rows.append([field.get('VarCharValue', '') for field in row['Data']])

            return {
                'columns': columns,
                'rows': rows,
                'query_execution_id': query_execution_id,
                'output_location': self.config.output_location,
                'query_execution': filtered_execution,
            }

        except Exception as e:
            raise Exception(f'Error executing query: {str(e)}')

    def test_connection(self) -> bool:
        """Test the connection to Athena by executing a simple query.

        Returns:
            bool: True if the connection is successful, False otherwise.
        """
        try:
            # Execute a simple query that should work in any Athena database
            self.execute_query('SELECT 1')
            return True
        except Exception:
            return False
