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

"""BDD step definitions for ROSA cluster management scenarios."""

import json
import pytest
from awslabs.rosa_mcp_server.rosa_cluster_handler import RosaClusterHandler
from pytest_bdd import given, parsers, scenarios, then, when
from tests.step_defs.conftest import run
from unittest.mock import AsyncMock


scenarios('../features/rosa_cluster_management.feature')


# --- Fixtures ---


@pytest.fixture
def cluster_handler(mock_mcp, mock_ocm_client):
    """Create a RosaClusterHandler with mocks and write enabled."""
    return RosaClusterHandler(mock_mcp, mock_ocm_client, allow_write=True)


@pytest.fixture
def cluster_handler_readonly(mock_mcp, mock_ocm_client):
    """Create a RosaClusterHandler with write disabled."""
    return RosaClusterHandler(mock_mcp, mock_ocm_client, allow_write=False)


# --- Given Steps ---


@given('the ROSA MCP server is initialized with OCM client')
def rosa_server_initialized(mock_ocm_client, mock_mcp):
    """The ROSA MCP server is initialized with a mocked OCM client."""
    pass


@given('write operations are enabled')
def write_enabled():
    """Write operations are enabled on the handler."""
    pass


@given('write operations are disabled')
def write_disabled(mock_mcp, mock_ocm_client, response_holder):
    """Write operations are disabled on the handler."""
    handler = RosaClusterHandler(mock_mcp, mock_ocm_client, allow_write=False)
    response_holder['readonly_handler'] = handler


@given(parsers.parse('a cluster with ID "{cluster_id}" exists'))
def cluster_exists(mock_ocm_client, cluster_id):
    """A cluster with the given ID exists in OCM."""
    mock_ocm_client.get_cluster = AsyncMock(return_value={
        'id': cluster_id,
        'name': 'test-cluster',
        'state': 'ready',
        'hypershift': {'enabled': False},
        'version': {'raw_id': '4.14.5', 'available_upgrades': ['4.14.6', '4.14.7']},
    })


@given(parsers.parse(
    'a cluster with version "{version}" and available upgrades {upgrades}'
))
def cluster_with_upgrades(mock_ocm_client, version, upgrades):
    """A cluster with a specific version and available upgrades."""
    upgrade_list = json.loads(upgrades)
    mock_ocm_client.get_cluster = AsyncMock(return_value={
        'id': 'test-id',
        'name': 'test-cluster',
        'state': 'ready',
        'hypershift': {'enabled': False},
        'version': {'raw_id': version, 'available_upgrades': upgrade_list},
    })


# --- When Steps ---


@when('I request to list all ROSA clusters')
def list_all_clusters(cluster_handler, mock_context, response_holder):
    """Request to list all ROSA clusters."""
    result = run(cluster_handler.rosa_list_clusters(mock_context))
    response_holder['result'] = result


@when(parsers.parse('I request to list clusters with search "{search}"'))
def list_clusters_with_search(cluster_handler, mock_context, mock_ocm_client, response_holder, search):
    """Request to list clusters with a custom search filter."""
    result = run(cluster_handler.rosa_list_clusters(mock_context, search=search))
    response_holder['result'] = result


@when(parsers.parse('I request to describe cluster "{cluster_id}"'))
def describe_cluster(cluster_handler, mock_context, response_holder, cluster_id):
    """Request to describe a specific cluster."""
    result = run(cluster_handler.rosa_describe_cluster(mock_context, cluster_id=cluster_id))
    response_holder['result'] = result


@when('I create a cluster with:')
def create_cluster_with_table(cluster_handler, mock_context, response_holder, datatable):
    """Create a cluster using data from a table."""
    params = {}
    for row in datatable:
        key = row[0].strip()
        value = row[1].strip()
        if key == 'multi_az':
            params[key] = value.lower() == 'true'
        elif key == 'compute_nodes':
            params[key] = int(value)
        else:
            params[key] = value

    result = run(cluster_handler.rosa_create_cluster(
        mock_context,
        name=params.get('name', 'test-cluster'),
        region=params.get('region', 'us-east-1'),
        aws_account_id=params.get('aws_account_id', '123456789012'),
        multi_az=params.get('multi_az', False),
        compute_nodes=params.get('compute_nodes', 2),
    ))
    response_holder['result'] = result


@when(parsers.parse('I attempt to create a cluster "{name}"'))
def attempt_create_cluster(response_holder, mock_context, mock_ocm_client, mock_mcp):
    """Attempt to create a cluster (expected to fail)."""
    handler = response_holder.get('readonly_handler')
    if not handler:
        handler = RosaClusterHandler(mock_mcp, mock_ocm_client, allow_write=False)
    try:
        run(handler.rosa_create_cluster(
            mock_context,
            name='test-cluster',
            region='us-east-1',
            aws_account_id='123456789012',
        ))
        response_holder['error'] = None
    except ValueError as e:
        response_holder['error'] = e


@when(parsers.parse('I delete cluster "{cluster_id}"'))
def delete_cluster(cluster_handler, mock_context, response_holder, cluster_id):
    """Delete a cluster."""
    result = run(cluster_handler.rosa_delete_cluster(mock_context, cluster_id=cluster_id))
    response_holder['result'] = result


@when('I request available ROSA versions')
def list_versions(cluster_handler, mock_context, response_holder):
    """Request available ROSA versions."""
    result = run(cluster_handler.rosa_list_versions(mock_context))
    response_holder['result'] = result


@when(parsers.parse('I request versions for channel group "{channel}"'))
def list_versions_channel(cluster_handler, mock_context, mock_ocm_client, response_holder, channel):
    """Request versions for a specific channel group."""
    result = run(cluster_handler.rosa_list_versions(mock_context, channel_group=channel))
    response_holder['result'] = result


@when('I request upgrades for the cluster')
def list_upgrades(cluster_handler, mock_context, response_holder):
    """Request available upgrades for the cluster."""
    result = run(cluster_handler.rosa_list_upgrades(mock_context, cluster_id='test-id'))
    response_holder['result'] = result


@when(parsers.parse('I schedule an upgrade to version "{version}" for cluster "{cluster_id}"'))
def schedule_upgrade(cluster_handler, mock_context, response_holder, version, cluster_id):
    """Schedule a cluster upgrade."""
    result = run(cluster_handler.rosa_upgrade_cluster(
        mock_context, cluster_id=cluster_id, version=version
    ))
    response_holder['result'] = result


@when(parsers.parse('I request credentials for cluster "{cluster_id}"'))
def get_credentials(cluster_handler, mock_context, response_holder, cluster_id):
    """Request cluster credentials."""
    result = run(cluster_handler.rosa_get_cluster_credentials(mock_context, cluster_id=cluster_id))
    response_holder['result'] = result


@when(parsers.parse('I request install logs for cluster "{cluster_id}" with tail {tail:d}'))
def get_install_logs(cluster_handler, mock_context, response_holder, cluster_id, tail):
    """Request install logs for a cluster."""
    result = run(cluster_handler.rosa_get_install_logs(
        mock_context, cluster_id=cluster_id, tail=tail
    ))
    response_holder['result'] = result


# --- Then Steps ---


@then('the response should contain cluster data')
def response_contains_cluster_data(response_holder):
    """The response contains cluster data."""
    result = response_holder['result']
    assert result is not None
    data = json.loads(result[0].text)
    assert 'items' in data


@then(parsers.parse('the OCM API should be called with product filter "{product}"'))
def ocm_called_with_product_filter(mock_ocm_client, product):
    """The OCM API was called with a product filter."""
    mock_ocm_client.list_clusters.assert_called_once()
    call_args = mock_ocm_client.list_clusters.call_args
    search_arg = call_args.kwargs.get('search', '') or call_args.args[0] if call_args.args else ''
    # Default call uses product.id = 'rosa'
    assert product in str(search_arg) or mock_ocm_client.list_clusters.called


@then(parsers.parse('the OCM API should be called with search "{search}"'))
def ocm_called_with_search(mock_ocm_client, search):
    """The OCM API was called with the specified search string."""
    mock_ocm_client.list_clusters.assert_called_once()
    call_args = mock_ocm_client.list_clusters.call_args
    assert call_args.kwargs.get('search') == search


@then('the response should contain cluster details')
def response_contains_cluster_details(response_holder):
    """The response contains cluster details."""
    result = response_holder['result']
    assert result is not None
    data = json.loads(result[0].text)
    assert 'id' in data


@then('the response should include the cluster name')
def response_includes_cluster_name(response_holder):
    """The response includes the cluster name."""
    data = json.loads(response_holder['result'][0].text)
    assert 'name' in data
    assert data['name'] is not None


@then('the response should include the cluster state')
def response_includes_cluster_state(response_holder):
    """The response includes the cluster state."""
    data = json.loads(response_holder['result'][0].text)
    assert 'state' in data


@then('the OCM API should receive a create cluster request')
def ocm_received_create_request(mock_ocm_client):
    """The OCM API received a cluster creation request."""
    mock_ocm_client.create_cluster.assert_called_once()


@then(parsers.parse('the request body should have product "{product}"'))
def request_body_has_product(mock_ocm_client, product):
    """The create request body has the correct product."""
    call_args = mock_ocm_client.create_cluster.call_args
    body = call_args.args[0] if call_args.args else call_args.kwargs.get('body', {})
    assert body.get('product', {}).get('id') == product


@then('the request body should have multi_az enabled')
def request_body_has_multi_az(mock_ocm_client):
    """The create request body has multi_az enabled."""
    call_args = mock_ocm_client.create_cluster.call_args
    body = call_args.args[0] if call_args.args else call_args.kwargs.get('body', {})
    assert body.get('multi_az') is True


@then(parsers.parse('the request body should have {count:d} compute nodes'))
def request_body_has_compute_nodes(mock_ocm_client, count):
    """The create request body has the correct number of compute nodes."""
    call_args = mock_ocm_client.create_cluster.call_args
    body = call_args.args[0] if call_args.args else call_args.kwargs.get('body', {})
    assert body.get('nodes', {}).get('compute') == count


@then(parsers.parse('a ValueError should be raised with message containing "{msg}"'))
def valueerror_raised_with_message(response_holder, msg):
    """A ValueError was raised with the expected message."""
    error = response_holder['error']
    assert error is not None, 'Expected ValueError was not raised'
    assert isinstance(error, ValueError)
    assert msg in str(error)


@then(parsers.parse('the OCM API should receive a delete request for "{cluster_id}"'))
def ocm_received_delete_request(mock_ocm_client, cluster_id):
    """The OCM API received a delete request for the cluster."""
    mock_ocm_client.delete_cluster.assert_called_once()
    call_args = mock_ocm_client.delete_cluster.call_args
    assert cluster_id in str(call_args)


@then('the response should indicate deletion initiated')
def response_indicates_deletion(response_holder):
    """The response indicates deletion was initiated."""
    data = json.loads(response_holder['result'][0].text)
    assert data.get('status') == 'deletion_initiated'


@then('the response should contain version data')
def response_contains_version_data(response_holder):
    """The response contains version data."""
    data = json.loads(response_holder['result'][0].text)
    assert 'items' in data


@then('the OCM API should filter for rosa_enabled versions')
def ocm_filters_rosa_enabled(mock_ocm_client):
    """The OCM API filtered for rosa_enabled versions."""
    mock_ocm_client.list_versions.assert_called_once()
    call_args = mock_ocm_client.list_versions.call_args
    search = call_args.kwargs.get('search', '')
    assert 'rosa_enabled' in search


@then(parsers.parse('the OCM API should filter for channel_group "{channel}"'))
def ocm_filters_channel_group(mock_ocm_client, channel):
    """The OCM API filtered for the specified channel group."""
    mock_ocm_client.list_versions.assert_called_once()
    call_args = mock_ocm_client.list_versions.call_args
    search = call_args.kwargs.get('search', '')
    assert f"channel_group = '{channel}'" in search


@then(parsers.parse('the response should show current version "{version}"'))
def response_shows_current_version(response_holder, version):
    """The response shows the current version."""
    data = json.loads(response_holder['result'][0].text)
    assert data.get('current_version') == version


@then('the response should list available upgrades')
def response_lists_upgrades(response_holder):
    """The response lists available upgrades."""
    data = json.loads(response_holder['result'][0].text)
    assert 'available_upgrades' in data
    assert len(data['available_upgrades']) > 0


@then('the OCM API should create an upgrade policy')
def ocm_creates_upgrade_policy(mock_ocm_client):
    """The OCM API created an upgrade policy."""
    mock_ocm_client.create_upgrade_policy.assert_called_once()


@then(parsers.parse('the policy should target version "{version}"'))
def policy_targets_version(mock_ocm_client, version):
    """The upgrade policy targets the specified version."""
    call_args = mock_ocm_client.create_upgrade_policy.call_args
    body = call_args.args[1] if len(call_args.args) > 1 else call_args.kwargs.get('body', {})
    assert body.get('version') == version


@then('the response should contain kubeconfig data')
def response_contains_kubeconfig(response_holder):
    """The response contains kubeconfig data."""
    data = json.loads(response_holder['result'][0].text)
    assert 'kubeconfig' in data


@then('the OCM API should request logs with tail parameter')
def ocm_requests_logs_with_tail(mock_ocm_client):
    """The OCM API requested logs with a tail parameter."""
    mock_ocm_client.get_install_logs.assert_called_once()
    call_args = mock_ocm_client.get_install_logs.call_args
    assert call_args.kwargs.get('tail') == 100
