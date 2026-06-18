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

"""Unit tests for the bcm_readiness_operations module.

These tests cover the evaluation scenarios from the design (CE not enabled,
ready, propagating, IAM denied/explicit-deny/cannot-verify, tags
inactive/missing, COH not enrolled), plus intent scoping and ARN normalization.
They exercise the pure detection logic against fake boto3 clients with a fixed
clock - no AWS calls. See tests/fixtures/bcm_readiness/README.md for the
real-account capture matrix behind the replay tests.
"""

import pytest
from awslabs.billing_cost_management_mcp_server.tools import bcm_readiness_operations as ops
from botocore.exceptions import ClientError
from datetime import datetime, timezone


NOW = datetime(2026, 5, 13, 10, 30, 0, tzinfo=timezone.utc)
ACCOUNT = '123456789012'


class FakeSTS:
    """Minimal STS client returning a configurable caller ARN."""

    def __init__(self, arn=f'arn:aws:sts::{ACCOUNT}:assumed-role/TestRole/test-session'):
        """Store the ARN that get_caller_identity should return."""
        self._arn = arn

    def get_caller_identity(self):
        """Return a fake caller identity."""
        return {'Account': ACCOUNT, 'Arn': self._arn}


class FakeIAM:
    """Fake IAM client returning one EvaluationResult per action."""

    def __init__(self, decisions, simulate_error=None):
        """Store a mapping of action name to eval decision (or an error to raise)."""
        self._decisions = decisions
        self._simulate_error = simulate_error

    def simulate_principal_policy(self, PolicySourceArn, ActionNames):
        """Return simulated evaluation results, or raise the configured error."""
        if self._simulate_error is not None:
            raise self._simulate_error
        return {
            'EvaluationResults': [
                {'EvalActionName': a, 'EvalDecision': self._decisions.get(a, 'allowed')}
                for a in ActionNames
            ]
        }


def _iam_error(code):
    """Build a ClientError for SimulatePrincipalPolicy with the given error code."""
    return ClientError({'Error': {'Code': code, 'Message': code}}, 'SimulatePrincipalPolicy')


def _ce_error(code, message=None):
    """Build a ClientError for GetCostAndUsage with the given error code/message."""
    return ClientError({'Error': {'Code': code, 'Message': message or code}}, 'GetCostAndUsage')


def _tags_error(code, message=None):
    """Build a ClientError for ListCostAllocationTags with the given code/message."""
    return ClientError(
        {'Error': {'Code': code, 'Message': message or code}}, 'ListCostAllocationTags'
    )


class FakeCE:
    """Fake Cost Explorer client for cost-and-usage and tag listing.

    ``tags`` may be a flat list (single page) or a list of lists (one inner list
    per page), in which case ``list_cost_allocation_tags`` paginates via
    NextToken so pagination handling can be exercised.
    """

    def __init__(self, cau=None, cau_error=None, tags=None, tags_error=None):
        """Configure the canned cost-and-usage response, error, and tags."""
        self._cau = cau
        self._cau_error = cau_error
        self._tags_error = tags_error
        # Normalize to a list of pages.
        if tags and tags and isinstance(tags[0], list):
            self._tag_pages = tags
        else:
            self._tag_pages = [tags or []]

    def get_cost_and_usage(self, **kwargs):
        """Return the canned response or raise the configured error."""
        if self._cau_error is not None:
            raise self._cau_error
        return self._cau

    def list_cost_allocation_tags(self, **kwargs):
        """Return one page of tags, advancing by NextToken."""
        if self._tags_error is not None:
            raise self._tags_error
        idx = int(kwargs.get('NextToken', '0'))
        page = self._tag_pages[idx]
        result = {'CostAllocationTags': page}
        if idx + 1 < len(self._tag_pages):
            result['NextToken'] = str(idx + 1)
        return result


class FakeCOH:
    """Fake Cost Optimization Hub client for enrollment status.

    ``status`` may be a single value (one item) or a list of statuses (one item
    each, on a single page).
    """

    def __init__(self, status):
        """Store the enrollment status(es) to report."""
        self._status = status

    def list_enrollment_statuses(self, **kwargs):
        """Return a canned enrollment status list."""
        if self._status is None:
            items = []
        elif isinstance(self._status, list):
            items = [{'status': s} for s in self._status]
        else:
            items = [{'status': self._status}]
        return {'items': items}


def _results_by_time(amount):
    """Build a one-period GetCostAndUsage response with the given amount."""
    return {
        'ResultsByTime': [
            {
                'TimePeriod': {'Start': '2026-05-10', 'End': '2026-05-11'},
                'Total': {'UnblendedCost': {'Amount': str(amount), 'Unit': 'USD'}},
                'Groups': [],
            }
        ]
    }


def _all_allowed(intent):
    """Return a decisions map allowing every action the intent requires."""
    return dict.fromkeys(ops.INTENT_IAM_ACTIONS[intent], 'allowed')


def _clients(**overrides):
    """Build a default ready-state client set, with optional overrides."""
    base = {
        'sts': FakeSTS(),
        'iam': FakeIAM(_all_allowed(ops.INTENT_BASIC)),
        'ce': FakeCE(cau=_results_by_time('805.49')),
    }
    base.update(overrides)
    return base


def test_basic_ready():
    """CE enabled with data -> ready, with capabilities, freshness, 1h cache."""
    result = ops.diagnose_readiness(ACCOUNT, ops.INTENT_BASIC, _clients(), now=NOW)
    assert result['status'] == 'ready'
    assert 'GetCostAndUsage' in result['capabilities']
    assert result['data_freshness'] == '2026-05-11'
    assert result['cache']['valid_until'] == '2026-05-13T11:30:00Z'


def test_basic_ce_not_enabled():
    """DataUnavailableException -> blocked on cost_explorer_not_enabled, 24h cache."""
    clients = _clients(ce=FakeCE(cau_error=_ce_error('DataUnavailableException')))
    result = ops.diagnose_readiness(ACCOUNT, ops.INTENT_BASIC, clients, now=NOW)
    assert result['status'] == 'blocked'
    assert result['blocker']['issue'] == 'cost_explorer_not_enabled'
    assert result['blocker']['is_paid'] is False
    assert result['after_resolution']['status'] == 'ready'
    assert result['cache']['valid_until'] == '2026-05-14T10:30:00Z'


def test_basic_ce_not_enabled_access_denied_shape():
    """AccessDeniedException 'not enabled for cost explorer' -> not-enabled blocker.

    Real accounts return this shape instead of DataUnavailableException when CE
    has never been activated (observed during fixture capture).
    """
    clients = _clients(
        ce=FakeCE(
            cau_error=_ce_error(
                'AccessDeniedException', 'User not enabled for cost explorer access'
            )
        )
    )
    result = ops.diagnose_readiness(ACCOUNT, ops.INTENT_BASIC, clients, now=NOW)
    assert result['status'] == 'blocked'
    assert result['blocker']['issue'] == 'cost_explorer_not_enabled'


def test_cost_explorer_reraises_unrelated_access_denied():
    """An AccessDeniedException without the not-enabled message still propagates."""
    clients = _clients(
        ce=FakeCE(cau_error=_ce_error('AccessDeniedException', 'Some other denial'))
    )
    with pytest.raises(ClientError):
        ops.diagnose_readiness(ACCOUNT, ops.INTENT_BASIC, clients, now=NOW)


def test_basic_ce_propagating():
    """CE enabled but all-zero -> pending with data_available_at."""
    clients = _clients(ce=FakeCE(cau=_results_by_time('0')))
    result = ops.diagnose_readiness(ACCOUNT, ops.INTENT_BASIC, clients, now=NOW)
    assert result['status'] == 'pending'
    assert result['pending_reason']['issue'] == 'cost_explorer_propagating'
    assert result['pending_reason']['data_available_at'] == '2026-05-14T10:30:00Z'


def test_basic_iam_missing_permission():
    """Missing CE permission -> blocked with suggested policy and 5-min cache."""
    decisions = _all_allowed(ops.INTENT_BASIC)
    decisions['ce:GetCostForecast'] = 'implicitDeny'
    clients = _clients(iam=FakeIAM(decisions))
    result = ops.diagnose_readiness(ACCOUNT, ops.INTENT_BASIC, clients, now=NOW)
    assert result['status'] == 'blocked'
    assert result['blocker']['issue'] == 'insufficient_iam_permissions'
    assert result['blocker']['missing_permissions'] == ['ce:GetCostForecast']
    assert result['blocker']['has_explicit_deny'] is False
    assert result['blocker']['suggested_policy_arn'].endswith('AWSBillingReadOnlyAccess')
    assert result['cache']['valid_until'] == '2026-05-13T10:35:00Z'


def test_basic_iam_explicit_deny():
    """Explicit deny -> blocked, action says remove deny, no policy suggestion."""
    decisions = _all_allowed(ops.INTENT_BASIC)
    decisions['ce:GetCostForecast'] = 'explicitDeny'
    clients = _clients(iam=FakeIAM(decisions))
    result = ops.diagnose_readiness(ACCOUNT, ops.INTENT_BASIC, clients, now=NOW)
    assert result['status'] == 'blocked'
    assert result['blocker']['has_explicit_deny'] is True
    assert 'Remove explicit deny' in result['blocker']['action']
    assert 'suggested_policy_arn' not in result['blocker']


def test_basic_iam_simulate_access_denied():
    """AccessDenied on SimulatePrincipalPolicy -> blocked, not a raw error."""
    clients = _clients(iam=FakeIAM({}, simulate_error=_iam_error('AccessDenied')))
    result = ops.diagnose_readiness(ACCOUNT, ops.INTENT_BASIC, clients, now=NOW)
    assert result['status'] == 'blocked'
    assert result['blocker']['issue'] == 'cannot_verify_iam_permissions'
    assert result['blocker']['missing_permissions'] == ['iam:SimulatePrincipalPolicy']
    assert result['blocker']['suggested_policy_arn'].endswith('AWSBillingReadOnlyAccess')


def test_iam_reraises_unexpected_clienterror():
    """A non-AccessDenied ClientError from SimulatePrincipalPolicy propagates out."""
    clients = _clients(iam=FakeIAM({}, simulate_error=_iam_error('ThrottlingException')))
    with pytest.raises(ClientError):
        ops.diagnose_readiness(ACCOUNT, ops.INTENT_BASIC, clients, now=NOW)


def test_tag_analysis_tags_inactive():
    """Tags exist but inactive -> blocked, surfaces available tags."""
    tags = [
        {'TagKey': 'Name', 'Status': 'Inactive', 'LastUpdatedDate': '2026-05-01'},
        {'TagKey': 'Application', 'Status': 'Inactive', 'LastUpdatedDate': '2023-10-01'},
    ]
    clients = _clients(
        iam=FakeIAM(_all_allowed(ops.INTENT_TAG)),
        ce=FakeCE(cau=_results_by_time('805.49'), tags=tags),
    )
    result = ops.diagnose_readiness(ACCOUNT, ops.INTENT_TAG, clients, now=NOW)
    assert result['status'] == 'blocked'
    assert result['blocker']['issue'] == 'tags_not_activated'
    assert len(result['blocker']['available_tags']) == 2
    assert result['blocker']['available_tags'][0]['key'] == 'Name'


def test_tag_analysis_no_tags_exist():
    """No tags at all -> blocked with the 'no tags exist' message."""
    clients = _clients(
        iam=FakeIAM(_all_allowed(ops.INTENT_TAG)),
        ce=FakeCE(cau=_results_by_time('805.49'), tags=[]),
    )
    result = ops.diagnose_readiness(ACCOUNT, ops.INTENT_TAG, clients, now=NOW)
    assert result['status'] == 'blocked'
    assert result['blocker']['issue'] == 'tags_not_activated'
    assert result['blocker']['available_tags'] == []
    assert 'No cost allocation tags exist' in result['blocker']['message']


def test_tag_analysis_ready_when_tag_active():
    """At least one active tag -> ready with TAG GroupBy capability."""
    tags = [{'TagKey': 'CostCenter', 'Status': 'Active'}]
    clients = _clients(
        iam=FakeIAM(_all_allowed(ops.INTENT_TAG)),
        ce=FakeCE(cau=_results_by_time('805.49'), tags=tags),
    )
    result = ops.diagnose_readiness(ACCOUNT, ops.INTENT_TAG, clients, now=NOW)
    assert result['status'] == 'ready'
    assert result['capabilities'] == ['GetCostAndUsage with TAG GroupBy']


def test_tag_analysis_active_tag_on_later_page():
    """An Active tag on a later page -> ready (pagination is followed)."""
    pages = [
        [{'TagKey': 'Name', 'Status': 'Inactive'}],
        [{'TagKey': 'CostCenter', 'Status': 'Active'}],
    ]
    clients = _clients(
        iam=FakeIAM(_all_allowed(ops.INTENT_TAG)),
        ce=FakeCE(cau=_results_by_time('805.49'), tags=pages),
    )
    result = ops.diagnose_readiness(ACCOUNT, ops.INTENT_TAG, clients, now=NOW)
    assert result['status'] == 'ready'


def test_tag_analysis_inactive_across_pages_aggregates_available():
    """All-inactive across pages -> blocked, available_tags spans every page."""
    pages = [
        [{'TagKey': 'Name', 'Status': 'Inactive'}],
        [{'TagKey': 'Application', 'Status': 'Inactive'}],
    ]
    clients = _clients(
        iam=FakeIAM(_all_allowed(ops.INTENT_TAG)),
        ce=FakeCE(cau=_results_by_time('805.49'), tags=pages),
    )
    result = ops.diagnose_readiness(ACCOUNT, ops.INTENT_TAG, clients, now=NOW)
    assert result['status'] == 'blocked'
    assert {t['key'] for t in result['blocker']['available_tags']} == {'Name', 'Application'}


def test_tag_analysis_linked_account_blocked_not_raised():
    """Linked-account AccessDenied on tag listing -> actionable blocker, not a raw error.

    Cost allocation tags are managed at the management account level, so listing
    them is denied outright on a member account (observed during fixture capture).
    """
    clients = _clients(
        iam=FakeIAM(_all_allowed(ops.INTENT_TAG)),
        ce=FakeCE(
            cau=_results_by_time('805.49'),
            tags_error=_tags_error(
                'AccessDeniedException',
                "Failed to list Cost Allocation Tags: Linked account doesn't have "
                'access to cost allocation tags.',
            ),
        ),
    )
    result = ops.diagnose_readiness(ACCOUNT, ops.INTENT_TAG, clients, now=NOW)
    assert result['status'] == 'blocked'
    assert result['blocker']['issue'] == 'tags_not_available_in_linked_account'
    assert result['blocker']['is_paid'] is False


def test_tag_analysis_reraises_unrelated_access_denied():
    """An AccessDenied on tag listing without the linked-account hint propagates."""
    clients = _clients(
        iam=FakeIAM(_all_allowed(ops.INTENT_TAG)),
        ce=FakeCE(
            cau=_results_by_time('805.49'),
            tags_error=_tags_error('AccessDeniedException', 'Some unrelated denial'),
        ),
    )
    with pytest.raises(ClientError):
        ops.diagnose_readiness(ACCOUNT, ops.INTENT_TAG, clients, now=NOW)


def test_optimization_coh_not_enrolled():
    """COH not enrolled -> blocked, immediate wait time, 5-min cache."""
    clients = _clients(
        iam=FakeIAM(_all_allowed(ops.INTENT_OPTIMIZATION)),
        coh=FakeCOH(status='Inactive'),
    )
    result = ops.diagnose_readiness(ACCOUNT, ops.INTENT_OPTIMIZATION, clients, now=NOW)
    assert result['status'] == 'blocked'
    assert result['blocker']['issue'] == 'cost_optimization_hub_not_enrolled'
    assert result['blocker']['wait_time'] == 'none'
    assert result['cache']['valid_until'] == '2026-05-13T10:35:00Z'


def test_optimization_ready():
    """COH active -> ready with optimization capabilities."""
    clients = _clients(
        iam=FakeIAM(_all_allowed(ops.INTENT_OPTIMIZATION)),
        coh=FakeCOH(status='Active'),
    )
    result = ops.diagnose_readiness(ACCOUNT, ops.INTENT_OPTIMIZATION, clients, now=NOW)
    assert result['status'] == 'ready'
    assert 'GetRecommendations' in result['capabilities']


def test_optimization_ready_when_active_not_first_item():
    """Any Active enrollment item -> ready, even if it is not the first."""
    clients = _clients(
        iam=FakeIAM(_all_allowed(ops.INTENT_OPTIMIZATION)),
        coh=FakeCOH(status=['Inactive', 'Active']),
    )
    result = ops.diagnose_readiness(ACCOUNT, ops.INTENT_OPTIMIZATION, clients, now=NOW)
    assert result['status'] == 'ready'


def test_optimization_missing_coh_client_raises_valueerror():
    """Omitting the required coh client raises a clear ValueError, not KeyError."""
    clients = _clients(iam=FakeIAM(_all_allowed(ops.INTENT_OPTIMIZATION)))
    with pytest.raises(ValueError, match="Missing required client 'coh'"):
        ops.diagnose_readiness(ACCOUNT, ops.INTENT_OPTIMIZATION, clients, now=NOW)


def test_unsupported_intent_raises():
    """An unknown intent raises ValueError."""
    with pytest.raises(ValueError, match='Unsupported intent'):
        ops.diagnose_readiness(ACCOUNT, 'bogus_intent', _clients(), now=NOW)


def test_basic_intent_does_not_check_tags_or_coh():
    """Basic intent is ready without tags and without a COH client present."""
    clients = _clients(ce=FakeCE(cau=_results_by_time('805.49'), tags=[]))
    result = ops.diagnose_readiness(ACCOUNT, ops.INTENT_BASIC, clients, now=NOW)
    assert result['status'] == 'ready'


def test_blocker_short_circuits_on_first_failure():
    """IAM is checked before CE, so an IAM failure is reported first."""
    decisions = _all_allowed(ops.INTENT_BASIC)
    decisions['ce:GetCostAndUsage'] = 'implicitDeny'
    clients = _clients(
        iam=FakeIAM(decisions),
        ce=FakeCE(cau_error=_ce_error('DataUnavailableException')),
    )
    result = ops.diagnose_readiness(ACCOUNT, ops.INTENT_BASIC, clients, now=NOW)
    assert result['blocker']['issue'] == 'insufficient_iam_permissions'


def test_credits_only_account_is_ready_not_pending():
    """A credits-only (negative) period counts as data -> ready, not pending."""
    resp = _results_by_time('-50.00')
    clients = _clients(ce=FakeCE(cau=resp))
    result = ops.diagnose_readiness(ACCOUNT, ops.INTENT_BASIC, clients, now=NOW)
    assert result['status'] == 'ready'
    assert result['data_freshness'] == '2026-05-11'


def test_latest_non_empty_period_picks_most_recent_with_data():
    """Freshness scan returns the End of the latest non-empty period."""
    results = [
        {
            'TimePeriod': {'Start': '2026-05-08', 'End': '2026-05-09'},
            'Total': {'UnblendedCost': {'Amount': '12.00', 'Unit': 'USD'}},
            'Groups': [],
        },
        {
            'TimePeriod': {'Start': '2026-05-09', 'End': '2026-05-10'},
            'Total': {'UnblendedCost': {'Amount': '0', 'Unit': 'USD'}},
            'Groups': [],
        },
    ]
    assert ops._latest_non_empty_period(results) == '2026-05-09'


def test_latest_non_empty_period_counts_groups_with_zero_total():
    """A period with groups but a zero Total still counts as non-empty."""
    results = [
        {
            'TimePeriod': {'Start': '2026-05-10', 'End': '2026-05-11'},
            'Total': {},
            'Groups': [{'Keys': ['svc'], 'Metrics': {}}],
        }
    ]
    assert ops._latest_non_empty_period(results) == '2026-05-11'


def test_latest_non_empty_period_all_empty_returns_none():
    """All-empty periods -> None (drives the propagating/pending verdict)."""
    assert ops._latest_non_empty_period(_results_by_time('0')['ResultsByTime']) is None


def test_ready_without_freshness_when_freshness_unavailable():
    """check_cost_explorer returning ready without data_freshness omits the field."""
    from unittest.mock import patch

    with patch.object(ops, 'check_cost_explorer', return_value={'status': 'ready'}):
        result = ops.diagnose_readiness(ACCOUNT, ops.INTENT_BASIC, _clients(), now=NOW)
    assert result['status'] == 'ready'
    assert 'data_freshness' not in result


def test_assumed_role_arn_normalized_to_role():
    """An STS assumed-role ARN is converted to its IAM role ARN."""
    arn = f'arn:aws:sts::{ACCOUNT}:assumed-role/MyRole/session-123'
    assert ops._principal_arn_for_simulation(arn) == f'arn:aws:iam::{ACCOUNT}:role/MyRole'


def test_non_assumed_role_arn_passed_through():
    """A non assumed-role ARN is returned unchanged."""
    arn = f'arn:aws:iam::{ACCOUNT}:user/alice'
    assert ops._principal_arn_for_simulation(arn) == arn


def test_cost_explorer_reraises_unexpected_clienterror():
    """A non-DataUnavailable ClientError from CE propagates out."""
    clients = _clients(ce=FakeCE(cau_error=_ce_error('ThrottlingException')))
    with pytest.raises(ClientError):
        ops.diagnose_readiness(ACCOUNT, ops.INTENT_BASIC, clients, now=NOW)
