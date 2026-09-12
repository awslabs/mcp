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

"""Constants used throughout the AWS Billing and Cost Management MCP server.

This module centralizes constant definitions to ensure consistency
and make maintenance easier across the codebase.
"""

from typing import List, Tuple


# ===== SQL Offload: Column Spec =====
# Used by `sql_utils._create_and_insert` to drive CREATE/INSERT for any
# helper-flattened record stream. Each spec is ``(column_name, sqlite_type)``;
# the column type also drives value coercion at insert time (REAL is coerced
# via ``float()`` to handle Decimal values that sqlite3 can't bind natively).
ColumnSpec = Tuple[str, str]


# ===== AWS Regions =====
REGION_US_EAST_1 = 'us-east-1'

# ===== Cost Optimization Hub Operation Types =====
OPERATION_LIST_RECOMMENDATION_SUMMARIES = 'list_recommendation_summaries'
OPERATION_LIST_RECOMMENDATIONS = 'list_recommendations'
OPERATION_GET_RECOMMENDATION = 'get_recommendation'
OPERATION_LIST_EFFICIENCY_METRICS = 'list_efficiency_metrics'

# ===== Cost Optimization Hub Group By Values =====
GROUP_BY_ACCOUNT_ID = 'AccountId'
GROUP_BY_REGION = 'Region'
GROUP_BY_ACTION_TYPE = 'ActionType'
GROUP_BY_RESOURCE_TYPE = 'ResourceType'
GROUP_BY_RESTART_NEEDED = 'RestartNeeded'
GROUP_BY_ROLLBACK_POSSIBLE = 'RollbackPossible'
GROUP_BY_IMPLEMENTATION_EFFORT = 'ImplementationEffort'

COST_OPTIMIZATION_HUB_VALID_GROUP_BY_VALUES = [
    GROUP_BY_ACCOUNT_ID,
    GROUP_BY_REGION,
    GROUP_BY_ACTION_TYPE,
    GROUP_BY_RESOURCE_TYPE,
    GROUP_BY_RESTART_NEEDED,
    GROUP_BY_ROLLBACK_POSSIBLE,
    GROUP_BY_IMPLEMENTATION_EFFORT,
]

# ===== Cost Optimization Hub - ListEfficiencyMetrics =====
# The efficiency-metrics API groups only by account ID or Region (no per-service
# or per-resource-type efficiency score exists), so it accepts a narrower group_by
# set than the recommendation APIs above.
EFFICIENCY_METRICS_VALID_GROUP_BY_VALUES = [
    GROUP_BY_ACCOUNT_ID,
    GROUP_BY_REGION,
]

# Time granularity. Note the title-case values (Daily/Monthly) differ from Cost
# Explorer's DAILY/MONTHLY.
GRANULARITY_DAILY = 'Daily'
GRANULARITY_MONTHLY = 'Monthly'
EFFICIENCY_METRICS_VALID_GRANULARITY = [GRANULARITY_DAILY, GRANULARITY_MONTHLY]

# Maximum look-back span the ListEfficiencyMetrics API serves per granularity:
# 90 days of Daily detail, 3 months of Monthly. Requests exceeding these are
# clamped (start moved forward) rather than rejected with a ValidationException.
EFFICIENCY_METRICS_MAX_DAILY_SPAN_DAYS = 90
EFFICIENCY_METRICS_MAX_MONTHLY_SPAN_MONTHS = 3

# ===== Cost Optimization Hub - orderBy (shared by list_recommendations and
# list_efficiency_metrics) =====
ORDER_ASC = 'Asc'
ORDER_DESC = 'Desc'
ORDER_BY_VALID_ORDERS = [ORDER_ASC, ORDER_DESC]

COST_OPTIMIZATION_HUB_LIST_EFFICIENCY_METRICS_VALID_ORDER_DIMENSIONS = [
    'Score',
    'Savings',
    'Spend',
]

COST_OPTIMIZATION_HUB_LIST_RECOMMENDATIONS_VALID_ORDER_DIMENSIONS = [
    'EstimatedMonthlySavings',
    'EstimatedMonthlyCost',
    'RestartNeeded',
    'ImplementationEffort',
    'AccountId',
    'RollbackPossible',
    'Region',
    'ResourceType',
    'ActionType',
    'ResourceArn',
    'ResourceId',
    'EstimatedSavingsPercentage',
]

# Maps a list_recommendations ``orderBy`` dimension (CamelCase API name) to the
# snake_case column it is stored under in the offloaded SQLite table
# (COST_OPTIMIZATION_HUB_RECOMMENDATION_COLUMNS). Used to build a sample query
# that mirrors the caller's requested ordering. Every orderBy dimension the API
# accepts has a stored column; a dimension absent from this map (e.g. an
# unexpected value) falls back to the default sample query.
COST_OPTIMIZATION_HUB_ORDER_DIMENSION_TO_COLUMN = {
    'EstimatedMonthlySavings': 'estimated_monthly_savings',
    'EstimatedMonthlyCost': 'estimated_monthly_cost',
    'ImplementationEffort': 'implementation_effort',
    'AccountId': 'account_id',
    'Region': 'region',
    'ResourceType': 'current_resource_type',
    'ActionType': 'action_type',
    'ResourceArn': 'resource_arn',
    'ResourceId': 'resource_id',
    'EstimatedSavingsPercentage': 'estimated_savings_percentage',
    'RestartNeeded': 'restart_needed',
    'RollbackPossible': 'rollback_possible',
}

# Maps a list_efficiency_metrics ``orderBy`` dimension to the snake_case column
# it is stored under in the offloaded SQLite table
# (COST_OPTIMIZATION_HUB_EFFICIENCY_METRICS_COLUMNS). Used to build a
# group-ranking sample query that mirrors the caller's requested ordering.
COST_OPTIMIZATION_HUB_EFFICIENCY_ORDER_DIMENSION_TO_COLUMN = {
    'Score': 'score',
    'Savings': 'savings',
    'Spend': 'spend',
}

# ===== Recommendation Details - Action Types =====
ACTION_TYPE_PURCHASE_SAVINGS_PLAN = 'PurchaseSavingsPlans'
ACTION_TYPE_PURCHASE_RESERVED_INSTANCE = 'PurchaseReservedInstances'
ACTION_TYPE_STOP = 'Stop'
ACTION_TYPE_DELETE = 'Delete'

# ===== Recommendation Details - Resource Types =====
RESOURCE_TYPE_EC2_INSTANCE = 'Ec2Instance'
RESOURCE_TYPE_EC2_ASG = 'Ec2AutoScalingGroup'
RESOURCE_TYPE_EBS_VOLUME = 'EbsVolume'
RESOURCE_TYPE_ECS_SERVICE = 'EcsService'
RESOURCE_TYPE_LAMBDA_FUNCTION = 'LambdaFunction'
RESOURCE_TYPE_RDS = 'RdsDbInstance'

# ===== Recommendation Details - Mapping Constants =====

# Term mapping (1-year, 3-year)
TERM_MAP = {'OneYear': 'ONE_YEAR', 'ThreeYear': 'THREE_YEARS'}

# Payment option mapping
PAYMENT_OPTION_MAP = {
    'AllUpfront': 'ALL_UPFRONT',
    'PartialUpfront': 'PARTIAL_UPFRONT',
    'NoUpfront': 'NO_UPFRONT',
}

# Account scope mapping
ACCOUNT_SCOPE_MAP = {'Linked': 'LINKED', 'Payer': 'PAYER'}

# Lookback period mapping
LOOKBACK_PERIOD_MAP = {
    7: 'SEVEN_DAYS',
    30: 'THIRTY_DAYS',
    60: 'SIXTY_DAYS',
    90: 'NINETY_DAYS',
    180: 'SIX_MONTHS',
    365: 'ONE_YEAR',
}

# Service name mapping
SERVICE_MAP = {
    'ec2ReservedInstances': 'Amazon Elastic Compute Cloud - Compute',
    'rdsReservedInstances': 'Amazon Relational Database Service',
    'redshiftReservedInstances': 'Amazon Redshift',
    'elastiCacheReservedInstances': 'Amazon ElastiCache',
    'openSearchReservedInstances': 'Amazon OpenSearch Service',
    'memoryDbReservedInstances': 'Amazon MemoryDB',
}

# Savings Plans type mapping
SAVINGS_PLANS_TYPE_MAP = {
    'ec2InstanceSavingsPlans': 'EC2_INSTANCE_SP',
    'computeSavingsPlans': 'COMPUTE_SP',
    'sageMakerSavingsPlans': 'SAGEMAKER_SP',
}


# Storage Lens configuration
STORAGE_LENS_DEFAULT_DATABASE = 'storage_lens_db'  # Default database name for Storage Lens data
STORAGE_LENS_DEFAULT_TABLE = 'storage_lens_metrics'  # Default table name for Storage Lens data

# Athena query configuration
ATHENA_MAX_RETRIES = 100  # Maximum number of retries for Athena query completion
ATHENA_RETRY_DELAY_SECONDS = 1  # Delay between retries in seconds

# Environment variable names
ENV_STORAGE_LENS_MANIFEST_LOCATION = (
    'STORAGE_LENS_MANIFEST_LOCATION'  # S3 URI to manifest file or folder
)
ENV_STORAGE_LENS_OUTPUT_LOCATION = (
    'STORAGE_LENS_OUTPUT_LOCATION'  # S3 location for Athena query results
)


# Schema used to offload ``list_recommendations`` responses to SQLite.
COST_OPTIMIZATION_HUB_RECOMMENDATION_COLUMNS: List[ColumnSpec] = [
    ('recommendation_id', 'TEXT'),
    ('account_id', 'TEXT'),
    ('region', 'TEXT'),
    ('resource_id', 'TEXT'),
    ('resource_arn', 'TEXT'),
    ('action_type', 'TEXT'),
    ('current_resource_type', 'TEXT'),
    ('recommended_resource_type', 'TEXT'),
    ('current_resource_summary', 'TEXT'),
    ('recommended_resource_summary', 'TEXT'),
    ('estimated_monthly_savings', 'REAL'),
    ('estimated_savings_percentage', 'REAL'),
    ('estimated_monthly_cost', 'REAL'),
    ('currency_code', 'TEXT'),
    ('implementation_effort', 'TEXT'),
    ('last_refresh_timestamp', 'TEXT'),
    ('lookback_period_in_days', 'INTEGER'),
    ('restart_needed', 'BOOLEAN'),
    ('rollback_possible', 'BOOLEAN'),
]


# Schema used to offload ``list_efficiency_metrics`` responses to SQLite. The
# response nests a per-timestamp series under each group, so it is denormalized
# to one row per (group, timestamp). A no-data group (empty ``metrics_by_time``)
# is preserved as a single row with null metrics so the group and its
# explanatory ``message`` survive offload rather than vanishing. The dimension
# column is ``group_value`` (not ``group``) because ``group`` is a SQL reserved
# word and ``_create_and_insert`` does not quote identifiers.
COST_OPTIMIZATION_HUB_EFFICIENCY_METRICS_COLUMNS: List[ColumnSpec] = [
    ('group_value', 'TEXT'),
    ('message', 'TEXT'),
    ('timestamp', 'TEXT'),
    ('score', 'REAL'),
    ('savings', 'REAL'),
    ('spend', 'REAL'),
]
