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

"""AWS S3 Tables MCP Server file processing module.

This module provides functionality for processing and analyzing uploaded files,
particularly focusing on CSV file handling and import capabilities.
"""

import io
import os
import pyarrow.csv as pc
from ..utils import get_s3_client, pyiceberg_load_catalog
from pyiceberg.exceptions import NoSuchTableError
from typing import Dict
from urllib.parse import urlparse


async def import_csv_to_table(
    warehouse: str,
    region: str,
    namespace: str,
    table_name: str,
    s3_url: str,
    uri: str,
    catalog_name: str = 's3tablescatalog',
    rest_signing_name: str = 's3tables',
    rest_sigv4_enabled: str = 'true',
) -> Dict:
    """Import data from a CSV file into an S3 table.

    This function reads data from a CSV file stored in S3 and imports it into an existing S3 table.
    If the table doesn't exist, it will be created using the schema inferred from the CSV file.

    Args:
        warehouse: Warehouse string for Iceberg catalog
        region: AWS region for S3Tables/Iceberg REST endpoint
        namespace: The namespace containing the table
        table_name: The name of the table to import data into
        s3_url: The S3 URL of the CSV file (format: s3://bucket-name/key)
        uri: REST URI for Iceberg catalog
        catalog_name: Catalog name
        rest_signing_name: REST signing name
        rest_sigv4_enabled: Enable SigV4 signing

    Returns:
        A dictionary containing:
        - status: 'success' or 'error'
        - message: Success message or error details
        - rows_processed: Number of rows processed (on success)
        - file_processed: Name of the processed file
        - table_created: Boolean indicating if a new table was created (on success)
    """
    # Parse S3 URL
    parsed = urlparse(s3_url)
    bucket = parsed.netloc
    key = parsed.path.lstrip('/')

    try:
        # Load Iceberg catalog
        catalog = pyiceberg_load_catalog(
            catalog_name,
            warehouse,
            uri,
            region,
            rest_signing_name,
            rest_sigv4_enabled,
        )

        # Get S3 client and read the CSV file to infer schema
        s3_client = get_s3_client()
        response = s3_client.get_object(Bucket=bucket, Key=key)
        csv_data = response['Body'].read()

        # Read CSV file into PyArrow Table to infer schema
        # Convert bytes to file-like object for PyArrow
        csv_buffer = io.BytesIO(csv_data)
        csv_table = pc.read_csv(csv_buffer)
        csv_schema = csv_table.schema

        table_created = False
        try:
            # Try to load existing table
            table = catalog.load_table(f'{namespace}.{table_name}')
        except NoSuchTableError:
            # Table doesn't exist, create it using the CSV schema
            try:
                table = catalog.create_table(
                    identifier=f'{namespace}.{table_name}',
                    schema=csv_schema,
                )
                table_created = True
            except Exception as create_error:
                return {
                    'status': 'error',
                    'error': f'Failed to create table: {str(create_error)}',
                }

        # Append data to Iceberg table
        table.append(csv_table)

        return {
            'status': 'success',
            'message': f'Successfully imported {csv_table.num_rows} rows{" and created new table" if table_created else ""}',
            'rows_processed': csv_table.num_rows,
            'file_processed': os.path.basename(key),
            'table_created': table_created,
            'table_uuid': table.metadata.table_uuid,
        }

    except Exception as e:
        return {'status': 'error', 'error': str(e)}
