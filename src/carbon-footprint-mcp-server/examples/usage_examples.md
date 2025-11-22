# AWS Carbon Footprint MCP Server Usage Examples

This document provides practical examples of using the AWS Carbon Footprint MCP Server.

## Prerequisites

1. AWS CLI installed and configured
2. Appropriate IAM permissions for BCM Data Exports
3. S3 bucket for storing export files
4. MCP client configured with the carbon footprint server

## Basic Usage Examples

### 1. Create a Monthly Carbon Export

```
Create a carbon export named "monthly-carbon-2024-01" for January 2024, storing results in my-carbon-data-bucket with CSV format
```

This will:
- Create an export for the entire month of January 2024
- Store the results in the specified S3 bucket
- Use CSV format with GZIP compression (default)

### 2. Monitor Export Progress

```
Check the status of my carbon export
```

Or with specific ARN:
```
Get the status of export arn:aws:bcm-data-exports:us-east-1:123456789012:export/monthly-carbon-2024-01
```

### 3. Retrieve Completed Export Data

```
Get the carbon emissions data from my completed export arn:aws:bcm-data-exports:us-east-1:123456789012:export/monthly-carbon-2024-01
```

## Advanced Query Examples

### 4. Analyze EC2 Emissions by Region

```
Query carbon emissions for EC2-Instance service from 2024-01-01 to 2024-01-31, grouped by region
```

### 5. Compare Service Emissions

```
Query carbon data from 2024-01-01 to 2024-03-31 grouped by service, limited to top 20 results
```

### 6. Account-Level Analysis

```
Show me carbon emissions for account 123456789012 from 2024-01-01 to 2024-01-31 grouped by account
```

### 7. Regional Comparison

```
Query carbon emissions in us-east-1 region from 2024-01-01 to 2024-01-31 grouped by service
```

## Workflow Examples

### Monthly Carbon Reporting Workflow

1. **Create Export:**
   ```
   Create a carbon export for last month's data in my-reports-bucket
   ```

2. **Wait for Completion:**
   ```
   Check export status every few minutes until COMPLETED
   ```

3. **Analyze Results:**
   ```
   Get the carbon data and analyze by service and region
   ```

### Quarterly Carbon Analysis

1. **Create Quarterly Export:**
   ```
   Create a carbon export named "Q1-2024-carbon" from 2024-01-01 to 2024-03-31 in quarterly-reports-bucket
   ```

2. **Service-Level Analysis:**
   ```
   Query the quarterly data grouped by service to identify top emitters
   ```

3. **Regional Breakdown:**
   ```
   Query the same period grouped by region for geographic analysis
   ```

### Multi-Account Carbon Tracking

1. **Create Organization Export:**
   ```
   Create a carbon export for all accounts from 2024-01-01 to 2024-01-31
   ```

2. **Account Comparison:**
   ```
   Query carbon data grouped by account to compare emissions across accounts
   ```

3. **Service Analysis per Account:**
   ```
   Query carbon data for specific account grouped by service
   ```

## Export Configuration Examples

### High-Volume Data Export

```
Create a carbon export named "annual-carbon-2023" from 2023-01-01 to 2023-12-31 in annual-data-bucket with PARQUET format and GZIP compression
```

### Daily Granular Export

```
Create a carbon export named "daily-carbon-2024-01-15" from 2024-01-15 to 2024-01-16 in daily-reports-bucket
```

### Service-Specific Analysis Setup

```
Create a carbon export for EC2 analysis from 2024-01-01 to 2024-01-31, then query for EC2-Instance service grouped by region
```

## Error Handling Examples

### Check Export Status Before Data Retrieval

```
First check: Get status of export arn:aws:bcm-data-exports:us-east-1:123456789012:export/my-export
If COMPLETED, then: Get export data from the same ARN
```

### Validate Date Ranges

```
Query carbon data from 2024-01-01 to 2024-01-31 (valid date range)
vs
Query carbon data from 2024-13-01 to 2024-01-31 (invalid - will fail)
```

## Best Practices Examples

### Incremental Monthly Exports

```
January: Create export from 2024-01-01 to 2024-02-01
February: Create export from 2024-02-01 to 2024-03-01
March: Create export from 2024-03-01 to 2024-04-01
```

### Focused Service Analysis

```
Step 1: Query all services to identify top emitters
Step 2: Create focused exports for top 3 services
Step 3: Analyze each service separately by region
```

### Cost-Optimized Querying

```
Use specific date ranges: 2024-01-01 to 2024-01-07 (one week)
Filter by service: EC2-Instance only
Limit results: maximum 100 records
Group efficiently: by service or region, not both
```

## Integration Examples

### With Cost Analysis

```
1. Create carbon export for January 2024
2. Create cost export for same period (using Cost Explorer MCP)
3. Correlate carbon emissions with costs by service
```

### With Infrastructure Monitoring

```
1. Query carbon data for EC2 instances
2. Use EKS MCP server to check cluster efficiency
3. Correlate container usage with carbon emissions
```

### With Optimization Tools

```
1. Identify high-carbon services from export
2. Use Compute Optimizer MCP for rightsizing recommendations
3. Estimate carbon reduction from optimization
```

## Troubleshooting Examples

### Export Stuck in CREATING Status

```
1. Check export status: Get status of problematic export
2. Verify S3 permissions: List exports to see if others work
3. Check date range: Ensure dates are valid and reasonable
```

### No Data in Export

```
1. Verify carbon data exists: Query with broader date range
2. Check account permissions: Ensure access to carbon footprint tool
3. Validate filters: Remove service/region filters to test
```

### S3 Access Issues

```
1. Test bucket access: List carbon exports to verify configuration
2. Check IAM permissions: Ensure S3 read/write permissions
3. Verify bucket region: Ensure bucket is in correct region
```
