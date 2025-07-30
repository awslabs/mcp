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
    """Handle common AWS API errors and return standardized error responses.

    Args:
        e: The exception that was raised
        resource_type: Optional resource type related to the error
        identifier: Optional resource identifier related to the error

    Returns:
        Standardized error response dictionary
    """
    print('performing error mapping for an AWS exception')
    error_message = str(e)
    error_type = 'UnknownError'

    # Extract error type from AWS exceptions if possible
    if hasattr(e, 'response') and 'Error' in getattr(e, 'response', {}):
        error_type = e.response['Error'].get('Code', 'UnknownError')  # pyright: ignore[reportAttributeAccessIssue]

    # Handle common AWS error patterns
    if 'AccessDenied' in error_message or error_type == 'AccessDeniedException':
        return ClientError('Access denied. Please check your AWS credentials and permissions.')
    elif 'IncompleteSignature' in error_message:
        return ClientError(
            'Incomplete signature. The request signature does not conform to AWS standards.'
        )
    elif 'InvalidAction' in error_message:
        return ClientError(
            'Invalid action. The action or operation requested is invalid. Verify that the action is typed correctly.'
        )
    elif 'InvalidClientTokenId' in error_message:
        return ClientError(
            'Invalid client token id. The X.509 certificate or AWS access key ID provided does not exist in our records.'
        )
    elif 'NotAuthorized' in error_message:
        return ClientError('Not authorized. You do not have permission to perform this action.')
    elif 'ValidationException' in error_message or error_type == 'ValidationException':
        return ClientError('Validation error. Please check your input parameters.')
    elif 'ResourceNotFoundException' in error_message or error_type == 'ResourceNotFoundException':
        return ClientError('Resource was not found')
    elif (
        'UnsupportedActionException' in error_message or error_type == 'UnsupportedActionException'
    ):
        return ClientError('This action is not supported for this resource type.')
    elif 'InvalidPatchException' in error_message:
        return ClientError(
            'The patch document provided contains errors or is not RFC 6902 compliant.'
        )
    elif 'ThrottlingException' in error_message or error_type == 'ThrottlingException':
        return ClientError('Request was throttled. Please reduce your request rate.')
    elif 'InternalFailure' in error_message or error_type == 'InternalFailure':
        return ServerError('Internal failure. The server failed to process the request.')
    elif 'ServiceUnavailable' in error_message or error_type == 'ServiceUnavailable':
        return ServerError('Service unavailable. The server failed to process the request.')
    else:
        # Generic error handling - we might shift to this for everything eventually since it gives more context to the LLM, will have to test
        return ClientError(f'An error occurred: {error_message}')


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

    def __init__(self, log):
        """Call super."""
        # Call the base class constructor with the parameters it needs
        super().__init__('An internal error occurred while processing your request')
        print(log)
        self.type = 'server'
