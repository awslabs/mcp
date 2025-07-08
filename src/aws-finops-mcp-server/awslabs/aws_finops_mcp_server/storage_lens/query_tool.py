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

"""S3 Storage Lens Query Tool for AWS FinOps MCP Server.

This module provides the main query tool that integrates manifest handling and Athena operations.
"""

from .athena_handler import AthenaHandler
from .manifest_handler import ManifestHandler


class StorageLensQueryTool:
    """Tool for querying S3 Storage Lens metrics using Athena."""

    def __init__(self):
        """Initialize the manifest and Athena handlers."""
        self.manifest_handler = ManifestHandler()
        self.athena_handler = AthenaHandler()

    async def query_storage_lens(
        self,
        manifest_location,
        query,
        output_location=None,
        database_name='storage_lens_db',
        table_name='storage_lens_metrics',
    ):
        """Query S3 Storage Lens metrics using Athena.

        Args:
            manifest_location (str): S3 URI to manifest file or folder containing manifest files
            query (str): SQL query to execute against the data
            output_location (str, optional): S3 location for Athena query results
            database_name (str, optional): Athena database name to use
            table_name (str, optional): Table name to create/use for the data

        Returns:
            dict: Query results and metadata
        """
        # 1. Locate and parse manifest file
        manifest = await self.manifest_handler.get_manifest(manifest_location)

        # 2. Extract data location and schema information
        data_location = self.manifest_handler.extract_data_location(manifest)
        schema_info = self.manifest_handler.parse_schema(manifest)

        # 3. Determine output location if not provided
        if not output_location:
            output_location = self.athena_handler.determine_output_location(data_location)

        # 4. Setup Athena database and table if needed
        await self.athena_handler.setup_table(
            database_name, table_name, schema_info, data_location, output_location
        )

        # 5. Replace {table} placeholder in query with actual table name
        formatted_query = query.replace('{table}', f'{database_name}.{table_name}')

        # 6. Execute query
        query_result = await self.athena_handler.execute_query(
            formatted_query, database_name, output_location
        )

        # 7. Wait for query to complete
        execution_details = await self.athena_handler.wait_for_query_completion(
            query_result['query_execution_id']
        )

        # 8. Get query results
        results = await self.athena_handler.get_query_results(query_result['query_execution_id'])

        # 9. Add query statistics and metadata
        stats = execution_details['Statistics']
        results.update(
            {
                'statistics': {
                    'engine_execution_time_ms': stats.get('EngineExecutionTimeInMillis', 0),
                    'data_scanned_bytes': stats.get('DataScannedInBytes', 0),
                    'total_execution_time_ms': stats.get('TotalExecutionTimeInMillis', 0),
                },
                'query': formatted_query,
                'manifest_location': manifest_location,
                'data_location': data_location,
            }
        )

        return results
