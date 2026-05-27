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


class TestSetupAuroraIAMPolicyRoleErrorPaths:
    """Tests for the role-attach error branches that returned partial coverage.

    These exercise the codepaths in cp_api_connection.py around lines
    491-582 (the second try/except that wraps attach_user_policy /
    attach_role_policy and the create_policy fallback).
    """

    @staticmethod
    def _client_factory(sts, iam):
        def factory(service, **kwargs):
            if service == 'sts':
                return sts
            elif service == 'iam':
                return iam
            return MagicMock()

        return factory

    @pytest.fixture
    def assumed_role_sts(self):
        """Build an STS mock returning an assumed-role caller identity."""
        sts = MagicMock()
        sts.get_caller_identity.return_value = {
            'Account': '123456789012',
            'Arn': 'arn:aws:sts::123456789012:assumed-role/MyRole/session',
            'UserId': 'AROAEXAMPLE:session',
        }
        return sts

    @patch('awslabs.mysql_mcp_server.connection.cp_api_connection.boto3.client')
    def test_create_policy_swallows_entity_already_exists(self, mock_boto, mock_sts, mock_iam):
        """If two processes race to create the policy, EntityAlreadyExists is logged, not raised."""
        mock_iam.get_policy.side_effect = mock_iam.exceptions.NoSuchEntityException()
        mock_iam.create_policy.side_effect = mock_iam.exceptions.EntityAlreadyExistsException()
        mock_iam.list_attached_user_policies.return_value = {'AttachedPolicies': []}

        mock_boto.side_effect = self._client_factory(mock_sts, mock_iam)

        # Should not raise; falls through to attach with the predicted policy_arn.
        result = setup_aurora_iam_policy_for_current_user('admin', 'cluster-1', 'us-east-1')
        assert result is not None

    @patch('awslabs.mysql_mcp_server.connection.cp_api_connection.boto3.client')
    def test_create_policy_unexpected_error_reraises(self, mock_boto, mock_sts, mock_iam):
        """Any non-EntityAlreadyExists error from create_policy must propagate."""
        mock_iam.get_policy.side_effect = mock_iam.exceptions.NoSuchEntityException()
        mock_iam.create_policy.side_effect = RuntimeError('AWS is on fire')

        mock_boto.side_effect = self._client_factory(mock_sts, mock_iam)

        with pytest.raises(RuntimeError, match='AWS is on fire'):
            setup_aurora_iam_policy_for_current_user('admin', 'cluster-1', 'us-east-1')

    @patch('awslabs.mysql_mcp_server.connection.cp_api_connection.boto3.client')
    def test_get_policy_unexpected_error_reraises(self, mock_boto, mock_sts, mock_iam):
        """A non-NoSuchEntity error from get_policy is re-raised after logging."""
        mock_iam.get_policy.side_effect = RuntimeError('IAM unreachable')

        mock_boto.side_effect = self._client_factory(mock_sts, mock_iam)

        with pytest.raises(RuntimeError, match='IAM unreachable'):
            setup_aurora_iam_policy_for_current_user('admin', 'cluster-1', 'us-east-1')

    @patch('awslabs.mysql_mcp_server.connection.cp_api_connection.boto3.client')
    def test_role_attach_access_denied_returns_policy_arn_with_instructions(
        self, mock_boto, assumed_role_sts, mock_iam
    ):
        """Access denied on attach_role_policy must NOT raise; return the arn so the operator can attach manually."""
        mock_iam.get_policy.side_effect = mock_iam.exceptions.NoSuchEntityException()
        mock_iam.create_policy.return_value = {
            'Policy': {'Arn': 'arn:aws:iam::123456789012:policy/AuroraIAMAuth-admin'}
        }
        mock_iam.list_attached_role_policies.return_value = {'AttachedPolicies': []}
        mock_iam.attach_role_policy.side_effect = mock_iam.exceptions.AccessDeniedException()

        mock_boto.side_effect = self._client_factory(assumed_role_sts, mock_iam)

        result = setup_aurora_iam_policy_for_current_user('admin', 'cluster-1', 'us-east-1')
        assert result == 'arn:aws:iam::123456789012:policy/AuroraIAMAuth-admin'

    @patch('awslabs.mysql_mcp_server.connection.cp_api_connection.boto3.client')
    def test_role_attach_no_such_entity_reraises(self, mock_boto, assumed_role_sts, mock_iam):
        """If the role itself is not found during attach, re-raise NoSuchEntity."""
        mock_iam.get_policy.side_effect = mock_iam.exceptions.NoSuchEntityException()
        mock_iam.create_policy.return_value = {
            'Policy': {'Arn': 'arn:aws:iam::123456789012:policy/AuroraIAMAuth-admin'}
        }
        mock_iam.list_attached_role_policies.side_effect = (
            mock_iam.exceptions.NoSuchEntityException()
        )

        mock_boto.side_effect = self._client_factory(assumed_role_sts, mock_iam)

        with pytest.raises(mock_iam.exceptions.NoSuchEntityException):
            setup_aurora_iam_policy_for_current_user('admin', 'cluster-1', 'us-east-1')

    @patch('awslabs.mysql_mcp_server.connection.cp_api_connection.boto3.client')
    def test_user_attach_no_such_entity_reraises(self, mock_boto, mock_sts, mock_iam):
        """If the user is not found during list_attached_user_policies, re-raise."""
        mock_iam.get_policy.side_effect = mock_iam.exceptions.NoSuchEntityException()
        mock_iam.create_policy.return_value = {
            'Policy': {'Arn': 'arn:aws:iam::123456789012:policy/AuroraIAMAuth-admin'}
        }
        mock_iam.list_attached_user_policies.side_effect = (
            mock_iam.exceptions.NoSuchEntityException()
        )

        mock_boto.side_effect = self._client_factory(mock_sts, mock_iam)

        with pytest.raises(mock_iam.exceptions.NoSuchEntityException):
            setup_aurora_iam_policy_for_current_user('admin', 'cluster-1', 'us-east-1')

    @patch('awslabs.mysql_mcp_server.connection.cp_api_connection.boto3.client')
    def test_user_attach_limit_exceeded_reraises(self, mock_boto, mock_sts, mock_iam):
        """LimitExceeded (10-policies-per-principal) must re-raise after a clear log."""
        mock_iam.get_policy.side_effect = mock_iam.exceptions.NoSuchEntityException()
        mock_iam.create_policy.return_value = {
            'Policy': {'Arn': 'arn:aws:iam::123456789012:policy/AuroraIAMAuth-admin'}
        }
        mock_iam.list_attached_user_policies.return_value = {'AttachedPolicies': []}
        mock_iam.attach_user_policy.side_effect = mock_iam.exceptions.LimitExceededException()

        mock_boto.side_effect = self._client_factory(mock_sts, mock_iam)

        with pytest.raises(mock_iam.exceptions.LimitExceededException):
            setup_aurora_iam_policy_for_current_user('admin', 'cluster-1', 'us-east-1')

    @patch('awslabs.mysql_mcp_server.connection.cp_api_connection.boto3.client')
    def test_user_attach_generic_exception_reraises(self, mock_boto, mock_sts, mock_iam):
        """Any other attach exception (e.g. throttling) re-raises with traceback logged."""
        mock_iam.get_policy.side_effect = mock_iam.exceptions.NoSuchEntityException()
        mock_iam.create_policy.return_value = {
            'Policy': {'Arn': 'arn:aws:iam::123456789012:policy/AuroraIAMAuth-admin'}
        }
        mock_iam.list_attached_user_policies.return_value = {'AttachedPolicies': []}
        mock_iam.attach_user_policy.side_effect = RuntimeError('throttled')

        mock_boto.side_effect = self._client_factory(mock_sts, mock_iam)

        with pytest.raises(RuntimeError, match='throttled'):
            setup_aurora_iam_policy_for_current_user('admin', 'cluster-1', 'us-east-1')


class TestSetupAuroraIAMPolicySTSAndArnEdgeCases:
    """Edge cases in identity resolution: STS failure and unexpected ARN shapes."""

    @patch('awslabs.mysql_mcp_server.connection.cp_api_connection.boto3.client')
    def test_sts_get_caller_identity_failure_reraises(self, mock_boto):
        """If get_caller_identity blows up, the exception propagates with a clear log line."""
        sts = MagicMock()
        sts.get_caller_identity.side_effect = RuntimeError('IMDS unreachable')
        iam = MagicMock()

        def factory(service, **kwargs):
            if service == 'sts':
                return sts
            elif service == 'iam':
                return iam
            return MagicMock()

        mock_boto.side_effect = factory

        with pytest.raises(RuntimeError, match='IMDS unreachable'):
            setup_aurora_iam_policy_for_current_user('admin', 'cluster-1', 'us-east-1')

    @patch('awslabs.mysql_mcp_server.connection.cp_api_connection.boto3.client')
    def test_unexpected_arn_format_raises(self, mock_boto):
        """Unrecognised ARN shapes (no :user/, :role/, :federated-user/, :root) must raise."""
        sts = MagicMock()
        sts.get_caller_identity.return_value = {
            'Account': '123456789012',
            # Neither user, assumed-role, federated-user, nor root.
            'Arn': 'arn:aws:iam::123456789012:something-weird/example',
            'UserId': 'EXAMPLE',
        }
        iam = MagicMock()

        def factory(service, **kwargs):
            if service == 'sts':
                return sts
            elif service == 'iam':
                return iam
            return MagicMock()

        mock_boto.side_effect = factory

        with pytest.raises(ValueError, match='Unexpected ARN format'):
            setup_aurora_iam_policy_for_current_user('admin', 'cluster-1', 'us-east-1')


class TestSetupAuroraIAMPolicySingleStringResource:
    """Covers the branch where existing policy has Resource as a string, not a list."""

    @patch('awslabs.mysql_mcp_server.connection.cp_api_connection.boto3.client')
    def test_resource_string_is_normalized_to_list(self, mock_boto, mock_sts, mock_iam):
        """A pre-existing policy with Resource: '<arn>' (not a list) is upgraded in place."""
        mock_iam.get_policy.return_value = {
            'Policy': {
                'Arn': 'arn:aws:iam::123456789012:policy/AuroraIAMAuth-admin',
                'DefaultVersionId': 'v1',
            }
        }
        # Resource is a single string, not a list -> normalisation branch fires.
        mock_iam.get_policy_version.return_value = {
            'PolicyVersion': {
                'Document': {
                    'Version': '2012-10-17',
                    'Statement': [
                        {
                            'Effect': 'Allow',
                            'Action': 'rds-db:connect',
                            'Resource': 'arn:aws:rds-db:us-east-1:123456789012:dbuser:cluster-OLD/admin',
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

        def factory(service, **kwargs):
            if service == 'sts':
                return mock_sts
            elif service == 'iam':
                return mock_iam
            return MagicMock()

        mock_boto.side_effect = factory

        result = setup_aurora_iam_policy_for_current_user('admin', 'cluster-NEW', 'us-east-1')
        # The new resource was added to the (now-listified) Resource set.
        mock_iam.create_policy_version.assert_called_once()
        assert result is not None


class TestSetupAuroraIAMPolicyRoleAlreadyAttached:
    """Covers the path where the role already has the policy attached."""

    @patch('awslabs.mysql_mcp_server.connection.cp_api_connection.boto3.client')
    def test_skips_attach_when_already_attached(self, mock_boto, mock_iam):
        """If list_attached_role_policies already shows the policy, don't re-attach."""
        sts = MagicMock()
        sts.get_caller_identity.return_value = {
            'Account': '123456789012',
            'Arn': 'arn:aws:sts::123456789012:assumed-role/MyRole/session',
            'UserId': 'AROA:session',
        }
        mock_iam.get_policy.side_effect = mock_iam.exceptions.NoSuchEntityException()
        mock_iam.create_policy.return_value = {
            'Policy': {'Arn': 'arn:aws:iam::123456789012:policy/AuroraIAMAuth-admin'}
        }
        # Both list_attached_role_policies calls (pre-check and post-attach
        # logging) report the policy as already attached. The second call's
        # for-loop covers the marker-logging branch (lines 544-545).
        mock_iam.list_attached_role_policies.return_value = {
            'AttachedPolicies': [
                {
                    'PolicyArn': 'arn:aws:iam::123456789012:policy/AuroraIAMAuth-admin',
                    'PolicyName': 'AuroraIAMAuth-admin',
                },
                {
                    'PolicyArn': 'arn:aws:iam::aws:policy/ReadOnlyAccess',
                    'PolicyName': 'ReadOnlyAccess',
                },
            ]
        }

        def factory(service, **kwargs):
            if service == 'sts':
                return sts
            elif service == 'iam':
                return mock_iam
            return MagicMock()

        mock_boto.side_effect = factory

        result = setup_aurora_iam_policy_for_current_user('admin', 'cluster-1', 'us-east-1')
        # Already-attached short-circuit: attach_role_policy must NOT be called.
        mock_iam.attach_role_policy.assert_not_called()
        assert result is not None
