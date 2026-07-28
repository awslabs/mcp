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

"""Centralised error handling for AgentCore Runtime tools."""

from .models import ErrorResponse
from botocore.exceptions import ClientError
from loguru import logger


def handle_runtime_error(operation: str, error: Exception) -> ErrorResponse:
    """Convert an exception into a structured ``ErrorResponse``.

    Args:
        operation: Friendly name of the API operation that failed.
        error: The caught exception.

    Returns:
        An ``ErrorResponse`` model with extracted error details.
    """
    if isinstance(error, ClientError):
        code = error.response.get('Error', {}).get('Code', 'Unknown')
        msg = error.response.get('Error', {}).get('Message', str(error))
        http = str(error.response.get('ResponseMetadata', {}).get('HTTPStatusCode', ''))
        logger.error(f'{operation} ClientError [{code}]: {msg}')
        return ErrorResponse(
            message=f'{operation} failed: {msg}',
            error_type=code,
            error_code=http,
        )

    logger.error(f'{operation} error: {error}', exc_info=True)
    return ErrorResponse(
        message=f'{operation} failed: {error}',
        error_type=type(error).__name__,
        error_code='',
    )
