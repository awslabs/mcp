# S3 Storage Lens Query Module

This module provides functionality to query S3 Storage Lens metrics data using Athena. Since there are no direct boto3 methods to query Storage Lens metrics, this tool leverages the exported data in S3 and Athena to run SQL queries against it.

## Overview

Amazon S3 Storage Lens is an analytics feature that provides organization-wide visibility into object storage usage and activity trends. This module allows you to query the metrics data that Storage Lens exports to S3.

## Prerequisites

1. **Storage Lens Dashboard with Export Enabled**:
   - You must have a Storage Lens dashboard configured with metrics export enabled
   - The export must be configured to write to an S3 bucket in CSV or Parquet format

2. **AWS Permissions**:
   - S3 permissions to read the manifest and data files
   - Athena permissions to create databases, tables, and run queries
   - Glue permissions for the Athena catalog

## Module Structure

- `__init__.py`: Exports the main classes
- `manifest_handler.py`: Handles locating and parsing Storage Lens manifest files
- `athena_handler.py`: Manages Athena database and table creation, and query execution
- `query_tool.py`: Main tool that integrates manifest handling and Athena operations

## Usage

```python
from storage_lens import StorageLensQueryTool

async def main():
    # Initialize the tool
    tool = StorageLensQueryTool()

    # Query Storage Lens metrics
    results = await tool.query_storage_lens(
        manifest_location="s3://my-bucket/storage-lens-exports/",
        query="SELECT aws_region, storage_class, SUM(CAST(metric_value AS BIGINT)) as total_bytes " +
              "FROM {table} " +
              "WHERE metric_name = 'StorageBytes' " +
              "GROUP BY aws_region, storage_class " +
              "ORDER BY total_bytes DESC",
        output_location="s3://my-bucket/athena-results/",
        database_name="storage_lens_db",
        table_name="storage_lens_metrics"
    )

    # Process results
    for row in results['rows']:
        print(f"Region: {row['aws_region']}, Storage Class: {row['storage_class']}, Size: {row['total_bytes']} bytes")
```

## Parameters

- `manifest_location`: S3 URI to manifest file or folder containing manifest files
  - If a specific manifest.json file is provided, it will be used directly
  - If a folder is provided, the latest manifest.json file will be used
- `query`: SQL query to execute against the data
  - Use `{table}` as a placeholder for the table name
- `output_location` (optional): S3 location for Athena query results
  - If not provided, a location in the same bucket as the data will be used
- `database_name` (optional): Athena database name to use (default: "storage_lens_db")
- `table_name` (optional): Table name to create/use for the data (default: "storage_lens_metrics")

## Sample Queries

See the `resources/storage_lens_metrics_reference.md` file for sample queries and a complete list of available metrics.
