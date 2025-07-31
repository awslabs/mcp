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

"""Tool to modify an existing Amazon RDS database instance."""

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
from .utils import format_instance_info
from loguru import logger
from pydantic import Field
from typing import Any, Dict, List, Optional
from typing_extensions import Annotated


MODIFY_INSTANCE_TOOL_DESCRIPTION = """Modify an existing Amazon RDS database instance.

This tool modifies the configuration of an existing RDS database instance. Various
attributes of the instance can be changed, such as instance class, storage configuration,
backup retention, security groups, and more.

You can specify whether the changes should be applied immediately or during the next
maintenance window.

<warning>
Some modifications might cause downtime, especially if applied immediately.
For storage changes, the instance may become unavailable during the modification.
</warning>
"""


@mcp.tool(
    name='ModifyDBInstance',
    description=MODIFY_INSTANCE_TOOL_DESCRIPTION,
)
@handle_exceptions
@readonly_check
async def modify_db_instance(
    db_instance_identifier: Annotated[
        str, Field(description='The identifier for the DB instance')
    ],
    apply_immediately: Annotated[
        Optional[bool],
        Field(
            description='Specifies whether the modifications are applied immediately, or during the next maintenance window'
        ),
    ] = None,
    allocated_storage: Annotated[
        Optional[int],
        Field(description='The new amount of storage (in GiB) to allocate for the DB instance'),
    ] = None,
    db_instance_class: Annotated[
        Optional[str],
        Field(
            description='The new compute and memory capacity of the DB instance, for example, db.m5.large'
        ),
    ] = None,
    storage_type: Annotated[
        Optional[str],
        Field(description='The new storage type to be associated with the DB instance'),
    ] = None,
    master_user_password: Annotated[
        Optional[str], Field(description='The new password for the master user')
    ] = None,
    manage_master_user_password: Annotated[
        Optional[bool],
        Field(
            description='Specifies whether to manage the master user password with AWS Secrets Manager'
        ),
    ] = None,
    vpc_security_group_ids: Annotated[
        Optional[List[str]],
        Field(description='A list of EC2 VPC security groups to associate with this DB instance'),
    ] = None,
    db_parameter_group_name: Annotated[
        Optional[str],
        Field(description='The name of the DB parameter group to apply to the DB instance'),
    ] = None,
    backup_retention_period: Annotated[
        Optional[int], Field(description='The number of days to retain automated backups')
    ] = None,
    preferred_backup_window: Annotated[
        Optional[str],
        Field(description='The daily time range during which automated backups are created'),
    ] = None,
    preferred_maintenance_window: Annotated[
        Optional[str],
        Field(description='The weekly time range during which system maintenance can occur'),
    ] = None,
    multi_az: Annotated[
        Optional[bool],
        Field(description='Specifies whether the DB instance is a Multi-AZ deployment'),
    ] = None,
    engine_version: Annotated[
        Optional[str], Field(description='The version number of the database engine to upgrade to')
    ] = None,
    allow_major_version_upgrade: Annotated[
        Optional[bool], Field(description='Indicates whether major version upgrades are allowed')
    ] = None,
    auto_minor_version_upgrade: Annotated[
        Optional[bool],
        Field(description='Indicates that minor version upgrades are applied automatically'),
    ] = None,
    publicly_accessible: Annotated[
        Optional[bool],
        Field(description='Specifies whether the DB instance is publicly accessible'),
    ] = None,
) -> Dict[str, Any]:
    """Modify an existing RDS database instance configuration.

    Args:
        db_instance_identifier: The identifier for the DB instance
        apply_immediately: Specifies whether the modifications are applied immediately
        allocated_storage: The new amount of storage (in GiB) to allocate
        db_instance_class: The new compute and memory capacity of the DB instance
        storage_type: The new storage type to be associated with the DB instance
        master_user_password: The new password for the master user
        manage_master_user_password: Specifies whether to manage the master user password with AWS Secrets Manager
        vpc_security_group_ids: A list of EC2 VPC security groups to associate with this DB instance
        db_parameter_group_name: The name of the DB parameter group to apply to the DB instance
        backup_retention_period: The number of days to retain automated backups
        preferred_backup_window: The daily time range during which automated backups are created
        preferred_maintenance_window: The weekly time range during which system maintenance can occur
        multi_az: Specifies whether the DB instance is a Multi-AZ deployment
        engine_version: The version number of the database engine to upgrade to
        allow_major_version_upgrade: Indicates whether major version upgrades are allowed
        auto_minor_version_upgrade: Indicates that minor version upgrades are applied automatically
        publicly_accessible: Specifies whether the DB instance is publicly accessible

    Returns:
        Dict[str, Any]: The response from the AWS API
    """
    rds_client = RDSConnectionManager.get_connection()

    params: dict[str, Any] = {
        'DBInstanceIdentifier': db_instance_identifier,
    }

    # Add optional parameters if provided
    if apply_immediately is not None:
        params['ApplyImmediately'] = apply_immediately
    if allocated_storage is not None:
        params['AllocatedStorage'] = allocated_storage
    if db_instance_class:
        params['DBInstanceClass'] = db_instance_class
    if storage_type:
        params['StorageType'] = storage_type
    if master_user_password:
        params['MasterUserPassword'] = master_user_password
    if manage_master_user_password is not None:
        params['ManageMasterUserPassword'] = manage_master_user_password
    if vpc_security_group_ids:
        params['VpcSecurityGroupIds'] = vpc_security_group_ids
    if db_parameter_group_name:
        params['DBParameterGroupName'] = db_parameter_group_name
    if backup_retention_period is not None:
        params['BackupRetentionPeriod'] = backup_retention_period
    if preferred_backup_window:
        params['PreferredBackupWindow'] = preferred_backup_window
    if preferred_maintenance_window:
        params['PreferredMaintenanceWindow'] = preferred_maintenance_window
    if multi_az is not None:
        params['MultiAZ'] = multi_az
    if engine_version:
        params['EngineVersion'] = engine_version
    if allow_major_version_upgrade is not None:
        params['AllowMajorVersionUpgrade'] = allow_major_version_upgrade
    if auto_minor_version_upgrade is not None:
        params['AutoMinorVersionUpgrade'] = auto_minor_version_upgrade
    if publicly_accessible is not None:
        params['PubliclyAccessible'] = publicly_accessible

    logger.info(f'Modifying DB instance {db_instance_identifier}')
    response = await asyncio.to_thread(rds_client.modify_db_instance, **params)
    logger.success(f'Successfully modified DB instance {db_instance_identifier}')

    result = format_rds_api_response(response)
    result['message'] = SUCCESS_MODIFIED.format(f'DB instance {db_instance_identifier}')
    result['formatted_instance'] = format_instance_info(result.get('DBInstance', {}))

    return result
