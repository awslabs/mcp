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
from typing import List, Optional, Union


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
    type: str = Field(default='EQUALS', alias='Type', description='The type of filter match')
    value: Union[str, List[str]] = Field(
        ...,
        alias='Value',
        description='The value(s) to match against - string for EQUALS/CONTAINS, list for ANY_OF/NONE_OF',
    )
    model_config = ConfigDict(validate_by_alias=True)

    def model_dump(self, by_alias=True, **kwargs):
        """Override to handle comma-separated values for ANY_OF and NONE_OF filters."""
        data = super().model_dump(by_alias=by_alias, **kwargs)
        if isinstance(self.value, list):
            data['Value'] = ','.join(self.value)
        return data


class OutputOptions(BaseModel):
    """Output filtering options for pricing responses to reduce response size."""

    pricing_terms: Optional[List[str]] = Field(
        None,
        description='List of pricing terms to include (e.g., ["OnDemand"], ["Reserved"], ["OnDemand", "Reserved"]). Default: include all terms. Use ["OnDemand"] to significantly reduce response size for large services like EC2.',
    )

    product_attributes: Optional[List[str]] = Field(
        None,
        description='List of product attribute keys to include (e.g., ["instanceType", "location", "memory"]). Default: include all attributes. Filtering to essential attributes can provide additional 20-40% size reduction.',
    )

    exclude_free_products: Optional[bool] = Field(
        False,
        description='Filter out products with $0.00 OnDemand pricing to reduce response size',
    )


# Reusable Pydantic Field constants
SERVICE_CODE_FIELD = Field(
    ..., description='AWS service code (e.g., "AmazonEC2", "AmazonS3", "AmazonES")'
)

REGION_FIELD = Field(
    ...,
    description='AWS region(s) - single region string (e.g., "us-east-1") or list for multi-region comparison (e.g., ["us-east-1", "us-west-2", "eu-west-1"])',
)

ATTRIBUTE_NAMES_FIELD = Field(
    ..., description='List of attribute names (e.g., ["instanceType", "location", "storageClass"])'
)

FILTERS_FIELD = Field(None, description='Optional list of filters to apply to the pricing query')

GET_PRICING_MAX_ALLOWED_CHARACTERS_FIELD = Field(
    100000,
    description='Maximum response length in characters (default: 100,000, use -1 for unlimited)',
)

EFFECTIVE_DATE_FIELD = Field(
    None,
    description='Effective date for pricing in format "YYYY-MM-DD HH:MM" (default: current timestamp)',
)

OUTPUT_OPTIONS_FIELD = Field(
    None,
    description='Optional output filtering options to reduce response size. Use {"pricing_terms": ["OnDemand"]} to significantly reduce response size for large services like EC2.',
)

MAX_RESULTS_FIELD = Field(
    100,
    description='Maximum number of results to return per page (default: 100, max: 100)',
    ge=1,
    le=100,
)

NEXT_TOKEN_FIELD = Field(
    None,
    description='Pagination token from previous response to get next page of results',
)
