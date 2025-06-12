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
# ruff: noqa: D101, D102, D103
"""Tests for the IAM handler."""

import json
import pytest
from awslabs.eks_mcp_server.iam_handler import IAMHandler
from mcp.server.fastmcp import Context
from unittest.mock import MagicMock, patch


@pytest.mark.asyncio
async def test_iam_handler_initialization():
    # Create a mock MCP server
    mock_mcp = MagicMock()

    # Initialize the IAM handler with the mock MCP server
    IAMHandler(mock_mcp, allow_write=True)

    # Verify that all tools were registered
    assert mock_mcp.tool.call_count == 2

    # Get all call args
    call_args_list = mock_mcp.tool.call_args_list

    # Get all tool names that were registered
    tool_names = [call_args[1]['name'] for call_args in call_args_list]

    # Verify that all expected tools were registered
    assert 'get_policies_for_role' in tool_names
    assert 'add_inline_policy' in tool_names


@pytest.mark.asyncio
@patch('awslabs.eks_mcp_server.aws_helper.AwsHelper.create_boto3_client')
async def test_get_policies_for_role(mock_create_client):
    # Create a mock IAM client
    mock_iam_client = MagicMock()
    mock_create_client.return_value = mock_iam_client

    # Create a mock MCP server
    mock_mcp = MagicMock()

    # Initialize the IAM handler with the mock MCP server
    handler = IAMHandler(mock_mcp)

    # Create a mock context
    mock_ctx = MagicMock(spec=Context)

    # Mock the get_role response
    mock_role_response = {
        'Role': {
            'RoleName': 'test-role',
            'RoleId': 'AROAEXAMPLEID',
            'Arn': 'arn:aws:iam::123456789012:role/test-role',
            'Path': '/',
            'CreateDate': MagicMock(isoformat=lambda: '2023-01-01T00:00:00Z'),
            'AssumeRolePolicyDocument': json.dumps(
                {
                    'Version': '2012-10-17',
                    'Statement': [
                        {
                            'Effect': 'Allow',
                            'Principal': {'Service': 'eks.amazonaws.com'},
                            'Action': 'sts:AssumeRole',
                        }
                    ],
                }
            ),
            'MaxSessionDuration': 3600,
            'Description': 'Test role',
            'Tags': [{'Key': 'Environment', 'Value': 'Test'}],
        }
    }
    mock_iam_client.get_role.return_value = mock_role_response

    # Mock the list_attached_role_policies response
    mock_attached_policies_response = {
        'AttachedPolicies': [
            {
                'PolicyName': 'AmazonEKSClusterPolicy',
                'PolicyArn': 'arn:aws:iam::aws:policy/AmazonEKSClusterPolicy',
            }
        ]
    }
    mock_iam_client.list_attached_role_policies.return_value = mock_attached_policies_response

    # Mock the get_policy response
    mock_policy_response = {
        'Policy': {
            'PolicyName': 'AmazonEKSClusterPolicy',
            'PolicyId': 'ANPAEXAMPLEID',
            'Arn': 'arn:aws:iam::aws:policy/AmazonEKSClusterPolicy',
            'Path': '/',
            'DefaultVersionId': 'v1',
            'AttachmentCount': 1,
            'IsAttachable': True,
            'CreateDate': MagicMock(isoformat=lambda: '2023-01-01T00:00:00Z'),
            'UpdateDate': MagicMock(isoformat=lambda: '2023-01-01T00:00:00Z'),
            'Description': 'Policy for EKS clusters',
        }
    }
    mock_iam_client.get_policy.return_value = mock_policy_response

    # Mock the get_policy_version response
    mock_policy_version_response = {
        'PolicyVersion': {
            'Document': {
                'Version': '2012-10-17',
                'Statement': [{'Effect': 'Allow', 'Action': 'eks:*', 'Resource': '*'}],
            },
            'VersionId': 'v1',
            'IsDefaultVersion': True,
            'CreateDate': MagicMock(isoformat=lambda: '2023-01-01T00:00:00Z'),
        }
    }
    mock_iam_client.get_policy_version.return_value = mock_policy_version_response

    # Mock the list_role_policies response
    mock_inline_policies_response = {'PolicyNames': ['test-inline-policy']}
    mock_iam_client.list_role_policies.return_value = mock_inline_policies_response

    # Mock the get_role_policy response
    mock_role_policy_response = {
        'PolicyName': 'test-inline-policy',
        'RoleName': 'test-role',
        'PolicyDocument': {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Effect': 'Allow',
                    'Action': 's3:GetObject',
                    'Resource': 'arn:aws:s3:::example-bucket/*',
                }
            ],
        },
    }
    mock_iam_client.get_role_policy.return_value = mock_role_policy_response

    # Call the get_policies_for_role method
    result = await handler.get_policies_for_role(mock_ctx, role_name='test-role')

    # Verify the result
    assert not result.isError
    assert len(result.content) == 1
    assert result.content[0].type == 'text'
    assert 'Successfully retrieved details for IAM role: test-role' in result.content[0].text
    assert result.role_arn == 'arn:aws:iam::123456789012:role/test-role'
    assert result.description == 'Test role'
    assert len(result.managed_policies) == 1
    assert result.managed_policies[0].policy_type == 'Managed'
    assert len(result.inline_policies) == 1
    assert result.inline_policies[0].policy_type == 'Inline'


@pytest.mark.asyncio
@patch('awslabs.eks_mcp_server.aws_helper.AwsHelper.create_boto3_client')
async def test_add_inline_policy_existing_policy(mock_create_client):
    # Create a mock IAM client
    mock_iam_client = MagicMock()
    mock_create_client.return_value = mock_iam_client

    # Create a mock MCP server
    mock_mcp = MagicMock()

    # Initialize the IAM handler with the mock MCP server with write access enabled
    handler = IAMHandler(mock_mcp, allow_write=True)

    # Create a mock context
    mock_ctx = MagicMock(spec=Context)

    # Mock the get_role_policy response to indicate the policy already exists
    mock_role_policy_response = {
        'PolicyName': 'test-inline-policy',
        'RoleName': 'test-role',
        'PolicyDocument': {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Effect': 'Allow',
                    'Action': 's3:GetObject',
                    'Resource': 'arn:aws:s3:::example-bucket/*',
                }
            ],
        },
    }
    mock_iam_client.get_role_policy.return_value = mock_role_policy_response

    # Define the permissions to add
    permissions = {
        'Effect': 'Allow',
        'Action': 's3:PutObject',
        'Resource': 'arn:aws:s3:::example-bucket/*',
    }

    # Call the add_inline_policy method
    result = await handler.add_inline_policy(
        mock_ctx, policy_name='test-inline-policy', role_name='test-role', permissions=permissions
    )

    # Verify the result indicates an error because the policy already exists
    assert result.isError
    assert len(result.content) == 1
    assert result.content[0].type == 'text'
    assert 'Policy test-inline-policy already exists in role test-role' in result.content[0].text
    assert result.policy_name == 'test-inline-policy'
    assert result.role_name == 'test-role'

    # Verify that put_role_policy was NOT called
    mock_iam_client.put_role_policy.assert_not_called()


@pytest.mark.asyncio
@patch('awslabs.eks_mcp_server.aws_helper.AwsHelper.create_boto3_client')
async def test_add_inline_policy_new_policy(mock_create_client):
    # Create a mock IAM client
    mock_iam_client = MagicMock()
    mock_create_client.return_value = mock_iam_client

    # Create a mock MCP server
    mock_mcp = MagicMock()

    # Initialize the IAM handler with the mock MCP server with write access enabled
    handler = IAMHandler(mock_mcp, allow_write=True)

    # Create a mock context
    mock_ctx = MagicMock(spec=Context)

    # Mock the get_role_policy to raise NoSuchEntityException
    mock_iam_client.exceptions.NoSuchEntityException = Exception
    mock_iam_client.get_role_policy.side_effect = (
        mock_iam_client.exceptions.NoSuchEntityException()
    )

    # Define the permissions to add
    permissions = {
        'Effect': 'Allow',
        'Action': 's3:PutObject',
        'Resource': 'arn:aws:s3:::example-bucket/*',
    }

    # Call the add_inline_policy method
    result = await handler.add_inline_policy(
        mock_ctx, policy_name='test-inline-policy', role_name='test-role', permissions=permissions
    )

    # Verify the result
    assert not result.isError
    assert len(result.content) == 1
    assert result.content[0].type == 'text'
    assert (
        'Successfully created new inline policy test-inline-policy in role test-role'
        in result.content[0].text
    )
    assert result.policy_name == 'test-inline-policy'
    assert result.role_name == 'test-role'
    assert result.permissions_added == permissions

    # Verify that put_role_policy was called with the correct parameters
    mock_iam_client.put_role_policy.assert_called_once()
    args, kwargs = mock_iam_client.put_role_policy.call_args
    assert kwargs['RoleName'] == 'test-role'
    assert kwargs['PolicyName'] == 'test-inline-policy'
    policy_document = json.loads(kwargs['PolicyDocument'])
    assert len(policy_document['Statement']) == 1
    assert policy_document['Statement'][0]['Action'] == 's3:PutObject'


@pytest.mark.asyncio
@patch('awslabs.eks_mcp_server.aws_helper.AwsHelper.create_boto3_client')
async def test_add_inline_policy_multiple_statements(mock_create_client):
    # Create a mock IAM client
    mock_iam_client = MagicMock()
    mock_create_client.return_value = mock_iam_client

    # Create a mock MCP server
    mock_mcp = MagicMock()

    # Initialize the IAM handler with the mock MCP server with write access enabled
    handler = IAMHandler(mock_mcp, allow_write=True)

    # Create a mock context
    mock_ctx = MagicMock(spec=Context)

    # Mock the get_role_policy to raise NoSuchEntityException
    mock_iam_client.exceptions.NoSuchEntityException = Exception
    mock_iam_client.get_role_policy.side_effect = (
        mock_iam_client.exceptions.NoSuchEntityException()
    )

    # Define the permissions to add (multiple statements)
    permissions = [
        {'Effect': 'Allow', 'Action': 's3:PutObject', 'Resource': 'arn:aws:s3:::example-bucket/*'},
        {
            'Effect': 'Allow',
            'Action': 's3:DeleteObject',
            'Resource': 'arn:aws:s3:::example-bucket/*',
        },
    ]

    # Call the add_inline_policy method
    result = await handler.add_inline_policy(
        mock_ctx, policy_name='test-inline-policy', role_name='test-role', permissions=permissions
    )

    # Verify the result
    assert not result.isError
    assert len(result.content) == 1
    assert result.content[0].type == 'text'
    assert (
        'Successfully created new inline policy test-inline-policy in role test-role'
        in result.content[0].text
    )
    assert result.policy_name == 'test-inline-policy'
    assert result.role_name == 'test-role'
    assert result.permissions_added == permissions

    # Verify that put_role_policy was called with the correct parameters
    mock_iam_client.put_role_policy.assert_called_once()
    args, kwargs = mock_iam_client.put_role_policy.call_args
    assert kwargs['RoleName'] == 'test-role'
    assert kwargs['PolicyName'] == 'test-inline-policy'
    policy_document = json.loads(kwargs['PolicyDocument'])
    assert len(policy_document['Statement']) == 2
    assert policy_document['Statement'][0]['Action'] == 's3:PutObject'
    assert policy_document['Statement'][1]['Action'] == 's3:DeleteObject'


@pytest.mark.asyncio
@patch('awslabs.eks_mcp_server.aws_helper.AwsHelper.create_boto3_client')
async def test_get_policies_for_role_error(mock_create_client):
    """Test get_policies_for_role method when an error occurs."""
    # Create a mock IAM client
    mock_iam_client = MagicMock()
    mock_create_client.return_value = mock_iam_client

    # Make get_role raise an exception
    mock_iam_client.get_role.side_effect = Exception('Role not found')

    # Create a mock MCP server
    mock_mcp = MagicMock()

    # Initialize the IAM handler with the mock MCP server
    handler = IAMHandler(mock_mcp)

    # Create a mock context
    mock_ctx = MagicMock(spec=Context)

    # Call the get_policies_for_role method
    result = await handler.get_policies_for_role(mock_ctx, role_name='non-existent-role')

    # Verify the result indicates an error
    assert result.isError
    assert len(result.content) == 1
    assert result.content[0].type == 'text'
    assert 'Failed to describe IAM role' in result.content[0].text
    assert 'Role not found' in result.content[0].text
    assert result.role_arn == ''
    assert result.assume_role_policy_document == {}
    assert result.description is None
    assert result.managed_policies == []
    assert result.inline_policies == []


@pytest.mark.asyncio
@patch('awslabs.eks_mcp_server.aws_helper.AwsHelper.create_boto3_client')
async def test_get_policies_for_role_string_policy_document(mock_create_client):
    """Test get_policies_for_role method when assume_role_policy_document is a string."""
    # Create a mock IAM client
    mock_iam_client = MagicMock()
    mock_create_client.return_value = mock_iam_client

    # Mock the get_role response with a string policy document
    mock_role_response = {
        'Role': {
            'RoleName': 'test-role',
            'RoleId': 'AROAEXAMPLEID',
            'Arn': 'arn:aws:iam::123456789012:role/test-role',
            'Path': '/',
            'CreateDate': MagicMock(isoformat=lambda: '2023-01-01T00:00:00Z'),
            'AssumeRolePolicyDocument': '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"eks.amazonaws.com"},"Action":"sts:AssumeRole"}]}',
            'MaxSessionDuration': 3600,
            'Description': 'Test role',
            'Tags': [{'Key': 'Environment', 'Value': 'Test'}],
        }
    }
    mock_iam_client.get_role.return_value = mock_role_response

    # Mock the list_attached_role_policies response
    mock_iam_client.list_attached_role_policies.return_value = {'AttachedPolicies': []}

    # Mock the list_role_policies response
    mock_iam_client.list_role_policies.return_value = {'PolicyNames': []}

    # Create a mock MCP server
    mock_mcp = MagicMock()

    # Initialize the IAM handler with the mock MCP server
    handler = IAMHandler(mock_mcp)

    # Create a mock context
    mock_ctx = MagicMock(spec=Context)

    # Call the get_policies_for_role method
    result = await handler.get_policies_for_role(mock_ctx, role_name='test-role')

    # Verify the result
    assert not result.isError
    assert len(result.content) == 1
    assert result.content[0].type == 'text'
    assert 'Successfully retrieved details for IAM role: test-role' in result.content[0].text
    assert result.role_arn == 'arn:aws:iam::123456789012:role/test-role'
    assert result.description == 'Test role'
    assert result.assume_role_policy_document == {
        'Version': '2012-10-17',
        'Statement': [
            {
                'Effect': 'Allow',
                'Principal': {'Service': 'eks.amazonaws.com'},
                'Action': 'sts:AssumeRole',
            }
        ],
    }
    assert result.managed_policies == []
    assert result.inline_policies == []


@pytest.mark.asyncio
@patch('awslabs.eks_mcp_server.aws_helper.AwsHelper.create_boto3_client')
async def test_get_managed_policies_error(mock_create_client):
    """Test _get_managed_policies method when an error occurs."""
    # Create a mock IAM client
    mock_iam_client = MagicMock()
    mock_create_client.return_value = mock_iam_client

    # Mock the get_role response
    mock_role_response = {
        'Role': {
            'RoleName': 'test-role',
            'RoleId': 'AROAEXAMPLEID',
            'Arn': 'arn:aws:iam::123456789012:role/test-role',
            'Path': '/',
            'CreateDate': MagicMock(isoformat=lambda: '2023-01-01T00:00:00Z'),
            'AssumeRolePolicyDocument': {
                'Version': '2012-10-17',
                'Statement': [
                    {
                        'Effect': 'Allow',
                        'Principal': {'Service': 'eks.amazonaws.com'},
                        'Action': 'sts:AssumeRole',
                    }
                ],
            },
            'MaxSessionDuration': 3600,
            'Description': 'Test role',
            'Tags': [{'Key': 'Environment', 'Value': 'Test'}],
        }
    }
    mock_iam_client.get_role.return_value = mock_role_response

    # Mock the list_attached_role_policies response
    mock_attached_policies_response = {
        'AttachedPolicies': [
            {
                'PolicyName': 'AmazonEKSClusterPolicy',
                'PolicyArn': 'arn:aws:iam::aws:policy/AmazonEKSClusterPolicy',
            }
        ]
    }
    mock_iam_client.list_attached_role_policies.return_value = mock_attached_policies_response

    # Mock the get_policy response
    mock_policy_response = {
        'Policy': {
            'PolicyName': 'AmazonEKSClusterPolicy',
            'PolicyId': 'ANPAEXAMPLEID',
            'Arn': 'arn:aws:iam::aws:policy/AmazonEKSClusterPolicy',
            'Path': '/',
            'DefaultVersionId': 'v1',
            'AttachmentCount': 1,
            'IsAttachable': True,
            'CreateDate': MagicMock(isoformat=lambda: '2023-01-01T00:00:00Z'),
            'UpdateDate': MagicMock(isoformat=lambda: '2023-01-01T00:00:00Z'),
            'Description': 'Policy for EKS clusters',
        }
    }
    mock_iam_client.get_policy.return_value = mock_policy_response

    # Make get_policy_version raise an exception
    mock_iam_client.get_policy_version.side_effect = Exception('Version not found')

    # Mock the list_role_policies response
    mock_iam_client.list_role_policies.return_value = {'PolicyNames': []}

    # Create a mock MCP server
    mock_mcp = MagicMock()

    # Initialize the IAM handler with the mock MCP server
    handler = IAMHandler(mock_mcp)

    # Create a mock context
    mock_ctx = MagicMock(spec=Context)

    # Call the get_policies_for_role method
    result = await handler.get_policies_for_role(mock_ctx, role_name='test-role')

    # Verify the result
    assert not result.isError
    assert len(result.content) == 1
    assert result.content[0].type == 'text'
    assert 'Successfully retrieved details for IAM role: test-role' in result.content[0].text
    assert result.role_arn == 'arn:aws:iam::123456789012:role/test-role'
    assert result.description == 'Test role'
    assert len(result.managed_policies) == 1
    assert result.managed_policies[0].policy_type == 'Managed'
    assert result.managed_policies[0].description == 'Policy for EKS clusters'
    assert result.managed_policies[0].policy_document is None  # Should be None due to the error
    assert result.inline_policies == []


@pytest.mark.asyncio
@patch('awslabs.eks_mcp_server.aws_helper.AwsHelper.create_boto3_client')
async def test_get_inline_policies_error(mock_create_client):
    """Test _get_inline_policies method when an error occurs."""
    # Create a mock IAM client
    mock_iam_client = MagicMock()
    mock_create_client.return_value = mock_iam_client

    # Mock the get_role response
    mock_role_response = {
        'Role': {
            'RoleName': 'test-role',
            'RoleId': 'AROAEXAMPLEID',
            'Arn': 'arn:aws:iam::123456789012:role/test-role',
            'Path': '/',
            'CreateDate': MagicMock(isoformat=lambda: '2023-01-01T00:00:00Z'),
            'AssumeRolePolicyDocument': {
                'Version': '2012-10-17',
                'Statement': [
                    {
                        'Effect': 'Allow',
                        'Principal': {'Service': 'eks.amazonaws.com'},
                        'Action': 'sts:AssumeRole',
                    }
                ],
            },
            'MaxSessionDuration': 3600,
            'Description': 'Test role',
            'Tags': [{'Key': 'Environment', 'Value': 'Test'}],
        }
    }
    mock_iam_client.get_role.return_value = mock_role_response

    # Mock the list_attached_role_policies response
    mock_iam_client.list_attached_role_policies.return_value = {'AttachedPolicies': []}

    # Mock the list_role_policies response
    mock_inline_policies_response = {'PolicyNames': ['test-inline-policy']}
    mock_iam_client.list_role_policies.return_value = mock_inline_policies_response

    # Make get_role_policy raise an exception
    mock_iam_client.get_role_policy.side_effect = Exception('Policy not found')

    # Create a mock MCP server
    mock_mcp = MagicMock()

    # Initialize the IAM handler with the mock MCP server
    handler = IAMHandler(mock_mcp)

    # Create a mock context
    mock_ctx = MagicMock(spec=Context)

    # Call the get_policies_for_role method
    result = await handler.get_policies_for_role(mock_ctx, role_name='test-role')

    # Verify the result indicates an error
    assert result.isError
    assert len(result.content) == 1
    assert result.content[0].type == 'text'
    assert 'Failed to describe IAM role' in result.content[0].text
    assert 'Policy not found' in result.content[0].text
    assert result.role_arn == ''
    assert result.assume_role_policy_document == {}
    assert result.description is None
    assert result.managed_policies == []
    assert result.inline_policies == []


@pytest.mark.asyncio
@patch('awslabs.eks_mcp_server.aws_helper.AwsHelper.create_boto3_client')
async def test_add_inline_policy_write_access_disabled(mock_create_client):
    """Test add_inline_policy method when write access is disabled."""
    # Create a mock IAM client
    mock_iam_client = MagicMock()
    mock_create_client.return_value = mock_iam_client

    # Create a mock MCP server
    mock_mcp = MagicMock()

    # Initialize the IAM handler with the mock MCP server with write access disabled
    handler = IAMHandler(mock_mcp, allow_write=False)

    # Create a mock context
    mock_ctx = MagicMock(spec=Context)

    # Define the permissions to add
    permissions = {
        'Effect': 'Allow',
        'Action': 's3:PutObject',
        'Resource': 'arn:aws:s3:::example-bucket/*',
    }

    # Call the add_inline_policy method
    result = await handler.add_inline_policy(
        mock_ctx, policy_name='test-inline-policy', role_name='test-role', permissions=permissions
    )

    # Verify the result indicates an error because write access is disabled
    assert result.isError
    assert len(result.content) == 1
    assert result.content[0].type == 'text'
    assert 'Adding inline policies requires --allow-write flag' in result.content[0].text
    assert result.policy_name == 'test-inline-policy'
    assert result.role_name == 'test-role'
    assert result.permissions_added == {}

    # Verify that no AWS API calls were made
    mock_create_client.assert_not_called()


@pytest.mark.asyncio
@patch('awslabs.eks_mcp_server.aws_helper.AwsHelper.create_boto3_client')
async def test_add_inline_policy_general_error(mock_create_client):
    """Test add_inline_policy method when a general error occurs."""
    # Create a mock IAM client
    mock_iam_client = MagicMock()
    mock_create_client.return_value = mock_iam_client

    # Make create_boto3_client raise an exception
    mock_create_client.side_effect = Exception('AWS credentials not found')

    # Create a mock MCP server
    mock_mcp = MagicMock()

    # Initialize the IAM handler with the mock MCP server with write access enabled
    handler = IAMHandler(mock_mcp, allow_write=True)

    # Create a mock context
    mock_ctx = MagicMock(spec=Context)

    # Define the permissions to add
    permissions = {
        'Effect': 'Allow',
        'Action': 's3:PutObject',
        'Resource': 'arn:aws:s3:::example-bucket/*',
    }

    # Call the add_inline_policy method
    result = await handler.add_inline_policy(
        mock_ctx, policy_name='test-inline-policy', role_name='test-role', permissions=permissions
    )

    # Verify the result indicates an error
    assert result.isError
    assert len(result.content) == 1
    assert result.content[0].type == 'text'
    assert 'Failed to create inline policy' in result.content[0].text
    assert 'AWS credentials not found' in result.content[0].text
    assert result.policy_name == 'test-inline-policy'
    assert result.role_name == 'test-role'
    assert result.permissions_added == {}
