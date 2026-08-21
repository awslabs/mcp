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

"""Amazon Connect realtime metrics tools for the MCP server.

Wraps the Connect GetCurrentMetricData and GetCurrentUserData APIs so an
assistant can answer questions like "how many contacts are in queue right now"
or "which agents are available" in natural language.
"""

from awslabs.amazon_connect_mcp_server.aws_common import get_aws_client
from awslabs.amazon_connect_mcp_server.common import paginate_with_next_token
from awslabs.amazon_connect_mcp_server.connect_realtime.constants import (
    CURRENT_METRIC_UNITS,
    DEFAULT_CURRENT_METRICS,
    VALID_CURRENT_GROUPINGS,
)
from awslabs.amazon_connect_mcp_server.connect_realtime.models import (
    AgentRealtimeStatus,
    AgentRealtimeStatusResponse,
    CurrentMetricDataResponse,
    CurrentMetricResult,
    CurrentMetricValue,
)
from loguru import logger
from mcp.server.fastmcp import Context
from pydantic import Field
from typing import Annotated, Any, Dict, List


class ConnectRealtimeTools:
    """Realtime (current) metric tools for Amazon Connect."""

    def __init__(self):
        """Initialize the Amazon Connect realtime tools."""
        pass

    def register(self, mcp):
        """Register all realtime tools with the MCP server."""
        mcp.tool(name='get_current_metric_data')(self.get_current_metric_data)
        mcp.tool(name='get_current_agent_status')(self.get_current_agent_status)

    async def get_current_metric_data(
        self,
        ctx: Context,
        instance_id: Annotated[
            str,
            Field(description='The identifier of the Amazon Connect instance.'),
        ],
        queue_ids: Annotated[
            list[str] | None,
            Field(
                description='Optional list of queue IDs to scope the metrics to. If omitted, all queues are included.'
            ),
        ] = None,
        channels: Annotated[
            list[str] | None,
            Field(
                description="Optional list of channels to filter by. Valid values: 'VOICE', 'CHAT', 'TASK'."
            ),
        ] = None,
        metrics: Annotated[
            list[str] | None,
            Field(
                description='Optional list of current metric names to retrieve (e.g., CONTACTS_IN_QUEUE, AGENTS_AVAILABLE, OLDEST_CONTACT_AGE). Defaults to a common set if omitted.'
            ),
        ] = None,
        groupings: Annotated[
            list[str] | None,
            Field(
                description="Optional list of groupings for the results. Valid values: 'QUEUE', 'CHANNEL', 'ROUTING_PROFILE'."
            ),
        ] = None,
        max_items: Annotated[
            int | None,
            Field(description='Maximum number of grouped results to return (default: 100).'),
        ] = 100,
        region: Annotated[
            str | None,
            Field(description='AWS region to query.'),
        ] = None,
        profile_name: Annotated[
            str | None,
            Field(description='AWS CLI Profile Name to use for AWS access.'),
        ] = None,
    ) -> CurrentMetricDataResponse:
        """Get realtime (current) metrics for an Amazon Connect instance.

        This tool wraps the Connect GetCurrentMetricData API. Use it to answer
        operational questions about the current state of a contact center, such
        as the number of contacts waiting in queue, the oldest contact age, and
        how many agents are online or available.

        Usage: First resolve the instance_id with list_connect_instances and,
        optionally, queue_ids with list_queues. Then call this tool with the
        metrics you care about.

        Args:
            ctx: The MCP context object for error handling and logging.
            instance_id: The identifier of the Connect instance.
            queue_ids: Optional list of queue IDs to scope the metrics to.
            channels: Optional list of channels (VOICE, CHAT, TASK) to filter by.
            metrics: Optional list of current metric names. Defaults to a common set.
            groupings: Optional groupings (QUEUE, CHANNEL, ROUTING_PROFILE).
            max_items: Maximum number of grouped results to return (default: 100).
            region: AWS region to query.
            profile_name: AWS CLI profile name to use for access.

        Returns:
            CurrentMetricDataResponse: The grouped realtime metric results.
        """
        try:
            if max_items is None or not isinstance(max_items, int):
                max_items = 100

            metric_names = metrics if metrics else list(DEFAULT_CURRENT_METRICS)
            invalid = [m for m in metric_names if m not in CURRENT_METRIC_UNITS]
            if invalid:
                raise ValueError(
                    f'Unsupported current metric(s): {", ".join(invalid)}. '
                    f'Supported metrics: {", ".join(sorted(CURRENT_METRIC_UNITS))}'
                )

            if groupings:
                bad_groupings = [g for g in groupings if g not in VALID_CURRENT_GROUPINGS]
                if bad_groupings:
                    raise ValueError(
                        f'Unsupported grouping(s): {", ".join(bad_groupings)}. '
                        f'Valid groupings: {", ".join(sorted(VALID_CURRENT_GROUPINGS))}'
                    )

            client = get_aws_client('connect', region, profile_name)

            # Build the filters block. Queues are required by the API, so when no
            # queue is specified we leave Queues out and rely on channel filtering.
            filters: Dict[str, Any] = {}
            if queue_ids:
                filters['Queues'] = queue_ids
            if channels:
                filters['Channels'] = channels
            if not filters:
                # The API requires at least one filter dimension; default to all channels.
                filters['Channels'] = ['VOICE', 'CHAT', 'TASK']

            current_metrics = [
                {'Name': name, 'Unit': CURRENT_METRIC_UNITS[name]} for name in metric_names
            ]

            request: Dict[str, Any] = {
                'InstanceId': instance_id,
                'Filters': filters,
                'CurrentMetrics': current_metrics,
            }
            if groupings:
                request['Groupings'] = groupings

            results: List[CurrentMetricResult] = []
            snapshot_time = None
            has_more = False
            for page in paginate_with_next_token(client.get_current_metric_data, request):
                if snapshot_time is None and page.get('DataSnapshotTime') is not None:
                    snapshot_time = page['DataSnapshotTime'].isoformat()
                for entry in page.get('MetricResults', []):
                    if len(results) < max_items:
                        results.append(self._transform_metric_result(entry))
                    else:
                        has_more = True
                        break
                if has_more:
                    break
                if page.get('NextToken') and len(results) >= max_items:
                    has_more = True
                    break

            message = None if results else 'No realtime metric data returned for the given filters'
            logger.info(
                f'get_current_metric_data returned {len(results)} grouped results '
                f'(has_more_results={has_more})'
            )
            return CurrentMetricDataResponse(
                instance_id=instance_id,
                data_snapshot_time=snapshot_time,
                results=results,
                has_more_results=has_more,
                message=message,
            )
        except Exception as e:
            logger.error(f'Error in get_current_metric_data: {str(e)}')
            await ctx.error(f'Error getting current metric data: {str(e)}')
            raise

    async def get_current_agent_status(
        self,
        ctx: Context,
        instance_id: Annotated[
            str,
            Field(description='The identifier of the Amazon Connect instance.'),
        ],
        queue_ids: Annotated[
            list[str] | None,
            Field(
                description='Optional list of queue IDs to scope the agent data to. If omitted, all agents are included.'
            ),
        ] = None,
        agent_ids: Annotated[
            list[str] | None,
            Field(description='Optional list of agent (user) IDs to scope the data to.'),
        ] = None,
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
    ) -> AgentRealtimeStatusResponse:
        """Get the current realtime status of agents in an Amazon Connect instance.

        This tool wraps the Connect GetCurrentUserData API. Use it to report on
        which agents are online, their current status (Available, On Contact,
        After Contact Work, Offline), how long they have been in that status, and
        how many contacts they are actively handling.

        Usage: Resolve the instance_id with list_connect_instances and optionally
        narrow by queue_ids (list_queues) or agent_ids (list_agents).

        Args:
            ctx: The MCP context object for error handling and logging.
            instance_id: The identifier of the Connect instance.
            queue_ids: Optional list of queue IDs to scope the agent data to.
            agent_ids: Optional list of agent (user) IDs to scope the data to.
            max_items: Maximum number of agents to return (default: 100).
            region: AWS region to query.
            profile_name: AWS CLI profile name to use for access.

        Returns:
            AgentRealtimeStatusResponse: The realtime status of the matching agents.
        """
        try:
            if max_items is None or not isinstance(max_items, int):
                max_items = 100

            client = get_aws_client('connect', region, profile_name)

            filters: Dict[str, Any] = {}
            if queue_ids:
                filters['Queues'] = queue_ids
            if agent_ids:
                filters['Agents'] = agent_ids
            if not filters:
                # GetCurrentUserData requires at least one filter; default to all agents
                # by way of the routing profile-agnostic Agents filter is not possible,
                # so we require a queue scope. Raise a helpful error instead.
                raise ValueError(
                    'At least one of queue_ids or agent_ids must be provided to scope agent data.'
                )

            request: Dict[str, Any] = {
                'InstanceId': instance_id,
                'Filters': filters,
            }

            agents: List[AgentRealtimeStatus] = []
            has_more = False
            for page in paginate_with_next_token(client.get_current_user_data, request):
                for entry in page.get('UserDataList', []):
                    if len(agents) < max_items:
                        agents.append(self._transform_user_data(entry))
                    else:
                        has_more = True
                        break
                if has_more:
                    break
                if page.get('NextToken') and len(agents) >= max_items:
                    has_more = True
                    break

            message = None if agents else 'No agent data returned for the given filters'
            logger.info(
                f'get_current_agent_status returned {len(agents)} agents '
                f'(has_more_results={has_more})'
            )
            return AgentRealtimeStatusResponse(
                instance_id=instance_id,
                agents=agents,
                has_more_results=has_more,
                message=message,
            )
        except Exception as e:
            logger.error(f'Error in get_current_agent_status: {str(e)}')
            await ctx.error(f'Error getting current agent status: {str(e)}')
            raise

    def _transform_metric_result(self, entry: Dict[str, Any]) -> CurrentMetricResult:
        """Transform a GetCurrentMetricData MetricResult into our model."""
        dimensions: Dict[str, str] = {}
        dims = entry.get('Dimensions', {})
        queue = dims.get('Queue')
        if queue:
            dimensions['queue_id'] = queue.get('Id', '')
            dimensions['queue_arn'] = queue.get('Arn', '')
        if dims.get('Channel'):
            dimensions['channel'] = dims['Channel']
        routing_profile = dims.get('RoutingProfile')
        if routing_profile:
            dimensions['routing_profile_id'] = routing_profile.get('Id', '')

        collections = []
        for collection in entry.get('Collections', []):
            metric = collection.get('Metric', {})
            collections.append(
                CurrentMetricValue(
                    name=metric.get('Name', ''),
                    unit=metric.get('Unit', ''),
                    value=collection.get('Value'),
                )
            )

        return CurrentMetricResult(dimensions=dimensions, collections=collections)

    def _transform_user_data(self, entry: Dict[str, Any]) -> AgentRealtimeStatus:
        """Transform a GetCurrentUserData UserData entry into our model."""
        user = entry.get('User', {})
        status = entry.get('Status', {})
        routing_profile = entry.get('RoutingProfile', {})

        slots: Dict[str, int] = {}
        for channel, count in (entry.get('AvailableSlotsByChannel') or {}).items():
            slots[channel] = int(count)

        status_start = status.get('StatusStartTimestamp')

        return AgentRealtimeStatus(
            agent_id=user.get('Id'),
            agent_arn=user.get('Arn'),
            status_name=status.get('StatusName'),
            status_start_timestamp=status_start.isoformat() if status_start else None,
            routing_profile_name=routing_profile.get('Name'),
            available_slots_by_channel=slots,
            active_contacts=len(entry.get('Contacts', []) or []),
        )
