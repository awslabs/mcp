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

"""BDD step definitions for ROSA machine pool management (live API)."""

import httpx
import pytest
import time
from pytest_bdd import given, parsers, scenarios, then, when
from tests.step_defs.conftest import run


scenarios('../features/rosa_machinepool_management.feature')


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


@when("I list pools for the test cluster")
def list_pools(ocm_client, cluster_id, is_hcp, response):
    """List machine/node pools for the test cluster."""
    if is_hcp:
        response.data = run(ocm_client.list_node_pools(cluster_id))
    else:
        response.data = run(ocm_client.list_machine_pools(cluster_id))


@when(parsers.parse('I create a test machine pool named "{name}" with {replicas:d} replicas'))
def create_pool(ocm_client, cluster_id, is_hcp, response, name, replicas):
    """Create a test machine pool."""
    try:
        if is_hcp:
            # HCP requires subnet + version from existing pool, same instance type for region compat
            existing = run(ocm_client.list_node_pools(cluster_id))
            ref_pool = existing['items'][0]
            body = {
                'id': name,
                'replicas': replicas,
                'aws_node_pool': {'instance_type': ref_pool['aws_node_pool']['instance_type']},
                'subnet': ref_pool['subnet'],
                'version': {'id': ref_pool['version']['id']},
            }
            response.data = run(ocm_client.create_node_pool(cluster_id, body))
        else:
            body = {
                'id': name,
                'replicas': replicas,
                'instance_type': 'm5.xlarge',
            }
            response.data = run(ocm_client.create_machine_pool(cluster_id, body))
    except httpx.HTTPStatusError as e:
        if e.response.status_code in (400, 403):
            pytest.skip(f"Cannot create pool: {e.response.status_code} {e.response.text[:200]}")
        raise


@when(parsers.parse('I delete the test pool "{name}"'))
def delete_pool(ocm_client, cluster_id, is_hcp, response, name):
    """Delete the test machine pool."""
    # Brief pause to let creation propagate
    time.sleep(2)
    if is_hcp:
        response.data = run(ocm_client.delete_node_pool(cluster_id, name))
    else:
        response.data = run(ocm_client.delete_machine_pool(cluster_id, name))


# --- Then Steps ---


@then("at least 1 pool should exist")
def check_pool_count(response):
    """Verify at least 1 pool exists."""
    items = response.data.get('items', [])
    assert len(items) >= 1


@then("each pool should have an instance type")
def check_pool_instance_type(response):
    """Verify each pool has an instance type."""
    items = response.data.get('items', [])
    for item in items:
        # Classic uses instance_type directly, HCP uses aws_node_pool.instance_type
        instance_type = item.get('instance_type') or (
            item.get('aws_node_pool', {}).get('instance_type')
        )
        assert instance_type is not None, f"Pool {item.get('id')} has no instance type"


@then("the pool creation should succeed")
def check_pool_creation(response):
    """Verify pool was created."""
    assert response.data is not None
    assert 'id' in response.data


@then("the pool should appear in the pool list")
def check_pool_in_list(ocm_client, cluster_id, is_hcp, response):
    """Verify the created pool appears in the list."""
    pool_id = response.data.get('id')
    if is_hcp:
        pools = run(ocm_client.list_node_pools(cluster_id))
    else:
        pools = run(ocm_client.list_machine_pools(cluster_id))
    ids = [p.get('id') for p in pools.get('items', [])]
    assert pool_id in ids


@then("the pool should no longer exist in the list")
def check_pool_deleted(ocm_client, cluster_id, is_hcp):
    """Verify the pool no longer exists."""
    # Brief pause to let deletion propagate
    time.sleep(2)
    if is_hcp:
        pools = run(ocm_client.list_node_pools(cluster_id))
    else:
        pools = run(ocm_client.list_machine_pools(cluster_id))
    ids = [p.get('id') for p in pools.get('items', [])]
    assert 'bdd-test-pool' not in ids
