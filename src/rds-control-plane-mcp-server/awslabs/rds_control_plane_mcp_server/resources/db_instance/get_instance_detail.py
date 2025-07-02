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
import json
from ...common.connection import RDSConnectionManager
from ...common.constants import RESOURCE_PREFIX_DB_INSTANCE
from ...common.decorator import handle_exceptions
from ...common.models import InstanceModel
from ...common.server import mcp
from .utils import format_instance_info
from loguru import logger
from pydantic import Field


GET_INSTANCE_DETAIL_DOCSTRING = """Get detailed information about a specific Amazon RDS instance.

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
- Parameter groups
- Option groups
"""


@mcp.resource(
    uri='aws-rds://db-instance/{instance_id}',
    name='GetDBInstanceDetails',
    mime_type='application/json',
    description=GET_INSTANCE_DETAIL_DOCSTRING,
)
@handle_exceptions
async def get_instance_detail(
    instance_id: str = Field(..., description='The instance identifier'),
) -> InstanceModel:
    """Get detailed information about a specific instance as a resource.

    Args:
        instance_id: The instance identifier

    Returns:
        JSON string with instance details
    """
    logger.info(f'Getting instance detail resource for {instance_id}')
    rds_client = RDSConnectionManager.get_connection()

    response = await asyncio.to_thread(
        rds_client.describe_db_instances, DBInstanceIdentifier=instance_id
    )

    instances = response.get('DBInstances', [])
    if not instances:
        raise ValueError(f'Instance {instance_id} not found')

    instance = format_instance_info(instances[0])
    instance.resource_uri = f'{RESOURCE_PREFIX_DB_INSTANCE}/{instance_id}'

    return instance
