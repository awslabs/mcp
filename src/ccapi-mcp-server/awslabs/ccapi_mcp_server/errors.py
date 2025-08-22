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


def handle_aws_api_error(e: Exception) -> Exception:
    """Handle AWS API errors using boto3's built-in exception information.

    Leverages boto3's structured error handling as documented at:
    https://boto3.amazonaws.com/v1/documentation/api/latest/guide/error-handling.html

    Args:
        e: The exception that was raised

    Returns:
        Standardized ClientError with AWS error details
    """
    # Import boto3 exceptions for proper type checking
    from botocore.exceptions import ClientError as BotocoreClientError
    from botocore.exceptions import NoCredentialsError, PartialCredentialsError

    # Handle boto3's structured exceptions directly
    if isinstance(e, BotocoreClientError):
        # boto3 ClientError already has structured error information
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        return ClientError(f'AWS API Error ({error_code}): {error_message}')
    elif isinstance(e, NoCredentialsError):
        return ClientError('AWS credentials not found. Please configure your AWS credentials.')
    elif isinstance(e, PartialCredentialsError):
        return ClientError(
            'Incomplete AWS credentials. Please check your AWS credential configuration.'
        )
    else:
        # Fallback for other exceptions
        return ClientError(f'An error occurred: {str(e)}')


class ClientError(Exception):
    """An error that indicates that the request was malformed or incorrect in some way. There was no issue on the server side."""

    def __init__(self, message):
        """Call super and set message."""
        # Call the base class constructor with the parameters it needs
        super().__init__(message)
        self.type = 'client'
        self.message = message


class ServerError(Exception):
    """An error that indicates that there was an issue processing the request."""

    def __init__(self, message: str):
        """Initialize ServerError with message."""
        super().__init__(message)
        self.type = 'server'
        self.message = message
