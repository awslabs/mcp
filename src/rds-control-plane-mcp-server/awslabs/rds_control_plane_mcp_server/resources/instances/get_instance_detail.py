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

"""Get Instance Detail handler for the RDS Control Plane MCP Server."""

import asyncio
import json
from awslabs.rds_control_plane_mcp_server.common.constants import RESOURCE_PREFIX_DB_INSTANCE
from awslabs.rds_control_plane_mcp_server.common.utils import (
    format_instance_info,
    handle_aws_error,
)
from loguru import logger
from mypy_boto3_rds import RDSClient
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


class GetInstanceDetailHandler:
    """Handler for RDS DB Instance detail operations in the RDS MCP Server.

    This class provides tools for retrieving detailed information about
    RDS database instances in your AWS account.
    """

    def __init__(self, mcp, rds_client: RDSClient):
        """Initialize the RDS Instance Detail handler.

        Args:
            mcp: The MCP server instance
            rds_client: The AWS RDS client instance
        """
        self.mcp = mcp
        self.rds_client = rds_client

        # Register resources
        self.mcp.resource(
            uri='aws-rds://db-instance/{instance_id}',
            name='GetDBInstanceDetails',
            mime_type='application/json',
            description=GET_INSTANCE_DETAIL_DOCSTRING,
        )(self.get_instance_detail)

    async def get_instance_detail(self, instance_id: str = Field(..., description='')) -> str:
        """Get detailed information about a specific instance as a resource.

        Args:
            instance_id: The instance identifier
            rds_client: AWS RDS client

        Returns:
            JSON string with instance details
        """
        try:
            logger.info(f'Getting instance detail resource for {instance_id}')
            response = await asyncio.to_thread(
                self.rds_client.describe_db_instances, DBInstanceIdentifier=instance_id
            )

            instances = response.get('DBInstances', [])
            if not instances:
                return json.dumps({'error': f'Instance {instance_id} not found'}, indent=2)

            instance = format_instance_info(instances[0])
            instance.resource_uri = f'{RESOURCE_PREFIX_DB_INSTANCE}/{instance_id}'

            return json.dumps(instance.model_dump(), indent=2)
        except Exception as e:
            error_result = await handle_aws_error(
                f'get_instance_detail_resource({instance_id})', e
            )
            return json.dumps(error_result, indent=2)
