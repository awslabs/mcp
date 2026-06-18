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

"""Detection logic for the BCM readiness checker.

Implements the diagnosis behind ``check-bcm-readiness``: a single-call pre-flight
check of an account's Billing and Cost Management configuration state, scoped to
the user's intent so only the prerequisites a given goal needs are verified.

The module is organized as:

- Intent configuration: which prerequisites each intent requires, the IAM
  actions it needs, and the capabilities it unlocks.
- Detection functions: one per prerequisite (IAM, Cost Explorer, cost allocation
  tags, Cost Optimization Hub). Each returns a normalized check result with a
  status of ``ready``, ``blocked``, or ``pending``.
- ``diagnose_readiness``: the router that runs the intent's checks in order and
  returns the first non-ready result, or a ``ready`` envelope with capabilities.

There is no direct API that distinguishes "Cost Explorer was never enabled" from
"enabled but still propagating". A pragmatic heuristic on ``GetCostAndUsage`` is
used (not-enabled exception -> not enabled; all-zero success -> propagating; real
data -> ready) and isolated in ``check_cost_explorer`` so it can be revisited.
The not-enabled signal has two observed shapes - ``DataUnavailableException`` and
``AccessDeniedException`` with a "not enabled for cost explorer access" message -
both handled in ``check_cost_explorer``.
"""

from botocore.exceptions import ClientError
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional


# --- Intent configuration ---

INTENT_BASIC = 'basic_cost_visibility'
INTENT_TAG = 'tag_analysis'
INTENT_OPTIMIZATION = 'optimization'

DEFAULT_INTENT = INTENT_BASIC

# Ordered prerequisite checks per intent. Order matters: the first blocker found
# short-circuits, so cheaper / more-fundamental checks come first.
INTENT_CHECKS: Dict[str, List[str]] = {
    INTENT_BASIC: ['iam', 'cost_explorer'],
    INTENT_TAG: ['iam', 'cost_explorer', 'tags'],
    INTENT_OPTIMIZATION: ['iam', 'cost_explorer', 'cost_optimization_hub'],
}

# IAM actions required for each intent (evaluated by SimulatePrincipalPolicy).
_BASIC_ACTIONS = ['ce:GetCostAndUsage', 'ce:GetCostForecast', 'ce:GetDimensionValues']
INTENT_IAM_ACTIONS: Dict[str, List[str]] = {
    INTENT_BASIC: _BASIC_ACTIONS,
    INTENT_TAG: _BASIC_ACTIONS + ['ce:ListCostAllocationTags'],
    INTENT_OPTIMIZATION: _BASIC_ACTIONS
    + [
        'cost-optimization-hub:ListRecommendations',
        'cost-optimization-hub:ListEnrollmentStatuses',
    ],
}

# Capabilities unlocked when an intent is ready.
INTENT_CAPABILITIES: Dict[str, List[str]] = {
    INTENT_BASIC: ['GetCostAndUsage', 'GetCostForecast', 'GetDimensionValues'],
    INTENT_TAG: ['GetCostAndUsage with TAG GroupBy'],
    INTENT_OPTIMIZATION: ['GetRecommendations', 'GetRightsizingSuggestions'],
}

# Cache durations (seconds) keyed by blocker / state, per the design.
_HOUR = 3600
_DAY = 24 * _HOUR
_FIVE_MIN = 5 * 60

CACHE_SECONDS = {
    'cost_explorer_not_enabled': _DAY,
    'cost_explorer_propagating': _DAY,
    'tags_not_activated': _DAY,
    'tags_not_available_in_linked_account': _DAY,
    'cost_optimization_hub_not_enrolled': _FIVE_MIN,
    'insufficient_iam_permissions': _FIVE_MIN,
    'cannot_verify_iam_permissions': _FIVE_MIN,
    'ready': _HOUR,
}

CACHE_REASONS = {
    'cost_explorer_not_enabled': 'State changes require 24h propagation',
    'cost_explorer_propagating': 'Waiting for 24h data propagation',
    'tags_not_activated': 'Tag activation requires 24h propagation',
    'tags_not_available_in_linked_account': 'Org structure is stable - long cache',
    'cost_optimization_hub_not_enrolled': 'Enrollment is immediate - short cache',
    'insufficient_iam_permissions': 'IAM changes are immediate - short cache',
    'cannot_verify_iam_permissions': 'IAM changes are immediate - short cache',
    'ready': 'Account state rarely changes once configured',
}


def _now() -> datetime:
    """Return the current UTC time.

    Wrapped so tests can inject a fixed clock via the ``now`` parameter of
    ``diagnose_readiness``.

    Returns:
        The current timezone-aware UTC datetime.
    """
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    """Format a datetime as a Z-suffixed ISO-8601 timestamp.

    Args:
        dt: The datetime to format.

    Returns:
        An ISO-8601 string in UTC with a trailing ``Z``.
    """
    return dt.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def _ce_date_window(now: datetime, lookback_days: int = 14) -> Dict[str, str]:
    """Build the Cost Explorer probe window.

    A multi-day window is used so the freshness check still finds data despite
    Cost Explorer's 24-48h reporting lag.

    Args:
        now: The reference "now" timestamp.
        lookback_days: How many days back the window should start.

    Returns:
        A dict with ``Start`` and ``End`` keys in ``YYYY-MM-DD`` format.
    """
    end = now.date()
    start = end - timedelta(days=lookback_days)
    return {'Start': start.strftime('%Y-%m-%d'), 'End': end.strftime('%Y-%m-%d')}


def build_cache(
    issue: str, now: datetime, valid_until: Optional[datetime] = None
) -> Dict[str, Any]:
    """Build the ``cache`` block for a response.

    Args:
        issue: The blocker / state key used to look up cache duration and reason.
        now: The reference "now" timestamp.
        valid_until: Optional explicit expiry; computed from ``issue`` if omitted.

    Returns:
        A dict with ``valid_until``, ``next_meaningful_check``, and ``reason``.
    """
    until = valid_until or (now + timedelta(seconds=CACHE_SECONDS.get(issue, _HOUR)))
    return {
        'valid_until': _iso(until),
        'next_meaningful_check': _iso(until),
        'reason': CACHE_REASONS.get(issue, 'Re-check after cache expiry'),
    }


# --- Detection: IAM permissions ---


def _principal_arn_for_simulation(caller_arn: str) -> str:
    """Convert an STS assumed-role ARN into the IAM role ARN.

    ``simulate_principal_policy`` requires an IAM user/role ARN, not the
    transient ``sts::...:assumed-role/Role/Session`` ARN returned by
    ``get_caller_identity``.

    Args:
        caller_arn: The ARN returned by ``sts:GetCallerIdentity``.

    Returns:
        The IAM role ARN when the input is an assumed-role ARN, otherwise the
        input unchanged.
    """
    parts = caller_arn.split(':')
    if len(parts) == 6 and parts[2] == 'sts' and ':assumed-role/' in caller_arn:
        account = parts[4]
        resource = parts[5]  # assumed-role/RoleName/SessionName
        segments = resource.split('/')
        if len(segments) >= 2:
            role_name = segments[1]
            return f'arn:aws:iam::{account}:role/{role_name}'
    return caller_arn


def check_iam_permissions(sts_client: Any, iam_client: Any, intent: str) -> Dict[str, Any]:
    """Diagnose whether the caller has the IAM permissions the intent needs.

    Resolves the caller principal via STS, then evaluates the intent's required
    actions with SimulatePrincipalPolicy. Reports any denied actions and whether
    an explicit deny is in play (an explicit deny cannot be fixed by attaching an
    allow policy).

    Args:
        sts_client: A boto3 STS client.
        iam_client: A boto3 IAM client.
        intent: The intent whose required actions should be evaluated.

    Returns:
        A normalized check result: ``{'status': 'ready'}`` or
        ``{'status': 'blocked', 'blocker': {...}}``.

    Raises:
        ClientError: For any AWS error other than an AccessDenied on the
            SimulatePrincipalPolicy call itself.
    """
    caller = sts_client.get_caller_identity()
    principal_arn = _principal_arn_for_simulation(caller['Arn'])
    actions = INTENT_IAM_ACTIONS[intent]

    try:
        result = iam_client.simulate_principal_policy(
            PolicySourceArn=principal_arn, ActionNames=actions
        )
    except ClientError as error:
        code = error.response.get('Error', {}).get('Code', '')
        if code == 'AccessDenied':
            # The caller cannot even run the permission probe. Fail closed with an
            # actionable blocker rather than surfacing a raw 403 - this is exactly
            # the misconfigured-account case the readiness check exists to catch.
            return {
                'status': 'blocked',
                'blocker': {
                    'issue': 'cannot_verify_iam_permissions',
                    'action': (
                        'Attach AWSBillingReadOnlyAccess policy (grants the required '
                        'billing permissions and iam:SimulatePrincipalPolicy used to '
                        'verify them)'
                    ),
                    'console_url': 'https://console.aws.amazon.com/iam/home',
                    'wait_time': 'none',
                    'is_paid': False,
                    'suggested_policy_arn': 'arn:aws:iam::aws:policy/AWSBillingReadOnlyAccess',
                    'missing_permissions': ['iam:SimulatePrincipalPolicy'],
                    'message': (
                        'Could not verify IAM permissions because the caller is not '
                        'authorized to perform iam:SimulatePrincipalPolicy. Grant this '
                        'action (and the billing read permissions) to enable readiness '
                        'checks.'
                    ),
                },
            }
        raise

    missing: List[str] = []
    has_explicit_deny = False
    for evaluation in result.get('EvaluationResults', []):
        decision = evaluation.get('EvalDecision', 'implicitDeny')
        if decision != 'allowed':
            missing.append(evaluation.get('EvalActionName', 'unknown'))
            if decision == 'explicitDeny':
                has_explicit_deny = True

    if not missing:
        return {'status': 'ready'}

    blocker: Dict[str, Any] = {
        'issue': 'insufficient_iam_permissions',
        'console_url': 'https://console.aws.amazon.com/iam/home',
        'wait_time': 'none',
        'is_paid': False,
        'missing_permissions': missing,
        'has_explicit_deny': has_explicit_deny,
    }
    if has_explicit_deny:
        blocker['action'] = f'Remove explicit deny policy for {", ".join(missing)}'
        blocker['message'] = (
            'An explicit deny overrides all allow policies. The deny statement must be removed.'
        )
    else:
        blocker['action'] = 'Attach AWSBillingReadOnlyAccess policy'
        blocker['suggested_policy_arn'] = 'arn:aws:iam::aws:policy/AWSBillingReadOnlyAccess'

    return {'status': 'blocked', 'blocker': blocker}


# --- Detection: Cost Explorer ---


def _latest_non_empty_period(results_by_time: List[Dict[str, Any]]) -> Optional[str]:
    """Find the End date of the most recent period with any spend.

    Args:
        results_by_time: The ``ResultsByTime`` list from a GetCostAndUsage response.

    Returns:
        The ``End`` date of the latest non-empty period, or None if all periods
        are empty.
    """
    for period in reversed(results_by_time):
        total = period.get('Total') or {}
        groups = period.get('Groups') or []
        # Any nonzero metric counts as data - including credits-only accounts
        # whose UnblendedCost is negative (``> 0`` would misclassify those as
        # still propagating).
        has_nonzero = False
        for metric in total.values():
            try:
                if float(metric.get('Amount', 0)) != 0:
                    has_nonzero = True
                    break
            except (TypeError, ValueError):
                pass
        if has_nonzero or groups:
            return period.get('TimePeriod', {}).get('End')
    return None


def check_cost_explorer(ce_client: Any, start_date: str, end_date: str) -> Dict[str, Any]:
    """Diagnose Cost Explorer enablement and data availability.

    Heuristic (see module docstring):

    - ``DataUnavailableException`` -> Cost Explorer not enabled (blocked).
    - ``AccessDeniedException`` whose message says the user is not enabled for
      Cost Explorer -> Cost Explorer not enabled (blocked). Real accounts return
      this shape (``"User not enabled for cost explorer access"``) rather than
      ``DataUnavailableException`` when CE has never been activated. IAM is
      verified first via SimulatePrincipalPolicy, so a true permission denial is
      already ruled out by the time this check runs; the message guard keeps an
      unrelated ``AccessDeniedException`` from being misread as not-enabled.
    - Success with at least one non-empty period -> ready (with data_freshness).
    - Success but every period is zero/empty -> enabled and propagating (pending).

    Args:
        ce_client: A boto3 Cost Explorer client.
        start_date: Probe window start in ``YYYY-MM-DD`` format.
        end_date: Probe window end in ``YYYY-MM-DD`` format.

    Returns:
        A normalized check result with status ``ready``, ``blocked``, or
        ``pending``.

    Raises:
        ClientError: For any AWS error other than the not-enabled signals above.
    """
    try:
        response = ce_client.get_cost_and_usage(
            TimePeriod={'Start': start_date, 'End': end_date},
            Granularity='DAILY',
            Metrics=['UnblendedCost'],
        )
    except ClientError as error:
        err = error.response.get('Error', {})
        code = err.get('Code', '')
        message = err.get('Message', '')
        not_enabled = code == 'DataUnavailableException' or (
            code == 'AccessDeniedException' and 'not enabled for cost explorer' in message.lower()
        )
        if not_enabled:
            return {
                'status': 'blocked',
                'blocker': {
                    'issue': 'cost_explorer_not_enabled',
                    'action': 'Enable Cost Explorer',
                    'console_url': (
                        'https://console.aws.amazon.com/cost-management/home#/cost-explorer'
                    ),
                    'wait_time': '24h',
                    'is_paid': False,
                },
            }
        raise

    freshness = _latest_non_empty_period(response.get('ResultsByTime', []))
    if freshness:
        return {'status': 'ready', 'data_freshness': freshness}

    return {
        'status': 'pending',
        'pending_reason': {
            'issue': 'cost_explorer_propagating',
            'message': (
                'Cost Explorer is enabled but no cost data is available yet. '
                'Data can take up to 24h to propagate after enablement.'
            ),
        },
    }


# --- Detection: cost allocation tags ---


def check_cost_allocation_tags(ce_client: Any) -> Dict[str, Any]:
    """Diagnose whether any cost allocation tags are activated.

    The ``tag_analysis`` intent is ready when at least one cost allocation tag is
    Active. Otherwise it is blocked, and the existing (inactive) tags are
    surfaced as alternatives so the agent can guide the user.

    The result is paginated: a single Active tag on any page makes the intent
    ready, so all pages must be read before concluding none are active.

    Cost allocation tags are managed only at the management (payer) account
    level, so ``list_cost_allocation_tags`` is denied outright on a linked /
    member account (``AccessDeniedException``: "Linked account doesn't have
    access to cost allocation tags"). That is a structural state, not a missing
    permission, so it is turned into an actionable blocker rather than surfacing
    a raw 403 - directing the user to run tag analysis from the management
    account.

    Args:
        ce_client: A boto3 Cost Explorer client.

    Returns:
        A normalized check result: ``{'status': 'ready'}`` or
        ``{'status': 'blocked', 'blocker': {...}}``.

    Raises:
        ClientError: For any AWS error other than the linked-account denial.
    """
    tags: List[Dict[str, Any]] = []
    next_token: Optional[str] = None
    while True:
        kwargs = {'NextToken': next_token} if next_token else {}
        try:
            response = ce_client.list_cost_allocation_tags(**kwargs)
        except ClientError as error:
            err = error.response.get('Error', {})
            code = err.get('Code', '')
            message = err.get('Message', '')
            if code == 'AccessDeniedException' and 'linked account' in message.lower():
                return {
                    'status': 'blocked',
                    'blocker': {
                        'issue': 'tags_not_available_in_linked_account',
                        'action': (
                            'Run tag analysis from the management (payer) account, or '
                            'activate cost allocation tags there'
                        ),
                        'console_url': 'https://console.aws.amazon.com/billing/home#/tags',
                        'wait_time': 'none',
                        'is_paid': False,
                        'message': (
                            'Cost allocation tags are managed at the management (payer) '
                            'account level and are not accessible from this linked account.'
                        ),
                    },
                }
            raise
        tags.extend(response.get('CostAllocationTags', []))
        next_token = response.get('NextToken')
        if not next_token:
            break

    active = [t for t in tags if t.get('Status') == 'Active']
    if active:
        return {'status': 'ready'}

    available = [
        {
            'key': t.get('TagKey'),
            'status': t.get('Status', 'Inactive'),
            'last_used': t.get('LastUpdatedDate') or t.get('LastUsedDate'),
        }
        for t in tags
    ]
    if available:
        message = (
            f'{len(available)} tags exist on resources but none are activated for cost allocation.'
        )
    else:
        message = 'No cost allocation tags exist on any resources in this account.'

    return {
        'status': 'blocked',
        'blocker': {
            'issue': 'tags_not_activated',
            'action': 'Activate cost allocation tags',
            'console_url': 'https://console.aws.amazon.com/billing/home#/tags',
            'wait_time': '24h',
            'is_paid': False,
            'available_tags': available,
            'message': message,
        },
    }


# --- Detection: Cost Optimization Hub ---


def check_cost_optimization_hub(coh_client: Any) -> Dict[str, Any]:
    """Diagnose Cost Optimization Hub enrollment for the optimization intent.

    Args:
        coh_client: A boto3 Cost Optimization Hub client.

    Returns:
        A normalized check result: ``{'status': 'ready'}`` or
        ``{'status': 'blocked', 'blocker': {...}}``.
    """
    items: List[Dict[str, Any]] = []
    next_token: Optional[str] = None
    while True:
        kwargs = {'nextToken': next_token} if next_token else {}
        response = coh_client.list_enrollment_statuses(**kwargs)
        items.extend(response.get('items') or response.get('Items') or [])
        next_token = response.get('nextToken') or response.get('NextToken')
        if not next_token:
            break

    is_active = any((i.get('status') or i.get('Status')) == 'Active' for i in items)

    if is_active:
        return {'status': 'ready'}

    return {
        'status': 'blocked',
        'blocker': {
            'issue': 'cost_optimization_hub_not_enrolled',
            'action': 'Enroll in Cost Optimization Hub',
            'console_url': 'https://console.aws.amazon.com/cost-optimization-hub/home',
            'wait_time': 'none',
            'is_paid': False,
        },
    }


# --- Router ---


def _assemble_blocked(
    account_id: str, intent: str, check: Dict[str, Any], now: datetime
) -> Dict[str, Any]:
    """Wrap a blocked check result into the full response envelope.

    Args:
        account_id: The AWS account being checked.
        intent: The intent being diagnosed.
        check: The blocked check result containing a ``blocker`` dict.
        now: The reference "now" timestamp for cache computation.

    Returns:
        The full ``blocked`` readiness response.
    """
    blocker = check['blocker']
    return {
        'account_id': account_id,
        'intent': intent,
        'status': 'blocked',
        'blocker': blocker,
        'after_resolution': {
            'status': 'ready',
            'capabilities': INTENT_CAPABILITIES[intent],
        },
        'cache': build_cache(blocker['issue'], now),
    }


def _assemble_pending(
    account_id: str, intent: str, check: Dict[str, Any], now: datetime
) -> Dict[str, Any]:
    """Wrap a pending check result into the full response envelope.

    Args:
        account_id: The AWS account being checked.
        intent: The intent being diagnosed.
        check: The pending check result containing a ``pending_reason`` dict.
        now: The reference "now" timestamp for cache computation.

    Returns:
        The full ``pending`` readiness response.
    """
    data_available_at = now + timedelta(seconds=CACHE_SECONDS['cost_explorer_propagating'])
    pending = {**check['pending_reason'], 'data_available_at': _iso(data_available_at)}
    return {
        'account_id': account_id,
        'intent': intent,
        'status': 'pending',
        'pending_reason': pending,
        'cache': build_cache('cost_explorer_propagating', now, valid_until=data_available_at),
    }


def diagnose_readiness(
    account_id: str,
    intent: str,
    clients: Dict[str, Any],
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Run the intent's prerequisite checks and assemble a readiness response.

    The first non-ready check short-circuits. If all checks pass, the response is
    ``ready`` with the intent's capabilities (and ``data_freshness`` from the
    Cost Explorer check).

    Args:
        account_id: AWS account being checked.
        intent: One of the supported intents.
        clients: Mapping with pre-created boto3 clients: ``sts``, ``iam``,
            ``ce``, and (for the optimization intent) ``coh``.
        now: Injectable clock for deterministic cache timestamps.

    Returns:
        The full readiness response envelope.

    Raises:
        ValueError: If ``intent`` is not supported, or a required client is
            missing from ``clients``.
    """
    now = now or _now()

    if intent not in INTENT_CHECKS:
        raise ValueError(
            f"Unsupported intent '{intent}'. Supported intents: {', '.join(sorted(INTENT_CHECKS))}"
        )

    # Each check maps to the client keys it needs; fail fast with a clear error
    # rather than a bare KeyError if the caller omits a required client.
    required_clients = {
        'iam': ('sts', 'iam'),
        'cost_explorer': ('ce',),
        'tags': ('ce',),
        'cost_optimization_hub': ('coh',),
    }
    for check_name in INTENT_CHECKS[intent]:
        for key in required_clients[check_name]:
            if key not in clients:
                raise ValueError(
                    f"Missing required client '{key}' for intent '{intent}' "
                    f"(check '{check_name}')."
                )

    ce_window = _ce_date_window(now)
    runners: Dict[str, Callable[[], Dict[str, Any]]] = {
        'iam': lambda: check_iam_permissions(clients['sts'], clients['iam'], intent),
        'cost_explorer': lambda: check_cost_explorer(
            clients['ce'], ce_window['Start'], ce_window['End']
        ),
        'tags': lambda: check_cost_allocation_tags(clients['ce']),
        'cost_optimization_hub': lambda: check_cost_optimization_hub(clients['coh']),
    }

    data_freshness: Optional[str] = None
    for check_name in INTENT_CHECKS[intent]:
        result = runners[check_name]()
        if result['status'] == 'blocked':
            return _assemble_blocked(account_id, intent, result, now)
        if result['status'] == 'pending':
            return _assemble_pending(account_id, intent, result, now)
        if check_name == 'cost_explorer':
            data_freshness = result.get('data_freshness')

    response: Dict[str, Any] = {
        'account_id': account_id,
        'intent': intent,
        'status': 'ready',
        'capabilities': INTENT_CAPABILITIES[intent],
        'cache': build_cache('ready', now),
    }
    if data_freshness:
        response['data_freshness'] = data_freshness
    return response
