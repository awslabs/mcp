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

"""Tests for the ROSA cluster handler."""

import json
import pytest
from awslabs.rosa_mcp_server.rosa_cluster_handler import RosaClusterHandler
from mcp.types import TextContent


class TestRosaListClusters:
    """Tests for rosa_list_clusters."""

    def test_given_clusters_when_list_then_returns_cluster_data(
        self, mock_mcp, mock_ocm_client, mock_context
    ):
        """Test rosa_list_clusters returns cluster data."""
        handler = RosaClusterHandler(mock_mcp, mock_ocm_client, allow_write=False)
        pytest.helpers.run_async(
            handler.rosa_list_clusters(mock_context)
        ) if hasattr(pytest, 'helpers') else None

    @pytest.mark.asyncio
    async def test_given_default_search_when_list_then_uses_rosa_filter(
        self, mock_mcp, mock_ocm_client, mock_context
    ):
        """Test rosa_list_clusters uses ROSA product filter by default."""
        handler = RosaClusterHandler(mock_mcp, mock_ocm_client, allow_write=False)
        result = await handler.rosa_list_clusters(mock_context)

        mock_ocm_client.list_clusters.assert_called_once_with(search="product.id = 'rosa'")
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        data = json.loads(result[0].text)
        assert 'items' in data

    @pytest.mark.asyncio
    async def test_given_custom_search_when_list_then_uses_custom_filter(
        self, mock_mcp, mock_ocm_client, mock_context
    ):
        """Test rosa_list_clusters with custom search filter."""
        handler = RosaClusterHandler(mock_mcp, mock_ocm_client, allow_write=False)
        await handler.rosa_list_clusters(mock_context, search="state = 'ready'")

        mock_ocm_client.list_clusters.assert_called_once_with(search="state = 'ready'")


class TestRosaDescribeCluster:
    """Tests for rosa_describe_cluster."""

    @pytest.mark.asyncio
    async def test_given_cluster_id_when_describe_then_returns_detailed_data(
        self, mock_mcp, mock_ocm_client, mock_context
    ):
        """Test rosa_describe_cluster returns detailed cluster data."""
        handler = RosaClusterHandler(mock_mcp, mock_ocm_client, allow_write=False)
        result = await handler.rosa_describe_cluster(mock_context, cluster_id='test-id')

        mock_ocm_client.get_cluster.assert_called_once_with('test-id')
        assert isinstance(result, list)
        data = json.loads(result[0].text)
        assert data['id'] == 'test-id'
        assert data['name'] == 'test-cluster'


class TestRosaCreateCluster:
    """Tests for rosa_create_cluster."""

    @pytest.mark.asyncio
    async def test_given_write_disabled_when_create_then_raises_value_error(
        self, mock_mcp, mock_ocm_client, mock_context
    ):
        """Test rosa_create_cluster requires allow_write."""
        handler = RosaClusterHandler(mock_mcp, mock_ocm_client, allow_write=False)

        with pytest.raises(ValueError, match='Write operations disabled'):
            await handler.rosa_create_cluster(
                mock_context,
                name='test-cluster',
                region='us-east-1',
                aws_account_id='123456789012',
            )

    @pytest.mark.asyncio
    async def test_given_basic_params_when_create_then_builds_correct_body(
        self, mock_mcp, mock_ocm_client, mock_context
    ):
        """Test rosa_create_cluster builds correct body with all fields."""
        handler = RosaClusterHandler(mock_mcp, mock_ocm_client, allow_write=True)
        await handler.rosa_create_cluster(
            mock_context,
            name='my-cluster',
            region='us-east-1',
            aws_account_id='123456789012',
            version='4.14.5',
            multi_az=True,
            compute_nodes=6,
            compute_machine_type='m5.2xlarge',
            etcd_encryption=True,
            fips=True,
        )

        mock_ocm_client.create_cluster.assert_called_once()
        body = mock_ocm_client.create_cluster.call_args[0][0]
        assert body['name'] == 'my-cluster'
        assert body['region'] == {'id': 'us-east-1'}
        assert body['multi_az'] is True
        assert body['nodes']['compute'] == 6
        assert body['nodes']['compute_machine_type'] == {'id': 'm5.2xlarge'}
        assert body['version'] == {'id': 'openshift-v4.14.5', 'channel_group': 'stable'}
        assert body['fips'] is True
        assert body['etcd_encryption'] is True

    @pytest.mark.asyncio
    async def test_given_sts_config_when_create_then_includes_sts_body(
        self, mock_mcp, mock_ocm_client, mock_context
    ):
        """Test rosa_create_cluster with STS config."""
        handler = RosaClusterHandler(mock_mcp, mock_ocm_client, allow_write=True)
        await handler.rosa_create_cluster(
            mock_context,
            name='sts-cluster',
            region='us-east-1',
            aws_account_id='123456789012',
            installer_role_arn='arn:aws:iam::123456789012:role/Installer',
            support_role_arn='arn:aws:iam::123456789012:role/Support',
            controlplane_role_arn='arn:aws:iam::123456789012:role/ControlPlane',
            worker_role_arn='arn:aws:iam::123456789012:role/Worker',
            operator_role_prefix='my-prefix',
            oidc_config_id='oidc-123',
        )

        body = mock_ocm_client.create_cluster.call_args[0][0]
        assert body['aws']['sts']['enabled'] is True
        assert body['aws']['sts']['role_arn'] == 'arn:aws:iam::123456789012:role/Installer'
        assert body['aws']['sts']['support_role_arn'] == 'arn:aws:iam::123456789012:role/Support'
        assert body['aws']['sts']['instance_iam_roles']['master_role_arn'] == 'arn:aws:iam::123456789012:role/ControlPlane'
        assert body['aws']['sts']['instance_iam_roles']['worker_role_arn'] == 'arn:aws:iam::123456789012:role/Worker'
        assert body['aws']['sts']['operator_role_prefix'] == 'my-prefix'
        assert body['aws']['sts']['oidc_config'] == {'id': 'oidc-123'}

    @pytest.mark.asyncio
    async def test_given_subnet_ids_and_private_when_create_then_sets_byo_vpc(
        self, mock_mcp, mock_ocm_client, mock_context
    ):
        """Test rosa_create_cluster with subnet_ids and private."""
        handler = RosaClusterHandler(mock_mcp, mock_ocm_client, allow_write=True)
        await handler.rosa_create_cluster(
            mock_context,
            name='private-cluster',
            region='us-east-1',
            aws_account_id='123456789012',
            private=True,
            subnet_ids=['subnet-abc', 'subnet-def'],
            tags={'env': 'prod'},
        )

        body = mock_ocm_client.create_cluster.call_args[0][0]
        assert body['aws']['subnet_ids'] == ['subnet-abc', 'subnet-def']
        assert body['aws']['private_link'] is True
        assert body['aws']['tags'] == {'env': 'prod'}


class TestRosaDeleteCluster:
    """Tests for rosa_delete_cluster."""

    @pytest.mark.asyncio
    async def test_given_write_disabled_when_delete_then_raises_value_error(
        self, mock_mcp, mock_ocm_client, mock_context
    ):
        """Test rosa_delete_cluster requires allow_write."""
        handler = RosaClusterHandler(mock_mcp, mock_ocm_client, allow_write=False)

        with pytest.raises(ValueError, match='Write operations disabled'):
            await handler.rosa_delete_cluster(mock_context, cluster_id='test-id')

    @pytest.mark.asyncio
    async def test_given_write_enabled_when_delete_then_calls_ocm_correctly(
        self, mock_mcp, mock_ocm_client, mock_context
    ):
        """Test rosa_delete_cluster calls OCM correctly."""
        handler = RosaClusterHandler(mock_mcp, mock_ocm_client, allow_write=True)
        result = await handler.rosa_delete_cluster(mock_context, cluster_id='test-id')

        mock_ocm_client.delete_cluster.assert_called_once_with('test-id', deprovision=True)
        data = json.loads(result[0].text)
        assert data['status'] == 'deletion_initiated'
        assert data['http_status'] == 204


class TestRosaListVersions:
    """Tests for rosa_list_versions."""

    @pytest.mark.asyncio
    async def test_given_default_params_when_list_versions_then_filters_rosa_enabled(
        self, mock_mcp, mock_ocm_client, mock_context
    ):
        """Test rosa_list_versions filters ROSA-enabled versions."""
        handler = RosaClusterHandler(mock_mcp, mock_ocm_client, allow_write=False)
        await handler.rosa_list_versions(mock_context)

        call_args = mock_ocm_client.list_versions.call_args
        search = call_args[1]['search']
        assert "rosa_enabled = 'true'" in search
        assert "enabled = 'true'" in search
        assert "channel_group = 'stable'" in search

    @pytest.mark.asyncio
    async def test_given_hcp_flag_when_list_versions_then_includes_hcp_filter(
        self, mock_mcp, mock_ocm_client, mock_context
    ):
        """Test rosa_list_versions with hosted_cp_only flag."""
        handler = RosaClusterHandler(mock_mcp, mock_ocm_client, allow_write=False)
        await handler.rosa_list_versions(mock_context, hosted_cp_only=True)

        call_args = mock_ocm_client.list_versions.call_args
        search = call_args[1]['search']
        assert "hosted_control_plane_enabled = 'true'" in search


class TestRosaListUpgrades:
    """Tests for rosa_list_upgrades."""

    @pytest.mark.asyncio
    async def test_given_cluster_with_upgrades_when_list_then_returns_available(
        self, mock_mcp, mock_ocm_client, mock_context
    ):
        """Test rosa_list_upgrades returns available versions."""
        handler = RosaClusterHandler(mock_mcp, mock_ocm_client, allow_write=False)
        result = await handler.rosa_list_upgrades(mock_context, cluster_id='test-id')

        data = json.loads(result[0].text)
        assert data['cluster_id'] == 'test-id'
        assert data['current_version'] == '4.14.5'
        assert '4.14.6' in data['available_upgrades']
        assert '4.14.7' in data['available_upgrades']


class TestRosaUpgradeCluster:
    """Tests for rosa_upgrade_cluster."""

    @pytest.mark.asyncio
    async def test_given_write_disabled_when_upgrade_then_raises_value_error(
        self, mock_mcp, mock_ocm_client, mock_context
    ):
        """Test rosa_upgrade_cluster requires allow_write."""
        handler = RosaClusterHandler(mock_mcp, mock_ocm_client, allow_write=False)

        with pytest.raises(ValueError, match='Write operations disabled'):
            await handler.rosa_upgrade_cluster(
                mock_context, cluster_id='test-id', version='4.14.6'
            )

    @pytest.mark.asyncio
    async def test_given_immediate_upgrade_when_upgrade_then_creates_manual_policy(
        self, mock_mcp, mock_ocm_client, mock_context
    ):
        """Test rosa_upgrade_cluster creates upgrade policy."""
        handler = RosaClusterHandler(mock_mcp, mock_ocm_client, allow_write=True)
        await handler.rosa_upgrade_cluster(
            mock_context, cluster_id='test-id', version='4.14.6'
        )

        mock_ocm_client.create_upgrade_policy.assert_called_once()
        call_args = mock_ocm_client.create_upgrade_policy.call_args
        assert call_args[0][0] == 'test-id'
        body = call_args[0][1]
        assert body['version'] == '4.14.6'
        assert body['schedule_type'] == 'manual'

    @pytest.mark.asyncio
    async def test_given_scheduled_upgrade_when_upgrade_then_sets_automatic(
        self, mock_mcp, mock_ocm_client, mock_context
    ):
        """Test rosa_upgrade_cluster with scheduled upgrade."""
        handler = RosaClusterHandler(mock_mcp, mock_ocm_client, allow_write=True)
        await handler.rosa_upgrade_cluster(
            mock_context, cluster_id='test-id', version='4.14.6', schedule='0 2 * * *'
        )

        body = mock_ocm_client.create_upgrade_policy.call_args[0][1]
        assert body['schedule'] == '0 2 * * *'
        assert body['schedule_type'] == 'automatic'


class TestRosaGetClusterCredentials:
    """Tests for rosa_get_cluster_credentials."""

    @pytest.mark.asyncio
    async def test_given_cluster_when_get_credentials_then_returns_data(
        self, mock_mcp, mock_ocm_client, mock_context
    ):
        """Test rosa_get_cluster_credentials returns credential data."""
        handler = RosaClusterHandler(mock_mcp, mock_ocm_client, allow_write=False)
        result = await handler.rosa_get_cluster_credentials(mock_context, cluster_id='test-id')

        mock_ocm_client.get_cluster_credentials.assert_called_once_with('test-id')
        data = json.loads(result[0].text)
        assert 'kubeconfig' in data


class TestRosaGetInstallLogs:
    """Tests for rosa_get_install_logs."""

    @pytest.mark.asyncio
    async def test_given_cluster_when_get_logs_then_returns_content(
        self, mock_mcp, mock_ocm_client, mock_context
    ):
        """Test rosa_get_install_logs returns log content."""
        handler = RosaClusterHandler(mock_mcp, mock_ocm_client, allow_write=False)
        result = await handler.rosa_get_install_logs(mock_context, cluster_id='test-id')

        mock_ocm_client.get_install_logs.assert_called_once_with('test-id', tail=None)
        data = json.loads(result[0].text)
        assert 'content' in data

    @pytest.mark.asyncio
    async def test_given_tail_param_when_get_logs_then_passes_tail(
        self, mock_mcp, mock_ocm_client, mock_context
    ):
        """Test rosa_get_install_logs with tail parameter."""
        handler = RosaClusterHandler(mock_mcp, mock_ocm_client, allow_write=False)
        await handler.rosa_get_install_logs(mock_context, cluster_id='test-id', tail=100)

        mock_ocm_client.get_install_logs.assert_called_once_with('test-id', tail=100)
