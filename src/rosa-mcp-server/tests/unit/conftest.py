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

"""Pytest configuration and fixtures for ROSA MCP Server tests."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def mock_ocm_client():
    """Create a mock OCMClient instance with all methods as AsyncMock."""
    mock = MagicMock()

    # Token handling
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
        'name': 'new-cluster',
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
        'id': 'pool-1',
        'replicas': 3,
        'instance_type': 'm5.2xlarge',
    })
    mock.update_machine_pool = AsyncMock(return_value={
        'id': 'pool-1',
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
        'aws_node_pool': {'instance_type': 'm5.2xlarge'},
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
    mock.list_upgrade_policies = AsyncMock(return_value={'items': []})
    mock.create_upgrade_policy = AsyncMock(return_value={
        'id': 'policy-1',
        'version': '4.14.6',
        'schedule_type': 'manual',
    })

    # Autoscaler
    mock.get_autoscaler = AsyncMock(return_value={
        'resource_limits': {'min_replicas': 2, 'max_replicas': 10},
        'scale_down': {'enabled': True},
    })
    mock.create_autoscaler = AsyncMock(return_value={
        'resource_limits': {'min_replicas': 2, 'max_replicas': 10},
    })
    mock.update_autoscaler = AsyncMock(return_value={
        'resource_limits': {'min_replicas': 3, 'max_replicas': 15},
    })
    mock.delete_autoscaler = AsyncMock(return_value=204)

    # Add-ons
    mock.list_available_addons = AsyncMock(return_value={
        'items': [
            {'id': 'addon-1', 'name': 'Cluster Logging Operator'},
        ],
    })
    mock.list_cluster_addons = AsyncMock(return_value={
        'items': [
            {'id': 'addon-1', 'state': 'ready'},
        ],
    })
    mock.install_addon = AsyncMock(return_value={
        'id': 'addon-1',
        'state': 'installing',
    })
    mock.uninstall_addon = AsyncMock(return_value=204)

    # Groups & Users
    mock.list_groups = AsyncMock(return_value={
        'items': [
            {'id': 'dedicated-admins'},
            {'id': 'cluster-admins'},
        ],
    })
    mock.list_group_users = AsyncMock(return_value={
        'items': [
            {'id': 'testuser'},
        ],
    })
    mock.add_user_to_group = AsyncMock(return_value={'id': 'newuser'})
    mock.remove_user_from_group = AsyncMock(return_value=204)

    # Break glass credentials
    mock.list_break_glass_credentials = AsyncMock(return_value={
        'items': [
            {'id': 'bg-1', 'status': 'active'},
        ],
    })
    mock.create_break_glass_credential = AsyncMock(return_value={
        'id': 'bg-new',
        'status': 'created',
        'ttl': '24h',
    })

    # Delete protection
    mock.get_delete_protection = AsyncMock(return_value={
        'enabled': True,
    })
    mock.update_delete_protection = AsyncMock(return_value={
        'enabled': False,
    })

    # Machine types
    mock.list_machine_types = AsyncMock(return_value={
        'items': [
            {'id': 'm5.xlarge', 'cpu': {'value': 4}, 'memory': {'value': 16}},
        ],
    })

    # Tuning configs
    mock.list_tuning_configs = AsyncMock(return_value={
        'items': [
            {'id': 'tuning-1', 'name': 'my-tuning'},
        ],
    })
    mock.create_tuning_config = AsyncMock(return_value={
        'id': 'tuning-new',
        'name': 'new-tuning',
    })
    mock.delete_tuning_config = AsyncMock(return_value=204)

    # Kubelet config
    mock.get_kubelet_config = AsyncMock(return_value={
        'pod_pids_limit': 4096,
    })
    mock.update_kubelet_config = AsyncMock(return_value={
        'pod_pids_limit': 8192,
    })

    # Cluster status & metrics
    mock.get_cluster_status = AsyncMock(return_value={
        'state': 'ready',
        'dns_ready': True,
        'oidc_ready': True,
    })
    mock.get_cluster_metrics = AsyncMock(return_value={
        'alerts': [],
    })

    # Hibernation
    mock.hibernate_cluster = AsyncMock(return_value=200)
    mock.resume_cluster = AsyncMock(return_value=200)

    # Generic request method (used by some handlers)
    mock.request = AsyncMock(return_value={'status': 'ok'})

    return mock


@pytest.fixture
def mock_ocm_client_hcp():
    """Create a mock OCMClient that returns HCP (Hosted Control Plane) cluster."""
    mock = MagicMock()

    mock._ensure_token = AsyncMock(
        return_value='header.eyJ1c2VybmFtZSI6InRlc3R1c2VyIiwiZW1haWwiOiJ0ZXN0QGV4YW1wbGUuY29tIiwib3JnX2lkIjoib3JnMTIzIn0.signature'
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
        'aws_node_pool': {'instance_type': 'm5.2xlarge'},
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
def mock_boto3_client():
    """Mock boto3 client creation."""
    with patch('boto3.client') as mock:
        yield mock
