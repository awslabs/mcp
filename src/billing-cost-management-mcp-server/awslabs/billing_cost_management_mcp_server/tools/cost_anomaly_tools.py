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

"""AWS Cost Anomaly Detection tools for the AWS Billing and Cost Management MCP server.

Updated to use shared utility functions.
"""

from ..utilities.aws_service_base import (
    PageSpec,
    create_aws_client,
    format_response,
    handle_aws_error,
    paginate_aws_items,
    validate_date_format,
    with_pagination,
)
from ..utilities.logging_utils import get_context_logger
from datetime import datetime, timedelta
from fastmcp import Context, FastMCP
from typing import Any, Dict, Optional


cost_anomaly_server = FastMCP(
    name='cost-anomaly-tools', instructions='Tools for working with AWS Cost Anomaly Detection API'
)

# Pages can come back short and still carry a token, so paging continues until no token.
GET_ANOMALIES = PageSpec(
    result_key='Anomalies',
    token_param='NextPageToken',
    token_key_in_response='NextPageToken',
    page_max=10000,
    page_size_param='MaxResults',
)


@cost_anomaly_server.tool(
    name='cost-anomaly',
    description="""Retrieves AWS cost anomalies using the Cost Explorer GetAnomalies API.

This tool allows you to retrieve cost anomalies detected on your AWS account during a specified time period.
Anomalies are available for up to 90 days.

Date range matching: an anomaly is returned when its end_date (the last day it was detected) falls
within start_date..end_date. Its start_date can be earlier than the requested start_date: an
anomaly that began before the range and was still being detected inside it is in range. When asked
for anomalies in a period (for example "the past 7 days"), report every returned anomaly, and do
not drop results whose start_date is before the range.

You can filter anomalies by:
- Date range (required)
- Monitor ARN (optional)
- Feedback status (optional)
- Total impact (optional)

Note: Both start_date and end_date are INCLUSIVE. To get anomalies including today, use today's date as end_date.

Feedback status options:
- YES: Anomalies marked as accurate
- NO: Anomalies marked as inaccurate
- PLANNED_ACTIVITY: Anomalies marked as planned activities

Pagination:
- max_items: total number of anomalies returned. Omit it to fetch every page (no limit).
  Pass it, or narrow the filters (monitor_arn, total impact, a shorter date range), for
  accounts with many anomalies.
- Anomalies come back newest first (by anomaly end date), so max_items=N returns the N most
  recent.
- If the result has complete_dataset: false, it is partial: call again with a larger
  max_items, continue with next_token, or say the result is partial.""",
)
async def cost_anomaly(
    ctx: Context,
    start_date: str,
    end_date: str,
    monitor_arn: Optional[str] = None,
    feedback: Optional[str] = None,
    max_items: Optional[int] = None,
    next_token: Optional[str] = None,
    total_impact_operator: Optional[str] = None,
    total_impact_start: Optional[float] = None,
    total_impact_end: Optional[float] = None,
) -> Dict[str, Any]:
    """Retrieves AWS cost anomalies using the Cost Explorer GetAnomalies API.

    Args:
        ctx: The MCP context object
        start_date: Start date in YYYY-MM-DD format (inclusive). Required.
        end_date: End date in YYYY-MM-DD format (inclusive — use today's date to include today's anomalies). Required.
        monitor_arn: Optional ARN of a specific cost anomaly monitor to filter results.
        feedback: Optional filter for anomalies by feedback status (YES, NO, PLANNED_ACTIVITY).
        max_items: Optional total number of anomalies to return. None fetches every page.
        next_token: Optional pagination token from a previous response.
        total_impact_operator: Optional numeric operator for filtering by total impact (EQUAL, GREATER_THAN, LESS_THAN, GREATER_THAN_OR_EQUAL, LESS_THAN_OR_EQUAL, BETWEEN).
        total_impact_start: Optional start value for total impact filter.
        total_impact_end: Optional end value for total impact filter (required when using BETWEEN operator).

    Returns:
        Dict containing the cost anomaly information
    """
    # Get context logger for consistent logging
    ctx_logger = get_context_logger(ctx, __name__)

    try:
        # Validate date formats first
        if not validate_date_format(start_date):
            return format_response(
                'error',
                {'invalid_parameter': 'start_date'},
                f'Invalid start_date format: {start_date}. Date must be in YYYY-MM-DD format.',
                error_type='validation_error',
                operation='cost_anomaly',
                service='Cost Explorer',
            )

        if not validate_date_format(end_date):
            return format_response(
                'error',
                {'invalid_parameter': 'end_date'},
                f'Invalid end_date format: {end_date}. Date must be in YYYY-MM-DD format.',
                error_type='validation_error',
                operation='cost_anomaly',
                service='Cost Explorer',
            )

        # Parse dates for validation
        start_date_obj = datetime.strptime(start_date, '%Y-%m-%d')
        end_date_obj = datetime.strptime(end_date, '%Y-%m-%d')

        # Cost Anomaly Detection has a 90-day lookback limitation
        today = datetime.now()
        max_lookback = today - timedelta(days=90)

        # Check if date range is valid
        if start_date_obj > end_date_obj:
            return format_response(
                'error',
                {'start_date': start_date, 'end_date': end_date},
                'Invalid date range: start_date must be before or equal to end_date.',
                error_type='validation_error',
                operation='cost_anomaly',
                service='Cost Explorer',
            )

        # Check if dates are in the future
        if end_date_obj > today:
            return format_response(
                'error',
                {'end_date': end_date},
                'Invalid end_date: Cannot request anomalies for future dates.',
                error_type='validation_error',
                operation='cost_anomaly',
                service='Cost Explorer',
            )

        # Check if dates are beyond the 90-day lookback period
        if start_date_obj < max_lookback:
            await ctx_logger.warning(
                f'Requested start_date {start_date} is more than 90 days in the past. '
                f'Cost Anomaly Detection has a 90-day data retention period. '
                f'Some data may not be available.'
            )

        # For 2024 data specifically (reported issue)
        current_year = today.year
        if start_date_obj.year == current_year or end_date_obj.year == current_year:
            # Check if we're in early January and querying current year data
            if today.month == 1 and today.day < 15:
                await ctx_logger.warning(
                    f'Querying data for {current_year} in early January may return incomplete results '
                    f'as Cost Anomaly Detection may still be processing recent data.'
                )

        # Validate feedback parameter if provided
        if feedback and feedback not in ['YES', 'NO', 'PLANNED_ACTIVITY']:
            return format_response(
                'error',
                {'invalid_parameter': 'feedback', 'value': feedback},
                f'Invalid feedback value: {feedback}. Must be one of: YES, NO, PLANNED_ACTIVITY.',
                error_type='validation_error',
                operation='cost_anomaly',
                service='Cost Explorer',
            )

        # Validate total impact operator if provided
        valid_operators = [
            'EQUAL',
            'GREATER_THAN',
            'LESS_THAN',
            'GREATER_THAN_OR_EQUAL',
            'LESS_THAN_OR_EQUAL',
            'BETWEEN',
        ]
        if total_impact_operator and total_impact_operator not in valid_operators:
            return format_response(
                'error',
                {'invalid_parameter': 'total_impact_operator', 'value': total_impact_operator},
                f'Invalid total_impact_operator: {total_impact_operator}. Must be one of: {", ".join(valid_operators)}',
                error_type='validation_error',
                operation='cost_anomaly',
                service='Cost Explorer',
            )

        # Validate total_impact_end is provided when using BETWEEN operator
        if total_impact_operator == 'BETWEEN' and total_impact_end is None:
            return format_response(
                'error',
                {'missing_parameter': 'total_impact_end'},
                'When using BETWEEN operator for total_impact, both total_impact_start and total_impact_end must be provided.',
                error_type='validation_error',
                operation='cost_anomaly',
                service='Cost Explorer',
            )

        await ctx_logger.info(f'Retrieving cost anomalies from {start_date} to {end_date}')

        # Initialize Cost Explorer client using shared utility
        ce_client = create_aws_client('ce', region_name='us-east-1')

        return await get_anomalies(
            ctx,
            ce_client,
            start_date,
            end_date,
            monitor_arn,
            feedback,
            max_items,
            next_token,
            total_impact_operator,
            total_impact_start,
            total_impact_end,
        )

    except ValueError as e:
        # Handle date parsing errors
        return format_response(
            'error',
            {'error_type': 'validation_error'},
            f'Date validation error: {str(e)}',
            error_type='validation_error',
            operation='cost_anomaly',
            service='Cost Explorer',
        )
    except Exception as e:
        # Use shared error handler for other exceptions
        return await handle_aws_error(ctx, e, 'cost_anomaly', 'Cost Explorer')


async def get_anomalies(
    ctx: Context,
    ce_client: Any,
    start_date: str,
    end_date: str,
    monitor_arn: Optional[str],
    feedback: Optional[str],
    max_items: Optional[int],
    next_token: Optional[str],
    total_impact_operator: Optional[str],
    total_impact_start: Optional[float],
    total_impact_end: Optional[float],
) -> Dict[str, Any]:
    """Retrieves cost anomalies using the AWS Cost Explorer GetAnomalies API.

    Args:
        ctx: The MCP context
        ce_client: Cost Explorer client
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        monitor_arn: Optional ARN of a specific monitor
        feedback: Optional filter for anomaly feedback
        max_items: Total anomalies to return. None fetches every page.
        next_token: Pagination token from a previous response
        total_impact_operator: Optional numeric operator for filtering
        total_impact_start: Optional start value for total impact filter
        total_impact_end: Optional end value for total impact filter

    Returns:
        Dict containing anomaly data
    """
    try:
        # Prepare the request parameters
        request_params: dict = {'DateInterval': {'StartDate': start_date, 'EndDate': end_date}}

        # Add optional parameters if provided
        if monitor_arn:
            request_params['MonitorArn'] = str(monitor_arn)

        if feedback:
            request_params['Feedback'] = str(feedback)

        # Add total impact filter if provided
        if total_impact_operator:
            total_impact: dict = {'NumericOperator': total_impact_operator}

            if total_impact_start is not None:
                total_impact['StartValue'] = float(total_impact_start)

            if total_impact_end is not None:
                total_impact['EndValue'] = float(total_impact_end)

            request_params['TotalImpact'] = total_impact

        all_anomalies, _, pagination = await paginate_aws_items(
            ctx,
            'GetAnomalies',
            ce_client.get_anomalies,
            request_params,
            GET_ANOMALIES,
            max_items=max_items,
            next_token=next_token,
        )

        # Format the response for better readability
        formatted_response: Dict[str, Any] = {'anomalies': []}

        for anomaly in all_anomalies:
            formatted_anomaly = {
                'id': anomaly.get('AnomalyId'),
                'start_date': anomaly.get('AnomalyStartDate'),
                'end_date': anomaly.get('AnomalyEndDate'),
                'dimension_value': anomaly.get('DimensionValue'),
                'monitor_arn': anomaly.get('MonitorArn'),
                'feedback': anomaly.get('Feedback'),
            }

            # Add anomaly score if present
            if 'AnomalyScore' in anomaly:
                formatted_anomaly['score'] = {
                    'current': anomaly['AnomalyScore'].get('CurrentScore'),
                    'max': anomaly['AnomalyScore'].get('MaxScore'),
                }

            # Add impact if present
            if 'Impact' in anomaly:
                formatted_anomaly['impact'] = {
                    'total_impact': anomaly['Impact'].get('TotalImpact'),
                    'total_impact_percentage': anomaly['Impact'].get('TotalImpactPercentage'),
                    'max_impact': anomaly['Impact'].get('MaxImpact'),
                    'total_actual_spend': anomaly['Impact'].get('TotalActualSpend'),
                    'total_expected_spend': anomaly['Impact'].get('TotalExpectedSpend'),
                }

            # Add root causes if present
            if 'RootCauses' in anomaly and anomaly['RootCauses']:
                formatted_anomaly['root_causes'] = []
                for cause in anomaly['RootCauses']:
                    formatted_cause = {
                        'service': cause.get('Service'),
                        'region': cause.get('Region'),
                        'linked_account': cause.get('LinkedAccount'),
                        'linked_account_name': cause.get('LinkedAccountName'),
                        'usage_type': cause.get('UsageType'),
                    }

                    # Add contribution if present
                    if 'Impact' in cause and 'Contribution' in cause['Impact']:
                        formatted_cause['contribution'] = cause['Impact']['Contribution']

                    formatted_anomaly['root_causes'].append(formatted_cause)

            formatted_response['anomalies'].append(formatted_anomaly)

        return format_response('success', with_pagination(formatted_response, pagination))

    except Exception as e:
        # Use shared error handler for consistent error reporting
        return await handle_aws_error(ctx, e, 'get_anomalies', 'Cost Explorer')


# Monitors and subscriptions page with NextPageToken. The service rejects only a MaxResults
# below 1; 100 per page keeps each page small.
GET_ANOMALY_MONITORS = PageSpec(
    result_key='AnomalyMonitors',
    token_param='NextPageToken',
    token_key_in_response='NextPageToken',
    page_max=100,
    page_size_param='MaxResults',
)
GET_ANOMALY_SUBSCRIPTIONS = PageSpec(
    result_key='AnomalySubscriptions',
    token_param='NextPageToken',
    token_key_in_response='NextPageToken',
    page_max=100,
    page_size_param='MaxResults',
)

MONITOR_OPERATIONS = ('list_monitors', 'list_subscriptions')


@cost_anomaly_server.tool(
    name='cost-anomaly-monitors',
    description="""Lists the Cost Anomaly Detection monitors and alert subscriptions defined in the account,
using the Cost Explorer GetAnomalyMonitors and GetAnomalySubscriptions APIs. Use it to see what
the monitor behind an anomaly tracks and who is alerted; use cost-anomaly for the anomalies.
This tool is read-only.

operation (required): list_monitors or list_subscriptions; any other value is a validation_error.
1. list_monitors: returns data.monitors.
   - monitor_type DIMENSIONAL tracks each value of monitor_dimension (SERVICE, LINKED_ACCOUNT,
     TAG or COST_CATEGORY) separately, and dimensional_value_count is how many values it tracks.
     An anomaly's dimension_value from such a monitor is one of those values: a service name for
     SERVICE, an account ID for LINKED_ACCOUNT. For TAG and COST_CATEGORY, monitor_specification
     names the tag or cost category key.
   - monitor_type CUSTOM tracks the costs that monitor_specification (a Cost Explorer filter
     expression) selects; monitor_dimension is null.
2. list_subscriptions: returns data.subscriptions.
   - A subscription alerts its subscribers about anomalies from the monitors in
     monitor_arn_list whose impact meets threshold_expression. Its dimensions are
     ANOMALY_TOTAL_IMPACT_ABSOLUTE (USD) and ANOMALY_TOTAL_IMPACT_PERCENTAGE (percent); And
     requires every condition, Or any. threshold is a deprecated absolute-USD field and can be
     null: read threshold_expression.
   - frequency DAILY or WEEKLY sends an email digest; IMMEDIATE sends to an SNS topic.
     subscribers holds email addresses or SNS topic ARNs; status DECLINED means the subscriber has
     declined (unsubscribed from) the alerts.
   - Subscriptions decide who is alerted, not what is detected: cost-anomaly also returns
     anomalies below every threshold.
   - An empty monitor_arn_list means the subscription is attached to no monitor, so it sends
     no alerts.

monitor_arn (optional): list_monitors returns only that monitor; list_subscriptions returns
only the subscriptions attached to it. On either operation, a monitor ARN in this account that
matches no monitor returns an empty list, not an error; a malformed ARN is a ValidationException
and another account's ARN is an AccessDeniedException.

Pagination:
- max_items: total monitors or subscriptions returned. Omit it to fetch every page.
- If the result has complete_dataset: false, it is partial: call again with a larger
  max_items, continue with next_token, or say the result is partial.""",
)
async def cost_anomaly_monitors(
    ctx: Context,
    operation: str,
    monitor_arn: Optional[str] = None,
    max_items: Optional[int] = None,
    next_token: Optional[str] = None,
) -> Dict[str, Any]:
    """Lists Cost Anomaly Detection monitors or alert subscriptions.

    Args:
        ctx: The MCP context object
        operation: Required. 'list_monitors' or 'list_subscriptions'.
        monitor_arn: Optional monitor ARN. list_monitors returns only that monitor;
            list_subscriptions returns only the subscriptions attached to it.
        max_items: Optional total number of items to return. None fetches every page.
        next_token: Optional pagination token from a previous response.

    Returns:
        Dict containing the monitors or subscriptions and a pagination block
    """
    if operation not in MONITOR_OPERATIONS:
        return format_response(
            'error',
            {'invalid_parameter': 'operation', 'value': operation},
            f'Unsupported operation: {operation}. Use one of: {", ".join(MONITOR_OPERATIONS)}.',
            error_type='validation_error',
            operation='cost_anomaly_monitors',
            service='Cost Explorer',
        )

    if monitor_arn is not None:
        monitor_arn = monitor_arn.strip()
    if monitor_arn == '':
        return format_response(
            'error',
            {'invalid_parameter': 'monitor_arn'},
            'monitor_arn is empty. Pass a monitor ARN, or omit monitor_arn to list them all.',
            error_type='validation_error',
            operation='cost_anomaly_monitors',
            service='Cost Explorer',
        )

    try:
        ce_client = create_aws_client('ce', region_name='us-east-1')
        if operation == 'list_monitors':
            return await list_anomaly_monitors(ctx, ce_client, monitor_arn, max_items, next_token)
        return await list_anomaly_subscriptions(ctx, ce_client, monitor_arn, max_items, next_token)
    except Exception as e:
        return await handle_aws_error(ctx, e, 'cost_anomaly_monitors', 'Cost Explorer')


async def list_anomaly_monitors(
    ctx: Context,
    ce_client: Any,
    monitor_arn: Optional[str],
    max_items: Optional[int],
    next_token: Optional[str],
) -> Dict[str, Any]:
    """Lists anomaly monitors using the Cost Explorer GetAnomalyMonitors API.

    Args:
        ctx: The MCP context
        ce_client: Cost Explorer client
        monitor_arn: Optional ARN of the one monitor to return
        max_items: Total monitors to return. None fetches every page.
        next_token: Pagination token from a previous response

    Returns:
        Dict containing monitor data
    """
    try:
        request_params: Dict[str, Any] = {}
        if monitor_arn:
            request_params['MonitorArnList'] = [monitor_arn]

        monitors, _, pagination = await paginate_aws_items(
            ctx,
            'GetAnomalyMonitors',
            ce_client.get_anomaly_monitors,
            request_params,
            GET_ANOMALY_MONITORS,
            max_items=max_items,
            next_token=next_token,
        )

        formatted = [
            {
                'monitor_arn': monitor.get('MonitorArn'),
                'monitor_name': monitor.get('MonitorName'),
                'monitor_type': monitor.get('MonitorType'),
                'monitor_dimension': monitor.get('MonitorDimension'),
                'monitor_specification': monitor.get('MonitorSpecification'),
                'dimensional_value_count': monitor.get('DimensionalValueCount'),
                'creation_date': monitor.get('CreationDate'),
                'last_updated_date': monitor.get('LastUpdatedDate'),
                'last_evaluated_date': monitor.get('LastEvaluatedDate'),
            }
            for monitor in monitors
        ]
        return format_response('success', with_pagination({'monitors': formatted}, pagination))

    except Exception as e:
        return await handle_aws_error(ctx, e, 'get_anomaly_monitors', 'Cost Explorer')


async def list_anomaly_subscriptions(
    ctx: Context,
    ce_client: Any,
    monitor_arn: Optional[str],
    max_items: Optional[int],
    next_token: Optional[str],
) -> Dict[str, Any]:
    """Lists anomaly alert subscriptions using the Cost Explorer GetAnomalySubscriptions API.

    Args:
        ctx: The MCP context
        ce_client: Cost Explorer client
        monitor_arn: Optional monitor ARN; only subscriptions attached to it are returned
        max_items: Total subscriptions to return. None fetches every page.
        next_token: Pagination token from a previous response

    Returns:
        Dict containing subscription data
    """
    try:
        request_params: Dict[str, Any] = {}
        if monitor_arn:
            request_params['MonitorArn'] = monitor_arn

        subscriptions, _, pagination = await paginate_aws_items(
            ctx,
            'GetAnomalySubscriptions',
            ce_client.get_anomaly_subscriptions,
            request_params,
            GET_ANOMALY_SUBSCRIPTIONS,
            max_items=max_items,
            next_token=next_token,
        )

        formatted = [
            {
                'subscription_arn': subscription.get('SubscriptionArn'),
                'subscription_name': subscription.get('SubscriptionName'),
                'account_id': subscription.get('AccountId'),
                'monitor_arn_list': subscription.get('MonitorArnList', []),
                'frequency': subscription.get('Frequency'),
                'threshold_expression': subscription.get('ThresholdExpression'),
                'threshold': subscription.get('Threshold'),
                'subscribers': [
                    {
                        'address': subscriber.get('Address'),
                        'type': subscriber.get('Type'),
                        'status': subscriber.get('Status'),
                    }
                    for subscriber in subscription.get('Subscribers', [])
                ],
            }
            for subscription in subscriptions
        ]
        return format_response(
            'success', with_pagination({'subscriptions': formatted}, pagination)
        )

    except Exception as e:
        return await handle_aws_error(ctx, e, 'get_anomaly_subscriptions', 'Cost Explorer')
