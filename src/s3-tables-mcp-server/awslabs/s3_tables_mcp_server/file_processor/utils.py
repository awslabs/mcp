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

"""AWS S3 Tables MCP Server file processing utilities.

This module provides utility functions for file processing operations,
particularly focusing on column name conversion and schema transformation.
"""

import os
import pyarrow as pa
from ..utils import get_s3_client, pyiceberg_load_catalog
from io import BytesIO
from pydantic.alias_generators import to_snake
from pyiceberg.exceptions import NoSuchTableError
from typing import Any, Callable, Dict
from urllib.parse import urlparse


def convert_column_names_to_snake_case(schema: pa.Schema) -> pa.Schema:
    """Convert column names in PyArrow schema to snake_case.

    Args:
        schema: PyArrow schema with original column names

    Returns:
        PyArrow schema with converted column names

    Raises:
        ValueError: If duplicate column names exist after conversion
    """
    # Extract original column names
    original_names = schema.names

    # Convert each column name to snake_case
    converted_names = [to_snake(name) for name in original_names]

    # Check for duplicates after conversion using set and len
    if len(set(converted_names)) != len(converted_names):
        raise ValueError(
            f'Duplicate column names after case conversion. '
            f'Original names: {original_names}. Converted names: {converted_names}'
        )

    # Create new schema with converted column names
    new_fields = []
    for i, field in enumerate(schema):
        new_field = pa.field(
            converted_names[i], field.type, nullable=field.nullable, metadata=field.metadata
        )
        new_fields.append(new_field)

    return pa.schema(new_fields, metadata=schema.metadata)


async def import_file_to_table(
    warehouse: str,
    region: str,
    namespace: str,
    table_name: str,
    s3_url: str,
    uri: str,
    create_pyarrow_table: Callable[[Any], pa.Table],
    catalog_name: str = 's3tablescatalog',
    rest_signing_name: str = 's3tables',
    rest_sigv4_enabled: str = 'true',
    preserve_case: bool = False,
) -> Dict:
    """Import data from a file (CSV, Parquet, etc.) into an S3 table using a provided PyArrow table creation function."""
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

        # Get S3 client and read the file
        s3_client = get_s3_client()
        response = s3_client.get_object(Bucket=bucket, Key=key)
        file_bytes = response['Body'].read()

        # Create PyArrow Table and Schema (file-like interface)
        file_like = BytesIO(file_bytes)
        pyarrow_table = create_pyarrow_table(file_like)
        pyarrow_schema = pyarrow_table.schema

        # Convert column names to snake_case unless preserve_case is True
        columns_converted = False
        if not preserve_case:
            try:
                pyarrow_schema = convert_column_names_to_snake_case(pyarrow_schema)
                pyarrow_table = pyarrow_table.rename_columns(pyarrow_schema.names)
                columns_converted = True
            except Exception as conv_err:
                return {
                    'status': 'error',
                    'error': f'Column name conversion failed: {str(conv_err)}',
                }

        table_created = False
        try:
            # Try to load existing table
            table = catalog.load_table(f'{namespace}.{table_name}')
        except NoSuchTableError:
            # Table doesn't exist, create it using the schema
            try:
                table = catalog.create_table(
                    identifier=f'{namespace}.{table_name}',
                    schema=pyarrow_schema,
                )
                table_created = True
            except Exception as create_error:
                return {
                    'status': 'error',
                    'error': f'Failed to create table: {str(create_error)}',
                }

        # Append data to Iceberg table
        table.append(pyarrow_table)

        # Build message with warnings if applicable
        message = f'Successfully imported {pyarrow_table.num_rows} rows{" and created new table" if table_created else ""}'
        if columns_converted:
            message += '. WARNING: Column names were converted to snake_case format. To preserve the original case, set preserve_case to True.'

        return {
            'status': 'success',
            'message': message,
            'rows_processed': pyarrow_table.num_rows,
            'file_processed': os.path.basename(key),
            'table_created': table_created,
            'table_uuid': table.metadata.table_uuid,
            'columns': pyarrow_schema.names,
        }

    except Exception as e:
        return {'status': 'error', 'error': str(e)}
