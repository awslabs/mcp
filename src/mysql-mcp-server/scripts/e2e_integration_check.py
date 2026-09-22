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

"""End-to-end integration test for mysql-mcp-server.

This test validates endpoint validation and connection behavior against
a real Aurora MySQL cluster. It requires:
  - A running Aurora MySQL cluster with Data API enabled
  - AWS credentials with access to RDS and Secrets Manager
  - Network connectivity to the cluster (VPC for mysqlwire methods)

This is a standalone script, not a pytest module: it is not collected by the
test runner (pytest's python_files = "test_*.py") and makes live AWS calls, so
it is not part of CI. Run it manually against a real cluster:

Usage:
    uv run python scripts/e2e_integration_check.py \
        --cluster-identifier <cluster-id> \
        --region <aws-region> \
        --database <db-name> \
        [--port 3306]
"""

import argparse
import asyncio
import awslabs.mysql_mcp_server.server as server_module
import json
import sys
from awslabs.mysql_mcp_server.connection.cp_api_connection import (
    internal_get_cluster_properties,
)
from awslabs.mysql_mcp_server.connection.db_connection_map import (
    ConnectionMethod,
    DatabaseType,
    DBConnectionMap,
)
from awslabs.mysql_mcp_server.server import internal_connect_to_database
from dataclasses import dataclass, field
from loguru import logger
from typing import List, Tuple


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class TestResult:
    """Stores pass/fail results for a test suite."""

    cluster_identifier: str
    connection_method_name: str
    passed: List[str] = field(default_factory=list)
    failed: List[Tuple[str, str]] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def log_step(step: str, status: str, detail: str = ''):
    """Log a test step with consistent formatting."""
    icon = '✓' if status == 'PASS' else '✗'
    msg = f'  {icon} [{status}] {step}'
    if detail:
        msg += f' — {detail}'
    logger.info(msg)


# ---------------------------------------------------------------------------
# Endpoint validation suite
# ---------------------------------------------------------------------------


def run_endpoint_validation_suite(
    cluster_identifier: str,
    region: str,
    database: str,
    valid_endpoint: str,
    port: int,
) -> TestResult:
    """Test the endpoint-validation security check in internal_connect_to_database.

    Positive case: caller-supplied db_endpoint matches the cluster's writer
    endpoint → connection succeeds, resolved endpoint in the response matches
    what AWS reports for the cluster.

    Negative case: caller-supplied db_endpoint is an arbitrary host that is
    not owned by the cluster → internal_connect_to_database must raise
    ValueError and no connection is created.

    The DB connection created here is cached in server.db_connection_map and
    reused by the main test suite that follows, so these checks don't add
    extra cluster warm-up cost.
    """
    result = TestResult(
        cluster_identifier=cluster_identifier,
        connection_method_name='endpoint_validation',
        passed=[],
        failed=[],
    )

    logger.info(f'\n{"=" * 60}')
    logger.info(f'Running endpoint validation suite on cluster: {cluster_identifier}')
    logger.info(f'{"=" * 60}')

    def record(step, ok, detail=''):
        """Record a test step result as passed or failed."""
        log_step(step, 'PASS' if ok else 'FAIL', detail)
        if ok:
            result.passed.append(step)
        else:
            result.failed.append((step, detail))

    # Use RDS_API for validation tests (no VPC needed, Data API is HTTP-based)
    method = ConnectionMethod.RDS_API

    # Positive case — db_endpoint matches the cluster's writer endpoint.
    step = 'endpoint_validation_positive(writer endpoint accepted)'
    try:
        # Reset connection map to ensure we go through the full validation path
        server_module.db_connection_map = DBConnectionMap()

        db_conn, llm_response = internal_connect_to_database(
            region=region,
            database_type=DatabaseType.AURORA_MYSQL,
            connection_method=method,
            cluster_identifier=cluster_identifier,
            db_endpoint=valid_endpoint,
            port=port,
            database=database,
        )
        resp_dict = json.loads(llm_response)
        # The response echoes the resolved (AWS-sourced) endpoint/port. For the
        # writer endpoint we just passed, host should match case-insensitively
        # and port should round-trip.
        host_ok = resp_dict.get('db_endpoint', '').lower() == valid_endpoint.lower()
        port_ok = int(resp_dict.get('port') or 0) == port
        ok = db_conn is not None and host_ok and port_ok
        record(
            step,
            ok,
            f'resolved={resp_dict.get("db_endpoint")}:{resp_dict.get("port")}',
        )
    except Exception as e:
        record(step, False, str(e))

    # Negative case — arbitrary host that does not belong to the cluster.
    step = 'endpoint_validation_negative(bogus endpoint rejected)'
    bogus_endpoint = 'attacker.example.com'
    try:
        internal_connect_to_database(
            region=region,
            database_type=DatabaseType.AURORA_MYSQL,
            connection_method=method,
            cluster_identifier=cluster_identifier,
            db_endpoint=bogus_endpoint,
            port=port,
            database=database,
        )
        record(step, False, f'Expected ValueError for endpoint {bogus_endpoint}, got success')
    except ValueError as e:
        msg = str(e)
        ok = bogus_endpoint in msg and cluster_identifier in msg
        record(step, ok, msg)
    except Exception as e:
        record(step, False, f'Expected ValueError, got {type(e).__name__}: {e}')

    # Negative case — valid host with a wrong port.
    step = 'endpoint_validation_negative(wrong port rejected)'
    wrong_port = port + 1
    try:
        internal_connect_to_database(
            region=region,
            database_type=DatabaseType.AURORA_MYSQL,
            connection_method=method,
            cluster_identifier=cluster_identifier,
            db_endpoint=valid_endpoint,
            port=wrong_port,
            database=database,
        )
        record(step, False, f'Expected ValueError for port {wrong_port}, got success')
    except ValueError as e:
        msg = str(e)
        ok = str(wrong_port) in msg and cluster_identifier in msg
        record(step, ok, msg)
    except Exception as e:
        record(step, False, f'Expected ValueError, got {type(e).__name__}: {e}')

    # Negative case — localhost/loopback (common SSRF target).
    step = 'endpoint_validation_negative(localhost rejected)'
    try:
        internal_connect_to_database(
            region=region,
            database_type=DatabaseType.AURORA_MYSQL,
            connection_method=method,
            cluster_identifier=cluster_identifier,
            db_endpoint='127.0.0.1',
            port=port,
            database=database,
        )
        record(step, False, 'Expected ValueError for localhost, got success')
    except ValueError as e:
        msg = str(e)
        ok = '127.0.0.1' in msg
        record(step, ok, msg)
    except Exception as e:
        record(step, False, f'Expected ValueError, got {type(e).__name__}: {e}')

    # Negative case — IP address (not a valid RDS endpoint form).
    step = 'endpoint_validation_negative(arbitrary IP rejected)'
    try:
        internal_connect_to_database(
            region=region,
            database_type=DatabaseType.AURORA_MYSQL,
            connection_method=method,
            cluster_identifier=cluster_identifier,
            db_endpoint='10.0.0.1',
            port=port,
            database=database,
        )
        record(step, False, 'Expected ValueError for IP address, got success')
    except ValueError as e:
        msg = str(e)
        ok = '10.0.0.1' in msg
        record(step, ok, msg)
    except Exception as e:
        record(step, False, f'Expected ValueError, got {type(e).__name__}: {e}')

    return result


# ---------------------------------------------------------------------------
# Query execution suite (validates connection actually works)
# ---------------------------------------------------------------------------


async def run_query_suite(
    cluster_identifier: str,
    region: str,
    database: str,
    valid_endpoint: str,
    port: int,
) -> TestResult:
    """Test basic query execution against the cluster after validation passes.

    This confirms that the endpoint validation doesn't break legitimate
    connections — queries still work when the endpoint is valid.
    """
    from awslabs.mysql_mcp_server.server import run_query

    result = TestResult(
        cluster_identifier=cluster_identifier,
        connection_method_name='query_execution',
        passed=[],
        failed=[],
    )

    logger.info(f'\n{"=" * 60}')
    logger.info(f'Running query execution suite on cluster: {cluster_identifier}')
    logger.info(f'{"=" * 60}')

    def record(step, ok, detail=''):
        log_step(step, 'PASS' if ok else 'FAIL', detail)
        if ok:
            result.passed.append(step)
        else:
            result.failed.append((step, detail))

    method = ConnectionMethod.RDS_API

    # SELECT 1 — basic connectivity check
    step = 'query_execution(SELECT 1)'
    try:

        class MockCtx:
            async def error(self, msg):
                pass

        response = await run_query(
            sql='SELECT 1 AS test_col',
            ctx=MockCtx(),
            connection_method=method,
            cluster_identifier=cluster_identifier,
            db_endpoint=valid_endpoint,
            database=database,
        )
        if isinstance(response, list) and len(response) == 1:
            ok = response[0].get('test_col') == 1
            record(step, ok, f'response={response}')
        else:
            record(step, False, f'Unexpected response: {response}')
    except Exception as e:
        record(step, False, f'{type(e).__name__}: {e}')

    return result


# ---------------------------------------------------------------------------
# Summary printer
# ---------------------------------------------------------------------------


def print_summary(results: List[TestResult]) -> bool:
    """Print a formatted summary of all test results. Returns True if all passed."""
    logger.info(f'\n{"=" * 60}')
    logger.info('TEST SUMMARY')
    logger.info(f'{"=" * 60}')

    total_passed = 0
    total_failed = 0

    for r in results:
        passed = len(r.passed)
        failed = len(r.failed)
        total_passed += passed
        total_failed += failed
        status = '✓ PASS' if failed == 0 else '✗ FAIL'
        logger.info(
            f'  {status} | {r.connection_method_name} on {r.cluster_identifier} '
            f'| {passed} passed, {failed} failed'
        )
        for step, detail in r.failed:
            logger.info(f'         ✗ {step}: {detail}')

    logger.info(f'\n  TOTAL: {total_passed} passed, {total_failed} failed')
    logger.info(f'{"=" * 60}')

    return total_failed == 0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


async def main_async(args):
    """Run all E2E test suites."""
    results: List[TestResult] = []

    # Reset global state
    server_module.db_connection_map = DBConnectionMap()
    server_module.readonly_query = True
    server_module.ca_bundle_path = None

    # Fetch cluster properties to get the valid endpoint
    logger.info(f'Fetching cluster properties for: {args.cluster_identifier}')
    cluster_properties = internal_get_cluster_properties(
        cluster_identifier=args.cluster_identifier,
        region=args.region,
    )
    valid_endpoint = cluster_properties.get('Endpoint', '')
    port = int(cluster_properties.get('Port', args.port))
    logger.info(f'Cluster writer endpoint: {valid_endpoint}:{port}')

    # Phase 1: Endpoint validation (the security fix)
    results.append(
        run_endpoint_validation_suite(
            cluster_identifier=args.cluster_identifier,
            region=args.region,
            database=args.database,
            valid_endpoint=valid_endpoint,
            port=port,
        )
    )

    # Phase 2: Query execution (confirms fix doesn't break legitimate usage)
    results.append(
        await run_query_suite(
            cluster_identifier=args.cluster_identifier,
            region=args.region,
            database=args.database,
            valid_endpoint=valid_endpoint,
            port=port,
        )
    )

    # Summary
    all_passed = print_summary(results)
    return all_passed


def main():
    """CLI entry point for E2E tests."""
    parser = argparse.ArgumentParser(
        description='E2E integration tests for mysql-mcp-server endpoint validation'
    )
    parser.add_argument(
        '--cluster-identifier',
        required=True,
        help='Aurora MySQL cluster identifier',
    )
    parser.add_argument(
        '--region',
        required=True,
        help='AWS region',
    )
    parser.add_argument(
        '--database',
        default='mysql',
        help='Database name (default: mysql)',
    )
    parser.add_argument(
        '--port',
        type=int,
        default=3306,
        help='Database port (default: 3306)',
    )

    args = parser.parse_args()

    logger.info('E2E Test Configuration:')
    logger.info(f'  Cluster: {args.cluster_identifier}')
    logger.info(f'  Region: {args.region}')
    logger.info(f'  Database: {args.database}')
    logger.info(f'  Port: {args.port}')

    all_passed = asyncio.run(main_async(args))
    sys.exit(0 if all_passed else 1)


if __name__ == '__main__':
    main()
