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

"""Unit tests for the bcm_readiness_tools module.

These tests verify the MCP tool wrapper: intent validation, AWS client creation,
mapping of the diagnosis result into the standard success envelope, and error
handling. AWS clients are mocked - no real API calls are made.
"""

import fastmcp
import importlib
import pytest
from awslabs.billing_cost_management_mcp_server.tools.bcm_readiness_tools import (
    bcm_readiness_server,
)
from botocore.exceptions import ClientError
from fastmcp import Context
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch


def _reload_with_identity_decorator() -> Any:
    """Reload module with FastMCP.tool patched to return the original function."""
    from awslabs.billing_cost_management_mcp_server.tools import bcm_readiness_tools as mod

    def _identity_tool(self, *args, **kwargs):
        def _decorator(fn):
            return fn

        return _decorator

    with patch.object(fastmcp.FastMCP, 'tool', _identity_tool):
        importlib.reload(mod)
        return mod


@pytest.fixture
def mock_context():
    """Create a mock MCP context."""
    context = MagicMock(spec=Context)
    context.info = AsyncMock()
    context.error = AsyncMock()
    return context


def _ready_clients():
    """Build mocked sts/iam/ce/coh clients that produce a ready basic result."""
    sts = MagicMock()
    sts.get_caller_identity.return_value = {
        'Account': '123456789012',
        'Arn': 'arn:aws:sts::123456789012:assumed-role/BCM-Test/session',
    }

    iam = MagicMock()
    iam.simulate_principal_policy.return_value = {
        'EvaluationResults': [
            {'EvalActionName': a, 'EvalDecision': 'allowed'}
            for a in ('ce:GetCostAndUsage', 'ce:GetCostForecast', 'ce:GetDimensionValues')
        ]
    }

    ce = MagicMock()
    ce.get_cost_and_usage.return_value = {
        'ResultsByTime': [
            {
                'TimePeriod': {'Start': '2026-05-10', 'End': '2026-05-11'},
                'Total': {'UnblendedCost': {'Amount': '805.49', 'Unit': 'USD'}},
                'Groups': [],
            }
        ]
    }
    return {'sts': sts, 'iam': iam, 'ce': ce}


def test_bcm_readiness_server_initialization():
    """Test that the bcm_readiness_server is properly initialized."""
    assert bcm_readiness_server.name == 'bcm-readiness-tools'
    assert bcm_readiness_server.instructions is not None


@pytest.mark.asyncio
class TestCheckBcmReadiness:
    """Tests for the check_bcm_readiness tool function."""

    async def test_invalid_intent_returns_validation_error(self, mock_context):
        """An unsupported intent returns a structured validation error."""
        mod = _reload_with_identity_decorator()

        result = await mod.check_bcm_readiness(
            mock_context, account_id='123456789012', intent='bogus'
        )

        assert result['status'] == 'error'
        assert result['data']['error_type'] == 'validation_error'

    async def test_ready_basic_intent(self, mock_context):
        """A fully configured account returns success with a ready result."""
        mod = _reload_with_identity_decorator()
        clients = _ready_clients()

        def _fake_create_client(service_name, region_name=None):
            return clients[{'sts': 'sts', 'iam': 'iam', 'ce': 'ce'}[service_name]]

        with patch.object(mod, 'create_aws_client', side_effect=_fake_create_client):
            result = await mod.check_bcm_readiness(mock_context, account_id='123456789012')

        assert result['status'] == 'success'
        assert result['data']['status'] == 'ready'
        assert result['data']['intent'] == 'basic_cost_visibility'

    async def test_default_intent_applied(self, mock_context):
        """Omitting intent defaults to basic_cost_visibility."""
        mod = _reload_with_identity_decorator()
        clients = _ready_clients()

        with patch.object(
            mod, 'create_aws_client', side_effect=lambda s, region_name=None: clients[s]
        ):
            result = await mod.check_bcm_readiness(
                mock_context, account_id='123456789012', intent=None
            )

        assert result['data']['intent'] == 'basic_cost_visibility'

    async def test_client_creation_failure(self, mock_context):
        """A client creation failure returns a structured client_creation_error."""
        mod = _reload_with_identity_decorator()

        with patch.object(mod, 'create_aws_client', side_effect=RuntimeError('boom')):
            result = await mod.check_bcm_readiness(mock_context, account_id='123456789012')

        assert result['status'] == 'error'
        assert result['data']['error_type'] == 'client_creation_error'

    async def test_client_error_handled(self, mock_context):
        """An unexpected ClientError during diagnosis is handled, not raised."""
        mod = _reload_with_identity_decorator()
        clients = _ready_clients()
        clients['ce'].get_cost_and_usage.side_effect = ClientError(
            {'Error': {'Code': 'ThrottlingException', 'Message': 'slow down'}},
            'GetCostAndUsage',
        )

        with patch.object(
            mod, 'create_aws_client', side_effect=lambda s, region_name=None: clients[s]
        ):
            result = await mod.check_bcm_readiness(mock_context, account_id='123456789012')

        assert result['status'] == 'error'
        assert result['error_type'] == 'ThrottlingException'

    async def test_optimization_intent_creates_coh_client(self, mock_context):
        """The optimization intent additionally creates a cost-optimization-hub client."""
        mod = _reload_with_identity_decorator()
        clients = _ready_clients()
        coh = MagicMock()
        coh.list_enrollment_statuses.return_value = {'items': [{'status': 'Active'}]}
        clients['coh'] = coh
        requested = []

        def _fake_create_client(service_name, region_name=None):
            requested.append(service_name)
            return clients[{'cost-optimization-hub': 'coh'}.get(service_name, service_name)]

        with patch.object(mod, 'create_aws_client', side_effect=_fake_create_client):
            result = await mod.check_bcm_readiness(
                mock_context, account_id='123456789012', intent='optimization'
            )

        assert 'cost-optimization-hub' in requested
        assert result['status'] == 'success'
        assert result['data']['status'] == 'ready'

    async def test_unexpected_exception_handled(self, mock_context):
        """A non-ClientError raised during diagnosis is handled, not propagated."""
        mod = _reload_with_identity_decorator()
        clients = _ready_clients()
        clients['ce'].get_cost_and_usage.side_effect = RuntimeError('unexpected')

        with patch.object(
            mod, 'create_aws_client', side_effect=lambda s, region_name=None: clients[s]
        ):
            result = await mod.check_bcm_readiness(mock_context, account_id='123456789012')

        assert result['status'] == 'error'
