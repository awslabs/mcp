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

"""CloudWatch metrics guidance handler for the EKS MCP Server."""

import json
import os
from awslabs.eks_mcp_server.logging_helper import LogLevel, log_with_request_id
from awslabs.eks_mcp_server.models import MetricsGuidanceResponse
from enum import Enum
from loguru import logger
from mcp.server.fastmcp import Context
from mcp.types import TextContent
from pydantic import Field
from typing import Any, Dict


class ResourceType(Enum):
    """Enum for supported resource types in CloudWatch metrics guidance."""

    CLUSTER = 'cluster'
    NODE = 'node'
    POD = 'pod'
    NAMESPACE = 'namespace'
    SERVICE = 'service'


class CloudWatchMetricsHandler:
    """Handler for CloudWatch metrics guidance tools in the EKS MCP Server.

    This class provides tools for accessing CloudWatch metrics guidance
    for different Kubernetes resource types in EKS clusters.
    """

    def __init__(self, mcp):
        """Initialize the CloudWatch metrics guidance handler.

        Args:
            mcp: The MCP server instance
        """
        self.mcp = mcp
        self.metrics_guidance = self._load_metrics_guidance()

        # Register the tool
        self.mcp.tool(name='get_eks_metrics_guidance')(self.get_eks_metrics_guidance)

    def _load_metrics_guidance(self) -> Dict[str, Any]:
        """Load metrics guidance from JSON file.

        Returns:
            Dict containing metrics guidance data
        """
        try:
            metrics_guidance_path = os.path.join(
                os.path.dirname(__file__), 'data', 'eks_cloudwatch_metrics_guidance.json'
            )
            with open(metrics_guidance_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f'Failed to load EKS CloudWatch metrics guidance: {str(e)}')
            return {}

    async def get_eks_metrics_guidance(
        self,
        ctx: Context,
        resource_type: str = Field(
            ...,
            description='Type of resource to get metrics for (cluster, node, pod, namespace, service)',
        ),
    ) -> MetricsGuidanceResponse:
        """Get CloudWatch metrics guidance for specific resource types in EKS clusters.

        This tool provides information about available CloudWatch metrics that are in the `ContainerInsights` naemspace for different resource types
        in EKS clusters, including metric names, dimensions, and descriptions to help with monitoring and troubleshooting.
        It's particularly useful for determining the correct dimensions to use with the get_cloudwatch_metrics tool.

        ## Response Information
        The response includes a list of metrics with their names, descriptions, and required dimensions
        for the specified resource type.

        ## Usage Tips
        - Use this tool before calling get_cloudwatch_metrics to determine the correct dimensions
        - For pod metrics, note that FullPodName has a random suffix while PodName doesn't
        - Different metrics require different dimension combinations

        Args:
            ctx: MCP context
            resource_type: Type of resource to get metrics for (cluster, node, pod, namespace, service)

        Returns:
            List of metrics with their details
        """
        # Validate resource type
        try:
            # Try to get the enum value by name (case-insensitive)
            ResourceType(resource_type.lower())
        except ValueError:
            valid_resource_types = [rt.value for rt in ResourceType]
            error_message = (
                f'Invalid resource type: {resource_type}. Must be one of {valid_resource_types}'
            )
            log_with_request_id(ctx, LogLevel.ERROR, error_message)

            return MetricsGuidanceResponse(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
                resource_type=resource_type,
                metrics=[],
            )

        metrics = self.metrics_guidance.get(resource_type.lower(), {}).get('metrics', [])
        resource_type_lower = resource_type.lower()

        log_with_request_id(
            ctx,
            LogLevel.INFO,
            f'Retrieved {len(metrics)} metrics for resource type {resource_type_lower}',
        )

        return MetricsGuidanceResponse(
            isError=False,
            content=[
                TextContent(
                    type='text',
                    text=f'Successfully retrieved {len(metrics)} metrics for resource type {resource_type_lower}',
                )
            ],
            resource_type=resource_type_lower,
            metrics=metrics,
        )
