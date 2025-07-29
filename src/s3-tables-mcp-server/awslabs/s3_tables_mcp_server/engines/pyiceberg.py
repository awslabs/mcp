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

import io
import json
import pyarrow as pa
import pyarrow.json as pj
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

    def append_rows(self, table_name: str, rows: list[dict]) -> None:
        """Append rows to an Iceberg table using pyiceberg with JSON encoding.

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
            # Encode rows as JSON (line-delimited format)
            json_lines = []
            for row in rows:
                json_lines.append(json.dumps(row))
            json_data = '\n'.join(json_lines)

            # Create a file-like object from the JSON data
            json_buffer = io.BytesIO(json_data.encode('utf-8'))

            # Read JSON data into PyArrow Table using pyarrow.json.read_json
            # This enforces the Iceberg schema and validates the data
            try:
                new_data_table = pj.read_json(
                    json_buffer, read_options=pj.ReadOptions(use_threads=True)
                )
            except pa.ArrowInvalid as e:
                raise ValueError(
                    f'Schema mismatch detected: {e}. Please ensure your data matches the table schema.'
                )

            # Append the new data to the Iceberg table
            table.append(new_data_table)

        except Exception as e:
            raise Exception(f'Error appending rows: {str(e)}')
