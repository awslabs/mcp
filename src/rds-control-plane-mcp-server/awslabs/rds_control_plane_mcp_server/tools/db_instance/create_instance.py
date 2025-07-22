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

"""Tool to create a new Amazon RDS database instance."""

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
from .utils import format_instance_info
from loguru import logger
from pydantic import Field
from typing import Any, Dict, List, Optional
from typing_extensions import Annotated


CREATE_INSTANCE_TOOL_DESCRIPTION = """Create a new Amazon RDS database instance.

This tool provisions a new Amazon RDS database instance with the specified configuration. For Aurora databases, instances provide the compute and memory capacity for an existing cluster.

<warning>
When not in readonly mode, this will create actual resources in your AWS account that may incur charges.
</warning>
"""


@mcp.tool(
    name='CreateDBInstance',
    description=CREATE_INSTANCE_TOOL_DESCRIPTION,
)
@handle_exceptions
@readonly_check
async def create_db_instance(
    db_instance_identifier: Annotated[
        str, Field(description='The identifier for the DB instance')
    ],
    db_instance_class: Annotated[
        str,
        Field(description='The compute and memory capacity of the DB instance, e.g., db.m5.large'),
    ],
    engine: Annotated[
        str, Field(description='The name of the database engine to be used for this instance')
    ],
    allocated_storage: Annotated[
        Optional[int],
        Field(description='The amount of storage (in GiB) to be allocated for the DB instance'),
    ] = None,
    master_username: Annotated[
        Optional[str], Field(description='The name of the master user for the DB instance')
    ] = None,
    db_name: Annotated[Optional[str], Field(description='The name for your database')] = None,
    db_cluster_identifier: Annotated[
        Optional[str],
        Field(description='The identifier of the DB cluster that this instance will belong to'),
    ] = None,
    vpc_security_group_ids: Annotated[
        Optional[List[str]],
        Field(description='A list of EC2 VPC security groups to associate with this DB instance'),
    ] = None,
    availability_zone: Annotated[
        Optional[str],
        Field(description='The Availability Zone where the DB instance will be created'),
    ] = None,
    db_subnet_group_name: Annotated[
        Optional[str], Field(description='A DB subnet group to associate with this DB instance')
    ] = None,
    multi_az: Annotated[
        Optional[bool], Field(description='Specifies if the DB instance is a Multi-AZ deployment')
    ] = False,
    engine_version: Annotated[
        Optional[str], Field(description='The version number of the database engine to use')
    ] = None,
    storage_type: Annotated[
        Optional[str],
        Field(
            description='The storage type to be associated with the DB instance (standard, gp2, io1)'
        ),
    ] = None,
    storage_encrypted: Annotated[
        Optional[bool], Field(description='Specifies whether the DB instance is encrypted')
    ] = None,
    port: Annotated[
        Optional[int],
        Field(description='The port number on which the database accepts connections'),
    ] = None,
    publicly_accessible: Annotated[
        Optional[bool],
        Field(description='Specifies whether the DB instance is publicly accessible'),
    ] = None,
    backup_retention_period: Annotated[
        Optional[int],
        Field(description='The number of days for which automated backups are retained'),
    ] = None,
) -> Dict[str, Any]:
    """Create a new RDS database instance.

    Args:
        db_instance_identifier: The identifier for the DB instance
        db_instance_class: The compute and memory capacity of the DB instance
        engine: The name of the database engine to be used for this instance
        allocated_storage: The amount of storage (in GiB) to be allocated for the DB instance
        master_username: The name of the master user for the DB instance
        master_user_password: The password for the master user
        manage_master_user_password: Specifies whether to manage the master user password with AWS Secrets Manager
        db_name: The name for your database
        db_cluster_identifier: The identifier of the DB cluster that this instance will belong to
        vpc_security_group_ids: A list of EC2 VPC security groups to associate with this DB instance
        availability_zone: The Availability Zone where the DB instance will be created
        db_subnet_group_name: A DB subnet group to associate with this DB instance
        multi_az: Specifies if the DB instance is a Multi-AZ deployment
        engine_version: The version number of the database engine to use
        storage_type: The storage type to be associated with the DB instance
        storage_encrypted: Specifies whether the DB instance is encrypted
        port: The port number on which the database accepts connections
        publicly_accessible: Specifies whether the DB instance is publicly accessible
        backup_retention_period: The number of days for which automated backups are retained

    Returns:
        Dict[str, Any]: The response from the AWS API
    """
    # Get RDS client
    rds_client = RDSConnectionManager.get_connection()

    params = {
        'DBInstanceIdentifier': db_instance_identifier,
        'DBInstanceClass': db_instance_class,
        'Engine': engine,
        'ManageMasterUserPassword': True,
    }

    # add optional parameters if provided
    if allocated_storage is not None:
        params['AllocatedStorage'] = allocated_storage
    if master_username:
        params['MasterUsername'] = master_username
    if db_name:
        params['DBName'] = db_name
    if db_cluster_identifier:
        params['DBClusterIdentifier'] = db_cluster_identifier
    if vpc_security_group_ids:
        params['VpcSecurityGroupIds'] = vpc_security_group_ids
    if availability_zone:
        params['AvailabilityZone'] = availability_zone
    if db_subnet_group_name:
        params['DBSubnetGroupName'] = db_subnet_group_name
    if multi_az is not None:
        params['MultiAZ'] = multi_az
    if engine_version:
        params['EngineVersion'] = engine_version
    if storage_type:
        params['StorageType'] = storage_type
    if storage_encrypted is not None:
        params['StorageEncrypted'] = storage_encrypted
    if port is not None:
        params['Port'] = port
    else:
        engine_lower = engine.lower()
        # Use ENGINE_PORT_MAP to get the port, defaulting to None if not found
        params['Port'] = ENGINE_PORT_MAP.get(engine_lower)
    if publicly_accessible is not None:
        params['PubliclyAccessible'] = publicly_accessible
    if backup_retention_period is not None:
        params['BackupRetentionPeriod'] = backup_retention_period

    # MCP tags
    params = add_mcp_tags(params)

    logger.info(f'Creating DB instance {db_instance_identifier} with engine {engine}')
    response = await asyncio.to_thread(rds_client.create_db_instance, **params)
    logger.success(f'Successfully created DB instance {db_instance_identifier}')

    result = format_rds_api_response(response)
    result['message'] = SUCCESS_CREATED.format(f'DB instance {db_instance_identifier}')
    result['formatted_instance'] = format_instance_info(result.get('DBInstance', {}))

    return result
