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


# Add necessary directories to Python path when running directly
if __name__ == '__main__':
    # Add the parent directory to sys.path (up two levels only since we're in billing-cost-management-mcp-server)
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

# Import tool servers directly - always use absolute imports for running as script
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
from fastmcp import FastMCP


# Main MCP server instance
mcp = FastMCP(
    name='billing-cost-management-mcp',
    instructions="""AWS Billing and Cost Management MCP Server - Provides AWS cost optimization tools and prompts through MCP.

When using these tools, always:
1. Provide explanations starting with "EXPLANATION:" before tool usage
2. Use UnblendedCost metric by default
3. Exclude Credits and Refunds by default
4. Be concise and focus on essential information first
5. For optimization queries, focus on top 2-3 highest impact recommendations

Available components:

TOOLS:
- cost_explorer: Historical cost and usage data with flexible filtering
- compute_optimizer: Recommendations for AWS compute resources like EC2, Lambda, ASG
- cost_optimization_hub: Cost optimization recommendations across AWS services
- storage_lens_run_query: Query S3 Storage Lens metrics data using Athena SQL
- athena_cur: Query Cost and Usage Report data through Athena
- pricing: Access AWS service pricing information
- budget: Retrieve AWS budget information
- cost_anomaly: Identify cost anomalies in AWS accounts
- cost_comparison: Compare costs between time periods
- free_tier_usage: Monitor AWS Free Tier usage
- get_recommendation_details: Get enhanced cost optimization recommendations
- ri_performance: Analyze Reserved Instance coverage and utilization
- sp_performance: Analyze Savings Plans coverage and utilization
- session_sql: Execute SQL queries on the session database

PROMPTS:
- savings_plans: Analyzes AWS usage and identifies opportunities for Savings Plans purchases
- graviton_migration: Analyzes EC2 instances and identifies opportunities to migrate to AWS Graviton processors

For financial analysis:
1. Start with a high-level view of costs using cost_explorer with SERVICE dimension
2. Look for cost optimization opportunities with compute_optimizer or cost_optimization_hub
3. For S3-specific optimizations, use storage_lens_run_query
4. For budget monitoring, use the budget tool
5. For anomaly detection, use the cost_anomaly tool

For cost optimization recommendations:
1. Use cost_optimization_hub to get broad recommendations across services
2. Use compute_optimizer for compute-specific recommendations
3. Use get_recommendation_details for enhanced recommendation analysis
4. Use ri_performance and sp_performance to analyze purchase programs

For multi-account environments:
- Include the LINKED_ACCOUNT dimension in cost_explorer queries
- Specify accountIds parameter for compute_optimizer and cost_optimization_hub tools
""",
)


async def register_prompts():
    """Register all prompts with the MCP server."""
    try:
        # Use absolute import instead of relative import
        from awslabs.billing_cost_management_mcp_server.prompts import register_all_prompts

        register_all_prompts(mcp)
        print('Registered all prompts')
    except Exception as e:
        print(f'Error registering prompts: {e}')


async def setup():
    """Initialize the MCP server by importing all tool servers."""
    # Import all tool servers
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

    # Register all prompts
    await register_prompts()

    # Log server initialization
    print('AWS Billing and Cost Management MCP Server initialized successfully')
    print('\nAvailable tools:')
    print('- cost_explorer')
    print('- compute_optimizer')
    print('- cost_optimization_hub')
    print('- storage_lens_run_query')
    print('- pricing')
    print('- budget')
    print('- cost_anomaly')
    print('- cost_comparison')
    print('- free_tier_usage')
    print('- get_recommendation_details')
    print('- ri_performance')
    print('- sp_performance')
    print('- session_sql')

    print('\nAvailable prompts:')
    print('- cost_analysis')
    print('- cost_optimization_recommendations')
    print('- reserved_capacity_analysis')
    print('- cost_anomaly_investigation')
    print('- budget_planning')
    print('- free_tier_optimization')
    print('- cost_breakdown_analysis')
    print('- cost_trend_analysis')
    print('- cur_sql_analysis')
    print('- multi_account_cost_analysis')


def main():
    """Main entry point for the server."""
    # Run the setup function to initialize the serve
    asyncio.run(setup())

    # Start the MCP server
    mcp.run()


if __name__ == '__main__':
    main()
