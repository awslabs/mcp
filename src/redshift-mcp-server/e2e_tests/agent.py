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

"""Generates the agent config that gives the testing agent the server under test.

Five servers, one per configuration whose behaviour differs. Each runs this working tree, not a
published release, so a run tests the code in front of you.

Access mode and write confirmation are read once at server start, so a configuration cannot be
changed mid-conversation. Handing the agent all five at once is what lets one scenario compare
them. The last two need credentials rather than configuration, so they carry an assumed role's
keys instead of the profile.

Two of them are denied the batch action, not one, because the fallback's refusals are only
reachable at particular configurations. `nb` is read-only, which is both the default install and
the compatibility case the fallback exists for. `nbw` skips write confirmation, because
confirmation is checked before the fallback is consulted: at any configuration that confirms,
a write is refused for want of a confirmation and the fallback's own explanation of why writes
cannot be served never surfaces.

Every server exposes the same seven tool names, and an agent shown five servers offering
`execute_query` is shown one `execute_query`, with no say in which server answers. So each is
aliased to a distinct name, `ro_execute_query` against `nb_execute_query` and so on. Without
that a scenario cannot tell the configurations apart, and reports comparing them are not
comparing anything.

The file is generated rather than committed: it holds live session credentials, and it names
absolute paths that are true only on the machine that wrote it. `.kiro/agents/` under the
harness is where kiro-cli looks when invoked from the harness directory, which keeps it out of
the workspace's own agent directory.
"""

import asyncio
import json
from awslabs.redshift_mcp_server import server
from e2e_tests import denied_batch
from e2e_tests.config import (
    AGENTS_DIR,
    DENIED_ACTION,
    PACKAGE_ROOT,
    Config,
    require_executable,
)
from pathlib import Path


# Where the server writes its own log. Not committed: it is a debugging aid for the run that
# just happened, and it holds every statement the agent sent.
LOGS_DIR = AGENTS_DIR.parent.parent / '.logs'

READ_ONLY = 'awslabs.redshift-mcp-server'
READ_WRITE = 'awslabs.redshift-mcp-server-read-write'
READ_WRITE_UNSAFE = 'awslabs.redshift-mcp-server-read-write-unsafe'
NO_BATCH = 'awslabs.redshift-mcp-server-no-batch'
NO_BATCH_WRITE = 'awslabs.redshift-mcp-server-no-batch-write'

# What each server is for, and the prefix its tools are aliased under. Both are quoted into the
# scenario prompts, so the agent is told the same thing the config says.
SERVERS = {
    READ_ONLY: (
        'ro',
        'default configuration: read-only, which is what a user gets by installing it',
    ),
    READ_WRITE: (
        'rw',
        'ACCESS_MODE=read-write, so writes are permitted and each one is confirmed',
    ),
    READ_WRITE_UNSAFE: (
        'rwu',
        'ACCESS_MODE=read-write with UNSAFE_SKIP_WRITE_CONFIRMATION=true, so writes run '
        'unconfirmed',
    ),
    NO_BATCH: (
        'nb',
        f'default configuration, but its credentials are denied {DENIED_ACTION}',
    ),
    NO_BATCH_WRITE: (
        'nbw',
        'ACCESS_MODE=read-write with UNSAFE_SKIP_WRITE_CONFIRMATION=true, and its credentials '
        f'are denied {DENIED_ACTION}',
    ),
}

# The builtins the agent needs: read the package to work out what to test, and run a shell for
# anything the server does not expose. Withholding the file-writing builtins is not a sandbox,
# because the shell can write, delete and run git just as well - it only means the agent has no
# reason to reach for the tree. Run this against a working tree you can throw away.
_BUILTIN_TOOLS = ('fs_read', 'execute_bash')

# Environment values the generated config carries that must not reach a report. The agent can read
# its own config, and the transcript is committed, so what it echoes has to be scrubbed rather
# than trusted not to appear.
_SECRET_ENV = ('AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'AWS_SESSION_TOKEN')


def tool_names() -> list[str]:
    """Return the server's tools, asked of the server rather than listed here.

    A list written down here would go stale the next time a tool is added, and the aliases
    would silently stop covering it.

    Returns:
        Every tool name the server registers, sorted.
    """
    return sorted(tool.name for tool in asyncio.run(server.mcp.list_tools()))


def aliases() -> dict[str, str]:
    """Map each server's tools to a name that says which server it is.

    Returns:
        `@<server>/<tool>` to `<prefix>_<tool>`, for every server and tool.
    """
    return {
        f'@{name}/{tool}': f'{prefix}_{tool}'
        for name, (prefix, _) in SERVERS.items()
        for tool in tool_names()
    }


def _server(uv: str, name: str, env: dict[str, str], *, without_profile: bool = False) -> dict:
    """Describe one MCP server running this working tree.

    Args:
        uv: Absolute path to uv, which runs the server in the package's own environment.
        name: Server name, used to name its log file.
        env: Environment for the server process.
        without_profile: Start it with `AWS_PROFILE` removed, for a server that authenticates
            from explicit keys.

    Returns:
        One entry for the agent config's `mcpServers`.
    """
    argv = [
        uv,
        '--directory',
        str(PACKAGE_ROOT / 'awslabs' / 'redshift_mcp_server'),
        'run',
        'server.py',
    ]

    if without_profile:
        # Removed from the child's environment, which omitting it from `env` does not do: an MCP
        # server inherits this process's environment, so the inherited profile stays in place,
        # and a profile wins over explicit keys.
        argv = [require_executable('env'), '-u', 'AWS_PROFILE', *argv]

    return {
        'command': argv[0],
        'args': argv[1:],
        'env': {'LOG_FILE': str(LOGS_DIR / f'{name}.log'), 'LOG_LEVEL': 'DEBUG', **env},
    }


def render(config: Config, sts) -> dict:
    """Build the agent config.

    Args:
        config: The harness config.
        sts: An STS client, used to assume the denied-batch role.

    Returns:
        The agent config, ready to serialize.

    Raises:
        DenialError: If the denied-batch credentials are not actually denied the action.
    """
    uv = require_executable('uv')
    profile = {'AWS_PROFILE': config.profile, 'AWS_REGION': config.region}

    account = sts.get_caller_identity()['Account']
    no_batch_env = denied_batch.environment(
        sts,
        f'arn:aws:iam::{account}:role/{config.denied_batch_role_name}',
        config.region,
    )
    # Serverless is the cheaper of the two to probe, and needs no secret to authenticate.
    denied_batch.verify(
        no_batch_env, {'WorkgroupName': config.workgroup_name, 'Database': config.database}
    )

    servers = {
        READ_ONLY: _server(uv, READ_ONLY, profile),
        READ_WRITE: _server(uv, READ_WRITE, {**profile, 'ACCESS_MODE': 'read-write'}),
        READ_WRITE_UNSAFE: _server(
            uv,
            READ_WRITE_UNSAFE,
            {**profile, 'ACCESS_MODE': 'read-write', 'UNSAFE_SKIP_WRITE_CONFIRMATION': 'true'},
        ),
        # These two authenticate as the denied role from explicit keys, so the inherited profile
        # has to go with them.
        NO_BATCH: _server(uv, NO_BATCH, no_batch_env, without_profile=True),
        NO_BATCH_WRITE: _server(
            uv,
            NO_BATCH_WRITE,
            {
                **no_batch_env,
                'ACCESS_MODE': 'read-write',
                'UNSAFE_SKIP_WRITE_CONFIRMATION': 'true',
            },
            without_profile=True,
        ),
    }

    tools = [*_BUILTIN_TOOLS, *(f'@{name}' for name in servers)]
    alias_map = aliases()

    return {
        'name': config.agent_name,
        'description': 'Runs end-to-end tests against the Redshift MCP server in this tree',
        # The point of the harness is that the servers are the ones it generated, at the
        # configurations it chose. Merging the workspace's own mcp.json would add servers
        # built from someone else's settings.
        'includeMcpJson': False,
        'mcpServers': servers,
        'tools': tools,
        'toolAliases': alias_map,
        # Nothing may stop for a confirmation prompt: a run has no terminal to answer one.
        # Named by server rather than by alias, because permission is matched against the tool
        # the server actually registered, not the name the agent calls it by.
        'allowedTools': tools,
        'model': config.model,
    }


def write(config: Config, sts) -> tuple[Path, set[str]]:
    """Generate the agent config and put it where kiro-cli will find it.

    Args:
        config: The harness config.
        sts: An STS client, used to assume the denied-batch role.

    Returns:
        Path to the written config, and the credential values it carries, for the caller to keep
        out of anything it writes down.
    """
    AGENTS_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    rendered = render(config, sts)

    path = AGENTS_DIR / f'{config.agent_name}.json'
    path.write_text(json.dumps(rendered, indent=2) + '\n')
    # Session credentials, so keep it to the owner. This stops another OS user reading them, not
    # the agent, which runs as this user and can read its own config.
    path.chmod(0o600)

    secret_values = {
        value
        for server in rendered['mcpServers'].values()
        for name, value in server.get('env', {}).items()
        if name in _SECRET_ENV and value
    }

    return path, secret_values


def trust_argument() -> str:
    """Return the value for kiro-cli's --trust-tools.

    Names each server rather than each alias: permission is matched against the tool the
    server registered, so a list of aliases matches nothing and every call is refused for want
    of a confirmation there is no terminal to give.

    Returns:
        A comma-separated tool list.
    """
    return ','.join([*_BUILTIN_TOOLS, *(f'@{{{name}}}/*' for name in SERVERS)])
