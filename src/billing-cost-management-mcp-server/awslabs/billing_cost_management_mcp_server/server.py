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

import asyncio
import os
import sys


if __name__ == '__main__':
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(os.path.dirname(current_dir))
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)

from awslabs.billing_cost_management_mcp_server.tools.aws_pricing_tools import aws_pricing_server
from awslabs.billing_cost_management_mcp_server.tools.budget_tools import budget_server
from awslabs.billing_cost_management_mcp_server.tools.compute_optimizer_tools import (
    compute_optimizer_server,
)
from awslabs.billing_cost_management_mcp_server.tools.cost_anomaly_tools import cost_anomaly_server
from awslabs.billing_cost_management_mcp_server.tools.cost_comparison_tools import (
    cost_comparison_server,
)
from awslabs.billing_cost_management_mcp_server.tools.cost_explorer_tools import (
    cost_explorer_server,
)
from awslabs.billing_cost_management_mcp_server.tools.cost_optimization_hub_tools import (
    cost_optimization_hub_server,
)
from awslabs.billing_cost_management_mcp_server.tools.free_tier_usage_tools import (
    free_tier_usage_server,
)
from awslabs.billing_cost_management_mcp_server.tools.recommendation_details_tools import (
    recommendation_details_server,
)
from awslabs.billing_cost_management_mcp_server.tools.ri_performance_tools import (
    ri_performance_server,
)
from awslabs.billing_cost_management_mcp_server.tools.sp_performance_tools import (
    sp_performance_server,
)
from awslabs.billing_cost_management_mcp_server.tools.storage_lens_tools import storage_lens_server
from awslabs.billing_cost_management_mcp_server.tools.unified_sql_tools import unified_sql_server
from awslabs.billing_cost_management_mcp_server.utilities.logging_utils import get_logger
from fastmcp import FastMCP


# Configure logger for server
logger = get_logger(__name__)


# Main MCP server instance
mcp = FastMCP(
    name='billing-cost-management-mcp',
    instructions="""AWS Billing and Cost Management MCP Server - Provides AWS cost optimization tools and prompts through MCP.

When using these tools, always:
1. Use UnblendedCost metric by default
2. Exclude Credits and Refunds by default
3. Be concise and focus on essential information first
4. For optimization queries, focus on top 2-3 highest impact recommendations

Available components:

TOOLS:
- cost-explorer: Historical cost and usage data with flexible filtering
- compute-optimizer: Performance optimization recommendations to identify under provisioned AWS compute resources like EC2, Lambda, ASG, RDS, ECS
- cost-optimization: Cost optimization recommendations across AWS services
- storage-lens: Query S3 Storage Lens metrics data using Athena SQL
- athena-cur: Query Cost and Usage Report data through Athena
- pricing: Access AWS service pricing information
- budget: Retrieve AWS budget information
- cost-anomaly: Identify cost anomalies in AWS accounts
- cost-comparison: Compare costs between time periods
- free-tier-usage: Monitor AWS Free Tier usage
- rec-details: Get enhanced cost optimization recommendations
- ri-performance: Analyze Reserved Instance coverage and utilization
- sp-performance: Analyze Savings Plans coverage and utilization
- session-sql: Execute SQL queries on the session database

PROMPTS:
- savings_plans: Analyzes AWS usage and identifies opportunities for Savings Plans purchases
- graviton_migration: Analyzes EC2 instances and identifies opportunities to migrate to AWS Graviton processors

For financial analysis:
1. Start with a high-level view of costs using cost-explorer with SERVICE dimension
2. Look for cost optimization opportunities with compute-optimizer or cost-optimization
3. For S3-specific optimizations, use storage-lens
4. For budget monitoring, use the budget tool
5. For anomaly detection, use the cost-anomaly tool

For optimization recommendations:
1. Use cost-optimization to get recommendations for cost optimization across services. This includes including Idle resources, Rightsizing for savings, RI/SP.
2. Use rec-details for enhanced recommendation analysis for specific cost optimization recommendations.
3. Use compute-optimizer to get performance optimization recommendations for compute resources such as EC2, ECS, EBS, Lambda, RDS, ASG.
4. Use ri-performance and sp-performance to analyze purchase programs

For multi-account environments:
- Include the LINKED_ACCOUNT dimension in cost_explorer queries
- Specify accountIds parameter for compute-optimizer and cost-optimization tools
""",
)


async def register_prompts():
    """Register all prompts with the MCP server."""
    try:
        from awslabs.billing_cost_management_mcp_server.prompts import register_all_prompts

        register_all_prompts(mcp)
        logger.info('Registered all prompts')
    except Exception as e:
        logger.error(f'Error registering prompts: {e}')


async def setup():
    """Initialize the MCP server by importing all tool servers."""
    await mcp.import_server(cost_explorer_server)
    await mcp.import_server(compute_optimizer_server)
    await mcp.import_server(cost_optimization_hub_server)
    await mcp.import_server(storage_lens_server)
    await mcp.import_server(aws_pricing_server)
    await mcp.import_server(budget_server)
    await mcp.import_server(cost_anomaly_server)
    await mcp.import_server(cost_comparison_server)
    await mcp.import_server(free_tier_usage_server)
    await mcp.import_server(recommendation_details_server)
    await mcp.import_server(ri_performance_server)
    await mcp.import_server(sp_performance_server)
    await mcp.import_server(unified_sql_server)

    await register_prompts()

    logger.info('AWS Billing and Cost Management MCP Server initialized successfully')

    logger.info('Available tools:')
    tools = [
        'cost-explorer',
        'compute-optimizer',
        'cost-optimization',
        'storage-lens',
        'pricing',
        'budget',
        'cost-anomaly',
        'cost-comparison',
        'free-tier-usage',
        'rec-details',
        'ri-performance',
        'sp-performance',
        'session-sql',
    ]
    for tool in tools:
        logger.info(f'- {tool}')

    logger.info('Available prompts:')
    prompts = ['savings_plans_analysis', 'graviton_analysis']
    for prompt in prompts:
        logger.info(f'- {prompt}')


def main():
    """Main entry point for the server."""
    # Run the setup function to initialize the server
    asyncio.run(setup())

    # Start the MCP server
    mcp.run()


if __name__ == '__main__':
    main()
