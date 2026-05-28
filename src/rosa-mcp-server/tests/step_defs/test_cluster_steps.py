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

"""BDD step definitions for ROSA cluster management (live API)."""

import pytest
from pytest_bdd import given, parsers, scenarios, then, when
from tests.step_defs.conftest import run


scenarios('../features/rosa_cluster_management.feature')


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


@when("I list all ROSA clusters via OCM API")
def list_clusters(ocm_client, response):
    """List all ROSA clusters."""
    response.data = run(ocm_client.list_clusters(search="product.id = 'rosa'"))


@when("I describe the test cluster")
def describe_cluster(ocm_client, cluster_id, response):
    """Describe the test cluster."""
    response.data = run(ocm_client.get_cluster(cluster_id))


@when("I list available ROSA versions")
def list_versions(ocm_client, response):
    """List available ROSA versions."""
    response.data = run(ocm_client.list_versions(
        search="rosa_enabled = 'true'", size=100
    ))


@when("I check available upgrades for the test cluster")
def check_upgrades(ocm_client, cluster_id, response):
    """Check available upgrades for the test cluster."""
    cluster = run(ocm_client.get_cluster(cluster_id))
    response.data = cluster.get('version', {})


@when("I get the test cluster status")
def get_status(ocm_client, cluster_id, response):
    """Get the cluster status."""
    response.data = run(ocm_client.get_cluster_status(cluster_id))


@when("I get credentials for the test cluster")
def get_credentials(ocm_client, cluster_id, response):
    """Get cluster credentials."""
    try:
        response.data = run(ocm_client.get_cluster_credentials(cluster_id))
    except Exception as e:
        # Some clusters may not expose credentials via this endpoint
        response.error = e


@when("I list available machine types")
def list_machine_types(ocm_client, response):
    """List available machine types (fetches multiple pages to find m5.xlarge)."""
    # Fetch first page for count assertion, then page with m5 types
    page1 = run(ocm_client.list_machine_types(size=100, page=1))
    total = page1.get('total', 0)
    # m5.xlarge is alphabetically around page 5-6 with size=100
    # Instead of fetching all pages, store total and first page items
    # Then fetch a targeted page for m5 types
    all_items = list(page1.get('items', []))
    # Fetch additional pages until we have m5.xlarge or hit 5 pages
    page_num = 2
    while page_num <= 6:
        page_data = run(ocm_client.list_machine_types(size=100, page=page_num))
        items = page_data.get('items', [])
        if not items:
            break
        all_items.extend(items)
        if any(i.get('id') == 'm5.xlarge' for i in items):
            break
        page_num += 1
    response.data = {'items': all_items, 'total': total}


# --- Then Steps ---


@then("the response should contain at least 1 cluster")
def check_clusters_count(response):
    """Verify at least 1 cluster returned."""
    assert response.data is not None
    total = response.data.get('total', 0)
    items = response.data.get('items', [])
    assert total >= 1 or len(items) >= 1


@then("each cluster should have an id and name")
def check_cluster_fields(response):
    """Verify each cluster has id and name."""
    items = response.data.get('items', [])
    for item in items:
        assert 'id' in item
        assert 'name' in item


@then("the response should contain the cluster name")
def check_cluster_name(response):
    """Verify cluster name is present."""
    assert 'name' in response.data
    assert response.data['name'] is not None
    assert len(response.data['name']) > 0


@then(parsers.parse('the cluster state should be "{state}"'))
def check_cluster_state(response, state):
    """Verify cluster state matches."""
    assert response.data.get('state') == state


@then("the cluster should have a version")
def check_cluster_version(response):
    """Verify cluster has a version."""
    version = response.data.get('version', {})
    assert 'raw_id' in version or 'id' in version


@then("the cluster should have a region")
def check_cluster_region(response):
    """Verify cluster has a region."""
    region = response.data.get('region', {})
    assert 'id' in region


@then("the cluster should have a console URL")
def check_cluster_console(response):
    """Verify cluster has a console URL."""
    console = response.data.get('console', {})
    assert 'url' in console
    assert console['url'].startswith('https://')


@then("at least 10 versions should be available")
def check_versions_count(response):
    """Verify at least 10 versions."""
    items = response.data.get('items', [])
    assert len(items) >= 10


@then("all versions should be ROSA-enabled")
def check_versions_rosa(response):
    """Verify all returned versions are ROSA-enabled."""
    items = response.data.get('items', [])
    for item in items:
        assert item.get('rosa_enabled') is True


@then("the response should include the current version")
def check_current_version(response):
    """Verify current version is in the response."""
    assert 'raw_id' in response.data or 'id' in response.data


@then(parsers.parse('the status should show state "{state}"'))
def check_status_state(response, state):
    """Verify status shows expected state."""
    assert response.data is not None
    assert response.data.get('state') == state


@then("DNS should be ready")
def check_dns_ready(response):
    """Verify DNS is ready."""
    assert response.data.get('dns_ready') is True


@then("the response should contain a kubeconfig")
def check_kubeconfig(response):
    """Verify kubeconfig is present."""
    if response.error:
        # Some clusters (HCP) may not support credentials endpoint
        pytest.skip(f"Credentials endpoint not available: {response.error}")
    assert response.data is not None
    assert 'kubeconfig' in response.data


@then("at least 50 machine types should be available")
def check_machine_types_count(response):
    """Verify at least 50 machine types available."""
    total = response.data.get('total', 0)
    assert total >= 50


@then("m5.xlarge should be in the list")
def check_m5xlarge(response):
    """Verify m5.xlarge is in the machine types list."""
    items = response.data.get('items', [])
    ids = [item.get('id', '') for item in items]
    assert 'm5.xlarge' in ids
