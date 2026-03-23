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

"""File operation tools for Code Interpreter."""

import base64
from .client import get_session_client
from .models import FileOperationResult
from loguru import logger
from mcp.server.fastmcp import Context
from typing import Any


async def upload_file(
    ctx: Context,
    session_id: str,
    path: str,
    content: str,
    description: str | None = None,
    region: str | None = None,
) -> FileOperationResult:
    """Upload a file to the sandboxed code interpreter session.

    Creates or overwrites a file at the specified path in the session's sandbox
    with the given content. Path must be relative (e.g. 'data/input.csv').
    The SDK raises ValueError for absolute paths.

    For binary files, pass the content as a base64-encoded string. The sandbox
    can then decode it, e.g. via ``import base64; data = base64.b64decode(content)``.

    Args:
        ctx: MCP context for error signaling and progress updates.
        session_id: The session ID to upload the file to.
        path: Relative file path in the sandbox (e.g. 'data/input.csv').
            Must not start with '/'.
        content: The file content as a string. For binary files, use
            base64 encoding.
        description: Optional description of the file for LLM context.
        region: AWS region.

    Returns:
        FileOperationResult with path and message.
    """
    logger.info(f'Uploading file to session {session_id}: {path}')

    try:
        client = get_session_client(session_id)

        kwargs: dict[str, Any] = {
            'path': path,
            'content': content,
        }
        if description is not None:
            kwargs['description'] = description

        # SDK upload_file() returns Dict[str, Any]
        client.upload_file(**kwargs)

    except Exception as e:
        error_msg = f'File upload failed: {type(e).__name__}: {e}'
        logger.error(error_msg, exc_info=True)
        await ctx.error(error_msg)
        raise

    return FileOperationResult(
        path=path,
        message=f'File uploaded successfully to {path}.',
    )


async def download_file(
    ctx: Context,
    session_id: str,
    path: str,
    region: str | None = None,
) -> FileOperationResult:
    """Download a file from the sandboxed code interpreter session.

    Reads the content of a file at the specified path in the session's sandbox.

    Args:
        ctx: MCP context for error signaling and progress updates.
        session_id: The session ID to download the file from.
        path: Relative file path in the sandbox to download (e.g. 'output/result.csv').
        region: AWS region.

    Returns:
        FileOperationResult with path, content, and message.
    """
    logger.info(f'Downloading file from session {session_id}: {path}')

    try:
        client = get_session_client(session_id)
        # SDK download_file() returns Union[str, bytes] directly,
        # raises FileNotFoundError if file doesn't exist
        result = client.download_file(path=path)

    except Exception as e:
        error_msg = f'File download failed: {type(e).__name__}: {e}'
        logger.error(error_msg, exc_info=True)
        await ctx.error(error_msg)
        raise

    # The SDK already attempts UTF-8 decoding and only returns bytes when
    # that fails, so bytes here always means non-decodable binary content.
    if isinstance(result, bytes):
        file_content = base64.b64encode(result).decode('ascii')
        message = f'File downloaded successfully from {path} (base64-encoded binary).'
    else:
        file_content = result
        message = f'File downloaded successfully from {path}.'

    return FileOperationResult(
        path=path,
        content=file_content,
        message=message,
    )
