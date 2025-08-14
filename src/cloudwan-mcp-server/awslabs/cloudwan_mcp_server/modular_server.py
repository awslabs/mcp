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

"""Modular AWS CloudWAN MCP Server implementation demonstrating the modularization strategy."""

import sys
import threading
from functools import lru_cache

import boto3
import loguru
from botocore.config import Config
from mcp.server.fastmcp import FastMCP
from pydantic_settings import BaseSettings, SettingsConfigDict

from .tools import register_all_tools

try:
    from .config_manager import config_persistence
except ImportError:
    # Fallback for missing config_manager
    config_persistence = None


class AWSConfig(BaseSettings):
    """Secure AWS configuration using pydantic-settings for environment variable validation."""

    default_region: str = "us-east-1"
    profile: str | None = None

    model_config = SettingsConfigDict(
        env_prefix="AWS_", env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )


# Global secure config instance
aws_config = AWSConfig()

# Thread safety for client caching
_client_lock = threading.Lock()

# Set up logging
logger = loguru.logger
logger.remove()
logger.add(sys.stderr, level="DEBUG")

# Initialize FastMCP server following AWS Labs pattern
mcp = FastMCP(
    "AWS CloudWAN MCP server (Modular) - Advanced network analysis and troubleshooting tools for AWS CloudWAN",
    dependencies=[
        "loguru",
        "boto3",
    ],
)


# AWS client cache with thread-safe LRU implementation (reused from original)
@lru_cache(maxsize=10)
def _create_client(service: str, region: str, profile: str | None = None, custom_endpoints: str | None = None) -> boto3.client:
    """Thread-safe client creation helper."""
    import json
    
    config = Config(region_name=region, retries={"max_attempts": 3, "mode": "adaptive"}, max_pool_connections=10)

    # Handle custom endpoints from parameter (for cache key inclusion)
    endpoint_url = None
    if custom_endpoints:
        try:
            endpoints_dict = json.loads(custom_endpoints)
            endpoint_url = endpoints_dict.get(service)
        except (json.JSONDecodeError, AttributeError):
            pass  # Invalid JSON or not a dict, ignore

    if profile:
        session = boto3.Session(profile_name=profile)
        return session.client(service, config=config, region_name=region, endpoint_url=endpoint_url)
    return boto3.client(service, config=config, region_name=region, endpoint_url=endpoint_url)


def get_aws_client(service: str, region: str | None = None) -> boto3.client:
    """Get AWS client with caching and standard configuration."""
    import os
    
    region = region or aws_config.default_region
    profile = aws_config.profile
    custom_endpoints = os.getenv("CLOUDWAN_AWS_CUSTOM_ENDPOINTS")

    # Thread-safe client creation with lock
    with _client_lock:
        return _create_client(service, region, profile, custom_endpoints)


def main() -> None:
    """Run the modular MCP server."""
    logger.info("Starting AWS CloudWAN MCP Server (Modular Architecture)...")

    # Validate environment
    region = aws_config.default_region
    if not region:
        logger.error("AWS_DEFAULT_REGION environment variable is required")
        sys.exit(1)

    profile = aws_config.profile or "default"
    logger.info(f"AWS Region: {region}")
    logger.info(f"AWS Profile: {profile}")

    # Register all modular tools
    try:
        logger.info("Registering modular tool architecture...")
        tool_instances = register_all_tools(mcp)
        logger.info(f"Successfully registered {len(tool_instances)} tool modules:")
        for i, tool_instance in enumerate(tool_instances, 1):
            tool_name = tool_instance.__class__.__name__
            logger.info(f"  {i}. {tool_name}")
        
        logger.info("Modular tool registration complete. Starting MCP server...")
        
    except Exception as e:
        logger.error(f"Failed to register modular tools: {e}")
        sys.exit(1)

    try:
        mcp.run()
    except KeyboardInterrupt:
        logger.info("Server shutdown requested")
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()