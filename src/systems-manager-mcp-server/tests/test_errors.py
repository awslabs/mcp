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

"""Tests for error handling."""

import os
import sys
from botocore.exceptions import ClientError, NoCredentialsError
from unittest.mock import patch


sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from awslabs.systems_manager_mcp_server.errors import (
    SsmClientError,
    SsmMcpError,
    SsmPermissionError,
    SsmValidationError,
    create_error_response,
    handle_ssm_error,
    log_error,
)


class TestSsmErrors:
    """Test SSM error classes."""

    def test_ssm_mcp_error(self):
        """Test SsmMcpError base exception."""
        error = SsmMcpError('Test error')
        assert str(error) == 'Test error'
        assert isinstance(error, Exception)

    def test_ssm_client_error(self):
        """Test SsmClientError with error code and status code."""
        error = SsmClientError('Client error', error_code='InvalidDocument', status_code=400)
        assert str(error) == 'Client error'
        assert error.error_code == 'InvalidDocument'
        assert error.status_code == 400

    def test_ssm_validation_error(self):
        """Test SsmValidationError."""
        error = SsmValidationError('Validation failed')
        assert str(error) == 'Validation failed'
        assert isinstance(error, SsmMcpError)

    def test_ssm_permission_error(self):
        """Test SsmPermissionError."""
        error = SsmPermissionError('Permission denied')
        assert str(error) == 'Permission denied'
        assert isinstance(error, SsmMcpError)


class TestHandleSsmError:
    """Test handle_ssm_error function."""

    def test_handle_existing_ssm_error(self):
        """Test handling existing SsmMcpError."""
        original_error = SsmClientError('Original error')
        result = handle_ssm_error(original_error)
        assert result is original_error

    def test_handle_no_credentials_error(self):
        """Test handling NoCredentialsError."""
        error = NoCredentialsError()
        result = handle_ssm_error(error)
        assert isinstance(result, SsmClientError)
        assert 'AWS credentials not found' in str(result)
        assert result.error_code == 'NoCredentialsError'

    def test_handle_client_error_document_already_exists(self):
        """Test handling ClientError with DocumentAlreadyExists."""
        client_error = ClientError(
            error_response={
                'Error': {
                    'Code': 'DocumentAlreadyExists',
                    'Message': 'The specified document already exists.',
                },
                'ResponseMetadata': {'HTTPStatusCode': 400, 'RequestId': 'test-request-id'},
            },
            operation_name='CreateDocument',
        )
        result = handle_ssm_error(client_error)
        assert isinstance(result, SsmClientError)
        assert 'already exists' in str(result)
        assert result.error_code == 'DocumentAlreadyExists'
        assert result.status_code == 400

    def test_handle_client_error_access_denied(self):
        """Test handling ClientError with AccessDenied."""
        client_error = ClientError(
            error_response={
                'Error': {'Code': 'AccessDenied', 'Message': 'User is not authorized'}
            },
            operation_name='ListDocuments',
        )
        result = handle_ssm_error(client_error)
        assert isinstance(result, SsmClientError)
        assert 'Access denied' in str(result)
        assert result.error_code == 'AccessDenied'

    def test_handle_client_error_unknown_code(self):
        """Test handling ClientError with unknown error code."""
        client_error = ClientError(
            error_response={
                'Error': {'Code': 'UnknownError', 'Message': 'Unknown error occurred'}
            },
            operation_name='TestOperation',
        )
        result = handle_ssm_error(client_error)
        assert isinstance(result, SsmClientError)
        assert 'Unknown error occurred' in str(result)
        assert result.error_code == 'UnknownError'

    def test_handle_value_error(self):
        """Test handling ValueError."""
        error = ValueError('Invalid value')
        result = handle_ssm_error(error)
        assert isinstance(result, SsmValidationError)
        assert 'Validation error: Invalid value' in str(result)

    def test_handle_permission_error(self):
        """Test handling PermissionError."""
        error = PermissionError('Permission denied')
        result = handle_ssm_error(error)
        assert isinstance(result, SsmPermissionError)
        assert 'Permission error: Permission denied' in str(result)

    def test_handle_generic_error(self):
        """Test handling generic Exception."""
        error = Exception('Generic error')
        result = handle_ssm_error(error)
        assert isinstance(result, SsmMcpError)
        assert 'Unexpected error: Generic error' in str(result)


class TestLogError:
    """Test log_error function."""

    @patch('awslabs.systems_manager_mcp_server.errors.logger')
    def test_log_error_with_operation(self, mock_logger):
        """Test log_error with operation name."""
        error = Exception('Test error')
        log_error(error, 'test operation')
        mock_logger.error.assert_called_with('Error in test operation: Test error')

    @patch('awslabs.systems_manager_mcp_server.errors.logger')
    def test_log_error_without_operation(self, mock_logger):
        """Test log_error without operation name."""
        error = Exception('Test error')
        log_error(error)
        mock_logger.error.assert_called_with('Error: Test error')

    @patch('awslabs.systems_manager_mcp_server.errors.logger')
    def test_log_error_with_client_error(self, mock_logger):
        """Test log_error with ClientError logs additional details."""
        client_error = ClientError(
            error_response={
                'Error': {'Code': 'TestError', 'Message': 'Test message'},
                'ResponseMetadata': {'RequestId': 'test-request-id', 'HTTPStatusCode': 400},
            },
            operation_name='TestOperation',
        )
        log_error(client_error, 'test operation')

        # Verify main error log
        mock_logger.error.assert_any_call(
            'Error in test operation: An error occurred (TestError) when calling the TestOperation operation: Test message'
        )

        # Verify additional details log
        expected_details = {
            'error_code': 'TestError',
            'error_message': 'Test message',
            'request_id': 'test-request-id',
            'http_status_code': 400,
        }
        mock_logger.error.assert_any_call(f'AWS error details: {expected_details}')


class TestCreateErrorResponse:
    """Test create_error_response function."""

    def test_create_error_response_basic(self):
        """Test create_error_response with basic error."""
        error = Exception('Test error')
        response = create_error_response(error)

        assert response['success'] is False
        assert response['error'] == 'Unexpected error: Test error'
        assert response['error_type'] == 'SsmMcpError'

    def test_create_error_response_with_operation(self):
        """Test create_error_response with operation name."""
        error = ValueError('Invalid input')
        response = create_error_response(error, 'test operation')

        assert response['success'] is False
        assert response['error'] == 'Validation error: Invalid input'
        assert response['error_type'] == 'SsmValidationError'
        assert response['operation'] == 'test operation'

    def test_create_error_response_with_client_error(self):
        """Test create_error_response with ClientError."""
        client_error = ClientError(
            error_response={
                'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'},
                'ResponseMetadata': {'HTTPStatusCode': 403},
            },
            operation_name='TestOperation',
        )
        response = create_error_response(client_error)

        assert response['success'] is False
        assert 'Access denied' in response['error']
        assert response['error_type'] == 'SsmClientError'
        assert response['error_code'] == 'AccessDenied'
        assert response['status_code'] == 403

    def test_create_error_response_with_ssm_client_error(self):
        """Test create_error_response with SsmClientError."""
        error = SsmClientError('Custom error', error_code='CustomError', status_code=500)
        response = create_error_response(error)

        assert response['success'] is False
        assert response['error'] == 'Custom error'
        assert response['error_type'] == 'SsmClientError'
        assert response['error_code'] == 'CustomError'
        assert response['status_code'] == 500
