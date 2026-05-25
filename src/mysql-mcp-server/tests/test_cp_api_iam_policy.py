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

"""Tests for setup_aurora_iam_policy_for_current_user with mocked STS + IAM."""

import pytest
from awslabs.mysql_mcp_server.connection.cp_api_connection import (
    setup_aurora_iam_policy_for_current_user,
)
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_sts():
    """Create a mock STS client."""
    sts = MagicMock()
    sts.get_caller_identity.return_value = {
        'Account': '123456789012',
        'Arn': 'arn:aws:iam::123456789012:user/testuser',
        'UserId': 'AIDAEXAMPLE',
    }
    return sts


@pytest.fixture
def mock_iam():
    """Create a mock IAM client."""
    iam = MagicMock()
    iam.exceptions = MagicMock()

    # Create real exception classes for testing
    class NoSuchEntityException(Exception):
        pass

    class EntityAlreadyExistsException(Exception):
        pass

    class LimitExceededException(Exception):
        pass

    class AccessDeniedException(Exception):
        pass

    iam.exceptions.NoSuchEntityException = NoSuchEntityException
    iam.exceptions.EntityAlreadyExistsException = EntityAlreadyExistsException
    iam.exceptions.LimitExceededException = LimitExceededException
    iam.exceptions.AccessDeniedException = AccessDeniedException

    return iam


class TestSetupAuroraIAMPolicyValidation:
    """Tests for input validation."""

    def test_empty_db_user_raises(self):
        """Should raise ValueError for empty db_user."""
        with pytest.raises(ValueError, match='db_user must be a non-empty string'):
            setup_aurora_iam_policy_for_current_user('', 'cluster-123', 'us-east-1')

    def test_none_db_user_raises(self):
        """Should raise ValueError for None db_user."""
        with pytest.raises(ValueError, match='db_user must be a non-empty string'):
            setup_aurora_iam_policy_for_current_user(None, 'cluster-123', 'us-east-1')  # pyright: ignore[reportArgumentType]

    def test_empty_cluster_resource_id_raises(self):
        """Should raise ValueError for empty cluster_resource_id."""
        with pytest.raises(ValueError, match='cluster_resource_id must be a non-empty string'):
            setup_aurora_iam_policy_for_current_user('admin', '', 'us-east-1')

    def test_empty_cluster_region_raises(self):
        """Should raise ValueError for empty cluster_region."""
        with pytest.raises(ValueError, match='cluster_region must be a non-empty string'):
            setup_aurora_iam_policy_for_current_user('admin', 'cluster-123', '')

    def test_non_string_db_user_raises(self):
        """Should raise ValueError for non-string db_user."""
        with pytest.raises(ValueError, match='db_user must be a non-empty string'):
            setup_aurora_iam_policy_for_current_user(123, 'cluster-123', 'us-east-1')  # pyright: ignore[reportArgumentType]


class TestSetupAuroraIAMPolicyIAMUser:
    """Tests for IAM user identity type."""

    @patch('awslabs.mysql_mcp_server.connection.cp_api_connection.boto3.client')
    def test_creates_new_policy_for_iam_user(self, mock_boto_client, mock_sts, mock_iam):
        """Should create a new policy and attach to IAM user."""
        mock_iam.get_policy.side_effect = mock_iam.exceptions.NoSuchEntityException()
        mock_iam.create_policy.return_value = {
            'Policy': {'Arn': 'arn:aws:iam::123456789012:policy/AuroraIAMAuth-admin'}
        }
        mock_iam.list_attached_user_policies.return_value = {'AttachedPolicies': []}

        def client_factory(service, **kwargs):
            if service == 'sts':
                return mock_sts
            elif service == 'iam':
                return mock_iam
            return MagicMock()

        mock_boto_client.side_effect = client_factory

        result = setup_aurora_iam_policy_for_current_user('admin', 'cluster-ABCD123', 'us-east-1')

        mock_iam.create_policy.assert_called_once()
        mock_iam.attach_user_policy.assert_called_once()
        assert result is not None

    @patch('awslabs.mysql_mcp_server.connection.cp_api_connection.boto3.client')
    def test_updates_existing_policy_for_iam_user(self, mock_boto_client, mock_sts, mock_iam):
        """Should update existing policy with new cluster resource."""
        mock_iam.get_policy.return_value = {
            'Policy': {
                'Arn': 'arn:aws:iam::123456789012:policy/AuroraIAMAuth-admin',
                'DefaultVersionId': 'v1',
            }
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
                                'arn:aws:rds-db:us-east-1:123456789012:dbuser:cluster-OLD/admin'
                            ],
                        }
                    ],
                }
            }
        }
        mock_iam.list_policy_versions.return_value = {
            'Versions': [{'VersionId': 'v1', 'IsDefaultVersion': True, 'CreateDate': '2024-01-01'}]
        }
        mock_iam.create_policy_version.return_value = {'PolicyVersion': {'VersionId': 'v2'}}
        mock_iam.list_attached_user_policies.return_value = {
            'AttachedPolicies': [
                {
                    'PolicyArn': 'arn:aws:iam::123456789012:policy/AuroraIAMAuth-admin',
                    'PolicyName': 'AuroraIAMAuth-admin',
                }
            ]
        }

        def client_factory(service, **kwargs):
            if service == 'sts':
                return mock_sts
            elif service == 'iam':
                return mock_iam
            return MagicMock()

        mock_boto_client.side_effect = client_factory

        result = setup_aurora_iam_policy_for_current_user('admin', 'cluster-NEW123', 'us-east-1')

        mock_iam.create_policy_version.assert_called_once()
        assert result is not None

    @patch('awslabs.mysql_mcp_server.connection.cp_api_connection.boto3.client')
    def test_skips_update_if_cluster_already_in_policy(self, mock_boto_client, mock_sts, mock_iam):
        """Should not update policy if cluster is already included."""
        resource_arn = 'arn:aws:rds-db:us-east-1:123456789012:dbuser:cluster-ABCD123/admin'
        mock_iam.get_policy.return_value = {
            'Policy': {
                'Arn': 'arn:aws:iam::123456789012:policy/AuroraIAMAuth-admin',
                'DefaultVersionId': 'v1',
            }
        }
        mock_iam.get_policy_version.return_value = {
            'PolicyVersion': {
                'Document': {
                    'Version': '2012-10-17',
                    'Statement': [
                        {
                            'Effect': 'Allow',
                            'Action': 'rds-db:connect',
                            'Resource': [resource_arn],
                        }
                    ],
                }
            }
        }
        mock_iam.list_attached_user_policies.return_value = {
            'AttachedPolicies': [
                {
                    'PolicyArn': 'arn:aws:iam::123456789012:policy/AuroraIAMAuth-admin',
                    'PolicyName': 'AuroraIAMAuth-admin',
                }
            ]
        }

        def client_factory(service, **kwargs):
            if service == 'sts':
                return mock_sts
            elif service == 'iam':
                return mock_iam
            return MagicMock()

        mock_boto_client.side_effect = client_factory

        result = setup_aurora_iam_policy_for_current_user('admin', 'cluster-ABCD123', 'us-east-1')

        mock_iam.create_policy_version.assert_not_called()
        assert result is not None


class TestSetupAuroraIAMPolicyAssumedRole:
    """Tests for assumed role identity type."""

    @patch('awslabs.mysql_mcp_server.connection.cp_api_connection.boto3.client')
    def test_attaches_policy_to_role(self, mock_boto_client, mock_iam):
        """Should attach policy to the base role for assumed role sessions."""
        mock_sts = MagicMock()
        mock_sts.get_caller_identity.return_value = {
            'Account': '123456789012',
            'Arn': 'arn:aws:sts::123456789012:assumed-role/MyRole/session-name',
            'UserId': 'AROAEXAMPLE:session-name',
        }

        mock_iam.get_policy.side_effect = mock_iam.exceptions.NoSuchEntityException()
        mock_iam.create_policy.return_value = {
            'Policy': {'Arn': 'arn:aws:iam::123456789012:policy/AuroraIAMAuth-admin'}
        }
        mock_iam.list_attached_role_policies.return_value = {'AttachedPolicies': []}

        def client_factory(service, **kwargs):
            if service == 'sts':
                return mock_sts
            elif service == 'iam':
                return mock_iam
            return MagicMock()

        mock_boto_client.side_effect = client_factory

        result = setup_aurora_iam_policy_for_current_user('admin', 'cluster-123', 'us-east-1')

        mock_iam.attach_role_policy.assert_called_once()
        assert result is not None


class TestSetupAuroraIAMPolicyUnsupportedIdentities:
    """Tests for unsupported identity types."""

    @patch('awslabs.mysql_mcp_server.connection.cp_api_connection.boto3.client')
    def test_federated_user_raises(self, mock_boto_client):
        """Should raise ValueError for federated users."""
        mock_sts = MagicMock()
        mock_sts.get_caller_identity.return_value = {
            'Account': '123456789012',
            'Arn': 'arn:aws:sts::123456789012:federated-user/feduser',
            'UserId': 'FEDEXAMPLE',
        }

        mock_iam = MagicMock()

        def client_factory(service, **kwargs):
            if service == 'sts':
                return mock_sts
            elif service == 'iam':
                return mock_iam
            return MagicMock()

        mock_boto_client.side_effect = client_factory

        with pytest.raises(ValueError, match='Cannot attach policies to federated users'):
            setup_aurora_iam_policy_for_current_user('admin', 'cluster-123', 'us-east-1')

    @patch('awslabs.mysql_mcp_server.connection.cp_api_connection.boto3.client')
    def test_root_user_raises(self, mock_boto_client):
        """Should raise ValueError for root users."""
        mock_sts = MagicMock()
        mock_sts.get_caller_identity.return_value = {
            'Account': '123456789012',
            'Arn': 'arn:aws:iam::123456789012:root',
            'UserId': '123456789012',
        }

        mock_iam = MagicMock()

        def client_factory(service, **kwargs):
            if service == 'sts':
                return mock_sts
            elif service == 'iam':
                return mock_iam
            return MagicMock()

        mock_boto_client.side_effect = client_factory

        with pytest.raises(ValueError, match='Cannot.*root user'):
            setup_aurora_iam_policy_for_current_user('admin', 'cluster-123', 'us-east-1')


class TestSetupAuroraIAMPolicyVersionCleanup:
    """Tests for policy version cleanup when at limit."""

    @patch('awslabs.mysql_mcp_server.connection.cp_api_connection.boto3.client')
    def test_deletes_oldest_version_when_at_limit(self, mock_boto_client, mock_sts, mock_iam):
        """Should delete oldest non-default version when at 5 version limit."""
        mock_iam.get_policy.return_value = {
            'Policy': {
                'Arn': 'arn:aws:iam::123456789012:policy/AuroraIAMAuth-admin',
                'DefaultVersionId': 'v5',
            }
        }
        mock_iam.get_policy_version.return_value = {
            'PolicyVersion': {
                'Document': {
                    'Version': '2012-10-17',
                    'Statement': [
                        {
                            'Effect': 'Allow',
                            'Action': 'rds-db:connect',
                            'Resource': ['arn:aws:rds-db:us-east-1:123:dbuser:cluster-OLD/admin'],
                        }
                    ],
                }
            }
        }
        mock_iam.list_policy_versions.return_value = {
            'Versions': [
                {'VersionId': 'v1', 'IsDefaultVersion': False, 'CreateDate': '2024-01-01'},
                {'VersionId': 'v2', 'IsDefaultVersion': False, 'CreateDate': '2024-02-01'},
                {'VersionId': 'v3', 'IsDefaultVersion': False, 'CreateDate': '2024-03-01'},
                {'VersionId': 'v4', 'IsDefaultVersion': False, 'CreateDate': '2024-04-01'},
                {'VersionId': 'v5', 'IsDefaultVersion': True, 'CreateDate': '2024-05-01'},
            ]
        }
        mock_iam.create_policy_version.return_value = {'PolicyVersion': {'VersionId': 'v6'}}
        mock_iam.list_attached_user_policies.return_value = {
            'AttachedPolicies': [
                {
                    'PolicyArn': 'arn:aws:iam::123456789012:policy/AuroraIAMAuth-admin',
                    'PolicyName': 'AuroraIAMAuth-admin',
                }
            ]
        }

        def client_factory(service, **kwargs):
            if service == 'sts':
                return mock_sts
            elif service == 'iam':
                return mock_iam
            return MagicMock()

        mock_boto_client.side_effect = client_factory

        setup_aurora_iam_policy_for_current_user('admin', 'cluster-NEW', 'us-east-1')

        mock_iam.delete_policy_version.assert_called_once_with(
            PolicyArn='arn:aws:iam::123456789012:policy/AuroraIAMAuth-admin',
            VersionId='v1',
        )
