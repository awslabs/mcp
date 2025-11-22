# AWS Carbon Footprint MCP Server

An AWS Model Context Protocol (MCP) server that provides tools for creating and managing AWS carbon footprint data exports using the AWS BCM Data Exports service.

## Features

- **Create Carbon Data Exports**: Generate carbon emissions data exports with custom configurations
- **Monitor Export Status**: Track the progress of carbon data exports
- **Retrieve Export Data**: Access completed carbon emissions data from S3
- **Query Carbon Data**: Analyze carbon emissions with flexible filters and grouping
- **Multiple Export Formats**: Support for CSV and Parquet formats with compression options

## Prerequisites

1. **AWS CLI**: Install and configure the AWS CLI
2. **AWS Credentials**: Configure AWS credentials with appropriate permissions
3. **IAM Permissions**: Ensure access to the following services:
   - AWS BCM Data Exports (`bcm-data-exports:*`)
   - Amazon S3 (`s3:GetObject`, `s3:PutObject`, `s3:ListBucket`)
   - AWS Carbon Footprint Tool (`sustainability:GetCarbonFootprintSummary`)
4. **S3 Bucket**: An S3 bucket for storing export files

## Installation

```bash
# Install using uvx (recommended)
uvx awslabs.carbon-footprint-mcp-server@latest

# Or install using pip
pip install awslabs.carbon-footprint-mcp-server
```

## Configuration

### Environment Variables

- `AWS_REGION`: AWS region (default: us-east-1)
- `AWS_PROFILE`: AWS profile name (optional)
- `FASTMCP_LOG_LEVEL`: Logging level (default: WARNING)

### MCP Client Configuration

Add to your MCP client configuration:

```json
{
  "mcpServers": {
    "carbon-footprint": {
      "command": "uvx",
      "args": ["awslabs.carbon-footprint-mcp-server@latest"],
      "env": {
        "AWS_REGION": "us-east-1",
        "AWS_PROFILE": "your-profile-name"
      }
    }
  }
}
```

## Available Tools

### create_carbon_export

Create a new carbon data export with custom configuration.

**Parameters:**
- `export_name` (required): Unique name for the export
- `s3_bucket` (required): S3 bucket for storing export files
- `s3_prefix`: S3 prefix path (default: "carbon-exports/")
- `start_date` (required): Start date in YYYY-MM-DD format
- `end_date` (required): End date in YYYY-MM-DD format
- `format`: Export format - CSV or PARQUET (default: CSV)
- `compression`: Compression type - GZIP or NONE (default: GZIP)

**Example:**
```
Create a carbon export named "monthly-carbon-2024-01" for January 2024 data, storing results in my-carbon-bucket
```

### list_carbon_exports

List all carbon data exports with their current status.

**Example:**
```
Show me all my carbon exports and their status
```

### get_export_status

Get detailed status information for a specific export.

**Parameters:**
- `export_arn` (required): ARN of the export to check

**Example:**
```
Check the status of export arn:aws:bcm-data-exports:us-east-1:123456789012:export/my-export
```

### get_export_data

Retrieve carbon emissions data from a completed export.

**Parameters:**
- `export_arn` (required): ARN of the completed export
- `max_records`: Maximum number of records to return (default: 1000)

**Example:**
```
Get the carbon data from my completed export
```

### query_carbon_data

Query carbon emissions data with custom filters and grouping.

**Parameters:**
- `start_date` (required): Query start date (YYYY-MM-DD)
- `end_date` (required): Query end date (YYYY-MM-DD)
- `service`: Filter by AWS service (optional)
- `region`: Filter by AWS region (optional)
- `account_id`: Filter by AWS account ID (optional)
- `group_by`: Group results by service, region, or account (default: service)
- `limit`: Maximum results to return (default: 100)

**Example:**
```
Query carbon emissions for EC2 services in us-east-1 from 2024-01-01 to 2024-01-31, grouped by service
```

## Usage Examples

### Basic Workflow

1. **Create a carbon export:**
   ```
   Create a carbon export for Q1 2024 data in my-carbon-bucket
   ```

2. **Monitor export progress:**
   ```
   Check the status of my carbon export
   ```

3. **Retrieve the data when complete:**
   ```
   Get the carbon emissions data from my completed export
   ```

### Advanced Analysis

1. **Compare emissions by region:**
   ```
   Query carbon data from 2024-01-01 to 2024-03-31 grouped by region
   ```

2. **Analyze specific services:**
   ```
   Show me EC2 carbon emissions for the last quarter
   ```

3. **Account-level analysis:**
   ```
   Query carbon emissions grouped by account for multi-account analysis
   ```

## Data Schema

Carbon emissions data includes the following fields:

- `billing_period_start_date`: Start of the billing period
- `billing_period_end_date`: End of the billing period
- `account_id`: AWS account identifier
- `region_code`: AWS region code (e.g., us-east-1)
- `product_code`: AWS service code (e.g., EC2-Instance)
- `total_mbm_emissions_value`: Emissions value in metric tons CO2e
- `total_mbm_emissions_unit`: Unit of measurement (MTCO2e)

## Best Practices

1. **Export Optimization:**
   - Use specific date ranges to minimize export size and cost
   - Choose appropriate compression for your use case
   - Use descriptive export names for easy identification

2. **Data Analysis:**
   - Filter by high-usage services for focused analysis
   - Group by region to identify optimization opportunities
   - Monitor monthly trends for carbon footprint tracking

3. **Cost Management:**
   - Be aware that BCM Data Exports may incur costs
   - Use filters to reduce data volume
   - Schedule exports appropriately for your needs

## Troubleshooting

### Common Issues

1. **Export Creation Fails:**
   - Verify IAM permissions for BCM Data Exports
   - Ensure S3 bucket exists and is accessible
   - Check date format (must be YYYY-MM-DD)

2. **No Data Retrieved:**
   - Confirm export is in COMPLETED status
   - Verify S3 permissions for reading objects
   - Check if carbon data exists for the specified date range

3. **AWS CLI Errors:**
   - Ensure AWS CLI is installed and configured
   - Verify AWS credentials are valid
   - Check region configuration

### Error Messages

- `Export is not complete`: Wait for export to finish before retrieving data
- `Invalid S3 bucket name`: Check bucket name format and existence
- `AWS CLI command failed`: Verify AWS CLI installation and credentials
- `No carbon emissions data found`: Confirm data exists for the specified criteria

## Security Considerations

- Use IAM roles with minimal required permissions
- Enable S3 bucket encryption for export data
- Monitor access to carbon emissions data
- Follow AWS security best practices for data handling

## Related Documentation

- [AWS Customer Carbon Footprint Tool](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/billing-reports-costusage-carbon.html)
- [AWS BCM Data Exports](https://docs.aws.amazon.com/cur/latest/userguide/dataexports-create-standard.html)
- [AWS CLI BCM Data Exports Reference](https://docs.aws.amazon.com/cli/latest/reference/bcm-data-exports/index.html)
- [Carbon Footprint Methodology](https://sustainability.aboutamazon.com/aws-customer-carbon-footprint-tool-methodology.pdf)

## Support

For issues and questions:
1. Check the troubleshooting section above
2. Review AWS documentation for BCM Data Exports
3. Verify IAM permissions and AWS CLI configuration
4. Open an issue in the [AWS MCP repository](https://github.com/awslabs/mcp)

## License

This project is licensed under the Apache License 2.0. See the [LICENSE](LICENSE) file for details.
