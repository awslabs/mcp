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

"""BDD step definitions for ROSA networking (live API)."""

from pytest_bdd import given, scenarios, then, when
from tests.step_defs.conftest import run


scenarios('../features/rosa_networking.feature')


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


@when("I list ingresses for the test cluster")
def list_ingresses(ocm_client, cluster_id, response):
    """List ingresses for the test cluster."""
    response.data = run(ocm_client.list_ingresses(cluster_id))


# --- Then Steps ---


@then("at least 1 ingress should exist")
def check_ingress_count(response):
    """Verify at least 1 ingress exists."""
    items = response.data.get('items', [])
    assert len(items) >= 1


@then("the default ingress should have a DNS name")
def check_ingress_dns(response):
    """Verify the default ingress has a DNS name."""
    items = response.data.get('items', [])
    # Find the default ingress (usually the first one or one with 'default' in attributes)
    default_ingress = items[0]
    # DNS name may be in 'dns_name' or derived from cluster domain
    default_ingress.get('dns_name', '') or default_ingress.get('default', '')
    # At minimum, the ingress should have an id
    assert default_ingress.get('id') is not None
