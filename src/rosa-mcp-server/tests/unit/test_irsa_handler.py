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

"""Tests for the ROSA IRSA handler."""

import json
import pytest
from awslabs.rosa_mcp_server.rosa_irsa_handler import RosaIRSAHandler
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def mock_ocm_with_oidc(mock_ocm_client):
    """OCM client that returns a cluster with OIDC endpoint."""
    mock_ocm_client.get_cluster = AsyncMock(return_value={
        'id': 'test-id',
        'name': 'test-cluster',
        'state': 'ready',
        'aws': {
            'sts': {
                'oidc_endpoint_url': 'https://rh-oidc.s3.us-east-1.amazonaws.com/abc123',
            },
        },
    })
    return mock_ocm_client


class TestConfigureIRSA:
    """Tests for rosa_configure_irsa."""

    @pytest.mark.asyncio
    async def test_given_write_disabled_when_configure_then_raises(
        self, mock_mcp, mock_ocm_with_oidc, mock_context
    ):
        handler = RosaIRSAHandler(mock_mcp, mock_ocm_with_oidc, allow_write=False)
        with pytest.raises(ValueError, match='Write operations disabled'):
            await handler.rosa_configure_irsa(
                mock_context,
                cluster_id='test-id',
                namespace='app-ns',
                service_account='app-sa',
                role_name='irsa-app-role',
                policy_arn='arn:aws:iam::123456789012:policy/S3ReadOnly',
            )

    @pytest.mark.asyncio
    @patch('boto3.client')
    async def test_given_valid_params_when_configure_then_creates_role_and_attaches_policy(
        self, mock_boto3, mock_mcp, mock_ocm_with_oidc, mock_context
    ):
        mock_sts = MagicMock()
        mock_sts.get_caller_identity.return_value = {'Account': '123456789012'}
        mock_iam = MagicMock()

        def client_factory(service, **kwargs):
            if service == 'sts':
                return mock_sts
            return mock_iam

        mock_boto3.side_effect = client_factory

        handler = RosaIRSAHandler(mock_mcp, mock_ocm_with_oidc, allow_write=True)
        result = await handler.rosa_configure_irsa(
            mock_context,
            cluster_id='test-id',
            namespace='app-ns',
            service_account='app-sa',
            role_name='irsa-app-role',
            policy_arn='arn:aws:iam::123456789012:policy/S3ReadOnly',
            annotate_service_account=False,
        )

        data = json.loads(result[0].text)
        assert data['message'] == 'IRSA configured successfully.'
        assert data['role_name'] == 'irsa-app-role'
        assert data['role_arn'] == 'arn:aws:iam::123456789012:role/irsa-app-role'
        assert data['namespace'] == 'app-ns'
        assert data['service_account'] == 'app-sa'

        # Verify IAM calls
        mock_iam.create_role.assert_called_once()
        call_kwargs = mock_iam.create_role.call_args[1]
        trust_doc = json.loads(call_kwargs['AssumeRolePolicyDocument'])
        assert trust_doc['Statement'][0]['Action'] == 'sts:AssumeRoleWithWebIdentity'
        assert 'rh-oidc.s3.us-east-1.amazonaws.com/abc123' in trust_doc['Statement'][0]['Principal']['Federated']
        condition = trust_doc['Statement'][0]['Condition']['StringEquals']
        assert condition['rh-oidc.s3.us-east-1.amazonaws.com/abc123:sub'] == 'system:serviceaccount:app-ns:app-sa'

        mock_iam.attach_role_policy.assert_called_once_with(
            RoleName='irsa-app-role',
            PolicyArn='arn:aws:iam::123456789012:policy/S3ReadOnly',
        )

    @pytest.mark.asyncio
    async def test_given_cluster_without_oidc_when_configure_then_returns_error(
        self, mock_mcp, mock_ocm_client, mock_context
    ):
        mock_ocm_client.get_cluster = AsyncMock(return_value={
            'id': 'test-id',
            'name': 'test-cluster',
            'aws': {},
        })
        handler = RosaIRSAHandler(mock_mcp, mock_ocm_client, allow_write=True)
        result = await handler.rosa_configure_irsa(
            mock_context,
            cluster_id='test-id',
            namespace='ns',
            service_account='sa',
            role_name='role',
            policy_arn='arn:aws:iam::123:policy/P',
        )
        assert 'does not have an OIDC endpoint' in result[0].text


class TestDescribeIRSA:
    """Tests for rosa_describe_irsa."""

    @pytest.mark.asyncio
    @patch('boto3.client')
    async def test_given_matching_role_when_describe_then_returns_role(
        self, mock_boto3, mock_mcp, mock_ocm_with_oidc, mock_context
    ):
        oidc_issuer = 'rh-oidc.s3.us-east-1.amazonaws.com/abc123'
        mock_iam = MagicMock()
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [
            {
                'Roles': [
                    {
                        'RoleName': 'irsa-app-role',
                        'Arn': 'arn:aws:iam::123456789012:role/irsa-app-role',
                        'AssumeRolePolicyDocument': {
                            'Statement': [
                                {
                                    'Principal': {'Federated': f'arn:aws:iam::123456789012:oidc-provider/{oidc_issuer}'},
                                    'Condition': {
                                        'StringEquals': {
                                            f'{oidc_issuer}:sub': 'system:serviceaccount:app-ns:app-sa',
                                        },
                                    },
                                },
                            ],
                        },
                    },
                    {
                        'RoleName': 'unrelated-role',
                        'Arn': 'arn:aws:iam::123456789012:role/unrelated-role',
                        'AssumeRolePolicyDocument': {
                            'Statement': [
                                {
                                    'Principal': {'Federated': 'arn:aws:iam::123456789012:oidc-provider/other'},
                                    'Condition': {'StringEquals': {}},
                                },
                            ],
                        },
                    },
                ],
            },
        ]
        mock_iam.get_paginator.return_value = mock_paginator
        mock_iam.list_attached_role_policies.return_value = {
            'AttachedPolicies': [{'PolicyName': 'S3ReadOnly', 'PolicyArn': 'arn:aws:iam::123:policy/S3ReadOnly'}],
        }
        mock_boto3.return_value = mock_iam

        handler = RosaIRSAHandler(mock_mcp, mock_ocm_with_oidc, allow_write=False)
        result = await handler.rosa_describe_irsa(
            mock_context,
            cluster_id='test-id',
            namespace='app-ns',
            service_account='app-sa',
        )

        data = json.loads(result[0].text)
        assert data['role_count'] == 1
        assert data['matching_roles'][0]['RoleName'] == 'irsa-app-role'
        assert len(data['matching_roles'][0]['AttachedPolicies']) == 1

    @pytest.mark.asyncio
    @patch('boto3.client')
    async def test_given_no_matching_role_when_describe_then_returns_empty(
        self, mock_boto3, mock_mcp, mock_ocm_with_oidc, mock_context
    ):
        mock_iam = MagicMock()
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [{'Roles': []}]
        mock_iam.get_paginator.return_value = mock_paginator
        mock_boto3.return_value = mock_iam

        handler = RosaIRSAHandler(mock_mcp, mock_ocm_with_oidc, allow_write=False)
        result = await handler.rosa_describe_irsa(
            mock_context,
            cluster_id='test-id',
            namespace='app-ns',
            service_account='app-sa',
        )

        data = json.loads(result[0].text)
        assert data['role_count'] == 0
        assert data['matching_roles'] == []


class TestDeleteIRSA:
    """Tests for rosa_delete_irsa."""

    @pytest.mark.asyncio
    async def test_given_write_disabled_when_delete_then_raises(
        self, mock_mcp, mock_ocm_with_oidc, mock_context
    ):
        handler = RosaIRSAHandler(mock_mcp, mock_ocm_with_oidc, allow_write=False)
        with pytest.raises(ValueError, match='Write operations disabled'):
            await handler.rosa_delete_irsa(mock_context, role_name='irsa-app-role')

    @pytest.mark.asyncio
    @patch('boto3.client')
    async def test_given_role_with_policies_when_delete_then_detaches_and_deletes(
        self, mock_boto3, mock_mcp, mock_ocm_with_oidc, mock_context
    ):
        mock_iam = MagicMock()
        mock_iam.list_attached_role_policies.return_value = {
            'AttachedPolicies': [
                {'PolicyName': 'S3ReadOnly', 'PolicyArn': 'arn:aws:iam::123:policy/S3ReadOnly'},
            ],
        }
        mock_iam.list_role_policies.return_value = {
            'PolicyNames': ['inline-1'],
        }
        mock_boto3.return_value = mock_iam

        handler = RosaIRSAHandler(mock_mcp, mock_ocm_with_oidc, allow_write=True)
        result = await handler.rosa_delete_irsa(mock_context, role_name='irsa-app-role')

        data = json.loads(result[0].text)
        assert 'deleted successfully' in data['message']
        assert data['policies_detached'] == 2

        mock_iam.detach_role_policy.assert_called_once_with(
            RoleName='irsa-app-role',
            PolicyArn='arn:aws:iam::123:policy/S3ReadOnly',
        )
        mock_iam.delete_role_policy.assert_called_once_with(
            RoleName='irsa-app-role',
            PolicyName='inline-1',
        )
        mock_iam.delete_role.assert_called_once_with(RoleName='irsa-app-role')


class TestBuildTrustPolicy:
    """Tests for the trust policy builder."""

    def test_trust_policy_structure(self, mock_mcp, mock_ocm_with_oidc):
        handler = RosaIRSAHandler(mock_mcp, mock_ocm_with_oidc, allow_write=False)
        policy = handler._build_trust_policy(
            account_id='123456789012',
            oidc_issuer='rh-oidc.s3.us-east-1.amazonaws.com/abc123',
            namespace='my-ns',
            service_account='my-sa',
        )

        assert policy['Version'] == '2012-10-17'
        stmt = policy['Statement'][0]
        assert stmt['Effect'] == 'Allow'
        assert stmt['Action'] == 'sts:AssumeRoleWithWebIdentity'
        assert '123456789012' in stmt['Principal']['Federated']
        assert stmt['Condition']['StringEquals'][
            'rh-oidc.s3.us-east-1.amazonaws.com/abc123:sub'
        ] == 'system:serviceaccount:my-ns:my-sa'
