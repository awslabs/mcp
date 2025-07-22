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

"""Resource for retrieving detailed information about RDS DB Instances."""

import asyncio
from ...common.connection import RDSConnectionManager
from ...common.decorators.handle_exceptions import handle_exceptions
from ...common.server import mcp
from ...tools.db_instance.utils import format_instance_info
from loguru import logger
from mypy_boto3_rds.type_defs import DBInstanceTypeDef
from pydantic import BaseModel, Field
from typing import Dict, List, Optional


DESCRIBE_INSTANCE_DETAIL_DOCSTRING = """Get detailed information about a specific Amazon RDS instance.

This resource retrieves comprehensive details about a specific RDS database instance identified by its instance ID, including configuration, status, endpoints, storage details, and security settings.
"""


class InstanceEndpoint(BaseModel):
    """DB instance endpoint model."""

    address: Optional[str] = Field(None, description='The DNS address of the instance')
    port: Optional[int] = Field(
        None, description='The port that the database engine is listening on'
    )
    hosted_zone_id: Optional[str] = Field(
        None, description='The ID of the Amazon Route 53 hosted zone'
    )


class InstanceStorage(BaseModel):
    """DB instance storage model."""

    type: Optional[str] = Field(None, description='The storage type')
    allocated: Optional[int] = Field(None, description='The allocated storage size in gibibytes')
    encrypted: Optional[bool] = Field(None, description='Whether the storage is encrypted')


class Instance(BaseModel):
    """DB instance model."""

    instance_id: str = Field(description='The DB instance identifier')
    status: str = Field(description='The current status of the DB instance')
    engine: str = Field(description='The database engine')
    engine_version: str = Field('', description='The version of the database engine')
    instance_class: str = Field(
        description='The compute and memory capacity class of the DB instance'
    )
    endpoint: Optional[InstanceEndpoint] = Field(None, description='The connection endpoint')
    availability_zone: Optional[str] = Field(
        None, description='The Availability Zone of the DB instance'
    )
    multi_az: bool = Field(description='Whether the DB instance is a Multi-AZ deployment')
    storage: Optional[InstanceStorage] = Field(None, description='The storage configuration')
    preferred_backup_window: Optional[str] = Field(
        None, description='The daily time range during which automated backups are created'
    )
    preferred_maintenance_window: Optional[str] = Field(
        None, description='The weekly time range during which system maintenance can occur'
    )
    publicly_accessible: bool = Field(description='Whether the DB instance is publicly accessible')
    vpc_security_groups: List[Dict[str, str]] = Field(
        default_factory=list,
        description='A list of VPC security groups the DB instance belongs to',
    )
    db_cluster: Optional[str] = Field(
        None, description='The DB cluster identifier, if this is a member of a DB cluster'
    )
    tags: Dict[str, str] = Field(default_factory=dict, description='A list of tags')
    dbi_resource_id: Optional[str] = Field(
        None, description='The AWS Region-unique, immutable identifier for the DB instance'
    )
    resource_uri: Optional[str] = Field(None, description='The resource URI for this instance')

    @classmethod
    def from_DBInstanceTypeDef(cls, instance: DBInstanceTypeDef) -> 'Instance':
        """Format instance information into a detailed model using the shared utility function.

        Takes raw instance data from AWS and formats it into a structured Instance model
        using the centralized format_instance_info utility to avoid code duplication.

        Args:
            instance: Raw instance data from AWS

        Returns:
            Instance: Formatted instance information with comprehensive details
        """
        # Use the shared utility function to format the instance data
        formatted_data = format_instance_info(instance)

        # Convert the formatted data to the pydantic models
        endpoint = None
        if formatted_data.get('endpoint'):
            endpoint_data = formatted_data['endpoint']
            endpoint = InstanceEndpoint(
                address=endpoint_data.get('address'),
                port=endpoint_data.get('port'),
                hosted_zone_id=endpoint_data.get('hosted_zone_id'),
            )

        storage = None
        if formatted_data.get('storage'):
            storage_data = formatted_data['storage']
            storage = InstanceStorage(
                type=storage_data.get('type'),
                allocated=storage_data.get('allocated'),
                encrypted=storage_data.get('encrypted'),
            )

        return cls(
            instance_id=formatted_data.get('instance_id', ''),
            status=formatted_data.get('status', ''),
            engine=formatted_data.get('engine', ''),
            engine_version=formatted_data.get('engine_version') or '',
            instance_class=formatted_data.get('instance_class', ''),
            endpoint=endpoint,
            availability_zone=formatted_data.get('availability_zone'),
            multi_az=formatted_data.get('multi_az', False),
            storage=storage,
            preferred_backup_window=formatted_data.get('preferred_backup_window'),
            preferred_maintenance_window=formatted_data.get('preferred_maintenance_window'),
            publicly_accessible=formatted_data.get('publicly_accessible', False),
            vpc_security_groups=formatted_data.get('vpc_security_groups', []),
            db_cluster=formatted_data.get('db_cluster'),
            tags=formatted_data.get('tags', {}),
            dbi_resource_id=formatted_data.get('resource_id'),
            resource_uri=None,
        )


@mcp.resource(
    uri='aws-rds://db-instance/{instance_id}',
    name='DescribeDBInstanceDetails',
    mime_type='application/json',
    description=DESCRIBE_INSTANCE_DETAIL_DOCSTRING,
)
@handle_exceptions
async def describe_instance_detail(
    instance_id: str = Field(..., description='The instance identifier'),
) -> Instance:
    """Get detailed information about a specific instance as a resource.

    Args:
        instance_id: The unique identifier of the RDS instance

    Returns:
        Instance: Detailed information about the specified RDS instance

    Raises:
        ValueError: If the specified instance is not found
    """
    logger.info(f'Getting instance detail resource for {instance_id}')
    rds_client = RDSConnectionManager.get_connection()

    response = await asyncio.to_thread(
        rds_client.describe_db_instances, DBInstanceIdentifier=instance_id
    )

    instances = response.get('DBInstances', [])
    if not instances:
        raise ValueError(f'Instance {instance_id} not found')

    instance = Instance.from_DBInstanceTypeDef(instances[0])
    instance.resource_uri = f'aws-rds://db-instance/{instance_id}'

    return instance
