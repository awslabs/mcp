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

"""BDD step definitions for ROSA authentication management (live API)."""

import httpx
import pytest
import time
from pytest_bdd import given, parsers, scenarios, then, when
from tests.step_defs.conftest import run


scenarios('../features/rosa_auth_management.feature')


# --- Given Steps ---


@given("a real OCM client is available")
def ocm_available(ocm_client):
    """Verify we have a real OCM client."""
    assert ocm_client is not None


@given("a test ROSA cluster exists")
def cluster_exists(cluster_id):
    """Verify a test cluster was discovered."""
    assert cluster_id is not None


# --- When Steps ---


@when("I list identity providers for the test cluster")
def list_idps(ocm_client, cluster_id, response):
    """List identity providers for the test cluster."""
    response.data = run(ocm_client.list_identity_providers(cluster_id))


@when(parsers.parse('I create a test IDP named "{name}" of type HTPasswd'))
def create_idp(ocm_client, cluster_id, response, name):
    """Create an HTPasswd identity provider."""
    body = {
        'type': 'HTPasswdIdentityProvider',
        'name': name,
        'htpasswd': {
            'users': {
                'items': [
                    {'username': 'bdd-test-user', 'password': 'BddT3st!Pass99'}
                ]
            }
        },
    }
    try:
        response.data = run(ocm_client.create_identity_provider(cluster_id, body))
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 403:
            pytest.skip("Insufficient permissions for write operations (403 Forbidden)")
        raise


@when(parsers.parse('I delete the test IDP "{name}"'))
def delete_idp(ocm_client, cluster_id, response, name):
    """Delete the test identity provider."""
    # Brief pause to let creation propagate
    time.sleep(2)
    # Find the IDP id by name
    idps = run(ocm_client.list_identity_providers(cluster_id))
    idp_id = None
    for item in idps.get('items', []):
        if item.get('name') == name:
            idp_id = item.get('id')
            break
    assert idp_id is not None, f"IDP '{name}' not found for deletion"
    response.data = run(ocm_client.delete_identity_provider(cluster_id, idp_id))


# --- Then Steps ---


@then("the response should be a valid IDP list")
def check_idp_list(response):
    """Verify the response is a valid IDP list."""
    assert response.data is not None
    # The response should have 'items' key (may be empty list)
    assert 'items' in response.data


@then("the IDP creation should succeed")
def check_idp_creation(response):
    """Verify IDP was created."""
    assert response.data is not None
    assert 'id' in response.data


@then(parsers.parse('"{name}" should appear in the IDP list'))
def check_idp_in_list(ocm_client, cluster_id, name):
    """Verify the IDP appears in the list."""
    idps = run(ocm_client.list_identity_providers(cluster_id))
    names = [item.get('name') for item in idps.get('items', [])]
    assert name in names


@then(parsers.parse('"{name}" should no longer appear in the IDP list'))
def check_idp_deleted(ocm_client, cluster_id, name):
    """Verify the IDP no longer appears in the list."""
    # Brief pause to let deletion propagate
    time.sleep(2)
    idps = run(ocm_client.list_identity_providers(cluster_id))
    names = [item.get('name') for item in idps.get('items', [])]
    assert name not in names
