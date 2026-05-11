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

"""Shared fixtures for ROSA MCP Server BDD live tests."""

import asyncio
import os
import pytest
from awslabs.rosa_mcp_server.ocm_client import OCMClient


def run(coro):
    """Run async from sync context."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            raise RuntimeError("loop running")
        return loop.run_until_complete(coro)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)


@pytest.fixture(scope="session")
def ocm_client():
    """Create a REAL OCM client from environment or ocm config."""
    try:
        client = OCMClient()
        return client
    except ValueError:
        pytest.skip("OCM credentials not available (set OCM_TOKEN or run `ocm login`)")


@pytest.fixture(scope="session")
def cluster_id(ocm_client):
    """Discover a ROSA cluster to test against.

    Uses ROSA_TEST_CLUSTER_ID env var if set, otherwise picks the first
    ready ROSA cluster found in the account.
    """
    env_id = os.environ.get('ROSA_TEST_CLUSTER_ID')
    if env_id:
        return env_id

    # Auto-discover: find first ready ROSA cluster
    data = run(ocm_client.list_clusters(
        search="product.id = 'rosa' AND state = 'ready'", size=1
    ))
    items = data.get('items', [])
    if not items:
        pytest.skip("No ready ROSA cluster found for testing")
    return items[0]['id']


@pytest.fixture(scope="session")
def cluster_info(ocm_client, cluster_id):
    """Get full cluster info for the test cluster."""
    return run(ocm_client.get_cluster(cluster_id))


@pytest.fixture(scope="session")
def is_hcp(cluster_info):
    """Whether the test cluster is HCP."""
    return cluster_info.get('hypershift', {}).get('enabled', False)


class ResponseHolder:
    """Holds response data between steps."""

    def __init__(self):
        """Initialize with empty data and error."""
        self.data = None
        self.error = None


@pytest.fixture
def response():
    """Provide a fresh ResponseHolder for each scenario."""
    return ResponseHolder()
