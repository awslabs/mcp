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
from awslabs.rds_control_plane_mcp_server import config
from awslabs.rds_control_plane_mcp_server.clients import (
    get_pi_client,
    get_rds_client,
)
from awslabs.rds_control_plane_mcp_server.constants import MCP_SERVER_VERSION
from awslabs.rds_control_plane_mcp_server.logs import list_db_log_files
from awslabs.rds_control_plane_mcp_server.models import DBLogFileSummary, PerformanceReportSummary
from awslabs.rds_control_plane_mcp_server.reports import (
    list_performance_reports,
    read_performance_report,
)
from awslabs.rds_control_plane_mcp_server.resource_docstrings import (
    GET_CLUSTER_DOCSTRING,
    GET_INSTANCE_DOCSTRING,
    LIST_CLUSTERS_DOCSTRING,
    LIST_DB_LOG_FILES_DOCSTRING,
    LIST_INSTANCES_DOCSTRING,
    LIST_PERFORMANCE_REPORTS_DOCSTRING,
    READ_PERFORMANCE_REPORT_DOCSTRING,
)
from awslabs.rds_control_plane_mcp_server.resources import (
    get_cluster_detail_resource,
    get_cluster_list_resource,
    get_instance_detail_resource,
    get_instance_list_resource,
)
from awslabs.rds_control_plane_mcp_server.utils import apply_docstring
from loguru import logger
from mcp.server.fastmcp import FastMCP
from pydantic import Field
from typing import Any, List, Union


mcp = FastMCP(
    'awslabs.rds-control-plane-mcp-server',
    version=MCP_SERVER_VERSION,
    instructions="""This server provides access to Amazon RDS database instances and clusters.

Key capabilities:
- View detailed information about RDS DB instances
- View detailed information about RDS DB clusters
- Access connection endpoints, configuration, and status information
- List performance reports and log files for DB instances

The server operates in read-only mode by default, providing safe access to RDS resources.""",
    dependencies=[
        'pydantic',
        'loguru',
        'boto3',
    ],
)

# Remove all default handlers then add our own
logger.remove()
logger.add(sys.stderr, level='INFO')

global _pi_client
global _rds_client
global _cloudwatch_client
global _readonly
_readonly = True

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

# ===== RESOURCES =====
# read-only access to RDS data


@mcp.resource(uri='aws-rds://db-cluster', name='DB Clusters', mime_type='application/json')
@apply_docstring(LIST_CLUSTERS_DOCSTRING)
async def list_clusters_resource() -> str:
    """List all available Amazon RDS clusters in your account."""
    return await get_cluster_list_resource(rds_client=_rds_client)


@mcp.resource(
    uri='aws-rds://db-cluster/{cluster_id}',
    name='DB Cluster Details',
    mime_type='application/json',
)
@apply_docstring(GET_CLUSTER_DOCSTRING)
async def get_cluster_resource(cluster_id: str) -> str:
    """Get detailed information about a specific Amazon RDS cluster."""
    return await get_cluster_detail_resource(cluster_id=cluster_id, rds_client=_rds_client)


@mcp.resource(uri='aws-rds://db-instance', name='DB Instances', mime_type='application/json')
@apply_docstring(LIST_INSTANCES_DOCSTRING)
async def list_instances_resource() -> str:
    """List all available Amazon RDS instances in your account."""
    return await get_instance_list_resource(rds_client=_rds_client)


@mcp.resource(
    uri='aws-rds://db-instance/{instance_id}',
    name='DB Instance Details',
    mime_type='application/json',
)
@apply_docstring(GET_INSTANCE_DOCSTRING)
async def get_instance_resource(instance_id: str) -> str:
    """Get detailed information about a specific Amazon RDS instance."""
    return await get_instance_detail_resource(instance_id, _rds_client)


@mcp.resource(
    uri='aws-rds://db-instance/{dbi_resource_identifier}/performance_report',
    name='ListPerformanceReports',
    mime_type='application/json',
)
@apply_docstring(LIST_PERFORMANCE_REPORTS_DOCSTRING)
async def list_performance_reports_resource(
    dbi_resource_identifier: str = Field(
        ..., description='The resource identifier for the DB instance'
    ),
) -> Union[List[PerformanceReportSummary], dict[str, Any]]:
    """List all available performance reports for a specific Amazon RDS instance."""
    return await list_performance_reports(
        dbi_resource_identifier,
        _pi_client,
    )


@mcp.resource(
    uri='aws-rds://db-instance/{dbi_resource_identifier}/performance_report/{report_identifier}',
    name='ReadPerformanceReport',
    mime_type='text/plain',
)
@apply_docstring(READ_PERFORMANCE_REPORT_DOCSTRING)
async def read_performance_report_resource(
    dbi_resource_identifier: str = Field(
        ..., description='The resource identifier for the DB instance'
    ),
    report_identifier: str = Field(
        ..., description='The identifier for the report you want to read'
    ),
) -> dict[str, Any]:
    """Read the contents of a specific performance report for a specific Amazon RDS instance."""
    return await read_performance_report(
        dbi_resource_identifier=dbi_resource_identifier,
        report_id=report_identifier,
        pi_client=_pi_client,
    )


@mcp.resource(
    uri='aws-rds://db-instance/{db_instance_identifier}/log',
    name='ListDBLogFiles',
    mime_type='application/json',
)
@apply_docstring(LIST_DB_LOG_FILES_DOCSTRING)
async def list_db_log_files_resource(
    db_instance_identifier: str = Field(..., description='The identifier for the DB instance'),
) -> Union[List[DBLogFileSummary], dict[str, Any]]:
    """List all available log files for a specific Amazon RDS instance."""
    return await list_db_log_files(
        db_instance_identifier=db_instance_identifier, rds_client=_rds_client
    )


def main():
    """Run the MCP server with CLI argument support."""
    global _readonly

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

    args = parser.parse_args()

    # global configuration
    _readonly = args.readonly.lower() == 'true'

    # Max items to fetch
    config.max_items = args.max_items

    # MCP server port
    if args.port:
        mcp.settings.port = args.port

    # log configuration
    logger.info(f'Starting RDS Control Plane MCP Server v{MCP_SERVER_VERSION}')
    logger.info(f'Read-only mode: {_readonly}')
    logger.info(f'Max items to fetch: {config.max_items}')

    # default streamable HTTP transport
    mcp.run()


if __name__ == '__main__':
    main()
