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

"""BDD step definitions for ROSA networking management scenarios."""

import json
import pytest
from awslabs.rosa_mcp_server.rosa_networking_handler import RosaNetworkingHandler
from pytest_bdd import given, parsers, scenarios, then, when
from tests.step_defs.conftest import run
from unittest.mock import AsyncMock


scenarios('../features/rosa_networking.feature')


# --- Fixtures ---


@pytest.fixture
def networking_handler(mock_mcp, mock_ocm_client):
    """Create a RosaNetworkingHandler with mocks and write enabled."""
    return RosaNetworkingHandler(mock_mcp, mock_ocm_client, allow_write=True)


# --- Given Steps ---


@given('the ROSA MCP server is initialized with OCM client', target_fixture='_server_init')
def rosa_server_initialized(mock_ocm_client, mock_mcp):
    """The ROSA MCP server is initialized with a mocked OCM client."""
    pass


@given('write operations are enabled', target_fixture='_write_enabled')
def write_enabled():
    """Write operations are enabled on the handler."""
    pass


# --- When Steps ---


@when(parsers.parse('I list ingresses for cluster "{cluster_id}"'))
def list_ingresses(networking_handler, mock_context, response_holder, cluster_id):
    """List ingresses for a cluster."""
    result = run(networking_handler.rosa_list_ingresses(mock_context, cluster_id=cluster_id))
    response_holder['result'] = result


@when('I create an ingress with:')
def create_ingress_with_table(networking_handler, mock_context, mock_ocm_client, response_holder, datatable):
    """Create an ingress using data from a table."""
    params = {}
    for row in datatable:
        key = row[0].strip()
        value = row[1].strip()
        if key == 'private':
            params[key] = value.lower() == 'true'
        else:
            params[key] = value

    # Update mock to reflect lb_type
    lb_type = params.get('lb_type', 'classic')
    mock_ocm_client.create_ingress = AsyncMock(return_value={
        'id': 'ingress-new',
        'listening': 'internal' if params.get('private', False) else 'external',
        'load_balancer_type': lb_type,
    })

    result = run(networking_handler.rosa_create_ingress(
        mock_context,
        cluster_id=params.get('cluster_id', 'test-id'),
        private=params.get('private', False),
        lb_type=lb_type,
    ))
    response_holder['result'] = result


@when(parsers.parse('I create a private ingress with route selectors {selectors_json}'))
def create_private_ingress(networking_handler, mock_context, mock_ocm_client, response_holder, selectors_json):
    """Create a private ingress with route selectors."""
    selectors = json.loads(selectors_json)

    mock_ocm_client.create_ingress = AsyncMock(return_value={
        'id': 'ingress-new',
        'listening': 'internal',
        'load_balancer_type': 'classic',
        'route_selectors': selectors,
    })

    result = run(networking_handler.rosa_create_ingress(
        mock_context,
        cluster_id='test-id',
        private=True,
        route_selectors=selectors,
    ))
    response_holder['result'] = result


@when(parsers.parse('I update ingress "{ingress_id}" on cluster "{cluster_id}" to private'))
def update_ingress(networking_handler, mock_context, response_holder, ingress_id, cluster_id):
    """Update an ingress to private."""
    result = run(networking_handler.rosa_update_ingress(
        mock_context,
        cluster_id=cluster_id,
        ingress_id=ingress_id,
        private=True,
    ))
    response_holder['result'] = result


@when(parsers.parse('I delete ingress "{ingress_id}" from cluster "{cluster_id}"'))
def delete_ingress(networking_handler, mock_context, response_holder, ingress_id, cluster_id):
    """Delete an ingress."""
    result = run(networking_handler.rosa_delete_ingress(
        mock_context,
        cluster_id=cluster_id,
        ingress_id=ingress_id,
    ))
    response_holder['result'] = result


# --- Then Steps ---


@then('the response should contain ingress data')
def response_contains_ingress_data(response_holder):
    """The response contains ingress data."""
    result = response_holder['result']
    assert result is not None
    data = json.loads(result[0].text)
    assert 'items' in data


@then('the ingress should use NLB load balancer type')
def ingress_uses_nlb(mock_ocm_client):
    """The ingress uses NLB load balancer type."""
    mock_ocm_client.create_ingress.assert_called_once()
    call_args = mock_ocm_client.create_ingress.call_args
    body = call_args.args[1] if len(call_args.args) > 1 else call_args.kwargs.get('body', {})
    assert body.get('load_balancer_type') == 'nlb'


@then('the ingress should be private')
def ingress_is_private(mock_ocm_client):
    """The ingress is private."""
    mock_ocm_client.create_ingress.assert_called_once()
    call_args = mock_ocm_client.create_ingress.call_args
    body = call_args.args[1] if len(call_args.args) > 1 else call_args.kwargs.get('body', {})
    assert body.get('listening') == 'internal'


@then('the ingress should have route selectors')
def ingress_has_route_selectors(mock_ocm_client):
    """The ingress has route selectors configured."""
    call_args = mock_ocm_client.create_ingress.call_args
    body = call_args.args[1] if len(call_args.args) > 1 else call_args.kwargs.get('body', {})
    assert 'route_selectors' in body


@then('the OCM API should patch the ingress')
def ocm_patches_ingress(mock_ocm_client):
    """The OCM API patched the ingress."""
    mock_ocm_client.update_ingress.assert_called_once()


@then('the OCM API should delete the ingress')
def ocm_deletes_ingress(mock_ocm_client):
    """The OCM API deleted the ingress."""
    mock_ocm_client.delete_ingress.assert_called_once()
