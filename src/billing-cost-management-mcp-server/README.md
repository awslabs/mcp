# AWS Billing and Cost Management MCP Server

MCP server for accessing AWS Billing and Cost Management capabilities.

**Important Note**: This server accesses cost and usage data from AWS Billing and Cost Management APIs. All API calls are performed using the caller's AWS credentials and follow AWS service limits and quotas.

## Features

### AWS Free Tier

- **Free Tier optimization**: Monitor Free Tier usage and avoid unexpected charges

### AWS Cost and Usage Analysis

- **Cost Explorer insights**: Analyze historical and forecasted AWS costs with flexible grouping and filtering
- **Usage metrics analysis**: Track resource usage trends across your AWS environment
- **Budget monitoring**: Check existing budgets and their status against actual spending
- **Cost anomaly detection**: Identify unusual spending patterns and their root causes

### Cost Optimization Recommendations

- **Compute Optimizer recommendations**: Get right-sizing suggestions for EC2, Lambda, EBS, and more
- **Cost Optimization Hub**: Access cost-saving opportunities across your AWS environment

### Savings Plans and Reserved Instanaces

- **Reserved Instance planning**: Analyze RI coverage and receive purchase recommendations
- **Savings Plans guidance**: Get personalized Savings Plans recommendations based on usage patterns

### S3 Storage Lens Analysis

- **Storage metrics querying**: Run SQL queries against Storage Lens metrics data
- **Storage cost breakdown**: Analyze S3 storage costs by bucket, storage class, and region
- **Storage optimization opportunities**: Identify lifecycle policy opportunities and cost-saving measures

### Cost and Usage Comparison

- **Month-over-month comparisons**: Compare cost and usage between time periods with detailed breakdown
- **Multi-account analysis**: Analyze costs across multiple linked accounts
- **Cost driver identification**: Identify key factors driving cost changes

### Specialized Cost Optimization Prompts

- **Graviton migration analysis**: Guided analysis to identify EC2 instances suitable for AWS Graviton migration
- **Savings Plans analysis**: Structured recommendations for optimal Savings Plans purchases based on usage patterns

## Prerequisites

1. Install `uv` from [Astral](https://docs.astral.sh/uv/getting-started/installation/) or the [GitHub README](https://github.com/astral-sh/uv#installation)
2. Install Python 3.10 or newer using uv python install 3.10 (or a more recent version)
3. Set up AWS credentials with access to AWS services
   - You need an AWS account with appropriate permissions
   - Configure AWS credentials with `aws configure` or environment variables
   - Ensure your IAM role/user has permissions to access AWS Billing and Cost Management APIs

## Installation

| Cursor | VS Code |
|:------:|:-------:|
| [![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/en/install-mcp?name=awslabs.billing-cost-management-mcp-server&config=ewogICAgImNvbW1hbmQiOiAidXZ4IGF3c2xhYnMuYmlsbGluZy1jb3N0LW1hbmFnZW1lbnQtbWNwLXNlcnZlckBsYXRlc3QiLAogICAgImVudiI6IHsKICAgICAgIkZBU1RNQ1BfTE9HX0xFVkVMIjogIkVSUk9SIiwKICAgICAgIkFXU19QUk9GSUxFIjogInlvdXItYXdzLXByb2ZpbGUiLAogICAgICAiQVdTX1JFR0lPTiI6ICJ1cy1lYXN0LTEiCiAgICB9LAogICAgImRpc2FibGVkIjogZmFsc2UsCiAgICAiYXV0b0FwcHJvdmUiOiBbXQogIH0K) | [![Install on VS Code](https://img.shields.io/badge/Install_on-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=AWS%20Billing%20and%20Cost%20Management%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.billing-cost-management-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%2C%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |

### ⚡ Using uv

Configure the MCP server in your MCP client configuration (e.g., for Amazon Q Developer CLI, edit `~/.aws/amazonq/mcp.json`):


**For Linux/MacOS users:**

```json
{
  "mcpServers": {
    "awslabs.billing-cost-management-mcp-server": {
      "command": "uvx",
      "args": [
         "awslabs.billing-cost-management-mcp-server@latest"
      ],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR",
        "AWS_PROFILE": "your-aws-profile",
        "AWS_REGION": "us-east-1"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

**For Windows users:**

```json
{
  "mcpServers": {
    "awslabs.billing-cost-management-mcp-server": {
      "command": "uvx",
      "args": [
         "--from",
         "awslabs.billing-cost-management-mcp-server@latest",
         "awslabs.billing-cost-management-mcp-server.exe"
      ],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR",
        "AWS_PROFILE": "your-aws-profile",
        "AWS_REGION": "us-east-1"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

### Using Docker

Or docker after a successful `docker build -t awslabs/billing-cost-management-mcp-server .`:

```file
# fictitious `.env` file with AWS temporary credentials
AWS_ACCESS_KEY_ID=ASIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
AWS_SESSION_TOKEN=AQoEXAMPLEH4aoAH0gNCAPy...truncated...zrkuWJOgQs8IZZaIv2BXIa2R4Olgk
AWS_REGION=us-east-1
```

```json
{
  "mcpServers": {
    "awslabs.billing-cost-management-mcp-server": {
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "--interactive",
        "--env",
        "FASTMCP_LOG_LEVEL=ERROR",
        "--env-file",
        "/full/path/to/file/above/.env",
        "awslabs/billing-cost-management-mcp-server:latest"
      ],
      "env": {},
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

NOTE: Your credentials will need to be kept refreshed from your host

### Storage Lens Configuration

To use the Storage Lens functionality, you'll need to set the following environment variables:

- **`STORAGE_LENS_MANIFEST_LOCATION`**: S3 URI to your Storage Lens manifest file or folder (e.g., `s3://bucket-name/storage-lens/manifests/`)
- **`STORAGE_LENS_OUTPUT_LOCATION`** (optional): S3 location for Athena query results (defaults to the same bucket as the manifest with an `athena-results/` suffix)

Example configuration:

```json
"env": {
  "AWS_PROFILE": "your-aws-profile",
  "AWS_REGION": "us-east-1",
  "STORAGE_LENS_MANIFEST_LOCATION": "s3://your-bucket/storage-lens-data/",
  "STORAGE_LENS_OUTPUT_LOCATION": "s3://your-bucket/athena-results/"
}
```

### AWS Authentication

The MCP server requires specific AWS permissions and configuration:

#### Required Permissions

Your AWS IAM role or user needs permissions to access various AWS Billing and Cost Management APIs:

Cost Explorer:
- ce:GetReservationPurchaseRecommendation
- ce:GetReservationCoverage
- ce:GetReservationUtilization
- ce:GetSavingsPlansUtilization
- ce:GetSavingsPlansCoverage
- ce:GetSavingsPlansUtilizationDetails
- ce:GetSavingsPlansPurchaseRecommendation
- ce:GetCostAndUsageComparisons
- ce:GetCostComparisonDrivers
- ce:GetAnomalies
- ce:GetCostAndUsage
- ce:GetCostAndUsageComparisons
- ce:GetCostAndUsageWithResources
- ce:GetDimensionValues
- ce:GetCostForecast
- ce:GetUsageForecast
- ce:GetTags
- ce:GetCostCategories

Cost Optimization Hub:
- cost-optimization-hub:GetRecommendation
- cost-optimization-hub:ListRecommendations
- cost-optimization-hub:ListRecommendationSummaries

Compute Optimizer:
- compute-optimizer:GetAutoScalingGroupRecommendations
- compute-optimizer:GetEBSVolumeRecommendations
- compute-optimizer:GetEC2InstanceRecommendations
- compute-optimizer:GetECSServiceRecommendations
- compute-optimizer:GetRDSDatabaseRecommendations
- compute-optimizer:GetLambdaFunctionRecommendations
- compute-optimizer:GetEnrollmentStatus
- compute-optimizer:GetIdleRecommendations

AWS Budgets:
- budgets:ViewBudget

AWS Pricing:
- pricing:DescribeServices
- pricing:GetAttributeValues
- pricing:GetProducts

AWS Free Tier:
- freetier:GetFreeTierUsage

Storage Lens (Athena and S3):
- athena:StartQueryExecution
- athena:GetQueryExecution
- athena:GetQueryResults
- athena:CreateWorkGroup
- athena:GetWorkGroup
- athena:CreateDataCatalog
- athena:GetDataCatalog
- athena:GetDatabase
- athena:CreateTable
- athena:GetTableMetadata
- athena:ListDatabases
- athena:ListTableMetadata
- s3:GetObject
- s3:ListBucket
- s3:PutObject
- s3:GetBucketLocation
- s3:GetStorageLensConfiguration
- s3:ListStorageLensConfigurations
- s3:PutStorageLensConfiguration
- s3:GetStorageLensConfigurationTagging
- s3:PutStorageLensConfigurationTagging

#### Configuration

The server uses these key environment variables:

- **`AWS_PROFILE`**: Specifies the AWS profile to use from your AWS configuration file. If not provided, it defaults to the "default" profile.
- **`AWS_REGION`**: Determines the AWS region for API calls. Some APIs like Cost Explorer are only available in specific regions.

```json
"env": {
  "AWS_PROFILE": "your-aws-profile",
  "AWS_REGION": "us-east-1"
}
```

## Supported AWS Services

The server currently supports the following AWS services

1. **Cost Explorer**
   - get_reservation_purchase_recommendation
   - get_reservation_coverage
   - get_reservation_utilization
   - get_savings_plans_purchase_recommendation
   - get_savings_plans_utilization
   - get_savings_plans_coverage
   - get_savings_plans_details
   - get_cost_comparison_drivers
   - get_cost_and_usage_comparisons
   - get_anomalies
   - get_cost_and_usage
   - get_cost_and_usage_with_resources
   - get_dimension_values
   - get_cost_forecast
   - get_usage_forecast
   - get_tags
   - get_cost_categories

2. **AWS Budgets**
   - describe_budgets

3. **AWS Free Tier**
   - get_free_tier_usage

4. **AWS Pricing**
   - get_service_codes
   - get_service_attributes
   - get_attribute_values
   - get_products

5. **Cost Optimization Hub**
   - get_recommendation
   - list_recommendations
   - list_recommendation_summaries

6. **Compute Optimizer**
   - get_auto_scaling_group_recommendations
   - get_ebs_volume_recommendations
   - get_ec2_instance_recommendations
   - get_ecs_service_recommendations
   - get_rds_database_recommendations
   - get_lambda_function_recommendations
   - get_idle_recommendations
   - get_enrollment_status

7. **S3 Storage Lens**
   - storage_lens_run_query (custom implementation using Athena)
