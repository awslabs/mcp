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

"""Tests for the consolidated engagement management tool."""

import inspect
import json
import pytest
from awslabs.aws_transform_mcp_server.tools.engagement import (
    MANAGE_ENGAGEMENT_DESCRIPTION,
    EngagementAction,
    EngagementHandler,
)
from tests.service_model_validation import validate_request
from types import SimpleNamespace
from typing import get_args
from unittest.mock import AsyncMock, MagicMock, patch


_MOD = 'awslabs.aws_transform_mcp_server.tools.engagement'
_VALID_TENANT_ID = 'tenant2'
_VALID_WORKSPACE_ID = '00000000-0000-0000-0000-000000000001'


def _parse(result: dict) -> dict:
    return json.loads(result['content'][0]['text'])


@pytest.fixture
def handler(mock_mcp):
    return EngagementHandler(mock_mcp)


@pytest.fixture
def ctx(mock_context):
    return mock_context


class TestManageEngagement:
    """Tests for manage_engagement validation and API dispatch."""

    def test_restricted_actions_and_fields_are_not_exposed(self):
        assert 'terminate' not in get_args(EngagementAction)
        assert 'update_workspace' not in get_args(EngagementAction)
        assert (
            'partnerTenantId'
            not in inspect.signature(EngagementHandler.manage_engagement).parameters
        )

    def test_remove_tenant_description_matches_supported_scope(self):
        assert (
            'Withdraw a pending partner invitation. Only the customer can do this.'
            in MANAGE_ENGAGEMENT_DESCRIPTION
        )
        assert (
            'Removing an accepted partner requires AWS Support.' in MANAGE_ENGAGEMENT_DESCRIPTION
        )

    def test_workspace_description_warns_about_jobs(self):
        description = ' '.join(MANAGE_ENGAGEMENT_DESCRIPTION.split())
        assert 'A workspace with jobs cannot later be removed from the engagement.' in description
        assert 'Remove a workspace that has no jobs.' in description

    @pytest.mark.asyncio
    @patch(f'{_MOD}.is_fes_available', return_value=False)
    async def test_not_configured(self, _, handler, ctx):
        result = await handler.manage_engagement(
            ctx,
            action='create',
            name='Migration',
            description='Migration engagement',
            tenantType='CUSTOMER',
        )
        assert _parse(result)['error']['code'] == 'NOT_CONFIGURED'

    @pytest.mark.asyncio
    @patch(f'{_MOD}.call_transform_api', new_callable=AsyncMock)
    @patch(f'{_MOD}.is_fes_available', return_value=False)
    async def test_validates_partner_metadata_before_connection_check(
        self, _, mock_fes, handler, ctx
    ):
        result = await handler.manage_engagement(
            ctx,
            action='add_tenant',
            engagementId='e-1',
            targetTenantId='t-2',
            tenantType='CUSTOMER',
            description='Customer invitation',
            customerConsent='GRANTED',
            partnerIntent='PERFORM_ASSESSMENT_AND_MIGRATION',
        )

        parsed = _parse(result)
        assert parsed['error']['code'] == 'VALIDATION_ERROR'
        assert 'tenantType="PARTNER"' in parsed['error']['message']
        mock_fes.assert_not_awaited()

    @pytest.mark.asyncio
    @patch(f'{_MOD}.call_transform_api', new_callable=AsyncMock)
    @patch(f'{_MOD}.is_fes_available', return_value=True)
    async def test_add_partner_tenant_accepts_elicited_customer_consent(
        self, _, mock_fes, handler, ctx
    ):
        ctx.session.check_client_capability = MagicMock(return_value=True)
        ctx.elicit = AsyncMock(
            return_value=SimpleNamespace(
                action='accept',
                data=SimpleNamespace(confirm=True),
            )
        )
        mock_fes.return_value = {'ok': True}

        result = await handler.manage_engagement(
            ctx,
            action='add_tenant',
            engagementId='e-1',
            targetTenantId='t-2',
            tenantType='PARTNER',
            description='Delivery partner',
            customerConsent='GRANTED',
            partnerIntent='PERFORM_ASSESSMENT_AND_MIGRATION',
        )

        assert _parse(result)['success'] is True
        ctx.elicit.assert_awaited_once()
        mock_fes.assert_awaited_once()

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        'action,confirmed',
        [('decline', False), ('cancel', False), ('accept', False)],
    )
    @patch(f'{_MOD}.call_transform_api', new_callable=AsyncMock)
    @patch(f'{_MOD}.is_fes_available', return_value=True)
    async def test_add_partner_tenant_does_not_mutate_when_consent_not_granted(
        self, _, mock_fes, action, confirmed, handler, ctx
    ):
        ctx.session.check_client_capability = MagicMock(return_value=True)
        ctx.elicit = AsyncMock(
            return_value=SimpleNamespace(
                action=action,
                data=SimpleNamespace(confirm=confirmed),
            )
        )

        result = await handler.manage_engagement(
            ctx,
            action='add_tenant',
            engagementId='e-1',
            targetTenantId='t-2',
            tenantType='PARTNER',
            description='Delivery partner',
            customerConsent='GRANTED',
            partnerIntent='PERFORM_ASSESSMENT_AND_MIGRATION',
        )

        parsed = _parse(result)
        assert parsed['error']['code'] == 'CONSENT_NOT_GRANTED'
        mock_fes.assert_not_awaited()

    @pytest.mark.asyncio
    @patch(f'{_MOD}.call_transform_api', new_callable=AsyncMock)
    @patch(f'{_MOD}.is_fes_available', return_value=True)
    async def test_add_partner_tenant_requires_confirm_when_elicitation_is_unavailable(
        self, _, mock_fes, handler, ctx
    ):
        ctx.session.check_client_capability = MagicMock(return_value=False)

        result = await handler.manage_engagement(
            ctx,
            action='add_tenant',
            engagementId='e-1',
            targetTenantId='t-2',
            tenantType='PARTNER',
            description='Delivery partner',
            customerConsent='GRANTED',
            partnerIntent='PERFORM_ASSESSMENT_AND_MIGRATION',
        )

        parsed = _parse(result)
        assert parsed['error']['code'] == 'CONSENT_CONFIRMATION_REQUIRED'
        assert 'confirm=true' in parsed['error']['suggestedAction']
        ctx.elicit.assert_not_awaited()
        mock_fes.assert_not_awaited()

    @pytest.mark.asyncio
    @patch(f'{_MOD}.call_transform_api', new_callable=AsyncMock)
    @patch(f'{_MOD}.is_fes_available', return_value=True)
    async def test_add_partner_tenant_requires_confirm_when_capability_check_fails(
        self, _, mock_fes, handler, ctx
    ):
        ctx.session.check_client_capability = MagicMock(
            side_effect=RuntimeError('capability check unavailable')
        )

        result = await handler.manage_engagement(
            ctx,
            action='add_tenant',
            engagementId='e-1',
            targetTenantId='t-2',
            tenantType='PARTNER',
            description='Delivery partner',
            customerConsent='GRANTED',
            partnerIntent='PERFORM_ASSESSMENT_AND_MIGRATION',
        )

        parsed = _parse(result)
        assert parsed['error']['code'] == 'CONSENT_CONFIRMATION_REQUIRED'
        assert 'confirm=true' in parsed['error']['suggestedAction']
        ctx.elicit.assert_not_awaited()
        mock_fes.assert_not_awaited()

    @pytest.mark.asyncio
    @patch(f'{_MOD}.call_transform_api', new_callable=AsyncMock)
    @patch(f'{_MOD}.is_fes_available', return_value=True)
    async def test_add_partner_tenant_falls_back_when_elicitation_fails(
        self, _, mock_fes, handler, ctx
    ):
        ctx.session.check_client_capability = MagicMock(return_value=True)
        ctx.elicit = AsyncMock(side_effect=RuntimeError('elicitation unavailable'))

        result = await handler.manage_engagement(
            ctx,
            action='add_tenant',
            engagementId='e-1',
            targetTenantId='t-2',
            tenantType='PARTNER',
            description='Delivery partner',
            customerConsent='GRANTED',
            partnerIntent='PERFORM_ASSESSMENT_AND_MIGRATION',
        )

        parsed = _parse(result)
        assert parsed['error']['code'] == 'CONSENT_CONFIRMATION_REQUIRED'
        assert 'confirm=true' in parsed['error']['suggestedAction']
        mock_fes.assert_not_awaited()

    @pytest.mark.asyncio
    @patch(f'{_MOD}.call_transform_api', new_callable=AsyncMock)
    @patch(f'{_MOD}.is_fes_available', return_value=True)
    async def test_add_partner_tenant_confirm_true_bypasses_elicitation(
        self, _, mock_fes, handler, ctx
    ):
        mock_fes.return_value = {'ok': True}

        result = await handler.manage_engagement(
            ctx,
            action='add_tenant',
            engagementId='e-1',
            targetTenantId='t-2',
            tenantType='PARTNER',
            description='Delivery partner',
            customerConsent='GRANTED',
            partnerIntent='PERFORM_ASSESSMENT_AND_MIGRATION',
            confirm=True,
        )

        assert _parse(result)['success'] is True
        ctx.elicit.assert_not_awaited()
        mock_fes.assert_awaited_once()

    @pytest.mark.asyncio
    @patch(f'{_MOD}.call_transform_api', new_callable=AsyncMock)
    @patch(f'{_MOD}.is_fes_available', return_value=True)
    async def test_add_partner_tenant_without_customer_consent_does_not_elicit(
        self, _, mock_fes, handler, ctx
    ):
        mock_fes.return_value = {'ok': True}

        result = await handler.manage_engagement(
            ctx,
            action='add_tenant',
            engagementId='e-1',
            targetTenantId='t-2',
            tenantType='PARTNER',
            description='Delivery partner',
            partnerIntent='PERFORM_ASSESSMENT_AND_MIGRATION',
        )

        assert _parse(result)['success'] is True
        ctx.elicit.assert_not_awaited()
        mock_fes.assert_awaited_once()

    @pytest.mark.asyncio
    @patch(f'{_MOD}.call_transform_api', new_callable=AsyncMock)
    @patch(f'{_MOD}.is_fes_available', return_value=True)
    async def test_add_partner_tenant_with_customer_consent_without_partner_intent(
        self, _, mock_fes, handler, ctx
    ):
        mock_fes.return_value = {'ok': True}

        result = await handler.manage_engagement(
            ctx,
            action='add_tenant',
            engagementId='e-1',
            targetTenantId=_VALID_TENANT_ID,
            tenantType='PARTNER',
            description='Delivery partner',
            customerConsent='GRANTED',
            confirm=True,
        )

        assert _parse(result)['success'] is True
        ctx.elicit.assert_not_awaited()
        mock_fes.assert_awaited_once_with(
            'AddEngagementTenant',
            {
                'engagementId': 'e-1',
                'targetTenantId': _VALID_TENANT_ID,
                'type': 'PARTNER',
                'description': 'Delivery partner',
                'customerConsent': 'GRANTED',
            },
        )

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        'action,kwargs,operation,body',
        [
            (
                'create',
                {
                    'name': 'Migration',
                    'description': 'Migration engagement',
                    'tenantType': 'PARTNER',
                    'partnerType': 'CONSULTING_PARTNER',
                    'customerEmail': 'customer@example.com',
                },
                'CreateEngagement',
                {
                    'name': 'Migration',
                    'description': 'Migration engagement',
                    'tenantType': 'PARTNER',
                    'partnerType': 'CONSULTING_PARTNER',
                    'customerEmail': 'customer@example.com',
                },
            ),
            (
                'update',
                {'engagementId': 'e-1', 'name': 'Updated'},
                'UpdateEngagement',
                {'engagementId': 'e-1', 'name': 'Updated'},
            ),
            (
                'accept_invitation',
                {'engagementId': 'e-1', 'partnerType': 'DISTRIBUTOR'},
                'AcceptEngagementInvitation',
                {'engagementId': 'e-1', 'partnerType': 'DISTRIBUTOR'},
            ),
            (
                'reject_invitation',
                {'engagementId': 'e-1', 'confirm': True},
                'RejectEngagementInvitation',
                {'engagementId': 'e-1'},
            ),
            (
                'add_tenant',
                {
                    'engagementId': 'e-1',
                    'targetTenantId': _VALID_TENANT_ID,
                    'tenantType': 'PARTNER',
                    'description': 'Delivery partner',
                    'customerConsent': 'GRANTED',
                    'partnerIntent': 'PERFORM_ASSESSMENT_AND_MIGRATION',
                    'confirm': True,
                },
                'AddEngagementTenant',
                {
                    'engagementId': 'e-1',
                    'targetTenantId': _VALID_TENANT_ID,
                    'type': 'PARTNER',
                    'description': 'Delivery partner',
                    'customerConsent': 'GRANTED',
                    'partnerIntent': 'PERFORM_ASSESSMENT_AND_MIGRATION',
                },
            ),
            (
                'remove_tenant',
                {
                    'engagementId': 'e-1',
                    'targetTenantId': _VALID_TENANT_ID,
                    'confirm': True,
                },
                'RemoveEngagementTenant',
                {'engagementId': 'e-1', 'targetTenantId': _VALID_TENANT_ID},
            ),
            (
                'add_user',
                {'engagementId': 'e-1', 'targetUserId': 'u-2', 'role': 'LEAD'},
                'AddEngagementUser',
                {'engagementId': 'e-1', 'targetUserId': 'u-2', 'role': 'LEAD'},
            ),
            (
                'remove_user',
                {'engagementId': 'e-1', 'targetUserId': 'u-2', 'confirm': True},
                'RemoveEngagementUser',
                {'engagementId': 'e-1', 'targetUserId': 'u-2'},
            ),
            (
                'add_workspace',
                {'engagementId': 'e-1', 'workspaceId': _VALID_WORKSPACE_ID},
                'AddEngagementWorkspace',
                {'engagementId': 'e-1', 'workspaceId': _VALID_WORKSPACE_ID},
            ),
            (
                'remove_workspace',
                {
                    'engagementId': 'e-1',
                    'workspaceId': _VALID_WORKSPACE_ID,
                    'confirm': True,
                },
                'RemoveEngagementWorkspace',
                {'engagementId': 'e-1', 'workspaceId': _VALID_WORKSPACE_ID},
            ),
        ],
    )
    @patch(f'{_MOD}.call_transform_api', new_callable=AsyncMock)
    @patch(f'{_MOD}.is_fes_available', return_value=True)
    async def test_dispatches_action(
        self,
        _,
        mock_fes,
        action,
        kwargs,
        operation,
        body,
        handler,
        ctx,
    ):
        mock_fes.return_value = {'ok': True}

        result = await handler.manage_engagement(ctx, action=action, **kwargs)

        assert _parse(result)['success'] is True
        mock_fes.assert_awaited_once_with(operation, body)
        dispatched_operation, dispatched_body = mock_fes.await_args.args
        validate_request(dispatched_operation, dispatched_body)

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        'action,kwargs',
        [
            ('reject_invitation', {'engagementId': 'e-1'}),
            ('remove_tenant', {'engagementId': 'e-1', 'targetTenantId': 't-2'}),
            ('remove_user', {'engagementId': 'e-1', 'targetUserId': 'u-2'}),
            ('remove_workspace', {'engagementId': 'e-1', 'workspaceId': 'w-1'}),
        ],
    )
    @patch(f'{_MOD}.is_fes_available', return_value=True)
    async def test_destructive_actions_require_confirmation(self, _, action, kwargs, handler, ctx):
        result = await handler.manage_engagement(ctx, action=action, **kwargs)
        parsed = _parse(result)
        assert parsed['error']['code'] == 'VALIDATION_ERROR'
        assert 'confirmation' in parsed['error']['message']

    @pytest.mark.asyncio
    @patch(f'{_MOD}.is_fes_available', return_value=True)
    async def test_rejects_parameter_for_different_action(self, _, handler, ctx):
        result = await handler.manage_engagement(
            ctx,
            action='remove_user',
            engagementId='e-1',
            targetUserId='u-2',
            workspaceId='w-1',
            confirm=True,
        )
        parsed = _parse(result)
        assert parsed['error']['code'] == 'VALIDATION_ERROR'
        assert 'workspaceId' in parsed['error']['message']

    @pytest.mark.asyncio
    @patch(f'{_MOD}.call_transform_api', new_callable=AsyncMock)
    @patch(f'{_MOD}.is_fes_available', return_value=True)
    async def test_confirm_false_is_ignored_for_non_destructive_action(
        self, _, mock_fes, handler, ctx
    ):
        mock_fes.return_value = {'ok': True}

        result = await handler.manage_engagement(
            ctx,
            action='create',
            name='Migration',
            description='Migration engagement',
            tenantType='CUSTOMER',
            confirm=False,
        )

        assert _parse(result)['success'] is True
        mock_fes.assert_awaited_once()

    @pytest.mark.asyncio
    @patch(f'{_MOD}.is_fes_available', return_value=True)
    async def test_confirm_false_does_not_bypass_destructive_gate(self, _, handler, ctx):
        result = await handler.manage_engagement(
            ctx,
            action='remove_user',
            engagementId='e-1',
            targetUserId='u-2',
            confirm=False,
        )

        parsed = _parse(result)
        assert parsed['error']['code'] == 'VALIDATION_ERROR'
        assert 'confirmation' in parsed['error']['message']

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        'action,kwargs,field',
        [
            ('update', {'engagementId': 'e-1', 'name': ''}, 'name'),
            (
                'create',
                {
                    'name': 'Migration',
                    'description': 'Migration engagement',
                    'tenantType': 'CUSTOMER',
                    'tenantDescription': '',
                },
                'tenantDescription',
            ),
            (
                'add_tenant',
                {
                    'engagementId': 'e-1',
                    'targetTenantId': 't-2',
                    'tenantType': 'CUSTOMER',
                    'description': '',
                },
                'description',
            ),
        ],
    )
    async def test_rejects_empty_min_length_fields(self, action, kwargs, field, handler, ctx):
        result = await handler.manage_engagement(ctx, action=action, **kwargs)

        parsed = _parse(result)
        assert parsed['error']['code'] == 'VALIDATION_ERROR'
        assert field in parsed['error']['message']
        assert 'must not be empty' in parsed['error']['message']

    @pytest.mark.asyncio
    async def test_missing_required_parameter(self, handler, ctx):
        result = await handler.manage_engagement(
            ctx,
            action='create',
            name='Migration',
            tenantType='CUSTOMER',
        )

        parsed = _parse(result)
        assert parsed['error']['code'] == 'VALIDATION_ERROR'
        assert 'description' in parsed['error']['message']

    @pytest.mark.asyncio
    @patch(f'{_MOD}.is_fes_available', return_value=True)
    async def test_partner_create_requires_partner_type(self, _, handler, ctx):
        result = await handler.manage_engagement(
            ctx,
            action='create',
            name='Migration',
            description='Migration engagement',
            tenantType='PARTNER',
        )
        parsed = _parse(result)
        assert parsed['error']['code'] == 'VALIDATION_ERROR'
        assert 'partnerType' in parsed['error']['message']

    @pytest.mark.asyncio
    @patch(f'{_MOD}.is_fes_available', return_value=True)
    async def test_customer_create_rejects_partner_type(self, _, handler, ctx):
        result = await handler.manage_engagement(
            ctx,
            action='create',
            name='Migration',
            description='Migration engagement',
            tenantType='CUSTOMER',
            partnerType='ISV',
        )
        parsed = _parse(result)
        assert parsed['error']['code'] == 'VALIDATION_ERROR'
        assert 'must be omitted' in parsed['error']['message']

    @pytest.mark.asyncio
    @patch(f'{_MOD}.is_fes_available', return_value=True)
    async def test_update_requires_a_changed_field(self, _, handler, ctx):
        result = await handler.manage_engagement(ctx, action='update', engagementId='e-1')
        parsed = _parse(result)
        assert parsed['error']['code'] == 'VALIDATION_ERROR'
        assert 'at least one field' in parsed['error']['message']

    @pytest.mark.asyncio
    @patch(
        f'{_MOD}.call_transform_api',
        new_callable=AsyncMock,
        side_effect=RuntimeError('API error'),
    )
    @patch(f'{_MOD}.is_fes_available', return_value=True)
    async def test_api_error_returns_failure(self, _, mock_fes, handler, ctx):
        result = await handler.manage_engagement(
            ctx,
            action='update',
            engagementId='e-1',
            name='Updated',
        )
        parsed = _parse(result)
        assert parsed['success'] is False
        assert 'API error' in parsed['error']['message']
