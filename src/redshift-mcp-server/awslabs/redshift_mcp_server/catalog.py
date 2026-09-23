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

"""What a warehouse contains, asked of the warehouse itself with SHOW."""

from awslabs.redshift_mcp_server import redshift
from awslabs.redshift_mcp_server.models import (
    RedshiftColumn,
    RedshiftDatabase,
    RedshiftSchema,
    RedshiftTable,
)
from loguru import logger
from sqlglot import exp


# The SHOW statements discovery runs. Templated rather than parameterised, because the Data
# API's placeholders bind values and these positions are identifiers, which is why every one
# goes through _sql_identifier first. Their results are read by column name, so a column
# SHOW adds or reorders changes nothing and one it renames fails loudly.
_DATABASES_SQL = 'SHOW DATABASES;'
_SCHEMAS_SQL = 'SHOW SCHEMAS FROM DATABASE {database};'
_TABLES_SQL = 'SHOW TABLES FROM SCHEMA {database}.{schema};'
_COLUMNS_SQL = 'SHOW COLUMNS FROM TABLE {database}.{schema}.{table};'


def _sql_identifier(value: str) -> str:
    """Render a value as a Redshift SQL identifier, safely quoted and escaped."""
    return exp.to_identifier(value, quoted=True).sql(dialect='redshift')


async def discover_databases(
    cluster_identifier: str, database_name: str = 'dev'
) -> list[RedshiftDatabase]:
    """Discover databases in a Redshift cluster using the Data API.

    Args:
        cluster_identifier: The cluster identifier to query.
        database_name: The database to connect to for querying system views.

    Returns:
        List of RedshiftDatabase models.
    """
    try:
        logger.info(f'Discovering databases in cluster {cluster_identifier}')

        results_response, _ = await redshift.execute_standalone_statement(
            cluster_identifier=cluster_identifier,
            database_name=database_name,
            sql=_DATABASES_SQL,
            # This server's own SQL, so it does not police itself.
            enforce_read_only=False,
        )

        databases = RedshiftDatabase.from_redshift_response(results_response)
        logger.info(f'Found {len(databases)} databases in cluster {cluster_identifier}')
        return databases

    except Exception as e:
        logger.error(f'Error discovering databases in cluster {cluster_identifier}: {str(e)}')
        raise


async def discover_schemas(
    cluster_identifier: str, schema_database_name: str
) -> list[RedshiftSchema]:
    """Discover schemas in a Redshift database using the Data API.

    Args:
        cluster_identifier: The cluster identifier to query.
        schema_database_name: The database name to filter schemas for. Also used to connect to.

    Returns:
        List of RedshiftSchema models.
    """
    try:
        logger.info(
            f'Discovering schemas in database {schema_database_name} in cluster {cluster_identifier}'
        )

        results_response, _ = await redshift.execute_standalone_statement(
            cluster_identifier=cluster_identifier,
            database_name=schema_database_name,
            sql=_SCHEMAS_SQL.format(database=_sql_identifier(schema_database_name)),
            enforce_read_only=False,
        )

        schemas = RedshiftSchema.from_redshift_response(results_response)
        logger.info(
            f'Found {len(schemas)} schemas in database {schema_database_name} in cluster {cluster_identifier}'
        )
        return schemas

    except Exception as e:
        logger.error(
            f'Error discovering schemas in database {schema_database_name} in cluster {cluster_identifier}: {str(e)}'
        )
        raise


async def discover_tables(
    cluster_identifier: str, table_database_name: str, table_schema_name: str
) -> list[RedshiftTable]:
    """Discover tables in a Redshift schema using the Data API.

    Args:
        cluster_identifier: The cluster identifier to query.
        table_database_name: The database name to filter tables for. Also used to connect to.
        table_schema_name: The schema name to filter tables for.

    Returns:
        List of RedshiftTable models.
    """
    try:
        logger.info(
            f'Discovering tables in schema {table_schema_name} in database {table_database_name} in cluster {cluster_identifier}'
        )

        results_response, _ = await redshift.execute_standalone_statement(
            cluster_identifier=cluster_identifier,
            database_name=table_database_name,
            sql=_TABLES_SQL.format(
                database=_sql_identifier(table_database_name),
                schema=_sql_identifier(table_schema_name),
            ),
            enforce_read_only=False,
        )

        tables = RedshiftTable.from_redshift_response(results_response)
        logger.info(
            f'Found {len(tables)} tables in schema {table_schema_name} in database {table_database_name} in cluster {cluster_identifier}'
        )
        return tables

    except Exception as e:
        logger.error(
            f'Error discovering tables in schema {table_schema_name} in database {table_database_name} in cluster {cluster_identifier}: {str(e)}'
        )
        raise


async def discover_columns(
    cluster_identifier: str,
    column_database_name: str,
    column_schema_name: str,
    column_table_name: str,
) -> list[RedshiftColumn]:
    """Discover columns in a Redshift table using the Data API.

    Args:
        cluster_identifier: The cluster identifier to query.
        column_database_name: The database name to filter columns for. Also used to connect to.
        column_schema_name: The schema name to filter columns for.
        column_table_name: The table name to filter columns for.

    Returns:
        List of RedshiftColumn models.
    """
    try:
        logger.info(
            f'Discovering columns in table {column_table_name} in schema {column_schema_name} in database {column_database_name} in cluster {cluster_identifier}'
        )

        results_response, _ = await redshift.execute_standalone_statement(
            cluster_identifier=cluster_identifier,
            database_name=column_database_name,
            sql=_COLUMNS_SQL.format(
                database=_sql_identifier(column_database_name),
                schema=_sql_identifier(column_schema_name),
                table=_sql_identifier(column_table_name),
            ),
            enforce_read_only=False,
        )

        columns = RedshiftColumn.from_redshift_response(results_response)
        logger.info(
            f'Found {len(columns)} columns in table {column_table_name} in schema {column_schema_name} in database {column_database_name} in cluster {cluster_identifier}'
        )
        return columns

    except Exception as e:
        logger.error(
            f'Error discovering columns in table {column_table_name} in schema {column_schema_name} in database {column_database_name} in cluster {cluster_identifier}: {str(e)}'
        )
        raise
