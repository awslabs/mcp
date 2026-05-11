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
    """Create a mock OCMClient instance."""
    mock = MagicMock()
    mock._ensure_token = AsyncMock(return_value='header.eyJ1c2VybmFtZSI6InRlc3R1c2VyIiwiZW1haWwiOiJ0ZXN0QGV4YW1wbGUuY29tIiwib3JnX2lkIjoib3JnMTIzIn0.signature')
    mock.list_clusters = AsyncMock(return_value={'items': [], 'total': 0})
    mock.get_cluster = AsyncMock(return_value={'id': 'test-id', 'name': 'test-cluster'})
    mock.create_cluster = AsyncMock(return_value={'id': 'new-id', 'name': 'new-cluster'})
    mock.delete_cluster = AsyncMock(return_value=204)
    mock.get_cluster_credentials = AsyncMock(return_value={'kubeconfig': ''})
    mock.get_install_logs = AsyncMock(return_value={'content': 'log data'})
    mock.list_versions = AsyncMock(return_value={'items': []})
    mock.list_machine_pools = AsyncMock(return_value={'items': []})
    mock.create_machine_pool = AsyncMock(return_value={'id': 'pool-1'})
    mock.update_machine_pool = AsyncMock(return_value={'id': 'pool-1'})
    mock.delete_machine_pool = AsyncMock(return_value=204)
    mock.list_identity_providers = AsyncMock(return_value={'items': []})
    mock.create_identity_provider = AsyncMock(return_value={'id': 'idp-1'})
    mock.delete_identity_provider = AsyncMock(return_value=204)
    mock.list_ingresses = AsyncMock(return_value={'items': []})
    mock.create_ingress = AsyncMock(return_value={'id': 'ingress-1'})
    mock.update_ingress = AsyncMock(return_value={'id': 'ingress-1'})
    mock.delete_ingress = AsyncMock(return_value=204)
    mock.list_upgrade_policies = AsyncMock(return_value={'items': []})
    mock.create_upgrade_policy = AsyncMock(return_value={'id': 'policy-1'})
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
