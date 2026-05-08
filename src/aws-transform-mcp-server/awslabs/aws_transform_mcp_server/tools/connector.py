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

import uuid
from awslabs.aws_transform_mcp_server.audit import audited_tool
from awslabs.aws_transform_mcp_server.aws_helper import AwsHelper
from awslabs.aws_transform_mcp_server.config_store import (
    get_config,
    is_fes_available,
)
from awslabs.aws_transform_mcp_server.tcp_client import call_tcp
from awslabs.aws_transform_mcp_server.tool_utils import (
    CREATE,
    MUTATE,
    error_result,
    failure_result,
    success_result,
)
from awslabs.aws_transform_mcp_server.transform_api_client import call_transform_api
from awslabs.aws_transform_mcp_server.transform_api_models import (
    AccountConnectionRequest,
    AwsAccountConnectionRequest,
    CreateConnectorRequest,
    GetConnectorRequest,
)
from mcp.server.fastmcp import Context
from pydantic import Field
from typing import Annotated, Any, Optional


_NOT_CONFIGURED_CODE = 'NOT_CONFIGURED'
_NOT_CONFIGURED_MSG = 'Transform connection not configured.'
_NOT_CONFIGURED_ACTION = 'Call "configure" first.'


def _build_verification_link(
    connector_id: str,
    region: str,
) -> str:
    """Build a console verification link for a connector."""
    return (
        f'https://{region}.console.aws.amazon.com/transform/connector/'
        f'{connector_id}/configure?region={region}'
    )


class ConnectorHandler:
    """Registers connector-related MCP tools."""

    def __init__(self, mcp: Any) -> None:
        """Register connector tools on the MCP server."""
        audited_tool(mcp, 'create_connector', title='Create Connector', annotations=MUTATE)(
            self.create_connector
        )
        audited_tool(mcp, 'accept_connector', title='Accept Connector', annotations=CREATE)(
            self.accept_connector
        )

    async def create_connector(
        self,
        ctx: Context,
        workspaceId: Annotated[str, Field(description='The workspace to create the connector in')],
        connectorName: Annotated[str, Field(description='Display name for the connector')],
        connectorType: Annotated[str, Field(description='Type of connector (e.g. "S3", "CODE")')],
        configuration: Annotated[
            dict,
            Field(
                description=(
                    'Connector configuration key-value pairs (e.g. { "s3Uri": "s3://bucket/path" })'
                ),
            ),
        ],
        awsAccountId: Annotated[
            str, Field(description='AWS account ID for the account connection')
        ],
        description: Annotated[
            Optional[str],
            Field(
                description='Optional description for the connector',
            ),
        ] = None,
        targetRegions: Annotated[
            Optional[list],
            Field(
                description='Optional list of target AWS regions (e.g. ["us-east-1", "us-west-2"])',
            ),
        ] = None,
    ) -> dict:
        """Create a connector in a workspace.

        Returns connector status and a verification link. After creation,
        the connector must be activated by either:
        1. Opening the verification link in the AWS console (lets you create
           an IAM role during approval), OR
        2. Calling accept_connector with an existing IAM role ARN.

        Requires browser/SSO auth.
        """
        if not is_fes_available():
            return error_result(_NOT_CONFIGURED_CODE, _NOT_CONFIGURED_MSG, _NOT_CONFIGURED_ACTION)

        try:
            create_req = CreateConnectorRequest(
                workspaceId=workspaceId,
                connectorName=connectorName,
                connectorType=connectorType,
                configuration=configuration,
                accountConnectionRequest=AccountConnectionRequest(
                    awsAccountConnectionRequest=AwsAccountConnectionRequest(
                        awsAccountId=awsAccountId,
                    ),
                ),
                idempotencyToken=str(uuid.uuid4()),
                description=description,
                targetRegions=targetRegions,
            )

            create_result = await call_transform_api('CreateConnector', create_req)

            connector_id = create_result['connectorId']

            status = await call_transform_api(
                'GetConnector',
                GetConnectorRequest(
                    workspaceId=workspaceId,
                    connectorId=connector_id,
                ),
            )

            config = get_config()
            if config is not None:
                region = config.region
            else:
                region = AwsHelper.resolve_region(AwsHelper.create_session())
            verification_link = _build_verification_link(
                connector_id,
                region,
            )

            data = {
                'connectorId': status.get('connectorId', connector_id)
                if isinstance(status, dict)
                else connector_id,
                'connectorName': status.get('connectorName') if isinstance(status, dict) else None,
                'accountConnection': status.get('accountConnection')
                if isinstance(status, dict)
                else None,
            }
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

    async def accept_connector(
        self,
        ctx: Context,
        workspaceId: Annotated[str, Field(description='The workspace containing the connector')],
        connectorId: Annotated[str, Field(description='The connector to associate the role with')],
        roleArn: Annotated[
            str,
            Field(
                description='ARN of the IAM role to associate with the connector',
            ),
        ],
    ) -> dict:
        """Activate a connector by associating an IAM role with it.

        Alternative to approving via the AWS console verification link.
        Use this when you already have an IAM role ARN ready. The AWS
        account ID is inferred from your AWS credentials.

        Requires both AWS credentials (auto-detected) and browser/SSO auth.
        """
        if not is_fes_available():
            return error_result(
                _NOT_CONFIGURED_CODE,
                _NOT_CONFIGURED_MSG,
                _NOT_CONFIGURED_ACTION,
            )

        session = AwsHelper.create_session()
        if session.get_credentials() is None:
            return error_result(
                'NO_AWS_CREDENTIALS',
                'No AWS credentials detected.',
                'Set AWS_PROFILE in your MCP client config env block, '
                'or configure via aws configure / environment variables. '
                'Use get_status to verify credentials are working.',
            )

        try:
            region = AwsHelper.resolve_region(session)
            sts_client = AwsHelper.create_boto3_client('sts', region_name=region)
            account_id = sts_client.get_caller_identity()['Account']

            await call_tcp(
                'AssociateConnectorResource',
                {
                    'connectorId': connectorId,
                    'workspaceId': workspaceId,
                    'sourceAccount': account_id,
                    'resource': {'roleArn': roleArn},
                    'clientToken': str(uuid.uuid4()),
                },
            )

            status = await call_transform_api(
                'GetConnector',
                GetConnectorRequest(
                    workspaceId=workspaceId,
                    connectorId=connectorId,
                ),
            )

            data = (
                {
                    'connectorId': status.get('connectorId', connectorId),
                    'connectorName': status.get('connectorName'),
                    'accountConnection': status.get('accountConnection'),
                }
                if isinstance(status, dict)
                else status
            )

            return success_result(data)
        except Exception as error:
            return failure_result(error)
