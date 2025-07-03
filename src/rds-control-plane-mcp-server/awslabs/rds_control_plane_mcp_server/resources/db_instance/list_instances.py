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

from ...common.connection import RDSConnectionManager
from ...common.decorator import handle_exceptions
from ...common.models import InstanceListModel
from ...common.server import mcp
from ...common.utils import paginate_aws_api_call
from .utils import format_instance_summary, InstanceSummaryModel
from loguru import logger


LIST_INSTANCES_RESOURCE_DESCRIPTION = """List all available Amazon RDS instances in your account.

<use_case>
Use this resource to discover all available RDS database instances in your AWS account.
</use_case>

<important_notes>
1. The response provides essential information about each instance
2. Instance identifiers returned can be used with other tools and resources in this MCP server
3. Keep note of the instance_id and dbi_resource_id for use with other tools
4. Instances are filtered to the AWS region specified in your environment configuration
5. Use the `aws-rds://db-instance/{instance_id}` to get more information about a specific instance
</important_notes>

## Response structure
Returns a JSON document containing:
- `instances`: Array of DB instance objects
- `count`: Number of instances found
- `resource_uri`: Base URI for accessing instances

Each instance object contains:
- `instance_id`: Unique identifier for the instance
- `dbi_resource_id`: The unique resource identifier for this instance
- `status`: Current status of the instance
- `engine`: Database engine type
- `engine_version`: The version of the database engine
- `instance_class`: The instance type (e.g., db.t3.medium)
- `availability_zone`: The AZ where the instance is located
- `multi_az`: Whether the instance has Multi-AZ deployment
- Other essential instance attributes
"""


class InstanceSummaryListModel(BaseModel):
    """DB instance summary list model."""

    instances: List[InstanceSummaryModel] = Field(default_factory=list, description='List of DB instances')
    count: int = Field(description='Total number of DB instances')
    resource_uri: str = Field(description='The resource URI for the DB instances')


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
        format_function=format_instance_summary,
        result_key='DBInstances'
    )

    result = InstanceListModel(
        instances=instances, count=len(instances), resource_uri='aws-rds://db-instance'
    )

    return result
