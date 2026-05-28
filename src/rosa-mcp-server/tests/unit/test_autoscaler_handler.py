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

"""Tests for the ROSA autoscaler handler."""

import json
import pytest
from awslabs.rosa_mcp_server.rosa_autoscaler_handler import RosaAutoscalerHandler
from unittest.mock import AsyncMock


class TestRosaGetAutoscaler:
    """Tests for rosa_get_autoscaler."""

    @pytest.mark.asyncio
    async def test_given_cluster_when_get_autoscaler_then_returns_config(
        self, mock_mcp, mock_ocm_client, mock_context
    ):
        """Test rosa_get_autoscaler returns autoscaler configuration."""
        mock_ocm_client.request = AsyncMock(return_value={
            'resource_limits': {'min_replicas': 2, 'max_replicas': 10},
            'scale_down': {'enabled': True, 'delay_after_add': '10m'},
        })
        handler = RosaAutoscalerHandler(mock_mcp, mock_ocm_client, allow_write=False)
        result = await handler.rosa_get_autoscaler(mock_context, cluster_id='test-id')

        mock_ocm_client.request.assert_called_once_with(
            'GET', '/api/clusters_mgmt/v1/clusters/test-id/autoscaler'
        )
        assert isinstance(result, list)
        data = json.loads(result[0].text)
        assert data['resource_limits']['min_replicas'] == 2
        assert data['resource_limits']['max_replicas'] == 10


class TestRosaCreateAutoscaler:
    """Tests for rosa_create_autoscaler."""

    @pytest.mark.asyncio
    async def test_given_write_disabled_when_create_then_raises_value_error(
        self, mock_mcp, mock_ocm_client, mock_context
    ):
        """Test rosa_create_autoscaler requires allow_write."""
        handler = RosaAutoscalerHandler(mock_mcp, mock_ocm_client, allow_write=False)

        with pytest.raises(ValueError, match='Write operations disabled'):
            await handler.rosa_create_autoscaler(
                mock_context, cluster_id='test-id', min_replicas=2, max_replicas=10
            )

    @pytest.mark.asyncio
    async def test_given_all_params_when_create_then_builds_correct_body(
        self, mock_mcp, mock_ocm_client, mock_context
    ):
        """Test rosa_create_autoscaler with all parameters."""
        mock_ocm_client.request = AsyncMock(return_value={
            'resource_limits': {'min_replicas': 2, 'max_replicas': 10},
        })
        handler = RosaAutoscalerHandler(mock_mcp, mock_ocm_client, allow_write=True)
        await handler.rosa_create_autoscaler(
            mock_context,
            cluster_id='test-id',
            min_replicas=2,
            max_replicas=10,
            scale_down_enabled=True,
            scale_down_delay_after_add='15m',
            scale_down_unneeded_time='5m',
            scale_down_utilization_threshold='0.6',
            max_pod_grace_period=300,
            balance_similar_node_groups=True,
            skip_nodes_with_local_storage=False,
        )

        mock_ocm_client.request.assert_called_once()
        call_args = mock_ocm_client.request.call_args
        assert call_args[0][0] == 'POST'
        assert '/clusters/test-id/autoscaler' in call_args[0][1]
        body = call_args[1]['body']
        assert body['resource_limits'] == {'min_replicas': 2, 'max_replicas': 10}
        assert body['scale_down']['enabled'] is True
        assert body['scale_down']['delay_after_add'] == '15m'
        assert body['scale_down']['unneeded_time'] == '5m'
        assert body['scale_down']['utilization_threshold'] == '0.6'
        assert body['max_pod_grace_period'] == 300
        assert body['balance_similar_node_groups'] is True
        assert body['skip_nodes_with_local_storage'] is False


class TestRosaUpdateAutoscaler:
    """Tests for rosa_update_autoscaler."""

    @pytest.mark.asyncio
    async def test_given_write_disabled_when_update_then_raises_value_error(
        self, mock_mcp, mock_ocm_client, mock_context
    ):
        """Test rosa_update_autoscaler requires allow_write."""
        handler = RosaAutoscalerHandler(mock_mcp, mock_ocm_client, allow_write=False)

        with pytest.raises(ValueError, match='Write operations disabled'):
            await handler.rosa_update_autoscaler(
                mock_context, cluster_id='test-id', min_replicas=3
            )

    @pytest.mark.asyncio
    async def test_given_partial_params_when_update_then_includes_only_provided(
        self, mock_mcp, mock_ocm_client, mock_context
    ):
        """Test rosa_update_autoscaler with partial params."""
        mock_ocm_client.request = AsyncMock(return_value={
            'resource_limits': {'min_replicas': 3, 'max_replicas': 15},
        })
        handler = RosaAutoscalerHandler(mock_mcp, mock_ocm_client, allow_write=True)
        await handler.rosa_update_autoscaler(
            mock_context,
            cluster_id='test-id',
            min_replicas=3,
            max_replicas=15,
            scale_down_enabled=False,
        )

        call_args = mock_ocm_client.request.call_args
        assert call_args[0][0] == 'PATCH'
        body = call_args[1]['body']
        assert body['resource_limits'] == {'min_replicas': 3, 'max_replicas': 15}
        assert body['scale_down'] == {'enabled': False}
        assert 'max_pod_grace_period' not in body


class TestRosaDeleteAutoscaler:
    """Tests for rosa_delete_autoscaler."""

    @pytest.mark.asyncio
    async def test_given_write_disabled_when_delete_then_raises_value_error(
        self, mock_mcp, mock_ocm_client, mock_context
    ):
        """Test rosa_delete_autoscaler requires allow_write."""
        handler = RosaAutoscalerHandler(mock_mcp, mock_ocm_client, allow_write=False)

        with pytest.raises(ValueError, match='Write operations disabled'):
            await handler.rosa_delete_autoscaler(mock_context, cluster_id='test-id')

    @pytest.mark.asyncio
    async def test_given_write_enabled_when_delete_then_calls_ocm_correctly(
        self, mock_mcp, mock_ocm_client, mock_context
    ):
        """Test rosa_delete_autoscaler calls OCM correctly."""
        mock_ocm_client.request = AsyncMock(return_value=None)
        handler = RosaAutoscalerHandler(mock_mcp, mock_ocm_client, allow_write=True)
        result = await handler.rosa_delete_autoscaler(mock_context, cluster_id='test-id')

        mock_ocm_client.request.assert_called_once_with(
            'DELETE', '/api/clusters_mgmt/v1/clusters/test-id/autoscaler'
        )
        data = json.loads(result[0].text)
        assert data['status'] == 'autoscaler_deleted'
        assert data['cluster_id'] == 'test-id'
