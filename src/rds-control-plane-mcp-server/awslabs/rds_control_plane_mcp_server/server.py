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

"""awslabs rds-control-plane MCP Server implementation."""

import argparse
import os
import sys
from awslabs.rds_control_plane_mcp_server.common import config
from awslabs.rds_control_plane_mcp_server.common.clients import (
    get_pi_client,
    get_rds_client,
)
from awslabs.rds_control_plane_mcp_server.common.constants import MCP_SERVER_VERSION
from awslabs.rds_control_plane_mcp_server.resources.clusters.get_cluster_detail import (
    GetClusterDetailHandler,
)
from awslabs.rds_control_plane_mcp_server.resources.clusters.list_clusters import (
    ListClustersHandler,
)
from awslabs.rds_control_plane_mcp_server.resources.instances.get_instance_detail import (
    GetInstanceDetailHandler,
)
from awslabs.rds_control_plane_mcp_server.resources.instances.list_db_logs import ListDBLogsHandler
from awslabs.rds_control_plane_mcp_server.resources.instances.list_instances import (
    ListInstancesHandler,
)
from awslabs.rds_control_plane_mcp_server.resources.instances.list_performance_reports import (
    ListPerformanceReportHandler,
)
from awslabs.rds_control_plane_mcp_server.resources.instances.read_performance_report import (
    ReadPerformanceReportHandler,
)
from loguru import logger
from mcp.server.fastmcp import FastMCP


SERVER_INSTRUCTIONS = """
This server provides access to Amazon RDS database instances and clusters.

Key capabilities:
- View detailed information about RDS DB instances
- View detailed information about RDS DB clusters
- Access connection endpoints, configuration, and status information
- List performance reports and log files for DB instances

The server operates in read-only mode by default, providing safe access to RDS resources.
"""

SERVER_DEPENDENCIES = ['pydantic', 'loguru', 'boto3']

# Global reference to the MCP server instance for testing purposes
_mcp = None


def create_mcp_server():
    """Create and configure the MCP server instance."""
    return FastMCP(
        'awslabs.rds-control-plane-mcp-server',
        version=MCP_SERVER_VERSION,
        instructions=SERVER_INSTRUCTIONS,
        dependencies=SERVER_DEPENDENCIES,
    )


global _pi_client
global _rds_client
global _cloudwatch_client

try:
    _pi_client = get_pi_client(
        region_name=os.getenv('AWS_REGION'),
        profile_name=os.getenv('AWS_PROFILE'),
    )
    _rds_client = get_rds_client(
        region_name=os.getenv('AWS_REGION'), profile_name=os.getenv('AWS_PROFILE')
    )
except Exception as e:
    logger.error(f'Error getting RDS or PI clients: {e}')
    raise e

logger.remove()
logger.add(sys.stderr, level='INFO')


def main():
    """Run the MCP server with CLI argument support."""
    global _readonly
    global _mcp

    parser = argparse.ArgumentParser(
        description='An AWS Labs MCP server for Amazon RDS control plane operations'
    )
    parser.add_argument('--port', type=int, default=8888, help='Port to run the server on')
    parser.add_argument(
        '--max-items',
        type=int,
        default=config.DEFAULT_MAX_ITEMS,
        help=f'The maximum number of items (logs, reports, etc.) to retrieve (default: {config.DEFAULT_MAX_ITEMS})',
    )
    parser.add_argument(
        '--readonly',
        type=str,
        default='true',
        choices=['true', 'false'],
        help='Whether to run in read-only mode (default: true)',
    )

    _mcp = create_mcp_server()
    _mcp.resource

    args = parser.parse_args()

    _readonly = args.readonly.lower() == 'true'
    config.max_items = args.max_items

    # MCP server port
    if args.port:
        _mcp.settings.port = args.port

    # log configuration
    logger.info(f'Starting RDS Control Plane MCP Server v{MCP_SERVER_VERSION}')
    logger.info(f'Read-only mode: {_readonly}')
    logger.info(f'Max items to fetch: {config.max_items}')

    # Initialize resource handlers - these are all READ-ONLY operations
    ListClustersHandler(_mcp, _rds_client)
    GetClusterDetailHandler(_mcp, _rds_client)
    ListInstancesHandler(_mcp, _rds_client)
    GetInstanceDetailHandler(_mcp, _rds_client)
    ListDBLogsHandler(_mcp, _rds_client)
    ListPerformanceReportHandler(_mcp, _pi_client)
    ReadPerformanceReportHandler(_mcp, _pi_client)

    # default streamable HTTP transport
    _mcp.run()

    return _mcp


if __name__ == '__main__':
    main()
