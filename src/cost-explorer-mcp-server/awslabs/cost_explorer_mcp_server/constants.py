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

"""Constants for the Cost Explorer MCP server."""

from typing import List


# AWS Cost Explorer supported dimensions
VALID_DIMENSIONS: List[str] = [
    'AZ',  # The Availability Zone. An example is us-east-1a.
    'BILLING_ENTITY',  # The Amazon Web Services seller that your account is with
    'CACHE_ENGINE',  # The Amazon ElastiCache operating system. Examples are Windows or Linux.
    'DEPLOYMENT_OPTION',  # The scope of Amazon Relational Database Service deployments. Valid values are SingleAZ and MultiAZ.
    'DATABASE_ENGINE',  # The Amazon Relational Database Service database. Examples are Aurora or MySQL.
    'INSTANCE_TYPE',  # The type of Amazon EC2 instance. An example is m4.xlarge.
    'INSTANCE_TYPE_FAMILY',  # A family of instance types optimized to fit different use cases
    'INVOICING_ENTITY',  # The name of the entity that issues the Amazon Web Services invoice
    'LEGAL_ENTITY_NAME',  # The name of the organization that sells you Amazon Web Services services
    'LINKED_ACCOUNT',  # The description in the attribute map that includes the full name of the member account
    'OPERATING_SYSTEM',  # The operating system. Examples are Windows or Linux.
    'OPERATION',  # The action performed. Examples include RunInstance and CreateBucket.
    'PLATFORM',  # The Amazon EC2 operating system. Examples are Windows or Linux.
    'PURCHASE_TYPE',  # The reservation type of the purchase that this usage is related to
    'RESERVATION_ID',  # The unique identifier for an Amazon Web Services Reservation Instance
    'SAVINGS_PLAN_ARN',  # The unique identifier for your Savings Plans
    'SAVINGS_PLANS_TYPE',  # Type of Savings Plans (EC2 Instance or Compute)
    'SERVICE',  # The Amazon Web Services service such as Amazon DynamoDB
    'TENANCY',  # The tenancy of a resource. Examples are shared or dedicated.
    'USAGE_TYPE',  # The type of usage. An example is DataTransfer-In-Bytes
    'USAGE_TYPE_GROUP',  # The grouping of common usage types. An example is Amazon EC2: CloudWatch – Alarms
    'REGION',  # The Amazon Web Services Region
    'RECORD_TYPE',  # The different types of charges such as Reserved Instance (RI) fees, usage costs, tax refunds, and credits
]

# Valid cost metrics for AWS Cost Explorer
VALID_COST_METRICS: List[str] = [
    'AmortizedCost',
    'BlendedCost',
    'NetAmortizedCost',
    'NetUnblendedCost',
    'UnblendedCost',
    'UsageQuantity',
]

# Valid granularity options for AWS Cost Explorer
VALID_GRANULARITIES: List[str] = ['DAILY', 'MONTHLY', 'HOURLY']

# Valid forecast granularities (subset of VALID_GRANULARITIES)
VALID_FORECAST_GRANULARITIES: List[str] = ['DAILY', 'MONTHLY']

# Valid match options for different filter types
VALID_MATCH_OPTIONS = {
    'Dimensions': ['EQUALS', 'CASE_SENSITIVE'],
    'Tags': ['EQUALS', 'ABSENT', 'CASE_SENSITIVE'],
    'CostCategories': ['EQUALS', 'ABSENT', 'CASE_SENSITIVE'],
}

# Valid group by types for AWS Cost Explorer
VALID_GROUP_BY_TYPES: List[str] = ['DIMENSION', 'TAG', 'COST_CATEGORY']

# Valid dimension keys for GROUP BY operations (subset of VALID_DIMENSIONS)
VALID_GROUP_BY_DIMENSIONS: List[str] = [
    'AZ',
    'INSTANCE_TYPE',
    'LEGAL_ENTITY_NAME',
    'INVOICING_ENTITY',
    'LINKED_ACCOUNT',
    'OPERATION',
    'PLATFORM',
    'PURCHASE_TYPE',
    'SERVICE',
    'TENANCY',
    'RECORD_TYPE',
    'USAGE_TYPE',
]

# Valid forecast metrics (UsageQuantity forecasting is not supported by AWS)
VALID_FORECAST_METRICS: List[str] = [
    'AMORTIZED_COST',
    'BLENDED_COST',
    'NET_AMORTIZED_COST',
    'NET_UNBLENDED_COST',
    'UNBLENDED_COST',
]

# Valid prediction interval levels for forecasts
VALID_PREDICTION_INTERVALS: List[int] = [80, 95]
