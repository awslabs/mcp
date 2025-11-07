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

import boto3
import importlib.metadata
import os
import tempfile
from loguru import logger
from pathlib import Path
from typing import Literal, cast


# Get package version for user agent
try:
    PACKAGE_VERSION = importlib.metadata.version('awslabs.aws_api_mcp_server')
except importlib.metadata.PackageNotFoundError:
    PACKAGE_VERSION = 'unknown'

TRUTHY_VALUES = frozenset(['true', 'yes', '1'])
READ_ONLY_KEY = 'READ_OPERATIONS_ONLY'
TELEMETRY_KEY = 'AWS_API_MCP_TELEMETRY'
REQUIRE_MUTATION_CONSENT_KEY = 'REQUIRE_MUTATION_CONSENT'
ALLOW_UNRESTRICTED_LOCAL_FILE_ACCESS_KEY = 'AWS_API_MCP_ALLOW_UNRESTRICTED_LOCAL_FILE_ACCESS'


def get_region(profile_name: str | None = None) -> str:
    """Get the region depending on configuration."""
    if AWS_REGION:
        return AWS_REGION

    fallback_region = 'us-east-1'

    if profile_name:
        return boto3.Session(profile_name=profile_name).region_name or fallback_region

    return boto3.Session().region_name or fallback_region


def get_server_directory():
    """Get platform-appropriate log directory."""
    base_location = 'aws-api-mcp'
    if os.name == 'nt' or os.uname().sysname == 'Darwin':  # Windows and macOS
        return Path(tempfile.gettempdir()) / base_location
    # Linux
    base_dir = (
        os.environ.get('XDG_RUNTIME_DIR') or os.environ.get('TMPDIR') or tempfile.gettempdir()
    )
    return Path(base_dir) / base_location


def get_env_bool(env_key: str, default: bool) -> bool:
    """Get a boolean value from an environment variable, with a default."""
    return os.getenv(env_key, str(default)).casefold() in TRUTHY_VALUES


def get_transport_from_env() -> Literal['stdio', 'streamable-http']:
    """Get a transport value from an environment variable, with a default."""
    transport = os.getenv('AWS_API_MCP_TRANSPORT', 'stdio')
    if transport not in ['stdio', 'streamable-http']:
        raise ValueError(f'Invalid transport: {transport}')

    # Enforce explicit auth configuration for streamable-http transport
    if transport == 'streamable-http':
        auth_type = os.getenv('AUTH_TYPE')
        if auth_type != 'no-auth':
            error_message = "Invalid configuration: 'streamable-http' transport requires AUTH_TYPE environment variable to be explicitly set to 'no-auth'."
            logger.error(error_message)
            raise ValueError(error_message)

    return cast(Literal['stdio', 'streamable-http'], transport)


def get_user_agent_extra() -> str:
    """Get the user agent extra string."""
    user_agent_extra = f'awslabs/mcp/AWS-API-MCP-server/{PACKAGE_VERSION}'
    if not OPT_IN_TELEMETRY:
        return user_agent_extra
    user_agent_extra += f' cfg/ro#{"1" if READ_OPERATIONS_ONLY_MODE else "0"}'
    user_agent_extra += f' cfg/consent#{"1" if REQUIRE_MUTATION_CONSENT else "0"}'
    user_agent_extra += f' cfg/scripts#{"1" if ENABLE_AGENT_SCRIPTS else "0"}'
    return user_agent_extra


FASTMCP_LOG_LEVEL = os.getenv('FASTMCP_LOG_LEVEL', 'INFO')
AWS_API_MCP_PROFILE_NAME = os.getenv('AWS_API_MCP_PROFILE_NAME')
AWS_REGION = os.getenv('AWS_REGION')
DEFAULT_REGION = get_region(AWS_API_MCP_PROFILE_NAME)
READ_OPERATIONS_ONLY_MODE = get_env_bool(READ_ONLY_KEY, False)
OPT_IN_TELEMETRY = get_env_bool(TELEMETRY_KEY, True)
WORKING_DIRECTORY = os.getenv('AWS_API_MCP_WORKING_DIR', get_server_directory() / 'workdir')
REQUIRE_MUTATION_CONSENT = get_env_bool(REQUIRE_MUTATION_CONSENT_KEY, False)
ENABLE_AGENT_SCRIPTS = get_env_bool('EXPERIMENTAL_AGENT_SCRIPTS', False)
TRANSPORT = get_transport_from_env()
HOST = os.getenv('AWS_API_MCP_HOST', '127.0.0.1')
PORT = int(os.getenv('AWS_API_MCP_PORT', 8000))
ALLOWED_HOSTS = os.getenv('AWS_API_MCP_ALLOWED_HOSTS', HOST)
ALLOWED_ORIGINS = os.getenv('AWS_API_MCP_ALLOWED_ORIGINS', HOST)
STATELESS_HTTP = get_env_bool('AWS_API_MCP_STATELESS_HTTP', False)
CUSTOM_SCRIPTS_DIR = os.getenv('AWS_API_MCP_AGENT_SCRIPTS_DIR')
ALLOW_UNRESTRICTED_LOCAL_FILE_ACCESS = get_env_bool(
    ALLOW_UNRESTRICTED_LOCAL_FILE_ACCESS_KEY, False
)
ENDPOINT_SUGGEST_AWS_COMMANDS = os.getenv(
    'ENDPOINT_SUGGEST_AWS_COMMANDS', 'https://api-mcp.global.api.aws/suggest-aws-commands'
)
