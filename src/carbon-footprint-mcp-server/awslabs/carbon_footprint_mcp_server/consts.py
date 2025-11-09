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

"""Constants for AWS Carbon Footprint MCP Server."""

# Default configuration values
DEFAULT_AWS_REGION = 'us-east-1'
DEFAULT_S3_PREFIX = 'carbon-exports/'
DEFAULT_EXPORT_FORMAT = 'CSV'
DEFAULT_COMPRESSION = 'GZIP'
DEFAULT_QUERY_LIMIT = 100
DEFAULT_MAX_RECORDS = 1000

# Export configuration limits
MAX_EXPORT_NAME_LENGTH = 128
MIN_EXPORT_NAME_LENGTH = 1
MAX_DESCRIPTION_LENGTH = 512
MAX_S3_BUCKET_NAME_LENGTH = 63
MIN_S3_BUCKET_NAME_LENGTH = 3
MAX_QUERY_LIMIT = 10000
MIN_QUERY_LIMIT = 1

# AWS service codes commonly associated with carbon emissions
COMMON_AWS_SERVICES = [
    'EC2-Instance',
    'EC2-EBS',
    'S3',
    'RDS',
    'Lambda',
    'ECS',
    'EKS',
    'ElastiCache',
    'Redshift',
    'EMR',
    'SageMaker',
    'Glue',
    'Kinesis',
    'DynamoDB',
    'CloudFront',
    'API Gateway',
    'ELB',
    'NAT Gateway',
    'VPC',
    'Route53',
]

# AWS regions commonly used for carbon analysis
COMMON_AWS_REGIONS = [
    'us-east-1',  # N. Virginia
    'us-east-2',  # Ohio
    'us-west-1',  # N. California
    'us-west-2',  # Oregon
    'eu-west-1',  # Ireland
    'eu-west-2',  # London
    'eu-west-3',  # Paris
    'eu-central-1',  # Frankfurt
    'ap-southeast-1',  # Singapore
    'ap-southeast-2',  # Sydney
    'ap-northeast-1',  # Tokyo
    'ap-northeast-2',  # Seoul
    'ap-south-1',  # Mumbai
    'ca-central-1',  # Canada
    'sa-east-1',  # São Paulo
]

# Carbon emissions data schema
CARBON_EMISSIONS_SCHEMA = {
    'billing_period_start_date': 'DATE',
    'billing_period_end_date': 'DATE',
    'account_id': 'STRING',
    'region_code': 'STRING',
    'product_code': 'STRING',
    'total_mbm_emissions_value': 'FLOAT',
    'total_mbm_emissions_unit': 'STRING',
}

# Standard SQL query templates
CARBON_QUERY_TEMPLATES = {
    'basic_query': """
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
    'aggregated_by_service': """
        SELECT
            product_code as service,
            SUM(total_mbm_emissions_value) as total_emissions_mtco2e,
            COUNT(*) as record_count,
            MIN(billing_period_start_date) as earliest_date,
            MAX(billing_period_end_date) as latest_date
        FROM carbon_emissions
        WHERE billing_period_start_date >= '{start_date}'
        AND billing_period_end_date <= '{end_date}'
        GROUP BY product_code
        ORDER BY total_emissions_mtco2e DESC
    """,
    'aggregated_by_region': """
        SELECT
            region_code as region,
            SUM(total_mbm_emissions_value) as total_emissions_mtco2e,
            COUNT(*) as record_count,
            MIN(billing_period_start_date) as earliest_date,
            MAX(billing_period_end_date) as latest_date
        FROM carbon_emissions
        WHERE billing_period_start_date >= '{start_date}'
        AND billing_period_end_date <= '{end_date}'
        GROUP BY region_code
        ORDER BY total_emissions_mtco2e DESC
    """,
    'aggregated_by_account': """
        SELECT
            account_id as account,
            SUM(total_mbm_emissions_value) as total_emissions_mtco2e,
            COUNT(*) as record_count,
            MIN(billing_period_start_date) as earliest_date,
            MAX(billing_period_end_date) as latest_date
        FROM carbon_emissions
        WHERE billing_period_start_date >= '{start_date}'
        AND billing_period_end_date <= '{end_date}'
        GROUP BY account_id
        ORDER BY total_emissions_mtco2e DESC
    """,
}

# Export status messages
EXPORT_STATUS_MESSAGES = {
    'CREATING': 'Export is being created and configured',
    'ACTIVE': 'Export is ready and can be executed',
    'UPDATING': 'Export configuration is being updated',
    'DELETING': 'Export is being deleted',
    'COMPLETED': 'Export has completed successfully',
    'FAILED': 'Export has failed - check error details',
}

# Error messages
ERROR_MESSAGES = {
    'INVALID_DATE_FORMAT': 'Date must be in YYYY-MM-DD format',
    'INVALID_DATE_RANGE': 'End date must be after start date',
    'INVALID_S3_BUCKET': 'Invalid S3 bucket name format',
    'INVALID_ACCOUNT_ID': 'Account ID must be a 12-digit number',
    'EXPORT_NOT_FOUND': 'Export not found with the specified ARN',
    'EXPORT_NOT_COMPLETE': 'Export is not in COMPLETED status',
    'NO_DATA_FOUND': 'No carbon emissions data found for the specified criteria',
    'AWS_CLI_ERROR': 'AWS CLI command failed',
    'S3_ACCESS_ERROR': 'Unable to access S3 bucket or objects',
    'PERMISSION_DENIED': 'Insufficient permissions for the requested operation',
}

# Success messages
SUCCESS_MESSAGES = {
    'EXPORT_CREATED': 'Carbon export created successfully',
    'EXPORT_LISTED': 'Carbon exports retrieved successfully',
    'STATUS_RETRIEVED': 'Export status retrieved successfully',
    'DATA_RETRIEVED': 'Carbon emissions data retrieved successfully',
    'QUERY_EXECUTED': 'Carbon data query executed successfully',
}

# File patterns for carbon exports
CARBON_FILE_PATTERNS = [
    r'.*carbon.*\.csv$',
    r'.*carbon.*\.csv\.gz$',
    r'.*emission.*\.csv$',
    r'.*emission.*\.csv\.gz$',
    r'.*\.parquet$',
    r'.*\.parquet\.gz$',
]

# Environment variable names
ENV_VARS = {
    'AWS_REGION': 'AWS_REGION',
    'AWS_PROFILE': 'AWS_PROFILE',
    'AWS_ACCESS_KEY_ID': 'AWS_ACCESS_KEY_ID',  # pragma: allowlist secret
    'AWS_SECRET_ACCESS_KEY': 'AWS_SECRET_ACCESS_KEY',  # pragma: allowlist secret
    'AWS_SESSION_TOKEN': 'AWS_SESSION_TOKEN',  # pragma: allowlist secret
    'FASTMCP_LOG_LEVEL': 'FASTMCP_LOG_LEVEL',
}

# Logging configuration
LOG_LEVELS = {
    'DEBUG': 'DEBUG',
    'INFO': 'INFO',
    'WARNING': 'WARNING',
    'ERROR': 'ERROR',
    'CRITICAL': 'CRITICAL',
}

# Carbon footprint analysis tips
ANALYSIS_TIPS = [
    'Use specific date ranges to optimize export performance and costs',
    'Filter by high-usage services like EC2 and S3 for focused analysis',
    'Compare emissions across regions to identify optimization opportunities',
    'Monitor monthly trends to track carbon footprint improvements',
    'Consider time zones when analyzing daily emission patterns',
    'Group by service to identify the highest-impact areas for optimization',
    'Use account-level grouping for multi-account carbon analysis',
    'Export data regularly for historical trend analysis',
    'Combine carbon data with cost data for comprehensive optimization',
    'Focus on regions with higher carbon intensity for maximum impact',
]

# Documentation links
DOCUMENTATION_LINKS = {
    'carbon_footprint_tool': 'https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/billing-reports-costusage-carbon.html',
    'data_exports': 'https://docs.aws.amazon.com/cur/latest/userguide/dataexports-create-standard.html',
    'bcm_data_exports_cli': 'https://docs.aws.amazon.com/cli/latest/reference/bcm-data-exports/index.html',
    'carbon_methodology': 'https://sustainability.aboutamazon.com/aws-customer-carbon-footprint-tool-methodology.pdf',
}
