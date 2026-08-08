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

"""Amazon Connect historical metrics tools for the MCP server.

Wraps the Connect GetMetricDataV2 API so an assistant can build historical
reports (handle time, abandonment, service level, occupancy, etc.) across
queues, channels, agents, and routing profiles using natural language.
"""

from awslabs.amazon_connect_mcp_server.aws_common import get_aws_client
from awslabs.amazon_connect_mcp_server.common import (
    paginate_with_next_token,
    parse_iso_datetime,
    split_into_intervals,
    to_utc_iso,
)
from awslabs.amazon_connect_mcp_server.connect_historical.constants import (
    COMMON_HISTORICAL_METRICS,
    DEFAULT_SERVICE_LEVEL_THRESHOLD_SECONDS,
    INTERVAL_FETCH_BUDGET_SECONDS,
    MAX_INTERVAL_CHUNKS,
    MAX_INTERVAL_HOURS,
    MAX_LOOKBACK_DAYS,
    THRESHOLD_METRICS,
    VALID_HISTORICAL_GROUPINGS,
)
from awslabs.amazon_connect_mcp_server.connect_historical.models import (
    HistoricalMetricDataResponse,
    HistoricalMetricResult,
    HistoricalMetricValue,
)
from datetime import datetime, timedelta, timezone
from loguru import logger
from mcp.server.fastmcp import Context
from pydantic import Field
from time import monotonic
from typing import Annotated, Any, Dict, List


class ConnectHistoricalTools:
    """Historical metric tools for Amazon Connect (GetMetricDataV2)."""

    def __init__(self):
        """Initialize the Amazon Connect historical tools."""
        pass

    def register(self, mcp):
        """Register all historical tools with the MCP server."""
        mcp.tool(name='get_historical_metric_data')(self.get_historical_metric_data)

    async def get_historical_metric_data(
        self,
        ctx: Context,
        instance_id: Annotated[
            str,
            Field(description='The identifier of the Amazon Connect instance.'),
        ],
        start_time: Annotated[
            str | None,
            Field(
                description="Start of the reporting interval in ISO 8601 format (e.g., '2025-06-01T00:00:00Z'). Defaults to 24 hours ago. Data is only available for the last 90 days. Ranges wider than 24 hours are automatically split into 24-hour intervals."
            ),
        ] = None,
        end_time: Annotated[
            str | None,
            Field(
                description='End of the reporting interval in ISO 8601 format. Defaults to the current time.'
            ),
        ] = None,
        metrics: Annotated[
            list[str] | None,
            Field(
                description='List of historical metric names to retrieve (e.g., CONTACTS_HANDLED, AVG_HANDLE_TIME, SERVICE_LEVEL, ABANDONMENT_RATE). Defaults to a common reporting set if omitted.'
            ),
        ] = None,
        queue_ids: Annotated[
            list[str] | None,
            Field(description='Optional list of queue IDs to filter the report by.'),
        ] = None,
        channels: Annotated[
            list[str] | None,
            Field(
                description="Optional list of channels to filter by. Valid values: 'VOICE', 'CHAT', 'TASK'."
            ),
        ] = None,
        agent_ids: Annotated[
            list[str] | None,
            Field(description='Optional list of agent (user) IDs to filter the report by.'),
        ] = None,
        routing_profile_ids: Annotated[
            list[str] | None,
            Field(description='Optional list of routing profile IDs to filter the report by.'),
        ] = None,
        groupings: Annotated[
            list[str] | None,
            Field(
                description="Optional groupings for the results. Valid values include 'QUEUE', 'CHANNEL', 'AGENT', 'ROUTING_PROFILE'."
            ),
        ] = None,
        service_level_threshold_seconds: Annotated[
            int | None,
            Field(
                description='Threshold in seconds for SERVICE_LEVEL (answered within X seconds). Defaults to 120 seconds when SERVICE_LEVEL is requested.'
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
    ) -> HistoricalMetricDataResponse:
        """Get historical metrics for an Amazon Connect instance (GetMetricDataV2).

        This tool builds historical reports for a contact center over a time
        window. It can answer questions such as "how many contacts did each queue
        handle yesterday", "what was the average handle time per agent last week",
        or "what is our service level by channel".

        Usage: Resolve the instance_id with list_connect_instances. Optionally
        resolve queue_ids, agent_ids, or routing_profile_ids with the discovery
        tools, then choose the metrics and groupings you want. Data is only
        available for the last 90 days.

        Time range handling: The Amazon Connect API caps a single request at a
        24-hour window. This tool automatically splits a wider requested range
        (up to 90 days) into consecutive 24-hour intervals and returns one set of
        result rows per interval. Each row carries interval_start/interval_end so
        per-interval values are never conflated. Average and rate metrics
        (e.g., AVG_HANDLE_TIME, SERVICE_LEVEL) are reported per interval and are
        not aggregated across intervals.

        Args:
            ctx: The MCP context object for error handling and logging.
            instance_id: The identifier of the Connect instance.
            start_time: ISO 8601 start of the interval. Defaults to 24 hours ago.
            end_time: ISO 8601 end of the interval. Defaults to now.
            metrics: List of historical metric names. Defaults to a common set.
            queue_ids: Optional queue IDs to filter by.
            channels: Optional channels (VOICE, CHAT, TASK) to filter by.
            agent_ids: Optional agent IDs to filter by.
            routing_profile_ids: Optional routing profile IDs to filter by.
            groupings: Optional groupings (QUEUE, CHANNEL, AGENT, ROUTING_PROFILE).
            service_level_threshold_seconds: Threshold for SERVICE_LEVEL metric.
            max_items: Maximum number of grouped results to return (default: 100).
            region: AWS region to query.
            profile_name: AWS CLI profile name to use for access.

        Returns:
            HistoricalMetricDataResponse: The grouped historical metric results,
            one set of rows per 24-hour interval.
        """
        try:
            if max_items is None or not isinstance(max_items, int):
                max_items = 100

            # Resolve time window (timezone-aware, UTC).
            end_dt = parse_iso_datetime(end_time) if end_time else datetime.now(timezone.utc)
            start_dt = parse_iso_datetime(start_time) if start_time else end_dt - timedelta(days=1)

            if start_dt >= end_dt:
                raise ValueError('start_time must be earlier than end_time')

            earliest_allowed = datetime.now(timezone.utc) - timedelta(days=MAX_LOOKBACK_DAYS)
            if start_dt < earliest_allowed:
                raise ValueError(
                    f'start_time is older than {MAX_LOOKBACK_DAYS} days. '
                    'GetMetricDataV2 only retains data for the last 90 days.'
                )

            metric_names = metrics if metrics else list(COMMON_HISTORICAL_METRICS)

            if groupings:
                bad_groupings = [g for g in groupings if g not in VALID_HISTORICAL_GROUPINGS]
                if bad_groupings:
                    raise ValueError(
                        f'Unsupported grouping(s): {", ".join(bad_groupings)}. '
                        f'Valid groupings: {", ".join(sorted(VALID_HISTORICAL_GROUPINGS))}'
                    )

            client = get_aws_client('connect', region, profile_name)
            resource_arn = self._resolve_instance_arn(client, instance_id)

            filters = self._build_filters(
                queue_ids=queue_ids,
                channels=channels,
                agent_ids=agent_ids,
                routing_profile_ids=routing_profile_ids,
            )
            if not self._has_non_channel_filter(filters):
                # GetMetricDataV2 requires at least one filter key other than CHANNEL.
                # When the caller only supplied a channel (or nothing), default the
                # report to the instance's queues (the API caps QUEUE at 100 values).
                default_queue_ids = self._list_queue_ids(client, instance_id, limit=100)
                if not default_queue_ids:
                    raise ValueError(
                        'No queues found for this instance to build a default report. '
                        'Provide queue_ids, agent_ids, or routing_profile_ids explicitly.'
                    )
                filters.append({'FilterKey': 'QUEUE', 'FilterValues': default_queue_ids})

            metric_definitions = self._build_metric_definitions(
                metric_names, service_level_threshold_seconds
            )

            base_request: Dict[str, Any] = {
                'ResourceArn': resource_arn,
                'Filters': filters,
                'Metrics': metric_definitions,
            }
            if groupings:
                base_request['Groupings'] = groupings

            # GetMetricDataV2 caps each request at a 24-hour window, so split the
            # requested range into consecutive intervals and fetch each one.
            intervals = list(
                split_into_intervals(
                    start_dt,
                    end_dt,
                    interval_hours=MAX_INTERVAL_HOURS,
                    max_chunks=MAX_INTERVAL_CHUNKS,
                )
            )

            results: List[HistoricalMetricResult] = []
            has_more = False
            budget_exceeded = False
            deadline = monotonic() + INTERVAL_FETCH_BUDGET_SECONDS
            intervals_fetched = 0
            for chunk_start, chunk_end in intervals:
                if has_more:
                    break
                # Stop before exceeding the host's per-operation timeout. Return
                # what we have so far with a clear message instead of hanging.
                if monotonic() >= deadline:
                    budget_exceeded = True
                    break

                request = dict(base_request)
                request['StartTime'] = chunk_start
                request['EndTime'] = chunk_end
                interval_start_iso = to_utc_iso(chunk_start)
                interval_end_iso = to_utc_iso(chunk_end)

                for page in paginate_with_next_token(client.get_metric_data_v2, request):
                    for entry in page.get('MetricResults', []):
                        if len(results) < max_items:
                            results.append(
                                self._transform_metric_result(
                                    entry, interval_start_iso, interval_end_iso
                                )
                            )
                        else:
                            # More data exists than the caller asked for.
                            has_more = True
                            break
                    if has_more:
                        break
                    if page.get('NextToken') and len(results) >= max_items:
                        has_more = True
                        break

                intervals_fetched += 1

            if budget_exceeded:
                has_more = True
                message = (
                    f'Returned partial results: fetched {intervals_fetched} of '
                    f'{len(intervals)} intervals before reaching the time budget. '
                    'Narrow the time range or add filters for a complete report.'
                )
            elif results:
                message = None
            else:
                message = 'No historical metric data returned for the given filters'

            logger.info(
                f'get_historical_metric_data returned {len(results)} grouped results '
                f'across {intervals_fetched}/{len(intervals)} interval(s) '
                f'(has_more_results={has_more}, budget_exceeded={budget_exceeded})'
            )
            return HistoricalMetricDataResponse(
                resource_arn=resource_arn,
                start_time=to_utc_iso(start_dt),
                end_time=to_utc_iso(end_dt),
                interval_count=len(intervals),
                results=results,
                has_more_results=has_more,
                message=message,
            )
        except Exception as e:
            logger.error(f'Error in get_historical_metric_data: {str(e)}')
            await ctx.error(f'Error getting historical metric data: {str(e)}')
            raise

    def _resolve_instance_arn(self, client, instance_id: str) -> str:
        """Resolve an instance ARN from its id. GetMetricDataV2 needs the ARN."""
        if instance_id.startswith('arn:'):
            return instance_id
        response = client.describe_instance(InstanceId=instance_id)
        return response.get('Instance', {}).get('Arn', instance_id)

    def _build_filters(
        self,
        queue_ids: List[str] | None,
        channels: List[str] | None,
        agent_ids: List[str] | None,
        routing_profile_ids: List[str] | None,
    ) -> List[Dict[str, Any]]:
        """Build the GetMetricDataV2 Filters list from the supplied dimensions."""
        filters: List[Dict[str, Any]] = []
        if queue_ids:
            filters.append({'FilterKey': 'QUEUE', 'FilterValues': queue_ids})
        if channels:
            filters.append({'FilterKey': 'CHANNEL', 'FilterValues': channels})
        if agent_ids:
            filters.append({'FilterKey': 'AGENT', 'FilterValues': agent_ids})
        if routing_profile_ids:
            filters.append({'FilterKey': 'ROUTING_PROFILE', 'FilterValues': routing_profile_ids})
        return filters

    def _has_non_channel_filter(self, filters: List[Dict[str, Any]]) -> bool:
        """Return True if any filter key other than CHANNEL is present.

        GetMetricDataV2 rejects requests whose only filter key is CHANNEL.
        """
        return any(f.get('FilterKey') != 'CHANNEL' for f in filters)

    def _list_queue_ids(self, client, instance_id: str, limit: int = 100) -> List[str]:
        """Return up to ``limit`` queue IDs for the instance for default reporting."""
        queue_ids: List[str] = []
        paginator = client.get_paginator('list_queues')
        for page in paginator.paginate(InstanceId=instance_id):
            for item in page.get('QueueSummaryList', []):
                queue_id = item.get('Id')
                if queue_id:
                    queue_ids.append(queue_id)
                if len(queue_ids) >= limit:
                    return queue_ids
        return queue_ids

    def _build_metric_definitions(
        self, metric_names: List[str], service_level_threshold_seconds: int | None
    ) -> List[Dict[str, Any]]:
        """Build the GetMetricDataV2 Metrics list, adding thresholds where required."""
        threshold_seconds = (
            service_level_threshold_seconds
            if isinstance(service_level_threshold_seconds, int)
            else DEFAULT_SERVICE_LEVEL_THRESHOLD_SECONDS
        )

        definitions: List[Dict[str, Any]] = []
        for name in metric_names:
            definition: Dict[str, Any] = {'Name': name}
            if name in THRESHOLD_METRICS:
                definition['Threshold'] = [
                    {
                        'Comparison': 'LT',
                        'ThresholdValue': float(threshold_seconds),
                    }
                ]
            definitions.append(definition)
        return definitions

    def _transform_metric_result(
        self,
        entry: Dict[str, Any],
        interval_start: str | None = None,
        interval_end: str | None = None,
    ) -> HistoricalMetricResult:
        """Transform a GetMetricDataV2 MetricResult into our model.

        Args:
            entry: A single MetricResult entry from the API response.
            interval_start: ISO 8601 start of the 24-hour interval this row covers.
            interval_end: ISO 8601 end of the 24-hour interval this row covers.

        Returns:
            The transformed HistoricalMetricResult.
        """
        dimensions: Dict[str, str] = {}
        for key, value in (entry.get('Dimensions') or {}).items():
            dimensions[key] = value

        metrics = []
        for collection in entry.get('Collections', []):
            metric = collection.get('Metric', {})
            metrics.append(
                HistoricalMetricValue(
                    name=metric.get('Name', ''),
                    value=collection.get('Value'),
                )
            )

        return HistoricalMetricResult(
            dimensions=dimensions,
            interval_start=interval_start,
            interval_end=interval_end,
            metrics=metrics,
        )
