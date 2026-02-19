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
        "clusters": [
            {
                "name": "prod-cluster",
                "region": "us-east-1",
                "account_id": "111111111111",
                "role_arn": "arn:aws:iam::111111111111:role/EKSAccessRole",
                "external_id": "my-external-id",
                "description": "Production cluster"
            },
            {
                "name": "dev-cluster",
                "region": "us-west-2",
                "profile": "dev-account",
                "description": "Development cluster"
            }
        ]
    }
"""

import json
import os
import yaml
from loguru import logger
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional


class ClusterConfig(BaseModel):
    """Configuration for a single EKS cluster.

    Attributes:
        name: EKS cluster name
        region: AWS region where the cluster is located
        account_id: AWS account ID (optional, for documentation/validation)
        role_arn: IAM role ARN for cross-account access via role assumption
        external_id: External ID for role assumption (security best practice)
        profile: AWS CLI profile name for cross-account access
        description: Human-readable description of the cluster
    """

    name: str = Field(..., description='EKS cluster name')
    region: str = Field(..., description='AWS region where the cluster is located')
    account_id: Optional[str] = Field(None, description='AWS account ID')
    role_arn: Optional[str] = Field(
        None, description='IAM role ARN for cross-account access via role assumption'
    )
    external_id: Optional[str] = Field(
        None, description='External ID for role assumption (security best practice)'
    )
    profile: Optional[str] = Field(
        None, description='AWS CLI profile name for cross-account access'
    )
    description: Optional[str] = Field(
        None, description='Human-readable description of the cluster'
    )

    @field_validator('role_arn')
    @classmethod
    def validate_role_arn(cls, v: Optional[str]) -> Optional[str]:
        """Validate IAM role ARN format."""
        if v and not v.startswith('arn:aws:iam::'):
            raise ValueError(f"Invalid IAM role ARN format: {v}. Must start with 'arn:aws:iam::'")
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

    def get_access_method(self) -> str:
        """Determine the access method for this cluster.

        Returns:
            'role_assumption' if role_arn is specified,
            'profile' if profile is specified,
            'default' otherwise
        """
        if self.role_arn:
            return 'role_assumption'
        elif self.profile:
            return 'profile'
        else:
            return 'default'


class ClustersConfig(BaseModel):
    """Root configuration containing all clusters.

    Attributes:
        clusters: List of cluster configurations
    """

    clusters: List[ClusterConfig] = Field(..., description='List of EKS cluster configurations')

    @field_validator('clusters')
    @classmethod
    def validate_unique_names(cls, v: List[ClusterConfig]) -> List[ClusterConfig]:
        """Validate that all cluster names are unique."""
        names = [c.name for c in v]
        duplicates = [name for name in names if names.count(name) > 1]
        if duplicates:
            raise ValueError(f'Duplicate cluster names found: {list(set(duplicates))}')
        return v


class ConfigManager:
    """Singleton manager for cluster configuration.

    This class provides a centralized way to load, store, and access
    cluster configurations. It implements the singleton pattern to ensure
    configuration is loaded once and accessible throughout the application.
    """

    _instance = None
    _config: Optional[ClustersConfig] = None
    _config_path: Optional[str] = None

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
        cls._config_path = config_path

        logger.info(f'Loaded configuration for {len(cls._config.clusters)} clusters')
        for cluster in cls._config.clusters:
            logger.debug(
                f'  - {cluster.name} ({cluster.region}) - access: {cluster.get_access_method()}'
            )

        return cls._config

    @classmethod
    def get_config(cls) -> Optional[ClustersConfig]:
        """Get the loaded configuration.

        Returns:
            The loaded ClustersConfig, or None if not loaded
        """
        return cls._config

    @classmethod
    def get_cluster(cls, cluster_name: str) -> Optional[ClusterConfig]:
        """Get configuration for a specific cluster by name.

        Args:
            cluster_name: Name of the cluster to find

        Returns:
            ClusterConfig for the specified cluster, or None if not found
        """
        if not cls._config:
            return None
        for cluster in cls._config.clusters:
            if cluster.name == cluster_name:
                return cluster
        return None

    @classmethod
    def list_clusters(cls) -> List[ClusterConfig]:
        """List all configured clusters.

        Returns:
            List of all ClusterConfig objects, or empty list if no config loaded
        """
        if not cls._config:
            return []
        return cls._config.clusters

    @classmethod
    def get_cluster_names(cls) -> List[str]:
        """Get list of all configured cluster names.

        Returns:
            List of cluster names
        """
        return [c.name for c in cls.list_clusters()]

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
