r"""End-to-end integration test for postgres MCP server.

Runs against real Aurora PostgreSQL clusters created during the test.
Creates one Express cluster and one Serverless cluster:
- Express cluster: tested with PG_WIRE_IAM_PROTOCOL (only supported method)
- Serverless cluster: tested with all 3 connection methods (RDS_API, PG_WIRE_IAM_PROTOCOL, PG_WIRE_PROTOCOL)
Then cleans up both clusters.

Usage:
    python tests/e2e_integration_test.py --region us-east-1 --engine-version 16.4

    python tests/e2e_integration_test.py \\
        --region us-east-1 \\
        --engine-version 16.4 \\
        --database mcp_test_db \\
        --port 5432
"""

import argparse
import asyncio
import awslabs.postgres_mcp_server.server as server
import json
import sys
import time
from awslabs.postgres_mcp_server.connection.cp_api_connection import internal_delete_cluster
from awslabs.postgres_mcp_server.connection.db_connection_map import ConnectionMethod, DatabaseType
from awslabs.postgres_mcp_server.server import (
    DummyCtx,
    connect_to_database,
    create_cluster,
    get_database_connection_info,
    get_job_status,
    get_table_schema,
    is_database_connected,
    run_query,
)
from dataclasses import dataclass
from datetime import datetime
from loguru import logger


@dataclass
class ClusterConfig:
    """Configuration for connecting to and testing an Aurora cluster."""

    cluster_identifier: str
    region: str
    database: str
    connection_method: ConnectionMethod
    db_endpoint: str
    port: int
    connection_method_name: str
    cluster_type: str  # 'express' or 'serverless'


@dataclass
class TestResult:
    """Result of running a test suite against one cluster with one connection method."""

    cluster_identifier: str
    connection_method_name: str
    passed: list
    failed: list  # list of (step_name, error_message) tuples

    @property
    def success(self) -> bool:
        """Return True if all test steps passed."""
        return len(self.failed) == 0


def log_step(step: str, status: str, detail: str = ''):
    """Log a test step with a status marker (✓ PASS, ✗ FAIL, → INFO)."""
    msg = f'  [{status}] {step}'
    if detail:
        msg += f': {detail}'
    if status == 'PASS':
        logger.success(msg)
    elif status == 'FAIL':
        logger.error(msg)
    else:
        logger.info(msg)


def create_express_cluster(
    cluster_identifier: str, region: str, database: str, engine_version: str
) -> str:
    """Create express cluster synchronously. Returns db_endpoint."""
    log_step('create_cluster (express)', 'INFO', cluster_identifier)
    result_json = create_cluster(
        region=region,
        cluster_identifier=cluster_identifier,
        database=database,
        engine_version=engine_version,
        with_express_configuration=True,
    )
    result = json.loads(result_json)
    if result.get('status') != 'Completed':
        raise RuntimeError(f'Express cluster creation failed: {result}')
    endpoint = result['db_endpoint']
    log_step('create_cluster (express)', 'PASS', f'endpoint={endpoint}')
    wait_for_dns(endpoint)
    return endpoint


def create_serverless_cluster_and_wait(
    cluster_identifier: str,
    region: str,
    database: str,
    engine_version: str,
    poll_interval: int = 30,
    max_attempts: int = 40,
) -> str:
    """Create serverless cluster async, poll until done. Returns db_endpoint."""
    log_step('create_cluster (serverless)', 'INFO', cluster_identifier)
    result_json = create_cluster(
        region=region,
        cluster_identifier=cluster_identifier,
        database=database,
        engine_version=engine_version,
        with_express_configuration=False,
    )
    result = json.loads(result_json)
    job_id = result.get('job_id')
    if not job_id:
        raise RuntimeError(f'No job_id returned from create_cluster: {result}')

    logger.info(f'  Polling job {job_id} every {poll_interval}s (max {max_attempts} attempts)...')
    for attempt in range(1, max_attempts + 1):
        status = get_job_status(job_id)
        state = status.get('state')
        logger.info(f'  Attempt {attempt}/{max_attempts}: state={state}')
        if state == 'succeeded':
            break
        elif state == 'failed':
            raise RuntimeError(f'Serverless cluster creation failed: {status}')
        time.sleep(poll_interval)
    else:
        raise RuntimeError(f'Serverless cluster creation timed out after {max_attempts} attempts')

    # Retrieve endpoint from cluster properties
    from awslabs.postgres_mcp_server.connection.cp_api_connection import (
        internal_get_cluster_properties,
    )

    props = internal_get_cluster_properties(cluster_identifier, region)
    endpoint = props['Endpoint']
    log_step('create_cluster (serverless)', 'PASS', f'endpoint={endpoint}')
    wait_for_dns(endpoint)
    return endpoint


def wait_for_dns(endpoint: str, max_wait: int = 120, interval: int = 10):
    """Wait until the endpoint DNS resolves."""
    import socket

    logger.info(f'  Waiting for DNS resolution of {endpoint} (max {max_wait}s)...')
    elapsed = 0
    while elapsed < max_wait:
        try:
            socket.getaddrinfo(endpoint, 5432)
            logger.info(f'  DNS resolved for {endpoint} after {elapsed}s')
            return
        except socket.gaierror:
            time.sleep(interval)
            elapsed += interval
    raise RuntimeError(f'DNS for {endpoint} not resolvable after {max_wait}s')


async def run_test_suite(config: ClusterConfig, table_suffix: str) -> TestResult:
    """Run the full MCP tool test suite against one cluster."""
    ctx = DummyCtx()
    result = TestResult(
        cluster_identifier=config.cluster_identifier,
        connection_method_name=config.connection_method_name,
        passed=[],
        failed=[],
    )
    table_name = f'mcp_test_{table_suffix}'
    cluster_display = f'{config.cluster_type} ({config.connection_method_name})'
    # Always use 'postgres' database for testing
    test_database = 'postgres'

    logger.info(f'\n{"=" * 60}')
    logger.info(f'Running test suite on {cluster_display} cluster: {config.cluster_identifier}')
    logger.info(f'{"=" * 60}')

    def record(step, ok, detail=''):
        """Record a test step result as passed or failed."""
        log_step(step, 'PASS' if ok else 'FAIL', detail)
        if ok:
            result.passed.append(step)
        else:
            result.failed.append((step, detail))

    # 1. connect_to_database
    step = 'connect_to_database'
    try:
        resp = await connect_to_database(
            region=config.region,
            database_type=DatabaseType.APG,
            connection_method=config.connection_method,
            cluster_identifier=config.cluster_identifier,
            db_endpoint=config.db_endpoint,
            port=config.port,
            database=test_database,
        )
        ok = 'Failed' not in resp
        record(step, ok, resp)
        if not ok:
            logger.error(f'Cannot continue suite without connection. Aborting {cluster_display}.')
            return result
    except Exception as e:
        record(step, False, str(e))
        logger.error(f'Cannot continue suite without connection. Aborting {cluster_display}.')
        return result

    # 2. is_database_connected
    step = 'is_database_connected'
    try:
        connected = is_database_connected(
            cluster_identifier=config.cluster_identifier,
            db_endpoint=config.db_endpoint,
            database=test_database,
        )
        record(step, connected, str(connected))
    except Exception as e:
        record(step, False, str(e))

    # 3. get_database_connection_info
    step = 'get_database_connection_info'
    try:
        info = get_database_connection_info()
        record(step, True, info)
    except Exception as e:
        record(step, False, str(e))

    # 4. run_query SELECT version()
    step = 'run_query(SELECT version())'
    try:
        rows = await run_query(
            sql='SELECT version()',
            ctx=ctx,
            connection_method=config.connection_method,
            cluster_identifier=config.cluster_identifier,
            db_endpoint=config.db_endpoint,
            database=test_database,
        )
        ok = rows and 'error' not in rows[0]
        record(step, ok, str(rows[0]) if rows else 'no rows')
    except Exception as e:
        record(step, False, str(e))

    # 5. run_query CREATE TABLE
    step = f'run_query(CREATE TABLE {table_name})'
    try:
        rows = await run_query(
            sql=f'CREATE TABLE {table_name} (id INT, name TEXT)',
            ctx=ctx,
            connection_method=config.connection_method,
            cluster_identifier=config.cluster_identifier,
            db_endpoint=config.db_endpoint,
            database=test_database,
        )
        ok = not rows or 'error' not in rows[0]
        record(step, ok, str(rows))
    except Exception as e:
        record(step, False, str(e))

    # 6. run_query INSERT
    step = f'run_query(INSERT INTO {table_name})'
    try:
        rows = await run_query(
            sql=f"INSERT INTO {table_name} VALUES (1, 'hello')",
            ctx=ctx,
            connection_method=config.connection_method,
            cluster_identifier=config.cluster_identifier,
            db_endpoint=config.db_endpoint,
            database=test_database,
        )
        ok = not rows or 'error' not in rows[0]
        record(step, ok, str(rows))
    except Exception as e:
        record(step, False, str(e))

    # 7. run_query SELECT
    step = f'run_query(SELECT * FROM {table_name})'
    try:
        rows = await run_query(
            sql=f'SELECT * FROM {table_name}',
            ctx=ctx,
            connection_method=config.connection_method,
            cluster_identifier=config.cluster_identifier,
            db_endpoint=config.db_endpoint,
            database=test_database,
        )
        ok = rows and 'error' not in rows[0] and len(rows) == 1
        record(step, ok, f'{len(rows)} row(s)' if rows else 'no rows')
    except Exception as e:
        record(step, False, str(e))

    # 8. get_table_schema
    step = f'get_table_schema({table_name})'
    try:
        rows = await get_table_schema(
            connection_method=config.connection_method,
            cluster_identifier=config.cluster_identifier,
            db_endpoint=config.db_endpoint,
            database=test_database,
            table_name=table_name,
            ctx=ctx,
        )
        ok = rows and 'error' not in rows[0] and len(rows) >= 1
        record(step, ok, f'{len(rows)} column(s)' if rows else 'no columns')
    except Exception as e:
        record(step, False, str(e))

    # 9. run_query DROP TABLE (should be rejected as risky command)
    step = f'run_query(DROP TABLE {table_name}) - expect rejection'
    try:
        rows = await run_query(
            sql=f'DROP TABLE {table_name}',
            ctx=ctx,
            connection_method=config.connection_method,
            cluster_identifier=config.cluster_identifier,
            db_endpoint=config.db_endpoint,
            database=test_database,
        )
        # Expect error because DROP is a risky command
        ok = rows and 'error' in rows[0]
        record(
            step, ok, 'Correctly rejected DROP command' if ok else 'DROP should have been rejected'
        )
    except Exception as e:
        record(step, False, str(e))

    # 10. Manual cleanup - delete table directly via psycopg (bypass MCP restrictions)
    step = f'Manual cleanup: DROP TABLE {table_name}'
    try:
        # Get the connection from the map
        from awslabs.postgres_mcp_server.server import db_connection_map

        db_conn = db_connection_map.get(
            config.connection_method,
            config.cluster_identifier,
            config.db_endpoint,
            test_database,
            config.port,
        )

        if db_conn:
            # Temporarily disable readonly to allow cleanup
            original_readonly = db_conn.readonly_query
            db_conn._readonly = False

            await db_conn.execute_query(f'DROP TABLE IF EXISTS {table_name}')

            # Restore readonly setting
            db_conn._readonly = original_readonly

            record(step, True, 'Table cleaned up')
        else:
            record(step, False, 'Could not get database connection for cleanup')
    except Exception as e:
        record(step, False, str(e))

    return result


def print_summary(results: list[TestResult]):
    """Print a formatted summary of all test results. Returns True if all passed."""
    logger.info(f'\n{"=" * 60}')
    logger.info('TEST SUMMARY')
    logger.info(f'{"=" * 60}')
    all_passed = True
    for r in results:
        status = 'PASSED' if r.success else 'FAILED'
        logger.info(f'\n  {r.connection_method_name} ({r.cluster_identifier}): {status}')
        for s in r.passed:
            logger.info(f'    ✓ {s}')
        for step, error in r.failed:
            logger.error(f'    ✗ {step}')
            if error:
                logger.error(f'      Error: {error}')
        if not r.success:
            all_passed = False
    logger.info(f'\n{"=" * 60}')
    logger.info(f'Overall: {"ALL PASSED" if all_passed else "SOME FAILED"}')
    logger.info(f'{"=" * 60}\n')
    return all_passed


async def main_async(args):
    """Main async entry point. Creates clusters, runs test suites, prints summary, and cleans up."""
    server.readonly_query = False

    ts = datetime.now().strftime('%Y%m%d%H%M%S')
    table_suffix = ts

    results = []
    clusters_to_delete = []

    try:
        # Phase 1: Create and test express cluster with PG_WIRE_IAM_PROTOCOL
        express_id = f'mcp-e2e-express-{ts}'
        express_endpoint = create_express_cluster(
            cluster_identifier=express_id,
            region=args.region,
            database=args.database,
            engine_version=args.engine_version,
        )
        clusters_to_delete.append(express_id)

        express_config = ClusterConfig(
            cluster_identifier=express_id,
            region=args.region,
            database=args.database,
            connection_method=ConnectionMethod.PG_WIRE_IAM_PROTOCOL,
            db_endpoint=express_endpoint,
            port=args.port,
            connection_method_name='PG_WIRE_IAM_PROTOCOL',
            cluster_type='express',
        )
        results.append(await run_test_suite(express_config, f'{table_suffix}_express'))

        # Phase 2: Create and test serverless cluster
        serverless_id = f'mcp-e2e-serverless-{ts}'
        serverless_endpoint = create_serverless_cluster_and_wait(
            cluster_identifier=serverless_id,
            region=args.region,
            database=args.database,
            engine_version=args.engine_version,
        )
        clusters_to_delete.append(serverless_id)

        connection_methods = [
            (ConnectionMethod.RDS_API, 'RDS_API'),
        ]

        if args.test_pgwire:
            connection_methods.extend(
                [
                    (ConnectionMethod.PG_WIRE_IAM_PROTOCOL, 'PG_WIRE_IAM_PROTOCOL'),
                    (ConnectionMethod.PG_WIRE_PROTOCOL, 'PG_WIRE_PROTOCOL'),
                ]
            )

        for conn_method, conn_name in connection_methods:
            config = ClusterConfig(
                cluster_identifier=serverless_id,
                region=args.region,
                database=args.database,
                connection_method=conn_method,
                db_endpoint=serverless_endpoint,
                port=args.port,
                connection_method_name=conn_name,
                cluster_type='serverless',
            )
            results.append(await run_test_suite(config, f'{table_suffix}_serverless_{conn_name}'))

    except Exception as e:
        logger.error(f'Test suite failed with error: {e}')
        import traceback

        traceback.print_exc()

    # Print summary before cleanup
    all_passed = print_summary(results)

    # Cleanup clusters
    logger.info('Cleaning up clusters...')

    async def delete_cluster_safe(cluster_id: str):
        """Delete a cluster, logging errors instead of raising."""
        try:
            logger.info(f'Deleting cluster: {cluster_id}')
            await asyncio.to_thread(internal_delete_cluster, args.region, cluster_id)
            logger.success(f'Deleted cluster: {cluster_id}')
        except Exception as e:
            logger.warning(f'Failed to delete {cluster_id}: {e}')

    await asyncio.gather(*[delete_cluster_safe(cid) for cid in clusters_to_delete])

    sys.exit(0 if all_passed else 1)


def main():
    """Parse CLI arguments and run the e2e integration test."""
    parser = argparse.ArgumentParser(
        description='End-to-end integration test for postgres MCP server'
    )
    parser.add_argument('--region', required=True, help='AWS region (e.g. us-east-1)')
    parser.add_argument(
        '--engine-version', required=True, help='Aurora PostgreSQL engine version (e.g. 16.4)'
    )
    parser.add_argument(
        '--database', default='mcp_test_db', help='Database name (default: mcp_test_db)'
    )
    parser.add_argument('--port', type=int, default=5432, help='Database port (default: 5432)')
    parser.add_argument(
        '--test-pgwire',
        action='store_true',
        default=False,
        help='Also test PG_WIRE_IAM_PROTOCOL and PG_WIRE_PROTOCOL (requires VPC access, default: False)',
    )
    args = parser.parse_args()

    asyncio.run(main_async(args))


if __name__ == '__main__':
    main()
