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

"""Error handling for AWS Systems Manager MCP Server."""

import logging
from botocore.exceptions import ClientError, NoCredentialsError
from typing import Any, Dict


logger = logging.getLogger(__name__)


class SsmMcpError(Exception):
    """Base exception for Systems Manager MCP server errors."""

    pass


class SsmClientError(SsmMcpError):
    """Exception for AWS Systems Manager client errors."""

    def __init__(self, message: str, error_code: str = None, status_code: int = None):
        """Initialize SsmClientError with message, error code, and status code."""
        super().__init__(message)
        self.error_code = error_code
        self.status_code = status_code


class SsmValidationError(SsmMcpError):
    """Exception for validation errors."""

    pass


class SsmPermissionError(SsmMcpError):
    """Exception for permission-related errors."""

    pass


def handle_ssm_error(error: Exception) -> SsmMcpError:
    """Handle and convert various AWS and other errors to appropriate SSM MCP errors.

    Args:
        error: The original exception

    Returns:
        SsmMcpError: Appropriate SSM MCP error
    """
    if isinstance(error, SsmMcpError):
        return error

    if isinstance(error, NoCredentialsError):
        return SsmClientError(
            'AWS credentials not found. Please configure your AWS credentials.',
            error_code='NoCredentialsError',
        )

    if isinstance(error, ClientError):
        error_code = error.response.get('Error', {}).get('Code', 'Unknown')
        error_message = error.response.get('Error', {}).get('Message', str(error))
        status_code = error.response.get('ResponseMetadata', {}).get('HTTPStatusCode')

        # Map common AWS errors to more user-friendly messages
        error_mappings = {
            'AccessDenied': 'Access denied. Please check your IAM permissions for Systems Manager.',
            'InvalidDocumentContent': 'The document content is invalid. Please check the JSON/YAML syntax and schema version.',
            'DocumentAlreadyExists': 'A document with this name already exists. Use update_document to modify it or choose a different name.',
            'DocumentVersionLimitExceeded': 'The document has reached the maximum number of versions allowed.',
            'InvalidPermissionType': 'Invalid permission type. Use "Share" for document sharing operations.',
            'ThrottlingException': 'API rate limit exceeded. Please wait and try again.',
            'ValidationException': f'Validation error: {error_message}',
            'ResourceNotFoundException': 'The requested resource was not found.',
            'InvalidParameterValue': f'Invalid parameter value: {error_message}',
            'DuplicateDocumentContent': 'Document with identical content already exists.',
            'DuplicateDocumentVersionName': 'A document version with this name already exists.',
            'InvalidDocumentOperation': 'The requested document operation is not valid.',
            'InvalidDocumentSchemaVersion': 'The document schema version is not supported.',
            'InvalidDocumentType': 'The specified document type is not valid.',
            'InvalidInstanceId': 'The specified instance ID is not valid.',
            'InvalidKeyId': 'The specified KMS key ID is not valid.',
            'InvalidNextToken': 'The specified next token is not valid.',
            'InvalidOutputFolder': 'The specified output folder is not valid.',
            'InvalidOutputLocation': 'The specified output location is not valid.',
            'InvalidParameters': f'Invalid parameters: {error_message}',
            'InvalidResourceId': 'The specified resource ID is not valid.',
            'InvalidResourceType': 'The specified resource type is not valid.',
            'InvalidRole': 'The specified IAM role is not valid.',
            'InvalidTarget': 'The specified target is not valid.',
            'InvalidTypeNameException': 'The specified type name is not valid.',
            'MaxDocumentSizeExceeded': 'The document size exceeds the maximum allowed limit.',
            'ParameterLimitExceeded': 'The number of parameters exceeds the limit.',
            'ParameterMaxVersionLimitExceeded': 'The parameter has reached the maximum number of versions.',
            'ParameterNotFound': 'The specified parameter was not found.',
            'ParameterVersionNotFound': 'The specified parameter version was not found.',
            'PoliciesLimitExceeded': 'The number of policies exceeds the limit.',
            'ResourceDataSyncAlreadyExistsException': 'A resource data sync with this name already exists.',
            'ResourceDataSyncNotFoundException': 'The specified resource data sync was not found.',
            'ResourceInUseException': 'The resource is currently in use and cannot be deleted.',
            'ResourceLimitExceededException': 'The resource limit has been exceeded.',
            'ServiceSettingNotFound': 'The specified service setting was not found.',
            'TooManyTagsError': 'Too many tags specified. Please reduce the number of tags.',
            'TooManyUpdates': 'Too many concurrent updates. Please wait and try again.',
            'UnsupportedCalendarException': 'The specified calendar type is not supported.',
            'UnsupportedFeatureRequiredException': 'This operation requires a feature that is not supported.',
            'UnsupportedInventoryItemContextException': 'The inventory item context is not supported.',
            'UnsupportedInventorySchemaVersionException': 'The inventory schema version is not supported.',
            'UnsupportedOperatingSystem': 'The operating system is not supported for this operation.',
            'UnsupportedParameterType': 'The parameter type is not supported.',
            'UnsupportedPlatformType': 'The platform type is not supported.',
        }

        friendly_message = error_mappings.get(error_code, error_message)

        return SsmClientError(friendly_message, error_code=error_code, status_code=status_code)

    # Handle other common exceptions
    if isinstance(error, ValueError):
        return SsmValidationError(f'Validation error: {str(error)}')

    if isinstance(error, PermissionError):
        return SsmPermissionError(f'Permission error: {str(error)}')

    # Generic error handling
    return SsmMcpError(f'Unexpected error: {str(error)}')


def log_error(error: Exception, operation: str = None) -> None:
    """Log an error with appropriate context.

    Args:
        error: The exception to log
        operation: Optional operation name for context
    """
    if operation:
        logger.error(f'Error in {operation}: {error}')
    else:
        logger.error(f'Error: {error}')

    # Log additional details for ClientError
    if isinstance(error, ClientError):
        error_details = {
            'error_code': error.response.get('Error', {}).get('Code'),
            'error_message': error.response.get('Error', {}).get('Message'),
            'request_id': error.response.get('ResponseMetadata', {}).get('RequestId'),
            'http_status_code': error.response.get('ResponseMetadata', {}).get('HTTPStatusCode'),
        }
        logger.error(f'AWS error details: {error_details}')


def create_error_response(error: Exception, operation: str = None) -> Dict[str, Any]:
    """Create a standardized error response dictionary.

    Args:
        error: The exception
        operation: Optional operation name

    Returns:
        Dict containing error information
    """
    ssm_error = handle_ssm_error(error)

    response = {'success': False, 'error': str(ssm_error), 'error_type': type(ssm_error).__name__}

    if hasattr(ssm_error, 'error_code') and ssm_error.error_code:
        response['error_code'] = ssm_error.error_code

    if hasattr(ssm_error, 'status_code') and ssm_error.status_code:
        response['status_code'] = ssm_error.status_code

    if operation:
        response['operation'] = operation

    return response
