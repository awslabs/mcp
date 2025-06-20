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

from awslabs.cost_explorer_mcp_server.helpers import validate_date_format, validate_date_range
from pydantic import BaseModel, Field, field_validator


"""Data models and validation logic for Cost Explorer MCP Server.
"""


class DateRange(BaseModel):
    """Date range model for cost queries."""

    start_date: str = Field(
        description='The start date of the billing period in YYYY-MM-DD format. Defaults to last month, if not provided.'
    )
    end_date: str = Field(description='The end date of the billing period in YYYY-MM-DD format.')

    @field_validator('start_date', 'end_date')
    @classmethod
    def validate_individual_dates(cls, v):
        """Validate that individual dates are in YYYY-MM-DD format and are valid dates."""
        is_valid, error = validate_date_format(v)
        if not is_valid:
            raise ValueError(error)
        return v

    def model_post_init(self, __context):
        """Validate the date range after both dates are set."""
        is_valid, error = validate_date_range(self.start_date, self.end_date)
        if not is_valid:
            raise ValueError(error)

    def validate_with_granularity(self, granularity: str):
        """Validate the date range with granularity-specific constraints."""
        is_valid, error = validate_date_range(self.start_date, self.end_date, granularity)
        if not is_valid:
            raise ValueError(error)


class DimensionKey(BaseModel):
    """Dimension key model."""

    dimension_key: str = Field(
        description='The name of the dimension to retrieve values for. Valid values are AZ, INSTANCE_TYPE, LINKED_ACCOUNT, OPERATION, PURCHASE_TYPE, SERVICE, USAGE_TYPE, PLATFORM, TENANCY, RECORD_TYPE, LEGAL_ENTITY_NAME, INVOICING_ENTITY, DEPLOYMENT_OPTION, DATABASE_ENGINE, CACHE_ENGINE, INSTANCE_TYPE_FAMILY, REGION, BILLING_ENTITY, RESERVATION_ID, SAVINGS_PLANS_TYPE, SAVINGS_PLAN_ARN, OPERATING_SYSTEM.'
    )
