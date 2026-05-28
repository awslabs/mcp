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

"""Tests for the ROSA addon handler."""

import json
import pytest
from awslabs.rosa_mcp_server.rosa_addon_handler import RosaAddonHandler
from unittest.mock import AsyncMock


class TestRosaListAvailableAddons:
    """Tests for rosa_list_available_addons."""

    @pytest.mark.asyncio
    async def test_given_catalog_when_list_then_returns_addons(
        self, mock_mcp, mock_ocm_client, mock_context
    ):
        """Test rosa_list_available_addons returns addon catalog."""
        mock_ocm_client.request = AsyncMock(return_value={
            'items': [
                {'id': 'cluster-logging-operator', 'name': 'Cluster Logging Operator'},
                {'id': 'managed-api-service', 'name': 'Managed API Service'},
            ],
        })
        handler = RosaAddonHandler(mock_mcp, mock_ocm_client, allow_write=False)
        result = await handler.rosa_list_available_addons(mock_context)

        mock_ocm_client.request.assert_called_once_with(
            'GET', '/api/clusters_mgmt/v1/addons'
        )
        assert isinstance(result, list)
        data = json.loads(result[0].text)
        assert 'items' in data
        assert len(data['items']) == 2


class TestRosaListClusterAddons:
    """Tests for rosa_list_cluster_addons."""

    @pytest.mark.asyncio
    async def test_given_cluster_when_list_addons_then_returns_installed(
        self, mock_mcp, mock_ocm_client, mock_context
    ):
        """Test rosa_list_cluster_addons returns installed addons."""
        mock_ocm_client.request = AsyncMock(return_value={
            'items': [
                {'id': 'cluster-logging-operator', 'state': 'ready'},
            ],
        })
        handler = RosaAddonHandler(mock_mcp, mock_ocm_client, allow_write=False)
        result = await handler.rosa_list_cluster_addons(mock_context, cluster_id='test-id')

        mock_ocm_client.request.assert_called_once_with(
            'GET', '/api/clusters_mgmt/v1/clusters/test-id/addons'
        )
        data = json.loads(result[0].text)
        assert data['items'][0]['state'] == 'ready'


class TestRosaInstallAddon:
    """Tests for rosa_install_addon."""

    @pytest.mark.asyncio
    async def test_given_write_disabled_when_install_then_raises_value_error(
        self, mock_mcp, mock_ocm_client, mock_context
    ):
        """Test rosa_install_addon requires allow_write."""
        handler = RosaAddonHandler(mock_mcp, mock_ocm_client, allow_write=False)

        with pytest.raises(ValueError, match='Write operations disabled'):
            await handler.rosa_install_addon(
                mock_context, cluster_id='test-id', addon_id='addon-1'
            )

    @pytest.mark.asyncio
    async def test_given_addon_with_params_when_install_then_builds_correct_body(
        self, mock_mcp, mock_ocm_client, mock_context
    ):
        """Test rosa_install_addon with parameters."""
        mock_ocm_client.request = AsyncMock(return_value={
            'id': 'addon-1',
            'state': 'installing',
        })
        handler = RosaAddonHandler(mock_mcp, mock_ocm_client, allow_write=True)
        params = {'notification-email': 'admin@example.com', 'retention': '7d'}
        await handler.rosa_install_addon(
            mock_context,
            cluster_id='test-id',
            addon_id='addon-1',
            parameters=params,
        )

        call_args = mock_ocm_client.request.call_args
        assert call_args[0][0] == 'POST'
        assert '/clusters/test-id/addons' in call_args[0][1]
        body = call_args[1]['body']
        assert body['addon'] == {'id': 'addon-1'}
        assert body['parameters']['items'] == [
            {'id': 'notification-email', 'value': 'admin@example.com'},
            {'id': 'retention', 'value': '7d'},
        ]

    @pytest.mark.asyncio
    async def test_given_addon_without_params_when_install_then_no_parameters_key(
        self, mock_mcp, mock_ocm_client, mock_context
    ):
        """Test rosa_install_addon without parameters omits parameters field."""
        mock_ocm_client.request = AsyncMock(return_value={
            'id': 'addon-1',
            'state': 'installing',
        })
        handler = RosaAddonHandler(mock_mcp, mock_ocm_client, allow_write=True)
        await handler.rosa_install_addon(
            mock_context, cluster_id='test-id', addon_id='addon-1'
        )

        body = mock_ocm_client.request.call_args[1]['body']
        assert 'parameters' not in body


class TestRosaUninstallAddon:
    """Tests for rosa_uninstall_addon."""

    @pytest.mark.asyncio
    async def test_given_write_disabled_when_uninstall_then_raises_value_error(
        self, mock_mcp, mock_ocm_client, mock_context
    ):
        """Test rosa_uninstall_addon requires allow_write."""
        handler = RosaAddonHandler(mock_mcp, mock_ocm_client, allow_write=False)

        with pytest.raises(ValueError, match='Write operations disabled'):
            await handler.rosa_uninstall_addon(
                mock_context, cluster_id='test-id', addon_id='addon-1'
            )

    @pytest.mark.asyncio
    async def test_given_write_enabled_when_uninstall_then_calls_ocm_correctly(
        self, mock_mcp, mock_ocm_client, mock_context
    ):
        """Test rosa_uninstall_addon calls OCM correctly."""
        mock_ocm_client.request = AsyncMock(return_value=None)
        handler = RosaAddonHandler(mock_mcp, mock_ocm_client, allow_write=True)
        result = await handler.rosa_uninstall_addon(
            mock_context, cluster_id='test-id', addon_id='addon-1'
        )

        mock_ocm_client.request.assert_called_once_with(
            'DELETE', '/api/clusters_mgmt/v1/clusters/test-id/addons/addon-1'
        )
        data = json.loads(result[0].text)
        assert data['status'] == 'addon_uninstalled'
        assert data['addon_id'] == 'addon-1'
        assert data['cluster_id'] == 'test-id'
