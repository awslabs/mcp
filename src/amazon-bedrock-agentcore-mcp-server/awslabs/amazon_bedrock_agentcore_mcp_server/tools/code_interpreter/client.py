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

"""CodeInterpreter client management with per-session isolation.

Each started session gets its own CodeInterpreter client instance, eliminating
shared mutable state. Region-level operations (get_session, list_sessions)
use a separate per-region client cache.
"""

import os
from bedrock_agentcore.tools.code_interpreter_client import CodeInterpreter
from loguru import logger


MCP_INTEGRATION_SOURCE = 'awslabs-mcp-code-interpreter-server'
DEFAULT_IDENTIFIER = 'aws.codeinterpreter.v1'

# Per-region clients for region-level operations (get_session, list_sessions)
_region_clients: dict[str, CodeInterpreter] = {}
# Per-session clients for session-bound operations (execute, upload, download, stop)
_session_clients: dict[str, CodeInterpreter] = {}


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


def get_client(region: str | None = None) -> CodeInterpreter:
    """Get or create a cached CodeInterpreter client for region-level operations.

    Used by get_session and list_sessions which don't operate on a specific
    session's state.

    Args:
        region: AWS region. Defaults to AWS_REGION env var or us-east-1.

    Returns:
        Cached CodeInterpreter client instance.
    """
    resolved_region = region or get_default_region()

    if resolved_region not in _region_clients:
        logger.info(f'Creating region client for {resolved_region}')
        _region_clients[resolved_region] = CodeInterpreter(
            region=resolved_region,
            integration_source=MCP_INTEGRATION_SOURCE,
        )

    return _region_clients[resolved_region]


def create_session_client(region: str | None = None) -> CodeInterpreter:
    """Create a new CodeInterpreter client for a new session.

    Each session gets its own client instance, avoiding shared mutable state
    from set_session_context() mutations.

    Args:
        region: AWS region. Defaults to AWS_REGION env var or us-east-1.

    Returns:
        A new CodeInterpreter client instance.
    """
    resolved_region = region or get_default_region()
    logger.info(f'Creating session client for region {resolved_region}')
    return CodeInterpreter(
        region=resolved_region,
        integration_source=MCP_INTEGRATION_SOURCE,
    )


def register_session_client(session_id: str, client: CodeInterpreter) -> None:
    """Register a client for an active session.

    Args:
        session_id: The session ID to associate with this client.
        client: The CodeInterpreter client instance for this session.
    """
    _session_clients[session_id] = client


def get_session_client(session_id: str) -> CodeInterpreter:
    """Get the client for an active session.

    Args:
        session_id: The session ID to look up.

    Returns:
        The CodeInterpreter client instance for this session.

    Raises:
        KeyError: If no client is registered for this session ID.
    """
    if session_id not in _session_clients:
        raise KeyError(f'No active session client for session {session_id}')
    return _session_clients[session_id]


def remove_session_client(session_id: str) -> None:
    """Remove a session client after the session is stopped.

    Args:
        session_id: The session ID to remove.
    """
    _session_clients.pop(session_id, None)


def clear_clients() -> None:
    """Clear all cached client instances.

    Called during server shutdown. Does not stop active sessions — sessions
    expire via their configured timeout.
    """
    logger.info(
        f'Clearing {len(_region_clients)} region client(s) '
        f'and {len(_session_clients)} session client(s)'
    )
    _region_clients.clear()
    _session_clients.clear()


async def stop_all_sessions() -> None:
    """Stop all active sessions.

    Called during server shutdown when AUTO_STOP_SESSIONS=true.
    Iterates through all per-session clients and stops each one.
    """
    for session_id, client in list(_session_clients.items()):
        try:
            logger.info(f'Stopping session {session_id}')
            client.stop()
        except Exception as e:
            logger.warning(f'Failed to stop session {session_id}: {e}')
    clear_clients()
