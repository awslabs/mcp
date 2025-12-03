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

from functools import wraps
from typing import Callable, Optional
from urllib.parse import urlparse


def handle_exceptions(func: Callable) -> Callable:
    """Decorator to handle exceptions in DynamoDB operations.

    Wraps the function in a try-catch block and returns any exceptions
    in a standardized error format.

    Args:
        func: The function to wrap

    Returns:
        The wrapped function that handles exceptions
    """

    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            return {'error': str(e)}

    return wrapper


def is_dynamodb_local(endpoint_url: Optional[str]) -> bool:
    """Determines if an endpoint URL points to DynamoDB Local.

    Args:
        endpoint_url: The endpoint URL to check, or None for AWS default

    Returns:
        True if endpoint is DynamoDB Local, False otherwise
    """
    # Handle None/empty endpoint cases - these indicate AWS DynamoDB
    if not endpoint_url:
        return False

    # Parse URL to extract hostname
    parsed = urlparse(endpoint_url)
    hostname = parsed.hostname

    # Check for DynamoDB Local indicators
    return hostname in ('localhost', '127.0.0.1')


def is_delete_table_operation(command: str) -> bool:
    """Determines if a command is a delete-table operation.

    Args:
        command: AWS CLI command string

    Returns:
        True if command is delete-table, False otherwise
    """
    # Convert to lowercase for case-insensitive matching
    command_lower = command.lower()

    # Check if command contains "delete-table"
    return 'delete-table' in command_lower


def validate_delete_table_operation(
    command: str, endpoint_url: Optional[str]
) -> tuple[bool, Optional[str]]:
    """Validates if a delete-table operation can be executed.

    Args:
        command: AWS CLI command string
        endpoint_url: Target endpoint URL

    Returns:
        Tuple of (is_allowed, error_message)
        - is_allowed: True if operation should proceed
        - error_message: Error description if blocked, None if allowed
    """
    # Check if this is a delete-table operation
    if not is_delete_table_operation(command):
        # Non-delete-table operations are always allowed
        return (True, None)

    # For delete-table operations, check if targeting DynamoDB Local
    if is_dynamodb_local(endpoint_url):
        # Delete-table allowed on DynamoDB Local
        return (True, None)

    # Delete-table blocked on AWS DynamoDB - generate error message
    endpoint_display = endpoint_url if endpoint_url else 'AWS DynamoDB (default)'
    error_message = f"""Delete-table operation is not allowed on AWS DynamoDB.
Table deletion can only be executed against DynamoDB Local.

To use DynamoDB Local, provide an endpoint-url parameter:
  --endpoint-url http://localhost:8000

Current endpoint: {endpoint_display}"""

    return (False, error_message)
