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

"""AWS Procurement Portal Preference tools for the BCM MCP server.

Exposes a single read-only ``procurement-preferences`` tool that routes by
``operation`` across the AWS Procurement Portal Preferences read APIs
(mirroring the ``invoicing`` tool). The rich tool description is the primary
vehicle that gives the agent semantic context about every request parameter and
response field.
"""

from ..utilities.aws_service_base import format_response
from .procurement_preferences_operations import (
    get_procurement_portal_preference as _get_procurement_portal_preference,
)
from .procurement_preferences_operations import (
    list_procurement_portal_preferences as _list_procurement_portal_preferences,
)
from fastmcp import Context, FastMCP
from typing import Any, Dict, Optional


procurement_preferences_server = FastMCP(
    name='procurement-preferences-tools',
    instructions='Read-only tools for AWS Procurement Portal Preferences (SAP/Coupa, e-invoice delivery)',
)


async def _procurement_preferences(
    ctx: Context,
    operation: str,
    procurement_portal_preference_arn: Optional[str] = None,
    max_results: Optional[int] = None,
    next_token: Optional[str] = None,
    max_pages: Optional[int] = None,
) -> Dict[str, Any]:
    """Route an AWS Procurement Portal Preference ``operation`` to its handler.

    Kept separate from the FastMCP-decorated wrapper so the routing can be unit
    tested directly (decorated tools cannot be invoked as plain functions).

    Args:
        ctx: The MCP context object.
        operation: The operation (``"list_procurement_portal_preferences"`` or
            ``"get_procurement_portal_preference"``).
        procurement_portal_preference_arn: ARN of a single preference
            (get_procurement_portal_preference).
        max_results: Maximum results per page (1-100).
        next_token: Pagination token from a previous response.
        max_pages: Maximum pages to auto-paginate through (default: all).

    Returns:
        The operation's response, or a standardized error for an unknown
        operation.
    """
    await ctx.info(f'Procurement portal preference operation: {operation}')

    if operation == 'list_procurement_portal_preferences':
        return await _list_procurement_portal_preferences(
            ctx,
            max_results=max_results,
            next_token=next_token,
            max_pages=max_pages,
        )

    if operation == 'get_procurement_portal_preference':
        if procurement_portal_preference_arn is None:
            return format_response(
                'error',
                {
                    'message': (
                        'procurement_portal_preference_arn is required for '
                        'get_procurement_portal_preference.'
                    )
                },
            )
        return await _get_procurement_portal_preference(
            ctx,
            procurement_portal_preference_arn=procurement_portal_preference_arn,
        )

    return format_response(
        'error',
        {
            'message': (
                f"Unsupported operation: '{operation}'. Supported operations: "
                'list_procurement_portal_preferences, get_procurement_portal_preference.'
            )
        },
    )


@procurement_preferences_server.tool(
    name='procurement-preferences',
    description="""Access AWS Procurement Portal Preferences — read-only. These are the procurement portal connections (e.g. SAP Business Network, Coupa) and e-invoice delivery / purchase-order retrieval settings configured for the account. Choose an action with the required `operation` parameter.

## OPERATIONS

1) list_procurement_portal_preferences - list configured procurement portal preferences
   Required: operation="list_procurement_portal_preferences"
   Pagination: max_results caps items per page (1-100); max_pages caps pages fetched (default: all). The `pagination` block reports total_results, pages_fetched, has_more, and next_token.
   Returns: `data.procurement_portal_preferences`, each including the preference ARN, portal type/connection details, status, EinvoiceDeliveryPreference, and CreateDate / LastUpdateDate (ISO 8601 UTC).

2) get_procurement_portal_preference - retrieve one procurement portal preference
   Required: operation="get_procurement_portal_preference", procurement_portal_preference_arn
   Returns: `data.procurement_portal_preference` with the fields above, including EinvoiceDeliveryPreference.EinvoiceDeliveryActivationDate (ISO 8601 UTC).

NOTE: preference records may include procurement portal connection details; treat the output as sensitive.

EXAMPLES
- {"operation": "list_procurement_portal_preferences"}
- {"operation": "get_procurement_portal_preference", "procurement_portal_preference_arn": "arn:aws:invoicing::123456789012:procurement-portal-preference/abc123"}""",
)
async def procurement_preferences(
    ctx: Context,
    operation: str,
    procurement_portal_preference_arn: Optional[str] = None,
    max_results: Optional[int] = None,
    next_token: Optional[str] = None,
    max_pages: Optional[int] = None,
) -> Dict[str, Any]:
    """FastMCP wrapper for AWS Procurement Portal Preference operations.

    Thin wrapper so the routing logic in ``_procurement_preferences`` can be
    unit tested directly (FastMCP-decorated tools cannot be invoked as plain
    functions).

    Args:
        ctx: The MCP context object.
        operation: The operation to perform.
        procurement_portal_preference_arn: ARN of a single preference
            (get_procurement_portal_preference).
        max_results: Maximum results per page (1-100).
        next_token: Pagination token from a previous response.
        max_pages: Maximum pages to auto-paginate through (default: all).

    Returns:
        Dict containing the operation result.
    """
    return await _procurement_preferences(
        ctx,
        operation,
        procurement_portal_preference_arn=procurement_portal_preference_arn,
        max_results=max_results,
        next_token=next_token,
        max_pages=max_pages,
    )
