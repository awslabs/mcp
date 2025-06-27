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

"""Tests for inline policy management functionality."""

import json
import pytest
from awslabs.iam_mcp_server.context import Context
from awslabs.iam_mcp_server.errors import IamClientError, IamValidationError
from awslabs.iam_mcp_server.models import InlinePolicyListResponse, InlinePolicyResponse
from awslabs.iam_mcp_server.server import (
    delete_role_policy,
    delete_user_policy,
    get_role_policy,
    get_user_policy,
    list_role_policies,
    list_user_policies,
    put_role_policy,
    put_user_policy,
)
from botocore.exceptions import ClientError as BotoClientError
from unittest.mock import Mock, patch


@pytest.fixture
def sample_policy_document():
    """Sample policy document for testing."""
    return {
        'Version': '2012-10-17',
        'Statement': [
            {
                'Effect': 'Allow',
                'Action': 's3:GetObject',
                'Resource': 'arn:aws:s3:::example-bucket/*',
            }
        ],
    }


@pytest.fixture
def sample_policy_document_str():
    """Sample policy document as string for testing."""
    return json.dumps(
        {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Effect': 'Allow',
                    'Action': 's3:GetObject',
                    'Resource': 'arn:aws:s3:::example-bucket/*',
                }
            ],
        }
    )


class TestUserInlinePolicies:
    """Test user inline policy management."""

    @patch('awslabs.iam_mcp_server.server.get_iam_client')
    async def test_put_user_policy_success_dict(self, mock_get_client, sample_policy_document):
        """Test successful creation of user inline policy with dict input."""
        # Setup
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        Context.initialize(readonly=False)

        # Execute
        result = await put_user_policy(
            user_name='test-user',
            policy_name='test-policy',
            policy_document=sample_policy_document,
        )

        # Verify
        assert isinstance(result, InlinePolicyResponse)
        assert result.policy_name == 'test-policy'
        assert result.user_name == 'test-user'
        assert 'Successfully created/updated' in result.message

        mock_client.put_user_policy.assert_called_once_with(
            UserName='test-user',
            PolicyName='test-policy',
            PolicyDocument=json.dumps(sample_policy_document),
        )

    @patch('awslabs.iam_mcp_server.server.get_iam_client')
    async def test_put_user_policy_success_string(
        self, mock_get_client, sample_policy_document_str
    ):
        """Test successful creation of user inline policy with string input."""
        # Setup
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        Context.initialize(readonly=False)

        # Execute
        result = await put_user_policy(
            user_name='test-user',
            policy_name='test-policy',
            policy_document=sample_policy_document_str,
        )

        # Verify
        assert isinstance(result, InlinePolicyResponse)
        assert result.policy_name == 'test-policy'
        assert result.user_name == 'test-user'

        mock_client.put_user_policy.assert_called_once_with(
            UserName='test-user',
            PolicyName='test-policy',
            PolicyDocument=sample_policy_document_str,
        )

    @patch('awslabs.iam_mcp_server.server.get_iam_client')
    async def test_put_user_policy_readonly_mode(self, mock_get_client, sample_policy_document):
        """Test put_user_policy fails in readonly mode."""
        # Setup
        Context.initialize(readonly=True)

        # Execute & Verify
        with pytest.raises(IamClientError, match='read-only mode'):
            await put_user_policy(
                user_name='test-user',
                policy_name='test-policy',
                policy_document=sample_policy_document,
            )

    async def test_put_user_policy_validation_errors(self, sample_policy_document):
        """Test put_user_policy validation errors."""
        Context.initialize(readonly=False)

        # Test missing user name
        with pytest.raises(IamValidationError, match='User name and policy name are required'):
            await put_user_policy(
                user_name='', policy_name='test-policy', policy_document=sample_policy_document
            )

        # Test missing policy name
        with pytest.raises(IamValidationError, match='User name and policy name are required'):
            await put_user_policy(
                user_name='test-user', policy_name='', policy_document=sample_policy_document
            )

        # Test invalid JSON
        with pytest.raises(IamValidationError, match='Invalid JSON'):
            await put_user_policy(
                user_name='test-user', policy_name='test-policy', policy_document='invalid-json'
            )

    @patch('awslabs.iam_mcp_server.server.get_iam_client')
    async def test_get_user_policy_success(self, mock_get_client, sample_policy_document_str):
        """Test successful retrieval of user inline policy."""
        # Setup
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.get_user_policy.return_value = {
            'UserName': 'test-user',
            'PolicyName': 'test-policy',
            'PolicyDocument': sample_policy_document_str,
        }

        # Execute
        result = await get_user_policy(user_name='test-user', policy_name='test-policy')

        # Verify
        assert isinstance(result, InlinePolicyResponse)
        assert result.policy_name == 'test-policy'
        assert result.user_name == 'test-user'
        assert result.policy_document == sample_policy_document_str

        mock_client.get_user_policy.assert_called_once_with(
            UserName='test-user', PolicyName='test-policy'
        )

    async def test_get_user_policy_validation_errors(self):
        """Test get_user_policy validation errors."""
        # Test missing user name
        with pytest.raises(IamValidationError, match='User name and policy name are required'):
            await get_user_policy(user_name='', policy_name='test-policy')

        # Test missing policy name
        with pytest.raises(IamValidationError, match='User name and policy name are required'):
            await get_user_policy(user_name='test-user', policy_name='')

    @patch('awslabs.iam_mcp_server.server.get_iam_client')
    async def test_delete_user_policy_success(self, mock_get_client):
        """Test successful deletion of user inline policy."""
        # Setup
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        Context.initialize(readonly=False)

        # Execute
        result = await delete_user_policy(user_name='test-user', policy_name='test-policy')

        # Verify
        assert (
            result['message']
            == 'Successfully deleted inline policy test-policy from user test-user'
        )
        assert result['user_name'] == 'test-user'
        assert result['policy_name'] == 'test-policy'

        mock_client.delete_user_policy.assert_called_once_with(
            UserName='test-user', PolicyName='test-policy'
        )

    @patch('awslabs.iam_mcp_server.server.get_iam_client')
    async def test_delete_user_policy_readonly_mode(self, mock_get_client):
        """Test delete_user_policy fails in readonly mode."""
        # Setup
        Context.initialize(readonly=True)

        # Execute & Verify
        with pytest.raises(IamClientError, match='read-only mode'):
            await delete_user_policy(user_name='test-user', policy_name='test-policy')

    @patch('awslabs.iam_mcp_server.server.get_iam_client')
    async def test_list_user_policies_success(self, mock_get_client):
        """Test successful listing of user inline policies."""
        # Setup
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.list_user_policies.return_value = {
            'PolicyNames': ['policy1', 'policy2', 'policy3']
        }

        # Execute
        result = await list_user_policies(user_name='test-user')

        # Verify
        assert isinstance(result, InlinePolicyListResponse)
        assert result.policy_names == ['policy1', 'policy2', 'policy3']
        assert result.user_name == 'test-user'
        assert result.count == 3

        mock_client.list_user_policies.assert_called_once_with(UserName='test-user')

    async def test_list_user_policies_validation_error(self):
        """Test list_user_policies validation error."""
        with pytest.raises(IamValidationError, match='User name is required'):
            await list_user_policies(user_name='')


class TestRoleInlinePolicies:
    """Test role inline policy management."""

    @patch('awslabs.iam_mcp_server.server.get_iam_client')
    async def test_put_role_policy_success(self, mock_get_client, sample_policy_document):
        """Test successful creation of role inline policy."""
        # Setup
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        Context.initialize(readonly=False)

        # Execute
        result = await put_role_policy(
            role_name='test-role',
            policy_name='test-policy',
            policy_document=sample_policy_document,
        )

        # Verify
        assert isinstance(result, InlinePolicyResponse)
        assert result.policy_name == 'test-policy'
        assert result.role_name == 'test-role'
        assert 'Successfully created/updated' in result.message

        mock_client.put_role_policy.assert_called_once_with(
            RoleName='test-role',
            PolicyName='test-policy',
            PolicyDocument=json.dumps(sample_policy_document),
        )

    @patch('awslabs.iam_mcp_server.server.get_iam_client')
    async def test_put_role_policy_readonly_mode(self, mock_get_client, sample_policy_document):
        """Test put_role_policy fails in readonly mode."""
        # Setup
        Context.initialize(readonly=True)

        # Execute & Verify
        with pytest.raises(IamClientError, match='read-only mode'):
            await put_role_policy(
                role_name='test-role',
                policy_name='test-policy',
                policy_document=sample_policy_document,
            )

    async def test_put_role_policy_validation_errors(self, sample_policy_document):
        """Test put_role_policy validation errors."""
        Context.initialize(readonly=False)

        # Test missing role name
        with pytest.raises(IamValidationError, match='Role name and policy name are required'):
            await put_role_policy(
                role_name='', policy_name='test-policy', policy_document=sample_policy_document
            )

        # Test missing policy name
        with pytest.raises(IamValidationError, match='Role name and policy name are required'):
            await put_role_policy(
                role_name='test-role', policy_name='', policy_document=sample_policy_document
            )

    @patch('awslabs.iam_mcp_server.server.get_iam_client')
    async def test_get_role_policy_success(self, mock_get_client, sample_policy_document_str):
        """Test successful retrieval of role inline policy."""
        # Setup
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.get_role_policy.return_value = {
            'RoleName': 'test-role',
            'PolicyName': 'test-policy',
            'PolicyDocument': sample_policy_document_str,
        }

        # Execute
        result = await get_role_policy(role_name='test-role', policy_name='test-policy')

        # Verify
        assert isinstance(result, InlinePolicyResponse)
        assert result.policy_name == 'test-policy'
        assert result.role_name == 'test-role'
        assert result.policy_document == sample_policy_document_str

        mock_client.get_role_policy.assert_called_once_with(
            RoleName='test-role', PolicyName='test-policy'
        )

    @patch('awslabs.iam_mcp_server.server.get_iam_client')
    async def test_delete_role_policy_success(self, mock_get_client):
        """Test successful deletion of role inline policy."""
        # Setup
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        Context.initialize(readonly=False)

        # Execute
        result = await delete_role_policy(role_name='test-role', policy_name='test-policy')

        # Verify
        assert (
            result['message']
            == 'Successfully deleted inline policy test-policy from role test-role'
        )
        assert result['role_name'] == 'test-role'
        assert result['policy_name'] == 'test-policy'

        mock_client.delete_role_policy.assert_called_once_with(
            RoleName='test-role', PolicyName='test-policy'
        )

    @patch('awslabs.iam_mcp_server.server.get_iam_client')
    async def test_list_role_policies_success(self, mock_get_client):
        """Test successful listing of role inline policies."""
        # Setup
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.list_role_policies.return_value = {'PolicyNames': ['policy1', 'policy2']}

        # Execute
        result = await list_role_policies(role_name='test-role')

        # Verify
        assert isinstance(result, InlinePolicyListResponse)
        assert result.policy_names == ['policy1', 'policy2']
        assert result.role_name == 'test-role'
        assert result.count == 2

        mock_client.list_role_policies.assert_called_once_with(RoleName='test-role')


class TestInlinePolicyErrorHandling:
    """Test error handling for inline policy operations."""

    @patch('awslabs.iam_mcp_server.server.get_iam_client')
    async def test_put_user_policy_aws_error(self, mock_get_client, sample_policy_document):
        """Test AWS error handling in put_user_policy."""
        # Setup
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.put_user_policy.side_effect = BotoClientError(
            error_response={'Error': {'Code': 'NoSuchEntity', 'Message': 'User not found'}},
            operation_name='PutUserPolicy',
        )
        Context.initialize(readonly=False)

        # Execute & Verify
        with pytest.raises(Exception):  # Will be handled by handle_iam_error
            await put_user_policy(
                user_name='nonexistent-user',
                policy_name='test-policy',
                policy_document=sample_policy_document,
            )

    @patch('awslabs.iam_mcp_server.server.get_iam_client')
    async def test_get_user_policy_not_found(self, mock_get_client):
        """Test get_user_policy when policy doesn't exist."""
        # Setup
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.get_user_policy.side_effect = BotoClientError(
            error_response={'Error': {'Code': 'NoSuchEntity', 'Message': 'Policy not found'}},
            operation_name='GetUserPolicy',
        )

        # Execute & Verify
        with pytest.raises(Exception):  # Will be handled by handle_iam_error
            await get_user_policy(user_name='test-user', policy_name='nonexistent-policy')

    @patch('awslabs.iam_mcp_server.server.get_iam_client')
    async def test_delete_user_policy_not_found(self, mock_get_client):
        """Test delete_user_policy when policy doesn't exist."""
        # Setup
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.delete_user_policy.side_effect = BotoClientError(
            error_response={'Error': {'Code': 'NoSuchEntity', 'Message': 'Policy not found'}},
            operation_name='DeleteUserPolicy',
        )
        Context.initialize(readonly=False)

        # Execute & Verify
        with pytest.raises(Exception):  # Will be handled by handle_iam_error
            await delete_user_policy(user_name='test-user', policy_name='nonexistent-policy')


class TestErrorHandlingCoverage:
    """Test error handling for coverage of specific lines."""

    @patch('awslabs.iam_mcp_server.server.get_iam_client')
    async def test_get_managed_policy_document_error_handling(self, mock_get_client):
        """Test error handling in get_managed_policy_document (lines 608-611)."""
        from awslabs.iam_mcp_server.server import get_managed_policy_document

        mock_client = Mock()
        mock_get_client.return_value = mock_client

        # Mock a ClientError to trigger the exception handler
        mock_client.get_policy_version.side_effect = BotoClientError(
            error_response={'Error': {'Code': 'NoSuchEntity', 'Message': 'Policy not found'}},
            operation_name='GetPolicyVersion',
        )

        with pytest.raises(Exception):  # Will be handled by handle_iam_error
            await get_managed_policy_document(
                policy_arn='arn:aws:iam::123456789012:policy/NonExistentPolicy'
            )

    @patch('awslabs.iam_mcp_server.server.get_iam_client')
    async def test_put_user_policy_invalid_json_error(self, mock_get_client):
        """Test put_user_policy with invalid JSON (lines 1065-1070)."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        Context.initialize(readonly=False)

        with pytest.raises(IamValidationError, match='Invalid JSON in policy_document'):
            await put_user_policy(
                user_name='testuser', policy_name='TestPolicy', policy_document='invalid json'
            )

    @patch('awslabs.iam_mcp_server.server.get_iam_client')
    async def test_put_role_policy_invalid_json_error(self, mock_get_client):
        """Test put_role_policy with invalid JSON (lines 1065-1070)."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        Context.initialize(readonly=False)

        with pytest.raises(IamValidationError, match='Invalid JSON in policy_document'):
            await put_role_policy(
                role_name='testrole', policy_name='TestPolicy', policy_document='invalid json'
            )

    @patch('awslabs.iam_mcp_server.server.get_iam_client')
    async def test_get_user_policy_exception_handling(self, mock_get_client):
        """Test exception handling in get_user_policy (lines 1130-1133)."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client

        # Mock a generic exception to trigger the exception handler
        mock_client.get_user_policy.side_effect = Exception('Generic error')

        with pytest.raises(Exception):  # Will be handled by handle_iam_error
            await get_user_policy(user_name='testuser', policy_name='TestPolicy')

    @patch('awslabs.iam_mcp_server.server.get_iam_client')
    async def test_get_role_policy_exception_handling(self, mock_get_client):
        """Test exception handling in get_role_policy (lines 1130-1133)."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client

        # Mock a generic exception to trigger the exception handler
        mock_client.get_role_policy.side_effect = Exception('Generic error')

        with pytest.raises(Exception):  # Will be handled by handle_iam_error
            await get_role_policy(role_name='testrole', policy_name='TestPolicy')

    @patch('awslabs.iam_mcp_server.server.get_iam_client')
    async def test_delete_user_policy_exception_handling(self, mock_get_client):
        """Test exception handling in delete_user_policy (lines 1178-1181)."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        Context.initialize(readonly=False)

        # Mock a generic exception to trigger the exception handler
        mock_client.delete_user_policy.side_effect = Exception('Generic error')

        with pytest.raises(Exception):  # Will be handled by handle_iam_error
            await delete_user_policy(user_name='testuser', policy_name='TestPolicy')

    @patch('awslabs.iam_mcp_server.server.get_iam_client')
    async def test_delete_role_policy_exception_handling(self, mock_get_client):
        """Test exception handling in delete_role_policy (lines 1178-1181)."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        Context.initialize(readonly=False)

        # Mock a generic exception to trigger the exception handler
        mock_client.delete_role_policy.side_effect = Exception('Generic error')

        with pytest.raises(Exception):  # Will be handled by handle_iam_error
            await delete_role_policy(role_name='testrole', policy_name='TestPolicy')

    @patch('awslabs.iam_mcp_server.server.get_iam_client')
    async def test_list_user_policies_exception_handling(self, mock_get_client):
        """Test exception handling in list_user_policies (lines 1219-1222)."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client

        # Mock a generic exception to trigger the exception handler
        mock_client.list_user_policies.side_effect = Exception('Generic error')

        with pytest.raises(Exception):  # Will be handled by handle_iam_error
            await list_user_policies(user_name='testuser')

    @patch('awslabs.iam_mcp_server.server.get_iam_client')
    async def test_list_role_policies_exception_handling(self, mock_get_client):
        """Test exception handling in list_role_policies (lines 1219-1222)."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client

        # Mock a generic exception to trigger the exception handler
        mock_client.list_role_policies.side_effect = Exception('Generic error')

        with pytest.raises(Exception):  # Will be handled by handle_iam_error
            await list_role_policies(role_name='testrole')
