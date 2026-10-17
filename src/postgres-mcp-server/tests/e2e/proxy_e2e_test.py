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
r"""End-to-end harness for RDS Proxy auto-detection, against pre-existing infrastructure.

Unlike ``e2e_integration_test.py``, this harness **provisions nothing and deletes
nothing**. It points at RDS instances and proxies that already exist in your
account, because RDS Proxy auto-detection only applies to standalone RPG
instances -- a topology the provisioning harness lists as "planned, not yet
supported".

Every query it issues is read-only (``SELECT``), and it never creates, alters, or
drops a database object. That makes it safe to aim at an existing instance whose
data you care about. It still connects as whatever role your configured secret
names, so prefer a least-privilege read-only role.

What it verifies
----------------

1. **Discovery** -- ``find_proxy_for_instance`` finds the proxy that fronts the
   instance, and the endpoint it returns matches what ``describe_db_proxies``
   reports. Cross-checked independently of the function under test.

2. **TLS under verify-full** -- the proxy presents a certificate that the bundled
   Amazon CA set actually verifies, *including hostname verification*. This is
   the check that cannot be unit-tested: the proxy has its own hostname
   (``*.proxy-<id>.<region>.rds.amazonaws.com``) and its own certificate, and the
   server now defaults to ``sslmode=verify-full``. Asserted from OpenSSL's verify
   return code, not merely logged.

3. **Connect and query through the proxy** -- the connection's host is the proxy
   endpoint, and a real ``SELECT`` succeeds over it. Also confirms, from the
   server's own view, that the backend really is reached via the proxy.

4. **Secret resolution** -- a per-target ``--secret_arn`` override keyed on the
   *instance* endpoint still resolves when the connection is routed to a proxy.
   The live analogue of
   ``test_per_target_secret_arn_keys_off_instance_not_proxy_endpoint``.

5. **Transparency to the caller** -- the connection is cached under the endpoint
   the caller supplied, the proxy host never enters the key space, and the connect
   response reports the instance endpoint with ``proxy_endpoint`` alongside it.
   ``run_query`` raises on a cache miss rather than reconnecting, so a key
   mismatch here would mean every query through a proxy fails.

6. **Negative control** -- an instance with *no* proxy falls back to a direct
   connection. Skipped unless ``--no-proxy-instance`` is supplied; without it
   suite 3 alone cannot distinguish "routed through the proxy" from "ignored the
   proxy and happened to work".

Prerequisites
-------------

- Network reachability from this host to the proxy endpoint on the Postgres port.
  RDS Proxy is normally private, so this generally means running from inside the
  VPC (or over VPN/DirectConnect with the proxy's security group allowing you).
- AWS credentials with ``rds:DescribeDBInstances``, ``rds:DescribeDBProxies``,
  ``rds:DescribeDBProxyTargets``, and ``secretsmanager:GetSecretValue`` on the
  secret in use. A read-only role is sufficient: nothing here mutates anything.
- A password for the ``pg_wire_secret`` path. Normally nothing to do -- the server
  discovers the instance's ``MasterUserSecret`` itself. ``--secret-arn`` is only
  needed when the instance has no managed master password, or to exercise the
  per-target override lookup.
- For ``--auth-type pg_wire_iam``: an ``rds-db:connect`` policy scoped to the
  **proxy** resource (``prx-*``), not the instance. See the README.

Usage
-----
    # Password auth via Secrets Manager (most common)
    python tests/e2e/proxy_e2e_test.py \
        --region us-east-1 \
        --db-instance-identifier my-proxied-instance \
        --database postgres \
        --secret-arn arn:aws:secretsmanager:us-east-1:123456789012:secret:my-secret

    # Add the negative control, and test IAM auth too
    python tests/e2e/proxy_e2e_test.py \
        --region us-east-1 \
        --db-instance-identifier my-proxied-instance \
        --no-proxy-instance my-bare-instance \
        --database postgres \
        --auth-type pg_wire_iam

See ``tests/e2e/run_proxy_e2e.sh`` for a wrapper that refreshes credentials first.
"""

import argparse
import asyncio
import awslabs.postgres_mcp_server.server as server
import boto3
import json
import os
import shutil
import socket
import subprocess
import sys
from awslabs.postgres_mcp_server.connection.cp_api_connection import find_proxy_for_instance
from awslabs.postgres_mcp_server.connection.db_connection_map import (
    ConnectionMethod,
    DatabaseType,
)
from awslabs.postgres_mcp_server.connection.psycopg_pool_connection import _bundled_ca_file
from awslabs.postgres_mcp_server.server import internal_create_connection, run_query
from loguru import logger
from typing import Any, Dict, List, Optional, Tuple


# The provisioning harness owns the shared reporting helpers; reuse them so both
# harnesses produce the same summary format. pytest/python put this file's own
# directory on sys.path only when it is the entry point, so be explicit.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from e2e_integration_test import (  # noqa: E402
    CapturingCtx,
    TestResult,
    log_step,
    log_tls_diagnostics,
    print_summary,
)


AUTH_TYPE_TO_METHOD = {
    'pg_wire_secret': ConnectionMethod.PG_WIRE_PROTOCOL,
    'pg_wire_iam': ConnectionMethod.PG_WIRE_IAM_PROTOCOL,
}


class Recorder:
    """Accumulate pass/fail/skip steps into a TestResult."""

    def __init__(self, label: str, connection_method_name: str):
        """Start an empty result set under the given labels.

        Keeps its own references to the skipped / not-applicable lists and hands
        those same objects to TestResult, which declares them Optional. Appending
        through these references is both type-safe and the same mutation, so the
        results genuinely land in the TestResult the summary reads.
        """
        self._skipped: List[Tuple[str, str]] = []
        self._not_applicable: List[Tuple[str, str]] = []
        self.result = TestResult(
            cluster_identifier=label,
            connection_method_name=connection_method_name,
            passed=[],
            failed=[],
            skipped=self._skipped,
            not_applicable=self._not_applicable,
        )

    def ok(self, step: str, detail: str = '') -> None:
        """Record a passing step."""
        log_step(step, 'PASS', detail)
        self.result.passed.append(step)

    def fail(self, step: str, detail: str = '') -> None:
        """Record a failing step."""
        log_step(step, 'FAIL', detail)
        self.result.failed.append((step, detail))

    def skip(self, step: str, reason: str) -> None:
        """Record a step that could not run. Counts as not-pass.

        Appends to the list directly, NOT via ``self.result.skipped or []``: the
        list starts empty, an empty list is falsy, so that idiom would build a
        throwaway list and silently drop every skip -- which would let an
        un-runnable check (missing openssl, say) pass the run instead of failing it.
        """
        log_step(step, 'SKIP', reason)
        self._skipped.append((step, reason))

    def not_applicable(self, step: str, reason: str) -> None:
        """Record a step with nothing to verify. Does NOT count against success."""
        log_step(step, 'N/A', reason)
        self._not_applicable.append((step, reason))

    def note(self, step: str, detail: str = '') -> None:
        """Record an observation that is neither a pass nor a failure."""
        log_step(step, 'INFO', detail)

    def check(self, step: str, condition: bool, detail: str = '') -> bool:
        """Record pass or fail from a boolean, and return it."""
        if condition:
            self.ok(step, detail)
        else:
            self.fail(step, detail)
        return condition


def resolve_instance(instance_id: str, region: str) -> Dict[str, Any]:
    """Look up an instance by identifier and return its describe_db_instances entry."""
    rds = boto3.client('rds', region_name=region)
    resp = rds.describe_db_instances(DBInstanceIdentifier=instance_id)
    instances = resp.get('DBInstances', [])
    if not instances:
        raise ValueError(f"instance '{instance_id}' not found in {region}")
    return instances[0]


def expected_proxy_for_instance(instance_id: str, region: str) -> Optional[Tuple[str, str]]:
    """Independently determine which proxy fronts an instance.

    Deliberately does not reuse ``find_proxy_for_instance``: this is the oracle
    that function is checked against, so it must not share its logic. Returns
    ``(proxy_name, endpoint)`` or None.
    """
    rds = boto3.client('rds', region_name=region)
    for proxy in rds.describe_db_proxies().get('DBProxies', []):
        if proxy.get('Status') != 'available':
            continue
        name = proxy['DBProxyName']
        targets = rds.describe_db_proxy_targets(DBProxyName=name).get('Targets', [])
        for target in targets:
            if target.get('RdsResourceId') == instance_id:
                return (name, proxy.get('Endpoint', ''))
    return None


def _resolve_ips(hostname: str) -> set:
    """Resolve a hostname to its set of IPv4/IPv6 addresses. Never raises."""
    try:
        return {info[4][0] for info in socket.getaddrinfo(hostname, None)}
    except Exception as e:
        logger.debug(f'could not resolve {hostname}: {type(e).__name__}: {e}')
        return set()


def _local_ips() -> set:
    """Best-effort set of this host's own addresses, for the direct/proxied check."""
    ips = set()
    try:
        ips |= _resolve_ips(socket.gethostname())
    except Exception as e:  # pragma: no cover - diagnostics only
        logger.debug(f'could not resolve own hostname: {type(e).__name__}: {e}')
    # A UDP socket to an off-box address reveals the outbound source IP without
    # sending anything, which catches the case where the hostname does not
    # resolve to the routable address.
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
            probe.connect(('192.0.2.1', 9))  # TEST-NET-1: routable, never answers
            ips.add(probe.getsockname()[0])
    except Exception as e:  # pragma: no cover - diagnostics only
        logger.debug(f'could not determine outbound source IP: {type(e).__name__}: {e}')
    return ips


def verify_tls(host: str, port: int, ca_bundle: Optional[str]) -> Tuple[bool, str]:
    """Verify the endpoint's certificate chain AND hostname against a CA bundle.

    Mirrors what libpq does under ``sslmode=verify-full`` so a failure here
    explains a connection failure there. Returns ``(ok, detail)``; ok is True
    only when OpenSSL reports verify return code 0 with hostname verification
    requested.
    """
    openssl = shutil.which('openssl')
    if not openssl:
        return (False, 'openssl not on PATH')

    cmd = [
        openssl,
        's_client',
        '-starttls',
        'postgres',
        '-connect',
        f'{host}:{port}',
        '-verify_return_error',
        '-verify_hostname',
        host,
    ]
    if ca_bundle and ca_bundle != 'system':
        cmd += ['-CAfile', ca_bundle]

    try:
        proc = subprocess.run(cmd, input=b'', capture_output=True, timeout=30)
    except subprocess.TimeoutExpired:
        return (False, f'handshake to {host}:{port} timed out after 30s (reachability?)')
    except Exception as e:
        return (False, f'{type(e).__name__}: {e}')

    out = proc.stdout.decode('utf-8', 'replace') + '\n' + proc.stderr.decode('utf-8', 'replace')
    if 'Verify return code: 0 (ok)' in out:
        return (True, f'chain + hostname verified against {ca_bundle or "system trust store"}')

    # Surface the specific verify error rather than the whole handshake dump.
    reasons = [
        ln.strip()
        for ln in out.splitlines()
        if 'Verify return code' in ln or ln.strip().startswith('verify error')
    ]
    return (False, '; '.join(reasons) or f'no verify result; exit={proc.returncode}')


async def suite_proxy_routing(
    instance_id: str,
    region: str,
    database: str,
    method: ConnectionMethod,
    auth_type: str,
) -> TestResult:
    """Run discovery, TLS, connect/query, secret-ordering, and conn-map checks."""
    rec = Recorder(instance_id, auth_type)
    logger.info(f'\n=== RDS Proxy routing: instance={instance_id} auth={auth_type} ===')

    # --- resolve the instance -------------------------------------------------
    try:
        instance = resolve_instance(instance_id, region)
    except Exception as e:
        rec.skip('resolve instance', f'{type(e).__name__}: {e}')
        return rec.result

    instance_host = instance.get('Endpoint', {}).get('Address', '')
    port = int(instance.get('Endpoint', {}).get('Port') or 5432)
    if not instance_host:
        rec.skip('resolve instance', f"instance '{instance_id}' reports no endpoint address")
        return rec.result

    # describe_db_instances accepts either an identifier or an ARN, but
    # DBProxyTarget.RdsResourceId is always the *identifier*. Canonicalize here so
    # an ARN passed on the command line still matches proxy targets instead of
    # silently reporting "no proxy found".
    instance_id = instance.get('DBInstanceIdentifier', instance_id)
    rec.ok('resolve instance', f'{instance_id} -> {instance_host}:{port}')

    if instance.get('DBClusterIdentifier'):
        rec.skip(
            'topology is standalone RPG',
            f"instance is a member of cluster '{instance['DBClusterIdentifier']}'; "
            'proxy auto-detection only applies to standalone instances',
        )
        return rec.result

    # --- 1. discovery ---------------------------------------------------------
    step = 'find_proxy_for_instance discovers the proxy'
    try:
        oracle = expected_proxy_for_instance(instance_id, region)
        found = find_proxy_for_instance(instance_id, region)
    except Exception as e:
        rec.fail(step, f'{type(e).__name__}: {e}')
        return rec.result

    if oracle is None:
        rec.skip(
            step,
            f"no available RDS Proxy targets '{instance_id}'; point --db-instance-identifier "
            'at a proxied instance (or pass this one as --no-proxy-instance instead)',
        )
        return rec.result

    proxy_name, expected_endpoint = oracle
    if not rec.check(
        step,
        found == expected_endpoint,
        f"proxy '{proxy_name}': expected {expected_endpoint!r}, got {found!r}",
    ):
        return rec.result
    proxy_host = expected_endpoint

    # --- 2. TLS under verify-full --------------------------------------------
    ca_bundle = server.configured_ca_bundle or _bundled_ca_file()
    if not ca_bundle:
        rec.skip(
            'proxy certificate verifies under verify-full',
            'no CA bundle available (run `python hatch_build.py`, or pass --ca-bundle)',
        )
    else:
        # Full diagnostic dump first, so a failure below has context in the log.
        log_tls_diagnostics(proxy_host, port, ca_bundle, server.configured_sslmode, 'proxy')
        ok, detail = verify_tls(proxy_host, port, ca_bundle)
        rec.check('proxy certificate verifies under verify-full', ok, detail)

        # The instance endpoint is the control: if neither verifies, the finding
        # is about the CA bundle or this host's egress, not about the proxy.
        if not ok:
            ctrl_ok, ctrl_detail = verify_tls(instance_host, port, ca_bundle)
            rec.note(
                'control: instance certificate verifies',
                f'{"yes" if ctrl_ok else "no"} -- {ctrl_detail}',
            )

    # --- 3. connect and query through the proxy ------------------------------
    # "Routes to the proxy" is a property of the connection's host, not of the
    # reported db_endpoint: db_endpoint stays the instance on purpose, and the
    # response payload is asserted separately in suite 5.
    step = 'the connection host is the proxy endpoint'
    conn = None
    try:
        conn, llm_response = internal_create_connection(
            region=region,
            database_type=DatabaseType.RPG,
            connection_method=method,
            cluster_identifier='',
            db_endpoint=instance_host,
            port=port,
            database=database,
        )
        actual_host = getattr(conn, 'host', None)
        rec.check(
            step,
            actual_host == proxy_host,
            f'connection host={actual_host!r} (proxy={proxy_host!r}, instance={instance_host!r})',
        )
    except Exception as e:
        rec.fail(step, f'{type(e).__name__}: {e}')
        return rec.result

    ctx = CapturingCtx()
    step = 'run_query(SELECT version()) over the proxy connection'
    try:
        rows = await run_query(
            sql='SELECT version()',
            ctx=ctx,
            connection_method=method,
            cluster_identifier='',
            db_endpoint=instance_host,
            database=database,
        )
        ok = bool(rows) and 'error' not in rows[0]
        rec.check(step, ok, str(rows[0]) if rows else f'no rows; ctx errors={ctx.errors}')
    except Exception as e:
        rec.fail(step, f'{type(e).__name__}: {e}')

    # Independent evidence that the session really is proxied, from the database's
    # own point of view rather than our bookkeeping.
    #
    # inet_client_addr() is the discriminating probe, NOT inet_server_addr():
    # inet_server_addr() is evaluated on the instance and reports the instance's
    # own address whether or not a proxy is involved. inet_client_addr() reports
    # who the instance thinks connected -- the proxy's ENI on a proxied session,
    # this host's address on a direct one.
    #
    # Reported rather than asserted: RDS Proxy is not contractually required to
    # reuse the same ENIs for client-facing and backend connections, so a
    # mismatch is worth a human look but is not proof of a defect.
    step = 'database sees the proxy as the client (inet_client_addr)'
    try:
        rows = await run_query(
            sql='SELECT inet_client_addr()::text AS client_addr, '
            'inet_server_addr()::text AS server_addr',
            ctx=ctx,
            connection_method=method,
            cluster_identifier='',
            db_endpoint=instance_host,
            database=database,
        )
        if rows and 'error' not in rows[0]:
            client_addr = str(rows[0].get('client_addr', '')).split('/')[0]
            proxy_ips = _resolve_ips(proxy_host)
            local_ips = _local_ips()
            if client_addr and client_addr in proxy_ips:
                verdict = f'{client_addr} is a client-facing proxy ENI -- session is proxied'
            elif client_addr and client_addr in local_ips:
                verdict = (
                    f'{client_addr} is THIS host -- the session reached the database '
                    'directly, bypassing the proxy'
                )
            elif client_addr:
                # The useful signal is that it is NOT this host: something else
                # opened the backend connection. RDS Proxy does not reuse its
                # client-facing ENIs for backend connections, so an address outside
                # the DNS-resolved set is expected rather than suspicious.
                verdict = (
                    f'{client_addr} is not this host {sorted(local_ips)}, so an '
                    'intermediary opened the backend connection -- consistent with '
                    f'proxying. It is outside the client-facing ENIs {sorted(proxy_ips)}, '
                    'which RDS Proxy does not guarantee to reuse for backend '
                    'connections, so the specific address cannot be attributed.'
                )
            else:
                verdict = 'no client address reported; inconclusive'
            rec.note(step, f'{rows[0]} -- {verdict}')
        else:
            rec.note(step, f'unavailable: {rows}')
    except Exception as e:
        rec.note(step, f'unavailable: {type(e).__name__}: {e}')

    # --- 4. secret resolution keys off the instance ---------------------------
    # Only meaningful when a secret is actually in play.
    step = 'per-target secret ARN keys off the instance endpoint'
    pinned = server.configured_secret_arns.get(instance_host)
    if method is ConnectionMethod.PG_WIRE_IAM_PROTOCOL:
        rec.not_applicable(step, 'IAM auth resolves a username, not a password secret')
    elif not pinned:
        reason = (
            'no per-target override configured; the secret came from the instance '
            'MasterUserSecret instead. Pass --secret-arn to exercise the override '
            'lookup as well (the ordering itself is covered by '
            'test_per_target_secret_arn_keys_off_instance_not_proxy_endpoint).'
        )
        rec.not_applicable(step, reason)
    else:
        # The connection succeeded above, which means the secret resolved. Were
        # the proxy host used as the lookup key, the instance-keyed entry would
        # have been missed -- and with no default configured, the connect would
        # have raised instead.
        actual = getattr(conn, 'secret_arn', None)
        rec.check(
            step,
            actual == pinned,
            f'connection uses {actual!r}; pinned to instance endpoint as {pinned!r}',
        )

    # --- 5. the routing is transparent to the caller -------------------------
    # The connection must be cached under the endpoint the caller supplied, not
    # the proxy endpoint it was routed to. run_query rebuilds the key from its own
    # db_endpoint argument and RAISES on a miss rather than reconnecting, so a
    # mismatch here means every query through a proxy fails.
    step = 'connection is cached under the caller-supplied instance endpoint'
    via_instance = server.db_connection_map.get(method, '', instance_host, database, port)
    via_proxy = server.db_connection_map.get(method, '', proxy_host, database, port)
    detail = (
        f'lookup by instance endpoint -> {"hit" if via_instance else "MISS"}; '
        f'lookup by proxy endpoint -> {"hit" if via_proxy else "MISS"}; '
        f'map keys={server.db_connection_map.get_keys_json()}'
    )
    rec.check(step, via_instance is not None, detail)

    # A hit on the proxy endpoint would mean the proxy host leaked into the key
    # space, which is what makes the caller-side lookup miss.
    rec.check(
        'proxy endpoint does not appear in the connection-map key space',
        via_proxy is None,
        detail,
    )

    # The reported identity must be the instance, with the proxy alongside it.
    step = 'connect response reports the instance endpoint plus proxy_endpoint'
    payload = json.loads(llm_response)
    rec.check(
        step,
        payload.get('db_endpoint') == instance_host
        and payload.get('proxy_endpoint') == proxy_host,
        f'db_endpoint={payload.get("db_endpoint")!r} '
        f'proxy_endpoint={payload.get("proxy_endpoint")!r}',
    )

    return rec.result


async def suite_negative_control(
    instance_id: str,
    region: str,
    database: str,
    method: ConnectionMethod,
    auth_type: str,
) -> TestResult:
    """Verify an instance with no proxy still connects directly."""
    rec = Recorder(f'{instance_id} (no-proxy control)', auth_type)
    logger.info(f'\n=== negative control: instance={instance_id} auth={auth_type} ===')

    try:
        instance = resolve_instance(instance_id, region)
    except Exception as e:
        rec.skip('resolve instance', f'{type(e).__name__}: {e}')
        return rec.result

    instance_host = instance.get('Endpoint', {}).get('Address', '')
    port = int(instance.get('Endpoint', {}).get('Port') or 5432)
    if not instance_host:
        rec.skip('resolve instance', 'no endpoint address')
        return rec.result

    # An ARN resolves fine above but never matches DBProxyTarget.RdsResourceId,
    # which would make any instance look un-proxied and turn this control into a
    # false pass. Canonicalize to the identifier first.
    instance_id = instance.get('DBInstanceIdentifier', instance_id)

    step = 'control instance genuinely has no proxy'
    oracle = expected_proxy_for_instance(instance_id, region)
    if not rec.check(
        step,
        oracle is None,
        'none found' if oracle is None else f'unexpectedly fronted by {oracle[0]}',
    ):
        return rec.result

    step = 'no-proxy instance connects directly'
    try:
        _, llm_response = internal_create_connection(
            region=region,
            database_type=DatabaseType.RPG,
            connection_method=method,
            cluster_identifier='',
            db_endpoint=instance_host,
            port=port,
            database=database,
        )
        reported = json.loads(llm_response).get('db_endpoint', '')
        rec.check(step, reported == instance_host, f'reported db_endpoint={reported!r}')
    except Exception as e:
        rec.fail(step, f'{type(e).__name__}: {e}')
        return rec.result

    ctx = CapturingCtx()
    step = 'run_query(SELECT 1) on the direct connection'
    try:
        rows = await run_query(
            sql='SELECT 1 AS ok',
            ctx=ctx,
            connection_method=method,
            cluster_identifier='',
            db_endpoint=instance_host,
            database=database,
        )
        ok = bool(rows) and 'error' not in rows[0]
        rec.check(step, ok, str(rows[0]) if rows else f'no rows; ctx errors={ctx.errors}')
    except Exception as e:
        rec.fail(step, f'{type(e).__name__}: {e}')

    return rec.result


async def main_async(args) -> int:
    """Configure the server globals, run the suites, and summarize."""
    logger.remove()
    logger.add(sys.stderr, level=args.log_level)

    method = AUTH_TYPE_TO_METHOD[args.auth_type]

    # Mirror how main() configures the server, so this exercises the real
    # defaults rather than a hand-built connection.
    server.readonly_query = True
    server.configured_sslmode = args.sslmode
    server.configured_ca_bundle = args.ca_bundle
    server.privilege_check_policy = args.privilege_check
    server.configured_secret_arns.clear()
    server.configured_default_secret_arn = ''

    if args.secret_arn:
        # Pin per-target, keyed on the AWS-resolved instance endpoint -- which is
        # exactly the ordering assertion in suite 4.
        instance = resolve_instance(args.db_instance_identifier, args.region)
        host = instance.get('Endpoint', {}).get('Address', '')
        server.configured_secret_arns[host] = args.secret_arn
        logger.info(f'pinned secret for instance endpoint {host}')

    logger.info(
        f'config: region={args.region} sslmode={server.configured_sslmode} '
        f'privilege_check={server.privilege_check_policy} auth={args.auth_type} '
        f'readonly={server.readonly_query}'
    )

    results: List[TestResult] = [
        await suite_proxy_routing(
            instance_id=args.db_instance_identifier,
            region=args.region,
            database=args.database,
            method=method,
            auth_type=args.auth_type,
        )
    ]

    if args.no_proxy_instance:
        results.append(
            await suite_negative_control(
                instance_id=args.no_proxy_instance,
                region=args.region,
                database=args.database,
                method=method,
                auth_type=args.auth_type,
            )
        )
    else:
        logger.warning(
            'No --no-proxy-instance given: the direct-connection fallback was not '
            'exercised, so a regression that ignores proxies entirely would not be caught.'
        )

    # Release pooled connections; this harness created no AWS resources, so
    # there is nothing else to clean up. Awaited individually rather than via
    # close_all(), which drops its close() coroutines when called from inside a
    # running event loop.
    for conn in server.db_connection_map.list_connections():
        try:
            await conn.close()
        except Exception as e:  # pragma: no cover - best-effort teardown
            logger.debug(f'ignoring close() failure: {type(e).__name__}: {e}')

    return 0 if print_summary(results) else 1


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser."""
    p = argparse.ArgumentParser(
        description='E2E harness for RDS Proxy auto-detection against existing infrastructure.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument('--region', required=True, help='AWS region of the instance and proxy')
    p.add_argument(
        '--db-instance-identifier',
        required=True,
        help='Standalone RPG instance that IS fronted by an RDS Proxy. The DB instance '
        'identifier (its name) or its ARN; an ARN is canonicalized to the identifier.',
    )
    p.add_argument(
        '--database',
        default='postgres',
        help='PostgreSQL database NAME inside the instance, not an ARN (default: postgres)',
    )
    p.add_argument(
        '--no-proxy-instance',
        default='',
        help='Instance with NO proxy, for the direct-connection control. Strongly recommended.',
    )
    p.add_argument(
        '--auth-type',
        choices=sorted(AUTH_TYPE_TO_METHOD),
        default='pg_wire_secret',
        help='Auth method (default: pg_wire_secret). pg_wire_iam needs an rds-db:connect '
        'policy on the prx-* resource.',
    )
    p.add_argument(
        '--secret-arn',
        default='',
        help='OPTIONAL. The server already discovers the instance MasterUserSecret on its '
        'own, so omit this unless the instance has no managed master password, or you '
        'want to exercise the per-target override path (it is pinned to the instance '
        'endpoint, which is also what the override-vs-proxy lookup check needs).',
    )
    p.add_argument(
        '--sslmode',
        default='verify-full',
        help='libpq sslmode (default: verify-full, the server default -- the mode under test)',
    )
    p.add_argument(
        '--ca-bundle',
        default=None,
        help="CA bundle path, or 'system'. Default: the bundled Amazon CA set.",
    )
    p.add_argument(
        '--privilege-check',
        choices=['off', 'warn', 'enforce'],
        default='warn',
        help='Least-privilege guardrail policy (default: warn, the server default)',
    )
    p.add_argument('--log-level', default='INFO', help='Log level (default: INFO)')
    return p


def main() -> None:
    """Entry point."""
    args = build_parser().parse_args()
    sys.exit(asyncio.run(main_async(args)))


if __name__ == '__main__':
    main()
