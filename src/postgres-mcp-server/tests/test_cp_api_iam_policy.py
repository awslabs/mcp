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
"""Additional tests for IAM policy setup in cp_api_connection.py."""

import pytest
from botocore.exceptions import ClientError
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_boto3_clients():
    """Mock boto3 clients for STS and IAM."""
    with patch('boto3.client') as mock_client:
        mock_sts = MagicMock()
        mock_iam = MagicMock()

        # Mock IAM exceptions
        class MockIAMExceptions:
            NoSuchEntityException = type('NoSuchEntityException', (ClientError,), {})
            EntityAlreadyExistsException = type('EntityAlreadyExistsException', (ClientError,), {})
            LimitExceededException = type('LimitExceededException', (ClientError,), {})
            AccessDeniedException = type('AccessDeniedException', (ClientError,), {})

        mock_iam.exceptions = MockIAMExceptions()

        def client_factory(service_name, **kwargs):
            if service_name == 'sts':
                return mock_sts
            elif service_name == 'iam':
                return mock_iam
            return MagicMock()

        mock_client.side_effect = client_factory
        yield mock_sts, mock_iam


class TestSetupAuroraIamPolicyAdditional:
    """Additional tests for setup_aurora_iam_policy_for_current_user."""

    def test_policy_already_attached_to_user(self, mock_boto3_clients):
        """Test when policy is already attached to user."""
        from awslabs.postgres_mcp_server.connection.cp_api_connection import (
            setup_aurora_iam_policy_for_current_user,
        )

        mock_sts, mock_iam = mock_boto3_clients

        # Mock IAM user identity
        mock_sts.get_caller_identity.return_value = {
            'Account': '123456789012',
            'Arn': 'arn:aws:iam::123456789012:user/testuser',
            'UserId': 'AIDAI123456789EXAMPLE',
        }

        policy_arn = 'arn:aws:iam::123456789012:policy/AuroraIAMAuth-dbuser'

        # Mock existing policy
        mock_iam.get_policy.return_value = {
            'Policy': {'Arn': policy_arn, 'DefaultVersionId': 'v1'}
        }

        # Mock policy document with resource already present
        mock_iam.get_policy_version.return_value = {
            'PolicyVersion': {
                'Document': {
                    'Version': '2012-10-17',
                    'Statement': [
                        {
                            'Effect': 'Allow',
                            'Action': 'rds-db:connect',
                            'Resource': [
                                'arn:aws:rds-db:us-east-1:123456789012:dbuser:cluster-ABC123/dbuser'
                            ],
                        }
                    ],
                }
            }
        }

        # Mock policy already attached
        mock_iam.list_attached_user_policies.return_value = {
            'AttachedPolicies': [{'PolicyName': 'AuroraIAMAuth-dbuser', 'PolicyArn': policy_arn}]
        }

        result = setup_aurora_iam_policy_for_current_user(
            db_user='dbuser', cluster_resource_id='cluster-ABC123', cluster_region='us-east-1'
        )

        assert result == policy_arn
        # Verify attach was not called since already attached
        mock_iam.attach_user_policy.assert_not_called()

    def test_policy_already_attached_to_role(self, mock_boto3_clients):
        """Test when policy is already attached to role."""
        from awslabs.postgres_mcp_server.connection.cp_api_connection import (
            setup_aurora_iam_policy_for_current_user,
        )

        mock_sts, mock_iam = mock_boto3_clients

        # Mock assumed role identity
        mock_sts.get_caller_identity.return_value = {
            'Account': '123456789012',
            'Arn': 'arn:aws:sts::123456789012:assumed-role/MyRole/session-name',
            'UserId': 'AROAI123456789EXAMPLE:session-name',
        }

        policy_arn = 'arn:aws:iam::123456789012:policy/AuroraIAMAuth-dbuser'

        # Mock existing policy
        mock_iam.get_policy.return_value = {
            'Policy': {'Arn': policy_arn, 'DefaultVersionId': 'v1'}
        }

        # Mock policy document
        mock_iam.get_policy_version.return_value = {
            'PolicyVersion': {
                'Document': {
                    'Version': '2012-10-17',
                    'Statement': [
                        {
                            'Effect': 'Allow',
                            'Action': 'rds-db:connect',
                            'Resource': [
                                'arn:aws:rds-db:us-east-1:123456789012:dbuser:cluster-ABC123/dbuser'
                            ],
                        }
                    ],
                }
            }
        }

        # Mock policy already attached to role
        mock_iam.list_attached_role_policies.return_value = {
            'AttachedPolicies': [{'PolicyName': 'AuroraIAMAuth-dbuser', 'PolicyArn': policy_arn}]
        }

        result = setup_aurora_iam_policy_for_current_user(
            db_user='dbuser', cluster_resource_id='cluster-ABC123', cluster_region='us-east-1'
        )

        assert result == policy_arn
        mock_iam.attach_role_policy.assert_not_called()

    def test_policy_update_with_version_limit(self, mock_boto3_clients):
        """Test policy update when version limit is reached."""
        from awslabs.postgres_mcp_server.connection.cp_api_connection import (
            setup_aurora_iam_policy_for_current_user,
        )

        mock_sts, mock_iam = mock_boto3_clients

        # Mock IAM user identity
        mock_sts.get_caller_identity.return_value = {
            'Account': '123456789012',
            'Arn': 'arn:aws:iam::123456789012:user/testuser',
            'UserId': 'AIDAI123456789EXAMPLE',
        }

        policy_arn = 'arn:aws:iam::123456789012:policy/AuroraIAMAuth-dbuser'

        # Mock existing policy
        mock_iam.get_policy.return_value = {
            'Policy': {'Arn': policy_arn, 'DefaultVersionId': 'v5'}
        }

        # Mock policy document with different resource
        mock_iam.get_policy_version.return_value = {
            'PolicyVersion': {
                'Document': {
                    'Version': '2012-10-17',
                    'Statement': [
                        {
                            'Effect': 'Allow',
                            'Action': 'rds-db:connect',
                            'Resource': [
                                'arn:aws:rds-db:us-east-1:123456789012:dbuser:cluster-OLD/dbuser'
                            ],
                        }
                    ],
                }
            }
        }

        # Mock 5 versions (at limit)
        from datetime import datetime

        mock_iam.list_policy_versions.return_value = {
            'Versions': [
                {'VersionId': 'v5', 'IsDefaultVersion': True, 'CreateDate': datetime(2024, 1, 5)},
                {'VersionId': 'v4', 'IsDefaultVersion': False, 'CreateDate': datetime(2024, 1, 4)},
                {'VersionId': 'v3', 'IsDefaultVersion': False, 'CreateDate': datetime(2024, 1, 3)},
                {'VersionId': 'v2', 'IsDefaultVersion': False, 'CreateDate': datetime(2024, 1, 2)},
                {'VersionId': 'v1', 'IsDefaultVersion': False, 'CreateDate': datetime(2024, 1, 1)},
            ]
        }

        mock_iam.delete_policy_version.return_value = {}
        mock_iam.create_policy_version.return_value = {'PolicyVersion': {'VersionId': 'v6'}}

        mock_iam.list_attached_user_policies.return_value = {'AttachedPolicies': []}
        mock_iam.attach_user_policy.return_value = {}

        result = setup_aurora_iam_policy_for_current_user(
            db_user='dbuser', cluster_resource_id='cluster-NEW', cluster_region='us-east-1'
        )

        # Verify oldest version was deleted
        mock_iam.delete_policy_version.assert_called_once_with(
            PolicyArn=policy_arn, VersionId='v1'
        )

        # Verify new version was created
        mock_iam.create_policy_version.assert_called_once()
        assert result == policy_arn

    def test_policy_creation_race_condition(self, mock_boto3_clients):
        """Test handling of race condition during policy creation."""
        from awslabs.postgres_mcp_server.connection.cp_api_connection import (
            setup_aurora_iam_policy_for_current_user,
        )

        mock_sts, mock_iam = mock_boto3_clients

        # Mock IAM user identity
        mock_sts.get_caller_identity.return_value = {
            'Account': '123456789012',
            'Arn': 'arn:aws:iam::123456789012:user/testuser',
            'UserId': 'AIDAI123456789EXAMPLE',
        }

        # Mock policy doesn't exist initially
        mock_iam.get_policy.side_effect = mock_iam.exceptions.NoSuchEntityException(
            {'Error': {'Code': 'NoSuchEntity'}}, 'GetPolicy'
        )

        # Mock policy creation fails due to race condition
        mock_iam.create_policy.side_effect = mock_iam.exceptions.EntityAlreadyExistsException(
            {'Error': {'Code': 'EntityAlreadyExists'}}, 'CreatePolicy'
        )

        mock_iam.list_attached_user_policies.return_value = {'AttachedPolicies': []}
        mock_iam.attach_user_policy.return_value = {}

        result = setup_aurora_iam_policy_for_current_user(
            db_user='dbuser', cluster_resource_id='cluster-ABC123', cluster_region='us-east-1'
        )

        # Should still return policy ARN
        assert result == 'arn:aws:iam::123456789012:policy/AuroraIAMAuth-dbuser'

    def test_attach_policy_to_role_access_denied(self, mock_boto3_clients):
        """Test graceful handling when attaching policy to role is denied."""
        from awslabs.postgres_mcp_server.connection.cp_api_connection import (
            setup_aurora_iam_policy_for_current_user,
        )

        mock_sts, mock_iam = mock_boto3_clients

        # Mock assumed role identity
        mock_sts.get_caller_identity.return_value = {
            'Account': '123456789012',
            'Arn': 'arn:aws:sts::123456789012:assumed-role/MyRole/session-name',
            'UserId': 'AROAI123456789EXAMPLE:session-name',
        }

        policy_arn = 'arn:aws:iam::123456789012:policy/AuroraIAMAuth-dbuser'

        # Mock policy doesn't exist
        mock_iam.get_policy.side_effect = mock_iam.exceptions.NoSuchEntityException(
            {'Error': {'Code': 'NoSuchEntity'}}, 'GetPolicy'
        )

        # Mock policy creation succeeds
        mock_iam.create_policy.return_value = {'Policy': {'Arn': policy_arn}}

        # Mock attach fails with AccessDenied
        mock_iam.list_attached_role_policies.return_value = {'AttachedPolicies': []}
        mock_iam.attach_role_policy.side_effect = mock_iam.exceptions.AccessDeniedException(
            {'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}}, 'AttachRolePolicy'
        )

        # Should return policy ARN even though attach failed
        result = setup_aurora_iam_policy_for_current_user(
            db_user='dbuser', cluster_resource_id='cluster-ABC123', cluster_region='us-east-1'
        )

        assert result == policy_arn

    def test_attach_policy_role_not_found(self, mock_boto3_clients):
        """Test handling when role is not found during attach."""
        from awslabs.postgres_mcp_server.connection.cp_api_connection import (
            setup_aurora_iam_policy_for_current_user,
        )

        mock_sts, mock_iam = mock_boto3_clients

        # Mock assumed role identity
        mock_sts.get_caller_identity.return_value = {
            'Account': '123456789012',
            'Arn': 'arn:aws:sts::123456789012:assumed-role/MyRole/session-name',
            'UserId': 'AROAI123456789EXAMPLE:session-name',
        }

        policy_arn = 'arn:aws:iam::123456789012:policy/AuroraIAMAuth-dbuser'

        # Mock existing policy
        mock_iam.get_policy.return_value = {
            'Policy': {'Arn': policy_arn, 'DefaultVersionId': 'v1'}
        }

        mock_iam.get_policy_version.return_value = {
            'PolicyVersion': {
                'Document': {
                    'Version': '2012-10-17',
                    'Statement': [
                        {
                            'Effect': 'Allow',
                            'Action': 'rds-db:connect',
                            'Resource': [
                                'arn:aws:rds-db:us-east-1:123456789012:dbuser:cluster-ABC123/dbuser'
                            ],
                        }
                    ],
                }
            }
        }

        # Mock role not found
        mock_iam.list_attached_role_policies.side_effect = (
            mock_iam.exceptions.NoSuchEntityException(
                {'Error': {'Code': 'NoSuchEntity'}}, 'ListAttachedRolePolicies'
            )
        )

        with pytest.raises(mock_iam.exceptions.NoSuchEntityException):
            setup_aurora_iam_policy_for_current_user(
                db_user='dbuser', cluster_resource_id='cluster-ABC123', cluster_region='us-east-1'
            )

    def test_attach_policy_limit_exceeded(self, mock_boto3_clients):
        """Test handling when policy limit is exceeded."""
        from awslabs.postgres_mcp_server.connection.cp_api_connection import (
            setup_aurora_iam_policy_for_current_user,
        )

        mock_sts, mock_iam = mock_boto3_clients

        # Mock IAM user identity
        mock_sts.get_caller_identity.return_value = {
            'Account': '123456789012',
            'Arn': 'arn:aws:iam::123456789012:user/testuser',
            'UserId': 'AIDAI123456789EXAMPLE',
        }

        policy_arn = 'arn:aws:iam::123456789012:policy/AuroraIAMAuth-dbuser'

        # Mock existing policy
        mock_iam.get_policy.return_value = {
            'Policy': {'Arn': policy_arn, 'DefaultVersionId': 'v1'}
        }

        mock_iam.get_policy_version.return_value = {
            'PolicyVersion': {
                'Document': {
                    'Version': '2012-10-17',
                    'Statement': [
                        {
                            'Effect': 'Allow',
                            'Action': 'rds-db:connect',
                            'Resource': [
                                'arn:aws:rds-db:us-east-1:123456789012:dbuser:cluster-ABC123/dbuser'
                            ],
                        }
                    ],
                }
            }
        }

        # Mock limit exceeded
        mock_iam.list_attached_user_policies.return_value = {'AttachedPolicies': []}
        mock_iam.attach_user_policy.side_effect = mock_iam.exceptions.LimitExceededException(
            {'Error': {'Code': 'LimitExceeded', 'Message': 'Limit exceeded'}}, 'AttachUserPolicy'
        )

        with pytest.raises(mock_iam.exceptions.LimitExceededException):
            setup_aurora_iam_policy_for_current_user(
                db_user='dbuser', cluster_resource_id='cluster-ABC123', cluster_region='us-east-1'
            )

    def test_unexpected_arn_format(self, mock_boto3_clients):
        """Test handling of unexpected ARN format."""
        from awslabs.postgres_mcp_server.connection.cp_api_connection import (
            setup_aurora_iam_policy_for_current_user,
        )

        mock_sts, mock_iam = mock_boto3_clients

        # Mock unexpected ARN format
        mock_sts.get_caller_identity.return_value = {
            'Account': '123456789012',
            'Arn': 'arn:aws:iam::123456789012:unknown/something',
            'UserId': 'UNKNOWN123',
        }

        with pytest.raises(ValueError, match='Unexpected ARN format'):
            setup_aurora_iam_policy_for_current_user(
                db_user='dbuser', cluster_resource_id='cluster-ABC123', cluster_region='us-east-1'
            )

    def test_sts_get_caller_identity_error(self, mock_boto3_clients):
        """Test handling of STS error."""
        from awslabs.postgres_mcp_server.connection.cp_api_connection import (
            setup_aurora_iam_policy_for_current_user,
        )

        mock_sts, mock_iam = mock_boto3_clients

        # Mock STS error
        mock_sts.get_caller_identity.side_effect = ClientError(
            {'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}}, 'GetCallerIdentity'
        )

        with pytest.raises(ClientError):
            setup_aurora_iam_policy_for_current_user(
                db_user='dbuser', cluster_resource_id='cluster-ABC123', cluster_region='us-east-1'
            )

    def test_policy_update_with_string_resource(self, mock_boto3_clients):
        """Test policy update when existing resource is a string (not list)."""
        from awslabs.postgres_mcp_server.connection.cp_api_connection import (
            setup_aurora_iam_policy_for_current_user,
        )

        mock_sts, mock_iam = mock_boto3_clients

        # Mock IAM user identity
        mock_sts.get_caller_identity.return_value = {
            'Account': '123456789012',
            'Arn': 'arn:aws:iam::123456789012:user/testuser',
            'UserId': 'AIDAI123456789EXAMPLE',
        }

        policy_arn = 'arn:aws:iam::123456789012:policy/AuroraIAMAuth-dbuser'

        # Mock existing policy
        mock_iam.get_policy.return_value = {
            'Policy': {'Arn': policy_arn, 'DefaultVersionId': 'v1'}
        }

        # Mock policy document with string resource (not list)
        mock_iam.get_policy_version.return_value = {
            'PolicyVersion': {
                'Document': {
                    'Version': '2012-10-17',
                    'Statement': [
                        {
                            'Effect': 'Allow',
                            'Action': 'rds-db:connect',
                            'Resource': 'arn:aws:rds-db:us-east-1:123456789012:dbuser:cluster-OLD/dbuser',
                        }
                    ],
                }
            }
        }

        mock_iam.list_policy_versions.return_value = {
            'Versions': [{'VersionId': 'v1', 'IsDefaultVersion': True}]
        }

        mock_iam.create_policy_version.return_value = {'PolicyVersion': {'VersionId': 'v2'}}

        mock_iam.list_attached_user_policies.return_value = {'AttachedPolicies': []}
        mock_iam.attach_user_policy.return_value = {}

        result = setup_aurora_iam_policy_for_current_user(
            db_user='dbuser', cluster_resource_id='cluster-NEW', cluster_region='us-east-1'
        )

        # Verify new version was created with both resources
        mock_iam.create_policy_version.assert_called_once()
        assert result == policy_arn

    def test_generic_exception_during_policy_creation(self, mock_boto3_clients):
        """Test handling of generic exception during policy creation."""
        from awslabs.postgres_mcp_server.connection.cp_api_connection import (
            setup_aurora_iam_policy_for_current_user,
        )

        mock_sts, mock_iam = mock_boto3_clients

        # Mock IAM user identity
        mock_sts.get_caller_identity.return_value = {
            'Account': '123456789012',
            'Arn': 'arn:aws:iam::123456789012:user/testuser',
            'UserId': 'AIDAI123456789EXAMPLE',
        }

        # Mock policy doesn't exist
        mock_iam.get_policy.side_effect = mock_iam.exceptions.NoSuchEntityException(
            {'Error': {'Code': 'NoSuchEntity'}}, 'GetPolicy'
        )

        # Mock generic exception during policy creation
        mock_iam.create_policy.side_effect = Exception('Unexpected error during policy creation')

        with pytest.raises(Exception, match='Unexpected error during policy creation'):
            setup_aurora_iam_policy_for_current_user(
                db_user='dbuser', cluster_resource_id='cluster-ABC123', cluster_region='us-east-1'
            )

    def test_generic_exception_during_policy_update(self, mock_boto3_clients):
        """Test handling of generic exception during policy update."""
        from awslabs.postgres_mcp_server.connection.cp_api_connection import (
            setup_aurora_iam_policy_for_current_user,
        )

        mock_sts, mock_iam = mock_boto3_clients

        # Mock IAM user identity
        mock_sts.get_caller_identity.return_value = {
            'Account': '123456789012',
            'Arn': 'arn:aws:iam::123456789012:user/testuser',
            'UserId': 'AIDAI123456789EXAMPLE',
        }

        # Mock existing policy but get_policy_version fails
        mock_iam.get_policy.return_value = {
            'Policy': {
                'Arn': 'arn:aws:iam::123456789012:policy/AuroraIAMAuth-dbuser',
                'DefaultVersionId': 'v1',
            }
        }

        mock_iam.get_policy_version.side_effect = Exception(
            'Unexpected error fetching policy version'
        )

        with pytest.raises(Exception, match='Unexpected error fetching policy version'):
            setup_aurora_iam_policy_for_current_user(
                db_user='dbuser', cluster_resource_id='cluster-ABC123', cluster_region='us-east-1'
            )

    def test_generic_exception_during_policy_attachment(self, mock_boto3_clients):
        """Test handling of generic exception during policy attachment."""
        from awslabs.postgres_mcp_server.connection.cp_api_connection import (
            setup_aurora_iam_policy_for_current_user,
        )

        mock_sts, mock_iam = mock_boto3_clients

        # Mock IAM user identity
        mock_sts.get_caller_identity.return_value = {
            'Account': '123456789012',
            'Arn': 'arn:aws:iam::123456789012:user/testuser',
            'UserId': 'AIDAI123456789EXAMPLE',
        }

        policy_arn = 'arn:aws:iam::123456789012:policy/AuroraIAMAuth-dbuser'

        # Mock existing policy
        mock_iam.get_policy.return_value = {
            'Policy': {'Arn': policy_arn, 'DefaultVersionId': 'v1'}
        }

        mock_iam.get_policy_version.return_value = {
            'PolicyVersion': {
                'Document': {
                    'Version': '2012-10-17',
                    'Statement': [
                        {
                            'Effect': 'Allow',
                            'Action': 'rds-db:connect',
                            'Resource': [
                                'arn:aws:rds-db:us-east-1:123456789012:dbuser:cluster-ABC123/dbuser'
                            ],
                        }
                    ],
                }
            }
        }

        # Mock generic exception during attachment
        mock_iam.list_attached_user_policies.side_effect = Exception('Unexpected IAM error')

        with pytest.raises(Exception, match='Unexpected IAM error'):
            setup_aurora_iam_policy_for_current_user(
                db_user='dbuser', cluster_resource_id='cluster-ABC123', cluster_region='us-east-1'
            )

    def test_policy_update_no_non_default_versions(self, mock_boto3_clients):
        """Test policy update when at version limit but no non-default versions to delete."""
        from awslabs.postgres_mcp_server.connection.cp_api_connection import (
            setup_aurora_iam_policy_for_current_user,
        )

        mock_sts, mock_iam = mock_boto3_clients

        # Mock IAM user identity
        mock_sts.get_caller_identity.return_value = {
            'Account': '123456789012',
            'Arn': 'arn:aws:iam::123456789012:user/testuser',
            'UserId': 'AIDAI123456789EXAMPLE',
        }

        policy_arn = 'arn:aws:iam::123456789012:policy/AuroraIAMAuth-dbuser'

        # Mock existing policy
        mock_iam.get_policy.return_value = {
            'Policy': {'Arn': policy_arn, 'DefaultVersionId': 'v5'}
        }

        # Mock policy document with different resource
        mock_iam.get_policy_version.return_value = {
            'PolicyVersion': {
                'Document': {
                    'Version': '2012-10-17',
                    'Statement': [
                        {
                            'Effect': 'Allow',
                            'Action': 'rds-db:connect',
                            'Resource': [
                                'arn:aws:rds-db:us-east-1:123456789012:dbuser:cluster-OLD/dbuser'
                            ],
                        }
                    ],
                }
            }
        }

        # Mock 5 versions but all are default (edge case)
        from datetime import datetime

        mock_iam.list_policy_versions.return_value = {
            'Versions': [
                {'VersionId': 'v5', 'IsDefaultVersion': True, 'CreateDate': datetime(2024, 1, 5)},
                {'VersionId': 'v4', 'IsDefaultVersion': True, 'CreateDate': datetime(2024, 1, 4)},
                {'VersionId': 'v3', 'IsDefaultVersion': True, 'CreateDate': datetime(2024, 1, 3)},
                {'VersionId': 'v2', 'IsDefaultVersion': True, 'CreateDate': datetime(2024, 1, 2)},
                {'VersionId': 'v1', 'IsDefaultVersion': True, 'CreateDate': datetime(2024, 1, 1)},
            ]
        }

        mock_iam.create_policy_version.return_value = {'PolicyVersion': {'VersionId': 'v6'}}

        mock_iam.list_attached_user_policies.return_value = {'AttachedPolicies': []}
        mock_iam.attach_user_policy.return_value = {}

        result = setup_aurora_iam_policy_for_current_user(
            db_user='dbuser', cluster_resource_id='cluster-NEW', cluster_region='us-east-1'
        )

        # Verify no version was deleted (no non-default versions)
        mock_iam.delete_policy_version.assert_not_called()

        # Verify new version was still created
        mock_iam.create_policy_version.assert_called_once()
        assert result == policy_arn

    def test_attach_policy_to_role_not_already_attached(self, mock_boto3_clients):
        """Test attaching policy to role when not already attached."""
        from awslabs.postgres_mcp_server.connection.cp_api_connection import (
            setup_aurora_iam_policy_for_current_user,
        )

        mock_sts, mock_iam = mock_boto3_clients

        # Mock assumed role identity
        mock_sts.get_caller_identity.return_value = {
            'Account': '123456789012',
            'Arn': 'arn:aws:sts::123456789012:assumed-role/MyRole/session-name',
            'UserId': 'AROAI123456789EXAMPLE:session-name',
        }

        policy_arn = 'arn:aws:iam::123456789012:policy/AuroraIAMAuth-dbuser'

        # Mock existing policy
        mock_iam.get_policy.return_value = {
            'Policy': {'Arn': policy_arn, 'DefaultVersionId': 'v1'}
        }

        mock_iam.get_policy_version.return_value = {
            'PolicyVersion': {
                'Document': {
                    'Version': '2012-10-17',
                    'Statement': [
                        {
                            'Effect': 'Allow',
                            'Action': 'rds-db:connect',
                            'Resource': [
                                'arn:aws:rds-db:us-east-1:123456789012:dbuser:cluster-ABC123/dbuser'
                            ],
                        }
                    ],
                }
            }
        }

        # Mock policy NOT already attached to role
        mock_iam.list_attached_role_policies.return_value = {'AttachedPolicies': []}
        mock_iam.attach_role_policy.return_value = {}

        result = setup_aurora_iam_policy_for_current_user(
            db_user='dbuser', cluster_resource_id='cluster-ABC123', cluster_region='us-east-1'
        )

        # Verify attach was called
        mock_iam.attach_role_policy.assert_called_once_with(
            RoleName='MyRole', PolicyArn=policy_arn
        )
        assert result == policy_arn
