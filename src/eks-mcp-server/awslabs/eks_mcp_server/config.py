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

"""Configuration management for multi-cluster support.

This module provides configuration loading and validation for managing
EKS clusters across multiple AWS regions and accounts.

Configuration File Format:
    {
        "accounts": [
            {
                "account_id": "111111111111",
                "role_arn": "arn:aws:iam::111111111111:role/CustomRole",
                "external_id": "my-external-id",
                "regions": ["us-east-1", "us-west-2"]
            },
            {
                "account_id": "222222222222",
                "regions": ["eu-west-1"]
            }
        ],
        "clusters": [
            {
                "name": "prod-cluster",
                "region": "us-east-1",
                "account_id": "111111111111",
                "description": "Production cluster"
            }
        ]
    }

    Notes:
    - accounts: Required list defining which account/region combinations can be managed
    - role_arn: Optional at account level, if not specified defaults to "arn:aws:iam::{account_id}:role/McpEksOpsRole"
    - profile: Optional alternative to role_arn for authentication (mutually exclusive with role_arn)
    - external_id: Optional, used with role_arn for role assumption
    - regions: Required list of regions for each account
    - clusters: Optional, if not provided, all clusters will be discovered in configured accounts/regions
"""

import json
import os
import yaml
from loguru import logger
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional


class AccountConfig(BaseModel):
    """Configuration for an AWS account and its regions.

    Attributes:
        account_id: AWS account ID
        role_arn: IAM role ARN for cross-account access (optional, defaults to McpEksOpsRole)
        external_id: External ID for role assumption (optional, security best practice)
        profile: AWS CLI profile name for cross-account access (optional, alternative to role_arn)
        regions: List of region names to manage in this account
    """

    account_id: str = Field(..., description='AWS account ID')
    role_arn: Optional[str] = Field(
        None,
        description='IAM role ARN for cross-account access (defaults to McpEksOpsRole if not specified)',
    )
    external_id: Optional[str] = Field(
        None, description='External ID for role assumption (security best practice)'
    )
    profile: Optional[str] = Field(
        None, description='AWS CLI profile name for cross-account access'
    )
    regions: List[str] = Field(..., description='List of region names to manage in this account')

    @field_validator('account_id')
    @classmethod
    def validate_account_id(cls, v: str) -> str:
        """Validate AWS account ID format."""
        if not v or not isinstance(v, str):
            raise ValueError('Account ID must be a non-empty string')
        if not v.isdigit() or len(v) != 12:
            raise ValueError(f'Invalid AWS account ID: {v}. Must be a 12-digit number')
        return v

    @field_validator('role_arn')
    @classmethod
    def validate_role_arn(cls, v: Optional[str]) -> Optional[str]:
        """Validate IAM role ARN format."""
        if v and not v.startswith('arn:aws:iam::'):
            raise ValueError(f"Invalid IAM role ARN format: {v}. Must start with 'arn:aws:iam::'")
        return v

    @field_validator('regions')
    @classmethod
    def validate_regions(cls, v: List[str]) -> List[str]:
        """Validate that at least one region is specified and all regions are valid."""
        if not v or len(v) == 0:
            raise ValueError('At least one region must be specified for each account')

        # Validate each region format
        for region in v:
            if not region or not isinstance(region, str):
                raise ValueError(f'Region must be a non-empty string: {region}')
            # Basic validation - AWS regions follow pattern like us-east-1, eu-west-1, etc.
            parts = region.split('-')
            if len(parts) < 3:
                raise ValueError(
                    f"Invalid AWS region format: {region}. Expected format like 'us-east-1'"
                )

        # Check for duplicate region names
        duplicates = [name for name in v if v.count(name) > 1]
        if duplicates:
            raise ValueError(f'Duplicate region names found in account: {list(set(duplicates))}')

        return v

    def get_effective_role_arn(self) -> str:
        """Get the effective role ARN, using default if not specified.

        Returns:
            The configured role_arn, or the default McpEksOpsRole if not specified
        """
        if self.role_arn:
            return self.role_arn
        return f'arn:aws:iam::{self.account_id}:role/McpEksOpsRole'

    def get_access_method(self) -> str:
        """Determine the access method for this account.

        Returns:
            'role_assumption' if role_arn is specified or will use default,
            'profile' if profile is specified,
            'default' otherwise
        """
        if self.profile:
            return 'profile'
        else:
            return 'role_assumption'


class ClusterConfig(BaseModel):
    """Configuration for a single EKS cluster.

    Attributes:
        name: EKS cluster name
        region: AWS region where the cluster is located
        account_id: AWS account ID
        description: Human-readable description of the cluster
        validated: Whether the cluster has been validated to exist (used for caching)
    """

    name: str = Field(..., description='EKS cluster name')
    region: str = Field(..., description='AWS region where the cluster is located')
    account_id: str = Field(..., description='AWS account ID')
    description: Optional[str] = Field(
        None, description='Human-readable description of the cluster'
    )
    validated: bool = Field(
        default=False, description='Whether the cluster has been validated to exist'
    )

    @field_validator('account_id')
    @classmethod
    def validate_account_id(cls, v: str) -> str:
        """Validate AWS account ID format."""
        if not v or not isinstance(v, str):
            raise ValueError('Account ID must be a non-empty string')
        if not v.isdigit() or len(v) != 12:
            raise ValueError(f'Invalid AWS account ID: {v}. Must be a 12-digit number')
        return v

    @field_validator('region')
    @classmethod
    def validate_region(cls, v: str) -> str:
        """Validate AWS region format."""
        if not v or not isinstance(v, str):
            raise ValueError('Region must be a non-empty string')
        # Basic validation - AWS regions follow pattern like us-east-1, eu-west-1, etc.
        parts = v.split('-')
        if len(parts) < 3:
            raise ValueError(f"Invalid AWS region format: {v}. Expected format like 'us-east-1'")
        return v


class ClustersConfig(BaseModel):
    """Root configuration containing accounts and optionally clusters.

    Attributes:
        accounts: List of account configurations with their regions
        clusters: Optional list of specific cluster configurations
    """

    accounts: List[AccountConfig] = Field(..., description='List of AWS account configurations')
    clusters: Optional[List[ClusterConfig]] = Field(
        default=None, description='Optional list of specific EKS cluster configurations'
    )

    @field_validator('accounts')
    @classmethod
    def validate_accounts(cls, v: List[AccountConfig]) -> List[AccountConfig]:
        """Validate accounts configuration."""
        if not v or len(v) == 0:
            raise ValueError('At least one account must be configured')
        # Check for duplicate account IDs
        account_ids = [a.account_id for a in v]
        duplicates = [aid for aid in account_ids if account_ids.count(aid) > 1]
        if duplicates:
            raise ValueError(f'Duplicate account IDs found: {list(set(duplicates))}')
        return v

    @field_validator('clusters')
    @classmethod
    def validate_clusters(cls, v: Optional[List[ClusterConfig]]) -> Optional[List[ClusterConfig]]:
        """Validate that all cluster names are unique if clusters are provided."""
        if v is None:
            return v
        names = [c.name for c in v]
        duplicates = [name for name in names if names.count(name) > 1]
        if duplicates:
            raise ValueError(f'Duplicate cluster names found: {list(set(duplicates))}')
        return v

    def validate_cluster_references(self) -> None:
        """Validate that all cluster configurations reference valid account/region combinations."""
        if not self.clusters:
            return

        # Build a set of valid (account_id, region) combinations
        valid_combinations = set()
        for account in self.accounts:
            for region in account.regions:
                valid_combinations.add((account.account_id, region))

        # Check each cluster
        for cluster in self.clusters:
            combo = (cluster.account_id, cluster.region)
            if combo not in valid_combinations:
                raise ValueError(
                    f"Cluster '{cluster.name}' references account_id='{cluster.account_id}' "
                    f"and region='{cluster.region}' which is not in the configured accounts/regions"
                )


class ConfigManager:
    """Singleton manager for cluster configuration.

    This class provides a centralized way to load, store, and access
    cluster configurations. It implements the singleton pattern to ensure
    configuration is loaded once and accessible throughout the application.
    """

    _instance = None
    _config: Optional[ClustersConfig] = None
    _config_path: Optional[str] = None
    _discovered_clusters: Optional[List[ClusterConfig]] = None

    def __new__(cls):
        """Ensure only one instance of ConfigManager exists."""
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
        return cls._instance

    @classmethod
    def load_config(cls, config_path: str) -> ClustersConfig:
        """Load and validate cluster configuration from JSON or YAML file.

        The file format is detected by extension:
        - .json files are parsed as JSON
        - .yaml or .yml files are parsed as YAML

        Args:
            config_path: Path to the configuration file (JSON or YAML)

        Returns:
            Validated ClustersConfig object

        Raises:
            FileNotFoundError: If the configuration file doesn't exist
            json.JSONDecodeError: If JSON file contains invalid JSON
            yaml.YAMLError: If YAML file contains invalid YAML
            ValueError: If the configuration is invalid or file format unsupported
        """
        # Validate path
        if not os.path.isabs(config_path):
            config_path = os.path.abspath(config_path)

        if not os.path.exists(config_path):
            raise FileNotFoundError(f'Configuration file not found: {config_path}')

        # Detect file format by extension
        _, ext = os.path.splitext(config_path)
        ext = ext.lower()

        logger.info(f'Loading cluster configuration from: {config_path}')

        with open(config_path, 'r') as f:
            if ext == '.json':
                try:
                    data = json.load(f)
                except json.JSONDecodeError as e:
                    raise json.JSONDecodeError(
                        f'Invalid JSON in configuration file: {e.msg}',
                        e.doc,
                        e.pos,
                    )
            elif ext in ('.yaml', '.yml'):
                try:
                    data = yaml.safe_load(f)
                except yaml.YAMLError as e:
                    raise ValueError(f'Invalid YAML in configuration file: {e}')
            else:
                raise ValueError(
                    f'Unsupported configuration file format: {ext}. Use .json, .yaml, or .yml'
                )

        cls._config = ClustersConfig(**data)

        # Validate cluster references if clusters are provided
        cls._config.validate_cluster_references()

        cls._config_path = config_path

        # Log configuration summary
        logger.info(f'Loaded configuration for {len(cls._config.accounts)} accounts')
        for account in cls._config.accounts:
            logger.debug(
                f'  - Account {account.account_id}: regions={account.regions}, '
                f'access={account.get_access_method()}'
            )

        if cls._config.clusters:
            logger.info(f'Loaded configuration for {len(cls._config.clusters)} specific clusters')
            for cluster in cls._config.clusters:
                logger.debug(f'  - {cluster.name} ({cluster.region}, {cluster.account_id})')
        else:
            logger.info('No specific clusters configured - discovery mode enabled')

        return cls._config

    @classmethod
    def get_config(cls) -> Optional[ClustersConfig]:
        """Get the loaded configuration.

        Returns:
            The loaded ClustersConfig, or None if not loaded
        """
        return cls._config

    @classmethod
    def get_account(cls, account_id: str) -> Optional[AccountConfig]:
        """Get configuration for a specific account by ID.

        Args:
            account_id: AWS account ID to find

        Returns:
            AccountConfig for the specified account, or None if not found
        """
        if not cls._config:
            return None
        for account in cls._config.accounts:
            if account.account_id == account_id:
                return account
        return None

    @classmethod
    def get_account_for_cluster(cls, cluster_name: str) -> Optional[AccountConfig]:
        """Get the account configuration for a specific cluster.

        Args:
            cluster_name: Name of the cluster

        Returns:
            AccountConfig for the cluster's account, or None if not found
        """
        cluster = cls.get_cluster(cluster_name)
        if not cluster:
            return None
        return cls.get_account(cluster.account_id)

    @classmethod
    def list_accounts(cls) -> List[AccountConfig]:
        """List all configured accounts.

        Returns:
            List of all AccountConfig objects, or empty list if no config loaded
        """
        if not cls._config:
            return []
        return cls._config.accounts

    @classmethod
    def list_account_region_combinations(cls) -> List[tuple[str, str]]:
        """List all configured (account_id, region) combinations.

        Returns:
            List of tuples containing (account_id, region_name)
        """
        if not cls._config:
            return []
        combinations = []
        for account in cls._config.accounts:
            for region in account.regions:
                combinations.append((account.account_id, region))
        return combinations

    @classmethod
    def get_cluster(cls, cluster_name: str) -> Optional[ClusterConfig]:
        """Get configuration for a specific cluster by name.

        Searches both explicit and discovered clusters.

        Args:
            cluster_name: Name of the cluster to find

        Returns:
            ClusterConfig for the specified cluster, or None if not found
        """
        if not cls._config:
            return None

        # First check explicit clusters
        if cls._config.clusters:
            for cluster in cls._config.clusters:
                if cluster.name == cluster_name:
                    return cluster

        # Then check discovered clusters
        for cluster in cls.get_discovered_clusters():
            if cluster.name == cluster_name:
                return cluster

        return None

    @classmethod
    def list_clusters(cls) -> List[ClusterConfig]:
        """List all configured or discovered clusters.

        Returns:
            List of all ClusterConfig objects (explicit or discovered), or empty list if none available
        """
        if not cls._config:
            return []
        # Return explicit clusters if configured, otherwise return discovered clusters
        if cls._config.clusters:
            return cls._config.clusters
        return cls.get_discovered_clusters()

    @classmethod
    def get_cluster_names(cls) -> List[str]:
        """Get list of all configured cluster names.

        Returns:
            List of cluster names, or empty list if no clusters configured
        """
        return [c.name for c in cls.list_clusters()]

    @classmethod
    def has_explicit_clusters(cls) -> bool:
        """Check if explicit clusters are configured.

        Returns:
            True if clusters are explicitly configured, False if in discovery mode
        """
        return (
            cls._config is not None
            and cls._config.clusters is not None
            and len(cls._config.clusters) > 0
        )

    @classmethod
    def is_configured(cls) -> bool:
        """Check if configuration has been loaded.

        Returns:
            True if configuration is loaded, False otherwise
        """
        return cls._config is not None

    @classmethod
    def reset(cls) -> None:
        """Reset the configuration manager (mainly for testing).

        Clears the loaded configuration and config path.
        """
        cls._config = None
        cls._config_path = None
        cls._discovered_clusters = None

    @classmethod
    def set_discovered_clusters(cls, clusters: List[ClusterConfig]) -> None:
        """Set the list of discovered clusters.

        This is called during startup when no explicit clusters are configured
        and automatic discovery is enabled.

        Args:
            clusters: List of discovered ClusterConfig objects
        """
        cls._discovered_clusters = clusters
        logger.info(f'Stored {len(clusters)} discovered clusters')

    @classmethod
    def get_discovered_clusters(cls) -> List[ClusterConfig]:
        """Get the list of discovered clusters.

        Returns:
            List of discovered ClusterConfig objects, or empty list if none discovered
        """
        return cls._discovered_clusters if cls._discovered_clusters is not None else []

    @classmethod
    def has_discovered_clusters(cls) -> bool:
        """Check if clusters were discovered at startup.

        Returns:
            True if clusters were discovered, False otherwise
        """
        return cls._discovered_clusters is not None and len(cls._discovered_clusters) > 0
