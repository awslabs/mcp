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

"""Amazon Connect administration / discovery tools for the MCP server.

These read-only tools allow an assistant to discover the resources it needs to
build reports: Connect instances, queues, agents (users), and routing profiles.
Their identifiers feed the realtime and historical metric tools.
"""

from awslabs.amazon_connect_mcp_server.aws_common import get_aws_client
from awslabs.amazon_connect_mcp_server.connect_admin.models import (
    AgentSummary,
    InstanceSummary,
    ListAgentsResponse,
    ListInstancesResponse,
    ListQueuesResponse,
    ListRoutingProfilesResponse,
    QueueSummary,
    RoutingProfileSummary,
)
from loguru import logger
from mcp.server.fastmcp import Context
from pydantic import Field
from typing import Annotated, Any


class ConnectAdminTools:
    """Discovery tools that surface Amazon Connect resource identifiers."""

    def __init__(self):
        """Initialize the Amazon Connect administration tools."""
        pass

    def register(self, mcp):
        """Register all administration tools with the MCP server."""
        mcp.tool(name='list_connect_instances')(self.list_connect_instances)
        mcp.tool(name='list_queues')(self.list_queues)
        mcp.tool(name='list_agents')(self.list_agents)
        mcp.tool(name='list_routing_profiles')(self.list_routing_profiles)

    async def list_connect_instances(
        self,
        ctx: Context,
        max_items: Annotated[
            int | None,
            Field(description='Maximum number of instances to return (default: 50).'),
        ] = 50,
        region: Annotated[
            str | None,
            Field(
                description='AWS region to query. Defaults to AWS_REGION environment variable or us-east-1 if not set.'
            ),
        ] = None,
        profile_name: Annotated[
            str | None,
            Field(
                description='AWS CLI Profile Name to use for AWS access. Falls back to AWS_PROFILE environment variable if not specified, or uses default AWS credential chain.'
            ),
        ] = None,
    ) -> ListInstancesResponse:
        """List the Amazon Connect instances in the account/region.

        Use this tool first to discover the instance_id required by nearly every
        other reporting tool. Each contact center is represented by an instance.

        Args:
            ctx: The MCP context object for error handling and logging.
            max_items: Maximum number of instances to return (default: 50).
            region: AWS region to query.
            profile_name: AWS CLI profile name to use for access.

        Returns:
            ListInstancesResponse: The Connect instances found in the region.
        """
        try:
            if max_items is None or not isinstance(max_items, int):
                max_items = 50

            client = get_aws_client('connect', region, profile_name)
            paginator = client.get_paginator('list_instances')
            page_iterator = paginator.paginate(PaginationConfig={'MaxItems': max_items})

            instances = []
            for page in page_iterator:
                for item in page.get('InstanceSummaryList', []):
                    instances.append(
                        InstanceSummary(
                            instance_id=item.get('Id', ''),
                            instance_arn=item.get('Arn', ''),
                            instance_alias=item.get('InstanceAlias'),
                            service_role=item.get('ServiceRole'),
                            instance_status=item.get('InstanceStatus'),
                        )
                    )

            message = None if instances else 'No Amazon Connect instances found'
            logger.info(f'Found {len(instances)} Connect instances')
            return ListInstancesResponse(instances=instances, message=message)
        except Exception as e:
            logger.error(f'Error in list_connect_instances: {str(e)}')
            await ctx.error(f'Error listing Connect instances: {str(e)}')
            raise

    async def list_queues(
        self,
        ctx: Context,
        instance_id: Annotated[
            str,
            Field(description='The identifier of the Amazon Connect instance.'),
        ],
        queue_types: Annotated[
            list[str] | None,
            Field(
                description="Optional filter for queue types. Valid values: 'STANDARD', 'AGENT'. Defaults to all types."
            ),
        ] = None,
        max_items: Annotated[
            int | None,
            Field(description='Maximum number of queues to return (default: 100).'),
        ] = 100,
        region: Annotated[
            str | None,
            Field(description='AWS region to query.'),
        ] = None,
        profile_name: Annotated[
            str | None,
            Field(description='AWS CLI Profile Name to use for AWS access.'),
        ] = None,
    ) -> ListQueuesResponse:
        """List the queues configured in an Amazon Connect instance.

        Queue identifiers returned here can be passed as filters/groupings to the
        realtime and historical metric tools.

        Args:
            ctx: The MCP context object for error handling and logging.
            instance_id: The identifier of the Connect instance.
            queue_types: Optional list of queue types to filter by.
            max_items: Maximum number of queues to return (default: 100).
            region: AWS region to query.
            profile_name: AWS CLI profile name to use for access.

        Returns:
            ListQueuesResponse: The queues found in the instance.
        """
        try:
            if max_items is None or not isinstance(max_items, int):
                max_items = 100

            client = get_aws_client('connect', region, profile_name)
            kwargs: dict[str, Any] = {'InstanceId': instance_id}
            if queue_types:
                kwargs['QueueTypes'] = queue_types

            paginator = client.get_paginator('list_queues')
            page_iterator = paginator.paginate(
                PaginationConfig={'MaxItems': max_items + 1}, **kwargs
            )

            queues = []
            total = 0
            for page in page_iterator:
                for item in page.get('QueueSummaryList', []):
                    total += 1
                    if len(queues) < max_items:
                        queues.append(
                            QueueSummary(
                                queue_id=item.get('Id', ''),
                                queue_arn=item.get('Arn', ''),
                                name=item.get('Name'),
                                queue_type=item.get('QueueType'),
                            )
                        )

            has_more = total > max_items
            message = None if queues else 'No queues found for this instance'
            logger.info(f'Found {len(queues)} queues (has_more_results={has_more})')
            return ListQueuesResponse(queues=queues, has_more_results=has_more, message=message)
        except Exception as e:
            logger.error(f'Error in list_queues: {str(e)}')
            await ctx.error(f'Error listing queues: {str(e)}')
            raise

    async def list_agents(
        self,
        ctx: Context,
        instance_id: Annotated[
            str,
            Field(description='The identifier of the Amazon Connect instance.'),
        ],
        max_items: Annotated[
            int | None,
            Field(description='Maximum number of agents to return (default: 100).'),
        ] = 100,
        region: Annotated[
            str | None,
            Field(description='AWS region to query.'),
        ] = None,
        profile_name: Annotated[
            str | None,
            Field(description='AWS CLI Profile Name to use for AWS access.'),
        ] = None,
    ) -> ListAgentsResponse:
        """List the agents (users) configured in an Amazon Connect instance.

        Agent identifiers returned here can be passed as filters/groupings to the
        realtime and historical metric tools to build per-agent reports.

        Args:
            ctx: The MCP context object for error handling and logging.
            instance_id: The identifier of the Connect instance.
            max_items: Maximum number of agents to return (default: 100).
            region: AWS region to query.
            profile_name: AWS CLI profile name to use for access.

        Returns:
            ListAgentsResponse: The agents found in the instance.
        """
        try:
            if max_items is None or not isinstance(max_items, int):
                max_items = 100

            client = get_aws_client('connect', region, profile_name)
            paginator = client.get_paginator('list_users')
            page_iterator = paginator.paginate(
                InstanceId=instance_id, PaginationConfig={'MaxItems': max_items + 1}
            )

            agents = []
            total = 0
            for page in page_iterator:
                for item in page.get('UserSummaryList', []):
                    total += 1
                    if len(agents) < max_items:
                        agents.append(
                            AgentSummary(
                                user_id=item.get('Id', ''),
                                user_arn=item.get('Arn', ''),
                                username=item.get('Username'),
                            )
                        )

            has_more = total > max_items
            message = None if agents else 'No agents found for this instance'
            logger.info(f'Found {len(agents)} agents (has_more_results={has_more})')
            return ListAgentsResponse(agents=agents, has_more_results=has_more, message=message)
        except Exception as e:
            logger.error(f'Error in list_agents: {str(e)}')
            await ctx.error(f'Error listing agents: {str(e)}')
            raise

    async def list_routing_profiles(
        self,
        ctx: Context,
        instance_id: Annotated[
            str,
            Field(description='The identifier of the Amazon Connect instance.'),
        ],
        max_items: Annotated[
            int | None,
            Field(description='Maximum number of routing profiles to return (default: 100).'),
        ] = 100,
        region: Annotated[
            str | None,
            Field(description='AWS region to query.'),
        ] = None,
        profile_name: Annotated[
            str | None,
            Field(description='AWS CLI Profile Name to use for AWS access.'),
        ] = None,
    ) -> ListRoutingProfilesResponse:
        """List the routing profiles configured in an Amazon Connect instance.

        Routing profiles can be used to group historical and realtime metrics.

        Args:
            ctx: The MCP context object for error handling and logging.
            instance_id: The identifier of the Connect instance.
            max_items: Maximum number of routing profiles to return (default: 100).
            region: AWS region to query.
            profile_name: AWS CLI profile name to use for access.

        Returns:
            ListRoutingProfilesResponse: The routing profiles found in the instance.
        """
        try:
            if max_items is None or not isinstance(max_items, int):
                max_items = 100

            client = get_aws_client('connect', region, profile_name)
            paginator = client.get_paginator('list_routing_profiles')
            page_iterator = paginator.paginate(
                InstanceId=instance_id, PaginationConfig={'MaxItems': max_items + 1}
            )

            profiles = []
            total = 0
            for page in page_iterator:
                for item in page.get('RoutingProfileSummaryList', []):
                    total += 1
                    if len(profiles) < max_items:
                        profiles.append(
                            RoutingProfileSummary(
                                routing_profile_id=item.get('Id', ''),
                                routing_profile_arn=item.get('Arn', ''),
                                name=item.get('Name'),
                            )
                        )

            has_more = total > max_items
            message = None if profiles else 'No routing profiles found for this instance'
            logger.info(f'Found {len(profiles)} routing profiles (has_more_results={has_more})')
            return ListRoutingProfilesResponse(
                routing_profiles=profiles, has_more_results=has_more, message=message
            )
        except Exception as e:
            logger.error(f'Error in list_routing_profiles: {str(e)}')
            await ctx.error(f'Error listing routing profiles: {str(e)}')
            raise
