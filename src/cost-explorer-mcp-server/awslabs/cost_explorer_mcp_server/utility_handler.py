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

Utility tools for Cost Explorer MCP Server.

"""

import os
import sys
from datetime import datetime, timezone
from loguru import logger
from mcp.server.fastmcp import Context
from typing import Dict


# Configure Loguru logging
logger.remove()
logger.add(sys.stderr, level=os.getenv('FASTMCP_LOG_LEVEL', 'WARNING'))


async def get_today_date(ctx: Context) -> Dict[str, str]:
    """Retrieve current date information in UTC time zone.

    This tool retrieves the current date in YYYY-MM-DD format and the current month in YYYY-MM format.
    It's useful for calculating relevent date when user ask last N months/days.

    Args:
        ctx: MCP context

    Returns:
        Dictionary containing today's date and current month
    """
    now_utc = datetime.now(timezone.utc)
    return {
        'today_date_UTC': now_utc.strftime('%Y-%m-%d'),
        'current_month': now_utc.strftime('%Y-%m'),
    }
