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

"""Redshift MCP Server implementation."""

import os
import sys
from awslabs.redshift_mcp_server.catalog import (
    discover_columns,
    discover_databases,
    discover_schemas,
    discover_tables,
)
from awslabs.redshift_mcp_server.clusters import discover_clusters
from awslabs.redshift_mcp_server.consts import (
    ACCESS_MODE_READ_WRITE,
    LOG_LEVEL_DEFAULT,
)
from awslabs.redshift_mcp_server.models import (
    QueryResult,
    RedshiftCluster,
    RedshiftColumn,
    RedshiftDatabase,
    RedshiftSchema,
    RedshiftTable,
)
from awslabs.redshift_mcp_server.redshift import (
    execute_query,
    no_batch_latched,
)
from awslabs.redshift_mcp_server.review.executor import review_cluster
from awslabs.redshift_mcp_server.review.models import ReviewResult
from awslabs.redshift_mcp_server.settings import (
    max_open_transactions_per_target,
    resolve_access_mode,
    resolve_skip_write_confirmation,
    session_keepalive,
)
from awslabs.redshift_mcp_server.sql_guard import assert_executable, might_write
from botocore.exceptions import BotoCoreError, ClientError
from loguru import logger
from mcp.server.mcpserver import Context, Elicit, MCPServer, Resolve
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ClientCapabilities, ElicitationCapability, ToolAnnotations
from pydantic import BaseModel, Field
from typing import Annotated, NoReturn


# Remove default handler and add custom configuration
logger.remove()
logger.add(
    os.environ.get('LOG_FILE', sys.stderr),
    # LOG_LEVEL is the documented variable; FASTMCP_LOG_LEVEL is an undocumented
    # fallback kept so existing configurations keep working.
    level=os.environ.get('LOG_LEVEL', os.environ.get('FASTMCP_LOG_LEVEL', LOG_LEVEL_DEFAULT)),
)


# Resolved here, rather than on first use like the settings that carry their own accessor,
# because this point is past the logger.add above and so the warnings both resolvers raise
# reach LOG_FILE. Once is enough: neither setting can change while the server runs.
ACCESS_MODE = resolve_access_mode()
SKIP_WRITE_CONFIRMATION = resolve_skip_write_confirmation(ACCESS_MODE)


def _current_settings() -> str:
    """Report the settings this server resolved at startup.

    Appended to the prose that names these settings, since the caller cannot read the
    server's environment and would otherwise have to guess which branch of that prose
    applies.

    Returns:
        A markdown section listing each setting and its resolved value.
    """
    settings = (
        f'- `ACCESS_MODE`: {ACCESS_MODE}\n'
        f'- `UNSAFE_SKIP_WRITE_CONFIRMATION`: {str(SKIP_WRITE_CONFIRMATION).lower()}\n'
        f'- `SESSION_KEEPALIVE`: {session_keepalive()} seconds\n'
        f'- `MAX_OPEN_TRANSACTIONS_PER_TARGET`: {max_open_transactions_per_target()}\n'
    )

    if SKIP_WRITE_CONFIRMATION:
        settings += (
            '\nNo confirmation prompt reaches the user before a write runs, so the database '
            'user privileges are the only remaining control. Tell the user what a write will '
            'change and get their agreement yourself before submitting it.\n'
        )

    return f'\n## Current Settings\n\nFixed for the life of this server process:\n\n{settings}'


mcp = MCPServer(
    'awslabs.redshift-mcp-server',
    instructions="""
# Amazon Redshift MCP Server

Discovers, explores and queries Amazon Redshift clusters and serverless workgroups over the
Redshift, Redshift Serverless and Redshift Data APIs.

## Tools

- `list_clusters` — provisioned clusters and serverless workgroups in the account.
- `list_databases`, `list_schemas`, `list_tables`, `list_columns` — metadata discovery, via
  `SHOW DATABASES`, `SHOW SCHEMAS`, `SHOW TABLES` and `SHOW COLUMNS`.
- `execute_query` — run one SQL statement. Read-only by default; read-write is opt-in via
  `ACCESS_MODE`. Supports named transactions across calls.
- `review_cluster` — diagnostic review of a cluster or workgroup. Needs the `sys:monitor`
  role, or a superuser.

## Discovery order

Work down the hierarchy: `list_clusters` for an identifier, then `list_databases` for that
cluster, then `list_schemas`, `list_tables` and `list_columns`. Every tool takes the cluster
identifier as its first argument, and only a cluster whose status is `available` can be
queried.

A database is connected to, while a schema and a table are filtered for. So an unknown schema
or table comes back as an empty list, but a database that does not exist or cannot be connected
to is an error, and it is the same error on every tool that names one — including the three
below `list_databases`, not only `list_schemas`.

## Concurrency

Without a transaction parameter, each statement runs on its own connection: statements
against the same `cluster:database` run concurrently, including behind a long-running one,
and no session state carries between calls: a temporary table or a `SET` is gone by the next,
though the statement that made it reports success.

To carry state across calls, name a transaction with `execute_query`'s `begin_transaction`,
`in_transaction`, `commit_transaction` and `rollback_transaction` parameters. Its statements
share one connection and are serialized against each other, but not against anything else.

## Credentials and region

The default AWS credentials chain, with `AWS_PROFILE` if set. Region precedence is
`AWS_REGION`, then `AWS_DEFAULT_REGION`, then the profile's own region.

Report AWS client errors in full — they name the misconfiguration. For a region error point
at `AWS_REGION`, `AWS_DEFAULT_REGION` or the profile; for a credentials error, at the
credentials setup and its permissions.

## Query guidelines

- Qualify objects with database and schema to avoid ambiguity.
- Filter on the distribution key and join on it where possible; order by the sort key.
- `LIMIT` exploratory queries.
- Name the columns you need rather than selecting every column.
- Check whether statistics are current before drawing conclusions from a plan.
- Prefer IAM authentication over database passwords.
"""
    + _current_settings(),
    dependencies=['boto3', 'loguru', 'pydantic', 'sqlglot'],
)


def _read_only_annotations(title: str) -> ToolAnnotations:
    """Return annotations for tools that only read the caller's AWS environment."""
    return ToolAnnotations(
        title=title,
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=True,
    )


class ConfirmWrite(BaseModel):
    """Response schema for the read-write confirmation prompt."""

    confirmed: bool = Field(
        description='True to execute the statement, false to abandon it.',
    )


def _write_confirmation(
    ctx: Context,
    cluster_identifier: str,
    database_name: str,
    sql: str | None,
    begin_transaction: str | None = None,
    in_transaction: str | None = None,
    commit_transaction: str | None = None,
    rollback_transaction: str | None = None,
) -> ConfirmWrite | Elicit[ConfirmWrite]:
    """Resolve the caller's approval for one statement.

    Returning `Elicit` asks the client. The framework runs the round trip on whichever
    shape the negotiated protocol requires and aborts the call on decline or cancel.
    Returning a value asks nothing, which is the case for read-only mode, the
    confirmation opt-out, and recognized reads.

    Args:
        ctx: The tool call context, used to check what the client can do.
        cluster_identifier: The target cluster, named in the prompt.
        database_name: The target database, named in the prompt.
        sql: The statement awaiting approval, or None when a transaction is only being
            closed, which carries no statement of the caller's.
        begin_transaction: Name of a transaction being opened, if any.
        in_transaction: Name of a transaction being added to, if any.
        commit_transaction: Name of a transaction being committed, if any.
        rollback_transaction: Name of a transaction being rolled back, if any.

    A decline or cancel is not observable here: the framework aborts the call after this
    returns, so only the request to ask is logged, not its answer.

    Returns:
        A standing approval when no confirmation is required, else a request to ask.

    Raises:
        ToolError: If the SQL is rejected by the guard, or the client cannot be asked.
    """
    if ACCESS_MODE != ACCESS_MODE_READ_WRITE or SKIP_WRITE_CONFIRMATION:
        return ConfirmWrite(confirmed=True)

    if sql is None:
        # Closing a transaction runs nothing of the caller's, and every write inside it was
        # confirmed when it was submitted.
        return ConfirmWrite(confirmed=True)

    # Reject before asking, so a statement that cannot run never raises a prompt. Only
    # this server's read-only protection is off here; the mode is read-write by this point.
    assert_executable(
        sql,
        enforce_read_only=False,
        in_transaction=bool(
            begin_transaction or in_transaction or commit_transaction or rollback_transaction
        ),
    )

    # The guard is not the only thing that refuses a write. While the batch action is denied on
    # this cluster the compatibility path serves reads only, so asking would have put a prompt
    # in front of a statement certain to be refused a moment later. Peeked rather than probed,
    # because deciding a statement's path consumes the re-probe and that decision is the tool
    # body's to make.
    if no_batch_latched(cluster_identifier) and might_write(sql):
        return ConfirmWrite(confirmed=True)

    if not might_write(sql):
        return ConfirmWrite(confirmed=True)

    # Checked here, rather than leaving it to the framework, so the error names the
    # setting that lets the operator proceed.
    if not ctx.session.check_client_capability(
        ClientCapabilities(elicitation=ElicitationCapability())
    ):
        logger.warning(
            f'Refused a write on {cluster_identifier}:{database_name}: the client cannot '
            'be asked to confirm it.'
        )
        raise ToolError(
            'This MCP client cannot prompt for confirmation, so the statement was not '
            'run. Use a client that supports elicitation, or set '
            'UNSAFE_SKIP_WRITE_CONFIRMATION=true to execute writes unconfirmed.'
        )

    # Logged twice per call, which is worth keeping: the SDK resolves this dependency once to
    # raise the prompt and once after the answer, so the pair brackets the round trip and the gap
    # between the two is how long the caller took to decide. Worded as a requirement rather than
    # an act, since only the first one asks.
    logger.info(f'Write on {cluster_identifier}:{database_name} requires confirmation')

    # What the caller is agreeing to differs by action, and the difference is what they are
    # deciding. A statement submitted with commit_transaction is committed by the same call,
    # and one submitted with rollback_transaction is discarded by it, so neither is pending.
    if commit_transaction is not None:
        consequence = (
            f'It runs inside transaction {commit_transaction!r} and commits it, so it is final '
            f'and cannot be rolled back.'
        )
    elif rollback_transaction is not None:
        # Scoped to the database deliberately. A rollback discards what the transaction wrote
        # there, and reaches nothing outside it: UNLOAD has already written to S3 by then, and
        # with CLEANPATH has already deleted what was there.
        consequence = (
            f'It runs inside transaction {rollback_transaction!r} and then rolls it back, so '
            f'any change it makes in the database is discarded. Anything it does outside the '
            f'database, such as writing to S3, is not.'
        )
    elif begin_transaction or in_transaction:
        transaction = begin_transaction or in_transaction
        consequence = (
            f'It runs inside transaction {transaction!r}, so any change it makes in the '
            f'database is not final until you commit. Anything it does outside the database, '
            f'such as writing to S3, is final as soon as it runs.'
        )
    else:
        consequence = 'It runs with autocommit and cannot be rolled back.'

    return Elicit(
        message=(
            f'Execute this statement against {cluster_identifier}:{database_name}? '
            f'{consequence}\n\n{sql}'
        ),
        schema=ConfirmWrite,
    )


def _execute_query_annotations(access_mode: str) -> ToolAnnotations:
    """Return execute_query annotations matching the configured access mode.

    In read-write mode the tool can modify and delete data, so the hints must say so
    rather than advertise the read-only guarantee the server no longer enforces.

    Args:
        access_mode: The resolved access mode, one of `ACCESS_MODES`.

    Returns:
        Annotations describing execute_query under the configured mode.
    """
    if access_mode != ACCESS_MODE_READ_WRITE:
        return _read_only_annotations('Execute read-only Redshift query')

    return ToolAnnotations(
        title='Execute read-write Redshift query',
        read_only_hint=False,
        destructive_hint=True,
        idempotent_hint=False,
        open_world_hint=True,
    )


def _tool_failed(tool: str, error: Exception) -> NoReturn:
    """Log a failed tool call and raise what the caller needs to see.

    The SDK withholds the text of anything that is not a `ToolError`, so an AWS error would
    otherwise reach the caller as a bare "Error executing tool ..." with nothing to act on.

    Every tool routes its failures here, which makes this the one place a failure is logged at
    ERROR; the paths below log the same fact at DEBUG, beside the SQL that caused it. Note for
    whoever ships this log elsewhere: an engine error carries the offending value, column or
    relation from the statement, so the line below can quote statement content that `LOG_LEVEL`
    otherwise keeps at DEBUG.

    A `ClientError` is AWS reporting a condition the caller can usually resolve: a paused or
    resuming cluster, an endpoint not yet available, throttling, expired credentials, a missing
    grant. Its message is theirs to read. A `BotoCoreError` is the SDK reporting that it cannot
    make the call at all - no region, no credentials, an unknown profile, an unreachable
    endpoint - which names something the operator has to fix and is useless withheld. Anything
    else is a defect in this server, whose text would tell them nothing useful, so it stays
    withheld.

    Args:
        tool: Name of the tool that failed, for the log.
        error: What it failed with.

    Raises:
        ToolError: If AWS reported the failure.
        Exception: The original error otherwise, for the SDK to report as a crash.
    """
    logger.error(f'Error in {tool}: {error}')

    if isinstance(error, (ClientError, BotoCoreError)):
        raise ToolError(str(error)) from error

    raise error


@mcp.tool(
    name='list_clusters',
    annotations=_read_only_annotations('List Redshift clusters and workgroups'),
)
async def list_clusters_tool(ctx: Context) -> list[RedshiftCluster]:
    """List Redshift clusters and serverless workgroups in the account.

    Returns one entry per cluster: identifier, type (provisioned or serverless), status,
    database_name, endpoint, port, vpc_id, node_type, number_of_nodes, creation_time,
    master_username, publicly_accessible, encrypted and tags.

    Only a cluster whose status is 'available' can be queried, and its identifier is what
    every other tool takes as its first argument.

    Requires redshift:DescribeClusters, redshift-serverless:ListWorkgroups and
    redshift-serverless:GetWorkgroup. Whichever of provisioned or serverless discovery is
    denied is skipped, so a partial list is normal; both denied is an error.
    """
    try:
        logger.info('Discovering Redshift clusters and serverless workgroups')
        clusters = await discover_clusters()

        logger.info(f'Successfully retrieved {len(clusters)} clusters')
        return clusters

    except Exception as e:
        _tool_failed('list_clusters_tool', e)


@mcp.tool(
    name='list_databases',
    annotations=_read_only_annotations('List Redshift databases'),
)
async def list_databases_tool(
    ctx: Context,
    cluster_identifier: str = Field(
        ...,
        description='The cluster identifier to query for databases. Must be a valid cluster identifier from the list_clusters tool.',
    ),
    database_name: str = Field(
        'dev',
        description='The database to connect to for metadata discovery. Defaults to "dev".',
    ),
) -> list[RedshiftDatabase]:
    """List the databases in a cluster, via SHOW DATABASES.

    Returns database_name, database_owner, database_type, database_acl, parameters and
    database_isolation_level.

    database_type is 'local' for a database on the cluster itself, 'shared' for one from a
    datashare, or 'auto mounted catalog' for one Redshift mounted from an external catalog such
    as AWS Glue. An auto-mounted catalog is listed here but cannot be explored further, since
    Redshift refuses to connect to it.

    A 'shared' database comes from a datashare, and appears only if the connecting
    principal has been granted access to the consumer database (GRANT USAGE ON DATABASE
    <db> TO <principal>) — so a datashare can exist without being listed here.

    Requires redshift-data:BatchExecuteStatement, redshift-data:DescribeStatement and
    redshift-data:GetStatementResult.
    """
    try:
        logger.info(f'Discovering databases on cluster: {cluster_identifier}')
        databases = await discover_databases(
            cluster_identifier=cluster_identifier, database_name=database_name
        )

        logger.info(
            f'Successfully retrieved {len(databases)} databases from cluster {cluster_identifier}'
        )
        return databases

    except Exception as e:
        _tool_failed('list_databases_tool', e)


@mcp.tool(
    name='list_schemas',
    annotations=_read_only_annotations('List Redshift schemas'),
)
async def list_schemas_tool(
    ctx: Context,
    cluster_identifier: str = Field(
        ...,
        description='The cluster identifier to query for schemas. Must be a valid cluster identifier from the list_clusters tool.',
    ),
    schema_database_name: str = Field(
        ...,
        description='The database name to list schemas for. Also used to connect to. Must be a valid database name from the list_databases tool.',
    ),
) -> list[RedshiftSchema]:
    """List the schemas in a database, via SHOW SCHEMAS.

    Returns database_name, schema_name, schema_owner, schema_type (local, external or
    shared), schema_acl, source_database and schema_option.

    An 'external' schema points at S3 or another database. A 'shared' schema comes from a
    datashare and appears only if the principal has been granted access to the consumer
    database. A database auto-mounted from a Glue Data Catalog cannot be explored: Redshift
    refuses to connect to it, so this tool fails on one even though list_databases lists it.

    Requires redshift-data:BatchExecuteStatement, redshift-data:DescribeStatement and
    redshift-data:GetStatementResult.
    """
    try:
        logger.info(
            f'Discovering schemas in database {schema_database_name} on cluster {cluster_identifier}'
        )
        schemas = await discover_schemas(
            cluster_identifier=cluster_identifier, schema_database_name=schema_database_name
        )

        logger.info(
            f'Successfully retrieved {len(schemas)} schemas from database {schema_database_name} on cluster {cluster_identifier}'
        )
        return schemas

    except Exception as e:
        _tool_failed('list_schemas_tool', e)


@mcp.tool(
    name='list_tables',
    annotations=_read_only_annotations('List Redshift tables'),
)
async def list_tables_tool(
    ctx: Context,
    cluster_identifier: str = Field(
        ...,
        description='The cluster identifier to query for tables. Must be a valid cluster identifier from the list_clusters tool.',
    ),
    table_database_name: str = Field(
        ...,
        description='The database name to list tables for. Must be a valid database name from the list_databases tool.',
    ),
    table_schema_name: str = Field(
        ...,
        description='The schema name to list tables for. Also used to connect to. Must be a valid schema name from the list_schemas tool.',
    ),
) -> list[RedshiftTable]:
    """List the tables in a schema, via SHOW TABLES.

    Returns database_name, schema_name, table_name, table_acl, table_type and remarks,
    where table_type is TABLE, VIEW, EXTERNAL TABLE or SHARED TABLE.

    An unknown schema returns an empty list rather than an error.

    Requires redshift-data:BatchExecuteStatement, redshift-data:DescribeStatement and
    redshift-data:GetStatementResult.
    """
    try:
        logger.info(
            f'Discovering tables in schema {table_schema_name} in database {table_database_name} on cluster {cluster_identifier}'
        )
        tables = await discover_tables(
            cluster_identifier=cluster_identifier,
            table_database_name=table_database_name,
            table_schema_name=table_schema_name,
        )

        logger.info(
            f'Successfully retrieved {len(tables)} tables from schema {table_schema_name} in database {table_database_name} on cluster {cluster_identifier}'
        )
        return tables

    except Exception as e:
        _tool_failed('list_tables_tool', e)


@mcp.tool(
    name='list_columns',
    annotations=_read_only_annotations('List Redshift columns'),
)
async def list_columns_tool(
    ctx: Context,
    cluster_identifier: str = Field(
        ...,
        description='The cluster identifier to query for columns. Must be a valid cluster identifier from the list_clusters tool.',
    ),
    column_database_name: str = Field(
        ...,
        description='The database name to list columns for. Must be a valid database name from the list_databases tool.',
    ),
    column_schema_name: str = Field(
        ...,
        description='The schema name to list columns for. Must be a valid schema name from the list_schemas tool.',
    ),
    column_table_name: str = Field(
        ...,
        description='The table name to list columns for. Must be a valid table name from the list_tables tool.',
    ),
) -> list[RedshiftColumn]:
    """List the columns in a table, via SHOW COLUMNS.

    Returns database_name, schema_name, table_name, column_name, ordinal_position,
    column_default, is_nullable, data_type, character_maximum_length, numeric_precision,
    numeric_scale and remarks.

    An unknown table returns an empty list rather than an error.

    Requires redshift-data:BatchExecuteStatement, redshift-data:DescribeStatement and
    redshift-data:GetStatementResult.
    """
    try:
        logger.info(
            f'Discovering columns in table {column_table_name} in schema {column_schema_name} in database {column_database_name} on cluster {cluster_identifier}'
        )
        columns = await discover_columns(
            cluster_identifier=cluster_identifier,
            column_database_name=column_database_name,
            column_schema_name=column_schema_name,
            column_table_name=column_table_name,
        )

        logger.info(
            f'Successfully retrieved {len(columns)} columns from table {column_table_name} in schema {column_schema_name} in database {column_database_name} on cluster {cluster_identifier}'
        )
        return columns

    except Exception as e:
        _tool_failed('list_columns_tool', e)


@mcp.tool(
    name='execute_query',
    annotations=_execute_query_annotations(ACCESS_MODE),
)
async def execute_query_tool(
    ctx: Context,
    confirmation: Annotated[ConfirmWrite, Resolve(_write_confirmation)],
    cluster_identifier: str = Field(
        ...,
        description='The cluster identifier to execute the query on. Must be a valid cluster identifier from the list_clusters tool.',
    ),
    database_name: str = Field(
        ...,
        description='The database name to execute the query against. Must be a valid database name from the list_databases tool.',
    ),
    sql: Annotated[
        str | None,
        Field(
            description=(
                'The SQL statement to execute. Must be a single SQL statement. Whether writes '
                'are permitted is fixed by the server configuration, not by this call. '
                'Required unless a transaction is only being committed or rolled back.'
            )
        ),
    ] = None,
    begin_transaction: Annotated[
        str | None,
        Field(
            description=(
                'Open a transaction under this name and run sql inside it, if given. The name '
                'is yours to choose and to reuse on later calls. Fails if it is already open.'
            )
        ),
    ] = None,
    in_transaction: Annotated[
        str | None,
        Field(description='Run sql inside the transaction already open under this name.'),
    ] = None,
    commit_transaction: Annotated[
        str | None,
        Field(description='Run sql, if given, then commit the transaction open under this name.'),
    ] = None,
    rollback_transaction: Annotated[
        str | None,
        Field(
            description='Run sql, if given, then roll back the transaction open under this name.'
        ),
    ] = None,
) -> QueryResult:
    """Execute one SQL statement against a Redshift cluster or serverless workgroup.

    Returns columns (names), rows, row_count and query_id. Values are typed as the Data API
    returns them: INTEGER and BIGINT as integers, REAL and DOUBLE PRECISION as floats,
    booleans as booleans, NULL as null, and everything else as a string, including VARCHAR,
    DECIMAL, dates, times, timestamps and SUPER.

    ## Execution Mode

    Fixed at server startup by the ACCESS_MODE environment variable, not per call. This
    server's resolved settings are listed at the end of its instructions.

    - Read-only (default): the statement runs inside `BEGIN READ ONLY ... ROLLBACK`, so
      nothing is persisted, and statement types the transaction cannot neutralize
      (`UNLOAD`, `GRANT`, `REVOKE`, `TRUNCATE`, `VACUUM`, `ANALYZE`, `COMMENT`, `CALL`,
      `CANCEL`, `SET`, `RESET`, `PREPARE`, `EXECUTE`, `DECLARE`, `FETCH`) are rejected
      before execution.
    - Read-write (`ACCESS_MODE=read-write`): the statement runs directly with autocommit
      and can create, modify and delete data and objects. Outside a transaction there is
      no rollback and nothing to undo.

    Transaction control is refused in both modes: `BEGIN`, `START`, `COMMIT`, `END`,
    `ROLLBACK` and `ABORT` belong to the transaction parameters below, not to `sql`. A
    statement that moved a boundary itself would leave this server and the engine
    disagreeing about what is open. `TRUNCATE` is refused inside a named transaction for the
    same reason, since it commits and cannot be rolled back; outside one it runs normally in
    read-write mode.

    In read-write mode a statement that may write is confirmed by the caller before it runs,
    while a recognized read runs unconfirmed. Confirmation is skipped entirely when the
    operator set `UNSAFE_SKIP_WRITE_CONFIRMATION=true`. A client that cannot prompt is
    refused rather than executed unconfirmed. Closing a transaction is not itself a write,
    so `commit_transaction` or `rollback_transaction` alone asks nothing.

    Both modes accept a single statement only; multi-statement submissions are rejected.

    ## Transactions

    Session state needs one: outside a transaction a temporary table or a `SET` is gone by the
    next call, though the statement that made it reports success.

    Name a transaction to keep it open across calls:

        begin_transaction='load' with the first statement, or on its own
        in_transaction='load' for each statement after that
        commit_transaction='load' or rollback_transaction='load' to end it

    At most one of the four per call. `sql` is optional on commit and rollback.

    Both modes support this. A read-only transaction gives several statements one
    consistent snapshot; a read-write one makes them succeed or fail together. Writes
    inside it are still confirmed one at a time, and a declined write leaves it open.

    A transaction is bound to this server process and to the cluster and database it was
    opened against, so the same name against a different pair is a different transaction and
    each call has to carry the pair its own transaction was opened on. A statement that fails
    inside one aborts it: it is rolled back and its
    name dropped, so the next call reports it as unknown rather than letting you commit
    nothing and call it done. Redshift ends one left idle for SESSION_KEEPALIVE seconds, and
    MAX_OPEN_TRANSACTIONS_PER_TARGET caps how many may be open at once against one cluster
    and database.

    Open and close a transaction in the same stretch of work, because while open it holds a
    Redshift connection and can block other writers on the tables it touched. Decide the
    statements it groups first, then run them with nothing in between: no waiting on the
    user, no waiting on another system, no exploring, no working out what to do next. If the
    user asks for one to be held open across any of that, tell them first that it stays open
    until they close it and may block other writers, then get their agreement.

    ## Security

    Avoid building SQL from untrusted input. The database user's privileges are the real
    boundary, so grant only what the workload needs.

    Requires redshift-data:BatchExecuteStatement, redshift-data:DescribeStatement and
    redshift-data:GetStatementResult.
    """
    try:
        logger.info(
            f'Executing query on cluster {cluster_identifier} in database {database_name} '
            f'(access mode: {ACCESS_MODE})'
        )

        if not confirmation.confirmed:
            raise ToolError('Statement not confirmed; nothing was executed.')

        query_result_data = await execute_query(
            cluster_identifier=cluster_identifier,
            database_name=database_name,
            sql=sql,
            enforce_read_only=ACCESS_MODE != ACCESS_MODE_READ_WRITE,
            begin_transaction=begin_transaction,
            in_transaction=in_transaction,
            commit_transaction=commit_transaction,
            rollback_transaction=rollback_transaction,
        )

        # Convert to QueryResult model
        query_result = QueryResult(**query_result_data)

        logger.info(
            f'Successfully executed query on cluster {cluster_identifier}: {query_result.row_count} rows returned'
        )
        return query_result

    except Exception as e:
        _tool_failed('execute_query_tool', e)


@mcp.tool(
    name='review_cluster',
    annotations=_read_only_annotations('Review Redshift cluster'),
)
async def review_cluster_tool(
    ctx: Context,
    cluster_identifier: str = Field(
        ...,
        description='The cluster identifier to run the review on. Must be a valid cluster identifier from the list_clusters tool.',
    ),
    database_name: str = Field(
        'dev',
        description='The database to connect to for querying system views. Defaults to "dev".',
    ),
) -> ReviewResult:
    """Run a diagnostic review of a Redshift cluster or serverless workgroup.

    Evaluates diagnostic signals against system views and returns the findings that
    triggered, with a recommendation for each. Provisioned-only diagnostics are skipped
    automatically for a serverless workgroup.

    Can take minutes: the diagnostics run one at a time.

    ## Reading the result

    - signals_evaluated: how many signals ran.
    - findings: one entry per triggered signal, carrying signal_name, section,
      affected_row_count, unit, and recommendation_ids.
    - recommendations: deduplicated, each with id, text (markdown, including
      documentation links) and triggered_by_signals. Their order carries no meaning: it is
      the order their signals first triggered, not effort and not impact.
    - queries_executed: names of the diagnostic queries that ran. One query carries several
      signals, so this is shorter than signals_evaluated.

    Count findings as len(findings), never from affected_row_count: that field counts
    affected objects in its own `unit` (7 tables, 3 nodes), so two findings each affecting
    7 tables is "2 findings across 7 tables", not 14. Each signal is an independent
    count(*) and one object can match several, so affected_row_count is NOT additive
    across findings or recommendations, and values in different units are NOT comparable.

    Zero findings means the cluster is healthy across every signal evaluated. Follow the
    documentation links in each recommendation. When there are findings, offer to act on
    them, starting with the lowest-effort, highest-impact items.

    ## Access

    The connected database user must be able to read Redshift system views, which requires
    superuser or the sys:monitor role:

        GRANT ROLE sys:monitor TO "<database_user>";

    <database_user> is the output of SELECT current_user, quoted because an IAM identity
    contains a colon (IAM:<user> or IAMR:<role>). Without that access the review fails
    fast rather than returning partial results.

    Requires redshift-data:BatchExecuteStatement, redshift-data:DescribeStatement and
    redshift-data:GetStatementResult.
    """
    try:
        logger.info(f'Running review on cluster {cluster_identifier}, database {database_name}')

        result = await review_cluster(
            cluster_identifier=cluster_identifier,
            execute_query_func=execute_query,
            discover_clusters_func=discover_clusters,
            database_name=database_name,
            progress_reporter_func=ctx.report_progress,
        )

        return result

    except Exception as e:
        _tool_failed('review_cluster_tool', e)


def main():
    """Run the MCP server with CLI argument support."""
    mcp.run()


if __name__ == '__main__':
    main()
