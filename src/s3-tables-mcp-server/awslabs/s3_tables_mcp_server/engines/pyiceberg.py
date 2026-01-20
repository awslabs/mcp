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

"""Engine for interacting with Iceberg tables using pyiceberg and daft (read-only)."""

import pyarrow as pa
from ..utils import pyiceberg_load_catalog
from daft import Catalog as DaftCatalog
from daft.session import Session
from datetime import datetime
from pydantic import BaseModel

# pyiceberg and daft imports
from typing import Any, Dict, Optional


def convert_temporal_fields(rows: list[dict], arrow_schema: pa.Schema) -> list[dict]:
    """Convert string temporal fields to appropriate datetime objects based on Arrow schema.

    Args:
        rows: List of row dictionaries with string temporal values
        arrow_schema: PyArrow schema defining field types

    Returns:
        List of row dictionaries with converted temporal values
    """
    converted_rows = []

    for row in rows:
        converted_row = {}
        for field_name, value in row.items():
            # Early skip for non-string values
            if not isinstance(value, str):
                converted_row[field_name] = value
                continue

            # Get the field type from schema
            field = arrow_schema.field(field_name)
            field_type = field.type

            # Date32 or Date64 - calendar date without timezone or time
            if pa.types.is_date(field_type):
                # Format: "2025-03-14"
                converted_row[field_name] = datetime.strptime(value, '%Y-%m-%d').date()

            # Time64 - time of day, microsecond precision, without date or timezone
            elif pa.types.is_time(field_type):
                # Format: "17:10:34.123456" or "17:10:34"
                fmt = '%H:%M:%S.%f' if '.' in value else '%H:%M:%S'
                converted_row[field_name] = datetime.strptime(value, fmt).time()

            # Timestamp without timezone
            elif pa.types.is_timestamp(field_type) and field_type.tz is None:
                # Format: "2025-03-14 17:10:34.123456" or "2025-03-14T17:10:34.123456"
                value_normalized = value.replace('T', ' ')
                if '.' in value_normalized:
                    # Truncate nanoseconds to microseconds if needed
                    parts = value_normalized.split('.')
                    if len(parts[1]) > 6:
                        value_normalized = f'{parts[0]}.{parts[1][:6]}'
                    fmt = '%Y-%m-%d %H:%M:%S.%f'
                else:
                    fmt = '%Y-%m-%d %H:%M:%S'
                converted_row[field_name] = datetime.strptime(value_normalized, fmt)

            # Timestamp with timezone (stored in UTC)
            elif pa.types.is_timestamp(field_type) and field_type.tz is not None:
                # Format: "2025-03-14 17:10:34.123456-07" or "2025-03-14T17:10:34.123456+00:00"
                value_normalized = value.replace('T', ' ')
                from datetime import timezone

                # Truncate nanoseconds to microseconds if present
                if '.' in value_normalized:
                    # Split on timezone indicator (+ or -)
                    # Find the last occurrence of + or - which should be the timezone
                    tz_idx = max(value_normalized.rfind('+'), value_normalized.rfind('-'))
                    if tz_idx > 10:  # Make sure it's not the date separator
                        timestamp_part = value_normalized[:tz_idx]
                        tz_part = value_normalized[tz_idx:]

                        # Truncate fractional seconds to 6 digits
                        if '.' in timestamp_part:
                            parts = timestamp_part.split('.')
                            if len(parts[1]) > 6:
                                timestamp_part = f'{parts[0]}.{parts[1][:6]}'

                        value_normalized = timestamp_part + tz_part

                # Try different timezone formats
                for fmt in [
                    '%Y-%m-%d %H:%M:%S.%f%z',
                    '%Y-%m-%d %H:%M:%S%z',
                    '%Y-%m-%d %H:%M:%S.%f',
                    '%Y-%m-%d %H:%M:%S',
                ]:
                    try:
                        dt = datetime.strptime(value_normalized, fmt)
                        if dt.tzinfo is None:
                            dt = dt.replace(tzinfo=timezone.utc)
                        converted_row[field_name] = dt.astimezone(timezone.utc)
                        break
                    except ValueError:
                        continue
                else:
                    raise ValueError(
                        f'Could not parse timestamp with timezone: {value} for field {field_name}'
                    )

            else:
                # Not a temporal field, keep as is
                converted_row[field_name] = value

        converted_rows.append(converted_row)

    return converted_rows


class PyIcebergConfig(BaseModel):
    """Configuration for PyIceberg/Daft connection."""

    warehouse: str  # e.g. 'arn:aws:s3tables:us-west-2:484907528679:bucket/customer-data-bucket'
    uri: str  # e.g. 'https://s3tables.us-west-2.amazonaws.com/iceberg'
    region: str  # e.g. 'us-west-2'
    namespace: str  # e.g. 'retail_data'
    catalog_name: str = 's3tablescatalog'  # default
    rest_signing_name: str = 's3tables'
    rest_sigv4_enabled: str = 'true'


class PyIcebergEngine:
    """Engine for read-only queries on Iceberg tables using pyiceberg and daft."""

    def __init__(self, config: PyIcebergConfig):
        """Initialize the PyIcebergEngine with the given configuration.

        Args:
            config: PyIcebergConfig object containing connection parameters.
        """
        self.config = config
        self._catalog: Optional[Any] = None
        self._session: Optional[Session] = None
        self._initialize_connection()

    def _initialize_connection(self):
        try:
            self._catalog = pyiceberg_load_catalog(
                self.config.catalog_name,
                self.config.warehouse,
                self.config.uri,
                self.config.region,
                self.config.rest_signing_name,
                self.config.rest_sigv4_enabled,
            )
            self._session = Session()
            self._session.attach(DaftCatalog.from_iceberg(self._catalog))
            self._session.set_namespace(self.config.namespace)
        except Exception as e:
            raise ConnectionError(f'Failed to initialize PyIceberg connection: {str(e)}')

    def execute_query(self, query: str) -> Dict[str, Any]:
        """Execute a SQL query against the Iceberg catalog using Daft.

        Args:
            query: SQL query to execute

        Returns:
            Dict containing:
                - columns: List of column names
                - rows: List of rows, where each row is a list of values
        """
        if not self._session:
            raise ConnectionError('No active session for PyIceberg/Daft')
        try:
            result = self._session.sql(query)
            if result is None:
                raise Exception('Query execution returned None result')
            df = result.collect()
            columns = df.column_names
            rows = df.to_pylist()
            return {
                'columns': columns,
                'rows': [list(row.values()) for row in rows],
            }
        except Exception as e:
            raise Exception(f'Error executing query: {str(e)}')

    def test_connection(self) -> bool:
        """Test the connection by listing namespaces."""
        if not self._session:
            return False
        try:
            _ = self._session.list_namespaces()
            return True
        except Exception:
            return False

    def append_rows(self, table_name: str, rows: list[dict]) -> None:
        """Append rows to an Iceberg table using pyiceberg.

        Args:
            table_name: The name of the table (e.g., 'namespace.tablename' or just 'tablename' if namespace is set)
            rows: List of dictionaries, each representing a row to append

        Raises:
            Exception: If appending fails
        """
        if not self._catalog:
            raise ConnectionError('No active catalog for PyIceberg')
        try:
            # If table_name does not contain a dot, prepend the namespace
            if '.' not in table_name:
                full_table_name = f'{self.config.namespace}.{table_name}'
            else:
                full_table_name = table_name

            # Load the Iceberg table
            table = self._catalog.load_table(full_table_name)

            # Convert Iceberg schema to Arrow schema to ensure types/order match
            arrow_schema = table.schema().as_arrow()

            # Convert temporal fields from strings to datetime objects
            converted_rows = convert_temporal_fields(rows, arrow_schema)

            # Create PyArrow table directly from pylist with schema validation
            try:
                pa_table = pa.Table.from_pylist(converted_rows, schema=arrow_schema)
            except pa.ArrowInvalid as e:
                raise ValueError(
                    f'Schema mismatch detected: {e}. Please ensure your data matches the table schema.'
                )

            # Append the PyArrow table to the Iceberg table
            table.append(pa_table)

        except Exception as e:
            raise Exception(f'Error appending rows: {str(e)}')
