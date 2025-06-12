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

"""Get cost and usage data for ElastiCache resources."""

from ...common.connection import CostExplorerConnectionManager
from ...common.decorators import handle_exceptions
from ...common.server import mcp
from pydantic import BaseModel, ConfigDict, Field
from typing import Any, Dict


class GetCostAndUsageRequest(BaseModel):
    """Request model for getting cost and usage data."""

    model_config = ConfigDict(validate_by_name=True, arbitrary_types_allowed=True)

    time_period: str = Field(
        ..., description='Time period for the cost and usage data. Format: YYYY-MM-DD/YYYY-MM-DD'
    )
    granularity: str = Field(
        ..., description='The granularity of the cost and usage data (DAILY, MONTHLY, or HOURLY)'
    )


@mcp.tool(name='get-cost-and-usage')
@handle_exceptions
async def get_cost_and_usage(request: GetCostAndUsageRequest) -> Dict[str, Any]:
    """Get cost and usage data for ElastiCache resources.

    This tool retrieves cost and usage data for ElastiCache resources with customizable
    time periods and granularity. It uses default configurations for:
    - Metrics: BlendedCost, UnblendedCost, UsageQuantity
    - Group By: SERVICE dimension and Environment tag
    - Filter: Filtered to Amazon ElastiCache service

    Args:
        request: The GetCostAndUsageRequest object containing:
            - time_period: Time period in YYYY-MM-DD/YYYY-MM-DD format
            - granularity: Data granularity (DAILY, MONTHLY, or HOURLY)

    Returns:
        Dict containing the cost and usage data.
    """
    # Get Cost Explorer client
    ce_client = CostExplorerConnectionManager.get_connection()

    # Split time period into start and end dates
    start_date, end_date = request.time_period.split('/')

    # Prepare request parameters
    params = {
        'TimePeriod': {'Start': start_date, 'End': end_date},
        'Granularity': request.granularity,
        'Metrics': ['BlendedCost', 'UnblendedCost', 'UsageQuantity'],
        'GroupBy': [
            {'Type': 'DIMENSION', 'Key': 'SERVICE'},
            {'Type': 'TAG', 'Key': 'Environment'},
        ],
        'Filter': {'Dimensions': {'Key': 'SERVICE', 'Values': ['Amazon ElastiCache']}},
    }

    # Get cost and usage data
    response = ce_client.get_cost_and_usage(**params)
    return response
