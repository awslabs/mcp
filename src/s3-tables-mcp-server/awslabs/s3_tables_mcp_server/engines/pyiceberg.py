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
from pydantic import BaseModel

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

    def _convert_row_to_schema_types(self, row: dict, schema: pa.Schema) -> dict:
        # NOTE: PyArrow (and thus Iceberg) sometimes fails to infer date/timestamp types from string values like '2023-07-21T10:26:00'.
        # If a string is passed for a date or timestamp field, PyArrow may throw an error such as:
        #   Exception: Error appending rows: object of type <class 'str'> cannot be converted to int.
        # This is because PyArrow expects a native Python datetime.date or datetime.datetime object for date/timestamp fields.
        # To work around this, we explicitly convert string representations of dates/timestamps to the appropriate Python types.
        converted_row = {}
        for field_name, value in row.items():
            schema_field = None
            for field in schema:
                if field.name == field_name:
                    schema_field = field
                    break

            if schema_field is None:
                converted_row[field_name] = value
                continue

            try:
                field_type_str = str(schema_field.type)
                if field_type_str.startswith('date'):
                    if isinstance(value, str):
                        from datetime import datetime

                        converted_row[field_name] = datetime.strptime(value, '%Y-%m-%d').date()
                    else:
                        converted_row[field_name] = value
                elif field_type_str.startswith('timestamp'):
                    # Handle timestamp fields (e.g., timestamp[us], timestamp[ms], etc.)
                    if isinstance(value, str):
                        from datetime import datetime

                        try:
                            # Try parsing with microseconds first, then fallback
                            converted_row[field_name] = datetime.fromisoformat(value)
                        except ValueError:
                            # Try parsing without T separator
                            try:
                                converted_row[field_name] = datetime.strptime(
                                    value, '%Y-%m-%d %H:%M:%S'
                                )
                            except Exception:
                                converted_row[field_name] = value
                else:
                    converted_row[field_name] = value
            except Exception:
                converted_row[field_name] = value

        return converted_row

    def append_rows(self, table_name: str, rows: list[dict]) -> None:
        """Append rows to an Iceberg table using pyiceberg with automatic schema inference.

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

            # Retrieve the table schema as a PyArrow schema
            iceberg_pyarrow_schema = table.schema().as_arrow()

            # Convert data types to match schema
            converted_rows = []
            for i, row in enumerate(rows):
                converted_row = self._convert_row_to_schema_types(row, iceberg_pyarrow_schema)
                converted_rows.append(converted_row)

            # Create a PyArrow table from the new row data, enforcing the Iceberg schema
            # This step also acts as an explicit schema validation check
            try:
                new_data_table = pa.Table.from_pylist(
                    converted_rows, schema=iceberg_pyarrow_schema
                )
            except pa.ArrowInvalid as e:
                raise ValueError(
                    f'Schema mismatch detected: {e}. Please ensure your data matches the table schema.'
                )

            # Append the new data to the Iceberg table
            table.append(new_data_table)

        except Exception as e:
            raise Exception(f'Error appending rows: {str(e)}')
