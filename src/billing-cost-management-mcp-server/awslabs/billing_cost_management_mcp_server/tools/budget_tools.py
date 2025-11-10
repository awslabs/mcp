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

"""AWS Budgets tools for the AWS Billing and Cost Management MCP server.

Updated to use shared utility functions and support multi-account access.
"""

from ..utilities.aws_service_base import format_response, handle_aws_error
from ..utilities.aws_credentials import credential_manager
from datetime import datetime
from fastmcp import Context, FastMCP
from typing import Any, Dict, List, Optional


budget_server = FastMCP(name='budget-tools', instructions='Tools for working with AWS Budgets API')


@budget_server.tool(
    name='budgets',
    description="""Retrieves AWS budget information using the AWS Budgets API.

This tool uses the DescribeBudgets API to retrieve all budgets for an account.

The API returns information about:
- Budget names, types, and time periods
- Budget limits (amount and unit)
- Current actual spend
- Forecasted spend
- Cost filters applied to budgets

With this information, you can determine which budgets have been exceeded or are projected to exceed their limits.

Multi-account support:
- Optionally specify account_id parameter to query budgets from a different AWS account
- If account_id is not provided, uses the current account where the MCP server is running
- Requires cross-account IAM role 'MCPServerCrossAccountRole' in target accounts

The tool automatically retrieves the AWS account ID of the calling identity or uses the provided account_id.""",
)
async def budgets(
    ctx: Context,
    budget_name: Optional[str] = None,
    max_results: int = 100,
    account_id: Optional[str] = None,
    region: str = 'us-east-1',
) -> Dict[str, Any]:
    """Retrieves AWS budget information using the AWS Budgets API.

    Args:
        ctx: The MCP context object
        budget_name: Optional budget name filter. If provided, only returns information for the specified budget.
        max_results: Maximum number of results to return. Defaults to 100.
        account_id: Target AWS account ID (optional, uses current account if not provided)
        region: AWS region (default: us-east-1)

    Returns:
        Dict containing the budget information with account tracking
    """
    # Track the account being queried
    target_account = account_id or credential_manager.current_account_id
    
    try:
        # Log the request
        await ctx.info(
            f'Retrieving budgets (budget_name={budget_name}, max_results={max_results})'
        )
        await ctx.info(f'Querying account: {target_account} in region: {region}')

        # Call describe_budgets
        return await describe_budgets(ctx, target_account, budget_name, max_results, region)

    except Exception as e:
        # Use shared error handler for consistent error reporting
        # Add account_id to error response
        error_response = await handle_aws_error(ctx, e, 'budgets', 'AWS Budgets')
        if isinstance(error_response, dict) and 'data' in error_response:
            error_response['data']['account_id'] = target_account
            error_response['data']['region'] = region
        return error_response


async def describe_budgets(
    ctx: Context,
    account_id: str,
    budget_name: Optional[str],
    max_results: int,
    region: str = 'us-east-1',
) -> Dict[str, Any]:
    """Retrieves budgets using the AWS Budgets API.

    Args:
        ctx: The MCP context object.
        account_id: The AWS account ID.
        budget_name: Optional budget name filter.
        max_results: Maximum number of results to return.
        region: AWS region (default: us-east-1)

    Returns:
        Dict containing the formatted budget information with account tracking.
    """
    try:
        # Get Budgets client with appropriate credentials
        # Note: Budgets API is only available in us-east-1
        budgets_client = credential_manager.get_client(
            service='budgets',
            account_id=account_id if account_id != credential_manager.current_account_id else None,
            region='us-east-1'  # Budgets API only available in us-east-1
        )

        # Prepare the request parameters
        request_params = {'AccountId': account_id, 'MaxResults': max_results}

        # Collect all budgets with internal pagination
        all_budgets = []
        next_token = None
        page_count = 0

        while True:
            page_count += 1
            if next_token:
                request_params['NextToken'] = next_token

            remaining = max_results - len(all_budgets)
            if remaining <= 0:
                break
            request_params['MaxResults'] = min(100, remaining)

            await ctx.info(f'Fetching budgets page {page_count}')
            response = budgets_client.describe_budgets(**request_params)

            page_budgets = response.get('Budgets', [])
            all_budgets.extend(page_budgets)

            await ctx.info(f'Retrieved {len(page_budgets)} budgets (total: {len(all_budgets)})')

            next_token = response.get('NextToken')
            if not next_token:
                break

        # Format the response for better readability
        formatted_budgets = format_budgets(all_budgets)

        # Handle budget name filtering client-side if provided
        if budget_name:
            filtered_budgets = [
                b for b in formatted_budgets if b.get('budget_name') == budget_name
            ]
            await ctx.info(f"Filtered to {len(filtered_budgets)} budgets matching '{budget_name}'")
            formatted_budgets = filtered_budgets

        # Return success response using shared format_response utility
        return format_response(
            'success',
            {
                'account_id': account_id,
                'region': region,
                'budgets': formatted_budgets,
                'total_count': len(formatted_budgets),
            },
        )

    except Exception as e:
        # Use shared error handler for consistent error reporting
        error_response = await handle_aws_error(ctx, e, 'describe_budgets', 'AWS Budgets')
        if isinstance(error_response, dict) and 'data' in error_response:
            error_response['data']['account_id'] = account_id
            error_response['data']['region'] = region
        return error_response


def format_budgets(budgets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Formats the budget objects from the AWS API response.

    Args:
        budgets: List of budget objects from the AWS API.

    Returns:
        List of formatted budget objects.
    """
    formatted_budgets = []

    for budget in budgets:
        formatted_budget = {
            'budget_name': budget.get('BudgetName'),
            'budget_type': budget.get('BudgetType'),
            'time_unit': budget.get('TimeUnit'),
        }

        # Add limit if present
        if 'BudgetLimit' in budget:
            formatted_budget['budget_limit'] = {
                'amount': budget['BudgetLimit'].get('Amount'),
                'unit': budget['BudgetLimit'].get('Unit'),
                'formatted': f'{budget["BudgetLimit"].get("Amount")} {budget["BudgetLimit"].get("Unit")}',
            }

        # Add calculated spend if present
        if 'CalculatedSpend' in budget:
            calculated_spend = budget['CalculatedSpend']
            calculated_spend_dict: Dict[str, Any] = {}

            if 'ActualSpend' in calculated_spend:
                actual = calculated_spend['ActualSpend']
                calculated_spend_dict['actual_spend'] = {
                    'amount': actual.get('Amount'),
                    'unit': actual.get('Unit'),
                    'formatted': f'{actual.get("Amount")} {actual.get("Unit")}',
                }

            if 'ForecastedSpend' in calculated_spend:
                forecast = calculated_spend['ForecastedSpend']
                calculated_spend_dict['forecasted_spend'] = {
                    'amount': forecast.get('Amount'),
                    'unit': forecast.get('Unit'),
                    'formatted': f'{forecast.get("Amount")} {forecast.get("Unit")}',
                }

            formatted_budget['calculated_spend'] = calculated_spend_dict

        # Add cost filters if present
        if 'CostFilters' in budget and budget['CostFilters']:
            formatted_budget['cost_filters'] = budget['CostFilters']

        # Add time period if present
        if 'TimePeriod' in budget:
            time_period = budget['TimePeriod']
            time_period_dict: Dict[str, Any] = {}

            if 'Start' in time_period:
                time_period_dict['start'] = (
                    time_period['Start'].strftime('%Y-%m-%d')
                    if isinstance(time_period['Start'], datetime)
                    else time_period['Start']
                )

            if 'End' in time_period:
                time_period_dict['end'] = (
                    time_period['End'].strftime('%Y-%m-%d')
                    if isinstance(time_period['End'], datetime)
                    else time_period['End']
                )

            formatted_budget['time_period'] = time_period_dict

        # Add budget status (derived field)
        calculated_spend = formatted_budget.get('calculated_spend')
        budget_limit = formatted_budget.get('budget_limit')

        if (
            calculated_spend is not None
            and isinstance(calculated_spend, dict)
            and 'actual_spend' in calculated_spend
            and budget_limit is not None
            and isinstance(budget_limit, dict)
        ):
            actual_spend = calculated_spend.get('actual_spend')
            if actual_spend and isinstance(actual_spend, dict) and 'amount' in actual_spend:
                actual_amount = float(actual_spend['amount'])
                limit_amount = float(budget_limit['amount'])

                if actual_amount >= limit_amount:
                    formatted_budget['status'] = 'EXCEEDED'
                elif 'forecasted_spend' in calculated_spend:
                    forecasted_spend = calculated_spend.get('forecasted_spend')
                    if (
                        forecasted_spend
                        and isinstance(forecasted_spend, dict)
                        and 'amount' in forecasted_spend
                    ):
                        forecast_amount = float(forecasted_spend['amount'])
                        if forecast_amount >= limit_amount:
                            formatted_budget['status'] = 'FORECASTED_TO_EXCEED'
                        else:
                            formatted_budget['status'] = 'OK'
                    else:
                        formatted_budget['status'] = 'OK'
                else:
                    formatted_budget['status'] = 'OK'
            else:
                formatted_budget['status'] = 'OK'

        formatted_budgets.append(formatted_budget)

    return formatted_budgets