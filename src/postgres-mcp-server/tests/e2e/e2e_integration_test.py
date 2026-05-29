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

Usage:
    # Default: express-only, fast
    python tests/e2e_integration_test.py --region us-east-1 --engine-version 16.4

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
    internal_create_connection,
    is_database_connected,
    run_query,
)
from dataclasses import dataclass
from datetime import datetime
from functools import partial
from loguru import logger
from typing import List, Optional


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
    skipped: Optional[list] = None  # list of (step_name, reason) tuples; None == empty

    def __post_init__(self):
        """Default skipped to an empty list."""
        if self.skipped is None:
            self.skipped = []

    @property
    def success(self) -> bool:
        """Return True if all test steps passed.

        Skipped steps count as not-pass so that 'cluster creation failed'
        cascades into a non-zero exit code.
        """
        return len(self.failed) == 0 and len(self.skipped or []) == 0


def log_step(step: str, status: str, detail: str = ''):
    """Log a test step with a status marker (PASS, FAIL, SKIP, INFO)."""
    msg = f'  [{status}] {step}'
    if detail:
        msg += f': {detail}'
    if status == 'PASS':
        logger.success(msg)
    elif status == 'FAIL':
        logger.error(msg)
    elif status == 'SKIP':
        logger.warning(msg)
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
    publicly_accessible: bool = False,
    vpc_security_group_ids: Optional[list] = None,
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
        ts_str = name[len(name_prefix):]
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
            logger.warning(
                f'gc_e2e_test_security_groups: could not delete {name} ({sg_id}): {e}'
            )

    if deleted or skipped:
        logger.info(
            f'gc_e2e_test_security_groups: deleted {deleted}, skipped {skipped}'
        )


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
        except Exception:
            pass
        raise

    logger.info(
        f'created test SG {sg_name} ({sg_id}) authorizing {", ".join(prefix_list_ids)} '
        'on tcp:5432'
    )
    return sg_id


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
        'Statement': [
            {'Effect': 'Allow', 'Action': 'rds-db:connect', 'Resource': [sentinel]}
        ],
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
            db_for_method = (
                pg_wire_database if cluster_kind == 'express' else database
            )
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
            record(step, True, 'skipped: RDS_API not supported on express cluster')
            # Record as passed skip rather than failed skip — this is a
            # by-design incompatibility, not a bug.
            # (Recording via record() with ok=True adds to passed.)
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
            record(step, True, 'skipped: PG_WIRE_PROTOCOL not supported on express cluster')
        elif not test_non_express_cluster:
            record(
                step,
                True,
                'skipped: --test-non-express-cluster not set (PG_WIRE_PROTOCOL '
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
            record(
                step,
                True,
                'skipped: --test-non-express-cluster not set (PG_WIRE_IAM_PROTOCOL '
                'on serverless requires VPC reachability)',
            )
        else:
            try:
                reset_to_real_secret()
                clear_cached_connection(
                    ConnectionMethod.PG_WIRE_IAM_PROTOCOL, pg_wire_database
                )
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
            record(
                step,
                True,
                'skipped: --test-non-express-cluster not set (serverless variant '
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
            record(step, True, 'skipped: RDS_API not supported on express cluster')
        else:
            try:
                reset_to_real_secret()
                clear_cached_connection(ConnectionMethod.RDS_API)

                # Return the real cluster properties with the MasterUserSecret
                # rewritten to an ARN the caller has no access to. The
                # configured (real) ARN must win, so SELECT 1 still works.
                tampered_props = dict(cluster_props)
                tampered_props['MasterUserSecret'] = {
                    'SecretArn': 'arn:aws:secretsmanager:us-east-1:000000000000:secret:attacker-owned-MNOPQR',
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
            record(
                step,
                True,
                'skipped: cluster has no managed secret (IAM-only express cluster)',
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
# These mirror the positive-path unit tests in
# tests/test_mutable_sql_detector.py but exercise the full run_query
# path against a real cluster.
ALLOWED_READ_QUERIES = [
    'SELECT 1',
    'SELECT version()',
    "SELECT 'hello' AS greeting",
    'SELECT count(*) FROM pg_class',
    'SELECT id FROM (SELECT 1 AS id) sub WHERE id = 1',
]

# Queries that MUST be blocked in read-only mode (mutating keywords).
# Each is a real statement an LLM might emit; run_query should reject it
# before it reaches the database when readonly is on.
READONLY_BLOCKED_QUERIES = [
    'INSERT INTO t (a) VALUES (1)',
    'UPDATE t SET a = 1 WHERE id = 2',
    'DELETE FROM t WHERE id = 1',
    'CREATE TABLE t (id int)',
    'ALTER TABLE t ADD COLUMN c int',
    'TRUNCATE TABLE t',
    'SET search_path TO public, attacker_schema',
    'RESET ALL',
    'DISCARD ALL',
    "LOAD 'auto_explain'",
    'DO $$ BEGIN PERFORM 1; END $$',
    'GRANT SELECT ON t TO bob',
]

# Queries that MUST be blocked in BOTH read-only and write mode because
# they go through check_sql_injection_risk (dangerous functions and
# security-sensitive GUCs), which runs regardless of the readonly flag.
ALWAYS_BLOCKED_QUERIES = [
    'SELECT pg_terminate_backend(99999)',
    'SELECT pg_cancel_backend(99999)',
    'SELECT pg_sleep(30)',
    "SELECT pg_read_file('/etc/passwd')",
    'SELECT pg_advisory_lock(42)',
    'SELECT pg_advisory_xact_lock(42)',
    "SELECT pg_notify('ch', 'x')",
    'SET row_security = off',
    'SET session_replication_role = replica',
]


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

    Assertions, all driven through the real ``run_query`` tool:
      readonly = True  (server started WITHOUT --allow_write_query):
        - ALLOWED_READ_QUERIES succeed
        - READONLY_BLOCKED_QUERIES are rejected (mutating keywords)
        - ALWAYS_BLOCKED_QUERIES are rejected (injection-risk check)
      readonly = False (server started WITH --allow_write_query):
        - ALLOWED_READ_QUERIES succeed
        - READONLY_BLOCKED_QUERIES are now allowed past the readonly
          guard (they may still error at the database for unrelated
          reasons like a missing table — we only assert they are not
          rejected by the MCP's readonly guard)
        - ALWAYS_BLOCKED_QUERIES are STILL rejected (mode-independent)
    """
    ctx = DummyCtx()
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

    def _is_rejected(rows) -> bool:
        """run_query returns [{'error': ...}] when it rejects/fails a query."""
        return bool(rows) and isinstance(rows[0], dict) and 'error' in rows[0]

    def _is_readonly_rejection(rows) -> bool:
        """Distinguish the readonly-guard rejection from other errors.

        run_query returns the write_query_prohibited_key message when the
        mutating-keyword guard fires. Other errors (injection risk,
        database errors) use different keys.
        """
        if not _is_rejected(rows):
            return False
        return rows[0]['error'] == server.write_query_prohibited_key

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

    async def _run(sql):
        return await run_query(
            sql=sql,
            ctx=ctx,
            connection_method=connection_method,
            cluster_identifier=cluster_identifier,
            db_endpoint=valid_endpoint,
            database=test_database,
        )

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

        for sql in ALLOWED_READ_QUERIES:
            step = f'readonly:allow {sql[:48]}'
            try:
                rows = await _run(sql)
                record(step, not _is_rejected(rows), str(rows)[:120])
            except Exception as e:
                record(step, False, f'{type(e).__name__}: {e}')

        for sql in READONLY_BLOCKED_QUERIES:
            step = f'readonly:block {sql[:48]}'
            try:
                rows = await _run(sql)
                # Must be rejected by the readonly mutating-keyword guard.
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
                # In write mode the readonly guard must NOT fire. The
                # query may still error at the DB (e.g. table 't' doesn't
                # exist), but it must not be rejected with the
                # write-prohibited key.
                record(step, not _is_readonly_rejection(rows), str(rows)[:120])
            except Exception as e:
                record(step, False, f'{type(e).__name__}: {e}')

        for sql in ALWAYS_BLOCKED_QUERIES:
            step = f'write:always-block {sql[:48]}'
            try:
                rows = await _run(sql)
                # These go through check_sql_injection_risk which is
                # mode-independent, so they must STILL be rejected.
                record(step, _is_rejected(rows), str(rows)[:120])
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
        except Exception:
            pass

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
    for r in results:
        if r.failed:
            status = 'FAILED'
        elif r.skipped:
            status = 'SKIPPED'
        else:
            status = 'PASSED'
        logger.info(f'\n  {r.connection_method_name} ({r.cluster_identifier}): {status}')
        for s in r.passed:
            logger.info(f'    [PASS] {s}')
            total_pass += 1
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
    logger.info(f'Totals: {total_pass} passed, {total_fail} failed, {total_skip} skipped')
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

    ts = datetime.now().strftime('%Y%m%d%H%M%S')
    table_suffix = ts

    results: list[TestResult] = []
    clusters_to_delete: list[str] = []
    test_security_group_id: Optional[str] = None

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
        """Compatibility matrix as a list of (kind, method, method_name, enabled).

        Express clusters are reachable from anywhere by default (no VPC
        security group restriction), so the express + PG_WIRE_IAM_PROTOCOL
        cell runs unconditionally. The regular (serverless) cluster is
        only created when --test-serverless-cluster is set, so all its
        cells are gated on that flag. Its PG Wire cells additionally
        require --test-non-express-cluster to indicate the host running
        this test can reach the cluster on TCP 5432. RDS_API is a public
        HTTPS endpoint and works whenever the serverless cluster exists.
        """
        return [
            ('express', ConnectionMethod.PG_WIRE_IAM_PROTOCOL, 'PG_WIRE_IAM_PROTOCOL', True),
            (
                'serverless',
                ConnectionMethod.RDS_API,
                'RDS_API',
                args.test_serverless_cluster,
            ),
            (
                'serverless',
                ConnectionMethod.PG_WIRE_IAM_PROTOCOL,
                'PG_WIRE_IAM_PROTOCOL',
                args.test_non_express_cluster,
            ),
            (
                'serverless',
                ConnectionMethod.PG_WIRE_PROTOCOL,
                'PG_WIRE_PROTOCOL',
                args.test_non_express_cluster,
            ),
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
                configure_server_secret_for_cluster(cid, args.region)
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
        phase3_kinds = ['express']
        if args.test_serverless_cluster:
            phase3_kinds.append('serverless')
        for kind in phase3_kinds:
            cid = cluster_ids[kind]
            endpoint = endpoints[kind]

            # The query-enforcement suite needs a connection method that
            # actually works against this cluster kind from the test
            # host. Express is publicly reachable via PG_WIRE_IAM.
            # Serverless uses RDS_API (public HTTPS) by default; only
            # use a PG Wire method against serverless when
            # --test-non-express-cluster confirms VPC reachability.
            if kind == 'express':
                enforce_method = ConnectionMethod.PG_WIRE_IAM_PROTOCOL
                enforce_method_name = 'PG_WIRE_IAM_PROTOCOL'
            else:
                enforce_method = ConnectionMethod.RDS_API
                enforce_method_name = 'RDS_API'

            # Each entry: (suite_name, is_async_runner, runner_fn).
            # Most suites are sync; run_secret_arn_validation_suite issues
            # SQL via run_query which is a coroutine, so it must be awaited.
            for suite_name, is_async, runner in (
                (
                    'endpoint_validation',
                    False,
                    lambda c=cid, e=endpoint, k=kind: run_endpoint_validation_suite(
                        cluster_identifier=c,
                        region=args.region,
                        database=args.database,
                        valid_endpoint=e,
                        port=args.port,
                        cluster_kind=k,
                    ),
                ),
                (
                    'secret_arn_validation',
                    True,
                    lambda c=cid, e=endpoint, k=kind: run_secret_arn_validation_suite(
                        cluster_identifier=c,
                        region=args.region,
                        database=args.database,
                        valid_endpoint=e,
                        port=args.port,
                        cluster_kind=k,
                        test_non_express_cluster=args.test_non_express_cluster,
                    ),
                ),
                (
                    'query_enforcement',
                    True,
                    lambda c=cid,
                    e=endpoint,
                    k=kind,
                    m=enforce_method,
                    mn=enforce_method_name: run_query_enforcement_suite(
                        cluster_identifier=c,
                        region=args.region,
                        database=args.database,
                        valid_endpoint=e,
                        port=args.port,
                        cluster_kind=k,
                        connection_method=m,
                        connection_method_name=mn,
                    ),
                ),
                (
                    'startup_secret_arn_validation',
                    False,
                    lambda c=cid: run_startup_secret_arn_validation_suite(
                        cluster_identifier=c,
                        region=args.region,
                    ),
                ),
            ):
                phase_label = f'{suite_name}_{kind}'

                if endpoint is None:
                    _record(skipped_result(cid, phase_label, f'{kind} cluster creation failed'))
                    continue

                try:
                    configure_server_secret_for_cluster(cid, args.region)
                    if is_async:
                        _record(await runner())
                    else:
                        _record(runner())
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

    # Best-effort SG cleanup. If the cluster's ENI hasn't been released
    # yet, this fails with DependencyViolation; gc_e2e_test_security_groups
    # at the next run reaps it.
    if test_security_group_id:
        try:
            await asyncio.to_thread(
                delete_e2e_test_security_group, args.region, test_security_group_id
            )
        except Exception as e:
            logger.warning(f'SG cleanup raised: {e}')

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
            '(the serverless cluster must exist to be PG-Wire-tested).'
        ),
    )
    args = parser.parse_args()

    # --test-non-express-cluster only makes sense if the serverless
    # cluster is actually created, so it implies --test-serverless-cluster.
    if args.test_non_express_cluster:
        args.test_serverless_cluster = True

    # Replace loguru's default sink with one at the requested level. This
    # filters everything (including the postgres-mcp-server modules' own
    # logger calls) so DEBUG-level cluster property dumps stay out of the
    # log unless the operator explicitly opts in.
    logger.remove()
    logger.add(sys.stderr, level=args.log_level)

    asyncio.run(main_async(args))


if __name__ == '__main__':
    main()
