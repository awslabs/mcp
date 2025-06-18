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

"""Tests for the errors module."""

from awslabs.elasticbeanstalk_mcp_server.errors import (
    ClientError,
    ServerError,
    handle_aws_api_error,
)
from unittest.mock import patch


class CustomException(Exception):
    """Custom exception class for testing."""

    def __init__(self, message, code):
        """Initialize with message and code."""
        self.response = {'Error': {'Code': code}}
        self.message = message
        super().__init__(message)

    def __str__(self):
        """Return the message."""
        return self.message


class TestHandleAwsApiError:
    """Test class for the handle_aws_api_error function."""

    def test_access_denied_error(self):
        """Test handling of AccessDenied errors."""
        # Arrange
        exception = CustomException('Access denied', 'AccessDeniedException')

        # Act
        result = handle_aws_api_error(exception)

        # Assert
        assert isinstance(result, ClientError)
        assert 'Access denied' in str(result)

    def test_incomplete_signature_error(self):
        """Test handling of IncompleteSignature errors."""
        # Arrange
        exception = CustomException(
            'IncompleteSignature: The request signature does not conform to AWS standards',
            'IncompleteSignature',
        )

        # Act
        result = handle_aws_api_error(exception)

        # Assert
        assert isinstance(result, ClientError)
        assert 'Incomplete signature' in str(result)

    def test_invalid_action_error(self):
        """Test handling of InvalidAction errors."""
        # Arrange
        exception = CustomException('InvalidAction: The action is invalid', 'InvalidAction')

        # Act
        result = handle_aws_api_error(exception)

        # Assert
        assert isinstance(result, ClientError)
        assert 'Invalid action' in str(result)

    def test_invalid_client_token_id_error(self):
        """Test handling of InvalidClientTokenId errors."""
        # Arrange
        exception = CustomException(
            'InvalidClientTokenId: The certificate or AWS access key ID provided does not exist',
            'InvalidClientTokenId',
        )

        # Act
        result = handle_aws_api_error(exception)

        # Assert
        assert isinstance(result, ClientError)
        assert 'Invalid client token id' in str(result)

    def test_not_authorized_error(self):
        """Test handling of NotAuthorized errors."""
        # Arrange
        exception = CustomException('NotAuthorized: You do not have permission', 'NotAuthorized')

        # Act
        result = handle_aws_api_error(exception)

        # Assert
        assert isinstance(result, ClientError)
        assert 'Not authorized' in str(result)

    def test_validation_exception_error(self):
        """Test handling of ValidationException errors."""
        # Arrange
        exception = CustomException(
            'ValidationException: Parameter validation failed', 'ValidationException'
        )

        # Act
        result = handle_aws_api_error(exception)

        # Assert
        assert isinstance(result, ClientError)
        assert 'Validation error' in str(result)

    def test_resource_not_found_exception_error(self):
        """Test handling of ResourceNotFoundException errors."""
        # Arrange
        exception = CustomException(
            'ResourceNotFoundException: Resource not found', 'ResourceNotFoundException'
        )

        # Act
        result = handle_aws_api_error(exception)

        # Assert
        assert isinstance(result, ClientError)
        assert 'Resource was not found' in str(result)

    def test_unsupported_action_exception_error(self):
        """Test handling of UnsupportedActionException errors."""
        # Arrange
        exception = CustomException(
            'UnsupportedActionException: This action is not supported',
            'UnsupportedActionException',
        )

        # Act
        result = handle_aws_api_error(exception)

        # Assert
        assert isinstance(result, ClientError)
        assert 'This action is not supported' in str(result)

    def test_invalid_patch_exception_error(self):
        """Test handling of InvalidPatchException errors."""
        # Arrange
        exception = CustomException(
            'InvalidPatchException: The patch document contains errors', 'InvalidPatchException'
        )

        # Act
        result = handle_aws_api_error(exception)

        # Assert
        assert isinstance(result, ClientError)
        assert 'The patch document provided contains errors' in str(result)

    def test_throttling_exception_error(self):
        """Test handling of ThrottlingException errors."""
        # Arrange
        exception = CustomException('ThrottlingException: Rate exceeded', 'ThrottlingException')

        # Act
        result = handle_aws_api_error(exception)

        # Assert
        assert isinstance(result, ClientError)
        assert 'Request was throttled' in str(result)

    def test_internal_failure_error(self):
        """Test handling of InternalFailure errors."""
        # Arrange
        exception = CustomException(
            'InternalFailure: An internal error occurred', 'InternalFailure'
        )

        # Act
        result = handle_aws_api_error(exception)

        # Assert
        assert isinstance(result, ServerError)
        assert 'Internal failure' in result.message

    def test_service_unavailable_error(self):
        """Test handling of ServiceUnavailable errors."""
        # Arrange
        exception = CustomException(
            'ServiceUnavailable: Service is unavailable', 'ServiceUnavailable'
        )

        # Act
        result = handle_aws_api_error(exception)

        # Assert
        assert isinstance(result, ServerError)
        assert 'Service unavailable' in result.message

    def test_unknown_error(self):
        """Test handling of unknown errors."""
        # Arrange
        exception = CustomException('Some unknown error occurred', 'UnknownError')

        # Act
        result = handle_aws_api_error(exception)

        # Assert
        assert isinstance(result, ClientError)
        assert 'An error occurred: Some unknown error occurred' in str(result)

    def test_error_without_response(self):
        """Test handling of errors without a response attribute."""
        # Arrange
        error_message = 'Generic error without response'
        exception = Exception(error_message)

        # Act
        result = handle_aws_api_error(exception)

        # Assert
        assert isinstance(result, ClientError)
        assert f'An error occurred: {error_message}' in str(result)


class TestClientError:
    """Test class for the ClientError exception."""

    def test_client_error_init(self):
        """Test initialization of ClientError."""
        # Arrange & Act
        error = ClientError('Test client error')

        # Assert
        assert str(error) == 'Test client error'
        assert error.type == 'client'
        assert error.message == 'Test client error'


class TestServerError:
    """Test class for the ServerError exception."""

    @patch('builtins.print')
    def test_server_error_init(self, mock_print):
        """Test initialization of ServerError."""
        # Arrange & Act
        error = ServerError('Test server error')

        # Assert
        assert str(error) == 'An internal error occurred while processing your request'
        assert error.type == 'server'
        assert error.message == 'Test server error'
        mock_print.assert_called_once_with('Test server error')
