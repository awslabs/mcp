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

"""Tests for error handling in the AWS IAM MCP Server."""

from awslabs.iam_mcp_server.errors import (
    IamClientError,
    IamMcpError,
    IamPermissionError,
    IamResourceNotFoundError,
    IamValidationError,
    handle_iam_error,
)
from botocore.exceptions import ClientError as BotoClientError


def test_iam_validation_error():
    """Test IamValidationError initialization."""
    error = IamValidationError('Test validation error')
    assert str(error) == 'Test validation error'
    assert error.error_code == 'IamValidationError'


def test_handle_iam_error_entity_already_exists():
    """Test handle_iam_error with EntityAlreadyExists error."""
    boto_error = BotoClientError(
        error_response={
            'Error': {'Code': 'EntityAlreadyExists', 'Message': 'User already exists'}
        },
        operation_name='CreateUser',
    )

    result = handle_iam_error(boto_error)
    assert isinstance(result, IamClientError)
    assert 'Resource already exists' in str(result)


def test_handle_iam_error_entity_already_exists_exception():
    """Test handle_iam_error with EntityAlreadyExistsException error."""
    boto_error = BotoClientError(
        error_response={
            'Error': {'Code': 'EntityAlreadyExistsException', 'Message': 'Role already exists'}
        },
        operation_name='CreateRole',
    )

    result = handle_iam_error(boto_error)
    assert isinstance(result, IamClientError)
    assert 'Resource already exists' in str(result)


def test_handle_iam_error_invalid_input():
    """Test handle_iam_error with InvalidInput error."""
    boto_error = BotoClientError(
        error_response={'Error': {'Code': 'InvalidInput', 'Message': 'Invalid parameter'}},
        operation_name='CreateUser',
    )

    result = handle_iam_error(boto_error)
    assert isinstance(result, IamValidationError)
    assert 'Invalid input' in str(result)


def test_handle_iam_error_invalid_input_exception():
    """Test handle_iam_error with InvalidInputException error."""
    boto_error = BotoClientError(
        error_response={
            'Error': {'Code': 'InvalidInputException', 'Message': 'Invalid parameter'}
        },
        operation_name='CreateUser',
    )

    result = handle_iam_error(boto_error)
    assert isinstance(result, IamValidationError)
    assert 'Invalid input' in str(result)


def test_handle_iam_error_validation_exception():
    """Test handle_iam_error with ValidationException error."""
    boto_error = BotoClientError(
        error_response={'Error': {'Code': 'ValidationException', 'Message': 'Validation failed'}},
        operation_name='CreateUser',
    )

    result = handle_iam_error(boto_error)
    assert isinstance(result, IamValidationError)
    assert 'Invalid input' in str(result)


def test_handle_iam_error_limit_exceeded():
    """Test handle_iam_error with LimitExceeded error."""
    boto_error = BotoClientError(
        error_response={'Error': {'Code': 'LimitExceeded', 'Message': 'Limit exceeded'}},
        operation_name='CreateUser',
    )

    result = handle_iam_error(boto_error)
    assert isinstance(result, IamClientError)
    assert 'Limit exceeded' in str(result)


def test_handle_iam_error_limit_exceeded_exception():
    """Test handle_iam_error with LimitExceededException error."""
    boto_error = BotoClientError(
        error_response={'Error': {'Code': 'LimitExceededException', 'Message': 'Limit exceeded'}},
        operation_name='CreateUser',
    )

    result = handle_iam_error(boto_error)
    assert isinstance(result, IamClientError)
    assert 'Limit exceeded' in str(result)


def test_handle_iam_error_service_failure():
    """Test handle_iam_error with ServiceFailure error."""
    boto_error = BotoClientError(
        error_response={'Error': {'Code': 'ServiceFailure', 'Message': 'Service failure'}},
        operation_name='CreateUser',
    )

    result = handle_iam_error(boto_error)
    assert isinstance(result, IamMcpError)
    assert 'AWS service failure' in str(result)
    assert result.error_code == 'ServiceFailure'


def test_handle_iam_error_service_failure_exception():
    """Test handle_iam_error with ServiceFailureException error."""
    boto_error = BotoClientError(
        error_response={
            'Error': {'Code': 'ServiceFailureException', 'Message': 'Service failure'}
        },
        operation_name='CreateUser',
    )

    result = handle_iam_error(boto_error)
    assert isinstance(result, IamMcpError)
    assert 'AWS service failure' in str(result)
    assert result.error_code == 'ServiceFailure'


def test_handle_iam_error_throttling():
    """Test handle_iam_error with Throttling error."""
    boto_error = BotoClientError(
        error_response={'Error': {'Code': 'Throttling', 'Message': 'Request throttled'}},
        operation_name='CreateUser',
    )

    result = handle_iam_error(boto_error)
    assert isinstance(result, IamMcpError)
    assert 'Request throttled' in str(result)
    assert result.error_code == 'Throttling'


def test_handle_iam_error_throttling_exception():
    """Test handle_iam_error with ThrottlingException error."""
    boto_error = BotoClientError(
        error_response={'Error': {'Code': 'ThrottlingException', 'Message': 'Request throttled'}},
        operation_name='CreateUser',
    )

    result = handle_iam_error(boto_error)
    assert isinstance(result, IamMcpError)
    assert 'Request throttled' in str(result)
    assert result.error_code == 'Throttling'


def test_handle_iam_error_incomplete_signature():
    """Test handle_iam_error with IncompleteSignature error."""
    boto_error = BotoClientError(
        error_response={
            'Error': {'Code': 'IncompleteSignature', 'Message': 'Incomplete signature'}
        },
        operation_name='CreateUser',
    )

    result = handle_iam_error(boto_error)
    assert isinstance(result, IamClientError)
    assert 'Incomplete signature' in str(result)


def test_handle_iam_error_invalid_action():
    """Test handle_iam_error with InvalidAction error."""
    boto_error = BotoClientError(
        error_response={'Error': {'Code': 'InvalidAction', 'Message': 'Invalid action'}},
        operation_name='CreateUser',
    )

    result = handle_iam_error(boto_error)
    assert isinstance(result, IamClientError)
    assert 'Invalid action' in str(result)


def test_handle_iam_error_invalid_client_token_id():
    """Test handle_iam_error with InvalidClientTokenId error."""
    boto_error = BotoClientError(
        error_response={
            'Error': {'Code': 'InvalidClientTokenId', 'Message': 'Invalid client token'}
        },
        operation_name='CreateUser',
    )

    result = handle_iam_error(boto_error)
    assert isinstance(result, IamClientError)
    assert 'Invalid client token ID' in str(result)


def test_handle_iam_error_not_authorized():
    """Test handle_iam_error with NotAuthorized error."""
    boto_error = BotoClientError(
        error_response={'Error': {'Code': 'NotAuthorized', 'Message': 'Not authorized'}},
        operation_name='CreateUser',
    )

    result = handle_iam_error(boto_error)
    assert isinstance(result, IamPermissionError)
    assert 'Not authorized' in str(result)


def test_handle_iam_error_request_expired():
    """Test handle_iam_error with RequestExpired error."""
    boto_error = BotoClientError(
        error_response={'Error': {'Code': 'RequestExpired', 'Message': 'Request expired'}},
        operation_name='CreateUser',
    )

    result = handle_iam_error(boto_error)
    assert isinstance(result, IamClientError)
    assert 'Request expired' in str(result)


def test_handle_iam_error_signature_does_not_match():
    """Test handle_iam_error with SignatureDoesNotMatch error."""
    boto_error = BotoClientError(
        error_response={
            'Error': {'Code': 'SignatureDoesNotMatch', 'Message': 'Signature does not match'}
        },
        operation_name='CreateUser',
    )

    result = handle_iam_error(boto_error)
    assert isinstance(result, IamClientError)
    assert 'Signature does not match' in str(result)


def test_handle_iam_error_token_refresh_required():
    """Test handle_iam_error with TokenRefreshRequired error."""
    boto_error = BotoClientError(
        error_response={
            'Error': {'Code': 'TokenRefreshRequired', 'Message': 'Token refresh required'}
        },
        operation_name='CreateUser',
    )

    result = handle_iam_error(boto_error)
    assert isinstance(result, IamClientError)
    assert 'Token refresh required' in str(result)


# Group Management Error Tests


def test_handle_iam_error_group_already_exists():
    """Test handling of EntityAlreadyExists error for groups."""
    boto_error = BotoClientError(
        error_response={
            'Error': {'Code': 'EntityAlreadyExists', 'Message': 'Group TestGroup already exists'}
        },
        operation_name='CreateGroup',
    )

    result = handle_iam_error(boto_error)
    assert isinstance(result, IamClientError)
    assert 'Group TestGroup already exists' in str(result)


def test_handle_iam_error_group_not_found():
    """Test handling of NoSuchEntity error for groups."""
    boto_error = BotoClientError(
        error_response={
            'Error': {'Code': 'NoSuchEntity', 'Message': 'Group TestGroup does not exist'}
        },
        operation_name='GetGroup',
    )

    result = handle_iam_error(boto_error)
    assert isinstance(result, IamResourceNotFoundError)
    assert 'Group TestGroup does not exist' in str(result)


def test_handle_iam_error_group_delete_conflict():
    """Test handling of DeleteConflict error for groups."""
    boto_error = BotoClientError(
        error_response={
            'Error': {
                'Code': 'DeleteConflict',
                'Message': 'Cannot delete group TestGroup because it has attached policies',
            }
        },
        operation_name='DeleteGroup',
    )

    result = handle_iam_error(boto_error)
    assert isinstance(result, IamMcpError)
    assert 'Cannot delete group TestGroup' in str(result)


def test_handle_iam_error_group_policy_attachment():
    """Test handling of InvalidInput error for group policy attachment."""
    boto_error = BotoClientError(
        error_response={
            'Error': {
                'Code': 'InvalidInput',
                'Message': 'Policy arn:aws:iam::123456789012:policy/TestPolicy is not attachable',
            }
        },
        operation_name='AttachGroupPolicy',
    )

    result = handle_iam_error(boto_error)
    assert isinstance(result, IamValidationError)
    assert 'Policy arn:aws:iam::123456789012:policy/TestPolicy is not attachable' in str(result)


def test_handle_iam_error_user_not_in_group():
    """Test handling of NoSuchEntity error when removing user from group."""
    boto_error = BotoClientError(
        error_response={
            'Error': {
                'Code': 'NoSuchEntity',
                'Message': 'User TestUser is not in group TestGroup',
            }
        },
        operation_name='RemoveUserFromGroup',
    )

    result = handle_iam_error(boto_error)
    assert isinstance(result, IamResourceNotFoundError)
    assert 'User TestUser is not in group TestGroup' in str(result)
