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
from datetime import date, datetime, time
from decimal import Decimal
from pydantic import BaseModel
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

# pyiceberg and daft imports
from typing import Any, Dict, Optional


class PyIcebergConfig(BaseModel):
    """Configuration for PyIceberg/Daft connection."""

    warehouse: str  # e.g. 'arn:aws:s3tables:us-west-2:484907528679:bucket/customer-data-bucket'
    uri: str  # e.g. 'https://s3tables.us-west-2.amazonaws.com/iceberg'
    region: str  # e.g. 'us-west-2'
    namespace: str  # e.g. 'retail_data'
    catalog_name: str = 's3tablescatalog'  # default
    rest_signing_name: str = 's3tables'
    rest_sigv4_enabled: str = 'true'


def convert_value_for_append(value, iceberg_type):
    """Convert a value to the appropriate type for appending to an Iceberg table column.

    Args:
        value: The value to convert. Can be of various types (str, int, float, etc.).
        iceberg_type: The Iceberg type to convert the value to.

    Returns:
        The value converted to the appropriate type for the Iceberg column, or None if value is None.

    Raises:
        NotImplementedError: If the iceberg_type is a complex type (ListType, MapType, StructType).
        ValueError: If the conversion is unsupported or fails.
    """
    if value is None:
        return None
    # Already correct type
    if isinstance(iceberg_type, BooleanType) and isinstance(value, bool):
        return value
    if isinstance(iceberg_type, (IntegerType, LongType)) and isinstance(value, int):
        return value
    if isinstance(iceberg_type, (FloatType, DoubleType)) and isinstance(value, float):
        return value
    if isinstance(iceberg_type, DecimalType) and isinstance(value, Decimal):
        return value
    if isinstance(iceberg_type, DateType) and isinstance(value, date):
        return value
    if isinstance(iceberg_type, TimeType) and isinstance(value, time):
        return value
    if isinstance(iceberg_type, (TimestampType, TimestamptzType)) and isinstance(value, datetime):
        return value
    if isinstance(iceberg_type, StringType) and isinstance(value, str):
        return value
    # Convert from string
    if isinstance(value, str):
        if isinstance(iceberg_type, BooleanType):
            return value.lower() in ('true', '1', 'yes')
        if isinstance(iceberg_type, (IntegerType, LongType)):
            return int(value)
        if isinstance(iceberg_type, (FloatType, DoubleType)):
            return float(value)
        if isinstance(iceberg_type, DecimalType):
            return Decimal(value)
        if isinstance(iceberg_type, DateType):
            return date.fromisoformat(value)
        if isinstance(iceberg_type, TimeType):
            return time.fromisoformat(value)
        if isinstance(iceberg_type, (TimestampType, TimestamptzType)):
            return datetime.fromisoformat(value)
        if isinstance(iceberg_type, StringType):
            return value
        if isinstance(iceberg_type, UUIDType):
            import uuid

            return uuid.UUID(value)
        if isinstance(iceberg_type, (BinaryType, FixedType)):
            return bytes.fromhex(value)
    # Convert from number
    if isinstance(value, (int, float)):
        if isinstance(iceberg_type, (IntegerType, LongType)):
            return int(value)
        if isinstance(iceberg_type, (FloatType, DoubleType)):
            return float(value)
        if isinstance(iceberg_type, DecimalType):
            return Decimal(str(value))
        if isinstance(iceberg_type, StringType):
            return str(value)
    if isinstance(iceberg_type, (ListType, MapType, StructType)):
        raise NotImplementedError(f'Complex type {iceberg_type} not supported in append_rows')
    raise ValueError(f'Unsupported conversion from {type(value)} to {iceberg_type}')


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
            table = self._catalog.load_table(full_table_name)
            iceberg_schema = table.schema()
            converted_rows = []
            for row in rows:
                converted_row = {}
                for field in iceberg_schema.fields:
                    field_name = field.name
                    field_type = field.field_type
                    value = row.get(field_name)
                    if field.required and value is None:
                        raise ValueError(f'Required field {field_name} is missing or None')
                    try:
                        converted_row[field_name] = convert_value_for_append(value, field_type)
                    except (ValueError, TypeError) as e:
                        raise ValueError(
                            f'Error converting value for field {field_name}: {str(e)}'
                        )
                converted_rows.append(converted_row)
            schema = iceberg_schema.as_arrow()
            pa_table = pa.Table.from_pylist(converted_rows, schema=schema)
            table.append(pa_table)
        except Exception as e:
            raise Exception(f'Error appending rows: {str(e)}')
