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

"""Code execution tools for Code Interpreter."""

from .client import get_session_client
from .models import ExecutionResult
from loguru import logger
from mcp.server.fastmcp import Context
from typing import Any


def _parse_invoke_response(result: Any) -> dict[str, Any]:
    """Parse the response from invoke_code_interpreter.

    The API returns an EventStream in result["stream"]. Each stream event may
    contain a "result" with structuredContent (stdout/stderr/exitCode) and
    content blocks (text output, resources).

    Falls back to flat-dict parsing if the SDK pre-consumes the stream in a
    future version.
    """
    stdout = ''
    stderr = ''
    exit_code = 0
    content = ''
    is_error = False

    if isinstance(result, dict) and 'stream' in result:
        for event in result['stream']:
            if 'result' not in event:
                continue
            event_result = event['result']

            structured = event_result.get('structuredContent', {}) or {}
            if structured:
                stdout += structured.get('stdout', '') or ''
                stderr += structured.get('stderr', '') or ''
                if 'exitCode' in structured:
                    exit_code = structured['exitCode']

            for block in event_result.get('content', []):
                if block.get('type') == 'text' and block.get('text'):
                    content += block['text']

            if event_result.get('isError'):
                is_error = True
    elif isinstance(result, dict):
        stdout = result.get('stdout', '')
        stderr = result.get('stderr', '')
        exit_code = result.get('exitCode', 0)
        content = result.get('result', result.get('content', ''))
        is_error = result.get('isError', False)
    elif isinstance(result, str):
        content = result

    if exit_code != 0:
        is_error = True

    return {
        'stdout': stdout,
        'stderr': stderr,
        'exitCode': exit_code,
        'content': content,
        'isError': is_error,
    }


async def execute_code(
    ctx: Context,
    session_id: str,
    code: str,
    language: str | None = None,
    clear_context: bool | None = None,
    region: str | None = None,
) -> ExecutionResult:
    """Execute code in a sandboxed code interpreter session.

    Runs Python, JavaScript, or TypeScript code in the session's sandbox.
    The execution context (variables, imports) persists across calls within
    the same session unless clear_context is True.

    Args:
        ctx: MCP context for error signaling and progress updates.
        session_id: The session ID to execute code in. Must be a started session.
        code: The source code to execute.
        language: Programming language ('python', 'javascript', 'typescript').
            Defaults to 'python'.
        clear_context: If True, reset the execution context before running.
        region: AWS region.

    Returns:
        ExecutionResult with stdout, stderr, exit_code, is_error, content, and message.
    """
    logger.info(f'Executing code in session {session_id} (language={language or "python"})')

    try:
        client = get_session_client(session_id)

        kwargs: dict[str, Any] = {'code': code}
        if language:
            kwargs['language'] = language
        if clear_context is not None:
            kwargs['clear_context'] = clear_context

        raw = client.execute_code(**kwargs)
        parsed = _parse_invoke_response(raw)

    except Exception as e:
        error_msg = f'Code execution failed: {type(e).__name__}: {e}'
        logger.error(error_msg, exc_info=True)
        await ctx.error(error_msg)
        raise

    return ExecutionResult(
        stdout=parsed['stdout'],
        stderr=parsed['stderr'],
        exit_code=parsed['exitCode'],
        is_error=parsed['isError'],
        content=parsed['content'],
        message='Code executed successfully.'
        if not parsed['isError']
        else 'Code execution failed.',
    )


async def execute_command(
    ctx: Context,
    session_id: str,
    command: str,
    region: str | None = None,
) -> ExecutionResult:
    """Execute a shell command in a sandboxed code interpreter session.

    Runs a shell command in the session's sandbox environment.

    Args:
        ctx: MCP context for error signaling and progress updates.
        session_id: The session ID to execute the command in.
        command: The shell command to execute.
        region: AWS region.

    Returns:
        ExecutionResult with stdout, stderr, exit_code, is_error, and message.
    """
    logger.info(f'Executing command in session {session_id}')

    try:
        client = get_session_client(session_id)
        raw = client.execute_command(command=command)
        parsed = _parse_invoke_response(raw)

    except Exception as e:
        error_msg = f'Command execution failed: {type(e).__name__}: {e}'
        logger.error(error_msg, exc_info=True)
        await ctx.error(error_msg)
        raise

    return ExecutionResult(
        stdout=parsed['stdout'],
        stderr=parsed['stderr'],
        exit_code=parsed['exitCode'],
        is_error=parsed['isError'],
        message='Command executed successfully.'
        if not parsed['isError']
        else 'Command execution failed.',
    )


async def install_packages(
    ctx: Context,
    session_id: str,
    packages: list[str],
    upgrade: bool = False,
    region: str | None = None,
) -> ExecutionResult:
    """Install Python packages in a sandboxed code interpreter session.

    Uses pip to install the specified packages in the session's sandbox.

    Args:
        ctx: MCP context for error signaling and progress updates.
        session_id: The session ID to install packages in.
        packages: List of package names to install (e.g. ['numpy', 'pandas>=2.0']).
        upgrade: If True, upgrade packages to the latest version.
        region: AWS region.

    Returns:
        ExecutionResult with stdout, stderr, exit_code, is_error, and message.
    """
    logger.info(f'Installing packages in session {session_id}: {packages}')

    try:
        client = get_session_client(session_id)

        kwargs: dict[str, Any] = {'packages': packages}
        if upgrade:
            kwargs['upgrade'] = upgrade

        raw = client.install_packages(**kwargs)
        parsed = _parse_invoke_response(raw)

    except Exception as e:
        error_msg = f'Package installation failed: {type(e).__name__}: {e}'
        logger.error(error_msg, exc_info=True)
        await ctx.error(error_msg)
        raise

    return ExecutionResult(
        stdout=parsed['stdout'],
        stderr=parsed['stderr'],
        exit_code=parsed['exitCode'],
        is_error=parsed['isError'],
        message=f'Installed {len(packages)} package(s) successfully.'
        if not parsed['isError']
        else 'Package installation failed.',
    )
