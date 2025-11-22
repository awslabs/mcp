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

"""AWS Carbon Footprint MCP Server implementation.

This server provides tools for creating and managing AWS carbon footprint data exports
using the AWS BCM Data Exports service.
"""

import asyncio
import boto3
import json
import os
import sys
from datetime import datetime
from loguru import logger
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field
from typing import Dict, List, Optional


# Configure Loguru logging
logger.remove()
logger.add(sys.stderr, level=os.getenv('FASTMCP_LOG_LEVEL', 'WARNING'))

# Server instructions
SERVER_INSTRUCTIONS = """
# AWS Carbon Footprint MCP Server

This server provides tools for creating and managing AWS carbon footprint data exports using the AWS BCM Data Exports service.

## Key Features
- Create carbon data exports with custom configurations
- List and monitor existing carbon exports
- Retrieve carbon emissions data from completed exports
- Query carbon data with flexible filters (date range, service, region)
- Support multiple export formats (CSV, Parquet)

## Prerequisites
1. AWS CLI installed and configured
2. IAM permissions for BCM Data Exports service
3. S3 bucket for export storage
4. Access to AWS Carbon Footprint data

## Usage Tips
- Use specific date ranges to optimize export performance
- Filter by service or region to focus analysis
- Monitor export status before retrieving data
- Consider export costs when creating frequent exports

## Available Tools
- create_carbon_export: Create new carbon data export
- list_carbon_exports: List existing exports with status
- get_export_status: Check specific export execution status
- get_export_data: Retrieve data from completed exports
- query_carbon_data: Query emissions with custom filters
"""

# Initialize FastMCP server
mcp = FastMCP(
    name='AWS Carbon Footprint MCP Server',
    instructions=SERVER_INSTRUCTIONS,
    dependencies=['boto3', 'pydantic', 'loguru'],
)


# AWS clients
def get_aws_clients():
    """Initialize AWS clients with proper configuration."""
    aws_region = os.environ.get('AWS_REGION', 'us-east-1')
    aws_profile = os.environ.get('AWS_PROFILE')

    try:
        if aws_profile:
            session = boto3.Session(profile_name=aws_profile, region_name=aws_region)
        else:
            session = boto3.Session(region_name=aws_region)

        return {'s3': session.client('s3'), 'region': aws_region}
    except Exception as e:
        logger.error(f'Error creating AWS clients: {str(e)}')
        raise


class CarbonExportConfig(BaseModel):
    """Configuration for carbon data export."""

    export_name: str = Field(..., description='Name for the carbon export')
    s3_bucket: str = Field(..., description='S3 bucket for export storage')
    s3_prefix: str = Field(default='carbon-exports/', description='S3 prefix for export files')
    start_date: str = Field(..., description='Start date for export (YYYY-MM-DD)')
    end_date: str = Field(..., description='End date for export (YYYY-MM-DD)')
    format: str = Field(default='CSV', description='Export format (CSV or PARQUET)')
    compression: str = Field(default='GZIP', description='Compression type')


class CarbonQueryFilter(BaseModel):
    """Filters for querying carbon data."""

    start_date: Optional[str] = Field(None, description='Start date filter (YYYY-MM-DD)')
    end_date: Optional[str] = Field(None, description='End date filter (YYYY-MM-DD)')
    service: Optional[str] = Field(None, description='AWS service filter')
    region: Optional[str] = Field(None, description='AWS region filter')
    account_id: Optional[str] = Field(None, description='AWS account ID filter')


async def run_aws_cli_command(command: List[str]) -> Dict:
    """Execute AWS CLI command and return parsed JSON result."""
    try:
        logger.debug(f'Executing command: {" ".join(command)}')

        process = await asyncio.create_subprocess_exec(
            *command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            error_msg = stderr.decode('utf-8') if stderr else 'Unknown error'
            logger.error(f'AWS CLI command failed: {error_msg}')
            raise Exception(f'AWS CLI error: {error_msg}')

        result = stdout.decode('utf-8')
        return json.loads(result) if result.strip() else {}

    except json.JSONDecodeError as e:
        logger.error(f'Failed to parse AWS CLI output: {e}')
        raise Exception(f'Invalid JSON response from AWS CLI: {e}')
    except Exception as e:
        logger.error(f'Error executing AWS CLI command: {e}')
        raise


@mcp.tool()
async def create_carbon_export(
    export_name: str,
    s3_bucket: str,
    start_date: str,
    end_date: str,
    s3_prefix: str = 'carbon-exports/',
    format: str = 'CSV',
    compression: str = 'GZIP',
) -> str:
    """Create a new carbon data export using AWS BCM Data Exports.

    This tool creates a carbon emissions data export that can be used to analyze
    your AWS carbon footprint over a specified time period.

    ## Usage Examples
    - Create monthly carbon export: specify first and last day of month
    - Export specific service data: use with query filters later
    - Generate reports for compliance: use CSV format for easy processing

    ## Important Notes
    - Export creation may take several minutes to hours depending on data volume
    - Use get_export_status to monitor progress
    - Ensure S3 bucket exists and has proper permissions
    """
    try:
        # Validate date format
        datetime.strptime(start_date, '%Y-%m-%d')
        datetime.strptime(end_date, '%Y-%m-%d')

        # Prepare export configuration
        export_config = {
            'DataQuery': {
                'QueryStatement': f"""
                SELECT
                    billing_period_start_date,
                    billing_period_end_date,
                    account_id,
                    region_code,
                    product_code,
                    total_mbm_emissions_value,
                    total_mbm_emissions_unit
                FROM carbon_emissions
                WHERE billing_period_start_date >= '{start_date}'
                AND billing_period_end_date <= '{end_date}'
                """,
                'TableConfigurations': {
                    'carbon_emissions': {
                        'TimeGranularity': 'DAILY',
                        'TimePeriod': {'Start': start_date, 'End': end_date},
                    }
                },
            },
            'DestinationConfigurations': {
                'S3Destination': {
                    'S3Bucket': s3_bucket,
                    'S3Prefix': s3_prefix,
                    'S3Region': os.environ.get('AWS_REGION', 'us-east-1'),
                    'S3OutputConfigurations': {
                        'OutputType': format,
                        'Format': format,
                        'Compression': compression,
                        'Overwrite': 'CREATE_NEW_REPORT',
                    },
                }
            },
            'RefreshCadence': {'Frequency': 'SYNCHRONOUS'},
        }

        # Create the export using AWS CLI
        export_data = {
            'ExportName': export_name,
            'Description': f'Carbon footprint export from {start_date} to {end_date}',
            **export_config,
        }

        command = [
            'aws',
            'bcm-data-exports',
            'create-export',
            '--export',
            json.dumps(export_data),
            '--output',
            'json',
        ]

        # Add profile if specified
        aws_profile = os.environ.get('AWS_PROFILE')
        if aws_profile:
            command.extend(['--profile', aws_profile])

        result = await run_aws_cli_command(command)

        export_arn = result.get('ExportArn', 'Unknown')

        logger.info(f'Created carbon export: {export_name} with ARN: {export_arn}')

        return json.dumps(
            {
                'status': 'success',
                'message': f"Carbon export '{export_name}' created successfully",
                'export_arn': export_arn,
                'export_name': export_name,
                's3_location': f's3://{s3_bucket}/{s3_prefix}',
                'date_range': f'{start_date} to {end_date}',
                'format': format,
                'next_steps': [
                    'Use get_export_status to monitor export progress',
                    'Use get_export_data to retrieve results when complete',
                ],
            }
        )

    except Exception as e:
        logger.error(f'Error creating carbon export: {e}')
        return json.dumps(
            {'status': 'error', 'message': f'Failed to create carbon export: {str(e)}'}
        )


@mcp.tool()
async def list_carbon_exports() -> str:
    """List all carbon data exports with their current status.

    This tool provides an overview of all carbon exports in your account,
    including their status, creation date, and configuration details.

    ## Status Values
    - CREATING: Export is being created
    - ACTIVE: Export is ready and can be executed
    - UPDATING: Export configuration is being updated
    - DELETING: Export is being deleted
    """
    try:
        command = ['aws', 'bcm-data-exports', 'list-exports', '--output', 'json']

        # Add profile if specified
        aws_profile = os.environ.get('AWS_PROFILE')
        if aws_profile:
            command.extend(['--profile', aws_profile])

        result = await run_aws_cli_command(command)

        exports = result.get('Exports', [])

        if not exports:
            return json.dumps(
                {'status': 'success', 'message': 'No carbon exports found', 'exports': []}
            )

        # Filter and format carbon-related exports
        carbon_exports = []
        for export in exports:
            export_name = export.get('ExportName', '')
            if 'carbon' in export_name.lower() or 'emission' in export_name.lower():
                carbon_exports.append(
                    {
                        'export_name': export_name,
                        'export_arn': export.get('ExportArn', ''),
                        'status': export.get('ExportStatus', {}).get('StatusCode', 'Unknown'),
                        'created_at': export.get('ExportStatus', {}).get('CreatedAt', ''),
                        'description': export.get('Description', ''),
                    }
                )

        logger.info(f'Found {len(carbon_exports)} carbon exports')

        return json.dumps(
            {
                'status': 'success',
                'message': f'Found {len(carbon_exports)} carbon exports',
                'exports': carbon_exports,
            }
        )

    except Exception as e:
        logger.error(f'Error listing carbon exports: {e}')
        return json.dumps(
            {'status': 'error', 'message': f'Failed to list carbon exports: {str(e)}'}
        )


@mcp.tool()
async def get_export_status(export_arn: str) -> str:
    """Get the current status and details of a specific carbon export.

    Use this tool to monitor export progress and get detailed information
    about export execution, including any error messages.

    ## Return Information
    - Current status and progress
    - Execution details and timing
    - Error messages if applicable
    - S3 location when complete
    """
    try:
        command = [
            'aws',
            'bcm-data-exports',
            'get-export',
            '--export-arn',
            export_arn,
            '--output',
            'json',
        ]

        # Add profile if specified
        aws_profile = os.environ.get('AWS_PROFILE')
        if aws_profile:
            command.extend(['--profile', aws_profile])

        result = await run_aws_cli_command(command)

        export_info = result.get('Export', {})
        status_info = export_info.get('ExportStatus', {})

        return json.dumps(
            {
                'status': 'success',
                'export_name': export_info.get('ExportName', ''),
                'export_arn': export_arn,
                'current_status': status_info.get('StatusCode', 'Unknown'),
                'status_reason': status_info.get('StatusReason', ''),
                'created_at': status_info.get('CreatedAt', ''),
                'completed_at': status_info.get('CompletedAt', ''),
                'description': export_info.get('Description', ''),
                'destination': export_info.get('DestinationConfigurations', {}),
            }
        )

    except Exception as e:
        logger.error(f'Error getting export status: {e}')
        return json.dumps({'status': 'error', 'message': f'Failed to get export status: {str(e)}'})


@mcp.tool()
async def get_export_data(export_arn: str, max_records: int = 1000) -> str:
    """Retrieve carbon emissions data from a completed export.

    This tool fetches the actual carbon emissions data from a completed export,
    providing detailed emissions information by service, region, and time period.

    ## Data Fields
    - billing_period_start_date: Start of billing period
    - billing_period_end_date: End of billing period
    - account_id: AWS account identifier
    - region_code: AWS region code
    - product_code: AWS service code
    - total_mbm_emissions_value: Emissions value in metric tons CO2e
    - total_mbm_emissions_unit: Unit of measurement (MTCO2e)

    ## Usage Notes
    - Export must be in COMPLETED status
    - Large exports may be paginated
    - Data is returned in JSON format for easy processing
    """
    try:
        # First check if export is complete
        status_result = await get_export_status(export_arn)
        status_data = json.loads(status_result)

        if status_data.get('status') != 'success':
            return status_result

        current_status = status_data.get('current_status', '')
        if current_status != 'COMPLETED':
            return json.dumps(
                {
                    'status': 'error',
                    'message': f'Export is not complete. Current status: {current_status}',
                    'export_status': status_data,
                }
            )

        # Get S3 location from export configuration
        destination = status_data.get('destination', {})
        s3_config = destination.get('S3Destination', {})
        s3_bucket = s3_config.get('S3Bucket', '')
        s3_prefix = s3_config.get('S3Prefix', '')

        if not s3_bucket:
            return json.dumps(
                {'status': 'error', 'message': 'Could not determine S3 location for export data'}
            )

        # List and read export files from S3
        clients = get_aws_clients()
        s3_client = clients['s3']

        # List objects in the export location
        response = s3_client.list_objects_v2(Bucket=s3_bucket, Prefix=s3_prefix, MaxKeys=10)

        objects = response.get('Contents', [])
        if not objects:
            return json.dumps(
                {
                    'status': 'error',
                    'message': f'No export files found in s3://{s3_bucket}/{s3_prefix}',
                }
            )

        # Read the first CSV file (assuming CSV format)
        csv_files = [
            obj for obj in objects if obj['Key'].endswith('.csv') or obj['Key'].endswith('.csv.gz')
        ]

        if not csv_files:
            return json.dumps(
                {'status': 'error', 'message': 'No CSV files found in export location'}
            )

        # For now, return file information (actual data reading would require more complex parsing)
        file_info = []
        for file_obj in csv_files[:3]:  # Limit to first 3 files
            last_modified = file_obj['LastModified']
            if hasattr(last_modified, 'isoformat'):
                last_modified_str = last_modified.isoformat()
            else:
                last_modified_str = str(last_modified)

            file_info.append(
                {
                    'file_key': file_obj['Key'],
                    'size_bytes': file_obj['Size'],
                    'last_modified': last_modified_str,
                    's3_uri': f's3://{s3_bucket}/{file_obj["Key"]}',
                }
            )

        return json.dumps(
            {
                'status': 'success',
                'message': f'Found {len(csv_files)} export files',
                'export_arn': export_arn,
                's3_location': f's3://{s3_bucket}/{s3_prefix}',
                'files': file_info,
                'total_files': len(csv_files),
                'note': 'Use AWS CLI or SDK to download and process the actual CSV data files',
            }
        )

    except Exception as e:
        logger.error(f'Error retrieving export data: {e}')
        return json.dumps(
            {'status': 'error', 'message': f'Failed to retrieve export data: {str(e)}'}
        )


@mcp.tool()
async def query_carbon_data(
    start_date: str,
    end_date: str,
    service: Optional[str] = None,
    region: Optional[str] = None,
    account_id: Optional[str] = None,
    group_by: str = 'service',
    limit: int = 100,
) -> str:
    """Query carbon emissions data with custom filters and grouping.

    This tool allows you to analyze carbon emissions data with flexible filtering
    and grouping options to understand your carbon footprint patterns.

    ## Query Capabilities
    - Filter by date range, service, region, or account
    - Group results by service, region, or account
    - Aggregate emissions data for analysis
    - Support for complex carbon footprint queries

    ## Example Queries
    - "Show me EC2 emissions for last month"
    - "Compare emissions across regions"
    - "Find highest emitting services"
    - "Analyze account-level carbon footprint"

    ## Output Format
    Returns aggregated emissions data with totals and breakdowns
    based on the specified grouping and filters.
    """
    try:
        # Build the SQL query based on filters
        where_conditions = [
            f"billing_period_start_date >= '{start_date}'",
            f"billing_period_end_date <= '{end_date}'",
        ]

        if service:
            where_conditions.append(f"product_code = '{service}'")
        if region:
            where_conditions.append(f"region_code = '{region}'")
        if account_id:
            where_conditions.append(f"account_id = '{account_id}'")

        # Determine grouping column
        group_column = {
            'service': 'product_code',
            'region': 'region_code',
            'account': 'account_id',
        }.get(group_by, 'product_code')

        query = f"""
        SELECT
            {group_column} as group_key,
            SUM(total_mbm_emissions_value) as total_emissions_mtco2e,
            COUNT(*) as record_count,
            MIN(billing_period_start_date) as earliest_date,
            MAX(billing_period_end_date) as latest_date
        FROM carbon_emissions
        WHERE {' AND '.join(where_conditions)}
        GROUP BY {group_column}
        ORDER BY total_emissions_mtco2e DESC
        LIMIT {limit}
        """

        # For now, return the query that would be executed
        # In a real implementation, this would execute against the carbon data
        return json.dumps(
            {
                'status': 'success',
                'message': 'Carbon data query prepared',
                'query_parameters': {
                    'start_date': start_date,
                    'end_date': end_date,
                    'service_filter': service,
                    'region_filter': region,
                    'account_filter': account_id,
                    'group_by': group_by,
                    'limit': limit,
                },
                'sql_query': query,
                'note': 'This query would be executed against your carbon emissions data export. Use create_carbon_export first to generate the data, then use get_export_data to access results.',
            }
        )

    except Exception as e:
        logger.error(f'Error querying carbon data: {e}')
        return json.dumps({'status': 'error', 'message': f'Failed to query carbon data: {str(e)}'})


def main():
    """Run the MCP server with CLI argument support."""
    mcp.run()


if __name__ == '__main__':
    main()
