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

from ..utilities.aws_service_base import (
    PageSpec,
    create_aws_client,
    format_response,
    handle_aws_error,
    paginate_aws_items,
    with_pagination,
)
from ..utilities.sql_utils import convert_response_if_needed
from botocore.exceptions import ClientError
from datetime import datetime
from fastmcp import Context, FastMCP
from typing import Any, Dict, List, Optional


budget_server = FastMCP(name='budget-tools', instructions='Tools for working with AWS Budgets API')


_PAGINATION_DESCRIPTION = """Pagination: `max_items` is the total number of items to return. Omit it to fetch every
page (no limit); pass it when the account can have many budgets. A partial result leads with
`complete_dataset: false` and a `warning`: call again with a larger `max_items`, continue by passing
`pagination.next_token` back as `next_token`, or say in the answer that the result is partial.
`pagination.items_returned` counts the items in this response, not every item that exists."""


# =============================================================================
# Tool entrypoints
# =============================================================================


@budget_server.tool(
    name='budgets',
    description="""Retrieves AWS budget information using the AWS Budgets API.

This tool uses the DescribeBudgets API to retrieve all budgets for an account, or the
DescribeBudget API to retrieve one budget when `budget_name` is given (an exact name match; an
unknown name returns an empty `budgets` list).

The API returns information about:
- Budget names, types, and time periods
- Budget limits (amount and unit)
- Current actual spend
- Forecasted spend
- Cost filters applied to budgets

With this information, you can determine which budgets have been exceeded or are projected to exceed their limits.

"""
    + _PAGINATION_DESCRIPTION
    + """ `max_items` and `next_token` apply only when
`budget_name` is omitted.

The tool automatically retrieves the AWS account ID of the calling identity or uses the provided account_id.""",
)
async def budgets(
    ctx: Context,
    budget_name: Optional[str] = None,
    account_id: Optional[str] = None,
    max_items: Optional[int] = None,
    next_token: Optional[str] = None,
) -> Dict[str, Any]:
    """Retrieves AWS budget information using the AWS Budgets API.

    Args:
        ctx: The MCP context object
        budget_name: Optional exact budget name. If provided, only that budget is returned.
        account_id: Optional AWS account ID. If not provided, it will be retrieved automatically.
        max_items: Optional total number of budgets to return. Omit it to fetch every page.
            Ignored when budget_name is given.
        next_token: Optional pagination token from a previous response. Ignored when
            budget_name is given.

    Returns:
        Dict containing the budget information
    """
    try:
        await ctx.info('Retrieving budgets')

        # Get the AWS account ID dynamically or use provided one
        if not account_id:
            account_id = await get_aws_account_id(ctx)

        return await describe_budgets(ctx, account_id, budget_name, max_items, next_token)

    except Exception as e:
        # Use shared error handler for consistent error reporting
        return await handle_aws_error(ctx, e, 'budgets', 'AWS Budgets')


@budget_server.tool(
    name='budget-actions',
    description="""Reads the enforcement action(s) attached to AWS Budgets.

A budget action is what AWS Budgets automatically does when a threshold is crossed — apply an
IAM or SCP policy, or run an SSM document. Read-only.

- Omit `budget_name` to audit every budget's actions across the account
  (DescribeBudgetActionsForAccount). This is the efficient way to find budgets with no
  enforcement configured.
- Pass `budget_name` to read one budget's actions directly (DescribeBudgetActionsForBudget) —
  no account-wide scan.

"""
    + _PAGINATION_DESCRIPTION
    + """ Large responses are automatically offloaded to
session SQL to save tokens.

An empty `actions` list is a real answer (a budget with no actions), distinct from an error
such as AccessDenied. For a budget's spend-vs-limit status use the `budgets` tool; for its alert
thresholds use `budget-notifications`. The account ID is retrieved automatically or you may pass
`account_id`.""",
)
async def budget_actions(
    ctx: Context,
    budget_name: Optional[str] = None,
    account_id: Optional[str] = None,
    max_items: Optional[int] = None,
    next_token: Optional[str] = None,
) -> Dict[str, Any]:
    """Reads AWS Budgets enforcement actions.

    Routes by ``budget_name``: DescribeBudgetActionsForBudget when a name is given, otherwise
    the account-wide DescribeBudgetActionsForAccount.

    Args:
        ctx: The MCP context object.
        budget_name: Optional. When provided, reads that one budget's actions directly.
        account_id: Optional AWS account ID; retrieved automatically if not provided.
        max_items: Optional total number of actions to return. Omit it to fetch every page.
        next_token: Optional pagination token from a previous response.

    Returns:
        Dict containing the formatted action configuration.
    """
    try:
        await ctx.info('Retrieving budget actions')

        if not account_id:
            account_id = await get_aws_account_id(ctx)

        return await describe_budget_actions(ctx, account_id, budget_name, max_items, next_token)

    except Exception as e:
        return await handle_aws_error(ctx, e, 'budget-actions', 'AWS Budgets')


@budget_server.tool(
    name='budget-notifications',
    description="""Reads the alert thresholds (notifications) configured on AWS Budgets.

A notification is an alert that fires when a budget crosses a threshold (e.g. 80% of the limit).
Read-only.

- Omit `budget_name` to audit every budget's notifications across the account
  (DescribeBudgetNotificationsForAccount). Each returned notification carries its `budget_name`.
- Pass `budget_name` to read one budget's notifications directly (DescribeNotificationsForBudget).

"""
    + _PAGINATION_DESCRIPTION
    + """ The account-wide call returns whole budgets
(up to 10 notifications each), so a `max_items` below 10 can still return up to 10 notifications.
Large responses are automatically offloaded to session SQL to save tokens.

For a budget's spend-vs-limit status use the `budgets` tool; for its enforcement actions use
`budget-actions`. The account ID is retrieved automatically or you may pass `account_id`.""",
)
async def budget_notifications(
    ctx: Context,
    budget_name: Optional[str] = None,
    account_id: Optional[str] = None,
    max_items: Optional[int] = None,
    next_token: Optional[str] = None,
) -> Dict[str, Any]:
    """Reads the notifications configured on AWS Budgets.

    Routes by ``budget_name``: DescribeNotificationsForBudget when a name is given, otherwise
    the account-wide DescribeBudgetNotificationsForAccount.

    Args:
        ctx: The MCP context object.
        budget_name: Optional. When provided, reads that one budget's notifications directly.
        account_id: Optional AWS account ID; retrieved automatically if not provided.
        max_items: Optional total number of notifications to return. Omit it to fetch every
            page.
        next_token: Optional pagination token from a previous response.

    Returns:
        Dict containing the formatted notification configuration.
    """
    try:
        await ctx.info('Retrieving budget notifications')

        if not account_id:
            account_id = await get_aws_account_id(ctx)

        return await describe_budget_notifications(
            ctx, account_id, budget_name, max_items, next_token
        )

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
        ClientError, BotoCoreError: If STS fails. They propagate unwrapped so
            handle_aws_error keeps the AWS error code (e.g. throttling is retryable).
    """
    # Create an STS client using shared utility
    sts_client = create_aws_client('sts')

    await ctx.info('Retrieving AWS account ID from STS')

    # Call get-caller-identity to retrieve the account ID
    response = sts_client.get_caller_identity()

    # Extract and return the account ID
    return response['Account']


# =============================================================================
# Operation handlers (AWS API calls)
# =============================================================================


# DescribeBudgets: MaxResults 1-1000. A page can be short, or empty, while a token is still
# returned.
BUDGETS_DESCRIBE_BUDGETS = PageSpec(
    result_key='Budgets',
    token_param='NextToken',
    token_key_in_response='NextToken',
    page_max=1000,
    page_size_param='MaxResults',
)

# DescribeBudgetActionsForAccount / DescribeBudgetActionsForBudget: MaxResults 1-100. The
# account-level call can return a short or empty page with a token.
BUDGETS_DESCRIBE_BUDGET_ACTIONS = PageSpec(
    result_key='Actions',
    token_param='NextToken',
    token_key_in_response='NextToken',
    page_max=100,
    page_size_param='MaxResults',
)

# DescribeNotificationsForBudget: MaxResults 1-100 (a budget has at most 10 notifications).
BUDGETS_DESCRIBE_NOTIFICATIONS_FOR_BUDGET = PageSpec(
    result_key='Notifications',
    token_param='NextToken',
    token_key_in_response='NextToken',
    page_max=100,
    page_size_param='MaxResults',
)


def _count_budget_notifications(entries: List[Dict[str, Any]]) -> int:
    """Count the notifications across one page of per-budget entries."""
    return sum(len(entry.get('Notifications') or []) for entry in entries)


# DescribeBudgetNotificationsForAccount: MaxResults (1-1000) counts BUDGETS, each with up to 10
# notifications, so one unit of page size can hold 10 items. A budget can hold more than 10;
# the helper keeps such a page and logs it.
BUDGETS_DESCRIBE_BUDGET_NOTIFICATIONS_FOR_ACCOUNT = PageSpec(
    result_key='BudgetNotificationsForAccount',
    token_param='NextToken',
    token_key_in_response='NextToken',
    page_max=10000,
    page_size_param='MaxResults',
    items_per_page_unit=10,
    count_items=_count_budget_notifications,
)


def _describe_budget_by_name(
    budgets_client: Any, account_id: str, budget_name: str
) -> List[Dict[str, Any]]:
    """Read one budget by exact name, or an empty list when it does not exist."""
    try:
        response = budgets_client.describe_budget(AccountId=account_id, BudgetName=budget_name)
    except ClientError as e:
        if e.response.get('Error', {}).get('Code') == 'NotFoundException':
            return []
        raise
    budget = response.get('Budget')
    return [budget] if budget else []


async def describe_budgets(
    ctx: Context,
    account_id: str,
    budget_name: Optional[str],
    max_items: Optional[int] = None,
    next_token: Optional[str] = None,
) -> Dict[str, Any]:
    """Retrieves budgets using the AWS Budgets API.

    With ``budget_name``, reads that one budget with DescribeBudget, so the name match never
    depends on which page the budget falls on. Otherwise pages through DescribeBudgets.

    Args:
        ctx: The MCP context object.
        account_id: The AWS account ID.
        budget_name: Optional exact budget name.
        max_items: Most budgets to return. None fetches every page. Ignored with budget_name.
        next_token: Pagination token from a previous response. Ignored with budget_name.

    Returns:
        Dict containing the formatted budget information and a ``pagination`` block.
    """
    try:
        budgets_client = create_aws_client('budgets', region_name='us-east-1')

        if budget_name:
            raw_budgets = _describe_budget_by_name(budgets_client, account_id, budget_name)
            pagination: Dict[str, Any] = {
                'complete_dataset': True,
                'has_more': False,
                'next_token': None,
                'items_returned': len(raw_budgets),
            }
        else:
            raw_budgets, _, pagination = await paginate_aws_items(
                ctx,
                'DescribeBudgets',
                budgets_client.describe_budgets,
                {'AccountId': account_id},
                BUDGETS_DESCRIBE_BUDGETS,
                max_items=max_items,
                next_token=next_token,
            )

        data = {'budgets': format_budgets(raw_budgets), 'account_id': account_id}
        return format_response('success', with_pagination(data, pagination))

    except Exception as e:
        # Use shared error handler for consistent error reporting
        return await handle_aws_error(ctx, e, 'describe_budgets', 'AWS Budgets')


async def describe_budget_actions(
    ctx: Context,
    account_id: str,
    budget_name: Optional[str],
    max_items: Optional[int] = None,
    next_token: Optional[str] = None,
) -> Dict[str, Any]:
    """Retrieves budget enforcement actions, routing by ``budget_name``.

    When ``budget_name`` is provided, calls the per-budget DescribeBudgetActionsForBudget
    (authorized by ``budgets:DescribeBudgetActionsForBudget``); otherwise calls the account-wide
    DescribeBudgetActionsForAccount (``budgets:DescribeBudgetActionsForAccount``). Both are
    paginated via the shared helper, and a large response is offloaded to session SQL.

    An empty ``actions`` list is a real answer (no actions configured), distinct from an error.
    """
    try:
        budgets_client = create_aws_client('budgets', region_name='us-east-1')

        request_params: Dict[str, Any] = {'AccountId': account_id}
        if budget_name:
            request_params['BudgetName'] = budget_name
            operation = 'DescribeBudgetActionsForBudget'
            api_call = budgets_client.describe_budget_actions_for_budget
        else:
            operation = 'DescribeBudgetActionsForAccount'
            api_call = budgets_client.describe_budget_actions_for_account

        all_actions, _, pagination = await paginate_aws_items(
            ctx,
            operation,
            api_call,
            request_params,
            BUDGETS_DESCRIBE_BUDGET_ACTIONS,
            max_items=max_items,
            next_token=next_token,
        )

        data: Dict[str, Any] = {
            'actions': [format_action(a) for a in all_actions],
            'account_id': account_id,
        }
        if budget_name:
            data['budget_name'] = budget_name

        converted = await convert_response_if_needed(
            ctx, with_pagination(data, pagination), 'budget_actions'
        )
        return format_response('success', converted)
    except Exception as e:
        return await handle_aws_error(ctx, e, 'describe_budget_actions', 'AWS Budgets')


async def describe_budget_notifications(
    ctx: Context,
    account_id: str,
    budget_name: Optional[str],
    max_items: Optional[int] = None,
    next_token: Optional[str] = None,
) -> Dict[str, Any]:
    """Retrieves budget notifications, routing by ``budget_name``.

    When ``budget_name`` is provided, calls the per-budget DescribeNotificationsForBudget;
    otherwise calls the account-wide DescribeBudgetNotificationsForAccount, whose response nests
    notifications under each budget. Both are paginated via the shared helper, and a large
    response is offloaded to session SQL. Every returned notification carries its ``budget_name``.
    """
    try:
        budgets_client = create_aws_client('budgets', region_name='us-east-1')

        if budget_name:
            raw_notifications, _, pagination = await paginate_aws_items(
                ctx,
                'DescribeNotificationsForBudget',
                budgets_client.describe_notifications_for_budget,
                {'AccountId': account_id, 'BudgetName': budget_name},
                BUDGETS_DESCRIBE_NOTIFICATIONS_FOR_BUDGET,
                max_items=max_items,
                next_token=next_token,
            )
            notifications = [format_notification(n, budget_name) for n in raw_notifications]
        else:
            per_budget, _, pagination = await paginate_aws_items(
                ctx,
                'DescribeBudgetNotificationsForAccount',
                budgets_client.describe_budget_notifications_for_account,
                {'AccountId': account_id},
                BUDGETS_DESCRIBE_BUDGET_NOTIFICATIONS_FOR_ACCOUNT,
                max_items=max_items,
                next_token=next_token,
            )
            # Each entry groups one budget's notifications; flatten and stamp the budget name.
            notifications = [
                format_notification(n, entry.get('BudgetName'))
                for entry in per_budget
                for n in entry.get('Notifications', [])
            ]

        data: Dict[str, Any] = {
            'notifications': notifications,
            'account_id': account_id,
        }
        if budget_name:
            data['budget_name'] = budget_name

        converted = await convert_response_if_needed(
            ctx, with_pagination(data, pagination), 'budget_notifications'
        )
        return format_response('success', converted)
    except Exception as e:
        return await handle_aws_error(ctx, e, 'describe_budget_notifications', 'AWS Budgets')


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


def format_notification(
    notification: Dict[str, Any], budget_name: Optional[str] = None
) -> Dict[str, Any]:
    """Formats a budget Notification object from the AWS API response.

    Args:
        notification: The raw Notification object from the AWS API.
        budget_name: The budget this notification belongs to. Stamped onto the result so a
            flattened account-wide list stays attributable to its budget.
    """
    formatted = {
        'notification_type': notification.get('NotificationType'),
        'comparison_operator': notification.get('ComparisonOperator'),
        'threshold': notification.get('Threshold'),
        'threshold_type': notification.get('ThresholdType'),
        'notification_state': notification.get('NotificationState'),
    }
    if budget_name is not None:
        formatted['budget_name'] = budget_name
    return formatted
