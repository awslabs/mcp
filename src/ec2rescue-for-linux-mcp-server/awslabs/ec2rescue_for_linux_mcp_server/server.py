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

"""awslabs EC2Rescue for Linux MCP Server entry point.

Holds the FastMCP instance, the ``list_instances`` tool, the boto3 session,
and the ``main()`` CLI dispatcher. All other helpers live in dedicated
modules (:mod:`.execution`, :mod:`.elicitation`, :mod:`.responses`,
:mod:`.ec2rl`) so this file stays small and easy to scan.
"""

import argparse
import boto3
import os
import sys
from awslabs.ec2rescue_for_linux_mcp_server import ec2rl as ec2rl_module
from awslabs.ec2rescue_for_linux_mcp_server import elicitation as _elicitation
from awslabs.ec2rescue_for_linux_mcp_server.auth import get_server_auth
from awslabs.ec2rescue_for_linux_mcp_server.consts import (
    DEFAULT_MOD_DIR,
    INSTANCE_ID_PATTERN,
    SERVER_NAME,
)
from awslabs.ec2rescue_for_linux_mcp_server.elicitation import _install_gate
from awslabs.ec2rescue_for_linux_mcp_server.responses import InstallResponse, InstanceListResponse
from awslabs.ec2rescue_for_linux_mcp_server.ssm import list_ssm_instances, run_install_ec2_rescue
from awslabs.ec2rescue_for_linux_mcp_server.yaml_loader import (
    ModuleManifestError,
    load_modules_from_yaml_dir,
)
from loguru import logger
from mcp.server.fastmcp import Context, FastMCP
from pydantic import Field


logger.remove()
logger.add(sys.stderr, level=os.environ.get('FASTMCP_LOG_LEVEL', 'WARNING'))

aws_region: str | None = os.environ.get('AWS_REGION') or os.environ.get('AWS_DEFAULT_REGION')

try:
    logger.info(
        f'AWS_REGION={os.environ.get("AWS_REGION")}, '
        f'AWS_DEFAULT_REGION={os.environ.get("AWS_DEFAULT_REGION")}, '
        f'AWS_PROFILE={os.environ.get("AWS_PROFILE")}, '
        f'HOME={os.environ.get("HOME")}'
    )
    session_kwargs: dict[str, str] = {}
    if aws_profile := os.environ.get('AWS_PROFILE'):
        session_kwargs['profile_name'] = aws_profile
    if aws_region:
        session_kwargs['region_name'] = aws_region
    session = boto3.Session(**session_kwargs)
    if not session.region_name:
        raise ValueError(
            'No AWS region configured. Set AWS_REGION, or configure a region '
            'for your AWS_PROFILE in ~/.aws/config.'
        )
    logger.info(f'Session region={session.region_name}, profile={session.profile_name}')
except Exception as e:
    logger.error(f'Error creating AWS session: {str(e)}')
    raise


# The FastMCP instance is created without auth settings initially (for stdio).
# When --transport=streamable-http is used, main() replaces this instance
# with one that has auth configured based on AUTH_TYPE env var.
mcp = FastMCP(
    SERVER_NAME,
    instructions='EC2Rescue for Linux MCP Server (ec2rl modules loaded at startup).',
    dependencies=[
        'boto3',
        'loguru',
        'pydantic',
        'pyyaml',
    ],
)


async def list_instances(
    ctx: Context,
) -> str:
    """List SSM-managed EC2 instances as JSON. Call first to get valid instance IDs."""
    try:
        logger.info('Listing SSM-managed instances')
        instances = await list_ssm_instances(session)
        if not instances:
            return InstanceListResponse(
                instances=[], message='No SSM-managed instances found.'
            ).model_dump_json(exclude_none=True)
        return InstanceListResponse(instances=instances).model_dump_json(exclude_none=True)
    except Exception as e:
        logger.error(f'Error listing instances: {str(e)}')
        await ctx.error(f'Error listing instances: {str(e)}')
        raise


async def install_ec2rescue_linux(
    ctx: Context,
    instance_id: str = Field(
        ...,
        pattern=INSTANCE_ID_PATTERN,
        description=(
            'The EC2 instance ID to install EC2 Rescue on. '
            'Must be a valid instance ID from the list_instances tool '
            '(e.g. i-0abc123def456789).'
        ),
    ),
) -> str:
    """Install EC2 Rescue for Linux on an instance via AWSSupport-InstallEC2Rescue.

    ## Usage Requirements
    - Call `list_instances` first to get a valid instance ID.
    - The instance must be SSM-managed and online.
    - The server must have been started with `--allow-install`.

    ## What This Does
    Runs the AWS SSM Automation document `AWSSupport-InstallEC2Rescue`,
    which downloads and installs the EC2 Rescue for Linux toolset on the
    target instance. This is a prerequisite for running any `run_ec2rescue_linux_*`
    diagnostic tool.

    ## Response Format
    Returns JSON with:
    - `instance_id`: Target instance.
    - `status`: Success / Failed / TimedOut / Cancelled / Aborted.
    - `automation_execution_id`: SSM Automation execution ID.
    - `failure_message`: Reason if the automation failed.

    ## Notes
    - NOTE: This installs software on the instance. It is disabled unless the
      server was started with `--allow-install`, and otherwise returns Aborted
      (`install_not_permitted`).
    """
    try:
        abort = _install_gate(instance_id)
        if abort is not None:
            return abort

        logger.info(f'Installing EC2 Rescue on {instance_id}')
        result = await run_install_ec2_rescue(session, instance_id)

        return InstallResponse(
            instance_id=instance_id,
            status=result['status'],
            automation_execution_id=result['automation_execution_id'],
            outputs=result['outputs'] or None,
            failure_message=result['failure_message'] or None,
        ).as_json()
    except Exception as e:
        logger.error(f'Error installing EC2 Rescue on {instance_id}: {str(e)}')
        await ctx.error(f'Error installing EC2 Rescue: {str(e)}')
        raise


# Back-compat re-exports — tests import these names from
# ``awslabs.ec2rescue_for_linux_mcp_server.server``. The real definitions live in
# :mod:`.execution` / :mod:`.elicitation`.
from awslabs.ec2rescue_for_linux_mcp_server.elicitation import (  # noqa: E402, F401
    _ReadAllElicitation,
)
from awslabs.ec2rescue_for_linux_mcp_server.execution import (  # noqa: E402, F401
    _run_ec2rl_module,
    _software_precheck,
    build_server_instructions,
    register_ec2rl_tools,
)


def register_core_tools(mcp_server: FastMCP) -> None:
    """Register the non-module tools on ``mcp_server``.

    Called from main(), not via decorators: main() rebinds ``mcp`` when auth
    is configured, which would drop decorator-time registrations. Install is
    registered unconditionally; ``_install_gate`` decides at call time.
    """
    mcp_server.tool(name='list_instances')(list_instances)
    mcp_server.tool(name='install_ec2rescue_linux')(install_ec2rescue_linux)


def _default_mod_dir() -> str:
    """Absolute path to the bundled ``mod.d/``; walks up from this package."""
    pkg_dir = os.path.dirname(os.path.abspath(__file__))
    # awslabs/ec2rescue_for_linux_mcp_server -> repo root (two levels up)
    candidates = [
        os.path.join(pkg_dir, 'mod.d'),
        os.path.join(os.path.dirname(pkg_dir), 'mod.d'),
        os.path.join(os.path.dirname(os.path.dirname(pkg_dir)), 'mod.d'),
    ]
    for candidate in candidates:
        if os.path.isdir(candidate):
            return candidate
    return DEFAULT_MOD_DIR


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments for the MCP server."""
    parser = argparse.ArgumentParser(
        prog='awslabs.ec2rescue-for-linux-mcp-server',
        description='MCP server that exposes EC2 Rescue Linux modules as MCP tools.',
    )
    parser.add_argument(
        '--remediate',
        action='store_true',
        help=(
            'Register remediation modules that may modify the target instance '
            '(openssh, rebuildinitrd, selinuxpermissive, fstabfailures, '
            'udevpersistentnet, arpignore, arpcache, tcprecycle). '
            'Disabled by default.'
        ),
    )
    parser.add_argument(
        '--transport',
        choices=['stdio', 'streamable-http'],
        default='stdio',
        help='MCP transport (default: stdio).',
    )
    parser.add_argument(
        '--host',
        default=None,
        help=(
            'Bind host for the streamable-http transport. '
            'Only used with --transport=streamable-http. '
            'Defaults to FastMCP setting (127.0.0.1).'
        ),
    )
    parser.add_argument(
        '--port',
        type=int,
        default=None,
        help=(
            'Bind port for the streamable-http transport. '
            'Only used with --transport=streamable-http. '
            'Defaults to FastMCP setting (8000).'
        ),
    )
    parser.add_argument(
        '--allow-perfimpact',
        action='store_true',
        help=(
            'Permit perfimpact modules (tcpdump, perf, strace, etc.), which '
            'may impact running processes. Denied by default; a startup flag '
            'rather than a runtime prompt because agentic MCP clients '
            'auto-answer elicitation.'
        ),
    )
    parser.add_argument(
        '--all',
        action='store_true',
        help=(
            'Register all available ec2rl modules as MCP tools (209+). '
            'Without this flag, only a curated set of 32 commonly-used '
            'modules is registered to reduce context consumption.'
        ),
    )
    parser.add_argument(
        '--modules',
        default=None,
        help=(
            'Comma-separated list of additional module names to register '
            'beyond the default set (e.g. --modules=tcpdump,strace,perf). '
            'Ignored when --all is used.'
        ),
    )
    parser.add_argument(
        '--allow-install',
        action='store_true',
        help=(
            'Permit the install_ec2rescue_linux tool to install EC2 '
            'Rescue via AWSSupport-InstallEC2Rescue. Without this flag the '
            'tool stays visible but refuses to run (fail-closed).'
        ),
    )
    return parser.parse_args(argv)


def main():
    """Run the MCP server with CLI argument support."""
    global mcp

    args = _parse_args()
    mod_dir = _default_mod_dir()

    logger.info(
        f'Starting {SERVER_NAME} '
        f'(region={session.region_name}, mod_dir={mod_dir}, remediation={args.remediate}, '
        f'allow_perfimpact={args.allow_perfimpact}, '
        f'all={args.all})'
    )
    _elicitation._ALLOW_PERFIMPACT = args.allow_perfimpact
    _elicitation._ALLOW_INSTALL = args.allow_install

    # Configure authentication based on transport.
    # For streamable-http, AUTH_TYPE env var is required.
    auth_settings, token_verifier = get_server_auth(args.transport)

    if auth_settings is not None or token_verifier is not None:
        # Recreate the FastMCP instance with auth configured.
        mcp = FastMCP(
            SERVER_NAME,
            instructions='EC2Rescue for Linux MCP Server (ec2rl modules loaded at startup).',
            dependencies=[
                'boto3',
                'loguru',
                'pydantic',
                'pyyaml',
            ],
            auth=auth_settings,
            token_verifier=token_verifier,
        )

    try:
        all_modules = load_modules_from_yaml_dir(mod_dir, include_remediation=args.remediate)
    except ModuleManifestError as e:
        # Fail closed: the bundled definitions were modified without the
        # checksum manifest being regenerated, so refuse to start.
        logger.error(f'Refusing to start: {e}')
        raise SystemExit(1) from e

    if args.all:
        modules = all_modules
    else:
        allowed = set(ec2rl_module.DEFAULT_MODULES)
        if args.modules:
            extra = {m.strip() for m in args.modules.split(',') if m.strip()}
            unknown = extra - set(all_modules)
            if unknown:
                logger.warning(
                    f'--modules references unknown module(s): {sorted(unknown)}; skipping them.'
                )
            allowed |= extra
        modules = {k: v for k, v in all_modules.items() if k in allowed}

    ec2rl_module.EC2RL_MODULES.clear()
    ec2rl_module.EC2RL_MODULES.update(modules)

    register_core_tools(mcp)
    register_ec2rl_tools(mcp, modules)

    # Swap in dynamically-built instructions for the underlying MCP server.
    mcp._mcp_server.instructions = build_server_instructions(modules)

    if args.transport == 'streamable-http':
        if args.host is not None:
            mcp.settings.host = args.host
        if args.port is not None:
            mcp.settings.port = args.port
        logger.info(
            f'Transport=streamable-http host={mcp.settings.host} '
            f'port={mcp.settings.port} path={mcp.settings.streamable_http_path}'
        )
        mcp.run(transport='streamable-http')
    else:
        if args.host is not None or args.port is not None:
            logger.warning('--host/--port ignored under --transport=stdio')
        mcp.run(transport='stdio')


if __name__ == '__main__':
    main()
