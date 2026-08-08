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

"""AWS context handler for runtime profile/region switching."""

from awslabs.eks_mcp_server.aws_helper import AwsHelper
from awslabs.eks_mcp_server.k8s_client_cache import K8sClientCache
from awslabs.eks_mcp_server.logging_helper import LogLevel, log_with_request_id
from loguru import logger
from mcp.server.fastmcp import Context, FastMCP
from mcp.types import CallToolResult, TextContent
from pydantic import BaseModel, Field
from typing import Annotated, Optional


class AwsContextData(BaseModel):
    """Data model for AWS context operations."""

    success: bool = Field(description='Whether the operation succeeded')
    profile: Optional[str] = Field(description='Current AWS profile (None if using default)')
    region: Optional[str] = Field(description='Current AWS region (None if using default)')
    message: str = Field(description='Human-readable status message')


class AwsContextHandler:
    """Handler for AWS context management tools.

    Provides tools to get and set AWS profile/region at runtime without
    restarting the MCP server.
    """

    def __init__(self, mcp: FastMCP):
        """Initialize the AWS context handler and register tools.

        Args:
            mcp: The FastMCP server instance
        """
        self.mcp = mcp

        # Register tools using the same pattern as other handlers
        self.mcp.tool(name='get_aws_context')(self.get_aws_context)
        self.mcp.tool(name='set_aws_context')(self.set_aws_context)

    async def get_aws_context(self, ctx: Context) -> CallToolResult:
        """Get the current AWS profile and region.

        Returns the currently configured AWS profile and region used for
        all AWS API calls. Returns None for values that are not explicitly
        set (falling back to AWS SDK defaults).

        This tool is useful for verifying which AWS credentials are currently
        in use before making API calls.

        Args:
            ctx: The MCP context

        Returns:
            CallToolResult with current profile and region
        """
        log_with_request_id(ctx, LogLevel.INFO, 'Getting AWS context')

        profile = AwsHelper.get_aws_profile()
        region = AwsHelper.get_aws_region()

        data = AwsContextData(
            success=True,
            profile=profile,
            region=region,
            message=f'AWS context: profile={profile or "(default)"}, region={region or "(default)"}',
        )

        return CallToolResult(
            content=[TextContent(type='text', text=data.model_dump_json(indent=2))]
        )

    async def set_aws_context(
        self,
        ctx: Context,
        profile: Annotated[
            Optional[str],
            Field(description='AWS profile name to use. Pass empty string "" to clear and use default credentials.'),
        ] = None,
        region: Annotated[
            Optional[str],
            Field(description='AWS region to use (e.g., "us-east-1", "ap-south-1"). Pass empty string "" to clear.'),
        ] = None,
    ) -> CallToolResult:
        """Set the AWS profile and/or region at runtime.

        Changes the AWS profile and/or region used for all subsequent AWS API calls.
        This clears all cached AWS and Kubernetes clients to ensure new connections
        use the updated credentials.

        Use this tool to switch between AWS accounts or regions without restarting
        the MCP server. For example, to switch from a dev account to prod, or to
        query clusters in different regions.

        IMPORTANT: After switching context, any subsequent tool calls will use the
        new credentials. This affects all AWS API operations including EKS cluster
        access.

        ## Usage Tips
        - Use get_aws_context first to see current settings
        - Pass None (or omit) to keep a value unchanged
        - Pass empty string "" to clear a value and use SDK defaults
        - Both profile and region can be changed in a single call

        Args:
            ctx: The MCP context
            profile: AWS profile name from ~/.aws/credentials or ~/.aws/config.
                    Pass None to keep current value, empty string to clear.
            region: AWS region code (e.g., "us-east-1").
                    Pass None to keep current value, empty string to clear.

        Returns:
            CallToolResult with the new profile and region values
        """
        try:
            log_with_request_id(
                ctx,
                LogLevel.INFO,
                f'Setting AWS context: profile={profile}, region={region}',
            )

            # Update AWS context and clear boto3 client cache
            result = AwsHelper.set_aws_context(profile=profile, region=region)

            # Also clear Kubernetes client cache since it uses AWS credentials
            k8s_cache = K8sClientCache()
            k8s_cache.clear_cache()

            new_profile = result['profile']
            new_region = result['region']

            log_with_request_id(
                ctx,
                LogLevel.INFO,
                f'AWS context updated: profile={new_profile}, region={new_region}',
            )

            data = AwsContextData(
                success=True,
                profile=new_profile,
                region=new_region,
                message=f'AWS context updated: profile={new_profile or "(default)"}, region={new_region or "(default)"}',
            )

            return CallToolResult(
                content=[TextContent(type='text', text=data.model_dump_json(indent=2))]
            )
        except Exception as e:
            error_msg = f'Failed to set AWS context: {str(e)}'
            log_with_request_id(ctx, LogLevel.ERROR, error_msg)
            return CallToolResult(
                isError=True,
                content=[TextContent(type='text', text=error_msg)],
            )
