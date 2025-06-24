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

"""AWS Labs RDS Control Plane MCP Server implementation for Amazon RDS databases."""

import argparse
import asyncio
import os
import sys
from typing import Any, Dict, List, Optional

import boto3
from botocore.config import Config
from loguru import logger
from mcp.server.fastmcp import Context, FastMCP

from .constants import MCP_SERVER_VERSION
from .resources import (
    get_cluster_list_resource,
    get_cluster_detail_resource,
    get_instance_list_resource,
    get_instance_detail_resource,
)

logger.remove()
logger.add(sys.stderr, level='INFO')

# global variables
_rds_client = None
_readonly = True
_region = None


def get_rds_client():
    """Get or create RDS client."""
    global _rds_client, _region
    if _rds_client is None:
        config = Config(
            region_name=_region,
            retries={'max_attempts': 3, 'mode': 'adaptive'},
        )
        _rds_client = boto3.client('rds', config=config)
    return _rds_client


mcp = FastMCP(
    'awslabs.rds-control-plane-mcp-server',
    version=MCP_SERVER_VERSION,
    instructions="""This server provides access to Amazon RDS database instances and clusters.

Key capabilities:
- View detailed information about RDS DB instances
- View detailed information about RDS DB clusters
- Access connection endpoints, configuration, and status information

The server operates in read-only mode by default, providing safe access to RDS resources.""",
    dependencies=['boto3', 'botocore', 'pydantic', 'loguru'],
)

# ===== RESOURCES =====
# read-only access to RDS data

@mcp.resource(uri='aws-rds://db-cluster', name='DB Clusters', mime_type='application/json')
async def list_clusters_resource() -> str:
    """List all available Amazon RDS clusters in your account.
    
    <use_case>
    Use this resource to discover all available RDS database clusters in your AWS account.
    </use_case>
    
    <important_notes>
    1. The response provides essential information about each cluster
    2. Cluster identifiers returned can be used with the db-cluster/{cluster_id} resource
    3. Clusters are filtered to the AWS region specified in your environment configuration
    </important_notes>
    
    ## Response structure
    Returns a JSON document containing:
    - `clusters`: Array of DB cluster objects
    - `count`: Number of clusters found
    - `resource_uri`: Base URI for accessing clusters
    """
    return await get_cluster_list_resource(get_rds_client())


@mcp.resource(
    uri='aws-rds://db-cluster/{cluster_id}',
    name='DB Cluster Details',
    mime_type='application/json',
)
async def get_cluster_resource(cluster_id: str) -> str:
    """Get detailed information about a specific Amazon RDS cluster.
    
    <use_case>
    Use this resource to retrieve comprehensive details about a specific RDS database cluster
    identified by its cluster ID.
    </use_case>
    
    <important_notes>
    1. The cluster ID must exist in your AWS account and region
    2. The response contains full configuration details about the specified cluster
    3. Error responses will be returned if the cluster doesn't exist
    </important_notes>
    
    ## Response structure
    Returns a JSON document containing detailed cluster information including:
    - Status, engine type, and version
    - Endpoints for connection
    - Backup configuration
    - Member instances
    - Security groups
    """
    return await get_cluster_detail_resource(cluster_id, get_rds_client())


@mcp.resource(uri='aws-rds://db-instance', name='DB Instances', mime_type='application/json')
async def list_instances_resource() -> str:
    """List all available Amazon RDS instances in your account.
    
    <use_case>
    Use this resource to discover all available RDS database instances in your AWS account.
    </use_case>
    
    <important_notes>
    1. The response provides essential information about each instance
    2. Instance identifiers returned can be used with the db-instance/{instance_id} resource
    3. Instances are filtered to the AWS region specified in your environment configuration
    </important_notes>
    
    ## Response structure
    Returns a JSON document containing:
    - `instances`: Array of DB instance objects
    - `count`: Number of instances found
    - `resource_uri`: Base URI for accessing instances
    """
    return await get_instance_list_resource(get_rds_client())


@mcp.resource(
    uri='aws-rds://db-instance/{instance_id}',
    name='DB Instance Details',
    mime_type='application/json',
)
async def get_instance_resource(instance_id: str) -> str:
    """Get detailed information about a specific Amazon RDS instance.
    
    <use_case>
    Use this resource to retrieve comprehensive details about a specific RDS database instance
    identified by its instance ID.
    </use_case>
    
    <important_notes>
    1. The instance ID must exist in your AWS account and region
    2. The response contains full configuration details about the specified instance
    3. Error responses will be returned if the instance doesn't exist
    </important_notes>
    
    ## Response structure
    Returns a JSON document containing detailed instance information including:
    - Status, engine type, and version
    - Instance class and storage configuration
    - Endpoint for connection
    - Availability zone and Multi-AZ setting
    - Security groups
    """
    return await get_instance_detail_resource(instance_id, get_rds_client())


def main():
    """Run the MCP server with CLI argument support."""
    global _readonly, _region
    
    parser = argparse.ArgumentParser(
        description='An AWS Labs MCP server for Amazon RDS control plane operations'
    )
    parser.add_argument('--port', type=int, default=8888, help='Port to run the server on')
    parser.add_argument(
        '--region',
        type=str,
        required=True,
        help='AWS region for RDS operations'
    )
    parser.add_argument(
        '--readonly',
        type=str,
        default='true',
        choices=['true', 'false'],
        help='Whether to run in read-only mode (default: true)'
    )
    parser.add_argument(
        '--profile',
        type=str,
        help='AWS profile to use for credentials'
    )

    args = parser.parse_args()

    # global configuration
    _readonly = args.readonly.lower() == 'true'
    _region = args.region
    
    # AWS profile if provided
    if args.profile:
        os.environ['AWS_PROFILE'] = args.profile
    
    # log configuration
    logger.info(f"Starting RDS Control Plane MCP Server v{MCP_SERVER_VERSION}")
    logger.info(f"Region: {_region}")
    logger.info(f"Read-only mode: {_readonly}")
    if args.profile:
        logger.info(f"AWS Profile: {args.profile}")

    if args.port:
        mcp.settings.port = args.port
        
    # default streamable HTTP transport
    mcp.run()


if __name__ == '__main__':
    main()
