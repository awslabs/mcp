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

"""Command-line entry point for the integration harness provisioning lifecycle.

This module wires the operator-facing ``provision`` / ``teardown`` / ``e2e`` commands to the
deployment-specific modules (:mod:`integration.deploy.agentcore` and
:mod:`integration.deploy.apigateway`).

The **agentcore** deployment is zero-setup: ``provision`` auto-creates the Tenant_Roles, the
execution role, a Cognito identity provider (minting the caller tokens), the DynamoDB role
registry, the ECR image, and the AgentCore Runtime -- no ``--tenant`` inputs are required. The
one-shot ``e2e`` command provisions, runs the AgentCore integration tests with the freshly
minted credentials wired into the environment, and (optionally) tears everything down::

    python -m integration.deploy.cli e2e --deployment agentcore --region us-east-1 --teardown

The **apigateway** deployment still consumes operator-supplied ``--tenant`` role mappings and
the live network inputs documented in the README, because the harness cannot fabricate the
operator-provisioned compute/network resources its private integration fronts.

AWS isolation
-------------
No boto3 client is constructed at import time or during argument parsing. The deployment
modules build their real, boto3-backed seams lazily only when a command actually runs, so
importing this module and exercising :func:`main` with ``--help`` never touches AWS. This
module never modifies server runtime code.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from collections.abc import Sequence
from integration.deploy import agentcore, apigateway
from integration.deploy.common import ProvisionResult, ProvisionStatus, TeardownResult
from integration.harness.opt_in import OPT_IN_ENV, is_opt_in_enabled
from integration.harness.tenants import TenantSpec, build_tenant_records
from pathlib import Path
from typing import Callable, Optional


# The deployment selectors accepted by ``--deployment`` (Req 8: selected deployment).
DEPLOYMENT_AGENTCORE = 'agentcore'
DEPLOYMENT_APIGATEWAY = 'apigateway'
DEPLOYMENT_CHOICES = (DEPLOYMENT_AGENTCORE, DEPLOYMENT_APIGATEWAY)

# Default DynamoDB role-registry table name shared by both deployments.
DEFAULT_TABLE_NAME = agentcore.DEFAULT_TABLE_NAME

# Environment variable carrying additional ``--tenant`` specs (apigateway only). Values use the
# ``identity,role_arn,external_id[,account_id]`` shape, separated by semicolons.
TENANTS_ENV = 'AHO_ITEST_TENANTS'

# The number of tenants the isolation demonstration requires (Tenant_A / Tenant_B).
MIN_TENANTS = 2

# The default AgentCore integration tests the ``e2e`` command runs once provisioned.
DEFAULT_AGENTCORE_TESTS = (
    'integration/tests/test_agentcore_transport.py',
    'integration/tests/test_cross_tenant_isolation.py',
)

# ``OPT_IN_ENV`` (the Opt_In_Signal) is imported from ``integration.harness.opt_in`` as the
# single source of truth; the ``e2e`` command sets it for the test run and ``main`` requires it.


def _repo_root() -> Path:
    """Return the repository root (this file is at ``integration/deploy/cli.py``)."""
    return Path(__file__).resolve().parents[2]


def default_inventory_path(deployment: str) -> str:
    """Return the default inventory file path for ``deployment``.

    Args:
        deployment: The selected deployment identifier.

    Returns:
        A path such as ``./agentcore-inventory.json``.
    """
    return f'./{deployment}-inventory.json'


def parse_tenant_spec(value: str) -> TenantSpec:
    """Parse one ``--tenant`` value into a :class:`TenantSpec` (apigateway only).

    The value is ``identity,role_arn,external_id`` with an optional trailing ``,account_id``.

    Args:
        value: The raw ``identity,role_arn,external_id[,account_id]`` string.

    Returns:
        The parsed tenant spec.

    Raises:
        argparse.ArgumentTypeError: If the value does not have three or four comma-separated,
            non-empty ``identity``/``role_arn``/``external_id`` fields.
    """
    parts = [part.strip() for part in value.split(',')]
    if len(parts) not in (3, 4):
        raise argparse.ArgumentTypeError(
            f'tenant must be "identity,role_arn,external_id[,account_id]"; got {value!r}'
        )
    identity, role_arn, external_id = parts[0], parts[1], parts[2]
    account_id = parts[3] if len(parts) == 4 else None
    if not identity or not role_arn or not external_id:
        raise argparse.ArgumentTypeError(
            f'tenant identity, role_arn, and external_id must all be non-empty; got {value!r}'
        )
    return TenantSpec(
        identity=identity,
        role_arn=role_arn,
        external_id=external_id,
        account_id=account_id or None,
    )


def _tenant_specs_from_env() -> list[TenantSpec]:
    """Return tenant specs parsed from :data:`TENANTS_ENV`, or an empty list if unset."""
    raw = os.environ.get(TENANTS_ENV, '').strip()
    if not raw:
        return []
    return [parse_tenant_spec(entry) for entry in raw.split(';') if entry.strip()]


def _collect_tenant_specs(args: argparse.Namespace) -> list[TenantSpec]:
    """Collect apigateway tenant specs from ``--tenant`` options and the environment.

    Args:
        args: The parsed CLI arguments.

    Returns:
        The collected tenant specs.

    Raises:
        ValueError: If fewer than :data:`MIN_TENANTS` specs are supplied.
    """
    specs: list[TenantSpec] = list(args.tenant or []) or _tenant_specs_from_env()
    if len(specs) < MIN_TENANTS:
        raise ValueError(
            f'at least {MIN_TENANTS} tenants are required (Tenant_A / Tenant_B); '
            f'got {len(specs)}. Provide repeatable --tenant options or set {TENANTS_ENV}.'
        )
    return specs


def _print_provision_result(result: ProvisionResult) -> None:
    """Print a provisioning outcome in a stable, human-readable form."""
    print(f'status: {result.status.value}')
    if result.status is ProvisionStatus.COMPLETE:
        print(f'endpoint: {result.endpoint}')
    else:
        print(f'failed_stage: {result.failed_stage}')
        print(f'detail: {result.detail}')
    print(f'inventory_path: {result.inventory_path}')


def _print_teardown_result(result: TeardownResult) -> None:
    """Print a teardown outcome, naming the exact undeleted resources on failure (Req 8.6)."""
    if result.succeeded:
        print('teardown: succeeded')
        return
    print('teardown: failed')
    print(f'undeleted ({len(result.undeleted)}):')
    for record in result.undeleted:
        print(f'  - {record.resource_type} {record.resource_id} (region={record.region})')


def _provision_agentcore(args: argparse.Namespace) -> agentcore.AgentCoreProvisionOutcome:
    """Provision the zero-setup AgentCore deployment and return its outcome."""
    inventory_path = args.inventory_path or default_inventory_path(DEPLOYMENT_AGENTCORE)
    table_name = args.table_name or DEFAULT_TABLE_NAME
    return agentcore.provision_agentcore(
        region=args.region,
        table_name=table_name,
        inventory_path=inventory_path,
        inbound=getattr(args, 'inbound', agentcore.INBOUND_AUTH_JWT),
    )


def _provision_apigateway(args: argparse.Namespace) -> ProvisionResult:
    """Provision the ApiGateway deployment from operator-supplied tenant specs."""
    specs = _collect_tenant_specs(args)
    tenant_records = build_tenant_records(specs)
    inventory_path = args.inventory_path or default_inventory_path(DEPLOYMENT_APIGATEWAY)
    table_name = args.table_name or DEFAULT_TABLE_NAME
    return apigateway.provision_apigateway(
        region=args.region,
        table_name=table_name,
        tenant_records=tenant_records,
        inventory_path=inventory_path,
    )


def _run_provision(args: argparse.Namespace) -> int:
    """Execute the ``provision`` subcommand and return a process exit code."""
    if args.deployment == DEPLOYMENT_AGENTCORE:
        outcome = _provision_agentcore(args)
        _print_provision_result(outcome.result)
        if outcome.run_config is not None:
            print(
                'note: run the tests with '
                '`python -m integration.deploy.cli e2e --deployment agentcore '
                f'--region {args.region}` so the freshly minted tokens are wired in.'
            )
        return 0 if outcome.result.status is ProvisionStatus.COMPLETE else 1

    result = _provision_apigateway(args)
    _print_provision_result(result)
    return 0 if result.status is ProvisionStatus.COMPLETE else 1


def _run_teardown(args: argparse.Namespace) -> int:
    """Execute the ``teardown`` subcommand and return a process exit code."""
    inventory_path = args.inventory_path or default_inventory_path(args.deployment)

    if args.deployment == DEPLOYMENT_AGENTCORE:
        result = agentcore.teardown_agentcore(inventory_path=inventory_path)
    else:
        result = apigateway.teardown_apigateway(inventory_path=inventory_path)

    _print_teardown_result(result)
    return 0 if result.succeeded else 1


def _run_pytest(env_overrides: dict[str, str], tests: Sequence[str]) -> int:
    """Run the selected integration tests in a subprocess with ``env_overrides`` applied.

    The Opt_In_Signal is enabled and the run config's ``AHO_ITEST_*`` values (including the
    minted bearer tokens) are injected into the child environment only; nothing secret is
    written to disk. The subprocess runs from the repository root so the test paths resolve.
    """
    child_env = dict(os.environ)
    child_env[OPT_IN_ENV] = 'true'
    child_env.update(env_overrides)
    completed = subprocess.run(
        [sys.executable, '-m', 'pytest', *tests, '-v'],
        cwd=str(_repo_root()),
        env=child_env,
    )
    return completed.returncode


def _run_e2e(args: argparse.Namespace) -> int:
    """Execute the one-shot ``e2e`` subcommand: provision, run tests, optionally teardown.

    Only the zero-setup AgentCore deployment is supported here, because it is the only
    deployment that can mint its own caller credentials with no operator inputs.
    """
    if args.deployment != DEPLOYMENT_AGENTCORE:
        print(f'e2e currently supports only the {DEPLOYMENT_AGENTCORE!r} deployment.')
        return 2

    inventory_path = args.inventory_path or default_inventory_path(DEPLOYMENT_AGENTCORE)
    outcome = _provision_agentcore(args)
    _print_provision_result(outcome.result)

    if outcome.result.status is not ProvisionStatus.COMPLETE or outcome.run_config is None:
        return 1

    tests = args.test or list(DEFAULT_AGENTCORE_TESTS)
    print(f'running tests: {" ".join(tests)}')
    test_rc = _run_pytest(outcome.run_config.to_env(), tests)

    if args.teardown:
        print('tearing down provisioned resources...')
        result = agentcore.teardown_agentcore(inventory_path=inventory_path)
        _print_teardown_result(result)
        if not result.succeeded:
            # Surface a teardown failure even when the tests passed, so leaked resources are
            # never silently ignored.
            return test_rc or 1

    return test_rc


def _add_common_arguments(parser: argparse.ArgumentParser) -> None:
    """Add the arguments shared by the subcommands (region, deployment, inventory, table)."""
    parser.add_argument(
        '--region',
        required=True,
        help='Target AWS region; resources are provisioned/torn down here (Req 8.4).',
    )
    parser.add_argument(
        '--deployment',
        required=True,
        choices=DEPLOYMENT_CHOICES,
        help='Which deployment to act on.',
    )
    parser.add_argument(
        '--inventory-path',
        default=None,
        help=(
            'Path to the resource inventory to write (provision) or read (teardown). '
            'Defaults to ./<deployment>-inventory.json.'
        ),
    )
    parser.add_argument(
        '--table-name',
        default=None,
        help=f'DynamoDB role-registry table name. Defaults to {DEFAULT_TABLE_NAME!r}.',
    )


def _add_inbound_argument(parser: argparse.ArgumentParser) -> None:
    """Add the ``--inbound`` mechanism selector (agentcore only)."""
    parser.add_argument(
        '--inbound',
        choices=agentcore.INBOUND_CHOICES,
        default=agentcore.INBOUND_AUTH_JWT,
        help=(
            'Inbound identity mechanism for the agentcore server. "jwt" (default) exercises '
            'the JWT-to-STS registry exchange. "explicit" forwards short-lived per-tenant '
            'credentials instead, avoiding sts:TagSession for accounts whose SCPs deny it.'
        ),
    )


def _add_tenant_argument(parser: argparse.ArgumentParser) -> None:
    """Add the repeatable ``--tenant`` option (used by the apigateway deployment)."""
    parser.add_argument(
        '--tenant',
        action='append',
        type=parse_tenant_spec,
        metavar='identity,role_arn,external_id[,account_id]',
        help=(
            'A tenant to register (apigateway only), repeatable. At least two are required. '
            f'If omitted, tenants are read from {TENANTS_ENV} (entries separated by ";"). '
            'Ignored for the agentcore deployment, which auto-provisions its tenants.'
        ),
    )


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for the provisioning CLI.

    Returns:
        The configured :class:`argparse.ArgumentParser`.
    """
    parser = argparse.ArgumentParser(
        prog='python -m integration.deploy.cli',
        description=(
            'Provision, tear down, or end-to-end run an AWS HealthOmics MCP '
            'integration-test deployment.'
        ),
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    provision_parser = subparsers.add_parser(
        'provision',
        help='Provision the selected deployment and record its resource inventory.',
    )
    _add_common_arguments(provision_parser)
    _add_inbound_argument(provision_parser)
    _add_tenant_argument(provision_parser)
    provision_parser.set_defaults(handler=_run_provision)

    teardown_parser = subparsers.add_parser(
        'teardown',
        help='Delete every resource recorded in the deployment inventory (idempotent).',
    )
    _add_common_arguments(teardown_parser)
    teardown_parser.set_defaults(handler=_run_teardown)

    e2e_parser = subparsers.add_parser(
        'e2e',
        help='Provision (agentcore), run the integration tests, and optionally tear down.',
    )
    _add_common_arguments(e2e_parser)
    _add_inbound_argument(e2e_parser)
    e2e_parser.add_argument(
        '--test',
        action='append',
        metavar='PYTEST_PATH',
        help=(
            'A pytest path to run, repeatable. Defaults to the AgentCore transport and '
            'cross-tenant isolation tests.'
        ),
    )
    e2e_parser.add_argument(
        '--teardown',
        action='store_true',
        help='Tear down all provisioned resources after the tests finish.',
    )
    e2e_parser.set_defaults(handler=_run_e2e)

    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Parse ``argv`` and run the selected subcommand, returning a process exit code.

    Args:
        argv: The argument vector to parse; defaults to ``sys.argv[1:]`` when ``None``.

    Returns:
        ``0`` on success, or a non-zero code on failure or invalid arguments.
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    # Fail-closed opt-in guard (defense in depth). Every subcommand performs live AWS
    # actions (create/delete infrastructure, build/push images via subprocess), so the
    # CLI refuses to run unless the operator has explicitly set the opt-in signal. This
    # ensures the provisioning capability cannot be triggered incidentally -- for example
    # from an automated or compromised context that merely imports and invokes this
    # module -- without a deliberate, out-of-band operator action.
    if not is_opt_in_enabled(os.environ):
        parser.error(
            f'Refusing to run: live AWS provisioning/teardown is gated behind an explicit '
            f'operator opt-in. Set {OPT_IN_ENV} to a truthy value (e.g. "true") to authorize '
            f'this command.'
        )

    handler: Callable[[argparse.Namespace], int] = args.handler
    try:
        return handler(args)
    except ValueError as exc:
        parser.error(str(exc))


if __name__ == '__main__':
    sys.exit(main())
