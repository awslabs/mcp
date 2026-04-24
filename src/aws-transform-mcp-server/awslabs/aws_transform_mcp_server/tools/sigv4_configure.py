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

"""SigV4 configure tool handler for AWS Transform MCP server."""

import boto3
from awslabs.aws_transform_mcp_server.audit import audited_tool
from awslabs.aws_transform_mcp_server.aws_helper import AwsHelper
from awslabs.aws_transform_mcp_server.config_store import (
    derive_tcp_endpoint,
    set_sigv4_config,
)
from awslabs.aws_transform_mcp_server.models import SigV4Config
from awslabs.aws_transform_mcp_server.tool_utils import (
    failure_result,
    success_result,
)
from mcp.server.fastmcp import Context
from pydantic import Field
from typing import Any


class SigV4ConfigureHandler:
    """Registers SigV4 configure MCP tool."""

    def __init__(self, mcp: Any) -> None:
        """Register sigv4 configure tool on the MCP server."""
        audited_tool(mcp, 'configure_sigv4')(self.configure_sigv4)

    async def configure_sigv4(
        self,
        ctx: Context,
        stage: str = Field(
            'prod',
            description=(
                'Environment stage (default: "prod"). Gamma only supports us-east-1 and us-west-2.'
            ),
        ),
        region: str = Field('us-east-1', description='AWS region (default: "us-east-1")'),
    ) -> dict:
        """Configure AWS credentials for the Transform Control Plane (TCP) API.

        Uses the standard AWS credential chain (env vars, ~/.aws/credentials,
        instance profile).  Validates via STS GetCallerIdentity before caching.
        This is completely independent from browser/SSO authentication (configure).
        """
        try:
            # Step 1: Resolve credentials from default provider chain
            session = boto3.Session()
            resolved = session.get_credentials()
            if resolved is None:
                raise ValueError('No AWS credentials found in the default provider chain.')
            credentials = resolved.get_frozen_credentials()

            # Step 2: Validate via STS GetCallerIdentity
            sts_client = AwsHelper.create_boto3_client('sts', region_name=region)
            identity = sts_client.get_caller_identity()

            tcp_endpoint = derive_tcp_endpoint(stage, region)

            # Step 3: Cache in memory
            set_sigv4_config(
                SigV4Config(
                    account_id=identity.get('Account', 'unknown'),
                    role='default',
                    stage=stage,
                    region=region,
                    tcp_endpoint=tcp_endpoint,
                    access_key_id=credentials.access_key or '',
                    secret_access_key=credentials.secret_key or '',
                    session_token=credentials.token,
                )
            )

        except Exception as error:
            return failure_result(
                error,
                'Ensure valid AWS credentials are available '
                '(via env vars, ~/.aws/credentials, or instance profile).',
            )

        return success_result(
            {
                'message': 'SigV4 credentials configured for Transform Control Plane',
                'accountId': identity.get('Account'),
                'arn': identity.get('Arn'),
                'stage': stage,
                'region': region,
                'tcpEndpoint': tcp_endpoint,
            }
        )
