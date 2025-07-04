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

"""Table schema analysis tools."""

from ..connection.base_connection import DBConnector
from loguru import logger
from typing import Any, Dict, List


async def get_table_schema(
    connection: DBConnector,
    table_name: str
) -> List[Dict[str, Any]]:
    """
    Get a table's schema information given the table name.

    Args:
        connection: Database connection instance
        table_name: Name of the table to analyze

    Returns:
        List of dictionaries containing column information
    """
    logger.info(f'get_table_schema: {table_name}')

    # Use parameterized query to prevent SQL injection
    sql = """
        SELECT
            a.attname AS column_name,
            pg_catalog.format_type(a.atttypid, a.atttypmod) AS data_type,
            col_description(a.attrelid, a.attnum) AS column_comment,
            NOT a.attnotnull AS is_nullable,
            pg_get_expr(d.adbin, d.adrelid) AS column_default
        FROM
            pg_attribute a
        LEFT JOIN pg_attrdef d ON a.attrelid = d.adrelid AND a.attnum = d.adnum
        WHERE
            a.attrelid = to_regclass(:table_name)
            AND a.attnum > 0
            AND NOT a.attisdropped
        ORDER BY a.attnum
    """

    try:
        # Execute query with parameterized approach
        params = [{'name': 'table_name', 'value': {'stringValue': table_name}}]
        response = await connection.execute_query(sql, params)

        # Parse response based on connection type
        if connection.connection_info['type'] == 'rds_data_api':
            # RDS Data API response format
            columns = [col['name'] for col in response.get('columnMetadata', [])]
            records = []

            for row in response.get('records', []):
                row_data = {}
                for col, cell in zip(columns, row):
                    if cell.get('isNull'):
                        row_data[col] = None
                    else:
                        # Extract value from cell
                        for key in ('stringValue', 'longValue', 'doubleValue',
                                   'booleanValue', 'blobValue'):
                            if key in cell:
                                row_data[col] = cell[key]
                                break
                records.append(row_data)

            return records
        else:
            # Direct PostgreSQL connection - ensure we return a list
            if isinstance(response, list):
                return response
            else:
                return [response] if response else []

    except Exception as e:
        logger.exception(f"Error fetching table schema for {table_name}")
        raise Exception(f"Failed to fetch table schema: {str(e)}")
