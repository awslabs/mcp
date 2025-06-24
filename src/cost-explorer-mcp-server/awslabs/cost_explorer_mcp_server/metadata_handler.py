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

"""Cost Explorer MCP server implementation.

Metadata tools for Cost Explorer MCP Server.
"""

import os
import sys
from awslabs.cost_explorer_mcp_server.helpers import (
    get_available_dimension_values,
    get_available_tag_values,
)
from awslabs.cost_explorer_mcp_server.models import DateRange, DimensionKey
from loguru import logger
from mcp.server.fastmcp import Context
from pydantic import Field
from typing import Any, Dict


# Configure Loguru logging
logger.remove()
logger.add(sys.stderr, level=os.getenv('FASTMCP_LOG_LEVEL', 'WARNING'))


async def get_dimension_values(
    ctx: Context, date_range: DateRange, dimension: DimensionKey
) -> Dict[str, Any]:
    """Retrieve available dimension values for AWS Cost Explorer.

    This tool retrieves all available and valid values for a specified dimension (e.g., SERVICE, REGION)
    over a period of time. This is useful for validating filter values or exploring available options
    for cost analysis.

    Args:
        ctx: MCP context
        date_range: The billing period start and end dates in YYYY-MM-DD format
        dimension: The dimension key to retrieve values for (e.g., SERVICE, REGION, LINKED_ACCOUNT)

    Returns:
        Dictionary containing the dimension name and list of available values
    """
    try:
        response = get_available_dimension_values(
            dimension.dimension_key, date_range.start_date, date_range.end_date
        )
        return response
    except Exception as e:
        logger.error(f'Error getting dimension values for {dimension.dimension_key}: {e}')
        return {'error': f'Error getting dimension values: {str(e)}'}


async def get_tag_values(
    ctx: Context,
    date_range: DateRange,
    tag_key: str = Field(..., description='The tag key to retrieve values for'),
) -> Dict[str, Any]:
    """Retrieve available tag values for AWS Cost Explorer.

    This tool retrieves all available values for a specified tag key over a period of time.
    This is useful for validating tag filter values or exploring available tag options for cost analysis.

    Args:
        ctx: MCP context
        date_range: The billing period start and end dates in YYYY-MM-DD format
        tag_key: The tag key to retrieve values for

    Returns:
        Dictionary containing the tag key and list of available values
    """
    try:
        response = get_available_tag_values(tag_key, date_range.start_date, date_range.end_date)
        return response
    except Exception as e:
        logger.error(f'Error getting tag values for {tag_key}: {e}')
        return {'error': f'Error getting tag values: {str(e)}'}
