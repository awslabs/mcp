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

File layout:
- Tool entrypoints: the @budget_server.tool functions the MCP client sees
  (`budgets`, `budget-actions`, `budget-notifications`).
- Account helper: `get_aws_account_id`.
- Operation handlers: the read calls each tool delegates to.
- Formatters: pure reshapers from raw AWS API dicts to the response shape.
"""

from ..utilities.aws_service_base import create_aws_client, format_response, handle_aws_error
from datetime import datetime
from fastmcp import Context, FastMCP
from typing import Any, Dict, List, Optional


budget_server = FastMCP(name='budget-tools', instructions='Tools for working with AWS Budgets API')


# =============================================================================
# Tool entrypoints
# =============================================================================


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

The tool automatically retrieves the AWS account ID of the calling identity or uses the provided account_id.""",
)
async def budgets(
    ctx: Context,
    budget_name: Optional[str] = None,
    max_results: int = 100,
    account_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Retrieves AWS budget information using the AWS Budgets API.

    Args:
        ctx: The MCP context object
        budget_name: Optional budget name filter. If provided, only returns information for the specified budget.
        max_results: Maximum number of results to return. Defaults to 100.
        account_id: Optional AWS account ID. If not provided, it will be retrieved automatically.

    Returns:
        Dict containing the budget information
    """
    try:
        # Log the request
        await ctx.info(
            f'Retrieving budgets (budget_name={budget_name}, max_results={max_results})'
        )

        # Get the AWS account ID dynamically or use provided one
        if not account_id:
            account_id = await get_aws_account_id(ctx)
        await ctx.info(f'Using AWS Account ID: {account_id}')

        # Call describe_budgets
        return await describe_budgets(ctx, account_id, budget_name, max_results)

    except Exception as e:
        # Use shared error handler for consistent error reporting
        return await handle_aws_error(ctx, e, 'budgets', 'AWS Budgets')


@budget_server.tool(
    name='budget-actions',
    description="""Reads the enforcement action(s) attached to AWS Budgets.

A budget action is what AWS Budgets automatically does when a threshold is crossed — apply an
IAM or SCP policy, or run an SSM document. Read-only; uses the account-scoped
DescribeBudgetActionsForAccount API.

- Omit `budget_name` to list every budget's actions in one call — the efficient way to audit
  which budgets have no enforcement configured.
- Pass `budget_name` to filter that same result to a single budget (there is no per-budget
  fan-out; filtering is client-side).

An empty `actions` list is a real answer (a budget with no actions), distinct from an error
such as AccessDenied. For a budget's spend-vs-limit status use the `budgets` tool; for its alert
thresholds use `budget-notifications`. The account ID is retrieved automatically or you may pass
`account_id`.""",
)
async def budget_actions(
    ctx: Context,
    budget_name: Optional[str] = None,
    max_results: int = 100,
    account_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Reads AWS Budgets enforcement actions (DescribeBudgetActionsForAccount).

    Args:
        ctx: The MCP context object.
        budget_name: Optional. If provided, the account-wide result is filtered to this budget.
        max_results: Maximum number of results to return. Defaults to 100.
        account_id: Optional AWS account ID; retrieved automatically if not provided.

    Returns:
        Dict containing the formatted action configuration.
    """
    try:
        await ctx.info(f'budget-actions (budget_name={budget_name}, max_results={max_results})')

        if not account_id:
            account_id = await get_aws_account_id(ctx)
        await ctx.info(f'Using AWS Account ID: {account_id}')

        return await describe_budget_actions(ctx, account_id, budget_name, max_results)

    except Exception as e:
        return await handle_aws_error(ctx, e, 'budget-actions', 'AWS Budgets')


@budget_server.tool(
    name='budget-notifications',
    description="""Reads the alert thresholds (notifications) configured on an AWS Budget.

A notification is an alert that fires when a budget crosses a threshold (e.g. 80% of the limit).
Read-only; uses the DescribeNotificationsForBudget API, which is per-budget — `budget_name` is
required (the AWS Budgets API has no account-scoped notifications read).

For a budget's spend-vs-limit status use the `budgets` tool; for its enforcement actions use
`budget-actions`. The account ID is retrieved automatically or you may pass `account_id`.""",
)
async def budget_notifications(
    ctx: Context,
    budget_name: str,
    max_results: int = 100,
    account_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Reads the notifications configured on a budget (DescribeNotificationsForBudget).

    Args:
        ctx: The MCP context object.
        budget_name: The budget whose notifications to read. Required.
        max_results: Maximum number of results to return. Defaults to 100.
        account_id: Optional AWS account ID; retrieved automatically if not provided.

    Returns:
        Dict containing the formatted notification configuration.
    """
    try:
        await ctx.info(
            f'budget-notifications (budget_name={budget_name}, max_results={max_results})'
        )

        if not budget_name:
            raise ValueError('budget_name is required')

        if not account_id:
            account_id = await get_aws_account_id(ctx)
        await ctx.info(f'Using AWS Account ID: {account_id}')

        return await describe_notifications_for_budget(ctx, account_id, budget_name, max_results)

    except Exception as e:
        return await handle_aws_error(ctx, e, 'budget-notifications', 'AWS Budgets')


# =============================================================================
# Account helper
# =============================================================================


async def get_aws_account_id(ctx: Context) -> str:
    """Retrieves the AWS account ID of the calling identity.

    Returns:
        str: The AWS account ID.

    Raises:
        Exception: If unable to retrieve the AWS account ID.
    """
    try:
        # Create an STS client using shared utility
        sts_client = create_aws_client('sts')

        await ctx.info('Retrieving AWS account ID from STS')

        # Call get-caller-identity to retrieve the account ID
        response = sts_client.get_caller_identity()

        # Extract and return the account ID
        return response['Account']
    except Exception as e:
        # Proper error handling - raise the exception with a clear message
        raise Exception(f'Failed to retrieve AWS account ID: {str(e)}')


# =============================================================================
# Operation handlers (AWS API calls)
# =============================================================================


async def describe_budgets(
    ctx: Context, account_id: str, budget_name: Optional[str], max_results: int
) -> Dict[str, Any]:
    """Retrieves budgets using the AWS Budgets API (DescribeBudgets).

    Args:
        ctx: The MCP context object.
        account_id: The AWS account ID.
        budget_name: Optional budget name filter.
        max_results: Maximum number of results to return.

    Returns:
        Dict containing the formatted budget information.
    """
    try:
        # Prepare the request parameters
        request_params = {'AccountId': account_id, 'MaxResults': max_results}

        # Initialize Budgets client using shared utility
        budgets_client = create_aws_client('budgets', region_name='us-east-1')

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
                'budgets': formatted_budgets,
                'total_count': len(formatted_budgets),
                'account_id': account_id,
            },
        )

    except Exception as e:
        # Use shared error handler for consistent error reporting
        return await handle_aws_error(ctx, e, 'describe_budgets', 'AWS Budgets')


async def describe_budget_actions(
    ctx: Context, account_id: str, budget_name: Optional[str], max_results: int
) -> Dict[str, Any]:
    """Retrieves budget enforcement actions via DescribeBudgetActionsForAccount.

    Always calls the account-scoped API (one permission,
    `budgets:DescribeBudgetActionsForAccount`, covers both the account-wide audit and a
    single-budget lookup). If `budget_name` is provided, the account-wide result is filtered to
    that budget client-side — the AWS API has no `BudgetName` parameter for the account call.

    An empty `actions` list is a real answer (no actions configured), distinct from an error.
    """
    try:
        budgets_client = create_aws_client('budgets', region_name='us-east-1')

        request_params: Dict[str, Any] = {'AccountId': account_id}
        all_actions: List[Dict[str, Any]] = []
        next_token = None
        page_count = 0

        while True:
            page_count += 1
            if next_token:
                request_params['NextToken'] = next_token
            # When filtering to one budget we cannot bound MaxResults by the filtered
            # count, so page fully; otherwise stop once we have max_results.
            if not budget_name:
                remaining = max_results - len(all_actions)
                if remaining <= 0:
                    break
                request_params['MaxResults'] = min(100, remaining)
            else:
                request_params['MaxResults'] = 100

            await ctx.info(f'Fetching account budget actions page {page_count}')
            response = budgets_client.describe_budget_actions_for_account(**request_params)
            all_actions.extend(response.get('Actions', []))
            next_token = response.get('NextToken')
            if not next_token:
                break

        if budget_name:
            all_actions = [a for a in all_actions if a.get('BudgetName') == budget_name]
            all_actions = all_actions[:max_results]

        data: Dict[str, Any] = {
            'actions': [format_action(a) for a in all_actions],
            'total_count': len(all_actions),
            'account_id': account_id,
        }
        if budget_name:
            data['budget_name'] = budget_name

        return format_response('success', data)
    except Exception as e:
        return await handle_aws_error(ctx, e, 'describe_budget_actions', 'AWS Budgets')


async def describe_notifications_for_budget(
    ctx: Context, account_id: str, budget_name: str, max_results: int
) -> Dict[str, Any]:
    """Retrieves the notifications configured on a budget (DescribeNotificationsForBudget).

    Per-budget only — the AWS Budgets API has no account-scoped notifications read, so this
    requires `budget_name`. Authorized by `budgets:ViewBudget`.
    """
    try:
        budgets_client = create_aws_client('budgets', region_name='us-east-1')

        request_params: Dict[str, Any] = {'AccountId': account_id, 'BudgetName': budget_name}
        all_notifications: List[Dict[str, Any]] = []
        next_token = None
        page_count = 0

        while True:
            page_count += 1
            if next_token:
                request_params['NextToken'] = next_token
            remaining = max_results - len(all_notifications)
            if remaining <= 0:
                break
            request_params['MaxResults'] = min(100, remaining)

            await ctx.info(f'Fetching notifications page {page_count}')
            response = budgets_client.describe_notifications_for_budget(**request_params)
            all_notifications.extend(response.get('Notifications', []))
            next_token = response.get('NextToken')
            if not next_token:
                break

        return format_response(
            'success',
            {
                'notifications': [format_notification(n) for n in all_notifications],
                'total_count': len(all_notifications),
                'budget_name': budget_name,
                'account_id': account_id,
            },
        )
    except Exception as e:
        return await handle_aws_error(ctx, e, 'describe_notifications_for_budget', 'AWS Budgets')


# =============================================================================
# Formatters (raw AWS API dict -> response shape)
# =============================================================================


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


def format_action(action: Dict[str, Any]) -> Dict[str, Any]:
    """Formats a budget Action object from the AWS API response."""
    formatted: Dict[str, Any] = {
        'action_id': action.get('ActionId'),
        'budget_name': action.get('BudgetName'),
        'notification_type': action.get('NotificationType'),
        'action_type': action.get('ActionType'),
        'approval_model': action.get('ApprovalModel'),
        'execution_role_arn': action.get('ExecutionRoleArn'),
        'status': action.get('Status'),
    }

    if 'ActionThreshold' in action:
        threshold = action['ActionThreshold']
        formatted['action_threshold'] = {
            'action_threshold_value': threshold.get('ActionThresholdValue'),
            'action_threshold_type': threshold.get('ActionThresholdType'),
        }

    if 'Definition' in action:
        formatted['definition'] = format_action_definition(action['Definition'])

    if 'Subscribers' in action:
        formatted['subscribers'] = [
            {
                'subscription_type': s.get('SubscriptionType'),
                'address': s.get('Address'),
            }
            for s in action['Subscribers']
        ]

    return formatted


def format_action_definition(definition: Dict[str, Any]) -> Dict[str, Any]:
    """Formats an action Definition — one of IAM / SCP / SSM sub-definitions."""
    result: Dict[str, Any] = {}

    if 'IamActionDefinition' in definition:
        iam = definition['IamActionDefinition']
        entry: Dict[str, Any] = {'policy_arn': iam.get('PolicyArn')}
        if iam.get('Roles'):
            entry['roles'] = iam['Roles']
        if iam.get('Groups'):
            entry['groups'] = iam['Groups']
        if iam.get('Users'):
            entry['users'] = iam['Users']
        result['iam_action_definition'] = entry

    if 'ScpActionDefinition' in definition:
        scp = definition['ScpActionDefinition']
        result['scp_action_definition'] = {
            'policy_id': scp.get('PolicyId'),
            'target_ids': scp.get('TargetIds', []),
        }

    if 'SsmActionDefinition' in definition:
        ssm = definition['SsmActionDefinition']
        result['ssm_action_definition'] = {
            'action_sub_type': ssm.get('ActionSubType'),
            'instance_ids': ssm.get('InstanceIds', []),
            'region': ssm.get('Region'),
        }

    return result


def format_notification(notification: Dict[str, Any]) -> Dict[str, Any]:
    """Formats a budget Notification object from the AWS API response."""
    return {
        'notification_type': notification.get('NotificationType'),
        'comparison_operator': notification.get('ComparisonOperator'),
        'threshold': notification.get('Threshold'),
        'threshold_type': notification.get('ThresholdType'),
        'notification_state': notification.get('NotificationState'),
    }
