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

"""Tests for the ROSA operator handler."""

import json
import pytest
from awslabs.rosa_mcp_server.rosa_operator_handler import RosaOperatorHandler
from unittest.mock import AsyncMock


class TestRosaListStsOperatorRoles:
    """Tests for rosa_list_sts_operator_roles."""

    @pytest.mark.asyncio
    async def test_list_sts_operator_roles_returns_data(
        self, mock_mcp, mock_ocm_client, mock_context
    ):
        """Test rosa_list_sts_operator_roles returns operator role data."""
        mock_ocm_client.request = AsyncMock(return_value={
            'items': [
                {
                    'name': 'ebs-cloud-credentials',
                    'namespace': 'openshift-cluster-csi-drivers',
                    'role_arn': 'arn:aws:iam::123456789012:role/test-ebs-cloud-credentials',
                },
                {
                    'name': 'cloud-credentials',
                    'namespace': 'openshift-ingress-operator',
                    'role_arn': 'arn:aws:iam::123456789012:role/test-cloud-credentials',
                },
                {
                    'name': 'installer-cloud-credentials',
                    'namespace': 'openshift-image-registry',
                    'role_arn': 'arn:aws:iam::123456789012:role/test-installer-cloud-credentials',
                },
                {
                    'name': 'cloud-credential-operator-iam-ro-creds',
                    'namespace': 'openshift-cloud-credential-operator',
                    'role_arn': 'arn:aws:iam::123456789012:role/test-cloud-credential-operator',
                },
            ],
        })
        handler = RosaOperatorHandler(mock_mcp, mock_ocm_client, allow_write=False)
        result = await handler.rosa_list_sts_operator_roles(mock_context, cluster_id='test-id')

        mock_ocm_client.request.assert_called_once_with(
            'GET', '/api/clusters_mgmt/v1/clusters/test-id/sts_operator_roles'
        )
        assert isinstance(result, list)
        data = json.loads(result[0].text)
        assert 'items' in data
        assert len(data['items']) == 4


class TestRosaGetClusterOperators:
    """Tests for rosa_get_cluster_operators."""

    @pytest.mark.asyncio
    async def test_get_cluster_operators_returns_status(
        self, mock_mcp, mock_ocm_client, mock_context
    ):
        """Test rosa_get_cluster_operators returns operator health status."""
        mock_ocm_client.request = AsyncMock(return_value={
            'operators': [
                {'name': 'authentication', 'condition': 'Available', 'value': 'True'},
                {'name': 'console', 'condition': 'Available', 'value': 'True'},
                {'name': 'dns', 'condition': 'Available', 'value': 'True'},
                {'name': 'ingress', 'condition': 'Degraded', 'value': 'False'},
            ],
        })
        handler = RosaOperatorHandler(mock_mcp, mock_ocm_client, allow_write=False)
        result = await handler.rosa_get_cluster_operators(mock_context, cluster_id='test-id')

        mock_ocm_client.request.assert_called_once_with(
            'GET', '/api/clusters_mgmt/v1/clusters/test-id/metric_queries/cluster_operators'
        )
        data = json.loads(result[0].text)
        assert 'operators' in data
        assert len(data['operators']) == 4


class TestRosaListStsCredentialRequests:
    """Tests for rosa_list_sts_credential_requests."""

    @pytest.mark.asyncio
    async def test_list_sts_credential_requests(
        self, mock_mcp, mock_ocm_client, mock_context
    ):
        """Test rosa_list_sts_credential_requests returns credential request templates."""
        mock_ocm_client.request = AsyncMock(return_value={
            'items': [
                {
                    'name': 'ebs-cloud-credentials',
                    'namespace': 'openshift-cluster-csi-drivers',
                    'service_accounts': ['aws-ebs-csi-driver-operator'],
                },
                {
                    'name': 'cloud-credentials',
                    'namespace': 'openshift-ingress-operator',
                    'service_accounts': ['ingress-operator'],
                },
                {
                    'name': 'installer-cloud-credentials',
                    'namespace': 'openshift-image-registry',
                    'service_accounts': ['cluster-image-registry-operator'],
                },
                {
                    'name': 'cloud-credential-operator-iam-ro-creds',
                    'namespace': 'openshift-cloud-credential-operator',
                    'service_accounts': ['cloud-credential-operator'],
                },
            ],
        })
        handler = RosaOperatorHandler(mock_mcp, mock_ocm_client, allow_write=False)
        result = await handler.rosa_list_sts_credential_requests(mock_context)

        mock_ocm_client.request.assert_called_once_with(
            'GET', '/api/clusters_mgmt/v1/aws_inquiries/sts_credential_requests'
        )
        data = json.loads(result[0].text)
        assert 'items' in data
        assert len(data['items']) == 4


class TestRosaListStsPolicies:
    """Tests for rosa_list_sts_policies."""

    @pytest.mark.asyncio
    async def test_list_sts_policies(
        self, mock_mcp, mock_ocm_client, mock_context
    ):
        """Test rosa_list_sts_policies returns STS IAM policies."""
        mock_ocm_client.request = AsyncMock(return_value={
            'items': [
                {'id': 'operator_iam_role_policy', 'type': 'OperatorRole'},
                {'id': 'account_installer_policy', 'type': 'AccountRole'},
                {'id': 'account_support_policy', 'type': 'AccountRole'},
            ],
        })
        handler = RosaOperatorHandler(mock_mcp, mock_ocm_client, allow_write=False)
        result = await handler.rosa_list_sts_policies(mock_context)

        mock_ocm_client.request.assert_called_once_with(
            'GET', '/api/clusters_mgmt/v1/aws_inquiries/sts_policies'
        )
        data = json.loads(result[0].text)
        assert 'items' in data
        assert len(data['items']) == 3


class TestRosaInstallOperator:
    """Tests for rosa_install_operator."""

    @pytest.mark.asyncio
    async def test_install_operator_requires_write(
        self, mock_mcp, mock_ocm_client, mock_context
    ):
        """Test rosa_install_operator requires allow_write."""
        handler = RosaOperatorHandler(mock_mcp, mock_ocm_client, allow_write=False)

        with pytest.raises(ValueError, match='Write operations disabled'):
            await handler.rosa_install_operator(
                mock_context, cluster_id='test-id', addon_id='operator-1'
            )

    @pytest.mark.asyncio
    async def test_install_operator_builds_correct_body(
        self, mock_mcp, mock_ocm_client, mock_context
    ):
        """Test rosa_install_operator builds correct request body without parameters."""
        mock_ocm_client.request = AsyncMock(return_value={
            'id': 'operator-1',
            'state': 'installing',
        })
        handler = RosaOperatorHandler(mock_mcp, mock_ocm_client, allow_write=True)
        await handler.rosa_install_operator(
            mock_context, cluster_id='test-id', addon_id='operator-1'
        )

        call_args = mock_ocm_client.request.call_args
        assert call_args[0][0] == 'POST'
        assert '/clusters/test-id/addons' in call_args[0][1]
        body = call_args[1]['body']
        assert body['addon'] == {'id': 'operator-1'}
        assert 'parameters' not in body

    @pytest.mark.asyncio
    async def test_install_operator_with_parameters(
        self, mock_mcp, mock_ocm_client, mock_context
    ):
        """Test rosa_install_operator with parameters builds correct body."""
        mock_ocm_client.request = AsyncMock(return_value={
            'id': 'operator-1',
            'state': 'installing',
        })
        handler = RosaOperatorHandler(mock_mcp, mock_ocm_client, allow_write=True)
        params = {'notification-email': 'admin@example.com', 'size': 'large'}
        await handler.rosa_install_operator(
            mock_context,
            cluster_id='test-id',
            addon_id='operator-1',
            parameters=params,
        )

        call_args = mock_ocm_client.request.call_args
        body = call_args[1]['body']
        assert body['addon'] == {'id': 'operator-1'}
        assert body['parameters']['items'] == [
            {'id': 'notification-email', 'value': 'admin@example.com'},
            {'id': 'size', 'value': 'large'},
        ]


class TestRosaUninstallOperator:
    """Tests for rosa_uninstall_operator."""

    @pytest.mark.asyncio
    async def test_uninstall_operator_requires_write(
        self, mock_mcp, mock_ocm_client, mock_context
    ):
        """Test rosa_uninstall_operator requires allow_write."""
        handler = RosaOperatorHandler(mock_mcp, mock_ocm_client, allow_write=False)

        with pytest.raises(ValueError, match='Write operations disabled'):
            await handler.rosa_uninstall_operator(
                mock_context, cluster_id='test-id', addon_id='operator-1'
            )

    @pytest.mark.asyncio
    async def test_uninstall_operator_calls_correct_endpoint(
        self, mock_mcp, mock_ocm_client, mock_context
    ):
        """Test rosa_uninstall_operator calls correct DELETE endpoint."""
        mock_ocm_client.request = AsyncMock(return_value=None)
        handler = RosaOperatorHandler(mock_mcp, mock_ocm_client, allow_write=True)
        result = await handler.rosa_uninstall_operator(
            mock_context, cluster_id='test-id', addon_id='operator-1'
        )

        mock_ocm_client.request.assert_called_once_with(
            'DELETE', '/api/clusters_mgmt/v1/clusters/test-id/addons/operator-1'
        )
        data = json.loads(result[0].text)
        assert data['status'] == 'operator_uninstalled'
        assert data['addon_id'] == 'operator-1'
        assert data['cluster_id'] == 'test-id'


class TestRosaGetOperatorStatus:
    """Tests for rosa_get_operator_status."""

    @pytest.mark.asyncio
    async def test_get_operator_status(
        self, mock_mcp, mock_ocm_client, mock_context
    ):
        """Test rosa_get_operator_status returns operator installation status."""
        mock_ocm_client.request = AsyncMock(return_value={
            'id': 'operator-1',
            'state': 'ready',
            'state_description': 'Operator is running',
        })
        handler = RosaOperatorHandler(mock_mcp, mock_ocm_client, allow_write=False)
        result = await handler.rosa_get_operator_status(
            mock_context, cluster_id='test-id', addon_id='operator-1'
        )

        mock_ocm_client.request.assert_called_once_with(
            'GET', '/api/clusters_mgmt/v1/clusters/test-id/addons/operator-1'
        )
        data = json.loads(result[0].text)
        assert data['id'] == 'operator-1'
        assert data['state'] == 'ready'
