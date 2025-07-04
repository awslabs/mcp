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

"""Tests for the AWS IAM MCP Server."""

import pytest
from awslabs.iam_mcp_server.aws_client import get_iam_client
from awslabs.iam_mcp_server.context import Context
from awslabs.iam_mcp_server.errors import (
    IamClientError,
    IamMcpError,
    IamPermissionError,
    IamResourceNotFoundError,
    IamValidationError,
    handle_iam_error,
)
from awslabs.iam_mcp_server.models import UsersListResponse
from botocore.exceptions import ClientError as BotoClientError
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch


def test_get_iam_client():
    """Test IAM client creation."""
    with patch('boto3.client') as mock_client:
        mock_client.return_value = Mock()
        client = get_iam_client()
        assert client is not None
        # Verify that boto3.client was called with 'iam' and a config object
        mock_client.assert_called_once()
        args, kwargs = mock_client.call_args
        assert args[0] == 'iam'
        assert 'config' in kwargs
        assert kwargs['config'].user_agent_extra == 'awslabs-iam-mcp-server/1.0.0'


def test_get_iam_client_with_region():
    """Test IAM client creation with region."""
    with patch('boto3.client') as mock_client:
        mock_client.return_value = Mock()
        client = get_iam_client(region='us-west-2')
        assert client is not None
        # Verify that boto3.client was called with 'iam', region, and config
        mock_client.assert_called_once()
        args, kwargs = mock_client.call_args
        assert args[0] == 'iam'
        assert kwargs['region_name'] == 'us-west-2'
        assert 'config' in kwargs
        assert kwargs['config'].user_agent_extra == 'awslabs-iam-mcp-server/1.0.0'


def test_handle_iam_error_access_denied():
    """Test handling of AccessDenied error."""
    error_response = {
        'Error': {
            'Code': 'AccessDenied',
            'Message': 'User is not authorized to perform this action',
        }
    }
    boto_error = BotoClientError(error_response, 'GetUser')

    handled_error = handle_iam_error(boto_error)

    assert isinstance(handled_error, IamPermissionError)
    assert 'Access denied' in str(handled_error)


def test_handle_iam_error_no_such_entity():
    """Test handling of NoSuchEntity error."""
    error_response = {'Error': {'Code': 'NoSuchEntity', 'Message': 'The user does not exist'}}
    boto_error = BotoClientError(error_response, 'GetUser')

    handled_error = handle_iam_error(boto_error)

    assert isinstance(handled_error, IamResourceNotFoundError)
    assert 'Resource not found' in str(handled_error)


def test_context_initialization():
    """Test Context initialization."""
    Context.initialize(readonly=True, region='us-east-1')

    assert Context.is_readonly() is True
    assert Context.get_region() == 'us-east-1'


def test_context_readonly_mode():
    """Test Context readonly mode."""
    Context.initialize(readonly=False)
    assert Context.is_readonly() is False

    Context.initialize(readonly=True)
    assert Context.is_readonly() is True


@pytest.mark.asyncio
async def test_list_users_mock():
    """Test list_users function with mocked IAM client."""
    from awslabs.iam_mcp_server.server import list_users

    mock_response = {
        'Users': [
            {
                'UserName': 'test-user',
                'UserId': 'AIDACKCEVSQ6C2EXAMPLE',
                'Arn': 'arn:aws:iam::123456789012:user/test-user',
                'Path': '/',
                'CreateDate': datetime(2023, 1, 1),
            }
        ],
        'IsTruncated': False,
    }

    mock_ctx = AsyncMock()

    with patch('awslabs.iam_mcp_server.server.get_iam_client') as mock_get_client:
        mock_client = Mock()
        mock_client.list_users.return_value = mock_response
        mock_get_client.return_value = mock_client

        result = await list_users(mock_ctx)

        assert isinstance(result, UsersListResponse)
        assert len(result.users) == 1
        assert result.users[0].user_name == 'test-user'
        assert result.count == 1
        assert result.is_truncated is False


@pytest.mark.asyncio
async def test_create_user_readonly_mode():
    """Test create_user function in readonly mode."""
    from awslabs.iam_mcp_server.server import create_user

    # Set readonly mode
    Context.initialize(readonly=True)

    mock_ctx = AsyncMock()

    with pytest.raises(IamClientError) as exc_info:
        await create_user(mock_ctx, user_name='test-user')

    assert 'read-only mode' in str(exc_info.value)


@pytest.mark.asyncio
async def test_create_user_success():
    """Test successful user creation."""
    from awslabs.iam_mcp_server.models import CreateUserResponse
    from awslabs.iam_mcp_server.server import create_user

    # Disable readonly mode
    Context.initialize(readonly=False)

    mock_response = {
        'User': {
            'UserName': 'new-user',
            'UserId': 'AIDACKCEVSQ6C2EXAMPLE',
            'Arn': 'arn:aws:iam::123456789012:user/new-user',
            'Path': '/',
            'CreateDate': datetime(2023, 1, 1),
        }
    }

    mock_ctx = AsyncMock()

    with patch('awslabs.iam_mcp_server.server.get_iam_client') as mock_get_client:
        mock_client = Mock()
        mock_client.create_user.return_value = mock_response
        mock_get_client.return_value = mock_client

        result = await create_user(mock_ctx, user_name='new-user')

        assert isinstance(result, CreateUserResponse)
        assert result.user.user_name == 'new-user'
        assert 'Successfully created user: new-user' in result.message


# Additional tests for better coverage


def test_get_iam_client_error():
    """Test IAM client creation error handling."""
    with patch('boto3.client') as mock_client:
        mock_client.side_effect = Exception('AWS credentials not found')

        with pytest.raises(Exception) as exc_info:
            get_iam_client()

        assert 'Failed to create IAM client' in str(exc_info.value)


def test_get_aws_client():
    """Test generic AWS client creation."""
    from awslabs.iam_mcp_server.aws_client import get_aws_client

    with patch('boto3.client') as mock_client:
        mock_client.return_value = Mock()
        client = get_aws_client('s3')
        assert client is not None
        # Verify that boto3.client was called with 's3' and a config object
        mock_client.assert_called_once()
        args, kwargs = mock_client.call_args
        assert args[0] == 's3'
        assert 'config' in kwargs
        assert kwargs['config'].user_agent_extra == 'awslabs-iam-mcp-server/1.0.0'


def test_get_aws_client_with_region():
    """Test generic AWS client creation with region."""
    from awslabs.iam_mcp_server.aws_client import get_aws_client

    with patch('boto3.client') as mock_client:
        mock_client.return_value = Mock()
        client = get_aws_client('ec2', region='eu-west-1')
        assert client is not None
        # Verify that boto3.client was called with correct arguments
        mock_client.assert_called_once()
        args, kwargs = mock_client.call_args
        assert args[0] == 'ec2'
        assert kwargs['region_name'] == 'eu-west-1'
        assert 'config' in kwargs


def test_get_aws_client_error():
    """Test generic AWS client creation error handling."""
    from awslabs.iam_mcp_server.aws_client import get_aws_client

    with patch('boto3.client') as mock_client:
        mock_client.side_effect = Exception('Service not available')

        with pytest.raises(Exception) as exc_info:
            get_aws_client('invalid-service')

        assert 'Failed to create invalid-service client' in str(exc_info.value)


def test_context_get_region():
    """Test Context.get_region method."""
    # Test when no region is set
    Context._region = None
    assert Context.get_region() is None

    # Test when region is set
    Context._region = 'us-east-1'
    assert Context.get_region() == 'us-east-1'


def test_handle_iam_error_throttling():
    """Test handling of throttling errors."""
    from awslabs.iam_mcp_server.errors import IamMcpError

    error = BotoClientError(
        error_response={'Error': {'Code': 'Throttling', 'Message': 'Rate exceeded'}},
        operation_name='ListUsers',
    )

    result = handle_iam_error(error)
    assert isinstance(result, IamMcpError)
    assert 'Rate exceeded' in str(result)


def test_handle_iam_error_invalid_user_type():
    """Test handling of InvalidUserType errors."""
    from awslabs.iam_mcp_server.errors import IamMcpError

    error = BotoClientError(
        error_response={'Error': {'Code': 'InvalidUserType', 'Message': 'Invalid user type'}},
        operation_name='CreateUser',
    )

    result = handle_iam_error(error)
    assert isinstance(result, IamMcpError)
    assert 'Invalid user type' in str(result)


def test_handle_iam_error_generic():
    """Test handling of generic errors."""
    from awslabs.iam_mcp_server.errors import IamMcpError

    error = Exception('Generic error')

    result = handle_iam_error(error)
    assert isinstance(result, IamMcpError)
    assert 'Generic error' in str(result)


@pytest.mark.asyncio
async def test_list_roles():
    """Test list_roles function."""
    from awslabs.iam_mcp_server.server import list_roles

    mock_response = {
        'Roles': [
            {
                'RoleName': 'test-role',
                'RoleId': 'AROA123456789EXAMPLE',
                'Arn': 'arn:aws:iam::123456789012:role/test-role',
                'Path': '/',
                'CreateDate': datetime(2023, 1, 1),
                'AssumeRolePolicyDocument': '%7B%22Version%22%3A%222012-10-17%22%7D',
            }
        ]
    }

    with patch('awslabs.iam_mcp_server.server.get_iam_client') as mock_get_client:
        mock_client = Mock()
        mock_client.list_roles.return_value = mock_response
        mock_get_client.return_value = mock_client

        result = await list_roles()

        assert len(result['Roles']) == 1
        assert result['Roles'][0]['RoleName'] == 'test-role'


@pytest.mark.asyncio
async def test_list_policies():
    """Test list_policies function."""
    from awslabs.iam_mcp_server.server import list_policies

    mock_response = {
        'Policies': [
            {
                'PolicyName': 'test-policy',
                'PolicyId': 'ANPA123456789EXAMPLE',
                'Arn': 'arn:aws:iam::123456789012:policy/test-policy',
                'Path': '/',
                'DefaultVersionId': 'v1',
                'AttachmentCount': 0,
                'PermissionsBoundaryUsageCount': 0,
                'IsAttachable': True,
                'Description': 'Test policy',
                'CreateDate': datetime(2023, 1, 1),
                'UpdateDate': datetime(2023, 1, 1),
            }
        ]
    }

    with patch('awslabs.iam_mcp_server.server.get_iam_client') as mock_get_client:
        mock_client = Mock()
        mock_client.list_policies.return_value = mock_response
        mock_get_client.return_value = mock_client

        result = await list_policies()

        assert len(result['Policies']) == 1
        assert result['Policies'][0]['PolicyName'] == 'test-policy'


@pytest.mark.asyncio
async def test_get_managed_policy_document():
    """Test get_managed_policy_document function."""
    from awslabs.iam_mcp_server.server import get_managed_policy_document

    mock_policy_document = {
        'Version': '2012-10-17',
        'Statement': [{'Effect': 'Allow', 'Action': 's3:*', 'Resource': '*'}],
    }

    mock_response = {
        'PolicyVersion': {
            'Document': mock_policy_document,
            'VersionId': 'v1',
            'IsDefaultVersion': True,
            'CreateDate': datetime(2023, 1, 1),
        }
    }

    with patch('awslabs.iam_mcp_server.server.get_iam_client') as mock_get_client:
        mock_client = Mock()
        mock_client.get_policy_version.return_value = mock_response
        mock_get_client.return_value = mock_client

        result = await get_managed_policy_document(
            policy_arn='arn:aws:iam::123456789012:policy/test-policy'
        )

        assert result.policy_arn == 'arn:aws:iam::123456789012:policy/test-policy'
        assert result.policy_name == 'test-policy'
        assert result.version_id == 'v1'
        assert result.is_default_version is True
        assert '"Action": "s3:*"' in result.policy_document
        assert '"Resource": "*"' in result.policy_document


@pytest.mark.asyncio
async def test_create_role():
    """Test create_role function."""
    from awslabs.iam_mcp_server.server import create_role

    trust_policy = {
        'Version': '2012-10-17',
        'Statement': [
            {
                'Effect': 'Allow',
                'Principal': {'Service': 'ec2.amazonaws.com'},
                'Action': 'sts:AssumeRole',
            }
        ],
    }

    mock_response = {
        'Role': {
            'RoleName': 'test-role',
            'RoleId': 'AROA123456789EXAMPLE',
            'Arn': 'arn:aws:iam::123456789012:role/test-role',
            'Path': '/',
            'CreateDate': datetime(2023, 1, 1),
            'AssumeRolePolicyDocument': '%7B%22Version%22%3A%222012-10-17%22%7D',
        }
    }

    # Disable readonly mode
    Context.initialize(readonly=False)

    with patch('awslabs.iam_mcp_server.server.get_iam_client') as mock_get_client:
        mock_client = Mock()
        mock_client.create_role.return_value = mock_response
        mock_get_client.return_value = mock_client

        result = await create_role(role_name='test-role', assume_role_policy_document=trust_policy)

        assert 'Successfully created role: test-role' in result['Message']
        assert result['Role']['RoleName'] == 'test-role'


@pytest.mark.asyncio
async def test_create_role_invalid_json():
    """Test create_role function with invalid JSON policy document."""
    from awslabs.iam_mcp_server.server import create_role

    # Disable readonly mode
    Context.initialize(readonly=False)

    with pytest.raises(Exception) as exc_info:
        await create_role(role_name='test-role', assume_role_policy_document='invalid json')

    assert 'Invalid JSON' in str(exc_info.value)


@pytest.mark.asyncio
async def test_create_role_readonly():
    """Test create_role function in readonly mode."""
    from awslabs.iam_mcp_server.server import create_role

    # Set readonly mode
    Context.initialize(readonly=True)

    with pytest.raises(IamClientError) as exc_info:
        await create_role(
            role_name='test-role', assume_role_policy_document={'Version': '2012-10-17'}
        )

    assert 'read-only mode' in str(exc_info.value)


# Additional comprehensive tests for server.py coverage


@pytest.mark.asyncio
async def test_get_user():
    """Test get_user function."""
    from awslabs.iam_mcp_server.server import get_user

    mock_user_response = {
        'User': {
            'UserName': 'test-user',
            'UserId': 'AIDACKCEVSQ6C2EXAMPLE',
            'Arn': 'arn:aws:iam::123456789012:user/test-user',
            'Path': '/',
            'CreateDate': datetime(2023, 1, 1),
        }
    }

    mock_policies_response = {
        'AttachedPolicies': [
            {
                'PolicyName': 'TestPolicy',
                'PolicyArn': 'arn:aws:iam::123456789012:policy/TestPolicy',
            }
        ]
    }

    mock_groups_response = {
        'Groups': [{'GroupName': 'TestGroup', 'Arn': 'arn:aws:iam::123456789012:group/TestGroup'}]
    }

    mock_keys_response = {
        'AccessKeyMetadata': [
            {
                'AccessKeyId': 'AKIAIOSFODNN7EXAMPLE',  # pragma: allowlist secret
                'Status': 'Active',
                'CreateDate': datetime(2023, 1, 1),
            }
        ]
    }

    mock_ctx = AsyncMock()

    with patch('awslabs.iam_mcp_server.server.get_iam_client') as mock_get_client:
        mock_client = Mock()
        mock_client.get_user.return_value = mock_user_response
        mock_client.list_attached_user_policies.return_value = mock_policies_response
        mock_client.list_user_policies.return_value = {'PolicyNames': ['InlinePolicy1']}
        mock_client.list_groups_for_user.return_value = mock_groups_response
        mock_client.list_access_keys.return_value = mock_keys_response
        mock_get_client.return_value = mock_client

        result = await get_user(mock_ctx, user_name='test-user')

        assert result.user.user_name == 'test-user'
        assert len(result.attached_policies) == 1
        assert result.attached_policies[0].policy_name == 'TestPolicy'


@pytest.mark.asyncio
async def test_get_user_not_found():
    """Test get_user function when user not found."""
    from awslabs.iam_mcp_server.server import get_user
    from botocore.exceptions import ClientError

    error = ClientError(
        error_response={'Error': {'Code': 'NoSuchEntity', 'Message': 'User not found'}},
        operation_name='GetUser',
    )

    with patch('awslabs.iam_mcp_server.server.get_iam_client') as mock_get_client:
        mock_client = Mock()
        mock_client.get_user.side_effect = error
        mock_get_client.return_value = mock_client

        with pytest.raises(Exception):
            await get_user(user_name='nonexistent-user')


@pytest.mark.asyncio
async def test_delete_user():
    """Test delete_user function."""


# Additional tests for better error handling coverage


@pytest.mark.asyncio
async def test_list_users_with_exception():
    """Test list_users function with generic exception."""
    from awslabs.iam_mcp_server.server import list_users

    with patch('awslabs.iam_mcp_server.server.get_iam_client') as mock_get_client:
        mock_client = Mock()
        mock_client.list_users.side_effect = Exception('Generic error')
        mock_get_client.return_value = mock_client

        with pytest.raises(Exception):
            await list_users()


@pytest.mark.asyncio
async def test_get_user_with_exception():
    """Test get_user function with generic exception."""
    from awslabs.iam_mcp_server.server import get_user

    with patch('awslabs.iam_mcp_server.server.get_iam_client') as mock_get_client:
        mock_client = Mock()
        mock_client.get_user.side_effect = Exception('Generic error')
        mock_get_client.return_value = mock_client

        with pytest.raises(Exception):
            await get_user(user_name='test-user')


@pytest.mark.asyncio
async def test_create_user_with_exception():
    """Test create_user function with generic exception."""
    from awslabs.iam_mcp_server.server import create_user

    with patch('awslabs.iam_mcp_server.server.get_iam_client') as mock_get_client:
        mock_client = Mock()
        mock_client.create_user.side_effect = Exception('Generic error')
        mock_get_client.return_value = mock_client

        with pytest.raises(Exception):
            await create_user(user_name='test-user')


@pytest.mark.asyncio
async def test_delete_user_with_exception():
    """Test delete_user function with generic exception."""
    from awslabs.iam_mcp_server.server import delete_user

    with patch('awslabs.iam_mcp_server.server.get_iam_client') as mock_get_client:
        mock_client = Mock()
        mock_client.delete_user.side_effect = Exception('Generic error')
        mock_get_client.return_value = mock_client

        with pytest.raises(Exception):
            await delete_user(user_name='test-user')


@pytest.mark.asyncio
async def test_list_roles_with_exception():
    """Test list_roles function with generic exception."""
    from awslabs.iam_mcp_server.server import list_roles

    with patch('awslabs.iam_mcp_server.server.get_iam_client') as mock_get_client:
        mock_client = Mock()
        mock_client.list_roles.side_effect = Exception('Generic error')
        mock_get_client.return_value = mock_client

        with pytest.raises(Exception):
            await list_roles()


@pytest.mark.asyncio
async def test_create_role_with_exception():
    """Test create_role function with generic exception."""
    from awslabs.iam_mcp_server.server import create_role

    with patch('awslabs.iam_mcp_server.server.get_iam_client') as mock_get_client:
        mock_client = Mock()
        mock_client.create_role.side_effect = Exception('Generic error')
        mock_get_client.return_value = mock_client

        with pytest.raises(Exception):
            await create_role(
                role_name='test-role', assume_role_policy_document={'Version': '2012-10-17'}
            )


@pytest.mark.asyncio
async def test_list_policies_with_exception():
    """Test list_policies function with generic exception."""
    from awslabs.iam_mcp_server.server import list_policies

    with patch('awslabs.iam_mcp_server.server.get_iam_client') as mock_get_client:
        mock_client = Mock()
        mock_client.list_policies.side_effect = Exception('Generic error')
        mock_get_client.return_value = mock_client

        with pytest.raises(Exception):
            await list_policies()


@pytest.mark.asyncio
async def test_attach_user_policy_with_exception():
    """Test attach_user_policy function with generic exception."""
    from awslabs.iam_mcp_server.server import attach_user_policy

    with patch('awslabs.iam_mcp_server.server.get_iam_client') as mock_get_client:
        mock_client = Mock()
        mock_client.attach_user_policy.side_effect = Exception('Generic error')
        mock_get_client.return_value = mock_client

        with pytest.raises(Exception):
            await attach_user_policy(
                user_name='test-user', policy_arn='arn:aws:iam::123456789012:policy/TestPolicy'
            )


@pytest.mark.asyncio
async def test_detach_user_policy_with_exception():
    """Test detach_user_policy function with generic exception."""
    from awslabs.iam_mcp_server.server import detach_user_policy

    with patch('awslabs.iam_mcp_server.server.get_iam_client') as mock_get_client:
        mock_client = Mock()
        mock_client.detach_user_policy.side_effect = Exception('Generic error')
        mock_get_client.return_value = mock_client

        with pytest.raises(Exception):
            await detach_user_policy(
                user_name='test-user', policy_arn='arn:aws:iam::123456789012:policy/TestPolicy'
            )


@pytest.mark.asyncio
async def test_create_access_key_with_exception():
    """Test create_access_key function with generic exception."""
    from awslabs.iam_mcp_server.server import create_access_key

    with patch('awslabs.iam_mcp_server.server.get_iam_client') as mock_get_client:
        mock_client = Mock()
        mock_client.create_access_key.side_effect = Exception('Generic error')
        mock_get_client.return_value = mock_client

        with pytest.raises(Exception):
            await create_access_key(user_name='test-user')


@pytest.mark.asyncio
async def test_delete_access_key_with_exception():
    """Test delete_access_key function with generic exception."""
    from awslabs.iam_mcp_server.server import delete_access_key

    with patch('awslabs.iam_mcp_server.server.get_iam_client') as mock_get_client:
        mock_client = Mock()
        mock_client.delete_access_key.side_effect = Exception('Generic error')
        mock_get_client.return_value = mock_client

        with pytest.raises(Exception):
            await delete_access_key(
                user_name='test-user',
                access_key_id='AKIAIOSFODNN7EXAMPLE',  # pragma: allowlist secret
            )


@pytest.mark.asyncio
async def test_simulate_principal_policy_success():
    """Test simulate_principal_policy function success case."""
    from awslabs.iam_mcp_server.server import simulate_principal_policy

    mock_response = {
        'EvaluationResults': [
            {
                'EvalActionName': 's3:GetObject',
                'EvalResourceName': 'arn:aws:s3:::my-bucket/*',
                'EvalDecision': 'allowed',
                'MatchedStatements': [{'SourcePolicyId': 'policy1'}],
                'MissingContextValues': [],
            }
        ],
        'IsTruncated': False,
        'Marker': 'marker123',
    }

    with patch('awslabs.iam_mcp_server.server.get_iam_client') as mock_get_client:
        mock_client = Mock()
        mock_client.simulate_principal_policy.return_value = mock_response
        mock_get_client.return_value = mock_client

        result = await simulate_principal_policy(
            policy_source_arn='arn:aws:iam::123456789012:user/test-user',
            action_names=['s3:GetObject'],
            resource_arns=['arn:aws:s3:::my-bucket/*'],
            context_entries={'aws:RequestedRegion': 'us-east-1'},
        )

        assert len(result['EvaluationResults']) == 1
        assert result['EvaluationResults'][0]['EvalActionName'] == 's3:GetObject'
        assert result['EvaluationResults'][0]['EvalResourceName'] == 'arn:aws:s3:::my-bucket/*'
        assert result['EvaluationResults'][0]['EvalDecision'] == 'allowed'
        assert result['IsTruncated'] is False
        assert result['Marker'] == 'marker123'
        assert result['PolicySourceArn'] == 'arn:aws:iam::123456789012:user/test-user'


@pytest.mark.asyncio
async def test_simulate_principal_policy_with_exception():
    """Test simulate_principal_policy function with generic exception."""
    from awslabs.iam_mcp_server.server import simulate_principal_policy

    with patch('awslabs.iam_mcp_server.server.get_iam_client') as mock_get_client:
        mock_client = Mock()
        mock_client.simulate_principal_policy.side_effect = Exception('Generic error')
        mock_get_client.return_value = mock_client

        with pytest.raises(Exception):
            await simulate_principal_policy(
                policy_source_arn='arn:aws:iam::123456789012:user/test-user',
                action_names=['s3:GetObject'],
            )


@pytest.mark.asyncio
async def test_delete_user_success():
    """Test delete_user function success case."""
    from awslabs.iam_mcp_server.server import delete_user

    # Disable readonly mode
    Context.initialize(readonly=False)

    with patch('awslabs.iam_mcp_server.server.get_iam_client') as mock_get_client:
        mock_client = Mock()
        mock_client.list_groups_for_user.return_value = {'Groups': []}
        mock_client.list_attached_user_policies.return_value = {'AttachedPolicies': []}
        mock_client.list_user_policies.return_value = {'PolicyNames': []}
        mock_client.list_access_keys.return_value = {'AccessKeyMetadata': []}
        mock_client.delete_user.return_value = {}
        mock_get_client.return_value = mock_client

        result = await delete_user(user_name='test-user')

        assert 'Successfully deleted user: test-user' in result['Message']
        mock_client.delete_user.assert_called_once_with(UserName='test-user')


@pytest.mark.asyncio
async def test_delete_user_readonly():
    """Test delete_user function in readonly mode."""
    from awslabs.iam_mcp_server.server import delete_user

    # Set readonly mode
    Context.initialize(readonly=True)

    with pytest.raises(IamClientError) as exc_info:
        await delete_user(user_name='test-user')

    assert 'read-only mode' in str(exc_info.value)


@pytest.mark.asyncio
async def test_delete_user_force():
    """Test delete_user function with force option."""
    from awslabs.iam_mcp_server.server import delete_user

    # Disable readonly mode
    Context.initialize(readonly=False)

    mock_policies_response = {
        'AttachedPolicies': [{'PolicyArn': 'arn:aws:iam::123456789012:policy/TestPolicy'}]
    }

    mock_groups_response = {'Groups': [{'GroupName': 'TestGroup'}]}

    mock_keys_response = {
        'AccessKeyMetadata': [{'AccessKeyId': 'AKIAIOSFODNN7EXAMPLE'}]  # pragma: allowlist secret
    }

    with patch('awslabs.iam_mcp_server.server.get_iam_client') as mock_get_client:
        mock_client = Mock()
        mock_client.list_attached_user_policies.return_value = mock_policies_response
        mock_client.list_groups_for_user.return_value = mock_groups_response
        mock_client.list_access_keys.return_value = mock_keys_response
        mock_client.list_user_policies.return_value = {'PolicyNames': []}
        mock_client.delete_user.return_value = {}
        mock_get_client.return_value = mock_client

        result = await delete_user(user_name='test-user', force=True)

        assert 'Successfully deleted user: test-user' in result['Message']
        mock_client.detach_user_policy.assert_called_once()
        mock_client.remove_user_from_group.assert_called_once()
        mock_client.delete_access_key.assert_called_once()


@pytest.mark.asyncio
async def test_attach_user_policy():
    """Test attach_user_policy function."""
    from awslabs.iam_mcp_server.server import attach_user_policy

    # Disable readonly mode
    Context.initialize(readonly=False)

    with patch('awslabs.iam_mcp_server.server.get_iam_client') as mock_get_client:
        mock_client = Mock()
        mock_client.attach_user_policy.return_value = {}
        mock_get_client.return_value = mock_client

        result = await attach_user_policy(
            user_name='test-user', policy_arn='arn:aws:iam::123456789012:policy/TestPolicy'
        )

        assert 'Successfully attached policy' in result['Message']
        mock_client.attach_user_policy.assert_called_once()


@pytest.mark.asyncio
async def test_attach_user_policy_readonly():
    """Test attach_user_policy function in readonly mode."""
    from awslabs.iam_mcp_server.server import attach_user_policy

    # Set readonly mode
    Context.initialize(readonly=True)

    with pytest.raises(IamClientError) as exc_info:
        await attach_user_policy(
            user_name='test-user', policy_arn='arn:aws:iam::123456789012:policy/TestPolicy'
        )

    assert 'read-only mode' in str(exc_info.value)


@pytest.mark.asyncio
async def test_detach_user_policy():
    """Test detach_user_policy function."""
    from awslabs.iam_mcp_server.server import detach_user_policy

    # Disable readonly mode
    Context.initialize(readonly=False)

    with patch('awslabs.iam_mcp_server.server.get_iam_client') as mock_get_client:
        mock_client = Mock()
        mock_client.detach_user_policy.return_value = {}
        mock_get_client.return_value = mock_client

        result = await detach_user_policy(
            user_name='test-user', policy_arn='arn:aws:iam::123456789012:policy/TestPolicy'
        )

        assert 'Successfully detached policy' in result['Message']
        mock_client.detach_user_policy.assert_called_once()


@pytest.mark.asyncio
async def test_detach_user_policy_readonly():
    """Test detach_user_policy function in readonly mode."""
    from awslabs.iam_mcp_server.server import detach_user_policy

    # Set readonly mode
    Context.initialize(readonly=True)

    with pytest.raises(IamClientError) as exc_info:
        await detach_user_policy(
            user_name='test-user', policy_arn='arn:aws:iam::123456789012:policy/TestPolicy'
        )

    assert 'read-only mode' in str(exc_info.value)


@pytest.mark.asyncio
async def test_create_access_key():
    """Test create_access_key function."""
    from awslabs.iam_mcp_server.server import create_access_key

    # Disable readonly mode
    Context.initialize(readonly=False)

    mock_response = {
        'AccessKey': {
            'AccessKeyId': 'AKIAIOSFODNN7EXAMPLE',  # pragma: allowlist secret
            'SecretAccessKey': 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY',  # pragma: allowlist secret
            'Status': 'Active',
            'UserName': 'test-user',
            'CreateDate': datetime(2023, 1, 1),
        }
    }

    with patch('awslabs.iam_mcp_server.server.get_iam_client') as mock_get_client:
        mock_client = Mock()
        mock_client.create_access_key.return_value = mock_response
        mock_get_client.return_value = mock_client

        result = await create_access_key(user_name='test-user')

        assert 'Successfully created access key' in result['Message']
        assert (
            result['AccessKey']['AccessKeyId']
            == 'AKIAIOSFODNN7EXAMPLE'  # pragma: allowlist secret
        )
        mock_client.create_access_key.assert_called_once()


@pytest.mark.asyncio
async def test_create_access_key_readonly():
    """Test create_access_key function in readonly mode."""
    from awslabs.iam_mcp_server.server import create_access_key

    # Set readonly mode
    Context.initialize(readonly=True)

    with pytest.raises(IamClientError) as exc_info:
        await create_access_key(user_name='test-user')

    assert 'read-only mode' in str(exc_info.value)


@pytest.mark.asyncio
async def test_delete_access_key():
    """Test delete_access_key function."""
    from awslabs.iam_mcp_server.server import delete_access_key

    # Disable readonly mode
    Context.initialize(readonly=False)

    with patch('awslabs.iam_mcp_server.server.get_iam_client') as mock_get_client:
        mock_client = Mock()
        mock_client.delete_access_key.return_value = {}
        mock_get_client.return_value = mock_client

        result = await delete_access_key(
            user_name='test-user',
            access_key_id='AKIAIOSFODNN7EXAMPLE',  # pragma: allowlist secret
        )

        assert 'Successfully deleted access key' in result['Message']
        mock_client.delete_access_key.assert_called_once()


@pytest.mark.asyncio
async def test_delete_access_key_readonly():
    """Test delete_access_key function in readonly mode."""
    from awslabs.iam_mcp_server.server import delete_access_key

    # Set readonly mode
    Context.initialize(readonly=True)

    with pytest.raises(IamClientError) as exc_info:
        await delete_access_key(
            user_name='test-user',
            access_key_id='AKIAIOSFODNN7EXAMPLE',  # pragma: allowlist secret
        )

    assert 'read-only mode' in str(exc_info.value)


# Test main function and server initialization


def test_main_function():
    """Test main function argument parsing."""
    from awslabs.iam_mcp_server.server import main

    # Test with readonly flag
    with patch('sys.argv', ['server.py', '--readonly']):
        with patch('awslabs.iam_mcp_server.server.mcp.run') as mock_run:
            main()
            mock_run.assert_called_once()
            # Verify readonly mode was set
            assert Context.is_readonly()

    # Test without readonly flag
    with patch('sys.argv', ['server.py']):
        with patch('awslabs.iam_mcp_server.server.mcp.run') as mock_run:
            main()
            mock_run.assert_called_once()


# Group Management Tests


@pytest.mark.asyncio
async def test_list_groups():
    """Test listing IAM groups."""
    from awslabs.iam_mcp_server.server import list_groups

    mock_response = {
        'Groups': [
            {
                'GroupName': 'TestGroup1',
                'GroupId': 'AGPAI23HZ27SI6FQMGNQ2',
                'Arn': 'arn:aws:iam::123456789012:group/TestGroup1',
                'Path': '/',
                'CreateDate': datetime(2023, 1, 1),
            },
            {
                'GroupName': 'TestGroup2',
                'GroupId': 'AGPAI23HZ27SI6FQMGNQ3',
                'Arn': 'arn:aws:iam::123456789012:group/TestGroup2',
                'Path': '/teams/',
                'CreateDate': datetime(2023, 1, 2),
            },
        ],
        'IsTruncated': False,
    }

    with patch('awslabs.iam_mcp_server.server.get_iam_client') as mock_get_client:
        mock_client = Mock()
        mock_client.list_groups.return_value = mock_response
        mock_get_client.return_value = mock_client

        result = await list_groups()

        assert len(result.groups) == 2
        assert result.groups[0].group_name == 'TestGroup1'
        assert result.groups[1].group_name == 'TestGroup2'
        assert result.groups[1].path == '/teams/'
        assert result.count == 2
        assert not result.is_truncated


@pytest.mark.asyncio
async def test_list_groups_with_path_prefix():
    """Test listing IAM groups with path prefix filter."""
    from awslabs.iam_mcp_server.server import list_groups

    mock_response = {
        'Groups': [
            {
                'GroupName': 'TeamGroup',
                'GroupId': 'AGPAI23HZ27SI6FQMGNQ4',
                'Arn': 'arn:aws:iam::123456789012:group/teams/TeamGroup',
                'Path': '/teams/',
                'CreateDate': datetime(2023, 1, 1),
            }
        ],
        'IsTruncated': False,
    }

    with patch('awslabs.iam_mcp_server.server.get_iam_client') as mock_get_client:
        mock_client = Mock()
        mock_client.list_groups.return_value = mock_response
        mock_get_client.return_value = mock_client

        result = await list_groups(path_prefix='/teams/', max_items=100)

        mock_client.list_groups.assert_called_once_with(MaxItems=100, PathPrefix='/teams/')
        assert len(result.groups) == 1
        assert result.groups[0].group_name == 'TeamGroup'


@pytest.mark.asyncio
async def test_get_group():
    """Test getting detailed group information."""
    from awslabs.iam_mcp_server.server import get_group

    mock_group_response = {
        'Group': {
            'GroupName': 'TestGroup',
            'GroupId': 'AGPAI23HZ27SI6FQMGNQ2',
            'Arn': 'arn:aws:iam::123456789012:group/TestGroup',
            'Path': '/',
            'CreateDate': datetime(2023, 1, 1),
        },
        'Users': [
            {'UserName': 'user1'},
            {'UserName': 'user2'},
        ],
    }

    mock_policies_response = {
        'AttachedPolicies': [
            {
                'PolicyName': 'TestPolicy',
                'PolicyArn': 'arn:aws:iam::123456789012:policy/TestPolicy',
            }
        ]
    }

    mock_inline_policies_response = {'PolicyNames': ['InlinePolicy1']}

    with patch('awslabs.iam_mcp_server.server.get_iam_client') as mock_get_client:
        mock_client = Mock()
        mock_client.get_group.return_value = mock_group_response
        mock_client.list_attached_group_policies.return_value = mock_policies_response
        mock_client.list_group_policies.return_value = mock_inline_policies_response
        mock_get_client.return_value = mock_client

        result = await get_group(group_name='TestGroup')

        assert result.group.group_name == 'TestGroup'
        assert len(result.users) == 2
        assert 'user1' in result.users
        assert 'user2' in result.users
        assert len(result.attached_policies) == 1
        assert result.attached_policies[0].policy_name == 'TestPolicy'
        assert len(result.inline_policies) == 1
        assert 'InlinePolicy1' in result.inline_policies


@pytest.mark.asyncio
async def test_create_group():
    """Test creating a new IAM group."""
    from awslabs.iam_mcp_server.server import create_group

    # Disable readonly mode
    Context.initialize(readonly=False)

    mock_response = {
        'Group': {
            'GroupName': 'NewGroup',
            'GroupId': 'AGPAI23HZ27SI6FQMGNQ5',
            'Arn': 'arn:aws:iam::123456789012:group/NewGroup',
            'Path': '/',
            'CreateDate': datetime(2023, 1, 1),
        }
    }

    with patch('awslabs.iam_mcp_server.server.get_iam_client') as mock_get_client:
        mock_client = Mock()
        mock_client.create_group.return_value = mock_response
        mock_get_client.return_value = mock_client

        result = await create_group(group_name='NewGroup', path='/')

        mock_client.create_group.assert_called_once_with(GroupName='NewGroup', Path='/')
        assert result.group.group_name == 'NewGroup'
        assert 'Successfully created IAM group: NewGroup' in result.message


@pytest.mark.asyncio
async def test_create_group_readonly():
    """Test creating group in readonly mode raises error."""
    from awslabs.iam_mcp_server.server import create_group

    with patch('awslabs.iam_mcp_server.context.Context.is_readonly', return_value=True):
        with pytest.raises(Exception) as exc_info:
            await create_group(group_name='NewGroup')
        assert 'Cannot create group in read-only mode' in str(exc_info.value)


@pytest.mark.asyncio
async def test_delete_group():
    """Test deleting an IAM group."""
    from awslabs.iam_mcp_server.server import delete_group

    # Disable readonly mode
    Context.initialize(readonly=False)

    with patch('awslabs.iam_mcp_server.server.get_iam_client') as mock_get_client:
        mock_client = Mock()
        mock_get_client.return_value = mock_client

        result = await delete_group(group_name='TestGroup', force=False)

        mock_client.delete_group.assert_called_once_with(GroupName='TestGroup')
        assert 'Successfully deleted IAM group: TestGroup' in result['message']


@pytest.mark.asyncio
async def test_delete_group_force():
    """Test force deleting an IAM group with cleanup."""
    from awslabs.iam_mcp_server.server import delete_group

    # Disable readonly mode
    Context.initialize(readonly=False)

    mock_group_response = {
        'Users': [
            {'UserName': 'user1'},
            {'UserName': 'user2'},
        ]
    }

    mock_attached_policies = {
        'AttachedPolicies': [{'PolicyArn': 'arn:aws:iam::123456789012:policy/TestPolicy'}]
    }

    mock_inline_policies = {'PolicyNames': ['InlinePolicy1']}

    with patch('awslabs.iam_mcp_server.server.get_iam_client') as mock_get_client:
        mock_client = Mock()
        mock_client.get_group.return_value = mock_group_response
        mock_client.list_attached_group_policies.return_value = mock_attached_policies
        mock_client.list_group_policies.return_value = mock_inline_policies
        mock_get_client.return_value = mock_client

        result = await delete_group(group_name='TestGroup', force=True)

        # Verify cleanup operations
        assert mock_client.remove_user_from_group.call_count == 2
        mock_client.detach_group_policy.assert_called_once()
        mock_client.delete_group_policy.assert_called_once()
        mock_client.delete_group.assert_called_once_with(GroupName='TestGroup')
        assert 'Successfully deleted IAM group: TestGroup' in result['message']


@pytest.mark.asyncio
async def test_delete_group_readonly():
    """Test deleting group in readonly mode raises error."""
    from awslabs.iam_mcp_server.server import delete_group

    with patch('awslabs.iam_mcp_server.context.Context.is_readonly', return_value=True):
        with pytest.raises(Exception) as exc_info:
            await delete_group(group_name='TestGroup')
        assert 'Cannot delete group in read-only mode' in str(exc_info.value)


@pytest.mark.asyncio
async def test_add_user_to_group():
    """Test adding a user to a group."""
    from awslabs.iam_mcp_server.server import add_user_to_group

    # Disable readonly mode
    Context.initialize(readonly=False)

    with patch('awslabs.iam_mcp_server.server.get_iam_client') as mock_get_client:
        mock_client = Mock()
        mock_get_client.return_value = mock_client

        result = await add_user_to_group(group_name='TestGroup', user_name='testuser')

        mock_client.add_user_to_group.assert_called_once_with(
            GroupName='TestGroup', UserName='testuser'
        )
        assert result.group_name == 'TestGroup'
        assert result.user_name == 'testuser'
        assert 'Successfully added user testuser to group TestGroup' in result.message


@pytest.mark.asyncio
async def test_add_user_to_group_readonly():
    """Test adding user to group in readonly mode raises error."""
    from awslabs.iam_mcp_server.server import add_user_to_group

    with patch('awslabs.iam_mcp_server.context.Context.is_readonly', return_value=True):
        with pytest.raises(Exception) as exc_info:
            await add_user_to_group(group_name='TestGroup', user_name='testuser')
        assert 'Cannot add user to group in read-only mode' in str(exc_info.value)


@pytest.mark.asyncio
async def test_remove_user_from_group():
    """Test removing a user from a group."""
    from awslabs.iam_mcp_server.server import remove_user_from_group

    # Disable readonly mode
    Context.initialize(readonly=False)

    with patch('awslabs.iam_mcp_server.server.get_iam_client') as mock_get_client:
        mock_client = Mock()
        mock_get_client.return_value = mock_client

        result = await remove_user_from_group(group_name='TestGroup', user_name='testuser')

        mock_client.remove_user_from_group.assert_called_once_with(
            GroupName='TestGroup', UserName='testuser'
        )
        assert result.group_name == 'TestGroup'
        assert result.user_name == 'testuser'
        assert 'Successfully removed user testuser from group TestGroup' in result.message


@pytest.mark.asyncio
async def test_remove_user_from_group_readonly():
    """Test removing user from group in readonly mode raises error."""
    from awslabs.iam_mcp_server.server import remove_user_from_group

    with patch('awslabs.iam_mcp_server.context.Context.is_readonly', return_value=True):
        with pytest.raises(Exception) as exc_info:
            await remove_user_from_group(group_name='TestGroup', user_name='testuser')
        assert 'Cannot remove user from group in read-only mode' in str(exc_info.value)


@pytest.mark.asyncio
async def test_attach_group_policy():
    """Test attaching a policy to a group."""
    from awslabs.iam_mcp_server.server import attach_group_policy

    # Disable readonly mode
    Context.initialize(readonly=False)

    policy_arn = 'arn:aws:iam::123456789012:policy/TestPolicy'

    with patch('awslabs.iam_mcp_server.server.get_iam_client') as mock_get_client:
        mock_client = Mock()
        mock_get_client.return_value = mock_client

        result = await attach_group_policy(group_name='TestGroup', policy_arn=policy_arn)

        mock_client.attach_group_policy.assert_called_once_with(
            GroupName='TestGroup', PolicyArn=policy_arn
        )
        assert result.group_name == 'TestGroup'
        assert result.policy_arn == policy_arn
        assert (
            'Successfully attached policy arn:aws:iam::123456789012:policy/TestPolicy to group TestGroup'
            in result.message
        )


@pytest.mark.asyncio
async def test_attach_group_policy_readonly():
    """Test attaching policy to group in readonly mode raises error."""
    from awslabs.iam_mcp_server.server import attach_group_policy

    with patch('awslabs.iam_mcp_server.context.Context.is_readonly', return_value=True):
        with pytest.raises(Exception) as exc_info:
            await attach_group_policy(
                group_name='TestGroup', policy_arn='arn:aws:iam::123456789012:policy/TestPolicy'
            )
        assert 'Cannot attach policy to group in read-only mode' in str(exc_info.value)


@pytest.mark.asyncio
async def test_detach_group_policy():
    """Test detaching a policy from a group."""
    from awslabs.iam_mcp_server.server import detach_group_policy

    # Disable readonly mode
    Context.initialize(readonly=False)

    policy_arn = 'arn:aws:iam::123456789012:policy/TestPolicy'

    with patch('awslabs.iam_mcp_server.server.get_iam_client') as mock_get_client:
        mock_client = Mock()
        mock_get_client.return_value = mock_client

        result = await detach_group_policy(group_name='TestGroup', policy_arn=policy_arn)

        mock_client.detach_group_policy.assert_called_once_with(
            GroupName='TestGroup', PolicyArn=policy_arn
        )
        assert result.group_name == 'TestGroup'
        assert result.policy_arn == policy_arn
        assert (
            'Successfully detached policy arn:aws:iam::123456789012:policy/TestPolicy from group TestGroup'
            in result.message
        )


@pytest.mark.asyncio
async def test_detach_group_policy_readonly():
    """Test detaching policy from group in readonly mode raises error."""
    from awslabs.iam_mcp_server.server import detach_group_policy

    with patch('awslabs.iam_mcp_server.context.Context.is_readonly', return_value=True):
        with pytest.raises(Exception) as exc_info:
            await detach_group_policy(
                group_name='TestGroup', policy_arn='arn:aws:iam::123456789012:policy/TestPolicy'
            )
        assert 'Cannot detach policy from group in read-only mode' in str(exc_info.value)


# Group Management Exception Tests


@pytest.mark.asyncio
async def test_list_groups_with_exception():
    """Test list_groups with exception handling."""
    from awslabs.iam_mcp_server.server import list_groups

    with patch('awslabs.iam_mcp_server.server.get_iam_client') as mock_get_client:
        mock_client = Mock()
        mock_client.list_groups.side_effect = BotoClientError(
            error_response={'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}},
            operation_name='ListGroups',
        )
        mock_get_client.return_value = mock_client

        with pytest.raises(IamPermissionError):
            await list_groups()


@pytest.mark.asyncio
async def test_get_group_with_exception():
    """Test get_group with exception handling."""
    from awslabs.iam_mcp_server.server import get_group

    with patch('awslabs.iam_mcp_server.server.get_iam_client') as mock_get_client:
        mock_client = Mock()
        mock_client.get_group.side_effect = BotoClientError(
            error_response={'Error': {'Code': 'NoSuchEntity', 'Message': 'Group does not exist'}},
            operation_name='GetGroup',
        )
        mock_get_client.return_value = mock_client

        with pytest.raises(IamResourceNotFoundError):
            await get_group(group_name='NonExistentGroup')


@pytest.mark.asyncio
async def test_create_group_with_exception():
    """Test create_group with exception handling."""
    from awslabs.iam_mcp_server.server import create_group

    # Disable readonly mode
    Context.initialize(readonly=False)

    with patch('awslabs.iam_mcp_server.server.get_iam_client') as mock_get_client:
        mock_client = Mock()
        mock_client.create_group.side_effect = BotoClientError(
            error_response={
                'Error': {'Code': 'EntityAlreadyExists', 'Message': 'Group already exists'}
            },
            operation_name='CreateGroup',
        )
        mock_get_client.return_value = mock_client

        with pytest.raises(IamClientError):
            await create_group(group_name='ExistingGroup')


@pytest.mark.asyncio
async def test_delete_group_with_exception():
    """Test delete_group with exception handling."""
    from awslabs.iam_mcp_server.server import delete_group

    with patch('awslabs.iam_mcp_server.server.get_iam_client') as mock_get_client:
        mock_client = Mock()
        mock_client.delete_group.side_effect = BotoClientError(
            error_response={'Error': {'Code': 'DeleteConflict', 'Message': 'Cannot delete group'}},
            operation_name='DeleteGroup',
        )
        mock_get_client.return_value = mock_client

        with pytest.raises(IamMcpError):
            await delete_group(group_name='GroupWithDependencies', force=False)


@pytest.mark.asyncio
async def test_add_user_to_group_with_exception():
    """Test add_user_to_group with exception handling."""
    from awslabs.iam_mcp_server.server import add_user_to_group

    # Disable readonly mode
    Context.initialize(readonly=False)

    with patch('awslabs.iam_mcp_server.server.get_iam_client') as mock_get_client:
        mock_client = Mock()
        mock_client.add_user_to_group.side_effect = BotoClientError(
            error_response={'Error': {'Code': 'NoSuchEntity', 'Message': 'User does not exist'}},
            operation_name='AddUserToGroup',
        )
        mock_get_client.return_value = mock_client

        with pytest.raises(IamResourceNotFoundError):
            await add_user_to_group(group_name='TestGroup', user_name='NonExistentUser')


@pytest.mark.asyncio
async def test_attach_group_policy_with_exception():
    """Test attach_group_policy with exception handling."""
    from awslabs.iam_mcp_server.server import attach_group_policy

    with patch('awslabs.iam_mcp_server.server.get_iam_client') as mock_get_client:
        mock_client = Mock()
        mock_client.attach_group_policy.side_effect = BotoClientError(
            error_response={
                'Error': {'Code': 'InvalidInput', 'Message': 'Policy is not attachable'}
            },
            operation_name='AttachGroupPolicy',
        )
        mock_get_client.return_value = mock_client

        with pytest.raises(IamValidationError):
            await attach_group_policy(
                group_name='TestGroup', policy_arn='arn:aws:iam::123456789012:policy/TestPolicy'
            )
