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

"""Engagement tool handler for AWS Transform MCP server."""

from awslabs.aws_transform_mcp_server.audit import audited_tool
from awslabs.aws_transform_mcp_server.config_store import is_fes_available
from awslabs.aws_transform_mcp_server.tool_utils import (
    DELETE,
    error_result,
    failure_result,
    success_result,
)
from awslabs.aws_transform_mcp_server.transform_api_client import call_transform_api
from mcp.server.mcpserver import Context
from mcp.types import ClientCapabilities, ElicitationCapability
from pydantic import BaseModel, Field
from typing import Annotated, Any, Dict, Literal, Optional


EngagementAction = Literal[
    'create',
    'update',
    'accept_invitation',
    'reject_invitation',
    'add_tenant',
    'remove_tenant',
    'add_user',
    'remove_user',
    'add_workspace',
    'remove_workspace',
]
TenantType = Literal['CUSTOMER', 'PARTNER']
PartnerType = Literal[
    'DISTRIBUTOR',
    'SOLUTION_PROVIDER_MSP',
    'CONSULTING_PARTNER',
    'HYBRID_SYSTEMS_INTEGRATOR',
    'ISV',
]
UserRole = Literal['LEAD']
CustomerConsent = Literal['GRANTED']
PartnerIntent = Literal[
    'PERFORM_MIGRATE_ONLY',
    'PERFORM_ASSESSMENT_ONLY',
    'PERFORM_ASSESSMENT_AND_MIGRATION',
]

MANAGE_ENGAGEMENT_DESCRIPTION = """Create or modify an AWS Transform engagement.

Actions:
- create: Create an engagement. Requires name, description, and tenantType.
- update: Update engagement details. Requires engagementId and at least one field to update.
- accept_invitation: Accept an invitation. Requires engagementId. First list
  engagement_invitations and use invitedTenantType: partnerType is required for
  PARTNER invitations and must be omitted for CUSTOMER invitations.
- reject_invitation: Reject an invitation. Requires engagementId and confirm=true.
- add_tenant: Invite a tenant. Requires engagementId, targetTenantId, tenantType, and description.
  When a customer invites a partner, customerConsent and partnerIntent may record the
  customer's data-sharing consent and intended partner work. Setting
  customerConsent=GRANTED requires the user's explicit agreement. The tool asks for
  confirmation when the client supports elicitation; otherwise retry with confirm=true
  only after the user explicitly agrees.
- remove_tenant: Withdraw a pending partner invitation. Only the customer can do this.
  Removing an accepted partner requires AWS Support. Requires engagementId,
  targetTenantId, and confirm=true.
- add_user: Add a user. Requires engagementId, targetUserId, and role.
- remove_user: Remove a user. Requires engagementId, targetUserId, and confirm=true.
- add_workspace: Attach a workspace. Requires engagementId and workspaceId. A workspace
  with jobs cannot later be removed from the engagement.
- remove_workspace: Remove a workspace that has no jobs. Workspaces with jobs cannot be
  removed. Requires engagementId, workspaceId, and confirm=true.

Caller user and tenant identity are derived from the authenticated session. Use
list_resources for engagement collections and get_resource for engagement details.
"""

_NOT_CONFIGURED_CODE = 'NOT_CONFIGURED'
_NOT_CONFIGURED_MSG = 'Not connected to AWS Transform.'
_NOT_CONFIGURED_ACTION = (
    'Call get_status. If AWS credentials are unavailable, call configure with '
    'authMode "cookie" or "sso".'
)

_ACTION_FIELDS = {
    'create': {
        'name',
        'description',
        'tenantType',
        'partnerType',
        'tenantDescription',
        'migrationExecutiveSponsorName',
        'customerEmail',
        'customerWebsite',
        'customerAddress',
    },
    'update': {
        'engagementId',
        'name',
        'description',
        'migrationExecutiveSponsorName',
        'customerEmail',
        'customerWebsite',
        'customerAddress',
    },
    'accept_invitation': {'engagementId', 'partnerType'},
    'reject_invitation': {'engagementId', 'confirm'},
    'add_tenant': {
        'engagementId',
        'targetTenantId',
        'tenantType',
        'description',
        'customerConsent',
        'partnerIntent',
        'confirm',
    },
    'remove_tenant': {'engagementId', 'targetTenantId', 'confirm'},
    'add_user': {'engagementId', 'targetUserId', 'role'},
    'remove_user': {'engagementId', 'targetUserId', 'confirm'},
    'add_workspace': {'engagementId', 'workspaceId'},
    'remove_workspace': {'engagementId', 'workspaceId', 'confirm'},
}

_REQUIRED_FIELDS = {
    'create': {'name', 'description', 'tenantType'},
    'update': {'engagementId'},
    'accept_invitation': {'engagementId'},
    'reject_invitation': {'engagementId'},
    'add_tenant': {'engagementId', 'targetTenantId', 'tenantType', 'description'},
    'remove_tenant': {'engagementId', 'targetTenantId'},
    'add_user': {'engagementId', 'targetUserId', 'role'},
    'remove_user': {'engagementId', 'targetUserId'},
    'add_workspace': {'engagementId', 'workspaceId'},
    'remove_workspace': {'engagementId', 'workspaceId'},
}

_DESTRUCTIVE_ACTIONS = {
    'reject_invitation',
    'remove_tenant',
    'remove_user',
    'remove_workspace',
}

_NON_EMPTY_FIELDS = {'name', 'description', 'tenantDescription'}


class CustomerConsentConfirmation(BaseModel):
    """Response collected before granting customer data-sharing consent."""

    confirm: bool = Field(
        description=(
            'True only if you explicitly agree to share engagement data with the invited partner.'
        )
    )


def _compact(**values: Any) -> Dict[str, Any]:
    """Remove omitted optional fields from a FES request body."""
    return {key: value for key, value in values.items() if value is not None}


async def _require_customer_consent(ctx: Context, confirm: Optional[bool]) -> Optional[dict]:
    """Obtain explicit user consent before granting partner data sharing."""
    if confirm is True:
        return None

    try:
        has_elicitation = ctx.session.check_client_capability(
            ClientCapabilities(elicitation=ElicitationCapability())
        )
    except Exception:
        has_elicitation = False

    if has_elicitation:
        try:
            result = await ctx.elicit(
                (
                    'Do you explicitly agree to share this engagement data with the '
                    'invited partner?'
                ),
                CustomerConsentConfirmation,
            )
        except Exception:
            pass
        else:
            if result.action == 'accept' and result.data.confirm is True:
                return None
            return error_result(
                'CONSENT_NOT_GRANTED',
                ('Customer data-sharing consent was not granted. No partner invitation was sent.'),
                'Do not retry unless the user explicitly agrees to share the data.',
            )

    return error_result(
        'CONSENT_CONFIRMATION_REQUIRED',
        ('Explicit user confirmation is required before granting customer data-sharing consent.'),
        (
            'Ask the user to explicitly agree, then retry add_tenant with '
            'customerConsent="GRANTED" and confirm=true.'
        ),
    )


class EngagementHandler:
    """Registers the consolidated engagement management tool."""

    def __init__(self, mcp: Any) -> None:
        """Register manage_engagement on the MCP server."""
        audited_tool(
            mcp,
            'manage_engagement',
            title='Manage Engagement',
            annotations=DELETE,
            description=MANAGE_ENGAGEMENT_DESCRIPTION,
        )(self.manage_engagement)

    async def manage_engagement(
        self,
        ctx: Context,
        action: Annotated[
            EngagementAction,
            Field(
                description=(
                    'Engagement operation to perform. Only provide parameters required '
                    'by the selected action.'
                )
            ),
        ],
        engagementId: Annotated[
            Optional[str],
            Field(description='Engagement identifier. Required for every action except create.'),
        ] = None,
        name: Annotated[
            Optional[str],
            Field(description='Engagement name for create or update.'),
        ] = None,
        description: Annotated[
            Optional[str],
            Field(description='Engagement or tenant invitation description.'),
        ] = None,
        tenantType: Annotated[
            Optional[TenantType],
            Field(description='Tenant type for create or add_tenant.'),
        ] = None,
        partnerType: Annotated[
            Optional[PartnerType],
            Field(description='Partner role for create or accept_invitation.'),
        ] = None,
        tenantDescription: Annotated[
            Optional[str],
            Field(description='Optional description of the creating tenant.'),
        ] = None,
        migrationExecutiveSponsorName: Annotated[
            Optional[str],
            Field(description='Optional migration executive sponsor name.'),
        ] = None,
        customerEmail: Annotated[
            Optional[str],
            Field(description='Optional customer contact email.'),
        ] = None,
        customerWebsite: Annotated[
            Optional[str],
            Field(description='Optional customer website.'),
        ] = None,
        customerAddress: Annotated[
            Optional[str],
            Field(description='Optional customer address.'),
        ] = None,
        targetTenantId: Annotated[
            Optional[str],
            Field(description='Target tenant for add_tenant or remove_tenant.'),
        ] = None,
        customerConsent: Annotated[
            Optional[CustomerConsent],
            Field(
                description=(
                    'Customer data-sharing consent for add_tenant. Use GRANTED only when '
                    'a customer invites a PARTNER tenant and the user has explicitly '
                    'agreed to share the data.'
                )
            ),
        ] = None,
        partnerIntent: Annotated[
            Optional[PartnerIntent],
            Field(
                description=(
                    'Work the invited partner is intended to perform for add_tenant. '
                    'Only valid when inviting a PARTNER tenant.'
                )
            ),
        ] = None,
        targetUserId: Annotated[
            Optional[str],
            Field(description='Target user for add_user or remove_user.'),
        ] = None,
        role: Annotated[
            Optional[UserRole],
            Field(description='Engagement user role for add_user.'),
        ] = None,
        workspaceId: Annotated[
            Optional[str],
            Field(description='Workspace for add_workspace or remove_workspace.'),
        ] = None,
        confirm: Annotated[
            Optional[bool],
            Field(
                description=(
                    'Must be true for reject_invitation and remove actions, or when '
                    'retrying add_tenant with customerConsent=GRANTED after the user '
                    'explicitly agrees and client elicitation is unavailable.'
                )
            ),
        ] = None,
    ) -> dict:
        """Create or modify an AWS Transform engagement."""
        params = {
            'engagementId': engagementId,
            'name': name,
            'description': description,
            'tenantType': tenantType,
            'partnerType': partnerType,
            'tenantDescription': tenantDescription,
            'migrationExecutiveSponsorName': migrationExecutiveSponsorName,
            'customerEmail': customerEmail,
            'customerWebsite': customerWebsite,
            'customerAddress': customerAddress,
            'targetTenantId': targetTenantId,
            'customerConsent': customerConsent,
            'partnerIntent': partnerIntent,
            'targetUserId': targetUserId,
            'role': role,
            'workspaceId': workspaceId,
            'confirm': confirm,
        }

        unexpected = sorted(
            field
            for field, value in params.items()
            if value is not None
            and not (field == 'confirm' and value is False)
            and field not in _ACTION_FIELDS[action]
        )
        if unexpected:
            return error_result(
                'VALIDATION_ERROR',
                f'Parameters not valid for action="{action}": {", ".join(unexpected)}.',
                'Remove parameters that do not apply to the selected action.',
            )

        empty = sorted(
            field
            for field in _NON_EMPTY_FIELDS
            if field in _ACTION_FIELDS[action] and params.get(field) == ''
        )
        if empty:
            return error_result(
                'VALIDATION_ERROR',
                f'Parameters must not be empty for action="{action}": {", ".join(empty)}.',
            )

        missing = sorted(
            field for field in _REQUIRED_FIELDS[action] if params.get(field) in (None, '')
        )
        if missing:
            return error_result(
                'VALIDATION_ERROR',
                f'Missing required parameters for action="{action}": {", ".join(missing)}.',
            )

        if action in _DESTRUCTIVE_ACTIONS and confirm is not True:
            return error_result(
                'VALIDATION_ERROR',
                f'action="{action}" requires explicit confirmation.',
                'Set confirm=true to proceed.',
            )

        try:
            if action == 'create':
                if tenantType == 'PARTNER' and partnerType is None:
                    return error_result(
                        'VALIDATION_ERROR',
                        'partnerType is required when tenantType="PARTNER".',
                        'Use list_resources with resource="partner_types" to choose a value.',
                    )
                if tenantType == 'CUSTOMER' and partnerType is not None:
                    return error_result(
                        'VALIDATION_ERROR',
                        'partnerType must be omitted when tenantType="CUSTOMER".',
                    )
                operation = 'CreateEngagement'
                body = _compact(
                    name=name,
                    description=description,
                    tenantType=tenantType,
                    partnerType=partnerType,
                    tenantDescription=tenantDescription,
                    migrationExecutiveSponsorName=migrationExecutiveSponsorName,
                    customerEmail=customerEmail,
                    customerWebsite=customerWebsite,
                    customerAddress=customerAddress,
                )
            elif action == 'update':
                updates = _compact(
                    name=name,
                    description=description,
                    migrationExecutiveSponsorName=migrationExecutiveSponsorName,
                    customerEmail=customerEmail,
                    customerWebsite=customerWebsite,
                    customerAddress=customerAddress,
                )
                if not updates:
                    return error_result(
                        'VALIDATION_ERROR',
                        'action="update" requires at least one field to update.',
                    )
                operation = 'UpdateEngagement'
                body = {'engagementId': engagementId, **updates}
            elif action == 'accept_invitation':
                operation = 'AcceptEngagementInvitation'
                body = _compact(engagementId=engagementId, partnerType=partnerType)
            elif action == 'reject_invitation':
                operation = 'RejectEngagementInvitation'
                body = {'engagementId': engagementId}
            elif action == 'add_tenant':
                if tenantType != 'PARTNER' and (
                    customerConsent is not None or partnerIntent is not None
                ):
                    return error_result(
                        'VALIDATION_ERROR',
                        'customerConsent and partnerIntent are valid only when '
                        'tenantType="PARTNER".',
                        'Remove those parameters or invite a PARTNER tenant.',
                    )
                if customerConsent == 'GRANTED':
                    consent_error = await _require_customer_consent(ctx, confirm)
                    if consent_error is not None:
                        return consent_error
                operation = 'AddEngagementTenant'
                body = _compact(
                    engagementId=engagementId,
                    targetTenantId=targetTenantId,
                    type=tenantType,
                    description=description,
                    customerConsent=customerConsent,
                    partnerIntent=partnerIntent,
                )
            elif action == 'remove_tenant':
                operation = 'RemoveEngagementTenant'
                body = {'engagementId': engagementId, 'targetTenantId': targetTenantId}
            elif action == 'add_user':
                operation = 'AddEngagementUser'
                body = {'engagementId': engagementId, 'targetUserId': targetUserId, 'role': role}
            elif action == 'remove_user':
                operation = 'RemoveEngagementUser'
                body = {'engagementId': engagementId, 'targetUserId': targetUserId}
            elif action == 'add_workspace':
                operation = 'AddEngagementWorkspace'
                body = {
                    'engagementId': engagementId,
                    'workspaceId': workspaceId,
                }
            else:
                operation = 'RemoveEngagementWorkspace'
                body = {'engagementId': engagementId, 'workspaceId': workspaceId}

            if not is_fes_available():
                return error_result(
                    _NOT_CONFIGURED_CODE,
                    _NOT_CONFIGURED_MSG,
                    _NOT_CONFIGURED_ACTION,
                )

            return success_result(await call_transform_api(operation, body))
        except Exception as error:
            return failure_result(error)
