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

"""Session lifecycle tools for Code Interpreter."""

from .client import (
    create_session_client,
    get_client,
    get_default_identifier,
    get_session_client,
    register_session_client,
    remove_session_client,
)
from .models import (
    CodeInterpreterSessionResponse,
    CodeInterpreterSessionSummary,
    SessionListResponse,
)
from loguru import logger
from mcp.server.fastmcp import Context
from typing import Any


# API default when session_timeout_seconds is not specified
DEFAULT_SESSION_TIMEOUT_SECONDS = 900


async def start_code_interpreter_session(
    ctx: Context,
    code_interpreter_identifier: str | None = None,
    name: str | None = None,
    session_timeout_seconds: int | None = None,
    region: str | None = None,
) -> CodeInterpreterSessionResponse:
    """Start a new sandboxed code interpreter session.

    Creates a new session that can execute code, run commands, and manage files
    in an isolated environment. The session remains active until explicitly
    stopped or until the timeout expires (default DEFAULT_SESSION_TIMEOUT_SECONDS).

    Args:
        ctx: MCP context for error signaling and progress updates.
        code_interpreter_identifier: Code interpreter to use. Defaults to
            CODE_INTERPRETER_IDENTIFIER env var or 'aws.codeinterpreter.v1'.
        name: Optional human-readable name for the session.
        session_timeout_seconds: Session timeout in seconds.
            Defaults to DEFAULT_SESSION_TIMEOUT_SECONDS (900).
        region: AWS region. Defaults to AWS_REGION env var or 'us-east-1'.

    Returns:
        CodeInterpreterSessionResponse with session_id, status, and message.
    """
    identifier = code_interpreter_identifier or get_default_identifier()
    client = create_session_client(region)

    logger.info(f'Starting code interpreter session with identifier={identifier}')

    try:
        kwargs: dict[str, Any] = {
            'identifier': identifier,
        }
        if name is not None:
            kwargs['name'] = name
        if session_timeout_seconds is not None:
            kwargs['session_timeout_seconds'] = session_timeout_seconds

        # SDK start() returns the new session_id as a string
        returned_session_id = client.start(**kwargs)
        session_id = returned_session_id or client.session_id
        if not session_id:
            raise ValueError('Failed to obtain session ID from SDK start() call')

        register_session_client(session_id, client)

        return CodeInterpreterSessionResponse(
            session_id=session_id,
            status='READY',
            code_interpreter_identifier=identifier,
            message=f'Session started successfully. Session ID: {session_id}',
        )

    except Exception as e:
        error_msg = f'Failed to start session: {type(e).__name__}: {e}'
        logger.error(error_msg, exc_info=True)
        await ctx.error(error_msg)
        raise


async def stop_code_interpreter_session(
    ctx: Context,
    session_id: str,
    code_interpreter_identifier: str | None = None,
    region: str | None = None,
) -> CodeInterpreterSessionResponse:
    """Stop a running code interpreter session and release its resources.

    Args:
        ctx: MCP context for error signaling and progress updates.
        session_id: The session ID to stop.
        code_interpreter_identifier: Code interpreter identifier. Defaults to
            CODE_INTERPRETER_IDENTIFIER env var or 'aws.codeinterpreter.v1'.
        region: AWS region. Defaults to AWS_REGION env var or 'us-east-1'.

    Returns:
        CodeInterpreterSessionResponse with session_id, status, and message.
    """
    identifier = code_interpreter_identifier or get_default_identifier()

    logger.info(f'Stopping session {session_id}')

    try:
        client = get_session_client(session_id)
        try:
            stopped = client.stop()
            if not stopped:
                logger.warning(f'Stop returned False for session {session_id}')
        finally:
            # Always remove from registry, even if stop() fails
            remove_session_client(session_id)

        return CodeInterpreterSessionResponse(
            session_id=session_id,
            status='TERMINATED',
            code_interpreter_identifier=identifier,
            message=f'Session {session_id} stop requested.',
        )

    except Exception as e:
        error_msg = f'Failed to stop session {session_id}: {type(e).__name__}: {e}'
        logger.error(error_msg, exc_info=True)
        await ctx.error(error_msg)
        raise


async def get_code_interpreter_session(
    ctx: Context,
    session_id: str,
    code_interpreter_identifier: str | None = None,
    region: str | None = None,
) -> CodeInterpreterSessionResponse:
    """Get the status and details of a code interpreter session.

    Args:
        ctx: MCP context for error signaling and progress updates.
        session_id: The session ID to query.
        code_interpreter_identifier: Code interpreter identifier. Defaults to
            CODE_INTERPRETER_IDENTIFIER env var or 'aws.codeinterpreter.v1'.
        region: AWS region. Defaults to AWS_REGION env var or 'us-east-1'.

    Returns:
        CodeInterpreterSessionResponse with session_id, status, and message.
    """
    identifier = code_interpreter_identifier or get_default_identifier()
    client = get_client(region)

    logger.info(f'Getting session {session_id}')

    try:
        # SDK get_session() returns a Dict with session details
        result = client.get_session(
            interpreter_id=identifier,
            session_id=session_id,
        )

        return CodeInterpreterSessionResponse(
            session_id=session_id,
            status=result.get('status', 'UNKNOWN') if isinstance(result, dict) else 'UNKNOWN',
            code_interpreter_identifier=identifier,
            message=f'Session {session_id} retrieved.',
        )

    except Exception as e:
        error_msg = f'Failed to get session {session_id}: {type(e).__name__}: {e}'
        logger.error(error_msg, exc_info=True)
        await ctx.error(error_msg)
        raise


async def list_code_interpreter_sessions(
    ctx: Context,
    code_interpreter_identifier: str | None = None,
    status: str | None = None,
    max_results: int | None = None,
    next_token: str | None = None,
    region: str | None = None,
) -> SessionListResponse:
    """List code interpreter sessions with optional filtering.

    Args:
        ctx: MCP context for error signaling and progress updates.
        code_interpreter_identifier: Code interpreter identifier. Defaults to
            CODE_INTERPRETER_IDENTIFIER env var or 'aws.codeinterpreter.v1'.
        status: Filter by session status ('READY' or 'TERMINATED').
        max_results: Maximum number of sessions to return (1-100).
        next_token: Pagination token from a previous response.
        region: AWS region. Defaults to AWS_REGION env var or 'us-east-1'.

    Returns:
        SessionListResponse with sessions list, next_token, and message.
    """
    identifier = code_interpreter_identifier or get_default_identifier()
    client = get_client(region)

    logger.info(f'Listing sessions for identifier={identifier}')

    try:
        kwargs: dict[str, Any] = {
            'interpreter_id': identifier,
        }
        if status is not None:
            kwargs['status'] = status
        if max_results is not None:
            kwargs['max_results'] = max_results
        if next_token is not None:
            kwargs['next_token'] = next_token

        # SDK list_sessions() returns a Dict with 'sessions' list and optional 'nextToken'
        result = client.list_sessions(**kwargs)

        sessions = []
        raw_sessions = result.get('items', []) if isinstance(result, dict) else []
        for s in raw_sessions:
            sessions.append(
                CodeInterpreterSessionSummary(
                    session_id=s.get('sessionId', ''),
                    status=s.get('status', 'UNKNOWN'),
                    name=s.get('name'),
                )
            )

        return SessionListResponse(
            sessions=sessions,
            next_token=result.get('nextToken') if isinstance(result, dict) else None,
            message=f'Found {len(sessions)} session(s).',
        )

    except Exception as e:
        error_msg = f'Failed to list sessions: {type(e).__name__}: {e}'
        logger.error(error_msg, exc_info=True)
        await ctx.error(error_msg)
        raise
