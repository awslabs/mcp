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

from ..utilities.aws_service_base import create_aws_client, format_response, handle_aws_error
from fastmcp import Context, FastMCP
from typing import Any, Dict, Optional


cost_anomaly_server = FastMCP(
    name='cost-anomaly-tools', instructions='Tools for working with AWS Cost Anomaly Detection API'
)


@cost_anomaly_server.tool(
    name='cost_anomaly',
    description="""Retrieves AWS cost anomalies using the Cost Explorer GetAnomalies API.

This tool allows you to retrieve cost anomalies detected on your AWS account during a specified time period.
Anomalies are available for up to 90 days.

You can filter anomalies by:
- Date range (required)
- Monitor ARN (optional)
- Feedback status (optional)
- Total impact (optional)

Feedback status options:
- YES: Anomalies marked as accurate
- NO: Anomalies marked as inaccurate
- PLANNED_ACTIVITY: Anomalies marked as planned activities""",
)
async def cost_anomaly(
    ctx: Context,
    start_date: str,
    end_date: str,
    monitor_arn: Optional[str] = None,
    feedback: Optional[str] = None,
    max_results: Optional[int] = None,
    total_impact_operator: Optional[str] = None,
    total_impact_start: Optional[float] = None,
    total_impact_end: Optional[float] = None,
) -> Dict[str, Any]:
    """Retrieves AWS cost anomalies using the Cost Explorer GetAnomalies API.

    Args:
        ctx: The MCP context object
        start_date: Start date in YYYY-MM-DD format. Required.
        end_date: End date in YYYY-MM-DD format. Required.
        monitor_arn: Optional ARN of a specific cost anomaly monitor to filter results.
        feedback: Optional filter for anomalies by feedback status (YES, NO, PLANNED_ACTIVITY).
        max_results: Optional maximum number of results to return.
        total_impact_operator: Optional numeric operator for filtering by total impact (EQUAL, GREATER_THAN, LESS_THAN, GREATER_THAN_OR_EQUAL, LESS_THAN_OR_EQUAL, BETWEEN).
        total_impact_start: Optional start value for total impact filter.
        total_impact_end: Optional end value for total impact filter (required when using BETWEEN operator).

    Returns:
        Dict containing the cost anomaly information
    """
    try:
        await ctx.info(f'Retrieving cost anomalies from {start_date} to {end_date}')

        # Initialize Cost Explorer client using shared utility
        ce_client = create_aws_client('ce', region_name='us-east-1')

        return await get_anomalies(
            ctx,
            ce_client,
            start_date,
            end_date,
            monitor_arn,
            feedback,
            max_results,
            total_impact_operator,
            total_impact_start,
            total_impact_end,
        )

    except Exception as e:
        # Use shared error handler for consistent error reporting
        return await handle_aws_error(ctx, e, 'cost_anomaly', 'Cost Explorer')


async def get_anomalies(
    ctx: Context,
    ce_client: Any,
    start_date: str,
    end_date: str,
    monitor_arn: Optional[str],
    feedback: Optional[str],
    max_results: Optional[int],
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
        max_results: Maximum results to return
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

        if max_results:
            request_params['MaxResults'] = int(max_results)

        # Add total impact filter if provided
        if total_impact_operator:
            total_impact: dict = {'NumericOperator': total_impact_operator}

            if total_impact_start is not None:
                total_impact['StartValue'] = float(total_impact_start)

            if total_impact_end is not None:
                total_impact['EndValue'] = float(total_impact_end)

            request_params['TotalImpact'] = total_impact

        # Collect all anomalies with internal pagination
        all_anomalies = []
        next_page_token = None
        page_count = 0

        while True:
            page_count += 1

            if next_page_token:
                request_params['NextPageToken'] = next_page_token

            await ctx.info(f'Fetching cost anomalies page {page_count}')
            response = ce_client.get_anomalies(**request_params)

            page_anomalies = response.get('Anomalies', [])
            all_anomalies.extend(page_anomalies)

            await ctx.info(
                f'Retrieved {len(page_anomalies)} anomalies (total: {len(all_anomalies)})'
            )

            next_page_token = response.get('NextPageToken')
            if not next_page_token:
                break

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

        return format_response('success', formatted_response)

    except Exception as e:
        # Use shared error handler for consistent error reporting
        return await handle_aws_error(ctx, e, 'get_anomalies', 'Cost Explorer')
