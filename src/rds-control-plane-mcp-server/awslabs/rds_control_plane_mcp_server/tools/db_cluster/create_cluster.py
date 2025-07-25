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

"""Tool to create a new Amazon RDS database cluster."""

import asyncio
from ...common.connection import RDSConnectionManager
from ...common.constants import (
    ENGINE_PORT_MAP,
    SUCCESS_CREATED,
)
from ...common.decorators.handle_exceptions import handle_exceptions
from ...common.decorators.readonly_check import readonly_check
from ...common.server import mcp
from ...common.utils import (
    add_mcp_tags,
    format_rds_api_response,
)
from .utils import format_cluster_info
from loguru import logger
from pydantic import Field
from typing import Any, Dict, List, Optional
from typing_extensions import Annotated


CREATE_CLUSTER_TOOL_DESCRIPTION = """Create a new Amazon RDS database cluster.

This tool provisions a new RDS database cluster in your AWS account with the specified engine and configuration. After creation, you'll need to create DB instances separately.

<warning>
When not in readonly mode, this will create actual resources in your AWS account that may incur charges.
</warning>
"""


@mcp.tool(
    name='CreateDBCluster',
    description=CREATE_CLUSTER_TOOL_DESCRIPTION,
)
@handle_exceptions
@readonly_check
async def create_db_cluster(
    db_cluster_identifier: Annotated[str, Field(description='The identifier for the DB cluster')],
    engine: Annotated[
        str,
        Field(
            description='The name of the database engine to be used for this DB cluster (e.g., aurora, aurora-mysql, aurora-postgresql, mysql, postgres, mariadb, oracle, sqlserver)'
        ),
    ],
    master_username: Annotated[
        str, Field(description='The name of the master user for the DB cluster')
    ],
    database_name: Annotated[
        Optional[str], Field(description='The name for your database')
    ] = None,
    vpc_security_group_ids: Annotated[
        Optional[List[str]],
        Field(description='A list of EC2 VPC security groups to associate with this DB cluster'),
    ] = None,
    db_subnet_group_name: Annotated[
        Optional[str], Field(description='A DB subnet group to associate with this DB cluster')
    ] = None,
    availability_zones: Annotated[
        Optional[List[str]],
        Field(
            description='A list of Availability Zones (AZs) where instances in the DB cluster can be created'
        ),
    ] = None,
    backup_retention_period: Annotated[
        Optional[int],
        Field(description='The number of days for which automated backups are retained'),
    ] = None,
    port: Annotated[
        Optional[int],
        Field(
            description='The port number on which the instances in the DB cluster accept connections'
        ),
    ] = None,
    engine_version: Annotated[
        Optional[str], Field(description='The version number of the database engine to use')
    ] = None,
) -> Dict[str, Any]:
    """Create a new RDS database cluster.

    Args:
        db_cluster_identifier: The identifier for the DB cluster
        engine: The name of the database engine to be used for this DB cluster
        master_username: The name of the master user for the DB cluster
        database_name: The name for your database
        vpc_security_group_ids: A list of EC2 VPC security groups to associate with this DB cluster
        db_subnet_group_name: A DB subnet group to associate with this DB cluster
        availability_zones: A list of Availability Zones (AZs) where instances in the DB cluster can be created
        backup_retention_period: The number of days for which automated backups are retained
        port: The port number on which the instances in the DB cluster accept connections
        engine_version: The version number of the database engine to use

    Returns:
        Dict[str, Any]: The response from the AWS API
    """
    # Get RDS client
    rds_client = RDSConnectionManager.get_connection()

    params = {
        'DBClusterIdentifier': db_cluster_identifier,
        'Engine': engine,
        'MasterUsername': master_username,
        'ManageMasterUserPassword': True,
    }

    # add optional parameters if provided
    if database_name:
        params['DatabaseName'] = database_name
    if vpc_security_group_ids:
        params['VpcSecurityGroupIds'] = vpc_security_group_ids
    if db_subnet_group_name:
        params['DBSubnetGroupName'] = db_subnet_group_name
    if availability_zones:
        params['AvailabilityZones'] = availability_zones
    if backup_retention_period is not None:
        params['BackupRetentionPeriod'] = backup_retention_period
    if port is not None:
        params['Port'] = port
    else:
        engine_lower = engine.lower()
        # Use ENGINE_PORT_MAP to get the port, defaulting to None if not found
        params['Port'] = ENGINE_PORT_MAP.get(engine_lower)
    if engine_version:
        params['EngineVersion'] = engine_version

    # MCP tags
    params = add_mcp_tags(params)

    logger.info(f'Creating DB cluster {db_cluster_identifier} with engine {engine}')
    response = await asyncio.to_thread(rds_client.create_db_cluster, **params)
    logger.success(f'Successfully created DB cluster {db_cluster_identifier}')

    result = format_rds_api_response(response)
    result['message'] = SUCCESS_CREATED.format(f'DB cluster {db_cluster_identifier}')
    result['formatted_cluster'] = format_cluster_info(result.get('DBCluster', {}))

    return result
