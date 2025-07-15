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

"""Test cases for common resource models."""

import pytest
from awslabs.aws_dataprocessing_mcp_server.models.common_resource_models import (
    AddInlinePolicyResponse,
    AnalyzeS3UsageResponse,
    BucketInfo,
    CreateRoleResponse,
    ListS3BucketsResponse,
    PolicySummary,
    RoleDescriptionResponse,
    RoleSummary,
    ServiceRolesResponse,
    UploadToS3Response,
)
from mcp.types import TextContent
from pydantic import ValidationError


# Test data
sample_text_content = [TextContent(type='text', text='Test message')]
sample_error_content = [TextContent(type='text', text='Error occurred')]


class TestRoleSummary:
    """Test class for RoleSummary model."""

    def test_role_summary_creation_with_all_fields(self):
        """Test creating RoleSummary with all fields."""
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

        role_summary = RoleSummary(
            role_name='test-role',
            role_arn='arn:aws:iam::123456789012:role/test-role',
            description='Test role description',
            create_date='2023-01-01T00:00:00Z',
            assume_role_policy_document=assume_role_policy,
        )

        assert role_summary.role_name == 'test-role'
        assert role_summary.role_arn == 'arn:aws:iam::123456789012:role/test-role'
        assert role_summary.description == 'Test role description'
        assert role_summary.create_date == '2023-01-01T00:00:00Z'
        assert role_summary.assume_role_policy_document == assume_role_policy

    def test_role_summary_creation_without_description(self):
        """Test creating RoleSummary without optional description."""
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

        role_summary = RoleSummary(
            role_name='test-role',
            role_arn='arn:aws:iam::123456789012:role/test-role',
            create_date='2023-01-01T00:00:00Z',
            assume_role_policy_document=assume_role_policy,
        )

        assert role_summary.role_name == 'test-role'
        assert role_summary.role_arn == 'arn:aws:iam::123456789012:role/test-role'
        assert role_summary.description is None
        assert role_summary.create_date == '2023-01-01T00:00:00Z'
        assert role_summary.assume_role_policy_document == assume_role_policy

    def test_role_summary_validation_missing_required_fields(self):
        """Test RoleSummary validation with missing required fields."""
        with pytest.raises(ValidationError) as exc_info:
            RoleSummary()

        errors = exc_info.value.errors()
        required_fields = {'role_name', 'role_arn', 'create_date', 'assume_role_policy_document'}
        error_fields = {error['loc'][0] for error in errors}
        assert required_fields.issubset(error_fields)

    def test_role_summary_with_complex_policy(self):
        """Test RoleSummary with complex assume role policy."""
        complex_policy = {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Effect': 'Allow',
                    'Principal': {'Service': ['glue.amazonaws.com', 'lambda.amazonaws.com']},
                    'Action': 'sts:AssumeRole',
                    'Condition': {'StringEquals': {'sts:ExternalId': 'unique-external-id'}},
                },
                {
                    'Effect': 'Allow',
                    'Principal': {'AWS': 'arn:aws:iam::123456789012:root'},
                    'Action': 'sts:AssumeRole',
                },
            ],
        }

        role_summary = RoleSummary(
            role_name='complex-role',
            role_arn='arn:aws:iam::123456789012:role/complex-role',
            description='Complex role with multiple principals',
            create_date='2023-01-01T00:00:00Z',
            assume_role_policy_document=complex_policy,
        )

        assert len(role_summary.assume_role_policy_document['Statement']) == 2
        assert 'Condition' in role_summary.assume_role_policy_document['Statement'][0]


class TestServiceRolesResponse:
    """Test class for ServiceRolesResponse model."""

    def test_service_roles_response_creation(self):
        """Test creating ServiceRolesResponse."""
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

        roles = [
            RoleSummary(
                role_name='glue-role-1',
                role_arn='arn:aws:iam::123456789012:role/glue-role-1',
                description='First Glue role',
                create_date='2023-01-01T00:00:00Z',
                assume_role_policy_document=assume_role_policy,
            ),
            RoleSummary(
                role_name='glue-role-2',
                role_arn='arn:aws:iam::123456789012:role/glue-role-2',
                create_date='2023-01-02T00:00:00Z',
                assume_role_policy_document=assume_role_policy,
            ),
        ]

        response = ServiceRolesResponse(
            isError=False, content=sample_text_content, service_type='glue', roles=roles
        )

        assert response.isError is False
        assert response.content == sample_text_content
        assert response.service_type == 'glue'
        assert len(response.roles) == 2
        assert response.roles[0].role_name == 'glue-role-1'
        assert response.roles[1].description is None

    def test_service_roles_response_empty_roles(self):
        """Test ServiceRolesResponse with empty roles list."""
        response = ServiceRolesResponse(
            isError=False, content=sample_text_content, service_type='lambda', roles=[]
        )

        assert response.isError is False
        assert response.service_type == 'lambda'
        assert len(response.roles) == 0

    def test_service_roles_response_error(self):
        """Test ServiceRolesResponse with error."""
        response = ServiceRolesResponse(
            isError=True, content=sample_error_content, service_type='glue', roles=[]
        )

        assert response.isError is True
        assert response.content == sample_error_content
        assert response.service_type == 'glue'
        assert len(response.roles) == 0


class TestPolicySummary:
    """Test class for PolicySummary model."""

    def test_policy_summary_managed_policy(self):
        """Test creating PolicySummary for managed policy."""
        policy_summary = PolicySummary(
            policy_type='managed', description='AWS managed policy for S3 full access'
        )

        assert policy_summary.policy_type == 'managed'
        assert policy_summary.description == 'AWS managed policy for S3 full access'
        assert policy_summary.policy_document is None

    def test_policy_summary_inline_policy(self):
        """Test creating PolicySummary for inline policy."""
        policy_document = {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Effect': 'Allow',
                    'Action': ['s3:GetObject', 's3:PutObject'],
                    'Resource': 'arn:aws:s3:::my-bucket/*',
                }
            ],
        }

        policy_summary = PolicySummary(
            policy_type='inline',
            description='Custom inline policy for S3 access',
            policy_document=policy_document,
        )

        assert policy_summary.policy_type == 'inline'
        assert policy_summary.description == 'Custom inline policy for S3 access'
        assert policy_summary.policy_document == policy_document

    def test_policy_summary_minimal(self):
        """Test creating PolicySummary with minimal fields."""
        policy_summary = PolicySummary(policy_type='managed')

        assert policy_summary.policy_type == 'managed'
        assert policy_summary.description is None
        assert policy_summary.policy_document is None

    def test_policy_summary_validation(self):
        """Test PolicySummary validation."""
        with pytest.raises(ValidationError) as exc_info:
            PolicySummary()

        errors = exc_info.value.errors()
        assert any(error['loc'][0] == 'policy_type' for error in errors)


class TestRoleDescriptionResponse:
    """Test class for RoleDescriptionResponse model."""

    def test_role_description_response_complete(self):
        """Test creating complete RoleDescriptionResponse."""
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

        managed_policies = [
            PolicySummary(policy_type='managed', description='AmazonS3FullAccess'),
            PolicySummary(policy_type='managed', description='AWSGlueServiceRole'),
        ]

        inline_policy_doc = {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Effect': 'Allow',
                    'Action': ['logs:CreateLogGroup', 'logs:CreateLogStream'],
                    'Resource': '*',
                }
            ],
        }

        inline_policies = [
            PolicySummary(
                policy_type='inline',
                description='Custom logging policy',
                policy_document=inline_policy_doc,
            )
        ]

        response = RoleDescriptionResponse(
            isError=False,
            content=sample_text_content,
            role_arn='arn:aws:iam::123456789012:role/test-role',
            assume_role_policy_document=assume_role_policy,
            description='Test role for Glue jobs',
            managed_policies=managed_policies,
            inline_policies=inline_policies,
        )

        assert response.isError is False
        assert response.role_arn == 'arn:aws:iam::123456789012:role/test-role'
        assert response.assume_role_policy_document == assume_role_policy
        assert response.description == 'Test role for Glue jobs'
        assert len(response.managed_policies) == 2
        assert len(response.inline_policies) == 1
        assert response.managed_policies[0].policy_type == 'managed'
        assert response.inline_policies[0].policy_document == inline_policy_doc

    def test_role_description_response_minimal(self):
        """Test creating minimal RoleDescriptionResponse."""
        assume_role_policy = {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Effect': 'Allow',
                    'Principal': {'Service': 'lambda.amazonaws.com'},
                    'Action': 'sts:AssumeRole',
                }
            ],
        }

        response = RoleDescriptionResponse(
            isError=False,
            content=sample_text_content,
            role_arn='arn:aws:iam::123456789012:role/lambda-role',
            assume_role_policy_document=assume_role_policy,
            managed_policies=[],
            inline_policies=[],
        )

        assert response.isError is False
        assert response.role_arn == 'arn:aws:iam::123456789012:role/lambda-role'
        assert response.description is None
        assert len(response.managed_policies) == 0
        assert len(response.inline_policies) == 0

    def test_role_description_response_error(self):
        """Test RoleDescriptionResponse with error."""
        response = RoleDescriptionResponse(
            isError=True,
            content=sample_error_content,
            role_arn='arn:aws:iam::123456789012:role/nonexistent-role',
            assume_role_policy_document={},
            managed_policies=[],
            inline_policies=[],
        )

        assert response.isError is True
        assert response.content == sample_error_content


class TestAddInlinePolicyResponse:
    """Test class for AddInlinePolicyResponse model."""

    def test_add_inline_policy_response_success(self):
        """Test successful AddInlinePolicyResponse."""
        permissions = {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Effect': 'Allow',
                    'Action': ['s3:GetObject', 's3:PutObject'],
                    'Resource': 'arn:aws:s3:::my-bucket/*',
                }
            ],
        }

        response = AddInlinePolicyResponse(
            isError=False,
            content=sample_text_content,
            policy_name='S3AccessPolicy',
            role_name='test-role',
            permissions_added=permissions,
        )

        assert response.isError is False
        assert response.policy_name == 'S3AccessPolicy'
        assert response.role_name == 'test-role'
        assert response.permissions_added == permissions

    def test_add_inline_policy_response_error(self):
        """Test AddInlinePolicyResponse with error."""
        response = AddInlinePolicyResponse(
            isError=True,
            content=sample_error_content,
            policy_name='FailedPolicy',
            role_name='test-role',
            permissions_added={},
        )

        assert response.isError is True
        assert response.content == sample_error_content
        assert response.policy_name == 'FailedPolicy'
        assert response.role_name == 'test-role'

    def test_add_inline_policy_response_complex_permissions(self):
        """Test AddInlinePolicyResponse with complex permissions."""
        complex_permissions = {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Effect': 'Allow',
                    'Action': ['s3:GetObject', 's3:PutObject', 's3:DeleteObject'],
                    'Resource': ['arn:aws:s3:::bucket1/*', 'arn:aws:s3:::bucket2/*'],
                    'Condition': {'StringEquals': {'s3:x-amz-server-side-encryption': 'AES256'}},
                },
                {
                    'Effect': 'Allow',
                    'Action': ['s3:ListBucket'],
                    'Resource': ['arn:aws:s3:::bucket1', 'arn:aws:s3:::bucket2'],
                },
            ],
        }

        response = AddInlinePolicyResponse(
            isError=False,
            content=sample_text_content,
            policy_name='ComplexS3Policy',
            role_name='data-processing-role',
            permissions_added=complex_permissions,
        )

        assert response.policy_name == 'ComplexS3Policy'
        assert response.role_name == 'data-processing-role'
        assert len(response.permissions_added['Statement']) == 2
        assert 'Condition' in response.permissions_added['Statement'][0]


class TestCreateRoleResponse:
    """Test class for CreateRoleResponse model."""

    def test_create_role_response_success(self):
        """Test successful CreateRoleResponse."""
        response = CreateRoleResponse(
            isError=False,
            content=sample_text_content,
            role_name='new-glue-role',
            role_arn='arn:aws:iam::123456789012:role/new-glue-role',
        )

        assert response.isError is False
        assert response.role_name == 'new-glue-role'
        assert response.role_arn == 'arn:aws:iam::123456789012:role/new-glue-role'

    def test_create_role_response_error(self):
        """Test CreateRoleResponse with error."""
        response = CreateRoleResponse(
            isError=True, content=sample_error_content, role_name='failed-role', role_arn=''
        )

        assert response.isError is True
        assert response.content == sample_error_content
        assert response.role_name == 'failed-role'
        assert response.role_arn == ''

    def test_create_role_response_validation(self):
        """Test CreateRoleResponse validation."""
        with pytest.raises(ValidationError) as exc_info:
            CreateRoleResponse(isError=False, content=sample_text_content)

        errors = exc_info.value.errors()
        required_fields = {'role_name', 'role_arn'}
        error_fields = {error['loc'][0] for error in errors}
        assert required_fields.issubset(error_fields)


class TestBucketInfo:
    """Test class for BucketInfo model."""

    def test_bucket_info_creation(self):
        """Test creating BucketInfo."""
        bucket_info = BucketInfo(
            name='my-data-bucket',
            creation_date='2023-01-01T00:00:00Z',
            region='us-east-1',
            object_count='1,234',
            last_modified='2023-12-01T10:30:00Z',
            idle_status='Active',
        )

        assert bucket_info.name == 'my-data-bucket'
        assert bucket_info.creation_date == '2023-01-01T00:00:00Z'
        assert bucket_info.region == 'us-east-1'
        assert bucket_info.object_count == '1,234'
        assert bucket_info.last_modified == '2023-12-01T10:30:00Z'
        assert bucket_info.idle_status == 'Active'

    def test_bucket_info_validation(self):
        """Test BucketInfo validation."""
        with pytest.raises(ValidationError) as exc_info:
            BucketInfo()

        errors = exc_info.value.errors()
        required_fields = {
            'name',
            'creation_date',
            'region',
            'object_count',
            'last_modified',
            'idle_status',
        }
        error_fields = {error['loc'][0] for error in errors}
        assert required_fields.issubset(error_fields)

    def test_bucket_info_with_special_characters(self):
        """Test BucketInfo with special characters and formats."""
        bucket_info = BucketInfo(
            name='my-bucket-with-dashes_and_underscores.dots',
            creation_date='2023-01-01T00:00:00.000Z',
            region='eu-west-1',
            object_count='0',
            last_modified='Never',
            idle_status='Idle (30+ days)',
        )

        assert bucket_info.name == 'my-bucket-with-dashes_and_underscores.dots'
        assert bucket_info.region == 'eu-west-1'
        assert bucket_info.object_count == '0'
        assert bucket_info.idle_status == 'Idle (30+ days)'


class TestListS3BucketsResponse:
    """Test class for ListS3BucketsResponse model."""

    def test_list_s3_buckets_response_with_buckets(self):
        """Test ListS3BucketsResponse with multiple buckets."""
        buckets = [
            BucketInfo(
                name='bucket-1',
                creation_date='2023-01-01T00:00:00Z',
                region='us-east-1',
                object_count='100',
                last_modified='2023-12-01T10:30:00Z',
                idle_status='Active',
            ),
            BucketInfo(
                name='bucket-2',
                creation_date='2023-02-01T00:00:00Z',
                region='us-west-2',
                object_count='0',
                last_modified='Never',
                idle_status='Idle',
            ),
            BucketInfo(
                name='bucket-3',
                creation_date='2023-03-01T00:00:00Z',
                region='eu-west-1',
                object_count='50,000',
                last_modified='2023-12-15T14:20:00Z',
                idle_status='Active',
            ),
        ]

        response = ListS3BucketsResponse(
            isError=False,
            content=sample_text_content,
            region='all',
            bucket_count=3,
            buckets=buckets,
        )

        assert response.isError is False
        assert response.region == 'all'
        assert response.bucket_count == 3
        assert len(response.buckets) == 3
        assert response.buckets[0].name == 'bucket-1'
        assert response.buckets[1].object_count == '0'
        assert response.buckets[2].region == 'eu-west-1'

    def test_list_s3_buckets_response_empty(self):
        """Test ListS3BucketsResponse with no buckets."""
        response = ListS3BucketsResponse(
            isError=False,
            content=sample_text_content,
            region='us-east-1',
            bucket_count=0,
            buckets=[],
        )

        assert response.isError is False
        assert response.region == 'us-east-1'
        assert response.bucket_count == 0
        assert len(response.buckets) == 0

    def test_list_s3_buckets_response_error(self):
        """Test ListS3BucketsResponse with error."""
        response = ListS3BucketsResponse(
            isError=True,
            content=sample_error_content,
            region='us-east-1',
            bucket_count=0,
            buckets=[],
        )

        assert response.isError is True
        assert response.content == sample_error_content
        assert response.region == 'us-east-1'
        assert response.bucket_count == 0

    def test_list_s3_buckets_response_count_mismatch(self):
        """Test ListS3BucketsResponse where count doesn't match actual buckets."""
        buckets = [
            BucketInfo(
                name='bucket-1',
                creation_date='2023-01-01T00:00:00Z',
                region='us-east-1',
                object_count='100',
                last_modified='2023-12-01T10:30:00Z',
                idle_status='Active',
            )
        ]

        # This should be allowed - count might be different for various reasons
        response = ListS3BucketsResponse(
            isError=False,
            content=sample_text_content,
            region='us-east-1',
            bucket_count=5,  # Different from actual bucket list length
            buckets=buckets,
        )

        assert response.bucket_count == 5
        assert len(response.buckets) == 1


class TestUploadToS3Response:
    """Test class for UploadToS3Response model."""

    def test_upload_to_s3_response_success(self):
        """Test successful UploadToS3Response."""
        response = UploadToS3Response(
            isError=False,
            content=sample_text_content,
            s3_uri='s3://my-bucket/path/to/file.txt',
            bucket_name='my-bucket',
            s3_key='path/to/file.txt',
        )

        assert response.isError is False
        assert response.s3_uri == 's3://my-bucket/path/to/file.txt'
        assert response.bucket_name == 'my-bucket'
        assert response.s3_key == 'path/to/file.txt'

    def test_upload_to_s3_response_error(self):
        """Test UploadToS3Response with error."""
        response = UploadToS3Response(
            isError=True,
            content=sample_error_content,
            s3_uri='',
            bucket_name='my-bucket',
            s3_key='path/to/file.txt',
        )

        assert response.isError is True
        assert response.content == sample_error_content
        assert response.s3_uri == ''
        assert response.bucket_name == 'my-bucket'

    def test_upload_to_s3_response_nested_path(self):
        """Test UploadToS3Response with deeply nested path."""
        response = UploadToS3Response(
            isError=False,
            content=sample_text_content,
            s3_uri='s3://data-lake-bucket/year=2023/month=12/day=15/hour=10/data.parquet',
            bucket_name='data-lake-bucket',
            s3_key='year=2023/month=12/day=15/hour=10/data.parquet',
        )

        assert (
            response.s3_uri
            == 's3://data-lake-bucket/year=2023/month=12/day=15/hour=10/data.parquet'
        )
        assert response.bucket_name == 'data-lake-bucket'
        assert response.s3_key == 'year=2023/month=12/day=15/hour=10/data.parquet'

    def test_upload_to_s3_response_validation(self):
        """Test UploadToS3Response validation."""
        with pytest.raises(ValidationError) as exc_info:
            UploadToS3Response(isError=False, content=sample_text_content)

        errors = exc_info.value.errors()
        required_fields = {'s3_uri', 'bucket_name', 's3_key'}
        error_fields = {error['loc'][0] for error in errors}
        assert required_fields.issubset(error_fields)


class TestAnalyzeS3UsageResponse:
    """Test class for AnalyzeS3UsageResponse model."""

    def test_analyze_s3_usage_response_complete(self):
        """Test complete AnalyzeS3UsageResponse."""
        service_usage = {
            'glue': ['s3://data-lake/raw/', 's3://data-lake/processed/'],
            'athena': ['s3://query-results/', 's3://data-lake/processed/'],
            'emr': ['s3://data-lake/raw/', 's3://emr-logs/'],
        }

        response = AnalyzeS3UsageResponse(
            isError=False,
            content=sample_text_content,
            analysis_summary='Analysis of S3 usage across AWS services shows heavy usage by Glue and Athena for data processing workflows.',
            service_usage=service_usage,
        )

        assert response.isError is False
        assert 'Glue and Athena' in response.analysis_summary
        assert len(response.service_usage) == 3
        assert 'glue' in response.service_usage
        assert 'athena' in response.service_usage
        assert 'emr' in response.service_usage
        assert len(response.service_usage['glue']) == 2
        assert 's3://data-lake/processed/' in response.service_usage['athena']

    def test_analyze_s3_usage_response_empty_usage(self):
        """Test AnalyzeS3UsageResponse with empty service usage."""
        response = AnalyzeS3UsageResponse(
            isError=False,
            content=sample_text_content,
            analysis_summary='No significant S3 usage detected across monitored services.',
            service_usage={},
        )

        assert response.isError is False
        assert 'No significant' in response.analysis_summary
        assert len(response.service_usage) == 0

    def test_analyze_s3_usage_response_single_service(self):
        """Test AnalyzeS3UsageResponse with single service."""
        service_usage = {'lambda': ['s3://lambda-deployment-bucket/', 's3://lambda-temp-storage/']}

        response = AnalyzeS3UsageResponse(
            isError=False,
            content=sample_text_content,
            analysis_summary='Primary S3 usage is from Lambda functions for deployment and temporary storage.',
            service_usage=service_usage,
        )

        assert response.isError is False
        assert 'Lambda functions' in response.analysis_summary
        assert len(response.service_usage) == 1
        assert 'lambda' in response.service_usage
        assert len(response.service_usage['lambda']) == 2

    def test_analyze_s3_usage_response_error(self):
        """Test AnalyzeS3UsageResponse with error."""
        response = AnalyzeS3UsageResponse(
            isError=True,
            content=sample_error_content,
            analysis_summary='Failed to analyze S3 usage due to insufficient permissions.',
            service_usage={},
        )

        assert response.isError is True
        assert response.content == sample_error_content
        assert 'Failed to analyze' in response.analysis_summary
        assert len(response.service_usage) == 0

    def test_analyze_s3_usage_response_validation(self):
        """Test AnalyzeS3UsageResponse validation."""
        with pytest.raises(ValidationError) as exc_info:
            AnalyzeS3UsageResponse(isError=False, content=sample_text_content)

        errors = exc_info.value.errors()
        required_fields = {'analysis_summary', 'service_usage'}
        error_fields = {error['loc'][0] for error in errors}
        assert required_fields.issubset(error_fields)


# Additional edge case tests
def test_model_serialization():
    """Test that models can be serialized and deserialized."""
    # Test RoleSummary serialization
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

    role_summary = RoleSummary(
        role_name='test-role',
        role_arn='arn:aws:iam::123456789012:role/test-role',
        description='Test role description',
        create_date='2023-01-01T00:00:00Z',
        assume_role_policy_document=assume_role_policy,
    )

    # Test that it can be converted to dict and back
    role_dict = role_summary.model_dump()
    reconstructed_role = RoleSummary(**role_dict)

    assert reconstructed_role.role_name == role_summary.role_name
    assert reconstructed_role.role_arn == role_summary.role_arn
    assert reconstructed_role.description == role_summary.description
    assert reconstructed_role.create_date == role_summary.create_date
    assert (
        reconstructed_role.assume_role_policy_document == role_summary.assume_role_policy_document
    )


def test_bucket_info_serialization():
    """Test BucketInfo serialization."""
    bucket_info = BucketInfo(
        name='test-bucket',
        creation_date='2023-01-01T00:00:00Z',
        region='us-east-1',
        object_count='100',
        last_modified='2023-12-01T10:30:00Z',
        idle_status='Active',
    )

    # Test serialization
    bucket_dict = bucket_info.model_dump()
    reconstructed_bucket = BucketInfo(**bucket_dict)

    assert reconstructed_bucket.name == bucket_info.name
    assert reconstructed_bucket.creation_date == bucket_info.creation_date
    assert reconstructed_bucket.region == bucket_info.region
    assert reconstructed_bucket.object_count == bucket_info.object_count
    assert reconstructed_bucket.last_modified == bucket_info.last_modified
    assert reconstructed_bucket.idle_status == bucket_info.idle_status


def test_policy_summary_serialization():
    """Test PolicySummary serialization."""
    policy_document = {
        'Version': '2012-10-17',
        'Statement': [
            {'Effect': 'Allow', 'Action': ['s3:GetObject'], 'Resource': 'arn:aws:s3:::my-bucket/*'}
        ],
    }

    policy_summary = PolicySummary(
        policy_type='inline', description='Test policy', policy_document=policy_document
    )

    # Test serialization
    policy_dict = policy_summary.model_dump()
    reconstructed_policy = PolicySummary(**policy_dict)

    assert reconstructed_policy.policy_type == policy_summary.policy_type
    assert reconstructed_policy.description == policy_summary.description
    assert reconstructed_policy.policy_document == policy_summary.policy_document


def test_response_models_with_large_data():
    """Test response models with large amounts of data."""
    # Create a large number of roles
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

    large_roles_list = []
    for i in range(100):
        role = RoleSummary(
            role_name=f'role-{i}',
            role_arn=f'arn:aws:iam::123456789012:role/role-{i}',
            description=f'Role number {i}',
            create_date='2023-01-01T00:00:00Z',
            assume_role_policy_document=assume_role_policy,
        )
        large_roles_list.append(role)

    response = ServiceRolesResponse(
        isError=False, content=sample_text_content, service_type='glue', roles=large_roles_list
    )

    assert len(response.roles) == 100
    assert response.roles[0].role_name == 'role-0'
    assert response.roles[99].role_name == 'role-99'


def test_response_models_with_unicode_data():
    """Test response models with unicode and special characters."""
    # Test with unicode characters
    bucket_info = BucketInfo(
        name='测试-bucket-ñáme',
        creation_date='2023-01-01T00:00:00Z',
        region='us-east-1',
        object_count='1,000',
        last_modified='2023-12-01T10:30:00Z',
        idle_status='Activo (ñ)',
    )

    assert bucket_info.name == '测试-bucket-ñáme'
    assert bucket_info.idle_status == 'Activo (ñ)'

    # Test with special characters in policy
    policy_with_special_chars = {
        'Version': '2012-10-17',
        'Statement': [
            {
                'Effect': 'Allow',
                'Action': ['s3:GetObject'],
                'Resource': 'arn:aws:s3:::my-bucket/path with spaces & special chars/*',
            }
        ],
    }

    policy_summary = PolicySummary(
        policy_type='inline',
        description='Policy with special characters: !@#$%^&*()',
        policy_document=policy_with_special_chars,
    )

    assert (
        policy_summary.description is not None
        and 'special characters' in policy_summary.description
    )
    assert 'path with spaces' in policy_summary.policy_document['Statement'][0]['Resource']


def test_empty_and_null_values():
    """Test models with empty and null values where allowed."""
    # Test PolicySummary with None values
    policy_summary = PolicySummary(policy_type='managed', description=None, policy_document=None)

    assert policy_summary.policy_type == 'managed'
    assert policy_summary.description is None
    assert policy_summary.policy_document is None

    # Test RoleSummary with None description
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

    role_summary = RoleSummary(
        role_name='test-role',
        role_arn='arn:aws:iam::123456789012:role/test-role',
        description=None,
        create_date='2023-01-01T00:00:00Z',
        assume_role_policy_document=assume_role_policy,
    )

    assert role_summary.description is None

    # Test response with empty lists
    response = ServiceRolesResponse(
        isError=False, content=sample_text_content, service_type='lambda', roles=[]
    )

    assert len(response.roles) == 0
    assert response.service_type == 'lambda'


def test_model_field_types():
    """Test that model fields have correct types."""
    # Test that role_name is string
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

    role_summary = RoleSummary(
        role_name='test-role',
        role_arn='arn:aws:iam::123456789012:role/test-role',
        create_date='2023-01-01T00:00:00Z',
        assume_role_policy_document=assume_role_policy,
    )

    assert isinstance(role_summary.role_name, str)
    assert isinstance(role_summary.role_arn, str)
    assert isinstance(role_summary.create_date, str)
    assert isinstance(role_summary.assume_role_policy_document, dict)

    # Test BucketInfo field types
    bucket_info = BucketInfo(
        name='test-bucket',
        creation_date='2023-01-01T00:00:00Z',
        region='us-east-1',
        object_count='100',
        last_modified='2023-12-01T10:30:00Z',
        idle_status='Active',
    )

    assert isinstance(bucket_info.name, str)
    assert isinstance(bucket_info.creation_date, str)
    assert isinstance(bucket_info.region, str)
    assert isinstance(bucket_info.object_count, str)
    assert isinstance(bucket_info.last_modified, str)
    assert isinstance(bucket_info.idle_status, str)


def test_complex_nested_structures():
    """Test models with complex nested data structures."""
    # Test with deeply nested policy document
    complex_policy = {
        'Version': '2012-10-17',
        'Statement': [
            {
                'Effect': 'Allow',
                'Action': ['s3:GetObject', 's3:PutObject', 's3:DeleteObject'],
                'Resource': ['arn:aws:s3:::bucket1/*', 'arn:aws:s3:::bucket2/*'],
                'Condition': {
                    'StringEquals': {'s3:x-amz-server-side-encryption': 'AES256'},
                    'IpAddress': {'aws:SourceIp': ['192.168.1.0/24', '10.0.0.0/8']},
                    'DateGreaterThan': {'aws:CurrentTime': '2023-01-01T00:00:00Z'},
                },
            },
            {
                'Effect': 'Deny',
                'Action': '*',
                'Resource': '*',
                'Condition': {'Bool': {'aws:SecureTransport': 'false'}},
            },
        ],
    }

    policy_summary = PolicySummary(
        policy_type='inline',
        description='Complex policy with multiple conditions',
        policy_document=complex_policy,
    )

    assert len(policy_summary.policy_document['Statement']) == 2
    assert 'Condition' in policy_summary.policy_document['Statement'][0]
    assert 'IpAddress' in policy_summary.policy_document['Statement'][0]['Condition']
    assert (
        len(
            policy_summary.policy_document['Statement'][0]['Condition']['IpAddress'][
                'aws:SourceIp'
            ]
        )
        == 2
    )

    # Test with complex service usage data
    complex_service_usage = {
        'glue': [
            's3://data-lake/raw/year=2023/month=01/',
            's3://data-lake/raw/year=2023/month=02/',
            's3://data-lake/processed/year=2023/month=01/',
            's3://data-lake/processed/year=2023/month=02/',
        ],
        'athena': [
            's3://query-results/year=2023/month=01/',
            's3://query-results/year=2023/month=02/',
            's3://data-lake/processed/',
        ],
        'emr': ['s3://emr-logs/cluster-1/', 's3://emr-logs/cluster-2/', 's3://data-lake/raw/'],
        'lambda': ['s3://lambda-deployment/', 's3://lambda-temp/'],
    }

    response = AnalyzeS3UsageResponse(
        isError=False,
        content=sample_text_content,
        analysis_summary='Complex analysis of S3 usage across multiple services with partitioned data structures.',
        service_usage=complex_service_usage,
    )

    assert len(response.service_usage) == 4
    assert len(response.service_usage['glue']) == 4
    assert len(response.service_usage['athena']) == 3
    assert len(response.service_usage['emr']) == 3
    assert len(response.service_usage['lambda']) == 2
    assert 'year=2023/month=01' in response.service_usage['glue'][0]
