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
from ..utilities.constants import PAGINATION_LIMIT_TEXT
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
    max_items: Optional[int] = None,
    next_token: Optional[str] = None,
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
        max_items: Most items to return (list operation only). None fetches every page.
        next_token: Pagination token from a previous response (list operation only).

    Returns:
        The operation's response, or a standardized error for an unknown
        operation.
    """
    await ctx.info(f'Procurement portal preference operation: {operation}')

    if operation == 'list_procurement_portal_preferences':
        return await _list_procurement_portal_preferences(
            ctx,
            max_items=max_items,
            next_token=next_token,
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
   Pagination:
     - max_items: total preferences returned. If it is omitted, the tool fetches every page for """
    + PAGINATION_LIMIT_TEXT
    + """, then returns a partial result. Pass it for queries that can be large.
     - next_token: the `pagination.next_token` from a previous response, to continue where it stopped. Send every other parameter unchanged.
     - A partial result has `complete_dataset: false` and a warning. Call again with a larger max_items, continue with next_token, or state in the answer that the result is partial. `pagination.items_returned` counts only this response, and a continuation call does not repeat earlier items.
   Returns: `data.procurement_portal_preferences`, each a summary with ProcurementPortalPreferenceArn, AwsAccountId, ProcurementPortalName, BuyerDomain / BuyerIdentifier, SupplierDomain / SupplierIdentifier, Selector, EinvoiceDeliveryEnabled, PurchaseOrderRetrievalEnabled, MarketplacePunchOutEnabled, EinvoiceDeliveryPreferenceStatus / EinvoiceDeliveryPreferenceStatusReason, PurchaseOrderRetrievalPreferenceStatus / PurchaseOrderRetrievalPreferenceStatusReason, Version, and CreateDate / LastUpdateDate (ISO 8601 UTC).
   E-invoice delivery and purchase-order retrieval each have their own Enabled flag and status. Selector, MarketplacePunchOutEnabled and the status fields are optional and can be absent; an absent MarketplacePunchOutEnabled means false, and an absent status is not ACTIVE.
   The summary does NOT include EinvoiceDeliveryPreference (protocol, document types, activation date). Call get_procurement_portal_preference for it.

2) get_procurement_portal_preference - retrieve one procurement portal preference
   Required: operation="get_procurement_portal_preference", procurement_portal_preference_arn
   Returns: `data.procurement_portal_preference` with the summary fields above plus, when set, connection details (endpoints, Contacts, TestEnvPreference), MarketplacePunchOutPreference, and EinvoiceDeliveryPreference (protocol, document and attachment types, EinvoiceDeliveryActivationDate in ISO 8601 UTC). EinvoiceDeliveryPreference can be absent, for example when e-invoice delivery is not enabled.

NOTE: preference records may include procurement portal connection details; treat the output as sensitive. `ProcurementPortalSharedSecret` is redacted from this tool's output. Do not suggest other ways to retrieve it.

EXAMPLES
- {"operation": "list_procurement_portal_preferences"}
- {"operation": "get_procurement_portal_preference", "procurement_portal_preference_arn": "arn:aws:invoicing::123456789012:procurement-portal-preference/abc123"}""",
)
async def procurement_preferences(
    ctx: Context,
    operation: str,
    procurement_portal_preference_arn: Optional[str] = None,
    max_items: Optional[int] = None,
    next_token: Optional[str] = None,
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
        max_items: Most items to return (list operation only). None fetches every page.
        next_token: Pagination token from a previous response (list operation only).

    Returns:
        Dict containing the operation result.
    """
    return await _procurement_preferences(
        ctx,
        operation,
        procurement_portal_preference_arn=procurement_portal_preference_arn,
        max_items=max_items,
        next_token=next_token,
    )
