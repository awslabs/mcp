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

"""Error handling utilities for the MediaLive MCP server.

Provides structured error responses for boto3 ClientError and unexpected exceptions,
ensuring internal details are never exposed to callers.
"""

from botocore.exceptions import ClientError
from loguru import logger


def handle_client_error(e: ClientError) -> dict:
    """Extract error code and message from a boto3 ClientError.

    Returns a structured dict with the error code and message from the AWS API response.
    """
    error_info = e.response['Error']
    return {
        'error': 'ClientError',
        'code': error_info.get('Code', 'Unknown'),
        'message': error_info.get('Message', 'No message provided'),
    }


def handle_general_error(e: Exception) -> dict:
    """Return a generic error response without exposing internal details.

    Logs the full exception for debugging, but returns only a safe message to the caller.
    """
    logger.exception('Unexpected error occurred: {}', e)
    return {
        'error': type(e).__name__,
        'message': 'An unexpected error occurred. Check server logs for details.',
    }
