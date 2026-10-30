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

"""AWS S3 Storage Lens tools for the AWS Billing and Cost Management MCP server.

This module provides functionality to create and query Athena tables for S3 Storage Lens data.
The storage-lens tool description lists the export columns and sample queries.
"""

import asyncio
import json
import os
import re
import sqlglot
import weakref
from ..utilities.aws_service_base import create_aws_client, format_response, handle_aws_error
from ..utilities.constants import (
    ATHENA_MAX_RETRIES,
    ATHENA_RETRY_DELAY_SECONDS,
    ENV_STORAGE_LENS_MANIFEST_LOCATION,
    ENV_STORAGE_LENS_OUTPUT_LOCATION,
    STORAGE_LENS_DEFAULT_DATABASE,
    STORAGE_LENS_DEFAULT_TABLE,
)
from datetime import datetime
from enum import Enum
from fastmcp import Context, FastMCP
from sqlglot import exp
from sqlglot.errors import SqlglotError
from typing import Any, Dict, List, Optional, TypedDict
from urllib.parse import urlparse


# FastMCP server instance
storage_lens_server = FastMCP(
    name='storage-lens-tools', instructions='Tools for working with AWS S3 Storage Lens data'
)


def validate_query_is_readonly_select(query: str) -> str | None:
    """Validate that a user-supplied query is a read-only SELECT or WITH...SELECT.

    Returns None if valid, or an error message string if invalid.
    """
    # Substitute {table} placeholder with a valid identifier for parsing
    parseable = query.replace('{table}', '__placeholder_table__')
    try:
        statements = sqlglot.parse(parseable, read='trino')
    except SqlglotError as e:
        return f'Query validation failed: unable to parse SQL: {e}'
    if not statements:
        return 'Query validation failed: empty query.'
    if len(statements) > 1:
        return 'Query validation failed: multiple statements are not allowed.'
    stmt = statements[0]
    if stmt is None:
        return 'Query validation failed: unable to parse SQL statement.'
    # Only allow top-level SELECT (which includes WITH...SELECT CTEs)
    if stmt.key != 'select':
        return f'Query validation failed: only SELECT queries are allowed, got {stmt.key.upper()}.'
    # Scan for any DDL/DML nested in CTE definitions
    _FORBIDDEN = {
        'create',
        'drop',
        'alter',
        'insert',
        'update',
        'delete',
        'merge',
        'grant',
        'revoke',
    }
    for node in stmt.walk():
        if node.key in _FORBIDDEN:
            return f'Query validation failed: {node.key.upper()} statements are not allowed.'
    return None


# Database and table names are written unquoted into Athena DDL and queries, so only a plain
# identifier is accepted: a letter, then letters, digits or underscores, at most 255 characters.
_ATHENA_NAME_PATTERN = re.compile(r'[A-Za-z][A-Za-z0-9_]{0,254}')


def validate_athena_name(arg_name: str, value: str) -> None:
    """Raise ValueError unless ``value`` is a plain Athena identifier."""
    if not isinstance(value, str) or not _ATHENA_NAME_PATTERN.fullmatch(value):
        shown = value[:64] if isinstance(value, str) else value
        raise ValueError(
            f'{arg_name} must start with a letter and contain only letters, digits and '
            f'underscores, at most 255 characters; got {shown!r}.'
        )


def references_qualified_table(query: str, database_name: str, table_name: str) -> bool:
    """Return True if the query reads the table as ``<database_name>.<table_name>``.

    Table references are read from the parsed SQL, so a name inside a string literal or a
    comment does not count, quoted identifiers do, and names are compared case-insensitively
    as Athena does. A catalog prefix other than Athena's default ``AwsDataCatalog`` names a
    different table and does not count.
    """
    try:
        statements = sqlglot.parse(query, read='trino')
    except SqlglotError:
        return False
    return any(
        table.name.lower() == table_name.lower()
        and table.db.lower() == database_name.lower()
        and table.catalog.lower() in ('', 'awsdatacatalog')
        for stmt in statements
        if stmt is not None
        for table in stmt.find_all(exp.Table)
    )


# Using constants from centralized constants.py file
# STORAGE_LENS_DEFAULT_DATABASE: Default database name for Storage Lens data
# STORAGE_LENS_DEFAULT_TABLE: Default table name for Storage Lens data
# ATHENA_MAX_RETRIES: Maximum number of retries for Athena query completion
# ATHENA_RETRY_DELAY_SECONDS: Delay between retries in seconds
# ENV_STORAGE_LENS_MANIFEST_LOCATION: Environment variable for S3 URI to manifest file
# ENV_STORAGE_LENS_OUTPUT_LOCATION: Environment variable for S3 location for Athena query results


# Schema format enum
class SchemaFormat(Enum):
    """Storage Lens data format."""

    CSV = 'CSV'
    PARQUET = 'PARQUET'


# Helper classes for typed data
class ColumnDefinition(TypedDict):
    """Column definition for Athena tables."""

    name: str
    type: str


class SchemaInfo(TypedDict):
    """Schema information for Storage Lens data."""

    format: SchemaFormat
    columns: List[ColumnDefinition]
    skip_header: bool


class ManifestFile(TypedDict):
    """Manifest file information."""

    key: str
    last_modified: datetime


class AthenaQueryExecution(TypedDict):
    """Athena query execution information."""

    query_execution_id: str
    status: str


class ManifestHandler:
    """Handler for S3 Storage Lens manifest files."""

    def __init__(self, ctx: Context):
        """Initialize the S3 client.

        Args:
            ctx: MCP context for logging
        """
        self.ctx = ctx
        self.s3_client = create_aws_client('s3')

    async def get_manifest(self, manifest_location: str) -> Dict[str, Any]:
        """Locate and parse the manifest file from S3.

        Args:
            manifest_location: S3 URI to manifest file or folder containing manifest files
                (e.g., 's3://bucket-name/path/to/manifest.json' or 's3://bucket-name/path/to/folder/')

        Returns:
            Dict[str, Any]: Parsed manifest JSON content
        """
        try:
            # Parse the S3 URI to get bucket and key
            parsed_uri = urlparse(manifest_location)
            bucket = parsed_uri.netloc
            key = parsed_uri.path.lstrip('/')

            await self.ctx.info(f'Looking for manifest at s3://{bucket}/{key}')

            if key.endswith('manifest.json'):
                return await self._read_manifest_file(bucket, key)
            else:
                return await self._find_latest_manifest(bucket, key)

        except Exception as e:
            await self.ctx.error(f'Failed to get manifest: {str(e)}')
            raise

    async def _read_manifest_file(self, bucket: str, key: str) -> Dict[str, Any]:
        """Read and parse a manifest file from S3.

        Args:
            bucket: S3 bucket name
            key: S3 object key for the manifest file

        Returns:
            Dict[str, Any]: Parsed manifest JSON content
        """
        try:
            response = self.s3_client.get_object(Bucket=bucket, Key=key)
            manifest_content = json.loads(response['Body'].read().decode('utf-8'))
            await self.ctx.info(f'Successfully read manifest file at s3://{bucket}/{key}')
            return manifest_content
        except Exception as e:
            await self.ctx.error(f'Failed to read manifest file at s3://{bucket}/{key}: {str(e)}')
            # Re-raise unwrapped so handle_aws_error keeps the AWS error code
            raise

    async def _find_latest_manifest(self, bucket: str, key: str) -> Dict[str, Any]:
        """Find the latest manifest.json file in the specified S3 location.

        Args:
            bucket: S3 bucket name
            key: S3 prefix to search for manifest files

        Returns:
            Dict[str, Any]: Parsed manifest JSON content
        """
        # Ensure key ends with a slash
        if not key.endswith('/'):
            key += '/'

        await self.ctx.info(f'Searching for manifest.json files in s3://{bucket}/{key}')

        try:
            # List objects with the prefix and filter for manifest.json files
            manifest_files = []

            # Use pagination to handle large directories
            paginator = self.s3_client.get_paginator('list_objects_v2')
            for page in paginator.paginate(Bucket=bucket, Prefix=key):
                if 'Contents' in page:
                    for obj in page['Contents']:
                        if obj['Key'].endswith('manifest.json'):
                            # Use the ManifestFile structure
                            manifest_file = ManifestFile(
                                key=obj['Key'], last_modified=obj['LastModified']
                            )
                            manifest_files.append(manifest_file)

            if not manifest_files:
                raise ValueError(f'No manifest.json files found at s3://{bucket}/{key}')

            # Sort by last modified date to get the latest
            latest_manifest = sorted(
                manifest_files, key=lambda x: x['last_modified'], reverse=True
            )[0]

            # Log only the selected latest manifest file
            await self.ctx.info(
                f'Selected latest manifest: s3://{bucket}/{latest_manifest["key"]} '
                f'(Last Modified: {latest_manifest["last_modified"]})'
            )

            # Get the content of the latest manifest file
            return await self._read_manifest_file(bucket, latest_manifest['key'])

        except Exception as e:
            await self.ctx.error(
                f'Failed to locate manifest file in s3://{bucket}/{key}: {str(e)}'
            )
            # Re-raise unwrapped so handle_aws_error keeps the AWS error code
            raise

    def extract_data_location(self, manifest: Dict[str, Any]) -> str:
        """Extract the S3 location of the data files from the manifest.

        Args:
            manifest: Parsed manifest JSON content

        Returns:
            str: S3 URI to the data files
        """
        report_files = manifest.get('reportFiles', [])

        if not report_files:
            raise ValueError('No report files found in manifest')

        # Determine the S3 location of the report files
        sample_file = report_files[0]['key']
        parsed_uri = urlparse(sample_file)

        if not parsed_uri.netloc:
            # If the key is relative, construct the full path
            destination_bucket = manifest.get('destinationBucket', '')
            if destination_bucket.startswith('arn:aws:s3:::'):
                bucket_name = destination_bucket.replace('arn:aws:s3:::', '')
            else:
                bucket_name = destination_bucket

            data_location = f's3://{bucket_name}/{sample_file}'
        else:
            data_location = sample_file

        # Return the directory containing the data files
        return '/'.join(data_location.split('/')[:-1])

    def parse_schema(self, manifest: Dict[str, Any]) -> SchemaInfo:
        """Parse the schema information from the manifest.

        Args:
            manifest: Parsed manifest JSON content

        Returns:
            SchemaInfo: Schema information including format, column definitions, etc.
        """
        report_format = manifest.get('reportFormat', 'CSV')
        report_schema = manifest.get('reportSchema', '')

        if report_format.upper() == 'CSV':
            # For CSV, the schema is a comma-separated list of column names
            columns = report_schema.split(',')
            column_definitions = []

            for column in columns:
                # Default to string type for all columns
                column_definitions.append(ColumnDefinition(name=column.strip(), type='STRING'))

            return SchemaInfo(
                format=SchemaFormat.CSV, columns=column_definitions, skip_header=True
            )
        else:  # Parquet format
            # For Parquet, we need to parse the message schema
            schema_str = report_schema

            # Extract field definitions from the Parquet message schema
            field_pattern = r'required\s+(\w+)\s+(\w+);'
            matches = re.findall(field_pattern, schema_str)

            column_definitions = []
            for match in matches:
                data_type, field_name = match
                # Map Parquet types to Athena types
                if data_type.lower() == 'string':
                    athena_type = 'STRING'
                elif data_type.lower() == 'long':
                    athena_type = 'BIGINT'
                elif data_type.lower() == 'double':
                    athena_type = 'DOUBLE'
                else:
                    athena_type = 'STRING'  # Default to STRING for unknown types

                column_definitions.append(ColumnDefinition(name=field_name, type=athena_type))

            return SchemaInfo(
                format=SchemaFormat.PARQUET, columns=column_definitions, skip_header=False
            )


# Column names come from the manifest's schema and are written backtick-quoted into the table DDL.
_COLUMN_NAME_PATTERN = re.compile(r'[A-Za-z_][A-Za-z0-9_]{0,254}')
# Input formats and SerDes of a CSV table, as Athena reports them (lowercase).
_CSV_FORMATS = ('textinputformat', 'lazysimpleserde', 'opencsvserde')


def _table_is_parquet(table_format: str) -> Optional[bool]:
    """True for a Parquet table, False for CSV, None when ``table_format`` is neither.

    ``table_format`` is the table's lowercase input format, else its SerDe. A symlink table lists
    data files rather than holding them, so it is neither.
    """
    if 'symlink' in table_format:
        return None
    if 'parquet' in table_format:
        return True
    if any(csv in table_format for csv in _CSV_FORMATS):
        return False
    return None


# The column types parse_schema produces.
_COLUMN_TYPES = frozenset({'STRING', 'BIGINT', 'DOUBLE'})
# A single day's Storage Lens report folder, the only LOCATION this tool has ever given a table:
# s3://<bucket>/[<prefix>/]StorageLens/<account or org>/<configuration>/V_<n>/reports/dt=<date>
_REPORT_FOLDER_PATTERN = re.compile(
    r's3://[^/]+/(?:.+/)?StorageLens/[^/]+/[^/]+/V_\d+/reports/dt=\d{4}-\d{2}-\d{2}/?'
)


def table_ddl_parts(schema_info: SchemaInfo, data_location: str) -> tuple[str, str]:
    """Return the column definitions and LOCATION literal for a CREATE TABLE statement.

    Both come from the manifest, which the caller chooses, so a column name must be a plain
    identifier, its type one of STRING, BIGINT or DOUBLE, and the location an s3:// URI with no
    quote or backslash; anything else raises ValueError rather than being written into the DDL.
    """
    for column in schema_info['columns']:
        if not _COLUMN_NAME_PATTERN.fullmatch(column['name']):
            raise ValueError(
                'Manifest schema column names must be letters, digits or underscores; got '
                f'{column["name"][:64]!r}.'
            )
        if column['type'] not in _COLUMN_TYPES:
            raise ValueError(
                f'Column types must be one of {", ".join(sorted(_COLUMN_TYPES))}; got '
                f'{str(column["type"])[:64]!r}.'
            )
    columns = ', '.join(
        f'`{column["name"]}` {column["type"]}' for column in schema_info['columns']
    )
    return columns, location_literal(data_location)


def location_literal(data_location: str) -> str:
    """Return the quoted LOCATION literal for data_location, an s3:// URI from the manifest.

    A location that is not an s3:// URI, or holds a quote or backslash, raises ValueError rather
    than being written into the DDL.
    """
    if not data_location.startswith('s3://') or any(c in data_location for c in "'\\"):
        raise ValueError(
            f'Manifest data location must be an s3:// URI without quotes or backslashes; got '
            f'{data_location[:128]!r}.'
        )
    return f"'{data_location}'"


# point_table_at moves a shared table's LOCATION, so two calls in this server for different days
# must not interleave one's ALTER with the other's SELECT. One lock per table and event loop
# serializes them; servers in separate processes that share a table are not covered.
_TABLE_LOCKS: 'weakref.WeakKeyDictionary[asyncio.AbstractEventLoop, Dict[str, asyncio.Lock]]' = (
    weakref.WeakKeyDictionary()
)


def table_lock(qualified_table: str) -> asyncio.Lock:
    """Return the lock that serializes setup and SELECT on ``qualified_table`` in this loop."""
    locks = _TABLE_LOCKS.setdefault(asyncio.get_running_loop(), {})
    key = qualified_table.lower()
    lock = locks.get(key)
    if lock is None:
        lock = locks[key] = asyncio.Lock()
    return lock


class AthenaHandler:
    """Handler for Athena operations on S3 Storage Lens data."""

    def __init__(self, ctx: Context):
        """Initialize the Athena client.

        Args:
            ctx: MCP context for logging
        """
        self.ctx = ctx
        # Create Athena client using shared utility function
        self.athena_client = create_aws_client('athena')

    async def create_database(self, database_name: str, output_location: str) -> None:
        """Create an Athena database if it doesn't exist.

        Args:
            database_name: Name of the database to create
            output_location: S3 location for query results
        """
        validate_athena_name('database_name', database_name)
        create_db_query = f'CREATE DATABASE IF NOT EXISTS {database_name}'
        await self.run_ddl(create_db_query, 'default', output_location)

    async def create_table_for_csv(
        self,
        database_name: str,
        table_name: str,
        schema_info: SchemaInfo,
        data_location: str,
        output_location: str,
    ) -> None:
        """Create an Athena table for CSV data.

        Args:
            database_name: Name of the database
            table_name: Name of the table to create
            schema_info: Schema information from manifest
            data_location: S3 location of the data files
            output_location: S3 location for query results
        """
        validate_athena_name('database_name', database_name)
        validate_athena_name('table_name', table_name)
        columns, location = table_ddl_parts(schema_info, data_location)

        create_table_query = f"""
        CREATE EXTERNAL TABLE IF NOT EXISTS {database_name}.{table_name} (
            {columns}
        )
        ROW FORMAT DELIMITED
        FIELDS TERMINATED BY ','
        STORED AS TEXTFILE
        LOCATION {location}
        TBLPROPERTIES ('skip.header.line.count'='1')
        """

        await self.run_ddl(create_table_query, database_name, output_location)

    async def create_table_for_parquet(
        self,
        database_name: str,
        table_name: str,
        schema_info: SchemaInfo,
        data_location: str,
        output_location: str,
    ) -> None:
        """Create an Athena table for Parquet data.

        Args:
            database_name: Name of the database
            table_name: Name of the table to create
            schema_info: Schema information from manifest
            data_location: S3 location of the data files
            output_location: S3 location for query results
        """
        validate_athena_name('database_name', database_name)
        validate_athena_name('table_name', table_name)
        columns, location = table_ddl_parts(schema_info, data_location)

        create_table_query = f"""
        CREATE EXTERNAL TABLE IF NOT EXISTS {database_name}.{table_name} (
            {columns}
        )
        STORED AS PARQUET
        LOCATION {location}
        """

        await self.run_ddl(create_table_query, database_name, output_location)

    async def setup_table(
        self,
        database_name: str,
        table_name: str,
        schema_info: SchemaInfo,
        data_location: str,
        output_location: str,
    ) -> None:
        """Set up an Athena table based on the schema information.

        Args:
            database_name: Name of the database
            table_name: Name of the table to create
            schema_info: Schema information from manifest
            data_location: S3 location of the data files
            output_location: S3 location for query results

        Raises:
            ValueError: If database_name or table_name is not a plain Athena identifier, or a
                manifest column name or the data location is unsafe to write into DDL
        """
        # Check everything written into the CREATE DATABASE / CREATE TABLE statements before
        # either is sent.
        validate_athena_name('database_name', database_name)
        validate_athena_name('table_name', table_name)
        table_ddl_parts(schema_info, data_location)
        await self.ctx.info(f'Setting up Athena table {database_name}.{table_name}')
        await self.ctx.info(f'Data location: {data_location}')
        await self.ctx.info(f'Schema format: {schema_info["format"]}')
        await self.ctx.info(f'Columns: {[col["name"] for col in schema_info["columns"]]}')

        # Create database if it doesn't exist
        await self.create_database(database_name, output_location)

        # Create table based on format
        if schema_info['format'] == SchemaFormat.CSV:
            await self.ctx.info('Creating table for CSV format')
            await self.create_table_for_csv(
                database_name, table_name, schema_info, data_location, output_location
            )
        else:  # Parquet format
            await self.ctx.info('Creating table for Parquet format')
            await self.create_table_for_parquet(
                database_name, table_name, schema_info, data_location, output_location
            )

        # CREATE TABLE IF NOT EXISTS leaves an existing table where it was, for example on an
        # earlier day's dt= folder, so point it at this manifest's folder when it reads another.
        await self.point_table_at(
            database_name, table_name, data_location, output_location, schema_info['format']
        )

    async def point_table_at(
        self,
        database_name: str,
        table_name: str,
        data_location: str,
        output_location: str,
        schema_format: SchemaFormat,
    ) -> None:
        """Set the table's LOCATION to data_location unless it already reads that folder.

        Only an unpartitioned table on another day's report folder, as this tool creates, is
        moved. Any other table (partitioned, with no location, or on a folder that is not a
        Storage Lens report day) was set up by someone else and is left as it is. A table already
        on the manifest's folder is still refused if it was created for the other report format.

        Args:
            database_name: Name of the database
            table_name: Name of the table
            data_location: S3 location of the data files the manifest describes
            output_location: S3 location for query results
            schema_format: Format of the manifest's report files

        Raises:
            ValueError: If the table is this tool's but the manifest's folder is not a report
                folder, or the table was created for the other report format (CSV or Parquet)
                or records no format
        """
        validate_athena_name('database_name', database_name)
        validate_athena_name('table_name', table_name)
        location = location_literal(data_location)
        metadata = self.athena_client.get_table_metadata(
            CatalogName='AwsDataCatalog', DatabaseName=database_name, TableName=table_name
        )
        table = metadata['TableMetadata']
        parameters = table.get('Parameters', {})
        current = parameters.get('location')
        name = f'{database_name}.{table_name}'
        # The table's SerDe stays as created, so CSV files read as Parquet (or the reverse) give
        # garbage rows; a different table_name gets a table of the right format. The SerDe decides
        # the format (TextInputFormat is shared by JSON, Regex and CSV tables); the input format
        # is used only without a SerDe, and must agree with it otherwise.
        serde = (parameters.get('serde.serialization.lib') or '').lower()
        input_format = (parameters.get('inputformat') or '').lower()
        table_format = serde or input_format
        table_is_parquet = _table_is_parquet(table_format)
        if serde and input_format and _table_is_parquet(input_format) != table_is_parquet:
            table_is_parquet = None
            table_format = f'{input_format} with {serde}'
        report_is_parquet = schema_format != SchemaFormat.CSV

        def format_mismatch(created_as_parquet: bool) -> ValueError:
            formats = {True: 'Parquet', False: 'CSV'}
            return ValueError(
                f'Table {name} was created for {formats[created_as_parquet]} report files, but '
                f"this manifest's report is {formats[report_is_parquet]}. Pass a different "
                'table_name.'
            )

        if current is not None and current.rstrip('/') == data_location.rstrip('/'):
            # Already on this report's folder; refuse only a format known to be the other one
            if table_is_parquet is not None and table_is_parquet != report_is_parquet:
                raise format_mismatch(table_is_parquet)
            return
        if table.get('PartitionKeys'):
            await self.ctx.info(f'Table {name} is partitioned; querying it as it is')
            return
        if current is None:
            await self.ctx.info(f'Table {name} has no location; querying it as it is')
            return
        if not _REPORT_FOLDER_PATTERN.fullmatch(current):
            await self.ctx.info(
                f'Table {name} reads {current}, not a Storage Lens report folder; querying it '
                'as it is'
            )
            return
        if not _REPORT_FOLDER_PATTERN.fullmatch(data_location):
            raise ValueError(
                f'Table {name} reads the Storage Lens report folder {current}, but the '
                f"manifest's report files are in {data_location}, which is not one "
                '(.../StorageLens/<id>/<configuration>/V_<n>/reports/dt=<date>). Pass a '
                'different table_name.'
            )
        # A table that is neither CSV nor Parquet (or records no format) is not moved
        if table_is_parquet is None:
            raise ValueError(
                f'Table {name} reads {current} but has no recognised report format (CSV or '
                f'Parquet; found {table_format or "none"}), so it is not pointed at '
                f'{data_location}. Pass a different table_name.'
            )
        if table_is_parquet != report_is_parquet:
            raise format_mismatch(table_is_parquet)
        await self.ctx.info(f'Table {name} reads {current}; pointing it at {data_location}')
        await self.run_ddl(
            f'ALTER TABLE {name} SET LOCATION {location}',
            database_name,
            output_location,
        )

    async def run_ddl(self, query: str, database_name: str, output_location: str) -> None:
        """Run a DDL statement and wait for it to finish, so the next statement sees its effect.

        Args:
            query: DDL statement to execute
            database_name: Athena database name to use
            output_location: S3 location for Athena query results
        """
        execution = await self.execute_query(query, database_name, output_location)
        # Long enough to keep an ALTER's whole target location in error messages
        statement = ' '.join(query.split())[:300]
        label = f'Athena table setup ({statement})'
        try:
            # The caller's query has not run yet, so a failed setup statement is not theirs to fix
            details = await self.wait_for_query_completion(
                execution['query_execution_id'],
                failure=RuntimeError,
                label=label,
            )
        except RuntimeError as e:
            # A concurrent call created the database or table between this statement's existence
            # check and its create, which leaves what this statement asked for.
            # Only Athena's reason counts: the label quotes the statement, which can hold any text
            reason = str(e).partition(f'{label} failed: ')[2]
            if 'IF NOT EXISTS' in query and 'already exists' in reason.lower():
                await self.ctx.info(f'{statement}: created concurrently by another query')
                return
            raise
        # Defensive: wait_for_query_completion returns only a SUCCEEDED execution or raises
        state = details.get('Status', {}).get('State')
        if state != 'SUCCEEDED':
            raise RuntimeError(f'Athena table setup did not succeed ({statement}): state {state}')

    async def execute_query(
        self, query: str, database_name: str, output_location: str
    ) -> AthenaQueryExecution:
        """Execute an Athena query.

        Args:
            query: SQL query to execute
            database_name: Athena database name to use
            output_location: S3 location for Athena query results

        Returns:
            AthenaQueryExecution: Query execution ID and status
        """
        try:
            await self.ctx.info(f'Executing Athena query on database {database_name}:')
            await self.ctx.info(f'Query: {query}')
            await self.ctx.info(f'Output location: {output_location}')

            # Start query execution
            response = self.athena_client.start_query_execution(
                QueryString=query,
                QueryExecutionContext={'Database': database_name},
                ResultConfiguration={'OutputLocation': output_location},
            )

            query_execution_id = response['QueryExecutionId']
            await self.ctx.info(f'Query execution ID: {query_execution_id}')

            return AthenaQueryExecution(query_execution_id=query_execution_id, status='STARTED')

        except Exception as e:
            await self.ctx.error(f'Error starting Athena query: {str(e)}')
            # Re-raise unwrapped so handle_aws_error keeps the AWS error code
            raise

    async def wait_for_query_completion(
        self,
        query_execution_id: str,
        max_retries: int = ATHENA_MAX_RETRIES,
        failure: type[Exception] = ValueError,
        label: str = 'Query',
    ) -> Dict[str, Any]:
        """Wait for an Athena query to complete.

        Args:
            query_execution_id: Query execution ID
            max_retries: Maximum number of retries
            failure: Exception raised when the query fails; ValueError marks the caller's query
            label: What is waited for, at the start of failure, cancel and timeout messages

        Returns:
            Dict[str, Any]: Query execution status
        """
        try:
            state = 'RUNNING'  # Initial state assumption
            retries = 0

            await self.ctx.info(f'Waiting for Athena query {query_execution_id} to complete...')

            while (state == 'RUNNING' or state == 'QUEUED') and retries < max_retries:
                response = self.athena_client.get_query_execution(
                    QueryExecutionId=query_execution_id
                )
                state = response['QueryExecution']['Status']['State']

                await self.ctx.info(f'Query state: {state} (retry {retries}/{max_retries})')

                if state == 'FAILED':
                    reason = response['QueryExecution']['Status'].get(
                        'StateChangeReason', 'Unknown error'
                    )
                    await self.ctx.error(f'Query failed: {reason}')
                    # A failed Athena query is almost always the query itself
                    raise failure(f'{label} failed: {reason}')
                elif state == 'CANCELLED':
                    reason = response['QueryExecution']['Status'].get(
                        'StateChangeReason', 'no reason given'
                    )
                    await self.ctx.error(f'Query cancelled: {reason}')
                    raise RuntimeError(f'{label} cancelled: {reason}')
                elif state == 'SUCCEEDED':
                    await self.ctx.info(f'Query succeeded after {retries} retries')
                    return response['QueryExecution']

                # Wait before checking again
                await asyncio.sleep(ATHENA_RETRY_DELAY_SECONDS)
                retries += 1

            if retries >= max_retries:
                await self.ctx.error(f'Query timed out after {max_retries} retries')
                raise TimeoutError(f'{label} timed out')

            # This should never be reached due to the exception above, but return empty dict for type safety
            return {'status': 'ERROR', 'message': 'Query timed out'}

        except Exception as e:
            # Use shared error handler for consistent error reporting
            await self.ctx.error(f'Error waiting for query completion: {str(e)}')
            raise

    async def get_query_results(self, query_execution_id: str) -> Dict[str, Any]:
        """Get the results of a completed Athena query.

        Args:
            query_execution_id: Query execution ID

        Returns:
            Dict[str, Any]: Query results and metadata
        """
        try:
            # Get query results
            results_response = self.athena_client.get_query_results(
                QueryExecutionId=query_execution_id
            )

            # Process results
            columns = [
                col['Label']
                for col in results_response['ResultSet']['ResultSetMetadata']['ColumnInfo']
            ]
            rows = []

            # Skip header row if it exists
            result_rows = results_response['ResultSet']['Rows']
            start_index = (
                1 if len(result_rows) > 0 and len(columns) == len(result_rows[0]['Data']) else 0
            )

            for row in result_rows[start_index:]:
                values = []
                for item in row['Data']:
                    values.append(item.get('VarCharValue', ''))
                rows.append(dict(zip(columns, values)))

            return {'columns': columns, 'rows': rows}

        except Exception as e:
            # Use shared error handler for consistent error reporting
            await self.ctx.error(f'Error getting query results: {str(e)}')
            raise

    def determine_output_location(
        self, data_location: str, output_location: Optional[str] = None
    ) -> str:
        """Determine the output location for Athena query results.

        Args:
            data_location: S3 location of the data files
            output_location: User-provided output location

        Returns:
            str: S3 location for Athena query results
        """
        if output_location:
            return output_location

        # If output_location is not provided, use the same bucket as the data
        parsed_data_uri = urlparse(data_location)
        bucket = parsed_data_uri.netloc
        return f's3://{bucket}/athena-results/'


class StorageLensQueryTool:
    """Tool for querying S3 Storage Lens metrics using Athena."""

    def __init__(self, ctx: Context):
        """Initialize the manifest and Athena handlers.

        Args:
            ctx: MCP context for logging
        """
        self.ctx = ctx
        self.manifest_handler = ManifestHandler(ctx)
        self.athena_handler = AthenaHandler(ctx)

    async def query_storage_lens(
        self,
        query: str,
        manifest_location: str,
        database_name: str = STORAGE_LENS_DEFAULT_DATABASE,
        table_name: str = STORAGE_LENS_DEFAULT_TABLE,
        output_location: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Query S3 Storage Lens metrics using Athena.

        Args:
            query: SQL query to execute against Storage Lens data
            manifest_location: S3 URI to manifest file or folder
            database_name: Athena database name (defaults to 'storage_lens_db'); a letter, then
                letters, digits or underscores, at most 255 characters
            table_name: Athena table name (defaults to 'storage_lens_metrics'); same rule
            output_location: S3 location for query results (optional)

        Returns:
            Dict[str, Any]: Query results and metadata; a validation_error if a name or the
            table reference is invalid
        """
        try:
            # 1. Check the names, replace the {table} placeholder, then require that the query
            # reads the qualified table. Anything else is rejected before AWS is called; nothing
            # but {table} is rewritten.
            validate_athena_name('database_name', database_name)
            validate_athena_name('table_name', table_name)
            qualified_table = f'{database_name}.{table_name}'
            formatted_query = query.replace('{table}', qualified_table)
            if not references_qualified_table(formatted_query, database_name, table_name):
                raise ValueError(
                    'Query must reference the table with the {table} placeholder (as in '
                    f'"FROM {{table}}") or by its qualified name {qualified_table}, and must '
                    'parse as SQL once {table} is replaced.'
                )

            # 2. Locate and parse manifest file
            manifest = await self.manifest_handler.get_manifest(manifest_location)

            # 3. Extract data location and schema information
            data_location = self.manifest_handler.extract_data_location(manifest)
            schema_info = self.manifest_handler.parse_schema(manifest)

            # 4. Determine output location if not provided
            if not output_location:
                output_location = self.athena_handler.determine_output_location(data_location)

            # 5-7. Set up the table, then run the query and wait for it, holding the table's lock
            # so a concurrent call cannot re-point the table before this query has read it
            async with table_lock(qualified_table):
                await self.athena_handler.setup_table(
                    database_name, table_name, schema_info, data_location, output_location
                )

                query_result = await self.athena_handler.execute_query(
                    formatted_query, database_name, output_location
                )

                execution_details = await self.athena_handler.wait_for_query_completion(
                    query_result['query_execution_id']
                )

            # 8. Get query results
            results = await self.athena_handler.get_query_results(
                query_result['query_execution_id']
            )

            # 9. Add query statistics and metadata
            stats = execution_details['Statistics']
            formatted_response = {
                'execution_time_ms': stats.get('TotalExecutionTimeInMillis', 0),
                'data_scanned_bytes': stats.get('DataScannedInBytes', 0),
                'engine_execution_time_ms': stats.get('EngineExecutionTimeInMillis', 0),
                'columns': results['columns'],
                'rows': results['rows'],
                'query': formatted_query,
                'manifest_location': manifest_location,
                'data_location': data_location,
            }

            return format_response('success', formatted_response)

        except Exception as e:
            # Use shared error handler for consistent error reporting
            return await handle_aws_error(self.ctx, e, 'query_storage_lens', 'Storage Lens')


@storage_lens_server.tool(
    name='storage-lens',
    description="""Query S3 Storage Lens metrics data using Athena SQL.

IMPORTANT USAGE GUIDELINES:
- Before using this tool, provide a 1-3 sentence explanation starting with "EXPLANATION:"
- Dialect: Athena engine version 3 (Trino SQL). In CSV exports every column is a string, so cast before math or numeric comparison, e.g. SUM(CAST(metric_value AS BIGINT))
- Reference the Storage Lens metrics table with the {table} placeholder (or its qualified <database>.<table> name). A query that does neither is rejected with a validation_error. Every {table} is replaced; nothing else in the query is changed
- database_name and table_name, if given, must start with a letter and contain only letters, digits and underscores (at most 255 characters); other values are rejected with a validation_error
- Perform aggregations (GROUP BY) when analyzing data across multiple dimensions

This tool allows you to analyze S3 Storage Lens metrics data using SQL queries.
Storage Lens provides metrics about your S3 storage, including:

- Storage metrics: Total bytes, object counts by storage class
- Cost optimization metrics: Transition opportunities, incomplete multipart uploads
- Data protection metrics: Replication, versioning, encryption status
- Activity metrics: Upload, download, and request metrics

STORAGE LENS EXPORT SCHEMA:
The Storage Lens export data has the following standard columns:
- version_number: The version of the S3 Storage Lens metrics being used
- configuration_id: The configuration_id of your S3 Storage Lens configuration
- report_date: The date that the metrics were tracked
- aws_account_number: Your AWS account number
- aws_region: The AWS Region for which the metrics are being tracked
- storage_class: The storage class (STANDARD, STANDARD_IA, GLACIER, etc.)
- record_type: The type of artifact being reported (ACCOUNT, BUCKET, PREFIX, STORAGE_LENS_GROUP_BUCKET, STORAGE_LENS_GROUP_ACCOUNT)
- record_value: The value of the record_type artifact (account ID, bucket name, prefix, or Storage Lens group ARN)
- bucket_name: The name of the bucket (when record_type is BUCKET or PREFIX)
- metric_name: The name of the metric (e.g., 'StorageBytes', 'ObjectCount', 'EncryptedStorageBytes')
- metric_value: The numeric value of the metric

IMPORTANT: Metrics are stored in rows, not columns. Each row represents one metric value for a specific combination of dimensions.

IMPORTANT: record_type levels are nested. The same storage is reported once per account (ACCOUNT), again per bucket (BUCKET) and again per prefix (PREFIX), plus once per Storage Lens group, so filter to exactly one record_type before SUM; otherwise totals count the same bytes two or more times. Use record_type = 'ACCOUNT' for account, Region or storage class totals and record_type = 'BUCKET' for per-bucket figures. The record_value column is URL-encoded.

The table holds one day's report: the one the manifest describes (for a folder, its newest manifest.json). Each call points the table at that report's folder, so a query reads only that day and needs no date filter. Calls through one server take turns on a table; separate server processes that share a table_name can still interleave, so give them different table_name values. A table_name whose table is partitioned, has no location, or is not on a Storage Lens report day folder is queried as it is.

Environment variables:
- STORAGE_LENS_MANIFEST_LOCATION: S3 URI to manifest file or folder (required)
- STORAGE_LENS_OUTPUT_LOCATION: S3 location for Athena query results (optional)

Example queries:
1. Top 10 buckets by storage size:
   SELECT
       bucket_name,
       SUM(CAST(metric_value AS BIGINT)) as total_size
   FROM {table}
   WHERE metric_name = 'StorageBytes'
     AND record_type = 'BUCKET'
   GROUP BY bucket_name
   ORDER BY total_size DESC
   LIMIT 10

2. Storage distribution by storage class:
   SELECT
       storage_class,
       SUM(CAST(metric_value AS BIGINT)) as total_size
   FROM {table}
   WHERE metric_name = 'StorageBytes'
     AND record_type = 'ACCOUNT'
   GROUP BY storage_class
   ORDER BY total_size DESC

3. Buckets with incomplete multipart uploads:
   SELECT
       bucket_name,
       SUM(CAST(metric_value AS BIGINT)) as incomplete_bytes
   FROM {table}
   WHERE metric_name = 'IncompleteMultipartUploadStorageBytes'
     AND record_type = 'BUCKET'
     AND CAST(metric_value AS BIGINT) > 0
   GROUP BY bucket_name
   ORDER BY incomplete_bytes DESC

4. Storage Distribution by Region and Storage Class:
   SELECT
       aws_region,
       storage_class,
       SUM(CAST(metric_value AS BIGINT)) as total_bytes
   FROM {table}
   WHERE metric_name = 'StorageBytes'
     AND record_type = 'ACCOUNT'
   GROUP BY aws_region, storage_class
   ORDER BY total_bytes DESC

5. Object Lifecycle Management Opportunities:
   SELECT
       aws_region,
       storage_class,
       SUM(CASE WHEN metric_name = 'NonCurrentVersionStorageBytes' THEN CAST(metric_value AS BIGINT) ELSE 0 END) as noncurrent_bytes,
       SUM(CASE WHEN metric_name = 'StorageBytes' THEN CAST(metric_value AS BIGINT) ELSE 0 END) as total_bytes
   FROM {table}
   WHERE metric_name IN ('NonCurrentVersionStorageBytes', 'StorageBytes')
     AND record_type = 'ACCOUNT'
   GROUP BY aws_region, storage_class
   HAVING SUM(CASE WHEN metric_name = 'NonCurrentVersionStorageBytes' THEN CAST(metric_value AS BIGINT) ELSE 0 END) > 0
   ORDER BY noncurrent_bytes DESC

6. Lifecycle Rule Analysis:
   SELECT
       bucket_name,
       SUM(CASE WHEN metric_name = 'TotalLifecycleRuleCount' THEN CAST(metric_value AS INTEGER) ELSE 0 END) as lifecycle_rule_count,
       SUM(CASE WHEN metric_name = 'StorageBytes' THEN CAST(metric_value AS BIGINT) ELSE 0 END) as total_bytes
   FROM {table}
   WHERE metric_name IN ('TotalLifecycleRuleCount', 'StorageBytes')
     AND record_type = 'BUCKET'
   GROUP BY bucket_name
   ORDER BY lifecycle_rule_count ASC, total_bytes DESC""",
)
async def storage_lens_run_query(
    ctx: Context,
    query: str,
    manifest_location: Optional[str] = None,
    output_location: Optional[str] = None,
    database_name: Optional[str] = None,
    table_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Query S3 Storage Lens metrics data using Athena SQL.

    Args:
        ctx: The MCP context
        query: SQL query to execute against the data. Reference the table with the {table}
            placeholder or its qualified <database>.<table> name; other queries are rejected.
        manifest_location: S3 URI to manifest file or folder (overrides environment variable)
        output_location: S3 location for Athena query results (overrides environment variable)
        database_name: Athena database name (defaults to 'storage_lens_db'; empty also means the
            default). A letter, then letters, digits or underscores, at most 255 characters.
        table_name: Athena table name (defaults to 'storage_lens_metrics'; empty also means the
            default). Same rule as database_name.

    Returns:
        Dict containing the query results and metadata
    """
    try:
        # Log the request
        await ctx.info(f'Running Storage Lens query: {query}')

        # Validate user-supplied query is a read-only SELECT
        validation_error = validate_query_is_readonly_select(query)
        if validation_error:
            return format_response(
                'error',
                {},
                validation_error,
                error_type='validation_error',
                operation='storage_lens_run_query',
                service='Storage Lens',
            )

        # Get manifest location from args or environment variable
        manifest_loc = manifest_location or os.environ.get(ENV_STORAGE_LENS_MANIFEST_LOCATION, '')
        if not manifest_loc:
            return format_response(
                'error',
                {},
                f"Missing manifest location. Provide 'manifest_location' parameter or set {ENV_STORAGE_LENS_MANIFEST_LOCATION} environment variable.",
                error_type='validation_error',
                operation='storage_lens_run_query',
                service='Storage Lens',
            )

        # Get output location from args or environment variable (optional)
        output_loc = output_location or os.environ.get(ENV_STORAGE_LENS_OUTPUT_LOCATION, '')

        # Use default or provided database and table names
        db_name = database_name or STORAGE_LENS_DEFAULT_DATABASE
        tbl_name = table_name or STORAGE_LENS_DEFAULT_TABLE

        # Create the query tool
        query_tool = StorageLensQueryTool(ctx)

        # Execute the query
        result = await query_tool.query_storage_lens(
            query=query,
            manifest_location=manifest_loc,
            database_name=db_name,
            table_name=tbl_name,
            output_location=output_loc,
        )

        return result

    except Exception as e:
        # Use shared error handler for consistent error reporting
        return await handle_aws_error(ctx, e, 'storage_lens_run_query', 'Athena')
