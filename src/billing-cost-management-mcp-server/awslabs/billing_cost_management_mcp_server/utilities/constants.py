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

# ===== AWS Regions =====
REGION_US_EAST_1 = 'us-east-1'

# ===== Cost Optimization Hub Operation Types =====
OPERATION_LIST_RECOMMENDATION_SUMMARIES = 'list_recommendation_summaries'
OPERATION_LIST_RECOMMENDATIONS = 'list_recommendations'
OPERATION_GET_RECOMMENDATION = 'get_recommendation'

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
