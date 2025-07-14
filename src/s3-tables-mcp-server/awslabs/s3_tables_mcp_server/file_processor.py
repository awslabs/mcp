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
particularly focusing on CSV file handling and preview capabilities.
"""

import csv
import os
import pyarrow as pa
import re
import uuid
from .utils import get_s3_client, pyiceberg_load_catalog
from datetime import date, datetime, time
from decimal import Decimal
from io import StringIO
from pyiceberg.types import (
    BinaryType,
    BooleanType,
    DateType,
    DecimalType,
    DoubleType,
    FixedType,
    FloatType,
    IntegerType,
    ListType,
    LongType,
    MapType,
    StringType,
    StructType,
    TimestampType,
    TimestamptzType,
    TimeType,
    UUIDType,
)
from typing import Dict, List, Optional
from urllib.parse import urlparse


def validate_s3_url(s3_url: str) -> tuple[bool, Optional[str], Optional[str], Optional[str]]:
    """Validate an S3 URL and extract its components.

    Args:
        s3_url: The S3 URL to validate (format: s3://bucket-name/key)

    Returns:
        Tuple containing:
        - bool: Whether the URL is valid
        - str: Error message if invalid, None if valid
        - str: Bucket name if valid, None if invalid
        - str: Object key if valid, None if invalid
    """
    try:
        parsed = urlparse(s3_url)
        if parsed.scheme != 's3':
            return False, f"Invalid URL scheme: {parsed.scheme}. Must be 's3://'", None, None

        if not parsed.netloc:
            return False, 'Missing bucket name in S3 URL', None, None

        bucket = parsed.netloc
        key = parsed.path.lstrip('/')

        if not key:
            return False, 'Missing object key in S3 URL', None, None

        return True, None, bucket, key
    except Exception as e:
        return False, f'Error parsing S3 URL: {str(e)}', None, None


def preview_csv_structure(s3_url: str) -> Dict:
    """Preview the structure of a CSV file stored in S3 by reading its headers and first row.

    This function provides a quick preview of a CSV file's structure by reading
    only the headers and first row of data from an S3 location. It's useful for
    understanding the schema and data format without downloading the entire file.

    Args:
        s3_url: The S3 URL of the CSV file (format: s3://bucket-name/key)

    Returns:
        A dictionary containing:
        - headers: List of column names from the first row
        - first_row: Dictionary mapping column names to their values from the first data row (empty if no data)
        - total_columns: Number of columns in the CSV
        - file_name: Name of the CSV file

    Returns error dictionary with status and error message if:
        - URL is not a valid S3 URL
        - File is not a CSV file
        - File cannot be accessed
        - Any other error occurs
    """
    try:
        # Validate S3 URL
        is_valid, error_msg, bucket, key = validate_s3_url(s3_url)
        if not is_valid:
            return {'status': 'error', 'error': error_msg}

        # At this point, bucket and key are guaranteed to be non-None strings
        if bucket is None or key is None:
            return {'status': 'error', 'error': 'Invalid S3 URL: bucket or key is None'}

        # Check if file has .csv extension
        if not key.lower().endswith('.csv'):
            return {
                'status': 'error',
                'error': f'File {key} is not a CSV file. Only .csv files are supported.',
            }

        # Get S3 client
        s3_client = get_s3_client()

        # Get the object from S3, only downloading first 8KB (should be enough for headers and first row)
        response = s3_client.get_object(
            Bucket=bucket,
            Key=key,
            Range='bytes=0-32768',  # First 32KB
        )

        # Read the CSV content
        csv_content = response['Body'].read().decode('utf-8')

        # Split content into lines
        lines = csv_content.splitlines()
        if not lines:
            return {'status': 'error', 'error': 'File is empty'}

        # Parse the headers
        headers = next(csv.reader([lines[0]]), [])

        # Try to get first row if it exists
        first_row = next(csv.reader([lines[1]]), []) if len(lines) > 1 else []

        # Create a dictionary mapping headers to first row values
        first_row_dict = dict(zip(headers, first_row)) if headers and first_row else {}

        return {
            'headers': headers,
            'first_row': first_row_dict,
            'total_columns': len(headers),
            'file_name': os.path.basename(key),
        }
    except Exception as e:
        return {'status': 'error', 'error': str(e)}


def convert_value(value: Optional[str], iceberg_type):
    """Convert a string value to the appropriate type based on Iceberg schema type.

    Args:
        value: The string value to convert (can be None)
        iceberg_type: The Iceberg type to convert to

    Returns:
        The converted value of the appropriate type

    Raises:
        ValueError: If the value cannot be converted to the target type
        NotImplementedError: For unsupported complex types
    """
    if value is None or value == '':
        return None

    if isinstance(iceberg_type, BooleanType):
        return value.lower() in ('true', '1', 'yes')

    elif isinstance(iceberg_type, IntegerType):
        return int(value)

    elif isinstance(iceberg_type, LongType):
        return int(value)

    elif isinstance(iceberg_type, FloatType):
        return float(value)

    elif isinstance(iceberg_type, DoubleType):
        return float(value)

    elif isinstance(iceberg_type, DecimalType):
        return Decimal(value)

    elif isinstance(iceberg_type, DateType):
        return date.fromisoformat(value)

    elif isinstance(iceberg_type, TimeType):
        return time.fromisoformat(value)

    elif isinstance(iceberg_type, TimestampType):
        return datetime.fromisoformat(value)

    elif isinstance(iceberg_type, TimestamptzType):
        return datetime.fromisoformat(value)  # Ensure it's tz-aware if needed

    elif isinstance(iceberg_type, StringType):
        return str(value)

    elif isinstance(iceberg_type, UUIDType):
        return uuid.UUID(value)

    elif isinstance(iceberg_type, BinaryType) or isinstance(iceberg_type, FixedType):
        return bytes.fromhex(value)

    elif isinstance(iceberg_type, ListType):
        # naive split for example; you'd want better parsing logic
        return [convert_value(v.strip(), iceberg_type.element_type) for v in value.split(',')]

    elif isinstance(iceberg_type, MapType):
        # naive: "key1:value1,key2:value2"
        return {
            k.strip(): convert_value(v.strip(), iceberg_type.value_type)
            for k, v in (item.split(':') for item in value.split(','))
        }

    elif isinstance(iceberg_type, StructType):
        raise NotImplementedError('Nested structs need structured input like JSON or dict.')

    else:
        raise ValueError(f'Unsupported Iceberg type: {iceberg_type}')


def create_pyarrow_schema_from_iceberg(schema) -> pa.Schema:
    """Create a PyArrow schema from an Iceberg schema, supporting basic types and decimals."""

    def convert_iceberg_type_to_pyarrow(iceberg_type_str: str):
        """Convert an Iceberg type string to a PyArrow type."""
        iceberg_type_str = iceberg_type_str.lower()

        if iceberg_type_str == 'boolean':
            return pa.bool_()
        elif iceberg_type_str == 'int':
            return pa.int32()
        elif iceberg_type_str == 'long':
            return pa.int64()
        elif iceberg_type_str == 'float':
            return pa.float32()
        elif iceberg_type_str == 'double':
            return pa.float64()
        elif iceberg_type_str == 'date':
            return pa.date32()
        elif iceberg_type_str == 'time':
            return pa.time64('us')
        elif iceberg_type_str == 'timestamp':
            return pa.timestamp('us')
        elif iceberg_type_str == 'timestamptz':
            return pa.timestamp('us', tz='UTC')
        elif iceberg_type_str == 'string':
            return pa.string()
        elif iceberg_type_str == 'uuid':
            return pa.string()
        elif iceberg_type_str == 'binary':
            return pa.binary()
        elif iceberg_type_str.startswith('fixed'):
            size_match = re.match(r'fixed\((\d+)\)', iceberg_type_str)
            return pa.binary(int(size_match.group(1))) if size_match else pa.binary()
        elif iceberg_type_str.startswith('decimal'):
            decimal_match = re.match(r'decimal\((\d+),\s*(\d+)\)', iceberg_type_str)
            if decimal_match:
                precision = int(decimal_match.group(1))
                scale = int(decimal_match.group(2))
                if precision <= 18:
                    return pa.decimal128(
                        precision, scale
                    )  # Will use INT64 encoding for small precision
                else:
                    return pa.decimal256(precision, scale)  # For large precision decimals
            else:
                raise ValueError(f'Invalid decimal type format: {iceberg_type_str}')
        else:
            raise ValueError(f'Unsupported Iceberg type: {iceberg_type_str}')

    # Build PyArrow schema
    pa_fields = []
    for field in schema.fields:
        name = field.name
        iceberg_type_str = str(field.field_type)
        try:
            pa_type = convert_iceberg_type_to_pyarrow(iceberg_type_str)
        except ValueError as e:
            raise ValueError(f"Error in field '{name}': {e}")

        pa_fields.append(pa.field(name, pa_type, nullable=not field.required))

    return pa.schema(pa_fields)


def process_chunk(chunk: List[Dict], table, chunk_name: str = 'Chunk') -> Dict:
    """Process a chunk of data by converting it to a PyArrow table and appending to the table.

    Args:
        chunk: List of dictionaries representing the data rows
        table: The Iceberg table to append data to
        chunk_name: Name identifier for the chunk (for logging purposes)

    Returns:
        Dictionary with status and message
    """
    try:
        # Get the Iceberg schema and create PyArrow schema
        schema = table.schema()
        pyarrow_schema = create_pyarrow_schema_from_iceberg(schema)

        # Convert list of dictionaries to PyArrow table with proper schema
        table_data = pa.Table.from_pylist(chunk, schema=pyarrow_schema)

        table.append(table_data)

        return {
            'status': 'success',
            'message': f'Successfully processed {len(chunk)} rows in {chunk_name.lower()}',
        }

    except Exception as e:
        return {'status': 'error', 'error': f'Error inserting {chunk_name.lower()}: {str(e)}'}


async def import_csv_to_table(
    warehouse: str,
    region: str,
    namespace: str,
    table_name: str,
    s3_url: str,
    uri: str = 'https://s3tables.us-west-2.amazonaws.com/iceberg',
    catalog_name: str = 's3tablescatalog',
    rest_signing_name: str = 's3tables',
    rest_sigv4_enabled: str = 'true',
) -> Dict:
    """Import data from a CSV file into an S3 table.

    This function reads data from a CSV file stored in S3 and imports it into an existing S3 table.
    The CSV file must have headers that match the table's schema. The function will validate the CSV structure
    before attempting to import the data.

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
        - csv_headers: List of CSV headers

    Returns error dictionary with status and error message if:
        - URL is not a valid S3 URL
        - File is not a CSV file
        - File cannot be accessed
        - Table does not exist
        - CSV headers don't match table schema
        - Any other error occurs
    """
    # Validate S3 URL
    is_valid, error_msg, bucket, key = validate_s3_url(s3_url)
    if not is_valid:
        return {'status': 'error', 'error': error_msg}

    if bucket is None or key is None:
        return {'status': 'error', 'error': 'Invalid S3 URL: bucket or key is None'}

    if not key.lower().endswith('.csv'):
        return {
            'status': 'error',
            'error': f'File {key} is not a CSV file. Only .csv files are supported.',
        }

    try:
        # Load catalog using provided parameters (see pyiceberg.py style)
        catalog = pyiceberg_load_catalog(
            catalog_name,
            warehouse,
            uri,
            region,
            rest_signing_name,
            rest_sigv4_enabled,
        )

        # Load existing table
        table = catalog.load_table(f'{namespace}.{table_name}')

        # Get schema information
        schema = table.schema()

        # Get S3 client
        s3_client = get_s3_client()

        # Get the CSV file from S3
        response = s3_client.get_object(Bucket=bucket, Key=key)
        csv_content = response['Body'].read().decode('utf-8')

        # Read CSV content
        csv_reader = csv.DictReader(StringIO(csv_content))

        # Validate headers against schema
        csv_headers = csv_reader.fieldnames
        schema_field_names = {field.name for field in schema.fields}

        if not csv_headers:
            return {'status': 'error', 'error': 'CSV file has no headers'}

        missing_columns = schema_field_names - set(csv_headers)
        if missing_columns:
            return {
                'status': 'error',
                'error': f'CSV is missing required columns: {", ".join(missing_columns)}',
            }

        # Process rows in chunks
        chunk_size = 5000
        rows_processed = 0
        current_chunk = []

        for row in csv_reader:
            # Transform row data according to schema types
            transformed_row = {}
            for field in schema.fields:
                value = row.get(field.name)

                # Handle required fields
                if field.required and (value is None or value == ''):
                    return {
                        'status': 'error',
                        'error': f'Required field {field.name} is missing or empty in row {rows_processed + 1}',
                    }

                # Transform value based on field type
                try:
                    if value is None or value == '':
                        transformed_row[field.name] = None
                    else:
                        transformed_row[field.name] = convert_value(value, field.field_type)
                except (ValueError, TypeError) as e:
                    return {
                        'status': 'error',
                        'error': f'Error converting value for field {field.name} in row {rows_processed + 1}: {str(e)}',
                    }

            current_chunk.append(transformed_row)
            rows_processed += 1

            # Process chunk when it reaches the chunk size
            if len(current_chunk) >= chunk_size:
                result = process_chunk(current_chunk, table, 'Chunk')
                if result['status'] == 'error':
                    return result
                current_chunk = []

        # Process any remaining rows
        if current_chunk:
            result = process_chunk(current_chunk, table, 'Final Chunk')
            if result['status'] == 'error':
                return result

        return {
            'status': 'success',
            'message': f'Successfully processed {rows_processed} rows',
            'rows_processed': rows_processed,
            'file_processed': os.path.basename(key),
            'csv_headers': csv_headers,
        }

    except Exception as e:
        return {'status': 'error', 'error': str(e)}
