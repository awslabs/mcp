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

"""Tests for the ROSA advanced handler."""

import json
import pytest
from awslabs.rosa_mcp_server.rosa_advanced_handler import RosaAdvancedHandler
from unittest.mock import AsyncMock


class TestRosaHibernateCluster:
    """Tests for rosa_hibernate_cluster."""

    @pytest.mark.asyncio
    async def test_given_write_disabled_when_hibernate_then_raises_value_error(
        self, mock_mcp, mock_ocm_client, mock_context
    ):
        """Test rosa_hibernate_cluster requires allow_write."""
        handler = RosaAdvancedHandler(mock_mcp, mock_ocm_client, allow_write=False)

        with pytest.raises(ValueError, match='Write operations disabled'):
            await handler.rosa_hibernate_cluster(mock_context, cluster_id='test-id')

    @pytest.mark.asyncio
    async def test_given_write_enabled_when_hibernate_then_calls_ocm(
        self, mock_mcp, mock_ocm_client, mock_context
    ):
        """Test rosa_hibernate_cluster calls OCM correctly."""
        mock_ocm_client.request = AsyncMock(return_value=None)
        handler = RosaAdvancedHandler(mock_mcp, mock_ocm_client, allow_write=True)
        result = await handler.rosa_hibernate_cluster(mock_context, cluster_id='test-id')

        mock_ocm_client.request.assert_called_once_with(
            'POST', '/api/clusters_mgmt/v1/clusters/test-id/hibernate'
        )
        data = json.loads(result[0].text)
        assert data['status'] == 'hibernation_initiated'
        assert data['cluster_id'] == 'test-id'


class TestRosaResumeCluster:
    """Tests for rosa_resume_cluster."""

    @pytest.mark.asyncio
    async def test_given_write_disabled_when_resume_then_raises_value_error(
        self, mock_mcp, mock_ocm_client, mock_context
    ):
        """Test rosa_resume_cluster requires allow_write."""
        handler = RosaAdvancedHandler(mock_mcp, mock_ocm_client, allow_write=False)

        with pytest.raises(ValueError, match='Write operations disabled'):
            await handler.rosa_resume_cluster(mock_context, cluster_id='test-id')

    @pytest.mark.asyncio
    async def test_given_write_enabled_when_resume_then_calls_ocm(
        self, mock_mcp, mock_ocm_client, mock_context
    ):
        """Test rosa_resume_cluster calls OCM correctly."""
        mock_ocm_client.request = AsyncMock(return_value=None)
        handler = RosaAdvancedHandler(mock_mcp, mock_ocm_client, allow_write=True)
        result = await handler.rosa_resume_cluster(mock_context, cluster_id='test-id')

        mock_ocm_client.request.assert_called_once_with(
            'POST', '/api/clusters_mgmt/v1/clusters/test-id/resume'
        )
        data = json.loads(result[0].text)
        assert data['status'] == 'resume_initiated'


class TestRosaGetClusterStatus:
    """Tests for rosa_get_cluster_status."""

    @pytest.mark.asyncio
    async def test_given_cluster_when_get_status_then_returns_status(
        self, mock_mcp, mock_ocm_client, mock_context
    ):
        """Test rosa_get_cluster_status returns cluster status."""
        mock_ocm_client.request = AsyncMock(return_value={
            'state': 'ready',
            'dns_ready': True,
            'oidc_ready': True,
            'provision_error_message': '',
        })
        handler = RosaAdvancedHandler(mock_mcp, mock_ocm_client, allow_write=False)
        result = await handler.rosa_get_cluster_status(mock_context, cluster_id='test-id')

        mock_ocm_client.request.assert_called_once_with(
            'GET', '/api/clusters_mgmt/v1/clusters/test-id/status'
        )
        data = json.loads(result[0].text)
        assert data['state'] == 'ready'
        assert data['dns_ready'] is True


class TestRosaGetClusterMetrics:
    """Tests for rosa_get_cluster_metrics."""

    @pytest.mark.asyncio
    async def test_given_alerts_metric_when_get_then_returns_alerts(
        self, mock_mcp, mock_ocm_client, mock_context
    ):
        """Test rosa_get_cluster_metrics with alerts metric type."""
        mock_ocm_client.request = AsyncMock(return_value={
            'alerts': [{'name': 'HighCPU', 'severity': 'warning'}],
        })
        handler = RosaAdvancedHandler(mock_mcp, mock_ocm_client, allow_write=False)
        result = await handler.rosa_get_cluster_metrics(
            mock_context, cluster_id='test-id', metric='alerts'
        )

        mock_ocm_client.request.assert_called_once_with(
            'GET', '/api/clusters_mgmt/v1/clusters/test-id/metric_queries/alerts'
        )
        data = json.loads(result[0].text)
        assert 'alerts' in data

    @pytest.mark.asyncio
    async def test_given_nodes_metric_when_get_then_returns_nodes(
        self, mock_mcp, mock_ocm_client, mock_context
    ):
        """Test rosa_get_cluster_metrics with nodes metric type."""
        mock_ocm_client.request = AsyncMock(return_value={
            'nodes': [{'name': 'worker-1', 'status': 'Ready'}],
        })
        handler = RosaAdvancedHandler(mock_mcp, mock_ocm_client, allow_write=False)
        await handler.rosa_get_cluster_metrics(
            mock_context, cluster_id='test-id', metric='nodes'
        )

        call_args = mock_ocm_client.request.call_args
        assert '/metric_queries/nodes' in call_args[0][1]

    @pytest.mark.asyncio
    async def test_given_cluster_operators_metric_when_get_then_returns_data(
        self, mock_mcp, mock_ocm_client, mock_context
    ):
        """Test rosa_get_cluster_metrics with cluster_operators metric."""
        mock_ocm_client.request = AsyncMock(return_value={
            'operators': [{'name': 'dns', 'available': True}],
        })
        handler = RosaAdvancedHandler(mock_mcp, mock_ocm_client, allow_write=False)
        await handler.rosa_get_cluster_metrics(
            mock_context, cluster_id='test-id', metric='cluster_operators'
        )

        call_args = mock_ocm_client.request.call_args
        assert '/metric_queries/cluster_operators' in call_args[0][1]

    @pytest.mark.asyncio
    async def test_given_invalid_metric_when_get_then_raises_value_error(
        self, mock_mcp, mock_ocm_client, mock_context
    ):
        """Test rosa_get_cluster_metrics rejects invalid metric."""
        handler = RosaAdvancedHandler(mock_mcp, mock_ocm_client, allow_write=False)

        with pytest.raises(ValueError, match="Invalid metric"):
            await handler.rosa_get_cluster_metrics(
                mock_context, cluster_id='test-id', metric='invalid_metric'
            )


class TestRosaBreakGlassCredentials:
    """Tests for break glass credential operations."""

    @pytest.mark.asyncio
    async def test_given_cluster_when_list_break_glass_then_returns_credentials(
        self, mock_mcp, mock_ocm_client, mock_context
    ):
        """Test rosa_list_break_glass_credentials returns credentials."""
        mock_ocm_client.request = AsyncMock(return_value={
            'items': [
                {'id': 'bg-1', 'status': 'active', 'ttl': '24h'},
            ],
        })
        handler = RosaAdvancedHandler(mock_mcp, mock_ocm_client, allow_write=False)
        result = await handler.rosa_list_break_glass_credentials(
            mock_context, cluster_id='test-id'
        )

        mock_ocm_client.request.assert_called_once_with(
            'GET', '/api/clusters_mgmt/v1/clusters/test-id/break_glass_credentials'
        )
        data = json.loads(result[0].text)
        assert len(data['items']) == 1

    @pytest.mark.asyncio
    async def test_given_write_disabled_when_create_break_glass_then_raises(
        self, mock_mcp, mock_ocm_client, mock_context
    ):
        """Test rosa_create_break_glass_credential requires allow_write."""
        handler = RosaAdvancedHandler(mock_mcp, mock_ocm_client, allow_write=False)

        with pytest.raises(ValueError, match='Write operations disabled'):
            await handler.rosa_create_break_glass_credential(
                mock_context, cluster_id='test-id'
            )

    @pytest.mark.asyncio
    async def test_given_write_enabled_when_create_break_glass_then_calls_ocm(
        self, mock_mcp, mock_ocm_client, mock_context
    ):
        """Test rosa_create_break_glass_credential creates credential."""
        mock_ocm_client.request = AsyncMock(return_value={
            'id': 'bg-new',
            'status': 'created',
            'ttl': '24h',
        })
        handler = RosaAdvancedHandler(mock_mcp, mock_ocm_client, allow_write=True)
        await handler.rosa_create_break_glass_credential(
            mock_context, cluster_id='test-id', ttl='12h'
        )

        call_args = mock_ocm_client.request.call_args
        assert call_args[0][0] == 'POST'
        assert '/break_glass_credentials' in call_args[0][1]
        assert call_args[1]['body'] == {'ttl': '12h'}


class TestRosaDeleteProtection:
    """Tests for delete protection operations."""

    @pytest.mark.asyncio
    async def test_given_cluster_when_get_delete_protection_then_returns_status(
        self, mock_mcp, mock_ocm_client, mock_context
    ):
        """Test rosa_get_delete_protection returns protection status."""
        mock_ocm_client.request = AsyncMock(return_value={
            'id': 'test-id',
            'delete_protection': {'enabled': True},
        })
        handler = RosaAdvancedHandler(mock_mcp, mock_ocm_client, allow_write=False)
        result = await handler.rosa_get_delete_protection(mock_context, cluster_id='test-id')

        data = json.loads(result[0].text)
        assert data['cluster_id'] == 'test-id'
        assert data['delete_protection_enabled'] is True

    @pytest.mark.asyncio
    async def test_given_write_disabled_when_set_protection_then_raises(
        self, mock_mcp, mock_ocm_client, mock_context
    ):
        """Test rosa_set_delete_protection requires allow_write."""
        handler = RosaAdvancedHandler(mock_mcp, mock_ocm_client, allow_write=False)

        with pytest.raises(ValueError, match='Write operations disabled'):
            await handler.rosa_set_delete_protection(
                mock_context, cluster_id='test-id', enabled=True
            )

    @pytest.mark.asyncio
    async def test_given_write_enabled_when_set_protection_then_patches_cluster(
        self, mock_mcp, mock_ocm_client, mock_context
    ):
        """Test rosa_set_delete_protection patches cluster."""
        mock_ocm_client.request = AsyncMock(return_value=None)
        handler = RosaAdvancedHandler(mock_mcp, mock_ocm_client, allow_write=True)
        result = await handler.rosa_set_delete_protection(
            mock_context, cluster_id='test-id', enabled=True
        )

        call_args = mock_ocm_client.request.call_args
        assert call_args[0][0] == 'PATCH'
        assert '/clusters/test-id' in call_args[0][1]
        assert call_args[1]['body'] == {'delete_protection': {'enabled': True}}
        data = json.loads(result[0].text)
        assert data['enabled'] is True


class TestRosaListMachineTypes:
    """Tests for rosa_list_machine_types."""

    @pytest.mark.asyncio
    async def test_given_no_region_when_list_machine_types_then_returns_all(
        self, mock_mcp, mock_ocm_client, mock_context
    ):
        """Test rosa_list_machine_types returns all machine types."""
        mock_ocm_client.request = AsyncMock(return_value={
            'items': [
                {'id': 'm5.xlarge', 'cpu': {'value': 4}, 'memory': {'value': 16}},
                {'id': 'm5.2xlarge', 'cpu': {'value': 8}, 'memory': {'value': 32}},
            ],
        })
        handler = RosaAdvancedHandler(mock_mcp, mock_ocm_client, allow_write=False)
        result = await handler.rosa_list_machine_types(mock_context)

        mock_ocm_client.request.assert_called_once()
        data = json.loads(result[0].text)
        assert len(data['items']) == 2

    @pytest.mark.asyncio
    async def test_given_region_when_list_machine_types_then_includes_search(
        self, mock_mcp, mock_ocm_client, mock_context
    ):
        """Test rosa_list_machine_types with region filter."""
        mock_ocm_client.request = AsyncMock(return_value={'items': []})
        handler = RosaAdvancedHandler(mock_mcp, mock_ocm_client, allow_write=False)
        await handler.rosa_list_machine_types(mock_context, region='us-east-1')

        call_args = mock_ocm_client.request.call_args
        path = call_args[0][1]
        assert 'machine_types' in path
        assert 'search=' in path
