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

"""Tests for the ROSA networking handler."""

import json
import pytest
from awslabs.rosa_mcp_server.rosa_networking_handler import RosaNetworkingHandler


class TestRosaListIngresses:
    """Tests for rosa_list_ingresses."""

    @pytest.mark.asyncio
    async def test_given_cluster_when_list_ingresses_then_returns_data(
        self, mock_mcp, mock_ocm_client, mock_context
    ):
        """Test rosa_list_ingresses returns ingress list."""
        handler = RosaNetworkingHandler(mock_mcp, mock_ocm_client, allow_write=False)
        result = await handler.rosa_list_ingresses(mock_context, cluster_id='test-id')

        mock_ocm_client.list_ingresses.assert_called_once_with('test-id')
        assert isinstance(result, list)
        data = json.loads(result[0].text)
        assert 'items' in data
        assert len(data['items']) == 1
        assert data['items'][0]['id'] == 'ingress-default'


class TestRosaCreateIngress:
    """Tests for rosa_create_ingress."""

    @pytest.mark.asyncio
    async def test_given_write_disabled_when_create_then_raises_value_error(
        self, mock_mcp, mock_ocm_client, mock_context
    ):
        """Test rosa_create_ingress requires allow_write."""
        handler = RosaNetworkingHandler(mock_mcp, mock_ocm_client, allow_write=False)

        with pytest.raises(ValueError, match='Write operations disabled'):
            await handler.rosa_create_ingress(mock_context, cluster_id='test-id')

    @pytest.mark.asyncio
    async def test_given_nlb_type_when_create_then_sets_lb_type(
        self, mock_mcp, mock_ocm_client, mock_context
    ):
        """Test rosa_create_ingress with NLB type."""
        handler = RosaNetworkingHandler(mock_mcp, mock_ocm_client, allow_write=True)
        await handler.rosa_create_ingress(
            mock_context, cluster_id='test-id', lb_type='nlb'
        )

        mock_ocm_client.create_ingress.assert_called_once()
        call_args = mock_ocm_client.create_ingress.call_args
        assert call_args[0][0] == 'test-id'
        body = call_args[0][1]
        assert body['load_balancer_type'] == 'nlb'
        assert body['listening'] == 'external'

    @pytest.mark.asyncio
    async def test_given_route_selectors_when_create_then_includes_selectors(
        self, mock_mcp, mock_ocm_client, mock_context
    ):
        """Test rosa_create_ingress with route_selectors."""
        handler = RosaNetworkingHandler(mock_mcp, mock_ocm_client, allow_write=True)
        route_selectors = {'app': 'frontend', 'tier': 'web'}
        await handler.rosa_create_ingress(
            mock_context,
            cluster_id='test-id',
            route_selectors=route_selectors,
        )

        body = mock_ocm_client.create_ingress.call_args[0][1]
        assert body['route_selectors'] == route_selectors

    @pytest.mark.asyncio
    async def test_given_private_when_create_then_sets_internal_listening(
        self, mock_mcp, mock_ocm_client, mock_context
    ):
        """Test rosa_create_ingress with private=True sets internal listening."""
        handler = RosaNetworkingHandler(mock_mcp, mock_ocm_client, allow_write=True)
        await handler.rosa_create_ingress(
            mock_context, cluster_id='test-id', private=True
        )

        body = mock_ocm_client.create_ingress.call_args[0][1]
        assert body['listening'] == 'internal'


class TestRosaUpdateIngress:
    """Tests for rosa_update_ingress."""

    @pytest.mark.asyncio
    async def test_given_write_disabled_when_update_then_raises_value_error(
        self, mock_mcp, mock_ocm_client, mock_context
    ):
        """Test rosa_update_ingress requires allow_write."""
        handler = RosaNetworkingHandler(mock_mcp, mock_ocm_client, allow_write=False)

        with pytest.raises(ValueError, match='Write operations disabled'):
            await handler.rosa_update_ingress(
                mock_context, cluster_id='test-id', ingress_id='ingress-1'
            )

    @pytest.mark.asyncio
    async def test_given_new_params_when_update_then_sends_correct_body(
        self, mock_mcp, mock_ocm_client, mock_context
    ):
        """Test rosa_update_ingress sends correct update body."""
        handler = RosaNetworkingHandler(mock_mcp, mock_ocm_client, allow_write=True)
        await handler.rosa_update_ingress(
            mock_context,
            cluster_id='test-id',
            ingress_id='ingress-default',
            private=True,
            lb_type='nlb',
        )

        mock_ocm_client.update_ingress.assert_called_once()
        call_args = mock_ocm_client.update_ingress.call_args
        assert call_args[0][0] == 'test-id'
        assert call_args[0][1] == 'ingress-default'
        body = call_args[0][2]
        assert body['listening'] == 'internal'
        assert body['load_balancer_type'] == 'nlb'


class TestRosaDeleteIngress:
    """Tests for rosa_delete_ingress."""

    @pytest.mark.asyncio
    async def test_given_write_disabled_when_delete_then_raises_value_error(
        self, mock_mcp, mock_ocm_client, mock_context
    ):
        """Test rosa_delete_ingress requires allow_write."""
        handler = RosaNetworkingHandler(mock_mcp, mock_ocm_client, allow_write=False)

        with pytest.raises(ValueError, match='Write operations disabled'):
            await handler.rosa_delete_ingress(
                mock_context, cluster_id='test-id', ingress_id='ingress-1'
            )

    @pytest.mark.asyncio
    async def test_given_write_enabled_when_delete_then_calls_ocm_correctly(
        self, mock_mcp, mock_ocm_client, mock_context
    ):
        """Test rosa_delete_ingress calls OCM correctly."""
        handler = RosaNetworkingHandler(mock_mcp, mock_ocm_client, allow_write=True)
        result = await handler.rosa_delete_ingress(
            mock_context, cluster_id='test-id', ingress_id='ingress-1'
        )

        mock_ocm_client.delete_ingress.assert_called_once_with('test-id', 'ingress-1')
        data = json.loads(result[0].text)
        assert data['status'] == 'deleted'
        assert data['ingress_id'] == 'ingress-1'
        assert data['http_status'] == 204
