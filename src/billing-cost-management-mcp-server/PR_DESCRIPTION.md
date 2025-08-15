# Summary

The AWS Billing and Cost Management MCP Server is designed to make AWS billing data, cost management features, and financial insights easily accessible to Large Language Models (LLMs) through the Model Context Protocol (MCP). It wraps boto3 SDK functions for AWS billing and cost management services, allowing LLMs to directly interact with AWS financial tools for cost analysis, budgeting, anomaly detection, and optimization recommendations.

## Changes

A new MCP server under billing-cost-management-mcp-server added with the following structure:

* **awslabs/billing_cost_management_mcp_server/**: Main directory containing the MCP server implementation
  * **server.py**: Implements the MCP server
  * **tools/**: Directory containing all tool implementations
    * **aws_pricing_tools.py**: AWS Pricing API tools
    * **budget_tools.py**: AWS Budgets tools
    * **cost_anomaly_tools.py**: Cost Anomaly Detection tools
    * **cost_comparison_tools.py**: Cost comparison tools
    * **cost_explorer_tools.py**: Cost Explorer tools
    * **cost_optimization_hub_tools.py**: Cost Optimization Hub tools
    * **free_tier_usage_tools.py**: Free Tier Usage tools
    * **ri_performance_tools.py**: Reserved Instance tools
    * **sp_performance_tools.py**: Savings Plans tools
    * **storage_lens_tools.py**: Storage Lens tools
    * **unified_sql_tools.py**: SQL tools for session data
  * **prompts/**: Directory containing prompt templates for MCP clients
    * **savings_plans.py**: Prompt templates for Savings Plans recommendations
    * **graviton_migration.py**: Prompt templates for Graviton migration recommendations
  * **utilities/**: Directory containing shared utility functions
    * **aws_service_base.py**: Common AWS service utilities
  * **templates/**: Directory containing templates for recommendations
* **__init__.py**: Makes the project a proper Python package
* **tests/**: Contains integration and unit tests for the server
  * **tools/**: Tests for each tool implementation
  * **prompts/**: Tests for prompt templates

## User experience

Users get a new MCP server with tools and prompts to analyze AWS billing patterns, cost management data, and cost optimization recommendations. The server provides access to:

1. Cost Explorer data for analysis
2. Compute Optimizer recommendations
3. Cost Optimization Hub recommendations
4. Budget and anomaly detection tools
5. Reserved Instance and Savings Plans performance metrics
6. Storage Lens data for S3 optimization

All these capabilities are accessible to LLMs through the standardized MCP interface, enabling AI systems to provide comprehensive financial analysis, spending insights, budget management, and actionable cost optimization recommendations.

## Checklist

If your change doesn't seem to apply, please leave them unchecked.

- [x] I have reviewed the [contributing guidelines](https://github.com/awslabs/mcp/blob/main/CONTRIBUTING.md)
- [x] I have performed a self-review of this change
- [x] Changes have been tested
- [x] Changes are documented

## Is this a breaking change? (Y/N)
N

## Acknowledgment

By submitting this pull request, I confirm that you can use, modify, copy, and redistribute this contribution, under the terms of the [project license](https://github.com/awslabs/mcp/blob/main/LICENSE).
