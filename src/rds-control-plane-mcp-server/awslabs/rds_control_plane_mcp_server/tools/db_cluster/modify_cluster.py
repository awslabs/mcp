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

"""Tool to modify an existing Amazon RDS database cluster."""

import asyncio
from ...common.connection import RDSConnectionManager
from ...common.constants import (
    SUCCESS_MODIFIED,
)
from ...common.decorators.handle_exceptions import handle_exceptions
from ...common.decorators.readonly_check import readonly_check
from ...common.server import mcp
from ...common.utils import (
    format_rds_api_response,
)
from .utils import format_cluster_info
from loguru import logger
from pydantic import Field
from typing import Any, Dict, List, Optional
from typing_extensions import Annotated


MODIFY_CLUSTER_TOOL_DESCRIPTION = """Modify an existing RDS database cluster configuration.

This tool updates the configuration of an existing Amazon RDS database cluster, allowing changes to settings like backup retention, parameter groups, security groups, and engine versions.

<warning>
Setting apply_immediately=True may cause downtime. By default, changes are applied during the next maintenance window.
</warning>
"""


@mcp.tool(
    name='ModifyDBCluster',
    description=MODIFY_CLUSTER_TOOL_DESCRIPTION,
)
@handle_exceptions
@readonly_check
async def modify_db_cluster(
    db_cluster_identifier: Annotated[str, Field(description='The identifier for the DB cluster')],
    apply_immediately: Annotated[
        Optional[bool],
        Field(
            description='Specifies whether the modifications are applied immediately, or during the next maintenance window'
        ),
    ] = None,
    backup_retention_period: Annotated[
        Optional[int],
        Field(description='The number of days for which automated backups are retained'),
    ] = None,
    db_cluster_parameter_group_name: Annotated[
        Optional[str],
        Field(description='The name of the DB cluster parameter group to use for the DB cluster'),
    ] = None,
    vpc_security_group_ids: Annotated[
        Optional[List[str]],
        Field(description='A list of EC2 VPC security groups to associate with this DB cluster'),
    ] = None,
    port: Annotated[
        Optional[int],
        Field(description='The port number on which the DB cluster accepts connections'),
    ] = None,
    engine_version: Annotated[
        Optional[str], Field(description='The version number of the database engine to upgrade to')
    ] = None,
    allow_major_version_upgrade: Annotated[
        Optional[bool], Field(description='Indicates whether major version upgrades are allowed')
    ] = None,
) -> Dict[str, Any]:
    """Modify an existing RDS database cluster configuration.

    Args:
        db_cluster_identifier: The identifier for the DB cluster
        apply_immediately: Specifies whether the modifications are applied immediately
        backup_retention_period: The number of days for which automated backups are retained
        db_cluster_parameter_group_name: The name of the DB cluster parameter group to use
        vpc_security_group_ids: A list of EC2 VPC security groups to associate with this DB cluster
        port: The port number on which the DB cluster accepts connections
        engine_version: The version number of the database engine to upgrade to
        allow_major_version_upgrade: Indicates whether major version upgrades are allowed

    Returns:
        Dict[str, Any]: The response from the AWS API
    """
    rds_client = RDSConnectionManager.get_connection()

    params: Dict[str, Any] = {
        'DBClusterIdentifier': db_cluster_identifier,
    }

    # Add optional parameters if provided
    if apply_immediately is not None:
        params['ApplyImmediately'] = apply_immediately
    if backup_retention_period is not None:
        params['BackupRetentionPeriod'] = backup_retention_period
    if db_cluster_parameter_group_name:
        params['DBClusterParameterGroupName'] = db_cluster_parameter_group_name
    if vpc_security_group_ids:
        params['VpcSecurityGroupIds'] = vpc_security_group_ids
    if port is not None:
        params['Port'] = port
    if engine_version:
        params['EngineVersion'] = engine_version
    if allow_major_version_upgrade is not None:
        params['AllowMajorVersionUpgrade'] = allow_major_version_upgrade

    logger.info(f'Modifying DB cluster {db_cluster_identifier}')
    response = await asyncio.to_thread(rds_client.modify_db_cluster, **params)
    logger.success(f'Successfully modified DB cluster {db_cluster_identifier}')

    result = format_rds_api_response(response)
    result['message'] = SUCCESS_MODIFIED.format(f'DB cluster {db_cluster_identifier}')
    result['formatted_cluster'] = format_cluster_info(result.get('DBCluster', {}))

    return result
