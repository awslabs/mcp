#!/usr/bin/env python3
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""AWS Service Factory - Abstraction layer for AWS SDK with dependency injection."""

from typing import Any, Dict, Optional, Protocol
from functools import lru_cache
import boto3
from botocore.config import Config
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


class AWSClient(Protocol):
    """Protocol for AWS service clients."""
    
    def describe_vpcs(self, **kwargs) -> Dict[str, Any]:
        """Describe VPCs."""
        ...
    
    def describe_subnets(self, **kwargs) -> Dict[str, Any]:
        """Describe subnets."""
        ...
    
    # Add other required methods as needed


@dataclass
class AWSConfig:
    """Configuration for AWS services."""
    region: Optional[str] = None
    profile_name: Optional[str] = None
    role_arn: Optional[str] = None
    max_retries: int = 3
    timeout: int = 30
    
    def to_boto_config(self) -> Config:
        """Convert to boto3 Config object."""
        return Config(
            region_name=self.region,
            retries={'max_attempts': self.max_retries},
            connect_timeout=self.timeout,
            read_timeout=self.timeout
        )


class AWSServiceFactory:
    """Factory for creating AWS service clients with caching and mocking support."""
    
    def __init__(self, config: Optional[AWSConfig] = None):
        self.config = config or AWSConfig()
        self._clients = {}
        self._mock_clients = {}
        self._mock_mode = False
    
    def enable_mock_mode(self):
        """Enable mock mode for testing."""
        self._mock_mode = True
    
    def disable_mock_mode(self):
        """Disable mock mode."""
        self._mock_mode = False
    
    def register_mock_client(self, service: str, region: str, mock_client: Any):
        """Register a mock client for testing."""
        key = f"{service}:{region}"
        self._mock_clients[key] = mock_client
    
    @lru_cache(maxsize=32)
    def get_client(self, service: str, region: Optional[str] = None,
                   profile_name: Optional[str] = None) -> Any:
        """Get or create an AWS service client with caching."""
        region = region or self.config.region or 'us-east-1'
        profile_name = profile_name or self.config.profile_name
        
        # Return mock client if in mock mode
        if self._mock_mode:
            key = f"{service}:{region}"
            if key in self._mock_clients:
                return self._mock_clients[key]
            # Create a default mock if not registered
            from unittest.mock import MagicMock
            mock = MagicMock()
            self._mock_clients[key] = mock
            return mock
        
        # Create cache key
        cache_key = f"{service}:{region}:{profile_name}"
        
        # Return cached client if exists
        if cache_key in self._clients:
            return self._clients[cache_key]
        
        # Create new client
        session_kwargs = {}
        if profile_name:
            session_kwargs['profile_name'] = profile_name
        
        try:
            session = boto3.Session(**session_kwargs)
            
            # Handle role assumption if configured
            if self.config.role_arn:
                sts = session.client('sts')
                assumed_role = sts.assume_role(
                    RoleArn=self.config.role_arn,
                    RoleSessionName='aws-network-mcp-server'
                )
                
                # Create new session with assumed role credentials
                session = boto3.Session(
                    aws_access_key_id=assumed_role['Credentials']['AccessKeyId'],
                    aws_secret_access_key=assumed_role['Credentials']['SecretAccessKey'],
                    aws_session_token=assumed_role['Credentials']['SessionToken']
                )
            
            # Create client with config
            client = session.client(
                service,
                region_name=region,
                config=self.config.to_boto_config()
            )
            
            # Cache the client
            self._clients[cache_key] = client
            logger.debug(f"Created {service} client for region {region}")
            
            return client
            
        except Exception as e:
            logger.error(f"Failed to create {service} client: {e}")
            raise
    
    def get_resource(self, service: str, region: Optional[str] = None,
                     profile_name: Optional[str] = None) -> Any:
        """Get or create an AWS service resource."""
        region = region or self.config.region or 'us-east-1'
        profile_name = profile_name or self.config.profile_name
        
        session_kwargs = {}
        if profile_name:
            session_kwargs['profile_name'] = profile_name
        
        session = boto3.Session(**session_kwargs)
        return session.resource(service, region_name=region)
    
    def clear_cache(self):
        """Clear the client cache."""
        self._clients.clear()
        self.get_client.cache_clear()
        logger.debug("Cleared AWS client cache")
    
    def get_all_regions(self, service: str = 'ec2') -> list:
        """Get all available regions for a service."""
        client = self.get_client('ec2', 'us-east-1')
        response = client.describe_regions()
        return [r['RegionName'] for r in response['Regions']]


# Global factory instance
_factory: Optional[AWSServiceFactory] = None


def get_factory(config: Optional[AWSConfig] = None) -> AWSServiceFactory:
    """Get or create the global AWS service factory."""
    global _factory
    if _factory is None:
        _factory = AWSServiceFactory(config)
    return _factory


def configure_aws(region: Optional[str] = None,
                  profile_name: Optional[str] = None,
                  role_arn: Optional[str] = None,
                  **kwargs) -> AWSServiceFactory:
    """Configure the global AWS service factory."""
    config = AWSConfig(
        region=region,
        profile_name=profile_name,
        role_arn=role_arn,
        **kwargs
    )
    return get_factory(config)


class AWSServiceProxy:
    """Proxy for AWS services with automatic error handling and retries."""
    
    def __init__(self, factory: AWSServiceFactory, service: str, region: str):
        self.factory = factory
        self.service = service
        self.region = region
        self._client = None
    
    @property
    def client(self):
        """Lazy load the actual client."""
        if self._client is None:
            self._client = self.factory.get_client(self.service, self.region)
        return self._client
    
    def __getattr__(self, name):
        """Proxy method calls to the actual client."""
        return getattr(self.client, name)