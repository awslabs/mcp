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

"""List Instances handler for the RDS Control Plane MCP Server."""

import asyncio
import json
from awslabs.rds_control_plane_mcp_server.common.constants import RESOURCE_PREFIX_DB_INSTANCE
from awslabs.rds_control_plane_mcp_server.common.models import InstanceListModel
from awslabs.rds_control_plane_mcp_server.common.utils import (
    format_instance_info,
    handle_aws_error,
)
from loguru import logger
from mypy_boto3_rds import RDSClient


LIST_INSTANCES_RESOURCE_DESCRIPTION = """List all available Amazon RDS instances in your account.

<use_case>
Use this resource to discover all available RDS database instances in your AWS account.
</use_case>

<important_notes>
1. The response provides essential information about each instance
2. Instance identifiers returned can be used with the db-instance/{instance_id} resource
3. Instances are filtered to the AWS region specified in your environment configuration
</important_notes>

## Response structure
Returns a JSON document containing:
- `instances`: Array of DB instance objects
- `count`: Number of instances found
- `resource_uri`: Base URI for accessing instances
"""


class ListInstancesHandler:
    """Handler for RDS DB Instance listing operations in the RDS MCP Server.

    This class provides tools for discovering and retrieving information about
    RDS database instances in your AWS account.
    """

    def __init__(self, mcp, rds_client: RDSClient):
        """Initialize the RDS Instance handler.

        Args:
            mcp: The MCP server instance
            rds_client: The AWS RDS client instance
        """
        self.mcp = mcp
        self.rds_client = rds_client

        # Register resources
        self.mcp.resource(
            uri='aws-rds://db-instance',
            name='ListDBInstances',
            mime_type='application/json',
            description=LIST_INSTANCES_RESOURCE_DESCRIPTION,
        )(self.list_instances)

    async def list_instances(self) -> str:
        """Get list of all RDS instances as a resource.

        Returns:
            JSON string with instance list
        """
        try:
            logger.info('Getting instance list resource')

            instances = []
            response = await asyncio.to_thread(self.rds_client.describe_db_instances)

            for instance in response.get('DBInstances', []):
                instances.append(format_instance_info(instance))

            # pagination if there's a marker for next page
            while 'Marker' in response:
                response = await asyncio.to_thread(
                    self.rds_client.describe_db_instances, Marker=response['Marker']
                )
                for instance in response.get('DBInstances', []):
                    instances.append(format_instance_info(instance))

            result = InstanceListModel(
                instances=instances, count=len(instances), resource_uri=RESOURCE_PREFIX_DB_INSTANCE
            )

            return json.dumps(result.model_dump(), indent=2)
        except Exception as e:
            error_result = await handle_aws_error('get_instance_list_resource', e)
            return json.dumps(error_result, indent=2)
