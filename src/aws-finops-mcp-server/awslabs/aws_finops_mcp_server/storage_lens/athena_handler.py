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

"""Athena handler for S3 Storage Lens data.

This module provides functionality to create and query Athena tables for S3 Storage Lens data.
"""

import logging
import time
from awslabs.aws_finops_mcp_server.consts import ATHENA_MAX_RETRIES, ATHENA_RETRY_DELAY_SECONDS
from awslabs.aws_finops_mcp_server.models import AthenaQueryExecution, SchemaInfo
from typing import Any, Dict, Optional
from urllib.parse import urlparse


# Configure logging
logger = logging.getLogger(__name__)


class AthenaHandler:
    """Handler for Athena operations on S3 Storage Lens data."""

    def __init__(self):
        """Initialize the Athena client."""
        from awslabs.aws_finops_mcp_server.utils.aws_utils import create_boto3_client

        # Create Athena client using the common utility function
        self.athena_client = create_boto3_client('athena')

    async def create_database(self, database_name: str, output_location: str) -> None:
        """Create an Athena database if it doesn't exist.

        Args:
            database_name: Name of the database to create
            output_location: S3 location for query results
        """
        create_db_query = f'CREATE DATABASE IF NOT EXISTS {database_name}'
        await self.execute_query(create_db_query, 'default', output_location)

    async def create_table_for_csv(
        self,
        database_name: str,
        table_name: str,
        schema_info: SchemaInfo,
        data_location: str,
        output_location: str,
    ) -> None:
        """Create an Athena table for CSV data.

        Args:
            database_name: Name of the database
            table_name: Name of the table to create
            schema_info: Schema information from manifest
            data_location: S3 location of the data files
            output_location: S3 location for query results
        """
        column_definitions = []
        for column in schema_info.columns:
            column_definitions.append(f'`{column.name}` {column.type}')

        create_table_query = f"""
        CREATE EXTERNAL TABLE IF NOT EXISTS {database_name}.{table_name} (
            {', '.join(column_definitions)}
        )
        ROW FORMAT DELIMITED
        FIELDS TERMINATED BY ','
        STORED AS TEXTFILE
        LOCATION '{data_location}'
        TBLPROPERTIES ('skip.header.line.count'='1')
        """

        await self.execute_query(create_table_query, database_name, output_location)

    async def create_table_for_parquet(
        self,
        database_name: str,
        table_name: str,
        schema_info: SchemaInfo,
        data_location: str,
        output_location: str,
    ) -> None:
        """Create an Athena table for Parquet data.

        Args:
            database_name: Name of the database
            table_name: Name of the table to create
            schema_info: Schema information from manifest
            data_location: S3 location of the data files
            output_location: S3 location for query results
        """
        column_definitions = []
        for column in schema_info.columns:
            column_definitions.append(f'`{column.name}` {column.type}')

        create_table_query = f"""
        CREATE EXTERNAL TABLE IF NOT EXISTS {database_name}.{table_name} (
            {', '.join(column_definitions)}
        )
        STORED AS PARQUET
        LOCATION '{data_location}'
        """

        await self.execute_query(create_table_query, database_name, output_location)

    async def setup_table(
        self,
        database_name: str,
        table_name: str,
        schema_info: SchemaInfo,
        data_location: str,
        output_location: str,
    ) -> None:
        """Set up an Athena table based on the schema information.

        Args:
            database_name: Name of the database
            table_name: Name of the table to create
            schema_info: Schema information from manifest
            data_location: S3 location of the data files
            output_location: S3 location for query results
        """
        logger.info(f'Setting up Athena table {database_name}.{table_name}')
        logger.info(f'Data location: {data_location}')
        logger.info(f'Schema format: {schema_info.format}')
        logger.info(f'Columns: {[col.name for col in schema_info.columns]}')

        # Create database if it doesn't exist
        await self.create_database(database_name, output_location)

        # Create table based on format
        from awslabs.aws_finops_mcp_server.models import SchemaFormat

        if schema_info.format == SchemaFormat.CSV:
            logger.info('Creating table for CSV format')
            await self.create_table_for_csv(
                database_name, table_name, schema_info, data_location, output_location
            )
        else:  # Parquet format
            logger.info('Creating table for Parquet format')
            await self.create_table_for_parquet(
                database_name, table_name, schema_info, data_location, output_location
            )

    async def execute_query(
        self, query: str, database_name: str, output_location: str
    ) -> AthenaQueryExecution:
        """Execute an Athena query.

        Args:
            query: SQL query to execute
            database_name: Athena database name to use
            output_location: S3 location for Athena query results

        Returns:
            AthenaQueryExecution: Query execution ID and status
        """
        try:
            logger.info(f'Executing Athena query on database {database_name}:')
            logger.info(f'Query: {query}')
            logger.info(f'Output location: {output_location}')

            # Start query execution
            response = self.athena_client.start_query_execution(
                QueryString=query,
                QueryExecutionContext={'Database': database_name},
                ResultConfiguration={'OutputLocation': output_location},
            )

            query_execution_id = response['QueryExecutionId']
            logger.info(f'Query execution ID: {query_execution_id}')

            return AthenaQueryExecution(query_execution_id=query_execution_id, status='STARTED')

        except Exception as e:
            logger.error(f'Error starting Athena query: {str(e)}')
            raise Exception(f'Error starting Athena query: {str(e)}')

    async def wait_for_query_completion(
        self, query_execution_id: str, max_retries: int = ATHENA_MAX_RETRIES
    ) -> Dict[str, Any]:
        """Wait for an Athena query to complete.

        Args:
            query_execution_id: Query execution ID
            max_retries: Maximum number of retries

        Returns:
            Dict[str, Any]: Query execution status
        """
        state = 'RUNNING'  # Initial state assumption
        retries = 0

        logger.info(f'Waiting for Athena query {query_execution_id} to complete...')

        while (state == 'RUNNING' or state == 'QUEUED') and retries < max_retries:
            response = self.athena_client.get_query_execution(QueryExecutionId=query_execution_id)
            state = response['QueryExecution']['Status']['State']

            logger.info(f'Query state: {state} (retry {retries}/{max_retries})')

            if state == 'FAILED':
                reason = response['QueryExecution']['Status'].get(
                    'StateChangeReason', 'Unknown error'
                )
                logger.error(f'Query failed: {reason}')
                logger.error(f'Full response: {response}')
                raise Exception(f'Query failed: {reason}')
            elif state == 'SUCCEEDED':
                logger.info(f'Query succeeded after {retries} retries')
                return response['QueryExecution']

            # Wait before checking again
            time.sleep(ATHENA_RETRY_DELAY_SECONDS)
            retries += 1

        if retries >= max_retries:
            logger.error(f'Query timed out after {max_retries} retries')
            raise Exception('Query timed out')

        return None

    async def get_query_results(self, query_execution_id: str) -> Dict[str, Any]:
        """Get the results of a completed Athena query.

        Args:
            query_execution_id: Query execution ID

        Returns:
            Dict[str, Any]: Query results and metadata
        """
        try:
            # Get query results
            results_response = self.athena_client.get_query_results(
                QueryExecutionId=query_execution_id
            )

            # Process results
            columns = [
                col['Label']
                for col in results_response['ResultSet']['ResultSetMetadata']['ColumnInfo']
            ]
            rows = []

            # Skip header row if it exists
            result_rows = results_response['ResultSet']['Rows']
            start_index = (
                1 if len(result_rows) > 0 and len(columns) == len(result_rows[0]['Data']) else 0
            )

            for row in result_rows[start_index:]:
                values = [item.get('VarCharValue', '') for item in row['Data']]
                rows.append(dict(zip(columns, values)))

            return {'columns': columns, 'rows': rows}

        except Exception as e:
            raise Exception(f'Error getting query results: {str(e)}')

    def determine_output_location(
        self, data_location: str, output_location: Optional[str] = None
    ) -> str:
        """Determine the output location for Athena query results.

        Args:
            data_location: S3 location of the data files
            output_location: User-provided output location

        Returns:
            str: S3 location for Athena query results
        """
        if output_location:
            return output_location

        # If output_location is not provided, use the same bucket as the data
        parsed_data_uri = urlparse(data_location)
        bucket = parsed_data_uri.netloc
        return f's3://{bucket}/athena-results/'
