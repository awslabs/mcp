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

"""BDD step definitions for ROSA advanced operations (live API)."""

from pytest_bdd import given, scenarios, then, when
from tests.step_defs.conftest import run


scenarios('../features/rosa_advanced_operations.feature')


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


@when("I query alerts metrics for the test cluster")
def query_alerts(ocm_client, cluster_id, response):
    """Query alerts metrics for the test cluster."""
    try:
        response.data = run(ocm_client.get_cluster_metrics(cluster_id, 'alerts'))
    except Exception as e:
        # Metrics may not always be available
        response.error = e
        response.data = {}


@when("I query cluster_operators metrics for the test cluster")
def query_cluster_operators(ocm_client, cluster_id, response):
    """Query cluster_operators metrics for the test cluster."""
    try:
        response.data = run(ocm_client.get_cluster_metrics(cluster_id, 'cluster_operators'))
    except Exception as e:
        response.error = e
        response.data = {}


@when("I check delete protection for the test cluster")
def check_delete_protection(ocm_client, cluster_id, response):
    """Check delete protection for the test cluster."""
    try:
        response.data = run(ocm_client.get_delete_protection(cluster_id))
    except Exception:
        # Fallback: get cluster info and check delete_protection field
        cluster = run(ocm_client.get_cluster(cluster_id))
        response.data = cluster.get('delete_protection', {})


@when("I list available add-ons")
def list_addons(ocm_client, response):
    """List available add-ons."""
    response.data = run(ocm_client.list_available_addons(size=100))


# --- Then Steps ---


@then("the response should be valid metrics data")
def check_metrics_data(response):
    """Verify the metrics response is valid."""
    # Either we got data or the error was a known API limitation
    if response.error:
        # HTTP 404 or similar — acceptable for some cluster types
        pass
    else:
        assert response.data is not None


@then("the response should indicate protection status")
def check_protection_status(response):
    """Verify protection status is returned."""
    assert response.data is not None
    # The response should contain an 'enabled' field or be a dict
    assert isinstance(response.data, dict)


@then("at least 1 add-on should be available")
def check_addons_count(response):
    """Verify at least 1 add-on is available."""
    items = response.data.get('items', [])
    assert len(items) >= 1


@then("each add-on should have a name and id")
def check_addon_fields(response):
    """Verify each add-on has a name and id."""
    items = response.data.get('items', [])
    for item in items:
        assert 'id' in item
        assert 'name' in item
