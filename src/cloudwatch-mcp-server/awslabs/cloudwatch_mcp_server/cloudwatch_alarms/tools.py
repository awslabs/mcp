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

"""CloudWatch Alarms tools for MCP server."""

import boto3
import json
import os
from awslabs.cloudwatch_mcp_server import MCP_SERVER_VERSION
from awslabs.cloudwatch_mcp_server.cloudwatch_alarms.models import (
    ActiveAlarmsResponse,
    AlarmDetails,
    AlarmHistoryItem,
    AlarmHistoryResponse,
    CompositeAlarmComponentResponse,
    CompositeAlarmSummary,
    MetricAlarmSummary,
    TimeRangeSuggestion,
)
from botocore.config import Config
from datetime import datetime, timedelta
from loguru import logger
from mcp.server.fastmcp import Context
from pydantic import Field
from typing import Annotated, Any, Dict, List, Union


class CloudWatchAlarmsTools:
    """CloudWatch Alarms tools for MCP server."""

    def __init__(self):
        """Initialize the CloudWatch Alarms client."""
        # Initialize client
        aws_region: str = os.environ.get('AWS_REGION', 'us-east-1')
        config = Config(user_agent_extra=f'awslabs/mcp/cloudwatch-mcp-server/{MCP_SERVER_VERSION}')

        try:
            if aws_profile := os.environ.get('AWS_PROFILE'):
                self.cloudwatch_client = boto3.Session(
                    profile_name=aws_profile, region_name=aws_region
                ).client('cloudwatch', config=config)
            else:
                self.cloudwatch_client = boto3.Session(region_name=aws_region).client(
                    'cloudwatch', config=config
                )
        except Exception as e:
            logger.error(f'Error creating cloudwatch client: {str(e)}')
            raise

    def register(self, mcp):
        """Register all CloudWatch Alarms tools with the MCP server."""
        # Register get_active_alarms tool
        mcp.tool(name='get_active_alarms')(self.get_active_alarms)

        # Register get_alarm_history tool
        mcp.tool(name='get_alarm_history')(self.get_alarm_history)

    async def get_active_alarms(
        self,
        ctx: Context,
        max_items: Annotated[
            int | None,
            Field(
                description='Maximum number of alarms to return (default: 50). Large values may cause context window overflow and impact LLM performance.'
            ),
        ] = 50,
    ) -> ActiveAlarmsResponse:
        """Gets all CloudWatch alarms currently in ALARM state.

        This tool retrieves all CloudWatch alarms that are currently in the ALARM state,
        including both metric alarms and composite alarms. Results are optimized for
        LLM reasoning with summary-level information.

        Usage: Use this tool to get an overview of all active alarms in your AWS account
        for troubleshooting, monitoring, and operational awareness.

        Args:
            ctx: The MCP context object for error handling and logging.
            max_items: Maximum number of alarms to return (default: 50).

        Returns:
            ActiveAlarmsResponse: Response containing active alarms.

        Example:
            result = await get_active_alarms(ctx, max_items=25)
            if isinstance(result, ActiveAlarmsResponse):
                print(f"Found {len(result.metric_alarms + result.composite_alarms)} active alarms")
                for alarm in result.metric_alarms:
                    print(f"Metric Alarm: {alarm.alarm_name}")
                for alarm in result.composite_alarms:
                    print(f"Composite Alarm: {alarm.alarm_name}")
        """
        try:
            # Pydantic Field doesn't automatically fill the required type with default if a value is not provided.
            # Because of this behavior, checking explicitly if we got what we expected.
            # if max_items is None or not isinstance(max_items, int):
            if max_items is None or not isinstance(max_items, int):
                max_items = 50

            # Validate max_items parameter
            if max_items < 1:
                raise ValueError('max_items must be at least 1')

            # Use default client
            cloudwatch_client = self.cloudwatch_client

            # Fetch active alarms using paginator
            logger.info(f'Fetching up to {max_items} active alarms')

            paginator = cloudwatch_client.get_paginator('describe_alarms')
            page_iterator = paginator.paginate(
                StateValue='ALARM',
                AlarmTypes=['CompositeAlarm', 'MetricAlarm'],
                PaginationConfig={
                    # Requesting an extra item so that we can evaluate if there's extra
                    'MaxItems': max_items + 1
                },
            )

            # Collect results
            metric_alarms = []
            composite_alarms = []
            total_items_fetched = 0
            items_to_return = 0

            for page in page_iterator:
                metric_alarms_list = page.get('MetricAlarms', [])
                composite_alarms_list = page.get('CompositeAlarms', [])

                total_items_fetched += len(metric_alarms_list) + len(composite_alarms_list)

                for alarm in metric_alarms_list:
                    if items_to_return < max_items:
                        metric_alarms.append(self._transform_metric_alarm(alarm))
                        items_to_return += 1
                    else:
                        break

                for alarm in composite_alarms_list:
                    if items_to_return < max_items:
                        composite_alarms.append(self._transform_composite_alarm(alarm))
                        items_to_return += 1
                    else:
                        break

            # Determine if more results are available
            has_more_results = total_items_fetched > max_items

            # Handle empty results
            message = None
            if items_to_return == 0:
                message = 'No active alarms found'
            elif has_more_results:
                message = f'Showing {items_to_return} alarms (more available)'

            logger.info(
                f'Found {items_to_return} active alarms ({len(metric_alarms)} metric, {len(composite_alarms)} composite), has_more_results: {has_more_results}'
            )

            return ActiveAlarmsResponse(
                metric_alarms=metric_alarms,
                composite_alarms=composite_alarms,
                has_more_results=has_more_results,
                message=message,
            )

        except Exception as e:
            logger.error(f'Error in get_active_alarms: {str(e)}')
            await ctx.error(f'Error getting active alarms: {str(e)}')
            raise

    async def get_alarm_history(
        self,
        ctx: Context,
        alarm_name: str = Field(..., description='Name of the alarm to retrieve history for'),
        start_time: Annotated[
            str | None,
            Field(
                description="The start time for the history query in ISO format (e.g., '2023-01-01T00:00:00Z') or as a datetime object. Defaults to 24 hours ago."
            ),
        ] = None,
        end_time: Annotated[
            str | None,
            Field(
                description="The end time for the history query in ISO format (e.g., '2023-01-01T00:00:00Z') or as a datetime object. Defaults to current time."
            ),
        ] = None,
        history_item_type: Annotated[
            str | None,
            Field(
                description="Type of history items to retrieve. Possible values: 'ConfigurationUpdate', 'StateUpdate', 'Action'. Defaults to 'StateUpdate'."
            ),
        ] = None,
        max_items: Annotated[
            int | None,
            Field(
                description='Maximum number of history items to return (default: 50). Large values may cause context window overflow and impact LLM performance. Adjust time-range to limit responses.'
            ),
        ] = 50,
        include_component_alarms: Annotated[
            bool | None,
            Field(
                description='For composite alarms, whether to include details about component alarms. Defaults to false.'
            ),
        ] = False,
    ) -> Union[AlarmHistoryResponse, CompositeAlarmComponentResponse]:
        """Gets the history for a CloudWatch alarm with time range suggestions for investigation.

        This tool retrieves the history for a specified CloudWatch alarm, focusing primarily
        on state transitions to ALARM state. It also provides suggested time ranges for
        investigation based on the alarm's configuration and history.

        Usage: Use this tool to understand when an alarm fired and get useful time ranges
        for investigating the underlying issue using other CloudWatch tools. The tool is
        particularly useful for identifying patterns like alarm flapping (going in and out
        of alarm state frequently).

        Args:
            ctx: The MCP context object for error handling and logging.
            alarm_name: Name of the alarm to retrieve history for.
            start_time: Optional start time for the history query. Defaults to 24 hours ago.
            end_time: Optional end time for the history query. Defaults to current time.
            history_item_type: Optional type of history items to retrieve. Defaults to 'StateUpdate'.
            max_items: Maximum number of history items to return. Defaults to 50.
            include_component_alarms: For composite alarms, whether to include details about component alarms.

        Returns:
            Union[AlarmHistoryResponse, CompositeAlarmComponentResponse]: Either a response containing
            alarm history with time range suggestions, or component alarm details for composite alarms.

        Example:
            result = await get_alarm_history(
                ctx,
                alarm_name="my-cpu-alarm",
                start_time="2025-06-18T00:00:00Z",
                end_time="2025-06-19T00:00:00Z"
            )
            if isinstance(result, AlarmHistoryResponse):
                print(f"Found {len(result.history_items)} history items")
                for suggestion in result.time_range_suggestions:
                    print(f"Suggested investigation time range: {suggestion.start_time} to {suggestion.end_time}")
        """
        try:
            # Handle FieldInfo objects - set default values
            if max_items is None or not isinstance(max_items, int):
                max_items = 50
            if include_component_alarms is None or not isinstance(include_component_alarms, bool):
                include_component_alarms = False
            if history_item_type is None or not isinstance(history_item_type, str):
                history_item_type = 'StateUpdate'

            # Use default client
            cloudwatch_client = self.cloudwatch_client

            # Set up default time range (last 24 hours)
            if end_time is None or not isinstance(end_time, str):
                end_time = datetime.now()
            else:
                end_time = datetime.fromisoformat(end_time.replace('Z', '+00:00'))

            if start_time is None or not isinstance(start_time, str):
                start_time = end_time - timedelta(days=1)
            else:
                start_time = datetime.fromisoformat(start_time.replace('Z', '+00:00'))

            logger.info(f'Fetching alarm history for {alarm_name}')
            logger.info(f'Time range: {start_time} to {end_time}')

            paginator = cloudwatch_client.get_paginator('describe_alarm_history')
            page_iterator = paginator.paginate(
                AlarmName=alarm_name,
                StartDate=start_time,
                EndDate=end_time,
                HistoryItemType=history_item_type,
                PaginationConfig={'MaxItems': max_items + 1},
            )

            # Collect results
            history_items = []
            total_items_fetched = 0
            items_to_return = 0

            for page in page_iterator:
                items_list = page.get('AlarmHistoryItems', [])
                total_items_fetched += len(items_list)

                for item in items_list:
                    if items_to_return < max_items:
                        history_item = self._transform_history_item(item)
                        history_items.append(history_item)
                        items_to_return += 1
                    else:
                        break

            # Determine if more results are available
            has_more_results = total_items_fetched > max_items

            # Get detailed alarm information
            alarm_details = await self._get_alarm_details(cloudwatch_client, alarm_name)

            # Handle composite alarms if requested
            if include_component_alarms and alarm_details.alarm_type == 'CompositeAlarm':
                return await self._handle_composite_alarm(cloudwatch_client, alarm_details)

            # Generate time range suggestions based on alarm history and configuration
            time_range_suggestions = self._generate_time_range_suggestions(
                history_items, alarm_details
            )

            # Create basic response
            message = None
            if items_to_return == 0:
                message = f'No alarm history found for {alarm_name} in the specified time range'
            elif has_more_results:
                message = f'Showing {items_to_return} history items (more available)'

            logger.info(
                f'Found {items_to_return} alarm history items, has_more_results: {has_more_results}'
            )

            return AlarmHistoryResponse(
                alarm_details=alarm_details,
                history_items=history_items,
                time_range_suggestions=time_range_suggestions,
                has_more_results=has_more_results,
                message=message,
            )

        except Exception as e:
            logger.error(f'Error in get_alarm_history: {str(e)}')
            await ctx.error(f'Error getting alarm history: {str(e)}')
            raise

    def _transform_metric_alarm(self, alarm: Dict[str, Any]) -> MetricAlarmSummary:
        """Transform AWS SDK metric alarm to summary model."""
        # Extract key dimensions only
        dimensions = []
        for dim in alarm.get('Dimensions', []):
            dimensions.append({'Name': dim.get('Name', ''), 'Value': dim.get('Value', '')})

        return MetricAlarmSummary(
            alarm_name=alarm.get('AlarmName', ''),
            alarm_description=alarm.get('AlarmDescription'),
            state_value=alarm.get('StateValue', ''),
            state_reason=alarm.get('StateReason', ''),
            metric_name=alarm.get('MetricName', ''),
            namespace=alarm.get('Namespace', ''),
            dimensions=dimensions,
            threshold=float(alarm.get('Threshold', 0)),
            comparison_operator=alarm.get('ComparisonOperator', ''),
            state_updated_timestamp=alarm.get('StateUpdatedTimestamp', datetime.now()),
        )

    def _transform_composite_alarm(self, alarm: Dict[str, Any]) -> CompositeAlarmSummary:
        """Transform AWS SDK composite alarm to summary model."""
        return CompositeAlarmSummary(
            alarm_name=alarm.get('AlarmName', ''),
            alarm_description=alarm.get('AlarmDescription'),
            state_value=alarm.get('StateValue', ''),
            state_reason=alarm.get('StateReason', ''),
            alarm_rule=alarm.get('AlarmRule', ''),
            state_updated_timestamp=alarm.get('StateUpdatedTimestamp', datetime.now()),
        )

    async def _get_alarm_details(self, cloudwatch_client, alarm_name: str) -> AlarmDetails:
        """Retrieve detailed information about a CloudWatch alarm."""
        try:
            logger.info(f'Fetching alarm details for {alarm_name}')

            # Call DescribeAlarms API for the specific alarm
            response = cloudwatch_client.describe_alarms(
                AlarmNames=[alarm_name], AlarmTypes=['MetricAlarm', 'CompositeAlarm']
            )

            # Check if alarm exists
            metric_alarms = response.get('MetricAlarms', [])
            composite_alarms = response.get('CompositeAlarms', [])

            if not metric_alarms and not composite_alarms:
                logger.warning(f'Alarm {alarm_name} not found')
                return AlarmDetails(
                    alarm_name=alarm_name,
                    alarm_type='Unknown',
                    current_state='Unknown',
                    alarm_description='Alarm not found',
                )

            # Process metric alarm
            if metric_alarms:
                alarm = metric_alarms[0]

                # Extract dimensions
                dimensions = []
                for dim in alarm.get('Dimensions', []):
                    dimensions.append({dim.get('Name', ''): dim.get('Value', '')})

                return AlarmDetails(
                    alarm_name=alarm.get('AlarmName', ''),
                    alarm_description=alarm.get('AlarmDescription'),
                    alarm_type='MetricAlarm',
                    current_state=alarm.get('StateValue', ''),
                    metric_name=alarm.get('MetricName'),
                    namespace=alarm.get('Namespace'),
                    dimensions=dimensions,
                    threshold=alarm.get('Threshold'),
                    comparison_operator=alarm.get('ComparisonOperator'),
                    evaluation_periods=alarm.get('EvaluationPeriods'),
                    period=alarm.get('Period'),
                    statistic=alarm.get('Statistic'),
                )

            # Process composite alarm
            elif composite_alarms:
                alarm = composite_alarms[0]

                return AlarmDetails(
                    alarm_name=alarm.get('AlarmName', ''),
                    alarm_description=alarm.get('AlarmDescription'),
                    alarm_type='CompositeAlarm',
                    current_state=alarm.get('StateValue', ''),
                    alarm_rule=alarm.get('AlarmRule'),
                )

        except Exception as e:
            logger.error(f'Error fetching alarm details for {alarm_name}: {str(e)}')
            # Return basic details on error
            return AlarmDetails(
                alarm_name=alarm_name,
                alarm_type='Unknown',
                current_state='Unknown',
                alarm_description=f'Error retrieving alarm details: {str(e)}',
            )

    def _transform_history_item(self, item: Dict[str, Any]) -> AlarmHistoryItem:
        """Parse and transform a CloudWatch alarm history item."""
        try:
            # Extract basic information
            alarm_name = item.get('AlarmName', '')
            alarm_type = item.get('AlarmType', '')
            timestamp = item.get('Timestamp', datetime.now())
            history_item_type = item.get('HistoryItemType', '')
            history_summary = item.get('HistorySummary', '')
            history_data = item.get('HistoryData', '')

            # Initialize state information
            old_state = None
            new_state = None
            state_reason = None

            # Parse HistoryData JSON for StateUpdate items
            if history_item_type == 'StateUpdate' and history_data:
                try:
                    data = json.loads(history_data)

                    # Extract old state information
                    if 'oldState' in data:
                        old_state_info = data['oldState']
                        old_state = old_state_info.get('stateValue')

                    # Extract new state information
                    if 'newState' in data:
                        new_state_info = data['newState']
                        new_state = new_state_info.get('stateValue')
                        state_reason = new_state_info.get('stateReason')

                except json.JSONDecodeError as e:
                    logger.warning(f'Failed to parse HistoryData JSON for {alarm_name}: {str(e)}')
                    # Continue with basic information even if JSON parsing fails
                except Exception as e:
                    logger.warning(f'Error processing HistoryData for {alarm_name}: {str(e)}')

            return AlarmHistoryItem(
                alarm_name=alarm_name,
                alarm_type=alarm_type,
                timestamp=timestamp,
                history_item_type=history_item_type,
                history_summary=history_summary,
                old_state=old_state,
                new_state=new_state,
                state_reason=state_reason,
            )

        except Exception as e:
            logger.error(f'Error transforming history item: {str(e)}')
            # Return basic item on error
            return AlarmHistoryItem(
                alarm_name=item.get('AlarmName', ''),
                alarm_type=item.get('AlarmType', ''),
                timestamp=item.get('Timestamp', datetime.now()),
                history_item_type=item.get('HistoryItemType', ''),
                history_summary=item.get('HistorySummary', ''),
                old_state=None,
                new_state=None,
                state_reason=None,
            )

    def _generate_time_range_suggestions(
        self, history_items: List[AlarmHistoryItem], alarm_details: AlarmDetails
    ) -> List[TimeRangeSuggestion]:
        """Generate time range suggestions based on alarm history and configuration."""
        try:
            suggestions = []

            # Filter for state transitions to ALARM state
            alarm_transitions = []
            for item in history_items:
                if item.history_item_type == 'StateUpdate' and item.new_state == 'ALARM':
                    alarm_transitions.append(item)

            if not alarm_transitions:
                logger.info('No transitions to ALARM state found')
                return suggestions

            # Get alarm configuration for time window calculation
            period = alarm_details.period or 300  # Default to 5 minutes if not available
            evaluation_periods = alarm_details.evaluation_periods or 1

            # Calculate dynamic window based on alarm period (up to 5x the evaluation period)
            window_before_seconds = period * evaluation_periods * 5
            window_after_seconds = period * 2

            logger.info(
                f'Using dynamic window: {window_before_seconds}s before, {window_after_seconds}s after alarm transitions'
            )

            # Generate suggestions for each alarm transition
            for transition in alarm_transitions:
                start_time = transition.timestamp - timedelta(seconds=window_before_seconds)
                end_time = transition.timestamp + timedelta(seconds=window_after_seconds)

                reason = f'Investigation window for alarm transition to ALARM state at {transition.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")} (based on {evaluation_periods} evaluation periods of {period}s each)'

                suggestions.append(
                    TimeRangeSuggestion(start_time=start_time, end_time=end_time, reason=reason)
                )

            # Check for alarm flapping (multiple transitions in a short time)
            if len(alarm_transitions) > 1:
                # Sort transitions by timestamp
                sorted_transitions = sorted(alarm_transitions, key=lambda x: x.timestamp)

                # Look for clusters of transitions within a short time window
                flapping_clusters = []
                current_cluster = [sorted_transitions[0]]

                for i in range(1, len(sorted_transitions)):
                    time_diff = (
                        sorted_transitions[i].timestamp - current_cluster[-1].timestamp
                    ).total_seconds()

                    # If transitions are within 1 hour of each other, consider them part of the same cluster
                    if time_diff <= 3600:  # 1 hour
                        current_cluster.append(sorted_transitions[i])
                    else:
                        if len(current_cluster) > 1:
                            flapping_clusters.append(current_cluster)
                        current_cluster = [sorted_transitions[i]]

                # Don't forget the last cluster
                if len(current_cluster) > 1:
                    flapping_clusters.append(current_cluster)

                # Generate suggestions for flapping clusters
                for cluster in flapping_clusters:
                    cluster_start = cluster[0].timestamp - timedelta(seconds=window_before_seconds)
                    cluster_end = cluster[-1].timestamp + timedelta(seconds=window_after_seconds)

                    reason = f'Alarm flapping detected: {len(cluster)} transitions to ALARM state between {cluster[0].timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")} and {cluster[-1].timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")}'

                    suggestions.append(
                        TimeRangeSuggestion(
                            start_time=cluster_start, end_time=cluster_end, reason=reason
                        )
                    )

            logger.info(f'Generated {len(suggestions)} time range suggestions')
            return suggestions

        except Exception as e:
            logger.error(f'Error generating time range suggestions: {str(e)}')
            return []

    async def _handle_composite_alarm(
        self, cloudwatch_client, alarm_details: AlarmDetails
    ) -> CompositeAlarmComponentResponse:
        """Handle composite alarm component details retrieval."""
        try:
            logger.info(f'Handling composite alarm: {alarm_details.alarm_name}')

            # Parse the alarm rule to identify component alarms
            component_alarms = self._parse_alarm_rule(alarm_details.alarm_rule or '')

            # Get details about component alarms
            component_details = []
            if component_alarms:
                logger.info(f'Found {len(component_alarms)} component alarms')

                for component_name in component_alarms:
                    try:
                        component_detail = await self._get_alarm_details(
                            cloudwatch_client, component_name
                        )
                        component_details.append(component_detail)
                    except Exception as e:
                        logger.warning(
                            f'Failed to get details for component alarm {component_name}: {str(e)}'
                        )
                        # Add basic details for failed component
                        component_details.append(
                            AlarmDetails(
                                alarm_name=component_name,
                                alarm_type='Unknown',
                                current_state='Unknown',
                                alarm_description=f'Failed to retrieve details: {str(e)}',
                            )
                        )

            return CompositeAlarmComponentResponse(
                composite_alarm_name=alarm_details.alarm_name,
                component_alarms=component_alarms,
                alarm_rule=alarm_details.alarm_rule or '',
                component_details=component_details,
            )

        except Exception as e:
            logger.error(f'Error handling composite alarm {alarm_details.alarm_name}: {str(e)}')
            # Return basic response on error
            return CompositeAlarmComponentResponse(
                composite_alarm_name=alarm_details.alarm_name,
                component_alarms=[],
                alarm_rule=alarm_details.alarm_rule or '',
                component_details=None,
            )

    def _parse_alarm_rule(self, alarm_rule: str) -> List[str]:
        """Parse composite alarm rule to extract component alarm names."""
        try:
            if not alarm_rule:
                return []

            # Simple regex-based parsing to extract alarm names
            # Composite alarm rules typically contain alarm names in quotes or as identifiers
            import re

            # Pattern to match alarm names in various formats:
            # - Quoted names: "alarm-name"
            # - ALARM() function: ALARM("alarm-name")
            # - Direct references: alarm-name (without spaces)
            patterns = [
                r'ALARM\("([^"]+)"\)',  # ALARM("alarm-name")
                r'"([^"]+)"',  # "alarm-name"
                r'ALARM\(([^)]+)\)',  # ALARM(alarm-name) without quotes
            ]

            component_alarms = set()  # Use set to avoid duplicates

            for pattern in patterns:
                matches = re.findall(pattern, alarm_rule)
                for match in matches:
                    # Clean up the alarm name
                    alarm_name = match.strip().strip('"').strip("'")
                    if alarm_name:
                        component_alarms.add(alarm_name)

            result = list(component_alarms)
            logger.info(f'Parsed {len(result)} component alarms from rule: {result}')
            return result

        except Exception as e:
            logger.error(f'Error parsing alarm rule: {str(e)}')
            return []
