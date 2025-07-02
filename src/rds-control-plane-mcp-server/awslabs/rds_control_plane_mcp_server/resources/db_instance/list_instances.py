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

"""Resource for listing availble RDS DB Instances."""

import json
from ...common.connection import RDSConnectionManager
from ...common.constants import RESOURCE_PREFIX_DB_INSTANCE
from ...common.decorator import handle_exceptions
from ...common.models import InstanceListModel
from ...common.server import mcp
from ...common.utils import paginate_aws_api_call
from .utils import format_instance_info
from loguru import logger


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


@mcp.resource(
    uri='aws-rds://db-instance',
    name='ListDBInstances',
    mime_type='application/json',
    description=LIST_INSTANCES_RESOURCE_DESCRIPTION,
)
@handle_exceptions
async def list_instances() -> InstanceListModel:
    """Get list of all RDS instances as a resource.

    Returns:
        JSON string with instance list
    """
    logger.info('Getting instance list resource')
    rds_client = RDSConnectionManager.get_connection()

    instances = await paginate_aws_api_call(
        client_function=rds_client.describe_db_instances,
        format_function=format_instance_info,
        result_key='DBInstances'
    )

    result = InstanceListModel(
        instances=instances, count=len(instances), resource_uri=RESOURCE_PREFIX_DB_INSTANCE
    )

    return result
