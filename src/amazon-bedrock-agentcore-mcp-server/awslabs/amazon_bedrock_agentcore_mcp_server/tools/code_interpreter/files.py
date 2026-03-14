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
from .client import get_client, set_session_context
from .models import FileOperationResult
from loguru import logger
from typing import Any


async def upload_file(
    session_id: str,
    path: str,
    content: str,
    description: str | None = None,
    region: str | None = None,
) -> dict[str, Any]:
    """Upload a file to the sandboxed code interpreter session.

    Creates or overwrites a file at the specified path in the session's sandbox
    with the given content. Path must be relative (e.g. 'data/input.csv').
    The SDK raises ValueError for absolute paths.

    Args:
        session_id: The session ID to upload the file to.
        path: Relative file path in the sandbox (e.g. 'data/input.csv').
            Must not start with '/'.
        content: The file content to upload.
        description: Optional description of the file for LLM context.
        region: AWS region.

    Returns:
        Dictionary with path, is_error, and message.
    """
    client = get_client(region)
    set_session_context(client, session_id)

    logger.info(f'Uploading file to session {session_id}: {path}')

    try:
        kwargs: dict[str, Any] = {
            'path': path,
            'content': content,
        }
        if description:
            kwargs['description'] = description

        # SDK upload_file() returns Dict[str, Any]
        client.upload_file(**kwargs)

        response = FileOperationResult(
            path=path,
            is_error=False,
            message=f'File uploaded successfully to {path}.',
        )
        return response.model_dump()

    except ValueError as e:
        logger.error(f'File upload validation failed: {type(e).__name__}: {e}', exc_info=True)
        return FileOperationResult(
            path=path,
            is_error=True,
            message=f'File upload failed: {type(e).__name__}: {e}',
        ).model_dump()
    except Exception as e:
        logger.error(f'File upload failed: {type(e).__name__}: {e}', exc_info=True)
        return FileOperationResult(
            path=path,
            is_error=True,
            message=f'File upload failed: {type(e).__name__}: {e}',
        ).model_dump()


async def download_file(
    session_id: str,
    path: str,
    region: str | None = None,
) -> dict[str, Any]:
    """Download a file from the sandboxed code interpreter session.

    Reads the content of a file at the specified path in the session's sandbox.

    Args:
        session_id: The session ID to download the file from.
        path: Relative file path in the sandbox to download (e.g. 'output/result.csv').
        region: AWS region.

    Returns:
        Dictionary with path, content, is_error, and message.
    """
    client = get_client(region)
    set_session_context(client, session_id)

    logger.info(f'Downloading file from session {session_id}: {path}')

    try:
        # SDK download_file() returns Union[str, bytes] directly,
        # raises FileNotFoundError if file doesn't exist
        result = client.download_file(path=path)

        is_binary = False
        if isinstance(result, bytes):
            try:
                file_content = result.decode('utf-8')
            except UnicodeDecodeError:
                file_content = base64.b64encode(result).decode('ascii')
                is_binary = True
        else:
            file_content = result

        message = (
            f'File downloaded successfully from {path} (base64-encoded binary).'
            if is_binary
            else f'File downloaded successfully from {path}.'
        )
        response = FileOperationResult(
            path=path,
            content=file_content,
            is_error=False,
            message=message,
        )
        return response.model_dump()

    except FileNotFoundError:
        logger.error(f'File not found: {path}')
        return FileOperationResult(
            path=path,
            is_error=True,
            message=f'File not found: {path}',
        ).model_dump()
    except Exception as e:
        logger.error(f'File download failed: {type(e).__name__}: {e}', exc_info=True)
        return FileOperationResult(
            path=path,
            is_error=True,
            message=f'File download failed: {type(e).__name__}: {e}',
        ).model_dump()
