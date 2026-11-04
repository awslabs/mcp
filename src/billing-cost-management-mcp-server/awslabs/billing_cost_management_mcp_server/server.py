#!/usr/bin/env python3
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
"""AWS Billing and Cost Management MCP Server.

A Model Context Protocol (MCP) server that provides tools for Billing and Cost Management
by wrapping boto3 SDK functions for AWS Billing and Cost Management services.
"""

import os
import sys


if __name__ == '__main__':
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(os.path.dirname(current_dir))
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)

import mcp.types as mcp_types
from awslabs.billing_cost_management_mcp_server.tools.aws_pricing_tools import aws_pricing_server
from awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools import (
    bcm_pricing_calculator_server,
)
from awslabs.billing_cost_management_mcp_server.tools.billing_conductor_tools import (
    billing_conductor_server,
)
from awslabs.billing_cost_management_mcp_server.tools.billing_preferences_tools import (
    billing_preferences_server,
)
from awslabs.billing_cost_management_mcp_server.tools.budget_tools import budget_server
from awslabs.billing_cost_management_mcp_server.tools.business_support_tools import (
    business_support_server,
)
from awslabs.billing_cost_management_mcp_server.tools.bvs_tools import bvs_server
from awslabs.billing_cost_management_mcp_server.tools.compute_optimizer_automation_tools import (
    compute_optimizer_automation_server,
)
from awslabs.billing_cost_management_mcp_server.tools.compute_optimizer_tools import (
    compute_optimizer_server,
)
from awslabs.billing_cost_management_mcp_server.tools.cost_allocation_tags_tools import (
    cost_allocation_tags_server,
)
from awslabs.billing_cost_management_mcp_server.tools.cost_anomaly_tools import cost_anomaly_server
from awslabs.billing_cost_management_mcp_server.tools.cost_category_tools import (
    cost_category_server,
)
from awslabs.billing_cost_management_mcp_server.tools.cost_comparison_tools import (
    cost_comparison_server,
)
from awslabs.billing_cost_management_mcp_server.tools.cost_explorer_tools import (
    cost_explorer_server,
)
from awslabs.billing_cost_management_mcp_server.tools.cost_optimization_hub_tools import (
    cost_optimization_hub_server,
)
from awslabs.billing_cost_management_mcp_server.tools.credits_tools import credits_server
from awslabs.billing_cost_management_mcp_server.tools.enterprise_support_tools import (
    enterprise_support_server,
)
from awslabs.billing_cost_management_mcp_server.tools.free_tier_usage_tools import (
    free_tier_usage_server,
)
from awslabs.billing_cost_management_mcp_server.tools.invoice_units_tools import (
    invoice_units_server,
)
from awslabs.billing_cost_management_mcp_server.tools.invoicing_tools import invoicing_server
from awslabs.billing_cost_management_mcp_server.tools.procurement_preferences_tools import (
    procurement_preferences_server,
)
from awslabs.billing_cost_management_mcp_server.tools.recommendation_details_tools import (
    recommendation_details_server,
)
from awslabs.billing_cost_management_mcp_server.tools.ri_performance_tools import (
    ri_performance_server,
)
from awslabs.billing_cost_management_mcp_server.tools.sp_explorer_tools import (
    sp_explorer_server,
)
from awslabs.billing_cost_management_mcp_server.tools.sp_performance_tools import (
    sp_performance_server,
)
from awslabs.billing_cost_management_mcp_server.tools.sp_purchase_analyzer_tools import (
    sp_purchase_analyzer_server,
)
from awslabs.billing_cost_management_mcp_server.tools.sp_recommendation_tools import (
    sp_recommendation_server,
)
from awslabs.billing_cost_management_mcp_server.tools.storage_lens_tools import storage_lens_server
from awslabs.billing_cost_management_mcp_server.tools.unified_sql_tools import unified_sql_server
from awslabs.billing_cost_management_mcp_server.utilities.error_contract import (
    add_retry_guidance,
)
from awslabs.billing_cost_management_mcp_server.utilities.logging_utils import get_logger
from fastmcp import FastMCP
from fastmcp.server.middleware import Middleware
from fastmcp.tools import ToolResult


# Configure logger for server
logger = get_logger(__name__)


class _ErrorToolResult(ToolResult):
    """A ToolResult that serializes to a CallToolResult with is_error=True."""

    def to_mcp_result(self):
        return mcp_types.CallToolResult(
            content=self.content,
            structured_content=self.structured_content,
            is_error=True,
            _meta=self.meta,
        )


class ErrorSignalingMiddleware(Middleware):
    """Middleware that sets is_error=True when a tool returns an error response.

    Per the MCP spec, tools should signal errors via is_error on CallToolResult.
    This middleware intercepts tool results that contain status='error' in their
    response body and returns a result with is_error=True, preserving the original
    content and structured_content for backward compatibility.

    It also adds retry_strategy (and hint, when one applies) derived from error_type,
    unless the tool already set them (see utilities/error_contract.py).
    """

    async def on_call_tool(self, context, call_next):
        """Intercept tool results and set is_error for error responses."""
        result = await call_next(context)
        if (
            isinstance(result, ToolResult)
            and isinstance(result.structured_content, dict)
            and result.structured_content.get('status') == 'error'
        ):
            structured_content = add_retry_guidance(result.structured_content)
            content = result.content
            # When content is the serialized structured_content (the case for dict
            # returns), re-derive it so the text the model reads carries the same fields.
            if (
                structured_content is not result.structured_content
                and content == ToolResult(structured_content=result.structured_content).content
            ):
                content = ToolResult(structured_content=structured_content).content
            return _ErrorToolResult(
                content=content,
                structured_content=structured_content,
                meta=result.meta,
            )
        return result


# Main MCP server instance
mcp = FastMCP(
    name='billing-cost-management-mcp',
    instructions="""AWS Billing and Cost Management MCP Server - Provides AWS cost optimization tools and prompts through MCP.

Unless the user or the host's instructions specify otherwise:
1. Use the UnblendedCost metric. If `metrics` is omitted, the tool returns UnblendedCost
2. Report net cost, with credits and refunds included
3. Be concise and focus on essential information first
4. For optimization queries, lead with the highest-impact recommendations; when truncating, state how many were omitted and their combined savings

For financial analysis:
1. Start with a high-level view of costs using cost-explorer with the SERVICE dimension
2. Look for cost optimization opportunities with cost-optimization or compute-optimizer
3. For S3-specific optimizations, use storage-lens
4. For budget monitoring, use budgets
5. For anomaly detection, use cost-anomaly; use cost-anomaly-monitors to find monitor ARNs and see who is alerted

For optimization recommendations:
1. Use cost-optimization for cost savings recommendations across services, including idle resources, rightsizing, Graviton migration, and Savings Plans / Reserved Instances purchases.
2. Use cost-optimization `get_recommendation` for one Cost Optimization Hub recommendation; use rec-details only when Compute Optimizer and Cost Explorer enrichment is wanted.
3. Use compute-optimizer for performance-based recommendations for compute resources such as EC2, ECS, EBS, Lambda, RDS, and Auto Scaling groups.
4. Use ri-performance and sp-performance to analyze existing Reserved Instances and Savings Plans.

For multi-account environments:
- Include the LINKED_ACCOUNT dimension in cost-explorer queries
- compute-optimizer takes `account_ids` as a JSON array with one account ID per call; make one call per account
- cost-optimization takes accounts in `filters`, e.g. '{"accountIds": ["123456789012"]}'; its top-level `account_id` applies only to `list_enrollment_statuses`
""",
)

# Register middleware to signal errors via isError per MCP spec
mcp.add_middleware(ErrorSignalingMiddleware())


def register_prompts():
    """Register all prompts with the MCP server."""
    try:
        from awslabs.billing_cost_management_mcp_server.prompts import register_all_prompts

        register_all_prompts(mcp)
        logger.info('Registered all prompts')
    except Exception as e:
        logger.error(f'Error registering prompts: {e}')


def setup():
    """Initialize the MCP server by mounting all tool servers."""
    mcp.mount(cost_explorer_server)
    mcp.mount(compute_optimizer_server)
    mcp.mount(compute_optimizer_automation_server)
    mcp.mount(cost_optimization_hub_server)
    mcp.mount(storage_lens_server)
    mcp.mount(aws_pricing_server)
    mcp.mount(bcm_pricing_calculator_server)
    mcp.mount(budget_server)
    mcp.mount(cost_anomaly_server)
    mcp.mount(cost_comparison_server)
    mcp.mount(free_tier_usage_server)
    mcp.mount(recommendation_details_server)
    mcp.mount(ri_performance_server)
    mcp.mount(sp_performance_server)
    mcp.mount(sp_explorer_server)
    mcp.mount(sp_recommendation_server)
    mcp.mount(sp_purchase_analyzer_server)
    mcp.mount(unified_sql_server)
    mcp.mount(billing_conductor_server)
    mcp.mount(bvs_server)
    mcp.mount(cost_allocation_tags_server)
    mcp.mount(cost_category_server)
    mcp.mount(invoicing_server)
    mcp.mount(invoice_units_server)
    mcp.mount(procurement_preferences_server)
    mcp.mount(credits_server)
    mcp.mount(billing_preferences_server)
    mcp.mount(enterprise_support_server)
    mcp.mount(business_support_server)

    register_prompts()

    logger.info('AWS Billing and Cost Management MCP Server initialized successfully')


def main():
    """Main entry point for the server."""
    # Run the setup function to initialize the server
    setup()

    # Start the MCP server
    mcp.run()


if __name__ == '__main__':
    main()
