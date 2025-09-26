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

"""Replication instance operations for DMS MCP Server."""

from awslabs.dms_mcp_server.aws_client import (
    get_dms_client,
    handle_aws_error,
)
from awslabs.dms_mcp_server.common.server import mcp
from awslabs.dms_mcp_server.consts import DEFAULT_MAX_RECORDS
from awslabs.dms_mcp_server.context import Context
from awslabs.dms_mcp_server.models import (
    CreateReplicationInstanceResponse,
    ReplicationInstanceListResponse,
    ReplicationInstanceResponse,
)
from loguru import logger
from pydantic import Field
from typing import Optional


@mcp.tool()
async def describe_replication_instances(
    replication_instance_identifier: Optional[str] = Field(
        default=None, description='Filter by specific replication instance identifier'
    ),
    max_records: int = Field(
        default=DEFAULT_MAX_RECORDS, description='Maximum number of records to return'
    ),
    marker: Optional[str] = Field(default=None, description='Pagination token'),
) -> ReplicationInstanceListResponse:
    """Describe one or more DMS replication instances."""
    try:
        dms_client = get_dms_client()

        describe_params = {'MaxRecords': max_records}

        if replication_instance_identifier:
            describe_params['Filters'] = [
                {'Name': 'replication-instance-id', 'Values': [replication_instance_identifier]}
            ]
        if marker:
            describe_params['Marker'] = marker

        response = dms_client.describe_replication_instances(**describe_params)

        instances = [
            ReplicationInstanceResponse(
                replication_instance_identifier=instance['ReplicationInstanceIdentifier'],
                replication_instance_arn=instance['ReplicationInstanceArn'],
                replication_instance_class=instance['ReplicationInstanceClass'],
                engine_version=instance.get('EngineVersion', ''),
                replication_instance_status=instance['ReplicationInstanceStatus'],
                allocated_storage=instance['AllocatedStorage'],
                replication_instance_public_ip_address=instance.get(
                    'ReplicationInstancePublicIpAddress'
                ),
                replication_instance_private_ip_address=instance.get(
                    'ReplicationInstancePrivateIpAddress'
                ),
                availability_zone=instance.get('AvailabilityZone'),
                vpc_security_groups=instance.get('VpcSecurityGroups'),
                preferred_maintenance_window=instance.get('PreferredMaintenanceWindow'),
                multi_az=instance['MultiAZ'],
                auto_minor_version_upgrade=instance['AutoMinorVersionUpgrade'],
                instance_create_time=instance.get('InstanceCreateTime'),
            )
            for instance in response['ReplicationInstances']
        ]

        return ReplicationInstanceListResponse(
            replication_instances=instances, marker=response.get('Marker')
        )

    except Exception as e:
        error_msg = handle_aws_error(e)
        logger.error(f'Failed to describe replication instances: {error_msg}')
        raise ValueError(f'Failed to describe replication instances: {error_msg}')


@mcp.tool()
async def create_replication_instance(
    replication_instance_identifier: str = Field(
        description='A unique name for the replication instance'
    ),
    replication_instance_class: str = Field(
        description='The compute and memory capacity of the replication instance (e.g., dms.t3.micro, dms.r5.large)'
    ),
    allocated_storage: int = Field(
        description='The amount of storage (in gigabytes) to allocate for the replication instance'
    ),
    multi_az: bool = Field(
        default=False,
        description='Specifies whether the replication instance is a Multi-AZ deployment',
    ),
    engine_version: Optional[str] = Field(
        default=None, description='The engine version number of the replication instance'
    ),
    auto_minor_version_upgrade: bool = Field(
        default=True,
        description='A value that indicates whether minor engine upgrades are applied automatically',
    ),
    preferred_maintenance_window: Optional[str] = Field(
        default=None,
        description="The weekly time range during which system maintenance can occur (e.g., 'sun:23:00-mon:01:00')",
    ),
    replication_subnet_group_identifier: Optional[str] = Field(
        default=None, description='A subnet group to associate with the replication instance'
    ),
    vpc_security_group_ids: Optional[str] = Field(
        default=None,
        description='Comma-separated list of VPC security group IDs to associate with the replication instance',
    ),
    publicly_accessible: bool = Field(
        default=False,
        description='Specifies the accessibility options for the replication instance',
    ),
    kms_key_id: Optional[str] = Field(
        default=None, description='An AWS KMS key identifier for encryption'
    ),
    tags: Optional[str] = Field(
        default=None,
        description='One or more tags to be assigned to the replication instance (JSON format)',
    ),
) -> CreateReplicationInstanceResponse:
    """Create a new DMS replication instance.

    This creates a new replication instance that can be used to perform database migration tasks.
    The replication instance provides the compute resources needed to migrate data between source and target databases.

    Args:
        replication_instance_identifier: Unique name for the replication instance
        replication_instance_class: Instance class (e.g., dms.t3.micro, dms.r5.large)
        allocated_storage: Storage size in GB (minimum 20 GB)
        multi_az: Whether to deploy in multiple availability zones for high availability
        engine_version: DMS engine version (optional, uses default if not specified)
        auto_minor_version_upgrade: Whether to automatically upgrade minor versions
        preferred_maintenance_window: Weekly maintenance window (e.g., 'sun:23:00-mon:01:00')
        replication_subnet_group_identifier: Subnet group for VPC deployment
        vpc_security_group_ids: Comma-separated security group IDs
        publicly_accessible: Whether the instance should be publicly accessible
        kms_key_id: KMS key for encryption
        tags: Resource tags in JSON format

    Example:
        Create a basic replication instance:
        replication_instance_identifier = "my-replication-instance"
        replication_instance_class = "dms.t3.micro"
        allocated_storage = 20
        multi_az = False
    """
    # Check if write operations are allowed
    Context.require_write_access()

    try:
        dms_client = get_dms_client()

        create_params = {
            'ReplicationInstanceIdentifier': replication_instance_identifier,
            'ReplicationInstanceClass': replication_instance_class,
            'AllocatedStorage': allocated_storage,
            'MultiAZ': multi_az,
            'AutoMinorVersionUpgrade': auto_minor_version_upgrade,
            'PubliclyAccessible': publicly_accessible,
        }

        # Add optional parameters only if provided
        if engine_version:
            create_params['EngineVersion'] = engine_version
        if preferred_maintenance_window:
            create_params['PreferredMaintenanceWindow'] = preferred_maintenance_window
        if replication_subnet_group_identifier:
            create_params['ReplicationSubnetGroupIdentifier'] = replication_subnet_group_identifier
        if vpc_security_group_ids:
            create_params['VpcSecurityGroupIds'] = vpc_security_group_ids.split(',')
        if kms_key_id:
            create_params['KmsKeyId'] = kms_key_id
        if tags:
            import json

            try:
                tags_list = json.loads(tags)
                create_params['Tags'] = tags_list
            except json.JSONDecodeError:
                raise ValueError('tags must be valid JSON format')

        response = dms_client.create_replication_instance(**create_params)
        instance = response['ReplicationInstance']

        instance_response = ReplicationInstanceResponse(
            replication_instance_identifier=instance['ReplicationInstanceIdentifier'],
            replication_instance_arn=instance['ReplicationInstanceArn'],
            replication_instance_class=instance['ReplicationInstanceClass'],
            engine_version=instance.get('EngineVersion', ''),
            replication_instance_status=instance['ReplicationInstanceStatus'],
            allocated_storage=instance['AllocatedStorage'],
            replication_instance_public_ip_address=instance.get(
                'ReplicationInstancePublicIpAddress'
            ),
            replication_instance_private_ip_address=instance.get(
                'ReplicationInstancePrivateIpAddress'
            ),
            availability_zone=instance.get('AvailabilityZone'),
            vpc_security_groups=instance.get('VpcSecurityGroups'),
            preferred_maintenance_window=instance.get('PreferredMaintenanceWindow'),
            multi_az=instance['MultiAZ'],
            auto_minor_version_upgrade=instance['AutoMinorVersionUpgrade'],
            instance_create_time=instance.get('InstanceCreateTime'),
        )

        return CreateReplicationInstanceResponse(replication_instance=instance_response)

    except Exception as e:
        error_msg = handle_aws_error(e)
        logger.error(f'Failed to create replication instance: {error_msg}')
        raise ValueError(f'Failed to create replication instance: {error_msg}')
