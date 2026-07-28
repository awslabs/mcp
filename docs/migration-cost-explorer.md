# Migration Guide: Cost Explorer MCP Server to Billing and Cost Management MCP Server

This guide helps you migrate from `awslabs.cost-explorer-mcp-server` to the [Billing and Cost Management MCP Server](https://github.com/awslabs/mcp/tree/main/src/billing-cost-management-mcp-server).

## Why We're Deprecating

The Billing and Cost Management MCP Server is a superset of the Cost Explorer MCP Server. It includes all Cost Explorer functionality plus Budgets, Cost Anomaly Detection, Savings Plans, Reserved Instances, Compute Optimizer, Storage Lens, Free Tier Usage, Billing Conductor, BCM Pricing Calculator, and AWS Pricing tools.

## Installing the Replacement

### Configuration

```json
{
  "mcpServers": {
    "awslabs.billing-cost-management-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.billing-cost-management-mcp-server@latest"],
      "env": {
        "AWS_PROFILE": "your-aws-profile",
        "AWS_REGION": "us-east-1",
        "FASTMCP_LOG_LEVEL": "ERROR"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

## Tool-by-Tool Migration

### get_today_date

**Cost Explorer server:** Returns current date for relative date calculations.

**Billing server:** The `cost-explorer` tool handles date context internally. No separate date tool needed.

### get_dimension_values

**Cost Explorer server:** Retrieves available values for Cost Explorer dimensions (SERVICE, REGION, etc.).

**Billing server:** Available through the `cost-explorer` tool, which wraps all Cost Explorer API operations including `GetDimensionValues`.

### get_tag_values

**Cost Explorer server:** Retrieves available tag values for a specific tag key.

**Billing server:** Available through the `cost-explorer` tool via `GetTags`.

### get_cost_and_usage

**Cost Explorer server:** Core cost and usage data retrieval with filtering and grouping.

**Billing server:** Available through the `cost-explorer` tool via `GetCostAndUsage`. Same parameters and behavior.

### get_cost_and_usage_comparisons

**Cost Explorer server:** Compares costs between two time periods.

**Billing server:** Available through the `cost-comparison` tool, which provides `GetCostAndUsageComparisons`.

### get_cost-comparison_drivers

**Cost Explorer server:** Analyzes top 10 cost change drivers between periods.

**Billing server:** Available through the `cost-comparison` tool, which provides `GetCostComparisonDrivers`.

### get_cost_forecast

**Cost Explorer server:** Generates cost forecasts based on historical usage.

**Billing server:** Available through the `cost-explorer` tool via `GetCostForecast`.

## New Capabilities in the Billing Server

The Billing and Cost Management server provides many tools the Cost Explorer server did not have:

| Tool | Description |
|------|-------------|
| `budgets` | AWS Budgets management and monitoring |
| `cost-anomaly` | Cost anomaly detection and analysis |
| `cost-optimization` | Centralized cost optimization recommendations |
| `compute-optimizer` | EC2, Lambda, EBS, RDS, ECS right-sizing recommendations |
| `ri-performance` | Reserved Instance coverage and utilization analysis |
| `sp-performance` | Savings Plans coverage and utilization analysis |
| `free-tier-usage` | Free tier usage tracking |
| `aws-pricing` | AWS service pricing lookups |
| `storage-lens` | S3 Storage Lens analytics via Athena |
| `bcm-pricing-calc` | BCM Pricing Calculator for cost estimation |
| `session-sql` | SQL queries against cost data |

## Summary of Gaps

All Cost Explorer MCP Server functionality is fully covered by the Billing and Cost Management MCP Server. There are no gaps.

| Old Tool | New Tool | Notes |
|----------|----------|-------|
| `get_today_date` | Built into `cost-explorer` | No separate tool needed |
| `get_dimension_values` | `cost-explorer` | Same API, unified tool |
| `get_tag_values` | `cost-explorer` | Same API, unified tool |
| `get_cost_and_usage` | `cost-explorer` | Same API, unified tool |
| `get_cost_and_usage_comparisons` | `cost-comparison` | Same API, dedicated tool |
| `get_cost-comparison_drivers` | `cost-comparison` | Same API, dedicated tool |
| `get_cost_forecast` | `cost-explorer` | Same API, unified tool |

## Removing the Old Server

Once you've verified the replacement meets your needs:

1. Remove `awslabs.cost-explorer-mcp-server` from your MCP configuration
2. Uninstall the package: `pip uninstall awslabs.cost-explorer-mcp-server`
3. The old package will remain on PyPI but will not receive updates
