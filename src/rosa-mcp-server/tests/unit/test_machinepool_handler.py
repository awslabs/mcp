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

"""Tests for the ROSA machine pool handler."""

import json
import pytest
from awslabs.rosa_mcp_server.rosa_machinepool_handler import RosaMachinePoolHandler


class TestRosaListMachinepools:
    """Tests for rosa_list_machinepools."""

    @pytest.mark.asyncio
    async def test_given_hcp_cluster_when_list_then_uses_node_pools(
        self, mock_mcp, mock_ocm_client_hcp, mock_context
    ):
        """Test rosa_list_machinepools detects HCP and uses node_pools."""
        handler = RosaMachinePoolHandler(mock_mcp, mock_ocm_client_hcp, allow_write=False)
        result = await handler.rosa_list_machinepools(mock_context, cluster_id='hcp-id')

        mock_ocm_client_hcp.get_cluster.assert_called_once_with('hcp-id')
        mock_ocm_client_hcp.list_node_pools.assert_called_once_with('hcp-id')
        data = json.loads(result[0].text)
        assert 'items' in data
        assert data['items'][0]['aws_node_pool']['instance_type'] == 'm5.xlarge'

    @pytest.mark.asyncio
    async def test_given_classic_cluster_when_list_then_uses_machine_pools(
        self, mock_mcp, mock_ocm_client, mock_context
    ):
        """Test rosa_list_machinepools uses machine_pools for Classic."""
        handler = RosaMachinePoolHandler(mock_mcp, mock_ocm_client, allow_write=False)
        result = await handler.rosa_list_machinepools(mock_context, cluster_id='test-id')

        mock_ocm_client.list_machine_pools.assert_called_once_with('test-id')
        data = json.loads(result[0].text)
        assert 'items' in data


class TestRosaCreateMachinepool:
    """Tests for rosa_create_machinepool."""

    @pytest.mark.asyncio
    async def test_given_write_disabled_when_create_then_raises_value_error(
        self, mock_mcp, mock_ocm_client, mock_context
    ):
        """Test rosa_create_machinepool requires allow_write."""
        handler = RosaMachinePoolHandler(mock_mcp, mock_ocm_client, allow_write=False)

        with pytest.raises(ValueError, match='Write operations disabled'):
            await handler.rosa_create_machinepool(
                mock_context, cluster_id='test-id', name='pool-1'
            )

    @pytest.mark.asyncio
    async def test_given_fixed_replicas_when_create_then_sets_replicas(
        self, mock_mcp, mock_ocm_client, mock_context
    ):
        """Test rosa_create_machinepool with fixed replicas."""
        handler = RosaMachinePoolHandler(mock_mcp, mock_ocm_client, allow_write=True)
        await handler.rosa_create_machinepool(
            mock_context,
            cluster_id='test-id',
            name='pool-1',
            instance_type='m5.2xlarge',
            replicas=3,
        )

        mock_ocm_client.create_machine_pool.assert_called_once()
        body = mock_ocm_client.create_machine_pool.call_args[0][1]
        assert body['id'] == 'pool-1'
        assert body['instance_type'] == 'm5.2xlarge'
        assert body['replicas'] == 3
        assert 'autoscaling' not in body

    @pytest.mark.asyncio
    async def test_given_autoscaling_when_create_then_sets_min_max(
        self, mock_mcp, mock_ocm_client, mock_context
    ):
        """Test rosa_create_machinepool with autoscaling (min/max)."""
        handler = RosaMachinePoolHandler(mock_mcp, mock_ocm_client, allow_write=True)
        await handler.rosa_create_machinepool(
            mock_context,
            cluster_id='test-id',
            name='pool-auto',
            min_replicas=2,
            max_replicas=10,
        )

        body = mock_ocm_client.create_machine_pool.call_args[0][1]
        assert body['autoscaling'] == {'min_replicas': 2, 'max_replicas': 10}
        assert 'replicas' not in body

    @pytest.mark.asyncio
    async def test_given_labels_and_taints_when_create_then_includes_them(
        self, mock_mcp, mock_ocm_client, mock_context
    ):
        """Test rosa_create_machinepool with labels and taints."""
        handler = RosaMachinePoolHandler(mock_mcp, mock_ocm_client, allow_write=True)
        labels = {'tier': 'gpu', 'team': 'ml'}
        taints = [{'key': 'gpu', 'value': 'true', 'effect': 'NoSchedule'}]

        await handler.rosa_create_machinepool(
            mock_context,
            cluster_id='test-id',
            name='gpu-pool',
            labels=labels,
            taints=taints,
            replicas=2,
        )

        body = mock_ocm_client.create_machine_pool.call_args[0][1]
        assert body['labels'] == labels
        assert body['taints'] == taints

    @pytest.mark.asyncio
    async def test_given_spot_instances_when_create_then_sets_spot_config(
        self, mock_mcp, mock_ocm_client, mock_context
    ):
        """Test rosa_create_machinepool with spot instances."""
        handler = RosaMachinePoolHandler(mock_mcp, mock_ocm_client, allow_write=True)
        await handler.rosa_create_machinepool(
            mock_context,
            cluster_id='test-id',
            name='spot-pool',
            spot_max_price=0.5,
            replicas=3,
        )

        body = mock_ocm_client.create_machine_pool.call_args[0][1]
        assert body['aws'] == {'spot_market_options': {'max_price': 0.5}}

    @pytest.mark.asyncio
    async def test_given_hcp_cluster_when_create_then_uses_node_pools_endpoint(
        self, mock_mcp, mock_ocm_client_hcp, mock_context
    ):
        """Test rosa_create_machinepool on HCP uses node_pools endpoint."""
        handler = RosaMachinePoolHandler(mock_mcp, mock_ocm_client_hcp, allow_write=True)
        await handler.rosa_create_machinepool(
            mock_context,
            cluster_id='hcp-id',
            name='nodepool-1',
            instance_type='m5.xlarge',
            replicas=2,
        )

        mock_ocm_client_hcp.create_node_pool.assert_called_once()
        body = mock_ocm_client_hcp.create_node_pool.call_args[0][1]
        assert body['aws_node_pool'] == {'instance_type': 'm5.xlarge'}
        assert 'instance_type' not in body

    @pytest.mark.asyncio
    async def test_given_no_replicas_when_create_then_defaults_to_two(
        self, mock_mcp, mock_ocm_client, mock_context
    ):
        """Test rosa_create_machinepool defaults to 2 replicas when not specified."""
        handler = RosaMachinePoolHandler(mock_mcp, mock_ocm_client, allow_write=True)
        await handler.rosa_create_machinepool(
            mock_context, cluster_id='test-id', name='pool-default'
        )

        body = mock_ocm_client.create_machine_pool.call_args[0][1]
        assert body['replicas'] == 2


class TestRosaUpdateMachinepool:
    """Tests for rosa_update_machinepool."""

    @pytest.mark.asyncio
    async def test_given_write_disabled_when_update_then_raises_value_error(
        self, mock_mcp, mock_ocm_client, mock_context
    ):
        """Test rosa_update_machinepool requires allow_write."""
        handler = RosaMachinePoolHandler(mock_mcp, mock_ocm_client, allow_write=False)

        with pytest.raises(ValueError, match='Write operations disabled'):
            await handler.rosa_update_machinepool(
                mock_context, cluster_id='test-id', pool_id='pool-1', replicas=5
            )

    @pytest.mark.asyncio
    async def test_given_replicas_when_update_then_changes_replicas(
        self, mock_mcp, mock_ocm_client, mock_context
    ):
        """Test rosa_update_machinepool changes replicas."""
        handler = RosaMachinePoolHandler(mock_mcp, mock_ocm_client, allow_write=True)
        await handler.rosa_update_machinepool(
            mock_context, cluster_id='test-id', pool_id='pool-1', replicas=5
        )

        mock_ocm_client.update_machine_pool.assert_called_once_with(
            'test-id', 'pool-1', {'replicas': 5}
        )

    @pytest.mark.asyncio
    async def test_given_autoscaling_params_when_update_then_enables_autoscaling(
        self, mock_mcp, mock_ocm_client, mock_context
    ):
        """Test rosa_update_machinepool enables autoscaling."""
        handler = RosaMachinePoolHandler(mock_mcp, mock_ocm_client, allow_write=True)
        await handler.rosa_update_machinepool(
            mock_context,
            cluster_id='test-id',
            pool_id='pool-1',
            min_replicas=2,
            max_replicas=8,
        )

        body = mock_ocm_client.update_machine_pool.call_args[0][2]
        assert body['autoscaling'] == {'min_replicas': 2, 'max_replicas': 8}
        assert 'replicas' not in body

    @pytest.mark.asyncio
    async def test_given_hcp_cluster_when_update_then_uses_update_node_pool(
        self, mock_mcp, mock_ocm_client_hcp, mock_context
    ):
        """Test rosa_update_machinepool on HCP uses update_node_pool."""
        handler = RosaMachinePoolHandler(mock_mcp, mock_ocm_client_hcp, allow_write=True)
        await handler.rosa_update_machinepool(
            mock_context, cluster_id='hcp-id', pool_id='nodepool-1', replicas=4
        )

        mock_ocm_client_hcp.update_node_pool.assert_called_once_with(
            'hcp-id', 'nodepool-1', {'replicas': 4}
        )


class TestRosaDeleteMachinepool:
    """Tests for rosa_delete_machinepool."""

    @pytest.mark.asyncio
    async def test_given_write_disabled_when_delete_then_raises_value_error(
        self, mock_mcp, mock_ocm_client, mock_context
    ):
        """Test rosa_delete_machinepool requires allow_write."""
        handler = RosaMachinePoolHandler(mock_mcp, mock_ocm_client, allow_write=False)

        with pytest.raises(ValueError, match='Write operations disabled'):
            await handler.rosa_delete_machinepool(
                mock_context, cluster_id='test-id', pool_id='pool-1'
            )

    @pytest.mark.asyncio
    async def test_given_classic_cluster_when_delete_then_deletes_machine_pool(
        self, mock_mcp, mock_ocm_client, mock_context
    ):
        """Test rosa_delete_machinepool on Classic."""
        handler = RosaMachinePoolHandler(mock_mcp, mock_ocm_client, allow_write=True)
        result = await handler.rosa_delete_machinepool(
            mock_context, cluster_id='test-id', pool_id='pool-1'
        )

        mock_ocm_client.delete_machine_pool.assert_called_once_with('test-id', 'pool-1')
        data = json.loads(result[0].text)
        assert data['status'] == 'deleted'
        assert data['pool_id'] == 'pool-1'

    @pytest.mark.asyncio
    async def test_given_hcp_cluster_when_delete_then_deletes_node_pool(
        self, mock_mcp, mock_ocm_client_hcp, mock_context
    ):
        """Test rosa_delete_machinepool on HCP."""
        handler = RosaMachinePoolHandler(mock_mcp, mock_ocm_client_hcp, allow_write=True)
        result = await handler.rosa_delete_machinepool(
            mock_context, cluster_id='hcp-id', pool_id='nodepool-1'
        )

        mock_ocm_client_hcp.delete_node_pool.assert_called_once_with('hcp-id', 'nodepool-1')
        data = json.loads(result[0].text)
        assert data['status'] == 'deleted'
