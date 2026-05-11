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

"""Shared fixtures for ROSA MCP Server BDD tests."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock


def run(coro):
    """Run an async coroutine synchronously for use in BDD step definitions."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@pytest.fixture
def mock_ocm_client():
    """Create a mock OCMClient instance with all methods as AsyncMock."""
    mock = MagicMock()

    # Token handling - JWT with test user info
    mock._ensure_token = AsyncMock(
        return_value='header.eyJ1c2VybmFtZSI6InRlc3R1c2VyIiwiZW1haWwiOiJ0ZXN0QGV4YW1wbGUuY29tIiwib3JnX2lkIjoib3JnMTIzIiwiYWNjb3VudF9pZCI6ImFjYzEyMyIsImlzX29yZ19hZG1pbiI6dHJ1ZSwiZmlyc3RfbmFtZSI6IlRlc3QiLCJsYXN0X25hbWUiOiJVc2VyIn0.signature'
    )

    # Cluster methods
    mock.list_clusters = AsyncMock(return_value={
        'kind': 'ClusterList',
        'items': [
            {'id': 'test-id', 'name': 'test-cluster', 'state': 'ready'},
        ],
        'total': 1,
    })
    mock.get_cluster = AsyncMock(return_value={
        'id': 'test-id',
        'name': 'test-cluster',
        'state': 'ready',
        'hypershift': {'enabled': False},
        'version': {'raw_id': '4.14.5', 'available_upgrades': ['4.14.6', '4.14.7']},
    })
    mock.create_cluster = AsyncMock(return_value={
        'id': 'new-id',
        'name': 'my-rosa-cluster',
        'state': 'installing',
    })
    mock.delete_cluster = AsyncMock(return_value=204)
    mock.update_cluster = AsyncMock(return_value={
        'id': 'test-id',
        'name': 'test-cluster',
        'state': 'ready',
    })
    mock.get_cluster_credentials = AsyncMock(return_value={
        'kubeconfig': 'apiVersion: v1\nclusters: []',
        'admin': {'user': 'admin', 'password': 'secret123'},
    })
    mock.get_install_logs = AsyncMock(return_value={
        'content': 'time="2024-01-01" level=info msg="Installing cluster..."',
    })

    # Versions
    mock.list_versions = AsyncMock(return_value={
        'items': [
            {'id': 'openshift-v4.14.5', 'raw_id': '4.14.5', 'rosa_enabled': True},
            {'id': 'openshift-v4.14.6', 'raw_id': '4.14.6', 'rosa_enabled': True},
        ],
    })

    # Machine pools
    mock.list_machine_pools = AsyncMock(return_value={
        'items': [
            {'id': 'worker', 'replicas': 2, 'instance_type': 'm5.xlarge'},
        ],
    })
    mock.create_machine_pool = AsyncMock(return_value={
        'id': 'gpu-workers',
        'replicas': 3,
        'instance_type': 'p3.2xlarge',
    })
    mock.update_machine_pool = AsyncMock(return_value={
        'id': 'workers',
        'replicas': 5,
    })
    mock.delete_machine_pool = AsyncMock(return_value=204)

    # Node pools (HCP)
    mock.list_node_pools = AsyncMock(return_value={
        'items': [
            {'id': 'workers', 'replicas': 2, 'aws_node_pool': {'instance_type': 'm5.xlarge'}},
        ],
    })
    mock.create_node_pool = AsyncMock(return_value={
        'id': 'nodepool-1',
        'replicas': 3,
        'aws_node_pool': {'instance_type': 'm5.xlarge'},
    })
    mock.update_node_pool = AsyncMock(return_value={
        'id': 'nodepool-1',
        'replicas': 5,
    })
    mock.delete_node_pool = AsyncMock(return_value=204)

    # Identity providers
    mock.list_identity_providers = AsyncMock(return_value={
        'items': [
            {'id': 'idp-1', 'type': 'HTPasswdIdentityProvider', 'name': 'htpasswd'},
            {'id': 'idp-2', 'type': 'GithubIdentityProvider', 'name': 'github'},
        ],
    })
    mock.create_identity_provider = AsyncMock(return_value={
        'id': 'idp-new',
        'type': 'HTPasswdIdentityProvider',
        'name': 'cluster-admin',
    })
    mock.delete_identity_provider = AsyncMock(return_value=204)

    # Ingresses
    mock.list_ingresses = AsyncMock(return_value={
        'items': [
            {'id': 'ingress-default', 'listening': 'external', 'load_balancer_type': 'classic'},
        ],
    })
    mock.create_ingress = AsyncMock(return_value={
        'id': 'ingress-new',
        'listening': 'external',
        'load_balancer_type': 'nlb',
    })
    mock.update_ingress = AsyncMock(return_value={
        'id': 'ingress-default',
        'listening': 'internal',
    })
    mock.delete_ingress = AsyncMock(return_value=204)

    # Upgrade policies
    mock.create_upgrade_policy = AsyncMock(return_value={
        'id': 'policy-1',
        'version': '4.14.6',
        'schedule_type': 'manual',
    })

    # Generic request method (used by advanced handler)
    mock.request = AsyncMock(return_value={'status': 'ok', 'state': 'ready', 'dns_ready': True})

    return mock


@pytest.fixture
def mock_ocm_client_hcp():
    """Create a mock OCMClient that returns HCP (Hosted Control Plane) cluster."""
    mock = MagicMock()

    mock._ensure_token = AsyncMock(
        return_value='header.eyJ1c2VybmFtZSI6InRlc3R1c2VyIiwiZW1haWwiOiJ0ZXN0QGV4YW1wbGUuY29tIn0.signature'
    )

    mock.get_cluster = AsyncMock(return_value={
        'id': 'hcp-id',
        'name': 'hcp-cluster',
        'state': 'ready',
        'hypershift': {'enabled': True},
        'version': {'raw_id': '4.14.5', 'available_upgrades': ['4.14.6']},
    })
    mock.list_node_pools = AsyncMock(return_value={
        'items': [
            {'id': 'workers', 'replicas': 2, 'aws_node_pool': {'instance_type': 'm5.xlarge'}},
        ],
    })
    mock.create_node_pool = AsyncMock(return_value={
        'id': 'nodepool-1',
        'replicas': 3,
        'aws_node_pool': {'instance_type': 'm5.xlarge'},
    })
    mock.update_node_pool = AsyncMock(return_value={
        'id': 'nodepool-1',
        'replicas': 5,
    })
    mock.delete_node_pool = AsyncMock(return_value=204)
    mock.list_machine_pools = AsyncMock(return_value={'items': []})
    mock.create_machine_pool = AsyncMock(return_value={'id': 'pool-1'})
    mock.update_machine_pool = AsyncMock(return_value={'id': 'pool-1'})
    mock.delete_machine_pool = AsyncMock(return_value=204)

    return mock


@pytest.fixture
def mock_mcp():
    """Create a mock MCP server instance."""
    mcp = MagicMock()
    mcp.tool = MagicMock(return_value=lambda f: f)
    return mcp


@pytest.fixture
def mock_context():
    """Create a mock MCP context."""
    ctx = MagicMock()
    ctx.request_id = 'test-request-id'
    return ctx


@pytest.fixture
def response_holder():
    """Hold response data between steps."""
    return {'result': None, 'error': None}
