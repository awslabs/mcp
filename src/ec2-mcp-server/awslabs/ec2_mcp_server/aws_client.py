#!/usr/bin/env python3
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
"""
AWS Client management for EC2 MCP Server.
"""

import os
from typing import Any, Dict, Optional

import boto3
from botocore.config import Config
from loguru import logger


class AwsClientManager:
    """Manages AWS EC2 client creation and configuration."""
    
    _client_cache: Dict[str, Any] = {}
    
    @classmethod
    def get_ec2_client(cls, region: Optional[str] = None) -> Any:
        """
        Get an EC2 client with proper configuration.
        
        Args:
            region: AWS region name. If not provided, uses environment variables.
            
        Returns:
            boto3 EC2 client
        """
        client_region = region or cls._get_region()
        cache_key = f"ec2_{client_region}"
        
        if cache_key not in cls._client_cache:
            logger.info(f"Creating new EC2 client for region: {client_region}")
            
            config = Config(
                user_agent_extra='awslabs-ec2-mcp-server/1.0.0',
                retries={'max_attempts': 3, 'mode': 'standard'}
            )
            
            cls._client_cache[cache_key] = boto3.client(
                'ec2',
                region_name=client_region,
                config=config
            )
        
        return cls._client_cache[cache_key]
    
    @classmethod
    def _get_region(cls) -> str:
        """Get AWS region from environment variables."""
        return (
            os.environ.get('AWS_REGION') or 
            os.environ.get('AWS_DEFAULT_REGION') or 
            'us-east-1'
        )
    
    @classmethod
    def clear_cache(cls) -> None:
        """Clear the client cache. Useful for testing."""
        cls._client_cache.clear()


def get_ec2_client(region: Optional[str] = None) -> Any:
    """Convenience function to get an EC2 client."""
    return AwsClientManager.get_ec2_client(region)