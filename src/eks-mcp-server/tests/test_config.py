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

"""Tests for the configuration module."""

import json
import os
import pytest
import tempfile
import yaml
from awslabs.eks_mcp_server.config import (
    AccountConfig,
    ClusterConfig,
    ClustersConfig,
    ConfigManager,
)


class TestAccountConfig:
    """Tests for AccountConfig model."""

    def test_minimal_account_config(self):
        """Test minimal account configuration."""
        account = AccountConfig(
            account_id='123456789012',
            regions=['us-east-1'],
        )
        assert account.account_id == '123456789012'
        assert len(account.regions) == 1
        assert account.regions[0] == 'us-east-1'
        assert account.role_arn is None
        assert account.profile is None

    def test_account_with_custom_role(self):
        """Test account with custom role."""
        account = AccountConfig(
            account_id='123456789012',
            role_arn='arn:aws:iam::123456789012:role/CustomRole',
            external_id='my-external-id',
            regions=['us-east-1'],
        )
        assert account.role_arn == 'arn:aws:iam::123456789012:role/CustomRole'
        assert account.external_id == 'my-external-id'

    def test_account_with_profile(self):
        """Test account with profile."""
        account = AccountConfig(
            account_id='123456789012',
            profile='my-profile',
            regions=['us-east-1'],
        )
        assert account.profile == 'my-profile'

    def test_get_effective_role_arn_default(self):
        """Test default role ARN."""
        account = AccountConfig(
            account_id='123456789012',
            regions=['us-east-1'],
        )
        assert account.get_effective_role_arn() == 'arn:aws:iam::123456789012:role/McpEksOpsRole'

    def test_get_effective_role_arn_custom(self):
        """Test custom role ARN."""
        account = AccountConfig(
            account_id='123456789012',
            role_arn='arn:aws:iam::123456789012:role/CustomRole',
            regions=['us-east-1'],
        )
        assert account.get_effective_role_arn() == 'arn:aws:iam::123456789012:role/CustomRole'

    def test_get_access_method_profile(self):
        """Test access method with profile."""
        account = AccountConfig(
            account_id='123456789012',
            profile='my-profile',
            regions=['us-east-1'],
        )
        assert account.get_access_method() == 'profile'

    def test_get_access_method_role(self):
        """Test access method with role."""
        account = AccountConfig(
            account_id='123456789012',
            regions=['us-east-1'],
        )
        assert account.get_access_method() == 'role_assumption'

    def test_invalid_account_id(self):
        """Test invalid account ID."""
        with pytest.raises(ValueError, match='Invalid AWS account ID'):
            AccountConfig(
                account_id='12345',  # Too short
                regions=['us-east-1'],
            )

    def test_invalid_role_arn(self):
        """Test invalid role ARN."""
        with pytest.raises(ValueError, match='Invalid IAM role ARN format'):
            AccountConfig(
                account_id='123456789012',
                role_arn='invalid-arn',
                regions=['us-east-1'],
            )

    def test_invalid_region_format(self):
        """Test account with invalid region format."""
        with pytest.raises(ValueError, match='Invalid AWS region format'):
            AccountConfig(
                account_id='123456789012',
                regions=['invalid'],
            )

    def test_no_regions(self):
        """Test account with no regions."""
        with pytest.raises(ValueError, match='At least one region must be specified'):
            AccountConfig(
                account_id='123456789012',
                regions=[],
            )

    def test_duplicate_regions(self):
        """Test account with duplicate regions."""
        with pytest.raises(ValueError, match='Duplicate region names'):
            AccountConfig(
                account_id='123456789012',
                regions=['us-east-1', 'us-east-1'],
            )


class TestClusterConfig:
    """Tests for ClusterConfig model."""

    def test_valid_cluster_config(self):
        """Test valid cluster configuration."""
        cluster = ClusterConfig(
            name='my-cluster',
            region='us-east-1',
            account_id='123456789012',
            description='Test cluster',
        )
        assert cluster.name == 'my-cluster'
        assert cluster.region == 'us-east-1'
        assert cluster.account_id == '123456789012'
        assert cluster.description == 'Test cluster'

    def test_cluster_without_description(self):
        """Test cluster without description."""
        cluster = ClusterConfig(
            name='my-cluster',
            region='us-east-1',
            account_id='123456789012',
        )
        assert cluster.description is None

    def test_invalid_account_id(self):
        """Test cluster with invalid account ID."""
        with pytest.raises(ValueError, match='Invalid AWS account ID'):
            ClusterConfig(
                name='my-cluster',
                region='us-east-1',
                account_id='invalid',
            )

    def test_invalid_region(self):
        """Test cluster with invalid region."""
        with pytest.raises(ValueError, match='Invalid AWS region format'):
            ClusterConfig(
                name='my-cluster',
                region='invalid',
                account_id='123456789012',
            )


class TestClustersConfig:
    """Tests for ClustersConfig model."""

    def test_minimal_config(self):
        """Test minimal configuration."""
        config = ClustersConfig(
            accounts=[
                AccountConfig(
                    account_id='123456789012',
                    regions=['us-east-1'],
                )
            ]
        )
        assert len(config.accounts) == 1
        assert config.clusters is None

    def test_config_with_clusters(self):
        """Test configuration with explicit clusters."""
        config = ClustersConfig(
            accounts=[
                AccountConfig(
                    account_id='123456789012',
                    regions=['us-east-1'],
                )
            ],
            clusters=[
                ClusterConfig(
                    name='my-cluster',
                    region='us-east-1',
                    account_id='123456789012',
                )
            ],
        )
        assert len(config.accounts) == 1
        assert len(config.clusters) == 1

    def test_no_accounts(self):
        """Test configuration with no accounts."""
        with pytest.raises(ValueError, match='At least one account must be configured'):
            ClustersConfig(accounts=[])

    def test_duplicate_account_ids(self):
        """Test configuration with duplicate account IDs."""
        with pytest.raises(ValueError, match='Duplicate account IDs'):
            ClustersConfig(
                accounts=[
                    AccountConfig(
                        account_id='123456789012',
                        regions=['us-east-1'],
                    ),
                    AccountConfig(
                        account_id='123456789012',
                        regions=['us-west-2'],
                    ),
                ]
            )

    def test_duplicate_cluster_names(self):
        """Test configuration with duplicate cluster names."""
        with pytest.raises(ValueError, match='Duplicate cluster names'):
            ClustersConfig(
                accounts=[
                    AccountConfig(
                        account_id='123456789012',
                        regions=['us-east-1'],
                    )
                ],
                clusters=[
                    ClusterConfig(
                        name='my-cluster',
                        region='us-east-1',
                        account_id='123456789012',
                    ),
                    ClusterConfig(
                        name='my-cluster',
                        region='us-east-1',
                        account_id='123456789012',
                    ),
                ],
            )

    def test_validate_cluster_references_valid(self):
        """Test valid cluster references."""
        config = ClustersConfig(
            accounts=[
                AccountConfig(
                    account_id='123456789012',
                    regions=['us-east-1'],
                )
            ],
            clusters=[
                ClusterConfig(
                    name='my-cluster',
                    region='us-east-1',
                    account_id='123456789012',
                )
            ],
        )
        # Should not raise
        config.validate_cluster_references()

    def test_validate_cluster_references_invalid_region(self):
        """Test invalid cluster region reference."""
        config = ClustersConfig(
            accounts=[
                AccountConfig(
                    account_id='123456789012',
                    regions=['us-east-1'],
                )
            ],
            clusters=[
                ClusterConfig(
                    name='my-cluster',
                    region='us-west-2',  # Not in configured regions
                    account_id='123456789012',
                )
            ],
        )
        with pytest.raises(ValueError, match='not in the configured accounts/regions'):
            config.validate_cluster_references()

    def test_validate_cluster_references_invalid_account(self):
        """Test invalid cluster account reference."""
        config = ClustersConfig(
            accounts=[
                AccountConfig(
                    account_id='123456789012',
                    regions=['us-east-1'],
                )
            ],
            clusters=[
                ClusterConfig(
                    name='my-cluster',
                    region='us-east-1',
                    account_id='999999999999',  # Not in configured accounts
                )
            ],
        )
        with pytest.raises(ValueError, match='not in the configured accounts/regions'):
            config.validate_cluster_references()


class TestConfigManager:
    """Tests for ConfigManager class."""

    @pytest.fixture(autouse=True)
    def reset_config_manager(self):
        """Reset ConfigManager before each test."""
        ConfigManager.reset()
        yield
        ConfigManager.reset()

    def test_load_json_config(self):
        """Test loading JSON configuration."""
        config_data = {
            'accounts': [
                {
                    'account_id': '123456789012',
                    'regions': ['us-east-1'],
                }
            ],
            'clusters': [
                {
                    'name': 'my-cluster',
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
            assert ConfigManager.is_configured()
            assert len(ConfigManager.list_accounts()) == 1
            assert len(ConfigManager.list_clusters()) == 1
        finally:
            os.unlink(config_path)

    def test_load_yaml_config(self):
        """Test loading YAML configuration."""
        config_data = {
            'accounts': [
                {
                    'account_id': '123456789012',
                    'regions': ['us-east-1'],
                }
            ],
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name

        try:
            ConfigManager.load_config(config_path)
            assert ConfigManager.is_configured()
            assert len(ConfigManager.list_accounts()) == 1
            assert not ConfigManager.has_explicit_clusters()
        finally:
            os.unlink(config_path)

    def test_get_account(self):
        """Test getting account by ID."""
        config_data = {
            'accounts': [
                {
                    'account_id': '123456789012',
                    'regions': ['us-east-1'],
                }
            ],
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            config_path = f.name

        try:
            ConfigManager.load_config(config_path)
            account = ConfigManager.get_account('123456789012')
            assert account is not None
            assert account.account_id == '123456789012'

            # Non-existent account
            assert ConfigManager.get_account('999999999999') is None
        finally:
            os.unlink(config_path)

    def test_get_cluster(self):
        """Test getting cluster by name."""
        config_data = {
            'accounts': [
                {
                    'account_id': '123456789012',
                    'regions': ['us-east-1'],
                }
            ],
            'clusters': [
                {
                    'name': 'my-cluster',
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
            cluster = ConfigManager.get_cluster('my-cluster')
            assert cluster is not None
            assert cluster.name == 'my-cluster'

            # Non-existent cluster
            assert ConfigManager.get_cluster('non-existent') is None
        finally:
            os.unlink(config_path)

    def test_list_account_region_combinations(self):
        """Test listing all account/region combinations."""
        config_data = {
            'accounts': [
                {
                    'account_id': '123456789012',
                    'regions': ['us-east-1', 'us-west-2'],
                },
                {
                    'account_id': '987654321098',
                    'regions': ['eu-west-1'],
                },
            ],
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            config_path = f.name

        try:
            ConfigManager.load_config(config_path)
            combinations = ConfigManager.list_account_region_combinations()
            assert len(combinations) == 3
            assert ('123456789012', 'us-east-1') in combinations
            assert ('123456789012', 'us-west-2') in combinations
            assert ('987654321098', 'eu-west-1') in combinations
        finally:
            os.unlink(config_path)

    def test_has_explicit_clusters(self):
        """Test checking for explicit clusters."""
        # Config without clusters
        config_data = {
            'accounts': [
                {
                    'account_id': '123456789012',
                    'regions': ['us-east-1'],
                }
            ],
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            config_path = f.name

        try:
            ConfigManager.load_config(config_path)
            assert not ConfigManager.has_explicit_clusters()
        finally:
            os.unlink(config_path)

        # Config with clusters
        config_data_with_clusters = {
            'accounts': [
                {
                    'account_id': '123456789012',
                    'regions': ['us-east-1'],
                }
            ],
            'clusters': [
                {
                    'name': 'my-cluster',
                    'region': 'us-east-1',
                    'account_id': '123456789012',
                }
            ],
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data_with_clusters, f)
            config_path = f.name

        try:
            ConfigManager.reset()
            ConfigManager.load_config(config_path)
            assert ConfigManager.has_explicit_clusters()
        finally:
            os.unlink(config_path)

    def test_get_account_for_cluster(self):
        """Test getting account for a specific cluster."""
        config_data = {
            'accounts': [
                {
                    'account_id': '123456789012',
                    'regions': ['us-east-1'],
                }
            ],
            'clusters': [
                {
                    'name': 'my-cluster',
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
            account = ConfigManager.get_account_for_cluster('my-cluster')
            assert account is not None
            assert account.account_id == '123456789012'
        finally:
            os.unlink(config_path)
