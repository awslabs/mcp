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

"""Error handling utilities for the AWS IAM MCP Server."""

from botocore.exceptions import ClientError as BotoClientError


class IamMcpError(Exception):
    """Base exception for IAM MCP Server errors."""

    def __init__(self, message: str, error_code: str = 'IamMcpError'):
        """Initialize the IAM MCP error.

        Args:
            message: Error message
            error_code: Error code identifier
        """
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)


class IamClientError(IamMcpError):
    """Exception for IAM client-side errors."""

    def __init__(self, message: str):
        """Initialize the IAM client error.

        Args:
            message: Error message
        """
        super().__init__(message, 'IamClientError')


class IamPermissionError(IamMcpError):
    """Exception for IAM permission-related errors."""

    def __init__(self, message: str):
        """Initialize the IAM permission error.

        Args:
            message: Error message
        """
        super().__init__(message, 'IamPermissionError')


class IamResourceNotFoundError(IamMcpError):
    """Exception for IAM resource not found errors."""

    def __init__(self, message: str):
        """Initialize the IAM resource not found error.

        Args:
            message: Error message
        """
        super().__init__(message, 'IamResourceNotFoundError')


class IamValidationError(IamMcpError):
    """Exception for IAM validation errors."""

    def __init__(self, message: str):
        """Initialize the IAM validation error.

        Args:
            message: Error message
        """
        super().__init__(message, 'IamValidationError')


def handle_iam_error(error: Exception) -> IamMcpError:
    """Handle IAM-specific errors and return standardized error responses.

    Args:
        error: The exception that was raised

    Returns:
        Standardized IAM MCP error
    """
    if isinstance(error, BotoClientError):
        error_code = error.response.get('Error', {}).get('Code', 'Unknown')
        error_message = error.response.get('Error', {}).get('Message', str(error))

        # Handle common AWS IAM error patterns
        if error_code in ['AccessDenied', 'AccessDeniedException']:
            return IamPermissionError(
                f'Access denied: {error_message}. Please check your AWS credentials and IAM permissions.'
            )
        elif error_code in ['NoSuchEntity', 'NoSuchEntityException']:
            return IamResourceNotFoundError(f'Resource not found: {error_message}')
        elif error_code in ['EntityAlreadyExists', 'EntityAlreadyExistsException']:
            return IamClientError(f'Resource already exists: {error_message}')
        elif error_code in ['InvalidInput', 'InvalidInputException', 'ValidationException']:
            return IamValidationError(f'Invalid input: {error_message}')
        elif error_code in ['LimitExceeded', 'LimitExceededException']:
            return IamClientError(f'Limit exceeded: {error_message}')
        elif error_code in ['ServiceFailure', 'ServiceFailureException']:
            return IamMcpError(f'AWS service failure: {error_message}', 'ServiceFailure')
        elif error_code in ['Throttling', 'ThrottlingException']:
            return IamMcpError(f'Request throttled: {error_message}', 'Throttling')
        elif error_code in ['IncompleteSignature']:
            return IamClientError(
                'Incomplete signature. The request signature does not conform to AWS standards.'
            )
        elif error_code in ['InvalidAction']:
            return IamClientError(
                'Invalid action. The action or operation requested is invalid. Verify that the action is typed correctly.'
            )
        elif error_code in ['InvalidClientTokenId']:
            return IamClientError(
                'Invalid client token ID. The X.509 certificate or AWS access key ID provided does not exist in our records.'
            )
        elif error_code in ['NotAuthorized']:
            return IamPermissionError(
                'Not authorized. The request signature we calculated does not match the signature you provided.'
            )
        elif error_code in ['RequestExpired']:
            return IamClientError(
                'Request expired. The request must be submitted within a valid time frame.'
            )
        elif error_code in ['SignatureDoesNotMatch']:
            return IamClientError(
                'Signature does not match. The request signature we calculated does not match the signature you provided.'
            )
        elif error_code in ['TokenRefreshRequired']:
            return IamClientError(
                'Token refresh required. The AWS access token needs to be refreshed.'
            )
        else:
            return IamMcpError(f'AWS IAM Error ({error_code}): {error_message}', error_code)

    elif isinstance(error, IamMcpError):
        # Already a handled IAM MCP error, return as-is
        return error

    else:
        # Generic error handling
        return IamMcpError(f'Unexpected error: {str(error)}', 'UnexpectedError')
