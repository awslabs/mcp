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

"""awslabs MCP Cost Analysis mcp server implementation.

This server provides models for analyzing AWS service costs.
"""

from pydantic import BaseModel, ConfigDict, Field


class ErrorResponse(BaseModel):
    """Generic standardized error response model for all MCP tools."""

    status: str = Field(default='error', description='Response status')
    error_type: str = Field(..., description='Type of error that occurred')
    message: str = Field(..., description='Human-readable error message')

    # Allow any additional fields to be passed dynamically
    model_config = ConfigDict(extra='allow')


class PricingFilter(BaseModel):
    """Filter model for AWS Price List API queries."""

    field: str = Field(
        ..., alias='Field', description="The field to filter on (e.g., 'instanceType', 'location')"
    )
    type: str = Field(default='TERM_MATCH', alias='Type', description='The type of filter match')
    value: str = Field(..., alias='Value', description='The value to match against')
    model_config = ConfigDict(validate_by_alias=True)


class PricingFilters(BaseModel):
    """Container for multiple pricing filters."""

    filters: list[PricingFilter] = Field(
        default_factory=list, description='List of filters to apply to the pricing query'
    )
