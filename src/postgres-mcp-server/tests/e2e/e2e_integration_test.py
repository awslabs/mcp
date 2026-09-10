r"""End-to-end integration test for postgres MCP server.

Runs against real Aurora PostgreSQL clusters created during the test.

By default ONLY an Express cluster is created and tested — this keeps the
default run fast (express provisions in well under a minute, whereas the
serverless cluster + instance adds roughly 7-8 minutes).

- Express cluster (default): tested with PG_WIRE_IAM_PROTOCOL (the only
  method express supports). Express is publicly reachable so this needs
  no special network setup.
- Serverless (regular) cluster: created only with
  --test-serverless-cluster. Tested with RDS_API (public HTTPS). Add
  --test-non-express-cluster to also test PG_WIRE_IAM_PROTOCOL and
  PG_WIRE_PROTOCOL — those open a Postgres pool on TCP 5432 and require
  the test host to have VPC reachability to the cluster.
  (--test-non-express-cluster implies --test-serverless-cluster.)

Whichever clusters are created are cleaned up at the end.

Endpoint / auth selection:
    Prefer --endpoint-types and --auth-types over the legacy flags. Endpoint
    types: express, serverless (rds-instance is planned, not yet supported).
    Auth types: pg_wire_iam, pg_wire_secret, rds_api -- filtered by each
    endpoint's supported set (express -> pg_wire_iam; serverless -> rds_api,
    pg_wire_iam, pg_wire_secret). An impossible combination (e.g. express +
    rds_api) is rejected. When neither flag is given, the legacy
    --test-serverless-cluster / --test-non-express-cluster behavior applies.
    See tests/e2e/run_e2e.sh for a wrapper that refreshes credentials (ada)
    and enumerates the Aurora endpoints by default.

Usage:
    # Default: express-only, fast
    python tests/e2e_integration_test.py --region us-east-1 --engine-version 16.4

    # New interface: all Aurora endpoints, all supported auth methods
    python tests/e2e_integration_test.py --region us-east-1 --engine-version 16.4 \\
        --endpoint-types express,serverless \\
        --auth-types pg_wire_iam,pg_wire_secret,rds_api

    # Also create + test the serverless cluster via RDS_API
    python tests/e2e_integration_test.py \\
        --region us-east-1 \\
        --engine-version 16.4 \\
        --database mcp_test_db \\
        --port 5432 \\
        --test-serverless-cluster

    # Full run including serverless PG Wire (needs VPC reachability)
    python tests/e2e_integration_test.py \\
        --region us-east-1 \\
        --engine-version 16.4 \\
        --database mcp_test_db \\
        --port 5432 \\
        --test-non-express-cluster

    # Verbose mode for debugging:
    python tests/e2e_integration_test.py \\
        --region us-east-1 --engine-version 16.4 \\
        --log-level DEBUG
"""

import argparse
import asyncio
import awslabs.postgres_mcp_server.server as server
import json
import os
import psycopg
import shutil
import subprocess
import sys
import tempfile
import time
from awslabs.postgres_mcp_server.connection.cp_api_connection import internal_delete_cluster
from awslabs.postgres_mcp_server.connection.db_connection_map import ConnectionMethod, DatabaseType
from awslabs.postgres_mcp_server.connection.psycopg_pool_connection import _bundled_ca_file
from awslabs.postgres_mcp_server.server import (
    DummyCtx,
    connect_to_database,
    create_cluster,
    get_database_connection_info,
    get_job_status,
    get_table_schema,
    internal_create_connection,
    is_database_connected,
    run_query,
)
from awslabs.postgres_mcp_server.sql_guard import (
    DANGEROUS_FUNCTIONS,
    DANGEROUS_QUALIFIED_FUNCTIONS,
    READ_ONLY_PROHIBITED_MUTATING_FUNCTIONS,
    READ_ONLY_PROHIBITED_QUALIFIED_FUNCTIONS,
    SECURITY_SENSITIVE_GUCS,
)
from dataclasses import dataclass
from datetime import datetime
from functools import partial
from loguru import logger
from typing import Any, List, Optional, Tuple


# Managed prefix lists authorized to reach the test serverless cluster on
# tcp:5432 when --test-non-express-cluster is set. These IDs are
# Amazon-managed lists covering the corp/VPN egress this test runs from;
# pinning to them keeps the SG stable across runs and across developer
# machines instead of churning on per-run egress IPs.
E2E_TEST_PREFIX_LIST_IDS = ['pl-aea742c7', 'pl-f8a64391', 'pl-45a6432c']


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
    # (step, reason) tuples for checks that could NOT run (missing tooling, or a
    # cluster that failed to create). Counts as not-pass -> fails the run.
    skipped: Optional[list] = None
    # (step, reason) tuples for by-design-impossible or operator-opted-out
    # combinations (e.g. RDS Data API on an express cluster). Surfaced honestly
    # as N/A but does NOT count against success -- there is nothing to verify.
    not_applicable: Optional[list] = None

    def __post_init__(self):
        """Default the optional lists to empty."""
        if self.skipped is None:
            self.skipped = []
        if self.not_applicable is None:
            self.not_applicable = []

    @property
    def success(self) -> bool:
        """Return True if all *applicable* test steps passed.

        Skipped steps (a check that could not run -- missing CA bundle/openssl,
        or a cluster that failed to create) count as not-pass, so they cascade
        into a non-zero exit code. Not-applicable steps (a by-design-impossible
        or operator-opted-out combination) do NOT count against success: there
        is nothing to verify, so they are neither a pass nor a failure.
        """
        return len(self.failed) == 0 and len(self.skipped or []) == 0


def log_step(step: str, status: str, detail: str = ''):
    """Log a test step with a status marker (PASS, FAIL, SKIP, N/A, INFO)."""
    msg = f'  [{status}] {step}'
    if detail:
        msg += f': {detail}'
    if status == 'PASS':
        logger.success(msg)
    elif status == 'FAIL':
        logger.error(msg)
    elif status == 'SKIP':
        logger.warning(msg)
    else:  # N/A, INFO, and any other marker are informational
        logger.info(msg)


def record_not_applicable(result: 'TestResult', step: str, reason: str) -> None:
    """Record a step as not-applicable: a by-design-impossible / opted-out combo.

    Surfaced honestly as ``[N/A]`` but does NOT count against
    ``TestResult.success`` -- unlike a pass it does not claim the check ran, and
    unlike a skip/failure it does not fail the run. Use ONLY when the
    combination genuinely does not exist (e.g. RDS Data API on an express
    cluster, or an operator opting out via a flag), never when a check that
    should run could not.
    """
    log_step(step, 'N/A', reason)
    assert result.not_applicable is not None
    result.not_applicable.append((step, reason))


_PGWIRE_METHODS = (
    ConnectionMethod.PG_WIRE_IAM_PROTOCOL,
    ConnectionMethod.PG_WIRE_PROTOCOL,
)


def _is_pgwire_method(method: ConnectionMethod) -> bool:
    """True for the direct Postgres (psycopg) methods that do a TLS handshake."""
    return method in _PGWIRE_METHODS


def log_tls_diagnostics(
    host: str,
    port: int,
    ca_bundle: Optional[str],
    sslmode: str,
    label: str = '',
) -> None:
    """Log the server certificate chain and CA-verification result for an endpoint.

    A best-effort troubleshooting aid for SSL/auth failures on the psycopg
    (PG-Wire) path: it records *what certificate the server presented*
    (subject / issuer chain + SubjectAltName) and *what validation was applied*
    (sslmode + which CA bundle), plus OpenSSL's verify result against that CA.
    Uses ``openssl s_client`` (already required by the TLS suite's throwaway-CA
    helper). Never raises -- diagnostics must not perturb the run.
    """
    tag = f'TLS-DIAG{f" [{label}]" if label else ""}'
    ca_desc = ca_bundle if ca_bundle else '(bundled AWS CA / system default)'
    logger.info(f'{tag}: endpoint={host}:{port} sslmode={sslmode} ca_bundle={ca_desc}')

    openssl = shutil.which('openssl')
    if not openssl:
        logger.info(f'{tag}: openssl not on PATH; cannot capture server certificate')
        return

    cmd = [
        openssl,
        's_client',
        '-starttls',
        'postgres',
        '-connect',
        f'{host}:{port}',
        '-showcerts',
    ]
    if ca_bundle and ca_bundle != 'system':
        cmd += ['-CAfile', ca_bundle]
    cmd += ['-verify_hostname', host]

    try:
        proc = subprocess.run(cmd, input=b'', capture_output=True, timeout=20)
        out = (
            proc.stdout.decode('utf-8', 'replace') + '\n' + proc.stderr.decode('utf-8', 'replace')
        )
    except Exception as e:
        logger.info(f'{tag}: certificate probe failed: {type(e).__name__}: {e}')
        return

    # Chain: OpenSSL prints "s:<subject>" / "i:<issuer>" per cert, plus a final
    # "Verify return code: N (...)". Surface both.
    chain = [ln.strip() for ln in out.splitlines() if ln.strip()[:2] in ('s:', 'i:')]
    verify = [
        ln.strip()
        for ln in out.splitlines()
        if 'Verify return code' in ln or ln.strip().startswith('verify error')
    ]
    if chain:
        logger.info(f'{tag}: server certificate chain (s=subject, i=issuer):')
        for ln in chain:
            logger.info(f'{tag}:   {ln}')
    else:
        logger.info(f'{tag}: no certificate captured (handshake may have failed): {out[:200]}')

    san = _extract_leaf_san(out, openssl)
    if san:
        logger.info(f'{tag}: leaf SubjectAltName: {san}')
    for ln in verify:
        logger.info(f'{tag}: {ln}')


def _extract_leaf_san(s_client_output: str, openssl: str) -> str:
    """Pull the leaf cert's SubjectAltName out of ``openssl s_client`` output.

    Feeds the first PEM certificate block back through ``openssl x509`` to read
    its SAN. Returns '' if it can't be determined. Never raises.
    """
    begin = s_client_output.find('-----BEGIN CERTIFICATE-----')
    end = s_client_output.find('-----END CERTIFICATE-----')
    if begin == -1 or end == -1:
        return ''
    leaf_pem = s_client_output[begin : end + len('-----END CERTIFICATE-----')] + '\n'
    try:
        proc = subprocess.run(
            [openssl, 'x509', '-noout', '-ext', 'subjectAltName'],
            input=leaf_pem.encode(),
            capture_output=True,
            timeout=10,
        )
        text = (
            proc.stdout.decode('utf-8', 'replace') + proc.stderr.decode('utf-8', 'replace')
        ).strip()
    except Exception:
        return ''
    # Output is typically two lines: the extension name then the DNS: entries.
    for line in text.splitlines():
        line = line.strip()
        if line.startswith('DNS:') or line.startswith('IP Address:'):
            return line
    return ''


# ---------------------------------------------------------------------------
# Endpoint-type x auth-type run planning
# ---------------------------------------------------------------------------
# Which auth methods each endpoint type actually supports. Enforced so an
# operator can't request a combination the platform can't do:
#   * express (Aurora) -> IAM only, for two different reasons. Password auth is
#     impossible: express fixes the master user authentication type to
#     iam-db-auth ("cannot be modified"), master password and Secrets Manager
#     master credentials are both documented as not applicable, and the internet
#     access gateway accepts only ephemeral IAM tokens -- so no role reaches the
#     database with a password, not just the master. The Data API is a weaker
#     "no": its HTTP endpoint is merely disabled by default and CAN be enabled
#     after creation, but the Data API authenticates through a Secrets Manager
#     secret carrying a username and password, and express has no password auth,
#     so RDS_API would still fail at authentication. Note also that
#     WithExpressConfiguration=True sets every other CreateDBCluster input
#     itself, so neither EnableHttpEndpoint nor ManageMasterUserPassword can be
#     requested at creation time.
#   * serverless (Aurora v2) supports the Data API (public HTTPS) and, with VPC
#     reachability, both PG-Wire auth modes.
#   * rds-instance (standalone RDS PostgreSQL) is planned but NOT yet provisioned
#     by this harness -- Aurora endpoints only for now. (The RDS Data API is
#     Aurora-only, so when added it will support PG-Wire auth only.)
ENDPOINT_AUTH_CAPABILITY = {
    'express': ('pg_wire_iam',),
    'serverless': ('rds_api', 'pg_wire_iam', 'pg_wire_secret'),
}
SUPPORTED_ENDPOINT_TYPES = tuple(ENDPOINT_AUTH_CAPABILITY.keys())
# Endpoint types we recognise but haven't wired provisioning for yet. Requested
# explicitly, they produce a clear "not yet supported" error rather than an
# "unknown endpoint" one.
FUTURE_ENDPOINT_TYPES = ('rds-instance',)
ALL_AUTH_TYPES = ('pg_wire_iam', 'pg_wire_secret', 'rds_api')
AUTH_TYPE_TO_METHOD = {
    'pg_wire_iam': (ConnectionMethod.PG_WIRE_IAM_PROTOCOL, 'PG_WIRE_IAM_PROTOCOL'),
    'pg_wire_secret': (ConnectionMethod.PG_WIRE_PROTOCOL, 'PG_WIRE_PROTOCOL'),
    'rds_api': (ConnectionMethod.RDS_API, 'RDS_API'),
}


class CapturingCtx(DummyCtx):
    """Capture the ctx.error detail that run_query intentionally keeps out of returns.

    The RDS Data API path redacts its returned error, so assertions that need to
    know *why* a query failed have to read what was reported to the context.

    ``errors`` is declared as a field rather than assigned in ``__init__`` because
    ``Context`` is a Pydantic model: ``self.errors = []`` on an undeclared
    attribute raises ``ValueError: "CapturingCtx" object has no field "errors"``
    and took down the whole query-enforcement suite at construction time. Declared
    this way Pydantic deep-copies the default, so instances stay independent.

    Defined at module level, not nested inside the suite, so the unit tests can
    construct it -- the failure it caused was reproducible without any AWS
    resources and should never have needed a live cluster to surface.
    """

    errors: List[str] = []

    def __init__(self) -> None:
        """Construct with no request context, mirroring DummyCtx.

        Declared explicitly because adding a field to a Pydantic model makes type
        checkers synthesize an ``__init__`` requiring every inherited field as a
        keyword argument. This keeps the no-argument constructor the suite uses.
        """
        super().__init__()

    async def error(self, data: Any, *, logger_name: Optional[str] = None):
        """Record the error detail instead of discarding it."""
        self.errors.append(str(data))


# --- Detached cluster teardown ---------------------------------------------
# Deleting an Aurora cluster is slow and strictly ordered: every member instance
# must be gone before delete_db_cluster is accepted, so internal_delete_cluster
# polls for instance deletion and then for cluster deletion (up to ~20 minutes
# each). None of that tells us anything about the code under test, and by the time
# it runs every assertion has already been recorded.
#
# It cannot simply be un-awaited, though. An asyncio task abandoned at
# interpreter exit is cancelled, and firing only the instance deletions would
# leave the cluster behind forever. So the teardown is handed to a *detached
# child process* that outlives this one: the harness returns immediately and the
# child keeps polling until the cluster is gone.
#
# The tradeoff is honest rather than free -- if the child is killed (machine
# sleep, container teardown, SIGKILL to the process group) the cluster leaks, the
# same failure mode the pre-existing --keep-clusters path already warns about.
# --wait-for-cleanup restores the blocking behavior for contexts that need the
# resources provably gone before the process exits.

# Run in the child. Region and cluster id arrive as argv so nothing has to be
# quoted or escaped into the snippet.
_DETACHED_DELETE_SNIPPET = (
    'import sys; '
    'from awslabs.postgres_mcp_server.connection.cp_api_connection import '
    'internal_delete_cluster; '
    'internal_delete_cluster(sys.argv[1], sys.argv[2])'
)


def spawn_detached_cluster_deletion(
    region: str, cluster_id: str, log_dir: Optional[str] = None
) -> Optional[Tuple[int, str]]:
    """Start cluster teardown in a process that survives this one.

    Uses ``sys.executable`` so the child runs in the same interpreter and can
    import the package, and ``start_new_session=True`` so it lands in a new
    process group and is not taken down by a signal sent to ours. Output goes to a
    per-cluster file, because a detached child that fails silently is worse than a
    slow teardown.

    Credentials come from the inherited environment and the shared credentials
    file. A teardown outliving the credential lifetime fails in the child and is
    recorded in its log rather than surfacing here.

    Args:
        region: AWS region holding the cluster.
        cluster_id: Cluster to delete.
        log_dir: Directory for the child's log. Defaults to the working directory,
            where the wrapper script already writes the run log.

    Returns:
        Optional[Tuple[int, str]]: ``(pid, log_path)``, or None if the child could
        not be started -- never raises, since teardown must not fail a run whose
        assertions have already completed.
    """
    directory = log_dir or os.getcwd()
    stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    log_path = os.path.join(directory, f'e2e-cleanup-{cluster_id}-{stamp}.log')
    try:
        handle = open(log_path, 'w')  # noqa: SIM115 - owned by the child, closed below
    except OSError as e:
        logger.warning(f'Could not open teardown log {log_path}: {e}')
        return None

    try:
        process = subprocess.Popen(  # noqa: S603 - fixed argv, no shell
            [sys.executable, '-c', _DETACHED_DELETE_SNIPPET, region, cluster_id],
            stdout=handle,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
            cwd=directory,
        )
    except Exception as e:
        logger.warning(f'Could not start detached teardown for {cluster_id}: {e}')
        return None
    finally:
        # The child holds its own descriptor; ours would otherwise keep the file
        # open for the lifetime of this process.
        handle.close()

    return process.pid, log_path


# --- Response classification -----------------------------------------------
# Defined at module level so the unit tests can exercise them against the real
# error strings this suite has observed. They were previously closures inside
# run_query_enforcement_suite, which meant a mistake in one could only be found
# by provisioning a cluster -- and that is exactly how the write-mode backstop
# assertion shipped too strict.


def is_rejected(rows: Any) -> bool:
    """True when run_query returned an error rather than rows.

    ``run_query`` reports every refusal and every database failure the same way,
    as ``[{'error': ...}]``, so this says nothing about *why* -- the two
    classifiers below are what separate the causes.
    """
    return bool(rows) and isinstance(rows[0], dict) and 'error' in rows[0]


def is_readonly_policy_rejection(rows: Any) -> bool:
    """True when the *guard* refused the statement as a write in read-only mode.

    The parser-based guard's read-only messages all contain "not allowed in
    read-only mode". Dangerous-set rejections, parse failures, and database errors
    all use different wording, so this stays specific to the write-set decision.
    """
    if not is_rejected(rows):
        return False
    return 'read-only mode' in str(rows[0]['error'])


def is_database_readonly_rejection(rows: Any, ctx_errors: List[str]) -> bool:
    """True when *PostgreSQL* refused the statement for read-only reasons.

    Distinct from :func:`is_readonly_policy_rejection`: this matches the engine's
    own "cannot execute ... in a read-only transaction", which proves the
    statement passed the guard and was stopped by the ``SET TRANSACTION READ
    ONLY`` wrapper instead. Observed on Aurora PG 17.5 as
    ``ReadOnlySqlTransaction: cannot execute SELECT FOR UPDATE in a read-only
    transaction``.

    The RDS Data API redacts the returned error, so the detail reported to the
    context is searched as well.

    Args:
        rows: The value ``run_query`` returned.
        ctx_errors: Detail captured by :class:`CapturingCtx`.

    Returns:
        bool: True when the engine's read-only transaction is the cause.
    """
    if not is_rejected(rows):
        return False
    detail = f'{rows[0]["error"]} {ctx_errors!r}'.lower()
    return 'read-only transaction' in detail


def _split_csv(value: str) -> List[str]:
    """Split a comma-separated CLI value into a list of trimmed, lowercased tokens."""
    return [tok.strip().lower() for tok in value.split(',') if tok.strip()]


def _lp_secret_for_method(lp: Optional[dict], method: ConnectionMethod) -> Optional[str]:
    """Return the least-privilege secret ARN appropriate for a connection method.

    On RDS PostgreSQL a role granted ``rds_iam`` can no longer use password
    auth, so we provision two distinct least-privilege roles and pick the right
    one per method:

      * PG_WIRE_IAM_PROTOCOL -> the IAM role's secret (username only; password
        is an IAM token). Requires the role to have ``rds_iam``.
      * PG_WIRE_PROTOCOL / RDS_API -> the password role's secret (username +
        password). The role must NOT have ``rds_iam``.

    Returns None when no suitable secret was provisioned (caller falls back to
    the cluster master secret).
    """
    if not lp:
        return None
    if method == ConnectionMethod.PG_WIRE_IAM_PROTOCOL:
        return lp.get('secret_arn_iam')
    if method == ConnectionMethod.PG_WIRE_PROTOCOL:
        # Direct password login: must be the role WITHOUT rds_iam.
        return lp.get('secret_arn_pw')
    # RDS_API (Data API) authenticates via the secret and works with either
    # role, so prefer the password role but fall back to the IAM role's secret.
    return lp.get('secret_arn_pw') or lp.get('secret_arn_iam')


def resolve_run_plan(endpoint_types: List[str], auth_types: List[str]):
    """Validate requested endpoint/auth types against the capability matrix.

    Returns ``(endpoint_kinds, plan_by_kind, serverless_pgwire)`` where
    ``plan_by_kind`` maps each endpoint kind to an ordered list of
    ``(ConnectionMethod, method_name)`` cells to run.

    Raises ``ValueError`` (with an actionable message) on any invalid
    combination: an unknown or not-yet-supported endpoint, an unknown auth
    type, or a requested endpoint that supports none of the requested auth
    types. Callers surface this to the operator and abort.
    """
    if not endpoint_types:
        raise ValueError('no endpoint types requested (use --endpoint-types)')
    if not auth_types:
        raise ValueError('no auth types requested (use --auth-types)')

    future = [e for e in endpoint_types if e in FUTURE_ENDPOINT_TYPES]
    if future:
        raise ValueError(
            f'endpoint type(s) {future} are not yet supported by this harness '
            f'(Aurora endpoints only for now: {list(SUPPORTED_ENDPOINT_TYPES)}).'
        )
    unknown_eps = [e for e in endpoint_types if e not in ENDPOINT_AUTH_CAPABILITY]
    if unknown_eps:
        raise ValueError(
            f'unknown endpoint type(s) {unknown_eps}; valid: {list(SUPPORTED_ENDPOINT_TYPES)}'
        )
    unknown_auths = [a for a in auth_types if a not in AUTH_TYPE_TO_METHOD]
    if unknown_auths:
        raise ValueError(f'unknown auth type(s) {unknown_auths}; valid: {list(ALL_AUTH_TYPES)}')

    plan_by_kind: dict = {}
    for ep in endpoint_types:
        supported = ENDPOINT_AUTH_CAPABILITY[ep]
        selected = [a for a in auth_types if a in supported]
        if not selected:
            raise ValueError(
                f"invalid combination: endpoint '{ep}' supports auth type(s) "
                f'{list(supported)}, but none of the requested {auth_types} apply. '
                'Adjust --endpoint-types / --auth-types.'
            )
        plan_by_kind[ep] = [AUTH_TYPE_TO_METHOD[a] for a in selected]

    # De-dup endpoint kinds while preserving order.
    endpoint_kinds = list(dict.fromkeys(endpoint_types))
    serverless_pgwire = 'serverless' in plan_by_kind and any(
        method in _PGWIRE_METHODS for method, _ in plan_by_kind['serverless']
    )
    return endpoint_kinds, plan_by_kind, serverless_pgwire


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
    publicly_accessible: bool = False,
    vpc_security_group_ids: Optional[list] = None,
    enable_iam_auth: bool = False,
) -> str:
    """Create serverless cluster, poll until done. Returns db_endpoint.

    When ``publicly_accessible`` or ``vpc_security_group_ids`` is set,
    bypasses the MCP create_cluster tool and calls
    ``internal_create_serverless_cluster`` directly. The public-access
    flags must NEVER be reachable through the MCP tool surface (an LLM
    could otherwise expose a cluster to the internet via prompt
    injection), so the test owns this codepath.
    """
    log_step('create_cluster (serverless)', 'INFO', cluster_identifier)

    if publicly_accessible or vpc_security_group_ids:
        from awslabs.postgres_mcp_server.connection.cp_api_connection import (
            internal_create_serverless_cluster,
            internal_get_cluster_properties,
            setup_aurora_iam_policy_for_current_user,
        )

        # Direct call — does not go through the threaded MCP create_cluster
        # tool, so this returns synchronously when the cluster is fully ready.
        cluster_result = internal_create_serverless_cluster(
            region=region,
            cluster_identifier=cluster_identifier,
            engine_version=engine_version,
            database_name=database,
            publicly_accessible=publicly_accessible,
            vpc_security_group_ids=vpc_security_group_ids,
            enable_iam_auth=enable_iam_auth,
        )

        # Mirror what server.create_cluster_worker does for IAM-auth setup
        # so PG_WIRE_IAM_PROTOCOL works against the cluster.
        setup_aurora_iam_policy_for_current_user(
            db_user=cluster_result['MasterUsername'],
            cluster_resource_id=cluster_result['DbClusterResourceId'],
            cluster_region=region,
        )

        props = internal_get_cluster_properties(cluster_identifier, region)
        endpoint = props['Endpoint']
        log_step('create_cluster (serverless, public)', 'PASS', f'endpoint={endpoint}')
        wait_for_dns(endpoint)
        return endpoint

    # Default path — go through the public MCP tool. Production-like.
    result_json = create_cluster(
        region=region,
        cluster_identifier=cluster_identifier,
        database=database,
        engine_version=engine_version,
        with_express_configuration=False,
        enable_iam_auth=enable_iam_auth,
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


def configure_server_secret_for_cluster(cluster_identifier: str, region: str) -> str:
    """Pin the cluster's managed secret in server.configured_secret_arns.

    Under the per-target override map, this isn't strictly required —
    internal_create_connection falls back to the cluster's
    MasterUserSecret when no override is set. This helper still exists so
    individual test cases can deterministically pin the per-target entry
    (useful for the "configured ARN overrides cluster metadata" case and
    for security suites that need to know exactly which ARN is being used).

    For Aurora express clusters there is no MasterUserSecret; in that
    case we ensure no entry exists for this cluster in
    configured_secret_arns so the IAM-path MasterUsername fallback in
    internal_create_connection takes over.

    Returns the resolved ARN (empty string for IAM-only clusters).
    """
    from awslabs.postgres_mcp_server.connection.cp_api_connection import (
        internal_get_cluster_properties,
    )

    props = internal_get_cluster_properties(cluster_identifier, region)
    secret_arn = props.get('MasterUserSecret', {}).get('SecretArn', '') or ''
    if secret_arn:
        server.configured_secret_arns[cluster_identifier] = secret_arn
        log_step('configure_server_secret', 'PASS', secret_arn)
    else:
        server.configured_secret_arns.pop(cluster_identifier, None)
        log_step(
            'configure_server_secret',
            'INFO',
            f"cluster '{cluster_identifier}' has no MasterUserSecret; "
            'leaving configured_secret_arns entry unset (IAM-only auth path)',
        )
    return secret_arn


async def provision_least_privilege_access(
    cluster_identifier: str,
    region: str,
    valid_endpoint: str,
    port: int,
    connection_method: ConnectionMethod,
    database: str,
    need_iam_role: bool = False,
    need_pw_role: bool = True,
) -> dict:
    """Create non-superuser least-privilege role(s) + Secrets Manager secret(s).

    On RDS PostgreSQL, granting ``rds_iam`` to a role **disables password
    authentication** for that role (it becomes IAM-only). A single role
    therefore cannot serve both the PG_WIRE_IAM path (IAM token) and the
    PG_WIRE_PROTOCOL / RDS_API paths (password). So depending on which methods
    the run will exercise, this provisions up to two roles:

      * ``need_iam_role`` -> ``<base>_iam``: granted ``rds_iam`` + an
        ``rds-db:connect`` IAM policy. Used for PG_WIRE_IAM_PROTOCOL.
      * ``need_pw_role`` -> ``<base>_pw``: a password role WITHOUT ``rds_iam``.
        Used for PG_WIRE_PROTOCOL and RDS_API (Data API).

    The master user is **not** granted ``rds_iam`` (that would break the
    master-password paths); master-via-IAM is not used by any suite under this
    model. Both roles are non-superuser (so they pass the 'enforce' guardrail)
    and get ``USAGE`` + ``CREATE`` on schema ``public`` to run the functional
    suite.

    Runs the provisioning DDL as the cluster master user (so it must be called
    while ``server.privilege_check_policy == 'off'``). ``connection_method``
    selects how to connect as master (RDS_API for serverless, PG_WIRE_IAM for
    express). Requires ``secretsmanager:CreateSecret``/``DeleteSecret``. Raises
    on failure so the caller can record the affected suites.

    Returns ``{'cluster_id', 'endpoint', 'database', 'role_iam',
    'secret_arn_iam', 'role_pw', 'secret_arn_pw', 'iam_policy_created'}``
    (the ``*_iam`` / ``*_pw`` entries are None when that role wasn't created).
    """
    import boto3
    import json as _json
    import secrets as _secrets
    from awslabs.postgres_mcp_server.connection.cp_api_connection import (
        internal_get_cluster_properties,
        setup_aurora_iam_policy_for_current_user,
    )

    base = f'mcp_e2e_lp_{cluster_identifier.replace("-", "_")}'
    iam_role = f'{base}_iam'[:60]
    pw_role = f'{base}_pw'[:60]
    # Random per-run passwords; generated at runtime, never hardcoded. The IAM
    # role's password is a placeholder (rds_iam disables password auth for it),
    # kept only so the secret has the username/password shape callers expect.
    pw_password = 'Lp' + _secrets.token_hex(16)  # pragma: allowlist secret
    iam_placeholder_pw = 'Lp' + _secrets.token_hex(16)  # pragma: allowlist secret

    # 1. Connect as the master user (nothing pinned yet → metadata /
    #    MasterUsername fallback) in write mode to run the provisioning DDL.
    saved_readonly = server.readonly_query
    server.readonly_query = False
    server.db_connection_map.remove(
        connection_method, cluster_identifier, valid_endpoint, database, port
    )
    resp = str(
        await connect_to_database(
            region=region,
            database_type=DatabaseType.APG,
            connection_method=connection_method,
            cluster_identifier=cluster_identifier,
            db_endpoint=valid_endpoint,
            port=port,
            database=database,
        )
    )
    if 'Failed' in resp:
        server.readonly_query = saved_readonly
        raise RuntimeError(f'master connect for provisioning failed: {resp}')
    conn = server.db_connection_map.get(
        connection_method, cluster_identifier, valid_endpoint, database, port
    )
    if conn is None:
        server.readonly_query = saved_readonly
        raise RuntimeError('no master connection available for provisioning')

    iam_policy_created = False
    try:
        # 2. Create the role(s). Names are unique per run (cluster id), so they
        #    never pre-exist and need no pre-clean.
        if need_iam_role:
            await conn.execute_query(
                f"CREATE ROLE {iam_role} LOGIN PASSWORD '{iam_placeholder_pw}' "
                'NOSUPERUSER NOCREATEDB NOCREATEROLE'
            )
            await conn.execute_query(f'GRANT USAGE, CREATE ON SCHEMA public TO {iam_role}')
            try:
                await conn.execute_query(f'GRANT rds_iam TO {iam_role}')
            except Exception as e:
                logger.warning(f'GRANT rds_iam TO {iam_role} failed (non-fatal): {e}')
            # 3. IAM path: authorize rds-db:connect for the IAM role.
            props = internal_get_cluster_properties(cluster_identifier, region)
            setup_aurora_iam_policy_for_current_user(
                db_user=iam_role,
                cluster_resource_id=props['DbClusterResourceId'],
                cluster_region=region,
            )
            iam_policy_created = True
        if need_pw_role:
            await conn.execute_query(
                f"CREATE ROLE {pw_role} LOGIN PASSWORD '{pw_password}' "
                'NOSUPERUSER NOCREATEDB NOCREATEROLE'
            )
            await conn.execute_query(f'GRANT USAGE, CREATE ON SCHEMA public TO {pw_role}')
    finally:
        # Drop the master provisioning connection so suites reconnect as lp.
        server.db_connection_map.remove(
            connection_method, cluster_identifier, valid_endpoint, database, port
        )
        server.readonly_query = saved_readonly

    # 4. Store each role's credentials in a tagged secret. If a create fails
    # after we've already created the IAM policy / the other secret, those
    # would leak (deprovision is never called because we never return lp_info),
    # so on failure best-effort tear down what exists before re-raising.
    sm = boto3.client('secretsmanager', region_name=region)
    ts = datetime.now().strftime('%Y%m%d%H%M%S')
    secret_arn_iam: Optional[str] = None
    secret_arn_pw: Optional[str] = None
    try:
        if need_iam_role:
            secret_arn_iam = sm.create_secret(
                Name=f'mcp-e2e-lp-iam-{cluster_identifier}-{ts}',
                SecretString=_json.dumps({'username': iam_role, 'password': iam_placeholder_pw}),
                Tags=[{'Key': 'mcp-e2e', 'Value': 'true'}],
            )['ARN']
        if need_pw_role:
            secret_arn_pw = sm.create_secret(
                Name=f'mcp-e2e-lp-pw-{cluster_identifier}-{ts}',
                SecretString=_json.dumps({'username': pw_role, 'password': pw_password}),
                Tags=[{'Key': 'mcp-e2e', 'Value': 'true'}],
            )['ARN']
    except Exception:
        await deprovision_least_privilege_access(
            {
                'cluster_id': cluster_identifier,
                'role_iam': iam_role if need_iam_role else None,
                'secret_arn_iam': secret_arn_iam,
                'role_pw': pw_role if need_pw_role else None,
                'secret_arn_pw': secret_arn_pw,
                'iam_policy_created': iam_policy_created,
            },
            region,
        )
        raise
    logger.success(
        f'Provisioned least-privilege role(s) for {cluster_identifier} '
        f'(iam={need_iam_role}, pw={need_pw_role})'
    )
    return {
        'cluster_id': cluster_identifier,
        'endpoint': valid_endpoint,
        'database': database,
        'role_iam': iam_role if need_iam_role else None,
        'secret_arn_iam': secret_arn_iam,
        'role_pw': pw_role if need_pw_role else None,
        'secret_arn_pw': secret_arn_pw,
        'iam_policy_created': iam_policy_created,
    }


async def deprovision_least_privilege_access(lp_info: dict, region: str) -> None:
    """Best-effort teardown of provisioned least-privilege AWS artifacts.

    The cluster is deleted immediately after this runs, which removes the
    database role and every object it owns — so we do NOT attempt DROP ROLE
    here. (On Aurora the master is rds_superuser, not a true superuser, and
    cannot drop objects owned by another role, so DROP OWNED/DROP ROLE would
    fail anyway.) We only clean up the AWS-side artifacts that outlive the
    cluster: the Secrets Manager secret and, when an IAM policy was created
    for the role, the per-role IAM policy (``AuroraIAMAuth-<role>``) that
    setup_aurora_iam_policy_for_current_user created and attached to the
    caller — otherwise it leaks and accumulates against the principal.

    Deletes both role secrets (``secret_arn_iam`` / ``secret_arn_pw``, whichever
    were created) and, when ``iam_policy_created`` is set, the per-role IAM
    policy ``AuroraIAMAuth-<role_iam>`` (only the IAM role gets an IAM policy).
    """
    import boto3
    from awslabs.postgres_mcp_server import __user_agent__
    from botocore.config import Config

    # Unpin any least-privilege secret pinned for this cluster.
    server.configured_secret_arns.pop(lp_info['cluster_id'], None)

    # Delete both role secrets (whichever were created).
    for key in ('secret_arn_iam', 'secret_arn_pw'):
        arn = lp_info.get(key)
        if not arn:
            continue
        try:
            sm = boto3.client('secretsmanager', region_name=region)
            sm.delete_secret(SecretId=arn, ForceDeleteWithoutRecovery=True)
        except Exception as e:
            logger.warning(f'deprovision delete_secret ({key}) failed: {e}')

    # Detach + delete the per-role IAM policy (only the IAM role gets one).
    if lp_info.get('iam_policy_created') and lp_info.get('role_iam'):
        try:
            sts = boto3.client('sts', config=Config(user_agent_extra=__user_agent__))
            iam = boto3.client('iam', config=Config(user_agent_extra=__user_agent__))
            ident = sts.get_caller_identity()
            arn = ident['Arn']
            policy_arn = (
                f'arn:aws:iam::{ident["Account"]}:policy/AuroraIAMAuth-{lp_info["role_iam"]}'
            )
            if ':user/' in arn:
                iam.detach_user_policy(
                    UserName=arn.split(':user/')[-1].split('/')[-1], PolicyArn=policy_arn
                )
            elif ':assumed-role/' in arn:
                iam.detach_role_policy(
                    RoleName=arn.split(':assumed-role/')[-1].split('/')[0], PolicyArn=policy_arn
                )
            for v in iam.list_policy_versions(PolicyArn=policy_arn)['Versions']:
                if not v['IsDefaultVersion']:
                    iam.delete_policy_version(PolicyArn=policy_arn, VersionId=v['VersionId'])
            iam.delete_policy(PolicyArn=policy_arn)
            logger.info(f'Deleted least-privilege IAM policy AuroraIAMAuth-{lp_info["role_iam"]}')
        except Exception as e:
            logger.warning(f'deprovision IAM policy cleanup failed: {e}')


def create_cluster_as_test(
    cluster_kind: str,
    creator_fn,
) -> tuple[Optional[str], 'TestResult']:
    """Run a cluster-creation function and record the result as a test case.

    Cluster creation is itself part of the MCP server's surface area —
    failures should fail the e2e run, and downstream functional tests
    against that cluster should be skipped (recorded, not silently dropped).

    Args:
        cluster_kind: Either 'express' or 'serverless'. Used for log labels
            and as the TestResult's connection_method_name.
        creator_fn: Zero-arg callable that creates the cluster and returns
            its endpoint. Typically a functools.partial wrapping
            create_express_cluster or create_serverless_cluster_and_wait.

    Returns:
        (endpoint_or_None, TestResult). endpoint is None if creation failed;
        TestResult.success reflects the same outcome.
    """
    logger.info(f'\n{"=" * 60}')
    logger.info(f'Creating {cluster_kind} cluster (recorded as a test case)')
    logger.info(f'{"=" * 60}')

    # cluster_identifier is attached for the summary; creator_fn closes over
    # whatever its actual value is. We derive it from the returned endpoint
    # at log time only; if creation fails, use '<not-created>' as the label.
    result = TestResult(
        cluster_identifier=f'<{cluster_kind}-pending>',
        connection_method_name=f'create_cluster_{cluster_kind}',
        passed=[],
        failed=[],
    )

    step = f'create_cluster_{cluster_kind}'
    try:
        endpoint = creator_fn()
        log_step(step, 'PASS', f'endpoint={endpoint}')
        result.passed.append(step)
        return endpoint, result
    except Exception as e:
        msg = f'{type(e).__name__}: {e}'
        log_step(step, 'FAIL', msg)
        result.failed.append((step, msg))
        return None, result


def skipped_result(
    cluster_identifier: str,
    connection_method_name: str,
    reason: str,
) -> 'TestResult':
    """Return a TestResult pre-populated with a single 'skipped' entry.

    Used when a planned test couldn't run because of an upstream failure
    (cluster creation broken, MCP server unstartable, etc.). The skipped
    entry surfaces in the summary and counts as not-pass for the exit code.
    """
    step_id = f'skipped_{connection_method_name}'
    r = TestResult(
        cluster_identifier=cluster_identifier,
        connection_method_name=connection_method_name,
        passed=[],
        failed=[],
        skipped=[(step_id, reason)],
    )
    log_step(
        f'{connection_method_name} ({cluster_identifier})',
        'SKIP',
        reason,
    )
    return r


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


def get_default_vpc_id(region: str) -> Optional[str]:
    """Return the default VPC ID in the region, or None if there isn't one.

    Some accounts have the default VPC removed by the account owner. In
    that case we can't auto-create the test SG and the caller should
    skip --test-non-express-cluster with a clear message rather than
    fail mid-run with a less obvious error.
    """
    import boto3

    ec2 = boto3.client('ec2', region_name=region)
    try:
        resp = ec2.describe_vpcs(Filters=[{'Name': 'is-default', 'Values': ['true']}])
    except Exception as e:
        logger.warning(f'describe_vpcs failed in {region}: {e}')
        return None
    vpcs = resp.get('Vpcs', [])
    if not vpcs:
        return None
    return vpcs[0]['VpcId']


def gc_e2e_test_security_groups(
    region: str,
    name_prefix: str = 'mcp-e2e-pgwire-',
    max_age_seconds: int = 3600,
) -> None:
    """Delete leftover test SGs from earlier crashed runs.

    Each test run creates a uniquely-named SG. A clean teardown removes
    it. A SIGKILL'd or otherwise crashed run leaks one. This pass walks
    SGs in the region whose name starts with the test prefix and whose
    tag mcp-e2e=true is set, and tries to delete any older than
    max_age_seconds. Errors (DependencyViolation while a recently-deleted
    cluster's ENI lingers) are logged but non-fatal.
    """
    import boto3

    ec2 = boto3.client('ec2', region_name=region)
    try:
        resp = ec2.describe_security_groups(
            Filters=[
                {'Name': 'tag:mcp-e2e', 'Values': ['true']},
                {'Name': 'group-name', 'Values': [f'{name_prefix}*']},
            ]
        )
    except Exception as e:
        logger.warning(f'gc_e2e_test_security_groups: describe_security_groups failed: {e}')
        return

    candidates = resp.get('SecurityGroups', [])
    if not candidates:
        return

    now = datetime.now()
    deleted = 0
    skipped = 0
    for sg in candidates:
        # Use the run timestamp encoded in the name (mcp-e2e-pgwire-<ts>)
        # rather than the SG's CreateDate (which describe_security_groups
        # doesn't reliably return). The ts format is YYYYMMDDHHMMSS.
        sg_id = sg['GroupId']
        name = sg.get('GroupName', '')
        ts_str = name[len(name_prefix) :]
        try:
            sg_created = datetime.strptime(ts_str, '%Y%m%d%H%M%S')
            age_s = (now - sg_created).total_seconds()
        except ValueError:
            # Name doesn't match expected format — be conservative,
            # don't delete.
            skipped += 1
            continue

        if age_s < max_age_seconds:
            skipped += 1
            continue

        try:
            ec2.delete_security_group(GroupId=sg_id)
            deleted += 1
            logger.info(
                f'gc_e2e_test_security_groups: deleted leftover {name} ({sg_id}, age {age_s:.0f}s)'
            )
        except Exception as e:
            # Common: DependencyViolation if the cluster ENI hasn't been
            # released yet. Leave it for the next GC pass.
            logger.warning(f'gc_e2e_test_security_groups: could not delete {name} ({sg_id}): {e}')

    if deleted or skipped:
        logger.info(f'gc_e2e_test_security_groups: deleted {deleted}, skipped {skipped}')


def create_e2e_test_security_group(
    region: str,
    vpc_id: str,
    prefix_list_ids: List[str],
    sg_name: str,
) -> str:
    """Create a dedicated SG for the e2e test and authorize tcp:5432 from prefix lists.

    Pinning ingress to managed prefix lists (rather than to the test
    runner's egress IP) avoids NAT-rotation flakes on long-running tests
    and keeps the SG stable across runs from different developer
    machines that share the same prefix list. Caller provides
    ``prefix_list_ids`` — typically Amazon's well-known managed corp
    prefix lists for office/VPN egress.

    Returns the SG id. Caller is responsible for delete_e2e_test_security_group
    on cleanup. The SG is tagged ``mcp-e2e=true`` so the GC pass can find
    orphans even if the test process crashes.
    """
    import boto3

    ec2 = boto3.client('ec2', region_name=region)

    resp = ec2.create_security_group(
        GroupName=sg_name,
        Description=f'e2e test SG for {sg_name} (auto-deleted)',
        VpcId=vpc_id,
        TagSpecifications=[
            {
                'ResourceType': 'security-group',
                'Tags': [
                    {'Key': 'mcp-e2e', 'Value': 'true'},
                    {'Key': 'Name', 'Value': sg_name},
                ],
            }
        ],
    )
    sg_id = resp['GroupId']

    try:
        ec2.authorize_security_group_ingress(
            GroupId=sg_id,
            IpPermissions=[
                {
                    'IpProtocol': 'tcp',
                    'FromPort': 5432,
                    'ToPort': 5432,
                    'PrefixListIds': [
                        {
                            'PrefixListId': pl_id,
                            'Description': f'e2e test access from prefix list {pl_id}',
                        }
                        for pl_id in prefix_list_ids
                    ],
                }
            ],
        )
    except Exception:
        # If we can't authorize the rule, the SG is useless — clean up.
        try:
            ec2.delete_security_group(GroupId=sg_id)
        except Exception as cleanup_err:
            logger.warning(
                f'best-effort cleanup failed: could not delete test SG {sg_id}: {cleanup_err}'
            )
        raise

    # Also authorize THIS host's public egress IP as a /32. The managed prefix
    # lists cover corp/VPN egress, but a Cloud Dev / dev-desktop host often
    # egresses from an IP outside them, so its packets to the publicly-
    # accessible cluster get silently dropped by the SG (TCP timeout). Adding
    # the detected egress /32 makes the cluster reachable from wherever the e2e
    # runs. Best-effort: if detection fails we keep the prefix-list rule.
    egress_ip = _detect_public_egress_ip()
    if egress_ip:
        try:
            ec2.authorize_security_group_ingress(
                GroupId=sg_id,
                IpPermissions=[
                    {
                        'IpProtocol': 'tcp',
                        'FromPort': 5432,
                        'ToPort': 5432,
                        'IpRanges': [
                            {
                                'CidrIp': f'{egress_ip}/32',
                                'Description': 'e2e test host public egress',
                            }
                        ],
                    }
                ],
            )
        except Exception as e:
            logger.warning(f'could not authorize host egress {egress_ip}/32 on test SG: {e}')

    logger.info(
        f'created test SG {sg_name} ({sg_id}) authorizing {", ".join(prefix_list_ids)}'
        f'{f" + {egress_ip}/32" if egress_ip else ""} on tcp:5432'
    )
    return sg_id


def _detect_public_egress_ip() -> Optional[str]:
    """Return this host's public egress IP (for SG ingress), or None.

    Best-effort HTTPS GET to a constant AWS IP-echo endpoint. Never raises —
    on any failure the caller falls back to the managed prefix lists alone.
    """
    import ipaddress
    import urllib.request

    try:
        with urllib.request.urlopen(  # nosec B310  # nosemgrep: python.lang.security.audit.dynamic-urllib-use-detected.dynamic-urllib-use-detected
            'https://checkip.amazonaws.com', timeout=10
        ) as resp:
            ip = resp.read().decode().strip()
        ipaddress.ip_address(ip)  # validate; raises if not a plain IP
        return ip
    except Exception as e:
        logger.warning(
            f'could not detect public egress IP (test SG will rely on prefix lists only): {e}'
        )
        return None


def delete_e2e_test_security_group(region: str, sg_id: str) -> None:
    """Best-effort delete of an e2e test SG.

    Failures (e.g. DependencyViolation while ENI is still attached) are
    logged. The startup GC pass will retry on the next run.
    """
    import boto3

    ec2 = boto3.client('ec2', region_name=region)
    try:
        ec2.delete_security_group(GroupId=sg_id)
        logger.info(f'deleted test SG {sg_id}')
    except Exception as e:
        logger.warning(
            f'could not delete SG {sg_id} ({e}); will be reaped by next run gc_e2e_test_security_groups'
        )


def gc_aurora_iam_policy(region: str, policy_name: str = 'AuroraIAMAuth-postgres'):
    """Wipe all dbuser entries from the IAM policy used for Aurora IAM auth.

    setup_aurora_iam_policy_for_current_user appends a
    ``dbuser:<cluster-resource-id>/<user>`` ARN every time a new cluster
    is created, but never removes entries when the cluster is deleted.
    Over many e2e runs the policy hits IAM's 6,144-char managed-policy
    size cap, after which CreatePolicyVersion fails with LimitExceeded.

    Strategy: clear the slate at the start of every run. We rewrite the
    policy with a single sentinel rds-db ARN so the policy document
    stays well-formed; the cluster-creation path then re-populates it
    with entries for whichever clusters this run actually creates.

    Errors are logged and swallowed so a CI principal without
    iam:CreatePolicyVersion isn't fatal — the existing policy stays
    intact and the run still has a chance of succeeding while the
    operator restores permissions.
    """
    import boto3

    iam = boto3.client('iam')
    sts = boto3.client('sts')
    try:
        account_id = sts.get_caller_identity()['Account']
    except Exception as e:
        logger.warning(f'gc_aurora_iam_policy: could not resolve account id: {e}')
        return

    policy_arn = f'arn:aws:iam::{account_id}:policy/{policy_name}'

    try:
        existing = iam.get_policy(PolicyArn=policy_arn)
    except iam.exceptions.NoSuchEntityException:
        logger.info(f'gc_aurora_iam_policy: policy {policy_name} does not exist; nothing to GC')
        return
    except Exception as e:
        logger.warning(f'gc_aurora_iam_policy: get_policy failed: {e}')
        return

    try:
        version = iam.get_policy_version(
            PolicyArn=policy_arn, VersionId=existing['Policy']['DefaultVersionId']
        )
    except Exception as e:
        logger.warning(f'gc_aurora_iam_policy: get_policy_version failed: {e}')
        return

    doc = version['PolicyVersion']['Document']
    statements = doc.get('Statement', [])
    existing_resources = []
    if statements:
        r = statements[0].get('Resource', [])
        existing_resources = [r] if isinstance(r, str) else list(r)

    # A non-empty placeholder Resource keeps the policy syntactically
    # valid even when no clusters exist. setup_aurora_iam_policy_for_current_user
    # will append the real cluster ARN alongside this sentinel; the
    # sentinel is harmless because no cluster has resource id 'placeholder'.
    sentinel = f'arn:aws:rds-db:{region}:{account_id}:dbuser:cluster-placeholder/none'

    if len(existing_resources) == 1 and existing_resources[0] == sentinel:
        logger.info(
            f'gc_aurora_iam_policy: {policy_name} already cleared (only sentinel present); '
            'nothing to do'
        )
        return

    logger.info(
        f'gc_aurora_iam_policy: clearing {len(existing_resources)} entries from {policy_name} '
        '(cluster creation will repopulate)'
    )

    new_doc = {
        'Version': doc.get('Version', '2012-10-17'),
        'Statement': [{'Effect': 'Allow', 'Action': 'rds-db:connect', 'Resource': [sentinel]}],
    }

    # Free up a slot if we're at the 5-version cap.
    try:
        versions = iam.list_policy_versions(PolicyArn=policy_arn).get('Versions', [])
        if len(versions) >= 5:
            non_default = [v for v in versions if not v['IsDefaultVersion']]
            if non_default:
                oldest = sorted(non_default, key=lambda v: v['CreateDate'])[0]
                logger.info(
                    f'gc_aurora_iam_policy: deleting oldest version {oldest["VersionId"]} '
                    f'to make room (created {oldest["CreateDate"]})'
                )
                iam.delete_policy_version(PolicyArn=policy_arn, VersionId=oldest['VersionId'])
    except Exception as e:
        logger.warning(f'gc_aurora_iam_policy: version-cap maintenance failed: {e}')

    try:
        iam.create_policy_version(
            PolicyArn=policy_arn,
            PolicyDocument=json.dumps(new_doc),
            SetAsDefault=True,
        )
        logger.success(f'gc_aurora_iam_policy: cleared {policy_name}')
    except Exception as e:
        logger.warning(f'gc_aurora_iam_policy: create_policy_version failed: {e}')


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
            # Connect failed. On the PG-Wire path this is often an SSL or auth
            # error; capture the server certificate + validation posture to
            # make the log self-sufficient for troubleshooting.
            if _is_pgwire_method(config.connection_method):
                log_tls_diagnostics(
                    config.db_endpoint,
                    config.port,
                    server.configured_ca_bundle or _bundled_ca_file(),
                    server.configured_sslmode,
                    label=f'{cluster_display} connect failed',
                )
            logger.error(f'Cannot continue suite without connection. Aborting {cluster_display}.')
            return result
    except Exception as e:
        record(step, False, str(e))
        if _is_pgwire_method(config.connection_method):
            log_tls_diagnostics(
                config.db_endpoint,
                config.port,
                server.configured_ca_bundle or _bundled_ca_file(),
                server.configured_sslmode,
                label=f'{cluster_display} connect exception',
            )
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

    # 9. run_query with a dangerous-set command: rejected regardless of mode.
    # This cell runs write-enabled (the CREATE/INSERT above succeeded), so DROP
    # is intentionally allowed here -- the parser-based guard blocks writes only
    # in read-only mode. Dangerous constructs (RCE/SSRF/filesystem), however, are
    # blocked in BOTH modes, so we assert one is rejected on the functional path.
    step = 'run_query(COPY ... TO PROGRAM) - expect rejection (dangerous, both modes)'
    try:
        rows = await run_query(
            sql="COPY (SELECT 1) TO PROGRAM 'id'",
            ctx=ctx,
            connection_method=config.connection_method,
            cluster_identifier=config.cluster_identifier,
            db_endpoint=config.db_endpoint,
            database=test_database,
        )
        # Expect error: COPY ... TO PROGRAM is command execution, always blocked.
        ok = rows and 'error' in rows[0]
        record(
            step,
            ok,
            'Correctly rejected COPY ... TO PROGRAM'
            if ok
            else 'COPY ... TO PROGRAM should have been rejected',
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


def run_endpoint_validation_suite(
    cluster_identifier: str,
    region: str,
    database: str,
    valid_endpoint: str,
    port: int,
    cluster_kind: str,
) -> TestResult:
    """Test the endpoint-validation security check in internal_create_connection.

    The connection method used for the positive case is picked to match the
    cluster: serverless uses RDS_API (always available), express uses
    PG_WIRE_IAM_PROTOCOL (the only method express supports). The negative
    cases trigger validation before any auth work, so they're method-agnostic
    in principle; we still pick a compatible method per cluster_kind for
    consistency.

    Positive case: caller-supplied db_endpoint matches the cluster's writer
    endpoint → connection succeeds, resolved endpoint in the response matches
    what AWS reports for the cluster.

    Negative case: caller-supplied db_endpoint is an arbitrary host that is
    not owned by the cluster → internal_create_connection must raise
    ValueError and no connection is created.

    The DB connection created here is cached in server.db_connection_map and
    reused by the main test suite that follows, so these checks don't add
    extra cluster warm-up cost.
    """
    # Pick a connection method compatible with the cluster. Express only
    # supports IAM auth; serverless supports all three but RDS_API is the
    # cheapest because it doesn't open a Postgres pool.
    method = (
        ConnectionMethod.PG_WIRE_IAM_PROTOCOL
        if cluster_kind == 'express'
        else ConnectionMethod.RDS_API
    )

    result = TestResult(
        cluster_identifier=cluster_identifier,
        connection_method_name='endpoint_validation',
        passed=[],
        failed=[],
    )

    logger.info(f'\n{"=" * 60}')
    logger.info(
        f'Running endpoint validation suite on {cluster_kind} cluster: {cluster_identifier}'
    )
    logger.info(f'{"=" * 60}')

    def record(step, ok, detail=''):
        """Record a test step result as passed or failed."""
        log_step(step, 'PASS' if ok else 'FAIL', detail)
        if ok:
            result.passed.append(step)
        else:
            result.failed.append((step, detail))

    # Positive case — db_endpoint matches the cluster's writer endpoint.
    step = 'endpoint_validation_positive(writer endpoint accepted)'
    try:
        db_conn, llm_response = internal_create_connection(
            region=region,
            database_type=DatabaseType.APG,
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
        internal_create_connection(
            region=region,
            database_type=DatabaseType.APG,
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
        internal_create_connection(
            region=region,
            database_type=DatabaseType.APG,
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

    return result


async def run_secret_arn_validation_suite(
    cluster_identifier: str,
    region: str,
    database: str,
    valid_endpoint: str,
    port: int,
    cluster_kind: str,
    test_non_express_cluster: bool,
    lp_iam_secret_arn: Optional[str] = None,
) -> TestResult:
    """Test Secrets-Manager-ARN resolution against a real Aurora cluster.

    Resolution priority is: configured_secret_arns[target] > configured_default_secret_arn > cluster MasterUserSecret.
    These cases cover both halves of the priority chain.

    Cases are gated by cluster_kind because express clusters only support
    PG_WIRE_IAM_PROTOCOL. RDS_API and PG_WIRE_PROTOCOL cases are skipped
    (recorded, not silently dropped) on express.

    Cases that open a real Postgres connection pool against a serverless
    cluster (PG Wire methods) are additionally gated by
    ``test_non_express_cluster``, mirroring how Phase 2's PG Wire cells
    are gated. The serverless cluster lives in a VPC; if the test host
    can't reach it on TCP 5432, those cases would time out at pool
    initialization.

      1. secret_arn_missing_falls_back_to_cluster_metadata: empty
         configured_secret_arns → resolution falls back to the cluster's
         MasterUserSecret. SELECT 1 succeeds because RDS auto-generates
         that secret at cluster creation time. (all cluster kinds; on
         serverless requires test_non_express_cluster because the
         success path uses PG_WIRE_PROTOCOL... actually no — it uses
         RDS_API on serverless and PG_WIRE_IAM on express, both of which
         are unaffected by VPC reachability. So this case stays
         unconditional.)
      2. secret_arn_rds_api_succeeds: configured ARN drives RDS Data API
         authentication end-to-end. (serverless only; RDS_API is public
         HTTPS so no VPC gate needed)
      3. secret_arn_pg_wire_succeeds: configured ARN drives psycopg
         credential retrieval end-to-end. (serverless only AND
         test_non_express_cluster — opens a real Postgres pool)
      4. secret_arn_pg_wire_iam_succeeds: IAM path — username comes from
         the configured secret, password comes from a generated IAM
         token. On express this is always run (express is publicly
         reachable). On serverless requires test_non_express_cluster.
      5. bogus_secret_arn: a non-existent ARN either fails at first query
         (serverless, via PG_WIRE_PROTOCOL) or at connect time (express,
         via PG_WIRE_IAM_PROTOCOL — the IAM path calls Secrets Manager
         synchronously inside internal_create_connection to read the
         username). Same invariant, different stack layer. Proves the
         configured override is actually used (not silently ignored).
         On serverless requires test_non_express_cluster.
      6. configured_arn_overrides_cluster_metadata: when configured ARN
         is set, internal_create_connection uses it even if the cluster
         advertises a different MasterUserSecret. (serverless only —
         needs RDS_API; unaffected by VPC reachability)

    Each case saves/restores server.configured_secret_arns and clears any
    cached connection entry so subsequent tests don't short-circuit on
    db_connection_map.
    """
    from unittest.mock import patch

    result = TestResult(
        cluster_identifier=cluster_identifier,
        connection_method_name='secret_arn_validation',
        passed=[],
        failed=[],
    )

    logger.info(f'\n{"=" * 60}')
    logger.info(
        f'Running secret-ARN validation suite on {cluster_kind} cluster: {cluster_identifier}'
    )
    logger.info(f'{"=" * 60}')

    def record(step, ok, detail=''):
        log_step(step, 'PASS' if ok else 'FAIL', detail)
        if ok:
            result.passed.append(step)
        else:
            result.failed.append((step, detail))

    # Resolve the real managed secret ARN for the cluster. Most positive
    # cases use this directly; the "cluster-property ignored" case uses
    # it to prove that even swapping in a bogus cluster-reported ARN
    # can't affect the connection as long as configured_secret_arns is
    # the real one.
    #
    # Express clusters have no MasterUserSecret by design (IAM-only auth).
    # That's not a setup failure — the suite simply skips cases that
    # depend on a managed secret and records them as informational skips.
    from awslabs.postgres_mcp_server.connection.cp_api_connection import (
        internal_get_cluster_properties,
    )

    cluster_props = internal_get_cluster_properties(cluster_identifier, region)
    real_secret_arn = cluster_props.get('MasterUserSecret', {}).get('SecretArn', '') or ''
    has_managed_secret = bool(real_secret_arn)
    if has_managed_secret:
        record('resolve_real_secret_arn', True, real_secret_arn)
    else:
        record(
            'resolve_real_secret_arn',
            True,
            f'cluster {cluster_identifier} has no MasterUserSecret '
            '(expected for IAM-only express clusters)',
        )

    saved_secret_arns = dict(server.configured_secret_arns)
    saved_default_secret_arn = server.configured_default_secret_arn

    # Express clusters auto-create only the 'postgres' database. The
    # caller's --database value (mcp_test_db) is created on serverless
    # at create_cluster time, but isn't created on express. PG Wire
    # connections that target a missing database fail the pool with
    # "FATAL: database <name> does not exist", which then loops in
    # psycopg_pool retry until PoolTimeout. Resolve to 'postgres' on
    # express to match how the functional Phase 2 suite handles the
    # same constraint.
    pg_wire_database = 'postgres' if cluster_kind == 'express' else database

    def reset_to_real_secret():
        # Pin the real cluster-managed secret on the per-cluster entry.
        # For IAM-only clusters (express) we clear the entry so the
        # MasterUsername fallback in internal_create_connection kicks in.
        if real_secret_arn:
            server.configured_secret_arns[cluster_identifier] = real_secret_arn
        else:
            server.configured_secret_arns.pop(cluster_identifier, None)

    def clear_cached_connection(method: ConnectionMethod, db: Optional[str] = None):
        """Remove any cached connection for this test's target.

        The next internal_create_connection call must not short-circuit on
        db_connection_map, otherwise the security invariants we're asserting
        won't actually be exercised.
        """
        server.db_connection_map.remove(
            method, cluster_identifier, valid_endpoint, db or database, port
        )

    ctx = DummyCtx()

    try:
        # ------------------------------------------------------------------
        # ------------------------------------------------------------------
        # Case 1: Missing configured_secret_arns falls back to cluster
        # metadata. Skipped on express + RDS_API combinations elsewhere;
        # uses PG_WIRE_IAM_PROTOCOL on express, RDS_API on serverless.
        # ------------------------------------------------------------------
        step = 'secret_arn_missing_falls_back_to_cluster_metadata'
        try:
            server.configured_secret_arns.pop(cluster_identifier, None)
            server.configured_default_secret_arn = None
            method = (
                ConnectionMethod.PG_WIRE_IAM_PROTOCOL
                if cluster_kind == 'express'
                else ConnectionMethod.RDS_API
            )
            # PG Wire methods on express must target the 'postgres' database
            # since express clusters don't auto-create the user-supplied DB.
            # RDS_API on serverless uses the user-supplied database.
            db_for_method = pg_wire_database if cluster_kind == 'express' else database
            clear_cached_connection(method, db_for_method)
            internal_create_connection(
                region=region,
                database_type=DatabaseType.APG,
                connection_method=method,
                cluster_identifier=cluster_identifier,
                db_endpoint=valid_endpoint,
                port=port,
                database=db_for_method,
            )
            rows = await run_query(
                sql='SELECT 1',
                ctx=ctx,
                connection_method=method,
                cluster_identifier=cluster_identifier,
                db_endpoint=valid_endpoint,
                database=db_for_method,
            )
            ok = bool(rows) and 'error' not in rows[0]
            record(step, ok, str(rows[0]) if rows else 'no rows')
        except Exception as e:
            record(step, False, f'{type(e).__name__}: {e}')
        finally:
            reset_to_real_secret()
            clear_cached_connection(
                ConnectionMethod.PG_WIRE_IAM_PROTOCOL
                if cluster_kind == 'express'
                else ConnectionMethod.RDS_API,
                pg_wire_database if cluster_kind == 'express' else database,
            )

        # ------------------------------------------------------------------
        # Case 2: Configured ARN drives RDS_API authentication
        # (serverless only — express doesn't support Data API)
        # ------------------------------------------------------------------
        step = 'secret_arn_rds_api_succeeds'
        if cluster_kind == 'express':
            record_not_applicable(result, step, 'RDS_API not supported on express cluster')
        else:
            try:
                reset_to_real_secret()
                clear_cached_connection(ConnectionMethod.RDS_API)
                internal_create_connection(
                    region=region,
                    database_type=DatabaseType.APG,
                    connection_method=ConnectionMethod.RDS_API,
                    cluster_identifier=cluster_identifier,
                    db_endpoint=valid_endpoint,
                    port=port,
                    database=database,
                )
                rows = await run_query(
                    sql='SELECT 1',
                    ctx=ctx,
                    connection_method=ConnectionMethod.RDS_API,
                    cluster_identifier=cluster_identifier,
                    db_endpoint=valid_endpoint,
                    database=database,
                )
                ok = bool(rows) and 'error' not in rows[0]
                record(step, ok, str(rows[0]) if rows else 'no rows')
            except Exception as e:
                record(step, False, f'{type(e).__name__}: {e}')

        # ------------------------------------------------------------------
        # Case 3: Configured ARN drives PG_WIRE_PROTOCOL authentication
        # (serverless only — express doesn't support this method —
        # AND requires --test-non-express-cluster because the serverless
        # cluster lives in a VPC and PG_WIRE_PROTOCOL opens a real
        # Postgres pool on TCP 5432).
        # ------------------------------------------------------------------
        step = 'secret_arn_pg_wire_succeeds'
        if cluster_kind == 'express':
            record_not_applicable(
                result, step, 'PG_WIRE_PROTOCOL not supported on express cluster'
            )
        elif not test_non_express_cluster:
            record_not_applicable(
                result,
                step,
                '--test-non-express-cluster not set (PG_WIRE_PROTOCOL '
                'on serverless requires VPC reachability)',
            )
        else:
            try:
                reset_to_real_secret()
                clear_cached_connection(ConnectionMethod.PG_WIRE_PROTOCOL)
                internal_create_connection(
                    region=region,
                    database_type=DatabaseType.APG,
                    connection_method=ConnectionMethod.PG_WIRE_PROTOCOL,
                    cluster_identifier=cluster_identifier,
                    db_endpoint=valid_endpoint,
                    port=port,
                    database=database,
                )
                rows = await run_query(
                    sql='SELECT 1',
                    ctx=ctx,
                    connection_method=ConnectionMethod.PG_WIRE_PROTOCOL,
                    cluster_identifier=cluster_identifier,
                    db_endpoint=valid_endpoint,
                    database=database,
                )
                ok = bool(rows) and 'error' not in rows[0]
                record(step, ok, str(rows[0]) if rows else 'no rows')
            except Exception as e:
                record(step, False, f'{type(e).__name__}: {e}')

        # ------------------------------------------------------------------
        # Case 4: IAM path pulls username from secret, password from token.
        # On express this always runs (express is publicly reachable). On
        # serverless requires --test-non-express-cluster for VPC reachability.
        # ------------------------------------------------------------------
        step = 'secret_arn_pg_wire_iam_succeeds'
        if cluster_kind == 'serverless' and not test_non_express_cluster:
            record_not_applicable(
                result,
                step,
                '--test-non-express-cluster not set (PG_WIRE_IAM_PROTOCOL '
                'on serverless requires VPC reachability)',
            )
        elif cluster_kind == 'serverless' and not lp_iam_secret_arn:
            record_not_applicable(
                result,
                step,
                'no IAM least-privilege role provisioned (the serverless '
                'master is not granted rds_iam under the two-role model, so the IAM '
                'username must come from the lp IAM role secret)',
            )
        else:
            try:
                # On express the master is IAM-capable (express enables IAM auth
                # for it), so use the master secret / MasterUsername fallback. On
                # serverless the master is NOT granted rds_iam, so drive the IAM
                # path from the IAM least-privilege role's secret instead.
                if cluster_kind == 'express':
                    reset_to_real_secret()
                else:
                    server.configured_secret_arns[cluster_identifier] = lp_iam_secret_arn  # type: ignore[assignment]
                clear_cached_connection(ConnectionMethod.PG_WIRE_IAM_PROTOCOL, pg_wire_database)
                internal_create_connection(
                    region=region,
                    database_type=DatabaseType.APG,
                    connection_method=ConnectionMethod.PG_WIRE_IAM_PROTOCOL,
                    cluster_identifier=cluster_identifier,
                    db_endpoint=valid_endpoint,
                    port=port,
                    database=pg_wire_database,
                )
                rows = await run_query(
                    sql='SELECT 1',
                    ctx=ctx,
                    connection_method=ConnectionMethod.PG_WIRE_IAM_PROTOCOL,
                    cluster_identifier=cluster_identifier,
                    db_endpoint=valid_endpoint,
                    database=pg_wire_database,
                )
                ok = bool(rows) and 'error' not in rows[0]
                record(step, ok, str(rows[0]) if rows else 'no rows')
            except Exception as e:
                record(step, False, f'{type(e).__name__}: {e}')

        # ------------------------------------------------------------------
        # Case 5: Bogus ARN must be rejected.
        # On serverless (PG_WIRE_PROTOCOL path): internal_create_connection
        # doesn't contact Secrets Manager, so connect succeeds; the error
        # surfaces at first query when initialize_pool fetches credentials.
        # On express (PG_WIRE_IAM_PROTOCOL path): internal_create_connection
        # does call get_credentials_from_secret to read the username, so
        # it fails at connect time with a ValueError. Same invariant,
        # different stack layer.
        # ------------------------------------------------------------------
        step = 'bogus_secret_arn_rejected'
        if cluster_kind == 'serverless' and not test_non_express_cluster:
            record_not_applicable(
                result,
                step,
                '--test-non-express-cluster not set (serverless variant '
                'opens PG_WIRE_PROTOCOL pool and requires VPC reachability)',
            )
        else:
            try:
                # Construct a syntactically-valid but non-existent ARN. We use
                # account 000000000000 so the test doesn't depend on the
                # caller's account ID and can't accidentally collide with a
                # real secret.
                bogus_arn = (
                    f'arn:aws:secretsmanager:{region}:000000000000:secret:'
                    f'mcp-e2e-does-not-exist-{int(time.time())}'
                )
                server.configured_secret_arns[cluster_identifier] = bogus_arn

                if cluster_kind == 'express':
                    clear_cached_connection(
                        ConnectionMethod.PG_WIRE_IAM_PROTOCOL, pg_wire_database
                    )
                    try:
                        internal_create_connection(
                            region=region,
                            database_type=DatabaseType.APG,
                            connection_method=ConnectionMethod.PG_WIRE_IAM_PROTOCOL,
                            cluster_identifier=cluster_identifier,
                            db_endpoint=valid_endpoint,
                            port=port,
                            database=pg_wire_database,
                        )
                        record(step, False, 'Expected ValueError at connect time, got success')
                    except ValueError as e:
                        ok = 'Failed to retrieve credentials from Secrets Manager' in str(e)
                        record(step, ok, str(e))
                    except Exception as e:
                        record(step, False, f'Expected ValueError, got {type(e).__name__}: {e}')
                else:
                    clear_cached_connection(ConnectionMethod.PG_WIRE_PROTOCOL)
                    # Connect is expected to succeed — no Secrets Manager call here.
                    internal_create_connection(
                        region=region,
                        database_type=DatabaseType.APG,
                        connection_method=ConnectionMethod.PG_WIRE_PROTOCOL,
                        cluster_identifier=cluster_identifier,
                        db_endpoint=valid_endpoint,
                        port=port,
                        database=database,
                    )
                    rows = await run_query(
                        sql='SELECT 1',
                        ctx=ctx,
                        connection_method=ConnectionMethod.PG_WIRE_PROTOCOL,
                        cluster_identifier=cluster_identifier,
                        db_endpoint=valid_endpoint,
                        database=database,
                    )
                    ok = bool(rows) and 'error' in rows[0]
                    record(step, ok, str(rows[0]) if rows else 'no rows')
            finally:
                reset_to_real_secret()
                # Leave a clean slate for the next case.
                if cluster_kind == 'express':
                    clear_cached_connection(
                        ConnectionMethod.PG_WIRE_IAM_PROTOCOL, pg_wire_database
                    )
                else:
                    clear_cached_connection(ConnectionMethod.PG_WIRE_PROTOCOL)

        # ------------------------------------------------------------------
        # Case 6: Configured ARN overrides cluster metadata.
        # When configured_secret_arns is set, internal_create_connection
        # must ignore the cluster's MasterUserSecret.SecretArn even if
        # describe_db_clusters reports a different (bogus) ARN. This is
        # the security guarantee for an operator who pinned a specific
        # secret via --secret_arn and doesn't trust whatever the cluster
        # advertises. Serverless only — express doesn't support RDS_API.
        # ------------------------------------------------------------------
        step = 'configured_arn_overrides_cluster_metadata'
        if cluster_kind == 'express':
            record_not_applicable(result, step, 'RDS_API not supported on express cluster')
        else:
            try:
                reset_to_real_secret()
                clear_cached_connection(ConnectionMethod.RDS_API)

                # Return the real cluster properties with the MasterUserSecret
                # rewritten to an ARN the caller has no access to. The
                # configured (real) ARN must win, so SELECT 1 still works.
                tampered_props = dict(cluster_props)
                tampered_props['MasterUserSecret'] = {
                    'SecretArn': 'arn:aws:secretsmanager:us-east-1:000000000000:secret:attacker-owned-MNOPQR',  # pragma: allowlist secret
                }

                with patch(
                    'awslabs.postgres_mcp_server.server.internal_get_cluster_properties',
                    return_value=tampered_props,
                ):
                    internal_create_connection(
                        region=region,
                        database_type=DatabaseType.APG,
                        connection_method=ConnectionMethod.RDS_API,
                        cluster_identifier=cluster_identifier,
                        db_endpoint=valid_endpoint,
                        port=port,
                        database=database,
                    )
                    rows = await run_query(
                        sql='SELECT 1',
                        ctx=ctx,
                        connection_method=ConnectionMethod.RDS_API,
                        cluster_identifier=cluster_identifier,
                        db_endpoint=valid_endpoint,
                        database=database,
                    )
                ok = bool(rows) and 'error' not in rows[0]
                record(step, ok, str(rows[0]) if rows else 'no rows')
            except Exception as e:
                record(step, False, f'{type(e).__name__}: {e}')

    finally:
        server.configured_secret_arns.clear()
        server.configured_secret_arns.update(saved_secret_arns)
        server.configured_default_secret_arn = saved_default_secret_arn

    return result


def run_startup_secret_arn_validation_suite(
    cluster_identifier: str,
    region: str,
) -> TestResult:
    """Test that main()'s startup probe fails fast on an unreadable ARN.

    Drives server.main() twice via monkeypatched sys.argv:

      1. Unreadable ARN (non-existent secret in an account we don't
         control) → expect SystemExit(1) before mcp.run is reached.
      2. Readable ARN (the real cluster secret) → expect main() to
         succeed through to mcp.run without SystemExit.

    Exercises the validate_secret_arn_at_startup gate we added to main().
    """
    from unittest.mock import patch

    result = TestResult(
        cluster_identifier=cluster_identifier,
        connection_method_name='startup_secret_arn_validation',
        passed=[],
        failed=[],
    )

    logger.info(f'\n{"=" * 60}')
    logger.info('Running startup-secret-ARN validation suite')
    logger.info(f'{"=" * 60}')

    def record(step, ok, detail=''):
        log_step(step, 'PASS' if ok else 'FAIL', detail)
        if ok:
            result.passed.append(step)
        else:
            result.failed.append((step, detail))

    from awslabs.postgres_mcp_server.connection.cp_api_connection import (
        internal_get_cluster_properties,
    )

    cluster_props = internal_get_cluster_properties(cluster_identifier, region)
    real_secret_arn = cluster_props.get('MasterUserSecret', {}).get('SecretArn', '') or ''
    has_managed_secret = bool(real_secret_arn)
    if has_managed_secret:
        record('startup_resolve_real_secret_arn', True, real_secret_arn)
    else:
        record(
            'startup_resolve_real_secret_arn',
            True,
            f'cluster {cluster_identifier} has no MasterUserSecret '
            '(case 2 will be skipped — IAM-only cluster)',
        )

    saved_argv = sys.argv[:]
    saved_secret_arns = dict(server.configured_secret_arns)
    saved_default_secret_arn = server.configured_default_secret_arn

    try:
        # --------------------------------------------------------------
        # Case 1: Unreadable ARN → SystemExit(1), mcp.run never called.
        # --------------------------------------------------------------
        step = 'main_exits_on_unreadable_secret_arn'
        unreadable_arn = (
            'arn:aws:secretsmanager:us-east-1:000000000000:secret:mcp-e2e-unreadable-XYZABC'
        )
        sys.argv = [
            'server.py',
            '--region',
            region,
            '--secret_arn',
            unreadable_arn,
        ]
        mcp_run_called = {'count': 0}

        def _fail_if_called():
            mcp_run_called['count'] += 1

        try:
            with patch('awslabs.postgres_mcp_server.server.mcp.run', _fail_if_called):
                try:
                    server.main()
                    record(step, False, 'main() returned instead of exiting')
                except SystemExit as e:
                    ok = e.code == 1 and mcp_run_called['count'] == 0
                    record(
                        step,
                        ok,
                        f'exit_code={e.code}, mcp_run_invocations={mcp_run_called["count"]}',
                    )
        except Exception as e:
            record(step, False, f'{type(e).__name__}: {e}')

        # --------------------------------------------------------------
        # Case 2: Readable ARN → main() runs through to mcp.run.
        # Skipped on IAM-only clusters (no managed secret to point at).
        # --------------------------------------------------------------
        step = 'main_succeeds_on_readable_secret_arn'
        if not has_managed_secret:
            record_not_applicable(
                result,
                step,
                'cluster has no managed secret (IAM-only express cluster)',
            )
        else:
            sys.argv = [
                'server.py',
                '--region',
                region,
                '--secret_arn',
                real_secret_arn,
            ]
            mcp_run_called = {'count': 0}

            def _record_call():
                mcp_run_called['count'] += 1

            try:
                with patch('awslabs.postgres_mcp_server.server.mcp.run', _record_call):
                    server.main()
                ok = mcp_run_called['count'] == 1
                record(step, ok, f'mcp_run_invocations={mcp_run_called["count"]}')
            except SystemExit as e:
                record(step, False, f'unexpected SystemExit({e.code})')
            except Exception as e:
                record(step, False, f'{type(e).__name__}: {e}')

    finally:
        sys.argv = saved_argv
        server.configured_secret_arns.clear()
        server.configured_secret_arns.update(saved_secret_arns)
        server.configured_default_secret_arn = saved_default_secret_arn

    return result


# Read queries that MUST be allowed in both read-only and write mode.
# These mirror the positive-path unit tests in tests/test_sql_guard.py but
# exercise the full run_query path against a real cluster.
# Every allowed read node type from the design's read-only allowlist (FR2).
# All must succeed in both read-only and write mode against a real cluster.
ALLOWED_READ_QUERIES = [
    # SelectStmt: plain SELECT, subquery, aggregate.
    'SELECT 1',
    'SELECT version()',
    "SELECT 'hello' AS greeting",
    'SELECT count(*) FROM pg_class',
    'SELECT id FROM (SELECT 1 AS id) sub WHERE id = 1',
    # SelectStmt: VALUES and TABLE spellings.
    'VALUES (1), (2)',
    # TABLE spelling. Uses a single-column information_schema view (one varchar
    # column) rather than a catalog like pg_am: pg_am.amhandler is a `regproc`,
    # a type the RDS Data API cannot serialize (UnsupportedResultException), so
    # the earlier vector failed on the RDS_API path even though the guard
    # correctly allowed the read. This view's result is serializable on both the
    # PG-Wire and RDS Data API paths.
    'TABLE information_schema.information_schema_catalog_name',
    # SelectStmt: WITH ... SELECT (read-only CTE).
    'WITH cte AS (SELECT 1 AS n) SELECT n FROM cte',
    # VariableShowStmt: SHOW.
    'SHOW work_mem',
    'SHOW ALL',
    # ExplainStmt: plain and ANALYZE of a read (EXPLAIN ANALYZE SELECT executes
    # a pure read and is allowed; the ANALYZE flag is not inspected -- FR2).
    'EXPLAIN SELECT 1',
    'EXPLAIN ANALYZE SELECT 1',
    # UNION / OR 1=1 are valid reads -- the injection-pattern heuristic was
    # dropped, so they must no longer be false-positived.
    'SELECT 1 UNION SELECT 2',
    'SELECT 1 WHERE 1 = 1 OR 1 = 1',
]

# Queries that MUST be blocked in read-only mode (mutating keywords).
# Each is a real statement an LLM might emit; run_query should reject it
# before it reaches the database when readonly is on.
# Every write-set category from design section 3.1. Each MUST be rejected in
# read-only mode (with a "not allowed in read-only mode" message) and MUST NOT
# be rejected by the read-only guard in write mode (it may still error at the DB
# for unrelated reasons, e.g. a missing table). None of these are in the
# dangerous set, so write mode lets them past the guard.
READONLY_BLOCKED_QUERIES = [
    # DML
    'INSERT INTO t (a) VALUES (1)',
    'UPDATE t SET a = 1 WHERE id = 2',
    'DELETE FROM t WHERE id = 1',
    'MERGE INTO t USING s ON t.id = s.id WHEN MATCHED THEN DELETE',
    'TRUNCATE TABLE t',
    # DDL
    'CREATE TABLE t (id int)',
    'ALTER TABLE t ADD COLUMN c int',
    'DROP TABLE t',
    'ALTER TABLE t RENAME TO t2',
    'CREATE VIEW v AS SELECT 1',
    'CREATE INDEX idx ON t (a)',
    'CREATE SEQUENCE seq',
    'CREATE SCHEMA s',
    'CREATE FUNCTION f() RETURNS int AS $$ SELECT 1 $$ LANGUAGE sql',
    'CREATE EXTENSION IF NOT EXISTS citext',
    # Metadata
    "COMMENT ON TABLE t IS 'x'",
    "SECURITY LABEL ON TABLE t IS 'x'",
    'IMPORT FOREIGN SCHEMA remote FROM SERVER srv INTO local',
    # Permissions
    'GRANT SELECT ON t TO bob',
    'REVOKE SELECT ON t FROM bob',
    # Maintenance
    'VACUUM t',
    'ANALYZE t',
    'CLUSTER t USING idx',
    'REINDEX TABLE t',
    'REFRESH MATERIALIZED VIEW mv',
    # Procedural / dynamic
    'DO $$ BEGIN PERFORM 1; END $$',
    'CALL some_proc()',
    # Prepared statements
    'PREPARE p AS SELECT 1',
    'EXECUTE p',
    'DEALLOCATE p',
    # Async / locking
    'LISTEN e2e_chan',
    'NOTIFY e2e_chan',
    'UNLISTEN e2e_chan',
    'LOCK TABLE t',
    # Session / backend state. Narrow RESET/DISCARD forms are ordinary writes;
    # the bulk forms are mode-independent policy below.
    "SET work_mem = '64MB'",
    'RESET work_mem',
    'DISCARD PLANS',
    'DISCARD SEQUENCES',
    'DISCARD TEMP',
    "LOAD 'auto_explain'",
    "SELECT set_config('work_mem', '64MB', false)",  # function form of SET
    # Transaction control
    'BEGIN',
    'COMMIT',
    'ROLLBACK',
    'SAVEPOINT sp',
    'ALTER SYSTEM SET wal_level = replica',
    # Client-side COPY (not PROGRAM, not a server file -> write set, not dangerous)
    'COPY t FROM STDIN',
    'COPY t TO STDOUT',
    # SelectStmt-that-writes and EXPLAIN-of-a-write (field/tree checks)
    'SELECT * INTO e2e_tmp FROM pg_class',
    'EXPLAIN INSERT INTO t (a) VALUES (1)',
    'WITH x AS (INSERT INTO t VALUES (1) RETURNING *) SELECT * FROM x',  # FR3 DML-in-CTE
    # Cursor family (Decision A tightening)
    'DECLARE e2e_cur CURSOR FOR SELECT 1',
    'FETCH 1 FROM e2e_cur',
    'MOVE 1 IN e2e_cur',
    'CLOSE e2e_cur',
    # Latent-gap commands the old regex missed
    'CHECKPOINT',
    'REASSIGN OWNED BY bob TO alice',
    "COMMIT PREPARED 'gid'",
]

# Every audited semantic function mutator is exercised through the real
# run_query path. The schema-qualified cast target is first proven absent by the
# suite, so write-mode probes fail during DB type resolution before any function
# can execute. This safely verifies “read-only guard rejects / write-mode guard
# permits” even for WAL, backup, replication, statistics-reset, index, and
# extension functions.
_POLICY_PROBE_SCHEMA = 'mcp_e2e_policy_probe_schema_must_not_exist'
_POLICY_PROBE_TYPE = f'{_POLICY_PROBE_SCHEMA}.missing_type'
_READ_ONLY_MUTATOR_CALLS = [
    f'SELECT {fn}(NULL::{_POLICY_PROBE_TYPE})'
    for fn in sorted(READ_ONLY_PROHIBITED_MUTATING_FUNCTIONS)
]
_READ_ONLY_QUALIFIED_MUTATOR_CALLS = [
    f'SELECT {schema}.{name}(NULL::{_POLICY_PROBE_TYPE})'
    for (schema, name) in sorted(READ_ONLY_PROHIBITED_QUALIFIED_FUNCTIONS)
]
_SAFE_MUTATOR_PROBES = set(_READ_ONLY_MUTATOR_CALLS + _READ_ONLY_QUALIFIED_MUTATOR_CALLS)
READONLY_BLOCKED_QUERIES += sorted(_SAFE_MUTATOR_PROBES)

# Queries that MUST be blocked in BOTH read-only and write mode because they
# are in the dangerous set (dangerous functions and security-sensitive GUCs),
# which the parser-based guard rejects regardless of the readonly flag.
# The dangerous set (design section 3.1): rejected regardless of read/write
# mode (FR4-FR6). The bare-function, schema-qualified, and security-GUC entries
# are generated from the guard's own constants so this suite covers EVERY entry
# and cannot drift out of sync with the implementation. The guard rejects by
# resolved name before execution, so these hold even where the extension or
# function is not installed on the test cluster.
_DANGEROUS_FUNCTION_CALLS = [f'SELECT {fn}()' for fn in sorted(DANGEROUS_FUNCTIONS)]
_DANGEROUS_QUALIFIED_CALLS = [
    f'SELECT {schema}.{name}()' for (schema, name) in sorted(DANGEROUS_QUALIFIED_FUNCTIONS)
]
_SECURITY_GUC_STATEMENTS = [f'SET {g} = off' for g in sorted(SECURITY_SENSITIVE_GUCS)] + [
    f"SELECT set_config('{g}', 'off', false)" for g in sorted(SECURITY_SENSITIVE_GUCS)
]

# Realistic shapes (real arguments), the COPY forms (FR4), and the reported
# Unicode-escape evasion (FR6a) -- exercising the guard's structural/decoding
# behavior beyond the generated name-only calls.
_DANGEROUS_REALISTIC = [
    'RESET ALL',  # bulk reset includes security-sensitive GUCs
    'DISCARD ALL',  # same bulk reset plus broader session cleanup
    "SELECT pg_read_file('/etc/passwd')",
    'SELECT pg_sleep(30)',
    "SELECT dblink('host=169.254.169.254 port=80', 'SELECT 1')",  # SSRF -> IMDS
    "SELECT pg_file_write('/tmp/e2e', 'x', false)",  # adminpack host-file write
    "SELECT aws_lambda.invoke('arn', '{}')",
    "SELECT aws_s3.query_export_to_s3('SELECT 1', 'bucket', 'key')",
    "COPY (SELECT 1) TO PROGRAM 'id'",  # command execution
    "COPY t FROM PROGRAM 'curl http://169.254.169.254'",
    "COPY t TO '/tmp/e2e.csv'",  # server-side file write
    "COPY t FROM '/etc/passwd'",  # server-side file read
    # Unicode-escape identifier PostgreSQL resolves to pg_read_file; the guard
    # must still reject it because pglast decodes the escape (the reported bug).
    r"""SELECT U&"pg_read_fil\0065"('/etc/passwd')""",
]

# Fail-closed cases (FR1 single statement, FR7 parse error / oversized), also
# rejected regardless of mode.
_FAIL_CLOSED = [
    'SELECT 1; SELECT 2',  # multi-statement
    'INSERT INTO t VALUES (1); DROP TABLE t',  # stacked
    'SELCT bogus (((',  # parse error
    'SELECT ' + ('1,' * 40000) + '1',  # exceeds MAX_SQL_LEN
]

ALWAYS_BLOCKED_QUERIES = (
    _DANGEROUS_REALISTIC
    + _DANGEROUS_FUNCTION_CALLS
    + _DANGEROUS_QUALIFIED_CALLS
    + _SECURITY_GUC_STATEMENTS
    + _FAIL_CLOSED
)

# --- Full policy corpus (--full-policy-corpus) ------------------------------
# The corpora above are a curated subset chosen so a routine run stays quick.
# With --full-policy-corpus the suite instead drives the entire unit-level policy
# matrix (tests/test_policy_matrix.py) through the real run_query tool, making
# this suite a strict superset of the unit policy tests plus the cases only a
# live engine can decide (BACKSTOP_ENFORCED_QUERIES, PARAMETERIZED_READ_QUERIES).
#
# Six of the eight matrix cells need no database objects at all, because their
# expected outcome is a *guard* rejection and run_query calls the guard before it
# touches the connection: sets 2/3/4 in read-only mode, sets 3/4 in write mode,
# and set 2 in write mode (whose assertion tolerates database errors by design --
# see _SAFE_MUTATOR_PROBES). Only the two set-1 cells expect rows back, so only
# they need the probe schema provisioned below.
# What the full sweep asserts, and what it deliberately does not: every cell
# checks the *policy decision made through the real run_query tool*, tolerating a
# database error. It does not check that a statement executes successfully. The
# unit matrix was written for a parser, so 51 of its 200 reads cannot execute
# anywhere -- 23 carry `:name` placeholders needing bound parameters, 4 are the
# locking clauses the read-only transaction refuses on purpose, and 24
# deliberately reference objects that do not exist (`t`, `u`, `s`, `items`,
# `myschema`, large object 1) or extensions that are not installed, including the
# QUALIFIED_NEGATIVE entries whose entire point is a missing function proving the
# guard does not over-block on a bare name.
#
# Executability is therefore not a policy question and asserting it here would
# require a large, brittle exclusion list. ALLOWED_READ_QUERIES keeps the stronger
# "must return rows" assertion on a curated set that really runs; the full sweep
# answers the different question of whether the *decision* is right end-to-end.
FULL_POLICY_CORPUS = False

try:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    from test_policy_matrix import (  # noqa: E402
        SET_1_READS,
        SET_2_WRITES,
        SET_3_DANGEROUS,
        SET_4_FAIL_CLOSED,
    )

    POLICY_MATRIX_AVAILABLE = True
except Exception as _matrix_import_error:  # pragma: no cover - optional import
    SET_1_READS = SET_2_WRITES = SET_3_DANGEROUS = SET_4_FAIL_CLOSED = []
    POLICY_MATRIX_AVAILABLE = False
    _MATRIX_IMPORT_ERROR = _matrix_import_error

# Statements the guard deliberately ALLOWS and the read-only *transaction*
# refuses. Read-only enforcement is two layers -- the parser-based guard and the
# ``SET TRANSACTION READ ONLY`` wrapper the connection opens -- and only an
# end-to-end run can observe the second one, so this corpus exists here and
# cannot exist in the unit suite.
#
# Row-locking SELECTs write tuple headers, so they are not reads, but the guard
# does not carry a locking-clause check: PostgreSQL already refuses them with
# "cannot execute SELECT FOR UPDATE in a read-only transaction" (verified on
# PG 16.4 locally and on Aurora PG 17.5 through this suite). The assertions pin
# both halves -- in read-only mode the request must fail and the failure must come
# from the database rather than the guard; in write mode the same statement must
# no longer hit a read-only refusal. If the wrapper were ever dropped, the
# read-only assertion turns red instead of the reliance silently becoming an
# exposure.
#
# pg_class is used as the target because it exists on every cluster and needs no
# provisioning. A least-privilege role cannot actually lock it, so the write-mode
# outcome is a privilege error rather than a successful lock -- see the assertion
# comment in the suite for why that is the stronger evidence.
BACKSTOP_ENFORCED_QUERIES = [
    'SELECT * FROM pg_class FOR UPDATE',
    'SELECT * FROM pg_class FOR NO KEY UPDATE',
    'SELECT * FROM pg_class FOR SHARE',
    'SELECT * FROM pg_class FOR KEY SHARE',
]

# Reads that carry Aurora-style ``:name`` placeholders. These cross two
# independent rewrites -- the guard's parse-only ``$1`` substitution and the
# psycopg executor's ``%(name)s`` substitution -- and a disagreement between them
# corrupts a statement the guard already approved (the array-slice defect:
# ``tags[1:limit_idx]`` became the unparseable ``tags[1%(limit_idx)s]``). Each
# entry is (sql, query_parameters) and must succeed in BOTH modes.
PARAMETERIZED_READ_QUERIES = [
    ('SELECT :n::int AS n', [{'name': 'n', 'value': {'longValue': 7}}]),
    (
        'SELECT relname FROM pg_class WHERE relname = :name LIMIT 1',
        [{'name': 'name', 'value': {'stringValue': 'pg_class'}}],
    ),
    (
        "SELECT 'a:b' AS literal_colon, :n::int AS n",
        [{'name': 'n', 'value': {'longValue': 2}}],
    ),
    (
        'SELECT count(*) FROM pg_class WHERE relkind IN (:a, :b)',
        [
            {'name': 'a', 'value': {'stringValue': 'r'}},
            {'name': 'b', 'value': {'stringValue': 'v'}},
        ],
    ),
]

# An array slice alongside a placeholder. Held separately because the RDS Data
# API cannot run it at all, for reasons that have nothing to do with this server.
#
# Three layers independently decide which ``:name`` sequences are placeholders:
# the SQL guard's parse-only rewrite, the psycopg executor's ``%(name)s`` rewrite,
# and -- on the RDS_API path -- the Data API's own server-side scanner. The first
# two share one pattern and correctly leave a slice colon alone, because the colon
# in ``[1:2]`` is preceded by a word character. The Data API's scanner does not: it
# reads the ``:2`` as a placeholder named "2" and rejects the call before
# PostgreSQL ever sees it, with
# ``ValidationException: Cannot find parameter: 2`` (observed on Aurora PG 17.5).
#
# It is literal-aware and cast-aware -- ``'a:b'``, ``:n::int`` and ``IN (:a, :b)``
# all work, which is why those stay in the corpus above. The gap is specific to
# the slice. So this runs on the PG-Wire paths, where it is the regression guard
# for the defect that motivated it (the executor once turned
# ``tags[1:limit_idx]`` into the unparseable ``tags[1%(limit_idx)s]``), and is
# recorded N/A on RDS_API rather than asserted as a permanent AWS bug.
PARAMETERIZED_SLICE_READS = [
    (
        "SELECT (ARRAY['a','b','c'])[1:2] AS slice, :n::int AS n",
        [{'name': 'n', 'value': {'longValue': 1}}],
    ),
    (
        'SELECT (ARRAY[10,20,30])[2:3] AS slice, :name AS label',
        [{'name': 'name', 'value': {'stringValue': 'x'}}],
    ),
]

# Why PARAMETERIZED_SLICE_READS cannot run on the Data API path.
DATA_API_SLICE_LIMITATION = (
    'RDS Data API reads the colon in an array slice as a named parameter '
    '("Cannot find parameter: 2"); unrelated to the MCP server'
)


async def run_query_enforcement_suite(
    cluster_identifier: str,
    region: str,
    database: str,
    valid_endpoint: str,
    port: int,
    cluster_kind: str,
    connection_method: ConnectionMethod,
    connection_method_name: str,
) -> TestResult:
    """Verify run_query's allow/block decisions under both readonly settings.

    The MCP server's ``--allow_write_query`` flag maps directly to the
    ``server.readonly_query`` global (``readonly_query = not
    allow_write_query``). Rather than recreate clusters or spawn a second
    MCP process per setting, this suite toggles that global in place and
    re-establishes the connection so the pooled connection picks up the
    new readonly state. Both the cluster and the MCP import are reused.

    This suite is the superset of the unit-level policy tests: read-only is
    enforced by two layers, the parser-based guard and the ``SET TRANSACTION
    READ ONLY`` wrapper the connection opens around every query, and only a run
    against a real engine can observe the second one. BACKSTOP_ENFORCED_QUERIES
    and PARAMETERIZED_READ_QUERIES exist for exactly that reason and have no
    unit-test equivalent.

    By default the policy corpora here are a curated subset, so a routine run
    stays quick. With ``--full-policy-corpus`` the suite drives every statement
    from the unit matrix through ``run_query`` as well, which makes the superset
    relationship literal rather than conceptual. That costs about a thousand extra
    round trips per connection method, which is why it is opt-in.

    Assertions, all driven through the real ``run_query`` tool:
      readonly = True  (server started WITHOUT --allow_write_query):
        - ALLOWED_READ_QUERIES succeed
        - READONLY_BLOCKED_QUERIES are rejected by the semantic write set
        - ALWAYS_BLOCKED_QUERIES are rejected by mode-independent policy
        - BACKSTOP_ENFORCED_QUERIES pass the guard and are then refused by the
          database's read-only transaction (the second layer, proven live)
        - PARAMETERIZED_READ_QUERIES survive both placeholder rewrites
        - PARAMETERIZED_SLICE_READS likewise, on the PG-Wire paths; N/A on
          RDS_API, which cannot express them (see DATA_API_SLICE_LIMITATION)
      readonly = False (server started WITH --allow_write_query):
        - ALLOWED_READ_QUERIES succeed
        - READONLY_BLOCKED_QUERIES are now allowed past the readonly
          guard (they may still error at the database for unrelated
          reasons like a missing table — we only assert they are not
          rejected by the MCP's readonly guard)
        - ALWAYS_BLOCKED_QUERIES are STILL rejected (mode-independent)
        - BACKSTOP_ENFORCED_QUERIES no longer hit a read-only refusal, since no
          read-only transaction is opened — which is what proves the read-only
          result above came from the wrapper. They may still fail on privileges
          (row locking needs more than SELECT, and this suite connects as a
          least-privilege role); PostgreSQL evaluates the read-only transaction
          before privileges, so the error changing from ReadOnlySqlTransaction to
          InsufficientPrivilege across modes is the evidence
        - PARAMETERIZED_READ_QUERIES still succeed
    """
    ctx = CapturingCtx()
    result = TestResult(
        cluster_identifier=cluster_identifier,
        connection_method_name=f'query_enforcement_{connection_method_name}',
        passed=[],
        failed=[],
    )

    logger.info(f'\n{"=" * 60}')
    logger.info(
        f'Running query-enforcement suite on {cluster_kind} '
        f'({connection_method_name}) cluster: {cluster_identifier}'
    )
    logger.info(f'{"=" * 60}')

    # Express clusters only auto-create the 'postgres' database; the
    # caller-supplied --database exists only on serverless. PG Wire and
    # RDS API both connect fine to 'postgres'.
    test_database = 'postgres'

    def record(step, ok, detail=''):
        """Record a test step result as passed or failed."""
        log_step(step, 'PASS' if ok else 'FAIL', detail)
        if ok:
            result.passed.append(step)
        else:
            result.failed.append((step, detail))

    _is_rejected = is_rejected
    _is_readonly_rejection = is_readonly_policy_rejection

    async def _connect():
        """(Re)establish the connection so it picks up readonly state.

        internal_create_connection reads the server.readonly_query
        global at connection-construction time, so the cached connection
        must be dropped and rebuilt whenever the mode changes.
        """
        # Drop any cached connection for this target first so the new
        # readonly state is actually applied.
        server.db_connection_map.remove(
            connection_method, cluster_identifier, valid_endpoint, test_database, port
        )
        return await connect_to_database(
            region=region,
            database_type=DatabaseType.APG,
            connection_method=connection_method,
            cluster_identifier=cluster_identifier,
            db_endpoint=valid_endpoint,
            port=port,
            database=test_database,
        )

    async def _run(sql, query_parameters=None):
        ctx.errors.clear()
        return await run_query(
            sql=sql,
            ctx=ctx,
            connection_method=connection_method,
            cluster_identifier=cluster_identifier,
            db_endpoint=valid_endpoint,
            database=test_database,
            query_parameters=query_parameters,
        )

    def _is_database_readonly_rejection(rows) -> bool:
        """True when the *database* refused the statement for read-only reasons."""
        return is_database_readonly_rejection(rows, ctx.errors)

    def _response_and_ctx_errors(rows) -> str:
        """Return visible + ctx-only errors (Data API redacts its return value)."""
        return f'{rows!r} {ctx.errors!r}'

    saved_readonly = server.readonly_query
    try:
        # ----------------------------------------------------------------
        # Mode 1: read-only (server started WITHOUT --allow_write_query)
        # ----------------------------------------------------------------
        server.readonly_query = True
        try:
            resp = await _connect()
            if 'Failed' in str(resp):
                record('readonly:connect', False, str(resp))
                return result
            record('readonly:connect', True, 'connected with readonly=True')
        except Exception as e:
            record('readonly:connect', False, f'{type(e).__name__}: {e}')
            return result

        # Prove the schema used to make mutator probes non-executable does not
        # exist. If it did, write-mode probes might resolve and execute a real
        # state-changing function, so fail/stop before running either mode.
        step = 'policy-probe:sentinel schema absent'
        try:
            rows = await _run(
                f"SELECT to_regnamespace('{_POLICY_PROBE_SCHEMA}') IS NULL AS absent"
            )
            absent = bool(rows) and isinstance(rows[0], dict) and bool(rows[0].get('absent'))
            record(step, absent, _response_and_ctx_errors(rows)[:160])
            if not absent:
                return result
        except Exception as e:
            record(step, False, f'{type(e).__name__}: {e}')
            return result

        for sql in ALLOWED_READ_QUERIES:
            step = f'readonly:allow {sql[:48]}'
            try:
                rows = await _run(sql)
                record(step, not _is_rejected(rows), str(rows)[:120])
            except Exception as e:
                record(step, False, f'{type(e).__name__}: {e}')

        # Cell (1, read-only): the read-only policy must not reject a read. A
        # database error is tolerated -- see the note on FULL_POLICY_CORPUS for
        # why executability is not the claim being tested here.
        if FULL_POLICY_CORPUS:
            for sql in SET_1_READS:
                step = f'full:set1-readonly-permitted {sql[:40]}'
                try:
                    rows = await _run(sql)
                    record(
                        step,
                        not _is_readonly_rejection(rows),
                        _response_and_ctx_errors(rows)[:160],
                    )
                except Exception as e:
                    record(step, False, f'{type(e).__name__}: {e}')

        # Cells (2, read-only), (3, read-only) and (4, read-only) over the whole
        # matrix. No database objects needed: the guard rejects before the
        # connection is used, so a missing table cannot affect the outcome.
        if FULL_POLICY_CORPUS:
            for sql in SET_2_WRITES:
                step = f'full:set2-readonly-blocked {sql[:40]}'
                try:
                    rows = await _run(sql)
                    record(
                        step, _is_readonly_rejection(rows), _response_and_ctx_errors(rows)[:160]
                    )
                except Exception as e:
                    record(step, False, f'{type(e).__name__}: {e}')
            for label, corpus in (('set3', SET_3_DANGEROUS), ('set4', SET_4_FAIL_CLOSED)):
                for sql in corpus:
                    step = f'full:{label}-readonly-blocked {sql[:40]}'
                    try:
                        rows = await _run(sql)
                        record(step, _is_rejected(rows), _response_and_ctx_errors(rows)[:160])
                    except Exception as e:
                        record(step, False, f'{type(e).__name__}: {e}')

        for sql in READONLY_BLOCKED_QUERIES:
            step = f'readonly:block {sql[:48]}'
            try:
                rows = await _run(sql)
                # Must be rejected specifically by the semantic read-only write set.
                record(step, _is_readonly_rejection(rows), str(rows)[:120])
            except Exception as e:
                record(step, False, f'{type(e).__name__}: {e}')

        for sql in ALWAYS_BLOCKED_QUERIES:
            step = f'readonly:always-block {sql[:48]}'
            try:
                rows = await _run(sql)
                record(step, _is_rejected(rows), str(rows)[:120])
            except Exception as e:
                record(step, False, f'{type(e).__name__}: {e}')

        # The second enforcement layer. These pass the guard on purpose, so the
        # only thing that can stop them is the read-only transaction the
        # connection opens -- which is why this assertion is only possible here.
        for sql in BACKSTOP_ENFORCED_QUERIES:
            step = f'readonly:backstop-blocks {sql[:48]}'
            try:
                rows = await _run(sql)
                detail = _response_and_ctx_errors(rows)
                # Must be refused, and refused by the database rather than the
                # guard: a guard rejection here would mean the guard grew a
                # locking-clause check and this corpus needs rehoming.
                stopped_by_transaction = _is_database_readonly_rejection(
                    rows
                ) and not _is_readonly_rejection(rows)
                record(step, stopped_by_transaction, detail[:200])
            except Exception as e:
                record(step, False, f'{type(e).__name__}: {e}')

        # Parameterized reads must survive both placeholder rewrites and return
        # rows. A disagreement between the two rewrites corrupts the statement
        # after the guard has approved it, which no guard-level test can see.
        for sql, params in PARAMETERIZED_READ_QUERIES:
            step = f'readonly:param-read {sql[:48]}'
            try:
                rows = await _run(sql, params)
                record(step, not _is_rejected(rows), _response_and_ctx_errors(rows)[:200])
            except Exception as e:
                record(step, False, f'{type(e).__name__}: {e}')

        for sql, params in PARAMETERIZED_SLICE_READS:
            step = f'readonly:param-slice-read {sql[:42]}'
            if connection_method == ConnectionMethod.RDS_API:
                record_not_applicable(result, step, DATA_API_SLICE_LIMITATION)
                continue
            try:
                rows = await _run(sql, params)
                record(step, not _is_rejected(rows), _response_and_ctx_errors(rows)[:200])
            except Exception as e:
                record(step, False, f'{type(e).__name__}: {e}')

        # ----------------------------------------------------------------
        # Mode 2: write enabled (server started WITH --allow_write_query)
        # ----------------------------------------------------------------
        server.readonly_query = False
        try:
            resp = await _connect()
            if 'Failed' in str(resp):
                record('write:connect', False, str(resp))
                return result
            record('write:connect', True, 'connected with readonly=False')
        except Exception as e:
            record('write:connect', False, f'{type(e).__name__}: {e}')
            return result

        for sql in ALLOWED_READ_QUERIES:
            step = f'write:allow {sql[:48]}'
            try:
                rows = await _run(sql)
                record(step, not _is_rejected(rows), str(rows)[:120])
            except Exception as e:
                record(step, False, f'{type(e).__name__}: {e}')

        for sql in READONLY_BLOCKED_QUERIES:
            step = f'write:not-readonly-blocked {sql[:48]}'
            try:
                rows = await _run(sql)
                detail = _response_and_ctx_errors(rows)
                if sql in _SAFE_MUTATOR_PROBES:
                    # Strong oracle: the absent schema/type error proves the
                    # read-only policy permitted the SQL and the database began
                    # analysis, while also proving the mutator never executed.
                    lower_detail = detail.lower()
                    reached_db_safely = _POLICY_PROBE_SCHEMA in detail and (
                        'does not exist' in lower_detail or 'undefined' in lower_detail
                    )
                    record(step, reached_db_safely, detail[:160])
                else:
                    # Other write statements may fail for missing objects or
                    # privileges, but must not be rejected by read-only policy.
                    record(step, not _is_readonly_rejection(rows), detail[:160])
            except Exception as e:
                record(step, False, f'{type(e).__name__}: {e}')

        for sql in ALWAYS_BLOCKED_QUERIES:
            step = f'write:always-block {sql[:48]}'
            try:
                rows = await _run(sql)
                # Dangerous-set constructs are mode-independent, so they must
                # STILL be rejected by the guard even with writes enabled.
                record(step, _is_rejected(rows), str(rows)[:120])
            except Exception as e:
                record(step, False, f'{type(e).__name__}: {e}')

        # The same row-locking SELECTs must no longer hit a read-only refusal,
        # which is what proves the read-only rejection above came from the
        # transaction wrapper rather than something incidental.
        #
        # The assertion is the absence of a read-only refusal, not overall
        # success. Row locking needs more than SELECT on the target and this
        # suite deliberately connects as a least-privilege role, so the honest
        # outcome here is InsufficientPrivilege. That is *better* evidence than a
        # successful lock would be: PostgreSQL checks the read-only transaction
        # before it checks privileges, so seeing the error change from
        # ReadOnlySqlTransaction (read-only mode) to InsufficientPrivilege (write
        # mode) for the identical statement and role pins the mechanism -- the
        # read-only gate was there in one mode and absent in the other.
        for sql in BACKSTOP_ENFORCED_QUERIES:
            step = f'write:backstop-absent {sql[:48]}'
            try:
                rows = await _run(sql)
                detail = _response_and_ctx_errors(rows)
                no_readonly_refusal = not _is_database_readonly_rejection(
                    rows
                ) and not _is_readonly_rejection(rows)
                record(step, no_readonly_refusal, detail[:200])
            except Exception as e:
                record(step, False, f'{type(e).__name__}: {e}')

        for sql, params in PARAMETERIZED_READ_QUERIES:
            step = f'write:param-read {sql[:48]}'
            try:
                rows = await _run(sql, params)
                record(step, not _is_rejected(rows), _response_and_ctx_errors(rows)[:200])
            except Exception as e:
                record(step, False, f'{type(e).__name__}: {e}')

        for sql, params in PARAMETERIZED_SLICE_READS:
            step = f'write:param-slice-read {sql[:42]}'
            if connection_method == ConnectionMethod.RDS_API:
                record_not_applicable(result, step, DATA_API_SLICE_LIMITATION)
                continue
            try:
                rows = await _run(sql, params)
                record(step, not _is_rejected(rows), _response_and_ctx_errors(rows)[:200])
            except Exception as e:
                record(step, False, f'{type(e).__name__}: {e}')

        # The remaining matrix cells in write mode.
        if FULL_POLICY_CORPUS:
            # Cell (1, write): enabling writes must never restrict a read.
            for sql in SET_1_READS:
                step = f'full:set1-write-permitted {sql[:42]}'
                try:
                    rows = await _run(sql)
                    record(
                        step,
                        not _is_readonly_rejection(rows),
                        _response_and_ctx_errors(rows)[:160],
                    )
                except Exception as e:
                    record(step, False, f'{type(e).__name__}: {e}')

            # Cell (2, write): allowed past the read-only guard. The statement may
            # still fail at the database for a missing object or a privilege --
            # only a read-only-policy rejection is a failure here.
            for sql in SET_2_WRITES:
                step = f'full:set2-write-allowed {sql[:42]}'
                try:
                    rows = await _run(sql)
                    record(
                        step,
                        not _is_readonly_rejection(rows),
                        _response_and_ctx_errors(rows)[:160],
                    )
                except Exception as e:
                    record(step, False, f'{type(e).__name__}: {e}')

            # Cells (3, write) and (4, write): mode-independent, so enabling
            # writes must not unlock either.
            for label, corpus in (('set3', SET_3_DANGEROUS), ('set4', SET_4_FAIL_CLOSED)):
                for sql in corpus:
                    step = f'full:{label}-write-blocked {sql[:42]}'
                    try:
                        rows = await _run(sql)
                        record(step, _is_rejected(rows), _response_and_ctx_errors(rows)[:160])
                    except Exception as e:
                        record(step, False, f'{type(e).__name__}: {e}')

    finally:
        # Restore global and drop the test connection so later suites
        # start from a clean state.
        server.readonly_query = saved_readonly
        try:
            server.db_connection_map.remove(
                connection_method, cluster_identifier, valid_endpoint, test_database, port
            )
        except Exception as e:
            logger.warning(f'Non-fatal cleanup failure removing test DB connection: {e}')

    return result


def _make_throwaway_ca() -> Optional[str]:
    """Generate an unrelated self-signed CA PEM for the wrong-CA TLS test.

    Returns the path to a temp PEM, or None if ``openssl`` is unavailable. The
    cert is unrelated to the Amazon RDS CA, so ``verify-full``/``verify-ca``
    against it must fail -- proving the guard actually verifies the server cert
    rather than merely encrypting.
    """
    openssl = shutil.which('openssl')
    if not openssl:
        return None
    cert_fd, cert_path = tempfile.mkstemp(prefix='e2e-bogus-ca-', suffix='.pem')
    os.close(cert_fd)
    key_fd, key_path = tempfile.mkstemp(prefix='e2e-bogus-key-', suffix='.pem')
    os.close(key_fd)
    try:
        subprocess.run(
            [
                openssl,
                'req',
                '-x509',
                '-newkey',
                'rsa:2048',
                '-nodes',
                '-keyout',
                key_path,
                '-out',
                cert_path,
                '-days',
                '1',
                '-subj',
                '/CN=e2e-bogus-ca',
            ],
            check=True,
            capture_output=True,
            timeout=30,
        )
        return cert_path
    except (subprocess.SubprocessError, OSError):
        try:
            os.remove(cert_path)
        except OSError:
            # Best-effort cleanup of the temp cert; ignore deletion failures.
            pass
        return None
    finally:
        try:
            os.remove(key_path)  # the private key is never needed
        except OSError:
            # Best-effort cleanup of the temp key; ignore deletion failures.
            pass


async def run_tls_enforcement_suite(
    cluster_identifier: str,
    region: str,
    database: str,
    valid_endpoint: str,
    port: int,
    cluster_kind: str,
    connection_method: ConnectionMethod,
    connection_method_name: str,
) -> TestResult:
    """Validate TLS enforcement on the psycopg (PG Wire) path against a real cluster.

    Mirrors ``run_query_enforcement_suite``: toggles ``server.configured_sslmode``
    / ``server.configured_ca_bundle`` in place and reconnects, so no cluster
    changes or extra MCP processes are needed. Skipped on RDS_API (that path is
    verified HTTPS and has no sslmode).

    Cases, all driven through the real connect_to_database / run_query tools:
      1. verify-full (default, bundled combined AWS CA): connect succeeds AND the
         session is encrypted (``pg_stat_ssl.ssl`` is true) -- regression + a
         positive proof that the out-of-the-box default connects to the real
         cluster (verifying both CA chain and hostname) and TLS is in effect.
      2. require: connect succeeds and the session is encrypted (no cert verify).
      3. verify-full + an unrelated (throwaway) CA: a query cannot succeed --
         proves the default mode genuinely verifies the certificate against the
         trusted CA, not just "SSL on".
    """
    result = TestResult(
        cluster_identifier=cluster_identifier,
        connection_method_name=f'tls_enforcement_{connection_method_name}',
        passed=[],
        failed=[],
    )

    def record(step, ok, detail=''):
        """Record a test step result as passed or failed."""
        log_step(step, 'PASS' if ok else 'FAIL', detail)
        if ok:
            result.passed.append(step)
        else:
            result.failed.append((step, detail))

    def record_skip(step, reason):
        """Record a step as skipped -- NOT passed.

        A skip means the check did not run (missing CA bundle / openssl), so it
        must not report green: TestResult.success counts skipped as not-pass, so
        a suite that could verify nothing fails rather than falsely passing.
        """
        log_step(step, 'SKIP', reason)
        assert result.skipped is not None
        result.skipped.append((step, reason))

    # sslmode applies only to the psycopg (PG Wire) path. The RDS Data API
    # connects over verified HTTPS and has no sslmode, so there is nothing to
    # test there.
    if connection_method == ConnectionMethod.RDS_API:
        record_not_applicable(
            result, 'tls:skipped', 'RDS Data API path is verified HTTPS (no sslmode)'
        )
        return result

    logger.info(f'\n{"=" * 60}')
    logger.info(
        f'Running TLS-enforcement suite on {cluster_kind} '
        f'({connection_method_name}) cluster: {cluster_identifier}'
    )
    logger.info(f'{"=" * 60}')

    # Capture the server certificate + default validation posture up front, so
    # every run's log shows exactly what cert the endpoint presents and how the
    # bundled AWS CA verifies it -- invaluable when a TLS case fails.
    log_tls_diagnostics(
        valid_endpoint,
        port,
        server.configured_ca_bundle or _bundled_ca_file(),
        server.configured_sslmode,
        label=f'{cluster_kind} default posture',
    )

    ctx = DummyCtx()
    test_database = 'postgres'

    def _is_rejected(rows) -> bool:
        return bool(rows) and isinstance(rows[0], dict) and 'error' in rows[0]

    async def _reconnect() -> str:
        """Drop the cached connection and reconnect under the current TLS globals."""
        server.db_connection_map.remove(
            connection_method, cluster_identifier, valid_endpoint, test_database, port
        )
        return str(
            await connect_to_database(
                region=region,
                database_type=DatabaseType.APG,
                connection_method=connection_method,
                cluster_identifier=cluster_identifier,
                db_endpoint=valid_endpoint,
                port=port,
                database=test_database,
            )
        )

    async def _run(sql):
        return await run_query(
            sql=sql,
            ctx=ctx,
            connection_method=connection_method,
            cluster_identifier=cluster_identifier,
            db_endpoint=valid_endpoint,
            database=test_database,
        )

    async def _session_is_encrypted() -> bool:
        """True if the current backend's connection is SSL (pg_stat_ssl)."""
        rows = await _run('SELECT ssl FROM pg_stat_ssl WHERE pid = pg_backend_pid()')
        if _is_rejected(rows) or not rows or not isinstance(rows[0], dict):
            return False
        val = rows[0].get('ssl')
        return str(val).strip().lower() in ('true', 't', 'on', '1')

    saved_sslmode = server.configured_sslmode
    saved_ca_bundle = server.configured_ca_bundle
    throwaway_ca: Optional[str] = None
    try:
        # Case 1: verify-full (default) -- connect out of the box and prove TLS is on.
        step = 'tls:verify-full (default) connect + pg_stat_ssl'
        if _bundled_ca_file() is None:
            record_skip(step, 'bundled AWS CA not present; run `python hatch_build.py`')
        else:
            try:
                server.configured_sslmode = 'verify-full'
                server.configured_ca_bundle = None
                resp = await _reconnect()
                if 'Failed' in resp:
                    record(step, False, f'connect failed: {resp[:160]}')
                else:
                    record(step, await _session_is_encrypted(), 'encrypted session confirmed')
            except Exception as e:
                record(step, False, f'{type(e).__name__}: {e}')

        # Case 2: require -- encrypted, no certificate verification.
        step = 'tls:require connect + pg_stat_ssl'
        try:
            server.configured_sslmode = 'require'
            server.configured_ca_bundle = None
            resp = await _reconnect()
            if 'Failed' in resp:
                record(step, False, f'connect failed: {resp[:160]}')
            else:
                record(step, await _session_is_encrypted(), 'encrypted session confirmed')
        except Exception as e:
            record(step, False, f'{type(e).__name__}: {e}')

        # Case 3: verify-full (the default) + an unrelated CA -- must NOT yield a
        # working session (proves the default mode verifies the cert, not just
        # encrypts).
        step = 'tls:verify-full wrong-CA rejected'
        throwaway_ca = _make_throwaway_ca()
        if throwaway_ca is None:
            record_skip(step, 'openssl unavailable to generate a throwaway CA')
        else:
            try:
                server.configured_sslmode = 'verify-full'
                server.configured_ca_bundle = throwaway_ca
                resp = await _reconnect()
                # Either the connect fails, or a trivial query fails -- either
                # way verify-full must refuse to run against an untrusted cert.
                rejected = 'Failed' in resp or _is_rejected(await _run('SELECT 1'))
                record(
                    step,
                    rejected,
                    'untrusted cert correctly rejected'
                    if rejected
                    else 'ERROR: connected/queried with an untrusted CA',
                )
            except psycopg.OperationalError as e:
                # A raised TLS error is a correct rejection ONLY when it is a
                # certificate-verification failure. Any other OperationalError
                # (DNS, auth, connection refused) is NOT what this test proves,
                # so it must fail rather than count as a green rejection.
                msg = str(e).lower()
                cert_failure = any(
                    marker in msg
                    for marker in (
                        'certificate verify failed',
                        'certificate verify',
                        'self-signed certificate',
                        'self signed certificate',
                        'unable to get local issuer',
                        'ssl error',
                    )
                )
                if cert_failure:
                    record(step, True, f'untrusted cert correctly rejected ({type(e).__name__})')
                else:
                    record(step, False, f'non-cert OperationalError (does not prove TLS): {e}')
    finally:
        server.configured_sslmode = saved_sslmode
        server.configured_ca_bundle = saved_ca_bundle
        if throwaway_ca:
            try:
                os.remove(throwaway_ca)
            except OSError as e:
                logger.warning(
                    f'Non-fatal cleanup failure removing throwaway CA bundle {throwaway_ca}: {e}'
                )
        try:
            server.db_connection_map.remove(
                connection_method, cluster_identifier, valid_endpoint, test_database, port
            )
        except Exception as e:
            logger.warning(f'Non-fatal cleanup failure removing test DB connection: {e}')

    return result


async def run_privilege_enforcement_suite(
    cluster_identifier: str,
    region: str,
    valid_endpoint: str,
    port: int,
    cluster_kind: str,
    connection_method: ConnectionMethod,
    connection_method_name: str,
    lp_secret_arn: Optional[str] = None,
) -> TestResult:
    """Verify the least-privilege guardrail (``server.privilege_check_policy``).

    Exercises both a superuser and (when provisioned) a least-privilege role by
    swapping which secret the connection resolves to and toggling the policy:

      Master user (rds_superuser) — selected by clearing the per-cluster secret
      pin so resolution falls back to the cluster metadata / MasterUsername:
        - ``enforce`` → connection **rejected** ("over-privileged")
        - ``warn`` / ``off`` → connection **allowed**

      Least-privilege role — selected by pinning its provisioned secret ARN
      (skipped with a note if no least-privilege role was provisioned for this
      cluster, e.g. the serverless cluster in the express-only setup):
        - ``enforce`` → connection **allowed**

    Restores the policy and the secret-pin map on exit.
    """
    result = TestResult(
        cluster_identifier=cluster_identifier,
        connection_method_name=f'privilege_enforcement_{connection_method_name}',
        passed=[],
        failed=[],
    )
    test_database = 'postgres'

    logger.info(f'\n{"=" * 60}')
    logger.info(
        f'Running privilege-enforcement suite on {cluster_kind} '
        f'({connection_method_name}) cluster: {cluster_identifier}'
    )
    logger.info(f'{"=" * 60}')

    def record(step, ok, detail=''):
        """Record a test step result as passed or failed."""
        log_step(step, 'PASS' if ok else 'FAIL', detail)
        if ok:
            result.passed.append(step)
        else:
            result.failed.append((step, detail))

    async def _connect():
        """Drop any cached connection and reconnect with the current pin."""
        server.db_connection_map.remove(
            connection_method, cluster_identifier, valid_endpoint, test_database, port
        )
        return str(
            await connect_to_database(
                region=region,
                database_type=DatabaseType.APG,
                connection_method=connection_method,
                cluster_identifier=cluster_identifier,
                db_endpoint=valid_endpoint,
                port=port,
                database=test_database,
            )
        )

    saved_policy = server.privilege_check_policy
    saved_secret_arns = dict(server.configured_secret_arns)

    try:
        # --- superuser (master): clear the pin → metadata/MasterUsername ---
        server.configured_secret_arns.pop(cluster_identifier, None)

        server.privilege_check_policy = server.PRIVILEGE_CHECK_ENFORCE
        try:
            resp = await _connect()
            record(
                'enforce:superuser_rejected',
                'Failed' in resp and 'over-privileged' in resp,
                resp[:200],
            )
        except Exception as e:
            record('enforce:superuser_rejected', False, f'{type(e).__name__}: {e}')

        server.privilege_check_policy = server.PRIVILEGE_CHECK_WARN
        try:
            resp = await _connect()
            record('warn:superuser_allowed', 'Failed' not in resp, resp[:200])
        except Exception as e:
            record('warn:superuser_allowed', False, f'{type(e).__name__}: {e}')

        server.privilege_check_policy = server.PRIVILEGE_CHECK_OFF
        try:
            resp = await _connect()
            record('off:superuser_allowed', 'Failed' not in resp, resp[:200])
        except Exception as e:
            record('off:superuser_allowed', False, f'{type(e).__name__}: {e}')

        # --- least-privilege role: pin its secret and connect under enforce ---
        if lp_secret_arn:
            server.configured_secret_arns[cluster_identifier] = lp_secret_arn
            server.privilege_check_policy = server.PRIVILEGE_CHECK_ENFORCE
            try:
                resp = await _connect()
                record('enforce:least_priv_allowed', 'Failed' not in resp, resp[:200])
            except Exception as e:
                record('enforce:least_priv_allowed', False, f'{type(e).__name__}: {e}')
        else:
            # skipped is initialized to [] by TestResult.__post_init__; assert
            # for the type-checker, which can't narrow the Optional here.
            assert result.skipped is not None
            result.skipped.append(
                (
                    'enforce:least_priv_allowed',
                    'no least-privilege role provisioned for this cluster',
                )
            )

    finally:
        server.privilege_check_policy = saved_policy
        server.configured_secret_arns.clear()
        server.configured_secret_arns.update(saved_secret_arns)
        try:
            server.db_connection_map.remove(
                connection_method, cluster_identifier, valid_endpoint, test_database, port
            )
        except Exception as e:
            logger.warning(f'Non-fatal cleanup failure removing test DB connection: {e}')

    return result


def print_summary(results: list[TestResult]):
    """Print a formatted summary of all test results.

    Returns True if every recorded TestResult is a clean pass (no failed
    steps and no skipped steps). Skipped tests count as not-pass so the
    process exits non-zero whenever any planned case couldn't run.
    """
    logger.info(f'\n{"=" * 60}')
    logger.info('TEST SUMMARY')
    logger.info(f'{"=" * 60}')
    all_passed = True
    total_pass = 0
    total_fail = 0
    total_skip = 0
    total_na = 0
    for r in results:
        if r.failed:
            status = 'FAILED'
        elif r.skipped:
            status = 'SKIPPED'
        else:
            # A suite with only passes and/or N/A entries is a clean pass:
            # N/A does not count against success.
            status = 'PASSED'
        logger.info(f'\n  {r.connection_method_name} ({r.cluster_identifier}): {status}')
        for s in r.passed:
            logger.info(f'    [PASS] {s}')
            total_pass += 1
        for step, reason in r.not_applicable or []:
            logger.info(f'    [N/A] {step}: {reason}')
            total_na += 1
        for step, reason in r.skipped or []:
            logger.warning(f'    [SKIP] {step}: {reason}')
            total_skip += 1
        for step, error in r.failed:
            logger.error(f'    [FAIL] {step}')
            if error:
                logger.error(f'      Error: {error}')
            total_fail += 1
        if not r.success:
            all_passed = False
    logger.info(f'\n{"=" * 60}')
    logger.info(
        f'Totals: {total_pass} passed, {total_fail} failed, {total_skip} skipped, {total_na} n/a'
    )
    logger.info(f'Overall: {"ALL PASSED" if all_passed else "FAILURES OR SKIPS PRESENT"}')
    logger.info(f'{"=" * 60}\n')
    return all_passed


async def main_async(args):
    """Main async entry point: create clusters, run suites, summarize, cleanup.

    Builds an explicit test plan up front so every planned case appears in
    the summary even if an upstream failure prevents it from running. The
    runner walks the plan, marks each entry passed/failed/skipped, and
    surfaces hard MCP-startup failures as a cascading skip reason for
    every subsequent entry.

    Plan structure:
      Phase 1: create the express cluster (always) and, when
               --test-serverless-cluster is set, the serverless cluster.
               Each creation is recorded as a test case so creation
               failures count toward the exit code.
      Phase 2: functional SQL suite, run once per compatible
               (cluster_kind, connection_method) cell.
      Phase 3: per-cluster security suites: endpoint validation,
               secret-ARN validation, query read/write enforcement,
               startup probe.

    Cells incompatible by design (e.g. RDS_API on express) are not in the
    plan. Cells that depend on a failed cluster show as skipped with the
    reason 'cluster creation failed'. Suite-level exceptions are recorded
    as failures for that suite only and do not cascade to other suites.
    """
    server.readonly_query = False

    # Start the run under 'off'. Bootstrapping (provisioning the least-privilege
    # role) connects as the master user (an rds_superuser member), which the
    # 'enforce' policy would reject. Once a least-privilege role is provisioned
    # for a cluster, its suites run under 'enforce' as that role (see
    # _apply_identity); clusters without one (e.g. serverless in the express-only
    # setup) keep connecting as master under 'off'.
    server.privilege_check_policy = server.PRIVILEGE_CHECK_OFF

    ts = datetime.now().strftime('%Y%m%d%H%M%S')
    table_suffix = ts

    results: list[TestResult] = []
    clusters_to_delete: list[str] = []
    test_security_group_id: Optional[str] = None

    # Cluster kind -> provisioned least-privilege access info (role + secret
    # ARN + connection context). Populated after cluster creation; used to pin
    # the least-privilege secret and run those suites under 'enforce'.
    lp_info_by_kind: dict = {}

    def _apply_identity(kind: str, cid: str, method: ConnectionMethod):
        """Set the connection identity + policy for a cluster's suite.

        Pins the least-privilege secret appropriate for ``method`` (IAM role for
        PG_WIRE_IAM, password role for PG_WIRE_PROTOCOL / RDS_API) and runs under
        'enforce' (production-like). Falls back to the cluster master secret
        under 'off' when no suitable least-privilege secret was provisioned.
        """
        lp = lp_info_by_kind.get(kind)
        arn = _lp_secret_for_method(lp, method) if lp else None
        if arn:
            server.configured_secret_arns[cid] = arn
            server.privilege_check_policy = server.PRIVILEGE_CHECK_ENFORCE
        else:
            configure_server_secret_for_cluster(cid, args.region)
            server.privilege_check_policy = server.PRIVILEGE_CHECK_OFF

    # Reset the IAM policy that setup_aurora_iam_policy_for_current_user
    # appends to. Without this, repeated e2e runs accumulate stale
    # cluster ARNs until the policy hits IAM's 6,144-char cap and
    # CreatePolicyVersion starts failing. We clear all entries up front;
    # cluster creation re-adds entries for the clusters this run owns.
    # Best-effort — failures are logged but don't abort the run.
    try:
        await asyncio.to_thread(gc_aurora_iam_policy, args.region)
    except Exception as e:
        logger.warning(f'gc_aurora_iam_policy raised: {e}')

    # Reap any SGs left over from earlier crashed runs.
    try:
        await asyncio.to_thread(gc_e2e_test_security_groups, args.region)
    except Exception as e:
        logger.warning(f'gc_e2e_test_security_groups raised: {e}')

    express_id = f'mcp-e2e-express-{ts}'
    serverless_id = f'mcp-e2e-serverless-{ts}'
    express_endpoint: Optional[str] = None
    serverless_endpoint: Optional[str] = None

    # --------------------------------------------------------------
    # Build the full plan up front. Each entry is a callable that
    # returns a TestResult, plus a description used for skip-record
    # placeholders if the entry can't run.
    # --------------------------------------------------------------

    def _phase2_plan():
        """Functional-suite cells derived from the resolved run plan.

        ``args.plan_by_kind`` (built in ``main()`` from --endpoint-types /
        --auth-types, validated against the capability matrix) maps each
        requested endpoint kind to its ``(method, method_name)`` cells. Every
        cell here is already known-valid, so all are enabled.
        """
        return [
            (kind, method, method_name, True)
            for kind in args.endpoint_kinds
            for method, method_name in args.plan_by_kind[kind]
        ]

    def _record(result: TestResult):
        results.append(result)

    try:
        # ==============================================================
        # Phase 1: create the express cluster (always) and the
        # serverless cluster (only with --test-serverless-cluster).
        # ==============================================================
        # Schedule cleanup BEFORE the create call. If creation succeeds
        # in AWS but a downstream step (wait_for_dns, IAM policy setup,
        # endpoint retrieval) raises, ep returns None but the cluster is
        # still alive in AWS. internal_delete_cluster handles
        # not-found gracefully, so it's safe to register cleanup eagerly.
        if 'express' not in args.endpoint_kinds:
            logger.info('Skipping express cluster creation (not in --endpoint-types).')
        else:
            clusters_to_delete.append(express_id)
            try:
                ep, res = create_cluster_as_test(
                    cluster_kind='express',
                    creator_fn=partial(
                        create_express_cluster,
                        cluster_identifier=express_id,
                        region=args.region,
                        database=args.database,
                        engine_version=args.engine_version,
                    ),
                )
                res.cluster_identifier = express_id
                _record(res)
                if ep is not None:
                    express_endpoint = ep
            except Exception as e:
                logger.exception('Express cluster phase aborted')
                _record(
                    TestResult(
                        cluster_identifier=express_id,
                        connection_method_name='create_cluster_express',
                        passed=[],
                        failed=[('create_cluster_express', f'{type(e).__name__}: {e}')],
                    )
                )

        # Provision a public-access path for the serverless cluster
        # when --test-non-express-cluster is set. The SG locks ingress
        # to a fixed set of managed prefix lists (Amazon corp/VPN
        # egress), and the cluster is configured PubliclyAccessible so
        # the writer instance gets a routable public IP. Both pieces
        # are torn down on cleanup.
        #
        # The serverless cluster is only created when
        # --test-serverless-cluster (or its implier
        # --test-non-express-cluster) is set. By default the run creates
        # the express cluster only, which is much faster.
        public_access_kwargs: dict = {}
        if not args.test_serverless_cluster:
            logger.info(
                'Skipping serverless cluster creation '
                '(--test-serverless-cluster not set; express-only run).'
            )
        else:
            if args.test_non_express_cluster:
                try:
                    vpc_id = await asyncio.to_thread(get_default_vpc_id, args.region)
                    if not vpc_id:
                        logger.error(
                            f'--test-non-express-cluster requires a default VPC in {args.region}; '
                            'none found. Skipping SG provisioning — PG Wire cases will fail.'
                        )
                    else:
                        sg_name = f'mcp-e2e-pgwire-{ts}'
                        test_security_group_id = await asyncio.to_thread(
                            create_e2e_test_security_group,
                            args.region,
                            vpc_id,
                            E2E_TEST_PREFIX_LIST_IDS,
                            sg_name,
                        )
                        public_access_kwargs = {
                            'publicly_accessible': True,
                            'vpc_security_group_ids': [test_security_group_id],
                        }
                except Exception as e:
                    logger.exception(
                        f'Failed to provision public-access SG for serverless cluster: {e}'
                    )

            # Same eager-cleanup guarantee as for the express cluster
            # above. Critical here because serverless creation routes
            # through a background thread and the public-access path adds
            # extra post-create steps (IAM policy, properties refetch)
            # that can raise after the cluster is alive in AWS.
            clusters_to_delete.append(serverless_id)
            try:
                ep, res = create_cluster_as_test(
                    cluster_kind='serverless',
                    creator_fn=partial(
                        create_serverless_cluster_and_wait,
                        cluster_identifier=serverless_id,
                        region=args.region,
                        database=args.database,
                        engine_version=args.engine_version,
                        # Enable IAM DB auth only when a serverless PG-Wire IAM
                        # cell is planned; otherwise the cluster (RDS_API-only)
                        # doesn't need it. Keeps the capability off unless used.
                        enable_iam_auth=args.serverless_pgwire,
                        **public_access_kwargs,
                    ),
                )
                res.cluster_identifier = serverless_id
                _record(res)
                if ep is not None:
                    serverless_endpoint = ep
            except Exception as e:
                logger.exception('Serverless cluster phase aborted')
                _record(
                    TestResult(
                        cluster_identifier=serverless_id,
                        connection_method_name='create_cluster_serverless',
                        passed=[],
                        failed=[('create_cluster_serverless', f'{type(e).__name__}: {e}')],
                    )
                )

        # Map cluster kind → endpoint, used by phases 2 and 3.
        endpoints = {'express': express_endpoint, 'serverless': serverless_endpoint}
        cluster_ids = {'express': express_id, 'serverless': serverless_id}

        # Provision least-privilege role(s) for the EXPRESS cluster so the
        # functional and security suites authenticate as a non-superuser role
        # under the 'enforce' policy (set by _apply_identity; mirroring the
        # recommended production setup). Provisioning runs under 'off' (it
        # connects as master to run DDL). On failure the affected suites degrade
        # to the master/off path and the failure is recorded. (Serverless is
        # provisioned the same way below.)
        def _role_needs(kind: str) -> tuple[bool, bool]:
            """(need_iam_role, need_pw_role) for a kind, from its resolved plan."""
            methods = {m for m, _ in args.plan_by_kind.get(kind, [])}
            need_iam = ConnectionMethod.PG_WIRE_IAM_PROTOCOL in methods
            need_pw = bool(methods & {ConnectionMethod.PG_WIRE_PROTOCOL, ConnectionMethod.RDS_API})
            return need_iam, need_pw

        if endpoints['express'] is not None:
            try:
                exp_iam, exp_pw = _role_needs('express')
                lp_info_by_kind['express'] = await provision_least_privilege_access(
                    cluster_identifier=cluster_ids['express'],
                    region=args.region,
                    valid_endpoint=endpoints['express'],
                    port=args.port,
                    connection_method=ConnectionMethod.PG_WIRE_IAM_PROTOCOL,
                    database='postgres',
                    need_iam_role=exp_iam,
                    need_pw_role=exp_pw,
                )
            except Exception as e:
                logger.error(f'least-privilege provisioning failed for express: {e}')
                _record(
                    TestResult(
                        cluster_identifier=cluster_ids['express'],
                        connection_method_name='least_privilege_provisioning_express',
                        passed=[],
                        failed=[('provision_least_privilege_access', f'{type(e).__name__}: {e}')],
                    )
                )

        # Provision least-privilege role(s) for the SERVERLESS cluster too
        # (only present when --test-serverless-cluster is set). We connect-as-
        # master over RDS_API — a public HTTPS endpoint that needs no VPC
        # reachability and is always available for serverless — to run the
        # provisioning DDL. Which roles are created depends on the requested
        # methods (_role_needs): an rds_iam role for PG_WIRE_IAM cells and/or a
        # password role for PG_WIRE_PROTOCOL / RDS_API cells. _apply_identity
        # then pins the right role's secret per connection method under the
        # 'enforce' policy.
        if endpoints['serverless'] is not None:
            try:
                sl_iam, sl_pw = _role_needs('serverless')
                lp_info_by_kind['serverless'] = await provision_least_privilege_access(
                    cluster_identifier=cluster_ids['serverless'],
                    region=args.region,
                    valid_endpoint=endpoints['serverless'],
                    port=args.port,
                    connection_method=ConnectionMethod.RDS_API,
                    database='postgres',
                    need_iam_role=sl_iam,
                    need_pw_role=sl_pw,
                )
            except Exception as e:
                logger.error(f'least-privilege provisioning failed for serverless: {e}')
                _record(
                    TestResult(
                        cluster_identifier=cluster_ids['serverless'],
                        connection_method_name='least_privilege_provisioning_serverless',
                        passed=[],
                        failed=[('provision_least_privilege_access', f'{type(e).__name__}: {e}')],
                    )
                )

        # ==============================================================
        # Phase 2: functional SQL suite per compatible cell.
        # ==============================================================
        for kind, method, method_name, enabled in _phase2_plan():
            if not enabled:
                # Operator opted out (e.g. --test-non-express-cluster not
                # set, so PG Wire methods on the regular cluster are gated).
                # Don't add to results — it wasn't planned for this run.
                continue

            cid = cluster_ids[kind]
            phase_label = f'functional_{kind}_{method_name}'

            endpoint = endpoints[kind]
            if endpoint is None:
                _record(skipped_result(cid, phase_label, f'{kind} cluster creation failed'))
                continue

            try:
                _apply_identity(kind, cid, method)
                config = ClusterConfig(
                    cluster_identifier=cid,
                    region=args.region,
                    database=args.database,
                    connection_method=method,
                    db_endpoint=endpoint,
                    port=args.port,
                    connection_method_name=method_name,
                    cluster_type=kind,
                )
                _record(await run_test_suite(config, f'{table_suffix}_{kind}_{method_name}'))
            except Exception as e:
                logger.exception(f'{phase_label} aborted unexpectedly')
                _record(
                    TestResult(
                        cluster_identifier=cid,
                        connection_method_name=phase_label,
                        passed=[],
                        failed=[(phase_label, f'{type(e).__name__}: {e}')],
                    )
                )

        # ==============================================================
        # Phase 3: security/invariant suites, per cluster.
        # Suites per cluster: endpoint validation, secret-ARN
        # validation, query read/write enforcement, startup probe.
        # The serverless cluster is only present when
        # --test-serverless-cluster is set; otherwise this is an
        # express-only run and serverless suites are not planned.
        # ==============================================================
        phase3_kinds = list(args.endpoint_kinds)

        # Suite names planned per cluster, used to emit skip placeholders
        # when a cluster's endpoint is unavailable (creation failed).
        phase3_suite_names = (
            'endpoint_validation',
            'secret_arn_validation',
            'query_enforcement',
            'tls_enforcement',
            'privilege_enforcement',
            'startup_secret_arn_validation',
        )
        for kind in phase3_kinds:
            cid = cluster_ids[kind]
            endpoint = endpoints[kind]

            # Guard up front so the rest of the loop body sees a non-None
            # endpoint (also lets the runner lambdas below close over a
            # narrowed `str`). If creation failed, record every planned
            # suite as skipped rather than silently dropping them.
            if endpoint is None:
                for suite_name in phase3_suite_names:
                    _record(
                        skipped_result(
                            cid, f'{suite_name}_{kind}', f'{kind} cluster creation failed'
                        )
                    )
                continue

            valid_endpoint: str = endpoint

            # query/tls enforcement run under one method per kind: prefer a
            # PG-Wire method (IAM first) so the TLS suite actually exercises TLS
            # (RDS_API has no sslmode and self-skips). Falls back to the first
            # planned cell (e.g. RDS_API when only the Data API was requested).
            kind_cells = args.plan_by_kind[kind]
            enforce_method, enforce_method_name = next(
                ((m, n) for m, n in kind_cells if m in _PGWIRE_METHODS),
                kind_cells[0],
            )

            # The privilege suite connects as the MASTER superuser (which is not
            # granted rds_iam under the two-role model) and as the lp role. It
            # therefore must use a method the master supports: on express that
            # is PG_WIRE_IAM (express manages the master's IAM auth); on
            # serverless that is RDS_API (Data API is always available and works
            # for the master without rds_iam). This is independent of the
            # requested --auth-types.
            if kind == 'express':
                priv_method, priv_method_name = (
                    ConnectionMethod.PG_WIRE_IAM_PROTOCOL,
                    'PG_WIRE_IAM_PROTOCOL',
                )
            else:
                priv_method, priv_method_name = ConnectionMethod.RDS_API, 'RDS_API'

            # endpoint_validation connects via express->PG_WIRE_IAM,
            # serverless->RDS_API (its own internal logic); pin the matching
            # identity so its positive case authenticates correctly.
            endpoint_method = (
                ConnectionMethod.PG_WIRE_IAM_PROTOCOL
                if kind == 'express'
                else ConnectionMethod.RDS_API
            )

            # Each entry: (suite_name, runner_coro_factory). Every runner
            # is an async callable returning Awaitable[TestResult] so the
            # dispatch below can uniformly `await` it. The two synchronous
            # suites are wrapped in async shims.
            async def _run_endpoint_validation(c=cid, e=valid_endpoint, k=kind):
                return run_endpoint_validation_suite(
                    cluster_identifier=c,
                    region=args.region,
                    database=args.database,
                    valid_endpoint=e,
                    port=args.port,
                    cluster_kind=k,
                )

            async def _run_secret_arn_validation(c=cid, e=valid_endpoint, k=kind):
                return await run_secret_arn_validation_suite(
                    cluster_identifier=c,
                    region=args.region,
                    database=args.database,
                    valid_endpoint=e,
                    port=args.port,
                    cluster_kind=k,
                    test_non_express_cluster=args.test_non_express_cluster,
                    lp_iam_secret_arn=(lp_info_by_kind.get(k) or {}).get('secret_arn_iam'),
                )

            async def _run_query_enforcement(
                c=cid,
                e=valid_endpoint,
                k=kind,
                m=enforce_method,
                mn=enforce_method_name,
            ):
                return await run_query_enforcement_suite(
                    cluster_identifier=c,
                    region=args.region,
                    database=args.database,
                    valid_endpoint=e,
                    port=args.port,
                    cluster_kind=k,
                    connection_method=m,
                    connection_method_name=mn,
                )

            async def _run_tls_enforcement(
                c=cid,
                e=valid_endpoint,
                k=kind,
                m=enforce_method,
                mn=enforce_method_name,
            ):
                return await run_tls_enforcement_suite(
                    cluster_identifier=c,
                    region=args.region,
                    database=args.database,
                    valid_endpoint=e,
                    port=args.port,
                    cluster_kind=k,
                    connection_method=m,
                    connection_method_name=mn,
                )

            async def _run_privilege_enforcement(
                c=cid,
                e=valid_endpoint,
                k=kind,
                m=priv_method,
                mn=priv_method_name,
            ):
                return await run_privilege_enforcement_suite(
                    cluster_identifier=c,
                    region=args.region,
                    valid_endpoint=e,
                    port=args.port,
                    cluster_kind=k,
                    connection_method=m,
                    connection_method_name=mn,
                    lp_secret_arn=_lp_secret_for_method(lp_info_by_kind.get(k), m),
                )

            async def _run_startup_secret_arn_validation(c=cid):
                return run_startup_secret_arn_validation_suite(
                    cluster_identifier=c,
                    region=args.region,
                )

            # Each entry pairs a suite with the connection method it will use,
            # so _apply_identity pins the matching least-privilege secret (IAM
            # role for PG_WIRE_IAM, password role for PG_WIRE_PROTOCOL/RDS_API).
            for suite_name, runner, suite_method in (
                ('endpoint_validation', _run_endpoint_validation, endpoint_method),
                ('secret_arn_validation', _run_secret_arn_validation, enforce_method),
                ('query_enforcement', _run_query_enforcement, enforce_method),
                ('tls_enforcement', _run_tls_enforcement, enforce_method),
                ('privilege_enforcement', _run_privilege_enforcement, priv_method),
                ('startup_secret_arn_validation', _run_startup_secret_arn_validation, priv_method),
            ):
                phase_label = f'{suite_name}_{kind}'

                try:
                    _apply_identity(kind, cid, suite_method)
                    # secret_arn_validation exercises the master-secret fallback
                    # and bogus ARNs, so it must run as master under 'off'
                    # regardless of whether a least-privilege role exists.
                    if suite_name == 'secret_arn_validation':
                        configure_server_secret_for_cluster(cid, args.region)
                        server.privilege_check_policy = server.PRIVILEGE_CHECK_OFF
                    _record(await runner())
                except Exception as e:
                    logger.exception(f'{phase_label} aborted unexpectedly')
                    _record(
                        TestResult(
                            cluster_identifier=cid,
                            connection_method_name=phase_label,
                            passed=[],
                            failed=[(phase_label, f'{type(e).__name__}: {e}')],
                        )
                    )

    except Exception as e:
        logger.error(f'Test orchestration failed at top level: {e}')
        import traceback

        traceback.print_exc()
        # Surface the orchestration failure as a recorded TestResult so
        # print_summary doesn't lie about overall pass/fail and the exit
        # code is non-zero.
        _record(
            TestResult(
                cluster_identifier='<orchestration>',
                connection_method_name='main_async',
                passed=[],
                failed=[('orchestration_error', f'{type(e).__name__}: {e}')],
            )
        )

    # Print summary before cleanup
    all_passed = print_summary(results)

    # --keep-clusters: leave everything standing so an operator can manually
    # troubleshoot (e.g. PG-Wire reachability to the serverless cluster).
    # Skips cluster deletion, SG deletion, and least-privilege deprovision, and
    # prints the connection + network details plus manual-cleanup commands.
    if getattr(args, 'keep_clusters', False):
        bar = '=' * 70
        logger.warning(bar)
        logger.warning(
            '--keep-clusters set: NOT deleting clusters, the test security group, '
            'or least-privilege secrets/IAM policies. Clean these up manually when '
            'done (they otherwise leak and the next run only GCs the SG).'
        )
        for cid in clusters_to_delete:
            logger.warning(f'  cluster (kept): {cid}')
        if test_security_group_id:
            logger.warning(f'  test security group (kept): {test_security_group_id}')
        for kind, lp in lp_info_by_kind.items():
            logger.warning(
                f'  [{kind}] endpoint={lp.get("endpoint")} '
                f'iam_role={lp.get("role_iam")} iam_secret={lp.get("secret_arn_iam")} '
                f'pw_role={lp.get("role_pw")} pw_secret={lp.get("secret_arn_pw")}'
            )
        logger.warning('Troubleshoot reachability from this host, e.g.:')
        logger.warning('  nc -vz <endpoint> 5432')
        logger.warning('  openssl s_client -starttls postgres -connect <endpoint>:5432')
        logger.warning('Inspect the serverless cluster network config (compare with a')
        logger.warning('cluster you CAN reach):')
        logger.warning(
            f'  aws rds describe-db-instances --region {args.region} '
            "--query \"DBInstances[?contains(DBInstanceIdentifier,'mcp-e2e')]."
            '[DBInstanceIdentifier,PubliclyAccessible,DBSubnetGroup.DBSubnetGroupName,'
            'VpcSecurityGroups,Endpoint.Address]"'
        )
        if test_security_group_id:
            logger.warning(
                f'  aws ec2 describe-security-groups --region {args.region} '
                f'--group-ids {test_security_group_id}'
            )
        logger.warning('Manual cleanup when finished:')
        for cid in clusters_to_delete:
            logger.warning(
                f'  # delete instances then cluster for {cid} (see internal_delete_cluster), '
                'plus its lp secret + AuroraIAMAuth-<role> IAM policy'
            )
        if test_security_group_id:
            logger.warning(
                f'  aws ec2 delete-security-group --region {args.region} '
                f'--group-id {test_security_group_id}   # after the cluster ENIs release'
            )
        logger.warning(bar)
        sys.exit(0 if all_passed else 1)

    # Tear down provisioned least-privilege roles/secrets before dropping the
    # clusters they live on. Best-effort — failures are logged, not fatal.
    for kind, lp in list(lp_info_by_kind.items()):
        try:
            await deprovision_least_privilege_access(lp, args.region)
        except Exception as e:
            logger.warning(f'least-privilege deprovision failed for {kind}: {e}')

    # Cleanup clusters. Every assertion is already recorded by this point, so the
    # default is to hand teardown to a detached child and return; --wait-for-cleanup
    # keeps the old blocking behavior.
    if args.wait_for_cleanup:
        logger.info('Cleaning up clusters (waiting for deletion to complete)...')

        async def delete_cluster_safe(cluster_id: str):
            """Delete a cluster, logging errors instead of raising."""
            try:
                logger.info(f'Deleting cluster: {cluster_id}')
                await asyncio.to_thread(internal_delete_cluster, args.region, cluster_id)
                logger.success(f'Deleted cluster: {cluster_id}')
            except Exception as e:
                logger.warning(f'Failed to delete {cluster_id}: {e}')

        await asyncio.gather(*[delete_cluster_safe(cid) for cid in clusters_to_delete])
    else:
        logger.info('Starting cluster teardown in the background (fire and forget)...')
        detached: List[Tuple[str, int, str]] = []
        for cid in clusters_to_delete:
            spawned = spawn_detached_cluster_deletion(args.region, cid)
            if spawned is None:
                # Could not detach: fall back to deleting inline rather than
                # leaking the cluster silently.
                logger.warning(f'Falling back to blocking teardown for {cid}')
                try:
                    await asyncio.to_thread(internal_delete_cluster, args.region, cid)
                    logger.success(f'Deleted cluster: {cid}')
                except Exception as e:
                    logger.warning(f'Failed to delete {cid}: {e}')
                continue
            pid, log_path = spawned
            detached.append((cid, pid, log_path))
            logger.info(f'Teardown of {cid} running detached as pid {pid}, log: {log_path}')

        if detached:
            logger.warning(
                'Cluster teardown is still running after this process exits. '
                'Instances and clusters are deleted in that order and can take '
                'up to ~20 minutes each. Verify with:'
            )
            for cid, pid, log_path in detached:
                logger.warning(f'  tail -f {log_path}    # pid {pid}')
            logger.warning(
                f'  aws rds describe-db-clusters --region {args.region} '
                '--query "DBClusters[?Tags]|[].DBClusterIdentifier"'
            )
            logger.warning(
                'If a teardown process is killed before it finishes, the cluster '
                'leaks and must be deleted by hand. Use --wait-for-cleanup when '
                'the resources must be gone before this process exits.'
            )

    # Best-effort SG cleanup. If the cluster's ENI hasn't been released
    # yet, this fails with DependencyViolation; gc_e2e_test_security_groups
    # at the next run reaps it. Detached teardown makes that the normal case
    # rather than the exception, since the cluster is still alive here.
    if test_security_group_id:
        try:
            await asyncio.to_thread(
                delete_e2e_test_security_group, args.region, test_security_group_id
            )
        except Exception as e:
            if args.wait_for_cleanup:
                logger.warning(f'SG cleanup raised: {e}')
            else:
                logger.info(
                    f'SG {test_security_group_id} still in use by the cluster being torn '
                    f'down; the next run garbage-collects it ({type(e).__name__})'
                )

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
        '--log-level',
        choices=('TRACE', 'DEBUG', 'INFO', 'SUCCESS', 'WARNING', 'ERROR', 'CRITICAL'),
        default='INFO',
        help=(
            'loguru log level for the e2e run. Default INFO. Use DEBUG to see '
            'cluster property dumps and other verbose internals.'
        ),
    )
    parser.add_argument(
        '--test-serverless-cluster',
        action='store_true',
        default=False,
        help=(
            'Also create and test a regular Aurora Serverless v2 cluster. '
            'OFF by default because serverless cluster + instance creation '
            'adds roughly 7-8 minutes to the run (instance provisioning). '
            'When off, only the express cluster is created and tested. '
            'Implied by --test-non-express-cluster. With this flag (and '
            'without --test-non-express-cluster) the serverless cluster is '
            'tested via RDS_API only (public HTTPS, no VPC reachability '
            'needed).'
        ),
    )
    parser.add_argument(
        '--test-non-express-cluster',
        action='store_true',
        default=False,
        help=(
            'Test PG_WIRE_IAM_PROTOCOL and PG_WIRE_PROTOCOL against the regular '
            '(serverless / non-express) cluster. The regular cluster lives in a '
            'VPC subnet group and is reachable on TCP 5432 only from inside the '
            'VPC; this flag asserts the host running the test has VPC '
            'reachability (direct, peering, VPN, or SSH tunnel). The express '
            'cluster is publicly reachable by default and its PG_WIRE_IAM_PROTOCOL '
            'cell always runs regardless of this flag. RDS_API is a public HTTPS '
            'endpoint and is unaffected. Implies --test-serverless-cluster '
            '(the serverless cluster must exist to be PG-Wire-tested). '
            'Legacy flag; prefer --endpoint-types / --auth-types.'
        ),
    )
    parser.add_argument(
        '--endpoint-types',
        default=None,
        help=(
            'Comma-separated endpoint types to provision and test: '
            f'{",".join(SUPPORTED_ENDPOINT_TYPES)} '
            '(rds-instance not yet supported). When omitted, falls back to the '
            'legacy --test-serverless-cluster / --test-non-express-cluster flags '
            '(default: express only). The wrapper script passes '
            "'express,serverless' to enumerate all Aurora endpoints."
        ),
    )
    parser.add_argument(
        '--keep-clusters',
        action='store_true',
        default=False,
        help=(
            'Do not tear down created clusters, the test security group, or the '
            'least-privilege secrets/IAM policies at the end of the run. Use this '
            'to manually troubleshoot a failure (e.g. PG-Wire reachability to the '
            'serverless cluster). The endpoints, SG id, and manual-cleanup steps '
            'are printed at the end. Remember to delete these resources yourself.'
        ),
    )
    parser.add_argument(
        '--auth-types',
        default=None,
        help=(
            'Comma-separated auth methods to include, filtered by each endpoint '
            f"type's supported set: {','.join(ALL_AUTH_TYPES)}. Default (when "
            '--endpoint-types is given) is all supported. An endpoint/auth '
            'combination the platform cannot do (e.g. express + rds_api) is '
            'rejected with an error.'
        ),
    )
    parser.add_argument(
        '--wait-for-cleanup',
        action='store_true',
        default=False,
        help=(
            'Block until created clusters are fully deleted before exiting. By '
            'default teardown is handed to a detached background process and this '
            'one returns immediately, which removes up to ~20 minutes of instance '
            'and cluster deletion polling from the run. Use this flag when the '
            'resources must be provably gone before the process exits (for example '
            'in CI that tears down the host straight after), since a detached '
            'teardown killed mid-flight leaks the cluster.'
        ),
    )
    parser.add_argument(
        '--full-policy-corpus',
        action='store_true',
        default=False,
        help=(
            'Drive the entire unit-level policy matrix (tests/test_policy_matrix.py, '
            '~515 statements x 2 modes) through run_query instead of the curated '
            'subset, making this suite a strict superset of the unit policy tests. '
            'Each cell asserts the policy decision reached through the real tool and '
            'tolerates a database error, since much of the unit corpus references '
            'objects that intentionally do not exist. Adds roughly a thousand round '
            'trips per connection method, so it is off by default; use it when '
            'changing the guard or its corpora.'
        ),
    )
    args = parser.parse_args()

    # Full sweep needs the unit matrix importable; fail fast rather than
    # silently running the curated subset when the operator asked for the sweep.
    if args.full_policy_corpus:
        if not POLICY_MATRIX_AVAILABLE:
            parser.error(
                '--full-policy-corpus requires tests/test_policy_matrix.py to be '
                f'importable, but importing it failed: {_MATRIX_IMPORT_ERROR!r}'
            )
        global FULL_POLICY_CORPUS
        FULL_POLICY_CORPUS = True
        logger.info(
            f'--full-policy-corpus: driving {len(SET_1_READS)} reads, '
            f'{len(SET_2_WRITES)} writes, {len(SET_3_DANGEROUS)} dangerous and '
            f'{len(SET_4_FAIL_CLOSED)} fail-closed statements through run_query in both modes'
        )

    # --test-non-express-cluster only makes sense if the serverless
    # cluster is actually created, so it implies --test-serverless-cluster.
    if args.test_non_express_cluster:
        args.test_serverless_cluster = True

    # Resolve the endpoint x auth run plan. Two paths:
    #  * New interface (--endpoint-types and/or --auth-types given): build the
    #    plan from the capability matrix, blocking invalid combinations.
    #  * Legacy interface (neither given): reproduce the historical behavior
    #    exactly from --test-serverless-cluster / --test-non-express-cluster.
    if args.endpoint_types is None and args.auth_types is None:
        endpoint_kinds = ['express']
        plan_by_kind = {'express': [AUTH_TYPE_TO_METHOD['pg_wire_iam']]}
        if args.test_serverless_cluster:
            endpoint_kinds.append('serverless')
            serverless_cells = [AUTH_TYPE_TO_METHOD['rds_api']]
            if args.test_non_express_cluster:
                serverless_cells.append(AUTH_TYPE_TO_METHOD['pg_wire_iam'])
                serverless_cells.append(AUTH_TYPE_TO_METHOD['pg_wire_secret'])
            plan_by_kind['serverless'] = serverless_cells
        serverless_pgwire = args.test_non_express_cluster
    else:
        endpoint_types: List[str] = (
            _split_csv(args.endpoint_types)
            if args.endpoint_types
            else list(SUPPORTED_ENDPOINT_TYPES)
        )
        auth_types: List[str] = (
            _split_csv(args.auth_types) if args.auth_types else list(ALL_AUTH_TYPES)
        )
        try:
            endpoint_kinds, plan_by_kind, serverless_pgwire = resolve_run_plan(
                endpoint_types, auth_types
            )
        except ValueError as e:
            parser.error(str(e))

    # Stash the resolved plan; also derive the legacy booleans main_async still
    # reads so the rest of the orchestration needs no change.
    args.endpoint_kinds = endpoint_kinds
    args.plan_by_kind = plan_by_kind
    args.serverless_pgwire = serverless_pgwire
    args.test_serverless_cluster = 'serverless' in endpoint_kinds
    args.test_non_express_cluster = serverless_pgwire

    # Replace loguru's default sink with one at the requested level. This
    # filters everything (including the postgres-mcp-server modules' own
    # logger calls) so DEBUG-level cluster property dumps stay out of the
    # log unless the operator explicitly opts in.
    logger.remove()
    logger.add(sys.stderr, level=args.log_level)

    asyncio.run(main_async(args))


if __name__ == '__main__':
    main()
