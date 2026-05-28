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

"""Tests for the ROSA config handler."""

import json
import pytest
from awslabs.rosa_mcp_server.rosa_config_handler import RosaConfigHandler
from unittest.mock import AsyncMock


class TestRosaListTuningConfigs:
    """Tests for rosa_list_tuning_configs."""

    @pytest.mark.asyncio
    async def test_given_cluster_when_list_tuning_configs_then_returns_data(
        self, mock_mcp, mock_ocm_client, mock_context
    ):
        """Test rosa_list_tuning_configs returns tuning configurations."""
        mock_ocm_client.request = AsyncMock(return_value={
            'items': [
                {'id': 'tuning-1', 'name': 'my-tuning', 'spec': {'sysctl': {}}},
            ],
        })
        handler = RosaConfigHandler(mock_mcp, mock_ocm_client, allow_write=False)
        result = await handler.rosa_list_tuning_configs(mock_context, cluster_id='test-id')

        mock_ocm_client.request.assert_called_once_with(
            'GET', '/api/clusters_mgmt/v1/clusters/test-id/tuning_configs'
        )
        assert isinstance(result, list)
        data = json.loads(result[0].text)
        assert 'items' in data
        assert data['items'][0]['name'] == 'my-tuning'


class TestRosaCreateTuningConfig:
    """Tests for rosa_create_tuning_config."""

    @pytest.mark.asyncio
    async def test_given_write_disabled_when_create_then_raises_value_error(
        self, mock_mcp, mock_ocm_client, mock_context
    ):
        """Test rosa_create_tuning_config requires allow_write."""
        handler = RosaConfigHandler(mock_mcp, mock_ocm_client, allow_write=False)

        with pytest.raises(ValueError, match='Write operations disabled'):
            await handler.rosa_create_tuning_config(
                mock_context,
                cluster_id='test-id',
                name='new-tuning',
                spec={'sysctl': {'vm.max_map_count': '262144'}},
            )

    @pytest.mark.asyncio
    async def test_given_write_enabled_when_create_then_builds_correct_body(
        self, mock_mcp, mock_ocm_client, mock_context
    ):
        """Test rosa_create_tuning_config creates configuration."""
        mock_ocm_client.request = AsyncMock(return_value={
            'id': 'tuning-new',
            'name': 'perf-tuning',
        })
        handler = RosaConfigHandler(mock_mcp, mock_ocm_client, allow_write=True)
        spec = {'sysctl': {'vm.max_map_count': '262144', 'net.core.somaxconn': '4096'}}
        result = await handler.rosa_create_tuning_config(
            mock_context,
            cluster_id='test-id',
            name='perf-tuning',
            spec=spec,
        )

        call_args = mock_ocm_client.request.call_args
        assert call_args[0][0] == 'POST'
        assert '/tuning_configs' in call_args[0][1]
        body = call_args[1]['body']
        assert body['name'] == 'perf-tuning'
        assert body['spec'] == spec
        data = json.loads(result[0].text)
        assert data['name'] == 'perf-tuning'


class TestRosaDeleteTuningConfig:
    """Tests for rosa_delete_tuning_config."""

    @pytest.mark.asyncio
    async def test_given_write_disabled_when_delete_then_raises_value_error(
        self, mock_mcp, mock_ocm_client, mock_context
    ):
        """Test rosa_delete_tuning_config requires allow_write."""
        handler = RosaConfigHandler(mock_mcp, mock_ocm_client, allow_write=False)

        with pytest.raises(ValueError, match='Write operations disabled'):
            await handler.rosa_delete_tuning_config(
                mock_context, cluster_id='test-id', config_id='tuning-1'
            )

    @pytest.mark.asyncio
    async def test_given_write_enabled_when_delete_then_calls_ocm_correctly(
        self, mock_mcp, mock_ocm_client, mock_context
    ):
        """Test rosa_delete_tuning_config calls OCM correctly."""
        mock_ocm_client.request = AsyncMock(return_value=None)
        handler = RosaConfigHandler(mock_mcp, mock_ocm_client, allow_write=True)
        result = await handler.rosa_delete_tuning_config(
            mock_context, cluster_id='test-id', config_id='tuning-1'
        )

        mock_ocm_client.request.assert_called_once_with(
            'DELETE', '/api/clusters_mgmt/v1/clusters/test-id/tuning_configs/tuning-1'
        )
        data = json.loads(result[0].text)
        assert data['status'] == 'tuning_config_deleted'
        assert data['config_id'] == 'tuning-1'


class TestRosaGetKubeletConfig:
    """Tests for rosa_get_kubelet_config."""

    @pytest.mark.asyncio
    async def test_given_cluster_when_get_kubelet_config_then_returns_data(
        self, mock_mcp, mock_ocm_client, mock_context
    ):
        """Test rosa_get_kubelet_config returns kubelet configuration."""
        mock_ocm_client.request = AsyncMock(return_value={
            'pod_pids_limit': 4096,
        })
        handler = RosaConfigHandler(mock_mcp, mock_ocm_client, allow_write=False)
        result = await handler.rosa_get_kubelet_config(mock_context, cluster_id='test-id')

        mock_ocm_client.request.assert_called_once_with(
            'GET', '/api/clusters_mgmt/v1/clusters/test-id/kubelet_config'
        )
        data = json.loads(result[0].text)
        assert data['pod_pids_limit'] == 4096


class TestRosaUpdateKubeletConfig:
    """Tests for rosa_update_kubelet_config."""

    @pytest.mark.asyncio
    async def test_given_write_disabled_when_update_then_raises_value_error(
        self, mock_mcp, mock_ocm_client, mock_context
    ):
        """Test rosa_update_kubelet_config requires allow_write."""
        handler = RosaConfigHandler(mock_mcp, mock_ocm_client, allow_write=False)

        with pytest.raises(ValueError, match='Write operations disabled'):
            await handler.rosa_update_kubelet_config(
                mock_context, cluster_id='test-id', pod_pids_limit=8192
            )

    @pytest.mark.asyncio
    async def test_given_write_enabled_when_update_then_patches_config(
        self, mock_mcp, mock_ocm_client, mock_context
    ):
        """Test rosa_update_kubelet_config patches kubelet configuration."""
        mock_ocm_client.request = AsyncMock(return_value={
            'pod_pids_limit': 8192,
        })
        handler = RosaConfigHandler(mock_mcp, mock_ocm_client, allow_write=True)
        result = await handler.rosa_update_kubelet_config(
            mock_context, cluster_id='test-id', pod_pids_limit=8192
        )

        call_args = mock_ocm_client.request.call_args
        assert call_args[0][0] == 'PATCH'
        assert '/kubelet_config' in call_args[0][1]
        body = call_args[1]['body']
        assert body['pod_pids_limit'] == 8192
        data = json.loads(result[0].text)
        assert data['pod_pids_limit'] == 8192
