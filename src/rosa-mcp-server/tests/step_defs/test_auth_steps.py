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

"""BDD step definitions for ROSA authentication management scenarios."""

import json
import pytest
from awslabs.rosa_mcp_server.rosa_auth_handler import RosaAuthHandler
from pytest_bdd import given, parsers, scenarios, then, when
from tests.step_defs.conftest import run
from unittest.mock import AsyncMock


scenarios('../features/rosa_auth_management.feature')


# --- Fixtures ---


@pytest.fixture
def auth_handler(mock_mcp, mock_ocm_client):
    """Create a RosaAuthHandler with mocks and write enabled."""
    return RosaAuthHandler(mock_mcp, mock_ocm_client, allow_write=True)


@pytest.fixture
def auth_handler_readonly(mock_mcp, mock_ocm_client):
    """Create a RosaAuthHandler with write disabled."""
    return RosaAuthHandler(mock_mcp, mock_ocm_client, allow_write=False)


# --- Given Steps ---


@given('the ROSA MCP server is initialized with OCM client', target_fixture='_server_init')
def rosa_server_initialized(mock_ocm_client, mock_mcp):
    """The ROSA MCP server is initialized with a mocked OCM client."""
    pass


@given('write operations are enabled', target_fixture='_write_enabled')
def write_enabled():
    """Write operations are enabled on the handler."""
    pass


@given('write operations are disabled')
def write_disabled(response_holder, mock_mcp, mock_ocm_client):
    """Write operations are disabled on the handler."""
    handler = RosaAuthHandler(mock_mcp, mock_ocm_client, allow_write=False)
    response_holder['readonly_handler'] = handler


@given('the OCM access token contains user info')
def token_contains_user_info(mock_ocm_client):
    """The OCM access token contains user information."""
    # Already set in the mock fixture with JWT containing username/email
    pass


@given('a cluster with HTPasswd and GitHub IDPs configured')
def cluster_with_idps(mock_ocm_client):
    """A cluster with both HTPasswd and GitHub IDPs configured."""
    mock_ocm_client.list_identity_providers = AsyncMock(return_value={
        'items': [
            {'id': 'idp-1', 'type': 'HTPasswdIdentityProvider', 'name': 'htpasswd'},
            {'id': 'idp-2', 'type': 'GithubIdentityProvider', 'name': 'github'},
        ],
    })


# --- When Steps ---


@when('I request whoami')
def request_whoami(auth_handler, mock_context, response_holder):
    """Request the current identity."""
    result = run(auth_handler.rosa_whoami(mock_context))
    response_holder['result'] = result


@when('I list identity providers for the cluster')
def list_idps(auth_handler, mock_context, response_holder):
    """List identity providers for the cluster."""
    result = run(auth_handler.rosa_list_idps(mock_context, cluster_id='test-id'))
    response_holder['result'] = result


@when('I create an IDP with:')
def create_idp_with_table(auth_handler, mock_context, mock_ocm_client, response_holder, datatable):
    """Create an IDP using data from a table."""
    params = {}
    for row in datatable:
        key = row[0].strip()
        value = row[1].strip()
        params[key] = value

    idp_type = params.get('idp_type', 'htpasswd')
    config = None
    if idp_type == 'htpasswd':
        config = {'username': 'admin', 'password': 'secret123'}
    elif idp_type == 'github':
        config = {'client_id': 'xxx', 'client_secret': 'yyy', 'organizations': ['myorg']}

    # Update mock to return matching type
    type_map = {
        'htpasswd': 'HTPasswdIdentityProvider',
        'github': 'GithubIdentityProvider',
    }
    mock_ocm_client.create_identity_provider = AsyncMock(return_value={
        'id': 'idp-new',
        'type': type_map.get(idp_type, idp_type),
        'name': params.get('name', 'test-idp'),
    })

    result = run(auth_handler.rosa_create_idp(
        mock_context,
        cluster_id=params.get('cluster_id', 'test-id'),
        name=params.get('name', 'test-idp'),
        idp_type=idp_type,
        config=config,
    ))
    response_holder['result'] = result


@when(parsers.parse('I delete IDP "{idp_id}" from cluster "{cluster_id}"'))
def delete_idp(auth_handler, mock_context, response_holder, idp_id, cluster_id):
    """Delete an identity provider."""
    result = run(auth_handler.rosa_delete_idp(
        mock_context, cluster_id=cluster_id, idp_id=idp_id
    ))
    response_holder['result'] = result


@when(parsers.parse('I create an admin for cluster "{cluster_id}"'))
def create_admin(auth_handler, mock_context, response_holder, cluster_id):
    """Create a cluster admin."""
    result = run(auth_handler.rosa_create_admin(mock_context, cluster_id=cluster_id))
    response_holder['result'] = result


@when('I attempt to create an IDP')
def attempt_create_idp(response_holder, mock_context):
    """Attempt to create an IDP (expected to fail)."""
    handler = response_holder.get('readonly_handler')
    try:
        run(handler.rosa_create_idp(
            mock_context,
            cluster_id='test-id',
            name='test-idp',
            idp_type='htpasswd',
        ))
        response_holder['error'] = None
    except ValueError as e:
        response_holder['error'] = e


# --- Then Steps ---


@then('the response should contain the username')
def response_contains_username(response_holder):
    """The response contains the username."""
    data = json.loads(response_holder['result'][0].text)
    assert 'username' in data
    assert data['username'] != ''


@then('the response should contain the email')
def response_contains_email(response_holder):
    """The response contains the email."""
    data = json.loads(response_holder['result'][0].text)
    assert 'email' in data
    assert data['email'] != ''


@then('the response should list both IDPs')
def response_lists_both_idps(response_holder):
    """The response lists both IDPs."""
    data = json.loads(response_holder['result'][0].text)
    assert 'items' in data
    assert len(data['items']) == 2


@then('the OCM API should create the IDP')
def ocm_creates_idp(mock_ocm_client):
    """The OCM API created the IDP."""
    mock_ocm_client.create_identity_provider.assert_called_once()


@then(parsers.parse('the IDP type should be "{idp_type}"'))
def idp_type_matches(mock_ocm_client, idp_type):
    """The IDP type matches the expected value."""
    call_args = mock_ocm_client.create_identity_provider.call_args
    body = call_args.args[1] if len(call_args.args) > 1 else call_args.kwargs.get('body', {})
    assert body.get('type') == idp_type


@then('the OCM API should delete the IDP')
def ocm_deletes_idp(mock_ocm_client):
    """The OCM API deleted the IDP."""
    mock_ocm_client.delete_identity_provider.assert_called_once()


@then('the response should contain a generated password')
def response_contains_password(response_holder):
    """The response contains a generated password."""
    data = json.loads(response_holder['result'][0].text)
    assert 'password' in data
    assert len(data['password']) > 0


@then(parsers.parse('an HTPasswd IDP named "{name}" should be created'))
def htpasswd_idp_created(mock_ocm_client, name):
    """An HTPasswd IDP with the specified name was created."""
    mock_ocm_client.create_identity_provider.assert_called_once()
    call_args = mock_ocm_client.create_identity_provider.call_args
    body = call_args.args[1] if len(call_args.args) > 1 else call_args.kwargs.get('body', {})
    assert body.get('name') == name
    assert body.get('type') == 'HTPasswdIdentityProvider'


@then('a ValueError should be raised')
def valueerror_raised(response_holder):
    """A ValueError was raised."""
    error = response_holder['error']
    assert error is not None, 'Expected ValueError was not raised'
    assert isinstance(error, ValueError)
