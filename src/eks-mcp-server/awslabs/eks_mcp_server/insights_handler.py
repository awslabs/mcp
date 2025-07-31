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

"""Insights handler for the EKS MCP Server."""

from awslabs.eks_mcp_server.aws_helper import AwsHelper
from awslabs.eks_mcp_server.logging_helper import LogLevel, log_with_request_id
from awslabs.eks_mcp_server.models import (
    EksInsightItem,
    EksInsightsResponse,
    EksInsightStatus,
)
from datetime import datetime
from mcp.server.fastmcp import Context
from mcp.types import TextContent
from pydantic import Field
from typing import Any, Optional


class InsightsHandler:
    """Handler for Amazon EKS Insights.

    This class provides tools for retrieving and analyzing insights about
    EKS cluster configuration and upgrade readiness.
    """

    def __init__(
        self,
        mcp,
        allow_sensitive_data_access: bool = False,
    ):
        """Initialize the Insights handler.

        Args:
            mcp: The MCP server instance
            allow_sensitive_data_access: Whether to allow access to sensitive data (default: False)
        """
        self.mcp = mcp
        self.allow_sensitive_data_access = allow_sensitive_data_access

        # Register tools
        self.mcp.tool(name='get_eks_insights')(self.get_eks_insights)

        # Initialize AWS clients
        self.eks_client = AwsHelper.create_boto3_client('eks')

    # EKS Insights tool
    async def get_eks_insights(
        self,
        ctx: Context,
        cluster_name: str = Field(..., description='Name of the EKS cluster'),
        insight_id: Optional[str] = Field(
            None,
            description='ID of a specific insight to get detailed information for. If provided, returns detailed information about this specific insight.',
        ),
        category: Optional[str] = Field(
            None,
            description='Filter insights by category (e.g., "MISCONFIGURATION" or "UPGRADE_READINESS")',
        ),
        next_token: Optional[str] = Field(
            None,
            description='Token for pagination to get the next set of results',
        ),
    ) -> EksInsightsResponse:
        """Get EKS Insights for cluster configuration and upgrade readiness.

        This tool retrieves Amazon EKS Insights that identify potential issues with
        your EKS cluster. These insights help identify both cluster configuration issues
        and upgrade readiness concerns that might affect hybrid nodes functionality.

        Amazon EKS provides two types of insights:
        - MISCONFIGURATION insights: Identify misconfigurations in your EKS cluster setup
        - UPGRADE_READINESS insights: Identify issues that could prevent successful cluster upgrades

        When used without an insight_id, it returns a list of all insights.
        When used with an insight_id, it returns detailed information about
        that specific insight, including recommendations.

        ## Requirements
        - The server must be run with the `--allow-sensitive-data-access` flag

        ## Response Information
        The response includes insight details such as status, description, and
        recommendations for addressing identified issues.

        ## Usage Tips
        - Review MISCONFIGURATION insights to identify cluster misconfigurations
        - Check UPGRADE_READINESS insights before upgrading your cluster
        - Pay special attention to insights with FAILING status
        - Focus on insights related to node and network configuration for hybrid nodes

        Args:
            ctx: MCP context
            cluster_name: Name of the EKS cluster
            insight_id: Optional ID of a specific insight to get detailed information for
            category: Optional category to filter insights by (e.g., "MISCONFIGURATION" or "UPGRADE_READINESS")
            next_token: Optional token for pagination to get the next set of results

        Returns:
            EksInsightsResponse with insights information
        """
        # Extract values from Field objects before passing them to the implementation method
        cluster_name_value = cluster_name
        insight_id_value = insight_id
        category_value = category
        next_token_value = next_token

        # Delegate to the implementation method with extracted values
        return await self._get_eks_insights_impl(
            ctx, cluster_name_value, insight_id_value, category_value, next_token_value
        )

    async def _get_eks_insights_impl(
        self,
        ctx: Context,
        cluster_name: str,
        insight_id: Optional[str] = None,
        category: Optional[str] = None,
        next_token: Optional[str] = None,
    ) -> EksInsightsResponse:
        """Internal implementation of get_eks_insights."""
        try:
            # Always use the default EKS client
            eks_client = self.eks_client

            # Determine operation mode based on whether insight_id is provided
            detail_mode = insight_id is not None

            if detail_mode:
                # Get details for a specific insight
                return await self._get_insight_detail(
                    ctx, eks_client, cluster_name, insight_id, next_token
                )
            else:
                # List all insights with optional category filter
                return await self._list_insights(
                    ctx, eks_client, cluster_name, category, next_token
                )

        except Exception as e:
            error_message = f'Error processing EKS insights request: {str(e)}'
            log_with_request_id(ctx, LogLevel.ERROR, error_message)
            return EksInsightsResponse(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
                cluster_name=cluster_name,
                insights=[],
                next_token=None,
                detail_mode=(insight_id is not None),
            )

    async def _get_insight_detail(
        self,
        ctx: Context,
        eks_client,
        cluster_name: str,
        insight_id: str,
        next_token: Optional[str] = None,
    ) -> EksInsightsResponse:
        """Get details for a specific EKS insight."""
        log_with_request_id(
            ctx,
            LogLevel.INFO,
            f'Getting details for insight {insight_id} in cluster {cluster_name}',
        )

        try:
            response = eks_client.describe_insight(id=insight_id, clusterName=cluster_name)

            # Extract and format the insight details
            if 'insight' in response:
                insight_data = response['insight']

                # Create insight status object
                status_obj = EksInsightStatus(
                    status=insight_data.get('insightStatus', {}).get('status', 'UNKNOWN'),
                    reason=insight_data.get('insightStatus', {}).get('reason', ''),
                )

                # Handle datetime objects for timestamps
                last_refresh_time = insight_data.get('lastRefreshTime', 0)
                if isinstance(last_refresh_time, datetime):
                    last_refresh_time = last_refresh_time.timestamp()

                last_transition_time = insight_data.get('lastTransitionTime', 0)
                if isinstance(last_transition_time, datetime):
                    last_transition_time = last_transition_time.timestamp()

                # Convert insight to EksInsightItem format
                insight_item = EksInsightItem(
                    id=insight_data.get('id', ''),
                    name=insight_data.get('name', ''),
                    category=insight_data.get('category', ''),
                    kubernetes_version=insight_data.get('kubernetesVersion'),
                    last_refresh_time=last_refresh_time,
                    last_transition_time=last_transition_time,
                    description=insight_data.get('description', ''),
                    insight_status=status_obj,
                    recommendation=insight_data.get('recommendation'),
                    additional_info=insight_data.get('additionalInfo', {}),
                    resources=insight_data.get('resources', []),
                    category_specific_summary=insight_data.get('categorySpecificSummary', {}),
                )

                success_message = f'Successfully retrieved details for insight {insight_id}'
                return EksInsightsResponse(
                    isError=False,
                    content=[TextContent(type='text', text=success_message)],
                    cluster_name=cluster_name,
                    insights=[insight_item],
                    next_token=None,  # No pagination for detail view
                    detail_mode=True,
                )
            else:
                error_message = f'No insight details found for ID {insight_id}'
                log_with_request_id(ctx, LogLevel.WARNING, error_message)
                return EksInsightsResponse(
                    isError=True,
                    content=[TextContent(type='text', text=error_message)],
                    cluster_name=cluster_name,
                    insights=[],
                    next_token=None,
                    detail_mode=True,
                )

        except Exception as e:
            error_message = f'Error retrieving insight details: {str(e)}'
            log_with_request_id(ctx, LogLevel.ERROR, error_message)
            return EksInsightsResponse(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
                cluster_name=cluster_name,
                insights=[],
                next_token=None,
                detail_mode=True,
            )

    async def _list_insights(
        self,
        ctx: Context,
        eks_client,
        cluster_name: str,
        category: Optional[str] = None,
        next_token: Optional[str] = None,
    ) -> EksInsightsResponse:
        """List EKS insights for a cluster with optional category filtering."""
        log_with_request_id(ctx, LogLevel.INFO, f'Listing insights for cluster {cluster_name}')

        try:
            # Build the list_insights parameters
            list_params: dict[str, Any] = {'clusterName': cluster_name}

            # Add category filter if provided
            if category:
                log_with_request_id(
                    ctx, LogLevel.INFO, f'Filtering insights by category: {category}'
                )
                # Use the filter parameter with the correct structure
                list_params['filter'] = {'categories': [category]}

            # Add next_token if provided
            if next_token:
                log_with_request_id(
                    ctx, LogLevel.INFO, 'Using pagination token for next page of results'
                )
                list_params['nextToken'] = next_token

            response = eks_client.list_insights(**list_params)

            # Extract and format the insights
            insight_items = []

            if 'insights' in response:
                for insight_data in response['insights']:
                    # Create insight status object
                    status_obj = EksInsightStatus(
                        status=insight_data.get('insightStatus', {}).get('status', 'UNKNOWN'),
                        reason=insight_data.get('insightStatus', {}).get('reason', ''),
                    )

                    # Handle datetime objects for timestamps
                    last_refresh_time = insight_data.get('lastRefreshTime', 0)
                    if isinstance(last_refresh_time, datetime):
                        last_refresh_time = last_refresh_time.timestamp()

                    last_transition_time = insight_data.get('lastTransitionTime', 0)
                    if isinstance(last_transition_time, datetime):
                        last_transition_time = last_transition_time.timestamp()

                    # Convert insight to EksInsightItem format
                    insight_item = EksInsightItem(
                        id=insight_data.get('id', ''),
                        name=insight_data.get('name', ''),
                        category=insight_data.get('category', ''),
                        kubernetes_version=insight_data.get('kubernetesVersion'),
                        last_refresh_time=last_refresh_time,
                        last_transition_time=last_transition_time,
                        description=insight_data.get('description', ''),
                        insight_status=status_obj,
                        # List mode doesn't include these fields
                        recommendation=None,
                        additional_info=None,
                        resources=None,
                        category_specific_summary=None,
                    )

                    insight_items.append(insight_item)

            success_message = (
                f'Successfully retrieved {len(insight_items)} insights for cluster {cluster_name}'
            )
            return EksInsightsResponse(
                isError=False,
                content=[TextContent(type='text', text=success_message)],
                cluster_name=cluster_name,
                insights=insight_items,
                next_token=response.get('nextToken'),
                detail_mode=False,
            )

        except Exception as e:
            error_message = f'Error listing insights: {str(e)}'
            log_with_request_id(ctx, LogLevel.ERROR, error_message)
            return EksInsightsResponse(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
                cluster_name=cluster_name,
                insights=[],
                next_token=None,
                detail_mode=False,
            )
