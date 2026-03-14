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

from .client import get_client, get_default_identifier, set_session_context
from .models import (
    CodeInterpreterSessionResponse,
    CodeInterpreterSessionSummary,
    SessionListResponse,
)
from loguru import logger
from typing import Any


# API default when session_timeout_seconds is not specified
DEFAULT_SESSION_TIMEOUT_SECONDS = 900


async def start_code_interpreter_session(
    code_interpreter_identifier: str | None = None,
    name: str | None = None,
    session_timeout_seconds: int | None = None,
    region: str | None = None,
) -> dict[str, Any]:
    """Start a new sandboxed code interpreter session.

    Creates a new session that can execute code, run commands, and manage files
    in an isolated environment. The session remains active until explicitly
    stopped or until the timeout expires (default DEFAULT_SESSION_TIMEOUT_SECONDS).

    Args:
        code_interpreter_identifier: Code interpreter to use. Defaults to
            CODE_INTERPRETER_IDENTIFIER env var or 'aws.codeinterpreter.v1'.
        name: Optional human-readable name for the session.
        session_timeout_seconds: Session timeout in seconds.
            Defaults to DEFAULT_SESSION_TIMEOUT_SECONDS (900).
        region: AWS region. Defaults to AWS_REGION env var or 'us-east-1'.

    Returns:
        Dictionary with session_id, status, code_interpreter_identifier, and message.
    """
    identifier = code_interpreter_identifier or get_default_identifier()
    client = get_client(region)

    logger.info(f'Starting code interpreter session with identifier={identifier}')

    try:
        kwargs: dict[str, Any] = {
            'identifier': identifier,
        }
        if name:
            kwargs['name'] = name
        if session_timeout_seconds:
            kwargs['session_timeout_seconds'] = session_timeout_seconds

        # SDK start() returns the new session_id as a string
        returned_session_id = client.start(**kwargs)

        response = CodeInterpreterSessionResponse(
            session_id=returned_session_id or client.session_id or '',
            status='READY',
            code_interpreter_identifier=identifier,
            message=f'Session started successfully. Session ID: {returned_session_id}',
        )
        return response.model_dump()

    except Exception as e:
        logger.error(f'Failed to start session: {type(e).__name__}: {e}', exc_info=True)
        return CodeInterpreterSessionResponse(
            session_id='',
            status='ERROR',
            code_interpreter_identifier=identifier,
            message=f'Failed to start session: {type(e).__name__}: {e}',
        ).model_dump()


async def stop_code_interpreter_session(
    session_id: str,
    code_interpreter_identifier: str | None = None,
    region: str | None = None,
) -> dict[str, Any]:
    """Stop a running code interpreter session and release its resources.

    Args:
        session_id: The session ID to stop.
        code_interpreter_identifier: Code interpreter identifier. Defaults to
            CODE_INTERPRETER_IDENTIFIER env var or 'aws.codeinterpreter.v1'.
        region: AWS region. Defaults to AWS_REGION env var or 'us-east-1'.

    Returns:
        Dictionary with session_id, status, and message.
    """
    identifier = code_interpreter_identifier or get_default_identifier()
    client = get_client(region)

    logger.info(f'Stopping session {session_id}')

    try:
        # Set session context before stopping. SDK stop() returns bool and
        # clears internal session state after the API call.
        set_session_context(client, session_id, identifier)
        stopped = client.stop()

        if not stopped:
            logger.warning(f'Stop returned False for session {session_id}')

        # Verify actual status from the service
        result = client.get_session(
            interpreter_id=identifier,
            session_id=session_id,
        )
        actual_status = result.get('status', 'UNKNOWN') if isinstance(result, dict) else 'UNKNOWN'

        response = CodeInterpreterSessionResponse(
            session_id=session_id,
            status=actual_status,
            code_interpreter_identifier=identifier,
            message=f'Session {session_id} stop requested. Status: {actual_status}.',
        )
        return response.model_dump()

    except Exception as e:
        logger.error(
            f'Failed to stop session {session_id}: {type(e).__name__}: {e}', exc_info=True
        )
        return CodeInterpreterSessionResponse(
            session_id=session_id,
            status='ERROR',
            code_interpreter_identifier=identifier,
            message=f'Failed to stop session: {type(e).__name__}: {e}',
        ).model_dump()


async def get_code_interpreter_session(
    session_id: str,
    code_interpreter_identifier: str | None = None,
    region: str | None = None,
) -> dict[str, Any]:
    """Get the status and details of a code interpreter session.

    Args:
        session_id: The session ID to query.
        code_interpreter_identifier: Code interpreter identifier. Defaults to
            CODE_INTERPRETER_IDENTIFIER env var or 'aws.codeinterpreter.v1'.
        region: AWS region. Defaults to AWS_REGION env var or 'us-east-1'.

    Returns:
        Dictionary with session_id, status, code_interpreter_identifier, and message.
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

        response = CodeInterpreterSessionResponse(
            session_id=session_id,
            status=result.get('status', 'UNKNOWN') if isinstance(result, dict) else 'UNKNOWN',
            code_interpreter_identifier=identifier,
            message=f'Session {session_id} retrieved.',
        )
        return response.model_dump()

    except Exception as e:
        logger.error(f'Failed to get session {session_id}: {type(e).__name__}: {e}', exc_info=True)
        return CodeInterpreterSessionResponse(
            session_id=session_id,
            status='ERROR',
            code_interpreter_identifier=identifier,
            message=f'Failed to get session: {type(e).__name__}: {e}',
        ).model_dump()


async def list_code_interpreter_sessions(
    code_interpreter_identifier: str | None = None,
    status: str | None = None,
    max_results: int | None = None,
    next_token: str | None = None,
    region: str | None = None,
) -> dict[str, Any]:
    """List code interpreter sessions with optional filtering.

    Args:
        code_interpreter_identifier: Code interpreter identifier. Defaults to
            CODE_INTERPRETER_IDENTIFIER env var or 'aws.codeinterpreter.v1'.
        status: Filter by session status ('READY' or 'TERMINATED').
        max_results: Maximum number of sessions to return (1-100).
        next_token: Pagination token from a previous response.
        region: AWS region. Defaults to AWS_REGION env var or 'us-east-1'.

    Returns:
        Dictionary with sessions list, next_token, and message.
    """
    identifier = code_interpreter_identifier or get_default_identifier()
    client = get_client(region)

    logger.info(f'Listing sessions for identifier={identifier}')

    try:
        kwargs: dict[str, Any] = {
            'interpreter_id': identifier,
        }
        if status:
            kwargs['status'] = status
        if max_results:
            kwargs['max_results'] = max_results
        if next_token:
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

        response = SessionListResponse(
            sessions=sessions,
            next_token=result.get('nextToken') if isinstance(result, dict) else None,
            message=f'Found {len(sessions)} session(s).',
        )
        return response.model_dump()

    except Exception as e:
        logger.error(f'Failed to list sessions: {type(e).__name__}: {e}', exc_info=True)
        return SessionListResponse(
            sessions=[],
            next_token=None,
            message=f'Failed to list sessions: {type(e).__name__}: {e}',
        ).model_dump()
