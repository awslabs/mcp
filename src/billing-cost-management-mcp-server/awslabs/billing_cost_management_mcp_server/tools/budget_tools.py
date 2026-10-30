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
  (`budgets`, `budget-actions`, `budget-notifications`, `budget-performance-history`).
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
from ..utilities.constants import PAGINATION_LIMIT_TEXT
from ..utilities.sql_utils import convert_response_if_needed
from ..utilities.time_utils import format_timestamp_to_utc_iso
from botocore.exceptions import ClientError
from datetime import datetime, timezone
from fastmcp import Context, FastMCP
from typing import Any, Dict, List, Optional


budget_server = FastMCP(name='budget-tools', instructions='Tools for working with AWS Budgets API')


_PAGINATION_DESCRIPTION = (
    """Pagination: `max_items` is the total number of items to return. If it is omitted, the tool fetches every page for """
    + PAGINATION_LIMIT_TEXT
    + """, then returns a partial result; pass it when the account can have many budgets. A partial result leads with
`complete_dataset: false` and a `warning`: call again with a larger `max_items`, continue by passing
`pagination.next_token` back as `next_token`, or say in the answer that the result is partial.
`pagination.items_returned` counts the items in this response, not every item that exists."""
)


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
- Budget limits (amount and unit), and any planned per-period limits or auto-adjust settings
- Current actual spend
- Forecasted spend
- The scope each budget tracks: its filter, cost metric and billing view, and whether AWS is
  still updating its spend

A budget's filter is in `filter_expression` (an Expression of Dimensions, Tags, CostCategories and
ProductAttributes combined with And, Or and Not) or, for budgets that use the deprecated form, in
`cost_filters`.
AWS does not forecast a COST or USAGE budget filtered by ProductAttributes, and its alerts can fire
only on actual spend, not on a forecast. Such a budget with no `forecasted_spend` carries
`forecast_note`: its `status`, when present, is `EXCEEDED` or `OK` from actual spend alone.
If `filter_expression_incomplete` is true, part of the filter could not be read (an empty or null
node in `filter_expression`): the budget is still filtered and `calculated_spend` reflects its full
filter.
`metrics` (or the deprecated `cost_types`) says how cost is measured, and `billing_view_arn` names
the billing view the budget reads, which can be a non-primary view such as a billing group or
custom view. A budget with no filter tracks everything its budget type measures in its billing
view. `calculated_spend` is computed on the budget's own filter, metric and billing view, so
compare it only with a Cost Explorer query that applies the same ones, never with an unfiltered
total. A `health_status` of `UNHEALTHY` means AWS has stopped updating the budget's spend, for
example because it can no longer read its billing view (`status_reason` says why), so its
`calculated_spend` may be stale.

An `actual_spend` of 0 on a filtered budget does not prove there was no spend: a filter that
matches nothing also tracks 0, and no error is raised. Two common causes: SERVICE (or `cost_filters`
`Service`) values given as service codes such as `AmazonEC2` instead of Cost Explorer service names
such as `Amazon Elastic Compute Cloud - Compute`; and `cost_filters` keys are combined with AND
(values within one key with OR), so keys that never occur together match nothing. Before reporting
no spend, run the equivalent filter, metric and billing view with `cost-explorer`. In
`filter_expression`, a tag value of `""` matches costs that have no value for that tag key.

In `cost_types` on a COST budget, `IncludeCredit` and `IncludeRefund` default to true, so unless
they are false the budget's spend is net of credits and refunds. A COST budget with no `cost_types`
includes credits and refunds unless its `filter_expression` excludes them, for example with a `Not`
on dimension `RECORD_TYPE` with values `Credit` and `Refund`. USAGE, RI and Savings Plans budgets
can also return `cost_types`; when an RI or Savings Plans budget returns it, it is
`IncludeSubscription` true and all else false.

`budget_limit` is the limit for the current period. A budget with `planned_budget_limits` has a
limit for each period of its plan (`period_start` in UTC; past periods are included) and keeps the
last one after the plan ends. A budget with `auto_adjust` (`last_auto_adjust_time` in UTC) has its
limit recomputed by AWS, from the average of up to `budget_adjustment_period` past periods
(`HISTORICAL`; `look_back_available_periods` is how many of those periods were averaged; periods
before the first one with cost are left out) or from the forecast (`FORECAST`), so the limit can
change with no one editing the budget.

With this information, you can determine which budgets have been exceeded or are projected to exceed their limits.

`status` (`EXCEEDED`, `FORECASTED_TO_EXCEED` or `OK`) compares actual and forecasted spend with the
limit, and is returned only for COST and USAGE budgets. RI_UTILIZATION, RI_COVERAGE,
SAVINGS_PLANS_UTILIZATION and SAVINGS_PLANS_COVERAGE budgets have no `status`: their limit is always
100 PERCENTAGE, `actual_spend` is the utilization or coverage percentage (higher is better), and
they alert when it falls below a notification threshold. For those, compare `actual_spend` with the
thresholds from `budget-notifications`, where `notification_state` is `ALARM` once a threshold is
crossed.

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


@budget_server.tool(
    name='budget-performance-history',
    description="""Reads a budget's performance history using the DescribeBudgetPerformanceHistory API:
for each period, the amount budgeted and the actual cost or usage. Use it to answer "was this
budget over last month?" or "which months breached?"; the `budgets` tool covers only the current
period. Read-only.

- Only DAILY, MONTHLY and QUARTERLY budgets have history. A CUSTOM or ANNUALLY budget returns a
  validation_error.
- The tool returns the service's default window: up to 13 MONTHLY periods (this month and the
  previous 12), 4 QUARTERLY periods or 60 DAILY periods. History starts when the budget was
  created (or re-created), whatever its start date, so a newer budget returns fewer periods:
  one created this period returns only the current one.
- `periods` are oldest first. Each has `start` and `end` (UTC dates; the end is exclusive, the
  start of the next period), `budgeted_amount` (the limit that applied in that period; null when
  the budget had none for it) and `actual_amount` (null when no actual data is available). The
  last period is the one containing today, so its actual amount is to date, not final.
- Amounts are decimal strings with a `unit`: compare them as numbers. For RI and Savings Plans
  utilization and coverage budgets they are percentages, and a period breached when
  `actual_amount` is below `budgeted_amount`; for COST and USAGE budgets, when it is above.
- `actual_amount` is measured with the budget's own filter and cost settings, so it can differ
  from an unfiltered Cost Explorer total.
- `time_unit` is often null: the service omits it for many budgets, and nothing in a budget's
  definition shows which. Take the time unit from the `budgets` tool, which always returns it.
- An unknown `budget_name` (an exact name) returns NotFoundException.

Pagination: the whole history fits in one page (at most 60 periods), so omit `max_items`;
passing it only trims the result, and `next_token` continues a trimmed one.

The account ID is retrieved automatically or you may pass `account_id`.""",
)
async def budget_performance_history(
    ctx: Context,
    budget_name: str,
    account_id: Optional[str] = None,
    max_items: Optional[int] = None,
    next_token: Optional[str] = None,
) -> Dict[str, Any]:
    """Reads a budget's budgeted and actual amounts per period.

    Args:
        ctx: The MCP context object.
        budget_name: Exact name of the budget.
        account_id: Optional AWS account ID; retrieved automatically if not provided.
        max_items: Optional total number of periods to return. Omit it to fetch every page.
        next_token: Optional pagination token from a previous response.

    Returns:
        Dict containing the budget's periods and a ``pagination`` block.
    """
    if not budget_name or not budget_name.strip():
        return format_response(
            'error',
            {'invalid_parameter': 'budget_name'},
            'budget_name is required: pass the exact name of a budget.',
            error_type='validation_error',
            operation='budget-performance-history',
            service='AWS Budgets',
        )

    try:
        await ctx.info('Retrieving budget performance history')

        if not account_id:
            account_id = await get_aws_account_id(ctx)

        return await describe_budget_performance_history(
            ctx, account_id, budget_name, max_items, next_token
        )

    except Exception as e:
        return await handle_aws_error(ctx, e, 'budget-performance-history', 'AWS Budgets')


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


# DescribeBudgetPerformanceHistory: MaxResults 1-100, each item one budget period. The periods
# are nested under BudgetPerformanceHistory, which also carries the budget's name and type.
BUDGETS_DESCRIBE_BUDGET_PERFORMANCE_HISTORY = PageSpec(
    result_key=('BudgetPerformanceHistory', 'BudgetedAndActualAmountsList'),
    token_param='NextToken',
    token_key_in_response='NextToken',
    page_max=100,
    page_size_param='MaxResults',
)

# The API's InvalidParameterException text for a budget whose time unit has no history
# (CUSTOM and ANNUALLY; a budget gets a history record when it is created).
_UNSUPPORTED_HISTORY_MESSAGE = 'does not support custom time periods'


def _no_history_error(budget_name: str) -> Dict[str, Any]:
    """The validation_error for a budget whose time unit has no performance history."""
    return format_response(
        'error',
        {'budget_name': budget_name},
        f'Budget {budget_name} has no performance history: history exists only for DAILY, '
        'MONTHLY and QUARTERLY budgets, and this budget is CUSTOM or ANNUALLY. Use the budgets '
        'tool for its current period.',
        error_type='validation_error',
        operation='budget-performance-history',
        service='AWS Budgets',
    )


async def describe_budget_performance_history(
    ctx: Context,
    account_id: str,
    budget_name: str,
    max_items: Optional[int] = None,
    next_token: Optional[str] = None,
) -> Dict[str, Any]:
    """Retrieves a budget's performance history, paging through its periods.

    A budget whose time unit has no history is reported as a validation_error naming the
    supported time units; other failures go to the shared handler.
    """
    try:
        budgets_client = create_aws_client('budgets', region_name='us-east-1')

        periods, pages, pagination = await paginate_aws_items(
            ctx,
            'DescribeBudgetPerformanceHistory',
            budgets_client.describe_budget_performance_history,
            {'AccountId': account_id, 'BudgetName': budget_name},
            BUDGETS_DESCRIBE_BUDGET_PERFORMANCE_HISTORY,
            max_items=max_items,
            next_token=next_token,
        )
    except ClientError as e:
        error = e.response.get('Error', {})
        if error.get('Code') == 'InvalidParameterException' and _UNSUPPORTED_HISTORY_MESSAGE in (
            error.get('Message') or ''
        ):
            return _no_history_error(budget_name)
        return await handle_aws_error(ctx, e, 'describe_budget_performance_history', 'AWS Budgets')
    except Exception as e:
        return await handle_aws_error(ctx, e, 'describe_budget_performance_history', 'AWS Budgets')

    history = (pages[0] if pages else {}).get('BudgetPerformanceHistory') or {}
    if history.get('TimeUnit') == 'ANNUALLY' and not periods:
        # The API rejects an ANNUALLY budget only when its history query finds a record, which a
        # budget gets on creation; a missing record (a rare data gap) returns no periods instead.
        return _no_history_error(budget_name)
    # At most 60 periods, so unlike budget-actions this is never offloaded to session SQL.
    data = {
        'budget_name': history.get('BudgetName', budget_name),
        'budget_type': history.get('BudgetType'),
        'time_unit': history.get('TimeUnit'),
        'account_id': account_id,
        'periods': [format_budget_period(period) for period in periods],
    }
    return format_response('success', with_pagination(data, pagination))


# =============================================================================
# Formatters (raw AWS API dict -> response shape)
# =============================================================================


# Budget types where more spend is worse, so actual or forecast at or above the limit is a breach.
# Utilization and coverage budgets (limit fixed at 100 PERCENTAGE) alert when actual falls below a
# notification threshold instead, so a spend-vs-limit status would read them inverted.
_SPEND_BUDGET_TYPES = frozenset({'COST', 'USAGE'})

_FILTER_EXPRESSION_INCOMPLETE_NOTE = (
    "Part of this budget's filter could not be read (an empty or null node in "
    "filter_expression), for example a filter type newer than this server's AWS SDK. The budget is "
    'still filtered and calculated_spend reflects its full filter; do not treat it as unfiltered.'
)

_FORECAST_NOTE = (
    'AWS does not forecast budgets filtered by ProductAttributes, so status, when present, is '
    'EXCEEDED or OK from actual spend only, never FORECASTED_TO_EXCEED; OK does not mean spend is '
    'on track to stay under the limit.'
)


def _expression_nodes(expression: Any):
    """Yield every node of a budgets Expression tree (And, Or and Not children included)."""
    yield expression
    if isinstance(expression, dict):
        for key in ('And', 'Or'):
            for child in expression.get(key) or []:
                yield from _expression_nodes(child)
        if 'Not' in expression:
            yield from _expression_nodes(expression['Not'])


def _has_unreadable_node(expression: Any) -> bool:
    """True if a node is empty or null: botocore parses a member it does not know as {}.

    An empty leaf such as {'Dimensions': {}} is not checked: the service never sends one.
    """
    return any(not node for node in _expression_nodes(expression))


def _has_product_attributes(expression: Any) -> bool:
    """True if the Expression has a ProductAttributes leaf at any depth."""
    return any(
        isinstance(node, dict) and 'ProductAttributes' in node
        for node in _expression_nodes(expression)
    )


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

        # Add the budget's scope if present; calculated_spend is computed on it.
        if 'CostFilters' in budget and budget['CostFilters']:
            formatted_budget['cost_filters'] = budget['CostFilters']
        # The API omits FilterExpression for an unfiltered budget, so a present one is kept even
        # when it parsed as {}: dropping it would make a filtered budget read as unfiltered.
        if 'FilterExpression' in budget:
            filter_expression = budget['FilterExpression']
            formatted_budget['filter_expression'] = filter_expression
            if _has_unreadable_node(filter_expression):
                formatted_budget['filter_expression_incomplete'] = True
                formatted_budget['filter_expression_note'] = _FILTER_EXPRESSION_INCOMPLETE_NOTE
            # Only when the response has no forecast, so the note never contradicts status.
            if (
                budget.get('BudgetType') in _SPEND_BUDGET_TYPES
                and _has_product_attributes(filter_expression)
                and 'ForecastedSpend' not in (budget.get('CalculatedSpend') or {})
            ):
                formatted_budget['forecast_note'] = _FORECAST_NOTE
        if budget.get('Metrics'):
            formatted_budget['metrics'] = budget['Metrics']
        if budget.get('CostTypes'):
            formatted_budget['cost_types'] = budget['CostTypes']
        if budget.get('BillingViewArn'):
            formatted_budget['billing_view_arn'] = budget['BillingViewArn']
        if budget.get('HealthStatus'):
            health = budget['HealthStatus']
            formatted_budget['health_status'] = {'status': health.get('Status')}
            if health.get('StatusReason'):
                formatted_budget['health_status']['status_reason'] = health['StatusReason']

        # Add planned and auto-adjusting limit settings if present; budget_limit is only the
        # current period's limit for these budgets.
        if budget.get('PlannedBudgetLimits'):
            formatted_budget['planned_budget_limits'] = format_planned_budget_limits(
                budget['PlannedBudgetLimits']
            )
        if budget.get('AutoAdjustData'):
            formatted_budget['auto_adjust'] = format_auto_adjust(budget['AutoAdjustData'])

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

        # Add budget status (derived field, COST and USAGE budgets only)
        calculated_spend = formatted_budget.get('calculated_spend')
        budget_limit = formatted_budget.get('budget_limit')

        if (
            budget.get('BudgetType') in _SPEND_BUDGET_TYPES
            and calculated_spend is not None
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


def format_planned_budget_limits(planned: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Formats PlannedBudgetLimits (epoch-second keys) as a list ordered by period start.

    A key that is not epoch seconds is kept as given, so no planned limit is dropped.
    """
    limits = []
    for key, spend in planned.items():
        try:
            period_start = datetime.fromtimestamp(int(key), tz=timezone.utc).strftime('%Y-%m-%d')
        except (TypeError, ValueError, OverflowError, OSError):
            period_start = key
        spend = spend or {}
        limits.append(
            {
                'period_start': period_start,
                'amount': spend.get('Amount'),
                'unit': spend.get('Unit'),
            }
        )
    return sorted(limits, key=lambda limit: str(limit['period_start']))


def format_auto_adjust(auto_adjust: Dict[str, Any]) -> Dict[str, Any]:
    """Formats AutoAdjustData, returning only the fields the API set."""
    formatted: Dict[str, Any] = {'auto_adjust_type': auto_adjust.get('AutoAdjustType')}
    historical = auto_adjust.get('HistoricalOptions') or {}
    if 'BudgetAdjustmentPeriod' in historical:
        formatted['budget_adjustment_period'] = historical['BudgetAdjustmentPeriod']
    if 'LookBackAvailablePeriods' in historical:
        formatted['look_back_available_periods'] = historical['LookBackAvailablePeriods']
    last = format_timestamp_to_utc_iso(auto_adjust.get('LastAutoAdjustTime'))
    if last:
        formatted['last_auto_adjust_time'] = last
    return formatted


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


def _utc_date(value: Any) -> Any:
    """Render a period boundary as a UTC date string; other values pass through."""
    if isinstance(value, datetime):
        if value.tzinfo is not None:
            value = value.astimezone(timezone.utc)
        return value.strftime('%Y-%m-%d')
    return value


def _spend(spend: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Reshape a Spend object, or None when it is absent."""
    if not spend:
        return None
    return {'amount': spend.get('Amount'), 'unit': spend.get('Unit')}


def format_budget_period(period: Dict[str, Any]) -> Dict[str, Any]:
    """Formats one BudgetedAndActualAmounts entry from DescribeBudgetPerformanceHistory."""
    time_period = period.get('TimePeriod') or {}
    return {
        'start': _utc_date(time_period.get('Start')),
        'end': _utc_date(time_period.get('End')),
        'budgeted_amount': _spend(period.get('BudgetedAmount')),
        'actual_amount': _spend(period.get('ActualAmount')),
    }
