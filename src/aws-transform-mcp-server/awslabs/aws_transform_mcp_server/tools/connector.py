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

"""Connector tool handlers for AWS Transform MCP server."""

import re
import uuid
from awslabs.aws_transform_mcp_server.audit import audited_tool
from awslabs.aws_transform_mcp_server.config_store import (
    get_config,
    is_configured,
    is_sigv4_configured,
)
from awslabs.aws_transform_mcp_server.fes_client import call_fes
from awslabs.aws_transform_mcp_server.tcp_client import call_tcp
from awslabs.aws_transform_mcp_server.tool_utils import (
    error_result,
    failure_result,
    success_result,
)
from mcp.server.fastmcp import Context
from pydantic import Field
from typing import Any, Dict, Optional
from urllib.parse import urlencode


_NOT_CONFIGURED_CODE = 'NOT_CONFIGURED'
_NOT_CONFIGURED_MSG = 'Transform connection not configured.'
_NOT_CONFIGURED_ACTION = 'Call "configure" first.'

_SIGV4_NOT_CONFIGURED_CODE = 'SIGV4_NOT_CONFIGURED'
_SIGV4_NOT_CONFIGURED_MSG = 'SigV4 credentials not configured.'
_SIGV4_NOT_CONFIGURED_ACTION = 'Call "configure_sigv4" to set up AWS credentials.'

_PROFILE_NAME_RE = re.compile(r'^[a-zA-Z][a-zA-Z0-9_-]{0,99}$')


def _build_verification_link(
    connector_id: str,
    stage: str,
    region: str,
    source_account: Optional[str] = None,
    workspace_id: Optional[str] = None,
) -> str:
    """Build a console verification link for a connector."""
    if stage == 'prod':
        return (
            f'https://{region}.console.aws.amazon.com/transform/connector/'
            f'{connector_id}/configure?region={region}'
        )
    # Gamma and other non-prod stages
    params: Dict[str, str] = {'region': region}
    if source_account:
        params['sourceAccount'] = source_account
    if workspace_id:
        params['workspaceId'] = workspace_id
    return (
        f'https://{region}.awsc-integ.aws.amazon.com/transform/connector/'
        f'{connector_id}/configure?{urlencode(params)}'
    )


class ConnectorHandler:
    """Registers connector-related MCP tools."""

    def __init__(self, mcp: Any) -> None:
        """Register connector tools on the MCP server."""
        audited_tool(mcp, 'create_connector')(self.create_connector)
        audited_tool(mcp, 'create_profile')(self.create_profile)
        audited_tool(mcp, 'accept_connector')(self.accept_connector)

    async def create_connector(
        self,
        ctx: Context,
        workspaceId: str = Field(..., description='The workspace to create the connector in'),
        connectorName: str = Field(..., description='Display name for the connector'),
        connectorType: str = Field(..., description='Type of connector (e.g. "S3", "CODE")'),
        configuration: dict = Field(
            ...,
            description=(
                'Connector configuration key-value pairs (e.g. { "s3Uri": "s3://bucket/path" })'
            ),
        ),
        awsAccountId: str = Field(..., description='AWS account ID for the account connection'),
        description: Optional[str] = Field(
            None, description='Optional description for the connector'
        ),
        targetRegions: Optional[list] = Field(
            None,
            description='Optional list of target AWS regions (e.g. ["us-east-1", "us-west-2"])',
        ),
    ) -> dict:
        """Create an S3 or code source connector in a workspace via FES.

        Returns connector status and a verification link to share with your
        AWS admin for approval.  Requires browser/SSO auth -- call configure first.
        """
        if not is_configured():
            return error_result(_NOT_CONFIGURED_CODE, _NOT_CONFIGURED_MSG, _NOT_CONFIGURED_ACTION)

        try:
            payload: Dict[str, Any] = {
                'workspaceId': workspaceId,
                'connectorName': connectorName,
                'connectorType': connectorType,
                'configuration': configuration,
                'accountConnectionRequest': {
                    'awsAccountConnectionRequest': {'awsAccountId': awsAccountId},
                },
                'idempotencyToken': str(uuid.uuid4()),
            }
            if description is not None:
                payload['description'] = description
            if targetRegions is not None:
                payload['targetRegions'] = targetRegions

            create_result = await call_fes('CreateConnector', payload)

            connector_id = create_result['connectorId']

            status = await call_fes(
                'GetConnector',
                {
                    'workspaceId': workspaceId,
                    'connectorId': connector_id,
                },
            )

            config = get_config()
            if config is None:
                return error_result(
                    'NOT_CONFIGURED',
                    'Not connected. Use configure first.',
                )
            verification_link = _build_verification_link(
                connector_id,
                config.stage,
                config.region,
                awsAccountId,
                workspaceId,
            )

            data = dict(status) if isinstance(status, dict) else {'status': status}
            data['verificationLink'] = verification_link
            data['nextStep'] = (
                'IMPORTANT: The connector is in PENDING status and CANNOT be used yet. '
                'Share the verification link with your AWS admin. They must open it and '
                'approve the connector. '
                'DO NOT proceed with any tasks that depend on this connector until the '
                'user confirms the admin has approved it. '
                'STOP here and ask the user to confirm once their AWS admin has approved '
                'the connector.'
            )
            return success_result(data)
        except Exception as error:
            return failure_result(error)

    async def create_profile(
        self,
        ctx: Context,
        profileName: str = Field(
            ...,
            description=(
                'Display name for the profile (alphanumeric, underscore, hyphen; 1-100 chars)'
            ),
        ),
        identityType: str = Field(
            ..., description='Identity provider type: "sso" or "externalIdp"'
        ),
        ssoInstanceArn: Optional[str] = Field(
            None, description='SSO instance ARN (required when identityType="sso")'
        ),
        ssoRegion: Optional[str] = Field(
            None, description='SSO region (required when identityType="sso")'
        ),
        clientId: Optional[str] = Field(
            None,
            description='OAuth client ID (required when identityType="externalIdp")',
        ),
        clientSecretArn: Optional[str] = Field(
            None,
            description=(
                'ARN of the secret containing the OAuth client secret '
                '(required when identityType="externalIdp")'
            ),
        ),
        authorizationUrl: Optional[str] = Field(
            None,
            description=(
                'OAuth authorization endpoint URL (required when identityType="externalIdp")'
            ),
        ),
        tokenUrl: Optional[str] = Field(
            None,
            description='OAuth token endpoint URL (required when identityType="externalIdp")',
        ),
        userInfoUrl: Optional[str] = Field(
            None,
            description='OAuth userinfo endpoint URL (required when identityType="externalIdp")',
        ),
        customerKmsArn: Optional[str] = Field(
            None, description='Customer-managed KMS key ARN for encryption'
        ),
    ) -> dict:
        """Create a new ATX profile via the Transform Control Plane (TCP).

        Requires AWS credentials -- call configure_sigv4 first.

        Identity type determines which params are needed:
          - "sso" -> ssoInstanceArn, ssoRegion
          - "externalIdp" -> clientId, clientSecretArn, authorizationUrl, tokenUrl, userInfoUrl
        """
        if not is_sigv4_configured():
            return error_result(
                _SIGV4_NOT_CONFIGURED_CODE,
                _SIGV4_NOT_CONFIGURED_MSG,
                _SIGV4_NOT_CONFIGURED_ACTION,
            )

        # Validate profileName format
        if not _PROFILE_NAME_RE.match(profileName):
            return error_result(
                'VALIDATION_ERROR',
                'profileName must be 1-100 characters: alphanumeric, underscore, or hyphen.',
            )

        # Validate identity-type-specific required params
        if identityType == 'sso':
            if not ssoInstanceArn:
                return error_result(
                    'VALIDATION_ERROR',
                    'ssoInstanceArn is required when identityType="sso".',
                )
            if not ssoRegion:
                return error_result(
                    'VALIDATION_ERROR',
                    'ssoRegion is required when identityType="sso".',
                )
        else:
            if not clientId:
                return error_result(
                    'VALIDATION_ERROR',
                    'clientId is required when identityType="externalIdp".',
                )
            if not clientSecretArn:
                return error_result(
                    'VALIDATION_ERROR',
                    'clientSecretArn is required when identityType="externalIdp".',
                )
            if not authorizationUrl:
                return error_result(
                    'VALIDATION_ERROR',
                    'authorizationUrl is required when identityType="externalIdp".',
                )
            if not tokenUrl:
                return error_result(
                    'VALIDATION_ERROR',
                    'tokenUrl is required when identityType="externalIdp".',
                )
            if not userInfoUrl:
                return error_result(
                    'VALIDATION_ERROR',
                    'userInfoUrl is required when identityType="externalIdp".',
                )

        try:
            # Build identitySource in the format the TCP API expects
            if identityType == 'sso':
                identity_source = {
                    'ssoIdentitySource': {
                        'instanceArn': ssoInstanceArn,
                        'ssoRegion': ssoRegion,
                    },
                }
            else:
                external_idp: dict = {
                    'clientId': clientId,
                    'clientSecretArn': clientSecretArn,
                }
                if authorizationUrl is not None:
                    external_idp['authorizationUrl'] = authorizationUrl
                if tokenUrl is not None:
                    external_idp['tokenUrl'] = tokenUrl
                if userInfoUrl is not None:
                    external_idp['userInfoUrl'] = userInfoUrl
                identity_source = {'externalIdpIdentitySource': external_idp}

            body: dict = {
                'profileName': profileName,
                'identitySource': identity_source,
                'clientToken': str(uuid.uuid4()),
            }
            if customerKmsArn:
                body['customerKmsArn'] = customerKmsArn

            data = await call_tcp('CreateProfile', body)
            return success_result(data)
        except Exception as error:
            return failure_result(error)

    async def accept_connector(
        self,
        ctx: Context,
        workspaceId: str = Field(..., description='The workspace containing the connector'),
        connectorId: str = Field(..., description='The connector to associate the role with'),
        awsAccountId: str = Field(..., description='AWS account ID that owns the IAM role'),
        roleArn: str = Field(
            ..., description='ARN of the IAM role to associate with the connector'
        ),
    ) -> dict:
        """Associate an IAM role with a connector via TCP, then return status from FES.

        Requires BOTH auth systems:
          - AWS credentials (configure_sigv4) for the TCP AssociateConnectorResource call
          - Browser/SSO auth (configure) for the FES GetConnector status check
        """
        if not is_sigv4_configured():
            return error_result(
                _SIGV4_NOT_CONFIGURED_CODE,
                _SIGV4_NOT_CONFIGURED_MSG,
                _SIGV4_NOT_CONFIGURED_ACTION,
            )
        if not is_configured():
            return error_result(
                _NOT_CONFIGURED_CODE,
                _NOT_CONFIGURED_MSG,
                'Call "configure" first (needed to fetch connector status).',
            )

        try:
            await call_tcp(
                'AssociateConnectorResource',
                {
                    'connectorId': connectorId,
                    'workspaceId': workspaceId,
                    'sourceAccount': awsAccountId,
                    'resource': {'roleArn': roleArn},
                    'clientToken': str(uuid.uuid4()),
                },
            )

            status = await call_fes(
                'GetConnector',
                {
                    'workspaceId': workspaceId,
                    'connectorId': connectorId,
                },
            )

            return success_result(status)
        except Exception as error:
            return failure_result(error)
