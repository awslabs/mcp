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

"""CodeInterpreter client factory with per-region caching."""

import os
from bedrock_agentcore.tools.code_interpreter_client import CodeInterpreter
from loguru import logger


MCP_INTEGRATION_SOURCE = 'awslabs-mcp-code-interpreter-server'
DEFAULT_IDENTIFIER = 'aws.codeinterpreter.v1'

_clients: dict[str, CodeInterpreter] = {}


def get_default_region() -> str:
    """Get the default AWS region from environment or fallback.

    Returns:
        AWS region string.
    """
    return os.environ.get('AWS_REGION', 'us-east-1')


def get_default_identifier() -> str:
    """Get the default code interpreter identifier from environment or fallback.

    Returns:
        Code interpreter identifier string.
    """
    return os.environ.get('CODE_INTERPRETER_IDENTIFIER', DEFAULT_IDENTIFIER)


def set_session_context(
    client: CodeInterpreter,
    session_id: str,
    identifier: str | None = None,
) -> None:
    """Set session context on the client before invoking operations.

    Must set both session_id AND identifier. The SDK's invoke() method
    auto-starts a new session if either is None, which would silently
    execute on a new session instead of the intended one.

    Args:
        client: The CodeInterpreter client instance.
        session_id: The session ID to operate on.
        identifier: Code interpreter identifier. Defaults to
            CODE_INTERPRETER_IDENTIFIER env var or 'aws.codeinterpreter.v1'.
    """
    client.session_id = session_id
    client.identifier = identifier or get_default_identifier()


def get_client(region: str | None = None) -> CodeInterpreter:
    """Get or create a cached CodeInterpreter client for the given region.

    One client instance is cached per region. The SDK client tracks session
    state internally (session_id, identifier), so one active session per
    region at a time.

    Args:
        region: AWS region. Defaults to AWS_REGION env var or us-east-1.

    Returns:
        Cached CodeInterpreter client instance.
    """
    resolved_region = region or get_default_region()

    if resolved_region not in _clients:
        logger.info(f'Creating CodeInterpreter client for region {resolved_region}')
        _clients[resolved_region] = CodeInterpreter(
            region=resolved_region,
            integration_source=MCP_INTEGRATION_SOURCE,
        )

    return _clients[resolved_region]


def clear_clients() -> None:
    """Clear all cached client instances.

    Called during server shutdown. Does not stop active sessions — sessions
    expire via their configured timeout.
    """
    logger.info(f'Clearing {len(_clients)} cached CodeInterpreter client(s)')
    _clients.clear()


async def stop_all_sessions() -> None:
    """Stop all active sessions across all cached clients.

    Called during server shutdown when AUTO_STOP_SESSIONS=true.
    """
    for region, client in _clients.items():
        if client.session_id:
            try:
                logger.info(f'Stopping session {client.session_id} in {region}')
                client.stop()
            except Exception as e:
                logger.warning(f'Failed to stop session in {region}: {e}')
    clear_clients()
