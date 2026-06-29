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
from .models import FileListResult, FileOperationResult
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


def _parse_list_files_response(result: Any) -> tuple[list[str], str]:
    """Parse the EventStream response from invoke('listFiles').

    The API returns a streaming response with content blocks. For listFiles,
    expect 'text' blocks with listing output and 'resource_link' blocks with
    file URIs.

    Args:
        result: Raw response from client.invoke('listFiles', ...).

    Returns:
        Tuple of (file_paths, raw_content_text).
    """
    files: list[str] = []
    text_parts: list[str] = []

    if isinstance(result, dict) and 'stream' in result:
        for event in result['stream']:
            if 'result' not in event:
                continue
            event_result = event['result']

            for block in event_result.get('content', []):
                block_type = block.get('type', '')

                if block_type == 'text' and block.get('text'):
                    text_parts.append(block['text'])

                elif block_type == 'resource_link':
                    uri = block.get('uri', '')
                    path = uri.replace('file://', '') if uri.startswith('file://') else uri
                    name = block.get('name', '')
                    entry = path or name
                    if entry:
                        files.append(entry)

    # If no resource_link blocks were found, extract file paths from text output
    if not files and text_parts:
        raw_text = '\n'.join(text_parts)
        for line in raw_text.splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith('total '):
                files.append(stripped)

    raw_content = '\n'.join(text_parts)
    return files, raw_content


async def list_files(
    ctx: Context,
    session_id: str,
    directory_path: str | None = None,
    region: str | None = None,
) -> FileListResult:
    """List files in the sandboxed code interpreter session.

    Lists files and directories at the specified path in the session's sandbox.
    If no directory_path is provided, lists files from the default working directory.

    Args:
        ctx: MCP context for error signaling and progress updates.
        session_id: The session ID to list files in. Must be a started session.
        directory_path: Optional directory path to list. Lists from the default
            working directory if omitted.
        region: AWS region.

    Returns:
        FileListResult with file paths, raw content text, and message.
    """
    target = directory_path or 'default working directory'
    logger.info(f'Listing files in session {session_id}: {target}')

    try:
        client = get_session_client(session_id)

        kwargs: dict[str, Any] = {}
        if directory_path is not None:
            kwargs['directoryPath'] = directory_path

        raw = client.invoke('listFiles', kwargs)
        files, content = _parse_list_files_response(raw)

    except Exception as e:
        error_msg = f'List files failed: {type(e).__name__}: {e}'
        logger.error(error_msg, exc_info=True)
        await ctx.error(error_msg)
        raise

    count = len(files)
    message = (
        f'Found {count} file(s) in {target}.' if count > 0 else f'No files found in {target}.'
    )

    return FileListResult(
        files=files,
        content=content,
        message=message,
    )
