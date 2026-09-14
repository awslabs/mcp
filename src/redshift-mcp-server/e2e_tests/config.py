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

"""Reads config.toml, the harness's only source of account-specific values.

Nothing here has a default that reaches AWS. A missing or unfilled config is an error rather
than a fallback, so a run cannot silently target the wrong account.
"""

import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TypeVar


if sys.version_info >= (3, 11):
    import tomllib
else:  # tomllib landed in 3.11, and this package supports 3.10.
    import tomli as tomllib


# The action whose absence selects the server's no_batch compatibility path. Named here, rather
# than beside the role that is denied it or the credentials that carry the denial, because both
# of those need it and neither should import the other.
DENIED_ACTION = 'redshift-data:BatchExecuteStatement'

HARNESS_ROOT = Path(__file__).resolve().parent

# The package under test, which the harness runs the server from and the agent reads.
PACKAGE_ROOT = HARNESS_ROOT.parent

CONFIG_PATH = HARNESS_ROOT / 'config.toml'
EXAMPLE_PATH = HARNESS_ROOT / 'config.toml.example'

# Committed, and referred to from commit messages and pull requests as evidence of testing.
REPORTS_DIR = HARNESS_ROOT / 'reports'

# kiro-cli discovers an agent from the working directory it is invoked in, so the generated
# agent has to sit here for the harness to own it rather than the workspace.
AGENTS_DIR = HARNESS_ROOT / '.kiro' / 'agents'


class ConfigError(RuntimeError):
    """The config is absent, incomplete, or still carries an example placeholder."""


@dataclass(frozen=True)
class Config:
    """Everything the harness needs to reach one account and drive one agent."""

    profile: str
    region: str
    cluster_identifier: str
    node_type: str
    number_of_nodes: int
    master_username: str
    cluster_subnet_group_name: str
    namespace_name: str
    workgroup_name: str
    base_capacity: int
    database: str
    schema: str
    s3_read_role_name: str
    denied_batch_role_name: str
    agent_command: str
    agent_name: str
    model: str
    timeout_seconds: int
    pause_after_run: bool
    destroy_after_run: bool


T = TypeVar('T', str, int, bool)


def _require(table: dict, section: str, key: str, expected: type[T]) -> T:
    """Return one setting, refusing an unfilled placeholder or the wrong type.

    Args:
        table: The parsed section.
        section: Section name, for the error message.
        key: Setting name.
        expected: What the setting has to be. A quoted number is a mistake worth reporting
            here rather than as a confusing failure from an AWS call much later.

    Returns:
        The configured value.

    Raises:
        ConfigError: If the key is missing, still holds an <UPPER_SNAKE> placeholder, or is not
            of the expected type.
    """
    if key not in table:
        raise ConfigError(f'{CONFIG_PATH.name} is missing [{section}].{key}')

    value = table[key]
    if isinstance(value, str) and value.startswith('<') and value.endswith('>'):
        raise ConfigError(f'[{section}].{key} still holds the placeholder {value}')

    # bool is a subclass of int, so a plain isinstance would let `true` pass for a count.
    if not isinstance(value, expected) or (expected is int and isinstance(value, bool)):
        raise ConfigError(
            f'[{section}].{key} should be {expected.__name__}, got '
            f'{type(value).__name__} ({value!r})'
        )

    return value


def load() -> Config:
    """Load and validate the config.

    Returns:
        The validated config.

    Raises:
        ConfigError: If the file is absent, or any setting is missing or unfilled.
    """
    if not CONFIG_PATH.exists():
        raise ConfigError(
            f'{CONFIG_PATH} not found. Copy {EXAMPLE_PATH.name} to {CONFIG_PATH.name} and fill '
            'in the profile and region.'
        )

    raw = tomllib.loads(CONFIG_PATH.read_text())
    aws = raw.get('aws', {})
    prov = raw.get('provisioned', {})
    serverless = raw.get('serverless', {})
    database = raw.get('database', {})
    iam = raw.get('iam', {})
    agent = raw.get('agent', {})
    lifecycle = raw.get('lifecycle', {})

    return Config(
        profile=_require(aws, 'aws', 'profile', str),
        region=_require(aws, 'aws', 'region', str),
        cluster_identifier=_require(prov, 'provisioned', 'cluster_identifier', str),
        node_type=_require(prov, 'provisioned', 'node_type', str),
        number_of_nodes=_require(prov, 'provisioned', 'number_of_nodes', int),
        master_username=_require(prov, 'provisioned', 'master_username', str),
        cluster_subnet_group_name=_require(prov, 'provisioned', 'cluster_subnet_group_name', str),
        namespace_name=_require(serverless, 'serverless', 'namespace_name', str),
        workgroup_name=_require(serverless, 'serverless', 'workgroup_name', str),
        base_capacity=_require(serverless, 'serverless', 'base_capacity', int),
        database=_require(database, 'database', 'name', str),
        schema=_require(database, 'database', 'schema', str),
        s3_read_role_name=_require(iam, 'iam', 's3_read_role_name', str),
        denied_batch_role_name=_require(iam, 'iam', 'denied_batch_role_name', str),
        agent_command=_require(agent, 'agent', 'command', str),
        agent_name=_require(agent, 'agent', 'name', str),
        model=_require(agent, 'agent', 'model', str),
        timeout_seconds=_require(agent, 'agent', 'timeout_seconds', int),
        pause_after_run=_require(lifecycle, 'lifecycle', 'pause_after_run', bool),
        destroy_after_run=_require(lifecycle, 'lifecycle', 'destroy_after_run', bool),
    )


def require_executable(name: str) -> str:
    """Resolve a command the harness shells out to, failing loudly when it is absent.

    Kept out of the config so that no machine-specific path is committed, and so a missing
    tool is reported by name rather than as a FileNotFoundError from deep inside a subprocess.

    Args:
        name: Command to look up on PATH.

    Returns:
        Its absolute path.

    Raises:
        ConfigError: If it is not on PATH.
    """
    path = shutil.which(name)
    if path is None:
        raise ConfigError(f'{name} is not on PATH, and the harness runs the server through it')
    return path
