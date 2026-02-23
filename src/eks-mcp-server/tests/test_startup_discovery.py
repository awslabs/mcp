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

"""Tests for automatic cluster discovery at startup."""

import json
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from awslabs.eks_mcp_server.config import ClusterConfig, ConfigManager
from awslabs.eks_mcp_server.eks_discovery_handler import EKSDiscoveryHandler


@pytest.fixture(autouse=True)
def reset_config():
    """Reset ConfigManager before each test."""
    ConfigManager.reset()
    yield
    ConfigManager.reset()


def test_discover_clusters_at_startup_no_config():
    """Test discovery when no configuration is loaded."""
    discovered = EKSDiscoveryHandler.discover_clusters_at_startup()
    assert discovered == []


def test_discover_clusters_at_startup_with_explicit_clusters():
    """Test that discovery is skipped when explicit clusters are configured."""
    # Create a config with explicit clusters
    config_data = {
        'accounts': [{'account_id': '123456789012', 'regions': ['us-east-1']}],
        'clusters': [
            {
                'name': 'test-cluster',
                'region': 'us-east-1',
                'account_id': '123456789012',
            }
        ],
    }

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(config_data, f)
        config_path = f.name

    try:
        ConfigManager.load_config(config_path)
        discovered = EKSDiscoveryHandler.discover_clusters_at_startup()
        assert discovered == []
    finally:
        import os

        os.unlink(config_path)


@patch('awslabs.eks_mcp_server.eks_discovery_handler.AwsHelper')
def test_discover_clusters_at_startup_discovers_clusters(mock_aws_helper):
    """Test that clusters are discovered when no explicit clusters configured."""
    # Create a config without explicit clusters
    config_data = {
        'accounts': [{'account_id': '123456789012', 'regions': ['us-east-1', 'us-west-2']}]
    }

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(config_data, f)
        config_path = f.name

    try:
        ConfigManager.load_config(config_path)

        # Mock the EKS client
        mock_eks_client = MagicMock()
        mock_eks_client.list_clusters.return_value = {'clusters': ['cluster1', 'cluster2']}
        mock_aws_helper.create_boto3_client_for_account_region.return_value = mock_eks_client

        # Run discovery
        discovered = EKSDiscoveryHandler.discover_clusters_at_startup()

        # Verify discovery was attempted for both regions
        assert mock_aws_helper.create_boto3_client_for_account_region.call_count == 2

        # Verify discovered clusters
        assert len(discovered) == 4  # 2 clusters x 2 regions
        cluster_names = [c.name for c in discovered]
        assert 'cluster1' in cluster_names
        assert 'cluster2' in cluster_names

    finally:
        import os

        os.unlink(config_path)


@patch('awslabs.eks_mcp_server.eks_discovery_handler.AwsHelper')
def test_config_manager_stores_discovered_clusters(mock_aws_helper):
    """Test that ConfigManager properly stores and retrieves discovered clusters."""
    # Create a config without explicit clusters
    config_data = {'accounts': [{'account_id': '123456789012', 'regions': ['us-east-1']}]}

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(config_data, f)
        config_path = f.name

    try:
        ConfigManager.load_config(config_path)

        # Mock the EKS client
        mock_eks_client = MagicMock()
        mock_eks_client.list_clusters.return_value = {'clusters': ['discovered-cluster']}
        mock_aws_helper.create_boto3_client_for_account_region.return_value = mock_eks_client

        # Run discovery and store results
        discovered = EKSDiscoveryHandler.discover_clusters_at_startup()
        ConfigManager.set_discovered_clusters(discovered)

        # Verify stored clusters
        assert ConfigManager.has_discovered_clusters()
        assert len(ConfigManager.get_discovered_clusters()) == 1
        assert ConfigManager.get_discovered_clusters()[0].name == 'discovered-cluster'

        # Verify list_clusters returns discovered clusters
        all_clusters = ConfigManager.list_clusters()
        assert len(all_clusters) == 1
        assert all_clusters[0].name == 'discovered-cluster'

        # Verify get_cluster works with discovered clusters
        cluster = ConfigManager.get_cluster('discovered-cluster')
        assert cluster is not None
        assert cluster.name == 'discovered-cluster'
        assert cluster.region == 'us-east-1'
        assert cluster.account_id == '123456789012'

    finally:
        import os

        os.unlink(config_path)


def test_config_manager_prefers_explicit_over_discovered():
    """Test that explicit clusters take precedence over discovered clusters."""
    # Create explicit clusters
    explicit_clusters = [
        ClusterConfig(
            name='explicit-cluster',
            region='us-east-1',
            account_id='123456789012',
            description='cluster1',
        )
    ]

    # Create discovered clusters
    discovered_clusters = [
        ClusterConfig(
            name='discovered-cluster',
            region='us-west-2',
            account_id='123456789012',
            description='cluster2',
        )
    ]

    # Store discovered clusters first
    ConfigManager.set_discovered_clusters(discovered_clusters)

    # Create config with explicit clusters
    config_data = {
        'accounts': [{'account_id': '123456789012', 'regions': ['us-east-1']}],
        'clusters': [
            {
                'name': 'explicit-cluster',
                'region': 'us-east-1',
                'account_id': '123456789012',
            }
        ],
    }

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(config_data, f)
        config_path = f.name

    try:
        ConfigManager.load_config(config_path)

        # Verify explicit clusters take precedence
        assert ConfigManager.has_explicit_clusters()
        all_clusters = ConfigManager.list_clusters()
        assert len(all_clusters) == 1
        assert all_clusters[0].name == 'explicit-cluster'

    finally:
        import os

        os.unlink(config_path)


@patch('awslabs.eks_mcp_server.eks_discovery_handler.AwsHelper')
def test_discover_clusters_with_default_credentials(mock_aws_helper):
    """Test discovering clusters using default credentials when no config file is provided."""
    # Mock STS client to return account ID
    mock_sts_client = MagicMock()
    mock_sts_client.get_caller_identity.return_value = {'Account': '123456789012'}

    # Mock EKS client to return clusters
    mock_eks_client = MagicMock()
    mock_eks_client.list_clusters.return_value = {
        'clusters': ['default-cluster-1', 'default-cluster-2']
    }

    # Configure mock to return appropriate clients
    def create_client_side_effect(service_name, region_name=None):
        if service_name == 'sts':
            return mock_sts_client
        elif service_name == 'eks':
            return mock_eks_client
        return MagicMock()

    mock_aws_helper.create_boto3_client.side_effect = create_client_side_effect
    mock_aws_helper.get_aws_region.return_value = 'us-east-1'

    # Run discovery with default credentials
    discovered = EKSDiscoveryHandler.discover_clusters_with_default_credentials()

    # Verify STS was called to get account ID
    mock_sts_client.get_caller_identity.assert_called_once()

    # Verify EKS client was called to list clusters
    mock_eks_client.list_clusters.assert_called_once()

    # Verify discovered clusters
    assert len(discovered) == 2
    assert discovered[0].name == 'default-cluster-1'
    assert discovered[0].region == 'us-east-1'
    assert discovered[0].account_id == '123456789012'
    assert discovered[0].validated is True
    assert discovered[1].name == 'default-cluster-2'


@patch('awslabs.eks_mcp_server.eks_discovery_handler.AwsHelper')
def test_discover_with_default_credentials_uses_fallback_region(mock_aws_helper):
    """Test that default credentials discovery uses us-east-1 when AWS_REGION is not set."""
    # Mock STS client
    mock_sts_client = MagicMock()
    mock_sts_client.get_caller_identity.return_value = {'Account': '123456789012'}

    # Mock EKS client
    mock_eks_client = MagicMock()
    mock_eks_client.list_clusters.return_value = {'clusters': ['test-cluster']}

    # Configure mock - no region from environment
    def create_client_side_effect(service_name, region_name=None):
        if service_name == 'sts':
            return mock_sts_client
        elif service_name == 'eks':
            return mock_eks_client
        return MagicMock()

    mock_aws_helper.create_boto3_client.side_effect = create_client_side_effect
    mock_aws_helper.get_aws_region.return_value = None  # No AWS_REGION set

    # Run discovery
    discovered = EKSDiscoveryHandler.discover_clusters_with_default_credentials()

    # Verify us-east-1 was used as default
    assert len(discovered) == 1
    assert discovered[0].region == 'us-east-1'


@patch('awslabs.eks_mcp_server.eks_discovery_handler.AwsHelper')
def test_discover_with_default_credentials_creates_minimal_config(mock_aws_helper):
    """Test that discovery with default credentials creates a minimal config."""
    # Mock STS client
    mock_sts_client = MagicMock()
    mock_sts_client.get_caller_identity.return_value = {'Account': '123456789012'}

    # Mock EKS client
    mock_eks_client = MagicMock()
    mock_eks_client.list_clusters.return_value = {'clusters': ['test-cluster']}

    def create_client_side_effect(service_name, region_name=None):
        if service_name == 'sts':
            return mock_sts_client
        elif service_name == 'eks':
            return mock_eks_client
        return MagicMock()

    mock_aws_helper.create_boto3_client.side_effect = create_client_side_effect
    mock_aws_helper.get_aws_region.return_value = 'us-west-2'

    # Before discovery, config should not be loaded
    assert not ConfigManager.is_configured()

    # Run discovery
    discovered = EKSDiscoveryHandler.discover_clusters_with_default_credentials()

    # After discovery, config should be loaded with minimal config
    assert ConfigManager.is_configured()
    config = ConfigManager.get_config()
    assert config is not None
    assert len(config.accounts) == 1
    assert config.accounts[0].account_id == '123456789012'
    assert config.accounts[0].regions == ['us-west-2']
    assert config.clusters is None  # No explicit clusters


@patch('awslabs.eks_mcp_server.eks_discovery_handler.AwsHelper')
def test_discover_with_default_credentials_handles_no_clusters(mock_aws_helper):
    """Test that discovery handles the case when no clusters are found."""
    # Mock STS client
    mock_sts_client = MagicMock()
    mock_sts_client.get_caller_identity.return_value = {'Account': '123456789012'}

    # Mock EKS client - no clusters
    mock_eks_client = MagicMock()
    mock_eks_client.list_clusters.return_value = {'clusters': []}

    def create_client_side_effect(service_name, region_name=None):
        if service_name == 'sts':
            return mock_sts_client
        elif service_name == 'eks':
            return mock_eks_client
        return MagicMock()

    mock_aws_helper.create_boto3_client.side_effect = create_client_side_effect
    mock_aws_helper.get_aws_region.return_value = 'us-east-1'

    # Run discovery
    discovered = EKSDiscoveryHandler.discover_clusters_with_default_credentials()

    # Verify empty list is returned
    assert len(discovered) == 0

    # Config should still be created
    assert ConfigManager.is_configured()
