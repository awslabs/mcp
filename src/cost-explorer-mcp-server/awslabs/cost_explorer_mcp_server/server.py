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

This server provides tools for analyzing AWS costs and usage data through the AWS Cost Explorer API.
"""

import os
import sys
from awslabs.cost_explorer_mcp_server.comparison_handler import (
    get_cost_and_usage_comparisons,
    get_cost_comparison_drivers,
)
from awslabs.cost_explorer_mcp_server.cost_usage_handler import get_cost_and_usage
from awslabs.cost_explorer_mcp_server.forecasting_handler import get_cost_forecast
from awslabs.cost_explorer_mcp_server.metadata_handler import (
    get_dimension_values,
    get_tag_values,
)
from awslabs.cost_explorer_mcp_server.utility_handler import get_today_date
from loguru import logger
from mcp.server.fastmcp import FastMCP


# Configure Loguru logging
logger.remove()
logger.add(sys.stderr, level=os.getenv('FASTMCP_LOG_LEVEL', 'WARNING'))

# Define server instructions
SERVER_INSTRUCTIONS = """
# AWS Cost Explorer MCP Server

## IMPORTANT: Each API call costs $0.01 - use filters and specific date ranges to minimize charges.

## Critical Rules
- Comparison periods: exactly 1 month, start on day 1 (e.g., "2025-04-01" to "2025-05-01")
- UsageQuantity: Recommended to filter by USAGE_TYPE, USAGE_TYPE_GROUP or results are meaningless
- When user says "last X months" - use full calendar months, not partial periods
- get_cost_comparison_drivers: returns only top 10 most significant drivers
"""

# Create FastMCP server with instructions
app = FastMCP(title='Cost Explorer MCP Server', instructions=SERVER_INSTRUCTIONS)

# Register all tools with the app
app.tool('get_today_date')(get_today_date)
app.tool('get_dimension_values')(get_dimension_values)
app.tool('get_tag_values')(get_tag_values)
app.tool('get_cost_forecast')(get_cost_forecast)
app.tool('get_cost_and_usage_comparisons')(get_cost_and_usage_comparisons)
app.tool('get_cost_comparison_drivers')(get_cost_comparison_drivers)
app.tool('get_cost_and_usage')(get_cost_and_usage)


def main():
    """Run the MCP server with CLI argument support."""
    app.run()


if __name__ == '__main__':
    main()
