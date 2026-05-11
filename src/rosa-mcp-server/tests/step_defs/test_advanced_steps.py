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

"""BDD step definitions for ROSA advanced operations scenarios."""

import json
import pytest
from awslabs.rosa_mcp_server.rosa_advanced_handler import RosaAdvancedHandler
from pytest_bdd import given, parsers, scenarios, then, when
from tests.step_defs.conftest import run
from unittest.mock import AsyncMock


scenarios('../features/rosa_advanced_operations.feature')


# --- Fixtures ---


@pytest.fixture
def advanced_handler(mock_mcp, mock_ocm_client):
    """Create a RosaAdvancedHandler with mocks and write enabled."""
    return RosaAdvancedHandler(mock_mcp, mock_ocm_client, allow_write=True)


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


@when(parsers.parse('I hibernate cluster "{cluster_id}"'))
def hibernate_cluster(advanced_handler, mock_context, response_holder, cluster_id):
    """Hibernate a cluster."""
    result = run(advanced_handler.rosa_hibernate_cluster(mock_context, cluster_id=cluster_id))
    response_holder['result'] = result


@when(parsers.parse('I resume cluster "{cluster_id}"'))
def resume_cluster(advanced_handler, mock_context, response_holder, cluster_id):
    """Resume a cluster."""
    result = run(advanced_handler.rosa_resume_cluster(mock_context, cluster_id=cluster_id))
    response_holder['result'] = result


@when(parsers.parse('I get status for cluster "{cluster_id}"'))
def get_cluster_status(advanced_handler, mock_context, mock_ocm_client, response_holder, cluster_id):
    """Get cluster status."""
    mock_ocm_client.request = AsyncMock(return_value={
        'state': 'ready',
        'dns_ready': True,
        'oidc_ready': True,
    })
    result = run(advanced_handler.rosa_get_cluster_status(mock_context, cluster_id=cluster_id))
    response_holder['result'] = result


@when(parsers.parse('I get "{metric}" metrics for cluster "{cluster_id}"'))
def get_cluster_metrics(advanced_handler, mock_context, mock_ocm_client, response_holder, metric, cluster_id):
    """Get cluster metrics."""
    mock_ocm_client.request = AsyncMock(return_value={
        'metric': metric,
        'data': [],
    })
    result = run(advanced_handler.rosa_get_cluster_metrics(
        mock_context, cluster_id=cluster_id, metric=metric
    ))
    response_holder['result'] = result


@when(parsers.parse('I request metric "{metric}" for cluster "{cluster_id}"'))
def request_invalid_metric(advanced_handler, mock_context, response_holder, metric, cluster_id):
    """Request an invalid metric (expected to fail)."""
    try:
        run(advanced_handler.rosa_get_cluster_metrics(
            mock_context, cluster_id=cluster_id, metric=metric
        ))
        response_holder['error'] = None
    except ValueError as e:
        response_holder['error'] = e


@when(parsers.parse('I list break-glass credentials for cluster "{cluster_id}"'))
def list_break_glass(advanced_handler, mock_context, mock_ocm_client, response_holder, cluster_id):
    """List break-glass credentials."""
    mock_ocm_client.request = AsyncMock(return_value={
        'items': [
            {'id': 'bg-1', 'status': 'active'},
        ],
    })
    result = run(advanced_handler.rosa_list_break_glass_credentials(
        mock_context, cluster_id=cluster_id
    ))
    response_holder['result'] = result


@when(parsers.parse('I create a break-glass credential for cluster "{cluster_id}"'))
def create_break_glass(advanced_handler, mock_context, mock_ocm_client, response_holder, cluster_id):
    """Create a break-glass credential."""
    mock_ocm_client.request = AsyncMock(return_value={
        'id': 'bg-new',
        'status': 'created',
        'ttl': '24h',
    })
    result = run(advanced_handler.rosa_create_break_glass_credential(
        mock_context, cluster_id=cluster_id
    ))
    response_holder['result'] = result


@when(parsers.parse('I check delete protection for cluster "{cluster_id}"'))
def check_delete_protection(advanced_handler, mock_context, mock_ocm_client, response_holder, cluster_id):
    """Check delete protection status."""
    mock_ocm_client.request = AsyncMock(return_value={
        'id': cluster_id,
        'delete_protection': {'enabled': True},
    })
    result = run(advanced_handler.rosa_get_delete_protection(
        mock_context, cluster_id=cluster_id
    ))
    response_holder['result'] = result


@when(parsers.parse('I enable delete protection for cluster "{cluster_id}"'))
def enable_delete_protection(advanced_handler, mock_context, mock_ocm_client, response_holder, cluster_id):
    """Enable delete protection."""
    mock_ocm_client.request = AsyncMock(return_value={
        'delete_protection': {'enabled': True},
    })
    result = run(advanced_handler.rosa_set_delete_protection(
        mock_context, cluster_id=cluster_id, enabled=True
    ))
    response_holder['result'] = result


@when('I list available machine types')
def list_machine_types(advanced_handler, mock_context, mock_ocm_client, response_holder):
    """List available machine types."""
    mock_ocm_client.request = AsyncMock(return_value={
        'items': [
            {'id': 'm5.xlarge', 'cpu': {'value': 4}, 'memory': {'value': 16}},
            {'id': 'm5.2xlarge', 'cpu': {'value': 8}, 'memory': {'value': 32}},
        ],
    })
    result = run(advanced_handler.rosa_list_machine_types(mock_context))
    response_holder['result'] = result


# --- Then Steps ---


@then('the OCM API should POST to hibernate endpoint')
def ocm_posts_hibernate(mock_ocm_client):
    """The OCM API POSTed to the hibernate endpoint."""
    mock_ocm_client.request.assert_called()
    call_args = mock_ocm_client.request.call_args
    assert call_args.args[0] == 'POST'
    assert 'hibernate' in call_args.args[1]


@then('the response should confirm hibernation initiated')
def response_confirms_hibernation(response_holder):
    """The response confirms hibernation was initiated."""
    data = json.loads(response_holder['result'][0].text)
    assert data.get('status') == 'hibernation_initiated'


@then('the OCM API should POST to resume endpoint')
def ocm_posts_resume(mock_ocm_client):
    """The OCM API POSTed to the resume endpoint."""
    mock_ocm_client.request.assert_called()
    call_args = mock_ocm_client.request.call_args
    assert call_args.args[0] == 'POST'
    assert 'resume' in call_args.args[1]


@then('the response should contain state information')
def response_contains_state(response_holder):
    """The response contains state information."""
    data = json.loads(response_holder['result'][0].text)
    assert 'state' in data


@then('the response should contain DNS readiness')
def response_contains_dns(response_holder):
    """The response contains DNS readiness information."""
    data = json.loads(response_holder['result'][0].text)
    assert 'dns_ready' in data


@then(parsers.parse('the OCM API should query metric_queries/{metric}'))
def ocm_queries_metric(mock_ocm_client, metric):
    """The OCM API queried the correct metric endpoint."""
    mock_ocm_client.request.assert_called()
    call_args = mock_ocm_client.request.call_args
    assert 'metric_queries' in call_args.args[1]
    assert metric in call_args.args[1]


@then('a ValueError should be raised')
def valueerror_raised(response_holder):
    """A ValueError was raised."""
    error = response_holder['error']
    assert error is not None, 'Expected ValueError was not raised'
    assert isinstance(error, ValueError)


@then('the response should contain credentials list')
def response_contains_credentials_list(response_holder):
    """The response contains a credentials list."""
    data = json.loads(response_holder['result'][0].text)
    assert 'items' in data


@then('the OCM API should create the credential')
def ocm_creates_credential(mock_ocm_client):
    """The OCM API created the break-glass credential."""
    mock_ocm_client.request.assert_called()
    call_args = mock_ocm_client.request.call_args
    assert call_args.args[0] == 'POST'
    assert 'break_glass_credentials' in call_args.args[1]


@then('the response should show protection status')
def response_shows_protection_status(response_holder):
    """The response shows delete protection status."""
    data = json.loads(response_holder['result'][0].text)
    assert 'delete_protection_enabled' in data


@then('the OCM API should update delete protection to enabled')
def ocm_updates_delete_protection(mock_ocm_client):
    """The OCM API updated delete protection."""
    mock_ocm_client.request.assert_called()
    call_args = mock_ocm_client.request.call_args
    assert call_args.args[0] == 'PATCH'
    body = call_args.kwargs.get('body', {})
    assert body.get('delete_protection', {}).get('enabled') is True


@then('the response should contain instance types')
def response_contains_instance_types(response_holder):
    """The response contains instance types."""
    data = json.loads(response_holder['result'][0].text)
    assert 'items' in data
    assert len(data['items']) > 0
