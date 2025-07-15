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

import json
import pytest
from awslabs.aws_dataprocessing_mcp_server.handlers.commons.common_resource_handler import (
    CommonResourceHandler,
)
from botocore.exceptions import ClientError
from datetime import datetime
from mcp.server.fastmcp import Context
from typing import Type
from unittest.mock import Mock, patch


class Exceptions:
    """Mock exceptions class for IAM client testing."""

    class NoSuchEntityException(ClientError):
        """Mock NoSuchEntityException for testing IAM client exceptions."""

        def __init__(self):
            """Initialize the NoSuchEntityException with appropriate error response."""
            operation_name = 'GetRolePolicy'
            error_response = {
                'Error': {'Code': 'NoSuchEntity', 'Message': 'Role policy not found'}
            }
            super().__init__(error_response, operation_name)


class MockIAMClient(Mock):
    """Mock IAM client for testing with exception handling capabilities."""

    exceptions: Type[Exceptions]

    def __init__(self, *args, **kwargs):
        """Initialize the MockIAMClient with exceptions property."""
        super().__init__(*args, **kwargs)
        # Set up exceptions as a property
        self.exceptions = Exceptions


@pytest.fixture
def mock_iam_client():
    """Create a mock IAM client instance for testing."""
    return Mock()


@pytest.fixture
def mock_s3_client():
    """Create a mock S3 client instance for testing."""
    return Mock()


@pytest.fixture
def mock_aws_helper():
    """Create a mock AwsHelper instance for testing."""
    with patch(
        'awslabs.aws_dataprocessing_mcp_server.handlers.commons.common_resource_handler.AwsHelper'
    ) as mock:
        mock.create_boto3_client.return_value = Mock()
        yield mock


@pytest.fixture
def handler(mock_aws_helper):
    """Create a mock CommonResourceHandler instance for testing."""
    mcp = Mock()
    return CommonResourceHandler(mcp, allow_write=True)


@pytest.fixture
def read_only_handler(mock_aws_helper):
    """Create a mock CommonResourceHandler instance with read-only access for testing."""
    mcp = Mock()
    return CommonResourceHandler(mcp, allow_write=False)


@pytest.fixture
def mock_context():
    """Create a mock context instance for testing."""
    return Mock(spec=Context)


# ============================================================================
# IAM Operations Tests
# ============================================================================


@pytest.mark.asyncio
async def test_get_policies_for_role_success(handler, mock_iam_client):
    """Test successful retrieval of policies for a role."""
    handler.iam_client = mock_iam_client

    # Mock role response
    mock_iam_client.get_role.return_value = {
        'Role': {
            'Arn': 'arn:aws:iam::123456789012:role/test-role',
            'AssumeRolePolicyDocument': {
                'Version': '2012-10-17',
                'Statement': [
                    {
                        'Effect': 'Allow',
                        'Principal': {'Service': 'glue.amazonaws.com'},
                        'Action': 'sts:AssumeRole',
                    }
                ],
            },
            'Description': 'Test role description',
        }
    }

    # Mock managed policies
    mock_iam_client.list_attached_role_policies.return_value = {
        'AttachedPolicies': [
            {
                'PolicyName': 'TestManagedPolicy',
                'PolicyArn': 'arn:aws:iam::aws:policy/TestManagedPolicy',
            }
        ]
    }

    mock_iam_client.get_policy.return_value = {
        'Policy': {'DefaultVersionId': 'v1', 'Description': 'Test managed policy'}
    }

    mock_iam_client.get_policy_version.return_value = {
        'PolicyVersion': {
            'Document': {
                'Version': '2012-10-17',
                'Statement': [{'Effect': 'Allow', 'Action': 's3:GetObject', 'Resource': '*'}],
            }
        }
    }

    # Mock inline policies
    mock_iam_client.list_role_policies.return_value = {'PolicyNames': ['TestInlinePolicy']}

    mock_iam_client.get_role_policy.return_value = {
        'PolicyDocument': {
            'Version': '2012-10-17',
            'Statement': [{'Effect': 'Allow', 'Action': 's3:PutObject', 'Resource': '*'}],
        }
    }

    ctx = Mock()
    response = await handler.get_policies_for_role(ctx, role_name='test-role')

    assert not response.isError
    assert response.role_arn == 'arn:aws:iam::123456789012:role/test-role'
    assert response.description == 'Test role description'
    assert len(response.managed_policies) == 1
    assert len(response.inline_policies) == 1
    assert response.managed_policies[0].policy_type == 'Managed'
    assert response.inline_policies[0].policy_type == 'Inline'


@pytest.mark.asyncio
async def test_get_policies_for_role_with_string_assume_role_policy(handler, mock_iam_client):
    """Test retrieval of policies for a role with string assume role policy document."""
    handler.iam_client = mock_iam_client

    # Mock role response with string assume role policy document
    assume_role_policy_str = json.dumps(
        {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Effect': 'Allow',
                    'Principal': {'Service': 'glue.amazonaws.com'},
                    'Action': 'sts:AssumeRole',
                }
            ],
        }
    )

    mock_iam_client.get_role.return_value = {
        'Role': {
            'Arn': 'arn:aws:iam::123456789012:role/test-role',
            'AssumeRolePolicyDocument': assume_role_policy_str,
            'Description': 'Test role description',
        }
    }

    # Mock empty policies
    mock_iam_client.list_attached_role_policies.return_value = {'AttachedPolicies': []}
    mock_iam_client.list_role_policies.return_value = {'PolicyNames': []}

    ctx = Mock()
    response = await handler.get_policies_for_role(ctx, role_name='test-role')

    assert not response.isError
    assert response.assume_role_policy_document['Version'] == '2012-10-17'
    assert len(response.assume_role_policy_document['Statement']) == 1


@pytest.mark.asyncio
async def test_get_policies_for_role_error_handling(handler, mock_iam_client):
    """Test error handling when getting policies for a role fails."""
    handler.iam_client = mock_iam_client
    mock_iam_client.get_role.side_effect = ClientError(
        {'Error': {'Code': 'NoSuchEntity', 'Message': 'Role not found'}}, 'GetRole'
    )

    ctx = Mock()
    response = await handler.get_policies_for_role(ctx, role_name='nonexistent-role')

    assert response.isError
    assert 'Failed to describe IAM role' in response.content[0].text
    assert response.role_arn == ''


@pytest.mark.asyncio
async def test_add_inline_policy_success(handler):
    """Test successful addition of an inline policy."""
    mock_iam_local_client = MockIAMClient()
    mock_iam_local_client.get_role_policy.side_effect = (
        mock_iam_local_client.exceptions.NoSuchEntityException()
    )
    handler.iam_client = mock_iam_local_client

    permissions = {
        'Effect': 'Allow',
        'Action': ['s3:GetObject', 's3:PutObject'],
        'Resource': 'arn:aws:s3:::test-bucket/*',
    }

    ctx = Mock()
    response = await handler.add_inline_policy(
        ctx, policy_name='test-policy', role_name='test-role', permissions=permissions
    )

    assert not response.isError
    assert response.policy_name == 'test-policy'
    assert response.role_name == 'test-role'
    assert response.permissions_added == permissions
    mock_iam_local_client.put_role_policy.assert_called_once()


@pytest.mark.asyncio
async def test_add_inline_policy_with_list_permissions(handler):
    """Test successful addition of an inline policy with list of permissions."""
    mock_iam_local_client = MockIAMClient()
    mock_iam_local_client.get_role_policy.side_effect = (
        mock_iam_local_client.exceptions.NoSuchEntityException()
    )
    mock_iam_local_client.put_role_policy.return_value = {
        'ResponseMetadata': {
            'test': 'dummy',
        },
    }
    handler.iam_client = mock_iam_local_client

    permissions = [
        {'Effect': 'Allow', 'Action': ['s3:GetObject'], 'Resource': 'arn:aws:s3:::test-bucket/*'},
        {'Effect': 'Allow', 'Action': ['s3:PutObject'], 'Resource': 'arn:aws:s3:::test-bucket/*'},
    ]

    ctx = Mock()
    response = await handler.add_inline_policy(
        ctx, policy_name='test-policy', role_name='test-role', permissions=permissions
    )

    assert not response.isError
    assert response.policy_name == 'test-policy'
    assert response.role_name == 'test-role'
    assert response.permissions_added == permissions


@pytest.mark.asyncio
async def test_add_inline_policy_without_write_permission(read_only_handler):
    """Test that adding inline policy fails when write access is disabled."""
    ctx = Mock()
    response = await read_only_handler.add_inline_policy(
        ctx,
        policy_name='test-policy',
        role_name='test-role',
        permissions={'Effect': 'Allow', 'Action': 's3:GetObject', 'Resource': '*'},
    )

    assert response.isError
    assert 'requires --allow-write flag' in response.content[0].text


@pytest.mark.asyncio
async def test_add_inline_policy_already_exists(handler, mock_iam_client):
    """Test that adding inline policy fails when policy already exists."""
    handler.iam_client = mock_iam_client

    # Mock that policy already exists
    mock_iam_client.get_role_policy.return_value = {
        'PolicyDocument': {'Version': '2012-10-17', 'Statement': []}
    }

    ctx = Mock()
    response = await handler.add_inline_policy(
        ctx,
        policy_name='existing-policy',
        role_name='test-role',
        permissions={'Effect': 'Allow', 'Action': 's3:GetObject', 'Resource': '*'},
    )

    assert response.isError
    assert 'already exists' in response.content[0].text


@pytest.mark.asyncio
async def test_create_data_processing_role_glue_success(handler, mock_iam_client):
    """Test successful creation of a Glue data processing role."""
    handler.iam_client = mock_iam_client

    mock_iam_client.create_role.return_value = {
        'Role': {'Arn': 'arn:aws:iam::123456789012:role/test-glue-role'}
    }

    ctx = Mock()
    response = await handler.create_data_processing_role(
        ctx,
        role_name='test-glue-role',
        service_type='glue',
        description='Test Glue role',
        managed_policy_arns=['arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole'],
    )

    assert not response.isError
    assert response.role_name == 'test-glue-role'
    assert response.role_arn == 'arn:aws:iam::123456789012:role/test-glue-role'

    # Verify create_role was called with correct trust relationship
    create_role_call = mock_iam_client.create_role.call_args
    assume_role_policy = json.loads(create_role_call[1]['AssumeRolePolicyDocument'])
    assert assume_role_policy['Statement'][0]['Principal']['Service'] == 'glue.amazonaws.com'

    # Verify managed policy was attached
    mock_iam_client.attach_role_policy.assert_called_once_with(
        RoleName='test-glue-role',
        PolicyArn='arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole',
    )


@pytest.mark.asyncio
async def test_create_data_processing_role_emr_success(handler, mock_iam_client):
    """Test successful creation of an EMR data processing role."""
    handler.iam_client = mock_iam_client

    mock_iam_client.create_role.return_value = {
        'Role': {'Arn': 'arn:aws:iam::123456789012:role/test-emr-role'}
    }

    ctx = Mock()
    response = await handler.create_data_processing_role(
        ctx, role_name='test-emr-role', service_type='emr'
    )

    assert not response.isError
    assert response.role_name == 'test-emr-role'

    # Verify create_role was called with correct trust relationship
    create_role_call = mock_iam_client.create_role.call_args
    assume_role_policy = json.loads(create_role_call[1]['AssumeRolePolicyDocument'])
    assert (
        assume_role_policy['Statement'][0]['Principal']['Service']
        == 'elasticmapreduce.amazonaws.com'
    )


@pytest.mark.asyncio
async def test_create_data_processing_role_athena_success(handler, mock_iam_client):
    """Test successful creation of an Athena data processing role."""
    handler.iam_client = mock_iam_client

    mock_iam_client.create_role.return_value = {
        'Role': {'Arn': 'arn:aws:iam::123456789012:role/test-athena-role'}
    }

    ctx = Mock()
    response = await handler.create_data_processing_role(
        ctx, role_name='test-athena-role', service_type='athena'
    )

    assert not response.isError
    assert response.role_name == 'test-athena-role'

    # Verify create_role was called with correct trust relationship
    create_role_call = mock_iam_client.create_role.call_args
    assume_role_policy = json.loads(create_role_call[1]['AssumeRolePolicyDocument'])
    assert assume_role_policy['Statement'][0]['Principal']['Service'] == 'athena.amazonaws.com'


@pytest.mark.asyncio
async def test_create_data_processing_role_with_inline_policy(handler, mock_iam_client):
    """Test successful creation of a role with inline policy."""
    handler.iam_client = mock_iam_client

    mock_iam_client.create_role.return_value = {
        'Role': {'Arn': 'arn:aws:iam::123456789012:role/test-role'}
    }

    inline_policy = {
        'Effect': 'Allow',
        'Action': ['s3:GetObject'],
        'Resource': 'arn:aws:s3:::test-bucket/*',
    }

    ctx = Mock()
    response = await handler.create_data_processing_role(
        ctx, role_name='test-role', service_type='glue', inline_policy=inline_policy
    )

    assert not response.isError

    # Verify inline policy was added
    mock_iam_client.put_role_policy.assert_called_once()
    put_policy_call = mock_iam_client.put_role_policy.call_args
    policy_document = json.loads(put_policy_call[1]['PolicyDocument'])
    assert policy_document['Statement'][0]['Action'] == ['s3:GetObject']


@pytest.mark.asyncio
async def test_create_data_processing_role_invalid_service_type(handler):
    """Test that creating role fails with invalid service type."""
    ctx = Mock()
    response = await handler.create_data_processing_role(
        ctx, role_name='test-role', service_type='invalid-service'
    )

    assert response.isError
    assert 'Invalid service type' in response.content[0].text


@pytest.mark.asyncio
async def test_create_data_processing_role_without_write_permission(read_only_handler):
    """Test that creating role fails when write access is disabled."""
    ctx = Mock()
    response = await read_only_handler.create_data_processing_role(
        ctx, role_name='test-role', service_type='glue'
    )

    assert response.isError
    assert 'requires --allow-write flag' in response.content[0].text


@pytest.mark.asyncio
async def test_get_roles_for_service_success(handler, mock_iam_client):
    """Test successful retrieval of roles for a service."""
    handler.iam_client = mock_iam_client

    # Mock paginator
    mock_paginator = Mock()
    mock_iam_client.get_paginator.return_value = mock_paginator

    # Mock role data
    mock_paginator.paginate.return_value = [
        {
            'Roles': [
                {
                    'RoleName': 'glue-role-1',
                    'Arn': 'arn:aws:iam::123456789012:role/glue-role-1',
                    'Description': 'Glue role 1',
                    'CreateDate': datetime(2023, 1, 1),
                    'AssumeRolePolicyDocument': {
                        'Version': '2012-10-17',
                        'Statement': [
                            {
                                'Effect': 'Allow',
                                'Principal': {'Service': 'glue.amazonaws.com'},
                                'Action': 'sts:AssumeRole',
                            }
                        ],
                    },
                },
                {
                    'RoleName': 'emr-role-1',
                    'Arn': 'arn:aws:iam::123456789012:role/emr-role-1',
                    'CreateDate': datetime(2023, 1, 2),
                    'AssumeRolePolicyDocument': {
                        'Version': '2012-10-17',
                        'Statement': [
                            {
                                'Effect': 'Allow',
                                'Principal': {'Service': 'elasticmapreduce.amazonaws.com'},
                                'Action': 'sts:AssumeRole',
                            }
                        ],
                    },
                },
            ]
        }
    ]

    ctx = Mock()
    response = await handler.get_roles_for_service(ctx, service_type='glue')

    assert not response.isError
    assert response.service_type == 'glue'
    assert len(response.roles) == 1  # Only the Glue role should be returned
    assert response.roles[0].role_name == 'glue-role-1'


@pytest.mark.asyncio
async def test_get_roles_for_service_with_string_assume_role_policy(handler, mock_iam_client):
    """Test retrieval of roles for a service with string assume role policy document."""
    handler.iam_client = mock_iam_client

    # Mock paginator
    mock_paginator = Mock()
    mock_iam_client.get_paginator.return_value = mock_paginator

    # Mock role data with string assume role policy document
    assume_role_policy_str = json.dumps(
        {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Effect': 'Allow',
                    'Principal': {'Service': 'glue.amazonaws.com'},
                    'Action': 'sts:AssumeRole',
                }
            ],
        }
    )

    mock_paginator.paginate.return_value = [
        {
            'Roles': [
                {
                    'RoleName': 'glue-role-1',
                    'Arn': 'arn:aws:iam::123456789012:role/glue-role-1',
                    'CreateDate': datetime(2023, 1, 1),
                    'AssumeRolePolicyDocument': assume_role_policy_str,
                }
            ]
        }
    ]

    ctx = Mock()
    response = await handler.get_roles_for_service(ctx, service_type='glue')

    assert not response.isError
    assert len(response.roles) == 1
    assert response.roles[0].role_name == 'glue-role-1'


@pytest.mark.asyncio
async def test_get_roles_for_service_error_handling(handler, mock_iam_client):
    """Test error handling when getting roles for a service fails."""
    handler.iam_client = mock_iam_client
    mock_iam_client.get_paginator.side_effect = ClientError(
        {'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}}, 'ListRoles'
    )

    ctx = Mock()
    response = await handler.get_roles_for_service(ctx, service_type='glue')

    assert response.isError
    assert 'Failed to list IAM roles' in response.content[0].text


# ============================================================================
# S3 Operations Tests
# ============================================================================


@pytest.mark.asyncio
async def test_list_s3_buckets_success(handler, mock_s3_client):
    """Test successful listing of S3 buckets."""
    handler.s3_client = mock_s3_client

    # Mock list_buckets response
    mock_s3_client.list_buckets.return_value = {
        'Buckets': [
            {'Name': 'test-glue-bucket', 'CreationDate': datetime(2023, 1, 1)},
            {'Name': 'other-bucket', 'CreationDate': datetime(2023, 1, 2)},
        ]
    }

    # Mock bucket location
    mock_s3_client.get_bucket_location.return_value = {'LocationConstraint': 'us-east-1'}

    # Mock list_objects_v2 response
    mock_s3_client.list_objects_v2.return_value = {
        'KeyCount': 5,
        'Contents': [{'LastModified': datetime(2023, 6, 1)}],
    }

    ctx = Mock()
    response = await handler.list_s3_buckets(ctx, region='us-east-1')

    assert not response.isError
    assert response.region == 'us-east-1'
    assert response.bucket_count == 1  # Only the bucket with 'glue' in name
    assert len(response.buckets) == 1
    assert response.buckets[0].name == 'test-glue-bucket'


@pytest.mark.asyncio
async def test_list_s3_buckets_with_environment_region(handler, mock_s3_client):
    """Test listing S3 buckets using environment region."""
    handler.s3_client = mock_s3_client

    with patch('os.getenv', return_value='us-west-2'):
        mock_s3_client.list_buckets.return_value = {'Buckets': []}

        ctx = Mock()
        response = await handler.list_s3_buckets(ctx)

        assert not response.isError
        assert response.region == 'us-west-2'


@pytest.mark.asyncio
async def test_list_s3_buckets_error_handling(handler, mock_s3_client):
    """Test error handling when listing S3 buckets fails."""
    handler.s3_client = mock_s3_client
    mock_s3_client.list_buckets.side_effect = ClientError(
        {'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}}, 'ListBuckets'
    )

    ctx = Mock()
    response = await handler.list_s3_buckets(ctx)

    assert response.isError
    assert 'AWS Error' in response.content[0].text


@pytest.mark.asyncio
async def test_upload_to_s3_success(handler, mock_s3_client):
    """Test successful upload to S3."""
    handler.s3_client = mock_s3_client

    # Mock bucket location
    mock_s3_client.get_bucket_location.return_value = {'LocationConstraint': 'us-east-1'}

    code_content = "print('Hello, World!')"

    ctx = Mock()
    response = await handler.upload_to_s3(
        ctx, code_content=code_content, bucket_name='test-bucket', s3_key='scripts/test.py'
    )

    assert not response.isError
    assert response.s3_uri == 's3://test-bucket/scripts/test.py'
    assert response.bucket_name == 'test-bucket'
    assert response.s3_key == 'scripts/test.py'

    # Verify put_object was called
    mock_s3_client.put_object.assert_called_once_with(
        Body=code_content, Bucket='test-bucket', Key='scripts/test.py', ContentType='text/x-python'
    )


@pytest.mark.asyncio
async def test_upload_to_s3_make_public(handler, mock_s3_client):
    """Test successful upload to S3 with public access."""
    handler.s3_client = mock_s3_client

    # Mock bucket location
    mock_s3_client.get_bucket_location.return_value = {'LocationConstraint': 'us-east-1'}

    code_content = "print('Hello, World!')"

    ctx = Mock()
    response = await handler.upload_to_s3(
        ctx,
        code_content=code_content,
        bucket_name='test-bucket',
        s3_key='scripts/test.py',
        make_public=True,
    )

    assert not response.isError

    # Verify put_object_acl was called
    mock_s3_client.put_object_acl.assert_called_once_with(
        Bucket='test-bucket', Key='scripts/test.py', ACL='public-read'
    )


@pytest.mark.asyncio
async def test_upload_to_s3_without_write_permission(read_only_handler):
    """Test that uploading to S3 fails when write access is disabled."""
    ctx = Mock()
    response = await read_only_handler.upload_to_s3(
        ctx, code_content="print('test')", bucket_name='test-bucket', s3_key='test.py'
    )

    assert response.isError
    assert 'requires --allow-write flag' in response.content[0].text


@pytest.mark.asyncio
async def test_upload_to_s3_bucket_not_found(handler, mock_s3_client):
    """Test upload to S3 when bucket doesn't exist."""
    handler.s3_client = mock_s3_client

    # Mock bucket not found
    mock_s3_client.head_bucket.side_effect = ClientError(
        {'Error': {'Code': '404', 'Message': 'Not Found'}}, 'HeadBucket'
    )

    ctx = Mock()
    response = await handler.upload_to_s3(
        ctx, code_content="print('test')", bucket_name='nonexistent-bucket', s3_key='test.py'
    )

    assert response.isError
    assert 'does not exist' in response.content[0].text


@pytest.mark.asyncio
async def test_analyze_s3_usage_for_data_processing_success(handler, mock_s3_client):
    """Test successful S3 usage analysis."""
    handler.s3_client = mock_s3_client

    # Mock list_buckets response
    mock_s3_client.list_buckets.return_value = {'Buckets': [{'Name': 'test-glue-bucket'}]}

    # Mock list_objects_v2 response
    mock_s3_client.list_objects_v2.return_value = {
        'KeyCount': 1,
        'Contents': [{'LastModified': datetime(2023, 6, 1)}],
    }

    # Mock AWS service clients
    with patch(
        'awslabs.aws_dataprocessing_mcp_server.handlers.commons.common_resource_handler.AwsHelper'
    ) as mock_aws_helper:
        mock_glue_client = Mock()
        mock_athena_client = Mock()
        mock_emr_client = Mock()

        mock_aws_helper.create_boto3_client.side_effect = lambda service: {
            'glue': mock_glue_client,
            'athena': mock_athena_client,
            'emr': mock_emr_client,
        }[service]

        # Mock service responses
        mock_glue_client.get_connections.return_value = {'ConnectionList': []}
        mock_glue_client.get_crawlers.return_value = {'Crawlers': []}
        mock_glue_client.get_jobs.return_value = {'Jobs': []}
        mock_athena_client.list_work_groups.return_value = {'WorkGroups': []}
        mock_emr_client.list_clusters.return_value = {'Clusters': []}

        ctx = Mock()
        response = await handler.analyze_s3_usage_for_data_processing(ctx)

        assert not response.isError
        assert 'S3 Usage Analysis' in response.analysis_summary
        assert response.service_usage is not None
        assert 'glue' in response.service_usage
        assert 'athena' in response.service_usage
        assert 'emr' in response.service_usage
        assert 'idle' in response.service_usage
        assert 'unknown' in response.service_usage


@pytest.mark.asyncio
async def test_analyze_s3_usage_specific_bucket(handler, mock_s3_client):
    """Test S3 usage analysis for a specific bucket."""
    handler.s3_client = mock_s3_client

    # Mock list_objects_v2 response
    mock_s3_client.list_objects_v2.return_value = {
        'KeyCount': 1,
        'Contents': [{'LastModified': datetime(2023, 6, 1)}],
    }

    # Mock AWS service clients
    with patch(
        'awslabs.aws_dataprocessing_mcp_server.handlers.commons.common_resource_handler.AwsHelper'
    ) as mock_aws_helper:
        mock_glue_client = Mock()
        mock_athena_client = Mock()
        mock_emr_client = Mock()

        mock_aws_helper.create_boto3_client.side_effect = lambda service: {
            'glue': mock_glue_client,
            'athena': mock_athena_client,
            'emr': mock_emr_client,
        }[service]

        # Mock service responses
        mock_glue_client.get_connections.return_value = {'ConnectionList': []}
        mock_glue_client.get_crawlers.return_value = {'Crawlers': []}
        mock_glue_client.get_jobs.return_value = {'Jobs': []}
        mock_athena_client.list_work_groups.return_value = {'WorkGroups': []}
        mock_emr_client.list_clusters.return_value = {'Clusters': []}

        ctx = Mock()
        response = await handler.analyze_s3_usage_for_data_processing(
            ctx, bucket_name='test-bucket'
        )

        assert not response.isError
        assert 'S3 Usage Analysis' in response.analysis_summary


@pytest.mark.asyncio
async def test_analyze_s3_usage_bucket_not_found(handler, mock_s3_client):
    """Test S3 usage analysis when specific bucket doesn't exist."""
    handler.s3_client = mock_s3_client

    # Mock bucket not found
    mock_s3_client.head_bucket.side_effect = ClientError(
        {'Error': {'Code': '404', 'Message': 'Not Found'}}, 'HeadBucket'
    )

    ctx = Mock()
    response = await handler.analyze_s3_usage_for_data_processing(
        ctx, bucket_name='nonexistent-bucket'
    )

    assert response.isError
    assert 'does not exist or is not accessible' in response.content[0].text


@pytest.mark.asyncio
async def test_analyze_s3_usage_error_handling(handler, mock_s3_client):
    """Test error handling when S3 usage analysis fails."""
    handler.s3_client = mock_s3_client
    mock_s3_client.list_buckets.side_effect = ClientError(
        {'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}}, 'ListBuckets'
    )

    ctx = Mock()
    response = await handler.analyze_s3_usage_for_data_processing(ctx)

    assert response.isError
    assert 'AWS Error' in response.content[0].text


# ============================================================================
# Helper Methods Tests
# ============================================================================


def test_get_trust_relationship_for_service_glue(handler):
    """Test trust relationship generation for Glue service."""
    trust_relationship = handler._get_trust_relationship_for_service('glue')

    assert trust_relationship['Version'] == '2012-10-17'
    assert len(trust_relationship['Statement']) == 1
    assert trust_relationship['Statement'][0]['Effect'] == 'Allow'
    assert trust_relationship['Statement'][0]['Principal']['Service'] == 'glue.amazonaws.com'
    assert trust_relationship['Statement'][0]['Action'] == 'sts:AssumeRole'


def test_get_trust_relationship_for_service_emr(handler):
    """Test trust relationship generation for EMR service."""
    trust_relationship = handler._get_trust_relationship_for_service('emr')

    assert (
        trust_relationship['Statement'][0]['Principal']['Service']
        == 'elasticmapreduce.amazonaws.com'
    )


def test_get_trust_relationship_for_service_athena(handler):
    """Test trust relationship generation for Athena service."""
    trust_relationship = handler._get_trust_relationship_for_service('athena')

    assert trust_relationship['Statement'][0]['Principal']['Service'] == 'athena.amazonaws.com'


def test_get_service_principal_known_services(handler):
    """Test service principal mapping for known services."""
    assert handler._get_service_principal('glue') == 'glue.amazonaws.com'
    assert handler._get_service_principal('emr') == 'elasticmapreduce.amazonaws.com'
    assert handler._get_service_principal('athena') == 'athena.amazonaws.com'
    assert handler._get_service_principal('lambda') == 'lambda.amazonaws.com'
    assert handler._get_service_principal('ec2') == 'ec2.amazonaws.com'


def test_get_service_principal_unknown_service(handler):
    """Test service principal mapping for unknown services."""
    assert handler._get_service_principal('unknown-service') == 'unknown-service.amazonaws.com'


def test_can_be_assumed_by_service_single_service(handler):
    """Test checking if role can be assumed by service with single service principal."""
    assume_role_policy = {
        'Version': '2012-10-17',
        'Statement': [
            {
                'Effect': 'Allow',
                'Principal': {'Service': 'glue.amazonaws.com'},
                'Action': 'sts:AssumeRole',
            }
        ],
    }

    assert handler._can_be_assumed_by_service(assume_role_policy, 'glue.amazonaws.com')
    assert not handler._can_be_assumed_by_service(assume_role_policy, 'emr.amazonaws.com')


def test_can_be_assumed_by_service_multiple_services(handler):
    """Test checking if role can be assumed by service with multiple service principals."""
    assume_role_policy = {
        'Version': '2012-10-17',
        'Statement': [
            {
                'Effect': 'Allow',
                'Principal': {'Service': ['glue.amazonaws.com', 'emr.amazonaws.com']},
                'Action': 'sts:AssumeRole',
            }
        ],
    }

    assert handler._can_be_assumed_by_service(assume_role_policy, 'glue.amazonaws.com')
    assert handler._can_be_assumed_by_service(assume_role_policy, 'emr.amazonaws.com')
    assert not handler._can_be_assumed_by_service(assume_role_policy, 'athena.amazonaws.com')


def test_can_be_assumed_by_service_string_action(handler):
    """Test checking if role can be assumed by service with string action."""
    assume_role_policy = {
        'Version': '2012-10-17',
        'Statement': [
            {
                'Effect': 'Allow',
                'Principal': {'Service': 'glue.amazonaws.com'},
                'Action': 'sts:AssumeRole',
            }
        ],
    }

    assert handler._can_be_assumed_by_service(assume_role_policy, 'glue.amazonaws.com')


def test_can_be_assumed_by_service_deny_effect(handler):
    """Test checking if role can be assumed by service with Deny effect."""
    assume_role_policy = {
        'Version': '2012-10-17',
        'Statement': [
            {
                'Effect': 'Deny',
                'Principal': {'Service': 'glue.amazonaws.com'},
                'Action': 'sts:AssumeRole',
            }
        ],
    }

    # The implementation correctly ignores Deny statements and only processes Allow statements
    assert not handler._can_be_assumed_by_service(assume_role_policy, 'glue.amazonaws.com')


def test_can_be_assumed_by_service_wrong_action(handler):
    """Test checking if role can be assumed by service with wrong action."""
    assume_role_policy = {
        'Version': '2012-10-17',
        'Statement': [
            {
                'Effect': 'Allow',
                'Principal': {'Service': 'glue.amazonaws.com'},
                'Action': 'sts:GetCallerIdentity',
            }
        ],
    }

    assert not handler._can_be_assumed_by_service(assume_role_policy, 'glue.amazonaws.com')


def test_can_be_assumed_by_service_empty_policy(handler):
    """Test checking if role can be assumed by service with empty policy."""
    assert not handler._can_be_assumed_by_service({}, 'glue.amazonaws.com')
    assert not handler._can_be_assumed_by_service({'Statement': []}, 'glue.amazonaws.com')


def test_add_permissions_to_document_single_statement(handler):
    """Test adding single permission statement to policy document."""
    policy_document = {'Version': '2012-10-17', 'Statement': []}
    permissions = {
        'Effect': 'Allow',
        'Action': ['s3:GetObject'],
        'Resource': 'arn:aws:s3:::test-bucket/*',
    }

    handler._add_permissions_to_document(policy_document, permissions)

    assert len(policy_document['Statement']) == 1
    assert policy_document['Statement'][0] == permissions


def test_add_permissions_to_document_multiple_statements(handler):
    """Test adding multiple permission statements to policy document."""
    policy_document = {'Version': '2012-10-17', 'Statement': []}
    permissions = [
        {'Effect': 'Allow', 'Action': ['s3:GetObject'], 'Resource': 'arn:aws:s3:::test-bucket/*'},
        {'Effect': 'Allow', 'Action': ['s3:PutObject'], 'Resource': 'arn:aws:s3:::test-bucket/*'},
    ]

    handler._add_permissions_to_document(policy_document, permissions)

    assert len(policy_document['Statement']) == 2
    assert policy_document['Statement'][0] == permissions[0]
    assert policy_document['Statement'][1] == permissions[1]


# ============================================================================
# Initialization Tests
# ============================================================================


@pytest.mark.asyncio
async def test_initialization_parameters(mock_aws_helper):
    """Test initialization of parameters for CommonResourceHandler object."""
    mcp = Mock()
    handler = CommonResourceHandler(mcp, allow_write=True)

    assert handler.allow_write
    assert handler.mcp == mcp


@pytest.mark.asyncio
async def test_initialization_registers_tools(mock_aws_helper):
    """Test that initialization registers the tools with the MCP server."""
    mcp = Mock()
    CommonResourceHandler(mcp)

    # Verify IAM tools are registered
    mcp.tool.assert_any_call(name='add_inline_policy')
    mcp.tool.assert_any_call(name='get_policies_for_role')
    mcp.tool.assert_any_call(name='create_data_processing_role')
    mcp.tool.assert_any_call(name='get_roles_for_service')

    # Verify S3 tools are registered
    mcp.tool.assert_any_call(name='list_s3_buckets')
    mcp.tool.assert_any_call(name='upload_to_s3')
    mcp.tool.assert_any_call(name='analyze_s3_usage_for_data_processing')


@pytest.mark.asyncio
async def test_initialization_default_parameters(mock_aws_helper):
    """Test initialization with default parameters."""
    mcp = Mock()
    handler = CommonResourceHandler(mcp)

    assert not handler.allow_write  # Default should be False
    assert handler.mcp == mcp
