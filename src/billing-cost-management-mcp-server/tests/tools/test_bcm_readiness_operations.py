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

These tests cover the 7 evaluation scenarios from the design (CE not enabled,
ready, propagating, IAM denied/explicit-deny, tags inactive/missing, COH not
enrolled), plus intent scoping and ARN normalization. They exercise the pure
detection logic against fake boto3 clients with a fixed clock - no AWS calls.
"""

import pytest
from awslabs.billing_cost_management_mcp_server.tools import bcm_readiness_operations as ops
from botocore.exceptions import ClientError
from datetime import datetime, timezone


NOW = datetime(2026, 5, 13, 10, 30, 0, tzinfo=timezone.utc)
ACCOUNT = '123456789012'


class FakeSTS:
    """Minimal STS client returning a configurable caller ARN."""

    def __init__(self, arn=f'arn:aws:sts::{ACCOUNT}:assumed-role/BCM-Test/lbragile-Isengard'):
        """Store the ARN that get_caller_identity should return."""
        self._arn = arn

    def get_caller_identity(self):
        """Return a fake caller identity."""
        return {'Account': ACCOUNT, 'Arn': self._arn}


class FakeIAM:
    """Fake IAM client returning one EvaluationResult per action."""

    def __init__(self, decisions):
        """Store a mapping of action name to eval decision."""
        self._decisions = decisions

    def simulate_principal_policy(self, PolicySourceArn, ActionNames):
        """Return simulated evaluation results for the requested actions."""
        return {
            'EvaluationResults': [
                {'EvalActionName': a, 'EvalDecision': self._decisions.get(a, 'allowed')}
                for a in ActionNames
            ]
        }


def _ce_error(code):
    """Build a ClientError for GetCostAndUsage with the given error code."""
    return ClientError({'Error': {'Code': code, 'Message': code}}, 'GetCostAndUsage')


class FakeCE:
    """Fake Cost Explorer client for cost-and-usage and tag listing."""

    def __init__(self, cau=None, cau_error=None, tags=None):
        """Configure the canned cost-and-usage response, error, and tags."""
        self._cau = cau
        self._cau_error = cau_error
        self._tags = tags or []

    def get_cost_and_usage(self, **kwargs):
        """Return the canned response or raise the configured error."""
        if self._cau_error is not None:
            raise self._cau_error
        return self._cau

    def list_cost_allocation_tags(self, **kwargs):
        """Return the configured cost allocation tags."""
        return {'CostAllocationTags': self._tags}


class FakeCOH:
    """Fake Cost Optimization Hub client for enrollment status."""

    def __init__(self, status):
        """Store the enrollment status to report."""
        self._status = status

    def list_enrollment_statuses(self, **kwargs):
        """Return a canned enrollment status list."""
        items = [{'status': self._status}] if self._status is not None else []
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
