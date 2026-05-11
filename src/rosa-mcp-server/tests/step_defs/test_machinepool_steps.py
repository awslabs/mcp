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

"""BDD step definitions for ROSA machine pool management scenarios."""

import json
import pytest
from awslabs.rosa_mcp_server.rosa_machinepool_handler import RosaMachinePoolHandler
from pytest_bdd import given, parsers, scenarios, then, when
from tests.step_defs.conftest import run
from unittest.mock import AsyncMock


scenarios('../features/rosa_machinepool_management.feature')


# --- Fixtures ---


@pytest.fixture
def machinepool_handler(mock_mcp, mock_ocm_client):
    """Create a RosaMachinePoolHandler with mocks and write enabled."""
    return RosaMachinePoolHandler(mock_mcp, mock_ocm_client, allow_write=True)


@pytest.fixture
def machinepool_handler_hcp(mock_mcp, mock_ocm_client_hcp):
    """Create a RosaMachinePoolHandler for HCP clusters."""
    return RosaMachinePoolHandler(mock_mcp, mock_ocm_client_hcp, allow_write=True)


# --- Given Steps ---


@given('the ROSA MCP server is initialized with OCM client', target_fixture='_server_init')
def rosa_server_initialized(mock_ocm_client, mock_mcp):
    """The ROSA MCP server is initialized with a mocked OCM client."""
    pass


@given('write operations are enabled', target_fixture='_write_enabled')
def write_enabled():
    """Write operations are enabled on the handler."""
    pass


@given(parsers.parse('a Classic ROSA cluster with ID "{cluster_id}"'))
def classic_cluster(mock_ocm_client, cluster_id):
    """A Classic ROSA cluster exists."""
    mock_ocm_client.get_cluster = AsyncMock(return_value={
        'id': cluster_id,
        'name': 'classic-cluster',
        'state': 'ready',
        'hypershift': {'enabled': False},
    })


@given(parsers.parse('an HCP ROSA cluster with ID "{cluster_id}"'))
def hcp_cluster(mock_ocm_client, cluster_id):
    """An HCP ROSA cluster exists."""
    mock_ocm_client.get_cluster = AsyncMock(return_value={
        'id': cluster_id,
        'name': 'hcp-cluster',
        'state': 'ready',
        'hypershift': {'enabled': True},
    })


# --- When Steps ---


@when(parsers.parse('I list machine pools for cluster "{cluster_id}"'))
def list_pools(machinepool_handler, mock_context, response_holder, cluster_id):
    """List machine pools for a cluster."""
    result = run(machinepool_handler.rosa_list_machinepools(mock_context, cluster_id=cluster_id))
    response_holder['result'] = result


@when('I create a machine pool with:')
def create_pool_with_table(machinepool_handler, mock_context, mock_ocm_client, response_holder, datatable):
    """Create a machine pool using data from a table."""
    params = {}
    for row in datatable:
        key = row[0].strip()
        value = row[1].strip()
        if key == 'replicas':
            params[key] = int(value)
        elif key == 'min_replicas':
            params[key] = int(value)
        elif key == 'max_replicas':
            params[key] = int(value)
        else:
            params[key] = value

    # Configure mock based on parameters
    if 'min_replicas' in params and 'max_replicas' in params:
        mock_ocm_client.create_machine_pool = AsyncMock(return_value={
            'id': params.get('name', 'pool-1'),
            'instance_type': params.get('instance_type', 'm5.xlarge'),
            'autoscaling': {
                'min_replicas': params['min_replicas'],
                'max_replicas': params['max_replicas'],
            },
        })
    else:
        mock_ocm_client.create_machine_pool = AsyncMock(return_value={
            'id': params.get('name', 'pool-1'),
            'replicas': params.get('replicas', 2),
            'instance_type': params.get('instance_type', 'm5.xlarge'),
        })

    result = run(machinepool_handler.rosa_create_machinepool(
        mock_context,
        cluster_id=params.get('cluster_id', 'test-id'),
        name=params.get('name', 'workers'),
        instance_type=params.get('instance_type', 'm5.xlarge'),
        replicas=params.get('replicas'),
        min_replicas=params.get('min_replicas'),
        max_replicas=params.get('max_replicas'),
    ))
    response_holder['result'] = result
    response_holder['create_params'] = params


@when(parsers.parse('I create a machine pool with spot_max_price {price}'))
def create_pool_with_spot(machinepool_handler, mock_context, mock_ocm_client, response_holder):
    """Create a machine pool with spot instances."""
    result = run(machinepool_handler.rosa_create_machinepool(
        mock_context,
        cluster_id='test-id',
        name='spot-workers',
        instance_type='m5.xlarge',
        replicas=2,
        spot_max_price=0.5,
    ))
    response_holder['result'] = result


@when(parsers.parse('labels {labels_json}'))
def set_labels(response_holder, labels_json):
    """Set labels for a machine pool creation."""
    response_holder['labels'] = json.loads(labels_json)


@when(parsers.parse('taints {taints_json}'))
def set_taints(machinepool_handler, mock_context, mock_ocm_client, response_holder, taints_json):
    """Set taints and re-create the machine pool with labels and taints."""
    taints = json.loads(taints_json)
    labels = response_holder.get('labels', {})
    params = response_holder.get('create_params', {})

    result = run(machinepool_handler.rosa_create_machinepool(
        mock_context,
        cluster_id=params.get('cluster_id', 'test-id'),
        name=params.get('name', 'dedicated'),
        instance_type=params.get('instance_type', 'm5.xlarge'),
        replicas=2,
        labels=labels,
        taints=taints,
    ))
    response_holder['result'] = result
    response_holder['taints'] = taints


@when(parsers.parse('I create a machine pool on cluster "{cluster_id}"'))
def create_pool_on_hcp(machinepool_handler, mock_context, response_holder, cluster_id):
    """Create a machine pool on an HCP cluster."""
    result = run(machinepool_handler.rosa_create_machinepool(
        mock_context,
        cluster_id=cluster_id,
        name='workers',
        instance_type='m5.xlarge',
        replicas=2,
    ))
    response_holder['result'] = result


@when(parsers.parse('I update machine pool "{pool_id}" on cluster "{cluster_id}" with replicas {replicas:d}'))
def update_pool(machinepool_handler, mock_context, response_holder, pool_id, cluster_id, replicas):
    """Update a machine pool's replica count."""
    result = run(machinepool_handler.rosa_update_machinepool(
        mock_context,
        cluster_id=cluster_id,
        pool_id=pool_id,
        replicas=replicas,
    ))
    response_holder['result'] = result


@when(parsers.parse('I delete machine pool "{pool_id}" from cluster "{cluster_id}"'))
def delete_pool(machinepool_handler, mock_context, response_holder, pool_id, cluster_id):
    """Delete a machine pool."""
    result = run(machinepool_handler.rosa_delete_machinepool(
        mock_context,
        cluster_id=cluster_id,
        pool_id=pool_id,
    ))
    response_holder['result'] = result


# --- Then Steps ---


@then('the OCM API should call machine_pools endpoint')
def ocm_calls_machine_pools(mock_ocm_client):
    """The OCM API called the machine_pools endpoint."""
    mock_ocm_client.list_machine_pools.assert_called_once()


@then('the response should contain pool data')
def response_contains_pool_data(response_holder):
    """The response contains machine pool data."""
    result = response_holder['result']
    assert result is not None
    data = json.loads(result[0].text)
    assert 'items' in data


@then('the OCM API should call node_pools endpoint')
def ocm_calls_node_pools(mock_ocm_client):
    """The OCM API called the node_pools endpoint."""
    mock_ocm_client.list_node_pools.assert_called_once()


@then(parsers.parse('the pool should be created with {count:d} replicas'))
def pool_created_with_replicas(mock_ocm_client, count):
    """The pool was created with the specified number of replicas."""
    mock_ocm_client.create_machine_pool.assert_called_once()
    call_args = mock_ocm_client.create_machine_pool.call_args
    body = call_args.args[1] if len(call_args.args) > 1 else call_args.kwargs.get('body', {})
    assert body.get('replicas') == count


@then(parsers.parse('the instance type should be "{instance_type}"'))
def pool_instance_type(mock_ocm_client, instance_type):
    """The pool has the specified instance type."""
    call_args = mock_ocm_client.create_machine_pool.call_args
    body = call_args.args[1] if len(call_args.args) > 1 else call_args.kwargs.get('body', {})
    assert body.get('instance_type') == instance_type


@then('the pool should have autoscaling configured')
def pool_has_autoscaling(mock_ocm_client):
    """The pool has autoscaling configured."""
    mock_ocm_client.create_machine_pool.assert_called_once()
    call_args = mock_ocm_client.create_machine_pool.call_args
    body = call_args.args[1] if len(call_args.args) > 1 else call_args.kwargs.get('body', {})
    assert 'autoscaling' in body


@then(parsers.parse('min replicas should be {count:d}'))
def min_replicas_value(mock_ocm_client, count):
    """The min replicas value matches."""
    call_args = mock_ocm_client.create_machine_pool.call_args
    body = call_args.args[1] if len(call_args.args) > 1 else call_args.kwargs.get('body', {})
    assert body['autoscaling']['min_replicas'] == count


@then(parsers.parse('max replicas should be {count:d}'))
def max_replicas_value(mock_ocm_client, count):
    """The max replicas value matches."""
    call_args = mock_ocm_client.create_machine_pool.call_args
    body = call_args.args[1] if len(call_args.args) > 1 else call_args.kwargs.get('body', {})
    assert body['autoscaling']['max_replicas'] == count


@then('the pool should have spot market options configured')
def pool_has_spot(mock_ocm_client):
    """The pool has spot market options configured."""
    mock_ocm_client.create_machine_pool.assert_called_once()
    call_args = mock_ocm_client.create_machine_pool.call_args
    body = call_args.args[1] if len(call_args.args) > 1 else call_args.kwargs.get('body', {})
    assert 'aws' in body
    assert 'spot_market_options' in body['aws']


@then('the pool should have the labels set')
def pool_has_labels(mock_ocm_client):
    """The pool has labels set."""
    mock_ocm_client.create_machine_pool.assert_called()
    call_args = mock_ocm_client.create_machine_pool.call_args
    body = call_args.args[1] if len(call_args.args) > 1 else call_args.kwargs.get('body', {})
    assert 'labels' in body


@then('the pool should have the taints set')
def pool_has_taints(mock_ocm_client):
    """The pool has taints set."""
    call_args = mock_ocm_client.create_machine_pool.call_args
    body = call_args.args[1] if len(call_args.args) > 1 else call_args.kwargs.get('body', {})
    assert 'taints' in body


@then('the OCM API should use the node_pools endpoint')
def ocm_uses_node_pools_endpoint(mock_ocm_client):
    """The OCM API used the node_pools endpoint for creation."""
    mock_ocm_client.create_node_pool.assert_called_once()


@then(parsers.parse('the OCM API should patch with replicas {count:d}'))
def ocm_patches_replicas(mock_ocm_client, count):
    """The OCM API patched with the specified replica count."""
    mock_ocm_client.update_machine_pool.assert_called_once()
    call_args = mock_ocm_client.update_machine_pool.call_args
    body = call_args.args[2] if len(call_args.args) > 2 else call_args.kwargs.get('body', {})
    assert body.get('replicas') == count


@then('the OCM API should delete the pool')
def ocm_deletes_pool(mock_ocm_client):
    """The OCM API deleted the pool."""
    mock_ocm_client.delete_machine_pool.assert_called_once()


@then('the response should confirm deletion')
def response_confirms_deletion(response_holder):
    """The response confirms the pool was deleted."""
    data = json.loads(response_holder['result'][0].text)
    assert data.get('status') == 'deleted'
